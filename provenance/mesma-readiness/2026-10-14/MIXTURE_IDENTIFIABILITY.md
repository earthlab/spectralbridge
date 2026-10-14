# Mixture identifiability

Held-out spectra bearing class C are compared with the best single same-class candidate and the best sum-one, nonnegative convex model with up to three OTHER classes. The wrong model includes all two-class and singleton faces. Both primary comparisons are no-shade models; the directed EAR-style confusion table separately and explicitly includes ideal black shade. Nominal C purity is not independently verified, so these are tests of the labelled library's geometry, not proof that true pure C can or cannot be identified.

| scheme | sensor | mean_class_ambiguity_rate | heldout_records |
| --- | --- | --- | --- |
| inferred_pft | NEON | 0.712 | 2659 |
| inferred_pft | OLI | 0.700 | 2659 |
| material | NEON | 0.812 | 4680 |
| material | OLI | 0.794 | 4680 |
| researcher | NEON | 0.723 | 4807 |
| researcher | OLI | 0.725 | 4807 |

A wrong reconstruction is ambiguous when its RMSE <= own-candidate RMSE + tolerance. Sensitivities 0.005,0.01,0.02 are fractions of a training-only RMS magnitude, not universally meaningful physical noise thresholds. Class ambiguity is additionally affected by poor own-class representativeness and asymmetric model capacity (one same-class prototype versus a convex combination of other classes). The selector/pool sensitivity table tests this dependence explicitly; the result is conditional on the specified library/model, not a proof of intrinsic physical non-identifiability. Exact errors and their signed gap, best wrong composition, near-composition counts, and original memberships are retained. Near-composition counts exclude zero-fraction additions: adding a material with fraction zero is not a new composition.

near_fraction_range spans the best model within each near-equivalent class set; it does not enumerate all endmember-choice variants within the same class set and is a LOWER-BOUND stability diagnostic. Monte Carlo separately probes empirical endmember choice. Different class means or previous permutation significance do not rule out convex overlap. MIXTURE_AMBIGUITY_MATRIX.csv exposes the masquerading class combinations. Missing-class tests in unknown_detection.parquet remove the entire nominal class and compare errors against training-only same-class thresholds; the main unknown test is the 100%-class endpoint, not an exhaustive contaminated-mixture OOD study.
