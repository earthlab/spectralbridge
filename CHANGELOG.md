## [2.3.0rc1] – 2026-09-08

### Added

- A separate, restart-safe bulk-analysis pipeline that discovers completed
  flightlines and streams immutable ENVI target products into compact,
  mergeable sufficient statistics without creating an ordinary pixel cache.
- Translation fits at pixel-pooled, flightline-balanced, site-balanced,
  per-flightline, and per-site levels, plus leave-one-site-out validation and
  candidate coefficient tables.
- `summarize_bulk_results()` for compact result summaries, scientific warning
  flags, figures, and reusable reports without reopening source rasters.
- Explicit `build_harmonized_dataset()` materialization for users who actually
  need a row-level harmonized dataset; it is not part of normal bulk analysis.
- Spectral-library preflight, compact summary, full-report, and extreme-spectrum
  inspection infrastructure operating on bulk polygon-extraction products.
- Product-registry-driven bulk discovery and translation-pair handling,
  including matched MicaSense products and target-only translation runs.
- Full-scene normal and drone processing notebooks and release-validation
  coverage for the public pipeline entry points.
- Production drone translation from corrected native MicaSense to separately
  named Landsat-like rasters and full/polygon spectral-library Parquets using
  explicitly selected, validated bulk candidate coefficients.
- Standalone drone translation QA plus optional supplied/STAC Landsat and
  normal-pipeline NEON comparison on the actual Landsat spatial grid.
- Restart-fingerprinted drone working-H5, ENVI, correction, and report stages;
  dashboard-first drone QA PDF and publication-ready translation figures.
- A strict, versioned production drone-coefficient registry API and compact-bulk
  importer, with fixed site-balanced selection, 18-band wavelength validation,
  coefficient confidence/LOSO metadata, strict caution handling, and translated
  spectral-library provenance. The numerical packaged registry remains pending
  import from the exact completed bulk artifacts; no values were reconstructed
  from rounded report statistics.
- Dashboard-first bulk QA, three manuscript-width publication figures, a
  self-contained PDF report, and restart reuse for the coupled compact
  coefficient/LOSO stage after process interruption.
- Config-driven brightness coefficients for Landsat→MicaSense (`landsat_to_micasense.json`) and helper loader.
- Automatic per-band brightness adjustment applied to Landsat-convolved products, recorded in QA JSON and brightness tables.
- Multi-page QA report (`*_qa.pdf`) with:
  - Page 1: ENVI product overview (one row, one panel per ENVI file).
  - Page 2: topographic and BRDF diagnostics (two rows).
  - Page 3: remaining QA diagnostics (convolution accuracy, header/mask summaries, issues, brightness coefficients).
- Expanded QA JSON metrics, including header integrity, mask coverage, Δ reflectance, convolution error, and brightness coefficients.

### Changed

- The PyPI distribution is now named `earthlab-spectralbridge` to avoid a
  normalized-name collision; the SpectralBridge product name, GitHub repository,
  `spectralbridge` import namespace, and `spectralbridge-*` commands are unchanged.
- Bulk analyses read completed-flightline source products in bounded windows and
  checkpoint one compact statistics artifact per flightline. Restarted runs
  reuse those checkpoints.
- Translation reporting compares pooled and balanced fits and surfaces weak,
  unstable, site-dependent, or high-correction cases instead of implying that a
  high R² alone makes sensors interchangeable.
- Bulk and sensor QA now resolve corresponding bands from packaged spectral
  identities and wavelengths, retain separate source/target band indices, and
  display wavelength-aware labels instead of treating band numbers as global.
- Drone processing remains a separate local-data workflow and supports full or
  polygon extraction; after corrected ENVI it uses affine cross-sensor
  translation while the normal hyperspectral NEON branch uses convolution.
- Release metadata, artifact tests, and documentation now cover Python
  3.10–3.12 and pre-release versions.
- ENVI export and pipeline logs now use affirmative, progress-oriented wording (e.g., “creating new ENVI export” instead of “not found or invalid”).
- CI simplified to four main checks on PRs: `CI / lite`, `CI / unit`, `Docs Drift Check / audit`, and `QA quick check / qa`.
- Topographic correction now defaults to SCS+C (`use_scs_c=True`) for HyTools/FlexBRDF consistency. To restore legacy cosine-ratio behaviour, call `apply_topo_correct(..., use_scs_c=False)` or use the corresponding CLI flag.

### Fixed

- Matched MicaSense TM/ETM+ and OLI/OLI-2 files are classified with their
  registered sensor identities, making all configured translation pairs
  eligible when the six target product families are complete.
- Bulk discovery, source identity, and reporting edge cases found during the
  122-flightline production run, including scalable spectral-library rendering.
- Duplicate QA/pytest workflows removed; QA quick check now runs once per PR (and optionally once per push to `main`).
- Rasterio WKT2 UTM metadata from valid drone TIFFs are recognized when
  constructing the working-H5 map information, preserving the established
  TIFF/H5 conversion behavior while enabling downstream polygon reprojection.

## [2025-10-30] Added Merge Stage + Restored QA Panel

- Added new DuckDB-based merge step combining original, corrected, and resampled pixel tables.
- Merged output uses naming convention: `<prefix>_merged_pixel_extraction.parquet`.
- QA panel (`<prefix>_qa.png`) is now rendered automatically after each merge, even in parallel runs.
- Documentation and examples updated accordingly.

## [2.2.0] – 2025-10-29
### Added
- Automatic NEON HDF5 download (`stage_download_h5`) with live progress bar.
- Per-flightline subdirectories containing all derived products (ENVI, corrected, convolved, parquet).
- QA summary panel generator (`cscal-qa`) that validates export, correction, convolution, and parquet output.
- Parallel flightline processing with `--max-workers` / `max_workers`.
- Progress bars for download, ENVI export tiling, and BRDF+topo correction tiling.

### Changed
- Pipeline now restores the documented behavior: `cscal-pipeline` / `go_forth_and_multiply()` handles download, correction, resampling, and export in one call.
- Logging now includes per-flightline prefixes during parallel execution for readability.
- Reproducibility documentation and CLI quickstart updated.

### Improved
- Idempotent skip logic preserved across all new stages.
- Organized output layout for long-term storage (keep corrected outputs, discard raw `.h5` if desired).
- Clearer environment setup instructions (conda or pip).

### Fixed
- Eliminated `GRGRGRGR...` spam; replaced with tqdm-style progress bars.
- Made output paths consistent between stages so downstream steps don't guess filenames.

## [Unreleased] – Pipeline refactor for idempotent, ordered execution (October 2025)

- Pipeline is now restart-safe / idempotent: each major stage checks for valid existing outputs
  and skips heavy recompute, logging `✅ ... (skipping)`.
- Introduced canonical output naming via `get_flightline_products()`.
- All per-sensor convolution products are now written as ENVI `.img/.hdr` pairs using the
  pattern `<flight_stem>_<sensor_name>_envi.img/.hdr`.
- Removed `.tif` GeoTIFF outputs from the advertised workflow.
- Convolution now ALWAYS reads the BRDF+topo corrected ENVI cube, never the raw NEON `.h5` directly.
- Added per-sensor success/skip/fail accounting and a final summary line:
  `📊 Sensor convolution summary ... | succeeded=[...] skipped=[...] failed=[...]`
- Pipeline no longer hard-stops if one sensor fails; it finishes the flight line as long as at
  least one sensor succeeded (or had a valid preexisting output).
- Added final site-level completion log: `✅ All requested flightlines processed.`
