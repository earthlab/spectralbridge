import SpectralBridge.Counterexamples
import SpectralBridge.Ridge

/-! Executable rational examples plus exact-real checks. These are finite conformance examples,
not a proof that IEEE Python implements the real-valued specification for all inputs. -/
namespace SpectralBridge.Bridge

-- Rational finite-example calculations. The accompanying real theorems certify these toy optima.
def qDot (x y : List ℚ) : ℚ := (List.zipWith (· * ·) x y).sum
def qMix (f : ℚ) (a b : List ℚ) : List ℚ := List.zipWith (fun x y => f*x+(1-f)*y) a b
def qLoss (x y : List ℚ) : ℚ := (List.zipWith (fun a b => (a-b)^2) x y).sum / x.length

def toyFCLS : List ℚ :=
  let f := (1 + (1:ℚ)/4 - 3/4)/2
  [f, 1-f]

def toyMESMA : List ℚ :=
  -- Admitted faces at target [.5,.5]: the three vertices plus the positive A/B interior.
  -- A/C and B/C optima lie on the already included C boundary.
  let target : List ℚ := [1/2,1/2]
  let candidates : List (List ℚ × List ℚ) := [([1,0],[1,0,0]), ([0,1],[0,1,0]),
    ([1/2,1/2],[0,0,1]), (qMix (1/2) [1,0] [0,1],[1/2,1/2,0])]
  let best := candidates.tail.foldl (fun old next =>
    if qLoss target next.1 < qLoss target old.1 - (1:ℚ)/100000000000000 then next else old) ([1,0],[1,0,0])
  best.2

def qProject (x : List ℚ) : List ℚ :=
  let sorted := x.mergeSort (fun a b => decide (a ≥ b))
  let state := sorted.foldl (fun (s : ℚ × ℕ × ℚ) v =>
    let count := s.2.1 + 1
    let total := s.1 + v
    let theta := (total-1)/count
    (total, count, if v-theta > 0 then theta else s.2.2)) (0,0,0)
  x.map (fun v => max 0 (v-state.2.2))

def cases : List (String × List ℚ) := [
  ("convolution", [20 / (4 + (1:ℚ)/1000000000000)]),
  ("multiplicative", [100 * (1 + (-4444952:ℚ)/100000000)]),
  ("affine", [2*3+1]),
  ("polygon_mean", [(2+6)/2]),
  ("mixture", qMix (1/5) [1,0] [0,1]),
  ("fcls_oracle", toyFCLS),
  ("mesma", toyMESMA),
  ("ridge", [1/2 - (1:ℚ)/3 * (1/2), 1/2 + (1:ℚ)/3 * (1/2)]),
  ("simplex_projection", qProject [-2,1,4/5])]

 theorem convolution_real : weighted (epsilonWeight (![1,3] : Spectrum 2) ((1:ℝ)/1000000000000)) (![2,6]) =
    (20:ℝ)/(4+1/1000000000000) := by
  norm_num [weighted, epsilonWeight, Fin.sum_univ_two]
 theorem multiplicative_real : (100:ℝ)*(1+(-4444952:ℝ)/100000000) = 11944381/125000 := by norm_num
 theorem affine_real : (2:ℝ)*3+1 = 7 := by norm_num
 theorem mean_real : ((2:ℝ)+6)/2 = 4 := by norm_num
 theorem mixture_real : mixture twoE (pairFractions (1/5)) = ![(1:ℝ)/5,4/5] := by
  ext i; fin_cases i <;> norm_num [mixture, twoE, pairFractions, Fin.sum_univ_two]
 theorem fcls_real : IsFCLS twoE (![ (1:ℝ)/4,3/4]) (pairFractions (1/4)) := by
  have he : mixture twoE (pairFractions (1/4)) = ![(1:ℝ)/4,3/4] := by
    ext i; fin_cases i <;> norm_num [mixture, twoE, pairFractions, Fin.sum_univ_two]
  rw [← he]; exact oracle_fcls _ _ (pair_simplex _ (by norm_num) (by norm_num))
 theorem mesma_real : loss ambiguousE (![ (1:ℝ)/2,1/2]) truth3 = 0 := by
  apply (loss_zero_iff _ _ _).mpr
  ext i; fin_cases i <;> norm_num [mixture, ambiguousE, truth3, Fin.sum_univ_succ]
 theorem ridge_real : (2+1:ℝ)*(-1/3) = -1 ∧ (2+1:ℝ)*(1/3)=1 ∧
    (1/2:ℝ) - (1/3)*(1/2) = 1/3 ∧ (1/2:ℝ)+(1/3)*(1/2)=2/3 := by norm_num
-- Sorting certificate for [-2,1,4/5]. Generic projection uniqueness identifies this KKT point.
 theorem projection_real :
    max (0:ℝ) (-2-2/5)=0 ∧ max (0:ℝ) (1-2/5)=3/5 ∧
    max (0:ℝ) (4/5-2/5)=2/5 ∧ (0:ℝ)+3/5+2/5=1 := by norm_num
 theorem projection_certificate :
    IsProjection (simplexE 3) (WithLp.toLp 2 (![-2,1,(4:ℝ)/5]))
      (WithLp.toLp 2 (![0,(3:ℝ)/5,2/5])) := by
  apply threshold_projection _ _ ((2:ℝ)/5)
  · constructor
    · intro i; fin_cases i <;> norm_num
    · norm_num [Fin.sum_univ_succ]
  · intro i; fin_cases i <;> norm_num
end SpectralBridge.Bridge

def main : IO Unit := do
  let entries := SpectralBridge.Bridge.cases.map fun (name, qs) =>
    "\"" ++ name ++ "\":[" ++ String.intercalate "," (qs.map fun q => "\"" ++ s!"{q.num}/{q.den}" ++ "\"") ++ "]"
  IO.println ("{" ++ String.intercalate "," entries ++ "}")
