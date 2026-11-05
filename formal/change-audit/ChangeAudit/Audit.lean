import ChangeAudit.Targets
import ChangeAudit.FixedHorizon

/-! Exported axiom report. Examples below are exact arithmetic fixtures and
contain no empirical task results or sampling assumptions. -/
namespace ChangeAudit

/-- A small exact Taylor certificate, matching the runtime checker's direction.
The rational threshold 320 is an example, not a frozen research allocation. -/
theorem example_log_enclosure : Real.log (320:ℝ) ≤ 6 := by
  apply log_le_of_taylor_lower (by norm_num) (by norm_num) 16
  norm_num [Finset.sum_range_succ, Nat.factorial]

theorem example_radius : conservativeRadius 6 (1/2) 48 = (1/2:ℝ) := by
  norm_num [conservativeRadius]

end ChangeAudit

#print axioms ChangeAudit.contrast_mem_Icc
#print axioms ChangeAudit.contrast_subgaussian
#print axioms ChangeAudit.FreshBounded.conditional_mgf
#print axioms ChangeAudit.FreshBounded.toConditionalMGF
#print axioms ChangeAudit.exponential_supermartingale
#print axioms MeasureTheory.Supermartingale.measure_ville_le_div
#print axioms ChangeAudit.anytime_bound
#print axioms ChangeAudit.finite_anytime_bound
#print axioms ChangeAudit.fixed_horizon_bound
#print axioms ChangeAudit.fixed_horizon_sqrt_bound
#print axioms ChangeAudit.freshOfContrasts
#print axioms ChangeAudit.prefix_target_identity
#print axioms ChangeAudit.rational_log_enclosure
#print axioms ChangeAudit.rational_family_log_enclosure
#print axioms ChangeAudit.finite_false_acceptance_bound
#print axioms ChangeAudit.finite_false_strict_acceptance_bound
#print axioms ChangeAudit.example_log_enclosure
