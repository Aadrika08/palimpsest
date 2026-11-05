import ChangeAudit.Exponential

noncomputable section
namespace ChangeAudit
open MeasureTheory ProbabilityTheory
open scoped BigOperators ENNReal NNReal
variable {Ω : Type*} [MeasurableSpace Ω]

/-- A fresh centered stream with a position-specific deterministic interval of
width two. The center may differ at every position: no iid catalog assumption.
Independence here is an explicit mathematical premise, never a hash field. -/
structure FreshBounded (g : ℕ → Ω → ℝ)
    (F : Filtration ℕ ‹MeasurableSpace Ω›) (μ : Measure Ω) where
  center : ℕ → ℝ
  current : ℕ → MeasurableSpace Ω
  current_le : ∀ n, current n ≤ ‹MeasurableSpace Ω›
  measurable : ∀ n, StronglyMeasurable[current n] (g n)
  independent : ∀ n, Indep (current n) (F n) μ
  bounded : ∀ n, ∀ᵐ ω ∂μ, g n ω ∈ Set.Icc (center n-1) (center n+1)
  mean_zero : ∀ n, μ[g n] = 0
  adapted : ∀ n, StronglyMeasurable[F (n+1)] (g n)

namespace FreshBounded
variable {g : ℕ → Ω → ℝ} {F : Filtration ℕ ‹MeasurableSpace Ω›}
variable {μ : Measure Ω} [IsProbabilityMeasure μ]

theorem subgaussian (A : FreshBounded g F μ) (n : ℕ) :
    HasSubgaussianMGF (g n) 1 μ := by
  have h := hasSubgaussianMGF_of_mem_Icc_of_integral_eq_zero
    ((A.measurable n).mono (A.current_le n)).aemeasurable (A.bounded n) (A.mean_zero n)
  have heq : A.center n+1-(A.center n-1) = 2 := by ring
  rw [heq] at h
  norm_num at h
  exact h

theorem conditional_mgf (A : FreshBounded g F μ) (scale : ℝ) (n : ℕ) :
    μ[fun ω => Real.exp (scale*g n ω) | F n] ≤ᵐ[μ]
      fun _ => Real.exp (scale^2/2) := by
  have hmeas : StronglyMeasurable[A.current n] (fun ω => Real.exp (scale*g n ω)) := by
    have hg := A.measurable n
    fun_prop
  have hindep := condExp_indep_eq (A.current_le n) (F.le n) hmeas (A.independent n)
  filter_upwards [hindep] with ω hω
  rw [hω]
  simpa [mgf] using (A.subgaussian n).mgf_le scale

omit [IsProbabilityMeasure μ] in
theorem wealth_adapted (A : FreshBounded g F μ) (scale : ℝ) :
    StronglyAdapted F (wealth g scale) := by
  intro n
  induction n with
  | zero => rw [wealth_zero]; exact stronglyMeasurable_const
  | succ n ih =>
    rw [wealth_step]
    have hp := ih.mono (F.mono (Nat.le_succ n))
    have hg := A.adapted n
    unfold factor
    fun_prop

omit [IsProbabilityMeasure μ] in
theorem factor_bounded (A : FreshBounded g F μ) {scale : ℝ} (hs : 0≤scale) (n : ℕ) :
    ∀ᵐ ω ∂μ, ‖factor g scale n ω‖ ≤
      Real.exp (-(scale^2/2)) * Real.exp (scale*(A.center n+1)) := by
  filter_upwards [A.bounded n] with ω hω
  have he := Real.exp_le_exp.mpr (mul_le_mul_of_nonneg_left hω.2 hs)
  unfold factor
  rw [Real.norm_eq_abs, abs_of_pos (mul_pos (Real.exp_pos _) (Real.exp_pos _))]
  exact mul_le_mul_of_nonneg_left he (Real.exp_pos _).le

theorem wealth_integrable (A : FreshBounded g F μ) {scale : ℝ} (hs : 0≤scale) :
    ∀ n, Integrable (wealth g scale n) μ := by
  intro n
  induction n with
  | zero => rw [wealth_zero]; exact integrable_const _
  | succ n ih =>
    rw [wealth_step]
    have hg := (A.measurable n).mono (A.current_le n)
    have hf : AEStronglyMeasurable (factor g scale n) μ := by
      unfold factor
      fun_prop
    exact ih.mul_bdd hf (A.factor_bounded hs n)

/-- Discharges all analytic premises of ConditionalMGF from explicit bounded
fresh observations, including exponential-process integrability/adaptedness. -/
def toConditionalMGF (A : FreshBounded g F μ) (scale : ℝ) (hs : 0≤scale) :
    ConditionalMGF g scale F μ where
  adapted := A.wealth_adapted scale
  integrable := A.wealth_integrable hs
  exp_integrable := fun n => (A.subgaussian n).integrable_exp_mul scale
  mgf_le := A.conditional_mgf scale

end FreshBounded
end ChangeAudit
