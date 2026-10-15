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

## Integrated information-retention audit

The 2026-10-14 integrated audit connects biological differences to whole-plant,
acquisition, year and site holdouts, training-only wavelength selection, prototype
coverage, withheld-class rejection and calibration. It reuses the canonical
functional, sensor and mixture evidence rather than treating classification as
abundance validation. Full-spectrum logistic recognition is strong for held-out
plants in this sample; site transfer is uneven and unknown-class rejection weak.

The experimental workflow requires the optional `analytics` extra. Its staged
entry point is `examples/spectral_library_analytics.py`; `--stage profile` measures
proper-training cost, while explicit learning/extensions/domains/mixtures stages
run the declared experiments. `--stage all` completes secondary diagnostics before
sealing the learning ledger. Training-only preprocessing, GlobalID purging and
independent calibration are required. This is not a stable top-level package API.

The source-specific human PDF, editable narrative, master tables, code-linked
model index, figures and checks are recorded under
`provenance/spectral-library-analytics/2026-10-14/`. The report is generated at
`output/pdf/spectral_library_analytics/SpectralBridge_Spectral_Library_Analytics_Report.pdf`.
Read its evidence dimensions and limitations before drawing a deployment claim.
