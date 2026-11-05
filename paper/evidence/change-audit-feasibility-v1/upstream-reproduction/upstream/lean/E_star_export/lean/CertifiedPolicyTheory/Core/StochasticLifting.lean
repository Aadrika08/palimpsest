import CertifiedPolicyTheory.Core.AnytimePACBayes

/-!
# Stochastic-policy and autoregressive-agent lifting

The statistical theorem acts on an executable policy through the loss of one
complete audit episode.  All exogenous randomness used by an internally
stochastic policy is placed in the audit world.  The resulting lifted policy
is deterministic on that enlarged world.  The complete execution may be
autoregressive and may contain arbitrary within-episode dependence; no
independence between tokens or internal steps is assumed.

This file proves exact preservation of population risk, Gibbs regression,
static PAC--Bayes certificates, and anytime-valid T1 certificates.
-/

open scoped BigOperators ENNReal
open MeasureTheory ProbabilityTheory

namespace CertifiedPolicyTheory

universe u v w x

open PositiveFiniteLaw

variable {H : Type u} [Fintype H]
variable {X : Type v} [Fintype X]
variable {U : Type w} [Fintype U]

/-- A finite stochastic policy model.  `X` is the externally sampled task and
`U` contains all exogenous randomness used by one complete execution. -/
structure StochasticPolicyModel
    (H : Type u) (X : Type v) (U : Type w)
    [Fintype X] [Fintype U] where
  taskLaw : PositiveFiniteLaw X
  seedLaw : PositiveFiniteLaw U
  loss : H → X → U → ℝ

namespace StochasticPolicyModel

variable (M : StochasticPolicyModel H X U)

/-- The enlarged audit world containing a task and all execution randomness. -/
abbrev World (_M : StochasticPolicyModel H X U) := X × U

/-- Independent law of the enlarged audit world. -/
def worldLaw : PositiveFiniteLaw M.World :=
  M.taskLaw.product M.seedLaw

/-- Deterministic loss after exposing the exogenous seed as audit data. -/
def liftedLoss (h : H) (ω : M.World) : ℝ :=
  M.loss h ω.1 ω.2

/-- Native nested expectation of a stochastic policy. -/
def stochasticRisk (h : H) : ℝ :=
  M.taskLaw.expect (fun task =>
    M.seedLaw.expect (fun seed => M.loss h task seed))

/-- Risk of the deterministic policy on the enlarged audit world. -/
def liftedRisk (h : H) : ℝ :=
  M.worldLaw.expect (M.liftedLoss h)

omit [Fintype H] in
/-- **T2.1: risk preservation under evaluation-world lifting.** -/
@[simp] theorem liftedRisk_eq_stochasticRisk (h : H) :
    M.liftedRisk h = M.stochasticRisk h := by
  change (M.taskLaw.product M.seedLaw).expect
      (fun xu : X × U => M.loss h xu.1 xu.2) =
    M.taskLaw.expect (fun task =>
      M.seedLaw.expect (fun seed => M.loss h task seed))
  exact PositiveFiniteLaw.expect_product M.taskLaw M.seedLaw
    (fun xu : X × U => M.loss h xu.1 xu.2)

/-- A finite audit sample of enlarged worlds. -/
abbrev AuditSample (_M : StochasticPolicyModel H X U) (n : ℕ) :=
  Fin n → X × U

/-- Empirical loss of one stochastic policy on an exposed task/seed sample. -/
noncomputable def empiricalLiftedRisk {n : ℕ} (s : M.AuditSample n) (h : H) : ℝ :=
  if n = 0 then 0
  else (1 / (n : ℝ)) * ∑ i, M.liftedLoss h (s i)

/-- Static risk model consumed by the paired PAC--Bayes theorem. -/
noncomputable def pairedRiskModel (n : ℕ) : PairedRiskModel H (M.AuditSample n) where
  populationRisk := M.stochasticRisk
  empiricalRisk := fun s h => M.empiricalLiftedRisk s h

/-- Native Gibbs risk of a posterior over stochastic policies. -/
def gibbsStochasticRisk (Q : PositiveFiniteLaw H) : ℝ :=
  Q.expect M.stochasticRisk

/-- Lifted Gibbs risk is unchanged. -/
theorem gibbsLiftedRisk_eq (Q : PositiveFiniteLaw H) :
    Q.expect M.liftedRisk = M.gibbsStochasticRisk Q := by
  apply congrArg (fun f : H → ℝ => Q.expect f)
  funext h
  exact M.liftedRisk_eq_stochasticRisk h

/-- Native stochastic-policy regression of candidate `Q` against parent `G`. -/
def stochasticRegression (Q G : PositiveFiniteLaw H) : ℝ :=
  M.gibbsStochasticRisk Q - M.gibbsStochasticRisk G

/-- **T2.2: paired population regression is preserved exactly.** -/
@[simp] theorem trueRegression_eq_stochasticRegression
    (n : ℕ) (Q G : PositiveFiniteLaw H) :
    (M.pairedRiskModel n).trueRegression Q G =
      M.stochasticRegression Q G := rfl

/-- Empirical paired regression is exactly the regression computed from the
exposed task/seed audit sample. -/
theorem empiricalRegression_eq
    (n : ℕ) (s : M.AuditSample n) (Q G : PositiveFiniteLaw H) :
    (M.pairedRiskModel n).empiricalRegression s Q G =
      Q.expect (M.empiricalLiftedRisk s) -
        G.expect (M.empiricalLiftedRisk s) := rfl

/-- **T2.3: a paired PAC--Bayes envelope for the lifted deterministic model is
already an envelope for the original stochastic policies.** -/
theorem stochasticRegression_le_of_envelope
    {n : ℕ} {s : M.AuditSample n}
    {prior G : PositiveFiniteLaw H}
    (E : PairedEnvelope (M.pairedRiskModel n) s prior G)
    (Q : PositiveFiniteLaw H) :
    M.stochasticRegression Q G ≤
      (M.pairedRiskModel n).empiricalRegression s Q G +
        (Q.kl prior + E.logMomentBudget) / E.scale := by
  simpa only [trueRegression_eq_stochasticRegression] using
    E.trueRegression_le Q

/-- **T2 static transport theorem.** A certified negative upper endpoint for
an evaluation-world audit implies the same quantitative improvement for the
original stochastic/autoregressive policies. -/
theorem stochasticPolicy_certificate_implies_improvement
    {n : ℕ} {s : M.AuditSample n}
    {prior G : PositiveFiniteLaw H}
    (E : PairedEnvelope (M.pairedRiskModel n) s prior G)
    (Q : PositiveFiniteLaw H) (γ : ℝ)
    (hgate :
      (M.pairedRiskModel n).empiricalRegression s Q G +
        (Q.kl prior + E.logMomentBudget) / E.scale ≤ -γ) :
    M.gibbsStochasticRisk Q ≤ M.gibbsStochasticRisk G - γ := by
  simpa [pairedRiskModel, gibbsStochasticRisk] using
    E.improvement_of_upperEndpoint Q γ hgate

end StochasticPolicyModel

variable {Ω : Type x}

/-- A sequential stochastic policy model for the anytime theorem. -/
structure SequentialStochasticPolicyModel
    (H : Type u) (X : Type v) (U : Type w) (Ω : Type x)
    [Fintype X] [Fintype U] where
  taskLaw : PositiveFiniteLaw X
  seedLaw : PositiveFiniteLaw U
  loss : H → X → U → ℝ
  empiricalRisk : ℕ → Ω → H → ℝ

namespace SequentialStochasticPolicyModel

variable (M : SequentialStochasticPolicyModel H X U Ω)

/-- Native risk of one complete stochastic execution. -/
def stochasticRisk (h : H) : ℝ :=
  M.taskLaw.expect (fun task =>
    M.seedLaw.expect (fun seed => M.loss h task seed))

/-- Joint task/seed law of an evaluation world. -/
def worldLaw : PositiveFiniteLaw (X × U) :=
  M.taskLaw.product M.seedLaw

/-- Deterministic lifted risk on the enlarged evaluation world. -/
def liftedRisk (h : H) : ℝ :=
  M.worldLaw.expect (fun xu => M.loss h xu.1 xu.2)

omit [Fintype H] in
/-- Sequential evaluation-world lifting preserves population risk exactly. -/
@[simp] theorem liftedRisk_eq_stochasticRisk (h : H) :
    M.liftedRisk h = M.stochasticRisk h := by
  change (M.taskLaw.product M.seedLaw).expect
      (fun xu : X × U => M.loss h xu.1 xu.2) =
    M.taskLaw.expect (fun task =>
      M.seedLaw.expect (fun seed => M.loss h task seed))
  exact PositiveFiniteLaw.expect_product M.taskLaw M.seedLaw
    (fun xu : X × U => M.loss h xu.1 xu.2)

/-- Sequential paired-risk model consumed by T1. -/
def riskModel : SequentialPairedRiskModel H Ω where
  populationRisk := M.liftedRisk
  empiricalRisk := M.empiricalRisk

/-- Native stochastic Gibbs regression. -/
def stochasticRegression (Q G : PositiveFiniteLaw H) : ℝ :=
  Q.expect M.stochasticRisk - G.expect M.stochasticRisk

/-- T1's lifted population regression is the native stochastic regression. -/
@[simp] theorem riskModel_trueRegression_eq_stochasticRegression
    (Q G : PositiveFiniteLaw H) :
    M.riskModel.trueRegression Q G = M.stochasticRegression Q G := by
  unfold riskModel SequentialPairedRiskModel.trueRegression stochasticRegression
  rw [show Q.expect M.liftedRisk = Q.expect M.stochasticRisk by
        exact congrArg (fun f : H → ℝ => Q.expect f)
          (funext M.liftedRisk_eq_stochasticRisk),
      show G.expect M.liftedRisk = G.expect M.stochasticRisk by
        exact congrArg (fun f : H → ℝ => G.expect f)
          (funext M.liftedRisk_eq_stochasticRisk)]

set_option linter.unusedSectionVars false in
/-- The empirical regression is unchanged by evaluation-world lifting. -/
@[simp] theorem riskModel_empiricalRegression
    (n : ℕ) (ω : Ω) (Q G : PositiveFiniteLaw H) :
    M.riskModel.empiricalRegression n ω Q G =
      Q.expect (M.empiricalRisk n ω) - G.expect (M.empiricalRisk n ω) := rfl

/--
## T2 headline, anytime form

With the same confidence level and radius as T1, the inequality holds at every
positive audit time and for every posterior over stochastic/autoregressive
policies, including an audit-adaptive posterior.
-/
theorem ae_anytime_stochastic_pacBayes
    {prior G : PositiveFiniteLaw H}
    [mΩ : MeasurableSpace Ω] {ℱ : Filtration ℕ mΩ}
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    (E : PairedEProcess M.riskModel prior G ℱ μ)
    {α : ℝ} (hα : 0 < α) :
    μ {ω | ∀ n : ℕ, 0 < n → ∀ Q : PositiveFiniteLaw H,
      M.stochasticRegression Q G ≤
        M.riskModel.empiricalRegression n ω Q G + E.radius α n Q}ᶜ ≤
      ENNReal.ofReal α := by
  simpa only [riskModel_trueRegression_eq_stochasticRegression] using
    E.ae_anytime_paired_pacBayes hα

/-- Bad-event formulation of the anytime stochastic-policy theorem. -/
theorem measure_stochastic_badEvent_le
    {prior G : PositiveFiniteLaw H}
    [mΩ : MeasurableSpace Ω] {ℱ : Filtration ℕ mΩ}
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    (E : PairedEProcess M.riskModel prior G ℱ μ)
    {α : ℝ} (hα : 0 < α) :
    μ {ω | ∃ n : ℕ, 0 < n ∧ ∃ Q : PositiveFiniteLaw H,
      M.stochasticRegression Q G >
        M.riskModel.empiricalRegression n ω Q G + E.radius α n Q} ≤
      ENNReal.ofReal α := by
  simpa only [PairedEProcess.badEvent,
    riskModel_trueRegression_eq_stochasticRegression] using
    E.measure_badEvent_le hα

/--
## T2 operational improvement theorem

A stochastic/autoregressive policy may be selected after the audit.  The event
that it passes the empirical margin gate but fails to improve native stochastic
risk by that margin has mass at most `α`.
-/
theorem measure_false_stochastic_improvement_le
    {prior G : PositiveFiniteLaw H}
    [mΩ : MeasurableSpace Ω] {ℱ : Filtration ℕ mΩ}
    {μ : Measure Ω} [IsProbabilityMeasure μ]
    (E : PairedEProcess M.riskModel prior G ℱ μ)
    {α : ℝ} (hα : 0 < α) (γ : ℝ) :
    μ {ω | ∃ n : ℕ, 0 < n ∧ ∃ Q : PositiveFiniteLaw H,
      M.riskModel.empiricalRegression n ω Q G + E.radius α n Q ≤ -γ ∧
        M.stochasticRegression Q G > -γ} ≤
      ENNReal.ofReal α := by
  simpa only [PairedEProcess.falseImprovementEvent,
    riskModel_trueRegression_eq_stochasticRegression] using
    E.measure_falseImprovementEvent_le hα γ

end SequentialStochasticPolicyModel

/-- Countably many stochastic-policy round/grid processes inherit T1's spending law. -/
theorem measure_exists_stochastic_anytime_violation_le
    {Ω : Type x} [mΩ : MeasurableSpace Ω]
    (M : ℕ → SequentialStochasticPolicyModel H X U Ω)
    (prior G : ℕ → PositiveFiniteLaw H)
    {ℱ : Filtration ℕ mΩ} {μ : Measure Ω}
    [IsProbabilityMeasure μ]
    (F : AnytimeFamily (fun i => (M i).riskModel) prior G ℱ μ)
    {δ : ℝ} (hδ : 0 < δ) :
    μ {ω | ∃ i n, 0 < n ∧ ∃ Q : PositiveFiniteLaw H,
      (M i).stochasticRegression Q (G i) >
        (M i).riskModel.empiricalRegression n ω Q (G i) +
          (F.process i).radius (δ * F.spend i) n Q} ≤
      ENNReal.ofReal δ := by
  simpa only [SequentialStochasticPolicyModel.riskModel_trueRegression_eq_stochasticRegression]
    using F.measure_exists_anytime_violation_le hδ

end CertifiedPolicyTheory
