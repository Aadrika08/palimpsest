import ChangeAudit.FreshBounded
import ChangeAudit.Numerical

noncomputable section
namespace ChangeAudit
open MeasureTheory ProbabilityTheory
open scoped BigOperators ENNReal NNReal
variable {Ω : Type*} [MeasurableSpace Ω]

/-- Expected contrasts may vary by position. This is an average over the
explicit schedule, not a claim that a balanced deterministic catalog is iid. -/
def centeredGap (target observed : ℕ → Ω → ℝ) : ℕ → Ω → ℝ :=
  fun n ω => target n ω - observed n ω

omit [MeasurableSpace Ω] in
theorem prefix_target_identity (target observed : ℕ → Ω → ℝ) (n : ℕ) (ω : Ω) :
    meanGap (centeredGap target observed) n ω =
      accumulated target n ω / n - accumulated observed n ω / n := by
  simp [meanGap, centeredGap, accumulated, Finset.sum_sub_distrib, sub_div]

/-- Constructor for deterministic position-specific means and fresh bounded
contrasts. The main ConditionalMGF interface separately permits predictable
conditional means when its exact conditional-MGF premise is discharged. -/
def freshOfContrasts {F : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsProbabilityMeasure μ] (D : ℕ → Ω → ℝ) (m : ℕ → ℝ)
    (current : ℕ → MeasurableSpace Ω)
    (hcur : ∀ n, current n ≤ ‹MeasurableSpace Ω›)
    (hmeas : ∀ n, StronglyMeasurable[current n] (D n))
    (hind : ∀ n, Indep (current n) (F n) μ)
    (hbounded : ∀ n, ∀ᵐ ω ∂μ, D n ω ∈ Set.Icc (-1) 1)
    (hmean : ∀ n, μ[D n] = m n)
    (hadapted : ∀ n, StronglyMeasurable[F (n+1)] (D n)) :
    FreshBounded (centeredGap (fun n _ => m n) D) F μ where
  center := m
  current := current
  current_le := hcur
  measurable := by intro n; have h := hmeas n; unfold centeredGap; fun_prop
  independent := hind
  bounded := by
    intro n
    filter_upwards [hbounded n] with ω hω
    exact centered_contrast_mem_Icc hω
  mean_zero := by
    intro n
    have hm := (hmeas n).mono (hcur n)
    have hi : Integrable (D n) μ := Integrable.of_mem_Icc (-1) 1 hm.aemeasurable (hbounded n)
    change μ[fun ω => m n - D n ω] = 0
    rw [integral_sub (integrable_const _) hi]
    simp [hmean]
  adapted := by intro n; have h := hadapted n; unfold centeredGap; fun_prop

/-- Familywise false acceptance bound for conservative endpoints and any
explicit target/observation gap representation. Targets can be predictable
conditional means; the conclusion is about their prefix average. -/
theorem finite_false_acceptance_bound {K : ℕ} (hK : 0<K)
    {g : Fin K → ℕ → Ω → ℝ} {truth estimate : Fin K → ℕ → Ω → ℝ}
    {scale alpha upperLog margin : ℝ}
    {F : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsProbabilityMeasure μ] (A : ∀j, ConditionalMGF (g j) scale F μ)
    (hs : 0<scale) (ha : 0<alpha)
    (hb : Real.log (1/(alpha/K)) ≤ upperLog)
    (hg : ∀j n ω, meanGap (g j) n ω = truth j n ω - estimate j n ω) :
    μ {ω | ∃j : Fin K, ∃n : ℕ, 0<n ∧
      estimate j n ω + conservativeRadius upperLog scale n ≤ -margin ∧
      -margin < truth j n ω} ≤ ENNReal.ofReal alpha := by
  apply (measure_mono (t := {ω | ∃j : Fin K,
    ω ∈ badEvent (g j) (alpha/K) scale}) ?_).trans (finite_anytime_bound hK A hs ha)
  intro ω hω
  rcases hω with ⟨j,n,hn,haccept,htruth⟩
  refine ⟨j,n,hn,?_⟩
  have hgate := conservative_acceptance hs hn hb haccept
  rw [hg]
  linarith

/-- Strict runtime acceptance (upper endpoint < -margin) guarantees a strict
improvement, except on the same familywise event. Includes the zero-truth
boundary that a non-strict conclusion alone would not exclude. -/
theorem finite_false_strict_acceptance_bound {K : ℕ} (hK : 0<K)
    {g : Fin K → ℕ → Ω → ℝ} {truth estimate : Fin K → ℕ → Ω → ℝ}
    {scale alpha upperLog margin : ℝ}
    {F : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsProbabilityMeasure μ] (A : ∀j, ConditionalMGF (g j) scale F μ)
    (hs : 0<scale) (ha : 0<alpha)
    (hb : Real.log (1/(alpha/K)) ≤ upperLog)
    (hg : ∀j n ω, meanGap (g j) n ω = truth j n ω - estimate j n ω) :
    μ {ω | ∃j : Fin K, ∃n : ℕ, 0<n ∧
      estimate j n ω + conservativeRadius upperLog scale n < -margin ∧
      -margin ≤ truth j n ω} ≤ ENNReal.ofReal alpha := by
  apply (measure_mono (t := {ω | ∃j : Fin K,
    ω ∈ badEvent (g j) (alpha/K) scale}) ?_).trans (finite_anytime_bound hK A hs ha)
  intro ω hω
  rcases hω with ⟨j,n,hn,haccept,htruth⟩
  refine ⟨j,n,hn,?_⟩
  have hrad := radius_le_conservative hs hn hb
  rw [hg]
  linarith

end ChangeAudit
