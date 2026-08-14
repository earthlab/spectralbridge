---
title: Validation — Save and restart behavior
---

# Validation: Save and restart behavior

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `save_restart-001`<br>Write an ENVI cube in two chunks split at row 1. | `chunk_split_row`=1; `shape_y_x_b`=[3,4,2] | **PASS** | `chunk_split_row`=1; `image_bytes`=96; `max_absolute_error`=0; `sha256`=aa7d1418648d4f23fc6002a9741b868f27493e546cc7903b635f03… | chunked_write_reconstructs_cube=✓; expected_byte_count=✓; read_does_not_mutate_artifact=✓ |
| `save_restart-002`<br>Write an ENVI cube in two chunks split at row 2. | `chunk_split_row`=2; `shape_y_x_b`=[4,5,3] | **PASS** | `chunk_split_row`=2; `image_bytes`=240; `max_absolute_error`=0; `sha256`=c556b17b18f405119ce671fb392c8988c9dfc84c60104b2fdfe571… | chunked_write_reconstructs_cube=✓; expected_byte_count=✓; read_does_not_mutate_artifact=✓ |
| `save_restart-003`<br>Write an ENVI cube in two chunks split at row 3. | `chunk_split_row`=3; `shape_y_x_b`=[5,6,4] | **PASS** | `chunk_split_row`=3; `image_bytes`=480; `max_absolute_error`=0; `sha256`=308faef52f0c097d825d98b121daf2993679072f717762316edba3… | chunked_write_reconstructs_cube=✓; expected_byte_count=✓; read_does_not_mutate_artifact=✓ |
| `save_restart-004`<br>Write an ENVI cube in two chunks split at row 4. | `chunk_split_row`=4; `shape_y_x_b`=[6,4,5] | **PASS** | `chunk_split_row`=4; `image_bytes`=480; `max_absolute_error`=0; `sha256`=a2ef06292a890769c6d044bcbdb57ee490c98c31d66514ff1b05a6… | chunked_write_reconstructs_cube=✓; expected_byte_count=✓; read_does_not_mutate_artifact=✓ |
| `save_restart-005`<br>Write an ENVI cube in two chunks split at row 1. | `chunk_split_row`=1; `shape_y_x_b`=[3,5,6] | **PASS** | `chunk_split_row`=1; `image_bytes`=360; `max_absolute_error`=0; `sha256`=05dad747989a20be5ab54817a75191c92e2e68ca470e6c3c9f41e2… | chunked_write_reconstructs_cube=✓; expected_byte_count=✓; read_does_not_mutate_artifact=✓ |

## What this tells us about QA

Use hashes, expected byte counts, and non-mutation checks to distinguish a valid reusable artifact from a merely present file.

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
