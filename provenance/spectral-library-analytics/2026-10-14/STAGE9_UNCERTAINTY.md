# 14 · Are confidence and uncertainty trustworthy?

Temperature scaling fits a single score-scale parameter on independent training calibration identities. It can soften or sharpen probabilities but does not change the winning class. Its held-out Brier score, log loss, expected calibration error and reliability bins are evaluated rather than presumed improved.

Raw PLS/SVM/centroid softmax mappings are scores, not automatically calibrated ecological probabilities. Brier score penalizes the whole probability vector; top-label ECE summarizes binwise confidence error but can conceal class-specific problems.

For PFT full-NEON logistic regression, empirical joint-identity conformal coverage ranges from 88.4% to 90.2% across plant folds, but from 50.3% to 83.7% across site folds. The nominal target is 90.0%.

The conformal score is fitted without calibration labels. One maximum nonconformity per calibration identity protects the within-identity cluster definition, conditional on the required exchangeability. Ordinary split conformal does not promise coverage after geographic or temporal shift.

Mixture Monte Carlo intervals describe endmember-choice stability. They are broad and under-cover their nominal target in several settings; they are not validated field abundance confidence intervals. More uncertainty replicates cannot create missing ground truth.

Evidence: uncertainty_calibration.csv; class_conformal_coverage.csv; mixture_uncertainty.csv; reliability.csv
