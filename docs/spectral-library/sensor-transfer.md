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
