---
title: Validation evidence
---

# Validation evidence

This section records how SpectralBridge functions behave across explicit input variations. Each row comes from a machine-readable campaign result rather than a hand-written success claim.

## Current evidence

| Module | Variations | Passed | Failed | Skipped | Results |
| --- | ---: | ---: | ---: | ---: | --- |
| NEON HDF5 download | 5 | 5 | 0 | 0 | [Open module evidence](neon_download.md) |
| HDF5 to raw ENVI | 5 | 5 | 0 | 0 | [Open module evidence](h5_to_envi.md) |
| Topographic correction | 5 | 5 | 0 | 0 | [Open module evidence](topographic_correction.md) |
| BRDF correction | 5 | 5 | 0 | 0 | [Open module evidence](brdf_correction.md) |
| Sensor convolution | 5 | 5 | 0 | 0 | [Open module evidence](sensor_convolution.md) |
| Parquet extraction and CSV conversion | 5 | 5 | 0 | 0 | [Open module evidence](parquet_csv.md) |
| Save and restart behavior | 5 | 5 | 0 | 0 | [Open module evidence](save_restart.md) |
| QA plots and diagnostics | 5 | 5 | 0 | 0 | [Open module evidence](qa_plots.md) |

## Two validation tiers

1. **Offline contract campaign:** small deterministic inputs, safe for local or CI execution. It checks dimensions, numerical invariants, schemas, restart behavior, and diagnostic generation.
2. **Live NEON campaign:** opt-in real data selected from a pinned inventory. It measures download reliability, full-stage behavior, correction support, performance, and QA usefulness across sites and acquisition conditions.

These tiers must remain separate. Repeating synthetic inputs 100 times can expose numerical and state bugs, but it cannot establish network reliability or scientific validity across 100 real flightlines.

## Recorded campaigns

| Campaign | Mode | Revision | Dirty tree | Generated (UTC) | Total | Passed | Failed |
| --- | --- | --- | --- | --- | ---: | ---: | ---: |
| `offline-contract-5-per-module` | offline | `bebf707` | true | 2026-08-14T18:05:29.385201+00:00 | 40 | 40 | 0 |

## Interpretation rules

- A **pass** means every explicit software-contract check for that variation passed.
- A **failure** remains visible and includes its diagnostics or exception.
- A **skip** must state why evidence was not collected.
- Synthetic checks must not be described as external scientific validation.
- QA thresholds should be changed only after a representative real-data campaign and scientific review.

The underlying JSON records live in `validation/results/` and are the source of truth for these pages.

Last updated: 2026-08-14
