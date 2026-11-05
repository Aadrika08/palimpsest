import CertifiedPolicyThesis.Core

/-!
# Rewrite- and loss-functional independence

The theorem observes executable behavior through a declared loss.  It does not
inspect how a successor was produced, and it does not privilege any particular
proxy.  Rewrite labels disappear extensionally; loss functionals matter only
through their predecessor/successor contrast on the evaluation law.
-/

set_option autoImplicit false

namespace CertifiedPolicyThesis

universe u v w

/-- Metadata-rich rewrite description.  The statistical observable uses only
`predecessor` and `successor`. -/
structure Rewrite (Artifact : Type v) (Metadata : Type w) where
  predecessor : Artifact
  successor : Artifact
  metadata : Metadata

/-- Measurement induced by a rewrite. -/
def Rewrite.measuredDifference
    {Artifact : Type v} {Metadata : Type w} {Observation : Type u}
    (P : EvaluationLaw Observation) (loss : Artifact → Observation → ℝ)
    (rewrite : Rewrite Artifact Metadata) : ℝ :=
  performanceDifference P loss rewrite.successor rewrite.predecessor


/-- Explicit boundedness premise required by concentration arguments.  The
proxy itself remains arbitrary. -/
def IsBoundedLoss {Artifact : Type v} {Observation : Type u}
    (loss : Artifact → Observation → ℝ) (a b : ℝ) : Prop :=
  ∀ artifact observation, a ≤ loss artifact observation ∧ loss artifact observation ≤ b

/-- Negation preserves boundedness and the range width, with endpoints
reversed. -/
theorem negated_bounded_loss
    {Artifact : Type v} {Observation : Type u}
    (loss : Artifact → Observation → ℝ) (a b : ℝ)
    (hbounded : IsBoundedLoss loss a b) :
    IsBoundedLoss (fun artifact observation => -loss artifact observation) (-b) (-a) := by
  intro artifact observation
  have h := hbounded artifact observation
  constructor <;> linarith

/-- Positive affine rescaling transports boundedness exactly. -/
theorem affine_bounded_loss
    {Artifact : Type v} {Observation : Type u}
    (loss : Artifact → Observation → ℝ) (a b scale offset : ℝ)
    (hscale : 0 ≤ scale) (hbounded : IsBoundedLoss loss a b) :
    IsBoundedLoss
      (fun artifact observation => scale * loss artifact observation + offset)
      (scale * a + offset) (scale * b + offset) := by
  intro artifact observation
  have h := hbounded artifact observation
  constructor
  · exact add_le_add_left (mul_le_mul_of_nonneg_left h.1 hscale) offset
  · exact add_le_add_left (mul_le_mul_of_nonneg_left h.2 hscale) offset

/-- Positive affine rescaling changes only the numerical scale of a signed
performance difference; the rewrite remains untouched. -/
theorem affine_loss_performanceDifference
    {Artifact : Type v} {Observation : Type u}
    (P : EvaluationLaw Observation)
    (loss : Artifact → Observation → ℝ)
    (successor predecessor : Artifact) (scale offset : ℝ) :
    performanceDifference P
      (fun artifact observation => scale * loss artifact observation + offset)
      successor predecessor =
      scale * performanceDifference P loss successor predecessor := by
  rw [performanceDifference_eq_expect_contrast,
    performanceDifference_eq_expect_contrast]
  have hcontrast :
      (fun z =>
        (scale * loss successor z + offset) -
          (scale * loss predecessor z + offset)) =
      (fun z => scale * (loss successor z - loss predecessor z)) := by
    funext z
    ring
  rw [hcontrast, P.expect_smul]

/-- Rewrite metadata is absent from the measured quantity. -/
theorem rewrite_metadata_independence
    {Artifact : Type v} {Metadata₁ : Type w} {Metadata₂ : Type*}
    {Observation : Type u}
    (P : EvaluationLaw Observation) (loss : Artifact → Observation → ℝ)
    (predecessor successor : Artifact) (metadata₁ : Metadata₁) (metadata₂ : Metadata₂) :
    (Rewrite.mk predecessor successor metadata₁).measuredDifference P loss =
      (Rewrite.mk predecessor successor metadata₂).measuredDifference P loss := rfl

/-- Any two rewrite paths producing extensionally identical endpoints have the
same performance difference. -/
theorem rewrite_path_independence
    {Artifact : Type v} {Metadata₁ : Type w} {Metadata₂ : Type*}
    {Observation : Type u}
    (P : EvaluationLaw Observation) (loss : Artifact → Observation → ℝ)
    (rewrite₁ : Rewrite Artifact Metadata₁) (rewrite₂ : Rewrite Artifact Metadata₂)
    (hpredecessor : rewrite₁.predecessor = rewrite₂.predecessor)
    (hsuccessor : rewrite₁.successor = rewrite₂.successor) :
    rewrite₁.measuredDifference P loss = rewrite₂.measuredDifference P loss := by
  simp only [Rewrite.measuredDifference]
  rw [hpredecessor, hsuccessor]

/-- The bound is proxy-parametric: two loss functionals that induce the same
paired contrast induce exactly the same measured difference. -/
theorem loss_contrast_extensionality
    {Artifact : Type v} {Observation : Type u}
    (P : EvaluationLaw Observation)
    (loss₁ loss₂ : Artifact → Observation → ℝ)
    (successor predecessor : Artifact)
    (hcontrast : ∀ z,
      loss₁ successor z - loss₁ predecessor z =
      loss₂ successor z - loss₂ predecessor z) :
    performanceDifference P loss₁ successor predecessor =
      performanceDifference P loss₂ successor predecessor := by
  rw [performanceDifference_eq_expect_contrast,
    performanceDifference_eq_expect_contrast]
  exact P.expect_congr hcontrast

/-- A rewrite implementation function may be arbitrary.  Once its returned
executable is fixed, the measurement factors through that executable alone. -/
theorem rewrite_function_factorization
    {Artifact : Type v} {RewriteCode : Type w} {Observation : Type u}
    (applyRewrite : RewriteCode → Artifact → Artifact)
    (P : EvaluationLaw Observation) (loss : Artifact → Observation → ℝ)
    (code : RewriteCode) (predecessor : Artifact) :
    performanceDifference P loss (applyRewrite code predecessor) predecessor =
      P.expect (fun z =>
        loss (applyRewrite code predecessor) z - loss predecessor z) := by
  exact performanceDifference_eq_expect_contrast _ _ _ _

/-- Renaming or re-representing executable systems through an equivalence does
not alter the theory when the loss is transported along that equivalence. -/
theorem executable_representation_independence
    {Artifact₁ : Type v} {Artifact₂ : Type w} {Observation : Type u}
    (e : Artifact₁ ≃ Artifact₂)
    (P : EvaluationLaw Observation)
    (loss₂ : Artifact₂ → Observation → ℝ)
    (successor predecessor : Artifact₁) :
    performanceDifference P (fun h z => loss₂ (e h) z) successor predecessor =
      performanceDifference P loss₂ (e successor) (e predecessor) := rfl

end CertifiedPolicyThesis
