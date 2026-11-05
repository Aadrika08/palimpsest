import ChangeAudit.Anytime

noncomputable section
namespace ChangeAudit
open MeasureTheory ProbabilityTheory
open scoped BigOperators ENNReal NNReal
variable {Ω : Type*} [MeasurableSpace Ω]

/-- Algebraic specialization at a predeclared horizon; the scale must not be
retuned after observing outcomes. -/
theorem radius_at_optimal_scale {alpha scale : ℝ} {n : ℕ}
    (hs : 0<scale) (hn : 0<n)
    (hopt : scale^2 = 2 * Real.log (1/alpha) / n) :
    singleRadius alpha scale n = scale := by
  have hnR : (0:ℝ)<n := by exact_mod_cast hn
  have hm := (eq_div_iff (ne_of_gt hnR)).mp hopt
  unfold singleRadius
  apply (eq_sub_iff_add_eq).mp
  apply (div_eq_iff (ne_of_gt (mul_pos hs hnR))).mpr
  nlinarith

/-- Every fixed-horizon violation is included in the all-prefix event for its
predeclared horizon-specific scale. -/
theorem fixed_horizon_bound {K n : ℕ} (hK : 0<K) (hn : 0<n)
    {g : Fin K → ℕ → Ω → ℝ} {scale alpha : ℝ}
    {F : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsProbabilityMeasure μ] (A : ∀j, ConditionalMGF (g j) scale F μ)
    (hs : 0<scale) (ha : 0<alpha)
    (hopt : scale^2 = 2 * Real.log (1/(alpha/K)) / n) :
    μ {ω | ∃j : Fin K, scale < meanGap (g j) n ω} ≤ ENNReal.ofReal alpha := by
  apply (measure_mono (t := {ω | ∃j : Fin K,
    ω ∈ badEvent (g j) (alpha/K) scale}) ?_).trans (finite_anytime_bound hK A hs ha)
  intro ω hω
  rcases hω with ⟨j,hj⟩
  refine ⟨j,n,hn,?_⟩
  rwa [radius_at_optimal_scale hs hn hopt]

/-- The familiar fixed-horizon square-root radius. It is not an anytime
boundary when recomputed at an audit-dependent horizon. -/
def fixedRadius (K : ℕ) (alpha : ℝ) (n : ℕ) : ℝ :=
  Real.sqrt (2 * Real.log (1/(alpha/K)) / n)

theorem fixed_horizon_sqrt_bound {K n : ℕ} (hK : 0<K) (hn : 0<n)
    {g : Fin K → ℕ → Ω → ℝ} {alpha : ℝ}
    {F : Filtration ℕ ‹MeasurableSpace Ω›} {μ : Measure Ω}
    [IsProbabilityMeasure μ]
    (A : ∀ scale : ℝ, 0<scale → ∀j, ConditionalMGF (g j) scale F μ)
    (ha : 0<alpha) (halt : alpha<1) :
    μ {ω | ∃j : Fin K, fixedRadius K alpha n < meanGap (g j) n ω} ≤
      ENNReal.ofReal alpha := by
  have hKR : (0:ℝ)<K := by exact_mod_cast hK
  have hnR : (0:ℝ)<n := by exact_mod_cast hn
  have hKone : (1:ℝ)≤K := by exact_mod_cast hK
  have hpart : 0<alpha/(K:ℝ) := div_pos ha hKR
  have hpartlt : alpha/(K:ℝ)<1 := (div_lt_one hKR).mpr (lt_of_lt_of_le halt hKone)
  have hinv : 1<1/(alpha/(K:ℝ)) := (lt_div_iff₀ hpart).mpr (by linarith)
  have hlog : 0<Real.log (1/(alpha/(K:ℝ))) := Real.log_pos hinv
  have hr : 0<2*Real.log (1/(alpha/(K:ℝ)))/(n:ℝ) := div_pos (mul_pos (by norm_num) hlog) hnR
  have hs : 0<fixedRadius K alpha n := by unfold fixedRadius; exact Real.sqrt_pos.2 hr
  have hopt : (fixedRadius K alpha n)^2 = 2*Real.log (1/(alpha/(K:ℝ)))/(n:ℝ) := by
    unfold fixedRadius
    exact Real.sq_sqrt hr.le
  exact fixed_horizon_bound hK hn (A _ hs) hs ha hopt

end ChangeAudit
