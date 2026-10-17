# Focused integration plan — P135, 17 October 2026

| Capability | Classification | Decision |
|---|---|---|
| Binary blocked whole-spectrum statistics | EXISTING FUNCTION | Reuse pft_method_audit.method_statistics; generic pairwise wrapper, identity aggregation, masks, region summaries and family correction needed |
| Grouped classifier tuning, orthogonal selection | EXISTING FUNCTION | Reuse spectral_learning and researcher_information kernels; generic strict outer/inner design and feature controls needed, never outer_folds' study-specific sites |
| FCLS and finite MESMA active-face solver | EXISTING FUNCTION | Reuse mixtures.fcls/model_indices; expose ordering, explicit candidates and candidate-level solutions |
| Simplex projection | EXISTING FUNCTION | Wrap existing matrix sorting kernel with vector/one-component validation |
| Pair/triple truth generator | NEW FUNCTION NEEDED | Generalize fixed fraction grids and preserve IDs, roles and category order |
| Identifiability, feature budgets, paired representations | NEW FUNCTION NEEDED | Shared strict group splits and training-only pipelines; optional PCA, matched random paths |
| Ridge fraction model, ambiguity, diagnostics, library sizes | NEW FUNCTION NEEDED | Composable structured outputs; retained preprocessing, candidate scope, clustered uncertainty |
| Five-category/site-specific runs, manuscript figures, historical audit fixtures | ANALYSIS-ONLY / DO NOT PACKAGE | Preserve provenance and use validated compact artifacts only for website |

Public numerical entry points will live together in spectralbridge.library_analysis, using the analytics extra. Existing API and production modules remain intact. Reject nonfinite input except explicit separability missing-column policy; never silently impute. Recognition metrics weight identities equally; model fitting is row-based and documented. Held-domain folds purge all target identities. Tuning fails clearly when insufficient grouped support exists rather than silently using target data. Library-size experiments use outer training rows only. New small synthetic tests and one offline teaching script/notebook cover the complete chain. Existing figures are reused with source hashes; scientific numbers are verified from canonical tables. No historical fitting, architecture/release changes or P133 repair.
