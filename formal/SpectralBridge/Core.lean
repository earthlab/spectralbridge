import Mathlib

/-! Exact-real specification. No floating-point execution or physical interpretation is an axiom. -/
namespace SpectralBridge
open scoped BigOperators
open Finset

inductive Sensor where
  | neon | oli | tm | etm | micaSense | translatedLandsat | actualLandsat
  deriving DecidableEq, Repr
abbrev Wavelength := ℝ
abbrev Band (n : ℕ) := Fin n
abbrev Spectrum (n : ℕ) := Fin n → ℝ
abbrev ReflectanceSpectrum (n : ℕ) := Spectrum n
abbrev PolygonID := String
inductive Category where
  | deciduous | evergreen | herbaceous | nonvegetatedDead | woodyShrub
  deriving DecidableEq, Repr, Fintype
abbrev ResponseFunction (n : ℕ) := Spectrum n
abbrev TranslationMatrix (m n : ℕ) := Matrix (Fin m) (Fin n) ℝ
abbrev Endmember (n : ℕ) := Spectrum n
abbrev CandidateLibrary (k n : ℕ) := Fin k → Endmember n
abbrev FractionVector (k : ℕ) := {f : Spectrum k // f ∈ stdSimplex ℝ (Fin k)}

def validSpectrum {n} (_x : Spectrum n) : Prop := True
-- Real vectors are finite mathematical values. Physical validation is separately supplied evidence.
structure PhysicalEvidence {n} (x : Spectrum n) where
  intendedUnits : Prop
  unitsEvidence : intendedUnits
  intendedSupport : Prop
  supportEvidence : intendedSupport

noncomputable def mixture {k n} (E : CandidateLibrary k n) (f : Spectrum k) : Spectrum n :=
  ∑ i, f i • E i
abbrev Mixture (n : ℕ) := Spectrum n

 theorem fraction_nonneg {k} (f : FractionVector k) (i) : 0 ≤ f.val i := f.property.1 i
 theorem fraction_sum {k} (f : FractionVector k) : ∑ i, f.val i = 1 := f.property.2
 theorem simplex_convex (k : ℕ) : Convex ℝ (stdSimplex ℝ (Fin k)) := convex_stdSimplex ℝ _
 theorem simplex_compact (k : ℕ) : IsCompact (stdSimplex ℝ (Fin k)) := isCompact_stdSimplex _
 theorem simplex_nonempty {k} [NeZero k] : (stdSimplex ℝ (Fin k)).Nonempty :=
  ⟨Pi.single 0 1, single_mem_stdSimplex ℝ (0 : Fin k)⟩

noncomputable def diagonal {n} (g : Spectrum n) : Spectrum n →ₗ[ℝ] Spectrum n where
  toFun x := fun i => g i * x i
  map_add' _ _ := by ext; simp [mul_add]
  map_smul' _ _ := by ext; simp [mul_left_comm]

 theorem diagonal_nonneg {n} (g x : Spectrum n) (hg : ∀ i, 0 ≤ g i)
    (hx : ∀ i, 0 ≤ x i) : ∀ i, 0 ≤ diagonal g x i := fun i => mul_nonneg (hg i) (hx i)

 theorem linear_zero {n m} (T : Spectrum n →ₗ[ℝ] Spectrum m) : T 0 = 0 := T.map_zero
 theorem linear_add {n m} (T : Spectrum n →ₗ[ℝ] Spectrum m) (x y) : T (x+y) = T x + T y := T.map_add x y
 theorem linear_smul {n m} (T : Spectrum n →ₗ[ℝ] Spectrum m) (a : ℝ) (x) : T (a • x) = a • T x := T.map_smul a x
 theorem linear_mixture {k n m} (T : Spectrum n →ₗ[ℝ] Spectrum m)
    (E : CandidateLibrary k n) (f : Spectrum k) :
    T (mixture E f) = mixture (fun i => T (E i)) f := by
  simp [mixture, map_sum]

structure AffineTranslation (n m : ℕ) where
  linear : Spectrum n →ₗ[ℝ] Spectrum m
  offset : Spectrum m
noncomputable def affine {n m} (T : AffineTranslation n m) (x : Spectrum n) := T.linear x + T.offset

 theorem affine_mixture_defect {k n m} (T : AffineTranslation n m)
    (E : CandidateLibrary k n) (f : Spectrum k) :
    mixture (fun i => affine T (E i)) f =
      T.linear (mixture E f) + (∑ i, f i) • T.offset := by
  simp [mixture, affine, smul_add, Finset.sum_add_distrib, Finset.sum_smul]
 theorem affine_mixture {k n m} (T : AffineTranslation n m)
    (E : CandidateLibrary k n) (f : Spectrum k) (hf : ∑ i, f i = 1) :
    affine T (mixture E f) = mixture (fun i => affine T (E i)) f := by
  rw [affine_mixture_defect, hf, one_smul]; rfl
 theorem affine_mixture_iff {k n m} (T : AffineTranslation n m)
    (E : CandidateLibrary k n) (f : Spectrum k) :
    affine T (mixture E f) = mixture (fun i => affine T (E i)) f ↔
      T.offset = (∑ i, f i) • T.offset := by
  rw [affine_mixture_defect]; exact add_left_cancel_iff

noncomputable def weighted {n} (w : Spectrum n) : Spectrum n →ₗ[ℝ] ℝ where
  toFun x := ∑ i, w i * x i
  map_add' x y := by simp [mul_add, Finset.sum_add_distrib]
  map_smul' a x := by simp [Finset.mul_sum, mul_left_comm]
 theorem weighted_constant {n} (w : Spectrum n) (c : ℝ) :
    weighted w (fun _ => c) = (∑ i, w i) * c := by simp [weighted, Finset.sum_mul]
 theorem normalized_constant {n} (w : Spectrum n) (h : ∑ i, w i = 1) (c : ℝ) :
    weighted w (fun _ => c) = c := by rw [weighted_constant, h, one_mul]
 theorem weighted_bounds {n} (w x : Spectrum n) (lo hi : ℝ)
    (hw : ∀ i, 0 ≤ w i) (hs : ∑ i, w i = 1)
    (hx : ∀ i, lo ≤ x i ∧ x i ≤ hi) : lo ≤ weighted w x ∧ weighted w x ≤ hi := by
  constructor
  · calc lo = ∑ i, w i * lo := by simp [← Finset.sum_mul, hs]
         _ ≤ weighted w x := Finset.sum_le_sum (fun i _ => mul_le_mul_of_nonneg_left (hx i).1 (hw i))
  · calc weighted w x ≤ ∑ i, w i * hi := by
           change (∑ i, w i * x i) ≤ ∑ i, w i * hi
           exact Finset.sum_le_sum (fun i _ => mul_le_mul_of_nonneg_left (hx i).2 (hw i))
         _ = hi := by simp [← Finset.sum_mul, hs]
noncomputable def epsilonWeight {n} (r : Spectrum n) (eps : ℝ) : Spectrum n := fun i => r i / ((∑ j, r j) + eps)
 theorem epsilon_weight_sum {n} (r : Spectrum n) (eps : ℝ) :
    (∑ i, epsilonWeight r eps i) = (∑ i, r i) / ((∑ i, r i) + eps) := by
  simp [epsilonWeight, ← Finset.sum_div]
 theorem normalized_response_sum {n} (r : Spectrum n) (hs : 0 < ∑ i, r i) :
    ∑ i, epsilonWeight r 0 i = 1 := by rw [epsilon_weight_sum]; simp [ne_of_gt hs]
 theorem normalized_response_nonneg {n} (r : Spectrum n) (hr : ∀ i, 0 ≤ r i) (hs : 0 < ∑ i, r i) :
    ∀ i, 0 ≤ epsilonWeight r 0 i := by
  intro i; exact div_nonneg (hr i) (by simpa using hs.le)
noncomputable def gaussianResponse {n} (waves : Spectrum n) (center width : ℝ) : Spectrum n :=
  fun i => Real.exp (-(1/2:ℝ) * ((waves i-center)/(width/(2*Real.sqrt (2*Real.log 2))))^2)
 theorem gaussian_response_positive {n} (waves : Spectrum n) (center width : ℝ) (i) :
    0 < gaussianResponse waves center width i := Real.exp_pos _
 theorem diagonal_monotone {n} (g x y : Spectrum n) (hg : ∀ i, 0 ≤ g i) (hxy : ∀ i, x i ≤ y i) :
    ∀ i, diagonal g x i ≤ diagonal g y i := fun i => mul_le_mul_of_nonneg_left (hxy i) (hg i)
 theorem epsilon_constant {n} (r : Spectrum n) (eps c : ℝ) :
    weighted (epsilonWeight r eps) (fun _ => c) = ((∑ i, r i) / ((∑ i, r i) + eps)) * c := by
  rw [weighted_constant, epsilon_weight_sum]

-- Frozen geometry/fit parameters only. Nonfinite inputs are excluded from this real-valued model.
noncomputable def guardedRatio (num den threshold : ℝ) := if threshold < den ∧ 0 < num / den then num / den else 1
 theorem guardedRatio_pos (num den threshold : ℝ) : 0 < guardedRatio num den threshold := by
  unfold guardedRatio; split_ifs with h; exact h.2; norm_num
 theorem multipliers_commute {n} (g h x : Spectrum n) : diagonal g (diagonal h x) = diagonal h (diagonal g x) := by
  ext i; simp [diagonal]; ring
 theorem order_matters : (2 : ℝ) * (3 + 1) ≠ 2 * 3 + 1 := by norm_num
noncomputable def clip01 (x : ℝ) := max 0 (min 1 x)
 theorem clipping_not_mixture : clip01 (((-1 : ℝ) + 1) / 2) ≠ (clip01 (-1) + clip01 1) / 2 := by norm_num [clip01]
noncomputable def median3 (a b c : ℝ) := a + b + c - min a (min b c) - max a (max b c)
 theorem median_not_additive :
    median3 (0+0) (0+1) (1+0) ≠ median3 0 0 1 + median3 0 1 0 := by norm_num [median3]
 theorem mean_affine {k n m} [NeZero k] (T : AffineTranslation n m) (E : CandidateLibrary k n) :
    affine T (mixture E (fun _ => (k : ℝ)⁻¹)) = mixture (fun i => affine T (E i)) (fun _ => (k : ℝ)⁻¹) := by
  apply affine_mixture
  simp [Nat.cast_ne_zero.mpr (NeZero.ne k)]

noncomputable def pairFractions (t : ℝ) : Spectrum 2 := ![t, 1-t]
 theorem pair_simplex (t : ℝ) (h0 : 0 ≤ t) (h1 : t ≤ 1) : pairFractions t ∈ stdSimplex ℝ (Fin 2) := by
  constructor
  · intro i; fin_cases i <;> simp [pairFractions] <;> linarith
  · simp [pairFractions, Fin.sum_univ_two]
 theorem triple_simplex :
    (![ (1:ℝ)/3, 1/3, 1/3] ∈ stdSimplex ℝ (Fin 3)) ∧
    (![ (1:ℝ)/10, 2/10, 7/10] ∈ stdSimplex ℝ (Fin 3)) ∧
    (![ (5:ℝ)/100, 45/100, 50/100] ∈ stdSimplex ℝ (Fin 3)) ∧
    (![ (8:ℝ)/10, 1/10, 1/10] ∈ stdSimplex ℝ (Fin 3)) := by
  repeat' constructor
  all_goals first | (intro i; fin_cases i <;> norm_num) | norm_num [Fin.sum_univ_succ, Matrix.cons_val_succ, Matrix.cons_val_zero]
end SpectralBridge
