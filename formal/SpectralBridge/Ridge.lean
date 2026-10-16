import SpectralBridge.Inference

namespace SpectralBridge
open scoped BigOperators Matrix

-- X and Y are CENTERED after the frozen proper-training transform. The intercept is unpenalized.
noncomputable def ridgeGram {r p} (X : Matrix (Fin r) (Fin p) ℝ) (lam : ℝ) := Xᵀ * X + lam • (1 : Matrix (Fin p) (Fin p) ℝ)
 theorem ridge_positive {r p} (X : Matrix (Fin r) (Fin p) ℝ) (lam : ℝ) (hl : 0 < lam) :
    (ridgeGram X lam).PosDef := by
  have hp := (Matrix.PosDef.one : (1 : Matrix (Fin p) (Fin p) ℝ).PosDef).smul hl
  have hs := Matrix.posSemidef_conjTranspose_mul_self X
  simpa [ridgeGram] using Matrix.PosDef.posSemidef_add hs hp
 theorem ridge_invertible {r p} (X : Matrix (Fin r) (Fin p) ℝ) (lam : ℝ) (hl : 0 < lam) :
    IsUnit (ridgeGram X lam) := (ridge_positive X lam hl).isUnit
 theorem ridge_injective {r p} (X : Matrix (Fin r) (Fin p) ℝ) (lam : ℝ) (hl : 0 < lam) :
    Function.Injective ((ridgeGram X lam).mulVec) := Matrix.mulVec_injective_iff_isUnit.mpr (ridge_invertible X lam hl)
noncomputable def ridgeCoefficient {r p} (X : Matrix (Fin r) (Fin p) ℝ) (y : Spectrum r) (lam : ℝ) : Spectrum p :=
  (ridgeGram X lam)⁻¹ *ᵥ (Xᵀ *ᵥ y)
 theorem ridge_unique {r p} (X : Matrix (Fin r) (Fin p) ℝ) (y : Spectrum r) (lam : ℝ) (hl : 0 < lam)
    (b c : Spectrum p) (hb : ridgeGram X lam *ᵥ b = Xᵀ *ᵥ y) (hc : ridgeGram X lam *ᵥ c = Xᵀ *ᵥ y) : b=c :=
  ridge_injective X lam hl (hb.trans hc.symm)
 theorem ridge_normal_equation {r p} (X : Matrix (Fin r) (Fin p) ℝ) (y : Spectrum r) (lam : ℝ) (hl : 0 < lam) :
    ridgeGram X lam *ᵥ ridgeCoefficient X y lam = Xᵀ *ᵥ y := by
  unfold ridgeCoefficient
  rw [Matrix.mulVec_mulVec, Matrix.mul_nonsing_inv _ (((ridgeGram X lam).isUnit_iff_isUnit_det).mp (ridge_invertible X lam hl)), Matrix.one_mulVec]

noncomputable def ridgeObjective {r p} (X : Matrix (Fin r) (Fin p) ℝ) (y : Spectrum r) (lam : ℝ) (b : Spectrum p) : ℝ :=
  dotProduct (y - X *ᵥ b) (y - X *ᵥ b) + lam * dotProduct b b
 theorem ridge_objective_sum {r p} (X : Matrix (Fin r) (Fin p) ℝ) (y : Spectrum r) (lam : ℝ) (b : Spectrum p) :
    ridgeObjective X y lam b = (∑ i, (y i - (X *ᵥ b) i)^2) + lam * ∑ j, (b j)^2 := by
  simp [ridgeObjective, dotProduct, pow_two]
 theorem adjoint_dot {r p} (X : Matrix (Fin r) (Fin p) ℝ) (u : Spectrum p) (v : Spectrum r) :
    dotProduct u (Xᵀ *ᵥ v) = dotProduct (X *ᵥ u) v := by
  rw [Matrix.mulVec_transpose, dotProduct_comm u, ← Matrix.dotProduct_mulVec, dotProduct_comm]
 theorem gram_dot {r p} (X : Matrix (Fin r) (Fin p) ℝ) (lam : ℝ) (u v : Spectrum p) :
    dotProduct u (ridgeGram X lam *ᵥ v) = dotProduct (X *ᵥ u) (X *ᵥ v) + lam * dotProduct u v := by
  simp only [ridgeGram, Matrix.add_mulVec, Matrix.smul_mulVec, Matrix.one_mulVec, dotProduct_add, dotProduct_smul]
  rw [← Matrix.mulVec_mulVec, adjoint_dot]
  rfl
 theorem ridge_gap {r p} (X : Matrix (Fin r) (Fin p) ℝ) (y : Spectrum r) (lam : ℝ)
    (b d : Spectrum p) (hb : ridgeGram X lam *ᵥ b = Xᵀ *ᵥ y) :
    ridgeObjective X y lam (b+d) = ridgeObjective X y lam b +
      dotProduct (X *ᵥ d) (X *ᵥ d) + lam * dotProduct d d := by
  have hh := congrArg (dotProduct d) hb
  rw [gram_dot, adjoint_dot] at hh
  have cross : dotProduct (y-X *ᵥ b) (X *ᵥ d) = lam * dotProduct b d := by
    rw [sub_dotProduct, dotProduct_comm y (X *ᵥ d), dotProduct_comm (X *ᵥ b) (X *ᵥ d), dotProduct_comm b d]
    linarith
  simp only [ridgeObjective, Matrix.mulVec_add, sub_add_eq_sub_sub, sub_dotProduct, dotProduct_sub,
    add_dotProduct, dotProduct_add]
  rw [dotProduct_comm (X *ᵥ d) y, dotProduct_comm (X *ᵥ d) (X *ᵥ b), dotProduct_comm d b] at hh ⊢
  nlinarith only [hh]
 theorem ridge_minimizes {r p} (X : Matrix (Fin r) (Fin p) ℝ) (y : Spectrum r) (lam : ℝ) (hl : 0 < lam)
    (b : Spectrum p) (hb : ridgeGram X lam *ᵥ b = Xᵀ *ᵥ y) (c : Spectrum p) :
    ridgeObjective X y lam b ≤ ridgeObjective X y lam c := by
  have hh := ridge_gap X y lam b (c-b) hb
  have h1 : 0 ≤ dotProduct (X *ᵥ (c-b)) (X *ᵥ (c-b)) := Finset.sum_nonneg (fun j _ => mul_self_nonneg _)
  have h2 : 0 ≤ dotProduct (c-b) (c-b) := Finset.sum_nonneg (fun j _ => mul_self_nonneg _)
  simp only [add_sub_cancel] at hh
  nlinarith
 theorem ridge_minimizer_unique {r p} (X : Matrix (Fin r) (Fin p) ℝ) (y : Spectrum r) (lam : ℝ) (hl : 0 < lam)
    (b c : Spectrum p) (hb : ridgeGram X lam *ᵥ b = Xᵀ *ᵥ y)
    (hc : ridgeObjective X y lam c ≤ ridgeObjective X y lam b) : c=b := by
  have hh := ridge_gap X y lam b (c-b) hb
  simp only [add_sub_cancel] at hh
  have h1 : 0 ≤ dotProduct (X *ᵥ (c-b)) (X *ᵥ (c-b)) := Finset.sum_nonneg (fun j _ => mul_self_nonneg _)
  have h2 : 0 ≤ dotProduct (c-b) (c-b) := Finset.sum_nonneg (fun j _ => mul_self_nonneg _)
  have hz : dotProduct (c-b) (c-b) = 0 := by nlinarith
  exact sub_eq_zero.mp (dotProduct_self_eq_zero.mp hz)
noncomputable def rawPredict {p k} (B : Matrix (Fin k) (Fin p) ℝ) (intercept : Spectrum k) (x : Spectrum p) : Spectrum k :=
  B *ᵥ x + intercept
noncomputable def standardizedPredict {p k} (B : Matrix (Fin k) (Fin p) ℝ) (intercept : Spectrum k)
    (mean scale x : Spectrum p) := rawPredict B intercept (fun j => (x j - mean j) / scale j)
-- Each output column has its own ridge RHS; the same Gram matrix is positive definite.
end SpectralBridge
