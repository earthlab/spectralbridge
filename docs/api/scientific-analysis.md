# Scientific analysis API and maturity

Stable top-level orchestration remains documented in the [Python API](index.md).
Use direct module imports below for explicit numerical/analysis contracts. A
module import does not automatically make every helper a stable public API.
No new top-level MESMA, PFT-classification or abundance-mapping export is added.

| Capability | Import / entry point | Maturity and input contract |
|---|---|---|
| Inspect/report library | `spectralbridge.inspect_spectral_library_preflight`, `run_spectral_library_analysis` | Stable public; existing library read in place; compact first, full traces opt-in |
| Empirical atlas | `spectralbridge.plant_spectral_atlas.run_plant_spectral_atlas` | Tested module workflow; Parquet with explicit identity, flight, source, polygon and label fields; native support preserved |
| Harmonize one spectrum | `spectralbridge.plant_spectral_atlas.harmonize_spectrum` | Tested numerical helper; ordered nm grid, finite support, unchanged stored units |
| Whole-spectrum comparison | `spectralbridge.pft_method_audit.method_statistics` | Audited research method; binary groups, eligible exact-history blocks, common support |
| Paired sensor experiment | `spectralbridge.sensor_pft_transfer.run_sensor_pft_transfer` | Research workflow; original library, validated coordinates, explicit permutations/bootstrap budgets |
| Gaussian OLI diagnostic | `spectralbridge.sensor_pft_transfer.project_neon_to_oli` | Numerical diagnostic after medians; not a replacement for canonical raster convolution |
| Actual Landsat comparison | `spectralbridge.landsat_flight_validation.compare_flight_to_real_landsat` | Tested module workflow; verified full raster support/scales/times, optional network extra |
| Endmember selection / FCLS | `spectralbridge.mixtures.select_endmembers`, `fcls`, `fit_models` | Experimental; finite same-unit matrices, small explicit model budgets; no ecological validity guarantee |
| Detection / fold / adequacy guards | `spectralbridge.mixtures.detection_metrics`, `validate_holdout`, `adequacy_status` | Experimental numerical validation; explicit thresholds, global identity purging, low residual never certifies membership |
| MESMA readiness | `spectralbridge.mesma_readiness.run_readiness` | Experimental research validation; original source plus verified same-source compact products |

## Minimal offline use

```python
import numpy as np
from spectralbridge.plant_spectral_atlas import harmonize_spectrum
from spectralbridge.sensor_pft_transfer import project_neon_to_oli
from spectralbridge.landsat_agreement import compute_agreement_metrics

wavelengths = np.arange(385.0, 2511.0, 5.0)
values = np.full(len(wavelengths), 0.2)  # invented teaching spectrum
harmonized = harmonize_spectrum(wavelengths, values, wavelengths)
oli, support = project_neon_to_oli(harmonized[None, :], wavelengths)
metrics = compute_agreement_metrics(oli[0], oli[0])
assert metrics["RMSE"] < 1e-12
```

This flat teaching curve verifies numerical usage, not real sensor performance.
Run `python examples/scientific_workflows_offline.py` for checked IO/preflight,
atlas aggregation, OLI projection and agreement without external data or network.
The [processing guides](../vignettes/full-pipeline.md) require real source data;
synthetic helpers do not emulate actual correction.

## Selected callable contracts

::: spectralbridge.plant_spectral_atlas.harmonize_spectrum
::: spectralbridge.plant_spectral_atlas.run_plant_spectral_atlas
::: spectralbridge.pft_method_audit.method_statistics
::: spectralbridge.sensor_pft_transfer.project_neon_to_oli
::: spectralbridge.landsat_agreement.compute_agreement_metrics
::: spectralbridge.landsat_agreement.aggregate_to_landsat_grid
::: spectralbridge.landsat_flight_validation.FlightValidationInput
::: spectralbridge.landsat_flight_validation.FlightValidationConfig
::: spectralbridge.landsat_flight_validation.compare_flight_to_real_landsat
::: spectralbridge.mixtures.fcls
::: spectralbridge.mixtures.validate_holdout
::: spectralbridge.mixtures.adequacy_status
::: spectralbridge.mixtures.detection_metrics
::: spectralbridge.mesma_readiness.run_readiness

Full research runs remain separately reproducible in examples/provenance. They
require the original data and explicit computational budgets. Testing a solver,
plot or bootstrap implementation does not promote an ecological application to
stable operational status.

## Historical closure diagnostics (experimental)

`spectralbridge.spectral_closure` supplies the tested descriptive two-year
partition, per-observation shape/amplitude sensitivity, explicit partial label
hierarchy and class-wise error rates with whole-identity intervals. It does not
change production normalization, fit causal regional variance components or
certify physical material purity. The source-specific execution and final report
builders are retained in `provenance/scientific-closure/2026-10-15/`.


## Canonical researcher-category research helpers

`spectralbridge.researcher_information` supplies explicit recorded-category
validation, identity weights, single-coordinate discriminants, complementary
orthogonal selection, disconnected derivatives, parent bundles and simplex
projection. These are experimental numerical helpers, not a field-abundance API.
The category-only repository experiment runs with
`python examples/researcher_pft_information.py --stage all`; its METHODS fixes
source paths, support, preprocessing, tuning and scientific interpretation.
`mesma_readiness.load_compact_inputs(..., include_historical_labels=False)`
reads paired products without constructing the retired taxonomic grouping.

## Three-question researcher-category validation

`python examples/researcher_evidence_validation.py --stage all --report-python /path/to/report/python`
reproduces the current separability / identifiability / abundance evidence packet.
Stages can run separately; completed fitting checkpoints verify input/code identities.
See the [spectral-library overview](../spectral-library/index.md#three-distinct-scientific-questions)
for the new matched controls and limits. Earlier researcher-information functions
and tables remain the preserved numerical companion.
