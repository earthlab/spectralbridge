# Goldhill red boundary: confirmed BRDF artifact

**Diagnosis completed 2026-10-30.** The stripe comes from the BRDF normalization stage. It is not the repaired source-grid geometry, and topographic correction alone does not produce it.

## Controlled stage isolation

Using the identical working H5, existing production coefficients and unchanged correction functions, the experiment computes full-scene raw, topographic-only, BRDF-only and combined results. BRDF-only reproduces the stripe; topographic-only has no such stripe. The combined replay matches **all 70,832,700 production values and validity masks exactly**. Previews are sampled every fifth pixel; the full-scene calculation/replay is not sampled.

See `stage_isolation.png` / `.pdf`. RGB panels have independent 2–90% display stretches. The correction-factor panels show the discontinuity independently of image contrast.

## The causal chain

1. **Numeric range / unit contract mismatch.** The working TIFF bridge uses scale 1. Source RGB values are generally in the hundreds, while the BRDF fitter defaults to `rho_min=0`, `rho_max=2`. Of 7,068,376 finite pixels in each source band, only **14 red-band pixels (650 nm)** and **13 green-band pixels (560 nm)** enter the fit. The blue display band (475 nm) has only one eligible pixel, so it receives neutral coefficients. The true physical scale is not established by the source metadata; no assumed conversion factor is endorsed here.
2. **The fitted angular model is unidentifiable.** Both recorded view angles are constant zero; source solar angles vary only slightly, and the fitter replaces solar zenith with a scene mean. The exact red and green fitting matrices have **rank 2 for 3 parameters**. The code calls least squares but discards its returned rank. Reconstructing the fits from those exact 14/13 source pixels reproduces the saved production coefficients bit-for-bit.
3. **Unconstrained reference-geometry extrapolation.** The scene is observed near solar zenith 27.765° and relative azimuth 204.7°, but normalization predicts at the default 45° solar zenith / 0° relative azimuth reference. The red model predicts roughly **91,740** there despite being trained only on values between 0 and 2. This prediction is not supported by the available angular information.
4. **The guard creates the visible boundary.** For the red band, the modeled observed-geometry denominator ranges across zero (about −0.758 to +1.594 in the stride-5 trace). Where it is non-positive, the code substitutes a factor of **1**, leaving red unchanged. Where it is small and positive, the reference/observed ratio applies factors from roughly **57,563 up to 11,742,750** on the sampled valid grid. The transition follows the model's zero contour: the diagonal red/cyan boundary. Green's reference prediction is negative, so its guard bypasses correction; blue is already neutral. This unequal treatment produces the color artifact.

The reconstructed BRDF formula reproduces the sampled BRDF-only output exactly, including the neutral-guard pattern for the red boundary. This is a numerical mechanism, not an inference from color appearance alone.

## What should change next

Confirm authoritative source reflectance units/scaling and band definitions. Add explicit input-range/fit-population checks, rank/conditioning and reference-support validation, and reject or clearly block unstable BRDF fits before application. A denominator clamp or arbitrary gain cap alone would hide symptoms without establishing a valid model. Correct scaling alone may not resolve the lack of angular diversity in a constant-view drone mosaic.

The topographic-only diagnostic removes the stripe but is not independently validated radiometry or an automatically approved replacement. Goldhill BRDF-corrected products and dependent bulk fits should remain scientifically unapproved pending repair/review. The verified spatial alignment remains valid. No scientific defaults, scaling, acquisition metadata or production coefficients were changed in this diagnosis.

## Preservation and evidence

All **66 original Goldhill product files** still match the pre-investigation upload-manifest SHA-256 hashes. Existing sources, corrected products and Data Store outputs were preserved. Full ablation intermediates live only under `/private/tmp/goldhill-correction-diagnosis-20261030`; compact diagnostics and reproduction scripts live here.

- `ablation.json`: exact full-scene production replay.
- `fit_population.json`: full source-band eligibility counts, numeric fitting limits and extrema.
- `fit_reconstruction.json`: exact eligible source coordinates, matrix ranks and reproduced saved coefficients.
- `brdf_mechanism.json`: denominator/reference ranges, multiplier ranges and exact sampled output/guard reconstruction.
- `saved_production_brdf_model.json`, `preservation_and_code.json`: observational coefficients, code hashes and unchanged-product checks.
- `ablate.py`, `trace_brdf.py`, `fit_population.py`, `reconstruct_fit.py`, `plot_ablation.py`: reproduction scripts; run from the repository root in the existing environment. The fit-reconstruction/trace scripts preserve the recorded acquisition and model conventions.

Eleven synthetic-control and existing BRDF tests pass; the synthetic fixtures contain no production coefficients or observation constants. They isolate the current guard discontinuity and default fit-range exclusion. They are diagnostic controls, not a production safety repair. Ruff, documentation links, whitespace and regenerated AI transparency are checked separately.
