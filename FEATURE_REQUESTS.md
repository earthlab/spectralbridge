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
- Status: Todo
- Goal: Review drone extraction paths and confirm chunked reading, correction,
  extraction, and restart-safe behavior are preserved.

### P5. Per-Flight Parquet Validation

- Priority: P5
- Status: Todo
- Goal: Validate per-flight parquet outputs for polygon mode and full
  extraction, restore missing functionality if needed using chunked processing,
  and surface QA metadata for parquet/merge/CSV status.

### P6. Drone QA And Failure-State Tests

- Priority: P6
- Status: Todo
- Goal: Expand drone tests for orientation, extraction modes, chunking, CRS,
  overlap, metadata preservation, overlays, correction failures, and CSV
  failures.

### P7. Restart, Checkpoint, And Recovery Integrity

- Priority: P7
- Status: Todo
- Goal: Add selective recovery and validation tests for restart-safe reuse,
  corrupt-output rebuilds, missing downstream products, and explicit statuses.

### P8. Output Schema Stability

- Priority: P8
- Status: Todo
- Goal: Protect required parquet schema fields, dtypes, and polygon metadata
  across per-flight and merged outputs.

### P9. Namespace And Container Compatibility

- Priority: P9
- Status: Todo
- Goal: Keep `import spectralbridge` canonical while preserving
  `import cross_sensor_cal` compatibility, add import/CLI tests, and avoid
  cwd-dependent behavior.

### P10. CI Hardening

- Priority: P10
- Status: Todo
- Goal: Expand CI coverage for `src/spectralbridge/**`, `tests/**`,
  `pyproject.toml`, and workflow changes with targeted install/lint/test steps.

### P11. Logging Review

- Priority: P11
- Status: Todo
- Goal: Review duplicate handlers plus notebook, multiprocessing, and Ray
  logging behavior; document findings without major refactors.

### P12. Public API Contract Review

- Priority: P12
- Status: Todo
- Goal: Review whether current smoke tests capture intentional public APIs
  without freezing internal helpers.

### P13. Release Hygiene

- Priority: P13
- Status: Todo
- Goal: Audit license/readme/citation/resources/manifest and confirm prompt
  logs, temporary outputs, large data, and development artifacts are not
  shipped unintentionally.

### P14. Versioning Review

- Priority: P14
- Status: Todo
- Goal: Review version definitions and release process to prevent drift.

### P15. Dependency Review

- Priority: P15
- Status: Todo
- Goal: Review `ray`, `geopandas`, and `rasterio` dependency posture and
  whether extras should change without breaking installs.

### P16. Documentation Modernization

- Priority: P16
- Status: In progress
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
- Remaining work:
  - Additional pages still use the older content structure and could use the
    same modernization treatment in a follow-up pass.

### P17. Architecture Audit

- Priority: P17
- Status: Todo
- Goal: Document lightweight findings on duplicate metadata/path/output logic,
  chunking consistency, restart-safe consistency, QA consistency, and shared
  drone/NEON infrastructure opportunities.

### P18. DOI And Zenodo Integration

- Priority: P18
- Status: Todo
- Goal: Add and document DOI generation infrastructure, including Zenodo
  enablement steps, release-to-DOI workflow guidance, and maintainer-facing
  verification steps.

### P19. Release Automation And Notes

- Priority: P19
- Status: Todo
- Goal: Add durable release automation guidance covering tagged releases,
  release notes, changelog/release note generation, and citation metadata
  refresh steps.

### P20. Software Citation And Publication Tracking

- Priority: P20
- Status: Todo
- Goal: Track associated publications, software-paper plans, preferred citation
  language, and versioned release citation policy in a maintainer-friendly way.

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
