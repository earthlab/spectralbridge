---
title: Validation — QA plots and diagnostics
---

# Validation: QA plots and diagnostics

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `qa_plots-001`<br>Render QA for delta +0.000 and 0% injected NoData. | `correction_delta`=0; `nodata_fraction`=0; `shape_b_y_x`=[4,10,9] | **PASS** | `issue_count`=1; `json_bytes`=3085; `median_reported_delta`=0; `png_bytes`=215175; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |
| `qa_plots-002`<br>Render QA for delta +0.005 and 2% injected NoData. | `correction_delta`=0.005; `nodata_fraction`=0.02; `shape_b_y_x`=[5,11,10] | **PASS** | `issue_count`=2; `json_bytes`=3716; `median_reported_delta`=0.005; `png_bytes`=222599; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |
| `qa_plots-003`<br>Render QA for delta -0.010 and 8% injected NoData. | `correction_delta`=-0.01; `nodata_fraction`=0.08; `shape_b_y_x`=[6,12,11] | **PASS** | `issue_count`=2; `json_bytes`=4026; `median_reported_delta`=-0.00999999; `png_bytes`=223599; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |
| `qa_plots-004`<br>Render QA for delta +0.020 and 15% injected NoData. | `correction_delta`=0.02; `nodata_fraction`=0.15; `shape_b_y_x`=[4,13,12] | **PASS** | `issue_count`=2; `json_bytes`=3598; `median_reported_delta`=0.02; `png_bytes`=227404; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |
| `qa_plots-005`<br>Render QA for delta -0.030 and 25% injected NoData. | `correction_delta`=-0.03; `nodata_fraction`=0.25; `shape_b_y_x`=[5,10,13] | **PASS** | `issue_count`=2; `json_bytes`=3742; `median_reported_delta`=-0.03; `png_bytes`=223818; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |

## What this tells us about QA

Verify that injected correction deltas and NoData patterns appear in machine-readable QA. Visual legibility still requires image review or approved perceptual baselines.

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
