"""Independently reconstruct every plotted panel and numerical annotation."""

import json
import numpy as np
import pandas as pd
from .figure_data import BASE, REPO, P129, P130, sha, load_bundle
from .palette import CATEGORIES as CATS


def main():
    m = json.loads((BASE / "figure_data_manifest.json").read_text())
    d = load_bundle()
    for name, h in m["source_sha256"].items():
        assert sha(REPO / name) == h, name
    preserved = 0
    for parent in [P129, P130]:
        old = json.loads((parent / "final_manifest.json").read_text())
        for name, h in old["sha256"].items():
            assert sha(REPO / name) == h, name
        preserved += len(old["sha256"])
    original = pd.read_csv(
        REPO / "provenance/publication-figures/2026-10-14/atlas_summary.csv"
    )
    pd.testing.assert_frame_equal(original, d["A_category_spectra"])
    support = (
        pd.read_csv(P130 / "tables/category_support.csv")
        .set_index("researcher_category")
        .annual_rows
    )
    for c, g in original.groupby("cover_category"):
        assert (g.N == support.loc[c]).all()
    raw = pd.read_csv(P129 / "tables/cohort_wavelength_inference.csv")
    b = d["B_wavelength_effects"]
    for r in b.itertuples():
        g = raw[raw.pair.eq(r.pair) & raw.wavelength_nm.eq(r.wavelength_nm)]
        assert len(g) == 4
        assert abs(np.median(g.matched_effect) - r.effect) < 1e-12
        expected = (g.adjusted_p <= 0.05).all() and (
            g.matched_effect.gt(0).all() or g.matched_effect.lt(0).all()
        )
        assert bool(r.consistent_evidence) == expected
    allc = pd.read_csv(P130 / "tables/metrics.csv")
    oldc = pd.read_csv(P129 / "tables/complementary_feature_performance.csv")
    for r in d["C_recognition"].itertuples():
        if r.method == "Full spectrum":
            values = oldc[
                oldc.kind.eq(r.kind) & oldc.budget.astype(str).eq("360")
            ].balanced_accuracy
        else:
            values = allc[
                allc.kind.eq(r.kind)
                & allc.method.eq(r.method)
                & allc.budget.eq(r.budget)
            ].BA
        assert len(values) == (15 if r.method == "Random" else 3)
        np.testing.assert_allclose(
            [r.BA, r.observed_min, r.observed_max],
            [values.mean(), values.min(), values.max()],
            atol=1e-12,
        )
    cm = pd.read_csv(P129 / "tables/confusion_matrices.csv")
    cm = cm[cm.kind.eq("site") & cm.budget.astype(str).eq("360")]
    matrices = []
    for _, g in cm.groupby("fold"):
        a = (
            g.pivot(
                index="truth", columns="predicted", values="identity_weighted_count"
            )
            .loc[list(CATS), list(CATS)]
            .to_numpy()
        )
        matrices.append(a / a.sum(axis=1, keepdims=True))
    actual = (
        d["D_confusion"]
        .pivot(index="truth", columns="predicted", values="mean_fold_row_fraction")
        .loc[list(CATS), list(CATS)]
        .to_numpy()
    )
    np.testing.assert_allclose(actual, np.mean(matrices, axis=0), atol=1e-12)
    recall = (
        d["D_recall"]
        .pivot(index="researcher_category", columns="kind", values="recall")
        .loc[list(CATS)]
    )
    np.testing.assert_allclose(actual.diagonal(), recall.site, atol=1e-12)
    f = pd.read_csv(P130 / "tables/fraction_grid_calibration.csv")
    for r in d["E_calibration"].itertuples():
        g = f[
            f.kind.eq("site")
            & f.representation.eq("NEON")
            & f.method.eq(r.method)
            & f.researcher_category.eq(r.researcher_category)
            & f.true_fraction.eq(r.true_fraction)
        ]
        assert g.fold.nunique() == 3
        assert abs(g.prediction_mean.mean() - r.prediction_mean) < 1e-12
    scores = pd.read_csv(P130 / "tables/abundance_macro_scores.csv")
    matched = pd.read_csv(P130 / "tables/same_candidate_ridge.csv")
    for r in d["F_library_comparison"].itertuples():
        if r.method == "Ridge15":
            v = matched[
                matched.kind.eq(r.kind) & matched.representation.eq("NEON")
            ].RMSE
        else:
            method = {"MESMA15": "MESMA", "Ridge120": "Ridge"}.get(r.method, r.method)
            v = scores[
                scores.kind.eq(r.kind)
                & scores.method.eq(method)
                & scores.representation.eq("NEON")
            ].macro_RMSE
        assert len(v) == 3
        np.testing.assert_allclose(
            [r.RMSE, r.min, r.max], [v.mean(), v.min(), v.max()], atol=1e-12
        )
    amb = pd.read_csv(P129 / "tables/abundance_by_ambiguity.csv")
    for r in d["F_ambiguity"].itertuples():
        method = {"MESMA15": "MESMA", "Ridge120": "Ridge"}[r.method]
        v = amb[
            amb.kind.eq("site")
            & amb.representation.eq("NEON")
            & amb.method.eq(method)
            & amb.ambiguity.eq(r.ambiguity)
        ].fraction_RMSE
        assert len(v) == 3 and abs(v.mean() - r.fraction_RMSE) < 1e-12
    a = d["annotations"].set_index("annotation").value
    for kind in ["plant", "site"]:
        for method in ["Selected replay", "Random"]:
            v = (
                d["C_recognition"]
                .query("kind == @kind and method == @method and budget == 20")
                .BA.iloc[0]
            )
            assert abs(v - a[f"C_{kind}_{method}_20"]) < 1e-12
        v = (
            d["C_recognition"]
            .query('kind == @kind and method == "Full spectrum"')
            .BA.iloc[0]
        )
        assert abs(v - a[f"C_{kind}_full"]) < 1e-12
        q = d["F_library_comparison"].query("kind == @kind").set_index("method").RMSE
        assert (
            abs((1 - q.Ridge120 / q.MESMA15) - a[f"F_{kind}_relative_improvement"])
            < 1e-12
        )
        assert q.Ridge15 > q.MESMA15 and q.Ridge120 < q.MESMA15
    assert abs(recall.loc["Woody shrub", "site"] - a["D_Woody_shrub_site"]) < 1e-12
    result = {
        "status": "passed",
        "panels_independently_reconstructed": list("ABCDEF"),
        "B_pair_wavelength_cells": len(b),
        "annotation_values_verified": len(a),
        "preserved_preceding_owned_files": preserved,
        "no_new_fits": True,
        "no_raw_spectra_access": True,
        "canonical_source_files": len(m["source_sha256"]),
    }
    (BASE / "numerical_validation.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
