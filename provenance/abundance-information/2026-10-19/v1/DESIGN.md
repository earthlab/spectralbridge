# Planned abundance-identifiability versus spectral-information experiment

**Not executed.** Source scaling is unresolved; the user's section-15 stop rule
has been invoked. This file fixes the intended design for resumption, not results
or preregistration. The data have already undergone extensive exploration.

Primary labels are solely the five recorded `cover_category` classes, ordered:
Deciduous; Evergreen; Herbaceous; Non-vegetated & dead; Woody shrub. They are not
certified pure materials. Field fractional cover is not established.

Preserve the existing parent-disjoint abundance design: 24 proper-training
bundles, 8 tuning bundles and up to 12 test bundles per existing supported fold,
one distinct GlobalID per category per bundle, globally disjoint roles. Preserve
the existing 170 pair/triple-grid mixture recipes per bundle. Same parent IDs,
role/domain assignments, fractions and target recipes across representations.
Record existing new-parent and held-site folds without drawing new targets for
each budget. Do not substitute the separate 603-reference/360-target OLI-only
experiment for this design or treat those benchmarks as directly equivalent.

Planned NEON feature budgets: 1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 75, 100 and all
validated retained coordinates. Existing common support is reported as 360
corrected coordinates after atmospheric/incomplete-coordinate exclusion; verify
ordered wavelengths and saved support/masks before fitting. Greedy complementary
wavelength selection uses proper-training parents only. Use five deterministic
label-independent random paths, nested across budgets, with no best-seed choice.
PCA, if included, uses matched supported dimensionality with proper-only fitting;
PCA coordinates are statistical dimensions, not physical sensor bands.

Full NEON and coordinate subsets use observed valid source support. Reduced
physical response representations may use only authoritative available response
definitions; record coefficients/backend and exact support, not rounded exported
band names. Synthetic OLI is a same-source representation, never independent
Landsat validation. MicaSense physical identities are already documented unresolved
and must not be guessed. Broader-band experiments are contingent on auditable
actual response definitions. Do not silently convolve hierarchical medians and
claim equivalence to the existing median-of-convolved-products path.

Freeze training library capacity, model families, projection rules and tuning
grid across budgets. Record raw and projected ridge fractions, finite-library
MESMA solutions, no-spectrum proper-training mean and a known-parent numerical
control. Recognition uses one fixed existing classifier/tuning rule, not an
additional model contest. One-band geometry needs explicit numerical support.

Measure separately:

1. Recognition BA, recall/confusion and held-site penalty on independent parents.
2. Pooled/class fraction RMSE, bias, MAE, calibration, absent-class false detection
   and low-fraction miss rates on the exact fixed synthetic mixtures.
3. Reconstruction RMSE in explicitly declared per-representation geometry, plus
   a common reference-space diagnostic where scientifically justified. Raw RMSEs
   from different units or coordinate weights are not directly comparable.
4. Restricted candidate-composition ambiguity, tolerance sensitivity and wrong-
   category alternatives. State whether a result retains one winner per category
   set or evaluates a broader feasible set. Use training-only tolerance scaling;
   representation geometry and scale affect a fixed numerical tolerance.

Uncertainty resamples independent test-parent bundles jointly across budgets and
methods. Report fold/domain values; generated mixture rows are not independent
biological replication. Overlapping folds do not create independent regions.

Planned figures: recognition versus budget; fraction RMSE versus budget and
prior; restricted ambiguity versus budget; reconstruction versus fraction error;
training-selected wavelength frequencies on supported VIS/red-edge/NIR/SWIR
coordinates. Cornflower blue may encode the main selected-wavelength result;
category colors encode categories only. Every caption explains observation,
interpretation and limits. No minimum-band threshold will be imposed.

The formal layer establishes conditional mixture preservation and counterexamples
to inverse identifiability after reduction. The experiment would locate empirical
losses within this observed library. Lean does not prove biological mixing,
correct units, label purity, transferability or measured field abundance.
