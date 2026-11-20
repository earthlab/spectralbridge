# BRDF benefit audit across Landsat HLS, AOP and drone data

Analysis started 19 November 2026; team report finalized 20 November 2026.
This is a task-specific reproducible evidence folder, **not a Python package**.
No source raster, production model, mask, label, Figure 4 table or QA policy is changed.

## Start here

Read `output/pdf/brdf_benefit_across_aop_drone_landsat_report.pdf` from the repository
root. The primary numerical results are `statistics/identifiability.csv`,
`statistics/separability.csv` and `statistics/separation_changes.csv`.
`analysis_design.json` records the new-run retrospective design before these effect
results were calculated. Historical project outcomes were already known; this is
not a preregistered study.

The measured results do not demonstrate a consistent large PFT benefit. They do
not establish that BRDF is unnecessary for physical accuracy or time series.
The drone primary contrast estimates **incremental BRDF after the same topographic
correction**. AOP archive results estimate **BRDF plus topography together**.
The HLS no-BRDF arm is a **same-grid reconstruction**, not original Collection 2.
Do not pool these effects into a single universal BRDF gain.

## Source data and units

All paths below are relative to the repository root. Sources are read in place;
there is no ordinary pixel-scale Parquet cache and no new full-scene corrected
raster. Existing source products remain immutable.

* HLS cohort: `provenance/landsat-pure-pixels/2026-11-18/expanded-search/round-2/power-directed-expansion/review-batch-2/hls-combined/hls_l30_nominal_95pct_observations.csv`.
  1,241 cells / 61 spatial patches; values are fractional HLS L30 v2 NBAR.
  Nine public granules supply per-pixel SAA/SZA/VAA/VZA and exact target solar
  angle metadata. Classification uses patches, not 1,241 independent replicates.
  Proposed PFT labels are not independently validated. The separate pixel atlas
  and reviewer CSV document that uncertainty. We did not change the cohort.
* AOP library: `Aug_2026_all_polygons_merged_pixel_extraction.parquet`.
  85,706 source pixel rows / 122 flights; matched raw/corrected native spectra;
  3,639 distinct plant identities / 4,807 identity-years across NIWO/WREF/YELL.
  Decode the historical NEON count convention by 0.0001. Native NoData -9999 is
  excluded; finite negative corrected values are retained. The corrected archive
  stage is BRDF + topography. Its historical correction activity/physical adequacy
  cannot be certified by this comparison alone.
* Drone: `provenance/drone-camera-rerun/2026-11-05/site_inputs.json` supplies
  original polygon indices, terrain/solar data and source grids. Native inputs,
  angular design and geometry are under
  `archive/local/drone-correction-stability/2026-11-05/stable_qr_v1/`.
  Frozen fits are under
  `provenance/drone-calibration-translation/2026-11-19/shade-excluded-refit-v2/`.
  Corrected products are under the corresponding
  `archive/local/drone-calibration-translation/2026-11-19/` folders.
  Native physical decoder is 0.0001999969482421875, zero offset. This preserves
  the conditional historical radiometry rather than claiming independent
  reflectance calibration. Use the fractional AOP-derived affine registry at
  `provenance/drone-calibration-translation/2026-11-19/aop-translation-audit/aop_derived_micasense_to_landsat_fractional_reflectance_registry.json`.
  The same mapping is applied to both stages. This mapping is synthetic diagnostic
  evidence, not independently measured sensor interchangeability.
* BRDF-only AOP control: real NEON R10C 2021 source
  `archive/local/validation-input/NEON_D10_R10C_DP1_L002-1_20210915_directional_reflectance.h5`.
  A 120 × 3,000 pixel window and ten native channels near MicaSense wavelengths;
  1 m source pixel size, 20 m grouping. This is a bounded diagnostic, not the
  labelled full AOP library and not an absolute reflectance validation.

`completed.json` files record source/code/output hashes. HLS metadata records the
actual source product IDs and exact angle/reflectance assets. Never substitute
another source, correction version or translation registry without making a new
study version and updating the design.

## Reproduce from the repository root

Use the project's `.venv` with SpectralBridge importable. Scientific dependencies
are NumPy, pandas, SciPy, scikit-learn, PyArrow, rasterio, h5py, Matplotlib,
threadpoolctl and the existing public-HLS access dependencies. HLS reconstruction
also needs a C compiler (`cc`) to compile the pinned official reference kernels.
Report authoring needs ReportLab, Pillow and pypdf; PDF verification uses
pdfplumber and Poppler (`pdftoppm`). Version information for the statistical
runtime is in `statistics/completed.json`.

```bash
export MPLCONFIGDIR=/tmp/spectralbridge-mpl
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
.venv/bin/python examples/brdf_benefit_hls.py
.venv/bin/python examples/brdf_benefit_aop.py
.venv/bin/python examples/brdf_benefit_drone.py
.venv/bin/python examples/brdf_benefit_aop_control.py
.venv/bin/python examples/brdf_benefit_statistics.py
.venv/bin/python examples/summarize_brdf_benefit.py
python3 examples/build_brdf_benefit_report.py
.venv/bin/python examples/verify_brdf_benefit_audit.py
.venv/bin/pytest -q tests/test_brdf_benefit_hls.py tests/test_brdf_benefit_statistics.py
```

For the report builder and PDF checks, select a Python environment containing
ReportLab/Pillow/pypdf/pdfplumber. The generation machine used Codex's bundled
report environment because the project `.venv` lacks those authoring libraries.
Use that environment only for the builder and PDF inspection; use `.venv` for the
scientific analysis. The builder's source-table hashes prevent stale evidence.
The named verifier below needs only the project scientific environment.

Initial HLS reconstruction needs public network access; matching granule caches
are reused after hash checks. AOP/drone/control/stats stages reuse completed
matching checkpoints. An interrupted AOP stage streams its 244 MB source again;
it never persists a pixel table. Model files inside the AOP control use the normal
model cache/validation rules. Do not delete source/model files to force a desired
answer. Code or source changes invalidate corresponding checkpoints.

## Meaning of the files

* `hls/paired_cells.csv`: identical current cells with official c-factors,
  reconstructed pre-NBAR bands, measured/reference angles and rounding bounds.
  `polygon_spectra.csv` is the shared-cell patch median per arm. Official
  RossThick/LiSparseR source is pinned under `source-reference/`.
* `aop/plant_flight_spectra.csv`: projection precedes paired polygon medians.
  `polygon_spectra.csv`: equal-flight plant-year means. `repeat_view_consistency.csv`:
  same-day nominal-ground repeat variance reduced immediately to polygon-day RMS.
  No duplicated same-flight/identity/ground coordinate contributes to that test.
* `drone/all_stage_polygon_spectra.csv`: raw, topographic-only and combined stages
  on each variant's common labelled pixels. Main compact source is
  `conservative_polygon_spectra.csv`; baseline is diagnostic, including failed
  Ruby QA. `coverage.csv` accounts for all 302 original polygons, including two
  without complete paired outputs. There are 300 analysed identities in each
  variant; they need not retain identical pixels between variants. The primary
  test is within variant, not a mask-effect estimate.
* `aop-control/`: current BRDF-only model, fitting/holdout group identities and
  complete QA; held native-channel diagnostics. Within-block angular R² is
  descriptive and land-cover confounded. It is not an accuracy score.
* `statistics/`: paired recognition, prediction rows, train/test memberships,
  per-class recalls, NPC tests and paired standardized separation changes.
  AOP histories stay grouped. Unsupported held-region classes and unmixed-site
  PFT pairs are explicit NA. Zero is not used as a substitute for unsupported.
* `summary/`: readable tables, PNG/SVG figures, QA support and all numerical input
  hashes. Figures are generated from completed compact outputs, without reopening
  production rasters. Plot display bounds never alter the tables or inference.
* `verification.json`: independent cohort/pairing/fold/source consistency checks.
* The PDF's adjacent `.provenance.json` records its bytes, builder and evidence
  hashes. `pdf_quality_checks.json` records rendered-page and text-bound checks.

## Statistical interpretation

Five-band physical reflectance is primary; seven-band AOP/HLS sensitivity is
included in multiplicity families. Recognition uses fixed C=1 balanced logistic
regression, training-only standardization, five identity-grouped folds and
leave-site/domain-out where all five classes survive training. Training is row
based; repeated histories have equal total identity weight in reported metrics.

Changes are corrected minus control; negative accuracy change means lower
recognition. The paired bootstrap resamples identities within true classes;
models/folds stay fixed. These conditional intervals omit model-training
uncertainty and do not establish new-site effects. Whole-domain swaps show the
small-domain limit separately. Nearby polygons may remain correlated.
There are three separately adjusted families: 10 supported recognition contrasts,
96 supported arm-specific NPC tests, and 48 supported separation changes. Each
identity-level/domain-level p-value family gets its own Holm adjustment. Neither
an unadjusted interval excluding zero nor an unadjusted p-value is a multiplicity-
adjusted or generalizable claim. Nonsignificance is not equivalence.

No measured scientist-hours, matched whole-pipeline RAM benchmarks or community
error frequencies exist in these inputs. We report only recorded computation,
QA support, coverage and practical endpoint effects. The local evidence does not
establish a universal BRDF benefit/harm or a sociological explanation for adoption.

## Sharing and FAIR limits

Source identity, units, grouping, methods, exclusions, hashes, output tables,
unsupported cases, script entry points and external primary references are
explicit. The folder is human-readable and reusable with the named sources.
It is **not** an independently validated public data release: some inputs are
local, labels need team review, no new persistent identifier is assigned, and
upstream redistribution/access conditions still apply. Preserve existing project
licensing and source notices; do not infer a new license for upstream NASA code
or research data from this README.
