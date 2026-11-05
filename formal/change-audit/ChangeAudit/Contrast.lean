import Mathlib.Probability.Moments.SubGaussian

/-!
Whole-scenario contrasts. Neither finite catalog provenance nor a bounded
contrast establishes a probability sampling law. Each position may have its
own deterministic mean. The conditional-MGF interface later also permits
predictable means; its target is the sum of those means, not a fixed iid risk.
-/
noncomputable section
namespace ChangeAudit
open MeasureTheory ProbabilityTheory

/-- Difference of losses, with candidate first: negative means improvement. -/
def contrast (candidate baseline : ℝ) : ℝ := candidate - baseline

theorem contrast_mem_Icc {candidate baseline : ℝ}
    (hc : candidate ∈ Set.Icc 0 1) (hb : baseline ∈ Set.Icc 0 1) :
    contrast candidate baseline ∈ Set.Icc (-1) 1 := by
  constructor <;> simp only [contrast] <;> linarith [hc.1, hc.2, hb.1, hb.2]

/-- Centering retains width 2; the endpoints depend on the position's mean. -/
theorem centered_contrast_mem_Icc {d m : ℝ} (hd : d ∈ Set.Icc (-1) 1) :
    m - d ∈ Set.Icc (m - 1) (m + 1) := by
  constructor <;> linarith [hd.1, hd.2]

/-- Mean-centered bounded contrasts have sub-Gaussian parameter 1.
This is an unconditional one-position lemma, not an independence claim. -/
theorem contrast_subgaussian {Ω : Type*} [MeasurableSpace Ω]
    (μ : Measure Ω) [IsProbabilityMeasure μ] (D : Ω → ℝ)
    (hm : AEMeasurable D μ) (hb : ∀ᵐ ω ∂μ, D ω ∈ Set.Icc (-1) 1) :
    HasSubgaussianMGF (fun ω => D ω - μ[D]) 1 μ := by
  have h := hasSubgaussianMGF_of_mem_Icc hm hb
  norm_num at h ⊢
  exact h

end ChangeAudit
