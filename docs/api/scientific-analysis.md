# Scientific analysis API and maturity

Stable top-level orchestration remains documented in the [Python API](index.md).
Use direct module imports below for explicit numerical/analysis contracts. A
module import does not automatically make every helper a stable public API.
The reusable numerical surface below is available by explicit module import; no operational abundance-mapping claim is added.

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

## Reusable library-analysis methods

The focused generic numerical surface is **`spectralbridge.library_analysis`**.
Its twelve named exports are supported callable contracts for finite in-memory
arrays; their scientific interpretations remain conditional. Existing experimental
study workflows and top-level pipeline APIs retain their previous status. Install
`earthlab-spectralbridge[analytics]`; these additions currently describe the checkout,
not a claim that a containing release has been published.

| Function | Input and sampling unit | Structured output / scientific limit |
|---|---|---|
| `spectral_separability` | Spectra, ordered wavelengths, labels; identity means within justified exchangeability blocks | Pair/coordinate/region tables; synchronized permutation/max and pair-family correction. Difference does not imply recognition |
| `evaluate_identifiability` | Spectra, labels, identities; optional held domains | Identity-weighted metrics, recall/confusion, scores, memberships, hyperparameters, pipelines. Strict grouped inner tuning; no inverse uniqueness claim |
| `evaluate_feature_budget` | Same plus wavelengths and explicit budgets | Selected/random/full/PCA curves and outer-fold coordinates. Selection inside inner training; not optimal sensor bands |
| `compare_representations` | Same-row paired representations | Dimensions, class recall, recognition/transfer penalties and reference differences. Caller guarantees alignment; synthetic data are not independent validation |
| `generate_mixtures` | Parent spectra/IDs/categories, pair/triple fraction grids | Algebraic spectra/truth, parent IDs/roles and weights. Shared-parent rows are dependent |
| `constrained_unmixing` | Common-support targets and ordered ≤12 endmembers | Nonnegative sum-one FCLS fractions, IDs, residual/reconstruction. Uses admitted numerical faces, not a certified unique biological inverse |
| `fit_mesma` | Candidate library/categories, maximum components or explicit index tuples | Selected references, component/category fractions, every evaluated candidate error/solution and ambiguity. Explicit budget and numerical tolerances |
| `candidate_ambiguity` | One target's candidate fractions/errors/tolerance | Best/near set, class ranges, maximum-range score and alternative count. Evaluated set only, not exhaustive uncertainty |
| `fit_ridge_fractions` | Training spectra and known simplex targets; independent parent-connected groups for multi-alpha tuning | Model with saved scale/coefficients/intercept, tuning memberships; `predict()` returns both raw and projected fractions. Fitted coefficient uniqueness is not inverse uniqueness |
| `project_simplex` | Finite fraction vector or matrix | Euclidean nonnegative sum-one projection; deterministic, including one component. Geometry does not add information |
| `fraction_diagnostics` | Known truth, finite raw/projected predictions, optional independent groups | RMSE/bias/class errors, calibration, false detections, low-fraction misses, positive-only error; optional whole-group bootstrap intervals |
| `evaluate_library_size` | Spectra/identities, sizes, random/balanced/farthest selection | Fold metrics, coverage distances, selected IDs. Training histories averaged; fixed C=1 classifier controls model rule, not every prior confound |

All recognition scale/selection/PCA/tuning fits exclude outer targets. Within a
fold, metrics give every identity total weight one; fitting uses supplied rows.
Held-domain splits globally purge target identities. Tuning requires sufficient
independent groups; unsupported splits raise instead of silently leaking or
changing the design. A single declared regularization value skips tuning.

The separability energy kernel uses quadratic unit-distance storage; its explicit
`maximum_units=5000` default prevents an accidental unbounded run. Raise that
budget deliberately for an appropriately sized in-memory identity analysis.

Nonfinite inputs are rejected, except separability's explicit mask/incomplete-column
policy. Spectral ordering stays caller-controlled; separability requires increasing
coordinates. Category order is deterministic (sorted by default, explicit where
available). Never infer sensor response coefficients from rounded wavelength names.
The implementation preserves existing production coefficients, scaling and masks.

`fit_mesma` performs FCLS for each explicit candidate, including faces. This
inspectable small-library route can be expensive: declare `maximum_models` and
keep the arrays/budgets bounded. It does not replace the historical study solver
or silently rerun its large benchmark. `constrained_unmixing` uses the same existing
rank/interior/update tolerances documented in the formal audit; ideal-real proofs
are separate from numerical checks.

[Run the offline lesson](https://github.com/earthlab/spectralbridge/blob/main/examples/spectral_library_methods.py)
or its [notebook](https://github.com/earthlab/spectralbridge/blob/main/examples/spectral_library_methods.ipynb).
[Scientific synthesis](../spectral-library/scientific-synthesis.md) explains the
current results separately from how to run these methods on another library.

::: spectralbridge.library_analysis.spectral_separability
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.evaluate_identifiability
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.evaluate_feature_budget
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.compare_representations
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.generate_mixtures
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.constrained_unmixing
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.fit_mesma
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.candidate_ambiguity
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.fit_ridge_fractions
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.project_simplex
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.fraction_diagnostics
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
::: spectralbridge.library_analysis.evaluate_library_size
    options:
      show_root_heading: true
      show_root_full_path: false
      heading_level: 3
