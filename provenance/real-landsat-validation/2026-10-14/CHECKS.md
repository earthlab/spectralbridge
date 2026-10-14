# Verification record - 2026-10-14

- Full repository suite: `MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/pytest`: **597 passed, 8 skipped, 29 warnings**, 120.93 seconds. The optional real-window test is one normal skip; the suite never depends on live network.
- Targeted contracts including actual cached real-window integration: set `SPECTRALBRIDGE_REAL_LANDSAT_WINDOW=artifacts/real_landsat_validation/R10C_20210915/cache/LC08_L2SP_033032_20210916_02_T1/actual_surface_reflectance.tif`, then `.venv/bin/pytest -q tests/test_landsat_agreement.py tests/test_landsat_flight_validation.py`: **18 passed**. This verifies the real 30 m seven-band crop without network.
- Focused Ruff over all changed package/example/test files and three provenance scripts: **passed**.
- `python scripts/check_docs_links.py`: **all doc links valid**.
- `mkdocs build --strict`: **passed**; existing non-navigation pages are reported as informational entries, not errors. Navigation is unchanged.
- `python scripts/generate_ai_transparency.py --check`: **six generated artifacts verified** after verbatim request/continue logging.
- `git diff --check -- . ':!provenance/prompts/PROMPT_LOG.md'`: **passed**. Original user wording remains verbatim, including pasted whitespace.
- Executed driver, agreement, report and reused legacy helper code hashes all match the final implementation hashes in the statistics manifest.
- Completed-run restart without network: **54 output/cache mtimes unchanged**; complete result returned from verified checksums.
- Source H5 is 2,532,249,598 bytes, SHA256 `7ad8032cbfca6879b38bf854640031b6fb2547f792e93bc9e915b3633345a8ff`; source, correction/header, response/gain and implementation fingerprints recorded in source_identity.json. Original source was read in place. Search evidence is unsigned (no SAS signature query strings).
- Compact evidence checks: all original owned output checksums verified; 3,583 unique native product/row/column IDs; all full-cell valid coverages >=0.90; identical N across variants/bands and across nine-shift sensitivity comparisons.
- Visual QA: all ten PDF/PNG/SVG scientific figure sets checked, and **all 18 pages of the final PDF rendered with Poppler and inspected**. Narrative is readable; vector appendix retains all scatter outliers, seven discrete bands, shared RGB stretch and poor-case provenance.

Raw logs are in checks/. No commit, push, release, coefficient refit or multi-flight run was performed. Remaining scientific limitations are in RESULTS.md and VALIDATION.md, not hidden as passing tests.
