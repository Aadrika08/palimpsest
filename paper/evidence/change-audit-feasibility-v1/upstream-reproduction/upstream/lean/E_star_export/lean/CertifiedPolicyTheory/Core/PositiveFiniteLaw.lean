import Mathlib.Analysis.SpecialFunctions.Log.Basic
import Mathlib.Algebra.BigOperators.Field
import Mathlib.Data.Fintype.Card
import Mathlib.Tactic

/-!
# Strictly positive finite probability laws

This file is the finite, checkable probability kernel used by the paper.
The positivity assumption is deliberate: it makes every logarithm and every
change of measure total, and it isolates support management from the
statistical argument.
-/

open scoped BigOperators

namespace CertifiedPolicyTheory

universe u v

/-- A probability law with strictly positive mass on every point of a finite type. -/
structure PositiveFiniteLaw (α : Type u) [Fintype α] where
  prob : α → ℝ
  prob_pos : ∀ x, 0 < prob x
  sum_prob : ∑ x, prob x = 1

namespace PositiveFiniteLaw

variable {α : Type u} {β : Type v}
variable [Fintype α] [Fintype β]

/-- Finite expectation. -/
def expect (P : PositiveFiniteLaw α) (f : α → ℝ) : ℝ :=
  ∑ x, P.prob x * f x

@[simp] theorem expect_const (P : PositiveFiniteLaw α) (c : ℝ) :
    P.expect (fun _ => c) = c := by
  simp [expect, ← Finset.sum_mul, P.sum_prob]


theorem expect_add (P : PositiveFiniteLaw α) (f g : α → ℝ) :
    P.expect (fun x => f x + g x) = P.expect f + P.expect g := by
  simp only [expect, mul_add, Finset.sum_add_distrib]

theorem expect_sub (P : PositiveFiniteLaw α) (f g : α → ℝ) :
    P.expect (fun x => f x - g x) = P.expect f - P.expect g := by
  simp only [expect, mul_sub, Finset.sum_sub_distrib]

theorem expect_smul (P : PositiveFiniteLaw α) (c : ℝ) (f : α → ℝ) :
    P.expect (fun x => c * f x) = c * P.expect f := by
  simp only [expect]
  calc
    ∑ x, P.prob x * (c * f x) = ∑ x, c * (P.prob x * f x) := by
      apply Finset.sum_congr rfl
      intro x _
      ring
    _ = c * ∑ x, P.prob x * f x := by
      rw [Finset.mul_sum]

/-- Expectation preserves pointwise nonnegativity. -/
theorem expect_nonneg (P : PositiveFiniteLaw α) (f : α → ℝ)
    (hf : ∀ x, 0 ≤ f x) : 0 ≤ P.expect f := by
  unfold expect
  exact Finset.sum_nonneg fun x _ =>
    mul_nonneg (P.prob_pos x).le (hf x)

/-- A pointwise upper bound transports through finite expectation. -/
theorem expect_le_const (P : PositiveFiniteLaw α) (f : α → ℝ) (c : ℝ)
    (hf : ∀ x, f x ≤ c) : P.expect f ≤ c := by
  calc
    P.expect f ≤ P.expect (fun _ => c) := by
      unfold expect
      exact Finset.sum_le_sum fun x _ =>
        mul_le_mul_of_nonneg_left (hf x) (P.prob_pos x).le
    _ = c := P.expect_const c

/-- Independent product of two positive finite laws. -/
def product (P : PositiveFiniteLaw α) (G : PositiveFiniteLaw β) :
    PositiveFiniteLaw (α × β) where
  prob x := P.prob x.1 * G.prob x.2
  prob_pos x := mul_pos (P.prob_pos x.1) (G.prob_pos x.2)
  sum_prob := by
    rw [Fintype.sum_prod_type]
    calc
      ∑ a, ∑ b, P.prob a * G.prob b =
          ∑ a, P.prob a * (∑ b, G.prob b) := by
            apply Finset.sum_congr rfl
            intro a _
            rw [Finset.mul_sum]
      _ = ∑ a, P.prob a := by rw [G.sum_prob]; simp
      _ = 1 := P.sum_prob

@[simp] theorem product_prob (P : PositiveFiniteLaw α) (G : PositiveFiniteLaw β)
    (x : α × β) :
    (P.product G).prob x = P.prob x.1 * G.prob x.2 := rfl

/-- Real-valued KL divergence on a positive finite space. -/
noncomputable def kl (Q P : PositiveFiniteLaw α) : ℝ :=
  ∑ x, Q.prob x * Real.log (Q.prob x / P.prob x)

/-- The elementary tangent inequality used by finite Gibbs nonnegativity. -/
private theorem mass_sub_mass_le_klTerm (Q P : PositiveFiniteLaw α) (x : α) :
    Q.prob x - P.prob x ≤
      Q.prob x * Real.log (Q.prob x / P.prob x) := by
  have hq : 0 < Q.prob x := Q.prob_pos x
  have hp : 0 < P.prob x := P.prob_pos x
  have hratio : 0 < P.prob x / Q.prob x := div_pos hp hq
  have hlog := Real.log_le_sub_one_of_pos hratio
  have hlog_symm : Real.log (P.prob x / Q.prob x) =
      -Real.log (Q.prob x / P.prob x) := by
    rw [Real.log_div hp.ne' hq.ne', Real.log_div hq.ne' hp.ne']
    ring
  rw [hlog_symm] at hlog
  have hmul := mul_le_mul_of_nonneg_left hlog hq.le
  have hratio_mul : Q.prob x * (P.prob x / Q.prob x - 1) =
      P.prob x - Q.prob x := by
    field_simp [hq.ne']
  calc
    Q.prob x - P.prob x = -(P.prob x - Q.prob x) := by ring
    _ = -(Q.prob x * (P.prob x / Q.prob x - 1)) := by rw [hratio_mul]
    _ ≤ -(-Q.prob x * Real.log (Q.prob x / P.prob x)) := by linarith
    _ = Q.prob x * Real.log (Q.prob x / P.prob x) := by ring

/-- Gibbs inequality for strictly positive finite laws. -/
theorem kl_nonneg (Q P : PositiveFiniteLaw α) : 0 ≤ Q.kl P := by
  calc
    0 = ∑ x, (Q.prob x - P.prob x) := by
      rw [Finset.sum_sub_distrib, Q.sum_prob, P.sum_prob, sub_self]
    _ ≤ ∑ x, Q.prob x * Real.log (Q.prob x / P.prob x) :=
      Finset.sum_le_sum fun x _ => mass_sub_mass_le_klTerm Q P x
    _ = Q.kl P := rfl

/-- The exponential normalizer is strictly positive. -/
theorem expect_exp_pos (P : PositiveFiniteLaw α) (f : α → ℝ) :
    0 < P.expect (fun x => Real.exp (f x)) := by
  classical
  have hne : (Finset.univ : Finset α).Nonempty := by
    by_contra h
    have huniv : (Finset.univ : Finset α) = ∅ :=
      Finset.not_nonempty_iff_eq_empty.mp h
    have hzero_one : (0 : ℝ) = 1 := by
      simpa [huniv] using P.sum_prob
    norm_num at hzero_one
  rw [expect]
  exact Finset.sum_pos
    (fun x _ => mul_pos (P.prob_pos x) (Real.exp_pos (f x))) hne

/-- Exponential tilt of a positive finite law. -/
noncomputable def tilt (P : PositiveFiniteLaw α) (f : α → ℝ) : PositiveFiniteLaw α := by
  let Z := P.expect (fun x => Real.exp (f x))
  have hZ : 0 < Z := P.expect_exp_pos f
  exact
    { prob := fun x => P.prob x * Real.exp (f x) / Z
      prob_pos := fun x => div_pos (mul_pos (P.prob_pos x) (Real.exp_pos (f x))) hZ
      sum_prob := by
        calc
          ∑ x, P.prob x * Real.exp (f x) / Z =
              (∑ x, P.prob x * Real.exp (f x)) / Z := by
                rw [Finset.sum_div]
          _ = Z / Z := rfl
          _ = 1 := div_self hZ.ne' }

private theorem log_ratio_tilt (Q P : PositiveFiniteLaw α) (f : α → ℝ) (x : α) :
    Real.log (Q.prob x / (P.tilt f).prob x) =
      Real.log (Q.prob x / P.prob x) - f x +
        Real.log (P.expect fun y => Real.exp (f y)) := by
  have hq : Q.prob x ≠ 0 := (Q.prob_pos x).ne'
  have hp : P.prob x ≠ 0 := (P.prob_pos x).ne'
  have hexp : Real.exp (f x) ≠ 0 := (Real.exp_pos (f x)).ne'
  have hZ : P.expect (fun y => Real.exp (f y)) ≠ 0 := (P.expect_exp_pos f).ne'
  have hratio : Q.prob x / (P.tilt f).prob x =
      (Q.prob x / P.prob x) *
        (P.expect (fun y => Real.exp (f y)) / Real.exp (f x)) := by
    simp only [tilt]
    field_simp [hq, hp, hexp, hZ]
  rw [hratio, Real.log_mul (div_ne_zero hq hp) (div_ne_zero hZ hexp),
    Real.log_div hZ hexp, Real.log_exp]
  ring

/-- Exact KL identity under exponential tilting. -/
theorem kl_tilt_identity (Q P : PositiveFiniteLaw α) (f : α → ℝ) :
    Q.kl (P.tilt f) =
      Q.kl P - Q.expect f + Real.log (P.expect fun x => Real.exp (f x)) := by
  classical
  simp only [kl, expect, log_ratio_tilt]
  calc
    ∑ x, Q.prob x *
        (Real.log (Q.prob x / P.prob x) - f x +
          Real.log (∑ y, P.prob y * Real.exp (f y))) =
        ∑ x, (Q.prob x * Real.log (Q.prob x / P.prob x) -
          Q.prob x * f x +
          Q.prob x * Real.log (∑ y, P.prob y * Real.exp (f y))) := by
            apply Finset.sum_congr rfl
            intro x _
            ring
    _ = (∑ x, Q.prob x * Real.log (Q.prob x / P.prob x)) -
          (∑ x, Q.prob x * f x) +
          (∑ x, Q.prob x * Real.log (∑ y, P.prob y * Real.exp (f y))) := by
            rw [Finset.sum_add_distrib, Finset.sum_sub_distrib]
    _ = (∑ x, Q.prob x * Real.log (Q.prob x / P.prob x)) -
          (∑ x, Q.prob x * f x) +
          Real.log (∑ y, P.prob y * Real.exp (f y)) := by
            rw [← Finset.sum_mul, Q.sum_prob, one_mul]

/-- Finite Donsker--Varadhan / Gibbs change of measure. -/
theorem finite_donsker_varadhan (Q P : PositiveFiniteLaw α) (f : α → ℝ) :
    Q.expect f ≤ Q.kl P + Real.log (P.expect fun x => Real.exp (f x)) := by
  have h := Q.kl_nonneg (P.tilt f)
  rw [kl_tilt_identity] at h
  linarith

/-- Exponentiated finite Donsker--Varadhan inequality. -/
theorem exp_expect_sub_kl_le (Q P : PositiveFiniteLaw α) (f : α → ℝ) :
    Real.exp (Q.expect f - Q.kl P) ≤ P.expect fun x => Real.exp (f x) := by
  have h := finite_donsker_varadhan Q P f
  have hZ : 0 < P.expect (fun x => Real.exp (f x)) := P.expect_exp_pos f
  calc
    Real.exp (Q.expect f - Q.kl P) ≤
        Real.exp (Real.log (P.expect fun x => Real.exp (f x))) := by
          apply Real.exp_le_exp.mpr
          linarith
    _ = P.expect fun x => Real.exp (f x) := Real.exp_log hZ

/-- Fubini identity for a finite product law. -/
theorem expect_product (P : PositiveFiniteLaw α) (G : PositiveFiniteLaw β)
    (f : α × β → ℝ) :
    (P.product G).expect f =
      P.expect (fun a => G.expect (fun b => f (a, b))) := by
  classical
  rw [expect, Fintype.sum_prod_type]
  simp only [product_prob]
  rw [expect]
  apply Finset.sum_congr rfl
  intro a _
  rw [expect, Finset.mul_sum]
  apply Finset.sum_congr rfl
  intro b _
  ring

/-- A product expectation of a function of the left coordinate is unchanged. -/
theorem expect_product_left (P : PositiveFiniteLaw α) (G : PositiveFiniteLaw β)
    (f : α → ℝ) :
    (P.product G).expect (fun x => f x.1) = P.expect f := by
  classical
  rw [expect, Fintype.sum_prod_type]
  simp only [product_prob]
  calc
    ∑ a, ∑ b, P.prob a * G.prob b * f a =
        ∑ a, P.prob a * f a * (∑ b, G.prob b) := by
          apply Finset.sum_congr rfl
          intro a _
          calc
            ∑ b, P.prob a * G.prob b * f a =
                ∑ b, (P.prob a * f a) * G.prob b := by
                  apply Finset.sum_congr rfl
                  intro b _
                  ring
            _ = P.prob a * f a * (∑ b, G.prob b) := by
                  rw [Finset.mul_sum]
    _ = ∑ a, P.prob a * f a := by rw [G.sum_prob]; simp
    _ = P.expect f := rfl

/-- A product expectation of a function of the right coordinate is unchanged. -/
theorem expect_product_right (P : PositiveFiniteLaw α) (G : PositiveFiniteLaw β)
    (f : β → ℝ) :
    (P.product G).expect (fun x => f x.2) = G.expect f := by
  classical
  rw [expect, Fintype.sum_prod_type]
  simp_rw [product_prob]
  calc
    ∑ a, ∑ b, P.prob a * G.prob b * f b =
        ∑ a, P.prob a * (∑ b, G.prob b * f b) := by
          apply Finset.sum_congr rfl
          intro a _
          rw [Finset.mul_sum]
          apply Finset.sum_congr rfl
          intro b _
          ring
    _ = (∑ a, P.prob a) * (∑ b, G.prob b * f b) := by
          rw [Finset.sum_mul]
    _ = G.expect f := by rw [P.sum_prob, one_mul]; rfl

/-- The same right comparator cancels exactly from product KL. -/
theorem productKL_same_right (Q P : PositiveFiniteLaw α)
    (G : PositiveFiniteLaw β) :
    (Q.product G).kl (P.product G) = Q.kl P := by
  classical
  rw [kl, Fintype.sum_prod_type]
  have hratio : ∀ a b,
      (Q.prob a * G.prob b) / (P.prob a * G.prob b) = Q.prob a / P.prob a := by
    intro a b
    field_simp [(P.prob_pos a).ne', (G.prob_pos b).ne']
  simp_rw [product_prob, hratio]
  calc
    ∑ a, ∑ b, Q.prob a * G.prob b * Real.log (Q.prob a / P.prob a) =
        ∑ a, (∑ b, Q.prob a * G.prob b) * Real.log (Q.prob a / P.prob a) := by
          apply Finset.sum_congr rfl
          intro a _
          rw [← Finset.sum_mul]
    _ = ∑ a, Q.prob a * (∑ b, G.prob b) *
          Real.log (Q.prob a / P.prob a) := by
            apply Finset.sum_congr rfl
            intro a _
            rw [← Finset.mul_sum]
    _ = ∑ a, Q.prob a * Real.log (Q.prob a / P.prob a) := by
          rw [G.sum_prob]
          simp
    _ = Q.kl P := rfl

end PositiveFiniteLaw
end CertifiedPolicyTheory
