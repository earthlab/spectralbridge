# Build a production bulk population analysis

Use the bulk pipeline after individual SpectralBridge flightlines have finished.
It is a separate analysis workflow: it does not download data, rerun
corrections, convolve sensors, invoke the drone pipeline, or alter any source
flightline folder.

## 1. Real input model

The input is a read-only staging tree containing completed flightline output
folders copied from distributed workers. Outer folders may carry machine,
worker, job, or collision-avoidance names. Those names are computational
provenance only.

The bulk pipeline recovers scientific identity from each canonical merged
product filename:

~~~text
<canonical-flightline-id>_merged_pixel_extraction.parquet
<canonical-flightline-id>_polygons_merged_pixel_extraction.parquet
~~~

The scientific hierarchy is:

~~~text
site
└── acquisition date
    └── canonical flightline
        └── pixel observations
~~~

Two flightlines copied from the same machine remain separate flightlines.
They are never paired, averaged, or grouped because of their storage location.

If the same canonical flightline ID occurs in different source directories,
every candidate is recorded in the duplicate catalog and excluded from
population analysis. The pipeline does not choose a winner or silently
double-count it.

## 2. Run a fast preflight first

Choose a completely fresh output directory outside the source tree. A realistic
large-VM invocation is:

~~~bash
spectralbridge-bulk /data/spectralbridge_completed_runs \
  --output-dir /data/spectralbridge_bulk_analysis \
  --threads <N> \
  --memory-limit <XGB> \
  --temp-directory /scratch/spectralbridge_bulk \
  --preflight-only
~~~

Replace the bracketed resource values with limits appropriate for the VM.
DuckDB may spill intermediate work to the supplied scratch directory. The
source staging tree and scratch/output directories must be separate.

Preflight uses filenames, file metadata, schemas, JSON metadata, and Parquet
footers. It does not scan the complete observation population. Review:

- <code>catalog/flightlines.parquet</code>
- <code>catalog/source_files.parquet</code>
- <code>catalog/duplicates.parquet</code>
- <code>catalog/rejected_sources.parquet</code>
- <code>analyses/dataset_census/dataset_census.md</code>

The catalog records canonical identity, site/date, full and polygon products,
QA and metadata availability, sensors, represented stages, rows, bytes, schema
fingerprints, recoverable brightness and BRDF/topographic state, validity,
duplicates, and original paths.

Ambiguous identity is rejected rather than guessed from a surrounding folder.
Unreadable Parquet candidates also remain visible with their rejection reason.

## 3. Run the analyses

After reviewing preflight, rerun without <code>--preflight-only</code>:

~~~bash
spectralbridge-bulk /data/spectralbridge_completed_runs \
  --output-dir /data/spectralbridge_bulk_analysis \
  --threads <N> \
  --memory-limit <XGB> \
  --temp-directory /scratch/spectralbridge_bulk
~~~

The default <code>--input-kind full</code> uses only full-flightline merged
tables. Polygon companions are cataloged but excluded from observations.

Use <code>--input-kind polygon</code> to analyze polygon tables or
<code>--input-kind both</code> only when combining full pixels and their
polygon subsets is scientifically intentional. The latter can count the
polygon pixels again by design.

## 4. Virtual observations are the default

The DuckDB database exposes:

- <code>flightlines</code>: canonical scientific units and processing state
- <code>source_files</code> and <code>bulk_sources</code>: product-level provenance
- <code>duplicates</code>: all excluded duplicate candidates
- <code>rejected_sources</code>: invalid, ambiguous, and duplicate flightlines
- <code>bulk_observations_virtual</code>: union-by-name over accepted originals
- <code>bulk_observations</code>: the analysis-facing observation view
- analysis result tables documented below

By default, <code>bulk_observations</code> reads the original accepted Parquets
virtually. DuckDB projection and predicate pushdown allow an analysis to read
only its required columns. No complete super-Parquet is created.

Every virtual observation receives explicit provenance columns:

~~~text
bulk_source_path
bulk_source_relative_path
bulk_source_kind
bulk_source_id
bulk_flightline_id
bulk_site
bulk_acquisition_date
~~~

Create a portable physical union only when it is really needed:

~~~bash
spectralbridge-bulk /data/spectralbridge_completed_runs \
  --output-dir /data/spectralbridge_bulk_portable \
  --materialize-observations \
  --threads <N> \
  --memory-limit <XGB> \
  --temp-directory /scratch/spectralbridge_bulk
~~~

This writes <code>database/bulk_observations.parquet</code>. For production
collections it may require multi-terabyte disk space.

## 5. Clean output contract

~~~text
bulk_output/
├── catalog/
│   ├── flightlines.parquet
│   ├── source_files.parquet
│   ├── duplicates.parquet
│   ├── rejected_sources.parquet
│   └── bulk_manifest.json
├── database/
│   ├── spectralbridge_bulk.duckdb
│   └── bulk_observations.parquet       # optional only
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

The output directory must be empty on its first run. Existing non-bulk files
are never overwritten. Subsequent runs may reuse or update a directory carrying
its recognized bulk manifest.

## 6. Dataset census

The census reports candidate source directories, accepted and unique canonical
flightlines, duplicate candidates, rejected records, source and accepted bytes,
Parquet-footer row counts, sites, dates/years, sensors, schemas,
translation-eligible flightlines, and major product inconsistencies.

It writes JSON, Parquet breakdowns, and a concise Markdown report under
<code>analyses/dataset_census/</code>. Matching tables are stored in DuckDB.

## 7. Synthetic cross-sensor translation

For each available wavelength-matched pair the pipeline fits:

~~~text
Landsat reflectance = slope × MicaSense reflectance + intercept
~~~

Both axes are synthetic products derived from the same corrected NEON
hyperspectral source. These results describe synthetic sensor translation.
They are not empirical calibration between independently observed instruments.

Each result includes slope, intercept, correlation, R², bias, RMSE, MAE, value
ranges, valid pixels, contributing sources, flightlines, and sites.

Separate tables are written for:

| Table | Statistical meaning |
| --- | --- |
| <code>pixel_pooled.parquet</code> | Every valid pixel has equal weight; large flightlines contribute more. |
| <code>per_flightline.parquet</code> | One regression for every independently processed canonical flightline. |
| <code>per_site.parquet</code> | One pixel-pooled regression within each site. |
| <code>flightline_balanced.parquet</code> | Every flightline has equal total weight, regardless of pixel count. |
| <code>site_balanced.parquet</code> | Every site has equal total weight, regardless of pixels or flightlines. |

The coefficient directory contains the pooled and balanced summaries as
candidate coefficients. They remain explicitly unapproved for empirical field
calibration.

Pixels are nested observations, flightlines are independent processing and
sampling units, and sites are the highest replication level currently modeled.
Billions of pixels are not interpreted as billions of independent landscapes.

### Translation is not brightness adjustment

The bulk analysis consumes values persisted by upstream processing. It does not
fit, apply, remove, or replace the separate percentage brightness adjustment.
Recoverable brightness configuration is cataloged so collections with
inconsistent upstream state can be identified.

## 8. Leave-one-site-out validation

For every compatible band pair and held-out site, the pipeline:

1. fits the linear relationship using pixels from all other sites;
2. applies it to the held-out site's pixels;
3. reports held-out RMSE, MAE, bias, predictive R², correlation, observed versus
   predicted slope/intercept, sample count, and held-out flightline count.

The output is
<code>analyses/leave_one_site_out/leave_one_site_out.parquet</code>, with an
interpretation/provenance JSON beside it. Degenerate fits and collections with
too few sites receive explicit status values rather than fabricated metrics.

## 9. Query the database

~~~python
import duckdb

database = "/data/spectralbridge_bulk_analysis/database/spectralbridge_bulk.duckdb"
with duckdb.connect(database, read_only=True) as con:
    census = con.execute("SELECT * FROM dataset_census_summary").df()
    balanced = con.execute(
        """
        SELECT landsat_sensor, band_index, slope, intercept, r2,
               flightline_count, site_count
        FROM translation_site_balanced
        ORDER BY landsat_sensor, band_index
        """
    ).df()
    held_out = con.execute(
        """
        SELECT held_out_site, landsat_sensor, band_index,
               held_out_rmse, held_out_bias, status
        FROM translation_leave_one_site_out
        ORDER BY held_out_site, landsat_sensor, band_index
        """
    ).df()
~~~

The Python API provides the same options:

~~~python
from spectralbridge import run_bulk_pipeline

result = run_bulk_pipeline(
    "/data/spectralbridge_completed_runs",
    "/data/spectralbridge_bulk_analysis",
    input_kind="full",
    threads=16,
    memory_limit="128GB",
    temp_directory="/scratch/spectralbridge_bulk",
)
~~~

The resource values above are examples, not hard-coded defaults.

## 10. Restart and provenance behavior

The manifest fingerprints the canonical catalog, Parquet size/mtime/schema/row
metadata, selection mode, scientific filters, and materialization choice.
An unchanged complete run returns <code>status="reused"</code>. Adding,
removing, replacing, or rewriting a source Parquet invalidates the derived run
state. Pass <code>--force</code> for an intentional rebuild.

Each analysis table carries a deterministic analysis-run ID tying it to the
manifest and source catalogs. Resource controls are recorded for execution
provenance but do not change scientific weighting.

The initial modules deliberately stop at census, hierarchical linear
translation, and leave-one-site-out validation. Correction-effectiveness,
residual-space, nonlinear, variance-partitioning, learning-curve, population
QA, morphospace, and uncertainty analyses can be added as separate modules
without changing the source catalog or observation-view contracts.
