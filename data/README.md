# Repository Data

## Overview

This root `data/` directory is for repository examples, local staging, and
development fixtures. It is not the package data directory used after
installation. Runtime metadata that installed users receive lives under
`src/spectralbridge/data/` and is included through `pyproject.toml`.

Root `data/` is excluded from source distributions by `MANIFEST.in` so local
working data and large staging files do not ship with the Python package by
accident.

## Current Contents

- `aop_macrosystems_data_1_7_25.geojson` - example polygon layer
- `Table_mountain_data/ROI_TM_NEON_LST.geojson` - example Table Mountain ROI
- `hyperspectral_bands.json` - repository copy of sensor band definitions
- `landsat_band_parameters.json` - repository copy of Landsat resampling
  parameters

The JSON files also exist under `src/spectralbridge/data/`, which is the
authoritative packaged location. Keep root copies only when they are useful for
examples or external notebooks; update both locations deliberately if values
change.

## Local Staging Pattern

When using this folder for local runs, create a site/date folder and keep all
large products inside that run-owned directory:

1. Create a new project directory inside `data/`, such as `data/NIWO_2023_08`.
2. Download NEON flightlines into `raw_h5/`:

```python
from spectralbridge.envi_download import download_neon_flight_lines

download_neon_flight_lines(
    out_dir="data/NIWO_2023_08/raw_h5",
    site_code="NIWO",
    product_code="DP1.30006.001",
    year_month="2023-08",
    flight_lines=["NEON_D13_NIWO_DP1_L019-1_20230815_directional_reflectance"],
)
```

3. Run the processing steps to populate `envi/`, `corrected/`, `resampled/`,
   Parquet, merged Parquet, and QA subfolders according to the active pipeline
   documentation.

## Next steps

Clean up local staging data when it is no longer needed. Move anything with
scientific or reproducibility value to a documented archive before removing it
from active development paths.

Last updated: 2026-06-02
