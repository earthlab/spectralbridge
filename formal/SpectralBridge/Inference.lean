import SpectralBridge.Projection

namespace SpectralBridge
open scoped BigOperators
open Set Finset

 theorem mixture_convexHull {k n} (E : CandidateLibrary k n) (f : Spectrum k)
    (hf : f ∈ stdSimplex ℝ (Fin k)) : mixture E f ∈ convexHull ℝ (Set.range E) := by
  apply (convex_convexHull ℝ (Set.range E)).sum_mem
  · exact fun i _ => hf.1 i
  · simpa using hf.2
  · intro i _; exact subset_convexHull ℝ _ (Set.mem_range_self i)

noncomputable def mixMap {k n} (E : CandidateLibrary k n) : Spectrum k →ₗ[ℝ] Spectrum n where
  toFun := mixture E
  map_add' f g := by simp [mixture, add_smul, Finset.sum_add_distrib]
  map_smul' a f := by simp [mixture, Finset.smul_sum, smul_smul]

def Identifiable {k n} (E : CandidateLibrary k n) := Set.InjOn (mixture E) (stdSimplex ℝ (Fin k))
 theorem identifiable_of_injective {k n} (E : CandidateLibrary k n) (h : Function.Injective (mixMap E)) : Identifiable E :=
  fun _ _ _ _ heq => h heq
-- An augmented system is sufficient: only zero-sum null directions matter for simplex weights.
 theorem identifiable_of_augmented {k n} (E : CandidateLibrary k n)
    (h : Function.Injective (fun f : Spectrum k => (mixture E f, ∑ i, f i))) : Identifiable E := by
  intro f hf g hg heq
  apply h; exact Prod.ext heq (hf.2.trans hg.2.symm)
 theorem indistinguishable_after_map {k n m} (E : CandidateLibrary k n) (T : Spectrum n →ₗ[ℝ] Spectrum m)
    (f g : Spectrum k) (h : mixture E f = mixture E g) :
    mixture (fun i => T (E i)) f = mixture (fun i => T (E i)) g := by
  rw [← linear_mixture, ← linear_mixture, h]
 theorem transformation_cannot_restore_identifiability {k n m} (E : CandidateLibrary k n)
    (T : Spectrum n →ₗ[ℝ] Spectrum m) (h : Identifiable (fun i => T (E i))) : Identifiable E := by
  intro f hf g hg heq
  exact h hf hg (indistinguishable_after_map E T f g heq)
 theorem rank_cannot_increase {k n m} (E : Spectrum k →ₗ[ℝ] Spectrum n)
    (T : Spectrum n →ₗ[ℝ] Spectrum m) : LinearMap.rank (T.comp E) ≤ LinearMap.rank E :=
  LinearMap.rank_comp_le_right E T
 theorem fewer_bands_not_injective {n m} (T : Spectrum n →ₗ[ℝ] Spectrum m) (h : m < n) :
    ¬ Function.Injective T := by
  intro hinj
  have hh := LinearMap.finrank_le_finrank_of_injective hinj
  simp only [Module.finrank_pi, Fintype.card_fin] at hh
  omega
 theorem kernel_collision {n m} (T : Spectrum n →ₗ[ℝ] Spectrum m) (v : Spectrum n)
    (hv : v ≠ 0) (hker : T v = 0) : v ≠ 0 ∧ T v = T 0 := ⟨hv, by simpa using hker⟩

noncomputable def loss {k n} (E : CandidateLibrary k n) (y : Spectrum n) (f : Spectrum k) : ℝ :=
  ∑ b, (y b - mixture E f b)^2
 theorem loss_nonneg {k n} (E : CandidateLibrary k n) (y) (f) : 0 ≤ loss E y f :=
  Finset.sum_nonneg (fun _ _ => sq_nonneg _)
 theorem loss_zero_iff {k n} (E : CandidateLibrary k n) (y) (f) : loss E y f = 0 ↔ mixture E f = y := by
  rw [loss, Finset.sum_eq_zero_iff_of_nonneg (fun b _ => sq_nonneg _)]
  constructor
  · intro h; ext b; have hb := h b (Finset.mem_univ b); nlinarith [sq_nonneg (y b - mixture E f b)]
  · intro h b _; simp [h]
 theorem loss_continuous {k n} (E : CandidateLibrary k n) (y) : Continuous (loss E y) := by
  unfold loss mixture
  fun_prop

def IsFCLS {k n} (E : CandidateLibrary k n) (y : Spectrum n) (f : Spectrum k) : Prop :=
  f ∈ stdSimplex ℝ (Fin k) ∧ ∀ g ∈ stdSimplex ℝ (Fin k), loss E y f ≤ loss E y g
 theorem fcls_exists {k n} [NeZero k] (E : CandidateLibrary k n) (y : Spectrum n) : ∃ f, IsFCLS E y f := by
  obtain ⟨f, hf, hm⟩ := (simplex_compact k).exists_isMinOn simplex_nonempty (loss_continuous E y).continuousOn
  exact ⟨f, hf, hm⟩
 theorem fcls_convex {k n} (E : CandidateLibrary k n) (y : Spectrum n) :
    ConvexOn ℝ (stdSimplex ℝ (Fin k)) (loss E y) := by
  refine ⟨simplex_convex k, ?_⟩
  intro f hf g hg a b ha hb hab
  have hm := (mixMap E).map_add (a • f) (b • g)
  simp only [map_smul] at hm
  change loss E y (a • f + b • g) ≤ a * loss E y f + b * loss E y g
  unfold loss
  rw [Finset.mul_sum, Finset.mul_sum, ← Finset.sum_add_distrib]
  apply Finset.sum_le_sum
  intro j _
  have hid : mixture E (a • f + b • g) j = a * mixture E f j + b * mixture E g j := congrFun hm j
  rw [hid]
  have he : y j - (a * mixture E f j + b * mixture E g j) =
      a * (y j - mixture E f j) + b * (y j - mixture E g j) := by
    calc y j - (a * mixture E f j + b * mixture E g j) = (a+b)*y j - (a * mixture E f j + b * mixture E g j) := by rw [hab]; ring
         _ = _ := by ring
  rw [he]
  have hh := mul_nonneg (mul_nonneg ha hb) (sq_nonneg ((y j - mixture E f j)-(y j-mixture E g j)))
  have hb' : b = 1-a := by linarith
  have hidpoly : a * (y j-mixture E f j)^2 + b * (y j-mixture E g j)^2 -
      (a*(y j-mixture E f j)+b*(y j-mixture E g j))^2 =
      a*b*((y j-mixture E f j)-(y j-mixture E g j))^2 := by rw [hb']; ring
  linarith only [hh, hidpoly]
 theorem oracle_fcls {k n} (E : CandidateLibrary k n) (f : Spectrum k) (hf : f ∈ stdSimplex ℝ (Fin k)) :
    IsFCLS E (mixture E f) f := by
  refine ⟨hf, fun g hg => ?_⟩
  have hz : loss E (mixture E f) f = 0 := (loss_zero_iff _ _ _).mpr rfl
  rw [hz]; exact loss_nonneg _ _ _
 theorem oracle_unique {k n} (E : CandidateLibrary k n) (f g : Spectrum k)
    (hf : f ∈ stdSimplex ℝ (Fin k)) (hg : g ∈ stdSimplex ℝ (Fin k))
    (hi : Identifiable E) (hz : loss E (mixture E f) g = 0) : g=f :=
  hi hg hf ((loss_zero_iff _ _ _).mp hz)
 theorem fcls_exact_recovery {k n} (E : CandidateLibrary k n) (f g : Spectrum k)
    (hf : f ∈ stdSimplex ℝ (Fin k)) (hi : Identifiable E)
    (hg : IsFCLS E (mixture E f) g) : g=f := by
  apply oracle_unique E f g hf hg.1 hi
  have hm := hg.2 f hf
  have hz : loss E (mixture E f) f = 0 := (loss_zero_iff _ _ _).mpr rfl
  rw [hz] at hm; exact le_antisymm hm (loss_nonneg _ _ _)

 theorem loss_midpoint {k n} (E : CandidateLibrary k n) (y : Spectrum n) (f g : Spectrum k) :
    loss E y ((1/2:ℝ) • f + (1/2:ℝ) • g) =
      (loss E y f + loss E y g)/2 - (∑ j, (mixture E f j - mixture E g j)^2)/4 := by
  have hm := (mixMap E).map_add ((1/2:ℝ) • f) ((1/2:ℝ) • g)
  simp only [map_smul] at hm
  unfold loss
  rw [← Finset.sum_add_distrib, Finset.sum_div, Finset.sum_div, ← Finset.sum_sub_distrib]
  apply Finset.sum_congr rfl
  intro j _
  have hj : mixture E ((1/2:ℝ) • f + (1/2:ℝ) • g) j = (1/2:ℝ)*mixture E f j + (1/2:ℝ)*mixture E g j := congrFun hm j
  rw [hj]; ring
 theorem fcls_unique {k n} (E : CandidateLibrary k n) (y : Spectrum n) (f g : Spectrum k)
    (hi : Identifiable E) (hf : IsFCLS E y f) (hg : IsFCLS E y g) : f=g := by
  have hmid := hf.2 _ ((simplex_convex k) hf.1 hg.1 (by norm_num : (0:ℝ) ≤ 1/2) (by norm_num : (0:ℝ) ≤ 1/2) (by norm_num : (1/2:ℝ)+1/2=1))
  rw [loss_midpoint] at hmid
  have heq := le_antisymm (hf.2 _ hg.1) (hg.2 _ hf.1)
  have hn : 0 ≤ ∑ j, (mixture E f j-mixture E g j)^2 := Finset.sum_nonneg (fun j _ => sq_nonneg _)
  have hz : (∑ j, (mixture E f j-mixture E g j)^2) = 0 := by nlinarith
  have hall := (Finset.sum_eq_zero_iff_of_nonneg (fun j _ => sq_nonneg (mixture E f j-mixture E g j))).mp hz
  apply hi hf.1 hg.1
  ext j
  have hj := hall j (Finset.mem_univ j)
  nlinarith [sq_nonneg (mixture E f j-mixture E g j)]

-- The searched candidates are admitted active-face solutions, not all biological compositions.
structure SearchResult (J : Type*) (cost : J → ℝ) (tau : ℝ) where
  selected : J
  bound : ∀ j, cost selected ≤ cost j + tau
-- Actual default search: nonempty faces, distinct recorded categories, at most maxComponents (default 3).
structure CandidateFace (k : ℕ) (labels : Fin k → Category) (maxComponents : ℕ) where
  indices : Finset (Fin k)
  nonempty : indices.Nonempty
  componentBound : indices.card ≤ maxComponents
  distinctClasses : Set.InjOn labels (indices : Set (Fin k))

def admittedRank (smallest largest : ℝ) : Prop := max ((1:ℝ)/1000000000000) (largest*((1:ℝ)/10000000000)) < smallest

def admittedInterior {k} (f : Spectrum k) : Prop :=
  (∀ i, (1:ℝ)/1000000000 < f i ∧ f i ≤ 1+(1:ℝ)/1000000000)

 theorem normalized_candidate_feasible {k} (v : Spectrum k) (hv : ∀ i, 0 ≤ v i) (hs : 0 < ∑ i, v i) :
    epsilonWeight v 0 ∈ stdSimplex ℝ (Fin k) :=
  ⟨normalized_response_nonneg v hv hs, normalized_response_sum v hs⟩
 theorem selected_feasible {J k} (cost : J → ℝ) (tau : ℝ) (r : SearchResult J cost tau)
    (fractions : J → Spectrum k) (hf : ∀ j, fractions j ∈ stdSimplex ℝ (Fin k)) :
    fractions r.selected ∈ stdSimplex ℝ (Fin k) := hf r.selected
 theorem search_bound {J} (cost : J → ℝ) (tau) (r : SearchResult J cost tau) (j) :
    cost r.selected ≤ cost j + tau := r.bound j
-- If each admitted cost is processed and replaced iff improvement exceeds tau, preserve this bound.
 theorem tolerant_update (old candidate z tau : ℝ) (ht : 0 ≤ tau) (h : old ≤ z + tau) :
    (if candidate < old-tau then candidate else old) ≤ z + tau ∧
    (if candidate < old-tau then candidate else old) ≤ candidate + tau := by
  split_ifs with hc <;> constructor <;> linarith

noncomputable def tolerantChoose {J} (cost : J → ℝ) (tau : ℝ) (old next : J) : J :=
  if cost next < cost old-tau then next else old
 theorem choose_le_old {J} (cost : J → ℝ) (tau : ℝ) (ht : 0 ≤ tau) (old next : J) :
    cost (tolerantChoose cost tau old next) ≤ cost old := by
  unfold tolerantChoose; split_ifs <;> linarith
 theorem choose_le_next {J} (cost : J → ℝ) (tau : ℝ) (ht : 0 ≤ tau) (old next : J) :
    cost (tolerantChoose cost tau old next) ≤ cost next+tau := by
  unfold tolerantChoose; split_ifs <;> linarith
 noncomputable def tolerantSearch {J} (cost : J → ℝ) (tau : ℝ) (start : J) (candidates : List J) : J :=
  candidates.foldl (tolerantChoose cost tau) start
 theorem search_le_start {J} (cost : J → ℝ) (tau : ℝ) (ht : 0 ≤ tau) (cs : List J) (start : J) :
    cost (tolerantSearch cost tau start cs) ≤ cost start := by
  induction cs generalizing start with
  | nil => exact le_rfl
  | cons a cs ih => exact (ih (tolerantChoose cost tau start a)).trans (choose_le_old cost tau ht start a)
 theorem tolerant_search_bound {J} (cost : J → ℝ) (tau : ℝ) (ht : 0 ≤ tau)
    (cs : List J) (start j : J) (hj : j ∈ cs) :
    cost (tolerantSearch cost tau start cs) ≤ cost j+tau := by
  induction cs generalizing start with
  | nil => simp at hj
  | cons a cs ih =>
    rcases List.mem_cons.mp hj with heq | hmem
    · subst j
      exact (search_le_start cost tau ht cs (tolerantChoose cost tau start a)).trans (choose_le_next cost tau ht start a)
    · exact ih (tolerantChoose cost tau start a) hmem

def ambiguity {J k} (frac : J → Spectrum k) (cost : J → ℝ) (rmin eps : ℝ) : Set (Spectrum k) :=
  {f | ∃ j, frac j = f ∧ cost j ≤ rmin+eps}
 theorem ambiguity_mono {J k} (frac : J → Spectrum k) (cost : J → ℝ) (rmin e1 e2 : ℝ) (h : e1 ≤ e2) :
    ambiguity frac cost rmin e1 ⊆ ambiguity frac cost rmin e2 := by
  rintro f ⟨j, hj, hc⟩; exact ⟨j, hj, by linarith⟩
 theorem selected_in_ambiguity {J k} (frac : J → Spectrum k) (cost : J → ℝ) (j : J) (eps : ℝ) (he : 0 ≤ eps) :
    frac j ∈ ambiguity frac cost (cost j) eps := ⟨j, rfl, by linarith⟩

-- Conditional full fixed-representation pipeline: calibration truth is a hypothesis, never a global axiom.
 theorem pipeline_recovery {k n m} (E : CandidateLibrary k n) (T : AffineTranslation n m)
    (f g : Spectrum k) (hf : f ∈ stdSimplex ℝ (Fin k))
    (ident : Identifiable (fun i => affine T (E i)))
    (solver : IsFCLS (fun i => affine T (E i)) (affine T (mixture E f)) g) : g=f := by
  rw [affine_mixture T E f hf.2] at solver
  exact fcls_exact_recovery _ f g hf ident solver
end SpectralBridge
