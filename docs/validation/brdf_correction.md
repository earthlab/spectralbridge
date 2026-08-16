---
title: Validation — BRDF correction
---

# Validation: BRDF correction

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## What this module test exercises

Use a neutral BRDF model as an identity contract across view angles, storage scales, cube sizes, and band counts.

**Implementation exercised:** `apply_brdf_correct`

### Inputs varied

| Field | Why it is recorded |
| --- | --- |
| `view_zenith_degrees` | Varies view geometry from nadir to 28°. |
| `scale_factor` | Alternates unit and scaled reflectance storage. |
| `shape_y_x_b` | Varies spatial dimensions and band count. |

### Checks and how to interpret them

| Check | Question | PASS means | If it does not pass |
| --- | --- | --- | --- |
| `shape_preserved` | Does BRDF application retain the cube shape? | Output and input dimensions match exactly. | Inspect band axis and tile assembly. |
| `neutral_model_is_identity` | Does an iso=1, vol=0, geo=0 model leave reflectance unchanged? | Input and output agree within `1e-5` stored units. | Any drift indicates a kernel, scaling, or factor-application regression. |
| `dtype_preserved` | Does correction retain the float32 output contract? | The output dtype is float32. | Review memory allocation and NumPy promotion before accepting larger files. |

### Diagnostics recorded for every variation

| Field | Why it is recorded |
| --- | --- |
| `max_absolute_error_stored_units` | Largest identity-model difference. |
| `finite_percent` | Percent of numerically defined corrected values. |
| `output_min_unitless` | Minimum output after conversion to unit reflectance. |
| `output_max_unitless` | Maximum output after conversion to unit reflectance. |

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `brdf_correction-001`<br>Neutral BRDF model at 0° view zenith. | `scale_factor`=1; `shape_y_x_b`=[5,6,2]; `view_zenith_degrees`=0 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.626875; `output_min_unitless`=0.0513522 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |
| `brdf_correction-002`<br>Neutral BRDF model at 7° view zenith. | `scale_factor`=0.0001; `shape_y_x_b`=[6,7,3]; `view_zenith_degrees`=7 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.64909; `output_min_unitless`=0.0542199 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |
| `brdf_correction-003`<br>Neutral BRDF model at 14° view zenith. | `scale_factor`=1; `shape_y_x_b`=[7,8,4]; `view_zenith_degrees`=14 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.643089; `output_min_unitless`=0.0510967 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |
| `brdf_correction-004`<br>Neutral BRDF model at 21° view zenith. | `scale_factor`=0.0001; `shape_y_x_b`=[8,6,5]; `view_zenith_degrees`=21 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.649915; `output_min_unitless`=0.0522228 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |
| `brdf_correction-005`<br>Neutral BRDF model at 28° view zenith. | `scale_factor`=1; `shape_y_x_b`=[5,7,2]; `view_zenith_degrees`=28 | **PASS** | `finite_percent`=100; `max_absolute_error_stored_units`=0; `output_max_unitless`=0.643964; `output_min_unitless`=0.0507589 | dtype_preserved=✓; neutral_model_is_identity=✓; shape_preserved=✓ |

## What a passing result establishes

Neutral-model invariance and basic numerical stability.

!!! warning "What it does not establish"
    Accuracy of fitted BRDF coefficients for real angular sampling.

The matching real stage checks are explained in the [stage QA test guide](stage-qa-guide.md#correction-parameters).

## Example from the real R10C test run

<div class="sb-validation-grid">
  <figure class="sb-validation-figure">
    <a href="../artifacts/r10c-l002-20210915/qa/stages/02_correction_parameters/overview.png"><img src="../artifacts/r10c-l002-20210915/qa/stages/02_correction_parameters/overview.png" alt="R10C correction parameter profiles" loading="lazy"></a>
    <figcaption>The real run displays fitted BRDF profiles and unfiltered geometry summaries; four fields are marked for range review.</figcaption>
  </figure>
</div>

The figure is evidence from one completed flightline, not a replacement for the variation table above. Open the [real flightline walkthrough](real-data-example.md) for exact values and limitations.

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
