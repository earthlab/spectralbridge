# Audit-stage implementation plan and A–E classification

Status: implementation and new empirical fitting stopped at the source-scale gate
in the attached request, section 15. This is a plan, not completed functionality.
Audit baseline: main, commit `38f646a` (`mesma reports`); checkout initially clean.
No version bump, release, deployment, historical refit or proof change is planned.

| Class | Finding | Action after the gate is resolved |
| --- | --- | --- |
| A — already implemented | `library_analysis` exposes 12 composable methods: differences, grouped recognition, feature budgets, paired representations, mixtures, constrained unmixing, small MESMA, candidate ambiguity, ridge fractions, simplex projection, fraction diagnostics and library-size experiments | Reuse rather than rebuild. Preserve all existing defaults and public entry points. |
| A — already implemented | `researcher_information.orthogonal_feature_path`, `TrainingTransform`, disjoint bundles and existing spectral-learning grouped folds; researcher-evidence selected/random/PCA recognition and same-candidate controls | Reuse selection logic, class order and fixed parent-role records; do not repeat the model contest. |
| B — reusable promotion | Reference-library coverage/discrimination, identity/domain tracking, training-only matched random controls, wrong-category neighbors and cross-category numerical reconstruction | Add one coherent `library_analysis.evaluate_reference_library` interface with structured coverage, discrimination, reconstruction and identifiability sections; generic labels, no study constants. Reuse existing distances, solvers and diagnostics. |
| B — reusable promotion | `exhaustive-v1/stream_mesma.py` finite-library streaming active-face search | Add explicit `fit_mesma_streaming` interface and cheap model-count preflight. Keep eager `fit_mesma` unchanged. Preserve deterministic enumeration and numerical rules; add resource guards, checkpoint integrity and optional compact category-set winners. |
| C — analysis only | Restricted string-array unpickling, source Parquet/NPY alignment, specific 603 selected indices, acquisition-date repair, fixed site/year cells and 360-target experiment | Keep in historical provenance; never encode study categories, local paths, counts, results or splits as package constants. |
| C — analysis only | LP certificates and specific selected-reference examples; report builders, figure selection and descriptive priors | Keep source-specific execution and interpretation in new provenance; only promote general numerical primitives if needed by the coherent audit interface. |
| D — scientific documentation | Exhaustive 603-member result separates spectral objective from composition, extends synthesis evidence ladder | Integrate validated existing numbers with links, preserving conditional/internal scope. Add information-budget page only when new results pass gates; no fabricated curves. |
| E — new information | Absolute units/scaling records, independently measured contemporaneous fractions, matched spatial support, broader site/year sampling, reference purity and label history | Obtain authoritative metadata first; field observations remain essential even if synthetic tests improve. |

## Sequence after source-scale resolution

1. Record authoritative units, multipliers, offsets, generating backend, processing
   stage and immutable source identity. Verify against source and paired compact
   hashes; do not infer physical reflectance from value ranges or divide by 10,000
   merely because an OLI array matched that numerical factor.
2. Promote the two bounded generic interfaces with synthetic tests first. Validate
   matrix support/wavelength ordering, labels/class ordering, unique observation
   keys versus repeated parent identities, consistent labels per parent, target
   identity exclusion, insufficient support, deterministic controls and resource
   budgets. Label fixed whole-archive selections as exposed, not selection-blind.
3. Use the existing read-only `mesma_readiness.load_compact_inputs` contract with
   explicit hashes and `include_historical_labels=False`. **Do not call historical
   `common.load()`**: it writes its old input/environment/observation records and
   would violate the sealed-artifact rule. Avoid all historical stage entry points
   that regenerate owned outputs.
4. Freeze exact previous proper/tuning/target parent memberships and mixture
   recipes, then build every representation from the same source-parent matrix.
   Verify identical truth and lineage hashes before fitting each representation.
5. Use the full stated budget grid and multiple deterministic nested random paths;
   select coordinates/PCA and all fit preprocessing on proper training only.
   Tune only on the original tuning parents; evaluate new-parent and held-site
   targets separately. Save unsupported domains instead of changing memberships.
6. Fix the estimators and library capacity across budgets. Use a prespecified
   training-only finite dictionary for MESMA, ridge with unchanged parent capacity,
   a no-spectrum training mean and the known-parent oracle. No new ML families or
   test-selected winning seed/budget. Candidate construction and channel scaling
   must remain explicit; record reconstruction geometry for each representation.
7. Evaluate recognition, fraction error, reconstruction and restricted ambiguity
   separately. Add full feasible near-fit envelopes only if explicitly implemented
   and numerically tested; one best solution per category set cannot supply them.
8. Save compact predictions, class/calibration/domain metrics, bundle uncertainty,
   feature paths, identities and figure data in a new version. Pilot costs before
   broad execution; finite-model and target/model guards prevent accidental huge
   tests/examples. Produce 3–5 major figures, each with explanatory captions.
9. Verify scientific controls and historical hashes before integrating the new
   website narrative. Run targeted/full feasible tests, Ruff, strict MkDocs, links,
   existing integration validation, package build and rendered-page checks. Do not
   alter formal proofs; conformance changes require a separately stated audit.
10. Answer the ten requested scientific questions from those actual curves. Do not
    force a minimum-band threshold, infer causal limitation from one comparison,
    or create another algorithm search if independent observations are the limit.

## Streaming-backend design details to settle and test

- Estimate distinct-category combinations with Python integer arithmetic before
  creating iterators. Declare maximum models, target/model evaluations, library
  rows, target count, chunk memory and category-set retention budget explicitly.
- Batch both targets and candidate tuples where needed; avoid unguarded library
  Gram allocations as library size grows. The analysis runner's Gram matrix is
  quadratic in endmember count and its target batch is all targets: it should not
  be promoted unchanged as universally bounded-memory for arbitrary input sizes.
- Fingerprint exact input values/labels/support, ordering, settings, kernel version
  and checkpoints. Atomic configuration/checkpoint writes, output hashes and
  contiguous verified checkpoint chains must reject corruption or gaps, not
  silently reuse unchecked `.npz` files. Preserve progress and clean restart state.
- Explicitly record rank absolute/relative thresholds, positive interior threshold,
  MSE improvement tolerance, declared components and one-reference-per-category
  restriction. Compare small-case winners against the existing numerical kernel;
  separately describe any wrapper tie-order differences rather than hide them.
- One feature is a requested experimental budget. Existing `mixtures._matrix`
  rejects fewer than two channels. The new design must explicitly test/support
  one-dimensional finite-library geometry or report it unsupported; do not
  silently remove this budget or pad a fictitious second band.
- Optional category-set winners and ambiguity summaries must distinguish active
  interiors, represented boundary faces and all feasible near-optimal fractions.
  Exhaustive finite dictionary search is not exhaustive physical uncertainty.

## Required evidence to clear the present gate

A source-linked record establishing the corrected NEON and synthetic OLI units,
any scale factor and offset, when they were applied, and whether they are common
across source flights/products. If the authoritative answer is that physical units
cannot be recovered, the user must explicitly revise the section-15 condition
before an experiment in declared stored numerical units can proceed. Such an
experiment could address conditional algebraic recovery, not physical radiometry.
