# Final validation record — 15 October 2026

## Scientific and numerical checks

All 172 new fixed closure fits passed independent validation: proper-training,
calibration and test identities are disjoint; scaling and selection use training
observations; predictions and balanced accuracy, F1, Brier and conformal
calculations reproduce. All 60 paired temporal fits use the same unseen target
identities in both years. Exact paired sum-of-squares accounting and global
identity-balanced class-effect calculations independently reproduce. All 116
owned prior analytics artifacts checked remain unchanged. No optimizer warnings
were recorded in the 172 final fit diagnostics. The 156-fit main runner reused
its completed checkpoint ledger on restart; the additional 16 fits are the
predeclared broad woody shape/amplitude clarification, not model search.

Metadata audit reads the supplied original Parquet in place. It establishes
2023/2024 annotation dates reused across image years, 1,168 repeated NIWO IDs,
122 source raster products with 1 m coordinate spacing, median two extracted
pixels per polygon/acquisition, and no exact source-pixel overlap across distinct
IDs. This does not establish independent biological individuals, annual truth,
pixel purity or independent flights. Synthetic OLI is spectral convolution at
native support; it is not a 30 m spatial validation.

## Software and website

- Final full feasible offline suite: **694 passed, 7 skipped, 2 deselected**,
  30 warnings, 177.59 seconds; branch-aware coverage **68.11%**, gate 45%.
- Focused closure/docs regression checks: 14 passed.
- Browser desktop/mobile website checks: 2 passed.
- Relevant Ruff, strict MkDocs, source links, built-site anchors/assets,
  scientific-document snapshots, AI transparency and whitespace checks pass.
- Skips retain existing optional-data/tool limitations: polygon extraction
  collection, four full-mode HyTools tests, cached real-Landsat window and
  optional image-hash package. Network/full/Playwright markers are excluded from
  the offline suite; the two browser checks were run separately.

## Artifact quality and reconstruction

The report has 19 substantive pages, including five synthesis figure families.
Every report page was rendered and visually inspected; the final temporal figure
legend was checked after its spacing correction. Text geometry found no words
outside page boundaries. All 15 PNG/PDF/SVG figure exports and the final report
must reproduce byte-identically; see manifests/rebuild_validation.json.
Editable JSON/Markdown, builders, tables and machine-readable evidence hashes
are retained. Checksums protect provenance rather than asserting scientific
validity. See DESIGN.md, FINAL_ANALYSIS_AUDIT.md and the report for assumptions,
conditional uncertainty and unsupported claims.

## Scope of the decision

Intervals condition on observed support and the stated resampling/model design;
they do not guarantee performance in new geographic populations or propagate
all annotation uncertainty. Hierarchy comparisons have different populations,
class counts and chance levels. Paired partitions are descriptive, not causal
random-effect variance components. Shape normalization is a sensitivity, not a
production correction. Earliest-observation sensitivity changes representation
and weighting together. Physical fraction recovery, dependable unknown rejection
and operational use remain unvalidated. No source copy, new pixel cache,
production coefficient change, commit, push or publication was performed.
