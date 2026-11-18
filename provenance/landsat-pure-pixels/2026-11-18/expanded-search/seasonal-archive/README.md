# Seasonal Landsat observations on fixed footprints

## Subsequent photo-annotation screen

A later [single-interpreter annotation attempt](../../photo-annotation/RESULTS.md) mapped 20 dated views on 12 footprints. Four provisional footprints pass its 95% photo screen. The matched rerun has only one herbaceous and one exposed-substrate footprint and cannot establish separability. Field validation and independent second review remain pending. The inventory and pre-annotation status statements below describe the earlier stage.

The regional search now includes **2020–2025** for the same **51 candidate ground footprints**. It retained **287 complete seven-band observations** across 306 possible footprint/year combinations. Nineteen combinations lacked an observation that met the configured screening rules. The median retained seasonal date offset is **3 days**, and the maximum is **19 days**.

| Region | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Front Range | 11 | 11 | 11 | 11 | 11 | 11 |
| Yellowstone | 9 | 7 | 9 | 9 | 9 | 9 |
| Cascades | 9 | 9 | 9 | 9 | 9 | 9 |
| Gunnison | 9 | 5 | 10 | 11 | 11 | 9 |
| California shrublands | 10 | 10 | 10 | 10 | 10 | 10 |

## Seasonal and spatial definition

I used the existing regional candidate dataset's reference acquisition month/day as the anchor and searched within **21 calendar days on either side** in each year. These are explicit starting choices for the expanded search.

| Region | Reference month/day |
| --- | --- |
| Front Range | August 20 |
| Yellowstone | August 2 |
| Cascades | July 16 |
| Gunnison | September 28 |
| California shrublands | June 27 |

The anchors preserve the previous regional reference seasons. Matching accepted reference labels to particular field or AOP acquisition dates remains part of the scientific cohort design. The stored date offsets support tighter seasonal filters, including for deciduous leaf state.

The search includes Landsat 8 OLI and Landsat 9 OLI-2 Collection 2 Level-2. The retained set contains 152 Landsat 8 and 135 Landsat 9 observations. Platform, scene and acquisition date remain explicit for sensor-specific analysis.

The same WRS path/row was searched for each region. Every retained observation has the same projected CRS, 30 m pixel dimensions and mapped cell center as its original reference footprint. The numerical center tolerance is 0.000001 m. Reference alignment and boundary-margin sensitivity remain part of PFT-purity verification.

## Observation selection

129 scenes supplied 1,312 footprint/scene QA evaluations. Selection required exact grid alignment, clear fill/cloud/cirrus/shadow/snow flags, no B1–B7 saturation or terrain-occlusion flag, a clear 150 m context window, no water flag, and aerosol level below the high category. Per-pixel QA was used across the catalogued scene cloud conditions.

Within each footprint/year, valid non-interpolated aerosol retrieval was preferred, followed by the smallest seasonal offset and lower aerosol level, with deterministic scene-ID tie breaking. Complete finite B1–B7 surface reflectance was then required. An invalid spectrum triggered consideration of the next eligible scene. Selection used QA and dates, with all seven reflectance values retained in physical surface-reflectance units, including finite negative values.

81 selected observations have the preferred aerosol retrieval flags. The other 206 retain their aerosol/interpolation evidence in the table. Every observation remains linked to its fixed candidate ID. Repeated years belong to the same footprint for inference and uncertainty assessment.

## Aerial history and PFT purity

The aerial search spans 2019–2025. For visual comparisons, dated aerial epochs were screened within 45 seasonal calendar days of the regional reference date. Up to three representative epochs per footprint were rendered with the same cyan 30 m cell and 80 m context. The archive contains **145 full-window aerial views** across all 51 footprints. Fifty footprints have at least two reviewed aerial epochs. Yellowstone candidate 30-2 has one suitable aerial epoch.

The reviewed images show persistent open vegetation at Front Range 30-1 and Cascades 30-3, and persistent exposed substrate at Front Range 60-2 and Yellowstone 60-3. These are priorities for measured cover annotation. The Cascades 30-2 history indicates apparent regrowth, and the Cascades 60-2 history shows changing engineered ground. The Gunnison aspen images leave canopy condition and leaf state unresolved. Several rocky sites have large illumination differences between images.

[Temporal cover notes](cover_review_notes.csv) record these findings. Their flags are joined to the observation table. The date and resolution differences between aerial epochs are visible in the panels. The qualitative review does not establish a numerical PFT cover fraction.

The accepted PFT-pure cohort remains empty. **PFT separability remains pending quantitative footprint composition and accepted year-specific labels.** The additional dates provide cleaner observation choices and evidence for evaluating temporal stability. The number of distinct candidate footprints remains 51.

## Data and review sheets

- [All footprint/year records](seasonal_observations.csv), including the 19 unfilled combinations
- [Regional support by year](seasonal_support.csv)
- [Temporal cover review notes](cover_review_notes.csv)
- [Verification](validation.json) and [source/output checksums](manifest.json)

| Region | Aerial panels |
| --- | --- |
| Front Range | [1](front_range-timeline-01.png), [2](front_range-timeline-02.png), [3](front_range-timeline-03.png) |
| Yellowstone | [1](yellowstone-timeline-01.png), [2](yellowstone-timeline-02.png), [3](yellowstone-timeline-03.png) |
| Cascades | [1](cascades-timeline-01.png), [2](cascades-timeline-02.png), [3](cascades-timeline-03.png) |
| Gunnison | [1](gunnison_aspen-timeline-01.png), [2](gunnison_aspen-timeline-02.png), [3](gunnison_aspen-timeline-03.png) |
| California | [1](california_shrublands-timeline-01.png), [2](california_shrublands-timeline-02.png), [3](california_shrublands-timeline-03.png) |

## Reproduction

The entry point is examples/publication_figures/landsat_seasonal_archive.py. From the repository root, use the existing geospatial environment and network access. Repeat the two regional commands for each of the five region names shown below.

~~~bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_seasonal_archive.py --region front_range
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_seasonal_archive.py --review-region front_range
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_seasonal_archive.py --finalize
~~~

Region names are front_range, yellowstone, cascades, gunnison_aspen and california_shrublands. Defaults are years 2020–2025 and a 21-day seasonal half-window, configurable through the years and half-window-days arguments. Catalogs retain their full queries, and sampled QA, band values and aerial windows use compact restart caches with atomic writes.

Five seasonal-archive regression tests and seven regional-discovery tests pass. The tests cover leap-year season matching, cross-calendar windows, shifted-grid rejection, response-independent quality ranking, and preservation of repeated footprint identities and review flags. Real-data checks verify selected rows against the source QA audits, finite bands, fixed coordinates, calendar offsets, unique footprint/year pairs and aerial metadata. All 15 aerial sheets were inspected.

The Landsat and NAIP source item catalogs and per-scene QA tables accompany the outputs. The original reference dataset is identified by its SHA-256 in the manifest. [Landsat Collection 2 Level-2](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2) and [NAIP](https://planetarycomputer.microsoft.com/api/stac/v1/collections/naip) supply the imagery.
