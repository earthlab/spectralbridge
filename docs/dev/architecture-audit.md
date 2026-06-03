# Architecture Audit

This page records a lightweight architecture review of the current
SpectralBridge codebase. It is intentionally descriptive rather than
prescriptive: the goal is to identify duplication, consistency strengths, and
safe follow-up opportunities without proposing a broad refactor.

Review date: 2026-06-03

## Scope reviewed

The audit focused on the live implementation in:

- `src/spectralbridge/pipelines/pipeline.py`
- `src/spectralbridge/pipelines/drone.py`
- `src/spectralbridge/paths.py`
- `src/spectralbridge/utils/naming.py`
- `src/spectralbridge/merge_duckdb.py`
- `src/spectralbridge/polygons.py`
- `src/spectralbridge/neon_cube.py`
- `src/spectralbridge/parquet_export.py`
- `src/spectralbridge/qa_plots.py`
- `src/spectralbridge/sensor_panel_plots.py`
- `src/spectralbridge/io/neon_schema.py`
- `src/spectralbridge/io/neon_legacy.py`
- `src/spectralbridge/envi.py`
- `src/spectralbridge/file_types.py`

## High-level conclusion

The codebase already has a strong central pipeline shape:

- file-based orchestration is consistent
- restart-safe reruns are a real design principle, not an afterthought
- chunked NEON processing is still the dominant path
- output filenames are treated as contracts across code, tests, and docs

The main architectural risk is not instability in the core workflow. It is
duplication around naming, output discovery, metadata parsing, and QA-related
artifact lookup. Those areas are still working, but they are now spread across
multiple helpers and would benefit from deliberate consolidation later.

## Findings

### 1. Path authority is split between two naming systems

The repository has one strong path object in `spectralbridge.paths`:

- `FlightlinePaths`
- `SensorProductPaths`

That is the clearest single source of truth for canonical NEON output
locations.

At the same time, the NEON pipeline still relies heavily on
`spectralbridge.utils.naming.get_flightline_products()`, and
`pipeline.py` explicitly treats it as authoritative during stage execution and
skip validation.

Practical effect:

- code and docs increasingly refer to `FlightlinePaths`
- orchestration still depends on the older dict-style naming helper
- future naming changes would have to update both systems carefully

Assessment:

- this is manageable today because the two helpers are kept aligned
- it is the clearest example of “working duplication” in the repo
- it should be treated as a future consolidation candidate, not refactored
  casually

### 2. Output discovery logic exists in multiple subsystems

Several modules independently rediscover outputs from a flightline directory:

- `merge_duckdb._discover_inputs()` scans for original, corrected, resampled,
  and polygon parquet files
- `polygons._available_product_parquets()` performs a parallel parquet
  discovery pass for polygon workflows
- `qa_plots.py` has repeated logic for locating regular vs polygon merged
  parquets
- `utils/qa_summary.py` searches for parquet files related to QA PNGs
- `pipelines/drone.py` builds its own path map for drone outputs

Practical effect:

- behavior is mostly correct today
- new output suffixes or variants require updates in several places
- some discovery rules are keyword-based rather than path-object-based

Assessment:

- this is the biggest maintainability hotspot found in the audit
- the duplication is understandable because NEON and drone workflows differ,
  but artifact resolution now spans too many local heuristics

### 3. Metadata parsing is reasonably modular, but still layered

Metadata and schema handling is distributed across:

- `io/neon_schema.py` for active NEON HDF5 schema resolution
- `io/neon_legacy.py` for legacy layout detection
- `file_types.py` for filename-based metadata parsing and reconstruction
- `envi.py` for ENVI header parsing and wavelength normalization
- `polygon_extraction.py` for some additional wavelength/header fallback logic

Practical effect:

- this split is more defensible than the output-discovery duplication because
  the modules serve different formats
- however, there are now multiple places where wavelength and file identity are
  inferred

Assessment:

- the architecture is acceptable, but maintainers should be careful not to add
  yet another metadata-normalization layer
- future cleanup should focus on shared helpers, not broad parser rewrites

### 4. Chunking is consistent in principle, but implemented at two levels

For NEON raster work, chunking is anchored well:

- `NeonCube.iter_chunks()` and `chunk_count()` define the core spatial chunk
  contract
- `brdf_topo.py` correction uses fixed 100x100 chunking over that iterator
- export and resampling also rely on chunked processing over the cube

Parquet extraction uses a separate chunk-planning system in
`parquet_export.py`, which is appropriate because the workload is row-group and
tabular rather than pure raster tiling.

Drone work is more mixed:

- the test suite protects chunk-preserving extraction behavior
- some correction paths intentionally operate on a full-scene chunk when that
  is the current workflow contract

Assessment:

- chunking is still a real invariant, especially in the NEON path
- the code does not appear to have drifted into accidental whole-scene NEON
  processing
- maintainers should continue distinguishing “raster tile chunking” from
  “parquet row-group chunking” instead of forcing them into one abstraction

### 5. Restart-safe behavior is strong, but status reporting is fragmented

The architecture consistently prefers:

- validate existing outputs
- skip when outputs are intact
- rebuild when outputs are missing or corrupt

That pattern shows up repeatedly in `pipeline.py`, parquet export, merge, and
the drone pipeline.

The gap is not behavior; it is reporting. Statuses are still expressed as a
mix of:

- log lines
- boolean checks
- ad hoc audit JSON fields in drone workflows
- implicit stage outcomes

Assessment:

- restart safety is one of the strongest architectural properties in the repo
- explicit machine-readable stage statuses are still a missing cross-cutting
  layer
- this matches the still-open `P7` work rather than indicating a new design
  problem

### 6. QA generation is consistent in purpose, but not yet centralized

The system treats QA artifacts as required outputs, which is good. But the QA
stack is spread across:

- `qa_plots.py` for panel and metric generation
- `sensor_panel_plots.py` for sensor-focused visualization
- `utils/qa_summary.py` for batch QA summary behavior
- pipeline and drone modules for deciding when and how QA is invoked

Practical effect:

- QA is a first-class concept across the codebase
- locating “the right parquet for this QA artifact” is still partly heuristic
- polygon-mode and drone-mode QA have special-case lookup behavior

Assessment:

- QA consistency is good at the contract level
- QA artifact resolution is another good candidate for future consolidation

### 7. Shared drone and NEON infrastructure is possible, but should stay additive

There are real shared patterns between the NEON and drone workflows:

- path maps and output auditing
- parquet export and merge expectations
- QA artifact expectations
- polygon parquet enrichment and downstream merge semantics

But the input contracts still differ materially:

- NEON starts from downloaded HDF5 plus canonical flightline naming
- drone starts from local HDF5 discovery and preserves drone-native provenance

Assessment:

- there is room for more shared helpers around output validation and QA wiring
- there is not a strong case for merging the orchestration layers wholesale
- future work should share utilities, not collapse the workflows into one

## Strengths worth preserving

- `FlightlinePaths` is a solid contract object and already improves
  maintainability.
- `NeonCube.iter_chunks()` provides a clear chunking mental model that the test
  suite reinforces.
- the NEON pipeline still has a clear ordered-stage design.
- parquet and QA outputs are consistently treated as important public artifacts.
- tests now cover many of the restart and corruption-recovery behaviors that
  matter operationally.

## Recommended follow-up themes

These are architecture follow-ups, not urgent bugs:

1. consolidate output discovery helpers so merge, polygons, QA, and summaries
   stop maintaining parallel file-scanning rules
2. define a shared artifact locator for merged parquet, polygon merged parquet,
   QA PNG, and QA JSON lookups
3. decide whether `FlightlinePaths` should eventually subsume more of
   `get_flightline_products()` or whether the two-layer system is intentionally
   permanent
4. continue the explicit-status work already captured under `P7`

## Not recommended from this audit

- no broad rename or namespace migration
- no merge of drone and NEON orchestration into one pipeline entry point
- no speculative chunking abstraction that hides the difference between raster
  tiling and parquet chunking
- no parser rewrite unless driven by a concrete bug or compatibility failure
