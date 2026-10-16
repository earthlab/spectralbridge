# Researcher-category design and execution amendments

15 October 2026; seed 20261015. Initial model grids and roles were fixed before new outer evaluations; synthesis additions are recorded below. This is a structured reanalysis of extensively explored data, not an independently preregistered confirmation.
The canonical field is cover_category: Deciduous, Evergreen, Herbaceous,
Non-vegetated & dead, Woody shrub. Species is provenance only. Historical
species-derived groupings do not enter any new estimator or primary result.

## Observations, scope and reuse

Read the supplied original table in place, verify the existing paired compact
NEON360/undarkened-OLI7 source identities, and retain finite negative values.
No guessed scaling, sensor noise, MicaSense coordinate repair or gap filling.
A GlobalID is a polygon footprint, not guaranteed plant/material purity.
2023/2024 annotations reused across image years are not annual field truth.
Use all 3,639 IDs and 4,807 annual observations where supported.

Reuse the forty researcher-category exact-acquisition-history permutation
ensembles (9,999 synchronized whole-curve shuffles each). Per-wavelength
max-T tail probabilities use their saved null maxima; Bonferroni across forty
pair/cohort contrasts controls the joint declared wavelength/contrast family.
These are full-cohort descriptive inference, NOT training selection evidence.
Training-only effect summaries and predictions are separately marked. Neighbors
are coordinates, never independent biological replicates.

## Single-wavelength discrimination

Ten pairs, every usable NEON coordinate and seven synthetic OLI bands.
Prespecified balanced-prior univariate linear discriminant rule: train class
means and pooled within-class variance; midpoint threshold and direction learned
only on training identities. This deliberately avoids 50,000 tuned classifiers.
Report standardized mean and robust median/IQR effects from training; held-out
balanced accuracy, AUC, sensitivity, specificity and confusion counts. Training
and evaluation weight annual rows by inverse within-role ID frequency. The
robust median/IQR column is an additional unweighted annual-observation
descriptive sensitivity; it is not the primary identity-weighted effect or an
independent-row inferential test. AUC uses
weighted ranks/ties. Conditional uncertainty uses whole-identity accuracy
contributions and/or variation across grouped outer folds, never wavelength
replication. Means, medians and effects are not chosen on test performance.

Use existing three stratified identity folds, three whole-site holds and two
global year holds, purging entire IDs. Temporal interpretation additionally uses
three complete-pair NIWO identity folds in both training-year directions: other
identities train in one year; the same target IDs are evaluated in both years.
All five classes require >=10 train IDs and >=3 target IDs; save failures.
Global year holds confound site composition and annotation truth remains static.

## Complementarity and stability

Nested three-fold identity CV fits a fresh orthogonal residual forward-selection
path inside each inner training set. At each step choose the coordinate with
largest balanced one-hot response residual gain after orthogonalizing earlier
coordinates. This is an explicit greedy training-fit criterion, not an optimal
sensor or a test-data ranking. Budgets: 1,2,3,5,7,10,20,50,100,all360 and OLI7.
Choose regularized logistic C in [0.1,1,10] by inner balanced accuracy for each
budget; refit the selector/model on outer training only. Evaluate new polygons
and held sites; preserve selected paths, coefficients, tuning scores/memberships.
Training-only correlation matrices and hierarchical |correlation| clusters show
redundancy. Selection frequencies reflect six observed outer training domains,
not selection probabilities over geographic populations.

A descriptive transfer score is max(0,2*minimum held-site BA-1), multiplied by
cohort effect-sign consistency. It rewards the weakest observed site and does
not claim validation elsewhere. Keep every domain value visible. Report site
variance, within-pair wavelength-rank correlations, both-year NIWO changes,
sign consistency and selection frequency separately. Tags use declared review
aids: consistently informative = minimum held-site BA>=.70 and sign agreement=1;
site-specific = site max BA>=.75 and range>=.15; year-sensitive = paired target
BA change magnitude>=.10; statistically different/poor prediction = any joint
adjusted p<=.05 with mean new-ID BA<.60. Other cases remain unresolved/unstable.
Tags overlap and thresholds are review aids, not universal ecological laws.

## Common synthetic abundance benchmark

Use five classes only. Existing group masks define 3 new-ID, 3 site and 2 global
year experiments. Add both NIWO paired-year directions with a fixed stratified
identity split: 60% proper parent pool, 20% tuning, 20% held-out; same target IDs
and fractions in both image years. This is a controlled one-split temporal
sensitivity, distinct from the three-fold single-wavelength temporal estimates.

Within each role sample disjoint bundles of five parents (one distinct GlobalID
per class), with no ID reused in another bundle or role. Choose one earliest
available observation per parent within that role/year. Proper training: 24
bundles (120 parents); tuning: 8 (40); test: up to 12 (60), limited explicitly by
rarest class. Each bundle generates the existing 170 pair/triple-grid mixtures.
All methods receive the same parent pools and exact mixtures. Save all parent,
bundle, fraction and role keys. Mixture rows from one bundle are dependent;
499 paired bootstrap draws resample test bundles, not synthetic rows. Inferences
are conditional on this finite parent budget. Record training size, not just
thousands of generated spectra. Test 8/16/24 training-bundle learning curves for
linear/PLS full-NEON models as a training-diversity sensitivity.

Primary comparison, full NEON and OLI:
1. exact FCLS with five training-class medoids;
2. existing exact active-face MESMA, EAR 3 candidates per class, <=3 components;
3. ridge multi-output regression, alpha [.1,10];
4. PLS regression, 5/15 components;
5. random forest, 100 trees, depth 12/unlimited, leaf minimum5;
6. multi-output histogram gradient boosting, 80 iterations, 7/15 leaves,
   64 bins, L2=1, no automatic row-level validation/early stopping;
7. two-stage class presence logistic followed by conditional ridge fractions,
   tuning presence cutoffs [.1,.3,.5,.7,.9] on tuning bundles only.

Ridge/PLS sensitivities: weighted unit-norm shape, disconnected first/second
wavelength derivatives, PCA20, training-selected complementary7/20, full and
OLI. All learned scalers/PCA/PLS/selectors use proper training only. Fixed
preprocessing alternatives are reported, not selected by outer scores.
Continuum removal is not adopted without a defensible continuum/purity model.
Ubiquitous exact zeros make arbitrary log-ratio zero replacement unjustified;
use explicit Euclidean simplex projection for supervised predictions instead.
A neural network is not initially justified by only120 independent training
parents per fold; synthetic rows do not create biological replication.

Tuning minimizes class-balanced fraction RMSE on parent-disjoint tuning mixtures.
Project fractions nonnegative/sum-one; preserve raw constraint violations too.
Save class bias/MAE/RMSE, positive-only and <=.10 errors, calibration slopes,
false presence at zero, false absence and detection versus fraction, all method
predictions and bundle uncertainty. A common class-mean reconstruction residual
is comparable across methods; retain MESMA native residual separately.

Ambiguity: existing MESMA near-solution fraction range at .01 training-RMS-scaled
spectral tolerance. Low <.10, moderate [.10,.30), high >=.30 maximum class range.
These are declared algorithm/library diagnostics, not physical uncertainty.
Stratify all methods on the SAME test ambiguity bins. An oracle using the actual
five test parents checks solver/linear-model positive control; it is unavailable
at deployment and must never be called field validation. Compare conditional
model gains, sensor loss, parent diversity and held-site/year penalties without
claiming a causal variance attribution. Missing independent fractions remains a
separate field-validation block even if synthetic scores improve.

## Methods grounding

Reuse earlier permutation/observational/MESMA methodology and limitations.
Official grouped CV: https://scikit-learn.org/stable/modules/cross_validation.html
PLS: https://scikit-learn.org/stable/modules/generated/sklearn.cross_decomposition.PLSRegression.html
Multi-output: https://scikit-learn.org/stable/modules/multiclass.html#multioutput-regression
Histogram boosting: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html
Simplex projection sorting algorithm: Duchi et al. (2008),
https://doi.org/10.1145/1390156.1390191 ; author manuscript
https://web.stanford.edu/~jduchi/projects/DuchiShSiCh08.pdf .
Implementation choices above are explicit source-specific adaptations.


## Explicit execution/synthesis additions

To satisfy the training-only evidence requirement separately from full-cohort
inference,230 eligible outer-training pair/cohort contrasts were evaluated with
1,999 blocked max-T shuffles each. Bonferroni spans eligible contrasts separately
inside each outer-training design. Across-design minima and support counts are
descriptive: overlapping folds are not independent replications. No outer target
labels or values enter these tests; no p-map chooses predictive features.
The implementation reproduces the existing blocked maximum engine on a fixed
synthetic regression fixture. Full-cohort evidence remains separately named.

The training-only parsimony synthesis rule chooses the smallest NEON budget with
inner BA within .02 of the best inner score and evaluates its already-saved outer
model. It never chooses a budget from outer scores and is not an optimized sensor.

An independent audit found a raw-stage FCLS/MESMA prediction-alias collision.
Canonicalization reconstructs distinct method-named exports from immutable owned
fraction archives and verifies every saved RMSE. Models/metrics did not change;
raw aliases are noncanonical intermediates. The regression contract protects
unique baseline export paths. Run summary/finalization before consuming exports.

OLI export labels are rounded to nanometers. Existing coordinate validation
permits this rounding; response annotations use exact packaged centers/FWHM.
No input bands were relabelled or values convolved again for this atlas.

Outer identity memberships reuse the existing fold seed20261014. Case-level/parent/permutation RNGs use20261015 plus stable name hashes. This distinction is recorded in configuration.json. Prior exploration of this same dataset limits confirmatory interpretation; nested grouping prevents within-experiment leakage, not all design adaptation to a known dataset.


A no-spectrum training-prior control was added at the interpretation audit to
address whether regression merely learns the synthetic fraction distribution.
Its constant composition is the proper-training mean fraction vector; no target
values define it. All methods are compared with its MSE skill as well as with
MESMA. This is an explicit diagnostic addition, not a test-tuned predictor or
claim of preregistration. The synthetic fraction grid is common by design;
stronger field-prior transfer remains unvalidated.
