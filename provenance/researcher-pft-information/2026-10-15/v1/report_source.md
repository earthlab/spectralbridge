# Researcher cover categories: spectral information and synthetic abundance


Supervised regression improves known synthetic fraction recovery: NEON ridge 0.216 versus MESMA 0.359 on new-parent tests, and 0.269 versus 0.362 on held sites. These gains do not establish unique inversion or field-cover accuracy.


## Figure 1. Whole-spectrum differences and recognition answer different questions

A: full-cohort acquisition-matched descriptive effects, not Cohen d. B: nested full-spectrum logistic class recall. Five recorded classes only; within-class spread and domain dependence remain.


**Finding:** All forty eligible researcher-category whole-spectrum comparisons were supported in the prior matched NPC analysis. Magnitudes differ. In the new full-spectrum tests, mean held-site recall is 94.2% for Evergreen and 91.7% for Non-vegetated & dead, versus 46.3% for Woody shrub.


**Limit:** These are observational cover labels, not randomized traits or pure-material guarantees. Full-cohort matched effects and nested prediction use different populations/weighting.


## Figure 2. Where do the matched spectral differences occur?

A: full-cohort descriptive effects. B: training-only max-T and within-design Bonferroni support in eight outer-training designs, which overlap and are not independent replications. No inference map selects predictive features. Triangles/short bars mark configured OLI centers/FWHM. Visible <700; red edge 700-750; NIR 750-1340; SWIR1 1450-1790; SWIR2 2000-2510 nm.


**Finding:** Strong differences occupy broad regions rather than isolated independent channels. Training-only corrected support is shown across eight overlapping outer-training designs; these are not independent replications. The signed mean can conceal reversals; consult individual site/year effects and sign consistency in the atlas.


**Limit:** Full-cohort evidence and training-only evidence are separate. Max-T and within-design Bonferroni control the declared training family. Neither inference map selects predictive features. Null support is not an effect confidence interval.


## Figure 3. Which individual wavelengths predict held-out categories?

Balanced-prior univariate LDA; direction and threshold trained without target identities. Mean versus weakest-site performance are different views. These are estimates for one rule, not a theoretical information bound.


**Finding:** Evergreen/Herbaceous and several contrasts involving Non-vegetated & dead have stronger single-coordinate signals. Herbaceous/Woody shrub remains below chance at its best observed worst-site coordinate under this mean-based rule.


**Limit:** LDA learns means, direction and midpoint threshold on training IDs only. It estimates one rule, not an upper bound on all nonlinear single-coordinate information. Outer peaks are descriptive, not selected deployment bands.


## Figure 4. A large group difference can still be a weak predictor

Four declared illustrations; all ten pairs are in the atlas. Effect height describes matched group differences; color describes a separate held-site predictor. Segments do not cross atmospheric gaps.


**Finding:** These four selected pairs compare two distinct quantities: adjusted curve magnitude and held-site prediction. Effect height is not accuracy. Near-infrared and shortwave-infrared information helps some pairs, while the difficult Herbaceous/Woody shrub contrast lacks a robust single-coordinate rule.


**Limit:** Illustrations are selected for interpretation, not another testing family. All ten pairs are available in the full map. Spectral association does not uniquely identify a biochemical cause.


## Figure 5. Which classes can one spectral coordinate recognize?

Prespecified five-class balanced-prior nearest-mean discriminant. A single coordinate can separate two classes yet confuse the five-way classification. This differs from pairwise balanced accuracy and full-spectrum logistic recall.


**Finding:** A coordinate that helps a two-class comparison need not distinguish all five classes at once. Mean-based class centers can crowd together. Full-spectrum logistic recognition is a separate, stronger model; these are not its wavelength importances.


**Limit:** Five-class nearest-mean recall differs from pairwise balanced accuracy. Class sizes differ; every identity, including its repeated years, stays together in train/test splitting.


## Figure 6. Separate spectral magnitude from site and year stability

Score=max(0,2*minimum held-site BA-1) times cohort sign consistency. It is a review aid over three observed sites. Temporal changes preserve target identities; annotations are reused later field labels. No geographic-population or annual-truth guarantee.


**Finding:** Some regions retain sign and predictive performance across sites; others are geographically specific or change between the paired image years. The score rewards the weakest observed site, so averaging cannot hide a failed domain.


**Limit:** Only three sites and two incompletely crossed years are available. Labels dated 2023/2024 are reused across image years. These are retrospective footprints, not independently verified annual individuals.


## Figure 7. Complementary information accumulates over many coordinates

All selection and C tuning refit inside group-aware inner folds. Correlation panel compresses unsupported gaps in its coordinate index and interpolates no missing channel. The greedy residual criterion seeks complementary information; it is not an optimized sensor.


**Finding:** New-polygon balanced accuracy rises from 41.6% at one complementary coordinate to 81.6% at twenty and 85.2% for the full grid. Held-site values are 70.1% and 73.8%. The inner-only parsimony rule chooses 50-100 coordinates across these folds.


**Limit:** Selectors and regularization refit inside each inner identity fold. The greedy residual path is not a globally optimal sensor. Correlation alone does not establish conditional predictive redundancy.


## Figure 8. Synthetic OLI preserves tests better than predictive accuracy

Identical class labels and paired source observations. OLI spectral convolution is synthetic, at native/polygon support; it does not supply independent sensor noise, a 30 m footprint or field validation.


**Finding:** All forty researcher contrasts retain statistical support in OLI. Yet full-spectrum new-polygon/held-site accuracy changes from 85.2%/73.8% for NEON to 66.8%/57.7% for synthetic OLI. Support retention is not preservation of all predictive information.


**Limit:** OLI is derived from the same NEON spectra at native/polygon support. It is neither independent Landsat validation nor 30 m spatial aggregation. MicaSense is excluded because physical coordinates remain unresolved.


## Figure S1. Which researcher categories are confused?

Rows are true classes; columns are predictions. Cells are fold-mean row fractions. The year panels reuse the earlier validated researcher-only logistic baseline and annual-row target weighting; new polygon/site panels use the new nested identity-weighted model. These are conditional observed-domain tests.


**Finding:** Evergreen and the broad background category transfer better than Woody shrub. Off-diagonal cells identify the alternatives receiving mistakes. The year panels preserve the prior researcher-only model and clearly label that reuse.


**Limit:** Rows are normalized within each fold, then averaged. The new polygon/site model uses identity weighting; historical year panels use the validated earlier annual-row model. Do not interpret these as identical fitted pipelines.


## Figure 9. Supervised models improve known synthetic fraction recovery

Solid bars: NEON; pale bars: OLI. Dots are outer folds, not independent fraction levels. All methods use identical parent-disjoint targets; 120 proper and 40 tuning parents per fold, up to 60 test parents. These are synthetic weights, not field cover.


**Finding:** NEON ridge fraction RMSE is 0.216 for new-polygon parents and 0.269 for held sites, versus MESMA 0.359/0.362. The no-spectrum training-prior control is 0.309: ridge beats it for new-parent/held-site targets, but not on average in the global-year tests. Flexible trees do not outperform ridge in the principal mean.


**Limit:** Each experiment uses 120 proper and 40 tuning parents, with up to 60 test parents. All methods share targets. Synthetic rows within a parent bundle are dependent; field abundance is not measured.


## Figure 10. Fraction errors depend on both class and true abundance

Curves average the three new-polygon folds; complete grids for all methods/domains are saved. At true zero, positive detection is false detection. The .10 cutoff is declared, not a universal detection limit. Mixtures sharing parents are dependent.


**Finding:** Models can shrink extremes, assign nonzero fractions to absent classes and differ substantially among researcher categories. Overall RMSE hides these patterns. The common projection enforces physical fraction constraints but cannot certify the biological interpretation.


**Limit:** Known fractions are algebraic source weights, not independent physical cover. Curves average folds on the stated synthetic prior. Every saved fraction is nonnegative and sums to one after projection.


## Figure 11. Fewer false detections can mean more missed low fractions

Curves average the three new-polygon folds; complete grids for all methods/domains are saved. At true zero, positive detection is false detection. The .10 cutoff is declared, not a universal detection limit. Mixtures sharing parents are dependent.


**Finding:** For Evergreen in new-parent tests, two-stage modeling reduces zero-fraction false detections relative to ridge, but increases low-fraction misses. Other classes show their own tradeoffs. A lower average fraction RMSE does not establish a reliable presence detector.


**Limit:** The .10 fraction cutoff is a stated comparison rule, not a universal detection limit. Parent-bundle dependence limits uncertainty; source class truth does not certify pure endmembers.


## Figure 12. Lower fraction error does not remove spectral ambiguity

Strata are shared across every method, using full-NEON MESMA near solutions within .01 training-RMS-scaled tolerance. Missing strata are unsupported. This diagnoses a candidate-library inverse problem, not intrinsic physical ambiguity or calibrated intervals.


**Finding:** Ridge improves average error in the high-ambiguity held-site stratum, but gains are not uniform: MESMA can perform better in a moderate stratum. A learned prior can improve expected error while another biological composition still fits almost as well.


**Limit:** Ambiguity is candidate-library- and tolerance-dependent. Strata use the same NEON diagnostic for all methods. Missing strata are unsupported, and near ranges are not calibrated confidence intervals.


## Figure 13. Abundance transfer depends on the target domain

Global year holds alter site composition. Paired NIWO directions reuse the same held-out target IDs/fractions in both years, with other IDs for proper/tuning pools. Annotation labels are retrospective. Each cell is conditional on sampled parent bundles.


**Finding:** Held-site and year targets alter model performance. Ridge global-year mean RMSE is 0.311, versus 0.309 for the no-spectrum training prior. The complete-pair NIWO design tests the same unseen IDs/fractions in both years, using other identities for fitting. Global year holds additionally change site composition; those columns are not a clean causal temporal effect.


**Limit:** Paired abundance is a fixed identity split, not the three-fold single-wavelength temporal experiment. Interval estimates condition on observed parent bundles; they do not cover new geographic populations.


## Figure 14. The final evidence is conditional, with a field-truth gate

Evidence status is use-specific, not an aggregate score. Lowest observed outer score is descriptive, not a tuning choice or multiplicity-corrected winner. No synthetic success is promoted to field abundance validation.


**Finding:** Researcher-category recognition and controlled synthetic fraction recovery are useful, with clear domain limits. Supervised regression improves the latter. Unique physical inversion and operational fractional cover remain unestablished without independent purity and complete field fractions.


**Limit:** The lowest observed outer score is a descriptive comparison, not test-set hyperparameter tuning or a multiplicity-corrected winner. No current result is promoted to field abundance validation.
