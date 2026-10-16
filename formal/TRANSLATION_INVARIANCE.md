# When translations preserve ideal abundance weights

“Preserves” means applying the same frozen map to the target and each generating endmember produces the same weighted sum. It does not mean a solver can uniquely recover those weights. Injectivity on the generating simplex is a separate condition.

| Transformation | Linear? | Affine? | Mixture preserving? | Fraction preserving in ideal model? | Requires sum-to-one? | Empirical calibration assumption? | Lean theorem |
|---|---|---|---|---|---|---|---|
| NEON storage multiplier | Yes, fixed metadata | Yes | Yes | Algebraically; recovery needs identifiability | No | Scale metadata must be correct | linear_mixture; diagonal_nonneg |
| Inline NEON→OLI or synthetic MicaSense | Yes, fixed SRFs/support, epsilon included | Yes | Yes | Algebraically, not necessarily recoverable | No | Sensor response adequacy | linear_mixture; epsilon_constant |
| Legacy coefficient-matrix resampling | Yes, fixed coefficients | Yes | Yes | Algebraically | No | Backend response approximation | linear_mixture |
| Fixed percentage Landsat-like darkening | Yes | Yes | Yes | Algebraically | No | Percent coefficients/order/axis | linear_mixture |
| Drone corrected MicaSense→Landsat-like | Generally no (nonzero intercept) | Yes, fixed wavelength selection/slopes/offsets | Yes | Algebraically; no physical calibration theorem | Yes unless offset defect vanishes | Same-source synthetic fit does not establish real calibration | affine_mixture; affine_mixture_iff |
| Actual Landsat DN conversion | No (offset−.2) | Yes on valid DN domain | Yes within fixed valid domain | Algebraic DN-domain statement only | Yes | Product metadata/QA | affine_mixture |
| Frozen SCS+C / BRDF factors | Yes, fixed per-location parameters | Yes | Yes for same location/factors/support | Algebraically only | No | Geometry/model correctness | diagonal_nonneg; linear_mixture |
| Scene fitting / NDVI-bin selection | Not generally | Not generally | Not guaranteed | No general claim | Insufficient | Yes | order_matters, conditional pipeline only |
| Scene brightness with clipping | Not generally | Only frozen preclip stage | Not generally | No general claim | Insufficient | Yes | clipping_not_mixture |
| Arithmetic polygon/footprint mean | Yes on fixed common support | Yes | Yes | If common representation and ideal model hold | Affine upstream map needs normalized averaging weights | Registration/membership/support | mean_affine; weighted_bounds |
| Hierarchical median library | Not generally | Not generally | Not under arbitrary cross-band maps | No universal interchange theorem | Insufficient | Membership/reference meaning | median_not_additive |
| Simplex projection / fitted ridge+projection | Not generally | Raw fixed prediction affine; projection piecewise affine | Not generally | No inverse-identifiability theorem | Insufficient | Training distribution/targets | projection_error; perfect_prediction_not_unique_inversion |

An affine map satisfies mixture commutation exactly when `offset = (sum weights) • offset`. Thus sum-to-one is sufficient, not logically necessary for zero offsets. Identifiability before translation is necessary but not sufficient for identifiability afterward. The two-band collapse counterexample is proved, while a specific library's rank/conditioning remains numerical evidence.
