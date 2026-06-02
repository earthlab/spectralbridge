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
```

3. Review the output and fix any failing tests before pushing changes.

## Reference
- `test_pipeline_convolution.py` – verifies the NEON pipeline ordering and resampling behavior
- `test_drone_pipeline.py` – verifies local-H5 drone orchestration and QA auditing
- `test_polygon_pipeline.py` / `test_polygon_extraction.py` – verify polygon spectral library workflows
- `test_parquet_export.py` / `test_duckdb_merge.py` – verify Parquet sidecars and merge behavior
- `test_qa/` and `test_qa_summary.py` – verify QA metrics, panels, and drone summary PDFs
- `test_file_sort.py` / `test_sort_core.py` – verify legacy sorting helpers still covered by compatibility tests
- `test_public_api_smoke.py` – imports and inspects every public top-level function under `src/spectralbridge`
- `test_docs_playwright.py` – browser smoke tests for the built MkDocs site; skipped unless `SPECTRALBRIDGE_DOCS_SITE` points at a served site

## Next steps
Add new test modules to expand coverage as you develop additional features.

Last updated: 2026-06-02
