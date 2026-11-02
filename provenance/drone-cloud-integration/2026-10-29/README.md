# Ruby: clean drone notebook end-to-end test

**Passed on 2026-10-29.** One real Ruby drone flight completed download → verified source preparation → correction → four translated products → polygon extraction → bulk analysis → figures/reports → Data Store upload. A subsequent restart reused the scientific products.

This executes the actual code cells in `Drone_2023_2024_Cloud_Production.ipynb`, with the explicit Ruby test setting and a separate work/result directory. It runs locally on macOS against the real Data Store. The Linux cloud container and fresh dependency installation were not exercised; the environment already imports the repaired checkout. `nbformat` was unavailable, so verification uses clean JSON/cell compilation and actual sequential code-cell execution rather than a Jupyter UI validator. This is an integration test, not a complete 2023/2024 campaign or independent field validation.

## What passed

- All seven code cells completed; the initial run took about six minutes including real transfers.
- Four original source H5/TIFF/terrain files downloaded through authenticated GoCommands. Original collections were read-only.
- Original TIFF geographic placement is retained through working H5, native ENVI, corrected ENVI and translated products: zero displacement at the control points.
- All 22,481 extracted records match source locations, polygon GlobalIDs/membership and researcher labels. All 224,810 checked spectral values match the corrected raster. No duplicate or invalid indices.
- All 36,514,800 translation value/mask checks pass across four sensors. Source NoData is not filled; existing terrain masking accounts for the additional exclusions.
- Bulk accepts exactly the one requested flight and creates compact statistics, candidate coefficients, figures, and a PDF report without a pixel-scale bulk cache. A single flight cannot establish cross-site transferability.
- GoCommands checksum-verified uploads complete. All 155 manifested remote files have expected sizes; all four remote manifests match local SHA-256 hashes. A complete 81,144,000-byte corrected raster is downloaded back and has the identical SHA-256 hash.
- Restart completes all notebook cells and preserves all 26 scientific products/checkpoints byte-for-byte with unchanged timestamps. Two run audit records refresh as expected. Uploads are disabled on restart to preserve the initial remote test snapshot.
- Focused drone/producer/notebook and adjacent NEON/ENVI/installed-artifact tests pass, together with Ruff, documentation links, whitespace and regenerated AI-transparency freshness checks.

## Scientific limits

Scientific QA remains **caution**. The explicit ten-band recipe proves correspondence with the historical H5; it does not identify the omitted eleventh TIFF channel or resolve the package/manifest acquisition-date mismatch. Terrain NoData remains unchanged. Existing correction/translation formulas and coefficients are preserved. Workflow, geographic and arithmetic conformance do not certify physical radiometric accuracy.

## Locations and evidence

Work directory:
`/private/tmp/spectralbridge-one-flight-e2e/ruby_integration_20261029_v1`

Dedicated Data Store destination (separate from original source packages):
`i:/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/ruby_integration_20261029_v1`

- `cell_execution.json`, `execution_summary.log`, `test_scope.json`: initial real run.
- `remote_verification.json`, `*_upload_manifest.json`: upload inventory, transfer and corrected-raster readback evidence from the initial run.
- `spatial_check/spatial_diagnostic.png`, `spatial_check/discrepancies.json`, `full_pixel_checks.json`: spatial, membership, full-value and masking checks.
- `restart_cell_execution.json`, `restart_test_scope.json`, `restart_products.json`: final restart evidence. The initial checker also treated refreshed audit timestamps as immutable products; `restart_initial_audit_classification.json` preserves that overly broad check. It found no raster/table changes. The corrected checker reports audits separately.
- `validated_code_snapshot.json`, `validated_workflow.patch`: exact code/input fingerprints and a patch against the recorded base commit. Applying this patch to an isolated clean base reconstructed all nine recorded file hashes. Do not apply it over already recovered edits.
- `run_notebook_test.py`, `check_outputs.py`, `verify_remote_outputs.py`: reproducible test scripts. Review their explicit paths; the first performs real downloads and test uploads unless `--no-upload` is supplied.

The GitHub Desktop stash was recovered and reconciled while retaining the newer notebook/helper, upstream scale-factor rollback, prompt logs and poster work. Working and index trees were separately archived and all 103 directly restored files verified byte-for-byte; there was no third-parent untracked snapshot. The obsolete stash was then removed, with no merge conflicts. See `stash_recovery.json`. No commit or push was performed.
