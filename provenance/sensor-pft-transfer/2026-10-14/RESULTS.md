# Does the ecological pattern survive spectral reduction?

## Direct answer

**Synthetic Landsat OLI: largely yes for the sampled contrasts, with measurable effect compression and one lost borderline detection. MicaSense: currently untestable because physical band identities are unverified.** This is a paired synthetic spectral-reduction experiment, not independent satellite/drone validation or classification accuracy.

## Identical units and corrected-NEON reproduction

All 12,504 source polygon/acquisition observations are shared across corrected NEON, undarkened OLI and darkened OLI. Common support contains all 3,639 polygon IDs and 4,807 polygon/year spectra. No sensor-specific sample loss occurred. Inferred-PFT inference uses 1,944 assigned identities; researcher categories use all 3,639 identities, including 1,143 without species names. Inferred PFT codes are DBS = deciduous broadleaf shrub, DBT = deciduous broadleaf tree, EBS = evergreen broadleaf shrub, ECS = evergreen conifer shrub and ECT = evergreen conifer tree. Exact shared acquisition-history blocks and per-pair membership are identical. All 21 inferred-PFT and all 40 researcher-class corrected-NEON eligible contrasts reproduce legacy raw and adjusted max, integrated and NPC probabilities exactly.

## Landsat OLI: primary inferred-PFT results

- Detection retention: 15/16 NEON-supported contrasts (93.75%) remain supported. All 5 NEON-unsupported comparisons remain unsupported. This percentage describes dependent contrasts; it has no binomial interpretation.
- Effect retention: median OLI/NEON standardized RMS ratio 0.824 (paired conditional bootstrap 95% interval 0.801-0.889); individual ratios 0.665-1.209. Ratios compare an equal-channel metric with a wavelength-integrated metric, not a literal percent of all biological information.
- Strong DBS/ECT and DBT/ECT differences persist in all four cohorts. DBS/ECT effect ratios range 0.728-0.787; DBT/ECT 0.744-0.872. The weak DBT/ECS contrasts remain unsupported in both NIWO years. No lower-resolution superiority is inferred from a smaller p-value.
- NIWO 2023 DBS/DBT loses support: NEON adjusted NPC p=0.045, OLI p=0.855; the RMS effect falls from 0.353 to 0.234 (ratio 0.665, paired interval 0.619-0.938). The original NEON finding was already borderline/post-exploration and family-sensitive. With identical samples/history, membership loss is ruled out here; spectral averaging/coverage, changed variance, weighting and resulting statistical power remain inseparable contributors. This does not prove an intrinsically hyperspectral-only biological mechanism.

## Pattern and direction retention

- Inferred species-to-PFT labels, Pearson: 0.955, paired cluster-bootstrap 95% interval 0.930-0.965. These are correlations across a fixed, dependent set of eligible contrast/cohort effects, not 21/40 independent experiments.
- Inferred species-to-PFT labels, Spearman: 0.982, paired cluster-bootstrap 95% interval 0.921-0.994. These are correlations across a fixed, dependent set of eligible contrast/cohort effects, not 21/40 independent experiments.
- Researcher cover categories, Pearson: 0.961, paired cluster-bootstrap 95% interval 0.955-0.966. These are correlations across a fixed, dependent set of eligible contrast/cohort effects, not 21/40 independent experiments.
- Researcher cover categories, Spearman: 0.961, paired cluster-bootstrap 95% interval 0.941-0.968. These are correlations across a fixed, dependent set of eligible contrast/cohort effects, not 21/40 independent experiments.

Every corresponding OLI-band point-estimate sign agrees with its NEON projection on that band support (147/147 inferred, 280/280 researcher). This is strong internal consistency for a shared-source Gaussian reduction, not an independent validation. Both pointwise intervals exclude zero in only 99/147 and 249/280 cases respectively; do not label the other directions resolved. Projection occurs after polygon/year medians while stored OLI reduction occurs before medians, so exact equality is not assumed. Response support fractions are in band_retention.csv.

## Cross-site retention

For the strong inferred contrasts in 2023, OLI standardized signed-vector cross-site cosines are 0.871-0.944 for DBS/ECT and 0.755-0.902 for DBT/ECT. Their matched NEON projections onto the same seven response supports are almost identical (0.872-0.944 and 0.757-0.902). Native-NEON full-domain standardized cosines span 0.859-0.955 and 0.781-0.936. Thus broad cross-site pattern similarity survives, while not every individual band has the same sign across sites. These standardized cosines differ from earlier raw-beta curve cosines and should not be equated with them. All pair/site comparisons, including weak and reversing directions, are retained in cross_site_consistency.csv.

## Separate researcher-category analysis

All 40/40 corrected-NEON-supported researcher-class contrasts remain supported in OLI (100%, descriptive). Median effect ratio 1.016 (conditional paired interval 0.989-1.029). Deciduous/Evergreen effect ratios are 0.742-0.819 and Evergreen/Woody shrub ratios 0.771-0.865 across cohorts, showing that retained detection can coexist with compressed biological contrasts. The five broad researcher categories are retained as a separate label system, not pooled with inferred taxa. Non-vegetated & dead is a mixed cover comparator, not a living PFT. Broad differentiation does not imply nonoverlapping individuals.

## Likely spectral reasons and ablation limits

OLI retains two SWIR channels near 1609 and 2201 nm. All five quoted historical intervals are confirmed: every gridpoint is outside the current matched-family maximum envelope in all four cohorts (DBS/ECT: 1500-1785 and 2260-2285 nm; DBT/ECT: 955-1030, 1140-1335 and 1550-1785 nm). The verification and response coverage are recorded in neon_region_coverage.csv. Gaussian-response coverage is diagnostic, not proof that a response interval is the causal feature. OLI has no channel centered in the 955-1030 or 1140-1335 nm regions, and its SWIR2 tail samples some of the cited 2260-2285 nm interval. It therefore preserves broad SWIR-related contrasts while averaging or omitting finer features.
Descriptive OLI-without-SWIR RMS effects are supplied for every contrast on the same polygons. Removing both SWIR bands reduces the descriptive equal-channel RMS effect to 0.394-0.616 of full OLI for DBS/ECT and 0.454-0.925 for DBT/ECT. DBT/ECT is largely retained in visible/NIR at YELL (0.925). This is not a proof that SWIR alone causes distinguishability: removing channels changes the equal-channel norm as well as support. No ablation significance family or classifier result was run.

## MicaSense: no ecological inference

The source contains ten complete values per pixel but its labels (475,560,668,717,840,841,842,843,844,845 nm) match a five-band fallback plus 1-nm padding, not the intended ten-band metadata (444,475,531,560,650,668,705,717,740,842 nm). No original headers or generation provenance establish the physical mapping. We stop this branch, do not guess relabeling, and mark all MicaSense cells blocked. Its intended VNIR-only configuration motivates a future SWIR-coverage hypothesis but does not establish an empirical MicaSense result.

## Weighting, brightness and uncertainty sensitivity

Equal OLI channel weights are primary; normalized FWHM weights are a distinct sensitivity. No supported/not-supported decisions change under that sensitivity in either label system. The actual darkened/undarkened OLI ratios match positive bandwise brightness gains. Their standardized effects differ by at most 8.8e-08, consistent with scale invariance; brightness adjustment is not responsible for the reported transfer pattern.
The 499 GlobalID bootstrap draws couple sensors, overlapping contrasts and repeated NIWO years, stratifying by fixed site, label and complete joint-year history pattern. There are 342 strata (120 singleton) among 1,944 inferred IDs and 594 strata (169 singleton) among 3,639 researcher IDs. Singleton strata cannot contribute bootstrap variability. Intervals are conditional descriptive percentile intervals, not population-site uncertainty, simultaneous confidence bands or proof of exchangeability. Species/spatial confounding and earlier exploration remain.

## What is sensor-robust, what is not established?

- Sensor-robust here: strong DBS/ECT and DBT/ECT group differentiation, weak DBT/ECS non-support, broad researcher-category differentiation, and much of the effect ranking and corresponding band direction.
- Spectral-resolution sensitive here: mean standardized separation is compressed for many inferred contrasts, with a lost borderline NIWO DBS/DBT detection and altered fine-feature coverage. This does not establish that hyperspectral information is universally necessary for that contrast.
- Cannot currently test: MicaSense biological retention, independent real-sensor transfer, novel-region/species recognition, a causal PFT effect, or classification accuracy. Acquisition/spatial scale/noise differences of actual OLI or drone imagery are absent from this synthetic experiment.

## Figures and tables

A_effect_heatmap_*: identical-sample effects and NPC support, labels separated. B_effect_retention: paired NEON/OLI effects. C_strong_exemplar_contrasts: signed NEON curves and discrete OLI points with pointwise bootstrap intervals. D_contrast_rank_retention: within-cohort ordering. E_effect_ratio_intervals: paired uncertainty. All figures have PDF/PNG/SVG versions. Tables include all candidate comparisons, insufficient support, actual eligible members, bootstrap intervals, width sensitivity and MicaSense gate. See DESIGN.md, METHODS.md, SENSOR_AUDIT.md and VALIDATION.md for contracts and verification.
