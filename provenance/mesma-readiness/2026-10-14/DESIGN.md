# MESMA readiness design, fixed before mixture results

This is an exploratory readiness audit, not confirmation of plot-driven hypotheses. Keep spectral separability, convex-mixture identifiability, known-fraction recovery and transferable ecological fractions separate. Existing PFT permutation results are context, never mixture validation. No single readiness score.

## Evidence and blocking gates

Reuse verified compact plant/flight and paired polygon/year tables from P120; source is read in place. All metadata labels are audited against the original Parquet. Atmospheric masks [1340,1450] and [1790,2000] nm and maximum interpolation gap 8 nm are inherited unchanged. Never use the 1,140-column union as one spectrum. Corrected NEON and seven undarkened OLI bands are primary; MicaSense remains physically unvalidated.

Blocking for operational abundance inference: no verified per-flight source headers/scale metadata for this merged library, no endmember-purity measurements, no independent fractional-cover truth, incomplete physical backgrounds. The real R10C pilot does not establish those facts for NIWO/WREF/YELL. STOP the physical/operational claim at these gates. Conditional, common-scale-invariant synthetic geometry can still be tested, with stored units explicitly retained and RMSE normalized by a training-only scalar. Never call that normalized number unitless reflectance or ecological abundance accuracy.

Material inventories use existing species, inferred PFT, cover_category and original cover_subcategory/dead_subcategory. Bare is not automatically labelled soil; shaded is illumination metadata, not a measured shade endmember; mixed backgrounds remain mixed. No artificial taxonomy relabeling or spectrum-based truth.

## Grouped separation and controlled stages

First exercise tiny analytic examples and a representative subset spanning strong DBS/ECT, DBT/ECT, weak DBT/ECS and all researcher categories. Only after checks pass run eligible complete-library folds. Endmember selection is rerun inside every training fold. Every GlobalID used as a held-out source is absent from training in ALL years/flights. Plant folds are stratified by class/site. Flight folds remove every identity observed in the held-out flight, even where this reduces support; unsupported folds remain explicit. Site/year folds likewise purge overlapping identities. Repeated NIWO years never count as separate sites. Class absence is reported, never merged away.

Selection is deterministic training-only random, Euclidean medoid, shade-model EAR, angular MASA, marginal in-CoB with EAR ties, published add/remove kappa IES, diversity farthest-point and an explicitly labelled IES-plus-CoB completion sensitivity. Any candidate-budget restriction or size-limited adaptation is disclosed. EAR/MASA are not renamed nearest-neighbor statistics. IES chooses a training classification library, not an abundance-optimal model.

## Mixture constraints and endpoints

FCLS solves nonnegative fractions summing exactly to one. MESMA enumerates one candidate per class with up to two/three material components, explicitly including all lower-dimensional faces. Do not enumerate impossible or excessive combinations: record exact model count before allocation, a configurable maximum and runtime; cap validation-source replicates rather than silently prune model space. Optimized exhaustive projections must agree with a separate constrained optimizer on analytic random cases. Four materials are not presumed justified.

No-shade primary; black photometric shade is an explicitly IDEALIZED sensitivity, not a measured water/shadow material. Shade-normalized fractions are reported only where the non-shade sum is positive, and are distinct from total-footprint fractions. Negative corrected values remain diagnostic, not automatically nodata or silently forced positive.

Synthetic validation uses held-out empirical sources, pair fractions 0,.05,.1,.2,.3,.4,.5,.6,.7,.8,.9,.95,1 and three-component examples. Identical sources/fractions/selection IDs across NEON and OLI isolate representation loss. Primary detection rule estimated class fraction >=0.10; sensitivities .05/.20. True zero defines false positives; positive truth defines false negatives. Detection curves are conditional empirical frequencies, with denominators; do not claim 50/80/95% thresholds from a handful of dependent simulations. Mixture draws from the same source pair are not independent biological samples. Fraction MAE/RMSE/bias, class-set error, residuals, spectral angles and constraint violations are all retained.

Mixture ambiguity: held-out class spectrum modelled by its own candidates versus 2/3-class convex models excluding its class. Record errors, gap, near-equivalent class compositions and fraction stability. Tolerance sensitivities are 0.005/0.01/0.02 times training RMS spectral magnitude, with no claimed universal physical noise floor. Residual adequacy threshold is the training-only leave-identity-out 95th percentile of within-class reconstruction, not a fitted validation cutoff.

Compare MESMA with class-medoid FCLS and Monte Carlo empirical-endmember FCLS. Monte Carlo intervals describe endmember-choice stability, not calibrated confidence/posterior intervals; test conditional truth coverage. Sparse L1 penalties under nonnegative sum-one constraints are constant and cannot create sparsity; do not present that as an implemented sparse method. Sparse unmixing is explicitly deferred if no well-tested alternative is added.

Real Landsat residuals are available from one different R10C acquisition. They are context, not a general noise distribution for these sites. Use training repeat-acquisition differences only as acquisition-variability perturbations, never identify them as instrument noise. Real abundance validation stays NOT YET AVAILABLE without independent co-registered fractions.

## Readiness dimensions and reporting

Report independently: integrity, material coverage, representativeness, distinguishability, mixture identifiability, fraction recovery, transferability, sensor robustness, uncertainty calibration and computation. READY requires independent evidence for the stated application; synthetic success alone can at most support a conditional simulation experiment. Each material/sensor assessment has numbers or INSUFFICIENT EVIDENCE. Six figure families and all requested evidence documents include unsupported/blocked analyses and exact remaining work.
