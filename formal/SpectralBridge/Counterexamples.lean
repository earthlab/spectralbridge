import SpectralBridge.Inference

namespace SpectralBridge
open scoped BigOperators
noncomputable def ambiguousE : CandidateLibrary 3 2 := ![![1,0], ![0,1], ![1/2,1/2]]
noncomputable def truth3 : Spectrum 3 := ![0,0,1]
noncomputable def alternative3 : Spectrum 3 := ![1/2,1/2,0]
 theorem ambiguous_truth_feasible : truth3 ∈ stdSimplex ℝ (Fin 3) := by
  constructor
  · intro i; fin_cases i <;> norm_num [truth3]
  · norm_num [truth3, Fin.sum_univ_succ]
 theorem ambiguous_alternative_feasible : alternative3 ∈ stdSimplex ℝ (Fin 3) := by
  constructor
  · intro i; fin_cases i <;> norm_num [alternative3]
  · norm_num [alternative3, Fin.sum_univ_succ]
 theorem ambiguous_reconstruction : mixture ambiguousE truth3 = mixture ambiguousE alternative3 := by
  ext i; fin_cases i <;> norm_num [mixture, Fin.sum_univ_succ, ambiguousE, truth3, alternative3]
 theorem reconstruction_not_identifiability : ¬ Identifiable ambiguousE := by
  intro h
  have he := congrFun (h ambiguous_truth_feasible ambiguous_alternative_feasible ambiguous_reconstruction) 0
  norm_num [truth3, alternative3] at he
 theorem perfect_prediction_not_unique_inversion :
    loss ambiguousE (mixture ambiguousE truth3) truth3 = 0 ∧ ¬ Identifiable ambiguousE :=
  ⟨(loss_zero_iff _ _ _).mpr rfl, reconstruction_not_identifiability⟩
-- Distinct singleton C and two-component A/B systems have exactly equal spectra and different class weights.
 theorem mesma_ambiguity : loss ambiguousE (mixture ambiguousE truth3) alternative3 = 0 ∧ truth3 ≠ alternative3 := by
  constructor
  · exact (loss_zero_iff _ _ _).mpr ambiguous_reconstruction.symm
  · intro h; have := congrFun h 0; norm_num [truth3, alternative3] at this

noncomputable def sumSensor : Spectrum 2 →ₗ[ℝ] Spectrum 1 where
  toFun x := fun _ => x 0 + x 1
  map_add' x y := by ext; simp; ring
  map_smul' a x := by ext; simp; ring
noncomputable def twoE : CandidateLibrary 2 2 := ![![1,0],![0,1]]
 theorem hyperspectral_identifiable : Identifiable twoE := by
  intro f hf g hg h
  have he0 := congrFun h 0
  have he1 := congrFun h 1
  simp [mixture, Fin.sum_univ_two, twoE] at he0 he1
  ext i; fin_cases i <;> assumption
 theorem convolution_destroys_identifiability : ¬ Identifiable (fun i => sumSensor (twoE i)) := by
  intro h
  have h0 := pair_simplex 0 (by norm_num) (by norm_num)
  have h1 := pair_simplex 1 (by norm_num) (by norm_num)
  have eqs : mixture (fun i => sumSensor (twoE i)) (pairFractions 0) =
      mixture (fun i => sumSensor (twoE i)) (pairFractions 1) := by
    ext i; fin_cases i; norm_num [mixture, Fin.sum_univ_two, sumSensor, twoE, pairFractions]
  have bad := congrFun (h h0 h1 eqs) 0
  norm_num [pairFractions] at bad
-- The candidate library is misspecified relative to the generating biological categories.
noncomputable def wrongE : CandidateLibrary 2 2 := ![![1,1],![0,0]]
 theorem residual_does_not_order_abundance_error :
    loss wrongE (![0,0]) (pairFractions 0) < loss wrongE (![0,0]) (pairFractions 1) ∧
    loss twoE (pairFractions 1) (pairFractions 0) > loss twoE (pairFractions 1) (pairFractions 1) := by
  norm_num [loss, mixture, wrongE, twoE, pairFractions, Fin.sum_univ_two]
end SpectralBridge
