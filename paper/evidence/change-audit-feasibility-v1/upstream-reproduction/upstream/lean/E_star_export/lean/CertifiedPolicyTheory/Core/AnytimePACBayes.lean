import CertifiedPolicyTheory.Core.PairedPACBayes
import Mathlib.Probability.Martingale.OptionalStopping
import Mathlib.MeasureTheory.Function.ConditionalExpectation.PullOut
import Mathlib.Probability.ConditionalExpectation
import Mathlib.Probability.Moments.SubGaussian
import FLT_Proofs.PureMath.Ville

/-!
# Anytime paired PAC--Bayes

The theorem in this file is deliberately split at the e-process boundary.
The statistical premise is a nonnegative mixture supermartingale generated
before the current audit.  The posterior is quantified only after the Ville
event is obtained, so it may depend on the observed audit.

The bounded/fresh-audit construction enters through the one-step conditional
e-process inequality consumed by `pairedEProcessOfPairwiseStep`.  The headline
theorem then uses only the resulting invariant, finite Donsker--Varadhan, and
Ville's inequality.
-/

open scoped BigOperators ENNReal NNReal
open MeasureTheory ProbabilityTheory Filter

namespace CertifiedPolicyTheory

universe u v

open PositiveFiniteLaw

variable {H : Type u} [Fintype H]
variable {Ω : Type v} [MeasurableSpace Ω]

/-- A sequential empirical-risk process for a fixed population risk. -/
structure SequentialPairedRiskModel (H : Type u) (Ω : Type v) where
  populationRisk : H → ℝ
  empiricalRisk : ℕ → Ω → H → ℝ

namespace SequentialPairedRiskModel

variable (M : SequentialPairedRiskModel H Ω)

/-- Population regression of candidate `Q` against deployed parent `G`. -/
def trueRegression (Q G : PositiveFiniteLaw H) : ℝ :=
  Q.expect M.populationRisk - G.expect M.populationRisk

/-- Empirical regression at audit time `n` and outcome `ω`. -/
def empiricalRegression (n : ℕ) (ω : Ω)
    (Q G : PositiveFiniteLaw H) : ℝ :=
  Q.expect (M.empiricalRisk n ω) - G.expect (M.empiricalRisk n ω)

/-- Pairwise population-minus-empirical regression gap. -/
def pairedGap (n : ℕ) (ω : Ω) (x : H × H) : ℝ :=
  (M.populationRisk x.1 - M.populationRisk x.2) -
    (M.empiricalRisk n ω x.1 - M.empiricalRisk n ω x.2)

/-- The cumulative population-minus-empirical paired gap at audit time `n`. -/
def cumulativeGap (n : ℕ) (ω : Ω) (x : H × H) : ℝ :=
  (n : ℝ) * M.pairedGap n ω x

/-- The one-step increment whose partial sums are `cumulativeGap`. -/
def pairIncrement (n : ℕ) (ω : Ω) (x : H × H) : ℝ :=
  M.cumulativeGap (n + 1) ω x - M.cumulativeGap n ω x

omit [Fintype H] [MeasurableSpace Ω] in
/-- The cumulative gap updates by exactly one `pairIncrement`. -/
theorem cumulativeGap_succ (n : ℕ) (ω : Ω) (x : H × H) :
    M.cumulativeGap (n + 1) ω x =
      M.cumulativeGap n ω x + M.pairIncrement n ω x := by
  simp [pairIncrement]

omit [MeasurableSpace Ω] in
/-- Product expectation of the sequential paired gap. -/
theorem expect_pairedGap (n : ℕ) (ω : Ω)
    (Q G : PositiveFiniteLaw H) :
    (Q.product G).expect (M.pairedGap n ω) =
      M.trueRegression Q G - M.empiricalRegression n ω Q G := by
  unfold pairedGap trueRegression empiricalRegression
  rw [PositiveFiniteLaw.expect_sub, PositiveFiniteLaw.expect_sub,
    PositiveFiniteLaw.expect_sub,
    Q.expect_product_left G M.populationRisk,
    Q.expect_product_right G M.populationRisk,
    Q.expect_product_left G (M.empiricalRisk n ω),
    Q.expect_product_right G (M.empiricalRisk n ω)]

end SequentialPairedRiskModel



/--
A paired PAC--Bayes e-process for one predictable round and one betting scale.

`varianceRate` is the compensator per observation.  For a loss in an interval
of width `R`, the bounded Hoeffding construction uses
`varianceRate = scale^2 * R^2 / 2`.
-/
structure PairedEProcess
    (M : SequentialPairedRiskModel H Ω)
    (prior G : PositiveFiniteLaw H)
    (ℱ : Filtration ℕ ‹MeasurableSpace Ω›)
    (μ : Measure Ω) where
  scale : ℝ
  scale_pos : 0 < scale
  varianceRate : ℝ
  varianceRate_nonneg : 0 ≤ varianceRate
  wealth : ℕ → Ω → ℝ
  wealth_eq : ∀ n ω,
    wealth n ω =
      (prior.product G).expect (fun x =>
        Real.exp
          (scale * (n : ℝ) * M.pairedGap n ω x -
            (n : ℝ) * varianceRate))
  supermartingale : Supermartingale wealth ℱ μ

/--
A nonnegative adapted multiplicative process is a supermartingale whenever its
next factor has conditional expectation at most one.  This is the exact
conditional-MGF/e-factor bridge used by bounded Hoeffding constructions and by
betting e-processes.
-/
theorem supermartingale_of_multiplicative_step
    {ℱ : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsFiniteMeasure μ]
    (wealth factor : ℕ → Ω → ℝ)
    (wealthAdapted : StronglyAdapted ℱ wealth)
    (wealthIntegrable : ∀ n, Integrable (wealth n) μ)
    (factorIntegrable : ∀ n, Integrable (factor n) μ)
    (productIntegrable : ∀ n, Integrable (wealth n * factor n) μ)
    (wealthNonneg : 0 ≤ wealth)
    (stepEq : ∀ n, wealth (n + 1) = wealth n * factor n)
    (condFactor_le_one : ∀ n,
      μ[factor n | ℱ n] ≤ᵐ[μ] fun _ => 1) :
    Supermartingale wealth ℱ μ := by
  apply supermartingale_nat wealthAdapted wealthIntegrable
  intro n
  rw [stepEq n]
  have hpull := condExp_mul_of_stronglyMeasurable_left
    (wealthAdapted n) (productIntegrable n) (factorIntegrable n)
  filter_upwards [hpull, condFactor_le_one n] with ω hpullω hfactorω
  rw [hpullω]
  simpa using mul_le_mul_of_nonneg_left hfactorω (wealthNonneg n ω)

/-- Finite prior-parent mixture of pairwise wealth processes. -/
def pairwiseMixtureWealth
    (prior G : PositiveFiniteLaw H)
    (pairWealth : H × H → ℕ → Ω → ℝ) : ℕ → Ω → ℝ :=
  ∑ x : H × H, (prior.product G).prob x • pairWealth x

/-- A finite positive mixture of supermartingales is a supermartingale. -/
theorem pairwiseMixture_supermartingale
    {ℱ : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    (prior G : PositiveFiniteLaw H)
    (pairWealth : H × H → ℕ → Ω → ℝ)
    (hpair : ∀ x, Supermartingale (pairWealth x) ℱ μ) :
    Supermartingale (pairwiseMixtureWealth prior G pairWealth) ℱ μ := by
  classical
  let P := prior.product G
  have hsum : ∀ s : Finset (H × H),
      Supermartingale (∑ x ∈ s, P.prob x • pairWealth x) ℱ μ := by
    intro s
    induction s using Finset.induction_on with
    | empty =>
        simpa using (martingale_zero ℝ ℱ μ).supermartingale
    | @insert x s hx ih =>
        rw [Finset.sum_insert hx]
        exact (hpair x).smul_nonneg (P.prob_pos x).le |>.add ih
  simpa [pairwiseMixtureWealth, P] using hsum Finset.univ

/--
Construct the paired mixture e-process from pairwise supermartingale witnesses.
This discharges the finite-mixture line of T1 inside the kernel.
-/
def pairedEProcessOfPairwise
    {ℱ : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    (M : SequentialPairedRiskModel H Ω)
    (prior G : PositiveFiniteLaw H)
    (scale varianceRate : ℝ)
    (scale_pos : 0 < scale)
    (varianceRate_nonneg : 0 ≤ varianceRate)
    (pairWealth : H × H → ℕ → Ω → ℝ)
    (pairWealth_eq : ∀ x n ω,
      pairWealth x n ω =
        Real.exp
          (scale * (n : ℝ) * M.pairedGap n ω x -
            (n : ℝ) * varianceRate))
    (pairSupermartingale : ∀ x,
      Supermartingale (pairWealth x) ℱ μ) :
    PairedEProcess M prior G ℱ μ where
  scale := scale
  scale_pos := scale_pos
  varianceRate := varianceRate
  varianceRate_nonneg := varianceRate_nonneg
  wealth := pairwiseMixtureWealth prior G pairWealth
  wealth_eq := by
    intro n ω
    simp [pairwiseMixtureWealth, PositiveFiniteLaw.expect,
      Pi.smul_apply, pairWealth_eq]
  supermartingale :=
    pairwiseMixture_supermartingale prior G pairWealth pairSupermartingale

/--
Construct T1's e-process from one-step conditional e-process inequalities.
A bounded fresh-audit Hoeffding argument instantiates `pairStep` with
`varianceRate = scale^2 * R^2 / 2`.
-/
def pairedEProcessOfPairwiseStep
    {ℱ : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsFiniteMeasure μ]
    (M : SequentialPairedRiskModel H Ω)
    (prior G : PositiveFiniteLaw H)
    (scale varianceRate : ℝ)
    (scale_pos : 0 < scale)
    (varianceRate_nonneg : 0 ≤ varianceRate)
    (pairWealth : H × H → ℕ → Ω → ℝ)
    (pairWealth_eq : ∀ x n ω,
      pairWealth x n ω =
        Real.exp
          (scale * (n : ℝ) * M.pairedGap n ω x -
            (n : ℝ) * varianceRate))
    (pairAdapted : ∀ x, StronglyAdapted ℱ (pairWealth x))
    (pairIntegrable : ∀ x n, Integrable (pairWealth x n) μ)
    (pairStep : ∀ x n,
      μ[pairWealth x (n + 1) | ℱ n] ≤ᵐ[μ] pairWealth x n) :
    PairedEProcess M prior G ℱ μ :=
  pairedEProcessOfPairwise M prior G scale varianceRate
    scale_pos varianceRate_nonneg pairWealth pairWealth_eq
    (fun x => supermartingale_nat (pairAdapted x)
      (pairIntegrable x) (pairStep x))

namespace PairedEProcess

variable {M : SequentialPairedRiskModel H Ω}
variable {prior G : PositiveFiniteLaw H}
variable {ℱ : Filtration ℕ ‹MeasurableSpace Ω›}
variable {μ : Measure Ω}

/-- Mixture wealth is pointwise nonnegative. -/
theorem wealth_nonneg (E : PairedEProcess M prior G ℱ μ) (n : ℕ) :
    0 ≤ E.wealth n := by
  intro ω
  rw [E.wealth_eq]
  exact Finset.sum_nonneg fun x _ =>
    mul_nonneg ((prior.product G).prob_pos x).le (Real.exp_pos _).le

/-- Mixture wealth starts exactly at one. -/
theorem wealth_zero (E : PairedEProcess M prior G ℱ μ) :
    E.wealth 0 = fun _ => 1 := by
  funext ω
  rw [E.wealth_eq]
  simpa [PositiveFiniteLaw.expect] using (prior.product G).sum_prob

/--
Finite paired Donsker--Varadhan turns a posterior regression gap into a lower
bound on mixture wealth.  This statement is deterministic and uniform over
posteriors.
-/
theorem exp_regression_gap_sub_kl_le_wealth
    (E : PairedEProcess M prior G ℱ μ)
    (n : ℕ) (ω : Ω) (Q : PositiveFiniteLaw H) :
    Real.exp
        (E.scale * (n : ℝ) *
            (M.trueRegression Q G - M.empiricalRegression n ω Q G) -
          (n : ℝ) * E.varianceRate - Q.kl prior) ≤
      E.wealth n ω := by
  let f : H × H → ℝ := fun x =>
    E.scale * (n : ℝ) * M.pairedGap n ω x -
      (n : ℝ) * E.varianceRate
  have hdv := PositiveFiniteLaw.exp_paired_expect_sub_kl_le Q prior G f
  have hEf :
      (Q.product G).expect f =
        E.scale * (n : ℝ) *
            (M.trueRegression Q G - M.empiricalRegression n ω Q G) -
          (n : ℝ) * E.varianceRate := by
    rw [show f = fun x =>
      E.scale * (n : ℝ) * M.pairedGap n ω x -
        (n : ℝ) * E.varianceRate by rfl]
    rw [PositiveFiniteLaw.expect_sub,
      PositiveFiniteLaw.expect_smul,
      PositiveFiniteLaw.expect_const,
      M.expect_pairedGap]
  rw [hEf] at hdv
  rw [E.wealth_eq]
  exact hdv

/-- PAC--Bayes radius associated with a Ville threshold `1 / α`. -/
noncomputable def radius (E : PairedEProcess M prior G ℱ μ)
    (α : ℝ) (n : ℕ) (Q : PositiveFiniteLaw H) : ℝ :=
  (Q.kl prior + Real.log (1 / α) + (n : ℝ) * E.varianceRate) /
    (E.scale * (n : ℝ))

/-- A posterior violation forces the e-process above the Ville threshold. -/
theorem wealth_gt_inv_of_violation
    (E : PairedEProcess M prior G ℱ μ)
    {α : ℝ} (hα : 0 < α) {n : ℕ} (hn : 0 < n)
    {ω : Ω} {Q : PositiveFiniteLaw H}
    (hviol :
      M.trueRegression Q G >
        M.empiricalRegression n ω Q G + E.radius α n Q) :
    1 / α < E.wealth n ω := by
  have hnR : 0 < (n : ℝ) := by exact_mod_cast hn
  have hscaleN : 0 < E.scale * (n : ℝ) := mul_pos E.scale_pos hnR
  have hmul :
      Q.kl prior + Real.log (1 / α) + (n : ℝ) * E.varianceRate <
        E.scale * (n : ℝ) *
          (M.trueRegression Q G - M.empiricalRegression n ω Q G) := by
    have hrad :
        E.radius α n Q <
          M.trueRegression Q G - M.empiricalRegression n ω Q G := by
      rw [lt_sub_iff_add_lt]
      linarith
    have := (div_lt_iff₀ hscaleN).mp hrad
    simpa [radius, add_assoc, mul_assoc, mul_comm, mul_left_comm] using this
  have hexpArg :
      Real.log (1 / α) <
        E.scale * (n : ℝ) *
            (M.trueRegression Q G - M.empiricalRegression n ω Q G) -
          (n : ℝ) * E.varianceRate - Q.kl prior := by
    linarith
  have hposInv : 0 < 1 / α := one_div_pos.mpr hα
  have hexp :
      1 / α < Real.exp
        (E.scale * (n : ℝ) *
            (M.trueRegression Q G - M.empiricalRegression n ω Q G) -
          (n : ℝ) * E.varianceRate - Q.kl prior) := by
    rw [← Real.exp_log hposInv]
    exact Real.exp_lt_exp.mpr hexpArg
  exact lt_of_lt_of_le hexp (E.exp_regression_gap_sub_kl_le_wealth n ω Q)

/-- The bad event for one round and one betting scale. -/
def badEvent (E : PairedEProcess M prior G ℱ μ) (α : ℝ) : Set Ω :=
  {ω | ∃ n : ℕ, 0 < n ∧ ∃ Q : PositiveFiniteLaw H,
    M.trueRegression Q G >
      M.empiricalRegression n ω Q G + E.radius α n Q}

/-- Every PAC--Bayes violation is contained in a Ville crossing event. -/
theorem badEvent_subset_crossing
    (E : PairedEProcess M prior G ℱ μ)
    {α : ℝ} (hα : 0 < α) :
    E.badEvent α ⊆ {ω | ∃ n : ℕ, 1 / α ≤ E.wealth n ω} := by
  intro ω hω
  rcases hω with ⟨n, hn, Q, hviol⟩
  exact ⟨n, (E.wealth_gt_inv_of_violation hα hn hviol).le⟩

/--
## T1, single round and single betting scale

With probability at least `1 - α`, the paired PAC--Bayes inequality holds
simultaneously for every positive audit time and every posterior, including a
posterior selected after observing the audit.
-/
theorem measure_badEvent_le
    [IsProbabilityMeasure μ]
    (E : PairedEProcess M prior G ℱ μ)
    {α : ℝ} (hα : 0 < α) :
    μ (E.badEvent α) ≤ ENNReal.ofReal α := by
  have hthreshold : 0 < 1 / α := one_div_pos.mpr hα
  let ε : ℝ≥0 := ⟨1 / α, hthreshold.le⟩
  have hεpos : 0 < ε := hthreshold
  have hε : ε ≠ 0 := ne_of_gt hεpos
  have hville := E.supermartingale.measure_ville_le_div
    (E.wealth_nonneg) hε
  have hsubset :
      E.badEvent α ⊆ {ω | ∃ n : ℕ, (ε : ℝ) ≤ E.wealth n ω} := by
    intro ω hω
    rcases E.badEvent_subset_crossing hα hω with ⟨n, hn⟩
    refine ⟨n, ?_⟩
    change 1 / α ≤ E.wealth n ω
    exact hn
  calc
    μ (E.badEvent α) ≤ μ {ω | ∃ n : ℕ, (ε : ℝ) ≤ E.wealth n ω} :=
      measure_mono hsubset
    _ ≤ ENNReal.ofReal (∫ ω, E.wealth 0 ω ∂μ) / (ε : ℝ≥0∞) := hville
    _ = ENNReal.ofReal α := by
      have hint : ∫ ω, E.wealth 0 ω ∂μ = (1 : ℝ) := by
        rw [E.wealth_zero]
        simp
      rw [hint, ENNReal.ofReal_one]
      rw [ENNReal.coe_nnreal_eq]
      have hεreal : (ε : ℝ) = 1 / α := rfl
      rw [hεreal]
      rw [show (1 / α : ℝ) = α⁻¹ by simp only [one_div]]
      rw [one_div, ENNReal.ofReal_inv_of_pos hα, inv_inv]

/-- Good-event formulation of T1. -/
theorem ae_anytime_paired_pacBayes
    [IsProbabilityMeasure μ]
    (E : PairedEProcess M prior G ℱ μ)
    {α : ℝ} (hα : 0 < α) :
    μ {ω | ∀ n : ℕ, 0 < n → ∀ Q : PositiveFiniteLaw H,
      M.trueRegression Q G ≤
        M.empiricalRegression n ω Q G + E.radius α n Q}ᶜ ≤
      ENNReal.ofReal α := by
  have heq :
      {ω | ∀ n : ℕ, 0 < n → ∀ Q : PositiveFiniteLaw H,
        M.trueRegression Q G ≤
          M.empiricalRegression n ω Q G + E.radius α n Q}ᶜ =
        E.badEvent α := by
    ext ω
    simp only [Set.mem_compl_iff, Set.mem_setOf_eq, badEvent]
    push Not
    rfl
  rw [heq]
  exact E.measure_badEvent_le hα

/-- A false accepted-improvement event: the empirical gate accepts margin `γ`,
but the true regression is worse than `-γ`. -/
def falseImprovementEvent
    (E : PairedEProcess M prior G ℱ μ) (α γ : ℝ) : Set Ω :=
  {ω | ∃ n : ℕ, 0 < n ∧ ∃ Q : PositiveFiniteLaw H,
    M.empiricalRegression n ω Q G + E.radius α n Q ≤ -γ ∧
      M.trueRegression Q G > -γ}

/-- Every false accepted improvement is an ordinary T1 violation. -/
theorem falseImprovementEvent_subset_badEvent
    (E : PairedEProcess M prior G ℱ μ) (α γ : ℝ) :
    E.falseImprovementEvent α γ ⊆ E.badEvent α := by
  intro ω hω
  rcases hω with ⟨n, hn, Q, hgate, hfalse⟩
  refine ⟨n, hn, Q, ?_⟩
  exact lt_of_le_of_lt hgate hfalse

/--
## T1 operational corollary

At confidence spend `α`, no audit-adaptive posterior can pass the margin-`γ`
gate while failing to improve by `γ`, except on an event of mass at most `α`.
-/
theorem measure_falseImprovementEvent_le
    [IsProbabilityMeasure μ]
    (E : PairedEProcess M prior G ℱ μ)
    {α : ℝ} (hα : 0 < α) (γ : ℝ) :
    μ (E.falseImprovementEvent α γ) ≤ ENNReal.ofReal α := by
  exact (measure_mono (E.falseImprovementEvent_subset_badEvent α γ)).trans
    (E.measure_badEvent_le hα)

end PairedEProcess

/-! ## Bounded fresh audits generate the pairwise e-process -/

/-- Hoeffding's sub-Gaussian parameter for a variable in `[lower, upper]`. -/
noncomputable def hoeffdingVariance (lower upper : ℝ) : ℝ≥0 :=
  (‖upper - lower‖₊ / 2) ^ 2

/-- The compensator in the exponential e-factor at betting scale `scale`. -/
noncomputable def hoeffdingVarianceRate (lower upper scale : ℝ) : ℝ :=
  (hoeffdingVariance lower upper : ℝ) * scale ^ 2 / 2

/--
The exact mathematical content of a bounded fresh paired audit.

For every policy pair and audit step, the new increment is measurable in a
current-round sigma algebra independent of the past filtration, is almost
surely bounded in a common interval, and has mean zero.  `pairedGapAdapted`
records that the empirical state visible after `n` observations is adapted.
-/
structure FreshBoundedPairedIncrements
    (M : SequentialPairedRiskModel H Ω)
    (ℱ : Filtration ℕ ‹MeasurableSpace Ω›)
    (μ : Measure Ω) (lower upper : ℝ) where
  current : H × H → ℕ → MeasurableSpace Ω
  current_le : ∀ x n, current x n ≤ ‹MeasurableSpace Ω›
  incrementStronglyMeasurable : ∀ x n,
    StronglyMeasurable[current x n] (fun ω => M.pairIncrement n ω x)
  current_indep_past : ∀ x n, Indep (current x n) (ℱ n) μ
  increment_mem_Icc : ∀ x n,
    ∀ᵐ ω ∂μ, M.pairIncrement n ω x ∈ Set.Icc lower upper
  increment_mean_zero : ∀ x n,
    μ[fun ω => M.pairIncrement n ω x] = 0
  pairedGapAdapted : ∀ x,
    StronglyAdapted ℱ (fun n ω => M.pairedGap n ω x)

namespace FreshBoundedPairedIncrements

variable {M : SequentialPairedRiskModel H Ω}
variable {ℱ : Filtration ℕ ‹MeasurableSpace Ω›}
variable {μ : Measure Ω} {lower upper : ℝ}

omit [Fintype H] in
/-- Each bounded fresh increment satisfies the conditional Hoeffding MGF bound. -/
theorem condExp_exp_pairIncrement_le
    [IsProbabilityMeasure μ]
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (x : H × H) (n : ℕ) (t : ℝ) :
    μ[fun ω => Real.exp (t * M.pairIncrement n ω x) | ℱ n] ≤ᵐ[μ]
      fun _ => Real.exp ((hoeffdingVariance lower upper : ℝ) * t ^ 2 / 2) := by
  have hincAmbient : AEMeasurable (fun ω => M.pairIncrement n ω x) μ :=
    ((A.incrementStronglyMeasurable x n).mono (A.current_le x n)).aemeasurable
  have hsubG : HasSubgaussianMGF (fun ω => M.pairIncrement n ω x)
      (hoeffdingVariance lower upper) μ :=
    hasSubgaussianMGF_of_mem_Icc_of_integral_eq_zero
      hincAmbient (A.increment_mem_Icc x n) (A.increment_mean_zero x n)
  have hexpStrong : StronglyMeasurable[A.current x n]
      (fun ω => Real.exp (t * M.pairIncrement n ω x)) := by
    have hinc := A.incrementStronglyMeasurable x n
    fun_prop
  have hindep := condExp_indep_eq (A.current_le x n) (ℱ.le n)
    hexpStrong (A.current_indep_past x n)
  filter_upwards [hindep] with ω hω
  rw [hω]
  simpa [mgf] using hsubG.mgf_le t

/-- Pairwise exponential wealth generated by the cumulative gap. -/
noncomputable def pairWealth (_A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (scale : ℝ) (x : H × H) (n : ℕ) (ω : Ω) : ℝ :=
  Real.exp
    (scale * M.cumulativeGap n ω x -
      (n : ℝ) * hoeffdingVarianceRate lower upper scale)

/-- The one-step e-factor of `pairWealth`. -/
noncomputable def pairFactor (_A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (scale : ℝ) (x : H × H) (n : ℕ) (ω : Ω) : ℝ :=
  Real.exp (-hoeffdingVarianceRate lower upper scale) *
    Real.exp (scale * M.pairIncrement n ω x)

omit [Fintype H] in
/-- Pairwise wealth starts at one. -/
@[simp] theorem pairWealth_zero
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (scale : ℝ) (x : H × H) :
    A.pairWealth scale x 0 = fun _ => 1 := by
  funext ω
  simp [pairWealth, SequentialPairedRiskModel.cumulativeGap]

omit [Fintype H] in
/-- The wealth recursion is exactly multiplicative. -/
theorem pairWealth_succ
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (scale : ℝ) (x : H × H) (n : ℕ) :
    A.pairWealth scale x (n + 1) =
      A.pairWealth scale x n * A.pairFactor scale x n := by
  funext ω
  change
    Real.exp (scale * M.cumulativeGap (n + 1) ω x -
      ((n + 1 : ℕ) : ℝ) * hoeffdingVarianceRate lower upper scale) =
    Real.exp (scale * M.cumulativeGap n ω x -
      (n : ℝ) * hoeffdingVarianceRate lower upper scale) *
      (Real.exp (-hoeffdingVarianceRate lower upper scale) *
        Real.exp (scale * M.pairIncrement n ω x))
  rw [M.cumulativeGap_succ, ← Real.exp_add, ← Real.exp_add]
  push_cast
  ring_nf

omit [Fintype H] in
/-- Pairwise wealth is adapted whenever the empirical paired gap is adapted. -/
theorem pairWealth_stronglyAdapted
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (scale : ℝ) (x : H × H) :
    StronglyAdapted ℱ (A.pairWealth scale x) := by
  intro n
  have hgap := A.pairedGapAdapted x n
  change StronglyMeasurable[ℱ n] (fun ω =>
    Real.exp (scale * ((n : ℝ) * M.pairedGap n ω x) -
      (n : ℝ) * hoeffdingVarianceRate lower upper scale))
  fun_prop

omit [Fintype H] in
/-- The one-step factor is ambient measurable. -/
theorem pairFactor_aestronglyMeasurable
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (scale : ℝ) (x : H × H) (n : ℕ) :
    AEStronglyMeasurable (A.pairFactor scale x n) μ := by
  have hinc := (A.incrementStronglyMeasurable x n).mono (A.current_le x n)
  change AEStronglyMeasurable (fun ω =>
    Real.exp (-hoeffdingVarianceRate lower upper scale) *
      Real.exp (scale * M.pairIncrement n ω x)) μ
  exact (by fun_prop)

omit [Fintype H] in
/-- A deterministic essential upper bound for every one-step factor. -/
theorem pairFactor_norm_le
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    {scale : ℝ} (hscale : 0 ≤ scale) (x : H × H) (n : ℕ) :
    ∀ᵐ ω ∂μ, ‖A.pairFactor scale x n ω‖ ≤
      Real.exp (-hoeffdingVarianceRate lower upper scale) *
        Real.exp (scale * upper) := by
  filter_upwards [A.increment_mem_Icc x n] with ω hω
  have hmul : scale * M.pairIncrement n ω x ≤ scale * upper :=
    mul_le_mul_of_nonneg_left hω.2 hscale
  have hexp := Real.exp_le_exp.mpr hmul
  change ‖Real.exp (-hoeffdingVarianceRate lower upper scale) *
      Real.exp (scale * M.pairIncrement n ω x)‖ ≤
    Real.exp (-hoeffdingVarianceRate lower upper scale) *
      Real.exp (scale * upper)
  rw [Real.norm_eq_abs, abs_of_pos (mul_pos (Real.exp_pos _) (Real.exp_pos _))]
  exact mul_le_mul_of_nonneg_left hexp (Real.exp_pos _).le

omit [Fintype H] in
/-- The conditional expectation of every fresh bounded e-factor is at most one. -/
theorem condExp_pairFactor_le_one
    [IsProbabilityMeasure μ]
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (scale : ℝ) (x : H × H) (n : ℕ) :
    μ[A.pairFactor scale x n | ℱ n] ≤ᵐ[μ] fun _ => 1 := by
  let v := hoeffdingVarianceRate lower upper scale
  let F : Ω → ℝ := fun ω => Real.exp (scale * M.pairIncrement n ω x)
  have hmgf : μ[F | ℱ n] ≤ᵐ[μ] fun _ => Real.exp v := by
    simpa [F, v, hoeffdingVarianceRate] using
      A.condExp_exp_pairIncrement_le x n scale
  have hsmul := condExp_smul (μ := μ) (Real.exp (-v)) F (ℱ n)
  have hcore :
      μ[(Real.exp (-v)) • F | ℱ n] ≤ᵐ[μ] fun _ => 1 := by
    filter_upwards [hsmul, hmgf] with ω hsmulω hmgfω
    calc
      μ[(Real.exp (-v)) • F | ℱ n] ω =
          Real.exp (-v) * μ[F | ℱ n] ω := by
            simpa [Pi.smul_apply] using hsmulω
      _ ≤ Real.exp (-v) * Real.exp v :=
        mul_le_mul_of_nonneg_left hmgfω (Real.exp_pos _).le
      _ = 1 := by rw [← Real.exp_add]; simp
  have hfactor : A.pairFactor scale x n = (Real.exp (-v)) • F := by
    funext ω
    simp [pairFactor, F, v, Pi.smul_apply]
  rw [hfactor]
  exact hcore

omit [Fintype H] in
/-- Every pairwise wealth process generated by a bounded fresh audit is integrable. -/
theorem pairWealth_integrable
    [IsProbabilityMeasure μ]
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    {scale : ℝ} (hscale : 0 ≤ scale) (x : H × H) :
    ∀ n, Integrable (A.pairWealth scale x n) μ := by
  intro n
  induction n with
  | zero =>
      simp only [A.pairWealth_zero scale x]
      exact integrable_const (1 : ℝ)
  | succ n ih =>
      rw [A.pairWealth_succ scale x n]
      exact ih.mul_bdd (A.pairFactor_aestronglyMeasurable scale x n)
        (A.pairFactor_norm_le hscale x n)

/--
Bounded, fresh, mean-zero paired increments construct the exact e-process used
by the headline T1 theorem.  No posterior appears in this construction.
-/
noncomputable def toPairedEProcess
    [IsProbabilityMeasure μ]
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (prior G : PositiveFiniteLaw H) (scale : ℝ) (hscale : 0 < scale) :
    PairedEProcess M prior G ℱ μ :=
  pairedEProcessOfPairwise M prior G scale
    (hoeffdingVarianceRate lower upper scale) hscale
    (by
      unfold hoeffdingVarianceRate
      positivity)
    (A.pairWealth scale)
    (by
      intro x n ω
      change Real.exp (scale * ((n : ℝ) * M.pairedGap n ω x) -
        (n : ℝ) * hoeffdingVarianceRate lower upper scale) =
        Real.exp (scale * (n : ℝ) * M.pairedGap n ω x -
          (n : ℝ) * hoeffdingVarianceRate lower upper scale)
      congr 1
      ring_nf)
    (fun x => supermartingale_of_multiplicative_step
      (A.pairWealth scale x) (A.pairFactor scale x)
      (A.pairWealth_stronglyAdapted scale x)
      (A.pairWealth_integrable hscale.le x)
      (fun n => by
        have hsubG : HasSubgaussianMGF (fun ω => M.pairIncrement n ω x)
            (hoeffdingVariance lower upper) μ :=
          hasSubgaussianMGF_of_mem_Icc_of_integral_eq_zero
            (((A.incrementStronglyMeasurable x n).mono
              (A.current_le x n)).aemeasurable)
            (A.increment_mem_Icc x n) (A.increment_mean_zero x n)
        have hi := hsubG.integrable_exp_mul scale
        change Integrable (fun ω =>
          Real.exp (-hoeffdingVarianceRate lower upper scale) *
            Real.exp (scale * M.pairIncrement n ω x)) μ
        exact hi.const_mul
          (Real.exp (-hoeffdingVarianceRate lower upper scale)))
      (fun n => by
        rw [← A.pairWealth_succ scale x n]
        exact A.pairWealth_integrable hscale.le x (n + 1))
      (fun n ω => (Real.exp_pos _).le)
      (A.pairWealth_succ scale x)
      (A.condExp_pairFactor_le_one scale x))

/--
## T1 from bounded fresh audits

At confidence `α`, the paired PAC--Bayes inequality holds simultaneously at
all positive audit times and for every posterior, including a posterior chosen
after observing the audit.
-/
theorem measure_badEvent_le_of_fresh_bounded
    [IsProbabilityMeasure μ]
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (prior G : PositiveFiniteLaw H) (scale : ℝ) (hscale : 0 < scale)
    {α : ℝ} (hα : 0 < α) :
    μ ((A.toPairedEProcess prior G scale hscale).badEvent α) ≤
      ENNReal.ofReal α :=
  (A.toPairedEProcess prior G scale hscale).measure_badEvent_le hα

end FreshBoundedPairedIncrements

/-- A countable family of round/grid e-processes with summable spending. -/
structure AnytimeFamily
    (M : ℕ → SequentialPairedRiskModel H Ω)
    (prior G : ℕ → PositiveFiniteLaw H)
    (ℱ : Filtration ℕ ‹MeasurableSpace Ω›)
    (μ : Measure Ω) where
  process : ∀ i, PairedEProcess (M i) (prior i) (G i) ℱ μ
  spend : ℕ → ℝ
  spend_pos : ∀ i, 0 < spend i
  spend_sum_le : ∑' i, ENNReal.ofReal (spend i) ≤ 1

namespace AnytimeFamily

variable {M : ℕ → SequentialPairedRiskModel H Ω}
variable {prior G : ℕ → PositiveFiniteLaw H}
variable {ℱ : Filtration ℕ ‹MeasurableSpace Ω›}
variable {μ : Measure Ω}

/--
## T1, countable rounds and grids

The index `i` may encode a modification round and a finite betting-grid point.
The countable spending schedule replaces a union bound over an a priori fixed
horizon.
-/
theorem measure_exists_anytime_violation_le
    [IsProbabilityMeasure μ]
    (F : AnytimeFamily M prior G ℱ μ)
    {δ : ℝ} (hδ : 0 < δ) :
    μ {ω | ∃ i n, 0 < n ∧ ∃ Q : PositiveFiniteLaw H,
      (M i).trueRegression Q (G i) >
        (M i).empiricalRegression n ω Q (G i) +
          (F.process i).radius (δ * F.spend i) n Q} ≤
      ENNReal.ofReal δ := by
  let B : ℕ → Set Ω := fun i =>
    (F.process i).badEvent (δ * F.spend i)
  have hBi : ∀ i, μ (B i) ≤ ENNReal.ofReal (δ * F.spend i) := by
    intro i
    exact (F.process i).measure_badEvent_le
      (mul_pos hδ (F.spend_pos i))
  have hsub :
      {ω | ∃ i n, 0 < n ∧ ∃ Q : PositiveFiniteLaw H,
        (M i).trueRegression Q (G i) >
          (M i).empiricalRegression n ω Q (G i) +
            (F.process i).radius (δ * F.spend i) n Q} =
      ⋃ i, B i := by
    ext ω
    simp [B, PairedEProcess.badEvent]
  rw [hsub]
  calc
    μ (⋃ i, B i) ≤ ∑' i, μ (B i) := measure_iUnion_le _
    _ ≤ ∑' i, ENNReal.ofReal (δ * F.spend i) :=
      ENNReal.tsum_le_tsum hBi
    _ = ENNReal.ofReal δ * ∑' i, ENNReal.ofReal (F.spend i) := by
      simp_rw [ENNReal.ofReal_mul hδ.le]
      rw [ENNReal.tsum_mul_left]
    _ ≤ ENNReal.ofReal δ * 1 := by
      gcongr
      exact F.spend_sum_le
    _ = ENNReal.ofReal δ := mul_one _

end AnytimeFamily

end CertifiedPolicyTheory
