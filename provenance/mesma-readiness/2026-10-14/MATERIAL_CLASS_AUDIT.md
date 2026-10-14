# Material class audit

The library has 3,639 GlobalIDs. A polygon identity is not necessarily an individual living plant, a pure canopy or a physically pure material. Species-null polygons remain through researcher labels. Preserve species, name-derived PFT and researcher categories as different annotation systems.

| label | unique_GlobalIDs | sites |
| --- | --- | --- |
| Deciduous | 442 | 3 |
| Evergreen | 1363 | 3 |
| Herbaceous | 677 | 3 |
| Non-vegetated & dead | 414 | 3 |
| Woody shrub | 743 | 3 |

## Existing physical hints, not invented classes

| field | label | unique_GlobalIDs | sites |
| --- | --- | --- | --- |
| cover_subcategory | Bare | 44 | 3 |
| cover_subcategory | Dead | 165 | 3 |
| cover_subcategory | Forb | 51 | 3 |
| cover_subcategory | Grass | 160 | 3 |
| cover_subcategory | Mixed Dead / Bare / Rock | 71 | 3 |
| cover_subcategory | Mixed grass & forb | 465 | 3 |
| cover_subcategory | Rock | 119 | 3 |
| cover_subcategory | Woody shrub - Broadleaf | 547 | 3 |
| cover_subcategory | Woody shrub - Needleleaf | 48 | 2 |
| cover_subcategory | (not recorded) | 1969 | 3 |
| dead_subcategory | Dead - Debris | 1 | 1 |
| dead_subcategory | Dead - Herbaceous | 18 | 2 |
| dead_subcategory | Dead - Woody downed | 62 | 3 |
| dead_subcategory | Dead - Woody standing | 119 | 3 |
| dead_subcategory | (not recorded) | 3439 | 3 |

The name-derived PFT experiment covers woody taxa: all 677 Herbaceous and all 414 Non-vegetated & dead identities are UNASSIGNED in that crosswalk. It therefore cannot substitute for a full material library. Some assigned PFTs span researcher cover categories; pft_by_cover_category.csv records the exact cross-tabulation.

The broad Non-vegetated & dead category is physically heterogeneous and cannot be treated as a single clean soil/NPV endmember. Rock (119 identities) and Bare (44) exist as explicit labels. Bare is a substrate annotation, not verified mineral soil. Dead standing/downed woody annotations exist; 71 polygons explicitly say Mixed Dead / Bare / Rock. No fraction or purity measurement resolves those mixtures. A Bare record also has a dead-herbaceous subtype: conflicting detail needs review. The five inferred PFT labels are trait annotations, not independent material spectra.

The controlled material experiment conservatively uses concordant category/subcategory labels. Generic Dead records use their recorded dead_subcategory. Fifteen records with missing cover_subcategory but recorded dead subtypes are kept in the inventory and outside this conservative material benchmark pending annotation reconciliation; they are not declared physically unknown or silently merged. Rare Dead - Herbaceous records in the concordant subset fail some/all support gates. Original metadata and fold-support tables expose these choices. The combined researcher category is tested separately to show consequences of a broad hierarchy, not adopted as an operational material.

Measured water, snow, litter, pure shade and verified soil are absent as distinct validated classes. Dead - Debris has one annotated identity and does not establish a litter library. The shaded field describes 206 shaded, 53 mixed, 1,872 sunlit and 1,508 unspecified polygons; it is not a measured black-shade spectrum. Do not rename canopy shadow as a new material or use zero as empirical shade truth.

Recommended hierarchy: retain broad vegetation types as labelled canopy proxies; separate annotated Rock, Bare, woody standing/downed and dead herbaceous where supported; retain mixed/uncertain annotations explicitly. Establish independently measured purity and background fractions before ecological material abundance mapping. Species-level readouts require their own sampling/validation and cannot inherit a PFT result.
