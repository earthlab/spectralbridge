# Results, calibrated recommendation and paper claim

Audit date: 2026-10-14. Existing outputs remain unchanged. See the four audit/review/design/recommendation documents in this directory. This is an exploratory analysis following inspection of the plots and earlier results, not a prospectively registered confirmatory study.

## What was run

54 eligible corrected-NEON contrasts, exactly the same units, supported bands and blocks across methods, with 9,999 permutations each. Every maximum-test raw p-value reproduces its legacy value exactly. All methods use the same plants: agreement is sensitivity evidence, not independent biological replication. Maximum envelopes are the same test visualized, not an independent confirmation. Integrated and FPCA contrasts are functional-response fixed-block adaptations; energy is a predeclared block-weighted distance adaptation. GET ERL and full functional mixed models were reviewed but not executed (R unavailable; unrestricted species+PFT effects aliased).

The primary family is the 21 acquisition-matched corrected contrasts. Methods are compared with Holm across that same 21-member family each; site/year-only sensitivity uses 33. This is different from the old combined 324-test family. The complete legacy values and a fixed Bonferroni×324 sensitivity for each new method are retained. Smaller adjusted values caused by changing the family are not new biological evidence. No union-of-methods rejection rule is used. Repeated adjusted p=0.0021 values reflect the 0.0001 Monte Carlo floor in a 21-test family, not identical biological effect strengths.

The graph scales A−B by s(lambda)/sqrt(q), a fixed, label-invariant variance proxy. It is not a Welch SE or necessarily the exact permutation SD when block variances differ. Envelope validity uses fixed scaling plus whole-curve exchangeability, not that proxy being a perfect variance estimator. The CSV field null_se names this proxy; it must be interpreted accordingly.

## Empirical method comparison

| cohort | pair | legacy max (324) | max (21) | integrated (21) | npc (21) | energy (21) | fpca (21) | rank (21) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| NIWO-2020 | DBS − DBT | 1 | 0.1298 | 0.3544 | 0.1794 | 0.1036 | 0.0148 | 0.1452 |
| NIWO-2020 | DBS − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| NIWO-2020 | DBT − EBS | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| NIWO-2020 | DBT − ECS | 1 | 0.0948 | 0.336 | 0.1407 | 0.1036 | 0.0021 | 0.2068 |
| NIWO-2020 | DBT − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| NIWO-2020 | ECS − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0864 |
| NIWO-2023 | DBS − DBT | 0.3248 | 0.0336 | 0.3544 | 0.045 | 0.018 | 0.307 | 0.0987 |
| NIWO-2023 | DBS − ECS | 0.6533 | 0.0595 | 0.1944 | 0.082 | 0.0035 | 0.0021 | 0.4154 |
| NIWO-2023 | DBS − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| NIWO-2023 | DBT − EBS | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| NIWO-2023 | DBT − ECS | 0.575 | 0.0595 | 0.3544 | 0.0815 | 0.1036 | 0.1149 | 0.2886 |
| NIWO-2023 | DBT − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| NIWO-2023 | EBS − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| NIWO-2023 | ECS − ECT | 0.0324 | 0.0021 | 0.0024 | 0.0028 | 0.0021 | 0.0045 | 0.191 |
| WREF-2023 | DBS − DBT | 0.0324 | 0.0021 | 0.0105 | 0.0021 | 0.0102 | 0.0021 | 0.0021 |
| WREF-2023 | DBS − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| WREF-2023 | DBT − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| YELL-2023 | DBS − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| YELL-2023 | DBT − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| YELL-2023 | EBS − ECT | 0.0324 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 | 0.0021 |
| YELL-2023 | ECS − ECT | 1 | 0.5586 | 0.6272 | 0.6164 | 0.1518 | 0.5662 | 0.9118 |

## Biological conclusions and disagreements

- **DBS–ECT and DBT–ECT:** supported by every compared method in all four cohorts, including acquisition matching. The central broadleaf-versus-conifer-tree sampled-mixture conclusion does not depend on using only a maximum statistic. This remains association among the sampled taxa, not a species-independent mechanism.
- **DBT–ECS:** max/integrated/NPC remain nonsignificant in both NIWO years. FPCA rejects in NIWO 2020 but not 2023. The projection test weights a limited whitened covariance subspace and has a different sensitivity; this isolated sensitivity result is not adopted as the primary conclusion.
- **DBS–DBT:** WREF remains supported. NIWO 2020 remains unresolved by the primary test, while FPCA alone rejects. NIWO 2023 becomes borderline (NPC adjusted p=0.045) only in the narrower 21-test family; even the unchanged max p becomes significant under that family. The fixed ×324 comparison does not support it. This is family/Monte-Carlo-sensitive, not a robust new discovery. YELL lacks minimum matched support.
- **ECS–ECT:** NIWO mean/integrated/NPC/energy/FPCA tests agree on a conditional association, whereas the legacy rank sensitivity does not. The weighted mean and weighted median contrast curves have cosines about 0.996 in both NIWO years. At their mean-statistic peak, weighted median contrasts have the same sign and similar amplitude as means. Thus the rank disagreement cannot simply be called an outlier artifact. The old rank test uses unnormalized within-block ranks: rank ranges and variance mass depend on block size (roughly cubic variance mass for untied ranks). It is not a pure neutral outlier-removal transformation. These diagnostics and unequal overlap help explain changed sensitivity; they do not prove either statistic uniformly better. ECS remains one species globally, and YELL shows no corresponding supported contrast.
- **NIWO 2023 DBS–ECS:** energy and FPCA reject while max/integrated/NPC do not. Distribution/covariance geometry and projection sensitivity differ from mean-functional evidence. Do not choose the sensitivity result with the lowest p-value.
- **Acquisition conditioning:** support shrinks and target mixtures change. A pooled significance loss can be reduced power, changed species composition or acquisition association; it is not by itself proof of a flight artifact.

## Distributional disagreement diagnostics

The table below reports descriptive pooled within-PFT/history residual trace-variance ratios (A/B), weighted-median versus mean curve cosine, and within-block Cliff delta at the mean-statistic peak. These are not new significance tests. A ratio different from one can help explain energy/projection sensitivity, but does not by itself prove why a particular p-value changed. Largest individual linear-term ratios and block rank-variance masses remain in the ignored interpretation tables for source-traceable review.

| cohort | pair | dispersion_trace_ratio_a_over_b | mean_median_curve_cosine | peak_weighted_cliffs_delta |
| --- | --- | --- | --- | --- |
| NIWO-2020 | DBT − ECS | 4.1338 | 0.9963 | 0.4154 |
| NIWO-2020 | ECS − ECT | 0.4532 | 0.9959 | 0.911 |
| NIWO-2023 | DBS − ECS | 0.1729 | 0.9787 | 0.6943 |
| NIWO-2023 | DBT − ECS | 0.6294 | 0.8616 | -0.6917 |
| NIWO-2023 | ECS − ECT | 2.1767 | 0.9967 | 0.7715 |
| YELL-2023 | ECS − ECT | 1.0892 | 0.9941 | -0.153 |

## Cross-site direction/shape (H3)

Use the three 2023 sites only for the independent-site comparison. For DBS–ECT and DBT–ECT, contrast-curve cosine similarities are positive and high; the full matrix below is descriptive rather than a random-site population test. DBS–DBT and ECS–ECT do not show a universal direction/shape. NIWO 2020 is a repeated-site view, not a fourth independent site.

| pair | site_a | site_b | bands | cosine | pearson_shape | sign_agreement |
| --- | --- | --- | --- | --- | --- | --- |
| DBS − DBT | NIWO | WREF | 360 | -0.3909 | -0.5865 | 0.5806 |
| DBS − ECT | NIWO | WREF | 360 | 0.9495 | 0.8431 | 0.9167 |
| DBS − ECT | NIWO | YELL | 360 | 0.9944 | 0.9834 | 0.9472 |
| DBS − ECT | WREF | YELL | 360 | 0.974 | 0.9164 | 0.8694 |
| DBT − ECT | NIWO | WREF | 360 | 0.9962 | 0.9901 | 0.8611 |
| DBT − ECT | NIWO | YELL | 360 | 0.939 | 0.91 | 0.7722 |
| DBT − ECT | WREF | YELL | 360 | 0.9237 | 0.8773 | 0.8667 |
| EBS − ECT | NIWO | YELL | 360 | 0.7885 | 0.8132 | 0.7972 |
| ECS − ECT | NIWO | YELL | 360 | -0.7105 | -0.3997 | 0.1083 |

## Simulation calibration and power

Nine initial scenarios plus two extreme-imbalance checks added after inspecting real support, 1,000 independently generated datasets each, 499 permutations per dataset. Curves use smooth correlated noise, unequal group sizes (including 10 versus 390 plants in the extreme check), three acquisition histories, four repeated observations reduced to one plant curve, atmospheric gaps and an isolated unsupported sample. No gap imputation occurs. Rejection rates below concern one test per simulated study, not the empirical 21-contrast multiplicity family. The generator is stylized rather than fitted to the exact crowns. These results demonstrate comparative behavior in this design, not universal optimality or validity in real spatially dependent crowns.

| scenario | energy | fpca | integrated | max | naive_max | npc |
| --- | --- | --- | --- | --- | --- | --- |
| H4_null_species_clusters | 100.0% | 90.6% | 84.6% | 86.0% | — | 86.9% |
| amplitude | 99.1% | 99.6% | 99.8% | 99.4% | — | 99.9% |
| block_confounded_null | 6.2% | 4.9% | 5.0% | 4.6% | 100.0% | 5.1% |
| broad_weak | 58.2% | 67.2% | 78.8% | 63.0% | — | 76.7% |
| exchangeable_null | 6.4% | 6.3% | 5.1% | 5.9% | — | 5.0% |
| extreme_imbalance_broad | 42.6% | 47.8% | 61.8% | 44.7% | — | 58.3% |
| extreme_imbalance_null | 5.3% | 4.4% | 4.2% | 4.9% | — | 4.8% |
| localized | 20.9% | 61.5% | 33.9% | 100.0% | — | 100.0% |
| mean_null_unequal_covariance | 100.0% | 37.4% | 27.3% | 30.6% | — | 30.5% |
| repeated_plant_null | 5.8% | 4.5% | 5.3% | 4.7% | 69.2% | 4.3% |
| shape | 76.5% | 95.2% | 95.1% | 98.1% | — | 97.2% |

The exchangeable null was expanded to 5,000 datasets after an initial noisy calibration estimate, retaining the original 1,000 and adding 4,000 independent replicates. The 95% Wilson intervals quantify Monte Carlo uncertainty in rejection rates, not uncertainty in biological effects.

| method | replicates | rate (95% MC interval) |
| --- | --- | --- |
| max | 5000 | 4.90% (4.34–5.53%) |
| integrated | 5000 | 4.80% (4.24–5.43%) |
| npc | 5000 | 4.86% (4.30–5.49%) |
| energy | 5000 | 5.00% (4.43–5.64%) |
| fpca | 5000 | 5.08% (4.51–5.72%) |

The combined test materially improves broad-weak sensitivity relative to max alone while retaining localized sensitivity in these simulations. The integrated statistic alone sacrifices localized power; NPC is not uniformly most powerful (for example, max is slightly better in the shape scenario). The NPC null rate is compatible with 5%; no gain is credited to an inflated equal-means rejection under heteroscedasticity.

The unequal-covariance scenario has equal means but different distributions: energy rejection is a true distributional alternative, and increased mean-focused rejection demonstrates why the strong exchangeability guarantee must not be recast as an arbitrary equal-means guarantee. The species-cluster scenario has no PFT coefficient but shared species functions; high rejection shows these plant-level tests cannot establish H4. Naively permuting repeated rows or ignoring strongly imbalanced acquisition blocks gives grossly misleading rejection rates.

## Exact paper recommendation

**Primary:** blocked, synchronized max-plus-integrated nonparametric combination of the whole plant contrast function, corrected NEON, exact flight/source-history conditioning, and a declared cohort/pair multiplicity family. Keep the maximum component and its simultaneous envelope as the principal graphical explanation.

**Sensitivity:** original maximum test, integrated norm, carefully interpreted rank sensitivity, energy distance and a label-blind reduced-rank functional model; show acquisition support and species composition. No method is a substitute for valid units or independent taxa.

**Claim:** “Among the sampled species mixtures, corrected whole-spectrum structure is associated with assigned PFT within matched acquisition contexts. Contrasts between sampled evergreen conifer trees and sampled deciduous broadleaf tree/shrub groups recur across NIWO, WREF and YELL. These observations do not isolate PFT from species composition, demonstrate a causal trait mechanism, or establish classification/detection accuracy.”

A colleague-facing description: We compared whole plant/year curves. Within shared acquisition histories we permuted each whole plant PFT label, preserving its entire spectrum and wavelength covariance. A synchronized combination of maximum and integrated contrast asks whether localized or distributed differences exceed those expected under that conditional exchangeability null. It gives one whole-spectrum probability; the simultaneous maximum envelope locates excursions of the maximum component, not every possible reason for combined rejection.

## Limitations and next validation

No test here establishes H4–H6. The primary guarantee is conditional on the exchangeability assumptions audited in CURRENT_METHOD_AUDIT.md. Spatial/plant identity uncertainty, inferred traits and species dominance remain. Add independent ECS/EBS taxa and spatial/field-trait covariates. A future species/site-held-out prediction study is needed for transfer/classification, with plant leakage prevented and unavailable classes explicitly excluded or abstained.

References and method-specific nulls are in METHODS_REVIEW.md. Code, seeds, supported domains, primary/sensitivity families and all output checksums are retained. The scalar and graphical thresholds differ when Holm is less conservative than the fixed Bonferroni envelope; do not reinterpret an envelope as a biological-effect confidence interval.
