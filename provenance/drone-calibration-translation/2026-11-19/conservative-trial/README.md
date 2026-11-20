# Conservative shade exclusion: actual translation-QA trial

19 November 2026. The user selected the conservative image-based candidate:
exclude source-visible brightness below 10% of its scene positive-brightness
95th percentile. This fixed choice predates the results below.

## Result

The mask **does not clear the existing translation QA block**.

| Site | Masked corrected input | Existing OLI / OLI-2 translation result |
|---|---|---|
| Gordon | Created and verified | Both refused: experimental correction is not eligible for an approved spectral library |
| Goldhill | Created and verified | Both refused: experimental correction is not eligible for an approved spectral library |
| Ruby | Not created | Selected combined BRDF branch has no accepted corrected product |

Gordon and Goldhill have separate masked ENVI copies in
`archive/local/drone-calibration-translation/2026-11-19/conservative-trial/`.
The same pixel is excluded from all ten bands. Every retained stored value is
exactly equal to the original corrected input, including existing missing-data
positions. Full source hashes are unchanged. Scientific/radiometry/BRDF statuses
were preserved; neither the originals nor the coefficient registry was edited.
No translated raster or upload was produced.

The test applies exclusions to existing corrections; **it does not refit the
BRDF or topographic model**. A trial with shade excluded from model fitting
would be a different experiment, requiring its own correction-support checks.
Masking the output cannot establish calibration provenance, change the original
model support, or repair an absent accepted Ruby combined product. The packaged
coefficient training-unit blocker documented in the parent directory also remains.

## Effect on existing correction gains

The table below uses corrected/original stored values at the same native band
and pixel, restricted to finite values with positive source. The common storage
scale cancels in this ratio. Maxima are exact over all eligible pixels; the CSV
also provides deterministic sampled p99 diagnostics, explicitly not exact p99s.
No acceptance thresholds were selected from these results.

| Site / native band | Maximum before | Maximum retained after |
|---|---:|---:|
| Gordon 650 nm | 17.1718x | 16.7149x |
| Gordon 668 nm | 20.7159x | 20.7159x |
| Goldhill 650 nm | 21.5450x | 21.5450x |
| Goldhill 668 nm | 22.6120x | 22.4754x |

Shade exclusion modestly reduces parts of the tail but does not remove the
largest corrections. The candidate is a dark-pixel screen, not verified shade.
Historical spectral metadata (including the source's old 862 nm label) are
retained for traceability, not silently revised by this masking experiment.

## Reproduce

From the repository root:

```sh
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_conservative_shade_translation_trial.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_shade_mask_preview.py
```

The script validates the chosen mask hash against the reviewed mask inventory,
checks exact raster alignment, writes in 256-line chunks, verifies every retained
value and excluded pixel, and calls the existing translation entry point for
OLI and OLI-2. Masked copies are reused only when source/header/mask/coefficient
identities and output hashes match. See `translation_trial.json` for runtime
errors and provenance, and `correction_gain_before_after.csv` for all ten bands.
Four focused tests and Ruff pass. No production correction or acceptance code
was changed.
