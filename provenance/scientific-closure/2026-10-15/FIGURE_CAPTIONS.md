# Five final synthesis figures

## F1_library_structure

A: identity counts within cohorts; across-year repeats are not additive biological replication. B: equal annual-row weighting differs from equal identity weighting. C: all repeated-year identities are at NIWO. GlobalID denotes a polygon, not verified biological-individual purity.

Source tables: observational_support.csv, sampling_weight_effect.csv, identity_sampling.csv

## F2_temporal_resolution

A: exact balanced two-year SS, not causal random-effect variances. B: equal-class-centroid distance and temporal change differ from weighted SS; intervals resample paired identities. Populations/classes differ across levels. C-D: same unseen identities in both years; lines average three folds. Neither year is trained using test identities. Reference labels are reused 2023/2024 annotations, not independent annual field verification.

Source tables: paired_temporal_partition.csv, paired_temporal_recognition.csv, paired_temporal_accuracy_change.csv

## F3_generalization_shape_sensor

A-B: descriptive mean fold scores on supported closed-set targets, with different class counts/populations and chance references. Global year holdouts confound site composition; paired NIWO inference is Figure 2. C: same held-site targets and training memberships; shape normalization is analytical only. D: reused twenty-coordinate training-only selection.

Source tables: biological_generalization.csv, closed_set_coverage.csv, brightness_sampling_sensitivity.csv, P126/wavelength_selection.csv

## F4_mixture_limits

All numerical experiments reused from the verified prior audit. A: ambiguity at the declared 0.01 training-normalized analytical metric tolerance, not an absolute reflectance threshold. B: exact saved parent/fraction/endmember comparisons. C: repeated trajectories are dependent, and positive detection at zero is false detection. D: unknown labels are ecological proxies; thresholds use known calibration only. No independent field abundance truth is present.

Source tables: P126/mixture_identifiability.csv, P126/sensor_resolution_mixture_results.csv, P126/detection_limits.csv, P126/unknown_material_detection.csv

## F5_final_decisions

Readiness categories follow the explicit DESIGN review scenarios and actual validation scope, not an averaged score. Classification is conditional on supported source-label populations. The real-Landsat constrained category applies only to one radiometric/spatial scene comparison. No use is operationally validated.

Source tables: FINAL_READINESS_MATRIX.csv, DESIGN.md
