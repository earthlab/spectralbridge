# Researcher category results

The analysis now uses the source `cover_category` field, not a species-to-PFT lookup. The exact classes are Deciduous, Evergreen, Herbaceous, Non-vegetated & dead, and Woody shrub. Non-vegetated & dead is a mixed cover/dead-material comparator; the five classes are researcher cover classes rather than five mutually exclusive physiological trait definitions.

All 3,639 source polygon identities were included, yielding 4,807 polygon/year spectra; 1,143 identities lack a species name. The source was read in place; original inferred-label outputs are preserved. NIWO contributes 2020 and 2023; WREF and YELL contribute 2023.

All 40 acquisition-matched class-pair comparisons are supported by the primary max+integrated NPC test after Holm correction across the 40-comparison family (adjusted p = 0.004 throughout). Maximum and FPCA sensitivities also support all 40; energy supports 38/40. All 40 site/year-only comparisons are supported by NPC in their separate sensitivity family.

The identical primary p-values are a Monte Carlo resolution floor: 9,999 permutations plus the observed statistic give minimum raw p = 0.0001; Holm yields 0.004 here. They do not mean the effects are equal or have precisely known probabilities. Corrected significance also does not imply nonoverlapping spectra or accurate assignment of an unknown polygon.

## Where methods disagree

- WREF 2023, Deciduous / Woody shrub: energy adjusted p = 0.2235, despite primary/max/FPCA support. Distribution-wide evidence is less robust for this comparison; a mean/projection contrast does not require the energy statistic to agree.
- YELL 2023, Deciduous / Herbaceous: energy adjusted p = 0.1182, despite primary/max/FPCA support. Distribution-wide evidence is less robust for this comparison; a mean/projection contrast does not require the energy statistic to agree.

## Magnitudes and interpretation

The wavelength-weighted RMS block-adjusted contrast divided by the fixed pooled within-block spectral SD ranges from 0.336 to 1.795 across matched comparisons. This descriptive standardized curve magnitude is not a classifier score or an independent effect confidence interval. `methods_and_effects.csv` records every value.

Smallest standardized contrasts in this dataset:

- WREF 2023, Deciduous / Woody shrub: RMS standardized contrast 0.336; matched n=204/138.
- YELL 2023, Herbaceous / Woody shrub: RMS standardized contrast 0.352; matched n=303/218.
- WREF 2023, Herbaceous / Woody shrub: RMS standardized contrast 0.409; matched n=81/122.
- NIWO 2023, Deciduous / Woody shrub: RMS standardized contrast 0.458; matched n=107/229.
- NIWO 2020, Deciduous / Woody shrub: RMS standardized contrast 0.496; matched n=136/241.

## Limits on scientific claims

The defensible result is conditional spectral differentiation among the sampled researcher-labeled polygon mixtures. Exact histories account for shared acquisition exposure, not all spatial, canopy, substrate, illumination or compositional confounding. Polygon IDs are sampling units; herbaceous patches are not individual plants. Repeated years are analyzed separately and are correlated replications where IDs recur. Test exchangeability remains an observational assumption.

Researcher labels vary within some species names, so the earlier deterministic species/PFT aliasing result cannot simply be transferred. This does not establish a fully adjusted causal PFT effect; missing species, mixed cover and sparse taxon/class cells remain. Generic P117 simulations need not be rerun for a label adapter and do not establish actual-data exchangeability. Classification, equivalence and transfer to new regions require separate validation.

Use `category_spectra.pdf` to see typical curves and within-class spread, and `../simultaneous_envelopes.pdf` for matched contrast localization. The former uses full cohorts and does not reproduce the matched estimator. Both retain wavelength gaps. `../RESULTS.md` contains the full primary table.
