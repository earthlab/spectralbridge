# Researcher-category publication figures

## R01_researcher_category_overview

A: full-cohort acquisition-matched descriptive effects, not Cohen d. B: nested full-spectrum logistic class recall. Five recorded classes only; within-class spread and domain dependence remain.

Sources: cohort_wavelength_inference.csv, class_specific_transfer.csv

## R02_wavelength_effect_and_support

A: full-cohort descriptive effects. B: training-only max-T and within-design Bonferroni support in eight outer-training designs, which overlap and are not independent replications. No inference map selects predictive features. Triangles/short bars mark configured OLI centers/FWHM. Visible <700; red edge 700-750; NIR 750-1340; SWIR1 1450-1790; SWIR2 2000-2510 nm.

Sources: researcher_pft_information_atlas.csv

## R03_single_wavelength_prediction

Balanced-prior univariate LDA; direction and threshold trained without target identities. Mean versus weakest-site performance are different views. These are estimates for one rule, not a theoretical information bound.

Sources: single_wavelength_discrimination.parquet, researcher_pft_information_atlas.csv

## R04_spectral_curves_colored_by_discrimination

Four declared illustrations; all ten pairs are in the atlas. Effect height describes matched group differences; color describes a separate held-site predictor. Segments do not cross atmospheric gaps.

Sources: researcher_pft_information_atlas.csv

## R05_class_recall_across_wavelengths

Prespecified five-class balanced-prior nearest-mean discriminant. A single coordinate can separate two classes yet confuse the five-way classification. This differs from pairwise balanced accuracy and full-spectrum logistic recall.

Sources: single_wavelength_class_recall.csv

## R06_site_year_stability

Score=max(0,2*minimum held-site BA-1) times cohort sign consistency. It is a review aid over three observed sites. Temporal changes preserve target identities; annotations are reused later field labels. No geographic-population or annual-truth guarantee.

Sources: researcher_pft_information_atlas.csv, domain_rank_consistency.csv

## R07_complementary_measurement_budgets

All selection and C tuning refit inside group-aware inner folds. Correlation panel compresses unsupported gaps in its coordinate index and interpolates no missing channel. The greedy residual criterion seeks complementary information; it is not an optimized sensor.

Sources: complementary_feature_performance.csv, complementary_selection.csv, training_correlation_clusters.csv

## R08_NEON_to_synthetic_Landsat

Identical class labels and paired source observations. OLI spectral convolution is synthetic, at native/polygon support; it does not supply independent sensor noise, a 30 m footprint or field validation.

Sources: complementary_feature_performance.csv, reused_researcher_sensor_effect_retention.csv

## R09_abundance_model_benchmark

Solid bars: NEON; pale bars: OLI. Dots are outer folds, not independent fraction levels. All methods use identical parent-disjoint targets; 120 proper and40 tuning parents per fold, up to60 test parents. These are synthetic weights, not field cover.

Sources: abundance_model_comparison.parquet, abundance_paired_uncertainty.csv

## R10_predicted_vs_known_fraction

Curves average the three new-polygon folds; complete grids for all methods/domains are saved. At true zero, positive detection is false detection. The .10 cutoff is declared, not a universal detection limit. Mixtures sharing parents are dependent.

Sources: abundance_by_true_fraction.csv

## R11_detection_vs_known_fraction

Curves average the three new-polygon folds; complete grids for all methods/domains are saved. At true zero, positive detection is false detection. The .10 cutoff is declared, not a universal detection limit. Mixtures sharing parents are dependent.

Sources: abundance_by_true_fraction.csv

## R12_abundance_error_and_ambiguity

Strata are shared across every method, using full-NEON MESMA near solutions within .01 training-RMS-scaled tolerance. Missing strata are unsupported. This diagnoses a candidate-library inverse problem, not intrinsic physical ambiguity or calibrated intervals.

Sources: abundance_by_ambiguity.csv

## R13_abundance_domain_transfer

Global year holds alter site composition. Paired NIWO directions reuse the same held-out target IDs/fractions in both years, with other IDs for proper/tuning pools. Annotation labels are retrospective. Each cell is conditional on sampled parent bundles.

Sources: abundance_model_comparison.parquet

## R14_final_researcher_evidence

Evidence status is use-specific, not an aggregate score. Lowest observed outer score is descriptive, not a tuning choice or multiplicity-corrected winner. No synthetic success is promoted to field abundance validation.

Sources: final_evidence_summary.csv
