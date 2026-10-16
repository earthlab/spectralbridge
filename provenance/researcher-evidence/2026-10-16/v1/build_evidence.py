"""Explicit requirement checklists, adverse explanations and evidence ladder."""

import json
import numpy as np
import pandas as pd
from run_controls import BASE, PRIOR, REPO

T = BASE / "tables"
O = PRIOR / "tables"


def main():
    rows = []

    def add(
        section,
        requirement,
        status,
        result,
        evidence,
        limit="Conditional on supplied observations; no independent field truth.",
    ):
        rows.append(
            dict(
                section=section,
                requirement=requirement,
                status=status,
                result=result,
                evidence=evidence,
                remaining_limitation=limit,
            )
        )

    foundation = json.loads((BASE / "foundation.json").read_text())
    add(
        "FOUNDATION",
        "GlobalID biological sampling unit",
        "PASS",
        f"{foundation['polygon_GlobalIDs']:,} identities; {foundation['polygon_year_spectra']:,} annual spectra; {foundation['repeated_IDs']:,} repeated IDs",
        "foundation.json",
        "A polygon footprint is not verified individual-plant or material purity.",
    )
    for requirement, result, evidence in [
        (
            "Category sample sizes and imbalance",
            "All five categories counted by distinct GlobalID, not pixel rows",
            "tables/category_support.csv",
        ),
        (
            "Site/year coverage",
            "Four observed site/year cells, not balanced crossed coverage",
            "tables/site_year_category_support.csv",
        ),
        (
            "Repeated identities and split grouping",
            "All acquisitions of each target ID excluded from model training",
            "control_validation.json",
        ),
        (
            "Spectral coordinate count",
            "360 usable NEON coordinates; seven synthetic OLI channels",
            "foundation.json",
        ),
        (
            "Atmospheric gaps",
            "Existing masked grid retained; no gap interpolation in analysis or plotting",
            "prior:tables/spectral_intervals.csv",
        ),
        (
            "Synthetic OLI construction",
            "Shared corrected-source convolution; exact configured centers/FWHM, rounded export labels",
            "prior:METHODS.md",
        ),
        (
            "Annotation dates documented",
            "2023/2024 annotations reused across imagery years",
            "provenance/scientific-closure/2026-10-15/tables/annotation_year_audit.csv",
        ),
        (
            "Missing source values",
            "Each pixel has 426 finite native coordinates; union schema has structural null padding; compact grid finite",
            "foundation.json; tables/source_corrected_validity.csv",
        ),
        (
            "Duplicate annual spectra",
            "No exact duplicate NEON or OLI annual vectors across or within identities",
            "tables/duplicate_spectra.csv",
        ),
        (
            "Exact source-pixel leakage",
            "Prior metadata audit: no shared source pixels across distinct GlobalIDs",
            "provenance/scientific-closure/2026-10-15/manifests/metadata_audit.json",
        ),
        (
            "Training-only preprocessing",
            "Scalers/PCA/selectors fitted within appropriate training roles",
            "control_validation.json; prior:numerical_validation.json",
        ),
        (
            "Nested feature and model selection",
            "Matching grouped inner folds; C chosen only by inner scores",
            "control_validation.json",
        ),
        (
            "Mixture parent membership",
            "Proper/tuning/test parents separated; same target mixtures for all primary models",
            "prior:tables/abundance_parent_memberships.csv; tables/canonical_prediction_checks.csv",
        ),
        (
            "Dependent mixtures",
            "Bootstrap resamples whole parent bundles, never independent synthetic rows",
            "tables/abundance_paired_vs_baselines.csv",
        ),
        (
            "Historical labels excluded",
            "Only source cover_category enters new models; prior grouping history preserved",
            "input_identity.json; run_controls.py",
        ),
    ]:
        add("FOUNDATION", requirement, "PASS", result, evidence)
    for requirement, result in [
        (
            "Absolute reflectance scaling and physical units",
            "Stored scale unresolved; no guessed rescaling or physical cross-sensor unit claim.",
        ),
        (
            "Independent annual biological truth",
            "Retrospective category labels cannot validate annual ecological change.",
        ),
        (
            "Independent field fractions and purity",
            "No contemporaneous fractional-cover or pure-material truth supplied.",
        ),
        (
            "Spatially independent regions beyond sampled sites",
            "Three sites do not establish new-region geographic generality; spatial autocorrelation remains.",
        ),
    ]:
        add(
            "FOUNDATION",
            requirement,
            "NOT TESTABLE",
            result,
            "foundation.json; prior:LIMITATIONS.md",
            result,
        )
    sep = [
        (
            "All ten category contrasts",
            "40 supported acquisition-history contrasts, all ten pairs in four cohorts",
            "tables/pair_support_and_evidence.csv",
        ),
        (
            "Whole-spectrum difference",
            "Effect magnitudes and Holm-adjusted permutation evidence reported separately",
            "tables/whole_spectrum_separability.csv",
        ),
        (
            "Wavelength-level difference",
            "All 360 retained coordinates; signed/absolute effects, support and null uncertainty",
            "tables/wavelength_effect_stability.csv; tables/wavelength_null_uncertainty.csv",
        ),
        (
            "Multiple comparison control",
            "Synchronized max-T over coordinates; Bonferroni over 40 contrasts. Whole-spectrum Holm family separate.",
            "prior:METHODS.md",
        ),
        (
            "Effects distinct from p-values",
            "Numerical effect and adjusted evidence shown on separate axes/tables",
            "tables/whole_spectrum_separability.csv",
        ),
        (
            "Site effects",
            "Every observed site remains visible; weakest effect domain recorded",
            "tables/wavelength_effect_stability.csv",
        ),
        (
            "Year effects",
            "NIWO 2020/2023 effects retained separately",
            "tables/region_separability.csv",
        ),
        (
            "Atmospheric gaps",
            "Heatmaps split into disconnected intervals; no bridge lines",
            "build_figures.py",
        ),
        (
            "Redundancy and regions",
            "Training correlation and equal-size subset controls; region effects separated",
            "tables/subset_redundancy.csv; tables/region_separability.csv",
        ),
        (
            "NEON-to-OLI effect retention",
            "Shared-source effect ratios and uncertainty, not empirical Landsat validation",
            "tables/whole_spectrum_separability.csv",
        ),
        (
            "Unsupported domains marked",
            "No WREF/YELL 2020, missing atmospheric intervals excluded",
            "tables/site_year_category_support.csv",
        ),
    ]
    for a, b, c in sep:
        add("SEPARABILITY", a, "PASS", b, c)
    ids = [
        (
            "Unseen identities",
            "Outer target GlobalIDs absent from all model training",
            "control_validation.json",
        ),
        (
            "Nested feature selection",
            "Prior selector trained fresh within inner folds; target-free random paths",
            "prior:numerical_validation.json; control_validation.json",
        ),
        (
            "Nested tuning",
            "C chosen on exact group-aware inner folds",
            "control_validation.json",
        ),
        (
            "Entire held sites unseen",
            "Three site holds; poor sites not averaged away in saved scores",
            "tables/metrics.csv",
        ),
        (
            "All five classes evaluated",
            "Recall, precision, FPR/FNR and confusion counts per class",
            "tables/rates.csv; prior:tables/class_specific_transfer.csv",
        ),
        (
            "Confusion matrices",
            "Five-class confusion matrices for each full/PCA/random/selected case",
            "tables/confusions.csv; prior:tables/confusion_matrices.csv",
        ),
        (
            "Pairwise versus five-class distinguished",
            "Binary LDA versus balanced-prior five-class nearest-mean rule",
            "tables/pairwise_single_coordinate_summary.csv; tables/single_coordinate_five_class.csv",
        ),
        (
            "Single-coordinate versus full spectrum",
            "Separate prediction tasks, 50% versus 20% chance BA",
            "tables/single_coordinate_five_class.csv; tables/metrics.csv",
        ),
        (
            "Complementary information",
            "Nested selector feature-budget curve and increments",
            "prior:tables/complementary_feature_performance.csv",
        ),
        (
            "Equal-size random controls",
            "Five fixed random paths, same inner folds/C grid; no winning seed selected",
            "tables/selected_minus_random.csv",
        ),
        (
            "Redundancy tested",
            "Within-subset correlations, random/PCA/full-spectrum sensitivities",
            "tables/subset_redundancy.csv; tables/metrics.csv",
        ),
        (
            "Geographic transfer",
            "All site folds plus class-specific failures",
            "tables/metrics.csv; prior:tables/class_specific_transfer.csv",
        ),
        (
            "Temporal transfer",
            "Consistent nested full NEON/OLI; paired identity targets both years",
            "tables/metrics.csv",
        ),
        (
            "NEON versus OLI predictive loss",
            "Same new-polygon/site outer framework; temporal losses also retained",
            "prior:tables/complementary_feature_performance.csv; tables/metrics.csv",
        ),
    ]
    for a, b, c in ids:
        add("IDENTIFIABILITY", a, "PASS", b, c)
    ab = [
        (
            "Mixture parent separation",
            "Distinct proper/tuning/target parents; no biological replication from synthetic rows",
            "prior:tables/abundance_parent_memberships.csv",
        ),
        (
            "Grouped dependent mixtures",
            "Whole-bundle paired uncertainty",
            "tables/abundance_paired_vs_baselines.csv",
        ),
        (
            "Known-parent oracle",
            "Near machine precision verifies ideal linear solver, not candidate adequacy",
            "prior:tables/oracle_solver_controls.csv",
        ),
        (
            "Identical targets",
            "384 canonical prediction cases checked against exact saved truth",
            "tables/canonical_prediction_checks.csv",
        ),
        (
            "Nonnegative sum-one fractions",
            "Constraints independently verified; raw projection sensitivity retained",
            "tables/canonical_prediction_checks.csv; prior:tables/raw_prediction_constraint_diagnostics.csv",
        ),
        (
            "Ridge beats MESMA in primary benchmark",
            "Yes on mean new-parent/held-site NEON under 120-parent ridge versus 15-candidate MESMA",
            "tables/abundance_domain_summary.csv",
        ),
        (
            "Paired uncertainty",
            "Conditional bootstrap differences versus MESMA AND training prior",
            "tables/abundance_paired_vs_baselines.csv",
        ),
        (
            "Class-specific errors",
            "RMSE, MAE, bias, slope, false detection and low-fraction miss per class",
            "prior:tables/abundance_model_comparison.csv",
        ),
        (
            "True-fraction calibration",
            "Full supported grid including zero/pure endpoints; shrinkage explicit",
            "prior:tables/abundance_by_true_fraction.csv",
        ),
        (
            "False detections",
            "At true zero, projected fraction >= .10 declared comparison rule",
            "prior:tables/abundance_by_true_fraction.csv",
        ),
        (
            "Low-fraction misses",
            "Conditional detection-versus-fraction and low_FNR",
            "prior:tables/abundance_model_comparison.csv",
        ),
        (
            "Detection versus quantification",
            "Stage A presence separate from final constrained fraction errors",
            "prior:tables/two_stage_presence_metrics.csv",
        ),
        (
            "Ambiguity calculated",
            "Every primary target assigned common NEON candidate-library max fraction-range stratum",
            "prior:tables/abundance_by_ambiguity.csv",
        ),
        (
            "RMSE versus non-unique fits",
            "Better expected fraction accuracy coexists with alternative candidate compositions",
            "prior:tables/abundance_by_ambiguity.csv",
        ),
        (
            "Held-site abundance",
            "All three holds, each method against prior",
            "tables/abundance_paired_vs_baselines.csv",
        ),
        (
            "Temporal abundance",
            "Global-year and complete-pair target comparisons; site and retrospective truth caveats",
            "tables/abundance_domain_summary.csv",
        ),
        (
            "NEON/OLI/transforms",
            "Existing full/OLI/shape/PCA/selected/derivative results reused without sweep",
            "prior:tables/abundance_model_comparison.csv",
        ),
        (
            "Synthetic versus field",
            "Synthetic algebraic fractions explicitly distinct from field fractional cover",
            "DESIGN.md",
        ),
    ]
    for a, b, c in ab:
        add("ABUNDANCE", a, "PASS", b, c)
    add(
        "ABUNDANCE",
        "Ridge beats prior across every domain",
        "FAIL",
        "Global-year NEON mean ridge error exceeds no-spectrum prior; not transferable skill in every domain",
        "tables/abundance_domain_summary.csv",
        "Domain failures retained; no universal abundance claim.",
    )
    add(
        "ABUNDANCE",
        "Ridge superiority after equal retained parent capacity",
        "FAIL",
        "15-parent NEON ridge loses its original advantage over 15-candidate MESMA",
        "tables/same_candidate_ridge.csv",
        "Control changes training diversity/bundle count; does not identify a single causal mechanism.",
    )
    add(
        "ABUNDANCE",
        "Unique physical inversion",
        "NOT TESTABLE",
        "Candidate-library alternatives disprove unique candidate solutions for many targets; exhaustive physical uniqueness unavailable",
        "prior:tables/abundance_by_ambiguity.csv",
        "No pure-material/field fraction truth; tolerance is an algorithmic diagnostic.",
    )
    table = pd.DataFrame(rows)
    table.insert(0, "requirement_id", [f"V{i:02}" for i in range(1, len(table) + 1)])
    table.to_csv(T / "design_validation.csv", index=False)
    # A hostile review must include failures rather than merely procedural checks.
    adversarial = []

    def adverse(claim, mode, test, result, status, limitation, evidence):
        adversarial.append(
            dict(
                claim=claim,
                potential_failure_mode=mode,
                test_performed=test,
                result=result,
                status=status,
                remaining_limitation=limitation,
                evidence=evidence,
            )
        )

    adverse(
        "Separability",
        "Pixel/wavelength pseudoreplication",
        "Identity summaries, acquisition-history blocks and whole-curve shuffles",
        "3,639 IDs; 360 coordinates are not replicates",
        "PASS",
        "Labels exchangeable within declared blocks is an assumption",
        "foundation.json; prior:METHODS.md",
    )
    adverse(
        "Separability",
        "Multiple testing and correlated wavelengths",
        "Synchronized max-T then 40-contrast Bonferroni; whole-spectrum Holm",
        "All ten pairs supported in four observed cohorts",
        "PASS",
        "Not an effect-size confidence band or independent replication",
        "tables/pair_support_and_evidence.csv",
    )
    adverse(
        "Separability",
        "One site/year drives the effect",
        "Retain all cohort effects/signs/ranks/weakest domain",
        "Magnitude and direction heterogeneity retained",
        "PASS",
        "Only NIWO repeats in time; not broad regional sampling",
        "tables/wavelength_effect_stability.csv; prior:tables/domain_rank_consistency.csv",
    )
    adverse(
        "Separability",
        "Physical scaling or annotation errors",
        "Inspect source metadata/validity and annotation dates; reuse shape sensitivity",
        "Relative numerical evidence available; absolute units/annual truth unresolved",
        "NOT TESTABLE",
        "No independent unit/purity certification",
        "foundation.json; prior:LIMITATIONS.md",
    )
    adverse(
        "Identifiability",
        "Repeated-identity or exact-copy leakage",
        "Replay memberships and exact duplicate annual vectors",
        "No shared target IDs; no duplicate annual vectors",
        "PASS",
        "Spatial autocorrelation can remain between distinct polygons",
        "control_validation.json; tables/duplicate_spectra.csv",
    )
    adverse(
        "Identifiability",
        "Feature/tuning leakage",
        "Recreate original inner group folds, random paths and chosen C; replay all predictions",
        "352 models / 364 target evaluations reconstructed",
        "PASS",
        "Dataset explored before this study",
        "control_validation.json",
    )
    adverse(
        "Identifiability",
        "Class imbalance/easy background hides poor classes",
        "Balanced training weights and per-class confusion/recall",
        "Woody shrub transfer remains substantially weaker",
        "PASS",
        "Broad heterogeneous category definitions remain",
        "prior:tables/class_specific_transfer.csv",
    )
    adverse(
        "Identifiability",
        "Selector adds no value over chance subsets",
        "Five random paths, same budgets/folds/C grid",
        "Moderate-budget benefit; very small subsets not uniformly better; large-budget gap small",
        "PASS",
        "Five Monte Carlo controls; no globally optimal bands",
        "tables/selected_minus_random.csv",
    )
    adverse(
        "Identifiability",
        "Neighbor redundancy mistaken for independent information",
        "Within-subset |r|, PCA20/50, random and full regularized models",
        "Many redundant coordinates; useful complementary combinations still improve accuracy",
        "PASS",
        "No universal intrinsic dimensionality identified",
        "tables/subset_redundancy.csv; tables/metrics.csv",
    )
    adverse(
        "Identifiability",
        "Site or acquisition memorization",
        "Hold whole sites; paired same-target-ID years",
        "Geographic and asymmetric temporal penalties remain",
        "PASS",
        "Retrospective footprint recognition, not annual ecological change",
        "tables/metrics.csv",
    )
    adverse(
        "Abundance",
        "Parent leakage/dependent synthetic rows",
        "Verify proper/tuning/target IDs; common truth and bundle bootstrap",
        "All canonical cases pass; bundles are uncertainty unit",
        "PASS",
        "Finite parent set and designed mixtures",
        "tables/canonical_prediction_checks.csv; prior:numerical_validation.json",
    )
    adverse(
        "Abundance",
        "Constrained solver broken",
        "Known generating-parent oracle",
        "Fraction RMSE near machine precision",
        "PASS",
        "Ideal linear control unavailable operationally",
        "prior:tables/oracle_solver_controls.csv",
    )
    adverse(
        "Abundance",
        "Ridge simply predicts class prior",
        "Compare every primary model/domain with proper-training fraction mean",
        "Ridge fails global-year mean no-spectrum control",
        "FAIL",
        "No transferable spectral skill in every observed domain",
        "tables/abundance_paired_vs_baselines.csv",
    )
    adverse(
        "Abundance",
        "Unequal retained library makes ridge comparison intrinsic",
        "Refit ridge from exact 15 MESMA candidate parents",
        "NEON advantage disappears in reduced-parent control",
        "FAIL",
        "Different priors/hypothesis classes and training diversity prevent causal apportionment",
        "tables/same_candidate_ridge.csv",
    )
    adverse(
        "Abundance",
        "Simplex projection creates all gains",
        "Raw versus projected ridge fraction error and independent projection tests",
        "Projection helps, especially shifted domains; raw new-parent ridge still improves on MESMA",
        "PASS",
        "Raw fractions are not physically constrained compositions",
        "prior:tables/raw_prediction_constraint_diagnostics.csv",
    )
    adverse(
        "Abundance",
        "Good reconstruction implies correct fractions",
        "Plot native residual against fraction error, retain ambiguity strata",
        "Low residual can coexist with wrong class fractions",
        "FAIL",
        "Reconstruction alone cannot validate biological fractions",
        "prior:tables/abundance_by_ambiguity.csv",
    )
    adverse(
        "Abundance",
        "Lower expected error removes spectral ambiguity",
        "Common candidate-library alternative-composition diagnostic",
        "Improved expected error coexists with high ambiguity",
        "FAIL",
        "Not an exhaustive physical uncertainty set",
        "prior:tables/abundance_by_ambiguity.csv",
    )
    adverse(
        "Abundance",
        "Recognition success guarantees fraction recovery",
        "Class-level recall/error/detection/ambiguity links",
        "Descriptive associations only five categories; miss/false-positive tradeoffs differ",
        "PASS",
        "No causal or population correlation inference",
        "tables/class_link_correlations.csv",
    )
    adverse(
        "Field abundance",
        "Synthetic fractions equal real cover",
        "Seek independent field fraction and purity truth",
        "Required observations absent",
        "NOT TESTABLE",
        "Acquisition, spatial support, nonlinearity and label purity unvalidated",
        "foundation.json; NEXT_DATA_NEEDED.md",
    )
    pd.DataFrame(adversarial).to_csv(T / "adversarial_validation.csv", index=False)
    ladder = pd.DataFrame(
        [
            dict(
                level=1,
                question="SEPARABILITY",
                status="ESTABLISHED",
                evidence="All ten researcher-category pairs show blocked whole-spectrum differences in four sampled cohorts; adjusted wavelength evidence retained.",
                scope="Observed labelled footprints, declared exchangeability/units assumptions; not universal ecological difference.",
            ),
            dict(
                level=2,
                question="IDENTIFIABILITY",
                status="CONDITIONAL",
                evidence="Nested unseen-ID recognition; weaker held-site and temporal performance; selected/random/PCA controls.",
                scope="Class-specific errors, sampled sites and retrospective labels; not guaranteed recognition in new regions.",
            ),
            dict(
                level=3,
                question="ABUNDANCE",
                status="CONDITIONAL",
                evidence="Known algebraic fractions recovered with conditional errors; oracle works. Ridge120 gains fail same-candidate NEON control and global-year prior control.",
                scope="Finite-parent synthetic mixtures only; learned prior and non-unique solutions remain.",
            ),
            dict(
                level=4,
                question="FIELD ABUNDANCE",
                status="NOT ESTABLISHED",
                evidence="No independent contemporaneous field fractions or verified pure parent materials.",
                scope="Requires new biological/physical observations, not more synthetic mixtures.",
            ),
        ]
    )
    ladder.to_csv(T / "evidence_ladder.csv", index=False)
    # Publication summaries and exact source filters.
    metrics = pd.read_csv(T / "metrics.csv")
    old = pd.read_csv(O / "complementary_feature_performance.csv")
    perf = (
        metrics[metrics.kind.isin(["plant", "site"])]
        .groupby(["kind", "method", "budget"])
        .BA.agg(["mean", "min", "max"])
        .reset_index()
    )
    save = perf.to_csv(T / "recognition_control_summary.csv", index=False)
    increments = []
    for (kind, method), g in perf[
        perf.method.isin(["Random", "Selected replay"])
    ].groupby(["kind", "method"]):
        g = g.sort_values("budget")
        last = None
        for r in g.itertuples():
            increments.append(
                dict(
                    kind=kind,
                    method=method,
                    budget=r.budget,
                    BA=r.mean,
                    increment_from_previous=np.nan if last is None else r.mean - last,
                )
            )
            last = r.mean
    pd.DataFrame(increments).to_csv(
        T / "recognition_budget_increments.csv", index=False
    )
    temporal = metrics[~metrics.kind.isin(["plant", "site"])].copy()
    temporal["training_year"] = temporal.fold.str.extract(r"train(\d{4})").astype(float)
    temporal["target_year"] = temporal.target.str.extract(r"target(\d{4})").astype(
        float
    )
    temporal["same_year"] = temporal.training_year.eq(temporal.target_year)
    temporal.to_csv(T / "temporal_recognition_summary.csv", index=False)
    print("Requirements", len(table), "adversarial claims", len(adversarial))


if __name__ == "__main__":
    main()
