"""Numerical and fail-closed checks for a planning tool, not scientific outcomes."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location("change_audit_assess", Path(__file__).with_name("assess.py"))
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)
ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "paper/evidence/authority-replay-v1/summary.json"


class FeasibilityChecks(unittest.TestCase):
    def test_reference_value_and_minimum_sample_count(self):
        self.assertAlmostEqual(M.fixed_radius(1, math.exp(-1), 2), 1.0)
        n = M.required_n(3, .05, .1)
        self.assertEqual(n, 819)
        self.assertLessEqual(M.fixed_radius(3, .05, n), .1)
        self.assertGreater(M.fixed_radius(3, .05, n - 1), .1)

    def test_anytime_design_horizon_and_nonvanishing_floor(self):
        scale = M.fixed_radius(3, .05, 128)
        self.assertAlmostEqual(M.anytime_radius(3, .05, 128, scale), scale)
        self.assertGreater(M.anytime_radius(3, .05, 10**9, scale), scale/2)
        self.assertGreater(scale/2, .1)

    def test_invalid_math_inputs_refused(self):
        for k, alpha, n in ((0,.05,1),(3,0,1),(3,1,1),(3,float("nan"),1),(3,.05,0),(True,.05,1)):
            with self.assertRaises(ValueError):
                M.fixed_radius(k, alpha, n)
        for scale in (0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                M.anytime_radius(3,.05,128,scale)

    def test_real_campaign_does_not_become_a_certificate(self):
        result = M.assess(SOURCE)
        self.assertEqual(result["retained_campaign"]["descriptors"],111)
        self.assertEqual(result["retained_campaign"]["matched_execution_cost_sets"],10)
        self.assertFalse(result["admissibility"]["existing_data_eligible_for_new_population_improvement_claim"])
        self.assertFalse(result["admissibility"]["new_simulation_executed"])

    def test_inconsistent_campaign_metadata_refused(self):
        original = json.loads(SOURCE.read_text())
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            p = Path(directory)/"summary.json"
            mutations = []
            duplicate = copy.deepcopy(original)
            duplicate["rows"][1] = duplicate["rows"][0]
            mutations.append(duplicate)
            drift = copy.deepcopy(original)
            drift["rows"][0]["identity"]["commit"] = "0"*40
            mutations.append(drift)
            mismatch = copy.deepcopy(original)
            next(r for r in mismatch["rows"] if r["kind"]=="execution_overhead")["actions_sha256"]="0"*64
            mutations.append(mismatch)
            for data in mutations:
                p.write_text(json.dumps(data))
                with self.assertRaises(ValueError):
                    M.assess(p)


if __name__ == "__main__":
    unittest.main()
