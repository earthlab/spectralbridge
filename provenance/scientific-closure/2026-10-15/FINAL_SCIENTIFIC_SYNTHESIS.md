# Final scientific synthesis

## One sentence

Broad woody leaf-habit associations in these labelled polygon footprints transfer better across the observed sites and NIWO image years than finer taxonomic distinctions, including after amplitude removal.

## One paragraph

Within the assigned woody subset, mean full-NEON balanced accuracy was 96.7% for new polygons and 90.1% across held-out sites; shape-only site performance was 92.6%. On the same unseen NIWO polygons, a model trained on other 2020 polygons scored 95.9% in 2020 and 86.3% in 2023. The corresponding species scores fell from 63.9% to 30.0%. Labels recorded in 2023/2024 are reused on both image years; this is retrospective footprint recognition, not independent annual field confirmation. This supports conditional broad functional discrimination, not universal species recognition, causal trait attribution or unique field-mixture recovery.

## Manuscript-ready Results

The source comprised 3,639 polygon identities and 4,807 polygon-year summaries across three sites, with repeated observations restricted to NIWO. In the paired NIWO panel, narrow-PFT temporal change was 0.953 times the RMS class-centroid separation, while the common year component accounted for 0.8% of total paired variation. Most variation was persistent within-class polygon structure and polygon-specific change rather than a shared year offset. Source field annotations date from 2023/2024 and were reused across image years, so the paired task evaluates retrospective labelled footprints rather than independently verified annual biological status. For full-NEON broad woody leaf habit, mean identity-held-out balanced accuracy was 96.7%; held-site accuracy averaged 90.1%, and shape-only held-site accuracy averaged 92.6%. On identical unseen NIWO targets, 2020-trained broad-label recognition changed from 95.9% to 86.3%, compared with 63.9% to 30.0% for supported species. Synthetic OLI retained useful broad discrimination (94.8% mean new-polygon accuracy), whereas mixture ambiguity, synthetic fraction error and weak omitted-class rejection prevented operational abundance conclusions. These results support conditional broad functional discrimination and retention of temporal observations, with explicit limits on finer taxonomic and mixture inference.

## What can we reliably learn from this library?

Final scientific synthesis | 15 October 2026

Broad woody leaf-habit associations in these labelled polygon footprints transfer better across the observed sites and NIWO image years than finer taxonomic distinctions, including after amplitude removal.

Within the assigned woody subset, mean full-NEON balanced accuracy was 96.7% for new polygons and 90.1% across held-out sites; shape-only site performance was 92.6%. On the same unseen NIWO polygons, a model trained on other 2020 polygons scored 95.9% in 2020 and 86.3% in 2023. The corresponding species scores fell from 63.9% to 30.0%. Labels recorded in 2023/2024 are reused on both image years; this is retrospective footprint recognition, not independent annual field confirmation. This supports conditional broad functional discrimination, not universal species recognition, causal trait attribution or unique field-mixture recovery.

Decision: the library is scientifically promising for supported closed-set ecological discrimination and controlled sensor/mixture diagnostics. Preserve repeated observations and their year/site/acquisition identity. Operational abundance mapping and reliable physical unknown-material recognition remain unvalidated.

This report closes the analysis. It reuses completed functional, sensor, real-Landsat, classifier and mixture evidence. New calculations address paired temporal change, biological resolution, shape/amplitude and repeat representation; no production correction, sensor coefficients or raw-library normalization changed.

Evidence: biological_generalization.csv; paired_temporal_recognition.csv; FINAL_READINESS_MATRIX.csv

## 1. What data do we actually have?

The source has 85,706 pixel records, 3,639 unique GlobalIDs and 4,807 annual polygon summaries, with 122 acquisition/flightline product identities. Pixels and repeats are not additional independent plants. A GlobalID is a polygon identifier; biological-individual or population purity is not established.

NIWO contains 1,168 polygons observed in both 2020 and 2023. Every 2023 NIWO polygon in this library has a 2020 observation. WREF and YELL contribute 2023 observations only. Site, year, species and acquisition history are therefore incompletely crossed.

Researcher categories, species names and inferred traits are separate labels. The broad PFT used here is deciduous versus evergreen within crosswalk-assigned woody taxa. The coarse cover grouping contrasts vegetation-labelled records with the heterogeneous nonvegetated/dead source category; it is not pure vegetation versus mineral soil.

The source histories identify 14 site-date groups, not necessarily independent flight events. Polygon field-year metadata span 2023-2024; NIWO's polygon imagery_year stays 2020 even for 2023 extractions. Acquisition year here comes from actual source histories. Reused labels are not independent annual field observations.

The extracted raster-coordinate vectors have median native lengths 1.00 by 1.00 in verified metre grids. Median extracted support is 2 pixels per polygon/acquisition. This is native polygon support, not an independently measured pure plant endmember.

The common corrected NEON spectrum retains supported coordinates without bridging atmospheric gaps. OLI is derived from that reference; MicaSense physical coordinates remain unverified. Finite negative corrected values remain valid. Library stored units are unresolved and are not silently treated as unitless reflectance.

Evidence: observational_support.csv; flight_support.csv; product_support.csv; identity_sampling.csv; DATA_AUDIT inherited from P126

## 2. How large is change in the same polygon?

We compare the complete 2020/2023 NIWO pairs, retaining only stable labels with descriptive support. A balanced two-year decomposition separates class differences, persistent polygon differences within a class, a common year shift, class-specific year shifts and residual polygon-specific change. The components sum exactly to the observed total.

For narrow PFTs, the common year component is 0.8% of paired-panel variation; persistent differences among polygons within class account for 60.5%, and residual polygon-specific change for 19.3%. The RMS change in a polygon is 0.953 times the equally weighted class-centroid separation.

Thus substantial temporal change does not require a large uniform year offset. Individual polygons can move differently, including changes large enough to disrupt fine discrimination. Shape normalization reduces several temporal differences but does not make every broad centroid separation stronger.

These are descriptive sums of squares, not causal population variance components. There is no within-NIWO site variance to estimate, only two years, and no balanced global site-year experiment. Changes may combine ecology, phenology, illumination, acquisition composition and processing; this dataset cannot apportion those causes. Stable labels across pairs reflect annotation reuse, not independent proof of biological stability.

Evidence: paired_temporal_partition.csv; paired_polygon_changes.csv; paired_label_audit.csv

## 3. What is the finest useful biological resolution?

Species is the finest tested target, but its support is conditional. We retain exact recorded two-token binomial names rather than promote genus-only or unidentified records to species. Training requires at least ten distinct IDs per class and test reporting at least three; missing/rare/absent-training classes remain explicit.

Species mean new-polygon balanced accuracy is 71.7%, versus 47.4% at held sites and 36.2% in global year holdouts. At WREF only 24.3% of named-species target IDs meet closed-set support; the score is not a claim to recognize all species there.

Broad woody leaf habit is more transferable: mean new-polygon/site scores are 96.7%/90.1%. But it covers assigned woody taxa, not herbaceous or background records. Researcher categories retain their separate, useful five-class interpretation.

Support counts marked * use the global descriptive subset with at least ten IDs per label; actual fold eligibility differs. The table compares different class counts, chance references and eligible populations. It is not proof that coarsening the same set of records monotonically improves information. The practical conclusion is conditional species recognition within familiar distributions, with broader functional labels better supported for transfer across these observed domains.

Evidence: biological_generalization.csv; biological_effect_sizes.csv; closed_set_coverage.csv; fold_support.csv; all_class_detection_rates.csv

## 4. Is the result merely brightness? What survives Landsat?

The analytical shape sensitivity divides each observation by its own weighted spectral norm. No population parameter or test label is used, and the production library is unchanged. An amplitude-only model uses that single norm. All learned scaling and tuning remain confined to proper training.

Broad woody shape-only held-site performance is 92.6%, versus 67.4% from amplitude alone. Researcher/narrow PFT recognition also remains useful after amplitude removal. These results reject an amplitude-only explanation within these tested labels/domains, without identifying a causal physiological mechanism.

The existing functional sensor audit retains 15 of 16 NEON-supported inferred-PFT contrasts in synthetic OLI. Broad woody OLI new-polygon/site scores are 94.8%/87.8%. Sensor aggregation loses some information but does not erase this broad distinction. Synthetic OLI changes spectral response at native/polygon support; it does not simulate 30 m spatial mixing, point-spread function or actual Landsat noise.

Training-selected narrow coordinates are correlated and not an optimized sensor. Repeated inferred-PFT selection concentrates in the established SWIR region, with additional NIR/SWIR functional localization. Placement, bandwidth, averaging, band count and selection method change together; their independent causal contributions are not identified.

The real R10C/Landsat pilot supplies independent 30 m footprint radiometric/spatial context: 3,583 matched footprints, 56 blocks, pooled SR RMSE 0.01477. It remains one next-day pair with a timestamp caveat, not a regional ecological validation. Heterogeneity-error Spearman association is 0.544 (descriptive spatially correlated footprints); the brightness-adjustment RMSE difference is -0.00018 with interval [-0.00044, 0.00004], spanning zero. Offset diagnostics support retaining original alignment. Atmosphere, timing, illumination and BRDF cannot be separately estimated here.

Evidence: brightness_sampling_sensitivity.csv; prior biological_contrasts.csv; prior real_landsat_flight_metrics.csv; prior registration/heterogeneity diagnostics

## 5. Is the library ready to test mixtures?

Yes, as an exploratory laboratory for constrained synthetic recoverability. No, as a validated field-abundance mapping system. Endmember coverage, redundancy, selector sensitivity, ambiguity and fraction recovery are already tested; repeating them would not create independent truth.

FCLS enforces nonnegative fractions that sum to one. MESMA compares small models with variable candidate spectra. Saved test parents, fractions and candidate identities are held fixed in sensor comparisons. This establishes mathematical performance under the declared linear mixture model, not canopy, biomass or surface-cover accuracy.

Wrong-class combinations often explain an observed spectrum as well as its own class. More endmembers can reduce residual error while adding alternative compositions. Therefore a low residual and good classification accuracy do not establish a unique or correct mixture.

The table uses the existing 0.10 detection cutoff and positive-fraction presence rule. Rates condition on repeated synthetic parent trajectories, not independent field populations. Class-specific D50/D80/D95 remain unestimated. EBS has lower conditional ambiguity but sparse support; no PFT is certified uniquely identifiable.

DBS/DBT are deciduous broadleaf shrubs/trees; EBS is evergreen broadleaf shrub; ECS/ECT are evergreen conifer shrubs/trees. These inferred woody types are not pure physical-material measurements.

Evidence: prior mixture_identifiability.csv; prior mixture_recovery.csv; prior detection_limits.csv; prior library-size/selector/uncertainty tables

## 6. How should false positives and uncertainty be read?

For each class, sensitivity/recall measures detection among true members; false-negative rate is its complement. Specificity measures rejection among all other known classes; false-positive rate is its complement. Precision asks how often an assigned label is correct. Multiclass negative pools and class prevalence matter, so these are not one universal Type I/II error pair.

The class table retains TP/FP/TN/FN, support, recall, specificity, precision and whole-identity conditional bootstrap intervals by fold and paired year. Rare/absent classes are not turned into reassuring zero-error rates. Confusion matrices show which classes are confused.

For omitted PFTs, nearest-angle unknown recall averages 16.5% at known rejection 3.7%. Most proxy unknowns therefore remain accepted. The declared 80%-recall/5%-known-FPR review scenario is not satisfied by this average result; physical unknown materials are less comprehensively tested still.

Existing full-NEON PFT group-conformal joint-identity coverage spans 88.4%-90.2% for plant folds, and 50.3%-83.7% for sites, against a 90% nominal target. Independent calibration is valuable but does not grant geographic exchangeability.

Brier score, log loss, reliability bins and ECE assess probability quality. Temperature scaling is fitted on separate known training identities; it does not fix domain shift automatically. Endmember Monte Carlo intervals quantify choice stability and can under-cover; they are not validated field fraction confidence intervals.

Evidence: all_class_detection_rates.csv; new_confusion.csv; prior unknown_material_detection.csv; uncertainty_calibration.csv; mixture_uncertainty.csv

## 7. Keep repeats, but do not let them dominate

NIWO supplies 58.2% of annual rows but 44.8% of unique polygon IDs. A repeated polygon can receive twice the row weight of a single-year polygon before flights or pixels are considered. This is a sampling distinction, not extra biological independence.

Choosing only the earliest proper-training observation per identity reduces narrow-PFT new-polygon BA from 86.8% to 82.2%; researcher-category BA changes from 85.8% to 84.2%. This sensitivity jointly removes temporal representation and changes weights. It does not isolate a pure weighting effect.

Recommendation: preserve every scientifically valid source observation with polygon, site, year, flight/source, product, label and QA metadata. Derive annual summaries, prototypes and endmembers separately and version them. Never erase the year/site identity by replacing the archive with a grand average.

For an equal-polygon inferential target, distribute a polygon’s total training weight across its repeated observations (for example, 1/n within that identity), and assess class/site weighting against the intended target population. Keep entire identity histories together in validation. Pixel count must not determine biological training weight.

For a new observation: preserve the original source; verify units and native coordinates; resolve GlobalID linkage and source labels; retain uncertain/unknown labels; apply documented QA; update derived summaries with provenance; and test new domains against frozen identity/site/year holdouts before retraining. Add independent truth as a separate evidence layer, never as another synthetic derivative.

Evidence: sampling_weight_effect.csv; identity_sampling.csv; brightness_sampling_sensitivity.csv; paired_polygon_changes.csv; label_hierarchy.csv

## 8. The final use decision and its criteria

Use now: reproducible descriptive characterization; conditional group contrasts; supported closed-set recognition in explicitly tested populations; sensor-response diagnostics; and exploratory endmember/mixture stress tests. Use the source-label interpretation appropriate to the question.

Classification is scientifically promising when supported folds beat the equal-class reference with conditional lower intervals. The review scenario for constrained predictive use additionally asks for at least 0.70 class recall and a 0.70 balanced-accuracy lower bound throughout its specified domain, plus an agreed ecological error tolerance and independent validation. These are necessary review aids, not automatic approvals or universal biological thresholds. Species use is downgraded to exploratory because target coverage and paired temporal transfer are poor, despite useful known-class polygon scores.

Composition is flagged nonunique when wrong-class alternatives are common at the established 0.01 residual tolerance. A hypothetical ten-percentage-point fraction application also requires RMSE no greater than 0.10, appropriate uncertainty and independent measured truth. The current evidence does not meet an operational abundance gate.

Unknown rejection review uses at least 0.80 recall at no more than 0.05 known false rejection. Current proxy-class challenges are inadequate for reliable open-world membership certification. No final-test threshold optimization is used to manufacture a pass.

The decision matrix distinguishes not ready, exploratory, scientifically promising, validated for constrained use and operationally validated. Only the single real-Landsat radiometric/spatial comparison has the narrowly constrained empirical interpretation stated there. No ecological abundance application is operationally validated.

Evidence: FINAL_READINESS_MATRIX.csv; DESIGN.md; biological_evidence_ladder.csv; class-specific support/rates

## 9. The smallest new evidence that would change the answer

First, recover original units/scaling and physical wavelength headers, especially the unresolved MicaSense export, and document polygon/material purity. This is inexpensive provenance recovery before purchasing more imagery. It can remove validity gates but cannot by itself validate abundance.

Highest scientific priority: independent co-located fraction and purity measurements at the relevant footprint, including true absences, low positive fractions and mixed materials. Use independently sampled parents/plots rather than many fraction levels from the same few spectra. This directly tests abundance, false detection and interval coverage.

Next: balanced repeated identities across additional site-year combinations, prioritizing underrepresented PFTs/species and deliberately crossing year with site. Retain a held-out acquisition/domain and independently record contemporary labels, mortality/turnover, persistent individual linkage and physiology/environment/illumination where practical. Recover dated historical field/photo evidence for retrospective image years; a later survey alone does not verify the earlier biological state. This distinguishes temporal ecology from observation conditions better than simply increasing pixel count.

Then: synchronized independent NEON, Landsat and physically verified drone observations across more sites/seasons, with common footprints and independent field references. This tests real sensor transfer rather than shared-reference convolution.

Determine sample size from the scientific error tolerance and clustered design; these data do not justify a universal number of pixels, plots or flights. Additional algorithm searches are lower priority than resolving missing truth and crossed sampling.

Evidence: NEXT_DATA_NEEDED.md; FINAL_READINESS_MATRIX.csv

## Descriptive class effects and their limits

The class-effect fraction is the proportion of weighted spectral variation explained by class centers. Each polygon identity contributes total weight one across its annual observations. The descriptive subset requires at least ten global identities per class; the identity/label support column in the recognition table refers to this subset, while actual fold eligibility can differ.

Intervals resample whole identities within classes. These are descriptive associations, not causal effects or new family-adjusted significance tests. Class count, eligible population and site/species composition differ across levels, so larger eta squared is not proof of a scientifically superior classification hierarchy.

A modest fraction of total spectral variance can coexist with accurate multivariate recognition: large within-class variation may occupy different directions from a discriminating boundary. Use the independently held-out recognition and class-error evidence for prediction decisions. The earlier blocked functional contrasts remain the confirmatory sampled-group evidence.

Evidence: biological_effect_sizes.csv; observational_support.csv; fold_support.csv; prior blocked functional results

## Methods in plain language

A metadata-only source audit found 0 exact source-image/flight/row/column pixels shared by distinct GlobalIDs among 85,706 records. This rules out that specific duplicate-pixel mechanism, not spatial autocorrelation, polygon purity or every possible geometry issue.

The main reusable statistics are tested against exact synthetic identities. Numerical validation independently reproduces saved predictions, metrics, calibration thresholds, identity roles and the balanced-panel partition. Descriptive class effects use equal identity weight and remain conditional associations, partly confounded with site/year/species.

Bootstrap intervals resample whole identities, stratified by class, retaining paired years. Different holdouts support different classes. No site-superpopulation interval, new p-value family, causal variance estimate or post-hoc best-model claim is introduced.

Evidence: FINAL_ANALYSIS_AUDIT.md; DESIGN.md; manifests/numerical_validation.json; tests/test_spectral_closure.py

## Manuscript-ready Results narrative

The source comprised 3,639 polygon identities and 4,807 polygon-year summaries across three sites, with repeated observations restricted to NIWO. In the paired NIWO panel, narrow-PFT temporal change was 0.953 times the RMS class-centroid separation, while the common year component accounted for 0.8% of total paired variation. Most variation was persistent within-class polygon structure and polygon-specific change rather than a shared year offset. Source field annotations date from 2023/2024 and were reused across image years, so the paired task evaluates retrospective labelled footprints rather than independently verified annual biological status. For full-NEON broad woody leaf habit, mean identity-held-out balanced accuracy was 96.7%; held-site accuracy averaged 90.1%, and shape-only held-site accuracy averaged 92.6%. On identical unseen NIWO targets, 2020-trained broad-label recognition changed from 95.9% to 86.3%, compared with 63.9% to 30.0% for supported species. Synthetic OLI retained useful broad discrimination (94.8% mean new-polygon accuracy), whereas mixture ambiguity, synthetic fraction error and weak omitted-class rejection prevented operational abundance conclusions. These results support conditional broad functional discrimination and retention of temporal observations, with explicit limits on finer taxonomic and mixture inference.

Interpretation boundaries: these comparisons use partial label hierarchies, differing class counts and eligible populations; they are not a causal decomposition of information loss. Broad leaf habit is inferred from woody taxa rather than measured on every polygon. Shape-only discrimination does not identify the responsible physiological mechanism. Two years at one repeated site do not define long-term temporal variance.

The report preserves negative findings: limited named-species coverage at some sites, narrow-class temporal failure, poor unknown recall, shifted uncertainty coverage and nonunique mixtures. Further fitting cannot replace missing independent mixture truth or a balanced observation design.

Evidence: all numerical master tables; original conditional inference/sensor/mixture evidence

## Validation, literature and provenance

The complete feasible offline suite, focused analytic tests, strict docs, links, formatting and numerical/lineage checks are recorded in VALIDATION.md and the checks/manifests folders. Skipped optional/network/full integrations are not represented as executed field validation. Earlier analyses remain immutable and their evidence hashes are checked.

Roberts et al. (2017), Ecography: structured ecological cross-validation. https://doi.org/10.1111/ecog.02881

Cawley and Talbot (2010), JMLR: model-selection overfitting and nested evaluation. https://www.jmlr.org/beta/papers/v11/cawley10a.html

Bioucas-Dias et al. (2012): spectral unmixing, variability and inverse-problem limits. https://doi.org/10.1109/JSTARS.2012.2194696

Angelopoulos and Bates (2021): split conformal calibration and exchangeability assumptions. https://arxiv.org/abs/2107.07511

Published methods versus adaptations, source sensor definitions, endmember-selection references and real-Landsat QA are documented in the reused P123/P126 literature/provenance records. The new balanced-panel partition is an algebraic descriptive identity, verified by exact tests; it is not presented as a fitted causal mixed-effects model.

Editable report source, five full-resolution figure sets, final readiness/evidence tables, source hashes, fitted model/membership references and the audit matrix make every numerical claim traceable. No independent fraction observations were invented. Production NEON/drone correction behavior is unchanged.

Evidence: VALIDATION.md; manifests/closure_run.json; manifests/broad_sensitivity.json; manifests/report_manifest.json; reused literature audits
