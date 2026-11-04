# ruff: noqa: E402
"""Fixed-region artifact and matched-polygon metrics; unsupported branches stay absent."""

import itertools
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import (
    ROOT,
    WORK,
    PRIOR,
    WAVES,
    SCALE,
    write,
    dist,
    angle,
    load_module,
    LEGACY,
    MODEL,
)  # noqa:E402
from spectralbridge.library_analysis import (
    spectral_separability,
    evaluate_identifiability,
)  # noqa:E402
from spectralbridge.researcher_validation import paired_identity_interval  # noqa:E402


def main():
    config = json.loads((PRIOR / "branches.json").read_text())
    selection = json.loads(
        (
            ROOT / "provenance/brdf-artifact-anatomy/2026-11-03/selection.json"
        ).read_text()
    )
    masks = np.load(HERE / "filter_masks.npz")
    rawold = np.load(WORK / "old_candidate.npy", mmap_mode="r")
    raw = np.load(WORK / "clean_candidate.npy", mmap_mode="r")
    A = np.load(WORK / "A_historical_stored.npy", mmap_mode="r")
    B = np.load(WORK / "B_historical_stored.npy", mmap_mode="r")
    topo = np.load(
        "/private/tmp/goldhill-conditional-topographic-20261103/current.npy",
        mmap_mode="r",
    )
    scale = np.full(10, SCALE)
    scale[9] = (65535 - 174) / (32768 * 10000)
    offset = np.zeros(10)
    offset[9] = 174 / 32768
    arrays = {
        "raw_historical": (rawold, 1.0, 0.0),
        "raw_clean": (raw, 1.0, 0.0),
        "A_historical_BRDF": (A, scale, offset),
        "B_clean_historical_BRDF": (B, SCALE, 0.0),
        "topographic_only": (topo, 1.0, 0.0),
    }

    def band(name, b):
        a, m, o = arrays[name]
        return (
            a[..., b] * np.asarray(m).reshape(-1)[b if np.ndim(m) else 0]
            + np.asarray(o).reshape(-1)[b if np.ndim(o) else 0]
        )

    common = masks["source_valid"] & np.logical_and.reduce(
        [np.isfinite(a).all(-1) & (a != -9999).all(-1) for a, _, _ in arrays.values()]
    )
    artifact_common = (
        masks["source_valid"]
        & np.isfinite(A).all(-1)
        & np.isfinite(B).all(-1)
        & np.isfinite(raw).all(-1)
    )
    np.save(WORK / "common_spectral_support.npy", common)
    redbase = rawold[..., 4]
    factorA = np.divide(
        A[..., 4] * SCALE,
        redbase,
        out=np.full(common.shape, np.nan, np.float32),
        where=redbase > 0,
    )
    factorB = np.divide(
        B[..., 4] * SCALE,
        raw[..., 4],
        out=np.full(common.shape, np.nan, np.float32),
        where=raw[..., 4] > 0,
    )
    # Fixed historical boundary and unaffected regions come from P165, before this experiment.
    state = factorA > 1.01
    h = (
        (state[:, :-1] != state[:, 1:])
        & artifact_common[:, :-1]
        & artifact_common[:, 1:]
    )
    v = (state[:-1] != state[1:]) & artifact_common[:-1] & artifact_common[1:]
    y0, y1, x0, x1 = selection["roi_native_indices"]
    roi = np.s_[y0:y1, x0:x1]
    roi_mask = np.zeros(common.shape, bool)
    roi_mask[roi] = True
    inside = artifact_common & roi_mask & state
    outside = artifact_common & roi_mask & ~state
    rr0 = selection["main_transect_row"]
    cl = selection["main_transition_left_column"]
    spectra = []
    metrics = []
    display = {}
    stats = []
    coverage = []
    regions = []
    for name, (a, m, o) in arrays.items():
        print("FIXED-REGION diagnostics", name, flush=True)
        own = np.isfinite(a).all(-1) & (a != -9999).all(-1)
        if name == "raw_historical" or name == "A_historical_BRDF":
            own &= masks["historical_native"]
        elif name == "topographic_only":
            pass
        else:
            own &= masks["source_valid"]
        coverage.append(
            dict(
                branch=name,
                native=int(own.sum()),
                common=int(common.sum()),
                native_lost_from_clean=int((masks["source_valid"] & ~own).sum()),
            )
        )
        red = band(name, 4)
        jump = np.r_[abs(red[:, :-1] - red[:, 1:])[h], abs(red[:-1] - red[1:])[v]]
        f = np.divide(
            red,
            raw[..., 4]
            if name not in ["raw_historical", "A_historical_BRDF"]
            else rawold[..., 4],
            out=np.full(common.shape, np.nan, np.float32),
            where=(
                raw[..., 4]
                if name not in ["raw_historical", "A_historical_BRDF"]
                else rawold[..., 4]
            )
            > 0,
        )
        fjump = np.r_[abs(f[:, :-1] - f[:, 1:])[h], abs(f[:-1] - f[1:])[v]]
        # Spectral discontinuity on exactly the same fixed edges.
        hh = np.column_stack(np.where(h))
        vv = np.column_stack(np.where(v))
        take_h = hh[:: max(1, len(hh) // 20000)]
        take_v = vv[:: max(1, len(vv) // 20000)]

        def get(rows, cols):
            return a[rows, cols].astype(float) * m + o

        aa = np.vstack(
            [get(take_h[:, 0], take_h[:, 1]), get(take_v[:, 0], take_v[:, 1])]
        )
        bb = np.vstack(
            [get(take_h[:, 0], take_h[:, 1] + 1), get(take_v[:, 0] + 1, take_v[:, 1])]
        )
        metrics.append(
            dict(
                branch=name,
                fixed_edges=int(h.sum() + v.sum()),
                red_cross_boundary_difference=dist(jump),
                factor_cross_boundary_difference=dist(fjump),
                spectral_angle_cross_boundary=dist(angle(aa, bb)),
                native_red_range=dist(red[own]),
                red_factor=dist(f[own]),
                extreme_gain_over10=int((own & (f > 10)).sum()),
                extreme_gain_over1million=int((own & (f > 1e6)).sum()),
                affected_pixels=int((own & (f > 1.01)).sum()),
                fixed_left=red[rr0, cl],
                fixed_right=red[rr0, cl + 1],
                fixed_jump=abs(red[rr0, cl + 1] - red[rr0, cl]),
            )
        )
        for label, z in [("inside", inside), ("outside", outside)]:
            regions.append(
                dict(branch=name, region=label, red=dist(red[z]), factor=dist(f[z]))
            )
        for b, w in enumerate(WAVES):
            z = band(name, b)
            for support, msk in [("native", own), ("common", common)]:
                val = z[msk]
                stats.append(
                    dict(
                        branch=name,
                        wavelength_nm=w,
                        support=support,
                        **dist(val),
                        negative=int((val < 0).sum()),
                        above1=int((val > 1).sum()),
                    )
                )
        display[name + "_red"] = np.where(own[::6, ::6], red[::6, ::6], np.nan)
        display[name + "_zoom_red"] = np.where(artifact_common[roi], red[roi], np.nan)
        display[name + "_zoom_rgb"] = (
            a[roi][..., [4, 3, 1]] * np.asarray(m)[[4, 3, 1]] + np.asarray(o)[[4, 3, 1]]
            if np.ndim(m)
            else a[roi][..., [4, 3, 1]] * m + o
        )
        display[name + "_factor"] = f[::6, ::6]
        display[name + "_zoom_factor"] = f[roi]
        display[name + "_transect"] = red[rr0, 840:1120]
        for item in selection["pixels"]:
            spectrum = get(item["row"], item["column"])
            spectra.append(
                dict(
                    branch=name,
                    region=item["label"],
                    row=item["row"],
                    column=item["column"],
                    spectrum=spectrum.tolist(),
                )
            )
    write("artifact_metrics.json", metrics)
    write(
        "fixed_regions.json",
        dict(
            selection=selection,
            definition="P165native ROI/transect/inside/outside and raw historical factor sign boundary; never selected on new output appearance",
            horizontal_edges=int(h.sum()),
            vertical_edges=int(v.sum()),
            artifact_common_pixels=int(artifact_common.sum()),
            all_spectral_common=int(common.sum()),
        ),
    )
    write("region_statistics.json", regions)
    write("native_common_statistics.json", stats)
    write("representative_spectra.json", spectra)
    pd.DataFrame(coverage).to_csv(HERE / "coverage.csv", index=False)
    factor_agree = np.isfinite(factorA) & np.isfinite(factorB) & artifact_common
    write(
        "factorial_contrasts.json",
        dict(
            A_minus_B_factor=dist(abs(factorA[factor_agree] - factorB[factor_agree])),
            A_B_extreme_boundary_pattern_agreement=float(
                np.mean(
                    (factorA[factor_agree] > 1.01) == (factorB[factor_agree] > 1.01)
                )
            ),
            interpretation="Saved-model factors depend on historical geometry/predictions and visited NDVI strata. Source repair does not recover directional information. No percentage causal attribution to unidentifiable coefficients is inferred.",
            C_D_E="UNSUPPORTED; no corrected values or counterfactual quality scores fabricated",
            F="NOT_EVALUATED; applicable independent model/contributor geometry unavailable",
        ),
    )
    # Model predictions reconstructed with actual historical functions, for causal diagnostics only.
    old = load_module("p172_analyze_historical", LEGACY)
    model = json.loads(MODEL.read_text())
    import rasterio

    geometry = {}
    for n in ["solar_az", "solar_zn"]:
        with rasterio.open(
            f"/private/tmp/goldhill-end-to-end-20261103/ancillary/legacy_{n}.tif"
        ) as src:
            geometry[n] = np.deg2rad(src.read(1))
    sz = old._resolve_scene_solar_zenith(geometry["solar_zn"])
    zeros = np.zeros_like(sz)
    kv = old.calc_volume_kernel(
        geometry["solar_az"], sz, zeros, zeros, kernel_type="RossThick"
    )
    kg = old.calc_geom_kernel(
        geometry["solar_az"], sz, zeros, zeros, kernel_type="LiDenseR", b_r=10, h_b=2
    )
    rz = np.full_like(sz, np.deg2rad(45))
    rv = old.calc_volume_kernel(zeros, rz, zeros, zeros, kernel_type="RossThick")
    rg = old.calc_geom_kernel(
        zeros, rz, zeros, zeros, kernel_type="LiDenseR", b_r=10, h_b=2
    )
    prediction = []
    for b in [4, 7]:
        beta = [np.float32(model[k][0][b]) for k in ["iso", "vol", "geo"]]
        pred = beta[0] + beta[1] * kv + beta[2] * kg
        ref = beta[0] + beta[1] * rv + beta[2] * rg
        prediction.append(
            dict(
                wavelength_nm=int(WAVES[b]),
                native_candidate_pixels=int(artifact_common.sum()),
                nonpositive_prediction=int((artifact_common & (pred <= 0)).sum()),
                observed_prediction=dist(pred[artifact_common]),
                reference_prediction=dist(ref[artifact_common]),
                fixed_left=pred[rr0, cl],
                fixed_right=pred[rr0, cl + 1],
                beta=beta,
            )
        )
        display[f"prediction_{WAVES[b]}_zoom"] = pred[roi]
    write("historical_prediction_diagnostics.json", prediction)
    for name in [
        "historical_native",
        "source_valid",
        "legacy_estimated_no_background_mix",
        "geometry_numerical",
        "C_revised_prefit",
        "D_revised_prefit",
    ]:
        display["mask_" + name] = masks[name][::6, ::6]
    np.savez_compressed(HERE / "display_arrays.npz", **display)
    # All inferential units are independent polygon identities, not adjacent pixels.
    index = pd.read_parquet(config["polygon_index"])
    rr = index.row.to_numpy()
    cc = index.col.to_numpy()
    keep = common[rr, cc]
    rows = []
    within = []
    between = []
    classification = []
    predictions = []
    separations = []
    members = None
    ids = set(pd.read_csv(PRIOR / "independent_polygon_representatives.csv").GlobalID)
    for name, (a, m, o) in arrays.items():
        values = a[rr, cc].astype(float) * m + o
        for identity, g in index.groupby("GlobalID", sort=True):
            z = g.index.to_numpy()
            z = z[keep[z]]
            if not len(z):
                continue
            vv = values[z]
            mean = vv.mean(0)
            std = vv.std(0, ddof=1)
            rec = dict(
                branch=name,
                GlobalID=identity,
                cover_category=g.cover_category.iloc[0],
                n=len(z),
                median_band_cv=np.median(std / np.maximum(abs(mean), 1e-20)),
                mean_variance=np.mean(std**2),
                within_angle_median=np.median(angle(vv, mean)),
                rededge_reversal=float(np.mean(vv[:, 7] < vv[:, 6])),
                NIR_red_ratio_median=float(
                    np.median(vv[:, 9] / np.maximum(vv[:, 4], 1e-20))
                ),
            )
            rec.update({f"b{b + 1}": mean[b] for b in range(10)})
            rows.append(rec)
        g = pd.DataFrame(rows)
        g = (
            g[(g.branch == name) & g.GlobalID.isin(ids)]
            .sort_values("GlobalID")
            .reset_index(drop=True)
        )
        x = g[[f"b{i + 1}" for i in range(10)]].to_numpy()
        y = g.cover_category.to_numpy()
        ident = g.GlobalID.to_numpy()
        print("PACKAGE PFT diagnostic", name, len(g), flush=True)
        result = evaluate_identifiability(
            x, y, groups=ident, folds=3, regularization=(1,), seed=20261103
        )
        if members is None:
            members = result["memberships"]
            members.to_csv(HERE / "classification_memberships.csv", index=False)
        else:
            pd.testing.assert_frame_equal(members, result["memberships"])
        prediction = result["predictions"].copy()
        prediction["branch"] = name
        predictions.append(prediction)
        result["confusion"].to_csv(HERE / f"confusion_{name}.csv")
        result["class_metrics"].to_csv(HERE / f"class_metrics_{name}.csv", index=False)
        classification.append(
            dict(
                branch=name,
                **result["overall"],
                polygons=len(g),
                class_support=g.cover_category.value_counts().to_dict(),
                status="DIAGNOSTIC_ONLY; no physical correction approval",
            )
        )
        separation = spectral_separability(
            x,
            y,
            WAVES,
            groups=ident,
            permutations=499,
            seed=20261103,
            integration_weights=np.ones(10),
        )
        pair = separation["pairs"]
        pair["branch"] = name
        separations.append(pair)
        for label in sorted(set(y)):
            v = x[y == label]
            center = v.mean(0)
            within.append(
                dict(
                    branch=name,
                    label=label,
                    n=len(v),
                    mean_variance=float(v.var(0, ddof=1).mean()),
                    median_cv=float(
                        np.median(v.std(0, ddof=1) / np.maximum(abs(center), 1e-20))
                    ),
                    median_angle=float(np.median(angle(v, center))),
                )
            )
        for first, second in itertools.combinations(sorted(set(y)), 2):
            a1 = x[y == first]
            a2 = x[y == second]
            q1 = np.quantile(a1, [0.25, 0.75], axis=0)
            q2 = np.quantile(a2, [0.25, 0.75], axis=0)
            overlap = np.maximum(
                0, np.minimum(q1[1], q2[1]) - np.maximum(q1[0], q2[0])
            ) / np.maximum(np.maximum(q1[1], q2[1]) - np.minimum(q1[0], q2[0]), 1e-20)
            between.append(
                dict(
                    branch=name,
                    first=first,
                    second=second,
                    angle=float(angle(a1.mean(0), a2.mean(0))),
                    distance=float(np.linalg.norm(a1.mean(0) - a2.mean(0))),
                    IQR_overlap=float(np.mean(overlap)),
                )
            )
    pd.DataFrame(rows).to_csv(HERE / "polygon_summaries.csv", index=False)
    pd.DataFrame(within).to_csv(HERE / "within_class.csv", index=False)
    pd.DataFrame(between).to_csv(HERE / "between_class.csv", index=False)
    pd.concat(separations).to_csv(HERE / "separability_pairs.csv", index=False)
    preds = pd.concat(predictions)
    preds.to_csv(HERE / "classification_predictions.csv", index=False)
    write("classification_summary.json", classification)
    gains = []
    for name in arrays:
        p = preds[preds.branch == "raw_clean"].merge(
            preds[preds.branch == name],
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
                uncertainty="Paired class-stratified identity bootstrap of fixed OOF predictions; no model/site/year uncertainty or independent physical truth.",
            )
        )
    write("paired_gain.json", gains)
    write(
        "PFT_unsupported_branches.json",
        [
            dict(
                branch=b,
                status="UNSUPPORTED" if b != "F" else "NOT_EVALUATED",
                balanced_accuracy=None,
                reason="No supported corrected image; raw is not substituted as a successful BRDF output",
            )
            for b in ["C", "D", "E", "F"]
        ],
    )
    write(
        "analysis_summary.json",
        dict(
            common_pixels=int(common.sum()),
            common_polygon_memberships=int(keep.sum()),
            identities=157,
            classes={
                "Evergreen": 98,
                "Woody shrub": 29,
                "Herbaceous": 25,
                "Deciduous": 5,
            },
            no_pft_tuning=True,
            no_pixel_leakage=True,
            full_scene_displays_stride=6,
            roi_native_pixels=[y0, y1, x0, x1],
            hypothesis="HYPOTHETICAL_UNVERIFIED",
        ),
    )
    print("ANALYSIS COMPLETE", flush=True)


if __name__ == "__main__":
    main()
