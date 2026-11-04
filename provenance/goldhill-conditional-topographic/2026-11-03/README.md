# Goldhill conditional topographic experiment - 2026-11-03

Calibration: **HYPOTHETICAL_UNVERIFIED**, hypothesis `MicaSense_Metashape_DN_32768`.
No production calibration promotion, BRDF, factor cap, library regeneration or datastore writes.

Read `report.md` or `goldhill_conditional_topographic_experiment.pdf` first.
`scientific_summary.json` contains the direct scientific decisions.

From the repository root, use its existing scientific environment:

```bash
export MPLCONFIGDIR=/private/tmp/spectralbridge-mpl
export OPENBLAS_NUM_THREADS=1
.venv/bin/python provenance/goldhill-conditional-topographic/2026-11-03/experiment.py
.venv/bin/python provenance/goldhill-conditional-topographic/2026-11-03/geometry_audit.py
.venv/bin/python provenance/goldhill-conditional-topographic/2026-11-03/analyze.py
.venv/bin/python provenance/goldhill-conditional-topographic/2026-11-03/median_sensitivity.py
.venv/bin/python provenance/goldhill-conditional-topographic/2026-11-03/additional_checks.py
.venv/bin/python provenance/goldhill-conditional-topographic/2026-11-03/figures.py
.venv/bin/python provenance/goldhill-conditional-topographic/2026-11-03/write_report.py
```

Run `make_pdf.py` using a Python with ReportLab/Pillow; the recorded run used the
bundled Codex Python. Render with `pdftoppm`, then visually inspect every page.
Run targeted tests (see `p171_tests.log` and XML), then `verify.py`. The latter
expects the test XML/logs in the dated temporary paths recorded in the script.

Inputs are read in place. `input_manifest.json` identifies exact source, geometry,
polygon-index, historical-function and historical-result paths/hashes. Existing
P169 source/ancillary preparation and P170 original-to-derivative precision checks
are prerequisites, not repeated source investigations. `terrain_audit.json`
records the independent delivered terrain paths and diagnostic assumptions.
No raw photograph archive or Metashape project is required for this conditional
experiment; their absence still prevents certifying calibration.

Seven Float32 image arrays and native support masks are isolated under
`/private/tmp/goldhill-conditional-topographic-20261103`; approximately 2 GB of
bounded single-flight scratch data. Persistent outputs are compact diagnostics,
masks, per-polygon means, classifications, figures, scripts and reports. They are
not an ordinary bulk pixel-scale Parquet cache or an approved spectral library.
Raw TIFF identity/grid remains the backing source. Scratch arrays can be rebuilt;
no production or historical output is overwritten.

Each script is a separate stage. After interruption, rerun the incomplete stage
and dependent stages, retaining completed prerequisite stages only while their
source hashes and script/configuration remain unchanged. Experimental correction
arrays are recomputed in their own namespace; partial arrays are not completion
records. `experiment_configuration.json` is written only after all experiment
branches and preservation checks finish. `verify.py` checks completion, hashes,
source-to-array spatial centers, masks, folds and guards. This research harness
is not a replacement for normal production checkpointing or a large-VM benchmark.

Current fitting/application functions retain their actual Python code objects in
an isolated copied namespace whose radiometry resolver accepts the local
hypothesis adapter. Production globals remain unchanged. The adapter delegates
the arithmetic to `Radiometry._affine`, keeps status hypothetical and remains
rejected by `Radiometry.require_valid()`. Historical functions are imported and
executed unchanged. No `VALID` or `VERIFIED` calibration object is constructed.

Correction choices were fixed before PFT evaluation. Polygon means are primary
to mirror the prior experiment; polygon medians are a separate aggregation
sensitivity. Do not select a correction by the best score in this exploratory
comparison. Global historical/current scene fits include evaluation reflectance
and are explicitly transductive diagnostic baselines; eligible/Huber/stabilized
fits exclude all evaluation polygons and a 2 m buffer. All classifier training
uses polygon-disjoint folds and training-only scaling.
