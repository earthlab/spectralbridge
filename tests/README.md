# Tests

## Overview
Automated tests ensure the calibration workflow behaves as expected. You should
run them before committing changes to verify that new code or documentation
does not break existing functionality.

## Prerequisites
- Python 3.10+
- `pytest`

## Step-by-step tutorial
1. Execute the full test suite from the repository root:

```bash
pytest
```

2. Run focused tests while iterating on localized changes:

```bash
pytest -q tests/test_drone_pipeline.py
pytest -q tests/test_polygon_pipeline.py
pytest -q tests/test_qa/test_qa_metrics_smoke.py
pytest -q tests/test_public_api_smoke.py
pytest -q tests/test_validation_campaign.py
```

3. Review the output and fix any failing tests before pushing changes.

4. Measure the same branch-aware coverage reported by CI:

```bash
CSCAL_TEST_MODE=unit pytest -q --cov=spectralbridge --cov-branch \
  --cov-report=term --cov-report=xml:coverage.xml \
  --cov-report=json:coverage.json
```

The repository currently enforces a conservative 45% combined coverage floor.
Treat that as a regression guard, not as evidence that every scientific path is
adequately tested. Review the per-module report and prioritize scientifically
important modules with low or zero coverage.

## Validation campaigns

Unit tests answer whether a focused contract still holds. Validation campaigns
run the same workflow functions over a matrix of input variations and retain
diagnostics as evidence for the website.

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl \
  python scripts/run_validation_campaign.py --iterations-per-module 5
python scripts/generate_validation_docs.py
python scripts/generate_validation_docs.py --check
```

The offline campaign uses synthetic and already-present inputs. A 100-case
offline run is useful for state and numerical variation, but it is not evidence
that 100 distinct NEON downloads or flightlines succeeded. Live campaigns must
use a pinned inventory and explicit network, storage, and compute approval.

## Reference
- `test_pipeline_convolution.py` – verifies the NEON pipeline ordering and resampling behavior
- `test_drone_pipeline.py` – verifies local-H5 drone orchestration and QA auditing
- `test_polygon_pipeline.py` / `test_polygon_extraction.py` – verify polygon spectral library workflows
- `test_parquet_export.py` / `test_duckdb_merge.py` – verify Parquet sidecars and merge behavior
- `test_qa/` and `test_qa_summary.py` – verify QA metrics, panels, and drone summary PDFs
- `test_file_sort.py` / `test_sort_core.py` – verify legacy sorting helpers still covered by compatibility tests
- `test_public_api_smoke.py` – imports and inspects every public top-level function under `src/spectralbridge`
- `test_docs_playwright.py` – browser smoke tests for the built MkDocs site; skipped unless `SPECTRALBRIDGE_DOCS_SITE` points at a served site
- `test_validation_campaign.py` – validates the evidence schema and runs one input variation through every offline validation module

## Next steps
Add new test modules to expand coverage as you develop additional features.

Last updated: 2026-08-14
