# Can we tell the functional groups apart?

Some groups differ strongly in the sampled spectra; others overlap or lack
robust matched support. The primary conclusion concerns the sampled plants and
species mixtures, conditional on recorded acquisition histories. It is not a
validated classifier for an unknown plant, new species or new region.

## Compare whole curves, not thousands of independent bands

A biological observation is a polygon/year curve. Comparisons use mixed blocks
sharing the exact flight/source acquisition history, within site/year cohorts.
Whole labels move within these blocks during permutation, preserving wavelength
covariance. The synchronized maximum and integrated tests combine into one
nonparametric combination (NPC) probability, with the declared family adjusted
for multiple comparisons. No exchangeable mixed block means no supported test.

The plotted effect is the standardized RMS contrast
`sqrt(sum w * (beta / s)**2)`: beta is the block-centered mean coefficient and s
is a fixed label-independent within-block spectral SD. This removes the
sample-size multiplier in the test statistic. It is not Cohen's d. A small
p-value does not establish large separation or nonoverlapping individuals.

DBS–ECT and DBT–ECT show repeated strong contrasts across the represented
cohorts. DBT–ECS is weak/unsupported in the eligible NIWO cohorts. The borderline
NIWO 2023 DBS–DBT result is sensitive to family/representation choices. The
[method audit](../validation/pft-methods.md) explains these limits and the
separate roles of scalar significance and spectral localization.

## Keep label hierarchies separate

Inferred PFTs are derived from species names; researcher cover categories come
from source annotations and include nonliving material. The latter provide
broader coverage, not an independent biological experiment. Their strong
conditional associations do not resolve species/PFT confounding.

--8<-- "docs/spectral-library/_transfer.md"

## What the evidence establishes

- Spectral differentiation: conditional differences among the sampled groups.
- Localization: wavelengths exceeding a specified simultaneous **null** envelope.
- Effect magnitude: descriptive standardized separation at stated support.

It does **not** establish classification accuracy, a causal PFT mechanism,
universal cross-site generalization or MESMA abundance recoverability. Repeated
years and overlapping contrasts share plants and are not independent trials.
Acquisition matching controls recorded histories, not all ecological/spatial
confounding. See [sensor retention](sensor-transfer.md) for the paired resolution
experiment and its publication figure.

[Audited methodology and results](https://github.com/earthlab/spectralbridge/tree/main/provenance/pft-audit/2026-10-14)
· [Researcher-category evidence](https://github.com/earthlab/spectralbridge/tree/main/provenance/researcher-pft/2026-10-14)
