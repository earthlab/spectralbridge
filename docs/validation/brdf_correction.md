---
title: Validation — BRDF correction
---

# Validation: BRDF correction

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `brdf_correction-001`<br>Neutral BRDF model at 0° view zenith. | `scale_factor`=1; `shape_y_x_b`=[5,6,2]; `view_zenith_degrees`=0 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.626875; `output_min_unitless`=0.0513522 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |
| `brdf_correction-002`<br>Neutral BRDF model at 7° view zenith. | `scale_factor`=0.0001; `shape_y_x_b`=[6,7,3]; `view_zenith_degrees`=7 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.64909; `output_min_unitless`=0.0542199 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |
| `brdf_correction-003`<br>Neutral BRDF model at 14° view zenith. | `scale_factor`=1; `shape_y_x_b`=[7,8,4]; `view_zenith_degrees`=14 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.643089; `output_min_unitless`=0.0510967 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |
| `brdf_correction-004`<br>Neutral BRDF model at 21° view zenith. | `scale_factor`=0.0001; `shape_y_x_b`=[8,6,5]; `view_zenith_degrees`=21 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.649915; `output_min_unitless`=0.0522228 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |
| `brdf_correction-005`<br>Neutral BRDF model at 28° view zenith. | `scale_factor`=1; `shape_y_x_b`=[5,7,2]; `view_zenith_degrees`=28 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.643964; `output_min_unitless`=0.0507589 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |

## What this tells us about QA

Use identity-model error to detect numerical drift, then add real-flightline diagnostics for view-angle support, coefficient stability, and correction magnitude by wavelength.

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
