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
