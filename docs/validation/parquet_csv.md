---
title: Validation — Parquet extraction and CSV conversion
---

# Validation: Parquet extraction and CSV conversion

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `parquet_csv-001`<br>Extract a 3×4×2 ENVI cube with chunk size 2, then write CSV. | `chunk_size`=2; `shape_b_y_x`=[2,3,4] | **PASS** | `column_count`=13; `csv_bytes`=1420; `csv_rows`=12; `parquet_bytes`=19318; `parquet_rows`=12; `spectral_column_count`=2 | all_pixels_exported=✓; coordinate_columns_present=✓; csv_row_count_matches=✓; spectral_band_count_matches=✓ |
| `parquet_csv-002`<br>Extract a 4×5×3 ENVI cube with chunk size 3, then write CSV. | `chunk_size`=3; `shape_b_y_x`=[3,4,5] | **PASS** | `column_count`=14; `csv_bytes`=2572; `csv_rows`=20; `parquet_bytes`=26289; `parquet_rows`=20; `spectral_column_count`=3 | all_pixels_exported=✓; coordinate_columns_present=✓; csv_row_count_matches=✓; spectral_band_count_matches=✓ |
| `parquet_csv-003`<br>Extract a 5×6×4 ENVI cube with chunk size 4, then write CSV. | `chunk_size`=4; `shape_b_y_x`=[4,5,6] | **PASS** | `column_count`=15; `csv_bytes`=4164; `csv_rows`=30; `parquet_bytes`=34119; `parquet_rows`=30; `spectral_column_count`=4 | all_pixels_exported=✓; coordinate_columns_present=✓; csv_row_count_matches=✓; spectral_band_count_matches=✓ |
| `parquet_csv-004`<br>Extract a 6×7×5 ENVI cube with chunk size 2, then write CSV. | `chunk_size`=2; `shape_b_y_x`=[5,6,7] | **PASS** | `column_count`=16; `csv_bytes`=6291; `csv_rows`=42; `parquet_bytes`=77539; `parquet_rows`=42; `spectral_column_count`=5 | all_pixels_exported=✓; coordinate_columns_present=✓; csv_row_count_matches=✓; spectral_band_count_matches=✓ |
| `parquet_csv-005`<br>Extract a 3×8×2 ENVI cube with chunk size 3, then write CSV. | `chunk_size`=3; `shape_b_y_x`=[2,3,8] | **PASS** | `column_count`=13; `csv_bytes`=2752; `csv_rows`=24; `parquet_bytes`=26869; `parquet_rows`=24; `spectral_column_count`=2 | all_pixels_exported=✓; coordinate_columns_present=✓; csv_row_count_matches=✓; spectral_band_count_matches=✓ |

## What this tells us about QA

Expose row preservation, spectral-column counts, coordinate fields, and CSV parity. These are direct candidates for the Parquet/merge page of the QA report.

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
