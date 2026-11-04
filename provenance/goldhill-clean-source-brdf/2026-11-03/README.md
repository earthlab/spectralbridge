# Clean-source Goldhill BRDF investigation — 2026-11-03

The report is `report.md`; the deliverable PDF is
`goldhill_clean_source_brdf_investigation.pdf`. `scientific_summary.json` records
the twelve required decisions. `verification.json` distinguishes completed
investigation/software hardening from the still unsupported Goldhill correction.
Goldhill calibration remains **HYPOTHETICAL_UNVERIFIED** throughout.

## Reproduce

Run from the repository root with the repository scientific environment:

```bash
export MPLCONFIGDIR=/private/tmp/spectralbridge-mpl
export OPENBLAS_NUM_THREADS=1
P172=provenance/goldhill-clean-source-brdf/2026-11-03
.venv/bin/python "$P172/experiment.py"
.venv/bin/python "$P172/legacy_refits.py"
.venv/bin/python "$P172/geometry_feasibility.py"
.venv/bin/python "$P172/analyze.py"
.venv/bin/python "$P172/neon_control.py" --phase after
.venv/bin/python "$P172/pipeline_validation.py"
.venv/bin/python "$P172/figures.py"
.venv/bin/python "$P172/write_report.py"
# Use a Python environment with ReportLab, Pillow and the documented Arial fonts.
python3 "$P172/make_pdf.py"
.venv/bin/python "$P172/verify.py"
```

The before-control was run with the preserved pre-edit module before hardening:
`neon_control.py --phase before`. All five source snapshots exactly match the
recorded HEAD. The scripts load the pinned old functions and current source
separately; do not replace the snapshots with current code. Do not overwrite
older model folders to bypass a stale signature: preserve them and select a fresh
scratch directory. `pipeline_validation.py` records three separate producer
attempts, including the explicit conditional UTC scenario.

`input_manifest.json` identifies every required source and protected historical
artifact by path and hash. These include temporary local raster inputs, previous
P169/P171 arrays, recovered camera CSV, the polygon GeoPackage, saved historical
BRDF model, and the archived real NEON directional H5. They are not bundled or
fetched automatically. If scratch inputs are unavailable, restore the exact
hash-identified bytes first; do not replace them with a new search result or
silently invent camera geometry. Original acquisition/calibration metadata remain
unresolved even when numerical arrays can be reproduced.

The isolated hypothesis adapter replaces only the calibration precondition in an
AST copy of the actual scientific function and selected nested calls. It delegates
numerical decoding to `Radiometry._affine`. The inherited production
`require_valid()` still rejects that adapter. Zero-view placeholders exist only
in diagnostic cubes; no such arrays are written to the new source H5. C/D refits
are actual historical function executions but their rank-deficient coefficients
are wrapped as diagnostic-only, never applied or exposed as supported models.

## Evidence and scaling

The fixed artifact definitions are in `fixed_regions.json`, with native and common
support retained separately. `classification_memberships.csv` and predictions
preserve identical identity folds and train-only scaling across branches.
Unsupported C/D/E/F branches have no invented raster or PFT score. The real NEON
control is a 120 × 3,000 window with ten selected native channels; it does not
establish MicaSense calibration transfer or full-flight empirical BRDF accuracy.
Both corrected NEON controls additionally pass actual ENVI serialization and
current library-header checks, without official-library regeneration.

Application masking is window bounded. The existing fitter still holds full
scene data/design buffers in memory. No large-VM streaming claim is made. The
experiment stores large pixel arrays only in dated `/private/tmp` scratch space;
compact sufficient statistics, tables, model diagnostics and figures are kept
here. It does not create a bulk pixel-scale Parquet cache. No original source,
previous report, datastore collection or approved library is overwritten.

`verification_logs/p172_final_tests.xml` records 178 tests, zero failures/errors or
skips. The earlier expected regression failures demonstrate the pre-edit gaps;
they are retained as historical evidence, not final acceptance failures. The
intermediate expanded integration failure exposed a dropped scientific header
field; the final test run includes its repair. `pdf_visual_qa.json` records the
rendered-page inspection and final PDF identity. `artifact_checksums.json` covers
this dated compact evidence package (excluding itself and Python bytecode).
