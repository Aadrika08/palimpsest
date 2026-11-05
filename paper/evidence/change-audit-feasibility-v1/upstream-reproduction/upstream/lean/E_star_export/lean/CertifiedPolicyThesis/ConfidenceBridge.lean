import CertifiedPolicyThesis.Bridge
import CertifiedPolicyTheory.Core.AnytimePACBayes

/-!
# Confidence bridge: a failure budget for the signed record

`CertifiedPolicyThesis.Bridge` identifies the signed interval *when* two
one-sided envelopes hold.  This file supplies the missing probabilistic
statement: outside an event of measure at most `δUpper + δLower`, the record's
interval contains the truth.

The composition is deliberately hypothesis-free on the analytic side.  No
independence between the two one-sided failure events is assumed, and no
measurability is required of the real-valued maps `truth`, `estimate`,
`lowerRadius`, `upperRadius`: the non-containment set is *contained* in the
union of the two bad events, so `measure_mono` and the already-proved
`signed_interval_failure_budget` suffice.

The second half instantiates this against the prior corpus's anytime layer
(`CertifiedPolicyTheory.Core.AnytimePACBayes`).  That layer's bad event
`PairedEProcess.badEvent` is *one-sided* — it collects only the violations
`trueRegression > empiricalRegression + radius` — so the two one-sided events
the composition needs are obtained by running the same construction on the model
and on the model with both risks negated.  The negated orientation is not an
extra premise: `FreshBoundedPairedIncrements.negModel` transports the bounded
fresh-increment premise, the increments negating and the bounding interval
endpoints swapping and negating.
-/

set_option autoImplicit false

open MeasureTheory
open scoped ENNReal

universe u v

namespace CertifiedPolicyThesis

/-- **C1.**  Two one-sided failure budgets pay for the signed record.  Outside
`badUpper ∪ badLower` the two signed estimation errors are controlled by the two
radii, hence `signed_interval_identification` applies pointwise; the failure set
is therefore contained in the union and is charged `δUpper + δLower`. -/
theorem contains_outside_union
    {Sample : Type u} [MeasurableSpace Sample] (μ : Measure Sample)
    (badUpper badLower : Set Sample) (δUpper δLower : ℝ≥0∞)
    (hUpper : μ badUpper ≤ δUpper) (hLower : μ badLower ≤ δLower)
    (truth estimate lowerRadius upperRadius : Sample → ℝ)
    (hUpperGood : ∀ ω, ω ∉ badUpper → truth ω - estimate ω ≤ upperRadius ω)
    (hLowerGood : ∀ ω, ω ∉ badLower → estimate ω - truth ω ≤ lowerRadius ω) :
    μ {ω | ¬ (SignedInterval.around (estimate ω) (lowerRadius ω)
        (upperRadius ω)).Contains (truth ω)} ≤ δUpper + δLower := by
  have hsubset :
      {ω | ¬ (SignedInterval.around (estimate ω) (lowerRadius ω)
          (upperRadius ω)).Contains (truth ω)} ⊆ badUpper ∪ badLower := by
    intro ω hω
    by_contra hmem
    exact hω (signed_interval_identification (truth ω) (estimate ω)
      (lowerRadius ω) (upperRadius ω)
      (hUpperGood ω fun h => hmem (Set.mem_union_left _ h))
      (hLowerGood ω fun h => hmem (Set.mem_union_right _ h)))
  exact (measure_mono hsubset).trans
    (signed_interval_failure_budget μ badUpper badLower δUpper δLower
      hUpper hLower)

end CertifiedPolicyThesis

namespace CertifiedPolicyTheory

namespace SequentialPairedRiskModel

/-- **C2.**  The sequential paired risk model with both risks negated.  This is
the sequential counterpart of `CertifiedPolicyTheory.PairedRiskModel.negModel`
(`CertifiedPolicyThesis.Bridge`); running the anytime construction on it
produces the *lower* radius of a signed record. -/
def negModel {H : Type u} {Ω : Type v} (M : SequentialPairedRiskModel H Ω) :
    SequentialPairedRiskModel H Ω where
  populationRisk := fun h => -M.populationRisk h
  empiricalRisk := fun n ω h => -M.empiricalRisk n ω h

@[simp] theorem negModel_pairedGap {H : Type u} {Ω : Type v}
    (M : SequentialPairedRiskModel H Ω) (n : ℕ) (ω : Ω) (x : H × H) :
    M.negModel.pairedGap n ω x = -M.pairedGap n ω x := by
  show (-M.populationRisk x.1 - -M.populationRisk x.2) -
      (-M.empiricalRisk n ω x.1 - -M.empiricalRisk n ω x.2) =
    -((M.populationRisk x.1 - M.populationRisk x.2) -
      (M.empiricalRisk n ω x.1 - M.empiricalRisk n ω x.2))
  ring

@[simp] theorem negModel_cumulativeGap {H : Type u} {Ω : Type v}
    (M : SequentialPairedRiskModel H Ω) (n : ℕ) (ω : Ω) (x : H × H) :
    M.negModel.cumulativeGap n ω x = -M.cumulativeGap n ω x := by
  show (n : ℝ) * M.negModel.pairedGap n ω x = -((n : ℝ) * M.pairedGap n ω x)
  rw [negModel_pairedGap]
  ring

@[simp] theorem negModel_pairIncrement {H : Type u} {Ω : Type v}
    (M : SequentialPairedRiskModel H Ω) (n : ℕ) (ω : Ω) (x : H × H) :
    M.negModel.pairIncrement n ω x = -M.pairIncrement n ω x := by
  show M.negModel.cumulativeGap (n + 1) ω x - M.negModel.cumulativeGap n ω x =
    -(M.cumulativeGap (n + 1) ω x - M.cumulativeGap n ω x)
  rw [negModel_cumulativeGap, negModel_cumulativeGap]
  ring

@[simp] theorem negModel_trueRegression {H : Type u} [Fintype H] {Ω : Type v}
    (M : SequentialPairedRiskModel H Ω) (Q G : PositiveFiniteLaw H) :
    M.negModel.trueRegression Q G = -M.trueRegression Q G := by
  show Q.expect (fun h => -M.populationRisk h)
      - G.expect (fun h => -M.populationRisk h)
    = -(Q.expect M.populationRisk - G.expect M.populationRisk)
  simp only [PositiveFiniteLaw.expect_neg]
  ring

@[simp] theorem negModel_empiricalRegression {H : Type u} [Fintype H]
    {Ω : Type v} (M : SequentialPairedRiskModel H Ω) (n : ℕ) (ω : Ω)
    (Q G : PositiveFiniteLaw H) :
    M.negModel.empiricalRegression n ω Q G =
      -M.empiricalRegression n ω Q G := by
  show Q.expect (fun h => -M.empiricalRisk n ω h)
      - G.expect (fun h => -M.empiricalRisk n ω h)
    = -(Q.expect (M.empiricalRisk n ω) - G.expect (M.empiricalRisk n ω))
  simp only [PositiveFiniteLaw.expect_neg]
  ring

end SequentialPairedRiskModel

namespace FreshBoundedPairedIncrements

/-- **C3.**  The bounded fresh-increment premise transports to the negated
model: every increment negates, so the same current-round sigma algebras,
independence, adaptedness and mean-zero facts are reused verbatim and the
bounding interval `[lower, upper]` becomes `[-upper, -lower]`. -/
def negModel {H : Type u} {Ω : Type v} [mΩ : MeasurableSpace Ω]
    {M : SequentialPairedRiskModel H Ω} {ℱ : Filtration ℕ mΩ} {μ : Measure Ω}
    {lower upper : ℝ}
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper) :
    FreshBoundedPairedIncrements M.negModel ℱ μ (-upper) (-lower) where
  current := A.current
  current_le := A.current_le
  incrementStronglyMeasurable := by
    intro x n
    have hfun : (fun ω => M.negModel.pairIncrement n ω x)
        = fun ω => -M.pairIncrement n ω x := by
      funext ω
      exact SequentialPairedRiskModel.negModel_pairIncrement M n ω x
    rw [hfun]
    exact (A.incrementStronglyMeasurable x n).neg
  current_indep_past := A.current_indep_past
  increment_mem_Icc := by
    intro x n
    filter_upwards [A.increment_mem_Icc x n] with ω hω
    rw [SequentialPairedRiskModel.negModel_pairIncrement]
    exact Set.mem_Icc.mpr ⟨by linarith [hω.2], by linarith [hω.1]⟩
  increment_mean_zero := by
    intro x n
    simp only [SequentialPairedRiskModel.negModel_pairIncrement]
    rw [integral_neg, A.increment_mean_zero x n, neg_zero]
  pairedGapAdapted := by
    intro x n
    show StronglyMeasurable[ℱ n] (fun ω => M.negModel.pairedGap n ω x)
    have hfun : (fun ω => M.negModel.pairedGap n ω x)
        = fun ω => -M.pairedGap n ω x := by
      funext ω
      exact SequentialPairedRiskModel.negModel_pairedGap M n ω x
    rw [hfun]
    exact (A.pairedGapAdapted x n).neg

end FreshBoundedPairedIncrements

namespace PairedEProcess

/-- **C4.**  Off the anytime bad event, the upper signed estimation error is at
most the anytime radius, at every positive audit time and every posterior. -/
theorem upper_error_le_radius_of_not_badEvent
    {H : Type u} [Fintype H] {Ω : Type v} [mΩ : MeasurableSpace Ω]
    {M : SequentialPairedRiskModel H Ω} {prior G : PositiveFiniteLaw H}
    {ℱ : Filtration ℕ mΩ} {μ : Measure Ω}
    (E : PairedEProcess M prior G ℱ μ) (α : ℝ) (n : ℕ) (hn : 0 < n)
    (Q : PositiveFiniteLaw H) {ω : Ω} (hω : ω ∉ E.badEvent α) :
    M.trueRegression Q G - M.empiricalRegression n ω Q G ≤ E.radius α n Q := by
  by_contra hcon
  push Not at hcon
  exact hω ⟨n, hn, Q, by linarith⟩

/-- **C5.**  Off the negated model's anytime bad event, the *lower* signed
estimation error is at most that model's anytime radius.  This is the second
one-sided event `contains_outside_union` needs, and it exists because the
anytime bad event is one-sided. -/
theorem lower_error_le_radius_of_not_badEvent
    {H : Type u} [Fintype H] {Ω : Type v} [mΩ : MeasurableSpace Ω]
    {M : SequentialPairedRiskModel H Ω} {prior G : PositiveFiniteLaw H}
    {ℱ : Filtration ℕ mΩ} {μ : Measure Ω}
    (E : PairedEProcess M.negModel prior G ℱ μ) (α : ℝ) (n : ℕ) (hn : 0 < n)
    (Q : PositiveFiniteLaw H) {ω : Ω} (hω : ω ∉ E.badEvent α) :
    M.empiricalRegression n ω Q G - M.trueRegression Q G ≤ E.radius α n Q := by
  by_contra hcon
  push Not at hcon
  refine hω ⟨n, hn, Q, ?_⟩
  simp only [SequentialPairedRiskModel.negModel_trueRegression,
    SequentialPairedRiskModel.negModel_empiricalRegression]
  linarith

end PairedEProcess

end CertifiedPolicyTheory

namespace CertifiedPolicyThesis

open CertifiedPolicyTheory

/-- **C6.**  The anytime layer discharges the signed record *with confidence*.
The premises are the prior corpus's own: bounded, fresh, mean-zero paired
increments for the model, from which the negated orientation is derived rather
than assumed.  The two radii are the anytime layer's own
`PairedEProcess.radius`, one for the model and one for its negation, and the
record fails on an event of measure at most `δUpper + δLower`. -/
theorem anytime_signed_record_confidence
    {H : Type u} [Fintype H] {Ω : Type v} [mΩ : MeasurableSpace Ω]
    {M : SequentialPairedRiskModel H Ω} {ℱ : Filtration ℕ mΩ}
    {μ : Measure Ω} [IsProbabilityMeasure μ] {lower upper : ℝ}
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (prior G : PositiveFiniteLaw H) (scale : ℝ) (hscale : 0 < scale)
    {δUpper δLower : ℝ} (hδUpper : 0 < δUpper) (hδLower : 0 < δLower)
    (n : ℕ) (hn : 0 < n) (Q : PositiveFiniteLaw H) :
    μ {ω | ¬ (SignedInterval.around
          (M.empiricalRegression n ω Q G)
          ((A.negModel.toPairedEProcess prior G scale hscale).radius δLower n Q)
          ((A.toPairedEProcess prior G scale hscale).radius
            δUpper n Q)).Contains
        (M.trueRegression Q G)} ≤
      ENNReal.ofReal δUpper + ENNReal.ofReal δLower :=
  contains_outside_union μ
    ((A.toPairedEProcess prior G scale hscale).badEvent δUpper)
    ((A.negModel.toPairedEProcess prior G scale hscale).badEvent δLower)
    (ENNReal.ofReal δUpper) (ENNReal.ofReal δLower)
    (A.measure_badEvent_le_of_fresh_bounded prior G scale hscale hδUpper)
    (A.negModel.measure_badEvent_le_of_fresh_bounded prior G scale hscale
      hδLower)
    (fun _ => M.trueRegression Q G)
    (fun ω => M.empiricalRegression n ω Q G)
    (fun _ => (A.negModel.toPairedEProcess prior G scale hscale).radius
      δLower n Q)
    (fun _ => (A.toPairedEProcess prior G scale hscale).radius δUpper n Q)
    (fun _ hω =>
      (A.toPairedEProcess prior G scale hscale).upper_error_le_radius_of_not_badEvent
        δUpper n hn Q hω)
    (fun _ hω =>
      (A.negModel.toPairedEProcess prior G scale
        hscale).lower_error_le_radius_of_not_badEvent δLower n hn Q hω)

/-- **C7.**  The anytime strengthening of `anytime_signed_record_confidence`:
the *same* failure budget covers every positive audit time and every posterior
simultaneously, including a posterior chosen after observing the audit.  This is
the form in which the anytime layer's uniformity survives the composition. -/
theorem anytime_signed_record_confidence_uniform
    {H : Type u} [Fintype H] {Ω : Type v} [mΩ : MeasurableSpace Ω]
    {M : SequentialPairedRiskModel H Ω} {ℱ : Filtration ℕ mΩ}
    {μ : Measure Ω} [IsProbabilityMeasure μ] {lower upper : ℝ}
    (A : FreshBoundedPairedIncrements M ℱ μ lower upper)
    (prior G : PositiveFiniteLaw H) (scale : ℝ) (hscale : 0 < scale)
    {δUpper δLower : ℝ} (hδUpper : 0 < δUpper) (hδLower : 0 < δLower) :
    μ {ω | ∃ n : ℕ, 0 < n ∧ ∃ Q : PositiveFiniteLaw H,
        ¬ (SignedInterval.around
            (M.empiricalRegression n ω Q G)
            ((A.negModel.toPairedEProcess prior G scale hscale).radius
              δLower n Q)
            ((A.toPairedEProcess prior G scale hscale).radius
              δUpper n Q)).Contains
          (M.trueRegression Q G)} ≤
      ENNReal.ofReal δUpper + ENNReal.ofReal δLower := by
  have hsubset :
      {ω | ∃ n : ℕ, 0 < n ∧ ∃ Q : PositiveFiniteLaw H,
        ¬ (SignedInterval.around
            (M.empiricalRegression n ω Q G)
            ((A.negModel.toPairedEProcess prior G scale hscale).radius
              δLower n Q)
            ((A.toPairedEProcess prior G scale hscale).radius
              δUpper n Q)).Contains
          (M.trueRegression Q G)} ⊆
        (A.toPairedEProcess prior G scale hscale).badEvent δUpper ∪
          (A.negModel.toPairedEProcess prior G scale hscale).badEvent δLower := by
    rintro ω ⟨n, hn, Q, hnc⟩
    by_contra hmem
    exact hnc (signed_interval_identification _ _ _ _
      ((A.toPairedEProcess prior G scale
          hscale).upper_error_le_radius_of_not_badEvent δUpper n hn Q
        fun h => hmem (Set.mem_union_left _ h))
      ((A.negModel.toPairedEProcess prior G scale
          hscale).lower_error_le_radius_of_not_badEvent δLower n hn Q
        fun h => hmem (Set.mem_union_right _ h)))
  exact (measure_mono hsubset).trans
    (signed_interval_failure_budget μ _ _ _ _
      (A.measure_badEvent_le_of_fresh_bounded prior G scale hscale hδUpper)
      (A.negModel.measure_badEvent_le_of_fresh_bounded prior G scale hscale
        hδLower))

end CertifiedPolicyThesis
