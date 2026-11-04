# Goldhill viewing geometry and experimental BRDF — 4 November 2026

`report.md` and the 18-page PDF explain actual experimental results, not only an
audit. Four geometry scenarios each produce BRDF-only and combined native 10 cm
ten-band rasters. **Every Goldhill output is experimental, with unverified
calibration, vertical datum and mosaic contributors.** The old red-line pole is
absent in the new BRDF-only results. Hard assignment adds new seams; combined
correction retains the separate topographic instability. None is approved for
production or official-library ingestion.

## Reusable implementation

`src/spectralbridge/drone_view_geometry.py` provides opt-in pure numerical helpers:

- `NadirFootprint`: explicit image dimensions, focal length, pixel size and size scenario.
- `camera_rays`: height-aware zenith and true-north ground-to-sensor azimuth.
- `footprint_candidates`: ideal rectangular footprint constraints at each local ground height.
- `assign_camera`: deterministic nearest or normalized most-central eligible camera, with -1 for no support.
- `aggregate_kernels`: simulated uniform or centrality-weighted kernel mixtures, with one design row per ground reflectance.

Call these on bounded ground chunks. Inputs must already share a projected metre
CRS; callers supply the grid-to-true north rotation explicitly. The module neither
relabels coordinates nor creates a calibration certificate. It does not change
any default pipeline behavior. Existing shared BRDF equations and all fit/application
safeguards are retained. No viewing angles are averaged to stand in for a mixture.

## Inputs and assumptions

`input_manifest.json` freezes source/P172 artifact hashes. `flight_and_crs.json`
records the independent report/field/raster evidence for EPSG:26913, the conflicting
5070 CSV declaration and the unresolved common vertical datum. `acquisition_path.csv`
retains camera IDs, positions, times, band associations by common station, path
legs and turn candidates. The assumed image-height axis follows flight heading;
optical axes are forced nadir. Recovered rotation matrices are not silently
interpreted as verified camera-world conventions.

`reported_sensor_calibrations.csv` preserves the ten report coefficient/error
rows, including fitted focal lengths, principal point and distortion. Exact
PhotoID-to-sensor/wavelength binding is not certified from the three-column
photo metadata. Nominal ideal rectangles are therefore explicit approximations,
with size, height and axis-rotation sensitivities. This does not imply that
calibration coefficients were absent from the report.

Original Goldhill photo pixels were unavailable in the checked collections. Live
listings and the failed recorded RawData path are retained in `verification_logs`.
`minimum_source_subset.csv` names 40 band photos at four geometry-selected positions
as a concrete small repeated-target source request. Their projected footprints
and condition numbers are candidate geometry, not recovered repeated reflectance.

## Reproduce from the repository root

Restore the exact existing inputs named by the manifest, including earlier scratch
arrays; the scripts do not replace unavailable data with newly searched sources.
Use the repository environment and keep large outputs outside the repository:

```bash
export MPLCONFIGDIR=/private/tmp/spectralbridge-mpl
export OPENBLAS_NUM_THREADS=1
P173=provenance/goldhill-viewing-geometry/2026-11-04
.venv/bin/python "$P173/reconstruct.py"
.venv/bin/python "$P173/fit_experiments.py"
.venv/bin/python "$P173/sensitivity.py"
.venv/bin/python "$P173/sensitivity_fits.py"
.venv/bin/python "$P173/evaluate.py"
.venv/bin/python "$P173/assignment_boundaries.py"
.venv/bin/python "$P173/diagnostic_maps.py"
.venv/bin/python "$P173/source_subset.py"
.venv/bin/python "$P173/intrinsic_audit.py"
.venv/bin/python "$P173/neon_control.py" --phase after
.venv/bin/python "$P173/figures.py"
.venv/bin/python "$P173/write_report.py"
# Use a Python with ReportLab and Pillow plus the documented Arial fonts.
python3 "$P173/make_pdf.py"
.venv/bin/python "$P173/verify.py"
```

Native reconstruction checks exact input/output and implementation hashes before
reusing completed artifacts. Changed bytes require a fresh dated evidence/scratch
namespace. Existing shared model signature validation controls fit-cache reuse;
do not delete or rewrite a stale model to bypass its source/design contract.
A first reconstruction writes its completion/hash manifest only after all native
maps are complete. Individual models persist before application. The experiment
scripts are reproducible research runs, not new integrated production stages.

The same P172 isolated calibration adapter is reused: it replaces only the
experimental calibration precondition in a copied function namespace and retains
`HYPOTHETICAL_UNVERIFIED` radiometry. C additionally supplies explicitly simulated
weighted kernel designs in that isolated namespace and fingerprints their bytes.
Production globals are untouched. Rank, condition, prediction positivity, roundoff,
uncertainty and runtime guards execute in the actual shared functions. The
production decoder still rejects these models/inputs as unverified.

## Outputs and evaluation

Large artifacts live at `/private/tmp/goldhill-viewing-geometry-20261104`:

- `goldhill_experimental_geometry.tif`: A/B views/assignments and C candidate distributions/kernels.
- `A_view_and_kernel_maps_EXPERIMENTAL.tif`, `B_view_and_kernel_maps_EXPERIMENTAL.tif`: angle/relative/kernel/prediction/factor maps.
- `A_brdf_EXPERIMENTAL.tif`, `B_brdf_EXPERIMENTAL.tif`, `C_uniform_brdf_EXPERIMENTAL.tif`, `C_center_brdf_EXPERIMENTAL.tif`.
- Four corresponding `*_combined_EXPERIMENTAL.tif` products; scientific extremes remain visible.
- Native design/output arrays and ROI/transect intermediates for reproducibility.

The fixed historical ROI, transect, exemplar, source polygon index, 144,406
memberships, 157 independent identities, labels, seed, folds and training-only
preprocessing are unchanged. No classifier result selects an experiment parameter.
The full source has 6,683,944 valid-alpha cells; 39 lack terrain. Their exclusion
leaves every established evaluation membership available. All main fits use native
pixels. The 24 sensitivity fits use a fixed every-tenth native-pixel lattice and
are explicitly separate from main native products.

Reconstruction uses three workers with at most 1,024 ground points x565cameras per
worker; it took about143seconds locally. It persists bounded progress and large
maps outside the repo. Existing BRDF fitting remains scene-in-memory; no new
large-VM streaming claim is made. No bulk pixel-scale Parquet cache is created.
All native outputs have exact geometry and experimental unit/status tags.
`large_artifacts.json` records their hashes. Temporary local files are not Data
Store uploads and must be copied deliberately if long-term retention is needed.

`verification.json`, JUnit logs and PDF QA record acceptance. The focused suite
contains 163 passing tests, including nine new geometric/adapter regressions.
The supported real NEON window is unchanged byte-for-byte in corrected values
and masks, in both BRDF-only and combined controls. No source, earlier report,
official library or calibration registry is overwritten.

One old P172 temporary original-TIFF path is no longer available locally; its
expected digest is retained in `historical_source_availability.json`. It is not
used or recreated by this experiment. All current direct inputs and completed
P172 artifacts are verified, alongside every available older expected artifact.
The requested clean source is present and its ten-band conditional decode is
checked exactly against the reused experiment array.
