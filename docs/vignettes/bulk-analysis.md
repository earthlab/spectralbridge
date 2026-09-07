# Build a bulk cross-run analysis

SpectralBridge has three related, but separate, workflows:

1. **Single flightline:** process one hyperspectral input through correction,
   target-sensor products, extraction, and QA.
2. **Multiple flightlines:** apply that workflow independently to a collection;
   each flightline keeps its own restart-safe outputs.
3. **Bulk analysis:** discover completed or minimally staged flightlines,
   validate them, stream immutable products in place, and fit population-level
   comparisons from compact sufficient statistics.

The bulk workflow is downstream analysis. It does not download inputs, rerun
correction or convolution, invoke the drone pipeline, or modify source folders.

## Generic input model

A flightline is the atomic scientific unit. Storage folders around it have no
scientific meaning and may be nested arbitrarily:

~~~text
completed_products/
├── transfer_group_01/
│   ├── flight_alpha/
│   │   ├── spectralbridge_flightline.json
│   │   ├── sensor_a.img
│   │   ├── sensor_a.hdr
│   │   ├── sensor_b.img
│   │   └── sensor_b.hdr
│   └── flight_beta/
│       └── ...
└── any/other/layout/
    └── flight_gamma/
        └── ...
~~~

For a generic flightline, add
`spectralbridge_flightline.json` to the scientific-unit directory:

~~~json
{
  "flightline_id": "flight-alpha",
  "site": "example-site",
  "acquisition_date": "2024-06-15"
}
~~~

Only `flightline_id` is required. `site` and an ISO `acquisition_date` are
optional. Canonical NEON directory and merged-product names remain supported
by a built-in identity parser. Custom Python callers can provide other identity
parsers without changing discovery.

Multiple flightlines under one parent remain independent. If one scientific ID
appears in different directories, all copies are reported in
`catalog/duplicates.parquet` and excluded; SpectralBridge does not guess which
copy is authoritative.

Prebuilt `*_merged_pixel_extraction.parquet` and
`*_polygons_merged_pixel_extraction.parquet` inputs remain supported through
`input_mode="merged_parquet"`. Automatic mode prefers identifiable flightline
directories and otherwise uses this compatibility path.

## Analysis profiles and minimal archives

Processing completeness, product availability, and analysis eligibility are
separate catalog fields. The built-in `translation` profile requires a complete
requested sensor relationship, not a raw or corrected hyperspectral cube. A
minimal archive containing only the two target ENVI products and their headers
is therefore valid. Raw/corrected cubes, QA, plots, HTML, and unrelated sensors
are optional unless a custom profile requires them.

Product recognition and translation relationships are centralized in a
`ProductRegistry`. The installed defaults describe SpectralBridge's current
matched MicaSense/Landsat products, while `ProductDescriptor` and
`TranslationPair` support other sensor names, filename patterns, matching
groups, expected band counts, and explicit source-to-target band mappings.

To select one installed relationship, use its pair key:

~~~bash
spectralbridge-bulk /data/completed_products \
  --output-dir /data/bulk_analysis \
  --analysis translation \
  --translation-pair MicaSense_to-match_OLI_and_OLI-2__to__Landsat_8_OLI \
  --preflight-only
~~~

`--sensor` is repeatable and retains only relationships whose source and target
are both selected. A requested relationship never requires unrelated products
that merely happen to be supported by the package.

## Run preflight first

Use a fresh output directory outside the read-only source tree:

~~~python
from spectralbridge import run_bulk_pipeline

result = run_bulk_pipeline(
    "/data/completed_products",
    "/data/bulk_analysis",
    analysis="translation",
    preflight_only=True,
)

print(result["preflight"])
~~~

The structured `preflight` result reports discovered, accepted, duplicate, and
excluded flightlines; the selected profile and relationship keys; required and
optional product roles; available sensors and relationships; selected source
bytes; estimated compact output and bounded diagnostic sample; temporary-disk
estimate; whether a pixel dataset was requested; exclusion counts; package
version; and all output locations. The linked census adds site/date/product
inventories.

Preflight reads paths, sizes, modification times, ENVI headers, small QA JSON,
and Parquet footers where applicable. It does not scan or copy raster pixels.

Review these outputs before the full run:

- `catalog/flightlines.parquet`
- `catalog/source_products.parquet`
- `catalog/exclusions.parquet`
- `catalog/exclusions.json`
- `catalog/exclusions.csv`
- `catalog/duplicates.parquet`
- `analyses/dataset_census/dataset_census.md`

Missing sidecars, zero-byte files, unreadable metadata, invalid dimensions,
incompatible bands, incomplete requested pairs, duplicate products, duplicate
identities, transient source disappearance, and streaming-analysis failures have stable
reason codes. `on_invalid="exclude"` is the population-safe default. Valid
flightlines continue when another one fails. Use `on_invalid="error"` when any
ineligible flightline should make the call raise after diagnostic catalogs are
written. Invalid optional products remain visible but do not invalidate an
otherwise eligible flightline.

## Run translation analysis

After reviewing preflight, rerun without `preflight_only`:

~~~python
result = run_bulk_pipeline(
    "/data/completed_products",
    "/data/bulk_analysis",
    analysis="translation",
)
~~~

For completed-flightline inputs, eligible source and target ENVI products are
opened together and read in deterministic aligned windows. Spatial dimensions,
transform, and CRS must match. A pixel is eligible only when the existing
sensor-wide ENVI no-data/finite rules and the requested reflectance threshold
all pass. Each chunk is immediately reduced into numerically stable bivariate
moments. No sensor Parquet or `observations.parquet` is created.

The first pass writes compact per-flightline statistics. Site, global,
flightline-balanced, and site-balanced fits combine those checkpoints. LOSO
training uses `global statistics - held-out site statistics`; one bounded second
pass computes exact absolute-error and held-out metrics. `extraction_workers`
remains the backward-compatible name for concurrent flightline readers and
defaults to one so disk bandwidth is not oversubscribed.

~~~text
Completed flightline products (read only)
        |
        v
Catalog + validation
        |
        v
Aligned chunked direct reads
        |
        v
Per-flightline sufficient statistics
        |
        v
Population aggregation
        +-- translation models
        +-- site and balanced models
        +-- LOSO
        +-- bounded diagnostics
~~~

For merged-Parquet inputs, `input_kind="full"` selects full-pixel tables,
`"polygon"` selects polygon tables, and `"both"` deliberately combines them.
Combining both can count polygon pixels a second time and should be a conscious
scientific choice.

The translation equation is always recorded explicitly:

~~~text
target reflectance = slope × source reflectance + intercept
~~~

Outputs include pixel-pooled, per-flightline, per-site, flightline-balanced,
and site-balanced fits, plus leave-one-site-out validation. Pixels are nested
within flightlines and sites; the balanced results prevent the largest rasters
from silently becoming the only effective replicates. Built-in matched
MicaSense/Landsat products are synthetic products from one corrected source, so
their coefficients are diagnostic candidates—not empirical field calibration.
Translation coefficients are also distinct from the upstream percentage
brightness adjustment.

## Output contract

~~~text
bulk_analysis/
├── catalog/
│   ├── flightlines.parquet
│   ├── source_files.parquet
│   ├── source_products.parquet
│   ├── exclusions.parquet
│   ├── exclusions.json
│   ├── exclusions.csv
│   ├── duplicates.parquet
│   ├── rejected_sources.parquet
│   └── bulk_manifest.json
├── statistics/
│   ├── translation_sufficient_statistics.parquet
│   ├── diagnostic_sample.parquet       # optional and globally bounded
│   └── flightlines/<flightline-id>/
│       ├── sufficient_statistics.parquet
│       ├── diagnostic_sample.parquet
│       ├── statistics_metadata.json
│       └── status.json
├── database/
│   ├── spectralbridge_bulk.duckdb
│   └── bulk_observations.parquet       # explicit dataset build only
├── analyses/
│   ├── dataset_census/
│   ├── sensor_translation/
│   ├── leave_one_site_out/
│   └── spectral_library/              # optional compact summaries
├── coefficients/
│   ├── candidate_translation_coefficients.parquet
│   └── candidate_translation_coefficients.json
├── tables/
├── figures/
│   └── spectral_library/              # optional summary/full PDFs
├── reports/
└── logs/
~~~

DuckDB stores catalogs, exclusions, sufficient statistics, models, QA summaries,
and provenance. In completed-flightline mode the compatibility
`bulk_observations` view is empty because analysis does not require an observation
layer. Original merged Parquets remain virtual read-in-place inputs.

Analysis and pixel-level dataset construction are separate operations:

~~~text
Completed flightline products
        |
        v
EXPLICIT DATASET BUILD
        |
        v
Harmonized pixel-level dataset
~~~

Use the explicit compatibility builder only when the combined pixel dataset is
itself the requested scientific product:

~~~python
from spectralbridge import build_harmonized_dataset

dataset = build_harmonized_dataset(
    "/data/completed_products",
    "/data/harmonized_pixel_dataset",
    threads=8,
    memory_limit="16GB",
    temp_directory="/scratch/spectralbridge_bulk",
)
~~~

`materialize_observations=True` remains temporarily available for backward
compatibility. New code should use `build_harmonized_dataset` so the disk cost
and scientific intent are explicit. A production analysis invocation is:

~~~bash
spectralbridge-bulk /data/completed_products \
  --output-dir /data/bulk_analysis \
  --extraction-workers 1 \
  --extraction-chunk-size 1024 \
  --diagnostic-sample-size 100000 \
  --diagnostic-seed 42
~~~

## Visualize an existing polygon spectral library

The intentional merged polygon spectral library is different from the removed
temporary observation cache. Pass its existing Parquet path separately: it is
opened read-only and is never copied into the bulk output. The adapter inspects
the footer before analysis, detects the species and available hierarchy fields,
and selects one compatible wavelength-bearing spectral stage. It prefers
`corr_*_wl*nm` columns when present; multiple other stages require an explicit
choice. Wavelengths are parsed from column names, numerically sorted, and kept
paired to their original values. Duplicate wavelengths, duplicate band indices,
non-numeric spectral columns, and schemas without physical wavelengths fail
explicitly.

~~~python
from spectralbridge import run_bulk_pipeline
from spectralbridge.bulk import SpectralLibraryPlotConfig

plots = SpectralLibraryPlotConfig(
    spectral_stage="corr",
    species_sort="count_desc",       # or "alphabetical"
    panels_per_page=4,
    trace_batch_size=2_000,
    summary_band_batch_size=32,
    max_traces_per_group=None,        # default: show every valid trace
    raster_dpi=150,
)

result = run_bulk_pipeline(
    "/data/completed_products",
    "/data/bulk_analysis",
    spectral_library="/data/library/polygons_merged_pixel_extraction.parquet",
    make_summary_plots=True,
    make_full_spectral_reports=True,
    spectral_library_config=plots,
)
print(result["preflight"]["spectral_library_schema"])
print(result["spectral_library"]["reports"])
~~~

`make_summary_plots=True` writes the between-species median overview and species
observation-count report. `make_full_spectral_reports=True` also writes the
species low-alpha ensemble, nested quantile envelopes, and available site,
flightline, and within-species hierarchy reports. It also implies the two
summary PDFs. No report is generated by default because large libraries can
require substantial sequential I/O and rendering time.

The trace alpha is deterministic:

~~~text
alpha = min(0.03, max(0.003, 0.2 / sqrt(rendered trace count)))
~~~

This makes tens of spectra individually legible and progressively lowers alpha
for dense groups. It is a qualitative spectral trace density, not a normalized
probability density. The raw trace layer is rendered batch by batch into a
fixed-size raster; titles, axes, annotations, and the median remain vector PDF
elements. By default every complete finite spectrum contributes. Sampling is
used only when `max_traces_per_group` (or
`--spectral-max-traces-per-group`) is explicitly set, in which case a seeded
DuckDB hash order makes the cap reproducible.

The compact products are `species_summary.parquet`,
`species_band_summary.parquet`, `species_quantiles.parquet`,
`species_median_spectra.parquet`, and `group_counts.parquet`. Quantiles default
to 2.5, 10, 25, 50, 75, 90, and 97.5 percent and use DuckDB
`approx_quantile` in bounded band batches. Complete-spectrum validity requires
every selected-stage value to be finite and at least the run's explicit
`minimum_reflectance` (0.0 by default), matching bulk translation validity.
Valid extreme values above that threshold are retained and determine the shared
report range; there is no undocumented clipping. Memory is bounded by one Arrow
trace batch plus at most the configured page's fixed-size panel rasters during
plotting, and by one configured band batch during summary calculation. The
companion JSON
records source signature, package version, run ID, detected schema, counts,
wavelength range, exact plot configuration, alpha rule, rasterization, sampling,
report paths, page counts, and sizes.

The full suite uses these canonical names when the corresponding grouping field
exists:

- `spectral_library_species_variability.pdf`
- `spectral_library_species_quantiles.pdf`
- `spectral_library_species_medians.pdf`
- `spectral_library_observation_counts.pdf`
- `spectral_library_hierarchical_variability.pdf`
- `spectral_library_site_variability.pdf`
- `spectral_library_flightline_variability.pdf`

These reports are additional products. Dataset census, translation, cross-
sensor, LOSO, and other QA/statistical outputs remain unchanged.

## Restart and provenance

The source tree remains read only. The run manifest records package version,
available git commit, profile, complete registry/pair configuration, source and
output roots, accepted/excluded units, execution settings, timestamps, and
artifact names. Raster fingerprints use path, size, modification time, header
hash, and readable ENVI metadata. Every flightline checkpoint records its source
signatures, algorithm/schema version, band and validity configuration, sampling
configuration, and package version.

An unchanged complete invocation returns `status="reused"`. Changing a selected
source invalidates only that flightline checkpoint; changing a profile,
relationship, registry, integrity rule, or streaming setting invalidates the
affected configuration. A failed streaming analysis is cataloged while other
flightlines continue. Pass `force=True` or
`--force` for an intentional rebuild.

## Advanced extension

The immutable `AnalysisProfile`, `ProductDescriptor`, `ProductRegistry`, and
`TranslationPair` types are importable from `spectralbridge.bulk`. Custom
registries belong in calling code or a future package extension, not in the
source archive. Discovery/statistics construction is separate from the independently
callable `run_dataset_census`, `run_sensor_translation`, and
`run_leave_one_site_out` analysis modules, so new analyses do not need to
reimplement source validation.

The large production campaign that motivated these checks is a validation case,
not a package data model: no site code, storage hierarchy, flightline count, or
campaign-specific folder name is embedded in the bulk architecture.
