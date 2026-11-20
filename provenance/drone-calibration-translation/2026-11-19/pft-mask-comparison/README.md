# Translated PFT information: unmasked null versus 10% mask

The results do not show a consistent loss of PFT information after masking. Effects are mixed; three calibration sites provide limited independent replication.

## Identifiability

| Pixel population | Evaluation | Unmasked BA | 10% BA | Change (percentage points) |
|---|---|---:|---:|---:|
| shared_pixels | held_out_site | 36.4% | 38.1% | +1.66 |
| shared_pixels | unseen_polygon | 61.5% | 60.5% | -0.98 |
| retained_pixels | held_out_site | 33.9% | 38.2% | +4.24 |
| retained_pixels | unseen_polygon | 58.8% | 60.0% | +1.14 |

Balanced accuracy is the mean of five class recalls from pooled out-of-fold predictions, not overall accuracy or an equal-site average. All 300 polygons are evaluated once per scheme and arm; every test class is present in training. OLI-like results match OLI-2-like results to the displayed precision.

No paired identifiability loss survives Holm adjustment across the eight prespecified comparisons. Site-level arm-swap tests have only eight possible assignments with three sites, so a one-sided p-value cannot be smaller than0.125. A nonsignificant result does not establish equivalence. Polygon-level swaps additionally assume exchangeability of polygon contributions and remain exploratory because nearby polygons and overlapping training folds can induce dependence.

## Separability

- shared_pixels: per-arm ten-pair Holm supports 8/10 unmasked versus 6/10 masked; joint80-contrast Holm supports 5/10 versus 5/10.
- retained_pixels: per-arm ten-pair Holm supports 8/10 unmasked versus 6/10 masked; joint80-contrast Holm supports 5/10 versus 5/10.

On shared pixels, standardized contrasts decrease for 3/10 pairs and increase for 7/10. Decreases occur for Deciduous/Evergreen, Evergreen/Herbaceous and Evergreen/Woody shrub. No directional effect-loss test survives Holm across the40 prespecified pair comparisons (smallest polygon-swap adjusted p approximately0.052). Counts of significant category differences are not themselves a test of whether masking changes separation.

## Class recalls: shared pixels, OLI-2-like

| PFT | n | Held-polygon unmasked | Held-polygon10% | Held-site unmasked | Held-site10% |
|---|---:|---:|---:|---:|---:|
| Deciduous | 12 | 58.3% | 58.3% | 58.3% | 58.3% |
| Evergreen | 176 | 64.2% | 66.5% | 43.8% | 46.0% |
| Herbaceous | 46 | 50.0% | 47.8% | 26.1% | 28.3% |
| Woody shrub | 40 | 42.5% | 37.5% | 0.0% | 0.0% |
| Non-vegetated & dead | 26 | 92.3% | 92.3% | 53.8% | 57.7% |

Woody-shrub held-site recall is0% in both arms. Thus overall recognition remains limited even where masking improves the mean score.

## Cohort, coverage and design

Original302 polygon footprints contain 200,363 indexed pixels. Two polygons have zero complete five-band valid pixels in both arms; neither is a mask-only dropout. The matched cohort is300 polygons: Deciduous12, Evergreen176, Herbaceous46, Woody shrub40, Non-vegetated/dead26. There are no overlapping indexed polygon pixels.

Complete five-band labelled pixels: unmasked 195,849; mask10 189,178; shared 188,336. These counts concern labelled footprints, not the whole scene. Both analyses keep the same polygon IDs. Shared-pixel medians use identical exact row/column sets. Retained-pixel medians use each arm's available pixels.

PFT annotations are the original calibration polygon labels. Spectra are polygon medians in fractional physical-reflectance units, without sum normalization. Separability uses the existing site-blocked whole-polygon label NPC kernel with9,999 synchronized draws, equal discrete band weights, ten-pair local Holm and joint80-contrast Holm. Effect change uses site-adjusted RMS standardized coefficients with paired whole-polygon arm swaps, plus exact whole-site swaps.

Classification uses training-only StandardScaler and balanced logistic regression, C=1, with fixed five stratified polygon folds and three leave-site-out folds. Fold memberships are identical between arms. There is no feature selection or hyperparameter tuning on test data. Correction models are fit separately for each site; held-site evaluation refers to classifier transfer after site-specific correction, not an entirely frozen correction pipeline applied to an unseen site.

The contrast includes changes in fitted SCS+C and BRDF parameters, and in the retained-pixel analysis also changes in pixel composition. It is not a mask-only causal experiment. Ruby's unmasked reference remains failed BRDF QA; all products retain conditional, unverified radiometry. Same-site spatial dependence, three-site scope and lack of independent external reflectance validation limit generalization. Figure4 and uploaded datasets were not changed.

## Reproduce

```bash
MPLCONFIGDIR=/tmp/spectralbridge-mpl OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python examples/compare_drone_mask_pft_information.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/summarize_drone_mask_pft_information.py
```

`analysis_policy.json` was frozen before test results. `manifest.json` records input/label/code and output hashes and software versions. Completed analytical outputs are reused only after hash checks. The internal null arm is serialized as `unmasked` so CSV readers do not treat it as missing. Full polygon spectra/coverage, folds, predictions, per-class results, effect/p-value tables and site-specific scores accompany this report.
