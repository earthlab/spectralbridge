# Lighter shade-mask sensitivity

19 November 2026. User-directed test of reducing the conservative mask while
retaining the same correction-model QA criteria. These are exploratory repeated
fits on the same dataset, not independent validation or a calibrated shade rule.

## Result

**No useful common-mask reduction was found among the tested cutoffs.** Ruby is
the limiting site. Every tested cutoff below 10% of source-visible brightness
p95 fails its combined 668 nm reference-support check. The original 10% cutoff
passes only narrowly. This is the lowest tested passing cutoff, not a proven
exact minimum or robust optimum.

| Ruby brightness cutoff | All valid source pixels excluded | Combined valid bands | 668 nm reference lower margin |
|---|---:|---:|---:|
| None | 0.00% | 8/10 | -0.0100403 |
| 5% | 8.01% | 9/10 | -0.0035548 |
| 7.5% | 14.31% | 9/10 | -0.0013077 |
| 9% | 17.01% | 9/10 | -0.0004653 |
| 9.5% | 17.82% | 9/10 | -0.0002163 |
| 9.75% | 18.21% | 9/10 | -0.0001025 |
| 9.9% | 18.44% | 9/10 | -0.0000227 |
| Prior conservative 10% | 18.60% | 10/10 | +0.0000322 |

Use the CSV for exact calculated values. The QA lower margin is the reference
prediction minus roundoff and 1.96 spatial-cluster standard errors under the
original conditional radiometry hypothesis. The 9.9% variant restores 2,741
training pixels relative to 10% and still fails. Mask exclusion percentages
refer to source pixels; cutoff percentages refer to brightness and must not be
confused with percent area removed.

Gordon and Goldhill already pass all ten combined model fits with **no shade
exclusion** in the numerically reproduced baseline experiment. Site-specific
lighter masking is therefore possible for those model checks. A uniform cutoff
that also passes Ruby has not been reduced meaningfully in this test. Dark-pixel
exclusion and strong correction gains remain separate concerns; this experiment
does not establish that every unmasked pixel is physically reliable.

## Design and integrity

The six new cutoffs (5, 7.5, 9, 9.5, 9.75, 9.9%) were fixed before running them.
All six Ruby outcomes are retained. The planned next step was to check the least
tested passing lighter Ruby cutoff at Gordon and Goldhill; none passed, so no
such additional cross-site run was needed. No threshold was silently adjusted
or selected only from passing results. Near-boundary interpolation is not
independent evidence of robustness, and fit responses need not be monotonic.

New masks use the identical pre-correction 475/560/668 nm brightness definition,
original scene p95 normalization, all-native-band NoData support and source
hashes from the prior preview. Fractional cutoffs have distinct raster paths
(e.g. `9p5pct`) to prevent checkpoint collisions. Full raster grids are checked
against the original cube before fitting.

Each variant refits both native SCS+C and raw/combined BRDF, using the original
camera designs, reference geometry, kernel configuration, eligibility limits,
field-polygon exclusions and 20 m uncertainty groups. Masked pixels are removed
from fitting and the modeled application domain. The same verified refit runner
and original frozen numerical sources are used. Original baseline/source data,
model criteria and prior results remain unchanged.

The predecessor `shade-excluded-refit-v2/` contains baseline reproduction and the
0/10/20/30% sensitivity. This stage contains six native refits, twelve BRDF models
and 120 band fits. No new corrected raster, translation, or datastore upload is
created. Physical calibration and compatible coefficient units remain separate
requirements for approved translation.

## Reproduce

From the repository root using the existing environment:

```sh
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_lighter_shade_sensitivity.py --site ruby
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python examples/drone_lighter_shade_sensitivity.py --summarize
MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/pytest -q tests/test_drone_shade_refit.py tests/test_drone_shade_mask_preview.py
```

`experiment_policy.json` freezes the design; `ruby_mask_inventory.json` records
mask hashes and full-resolution exclusion counts. `<site>/<variant>/` contains
fit models and verified restart checkpoints. `ruby_lighter_mask_results.csv`
contains all tested outcomes plus the prior baseline/conservative comparisons.
`result_manifest.json` records output/code hashes and the absence of an
independently validated or exact minimum threshold. Eight focused tests and
Ruff pass. Existing baseline/source/model files were not overwritten.
