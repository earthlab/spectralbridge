# Build a bulk cross-run analysis

SpectralBridge has three related, but separate, workflows:

1. **Single flightline:** process one hyperspectral input through correction,
   target-sensor products, extraction, and QA.
2. **Multiple flightlines:** apply that workflow independently to a collection;
   each flightline keeps its own restart-safe outputs.
3. **Bulk analysis:** discover completed or minimally staged flightlines, validate
   them for a selected analysis, create a compact analytical cache, and fit
   population-level comparisons.

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
bytes; estimated cache bytes; exclusion counts; package version; and all output
locations. The linked census adds site/date/product inventories.

Preflight reads paths, sizes, modification times, ENVI headers, small QA JSON,
and Parquet footers where applicable. It does not scan raster pixels or create
the per-flightline cache.

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
identities, transient source disappearance, and extraction failures have stable
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

For completed-flightline inputs, each eligible target ENVI product is read in
bounded windows. Only selected sensors are written to narrow Parquets below
`cache/<flightline-id>/`; valid bands are joined by pixel ID into
`observations.parquet`. ENVI no-data and non-finite values are excluded.
`extraction_workers` defaults to one to avoid saturating shared storage, while
`extraction_chunk_size` bounds raster windows and Parquet row groups.

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
├── cache/
│   └── <flightline-id>/
│       ├── <selected-sensor>.parquet
│       ├── observations.parquet
│       ├── extraction_metadata.json
│       └── status.json
├── database/
│   ├── spectralbridge_bulk.duckdb
│   └── bulk_observations.parquet       # optional
├── analyses/
│   ├── dataset_census/
│   ├── sensor_translation/
│   └── leave_one_site_out/
├── coefficients/
│   ├── candidate_translation_coefficients.parquet
│   └── candidate_translation_coefficients.json
├── tables/
├── figures/
├── reports/
└── logs/
~~~

The DuckDB database contains the same catalogs, an `exclusions` table, a
`bulk_observations` view, and each analysis table. The population stays virtual
by default. Create a portable super-Parquet only when its storage cost is
acceptable:

~~~bash
spectralbridge-bulk /data/completed_products \
  --output-dir /data/portable_bulk_analysis \
  --materialize-observations \
  --threads 8 \
  --memory-limit 16GB \
  --temp-directory /scratch/spectralbridge_bulk
~~~

## Restart and provenance

The source tree remains read only. The run manifest records package version,
available git commit, profile, complete registry/pair configuration, source and
output roots, accepted/excluded units, execution settings, timestamps, and
artifact names. Raster fingerprints use path, size, modification time, header
hash, and readable ENVI metadata. Every cache records its source products,
schema version, source fingerprints, selection, and package version.

An unchanged complete invocation returns `status="reused"`. Changing a selected
source, profile, relationship, registry, integrity rule, or extraction setting
invalidates relevant derived state. A failed extraction writes a status file
and traceback log while other flightlines continue. Pass `force=True` or
`--force` for an intentional rebuild.

## Advanced extension

The immutable `AnalysisProfile`, `ProductDescriptor`, `ProductRegistry`, and
`TranslationPair` types are importable from `spectralbridge.bulk`. Custom
registries belong in calling code or a future package extension, not in the
source archive. Discovery/cache construction is separate from the independently
callable `run_dataset_census`, `run_sensor_translation`, and
`run_leave_one_site_out` analysis modules, so new analyses do not need to
reimplement source validation.

The large production campaign that motivated these checks is a validation case,
not a package data model: no site code, storage hierarchy, flightline count, or
campaign-specific folder name is embedded in the bulk architecture.
