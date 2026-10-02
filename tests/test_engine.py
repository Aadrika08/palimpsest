import copy
import hashlib
import json
import math
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

try:
    import numpy as np
except ModuleNotFoundError:
    np = None

from palimpsest.engine import Engine
from palimpsest.records import RunWriter, iter_ticks


class SmallEnv:
    def __init__(self, terminate_at=None, truncate_at=None):
        self.model = SimpleNamespace(opt=SimpleNamespace(timestep=.002))
        self.frame_skip, self.arena, self.goal_radius = 10, 7., .8
        self.data = SimpleNamespace(qpos=np.zeros(3), qvel=np.zeros(3), ctrl=np.zeros(2), time=0.)
        self._goal_xy, self._obstacle_xy = np.array([5., 0.]), np.array([[2., 2.]])
        self.terminate_at, self.truncate_at = terminate_at, truncate_at
        self.calls = 0
        self.closed = False

    def reset(self, seed):
        self.calls = 0
        self.data.qpos[:] = 0.
        self.data.qvel[:] = 0.
        self.data.ctrl[:] = 0.
        self.data.time = 0.
        return self._get_obs(), {"dist_to_goal": 5.}

    def _get_obs(self):
        return {"cam_left": np.full((2, 2, 3), self.calls, np.uint8),
                "cam_right": np.zeros((2, 2, 3), np.uint8),
                "sensors": {"collision": False, "collision_angle": None,
                            "wind_direction": np.array([1., 0.]), "vec_to_goal": np.array([5., 0.])},
                "privileged": np.array([999.])}

    def _base_xy(self):
        return self.data.qpos[:2].copy()

    def _base_yaw(self):
        return self.data.qpos[2]

    def step(self, action):
        self.calls += 1
        self.data.qpos[:2] += action * .02
        self.data.ctrl[:] = action
        self.data.time += .02
        terminated, truncated = self.calls == self.terminate_at, self.calls == self.truncate_at
        return self._get_obs(), 1., terminated, truncated, {"dist_to_goal": .2 if terminated else 5., "stalled": False}

    def close(self):
        self.closed = True


class SmallPolicy:
    def __init__(self, action=(.5, 0.)):
        self.action = action
        self.seen = None
        self.failure_diagnostics = {}

    def reset(self):
        self.seen = None

    def act(self, observation):
        self.seen = observation
        return {"action": np.asarray(self.action), "encoded_input": np.zeros(4, np.float32),
                "raw_output": np.zeros(2, np.float32)}


class SmallTeacher:
    def __init__(self, arena_half_extent=7., device="cpu", velocity=.2):
        self.calls = 0
        self.velocity = velocity

    def act(self, env):
        self.calls += 1
        return np.array([self.velocity, .1], dtype=np.float32)


@unittest.skipIf(np is None, "NumPy is provided by the simulation extra")
class EngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engines = []
        self.addCleanup(self.close_engines)

    def close_engines(self):
        for engine in self.engines:
            engine.close()

    def engine(self, name="run", **kwargs):
        env = kwargs.pop("env", SmallEnv())
        writer = RunWriter(self.root / name, {"run_id": name})
        engine = Engine(env, writer, **kwargs)
        self.engines.append(engine)
        return engine

    def command(self, engine, identifier, kind, payload=None, **expected):
        command = {"id": identifier, "kind": kind, "expected_state": expected.get("state", engine.phase),
                   "expected_episode": expected.get("episode", engine.episode)}
        if payload is not None:
            command["payload"] = payload
        return command

    def test_pause_step_run_stop_and_reset_have_exact_tick_boundaries(self):
        engine = self.engine()
        self.assertEqual(engine.advance()["phase"], "paused")
        for identifier in ("step1", "step2"):
            engine.submit(self.command(engine, identifier, "step"))
        self.assertEqual(engine.advance()["total_tick"], 1)
        self.assertEqual(engine.advance()["total_tick"], 2)
        self.assertEqual(engine.advance()["total_tick"], 2)
        engine.submit(self.command(engine, "action", "set_action", {"action": [3., -3.]}))
        engine.submit(self.command(engine, "run", "run"))
        self.assertEqual(engine.advance()["total_tick"], 3)
        np.testing.assert_array_equal(engine.env.data.ctrl, [3., -3.])
        engine.submit(self.command(engine, "pause", "pause"))
        self.assertEqual(engine.advance()["total_tick"], 3)
        engine.submit(self.command(engine, "stop", "stop"))
        self.assertEqual(engine.advance()["phase"], "stopped")
        engine.submit(self.command(engine, "bad-run", "run"))
        self.assertEqual(engine.advance()["phase"], "stopped")
        engine.submit(self.command(engine, "reset", "reset", {"seed": 4}))
        state = engine.advance()
        self.assertEqual((state["phase"], state["episode"], state["total_tick"], state["episode_step"]), ("paused", 1, 3, 0))
        np.testing.assert_array_equal(engine.manual_action, [0., 0.])
        engine.close()
        ticks = list(iter_ticks(self.root / "run"))
        self.assertEqual(len(ticks), 3)
        self.assertEqual(float(ticks[-1]["simulation_time"]), .06)

    def test_duplicate_identity_and_stale_application_are_recorded(self):
        engine = self.engine()
        command = self.command(engine, "one", "step")
        receipt = engine.submit(command)
        self.assertEqual(engine.submit(copy.deepcopy(command)), receipt)
        engine.advance()
        duplicate = engine.submit(command)
        self.assertEqual(duplicate["status"], "applied")
        self.assertEqual((duplicate["received_tick"], duplicate["applied_tick"]), (0, 0))
        self.assertEqual(engine.advance()["total_tick"], 1)
        with self.assertRaises(ValueError):
            engine.submit({**command, "kind": "run"})
        engine.submit(self.command(engine, "reset", "reset"))
        stale = self.command(engine, "stale", "step")
        engine.submit(stale)
        engine.advance()
        self.assertEqual(engine.submit(stale)["status"], "rejected")
        self.assertEqual(engine.total_tick, 1)
        events = [json.loads(line) for line in (self.root / "run/events.jsonl").read_text().splitlines()]
        self.assertEqual(sum(event["kind"] == "command_applied" and event["id"] == "one" for event in events), 1)

    def test_terminal_states_cannot_step_without_explicit_reset(self):
        for name, env, expected in (("goal", SmallEnv(terminate_at=1), "terminated"),
                                    ("limit", SmallEnv(truncate_at=1), "truncated")):
            engine = self.engine(name, env=env)
            engine.submit(self.command(engine, "run", "run"))
            self.assertEqual(engine.advance()["phase"], expected)
            for _ in range(3):
                engine.advance()
            self.assertEqual(engine.env.calls, 1)
            engine.submit(self.command(engine, "step", "step"))
            engine.advance()
            self.assertEqual(engine.env.calls, 1)

    def test_policy_allowlist_and_invalid_output_stop_before_world_step(self):
        policy = SmallPolicy()
        engine = self.engine(controller="flynn", policy=policy)
        engine.submit(self.command(engine, "step", "step"))
        engine.advance()
        self.assertEqual(set(policy.seen), {"cam_left", "cam_right", "sensors"})
        self.assertEqual(set(policy.seen["sensors"]), {"collision", "collision_angle", "wind_direction"})
        policy.action = [float("nan"), 0.]
        engine.submit(self.command(engine, "bad", "step"))
        self.assertEqual(engine.advance()["phase"], "failed")
        self.assertEqual(engine.env.calls, 1)
        self.assertEqual(engine.total_tick, 1)
        engine.close()
        manifest = json.loads((self.root / "run/manifest.json").read_text())
        self.assertEqual(manifest["status"], "failed")
        self.assertEqual(len(list(iter_ticks(self.root / "run"))), 1)

    def test_rejects_bad_commands_and_cross_thread_access(self):
        engine = self.engine()
        for command in ({**self.command(engine, "x", "step"), "extra": 1},
                        self.command(engine, "x", "set_action", {"action": [float("nan"), 0.]}),
                        self.command(engine, "x", "set_action", {"action": [3.1, 0.]}),
                        self.command(engine, "x", "set_action", {"action": [[1., 0.]]})):
            with self.assertRaises(ValueError):
                engine.submit(command)
        errors = []
        def wrong_thread():
            try:
                engine.advance()
            except RuntimeError as error:
                errors.append(str(error))
        thread = threading.Thread(target=wrong_thread)
        thread.start()
        thread.join()
        self.assertEqual(len(errors), 1)
        self.assertEqual(engine.total_tick, 0)

    def test_queue_and_idempotency_caps_do_not_drop_accepted_commands(self):
        engine = self.engine()
        with patch.object(Engine, "MAX_QUEUE", 2), patch.object(Engine, "MAX_IDS", 2):
            engine.submit(self.command(engine, "first", "step"))
            engine.submit(self.command(engine, "second", "step"))
            with self.assertRaises(RuntimeError):
                engine.submit(self.command(engine, "third", "step"))
            engine.advance()
            engine.advance()
            with self.assertRaises(RuntimeError):
                engine.submit(self.command(engine, "third", "step"))
        self.assertEqual(engine.total_tick, 2)
        self.assertEqual(engine.phase, "failed")
        self.assertEqual(engine.advance()["total_tick"], 2)

    def test_application_restore_preserves_pending_command_and_destination_identity(self):
        source = self.engine("source")
        source.submit(self.command(source, "first", "step"))
        source.advance()
        pending = self.command(source, "resume", "run")
        source.submit(pending)
        saved = source.application_state()
        prefix = (self.root / "source/events.jsonl").read_bytes()
        self.assertEqual(saved["event_prefix"], {"sha256": hashlib.sha256(prefix).hexdigest(),
                                                "size_bytes": len(prefix), "event_count": prefix.count(b"\n")})
        self.assertEqual(len(list(iter_ticks(self.root / "source"))), 1)
        destination = self.engine("branch")
        self.assertEqual(destination.validate_application(saved), saved)
        self.assertEqual(destination.total_tick, 0)
        destination.restore_application(saved)
        saved["pending_commands"].clear()
        state = destination.advance()
        self.assertEqual((state["run_id"], state["parent_run_id"], state["total_tick"]), ("branch", "source", 2))
        self.assertEqual(destination.submit(pending)["status"], "applied")
        self.assertEqual(source.total_tick, 1)
        self.assertEqual(destination.parent_event_prefix, saved["event_prefix"])
        with self.assertRaises(ValueError):
            destination.restore_application(source.application_state())

    def test_manual_pi_boundary_and_teacher_reset(self):
        engine = self.engine()
        engine.submit(self.command(engine, "action", "set_action", {"action": [3., math.pi]}))
        engine.submit(self.command(engine, "step", "step"))
        self.assertEqual(engine.advance()["phase"], "paused")
        self.assertEqual(engine.total_tick, 1)
        teacher = self.engine("teacher", controller="teacher", teacher=SmallTeacher(velocity=.7))
        teacher.submit(self.command(teacher, "step", "step"))
        teacher.advance()
        old = teacher.teacher
        teacher.submit(self.command(teacher, "reset", "reset"))
        teacher.advance()
        self.assertIsNot(teacher.teacher, old)
        self.assertEqual(teacher.teacher.calls, 0)
        self.assertEqual(teacher.teacher.velocity, .7)

    def test_intervention_refresh_failure_is_runtime_failure_after_mutation(self):
        engine = self.engine()
        command = self.command(engine, "edit", "intervene", {"kind": "move_goal", "xy": [4., 0.]})
        engine.submit(command)
        def apply(env, payload, teacher=None):
            env._goal_xy[:] = payload["xy"]
            return {"old": [5., 0.], "new": [4., 0.]}
        with patch("palimpsest.interventions.apply_intervention", side_effect=apply):
            with patch.object(engine.env, "_get_obs", side_effect=ValueError("renderer failed")):
                self.assertEqual(engine.advance()["phase"], "failed")
        np.testing.assert_array_equal(engine.env._goal_xy, [4., 0.])
        events = [json.loads(line) for line in (self.root / "run/events.jsonl").read_text().splitlines()]
        self.assertFalse(any(event["kind"] == "command_rejected" for event in events))
        self.assertTrue(any(event["kind"] == "runtime_failure" for event in events))
        self.assertEqual(engine.env.calls, 0)
        self.assertEqual(engine.submit(command)["status"], "failed")
        engine.submit(self.command(engine, "reset", "reset"))
        self.assertEqual(engine.advance()["phase"], "paused")
        branch = self.engine("branch")
        branch.validate_application(engine.application_state())

    def test_invalid_application_is_rejected_without_mutation(self):
        source, branch = self.engine("source"), self.engine("branch")
        state = source.application_state()
        original = branch.application_state()
        for key, value in (("phase", "running"), ("metrics", {"reward": float("nan")}),
                           ("total_tick", -1), ("source_run_id", "branch")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                branch.restore_application({**state, key: value})
            self.assertEqual(branch.application_state(), original)

    def test_close_releases_world_when_recorder_cannot_log_pending_cancellation(self):
        engine = self.engine()
        engine.submit(self.command(engine, "waiting", "step"))
        with patch.object(engine.writer, "event", side_effect=RuntimeError("recording failed")):
            with self.assertRaisesRegex(RuntimeError, "recording failed"):
                engine.close()
        self.assertTrue(engine.env.closed)
        self.assertEqual(engine.public_state()["phase"], "failed")

    def test_teacher_reset_baseline_mismatch_rejected_before_branch_mutation(self):
        source = self.engine("source", controller="teacher", teacher=SmallTeacher(velocity=.7))
        source.submit(self.command(source, "reset-after-snapshot", "reset"))
        state = source.application_state()
        mismatch = self.engine("mismatch", controller="teacher", teacher=SmallTeacher(velocity=.2))
        before = mismatch.application_state()
        with self.assertRaisesRegex(ValueError, "reset baseline identity"):
            mismatch.validate_application(state)
        self.assertEqual(mismatch.application_state(), before)
        matching = self.engine("matching", controller="teacher", teacher=SmallTeacher(velocity=.7))
        matching.restore_application(state)
        source.advance()
        matching.advance()
        self.assertEqual((source.teacher.velocity, matching.teacher.velocity), (.7, .7))
        self.assertEqual((source.episode, matching.episode), (1, 1))

    def test_intervention_shape_rejected_before_copy_or_queue(self):
        engine = self.engine()
        invalid = ({"kind": "move_goal", "xy": [1., 2.], "extra": "unbounded"},
                   {"kind": "move_goal", "xy": [0.] * 10},
                   {"kind": "move_goal", "xy": [True, 0.]},
                   {"kind": "move_goal", "xy": [float("inf"), 0.]},
                   {"kind": "move_obstacle", "xy": [1., 2.], "index": True})
        for payload in invalid:
            command = self.command(engine, "invalid", "intervene", payload)
            with self.subTest(payload=payload), patch("palimpsest.engine.copy.deepcopy", side_effect=AssertionError("copied before validation")):
                with self.assertRaises(ValueError):
                    engine.submit(command)
        self.assertEqual(engine.public_state()["pending_commands"], 0)
        self.assertEqual(engine.application_state()["original_commands"], {})


if __name__ == "__main__":
    unittest.main()
