# Shade-excluded native correction refits

19 November 2026. This experiment refits SCS+C and BRDF after excluding the
previously frozen candidate shade masks. It is different from masking an
already corrected image. The original camera-position workflow is retained;
no original-photo reconstruction is performed.

## Main result

**The conservative refit clears the ten-band combined model-support checks at
all three sites, including Ruby.** More aggressive exclusion does not consistently
improve support and can make bands unavailable.

| Site | Original combined fit | Conservative refit | Moderate refit | Stronger refit |
|---|---:|---:|---:|---:|
| Gordon | 10/10 | 10/10 | 9/10 | 8/10 |
| Goldhill | 10/10 | 10/10 | 10/10 | 10/10 |
| Ruby | 8/10 | 10/10 | 8/10 | 8/10 |

Counts require actual `VALID` BRDF fits for all bands; `NOT_APPLICABLE` bands are
not counted as passes. Combined full-support status also requires all ten
SCS+C fits to be valid. The original Ruby combined model was rejected because
650/668 nm reference predictions were unresolved. Its conservative refit has
positive reference lower margins in both bands.

Ruby's conservative 668 nm result is **marginal**: reference prediction 0.019286,
spatial-cluster SE 0.009823, lower margin approximately 0.0000322 under the
unchanged 1.96-SE criterion (conditional physical-fraction hypothesis). The
baseline lower margin was -0.0100403. This is model support under the specified
mask, not strong independent evidence of a physically accurate correction.

More aggressive combined fits lose Ruby's native bands 9/10 (740/862 nm in
historic metadata). Gordon's moderate fit loses band 10 and stronger fit loses
bands 9/10. Some aggregate model statuses remain `VALID` despite these unavailable
bands; the table deliberately exposes that limitation. Goldhill retains all
bands at every tested exclusion.

## What changed and what stayed fixed

All three original full native training populations, SCS+C C estimates, BRDF
regression coefficients, kernel/reference settings, eligibility counts and
per-band QA statuses were reproduced before interpreting mask comparisons.
The baseline and all three prespecified candidate masks are reported; thresholds
were not iteratively tuned to find a pass. Masks use source visible brightness,
not translated values or correction residuals.

For each mask, the original training subset is intersected with retained pixels.
The retained mask also restricts the modeled application/validation domain.
Field polygon exclusions, their original 2 m buffer and original 20 m spatial
uncertainty groups remain unchanged. Both SCS+C and BRDF are refitted. The
combined BRDF is fitted after applying its newly fitted SCS+C model, matching
the original processing order. Raw-BRDF-only fits are reported separately.

The experiment uses the exact saved November 5 stable QR numerical sources,
RossThick/LiDenseR configuration (`b_r=10`, `h_b=2`, scene solar), NDVI-bin settings,
reference solar 45 degrees/nadir, reflectance eligibility limits and QA criteria.
The original serialized reference design [1, -0.04586202988221, -1] is reproduced
by those settings; no reference vector or acceptance threshold is overridden.
The cached camera-kernel design and solar/terrain ancillary arrays are reused.

The old temporary aligned DEM file is absent. It is not needed to refit the
existing design: the original full spatial domain is reconstructed from the
persistent prepared-raster footprint and cached camera support. Its population
matches the saved baseline exactly; the stronger verification is reproduction
of all original fit parameters, eligibility counts and per-band statuses.
Frozen site input contracts include source, ancillary and configuration hashes.

## Limits and next processing step

These are **conditional experimental model-support results**. The historical
radiometry hypothesis and original spectral metadata are preserved. Physical
calibration/contributor provenance and compatible physical-unit translation
coefficients remain separate requirements. Passing these fit checks does not
approve OLI/OLI-2 translation, independent field accuracy, generalization or
production upload.

This run writes model JSONs and diagnostics, not newly corrected rasters or
translated products. Complete raster application still needs per-band output
coverage, finite values, gain distributions and calibration/library acceptance
checks. Fitting on a smaller selected population can change the scientific
population and weaken transfer to excluded shade. Original raw/corrected
products and production defaults remain unchanged.

## Files and reproduction

- `experiment_policy.json`: fixed variants/assumptions.
- `<site>/input_contract.json`: frozen data/ancillary/configuration identities.
- `<site>/<variant>/conditioned_scsc_model.json`: native ten-band SCS+C fits.
- `<site>/<variant>/{brdf_only,combined}/*_brdf_model.json`: fitted BRDF and QA.
- `<site>/<variant>/completed.json`: restart identities and output hashes.
- `all_variant_fit_support.csv`: every site/variant/branch, missing-band counts.
- `all_band_reference_checks.csv`: all 240 band fits and reference diagnostics.

From the repository root:

```sh
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_shade_excluded_refit.py --site ruby
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_shade_excluded_refit.py --site gordon
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_shade_excluded_refit.py --site goldhill
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_shade_refit_summary.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_shade_refit.py tests/test_drone_shade_mask_preview.py
```

Seven focused tests pass; Ruff passes. Completed native fits are reused after
source/mask/output hash checks. Inputs are memory mapped and variants run
sequentially per site. The inherited BRDF fitter materializes a native physical
cube and regression arrays, so this remains an explicit memory-intensive research
fit, not a change to the package's ordinary bulk workflow.

The sibling `shade-excluded-refit/` directory is an **aborted baseline harness**:
the initial direct call used generic default kernel settings rather than the
original drone settings. Its coefficients reproduced but reference QA did not.
No shade conclusion comes from it. Version 2 explicitly supplies the original
configuration and passes full baseline reproduction without a reference override.
