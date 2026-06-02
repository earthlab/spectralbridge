# SpectralBridge Feature Requests

Review date: 2026-06-02  
Branch: main

This document tracks publication-readiness issues found during repository
cleanup review. The active cleanup requests from that review have been resolved.
Release-process gates that remain, such as building distribution artifacts or
running `twine check`, are tracked in `publication_checklist.md`.

## Active Requests

None from the 2026-06-02 publication cleanup review.

## Completed During Publication Cleanup

- Confirmed `AGENTS.md` exists with repo-specific guidance for future coding
  agents.
- Appended user prompts to `PROMPT_LOG.md` per repo policy.
- Removed accidental unrelated external-repo PRISM artifacts after user
  approval.
- Added ignore rules for OS files, bytecode, notebook checkpoints, caches, and
  generated docs reports.
- Archived tracked `.DS_Store` and Python bytecode files under
  `deprecated/generated_artifacts/2026-06-02/`.
- Archived stale generated docs reports under
  `deprecated/generated_docs/2026-06-02/`.
- Added `MANIFEST.in` so distributions intentionally include package data,
  docs, and tests while excluding root staging data, deprecated archives,
  generated docs reports, and container-only helper scripts.
- Documented root container/remote helper scripts in
  `docs/dev/container-workflows.md` and kept them active because container mount
  roots are part of the workflow.
- Documented root `data/` as examples/local staging and
  `src/spectralbridge/data/` as the authoritative packaged data location.
- Documented large deprecated Megan unmixing data as provenance-only and
  excluded it from package distributions.
- Updated README, Quickstart, and tutorials so `SpectralBridge`/`spectralbridge`
  is the canonical project/package name while cross-sensor calibration remains
  the technical workflow concept.
- Clarified Ray as a required dependency and the default parallel backend.
- Preserved Parquet as the authoritative tabular output in docs.
- Added a public-function import/signature smoke matrix.
- Added Ray/default-engine tests and removed the old optional-Ray test naming.
- Added Playwright browser smoke tests for the MkDocs site and wired them into
  the docs workflow.
- Rewrote the MicaSense tutorial around the supported `run_drone_pipeline`
  local-H5 workflow.
- Rewrote `docs/reference/extending.md` around current extension points instead
  of a nonexistent registry API.
- Archived stale root draft docs with `FILLME` markers under
  `deprecated/docs/publication_cleanup_2026-06-02/`.
- Refreshed root `CONTRIBUTING.md` so it uses SpectralBridge naming, current
  install/test guidance, Ray-required language, and marker-free text.
- Updated `scripts/check_docs_links.py` to scan nested docs and make
  `FILLME` marker failures opt-in with `--fail-on-fillme`.
- Removed active-doc `FILLME` markers from `docs/naming-conventions.md`.
- Added lazy top-level exports for `go_forth_and_multiply` and
  `process_one_flightline`.
- Replaced the README QA “coming soon” placeholder with an existing checked-in
  workflow artifact that shows QA reports in the output contract.
- Refreshed `publication_checklist.md` and added
  `docs/dev/publication-cleanup-log.md` as the detailed cleanup record.

## Notes

- A renderer-produced QA PNG was not generated during this cleanup because the
  local Python environments available here do not have `matplotlib`. Existing
  QA tests still cover fixture rendering in environments with the test
  dependencies installed.
- No scientific correction assumptions, Parquet behavior, chunking strategy, or
  restart-safe pipeline contracts were intentionally changed.
