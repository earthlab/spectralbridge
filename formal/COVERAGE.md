# Request coverage and intentional boundaries

| Requested part | Delivered location / boundary |
|---|---|
| I Core mathematical objects | Core.lean: sensors, wavelength/band, spectra, validity/evidence, matrices/affine maps, polygon/category, endmembers/library/fractions/mixtures; actual five categories |
| II Sensor transformations | Linear zero/add/scalar/mixture and affine offset-defect/convex-mixture theorems |
| III Response convolution | Gaussian exact-real sampling definition and actual discrete weighted/epsilon formulas; constants/bounds/normalization. Header parsing, Gaussian IEEE evaluation and optional HyTools internals are not formally verified |
| IV Cross-sensor translation | Fixed percentage diagonal and mapped affine drone paths; actual DN affine scale; TRANSLATION_INVARIANCE.md separates algebra from calibration |
| V Corrections | Exact guarded finite-real ratio; frozen gains positivity/monotonicity; noncommuting offset example. Full trigonometric kernels, regression/bin fitting and physical appropriateness remain inspected/numerical/empirical |
| VI Polygon aggregation | Actual per-pixel extraction and hierarchical median identified; mean/affine theorem applies to actual footprint mean, not primary median library; median/clipping counterexamples |
| VII Mixture generation | Exact pairs and all four triple recipes simplex; convex hull/reconstruction. Random parent selection and all generator implementation paths are not universally proved |
| VIII Identifiability | Simplex injectivity, augmented-system sufficient condition, rank nonincrease, inability to restore lost identifiability, explicit null/collapse examples |
| IX FCLS | Convexity, compact-domain existence, uniqueness conditional on simplex identifiability, known-parent oracle theorem. Actual active-face rank/interior/tie tolerances remain explicit |
| X MESMA | Distinct-category/max-components face type, rank/interior predicates, normalization feasibility, admitted finite search tolerance bound, ambiguity monotonicity/nonemptiness and explicit equal-residual class systems. No full proof of numerical active-face enumeration/solver |
| XI Ridge | Centered objective matches coordinate squared loss plus penalty; positive Gram/inverse, normal equation, objective gap/unique minimizer; explicit standardized/intercept prediction. Per-output theorem extends columnwise; no proof of sklearn execution |
| XII Projection | Euclidean closed convex simplex, existence/uniqueness/constraints/fixed-point/idempotence/error; threshold-form certificate and exact toy certificate. General sorting/rho algorithm equivalence is numerical evidence only |
| XIII Ridge versus MESMA | Explicit different objectives and counterexamples, no universal estimator-ranking theorem |
| XIV Full composition | Pipeline.lean explicit stage composition and conditional exact recovery; actual nonlinearity/medians prevent asserting hypotheses globally |
| XV Translation invariance | Formal linear/affine theorems and separate transformation table |
| XVI Sensor information loss | Finite-dimensional impossibility, kernel collision, explicit identifiable-before/ambiguous-after mixture |
| XVII Numerical bridge | Bridge.lean executes nine rational examples; exact-real identities/certificates; conformance tests call actual Python functions/file paths; declared tolerances; no IEEE certification claim |
| XVIII Assumptions | ASSUMPTIONS.md separates five kinds, explicit theorem hypotheses, no custom axioms |
| XIX Proof status | PROOF_STATUS.md plus full kernel dependency audit and machine-readable build hashes |
| XX Adversarial audit | IMPLEMENTATION_AUDIT.md; isolated axis/SRF/chunk discrepancy tests; source/evidence hash preservation; queued follow-up fixes |

A missing field measurement is not a missing Lean proof. Physical unit validity, coefficient transfer, reference biological purity and independently measured field fractions require evidence rather than a theorem. Conversely, the universal sorting/active-face/IEEE algorithm proofs are genuine uncompleted implementation-verification work, clearly separated from the proved ideal mathematics. The project does not claim complete end-to-end software verification.
