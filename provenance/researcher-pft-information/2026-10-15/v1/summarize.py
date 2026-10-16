"""Tidy researcher-only wavelength atlas and paired abundance uncertainty."""

import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from common import BASE, REPO, save, seed


def atlas():
    root = BASE / "tables"
    sw = pd.read_parquet(root / "single_wavelength_discrimination.parquet")
    neon = sw[sw.sensor.eq("NEON")]
    inference = pd.read_csv(root / "cohort_wavelength_inference.csv")
    keys = ["pair", "class_a", "class_b", "wavelength_nm"]
    result = neon[keys].drop_duplicates().set_index(keys)
    for kind, label in [
        ("plant", "new_polygon"),
        ("site", "held_site"),
        ("year", "held_year"),
    ]:
        use = neon[neon.kind.eq(kind)]
        g = use.groupby(keys)
        for field, name in [
            ("balanced_accuracy", "BA"),
            ("AUC", "AUC"),
            ("effect", "training_effect"),
            ("robust_effect", "training_annual_robust_effect"),
            ("sensitivity", "sensitivity"),
            ("specificity", "specificity"),
        ]:
            result[label + "_" + name] = g[field].mean()
        result[label + "_AUC_sd"] = g.AUC.std()
        result[label + "_BA_min"] = g.balanced_accuracy.min()
        result[label + "_BA_max"] = g.balanced_accuracy.max()
        result[label + "_BA_sd"] = g.balanced_accuracy.std()
    g = inference.groupby(keys)
    result["matched_effect_mean"] = g.matched_effect.mean()
    result["matched_effect_abs_max"] = g.matched_effect.apply(lambda x: abs(x).max())
    result["adjusted_p_min"] = g.adjusted_p.min()
    result["adjusted_p_max"] = g.adjusted_p.max()
    result["supported_cohorts"] = g.adjusted_p.apply(lambda x: (x <= 0.05).sum())
    result["effect_sign_consistency"] = g.matched_effect.apply(
        lambda x: max((x > 0).mean(), (x < 0).mean())
    )
    ranks = inference.assign(
        effect_rank=inference.groupby(
            ["pair", "site", "year"]
        ).matched_effect.transform(lambda x: abs(x).rank(pct=True))
    )
    result["effect_rank_sd"] = ranks.groupby(keys).effect_rank.std()
    paired = neon[neon.kind.eq("paired_year")].copy()
    paired["trainyear"] = paired.fold.str.extract(r"train(\d+)").astype(int)
    paired["targetyear"] = paired.fold.str.extract(r"target(\d+)").astype(int)
    p = (
        paired.groupby(keys + ["trainyear", "targetyear"])
        .balanced_accuracy.mean()
        .unstack("targetyear")
    )
    p["absolute_year_change"] = abs(p[2023] - p[2020])
    result["paired_year_max_absolute_BA_change"] = p.groupby(
        keys
    ).absolute_year_change.max()
    result["year_stability"] = np.clip(
        1 - result.paired_year_max_absolute_BA_change / 0.5, 0, 1
    )
    sel = pd.read_csv(root / "complementary_selection.csv")
    frequency = (
        sel[sel["rank"] <= 20].groupby("wavelength_nm").fold.nunique()
        / sel.fold.nunique()
    )
    result["global_multiclass_selection_frequency_k20"] = (
        result.index.get_level_values("wavelength_nm").map(frequency).fillna(0)
    )
    result["transfer_stability_score"] = (
        np.maximum(0, 2 * result.held_site_BA_min - 1) * result.effect_sign_consistency
    )
    result["consistently_informative"] = (
        result.held_site_BA_min >= 0.7
    ) & result.effect_sign_consistency.eq(1)
    result["site_specific"] = (result.held_site_BA_max >= 0.75) & (
        (result.held_site_BA_max - result.held_site_BA_min) >= 0.15
    )
    result["year_sensitive"] = result.paired_year_max_absolute_BA_change >= 0.10
    result["statistically_different_poor_predictor"] = (
        result.adjusted_p_min <= 0.05
    ) & (result.new_polygon_BA < 0.6)
    training_file = root / "training_wavelength_inference.parquet"
    if training_file.exists():
        training = pd.read_parquet(training_file)
        per_design = training.groupby(keys + ["fold"]).training_adjusted_p.min()
        result["training_adjusted_p_min_across_designs_descriptive"] = (
            per_design.groupby(keys).min()
        )
        result["training_supported_outer_designs"] = per_design.groupby(keys).apply(
            lambda x: int((x <= 0.05).sum())
        )
        result["training_inference_outer_designs"] = per_design.groupby(keys).size()
        result["training_evidence_scope"] = (
            "max-T+Bonferroni within each outer-training design; across-design minima descriptive"
        )
    result = result.reset_index()
    w = result.wavelength_nm
    result["spectral_region"] = np.select(
        [w < 700, w < 750, w < 1340, w < 1790],
        ["Visible", "Red edge", "NIR", "SWIR1"],
        default="SWIR2",
    )
    # Existing source-specific verified OLI centers/FWHM, not guessed archive labels.
    import sys

    sys.path.insert(0, str(BASE))
    from common import load

    _, _, waves, _ = load()
    centers = waves["OLI"]
    band_config = json.loads(
        (REPO / "src/spectralbridge/data/landsat_band_parameters.json").read_text()
    )["Landsat 8 OLI"]
    np.testing.assert_allclose(centers, band_config["wavelengths"], atol=0.5, rtol=0)
    centers = np.asarray(band_config["wavelengths"])
    fwhm = np.asarray(band_config["fwhms"])
    result["Landsat_centers_within_FWHM"] = result.wavelength_nm.map(
        lambda x: "|".join(
            f"{c:g}" for c, d in zip(centers, fwhm) if abs(x - c) <= d / 2
        )
    )
    result["Landsat_Gaussian_max_response"] = result.wavelength_nm.map(
        lambda x: float(np.max(np.exp(-4 * np.log(2) * ((x - centers) / fwhm) ** 2)))
    )
    result["Landsat_sampling_definition"] = (
        "centered configured FWHM interval; Gaussian tails extend beyond"
    )
    result["Landsat_samples_region"] = result.Landsat_centers_within_FWHM.ne("")
    save(result, "researcher_pft_information_atlas.csv")
    save(result, "researcher_pft_information_atlas.parquet")
    result.to_csv(BASE / "researcher_pft_information_atlas.csv", index=False)
    result.to_parquet(BASE / "researcher_pft_information_atlas.parquet", index=False)
    rankrows = []
    for pair, frame in inference.groupby("pair"):
        pivot = frame.pivot(
            index="wavelength_nm", columns=["site", "year"], values="matched_effect"
        ).abs()
        for i, a in enumerate(pivot):
            for b in list(pivot)[i + 1 :]:
                rankrows.append(
                    dict(
                        pair=pair,
                        domain_a=str(a),
                        domain_b=str(b),
                        rank_correlation=spearmanr(pivot[a], pivot[b]).statistic,
                    )
                )
    save(pd.DataFrame(rankrows), "domain_rank_consistency.csv")
    intervals = []
    for pair, frame in result.groupby("pair"):
        for flag in [
            "consistently_informative",
            "site_specific",
            "year_sensitive",
            "statistically_different_poor_predictor",
        ]:
            values = (
                frame[frame[flag]].sort_values("wavelength_nm").wavelength_nm.to_numpy()
            )
            if not len(values):
                continue
            split = np.flatnonzero(np.diff(values) > 8) + 1
            for segment in np.split(values, split):
                intervals.append(
                    dict(
                        pair=pair,
                        interpretation=flag,
                        start_nm=segment[0],
                        end_nm=segment[-1],
                        coordinates=len(segment),
                    )
                )
    save(pd.DataFrame(intervals), "spectral_intervals.csv")
    peaks = (
        result.sort_values(
            ["pair", "transfer_stability_score", "held_site_BA_min"],
            ascending=[True, False, False],
        )
        .groupby("pair", as_index=False)
        .head(1)
        .copy()
    )
    peaks["positive_transfer_score_observed"] = peaks.transfer_stability_score.gt(0)
    save(peaks, "pair_transfer_peaks.csv")
    # Prior year confusion is explicitly tagged reused, not pooled with the new rule.
    old = pd.read_csv(REPO / "artifacts/plant_spectral_atlas/analytics/confusion.csv")
    old = old[
        old.scheme.eq("researcher")
        & old.kind.eq("year")
        & old.model.eq("logistic")
        & old.probability.eq("raw")
        & old.representation.isin(["NEON_full", "OLI"])
    ]
    save(old.drop(columns="scheme"), "reused_researcher_year_confusion.csv")
    print("Atlas:", len(result), "pair/wavelength records")


def abundance():
    root = BASE / "tables"
    if not (root / "abundance_model_comparison.parquet").exists():
        return
    from finalize_exports import main as finalize_exports

    finalize_exports()
    from add_prior_control import main as add_prior_control

    add_prior_control()
    comparison = pd.read_parquet(root / "abundance_model_comparison.parquet")
    comparison.to_parquet(BASE / "abundance_model_comparison.parquet", index=False)
    b = pd.read_parquet(root / "abundance_bundle_scores.parquet")
    rows = []
    for key, g in b.groupby(["fold", "kind", "target", "representation"]):
        pivot = g.groupby(["bundle", "method"]).MSE.mean().unstack("method")
        if "MESMA" not in pivot:
            reference = (
                b[
                    b.fold.eq(key[0])
                    & b.target.eq(key[2])
                    & b.representation.eq("NEON")
                    & b.method.eq("MESMA")
                ]
                .groupby("bundle")
                .MSE.mean()
            )
            pivot["MESMA"] = reference.reindex(pivot.index)
        rng = np.random.default_rng(seed(str(key)))
        ix = rng.integers(0, len(pivot), (499, len(pivot)))
        boot = np.sqrt(pivot.to_numpy()[ix].mean(axis=1))
        center = np.sqrt(pivot.mean())
        ref = list(pivot).index("MESMA")
        for j, method in enumerate(pivot):
            lo, hi = np.quantile(boot[:, j], [0.025, 0.975])
            dlo, dhi = np.quantile(boot[:, j] - boot[:, ref], [0.025, 0.975])
            rows.append(
                dict(
                    fold=key[0],
                    kind=key[1],
                    target=key[2],
                    representation=key[3],
                    method=method,
                    macro_fraction_RMSE=center[method],
                    RMSE_low=lo,
                    RMSE_high=hi,
                    difference_from_MESMA=center[method] - center["MESMA"],
                    difference_low=dlo,
                    difference_high=dhi,
                    independent_test_bundles=len(pivot),
                    interval_scope="conditional_paired_bundle_percentile_not_multiplicity_adjusted",
                )
            )
    save(pd.DataFrame(rows), "abundance_paired_uncertainty.csv")
    print("Abundance:", len(comparison), "class/model/domain rows")


if __name__ == "__main__":
    atlas()
    abundance()
