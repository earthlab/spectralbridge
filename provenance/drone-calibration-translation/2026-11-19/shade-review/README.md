# Image-based shade-mask candidates

These previews support a human choice before drone translation. Orange denotes
pixels proposed for exclusion. It is a brightness proxy, not a validated shade
classification: dark vegetation and soil can also be sunlit.

## Compare the masks

Open `three_site_shade_mask_comparison.png` for the full comparison or the
separate `gordon_shade_mask_candidates.png`, `goldhill_shade_mask_candidates.png`
and `ruby_shade_mask_candidates.png` images to inspect individual sites.

| Site | Conservative | Moderate | Stronger |
|---|---:|---:|---:|
| Gordon | 15.8% | 29.8% | 44.6% |
| Goldhill | 7.5% | 15.3% | 22.6% |
| Ruby | 18.6% | 32.3% | 48.9% |

Numbers are fractions of valid source pixels proposed for exclusion. They are
not estimates of true shadow cover. Stronger candidates remove broad forest
areas, so inspect retained canopy carefully rather than choosing by fraction.
No candidate has been selected, applied to a translated product or uploaded.

## Definition and provenance

Brightness is the arithmetic mean of the native 475, 560 and 668 nm bands divided
by its scene-specific positive-value 95th percentile. The reference percentile
uses a deterministic systematic spatial sample of up to approximately 200,000
native pixels; it is not computed from display-stretched RGB. Conservative,
moderate and stronger cutoffs are respectively 0.10, 0.20 and 0.30 of that
reference brightness. These are explicit exploratory choices, not calibrated
physical shadow thresholds or fixed exclusion percentiles.

Masks come from the pre-correction `__experimental_candidate.img` inputs used by
the camera-position `stable_qr_v1` experiment. Their geometry matches the
correction run. Correction gains therefore cannot brighten a dark source pixel
out of the screen. No original-photo reconstruction is performed. Wavelength
matching is explicit and independent of native band positions. Display RGB uses
separate 2nd–98th percentile stretches for viewing only.

Full-resolution GeoTIFFs are saved in
`archive/local/drone-calibration-translation/2026-11-19/shade-mask-candidates/`.
They retain the exact source CRS, transform and dimensions, with codes:

- `0`: candidate retained pixel
- `1`: candidate excluded pixel
- `255`: source NoData / any missing native spectral band

A future selected mask must exclude pixels identically across all translated
bands. Existing missing pixels must remain missing. NoData is not sunlight.
Mask choice does not resolve the correction/physical-unit blockers documented
in the parent directory, and no existing scientific gate has been changed.

`candidate_mask_policy.json`, `source_provenance.json` and
`candidate_exclusion_counts.csv` record definitions, source/mask hashes, native
band selection, normalization values and exact full-resolution counts.

## Reproduce

Run from the repository root with its existing environment:

```sh
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_shade_mask_preview.py
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_shade_mask_preview.py
```

The script reads native pixels in 256-line chunks, hashes rasters in bounded
buffers and leaves the original inputs unchanged. Re-running regenerates this
same preview stage. A different threshold policy requires a separate version;
the current frozen policy is checked before generating outputs.
