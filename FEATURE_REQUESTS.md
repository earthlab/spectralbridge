# SpectralBridge Feature Requests

Review date: 2026-06-02  
Branch: main

This document tracks publication-readiness issues found during repository
cleanup review. Items here were not changed automatically because they may
affect packaging, public documentation structure, reproducibility, or existing
workflows.

## Completed During This Review

- Confirmed `AGENTS.md` exists.
- Appended the user request to `PROMPT_LOG.md`.
- Added ignore rules for common OS, notebook, cache, and Python bytecode files.
- Updated README/Quickstart wording so Ray is documented as required and default.
- Repaired several broken Markdown tutorials and removed unsupported CLI flags
  from active examples.
- Updated notebook examples to use `go_forth_and_multiply(..., flight_lines=...)`.
- Updated `docs/naming-conventions.md` to match current NEON/drone output names.
- Preserved Parquet as the authoritative tabular output in docs.
- Removed the accidental unrelated PRISM helper package and notebook artifacts.
- Clarified Ray language in dependency errors and Ray engine tests.
- Added a public-function import/signature smoke matrix.
- Added Playwright browser smoke tests for the built MkDocs site and wired them
  into the docs workflow.

## Requests To Review

### FR-001: Archive or untrack generated OS/Python artifacts

**Finding:** `.DS_Store` and Python `__pycache__/*.pyc` files are tracked in the
repository, including under `src/spectralbridge/`, `tests/`, and `deprecated/`.

**Why it matters:** These are generated local artifacts, add noise to reviews,
and can confuse publication packaging.

**Decision needed:** Move tracked generated artifacts into a dated folder under
`deprecated/` or remove them from the active tree after confirming they have no
reproducibility value.

### FR-002: Decide how to handle large deprecated data artifacts

**Finding:** `deprecated/notebooks/megan_unmixing/data/` contains very large
Landsat TIFs and shapefile components. The root also tracks a `gocmd` binary.

**Why it matters:** The repository is heavy for publication and source
distribution. The files may be valuable provenance, but they are not active
pipeline code.

**Decision needed:** Keep as-is, move to external archive, use Git LFS, or keep
only metadata/pointers in the repository. Do not delete without an archival plan.

### FR-003: Define package/source distribution contents

**Finding:** `pyproject.toml` uses package discovery under `src/`, while the repo
also contains root data, notebooks, generated docs reports, deprecated assets,
and vendored MkDocs plugins.

**Why it matters:** Wheel and source distribution contents should be intentional
before publication.

**Decision needed:** Add or verify distribution rules, such as `MANIFEST.in` or
setuptools exclude settings, after deciding which non-code artifacts should ship.

### FR-004: Triage root scripts

**Finding:** Root-level scripts such as `move_folders_from_instance_to_remote.py`,
`remote_to_instance.py`, and `patch_script_toworkfromcorrectedfiles.py` appear
workflow-specific.

**Why it matters:** These may distract publication reviewers or unintentionally
ship as part of SpectralBridge.

**Decision needed:** Confirm whether each item is active, should move under
`tools/`, or should move to `deprecated/`.

### FR-005: Finish documentation source-of-truth cleanup

**Finding:** Several root-level docs still contain `FILLME` markers or older
workflow language (`docs/configuration.md`, `docs/stage-03-pixel-extraction.md`,
`docs/validation.md`, `docs/extending.md`, and related pages). Some are not in
the MkDocs nav, while similar pages under `docs/reference/`, `docs/pipeline/`,
and `docs/usage/` are closer to current behavior.

**Why it matters:** Verbose documentation is useful, but duplicate stale pages
make it hard to know which page is authoritative.

**Decision needed:** For each stale root doc, decide whether to rewrite, move to
`deprecated/docs/`, or keep as a historical note with an explicit banner.

### FR-006: Align docs link/marker tooling with the actual docs policy

**Finding:** `scripts/check_docs_links.py` scans only top-level `docs/*.md` and
fails on `FILLME`, while the repo instructions say to respect marker comments.
The MkDocs nav uses many nested pages that the script does not scan.

**Why it matters:** The docs verification tool can fail for intentional markers
and miss broken links in active nested docs.

**Decision needed:** Update the checker to follow MkDocs nav/nested docs and
either allow marker comments or require a marker-free publication pass.

### FR-007: Replace README QA placeholder with a real artifact

**Finding:** `README.md` still contains a "QA panel example coming soon" note.

**Why it matters:** The README is the human-facing entry point and should show a
real QA artifact before publication.

**Decision needed:** Add a representative QA PNG or move the example to docs if
the README should stay lightweight.

### FR-008: Rewrite or relocate the MicaSense tutorial

**Finding:** `docs/tutorials/micasense-to-landsat.md` previously documented a
nonexistent `spectralbridge-micasense-to-landsat` CLI. It is now marked as a
pending runnable tutorial refresh.

**Why it matters:** A public tutorial should either be runnable or clearly
conceptual.

**Decision needed:** Rewrite around `run_drone_pipeline`, make it a conceptual
page, or move it out of public tutorial navigation.

### FR-009: Fix stale reference examples

**Finding:** `docs/reference/extending.md` references
`spectralbridge.convolution.registry`, which does not exist. `docs/validation.md`
still uses CSV-first examples unrelated to the current Parquet-centered pipeline.

**Why it matters:** Reference pages should be more exact than tutorials.

**Decision needed:** Update these pages against current code or move them to
`deprecated/docs/` until the described APIs exist.

### FR-011: Decide whether to export orchestration helpers at top level

**Finding:** Some docs previously used `from spectralbridge import
go_forth_and_multiply`, but `spectralbridge.__init__` does not export that name.
Docs now import from `spectralbridge.pipelines.pipeline`.

**Why it matters:** A top-level import may be friendlier, but adding it changes
the public API surface.

**Decision needed:** Keep explicit module imports or intentionally add top-level
exports for common orchestration helpers.

### FR-012: Review generated docs drift reports

**Finding:** `docs/_build/doc_drift_report.*` is tracked and contains stale
sensor-drift output. The drift tool regenerates these files.

**Why it matters:** Generated reports can either be useful audit artifacts or
stale noise in publication diffs.

**Decision needed:** Decide whether generated docs reports should remain tracked,
move under `deprecated/`, or be ignored/regenerated only in CI.

### FR-013: Reconcile duplicated data locations

**Finding:** Some metadata files exist both under root `data/` and
`src/spectralbridge/data/`.

**Why it matters:** Package data under `src/spectralbridge/data/` is what
installed users receive. Root `data/` may be examples, fixtures, or stale copies.

**Decision needed:** Label root data as examples/fixtures, move stale duplicates
to `deprecated/`, or document why both locations exist.

### FR-014: Refresh `publication_checklist.md`

**Finding:** The checklist predates several completed changes and still has
unchecked items that may now be partly done.

**Why it matters:** The checklist should be a reliable publication gate.

**Decision needed:** Review each checkbox, update status, and link completed
items to docs/tests where possible.
