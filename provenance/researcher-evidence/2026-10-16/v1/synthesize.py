"""Auditable foundation and three-question numerical synthesis; no model fitting."""

from pathlib import Path
import hashlib
import json
import sys
from itertools import combinations
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import spearmanr

BASE = Path(__file__).resolve().parent
REPO = BASE.parents[3]
OLD = REPO / "provenance/researcher-pft-information/2026-10-15/v1"
T = BASE / "tables"
T.mkdir(exist_ok=True)
O = OLD / "tables"
sys.path.insert(0, str(BASE))
from run_controls import load_data, CATS  # noqa: E402
from spectralbridge.researcher_validation import paired_identity_interval  # noqa: E402


def save(f, name):
    f.to_csv(T / name, index=False)


def main():
    t, arrays, waves, identity = load_data()
    oldmanifest = json.loads((OLD / "final_manifest.json").read_text())
    for name, h in oldmanifest["sha256"].items():
        assert hashlib.sha256((REPO / name).read_bytes()).hexdigest() == h, name
    foundation = {
        **identity,
        "prior_sealed_files_verified": len(oldmanifest["sha256"]),
        "polygon_GlobalIDs": int(t.GlobalID.nunique()),
        "polygon_year_spectra": len(t),
        "repeated_IDs": int(t.groupby("GlobalID").size().gt(1).sum()),
        "NEON_coordinates": len(waves["NEON"]),
        "OLI_channels": len(waves["OLI"]),
        "missing_compact_labels": int(t.label.isna().sum()),
        "missing_compact_spectral_values": 0,
        "units_status": "NOT TESTABLE: stored numerical units; absolute reflectance scale unresolved",
        "annotation_status": "2023/2024 retrospective category annotations reused across acquisition years",
    }
    duplicate_rows = []
    for rep, X in arrays.items():
        _, inv, counts = np.unique(X, axis=0, return_inverse=True, return_counts=True)
        d = pd.DataFrame({"fingerprint": inv, "GlobalID": t.GlobalID})
        cross = d.groupby("fingerprint").GlobalID.nunique()
        duplicate_rows.append(
            dict(
                representation=rep,
                annual_rows=len(X),
                unique_spectra=len(counts),
                duplicate_annual_rows_beyond_first=int((counts - 1).sum()),
                spectral_groups_across_distinct_IDs=int((cross > 1).sum()),
            )
        )
    save(pd.DataFrame(duplicate_rows), "duplicate_spectra.csv")
    support = (
        t.groupby(["site", "year", "label"])
        .agg(GlobalIDs=("GlobalID", "nunique"), annual_rows=("GlobalID", "size"))
        .reset_index()
        .rename(columns={"label": "researcher_category"})
    )
    save(support, "site_year_category_support.csv")
    class_support = (
        t.groupby("label")
        .agg(GlobalIDs=("GlobalID", "nunique"), annual_rows=("GlobalID", "size"))
        .reset_index()
        .rename(columns={"label": "researcher_category"})
    )
    class_support["identity_fraction"] = class_support.GlobalIDs / t.GlobalID.nunique()
    save(class_support, "category_support.csv")
    # One bounded streaming pass: validity counts only, no pixel cache.
    source = REPO / "Aug_2026_all_polygons_merged_pixel_extraction.parquet"
    pf = pq.ParquetFile(source)
    cols = [c for c in pf.schema_arrow.names if c.startswith("corr_")]
    counts = []
    row_valid_counts = []
    nonfinite = np.zeros(len(cols), int)
    negative = np.zeros(len(cols), int)
    invalidids = 0
    invalidlabels = 0
    for batch in pf.iter_batches(
        batch_size=4096, columns=["GlobalID", "cover_category"] + cols
    ):
        f = batch.to_pandas()
        X = f[cols].to_numpy(float)
        row_valid_counts.extend(np.isfinite(X).sum(axis=1).tolist())
        nonfinite += (~np.isfinite(X)).sum(axis=0)
        negative += ((X < 0) & np.isfinite(X)).sum(axis=0)
        invalidids += int(f.GlobalID.isna().sum())
        invalidlabels += int((~f.cover_category.isin(CATS)).sum())
    save(
        pd.DataFrame(
            {
                "source_column": cols,
                "nonfinite_pixel_values": nonfinite,
                "finite_negative_pixel_values": negative,
                "source_pixel_rows": pf.metadata.num_rows,
            }
        ),
        "source_corrected_validity.csv",
    )
    foundation.update(
        source_pixel_rows=pf.metadata.num_rows,
        source_corrected_coordinates=len(cols),
        source_missing_ID_rows=invalidids,
        source_unrecognized_category_rows=invalidlabels,
        source_corrected_nonfinite_values=int(nonfinite.sum()),
        source_valid_corrected_coordinates_per_pixel_min=int(np.min(row_valid_counts)),
        source_valid_corrected_coordinates_per_pixel_median=float(np.median(row_valid_counts)),
        source_valid_corrected_coordinates_per_pixel_max=int(np.max(row_valid_counts)),
        source_missingness_interpretation="Union of native wavelength columns across source products; structural null padding is not missingness on the harmonized analytical grid",
        source_finite_negative_values=int(negative.sum()),
    )
    (BASE / "foundation.json").write_text(json.dumps(foundation, indent=2) + "\n")
    # Difference evidence, deliberately separate from predictive metrics.
    whole = pd.read_csv(O / "reused_researcher_sensor_effect_retention.csv")
    keep = [
        "test_id",
        "site",
        "year",
        "contrast",
        "a",
        "b",
        "n_a",
        "n_b",
        "NEON_effect",
        "OLI_effect",
        "OLI_NEON_ratio",
        "ratio_lo",
        "ratio_hi",
        "NEON_p_holm",
        "OLI_p_holm",
        "NEON_supported",
        "OLI_supported",
        "ratio_status",
        "OLI_width_effect",
        "OLI_width_supported",
    ]
    save(whole[keep], "whole_spectrum_separability.csv")
    w = pd.read_csv(O / "cohort_wavelength_inference.csv")
    w["region"] = np.select(
        [
            w.wavelength_nm < 700,
            w.wavelength_nm < 750,
            w.wavelength_nm < 1340,
            w.wavelength_nm < 1790,
        ],
        ["Visible", "Red edge", "NIR", "SWIR1"],
        default="SWIR2",
    )
    w["absolute_effect"] = w.matched_effect.abs()
    w["joint_supported"] = w.adjusted_p <= 0.05
    grouped = w.groupby(["pair", "wavelength_nm"])
    stability = grouped.agg(
        min_abs_effect=("absolute_effect", "min"),
        max_abs_effect=("absolute_effect", "max"),
        mean_abs_effect=("absolute_effect", "mean"),
        sd_abs_effect=("absolute_effect", "std"),
        supported_cohorts=("joint_supported", "sum"),
        cohorts=("matched_effect", "size"),
    ).reset_index()
    signs = grouped.matched_effect.apply(
        lambda x: max((x > 0).mean(), (x < 0).mean())
    ).reset_index(name="sign_consistency")
    stability = stability.merge(signs)
    weak = w.loc[
        grouped.absolute_effect.idxmin(), ["pair", "wavelength_nm", "site", "year"]
    ].rename(columns={"site": "weakest_effect_site", "year": "weakest_effect_year"})
    stability = stability.merge(weak)
    save(stability, "wavelength_effect_stability.csv")
    regions = (
        w.groupby(["pair", "site", "year", "region"])
        .agg(
            coordinates=("wavelength_nm", "size"),
            supported_coordinates=("joint_supported", "sum"),
            mean_abs_effect=("absolute_effect", "mean"),
            max_abs_effect=("absolute_effect", "max"),
        )
        .reset_index()
    )
    save(regions, "region_separability.csv")
    pair = (
        whole.groupby("contrast")
        .agg(
            cohorts=("test_id", "size"),
            minimum_class_a_IDs=("n_a", "min"),
            minimum_class_b_IDs=("n_b", "min"),
            min_NEON_effect=("NEON_effect", "min"),
            max_NEON_effect=("NEON_effect", "max"),
            largest_adjusted_NEON_p=("NEON_p_holm", "max"),
            significant_NEON_cohorts=("NEON_supported", "sum"),
            min_OLI_retention=("OLI_NEON_ratio", "min"),
            max_OLI_retention=("OLI_NEON_ratio", "max"),
        )
        .reset_index()
    )
    save(pair, "pair_support_and_evidence.csv")
    # Null envelopes are not effect confidence intervals.
    null_rows = []
    checkpoints = (
        REPO / "artifacts/plant_spectral_atlas/researcher_pft_statistics/checkpoints"
    )
    for row in whole.itertuples():
        with np.load(checkpoints / (row.test_id.removeprefix("researcher_category__") + ".npz")) as a:
            for j, ww in enumerate(
                w[
                    w.pair.eq(row.contrast) & w.site.eq(row.site) & w.year.eq(row.year)
                ].wavelength_nm
            ):
                null_rows.append(
                    dict(
                        pair=row.contrast,
                        site=row.site,
                        year=row.year,
                        wavelength_nm=ww,
                        beta=float(a["curves"][0, j]),
                        null_standard_error=float(a["se"][j]),
                        scale=float(a["scale"][j]),
                        uncertainty_scope="exchangeability-null standard error, not effect confidence interval",
                    )
                )
    save(pd.DataFrame(null_rows), "wavelength_null_uncertainty.csv")
    # Existing five-class single-coordinate rule, all domains, not best-coordinate tuning.
    single = pd.read_csv(O / "single_wavelength_class_recall.csv")
    save(
        single.groupby(["fold", "kind", "sensor", "wavelength_nm"])
        .recall.mean()
        .reset_index(name="balanced_accuracy"),
        "single_coordinate_five_class.csv",
    )
    sw = pd.read_parquet(O / "single_wavelength_discrimination.parquet")
    save(
        sw.groupby(["pair", "kind", "sensor", "wavelength_nm"])
        .agg(
            mean_BA=("balanced_accuracy", "mean"),
            min_BA=("balanced_accuracy", "min"),
            max_BA=("balanced_accuracy", "max"),
            mean_AUC=("AUC", "mean"),
            folds=("fold", "nunique"),
        )
        .reset_index(),
        "pairwise_single_coordinate_summary.csv",
    )
    # New matched controls, paired at ID level; no seed chosen by outer performance.
    metrics = pd.read_csv(T / "metrics.csv")
    correct = pd.read_parquet(T / "identity_correctness.parquet")
    comparisons = []
    for (fold, kind, budget), g in correct[
        correct.method.isin(["Random", "Selected replay"])
    ].groupby(["fold", "kind", "budget"]):
        a = g[g.method.eq("Selected replay")][["GlobalID", "truth", "correct"]].rename(
            columns={"correct": "selected"}
        )
        b = (
            g[g.method.eq("Random")]
            .groupby(["GlobalID", "truth"])
            .correct.mean()
            .reset_index(name="random")
        )
        joined = a.merge(b, on=["GlobalID", "truth"], validate="one_to_one")
        comparisons.append(
            dict(
                fold=fold,
                kind=kind,
                budget=budget,
                **paired_identity_interval(joined, seed=20261016),
                random_replicates=5,
                interval_scope="conditional whole-ID bootstrap; exploratory pointwise; no joint multiplicity claim",
            )
        )
    save(pd.DataFrame(comparisons), "selected_minus_random.csv")
    # Correlation/redundancy on outer-training spectra only; all pair correlations within subset.
    redundancy = []
    for fold in metrics[metrics.kind.isin(["plant", "site"])].fold.unique():
        corr = np.load(O / f"training_correlation_{fold}.npz")["correlation"]
        features = pd.read_csv(BASE / "checkpoints" / fold / "features.csv")
        for variant, g in features.groupby("variant"):
            for budget in [7, 20, 50, 100]:
                ix = g.column.to_numpy()[:budget]
                if len(ix) != budget:
                    continue
                vals = np.abs(corr[np.ix_(ix, ix)])[np.triu_indices(budget, 1)]
                redundancy.append(
                    dict(
                        fold=fold,
                        variant=variant,
                        budget=budget,
                        median_abs_correlation=np.median(vals),
                        fraction_abs_r_above_09=np.mean(vals >= 0.9),
                    )
                )
    save(pd.DataFrame(redundancy), "subset_redundancy.csv")
    # Recalculate all primary model/domain values and conditional paired comparisons.
    allm = pd.read_csv(O / "abundance_model_comparison.csv")
    primary = allm[allm.representation.isin(["NEON", "OLI"])]
    macro = (
        primary.groupby(["fold", "kind", "target", "method", "representation"])
        .RMSE.apply(lambda x: np.sqrt(np.mean(x * x)))
        .reset_index(name="macro_RMSE")
    )
    save(macro, "abundance_macro_scores.csv")
    save(
        macro.groupby(["kind", "method", "representation"])
        .macro_RMSE.agg(["mean", "min", "max", "count"])
        .reset_index(),
        "abundance_domain_summary.csv",
    )
    bundles = pd.read_parquet(O / "abundance_bundle_scores.parquet")
    paired = []
    for (fold, kind, target, rep), g in bundles[
        bundles.representation.isin(["NEON", "OLI"])
    ].groupby(["fold", "kind", "target", "representation"]):
        pivot = g.groupby(["bundle", "method"]).MSE.mean().unstack("method")
        rng = np.random.default_rng(20261016)
        draw = rng.integers(0, len(pivot), (999, len(pivot)))
        for reference in ["MESMA", "Training prior"]:
            if reference not in pivot:
                continue
            for method in pivot:
                d = np.sqrt(pivot[method].to_numpy()[draw].mean(axis=1)) - np.sqrt(
                    pivot[reference].to_numpy()[draw].mean(axis=1)
                )
                m = np.sqrt(pivot[method].mean())
                r = np.sqrt(pivot[reference].mean())
                lo, hi = np.quantile(d, [0.025, 0.975])
                paired.append(
                    dict(
                        fold=fold,
                        kind=kind,
                        target=target,
                        representation=rep,
                        method=method,
                        reference=reference,
                        RMSE=m,
                        reference_RMSE=r,
                        difference=m - r,
                        difference_low=lo,
                        difference_high=hi,
                        relative_reduction=1 - m / r,
                        independent_bundles=len(pivot),
                        scope="conditional paired whole-bundle bootstrap; pointwise not joint",
                    )
                )
    save(pd.DataFrame(paired), "abundance_paired_vs_baselines.csv")
    # Class links: ambiguity burden for mixtures containing the class, not class-specific range.
    index = pd.read_csv(O / "abundance_case_index.csv")
    classrows = []
    for row in index[
        index.method.eq("MESMA") & index.representation.eq("NEON")
    ].itertuples():
        truth = pd.read_parquet(REPO / row.truth)
        archive = (REPO / row.predictions).with_name(row.target + "_MESMA.npz")
        ambiguity = np.load(archive)["ambiguity_range"]
        for c in CATS:
            present = truth[c].to_numpy() > 0
            classrows.append(
                dict(
                    fold=row.fold,
                    kind=row.kind,
                    target=row.target,
                    researcher_category=c,
                    high_ambiguity_fraction_when_present=float(
                        np.mean(ambiguity[present] >= 0.3)
                    ),
                    mean_mixture_max_range_when_present=float(
                        np.mean(ambiguity[present])
                    ),
                    scope="maximum class range of mixture containing category, not category-specific feasible range",
                )
            )
    burden = pd.DataFrame(classrows)
    save(burden, "class_ambiguity_burden.csv")
    recall = pd.read_csv(O / "class_specific_transfer.csv")
    recall = recall[recall.budget.astype(str).eq("360")]
    links = []
    for kind in ["plant", "site"]:
        rr = recall[recall.kind.eq(kind)].groupby("researcher_category").recall.mean()
        aa = (
            primary[
                primary.kind.eq(kind)
                & primary.method.eq("Ridge")
                & primary.representation.eq("NEON")
            ]
            .groupby("researcher_category")[["RMSE", "FPR", "low_FNR"]]
            .mean()
        )
        bb = (
            burden[burden.kind.eq(kind)]
            .groupby("researcher_category")
            .high_ambiguity_fraction_when_present.mean()
        )
        f = aa.join(rr).join(bb).reset_index()
        f["kind"] = kind
        links.append(f)
    links = pd.concat(links, ignore_index=True)
    save(links, "class_recognition_abundance_links.csv")
    relationship = []
    for kind, g in links.groupby("kind"):
        for metric in [
            "RMSE",
            "FPR",
            "low_FNR",
            "high_ambiguity_fraction_when_present",
        ]:
            relationship.append(
                dict(
                    kind=kind,
                    metric=metric,
                    Spearman_rho=spearmanr(g.recall, g[metric]).statistic,
                    categories=5,
                    interpretation="descriptive five-category relationship; no population p-value or causal claim",
                )
            )
    save(pd.DataFrame(relationship), "class_link_correlations.csv")
    # Every canonical truth and prediction checked, not just aggregate copied metrics.
    constraints = []
    for row in index.itertuples():
        truth = pd.read_parquet(REPO / row.truth)
        pred = pd.read_parquet(REPO / row.predictions)
        if all(c in pred for c in CATS):
            P = pred[CATS].to_numpy()
        else:
            P = pred[["pred_" + c for c in CATS]].to_numpy()
        Y = truth[CATS].to_numpy()
        assert len(P) == len(Y) and np.allclose(Y.sum(axis=1), 1) and np.all(Y >= 0)
        assert np.allclose(P.sum(axis=1), 1, atol=1e-9) and np.all(P >= -1e-10)
        expected = (
            allm[
                (allm.fold.eq(row.fold))
                & (allm.target.eq(row.target))
                & (allm.method.eq(row.method))
                & (allm.representation.eq(row.representation))
            ]
            .set_index("researcher_category")
            .loc[CATS]
            .RMSE.to_numpy()
        )
        np.testing.assert_allclose(
            np.sqrt(np.mean((P - Y) ** 2, axis=0)), expected, rtol=1e-9, atol=1e-10
        )
        constraints.append(
            dict(
                fold=row.fold,
                target=row.target,
                method=row.method,
                representation=row.representation,
                rows=len(Y),
                max_sum_error=float(abs(P.sum(axis=1) - 1).max()),
                min_fraction=float(P.min()),
                status="PASS",
            )
        )
    save(pd.DataFrame(constraints), "canonical_prediction_checks.csv")
    (BASE / "synthesis_validation.json").write_text(
        json.dumps(
            {
                "status": "passed",
                "prior_sealed_files_unchanged": len(oldmanifest["sha256"]),
                "canonical_abundance_cases_verified": len(constraints),
                "all_ten_pairs": len(pair) == 10,
                "foundation": foundation,
            },
            indent=2,
        )
        + "\n"
    )
    print("Foundation and three-question synthesis complete.")


if __name__ == "__main__":
    main()
