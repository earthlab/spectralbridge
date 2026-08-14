---
title: Validation — Sensor convolution
---

# Validation: Sensor convolution

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `sensor_convolution-001`<br>Resample 4 source bands into 1 target bands. | `input_shape_y_x_b`=[3,4,4]; `target_band_count`=1 | **PASS** | `max_absolute_error`=2.98023e-08; `output_max`=0.793138; `output_min`=0.253127; `output_shape`=[3,4,1] | dtype_is_float32=✓; output_band_count_correct=✓; weighted_average_matches_reference=✓ |
| `sensor_convolution-002`<br>Resample 5 source bands into 2 target bands. | `input_shape_y_x_b`=[4,5,5]; `target_band_count`=2 | **PASS** | `max_absolute_error`=5.96046e-08; `output_max`=0.824112; `output_min`=0.138205; `output_shape`=[4,5,2] | dtype_is_float32=✓; output_band_count_correct=✓; weighted_average_matches_reference=✓ |
| `sensor_convolution-003`<br>Resample 6 source bands into 3 target bands. | `input_shape_y_x_b`=[5,4,6]; `target_band_count`=3 | **PASS** | `max_absolute_error`=1.19209e-07; `output_max`=0.71096; `output_min`=0.121563; `output_shape`=[5,4,3] | dtype_is_float32=✓; output_band_count_correct=✓; weighted_average_matches_reference=✓ |
| `sensor_convolution-004`<br>Resample 7 source bands into 4 target bands. | `input_shape_y_x_b`=[3,5,7]; `target_band_count`=4 | **PASS** | `max_absolute_error`=1.19209e-07; `output_max`=0.764092; `output_min`=0.219115; `output_shape`=[3,5,4] | dtype_is_float32=✓; output_band_count_correct=✓; weighted_average_matches_reference=✓ |
| `sensor_convolution-005`<br>Resample 8 source bands into 5 target bands. | `input_shape_y_x_b`=[4,4,8]; `target_band_count`=5 | **PASS** | `max_absolute_error`=5.96046e-08; `output_max`=0.768413; `output_min`=0.313292; `output_shape`=[4,4,5] | dtype_is_float32=✓; output_band_count_correct=✓; weighted_average_matches_reference=✓ |

## What this tells us about QA

Surface numerical error against an independent weighted-average reference, output range, and target-band support. QA should flag missing or near-zero spectral-response support.

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
