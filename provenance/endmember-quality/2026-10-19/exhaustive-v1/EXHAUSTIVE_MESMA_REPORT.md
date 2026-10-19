# What changes when MESMA searches the entire selected library?

**Completed exhaustive internal benchmark — 19 October 2026.**

The search evaluated **16,918,447 candidate combinations for each of the same 360 synthetic targets: 6,090,640,920 target–model evaluations**. No nearest-endmember shortlist was used. The fixed library contains 603 references in five researcher-assigned categories.

The exhaustive search gave PFT fraction RMSE **0.3336**, compared with **0.3215** for the earlier three-reference-per-category screening. Mean spectral reconstruction RMSE changed from **0.003721 to 0.000792** (78.7% reduction). These measure different things: matching a spectrum and recovering its known generating fractions.

## What was tested?

Each target is a known algebraic mixture of one, two or three observed seven-band polygon spectra. There are eight disjoint parent bundles, each containing five different polygon IDs, one per category. Every bundle contributes 45 targets. Its generating parent IDs are excluded from the fixed candidate library. Targets cover four observed site–acquisition-year cells and use the exact preceding target recipes. This is synthetic linear mixing of observed spectra, not independently measured ground cover.

The library contains 115 Deciduous, 166 Evergreen, 90 Herbaceous, 141 Non-vegetated & dead and 91 Woody shrub references. MESMA chooses up to three different categories, at most one reference per category, and nonnegative fractions that sum to one. It minimizes **mean squared spectral reconstruction error**, not known fraction error. All single-reference and two-reference faces are evaluated, as well as triples. No shade or additional endmembers were introduced.

## How much does exhaustive searching help?

| Method | PFT fraction RMSE | PFT fraction MAE |
| --- | ---: | ---: |
| Exhaustive selected | 0.3336 | 0.2339 |
| Screened selected (3/category) | 0.3215 | 0.2226 |
| Screened selected (5/category) | 0.3165 | 0.2189 |
| Screened matched random (one draw) | 0.3130 | 0.2141 |
| Dense design prior | 0.3036 | 0.2489 |
| Sparse design prior | 0.3447 | 0.2560 |
| Known-parent oracle | 0.0000 | 0.0000 |

Fraction RMSE is sqrt(mean squared error over all 360 × 5 fractions); it is not the mean of 360 per-target RMSE values. Lower is better. The dense prior has five nonzero fractions and therefore a different output constraint from three-component MESMA. The sparse prior is constraint matched. The oracle supplies the actual generating spectra and is an implementation control, not an available deployment method. Comparing against a single screened random draw does not establish selector superiority.

Across targets, exhaustive searching reduced fraction error for **156**, increased it for **203**, and left it effectively unchanged for **1** (absolute fraction-RMSE tolerance 1e-8). Spectral error improved for 359 targets by more than 1e-9 supplied-array units.

The winning exhaustive fits use one category for **0** targets, two for **5**, and three for **355**. The search chooses the smallest spectral error without a complexity penalty; the stated numerical tie rule retains earlier, lower-dimensional solutions when improvement is negligible. Generating component counts are known only for evaluation and are not supplied to the solver.

The paired exhaustive-minus-screened fraction RMSE difference is **+0.0121**. Its conditional 95% whole-bundle bootstrap range is **[-0.0055, +0.0289]**, using 1,999 paired resamples of eight parent bundles. Negative differences favor exhaustive search. Only eight bundles are available: this describes sensitivity to those parents, not validated population coverage or a site-general significance test.

![Figure 1. All methods predict the same 360 synthetic targets. RMSE pools all target × category fraction errors before taking the square root. The dense prior predicts 0.2 for every category; the sparse prior predicts 1/3 for each of three fixed categories. They are design controls, not spectrum-based estimators. The oracle knows the generating parents. The random comparator remains screened and is only one matched draw.](figures/01_fraction_accuracy.png)

Figure 1. All methods predict the same 360 synthetic targets. RMSE pools all target × category fraction errors before taking the square root. The dense prior predicts 0.2 for every category; the sparse prior predicts 1/3 for each of three fixed categories. They are design controls, not spectrum-based estimators. The oracle knows the generating parents. The random comparator remains screened and is only one matched draw.

![Figure 2. Each point is one target, not an independent plant replicate. Colors denote one (teal), two (orange), or three (purple) generating categories. Searching more models can lower the spectral residual without moving fractions toward the known truth. Spectral RMSE is in supplied-array units; fraction RMSE is dimensionless.](figures/02_fit_vs_fractions.png)

Figure 2. Each point is one target, not an independent plant replicate. Colors denote one (teal), two (orange), or three (purple) generating categories. Searching more models can lower the spectral residual without moving fractions toward the known truth. Spectral RMSE is in supplied-array units; fraction RMSE is dimensionless.

![Figure 3. Each PFT has equal target weight within its row. Left: fraction errors across all targets. Right: false detections restricted to targets where that PFT is absent; prediction ≥0.10 counts as a detection. The 10% threshold is descriptive and unchanged across methods, not a validated field decision threshold.](figures/03_category_errors.png)

Figure 3. Each PFT has equal target weight within its row. Left: fraction errors across all targets. Right: false detections restricted to targets where that PFT is absent; prediction ≥0.10 counts as a detection. The 10% threshold is descriptive and unchanged across methods, not a validated field decision threshold.

![Figure 4. Deliberately selected extremes illustrate improvement and failure; they are not typical targets. The left column compares seven-band spectral reconstructions. The right column compares their PFT fractions with the exact generating weights. Closely overlapping spectral traces can correspond to different category mixtures. Nonveg. & dead is one recorded category.](figures/04_target_examples.png)

Figure 4. Deliberately selected extremes illustrate improvement and failure; they are not typical targets. The left column compares seven-band spectral reconstructions. The right column compares their PFT fractions with the exact generating weights. Closely overlapping spectral traces can correspond to different category mixtures. Nonveg. & dead is one recorded category.

## What about alternative explanations for the same spectrum?

The average numbers of near-optimal distinct category sets are **8.49**, **17.54** and **20.01**, at additive spectral RMSE tolerances 0.001, 0.005 and 0.01. Up to 25 sets are possible under the one-to-three-category model family. These are descriptive tolerances, not measured sensor noise. We retain one best interior solution per category set; this is a restricted ambiguity diagnostic and **does not bound every feasible fraction or prove uniqueness**.

## What does this establish, and what remains open?

This experiment separates candidate screening from full search over the declared fixed-library model family. Better spectral optimization is evidence about that model family; biological fraction accuracy must be judged from fraction errors and external observations. A globally best spectral fit need not identify the generating materials uniquely.

Selection used the whole archive. Excluding candidate parent IDs from target generation prevents direct parent reuse, but does not undo selection exposure. Results therefore remain **internal fixed-library diagnostics**, not selection-blind validation, universal sensor calibration or field PFT-cover accuracy. The targets are noiseless algebraic mixtures with constrained fractions; real scenes can include nonlinear mixing, shade, acquisition differences and materials absent from the dictionary.

The next validation step is to freeze this library and test independent targets with independently measured complete fractions, or reselect endmembers inside training-only identity/domain splits. Exhaustive random-library searches and independent site/year transfer experiments are separate work.

## Numerical audit and reproducibility

The analysis-only solver streams 1,024 models at a time, checkpoints each of 25 category sets, fingerprints inputs/code and reuses valid checkpoints on restart. Search time was 364.3 seconds, excluding data preparation and reporting. Candidate-model storage does not grow with the 16.9-million-model count. Rank, positive-interior and improvement thresholds match the existing kernel; “exhaustive” is relative to those floating-point thresholds and the declared model family.

Regression tests compare against the existing solver and independently enumerate small libraries, including pure/boundary/degenerate cases and restart/input-mismatch behavior. The numerical audit independently reconstructs every reported winner, checks its constrained optimum using SLSQP, compares the 12-target pilot, and directly evaluates all 16.9 million models for one prespecified triple target using separate seven-band difference geometry. Original P136 packet hashes are preserved. See `numerical_validation.json`, `full_summary.json`, `full_run.log`, input/code hashes and the compact tables for exact records.
