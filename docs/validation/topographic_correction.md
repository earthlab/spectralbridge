---
title: Validation — Topographic correction
---

# Validation: Topographic correction

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `topographic_correction-001`<br>SCS+C correction over terrain slopes up to 5°. | `scale_factor`=1; `shape_y_x_b`=[8,9,3]; `slope_max_degrees`=5 | **PASS** | `correlation_reduction`=0.867244; `finite_percent`=100; `incidence_correlation_after`=0.132756; `incidence_correlation_before`=1; `mean_absolute_change`=0.0015484 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |
| `topographic_correction-002`<br>SCS+C correction over terrain slopes up to 10°. | `scale_factor`=0.0001; `shape_y_x_b`=[9,10,4]; `slope_max_degrees`=10 | **PASS** | `correlation_reduction`=0.909479; `finite_percent`=100; `incidence_correlation_after`=0.0905207; `incidence_correlation_before`=1; `mean_absolute_change`=0.00337437 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |
| `topographic_correction-003`<br>SCS+C correction over terrain slopes up to 15°. | `scale_factor`=1; `shape_y_x_b`=[10,11,5]; `slope_max_degrees`=15 | **PASS** | `correlation_reduction`=0.952548; `finite_percent`=100; `incidence_correlation_after`=0.0474518; `incidence_correlation_before`=1; `mean_absolute_change`=0.00545464 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |
| `topographic_correction-004`<br>SCS+C correction over terrain slopes up to 20°. | `scale_factor`=0.0001; `shape_y_x_b`=[8,12,3]; `slope_max_degrees`=20 | **PASS** | `correlation_reduction`=0.996449; `finite_percent`=100; `incidence_correlation_after`=0.00355099; `incidence_correlation_before`=1; `mean_absolute_change`=0.00606101 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |
| `topographic_correction-005`<br>SCS+C correction over terrain slopes up to 25°. | `scale_factor`=1; `shape_y_x_b`=[9,9,4]; `slope_max_degrees`=25 | **PASS** | `correlation_reduction`=0.950993; `finite_percent`=100; `incidence_correlation_after`=0.0490067; `incidence_correlation_before`=1; `mean_absolute_change`=0.00837028 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |

## What this tells us about QA

Report finite support, correction magnitude, and terrain/illumination relationships before and after correction. Synthetic correlation reduction is a contract diagnostic, not proof of physical accuracy on real terrain.

## Expansion to 100 real variations

The repository includes a [live 100-flightline campaign specification](https://github.com/earthlab/spectralbridge/blob/main/validation/campaigns/neon-live-100.example.json). It requires a pinned inventory of real flightline IDs plus an explicit compute, storage, and network allocation. Live results must be stored as a new campaign record; they must not overwrite this offline baseline.

## Reproduce or expand this module

```bash
# Fast local evidence matrix (five variations per module)
python scripts/run_validation_campaign.py --iterations-per-module 5

# Exercise 100 deterministic small-data variations per module
python scripts/run_validation_campaign.py --iterations-per-module 100 \
  --output validation/results/offline-contract-100.json

python scripts/generate_validation_docs.py
```

The 100-case offline command scales contract variation and randomized synthetic inputs. It does **not** substitute for 100 distinct NEON downloads.

Last updated: 2026-08-14
