# Recommendation and comparison plan

Written after the design/code/literature audit and **before** implementing or running the new empirical comparison. Results and the final paper answer will be appended in RESULTS.md; this recommendation is not chosen by the smallest empirical p-value.

## Primary

Use a **blocked functional permutation omnibus combining maximum and wavelength-integrated standardized contrast**, with one plant/year curve per unit and exact shared flight/source histories as the primary conditioning design. Calibrate the combination with synchronized permutations (a Tippett/min-partial-p nonparametric combination), not an uncorrected minimum of two p-values. This explicitly protects both localized and broad distributed alternatives. Rank methods, energy and FPCA are sensitivities, not additional ways to claim a primary positive result.

This is a small additive extension of the existing test. Keep the existing variance scale, contrast estimand, biological units and preprocessing so method differences are interpretable. Record the precise strong exchangeability null; do not call it a pure equal-means test under arbitrary unequal covariance. No statistic overcomes species/PFT aliasing.

For the paper's primary family, use corrected NEON and the 21 existing eligible matched-history cohort/pair contrasts, with Holm across those contrasts. Site/year-only comparisons answer a different, broader sampled-mixture question and form a separately declared sensitivity family. Report the legacy 324-family values alongside the common per-method family so a significance change caused by multiplicity is not called a method improvement. The audit compares all 54 eligible corrected contrasts on the same units for each method; no post-hoc family pruning by p-value.

## Why this primary / ranked alternatives

1. **Synchronized max+integrated functional omnibus:** direct design match, no unsupported covariance inversion, local/distributed coverage; finite-sample permutation calibration under the stated null. It may sacrifice some max-only power and is not asserted universally most powerful.
2. **Current scaled maximum with a simultaneous scaled-MAD null envelope:** retain as the localization component and close sensitivity/baseline. A maximum test alone remains a very defensible primary when a localized alternative is specified scientifically. The audit will not replace it merely for complexity.
3. **Blocked energy distance:** distributional sensitivity; can detect spread/shape absent a mean change. Interpret disagreement as a target difference. Predeclare metric/scaling; no bandwidth tuning.
4. **Label-blind FPCA block fixed-effects score model:** FDA sensitivity to dominant covariance directions. Select 95% variance with cap 10 and rank/df bounds using no PFT labels. It cannot guarantee detection of low-variance functional differences.
5. **Observation-level functional mixed/spatial model:** future mechanistic/context model after adequate taxon/spatial replication and covariates. A random-species formulation is assumption-dependent; unrestricted species fixed effects plus PFT are aliased here.

## Simultaneous figure

Retain the signed A−B contrast and all blocked permutation contrast curves. Use an established fixed-scale maximum absolute deviation envelope: c is the finite Monte Carlo order-statistic critical maximum and the null band is ±c*s(lambda)/sqrt(q). It is simultaneous over the supported discrete wavelength domain, with strict excursions and conservative ties. Provide 95% within-contrast and Bonferroni-across-primary-family envelopes separately. The latter can be more conservative than Holm scalar decisions. Never substitute pointwise permutation or bootstrap quantiles.

The envelope graphically represents the max component, **not** the entire combined NPC test. A broad NPC/integrated rejection without an excursion is not a contradiction and must not be assigned “significant wavelengths” from the omnibus alone. Do not present this as an ERL implementation: GET's rank/ERL constructions are reviewed, but a reference R runtime is unavailable.

## Empirical comparison before interpretation

Use the exact same plant membership/complete bands/blocking for max, its envelope, integrated, energy and FPCA. Reproduce legacy max probabilities from identical permutations first. Compute synchronized max/integrated NPC from the observed+permuted statistics, including conservative ranks/ties. Compare DBS–ECT, DBT–ECT, DBT–ECS and conditioning losses explicitly. Compare signed 2023 cross-site curves on common supported bands; NIWO 2020 is an additional repeated-site view. Investigate disagreements through estimand, localization, projection variance, distributional shape, support loss and family definition, never pick whichever test rejects.

## Calibration and validation

Simulate smooth correlated spectra with unequal PFT counts in acquisition blocks, shared acquisition curves, multiple observations per plant reduced before inference, common atmospheric gaps and isolated unsupported samples. Prespecify exchangeable null, block-confounded null, localized, broad weak, amplitude and shape alternatives. Include unequal-covariance equal-mean and species-cluster/no-PFT-coefficient stress scenarios, clearly outside the exact exchangeability or species-independent interpretation. Include a deliberately naive repeated-row control to expose pseudoreplication.

Use at least 200 independent datasets per scenario and 499 permutations initially, with Wilson uncertainty for rejection rates. These are finite Monte Carlo diagnostics, not proof of universal validity; expand ambiguous null rates rather than using them as evidence of power. Report rank sensitivity and covariance alternatives without calling a valid distributional rejection a false positive for a weaker mean null.

Do not fit H4–H6 by relabeling an association test. Before any classification study, specify deployment context and species/site/plant grouped folds, require class support, fit preprocessing inside training and measure balanced sensitivity/specificity and uncertainty against a baseline. ECS leave-one-species-out cannot train its own class. No full five-class generalization claim is available now.

## Do not use

- Pixels, individual wavelength samples, quantile lines or repeated flight rows as independent plants.
- Off-the-shelf iid functional ANOVA/PERMANOVA/MMD with no acquisition or plant design.
- Full-band classical Hotelling inversion in singular/small groups.
- Species+PFT unrestricted fixed-effect formulas, an unsupported site×year factorial model, or a random effect to manufacture a missing taxon replicate.
- Global pointwise “95% envelopes”, smoothing/imputation across spectral gaps, p-value rankings of processing quality, or equivalence claims without a biological margin.

## Future data needed

Prioritize independent species replication for ECS/EBS across shared sites/acquisitions, measured individual traits, spatial/crown covariates and identity reconciliation. More plants of the same sole ECS species cannot by itself identify a species-independent ECS effect.

Provisional paper claim: **The sampled PFT-labeled species mixtures show conditional whole-spectrum association within specified acquisition contexts.** Which contrasts survive and whether the omnibus adds useful broad-signal sensitivity will be reported from the calibrated empirical comparison, not assumed here. This claim excludes species-independent mechanism, generalization and classification accuracy.

## Final decision after empirical and calibration checks

Retain the ranked recommendation above. The calibrated **synchronized max-plus-integrated omnibus** is the single recommended primary test for the conditional sampled-mixture question. The integrated component is q × the wavelength-weighted squared standardized contrast, closely related to the old descriptive RMS, but now its permutation distribution is actually tested. The maximum remains indispensable for localized alternatives and graphical localization; its simultaneous envelope is not an independent second confirmation.

The [results](RESULTS.md) provide all 21 matched contrasts, disagreement diagnostics, three-site curve consistency, 11,000 simulated datasets plus the 4,000-dataset null extension (15,000 unique datasets total), and uncertainty in calibration/power. The strongest broadleaf/conifer-tree conclusions persist; weak or species-limited contrasts do not justify a universal PFT mechanism. Do not label the narrower 21-contrast correction confirmatory: the data and earlier 324-family results had already been explored. Preserve both families' results.

The current maximum test was not statistically displaced by an exotic model: its raw probabilities were reproduced exactly and it remains a key component. The extension is justified by the prespecified broad-signal question and the simulated power/calibration tradeoff, not by stronger empirical significance. Species-independent effects and classification remain separate, unestablished questions.
