"""Contract and orchestration checks for the one-shot diagnosis amendment."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import diagnose_male_navigation_v2 as diagnosis
import evaluate_male_navigation_v2 as producer
import run_male_navigation_v2_diagnosis_amendment as amendment
from test_male_navigation_v2_diagnosis import BatchFixture, _sha, _write_json


class AmendmentContractTests(unittest.TestCase):
    def test_frozen_amendment_binds_unchanged_analysis_and_disclosure(self):
        value = amendment.load_amendment()

        self.assertEqual(amendment.AMENDMENT_SHA256,
                         "94dc0b7ead6942bc13c568f9d8e2c77af7604fe3fbaa5ea55b013f000933c41c")
        self.assertEqual(value["execution"]["amended_invocations_allowed"], 1)
        self.assertTrue(value["execution"]["no_third_attempt"])
        self.assertEqual(hashlib.sha256(amendment.CLARIFICATION_PATH.read_bytes()).hexdigest(),
                         "2d03e2aaedc8ada337a0b8315126eb665c8f6667273ea8306303f8bb7227f588")

    def test_runner_import_excludes_forbidden_native_stacks(self):
        command = [
            sys.executable,
            "-I",
            "-c",
            ("import sys;"
             f"sys.path[:0]=[{str(ROOT / 'src')!r},{str(ROOT / 'scripts')!r}];"
             "import run_male_navigation_v2_diagnosis_amendment;"
             "assert 'torch' not in sys.modules and 'mujoco' not in sys.modules"),
        ]
        subprocess.run(command, check=True, cwd=ROOT, timeout=15)

    def test_real_producer_string_survives_owner_payload_and_admission(self):
        class Writer:
            def tick(self, episode, tick, **arrays):
                return None

        class Policy:
            def act(self, observation):
                return np.array([0., 0.], dtype=np.float32)

        class Engine:
            writer = Writer()
            policy = Policy()
            teacher = None
            env = object()
            total_tick = 0
            phase = "paused"

            def public_state(self):
                return {"phase": self.phase, "last_outcome": {"reason": "goal"},
                        "total_tick": self.total_tick, "episode": 0}

        class Probe:
            def begin(self, tick):
                return None

            def end(self):
                return {"callback_count": 1, "coverage_passed": True, "coverage_errors": []}

        engine = Engine()
        result = {"rows": [], "numeric_admission": {"bytes_per_tick": 1024},
                  "contact_ownership": {}, "contact_incidence": {}}

        def command(current, identifier, action):
            current.policy.act({})
            current.writer.tick(0, 0, action=np.array([.2, .1], dtype=np.float32))
            current.total_tick = 1
            current.phase = "terminated"

        sample = {"pose": [0., 0., 0.], "time_s": 0.,
                  "position_xyz": [0., 0., 0.], "quaternion": [1., 0., 0., 0.]}
        with (patch.object(producer.common, "command", side_effect=command),
              patch.object(producer.common, "input_row", return_value={}),
              patch.object(producer.common, "input_hashes", return_value={"input": "a", "features": "b"}),
              patch.object(producer, "native_sample", return_value=sample),
              patch.object(producer, "bind_interval", return_value={}),
              patch.object(producer.common.body, "contact_arrays", return_value={}),
              patch.object(producer.contacts, "row_contacts", return_value=[]),
              patch.object(producer.contacts, "add_incidence", return_value=None)):
            outcome = producer.run_episode(engine, Probe(), result, time.monotonic() + 5,
                                           Path("unused"), object())

        case = {"id": "dev-3110-seed-10-old-corpus", "scene_seed": 3110,
                "training_seed": 10, "arm": "old-corpus", "ticks": 1, "outcome": "goal"}
        result.update(status="completed-recording", case={key: case[key] for key in
                      ("id", "scene_seed", "training_seed", "arm")}, outcome=outcome)
        decoded = json.loads(producer.owner_payload(result))

        self.assertIs(type(outcome), str)
        self.assertEqual(amendment.admit_owner_result(decoded, case), "goal")

    def test_owner_result_rejects_object_missing_invalid_and_mismatch(self):
        case = {"id": "dev-3110-seed-10-old-corpus", "scene_seed": 3110,
                "training_seed": 10, "arm": "old-corpus", "ticks": 2, "outcome": "goal"}
        valid = {"status": "completed-recording", "executed_ticks": 2, "outcome": "goal",
                 "case": {key: case[key] for key in ("id", "scene_seed", "training_seed", "arm")}}
        variants = [
            ({**valid, "outcome": {"reason": "goal"}}, "string"),
            ({key: value for key, value in valid.items() if key != "outcome"}, "missing"),
            ({**valid, "outcome": "not-natural"}, "invalid"),
            ({**valid, "outcome": "stalled"}, "differs"),
        ]
        for value, message in variants:
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    amendment.admit_owner_result(value, case)

    def test_ledger_paths_reject_heldout_before_file_access(self):
        protocol = diagnosis.load_protocol()
        ledger = {f"{protocol['input']['run_root_relative']}/dev-3120-seed-10-old-corpus/result.json":
                  {"bytes": 1, "sha256": "a" * 64}}

        with self.assertRaisesRegex(ValueError, "held-out"):
            amendment.validate_ledger_paths(ledger, protocol, amendment.load_amendment())


class AmendmentOrchestrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.fixture = BatchFixture(self.root)
        self.contract = amendment.load_amendment()

    def _mutate_last_outcome(self, value):
        case = self.fixture.protocol["cases"][-1]
        path = self.fixture.run_root / case["id"] / "result.json"
        result = json.loads(path.read_text())
        result["outcome"] = value
        _write_json(path, result)
        relative = path.relative_to(self.fixture.producer).as_posix()
        self.fixture.ledger[relative] = {"bytes": path.stat().st_size, "sha256": _sha(path)}
        self.fixture.index["copied_root_raw_files"] = self.fixture.ledger
        self.fixture.index["reference_summary"]["copied_root_raw_ledger_bytes"] = sum(
            item["bytes"] for item in self.fixture.ledger.values())
        _write_json(self.fixture.index_path, self.fixture.index)
        self.fixture.protocol["input"]["expected_ledger_bytes"] = sum(
            item["bytes"] for item in self.fixture.ledger.values())
        self.fixture.protocol["input"]["development_index_sha256"] = _sha(self.fixture.index_path)

    def test_all_owner_results_prevalidate_before_trajectory_decode(self):
        self._mutate_last_outcome({"reason": "stalled"})
        admit = amendment.admit_owner_result
        visited = []

        def track(result, case):
            visited.append(case["id"])
            return admit(result, case)

        with patch.object(diagnosis, "_run_rows") as decode, \
                patch.object(amendment, "admit_owner_result", side_effect=track):
            with self.assertRaisesRegex(ValueError, "string"):
                amendment.prevalidate_owner_results(
                    self.fixture.producer,
                    self.fixture.index_path,
                    self.fixture.protocol,
                    self.contract,
                    deadline=time.monotonic() + 10,
                )
        decode.assert_not_called()
        self.assertEqual(visited, [case["id"] for case in self.fixture.protocol["cases"]])

    def test_successful_synthetic_amendment_publishes_receipt(self):
        with patch.object(amendment, "ROOT", self.root):
            output = self.root / self.contract["execution"]["fresh_output_relative"]
            report = amendment.execute_amendment(
                self.fixture.producer,
                self.fixture.index_path,
                output,
                self.fixture.protocol,
                self.contract,
                amendment.AMENDMENT_PATH.read_bytes(),
                amendment.CLARIFICATION_PATH.read_bytes(),
            )

        receipt = json.loads((output / "amendment-execution.json").read_text())
        self.assertEqual(report["status"], "completed-read-only-diagnosis")
        self.assertEqual(receipt["status"], "completed-amended-diagnosis")
        self.assertEqual(receipt["prevalidation"]["owner_results"], 24)
        self.assertFalse(receipt["r3_complete"])
        self.assertEqual(receipt["qualification_claims"], [])

    def test_prevalidation_failure_retains_evidence_and_never_calls_analyzer(self):
        self._mutate_last_outcome(None)
        with patch.object(amendment, "ROOT", self.root), patch.object(diagnosis, "analyze") as execute:
            output = self.root / self.contract["execution"]["fresh_output_relative"]
            with self.assertRaisesRegex(ValueError, "string"):
                amendment.execute_amendment(
                    self.fixture.producer,
                    self.fixture.index_path,
                    output,
                    self.fixture.protocol,
                    self.contract,
                    amendment.AMENDMENT_PATH.read_bytes(),
                    amendment.CLARIFICATION_PATH.read_bytes(),
                )

        execute.assert_not_called()
        failure = json.loads((output / "amendment-failure.json").read_text())
        self.assertEqual(failure["status"], "failed-amended-diagnosis")
        self.assertFalse((output / "report.json").exists())

    def test_completion_receipt_fault_leaves_only_failure_evidence(self):
        write = diagnosis._write_output

        def fail_after_receipt_rename(output, name, payload, maximum):
            write(output, name, payload, maximum)
            if name == "amendment-execution.json":
                raise OSError("authored directory fsync failure")

        with patch.object(amendment, "ROOT", self.root), \
                patch.object(diagnosis, "_write_output", side_effect=fail_after_receipt_rename):
            output = self.root / self.contract["execution"]["fresh_output_relative"]
            with self.assertRaisesRegex(OSError, "authored directory fsync failure"):
                amendment.execute_amendment(
                    self.fixture.producer,
                    self.fixture.index_path,
                    output,
                    self.fixture.protocol,
                    self.contract,
                    amendment.AMENDMENT_PATH.read_bytes(),
                    amendment.CLARIFICATION_PATH.read_bytes(),
                )

        self.assertFalse((output / "report.json").exists())
        self.assertFalse((output / "amendment-execution.json").exists())
        failure = json.loads((output / "amendment-failure.json").read_text())
        self.assertEqual(failure["status"], "failed-amended-diagnosis")


if __name__ == "__main__":
    unittest.main()
