import ChangeAudit.Contrast
import ChangeAudit.Ville
import Mathlib.MeasureTheory.Function.ConditionalExpectation.PullOut
import Mathlib.Probability.ConditionalExpectation

noncomputable section
namespace ChangeAudit
open MeasureTheory ProbabilityTheory
open scoped BigOperators ENNReal NNReal

variable {Ω : Type*} [MeasurableSpace Ω]

def accumulated (g : ℕ → Ω → ℝ) (n : ℕ) (ω : Ω) : ℝ :=
  ∑ i ∈ Finset.range n, g i ω

def wealth (g : ℕ → Ω → ℝ) (scale : ℝ) (n : ℕ) (ω : Ω) : ℝ :=
  Real.exp (scale * accumulated g n ω - (n : ℝ) * scale^2 / 2)

def factor (g : ℕ → Ω → ℝ) (scale : ℝ) (n : ℕ) (ω : Ω) : ℝ :=
  Real.exp (-(scale^2 / 2)) * Real.exp (scale * g n ω)

omit [MeasurableSpace Ω] in
@[simp] theorem wealth_zero (g : ℕ → Ω → ℝ) (scale : ℝ) :
    wealth g scale 0 = fun _ => 1 := by
  funext ω
  simp [wealth, accumulated]

omit [MeasurableSpace Ω] in
theorem wealth_nonneg (g : ℕ → Ω → ℝ) (scale : ℝ) :
    0 ≤ wealth g scale := by
  intro n ω
  exact (Real.exp_pos _).le

omit [MeasurableSpace Ω] in
theorem wealth_step (g : ℕ → Ω → ℝ) (scale : ℝ) (n : ℕ) :
    wealth g scale (n+1) = wealth g scale n * factor g scale n := by
  funext ω
  simp only [wealth, accumulated, Finset.sum_range_succ, factor, Pi.mul_apply]
  rw [← Real.exp_add, ← Real.exp_add]
  congr 1
  push_cast
  ring

/-- Explicit analytic boundary. Adaptedness and integrability are assumptions
about the declared stream, not facts inferred from hashes or an audit schema.
The MGF premise is weaker than independence; it permits predictable means and
nonidentical distributions. No tail bound is assumed here. -/
structure ConditionalMGF (g : ℕ → Ω → ℝ) (scale : ℝ)
    (F : Filtration ℕ ‹MeasurableSpace Ω›) (μ : Measure Ω) : Prop where
  adapted : StronglyAdapted F (wealth g scale)
  integrable : ∀ n, Integrable (wealth g scale n) μ
  exp_integrable : ∀ n, Integrable (fun ω => Real.exp (scale * g n ω)) μ
  mgf_le : ∀ n,
    μ[fun ω => Real.exp (scale * g n ω) | F n] ≤ᵐ[μ]
      fun _ => Real.exp (scale^2 / 2)

set_option backward.isDefEq.respectTransparency false in
/-- The conditional MGF bound constructs, rather than assumes, the nonnegative
exponential supermartingale. -/
theorem exponential_supermartingale
    {g : ℕ → Ω → ℝ} {scale : ℝ}
    {F : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsFiniteMeasure μ] (A : ConditionalMGF g scale F μ) :
    Supermartingale (wealth g scale) F μ := by
  apply supermartingale_nat A.adapted A.integrable
  intro n
  have hfactor : Integrable (factor g scale n) μ :=
    (A.exp_integrable n).const_mul _
  have hproduct : Integrable (wealth g scale n * factor g scale n) μ := by
    rw [← wealth_step]
    exact A.integrable (n+1)
  have hpull := condExp_mul_of_stronglyMeasurable_left
    (A.adapted n) hproduct hfactor
  have hsmul := condExp_smul (μ := μ) (Real.exp (-(scale^2 / 2)))
    (fun ω => Real.exp (scale * g n ω)) (F n)
  have hfac : μ[factor g scale n | F n] ≤ᵐ[μ] fun _ => 1 := by
    filter_upwards [hsmul, A.mgf_le n] with ω hs hm
    change μ[(Real.exp (-(scale^2/2))) • (fun ω => Real.exp (scale*g n ω)) | F n] ω ≤ 1
    rw [hs]
    change Real.exp (-(scale^2/2)) * _ ≤ 1
    calc
      _ ≤ Real.exp (-(scale^2/2)) * Real.exp (scale^2/2) :=
        mul_le_mul_of_nonneg_left hm (Real.exp_pos _).le
      _ = 1 := by rw [← Real.exp_add]; simp
  rw [wealth_step]
  filter_upwards [hpull, hfac] with ω hp hf
  rw [hp]
  change wealth g scale n ω * μ[factor g scale n | F n] ω ≤ wealth g scale n ω
  nlinarith [mul_le_mul_of_nonneg_left hf (wealth_nonneg g scale n ω)]

end ChangeAudit
