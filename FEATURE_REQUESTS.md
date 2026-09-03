# SpectralBridge Feature Requests

Review date: 2026-09-03
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

### P68. Across-Track Half-Flight Processing

- Priority: User-directed
- Status: Complete
- Owner: Cursor Agent
- Started: 2026-09-03
- Completed: 2026-09-03
- Goal: Add an opt-in `split_across_track` mode that processes a NEON
  flightline as independent left/right column halves without changing the
  default full-flightline path.
- Outcome: Default `go_forth_and_multiply` / `process_one_flightline` path
  is unchanged. `split_across_track=True` downloads the original H5 once,
  then processes `{id}_left` and `{id}_right` with an across-track H5
  column window so ENVI + BRDF only load that half. Shared H5 stays at
  `<base>/<id>.h5`; each half folder gets a full renamed product tree.
- Verification: `pytest -q tests/test_neon_cube.py tests/test_split_across_track.py tests/test_pipeline_ray_engines.py tests/test_stage_export.py tests/test_brdf_topo_chunking.py tests/test_brdf_topo_streamlined.py`
- Blockers: None.
- Next recommended task: Run a real stalled YELL/WREF flightline with
  `split_across_track=True` and `engine="thread", max_workers=1`.

### P67. Defer Stage QA Until End Of Flightline And Bound ENVI Reads

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-17
- Goal: Keep the new stage QA reports (acquisition through analysis tables)
  and the legacy flightline QA panel, but run both only after the scientific
  pipeline has finished. Stage QA must read each stage's on-disk ENVI/Parquet
  products with bounded sampling so Jupyter kernels do not OOM after BRDF/topo
  writes a multi-GB corrected cube.
- Plan:
  - Stop emitting stage QA between download/export/correction/convolution.
  - After polygon extraction (or skip), free memory, then
    `run_completed_flightline_qa` followed by `render_flightline_panel`.
  - Sample hyperspectral ENVI from a BSQ memmap one band at a time; never
    materialize a full cube as float32.
  - Add regression tests and update stage-QA docs.
- Completion notes:
  - Mid-stage `_emit_stage_qa_safe` calls were removed from
    `process_one_flightline` and from the H5 download loop.
  - `_run_end_of_pipeline_qa` runs after convolution/merge/polygon: stage QA
    from on-disk artifacts, then the legacy `_qa.png` panel.
  - `emit_stage_qa` memmaps BSQ ENVI and copies a spatial preview one band at
    a time; paired BRDF QA loads the reference preview separately and does not
    keep two full cubes.
  - `qa_mode="off"` still skips new stage reports but still writes the legacy
    panel. Default remains `standard`.
- Verification:
  - `/opt/anaconda3/bin/pytest -q tests/test_stage_qa.py tests/test_brightness_coefficients.py`
    (31 passed)
- Blockers: None.
- Next recommended task: Re-run the NIWO flightline with default `qa_mode`
  (or `"standard"`) so stage QA happens after convolution instead of after
  the BRDF write.

### P66. Add Independent Bulk Cross-Run Analysis Pipeline

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-09-03
- Goal: Add a pipeline, separate from the NEON and drone processors, that
  recursively discovers completed run outputs under a supplied directory,
  builds one restart-safe cross-run analysis dataset, and calculates pooled
  MicaSense-to-Landsat regressions from the full collection.
- Scope:
  - Accept a local root directory, including paths under the user's home
    directory, and recursively inventory compatible merged Parquet outputs.
  - Materialize a portable super-Parquet dataset and a queryable DuckDB
    catalog without loading all rows into Python memory.
  - Calculate deterministic pooled per-band MicaSense-to-Landsat regression
    coefficients with source and row-count provenance.
  - Keep all artifacts in an explicit bulk-analysis output directory and make
    no changes to individual NEON or drone run directories.
  - Add a public Python entry point, dedicated CLI, focused tests, and user and
    reference documentation.
- Plan:
  - Audit existing merge, sensor-panel, path, CLI, documentation, and testing
    conventions.
  - Implement recursive discovery, schema-aware union, DuckDB-backed
    materialization, pooled regression summaries, and restart-safe manifests.
  - Add regression and contract tests for discovery, provenance, incompatible
    inputs, deterministic reruns, and CLI/API exposure.
  - Document inputs, outputs, scientific interpretation, and the distinction
    between pooled synthetic regression and brightness adjustment.
  - Run focused tests, lint or compilation checks, documentation validation,
    and AI-transparency regeneration.
- Outcome (2026-09-03):
  - Added the independent `run_bulk_pipeline` API and `spectralbridge-bulk`
    CLI. They accept one canonical merged Parquet or recursively inventory a
    supplied directory tree without invoking or mutating the NEON and drone
    orchestrators.
  - Defaulted discovery to full-pixel
    `*_merged_pixel_extraction.parquet` products and added explicit `polygon`
    and `both` modes so polygon subsets are not silently double-counted.
    Invalid canonical candidates remain visible as rejected catalog records.
  - Added a streaming DuckDB union-by-name build of
    `bulk_observations.parquet` with per-row source provenance, plus
    `bulk_analysis.duckdb`, `bulk_sources.parquet`, pooled coefficient
    JSON/Parquet, and a restart manifest.
  - Added exact pooled MicaSense-X/Landsat-Y regressions across all valid rows,
    recording slope, intercept, correlation, R², bias, RMSE, MAE, row count,
    source count, and value ranges. The artifacts explicitly retain the
    same-source synthetic evidence boundary and state that upstream persisted
    brightness state is consumed as-is rather than refitted.
  - Added five focused bulk-pipeline tests, public API/CLI coverage, a dedicated
    documentation page, CLI/API/output/schema references, README/start-page
    guidance, and a clean runnable bulk-analysis notebook.
- Verification:
  - Full `pytest -q` suite passes with the repository's six expected skips.
  - Thirty focused bulk, sensor-panel, public-API, and notebook tests pass; the
    five bulk-specific tests also pass independently.
  - Strict MkDocs build, documentation link validation, Python compilation,
    diff whitespace checks, and AI-transparency freshness checks pass.
- Blockers: Ruff is not installed in the local environment, so Ruff could not
  be run.
- Next recommended task: Run `spectralbridge-bulk` against the real processed
  data tree, review the pooled population and upstream brightness consistency,
  and only then approve a versioned coefficient set for drone translation.

### P65. Repair Current Full-Suite Test Failures

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-17
- Goal: Resolve the pasted full-suite failures without changing scientific
  assumptions or pipeline behavior.
- Scope:
  - Align brightness coefficient tests and synthetic QA fixtures with the
    currently packaged brightness coefficient JSON files.
  - Make pipeline engine tests robust to no-op/stubbed downloads while keeping
    real download logging intact.
  - Confirm the stale Playwright docs assertion is already repaired locally or
    patch it if needed.
  - Refresh AI transparency artifacts after logging the prompt.
- Plan:
  - Read the failing tests, current coefficient files, and orchestration code.
  - Apply the smallest code/test changes that restore the intended contracts.
  - Run focused failing tests plus lightweight repository checks.
- Outcome (2026-08-17):
  - Confirmed the pasted Playwright assertion was already repaired locally; the
    local test now checks the durable "Before minus after correlation." table
    cell.
  - Treated commit `8417135` and the packaged brightness JSON files as the
    current source of truth, then updated brightness tests and the synthetic
    stage-QA brightness fixture to use those current coefficients instead of
    stale pre-update values.
  - Made the high-level pipeline logger tolerate test stubs or no-op download
    helpers that return `None`, while real downloads still log the returned H5
    filename.
  - Regenerated and verified AI transparency artifacts after logging this
    prompt.
  - Focused failing tests pass, and the exact pasted full command
    `pytest -q --cov=spectralbridge --cov-branch` passes locally with 53.94%
    coverage against the 45% floor.
- Blockers: Ruff is not installed in the local `.venv`, so no Ruff check was
  available.
- Next recommended task: Decide whether checked-in real R10C brightness QA
  artifacts should be regenerated from products produced with the newer Table
  Mountain HLS coefficient table, or explicitly labeled as historical
  validation artifacts.

### P64. Add Printable Combined Stage QA PDF

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-17
- Goal: Produce a single downloadable PDF companion to the combined stage-QA
  HTML report so users can compare complete flightline summaries outside the
  browser.
- Scope:
  - Add a canonical `combined_qa.pdf` artifact next to `combined_qa.html`.
  - Build the PDF from the same combined and stage payloads used by the HTML
    reports, including stage summaries and available diagnostic figures.
  - Preserve existing HTML, JSON, plot, naming, and restart behavior.
  - Document the artifact and add focused regression coverage.
- Plan:
  - Extend the combined QA paths and report assembly code.
  - Add a deterministic multi-page PDF renderer with graceful handling of
    missing stage plots.
  - Verify with a focused stage-QA test and update generated AI transparency.
- Outcome (2026-08-17):
  - Added canonical `qa/combined/combined_qa.pdf` output via
    `CombinedQAPaths.pdf`.
  - `assemble_combined_report()` now writes the HTML first and then emits a
    single letter-sized, page-numbered PDF containing the combined summary,
    cross-stage interpretation, pipeline evolution figure, each stage summary,
    and each available stage diagnostic image.
  - Regenerated the checked-in R10C validation artifact at
    `docs/validation/artifacts/r10c-l002-20210915/qa/combined/combined_qa.pdf`
    as a 19-page PDF.
  - Updated output and stage-QA docs and refreshed AI transparency artifacts.
  - Focused stage-QA tests, compile checks, doc-link checks, PDF metadata
    inspection, and rendered-page visual checks pass.
- Blockers: Ruff is not installed in the local `.venv`, so Ruff could not be
  run from this environment.
- Next recommended task: Add a small CLI/status message that prints the PDF path
  after `spectralbridge-stage-qa` rebuilds an existing flightline report.

### P63. Diagnose BRDF Kernel Crash At Zero Percent

- Priority: User-directed
- Status: Paused after user redirect
- Owner: Codex
- Started: 2026-08-17
- Goal: Determine why the local kernel exits as BRDF processing begins and
  distinguish an out-of-memory/process-backend failure from a scientific data
  or algorithm error.
- Scope:
  - Trace BRDF initialization, chunk allocation, and execution backend settings.
  - Inspect the available R10C run artifacts and any local diagnostic logs.
  - Report the evidence-backed cause and conservative ways to run the existing
    pipeline without changing its scientific assumptions.
- Plan:
  - Read the BRDF/topographic orchestration and its focused tests/docs.
  - Estimate first-chunk memory and identify work duplicated across workers.
  - Reproduce only with a bounded diagnostic if existing evidence is
    insufficient, then document findings and next actions.
- Current finding:
  - Evidence gathered before redirect points to first-tile memory pressure in
    scene-mode BRDF/topographic application rather than a scientific data
    quality failure: the R10C cube expands to roughly 10 GiB as float32, and the
    current scene-mode apply path can hold several full-scene arrays before the
    progress bar advances beyond 0%.
- Remaining work:
  - If resumed, provide the user-facing diagnosis and optionally implement a
    bounded row-strip application mode that preserves scene-level coefficients.

### P62. Synthetic Sensor Regression Plot And Coefficient Sidecar

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-17
- Goal: Add an explicit end-of-run comparison of paired synthetic MicaSense and
  Landsat products, with the plotted linear-regression coefficients retained
  for inspection while empirical calibration remains deferred.
- Scope:
  - Reuse the existing wavelength-matched MicaSense/Landsat synthetic panels.
  - Label the plot as a synthetic diagnostic rather than empirical calibration.
  - Persist deterministic slope, intercept, correlation, R², and sample-count
    records for every plotted band pair.
  - Preserve existing PNG filenames and pipeline restart behavior.
- Plan:
  - Refactor the plotting regression helper to return its displayed metrics.
  - Write one JSON sidecar beside each generated comparison panel.
  - Add focused regression tests and document the new QA artifact.
- Outcome (2026-08-17):
  - Preserved the existing end-of-run MicaSense-versus-Landsat PNG filename and
    made its title and footer explicitly identify both axes as synthetic
    products derived from the same corrected NEON source.
  - The plotted ordinary least-squares equation now comes from one reusable
    metric record containing slope, intercept, correlation, R², and sample
    count. Each PNG receives an atomic, same-stem JSON coefficient sidecar.
  - Made DuckDB reservoir sampling repeatable with a fixed seed so repeated
    runs produce identical coefficient records; the deterministic fallback
    also avoids random ordering.
  - Added focused numerical and artifact tests, including byte-identical JSON
    regeneration. Nine targeted tests, strict MkDocs, documentation links,
    generated-page checks, AI-transparency freshness, compilation, and visual
    inspection pass.
- Blockers: None.
- Next recommended task: Later empirical translation work should supply paired
  observed sensor measurements and blocked validation folds; it must not reuse
  these same-source synthetic coefficients as fitted calibration evidence.

### P61. Repair Stale Topographic Validation Browser Assertion

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-17
- Goal: Restore the docs browser smoke test after the generated topographic
  validation page replaced an older prose sentence with structured check and
  diagnostic documentation.
- Scope:
  - Align the browser assertion with durable content generated from
    `scripts/validation_docs_content.py`.
  - Preserve the current scientific wording and generated-doc contract.
  - Rebuild the docs and run focused source and browser verification.
- Plan:
  - Confirm the rendered page contains the structured topographic diagnostic.
  - Replace only the stale prose assertion with a current durable contract.
  - Run focused validation-doc and Playwright tests, then record the outcome.
- Outcome (2026-08-17):
  - Confirmed the failure was test drift introduced when the generated module
    guide replaced the legacy sentence with structured check and diagnostic
    tables; the validation results and page generation were current.
  - Replaced the deleted prose assertion with the unique generated diagnostic
    definition, `Before minus after correlation.`, preserving the intended
    topographic-correction browser contract without changing scientific text.
  - Generated validation pages are current, five focused validation-doc tests
    pass, strict MkDocs build passes, the rendered diagnostic is uniquely
    visible, and the full Playwright docs smoke test passes.
- Blockers: None.
- Next recommended task: Continue P46 with a pinned, representative live NEON
  flightline inventory before interpreting the offline campaign as cross-site
  scientific validation.

### P60. QA Code Organization And Validation Website Guide

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-15
- Goal: Keep the expanded QA implementation easy to navigate and make the
  Validation website explain every implemented check in the stage where users
  encounter it, illustrated with the real R10C run.
- Scope:
  - Audit `src/spectralbridge/qa/` for clear responsibilities, naming,
    docstrings, and avoidable concentration of unrelated logic.
  - Refactor only where organization can improve without changing scientific
    calculations, thresholds, schemas, filenames, or pipeline behavior.
  - Expand every Validation module page with the test purpose, varied inputs,
    pass/fail interpretation, diagnostics, limitations, and related stage QA.
  - Add a stage-oriented real-data validation guide with example figures from
    the checked-in R10C report bundle and clear links to HTML/JSON evidence.
  - Keep generated validation pages reproducible from their generator.
- Plan:
  - Inventory QA source modules, test ownership, validation-page generation,
    navigation, and real figures.
  - Add a concise QA architecture map and extract documentation metadata from
    generated-page prose so tests remain traceable and maintainable.
  - Regenerate the website pages, add real stage examples, and verify source,
    generated-doc, link, visual, lint, and test contracts.
- Outcome (2026-08-15):
  - Confirmed that `src/spectralbridge/qa/` already separates schemas, paths,
    thresholds, metrics, brightness diagnostics, network diagnostics, plots,
    stage assembly, reporting, and orchestration. Added section markers and
    missing helper docstrings in the stage coordinator without changing its
    calculations, thresholds, schemas, filenames, or output behavior.
  - Added a maintainer-facing QA implementation map with module ownership,
    execution flow, extension rules, and matching test locations.
  - Centralized publication-facing explanations in typed documentation records.
    Every recorded module input, Boolean check, diagnostic, real-stage check
    family, pass contract, review action, and evidence limitation is covered by
    a regression test.
  - Expanded the Validation overview and all eight module pages, and added a
    six-stage QA guide that reports the observed R10C status and value for each
    check family. The pages distinguish software contracts, numerical QA, and
    scientific validation and preserve `WARN`/`NOT EVALUATED` evidence.
  - Added linked, captioned examples from every stage of the checked-in R10C
    run. Figure cards are responsive and use correct nested-page paths; a
    regression test protects that deployment contract.
  - Regenerated the website pages from campaign JSON, refreshed the AI
    transparency artifacts, and visually inspected desktop and narrow layouts.
    Focused validation tests, the full suite, repository-wide Ruff, strict
    MkDocs, documentation-link checks, generated-page freshness, and browser
    console checks pass.
  - Made the idempotence/skip test explicitly select the thread backend. Its
    subject is restart behavior, while Ray selection remains covered by the
    dedicated engine tests; this avoids a real Ray startup during unit tests.
- Blockers: None.
- Next recommended task: Continue P46 with a pinned, representative live NEON
  flightline inventory before interpreting the current offline campaign as
  cross-site scientific validation.

### P59. Complete Stage Figures And Python Brightness Diagnostics

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-15
- Goal: Give every canonical QA stage a meaningful image, add clear Parquet
  extraction/merge and correction diagnostics, and reproduce the historical R
  brightness-coefficient figures in tested Python code.
- Scope:
  - Emit at least one deterministic, location-labeled image for acquisition,
    input, correction parameters, combined correction, convolution, and
    analysis-table stages.
  - Add table-structure and merged-output plots without loading entire Parquet
    products into memory.
  - Port the plots and statistical intent in `coef_plots_Ty.qmd` at commit
    `a30498a` to Python against the packaged coefficient JSON files.
  - Add brightness-correction numerical and plotting tests without changing
    coefficients or correction behavior.
- Plan:
  - Audit the historical QMD, active brightness code, coefficient schemas,
    stage artifacts, and existing tests.
  - Add reusable stage renderers and a Python coefficient-diagnostics entry
    point using the existing QA plot contract.
  - Regenerate the real report bundle, document the figures, and verify tests,
    lint, docs, and generated artifacts.
- Outcome (2026-08-15):
  - Added deterministic, location-labeled images for every canonical stage:
    source artifact inventory, input reflectance, correction parameters,
    combined BRDF/topographic correction, spectral convolution with brightness
    audits, and Parquet extraction/merge structure.
  - Added stage-QA schema 1.3 and plot-contract version 1.1. Every stage records
    the plot contract; new fixed ranges cover brightness adjustments, BRDF
    coefficients, and physical geometry summaries.
  - Ported the core statistical intent of historical `coef_plots_Ty.qmd` into
    Python: paired before/after reflectance, per-band linear gains,
    fitted-versus-configured coefficient profiles, and bandwise medians.
    Invalid diagnostic cells are excluded pairwise and source products are not
    modified.
  - Added a non-provisional brightness-application contract test. On the real
    R10C run, all four Landsat products passed with maximum absolute fitted gain
    errors between `2.61e-08` and `2.76e-08`, against a `1e-4` tolerance.
  - Added a report-only physical-range review for persisted correction geometry.
    The real run now marks four sentinel-contaminated fields as `WARN`, displays
    their unfiltered summaries, and does not mask or rewrite them.
  - Parquet figures distinguish extracted and merged products while obtaining
    row counts and schemas through DuckDB rather than loading full tables.
  - Regenerated and visually inspected the checked-in R10C HTML/JSON/PNG report
    bundle. Focused tests, the full branch-aware suite, repository-wide Ruff,
    strict MkDocs build, documentation links, and AI-transparency freshness all
    pass. Combined branch-aware coverage is 52.84%, above the 45% gate.
- Blockers: None.
- Next recommended task:
  - Run a small multi-site pilot and review whether the fixed plot ranges and
    geometry-warning summaries remain interpretable before starting the full
    approximately 300-flightline campaign.

### P58. Comparable QA Plot Scales And Embedded Location Labels

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-15
- Goal: Make QA figures directly comparable across an approximately 300-run
  validation campaign without relying on surrounding report headers.
- Scope:
  - Standardize physical x/y axes and map color ranges wherever a shared scale
    is scientifically meaningful.
  - Preserve values outside display limits in metrics and annotate clipping;
    plotting limits must not alter data or QA calculations.
  - Embed flightline/location identity in every stage and combined figure.
  - Use georeferenced map axes when valid ENVI map metadata are available;
    otherwise label sampled row/column axes explicitly.
- Plan:
  - Define and document one reusable QA plotting-scale contract.
  - Pass location and map metadata through the stage plotting entry points.
  - Add plot-contract tests and regenerate the real-flightline report bundle.
- Outcome (2026-08-15):
  - Added stage-QA schema 1.2 and machine-readable plot-contract version 1.0
    with fixed wavelength, reflectance, valid/negative fraction, correction,
    RGB, and seam-score display ranges.
  - Standardized reflectance/difference map normalization. The correction map
    uses one fixed symmetric-log normalization so subtle differences remain
    visible while all runs keep identical endpoints and transformation.
  - Embedded compact site, domain, flightline, and date labels in every stage
    and combined figure. Spatial panels now use ENVI map metadata for UTM
    easting/northing axes, with explicit sampled row/column fallback.
  - Values outside display limits remain unchanged in files and metrics;
    affected panels annotate the clipped display fraction.
  - Added direct axis, color-normalization, georeferencing, location-label, and
    combined-figure contract tests. Regenerated and visually inspected the real
    R10C report bundle.
  - Full unit-mode suite: 218 passed and seven expected skips. Branch-aware
    coverage is 56.41% statements, 38.55% branches, and 52.01% combined.
- Blockers: None.
- Next recommended task:
  - Run a small multi-site pilot with plot-contract version 1.0 before the full
    campaign, then version any display-contract change instead of silently
    rescaling an active campaign.

### P57. Report-Only Footprint And Spectral-Quality Classification

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-15
- Goal: Interpret structural flight-track background and known poor-quality
  wavelength regions correctly in stage QA while retaining every pixel, band,
  and stored value unchanged.
- Scope:
  - Report bounding-box occupancy separately from valid support within the
    observed flight footprint.
  - Label established poor-quality wavelength regions in metrics, per-band
    summaries, checks, and reports without masking, filtering, replacing, or
    rewriting any data.
  - Evaluate unexpected high reflectance on the remaining usable wavelengths,
    while continuing to disclose the all-band result.
  - Do not change correction, convolution, extraction, or pipeline behavior.
- Plan:
  - Add report-only footprint and spectral-quality metrics to stage QA.
  - Add regression tests proving values are retained and classifications are
    explicit.
  - Regenerate the real-flightline QA artifacts and update their interpretation.
- Outcome (2026-08-15):
  - Added schema 1.1 footprint metrics that report bounding-box occupancy
    separately from valid support inside the observed footprint. No spatial
    value is cropped, masked, or rewritten.
  - Added report-only labels for the repository's established poor-quality
    wavelength ranges. Per-band metrics now use `known_bad_retained`, `usable`,
    or `unclassified_retained`; all-band summaries remain visible and no
    wavelength is removed.
  - Real input and corrected products retain all 426 bands, with 68 labeled as
    known bad. The all-band fraction above 1.2 remains 0.0593, while the usable
    358-band fraction is approximately 0.0000142. Within-footprint support is
    1.0 and bounding-box footprint occupancy remains 0.5713.
  - Regenerated the real report bundle. Overall QA is now `WARN`: input and
    correction warn about retained bad bands; convolution and every
    computational/output stage pass.
  - Added byte-preservation and classification regression coverage. The full
    unit-mode suite passes with 213 tests and seven expected skips; combined
    branch-aware coverage is 51.73%.
- Blockers: None.
- Next recommended task:
  - Validate these report-only classifications across the planned multi-site,
    multi-date campaign before changing any scientific mask policy.

### P56. Stage-by-Stage Scientific QA Framework

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Add deterministic, restart-safe, provenance-aware QA after every
  canonical processing stage and assemble a cross-stage report that tests
  physical signal preservation and computational artifacts.
- Repository audit:
  - The current NEON orchestrator has five explicit stage functions: download,
    raw ENVI export, correction-parameter JSON, combined BRDF/topographic
    correction, and sensor convolution; Parquet export, DuckDB merge, and the
    legacy final QA panel occur inside or immediately after convolution.
  - Topographic and BRDF correction are applied sequentially inside one
    canonical file-transform stage, but no topographic-only intermediate is
    persisted. QA must therefore state when separate attribution is not
    evaluable instead of inventing a stage artifact.
  - Existing `qa_plots.py` produces useful final PNG/JSON/PDF diagnostics, and
    `qa_metrics.py` defines a compact metrics schema, but there is no reusable
    stage-report schema, configured threshold classification, explicit
    `NOT EVALUATED`, or combined cross-stage synthesis.
  - `qa_dashboard.py` consumes `_qa_metrics.parquet`, but no producer for that
    documented artifact exists under `src/`; this is a pre-existing output
    contract gap.
  - The repository contains deterministic synthetic software fixtures but no
    checked-in real processed HDF5/ENVI/Parquet dataset. Synthetic reports can
    validate implementation mechanics but must not be presented as scientific
    evidence.
- Architecture plan:
  - Add a modular `spectralbridge.qa` package for schemas, configurable
    provisional thresholds, shared numerical metrics, seam/chunk diagnostics,
    deterministic stage paths, stage runners, plots, and HTML assembly.
  - Preserve existing `_qa.png/.json/.pdf` outputs while adding versioned stage
    JSON/HTML/PNG reports below each canonical flightline directory.
  - Emit standard QA automatically from `process_one_flightline`; expose an
    explicit off/standard/deep mode without changing scientific defaults.
  - Use actual on-disk stage artifacts and deterministic sampling. Record every
    unavailable diagnostic as `NOT EVALUATED` with a reason.
  - Assemble a combined report that compares valid fraction, reflectance
    summaries, correction magnitude, seam scores, and stage statuses, and only
    emits cross-stage findings supported by those metrics.
  - Add tests for deterministic paths/metrics, threshold logic, residuals,
    SRF support, seam/no-seam, chunk invariance, missing ancillary handling,
    report restart safety, and orchestrator integration.
  - Document what each implemented diagnostic means, its provisional threshold,
    how to reproduce it, attribution limitations, and which requested advanced
    diagnostics remain deferred pending real data or translation models.
- Progress (2026-08-14):
  - Added the versioned `spectralbridge.qa` package, automatic per-stage
    emission, combined HTML/JSON reports, provisional thresholds, deterministic
    sampling and fingerprints, spatial/spectral summaries, seam scoring,
    correction deltas, Parquet checks, and reusable SRF, chunk-invariance,
    residual, blocked-group, path, and cycle metrics.
  - Added `--qa-mode`, `spectralbridge-stage-qa`, focused regression tests, and
    the stage-QA documentation/output contract while preserving legacy QA.
  - Added a real-flightline validation page and a compact 3.4 MB bundle of
    stage JSON/HTML/PNG reports plus the legacy QA panel. The 2.4 GB HDF5 and
    approximately 21 GB of intermediate products remain local and unversioned.
  - Attempted the authorized NIWO L019 real-data download. NEON returned HTTP
    403 because its data endpoint now requires authentication. The attempt also
    exposed an invalid `requests.ProxyError` reference; this is fixed and
    protected by tests. Download helpers now read `NEON_API_TOKEN` or
    `NEON_TOKEN` from the environment and explain missing authentication.
  - Ran the user-provided R10C L002 2021-09-15 HDF5 through the complete bounded
    polygon pipeline with deep QA. The process exited normally, wrote 18
    readable Parquet products, and merged 25 rows × 929 columns. Provisional QA
    initially returned `FAIL` for 0.5713 all-array valid support and 0.0593 of
    sampled source values above 1.2; correction magnitude itself passed at
    absolute-difference q99 0.003894. P57 subsequently stratified those metrics
    by flight footprint and established bad-band regions without changing data.
  - The real run exposed and prompted regression fixes for missing reflectance
    scale/no-data ENVI metadata, no-data leakage through Landsat brightness
    adjustment, polygon table discovery, legacy-panel reflectance scaling and
    no-data masking, its fixed count-scale plot axis, and an eager NumPy
    division warning.
  - Verified all 218 collected tests (212 passed, six expected skips) using a
    parallel run with HDF5 file locking disabled for the test process. Current
    branch-aware coverage is 55.95% statements, 38.18% branches, and 51.56%
    combined, above the 45% floor. Ruff, strict
    MkDocs, documentation-link validation, diff whitespace, and generated
    AI-transparency checks pass. The new docs and raw reports were also
    inspected in a browser; the only console error was the temporary local
    server's absent favicon.
- Blockers: None for the implemented framework.
- Deferred diagnostics:
  - Ancillary-aware illumination/geometry residual attribution and a genuine
    alternate-application-chunk rerun remain `NOT EVALUATED`; the canonical
    stage has no topo-only artifact or independent application-chunk control.
  - Exact SRF coverage remains `NOT EVALUATED` until convolved artifacts persist
    the response weights used for each output band.
  - Translation-edge held-out residuals, blocked validation, path/cycle
    consistency, and direct Landsat NBAR comparison require paired observations
    and model artifacts outside a canonical NEON-only processing run.
  - `_qa_metrics.parquet` remains a pre-existing documented producer gap for
    the legacy dashboard and should be handled as a separate output-contract
    task.
- Next recommended task:
  - Run a pinned multi-site, multi-date validation campaign to tune the
    provisional support/extreme/seam thresholds and decide whether valid
    support should be stratified by acquisition footprint or land-only pixels.

### P55. Align Vignette Notebooks With Active Research Notebooks

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Make the runnable vignette notebooks feel familiar to users of the
  active root-level `Raster_processing.ipynb` and `Drone_processing.ipynb`
  notebooks by following their orchestration, output-checking, and narrative
  patterns more closely.
- Scope:
  - Treat the two root notebooks as the style and workflow reference.
  - Preserve existing public pipeline functions, scientific behavior, output
    contracts, dry-run safeguards, and the nine-notebook learning sequence.
  - Change notebook examples and documentation only; do not modify pipeline
    implementation.
- Plan:
  - Compare the root notebooks with every vignette notebook at the cell,
    function-call, configuration, restart, and output-diagnostic levels.
  - Reuse the root notebooks' established orchestration and inspection calls
    where they are appropriate for a focused vignette.
  - Normalize the vignette narrative around setup, editable configuration,
    execution, restart-safe output checks, and interpretation.
  - Add notebook contract coverage and verify clean execution in guarded mode,
    documentation links, and strict site rendering.
- Outcome:
  - Used `Raster_processing.ipynb` and `Drone_processing.ipynb` as direct
    workflow references without modifying either active research notebook.
  - Reworked all nine clean vignette notebooks into a consistent numbered
    sequence: setup or context, editable configuration, run/resume, concrete
    output inspection, and interpretation or next steps.
  - Kept `go_forth_and_multiply` and `run_drone_pipeline` as the public
    orchestrators in the full NEON and drone vignettes, matching the root
    notebooks' lower-case configuration and function-call style.
  - Carried the root notebooks' practical diagnostics into the focused
    vignettes: processed/failed/merged/QA summaries, `pprint`, DuckDB Parquet
    previews, pandas merged-table previews, file inventories, and reusable ENVI
    band/RGB plotting helpers.
  - Retained low-level `stage_*` calls only where a notebook intentionally runs
    one part of the pipeline, and documented how each stage relates to the
    public orchestrator.
  - Removed machine-specific transfer/install commands and saved outputs from
    the reusable versions; every processing cell remains guarded by
    `RUN = False` and no pipeline implementation or scientific behavior
    changed.
  - Updated the notebook catalog and directory README to explain the
    relationship between active research notebooks and portable vignettes.
  - Added contract tests proving that the vignettes continue to mirror the
    root notebooks' orchestrators and diagnostic patterns.
- Verification:
  - All nine notebook JSON/schema, clean-output, compile, and guarded-execution
    contracts passed, including the new root-notebook alignment assertions.
  - Rendered temporary HTML exports of the full NEON and drone notebooks and
    visually verified their headings, cell sequence, code, and explanatory
    text in the browser without executing processing cells.
  - Strict MkDocs build, documentation-link validation, Ruff, AI-transparency
    artifact verification, and repository whitespace checks passed.
- Blockers:
  - None.
- Next recommended task:
  - Have a regular user of the two active root notebooks review the revised
    vignettes and identify any additional exploratory checks worth promoting
    into the portable teaching sequence.

### P54. Route Notebook Links To The Repository Viewer

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Ensure every website notebook link opens the real tracked `.ipynb` in
  the GitHub repository viewer instead of navigating to a static GitHub Pages
  asset that cannot render as a notebook.
- Scope:
  - Keep all nine notebook files, cells, kernels, code, and dry-run safeguards
    unchanged.
  - Update link destinations and explanatory copy only.
- Plan:
  - Inventory every documentation link to a notebook and replace relative
    GitHub Pages asset links with stable GitHub `blob/main` notebook URLs.
  - Clearly state that notebooks can be viewed on GitHub and cloned/downloaded
    for local execution, but are not live browser runtimes.
  - Add link-contract coverage and verify strict docs, links, notebook schema,
    and the rendered GitHub destination.
- Outcome:
  - Kept all nine vignette notebooks as actual tracked `.ipynb` files under
    `docs/vignettes/notebooks/`; no notebook cells, outputs, kernels, or
    scientific code changed.
  - Replaced every website-relative notebook asset link with a GitHub
    `blob/main` link to the corresponding repository file, including the
    module vignettes, notebook catalog, resume guide, and custom-correction
    reference.
  - Clarified that GitHub is the web viewer and that cloning or downloading is
    required to execute or modify a notebook.
  - Added source and browser contracts that require the exact nine notebooks,
    prohibit documentation links back to GitHub Pages notebook assets, and
    verify the rendered catalog exposes nine GitHub repository links.
- Verification:
  - Notebook/example contracts passed.
  - Strict MkDocs build and documentation-link validation passed.
  - Playwright site smoke test passed against the built documentation,
    including the exact `02_correct_neon.ipynb` GitHub destination.
  - Ruff, AI-transparency artifact verification, and repository whitespace
    checks passed.
- Blockers:
  - None.
- Next recommended task:
  - Deploy the documentation changes, then confirm the public notebook catalog
    links to GitHub after the Pages build refreshes.

### P53. Homepage Scientific Visual Story

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Transform the supplied three-panel scientific concept figure into a
  readable, engaging homepage sequence that matches the SpectralBridge visual
  system without embedding one dense poster.
- Scope:
  - Use the supplied figure as the scientific and compositional reference.
  - Derive separate text-free visual assets for sensors, processing, and
    translation; keep scientific labels and explanations as accessible HTML.
  - Preserve the established Drone -> NEON -> Landsat framing, pipeline
    behavior, scientific values, routes, and existing calls to action.
- Plan:
  - Preserve the supplied technical figure without generative simplification;
    do not use the rejected abstract illustration drafts.
  - Present the original figure as three separately enlarged, editorial
    homepage panels so its existing fonts, plots, arrows, and terminology are
    readable while retaining exact scientific content.
  - Integrate the panels with responsive CSS, accessible descriptions, and
    links to the relevant vignettes.
  - Verify asset paths, strict docs, links, browser console, desktop/mobile
    layout, and homepage regression checks.
- Outcome:
  - Preserved the user's supplied 1536 x 1024 technical figure byte-for-byte in
    `docs/images/homepage/spectralbridge-technical-overview.png`; rejected
    abstract image-generation drafts were not added to the repository or used
    by the site.
  - Added an editorial homepage sequence that crops the original figure into
    three separately enlarged views for observing systems, the processing
    chain, and the sensor translation network.
  - Kept every original plot, label, wavelength range, arrow, and scientific
    relationship intact while adding large accessible HTML headings, concise
    interpretation, related-vignette links, figure descriptions, and a
    full-resolution source link.
  - Added a horizontally inspectable mobile viewport so the technical figure
    stays legible instead of being reduced to the width of a phone.
  - Recreated the supplied reproducibility-principles strip as responsive HTML
    so its typography remains readable at every viewport.
  - Made no changes to pipeline code, algorithms, scientific values, routes, or
    runtime outputs.
- Verification:
  - Confirmed the repository asset and supplied source have identical SHA-256
    hashes.
  - Strict MkDocs build and documentation link validation passed.
  - Expanded Playwright documentation test passed, including three panels,
    source links, minimum desktop figure width, mobile internal scrolling,
    page overflow, asset failures, browser errors, and console errors.
  - In-app browser review confirmed the original technical typography is
    readable at desktop width and the page has no horizontal overflow.
  - Ruff and repository whitespace checks passed.
- Blockers:
  - None.
- Next recommended task:
  - Ask the figure author to verify the homepage captions against the intended
    calibration-network interpretation before deploying the site.

### P52. Repair FAQ And Systemic Markdown-In-HTML Rendering

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Repair the FAQ and prevent the same raw-HTML/code-block rendering
  failure across documentation pages using `markdown="1"` containers.
- Scope:
  - Keep page content, navigation routes, pipeline instructions, and runtime
    behavior unchanged.
  - Normalize only the indentation that controls Markdown parsing inside the
    existing HTML layout components.
- Plan:
  - Confirm the FAQ failure in the published site and inventory pages sharing
    the same markup pattern.
  - Normalize affected page markup and extend browser checks to detect raw HTML
    leakage on every repaired route.
  - Verify strict docs, links, desktop/mobile layout, and representative page
    content before completion.
- Outcome:
  - Confirmed the published FAQ rendered its intended hero and cards as a raw
    HTML code block, matching the cloud/HPC tutorial defect.
  - Audited all documentation sources using `markdown="1"` containers and
    normalized Markdown-sensitive indentation on 15 affected routes spanning
    API, concepts, FAQ, pipeline, quickstart, reference, troubleshooting,
    cloud/HPC, CLI, and Parquet pages.
  - Removed the redundant plain Markdown page headings that became visible once
    the styled hero headings rendered correctly; every repaired page now has
    exactly one semantic `<h1>`.
  - Expanded the Playwright smoke test to visit every affected route and reject
    missing hero markup or leaked raw HTML, with dedicated FAQ and cloud/HPC
    card and mobile-overflow checks.
  - Preserved all prose, commands, links, routes, scientific values, pipeline
    code, and runtime behavior.
- Verification:
  - Strict MkDocs build passed.
  - Expanded Playwright documentation test passed across all 15 routes at
    desktop width and the FAQ/cloud pages at 390-pixel mobile width.
  - In-app browser inspection confirmed every repaired route has one hero, one
    `<h1>`, no raw-markup leakage, and no desktop horizontal overflow.
  - Ruff, documentation link validation, and repository whitespace checks
    passed.
- Blockers:
  - None.
- Next recommended task:
  - Deploy the documentation branch and smoke-test the public GitHub Pages URLs
    after the workflow completes.

### P51. Repair Cloud And HPC Tutorial Rendering

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Restore structured rendering on the published cloud/HPC tutorial,
  which currently displays its HTML layout as literal code and text.
- Plan:
  - Compare the published page with its Markdown source and local rendering.
  - Repair the malformed HTML structure without changing tutorial meaning or
    pipeline instructions.
  - Add a regression check for raw-HTML leakage and verify the page visually at
    desktop and mobile widths, then run strict docs and link checks.
- Outcome:
  - Confirmed in the published site that indented content inside
    `markdown="1"` containers was being parsed as code, exposing HTML tags and
    collapsing the intended card layout.
  - Normalized the tutorial's Markdown-in-HTML boundaries so headings, cards,
    lists, links, and both Bash examples render as their intended elements.
  - Added a browser regression check for the hero cards, raw-HTML leakage, and
    mobile horizontal overflow.
  - Made no changes to pipeline instructions, runtime code, APIs, or outputs.
- Verification:
  - Strict MkDocs build passed.
  - Documentation link validation and repository whitespace checks passed.
  - Focused Playwright documentation test passed at desktop and 390-pixel
    mobile viewports.
  - In-app browser inspection confirmed three hero cards, two rendered code
    blocks, no raw-markup leakage, and no desktop horizontal overflow.
- Blockers:
  - None.
- Next recommended task:
  - Audit other pages using indented `markdown="1"` containers for the same
    raw-markup rendering defect.

### P50. Clarify NEON-Mediated Drone-To-Landsat Translation

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Correct the repository's high-level scientific framing so users
  understand that NEON is the airborne intermediary translating between drone
  observations and Landsat-compatible reflectance.
- Scope:
  - Update prominent onboarding and conceptual language.
  - Preserve existing pipeline behavior, APIs, routes, filenames, and
    historical tutorial filenames.
- Plan:
  - Replace direct drone-to-Landsat marketing shorthand with an explicit
    Drone -> NEON -> Landsat relationship.
  - Add a concise explanation of what “translated by NEON” means scientifically.
  - Run documentation links and a strict site build.
- Outcome:
  - Reframed the homepage, README, and start guide around the explicit
    **Drone -> NEON -> Landsat** scientific relationship.
  - Identified NEON airborne hyperspectral observations as the translating
    reference rather than implying a direct drone-to-Landsat conversion.
  - Clarified on the concepts page, drone vignette, and retained MicaSense
    tutorial that the drone and NEON entry points remain separate and that the
    drone workflow does not directly convolve its inputs into Landsat bands.
  - Preserved all pipeline code, APIs, routes, filenames, scientific values,
    and restart behavior.
- Verification:
  - Strict MkDocs build passed.
  - Documentation link validation passed.
  - AI transparency artifacts regenerated and passed their consistency check.
  - Repository diff whitespace check passed.
- Blockers:
  - None.
- Next recommended task:
  - Have a domain scientist confirm that “translating reference” matches the
    intended description of NEON's role in the project methodology.

### P49. New-User Repository Map, Runnable Examples, And Notebook Vignettes

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Make the repository understandable and runnable for scientists across
  local, notebook, container, cloud, and HPC environments without changing the
  working pipeline or its on-disk contracts.
- Scope:
  - Keep all pipeline modules, stage order, scientific assumptions, filenames,
    and restart behavior unchanged.
  - Add a concise start-here map and clearly label runtime code, user examples,
    maintainer tools, validation evidence, legacy material, and data assets.
  - Catalog every active JSON file by authority, consumer, units, edit policy,
    and validation method rather than adding unrecognized metadata to runtime
    JSON schemas.
  - Add documented, container-friendly Python entry scripts and organized
    Jupyter notebooks for the full NEON workflow, local-HDF5/resume workflows,
    individual stages, drone processing, QA, polygon extraction, and a custom
    correction hook between canonical stages.
  - Link notebooks to the existing one-vignette-per-module learning structure.
- Verification plan:
  - Validate every notebook with `nbformat`, compile all notebook code cells,
    and run configuration-only modes for new scripts.
  - Run strict MkDocs, link checks, Ruff, focused docs tests, naming/path tests,
    and existing pipeline regression tests relevant to imported entry points.
- Outcome:
  - Added `START_HERE.md`, a website repository map, and prominent README link
    so new users can choose a full run, local HDF5 run, notebook, drone run,
    validation path, or extension path without traversing the whole repository.
  - Added two self-checking, container-friendly Python runners with
    self-documenting JSON configurations under `examples/`.
  - Added a JSON catalog that distinguishes authoritative packaged parameters,
    example copies, run-generated evidence, validation plans, generated results,
    units, consumers, edit policy, and validation methods.
  - Added a script catalog and labeled three hard-coded root utilities as
    site-specific or historical rather than supported entry points.
  - Added nine clean, ordered notebook vignettes matching the full workflow and
    module pages, including an isolated custom-correction hook after topo/BRDF
    and before convolution.
  - Added notebook links to every module vignette and a `notebooks` optional
    dependency for a reproducible JupyterLab environment.
  - Made no changes to pipeline stage order, algorithms, scientific parameter
    values, filename contracts, or restart behavior.
- Verification:
  - `.venv/bin/python -m pytest -q tests/test_example_entrypoints.py tests/test_paths.py` — 4 passed.
  - `.venv/bin/python -m pytest -q tests/test_polygon_pipeline.py` — 4 passed.
  - Both example scripts pass `--check` without network or imagery access.
  - Official `nbformat` schema validation passes for all nine notebooks; they
    have stable cell IDs, clean kernels/no outputs, compile, and execute their
    `RUN = False` cells with current imports.
  - Strict MkDocs build, documentation link check, and docs Playwright smoke
    test pass; browser review confirmed all nine notebook downloads and the JSON
    and custom-correction pages are visible with no console errors.
  - Ruff and Python compile checks pass for new examples/tests and relabeled
    root utilities.
  - `uv build --out-dir /tmp/spectralbridge-organized-dist` produced a wheel
    and source distribution successfully.
- Blockers:
  - None.
- Next recommended task:
  - Ask one new package user to attempt the `START_HERE.md` check-mode flow and
    one domain scientist to review the custom-correction validation contract.

### P48. Drone Merged-Preview Parquet Fallback Regression

- Priority: User-directed CI failure
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Restore the drone QA merged-Parquet preview behavior when the safe
  reader reaches its pandas fallback without a requested column projection.
- Plan:
  - Reproduce the two focused failures and trace the safe Parquet fallback.
  - Make the pandas call omit the optional `columns` keyword when it is unused.
  - Rerun the focused preview tests, safe-Parquet tests, and full drone pipeline
    test module; run Ruff on the touched files.
- Outcome:
  - Updated `_safe_read_parquet` so its pandas fallback calls
    `pandas.read_parquet(path)` when no column projection was requested, while
    preserving the projected call when columns are supplied.
  - Restored merged-preview row counts, non-NoData row selection, and rightmost
    spectral-column display without changing DuckDB or PyArrow behavior.
- Verification:
  - `.venv/bin/python -m pytest -q tests/test_drone_pipeline.py` — 53 passed.
  - `.venv/bin/python -m pytest -q tests/test_qa_safe_parquet.py` — 1 passed.
  - `uvx ruff check src/spectralbridge/qa_plots.py tests/test_drone_pipeline.py tests/test_qa_safe_parquet.py`
  - `git diff --check`
- Blockers:
  - None.
- Next recommended task:
  - Rerun the repository CI workflow to confirm the Python 3.11 runner matches
    the focused local result.

### P47. Editorial SpectralBridge Website Redesign

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Redesign the MkDocs site to feel like an editorial, science-focused
  creative studio while preserving SpectralBridge's learning, validation, and
  technical-reference information architecture.
- Reference direction:
  - Retain the strong hierarchy, editorial type, generous whitespace, and
    narrative structure inspired by science media sites.
  - Restore the original SpectralBridge logo and derive the palette from its
    navy, sky-blue, teal, green, and spectral yellow colors instead of using
    the reference site's black/yellow identity.
  - Write and design for scientists translating hyperspectral observations
    from drone and airborne sensors into Landsat-compatible reflectance.
  - Do not copy proprietary artwork, text, logos, or page layouts. Keep the
    result recognizably SpectralBridge and accessible as technical
    documentation.
- Plan:
  - Inspect the reference site's visual system and the current MkDocs theme,
    homepage markup, logo assets, and CSS overrides.
  - Establish a logo-derived SpectralBridge color, typography, spacing,
    navigation, card, table, code, and footer system with responsive behavior.
  - Recompose the homepage into an editorial science story with clear routes
    into Learn, Validation, and Technical reference.
  - Apply the design system to content pages without reducing documentation
    readability or changing scientific content.
  - Render and inspect desktop/mobile pages, run accessibility-oriented browser
    checks, and verify strict docs, links, and documentation smoke tests.
- Outcome:
  - Restored the original panoramic SpectralBridge logo on the homepage and
    the original compact spectral bridge mark in the site header.
  - Kept the editorial information hierarchy while replacing the reference
    site's black/yellow identity with a logo-derived navy, sky-blue, teal,
    green, lime, and restrained gold palette.
  - Reframed the homepage for scientists moving hyperspectral reflectance from
    drone and airborne observations into Landsat-compatible products.
  - Propagated the scientific palette through navigation, content heroes,
    cards, tables, admonitions, workflow sections, buttons, and the footer.
  - Confirmed desktop and phone layouts have no page-level horizontal overflow;
    wide validation tables remain independently scrollable on phones.
- Verification:
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/mkdocs build --strict --site-dir /tmp/spectralbridge-site-impact`
  - `python3 scripts/check_docs_links.py`
  - `SPECTRALBRIDGE_DOCS_SITE=http://127.0.0.1:8765 .venv/bin/python -m pytest -q tests/test_docs_playwright.py`
  - `uvx ruff check src tests scripts/generate_ai_transparency.py scripts/generate_validation_docs.py scripts/run_validation_campaign.py`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python scripts/generate_ai_transparency.py --check`
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python scripts/generate_validation_docs.py --check`
  - In-app browser review of the homepage and representative learning,
    validation, and reference pages at 1280×900 and 390×844.
- Blockers:
  - None.
- Next recommended task:
  - Ask a small group of drone and Landsat scientists to perform a short
    findability review of the Learn, Validation, and Technical reference paths.

### P46. Pipeline Validation Matrix And Published Diagnostics

- Priority: User-directed
- Status: In progress
- Owner: Codex
- Started: 2026-08-14
- Goal: Add reproducible validation suites that exercise every user-facing
  pipeline module across varied inputs, record quantitative diagnostics, and
  publish one results page per module in a dedicated website section.
- Plan:
  - Inventory current stage functions, fixtures, tests, and existing QA metrics
    to define explicit validation contracts without changing scientific
    assumptions.
  - Implement a deterministic validation manifest and result schema that record
    input variation, expected behavior, observed diagnostics, status, runtime,
    provenance, and skip reasons.
  - Add an offline validation runner for reliable CI-scale variation testing and
    a separately marked live NEON campaign for opt-in sampling across sites and
    flight lines without making normal tests download hundreds of large files.
  - Generate a validation website index and one page per module from the
    recorded results, including variation lists, pass/fail summaries, and
    diagnostics suitable for improving QA plots.
  - Add contract tests for the runner and generated documentation, then verify
    the smallest relevant suites, documentation build, and links.
- Scope decision:
  - Treat “100 iterations” as a campaign target, not a unit-test default. Live
    download and full-scene processing require network, storage, compute, and a
    pinned NEON product inventory; those runs will be explicit and resumable.
- Progress:
  - Added a versioned validation evidence schema with atomic JSON output,
    explicit checks, diagnostics, runtimes, errors, skip reasons, Git revision,
    and dirty-worktree provenance.
  - Added a deterministic offline runner that can scale to any requested
    iteration count and invokes actual functions for download reuse, synthetic
    HDF5-to-ENVI conversion, topographic correction, BRDF correction, sensor
    convolution, Parquet extraction, CSV conversion, chunked saving, restart
    integrity, and QA rendering.
  - Recorded an initial five-variation-per-module campaign: 40 passed, 0 failed,
    and 0 skipped. The evidence is explicitly labeled as synthetic or
    already-present-input software validation, not external scientific
    validation.
  - Added a top-level Validation website section with an overview and eight
    generated module pages showing every input variation, quantitative
    diagnostics, explicit checks, pass/fail state, QA implications, and
    reproduction commands.
  - Added a live 100-flightline campaign specification that requires exact
    flightline inventory, checksums, dates, and approved network/storage/compute
    resources before execution.
  - Added CI freshness checks, validation framework tests, and rendered-site
    smoke coverage. No scientific QA thresholds were changed from synthetic
    evidence alone.
  - Used the campaign to identify and fix a concrete QA-rendering issue: PDF
    status panels now use font-safe `OK`/`WARN`/`FAIL` labels instead of a
    missing cross-mark glyph, with a regression assertion for that warning.
- Verification:
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python scripts/run_validation_campaign.py --iterations-per-module 5` (40 passed)
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python -m pytest -q tests/test_validation_campaign.py` (3 passed)
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python -m pytest -q tests/test_qa/test_qa_metrics_smoke.py` (3 passed)
  - `.venv/bin/python scripts/generate_validation_docs.py --check`
  - `SPECTRALBRIDGE_DOCS_SITE=http://127.0.0.1:8765 .venv/bin/python -m pytest -q tests/test_docs_playwright.py` (1 passed)
  - `.venv/bin/mkdocs build --strict --site-dir /tmp/spectralbridge-site-validation`
  - `python3 scripts/check_docs_links.py`
  - `uvx ruff check src tests scripts/generate_ai_transparency.py scripts/generate_validation_docs.py scripts/run_validation_campaign.py`
  - `python3 -m compileall -q src tests scripts` and `git diff --check`
  - In-app browser review covered desktop and mobile validation layouts, dense
    table containment, navigation, and console output; no browser errors were
    found.
- Blockers:
  - The repository does not currently contain 100 representative NEON HDF5
    fixtures, and this task has not authorized the bandwidth/storage cost of a
    100-flightline live campaign.
- Next recommended task:
  - Build and pin the 100-flightline NEON inventory, estimate download and
    output storage, choose a durable campaign workspace, and approve the live
    resource budget. Then execute the campaign restart-safely and use its
    distributions to review QA panels and thresholds with scientific oversight.

### P45. Simplify Website Into Educational And Technical Paths

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Make the documentation site less overwhelming by separating
  task-oriented educational vignettes from technical reference material, with
  one canonical vignette per pipeline module plus full-run and restart/resume
  workflows.
- Plan:
  - Inventory existing docs and map each page to an educational vignette,
    technical reference, troubleshooting, or maintainer-only role.
  - Consolidate the visible MkDocs navigation into two primary learning paths
    while preserving useful existing pages and stable file locations.
  - Add a vignette index, one canonical vignette for each user-facing pipeline
    module, a full-pipeline vignette, and a “Carry On My Wayward Son” restart
    vignette for resuming partially completed file-based runs.
  - Cross-link the educational pages to deeper technical descriptions without
    duplicating scientific assumptions.
  - Verify links, strict MkDocs rendering, navigation clarity, and relevant
    documentation tests; then record completion and remaining gaps here.
- Completion notes:
  - Reduced the public site to four top-level destinations: Home, Learn,
    Technical reference, and Project. The homepage now presents the educational
    and technical paths directly instead of exposing the full documentation
    inventory at once.
  - Added a canonical Learn index, a full-pipeline vignette, a “Carry On My
    Wayward Son” restart vignette, and one vignette for each of seven
    user-facing modules: NEON acquisition, correction, sensor harmonization,
    analysis tables, QA, drone processing, and polygon extraction.
  - Added a technical-reference landing page that groups stage/file contracts,
    interfaces, schemas, algorithms, extension points, and architecture.
  - Preserved the older tutorial URLs for incoming links but removed the
    overlapping pages from navigation and search so learners see one canonical
    path per module.
  - Documented the new information-architecture and vignette conventions in the
    documentation style guide and updated the rendered-site smoke contract.
- Verification:
  - `.venv/bin/mkdocs build --strict --site-dir /tmp/spectralbridge-site-webcleanup`
  - `python3 scripts/check_docs_links.py`
  - `SPECTRALBRIDGE_DOCS_SITE=http://127.0.0.1:8765 .venv/bin/python -m pytest -q tests/test_docs_playwright.py` (1 passed)
  - `uvx ruff check tests/test_docs_playwright.py scripts/generate_ai_transparency.py`
  - `.venv/bin/python scripts/generate_ai_transparency.py --check`
  - `python3 -m compileall -q tests scripts` and `git diff --check`
  - In-app browser review covered the homepage, Learn and Technical reference
    navigation, the restart vignette, mobile layout, search results, and browser
    console output; no rendering or console errors were found.
- Blockers:
  - None for this request. MkDocs still reports intentionally unlisted legacy
    and maintainer pages; they remain available for stable links and future
    archival decisions.
- Next recommended task:
  - Have a new user follow the full-pipeline and restart vignettes against a
    small fixture, then refine any steps whose required inputs or expected
    outputs are not obvious without prior SpectralBridge knowledge.

### P44. Publication Readiness, Test Coverage, And AI Transparency Audit

- Priority: User-directed
- Status: Completed
- Owner: Codex
- Started: 2026-08-14
- Goal: Audit publication readiness and test coverage, then add a reproducible
  AI-transparency report generated from the verbatim prompt log with summary
  figures, narrative statistics, and explicit model/provenance limitations.
- Plan:
  - Inventory publication, citation, governance, packaging, release, and
    reproducibility artifacts and record evidence-backed readiness findings.
  - Run the available test suite, coverage measurement, lint, packaging, and
    documentation checks, separating verified results from environment gaps.
  - Define a deterministic prompt-log parser and transparent classification
    rules that do not infer unavailable model metadata.
  - Generate version-controlled text and figure outputs and add automation to
    detect stale AI-transparency artifacts.
  - Add regression tests and documentation for the generator, then rerun the
    smallest relevant checks and the broader verification available locally.
- Completion notes:
  - Added an evidence-backed publication-readiness and test-coverage audit under
    `docs/dev/`, and updated the living publication checklist with verified
    gates and remaining blockers.
  - Added a standard-library prompt-log analyzer that generates a public
    Markdown statement, machine-readable JSON, and four accessible SVG figures
    covering prompt timing, topics, intents, lengths, and recorded AI identity.
  - Added prospective AI system/model fields to the prompt-log contract and
    explicitly preserves unknown historical model identities as `Not recorded`.
  - Added regression tests and a CI staleness check for all generated
    transparency artifacts.
  - Added branch-aware coverage collection and retained JSON/XML CI artifacts,
    with a conservative 45% combined regression floor.
  - Made the CI Ruff baseline explicit (`E4`, `E7`, `E9`, and `F`) and removed
    the one unused import that prevented that baseline from passing.
  - Aligned test extras with the existing pytest `<9` contributor constraint.
- Verification:
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python -m pytest -q tests/test_ai_transparency.py` (3 passed)
  - `MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python -m pytest -q tests/test_duckdb_merge.py` (6 passed)
  - `.venv/bin/python scripts/generate_ai_transparency.py --check`
  - `python3 scripts/check_docs_links.py`
  - `python3 -m compileall -q src tests scripts`
  - `uvx ruff check src tests scripts/generate_ai_transparency.py`
  - `uv run --extra docs mkdocs build --strict --site-dir /tmp/spectralbridge-site-audit`
  - Full unit-mode coverage run: 186 passed, 7 skipped, 2 failed; 49.66%
    statements, 33.43% branches, and 45.56% combined coverage.
  - `uv build` produced the 2.2.0 sdist and wheel; both passed `twine check`.
  - A clean Python 3.12 wheel install imported version 2.2.0, included the
    brightness coefficient JSON, and ran primary CLI help commands.
- Blockers:
  - The publication release remains blocked by two drone-preview test failures,
    metadata/version and DOI inconsistencies, placeholder authorship, and the
    outstanding GPL/third-party provenance review. See the dated audit for the
    complete evidence and recommendations.
  - The strict docs build reports 25 Markdown pages outside MkDocs
    navigation; maintainers should confirm that each exclusion is intentional.
- Next recommended task:
  - Repair and confirm the two drone-preview test contracts in Python 3.10/3.11
    CI, then add a release metadata consistency check before raising coverage in
    the lowest-tested scientific modules.

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
