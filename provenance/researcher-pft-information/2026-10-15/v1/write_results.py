"""Researcher-only scientific narrative derived from the saved result tables."""

import json
import pandas as pd
from common import BASE, save


def main():
    t = BASE / "tables"
    a = pd.read_parquet(BASE / "researcher_pft_information_atlas.parquet")
    features = pd.read_csv(t / "complementary_feature_performance.csv")
    comp = pd.read_parquet(BASE / "abundance_model_comparison.parquet")
    comp = comp.assign(MSE=comp.RMSE**2)
    macro = (
        comp.groupby(["fold", "kind", "target", "method", "representation"])
        .MSE.mean()
        .pow(0.5)
        .rename("RMSE")
        .reset_index()
    )
    scores = macro.groupby(["kind", "method", "representation"]).RMSE.mean()
    acc = features.groupby(["kind", "budget"]).balanced_accuracy.mean()
    rates = pd.read_csv(t / "class_specific_transfer.csv")
    rates = (
        rates[rates.budget.eq("360")]
        .groupby(["kind", "researcher_category"])
        .mean(numeric_only=True)
    )
    peaks = pd.read_csv(t / "pair_transfer_peaks.csv").set_index("pair")
    budgets = pd.read_csv(t / "inner_selected_parsimonious_budget.csv")
    pairs = [
        "Deciduous / Evergreen",
        "Deciduous / Woody shrub",
        "Evergreen / Herbaceous",
        "Evergreen / Woody shrub",
        "Herbaceous / Woody shrub",
    ]
    lines = [
        "# Researcher-category spectral information and synthetic abundance",
        "",
        "Only the five recorded cover_category classes are primary. The earlier taxonomic grouping and reports are historical, preserved and excluded from these conclusions.",
        "",
        "## Main answer",
        "",
        f"The five researcher categories contain useful spectral signals, but their predictive difficulty is uneven. Full-NEON nested logistic balanced accuracy is {acc['plant', '360']:.1%} on new polygons and {acc['site', '360']:.1%} on held sites; synthetic OLI gives {acc['plant', 'OLI']:.1%} and {acc['site', 'OLI']:.1%}. All scores are conditional on these labelled source populations, not field deployment guarantees.",
        "",
        f"Supervised regression improves the controlled abundance benchmark. Ridge reduces mean-fold class-balanced NEON fraction RMSE from MESMA {scores['plant', 'MESMA', 'NEON']:.3f} to {scores['plant', 'Ridge', 'NEON']:.3f} on new-polygon parents, and from {scores['site', 'MESMA', 'NEON']:.3f} to {scores['site', 'Ridge', 'NEON']:.3f} on held sites. This is known synthetic mixing-weight recovery, not independently validated field cover.",
        "",
        f"The proper-training-mean fraction control (no spectra) has RMSE {scores['plant', 'Training prior', 'NEON']:.3f}. Ridge improves on it for new-parent and held-site targets, but its global-year mean RMSE {scores['year', 'Ridge', 'NEON']:.3f} does not improve over the prior control {scores['year', 'Training prior', 'NEON']:.3f}. MESMA is worse than that control in the primary familiar/held-site benchmark. Gains over MESMA alone are therefore not enough to establish transferable spectral skill.",
        "",
        "## Where is the information?",
        "",
        "The atlas has 3,600 pair/wavelength records: every one of ten category pairs at 360 supported NEON coordinates. Full-cohort max-T/Bonferroni evidence, training-only effects, held-out prediction and stability remain separate fields. OLI locations use exact configured centers/FWHM after verifying rounded export labels. Peaks below are descriptive outer-evaluation summaries, not operational feature selections.",
        "",
        "| Researcher-category pair | Descriptive best worst-site wavelength | Minimum held-site BA |",
        "|---|---:|---:|",
    ]
    for pair in pairs:
        row = peaks.loc[pair]
        lines.append(
            f"| {pair} | {row.wavelength_nm:g} nm | {row.held_site_BA_min:.1%} |"
        )
    lines += [
        "",
        "Herbaceous versus Woody shrub is the clearest weak single-coordinate contrast; its worst-site score stays below chance even at its best observed worst-site coordinate. This is evidence about the prespecified univariate mean-based rule, not proof that no nonlinear information exists. Evergreen/Herbaceous and several vegetation-versus-background contrasts are stronger. The complete atlas and spectral_intervals.csv retain every coordinate and overlapping review tag; some maxima occur near segment boundaries and are not universal recommended bands.",
        "",
        "## Which categories drive recognition errors?",
        "",
        "| Researcher category | New-polygon recall | Held-site recall | Held-site precision |",
        "|---|---:|---:|---:|",
    ]
    for c in [
        "Deciduous",
        "Evergreen",
        "Herbaceous",
        "Non-vegetated & dead",
        "Woody shrub",
    ]:
        lines.append(
            f"| {c} | {rates.loc[('plant', c), 'recall']:.1%} | {rates.loc[('site', c), 'recall']:.1%} | {rates.loc[('site', c), 'precision']:.1%} |"
        )
    lines += [
        "",
        "Evergreen and Non-vegetated & dead are recognized more consistently than Woody shrub. A useful background label is still not a pure physical material. Every confusion cell and per-class FPR/FNR is saved; temporal whole-spectrum class rates/confusions reuse the prior validated researcher-only logistic baseline and are explicitly marked reused, rather than silently pooled with the new identity-weighted model.",
        "",
        "## Redundancy and complementarity",
        "",
        f"Nested complementary-coordinate mean new-polygon BA is {acc['plant', '1']:.1%} with one coordinate, {acc['plant', '7']:.1%} with seven, {acc['plant', '20']:.1%} with twenty, {acc['plant', '50']:.1%} with fifty and {acc['plant', '360']:.1%} with the full grid. Held-site values are {acc['site', '7']:.1%}, {acc['site', '20']:.1%}, {acc['site', '50']:.1%} and {acc['site', '360']:.1%}, respectively. The training-only two-percentage-point parsimony rule chooses {int(budgets.selected_budget.min())}-{int(budgets.selected_budget.max())} coordinates across folds. This does not prove an optimal sensor or fixed universal saturation point. Correlation clusters and orthogonal residual gains distinguish repeated from complementary training information.",
        "",
        "## Abundance improvements, failures and what they mean",
        "",
        "All primary methods share 120 proper-training parents, 40 tuning parents and up to60 held-out parents per experiment. Each five-parent bundle supplies170 dependent pair/triple mixtures. Twelve parent bundles, not2,040 independent spectra, define a full test. Ten training experiments yield twelve target sets, including both image years for the paired temporal directions. All model tuning/preprocessing occurs in the appropriate parent role. Fractions are nonnegative and sum to one after explicit projection.",
        "",
        f"Ridge also outperforms the primary full-NEON gradient booster on average here: {scores['plant', 'Ridge', 'NEON']:.3f} versus {scores['plant', 'Gradient boosting', 'NEON']:.3f} on new parents, and {scores['site', 'Ridge', 'NEON']:.3f} versus {scores['site', 'Gradient boosting', 'NEON']:.3f} on held sites. These are fixed outer comparisons, not a multiplicity-corrected universal ranking. Ridge OLI RMSE is {scores['plant', 'Ridge', 'OLI']:.3f}/{scores['site', 'Ridge', 'OLI']:.3f}; first-derivative ridge is {scores['plant', 'Ridge', 'derivative1']:.3f}/{scores['site', 'Ridge', 'derivative1']:.3f}, and second-derivative ridge is {scores['plant', 'Ridge', 'derivative2']:.3f}/{scores['site', 'Ridge', 'derivative2']:.3f} (new-parent/held-site). Derivatives do not improve this benchmark; shape/PCA/selected-coordinate sensitivities remain fully reported.",
        "",
        "The two-stage procedure trades fewer false detections for more missed low fractions; it does not dominate fraction RMSE. For example, Evergreen new-parent false detections at zero fall from ridge26.4% to two-stage10.9%, while low-fraction false negatives rise from61.4% to82.0% at the common .10 fraction cutoff. These conditional source-specific observations are not universal detection limits.",
        "",
        "Paired bundle intervals and error-by-fraction/ambiguity tables retain negative results. Ridge improves average held-site error in the high-ambiguity stratum, but not every method/stratum; the moderate stratum can favor MESMA. A learned prior can improve expected fraction error without eliminating another feasible spectral explanation. No reduction of mathematical non-identifiability is established.",
        "",
        "## What currently limits abundance?",
        "",
        "- Model choice matters: supervised projected regressions substantially improve known-weight recovery under the common design.",
        "- Spectral representation matters: OLI loses some recognition and fraction information; derivatives are not a remedy here.",
        "- Within-class variability/library mismatch matters: known-parent oracle fraction error is near machine precision, while class-reference models are much worse. This is a positive control, not a deployable model.",
        "- Between-class/candidate ambiguity persists: multiple near-fitting class combinations remain, and improvements are not uniform across ambiguity strata.",
        "- Geographic/temporal shift matters: held-site and paired cross-year conditions differ from familiar-parent tests. Three sites and retrospective labels cannot isolate their causes.",
        "- Independent physical truth is the deployment gate: category annotations do not certify pure parents or field fractional cover. No current experiment causally apportions all failure among these factors.",
        "",
        "## What to do next",
        "",
        "Retain valid repeated observations and metadata; keep complete identity histories in validation. Recover original units/physical coordinates/purity first. Collect independent co-located complete fractions, true absences and low positives; cross contemporary annotations with sites and years. Replicate actual sensor/footprint comparisons. More generated mixtures or another complex model cannot replace independent biological and physical truth.",
    ]
    (BASE / "RESULTS.md").write_text("\n".join(lines) + "\n")
    (BASE / "FINAL_SCIENTIFIC_SYNTHESIS.md").write_text("\n".join(lines) + "\n")
    limitations = """# Limitations and inconclusive experiments

- Results concern sampled researcher-labelled polygon footprints. A GlobalID is
  not verified material purity or one biological individual. Later annotations
  are reused across image years; there is no independent annual biological truth.
- Only three sites and incompletely crossed years are observed. Conditional ID
  or bundle intervals do not define a population of new regions or propagate
  all annotation/model-selection uncertainty.
- Single-coordinate discrimination is a prespecified linear mean-based rule;
  its failure is not a theorem about every possible nonlinear classifier.
  Max-T evidence is observational and needs exchangeable acquisition blocks.
- Full-cohort inferential effects and training-only predictive effects describe
  different populations/designs; they are never merged into one significance score.
- Forward orthogonal selection is greedy and training-fit-based. Correlation can
  reflect class composition; neither it nor selected frequencies proves causal
  biochemical importance or a globally optimal sensor.
- Synthetic fractions are algebraic parent weights. Twelve test bundles share
  many fraction levels internally; they do not yield2,040 independent biological
  replicates. Fixed120-parent training budget limits claims about model capacity.
- Supervised gains can exploit the finite mixture prior. Held sites/years test
  some shift, but no unknown physical material or independent field fractions
  validate general abundance recovery. Better mean error does not erase ambiguity.
- Presence thresholds trade false detection against false absence. Two-stage
  regression, shape, PCA and derivatives do not consistently dominate the simple
  full-spectrum ridge model. No calibrated field abundance intervals are claimed.
- Continuum removal/log-ratio zero replacement and neural networks were not
  scientifically justified here. This is explicit non-adoption, not a failed test.
- Library absolute scaling and MicaSense physical coordinates remain unresolved.
  Synthetic OLI is not an independent Landsat observation or30m spatial mixing.
- Early inference and older dual-label final/lab reports remain historical.
  The current primary biological results contain only the five researcher classes.
"""
    limitations += "\nThis is a structured reanalysis of extensively explored data. Grouped/nested evaluation prevents within-experiment leakage but does not replace independent external confirmation or erase all prior design adaptation to this library.\n"
    (BASE / "LIMITATIONS.md").write_text(limitations)
    (BASE / "NEXT_DATA_NEEDED.md").write_text(
        "# Next data needed\n\nVerify units, physical band headers and polygon purity. Obtain independent complete fractions, true absences and low positive cover at matched footprints; independently update dated labels across crossed site/year sampling. Expand co-located independent sensor/field observations. Preserve all valid repeated observations with annotation and acquisition dates; keep histories grouped and weights explicit. Prioritize this truth over additional algorithm searches.\n"
    )
    readiness = pd.DataFrame(
        [
            dict(
                use="Researcher-category spectral differences",
                status="conditional evidence",
                scope="Forty acquisition-matched contrasts; observational exchangeability",
            ),
            dict(
                use="Single-wavelength researcher-category recognition",
                status="pair and domain dependent",
                scope="Every coordinate evaluated; weak contrasts remain",
            ),
            dict(
                use="Multivariate researcher-category recognition",
                status="scientifically promising",
                scope="Nested grouped and held-site validation; retrospective labels",
            ),
            dict(
                use="Synthetic researcher-category fraction recovery",
                status="improved by supervised regression",
                scope="Fixed parent-disjoint synthetic benchmark; not field truth",
            ),
            dict(
                use="Unique physical mixture inversion",
                status="not established",
                scope="Candidate-library spectral alternatives persist",
            ),
            dict(
                use="Operational field fractional cover",
                status="not ready",
                scope="Independent purity/fraction truth and domain replication required",
            ),
        ]
    )
    save(readiness, "FINAL_READINESS_MATRIX.csv")
    (BASE / "FINAL_ANALYSIS_AUDIT.md").write_text(
        (BASE / "LABEL_SYSTEM_AUDIT.md").read_text()
        + "\nThe new work reuses the forty researcher-category permutation ensembles and historical researcher-only temporal class metrics. New work comprises20 paired/domain single-coordinate evaluation cases, six nested multivariate feature-budget cases and ten parent-disjoint abundance training experiments with twelve target sets. No historical woody grouping or physical-material proxy is an active biological target.\n"
    )
    source = {
        "classification": {f"{k[0]}_{k[1]}": v for k, v in acc.items()},
        "synthetic_scores": {"|".join(k): float(v) for k, v in scores.items()},
        "counts": {
            "identities": 3639,
            "annual_observations": 4807,
            "atlas_rows": len(a),
            "class_pairs": 10,
            "NEON_coordinates": 360,
            "synthetic_OLI_channels": 7,
        },
    }
    (BASE / "report_numbers.json").write_text(json.dumps(source, indent=2) + "\n")
    print("Wrote researcher-only scientific conclusions and readiness.")


if __name__ == "__main__":
    main()
