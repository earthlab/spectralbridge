# 4 · Can we recognize a new plant?

All 3 outer plant folds hold out entire GlobalIDs across years and flights. Proper training fits scaling, coordinate selection and tuning. A separate 20.0% training-identity reserve is used for calibration where support permits; the final test plants are never used to choose parameters.

Logistic regression is a regularized linear rule that learns how spectral coordinates jointly distinguish classes. PLS-DA compresses correlated predictors while fitting one-hot class responses. RBF SVM and random forest can learn nonlinear boundaries. Majority, stratified random and nearest-centroid rules provide simpler reference points.

Full-NEON mean plant-fold balanced accuracy is 86.8% for PFTs and 85.8% for researcher categories. Per-class recall, precision, confusion matrices and whole-identity bootstrap intervals are available; overall accuracy alone would hide rare-class failures.

The complex models did not improve the principal plant-fold comparison over logistic regression. PLS-DA was particularly weak for inferred PFTs under the fixed component grid. This result supports retaining a simple baseline, not a universal ranking of algorithms.

These tests recognize new identities among the sampled class/site/species distribution. They do not withhold entire species and cannot establish recognition of novel species or continents.

Evidence: ml_generalization.csv; class_predictive_performance.csv; paired_model_differences.csv

# 5 · What changes across acquisition, year and site?

A held-flight target uses its actual compact flight spectrum, not an annual median that mixes it with other acquisitions. Every identity exposed to that flight is removed from training. Site and year holdouts likewise purge each GlobalID’s entire history.

Class support is a scientific gate. A class absent from training is an open-set case, not an ordinary closed-set error. Multiclass scores require multiple evaluable test classes; unsupported or single-class folds remain explicit in the support table.

For inferred PFTs, full-NEON mean balanced accuracy is 76.7% by acquisition, 69.8% by year and 58.8% by site. These are descriptive equal-fold averages, not equally representative geographic populations.

Direction matters: training on 2020 and testing in 2023 can differ sharply from the reverse direction. The within-NIWO year experiment helps separate this question from the addition of other 2023 sites, but only one eligible direction supports its summary.

Bootstrap intervals resample whole plants conditional on the observed site and class support. With only the observed sites, a reliable superpopulation confidence interval over regions is not available.

Evidence: ml_generalization.csv; fold_support.csv; paired_sensor_differences.csv

# 6 · The spectra also encode observational domains

We reverse the prediction question and ask whether spectra identify site, year or acquisition on unseen plant identities. Strong domain prediction indicates structured spectral differences that a biological classifier might exploit or encounter as shift.

These diagnostic models use a fixed logistic setting and grouped folds. Acquisition targets use actual plant/flight observations. A repeated identity may have multiple domain labels across acquisitions; the GlobalID remains grouped through validation and uncertainty.

High site/year accuracy is not proof of instrument bias. Real ecological differences, species composition, water status, phenology, illumination and processing may all contribute. Three sites and incomplete year crossing cannot disentangle them causally.

The practical implication is to qualify ecological predictions by domain and to prioritize balanced repeated sampling. A very high random-plant score does not remove this concern.

Evidence: domain_performance.csv; domain memberships/predictions
