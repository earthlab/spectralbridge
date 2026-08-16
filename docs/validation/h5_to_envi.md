---
title: Validation — HDF5 to raw ENVI
---

# Validation: HDF5 to raw ENVI

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## What this module test exercises

Verify that a NEON-layout HDF5 reflectance cube becomes a band-sequential float32 ENVI image with matching dimensions, values, and a readable header.

**Implementation exercised:** `neon_to_envi_no_hytools` and `EnviWriter`

### Inputs varied

| Field | Why it is recorded |
| --- | --- |
| `shape_y_x_b` | Varies lines, samples, and spectral band count. |
| `brightness_offset` | Exercises zero and small explicit export offsets. |
| `site_code` | Varies realistic flightline naming metadata. |

### Checks and how to interpret them

| Check | Question | PASS means | If it does not pass |
| --- | --- | --- | --- |
| `shape_preserved` | Did conversion preserve lines, samples, and bands? | The reconstructed ENVI array has the same Y×X×band shape as the source. | Inspect axis order, header dimensions, and BSQ serialization. |
| `float32_bsq_values_preserved` | Do stored values match an independent expected array? | Maximum absolute error is at most `1e-7` after applying the configured offset. | Inspect scaling, axis transposition, datatype, and chunk writes. |
| `header_written` | Was a non-empty ENVI header produced? | The `.hdr` exists and contains bytes. | Do not run downstream correction until dimensions and metadata parse correctly. |

### Diagnostics recorded for every variation

| Field | Why it is recorded |
| --- | --- |
| `shape` | Observed ENVI shape after independent read-back. |
| `max_absolute_error` | Largest source-versus-output value difference. |
| `output_bytes` | ENVI image size used to catch incomplete writes. |
| `header_bytes` | Header size used as a minimal persistence check. |

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `h5_to_envi-001`<br>Convert a 3×4×2 synthetic NEON-layout cube. | `brightness_offset`=0; `shape_y_x_b`=[3,4,2]; `site_code`=HARV | **PASS** | `header_bytes`=453; `max_absolute_error`=0; `output_bytes`=96; `shape`=[3,4,2] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |
| `h5_to_envi-002`<br>Convert a 4×6×3 synthetic NEON-layout cube. | `brightness_offset`=0.01; `shape_y_x_b`=[4,6,3]; `site_code`=OSBS | **PASS** | `header_bytes`=466; `max_absolute_error`=0; `output_bytes`=288; `shape`=[4,6,3] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |
| `h5_to_envi-003`<br>Convert a 5×8×4 synthetic NEON-layout cube. | `brightness_offset`=0.02; `shape_y_x_b`=[5,8,4]; `site_code`=NIWO | **PASS** | `header_bytes`=503; `max_absolute_error`=0; `output_bytes`=640; `shape`=[5,8,4] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |
| `h5_to_envi-004`<br>Convert a 6×5×5 synthetic NEON-layout cube. | `brightness_offset`=0; `shape_y_x_b`=[6,5,5]; `site_code`=JORN | **PASS** | `header_bytes`=492; `max_absolute_error`=0; `output_bytes`=600; `shape`=[6,5,5] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |
| `h5_to_envi-005`<br>Convert a 7×7×6 synthetic NEON-layout cube. | `brightness_offset`=0.01; `shape_y_x_b`=[7,7,6]; `site_code`=SJER | **PASS** | `header_bytes`=505; `max_absolute_error`=0; `output_bytes`=1176; `shape`=[7,7,6] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |

## What a passing result establishes

Small-cube axis, datatype, value, and header contracts.

!!! warning "What it does not establish"
    Performance on full flightlines or completeness of every provider-specific HDF5 metadata field.

The matching real stage checks are explained in the [stage QA test guide](stage-qa-guide.md#input-reflectance).

## Example from the real R10C test run

<div class="sb-validation-grid">
  <figure class="sb-validation-figure">
    <a href="../artifacts/r10c-l002-20210915/qa/stages/01_input_data/overview.png"><img src="../artifacts/r10c-l002-20210915/qa/stages/01_input_data/overview.png" alt="R10C input reflectance overview" loading="lazy"></a>
    <figcaption>The real exported ENVI is reviewed spatially and spectrally after scale and NoData metadata are applied.</figcaption>
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
