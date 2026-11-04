"""Native/common-support diagnostics and label-blind paired polygon inference."""

import itertools
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from experiment import WORK, PRIOR, WAVES, write, distribution  # noqa: E402
from spectralbridge.library_analysis import (  # noqa: E402
    evaluate_identifiability,
    spectral_separability,
)  # noqa: E402
from spectralbridge.researcher_validation import paired_identity_interval  # noqa: E402
import json  # noqa: E402


def angle(x, y):
    den = np.linalg.norm(x, axis=-1) * np.linalg.norm(y, axis=-1)
    return np.rad2deg(
        np.arccos(np.clip(np.sum(x * y, axis=-1) / np.maximum(den, 1e-30), -1, 1))
    )


def corr(x, y):
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    return np.corrcoef(x, y)[0, 1]


def main():
    cfg = json.loads((HERE / "branches.json").read_text())
    index = pd.read_parquet(cfg["polygon_index"])
    rr = index.row.to_numpy()
    cc = index.col.to_numpy()
    common = np.load(WORK / "common.npy")
    raw = np.load(WORK / "raw.npy", mmap_mode="r")
    arrays = {k: np.load(v["path"], mmap_mode="r") for k, v in cfg["branches"].items()}
    import rasterio

    geom = {}
    for n in ["slope", "aspect", "solar_zn", "solar_az"]:
        with rasterio.open(
            f"/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_{n}.tif"
        ) as src:
            geom[n] = np.deg2rad(src.read(1))
    from spectralbridge.corrections import calc_cosine_i

    ci = calc_cosine_i(
        geom["solar_zn"], geom["solar_az"], geom["aspect"], geom["slope"]
    )
    idxcommon = common[rr, cc]
    rows = []
    scenestats = []
    dependence = []
    spatial = []
    cover = []
    pixelchanges = []
    rng = np.random.default_rng(20261103)
    coordinates = np.flatnonzero(common)
    sample = rng.choice(coordinates, min(100000, len(coordinates)), replace=False)
    base = raw.reshape(-1, 10)[sample].astype(float)
    for name, a in arrays.items():
        print("DIAGNOSTICS", name, flush=True)
        own = np.isfinite(a).all(axis=-1)
        vals = a[rr, cc].astype(float)
        basevals = raw[rr, cc].astype(float)
        for support, sel in [("native", own), ("common", common)]:
            for b, w in enumerate(WAVES):
                scenestats.append(
                    dict(
                        branch=name,
                        support=support,
                        wavelength_nm=int(w),
                        **distribution(a[..., b][sel]),
                    )
                )
        v = a.reshape(-1, 10)[sample].astype(float)
        xx = ci.ravel()[sample]
        pixelchanges.append(
            dict(
                branch=name,
                n=len(sample),
                angle=distribution(angle(v, base)),
                red_edge_705_717_change=distribution(
                    (v[:, 7] - v[:, 6]) - (base[:, 7] - base[:, 6])
                ),
                NIR_red_ratio=distribution(v[:, 9] / np.maximum(v[:, 4], 1e-20)),
                negative_rededge_fraction=float(np.mean(v[:, 7] < v[:, 6])),
            )
        )
        for b, w in enumerate(WAVES):
            for key, z in [
                ("illumination", ci.ravel()[sample]),
                ("slope", geom["slope"].ravel()[sample]),
                ("aspect_sin", np.sin(geom["aspect"].ravel()[sample])),
                ("aspect_cos", np.cos(geom["aspect"].ravel()[sample])),
            ]:
                dependence.append(
                    dict(
                        branch=name,
                        wavelength_nm=int(w),
                        variable=key,
                        scale="common_scene_sample",
                        n=len(sample),
                        pearson=corr(z, v[:, b]),
                        spearman=spearmanr(z, v[:, b]).statistic,
                    )
                )
        red = a[..., 4]
        h = common[:, 1:] & common[:, :-1]
        vert = common[1:] & common[:-1]
        jumps = np.r_[abs(red[:, 1:] - red[:, :-1])[h], abs(red[1:] - red[:-1])[vert]]
        spatial.append(dict(branch=name, adjacent_common_edges=distribution(jumps)))
        for identity, g in index.groupby("GlobalID", sort=True):
            z = g.index.to_numpy()
            keep = idxcommon[z]
            native = own[rr[z], cc[z]]
            cover.append(
                dict(
                    branch=name,
                    GlobalID=identity,
                    label=g.cover_category.iloc[0],
                    total=len(z),
                    native=int(native.sum()),
                    common=int(keep.sum()),
                )
            )
            for support, k in [("common", keep), ("native", native)]:
                vv = vals[z[k]]
                bb = basevals[z[k]]
                if not len(vv):
                    continue
                med = np.median(vv, axis=0)
                mean = vv.mean(0)
                std = vv.std(0, ddof=1) if len(vv) > 1 else np.zeros(10)
                item = dict(
                    branch=name,
                    support=support,
                    GlobalID=identity,
                    cover_category=g.cover_category.iloc[0],
                    n=len(vv),
                    median_band_cv=np.median(std / np.maximum(abs(mean), 1e-20)),
                    mean_variance=np.mean(std**2),
                    angle_to_raw_median=float(angle(med, np.median(bb, axis=0))),
                    within_angle_median=np.median(angle(vv, med)),
                    illumination_median=np.median(ci[rr[z[k]], cc[z[k]]]),
                    slope_median=np.median(geom["slope"][rr[z[k]], cc[z[k]]]),
                    x=float(g.x.mean()),
                    y=float(g.y.mean()),
                )
                item.update({f"b{b + 1}": mean[b] for b in range(10)})
                rows.append(item)
    table = pd.DataFrame(rows)
    table.to_csv(HERE / "polygon_summaries.csv", index=False)
    pd.DataFrame(cover).to_csv(HERE / "polygon_coverage.csv", index=False)
    pd.DataFrame(dependence).to_csv(HERE / "topographic_dependence.csv", index=False)
    write("scene_statistics.json", scenestats)
    write("spectral_change.json", pixelchanges)
    write("spatial_discontinuities.json", spatial)
    # Use the existing outcome-blind non-overlapping identities, then intersect across branches.
    ids = set(pd.read_csv(PRIOR / "independent_polygon_representatives.csv").GlobalID)
    groups = table[(table.support == "common") & table.GlobalID.isin(ids)]
    sets = [set(g.GlobalID) for _, g in groups.groupby("branch")]
    ids = set.intersection(*sets)
    groups = groups[groups.GlobalID.isin(ids)]
    summary = []
    predictions = []
    membership = None
    separation = []
    classstats = []
    pairs = []
    controlled = []
    for name, g in groups.groupby("branch", sort=True):
        g = g.sort_values("GlobalID").reset_index(drop=True)
        X = g[[f"b{b + 1}" for b in range(10)]].to_numpy(float)
        y = g.cover_category.to_numpy()
        ident = g.GlobalID.to_numpy()
        print("PACKAGE PFT", name, len(g), flush=True)
        result = evaluate_identifiability(
            X, y, groups=ident, folds=3, regularization=(1,), seed=20261103
        )
        if membership is None:
            membership = result["memberships"]
            membership.to_csv(HERE / "classification_memberships.csv", index=False)
        else:
            pd.testing.assert_frame_equal(membership, result["memberships"])
        pred = result["predictions"].copy()
        pred["branch"] = name
        predictions.append(pred)
        result["confusion"].to_csv(HERE / f"confusion_{name}.csv")
        result["class_metrics"].to_csv(HERE / f"class_metrics_{name}.csv", index=False)
        summary.append(
            dict(
                branch=name,
                **result["overall"],
                identities=len(g),
                class_support=g.cover_category.value_counts().to_dict(),
            )
        )
        sep = spectral_separability(
            X,
            y,
            WAVES,
            groups=ident,
            permutations=499,
            seed=20261103,
            integration_weights=np.ones(10),
        )
        frame = sep["pairs"].copy()
        frame["branch"] = name
        separation.append(frame)
        sep["wavelengths"].to_csv(
            HERE / f"separability_wavelengths_{name}.csv", index=False
        )
        for label, sub in g.groupby("cover_category"):
            xx = sub[[f"b{b + 1}" for b in range(10)]].to_numpy(float)
            centroid = xx.mean(0)
            classstats.append(
                dict(
                    branch=name,
                    label=label,
                    n=len(sub),
                    mean_variance=float(np.var(xx, axis=0, ddof=1).mean()),
                    median_band_cv=float(
                        np.median(xx.std(0, ddof=1) / np.maximum(abs(centroid), 1e-20))
                    ),
                    median_angle=float(np.median(angle(xx, centroid))),
                )
            )
        for left_label, r in itertools.combinations(sorted(set(y)), 2):
            a = X[y == left_label]
            b = X[y == r]
            q1 = np.quantile(a, [0.25, 0.75], axis=0)
            q2 = np.quantile(b, [0.25, 0.75], axis=0)
            pairs.append(
                dict(
                    branch=name,
                    first=left_label,
                    second=r,
                    angle=float(angle(a.mean(0), b.mean(0))),
                    distance=float(np.linalg.norm(a.mean(0) - b.mean(0))),
                    IQR_overlap=float(
                        np.mean(
                            np.maximum(
                                0, np.minimum(q1[1], q2[1]) - np.maximum(q1[0], q2[0])
                            )
                            / np.maximum(
                                np.maximum(q1[1], q2[1]) - np.minimum(q1[0], q2[0]),
                                1e-20,
                            )
                        )
                    ),
                )
            )
        # Partial association across independent polygons controlling class + x/y plane.
        design = np.column_stack(
            [
                np.ones(len(g)),
                pd.get_dummies(
                    g.cover_category, drop_first=True, dtype=float
                ).to_numpy(),
                (g.x - g.x.mean()) / g.x.std(),
                (g.y - g.y.mean()) / g.y.std(),
            ]
        )
        illumination = g.illumination_median.to_numpy()
        resx = (
            illumination - design @ np.linalg.lstsq(design, illumination, rcond=None)[0]
        )
        for b, w in enumerate(WAVES):
            resy = X[:, b] - design @ np.linalg.lstsq(design, X[:, b], rcond=None)[0]
            controlled.append(
                dict(
                    branch=name,
                    wavelength_nm=int(w),
                    partial_illumination_pearson=corr(resx, resy),
                    control="class and linear spatial coordinates; descriptive, not independent validation",
                )
            )
    allpred = pd.concat(predictions, ignore_index=True)
    allpred.to_csv(HERE / "classification_predictions.csv", index=False)
    gains = []
    rawpred = allpred[allpred.branch == "raw"]
    for name in arrays:
        p = rawpred.merge(
            allpred[allpred.branch == name],
            on=["identity", "truth"],
            suffixes=("_raw", "_other"),
        )
        frame = pd.DataFrame(
            dict(
                GlobalID=p.identity,
                truth=p.truth,
                selected=(p.prediction_other == p.truth).astype(float),
                random=(p.prediction_raw == p.truth).astype(float),
            )
        )
        gains.append(
            dict(
                branch=name,
                **paired_identity_interval(frame, draws=1999, seed=20261103),
                changed_predictions=int((p.prediction_raw != p.prediction_other).sum()),
                interpretation="Class-stratified paired polygon bootstrap of fixed out-of-fold predictions; not training-set, site or coefficient uncertainty. Exploratory multiple branches.",
            )
        )
    write("classification_summary.json", summary)
    write("paired_gain.json", gains)
    pd.concat(separation, ignore_index=True).to_csv(
        HERE / "separability_pairs.csv", index=False
    )
    pd.DataFrame(classstats).to_csv(HERE / "within_class.csv", index=False)
    pd.DataFrame(pairs).to_csv(HERE / "between_class.csv", index=False)
    pd.DataFrame(controlled).to_csv(HERE / "class_spatial_control.csv", index=False)
    # Native-support historical/raw benchmark on the original common historical support.
    baseline = []
    for name in ["raw", "historical"]:
        g = table[
            (table.branch == name)
            & (table.support == "native")
            & table.GlobalID.isin(ids)
        ].sort_values("GlobalID")
        result = evaluate_identifiability(
            g[[f"b{b + 1}" for b in range(10)]].to_numpy(),
            g.cover_category.to_numpy(),
            groups=g.GlobalID.to_numpy(),
            folds=3,
            regularization=(1,),
            seed=20261103,
        )
        baseline.append(
            dict(
                branch=name,
                **result["overall"],
                warning="Native support differs; contrast with common-support results, not causal correction gain",
            )
        )
    write("native_classification.json", baseline)
    write(
        "analysis_summary.json",
        dict(
            common_pixels=cfg["common_pixels"],
            polygon_identities=len(ids),
            original_polygon_identities=int(index.GlobalID.nunique()),
            original_class_support=index.groupby("GlobalID")
            .cover_category.first()
            .value_counts()
            .to_dict(),
            common_class_support=groups[groups.branch == "raw"]
            .cover_category.value_counts()
            .to_dict(),
            common_polygon_memberships=int(idxcommon.sum()),
            source="Researcher labels unchanged; pixel-center package index reused; no pixel-level classifier; fixed training-only scaling; correction coefficients for eligible/robust/stabilized exclude all evaluation polygons+2m. Historical/current scene fits are transductive diagnostic baselines.",
        ),
    )
    print("ANALYSIS COMPLETE", flush=True)


if __name__ == "__main__":
    main()
