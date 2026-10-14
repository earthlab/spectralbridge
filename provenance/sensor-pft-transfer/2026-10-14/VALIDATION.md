# Validation and scope

## Tests and documentation

- Full repository suite: **580 passed, 7 skipped, 29 warnings**, 112.94 seconds.
  Command: `CSCAL_TEST_MODE=unit pytest -q -o addopts=`, with Matplotlib cache in
  `/tmp` and BLAS thread counts limited to one. This is the complete configured
  offline/unit suite, not an assertion that unavailable network/external-data
  tests ran. Skip counts remain explicit. Warnings are the reported dependency,
  all-NaN diagnostic and pandas deprecation notices; no failures occurred.
- Targeted sensor/core tests: **17 passed**. They cover observation intersection
  before medians, metadata conflicts/duplicate identities, OLI coordinate
  validation and MicaSense blocking, coupled repeated-year cluster weights,
  fixed cell counts, bootstrap sufficient moments against expanded rows,
  positive-gain invariance, response-support projection, full synthetic end-to-end
  inference and checksum-valid restart, plus default-core numerical regression.
- Focused Ruff passes. Source documentation links and strict MkDocs build pass.
  Generated AI-transparency artifacts are checked after verbatim prompt logging.
- Primary behavior change is an optional explicit band-weight argument in the
  audited core. Default wavelength integration is unchanged and tested against
  explicit legacy weights and the legacy max test. The new runner is additive;
  no resampling kernels, brightness coefficients or pipeline outputs were altered.

## Source and metadata

Source SHA-256:
`cd3a8afd2697f09d1f4749f92df8a5e2cc71ee12490d38de12f21f90b2a75978`.
The original merged Parquet was read in place, not copied or rewritten. Projection
and band batches bound source reads; derived checkpoints contain compact
polygon/acquisition medians and model/bootstrap arrays, not a pixel cache.

OLI's seven implemented band identities are coherent with the packaged metadata
and strongly numerically consistent with a Gaussian reduction of corrected NEON.
Original historical headers/exact kernels are unavailable, so results are for the
stored synthetic OLI-like representation, not an assertion of exact manufacturer
response functions. MicaSense physical coordinates FAIL validation and its
biological branch was not run. Availability is not confused with validity:
all ten stored MicaSense values are present, but their mapping remains unverified.

## Pairing and analytical replication

All 12,504 polygon/acquisition observations, 4,807 polygon/year spectra and 3,639
polygon IDs survive the admitted NEON/OLI common-support intersection. There is
no sensor-specific sample loss. The inferred analysis has 1,944 assigned IDs;
the researcher analysis includes all 3,639. Row/pixel/flight repetitions are
reduced before inference. Exact flight/source histories are identical across
representations, including the mixed-block membership for each contrast.
Memberships retain verbatim species, category, site/year, GlobalID and history.

All **21** eligible inferred-PFT and **40** researcher-category NEON comparisons
reproduce legacy raw AND Holm-adjusted max/integrated/NPC p-values exactly on
identical common support. `legacy_reproduction.csv` records those checks. Existing
P116 statistics, P117 empirical audit and P118 researcher-class output ledgers
were rechecked unchanged; no old conclusions were overwritten.

No OLI bands are interpolated into continuous spectra. OLI weights are explicit
equal channels; FWHM weights are a separately declared sensitivity. Native NEON
uses disconnected supported intervals, and projected direction diagnostics report
response mass available after atmospheric exclusions. Both schemes retain all
360 complete, variable native test wavelengths. Every analysis checkpoint's
bootstrap effect/band arrays is finite. Discrete coordinates and equal weights
are verified; stored darkening changes standardized effects by less than 9e-8.

## Uncertainty and retention

The primary NPC family is fixed separately by label system and representation:
21 inferred comparisons and 40 researcher comparisons. FWHM results are
sensitivities and no union of methods/labels is declared. Permutations are
synchronized across sensors by shared legacy-compatible seed and identical
membership/blocks. The recorded NEON replication additionally checks that default
permutation order and component calibration remained stable.

499 GlobalID bootstrap replicates couple sensors, shared contrasts and repeated
years. Site/label/joint-history strata hold block/class counts fixed. Counts are
342 strata/120 singleton for inferred labels and 594/169 for researcher labels;
singletons do not generate bootstrap variability. All reported intervals are
conditional descriptive percentile intervals, not simultaneous bands or
random-site generalization. Retention percentages are descriptive summaries of
dependent contrasts, with no binomial trials or intervals. Ratios are guarded
against a NEON RMS denominator <=0.1; no empirical ratio needs that suppression.
Different spectral norms mean ratios are not literal information fractions.

## Restart, figures and reproducibility

All analysis-owned hashes and current code fingerprints were checked. Repeating
the complete runner reuses the verified manifest and leaves every owned output
mtime unchanged. Checksums distinguish scientific analysis, source audit,
interpretation and figures. `statistics_manifest.json` names the analysis root
explicitly, so compact provenance records do not pretend to contain ignored
source spectra/checkpoints.

A (separate label-system heatmaps), B (paired effects), C (strong signed
exemplars), D (within-cohort ranks) and E (ratio intervals) are produced in
PDF/PNG/SVG. Figure C uses disconnected NEON support and separate OLI channel
points with pointwise bootstrap intervals. All MicaSense panels are visibly
blocked. Figure captions distinguish insufficient support from metadata failure,
descriptive effect norms from accuracy, and localization from effect uncertainty.
PNG renderings are visually inspected, including labels, captions and intervals;
PDF and SVG outputs retain vector content and text.

## Remaining scientific limits

Exchangeability is an observational assumption. Spatial autocorrelation,
species composition, canopy/substrate and historical processing provenance are
not resolved by matching flights. This is not a mixed-species causal model,
held-out classifier, equivalence test, independent sensor validation or
random-population test of regional transfer. The lost borderline NEON detection
cannot by itself establish an intrinsically hyperspectral-only biological effect.
MicaSense requires original band/header/SRF provenance or an explicitly separate
verified regeneration before inference can proceed.
