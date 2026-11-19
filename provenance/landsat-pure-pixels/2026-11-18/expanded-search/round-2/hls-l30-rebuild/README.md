# BRDF-normalized Landsat reference dataset: HLS L30 v2

Rebuilt 19 November 2026 from NASA HLS L30 v2 (`hls2-l30`, DOI
10.5067/HLS/HLSL30.002), accessed through Planetary Computer public COGs.
The original Collection 2 SR dataset is preserved. These are new HLS-grid
observations, not rescaled copies of the old table. B1–B7 are nadir-view
BRDF-normalized reflectance. No new empirical sensor calibration is claimed.

## Rebuilt observations

| PFT | Nominal 95% cover cells | Also pass 95% source-support screen |
| --- | ---: | ---: |
| Deciduous | 77 | 32 |
| Evergreen | 110 | 20 |
| Herbaceous | 99 | 30 |
| Woody shrub | 55 | 16 |
| Non-vegetated & dead | 41 | 16 |
| Total | 382 | 114 |

The nominal cohort represents 19 spatial patch groups. The strict-support subset
represents nine (two deciduous, two evergreen, three herbaceous, one shrub, one
non-vegetated). Pixels within a patch are not independent replicates. The smaller
strict collection cannot support the previous five-class held-patch protocol for
classes represented by only one patch. Do not carry over old accuracy or p-values.

Seven HLS granules supply the retained observations: 378 Landsat 9 cells and four
Landsat 8 cells. Photo/acquisition gaps are 0–29 days in the same year; selected
dates are within one day of their regional seasonal anchor. Fmask aerosol levels
are low (323 cells) or moderate (59); no climatology/high-AOT observations were
selected. The search evaluated 6,859 cell/granule QA records and 2,176 cover
measurements. All 382 retained records have seven finite scaled bands.

## Which table to use

- `hls_l30_nominal_95pct_observations.csv`: 382 cells passing nominal footprint
  cover and HLS QA. This is the broader, explicitly nominal-support collection.
- `hls_l30_strict_source_support_95pct_observations.csv`: 114 cells additionally
  passing the conservative source-area cover screen. This is the primary strict
  support dataset for purity-focused work. It is a subset, not another sample.
- `reference_support.csv`: per-class patch, region and acquisition support for
  both cohorts. Check this before any inferential run.
- `hls_native_footprints.geojson`: actual 30 m HLS squares, WGS84 coordinates.
- `hls_source_kernel_support.geojson`: conservative native-source support boxes,
  with the same cell IDs and strict-support flags.
- `*-all_cover_measurements.csv`: passes and failures on the new grid.
- `*-nominal_reference_cells.csv`: reference selection before spectral retrieval.
- `*-hls_qa_audit.csv`: every tested cell/granule, including exclusions.
- `*-selected_observations.csv`: regional selected data, before final reduction.
- `*-catalogue.json`: frozen public item metadata and unsigned asset URLs.
- `independent_source_spot_checks.csv`: fresh B05 and grid checks, one per PFT.
- `rebuild_policy.json`, `manifest.json`: explicit selection policy and hashes.

## Footprints, purity and source mixing

HLS has a distinct 30 m MGRS grid, shifted 15 m in both axes relative to the
original native Landsat lattice here. We enumerate the actual HLS cells fully
contained in each frozen 240 m reference context, instead of using old cell IDs.
Nominal cover is remeasured against the projected target-cover geometry from the
frozen photo annotations, including their existing unknown/boundary exclusions.
Unannotated area remains unknown and cannot count as target cover.

HLS resamples Landsat with cubic convolution. For the same-UTM native lattice,
the strict screen measures target cover across the full bounding area of its
4x4 native Landsat source pixels (120x120 m = 14,400 square metres). This is an
unweighted **conservative source-area diagnostic**, not the signed cubic weights,
an exact contamination estimate, a confidence bound, or proof of purity. Both
nominal and support cover must be >=95% for the strict table. Full support area
remains the denominator where references are missing. Out-of-zone HLS tiles are
excluded rather than approximating an unvalidated reprojected source kernel.

For evergreen, cover is remeasured from the saved one-metre first-return-height
grid, counting bins >5 m and leaving missing bins unknown. This is a structural
proxy with 2016/2018 lidar supporting provisional 2023 evergreen identities; it
is not measured current evergreen PFT cover. The reference basis, structural
project, dated aerial source and independent-verification flags are retained.
All labels remain provisional and `pft_purity_verified=False`.

Candidate references are selected by mapped cover before reflectance retrieval.
Contradictory class labels for the same new cell/year are excluded; same-label
overlaps are deduplicated deterministically by support/nominal cover. Overlapping
240 m contexts share a transitive patch group. The physical cell identity is
EPSG plus projected HLS centre, so overlapping MGRS tiles cannot multiply samples.

## HLS-specific extraction and QA

HLS reflectance is signed int16, scaled by **0.0001 with zero offset**; -9999 is
fill. Collection 2's 0.0000275 and -0.2 conversion is not used. Finite negative
reflectance is retained. All seven bands must match the declared HLS grid and
nodata contract. Fmask is uint8 with 255 fill: bits 1–5 flag cloud, adjacency,
shadow, snow and water; reserved bit 0 is also conservatively rejected. Bits6–7
encode aerosol level; high (3) is excluded. A surrounding 5x5 HLS window (150 m)
must have no lower-six-bit flags or fill. HLS Fmask does not expose native
Collection 2 saturation QA, recorded explicitly in `saturation_qa_status`.

Scenes must be within the pre-existing regional +/-21-day seasonal window and
within 45 days of same-year aerial imagery. Prefer non-climatology aerosol, then
nearest seasonal date, nearest photo date, then stable item ID. Reflectance and
classification outcomes never rank scenes. Final records are checked against
their saved QA audit, including Fmask, raster row/column and date gap.

## Reproduce within the repository

Use the existing `.venv` and repository dependencies. The builder is a standalone
analysis script, not a new package. Run from repository root:

```bash
.venv/bin/python examples/publication_figures/landsat_hls_reference_rebuild.py --region front_range
.venv/bin/python examples/publication_figures/landsat_hls_reference_rebuild.py --region gunnison_aspen
.venv/bin/python examples/publication_figures/landsat_hls_reference_rebuild.py --region cascades
.venv/bin/python examples/publication_figures/landsat_hls_reference_rebuild.py --region california_shrublands
.venv/bin/python examples/publication_figures/landsat_hls_reference_rebuild.py --region yellowstone
.venv/bin/python examples/publication_figures/landsat_hls_reference_rebuild.py --finalize
.venv/bin/pytest -q tests/test_landsat_hls_reference_rebuild.py
```

The regional steps require public Planetary Computer access for uncached reads.
The finalizer runs offline from completed regional tables. Frozen photo masks,
annotation policy/image hashes, cached aerial contexts and saved structural grids
are read in place from earlier round-2 artifacts. Compact QA/band checkpoints are
under `archive/local/landsat-hls-l30-rebuild`; they are reused when signatures
match. Changed builder code/reference selections invalidate their cache identity.
Never edit a frozen policy to reuse stale data; create a new stage/version for a
scientific policy change. Original source terms apply; no new data license is
asserted. Current data URLs are unsigned; temporary access signatures stay in
memory. No Earthdata credentials are required for this public mirror.

This rebuild does not overwrite Figure 4 or claim rerun separability/
identifiability results. Those require explicitly choosing and reporting the HLS
support cohort and the corresponding reduced spatial replication.
