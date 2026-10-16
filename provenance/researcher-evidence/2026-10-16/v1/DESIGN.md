# Fixed additions after evidence audit

2026-10-16; analysis of an extensively explored dataset, not preregistered confirmation.
Only the five recorded researcher cover categories enter new analysis.
P129 and all previous outputs remain immutable. All prior packet hashes will be
verified before and after execution. Reuse valid effects, uncertainty, mixtures,
model predictions and permutation ensembles rather than refit them.

## Audit findings before new fits

Five-class single-coordinate recognition already exists: the prespecified
balanced-prior nearest-training-mean rule, per-class recall, all 20 outer domain
cases. It was inadequately emphasized in the previous narrative; summarize it
rather than substitute a new optimized rule. All ten whole-spectrum contrasts,
40 acquisition-matched cohorts and max-T wavelength evidence already exist.

Missing: equal-size random subset controls for the complementary selector;
matched PCA recognition; consistent identity-weighted/nested full-spectrum
recognition for year targets; explicit class-level recognition/abundance links;
structured PASS/FAIL/NOT TESTABLE and hostile-review matrices.

## Bounded new recognition controls

Reuse the same six new-polygon/site outer folds and the exact three inner
StratifiedGroupKFold splits, including the original per-case seed. For five
fixed random seeds (0..4), generate a uniform random permutation of all 360
usable coordinates, independent of spectra and labels. Prefixes of length
1,2,3,5,7,10,20,50,100 give nested random subsets. Each replicate tunes logistic
C in [.1,1,10] on the same inner folds as the selector, independently at each
budget; no choice among random seeds. Compare all five seeds and their mean
against the already validated selector. Regularized full-spectrum/OLI baselines
are already available. Add train-only StandardScaler + PCA20/PCA50 + the same
nested logistic tuning (unweighted annual-row PCA fit, balanced identity-weighted
scaling and logistic fit). PCA is a fixed sensitivity, not selected by outer score.

Persist each case separately with code/data identity and output hashes; restart
reuses valid checkpoints. No source spectral arrays are copied to provenance.
Save feature indices, tuning scores, group memberships, coefficients/scales,
per-identity correctness and metrics. Random-seed ranges are Monte Carlo variation,
not confidence intervals. Conditional paired accuracy intervals resample target
GlobalIDs (stratified by class), holding fitted rules fixed; overlapping outer
training folds do not supply independent geographic replication.

## Temporal recognition

Apply full-NEON and OLI nested weighted logistic to two global-year folds and six
complete-pair NIWO training-year/identity folds (three target folds x two training
years); evaluate both acquisition years of each paired target set using the same
model. All target IDs are absent from training. C chosen from three inner grouped
folds; no coordinate selection. Static retrospective category labels and site/year
confounding prohibit claims of validated annual biological change. These are
controlled image-year sensitivities. No synthetic temporal rows treated as new plants.

## Synthesis additions without new abundance fitting

Recalculate macro RMSE, absolute/relative ridge gains, paired bundle uncertainty,
prior skill, every class/fraction/detection and ambiguity result from canonical
saved predictions/tables. Add per-class candidate-library fraction-range summaries
from saved MESMA fits if available, then relate these descriptively to recall,
RMSE, false detection and low-fraction misses (only five categories, not a
population correlation hypothesis test). Explicitly audit the fraction grid:
no pure/high-end claim beyond its actual support. Reconstruction and fraction
error remain separate axes. No field fractions/purity truth are invented.
