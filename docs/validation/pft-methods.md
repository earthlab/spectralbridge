# How do the whole-spectrum tests work?

The [biological analysis](../spectral-library/biological-variation.md) compares
sampled group curves under conditional label exchangeability. Tests validate an
explicit null and sampling design; they do not remove species, spatial or
unrecorded acquisition confounding.

| Method | Question / statistic | Interpretation limit |
|---|---|---|
| Maximum | Largest absolute standardized contrast across supported wavelengths | Sensitive to a localized excursion; null envelope is not an effect confidence band |
| Integrated | Weighted sum of squared standardized contrasts | Sensitive to distributed differences; atmospheric gaps have no area |
| NPC | Synchronized Tippett combination of maximum and integrated permutation probabilities | Calibrated against the joint ensemble, not an uncorrected minimum p |
| Rank sensitivity | Rank-based contrast comparison in the earlier framework | Different estimand; robust ordering is not automatically a mean effect |
| Energy sensitivity | Within-block multivariate distribution-distance statistic | Can detect distribution/dispersion changes without a mean shift |
| FPCA sensitivity | Test in a fixed label-independent spectral principal-component subspace | Retained rank/variance choices can affect power; not proof from a PCA picture |

## Permute the right unit

Labels move as whole polygon/year curves within exact flight/source-history
blocks. This preserves wavelength covariance and block membership. It assumes
exchangeability conditional on the block, not merely equal means under arbitrary
covariance differences. Single-class histories do not supply within-block
contrasts. Pixel duplication must not create extra independent plants; the
atlas aggregates before inference. Repeated GlobalIDs across years are coupled
in the cluster bootstrap rather than resampled as unrelated plants.

The primary family contains 21 eligible inferred-PFT contrasts in this dataset.
Holm-adjusted scalar probabilities control that declared family. The plotted
maximum-component localization uses a fixed Bonferroni family envelope, which can
be more conservative than Holm. An NPC-supported curve need not cross the
maximum envelope if support is distributed. Pointwise bootstrap intervals are
uncertainty aids, not simultaneous evidence across all bands.

## Why the audit matters

Strong repeated DBS–ECT and DBT–ECT contrasts survive several checks. Weak
DBT–ECS and borderline DBS–DBT findings should not be rewritten as universal
separability. The inferred PFTs are attached to species; the design concerns the
sampled mixtures of taxa, not a species-independent functional mechanism.
Biological replicate counts, missing support, exact histories and multiplicity
families are retained in the numerical tables.

[Full method review and simulations](https://github.com/earthlab/spectralbridge/tree/main/provenance/pft-audit/2026-10-14)
· [Module contracts](../api/scientific-analysis.md)
· [Scientific testing philosophy](../dev/scientific-testing.md)
