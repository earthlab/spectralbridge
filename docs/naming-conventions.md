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

## Bulk analysis output suffixes

Bulk analysis is a separate post-processing workflow. Its output directory uses
fixed collection-level names rather than NEON or drone flight stems:

| Path | Meaning |
| --- | --- |
| `catalog/flightlines.parquet` | Scientific flightline catalog with identity source, processing completeness, product availability, profile eligibility, and status |
| `catalog/source_files.parquet` | Recursive product inventory and source provenance |
| `catalog/source_products.parquet` | Read-only upstream corrected/raw/target-product inventory |
| `catalog/duplicates.parquet` | Duplicate canonical-ID candidates excluded from analysis |
| `catalog/rejected_sources.parquet` | Invalid, ambiguous, or excluded flightline records |
| `catalog/exclusions.parquet` | Deterministic structured exclusions and reason codes |
| `catalog/exclusions.json` | Portable structured exclusion report |
| `catalog/exclusions.csv` | Tabular exclusion report for non-Parquet tools |
| `catalog/bulk_manifest.json` | Restart, settings, and provenance manifest |
| `statistics/flightlines/<flightline-id>/sufficient_statistics.parquet` | Restart-safe mergeable moments derived by bounded direct reads |
| `statistics/translation_sufficient_statistics.parquet` | Compact collection of all valid flightline/band statistics |
| `statistics/diagnostic_sample.parquet` | Optional globally bounded reproducible pixel-pair sample |
| `database/spectralbridge_bulk.duckdb` | Catalogs, compact statistics, models, exclusions, and provenance |
| `database/bulk_observations.parquet` | Explicit harmonized-dataset build; never created by normal analysis |
| `coefficients/candidate_translation_coefficients.parquet/.json` | Pixel-pooled and balanced source-to-target translation candidates |
| `analyses/bulk_results/*.parquet` | Compact weighting, stability, transferability, pair-band, and attention-flag tables derived from completed model outputs |
| `analyses/bulk_results/bulk_results_summary.json` | Results configuration, compact input fingerprints, overview, warnings, and restart signature |
| `figures/bulk_results/*.png` | Optional compact translation interpretation figures |
| `reports/bulk_results/bulk_translation_results.md` | Optional Markdown translation interpretation report |
| `analyses/spectral_library/species_summary.parquet` | Species counts, wavelength coverage, and observed reflectance bounds |
| `analyses/spectral_library/species_band_summary.parquet` | Compact per-species/per-wavelength moments and extrema |
| `analyses/spectral_library/species_quantiles.parquet` | Approximate spectral quantiles at configured probabilities |
| `analyses/spectral_library/species_median_spectra.parquet` | One compact median spectrum per species |
| `analyses/spectral_library/group_counts.parquet` | Species, site, flightline, and polygon contribution counts when available |
| `analyses/spectral_library/species_plot_ranges.parquet` | Full and robust display bounds plus per-species out-of-range counts |
| `analyses/spectral_library/extreme_spectra.parquet` | Bounded ranked traceability records for spectra outside the robust display range |
| `analyses/spectral_library/spectral_library_summary.json` | Source signature, detected schema, plot configuration, reports, and interpretation |
| `figures/spectral_library/spectral_library_species_variability.pdf` | Primary low-alpha report using the configured global or per-group scale |
| `figures/spectral_library/spectral_library_species_variability_full_range.pdf` | Full observed-range audit view from the full report suite |
| `figures/spectral_library/spectral_library_*.pdf` | Other opt-in summary and full spectral variability reports |

Analysis-specific tables live below `analyses/`. These names must not be used
inside individual flightline or drone product contracts.

## Common violations and fixes

| Violation | Why it matters | Fix |
| --- | --- | --- |
| Inventing a filename outside the helper APIs | Downstream stages and docs may not find the artifact | Add or update the relevant path helper |
| Renaming NEON outputs to shorter stems | Breaks restart safety and provenance | Preserve the full `<flight_id>` stem |
| Using NEON-style names for drone outputs | Loses drone-native provenance and conflicts with the drone workflow contract | Use the double-underscore drone patterns |
| Replacing Parquet with CSV as the authoritative table | Breaks the high-performance analysis path | Keep Parquet authoritative; CSV sidecars, when present, are convenience copies |
| Changing sensor suffix spelling | Breaks `FlightlinePaths.sensor_products` consumers | Update path helpers, tests, and docs together if a suffix must change |
