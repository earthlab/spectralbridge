# Lidar-supported evergreen candidate cells

19 November 2026. **88 distinct 30 m cells across three Cascades patches** now
have complete, QA-screened Landsat B1–B7 observations and >=95% structural canopy
support under the exploratory rule below. These are candidates for reference
validation, not accepted current evergreen purity labels. The primary 393-cell
photo-screened cohort and Figure 4 are unchanged. No five-class test was run.

| Context patch | Nominal structural candidates | Retain screen at 5 m shifts |
| --- | ---: | ---: |
| evergreen-005 | 20 | 9 |
| evergreen-006 | 33 | 22 |
| evergreen-007 | 35 | 29 |
| Total | 88 | 60 |

The three patches supply three spatial groups, not 88 independent sites. All are
in one region. Landsat imagery comes from three scenes: 77 Landsat 9 and 11
Landsat 8 observations. Aerial/Landsat gaps are 1–15 days. All cells pass the
existing grid, core/saturation, 150 m context, same-year photo/date and non-high
aerosol checks. Thirty-one have preferred aerosol retrieval and 57 retain
explicit fallback flags. Validate the latter separately in sensitivity analyses.

## What the structural screen means

Public USGS COPC clouds are queried only inside a 242 m window at pre-existing
patches. Only first returns are retained, excluding withheld and noise classes
7/18. Heights are normalized using the public DTM from the same acquisition
project and vertical datum; terrain is sampled with nearest-neighbour resampling.
The maximum finite first-return height is recorded in each 1 m bin. Missing bins
remain unknown; no canopy interpolation or gap filling is used. A nominal cell
passes if at least 855 of its 900 bins have a return >5 m above terrain. Fractions
above 2/10 m and observed-bin fractions are also reported. A 1 m occupied bin is
a resolution-dependent structural proxy, not an exact canopy-area measurement.

Projects and acquisition years remain separate. For each physical cell the latest
available project is selected before applying the threshold, so older passing
structure cannot conceal a newer failure. Whole-cell shifts are evaluated at all
nine combinations of -3/0/3 m and -5/0/5 m. These are discrete sensitivities,
not a statistical confidence interval or an exhaustive registration-error model.

The selected lidar is from 2016 (evergreen-005) and 2018 (006/007), while aerial
references and Landsat observations are from 2023. Dated aerial views in 2019 and
2023 show persistent conifer-form crowns without an obvious stand-replacing
clearing in single-Codex visual triage. They do not quantify current evergreen
cover or resolve every shaded crown, understory component or small mortality
change. Older height data cannot establish current PFT purity. All records retain
`pft_purity_verified=False` and a pending-reference status. This is a separate
structural criterion; do not substitute it for the primary photo-cover fraction.

## Files for review

- `evergreen_candidate_review_board.png`: 2019 and 2023 aerial views beside
  first-return heights. Green cells retain the screen at 5 m shifts; orange pass
  only the nominal screen. White lidar bins are missing, not bare ground.
- `landsat_evergreen_structural_candidate_observations.csv`: 88 candidates with
  B1–B7, QA, date, structural support and identity fields.
- `evergreen_candidate_footprints.geojson`: corresponding native cell boundaries.
- `structurally_screened_candidate_cells.csv`: reference candidates before QA.
- `structural_candidates_landsat_qa_audit.csv`: all 440 scene/cell QA checks.
- `native_cell_structural_support.csv`: all measured cells, including failures
  and separate acquisition projects; do not count duplicate physical cells twice.
- `dated_visual_triage.json`: exact dated imagery hashes and interpretation limits.
- `*.npy` and matching JSON: compact height grids, source item IDs, acquisition
  intervals, selection identity and SHA-256. Catalogue JSON retains source URLs.
- `validation_summary.json`: machine-readable verification and limitations.

## Reproduce from repository root

Use the existing repository virtual environment. The optional point-cloud reader
was installed under /tmp without changing project dependencies. For a new machine,
install laspy 2.6.1 and lazrs 0.9.0 in a separate local environment alongside the
repository dependencies. Other analysis scripts use the existing repo environment.

```bash
PYTHONPATH=/tmp/spectralbridge-lidar-tools MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_evergreen_pointcloud.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_evergreen_shortlist.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_evergreen_review_board.py
.venv/bin/pytest -q tests/test_landsat_reference_sources.py
```

The /tmp reader installation is temporary; adjust PYTHONPATH to the location of
your optional laspy installation. Original public source datasets retain their
source terms. Compact outputs are reusable in place; scripts never modify the
underlying source clouds. Cached aerial imagery under `archive/local/` is required
for review-board rendering. Source IDs and hashes support retrieval, but this
folder is not a complete offline archive. Public catalogue/asset access is required
for uncached reads. Successful hashed height grids and Landsat QA caches are reused.

Next: independently review the dated footprints and evergreen growth form, seek
closer-date height evidence or quantify temporal cover changes, then declare a
combined reference policy before merging these candidates into inferential tests.
