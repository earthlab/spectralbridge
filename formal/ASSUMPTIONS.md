# Assumption ledger

No global physical/biological axioms are added. Theorems quantify over real vectors/operators and put hypotheses in their statements. Lean's ordinary foundational axioms (choice, propositional extensionality, quotient soundness) are not empirical assumptions. PhysicalEvidence deliberately requires a supplied proof of the chosen proposition; its existence is never assumed by a theorem.

| ID | Kind | Required assumption / limitation | Consequence if absent |
|---|---|---|---|
| M1 | Mathematical | Compatible finite dimensions; nonempty simplex requires component count >0 | Empty feasible set has no projection/minimizer |
| M2 | Mathematical | Real finite values on common support; no NaN/nodata encoded as a real spectrum | Masked-array behavior is outside algebraic proofs |
| M3 | Mathematical | Same fixed linear/affine transform on target and all endmembers | No mixture commutation across differing gains/intercepts/support |
| M4 | Mathematical | Sum-to-one for arbitrary affine offsets (or the exact offset-defect condition) | Offset contributes a different amount to a weighted sum |
| M5 | Mathematical | Nonnegative normalized response weights for convex bounds and exact constants | Epsilon inline weights are not exactly normalized; negative interpolation weights lack convex bounds |
| M6 | Mathematical | Positive ridge alpha, nonempty training for intercept means, centered design/targets, unpenalized intercept restored | Stated coefficient uniqueness/closed form need not hold |
| M7 | Mathematical | Identifiability on simplex of transformed generating library | Zero residual does not uniquely determine fractions |
| M8 | Mathematical | Euclidean projection onto a nonempty closed convex simplex | Error guarantee does not apply to clipping-only or different norms |
| I1 | Implementation | Correct file/header scale, wavelength order, band mapping and coefficient orientation | Algebra can be correct on incorrectly interpreted data |
| I2 | Implementation | Frozen geometry, fitted coefficients, NDVI bins, validity mask for linear-stage claim | Full data-dependent correction need not preserve mixtures |
| I3 | Implementation | Floating-point roundoff and declared rank/tie tolerances acceptable | Exact-real theorem is not exact execution certification |
| I4 | Implementation | Candidate faces, class restrictions and search budget match the scientific question | Ideal unrestricted FCLS/MESMA theorem overstates searched domain |
| I5 | Implementation | Proper-only scaler/selection, disjoint identities and correct saved replay | Numerical transfer evidence can be contaminated; Lean does not verify workflow I/O |
| I6 | Implementation | Correct band axis and duplicate-free polygon records | Current axis/chunk findings require restricted claims; see audit |
| P1 | Physical | Stored values represent intended reflectance quantity and comparable units | Spectral amplitudes lack established physical interpretation |
| P2 | Physical | Linear mixing is appropriate at aligned spatial support | Synthetic algebraic fractions need not equal field fractional cover |
| P3 | Physical | Geometry/correction model describes acquisition and scene | Positive correction factor does not establish physical correctness |
| P4 | Physical | Empirical translation coefficients transfer to native drone observations | Same-source synthetic NEON fits cannot validate real sensor calibration |
| B1 | Biological | Recorded polygon/year cover_category represents intended cover | Class recognition cannot establish purity or annual biological change |
| B2 | Biological | References represent generating materials and within-class variability | Different candidate sets may reconstruct spectra with wrong categories |
| B3 | Biological | Algebraic category weights have intended ecological fraction meaning | No field-cover recovery claim follows from the synthetic benchmark |
| E1 | Empirical | Independent cross-site/year support and aligned truth | Sampled-domain recognition cannot be generalized universally |
| E2 | Empirical | Calibration estimated adequately and independent residuals acceptable | Algebra does not supply calibration validity |
| E3 | Empirical | Independent contemporaneous field fractions | Field abundance remains NOT ESTABLISHED |

The most limiting biological assumptions are P1/P2/P4/B1/B2/B3/E3. A positive-definite ridge training system guarantees a unique fitted coefficient matrix, not an identifiable inverse physical mixture.
