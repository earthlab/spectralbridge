# Module vignette 4: build analysis tables

Use this module after ENVI products exist and you want analysis-ready tabular
data. The main pipeline writes per-product Parquet sidecars and merges compatible
tables into one flightline-level Parquet.

## Find the merged table

```python
from pathlib import Path

base = Path("spectralbridge_output")
flight = "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance"
flight_dir = base / flight
merged = flight_dir / f"{flight}_merged_pixel_extraction.parquet"

print(merged)
print(merged.exists())
```

If per-product Parquets exist but the merged table does not, run the dedicated
merge command:

```bash
spectralbridge-merge-duckdb --help
```

Use `--help` from the installed version because merge controls can vary by
release. The normal full pipeline performs this merge automatically.

## Explore without loading everything

```python
import duckdb

relation = duckdb.read_parquet(str(merged))
relation.limit(5).df()
```

```python
with duckdb.connect() as connection:
    row_count = connection.execute(
        "SELECT COUNT(*) AS rows FROM read_parquet(?)",
        [str(merged)],
    ).df()

row_count
```

For large products, query with DuckDB or PyArrow instead of eagerly loading the
entire table into pandas.

## Continue

- [Review QA outputs](qa-and-analysis.md)
- [Extract polygon spectra](polygon-extraction.md)
- Technical details: [Parquet outputs](../usage/parquet.md), [output
  contracts](../pipeline/outputs.md), and [merge API](../api/merge_duckdb.md)
