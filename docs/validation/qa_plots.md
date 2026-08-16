---
title: Validation — QA plots and diagnostics
---

# Validation: QA plots and diagnostics

**Recorded evidence:** 5 variations; 5 passed, 0 failed, and 0 skipped (100.0% pass rate over all recorded variations).

!!! info "Evidence boundary"
    The current checked-in campaign uses small synthetic or already-present inputs and does not contact NEON. It validates software contracts and diagnostics, not real-flightline scientific accuracy.

## What this module test exercises

Inject known correction deltas and NoData patterns, render QA, and confirm that both image and JSON diagnostics record the intended signal.

**Implementation exercised:** `render_flightline_panel` and its machine-readable QA payload

### Inputs varied

| Field | Why it is recorded |
| --- | --- |
| `correction_delta` | Varies positive, negative, and zero changes. |
| `nodata_fraction` | Varies injected invalid support from 0% to 25%. |
| `shape_b_y_x` | Varies bands and spatial dimensions. |

### Checks and how to interpret them

| Check | Question | PASS means | If it does not pass |
| --- | --- | --- | --- |
| `png_written` | Was a non-empty visual QA artifact written? | PNG exists and contains bytes. | Inspect rendering dependencies, output paths, and figure closure. |
| `json_written` | Was a non-empty machine-readable companion written? | JSON exists and contains bytes. | Do not rely on the image alone; investigate serialization or path errors. |
| `band_count_reported` | Does QA describe the supplied spectral dimension? | Reported band count equals the fixture band count. | Inspect header parsing and cube orientation. |
| `delta_diagnostic_matches_input` | Does the reported correction magnitude recover the injected change? | Median reported delta matches the known delta within numerical tolerance. | Inspect NoData exclusion, scale conversion, and before/after pairing. |

### Diagnostics recorded for every variation

| Field | Why it is recorded |
| --- | --- |
| `png_bytes` | Rendered image size. |
| `json_bytes` | Machine-readable report size. |
| `median_reported_delta` | Recovered median after-minus-before change. |
| `reported_valid_percent` | QA-reported valid support. |
| `issue_count` | Number of report findings retained for review. |

## Input variations and results

On narrow screens, scroll the table horizontally to see every diagnostic and check.

| Variation | Input variation | Result | Diagnostics | Explicit checks |
| --- | --- | --- | --- | --- |
| `qa_plots-001`<br>Render QA for delta +0.000 and 0% injected NoData. | `correction_delta`=0; `nodata_fraction`=0; `shape_b_y_x`=[4,10,9] | **PASS** | `issue_count`=1; `json_bytes`=3085; `median_reported_delta`=0; `png_bytes`=215175; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |
| `qa_plots-002`<br>Render QA for delta +0.005 and 2% injected NoData. | `correction_delta`=0.005; `nodata_fraction`=0.02; `shape_b_y_x`=[5,11,10] | **PASS** | `issue_count`=2; `json_bytes`=3716; `median_reported_delta`=0.005; `png_bytes`=222599; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |
| `qa_plots-003`<br>Render QA for delta -0.010 and 8% injected NoData. | `correction_delta`=-0.01; `nodata_fraction`=0.08; `shape_b_y_x`=[6,12,11] | **PASS** | `issue_count`=2; `json_bytes`=4026; `median_reported_delta`=-0.00999999; `png_bytes`=223599; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |
| `qa_plots-004`<br>Render QA for delta +0.020 and 15% injected NoData. | `correction_delta`=0.02; `nodata_fraction`=0.15; `shape_b_y_x`=[4,13,12] | **PASS** | `issue_count`=2; `json_bytes`=3598; `median_reported_delta`=0.02; `png_bytes`=227404; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |
| `qa_plots-005`<br>Render QA for delta -0.030 and 25% injected NoData. | `correction_delta`=-0.03; `nodata_fraction`=0.25; `shape_b_y_x`=[5,10,13] | **PASS** | `issue_count`=2; `json_bytes`=3742; `median_reported_delta`=-0.03; `png_bytes`=223818; `reported_valid_percent`=100 | band_count_reported=✓; delta_diagnostic_matches_input=✓; json_written=✓; png_written=✓ |

## What a passing result establishes

Artifact generation and recovery of deliberately injected diagnostic signals.

!!! warning "What it does not establish"
    Human legibility across every display or scientific acceptability of a correction.

The matching real stage checks are explained in the [stage QA test guide](stage-qa-guide.md).

## Example from the real R10C test run

<div class="sb-validation-grid">
  <figure class="sb-validation-figure">
    <a href="../artifacts/r10c-l002-20210915/legacy-qa.png"><img src="../artifacts/r10c-l002-20210915/legacy-qa.png" alt="R10C legacy QA panel" loading="lazy"></a>
    <figcaption>The compatibility panel remains available alongside the more focused stage reports.</figcaption>
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
