# Landsat reference expansion, round 2

Updated 19 November 2026. This is a provisional reference-development dataset,
not a validated five-PFT training or accuracy dataset. Figure 4 is unchanged.

## Current result

393 distinct native 30 m Landsat cells pass the declared photo-cover and scene-QA
screens: 109 deciduous, 141 herbaceous, 82 woody shrub, 61 non-vegetated/dead,
and zero evergreen. These represent 17 patch groups, not 393 independent sites.
All interpretations were made by one Codex interpreter; none has independent
interpreter or field validation. A 95% mapped-cover threshold is not a 95%
confidence statement about the true PFT cover.

`expanded_photo_screened_landsat_dataset.csv` is the primary compact table.
`identifiability_readiness.csv` records class, patch and region support.
`preferred_aerosol_subset.csv` contains 90 cells with preferred aerosol retrieval;
the other 303 retain explicitly flagged fallback aerosol status. High aerosol is
excluded. Do not silently substitute the fallback subset for preferred retrieval.
`purity_and_registration_sensitivity.csv` records cover and registration sensitivity.
Only primary 95% photo candidates were passed through Landsat extraction; looser
threshold photo counts do not establish an expanded QA-screened Landsat cohort.

## Selection and independence

WorldCover and historical GAP are candidate locators, not purity truth. There are
199 base context proposals plus 10 live-oak hypotheses, each with 240 m aerial
context. Thirty-one contexts have quantitative, dated interpretation policies.
The policy is frozen in `reviewed_patch_policy.json`; image and metadata hashes
are retained. Unknown shadow, snow and ambiguous growth form are not assumed to
belong to the target category. Each complete cell uses the full 900 square metre
denominator, with a 0.6 m boundary uncertainty belt and 3/5 m shift sensitivities.

The primary cohort requires >=95% lower mapped target cover, complete B1–B7,
clear pixel/saturation and 150 m context QA, no water, aerosol level below high,
aerial/Landsat dates within 45 days in the same year, and the original regional
seasonal window. Spectral class separation is never a scene-selection criterion.
Repeated years share the same physical cell identity. Overlapping context patches
are merged into patch groups. Validation must hold out whole groups. Deciduous
and woody shrub currently each come from one region; regional transfer is untested.

## Audit files

- `dated_cell_cover_fractions.csv`: 1,519 measured cell views before screening.
- `photo_reference_annotations.gpkg`: projected target/other/unknown geometries.
- `reviewed_native_cells.geojson`: reviewed cell locations, including failures.
- `photo_screened_reference_cells.csv`: 395 photo-passing cells; two have no
  eligible Landsat observation and are excluded from the primary 393.
- `*-landsat_qa_audit.csv`: all 1,975 footprint/scene QA checks.
- `annotated-contexts/`: original and interpreted overlays for inspection.
- `annotation_manifest.json`: input, policy and annotation implementation hashes.

## Evergreen follow-up using public sources

`evergreen-epochs/` contains 16 additional aerial contexts at eight locations:
six Cascades, six Front Range, four Gunnison views. Yellowstone had no alternate
image meeting the selected location/date conditions. These are review candidates,
not accepted references or additional independent pixels. In the Cascades views
reviewed so far, shaded spaces remain ambiguous. No alternate-year reference has
been promoted into the primary cohort.

`public-lidar/` contains the Planetary Computer USGS 3DEP collection definition,
26-item Cascades catalogue, ten small HAG windows at eight evergreen candidates,
source metadata, hashes, comparison images and coverage audit. Several catalogue
footprints contain large nodata areas; only two distinct candidate contexts have
complete windows. Read actual valid fractions, not catalogue footprint coverage.
The HAG product interpolates normalized point heights with IDW, including ground
returns: it is not a canopy-top cover raster. Its 2016/2018 acquisition intervals
also precede current aerial references. At evergreen-006, tall structure occurs
in many aerial-dark areas, which makes a structural follow-up promising. It does
not establish 95% current evergreen cover. Next obtain canopy-top DSM and terrain
DTM (or classified point clouds), quantify valid coverage, and inspect disturbance
and leaf habit across dates before proposing a separate structural reference rule.
Do not threshold this interpolated HAG into accepted PFT purity.

NEON ecosystem-structure product metadata was accessible, but correct NIWO/WREF
monthly file-list endpoints returned HTTP 403. `supplemental_canopy_height_access.json`
records this source failure; no inaccessible NEON height data were used.

## Rerun in the repository

These are analysis scripts, not a Python package. Run from repository root using
the existing `.venv` with repository dependencies installed. Network steps require
public Planetary Computer/USGS access. Large window caches live under ignored
`archive/local/`; this compact audit folder alone is not an offline image archive.
Public-source item IDs, asset URLs and hashes support retrieval and verification;
future providers may change availability. Source data retain their source terms.

```bash
# Regenerate annotations only from the frozen policy and matching cached images.
.venv/bin/python examples/publication_figures/landsat_spatial_expansion.py --annotate
# Run separately for each of the five regions; existing valid checkpoints are reused.
.venv/bin/python examples/publication_figures/landsat_spatial_expansion.py --extract front_range
.venv/bin/python examples/publication_figures/landsat_spatial_expansion.py --finalize
# Supplementary imagery and structural review, kept separate from accepted labels.
.venv/bin/python examples/publication_figures/landsat_evergreen_epochs.py --region cascades
.venv/bin/python examples/publication_figures/landsat_structural_reference.py
pytest -q tests/test_landsat_reference_sources.py tests/test_landsat_spatial_expansion.py tests/test_landsat_photo_annotation.py tests/test_landsat_regional_candidates.py tests/test_landsat_seasonal_archive.py
```

Other extract regions: gunnison_aspen, california_shrublands, cascades, yellowstone.
Discovery/context CLI options are documented by `--help` in the expansion script.
Retain old cohorts and outputs when creating a new interpretation policy. Hash
mismatches fail explicitly. The finalizer rejects stale class, image, date, patch
or cover metadata even when a physical cell ID is unchanged.

No five-class identifiability result has been generated: evergreen is absent and
all reference labels remain provisional. Keep these limitations visible when
sharing the tables. A four-class exploratory grouped test would address a different
question and must be labelled accordingly.

## Subsequent evergreen shortlist

See `evergreen-pointcloud/README.md`: 88 new lidar-supported candidates have
QA-screened Landsat spectra across three patches; 60 retain their structural
screen under 5 m shifts. They remain separate from the 393 primary references
because current evergreen purity and the older-lidar date mismatch remain
unvalidated. The alternate-aerial inventory now contains 19 views (nine Cascades).
