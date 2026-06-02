# Naming Conventions

## Authoritative helpers

Naming is part of the public workflow contract. Do not construct output paths
ad hoc; use:

- `spectralbridge.paths.FlightlinePaths`
- `spectralbridge.paths.SensorProductPaths`
- `spectralbridge.utils.naming.get_flight_paths`
- `spectralbridge.utils.naming.get_flightline_products`

## NEON flightline identifiers

Current NEON examples use the full flightline stem supplied to the pipeline:

```text
NEON_D13_NIWO_DP1_L019-1_20230815_directional_reflectance
```

SpectralBridge preserves that stem in every per-flightline output. The raw HDF5
is stored at the base folder root:

```text
<base_folder>/<flight_id>.h5
```

All derived products for that flight line live under:

```text
<base_folder>/<flight_id>/
```

## NEON output suffixes

| Pattern | Meaning |
| --- | --- |
| `<flight_id>_envi.img/.hdr/.parquet` | Raw NEON ENVI export and Parquet sidecar |
| `<flight_id>_brdf_model.json` | Scene-level BRDF coefficient model |
| `<flight_id>_brdfandtopo_corrected_envi.img/.hdr/.json/.parquet` | Canonical BRDF + topographic corrected product |
| `<flight_id>_<sensor>_envi.img/.hdr/.parquet` | Sensor-resampled output |
| `<flight_id>_merged_pixel_extraction.parquet` | Merged per-flightline Parquet table |
| `<flight_id>_qa.png/.json/.pdf` | QA artifacts |
| `<flight_id>_qa_metrics.parquet` | QA metrics table |

Supported sensor suffixes currently include:

```text
landsat_tm
landsat_etm+
landsat_oli
landsat_oli2
micasense
micasense_to_match_tm_etm+
micasense_to_match_oli_oli2
```

## Drone output suffixes

The drone workflow preserves drone-native provenance and intentionally uses a
double-underscore separator for drone products:

| Pattern | Meaning |
| --- | --- |
| `<flight_stem>__working.h5` | Run-owned local HDF5 copy |
| `<flight_stem>__envi.img/.hdr` | Drone ENVI export |
| `<flight_stem>__corrected.img/.hdr` | Drone corrected ENVI output |
| `<flight_stem>__polygon_index.parquet` | Polygon-to-pixel lookup |
| `<flight_stem>__polygons.parquet` | Polygon-filtered spectral table |
| `<flight_stem>__qa.png/.json` | Drone QA artifacts |
| `drone_merged.parquet` | Merged drone polygon table |
| `drone_qa_summary.json` | Batch QA summary |

## Common violations and fixes

| Violation | Why it matters | Fix |
| --- | --- | --- |
| Inventing a filename outside the helper APIs | Downstream stages and docs may not find the artifact | Add or update the relevant path helper |
| Renaming NEON outputs to shorter stems | Breaks restart safety and provenance | Preserve the full `<flight_id>` stem |
| Using NEON-style names for drone outputs | Loses drone-native provenance and conflicts with the drone workflow contract | Use the double-underscore drone patterns |
| Replacing Parquet with CSV as the authoritative table | Breaks the high-performance analysis path | Keep Parquet authoritative; CSV sidecars, when present, are convenience copies |
| Changing sensor suffix spelling | Breaks `FlightlinePaths.sensor_products` consumers | Update path helpers, tests, and docs together if a suffix must change |
