## F01_foundation: The biological sampling unit is the polygon, not the pixel

HOW TO READ IT: Counts use distinct GlobalIDs. A repeated ID can occur in two acquisition-year cells. Audit FAIL refers to a tested claim failing, not a concealed pipeline error.

WHAT WE LEARN: The library has broad category coverage but only four site/year cells. The experimental independence and truth limits are explicit.

WHAT REMAINS UNCERTAIN: Polygon purity, absolute reflectance units and independent annual/field fraction truth are not verified. Distinct nearby polygons can remain spatially correlated.

Sources: tables/category_support.csv; tables/site_year_category_support.csv; foundation.json; tables/design_validation.csv

## F02_separability: Different spectra: effect size, statistical evidence and sensor retention

HOW TO READ IT: Each heatmap row is one of ten category pairs. All four cohorts remain visible. Ratios measure standardized effect retention, not prediction accuracy or a probability.

WHAT WE LEARN: All ten whole-spectrum contrasts are supported in the four observed cohorts after declared blocked permutation correction. Effect magnitude and OLI retention vary by pair/domain.

WHAT REMAINS UNCERTAIN: Absolute physical units remain unresolved. Convolution can smooth within-class variability, so a standardized effect ratio above one is possible. Synthetic OLI is not independent Landsat evidence.

Sources: tables/whole_spectrum_separability.csv; tables/pair_support_and_evidence.csv; tables/region_separability.csv

## F03_wavelength_separability: Wavelength-level differences retain their domain context

HOW TO READ IT: Top: signed matched effect, class A minus B in the displayed pair. Bottom: adjusted evidence; 1.30 corresponds to p=.05. Grey intervals are masked gaps. Color limits bound display only.

WHAT WE LEARN: Many broad regions are supported, but sign/magnitude/rank stability is pair- and domain-dependent. All coordinates share whole-curve permutation shuffles; adjacent channels are not independent tests.

WHAT REMAINS UNCERTAIN: The lower map is evidence against exchangeability, not an effect confidence interval. Full-cohort maps are descriptive and never used to select predictive features. Null standard errors and every unbounded effect are saved.

Sources: prior:tables/cohort_wavelength_inference.csv; tables/wavelength_effect_stability.csv; tables/wavelength_null_uncertainty.csv; prior:tables/domain_rank_consistency.csv

## F04_single_coordinate_recognition: Statistical differences do not guarantee individual recognition

HOW TO READ IT: Left is a five-class problem (chance BA=.20); shaded ranges are observed outer-fold ranges. Right contains ten separate binary problems (chance=.50). No coordinate is chosen using these test scores.

WHAT WE LEARN: Single-coordinate five-class recognition is limited. Herbaceous versus Woody shrub remains especially weak under the fixed pairwise rule despite supported differences.

WHAT REMAINS UNCERTAIN: This tests specified mean-based rules, not all possible nonlinear classifiers. Observed maxima are descriptive and not validated operational bands.

Sources: tables/single_coordinate_five_class.csv; tables/pairwise_single_coordinate_summary.csv

## F05_complementarity_controls: Complementary selection adds value, but random bands can catch up

HOW TO READ IT: Selected and random subsets use identical inner folds and tuning grids. Five fixed random paths are averaged; shaded envelopes include seed/fold variation, not confidence intervals. PCA uses every input wavelength.

WHAT WE LEARN: Selected subsets improve modest-budget average recognition. The gap narrows at large budgets; two/three-band held-site controls can favor random subsets. High correlation does not make every additional band useless.

WHAT REMAINS UNCERTAIN: No seed or budget is chosen from outer scores. Five random controls do not establish an optimal selector, universal intrinsic dimension or optimized sensor. PCA fit uses annual rows within training only.

Sources: tables/recognition_control_summary.csv; tables/selected_minus_random.csv; tables/recognition_budget_increments.csv; tables/subset_redundancy.csv; prior:tables/complementary_feature_performance.csv

## F06_class_and_domain_failures: Recognition failures are class-specific and domain-dependent

HOW TO READ IT: Recall measures recovered true-category observations. Confusion rows sum to one. Paired-year targets keep the same held identities and trained model; global-year targets change site composition.

WHAT WE LEARN: Woody shrub transfers poorly relative to Evergreen/background. Controlled paired NEON recognition drops in both temporal directions and is asymmetric. OLI can be less temporally sensitive despite lower familiar-domain recognition.

WHAT REMAINS UNCERTAIN: Static retrospective annotations test footprint recognition, not annual biological truth. Three sites and one repeatedly observed site cannot isolate ecological, illumination and processing causes.

Sources: prior:tables/class_specific_transfer.csv; prior:tables/confusion_plot_values.csv; tables/temporal_recognition_summary.csv; tables/rates.csv; tables/confusions.csv

## F07_abundance_controls: Synthetic abundance gains depend on domain, priors and retained library

HOW TO READ IT: All main models see identical outer mixtures. Macro RMSE is sqrt(mean class MSE) within target then averaged across folds. The fairness control reduces ridge to the exact 15 MESMA candidates; the original ridge uses 120 parents.

WHAT WE LEARN: Ridge120 improves the primary new-parent/held-site benchmark, but fails the global-year prior on average. Ridge15 loses the NEON advantage. Projection improves error. The known-generating-parent oracle has near-zero fraction error.

WHAT REMAINS UNCERTAIN: The candidate control changes training diversity/bundle count and model prior; it does not prove a single cause. Methods are not intrinsically ranked, and these algebraic fractions are not field cover.

Sources: tables/abundance_domain_summary.csv; tables/same_candidate_ridge.csv; tables/abundance_paired_vs_baselines.csv; prior:tables/raw_prediction_constraint_diagnostics.csv; prior:tables/oracle_solver_controls.csv

## F08_fraction_calibration: Zero, low and pure-end mixtures reveal shrinkage hidden by RMSE

HOW TO READ IT: Each point averages predictions at a nominal truth-grid fraction, first count-weighting machine-precision-equivalent bins within fold, then averaging held sites. The diagonal represents unbiased mean recovery. Endpoints are synthetic pure-parent mixtures, not verified pure materials.

WHAT WE LEARN: Many methods overpredict absent categories and shrink high fractions. Similar overall RMSE can hide different class-specific biases and detection behavior.

WHAT REMAINS UNCERTAIN: Mean calibration curves hide bundle variation; paired intervals and per-fold/per-class errors remain saved. No universal field detection threshold follows from this grid.

Sources: tables/calibration_plot_values.csv; tables/fraction_grid_calibration.csv

## F09_detection_and_class_links: Recognition, false detection and quantification are different outcomes

HOW TO READ IT: Rows are researcher categories and columns are methods. False detection and low-fraction misses use the declared .10 final-fraction cutoff. The final panel shows empirical detection frequency versus truth, ridge solid and two-stage dashed. Class-level links are saved separately for all five categories.

WHAT WE LEARN: Harder-to-recognize categories also tend to have larger ridge fraction error here. False detection and missed low fractions trade off; a stronger prior can improve one while worsening the other.

WHAT REMAINS UNCERTAIN: Class-level associations are descriptive, not five independent geographic replicates. Stage-A presence metrics are separately saved; .10 is a comparison rule, not an independently validated detection limit.

Sources: prior:tables/abundance_model_comparison.csv; prior:tables/two_stage_presence_metrics.csv; tables/fraction_grid_calibration.csv; tables/class_recognition_abundance_links.csv; tables/class_link_correlations.csv

## F10_ambiguity_and_limits: Better expected fractions do not establish unique physical inversion

HOW TO READ IT: Ambiguity is maximum candidate-class fraction range among near-fitting solutions at the declared .01 tolerance. High means range >=.30. Every scatter point is one saved synthetic mixture, not an independent plant.

WHAT WE LEARN: Ridge can reduce error in high-ambiguity targets while alternatives remain feasible. The moderate stratum can favor MESMA. Spectral reconstruction is insufficient, and derivatives do not remedy the main limitations.

WHAT REMAINS UNCERTAIN: Candidate/tolerance ambiguity is not exhaustive physical uncertainty. The class burden is mixture-level ambiguity conditional on category presence. Observational data cannot uniquely apportion library variability, overlap, acquisition shift and prior effects.

Sources: prior:tables/abundance_by_ambiguity.csv; tables/reconstruction_fraction_points.parquet; prior:tables/abundance_model_comparison.csv; tables/class_recognition_abundance_links.csv
