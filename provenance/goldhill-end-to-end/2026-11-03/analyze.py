"""Matched-support numerical spectral/PFT diagnostics; no calibration claims."""

import importlib.util
import itertools
import json
from pathlib import Path
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import rasterio
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
from spectralbridge.library_analysis import (  # noqa: E402
    spectral_separability,
    evaluate_identifiability,
)  # noqa: E402
from spectralbridge.researcher_information import validate_researcher_labels  # noqa: E402
from spectralbridge.researcher_validation import paired_identity_interval  # noqa: E402

WORK = Path("/private/tmp/goldhill-end-to-end-20261103")
WAVE = np.array([444, 475, 531, 560, 650, 668, 705, 717, 740, 862])
POLYGONS = (
    ROOT / "Datasets/niwot_aop_polygons_2023_12_8_23_analysis_ready_half_diam.gpkg"
)


def safe(x):
    if isinstance(x, dict):
        return {str(k): safe(v) for k, v in x.items()}
    if isinstance(x, (list, tuple, np.ndarray)):
        return [safe(v) for v in x]
    if isinstance(x, np.generic):
        return safe(x.item())
    if isinstance(x, float) and not np.isfinite(x):
        return None
    return x


def write(name, x):
    (HERE / name).write_text(json.dumps(safe(x), indent=2, allow_nan=False) + "\n")


def angle(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    den = np.linalg.norm(x, axis=-1) * np.linalg.norm(y, axis=-1)
    return np.degrees(
        np.arccos(
            np.clip(
                np.divide(
                    np.sum(x * y, axis=-1),
                    den,
                    out=np.full_like(den, np.nan),
                    where=den > 0,
                ),
                -1,
                1,
            )
        )
    )


def numeric_table(frame, path, metadata):
    table = pa.Table.from_pandas(frame, preserve_index=False)
    meta = dict(table.schema.metadata or {})
    meta[b"spectralbridge.experimental_numeric_only"] = json.dumps(
        metadata, sort_keys=True
    ).encode()
    pq.write_table(table.replace_schema_metadata(meta), path, compression="zstd")


def main():
    config = json.loads((HERE / "branches.json").read_text())
    branches = config["branches"]
    arrays = {}
    for name, item in branches.items():
        if item["format"] == "npy":
            arrays[name] = np.load(item["path"], mmap_mode="r")
        else:
            with rasterio.open(item["path"]) as src:
                arrays[name] = src.read().transpose(1, 2, 0)
    # Compose the verified inverse old normalization with the requested fixed encoding.
    out = WORK / "old_reencoded_fixed.npy"
    if not out.exists():
        a = np.lib.format.open_memmap(
            out, mode="w+", dtype="float32", shape=arrays["old_raw"].shape
        )
        for b in range(10):
            minimum = 174 if b == 9 else 0
            a[..., b] = (
                arrays["old_raw"][..., b] * (65535 - minimum) / 65535
                + minimum * 10000 / 65535
            )
        a.flush()
        del a
    arrays["old_reencoded_fixed"] = np.load(out, mmap_mode="r")
    masks = {
        name: np.isfinite(a).all(axis=-1) & (a != -9999).all(axis=-1)
        for name, a in arrays.items()
    }
    masks["old_reencoded_fixed"] &= masks["old_raw"]
    raw_common = masks["old_raw"] & masks["new_raw"]
    common = np.logical_and.reduce(list(masks.values()))
    np.save(WORK / "common_all.npy", common)
    np.save(WORK / "common_raw.npy", raw_common)
    coverage = []
    stats = []
    corrections = []
    boundary = []
    display = {}
    selection = json.loads(
        (
            ROOT / "provenance/brdf-artifact-anatomy/2026-11-03/selection.json"
        ).read_text()
    )
    y0, y1, x0, x1 = selection["roi_native_indices"]
    roi = np.s_[y0:y1, x0:x1]
    row = selection["main_transect_row"]
    left = selection["main_transition_left_column"]
    oldratio = np.divide(
        arrays["old_brdf"][..., 4],
        arrays["old_raw"][..., 4],
        out=np.ones(common.shape, np.float32),
        where=np.isfinite(arrays["old_raw"][..., 4]) & (arrays["old_raw"][..., 4] > 0),
    )
    positive = oldratio > 1.01
    horizontal = (positive[:, :-1] != positive[:, 1:]) & common[:, :-1] & common[:, 1:]
    vertical = (positive[:-1] != positive[1:]) & common[:-1] & common[1:]
    for name, a in arrays.items():
        print("NUMERICAL scene stats", name, flush=True)
        coverage.append(
            dict(
                branch=name,
                valid_pixels=int(masks[name].sum()),
                raw_pair_common=int((masks[name] & raw_common).sum()),
                all_branch_common=int(common.sum()),
                excluded_by_stage_from_new_source=int(
                    (masks["new_raw"] & ~masks[name]).sum()
                ),
            )
        )
        display[name + "_red"] = np.where(masks[name][::6, ::6], a[::6, ::6, 4], np.nan)
        display[name + "_rgb"] = a[::6, ::6][:, :, [4, 3, 1]].copy()
        display[name + "_zoom_red"] = np.where(common[roi], a[roi][..., 4], np.nan)
        display[name + "_zoom_rgb"] = a[roi][:, :, [4, 3, 1]].copy()
        display[name + "_transect"] = a[row, 840:1120, 4].copy()
        for b in range(10):
            v = a[..., b][common].astype(float)
            own = a[..., b][masks[name]].astype(float)
            stats.append(
                dict(
                    branch=name,
                    wavelength_nm=int(WAVE[b]),
                    common_pixels=int(len(v)),
                    minimum=float(v.min()),
                    maximum=float(v.max()),
                    mean=float(v.mean()),
                    variance=float(v.var()),
                    quantiles=np.quantile(
                        v, [0, 0.001, 0.01, 0.25, 0.5, 0.75, 0.99, 0.999, 1]
                    ).tolist(),
                    negative=int((v < 0).sum()),
                    above_10000_encoding_units=int((v > 10000).sum()),
                    own_support_mean=float(own.mean()),
                    own_support_quantiles=np.quantile(
                        own, [0, 0.01, 0.5, 0.99, 1]
                    ).tolist(),
                )
            )
        red = a[..., 4]
        jumps = np.r_[
            abs(red[:, 1:] - red[:, :-1])[horizontal], abs(red[1:] - red[:-1])[vertical]
        ].astype(float)
        boundary.append(
            dict(
                branch=name,
                edges=int(len(jumps)),
                median_abs_jump=float(np.median(jumps)),
                p99_abs_jump=float(np.quantile(jumps, 0.99)),
                maximum_abs_jump=float(jumps.max()),
                fixed_row=int(row),
                left_column=int(left),
                fixed_left=float(red[row, left]),
                fixed_right=float(red[row, left + 1]),
                fixed_jump=float(
                    abs(float(red[row, left + 1]) - float(red[row, left]))
                ),
            )
        )
        if name.startswith("new_historical_"):
            for b in range(10):
                base = arrays["new_raw"][..., b]
                valid = common & (base > 0)
                f = (a[..., b][valid] / base[valid]).astype(float)
                corrections.append(
                    dict(
                        branch=name,
                        wavelength_nm=int(WAVE[b]),
                        n=int(len(f)),
                        minimum=float(f.min()),
                        maximum=float(f.max()),
                        quantiles=np.quantile(
                            f, [0, 0.001, 0.01, 0.5, 0.99, 0.999, 1]
                        ).tolist(),
                        above_2=int((f > 2).sum()),
                        above_10=int((f > 10).sum()),
                        above_100=int((f > 100).sum()),
                        zero_base_excluded=int((common & (base == 0)).sum()),
                    )
                )
    display["new_mask"] = masks["new_raw"][::6, ::6]
    display["old_mask"] = masks["old_raw"][::6, ::6]
    display["common_mask"] = common[::6, ::6]
    ci = np.load(config["illumination"], mmap_mode="r")
    display["ci"] = ci[::6, ::6]
    write(
        "illumination_statistics.json",
        dict(
            valid_new=int((masks["new_raw"] & np.isfinite(ci)).sum()),
            missing_on_new=int((masks["new_raw"] & ~np.isfinite(ci)).sum()),
            negative_or_zero_on_new=int(
                (masks["new_raw"] & np.isfinite(ci) & (ci <= 0)).sum()
            ),
            quantiles=np.quantile(ci[common], [0, 0.01, 0.5, 0.99, 1]),
            solar_datetime_status="UNVERIFIED; original date and inherited computation date conflict",
        ),
    )
    pd.DataFrame(coverage).to_csv(HERE / "stage_coverage.csv", index=False)
    pd.DataFrame(stats).to_json(
        HERE / "scene_band_statistics.json", orient="records", indent=2
    )
    pd.DataFrame(boundary).to_csv(
        HERE / "red_boundary_discontinuities.csv", index=False
    )
    write("correction_factor_statistics.json", corrections)
    # Actual production membership, then numerical sampling in an explicitly nonphysical dataset.
    index = pd.read_parquet(config["polygon_index"])
    rr = index.row.to_numpy()
    cc = index.col.to_numpy()
    index["common_all"] = common[rr, cc]
    index["common_raw"] = raw_common[rr, cc]
    coverage_poly = []
    poly = []
    pixelcomparisons = []
    experiment = WORK / "numerical_polygon_tables"
    experiment.mkdir(exist_ok=True)
    groups = index.groupby("GlobalID", sort=True)
    for name, a in arrays.items():
        x = a[rr, cc].astype(np.float32)
        own = masks[name][rr, cc]
        keep = index.common_all.to_numpy()
        frame = index.loc[
            keep,
            [
                "GlobalID",
                "cover_category",
                "species",
                "flight_id",
                "pixel_id",
                "row",
                "col",
            ],
        ].copy()
        for b, w in enumerate(WAVE):
            frame[f"encoded_{w}nm"] = x[keep, b]
        frame["branch"] = name
        frame["units"] = "uncalibrated numerical encoding; not physical reflectance"
        manifest = json.loads((HERE / "input_manifest.json").read_text())
        if name.startswith("old_"):
            source_input = (
                branches["old_raw"]["path"]
                if name == "old_reencoded_fixed"
                else branches[name]["path"]
            )
        else:
            source_input = str(
                Path(
                    "/private/tmp/p168-goldhill-sources/derived_10cm_10k/goldhill_10cm_fixed_10k.tif"
                )
            )
        frame["source_input"] = source_input
        frame["source_sha256"] = manifest["protected_hashes"][source_input]

        numeric_table(
            frame,
            experiment / f"{name}_diagnostic_numeric.parquet",
            dict(
                status="UNVERIFIED_NUMERICAL_ONLY",
                branch=name,
                selection="common_all; actual package polygon index; pixel centers/all_touched=False",
                wavelengths_nm=WAVE.tolist(),
            ),
        )
        for identity, g in groups:
            ix = g.index.to_numpy()
            selected = ix[keep[ix]]
            native = ix[own[ix]]
            rec = dict(
                branch=name,
                GlobalID=identity,
                cover_category=str(g.cover_category.iloc[0]),
                species=str(g.species.iloc[0]),
                index_pixels=len(ix),
                native_valid_pixels=len(native),
                common_pixels=len(selected),
            )
            coverage_poly.append(rec)
            if not len(selected):
                continue
            values = x[selected].astype(float)
            mean = values.mean(0)
            sd = values.std(0, ddof=1) if len(values) > 1 else np.full(10, np.nan)
            cv = np.divide(
                sd, abs(mean), out=np.full(10, np.nan), where=abs(mean) > 1e-12
            )
            rec.update(
                mean_band_variance=float(np.mean(sd**2)),
                median_band_cv=float(np.nanmedian(cv)),
                median_pixel_angle_to_mean=float(np.nanmedian(angle(values, mean))),
                native_mean_bands=x[native].mean(0).tolist() if len(native) else None,
            )
            for b in range(10):
                rec[f"b{b + 1}"] = mean[b]
            poly.append(rec)
        newx = arrays["new_raw"][rr[keep], cc[keep]].astype(float)
        vx = x[keep].astype(float)
        ang = angle(vx, newx)
        dist = np.linalg.norm(vx - newx, axis=1)
        pixelcomparisons.append(
            dict(
                branch=name,
                n=int(keep.sum()),
                spectral_angle_quantiles=np.nanquantile(
                    ang, [0, 0.01, 0.5, 0.99, 1]
                ).tolist(),
                euclidean_distance_quantiles=np.quantile(
                    dist, [0, 0.01, 0.5, 0.99, 1]
                ).tolist(),
            )
        )
    pd.DataFrame(coverage_poly).to_csv(HERE / "polygon_coverage.csv", index=False)
    table = pd.DataFrame(poly)
    numeric_table(
        table,
        HERE / "polygon_spectral_summaries.parquet",
        dict(
            status="NUMERICAL_ONLY",
            support="identical all-branch common pixels per polygon",
        ),
    )
    table.to_csv(HERE / "polygon_spectral_summaries.csv", index=False)
    write("matched_pixel_spectral_comparisons.json", pixelcomparisons)
    # Outcome-blind removal of overlapping support using the established investigation helper.
    polygons = gpd.read_file(POLYGONS).to_crs(config["profile"]["crs"])
    eligible = set(table.GlobalID)
    selected = polygons[polygons.GlobalID.isin(eligible)].copy()
    spec = importlib.util.spec_from_file_location(
        "p169_existing_polygon_independence",
        ROOT / "provenance/drone-brdf-strategy/2026-11-02/analyze.py",
    )
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    independent = helpers.independent_polygons(selected)
    ids = set(independent.GlobalID)
    table["independent_representative"] = table.GlobalID.isin(ids)
    independent[["GlobalID", "cover_category"]].to_csv(
        HERE / "independent_polygon_representatives.csv", index=False
    )
    classification = []
    separation = []
    classmetrics = []
    predictions = []
    pca_rows = []
    pair_distances = []
    memberships = {}
    for name, g in table[table.independent_representative].groupby("branch", sort=True):
        g = g.sort_values("GlobalID").reset_index(drop=True)
        X = g[[f"b{b + 1}" for b in range(10)]].to_numpy(float)
        y = validate_researcher_labels(g.cover_category)
        ident = g.GlobalID.to_numpy()
        print("PACKAGE PFT methods", name, "independent polygons", len(g), flush=True)
        centroids = []
        classes = sorted(set(y))
        for label in classes:
            xx = X[y == label]
            centroid = xx.mean(0)
            centroids.append(centroid)
            cv = np.std(xx, axis=0, ddof=1) / np.maximum(abs(centroid), 1e-12)
            classmetrics.append(
                dict(
                    branch=name,
                    cover_category=label,
                    polygons=int(len(xx)),
                    mean_variance=float(np.var(xx, axis=0, ddof=1).mean()),
                    median_band_cv=float(np.median(cv)),
                    median_angle_to_centroid=float(np.median(angle(xx, centroid))),
                    median_within_polygon_cv=float(
                        g.loc[y == label, "median_band_cv"].median()
                    ),
                )
            )
        for i, j in itertools.combinations(range(len(classes)), 2):
            q, z = X[y == classes[i]], X[y == classes[j]]
            lo1, hi1 = np.quantile(q, [0.25, 0.75], axis=0)
            lo2, hi2 = np.quantile(z, [0.25, 0.75], axis=0)
            width = np.maximum(hi1, hi2) - np.minimum(lo1, lo2)
            overlap = np.maximum(0, np.minimum(hi1, hi2) - np.maximum(lo1, lo2))
            ratio = np.divide(overlap, width, out=np.zeros(10), where=width > 0)
            pair_distances.append(
                dict(
                    branch=name,
                    first=classes[i],
                    second=classes[j],
                    centroid_angle=float(
                        angle(np.array(centroids[i]), np.array(centroids[j]))
                    ),
                    euclidean_centroid_distance=float(
                        np.linalg.norm(centroids[i] - centroids[j])
                    ),
                    mean_band_IQR_overlap=float(ratio.mean()),
                )
            )
        try:
            result = spectral_separability(
                X,
                y,
                WAVE,
                groups=ident,
                permutations=499,
                seed=20261103,
                integration_weights=np.ones(10),
            )
            pairs = result["pairs"].copy()
            pairs["branch"] = name
            separation.append(pairs)
            result["wavelengths"].to_csv(
                HERE / f"separability_wavelengths_{name}.csv", index=False
            )
        except Exception as e:
            write(
                f"separability_{name}_failure.json",
                dict(status="UNSUPPORTED", reason=str(e)),
            )
        try:
            result = evaluate_identifiability(
                X, y, groups=ident, folds=3, regularization=(1,), seed=20261103
            )
            result["memberships"].to_csv(
                HERE / f"classification_memberships_{name}.csv", index=False
            )
            memberships[name] = result["memberships"]
            prediction = result["predictions"].copy()
            prediction["branch"] = name
            predictions.append(prediction)
            result["confusion"].to_csv(HERE / f"classification_confusion_{name}.csv")
            result["class_metrics"].to_csv(
                HERE / f"classification_class_metrics_{name}.csv", index=False
            )
            classification.append(
                dict(
                    branch=name,
                    status="EXECUTED_EXPLORATORY_POLYGON_CV",
                    **result["overall"],
                    independent_polygons=len(g),
                    class_support=g.cover_category.value_counts().to_dict(),
                    folds=3,
                    regularization_C=1,
                    meaning="Identity-disjoint folds with no intersecting polygon components across identities; single-flight exploratory score, not transfer or physical validation",
                )
            )
        except Exception as e:
            classification.append(
                dict(branch=name, status="UNSUPPORTED", reason=str(e))
            )
        if name in ["new_raw", "old_raw", "old_reencoded_fixed"]:
            pca = PCA(n_components=2)
            score = pca.fit_transform(StandardScaler().fit_transform(X))
            for i in range(len(g)):
                pca_rows.append(
                    dict(
                        branch=name,
                        GlobalID=ident[i],
                        cover_category=y[i],
                        pc1=score[i, 0],
                        pc2=score[i, 1],
                        variance1=pca.explained_variance_ratio_[0],
                        variance2=pca.explained_variance_ratio_[1],
                    )
                )
    # Confirm exactly paired folds, then bootstrap fixed out-of-fold predictions by class/identity.
    if memberships:
        reference = memberships[next(iter(memberships))]
        for name, frame in memberships.items():
            pd.testing.assert_frame_equal(frame, reference)
    allpred = (
        pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()
    )
    allpred.to_csv(HERE / "classification_predictions.csv", index=False)
    gains = []
    if not allpred.empty:
        for base in ["old_raw", "old_reencoded_fixed"]:
            left = allpred[allpred.branch == base]
            right = allpred[allpred.branch == "new_raw"]
            paired = left.merge(
                right, on=["identity", "truth"], suffixes=("_old", "_new")
            )
            if len(paired):
                frame = pd.DataFrame(
                    dict(
                        GlobalID=paired.identity,
                        truth=paired.truth,
                        selected=(paired.prediction_new == paired.truth).astype(float),
                        random=(paired.prediction_old == paired.truth).astype(float),
                    )
                )
                gains.append(
                    dict(
                        comparison="new_raw minus " + base,
                        **paired_identity_interval(frame, draws=1999, seed=20261103),
                        interpretation="Class-stratified paired whole-polygon bootstrap of fixed OOF predictions; training-sample/model uncertainty not included",
                    )
                )
    write("classification_summary.json", classification)
    write("paired_classification_gain.json", gains)
    if separation:
        pd.concat(separation, ignore_index=True).to_csv(
            HERE / "package_separability_pairs.csv", index=False
        )
    pd.DataFrame(classmetrics).to_csv(HERE / "within_class_metrics.csv", index=False)
    pd.DataFrame(pair_distances).to_csv(HERE / "between_class_metrics.csv", index=False)
    pd.DataFrame(pca_rows).to_csv(HERE / "pca_structure.csv", index=False)
    np.savez_compressed(HERE / "display_arrays.npz", **display)
    write(
        "analysis_summary.json",
        dict(
            status="PASS",
            scene_common_all=int(common.sum()),
            scene_common_raw=int(raw_common.sum()),
            polygon_index_rows=len(index),
            polygon_index_identities=int(index.GlobalID.nunique()),
            common_polygon_identities=int(table.GlobalID.nunique()),
            common_polygon_memberships=int(index.common_all.sum()),
            independent_representatives=len(ids),
            independent_class_counts=independent.cover_category.value_counts().to_dict(),
            classes_absent="Non-vegetated & dead is not represented in this Goldhill subset; not invented or relabeled",
            comparison_units="Stored numerical 0–10000 encodings; old_reencoded_fixed controls verified affine normalization change",
            raw_pixel_improvement_requires_comparison="new_raw versus old_reencoded_fixed, on common pixels; CV/angle differences versus old_raw may follow encoding alone",
            library_status="No approved physical library generated; numerical tables explicitly flagged UNVERIFIED",
            production_corrections="UNSUPPORTED; legacy replays only",
            abundance=dict(
                status="NOT_EVALUATED",
                reason="No verified physical library, independent fractional-cover ground truth or defensible abundance validation design; category recognition cannot validate abundance accuracy",
            ),
            classification_uncertainty="Only polygon-disjoint single-flight inference; no independent site/year/domain validation. Four recorded classes, no fifth invented class.",
            PCA="Each raw representation fitted separately for descriptive structure; component axes may rotate/flip, not direct physical-change measurements",
            boundary_definition="Edges where the historical red factor crosses 1.01, fixed from old outputs before new-branch evaluation; common support only",
            display_roi=selection,
        ),
    )
    print("Matched-support numerical/PFT analysis complete", flush=True)


if __name__ == "__main__":
    main()
