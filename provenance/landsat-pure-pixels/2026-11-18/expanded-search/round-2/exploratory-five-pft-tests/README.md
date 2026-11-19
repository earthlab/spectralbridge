# Exploratory Landsat separability and identifiability

Provisional five-class analysis, 19 November 2026. Neither independently validated accuracy nor a change to Figure 4.

Combined cohort: 481 unique 30 m cells, 20 spatial patch groups, 5 PFT labels. Evergreen consists of 88 structurally screened candidates with older lidar; the other 393 are single-interpreter photo references.

## Primary results

Leave-one-patch-out identification correctly predicts 19/20 patch medians (95%). Each patch is predicted once; all pixels from that patch are excluded from training. Models are trained on equally weighted patch medians, with balanced class weights. Pixel predictions are secondary descriptive outputs, not extra independent test replicates.

| PFT | Correct held-out patches | Recall |
| --- | ---: | ---: |
| Deciduous | 5/5 | 100% |
| Evergreen | 3/3 | 100% |
| Herbaceous | 4/5 | 80% |
| Woody shrub | 3/3 | 100% |
| Non-vegetated & dead | 4/4 | 100% |

The geography-only leave-patch-out majority baseline correctly predicts 11/20 patches, without using spectra. Classes and geography are strongly associated.

Exact pooled NPC separability: 0/10 contrasts supported after Holm correction. Adjusted p-values range from 0.0794 to 0.1250. This is insufficient evidence for all-pair separability, not proof of spectral equivalence. With only 3–5 patches per class, the smallest attainable exact two-sided p-value across these pair designs exceeds the first Holm threshold of 0.005; adding adjacent pixels does not improve permutation resolution.

Within-region tests have mixed-class support for only 2/10 contrasts, and none passes correction. Those tests restrict permutations by region; they do not fully control acquisition date or scene. The pooled tests assume whole-patch exchangeability across regions/seasons, a strong and potentially invalid assumption.

## Geographic transfer

Deciduous, evergreen and shrub each occur in one region. Holding that region out removes the class from training entirely, so regional-transfer recall for those classes is unavailable. Zero predictions for an unseen training class are retained in the audit, but must not be described as an ordinary measured class-transfer accuracy. The raw overall leave-region-out score conflates unsupported classes and supported predictions; consult support flags rather than reporting its overall percentage as five-class transfer performance.

## Sensitivity analyses

Separate folders repeat the entire analysis for the 5 m registration screen, preferred aerosol retrieval only, shared B1–B5, and raw B1–B7 reflectance. These are diagnostics, not independent confirmations or a basis for selecting whichever result looks best. `analysis_overview.csv` reports the resulting patch counts and performance. Some restrictions remove whole patches; track the denominator.

## Reproduce and interpret

Run from repository root with the existing environment:

```bash
.venv/bin/python examples/publication_figures/landsat_exploratory_pft_tests.py
.venv/bin/pytest -q tests/test_landsat_exploratory_pft_tests.py
```

Inputs are read in place from round-2 primary references and the evergreen candidate table. `manifest.json` records their hashes, code and output CSV checksums. `combined_provisional_cohort.csv` preserves both reference bases rather than relabeling structural occupancy as photo-cover purity. For normalized analyses, divide each pixel by its B1–B5 sum before taking patch medians. Exact synchronized max/integrated NPC statistics reuse the existing annotation helper, with equal band weights. Holm correction includes all ten planned pairs separately for each scope/variant. Identification uses StandardScaler and balanced logistic regression (C=1), fitted only to training patch medians; no tuning on held-out data was performed.

This is the same NPC statistic family used previously, but spatial patch units and the current cohort differ from archived NEON/drone protocols. Percentages should not be presented as directly comparable cross-sensor validation. Label source, season and geography are confounded; independent reference validation and more distinct matched-region patches remain necessary.
