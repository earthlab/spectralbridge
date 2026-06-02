# Tutorial: NEON -> Landsat-Style Reflectance

This tutorial shows how SpectralBridge turns physically corrected NEON ENVI
reflectance into Landsat-style sensor products using sensor spectral response
functions (SRFs).

The output is a set of ENVI cubes and Parquet tables representing NEON
reflectance in target sensor bandspaces such as Landsat TM, ETM+, OLI, and
OLI-2.

---

## Prerequisites

Before running this tutorial, complete:

- [NEON -> corrected ENVI](neon-to-envi.md)

You will need the `*_brdfandtopo_corrected_envi.img` product. If it already
exists and validates, the pipeline will reuse it and continue to sensor
resampling.

---

## 1. Select a corrected ENVI cube

Your corrected data should live inside a per-flightline folder:

```text
output_neon_to_envi/
└── NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance/
    └── NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance_brdfandtopo_corrected_envi.img
```

This corrected ENVI product is the input to sensor bandpass convolution.

---

## 2. Run the pipeline

Sensor resampling runs automatically after BRDF + topographic correction. To
generate or refresh Landsat-style products, re-run the standard pipeline for
the same flight line. Completed earlier stages are skipped.

```bash
spectralbridge-pipeline \
  --base-folder "$BASE" \
  --site-code NIWO \
  --year-month 2023-08 \
  --product-code DP1.30006.001 \
  --flight-lines NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance \
  --max-workers 2 \
  --engine thread
```

Outputs include sensor-specific files such as:

```text
*_landsat_tm_envi.img
*_landsat_tm_envi.hdr
*_landsat_tm_envi.parquet
*_landsat_oli_envi.img
*_landsat_oli_envi.hdr
*_landsat_oli_envi.parquet
```

---

## 3. Understanding Landsat bandpass integration

The convolution stage integrates each corrected NEON spectrum against the
target sensor SRFs. For Landsat OLI-style products, the output bands include
coastal/aerosol, blue, green, red, NIR, SWIR1, and SWIR2 where supported by the
sensor definition.

This process produces reflectance values aligned to Landsat definitions,
enabling:

- direct comparison to satellite imagery
- validation exercises
- cross-scale modeling
- harmonized vegetation index calculations

---

## 4. Inspecting Landsat-style ENVI outputs

Example in Python:

```python
import rioxarray as rxr

landsat = rxr.open_rasterio("path/to/..._landsat_oli_envi.img")
landsat
```

Band order, wavelengths, and metadata are stored in the matching ENVI header.

---

## 5. Checking QA outputs

The QA JSON and QA PNG summarize:

- brightness adjustments used in harmonization
- bandwise statistics after convolution
- wavelength alignment checks
- mask and no-data diagnostics

Use these artifacts to verify successful harmonization before downstream
analysis.

---

## 6. Using the Parquet tables

Sensor Parquet files use one row per pixel-band observation. A quick DuckDB
summary looks like:

```python
import duckdb

duckdb.query("""
    SELECT wavelength_nm, AVG(reflectance) AS mean_reflectance
    FROM '..._landsat_oli_envi.parquet'
    GROUP BY wavelength_nm
    ORDER BY wavelength_nm
""").df()
```

For analysis across all products, start with the merged table:
`*_merged_pixel_extraction.parquet`.

---

## Next steps

- [MicaSense -> Landsat harmonization](micasense-to-landsat.md)
- [Working with Parquet](../usage/parquet.md)
- [Pipeline QA](../pipeline/qa.md)
