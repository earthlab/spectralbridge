# Release Hygiene Review

Review date: 2026-06-03

This note records the release-hygiene audit performed during package hardening.
It focuses on what is likely to ship in source distributions and on obvious
repository artifacts that should not be treated as release payload.

## Reviewed files

- `pyproject.toml`
- `MANIFEST.in`
- `README.md`
- `LICENSE`
- `CITATION.cff`
- top-level repository artifacts and generated files visible in the working tree

## Low-risk fixes applied

`MANIFEST.in` was tightened to avoid shipping maintainer-only and accidental
artifacts in source releases.

Changes made:

- removed explicit inclusion of:
  - `AGENTS.md`
  - `FEATURE_REQUESTS.md`
  - `publication_checklist.md`
- added explicit excludes for:
  - `PROMPT_LOG.md`
  - `Drone_processing.ipynb`
  - `Raster_processing.ipynb`
  - `:memory:`
  - `ty_tuff_contributions_last_year.md`
- added pruning for:
  - `Datasets/`
  - `vendor/`
- added a global exclude for:
  - `__pycache__/`
  - `*.pyc`, `*.pyo`, `*.pyd`

## Findings

### 1. Prompt log was a real packaging risk

`PROMPT_LOG.md` exists at repo root and contains verbatim development prompts.
Without an explicit manifest exclusion, it is the kind of maintainer artifact
that can accidentally end up in an sdist.

### 2. Repo-root notebooks are publication/support assets, not package payload

The root notebooks are useful working materials, but they are not required for
package installation or runtime and should not ship unintentionally in a source
release.

### 3. Large local/support assets exist in the repo tree

Examples observed during the audit:

- `Datasets/` with geopackages and spreadsheets
- `gocmd`
- `:memory:`
- `ty_tuff_contributions_last_year.md`

The manifest now excludes or prunes the obvious packaging risks, but these
files remain repo-hygiene concerns worth keeping visible.

### 4. Core metadata files are present and aligned at a high level

The repository currently includes:

- `LICENSE`
- `README.md`
- `CITATION.cff`
- `pyproject.toml`

No contradictory packaging metadata issue was identified in this pass beyond
the previously documented license/provenance concerns.

## Verification limits

This environment does not currently have `setuptools` or `build` available in
the active Python interpreter, so a local source-distribution build/listing
could not be executed during this audit.

## Recommendation

Before a release cut, run an actual build in a packaging-capable environment
and inspect the resulting sdist contents directly. This audit reduces risk, but
the final packaging check should use the real build artifact.
