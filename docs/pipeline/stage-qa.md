# Stage-by-stage scientific QA

SpectralBridge writes a deterministic QA report after every canonical pipeline
stage. Standard QA runs automatically. It uses the real artifact produced by
that stage and never substitutes simulated scientific results.

The existing `<flight_id>_qa.png`, `.json`, and `.pdf` remain the quick-look and
legacy audit contract. The stage framework adds smaller, focused reports and a
combined cross-stage interpretation under:

```text
<flightline>/qa/
├── stages/
│   ├── 00_acquisition/stage_qa.json|html
│   │   └── overview.png
│   ├── 01_input_data/stage_qa.json|html + overview.png
│   ├── 02_correction_parameters/stage_qa.json|html + overview.png
│   ├── 03_brdf_topographic_correction/stage_qa.json|html + overview.png
│   ├── 04_spectral_convolution/stage_qa.json|html
│   │   ├── overview.png
│   │   └── brightness*.png
│   └── 05_analysis_tables/stage_qa.json|html + overview.png
└── combined/
    ├── combined_qa.json
    ├── combined_qa.html
    ├── combined_qa.pdf
    └── pipeline_evolution.png
```

## Status model

Every check is one of `PASS`, `WARN`, `FAIL`, or `NOT EVALUATED`. A diagnostic
that cannot be supported by the artifacts available to a run must say `NOT
EVALUATED` and record why; it must not silently disappear.

The report records package version, Git revision, artifact fingerprints,
parameters, sampling, thresholds, and whether thresholds are provisional. Large
artifacts use a deterministic size/head/tail fingerprint so routine QA does not
reread tens of gigabytes merely to calculate provenance.

Reflectance diagnostics are reported in physical unit reflectance. When NEON
stores integer-like reflectance, QA reads the persisted `reflectance scale
factor`, divides stored values by that factor, and removes the persisted `data
ignore value` before calculating metrics. The ENVI writer now carries both
fields forward so every downstream stage uses the same contract.

The interpretation layer is deliberately non-destructive. It separates the
observed flight footprint from structural no-data background inside the raster
bounding box, but it does not crop or mask either area. It also labels the
repository's established poor-quality wavelength regions (300–400,
1337–1430, 1800–1960, and 2450–2600 nm) as `known_bad_retained`. Every band and
stored value remains in the source and output files. Reports disclose the
all-band distribution and separately evaluate unexpected extremes in the
remaining usable wavelengths.

## Diagnostics by canonical stage

| Stage | Standard diagnostics | Scientific question | Important limitation |
| --- | --- | --- | --- |
| Acquisition | canonical file existence, size, bounded fingerprint, and artifact-size inventory | Did the expected source arrive intact enough for the next validator? | Reflectance and masks are not evaluated until ENVI export. |
| Input reflectance | labeled RGB approximation or false color, valid-support map, footprint occupancy, within-footprint support, retained bad-band labels, median and 5th–95th percentile spectra, valid fraction by wavelength, reflectance quantiles and extreme fractions | Is there usable spatial and spectral support before correction, and where is known poor-quality information retained? | Source-specific cloud, water, shadow, and saturation fields are reported as unavailable when they are not encoded in the common ENVI contract. Bad-band labels are diagnostic only and do not modify data. |
| Correction parameters | geometry-field coverage, unfiltered persisted geometry ranges, and BRDF coefficient profiles | Are the physical variables required by correction represented, and do persisted parameters contain conspicuous out-of-range values? | Summary geometry is not the same as a pixelwise residual model. Values outside the physical display range are retained and flagged rather than masked. |
| BRDF + topographic correction | matched-scale before/after map, zero-centered difference map, spectral distribution change, paired residual metrics, correction magnitude, and seam score when internal application boundaries exist | Did correction preserve signal and avoid extreme or chunk-aligned artifacts? | The canonical stage persists only the combined output, so separate topo-versus-BRDF attribution is `NOT EVALUATED`. |
| Spectral convolution | output reflectance support, bandwise summaries, chunk-seam score, plus paired undarkened/final Landsat brightness plots and fitted-versus-configured gains | Did the convolved product retain usable support without numerical seams, and was each brightness coefficient applied as configured? | Passing the application test verifies implementation, not whether the empirical coefficient is scientifically optimal. SRF weights are not yet persisted, so per-output-band SRF coverage remains `NOT EVALUATED`. |
| Analysis tables | output existence, DuckDB readability, rows, columns, column names, file sizes, and plots distinguishing extracted from merged tables | Are the analysis products readable and structurally complete, and did the merge carry the expected rows into a wider schema? | The figure reads Parquet metadata and counts through DuckDB rather than loading entire tables. Scientific translation accuracy requires paired observed data and is not inferred from table existence. |
| Combined | stage statuses, pipeline evolution, evaluated seam-score change, first-order cross-stage findings | Where did warnings or artifacts first become visible? | Sensor-triangle and directly acquired Landsat NBAR checks require artifacts outside a canonical NEON-only run. |

## Provisional thresholds

These defaults are operational starting points, not published scientific
acceptance limits. Tune them with a pinned real-data validation campaign.

| Check | Warn | Fail | Direction |
| --- | ---: | ---: | --- |
| Valid reflectance fraction within the observed footprint | 0.90 | 0.70 | lower is worse |
| Negative reflectance fraction | 0.01 | 0.05 | higher is worse |
| Reflectance above 1.2 in usable wavelengths | 0.01 | 0.05 | higher is worse |
| 99th-percentile absolute correction | 0.20 | 0.50 | higher is worse |
| Chunk seam score | 1.50 | 2.50 | higher is worse |
| SRF valid coverage | 0.98 | 0.90 | lower is worse |
| Chunk-invariance numerical tolerance | — | `1e-6` | absolute difference |

Persisted correction geometry receives a separate categorical review: each
field is `PASS` when its stored minimum, mean, and maximum fall within the
field's physical radian range, and the stage is `WARN` when any field needs
review. This is not a masking rule and has no effect on correction outputs.

A `PASS` means the observed metric is within the current threshold, not that the
scene is scientifically perfect. Genuine landscape edges can coincide with
chunk boundaries, and a correction can reduce unwanted dependence while still
distorting ecological signal. Always review the plots and provenance.

Bounding-box footprint fraction is reported as acquisition geometry and has no
universal pass/fail threshold. A narrow or angled flight track can legitimately
occupy much less than the rectangular raster extent. When established bad-band
regions are present, `known_bad_spectral_bands_retained` is `WARN`: this marks
known poor-quality information for review without treating it as an unexpected
pipeline failure and without removing it.

## Comparable plot contract

Stage-QA schema 1.3 includes plot-contract version 1.1 in every applicable
stage JSON and in the combined JSON. This makes figures from a multi-run
campaign directly comparable instead of letting Matplotlib choose a new scale
for every flightline.

The combined report also writes `qa/combined/combined_qa.pdf` after the HTML is
created. The PDF is a single printable artifact for flightline-to-flightline
review: it includes the combined status, cross-stage interpretation, pipeline
evolution plot, each stage summary, and each available stage diagnostic image.
Use the PDF for side-by-side reading or download; use the JSON for automated
checks and exact numeric comparisons.

| Display | Standard range |
| --- | --- |
| Wavelength x-axis | 350–2600 nm |
| Spectral reflectance y-axis | -0.1–1.6 |
| Reflectance map color scale | 0–1.2 |
| RGB channel stretch | 0–0.6 reflectance |
| Correction difference | -0.2–0.2 reflectance, with one fixed symmetric-log color normalization (`linthresh=0.005`) |
| Valid-fraction plot | 0–1.02 (2% headroom keeps values at 1 visible) |
| Valid-fraction map | 0–1 |
| Negative fraction | 0–0.055 (keeps the provisional 0.05 fail line visible) |
| Chunk seam score | 0–3 |
| Brightness adjustment | -15–5% |
| Persisted geometry summary | -0.1–approximately 6.38 radians |
| BRDF coefficient | -1.5–1.5 |

These are visualization limits, not scientific acceptance thresholds. Values
outside a display range remain unchanged in the products and machine-readable
metrics; affected panels state the fraction outside the displayed range. Plot
contract changes should receive a new contract version so figures within a
campaign never silently change meaning.

Every figure embeds a compact location label derived from the flightline ID:
site, NEON domain, flightline, and acquisition date. Maps use ENVI `map info`
to show projected easting and northing axes when it is available. If valid map
metadata are absent, the map explicitly uses sampled row and column axes rather
than implying geolocation.

## Brightness coefficient audit

The Python brightness figure preserves the statistical intent of the historical
`coef_plots_Ty.qmd`: it plots paired reflectance before and after adjustment,
fits `after ~ before` separately by band, compares the inferred percentage to
the packaged JSON coefficient, and shows band medians before and after. The QA
test passes when the persisted multiplicative gain agrees with the configured
gain within `1e-4` absolute gain. It never refits or replaces the coefficient.

The implementation is reusable through
`spectralbridge.qa.brightness_correction_metrics` and
`spectralbridge.qa.plots.render_brightness_diagnostics`. Invalid cells are
represented as `NaN` for diagnostics and excluded pairwise; the underlying ENVI
products are not changed.

## Run QA

Automatic standard QA:

```bash
spectralbridge-pipeline \
  --base-folder outputs \
  --site-code NIWO \
  --year-month 2023-08 \
  --product-code DP1.30006.001 \
  --flight-lines NEON_D13_NIWO_DP1_L019-1_20230815_directional_reflectance \
  --engine thread --max-workers 1 --qa-mode standard
```

Rebuild reports from an existing completed flightline:

```bash
spectralbridge-stage-qa \
  --flightline-dir outputs/NEON_D13_NIWO_DP1_L019-1_20230815_directional_reflectance \
  --mode deep --force
```

`deep` increases deterministic sampling and the number of wavelengths inspected
for seams. The reusable API also exposes `chunk_invariance_metrics`,
`spectral_response_support`, `translation_edge_metrics`,
`grouped_residual_metrics`, `path_consistency_metrics`,
`cycle_consistency_metrics`, and residual metrics for controlled reruns and
translation-validation workflows. These helpers evaluate predictions supplied
by a validation workflow; they do not fit a model or relabel training residuals
as held-out evidence.

## Real-data example

The full framework was exercised on a 2.4 GB R10C directional-reflectance HDF5
flightline, through ENVI export, BRDF/topographic correction, spectral
convolution, polygon extraction, Parquet merge, legacy QA, and deep stage QA.
The run completed and produced all expected outputs. The revised report-only
interpretation returns `WARN`, not `FAIL`: 57.1% is the flight footprint's
occupancy of its rectangular bounding box, while support within that footprint
is 100%. The all-band fraction above 1.2 remains disclosed at 5.93%; 68 known
poor-quality bands are retained and labeled, while the corresponding fraction
over the other 358 wavelengths is 0.0000142.

[Read the real-flightline validation record](../validation/real-data-example.md)
for the exact metrics, interpretation, figures, and compact machine-readable
artifacts retained in the repository.

## Scientific distinctions retained

- NEON and MicaSense can pass through the relevant corrections; Landsat
  Collection 2 NBAR is acquired directly and is not sent through the NEON
  correction chain.
- Spectral convolution creates target-sensor representations. Empirical
  calibration learns translations against observed sensors; they are not the
  same operation.
- Sensor-edge, blocked-validation, path-consistency, and cycle-consistency QA
  are only evaluated when fitted translation artifacts and paired observations
  are supplied. A NEON processing run does not manufacture them.

## Current empirical tuning needs

Before publication, validate thresholds across multiple sites, dates, terrain
conditions, land-cover classes, and illumination geometries. In particular,
establish empirical seam-score distributions for known clean scenes, verify the
report-only wavelength classifications across instruments, decide which
reflectance extremes are scientifically plausible by product, and persist the
actual SRF weights and translation-validation folds needed for later QA.
