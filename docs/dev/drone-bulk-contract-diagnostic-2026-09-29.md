# Canonical drone-to-bulk contract diagnostic (2026-09-29)

This trace used the supplied
`NEON_D13_NIWO_test_aligned_orthomosaic.h5` as a read-only input. The drone
pipeline wrote its products beneath a separate temporary output root, and bulk
read those products in place. Because the supplied file was stored directly in
`Downloads`, its generated manifest identity is `Downloads` / `DOWNLOADS`; real
production packages retain their own manifest flight identity.

The identity parser selected `spectralbridge_flightline_manifest` for every row
below. Before the repair, all four source/target pair structures failed because
the translated targets were validated against the NEON convolution band counts.
The repaired contract is shown in the descriptor, semantics, stage, and expected
schema columns.

| Filename | Descriptor key | Role | Semantics | Sensor | Stage | Mode | Detected schema | Expected schema | Pair membership / eligibility | Original exclusion |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Downloads__micasense_to_match_tm_etm+_envi.img` | `drone_micasense_matched_tm_etm` | `target_sensor` | `matched_native_application_input` | MicaSense TM/ETM+ match | `affine_cross_sensor_translation_input` | raster | 4 bands | 4 bands | source of L5 and L7 pairs; structurally valid | none |
| `Downloads__landsat_like_landsat_tm_translated_envi.img` | `drone_landsat_like_5_tm` | `target_sensor` | `landsat_like_translated` | Landsat 5 TM | `affine_cross_sensor_translation` | raster | 4 bands | 4 shared bands | target of L5 pair; application-verification eligible | `incompatible_band_schema`: original `landsat_5_tm` descriptor expected 6 |
| `Downloads__landsat_like_landsat_etm+_translated_envi.img` | `drone_landsat_like_7_etm` | `target_sensor` | `landsat_like_translated` | Landsat 7 ETM+ | `affine_cross_sensor_translation` | raster | 4 bands | 4 shared bands | target of L7 pair; application-verification eligible | `incompatible_band_schema`: original `landsat_7_etm` descriptor expected 6 |
| `Downloads__micasense_to_match_oli_oli2_envi.img` | `drone_micasense_matched_oli` | `target_sensor` | `matched_native_application_input` | MicaSense OLI/OLI-2 match | `affine_cross_sensor_translation_input` | raster | 5 bands | 5 bands | source of L8 and L9 pairs; structurally valid | none |
| `Downloads__landsat_like_landsat_oli_translated_envi.img` | `drone_landsat_like_8_oli` | `target_sensor` | `landsat_like_translated` | Landsat 8 OLI | `affine_cross_sensor_translation` | raster | 5 bands | 5 shared bands | target of L8 pair; application-verification eligible | `incompatible_band_schema`: original `landsat_8_oli` descriptor expected 7 |
| `Downloads__landsat_like_landsat_oli2_translated_envi.img` | `drone_landsat_like_9_oli2` | `target_sensor` | `landsat_like_translated` | Landsat 9 OLI-2 | `affine_cross_sensor_translation` | raster | 5 bands | 5 shared bands | target of L9 pair; application-verification eligible | `incompatible_band_schema`: original `landsat_9_oli2` descriptor expected 7 |
| `Downloads__full.parquet` | `drone_corrected_native_full` | `native_corrected_tabular` | `native_corrected_observation` | native MicaSense | `tabular_extraction` | full | 10 spectral / 21 total columns | inventory contract | not a raster-pair input | none |
| `Downloads__landsat_like_landsat_tm_translated_envi.parquet` | `drone_landsat_5_tm_full` | `translated_tabular` | `landsat_like_translated` | Landsat 5 TM | `affine_cross_sensor_translation` | full | 4 spectral / 36 total columns | 4 spectral plus required translation provenance | catalogs L5 application | none; schema was not validated originally |
| `Downloads__landsat_like_landsat_etm+_translated_envi.parquet` | `drone_landsat_7_etmplus_full` | `translated_tabular` | `landsat_like_translated` | Landsat 7 ETM+ | `affine_cross_sensor_translation` | full | 4 spectral / 36 total columns | 4 spectral plus required translation provenance | catalogs L7 application | none; schema was not validated originally |
| `Downloads__landsat_like_landsat_oli_translated_envi.parquet` | `drone_landsat_8_oli_full` | `translated_tabular` | `landsat_like_translated` | Landsat 8 OLI | `affine_cross_sensor_translation` | full | 5 spectral / 37 total columns | 5 spectral plus required translation provenance | catalogs L8 application | none; schema was not validated originally |
| `Downloads__landsat_like_landsat_oli2_translated_envi.parquet` | `drone_landsat_9_oli_2_full` | `translated_tabular` | `landsat_like_translated` | Landsat 9 OLI-2 | `affine_cross_sensor_translation` | full | 5 spectral / 37 total columns | 5 spectral plus required translation provenance | catalogs L9 application | none; schema was not validated originally |

The four target-raster failures explain the production count exactly:
43 flightlines × 4 translated targets = 172 `incompatible_band_schema`
exclusions. Once those targets were rejected, every flight lacked a complete
source/target relationship, producing 43 `incomplete_translation_pair`
exclusions. The reported 43 `missing_required_product` records are the same
flight-level cascade under the production profile/catalog version: the rejected
translated targets could not satisfy the required target identities. They do
not identify a fifth malformed product.

After the repair, preflight on this generated flight accepted 1 flight, found
all 4 relationships, and emitted no exclusions. The full bulk run read
1,215,506 valid pixels, produced 18 band-level relationship specifications and
54 pooled/balanced candidate rows, and labeled the artifact
`diagnostic_application_verification_only`. These fits verify application of an
existing registry; they are not independent sensor calibration evidence.
