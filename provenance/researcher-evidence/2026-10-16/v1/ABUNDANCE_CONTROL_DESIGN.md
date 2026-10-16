# Same-candidate ridge fairness control

Added during the hostile-review audit, before evaluating this control. The main
ridge has 120 proper-training parents while EAR/MESMA retains 15 candidates (3
per category) from that pool. Equal test mixtures do not imply equal retained
library capacity. Prior library-size experiments are informative but are not a
matched explanation of the present ridge gain.

For every existing training context and both sensors, use exactly the 15 saved
MESMA candidate parent indices. Form three deterministic five-category bundles
by candidate order within class; generate the unchanged 170 mixtures/bundle
fraction grid (510 dependent training mixtures, 15 independent parents). Fit the
same training-only scaler/ridge [.1,10], choose alpha on the unchanged 40-parent
tuning set, project to simplex, evaluate the identical 60-parent outer targets.
Report this as a capacity sensitivity, not a replacement winner or equivalent
hypothesis class. MESMA and ridge impose different priors; neither pure-parent
truth nor field fraction validity is established. No target-dependent candidate
or hyperparameter selection. Save all membership, tuning and predictions.
