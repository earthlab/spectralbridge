import SpectralBridge.Inference

namespace SpectralBridge
-- Functional composition only; scene fitting, masks, file I/O and physical fidelity are not certified.
structure Pipeline (r o c t a l k : ℕ) where
  sensorObservation : Spectrum r → Spectrum o
  spectralCorrection : Spectrum o → Spectrum c
  sensorTranslation : Spectrum c → Spectrum t
  polygonAggregation : Spectrum t → Spectrum a
  libraryRepresentation : Spectrum a → Spectrum l
  abundanceEstimator : Spectrum l → Spectrum k
noncomputable def representation {r o c t a l k} (P : Pipeline r o c t a l k) :=
  P.libraryRepresentation ∘ P.polygonAggregation ∘ P.sensorTranslation ∘ P.spectralCorrection ∘ P.sensorObservation
noncomputable def fullPipeline {r o c t a l k} (P : Pipeline r o c t a l k) := P.abundanceEstimator ∘ representation P
 theorem full_pipeline_conditional {r o c t a l k} (P : Pipeline r o c t a l k)
    (E : CandidateLibrary k r) (f : Spectrum k) (hf : f ∈ stdSimplex ℝ (Fin k))
    (preserves : representation P (mixture E f) = mixture (fun i => representation P (E i)) f)
    (ident : Identifiable (fun i => representation P (E i)))
    (solver : IsFCLS (fun i => representation P (E i)) (representation P (mixture E f)) (fullPipeline P (mixture E f))) :
    fullPipeline P (mixture E f) = f := by
  rw [preserves] at solver
  exact fcls_exact_recovery _ f _ hf ident solver
end SpectralBridge
