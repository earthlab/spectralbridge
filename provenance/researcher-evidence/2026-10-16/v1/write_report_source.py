"""Author an editable, source-linked report organized by exactly three questions."""

import json
import numpy as np
import pandas as pd
from run_controls import BASE, PRIOR, REPO, CATS

T = BASE / "tables"
O = PRIOR / "tables"


def main():
    foundation = json.loads((BASE / "foundation.json").read_text())
    figures = json.loads((BASE / "figure_manifest.json").read_text())
    old = pd.read_csv(O / "complementary_feature_performance.csv")
    metrics = pd.read_csv(T / "metrics.csv")
    summ = pd.read_csv(T / "abundance_domain_summary.csv")
    same = pd.read_csv(T / "same_candidate_ridge.csv")

    def ba(kind, budget):
        return old[
            old.kind.eq(kind) & old.budget.astype(str).eq(str(budget))
        ].balanced_accuracy.mean()

    def rmse(kind, method, rep="NEON"):
        return summ[
            summ.kind.eq(kind) & summ.method.eq(method) & summ.representation.eq(rep)
        ]["mean"].iloc[0]

    def control(kind, method, budget):
        return metrics[
            metrics.kind.eq(kind)
            & metrics.method.eq(method)
            & metrics.budget.eq(budget)
        ].BA.mean()

    def equal(kind):
        return same[same.kind.eq(kind) & same.representation.eq("NEON")].RMSE.mean()

    class_rho = (
        pd.read_csv(T / "class_link_correlations.csv")
        .query("kind == 'site' and metric == 'RMSE'")
        .Spearman_rho.iloc[0]
    )
    claims = []

    def claim(cid, text, source, filter_text, scope):
        claims.append(
            dict(
                claim_id=cid,
                claim=text,
                source=source,
                source_filter=filter_text,
                scope=scope,
            )
        )

    for kind in ["plant", "site"]:
        claim(
            "ID_" + kind,
            f"Full NEON BA {ba(kind, 360):.3f}; synthetic OLI BA {ba(kind, 'OLI'):.3f}",
            "prior:tables/complementary_feature_performance.csv",
            f"kind={kind}, budget=360 or OLI; mean balanced_accuracy",
            "Three observed outer folds, no deployment guarantee",
        )
        claim(
            "RANDOM_" + kind,
            f"20-coordinate BA selected {control(kind, 'Selected replay', 20):.3f}, random {control(kind, 'Random', 20):.3f}",
            "tables/metrics.csv",
            f"kind={kind}, budget=20; mean BA by method",
            "Five random paths, no outer seed selection",
        )
        claim(
            "AB_" + kind,
            f"NEON RMSE ridge120 {rmse(kind, 'Ridge'):.3f}, MESMA15 {rmse(kind, 'MESMA'):.3f}, prior {rmse(kind, 'Training prior'):.3f}",
            "tables/abundance_domain_summary.csv",
            f"kind={kind}, representation=NEON",
            "Synthetic finite-parent mixtures, conditional mean-fold error",
        )
        claim(
            "FAIR_" + kind,
            f"Same-candidate ridge15 RMSE {equal(kind):.3f} versus MESMA15 {rmse(kind, 'MESMA'):.3f}",
            "tables/same_candidate_ridge.csv",
            f"kind={kind}, representation=NEON; mean RMSE/MESMA_RMSE",
            "Capacity sensitivity, not a causal decomposition",
        )
    claim(
        "YEAR_PRIOR",
        f"Global-year NEON ridge RMSE {rmse('year', 'Ridge'):.3f}, prior {rmse('year', 'Training prior'):.3f}",
        "tables/abundance_domain_summary.csv",
        "kind=year, representation=NEON",
        "Site/year confounding, retrospective category truth",
    )
    pair = pd.read_csv(T / "pair_support_and_evidence.csv")
    claim(
        "SEP_ALL",
        f"{len(pair)} category pairs in {int(pair.cohorts.sum())} supported cohort contrasts; largest adjusted whole-spectrum p={pair.largest_adjusted_NEON_p.max():.3f}",
        "tables/pair_support_and_evidence.csv",
        "all ten pairs, four acquisition-matched cohorts",
        "Exchangeability within exact acquisition-history blocks assumed",
    )
    rate = pd.read_csv(O / "class_specific_transfer.csv")
    shrub = rate[
        rate.kind.eq("site")
        & rate.budget.astype(str).eq("360")
        & rate.researcher_category.eq("Woody shrub")
    ].recall.mean()
    claim(
        "SHRUB",
        f"Woody shrub held-site NEON recall {shrub:.3f}",
        "prior:tables/class_specific_transfer.csv",
        "kind=site,budget=360,researcher_category=Woody shrub; mean recall",
        "Three sampled site targets, not all woody shrubs",
    )
    pd.DataFrame(claims).to_csv(T / "claim_registry.csv", index=False)
    pages = []

    def page(
        title, paragraphs=None, figure=None, table=None, ending=None, sources=None
    ):
        pages.append(
            dict(
                title=title,
                paragraphs=paragraphs or [],
                figure=figure,
                table=table,
                ending=ending or [],
                sources=sources or [],
            )
        )

    page(
        "Three questions, three different levels of evidence",
        [
            (
                "Purpose",
                "Do the five researcher-defined categories have different spectra? Can we recognize an unseen observation? Can we recover category fractions from a mixture? These questions demand progressively stronger evidence. A positive answer at one level is not a positive answer at the next.",
            ),
            (
                "The biological grouping",
                "Deciduous; Evergreen; Herbaceous; Non-vegetated & dead; Woody shrub. Only the recorded cover_category field enters this primary analysis. Historical groupings and all earlier reports remain preserved separately.",
            ),
            (
                "The evidence progression",
                "Spectra can differ → differences may allow category recognition → recognized components may or may not have recoverable abundance → real field cover still requires independent validation.",
            ),
            (
                "The main result",
                f"All ten category pairs differ in the sampled blocked comparisons. Full-NEON recognition BA is {ba('plant', 360):.1%} for unseen polygons and {ba('site', 360):.1%} for held sites. Synthetic ridge120 fraction RMSE is {rmse('plant', 'Ridge'):.3f}/{rmse('site', 'Ridge'):.3f}, but the same-candidate ridge15 control loses that advantage, and global-year ridge does not beat the no-spectrum prior.",
            ),
            (
                "What changed after the audit",
                "This is more than a rearranged report: five random-subset paths per budget, PCA recognition controls, a consistent nested temporal classifier, a 15-parent same-candidate ridge test, class-level recognition/abundance links and explicit adverse explanations were added. Valid prior evidence was reused.",
            ),
            (
                "Scope",
                "This is a structured reanalysis of an extensively explored observational library, not an independently preregistered confirmation. Scores concern labelled polygon footprints and synthetic algebraic weights. No independent field fractional-cover validation exists.",
            ),
        ],
        sources=[
            "tables/claim_registry.csv",
            "DESIGN.md",
            "ABUNDANCE_CONTROL_DESIGN.md",
        ],
    )
    page("Foundational validation: observations, support and independence", figure=1)
    page(
        "Foundational validation: what passes and what cannot be tested",
        [
            (
                "How to read this audit",
                "PASS means the stated design requirement was met or its limitation was documented by evidence. FAIL means a substantive tested claim failed. NOT TESTABLE means the required truth or independent support is unavailable. A procedurally valid experiment may correctly produce a negative scientific result.",
            ),
            (
                "Source validity",
                f"The supplied table has {foundation['source_pixel_rows']:,} pixel rows. Its merged corrected schema contains {foundation['source_corrected_coordinates']:,} native wavelength columns because source products have different native coordinates; each pixel has exactly {foundation['source_valid_corrected_coordinates_per_pixel_min']} finite corrected native values. Structural null padding must not be called analytical-grid missingness. The retained 360-coordinate polygon/year grid is finite, and no exact duplicate annual NEON/OLI spectra were found.",
            ),
            (
                "Truth and units",
                "Annotations date to 2023/2024 and are reused across acquisition years. GlobalID denotes a polygon footprint, not certified plant/material purity. Absolute stored reflectance scaling is unresolved; no guessed correction, rescaling or interpolation was introduced.",
            ),
        ],
        table="FOUNDATION",
        sources=[
            "foundation.json",
            "tables/source_corrected_validity.csv",
            "tables/duplicate_spectra.csv",
            "tables/design_validation.csv",
        ],
    )
    page(
        "1. SEPARABILITY",
        [
            (
                "Scientific question",
                "Are the five researcher categories spectrally different, where do differences occur, and are those differences stable across observed domains? This section concerns difference, not classification or fractions.",
            ),
            (
                "Relevant method",
                "Reuse 40 exact-acquisition-history matched cohort contrasts: ten category pairs in NIWO 2020, NIWO 2023, WREF 2023 and YELL 2023. Whole-curve category permutations preserve adjacent-wavelength correlation; 9,999 synchronized shuffles per contrast support the existing maximum, integrated and combined tests. Whole-spectrum evidence uses its declared Holm family.",
            ),
            (
                "Wavelength evidence",
                "The wavelength map uses within-contrast max-T and Bonferroni across 40 contrasts. Whole-curve null maxima account for correlated channels; 360 wavelengths are never treated as 360 independent biological samples. Full-cohort inferential maps are descriptive and never select predictive features. Separate training-only evidence was previously validated.",
            ),
            (
                "Effect versus evidence",
                "Standardized signed effects and width-weighted RMS whole-spectrum effects quantify magnitude. Adjusted permutation probabilities quantify evidence under the exchangeability assumption. Saved null standard errors/envelopes localize departures from that null; they are not confidence intervals for effect size.",
            ),
            (
                "Domain and resolution",
                "All four cohort effects, wavelength sign/magnitude consistency, rank consistency, weakest observed effect domain and NIWO year differences are retained. Visible, red edge, NIR, SWIR1 and SWIR2 are summaries of disconnected supported coordinates. OLI is a synthetic convolution of the same corrected reference, not independent satellite validation.",
            ),
        ],
        table="PAIR_SUPPORT",
        sources=[
            "tables/pair_support_and_evidence.csv",
            "tables/whole_spectrum_separability.csv",
            "tables/wavelength_effect_stability.csv",
            "tables/wavelength_null_uncertainty.csv",
            "prior:tables/domain_rank_consistency.csv",
        ],
    )
    page("1. SEPARABILITY | effect magnitude and sensor resolution", figure=2)
    page(
        "1. SEPARABILITY | every supported wavelength, every observed cohort", figure=3
    )
    page(
        "1. SEPARABILITY | validation and evidence statement",
        table="SEPARABILITY",
        ending=[
            (
                "WHAT WE KNOW",
                "All ten researcher-category contrasts differ in these acquisition-matched cohorts. Many broad spectral intervals carry adjusted evidence; magnitudes and directions are not equally stable everywhere. Synthetic OLI often retains substantial standardized effect despite reduced spectral resolution.",
            ),
            (
                "WHAT WE DO NOT KNOW",
                "Universal differences across ecological regions, physical pure-material distinctions, independently verified annual biological change, and absolute physical reflectance units are not established.",
            ),
            (
                "WHAT WOULD FALSIFY THE CURRENT INTERPRETATION",
                "An independently annotated, adequately supported acquisition-matched sample that fails to reproduce the effect, reverses its domain stability, or reveals an unaccounted source/label/scaling artifact would challenge generalization. A documented violation of within-block exchangeability would weaken the present permutation interpretation.",
            ),
        ],
        sources=[
            "tables/design_validation.csv",
            "tables/whole_spectrum_separability.csv",
            "tables/wavelength_effect_stability.csv",
        ],
    )
    page(
        "2. IDENTIFIABILITY",
        [
            (
                "Scientific question",
                "Given an unseen polygon spectrum, can we identify its researcher category? A significant distributional difference does not guarantee a correct label for an individual observation.",
            ),
            (
                "Relevant method",
                "Binary comparisons use the prespecified balanced-prior univariate linear discriminant rule: direction and midpoint are learned only from training IDs. Five-class single-coordinate recognition uses nearest training-class mean with equal priors. These rules were already run; they are reused rather than silently replaced with an optimized classifier. Pairwise BA has chance .50, five-class BA .20.",
            ),
        ],
        figure=4,
    )
    page(
        "2. IDENTIFIABILITY | complementary information and matched controls",
        [
            (
                "Relevant method",
                "The original greedy orthogonal-residual selector is refitted within each inner group fold; logistic C is chosen from .1/1/10. Five fixed uniform random coordinate permutations now supply nested equal-size controls using the exact same inner folds and C grid. No random seed is chosen by target performance. PCA20/PCA50 and regularized full NEON/OLI provide training-only sensitivities.",
            ),
            (
                "Incremental information",
                f"At 20 coordinates, new-polygon BA is {control('plant', 'Selected replay', 20):.1%} selected versus {control('plant', 'Random', 20):.1%} random; held-site BA is {control('site', 'Selected replay', 20):.1%} versus {control('site', 'Random', 20):.1%}. At 100 coordinates the average gap narrows. These curves do not establish an optimal sensor or universal independent information dimension.",
            ),
        ],
        figure=5,
    )
    page(
        "2. IDENTIFIABILITY | class-specific and domain failures",
        [
            (
                "Relevant method",
                "Full-spectrum recognition is identity-balanced regularized logistic with group-aware inner tuning. Every held site is absent from training. The new temporal framework uses the same full/OLI model procedure: global-year holds plus three NIWO held-ID folds in each training-year direction, with the same targets evaluated in both acquisition years.",
            ),
            (
                "Transfer penalty",
                f"Mean new-polygon to held-site BA falls by {100 * (ba('plant', 360) - ba('site', 360)):.1f} percentage points for NEON and {100 * (ba('plant', 'OLI') - ba('site', 'OLI')):.1f} percentage points for OLI. Woody shrub held-site recall is {shrub:.1%}. Means alone must not hide this failure or the differing temporal directions.",
            ),
        ],
        figure=6,
    )
    page(
        "2. IDENTIFIABILITY | validation and evidence statement",
        table="IDENTIFIABILITY",
        ending=[
            (
                "WHAT WE CAN IDENTIFY",
                "The five-category label of unseen sampled-population polygons with useful but imperfect accuracy. Evergreen and background transfer more reliably than Woody shrub. Complementary subsets add average moderate-budget value over equal-size random controls.",
            ),
            (
                "WHAT WE CANNOT RELIABLY IDENTIFY",
                "Every Woody shrub footprint, every small-subset target, or observations from arbitrary new regions/years. Category recognition is not species identity, material purity or unique mixture composition.",
            ),
            (
                "WHERE IDENTIFICATION FAILS",
                "Held sites, asymmetric paired image-year transfer, difficult category overlaps, and insufficient individual-coordinate information. Small selected budgets do not uniformly outperform random subsets.",
            ),
            (
                "WHAT ADDITIONAL DATA WOULD MOST IMPROVE IDENTIFICATION",
                "Independently annotated footprints across more sites and acquisition years, deliberate hard-class sampling, spatially separated target plots and contemporaneous repeated biological labels.",
            ),
        ],
        sources=[
            "tables/design_validation.csv",
            "tables/metrics.csv",
            "tables/selected_minus_random.csv",
            "tables/temporal_recognition_summary.csv",
        ],
    )
    page(
        "3. ABUNDANCE",
        [
            (
                "Scientific question",
                "Given a mixed spectrum, can we recover the fraction belonging to each researcher category? Fraction accuracy is the target. Spectral reconstruction alone is not a biological fraction validation.",
            ),
            (
                "Relevant method",
                "Reuse the fixed 170 pair/triple-grid mixtures per five-parent bundle. A training context has 24 proper bundles (120 distinct parents), eight tuning bundles (40 parents) and 12 target bundles (60 parents). GlobalIDs are disjoint across roles; all primary methods receive identical outer targets. Twelve dependent bundles, not 2,040 synthetic rows, define each target experiment.",
            ),
            (
                "Models and constraints",
                "No-spectrum proper-training fraction mean, FCLS, EAR/MESMA, ridge, PLS, forest, boosting and two-stage presence/conditional regression are compared. Hyperparameters/scalers/transforms are fitted only in the appropriate training/tuning roles. Supervised fractions use independently tested Euclidean simplex projection; raw error/constraint violations are retained.",
            ),
            (
                "Oracle before model ranking",
                "Given the actual generating parents, the ideal linear constrained oracle recovers fractions to near machine precision. That verifies the algebraic solver/mixture control; failure with a candidate library cannot simply be blamed on the solver. The oracle cannot be deployed and does not validate physical mixing or purity.",
            ),
            (
                "Uncertainty and domain scope",
                "Paired bootstrap draws resample whole target parent bundles, retaining matching method errors. Report per-target intervals against MESMA and the no-spectrum prior. New-parent, held-site, global-year and complete-pair temporal targets remain distinct; the same identities across paired target years are not independent replicates.",
            ),
            (
                "The most important new adverse test",
                "The main ridge uses all 120 proper parents but MESMA retains 15 candidates from that pool. The new fairness control uses exactly those 15 saved MESMA parents to train ridge, with the unchanged tuning/target sets. Its failure materially limits an intrinsic ridge-versus-MESMA interpretation.",
            ),
        ],
        sources=[
            "DESIGN.md",
            "ABUNDANCE_CONTROL_DESIGN.md",
            "prior:METHODS.md",
            "prior:tables/abundance_parent_memberships.csv",
            "prior:tables/oracle_solver_controls.csv",
            "tables/same_candidate_ridge.csv",
        ],
    )
    page("3. ABUNDANCE | model, prior, projection and capacity controls", figure=7)
    page("3. ABUNDANCE | error across the supported true-fraction grid", figure=8)
    page("3. ABUNDANCE | presence, amount and category-specific overlap", figure=9)
    page(
        "3. ABUNDANCE | detection and conditional quantification",
        [
            (
                "Two distinct questions",
                "Stage A tests presence using tuning-only thresholds. If every class is rejected, the existing algorithm admits its highest-scoring class; the table reports this admitted gate. Raw versus admitted decisions and detection by fraction are saved separately. Final-fraction detection uses the separate declared .10 comparison cutoff. Positive RMSE below is conditional on true presence, not on the model accepting the category. Missed low fractions and absent-category false detections must be assessed together.",
            ),
            (
                "Class-level link",
                f"Across these five categories, higher held-site recognition recall is descriptively associated with lower ridge120 fraction RMSE (Spearman rho={class_rho:.1f}), but low-fraction misses do not follow the same ranking. Five class means do not supply population or causal correlation evidence. Mixture ambiguity burden is the maximum feasible range of any class in mixtures containing the named class, not a class-specific uncertainty interval.",
            ),
        ],
        table="DETECTION",
        sources=[
            "prior:tables/abundance_model_comparison.csv",
            "prior:tables/two_stage_presence_metrics.csv",
            "tables/class_recognition_abundance_links.csv",
            "tables/class_link_correlations.csv",
            "tables/stage_A_detection_by_fraction.csv",
            "tables/forced_presence_admission.csv",
        ],
    )
    page(
        "3. ABUNDANCE | ambiguity, reconstruction and spectral representation",
        figure=10,
    )
    page(
        "3. ABUNDANCE | paired uncertainty against both baselines",
        [
            (
                "How to read the table",
                "Each row is a NEON target set. Differences are ridge120 minus the named comparator, so a negative value favors ridge. Brackets are conditional 95% paired whole-bundle bootstrap intervals (999 draws), not joint family-corrected declarations. Target sets from paired years reuse parents; do not pool them as independent biological samples.",
            ),
            (
                "Absolute and relative gains",
                f"For new-parent targets, mean RMSE decreases {rmse('plant', 'MESMA') - rmse('plant', 'Ridge'):.3f} ({1 - rmse('plant', 'Ridge') / rmse('plant', 'MESMA'):.1%}) relative to MESMA; held-site reduction is {rmse('site', 'MESMA') - rmse('site', 'Ridge'):.3f} ({1 - rmse('site', 'Ridge') / rmse('site', 'MESMA'):.1%}). These are gains for the configured unequal-capacity benchmark, not intrinsic method superiority.",
            ),
            (
                "Negative controls matter",
                f"Global-year mean ridge error {rmse('year', 'Ridge'):.3f} exceeds the no-spectrum prior {rmse('year', 'Training prior'):.3f}. Same-candidate ridge15 NEON error is {equal('plant'):.3f}/{equal('site'):.3f}, so the full-parent gains cannot be generalized to equal retained training diversity.",
            ),
        ],
        table="PAIRED",
        sources=[
            "tables/abundance_paired_vs_baselines.csv",
            "tables/abundance_domain_summary.csv",
            "tables/same_candidate_ridge.csv",
        ],
    )
    page(
        "3. ABUNDANCE | validation checklist",
        table="ABUNDANCE",
        sources=["tables/design_validation.csv"],
    )
    page(
        "3. ABUNDANCE | limiting factors and evidence statement",
        table="LIMITING",
        ending=[
            (
                "WHAT WE CAN ESTIMATE",
                f"Known algebraic category weights in this finite-parent synthetic benchmark. Full-parent ridge120 mean RMSE is {rmse('plant', 'Ridge'):.3f} for new parents and {rmse('site', 'Ridge'):.3f} for held sites; class-specific biases and detection tradeoffs remain substantial.",
            ),
            (
                "WHERE IT TRANSFERS / WHERE IT FAILS",
                "Some sampled held-site and paired-year targets retain useful skill. Global-year mean fails the no-spectrum prior, same-candidate NEON ridge loses its advantage, and derivative transformations worsen the main results. Do not select a winner solely from one favorable mean.",
            ),
            (
                "WHETHER THE INVERSION IS UNIQUE",
                "Not established. Alternative candidate compositions can fit nearly equally well even when expected fraction error is reduced. Learned priors can improve prediction without removing non-uniqueness.",
            ),
            (
                "WHAT IS STILL REQUIRED FOR FIELD ABUNDANCE",
                "Independent contemporaneous field fractions at aligned spatial support, validated annotation/material purity and reflectance units, real mixing/nonlinearity checks, and broader site/year external targets. More mixtures from the same parents do not fill these gaps.",
            ),
        ],
        sources=[
            "tables/abundance_domain_summary.csv",
            "tables/same_candidate_ridge.csv",
            "prior:tables/abundance_by_ambiguity.csv",
            "prior:tables/abundance_model_comparison.csv",
        ],
    )
    page(
        "FINAL EVIDENCE LADDER",
        table="LADDER",
        ending=[
            (
                "LIMITATIONS",
                "The dataset was repeatedly explored before these experiments. Nested splitting protects within-experiment tuning, not all design adaptation to known data. Only three sites and one repeatedly sampled site are available; site/year/class/acquisition effects are not fully crossed. Distinct polygons can be spatially correlated. Retrospective annotations do not certify biological persistence or purity.",
            ),
            (
                "Do not collapse the ladder",
                "A significant distributional contrast is not reliable individual recognition; recognition is not unique inversion; low synthetic fraction error is not independent field-cover validation. The four levels retain separate statuses and evidence.",
            ),
        ],
        sources=["tables/evidence_ladder.csv", "tables/adversarial_validation.csv"],
    )
    page(
        "WHAT DATA SHOULD BE COLLECTED NEXT",
        [
            (
                "1. Independent field fraction targets",
                "Collect contemporaneous fractional cover for all five categories at explicitly matched footprint/PSF support, including true zeros, small fractions, intermediate and near-pure cases. Hold these plots out from all library selection, model development and calibration. Include repeated human/measurement uncertainty.",
            ),
            (
                "2. Verify physical reference meaning",
                "Document reflectance scaling/units, radiometric lineage, spatial support and parent-material/category purity. Synthetic convolution from the same reference cannot establish satellite/drone interchangeability or certify physical endmembers.",
            ),
            (
                "3. Separate geography from time",
                "Add balanced category samples across multiple new regions and years, with independently repeated biological annotations and acquisition metadata. Use spatially separated or buffered targets to test residual neighborhood dependence.",
            ),
            (
                "4. Target known failures",
                "Oversample independently verified Woody shrub versus Herbaceous/Deciduous overlaps; include varied within-category conditions and mixed backgrounds. Assess absent-category false detections and low-fraction misses independently of the comparison cutoff.",
            ),
            (
                "5. Freeze the next validation protocol",
                "Before collecting/evaluating the new targets, fix models, training-library capacity, fraction priors, spatial aggregation, missingness rules, sensor construction, detection/quantification criteria and acceptable uncertainty. Treat current thresholds and data-dependent discoveries as hypothesis-generating.",
            ),
        ],
        sources=["NEXT_DATA_NEEDED.md", "tables/adversarial_validation.csv"],
    )
    page(
        "REPRODUCIBILITY",
        [
            (
                "Canonical inputs and preserved history",
                "The supplied polygon Parquet is read in place. No source spectral dataset was copied. The sealed P129 packet and its previous report remain immutable; its 196 owned files are checked before/after. All new scientific grouping uses cover_category only.",
            ),
            (
                "New analysis protocol",
                "DESIGN.md fixes random/PCA/temporal controls; ABUNDANCE_CONTROL_DESIGN.md records the later hostile-review fairness addition before its evaluation. Fixed seeds, split memberships, feature paths, inner scores, model parameters, target contributions and per-case hashes are saved. This is a documented exploratory reanalysis, not retrospective preregistration.",
            ),
            (
                "Numerical reproduction",
                "run_controls.py and run_candidate_control.py are restart-safe. validate_controls.py independently reconstructs all saved classification predictions and inner groups; validate_candidates.py uses independent ridge normal equations. synthesize.py checks every canonical abundance evaluation against saved truth; no model is accepted solely from a summary CSV.",
            ),
            (
                "Figures and report",
                "Ten figure families have PNG/PDF/SVG exports. Every caption states how to read it, what is learned and what remains uncertain. figure_manifest.json lists exact numerical sources/hashes. report_source.json and report_source.md are editable; build_report.py renders from saved sources without refitting. Final geometry, rendered-page review, source hashes and deterministic rebuilding are recorded.",
            ),
            (
                "Interpretive traceability",
                "tables/design_validation.csv contains every requirement and its PASS/FAIL/NOT TESTABLE result. tables/adversarial_validation.csv records the hostile review. tables/claim_registry.csv maps key quantitative claims to their exact source filters. tables/evidence_ladder.csv keeps four scientific evidence levels separate.",
            ),
        ],
        sources=[
            "README.md",
            "VALIDATION.md",
            "control_validation.json",
            "candidate_validation.json",
            "synthesis_validation.json",
            "figure_manifest.json",
            "tables/claim_registry.csv",
        ],
    )
    audit = pd.read_csv(T / "adversarial_validation.csv")
    for start in range(0, len(audit), 7):
        page(
            f"Adversarial validation appendix | {start + 1}-{min(start + 7, len(audit))}",
            [
                (
                    "Hostile-review rule",
                    "Each major claim must survive its plausible alternative explanations. FAIL explicitly preserves a failed interpretation; it does not disappear because other tests passed. NOT TESTABLE identifies missing evidence rather than an invented substitute.",
                )
            ],
            table=f"ADVERSARIAL:{start}",
            sources=["tables/adversarial_validation.csv"],
        )
    for item in pages:
        if item["title"] == "3. ABUNDANCE | limiting factors and evidence statement":
            last_two = item["ending"][-2:]
            item["ending"] = [
                (
                    "WHAT WE CAN ESTIMATE",
                    "Known algebraic researcher-category weights in this finite-parent synthetic benchmark; these are not independently measured field fractions.",
                ),
                (
                    "HOW ACCURATELY",
                    f"Full-parent ridge120 mean RMSE is {rmse('plant', 'Ridge'):.3f} for new parents and {rmse('site', 'Ridge'):.3f} for held sites. Class-specific biases, false detections and low-fraction misses remain substantial.",
                ),
                (
                    "WHERE IT TRANSFERS",
                    "Some sampled held-site and paired acquisition-year targets retain useful conditional skill. This does not establish performance in arbitrary regions or years.",
                ),
                (
                    "WHERE IT FAILS",
                    "Global-year mean fails the no-spectrum prior, same-candidate NEON ridge loses its original advantage, and derivatives worsen the main results. Do not select a winner solely from one favorable mean.",
                ),
            ] + last_two
    pages[1]["paragraphs"] = pages[2]["paragraphs"][1:]
    pages[2]["paragraphs"] = pages[2]["paragraphs"][:1]
    source = {
        "title": "Separability, Identifiability and Abundance",
        "subtitle": "Five researcher categories: a hostile-review validation report",
        "date": "2026-10-16",
        "pages": pages,
        "figures": figures,
        "claims": claims,
    }
    (BASE / "report_source.json").write_text(json.dumps(source, indent=2) + "\n")
    lines = ["# " + source["title"], "", source["subtitle"], ""]
    for p in pages:
        lines += ["## " + p["title"], ""]
        for h, text in p["paragraphs"] + p["ending"]:
            lines += ["### " + h, "", text, ""]
        if p["figure"]:
            lines += ["Figure: " + figures[p["figure"] - 1]["name"], ""]
        if p["table"]:
            lines += ["Table: " + p["table"], ""]
        lines += ["Sources: " + "; ".join(p["sources"]), ""]
    (BASE / "report_source.md").write_text("\n".join(lines) + "\n")
    print(
        "Authored",
        len(pages),
        "report page groups and",
        len(claims),
        "quantitative claims.",
    )


if __name__ == "__main__":
    main()
