/-
Copyright (c) 2026 Dhruv Gupta. All rights reserved.
Released under Apache 2.0 license as described in the file LICENSE.
Authors: Dhruv Gupta
-/
import Mathlib.Probability.Martingale.OptionalStopping

/-!
# Ville's maximal inequality for nonnegative supermartingales

For a nonnegative supermartingale `f` (discrete time) and `ε > 0`:

  `ε • μ {ω | ∃ k, ε ≤ f k ω} ≤ ENNReal.ofReal (∫ ω, f 0 ω ∂μ)`

i.e. `P(sup_k f k ≥ ε) ≤ E[f 0] / ε` — the anytime-valid guarantee behind every
betting/Kelly e-process ("Ville's inequality", Ville 1939).

Mathlib carries the submartingale side (`MeasureTheory.maximal_ineq`, Doob); this file
derives the supermartingale side from the optional stopping theorem
(`Submartingale.expected_stoppedValue_mono`, applied to `-f`) and the hitting-time API:

1. (horizon `n`) Let `τ` be the first hitting time of `[ε, ∞)` before `n`. Optional
   stopping gives `∫ stoppedValue f τ ≤ ∫ f 0`; on the event that `[ε,∞)` is reached by
   time `n` the stopped value is `≥ ε` (`stoppedValue_hittingBtwn_mem`), and it is `≥ 0`
   elsewhere, so `ε • μ(reach by n) ≤ ENNReal.ofReal (∫ f 0)`.
2. (`n → ∞`) The reach-by-`n` events increase to the reach event; conclude by
   `tendsto_measure_iUnion_atTop`.

Downstream (design-lab): this is the kernel-verified guarantee that the metis
`EProcess` gate cites in prose (Metis/Gates/EProcess.lean §19) — the mixture wealth
`E_t = ∏(1+λ·d_s)` is a nonnegative supermartingale with `E_0 = 1` under H0, so
`P(∃t : E_t ≥ 1/δ) ≤ δ`. The bridge from this abstract statement to the dyadic
executable engine (carrier-law semantics) is a separate, scheduled obligation.
-/

open MeasureTheory Filter Set
open scoped ENNReal NNReal ProbabilityTheory Topology

namespace MeasureTheory

variable {Ω : Type*} {m0 : MeasurableSpace Ω} {μ : Measure Ω} {𝒢 : Filtration ℕ m0}
  {f : ℕ → Ω → ℝ}

/-- The event that an adapted process reaches level `c` by time `n` is measurable. -/
lemma measurableSet_exists_le_reach (hf : Adapted 𝒢 f) (c : ℝ) (n : ℕ) :
    MeasurableSet {ω | ∃ k ≤ n, c ≤ f k ω} := by
  have h : {ω | ∃ k ≤ n, c ≤ f k ω} = ⋃ k, ⋃ _ : k ≤ n, {ω | c ≤ f k ω} := by
    ext ω; simp
  rw [h]
  exact MeasurableSet.iUnion fun k => MeasurableSet.iUnion fun _ =>
    measurableSet_le measurable_const ((hf k).le (𝒢.le k))

/-- Finite-horizon Ville inequality: for a nonnegative supermartingale `f`,
`ε • μ {∃ k ≤ n, ε ≤ f k} ≤ ENNReal.ofReal (∫ f 0)`. -/
theorem Supermartingale.smul_measure_reach_le [IsFiniteMeasure μ]
    (hf : Supermartingale f 𝒢 μ) (hnonneg : 0 ≤ f) {ε : ℝ≥0} (n : ℕ) :
    ε • μ {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω} ≤ ENNReal.ofReal (∫ ω, f 0 ω ∂μ) := by
  classical
  set τ : Ω → ℕ∞ := fun ω => ((hittingBtwn f {y : ℝ | (ε : ℝ) ≤ y} 0 n ω : ℕ) : ℕ∞)
  have hτ_st : IsStoppingTime 𝒢 τ :=
    hf.stronglyAdapted.adapted.isStoppingTime_hittingBtwn measurableSet_Ici
  have hτ_le : ∀ ω, τ ω ≤ (n : ℕ∞) := fun ω => by
    show ((hittingBtwn f {y : ℝ | (ε : ℝ) ≤ y} 0 n ω : ℕ) : ℕ∞) ≤ (n : ℕ∞)
    have hh : hittingBtwn f {y : ℝ | (ε : ℝ) ≤ y} 0 n ω ≤ n := hittingBtwn_le ω
    exact_mod_cast hh
  -- integrability of the stopped value, via the negated submartingale
  have hint : Integrable (stoppedValue f τ) μ := by
    have h := hf.neg.integrable_stoppedValue hτ_st hτ_le
    have heq : stoppedValue (-f) τ = -(stoppedValue f τ) := rfl
    rw [heq] at h
    exact integrable_neg_iff.mp h
  -- optional stopping: ∫ stoppedValue f τ ≤ ∫ f 0
  have hOS : ∫ ω, stoppedValue f τ ω ∂μ ≤ ∫ ω, f 0 ω ∂μ := by
    have h := hf.neg.expected_stoppedValue_mono (isStoppingTime_const 𝒢 0) hτ_st
      (fun ω => by
        show ((0 : ℕ) : ℕ∞) ≤ ((hittingBtwn f {y : ℝ | (ε : ℝ) ≤ y} 0 n ω : ℕ) : ℕ∞)
        exact_mod_cast Nat.zero_le _) hτ_le
    simp only [stoppedValue_const] at h
    have e1 : ∫ ω, (-f) 0 ω ∂μ = -∫ ω, f 0 ω ∂μ := integral_neg _
    have e2 : ∫ ω, stoppedValue (-f) τ ω ∂μ = -∫ ω, stoppedValue f τ ω ∂μ := integral_neg _
    rw [e1, e2] at h
    linarith
  -- on the reach event the stopped value is ≥ ε
  have hval : ∀ ω ∈ {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω}, (ε : ℝ) ≤ stoppedValue f τ ω := by
    intro ω hω
    obtain ⟨k, hk, hfk⟩ := hω
    exact stoppedValue_hittingBtwn_mem ⟨k, ⟨Nat.zero_le _, hk⟩, hfk⟩
  have hAmeas : MeasurableSet {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω} :=
    measurableSet_exists_le_reach hf.stronglyAdapted.adapted _ n
  have hsv_nonneg : ∀ ω, 0 ≤ stoppedValue f τ ω := fun ω => hnonneg _ ω
  have hchain : (ε : ℝ) * (μ {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω}).toReal ≤ ∫ ω, f 0 ω ∂μ :=
    calc (ε : ℝ) * (μ {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω}).toReal
        ≤ ∫ ω in {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω}, stoppedValue f τ ω ∂μ :=
          setIntegral_ge_of_const_le_real hAmeas (measure_ne_top _ _) hval hint.integrableOn
      _ ≤ ∫ ω, stoppedValue f τ ω ∂μ :=
          setIntegral_le_integral hint (Eventually.of_forall hsv_nonneg)
      _ ≤ ∫ ω, f 0 ω ∂μ := hOS
  rw [ENNReal.le_ofReal_iff_toReal_le, ENNReal.toReal_smul]
  · exact hchain
  · exact ENNReal.mul_ne_top (by simp) (measure_ne_top _ _)
  · exact le_trans (mul_nonneg ε.coe_nonneg ENNReal.toReal_nonneg) hchain

/-- **Ville's inequality**: for a nonnegative supermartingale `f`,
`ε • μ {ω | ∃ k, ε ≤ f k ω} ≤ ENNReal.ofReal (∫ f 0)` — the probability that the
process EVER reaches `ε` is at most `E[f 0]/ε`, uniformly over all (stopping) times. -/
theorem Supermartingale.smul_measure_ville_le [IsFiniteMeasure μ]
    (hf : Supermartingale f 𝒢 μ) (hnonneg : 0 ≤ f) (ε : ℝ≥0) :
    ε • μ {ω | ∃ k, (ε : ℝ) ≤ f k ω} ≤ ENNReal.ofReal (∫ ω, f 0 ω ∂μ) := by
  have hunion : {ω | ∃ k, (ε : ℝ) ≤ f k ω} = ⋃ n, {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω} := by
    ext ω
    simp only [Set.mem_setOf_eq, Set.mem_iUnion]
    exact ⟨fun ⟨k, h⟩ => ⟨k, k, le_rfl, h⟩, fun ⟨n, k, _, h⟩ => ⟨k, h⟩⟩
  have hmono : Monotone fun n => {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω} := by
    intro a b hab ω hω
    obtain ⟨k, hk, h⟩ := hω
    exact ⟨k, hk.trans hab, h⟩
  rw [hunion, ENNReal.smul_def]
  have htend : Tendsto (fun n => (ε : ℝ≥0∞) * μ {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω}) atTop
      (𝓝 ((ε : ℝ≥0∞) * μ (⋃ n, {ω | ∃ k ≤ n, (ε : ℝ) ≤ f k ω}))) :=
    ENNReal.Tendsto.const_mul (tendsto_measure_iUnion_atTop hmono)
      (Or.inr ENNReal.coe_ne_top)
  refine le_of_tendsto' htend fun n => ?_
  simpa [ENNReal.smul_def] using hf.smul_measure_reach_le hnonneg n

/-- Ville's inequality, division form: `μ {∃ k, ε ≤ f k} ≤ ENNReal.ofReal (∫ f 0) / ε`. -/
theorem Supermartingale.measure_ville_le_div [IsFiniteMeasure μ]
    (hf : Supermartingale f 𝒢 μ) (hnonneg : 0 ≤ f) {ε : ℝ≥0} (hε : ε ≠ 0) :
    μ {ω | ∃ k, (ε : ℝ) ≤ f k ω} ≤ ENNReal.ofReal (∫ ω, f 0 ω ∂μ) / ε := by
  rw [ENNReal.le_div_iff_mul_le (Or.inl (by exact_mod_cast hε))
    (Or.inl ENNReal.coe_ne_top), mul_comm]
  simpa [ENNReal.smul_def] using hf.smul_measure_ville_le hnonneg ε

end MeasureTheory
