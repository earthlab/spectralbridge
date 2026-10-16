# Separability, Identifiability and Abundance

Five researcher categories: a hostile-review validation report

## Three questions, three different levels of evidence

### Purpose

Do the five researcher-defined categories have different spectra? Can we recognize an unseen observation? Can we recover category fractions from a mixture? These questions demand progressively stronger evidence. A positive answer at one level is not a positive answer at the next.

### The biological grouping

Deciduous; Evergreen; Herbaceous; Non-vegetated & dead; Woody shrub. Only the recorded cover_category field enters this primary analysis. Historical groupings and all earlier reports remain preserved separately.

### The evidence progression

Spectra can differ → differences may allow category recognition → recognized components may or may not have recoverable abundance → real field cover still requires independent validation.

### The main result

All ten category pairs differ in the sampled blocked comparisons. Full-NEON recognition BA is 85.2% for unseen polygons and 73.8% for held sites. Synthetic ridge120 fraction RMSE is 0.216/0.269, but the same-candidate ridge15 control loses that advantage, and global-year ridge does not beat the no-spectrum prior.

### What changed after the audit

This is more than a rearranged report: five random-subset paths per budget, PCA recognition controls, a consistent nested temporal classifier, a 15-parent same-candidate ridge test, class-level recognition/abundance links and explicit adverse explanations were added. Valid prior evidence was reused.

### Scope

This is a structured reanalysis of an extensively explored observational library, not an independently preregistered confirmation. Scores concern labelled polygon footprints and synthetic algebraic weights. No independent field fractional-cover validation exists.

Sources: tables/claim_registry.csv; DESIGN.md; ABUNDANCE_CONTROL_DESIGN.md

## Foundational validation: observations, support and independence

### Source validity

The supplied table has 85,706 pixel rows. Its merged corrected schema contains 1,140 native wavelength columns because source products have different native coordinates; each pixel has exactly 426 finite corrected native values. Structural null padding must not be called analytical-grid missingness. The retained 360-coordinate polygon/year grid is finite, and no exact duplicate annual NEON/OLI spectra were found.

### Truth and units

Annotations date to 2023/2024 and are reused across acquisition years. GlobalID denotes a polygon footprint, not certified plant/material purity. Absolute stored reflectance scaling is unresolved; no guessed correction, rescaling or interpolation was introduced.

Figure: F01_foundation

Sources: 

## Foundational validation: what passes and what cannot be tested

### How to read this audit

PASS means the stated design requirement was met or its limitation was documented by evidence. FAIL means a substantive tested claim failed. NOT TESTABLE means the required truth or independent support is unavailable. A procedurally valid experiment may correctly produce a negative scientific result.

Table: FOUNDATION

Sources: foundation.json; tables/source_corrected_validity.csv; tables/duplicate_spectra.csv; tables/design_validation.csv

## 1. SEPARABILITY

### Scientific question

Are the five researcher categories spectrally different, where do differences occur, and are those differences stable across observed domains? This section concerns difference, not classification or fractions.

### Relevant method

Reuse 40 exact-acquisition-history matched cohort contrasts: ten category pairs in NIWO 2020, NIWO 2023, WREF 2023 and YELL 2023. Whole-curve category permutations preserve adjacent-wavelength correlation; 9,999 synchronized shuffles per contrast support the existing maximum, integrated and combined tests. Whole-spectrum evidence uses its declared Holm family.

### Wavelength evidence

The wavelength map uses within-contrast max-T and Bonferroni across 40 contrasts. Whole-curve null maxima account for correlated channels; 360 wavelengths are never treated as 360 independent biological samples. Full-cohort inferential maps are descriptive and never select predictive features. Separate training-only evidence was previously validated.

### Effect versus evidence

Standardized signed effects and width-weighted RMS whole-spectrum effects quantify magnitude. Adjusted permutation probabilities quantify evidence under the exchangeability assumption. Saved null standard errors/envelopes localize departures from that null; they are not confidence intervals for effect size.

### Domain and resolution

All four cohort effects, wavelength sign/magnitude consistency, rank consistency, weakest observed effect domain and NIWO year differences are retained. Visible, red edge, NIR, SWIR1 and SWIR2 are summaries of disconnected supported coordinates. OLI is a synthetic convolution of the same corrected reference, not independent satellite validation.

Table: PAIR_SUPPORT

Sources: tables/pair_support_and_evidence.csv; tables/whole_spectrum_separability.csv; tables/wavelength_effect_stability.csv; tables/wavelength_null_uncertainty.csv; prior:tables/domain_rank_consistency.csv

## 1. SEPARABILITY | effect magnitude and sensor resolution

Figure: F02_separability

Sources: 

## 1. SEPARABILITY | every supported wavelength, every observed cohort

Figure: F03_wavelength_separability

Sources: 

## 1. SEPARABILITY | validation and evidence statement

### WHAT WE KNOW

All ten researcher-category contrasts differ in these acquisition-matched cohorts. Many broad spectral intervals carry adjusted evidence; magnitudes and directions are not equally stable everywhere. Synthetic OLI often retains substantial standardized effect despite reduced spectral resolution.

### WHAT WE DO NOT KNOW

Universal differences across ecological regions, physical pure-material distinctions, independently verified annual biological change, and absolute physical reflectance units are not established.

### WHAT WOULD FALSIFY THE CURRENT INTERPRETATION

An independently annotated, adequately supported acquisition-matched sample that fails to reproduce the effect, reverses its domain stability, or reveals an unaccounted source/label/scaling artifact would challenge generalization. A documented violation of within-block exchangeability would weaken the present permutation interpretation.

Table: SEPARABILITY

Sources: tables/design_validation.csv; tables/whole_spectrum_separability.csv; tables/wavelength_effect_stability.csv

## 2. IDENTIFIABILITY

### Scientific question

Given an unseen polygon spectrum, can we identify its researcher category? A significant distributional difference does not guarantee a correct label for an individual observation.

### Relevant method

Binary comparisons use the prespecified balanced-prior univariate linear discriminant rule: direction and midpoint are learned only from training IDs. Five-class single-coordinate recognition uses nearest training-class mean with equal priors. These rules were already run; they are reused rather than silently replaced with an optimized classifier. Pairwise BA has chance .50, five-class BA .20.

Figure: F04_single_coordinate_recognition

Sources: 

## 2. IDENTIFIABILITY | complementary information and matched controls

### Relevant method

The original greedy orthogonal-residual selector is refitted within each inner group fold; logistic C is chosen from .1/1/10. Five fixed uniform random coordinate permutations now supply nested equal-size controls using the exact same inner folds and C grid. No random seed is chosen by target performance. PCA20/PCA50 and regularized full NEON/OLI provide training-only sensitivities.

### Incremental information

At 20 coordinates, new-polygon BA is 81.6% selected versus 77.4% random; held-site BA is 70.1% versus 65.0%. At 100 coordinates the average gap narrows. These curves do not establish an optimal sensor or universal independent information dimension.

Figure: F05_complementarity_controls

Sources: 

## 2. IDENTIFIABILITY | class-specific and domain failures

### Relevant method

Full-spectrum recognition is identity-balanced regularized logistic with group-aware inner tuning. Every held site is absent from training. The new temporal framework uses the same full/OLI model procedure: global-year holds plus three NIWO held-ID folds in each training-year direction, with the same targets evaluated in both acquisition years.

### Transfer penalty

Mean new-polygon to held-site BA falls by 11.4 percentage points for NEON and 9.1 percentage points for OLI. Woody shrub held-site recall is 46.3%. Means alone must not hide this failure or the differing temporal directions.

Figure: F06_class_and_domain_failures

Sources: 

## 2. IDENTIFIABILITY | validation and evidence statement

### WHAT WE CAN IDENTIFY

The five-category label of unseen sampled-population polygons with useful but imperfect accuracy. Evergreen and background transfer more reliably than Woody shrub. Complementary subsets add average moderate-budget value over equal-size random controls.

### WHAT WE CANNOT RELIABLY IDENTIFY

Every Woody shrub footprint, every small-subset target, or observations from arbitrary new regions/years. Category recognition is not species identity, material purity or unique mixture composition.

### WHERE IDENTIFICATION FAILS

Held sites, asymmetric paired image-year transfer, difficult category overlaps, and insufficient individual-coordinate information. Small selected budgets do not uniformly outperform random subsets.

### WHAT ADDITIONAL DATA WOULD MOST IMPROVE IDENTIFICATION

Independently annotated footprints across more sites and acquisition years, deliberate hard-class sampling, spatially separated target plots and contemporaneous repeated biological labels.

Table: IDENTIFIABILITY

Sources: tables/design_validation.csv; tables/metrics.csv; tables/selected_minus_random.csv; tables/temporal_recognition_summary.csv

## 3. ABUNDANCE

### Scientific question

Given a mixed spectrum, can we recover the fraction belonging to each researcher category? Fraction accuracy is the target. Spectral reconstruction alone is not a biological fraction validation.

### Relevant method

Reuse the fixed 170 pair/triple-grid mixtures per five-parent bundle. A training context has 24 proper bundles (120 distinct parents), eight tuning bundles (40 parents) and 12 target bundles (60 parents). GlobalIDs are disjoint across roles; all primary methods receive identical outer targets. Twelve dependent bundles, not 2,040 synthetic rows, define each target experiment.

### Models and constraints

No-spectrum proper-training fraction mean, FCLS, EAR/MESMA, ridge, PLS, forest, boosting and two-stage presence/conditional regression are compared. Hyperparameters/scalers/transforms are fitted only in the appropriate training/tuning roles. Supervised fractions use independently tested Euclidean simplex projection; raw error/constraint violations are retained.

### Oracle before model ranking

Given the actual generating parents, the ideal linear constrained oracle recovers fractions to near machine precision. That verifies the algebraic solver/mixture control; failure with a candidate library cannot simply be blamed on the solver. The oracle cannot be deployed and does not validate physical mixing or purity.

### Uncertainty and domain scope

Paired bootstrap draws resample whole target parent bundles, retaining matching method errors. Report per-target intervals against MESMA and the no-spectrum prior. New-parent, held-site, global-year and complete-pair temporal targets remain distinct; the same identities across paired target years are not independent replicates.

### The most important new adverse test

The main ridge uses all 120 proper parents but MESMA retains 15 candidates from that pool. The new fairness control uses exactly those 15 saved MESMA parents to train ridge, with the unchanged tuning/target sets. Its failure materially limits an intrinsic ridge-versus-MESMA interpretation.

Sources: DESIGN.md; ABUNDANCE_CONTROL_DESIGN.md; prior:METHODS.md; prior:tables/abundance_parent_memberships.csv; prior:tables/oracle_solver_controls.csv; tables/same_candidate_ridge.csv

## 3. ABUNDANCE | model, prior, projection and capacity controls

Figure: F07_abundance_controls

Sources: 

## 3. ABUNDANCE | error across the supported true-fraction grid

Figure: F08_fraction_calibration

Sources: 

## 3. ABUNDANCE | presence, amount and category-specific overlap

Figure: F09_detection_and_class_links

Sources: 

## 3. ABUNDANCE | detection and conditional quantification

### Two distinct questions

Stage A tests presence using tuning-only thresholds. If every class is rejected, the existing algorithm admits its highest-scoring class; the table reports this admitted gate. Raw versus admitted decisions and detection by fraction are saved separately. Final-fraction detection uses the separate declared .10 comparison cutoff. Positive RMSE below is conditional on true presence, not on the model accepting the category. Missed low fractions and absent-category false detections must be assessed together.

### Class-level link

Across these five categories, higher held-site recognition recall is descriptively associated with lower ridge120 fraction RMSE (Spearman rho=-1.0), but low-fraction misses do not follow the same ranking. Five class means do not supply population or causal correlation evidence. Mixture ambiguity burden is the maximum feasible range of any class in mixtures containing the named class, not a class-specific uncertainty interval.

Table: DETECTION

Sources: prior:tables/abundance_model_comparison.csv; prior:tables/two_stage_presence_metrics.csv; tables/class_recognition_abundance_links.csv; tables/class_link_correlations.csv; tables/stage_A_detection_by_fraction.csv; tables/forced_presence_admission.csv

## 3. ABUNDANCE | ambiguity, reconstruction and spectral representation

Figure: F10_ambiguity_and_limits

Sources: 

## 3. ABUNDANCE | paired uncertainty against both baselines

### How to read the table

Each row is a NEON target set. Differences are ridge120 minus the named comparator, so a negative value favors ridge. Brackets are conditional 95% paired whole-bundle bootstrap intervals (999 draws), not joint family-corrected declarations. Target sets from paired years reuse parents; do not pool them as independent biological samples.

### Absolute and relative gains

For new-parent targets, mean RMSE decreases 0.143 (39.8%) relative to MESMA; held-site reduction is 0.093 (25.6%). These are gains for the configured unequal-capacity benchmark, not intrinsic method superiority.

### Negative controls matter

Global-year mean ridge error 0.311 exceeds the no-spectrum prior 0.309. Same-candidate ridge15 NEON error is 0.365/0.387, so the full-parent gains cannot be generalized to equal retained training diversity.

Table: PAIRED

Sources: tables/abundance_paired_vs_baselines.csv; tables/abundance_domain_summary.csv; tables/same_candidate_ridge.csv

## 3. ABUNDANCE | validation checklist

Table: ABUNDANCE

Sources: tables/design_validation.csv

## 3. ABUNDANCE | limiting factors and evidence statement

### WHAT WE CAN ESTIMATE

Known algebraic researcher-category weights in this finite-parent synthetic benchmark; these are not independently measured field fractions.

### HOW ACCURATELY

Full-parent ridge120 mean RMSE is 0.216 for new parents and 0.269 for held sites. Class-specific biases, false detections and low-fraction misses remain substantial.

### WHERE IT TRANSFERS

Some sampled held-site and paired acquisition-year targets retain useful conditional skill. This does not establish performance in arbitrary regions or years.

### WHERE IT FAILS

Global-year mean fails the no-spectrum prior, same-candidate NEON ridge loses its original advantage, and derivatives worsen the main results. Do not select a winner solely from one favorable mean.

### WHETHER THE INVERSION IS UNIQUE

Not established. Alternative candidate compositions can fit nearly equally well even when expected fraction error is reduced. Learned priors can improve prediction without removing non-uniqueness.

### WHAT IS STILL REQUIRED FOR FIELD ABUNDANCE

Independent contemporaneous field fractions at aligned spatial support, validated annotation/material purity and reflectance units, real mixing/nonlinearity checks, and broader site/year external targets. More mixtures from the same parents do not fill these gaps.

Table: LIMITING

Sources: tables/abundance_domain_summary.csv; tables/same_candidate_ridge.csv; prior:tables/abundance_by_ambiguity.csv; prior:tables/abundance_model_comparison.csv

## FINAL EVIDENCE LADDER

### LIMITATIONS

The dataset was repeatedly explored before these experiments. Nested splitting protects within-experiment tuning, not all design adaptation to known data. Only three sites and one repeatedly sampled site are available; site/year/class/acquisition effects are not fully crossed. Distinct polygons can be spatially correlated. Retrospective annotations do not certify biological persistence or purity.

### Do not collapse the ladder

A significant distributional contrast is not reliable individual recognition; recognition is not unique inversion; low synthetic fraction error is not independent field-cover validation. The four levels retain separate statuses and evidence.

Table: LADDER

Sources: tables/evidence_ladder.csv; tables/adversarial_validation.csv

## WHAT DATA SHOULD BE COLLECTED NEXT

### 1. Independent field fraction targets

Collect contemporaneous fractional cover for all five categories at explicitly matched footprint/PSF support, including true zeros, small fractions, intermediate and near-pure cases. Hold these plots out from all library selection, model development and calibration. Include repeated human/measurement uncertainty.

### 2. Verify physical reference meaning

Document reflectance scaling/units, radiometric lineage, spatial support and parent-material/category purity. Synthetic convolution from the same reference cannot establish satellite/drone interchangeability or certify physical endmembers.

### 3. Separate geography from time

Add balanced category samples across multiple new regions and years, with independently repeated biological annotations and acquisition metadata. Use spatially separated or buffered targets to test residual neighborhood dependence.

### 4. Target known failures

Oversample independently verified Woody shrub versus Herbaceous/Deciduous overlaps; include varied within-category conditions and mixed backgrounds. Assess absent-category false detections and low-fraction misses independently of the comparison cutoff.

### 5. Freeze the next validation protocol

Before collecting/evaluating the new targets, fix models, training-library capacity, fraction priors, spatial aggregation, missingness rules, sensor construction, detection/quantification criteria and acceptable uncertainty. Treat current thresholds and data-dependent discoveries as hypothesis-generating.

Sources: NEXT_DATA_NEEDED.md; tables/adversarial_validation.csv

## REPRODUCIBILITY

### Canonical inputs and preserved history

The supplied polygon Parquet is read in place. No source spectral dataset was copied. The sealed P129 packet and its previous report remain immutable; its 196 owned files are checked before/after. All new scientific grouping uses cover_category only.

### New analysis protocol

DESIGN.md fixes random/PCA/temporal controls; ABUNDANCE_CONTROL_DESIGN.md records the later hostile-review fairness addition before its evaluation. Fixed seeds, split memberships, feature paths, inner scores, model parameters, target contributions and per-case hashes are saved. This is a documented exploratory reanalysis, not retrospective preregistration.

### Numerical reproduction

run_controls.py and run_candidate_control.py are restart-safe. validate_controls.py independently reconstructs all saved classification predictions and inner groups; validate_candidates.py uses independent ridge normal equations. synthesize.py checks every canonical abundance evaluation against saved truth; no model is accepted solely from a summary CSV.

### Figures and report

Ten figure families have PNG/PDF/SVG exports. Every caption states how to read it, what is learned and what remains uncertain. figure_manifest.json lists exact numerical sources/hashes. report_source.json and report_source.md are editable; build_report.py renders from saved sources without refitting. Final geometry, rendered-page review, source hashes and deterministic rebuilding are recorded.

### Interpretive traceability

tables/design_validation.csv contains every requirement and its PASS/FAIL/NOT TESTABLE result. tables/adversarial_validation.csv records the hostile review. tables/claim_registry.csv maps key quantitative claims to their exact source filters. tables/evidence_ladder.csv keeps four scientific evidence levels separate.

Sources: README.md; VALIDATION.md; control_validation.json; candidate_validation.json; synthesis_validation.json; figure_manifest.json; tables/claim_registry.csv

## Adversarial validation appendix | 1-7

### Hostile-review rule

Each major claim must survive its plausible alternative explanations. FAIL explicitly preserves a failed interpretation; it does not disappear because other tests passed. NOT TESTABLE identifies missing evidence rather than an invented substitute.

Table: ADVERSARIAL:0

Sources: tables/adversarial_validation.csv

## Adversarial validation appendix | 8-14

### Hostile-review rule

Each major claim must survive its plausible alternative explanations. FAIL explicitly preserves a failed interpretation; it does not disappear because other tests passed. NOT TESTABLE identifies missing evidence rather than an invented substitute.

Table: ADVERSARIAL:7

Sources: tables/adversarial_validation.csv

## Adversarial validation appendix | 15-19

### Hostile-review rule

Each major claim must survive its plausible alternative explanations. FAIL explicitly preserves a failed interpretation; it does not disappear because other tests passed. NOT TESTABLE identifies missing evidence rather than an invented substitute.

Table: ADVERSARIAL:14

Sources: tables/adversarial_validation.csv

