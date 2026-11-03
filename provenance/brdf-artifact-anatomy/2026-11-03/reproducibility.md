# Reproduce the artifact anatomy

This is an isolated read-only historical replay and report, not a production
processing recipe. No source TIFF/H5, correction code, saved model or library is
modified. The analysis-ready **half-diameter** polygon file is used as supplied.

## Inputs and identities

`provenance.json` records repository/historical revisions and all absolute
input paths and SHA256 values. `preservation.json` records their before/after
equality. Large restored H5s, recovered 10 cm source-DN TIFFs and Goldhill cached
stages remain outside the repository. They must be restored at exactly those
identities before a full replay; no download is implied by the scripts.

The historical model JSONs and production QA snapshot are preserved here as
small diagnostic copies. Original model source collection:

```text
i:/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/gordon_goldhill_ruby_20261029_v1/flight_products
```

Read-only retrieval used the existing authenticated GoCommands client:

```bash
/private/tmp/spectralbridge-gocmd/gocmd get \
  i:/iplant/home/shared/earthlab/macrosystems/field-data/output/spectralbridge_processed/gordon_goldhill_ruby_20261029_v1/flight_products/AOP_GOLDHILL_20230814__brdf_model.json \
  /private/tmp/brdf-artifact-anatomy-20261103/models/
```

Equivalent Gordon/Ruby model filenames are in `models/`. The original source
and output identities are in the saved QA and previous experiment manifest.
The current production corrected raster was unavailable locally; the prior
direct production comparison is reused, rather than represented as a fresh
download or comparison. Gordon/Ruby corrected stages are diagnostic replays,
not a newly verified reproduction of missing production raster bytes.

## Scientific analysis and figures

Run from repository root with the scientific environment used for the preceding
investigations (NumPy, SciPy, pandas, GeoPandas, rasterio, h5py and Matplotlib):

```bash
export MPLCONFIGDIR=/private/tmp/spectralbridge-mpl
export OPENBLAS_NUM_THREADS=1
.venv/bin/python provenance/brdf-artifact-anatomy/2026-11-03/analyze.py
.venv/bin/python provenance/brdf-artifact-anatomy/2026-11-03/export_zoom.py
.venv/bin/python provenance/brdf-artifact-anatomy/2026-11-03/figures.py
.venv/bin/python provenance/brdf-artifact-anatomy/2026-11-03/write_report.py
```

`analyze.py` imports the pinned historical correction file only for isolated
reconstruction. Current kernels are used solely for the contrasting angular
design audit. It reuses Goldhill's four cached stage arrays; Gordon/Ruby
historical stages are evaluated in memory, reduced to compact diagnostics and
discarded. `export_zoom.py` selects the nearest qualifying boundary-crossing
polygon to the prior transect, exports the native ROI and records the NDVI-bin
exception. It must run after `analyze.py`, which initially selects a different
diagnostic candidate. The final `selection.json` is authoritative for all
report maps and spectra. No saved production coefficient is refitted or altered.

The compact `*_display.npz`, zoom and transect NPZ files permit figure
regeneration without reopening large production rasters. The figure script can
also accept figure stems to redraw only selected panels. PNGs are high-resolution
raster figures; corresponding SVGs retain vector text/line plots with embedded
raster imagery. Every display scale, RGB selector, sampling stride and numerical
encoding is recorded in `display_contract.json`.

## Report and PDF

`write_report.py` creates `report_pages.json`, Markdown and the executive summary
from one narrative specification. `make_pdf.py` uses ReportLab, Pillow and the
macOS Arial fonts; on another platform substitute an installed Unicode font in
`FONTROOT`. The bundled Codex runtime provided those libraries for this run:

```bash
/Users/tuff/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  provenance/brdf-artifact-anatomy/2026-11-03/make_pdf.py
pdftoppm -scale-to 1350 -png \
  provenance/brdf-artifact-anatomy/2026-11-03/anatomy_of_a_red_artifact.pdf \
  /private/tmp/brdf-artifact-anatomy-20261103/page
```

The 19-page report uses A3 pages, portrait for tall stage/pixel/transect figures
and landscape elsewhere. All rendered pages are visually reviewed. PDF and
Markdown share the same narrative, figures and coefficient table (PDF table
rounds for space; JSON retains full numerical precision).

## Verification

```bash
.venv/bin/python -m pytest -q tests/test_brdf_artifact_anatomy.py \
  tests/test_brdf_diagnostic_controls.py tests/test_radiometric_contract.py
.venv/bin/python provenance/brdf-artifact-anatomy/2026-11-03/verify.py
.venv/bin/ruff check provenance/brdf-artifact-anatomy/2026-11-03/*.py \
  tests/test_brdf_artifact_anatomy.py
python3 scripts/check_docs_links.py
python3 scripts/generate_ai_transparency.py
python3 scripts/generate_ai_transparency.py --check
git diff --check
```

Synthetic helper tests check sign/nonfinite guards, uncapped positive ratios,
unvisited bins and oriented native-edge comparisons. Actual observations are
verified from supplied tables/arrays, never embedded as package constants or
as synthetic test expectations. Current exact comparisons require zero float32
value and mask mismatches. The preserved prior comparison checked 70,832,700
Goldhill production values/masks. Final output identities are in
`artifact_checksums.json`; it excludes itself.

## Evidence chain and limits

- [Goldhill stage isolation](../../goldhill-correction-diagnosis/2026-10-30/README.md).
- [Radiometric recovery](../../../docs/dev/drone-radiometric-recovery-experiment.md).
- [BRDF identifiability](../../../docs/dev/drone-brdf-identifiability-investigation.md).
- [P162 metadata recovery](../../../docs/dev/photogrammetry-metadata-investigation.md).
- [P164 assumed angles](../../assumed-viewing-angles/2026-11-03/report.md).

The current zero views are placeholders; solar timestamps and terrain source
provenance remain unresolved; physical reflectance calibration is unverified.
Recovered source-DN is the inverse encoding of resampled 10 cm data, not original
camera resolution. Polygon pixel spreads are descriptive, not independent plant
replicates. Negative finite signals remain valid numerical observations unless
masked; no robust display bound changes any analytical statistic. Source-alpha
filtering is explicit analysis eligibility, not a change to production mask
policy. Current rejection prevents unsupported fitting but does not validate
topography, external calibration or spectral libraries.
