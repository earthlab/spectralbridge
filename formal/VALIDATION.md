# Verification record — 2026-10-16

- Lean 4.24.0 / mathlib v4.24.0, resolved dependency revisions in `lake-manifest.json`.
- `lake build` passed for the complete root import; all 106 project theorem declarations appear in the axiom audit. Only `propext`, `Classical.choice`, and `Quot.sound` occur. No custom axioms, proof holes or unsafe proof declarations are admitted.
- `check.py` passed build, axiom, exact rational execution, source/configuration/test fingerprint and historical preservation checks. `checks/proof_build.json` hashes every theorem module; `checks/axioms.log` identifies all theorem dependencies.
- Nine exact rational examples executed in Lean. Thirteen Python conformance/audit tests passed in 13.80 seconds. Tests call actual convolution, brightness, affine drone writer, footprint aggregation, generator, FCLS, MESMA, ridge/preprocessing and projection paths. Four tests also expose current axis/epsilon/median-clipping/chunk behavior. Tolerances are explicit in the tests.
- Existing focused regression suite: 21 passed (`tests/test_mixtures.py`, `tests/test_researcher_information.py`). No full repository suite was rerun because production code did not change.
- All 940 unique files owned by P129, P130 and P131 manifests remain unchanged. All audited implementation/configuration/test snapshot hashes match. No scientific fits or source spectral scans were performed.
- Scoped Ruff, local formal-document links, AI-transparency freshness and Git whitespace checks passed.

Machine outputs are retained under `checks/`. `packet_manifest.json` seals this formal layer (excluding itself, ignored toolchain/dependency/build caches). Proof status must be reconsidered after any mapped implementation changes. This is mathematical specification plus finite implementation conformance, not full Python/IEEE or physical end-to-end verification.
