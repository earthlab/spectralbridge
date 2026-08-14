---
title: Validation — HDF5 to raw ENVI
---

# Validation: HDF5 to raw ENVI

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `h5_to_envi-001`<br>Convert a 3×4×2 synthetic NEON-layout cube. | `brightness_offset`=0; `shape_y_x_b`=[3,4,2]; `site_code`=HARV | **PASS** | `header_bytes`=453; `max_absolute_error`=0; `output_bytes`=96; `shape`=[3,4,2] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |
| `h5_to_envi-002`<br>Convert a 4×6×3 synthetic NEON-layout cube. | `brightness_offset`=0.01; `shape_y_x_b`=[4,6,3]; `site_code`=OSBS | **PASS** | `header_bytes`=466; `max_absolute_error`=0; `output_bytes`=288; `shape`=[4,6,3] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |
| `h5_to_envi-003`<br>Convert a 5×8×4 synthetic NEON-layout cube. | `brightness_offset`=0.02; `shape_y_x_b`=[5,8,4]; `site_code`=NIWO | **PASS** | `header_bytes`=503; `max_absolute_error`=0; `output_bytes`=640; `shape`=[5,8,4] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |
| `h5_to_envi-004`<br>Convert a 6×5×5 synthetic NEON-layout cube. | `brightness_offset`=0; `shape_y_x_b`=[6,5,5]; `site_code`=JORN | **PASS** | `header_bytes`=492; `max_absolute_error`=0; `output_bytes`=600; `shape`=[6,5,5] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |
| `h5_to_envi-005`<br>Convert a 7×7×6 synthetic NEON-layout cube. | `brightness_offset`=0.01; `shape_y_x_b`=[7,7,6]; `site_code`=SJER | **PASS** | `header_bytes`=505; `max_absolute_error`=0; `output_bytes`=1176; `shape`=[7,7,6] | float32_bsq_values_preserved=✓; header_written=✓; shape_preserved=✓ |

## What this tells us about QA

Compare source and output dimensions, value error, wavelength/header integrity, and NoData handling. These checks should become visible in ENVI/header QA summaries.

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
