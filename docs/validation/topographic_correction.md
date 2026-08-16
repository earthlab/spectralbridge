---
title: Validation — Topographic correction
---

# Validation: Topographic correction

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## What this module test exercises

Apply SCS+C to controlled synthetic terrain and confirm that correction reduces the injected reflectance relationship with illumination geometry.

**Implementation exercised:** `calc_cosine_i` and `apply_topo_correct`

### Inputs varied

| Field | Why it is recorded |
| --- | --- |
| `slope_max_degrees` | Varies terrain from gentle to steeper slopes. |
| `scale_factor` | Alternates unit reflectance and 10,000-scaled storage. |
| `shape_y_x_b` | Varies spatial dimensions and band count. |

### Checks and how to interpret them

| Check | Question | PASS means | If it does not pass |
| --- | --- | --- | --- |
| `shape_preserved` | Does correction retain the cube shape? | Corrected and input arrays have identical dimensions. | Inspect band/spatial axis handling and tile assembly. |
| `all_values_finite` | Did valid synthetic support remain numerically defined? | All corrected values are finite for this no-NoData fixture. | Inspect divisions, invalid geometry, and correction-factor bounds. |
| `terrain_correlation_reduced` | Did SCS+C reduce the deliberately injected illumination dependence? | Absolute correlation with cosine incidence is lower after correction. | Review coefficients and geometry; this check is directional, not an accuracy threshold. |

### Diagnostics recorded for every variation

| Field | Why it is recorded |
| --- | --- |
| `incidence_correlation_before` | Absolute pre-correction geometry correlation. |
| `incidence_correlation_after` | Absolute post-correction geometry correlation. |
| `correlation_reduction` | Before minus after correlation. |
| `finite_percent` | Percent of corrected cells that are finite. |
| `mean_absolute_change` | Average correction magnitude in unit reflectance. |

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `topographic_correction-001`<br>SCS+C correction over terrain slopes up to 5°. | `scale_factor`=1; `shape_y_x_b`=[8,9,3]; `slope_max_degrees`=5 | **PASS** | `correlation_reduction`=0.867244; `finite_percent`=100; `incidence_correlation_after`=0.132756; `incidence_correlation_before`=1; `mean_absolute_change`=0.0015484 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |
| `topographic_correction-002`<br>SCS+C correction over terrain slopes up to 10°. | `scale_factor`=0.0001; `shape_y_x_b`=[9,10,4]; `slope_max_degrees`=10 | **PASS** | `correlation_reduction`=0.909479; `finite_percent`=100; `incidence_correlation_after`=0.0905207; `incidence_correlation_before`=1; `mean_absolute_change`=0.00337437 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |
| `topographic_correction-003`<br>SCS+C correction over terrain slopes up to 15°. | `scale_factor`=1; `shape_y_x_b`=[10,11,5]; `slope_max_degrees`=15 | **PASS** | `correlation_reduction`=0.952548; `finite_percent`=100; `incidence_correlation_after`=0.0474518; `incidence_correlation_before`=1; `mean_absolute_change`=0.00545464 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |
| `topographic_correction-004`<br>SCS+C correction over terrain slopes up to 20°. | `scale_factor`=0.0001; `shape_y_x_b`=[8,12,3]; `slope_max_degrees`=20 | **PASS** | `correlation_reduction`=0.996449; `finite_percent`=100; `incidence_correlation_after`=0.00355099; `incidence_correlation_before`=1; `mean_absolute_change`=0.00606101 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |
| `topographic_correction-005`<br>SCS+C correction over terrain slopes up to 25°. | `scale_factor`=1; `shape_y_x_b`=[9,9,4]; `slope_max_degrees`=25 | **PASS** | `correlation_reduction`=0.950993; `finite_percent`=100; `incidence_correlation_after`=0.0490067; `incidence_correlation_before`=1; `mean_absolute_change`=0.00837028 | all_values_finite=✓; shape_preserved=✓; terrain_correlation_reduced=✓ |

## What a passing result establishes

Numerical shape, scaling, finite-value, and directional decorrelation behavior.

!!! warning "What it does not establish"
    Ecological signal preservation or optimal correction on real terrain.

The matching real stage checks are explained in the [stage QA test guide](stage-qa-guide.md#brdf-and-topographic-correction).

## Example from the real R10C test run

<div class="sb-validation-grid">
  <figure class="sb-validation-figure">
    <a href="../artifacts/r10c-l002-20210915/qa/stages/03_brdf_topographic_correction/overview.png"><img src="../artifacts/r10c-l002-20210915/qa/stages/03_brdf_topographic_correction/overview.png" alt="R10C before and after correction overview" loading="lazy"></a>
    <figcaption>Matched maps and spectra show the combined persisted BRDF/topographic result; the pipeline does not store a topo-only intermediate.</figcaption>
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
