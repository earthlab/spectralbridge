# Build a bulk cross-run analysis

Use the bulk pipeline after individual SpectralBridge runs have finished. It is
an independent analysis workflow: it does not download data, rerun corrections,
convolve sensors, alter flightline folders, or invoke the drone pipeline.

## 1. Point it at the processed-data tree

The input may be one canonical merged Parquet file or a directory containing
many processed sites, dates, and flightlines. Directory inputs are searched
recursively.

```bash
spectralbridge-bulk ~/processed_spectralbridge \
  --output-dir ~/spectralbridge_bulk_results \
  --threads 4 \
  --memory-limit 8GB
```

The default `--input-kind full` discovers readable files matching:

```text
*_merged_pixel_extraction.parquet
```

It deliberately excludes `*_polygons_merged_pixel_extraction.parquet`. This
prevents polygon subsets from being counted a second time when both the full
and polygon products exist for a flightline.

Choose polygon data explicitly when that is the intended population:

```bash
spectralbridge-bulk ~/processed_spectralbridge \
  --input-kind polygon \
  --output-dir ~/spectralbridge_polygon_bulk
```

`--input-kind both` is available, but use it only when combining the full and
polygon populations is scientifically intentional. The pipeline does not
deduplicate observations across those products.

## 2. What the pipeline builds

The output directory has its own restart-safe file contract:

| Artifact | Purpose |
| --- | --- |
| `bulk_observations.parquet` | Portable union-by-name “super Parquet” containing every accepted source row and source-provenance columns. |
| `bulk_analysis.duckdb` | Queryable catalog with a `bulk_observations` view plus materialized source and coefficient tables. |
| `bulk_sources.parquet` | Inventory of accepted and rejected candidates, row counts, schema fingerprints, and source paths. |
| `synthetic_translation_coefficients.parquet` | Analysis-ready pooled regression table. |
| `synthetic_translation_coefficients.json` | Machine-readable coefficient sidecar with interpretation and provenance. |
| `bulk_manifest.json` | Input inventory, settings, counts, and output names used for restart checks. |

The DuckDB database does not duplicate the large observation table. Its
`bulk_observations` view reads the super Parquet directly, while the smaller
catalog and coefficient tables live in the database.

## 3. How the pooled regressions are calculated

For every wavelength-matched synthetic MicaSense/Landsat band pair found in the
merged tables, the bulk pipeline fits all valid rows together:

```text
Landsat reflectance = slope × MicaSense reflectance + intercept
```

The calculation excludes null, non-finite, negative, and explicitly
error-flagged values. It records slope, intercept, correlation, R², bias, RMSE,
MAE, valid-row count, contributing-source count, and value ranges.

The default weighting is by valid row. A flightline with more valid pixels
therefore contributes more observations than a smaller flightline. This is a
pooled synthetic-sensor diagnostic, not held-out empirical calibration.

### Translation is not brightness adjustment

The bulk pipeline uses values already persisted by each upstream run. If a
normal pipeline run applied the separate Landsat brightness adjustment, the
pooled regression sees those adjusted Landsat values; it does not apply,
remove, or estimate that adjustment itself.

Brightness coefficients are percentage gains. Bulk translation coefficients
are slopes and intercepts relating wavelength-matched synthetic MicaSense and
Landsat values. Keep those artifacts and their provenance separate.

## 4. Query the result

```python
import duckdb

with duckdb.connect("/home/me/spectralbridge_bulk_results/bulk_analysis.duckdb") as con:
    coefficients = con.execute(
        """
        SELECT landsat_sensor, band_index, slope, intercept, r2, sample_count
        FROM synthetic_translation_coefficients
        ORDER BY landsat_sensor, band_index
        """
    ).df()

    sources = con.execute(
        """
        SELECT relative_path, status, row_count, translation_eligible
        FROM bulk_sources
        ORDER BY relative_path
        """
    ).df()
```

The same workflow is available from Python:

```python
from spectralbridge import run_bulk_pipeline

result = run_bulk_pipeline(
    "~/processed_spectralbridge",
    "~/spectralbridge_bulk_results",
    input_kind="full",
    threads=4,
    memory_limit="8GB",
)

print(result["coefficients_json"])
print(result["database"])
```

## 5. Restart and update behavior

The pipeline records each candidate's relative path, file size, modification
time, row count, and schema fingerprint. If the inventory and analysis settings
are unchanged and all outputs validate, a rerun returns `status="reused"`
without rewriting the collection. Adding, removing, or changing a source causes
the bulk artifacts to be rebuilt. Pass `--force` for an intentional rebuild.

Unreadable canonical candidates appear as rejected rows in `bulk_sources` when
other valid inputs remain. A run fails clearly when no readable master tables
are found or, by default, when the collection lacks paired synthetic
MicaSense/Landsat columns. Use `--allow-no-translation` only when an
aggregation-only super Parquet is intentional.

## 6. Relationship to the other pipelines

- The main NEON pipeline creates the corrected, convolved, and merged
  per-flightline inputs.
- The drone pipeline remains a separate local imagery workflow.
- The bulk pipeline reads completed merged tables across many runs and produces
  population-level analysis artifacts.

This separation lets a reviewed bulk coefficient set later become an explicit
input to drone-to-Landsat translation without making coefficient fitting part
of every individual processing run.
