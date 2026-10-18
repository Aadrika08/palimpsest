"""Synthetic checks for the read-only navigation-v2 diagnosis."""
import ast
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import diagnose_male_navigation_v2 as diagnosis


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True, allow_nan=False) + "\n")


def _sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class BatchFixture:
    def __init__(self, root):
        self.root = Path(root)
        self.producer = self.root / "producer"
        self.run_root = self.producer / "runs/m7-navigation-development-v2-e3f9a47-v1"
        self.protocol = json.loads((ROOT / "docs/plans/m7-navigation-v2-failure-diagnosis-v1.json").read_text())
        self.protocol["input"]["run_root_relative"] = "runs/m7-navigation-development-v2-e3f9a47-v1"
        self.protocol["cases"] = [{**case, "ticks": 2} for case in self.protocol["cases"]]
        self.protocol["input"]["expected_numeric_ticks"] = 48
        self.protocol["input"]["expected_events"] = 48
        self.ledger = {}
        for case in self.protocol["cases"]:
            self._run(case)
        self.protocol["input"]["expected_ledger_files"] = len(self.ledger)
        self.protocol["input"]["expected_ledger_bytes"] = sum(item["bytes"] for item in self.ledger.values())
        self.index = {
            "status": "completed-development-negative-gate",
            "producer_commit": self.protocol["input"]["producer_commit"],
            "output_root": str(self.run_root),
            "numeric_ticks": 48,
            "events": 48,
            "initial_snapshots": 24,
            "held_out_status": "locked_pending_separate_review",
            "cases": [{**case, "controller": "male-original", "status": "completed-recording", "variant": "original"}
                      for case in self.protocol["cases"]],
            "copied_root_raw_files_base": str(self.producer),
            "copied_root_raw_files": self.ledger,
            "reference_summary": {
                "copied_root_raw_ledger_entries": len(self.ledger),
                "copied_root_raw_ledger_bytes": sum(item["bytes"] for item in self.ledger.values()),
            },
            "qualification_claims": [],
        }
        self.index_path = self.root / "index.json"
        _write_json(self.index_path, self.index)
        self.protocol["input"]["development_index_path"] = "index.json"
        self.protocol["input"]["development_index_sha256"] = _sha(self.index_path)

    def _record(self, path):
        relative = path.relative_to(self.producer).as_posix()
        self.ledger[relative] = {"bytes": path.stat().st_size, "sha256": _sha(path)}

    def _run(self, case):
        run = self.run_root / case["id"] / case["run_id"]
        recording = run / "recording"
        chunk = recording / "chunks/000000.npz"
        chunk.parent.mkdir(parents=True)
        slow_contact = case["id"] == "dev-3110-seed-10-augmented"
        if slow_contact:
            pose = np.array([[0., 0., 0.], [.001, 0., 0.]], dtype=np.float64)
            next_pose = np.array([[.001, 0., 0.], [.002, 0., 0.]], dtype=np.float64)
            sensors = np.array([[1., 0., 0., 0.], [1., 0., 0., 0.]], dtype=np.float32)
            action = np.array([[.2, .1], [.2, -.1]], dtype=np.float32)
        else:
            pose = np.array([[0., 0., 0.], [.1, 0., 0.]], dtype=np.float64)
            next_pose = np.array([[.1, 0., 0.], [.2, 0., 0.]], dtype=np.float64)
            sensors = np.zeros((2, 4), dtype=np.float32)
            action = np.array([[.5, .1], [.5, -.1]], dtype=np.float32)
        if case["arm"] == "augmented" and not slow_contact:
            action[:, 0] *= -1
        control = np.stack([diagnosis.expected_control(row) for row in action]).astype(np.float64)
        arrays = {
            "action": action,
            "control": control,
            "pose": pose,
            "next_pose": next_pose,
            "sensors": sensors,
            "simulation_time": np.array([.02, .04], dtype=np.float64),
            # Accessing this member with allow_pickle=False raises. The diagnosis must not decode it.
            "cam_left": np.array([{"trap": 0}, {"trap": 1}], dtype=object),
        }
        with io.BytesIO() as stream:
            np.savez(stream, **arrays)
            chunk.write_bytes(stream.getvalue())
        fields = {name: {"dtype": value.dtype.str, "shape": list(value.shape[1:])}
                  for name, value in arrays.items()}
        events = [
            {"episode": 0, "kind": "episode_started", "sequence": 0,
             "world": {"arena": 7., "goal": [2., 0.], "obstacles": [], "pose": [0., 0., 0.]}},
            {"arrays": fields, "count": 2, "episode": 0, "kind": "chunk", "path": "chunks/000000.npz",
             "sequence": 1, "sha256": _sha(chunk), "start": 0},
        ]
        (recording / "events.jsonl").write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in events))
        _write_json(recording / "manifest.json", {
            "recording_format": "palimpsest-npz-v1", "recorded_chunks": 1, "recorded_events": 2,
            "recorded_ticks": 2, "run_id": case["run_id"], "status": "completed",
        })
        _write_json(run.parent / "result.json", {
            "case": {key: case[key] for key in ("id", "scene_seed", "training_seed", "arm")},
            "executed_ticks": 2, "outcome": case["outcome"],
            "run_id": case["run_id"], "status": "completed-recording",
        })
        for path in (chunk, recording / "events.jsonl", recording / "manifest.json", run.parent / "result.json"):
            self._record(path)


class ProtocolTests(unittest.TestCase):
    def test_frozen_protocol_is_exact(self):
        path = ROOT / "docs/plans/m7-navigation-v2-failure-diagnosis-v1.json"
        protocol = diagnosis.load_protocol(path)

        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), diagnosis.PROTOCOL_SHA256)
        self.assertEqual(len(protocol["cases"]), 24)
        self.assertEqual(sum(case["ticks"] for case in protocol["cases"]), 10_822)
        self.assertEqual(protocol["input"]["held_out_scene_ids_forbidden"], list(range(3120, 3128)))

    def test_rejects_case_inventory_drift(self):
        protocol = diagnosis.load_protocol()
        protocol["cases"].pop()

        with self.assertRaisesRegex(ValueError, "exactly 24"):
            diagnosis.validate_protocol(protocol)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.fixture = BatchFixture(temporary.name)

    def test_analyzes_exact_batch_without_decoding_camera_members(self):
        report = diagnosis.analyze(
            self.fixture.producer,
            self.fixture.index_path,
            self.fixture.protocol,
        )

        self.assertEqual(report["status"], "completed-read-only-diagnosis")
        self.assertEqual(report["numeric_ticks"], 48)
        self.assertEqual(len(report["runs"]), 24)
        self.assertEqual(len(report["pairs"]), 12)
        slow = next(row for row in report["runs"] if row["case_id"] == "dev-3110-seed-10-augmented")
        self.assertEqual(slow["terminal_class"], "terminal-contact-stall")
        self.assertEqual(slow["terminal_stall_like_suffix_ticks"], 2)
        self.assertAlmostEqual(slow["path_length_metres"], .002)
        pair = next(row for row in report["pairs"] if row["scene_seed"] == 3110 and row["training_seed"] == 10)
        self.assertEqual(pair["common_ticks"], 2)
        self.assertEqual(pair["first_action_divergence_tick"], 0)
        self.assertFalse(report["r3_complete"])
        self.assertEqual(report["qualification_claims"], [])

    def test_expected_control_matches_frozen_projection(self):
        np.testing.assert_array_equal(
            diagnosis.expected_control(np.array([.7, .4], dtype=np.float32)),
            np.array([1., 1.8], dtype=np.float32),
        )

    def test_rejects_ledger_drift_before_decode(self):
        case = self.fixture.protocol["cases"][0]
        chunk = (self.fixture.run_root / case["id"] / case["run_id"] /
                 "recording/chunks/000000.npz")
        chunk.write_bytes(chunk.read_bytes() + b"drift")

        with self.assertRaisesRegex(ValueError, "ledger drift"):
            diagnosis.analyze(self.fixture.producer, self.fixture.index_path, self.fixture.protocol)

    def test_rejects_event_inventory_drift(self):
        self.fixture.index["events"] -= 1
        _write_json(self.fixture.index_path, self.fixture.index)
        self.fixture.protocol["input"]["development_index_sha256"] = _sha(self.fixture.index_path)

        with self.assertRaisesRegex(ValueError, "development index differs"):
            diagnosis.analyze(self.fixture.producer, self.fixture.index_path, self.fixture.protocol)

    def test_rejects_lexical_parent_traversal_even_inside_producer(self):
        case = self.fixture.protocol["cases"][0]
        relative = (f"{self.fixture.protocol['input']['run_root_relative']}/"
                    f"{case['id']}/../{case['id']}/result.json")

        with self.assertRaisesRegex(ValueError, "unsafe ledger path"):
            diagnosis._safe_file(self.fixture.producer, relative)

    def test_rejects_input_change_after_decode(self):
        before = {"files": 96, "bytes": 1, "sha256": "a" * 64}
        after = {**before, "sha256": "b" * 64}

        with patch.object(diagnosis, "_check_ledger", side_effect=(before, after)):
            with self.assertRaisesRegex(ValueError, "changed during analysis"):
                diagnosis.analyze(self.fixture.producer, self.fixture.index_path, self.fixture.protocol)

    def test_rejects_index_change_during_analysis(self):
        check = diagnosis._check_ledger
        passes = 0

        def change_after_second_pass(*args, **kwargs):
            nonlocal passes
            result = check(*args, **kwargs)
            passes += 1
            if passes == 2:
                self.fixture.index_path.write_text("{}\n")
            return result

        with patch.object(diagnosis, "_check_ledger", side_effect=change_after_second_pass):
            with self.assertRaisesRegex(ValueError, "index changed"):
                diagnosis.analyze(self.fixture.producer, self.fixture.index_path, self.fixture.protocol)

    def test_deadline_fails_before_input_decode(self):
        with self.assertRaisesRegex(TimeoutError, "deadline"):
            diagnosis.analyze(self.fixture.producer, self.fixture.index_path, self.fixture.protocol, deadline=0.)

    def test_execute_writes_one_bounded_report_and_refuses_reuse(self):
        output = self.fixture.root / "evidence"
        report = diagnosis.execute(
            self.fixture.producer,
            self.fixture.index_path,
            output,
            self.fixture.protocol,
        )

        self.assertEqual(json.loads((output / "report.json").read_text()), report)
        self.assertTrue((output / "protocol.json").is_file())
        self.assertLessEqual(sum(path.stat().st_size for path in output.iterdir()), 16 * 1024**2)
        with self.assertRaisesRegex(ValueError, "fresh"):
            diagnosis.execute(self.fixture.producer, self.fixture.index_path, output, self.fixture.protocol)

    def test_execute_retains_failure_without_partial_report(self):
        case = self.fixture.protocol["cases"][0]
        chunk = (self.fixture.run_root / case["id"] / case["run_id"] /
                 "recording/chunks/000000.npz")
        chunk.write_bytes(chunk.read_bytes() + b"drift")
        output = self.fixture.root / "failed-evidence"

        with self.assertRaisesRegex(ValueError, "ledger drift"):
            diagnosis.execute(
                self.fixture.producer,
                self.fixture.index_path,
                output,
                self.fixture.protocol,
            )

        failure = json.loads((output / "failure.json").read_text())
        self.assertEqual(failure["status"], "failed-diagnostic")
        self.assertEqual(failure["qualification_claims"], [])
        self.assertFalse((output / "report.json").exists())

    def test_execute_removes_partial_report_and_retains_write_failure(self):
        output = self.fixture.root / "write-failed-evidence"
        write = diagnosis._write_output

        def fail_report(target, name, payload, maximum):
            if name == "report.json":
                (target / name).write_bytes(b"partial")
                raise OSError("authored report write failure")
            return write(target, name, payload, maximum)

        with patch.object(diagnosis, "_write_output", side_effect=fail_report):
            with self.assertRaisesRegex(OSError, "authored report write failure"):
                diagnosis.execute(
                    self.fixture.producer,
                    self.fixture.index_path,
                    output,
                    self.fixture.protocol,
                )

        failure = json.loads((output / "failure.json").read_text())
        self.assertEqual(failure["error"]["type"], "OSError")
        self.assertFalse((output / "report.json").exists())

    def test_rejects_output_overlap_before_creating_parent(self):
        parent = self.fixture.producer / "must-not-be-created"

        with self.assertRaisesRegex(ValueError, "overlaps"):
            diagnosis.execute(
                self.fixture.producer,
                self.fixture.index_path,
                parent / "evidence",
                self.fixture.protocol,
            )

        self.assertFalse(parent.exists())


class ImportBoundaryTests(unittest.TestCase):
    def test_source_and_import_exclude_forbidden_native_stacks(self):
        source = (ROOT / "scripts/diagnose_male_navigation_v2.py").read_text()
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(ast.parse(source))
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertTrue({"torch", "mujoco"}.isdisjoint(imported))

        command = [
            sys.executable,
            "-I",
            "-B",
            "-c",
            ("import sys;"
             f"sys.path[:0]=[{str(ROOT / 'src')!r},{str(ROOT / 'scripts')!r}];"
             "import diagnose_male_navigation_v2;"
             "assert 'torch' not in sys.modules and 'mujoco' not in sys.modules"),
        ]
        subprocess.run(command, check=True, cwd=ROOT, timeout=15)


if __name__ == "__main__":
    unittest.main()
