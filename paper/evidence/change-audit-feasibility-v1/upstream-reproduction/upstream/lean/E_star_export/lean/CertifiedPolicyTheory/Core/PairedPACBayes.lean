import CertifiedPolicyTheory.Core.PositiveFiniteLaw

/-!
# Paired PAC--Bayes with distinct comparator and reference prior

The deployed parent/comparator `G` and the PAC--Bayes reference prior `prior` are
separate objects.  The right comparator appears unchanged on both sides of
the product change of measure, so its KL contribution cancels exactly.
-/

open scoped BigOperators

namespace CertifiedPolicyTheory

universe u v

open PositiveFiniteLaw

variable {H : Type u} [Fintype H]
variable {S : Type v}

/-- Population and empirical risks for a policy family. -/
structure PairedRiskModel (H : Type u) (S : Type v) where
  populationRisk : H → ℝ
  empiricalRisk : S → H → ℝ

namespace PairedRiskModel

variable (M : PairedRiskModel H S)

/-- Population regression of candidate `Q` against deployed parent `G`. -/
def trueRegression (Q G : PositiveFiniteLaw H) : ℝ :=
  Q.expect M.populationRisk - G.expect M.populationRisk

/-- Empirical regression on audit state `s`. -/
def empiricalRegression (s : S) (Q G : PositiveFiniteLaw H) : ℝ :=
  Q.expect (M.empiricalRisk s) - G.expect (M.empiricalRisk s)

/-- Pairwise population-minus-empirical regression gap. -/
def pairedGap (s : S) (x : H × H) : ℝ :=
  (M.populationRisk x.1 - M.populationRisk x.2) -
    (M.empiricalRisk s x.1 - M.empiricalRisk s x.2)

/-- Product expectation of the paired gap equals the Gibbs regression gap. -/
theorem expect_pairedGap (s : S) (Q G : PositiveFiniteLaw H) :
    (Q.product G).expect (M.pairedGap s) =
      M.trueRegression Q G - M.empiricalRegression s Q G := by
  unfold pairedGap trueRegression empiricalRegression
  rw [PositiveFiniteLaw.expect_sub, PositiveFiniteLaw.expect_sub,
    PositiveFiniteLaw.expect_sub,
    Q.expect_product_left G M.populationRisk,
    Q.expect_product_right G M.populationRisk,
    Q.expect_product_left G (M.empiricalRisk s),
    Q.expect_product_right G (M.empiricalRisk s)]

end PairedRiskModel

/-- Paired finite Donsker--Varadhan with a distinct parent and reference prior. -/
theorem PositiveFiniteLaw.paired_donsker_varadhan
    (Q prior G : PositiveFiniteLaw H) (f : H × H → ℝ) :
    (Q.product G).expect f ≤
      Q.kl prior + Real.log ((prior.product G).expect fun x => Real.exp (f x)) := by
  have h := PositiveFiniteLaw.finite_donsker_varadhan (Q.product G) (prior.product G) f
  rw [PositiveFiniteLaw.productKL_same_right] at h
  exact h

/-- Exponentiated paired change of measure. -/
theorem PositiveFiniteLaw.exp_paired_expect_sub_kl_le
    (Q prior G : PositiveFiniteLaw H) (f : H × H → ℝ) :
    Real.exp ((Q.product G).expect f - Q.kl prior) ≤
      (prior.product G).expect fun x => Real.exp (f x) := by
  have h := PositiveFiniteLaw.exp_expect_sub_kl_le (Q.product G) (prior.product G) f
  rw [PositiveFiniteLaw.productKL_same_right] at h
  exact h

/-- A finite PAC--Bayes envelope obtained from a paired exponential moment. -/
structure PairedEnvelope (M : PairedRiskModel H S) (s : S)
    (prior G : PositiveFiniteLaw H) where
  scale : ℝ
  scale_pos : 0 < scale
  logMomentBudget : ℝ
  moment_le :
    (prior.product G).expect
      (fun x => Real.exp (scale * M.pairedGap s x)) ≤
      Real.exp logMomentBudget

namespace PairedEnvelope

variable {M : PairedRiskModel H S} {s : S}
variable {prior G : PositiveFiniteLaw H}

/-- The envelope controls true regression for every posterior simultaneously. -/
theorem trueRegression_le (E : PairedEnvelope M s prior G)
    (Q : PositiveFiniteLaw H) :
    M.trueRegression Q G ≤
      M.empiricalRegression s Q G + (Q.kl prior + E.logMomentBudget) / E.scale := by
  have hdv := PositiveFiniteLaw.paired_donsker_varadhan Q prior G
    (fun x => E.scale * M.pairedGap s x)
  have hmomentPos :
      0 < (prior.product G).expect
        (fun x => Real.exp (E.scale * M.pairedGap s x)) :=
    (prior.product G).expect_exp_pos _
  have hlog := Real.log_le_log hmomentPos E.moment_le
  rw [Real.log_exp] at hlog
  have hgap :
      (Q.product G).expect (fun x => E.scale * M.pairedGap s x) =
        E.scale * (M.trueRegression Q G - M.empiricalRegression s Q G) := by
    rw [PositiveFiniteLaw.expect_smul, M.expect_pairedGap]
  rw [hgap] at hdv
  have hmomentAdd :
      Q.kl prior + Real.log ((prior.product G).expect
        (fun x => Real.exp (E.scale * M.pairedGap s x))) ≤
        Q.kl prior + E.logMomentBudget := by
    linarith
  have hcombined :
      E.scale * (M.trueRegression Q G - M.empiricalRegression s Q G) ≤
        Q.kl prior + E.logMomentBudget := le_trans hdv hmomentAdd
  have hdiv : M.trueRegression Q G - M.empiricalRegression s Q G ≤
      (Q.kl prior + E.logMomentBudget) / E.scale := by
    apply (le_div_iff₀ E.scale_pos).2
    nlinarith
  linarith

/-- A negative certified upper endpoint implies a quantitative improvement. -/
theorem improvement_of_upperEndpoint
    (E : PairedEnvelope M s prior G) (Q : PositiveFiniteLaw H) (γ : ℝ)
    (hgate : M.empiricalRegression s Q G +
      (Q.kl prior + E.logMomentBudget) / E.scale ≤ -γ) :
    Q.expect M.populationRisk ≤ G.expect M.populationRisk - γ := by
  have hreg := E.trueRegression_le Q
  dsimp [PairedRiskModel.trueRegression] at hreg
  linarith

end PairedEnvelope

end CertifiedPolicyTheory
