# Expanded HLS results and method comparison

19 November 2026. The working cohort is nominal-footprint >=95% cover; the added
120 m source-area gate is now a sensitivity. This restores the original question
of reference PFT cover on a 30 m HLS cell. It does not assert that resampling has
no mixing effects. Four additional shrub patches and one exposed-rock patch were
reviewed by cover before their HLS spectra were retrieved. The nominal cohort
increased from 382/19 cells/patches to **496/24**. All stages are preserved.

## Current Figure 4 numbers

| PFT | Cells | Patches | NPC supported/testable pairs | Held-patch recall | Mean pairwise balanced accuracy |
| --- | ---: | ---: | --- | --- | ---: |
| Deciduous | 77 | 5 | 1/4 | 80% (4/5) | 98.2% |
| Evergreen | 110 | 3 | 0/4 | 100% (3/3) | 98.2% |
| Herbaceous | 99 | 5 | 1/4 | 100% (5/5) | 97.5% |
| Woody shrub | 165 | 7 | 3/4 | 86% (6/7) | 93.9% |
| Non-vegetated & dead | 45 | 4 | 1/4 | 75% (3/4) | 100% |

All ten exact pooled NPC contrasts are testable. Three meet the current ten-pair
Holm criterion: deciduous/shrub (adjusted p .022727), herbaceous/shrub (.012626),
and shrub/non-vegetated (.024242). The class rows share contrasts and must not be
counted as 20 separate tests. The original NPC statistic, spatial patch units,
minimum support and multiplicity family are unchanged. There are still no
supported region-blocked contrasts; pooled region/season exchangeability is a
strong assumption. No causal or geographically general PFT mechanism is inferred.

Five-class held-patch prediction is correct for **21/24 patches (87.5%)**. Each
patch is excluded in full from training once. Every class exists in training for
every held-patch evaluation. Secondary pixel predictions are retained but do not
increase independent test support. Held-region predictions retain explicit
training-class support flags; single-region classes still do not have ordinary
held-region generalization estimates.

## What the method comparison changes and does not change

The additional predictive measure is binary **balanced accuracy** for each PFT
pair: mean recall of the two classes, so chance is 50% even when patch counts
differ. It uses the same fixed training-only StandardScaler and balanced logistic
classifier C=1 in a fresh whole-patch leave-one-out run for each pair. Every patch
contributes once per applicable pair. Pairwise BA averages 97.6% over ten tasks.
The per-class column averages its four pair scores; min/max and every pairwise
prediction are archived. These are point estimates, not a significance test,
uncertainty interval, a replacement for NPC evidence, or an independent repeat.
No classifier/feature/threshold was selected to maximize these scores. Figure 4
keeps the existing NPC supported counts, rather than substituting a favorable
new metric for the other sensors' different statistical summaries.

The full-source-area sensitivity now has 161 cells in 13 patches and no supported
pooled NPC contrasts. It has one non-vegetated patch, so five-class holdout
accuracy is unavailable (10/12 supported targets are correct; this is not an
all-class rate). This sensitivity remains visible: conclusions depend on the
reference definition and pooling, not just the reflectance product.

## Reproduce

```bash
.venv/bin/python examples/publication_figures/landsat_hls_method_comparison.py
.venv/bin/pytest -q tests/test_landsat_hls_method_comparison.py
```

Inputs are the immutable expanded HLS tables from the sibling
`hls-l30-expanded-references/`. Both nominal-primary and source-support-sensitivity
folders retain patch medians, all NPC p-values and unavailable statuses, five-
class and pairwise held-patch predictions, class support, estimates and numeric
figure inputs. `analysis_design.json` declares the comparison; `manifest.json`
hashes input tables, reference provenance, code and outputs. Analyses read compact
inputs in place and need no raster/network access.

All labels remain provisional single-interpreter photo/structural references.
Older evergreen lidar is not current PFT truth. Data collection and definitions
have been amended after earlier exploratory results; this is not preregistered
confirmation. Current-family Holm correction does not control all historical
looks. More classes in common regions/seasons and independent reference review
are still needed for stronger ecological transfer claims. No previous run is
erased, and poor-fitting accepted references remain in the analysis.
