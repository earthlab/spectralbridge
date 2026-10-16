# Can researcher-category fractions be estimated reliably?

The current [three-question validation](index.md#three-distinct-scientific-questions)
adds matched random/temporal recognition and same-candidate abundance controls.
The latter removes the larger-library NEON ridge advantage when reduced to the
exact 15 MESMA parents. Treat the preceding numerical snapshot below as a
preserved companion, with this new capacity limitation.


!!! warning "Controlled synthetic benchmark, not field abundance validation"
    Exact mixture weights are known because observed polygon spectra are mixed
    algebraically. They are not independently measured biological cover fractions.

The canonical benchmark uses only Deciduous, Evergreen, Herbaceous,
Non-vegetated & dead, and Woody shrub. All methods receive identical mixtures
and independent parent roles. No GlobalID appears in both training and test,
even through another year or acquisition.

## Competing approaches

Compare exact FCLS, existing EAR-candidate MESMA, regularized multi-output ridge,
PLS, random forest, gradient boosting, and a presence-then-conditional-abundance
model. Supervised predictions are projected onto nonnegative, sum-one fractions.
Hyperparameters and detection cutoffs use separate training/tuning parent sets.
Automatic row-level boosting validation is disabled. Synthetic rows sharing
parents do not become independent biological replication.

The primary experiment has 24 training parent bundles (120 independent IDs),
eight tuning bundles (40 IDs) and up to twelve test bundles (60 IDs). Every bundle
contains one distinct parent per researcher category. Curves include zero and
low fractions; all related mixtures stay together in uncertainty calculations.
Training-diversity sensitivity, spectral shape, disconnected derivatives, PCA,
PLS and selected coordinates are reported separately from the primary models.

## What distinguishes a good fit from the right fractions?

MESMA near-solution fraction ranges identify candidate-library ambiguity at a
stated training-scaled tolerance. All methods are stratified on the same target
ambiguity categories. A common class-mean reconstruction diagnostic permits
comparison across methods; native MESMA residuals are retained separately.
Known-parent oracle controls test the solver under the idealized linear model.
An oracle is unavailable in deployment and does not validate material purity.

Model improvements within a synthetic distribution must also survive held-site
and temporal targets. Bias, class RMSE/MAE, low-abundance error, false detections,
calibration and detection curves matter more than an isolated average RMSE.
Bootstrap intervals resample parent bundles, not dependent fraction levels.

## The remaining validity gate

Even a successful synthetic model does not establish unique physical inversion
or field-cover accuracy. Recorded cover categories can be mixed materials;
units/purity, balanced independent domains and independently measured complete
fractional cover remain essential. A small residual is not membership evidence.

[Final versioned benchmark, figures and report](https://github.com/earthlab/spectralbridge/tree/main/provenance/researcher-pft-information/2026-10-15/v1)
retains positive, failed and inconclusive experiments with their exact scope.
