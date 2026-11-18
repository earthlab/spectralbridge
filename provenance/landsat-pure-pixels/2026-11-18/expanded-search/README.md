# Regional Landsat candidate dataset

## Subsequent photo-annotation screen

A later [single-interpreter annotation attempt](../photo-annotation/RESULTS.md) mapped 20 dated views on 12 footprints. Four provisional footprints pass its 95% photo screen. The matched rerun has only one herbaceous and one exposed-substrate footprint and cannot establish separability. Field validation and independent second review remain pending. The inventory and pre-annotation status statements below describe the earlier stage.

The search now covers five western regions beyond the three original drone footprints. The dataset contains **51 candidate native Landsat 9 cells with complete seven-band surface-reflectance spectra**. Dated NAIP RGB context was available over the full displayed window for **50 cells**.

## Acquisition matching

| Region | Candidate cells | Full aerial chips | Landsat acquisition | Aerial date gap |
| --- | ---: | ---: | --- | ---: |
| Front Range, Colorado | 11 | 11 | 20 August 2023 | 1 day |
| Yellowstone region, Wyoming/Montana | 9 | 8 | 2 August 2024 | 1 day |
| Cascades, Washington/Oregon | 9 | 9 | 16 July 2023 | 1–2 days |
| Gunnison, Colorado | 12 | 12 | 28 September 2023 | 3–6 days |
| California shrublands | 10 | 10 | 27 June 2024 | 16–34 days |

Calendar-date differences use catalog acquisition dates. NAIP timestamps do not establish the exact local time of every source exposure. Landsat scenes were matched to regional aerial acquisition periods. Scene and region remain explicit because seasons and years vary.

## Discovery and QA

ESA WorldCover 2021 was read into a 20 m nearest-neighbor discovery grid. The search prioritized coarse-map interiors at least 60 m from a mapped boundary and proposed up to three locations per cover class per region, with 1 km spacing within each locator class. USGS GAP 2011 class 148, Rocky Mountain Aspen Forest and Woodland, supplied three additional Gunnison proposals. These distances rank locations and do not measure physical purity or guarantee statistical independence.

Each proposal was snapped to a native Landsat cell. Cloud/fill/cirrus/shadow/snow and B1–B7 saturation/terrain-occlusion QA were screened. Surface reflectance uses DN × 0.0000275 − 0.2, retaining finite negative values.

Additional fields record aerosol level, retrieval validity and interpolation flags, water flag, and cloud QA over a 5 × 5-cell neighborhood. The priority_observation flag requires a clear neighborhood, valid non-interpolated aerosol retrieval below the high level, no water flag, and aerial dates within 45 days. Five cells meet this deliberately strict observation-quality tier. Other records retain their QA evidence. Observation quality and PFT purity have separate fields.

Aerial sheets show 80 m context and the native 30 m cell in cyan. The review GeoJSON omits Landsat band values. No Landsat band value was used to locate or rank the map-based patches.

## Image review and statistical status

Several open-cover and exposed-rock candidates have more uniform footprints than the drone-site examples. Front Range grassland candidate 1, Cascades grassland candidate 3, Front Range bare/sparse candidate 2, and California shrubland candidate 1 are priorities for explicit cover annotation. Their full PFT fractions remain unmeasured.

Roads cross some nominal grassland cells. Several nominal bare/sparse cells show vegetation or strong shadow. The historical aspen candidates have nearby yellow foliage, brown central textures, conifer-like crowns and shadow. The review does not resolve living-deciduous cover, leaf-off cover and dead material throughout those cells.

[Qualitative notes](visual_review_notes.csv) document 28 candidates. Proposed PFT names there are follow-up hypotheses. The analytical researcher-category column remains unassigned.

The expanded cohort currently has **zero quantitatively verified PFT-pure cells**, so it produces no new PFT separability p-values. The remaining work is full-footprint class assignment and measured cover fractions, followed by sensitivity to purity cutoff and boundary margin. A regional test should retain scene/region strata and patch identities, assess spatial dependence, and compare classes within strata with actual category overlap. The earlier Niwot 300 m block and 30-day choices were specific to that exploratory audit.

## Dataset and images

- [Candidate spectra and QA](regional_candidate_dataset.csv)
- [Native-cell review footprints](regional_review_footprints.geojson)
- [Front Range aerial sheet](front_range-aerial-review.png)
- [Yellowstone aerial sheet](yellowstone-aerial-review.png)
- [Cascades aerial sheet](cascades-aerial-review.png)
- [Gunnison and aspen-locator aerial sheet](gunnison_aspen-aerial-review.png)
- [California aerial sheet](california_shrublands-aerial-review.png)
- [Source and output manifest](source_manifest.json)

## Reproduction and verification

Run from the repository root in the existing geospatial environment with network access.

~~~bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_regional_candidates.py --catalogue
~~~

Repeat the command below with front_range, yellowstone, cascades, gunnison_aspen and california_shrublands.

~~~bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_regional_candidates.py --region front_range
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_regional_candidates.py --finalize
~~~

The workflow uses bounded raster windows and compact local caches. Candidate checkpoints are reused under recorded acquisition-selection settings. Truncated catalog queries subdivide spatially after the service's deep-pagination endpoint repeatedly timed out.

Seven focused regression tests pass. They cover empty/thin patches, interior support and spacing, scene footprint/time ranking, complete partitioned catalog retrieval, unassigned researcher labels, map-asset conventions and cache reuse. Real-data checks cover finite seven-band values, unique native cells, QA, dates and 30 m geometry. All five final aerial sheets were visually inspected.

## Sources

- WorldCover provides Sentinel-derived broad land-cover classes. Its tree category combines multiple forest types. [Collection metadata](https://planetarycomputer.microsoft.com/api/stac/v1/collections/esa-worldcover)
- GAP/LANDFIRE National Terrestrial Ecosystems 2011 supplies historical ecosystem locators. Map age remains explicit in the aspen candidate label. [Collection metadata](https://planetarycomputer.microsoft.com/api/stac/v1/collections/gap)
- NAIP supplies the dated aerial RGB context. [Collection metadata](https://planetarycomputer.microsoft.com/api/stac/v1/collections/naip)
- Landsat Collection 2 Level-2 supplies reflectance and pixel, saturation and aerosol QA. [Collection metadata](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2)

## Multi-year seasonal expansion

The [2020–2025 seasonal archive](seasonal-archive/README.md) now contains 287 observations on the same 51 footprints, with a median seasonal offset of three days. It also adds 145 aerial views across years and temporal cover-review flags. The single-reference counts above describe the earlier regional dataset.
