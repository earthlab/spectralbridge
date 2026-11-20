# Power-directed HLS reference expansion

19 November 2026. This stage preserves the prior 496-cell, 24-patch dataset and
appends new independently located contexts. All reference labels remain
single-interpreter provisional; none is independently field-validated.

## Current dataset and results

Use `review-batch-2/hls-combined/hls_l30_nominal_95pct_observations.csv` for the
latest combined cohort: **1,241 distinct HLS cells in 61 spatial patches**.
The five-class counts are:

| PFT | HLS cells | Independent patches |
|---|---:|---:|
| Deciduous | 165 | 12 |
| Evergreen | 364 | 11 |
| Herbaceous | 288 | 14 |
| Woody shrub | 339 | 15 |
| Non-vegetated & dead | 85 | 9 |

The unchanged >=95% nominal 30 m mapped-cover definition is primary. An extra
120 m source-area cover screen is retained separately: 362 cells / 30 patches.
Every selected record passes the existing HLS L30 v2 NBAR, seven-band, Fmask,
150 m surrounding-clear, same-year photo/date-gap and seasonal-window contracts.
All 496 parent records and their original measurements are preserved.

`review-batch-2/analysis/` contains the new tests and every held-out prediction.
Direct-reflectance five-class leave-one-patch-out accuracy is 58/61 (95.1%).
Recall is D11/12, E11/11, H14/14, W13/15, nonveg9/9. All ten pooled contrasts
pass the current ten-pair Holm family. Region-conditioned tests support two
contrasts (deciduous/nonveg and herbaceous/nonveg); evergreen/herbaceous is not
supported, and seven contrasts lack sufficient mixed-region support. Deciduous,
evergreen and woody shrub remain single-region classes. Pooled results therefore
retain region/season confounding and do not establish geographic transfer.
Current-family correction does not adjust across previous collection rounds.
These are exploratory results, not confirmatory power or validated reference
truth. Figure 4 has not been changed by this expansion stage.

## Collection and review

`patch_proposals.csv` freezes 116 new 240 m contexts. Land-cover and GAP products
are locators only. Proposals are snapped to the existing reference lattice and
spaced at least 1 km from prior proposals and other new contexts in the region.
No HLS spectrum or p-value selected these locations or cover polygons.

All 116 dated aerial contexts are cached locally. The two frozen review policies
specify 33 and 14 contexts before retrieval of their spectra. Some reviewed
contexts produce no valid cells. Other contexts remain unaccepted, not silently
labelled. `reviewed_photo_cover.gpkg` records target/other/unknown projected
polygons; source image and metadata hashes are frozen in the policies.
Evergreen additions use old public COPC first-return no-fill 1 m canopy-height
grids plus current photo interpretation. Unknown height bins stay unknown.
The old lidar establishes a structural proxy, not current evergreen purity;
photo shadows, growth-form identity and acquisition-year stability remain
uncertain. Front Range grids do not reach the threshold; Yellowstone has no
usable structural coverage in this retrieval.

## Power planning

`power-planning-v2/` is the authoritative scenario analysis. `superseded_power_prototype/`
is retained solely for provenance; do not use its targets. The corrected design
uses exact enumeration of small label spaces and independent per-scenario seeds.
Under three matched regions, Gaussian residuals and a one-standard-deviation
shift in all seven correlated bands, 24 independent patches/class reach the
stated 80% power criterion (Wilson 95% lower bound >=80%). A shift in one band
requires 48/class under these assumptions. Smaller effects may need more than
60/class. These are conditional scenarios, not estimated power of this dataset.
The present cohort does not satisfy that matched-region design. Additional
region-matched classes and independent cover validation remain the next task;
more dates from the same physical patch do not create independent patches.

## Reproduce from the repository root

Use the repository `.venv`; geospatial/network dependencies are required for
source retrieval. Existing downloads/checkpoints are reused.

```sh
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_hls_power_planning.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_hls_sampling_batch.py --discover
# Retrieve each region's contexts with --context REGION. Requires public network.
# Optional lidar reader: PYTHONPATH=/tmp/spectralbridge-lidar-tools
# .venv/bin/python examples/publication_figures/landsat_hls_power_lidar.py --region cascades

MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_hls_power_reference_build.py --freeze
# Then --extract cascades, --extract gunnison_aspen, --extract front_range
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_hls_power_reference_build.py --finalize
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_hls_power_reference_batch2.py --freeze
# Then --extract yellowstone and --extract california_shrublands
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_hls_power_reference_batch2.py --finalize
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_hls_power_analysis.py
```

Complete `--freeze` sequentially before running independent regional extractions;
only the freeze step writes the shared review GeoPackage. New photo/lidar source
identities or review choices require a new version, not editing the frozen policy.
The first batch is the immutable parent of the second batch. Finalization and
statistical analysis can run offline after extraction.

Larger patch counts exceed the previous exact-enumeration budget. The new
analysis retains exact NPC for <=100,000 label assignments; larger designs use
99,999 reproducible within-block random assignments plus the observed assignment.
This preserves the statistic, exchangeability blocks, ten-pair Holm correction,
training-only classifier preprocessing, and patch unit. Each output records the
method, label-space size, draw count and input-derived seed. Randomized p-values
are estimates at finite permutation resolution, not exact probabilities.
