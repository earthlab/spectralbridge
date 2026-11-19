# Expanded HLS L30 references, 19 November 2026

The working dataset restores the original **95% mapped cover on the nominal
30 m HLS footprint**. The additional 120 m source-area gate is a conservative
sensitivity, not a standard HLS requirement. Earlier strict/nominal stages remain
unchanged; the full source-area fractions remain available for every cell.

The expanded nominal dataset contains **496 HLS cells in 24 spatial patches**:
77 deciduous (5 patches), 110 evergreen (3), 99 herbaceous (5), 165 woody shrub
(7), and 45 non-vegetated/dead (4). It adds 114 cells from five spatial patches:
four chaparral-form shrub contexts and one exposed-rock context. No extra
independent units are created within a patch. Shrub and non-vegetated holdout
classes are now represented in training, unlike the earlier strict table.

The source-area sensitivity retains 161 cells in 13 patches: D32/2, E20/2,
H30/3, shrub63/5, non-vegetated16/1. It still lacks independent non-vegetated
patch support for a five-class holdout evaluation.

## New cover review and extraction

`additional_review_policy.json` freezes the five new dated aerial cases, image
and metadata hashes, case-specific exclusion rules and bounds. All four shrub
cases use the same dark/bright uncertainty cutoffs as the earlier shrub masks;
large crown/mixed areas of case003 are excluded by restricting the reviewed
region. The exposed-rock case traces only the eastern slab and marks dark cracks
or ambiguous material unknown. A 0.6 m boundary uncertainty belt is retained.
These are single-interpreter provisional labels, not field-validated cover.

`*-cover-review.png` shows each source and orange unknown/magenta other overlay.
`additional_photo_annotations.gpkg` retains projected target/other/unknown masks.
The photo review was frozen before retrieving spectra for these new locations;
no reference is removed for poor classifier fit or undesirable p-values.
Every new nominal >=95% pass was subjected to the same HLS Fmask/date/grid/
aerosol/finite-band rules as before. The parent HLS dataset, frozen original
photo geometries and older-lidar evergreen references remain immutable.

Outputs follow the parent HLS stage: `hls_l30_nominal_95pct_observations.csv`,
`hls_l30_strict_source_support_95pct_observations.csv`, support tables, native
footprints, source-kernel polygons, measured cover failures, complete QA and
selected observations. `parent_identity.json` prevents reuse after parent input
changes; `expansion_provenance.json` hashes the new policy, geometry and wrapper.
The inherited builder manifest hashes the complete selected tables and source
catalogues; the wrapper provenance supplements it with the new masks.

## Reproduce in this repository

```bash
.venv/bin/python examples/publication_figures/landsat_hls_reference_expansion.py --review-only
.venv/bin/python examples/publication_figures/landsat_hls_reference_expansion.py
.venv/bin/python examples/publication_figures/landsat_hls_method_comparison.py
```

The first command renders the frozen review without reading Landsat spectra.
The second reuses unchanged parent regional outputs, rebuilds California from
all old/new references, reuses valid compact HLS checkpoints and finalizes both
cohorts. Public Planetary Computer access is needed only for uncached reads.
The third runs analyses from compact tables without network/raster reads.
The existing repository environment and upstream cached aerial/structural
references are required. This is an analysis folder, not a separate package.
Source data retain provider terms. All reference-purity verification flags
remain false; the older-lidar evergreen date uncertainty remains explicit.
