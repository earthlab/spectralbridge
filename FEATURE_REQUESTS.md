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
- Status: Todo
- Goal: Prefer `import spectralbridge` in examples while documenting HDF5
  contracts, chunking, restart behavior, parquet authority, CSV sidecars, and
  drone/NEON workflows.

### P17. Architecture Audit

- Priority: P17
- Status: Todo
- Goal: Document lightweight findings on duplicate metadata/path/output logic,
  chunking consistency, restart-safe consistency, QA consistency, and shared
  drone/NEON infrastructure opportunities.

## Completed Requests

- 2026-06-02: Publication cleanup backlog completed and moved to
  `docs/dev/publication-cleanup-log.md` plus `publication_checklist.md` for
  release gating details.

## Blockers And Resume Notes

- Local verification depends on which Python/test dependencies are available in
  the active environment. Record any missing tooling under the active item
  before stopping.
