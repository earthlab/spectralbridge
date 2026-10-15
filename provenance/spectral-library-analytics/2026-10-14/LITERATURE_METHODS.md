# Method verification before implementation

Primary sources inspected 2026-10-14; use the published method where practical
and label adaptations. Existing MESMA literature audit is reused, not replaced.

- Roberts et al. (2017), *Ecography* 40:913–929, DOI
  [10.1111/ecog.02881](https://doi.org/10.1111/ecog.02881): structured ecological
  data require validation targeted to the intended temporal/spatial/hierarchical
  transfer question. [Author/institution copy](https://www.wsl.ch/lud/biodiversity_events/papers/Roberts_et_al-2017-Ecography.pdf).
  Our plant/acquisition/year/site purging and nested feature selection are
  source-specific designs, not a claim to remove all environmental confounding.
- Angelopoulos & Bates, [A Gentle Introduction to Conformal Prediction](https://arxiv.org/abs/2107.07511),
  [author PDF](https://people.eecs.berkeley.edu/~angelopoulos/publications/downloads/gentle_intro_conformal_dfuq.pdf):
  split conformal uses held-out calibration scores and a finite-sample quantile;
  geographic/domain-shift coverage is not guaranteed by ordinary exchangeability.
  Proposed classification prediction sets will be evaluated empirically by
  domain/class; no field abundance guarantee will be implied.
- Bioucas-Dias et al. (2012), [Hyperspectral Unmixing Overview](https://arxiv.org/abs/1202.6294),
  DOI [10.1109/JSTARS.2012.2194696](https://doi.org/10.1109/JSTARS.2012.2194696):
  linear mixture assumptions, variability, noise and inverse-problem ambiguity
  matter in addition to spectral fit. Fixed/variable endmember and selected-band
  comparisons remain controlled algebraic experiments without independent truth.
- Roth, Dennison & Roberts (2012), DOI
  [10.1016/j.rse.2012.08.030](https://doi.org/10.1016/j.rse.2012.08.030),
  [author PDF](https://content.csbs.utah.edu/~pdennison/reprints/denn/2012_Roth_etal_RSE.pdf):
  EAR/CoB/IES/hybrid selection compares representativeness and classification
  performance in separate reference libraries. Source-specific candidate budgets,
  repeated EAR/MASA ranks and IES completion are adaptations already declared in
  provenance/mesma-readiness/2026-10-14/LITERATURE_METHODS.md.

Before specialized ML/selection/open-set implementation, add the corresponding
primary papers/official implementation contracts and fix the exact operational
choices in DESIGN.md. This file is an initial verified bibliography, not a claim
that every proposed method has been implemented or validated.


## New classification/calibration implementation grounding

- Cawley & Talbot (2010), [JMLR 11:2079–2107](https://www.jmlr.org/beta/papers/v11/cawley10a.html): tuning/selection can itself overfit the validation criterion. Nested group-aware choices remain separate from outer test reporting; no best-model claim from uncorrected searches over outer folds.
- Guo et al. (2017), [PMLR 70:1321–1330](https://proceedings.mlr.press/v70/guo17a.html): temperature scaling fits a single score-scale parameter on a held-out calibration sample. Applying that mapping to classical model log-probabilities/decision scores is our explicitly evaluated adaptation, not an assumed guarantee of calibration under geographic shift.
- Scheirer et al. (2013), [author open-set recognition project](https://www.wjscheirer.com/projects/openset-recognition/), DOI 10.1109/TPAMI.2012.256: known-class classification must be distinguished from recognition in the presence of unknown classes. Our held-class challenges use training-calibrated novelty thresholds rather than claim to reproduce the paper's particular open-space-risk classifier.

Primary implementation contracts (official documentation) will be checked against
the installed scikit-learn version before coding PLS/SVM/calibration details.
The optional `analytics` extra isolates classical ML dependencies from core
processing and ordinary spectral-library use.

Official scikit-learn 1.9.1 contracts checked: [PLSRegression](https://scikit-learn.org/stable/modules/generated/sklearn.cross_decomposition.PLSRegression.html), [SVC](https://scikit-learn.org/stable/modules/generated/sklearn.svm.SVC.html), [StratifiedGroupKFold](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html) and [SelectKBest](https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.SelectKBest.html). PLS-DA is an explicitly documented one-hot-response regression/argmax adaptation. SVC internal probability calibration is avoided in favor of independent group calibration. Feature selectors and scalers are steps inside each fitted training pipeline. Group stratification is approximate; every realized fold membership/support is checked, not assumed from the splitter name.


## Executed adaptations and exclusions

The declared classical pipelines, independent temperature calibration, raw-score grouped conformal sets, training-only F selection, KMeans-nearest-observation prototypes and withheld-class novelty diagnostics were executed. KMeans prototypes are an explicit adaptation, not a claim to implement global PAM. PCA radius is an exploratory standardized latent-space score, not a Gaussian probability. Full-model coefficients and PLS loadings complement univariate selection; no random-forest-only importance claim is made. Prior EAR/MASA/CoB/IES definitions and caveats remain those of the canonical MESMA literature audit.

No new deep representation, calibrated field abundance interval, empirical cross-sensor noise law or universal physical unknown detector was justified. Fixed classical grids, proxy unknowns and correlated selected wavelengths restrict interpretation.
