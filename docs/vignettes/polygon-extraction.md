# Module vignette 7: extract polygon spectra

**Notebook:** [View the polygon-extraction notebook in the repository](https://github.com/earthlab/spectralbridge/blob/main/docs/vignettes/notebooks/07_polygon_extraction.ipynb). GitHub displays the cells; clone or download the file to run them.

Use this optional module when you have processed flightline products and a
polygon layer representing plots, crowns, or other sampling units. It creates a
pixel index, filters product Parquets to intersecting pixels, and writes a merged
polygon spectral library.

## What you need

- a processed flightline directory with product Parquet tables;
- a vector file readable by GeoPandas; and
- a reference ENVI product that overlaps the polygons.

Polygons are reprojected to the reference raster. A `polygon_id` field is reused
when present; otherwise the workflow creates identifiers.

## Run it

```python
from spectralbridge.paths import FlightlinePaths
from spectralbridge.polygons import run_polygon_pipeline_for_flightline

flight = "NEON_D13_NIWO_DP1_L020-1_20230815_directional_reflectance"
flight_paths = FlightlinePaths("spectralbridge_output", flight)

result = run_polygon_pipeline_for_flightline(
    flight_paths,
    "field_plots.gpkg",
    products=[
        "envi",
        "brdfandtopo_corrected_envi",
        "landsat_oli_envi",
    ],
)

print(result["polygon_index_path"])
print(result["polygon_merged_parquet"])
```

Choose only products that already exist for the flightline.

## Confirm the result

The key outputs are:

- `*_polygon_pixel_index.parquet`, which records the polygon-to-pixel mapping;
- per-product `*_polygons.parquet` tables; and
- `*_polygons_merged_pixel_extraction.parquet`, the analysis-ready polygon
  spectral library.

Check coordinate alignment and feature counts before using the merged library
for modeling.

## Continue

- [Build analysis tables](analysis-tables.md)
- [Review QA outputs](qa-and-analysis.md)
- Technical details: [polygon pipeline contract](../pipeline/polygons.md) and
  [Parquet outputs](../usage/parquet.md)
