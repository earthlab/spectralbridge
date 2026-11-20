# Full drone/AOP scale chain checked for translation

19 November 2026. This audit checks the user's recalled encoding and the desired
common 1000 scale against actual source arrays, model records and output headers.
It does not edit source rasters, refit models or approve physical calibration.

## Findings

**The current drone pre-BRDF radiometric decode is numerically correct for its
recorded encoding. No missing/double scale factor was found in these runs.**
However, the present stored rasters are not all on a common 1000 scale.

| Stage | Actual convention | Decode to reflectance fraction |
|---|---|---|
| Original calibrated drone integer export |32768 approximately 100%;65535 approximately 200% | DN/32768 |
| Historical fixed-range drone preparation | S=DN*10000/65535;10000 approximately 200% | S*65535/(10000*32768) |
| Conservative refitted corrected drone ENVI | Same storage representation as its prepared input | Same multiplier 0.0001999969482421875 |
| Actual AOP training products |10000=100% | Stored/10000 |
| Derived translation registry | Fractional source and target | Slope unchanged; original intercept/10000 |
| Desired common 1000 output |1000=100%;2000 approximately 200% | Stored/1000 |

The 32768 convention maps 65535 to 1.99996948, approximately 200%; the audit retains
that established exact divisor rather than silently replacing it by 65535/2.
The same words “0–10000” previously described different physical scales. Reading
fixed-range drone S as S/10000 would yield 0.50000763 times its intended fraction,
an approximately 50% underestimate. Raw sensor-photo DN and the already calibrated
orthomosaic encoding are different; this audit does not reapply sensor calibration.

Example: original drone DN 8192 corresponds to fraction 0.25. Its historical
fixed-range derivative is 1250.01907378; the correct multiplier recovers 0.25.
A properly labelled fraction-times 1000 representation stores 250.

## Verified full data chain

For all 3 sites and all 30 bands, the recorded preparation operation was reconstructed
from each original UInt 16 raster: alpha-masked source values, bilinear resampling
to the existing 10 cm grid, then the fixed 10000/65535 encoding. Every finite prepared
pixel equals the reconstructed value exactly. Every native fitting-cache value
also equals the actual prepared TIFF exactly, including NoData locations.
No band-minimum subtraction, min/max stretch or clipping was introduced here.

All saved conservative SCS+C and combined-BRDF radiometry records have multiplier
65535/(10000*32768) and zero offset, matching the corrected ENVI headers. Their
`reflectance scale factor` is the reciprocal, approximately 5000.0763, not 1000
or 10000. Both corrections decode to fractional units for calculations and
re-encode to the original storage representation on output. The existing 1920
independent corrected-value algebra samples verify that no extra scale factor
was introduced in the stored correction result.

The AOP coefficient units are separately proven by 72 recovered archived headers
(all explicitly 10000), not inferred from coefficient magnitudes. Every derived
fractional mapping was checked against its original count-scale equation.

## Correct translation equations

Using the existing historical drone stored value S, original AOP count-scale
intercept a, and fitted slope b:

```text
drone_fraction = S * 65535/(10000*32768)
landsat_like_fraction = b*drone_fraction + a/10000
landsat_like_stored_1000 = 1000*landsat_like_fraction
```

If both input and output are explicitly encoded as 1000 times physical reflectance,
the same mapping is `L1000 = b*M1000 + a/10`. Slopes stay unchanged. Thus the
original count-scale intercept must not be added directly to either fractional
or 1000-scale input. The physical-unit registry is intended to be used after each
input is decoded using its own actual radiometry, then output can be encoded
once to 1000 with an explicit 0.001 physical multiplier. No raw/corrected raster
has been silently rewritten to 1000 in this audit.

## Evidence and reproduction

- `all_30_band_source_preparation_checks.csv`: exact reconstruction/cache checks.
- `drone_scale_chain.csv`: all 3 actual model/header scale chains and source hashes.
- `drone_scale_examples.csv`: representative DN/fixed-range/fraction/1000 values.
- `translation_intercepts_by_storage_scale.csv`: all 18 intercepts at original,
  fractional and common 1000 scales; dimensionless slopes unchanged.
- `scale_chain_verification.json`: results and output/code hashes.

From the repository root:

```sh
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/audit_translation_scale_chain.py
```

Reconstruction reduces one original/prepared band at a time and does not create
another full native pixel cache. The prior full-output independent verification
is `../conservative-refitted-products/verification.json`. Source/calibration
status and empirical accuracy are retained separately: verifying this numeric
unit chain does not by itself promote experimental correction products to
approved spectral-library inputs. The coefficient-unit provenance gap has now
been resolved by the separate AOP header audit.
