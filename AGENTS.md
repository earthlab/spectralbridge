# AGENTS.md

This file gives Codex and other coding agents a repo-specific operating manual for `spectralbridge`.

## Mission

SpectralBridge is a scientific Python package for translating reflectance across sensors and scales. The core workflow is a restart-safe, file-based pipeline that processes NEON flight lines into ENVI, corrected ENVI, resampled sensor products, Parquet outputs, merged Parquet tables, and QA artifacts.

Treat this repository like a scientific workflow system, not a generic app:

- Preserve reproducibility and restart safety.
- Prefer extending existing utilities over adding parallel implementations.
- Avoid changing scientific assumptions unless the user explicitly asks.
- Assume on-disk artifacts and filename contracts are part of the public API.

## Sources Of Truth

When deciding how the repo should behave, prioritize these sources:

1. Code under `src/spectralbridge/`
2. Tests under `tests/`
3. Local docs under `docs/`
4. Published docs site: `https://earthlab.github.io/spectralbridge/`

Useful local references:

- `README.md`
- `pyproject.toml`
- `docs/dev/codex-guidelines.md`
- `docs/dev/architecture.md`
- `docs/pipeline.md`
- `docs/naming-conventions.md`
- `tests/README.md`

## Non-Negotiable Guardrails

- Do not invent scientific claims.
- Do not silently alter BRDF, topographic correction, reflectance scaling, brightness coefficients, or spectral response definitions.
- Do not reorganize docs navigation or folder structure unless the user asks.
- Do not delete placeholders, schemas, metadata, or reproducibility files.
- Do not rename core files/functions just for style.
- Keep NEON behavior stable unless the task explicitly targets the NEON pipeline.

## Architecture Snapshot

Key package areas:

- `src/spectralbridge/pipelines/`: orchestration entry points
- `src/spectralbridge/io/`: NEON schema and I/O helpers
- `src/spectralbridge/utils/`: naming, paths, memory, shared helpers
- `src/spectralbridge/data/`: band parameters, brightness coefficients, metadata tables
- `src/spectralbridge/qa_plots.py`, `src/spectralbridge/qa_metrics.py`, `src/spectralbridge/qa_dashboard.py`: QA outputs
- `src/spectralbridge/merge_duckdb.py`: parquet merge stage
- `src/spectralbridge/polygon_extraction.py`, `src/spectralbridge/polygons.py`: polygon workflows

Important invariants from the current code/docs:

- Outputs are the API.
- Stages communicate through files, not shared state.
- Naming/path helpers are authoritative; do not invent filenames ad hoc.
- Pipeline stages are ordered and restart-safe.
- Valid existing outputs should be reused instead of recomputed.

## Workflow Expectations For Agents

`FEATURE_REQUESTS.md` is the authoritative project work queue.

Required execution order for non-trivial work:

1. Read `FEATURE_REQUESTS.md`.
2. Select the highest-priority unfinished item.
3. Update `FEATURE_REQUESTS.md` with the item you are starting, scope, and status before coding.
4. Read the specific code, tests, and docs relevant to that item.
5. Implement the smallest restart-safe change that satisfies the request.
6. Add regression or contract tests before considering the work complete.
7. Update docs when public behavior, contracts, or outputs change.
8. Update `FEATURE_REQUESTS.md` after verification with completion status, blockers, and the next recommended task.

If interrupted, leave `FEATURE_REQUESTS.md` in a resumable state with:

- current status
- remaining work
- blockers
- recommended next task

Before changing code:

- Read the specific module(s) you plan to edit.
- Read nearby tests first if they exist.
- Check whether the behavior is already documented in `docs/` or `README.md`.

When changing code:

- Make the smallest change that satisfies the request.
- Reuse existing helpers and file/path conventions.
- Keep new defaults explicit in code.
- Prefer regression tests, then behavior tests, then contract tests, then integration tests.
- Add or update tests for behavior changes.
- Update docs when user-facing behavior, entry points, outputs, or CLI/API usage changes.
- Preserve chunked processing, deterministic outputs, and restart-safe behavior.
- Favor additive validation and explicit status reporting over implicit behavior changes.

After changing code:

- Run the smallest relevant verification first.
- Prefer targeted test modules over the entire suite when the change is localized.
- If tooling is missing in the environment, say so clearly and list what was not run.
- Record completion, deferred work, blockers, and the next recommended task in `FEATURE_REQUESTS.md`.
- Documentation and governance work should also consider whether `README.md`,
  docs, `CITATION.cff`, release notes, and maintainer-facing checklists need
  updates.

## Testing And Verification

Baseline expectations from repo docs:

- Python 3.10 is the main supported baseline.
- `pytest` is the standard test runner.
- Ruff is expected when available.

Recommended commands:

```bash
pytest
ruff check src tests
```

For focused work, prefer smaller checks like:

```bash
pytest -q tests/test_drone_pipeline.py
pytest -q tests/test_polygon_pipeline.py
pytest -q tests/test_qa/test_qa_metrics_smoke.py
```

If you touch docs only, consider:

```bash
python3 scripts/check_docs_links.py
```

## Docs And Website Rules

This repo has a MkDocs site. In most cases, edit source docs under `docs/`, not generated artifacts under `docs/_build/`.

- Preserve existing page structure and navigation unless asked.
- Keep fenced code blocks intact.
- Respect marker comments like `<!-- FILLME:START -->` / `<!-- FILLME:END -->`.
- When behavior changes, update the nearest relevant doc page instead of scattering the same explanation across many files.

## Open Science Expectations

- Consider reproducibility, software citation, release readiness, and
  long-term maintainability when making changes.
- Keep citation metadata, license references, and release-facing documentation
  aligned with the actual repository state.
- Do not claim a license migration is complete unless repository content and
  provenance support that statement.

## Notebook Rules

There are active notebooks at the repo root, including:

- `Drone_processing.ipynb`
- `Raster_processing.ipynb`

When editing notebooks:

- Do not delete existing cells unless asked.
- Prefer appending new cells over rewriting large existing cells.
- Keep paths repo-relative when the notebook already assumes execution from repo root.
- Mirror existing example data and polygon paths when appropriate.

## Pipeline-Specific Guidance

### NEON pipeline

- The canonical NEON workflow downloads H5 files, exports ENVI, builds correction JSON, applies BRDF/topo correction, resamples to target sensors, exports parquet products, merges outputs, and renders QA.
- Keep canonical NEON naming stable.

### Drone pipeline

- Drone support should remain separate from the NEON download workflow.
- Drone orchestration should use local supported HDF5/TIFF discovery, recurse through subfolders, and preserve provenance from original filenames.
- Drone logic should be wavelength-driven for conceptual band mapping.
- Avoid index-based band assumptions in drone-only code.
- Skip convolution unless a task explicitly introduces it.
- Treat the existing HDF5 and TIFF readers as explicit input contracts. Do not add ad hoc repairs for malformed upstream conversions.
- Protect orientation, ancillary alignment, chunking, checkpointing, per-flight parquet outputs, and QA transparency with focused regression tests.

### Bulk pipeline

- Keep bulk analysis cleanly separated from both individual-flightline pipelines.
- Treat completed-flightline source products as immutable. Normal bulk analysis
  reads them in bounded windows and reduces observations immediately to compact,
  mergeable sufficient statistics. Source paths and source identity remain the
  authoritative backing data and are part of the analytical provenance contract.
- Never reintroduce an ordinary pixel-scale Parquet cache into normal bulk
  analysis. Row-level materialization is allowed only through the explicit
  `build_harmonized_dataset()` workflow.
- Checkpoint compact sufficient statistics per flightline and reuse valid
  checkpoints on restart.
- Translation statistics aggregate hierarchically from chunk to flightline to
  site to global. Preserve stable online/mergeable moment calculations; do not
  replace them casually with naive sums. Reuse additive/subtractive statistics
  for LOSO when mathematically valid.
- Persistent analysis output should scale primarily with flightlines and models,
  not total pixels. Tune parallelism for storage bandwidth as well as CPU and RAM.
- Preserve the full translation evidence chain: pixel-pooled,
  flightline-balanced, site-balanced, per-flightline, per-site, and
  leave-one-site-out fits plus candidate coefficients.
- `summarize_bulk_results()` must operate only on compact completed-run outputs;
  it must not reopen rasters, regenerate statistics, or require the original
  production archive.
- Compare pooled and balanced results. Surface weighting dependence,
  heterogeneity, site dependence, transferability failures, weak fits, and
  large corrections explicitly. High R² alone does not establish sensor
  interchangeability. Configured review thresholds are decision aids, not
  universal scientific approval criteria.
- Spectral-library reporting reads the supplied library in place. Keep
  preflight cheap, use compact summaries by default, and require explicit
  choices for potentially expensive full trace reports. The merged polygon
  Parquet is an intentional scientific dataset and must not be copied for
  computational convenience.
- Keep visualization validity separate from regression validity. Finite negative
  corrected reflectance is not automatically nodata. Low-alpha ensembles are
  qualitative density-like views, not normalized probability densities. Rasterize
  very large trace layers while retaining readable annotations where practical.
  Robust plot bounds must never alter analytical summaries, and bounded extreme
  spectra must remain traceable to source records.
- Separate descriptive diagnostics from empirical calibration claims. Synthetic
  MicaSense/Landsat convolution comparisons derived from the same corrected
  reference are diagnostic relationships unless independent empirical
  observations are explicitly supplied; do not present them as universal sensor
  calibration.
- Production observations such as row counts, fitted slopes, R² values, or
  correction magnitudes are evidence, not package constants. Calculate metrics
  from supplied tables and use synthetic fixtures in tests.
- Changes to pixel-scale code must evaluate memory and disk scaling, filesystem
  reads, source-data passes, restartability, progress, and large-VM behavior.
  Long-running work must expose meaningful flightline/chunk/stage progress
  without creating giant state files; a pipeline that can run silently for hours
  is not production-ready.

### Release engineering

- Keep the release identities distinct: the PyPI distribution is
  `earthlab-spectralbridge`, the Python import package is `spectralbridge`, the
  scientific/software name is SpectralBridge, and the repository is
  `earthlab/spectralbridge`. Do not infer that changing one renames the others.
- Keep `pyproject.toml`, `spectralbridge.__version__`, `CITATION.cff`, the first
  changelog heading, and the release tag synchronized.
- Release tags use `vMAJOR.MINOR.PATCH` or strict PEP 440 prerelease suffixes
  such as `v2.3.0rc1`; do not use hyphenated RC tags.
- Build the wheel and sdist once. Test those exact bytes and publish the same
  artifacts; never rebuild between validation and publication.
- Validate wheels on Python 3.10, 3.11, and 3.12 and the sdist on Python 3.10.
- The installed-artifact smoke must run outside the source checkout and cover
  normal, drone, bulk, compact results, spectral-library, public API, console
  script, and packaged-data wiring without network access.
- PyPI publication uses trusted publishing through the protected `pypi` GitHub
  environment. Do not store an API token in repository secrets.
- Prerelease tags must create GitHub prereleases and publish a prerelease version
  to PyPI only after every source, documentation, build, metadata, and exact
  artifact gate passes.

## Naming And Path Conventions

- Use existing naming/path helpers whenever possible.
- For NEON workflows, filenames are tightly coupled to downstream expectations and docs.
- For drone workflows, preserve drone-native provenance and avoid introducing NEON-style names unless explicitly requested.
- If a naming change is unavoidable, update tests and docs in the same task.

## Prompt Logging Requirement

Future Codex runs in this repo should maintain a verbatim prompt log.

Default behavior:

- Append each new user prompt verbatim to `PROMPT_LOG.md` before making substantive edits.
- Include the date, branch name if known, and a short task label.
- Include `AI system` and `Model` metadata when those values are exposed by the
  execution environment. Use `Not recorded` rather than inferring an unknown
  model name.
- Preserve the exact user wording inside a fenced code block.
- Do not paraphrase the prompt in the log.
- After changing the prompt log, run
  `python scripts/generate_ai_transparency.py` and include the regenerated
  statement, JSON summary, and figures with the same change. CI rejects stale
  generated artifacts.

Suggested entry format:

````md
## 2026-03-21 - task label
Branch: main
AI system: OpenAI Codex
Model: Not recorded

```text
<verbatim user prompt>
```
````

Exceptions:

- If the user explicitly asks not to log prompts, do not log them.
- If the prompt contains obvious secrets or credentials, pause and ask before storing it verbatim.

## Safe Defaults For Agents

- Prefer surgical edits.
- Prefer local docs and tests over memory.
- Prefer repo-relative paths in examples.
- Keep changes scientifically conservative.
- Call out uncertainties instead of guessing.
- Protect intentionally public APIs such as `spectralbridge.go_forth_and_multiply`,
  `spectralbridge.process_one_flightline`, `spectralbridge.run_drone_pipeline`,
  `spectralbridge.run_bulk_pipeline`, `spectralbridge.summarize_bulk_results`,
  `spectralbridge.run_spectral_library_analysis`,
  `spectralbridge.inspect_spectral_library_preflight`, and
  `spectralbridge.build_harmonized_dataset`.
- Leave known issues visible: fix them or add/update a feature request instead of letting them disappear.

## Good First Files To Read For Most Tasks

- `README.md`
- `pyproject.toml`
- `docs/dev/codex-guidelines.md`
- `docs/dev/architecture.md`
- the specific module being edited
- the nearest matching test file in `tests/`

## If You Are Unsure

- Check the tests.
- Check the docs page nearest to the feature.
- Preserve existing behavior and extend rather than rewrite.
- Leave a short note in your final response describing any assumptions you made.
