---
title: Validation — NEON HDF5 download
---

# Validation: NEON HDF5 download

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `neon_download-001`<br>Reuse a non-empty HDF5 artifact for site HARV. | `domain`=D01; `site_code`=HARV; `year_month`=2023-01 | **PASS** | `artifact_reused_unchanged`=true; `network_contacted`=false; `output_bytes`=17; `sha256`=cd2fd60d74decf19f5dbe9c0a4d8b939b3673a3fb44d210dde3dd5… | canonical_path_returned=✓; nonempty_h5_reused=✓ |
| `neon_download-002`<br>Reuse a non-empty HDF5 artifact for site OSBS. | `domain`=D03; `site_code`=OSBS; `year_month`=2023-02 | **PASS** | `artifact_reused_unchanged`=true; `network_contacted`=false; `output_bytes`=17; `sha256`=6fed15190444ff95af64dfad2a33a267b549e977f59123d7a52b8e… | canonical_path_returned=✓; nonempty_h5_reused=✓ |
| `neon_download-003`<br>Reuse a non-empty HDF5 artifact for site NIWO. | `domain`=D13; `site_code`=NIWO; `year_month`=2023-03 | **PASS** | `artifact_reused_unchanged`=true; `network_contacted`=false; `output_bytes`=17; `sha256`=3213c75a5afd84c427256530bfc4740e7e8725c78680565b6c47ba… | canonical_path_returned=✓; nonempty_h5_reused=✓ |
| `neon_download-004`<br>Reuse a non-empty HDF5 artifact for site JORN. | `domain`=D14; `site_code`=JORN; `year_month`=2023-04 | **PASS** | `artifact_reused_unchanged`=true; `network_contacted`=false; `output_bytes`=17; `sha256`=c3fe844c11a0342791c89d0077750be5c3acaf7801812d6c48cb94… | canonical_path_returned=✓; nonempty_h5_reused=✓ |
| `neon_download-005`<br>Reuse a non-empty HDF5 artifact for site SJER. | `domain`=D17; `site_code`=SJER; `year_month`=2023-05 | **PASS** | `artifact_reused_unchanged`=true; `network_contacted`=false; `output_bytes`=17; `sha256`=40af97777b435041c55e4afeace8884a6b11fe49f0c188fcc11319… | canonical_path_returned=✓; nonempty_h5_reused=✓ |

## What this tells us about QA

Track availability, artifact size, retry count, and failure category. A live campaign should expose site/month combinations that need clearer download diagnostics.

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
