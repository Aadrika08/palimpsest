"""Planning-only change-audit feasibility; never runs policies or certifies old data."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

K = 3
ALPHA = 0.05
HORIZON = 128
CHECKPOINTS = (32, 64, 128, 512)
SOURCE_COMMIT = "cc57edf9f70323926237d887d766627d8c9cdd42"


def validate(k: int, alpha: float, n: int) -> None:
    if type(k) is not int or k < 1 or type(n) is not int or n < 1:
        raise ValueError("positive integer candidate and whole-scenario counts required")
    if not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError("alpha must be finite and between zero and one")


def fixed_radius(k: int, alpha: float, n: int) -> float:
    """One-sided simultaneous finite-candidate Hoeffding, contrasts in [-1,1]."""
    validate(k, alpha, n)
    return math.sqrt(2 * math.log(k / alpha) / n)


def anytime_radius(k: int, alpha: float, n: int, scale: float) -> float:
    """Fixed pre-audit betting scale, Ville+finite union; not a Lean instantiation."""
    validate(k, alpha, n)
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError("positive finite predeclared scale required")
    return math.log(k / alpha) / (scale * n) + scale / 2


def required_n(k: int, alpha: float, radius: float) -> int:
    validate(k, alpha, 1)
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("positive finite target radius required")
    return math.ceil(2 * math.log(k / alpha) / radius**2)


def assess(summary: Path) -> dict:
    raw = summary.read_bytes()
    data = json.loads(raw)
    if data["identity"]["commit"] != SOURCE_COMMIT:
        raise ValueError("unexpected frozen campaign source")
    rows = data["rows"]
    if len(rows) != data["declared_units"]:
        raise ValueError("campaign denominator mismatch")
    if len({r["unit_id"] for r in rows}) != len(rows):
        raise ValueError("duplicate campaign unit")
    if any(r["identity"] != data["identity"] for r in rows):
        raise ValueError("row identity drift")
    kinds = Counter(r["kind"] for r in rows)
    conditions = [r for r in rows if r["kind"] == "execution_overhead"]
    groups = {}
    for row in conditions:
        group = groups.setdefault(row["seed"], {})
        if row["condition"] in group:
            raise ValueError("duplicate matched condition")
        group[row["condition"]] = row
    for group in groups.values():
        if len(group) != 4 or any(r["status"] != "completed" for r in group.values()):
            raise ValueError("incomplete matched execution-cost group")
        if len({r["actions_sha256"] for r in group.values()}) != 1:
            raise ValueError("matched actions differ")
        if len({r["final_state_sha256"] for r in group.values()}) != 1:
            raise ValueError("matched normalized state differs")
    scale = fixed_radius(K, ALPHA, HORIZON)
    return {
        "schema_version": 1,
        "scope": "Planning arithmetic and compact recorded-metadata consistency; no new task execution or statistical certificate.",
        "source": {"path": str(summary), "sha256": hashlib.sha256(raw).hexdigest(),
                   "runtime_commit": SOURCE_COMMIT, "protocol_sha256": data["identity"]["protocol_sha256"]},
        "retained_campaign": {"descriptors": len(rows), "statuses": dict(Counter(r["status"] for r in rows)),
                              "units_by_kind": dict(kinds), "matched_execution_cost_sets": len(groups)},
        "admissibility": {
            "existing_data_eligible_for_new_population_improvement_claim": False,
            "reason": "Selected engineering seeds and repeated ticks are not fresh independent draws from a declared task distribution. Continuation/replay agreement measures identity, not task loss.",
            "new_simulation_executed": False, "lean_certified": False,
            "source_binding_check_scope": "Compact row identity and recorded action/normalized-state digests only; no new raw-runtime validation."
        },
        "planning": {
            "candidates_excluding_fixed_baseline": K, "familywise_one_sided_alpha": ALPHA,
            "individual_loss_range": [0, 1], "contrast_range": [-1, 1],
            "scale_fixed_before_audit_at_design_horizon": HORIZON, "scale": scale,
            "formulas": {
                "fixed": "sqrt(2*log(K/alpha)/n)",
                "anytime_fixed_scale": "log(K/alpha)/(lambda*n)+lambda/2",
                "assumptions": "Fixed candidate family and baseline; fixed target distribution and bounded whole-scenario loss; fresh independent scenario draws (or validated conditional MGF); no audit-driven prior/family/scale change."
            },
            "radii": [{"independent_scenarios": n, "fixed_horizon": fixed_radius(K, ALPHA, n),
                       "anytime_fixed_scale": anytime_radius(K, ALPHA, n, scale)}
                      for n in (10,) + CHECKPOINTS],
            "fixed_horizon_counts_for_target_radius": {
                str(r): required_n(K, ALPHA, r) for r in (0.2, 0.1, 0.05)},
            "interpretation": "These are worst-case confidence radii, not observed effects, power calculations, or guarantees of certification. Improvement requires an observed upper endpoint strictly below zero. Two-sided intervals must split alpha between tails. The fixed-horizon radius is not valid for arbitrary early stopping.",
            "decision": "Conditional go for a new small plumbing pilot after freezing actual policy adapters and the sampling/asset path; no-go for claiming certified improvement from existing campaign or running a large certification campaign now."
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = assess(args.summary)
    with args.output.open("x") as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps({"output": str(args.output), "admissible_for_improvement": False,
                      "matched_execution_cost_sets": result["retained_campaign"]["matched_execution_cost_sets"],
                      "planning": result["planning"]["fixed_horizon_counts_for_target_radius"]}))


if __name__ == "__main__":
    main()
