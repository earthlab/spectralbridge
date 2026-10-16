# Researcher-category spectral information and synthetic abundance

Only the five recorded cover_category classes are primary. The earlier taxonomic grouping and reports are historical, preserved and excluded from these conclusions.

## Main answer

The five researcher categories contain useful spectral signals, but their predictive difficulty is uneven. Full-NEON nested logistic balanced accuracy is 85.2% on new polygons and 73.8% on held sites; synthetic OLI gives 66.8% and 57.7%. All scores are conditional on these labelled source populations, not field deployment guarantees.

Supervised regression improves the controlled abundance benchmark. Ridge reduces mean-fold class-balanced NEON fraction RMSE from MESMA 0.359 to 0.216 on new-polygon parents, and from 0.362 to 0.269 on held sites. This is known synthetic mixing-weight recovery, not independently validated field cover.

The proper-training-mean fraction control (no spectra) has RMSE 0.309. Ridge improves on it for new-parent and held-site targets, but its global-year mean RMSE 0.311 does not improve over the prior control 0.309. MESMA is worse than that control in the primary familiar/held-site benchmark. Gains over MESMA alone are therefore not enough to establish transferable spectral skill.

## Where is the information?

The atlas has 3,600 pair/wavelength records: every one of ten category pairs at 360 supported NEON coordinates. Full-cohort max-T/Bonferroni evidence, training-only effects, held-out prediction and stability remain separate fields. OLI locations use exact configured centers/FWHM after verifying rounded export labels. Peaks below are descriptive outer-evaluation summaries, not operational feature selections.

| Researcher-category pair | Descriptive best worst-site wavelength | Minimum held-site BA |
|---|---:|---:|
| Deciduous / Evergreen | 1150 nm | 63.8% |
| Deciduous / Woody shrub | 2025 nm | 60.2% |
| Evergreen / Herbaceous | 1780 nm | 81.6% |
| Evergreen / Woody shrub | 1690 nm | 76.0% |
| Herbaceous / Woody shrub | 1320 nm | 47.6% |

Herbaceous versus Woody shrub is the clearest weak single-coordinate contrast; its worst-site score stays below chance even at its best observed worst-site coordinate. This is evidence about the prespecified univariate mean-based rule, not proof that no nonlinear information exists. Evergreen/Herbaceous and several vegetation-versus-background contrasts are stronger. The complete atlas and spectral_intervals.csv retain every coordinate and overlapping review tag; some maxima occur near segment boundaries and are not universal recommended bands.

## Which categories drive recognition errors?

| Researcher category | New-polygon recall | Held-site recall | Held-site precision |
|---|---:|---:|---:|
| Deciduous | 78.4% | 67.3% | 69.6% |
| Evergreen | 95.2% | 94.2% | 87.7% |
| Herbaceous | 87.5% | 69.6% | 70.0% |
| Non-vegetated & dead | 92.4% | 91.7% | 77.8% |
| Woody shrub | 72.5% | 46.3% | 67.3% |

Evergreen and Non-vegetated & dead are recognized more consistently than Woody shrub. A useful background label is still not a pure physical material. Every confusion cell and per-class FPR/FNR is saved; temporal whole-spectrum class rates/confusions reuse the prior validated researcher-only logistic baseline and are explicitly marked reused, rather than silently pooled with the new identity-weighted model.

## Redundancy and complementarity

Nested complementary-coordinate mean new-polygon BA is 41.6% with one coordinate, 74.4% with seven, 81.6% with twenty, 83.7% with fifty and 85.2% with the full grid. Held-site values are 60.8%, 70.1%, 73.7% and 73.8%, respectively. The training-only two-percentage-point parsimony rule chooses 50-100 coordinates across folds. This does not prove an optimal sensor or fixed universal saturation point. Correlation clusters and orthogonal residual gains distinguish repeated from complementary training information.

## Abundance improvements, failures and what they mean

All primary methods share 120 proper-training parents, 40 tuning parents and up to60 held-out parents per experiment. Each five-parent bundle supplies170 dependent pair/triple mixtures. Twelve parent bundles, not2,040 independent spectra, define a full test. Ten training experiments yield twelve target sets, including both image years for the paired temporal directions. All model tuning/preprocessing occurs in the appropriate parent role. Fractions are nonnegative and sum to one after explicit projection.

Ridge also outperforms the primary full-NEON gradient booster on average here: 0.216 versus 0.246 on new parents, and 0.269 versus 0.297 on held sites. These are fixed outer comparisons, not a multiplicity-corrected universal ranking. Ridge OLI RMSE is 0.266/0.280; first-derivative ridge is 0.276/0.346, and second-derivative ridge is 0.310/0.360 (new-parent/held-site). Derivatives do not improve this benchmark; shape/PCA/selected-coordinate sensitivities remain fully reported.

The two-stage procedure trades fewer false detections for more missed low fractions; it does not dominate fraction RMSE. For example, Evergreen new-parent false detections at zero fall from ridge26.4% to two-stage10.9%, while low-fraction false negatives rise from61.4% to82.0% at the common .10 fraction cutoff. These conditional source-specific observations are not universal detection limits.

Paired bundle intervals and error-by-fraction/ambiguity tables retain negative results. Ridge improves average held-site error in the high-ambiguity stratum, but not every method/stratum; the moderate stratum can favor MESMA. A learned prior can improve expected fraction error without eliminating another feasible spectral explanation. No reduction of mathematical non-identifiability is established.

## What currently limits abundance?

- Model choice matters: supervised projected regressions substantially improve known-weight recovery under the common design.
- Spectral representation matters: OLI loses some recognition and fraction information; derivatives are not a remedy here.
- Within-class variability/library mismatch matters: known-parent oracle fraction error is near machine precision, while class-reference models are much worse. This is a positive control, not a deployable model.
- Between-class/candidate ambiguity persists: multiple near-fitting class combinations remain, and improvements are not uniform across ambiguity strata.
- Geographic/temporal shift matters: held-site and paired cross-year conditions differ from familiar-parent tests. Three sites and retrospective labels cannot isolate their causes.
- Independent physical truth is the deployment gate: category annotations do not certify pure parents or field fractional cover. No current experiment causally apportions all failure among these factors.

## What to do next

Retain valid repeated observations and metadata; keep complete identity histories in validation. Recover original units/physical coordinates/purity first. Collect independent co-located complete fractions, true absences and low positives; cross contemporary annotations with sites and years. Replicate actual sensor/footprint comparisons. More generated mixtures or another complex model cannot replace independent biological and physical truth.
