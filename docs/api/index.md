# API Reference

Find a callable by scientific task, then follow its name for the source-derived signature, defaults and docstring. Prefer package exports for supported orchestration; direct-module research APIs retain their existing maturity limits.

The reference is generated without importing scientific dependencies. Each definition renders once at its canonical module path; exported aliases point to that entry. [Download the complete inventory](inventory.json), try the [checked examples](examples.md), or read the [API audit and maintenance policy](audit.md).

Workflow guides explain **how to accomplish a task**; these entries explain **how to call a particular object**. See the [scientific API maturity guide](scientific-analysis.md) before interpreting research outputs.

This revision documents **84 public functions/classes** and **409 advanced functions/classes**. Names that merely look public are not a stability guarantee. Private helpers and CLI/compatibility plumbing are listed separately in the inventory.

## Package exports

Use these existing package-level names in scripts. Aliases lead to their canonical callable entries; constants and source-level type aliases remain distinct from functions.

| Import | Reference |
| --- | --- |
| `spectralbridge.BulkProductionResult` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.BulkProductionResult) |
| `spectralbridge.DroneCampaignConfig` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.DroneCampaignConfig) |
| `spectralbridge.DroneCampaignIncompleteError` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.DroneCampaignIncompleteError) |
| `spectralbridge.DroneCampaignResult` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.DroneCampaignResult) |
| `spectralbridge.DroneCollectionInventory` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.DroneCollectionInventory) |
| `spectralbridge.DroneFlightStatus` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.DroneFlightStatus) |
| `spectralbridge.DroneSource` | Source-level constant or type alias (`spectralbridge.drone_production.DroneSource`); see inventory. |
| `spectralbridge.DroneYearSource` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.DroneYearSource) |
| `spectralbridge.RemoteDronePackage` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.RemoteDronePackage) |
| `spectralbridge.__version__` | Source-level constant or type alias (`spectralbridge.__version__`); see inventory. |
| `spectralbridge.apply_brightness_correction` | [canonical entry](generated/brightness.md#spectralbridge.brightness.apply_brightness_correction) |
| `spectralbridge.build_drone_translation_coefficient_registry` | [canonical entry](generated/drone_translation_registry.md#spectralbridge.drone_translation_registry.build_drone_translation_coefficient_registry) |
| `spectralbridge.build_harmonized_dataset` | [canonical entry](generated/bulk-harmonized.md#spectralbridge.bulk.harmonized.build_harmonized_dataset) |
| `spectralbridge.get_drone_translation_coefficient` | [canonical entry](generated/drone_translation_registry.md#spectralbridge.drone_translation_registry.get_drone_translation_coefficient) |
| `spectralbridge.go_forth_and_multiply` | [canonical entry](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.go_forth_and_multiply) |
| `spectralbridge.inspect_drone_collection` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.inspect_drone_collection) |
| `spectralbridge.inspect_spectral_library_preflight` | [canonical entry](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.inspect_spectral_library_preflight) |
| `spectralbridge.load_brightness_coefficients` | [canonical entry](generated/brightness_config.md#spectralbridge.brightness_config.load_brightness_coefficients) |
| `spectralbridge.load_drone_translation_coefficients` | [canonical entry](generated/drone_translation_registry.md#spectralbridge.drone_translation_registry.load_drone_translation_coefficients) |
| `spectralbridge.make_micasense_vs_landsat_panels` | [canonical entry](generated/sensor_panel_plots.md#spectralbridge.sensor_panel_plots.make_micasense_vs_landsat_panels) |
| `spectralbridge.make_sensor_vs_neon_panels` | [canonical entry](generated/sensor_panel_plots.md#spectralbridge.sensor_panel_plots.make_sensor_vs_neon_panels) |
| `spectralbridge.process_one_flightline` | [canonical entry](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.process_one_flightline) |
| `spectralbridge.run_bulk_pipeline` | [canonical entry](generated/pipelines-bulk.md#spectralbridge.pipelines.bulk.run_bulk_pipeline) |
| `spectralbridge.run_drone_bulk_production` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.run_drone_bulk_production) |
| `spectralbridge.run_drone_campaign` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.run_drone_campaign) |
| `spectralbridge.run_drone_pipeline` | [canonical entry](generated/pipelines-drone.md#spectralbridge.pipelines.drone.run_drone_pipeline) |
| `spectralbridge.run_spectral_library_analysis` | [canonical entry](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.run_spectral_library_analysis) |
| `spectralbridge.stage_drone_collection` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.stage_drone_collection) |
| `spectralbridge.summarize_bulk_results` | [canonical entry](generated/bulk-results.md#spectralbridge.bulk.results.summarize_bulk_results) |
| `spectralbridge.validate_bulk_ready_flightline` | [canonical entry](generated/drone_production.md#spectralbridge.drone_production.validate_bulk_ready_flightline) |

## NEON and drone workflows

[Workflow / scientific context](../vignettes/full-pipeline.md)

| Object | Purpose | Audience |
| --- | --- | --- |
| [`list_neon_products`](generated/envi_download.md#spectralbridge.envi_download.list_neon_products) | Print the available NEON products (utility/debug helper). | advanced |
| [`download_neon_file`](generated/envi_download.md#spectralbridge.envi_download.download_neon_file) | Download a single NEON flight line HDF5. | advanced |
| [`download_neon_flight_lines`](generated/envi_download.md#spectralbridge.envi_download.download_neon_flight_lines) | Download one or more NEON flight lines into out_dir. | advanced |
| [`neon_to_envi_no_hytools`](generated/neon_to_envi.md#spectralbridge.neon_to_envi.neon_to_envi_no_hytools) | Convert NEON .h5 reflectance cubes into ENVI BSQ rasters. | advanced |
| [`run_bulk_pipeline`](generated/pipelines-bulk.md#spectralbridge.pipelines.bulk.run_bulk_pipeline) | Catalog completed flightlines and run population analyses. | public |
| [`DroneCorrectionUnavailableError`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.DroneCorrectionUnavailableError) | Raised when a requested drone correction cannot produce a valid output. | advanced |
| [`DronePipelineIncompleteError`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.DronePipelineIncompleteError) | A run did not satisfy its requested scientific output contract. | advanced |
| [`DroneInputSource`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.DroneInputSource) | Describe one supported discovered drone HDF5/TIFF source and its provenance. | advanced |
| [`DroneOutputRequirement`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.DroneOutputRequirement) | Describe one canonical product required by a selected drone extraction/translation workflow. | advanced |
| [`load_drone_manifest`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.load_drone_manifest) | Load drone flight acquisition datetimes from a CSV manifest. | advanced |
| [`lookup_flight_datetime`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.lookup_flight_datetime) | Return a manifest datetime for a derived drone flight identifier. | advanced |
| [`clean_name`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.clean_name) | Normalise a source name minimally for filesystem-safe output filenames. | advanced |
| [`derive_drone_flight_stem`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.derive_drone_flight_stem) | Derive a drone flight stem from the package folder rather than the inner HDF5. | advanced |
| [`build_drone_output_paths`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.build_drone_output_paths) | Return per-flight drone paths under a dedicated flight directory. | advanced |
| [`required_drone_outputs`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.required_drone_outputs) | Describe the per-flight artifacts required by the requested workflow. | advanced |
| [`summarize_drone_h5_solar_geometry`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.summarize_drone_h5_solar_geometry) | Return solar geometry provenance and summary stats for a drone working H5. | advanced |
| [`diagnose_drone_h5_solar_geometry`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.diagnose_drone_h5_solar_geometry) | Compare source H5 angles with scene-center solar position, read-only. | advanced |
| [`convert_drone_tiff_to_h5`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.convert_drone_tiff_to_h5) | Convert a supported georeferenced multiband reflectance TIFF and aligned ancillary inputs to the drone HDF5 contract. | advanced |
| [`resolve_band_map`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.resolve_band_map) | Map conceptual drone band names to nearest wavelength coordinates, recording selected indices and distances. | advanced |
| [`validate_drone_h5_metadata`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.validate_drone_h5_metadata) | Validate minimally required drone H5 metadata and return a structured summary. | advanced |
| [`export_h5_to_envi`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.export_h5_to_envi) | Export a local H5 cube to ENVI using a drone-native filename stem. | advanced |
| [`build_drone_config`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.build_drone_config) | Build the explicit local drone correction configuration from existing paths, wavelengths and correction flags. | advanced |
| [`apply_drone_corrections`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.apply_drone_corrections) | Apply optional topo/BRDF corrections to a drone ENVI export. | advanced |
| [`collect_drone_spatial_diagnostics`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.collect_drone_spatial_diagnostics) | Collect drone-only raster/polygon overlay diagnostics before extraction. | advanced |
| [`save_drone_overlay_debug_plot`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.save_drone_overlay_debug_plot) | Write a lightweight overlay PNG for drone polygon/raster diagnostics. | advanced |
| [`run_drone_pipeline`](generated/pipelines-drone.md#spectralbridge.pipelines.drone.run_drone_pipeline) | Run the drone pipeline from local HDF5 or reflectance TIFF sources. | public |
| [`is_valid_envi_pair`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.is_valid_envi_pair) | Return True when both ENVI files exist and are non-empty. | advanced |
| [`convolve_resample_product`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.convolve_resample_product) | Stream a corrected BSQ cube through supplied spectral-response weights into canonical target-sensor products. | advanced |
| [`resample_to_sensor_bands`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.resample_to_sensor_bands) | Construct target-band response weights from source wavelength metadata and a registered sensor specification. | advanced |
| [`write_resampled_product`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.write_resampled_product) | Delegate target-response convolution and writing using the canonical sensor output stem. | advanced |
| [`write_resampled_envi_cube`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.write_resampled_envi_cube) | Persist a resampled sensor bandstack to ENVI .img/.hdr files. | advanced |
| [`stage_download_h5`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.stage_download_h5) | Ensure <base_folder>/<flight_stem>.h5 exists and is non-empty. | advanced |
| [`stage_export_envi_from_h5`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.stage_export_envi_from_h5) | Ensure we have the uncorrected ENVI export (.img/.hdr) for this flightline. | advanced |
| [`stage_build_and_write_correction_json`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.stage_build_and_write_correction_json) | Compute + persist BRDF/topo correction parameters (illumination geometry, slope/aspect, | advanced |
| [`stage_apply_brdf_topo_correction`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.stage_apply_brdf_topo_correction) | Apply BRDF + topographic correction using the precomputed JSON. | advanced |
| [`stage_convolve_all_sensors`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.stage_convolve_all_sensors) | Convolve the BRDF+topo corrected ENVI cube into sensor bandstacks. | advanced |
| [`process_one_flightline`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.process_one_flightline) | Run the structured, skip-aware workflow for a single flightline. | public |
| [`sort_and_sync_files`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.sort_and_sync_files) | Generate file sorting list and optionally sync files to iRODS using gocmd. | advanced |
| [`go_forth_and_multiply`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.go_forth_and_multiply) | High-level orchestrator for processing multiple flight lines. | public |
| [`resample_translation_to_other_sensors`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.resample_translation_to_other_sensors) | Run the retained legacy sensor-translation adapter across discovered corrected ENVI products. | advanced |
| [`process_base_folder`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.process_base_folder) | Processes subdirectories in a base folder, finding raster files and applying analysis. | advanced |
| [`process_all_subdirectories`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.process_all_subdirectories) | Searches and processes all subdirectories. | advanced |
| [`jefe`](generated/pipelines-pipeline.md#spectralbridge.pipelines.pipeline.jefe) | A control function that orchestrates the processing of spectral data. | advanced |

## Drone production and translation

[Workflow / scientific context](../vignettes/drone-processing.md)

| Object | Purpose | Audience |
| --- | --- | --- |
| [`RemoteDronePackage`](generated/drone_production.md#spectralbridge.drone_production.RemoteDronePackage) | One candidate ExportPackage discovered without downloading its H5. | public |
| [`DroneYearSource`](generated/drone_production.md#spectralbridge.drone_production.DroneYearSource) | Resolved remote source and manifest expectation for one requested year. | public |
| [`DroneCollectionInventory`](generated/drone_production.md#spectralbridge.drone_production.DroneCollectionInventory) | Serializable remote collection inventory and campaign expectation set. | public |
| [`BulkReadinessValidation`](generated/drone_production.md#spectralbridge.drone_production.BulkReadinessValidation) | Result of classifying one producer directory with bulk's own discovery. | advanced |
| [`StagedDroneInput`](generated/drone_production.md#spectralbridge.drone_production.StagedDroneInput) | Validated local copy of one required remote H5. | advanced |
| [`DroneCampaignConfig`](generated/drone_production.md#spectralbridge.drone_production.DroneCampaignConfig) | Explicit production settings for independent drone flight checkpoints. | public |
| [`DroneFlightStatus`](generated/drone_production.md#spectralbridge.drone_production.DroneFlightStatus) | Durable campaign state for one expected remote flight package. | public |
| [`DroneCampaignResult`](generated/drone_production.md#spectralbridge.drone_production.DroneCampaignResult) | Completed, partial, or failed per-flight campaign outcome. | public |
| [`BulkProductionResult`](generated/drone_production.md#spectralbridge.drone_production.BulkProductionResult) | Top-level campaign, bulk, summary, package, and upload result. | public |
| [`DroneCampaignIncompleteError`](generated/drone_production.md#spectralbridge.drone_production.DroneCampaignIncompleteError) | The intended eligible population was not fully bulk-ready. | public |
| [`validate_bulk_ready_flightline`](generated/drone_production.md#spectralbridge.drone_production.validate_bulk_ready_flightline) | Apply bulk's real discovery/classification contract to one producer output. | public |
| [`inspect_drone_collection`](generated/drone_production.md#spectralbridge.drone_production.inspect_drone_collection) | Inventory remote ExportPackages and required H5s before large transfer. | public |
| [`stage_drone_package`](generated/drone_production.md#spectralbridge.drone_production.stage_drone_package) | Download or reuse one complete H5 while preserving ExportPackage layout. | advanced |
| [`stage_drone_collection`](generated/drone_production.md#spectralbridge.drone_production.stage_drone_collection) | Stage every eligible H5; campaign runners normally stage one at a time. | public |
| [`run_drone_campaign`](generated/drone_production.md#spectralbridge.drone_production.run_drone_campaign) | Stage and run independent restart-safe drone producer checkpoints. | public |
| [`package_drone_bulk_results`](generated/drone_production.md#spectralbridge.drone_production.package_drone_bulk_results) | Build a compact, checksummed closeout package without raw or cache data. | advanced |
| [`verify_uploaded_results`](generated/drone_production.md#spectralbridge.drone_production.verify_uploaded_results) | Verify every packaged file remotely by presence and size/checksum metadata. | advanced |
| [`run_drone_bulk_production`](generated/drone_production.md#spectralbridge.drone_production.run_drone_bulk_production) | Run remote inventory through producer, bulk, reporting, and optional upload. | public |
| [`render_drone_translation_qa`](generated/drone_qa.md#spectralbridge.drone_qa.render_drone_translation_qa) | Render native-corrected versus Landsat-like translated band QA. | advanced |
| [`render_common_support_comparison`](generated/drone_qa.md#spectralbridge.drone_qa.render_common_support_comparison) | Render compact actual-Landsat and optional three-way metric summaries. | advanced |
| [`render_drone_translation_publication`](generated/drone_qa.md#spectralbridge.drone_qa.render_drone_translation_publication) | Render a compact three-panel translation figure from QA JSON values. | advanced |
| [`DroneTranslationBand`](generated/drone_translation.md#spectralbridge.drone_translation.DroneTranslationBand) | One validated source-band to target-band affine relationship. | advanced |
| [`DroneTranslationPlan`](generated/drone_translation.md#spectralbridge.drone_translation.DroneTranslationPlan) | Validated coefficients and band mapping for one Landsat target sensor. | advanced |
| [`load_drone_translation_plans`](generated/drone_translation.md#spectralbridge.drone_translation.load_drone_translation_plans) | Load and scientifically validate bulk coefficients for drone application. | advanced |
| [`translated_output_stem`](generated/drone_translation.md#spectralbridge.drone_translation.translated_output_stem) | Return a precise, sensor-specific Landsat-like translated ENVI stem. | advanced |
| [`matched_source_output_stem`](generated/drone_translation.md#spectralbridge.drone_translation.matched_source_output_stem) | Return the canonical matched-MicaSense product stem used by bulk. | advanced |
| [`ensure_matched_source_product`](generated/drone_translation.md#spectralbridge.drone_translation.ensure_matched_source_product) | Persist the plan's wavelength-selected source bands for bulk analysis. | advanced |
| [`apply_drone_translation`](generated/drone_translation.md#spectralbridge.drone_translation.apply_drone_translation) | Apply one validated affine plan to a corrected native MicaSense ENVI. | advanced |
| [`coefficient_rows_for_parquet`](generated/drone_translation.md#spectralbridge.drone_translation.coefficient_rows_for_parquet) | Return compact band-level provenance records for table enrichment. | advanced |
| [`enrich_translated_spectral_library`](generated/drone_translation.md#spectralbridge.drone_translation.enrich_translated_spectral_library) | Attach constant translation/provenance fields without loading pixel rows. | advanced |
| [`packaged_drone_translation_coefficients_path`](generated/drone_translation_registry.md#spectralbridge.drone_translation_registry.packaged_drone_translation_coefficients_path) | Return the packaged production registry or an actionable error. | advanced |
| [`validate_drone_translation_coefficients`](generated/drone_translation_registry.md#spectralbridge.drone_translation_registry.validate_drone_translation_coefficients) | Validate a complete static production coefficient registry. | advanced |
| [`load_drone_translation_coefficients`](generated/drone_translation_registry.md#spectralbridge.drone_translation_registry.load_drone_translation_coefficients) | Load the packaged or explicitly supplied static production registry. | public |
| [`get_drone_translation_coefficient`](generated/drone_translation_registry.md#spectralbridge.drone_translation_registry.get_drone_translation_coefficient) | Return one unambiguous production target-band coefficient. | public |
| [`build_drone_translation_coefficient_registry`](generated/drone_translation_registry.md#spectralbridge.drone_translation_registry.build_drone_translation_coefficient_registry) | Build a static registry from exact compact bulk result artifacts. | public |
| [`RemoteError`](generated/remote.md#spectralbridge.remote.RemoteError) | Base class for remote collection failures. | advanced |
| [`RemoteAuthenticationError`](generated/remote.md#spectralbridge.remote.RemoteAuthenticationError) | The remote client is installed but not configured for access. | advanced |
| [`RemoteCommandError`](generated/remote.md#spectralbridge.remote.RemoteCommandError) | A remote client command returned a non-zero status. | advanced |
| [`RemoteEntry`](generated/remote.md#spectralbridge.remote.RemoteEntry) | One collection or data object returned by a remote backend. | advanced |
| [`RemoteCollectionBackend`](generated/remote.md#spectralbridge.remote.RemoteCollectionBackend) | Storage operations required by the drone production orchestrator. | advanced |
| [`normalize_remote_path`](generated/remote.md#spectralbridge.remote.normalize_remote_path) | Normalize separators while preserving the i: CyVerse prefix. | advanced |
| [`remote_join`](generated/remote.md#spectralbridge.remote.remote_join) | Join one child name to a normalized remote path. | advanced |
| [`remote_relative_path`](generated/remote.md#spectralbridge.remote.remote_relative_path) | Return a safe POSIX relative path beneath root. | advanced |
| [`parse_gocmd_listing`](generated/remote.md#spectralbridge.remote.parse_gocmd_listing) | Parse the stable collection/data-object lines emitted by gocmd ls. | advanced |
| [`GocmdRemoteBackend`](generated/remote.md#spectralbridge.remote.GocmdRemoteBackend) | CyVerse backend using an existing non-interactive gocmd configuration. | advanced |
| [`remote_parent`](generated/remote.md#spectralbridge.remote.remote_parent) | Return the parent of a normalized remote path. | advanced |

## Bulk processing and compact results

[Workflow / scientific context](../vignettes/bulk-analysis.md)

| Object | Purpose | Audience |
| --- | --- | --- |
| [`PairSpec`](generated/bulk-analyses-common.md#spectralbridge.bulk.analyses.common.PairSpec) | Describe one registered source/target band pair available in a bulk observation view. | advanced |
| [`band_map`](generated/bulk-analyses-common.md#spectralbridge.bulk.analyses.common.band_map) | Map sensor-labelled *_band_<integer> columns to their available band indices. | advanced |
| [`available_pair_specs`](generated/bulk-analyses-common.md#spectralbridge.bulk.analyses.common.available_pair_specs) | Select registered band relationships whose source and target columns both exist. | advanced |
| [`valid_pair_cte`](generated/bulk-analyses-common.md#spectralbridge.bulk.analyses.common.valid_pair_cte) | Projected valid-pair CTE shared by all regression levels. | advanced |
| [`pair_literals`](generated/bulk-analyses-common.md#spectralbridge.bulk.analyses.common.pair_literals) | Build SQL literal columns identifying one registered band relationship. | advanced |
| [`DatasetCensusPaths`](generated/bulk-analyses-dataset_census.md#spectralbridge.bulk.analyses.dataset_census.DatasetCensusPaths) | Resolve compact census tables and report paths beneath a bulk analysis run. | advanced |
| [`run_dataset_census`](generated/bulk-analyses-dataset_census.md#spectralbridge.bulk.analyses.dataset_census.run_dataset_census) | Write metadata-only census tables without scanning observation values. | public |
| [`LeaveOneSiteOutPaths`](generated/bulk-analyses-leave_one_site_out.md#spectralbridge.bulk.analyses.leave_one_site_out.LeaveOneSiteOutPaths) | Resolve held-site fit tables and metadata beneath a bulk analysis run. | advanced |
| [`run_leave_one_site_out`](generated/bulk-analyses-leave_one_site_out.md#spectralbridge.bulk.analyses.leave_one_site_out.run_leave_one_site_out) | Fit on all other sites and score every held-out site. | public |
| [`SensorTranslationPaths`](generated/bulk-analyses-sensor_translation.md#spectralbridge.bulk.analyses.sensor_translation.SensorTranslationPaths) | Resolve pooled, balanced and grouped sensor-fit artifacts beneath a bulk run. | advanced |
| [`run_sensor_translation`](generated/bulk-analyses-sensor_translation.md#spectralbridge.bulk.analyses.sensor_translation.run_sensor_translation) | Run pooled, grouped, and equal-replicate sensor regressions. | public |
| [`SpectralBand`](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.SpectralBand) | Record one wavelength-bearing Parquet column and its band index and nanometer coordinate. | advanced |
| [`SpectralLibrarySchema`](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.SpectralLibrarySchema) | Record the detected group fields, source fingerprint and selected wavelength-bearing spectral stage. | advanced |
| [`SpectralLibraryPlotConfig`](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.SpectralLibraryPlotConfig) | Explicit controls for potentially expensive spectral-library reports. | public |
| [`SpectralLibraryPaths`](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.SpectralLibraryPaths) | Resolve compact spectral-library summaries, trace diagnostics and report locations. | advanced |
| [`inspect_spectral_library`](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.inspect_spectral_library) | Inspect a merged polygon Parquet and select one coherent spectral stage. | public |
| [`trace_alpha`](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.trace_alpha) | Deterministic low-alpha rule for qualitative trace-density ensembles. | advanced |
| [`inspect_spectral_library_preflight`](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.inspect_spectral_library_preflight) | Inspect schema, exact group counts, and approximate report cost without PDFs. | public |
| [`iter_group_spectra`](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.iter_group_spectra) | Yield one group's spectra as bounded NumPy batches without pandas. | advanced |
| [`run_spectral_library_analysis`](generated/bulk-analyses-spectral_library.md#spectralbridge.bulk.analyses.spectral_library.run_spectral_library_analysis) | Build compact summaries and requested PDFs without copying source spectra. | public |
| [`run_streaming_translation_analyses`](generated/bulk-analyses-streaming_translation.md#spectralbridge.bulk.analyses.streaming_translation.run_streaming_translation_analyses) | Derive all model levels and LOSO, using one bounded MAE evaluation pass. | advanced |
| [`canonical_identity_from_product`](generated/bulk-catalog.md#spectralbridge.bulk.catalog.canonical_identity_from_product) | Recover scientific identity from a canonical merged-product filename. | public |
| [`discover_bulk_sources`](generated/bulk-catalog.md#spectralbridge.bulk.catalog.discover_bulk_sources) | Recursively inventory full and polygon merged-Parquet candidates. | public |
| [`build_bulk_catalog`](generated/bulk-catalog.md#spectralbridge.bulk.catalog.build_bulk_catalog) | Build source-file and canonical-flightline catalogs. | public |
| [`catalog_signature_records`](generated/bulk-catalog.md#spectralbridge.bulk.catalog.catalog_signature_records) | Return deterministic manifest-ready catalog records. | advanced |
| [`create_bulk_database`](generated/bulk-dataset.md#spectralbridge.bulk.dataset.create_bulk_database) | Create a temporary database ready for modular analysis execution. | advanced |
| [`observation_columns`](generated/bulk-dataset.md#spectralbridge.bulk.dataset.observation_columns) | List column names in the prepared bulk_observations DuckDB view. | advanced |
| [`build_exclusion_records`](generated/bulk-exclusions.md#spectralbridge.bulk.exclusions.build_exclusion_records) | Build deterministic exclusions from product and flightline validation. | advanced |
| [`ProductValidationError`](generated/bulk-flightline_outputs.md#spectralbridge.bulk.flightline_outputs.ProductValidationError) | Validation failure with a stable machine-readable reason code. | advanced |
| [`find_canonical_flightline_directories`](generated/bulk-flightline_outputs.md#spectralbridge.bulk.flightline_outputs.find_canonical_flightline_directories) | Find scientifically identifiable flightline directories recursively. | advanced |
| [`discover_completed_flightlines`](generated/bulk-flightline_outputs.md#spectralbridge.bulk.flightline_outputs.discover_completed_flightlines) | Inventory identifiable flightlines without reading raster pixels. | advanced |
| [`extract_flightline_cache`](generated/bulk-flightline_outputs.md#spectralbridge.bulk.flightline_outputs.extract_flightline_cache) | Explicitly create or reuse a legacy pixel-level observation cache. | advanced |
| [`build_harmonized_dataset`](generated/bulk-harmonized.md#spectralbridge.bulk.harmonized.build_harmonized_dataset) | Build the legacy combined pixel dataset as an explicit requested product. | public |
| [`FlightlineIdentity`](generated/bulk-identity.md#spectralbridge.bulk.identity.FlightlineIdentity) | Scientific identity for one independently processed flightline. | public |
| [`FlightlineIdentityParser`](generated/bulk-identity.md#spectralbridge.bulk.identity.FlightlineIdentityParser) | Protocol for adding identity conventions without changing discovery. | public |
| [`ManifestIdentityParser`](generated/bulk-identity.md#spectralbridge.bulk.identity.ManifestIdentityParser) | Parse a generic, user-authored flightline identity manifest. | advanced |
| [`NEONDirectoryIdentityParser`](generated/bulk-identity.md#spectralbridge.bulk.identity.NEONDirectoryIdentityParser) | Preserve canonical NEON-directory support as one parser plugin. | advanced |
| [`resolve_flightline_identity`](generated/bulk-identity.md#spectralbridge.bulk.identity.resolve_flightline_identity) | Resolve one directory, rejecting conflicting parser results. | advanced |
| [`SourceFileRecord`](generated/bulk-models.md#spectralbridge.bulk.models.SourceFileRecord) | One source product discovered in the read-only input tree. | public |
| [`FlightlineRecord`](generated/bulk-models.md#spectralbridge.bulk.models.FlightlineRecord) | Canonical scientific unit recovered from one source directory. | public |
| [`ExclusionRecord`](generated/bulk-models.md#spectralbridge.bulk.models.ExclusionRecord) | One deterministic, machine-readable bulk exclusion. | public |
| [`BulkAnalysisPaths`](generated/bulk-models.md#spectralbridge.bulk.models.BulkAnalysisPaths) | Canonical, isolated output paths for one bulk-analysis run. | public |
| [`ProductDescriptor`](generated/bulk-registry.md#spectralbridge.bulk.registry.ProductDescriptor) | Recognize and describe one persisted raster-product convention. | public |
| [`TabularProductDescriptor`](generated/bulk-registry.md#spectralbridge.bulk.registry.TabularProductDescriptor) | Recognize one canonical per-flight tabular product convention. | public |
| [`TranslationPair`](generated/bulk-registry.md#spectralbridge.bulk.registry.TranslationPair) | A scientifically defined relationship between two sensor products. | public |
| [`AnalysisProfile`](generated/bulk-registry.md#spectralbridge.bulk.registry.AnalysisProfile) | Product and integrity requirements for one bulk analysis. | public |
| [`ProductRegistry`](generated/bulk-registry.md#spectralbridge.bulk.registry.ProductRegistry) | Immutable registry used by discovery, extraction, and analysis. | public |
| [`resolve_analysis_profile`](generated/bulk-registry.md#spectralbridge.bulk.registry.resolve_analysis_profile) | Resolve a registered profile name or retain an explicit AnalysisProfile; reject unknown names. | advanced |
| [`render_bulk_summary_dashboard`](generated/bulk-reporting.md#spectralbridge.bulk.reporting.render_bulk_summary_dashboard) | Render a one-page population QA dashboard from machine-readable metrics. | advanced |
| [`render_bulk_publication_figures`](generated/bulk-reporting.md#spectralbridge.bulk.reporting.render_bulk_publication_figures) | Render three manuscript-width figures from compact result tables only. | advanced |
| [`render_bulk_pdf_report`](generated/bulk-reporting.md#spectralbridge.bulk.reporting.render_bulk_pdf_report) | Assemble a self-contained PDF from already-computed compact QA outputs. | advanced |
| [`BulkResultsConfig`](generated/bulk-results.md#spectralbridge.bulk.results.BulkResultsConfig) | Configurable review criteria for compact bulk translation results. | public |
| [`BulkResultsPaths`](generated/bulk-results.md#spectralbridge.bulk.results.BulkResultsPaths) | Canonical compact inputs and interpretation outputs for one bulk run. | public |
| [`summarize_bulk_results`](generated/bulk-results.md#spectralbridge.bulk.results.summarize_bulk_results) | Summarize completed translation results without the source archive. | public |
| [`BivariateStatistics`](generated/bulk-streaming.md#spectralbridge.bulk.streaming.BivariateStatistics) | Numerically stable, mergeable bivariate population moments. | advanced |
| [`PairBand`](generated/bulk-streaming.md#spectralbridge.bulk.streaming.PairBand) | Record a one-based source/target band relationship for streamed sufficient statistics. | advanced |
| [`pair_bands`](generated/bulk-streaming.md#spectralbridge.bulk.streaming.pair_bands) | Expand registered translation pairs into ordered band-level statistics specifications. | advanced |
| [`iter_aligned_pair_chunks`](generated/bulk-streaming.md#spectralbridge.bulk.streaming.iter_aligned_pair_chunks) | Read all requested sensors together and yield aligned, valid pair arrays. | advanced |
| [`write_statistics`](generated/bulk-streaming.md#spectralbridge.bulk.streaming.write_statistics) | Atomically write compact sufficient-statistics rows using the fixed statistics schema. | advanced |
| [`write_diagnostic_sample`](generated/bulk-streaming.md#spectralbridge.bulk.streaming.write_diagnostic_sample) | Atomically write the explicitly requested diagnostic pixel sample using its fixed schema. | advanced |
| [`compute_flightline_statistics`](generated/bulk-streaming.md#spectralbridge.bulk.streaming.compute_flightline_statistics) | Create or reuse one compact per-flightline analytical checkpoint. | advanced |

## Spectral libraries and scientific analysis

[Workflow / scientific context](../api/scientific-analysis.md)

| Object | Purpose | Audience |
| --- | --- | --- |
| [`ReferenceGrid`](generated/landsat_agreement.md#spectralbridge.landsat_agreement.ReferenceGrid) | Describe the common CRS, affine grid, dimensions and support used for Landsat comparisons. | advanced |
| [`mask_landsat_qa`](generated/landsat_agreement.md#spectralbridge.landsat_agreement.mask_landsat_qa) | L8/9: reject flags 0-5, B1-B7 saturation and terrain occlusion. | advanced |
| [`scale_landsat_sr`](generated/landsat_agreement.md#spectralbridge.landsat_agreement.scale_landsat_sr) | Official Collection 2 Level-2 DN contract; never guess from magnitudes. | advanced |
| [`spectral_angle`](generated/landsat_agreement.md#spectralbridge.landsat_agreement.spectral_angle) | Compute spectral angle in degrees along matching seven-channel vectors; zero-norm comparisons yield NaN. | advanced |
| [`deming_regression`](generated/landsat_agreement.md#spectralbridge.landsat_agreement.deming_regression) | y versus x, lambda=variance(y measurement error)/variance(x error). | advanced |
| [`compute_agreement_metrics`](generated/landsat_agreement.md#spectralbridge.landsat_agreement.compute_agreement_metrics) | Summarize paired scalar reflectance observations in their supplied units. | advanced |
| [`spatial_bootstrap_indices`](generated/landsat_agreement.md#spectralbridge.landsat_agreement.spatial_bootstrap_indices) | Resample spatial blocks, never individual pixels as independent evidence. | advanced |
| [`aggregate_to_landsat_grid`](generated/landsat_agreement.md#spectralbridge.landsat_agreement.aggregate_to_landsat_grid) | Aggregate joint seven-band products to actual projected Landsat footprints. | advanced |
| [`build_flight_validation_figures`](generated/landsat_flight_report.md#spectralbridge.landsat_flight_report.build_flight_validation_figures) | Render common-support maps and band diagnostics from an existing flight-validation result packet. | advanced |
| [`FlightValidationInput`](generated/landsat_flight_validation.md#spectralbridge.landsat_flight_validation.FlightValidationInput) | Specify existing raw/adjusted synthetic products and an actual Landsat comparison source for one flight. | advanced |
| [`FlightValidationConfig`](generated/landsat_flight_validation.md#spectralbridge.landsat_flight_validation.FlightValidationConfig) | Configure explicit support, acquisition-time, screening and rendering settings for flight validation. | advanced |
| [`candidate_records`](generated/landsat_flight_validation.md#spectralbridge.landsat_flight_validation.candidate_records) | All searched scenes; compatibility and collection are explicit gates. | advanced |
| [`rank_scene_candidates`](generated/landsat_flight_validation.md#spectralbridge.landsat_flight_validation.rank_scene_candidates) | Temporal -> clear overlap -> compatibility -> coverage -> quality; never error. | advanced |
| [`load_scene_qa`](generated/landsat_flight_validation.md#spectralbridge.landsat_flight_validation.load_scene_qa) | Windowed Collection 2 QA with a 600-m halo for conservative proximity. | advanced |
| [`load_scene_surface_reflectance`](generated/landsat_flight_validation.md#spectralbridge.landsat_flight_validation.load_scene_surface_reflectance) | Read seven real SR assets on their native Landsat window; no TOA route. | advanced |
| [`compare_flight_to_real_landsat`](generated/landsat_flight_validation.md#spectralbridge.landsat_flight_validation.compare_flight_to_real_landsat) | Select one real scene and compare it with a verified seven-band flight. | advanced |
| [`summarize_flight_validations`](generated/landsat_flight_validation.md#spectralbridge.landsat_flight_validation.summarize_flight_validations) | Read compact completed results only; equally weight flights, never pixels. | advanced |
| [`LandsatObservation`](generated/landsat_validation.md#spectralbridge.landsat_validation.LandsatObservation) | A cropped, QA-masked actual Landsat surface-reflectance product. | advanced |
| [`acquire_landsat_observation`](generated/landsat_validation.md#spectralbridge.landsat_validation.acquire_landsat_observation) | Discover and cache the best overlapping Landsat Collection 2 L2 crop. | advanced |
| [`load_supplied_landsat_observation`](generated/landsat_validation.md#spectralbridge.landsat_validation.load_supplied_landsat_observation) | Load an acquisition manifest or a user-supplied multiband raster. | advanced |
| [`raster_bounds_wgs84`](generated/landsat_validation.md#spectralbridge.landsat_validation.raster_bounds_wgs84) | Transform raster bounds to (west, south, east, north) in WGS84 degrees; reject a missing CRS. | advanced |
| [`raster_acquisition_datetime`](generated/landsat_validation.md#spectralbridge.landsat_validation.raster_acquisition_datetime) | Read an acquisition timestamp tag or conservative YYYYMMDD filename token. | advanced |
| [`compare_landsat_common_support`](generated/landsat_validation.md#spectralbridge.landsat_validation.compare_landsat_common_support) | Aggregate drone/optional NEON products to the actual Landsat grid. | advanced |
| [`project_simplex`](generated/library_analysis.md#spectralbridge.library_analysis.project_simplex) | Enforce Euclidean nonnegative sum-one fraction geometry. | public |
| [`spectral_separability`](generated/library_analysis.md#spectralbridge.library_analysis.spectral_separability) | Test pairwise conditional whole-spectrum differences, not prediction. | public |
| [`generate_mixtures`](generated/library_analysis.md#spectralbridge.library_analysis.generate_mixtures) | Generate reproducible pair/triple linear mixtures and exact generating weights. | public |
| [`constrained_unmixing`](generated/library_analysis.md#spectralbridge.library_analysis.constrained_unmixing) | Fit nonnegative sum-one FCLS using the existing small-library face solver. | public |
| [`candidate_ambiguity`](generated/library_analysis.md#spectralbridge.library_analysis.candidate_ambiguity) | Summarize fraction variation among evaluated near-best candidate solutions. | public |
| [`fit_mesma`](generated/library_analysis.md#spectralbridge.library_analysis.fit_mesma) | Search explicit candidate models and retain inspectable near-fit compositions. | public |
| [`evaluate_identifiability`](generated/library_analysis.md#spectralbridge.library_analysis.evaluate_identifiability) | Evaluate unseen identities or held domains with nested regularized recognition. | public |
| [`evaluate_feature_budget`](generated/library_analysis.md#spectralbridge.library_analysis.evaluate_feature_budget) | Measure predictive information versus feature count with nested selection. | public |
| [`compare_representations`](generated/library_analysis.md#spectralbridge.library_analysis.compare_representations) | Compare paired same-row representations under identical grouped splits. | public |
| [`fit_ridge_fractions`](generated/library_analysis.md#spectralbridge.library_analysis.fit_ridge_fractions) | Fit supervised multi-output ridge with explicit raw/projected predictions. | public |
| [`fraction_diagnostics`](generated/library_analysis.md#spectralbridge.library_analysis.fraction_diagnostics) | Separate known-fraction quantification from thresholded detection errors. | public |
| [`evaluate_library_size`](generated/library_analysis.md#spectralbridge.library_analysis.evaluate_library_size) | Evaluate retained identity-library capacity with fixed classifier/prior. | public |
| [`ReadinessConfig`](generated/mesma_readiness.md#spectralbridge.mesma_readiness.ReadinessConfig) | Configure the experimental MESMA-readiness study and computational budgets. | advanced |
| [`decode_flight_history`](generated/mesma_readiness.md#spectralbridge.mesma_readiness.decode_flight_history) | Decode the established nested JSON exposure contract, never split on pipes. | advanced |
| [`load_compact_inputs`](generated/mesma_readiness.md#spectralbridge.mesma_readiness.load_compact_inputs) | Validate paired memberships/support; retain stored units without guessing. | advanced |
| [`flight_target_tables`](generated/mesma_readiness.md#spectralbridge.mesma_readiness.flight_target_tables) | Actual paired plant/flight means, never polygon/year medians in flight tests. | advanced |
| [`replace_flight_targets`](generated/mesma_readiness.md#spectralbridge.mesma_readiness.replace_flight_targets) | Replace only held-out rows with their actual flight; expose missing sources. | advanced |
| [`run_readiness`](generated/mesma_readiness.md#spectralbridge.mesma_readiness.run_readiness) | Run experimental grouped readiness diagnostics on verified compact inputs. | advanced |
| [`model_indices`](generated/mixtures.md#spectralbridge.mixtures.model_indices) | Enumerate distinct-class candidate sets, including every simplex face. | advanced |
| [`fit_models`](generated/mixtures.md#spectralbridge.mixtures.fit_models) | Exact active-face search, not unconstrained fractions clipped afterwards. | advanced |
| [`fcls`](generated/mixtures.md#spectralbridge.mixtures.fcls) | Exactly fit a small fixed library under nonnegative sum-one constraints. | advanced |
| [`shade_model_errors`](generated/mixtures.md#spectralbridge.mixtures.shade_model_errors) | RMSE(target, f*candidate+(1-f)*0), 0<=f<=1; rows target, cols candidate. | advanced |
| [`selection_scores`](generated/mixtures.md#spectralbridge.mixtures.selection_scores) | Published EAR and MASA within-class means excluding self. | advanced |
| [`select_endmembers`](generated/mixtures.md#spectralbridge.mixtures.select_endmembers) | Training-only selections. IES budget is global count_per_class x classes. | advanced |
| [`grouped_identity_split`](generated/mixtures.md#spectralbridge.mixtures.grouped_identity_split) | Purge every held-out identity from training while preserving the supplied test-row mask. | advanced |
| [`mixture_truth`](generated/mixtures.md#spectralbridge.mixtures.mixture_truth) | Generate linear mixtures ONLY from a caller-provided held-out source set. | advanced |
| [`validate_holdout`](generated/mixtures.md#spectralbridge.mixtures.validate_holdout) | Reject identity leakage or endmembers selected outside a training fold. | advanced |
| [`adequacy_status`](generated/mixtures.md#spectralbridge.mixtures.adequacy_status) | Experimental residual adequacy labels; never certify material membership. | advanced |
| [`detection_metrics`](generated/mixtures.md#spectralbridge.mixtures.detection_metrics) | Conditional fraction-detection counts; true presence means truth > 0. | advanced |
| [`AuditConfig`](generated/pft_method_audit.md#spectralbridge.pft_method_audit.AuditConfig) | Configure the historical whole-spectrum PFT method audit and its explicit resampling budgets. | advanced |
| [`wavelength_weights`](generated/pft_method_audit.md#spectralbridge.pft_method_audit.wavelength_weights) | Trapezoidal weights on disconnected supported segments, never across gaps. | advanced |
| [`upper_p`](generated/pft_method_audit.md#spectralbridge.pft_method_audit.upper_p) | Exchangeable ensemble upper-tail ranks, inclusive of identity and ties. | advanced |
| [`npc_probability`](generated/pft_method_audit.md#spectralbridge.pft_method_audit.npc_probability) | Synchronized Tippett combination; calibrate min partial p on same ensemble. | advanced |
| [`envelope_critical`](generated/pft_method_audit.md#spectralbridge.pft_method_audit.envelope_critical) | Conservative Monte Carlo MAD multiplier with strict excursion/tie rule. | advanced |
| [`method_statistics`](generated/pft_method_audit.md#spectralbridge.pft_method_audit.method_statistics) | Evaluate synchronized conditional whole-spectrum permutation statistics. | advanced |
| [`run_method_audit`](generated/pft_method_audit.md#spectralbridge.pft_method_audit.run_method_audit) | Audit historical PFT comparisons against checksum-verified prior results with restart checkpoints. | advanced |
| [`PFTStatisticsConfig`](generated/plant_pft_statistics.md#spectralbridge.plant_pft_statistics.PFTStatisticsConfig) | Explicit, reproducible inferential choices (not acceptance thresholds). | advanced |
| [`holm`](generated/plant_pft_statistics.md#spectralbridge.plant_pft_statistics.holm) | Holm family-wise adjustment; valid under arbitrary dependence. | advanced |
| [`permute_within`](generated/plant_pft_statistics.md#spectralbridge.plant_pft_statistics.permute_within) | Shuffle whole plant labels jointly across bands, preserving block counts. | advanced |
| [`contrast`](generated/plant_pft_statistics.md#spectralbridge.plant_pft_statistics.contrast) | Block-adjusted binary coefficient with fixed null scaling and max-T. | advanced |
| [`run_pft_statistics`](generated/plant_pft_statistics.md#spectralbridge.plant_pft_statistics.run_pft_statistics) | Read verified compact products in place and write resumable statistics. | advanced |
| [`run_quantile_overlays`](generated/plant_quantile_overlays.md#spectralbridge.plant_quantile_overlays.run_quantile_overlays) | Render 100 slots (100 unfitted, then 99–1) without changing any fit. | advanced |
| [`harmonize_spectrum`](generated/plant_spectral_atlas.md#spectralbridge.plant_spectral_atlas.harmonize_spectrum) | Linearly harmonize one spectrum without bridging unsupported intervals. | advanced |
| [`run_plant_spectral_atlas`](generated/plant_spectral_atlas.md#spectralbridge.plant_spectral_atlas.run_plant_spectral_atlas) | Create/reuse empirical plant-atlas derivatives without copying source pixels. | advanced |
| [`run_plant_comparison_atlas`](generated/plant_spectral_comparison.md#spectralbridge.plant_spectral_comparison.run_plant_comparison_atlas) | Render alphabetical species rows using matched independent plants. | advanced |
| [`load_pft_crosswalk`](generated/plant_spectral_pfts.md#spectralbridge.plant_spectral_pfts.load_pft_crosswalk) | Load the explicit, versioned lookup; never infer a species from a genus. | advanced |
| [`tag_pfts`](generated/plant_spectral_pfts.md#spectralbridge.plant_spectral_pfts.tag_pfts) | Add tags while retaining verbatim species and all observation identities. | advanced |
| [`run_pft_spectral_analysis`](generated/plant_spectral_pfts.md#spectralbridge.plant_spectral_pfts.run_pft_spectral_analysis) | Write additive PFT products; the original species products stay immutable. | advanced |
| [`QuantileModelConfig`](generated/plant_spectral_quantiles.md#spectralbridge.plant_spectral_quantiles.QuantileModelConfig) | Configure historical boosted quantile spectral models, group eligibility and rendering budgets. | advanced |
| [`fit_quantile_signature`](generated/plant_spectral_quantiles.md#spectralbridge.plant_spectral_quantiles.fit_quantile_signature) | Fit exact supplied wavelengths with equal total weight per input spectrum. | advanced |
| [`quantile_distance`](generated/plant_spectral_quantiles.md#spectralbridge.plant_spectral_quantiles.quantile_distance) | Mean pinball loss times two: a discrete 1–99% integrated-score approximation. | advanced |
| [`rank_unknown_spectrum`](generated/plant_spectral_quantiles.md#spectralbridge.plant_spectral_quantiles.rank_unknown_spectrum) | Rank supplied native-unit spectra against full quantile references. | advanced |
| [`run_boosted_quantile_atlas`](generated/plant_spectral_quantiles.md#spectralbridge.plant_spectral_quantiles.run_boosted_quantile_atlas) | Fit species/site and individual-polygon quantile signatures with checkpoints. | advanced |
| [`run_regional_plant_atlas`](generated/plant_spectral_regions.md#spectralbridge.plant_spectral_regions.run_regional_plant_atlas) | Reuse completed plant spectra for source-table site comparisons. | advanced |
| [`run_year_site_quantiles`](generated/plant_spectral_years.md#spectralbridge.plant_spectral_years.run_year_site_quantiles) | Fit or reuse boosted spectral quantiles within eligible species-by-site-by-year cohorts. | advanced |
| [`validate_researcher_labels`](generated/researcher_information.md#spectralbridge.researcher_information.validate_researcher_labels) | Validate labels against the five recorded researcher cover categories. | advanced |
| [`identity_weights`](generated/researcher_information.md#spectralbridge.researcher_information.identity_weights) | Each identity has total weight one; optionally balance class totals. | advanced |
| [`project_simplex`](generated/researcher_information.md#spectralbridge.researcher_information.project_simplex) | Euclidean projection onto nonnegative sum-one fractions (sorting rule). | advanced |
| [`weighted_auc`](generated/researcher_information.md#spectralbridge.researcher_information.weighted_auc) | Weighted binary ROC AUC per column, with half credit for tied values. | advanced |
| [`univariate_discrimination`](generated/researcher_information.md#spectralbridge.researcher_information.univariate_discrimination) | Balanced-prior single-coordinate LDA; threshold learned on training only. | advanced |
| [`orthogonal_feature_path`](generated/researcher_information.md#spectralbridge.researcher_information.orthogonal_feature_path) | Greedy complementary coordinates via balanced one-hot residual gains. | advanced |
| [`disconnected_derivative`](generated/researcher_information.md#spectralbridge.researcher_information.disconnected_derivative) | Derivatives within supported segments, with no atmospheric-gap bridges. | advanced |
| [`disjoint_parent_bundles`](generated/researcher_information.md#spectralbridge.researcher_information.disjoint_parent_bundles) | Sample one observation per class/ID, never reuse an ID across bundles. | advanced |
| [`fraction_metrics`](generated/researcher_information.md#spectralbridge.researcher_information.fraction_metrics) | Per-class fraction errors and presence metrics at a fixed .10 cutoff. | advanced |
| [`TrainingTransform`](generated/researcher_information.md#spectralbridge.researcher_information.TrainingTransform) | Fit-only training scalers/PCA; observation-local shape and derivatives. | advanced |
| [`category_metadata`](generated/researcher_pft_statistics.md#spectralbridge.researcher_pft_statistics.category_metadata) | Validate labels without requiring taxonomic identification. | advanced |
| [`run_researcher_statistics`](generated/researcher_pft_statistics.md#spectralbridge.researcher_pft_statistics.run_researcher_statistics) | Corrected NEON; exact acquisition history primary, site/year sensitivity. | advanced |
| [`random_feature_path`](generated/researcher_validation.md#spectralbridge.researcher_validation.random_feature_path) | Uniform nested subsets, independent of spectra, labels and target outcomes. | advanced |
| [`identity_correctness`](generated/researcher_validation.md#spectralbridge.researcher_validation.identity_correctness) | Per-ID correctness; repeated acquisitions cannot inflate biological weight. | advanced |
| [`balanced_accuracy`](generated/researcher_validation.md#spectralbridge.researcher_validation.balanced_accuracy) | Compute mean class recall with equal total weight per independent identity. | advanced |
| [`paired_identity_interval`](generated/researcher_validation.md#spectralbridge.researcher_validation.paired_identity_interval) | Stratified whole-ID bootstrap of paired, fixed-rule balanced-accuracy gain. | advanced |
| [`make_sensor_vs_neon_panels`](generated/sensor_panel_plots.md#spectralbridge.sensor_panel_plots.make_sensor_vs_neon_panels) | Render matched sensor products against corrected NEON bands. | public |
| [`make_micasense_vs_landsat_panels`](generated/sensor_panel_plots.md#spectralbridge.sensor_panel_plots.make_micasense_vs_landsat_panels) | Render wavelength-matched MicaSense and Landsat diagnostic panels. | public |
| [`validate_sensor_coordinates`](generated/sensor_pft_transfer.md#spectralbridge.sensor_pft_transfer.validate_sensor_coordinates) | No guessed ten-band relabeling; the supplied MicaSense cannot pass. | advanced |
| [`paired_observations`](generated/sensor_pft_transfer.md#spectralbridge.sensor_pft_transfer.paired_observations) | Intersect valid observations before medians; reject identity/label drift. | advanced |
| [`joint_cluster_multiplicities`](generated/sensor_pft_transfer.md#spectralbridge.sensor_pft_transfer.joint_cluster_multiplicities) | GlobalID clusters coupled across sensors, contrasts and repeated years. | advanced |
| [`bootstrap_contrasts`](generated/sensor_pft_transfer.md#spectralbridge.sensor_pft_transfer.bootstrap_contrasts) | Stable centered sufficient moments for a fixed-count cluster bootstrap. | advanced |
| [`project_neon_to_oli`](generated/sensor_pft_transfer.md#spectralbridge.sensor_pft_transfer.project_neon_to_oli) | Diagnostically project common-support NEON curves to seven OLI channels. | advanced |
| [`run_sensor_pft_transfer`](generated/sensor_pft_transfer.md#spectralbridge.sensor_pft_transfer.run_sensor_pft_transfer) | Primary inferred-PFT and separate researcher-category paired OLI experiment. | advanced |
| [`checkpoint`](generated/spectral_analytics_extensions.md#spectralbridge.spectral_analytics_extensions.checkpoint) | Publish a stage ledger last; reject altered completed outputs. | advanced |
| [`novelty_threshold`](generated/spectral_analytics_extensions.md#spectralbridge.spectral_analytics_extensions.novelty_threshold) | Known-only higher empirical quantile of whole-identity maxima. | advanced |
| [`unknown_metrics`](generated/spectral_analytics_extensions.md#spectralbridge.spectral_analytics_extensions.unknown_metrics) | Unknown precision/recall and known rejection at a prechosen threshold. | advanced |
| [`safe_novelty_scores`](generated/spectral_analytics_extensions.md#spectralbridge.spectral_analytics_extensions.safe_novelty_scores) | Keep zero selected-band spectra for distance/PCA; angle is undefined. | advanced |
| [`run_extensions`](generated/spectral_analytics_extensions.md#spectralbridge.spectral_analytics_extensions.run_extensions) | Run declared secondary comparisons with per-fold restart checkpoints. | advanced |
| [`run_domains`](generated/spectral_analytics_extensions.md#spectralbridge.spectral_analytics_extensions.run_domains) | Predict observational domains on held-out identities, not instrument causes. | advanced |
| [`reconstruct_saved_mixtures`](generated/spectral_analytics_mixtures.md#spectralbridge.spectral_analytics_mixtures.reconstruct_saved_mixtures) | Reconstruct saved linear targets from explicit identity/year parents. | advanced |
| [`run_selected_mixtures`](generated/spectral_analytics_mixtures.md#spectralbridge.spectral_analytics_mixtures.run_selected_mixtures) | Run the retained selected-endmember mixture sensitivity study using verified prior truth and fold membership. | advanced |
| [`validate_learning_run`](generated/spectral_analytics_validation.md#spectralbridge.spectral_analytics_validation.validate_learning_run) | Verify owned bytes before trusted model loading; compare math and support. | advanced |
| [`spectral_shape`](generated/spectral_closure.md#spectralbridge.spectral_closure.spectral_shape) | Per-observation weighted unit norm and amplitude; never fit on test rows. | advanced |
| [`closure_labels`](generated/spectral_closure.md#spectralbridge.spectral_closure.closure_labels) | Explicit partial biological hierarchy; mixed cover is a proxy, not purity. | advanced |
| [`paired_partition`](generated/spectral_closure.md#spectralbridge.spectral_closure.paired_partition) | Exact class/polygon/year/interaction/residual SS on a complete two-year panel. | advanced |
| [`paired_partition_bootstrap`](generated/spectral_closure.md#spectralbridge.spectral_closure.paired_partition_bootstrap) | Class-stratified identity resampling preserves both years of each pair. | advanced |
| [`one_vs_rest_metrics`](generated/spectral_closure.md#spectralbridge.spectral_closure.one_vs_rest_metrics) | Multiclass one-versus-rest rates; undefined denominators stay NaN. | advanced |
| [`cluster_rate_intervals`](generated/spectral_closure.md#spectralbridge.spectral_closure.cluster_rate_intervals) | Conditional class-stratified whole-identity intervals for detection rates. | advanced |
| [`LearningConfig`](generated/spectral_learning.md#spectralbridge.spectral_learning.LearningConfig) | Fixed experimental budgets; counts are identities, never source pixels. | advanced |
| [`outer_folds`](generated/spectral_learning.md#spectralbridge.spectral_learning.outer_folds) | Yield actual plant/site/year/flight masks with entire identities purged. | advanced |
| [`calibration_split`](generated/spectral_learning.md#spectralbridge.spectral_learning.calibration_split) | Uniformly reserve whole training identities, not stratified pixel rows. | advanced |
| [`StableFSelector`](generated/spectral_learning.md#spectralbridge.spectral_learning.StableFSelector) | Training-only F-rank coordinate selection with deterministic tie handling. | advanced |
| [`PLSDA`](generated/spectral_learning.md#spectralbridge.spectral_learning.PLSDA) | PLS regression on one-hot labels; argmax classification, raw softmax scores. | advanced |
| [`CentroidClassifier`](generated/spectral_learning.md#spectralbridge.spectral_learning.CentroidClassifier) | Equal-class nearest mean baseline in its training-scaled input space. | advanced |
| [`model_pipeline`](generated/spectral_learning.md#spectralbridge.spectral_learning.model_pipeline) | Return an unfitted training-only pipeline and predeclared small inner grid. | advanced |
| [`fit_training_model`](generated/spectral_learning.md#spectralbridge.spectral_learning.fit_training_model) | Fit only supplied proper-training data; inner splits use GlobalID groups. | advanced |
| [`probabilities`](generated/spectral_learning.md#spectralbridge.spectral_learning.probabilities) | Model-order probabilities or explicitly uncalibrated normalized decisions. | advanced |
| [`check_probabilities`](generated/spectral_learning.md#spectralbridge.spectral_learning.check_probabilities) | Validate finite nonnegative (observations, classes) scores whose rows sum to one. | advanced |
| [`temperature_probabilities`](generated/spectral_learning.md#spectralbridge.spectral_learning.temperature_probabilities) | Apply a positive temperature to clipped log probabilities and renormalize with softmax. | advanced |
| [`fit_temperature`](generated/spectral_learning.md#spectralbridge.spectral_learning.fit_temperature) | Fit one temperature using ONLY a separately reserved calibration sample. | advanced |
| [`conformal_threshold`](generated/spectral_learning.md#spectralbridge.spectral_learning.conformal_threshold) | Finite-sample quantile of maximum RAW nonconformity per identity. | advanced |
| [`conformal_metrics`](generated/spectral_learning.md#spectralbridge.spectral_learning.conformal_metrics) | Empirical row/whole-identity prediction-set coverage, not a shift guarantee. | advanced |
| [`classification_metrics`](generated/spectral_learning.md#spectralbridge.spectral_learning.classification_metrics) | Balanced accuracy/macro F1 and calibration with explicit class order. | advanced |
| [`cluster_bootstrap_accuracy`](generated/spectral_learning.md#spectralbridge.spectral_learning.cluster_bootstrap_accuracy) | Stratified whole-identity balanced-accuracy draws for paired comparisons. | advanced |
| [`class_prototypes`](generated/spectral_learning.md#spectralbridge.spectral_learning.class_prototypes) | Training-only empirical class representatives; never a purity certificate. | advanced |
| [`fit_novelty_space`](generated/spectral_learning.md#spectralbridge.spectral_learning.fit_novelty_space) | Training-only scaled PCA novelty scores; no Gaussian/outlier guarantee. | advanced |
| [`novelty_scores`](generated/spectral_learning.md#spectralbridge.spectral_learning.novelty_scores) | Nearest angle/distance and PCA radius/reconstruction residual. | advanced |
| [`stable_seed`](generated/spectral_library_analytics.md#spectralbridge.spectral_library_analytics.stable_seed) | Derive a deterministic 32-bit-compatible random seed from a name and base seed. | advanced |
| [`load_analytics_inputs`](generated/spectral_library_analytics.md#spectralbridge.spectral_library_analytics.load_analytics_inputs) | Verify upstream compact ownership, write only metadata/reference index. | advanced |
| [`scheme_data`](generated/spectral_library_analytics.md#spectralbridge.spectral_library_analytics.scheme_data) | Subset paired arrays to assigned, nonmissing labels with nonzero spectral support. | advanced |
| [`fold_support`](generated/spectral_library_analytics.md#spectralbridge.spectral_library_analytics.fold_support) | Report per-label training/test identity counts and explicit closed/open/insufficient-support statuses. | advanced |
| [`prepare_fold`](generated/spectral_library_analytics.md#spectralbridge.spectral_library_analytics.prepare_fold) | Class support/calibration gates, using actual flight targets when required. | advanced |
| [`representation_values`](generated/spectral_library_analytics.md#spectralbridge.spectral_library_analytics.representation_values) | Decode a representation name into its NEON/OLI sensor and feature budget; the arrays argument is retained but unused. | advanced |
| [`fit_predict_case`](generated/spectral_library_analytics.md#spectralbridge.spectral_library_analytics.fit_predict_case) | One owned restartable fit; no final-test labels influence fitting choices. | advanced |
| [`profile_learning`](generated/spectral_library_analytics.md#spectralbridge.spectral_library_analytics.profile_learning) | Profile declared models without computing or inspecting outer-test scores. | advanced |
| [`run_learning`](generated/spectral_library_analytics.md#spectralbridge.spectral_library_analytics.run_learning) | Run declared classical models/representations with per-fit restart checks. | advanced |

## Corrections and spectral processing

[Workflow / scientific context](../brdf_topo_algorithm.md)

| Object | Purpose | Audience |
| --- | --- | --- |
| [`build_correction_parameters_dict`](generated/brdf_topo.md#spectralbridge.brdf_topo.build_correction_parameters_dict) | Compute the correction parameter payload without writing it to disk. | advanced |
| [`build_and_write_correction_json`](generated/brdf_topo.md#spectralbridge.brdf_topo.build_and_write_correction_json) | Persist BRDF/topographic correction parameters for a flightline. | advanced |
| [`apply_brdf_topo_core`](generated/brdf_topo.md#spectralbridge.brdf_topo.apply_brdf_topo_core) | Run the BRDF+topographic correction using params into out_* paths. | advanced |
| [`apply_brdf_topo_correction`](generated/brdf_topo.md#spectralbridge.brdf_topo.apply_brdf_topo_correction) | Apply BRDF + topographic correction using precomputed parameters. | advanced |
| [`apply_brightness_correction`](generated/brightness.md#spectralbridge.brightness.apply_brightness_correction) | Apply a per-band brightness correction to hyperspectral/multispectral data. | public |
| [`load_brightness_coefficients`](generated/brightness_config.md#spectralbridge.brightness_config.load_brightness_coefficients) | Load brightness coefficients for a given system pair. | public |
| [`NDVIBinningConfig`](generated/corrections.md#spectralbridge.corrections.NDVIBinningConfig) | Configuration for NDVI binning used during BRDF fitting and application. | advanced |
| [`ReferenceGeometry`](generated/corrections.md#spectralbridge.corrections.ReferenceGeometry) | Reference geometry (degrees) for BRDF normalization. | advanced |
| [`BRDFKernelConfig`](generated/corrections.md#spectralbridge.corrections.BRDFKernelConfig) | Kernel and geometry settings for BRDF fitting/application. | advanced |
| [`log_stats`](generated/corrections.md#spectralbridge.corrections.log_stats) | Log min/max and validity fractions for quick debugging. | advanced |
| [`load_brdf_model`](generated/corrections.md#spectralbridge.corrections.load_brdf_model) | Load the BRDF model JSON for flightline_dir after normalizing its name. | advanced |
| [`compute_ndvi`](generated/corrections.md#spectralbridge.corrections.compute_ndvi) | Compute NDVI from unitless reflectance data. | advanced |
| [`compute_ndvi_bins`](generated/corrections.md#spectralbridge.corrections.compute_ndvi_bins) | Return NDVI bin edges and bin indices. | advanced |
| [`calc_cosine_i`](generated/corrections.md#spectralbridge.corrections.calc_cosine_i) | Adapted from hytools.topo.calc_cosine_i (GPLv3; HyTools Authors: | advanced |
| [`calc_volume_kernel`](generated/corrections.md#spectralbridge.corrections.calc_volume_kernel) | Adapted from hytools.brdf.kernels.calc_volume_kernel (GPLv3; HyTools Authors: | advanced |
| [`calc_geom_kernel`](generated/corrections.md#spectralbridge.corrections.calc_geom_kernel) | Adapted from hytools.brdf.kernels.calc_geom_kernel (GPLv3; HyTools Authors: | advanced |
| [`fit_scs_c_coefficients`](generated/corrections.md#spectralbridge.corrections.fit_scs_c_coefficients) | Fit per-band SCS+C C parameters over a full NeonCube footprint. | advanced |
| [`apply_topo_correct`](generated/corrections.md#spectralbridge.corrections.apply_topo_correct) | Topographic (illumination) correction on a hyperspectral chunk. | advanced |
| [`apply_brdf_correct`](generated/corrections.md#spectralbridge.corrections.apply_brdf_correct) | Perform BRDF normalization on a hyperspectral chunk using FlexBRDF ratio. | advanced |
| [`apply_glint_correct`](generated/corrections.md#spectralbridge.corrections.apply_glint_correct) | Placeholder for sunglint correction. | advanced |
| [`fit_and_save_brdf_model`](generated/corrections.md#spectralbridge.corrections.fit_and_save_brdf_model) | Estimate and persist BRDF coefficients for a NEON flightline. | advanced |
| [`resample_chunk_to_sensor`](generated/resample.md#spectralbridge.resample.resample_chunk_to_sensor) | Resample a hyperspectral chunk to target sensor bands using SRFs. | advanced |
| [`apply_resampler`](generated/standard_resample.md#spectralbridge.standard_resample.apply_resampler) | Apply a HyTools resampler configuration to a data slice. | advanced |
| [`resampler_hy_obj`](generated/standard_resample.md#spectralbridge.standard_resample.resampler_hy_obj) | Configure the retained legacy sensor-response resampler and ENVI writer. | advanced |
| [`load_envi_data`](generated/standard_resample.md#spectralbridge.standard_resample.load_envi_data) | Load hyperspectral data from an ENVI binary file. | advanced |
| [`translate_to_sensor`](generated/standard_resample.md#spectralbridge.standard_resample.translate_to_sensor) | Read an existing ENVI product and write one target-sensor product through the retained legacy resampler. | advanced |
| [`translate_to_other_sensors`](generated/standard_resample.md#spectralbridge.standard_resample.translate_to_other_sensors) | Run the retained legacy resampler for its configured Landsat and MicaSense targets. | advanced |

## Quality assurance and validation

[Workflow / scientific context](../vignettes/qa-and-analysis.md)

| Object | Purpose | Audience |
| --- | --- | --- |
| [`brightness_correction_metrics`](generated/qa-brightness.md#spectralbridge.qa.brightness.brightness_correction_metrics) | Summarize a bandwise multiplicative brightness correction. | public |
| [`reflectance_summary`](generated/qa-metrics.md#spectralbridge.qa.metrics.reflectance_summary) | Summarize valid support and distribution without changing reflectance scale. | public |
| [`linear_diagnostic`](generated/qa-metrics.md#spectralbridge.qa.metrics.linear_diagnostic) | Fit y = intercept + slope*x for diagnostic, not inferential, use. | public |
| [`residual_metrics`](generated/qa-metrics.md#spectralbridge.qa.metrics.residual_metrics) | Return held-out-style residual metrics for paired observations. | public |
| [`seam_score`](generated/qa-metrics.md#spectralbridge.qa.metrics.seam_score) | Compare gradients crossing chunk boundaries with interior neighbors. | public |
| [`chunk_invariance_metrics`](generated/qa-metrics.md#spectralbridge.qa.metrics.chunk_invariance_metrics) | Compare two outputs that should be scientifically identical. | public |
| [`spectral_response_support`](generated/qa-metrics.md#spectralbridge.qa.metrics.spectral_response_support) | Quantify SRF normalization and support on available source wavelengths. | public |
| [`translation_edge_metrics`](generated/qa-network.md#spectralbridge.qa.network.translation_edge_metrics) | Evaluate one sensor-to-sensor edge from paired held-out observations. | public |
| [`grouped_residual_metrics`](generated/qa-network.md#spectralbridge.qa.network.grouped_residual_metrics) | Return residual metrics by an explicit validation block. | public |
| [`path_consistency_metrics`](generated/qa-network.md#spectralbridge.qa.network.path_consistency_metrics) | Compare a direct translation with a multi-edge translation path. | public |
| [`cycle_consistency_metrics`](generated/qa-network.md#spectralbridge.qa.network.cycle_consistency_metrics) | Measure drift after translating around a sensor cycle back to its start. | public |
| [`normalize_stage_id`](generated/qa-paths.md#spectralbridge.qa.paths.normalize_stage_id) | Normalize a stage label to a nonempty lowercase underscore identifier for deterministic QA paths. | advanced |
| [`StageQAPaths`](generated/qa-paths.md#spectralbridge.qa.paths.StageQAPaths) | Canonical paths for one stage report. | advanced |
| [`CombinedQAPaths`](generated/qa-paths.md#spectralbridge.qa.paths.CombinedQAPaths) | Canonical paths for the cross-stage report. | advanced |
| [`qa_plot_contract`](generated/qa-plots.md#spectralbridge.qa.plots.qa_plot_contract) | Return the machine-readable fixed display contract for QA figures. | advanced |
| [`format_location_label`](generated/qa-plots.md#spectralbridge.qa.plots.format_location_label) | Return a compact location/date label while preserving fallback identity. | advanced |
| [`spatial_plot_context`](generated/qa-plots.md#spectralbridge.qa.plots.spatial_plot_context) | Derive a projected plotting extent from standard ENVI map metadata. | advanced |
| [`render_envi_overview`](generated/qa-plots.md#spectralbridge.qa.plots.render_envi_overview) | Render spatial support and spectral distribution from an actual ENVI cube. | advanced |
| [`render_correction_overview`](generated/qa-plots.md#spectralbridge.qa.plots.render_correction_overview) | Render before/after/difference maps with matched and zero-centered scales. | advanced |
| [`render_artifact_inventory`](generated/qa-plots.md#spectralbridge.qa.plots.render_artifact_inventory) | Render a compact inventory of the files produced by a stage. | advanced |
| [`render_correction_parameters`](generated/qa-plots.md#spectralbridge.qa.plots.render_correction_parameters) | Plot persisted BRDF coefficients and geometry without changing them. | advanced |
| [`render_brightness_diagnostics`](generated/qa-plots.md#spectralbridge.qa.plots.render_brightness_diagnostics) | Render the Python equivalent of the historical coefficient QMD plots. | advanced |
| [`render_parquet_overview`](generated/qa-plots.md#spectralbridge.qa.plots.render_parquet_overview) | Render extraction and merge structure from Parquet metadata. | advanced |
| [`render_stage_html`](generated/qa-reporting.md#spectralbridge.qa.reporting.render_stage_html) | Write a standalone deterministic HTML report for one stage. | advanced |
| [`assemble_combined_report`](generated/qa-reporting.md#spectralbridge.qa.reporting.assemble_combined_report) | Assemble stage reports and derive cross-stage findings. | public |
| [`run_completed_flightline_qa`](generated/qa-runner.md#spectralbridge.qa.runner.run_completed_flightline_qa) | Generate every applicable stage report from existing real artifacts. | public |
| [`QAStatus`](generated/qa-schema.md#spectralbridge.qa.schema.QAStatus) | Four-state QA classification used throughout SpectralBridge. | public |
| [`QACheck`](generated/qa-schema.md#spectralbridge.qa.schema.QACheck) | One explicit check, including thresholds and interpretation. | advanced |
| [`StageQAReport`](generated/qa-schema.md#spectralbridge.qa.schema.StageQAReport) | Machine-readable report emitted for one canonical pipeline stage. | public |
| [`overall_status`](generated/qa-schema.md#spectralbridge.qa.schema.overall_status) | Return the most severe evaluated status, or NOT EVALUATED. | advanced |
| [`emit_stage_qa`](generated/qa-stages.md#spectralbridge.qa.stages.emit_stage_qa) | Emit or reuse one deterministic stage QA JSON/HTML report from on-disk artifacts. | public |
| [`QAThresholds`](generated/qa-thresholds.md#spectralbridge.qa.thresholds.QAThresholds) | Provisional standard-mode thresholds expressed as fractions. | public |
| [`classify_high_bad`](generated/qa-thresholds.md#spectralbridge.qa.thresholds.classify_high_bad) | Classify a metric against inclusive upper warn/fail bounds; None yields NOT EVALUATED. | advanced |
| [`classify_low_bad`](generated/qa-thresholds.md#spectralbridge.qa.thresholds.classify_low_bad) | Classify a metric against inclusive lower warn/fail bounds; None yields NOT EVALUATED. | advanced |
| [`collect_qa_metrics`](generated/qa_dashboard.md#spectralbridge.qa_dashboard.collect_qa_metrics) | Collect all *_qa_metrics.parquet files into a single dataframe. | advanced |
| [`summarize_qa`](generated/qa_dashboard.md#spectralbridge.qa_dashboard.summarize_qa) | Compute per-flightline summary statistics. | advanced |
| [`plot_qa_dashboard`](generated/qa_dashboard.md#spectralbridge.qa_dashboard.plot_qa_dashboard) | Generate an overview plot showing flag fractions per flightline. | advanced |
| [`HeaderReport`](generated/qa_metrics.md#spectralbridge.qa_metrics.HeaderReport) | Store legacy ENVI header QA findings and metadata. | advanced |
| [`MaskReport`](generated/qa_metrics.md#spectralbridge.qa_metrics.MaskReport) | Store legacy validity-mask QA findings. | advanced |
| [`CorrectionReport`](generated/qa_metrics.md#spectralbridge.qa_metrics.CorrectionReport) | Store legacy correction QA diagnostics. | advanced |
| [`ConvolutionReport`](generated/qa_metrics.md#spectralbridge.qa_metrics.ConvolutionReport) | Store legacy target-sensor convolution QA diagnostics. | advanced |
| [`Provenance`](generated/qa_metrics.md#spectralbridge.qa_metrics.Provenance) | Store source and execution metadata accompanying a legacy QA report. | advanced |
| [`QAMetrics`](generated/qa_metrics.md#spectralbridge.qa_metrics.QAMetrics) | Group legacy header, mask, correction, convolution and provenance QA records. | advanced |
| [`write_json`](generated/qa_metrics.md#spectralbridge.qa_metrics.write_json) | Serialize legacy QAMetrics to JSON, creating the destination parent directory. | advanced |
| [`render_drone_panel`](generated/qa_plots.md#spectralbridge.qa_plots.render_drone_panel) | Render paired raw/corrected drone QA, respecting nodata and wavelength metadata, with optional JSON diagnostics. | advanced |
| [`render_flightline_panel`](generated/qa_plots.md#spectralbridge.qa_plots.render_flightline_panel) | Return (png_path, metrics_dict); also writes _qa.json/_qa.pdf when requested. | advanced |
| [`QAPlotStyle`](generated/qa_style.md#spectralbridge.qa_style.QAPlotStyle) | Typography and export defaults for drone/bulk QA figures. | advanced |
| [`sensor_display_label`](generated/qa_style.md#spectralbridge.qa_style.sensor_display_label) | Return a stable human label without changing the underlying sensor ID. | advanced |
| [`wavelength_pair_label`](generated/qa_style.md#spectralbridge.qa_style.wavelength_pair_label) | Return a compact physical source-to-target band label. | advanced |
| [`apply_qa_axis_style`](generated/qa_style.md#spectralbridge.qa_style.apply_qa_axis_style) | Apply the restrained drone/bulk axis treatment. | advanced |
| [`ValidationObservation`](generated/validation.md#spectralbridge.validation.ValidationObservation) | Diagnostics and explicit checks returned by one validation variation. | advanced |
| [`ValidationCase`](generated/validation.md#spectralbridge.validation.ValidationCase) | One operation/input combination in a validation campaign. | advanced |
| [`ValidationResult`](generated/validation.md#spectralbridge.validation.ValidationResult) | Serializable result from one :class:ValidationCase. | advanced |
| [`run_case`](generated/validation.md#spectralbridge.validation.run_case) | Run one case, converting failures and skips into structured evidence. | advanced |
| [`run_campaign`](generated/validation.md#spectralbridge.validation.run_campaign) | Run cases and return a versioned, machine-readable campaign record. | advanced |
| [`write_campaign`](generated/validation.md#spectralbridge.validation.write_campaign) | Atomically write one campaign JSON file. | advanced |
| [`load_campaign`](generated/validation.md#spectralbridge.validation.load_campaign) | Load and minimally validate a campaign record. | advanced |

## Input, output and polygon extraction

[Workflow / scientific context](../vignettes/polygon-extraction.md)

| Object | Purpose | Audience |
| --- | --- | --- |
| [`hdr_to_dict`](generated/envi.md#spectralbridge.envi.hdr_to_dict) | Parse an ENVI header, tolerating absent or unparseable wavelength lists where supported. | advanced |
| [`band_axis_from_header`](generated/envi.md#spectralbridge.envi.band_axis_from_header) | Locate a band-count-matching axis, falling back to the last axis for unmatched three-dimensional arrays. | advanced |
| [`wavelength_array`](generated/envi.md#spectralbridge.envi.wavelength_array) | Read numeric wavelength metadata as an array, returning None when absent or unparseable. | advanced |
| [`memmap_bsq`](generated/envi.md#spectralbridge.envi.memmap_bsq) | Open a read-only BSQ memory map shaped (bands, lines, samples) with header-declared dtype and byte order. | advanced |
| [`read_envi_cube`](generated/envi.md#spectralbridge.envi.read_envi_cube) | Read a BSQ ENVI image as float32 in (bands, lines, samples) order without reflectance rescaling. | advanced |
| [`to_unitless_reflectance`](generated/envi.md#spectralbridge.envi.to_unitless_reflectance) | Apply the legacy median heuristic: divide by 10000 when the finite median exceeds 1.5. | advanced |
| [`build_envi_header_text`](generated/envi_writer.md#spectralbridge.envi_writer.build_envi_header_text) | Build the ENVI .hdr file text from a header_dict. | advanced |
| [`EnviWriter`](generated/envi_writer.md#spectralbridge.envi_writer.EnviWriter) | EnviWriter assembles a corrected hyperspectral cube into a BSQ ENVI file. | advanced |
| [`GeoContext`](generated/exports-geo_utils.md#spectralbridge.exports.geo_utils.GeoContext) | Store EPSG and affine pixel geometry needed for export-coordinate columns. | advanced |
| [`load_geo_from_hdr`](generated/exports-geo_utils.md#spectralbridge.exports.geo_utils.load_geo_from_hdr) | Extract pixel size, origin and an inferred EPSG code from an existing ENVI header; return None without map information. | advanced |
| [`add_lonlat_inplace`](generated/exports-geo_utils.md#spectralbridge.exports.geo_utils.add_lonlat_inplace) | Fill x,y from row/col + affine if needed; then lon,lat from x,y + CRS. | advanced |
| [`write_parquet_with_lonlat`](generated/exports-geo_utils.md#spectralbridge.exports.geo_utils.write_parquet_with_lonlat) | Write a dataframe to parquet after enriching lon/lat from an ENVI header. | advanced |
| [`infer_stage_from_name`](generated/exports-schema_utils.md#spectralbridge.exports.schema_utils.infer_stage_from_name) | Infer the stage key (column prefix) from a filename. | advanced |
| [`sort_and_rename_spectral_columns`](generated/exports-schema_utils.md#spectralbridge.exports.schema_utils.sort_and_rename_spectral_columns) | Rebuild DataFrame with non-spectral first, then spectral columns sorted by wavelength | advanced |
| [`parse_envi_wavelengths_nm`](generated/exports-schema_utils.md#spectralbridge.exports.schema_utils.parse_envi_wavelengths_nm) | Parse ENVI header text for numeric wavelengths, return nm ints or None. | advanced |
| [`compute_lonlat`](generated/exports-schema_utils.md#spectralbridge.exports.schema_utils.compute_lonlat) | Transform planar x,y to lon,lat. Returns (lon, lat). | advanced |
| [`ensure_coord_columns`](generated/exports-schema_utils.md#spectralbridge.exports.schema_utils.ensure_coord_columns) | Make sure df has x, y, lon, lat columns. If missing, compute from row/col with affine transform and the CRS. | advanced |
| [`write_parquet_standardized`](generated/exports-schema_utils.md#spectralbridge.exports.schema_utils.write_parquet_standardized) | Standardized Parquet writer: | advanced |
| [`is_pre_2021`](generated/io-neon.md#spectralbridge.io.neon.is_pre_2021) | Return True when h5_path appears to be a pre-2021 NEON export. | public |
| [`reflectance_to_unitless_multiplier`](generated/io-neon.md#spectralbridge.io.neon.reflectance_to_unitless_multiplier) | Return m such that unitless = stored * m. | advanced |
| [`stored_to_unitless`](generated/io-neon.md#spectralbridge.io.neon.stored_to_unitless) | Convert stored reflectance values to unitless reflectance. | advanced |
| [`unitless_to_stored`](generated/io-neon.md#spectralbridge.io.neon.unitless_to_stored) | Convert unitless reflectance back to the cube's storage scale. | advanced |
| [`read_neon_reflectance_unitless`](generated/io-neon.md#spectralbridge.io.neon.read_neon_reflectance_unitless) | Return unitless reflectance scaled by the NEON factor with ignore masked. | advanced |
| [`peek_neon_raster_shape`](generated/io-neon.md#spectralbridge.io.neon.peek_neon_raster_shape) | Return (n_lines, n_samples) without loading the reflectance cube. | public |
| [`peek_neon_sample_count`](generated/io-neon.md#spectralbridge.io.neon.peek_neon_sample_count) | Return the across-track sample count without loading the reflectance cube. | public |
| [`read_neon_cube`](generated/io-neon.md#spectralbridge.io.neon.read_neon_cube) | Return (cube, wavelengths, metadata) for h5_path regardless of layout. | public |
| [`NeonPaths`](generated/io-neon_legacy.md#spectralbridge.io.neon_legacy.NeonPaths) | Group legacy NEON HDF5 dataset locations for reflectance, wavelengths and ancillary metadata. | advanced |
| [`detect_legacy_neon_schema`](generated/io-neon_legacy.md#spectralbridge.io.neon_legacy.detect_legacy_neon_schema) | Heuristically detect pre-2021 NEON AOP DP1.30006 HDF5 layout. | advanced |
| [`resolve_neon_paths`](generated/io-neon_legacy.md#spectralbridge.io.neon_legacy.resolve_neon_paths) | Return canonical dataset paths that work for both legacy and modern files. | advanced |
| [`NeonResolved`](generated/io-neon_schema.md#spectralbridge.io.neon_schema.NeonResolved) | References to key NEON HDF5 datasets and legacy flag. | advanced |
| [`detect_legacy`](generated/io-neon_schema.md#spectralbridge.io.neon_schema.detect_legacy) | Return True when the legacy (pre-2021) NEON schema is detected. | advanced |
| [`resolve`](generated/io-neon_schema.md#spectralbridge.io.neon_schema.resolve) | Return dataset handles for reflectance, wavelength, FWHM, and angles. | advanced |
| [`canonical_vectors`](generated/io-neon_schema.md#spectralbridge.io.neon_schema.canonical_vectors) | Load spectral/angle vectors in canonical float32 units. | advanced |
| [`merge_flightline`](generated/merge_duckdb.md#spectralbridge.merge_duckdb.merge_flightline) | Merge all pixel-level parquet tables for one flightline. | advanced |
| [`merge_all_flightlines`](generated/merge_duckdb.md#spectralbridge.merge_duckdb.merge_all_flightlines) | Run per-flightline merges across matching directories, collecting successful output paths and reporting failures. | advanced |
| [`NeonCube`](generated/neon_cube.md#spectralbridge.neon_cube.NeonCube) | In-memory NEON hyperspectral cube loader. | advanced |
| [`debug_load_neon_cube`](generated/neon_cube.md#spectralbridge.neon_cube.debug_load_neon_cube) | Convenience helper for manual debugging of NEON cubes. | advanced |
| [`read_envi_in_chunks`](generated/parquet_export.md#spectralbridge.parquet_export.read_envi_in_chunks) | Yield DataFrame chunks from an ENVI cube along with shared metadata. | advanced |
| [`parquet_exists_and_valid`](generated/parquet_export.md#spectralbridge.parquet_export.parquet_exists_and_valid) | Return True when parquet_path exists and has a readable schema. | advanced |
| [`build_parquet_from_envi`](generated/parquet_export.md#spectralbridge.parquet_export.build_parquet_from_envi) | Read an ENVI cube and emit a wide per-pixel Parquet table. | advanced |
| [`ensure_parquet_from_envi`](generated/parquet_export.md#spectralbridge.parquet_export.ensure_parquet_from_envi) | Reuse a readable Parquet schema or rebuild the table from the existing ENVI image/header in bounded chunks. | advanced |
| [`repair_lonlat_in_place`](generated/parquet_export.md#spectralbridge.parquet_export.repair_lonlat_in_place) | Add missing coordinate columns to eligible Parquets in place using matching ENVI geometry. | advanced |
| [`ensure_parquet_for_envi`](generated/parquet_export.md#spectralbridge.parquet_export.ensure_parquet_for_envi) | Ensure a .parquet sidecar exists for envi_img. | advanced |
| [`is_ok_columns`](generated/parquet_validation.md#spectralbridge.parquet_validation.is_ok_columns) | Return whether spectral columns are named and ordered per stage. | advanced |
| [`collect_issues`](generated/parquet_validation.md#spectralbridge.parquet_validation.collect_issues) | Return validation issues for every direct Parquet child of root. | advanced |
| [`validate_bands_in_dir`](generated/polygon_extraction.md#spectralbridge.polygon_extraction.validate_bands_in_dir) | Validate band layout and sample values for each Parquet file in directory. | advanced |
| [`control_function_for_extraction`](generated/polygon_extraction.md#spectralbridge.polygon_extraction.control_function_for_extraction) | Finds and processes raster files in a directory. | advanced |
| [`plot_spectra_from_parquet_dir`](generated/polygon_extraction.md#spectralbridge.polygon_extraction.plot_spectra_from_parquet_dir) | Generate spectral plots for each Parquet file within directory. | advanced |
| [`select_best_files`](generated/polygon_extraction.md#spectralbridge.polygon_extraction.select_best_files) | Choose one product per domain/site/date/time group, preferring masked and BRDF-corrected ENVI candidates. | advanced |
| [`find_best_resampled_files`](generated/polygon_extraction.md#spectralbridge.polygon_extraction.find_best_resampled_files) | Discover typed resampled products and apply the established per-flight product preference. | advanced |
| [`get_all_priority_rasters`](generated/polygon_extraction.md#spectralbridge.polygon_extraction.get_all_priority_rasters) | Return all raster files in base_dir prioritising BRDF corrected files first. | advanced |
| [`get_crs_from_hdr`](generated/polygon_extraction.md#spectralbridge.polygon_extraction.get_crs_from_hdr) | Reads an ENVI .hdr file and extracts the CRS as a Proj string or EPSG code. | advanced |
| [`process_raster_in_chunks`](generated/polygon_extraction.md#spectralbridge.polygon_extraction.process_raster_in_chunks) | Processes a raster file in chunks, intersects pixels with a polygon, and writes extracted | advanced |
| [`create_dummy_polygon`](generated/polygons.md#spectralbridge.polygons.create_dummy_polygon) | Create a dummy polygon covering a portion of the flightline. | advanced |
| [`validate_coordinate_match`](generated/polygons.md#spectralbridge.polygons.validate_coordinate_match) | Validate that polygon and ENVI coordinates match. | advanced |
| [`filter_polygons_by_overlap`](generated/polygons.md#spectralbridge.polygons.filter_polygons_by_overlap) | Filter polygons from GeoJSON that overlap the flightline. | advanced |
| [`visualize_polygons_on_envi`](generated/polygons.md#spectralbridge.polygons.visualize_polygons_on_envi) | Create a visualization showing polygons overlaid on ENVI RGB image. | advanced |
| [`build_polygon_pixel_index`](generated/polygons.md#spectralbridge.polygons.build_polygon_pixel_index) | Create a pixel→polygon lookup table for flight_paths. | advanced |
| [`extract_polygon_parquet_from_envi`](generated/polygons.md#spectralbridge.polygons.extract_polygon_parquet_from_envi) | Extract polygon-filtered parquet directly from ENVI file. | advanced |
| [`extract_all_polygon_parquets_from_envi`](generated/polygons.md#spectralbridge.polygons.extract_all_polygon_parquets_from_envi) | Extract polygon parquets directly from all ENVI files in flightline. | advanced |
| [`extract_polygon_parquets_for_flightline`](generated/polygons.md#spectralbridge.polygons.extract_polygon_parquets_for_flightline) | Filter per-product Parquet tables down to polygon pixels. | advanced |
| [`merge_polygon_parquets_for_flightline`](generated/polygons.md#spectralbridge.polygons.merge_polygon_parquets_for_flightline) | Merge polygon-filtered Parquet tables into one spectral library. | advanced |
| [`run_polygon_pipeline_for_flightline`](generated/polygons.md#spectralbridge.polygons.run_polygon_pipeline_for_flightline) | Execute the polygon pipeline end-to-end for one flightline. | advanced |

## Paths, metadata and utilities

[Workflow / scientific context](../naming-conventions.md)

| Object | Purpose | Audience |
| --- | --- | --- |
| [`categorize_file`](generated/file_sort.md#spectralbridge.file_sort.categorize_file) | Return the destination category name for file_obj. | advanced |
| [`generate_file_move_list`](generated/file_sort.md#spectralbridge.file_sort.generate_file_move_list) | Scans base_folder recursively to find all files matching the defined file types | advanced |
| [`SensorType`](generated/file_types.md#spectralbridge.file_types.SensorType) | Enumerate sensor-name strings used by the legacy typed filename conventions. | advanced |
| [`DataFile`](generated/file_types.md#spectralbridge.file_types.DataFile) | Base class for NEON data files. | advanced |
| [`MaskedFileMixin`](generated/file_types.md#spectralbridge.file_types.MaskedFileMixin) | Mixin to handle optional '_masked' suffixes in filenames. | advanced |
| [`NEONReflectanceFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceFile) | Represent the legacy typed filename contract for a raw reflectance HDF5 product. | advanced |
| [`NEONReflectanceENVIFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceENVIFile) | Base (uncorrected) NEON reflectance ENVI image. | advanced |
| [`NEONReflectanceENVIHDRFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceENVIHDRFile) | Represent the legacy typed filename contract for a raw reflectance ENVI header product. | advanced |
| [`NEONReflectanceAncillaryENVIFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceAncillaryENVIFile) | Ancillary ENVI image stack, e.g. | advanced |
| [`NEONReflectanceAncillaryENVIHDRFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceAncillaryENVIHDRFile) | Represent the legacy typed filename contract for a ancillary ENVI header product. | advanced |
| [`NEONReflectanceConfigFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceConfigFile) | Represent the legacy typed filename contract for a correction configuration JSON product. | advanced |
| [`NEONReflectanceBRDFCorrectedENVIFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceBRDFCorrectedENVIFile) | Represent the legacy typed filename contract for a BRDF/topographically corrected ENVI image product. | advanced |
| [`NEONReflectanceBRDFCorrectedENVIHDRFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceBRDFCorrectedENVIHDRFile) | Represent the legacy typed filename contract for a BRDF/topographically corrected ENVI header product. | advanced |
| [`NEONReflectanceBRDFMaskENVIFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceBRDFMaskENVIFile) | Represent the legacy typed filename contract for a BRDF mask ENVI image product. | advanced |
| [`NEONReflectanceBRDFMaskENVIHDRFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceBRDFMaskENVIHDRFile) | Represent the legacy typed filename contract for a BRDF mask ENVI header product. | advanced |
| [`NEONReflectanceCoefficientsFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceCoefficientsFile) | Represent the legacy typed filename contract for a correction coefficient product. | advanced |
| [`NEONReflectanceResampledENVIFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceResampledENVIFile) | Represent the legacy typed filename contract for a resampled sensor ENVI image product. | advanced |
| [`NEONReflectanceResampledHDRFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceResampledHDRFile) | Represent the legacy typed filename contract for a resampled sensor ENVI header product. | advanced |
| [`NEONReflectanceResampledMaskENVIFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceResampledMaskENVIFile) | Represent the legacy typed filename contract for a resampled sensor mask ENVI image product. | advanced |
| [`NEONReflectanceResampledMaskHDRFile`](generated/file_types.md#spectralbridge.file_types.NEONReflectanceResampledMaskHDRFile) | Represent the legacy typed filename contract for a resampled sensor mask ENVI header product. | advanced |
| [`SpectralDataParquetFile`](generated/file_types.md#spectralbridge.file_types.SpectralDataParquetFile) | Represent the legacy typed filename contract for a spectral-data Parquet product. | advanced |
| [`MaskedSpectralCSVFile`](generated/file_types.md#spectralbridge.file_types.MaskedSpectralCSVFile) | Represents masked spectral data CSV files like NEON_D13_NIWO_DP1_*_with_mask_and_all_spectra.csv | advanced |
| [`EndmembersCSVFile`](generated/file_types.md#spectralbridge.file_types.EndmembersCSVFile) | Represents endmembers CSV output from unmixing process | advanced |
| [`UnmixingModelBestTIF`](generated/file_types.md#spectralbridge.file_types.UnmixingModelBestTIF) | Represents model_best.tif output from unmixing | advanced |
| [`UnmixingModelFractionsTIF`](generated/file_types.md#spectralbridge.file_types.UnmixingModelFractionsTIF) | Represents model_fractions.tif output from unmixing | advanced |
| [`UnmixingModelRMSETIF`](generated/file_types.md#spectralbridge.file_types.UnmixingModelRMSETIF) | Represents model_rmse.tif output from unmixing | advanced |
| [`HalfWindow`](generated/half_flight.md#spectralbridge.half_flight.HalfWindow) | Half-open raster window for one half-flight product. | advanced |
| [`classify_footprint_orientation`](generated/half_flight.md#spectralbridge.half_flight.classify_footprint_orientation) | Classify corridor orientation from geographic footprint extents. | advanced |
| [`across_track_slices`](generated/half_flight.md#spectralbridge.half_flight.across_track_slices) | Return left/right column windows (east–west half-route mode). | advanced |
| [`along_track_slices`](generated/half_flight.md#spectralbridge.half_flight.along_track_slices) | Return left/right line windows (north–south half-route mode). | advanced |
| [`half_flight_id`](generated/half_flight.md#spectralbridge.half_flight.half_flight_id) | Append a validated left/right half-route suffix to the original flight identifier. | advanced |
| [`plan_half_flight`](generated/half_flight.md#spectralbridge.half_flight.plan_half_flight) | Plan heading-aware half-route windows for one NEON H5. | advanced |
| [`wavelengths_from_hdr`](generated/header_utils.md#spectralbridge.header_utils.wavelengths_from_hdr) | Return header wavelength values and their provenance, with an explicitly supplied sensor fallback. | advanced |
| [`mask_raster_with_polygons`](generated/mask_raster.md#spectralbridge.mask_raster.mask_raster_with_polygons) | Masks an ENVI raster using polygons from a GeoJSON file. | advanced |
| [`find_raster_files`](generated/mask_raster.md#spectralbridge.mask_raster.find_raster_files) | Finds raster files ending with '_reflectance', '_envi', or '.img' while excluding | advanced |
| [`SensorProductPaths`](generated/paths.md#spectralbridge.paths.SensorProductPaths) | Convenience wrapper for per-sensor ENVI/Parquet/QA artefacts. | advanced |
| [`FlightlinePaths`](generated/paths.md#spectralbridge.paths.FlightlinePaths) | Centralised path helper ensuring per-flightline isolation. | advanced |
| [`scene_prefix_from_dir`](generated/paths.md#spectralbridge.paths.scene_prefix_from_dir) | Recover a scene prefix from a raw ENVI image, HDF5 filename or, as a last fallback, the directory name. | advanced |
| [`site_from_prefix`](generated/paths.md#spectralbridge.paths.site_from_prefix) | Extract a NEON site code from a matching canonical scene prefix, otherwise return None. | advanced |
| [`normalize_brdf_model_path`](generated/paths.md#spectralbridge.paths.normalize_brdf_model_path) | Ensure the BRDF model JSON in  flightline_dir  matches the scene prefix: | advanced |
| [`SensorBandIdentity`](generated/sensor_pairs.md#spectralbridge.sensor_pairs.SensorBandIdentity) | Physical identity for one one-based sensor band. | advanced |
| [`sensor_band_identity`](generated/sensor_pairs.md#spectralbridge.sensor_pairs.sensor_band_identity) | Return packaged physical metadata, or None for a custom sensor. | advanced |
| [`wavelength_matched_band_pairs`](generated/sensor_pairs.md#spectralbridge.sensor_pairs.wavelength_matched_band_pairs) | Pair shared spectral identities using packaged wavelength definitions. | advanced |
| [`clean_memory`](generated/utils-memory.md#spectralbridge.utils.memory.clean_memory) | Force garbage collection and log memory usage. | advanced |
| [`get_flight_paths`](generated/utils-naming.md#spectralbridge.utils.naming.get_flight_paths) | Return canonical high-level paths for a flight line. | advanced |
| [`get_flightline_products`](generated/utils-naming.md#spectralbridge.utils.naming.get_flightline_products) | Return canonical paths for artefacts tied to flight_stem. | advanced |
| [`get_package_data_path`](generated/utils-paths.md#spectralbridge.utils.paths.get_package_data_path) | Return the absolute path to a bundled data file. | public |
| [`render_drone_qa_report`](generated/utils-qa_summary.md#spectralbridge.utils.qa_summary.render_drone_qa_report) | Render/reuse the final dashboard and PDF using compact QA products only. | advanced |
| [`build_drone_qa_summary`](generated/utils-qa_summary.md#spectralbridge.utils.qa_summary.build_drone_qa_summary) | Backward-compatible wrapper returning the final drone QA PDF path. | public |
| [`is_valid_envi_pair`](generated/utils_checks.md#spectralbridge.utils_checks.is_valid_envi_pair) | Return True if both ENVI files exist and are non-empty. | advanced |
| [`is_valid_json`](generated/utils_checks.md#spectralbridge.utils_checks.is_valid_json) | Return True if the JSON file exists, is non-empty, and parses. | advanced |
