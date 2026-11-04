# Goldhill end-to-end experiment - 2026-11-03

Read `report.md` or `goldhill_end_to_end_validation.pdf` first. This is a completed
experiment with explicit unsupported physical stages, not an approved physical
Goldhill library. `scientific_summary.json` provides the final decisions.

Large local rasters and numeric-only polygon tables are under
`/private/tmp/goldhill-end-to-end-20261103/`; `outputs_manifest.json` records their
sizes and checksums. No large raster/library is copied into this evidence folder.
The numerical tables are intentionally rejected by `require_physical_table()`.

## Restore inputs before reproduction

`input_manifest.json` records exact local source identities, including the new
fixed-10K TIFF, original and old TIFFs, the restored legacy working H5, researcher
half-diameter polygons, supplied camera CSV, unchanged historical correction code,
saved model, and four prior cached historical stage arrays. Restore those exact
inputs from their P168/P165/P160 provenance; do not silently replace the old model
with a new fit. The direct-source TIFF locations are documented in
`docs/dev/goldhill-original-source-investigation.md`.

The additional original photo metadata CSVs must be restored to
`/private/tmp/goldhill-end-to-end-20261103/source_metadata/`. Their exact remote
paths and hashes are in `photo_time_reconciliation.json`. These three-column
metadata exports establish photo IDs/tags, not physical calibration or time-zone
accuracy. No raw-photo archive or camera contributor map is fabricated.

Run from the repository root using the scientific environment:

```bash
export MPLCONFIGDIR=/private/tmp/spectralbridge-mpl
export OPENBLAS_NUM_THREADS=1
.venv/bin/python provenance/goldhill-end-to-end/2026-11-03/run_pipeline.py
.venv/bin/python provenance/goldhill-end-to-end/2026-11-03/audit_photo_times.py
.venv/bin/python provenance/goldhill-end-to-end/2026-11-03/analyze.py
.venv/bin/python provenance/goldhill-end-to-end/2026-11-03/figures.py
.venv/bin/python provenance/goldhill-end-to-end/2026-11-03/write_report.py
```

`make_pdf.py` uses ReportLab and Pillow. They were available in the bundled Codex
Python runtime, independently of the scientific virtualenv. Run that script with
a Python containing those dependencies, render with Poppler, and inspect every
page. `pdf_layout.json` additionally asserts text remains above the footer.
`verify.py` checks inputs, actual membership, guards, fixed-fold predictions,
figure/page inventory and JUnit results; `inventory_outputs.py` hashes the products.
The exact targeted pytest record is `tests.xml`, with the command modules listed
in `targeted_tests.log` and the matching test cases in JUnit.

The pipeline resumes validated source/export/index/subset outputs and retained
historical arrays within this experimental namespace. It does not overwrite
original or production inputs. Initial caller-directory setup failures are kept
in `production_stage_results_initial.json`; corrected final API outcomes are in
`production_stage_results.json`.

## Scientific boundaries

- Physical radiometry is unverified; no current physical SCS+C, BRDF, Landsat
  translation or approved spectral library was created.
- Current H5 has no sensor-view datasets. Legacy zero-view geometry is used only
  in explicitly labeled unchanged historical replays.
- Original photo tags support August 15 and the inherited scene midpoint. Per-pixel
  contributors, explicit clock/time-zone conventions and camera CRS remain open.
- Single-flight, matched-polygon identification is exploratory. Parent/pixel
  leakage is prevented, but independent domain/abundance validation is absent.
- No package defaults, source imagery, official outputs, or CyVerse objects changed.
