# Ecological signal is real. Transfer and inversion are conditional.

SpectralBridge spectral-library analytics report | 14 October 2026

The central question is how much ecological information survives new plants, acquisitions, years, sites, spectral reduction and mixtures. The library supports conditional ecological discrimination. It does not yet establish reliable operational abundance mapping.

Across held-out plant identities, full-spectrum logistic regression achieved mean balanced accuracy of 86.8% for inferred PFTs and 85.8% for researcher categories. Equal class recall, rather than majority-dominated overall accuracy, is the principal metric.

Transfer to a held-out site was much less uniform: inferred-PFT balanced accuracy ranged from 39.3% to 83.5%. These are the observed sites, not a confidence interval for new regions.

Biological differences mostly survive synthetic OLI: 15 of 16 NEON-supported PFT contrasts remain supported. That preservation does not imply accurate fractions. Full-NEON primary synthetic PFT fraction RMSE was 0.344.

The decisive restrictions are domain dependence, wrong-class mixture reconstructions, weak unknown rejection, physical-material/purity gaps and absent independent abundance truth. A small residual is evidence of fit, not proof that the identified materials or fractions are correct.

Evidence: ml_generalization.csv; biological_contrasts.csv; sensor_resolution_mixture_results.csv

# Five findings and the decision

1. New-plant recognition is credible within the sampled population: PFT plant-fold scores span 83.3%–88.9%. This is stronger predictive evidence than significant group contrasts alone.

2. Geographic and temporal transfer depend on direction and available classes. Site and year are themselves highly predictable. Environmental, species, phenological and acquisition structure remain entangled; the experiment cannot assign a causal share to each.

3. Broad OLI responses can preserve useful information: PFT plant-held-out balanced accuracy is 76.4%, versus 63.2% for seven training-selected narrow coordinates. The experiment changes response width and placement as well as selection; it does not isolate a pure band-number effect.

4. Better classification and larger endmember libraries do not solve the inverse mixture problem. Wrong-class combinations frequently fit pure observations well, and conditional fraction errors remain substantial. Detection frequencies are not population detection limits.

5. Unknowns and uncertainty are weak links. Withheld-class detectors generally accept most unknown spectra at thresholds chosen to keep known rejection low. Conformal sets can look reasonable for held-out plants and lose coverage under site shift.

Decision: use the library for reproducible characterization, sampled-group comparisons and explicitly validated closed-set recognition. Treat MESMA as an experimental diagnostic. Collect independent fractional-cover/purity truth, replicated site/year acquisitions and matched real sensor observations before operational ecological abundance claims.

No operational class is declared READY on the basis of a composite score. The evidence-linked matrix reports each readiness dimension separately. Deep learning is not warranted by the present sampling and validation gaps.

Evidence: readiness_matrix.csv; unknown_material_detection.csv; uncertainty_calibration.csv

# 1 · Why this audit follows an information ladder

A plot can show different curves without establishing that an unseen plant can be recognized. A classifier can recognize pure classes without determining the fractions in a mixed pixel. Each step asks a harder scientific question with its own observational unit and failure modes.

Observed spectra → new individual → new acquisition → new year → new site → reduced spectral response → mixed composition → unknown material and uncertainty → defensible ecological inference.

This ladder is an organizing logic, not a sequence of nested numerical percentages. Different holdouts contain different plants, years and supported classes. Their scores cannot be subtracted to estimate a causal “fraction of ecological information lost.”

The original library is read in place. Earlier functional inference, sensor-transfer, real-Landsat and MESMA results are reused with their original scope. New experiments add grouped classical prediction, coordinate selection, prototypes, domain diagnostics and withheld-class challenges.

Evidence: DESIGN.md; REPOSITORY_AUDIT.md; OBSERVATIONAL_STRUCTURE.md

# 2 · What is in the library?

The source contains 85,706 pixel records and 3,639 globally identified polygons/plants. Compact observations produce 4,807 polygon/year summaries. They are repeated observations, not independent new plants.

The sites are NIWO, WREF and YELL. NIWO has 2020 and 2023 observations; WREF and YELL are represented in 2023. Consequently “year” and “region” are incompletely crossed. Species, source categories and inferred functional types remain distinct label systems.

The common NEON representation has 360 supported coordinates and the synthetic OLI representation has 7 channels. Atmospheric gaps are excluded rather than interpolated. Original native-grid identities and complete acquisition histories remain traceable.

Finite negative corrected values are retained. The library’s absolute stored-unit interpretation remains unresolved; no division by an assumed scaling constant is introduced. The independently checked Landsat pilot has its own verified reflectance units and does not repair the library’s missing scale provenance.

Missing species and unassigned PFT records are reported, not guessed or merged to improve prediction. Researcher categories are source labels, not certificates of pure vegetation, soil, dead material or shade.

Evidence: library_summary.csv; canonical metadata/reference index; material_unique_counts.csv

# 3 · Do ecological groups actually look different?

The primary functional analysis compares whole curves within matched observational-history blocks. A maximum statistic asks whether the largest standardized difference is unusual; an integrated statistic asks whether differences accumulate over supported wavelengths. Synchronized nonparametric combination joins their evidence without pretending they are independent tests.

The audited PFT family contains 21 eligible contrasts: 16 are supported with full NEON and 15 retain support with OLI. The researcher-category family contains 40 contrasts. Family adjustment and exact memberships are retained from the earlier audit.

Repeated strong contrasts include deciduous broadleaf shrubs versus evergreen conifer trees and deciduous broadleaf trees versus evergreen conifer trees. A weak or unsupported contrast is not evidence of equivalence: limited independent support and heterogeneous groups can also reduce power.

Localization is conditional on the supported contrast and matching design. Established repeated intervals include portions of NIR and SWIR. An interval showing a group effect is not automatically an optimal prediction band or an identifiable mixture endmember.

Holm adjustment applies to the declared contrast families. Family excursion envelopes control wavelength searches for differences; they are not uncertainty intervals for the magnitude of every ecological effect.

Evidence: biological_contrasts.csv; original pft-audit and sensor-pft-transfer manifests

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

# 7 · Where is transferable wavelength information?

The primary predictive ranking is a training-only between-class/within-class F ratio. It is recomputed within every inner tuning fit and again on proper training after tuning. Its numerical F values are exploratory ranks, not confirmatory wavelength p-values.

Selection frequency across outer folds, standardized logistic coefficients and PLS loading norms provide complementary views. Existing functional localization supplies a separate biological check. Correlated adjacent coordinates can exchange ranks without representing different ecological processes.

The figure shows which coordinates recur when twenty are selected. Repetition across the observed site holdouts is stronger evidence of stability than one pooled importance curve; it still does not establish a universal sensor design.

Coordinates selected in every observed site-training fold span 1695–1760 nm for the inferred-PFT twenty-coordinate ranking. This concentrated SWIR choice is correlated and does not deliver the best broad-spectrum recognition.

The coordinate table records exact wavelengths and frequencies. Interpret repeated regions rather than attaching causal pigment/water mechanisms to a selected coordinate without an independent physiological measurement.

Evidence: wavelength_selection.csv; wavelength_coefficients.csv; original functional localization

# 8 · How much spectral resolution is enough?

The controlled prediction curve compares full common NEON, training-selected coordinate subsets, and the packaged synthetic OLI response. All representations use exactly the same eligible final test keys within each fold.

PFT plant-held-out mean balanced accuracy is 86.8% for full NEON, 78.6% for one hundred selected coordinates, 63.2% for seven selected coordinates and 76.4% for OLI.

The selected-coordinate curve is not monotonic in every domain. For example, a reduced representation can regularize a site-transfer problem better than all available coordinates. This is evidence about this training rule and population, not proof that the omitted wavelengths contain no ecological information.

OLI versus seven narrow coordinates changes placement, width, averaging and the supervised selection rule together. Both count and response design can matter, but this experiment cannot assign an isolated causal contribution to either. A globally optimized seven-band sensor has not been demonstrated.

MicaSense remains blocked for physical sensor inference because the stored fallback/padded coordinates do not have verified source wavelength provenance. No MicaSense accuracy or sensor-transfer conclusion is manufactured.

Evidence: spectral_resolution_performance.csv; paired_sensor_differences.csv; SENSOR_AUDIT predecessor

# 9 · Does one example describe a class?

A mean or median summarizes a class but can be a spectrum no observed plant actually had. A medoid is an observed central plant. Cluster medoids spread representatives across training clusters; diversity selection deliberately chooses distant examples.

Candidates use one earliest proper-training observation per independent identity. Distances are evaluated in coordinate space standardized using proper training only. A cluster medoid here is the observed point nearest a KMeans center, not a global PAM optimum.

Multiple cluster representatives often improve coverage over a single center, especially for heterogeneous researcher categories. Maximal diversity does not reliably improve classification: extreme examples can move nearest-prototype boundaries in harmful ways.

Size requests beyond the available independent candidates are marked insufficient support. The rarer inferred PFTs limit the all-class size curve. There is no defensible single “number of endmembers needed” for every class/domain.

The earlier class-specific accumulation and reconstruction tables distinguish which classes remain variable. More candidates can reduce reconstruction error while also providing more wrong-class mixture alternatives. Coverage and uniqueness must be evaluated together.

Evidence: prototype_performance.csv; prototype memberships; library_size.csv predecessor; library_size_recovery_summary.csv

# 10 · Can a pure class be mistaken for a mixture?

Mixture identifiability asks a different question from classification. Can an observation from class C be reconstructed by a nonnegative sum-to-one combination of candidates from other classes? If so, a low spectral residual cannot uniquely identify its composition.

The audit compares the best own-class fit with wrong-class convex combinations under the same declared metric and tolerance. A near-alternative composition is not a second independent material truth; it is evidence that the inverse problem admits competing explanations.

No PFT is certified uniquely mixture-identifiable. Some classes have lower conditional ambiguity than others, but limited rare-class support and unverified pure-material labels prevent a general uniqueness claim.

Adding more representatives can improve spectral coverage and simultaneously increase ambiguity. A library can be valuable for classification yet unsuitable for unique fraction inversion. That tension is an important scientific result, not a software failure.

Evidence: mixture_identifiability.csv; original ambiguity and selector-sensitivity tables

# 11 · Can known fractions be recovered?

Synthetic mixtures combine held-out empirical parent spectra at known algebraic fractions. The training library never contains those parent identities. FCLS uses nonnegative fractions that sum to one; MESMA compares small models with varying endmembers. An exact constrained face search avoids pretending that clipped unconstrained coefficients solve the problem.

These are controlled linear-mixture experiments. The fractions are known because we created them; they are not independently measured canopy, biomass, surface-cover or leaf-area fractions. Nonlinear radiative transfer, three-dimensional structure and real spatial mixing are not reproduced.

The primary EAR-MESMA full-NEON mean class/fold fraction RMSE is 0.344 for PFTs and 0.380 for researcher categories. These substantial errors do not establish reliable operational abundance recovery.

Selected-coordinate counterparts preserve the exact saved parents, fractions, folds and EAR candidate identities. Full-spectrum reconstruction is checked against the earlier saved fit before interpreting the new comparisons. Reduced-band errors are not contaminated by a fresh random parent draw.

Residual error, fraction error, class-set error, runner-up composition and near-fraction ranges are separate diagnostics. A good residual alone cannot certify correct fractions.

Evidence: mixture_recovery.csv; sensor_resolution_mixture_results.csv; legacy reproduction manifests

# 12 · How much must be present to detect it?

Detection means the estimated class fraction exceeds a declared operating cutoff. True presence means any positive algebraic fraction. These definitions differ from the class-set metric, which uses its own fraction threshold for the true composition.

The detection curves show conditional frequencies along saved parent trajectories. At zero true fraction, a positive detection is a false positive. At a small positive fraction, failure to cross the cutoff is a false negative. Both matter; showing only recall at high abundance is misleading.

Population D50, D80 and D95 thresholds are marked INSUFFICIENT EVIDENCE. The repeated fraction levels share a few parent draws and cannot be treated as independent plants to fit a precise universal detection curve. No extrapolated population limit is reported.

The machine table gives class-specific conditional frequencies and support for full NEON, selected coordinates and OLI. Those can guide a future independent-parent experiment, but cannot promise a particular field detection limit.

Evidence: detection_limits.csv; original cutoff sensitivity tables

# 13 · Does the library know when it lacks the answer?

For each class challenge, that entire ecological class is removed from proper training and known calibration. Final test plants from the omitted class become proxy unknowns. A model trained on the remaining classes is asked to reject them, rather than simply force their assignment.

We compare nearest spectral angle, nearest distance, scaled PCA radius and reconstruction residual, classifier confidence and empty raw-score conformal sets. Distance thresholds are chosen from known calibration identities alone. Unknown labels never tune them.

Unknown recall is low at the resulting low known-class rejection rates. This is a strong reason not to interpret a confident closed-set class label as proof of membership. Precision and average precision also depend on the challenge prevalence; the tables retain that baseline.

The omitted labels are ecological proxies. They do not exhaust water, soil, snow, mixed vegetation, shadow or new mineral materials. Earlier absent-class MESMA residual and ambiguity checks reinforce the same warning: unknown materials can lie inside the known library’s convex spectral space.

A zero vector in selected coordinates has no spectral angle; the angle result is explicitly undefined while valid distance/PCA diagnostics remain available. No artificial angle is assigned.

Evidence: unknown_material_detection.csv; withheld memberships/predictions; earlier unknown residual audit

# 14 · Are confidence and uncertainty trustworthy?

Temperature scaling fits a single score-scale parameter on independent training calibration identities. It can soften or sharpen probabilities but does not change the winning class. Its held-out Brier score, log loss, expected calibration error and reliability bins are evaluated rather than presumed improved.

Raw PLS/SVM/centroid softmax mappings are scores, not automatically calibrated ecological probabilities. Brier score penalizes the whole probability vector; top-label ECE summarizes binwise confidence error but can conceal class-specific problems.

For PFT full-NEON logistic regression, empirical joint-identity conformal coverage ranges from 88.4% to 90.2% across plant folds, but from 50.3% to 83.7% across site folds. The nominal target is 90.0%.

The conformal score is fitted without calibration labels. One maximum nonconformity per calibration identity protects the within-identity cluster definition, conditional on the required exchangeability. Ordinary split conformal does not promise coverage after geographic or temporal shift.

Mixture Monte Carlo intervals describe endmember-choice stability. They are broad and under-cover their nominal target in several settings; they are not validated field abundance confidence intervals. More uncertainty replicates cannot create missing ground truth.

Evidence: uncertainty_calibration.csv; class_conformal_coverage.csv; mixture_uncertainty.csv; reliability.csv

# 15 · What does real Landsat add?

Synthetic OLI is convolution of the same NEON reference and establishes a controlled spectral-response relationship. The independent R10C pilot adds real spatial footprint aggregation, timing, atmospheric product, QA and alignment effects. These are distinct evidence layers.

The pilot uses one paired NEON flightline and Landsat 8 Level-2 scene. It applies documented Landsat scaling and QA, uses true footprint overlap and spatial-block uncertainty, compares the original alignment with a limited offset diagnostic and surfaces heterogeneity dependence.

The undarkened comparison includes 3,583 matched footprints and 56 spatial blocks. Pooled seven-band RMSE is 0.01477 in verified reflectance units; median spectral angle is 2.09°. The nominal lag is 22.37 hours, conditional on the legacy NEON timestamp interpretation.

The actual pilot numeric results and plotted data are reused from its own verified provenance. They do not measure PFT classification, fractional-cover accuracy or multi-site sensor interchangeability. Its verified reflectance units cannot be transplanted into the spectral library by assumption.

Empirical real-Landsat residual perturbation of the library mixtures is therefore blocked: the library’s absolute stored-unit provenance is unresolved and transfer of one scene’s residual distribution would require additional assumptions. The earlier acquisition-variability sensitivity remains a sensitivity, not measured universal sensor noise.

Good agreement in one real pair strengthens confidence that the pipeline can make a meaningful sensor comparison. It does not overcome the ecological inversion or validation gaps.

Evidence: REAL_LANDSAT_CONTEXT.md; provenance/real-landsat-validation/2026-10-14

# 16 · Is the library ready for MESMA?

Readiness is evaluated by dimension: spectral integrity, ecological distinction, plant recognition, domain transfer, endmember uniqueness, fraction recovery, unknown rejection, uncertainty calibration and operational validation. No arbitrary composite readiness score is calculated.

Conditional uses include sampled-library characterization, matched group contrasts, controlled synthetic sensor-response comparisons and held-out closed-set recognition in explicitly evaluated domains.

Operational fractions are NOT READY or have INSUFFICIENT EVIDENCE. The reasons are traceable: unknown library scale/purity, ecological labels that are not pure physical materials, ambiguity under convex mixtures, substantial synthetic fraction error, weak unknown rejection and absent independent abundance truth.

“Green vegetation,” “Non-vegetated & dead,” woody shrubs and dead-material proxies must not be silently treated as pure endmembers for water, soil, snow, shade or species abundance. A missing physical material remains missing, even if an ecological classifier performs well.

Every class × dimension decision links to the exact supporting master table and limitation. Human review should apply the intended ecological error tolerance and deployment domain before approving any narrower application.

Evidence: readiness_matrix.csv; MATERIAL_CLASS_AUDIT.md; RECOMMENDATIONS.md

# 17 · The three most valuable new datasets

First: co-located, independently measured fractional cover and endmember purity. Measure actual green, senescent/dead, soil/mineral, water and shade fractions at the relevant footprint, with repeat observers or uncertainty estimates. Include small positive fractions and true absences. This directly tests inversion, false detection and interval coverage.

Second: a balanced repeated site × year × species/PFT panel with persistent plant identities, native wavelength metadata, units, acquisition geometry and physiological/environmental measurements. Prioritize currently rare or geographically restricted classes. This separates ecological variability from domain structure and supports stronger transfer claims.

Third: matched independent NEON, Landsat and verified drone acquisitions across sites/seasons, with tight timing, documented QA, spatial footprints and scale. This tests real sensor/domain shift rather than only convolution of one reference.

Analysis priorities after collection: freeze deployment questions and error tolerances; repeat the same grouped evaluation; assess class-specific physical unknown rejection and fraction uncertainty against independent truth; only then consider more complex representations if they solve a documented failure.

The current negative results change the description of SpectralBridge: it is a reproducible translation and scientific diagnostic system with demonstrated conditional ecological signal, not a universally calibrated sensor or validated ecological abundance engine.

Evidence: RECOMMENDATIONS.md; LIMITATIONS.md; readiness_matrix.csv

# Methods choices · why these tests?

Published methods are distinguished from source-specific adaptations in LITERATURE_METHODS.md. A method’s reputation does not substitute for validation on the intended observational unit.

Evidence: DESIGN.md; LITERATURE_METHODS.md; reusable experimental modules

# Model protocol and candidate budgets

Grouped inner tuning uses up to 3 folds; insufficient support is marked fixed/untuned. Every selector and scaler is refitted within each inner training fold. The final proper-training model is refitted after the declared choice.

PLS components are capped by available feature/sample dimensions. SVM internal random-row probability fitting is disabled. Temperature calibration and conformal thresholds use separate grouped calibration, as described in DESIGN.

Prototype size requests and selected-coordinate counts are fixed before final tests. The largest supported sizes differ by class; unsupported requests are not filled using repeated observations. No final-test optimization chooses a preferred size or wavelength set.

Evidence: manifests/model_protocol.json; per-fit parameter/warning/membership records; DESIGN.md

# Methods glossary

Labels, targets and uncertainty units should be read together. A plant-held-out accuracy, a blocked group-effect p-value and a synthetic fraction RMSE answer different questions.

Evidence: Methods implementation and master-table schemas

# Reproducibility and statistical scope

Fixed seed 20261014; whole-identity bootstrap draws 499; minimum training/test identities per class 10/3; independent calibration reserve 20.0%. Unsupported branches are explicit rather than forced.

Proper-training preprocessing and grouped inner tuning precede final evaluation. Models, selected wavelengths, memberships, calibration status, exact source hash, configuration, versions and output hashes are retained. Completed fold checkpoints are verified and reused; changed evidence is rejected.

Paired sensor/model differences resample the same identity clusters with the same draws. They condition on observed folds/classes. They are descriptive conditional intervals, not a new family of multiple-testing-adjusted superiority claims. Existing biological Holm-adjusted families are reused unchanged.

Synthetic mixture parents and fraction trajectories are dependent. Repeated rows at many fractions do not supply independent abundance-validation samples. Site averages are descriptive because the observed sites do not support a geographic superpopulation claim.

Report figures read tidy master tables. Editable JSON/Markdown narrative, the builder, source/result checksums and a section-level report manifest allow every major claim to be traced. Trusted local joblib files are loaded only after checksum verification.

Evidence: manifests/learning_run.json; full_learning_validation.json; report_manifest.json; VALIDATION.md

# Detailed geographic evidence · inferred PFTs

Each row is one complete held-site target, using only eligible supported classes. Balanced-accuracy intervals are whole-identity conditional bootstrap intervals. Coverage is empirical joint-identity raw-score conformal coverage, not a guarantee.

A high score in one direction cannot cancel a weak score in another. Examine class support and class-specific recall before applying the library to a particular region or functional group.

Evidence: ml_generalization.csv; class_predictive_performance.csv; fold_support.csv

# Unknown challenge · full-spectrum diagnostic detail

Rows average omitted-class × plant-fold challenges equally. Thresholds use known calibration only. Average precision is compared with each challenge’s retained unknown prevalence in the machine table; an average AP alone is not a prevalence-free deployment guarantee.

Low known rejection and low unknown recall mean that the method is conservative about rejecting familiar observations but accepts many missing classes. This is not reliable open-world membership validation.

Evidence: unknown_material_detection.csv

# Limitations that bound every conclusion

Independence: source pixels, repeat flights, repeat years and mixture fraction trajectories are not independent plants. GlobalID grouping addresses known identities but cannot remove all spatial, species or exposure dependence.

Observational design: few sites, incomplete year crossing, uneven class support and species/domain aliasing limit ecological attribution and external validity. No causal plant-trait mechanism or novel-species recognition is established.

Spectral/physical validity: absolute library units, source purity and physical-material coverage remain incomplete; MicaSense coordinates are unverified. Atmospheric gaps are never bridged. Finite negative corrected values are not automatically nodata.

Predictive scope: thresholds and grids are predeclared and training-confined, but the experiment is still a source-specific benchmark. Conditional confidence intervals do not represent unobserved geographic populations.

Inverse problems: empirical endmembers vary; linear synthetic mixtures omit real radiative transfer, spatial adjacency and canopy structure. Spectral fit cannot establish correct abundance, and no independent fraction truth validates operational MESMA.

Sensor evidence: synthetic OLI is derived from NEON. One real pair adds important radiometric/spatial context but does not validate regional PFT classification or abundance. Poor unknown rejection and shifted uncertainty coverage remain visible, not averaged away.

Evidence: LIMITATIONS.md; all stage and readiness evidence

# Primary literature and implementation provenance

Roberts et al. (2017). Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography. https://doi.org/10.1111/ecog.02881

Cawley & Talbot (2010). On over-fitting in model selection and subsequent selection bias. JMLR. https://www.jmlr.org/beta/papers/v11/cawley10a.html

Bioucas-Dias et al. (2012). Hyperspectral unmixing overview. https://doi.org/10.1109/JSTARS.2012.2194696

Roth, Dennison & Roberts (2012). Comparing endmember selection and vegetation classification. https://doi.org/10.1016/j.rse.2012.08.030

Guo et al. (2017). On Calibration of Modern Neural Networks. Temperature scaling adapted and evaluated here for classical scores. https://proceedings.mlr.press/v70/guo17a.html

Angelopoulos & Bates (2021). A Gentle Introduction to Conformal Prediction. https://arxiv.org/abs/2107.07511

Scheirer et al. (2013). Toward Open Set Recognition. https://doi.org/10.1109/TPAMI.2012.256

Implementation contracts and prior MESMA definitions: LITERATURE_METHODS.md and provenance/mesma-readiness/2026-10-14/LITERATURE_METHODS.md. Official scikit-learn contracts are linked there.

Evidence: LITERATURE_METHODS.md; original audited references
