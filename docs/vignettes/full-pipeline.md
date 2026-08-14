# Vignette: run the full NEON pipeline

Use this vignette when you want one NEON flightline to move from source HDF5 to
corrected ENVI, harmonized sensor products, Parquet tables, and QA artifacts.

## What you need

- Python 3.10 or newer with `spectralbridge` installed
- enough local storage for the HDF5 and derived products
- a NEON site, acquisition month, product code, and exact flightline identifier

This example uses one NIWO directional-reflectance flightline and the lightweight
thread engine. The same command is safe to run again.

## Run it

```bash
spectralbridge-pipeline \
  --base-folder spectralbridge_output \
  --site-code NIWO \
  --year-month 2023-08 \
  --product-code DP1.30006.001 \
  --flight-lines NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance \
  --engine thread \
  --max-workers 2
```

The command runs the ordered, restart-safe workflow:

1. acquire the NEON HDF5;
2. export the raw ENVI cube;
3. fit and write correction parameters;
4. apply BRDF and topographic correction;
5. harmonize all configured target sensors;
6. export and merge Parquet tables; and
7. render QA outputs.

## Confirm the result

Set the flightline identifier once so the expected directory is easy to inspect:

```bash
FLIGHT=NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance
find "spectralbridge_output/$FLIGHT" -maxdepth 1 -type f | sort
```

A complete run normally includes:

- `$FLIGHT_brdfandtopo_corrected_envi.img` and `.hdr`;
- one ENVI pair for each configured target sensor;
- per-product `.parquet` files;
- `$FLIGHT_merged_pixel_extraction.parquet`; and
- QA PNG and JSON artifacts.

Exact names and optional products are defined in [Outputs and file
structure](../pipeline/outputs.md).

## Use the analysis-ready table

```python
from pathlib import Path

import duckdb

flight = "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance"
merged = (
    Path("spectralbridge_output")
    / flight
    / f"{flight}_merged_pixel_extraction.parquet"
)

preview = duckdb.read_parquet(str(merged)).limit(5).df()
preview
```

## If the run stops

Do not delete valid outputs. Continue with [Carry On My Wayward
Son](carry-on-wayward-son.md), which explains how the pipeline validates and
reuses completed stages.

For exact CLI arguments and stage contracts, use the [technical
reference](../reference/index.md).
