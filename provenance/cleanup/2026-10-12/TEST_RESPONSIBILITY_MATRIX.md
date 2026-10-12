# Test and evidence responsibility map

This maps scientific responsibilities to existing bounded software tests, not a
coverage percentage or a claim of independent scientific validation. The complete
local suite passed on Python 3.12; live-data/browser availability skips are
recorded separately. Installed wheel and sdist smokes exercised actual installed
code with synthetic fixtures, outside the checkout, with network blocked.

| Responsibility | Representative executable contracts | Evidence boundary / further work |
| --- | --- | --- |
| NEON acquisition | `test_envi_download.py`, `test_neon_filename_parsing.py`, offline acquisition campaign | Mocked/download contracts do not establish service reliability over a campaign |
| HDF5 ingestion / legacy schema | `test_neon_cube.py`, `test_neon_legacy.py`, `test_schema_parity.py`, `test_schema_utils.py` | Small controlled schemas; real malformed upstream products remain explicit failures |
| HDF5 → ENVI | `test_stage_export.py`, installed normal/drone smoke, offline HDF5 campaign | Shape, scale, metadata and file wiring; actual R10C artifacts remain dated evidence |
| Topographic / BRDF correction | `test_brdf_scale.py`, `test_brdf_topo_chunking.py`, `test_brdf_topo_streamlined.py`, offline correction campaign | Fixture arithmetic/chunk/restart contracts; independent terrain/directional validation requires suitable observations |
| Spectral weighting | Offline sensor-convolution cases in `run_validation_campaign.py`, `test_validation_campaign.py`, `test_pipeline_convolution.py` | Arithmetic and stage contracts; measured response provenance and independent sensor agreement remain separate |
| Drone TIFF/HDF5 / geometry | `test_drone_pipeline.py`, `test_drone_solar_qa.py`, installed drone smoke | Wavelength mapping, ancillary alignment, orientation and input-unit handling, not complete validation of all upstream conversions |
| Affine translation / registry | `test_drone_translation.py`, `test_drone_translation_registry.py`, `test_brightness_coefficients.py` | Application and coefficient-schema/scale safeguards; no new empirical calibration |
| Polygon extraction | `test_polygon_extraction.py`, `test_polygon_pipeline.py`, `test_polygons.py` | Geometry/index/table contracts; ecological support must be justified for the study |
| Parquet and merge | `test_parquet_export.py`, `test_duckdb_merge.py`, `test_merge_filter_nodata.py` | Schema, rows, bounded processing and filtering; original source identity remains authoritative |
| QA | `test_qa/`, `test_stage_qa.py`, `test_drone_qa_summary.py`, `test_qa_safe_parquet.py` | Status/plot/metric contracts; a configured pass is not scientific certification |
| Restart / reuse | `test_pipeline_convolution.py`, `test_bulk_streaming_restart.py`, `test_split_across_track.py` | Reuse and invalidation under controlled mutations; production replay still matters |
| Completion / remote production | `test_drone_production.py`, `test_gocmd_upload_helper.py` | Bounded inventory/gate/transfer mocks; no real CyVerse authentication or campaign replay in this cleanup |
| Bulk discovery / compact statistics | `test_bulk_pipeline.py`, `test_bulk_streaming_restart.py`, installed bulk smoke | Source catalog, stable compact sufficient statistics, weighting and immutable-input contracts |
| LOSO / transferability | `test_bulk_pipeline.py`, compact-results tests and installed smoke | Synthetic held-out-site arithmetic, not universal transferability |
| Compact results | `test_bulk_results.py`, installed compact-results smoke | Reads completed compact products, does not reopen production rasters |
| Spectral libraries | `test_bulk_spectral_library.py`, installed library smoke and new offline first example | Schema, finite-value/negative-value/plot policies, report cost and source reuse; no independent field validation |
| Actual Landsat comparison | `test_landsat_validation.py` | Controlled observation/grid/masking interfaces; actual independent agreement needs study data and uncertainty accounting |
| CLI/public API / compatibility | `test_public_api_smoke.py`, `test_cross_sensor_cal_shim.py`, installed artifact console checks | Import/argument/package-data wiring; preserved deprecated aliases are intentional interfaces |
| Documentation examples | `test_example_entrypoints.py`, `test_publication_cleanup.py`, existing notebook compilation guards | New offline example executes public preflight; guarded production examples still require configured real inputs |
| Website | `test_docs_playwright.py`, `check_built_site.py`, `check_docs_links.py` | Desktop/mobile/search/local assets and all rendered internal anchors, not external publisher availability |
| Manuscript/SI | `test_joss_submission.py`, `test_supplement_docs.py`, official renderer | Source structure, completeness, exact fingerprints and readable draft PDF; human declarations/editorial eligibility remain separate |
| Attribution/release metadata | `test_hytools_provenance.py`, `test_release_metadata.py`, metadata checker | File-level notices and synchronized identities; no new license migration claim |

The old `test_resample_math_lite.py` checks a generic SciPy mean-filter operation.
It is not evidence for the spectral-response weighting algorithm. Use the actual
convolution campaign and installed production-path tests for that responsibility.
No numerical/scientific tests were added to inflate coverage. New tests address
actual cleanup regressions: in-memory HDF5 backing store, installed-client argument
forwarding, a runnable public first example, rendered anchors/assets, and canonical
publication/compatibility paths.
