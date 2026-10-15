# Information-retention design — fixed questions before new fits

Date/seed: 2026-10-14 / 20261014. No new ML/feature/prototype experiment has
been run at this design stage. Existing empirical inference/mixture/pilot results
are reused without altering their original scope. Implementation smoke/profiling
may reduce a declared computational grid before the full run; record changes
before inspecting held-out performance. Do not change the scientific questions.

## Primary questions (Q1–Q15)

1. What spectral/ecological variation exists?
2. Which biological groups have repeatable differences?
3. Can identity be predicted for observations not used in training?
4. How does prediction change across plant/acquisition/year/site/sensor?
5. Which wavelengths carry transferable ecological information?
6. How much spectral resolution is necessary?
7. Does one representative adequately describe a class?
8. Can an endmember be distinguished from other-class mixtures?
9. Can known fractions be recovered?
10. What fraction is needed for reliable detection?
11. How does OLI reduction change mixture evidence?
12. Can out-of-library observations be recognized?
13. Are predictive/fraction uncertainties calibrated?
14. What does the independent real-Landsat pilot add?
15. Which classes/applications are ready for MESMA, conditional or unsupported?

## Units, common index and QC

Original input is read in place; annual empirical NEON/OLI curves reuse the
verified paired compact tables. Store only a canonical metadata/reference index,
not another pixel matrix. Site/year/GlobalID keys join spectra and exact exposure
histories, species, source researcher categories, inferred PFT, native-grid set
and quality/provenance references. Keep all complete finite stored values,
including finite negatives. No guessed reflectance division or atmospheric-gap
interpolation. All-zero/zero-norm spectra, if present, are explicitly unsuitable
for angle-based prediction and excluded by a documented paired sensor mask;
record counts and identities. Other extremes are retained and traceable.

Observation: polygon/year curve. Independence: GlobalID, with complete history
purged across all years/acquisitions before any training. Classification fitting
uses equal polygon/year observations; uncertainty resamples whole identities.
Inference over site populations is not supported by only three observed sites.
PFTs and researcher categories are separate primary label schemes; species
classification is not silently substituted. Physical-material audits remain
separate and cannot be inferred from a five-class cover label.

## Holdout ladder and support gates

- Three seeded stratified identity folds for plant transfer.
- Every available acquisition/flight considered. Purge all GlobalIDs exposed to
  it, and use the actual held-out flight curves as targets (not an annual median
  combining the held-out flight with other acquisitions). Save unsupported folds.
- Every available acquisition year, with global identity purging. Do not call a
  direction geographic/temporal generalization when class support is absent.
- Every available site; no training observation or identity from held-out site.

Training classes require >=10 unique identities; class-specific test metrics
require >=3. Save all class/fold support counts and roles. Classes absent in
training are open-set, not ordinary closed-set errors. Present but inadequate
training classes are insufficient-support cases, not merged categories. Small
test classes can retain predictions but are not promoted to reliable estimates.
Require at least two evaluable test classes for a multiclass balanced-accuracy
summary; a one-class flight supplies recall/support diagnostics, not a general
separability score. Keep identical eligible target memberships across full NEON, selected bands and
OLI within a comparison. Scores across different holdout types also differ in
population/class support; their difference is not a causal decomposition.

## Predictive model ladder and baselines

Primary: regularized multinomial logistic; PLS-DA; RBF SVM; random forest.
No neural/deep model initially. Include majority, seeded stratified random,
nearest-centroid and/or spectral-angle prototypes. Balanced accuracy, macro F1,
class precision/recall/confusion, raw/calibrated Brier/log-loss/ECE, support counts
and bootstrap intervals take priority over overall accuracy.

All scaling, PLS/PCA, features, tuning and prototypes fit inside training. Use a
small predeclared group-aware inner grid; if support cannot sustain it, use an
explicit fixed setting and report untuned status. Tentative grid for profiling:
logistic C=.1/1/10; PLS components 2/4/8; SVM C=1/10 with scale gamma;
forest 100 trees, minimum leaf 5, depths 8/unlimited. All seeds/configurations
recorded. Classical model comparisons primarily use plant/year/site folds;
all-flight primary diagnostics use logistic to bound cost. Do not rank models
by whichever outer test happened to look best.

SVM probability=True is prohibited: its internal calibration would split rows,
not GlobalIDs. Use decision scores and a separately held-out group calibration
mapping. PLS-DA argmax comes from one-hot response scores; any softmax score
normalization is explicitly a raw score mapping, not an a priori probability.
Class weighting is used where supported and recorded; no synthetic rare-class
oversampling or relabeling to improve scores.

## Calibration and conditional uncertainty

Reserve approximately 20% of training GlobalIDs uniformly, before model choice,
for calibration; the rest is proper training. If class support fails, explicitly
omit calibration/sets rather than leak or force a guarantee. Inner selection
uses only proper training. Temperature scaling (if used) fits on independent
calibration labels and is assessed on outer tests. Thresholds never use the
outer test. For conformal sets, use RAW scores from the model fitted without calibration
labels, not the temperature-scaled scores fitted on those calibration labels.
This avoids reusing labels to fit the conformal scoring function. Use finite-sample higher score quantiles,
with one maximum nonconformity per calibration identity to respect repeated
observations. Report empirical identity/row/class coverage and set size. No
geographic or observational-population guarantee is claimed; explain required
exchangeability and domain-shift failures.

Use 499 seeded whole-GlobalID bootstrap draws for conditional performance and
paired sensor differences. Same draws couple sensor/model comparisons. Intervals
condition on observed sites/classes/support, not a geographic superpopulation.
Avoid treating dependent contrasts, mixture fraction trajectories or pixels as
independent draws.

## Wavelength information and resolution

Primary controlled curve: full common NEON; training-selected 100/50/20/10/7
coordinates; seven synthetic OLI channels. Fixed numbers can be reduced only
for measured computational/support reasons before the full run. Train selection
inside inner CV, not globally. Compare the equally sized seven-coordinate and
OLI representations on identical target observations, especially held-out site.

Use complementary diagnostics: univariate training F ranks (not confirmatory
p-values), fitted logistic coefficients, PLS loadings and, where affordable,
training-internal validation permutation of contiguous wavelength regions.
Record stability/frequency across outer folds and links to existing functional
localization. Do not use outer-test feature importance to select bands.

Call these **training-selected seven wavelengths**, not a proven global optimum.
A comparison with broad OLI responses changes placement, bandwidth, averaging and
selection together; it cannot uniquely attribute a difference to band count or
placement alone. No universal sensor-design conclusion from three sites.

## Domain diagnostics and class representation

Predict site, year (all sites and within NIWO separately) and acquisition using
actual compact observations and identity-held-out splits. Domain predictability
can reflect environment, species, phenology or observation conditions; it is not
proof of instrumental confounding. Keep rare domain labels explicit.

Compare class mean/median/observed medoid, multiple cluster medoids and diversity
prototypes at 1/2/5/10/20/50 where training identities permit. Choose candidates
only inside each fold, with distinct identity provenance. Report class-wise
held-out reconstruction/nearest-class performance and size curves; do not pick
an optimal size from final tests. Reuse EAR/MASA/CoB/IES and coverage/size results
from the prior audit rather than rerunning them for novelty.

## Mixtures, unknowns and real sensors

Reuse full NEON/OLI ambiguity, FCLS/MESMA, fractions, detection and Monte Carlo
coverage. New selected-band counterparts must reuse exact saved held-out parents,
fractions, training memberships and candidate identities; validate a subset
against the previous solver/ledger before complete eligible counterparts.
Different per-representation norms are explicit. Keep two/three-component truth,
shade and thresholds unchanged. No unconstrained clip-and-renormalize solver.

Operational detection rule: estimated fraction >= declared cutoff (default .1,
existing .05/.1/.2 sensitivity); true presence means any positive true fraction.
Class-set error with true fraction >=.1 is a different estimand. Estimate D50/80/95
only if independent-parent support and a defensible curve warrant them; otherwise
save conditional frequencies plus insufficient-evidence status, without extrapolation.

For unknowns, omit an entire class; compare known false rejection and unknown
recall/precision/PR-AUC using nearest-library angle/distance, training PCA-space
novelty, classifier confidence/sets, and existing mixture residual/ambiguity.
Thresholds come from training-only known calibration, never unknown/final tests.
A small residual is explicitly unvalidated membership, including convex-combination
unknowns. Keep actual absent classes separate from artificially rare-class gates.

Do not add empirical unitless real-Landsat SR residuals to an unverified-unit
library. An empirical-residual mixture perturbation is blocked unless scale and
transfer assumptions can be justified. Prior training-acquisition variability
stress remains a sensitivity, not measured sensor noise. The R10C pair provides
radiometric/spatial context, not ecological abundance truth.

## Decision gates and cost

QC/support failures stop affected branches; preserve statuses. Incoherent/mixed
cover labels are not silently promoted to pure materials. Severe ambiguity and
missing independent truth must be reported before optimized abundance claims.
Do not add L1 sparse unmixing under a nonnegative sum-one constraint merely as a
new algorithm (the penalty is constant). Neural models require adequate independent
support and a meaningful question after classical baselines; few sites/material
truth gaps can keep this gate closed even when a nonlinear classifier helps.

Profile a small representative run before large jobs. Original arrays are only
4,807×360 plus seven-band paired summaries; model/provenance outputs should scale
with folds/models, not pixels. Use deterministic seed/config/code/source identities,
atomic fold checkpoints, checksums and meaningful fold/model progress. Never create
an ordinary pixel cache. Final figures and report read tidy result tables; no
manually typed scientific values when machine-readable evidence exists.
