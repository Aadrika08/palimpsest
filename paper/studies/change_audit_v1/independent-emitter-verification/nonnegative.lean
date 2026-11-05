import ChangeAudit.Numerical

-- Closed numerical witness only; no sampling or runtime theorem application.
noncomputable section
namespace ChangeAudit.Generated.Certificate_2b22237ff06907372dc1da6e311bf054cf00bb1cf7049415ad9e9dafa9ba5a9d_ad50df0a26bd287adba2cc646c4ee321b7f2c7056ebc83ba30b6c3e41453601b

def protocolSha256 : String := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
def specSha256 : String := "2b22237ff06907372dc1da6e311bf054cf00bb1cf7049415ad9e9dafa9ba5a9d"
def observationsSha256 : String := "ad50df0a26bd287adba2cc646c4ee321b7f2c7056ebc83ba30b6c3e41453601b"
def referencedProofReceiptSha256 : String := "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
def familyCount : ℕ := 16
def contrastCount : ℕ := 2
def taylorTerms : ℕ := 16
def alpha : ℚ := ((1 : ℚ) / 10)
def upperLog : ℚ := ((4 : ℚ) / 1)
def scale : ℚ := ((1 : ℚ) / 2)

theorem log_budget_enclosure :
    Real.log (1 / ((alpha : ℝ) / (contrastCount : ℝ))) ≤ (upperLog : ℝ) := by
  exact ChangeAudit.rational_family_log_enclosure contrastCount alpha upperLog taylorTerms
    (by norm_num [contrastCount])
    (by norm_num [alpha])
    (by norm_num [upperLog])
    (by norm_num [contrastCount, alpha, upperLog, taylorTerms,
      Finset.sum_range_succ, Nat.factorial])

def losses_0 : List ℚ := [((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1)]
def mean_0 : ℚ := losses_0.sum / (familyCount : ℚ)

theorem losses_0_count : losses_0.length = familyCount := by
  norm_num [losses_0, familyCount]

theorem mean_0_exact : mean_0 = ((0 : ℚ) / 1) := by
  norm_num [mean_0, losses_0, familyCount]

theorem upper_0_exact :
    (mean_0 : ℝ) + ChangeAudit.conservativeRadius (upperLog : ℝ) (scale : ℝ) familyCount = (((3 : ℚ) / 4) : ℝ) := by
  norm_num [mean_0, losses_0, familyCount, upperLog, scale,
    ChangeAudit.conservativeRadius]

theorem upper_0_nonnegative : 0 ≤ (mean_0 : ℝ) + ChangeAudit.conservativeRadius (upperLog : ℝ) (scale : ℝ) familyCount := by
  rw [upper_0_exact]
  norm_num

def losses_1 : List ℚ := [((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1), ((0 : ℚ) / 1)]
def mean_1 : ℚ := losses_1.sum / (familyCount : ℚ)

theorem losses_1_count : losses_1.length = familyCount := by
  norm_num [losses_1, familyCount]

theorem mean_1_exact : mean_1 = ((0 : ℚ) / 1) := by
  norm_num [mean_1, losses_1, familyCount]

theorem upper_1_exact :
    (mean_1 : ℝ) + ChangeAudit.conservativeRadius (upperLog : ℝ) (scale : ℝ) familyCount = (((3 : ℚ) / 4) : ℝ) := by
  norm_num [mean_1, losses_1, familyCount, upperLog, scale,
    ChangeAudit.conservativeRadius]

theorem upper_1_nonnegative : 0 ≤ (mean_1 : ℝ) + ChangeAudit.conservativeRadius (upperLog : ℝ) (scale : ℝ) familyCount := by
  rw [upper_1_exact]
  norm_num

end ChangeAudit.Generated.Certificate_2b22237ff06907372dc1da6e311bf054cf00bb1cf7049415ad9e9dafa9ba5a9d_ad50df0a26bd287adba2cc646c4ee321b7f2c7056ebc83ba30b6c3e41453601b
