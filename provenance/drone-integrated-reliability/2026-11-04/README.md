# Goldhill integrated correction reliability - November 4, 2026

**Scientific status: EXPERIMENTAL.** Numerical decoding is supported; physical
DN/32768 calibration, actual orthomosaic contributors, camera conventions and
vertical datum are unverified. No production archive or approved library is
modified. This is an engineering repair with conditional scientific evidence.

## Deliverables

- `Toward_a_Reliable_Drone_Correction_Pipeline.pdf`: 16-page illustrated report.
- `report.md`, `report_pages.json`: editable narrative and precise page manifest.
- `figures/`: standalone high-resolution PNG and editable SVG figures.
- `product_catalog.json`: seven native GeoTIFFs, hashes, tags and persistent paths.
- `verification.json`: native block-wise equality, exact NEON parity, preserved
  artifact hashes and test-run evidence.
- `native_topographic_diagnostics.csv`, `native_output_extremes.csv`: uncapped
  native denominator tails, back-facing counts, factors and extreme frequencies.
- `final_source_manifest.json`: exact final implementation and script hashes.
- `radiometric_validation.csv`, `native_vs_common_extremes.json`,
  `topographic_coverage.json`: numerical evidence and support definitions.
- `polygon_summaries.csv`, class/confusion CSVs, paired results and separability:
  matched ecological evidence, not physical validation.

Requested native GeoTIFFs and their topographic status map are preserved under
`archive/local/drone-integrated-reliability/2026-11-04/` (intentionally Git-ignored,
about 1.4 GB). Provenance files are compact and versionable. The catalog uses
absolute paths for this run; do not commit the native rasters to Git.

## Reproduce

Run from repository root with the scientific project environment. Inputs are
local research files declared in `input_manifest.json` and the P172/P173
provenance scripts. They are **not bundled** with the compact report. Scratch
paths identify this exact run, not a portable input discovery API. Restore those
inputs at their declared locations, or explicitly update the research-script
paths and record a new run. Check hashes before interpreting a rerun.

```bash
export MPLCONFIGDIR=/private/tmp/spectralbridge-mpl
export OPENBLAS_NUM_THREADS=1
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/run_experiment.py
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/run_homogeneous.py
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/spatial_controls.py
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/evaluate.py
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/neon_control.py after
.venv/bin/python provenance/brdf-artifact-anatomy-part-ii/2026-11-04/collect_evidence.py
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/build_publications.py
python provenance/drone-integrated-reliability/2026-11-04/render_pdf.py
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/topographic_diagnostics.py
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/verify.py
.venv/bin/python provenance/drone-integrated-reliability/2026-11-04/package_products.py
```

The final two scientific arrays and figures are reproducible from the same
frozen inputs. Report rendering requires ReportLab and Arial; scientific figures
require NumPy, Matplotlib, Rasterio and the existing package dependencies.
`render_pdf.py` renders both authorized reports, not historical publications.
To inspect, use `pdftoppm -png REPORT.pdf PREFIX` and review every page.

`experiment_support.py` uses the documented P172 isolated research adapter:
functions are cloned into a private namespace where conditional radiometry and
inferred designs can be evaluated. It does **not** alter production globals,
mark physical calibration VALID, or permit ordinary production processing of
hypothetical calibration. The actual correction driver and shared equations are
executed inside that isolation. Do not copy this adapter into production code.

## Policies and resource behavior

SCS+C: positive incidence, slope >=5 degrees for fitting, physical candidate
0-2, 20 m uncertainty clusters, conditional 95% Fieller interval for C and a
positive numerator/denominator over the whole interval. Application denominator
must exceed 0.001 and remain in fit incidence support, except analytic flat
terrain. These are explicit experimental decisions. Unsupported cells are
NoData/status 1, never identity values; missing is 0, corrected is 2. No gain cap.

BRDF: unchanged shared kernels/reference; masks exclude original polygon
memberships plus 20-step Manhattan dilation. The homogeneous branch uses raw
NDVI >0.5, complete 31x31 windows, red/NIR CV <0.15, fixed before PFT evaluation.
Class-specific fits are diagnostics and never create evaluated corrected images.
Cluster covariance changes uncertainty, not OLS point predictions.

The existing fitter holds the loaded cube and per-band eligible regression
arrays; this work does not claim fully out-of-core fitting. SCS+C application
uses 128-row chunks. Research NPY arrays stay in scratch; no ordinary pixel-scale
Parquet cache is added. Long runs print branch and stage progress. Model cache
signatures bind optional masks, groups, provenance and conditioned models.

## Results that must stay paired with their populations

- Native 717 nm combined maxima: previous 63.51085; conditioned 1.78036.
- On shared all-ten-band support: previous 0.65503; conditioned 0.68932.
- All-ten-band support: 6,613,717 pixels. Different per-band counts are retained.
- Integrated ecology: 157 original identities, 142,637 common memberships,
  fixed folds. Raw BA 68.30%; controlled BRDF 69.39%; conditioned combined
  66.42%; paired intervals include zero. No decisive ecological gain established.
- 27 sampled controls: three unsupported subsets. Shifted reflectance can fit
  as well as the original, exposing spatial confounding.
- Real NEON control: exact unchanged outputs for BRDF-only and combined,
  3.6 million values each. This is regression preservation, not drone validation.
- 175 focused tests plus five additional contract cases passed (180 unique).
  The second 17-test module run repeats the original twelve with five additions.

## Smallest unresolved source request

Use `provenance/goldhill-viewing-geometry/2026-11-04/minimum_source_subset.csv`:
40 original band photographs at four existing positions, with original metadata,
verified PhotoID-to-sensor bindings, camera pose convention and height datum.
Supply applied panel/DLS calibration and Metashape radiometric/export settings,
plus contributor/seam/blending metadata if available. These can establish whether
radiometrically comparable repeated target observations are recoverable. The
empty searched photo collection does not prove originals are absent elsewhere.

Gordon and Ruby require comparable clean source/radiometry and viewing evidence
before this full experiment can be honestly extended. No camera geometry was
invented for them. No further user retrieval is necessary to inspect the
completed conditional products and reports.
