# Current PFT method audit

Audit: 2026-10-14. This is an audit of `src/spectralbridge/plant_pft_statistics.py`, its tests/CLI, `plant_spectral_years.py`, `plant_spectral_pfts.py`, the atlas/harmonization helpers, saved statistics manifest and `CONCLUSIONS.md`. The existing results are preserved. Source manifest fingerprint and measured design counts are in [DESIGN_METRICS.json](DESIGN_METRICS.json). This document was written before implementing the comparison extension; empirical/calibration findings will be appended separately.

## Reconstruction from code

1. `_model_inputs` verifies compact product checksums and source identity. Original union-schema pixels are not read as a universal spectral axis. The atlas had reconstructed native grids, interpolated only adjacent supported samples onto 385–2510 nm in 5 nm steps, and excluded 1340–1450 and 1790–2000 nm without bridging gaps. Finite negative values survive; original scaling is not invented.
2. `_year_plant_spectra` takes equal-observation per-band medians within GlobalID/site/year. In this dataset each plant/flight/source has one local polygon record, so observations also correspond to flights. GlobalID is a stable crown/plant proxy, not proof that distinct polygons are biologically or spatially independent. It rejects inconsistent labels/sites, duplicate observation keys and inconsistent acquisition dates.
3. A curated species-name lookup assigns 1,944 of 2,496 identities to five PFTs. This yields 2,659 assigned plant-years. It does not require the earlier 10-plants-per-species display threshold. Typical species traits are inferred, not individually measured. Unassigned plants are excluded explicitly.
4. Each of four site/year cohorts is analyzed separately. `site_year` is one unrestricted block within that cohort. `flight_history` conditions on an exact set of flight/source-image pairs; mixed-PFT history cells alone contribute. The latter changes both the estimand and sample composition, not just the standard error. At least 10 retained plants per PFT is a support rule, not a demonstration of adequate power.
5. For binary z=1(A), z=0(B), let x=z−blockmean(z), Yc=Y−blockmean(Y), q=x'x. Then beta(lambda)=x'Yc/q is a block fixed-effects coefficient, weighting block-specific A−B differences by nA*nB/(nA+nB). Only complete, variable bands on retained plants are used; no imputation occurs.
6. s²(lambda)=sum(Yc²)/(n−number_of_blocks). This label-independent SD **includes PFT-associated variation**, unlike a within-PFT residual SD or Welch standard error. T(lambda)=sqrt(q)*beta(lambda)/s(lambda) is null-scaled; it is not an ordinary Welch t statistic. Fixed within-block counts make q and s invariant across permutations.
7. The inferential statistic is max_lambda |T(lambda)|. All bands of each plant move together when PFT labels are permuted within a block. There are 9,999 draws, inclusive upper-tail comparisons with a numerical tie tolerance, and (exceedances+1)/10,000 probabilities. Wavelength dependence is preserved by joint permutation, not estimated by a parametric covariance matrix.
8. The rank sensitivity first average-tie ranks each band **within each block**, then applies a separately scaled maximum statistic with the same label permutations. It tests ordering/distributional association; it is not a robustness proof for a mean-only effect.
9. The displayed RMS is sqrt(mean_lambda((beta/s)²)). It is a descriptive standardized contrast, **not the test statistic**, not Cohen's d, not classification accuracy, not an integral over a continuous spectrum, and not wavelength-length weighted. Equal-grid sampling mostly approximates equal-length weighting except segment endpoints.
10. All 162 estimable contrasts × two test versions form one 324-test Holm family across products, cohorts and conditioning. The scalar band probabilities use the permutation maximum across wavelengths, then Bonferroni ×324. Holm can differ from these conservative band decisions. A whole-curve rejection need not identify a band under the stricter across-family band threshold.
11. Bootstrap: 999 independent resamples inside each PFT/history cell, recomputing the same coefficient with fixed cell sizes. Pointwise percentile intervals and RMS intervals are descriptive, not simultaneous bands. Singleton cells contribute no estimated bootstrap variance. Positive RMS bias means its interval cannot test a zero functional effect.

## Exact null and validity boundary

The finite-sample randomization argument requires the **joint distribution of whole plant curves to be invariant under the permitted label permutations, conditional on block membership and counts**. Identical independent curve distributions within a block suffice. It is a strong exchangeability null, not merely equality of group mean curves. Distinct covariance/dispersion, species clustering, crown proximity, label-dependent measurement error or other residual dependence can invalidate an interpretation as an exact equal-means test.

This is observational labeling; no randomized PFT assignment exists. Conditioning on flight history controls recorded exposure sets, not all plant location, species, canopy structure, illumination or microenvironment. Shared acquisition effects common to a block cancel additively; interactions and spatial covariance can remain. NIWO repeated years are never pooled as independent plants in one test, and dependence across tests does not defeat Holm, but two NIWO years are not independent replication of a site.

Under its stated null, the code's max statistic, nonzero Monte Carlo probabilities and scalar multiplicity calculations are defensible. The biological exchangeability assumption is not verified by passing unit tests. [Winkler et al. (2014)](https://doi.org/10.1016/j.neuroimage.2014.01.060) distinguish nuisance adjustment from exchangeability design; [Chung & Romano (2013)](https://doi.org/10.1214/13-AOS1090) distinguish distributional permutation validity from robustness for weaker parameter nulls. A more elaborate statistic cannot repair wrong permutable units.

## What the present conclusions do and do not establish

They support conditional, exploratory H1/H2 association among the sampled plants/species mixtures, subject to those assumptions. Mean and rank agreement is useful sensitivity evidence, not independent replication. H3 currently consists of recurring rejections; it still needs direction/shape comparison. H4 is not established: species and PFT fixed effects are exactly aliased. H5/H6 are not evaluated. Nonsignificance is not equivalence.

The earlier claim that the 1550–1785 nm mean contrast recurs is a statement about corrected spectra, selected cohorts and the conservative band family. It is not a biochemical attribution. The 13/21 matched-flight contrasts passing both tests are cohort contrasts, not 13 independent PFT relationships.

## Weaknesses to address without rewriting the analysis

- Give the observed contrast a legitimate simultaneous null envelope; existing bootstrap ribbons are not one.
- Add a wavelength-weighted integrated statistic for distributed weak signals. Combine max/integrated using synchronized permutation calibration rather than selecting the smaller uncalibrated p-value.
- Distinguish sensitivity families from the primary scientific family. The present 324-test family is defensible but mixes three dependent representations, two conditioning targets and two test versions; it is not the only defensible predeclared family.
- Reproduce the existing raw p-values exactly before interpreting method differences; report old and common-family adjustments to expose multiplicity-driven differences.
- Compare a distributional statistic with mean-focused statistics; disagreement can reveal distribution shape, not that one test is wrong.
- Quantify type-I error only under each method's actual null. Heteroscedastic equal-means simulations are outside the exchangeability null; species-random-effect simulations address H4 and cannot validate H1 plant permutations for H4.
- Evaluate support loss, singleton cells, species dominance, curve direction, source quality and Monte Carlo uncertainty. Minimum unadjusted p=0.0001 yields repeated adjusted p=0.0324 in the legacy family; these are resolution-limited evidence, not equal effect strengths.
- Formal strong wavelength attribution under partial nulls requires exchangeability/subset-validity assumptions for null-band vectors. An overall permutation rejection under arbitrary heterogeneity is not blanket validation of every band-specific mean claim.

No runtime correction, scaling, spectral response or source dataset changes are justified by this audit.
