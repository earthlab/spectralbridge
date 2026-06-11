# SpectralBridge Feature Requests

Review date: 2026-06-02  
Branch: main

This file is the authoritative work queue for non-trivial SpectralBridge work.
Agents must update it before coding, after verification, and whenever work is
left incomplete so the next agent can resume immediately.

## Workflow Rules

1. Read this file before making substantive changes.
2. Select the highest-priority unfinished item unless the user directs
   otherwise.
3. Update the chosen item with `Status`, `Owner`, `Started`, and `Plan` before
   coding.
4. Add or update tests with every behavior change.
5. Update docs when public behavior, contracts, outputs, or workflows change.
6. After verification, record outcome, blockers, and the next recommended task.

## Active Requests

### P43. CI Regression Stabilization After Drone/Docs Updates

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-11
- Goal: Fix the full-test CI regressions reported in the attached pytest log
  without changing scientific workflow behavior.
- Plan:
  - Identify shared causes behind the reported failures before making broad
    edits.
  - Restore testable module boundaries where monkeypatches should intercept
    pipeline calls.
  - Add or adjust focused regression coverage only where needed.
  - Run targeted tests for each fixed failure cluster, then broader test
    modules when feasible.
- Completion notes:
  - Fixed `tests/test_cross_sensor_cal_shim.py` so fresh namespace import tests
    restore prior `spectralbridge` and `cross_sensor_cal` modules after each
    check. This prevents later tests from holding stale direct function imports
    while monkeypatch modifies a different live module instance.
  - Fixed `tests/conftest.py` so the fake PyArrow shim is only installed when
    real `pyarrow` cannot be imported, instead of shadowing an installed
    PyArrow package before pandas ArrowDtype tests run.
  - No scientific workflow code was changed for this stabilization pass.
- Verification:
  - `python3 -m py_compile tests/test_cross_sensor_cal_shim.py tests/conftest.py`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_cross_sensor_cal_shim.py tests/test_drone_pipeline.py::test_run_drone_pipeline_skips_polygons_cleanly tests/test_drone_pipeline.py::test_run_drone_pipeline_accepts_tiff_sources tests/test_drone_pipeline.py::test_apply_drone_corrections_uses_full_scene_chunk tests/test_stage_export.py::test_stage_export_envi_targets_raw_names tests/test_polygons.py::test_extract_polygon_parquet_from_envi_stabilizes_null_only_metadata_chunks`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_cross_sensor_cal_shim.py tests/test_drone_pipeline.py tests/test_logging_config.py tests/test_parquet_export.py tests/test_pipeline_convolution.py tests/test_pipeline_ray_engines.py tests/test_polygons.py tests/test_stage_export.py --disable-warnings`
    reached 100% with no assertion failures in local output.
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q --disable-warnings`
    reached 100% with no assertion failures in local output.
- Blockers:
  - The local full-suite process reports a signal-style pytest exit value after
    printing 100% completion (`PYTEST_EXIT:143` when explicitly echoed), so CI
    should be treated as the authoritative final full-suite process-exit check.
    The attached assertion failures are no longer reproduced after the test
    isolation fixes.
- Next recommended task:
  - Push the test-isolation fixes and rerun CI; if CI still reports a nonzero
    exit after all assertions pass, investigate Ray/process shutdown separately.

### P42. Drone Empty Input Discovery Status

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-10
- Goal: Make drone pipeline runs with zero discovered H5/TIFF inputs explicit
  and actionable in logs and QA metadata.
- Plan:
  - Preserve the existing non-raising empty-run behavior for compatibility.
  - Add explicit QA metadata describing the searched path, whether it exists,
    whether it is a file or directory, and the supported input extensions.
  - Emit an actionable warning when no drone inputs are discovered.
  - Add a regression test for empty input discovery status.
- Completion notes:
  - Added explicit empty-discovery QA metadata to `run_drone_pipeline()`,
    including input path, resolved path, existence, path type, supported input
    extensions, `input_discovery_status`, and `skip_reason`.
  - Added a visible `[drone] No supported drone inputs discovered...` message
    when a run finds no `.h5`, `.tif`, or `.tiff` flight inputs.
  - Preserved the existing non-raising empty-run behavior for restart-safe
    compatibility.
  - Added regression coverage for empty input discovery status and written QA
    JSON metadata.
- Verification:
  - `python3 -m py_compile src/spectralbridge/pipelines/drone.py tests/test_drone_pipeline.py`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py::test_run_drone_pipeline_reports_empty_input_discovery`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py`
- Blockers:
  - Ruff is not installed in the local `.venv`, so `ruff check` could not be
    run here.
- Next recommended task:
  - In the notebook, inspect the current working directory and the requested
    input folder with `Path.cwd()` and `list(Path("drone_inputs").rglob("*"))`
    to confirm the TIFF/H5 files are actually under the path passed to
    `run_drone_pipeline()`.

### P41. Remove Remote Docs CDN Assets From Browser Smoke Path

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-10
- Goal: Fix the docs Playwright smoke test failure caused by browser console
  errors from remote GLightbox CDN assets returning HTTP 403 during local site
  testing.
- Plan:
  - Remove remote GLightbox CSS/JS references from `mkdocs.yml` so the built
    docs site uses local assets only during browser smoke tests.
  - Preserve the local no-op GLightbox initializer, which safely exits when the
    optional library is absent.
  - Rebuild or otherwise verify docs configuration and rerun the focused docs
    smoke test when local tooling is available.
- Completion notes:
  - Removed the external jsDelivr GLightbox CSS and JS entries from
    `mkdocs.yml`.
  - Kept the local `docs/js/glightbox-init.js` no-op guard so docs pages remain
    safe if GLightbox is reintroduced locally later.
  - Confirmed no remaining docs or MkDocs configuration references to the
    remote GLightbox CDN assets.
- Verification:
  - `python3 scripts/check_docs_links.py`
  - `rg -n "cdn\\.jsdelivr|glightbox/dist" docs mkdocs.yml`
  - `.venv/bin/pytest -q tests/test_docs_playwright.py` skipped locally because
    `SPECTRALBRIDGE_DOCS_SITE` was not set.
- Blockers:
  - The local environment does not have `mkdocs` installed, so `mkdocs build
    --strict` and the served-site Playwright check could not be run here.
- Next recommended task:
  - Let CI rebuild the docs site from `mkdocs.yml` and rerun the browser smoke
    test; the two prior 403 console errors should be gone because the remote
    assets are no longer requested.

### P40. Bundle Drone Field Manifest

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-10
- Goal: Track the drone field manifest in the repository and reference the
  bundled copy from the drone pipeline.
- Plan:
  - Add the provided manifest CSV as package data under
    `src/spectralbridge/data`.
  - Include CSV package data in `pyproject.toml`.
  - Update the drone manifest resolver so omitted `drone_manifest_path` and
    bare manifest filenames can resolve to the bundled package-data copy.
  - Add tests proving the bundled default is used without requiring a notebook
    local CSV.
- Completion notes:
  - Added the provided field manifest as
    `src/spectralbridge/data/drone_field_manifest.csv`.
  - Updated package metadata so CSV files under `spectralbridge.data` are
    included as package data.
  - Updated `run_drone_pipeline()` so `drone_manifest_path=None` resolves to the
    bundled manifest by default.
  - Updated manifest resolution so the original long CSV filename also resolves
    to the bundled package-data copy when no local file is present.
  - Updated the MicaSense/drone tutorial to document the bundled default and
    custom-manifest override behavior.
- Verification:
  - `python3 -m py_compile src/spectralbridge/pipelines/drone.py tests/test_drone_pipeline.py`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py::test_run_drone_pipeline_uses_bundled_manifest_by_default tests/test_drone_pipeline.py::test_run_drone_pipeline_resolves_original_manifest_filename_to_bundle tests/test_drone_pipeline.py::test_run_drone_pipeline_resolves_manifest_relative_to_input_dir tests/test_drone_pipeline.py::test_run_drone_pipeline_resolves_manifest_relative_to_relative_input_folder`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py`
  - `python3 scripts/check_docs_links.py`
- Next recommended task:
  - Run packaging/build checks in CI to confirm `drone_field_manifest.csv` is
    present in built wheels and source distributions.

### P39. AOP QA PNG pHash Baseline Refresh

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-10
- Goal: Refresh the optional imagehash regression baseline for the intentionally
  redesigned AOP QA PNG quicklook.
- Plan:
  - Generate the QA PNG from the existing test fixture.
  - Compute the new perceptual hash for the 2x3 AOP QA panel layout.
  - Update `tests/test_qa/test_qa_png_phash.py` and rerun `pytest -q
    tests/test_qa`.
- Completion notes:
  - Recomputed the pHash baseline from the deterministic QA fixture and the
    redesigned 2x3 AOP QA PNG layout.
  - Updated `tests/test_qa/test_qa_png_phash.py` from the old 2x2-panel hash to
    `be3e91c3c1e5c3db`.
- Verification:
  - `python3 -m py_compile tests/test_qa/test_qa_png_phash.py`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_qa`
    passed locally with the pHash test skipped because `imagehash` is not
    installed in the local `.venv`.
- Next recommended task:
  - Let CI run the optional `imagehash` pHash check against the refreshed
    baseline.

### P38. Drone Manifest Relative Input Folder Fallback

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-10
- Goal: Fix the drone manifest resolver so a relative `input_h5_dir` such as
  `drone_inputs` is checked for a relative manifest CSV even if the input
  directory has not resolved as an existing directory yet.
- Plan:
  - Add current-working-directory-relative input folder candidates to
    `_resolve_drone_manifest_path()`.
  - Preserve the clearer missing-file error with checked paths.
  - Add focused regression coverage for resolving
    `input_h5_dir="drone_inputs"` plus `drone_manifest_path="manifest.csv"`.
- Completion notes:
  - Updated `_resolve_drone_manifest_path()` to check both the raw relative
    `input_h5_dir` and the current-working-directory-resolved input folder for
    relative manifest CSVs.
  - Resolved manifest paths are now stored as absolute paths in QA metadata so
    notebook runs are easier to audit.
  - Added a CyVerse-shaped regression test for
    `input_h5_dir="drone_inputs"` and `drone_manifest_path="manifest.csv"`.
- Verification:
  - `python3 -m py_compile src/spectralbridge/pipelines/drone.py tests/test_drone_pipeline.py`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py::test_run_drone_pipeline_resolves_manifest_relative_to_input_dir tests/test_drone_pipeline.py::test_run_drone_pipeline_resolves_manifest_relative_to_relative_input_folder tests/test_drone_pipeline.py::test_run_drone_pipeline_missing_manifest_error_lists_checked_paths`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py`
- Next recommended task:
  - In CyVerse, upload/copy the manifest CSV either to the notebook working
    directory or to `drone_inputs/`; the patched resolver will now find either.

### P37. Drone Manifest Path Resolution Error Clarity

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-10
- Goal: Improve `run_drone_pipeline()` behavior when `drone_manifest_path` is
  a relative path that is not found from the notebook working directory.
- Plan:
  - Resolve relative manifest paths against the current working directory and
    nearby drone input locations before loading the CSV.
  - Raise an actionable `FileNotFoundError` that lists checked locations and
    tells users to pass an absolute path or place/upload the CSV into the
    working environment.
  - Add focused regression coverage for relative path resolution and missing
    manifest error clarity.
- Completion notes:
  - Added `_resolve_drone_manifest_path()` so relative `drone_manifest_path`
    values are checked from the notebook/current working directory, the drone
    input folder, and the input folder parent before loading the CSV.
  - Improved missing-manifest failures with an actionable `FileNotFoundError`
    that lists every checked path and tells users to pass an absolute path or
    upload/place the CSV into the working environment.
  - Added regression tests for resolving a manifest placed inside the drone
    input directory and for the clearer missing-file error.
- Verification:
  - `python3 -m py_compile src/spectralbridge/pipelines/drone.py tests/test_drone_pipeline.py`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py::test_run_drone_pipeline_resolves_manifest_relative_to_input_dir tests/test_drone_pipeline.py::test_run_drone_pipeline_missing_manifest_error_lists_checked_paths tests/test_drone_pipeline.py::test_lookup_flight_datetime_matches_compact_mixed_separator_id`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py`
- Next recommended task:
  - In the notebook/Jupyter environment, either upload the manifest CSV next to
    the notebook or `drone_inputs/`, or pass the absolute path to the uploaded
    CSV.

### P36. Drone Manifest Real CSV Matching Cleanup

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-10
- Goal: Validate the real drone field manifest CSV against the manifest loader
  and tighten flight-ID matching for mixed separator forms such as `SPR-1`
  matching derived package stems like `SPR1_20230628`.
- Plan:
  - Test `load_drone_manifest()` and `lookup_flight_datetime()` against the
    provided field CSV without committing the CSV to the repository.
  - Make missing/blank manifest IDs skip cleanly instead of normalizing pandas
    missing values to `NAN`.
  - Add compact alphanumeric fallback matching while preserving exact and
    date-stripped matching priority.
  - Add focused regression tests for `SPR-1` -> `SPR1_YYYYMMDD` matching.
- Completion notes:
  - Validated the provided field CSV in `/Users/tuff/Downloads` without copying
    it into the repository.
  - Updated manifest ID normalization so pandas missing IDs skip cleanly as
    missing values instead of becoming `NAN`.
  - Added compact alphanumeric fallback matching so manifest IDs such as
    `SPR-1` and `SPR-2` resolve derived stems such as `SPR1_20230628` and
    `SPR2_20230628`.
  - Confirmed the real manifest resolves representative package stems:
    `SPR1_20230628`, `SPR2_20230628`, `SH67_1_20230707`, `SH67W2_20230711`,
    `AOP_GOLDHILL_20230814`, and `AOP_GORDON_20230814`.
  - The real CSV loaded 44 valid acquisition datetimes; row 31 (`MTST_11`) is
    missing date/time and row 46 has a missing `Plot` value, both now reported
    with clear warnings.
- Verification:
  - `python3 -m py_compile src/spectralbridge/pipelines/drone.py tests/test_drone_pipeline.py`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py::test_load_drone_manifest_parses_flight_datetime tests/test_drone_pipeline.py::test_lookup_flight_datetime_matches_manifest_id_without_date_suffix tests/test_drone_pipeline.py::test_lookup_flight_datetime_matches_compact_mixed_separator_id`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_pipeline.py`
- Next recommended task:
  - Use the manifest path in a real `run_drone_pipeline()` TIFF run and confirm
    the generated per-flight QA audit reports `solar_geometry_source` as
    `manifest_computed` for flights without explicit solar rasters/scalars.

### P35. Drone Manifest Solar Geometry

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-09
- Goal: Restore drone solar-geometry derivation from a flight manifest CSV so
  TIFF-backed drone inputs can produce NEON-equivalent H5 solar angle datasets
  when explicit solar rasters/scalars are not supplied.
- Plan:
  - Keep the standard NEON/AOP pipeline unchanged and contain all behavior in
    `src/spectralbridge/pipelines/drone.py`.
  - Add optional `drone_manifest_path` and `require_solar_geometry` inputs to
    the drone adapter path without requiring them for existing H5 workflows.
  - Implement manifest loading, flight-ID lookup, raster-coordinate lat/lon
    generation, and per-pixel solar zenith/azimuth calculation for TIFF-to-H5
    conversion.
  - Record solar-geometry provenance and summary statistics in drone QA output.
  - Add focused regression tests for manifest parsing, flight lookup,
    manifest-derived H5 geometry, and required-geometry failure behavior.
- Completion notes:
  - Added `load_drone_manifest()` and `lookup_flight_datetime()` to the drone
    adapter with tolerant CSV column matching, flight-id normalization, and
    date-suffix matching such as `AOP_GOLDHILL_20230814` ->
    `AOP_GOLDHILL`.
  - Extended `convert_drone_tiff_to_h5()` to preserve the existing priority
    order for explicit solar rasters/scalars and compute per-pixel
    `Solar_Zenith_Angle` / `Solar_Azimuth_Angle` from manifest acquisition
    datetime plus raster CRS/transform when explicit geometry is absent.
  - Added `drone_manifest_path` and `require_solar_geometry` to
    `run_drone_pipeline()` and threaded manifest-derived datetimes through the
    TIFF-to-H5 preparation stage without modifying the standard NEON/AOP
    pipeline.
  - Added per-flight QA/audit fields for solar geometry source, acquisition
    datetime used, and solar zenith/azimuth summary statistics.
  - Updated the MicaSense/drone tutorial to document manifest-derived solar
    geometry and the required-geometry behavior.
- Verification:
  - `python3 -m py_compile src/spectralbridge/pipelines/drone.py tests/test_drone_pipeline.py`
  - `CSCAL_TEST_MODE=full .venv/bin/pytest -q tests/test_drone_pipeline.py`
  - `python3 scripts/check_docs_links.py`
- Remaining work:
  - `ruff check src tests` was not run because `ruff` is not installed in the
    local `.venv` or available on `PATH` in this environment.
- Next recommended task:
  - Run CI or a local environment with Ruff installed to verify linting, then
    test the manifest path against the real field CSV to confirm timestamp
    timezone assumptions match the acquisition metadata.

### P34. AOP QA PNG Redesign

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-09
- Goal: Redesign the normal AOP/NEON QA PNG so the compact quick-look panel
  explicitly shows the original ENVI, corrected ENVI, and core diagnostics,
  while leaving the multi-page PDF as the fuller audit report.
- Plan:
  - Keep the existing metrics and PDF generation path intact.
  - Reorganize the single-page PNG generated by `render_flightline_panel()` so
    it includes raw and corrected RGB previews plus correction, harmonization,
    and QA-summary diagnostics.
  - Add focused tests that lock the new normal-pipeline QA panel layout without
    touching drone QA behavior.
- Completion notes:
  - Updated the AOP/NEON single-page PNG generated by
    `render_flightline_panel()` to use a compact 2x3 publication-facing layout
    with original ENVI RGB, corrected ENVI RGB, histogram diagnostics,
    wavelength correction distribution, convolved-vs-corrected scatter, and a
    compact QA summary/flags panel.
  - Kept the multi-page PDF generation path intact as the fuller audit artifact,
    preserving the existing raw/corrected/convolved overview and diagnostics.
  - Updated `docs/pipeline/qa_panel.md` to document the distinction between the
    compact PNG quicklook, structured JSON metrics, and full PDF QA report.
  - Added a focused smoke regression in `tests/test_qa/test_qa_metrics_smoke.py`
    to lock the AOP QA PNG panel titles/layout.
- Verification:
  - `python3 -m py_compile src/spectralbridge/qa_plots.py tests/test_qa/test_qa_metrics_smoke.py`
  - `CSCAL_TEST_MODE=full .venv/bin/pytest -q tests/test_qa/test_qa_metrics_smoke.py`
  - `CSCAL_TEST_MODE=full .venv/bin/pytest -q tests/test_qa/test_qa_png_phash.py`
    skipped because optional `imagehash` is not installed in this environment.
  - `python3 scripts/check_docs_links.py`
- Next recommended task:
  - Continue the AOP QA review by deciding which diagnostics, if any, should be
    promoted from the PDF-only audit pages into the compact PNG quicklook.

### P32. Drone QA Panel Labeling Cleanup

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Simplify the drone QA page by removing the inset `% changed` mini-map
  from the correction-magnitude panel and improve panel labels so the layout is
  easier to interpret in exported QA PDFs.
- Plan:
  - Remove the inset map from the per-pixel correction magnitude panel while
    keeping the underlying summary statistics intact in the QA payload/text.
  - Tighten and clarify the visible subplot titles/labels in the drone QA
    figure without changing the scientific metrics being rendered.
  - Update the nearest render regression tests to lock the clarified titles and
    keep the layout stable.
- Completion notes:
  - Removed the `% changed` inset from the spatial correction-magnitude panel
    in `src/spectralbridge/qa_plots.py` while preserving the underlying
    changed-pixel summary metrics in the QA payload and text box.
  - Renamed the visible drone QA subplot titles to clearer publication-facing
    labels for the RGB preview, spectral comparison, correction spectrum,
    spatial correction map, polygon overlay, merged preview, and raw/corrected
    invalid-band maps.
  - Updated the subplot-layout regression in `tests/test_drone_pipeline.py` to
    assert the new titles and explicitly guard against reintroducing the
    `% changed` inset axis.
- Verification:
  - `python3 -m py_compile src/spectralbridge/qa_plots.py tests/test_drone_pipeline.py`
  - `CSCAL_TEST_MODE=full .venv/bin/pytest -q tests/test_drone_pipeline.py -k 'render_drone_panel_places_invalid_maps_on_bottom_row or render_drone_panel_includes_correction_status or render_drone_panel_logs_sampling_debug_and_writes_debug_payload'`

### P31. Drone Polygon Parquet Schema Stabilization

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Stabilize chunked polygon Parquet writing so polygon metadata columns
  keep consistent Arrow-compatible schemas across chunks even when an early
  chunk is entirely null for a text field and a later chunk contains strings.
- Plan:
  - Inspect the shared polygon extraction write path used by
    `extract_polygon_parquet_from_envi()` and identify the narrowest safe place
    to normalize polygon metadata dtypes before Parquet chunk emission.
  - Preserve numeric, datetime, binary WKB, and integer `polygon_id` types
    while ensuring text/object/categorical polygon metadata columns cannot be
    inferred as Arrow `null` from an all-missing first chunk.
  - Add a regression test that reproduces the null-only-first-chunk failure
    mode and verify the chunked writer remains stable without changing NEON
    behavior broadly.
- Completion notes:
  - Added polygon-metadata dtype inference and per-chunk normalization in
    `src/spectralbridge/polygons.py` so chunked polygon extraction stabilizes
    text/object/categorical metadata as pandas string dtype, preserves
    nullable integer `polygon_id`, keeps numeric and datetime metadata typed,
    and preserves WKB bytes instead of letting null-only early chunks lock the
    writer to Arrow `null`.
  - Kept the change local to the shared polygon extraction path used by
    `extract_polygon_parquet_from_envi()` instead of changing the global
    Parquet writer behavior for unrelated NEON exports.
  - Added `tests/test_polygons.py` to reproduce the null-only-first-chunk
    metadata scenario (`species`, `cover_subcategory`,
    `dead_subcategory`) and assert that both extracted chunks reach the writer
    with stable dtypes and preserved later-string values.
- Verification:
  - `python3 -m py_compile src/spectralbridge/polygons.py tests/test_polygons.py`
  - `CSCAL_TEST_MODE=full .venv/bin/pytest -q tests/test_polygons.py`
  - `CSCAL_TEST_MODE=full .venv/bin/pytest -q tests/test_drone_pipeline.py`
- Remaining work:
  - `ruff check src tests` could not be run in this local environment because
    `ruff` is declared in project metadata/CI but is not currently installed in
    either `.venv` or the system Python available to Codex.

### P30. Mixed Drone TIFF Or HDF5 Input Support

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Extend the drone pipeline so it can accept either existing HDF5 inputs
  or source GeoTIFF reflectance inputs, automatically recognize the source
  type, and convert TIFF sources into the working HDF5 contract before the
  existing drone workflow continues.
- Plan:
  - Preserve the existing HDF5 path unchanged and add a narrow TIFF bridge
    rather than rewriting the correction or QA workflow.
  - Convert TIFF inputs into the same working-HDF5 layout the current
    `NeonCube` reader already understands, with explicit validation of raster
    alignment and ancillary requirements.
  - Add regression tests for source-type detection, TIFF-to-working-HDF5
    conversion, and mixed-source pipeline execution.
- Completion notes:
  - `run_drone_pipeline()` now discovers either `.h5` inputs or reflectance
    `.tif` / `.tiff` inputs and automatically branches to the existing HDF5
    path or a new TIFF-to-working-HDF5 conversion bridge.
  - The TIFF bridge emits the same site-group legacy HDF5 layout already
    accepted by `NeonCube`, preserving the downstream correction, QA, and
    polygon workflows instead of creating a parallel TIFF-only execution path.
  - HDF5 inputs still take precedence when both HDF5 and TIFF sources resolve
    to the same derived flight stem.
  - Added focused regression coverage in `tests/test_drone_pipeline.py` for
    source discovery, TIFF-backed pipeline runs, working-HDF5 preparation, and
    `NeonCube` readability of converted TIFF inputs.
  - Updated `docs/tutorials/micasense-to-landsat.md` to document the mixed
    source contract, ancillary TIFF expectations, and TIFF scalar solar-angle
    fallbacks.
- Remaining work:
  - TIFF support currently relies on strict ancillary filename discovery and
    either default 10-band Erick notebook wavelengths/FWHM or explicit
    `tiff_wavelengths_nm` / `tiff_fwhm_nm` arguments for other band layouts.
- Progress notes:
  - Follow-up cleanup is still needed in `tests/test_drone_pipeline.py` so the
    progress/status assertions reflect the new mixed-source logging message
    instead of the old HDF5-only wording.
- Completion notes:
  - Updated the drone progress/status regression test to assert the new
    mixed-source log wording (`type=h5 | stage=preparing working H5`) instead
    of the old HDF5-only phrase.
  - Re-ran a focused mixed-source drone slice covering HDF5 progress logs,
    TIFF source discovery, TIFF-backed runs, and the no-polygon HDF5 path.
- Next recommended task: If TIFF-backed workflows expand further, add a richer
  package metadata contract for ancillary discovery and explicit spectral
  metadata instead of relying on filename heuristics alone.

### P0b. License Migration Audit And Citation Infrastructure

- Priority: P0
- Status: Completed
- Owner: Codex
- Started: 2026-06-02
- Goal: Audit repository licensing, citation, and release-governance state;
  update open-science documentation; and record blockers for any Apache 2.0
  migration.
- Plan:
  - Review current license, metadata, citation, docs, templates, and release
    files.
  - Record discovered gaps and legal blockers before implementing low-risk
    governance/documentation updates.
  - Add durable feature requests for DOI/Zenodo/release infrastructure where
    missing.
- Findings so far:
  - The repository is currently GPLv3 in `LICENSE`, `pyproject.toml`,
    `CITATION.cff`, and `README.md`.
  - Several runtime source files and docs explicitly state that portions are
    adapted from HyTools under GPLv3, which is a legal blocker for silently
    relicensing the current codebase to Apache 2.0.
  - `CITATION.cff` still contains `FILLME` markers, a future-looking release
    date, team-placeholder authors, and GPL metadata.
  - No `NOTICE` file exists.
  - No obvious Zenodo configuration or DOI workflow files are present in the
    repository snapshot reviewed so far.
- Completion notes:
  - Updated `README.md` with stronger citation guidance, current license
    status, open-science framing, and a brief commercialization section that
    does not misstate the current GPL status.
  - Updated `CITATION.cff` to remove `FILLME` markers and incorrect release
    dating while keeping TODO comments for maintainer-approved author details.
  - Updated `CONTRIBUTING.md`, `AGENTS.md`, `pyproject.toml`, and
    `publication_checklist.md` to reflect citation/release expectations and the
    need for legal/provenance review before any Apache 2.0 migration.
  - Confirmed that no issue/PR templates were present under `.github/`, no
    Zenodo configuration was found, and local tags are inconsistent (`0.1`,
    `v1.0.0`).
- Blockers:
  - Apache 2.0 migration appears to require maintainer/legal review and likely
    a provenance audit for GPL-derived HyTools adaptations before any direct
    license replacement.
- Next recommended task: Prioritize DOI/Zenodo/release-governance work and
  decide whether an Apache 2.0 migration is legally feasible for the existing
  codebase.

### P0. Governance And Resumability

- Priority: P0
- Status: Completed
- Owner: Codex
- Started: 2026-06-02
- Goal: Update repo governance so future work is resumable, reviewable,
  test-driven, and feature-request-driven.
- Plan:
  - Update `AGENTS.md` with explicit `FEATURE_REQUESTS.md` workflow rules.
  - Replace the cleanup-oriented placeholder queue with a durable prioritized
    backlog.
- Completion notes:
  - `AGENTS.md` updated to require work-queue-first execution, resumable status
    recording, regression-test preference, and drone HDF5/chunking guardrails.
  - `FEATURE_REQUESTS.md` converted into the authoritative queue for ongoing
    hardening work.
- Next recommended task: Complete P1 before moving to lower-priority items.

### P1. HDF5 Orientation Contract Tests

- Priority: P1
- Status: Completed
- Owner: Codex
- Started: 2026-06-02
- Goal: Add regression tests that protect drone HDF5 orientation assumptions
  using tiny asymmetric non-square synthetic fixtures.
- Requirements:
  - Include reflectance plus ancillary layers for `slope`, `aspect`,
    `solar_zn`, `solar_az`, `sensor_zn`, and `sensor_az`.
  - Verify correct alignment and detect transpose, diagonal mirror, row
    reversal, and column reversal regressions.
  - Document that these tests protect against upstream TIFF-to-HDF5
    orientation regressions without adding TIFF logic to SpectralBridge.
- Plan:
  - Inspect current drone HDF5 loading/orientation helpers and nearby tests.
  - Add focused regression tests with synthetic HDF5 fixtures.
  - Update nearest docs only if the contract is not already documented.
- Completion notes:
  - Added tiny asymmetric non-square synthetic HDF5 orientation tests in
    `tests/test_neon_cube.py` covering reflectance plus `slope`, `aspect`,
    `solar_zn`, `solar_az`, `sensor_zn`, and `sensor_az`.
  - Protected against transpose, row-reversal, and column-reversal regressions
    by asserting the loaded cube and ancillary rasters do not mirror those
    spatial transforms.
  - Documented the drone HDF5 input contract in
    `docs/tutorials/micasense-to-landsat.md`.
- Blockers: Diagonal-mirror regression coverage currently comes from transpose
  assertions because NumPy's 2-D mirror across the diagonal is a transpose for
  these synthetic rasters.
- Next recommended task: Continue with P4 and P5 to validate chunked extraction
  and per-flight parquet outputs end to end.

### P2. Spectral Axis Orientation Tests

- Priority: P2
- Status: Completed
- Goal: Protect `_orient_cube()` for `(lines, columns, bands)`,
  `(bands, lines, columns)`, and `(lines, bands, columns)` without permitting
  spatial mirroring or row/column flipping.
- Completion notes:
  - Added `_orient_cube()` tests for all three supported spectral-axis
    placements and verified that only the spectral axis moves.

### P3. Ancillary Raster Contract Tests

- Priority: P3
- Status: Completed
- Goal: Verify `cube.get_ancillary(...)` fails clearly and actionably when
  ancillary dimensions do not match `(lines, columns)`.
- Completion notes:
  - Added a targeted shape-mismatch regression test asserting the explicit
    `(4, 3)` vs `(3, 4)` error message for ancillary rasters.

### P4. Preserve Chunked Processing

- Priority: P4
- Status: Completed
- Owner: Codex
- Started: 2026-06-02
- Goal: Review drone extraction paths and confirm chunked reading, correction,
  extraction, and restart-safe behavior are preserved.
- Plan:
  - Audit existing drone and polygon-extraction tests against the chunked
    processing guarantees.
  - Add any missing regression coverage needed to prove chunked reading and
    extraction are still the live path.
  - Only mark complete if the current implementation preserves chunked behavior
    without needing risky functional changes.
- Completion notes:
  - Confirmed existing drone correction coverage already locks the correction
    path to chunked full-scene iteration through `apply_drone_corrections`.
  - Added a focused regression test in `tests/test_polygon_extraction.py`
    proving `process_raster_in_chunks` still reads and writes multiple chunk
    windows instead of collapsing to a whole-raster extraction path.
  - Updated stale polygon-extraction tests to patch the current
    `require_rasterio()` import path, keeping the test suite aligned with the
    live implementation.
- Next recommended task: Continue with P5 to decide whether the current drone
  pipeline fully satisfies per-flight parquet expectations beyond polygon mode.

### P5. Per-Flight Parquet Validation

- Priority: P5
- Status: In progress
- Owner: Codex
- Started: 2026-06-03
- Goal: Validate per-flight parquet outputs for polygon mode and full
  extraction, restore missing functionality if needed using chunked processing,
  and surface QA metadata for parquet/merge/CSV status.
- Plan:
  - Confirm the current polygon-mode per-flight parquet outputs retain polygon
    metadata all the way through extraction and merge.
  - Audit the no-polygon drone path against the requested
    `<flight_stem>__extracted.parquet` expectation and treat any larger gap as
    a follow-up only if it can be fixed safely without destabilizing restart
    behavior.
  - Keep chunked extraction intact while closing any metadata-loss regressions.
- Progress notes:
  - Audit found that polygon pixel-index parquets already store polygon
    metadata, but direct ENVI-to-polygon extracted parquets currently drop that
    metadata before merge.
  - Fixed polygon-mode extraction so both the per-product parquet filter and
    the direct ENVI chunked extractor preserve `polygon_id` and user polygon
    attributes in the extracted per-flight parquet outputs.
- Remaining work:
  - The current drone no-polygon path intentionally ends in
    `success_qa_only_no_polygons` rather than producing a
    `<flight_stem>__extracted.parquet` full-scene output. Restoring that
    expectation would be a larger behavioral change and is intentionally left
    open pending a design decision so restart-safe behavior is not changed
    casually.
- Blockers:
  - The requested no-polygon per-flight extracted parquet contract does not
    match the current shipped drone workflow, so this item cannot be marked
    complete without deciding whether to add a new chunked full-scene parquet
    stage.

### P6. Drone QA And Failure-State Tests

- Priority: P6
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Expand drone tests for orientation, extraction modes, chunking, CRS,
  overlap, metadata preservation, overlays, correction failures, and CSV
  failures.
- Completion notes:
  - Confirmed the existing suite already covers the requested categories across
    `tests/test_neon_cube.py` and `tests/test_drone_pipeline.py`, including
    orientation alignment, polygon and no-polygon execution paths, chunked
    correction, CRS/overlap diagnostics, polygon metadata preservation, overlay
    image generation, correction-unavailable handling, and CSV export failures.
  - Re-ran a representative focused slice of those tests to verify the coverage
    remains live after the polygon parquet metadata changes.

### P7. Restart, Checkpoint, And Recovery Integrity

- Priority: P7
- Status: In progress
- Owner: Codex
- Started: 2026-06-03
- Goal: Add selective recovery and validation tests for restart-safe reuse,
  corrupt-output rebuilds, missing downstream products, and explicit statuses.
- Plan:
  - Turn the current skip/rebuild code paths into explicit recovery contracts
    with focused tests around valid-output reuse, corrupt sidecar regeneration,
    and selective downstream recomputation.
  - Reuse existing stage-level helpers where possible instead of adding a new
    recovery framework.
  - Only change runtime behavior if a test exposes a real gap that can be fixed
    safely without broadening the pipeline contract.
- Progress notes:
  - Added restart-contract tests proving a recovered raw ENVI export is reused
    on the next run instead of being rebuilt again.
  - Added a recovery test proving corrupt parquet sidecars are regenerated once
    and then treated as valid skip candidates on subsequent runs.
  - Added a selective recomputation test proving the convolution stage rebuilds
    only a missing downstream sensor product while leaving already-valid sensor
    outputs untouched.
- Remaining work:
  - Explicit machine-readable statuses such as
    `skipped_existing_valid_output`, `recomputed_missing_output`,
    `recomputed_corrupt_output`, and `failed_validation` are still not emitted
    by the core NEON pipeline stages, so this item remains open.
- Blockers:
  - Closing the status-vocabulary gap would require a deliberate API/logging
    decision rather than a test-only hardening pass.

### P8. Output Schema Stability

- Priority: P8
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Protect required parquet schema fields, dtypes, and polygon metadata
  across per-flight and merged outputs.
- Completion notes:
  - Added a canonical-schema regression in `tests/test_schema_parity.py`
    covering required field order through `CANONICAL_COLUMNS` while remaining
    compatible with the lightweight fake-`pyarrow` test environment.
  - Strengthened `tests/test_polygon_pipeline.py` to assert that extracted and
    merged polygon parquets retain `polygon_id` plus user attributes such as
    `species`.
  - Updated `src/spectralbridge/polygons.py` so both polygon extraction paths
    preserve polygon index metadata without abandoning chunked ENVI reads or
    altering output naming.

### P9. Namespace And Container Compatibility

- Priority: P9
- Status: Completed
- Owner: Codex
- Started: 2026-06-02
- Goal: Keep `import spectralbridge` canonical while preserving
  `import cross_sensor_cal` compatibility, add import/CLI tests, and avoid
  cwd-dependent behavior.
- Plan:
  - Extend compatibility tests to assert the deprecation warning and key public
    imports under both namespaces.
  - Add a packaging-level test for the published console-script entry points so
    docs and release metadata stay aligned with the implementation.
  - Avoid changing import behavior unless a test proves a real compatibility
    gap.
- Progress notes:
  - Added tests asserting that `import cross_sensor_cal` emits the expected
    deprecation warning while still re-exporting key top-level helpers from
    `spectralbridge`.
  - Added a packaging-level test that every published console-script entry
    point in `pyproject.toml` resolves to a callable implementation.
- Completion notes:
  - Added non-repo-working-directory tests proving both namespaces and the
    published CLI entry points still resolve from an arbitrary `cwd`, reducing
    the risk of repo-root/container-path assumptions leaking into the package
    surface.

### P10. CI Hardening

- Priority: P10
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Expand CI coverage for `src/spectralbridge/**`, `tests/**`,
  `pyproject.toml`, and workflow changes with targeted install/lint/test steps.
- Completion notes:
  - Hardened `.github/workflows/ci.yml` so push/PR triggers are scoped to the
    actual code/test/workflow surfaces requested, added a package-version import
    smoke step, and inserted targeted drone/QA regression slices ahead of the
    full pytest run.
  - Updated `.github/workflows/qa-ci.yml` to watch `src/spectralbridge/**` in
    addition to the legacy compatibility tree and to generate its fixture using
    `spectralbridge.qa_plots` instead of the deprecated namespace.
- Verification notes:
  - Local workflow YAML parsing could not be run with Python because `pyyaml`
    is not installed in this environment, so workflow verification here was
    limited to source inspection plus targeted test execution.

### P11. Logging Review

- Priority: P11
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Review duplicate handlers plus notebook, multiprocessing, and Ray
  logging behavior; document findings without major refactors.
- Completion notes:
  - Added `docs/dev/logging-review.md` documenting the current logging posture
    across the NEON pipeline, drone pipeline, QA modules, CLIs, multiprocessing,
    and Ray integration.
  - Confirmed the biggest consistency risks are import-time logger setup in
    `pipelines/pipeline.py`, import-time level forcing in `qa_plots.py`,
    root-logger usage in `corrections.py`, and mixed CLI/root-logger handling
    via `logging.basicConfig(...)`.
  - Confirmed the current review did not find an immediate scientific or
    restart-safety bug, so no runtime logging refactor was made in this pass.

### P24. Logging Configuration Cleanup And Harmonization

- Priority: P11
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Incrementally unify library vs CLI logging behavior, reduce import-time
  logger side effects, and standardize progress/log capture behavior across
  NEON, drone, multiprocessing, and Ray paths without destabilizing the
  scientific pipeline.
- Plan:
  - Remove the safest import-time logger side effects first, especially where
    modules force levels or call root logging helpers during import.
  - Keep CLI-visible logging behavior intact by moving configuration into
    explicit runtime helpers where possible.
  - Add focused regression coverage for the changed logging contracts instead
    of attempting a broad logging-system rewrite.
- Completion notes:
  - Added `src/spectralbridge/logging_utils.py` with a shared
    `configure_cli_logging()` helper so CLI entry points configure root logging
    only when the root logger is otherwise unconfigured.
  - Updated `src/spectralbridge/qa_dashboard.py` and
    `src/spectralbridge/cli/recover_cli.py` to use the shared helper instead
    of calling `logging.basicConfig(...)` inline, and made
    `recover_cli.main()` accept optional argv for cleaner testability.
  - Removed `qa_plots` import-time level forcing so the module no longer
    silently pins its logger to `INFO`.
  - Switched `src/spectralbridge/corrections.py` from direct root-logger calls
    to a module-scoped logger so logging behavior now follows the package
    namespace hierarchy instead of bypassing it.
  - Added `tests/test_logging_config.py` to cover the shared CLI logging
    helper, the `qa_plots` import contract, the `corrections.log_stats()`
    logger path, and the updated CLI entry point setup.
- Verification:
  - `python3 -m py_compile src/spectralbridge/logging_utils.py src/spectralbridge/qa_dashboard.py src/spectralbridge/cli/recover_cli.py src/spectralbridge/qa_plots.py src/spectralbridge/corrections.py tests/test_logging_config.py`
  - `CSCAL_TEST_MODE=full .venv/bin/pytest -q tests/test_logging_config.py`
  - `CSCAL_TEST_MODE=full .venv/bin/pytest -q tests/test_drone_pipeline.py -k 'render_drone_panel_logs_sampling_debug_and_writes_debug_payload or render_drone_panel_includes_correction_status or render_drone_panel_places_invalid_maps_on_bottom_row'`

### P33. Pipeline Logger Ownership Review

- Priority: P11
- Status: Todo
- Goal: Decide whether the module-owned handler in
  `spectralbridge.pipelines.pipeline` should remain an intentional application
  behavior or eventually move to the same explicit runtime-configuration model
  now used by the lighter CLI utilities.

### P12. Public API Contract Review

- Priority: P12
- Status: Completed
- Owner: Codex
- Started: 2026-06-02
- Goal: Review whether current smoke tests capture intentional public APIs
  without freezing internal helpers.
- Completion notes:
  - Reworked the public API smoke tests to derive the matrix from intentional
    module exports instead of every non-underscore helper found under `src/`.
  - Kept coverage on top-level package, CLI, and pipeline entry points while
    allowing internal helpers to evolve without being frozen into the contract.

### P13. Release Hygiene

- Priority: P13
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Audit license/readme/citation/resources/manifest and confirm prompt
  logs, temporary outputs, large data, and development artifacts are not
  shipped unintentionally.
- Completion notes:
  - Tightened `MANIFEST.in` to stop explicitly shipping maintainer-only files
    and to exclude obvious accidental artifacts such as `PROMPT_LOG.md`,
    root-level notebooks, `:memory:`, and local contribution notes.
  - Added `docs/dev/release-hygiene.md` documenting the release-hygiene audit,
    the manifest changes, and the remaining repo-level concerns that are now
    visible to maintainers.
  - Confirmed local docs links still pass after the new review note was added.
- Verification notes:
  - A real source-distribution build could not be executed in this environment
    because the active Python lacks `setuptools` and `build`, so this item was
    verified by manifest review plus targeted docs checks rather than by
    inspecting a built artifact directly.

### P14. Versioning Review

- Priority: P14
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Review version definitions and release process to prevent drift.
- Completion notes:
  - Added `docs/dev/versioning-review.md` documenting the current version
    sources, the local tag drift, and the mismatch between packaged metadata
    (`2.2.0`) and the leading `CHANGELOG.md` release heading (`2.3.0`).
  - Updated `CONTRIBUTING.md` so release guidance explicitly includes
    `src/spectralbridge/__init__.py` and warns against leaving future release
    headings above the current packaged version unless they are clearly
    unreleased.
  - Updated `publication_checklist.md` with an explicit version-sync checklist
    item so future releases verify `pyproject.toml`, `__init__.py`,
    `CITATION.cff`, `CHANGELOG.md`, and the Git tag together.
- Verification notes:
  - This pass was a repository-state audit only. No version numbers or tag
    history were rewritten automatically.

### P15. Dependency Review

- Priority: P15
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Review `ray`, `geopandas`, and `rasterio` dependency posture and
  whether extras should change without breaking installs.
- Completion notes:
  - Added `docs/dev/dependency-review.md` documenting the current dependency
    layout and why `ray`, `rasterio`, and `geopandas` should remain required
    under the current workflow contract.
  - Updated `docs/env.md` to reflect the real runtime dependency stack and to
    clarify that `rioxarray` / `xarray` are optional notebook companions, not
    direct package requirements.
  - Confirmed that changing extras automatically would amount to a packaging
    redesign rather than a safe hardening tweak, so dependency declarations
    were left unchanged in this pass.

### P16. Documentation Modernization

### P16. Documentation Modernization

- Priority: P16
- Status: Completed
- Owner: Codex
- Started: 2026-06-02
- Goal: Prefer `import spectralbridge` in examples while documenting HDF5
  contracts, chunking, restart behavior, parquet authority, CSV sidecars, and
  drone/NEON workflows.
- Plan:
  - Bring the homepage workflow visuals and high-traffic subpages into the new
    docs visual system so the site feels consistent end to end.
  - Audit `quickstart.md`, `usage/cli.md`, and the pipeline overview/output
    pages against the current package entry points and documented outputs.
  - Update page structure and copy to match the actual CLI defaults, outputs,
    and restart-safe behavior without inventing features.
- Progress notes:
  - Updated the homepage workflow arrows to match the left-to-right visual
    flow.
  - Reworked `docs/quickstart.md`, `docs/usage/cli.md`,
    `docs/pipeline/stages.md`, and `docs/pipeline/outputs.md` into the newer
    docs visual system while aligning examples and command details with the
    current package entry points.
  - Added broader docs styling so non-homepage pages better match the primary
    landing-page direction without requiring a full docs rewrite in one pass.
  - Started a second docs pass for the remaining high-traffic pages:
    `docs/concepts/why-calibration.md`, `docs/pipeline/qa.md`,
    `docs/usage/parquet.md`, and `docs/troubleshooting.md`.
  - Completed that second pass and aligned those pages with the newer
    card-and-section layout while keeping the content tied to the current
    package behavior, restart guidance, and CLI entry points.
  - Verified that the public docs and `README.md` no longer contain stale
    `cross_sensor_cal` or `cross-sensor-cal` references.
- Completion notes:
  - Modernized the remaining older public docs pages that were still visually
    and structurally out of sync with the refreshed site, including
    `docs/faq.md`, `docs/reference/configuration.md`,
    `docs/reference/validation.md`, `docs/reference/schemas.md`,
    `docs/api/index.md`, and `docs/tutorials/cloud-workflow.md`.
  - Updated those pages to use the newer card-and-section layout while keeping
    examples aligned with the current package behavior, canonical namespace,
    restart-safe workflow, and published CLI entry points.
  - Corrected stale configuration guidance by removing unsupported runtime
    environment-variable claims and documenting the environment knobs that are
    actually read by the current code.
- Verification:
  - `python3 scripts/check_docs_links.py`

### P17. Architecture Audit

- Priority: P17
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Document lightweight findings on duplicate metadata/path/output logic,
  chunking consistency, restart-safe consistency, QA consistency, and shared
  drone/NEON infrastructure opportunities.
- Plan:
  - Review the live orchestration, path, merge, polygon, QA, and metadata
    modules rather than proposing a speculative redesign.
  - Capture concrete duplication and consistency findings in a maintainer-facing
    architecture audit.
  - Create follow-up feature requests only where the current implementation is
    working but visibly split across multiple helpers.
- Completion notes:
  - Added `docs/dev/architecture-audit.md` with a documentation-only review of
    the live orchestration, path, merge, polygon, metadata, chunking, and QA
    layers.
  - Confirmed that the strongest architectural invariants are still the
    file-based stage ordering, restart-safe reruns, chunk-preserving NEON
    processing, and treating parquet and QA outputs as contracts.
  - Identified split naming authority between `FlightlinePaths` and
    `get_flightline_products()` plus duplicated output-discovery logic across
    merge, polygon, QA, and summary helpers as the main maintainability
    hotspots.
  - Confirmed that the best shared drone/NEON opportunities are around
    artifact lookup and validation helpers, not around collapsing both
    orchestration layers into one pipeline entry point.
- Next recommended task: Continue with P18, and treat P25/P26 below as
  additive cleanup work rather than urgent refactors.

### P25. Output Discovery Consolidation

- Priority: P17
- Status: Todo
- Goal: Reduce duplicated parquet and merged-output discovery logic across
  `merge_duckdb.py`, `polygons.py`, `qa_plots.py`, and QA summary helpers by
  introducing shared artifact-location utilities without changing filename
  contracts.

### P26. Naming Authority Review

- Priority: P17
- Status: Todo
- Goal: Decide whether `FlightlinePaths` should subsume more of
  `get_flightline_products()` or whether the current dual path/naming layer is
  intentionally permanent, then document that decision for future maintainers.

### P18. DOI And Zenodo Integration

- Priority: P18
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Add and document DOI generation infrastructure, including Zenodo
  enablement steps, release-to-DOI workflow guidance, and maintainer-facing
  verification steps.
- Plan:
  - Verify the repository's current external DOI/Zenodo state before changing
    local docs or badges.
  - Surface any existing DOI clearly in the README while distinguishing between
    archived historical releases and the current package version.
  - Add maintainer-facing documentation for Zenodo verification and release
    updates so DOI state remains reproducible.
- Completion notes:
  - Verified that the repository already has a Zenodo software archive for the
    pre-rename `earthlab/cross-sensor-cal: Version 1` release published on
    2024-05-09 with DOI `10.5281/zenodo.11167877`.
  - Added the existing Zenodo DOI badge to `README.md` and updated the
    citation section so it no longer claims DOI infrastructure is undocumented.
  - Added `docs/dev/doi-zenodo.md` documenting the current Zenodo state, the
    distinction between the historic archived release and the current
    `SpectralBridge` package version, and the maintainer verification workflow
    for future releases.
  - Added a Zenodo verification reminder to `publication_checklist.md`.
- Next recommended task: Continue with P19, and treat P27 below as a follow-up
  if maintainers want a post-rename SpectralBridge-specific Zenodo release
  record to be explicitly refreshed.

### P27. Zenodo Metadata Refresh For Post-Rename Releases

- Priority: P18
- Status: Todo
- Goal: Ensure the next archived Zenodo release uses current SpectralBridge
  naming, synchronized version metadata, and the maintainers' preferred DOI
  target strategy (historic version DOI vs concept/latest DOI).

### P19. Release Automation And Notes

- Priority: P19
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Add durable release automation guidance covering tagged releases,
  release notes, changelog/release note generation, and citation metadata
  refresh steps.
- Plan:
  - Review the existing GitHub Actions and maintainer docs to see what release
    automation is missing today.
  - Add a conservative tag-driven release workflow that builds and validates
    package artifacts without assuming PyPI credentials.
  - Document the maintainer release sequence, including changelog, citation,
    Zenodo, and release-note verification steps.
- Completion notes:
  - Added `.github/workflows/release.yml` so version tags matching
    `vMAJOR.MINOR.PATCH` now build `sdist` and wheel artifacts, run
    `twine check`, install the built wheel for an import smoke test, upload the
    artifacts, and create or update a GitHub release with generated release
    notes.
  - Added `docs/dev/releasing.md` documenting the maintainer release sequence,
    including version synchronization, changelog review, citation refresh,
    Zenodo verification, and the current limits of the automation.
  - Updated `CONTRIBUTING.md` and `publication_checklist.md` so the release
    workflow and maintainer checklist are part of the documented project
    process.
- Next recommended task: Continue with P20, and treat P28 below as a follow-up
  if maintainers want CI to block tag cuts when package metadata and tags are
  out of sync.

### P28. Release Metadata Sync Validation

- Priority: P19
- Status: Todo
- Goal: Add a release-focused validation check that confirms the Git tag,
  package version, `CITATION.cff`, and changelog header are synchronized before
  a release is treated as valid.

### P20. Software Citation And Publication Tracking

- Priority: P20
- Status: Completed
- Owner: Codex
- Started: 2026-06-03
- Goal: Track associated publications, software-paper plans, preferred citation
  language, and versioned release citation policy in a maintainer-friendly way.
- Plan:
  - Review the existing citation guidance, DOI notes, and maintainer-facing
    publication references already present in the repository.
  - Add a dedicated maintainer document that records preferred citation
    language, publication-tracking placeholders, and the current policy for
    citing software releases vs associated papers.
  - Link that guidance from the README and/or release-facing docs so it stays
    discoverable.
- Completion notes:
  - Added `docs/dev/software-citation.md` as the maintainer-facing source of
    truth for preferred citation wording, versioned release citation policy,
    associated publication tracking, and software-paper placeholders.
  - Updated `README.md` so the public citation section now points maintainers
    to both the DOI/Zenodo note and the new citation-policy tracker.
  - Updated `publication_checklist.md` so software citation and publication
    tracking is part of the documented release-readiness checklist.
- Next recommended task: Continue with P21, and treat P29 below as a follow-up
  for filling in the actual publication list once maintainers confirm the
  canonical references.

### P29. Populate Confirmed Publication References

- Priority: P20
- Status: Todo
- Goal: Replace the placeholder publication-tracking entries in
  `docs/dev/software-citation.md` with the maintainer-approved software paper,
  associated publications, and canonical citation strings once those references
  are confirmed.

### P21. Long-Term Governance And Open Science Policy

- Priority: P21
- Status: Todo
- Goal: Document maintainer-facing governance, open-science expectations,
  citation/release ownership, and commercialization-compatible stewardship
  guidance.

### P22. Contributor Templates And Acknowledgements

- Priority: P22
- Status: Todo
- Goal: Add or refresh GitHub issue/PR templates, acknowledgement guidance, and
  maintainer-facing contribution prompts for release/citation-sensitive changes.

### P23. Release Tag Hygiene

- Priority: P23
- Status: Todo
- Goal: Normalize release tag conventions, document the canonical tag scheme,
  and reconcile any legacy inconsistent tags in maintainers' release records.

## Completed Requests

- 2026-06-02: Publication cleanup backlog completed and moved to
  `docs/dev/publication-cleanup-log.md` plus `publication_checklist.md` for
  release gating details.
- 2026-06-02: Hardened Ray startup compatibility by falling back to the thread
  executor when Ray cannot initialize before task submission in the local
  environment.
- 2026-06-02: Stabilized the public API smoke matrix so it imports the current
  repo source without polluting later tests.

## Blockers And Resume Notes

- Local verification depends on which Python/test dependencies are available in
  the active environment. Record any missing tooling under the active item
  before stopping.
