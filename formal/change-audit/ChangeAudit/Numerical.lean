import ChangeAudit.Anytime
import Mathlib.Analysis.Complex.Exponential

noncomputable section
namespace ChangeAudit
open MeasureTheory ProbabilityTheory
open scoped BigOperators ENNReal NNReal
variable {Ω : Type*} [MeasurableSpace Ω]

/-- Finite positive Taylor sums lower-bound exp, so a rational inequality
against such a sum establishes an upper logarithm budget without floating
logarithms. Concrete rational certificates can be discharged by norm_num. -/
theorem log_le_of_taylor_lower {threshold q : ℝ} (ht : 0<threshold)
    (hq : 0≤q) (terms : ℕ)
    (hcertificate : threshold ≤ ∑ i ∈ Finset.range terms, q^i / (Nat.factorial i)) :
    Real.log threshold ≤ q := by
  exact (Real.log_le_iff_le_exp ht).mpr
    (hcertificate.trans (Real.sum_le_exp_of_nonneg hq terms))

def conservativeRadius (upperLog scale : ℝ) (n : ℕ) : ℝ :=
  upperLog / (scale*n) + scale/2

theorem radius_le_conservative {alpha scale upperLog : ℝ} {n : ℕ}
    (hs : 0<scale) (hn : 0<n) (hb : Real.log (1/alpha) ≤ upperLog) :
    singleRadius alpha scale n ≤ conservativeRadius upperLog scale n := by
  have hnR : (0:ℝ)<n := by exact_mod_cast hn
  dsimp [singleRadius, conservativeRadius]
  linarith [div_le_div_of_nonneg_right hb (mul_pos hs hnR).le]

/-- Passing a conservative numerical endpoint implies passing the mathematical
endpoint. This connects exact arithmetic to the already-proved probability
bound; it does not certify a runtime parser or its sampling assumptions. -/
theorem conservative_acceptance {estimate margin alpha scale upperLog : ℝ} {n : ℕ}
    (hs : 0<scale) (hn : 0<n) (hb : Real.log (1/alpha) ≤ upperLog)
    (ha : estimate + conservativeRadius upperLog scale n ≤ -margin) :
    estimate + singleRadius alpha scale n ≤ -margin := by
  have hr := radius_le_conservative hs hn hb
  linarith

/-- Exact rational metadata has its ordinary real interpretation. This theorem
allows positive rational q, lambda and a verified finite Taylor inequality. -/
theorem rational_log_enclosure (threshold q : ℚ) (terms : ℕ)
    (ht : 0<threshold) (hq : 0≤q)
    (hc : threshold ≤ ∑ i ∈ Finset.range terms, q^i / (Nat.factorial i)) :
    Real.log (threshold:ℝ) ≤ (q:ℝ) := by
  apply log_le_of_taylor_lower (by exact_mod_cast ht) (by exact_mod_cast hq) terms
  exact_mod_cast hc

/-- Connect the runtime K/alpha Taylor threshold to the finite-family theorem's
per-candidate confidence alpha/K. All inputs here are exact rationals. -/
theorem rational_family_log_enclosure (K : ℕ) (alpha q : ℚ) (terms : ℕ)
    (hK : 0<K) (ha : 0<alpha) (hq : 0≤q)
    (hc : (K:ℚ)/alpha ≤ ∑ i ∈ Finset.range terms, q^i / (Nat.factorial i)) :
    Real.log (1/((alpha:ℝ)/K)) ≤ (q:ℝ) := by
  have ht : (0:ℚ)<(K:ℚ)/alpha := div_pos (by exact_mod_cast hK) ha
  have h := rational_log_enclosure ((K:ℚ)/alpha) q terms ht hq hc
  simpa only [one_div_div, Rat.cast_div, Rat.cast_natCast] using h

end ChangeAudit
