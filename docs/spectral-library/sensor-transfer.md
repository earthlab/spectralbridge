# What researcher-category information survives synthetic Landsat reduction?

The paired synthetic experiment uses corrected NEON and seven undarkened OLI
channels on identical polygon/year support. The five recorded researcher
categories are the only primary biological groups.

All forty researcher-category whole-spectrum contrasts retain combined-test
support in synthetic OLI. This does not mean all magnitudes or prediction scores
are preserved: significance, effect size and held-out recognition are different
quantities. The new information atlas maps individual-channel discrimination,
configured OLI response regions and nested full-spectrum-versus-OLI prediction.

Synthetic OLI changes spectral response at native/polygon support. It is **not**
an independent satellite observation and does not spatially aggregate a sparse
polygon sample into a 30 m satellite footprint. FWHM annotations indicate the
configured response interval; Gaussian tails extend beyond that interval.

The source brightness adjustment applies fixed positive bandwise gains.
Standardized contrasts are scale-invariant, so their stability under this
adjustment does not validate absolute radiometry. A separate
[real-Landsat pilot](../validation/landsat-pilot.md) compares one independent
next-day R10C acquisition pair at matched 30 m support. Its scope remains one
flight/scene, not regional calibration.

MicaSense physical band identities remain unresolved. No guessed wavelengths,
physical transfer result or independent drone-validation claim is included.

[Canonical researcher-category analysis](https://github.com/earthlab/spectralbridge/tree/main/provenance/researcher-pft-information/2026-10-15/v1)
provides paired NEON/OLI class-specific recognition and synthetic-fraction results.

## Current recognition result and mathematical interpretation

Full NEON → configured sensor representation → synthetic OLI asks **how much
information survives**. Mean balanced accuracy falls from **85.2% to 66.8%** for
unseen polygons and from **73.8% to 57.7%** for held sites in the primary
[recognition table](https://github.com/earthlab/spectralbridge/blob/main/provenance/researcher-pft-information/2026-10-15/v1/tables/complementary_feature_performance.csv).
All forty observed researcher-category combined-test contrasts retain support;
significance and recognition performance are different quantities.

![Paired standardized spectral-effect retention across category pairs and cohorts.](../images/spectral-library/current-separability.png)

**What you see:** paired NEON/synthetic OLI effect comparisons.
**What to notice:** retention varies by category pair/domain; standardized ratios
can exceed one when within-class variability is smoothed.
**What it means:** some group information survives response reduction, with losses
in predictive performance.
**What it does not mean:** synthetic OLI is equivalent to a real Landsat acquisition
or validates cross-platform physical calibration.

The [formal result](mathematical-guarantees.md) explains a compatible mechanism:
a fixed transformation can preserve the ideal mixture equation while collapsing
information needed to distinguish compositions. It does not prove that this
mechanism alone causes the observed accuracy gap.

## Run this analysis with SpectralBridge

```python
import numpy as np
from spectralbridge.library_analysis import compare_representations
rng = np.random.default_rng(4)
y = np.repeat(['A', 'B'], 18)
x = rng.normal(size=(36, 6)) + (y == 'B')[:, None]
result = compare_representations(
    {'original': x, 'two_coordinate_view': x[:, :2]}, y, np.arange(36),
    folds=3, inner_folds=2,
)
print(result['summary'])
```

Representations must have exactly the same row order and identity lineage.
The method compares classifiers with identical outer/inner split rules and
independent training-only preprocessing. Supply `domains=` for paired held-domain
scores and transfer penalties; results include dimensions, recall, confusion and
reference differences. It does not manufacture independently measured sensor data.
