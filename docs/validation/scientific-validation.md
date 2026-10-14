# How do we know SpectralBridge works?

Evidence has several levels. Correct mathematics and complete files are
necessary; neither proves a broad ecological application works.

| Level | Evidence | What remains outside that claim |
|---|---|---|
| 1. Mathematical correctness | Analytic spectra/fractions, independent constrained optimizer, QA/scaling/geometry tests | Real-world measurement accuracy |
| 2. Pipeline contracts | IO, orientation, ancillary alignment, chunking, filename contracts, restart and source immutability | External sensor agreement |
| 3. Biological association | Whole-curve conditional permutation analysis; researcher labels and inferred PFTs separate | Causal functional mechanisms, novel-species classification |
| 4. Synthetic sensor reduction | Paired memberships/history, effect/direction/rank retention in OLI | Independent satellite or drone observations |
| 5. Real-sensor comparison | One independently selected next-day R10C/OLI pilot with QA, footprint and uncertainty checks | Multisite/general sensor interchangeability |
| 6. Mixture/abundance inference | Experimental synthetic fraction recovery and ambiguity tests | Operational ecological fraction accuracy; incomplete independent truth |

Read [execution versus QA evidence](evidence-hierarchy.md),
[whole-spectrum methods](pft-methods.md), [real Landsat](landsat-pilot.md) and
[MESMA readiness](../spectral-library/mesma-readiness.md) for the detailed scopes.
The [test hierarchy](../dev/scientific-testing.md) explains what automated tests
protect. Canonical reports keep full memberships, seeds, hashes and failures;
website figures summarize rather than replace them.

## Known limitations

Library physical scaling remains unresolved; use stored units until source
metadata confirms a conversion. Multiple wavelength grids and structural NaNs
must not be zero-filled into a universal spectrum. Species/PFT and environmental
composition are confounded. Repeated plants, years, overlapping contrasts and
shared source spectra are dependent. MicaSense physical coordinates remain
blocked in the current library export. Synthetic OLI shares its parent NEON
source. The real pilot has a next-day lag and legacy timezone caveat. Independent
pure-material and full fractional-cover truth are missing.

Passing a test or threshold does not eliminate these limitations. New geographic,
sensor or ecological applications require validation designed for that target.
