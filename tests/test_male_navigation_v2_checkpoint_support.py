"""Synthetic contracts for the one-pass selected-checkpoint support audit."""
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/audit_male_navigation_v2_checkpoint_support.py"
PROTOCOL = ROOT / "docs/plans/m7-navigation-v2-checkpoint-support-v1.json"


def load_audit():
    if not SCRIPT.exists():
        raise AssertionError("checkpoint-support audit script is not implemented")
    spec = importlib.util.spec_from_file_location("checkpoint_support", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metric(loss=0.25, velocity=0.5, heading=0.75):
    return {
        "ticks": 6,
        "loss": loss,
        "velocity_mae": velocity,
        "wrapped_heading_mae_radians": heading,
        "interpretation": "recorded-input teacher imitation; not closed-loop navigation success",
    }


class MetricTests(unittest.TestCase):
    def test_summary_resets_sign_transitions_at_source_boundaries(self):
        audit = load_audit()
        values = np.asarray([-.2, 0., .2, .3, -.4, .01], dtype=np.float32)

        summary = audit.component_summary(values, [3, 3], .05, [0., .5, 1.])

        self.assertEqual(summary["sign_counts"], {"negative": 2, "deadband": 2, "positive": 2})
        self.assertEqual(summary["within_source_sign_changes"], 2)
        self.assertEqual(summary["quantiles"], [-.4000000059604645, .004999999888241291, .30000001192092896])

    def test_summary_rejects_nonfinite_or_wrong_source_lengths(self):
        audit = load_audit()
        with self.assertRaisesRegex(ValueError, "finite float32"):
            audit.component_summary(np.asarray([0., np.nan], np.float32), [2], .05, [0., 1.])
        with self.assertRaisesRegex(ValueError, "source lengths"):
            audit.component_summary(np.asarray([0., 1.], np.float32), [1], .05, [0., 1.])

    def test_support_classification_uses_target_sign_support(self):
        audit = load_audit()
        absent = {"sign_counts": {"negative": 0, "deadband": 1, "positive": 2}, "within_source_sign_changes": 0}
        both = {"sign_counts": {"negative": 1, "deadband": 0, "positive": 1}, "within_source_sign_changes": 1}
        positive = {"sign_counts": {"negative": 0, "deadband": 0, "positive": 2}, "within_source_sign_changes": 0}
        no_switch = {"sign_counts": {"negative": 1, "deadband": 0, "positive": 1}, "within_source_sign_changes": 0}

        self.assertEqual(audit.support_classification(absent, both), "target_support_absent")
        self.assertEqual(audit.support_classification(both, positive), "checkpoint_sign_missing")
        self.assertEqual(audit.support_classification(both, no_switch), "checkpoint_signs_present_no_switch")
        self.assertEqual(audit.support_classification(both, both), "checkpoint_switches")


class AdmissionTests(unittest.TestCase):
    def test_candidate_admission_uses_exact_common_frozen_training_root(self):
        audit = load_audit()
        protocol = audit.load_protocol()
        expected = Path("/home/utkarsh/Work/shraddha/brain/.worktrees/male-navigation-training-v2")
        observed = {}

        def admit(root, assets, index):
            observed.update(root=root, assets=assets, index=index)
            return "admitted"

        research = mock.Mock()
        research._admit.side_effect = admit
        self.assertEqual(audit.admit_candidates(protocol, {"models": []}, research), "admitted")
        self.assertEqual(observed, {
            "root": expected,
            "assets": Path("/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/data/assets/flynn"),
            "index": {"models": []},
        })

        protocol["immutable_inputs"]["cell_source"]["path"] = str(
            Path("/tmp/different") / "upstream/fly-gym/models/connectome_rnn_model.py")
        with self.assertRaisesRegex(ValueError, "common frozen training root"):
            audit.admit_candidates(protocol, {}, research)

        protocol = audit.load_protocol()
        protocol["checkpoints"][0]["path"] = "/tmp/different/old-corpus.pt"
        with self.assertRaisesRegex(ValueError, "training artifact root"):
            audit.admit_candidates(protocol, {}, research)

    def test_execution_manifest_binds_source_test_protocol_and_output(self):
        audit = load_audit()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "result"
            manifest = {
                "schema": "m7-navigation-v2-checkpoint-support-execution-manifest-v1",
                "attempt": 1,
                "retry_allowed": False,
                "protocol_sha256": audit.PROTOCOL_SHA256,
                "script_sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
                "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "behavior_sources": audit.load_protocol()["reader_sources"],
                "outer_timeout_seconds": 210,
                "outer_supervisor": {"program": "/usr/bin/timeout",
                                     "arguments": ["--signal=TERM", "210s"],
                                     "through_return_seconds": 210},
                "output": str(output),
            }
            path = root / "execution-manifest.json"
            path.write_text(json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n")
            pin = hashlib.sha256(path.read_bytes()).hexdigest()

            self.assertEqual(audit.load_execution_manifest(path, pin, output), manifest)
            with self.assertRaisesRegex(ValueError, "execution manifest"):
                audit.load_execution_manifest(path, "0" * 64, output)
            with self.assertRaisesRegex(ValueError, "execution output"):
                audit.load_execution_manifest(path, pin, root / "different")

    def test_all_local_behavior_sources_are_pinned_before_import(self):
        audit = load_audit()
        protocol = audit.load_protocol()
        expected = {
            "scripts/prepare_male_navigation_v2.py",
            "scripts/train_male_navigation_v2.py",
            "scripts/train_male_reduced.py",
            "src/palimpsest/artifacts.py",
            "src/palimpsest/male_model.py",
            "src/palimpsest/male_navigation_research.py",
            "src/palimpsest/male_policy.py",
            "src/palimpsest/male_research.py",
            "src/palimpsest/records.py",
            "src/palimpsest/storage.py",
        }
        self.assertEqual(set(protocol["reader_sources"]), expected)
        self.assertEqual(audit.verify_behavior_sources(protocol, math.inf), protocol["reader_sources"])

    def test_execute_reserves_attempt_before_import_or_input_hashes(self):
        audit = load_audit()
        protocol = audit.load_protocol()
        events = []

        class StopBeforeInput(Exception):
            pass

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "runs").mkdir()
            output = root / "runs/result"
            with (mock.patch.object(audit, "ROOT", root),
                  mock.patch.object(audit, "load_execution_manifest", return_value={
                      "outer_supervisor": protocol["attempt_contract"]["outer_supervisor"]}),
                  mock.patch.object(audit, "load_protocol", return_value=protocol),
                  mock.patch.object(audit, "verify_behavior_sources",
                                    side_effect=lambda *_: events.append("sources") or {}),
                  mock.patch.object(audit, "reserve_attempt",
                                    side_effect=lambda *_: events.append("reserve") or b"attempt"),
                  mock.patch.object(audit, "load_behavior",
                                    side_effect=lambda *_: events.append("imports") or object()),
                  mock.patch.object(audit, "_fingerprints",
                                    side_effect=lambda *_: (events.append("inputs"), (_ for _ in ()).throw(StopBeforeInput()))[1])):
                with self.assertRaises(StopBeforeInput):
                    audit.execute(output, Path("manifest"), "0" * 64)
        self.assertEqual(events, ["reserve", "sources", "imports", "sources", "inputs"])

    def test_protocol_hash_and_exact_budget_accounting(self):
        audit = load_audit()
        protocol = audit.load_protocol()

        self.assertEqual(hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(), audit.PROTOCOL_SHA256)
        self.assertEqual(audit.selected_budget(20, 2117, 72),
                         {"epoch": 20, "row_presentations": 42340, "optimizer_updates": 1440})
        audit.validate_budget_accounting(protocol)

        protocol["budget_accounting"]["selected_checkpoints"][0]["augmented"]["optimizer_updates"] += 1
        with self.assertRaisesRegex(ValueError, "budget accounting"):
            audit.validate_budget_accounting(protocol)

    def test_document_admission_rejects_wrong_roster_or_heldout(self):
        audit = load_audit()
        protocol = audit.load_protocol()
        index = {
            "models": [{"training_seed": item["training_seed"], "arm": item["arm"],
                        "selected_epoch": item["selected_epoch"],
                        "checkpoint": {"path": Path(item["path"]).relative_to(
                            "/home/utkarsh/Work/shraddha/brain/.worktrees/male-navigation-training-v2").as_posix(),
                            "size_bytes": item["bytes"], "sha256": item["sha256"]},
                        "report": {"path": Path(next(report["path"] for report in protocol["pair_reports"]
                                                      if report["training_seed"] == item["training_seed"])).relative_to(
                            "/home/utkarsh/Work/shraddha/brain/.worktrees/male-navigation-training-v2").as_posix(),
                            "size_bytes": next(report["bytes"] for report in protocol["pair_reports"]
                                               if report["training_seed"] == item["training_seed"]),
                            "sha256": next(report["sha256"] for report in protocol["pair_reports"]
                                          if report["training_seed"] == item["training_seed"])},
                        "selected_recorded_dev": {**metric(), "ticks": 1228}}
                       for item in protocol["checkpoints"]],
            "held_out_status": "locked_unopened",
            "qualification_claims": [],
        }
        data = {"arms": {"old": {"held_out": []}, "augmented": {"held_out": []}}}
        admitted = audit.validate_documents(protocol, index, data)
        self.assertEqual(len(admitted), 6)

        data["arms"]["augmented"]["held_out"] = ["forbidden"]
        with self.assertRaisesRegex(ValueError, "held-out"):
            audit.validate_documents(protocol, index, data)

        data["arms"]["augmented"]["held_out"] = []
        index["models"][0]["report"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "pair report"):
            audit.validate_documents(protocol, index, data)
        index["models"][0]["report"]["sha256"] = protocol["pair_reports"][0]["sha256"]
        index["models"].reverse()
        with self.assertRaisesRegex(ValueError, "six ordered"):
            audit.validate_documents(protocol, index, data)

    def test_file_pin_rejects_symlink_and_mismatch(self):
        audit = load_audit()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            value = root / "value.json"
            value.write_bytes(b"{}\n")
            pin = {"path": str(value), "bytes": 3, "sha256": hashlib.sha256(value.read_bytes()).hexdigest()}
            self.assertEqual(audit.read_pin(pin, 16), b"{}\n")
            alias = root / "alias.json"
            alias.symlink_to(value)
            with self.assertRaisesRegex(ValueError, "regular non-symlink"):
                audit.read_pin({**pin, "path": str(alias)}, 16)
            with self.assertRaisesRegex(ValueError, "differs"):
                audit.read_pin({**pin, "sha256": "0" * 64}, 16)


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.audit = load_audit()
        self.protocol = self.audit.load_protocol()
        self.protocol["recorded_development"].update(rows=6, windows_per_model=2, total_rows=36, total_windows=12)
        self.protocol["recorded_development"]["sequence_order"] = [
            {"run_id": "a", "rows": 3, "feature_target_sha256": "a" * 64},
            {"run_id": "b", "rows": 3, "feature_target_sha256": "b" * 64},
        ]
        targets = [np.asarray([[.2, -.2], [.3, .2], [.4, .1]], np.float32),
                   np.asarray([[.2, .2], [.3, -.2], [.4, -.1]], np.float32)]
        self.targets = targets
        self.outputs = {}
        for item in self.protocol["checkpoints"]:
            key = self.audit.model_key(item["training_seed"], item["arm"])
            raw = [np.arctanh(source / np.asarray([3., np.pi], np.float32)).astype(np.float32)
                   for source in targets]
            actions = [(np.tanh(value) * np.asarray([3., np.pi], np.float32)).astype(np.float32)
                       for value in raw]
            self.outputs[key] = {"actions": actions, "raw_outputs": raw, "metrics": metric(),
                                 "scaling_exact": True, "rows": 6, "windows": 2}
        self.published = {self.audit.model_key(item["training_seed"], item["arm"]): metric()
                          for item in self.protocol["checkpoints"]}

    def test_analyzes_all_models_and_builds_safe_compact_npz(self):
        report, payload = self.audit.analyze_outputs(self.protocol, self.targets, self.outputs, self.published)

        self.assertEqual(report["rows"], 36)
        self.assertEqual(report["windows"], 12)
        self.assertEqual(len(report["models"]), 6)
        self.assertEqual(report["models"][0]["heading"]["support"], "checkpoint_switches")
        self.assertEqual(len(report["pairs"]), 3)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            self.assertTrue(all(item.compress_type == zipfile.ZIP_STORED for item in archive.infolist()))
            self.assertEqual(len(archive.infolist()), 26)
            with np.load(io.BytesIO(payload), allow_pickle=False) as arrays:
                self.assertTrue(all(value.dtype == np.float32 for value in arrays.values()))

    def test_analysis_rejects_second_pass_shape_nonfinite_scaling_and_metric_drift(self):
        key = self.audit.model_key(10, "old-corpus")
        variants = []
        wrong_rows = {**self.outputs[key], "rows": 7}
        variants.append((wrong_rows, "row/window"))
        nonfinite = {**self.outputs[key], "actions": [x.copy() for x in self.outputs[key]["actions"]]}
        nonfinite["actions"][0][0, 0] = np.nan
        variants.append((nonfinite, "finite float32"))
        variants.append(({**self.outputs[key], "scaling_exact": False}, "tanh scaling"))
        variants.append(({**self.outputs[key], "metrics": metric(loss=.3)}, "published metric"))
        for value, message in variants:
            with self.subTest(message=message):
                outputs = {**self.outputs, key: value}
                with self.assertRaisesRegex(ValueError, message):
                    self.audit.analyze_outputs(self.protocol, self.targets, outputs, self.published)

    def test_inference_resets_each_source_and_carries_between_windows(self):
        audit = self.audit
        calls = []

        class Agent:
            training = False
            resets = 0

            def parameters(self):
                return []

            def reset(self):
                value = f"reset-{self.resets}"
                self.resets += 1
                return value

        class Torch:
            @staticmethod
            def inference_mode():
                return mock.MagicMock(__enter__=lambda _: None, __exit__=lambda *_: None)

        def forward(_agent, features, targets, hidden, _torch, _loss):
            calls.append((len(features), hidden))
            rows = len(features)
            actions = np.zeros((rows, 2), np.float32)
            raw = np.ones((rows, 2), np.float32)
            return f"{hidden}+{rows}", actions, raw, True, float(rows), 0.0, 0.0

        episodes = [
            {"features": np.zeros((33, 388), np.float32), "targets": np.zeros((33, 2), np.float32)},
            {"features": np.zeros((1, 388), np.float32), "targets": np.zeros((1, 2), np.float32)},
        ]
        result = audit._infer(Agent(), episodes, Torch(), math.inf, None, forward_window=forward)

        self.assertEqual(calls, [(32, "reset-0"), (1, "reset-0+32"), (1, "reset-1")])
        self.assertEqual((result["rows"], result["windows"]), (34, 3))


class PublicationTests(unittest.TestCase):
    def test_attempt_reservation_is_durable_and_nonrepeatable(self):
        audit = load_audit()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fresh"
            payload = audit.reserve_attempt(output, {"status": "attempt-reserved"})
            self.assertEqual((output / "attempt.json").read_bytes(), payload)
            with self.assertRaises(FileExistsError):
                audit.reserve_attempt(output, {"status": "attempt-reserved"})

    def test_deadline_rss_and_aggregate_output_caps_fail_closed(self):
        audit = load_audit()
        protocol = audit.load_protocol()
        with self.assertRaises(TimeoutError):
            audit.final_prepublication_checks(protocol, time.monotonic() - 1, math.inf, b"")
        high = mock.Mock(ru_maxrss=protocol["limits"]["rss_budget_bytes"] // 1024 + 1)
        with mock.patch.object(audit.resource, "getrusage", return_value=high):
            with self.assertRaises(MemoryError):
                audit.final_prepublication_checks(protocol, math.inf, math.inf, b"")
        protocol["limits"]["output_bytes"] = 3
        with self.assertRaisesRegex(ValueError, "publication"):
            audit.final_prepublication_checks(protocol, math.inf, math.inf, b"aa", b"bb")

    def test_success_is_atomic_and_report_is_last(self):
        audit = load_audit()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fresh"
            audit.reserve_attempt(output, {"status": "attempt-reserved"})
            audit.publish_success(output, b"{}\n", b"arrays", {"status": "completed"},
                                  {"status": "completed-execution"})
            self.assertEqual(sorted(path.name for path in output.iterdir()),
                             ["attempt.json", "execution.json", "outputs.npz", "protocol.json", "report.json"])
            self.assertEqual(json.loads((output / "report.json").read_text())["status"], "completed")

    def test_final_marker_failure_removes_completion_markers_but_retains_attempt(self):
        audit = load_audit()
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "fresh"
            audit.reserve_attempt(output, {"status": "attempt-reserved"})
            with self.assertRaisesRegex(OSError, "injected"):
                audit.publish_success(output, b"{}\n", b"arrays", {"status": "completed"},
                                      {"status": "completed-execution"}, fault="final_rename")
            self.assertFalse((output / "report.json").exists())
            self.assertFalse((output / "execution.json").exists())
            self.assertTrue((output / "attempt.json").is_file())
            audit.publish_failure(output, {"status": "failed", "error": "injected"})
            self.assertTrue((output / "failure.json").is_file())

    def test_import_does_not_load_torch_or_simulator(self):
        command = [
            sys.executable, "-I", "-c",
            ("import importlib.util, pathlib, sys;"
             f"p=pathlib.Path({str(SCRIPT)!r});s=importlib.util.spec_from_file_location('audit',p);"
             "m=importlib.util.module_from_spec(s);s.loader.exec_module(m);"
             "v=m.load_protocol();m.verify_behavior_sources(v,float('inf'));b=m.load_behavior(v);"
             f"r=pathlib.Path({str(ROOT)!r}).resolve();"
             "assert all(pathlib.Path(x.__file__).resolve().is_relative_to(r) for x in b.modules);"
             "assert 'torch' not in sys.modules and 'mujoco' not in sys.modules"),
        ]
        subprocess.run(command, check=True, cwd=ROOT, timeout=15)


if __name__ == "__main__":
    unittest.main()
