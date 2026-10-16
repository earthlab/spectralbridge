# SpectralBridge mathematical verification

This directory checks what the pipeline's equations imply—and what they cannot imply. It does not rewrite the Python pipeline, certify observations or turn a synthetic benchmark into field validation. The actual implementation was mapped before proof construction in [TRACEABILITY.md](TRACEABILITY.md).

The key result is a distinction: **a fixed linear or affine sensor translation can preserve ideal mixture weights while destroying the ability to recover them uniquely.** A proved counterexample shows two identifiable hyperspectral components becoming indistinguishable after a band reduction. Another shows different category compositions reconstructing the same spectrum exactly. A fitted ridge coefficient matrix can be unique even when the physical inverse is not.

## What the files mean

- [CLAIMS.md](CLAIMS.md): scientist-facing interpretation and empirical boundary.
- [PROOF_STATUS.md](PROOF_STATUS.md): exact theorem/test/evidence matrix; no theorem is certified solely by appearing in a planning table.
- [ASSUMPTIONS.md](ASSUMPTIONS.md): mathematical, implementation, physical, biological and empirical assumptions.
- [IMPLEMENTATION_AUDIT.md](IMPLEMENTATION_AUDIT.md): discrepancies and reproducible counterexamples, including band-axis inference and overlapping extraction windows.
- [TRANSLATION_INVARIANCE.md](TRANSLATION_INVARIANCE.md): which actual transformations preserve ideal weights and under what conditions.
- `SpectralBridge/Core.lean`: real finite spectra, five recorded categories, simplex, linear/affine operators, weighted response, guarded correction, mean/median/clipping distinctions and synthetic truth recipes.
- `Projection.lean`: **Euclidean** simplex and projection theorem; threshold-form certificate.
- `Inference.lean`: convex hull, identifiability, rank loss, ideal FCLS, tolerance search, restricted ambiguity and conditional recovery.
- `Ridge.lean`: centered ridge with positive penalty, invertibility, unique coefficient minimizer and intercept/standardized prediction definitions.
- `Counterexamples.lean`: ambiguity, information loss and incompatible error objectives.
- `Pipeline.lean`: explicit functional composition with conditional—not asserted—mixture-preservation and ideal-solver hypotheses.
- `Bridge.lean`: executable rational examples and exact-real identities tied to deterministic Python conformance tests.
- `AxiomAudit.lean`: prints dependencies for every project theorem; no custom axioms or proof holes are permitted.

## Reproduce

Pinned Lean **4.24.0** and matching mathlib release **v4.24.0** (resolved commit in `lake-manifest.json`). This is a reproducibility pin, not a claim to use the latest release. Install elan as described by the [Lean community project guide](https://leanprover-community.github.io/install/project.html). `lake update` downloads dependencies and the mathlib cache; generated dependencies/toolchains stay ignored. Do not commit `.lake/` or `.elan/`.

```bash
cd formal
# Optional isolated toolchain location used in this working copy:
export ELAN_HOME="$PWD/.elan"
lake update
lake build
cd ..
.venv/bin/python formal/check.py
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -m pytest -q formal/tests/test_conformance.py
```

`check.py` builds the complete root import, audits theorem axioms, executes Lean's rational bridge, hashes its output, and verifies the prior analysis/manuscript packets unchanged. `checks/` retains build, axiom, bridge, conformance and preservation results. A changed bridge must be executed again before its Python checks accept the stored exact outputs. A proof build alone does not imply Python conformance tests passed.

The Python environment needs the repository scientific/analytics/test dependencies; tests create only temporary toy rasters/tables. Nine bridge cases cover convolution, multiplication, affine drone translation through its file writer, actual Landsat-footprint mean, synthetic mixtures, FCLS oracle, MESMA ambiguity, centered ridge prediction and simplex projection. Tolerances are explicit per test (float32 1e-6/1e-5 where appropriate, float64 1e-10/1e-12 or tighter). Additional tests expose audit discrepancies. They deliberately assert current mismatches and must be revised when a separately reviewed production fix resolves the finding. These examples are numerical conformance, not a universal proof of IEEE execution.

## Scope and limitations

The ordinary vector type models exact real values; it does not contain NaNs or physical provenance. Validity is separate from physical evidence. Projection uses `EuclideanSpace`, because the default norm on function vectors is not the intended Euclidean norm. FCLS's coordinate-squared objective agrees with Euclidean least squares; dividing by band count does not change the minimizer for positive band count. MESMA's implementation chooses among finite admitted faces, uses rank/interior/tie thresholds, and retains a restricted near-composition diagnostic. Its selection theorem is correspondingly tolerance-aware.

Inline Gaussian convolution is a fixed weighted sum with a `1e-12` denominator stabilizer, not exactly a normalized mean. The optional legacy fallback and installed HyTools path are not claimed numerically equivalent. Native drone processing deliberately uses wavelength selection/affine coefficients, not a fictitious convolution. Scene fits, NDVI bins, clipping, support masks and hierarchical medians prevent a universal linear-pipeline theorem. Physical model adequacy, coefficient transfer, reference purity and biological label meaning remain assumptions, not Lean axioms.

The canonical evidence is the unchanged [26-page validation report](../output/pdf/researcher_evidence/Separability_Identifiability_and_Abundance.pdf) and its [scientific synthesis](../provenance/researcher-evidence/2026-10-16/v1/FINAL_SCIENTIFIC_SYNTHESIS.md). Ridge120's conditional synthetic advantage is lost under the matched15-parent control; global-year ridge fails the prior. No theorem here ranks ridge above MESMA or establishes field fractions. Independent contemporaneous field fractional-cover validation remains outstanding.

This layer is outside the installed Python package and production execution path. It changes no scientific outputs, coefficient files or algorithms. Audit fixes should be separate reviewed work with a provenance-based decision about any affected historical results.
