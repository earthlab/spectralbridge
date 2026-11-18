# Landsat pure-pixel audit for the five researcher categories

## Literature and decision rule

- Olofsson et al. (2014) recommend reference data with adequate spatial and temporal representation of the sampling unit and a response design that assigns reliable reference labels. Here the sampling unit is the native Landsat cell. A field label attached to a smaller patch supplies evidence only for the patch's mapped area. [Good practices for estimating area and assessing accuracy of land change](https://doi.org/10.1016/j.rse.2014.02.015)
- Keshava and Mustard (2002) review how multiple materials produce mixed spectra and explain that the adequacy of unmixing assumptions depends on the scene. Small (2004) examines the spectral mixing space of Landsat ETM+. A spectrally extreme or smooth pixel can help find candidates, but assigning these researcher classes using the Landsat spectra and then testing those spectra would select for the outcome. No Landsat reflectance value was used to rank candidates. [Spectral unmixing](https://doi.org/10.1109/79.974727), [The Landsat ETM+ spectral mixing space](https://doi.org/10.1016/j.rse.2004.06.007)
- Landsat Collection 2 Level-2 B1–B7 were decoded with the official surface-reflectance scale and offset. Fill, cloud, cirrus, shadow, snow, saturation in any of the seven bands, and terrain occlusion were excluded using the two QA layers. QA establishes observational usability. Purity was checked separately. [Landsat 9 Collection 2 Level-2 data and QA](https://developers.google.com/earth-engine/datasets/catalog/LANDSAT_LC09_C02_T1_L2)

I used a conservative operational definition of purity for this audit. The site reference must support one researcher category throughout the 30 × 30 m cell and a 10 m margin on each side, with no conflicting reference area, field-date lag of at most 30 days, and independent review of the entire 50 × 50 m reference chip. The date and margin are study choices, neither a universal threshold nor a measured sensor point-spread function. The near-date test used the archived collection date and kept records with unknown dates out of the verification gate. As a separate sensitivity check, I computed the largest area mapped to each category inside the 30 m cell using all dates and zero margin, before imposing recent coverage or independent review. Same-class overlaps were unioned so duplicate geometry could not inflate coverage. “Non-vegetated & dead” is a researcher-defined grouped category. Class purity at that level does not imply a single physical endmember.

## Real-scene audit

The audit uses Landsat 9 scene `LC09_L2SP_034032_20230820_20230822_02_T1` over the Niwot-area field sites. B7 and QA_RADSAT came from the matching [Planetary Computer STAC record](https://planetarycomputer.microsoft.com/api/stac/v1/collections/landsat-c2-l2/items/LC09_L2SP_034032_20230820_02_T1). The polygon audit uses the original Niwot GPKG and merged AOP polygon layer, without the half-diameter shrink. Local 14 August 2023 Goldhill, Gordon and Ruby drone mosaics supplied six-day-offset RGB review context. Drone bounding boxes screen for potential overlap. The review sheet additionally required sampled RGB support over the full displayed window. Gordon RGB was used visually under a display stretch, with no fractional-reflectance interpretation. The audit makes no inference about scenes outside the Niwot Landsat scene footprint.

| Researcher category | Clear, valid cells with this largest mapped class | Max mapped share in any clear cell, 30 m, any date |
| --- | ---: | ---: |
| Deciduous | 139 | 67.9% |
| Evergreen | 337 | 16.6% |
| Herbaceous | 144 | 41.0% |
| Non-vegetated & dead | 130 | 15.4% |
| Woody shrub | 167 | 20.2% |

948 native cells touched archived reference polygons. 917 passed the QA and complete-spectrum gate. 112 of those intersected a drone raster's bounds. The maximum documented **same-category** cover was 67.9% at Landsat row 5002, column 4678 for Deciduous. Unknown area could contain that category, so the measured mapped share is neither a complete composition estimate nor evidence that every cell is mixed. Ten high-ranked cells with usable drone RGB were reviewed as 50 m chips. Roads, canopy gaps, shadow, and transitions between woody and open cover were visible in the shortlist. None justified a full-footprint class assignment. The selected chips cannot rule out suitable cells elsewhere in the mosaics.

## Separability

Zero cells passed the purity gate. The same whole-spectrum nonparametric-combination test used in the NEON sensor audit is wired for seven Landsat surface-reflectance bands with equal integration weights, 9,999 blocked permutations, and Holm correction across tested contrasts. I set a minimum of 10 verified cells per class within mixed spatial blocks, using the earlier audit’s per-class count and requiring at least three mixed 300 m blocks for this pilot. Those blocks are a screening design choice and would need a spatial-dependence check on an eligible cohort.

The real-data support check ran for all ten category pairs. No pair was eligible for the permutation stage, and the results table contains no measured Landsat p-values. A synthetic positive control passed through that stage. The prior centroid-associated Landsat spectra in the figure remain descriptive.

## Outputs and follow-through

- [Footprint audit](footprint_audit.parquet) contains real Landsat B1–B7 reflectance, grids, QA, fine-reference coverage, and polygon identifiers for all 948 screened cells.
- [Verified cohort](verified_pixels.parquet) preserves the eligibility schema and currently contains zero rows.
- [Separability outcomes](separability.csv) records support and test status for every pair.
- [Drone review footprints](drone_review_shortlist.geojson) and [RGB chips](drone_review_chips.png) identify ten candidate cells by Landsat row and column. The review export omits the Landsat band values.

The limiting input is a contiguous class reference layer aligned to Landsat, with the surrounding cover independently delineated. Annotate large, contiguous examples of each exact researcher category in the dated drone or NEON imagery using the field polygons as anchors, then review the entire footprint and margin with a second interpreter. The most useful additional sites would provide large patches of the hardest classes and multiple spatial blocks where categories co-occur. Additional scenes can resolve clouds and acquisition timing once those reference patches exist.

## Geographic expansion

The later [regional search](expanded-search/README.md) assembled 51 Landsat cells across five regions with 50 dated aerial contexts, including 2024 acquisitions for Yellowstone and California. The counts and coverage limitations above apply to the initial Niwot scene audit. Quantitative PFT purity remains unverified in the regional candidate dataset.
