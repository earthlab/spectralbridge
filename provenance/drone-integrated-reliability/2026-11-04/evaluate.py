# ruff: noqa: E402
"""Fixed ROI and unchanged polygon/fold evaluation, with no score-driven tuning."""

import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
P172 = ROOT / "provenance/goldhill-clean-source-brdf/2026-11-03"
sys.path.insert(0, str(P172))
from common import dist, safe, angle, SCALE, WAVES  # noqa:E402
from spectralbridge.library_analysis import (
    evaluate_identifiability,
    spectral_separability,
)  # noqa:E402
from spectralbridge.researcher_validation import paired_identity_interval  # noqa:E402

WORK = Path("/private/tmp/drone-integrated-reliability-20261104/final_v2")
OLDWORK = Path("/private/tmp/goldhill-clean-source-brdf-20261103")


def write(n, v):
    (HERE / n).write_text(json.dumps(safe(v), indent=2, allow_nan=False) + "\n")


def main():
    statuses = json.loads((HERE / "pipeline_results.json").read_text())
    assert len(statuses) == 7, "Wait for all requested controlled branches"
    raw = np.load(OLDWORK / "clean_candidate.npy", mmap_mode="r")
    historical = np.load(OLDWORK / "B_historical_stored.npy", mmap_mode="r")
    topo = np.load(
        "/private/tmp/goldhill-conditional-topographic-20261103/current.npy",
        mmap_mode="r",
    )
    maps = np.load(
        "/private/tmp/goldhill-viewing-geometry-20261104/geometry_native.npy",
        mmap_mode="r",
    )
    arrays = {
        "clean_raw": (raw, 1),
        "historical_BRDF": (historical, SCALE),
        "topographic_only": (topo, 1),
        "baseline_BRDF": (
            np.load(
                "/private/tmp/goldhill-viewing-geometry-20261104/C_center_brdf.npy",
                mmap_mode="r",
            ),
            1,
        ),
        "baseline_combined": (
            np.load(
                "/private/tmp/goldhill-viewing-geometry-20261104/C_center_combined.npy",
                mmap_mode="r",
            ),
            1,
        ),
    }
    arrays.update(
        {
            s["branch"]: (np.load(s["array"], mmap_mode="r"), 1)
            for s in statuses
            if s["image_created"]
        }
    )
    common = np.load(OLDWORK / "common_spectral_support.npy", mmap_mode="r")
    for array, scale in arrays.values():
        common = common & np.isfinite(array).all(-1)
    np.save(WORK / "common_spectral_support.npy", common)
    fixed = json.loads((P172 / "fixed_regions.json").read_text())["selection"]
    y0, y1, x0, x1 = fixed["roi_native_indices"]
    roi = np.s_[y0:y1, x0:x1]
    row = fixed["main_transect_row"]
    start, end = fixed["main_transect_columns"]
    left = fixed["main_transition_left_column"]
    config = json.loads(
        (ROOT / "provenance/goldhill-end-to-end/2026-11-03/branches.json").read_text()
    )
    index = pd.read_parquet(config["polygon_index"])
    rr = index.row.to_numpy()
    cc = index.col.to_numpy()
    keep = common[rr, cc]
    assert keep.sum() > 0
    ids = set(
        pd.read_csv(
            ROOT
            / "provenance/goldhill-end-to-end/2026-11-03/independent_polygon_representatives.csv"
        ).GlobalID
    )
    oldmembers = pd.read_csv(P172 / "classification_memberships.csv")
    rows = []
    scores = []
    predictions = []
    separations = []
    summaries = []
    images = {}
    transects = {}
    spectra = []
    state = historical[..., 4] * SCALE > raw[..., 4] * 1.01
    base = np.isfinite(raw).all(-1)
    h = (state[:, :-1] != state[:, 1:]) & base[:, :-1] & base[:, 1:]
    v = (state[:-1] != state[1:]) & base[:-1] & base[1:]
    np.savez_compressed(WORK / "fixed_edges.npz", h=h, v=v)
    for name, (a, scale) in arrays.items():
        print("MATCHED EVALUATION", name, flush=True)
        valid = np.isfinite(a).all(-1) & base
        record = dict(
            branch=name,
            finite_native=int(valid.sum()),
            missing_from_fixed_P172_support=int(np.sum(common & ~valid)),
            band_stats=[],
        )
        for band in [4, 7, 9]:
            signal = a[..., band] * scale
            z = signal[valid]
            record["band_stats"].append(
                dict(
                    wavelength=int(WAVES[band]),
                    distribution=dist(z),
                    negative=int(np.sum(z < 0)),
                    greater_than_one=int(np.sum(z > 1)),
                )
            )
            if band in [4, 7]:
                images[name + "_" + str(WAVES[band])] = signal[roi]
                transects[name + "_" + str(WAVES[band])] = signal[row, start:end]
                hi = h & valid[:, :-1] & valid[:, 1:]
                vi = v & valid[:-1] & valid[1:]
                jump = np.r_[
                    abs(np.diff(signal, axis=1))[hi], abs(np.diff(signal, axis=0))[vi]
                ]
                record.setdefault("fixed_boundary", {})[str(WAVES[band])] = dict(
                    edges=len(jump),
                    jump=dist(jump),
                    fixed_adjacent_jump=float(
                        abs(signal[row, left + 1] - signal[row, left])
                    ),
                )
        # Assignment-boundary diagnostics use the same edge locations for corrected/raw.
        boundary = maps[:, :-1, 2] != maps[:, 1:, 2]
        eligible = valid[:, :-1] & valid[:, 1:]
        for label, bound in [
            ("nearest_camera_boundary", boundary),
            ("same_nearest_camera", ~boundary),
        ]:
            selected = eligible & bound
            corrected_jump = abs(np.diff(a[..., 4] * scale, axis=1))[selected]
            raw_jump = abs(np.diff(raw[..., 4], axis=1))[selected]
            record[label] = dict(
                edges=int(selected.sum()),
                red_jump=dist(corrected_jump),
                matched_raw_jump=dist(raw_jump),
            )
        summaries.append(record)
        values = a[rr, cc].astype(float) * scale
        if not np.isfinite(values[keep]).all():
            scores.append(
                dict(
                    branch=name,
                    status="NOT_EVALUATED_UNCHANGED_MEMBERSHIP_UNAVAILABLE",
                    reason="Some established membership values unavailable; no changed support substituted",
                )
            )
            continue
        newrows = []
        for identity, g in index.groupby("GlobalID", sort=True):
            z = g.index.to_numpy()
            z = z[keep[z]]
            if not len(z):
                continue
            vv = values[z]
            mean = vv.mean(0)
            sd = vv.std(0, ddof=1)
            r = dict(
                branch=name,
                GlobalID=identity,
                cover_category=g.cover_category.iloc[0],
                n=len(z),
                mean_variance=float(np.mean(sd**2)),
                median_band_cv=float(np.median(sd / np.maximum(abs(mean), 1e-20))),
                within_angle_median=float(np.median(angle(vv, mean))),
                rededge_reversal=float(np.mean(vv[:, 7] < vv[:, 6])),
                NIR_red_ratio_median=float(
                    np.median(vv[:, 9] / np.maximum(vv[:, 4], 1e-20))
                ),
            )
            r.update({f"b{i + 1}": mean[i] for i in range(10)})
            r.update({f"median{i + 1}": np.median(vv[:, i]) for i in range(10)})
            r.update({f"q25_{i + 1}": np.quantile(vv[:, i], 0.25) for i in range(10)})
            r.update({f"q75_{i + 1}": np.quantile(vv[:, i], 0.75) for i in range(10)})
            newrows.append(r)
            if identity == fixed["exemplar_GlobalID"]:
                spectra.append(
                    dict(
                        branch=name,
                        GlobalID=identity,
                        mean_spectrum=mean,
                        within_std=sd,
                        n=len(vv),
                    )
                )
        rows.extend(newrows)
        g = pd.DataFrame(newrows)
        g = g[g.GlobalID.isin(ids)].sort_values("GlobalID").reset_index(drop=True)
        assert len(g) == 157
        x = g[[f"b{i + 1}" for i in range(10)]].to_numpy()
        y = g.cover_category.to_numpy()
        identity = g.GlobalID.to_numpy()
        result = evaluate_identifiability(
            x, y, groups=identity, folds=3, regularization=(1,), seed=20261103
        )
        pd.testing.assert_frame_equal(
            result["memberships"].astype(str), oldmembers.astype(str)
        )
        result["confusion"].to_csv(HERE / ("confusion_" + name + ".csv"))
        result["class_metrics"].to_csv(
            HERE / ("class_metrics_" + name + ".csv"), index=False
        )
        pred = result["predictions"].copy()
        pred["branch"] = name
        predictions.append(pred)
        scores.append(
            dict(
                branch=name,
                status="CONDITIONAL_EXPERIMENTAL_DIAGNOSTIC",
                **result["overall"],
                polygons=157,
                memberships=int(keep.sum()),
            )
        )
        separation = spectral_separability(
            x,
            y,
            WAVES,
            groups=identity,
            permutations=499,
            seed=20261103,
            integration_weights=np.ones(10),
        )["pairs"]
        separation["branch"] = name
        separations.append(separation)
    pred = pd.concat(predictions)
    pred.to_csv(HERE / "classification_predictions.csv", index=False)
    oldmembers.to_csv(HERE / "classification_memberships.csv", index=False)
    pd.DataFrame(rows).to_csv(HERE / "polygon_summaries.csv", index=False)
    pd.concat(separations).to_csv(HERE / "separability_pairs.csv", index=False)
    write("classification_summary.json", scores)
    paired = []
    baseline = pred[pred.branch == "clean_raw"]
    for name in pred.branch.unique():
        pair = baseline.merge(
            pred[pred.branch == name],
            on=["identity", "truth"],
            suffixes=("_raw", "_other"),
        )
        frame = pd.DataFrame(
            dict(
                GlobalID=pair.identity,
                truth=pair.truth,
                selected=(pair.prediction_other == pair.truth).astype(float),
                random=(pair.prediction_raw == pair.truth).astype(float),
            )
        )
        paired.append(
            dict(
                branch=name,
                **paired_identity_interval(frame, draws=1999, seed=20261103),
                changed_predictions=int(
                    (pair.prediction_raw != pair.prediction_other).sum()
                ),
            )
        )
    write("paired_gain.json", paired)
    write("matched_metrics.json", summaries)
    write("exemplar_spectra.json", spectra)
    # Predictions and reference from the actual accepted/rejected model, not inferred from displayed colors.
    import rasterio

    geom = {}
    for n in ["solar_az", "solar_zn"]:
        with rasterio.open(
            "/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_" + n + ".tif"
        ) as src:
            geom[n] = src.read(1)[roi]
    for s in statuses:
        name = s["branch"]
        model_file = HERE / (name + "_model.json")
        if not s["image_created"] or not model_file.exists():
            continue
        model = json.loads(model_file.read_text())
        X = np.load(
            "/private/tmp/goldhill-viewing-geometry-20261104/C_center_design.npy",
            mmap_mode="r",
        )[roi]
        for b in [4, 7]:
            beta = np.array([model[k][0][b] for k in ["iso", "vol", "geo"]])
            observed = X @ beta
            reference = float(np.array(model["reference_design"]) @ beta)
            factor = reference / observed
            images[name + "_prediction_" + str(WAVES[b])] = observed
            images[name + "_factor_" + str(WAVES[b])] = factor
            images[name + "_reference_" + str(WAVES[b])] = np.full(
                observed.shape, reference
            )
            transects[name + "_factor_" + str(WAVES[b])] = factor[
                row - y0, start - x0 : end - x0
            ]
            transects[name + "_prediction_" + str(WAVES[b])] = observed[
                row - y0, start - x0 : end - x0
            ]
            transects[name + "_reference_" + str(WAVES[b])] = np.full(
                end - start, reference
            )
    np.savez_compressed(WORK / "roi_displays.npz", **images)
    np.savez_compressed(WORK / "transects.npz", **transects)
    write(
        "evaluation_contract.json",
        dict(
            source_index=config["polygon_index"],
            same_memberships=int(keep.sum()),
            same_independent_identities=157,
            same_folds=True,
            seed=20261103,
            classifier_C=1,
            train_only_preprocessing=True,
            parameter_selection_using_PFT=False,
            fixed_regions=fixed,
            uncertainty="Class-stratified paired identity bootstrap of fixed OOF predictions; no training/site-year or nearby-polygon dependence uncertainty",
            supported_experimental_images=sum(s["image_created"] for s in statuses),
            membership_definition="Original source index unchanged; same joint valid subset used for all paired branches",
            source_memberships_before_unsupported_illumination=144406,
        ),
    )
    print("EVALUATION COMPLETE", flush=True)


if __name__ == "__main__":
    main()
