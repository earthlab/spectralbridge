# Dated Landsat footprint photo annotations

I interpreted **20 aerial views covering 12 candidate footprints**, mapped target, known other, and uncertain areas, and calculated their intersection with the complete 900 m² Landsat cell. **Four distinct footprints pass the provisional 95% photo-annotation screen**, supplying seven dated observations in the existing seasonal archive.

These are single-interpreter photo references made by OpenAI Codex. Independent second interpretation and field validation remain pending. All 12 candidate footprints have zero overlap with the existing field polygons. Nearby field labels were retained as contextual evidence in the field-anchor table, with distances and dates.

## Candidates passing the primary screen

| Footprint | Interpreted cover | Aerial years supporting the screen | Mapped target fraction |
| --- | --- | --- | ---: |
| front_range-30-1 | Herbaceous | 2021, 2023 | 100% |
| cascades-30-3 | Herbaceous | 2023 | 98.0% |
| yellowstone-30-3 | Herbaceous | 2022, 2024 | 100% |
| yellowstone-60-3 | Non-vegetated & dead, exposed substrate | 2022, 2024 | 98.6–99.9% |

The mapped fractions describe the interpreted cover at aerial-image resolution. Subpixel mixtures, background contributions, and interpretation error remain sources of uncertainty. Unassigned area has an explicit unknown class. A zero target lower bound with 100% unknown expresses unresolved composition.

At 90%, a fifth footprint, california_shrublands-30-1, qualifies in 2020 and 2022 with approximately 92.0% mapped herbaceous cover after excluding the track and boundary uncertainty. Its 2024 image falls to 79.1% under the additional track interpretation. It fails the 95% screen in every annotated year.

The deciduous, evergreen, and woody-shrub cases retain unresolved PFT or projected-cover assignments. The original Front Range rock candidate has 11–18% unassigned dark interstices under the conservative annotation stencil. The later Gunnison rock image has 39% unassigned interstices. These uncertain areas reduce their target lower bounds.

## Purity and registration sensitivity

| Required mapped target cover | Herbaceous footprints with usable Landsat QA | Exposed-substrate footprints | Total distinct footprints |
| --- | ---: | ---: | ---: |
| 90% | 4 | 1 | 5 |
| 95%, primary | 3 | 1 | 4 |
| 100% | 2 | 0 | 2 |

The counts above are unchanged when using the minimum mapped target fraction across the nine examined positions at ±3 m or ±5 m in the two coordinate directions. The sensitivity scores cover those discrete shifts. The complete dated fractions and upper bounds are supplied separately.

## Matched Landsat separability rerun

The seven-band max/integrated nonparametric-combination diagnostic was rerun using the same standardized statistic and NPC calibration utilities as the package's PFT method audit. Class labels move as complete footprint spectra. Complete enumeration replaces Monte Carlo sampling for this small cohort.

For each class pair and region, the algorithm chooses one scene/year containing both accepted labels. Selection uses matched class support, aerosol-retrieval quality and aerial date gap. A footprint appears once in a contrast. Region/acquisition blocks preserve the same-scene comparison. Inference is conditional on the photo labels and within-block exchangeability. Holm adjustment covers the ten planned class pairs, with untested contrasts represented conservatively by p=1 only in the adjustment calculation. Their output p-values remain absent.

Only **Herbaceous / Non-vegetated & dead** has a matched cohort at the 95% threshold.

| Quantity | Result |
| --- | --- |
| Scene | LC09_L2SP_038029_20240818_02_T1 |
| Footprints | yellowstone-30-3 and yellowstone-60-3 |
| Aerial reference date | 1 August 2024 |
| Landsat date | 18 August 2024 |
| Independent footprint counts | 1 herbaceous, 1 exposed substrate |
| Whole-footprint label assignments | 2 |
| Exact max, integrated and NPC p | 1.0 |
| Holm-adjusted NPC p | 1.0 |

Both possible label assignments have the same absolute contrast statistics. This cohort therefore has no power to establish separability with the two-sided diagnostic. It provides no basis for a positive or negative conclusion about PFT separability across Landsat. The same limitation holds at 90%; at 100% the exposed-substrate class lacks support. The other nine PFT pairs lack an accepted matched cohort. Recognition/identifiability accuracy remains unassessed.

## Annotation method and limits

The source policy was frozen before calculating the Landsat test results. It records each image/year, proposed cover class, manually traced context polygons, internal exclusions and abstentions. The geometry preserves the full 30 m cell denominator and partitions the surrounding 80 m view into target, known other and uncertain areas.

A 0.6 m uncertainty belt was added around traced internal polygon boundaries. It is an initial annotation choice tied to the coarser aerial resolution represented here. Some exposed-rock and pale-fleck cases additionally use explicitly recorded raw-image display cutoffs as conservative uncertainty stencils. These image-specific cutoffs flag unresolved areas. Target classes come from interpreted morphology and context. The stencils require review with the source imagery before treating these references as validated labels.

All geometry intersections use projected metres. Raster-derived exclusion polygons preserve pixel footprints and holes. Cover lower bounds count only mapped target area; upper bounds additionally include unknown area. Interpretation uncertainty from a second reviewer remains unmeasured.

Labels apply to their aerial-image years, and matched Landsat scenes must be within 45 calendar days in the same year. The existing Landsat seasonal archive already restricts acquisitions to ±21 days of the regional reference season. Each photo label remains restricted to its aerial-image year.

## Deliverables

- [Annotation policy](annotation_policy.json)
- [Dated cover fractions](dated_cover_fractions.csv)
- [Projected annotation polygons](annotations.gpkg), with one layer per UTM CRS
- [Field-anchor support and distances](field_anchor_support.csv)
- [Seven photo-screened annual observations](photo_supported_observations.csv)
- [Purity and shift support](purity_support.csv)
- [All planned contrasts and statuses](separability.csv)
- [Actual test memberships and spectra](test_memberships.csv)
- [Verification](validation.json) and [provenance](provenance.json)

Review sheets pair the original aerial view with the exclusion overlay. Cyan marks the cell, orange marks unknown cover, and magenta marks known other cover.

- [Sheet 1](annotation-review-01.png) — Front Range open vegetation and rock
- [Sheet 2](annotation-review-02.png) — Gunnison rock, Cascades open vegetation, Yellowstone drainage edge
- [Sheet 3](annotation-review-03.png) — Yellowstone open vegetation and substrate
- [Sheet 4](annotation-review-04.png) — Yellowstone substrate and California cases
- [Sheet 5](annotation-review-05.png) — California track, unresolved vegetation, conifer and aspen examples

## Verification and reproduction

Nine focused tests pass. They cover area conservation, unknown/other priority, dated exclusions, 0.6 m boundary uncertainty, global shifts, year/date matching including fractional-second timestamps, correct overlay holes, stale-checkpoint rejection, and exact statistics checked against the package implementation. Real-data checks confirm 900 m² class-area totals, the frozen policy and fraction hashes, source aerial checksums, same-scene test membership and unique footprint units.

The JSON policy is the regeneration source. Use the existing geospatial environment from the repository root.

~~~bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_photo_annotation.py --annotate
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/publication_figures/landsat_photo_annotation.py --test
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_landsat_photo_annotation.py
~~~

The next reference work is an independent review of the provisional herbaceous/substrate labels and additional complete-footprint labels for the three unresolved vegetation classes. Multiple distinct patches with matched class support are needed for a useful test. 
