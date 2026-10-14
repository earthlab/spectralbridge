# Fraction uncertainty, shade and unknowns

| scheme | sensor | mean_empirical_interval_width | conditional_truth_coverage | mean_fraction_RMSE |
| --- | --- | --- | --- | --- |
| inferred_pft | NEON | 0.595 | 0.867 | 0.281 |
| inferred_pft | OLI | 0.594 | 0.865 | 0.277 |
| material | NEON | 0.388 | 0.863 | 0.233 |
| material | OLI | 0.390 | 0.868 | 0.234 |
| researcher | NEON | 0.587 | 0.842 | 0.279 |
| researcher | OLI | 0.598 | 0.869 | 0.279 |

Twelve empirical random one-candidate-per-class FCLS draws produce an ensemble mean and empirical 2.5/97.5 percentiles. These are ENDMember-choice stability ranges, not posterior distributions or confidence intervals. Twelve draws are sparse for tail estimation. The nominal 95% reference is evaluated against controlled synthetic truth, not asserted calibrated. Finite candidate pools omit unobserved variability; the parent spectra themselves may be mixed. No independent flight-based sensor-noise model is available.

The best-per-composition near-model range is a lower bound on model ambiguity, not a full fraction interval. Small spectral residuals can coexist with large fraction RMSE; unreliable_fraction_flags.csv quantifies false-confidence sensitivities without choosing a threshold after seeing results. Thresholds 0.005/0.01/0.02 are relative spectral tolerances and fraction error 0.10/0.20 are illustrative decision aids, not universal pass criteria. Do not operationally accept an unknown merely because its residual is small.

Removing an entire class tests unknown-material masquerading at pure nominal-label endpoints. More realistic unknown mixtures, novel species/backgrounds, complete-source-image OOD validation and calibrated abstention remain required. Independent empirical shade spectra are missing. A 25% idealized zero-shade simulation probes algebra only; shade-normalized fractions describe conditional non-shade composition, while total fractions describe the footprint. Nonlinearity cannot be diagnosed uniquely from these residuals: endmember incompleteness, purity, atmosphere/correction and variable scaling are competing explanations. No nonlinear model was implemented to explain away failure.
