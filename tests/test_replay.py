import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

from palimpsest.replay import Divergence, _same_tick, _register_initial, replay_run

REPO = Path(__file__).resolve().parents[1]


class ReplayValidation(unittest.TestCase):
    def test_loading_cancellation_and_invalid_source_preserve_reports(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / uuid.uuid4().hex
            source.mkdir()
            for cancel in (False, True):
                destination = root / uuid.uuid4().hex
                destination.mkdir()
                def progress(stage):
                    self.assertEqual(stage, "loading")
                    raise InterruptedError("operator stop")
                report = replay_run(source, destination, mode="actions", repo_root=REPO, asset_root=root,
                                    progress=progress if cancel else None)
                self.assertEqual(report["status"], "cancelled" if cancel else "failed")
                self.assertEqual(report, json.loads((destination / "replay-report.json").read_text()))
                self.assertFalse((destination / "recording").exists())

    def test_optional_recording_limit_forwarded_and_default_call_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);source=root/uuid.uuid4().hex;source.mkdir()
            manifest={'controller':'manual','scenario':{'id':'reproduction'},
                      'requested_device':'cpu','seed':1,'texture':'checker'}
            calls=[]
            for limit in (None,256*1024**2):
                destination=root/uuid.uuid4().hex;destination.mkdir()
                with patch('palimpsest.replay._load',return_value={'manifest':manifest}), \
                     patch('palimpsest.replay._initial_snapshot',return_value=(
                         {'application':{}},{'snapshot_id':'fixture','sha256':'a'*64},[])), \
                     patch('palimpsest.engine.Engine.open',side_effect=RuntimeError('fixture stop before allocation')) as opened:
                    report=replay_run(source,destination,mode='actions',repo_root=REPO,asset_root=root,
                                      recording_max_bytes=limit)
                self.assertEqual(report['status'],'failed')
                calls.append(opened.call_args.kwargs)
            self.assertNotIn('max_bytes',calls[0])
            self.assertEqual(calls[1].pop('max_bytes'),256*1024**2)
            # Destination ID changes; every other pre-existing keyword stays identical.
            calls[0].pop('run_id');calls[1].pop('run_id')
            self.assertEqual(calls[0],calls[1])

    def test_report_lists_checked_body_fields_and_runtime_sources(self):
        from palimpsest.replay import _RUNTIME, _BODY_RUNTIME, _ADAPTIVE_RUNTIME, _MALE_RUNTIME, _PHYSICAL
        from palimpsest.body_profile import TICK_FIELDS
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / uuid.uuid4().hex
            source.mkdir()
            for controller, scenario, extra in (
                    ('manual', 'calibrated-wheel-compensation', _BODY_RUNTIME),
                    ('manual', 'adaptive-wheel-calibration', _ADAPTIVE_RUNTIME),
                    ('manual', 'reproduction', ()),
                    ('male-original', 'reproduction', _MALE_RUNTIME)):
                for mode in ('actions', 'policy'):
                    with self.subTest(controller=controller, scenario=scenario, mode=mode):
                        destination = root / uuid.uuid4().hex
                        destination.mkdir()
                        # A stray identity key must not select body reporting for another scenario.
                        manifest = {'controller': controller, 'scenario': {'id': scenario},
                                    'requested_device': 'cpu', 'seed': 1, 'texture': 'checker',
                                    'body_profile_identity': {}}
                        with patch('palimpsest.replay._load', return_value={'manifest': manifest}), \
                             patch('palimpsest.replay._initial_snapshot', return_value=(
                                 {'application': {}}, {'snapshot_id': 'fixture', 'sha256': 'a'*64}, [])), \
                             patch('palimpsest.replay.validate_identity', return_value={}), \
                             patch('palimpsest.engine.Engine.open', side_effect=RuntimeError('fixture stop before physics')):
                            report = replay_run(source, destination, mode=mode,
                                                repo_root=REPO, asset_root=root)
                        self.assertEqual(report['status'], 'failed')
                        self.assertEqual(report['comparison']['runtime_source_keys'], list(_RUNTIME + extra))
                        fields = _PHYSICAL | (TICK_FIELDS if scenario in ('calibrated-wheel-compensation','adaptive-wheel-calibration') else set())
                        self.assertEqual(report['comparison']['fields'], sorted(fields) if mode == 'actions'
                                         else 'all recorded fields except wall latencies')
                        self.assertEqual(report, json.loads((destination/'replay-report.json').read_text()))

    @unittest.skipIf(np is None, "NumPy is provided by simulation extra")
    def test_float_tolerance_integer_exact_and_first_field_details(self):
        expected = {"episode": 2, "tick": 7, "hidden": np.array([.3, .4]), "camera": np.array([1, 2], np.uint8)}
        actual = copy.deepcopy(expected)
        actual["hidden"][0] += 1e-8
        _same_tick(expected, actual, "policy", 15)
        actual["camera"][1] = 3
        with self.assertRaises(Divergence) as error:
            _same_tick(expected, actual, "policy", 15)
        self.assertEqual(error.exception.detail, {"field": "camera", "reason": "numeric replay divergence",
            "episode": 2, "tick": 7, "global_tick": 15, "index": [1], "expected": 2, "actual": 3})
        actual = copy.deepcopy(expected)
        actual["hidden"][0] = np.nan
        with self.assertRaises(Divergence) as error:
            _same_tick(expected, actual, "policy", 15)
        self.assertEqual(error.exception.detail["actual"], "nan")
        json.dumps(error.exception.detail, allow_nan=False)


@unittest.skipUnless(os.environ.get("PALIMPSEST_SIMULATION_TESTS") == "1", "opt-in actual upstream EGL replay")
class ActualReplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def destination(self):
        path = self.root / uuid.uuid4().hex
        path.mkdir()
        return path

    def open(self, run):
        from palimpsest.engine import Engine
        return Engine.open(REPO, self.root / "assets", run / "recording", controller="manual", seed=19,
                           scenario="sparse-navigation", run_id=run.name)

    def command(self, engine, kind, payload=None, *, advance=True, expected_episode=None):
        command = {"id": uuid.uuid4().hex, "kind": kind, "expected_state": engine.phase,
                   "expected_episode": engine.episode if expected_episode is None else expected_episode}
        if payload is not None:
            command["payload"] = payload
        engine.submit(command)
        if advance:
            engine.advance()
        return command

    def source(self, *, pending_initial=False):
        source = self.destination()
        engine = self.open(source)
        try:
            if pending_initial:
                self.command(engine, "step", advance=False)
                self.command(engine, "step", advance=False)
            initial = _register_initial(engine, source)
            if pending_initial:
                engine.advance()
                engine.advance()
            self.command(engine, "set_action", {"action": [.3, .1]})
            self.command(engine, "step")
            self.command(engine, "set_eyes", {"left": False, "right": True})
            goal = engine.world()["goal"]
            for dx, dy in ((.25, 0.), (-.25, 0.), (0., .25), (0., -.25)):
                payload = {"kind": "move_goal", "xy": [goal[0] + dx, goal[1] + dy]}
                try:
                    engine.preview(payload)
                except ValueError:
                    continue
                self.command(engine, "intervene", payload)
                break
            else:
                self.fail("actual seeded scene lacks a nearby valid goal edit")
            self.command(engine, "run")
            engine.advance()
            # Disconnect cancels queued commands before resetting intent and pause.
            self.command(engine, "set_action", {"action": [.1, 0.]}, advance=False)
            engine.pause_for_disconnect()
            self.command(engine, "reset", {"seed": 20})
            self.command(engine, "step")
            self.command(engine, "pause", expected_episode=0)  # Explicit stale rejection.
            self.command(engine, "step", advance=False)  # Close rejection; must not add a tick.
        finally:
            engine.close()
        return source, initial

    def replay(self, source, mode, **kwargs):
        destination = self.destination()
        report = replay_run(source, destination, mode=mode, repo_root=REPO, asset_root=self.root / "assets", **kwargs)
        return destination, report

    def test_actual_actions_policy_events_masks_reset_and_inherited_queue(self):
        from palimpsest.artifacts import registered_snapshots
        from palimpsest.records import iter_ticks
        source, initial = self.source(pending_initial=True)
        for mode in ("actions", "policy"):
            stages = []
            def progress(stage, **values):
                stages.append(stage)
                if stage != "loading":
                    self.assertIn("state", values)
            destination, report = self.replay(source, mode, progress=progress)
            self.assertEqual(report["status"], "passed", report)
            self.assertEqual(report["compared_ticks"], 6)
            self.assertGreater(report["compared_events"], 20)
            self.assertIn("ready", stages)
            self.assertEqual(stages.count("step") % 2, 0)
            manifest = json.loads((destination / "recording/manifest.json").read_text())
            self.assertEqual(manifest["source_snapshot_id"], initial)
            self.assertEqual(manifest["parent_run_id"], source.name)
            self.assertEqual(manifest["execution_mode"], mode)
            self.assertFalse(manifest["inference_executed"])  # Manual mode invokes no neural model.
            self.assertEqual(manifest["controller_reexecuted"], mode == "policy")
            self.assertEqual(len(list(iter_ticks(destination / "recording"))), 6)
            self.assertEqual(len(registered_snapshots(destination)), 1)
            self.assertTrue((destination / "snapshots/index.json").is_file())

    def test_actual_first_divergence_and_ready_cancellation(self):
        from palimpsest.engine import Engine
        source, _ = self.source()
        original = Engine.advance
        def altered(engine, action_override=None):
            if action_override is not None:
                action_override = action_override.copy()
                action_override[0] += .1
            return original(engine, action_override=action_override)
        with patch.object(Engine, "advance", altered):
            destination, report = self.replay(source, "actions")
        self.assertEqual(report["status"], "diverged", report)
        self.assertEqual(report["first_divergence"]["field"], "action")
        self.assertEqual(report["first_divergence"]["tick"], 0)
        self.assertEqual(json.loads((destination / "replay-report.json").read_text()), report)
        def cancel(stage, **values):
            if stage == "ready":
                raise InterruptedError("operator cancellation at ready boundary")
        destination, report = self.replay(source, "policy", progress=cancel)
        self.assertEqual(report["status"], "cancelled", report)
        manifest = json.loads((destination / "recording/manifest.json").read_text())
        self.assertEqual(manifest["recorded_ticks"], 0)
        self.assertEqual(manifest["status"], "completed")

    def test_actual_snapshot_prefix_and_runtime_mismatch_fail_before_step(self):
        from palimpsest.snapshots import read_snapshot, save_snapshot
        source, _ = self.source()
        path = source / "snapshots/initial.snp"
        snapshot = read_snapshot(path)
        snapshot["application"]["event_prefix"]["sha256"] = "0" * 64
        path.unlink()
        save_snapshot(snapshot, path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        events_path = source / "recording/events.jsonl"
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        registration = next(event for event in events if event["kind"] == "snapshot_registered" and event["initial"])
        registration["sha256"] = digest
        events_path.write_text("".join(json.dumps(event) + "\n" for event in events))
        index_path = source / "snapshots/index.json"
        index = json.loads(index_path.read_text())
        index["snapshots"][registration["snapshot_id"]]["sha256"] = digest
        index_path.write_text(json.dumps(index))
        destination, report = self.replay(source, "policy")
        self.assertEqual(report["status"], "failed", report)
        self.assertIn("event prefix", report["errors"][0]["message"])
        self.assertFalse((destination / "recording").exists())
        clean, _ = self.source()
        events_path = clean / "recording/events.jsonl"
        events = [json.loads(line) for line in events_path.read_text().splitlines()]
        next(event for event in events if event["kind"] == "environment")["lock_sha256"] = "wrong"
        # Bind a well-formed initial snapshot to the altered provenance prefix;
        # the independent runtime comparison must still reject before a tick.
        snapshot_path = clean / "snapshots/initial.snp"
        snapshot = read_snapshot(snapshot_path)
        prefix = snapshot["application"]["event_prefix"]
        raw = "".join(json.dumps(event) + "\n" for event in events[:prefix["event_count"]]).encode()
        prefix.update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        snapshot_path.unlink()
        save_snapshot(snapshot, snapshot_path)
        digest = hashlib.sha256(snapshot_path.read_bytes()).hexdigest()
        registration = next(event for event in events if event["kind"] == "snapshot_registered" and event["initial"])
        registration["sha256"] = digest
        events_path.write_text("".join(json.dumps(event) + "\n" for event in events))
        index_path = clean / "snapshots/index.json"
        index = json.loads(index_path.read_text())
        index["snapshots"][registration["snapshot_id"]]["sha256"] = digest
        index_path.write_text(json.dumps(index))
        destination, report = self.replay(clean, "actions")
        self.assertEqual(report["status"], "failed", report)
        self.assertIn("runtime provenance", report["errors"][0]["message"])
        self.assertEqual(report["compared_ticks"], 0)
        self.assertEqual(json.loads((destination / "recording/manifest.json").read_text())["recorded_ticks"], 0)

    def test_actual_replay_of_a_branch_preserves_nonzero_origin_and_stop(self):
        from palimpsest.snapshots import capture
        original = self.destination()
        engine = self.open(original)
        try:
            _register_initial(engine, original)
            self.command(engine, "set_action", {"action": [.2, .05]})
            self.command(engine, "step")
            snapshot = capture(engine.env, engine.observation, application=engine.application_state())
        finally:
            engine.close()
        branch = self.destination()
        engine = self.open(branch)
        try:
            engine.restore_branch(snapshot)
            engine.writer.event("branch_created", run_id=engine.run_id, parent_snapshot_id=uuid.uuid4().hex,
                                controller_replaced=False)
            _register_initial(engine, branch)
            self.command(engine, "step")
            self.command(engine, "reset", {"seed": 22})
            self.command(engine, "step")
            self.command(engine, "stop")
        finally:
            engine.close()
        destination, report = self.replay(branch, "policy")
        self.assertEqual(report["status"], "passed", report)
        self.assertEqual(report["compared_ticks"], 2)
        manifest = json.loads((destination / "recording/manifest.json").read_text())
        self.assertEqual(manifest["total_tick"], 3)
        self.assertEqual(manifest["final_phase"], "stopped")
        self.assertEqual(manifest["last_outcome"]["reason"], "user_stop")
        self.assertEqual(manifest["parent_run_id"], branch.name)


if __name__ == "__main__":
    unittest.main()
