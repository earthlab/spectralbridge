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
- Drone orchestration should use local H5 discovery, recurse through subfolders, and preserve provenance from original H5 filenames.
- Drone logic should be wavelength-driven for conceptual band mapping.
- Avoid index-based band assumptions in drone-only code.
- Skip convolution unless a task explicitly introduces it.
- Treat HDF5 as the input contract. Do not add TIFF conversion logic or repairs for malformed upstream TIFF-to-HDF5 conversions.
- Protect orientation, ancillary alignment, chunking, checkpointing, per-flight parquet outputs, and QA transparency with focused regression tests.

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
- Preserve the exact user wording inside a fenced code block.
- Do not paraphrase the prompt in the log.

Suggested entry format:

````md
## 2026-03-21 - task label
Branch: main

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
- Protect intentionally public APIs such as `spectralbridge.go_forth_and_multiply`, `spectralbridge.process_one_flightline`, and `spectralbridge.run_drone_pipeline`.
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
