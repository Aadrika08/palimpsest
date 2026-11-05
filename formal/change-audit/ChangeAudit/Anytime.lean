import ChangeAudit.Exponential

noncomputable section
namespace ChangeAudit
open MeasureTheory ProbabilityTheory
open scoped BigOperators ENNReal NNReal
variable {Ω : Type*} [MeasurableSpace Ω]

def meanGap (g : ℕ → Ω → ℝ) (n : ℕ) (ω : Ω) : ℝ := accumulated g n ω / n

def singleRadius (alpha scale : ℝ) (n : ℕ) : ℝ :=
  Real.log (1/alpha) / (scale*n) + scale/2

def badEvent (g : ℕ → Ω → ℝ) (alpha scale : ℝ) : Set Ω :=
  {ω | ∃ n : ℕ, 0<n ∧ singleRadius alpha scale n < meanGap g n ω}

omit [MeasurableSpace Ω] in
theorem threshold_of_violation {g : ℕ → Ω → ℝ} {alpha scale : ℝ}
    (ha : 0<alpha) (hs : 0<scale) {n : ℕ} (hn : 0<n) {ω : Ω}
    (hv : singleRadius alpha scale n < meanGap g n ω) :
    1/alpha < wealth g scale n ω := by
  have hnR : (0:ℝ)<n := by exact_mod_cast hn
  have hsn : (0:ℝ)<scale*n := mul_pos hs hnR
  have hmul := mul_lt_mul_of_pos_left hv hsn
  have hleft : scale*(n:ℝ) * singleRadius alpha scale n =
      Real.log (1/alpha) + (n:ℝ)*scale^2/2 := by
    unfold singleRadius
    field_simp [ne_of_gt hs, ne_of_gt hnR]
  have hright : scale*(n:ℝ)*meanGap g n ω = scale*accumulated g n ω := by
    unfold meanGap
    field_simp [ne_of_gt hnR]
  rw [hleft, hright] at hmul
  have hlog : Real.log (1/alpha) <
      scale*accumulated g n ω - (n:ℝ)*scale^2/2 := by linarith
  have hexp := Real.exp_lt_exp.mpr hlog
  rw [Real.exp_log (one_div_pos.mpr ha)] at hexp
  exact hexp

/-- One declared stream, fixed betting scale, all positive prefix lengths. -/
theorem anytime_bound {g : ℕ → Ω → ℝ} {scale alpha : ℝ}
    {F : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsProbabilityMeasure μ] (A : ConditionalMGF g scale F μ)
    (hs : 0<scale) (ha : 0<alpha) :
    μ (badEvent g alpha scale) ≤ ENNReal.ofReal alpha := by
  let eps : ℝ≥0 := ⟨1/alpha, (one_div_pos.mpr ha).le⟩
  have heps : eps ≠ 0 := ne_of_gt (show 0<eps from one_div_pos.mpr ha)
  have hville := (exponential_supermartingale A).measure_ville_le_div
    (wealth_nonneg g scale) heps
  have hsubset : badEvent g alpha scale ⊆
      {ω | ∃ n : ℕ, (eps:ℝ) ≤ wealth g scale n ω} := by
    intro ω hω
    rcases hω with ⟨n, hn, hv⟩
    exact ⟨n, (threshold_of_violation ha hs hn hv).le⟩
  calc
    μ (badEvent g alpha scale) ≤ μ {ω | ∃ n : ℕ, (eps:ℝ) ≤ wealth g scale n ω} :=
      measure_mono hsubset
    _ ≤ ENNReal.ofReal (∫ ω, wealth g scale 0 ω ∂μ) / (eps:ℝ≥0∞) := hville
    _ = ENNReal.ofReal alpha := by
      have hi : ∫ ω, wealth g scale 0 ω ∂μ = (1:ℝ) := by rw [wealth_zero]; simp
      rw [hi, ENNReal.ofReal_one, ENNReal.coe_nnreal_eq]
      change 1 / ENNReal.ofReal (1/alpha) = ENNReal.ofReal alpha
      simp only [one_div, ENNReal.ofReal_inv_of_pos ha, inv_inv]

/-- Deterministic finite candidates may be correlated within a scenario.
Only their separate conditional-MGF premises are needed; no positive posterior
or Gibbs comparator is introduced. -/
theorem finite_anytime_bound {K : ℕ} (hK : 0<K)
    {g : Fin K → ℕ → Ω → ℝ} {scale alpha : ℝ}
    {F : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsProbabilityMeasure μ] (A : ∀j, ConditionalMGF (g j) scale F μ)
    (hs : 0<scale) (ha : 0<alpha) :
    μ {ω | ∃j : Fin K, ω ∈ badEvent (g j) (alpha/K) scale} ≤
      ENNReal.ofReal alpha := by
  have hKR : (0:ℝ)<K := by exact_mod_cast hK
  have hpart : 0<alpha/(K:ℝ) := div_pos ha hKR
  have heq : {ω | ∃j : Fin K, ω ∈ badEvent (g j) (alpha/K) scale} =
      ⋃ j : Fin K, badEvent (g j) (alpha/K) scale := by ext ω; simp
  rw [heq]
  calc
    μ (⋃ j : Fin K, badEvent (g j) (alpha/K) scale) ≤
        ∑' j : Fin K, μ (badEvent (g j) (alpha/K) scale) := measure_iUnion_le _
    _ ≤ ∑' _j : Fin K, ENNReal.ofReal (alpha/(K:ℝ)) :=
      ENNReal.tsum_le_tsum (fun j => anytime_bound (A j) hs hpart)
    _ = ENNReal.ofReal alpha := by
      rw [tsum_fintype, Finset.sum_const, Finset.card_univ, Fintype.card_fin,
        nsmul_eq_mul]
      rw [← ENNReal.ofReal_natCast, ← ENNReal.ofReal_mul (Nat.cast_nonneg K)]
      congr 1
      field_simp [ne_of_gt hKR]

omit [MeasurableSpace Ω] in
/-- A false margin acceptance is contained in the already-budgeted bad event. -/
theorem false_improvement_subset {g : ℕ → Ω → ℝ} {alpha scale margin : ℝ}
    {truth estimate : ℕ → Ω → ℝ}
    (hg : ∀ n ω, meanGap g n ω = truth n ω - estimate n ω) :
    {ω | ∃n : ℕ, 0<n ∧ estimate n ω + singleRadius alpha scale n ≤ -margin ∧
      -margin < truth n ω} ⊆ badEvent g alpha scale := by
  intro ω hω
  rcases hω with ⟨n,hn,ha,ht⟩
  refine ⟨n,hn,?_⟩
  rw [hg]
  linarith

end ChangeAudit
