import SpectralBridge.Core

namespace SpectralBridge
open scoped BigOperators
open Set
abbrev Euclid (n : ℕ) := EuclideanSpace ℝ (Fin n)
def simplexE (n : ℕ) : Set (Euclid n) := {x | (∀ i, 0 ≤ x i) ∧ ∑ i, x i = 1}
 theorem simplexE_closed (n) : IsClosed (simplexE n) := by
  have h : simplexE n = (⋂ i, {x : Euclid n | 0 ≤ x i}) ∩ {x | ∑ i, x i = 1} := by
    ext x; simp [simplexE]
  rw [h]
  exact (isClosed_iInter fun i => isClosed_le continuous_const (PiLp.continuous_apply _ _ i)).inter
    (isClosed_eq (continuous_finset_sum _ fun i _ => PiLp.continuous_apply _ _ i) continuous_const)
 theorem simplexE_convex (n) : Convex ℝ (simplexE n) := by
  intro x hx y hy a b ha hb hab
  constructor
  · intro i; change 0 ≤ a * x i + b * y i
    exact add_nonneg (mul_nonneg ha (hx.1 i)) (mul_nonneg hb (hy.1 i))
  · change (∑ i, (a * x i + b * y i)) = 1
    simp [Finset.sum_add_distrib, ← Finset.mul_sum, hx.2, hy.2, hab]
 theorem simplexE_nonempty {n} [NeZero n] : (simplexE n).Nonempty := by
  refine ⟨EuclideanSpace.single 0 1, ?_⟩
  constructor
  · intro i; simp [EuclideanSpace.single_apply]; positivity
  · simp [EuclideanSpace.single_apply]

section Projection
variable {H : Type*} [NormedAddCommGroup H] [InnerProductSpace ℝ H]
variable {K : Set H}
-- A variational certificate, not an assumption that the Python sorting routine is verified.
def IsProjection (K : Set H) (x p : H) : Prop :=
  p ∈ K ∧ ∀ z ∈ K, inner ℝ (x-p) (z-p) ≤ 0
 theorem projection_exists (hne : K.Nonempty) (hcomplete : IsComplete K) (hconv : Convex ℝ K) (x : H) :
    ∃ p, IsProjection K x p := by
  obtain ⟨p, hp, hmin⟩ := exists_norm_eq_iInf_of_complete_convex hne hcomplete hconv x
  exact ⟨p, hp, (norm_eq_iInf_iff_real_inner_le_zero hconv hp).mp hmin⟩
 theorem projection_error {x p z : H} (hp : IsProjection K x p) (hz : z ∈ K) : ‖p-z‖ ≤ ‖x-z‖ := by
  have hv := hp.2 z hz
  have hn := norm_nonneg (x-p)
  have id : x-z = (x-p) - (z-p) := by abel
  have he := norm_sub_sq_real (x-p) (z-p)
  rw [← id] at he
  have hs : ‖p-z‖ = ‖z-p‖ := norm_sub_rev _ _
  nlinarith [norm_nonneg (p-z), norm_nonneg (x-z), sq_nonneg ‖x-p‖]
 theorem projection_unique {x p q : H} (hp : IsProjection K x p) (hq : IsProjection K x q) : p=q := by
  have h1 := hp.2 q hq.1
  have h2 := hq.2 p hp.1
  have h : inner ℝ (p-q) (p-q) ≤ 0 := by
    have hid : x-q = (x-p) + (p-q) := by abel
    have hid2 : q-p = -(p-q) := by abel
    rw [hid, inner_add_left] at h2
    rw [hid2, inner_neg_right] at h1
    linarith
  have hz : ‖p-q‖ = 0 := by rw [real_inner_self_eq_norm_sq] at h; nlinarith [norm_nonneg (p-q)]
  exact sub_eq_zero.mp (norm_eq_zero.mp hz)
 theorem projection_self {x : H} (hx : x ∈ K) : IsProjection K x x := by
  exact ⟨hx, by intro z hz; simp⟩
 theorem projection_fixes {x p : H} (hp : IsProjection K x p) (hx : x ∈ K) : p=x :=
  projection_unique hp (projection_self hx)
end Projection

-- Certificate for the threshold form used by the Python sorting projection.
 theorem threshold_projection {n} (x p : Euclid n) (theta : ℝ)
    (hp : p ∈ simplexE n) (hform : ∀ i, p i = max 0 (x i-theta)) :
    IsProjection (simplexE n) x p := by
  refine ⟨hp, ?_⟩
  intro z hz
  simp only [PiLp.inner_apply, RCLike.inner_apply', conj_trivial, PiLp.sub_apply]
  calc (∑ i, (x i-p i)*(z i-p i)) ≤ ∑ i, theta*(z i-p i) := by
        apply Finset.sum_le_sum
        intro i _
        by_cases h : 0 ≤ x i-theta
        · have he : p i = x i-theta := (hform i).trans (max_eq_right h)
          rw [he]; ring_nf; exact le_rfl
        · have he : p i = 0 := (hform i).trans (max_eq_left (le_of_not_ge h))
          rw [he]; simp only [sub_zero]
          exact mul_le_mul_of_nonneg_right (by linarith) (hz.1 i)
       _ = 0 := by rw [← Finset.mul_sum, Finset.sum_sub_distrib, hz.2, hp.2]; ring

noncomputable def simplexProjection {n} [NeZero n] (x : Euclid n) : Euclid n :=
  Classical.choose (projection_exists simplexE_nonempty (simplexE_closed n).isComplete (simplexE_convex n) x)
 theorem simplexProjection_spec {n} [NeZero n] (x : Euclid n) :
    IsProjection (simplexE n) x (simplexProjection x) := Classical.choose_spec
      (projection_exists simplexE_nonempty (simplexE_closed n).isComplete (simplexE_convex n) x)
 theorem projection_mem {n} [NeZero n] (x : Euclid n) : simplexProjection x ∈ simplexE n := (simplexProjection_spec x).1
 theorem projection_nonneg {n} [NeZero n] (x : Euclid n) (i) : 0 ≤ simplexProjection x i := (projection_mem x).1 i
 theorem projection_sum {n} [NeZero n] (x : Euclid n) : ∑ i, simplexProjection x i = 1 := (projection_mem x).2
 theorem projection_fixed {n} [NeZero n] (x : Euclid n) (hx : x ∈ simplexE n) : simplexProjection x = x :=
  projection_fixes (simplexProjection_spec x) hx
 theorem projection_idempotent {n} [NeZero n] (x : Euclid n) : simplexProjection (simplexProjection x) = simplexProjection x :=
  projection_fixed _ (projection_mem x)
 theorem simplex_projection_error {n} [NeZero n] (x f : Euclid n) (hf : f ∈ simplexE n) :
    ‖simplexProjection x-f‖ ≤ ‖x-f‖ := projection_error (simplexProjection_spec x) hf
end SpectralBridge
