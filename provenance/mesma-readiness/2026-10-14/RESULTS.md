# Executive scientific answer: is the library ready for MESMA?

**Conditionally useful for spectral/mixture diagnostics; NOT operationally validated for material abundances.** Existing spectral separation is not mixture identifiability. Composite endmembers, convex ambiguity, held-out fraction errors, background gaps, unverified per-source scales and absent independent fractions prevent a defensible operational pass. This is a negative/qualified readiness result, not a recommendation to run all spectra through a raster solver.

## 1. Which material classes are supported?

Researcher Deciduous/Evergreen/Herbaceous/Woody shrub/Non-vegetated & dead and five inferred PFTs support labelled-library tests. Rock, Bare and some dead standing/downed classes have explicit subcategory annotations and bounded tests. Those are canopy/background proxies, not verified pure endmembers. MATERIAL_CLASS_AUDIT documents counts and rare/incomplete tags. Green vegetation versus soil/shade material fractions are not yet validated.

## 2. Which distinguishable classes are mixture-ambiguous?

| scheme | sensor | mean_class_ambiguity_rate |
| --- | --- | --- |
| inferred_pft | NEON | 0.712 |
| inferred_pft | OLI | 0.700 |
| material | NEON | 0.812 |
| material | OLI | 0.794 |
| researcher | NEON | 0.723 |
| researcher | OLI | 0.725 |

These are mean class ambiguity rates in held-out plant folds at relative tolerance 0.01, with correct candidate and other-class convex fits. Class-specific combinations and tolerance sensitivities are retained. Strong historical DBS-ECT/DBT-ECT significance does not eliminate convex overlap; weak DBT-ECS is not treated as an interchangeable material merely because an old test failed.

Selector sensitivity on the SAME plant folds, using at most TWO other materials and a common tolerance of 0.01:

| scheme | sensor | selection | ambiguity_rate |
| --- | --- | --- | --- |
| inferred_pft | NEON | EAR | 0.713 |
| inferred_pft | NEON | MASA | 0.708 |
| inferred_pft | NEON | all_proposed_candidates | 0.908 |
| inferred_pft | NEON | medoid | 0.664 |
| inferred_pft | OLI | EAR | 0.699 |
| inferred_pft | OLI | MASA | 0.694 |
| inferred_pft | OLI | all_proposed_candidates | 0.860 |
| inferred_pft | OLI | medoid | 0.643 |
| material | NEON | EAR | 0.812 |
| material | NEON | MASA | 0.860 |
| material | NEON | all_proposed_candidates | 0.906 |
| material | NEON | medoid | 0.759 |
| material | OLI | EAR | 0.791 |
| material | OLI | MASA | 0.839 |
| material | OLI | all_proposed_candidates | 0.920 |
| material | OLI | medoid | 0.746 |
| researcher | NEON | EAR | 0.720 |
| researcher | NEON | MASA | 0.736 |
| researcher | NEON | all_proposed_candidates | 0.835 |
| researcher | NEON | medoid | 0.651 |
| researcher | OLI | EAR | 0.722 |
| researcher | OLI | MASA | 0.735 |
| researcher | OLI | all_proposed_candidates | 0.826 |
| researcher | OLI | medoid | 0.649 |

More proposed candidates improve own-class coverage but also create more wrong-class convex combinations. This check does not use the test data for selection. It guards against blaming intrinsic material physics for one EAR/shade-aware prototype choice. Candidate budget and model assumptions still limit generalization.

Class-specific inferred-PFT ambiguity (pooled held-out polygon-year records across three plant folds):

| sensor | label | ambiguity_rate | median_correct_class_RMSE | median_incorrect_RMSE |
| --- | --- | --- | --- | --- |
| NEON | DBS | 0.920 | 0.376 | 0.081 |
| NEON | DBT | 0.948 | 0.719 | 0.092 |
| NEON | EBS | 0.114 | 0.123 | 0.293 |
| NEON | ECS | 0.767 | 0.204 | 0.140 |
| NEON | ECT | 0.809 | 0.270 | 0.183 |
| OLI | DBS | 0.920 | 0.289 | 0.062 |
| OLI | DBT | 0.944 | 0.559 | 0.086 |
| OLI | EBS | 0.089 | 0.097 | 0.245 |
| OLI | ECS | 0.767 | 0.161 | 0.110 |
| OLI | ECT | 0.778 | 0.196 | 0.139 |

## 3. Which classes are inadequately sampled?

Dead - Debris has one identity; dead herbaceous is rare/incompletely annotated; named taxa have severe long tails; some PFTs are species-confounded. Rare/missing class/fold cells stay insufficient, never merged to inflate performance. Some year-transfer directions have no disjoint training support. See original material counts and fold_support.csv.

## 4. Missing backgrounds?

No verified pure soil, litter, water, snow or measured shade classes. Bare is not proof of soil, and shaded polygons are not shade endmembers. Broad Non-vegetated & dead combines disparate materials.

## 5. How many endmembers before a plateau?

Not established. Optimization probes 1,2,5,10 entries within up to 12 proposed training identities/class. Larger 20/50/100 trials are explicitly outside this budget; nearest-neighbor accumulation separately extends up to 500 where support allows. A bounded curve cannot identify a universal optimal count, and adding candidates can increase mixture ambiguity. library_size_fraction_recovery.csv measures this directly on the same mixtures at 1/2/5/10 entries where exact model counts permit.

| scheme | sensor | requested_per_class | fraction_RMSE |
| --- | --- | --- | --- |
| inferred_pft | NEON | 1 | 0.376 |
| inferred_pft | NEON | 2 | 0.344 |
| inferred_pft | NEON | 5 | 0.325 |
| inferred_pft | NEON | 10 | 0.290 |
| inferred_pft | OLI | 1 | 0.360 |
| inferred_pft | OLI | 2 | 0.351 |
| inferred_pft | OLI | 5 | 0.326 |
| inferred_pft | OLI | 10 | 0.294 |
| material | NEON | 1 | 0.304 |
| material | NEON | 2 | 0.292 |
| material | NEON | 5 | 0.273 |
| material | OLI | 1 | 0.302 |
| material | OLI | 2 | 0.291 |
| material | OLI | 5 | 0.279 |
| researcher | NEON | 1 | 0.384 |
| researcher | NEON | 2 | 0.380 |
| researcher | NEON | 5 | 0.310 |
| researcher | NEON | 10 | 0.306 |
| researcher | OLI | 1 | 0.387 |
| researcher | OLI | 2 | 0.380 |
| researcher | OLI | 5 | 0.317 |
| researcher | OLI | 10 | 0.309 |

## 6. Best selection method on held-out data?

| scheme | sensor | method | fraction_RMSE |
| --- | --- | --- | --- |
| inferred_pft | NEON | random_MESMA3 | 0.323 |
| inferred_pft | OLI | random_MESMA3 | 0.324 |
| material | NEON | CoB_MESMA3 | 0.281 |
| material | OLI | CoB_MESMA3 | 0.282 |
| researcher | NEON | MASA_MESMA3 | 0.341 |
| researcher | OLI | diversity_MESMA3 | 0.332 |

These are descriptive winners for the declared bounded pool and controlled plant folds, not globally selected operational methods. Three plant folds and one seeded proposed pool do not identify a generally superior selector. Acquisition-stress variants have different targets and are excluded from this ranking. No held-out result was used to choose candidates or change thresholds. IES training kappa need not optimize fractions or retain rare classes.

## 7. Known-fraction recovery?

| scheme | sensor | fraction_RMSE | fraction_MAE | class_set_error |
| --- | --- | --- | --- | --- |
| inferred_pft | NEON | 0.344 | 0.215 | 0.888 |
| inferred_pft | OLI | 0.351 | 0.222 | 0.867 |
| material | NEON | 0.292 | 0.166 | 0.947 |
| material | OLI | 0.291 | 0.165 | 0.938 |
| researcher | NEON | 0.380 | 0.255 | 0.904 |
| researcher | OLI | 0.380 | 0.252 | 0.878 |

EAR_MESMA3 values are macro means of class/fold fraction RMSE/MAE, in fraction units (0.10 = ten percentage points). Truth consists of algebraic weights on held-out COMPOSITE polygon curves. Synthetic success would not establish actual cover accuracy; the observed errors are already substantial for many labels. Class-specific material results:

| sensor | label | fraction_RMSE | fraction_MAE |
| --- | --- | --- | --- |
| NEON | Bare | 0.235 | 0.105 |
| NEON | Dead - Woody downed | 0.269 | 0.131 |
| NEON | Dead - Woody standing | 0.464 | 0.353 |
| NEON | Deciduous | 0.270 | 0.135 |
| NEON | Evergreen | 0.260 | 0.170 |
| NEON | Herbaceous | 0.276 | 0.148 |
| NEON | Rock | 0.271 | 0.138 |
| NEON | Woody shrub | 0.293 | 0.151 |
| OLI | Bare | 0.223 | 0.098 |
| OLI | Dead - Woody downed | 0.282 | 0.138 |
| OLI | Dead - Woody standing | 0.462 | 0.350 |
| OLI | Deciduous | 0.264 | 0.125 |
| OLI | Evergreen | 0.265 | 0.174 |
| OLI | Herbaceous | 0.272 | 0.141 |
| OLI | Rock | 0.270 | 0.140 |
| OLI | Woody shrub | 0.290 | 0.153 |

## 8. False positives and false negatives?

| scheme | sensor | macro_FPR_true_zero | macro_FNR_true_0.2 | macro_FNR_true_0.5 | macro_FNR_true_1 |
| --- | --- | --- | --- | --- | --- |
| inferred_pft | NEON | 0.320 | 0.561 | 0.473 | 0.383 |
| inferred_pft | OLI | 0.324 | 0.626 | 0.458 | 0.383 |
| material | NEON | 0.230 | 0.654 | 0.531 | 0.452 |
| material | OLI | 0.223 | 0.671 | 0.576 | 0.435 |
| researcher | NEON | 0.286 | 0.599 | 0.531 | 0.500 |
| researcher | OLI | 0.277 | 0.557 | 0.561 | 0.517 |

Values are macro class/fold conditional frequencies on controlled mixtures, not field error probabilities.

Detection rule estimated fraction >=0.10 was declared before testing; 0.05/0.20 sensitivities are included. detection_errors.parquet reports per-fraction false-positive rates at true zero and false-negative rates at positive truth, with exact simulation denominators. They depend strongly on hierarchy, component and fraction; no single biological FPR/FNR is justified. Reused source parents invalidate treating all gradient points as independent field samples.

## 9. Reliable abundance detection thresholds?

No defensible population 50/80/95% threshold. Figure 4 shows conditional curves. Three plant folds and one parent set per composition provide too little independent replication, and the sources are not verified pure materials. A nominal detection at one simulation fraction is not a calibrated ecological detection limit.

## 10. NEON to OLI loss?

The table above and paired sensor_comparison.csv use the same parents, fractions and candidate identities. Interpret OLI-minus-NEON fraction RMSE within exact class/fold pairs, not the previous 15/16 biological-test retention statistic. Both sensors can be ambiguous; little additional spectral loss does not mean either recovers fractions well. Weighting differs by declared spectral support. This is synthetic reduction, not independent satellite abundance validation.

## 11. Does MESMA outperform FCLS?

method_comparison.csv compares EAR-limited two/three-component variable candidates with fixed class-medoid FCLS on identical mixtures. Performance is hierarchy-dependent. Extra spectral flexibility does not consistently guarantee lower fraction error, and minimal spectral residual is not a fraction-accuracy selector. No universal MESMA advantage is established.

| scheme | sensor | EAR_MESMA3 | FCLS_medoid | MESMA3_minus_FCLS | MC_mean_FCLS | MC_minus_FCLS |
| --- | --- | --- | --- | --- | --- | --- |
| inferred_pft | NEON | 0.344 | 0.366 | -0.022 | 0.281 | -0.085 |
| inferred_pft | OLI | 0.351 | 0.364 | -0.013 | 0.277 | -0.088 |
| material | NEON | 0.292 | 0.295 | -0.003 | 0.233 | -0.062 |
| material | OLI | 0.291 | 0.295 | -0.004 | 0.234 | -0.061 |
| researcher | NEON | 0.380 | 0.342 | 0.037 | 0.279 | -0.063 |
| researcher | OLI | 0.380 | 0.345 | 0.035 | 0.279 | -0.066 |

## 12. Does Monte Carlo help?

MC_mean_FCLS is evaluated on the same sources; uncertainty tables show its fraction errors, empirical width and conditional truth coverage. An ensemble can stabilize some estimates, but empirical 95% intervals are not assumed calibrated. Twelve endmember draws cannot justify tail-probability claims or resolve unobserved materials. The ensemble improves macro fraction RMSE in this benchmark but often increases thresholded class-set error by distributing fractions across absent classes; it is not an unqualified improvement in material detection.

## 13-15. Flight, year and site transfer?

TRANSFERABILITY.md and transferability_summary.csv give class/fold error distributions, support and exact source memberships. All actual flight holdouts were considered; rare/absent class cases remain explicit. Actual flight spectra are used as targets, and repeated IDs are purged globally. Year/site shifts alter class/taxon composition and candidate availability; no isolated environmental penalty is inferred. Repeated NIWO years never count as geographic replication. Unsupported reverse-year directions do not become optimistic estimates.

## 16. Correct material absent?

| scheme | sensor | known_false_alarm | unknown_flag_rate |
| --- | --- | --- | --- |
| inferred_pft | NEON | 0.693 | 0.401 |
| inferred_pft | OLI | 0.661 | 0.362 |
| material | NEON | 0.721 | 0.421 |
| material | OLI | 0.727 | 0.449 |
| researcher | NEON | 0.836 | 0.657 |
| researcher | OLI | 0.802 | 0.623 |

These are pure nominal-label missing-class diagnostics against training-only thresholds. Wrong classes can fit well; acceptance does not establish presence. unknown_model_status.parquet restores source year from the exactly matching pure-target ledger and explicitly marks NO_ADEQUATE_LIBRARY_MODEL or LOW_RESIDUAL_NOT_VALIDATED_MEMBERSHIP, not a forced operational class. The rates are descriptive repeated-record frequencies, not calibrated field probabilities. Partly unknown mixtures and new background types need additional validation.

## 17. Detect unreliable estimates?

unreliable_fraction_flags.csv reports the fraction of poor estimates hiding below three residual tolerances and sensitivity of a near-model fraction-range flag. Small residual is insufficient. Model-choice ranges and empirical bundles help expose instability but miss within-composition/unsampled variability. No validated operational rejection algorithm is claimed.

## 18. Applications supported now?

Stored-library QC, labelled material/PFT variability, conditional same-library spectral comparisons, controlled linear-mixture geometry and paired spectral-resolution diagnostics. These are exploratory analyses, not calibrated abundance products.

## 19. Applications not supported?

Real vegetation/background/species cover maps, calibrated uncertainty/detection limits, universal cross-site/year fraction transfer, unlabelled-landscape completeness, real Landsat abundance maps and subtle abundance change detection. Independent REAL ABUNDANCE VALIDATION = NOT YET AVAILABLE.

## 20. Exact work before operational MESMA?

Recover per-flight metadata and processing provenance; audit purity and dated labels; reconcile backgrounds; add missing pure materials and rare independent identities; obtain complete co-registered independent fractions; validate larger nested libraries and source-parent replication; calibrate uncertainty/abstention; separate spectral from actual spatial-support effects and validate real sensors across independent acquisitions. No global coefficient or BRDF/SRF change was made to improve this audit.

## Defensible manuscript statement

"In identity-disjoint controlled mixtures constructed from the current 3,639-identity SpectralBridge library, the tested candidate/model sets showed substantial other-class convex overlap. With two EAR-selected candidates per class and at most three nonnegative, sum-one material components, macro class/fold fraction RMSE was 0.344 for inferred PFTs and 0.380 for researcher categories in corrected NEON space, versus 0.351 and 0.380 in paired synthetic OLI space. Larger candidate sets and alternative selectors changed performance but did not establish operational abundance readiness. These simulations use empirical composite polygon curves; unverified source-scale/purity information and unavailable independent fractional-cover truth preclude a claim of field abundance accuracy."

## Final operational readiness matrix

| material | NEON | Landsat_like |
| --- | --- | --- |
| Green vegetation | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Deciduous | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Evergreen | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Herbaceous | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Woody shrub | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| NPV/dead | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Rock | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Bare | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Soil | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Water | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Snow | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Measured shade | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |
| Species-level | INSUFFICIENT EVIDENCE | INSUFFICIENT EVIDENCE |

Each cell lacks independently validated material fractions and source/purity completeness. This does not mean all spectral comparisons are impossible. It means the current evidence does not justify operational ecological abundance claims. Ten separate dimensions are recorded in readiness_dimensions.csv; there is no opaque combined score.
