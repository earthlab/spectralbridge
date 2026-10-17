# New analyses integration report

17 October 2026 · P135 · local checkout, not a release or website deployment

SpectralBridge now has twelve composable generic analysis entry points in
**src/spectralbridge/library_analysis.py**. They reuse existing audited numerical
kernels and expose strict identity, support, ordering and interpretation contracts.
The website tells the current researcher-category story and provides runnable API
examples. No historical study was refitted.

## New package functions

All functions are explicitly importable from spectralbridge.library_analysis;
existing top-level orchestration APIs retain their behavior. Install the analytics
extra. Each docstring records inputs, sampling unit, outputs, assumptions and what
its result does not establish. Numerical API support does not imply ecological
validation.

| Function | Purpose | Existing implementation reused | Tests | Docs/example |
|---|---|---|---|---|
| spectral_separability | Identity-mean pairwise difference, synchronized blocked permutations, max/pair correction, gap-aware regions | pft_method_audit.method_statistics; plant_pft_statistics.holm | identity aggregation, sign, masks/missingness, three-pair family, ordered coordinates | Separability page; offline lesson |
| evaluate_identifiability | Strict nested identity/domain recognition with auditable memberships, recall, confusion and scores | Existing group guards and sklearn training-only pipeline pattern | all inner/outer identities disjoint; global domain purge; scaling unaffected by target outliers; class order/determinism | Identifiability page; offline lesson |
| evaluate_feature_budget | Complementary selection vs matched fixed random paths; optional full/PCA | researcher_information.orthogonal_feature_path | nested paths, wavelength reversal, known signal, invalid budgets | Identifiability page; lesson |
| compare_representations | Paired dimensions, recognition/recall, reference differences and transfer penalties | Shared strict recognition evaluation | identical split membership, dimensions, misalignment rejection | Sensor information retention page; lesson |
| generate_mixtures | Configurable pair/triple algebraic mixtures with category/parent ID/role tracking | Generalizes fixed-grid historical generator without changing it | exact reconstruction, deterministic grids, role/order, invalid simplex/budget | Abundance page; lesson |
| constrained_unmixing | Ordered nonnegative sum-one FCLS, residual and reconstruction | mixtures.fcls | known-parent truth, ordering, independent optimizer protection in existing tests | Abundance page; lesson |
| fit_mesma | Explicit restricted candidate search, selected components and all candidate solutions/errors | mixtures.model_indices and fcls | nonunique candidates, restrictions, ordering, invalid indices, default enumeration | Abundance page; lesson |
| candidate_ambiguity | Near-best candidate set and class ranges at additive RMSE tolerance | Existing restricted-ambiguity interpretation, generalized to caller-supplied candidates | intentionally nonunique exact fits, tolerance monotonicity, error validation | Mathematics/abundance pages; lesson |
| fit_ridge_fractions | Group-tuned multi-output ridge with saved scale/coefficients/intercept; raw/projected predictions | Existing StandardScaler/centered Ridge benchmark pattern | saved-parameter replay, group disjointness, known recovery, raw negatives, projected validity, tuning rejection without groups | Abundance page; lesson |
| project_simplex | Vector/matrix Euclidean projection with offset stabilization | researcher_information.project_simplex sorting kernel | known examples, idempotence, independent SLSQP, feasible-truth distance, huge finite offsets | Mathematics page; lesson |
| fraction_diagnostics | Known-fraction RMSE/bias/calibration, absence and low-positive detection, positive-only error, cluster intervals | Extends existing fraction/detection metrics to arbitrary class order | hand-computed errors/rates, empty denominators, deterministic whole-cluster bootstrap | Abundance page; lesson |
| evaluate_library_size | Training-only random/balanced/farthest identity-library capacity experiments | Shared strict grouped folds/classifier | exact retained counts, held-ID exclusion, deterministic scores, oversize rejection | API reference and abundance page; lesson |

Tests: tests/test_library_analysis.py (17 numerical contracts),
tests/test_library_analysis_docs.py (4 integration/example contracts), plus the
existing mixture, learning, researcher-information/validation, method-audit and
scientific-doc integration modules. The primary source location for every new
public entry point is src/spectralbridge/library_analysis.py; no existing solver
was replaced. Explicit candidate MESMA is intentionally a bounded small-library
inspection route, not a fast raster mapping implementation.

## Examples

examples/spectral_library_methods.py and its runnable notebook use the same
invented dataset. They connect difference, recognition, feature controls, paired
representations, disjoint parent-bundle mixtures, oracle FCLS, MESMA, ridge,
ambiguity, diagnostics and retained library size. Notebook cells execute in order
in an automated test. All five new website Python snippets execute offline.

## Website changes

Added four pages within the existing Spectral Library section:

- Scientific synthesis — From spectra to ecological inference.
- Separability — whole-spectrum and wavelength evidence, generic API.
- Identifiability — unseen identity/site/year, class failures and random controls.
- What the mathematics guarantees — preservation, loss, inference and assumption ladder.

Expanded existing sensor-transfer and MESMA-readiness pages without breaking
their URLs. The latter is labelled Abundance and ambiguity in navigation. Existing
Biological variation remains available, preserving its links. Added a concise
homepage synthesis section, a library-overview link, README discovery paragraph
and twelve callable contracts in the existing scientific API reference.

Eleven existing validated figure assets were reused byte-for-byte, including
category coverage/spectra, whole-spectrum and wavelength effects, feature budgets,
held-site confusion/temporal failures, abundance controls, calibration, detection,
ambiguity, information loss and assumption ladder. Every newly embedded figure
has four plain-language interpretation clauses. Sources and SHA-256 values are in
docs/spectral-library/integration-figure-sources.json. No AI imagery or new
scientific figure fitting was used.

## Scientific results now exposed

Only the five recorded cover_category groups are primary. Background/dead remains
a comparator rather than a biological PFT. Verified from compact canonical tables:

- Separability: all ten pairs in forty supported acquisition-matched contrasts;
  largest adjusted whole-spectrum p=0.004. Exchangeability and domain limits remain explicit.
- Recognition: full NEON 85.2% new polygons / 73.8% held sites; Woody shrub
  held-site recall 46.3%. Static annotations do not certify annual biological truth.
- Feature information: held-site 20-coordinate BA 70.1% selected / 65.0% random;
  modest-budget gains, small-budget exceptions and narrowing large-budget gap visible.
- Sensor retention: synthetic OLI 66.8% / 57.7%; same-source products do not
  establish independent Landsat calibration.
- Abundance: Ridge120 NEON RMSE 0.216 / 0.269; MESMA15 0.359 / 0.362.
  Matched Ridge15 0.365 / 0.387 removes the original NEON advantage. Global-year
  ridge 0.311 fails the prior 0.309 on average. No intrinsic method ranking follows.
- Ambiguity: residual quality and expected fraction prediction are distinct from
  unique composition; evaluated near-fit candidates are not exhaustive uncertainty.
- Formal guarantees: fixed linear/appropriate affine mixture preservation can
  coexist with information loss. Ideal FCLS/ridge/projection proofs retain their
  hypotheses; finite conformance is separate. Field abundance remains unestablished.

Exact recomputed values and evidence hashes are in
[the validation snapshot](docs/spectral-library/integration-validation.json).
The source validation script preserves all 1,053 previously owned files across
scientific, manuscript, proof and illustrated proof-report packets. The 940
preceding scientific files are a subset. No old manifest was refreshed or resealed.

## Verification

- 87 targeted numerical/integration/regression tests passed; one existing
  matplotlib colormap deprecation warning, with no failures/skips.
- Strict MkDocs build passed. Internal documentation links passed.
- Five website Python examples and all notebook cells executed successfully.
- Nine affected desktop routes and six science routes at mobile width rendered
  in Chromium. No broken article images or horizontal page overflow. Screenshots
  were inspected; the source Markdown and callable reference remain readable.
- Eleven copied figures and seven canonical numerical source tables hash-checked;
  scientific headline values independently recomputed.
- Scoped Ruff, prompt-transparency consistency and git whitespace checks passed.

Useful commands from repository root:

    OPENBLAS_NUM_THREADS=1 MPLCONFIGDIR=/tmp/spectralbridge-mpl .venv/bin/python -m pytest -ra tests/test_library_analysis.py tests/test_library_analysis_docs.py tests/test_mixtures.py tests/test_spectral_learning.py tests/test_researcher_information.py tests/test_researcher_validation.py tests/test_pft_method_audit.py tests/test_scientific_docs_integration.py
    .venv/bin/python scripts/validate_library_analysis_integration.py --examples
    .venv/bin/python examples/spectral_library_methods.py
    .venv/bin/python -m mkdocs build --strict --site-dir /tmp/spectralbridge-docs
    python3 scripts/check_docs_links.py

## Left unchanged

NEON/drone/bulk pipelines, file naming and restart contracts, all existing solver
implementations and experimental workflows, correction/scaling/response and
brightness coefficients, raw library/Parquet data, historical results/reports and
provenance organization, Lean proofs, manuscript content, release/version/citation
identities, publication infrastructure and the website theme/layout are unchanged.
No commit, release, website deployment or historical regeneration was performed.
The required prompt log and generated AI transparency artifacts were updated.

## Remaining opportunities

- P133: separately fix audited production axis/window/import issues after tracing
  historical source impact; this task does not assert the library was affected.
- Add independent field fractions, verified purity/units and crossed site/year
  labels before making ecological abundance or cross-platform calibration claims.
- Extend library capacity controls to explicit unmixing callbacks or carefully
  defined medoids if justified; currently three clear strategies and a fixed
  classifier avoid a vague configurable experiment engine.
- Add larger-library bounded candidate-search acceleration without hiding evaluated
  alternatives. Current full candidate retention is deliberately budgeted.
- Add external calibration/spatial buffer designs when appropriate observations
  exist; current APIs expose supplied groups/domains rather than inventing them.

The core implementation/classification decisions are recorded in
NEW_ANALYSES_IMPLEMENTATION_PLAN.md. There are no remaining blockers for this
focused integration; independent scientific validation remains a separate need.
