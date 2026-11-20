!!! note "Historical / exploratory workflow sections"
    Species-derived grouping examples on this page are retained for historical
    reproduction. The primary analysis now uses only recorded researcher
    `cover_category` labels; see [the canonical label policy](../spectral-library/labels.md).

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

## Current five-category HLS and drone studies

The [HLS pure-pixel study](landsat-pilot.md#which-tests-verify-what) and
[drone calibration comparisons](drone-findings.md#did-masking-reduce-pft-information)
use the recorded five researcher categories. Their sampling units and families
are study-specific; they do not inherit the historical 21 inferred-PFT family
below. A significant difference is a lower evidential requirement than accurate
recognition, but the actual finite-sample tests and power need not be nested.
They can give different outcomes without a contradiction.

For Figure 4 HLS, seven direct-reflectance patch medians feed whole-patch NPC
and fixed-classifier LOPO. Cells in the same patch do not become independent
replicates. Holm covers ten planned pairs; exact enumeration is used up to
100,000 assignments, otherwise observed + 99,999 reproducible assignments. Pooled and
within-region support are reported separately; missing mixed-region support
cannot be fixed by changing a p-value threshold.

The masked/null drone study uses five translated channels, original polygon
identities, site blocking and paired folds. The separate BRDF-benefit audit uses
identity-grouped histories and matched stage comparisons, with separate Holm
families of 10 recognition, 96 arm-specific NPC and 48 separation-change contrasts.
Conditional identity-bootstrap intervals keep fitted models fixed; whole-site
swaps separately expose the limited independent-site count. No significance,
failed-class score or independent validation is manufactured for unsupported
comparisons. Full protocols accompany each linked study.

The following exact-history/species-derived account remains a historical method
record; it is not the definition of the current five-category Figure 4 table.

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
