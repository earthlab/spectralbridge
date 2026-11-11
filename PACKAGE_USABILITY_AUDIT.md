# SpectralBridge core functionality and user experience audit

Date: 2026-11-04. Target: 2.3.0rc2. Audited baseline: clean `main` at
`bb3da46bea0a4295ca3152a9f607ed17140575f1`, identifying itself as **2.3.0rc1**.
This audit changes the working tree; it does not publish, tag, merge or certify RC2.
Earlier uncommitted RC2 changes were not present in this checkout and were not
assumed to be available.

## Executive summary

**A new researcher can install the source and obtain a useful offline result.
The principal small-data workflows execute, but this checkout is not ready to
be called a fully validated RC2 release.** Installation, examples, help, navigation
and output interpretation were improved directly. Remaining regression-gate
failures are recorded rather than hidden behind successful demonstrations.

Three strongest features:

1. Separate NEON, drone and bulk orchestration, with reusable stage products and
   tested restart behavior.
2. Extensive provenance, explicit correction/calibration acceptance and compact
   bulk statistics without an ordinary pixel cache.
3. Source-derived API reference, offline numerical lessons and documented
   distinctions between execution, numerical support and scientific validity.

Three most important problems found:

1. A valid scientific metadata record could become unreadable during sensor
   resampling, stopping subsequent library export. **Fixed and regression-tested.**
2. The beginner path obscured downstream translation, polygon-library creation
   and numerical analysis; examples disappeared into temporary directories and
   runner errors exposed tracebacks for routine configuration mistakes.
   **Improved with tested existing entry points, persistent output and clearer errors.**
3. The broad regression gate already had failing fixtures/import-isolation
   contracts, and current dependency installations exposed additional compatibility
   checks. **The audit identifies the remaining gate as a release blocker;
   successful example execution does not close it.**

## Core capability inventory

SpectralBridge prepares, corrects, represents and compares spectral observations
across sensors and scales. Six researcher capabilities are served by three
pipelines plus downstream modules, not six competing processing frameworks.
The [user-facing capability map](docs/vignettes/index.md#capability-map) records
inputs, outputs, Python/CLI entry points, examples and support limits.

| Capability / primary user | Inputs → outputs | Entry point / guide | Support |
| --- | --- | --- | --- |
| NEON / airborne researcher | Directional-reflectance H5, acquisition identifiers and geometry → corrected ENVI, target-sensor products, optional tables and QA | `spectralbridge.go_forth_and_multiply`, `process_one_flightline`; `spectralbridge-pipeline`; [guide](docs/vignettes/full-pipeline.md) | Core supported workflow; downloads need credentials and adequate storage |
| Drone / UAS researcher | Supported TIFF/H5, authoritative radiometry and aligned ancillary data → native/corrected ENVI, optional translated products, tables and QA | `spectralbridge.run_drone_pipeline`; JSON runner; [guide](docs/vignettes/drone-processing.md) | Core orchestration; camera-contributor reconstruction remains explicit experimental work |
| Translation / cross-sensor researcher | Corrected NEON + response definitions, or corrected drone + reviewed coefficients → separately named target-band rasters | Existing producer orchestration; [sensor guide](docs/vignettes/sensor-harmonization.md) and [drone guide](docs/vignettes/drone-processing.md) | Convolution and affine translation are different supported operations; neither alone establishes empirical calibration |
| Library creation / field collaborator | Completed imagery/products + overlapping polygons and researcher attributes → pixel index and labeled spectral Parquet | `spectralbridge.polygons.run_polygon_pipeline_for_flightline`; [polygon guide](docs/vignettes/polygon-extraction.md) | Core extraction; researcher-supplied identities/labels and spatial validity remain necessary |
| Library inspection and analysis / ecologist | Spectral table or common-unit arrays, labels and independent identities → summaries, difference/recognition metrics and mixture diagnostics | `inspect_spectral_library_preflight`, `run_spectral_library_analysis`; explicit `spectralbridge.library_analysis` imports; [maturity guide](docs/api/scientific-analysis.md) | Core reporting and documented numerical contracts; operational abundance mapping remains experimental |
| Bulk / collection manager | Completed immutable flightlines → pooled, balanced, per-site and held-out statistics and compact reports | `run_bulk_pipeline`, `summarize_bulk_results`; `spectralbridge-bulk`; [guide](docs/vignettes/bulk-analysis.md) | Core; ordinary analysis does not materialize the entire observation population |

Internal stage helpers, compatibility aliases, release smoke tools and historical
research runners are not additional beginner APIs. No public function was renamed,
no duplicate high-level API was introduced and no new dependency was added.

## User journey assessment

| Journey | Before | Implemented result / evidence |
| --- | --- | --- |
| Discovery | README emphasized three pipelines; downstream tasks were less visible | Six-task route table, direct workflow map, home-page “Run your first example” action |
| Installation | Virtual environment was recommended without complete commands; old publication-status wording distracted from the tested source path | Explicit clone/venv/activation/install commands, distribution/import distinction, optional-extra table and version troubleshooting |
| First result | Preflight lesson worked but temporary data vanished | Existing offline scientific lesson now accepts `--output-dir NEW_DIR`, retains source table, compact library/plant summaries and explained JSON; refuses overwrite |
| Workflow selection | Analysis lived deep in reference; polygon extraction mainly appeared as a module | Translation, polygon creation and analysis are visible in the primary workflow navigation; detailed research history retained |
| Configuration | Missing/malformed JSON produced a stack trace; drone runner rejected existing calibration/timezone API arguments | Actionable file/key errors with exit code 2; established radiometry/timezone options pass through unchanged |
| Result interpretation | Many intermediate files; a corrected filename could be mistaken for applied correction | “Open these results first” table points to existing manifests, QA and returned compact paths; applied flags and scientific support explained |

A second **clean standard-venv/pip editable install** followed the documented
installation path, and both basic offline lessons ran successfully with no broken
requirements. An independent clean **non-editable** installation exercised bounded
producer/bulk/library workflows outside the source import tree. Optional analysis
and documentation extras were also installed and exercised. These checks cover
Python 3.12 on this Mac, not the release's complete Python/OS matrix.

### Walkthrough costs and decisions

Counts below are researcher actions after installation, not internal pipeline
stages or promises that real data need no preparation.

| Workflow | Actions / decisions | Dependencies and common failure points | Execution evidence / output discovery |
| --- | --- | --- | --- |
| NEON | 4: choose acquisition, configure storage/workers/corrections, run, review | Token for remote acquisition; exact IDs, disk space and valid geometry | Tiny installed H5 traversed correction, seven target sensors, tables and QA; restart reused core products. Per-flight QA/header paths documented |
| Drone | 4: establish calibration/ancillary evidence, configure, run, review | Local supported schema; physical units, CRS/affine and angular support. Remote HDF5 campaigns separately need GoCommands | Two tiny installed flights exercised topo+BRDF, affine translation, full and polygon extraction, QA. Console now separates processed/blocked/failed |
| Translation | 3: choose response/registry, run producer stage, inspect target headers/provenance | Wavelength coverage, reviewed coefficient equation/units; actual-sensor comparison requires independent data | NEON convolution and drone affine branches exercised through production code, not substituted teaching calculations |
| Libraries | 4: establish polygon/grid/labels, extract, inspect preflight, report | Valid geometry, identities, compatible wavelength schema and accepted source provenance | Polygon extraction plus standalone four-row compact library reporting executed; source table read in place. Standalone recipe no longer requires a bulk-raster example |
| Scientific analysis | 3: choose common-support arrays/identities, select method/budget, interpret | `analytics` extra; group leakage, small independent samples, unverified ecological interpretation | Existing offline lesson executed separability, nested recognition, feature budgets, mixtures/FCLS/MESMA/ridge diagnostics. Outputs remain explicitly synthetic |
| Bulk | 4: choose completed sources, preflight, analyze, summarize | Completed source contract, output outside source tree, population weighting and storage bandwidth | Three-flightline/12-row installed fixture exercised streaming statistics, LOSO, results and restart; no ordinary pixel cache |

Measured fixture times, output bytes and exact stage checks are in
[`workflow_smoke.json`](provenance/package-usability-audit/2026-11-04/workflow_smoke.json).
They are small-fixture software timings, **not production runtime estimates**.
Worker budget was one, Parquet chunks eight rows, network connections blocked
inside the installed smoke and output budget 128 MiB. Peak RAM was not measured.
No large NEON download, new drone correction campaign, disk-full simulation or
independent field validation was claimed by this audit.

## API and CLI findings

The source inventory and public import/signature tests were reviewed alongside
major call signatures. Existing package exports provide the right orchestration;
`go_forth_and_multiply` is a discoverability problem best handled by the task map,
not a breaking rename. NEON exposes file products; drone/bulk expose structured
results plus files. Documentation now explains that difference.

The standalone library reporter accepts a DuckDB connection and
`BulkAnalysisPaths`; this is more setup than a beginner expects. A tested recipe
and offline lesson demonstrate that existing API without creating a second
reporting system. A future convenience interface needs a compatibility proposal.

All **17 declared console scripts** (11 current names, six compatibility aliases)
and the remote command's three subcommand help pages were executed. Primary
NEON/bulk/remote help now includes a starting example, prerequisites, output and
restart guidance plus the guide link. The CLI page distinguishes primary and
supporting tools. Local drone processing uses the existing Python/JSON runner;
remote production currently inventories supported HDF5 packages, not an automatic
original-TIFF/camera reconstruction service. There is no standalone library CLI;
its existing Python route is documented explicitly.

Routine malformed/missing JSON now produces an actionable parser error without a
traceback. Scientifically incomplete drone results exit nonzero even when callers
set `raise_on_incomplete=False`; the wrapper also reports the audit attached to
`DronePipelineIncompleteError`. Unexpected programming failures and substantive
scientific diagnostics are not silently swallowed.

## Documentation and output findings

The site already separated workflows, reference, methods and development; a
wholesale redesign was unnecessary. Three direct workflow links and a task map
make the principal capabilities easier to find. Historical reports remain intact.

The original strict build failed on retained links that existed in the repository
but were outside the generated site. **128 links in eight pages** now point to
those same GitHub source artifacts; no evidence was moved or deleted. Regenerated
API inventory also exposes the existing experimental geometry/topography modules
without promoting their scientific status. Strict MkDocs and all **393 rendered
API signatures** pass. Desktop/mobile beginner previews have no page-wide overflow.

Existing `drone_qa_summary.json`, flight QA, bulk manifest and compact report paths
remain authoritative; no redundant manifest was added. The output guide separates
raw, identity-copy, corrected, translated and actual satellite observations. Source
and model provenance are still required when interpreting a completed run.

The public website was inspected as well as local source; its retrieved snapshot
had older navigation. The changed pages and screenshots here are a **local build**,
not a claim that these revisions have been deployed.

## Changes implemented

- Complete beginner setup, optional dependency guidance, six-capability navigation,
  standalone library recipe and practical output/status troubleshooting.
- Persistent offline lesson using existing public functions; no overwrite of an
  existing destination, no credentials and no source population copy.
- Existing drone JSON runner accepts radiometry/timezone controls, reports blocks
  and incomplete status accurately, and handles expected config errors clearly.
- Major CLI help starts with a usable route instead of only an option inventory.
- Fixed scalar `json:` metadata preservation through ENVI sensor resampling;
  physical-library acceptance now reads the original contract successfully.
- Fixed observed topographic bands being erased when another band is missing.
  Existing equations/acceptance remain unchanged; per-band sentinels stay missing.
  Regression tests compare observed-band results exactly with fully observed inputs.
- Updated a single-row DuckDB relation diagnostic to consume its result using the
  supported relation API. Existing query tests retain their expected values across
  current DuckDB installations.
- Added a guarded result-summary cell to the active drone notebook; preserved all
  existing cells. Updated the browser assertion for the deliberately improved CTA.

### Before and after

| Before | After, using actual existing entry points |
| --- | --- |
| Temporary lesson prints a result that cannot be reopened | `python examples/scientific_workflows_offline.py --output-dir lesson_output`; open `example_summary.json` and the compact output paths it records |
| Calibration passed in drone JSON is rejected as an unknown key | Existing `pipeline.radiometry` and timezone arguments are accepted; scientific validation still decides eligibility |
| Missing configuration produces a stack trace | `--config missing.json --check` names the file and template, explains the error and exits 2 |
| A non-raising incomplete drone result may exit successfully | Summary prints `Blocked`, `Failed`, `Status` and QA path; incomplete exits 1 |
| A correctly serialized calibration fails after convolution | Scalar contract survives header round trip and the installed producer-to-library chain completes |
| Corrected filename appears to prove a correction | Output guide directs users to applied flags, radiometry and scientific support before use |

## New camera-table availability

The user's continuation supplied the Data Store collection
`/iplant/home/shared/earthlab/macrosystems/field-data/output/summer-2023` and the
`*-camera-locations.csv` convention. All five AOP tables were discovered and
checksum-verified read-only. The files have explicit CRS/count preamble rows and
a `# PhotoID` header; blindly treating their first row as the column header is
incorrect. Format-specific inspection preserves the source bytes.

| Package | Data rows | Distinct XYZ positions | Declared EPSG |
| --- | ---: | ---: | ---: |
| Goldhill | 5,650 | 565 | 5070 |
| Gordon | 5,720 | 572 | 26913 |
| MRS1 | 4,500 | 450 | 26913 |
| MRS2 | 4,330 | 433 | 26913 |
| Ruby | 5,070 | 507 | 26913 |

Rows are photo/band records, not independent ground observations. Photo IDs are
unique and numeric values are finite; orientation matrices and historical
footprint comparisons are recorded in
[`camera_table_validation.json`](provenance/package-usability-audit/2026-11-04/camera_table_validation.json).
Goldhill still declares EPSG:5070 while its XY values match the earlier UTM zone
13N interpretation; no automatic relabeling or source overwrite was performed.
These tables do not include timestamps, establish applied physical reflectance
calibration, identify actual orthomosaic contributors or certify clock/vertical
conventions. Their arrival removes the **missing-file** limitation, not every
scientific dependency. No full reprocessing/upload was initiated as part of the
usability audit.

Naming dates differ (`8-14-2023` versus folder `08-14-23`) and Ruby capitalization
varies. A future production association must normalize identity/date deliberately;
literal basename-prefix equality is not a sufficient contract. The input discovery
recommendation below now refers to these supplied files rather than asking the
user to provide them again.

## Verification and remaining recommendations

<!-- AUDIT:FINAL_CHECKS -->
- Clean standard-venv/pip source installation and offline lessons: **passed**; dependency check: **no broken requirements**.
- Installed stage-complete synthetic NEON, drone/full/polygon/translation, bulk/restart and library checks: **passed**; six changed runtime-module hashes exactly match the tested non-editable installation.
- Final focused regression set: **48 passed**. An additional overlapping API/numerical/producer set had **92 passed**; these counts are not additive unique coverage.
- Browser checks: **2 passed**; four desktop/mobile reader captures inspected, no page-wide overflow.
- All **17 CLI help interfaces**, three remote subcommand help pages and four beginner/configuration entry points: **24 successful runs**.
- Strict docs, **393 rendered API signatures**, repository link checks, API freshness, Ruff and generated transparency: **passed**.
- Broad final source gate: **935 passed, 9 failed, 11 skipped, 0 errors**. This is deliberately **not** reported as a green suite. Failures and exact test names are retained in [final_checks.json](provenance/package-usability-audit/2026-11-04/final_checks.json) and the source JUnit/log evidence.

The broad source run is reported separately from focused passing checks. The
remaining failures predate these usability changes and involve bulk-readiness
fixtures, a stale checkpoint-version expectation, historical `common` import
isolation, polygon mock/header setup, QA calibration fixtures and the offline
validation campaign. They must be reconciled with current contracts; acceptance
checks must not be weakened merely to turn the suite green.

| Priority | Remaining recommendation | Release consequence |
| --- | --- | --- |
| **P0** | Reconcile the recorded broad regression/validation failures, including fixture provenance and import isolation, and rerun the full source gate | This audit does not declare RC2 ready while the gate remains red. Passing tiny examples is insufficient |
| **P1** | Integrate explicit camera-table association/validation with supported original-package intake; handle the Metashape preamble/date variants and resolve Goldhill CRS from authoritative evidence | Current remote CLI must not advertise automatic original TIFF/camera reconstruction; newly provided files are recorded and available |
| **P1** | Align release identity and exact-artifact checks when preparing RC2; this checkout still identifies as rc1 | No rc2 publication/version claim; rerun Python 3.10–3.12 artifact gates for the final candidate |
| **P1** | Keep scientific support visible in source-only/no-correction QA and explain generic reflectance labels for unsupported stored units | Identity copies must not be mistaken for successful physical correction; current documentation calls this out |
| **P2** | Propose, rather than silently introduce, a simpler standalone library-report convenience interface | Existing tested recipe works; preserve the current API |
| **P2** | Measure production RAM/disk/time on representative input sizes and extend clean-platform installation coverage | Tiny synthetic timing is not a production capacity estimate |
| **P2** | Continue reducing advanced option overload through staged examples and keep published docs synchronized with the selected release | No CLI hierarchy migration or deletion of historical evidence is needed for this audit |

Physical calibration and inferred contributors remain scientific limitations,
not automatically software-release defects. General operational abundance mapping
was not promoted to a stable feature. No license, citation authorship, kernel,
spectral response, fitted coefficient or default correction request was changed.

Evidence and reproducible audit scripts:
[`provenance/package-usability-audit/2026-11-04/`](provenance/package-usability-audit/2026-11-04/).
Large temporary environments and synthetic products are under
`/private/tmp/spectralbridge-usability-20261104/` and
`/private/tmp/spectralbridge-usability-pip-20261104/`, not committed datasets.
