# Camera-position calibration translation preflight — 19 November 2026

**Subsequent unit-audit update (19 November 2026):** all72 archived AOP training headers confirm a10000 storage divisor. A separate fractional-reflectance registry now resolves the coefficient-unit issue. See `aop-translation-audit/README.md` and `scale-chain-audit/README.md`. Historical refusal records below remain unchanged; experimental input status is a separate remaining gate.

The requested inputs are the orthomosaic correction products using camera
positions, after the November 5 stability investigation (`stable_qr_v1`). They
are not the November 13 baseline, and do not use reconstruction from all
original photographs.

## Actual outcome

No translated raster was generated or uploaded. The existing translation entry
point was executed against the selected Gordon and Goldhill combined ENVI
products. Both fail the approved-library check: their headers retain
`scientific validation status = EXPERIMENTAL` and
`radiometry status = HYPOTHETICAL_UNVERIFIED`. Ruby's combined branch was rejected
by the BRDF model and is not a usable corrected source. Partial fragments must
not substitute for it.

Separately, the packaged site-balanced translation coefficient registry does not
record `physical_reflectance_v1` training units. Correcting an input header alone
would not resolve that independent translation guard. The bulk candidate and
manifest evidence in `archive/research/bulk-calibration/` does not establish a
verified physical-unit conversion for those fitted coefficients.

The November 13 baseline has newer encoding/wavelength metadata for Ruby and
Goldhill, but deferred BRDF/topographic correction. It does not supersede the
selected camera-position correction arrays. No source header, scale, coefficient,
BRDF acceptance criterion or output filename was changed to bypass a guard.

## Reproduce

From the repository root, with its existing Python environment:

```sh
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python \
  provenance/drone-calibration-translation/2026-11-19/check_selected_run.py
```

Read `selected_run_translation_preflight.json` for exact source paths, band
mapping, expected filenames and runtime refusal messages. The authoritative
correction evidence is `DRONE_CORRECTION_STABILITY_REPORT.md` and
`provenance/drone-correction-stability/2026-11-05/final_checks.json`.

To finish the requested upload, first obtain a usable accepted camera-position
correction with explicit current radiometry/spectral metadata and a reviewed
translation registry in compatible physical units. Ruby needs a supported BRDF
result or an explicitly different requested processing branch. Upload only the
resulting verified products; retain the historical calibration runs separately.
