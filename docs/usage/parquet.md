# Working with Parquet Outputs

SpectralBridge writes Parquet sidecars for ENVI products and a merged Parquet
table for each completed flight line. These files are the main analysis entry
point for DuckDB, pandas, or other columnar tools.

---

## Why Parquet?

- Supports efficient columnar reads.
- Compresses well for large flight lines.
- Works cleanly with DuckDB SQL.
- Avoids loading full scenes into memory for simple summaries.

---

## File structure

Typical Parquet files include:

```text
*_envi.parquet
*_brdfandtopo_corrected_envi.parquet
*_landsat_oli_envi.parquet
*_merged_pixel_extraction.parquet
```

Per-product files use one row per pixel-band observation and include columns
such as:

- `flightline_id`
- `row`, `col`, `x`, `y`
- `band`
- `wavelength_nm`
- `fwhm_nm`
- `reflectance`

The merged Parquet combines raw, corrected, and sensor-resampled sidecars into
the per-flightline table named `<flight_id>_merged_pixel_extraction.parquet`.

---

## Quick preview using DuckDB

```python
import duckdb

duckdb.query("""
    SELECT *
    FROM '..._brdfandtopo_corrected_envi.parquet'
    LIMIT 5
""").df()
```

Check dimensions without loading the full table:

```python
duckdb.query("""
    SELECT COUNT(*) AS nrows
    FROM '..._landsat_oli_envi.parquet'
""").df()
```

Summarize a sensor product lazily:

```python
duckdb.query("""
    SELECT wavelength_nm, AVG(reflectance) AS mean_reflectance
    FROM '..._landsat_oli_envi.parquet'
    GROUP BY wavelength_nm
    ORDER BY wavelength_nm
""").df()
```

---

## Loading with pandas

```python
import pandas as pd

df = pd.read_parquet("..._merged_pixel_extraction.parquet")
df.head()
```

Use pandas cautiously for large flight lines. DuckDB is usually better for
filtering or aggregation before collecting results into memory.

---

## Loading with xarray

Parquet-to-xarray workflows work best after pivoting or aggregating data. For
full spatial cubes, the ENVI `.img/.hdr` products remain the easier raster
interface.

---

## Next steps

- [CLI usage](cli.md)
- [Pipeline outputs](../pipeline/outputs.md)
