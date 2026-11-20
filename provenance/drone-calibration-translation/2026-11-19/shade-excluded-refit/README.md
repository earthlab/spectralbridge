# Aborted baseline harness — do not use for conclusions

The initial direct BRDF fit call used generic default kernel settings, rather
than the original drone RossThick/LiDenseR settings. Baseline coefficients
reproduced, but reference predictions and some per-band statuses did not. No
shade variants or conclusions from this directory are used.

The complete corrected experiment is in `../shade-excluded-refit-v2/`.
It explicitly passes the original saved kernel, NDVI and eligibility settings,
and reproduces all baseline fit coefficients and per-band statuses before mask
comparisons. No reference-vector override or acceptance change is used.
