import copy
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import random
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from palimpsest.snapshots import capture, restore, save_snapshot, read_snapshot


HAS_SIM = all(importlib.util.find_spec(name) for name in ("numpy", "mujoco"))
REPO = Path(__file__).resolve().parents[1]


@unittest.skipUnless(HAS_SIM, "simulation dependencies unavailable")
class PhysicsSnapshots(unittest.TestCase):
    def setUp(self):
        import mujoco
        import numpy as np
        self.mj, self.np = mujoco, np
        model = mujoco.MjModel.from_xml_string('''<mujoco>
          <option gravity="0 0 0" timestep=".01"/>
          <worldbody><body name="moving"><joint type="slide" axis="1 0 0"/>
          <geom size=".1"/><site name="goal" pos="1 0 0"/></body></worldbody>
        </mujoco>''')
        self.env = SimpleNamespace(model=model, data=mujoco.MjData(model),
            np_random=np.random.default_rng(33), _t=1, visited={(1, 2)},
            _prev_xy=np.array([.0, .0], dtype=np.float32), _speed=1.)
        self.env.data.qvel[0] = 1.
        mujoco.mj_step(model, self.env.data)
        self.obs = {"cam_left": np.full((2, 2, 3), 37, dtype=np.uint8),
                    "sensors": {"collision_angle": None}}
        self.app = {"next_tick": 7, "commands": [{"sequence": 8, "kind": "goal"}],
                    "seen": {"request-1": ("accepted", 7)}}

    def snapshot(self):
        return capture(self.env, self.obs, application=self.app)

    def test_actual_physics_continues_with_stale_derived_cache_preserved(self):
        snp = self.snapshot()
        self.assertAlmostEqual(self.env.data.qpos[0], .01)
        self.assertAlmostEqual(self.env.data.xpos[1, 0], 0.)
        expected = []
        for _ in range(4):
            self.mj.mj_step(self.env.model, self.env.data)
            expected.append((self.env.data.qpos.copy(), self.env.data.xpos.copy()))
        observation, application = restore(snp, self.env)
        self.assertAlmostEqual(self.env.data.xpos[1, 0], 0.)
        self.assertEqual(application, self.app)
        self.np.testing.assert_array_equal(observation["cam_left"], self.obs["cam_left"])
        for qpos, xpos in expected:
            self.mj.mj_step(self.env.model, self.env.data)
            self.np.testing.assert_array_equal(self.env.data.qpos, qpos)
            self.np.testing.assert_array_equal(self.env.data.xpos, xpos)

    def test_capture_and_restore_do_not_alias_snapshot(self):
        snp = self.snapshot()
        self.obs["cam_left"].fill(99)
        self.app["commands"].clear()
        self.env.visited.clear()
        obs, app = restore(snp, self.env)
        self.assertEqual(int(obs["cam_left"][0, 0, 0]), 37)
        self.assertEqual(len(app["commands"]), 1)
        self.assertEqual(self.env.visited, {(1, 2)})
        obs["cam_left"].fill(0)
        self.env.visited.clear()
        obs, _ = restore(snp, self.env)
        self.assertEqual(int(obs["cam_left"][0, 0, 0]), 37)
        self.assertEqual(self.env.visited, {(1, 2)})

    def test_rngs_and_mutable_model_arrays_restore(self):
        snp = self.snapshot()
        expected = (random.random(), self.np.random.random(), self.env.np_random.random())
        self.env.model.jnt_range[:] = [3., 4.]
        self.env.model.geom_rgba[:] = 0.
        self.env.model.site_pos[:] = 12.
        restore(snp, self.env)
        self.assertEqual(expected, (random.random(), self.np.random.random(), self.env.np_random.random()))
        self.np.testing.assert_array_equal(self.env.model.site_pos[0], [1., 0., 0.])
        self.assertGreater(float(self.env.model.geom_rgba[0, 3]), 0.)

    def test_invalid_snapshot_rejected_without_source_mutation(self):
        snp = self.snapshot()
        for change in (lambda s: s.update(schema_version=999),
                       lambda s: s["identity"].update(model_sha256="0" * 64),
                       lambda s: s.update(native_data=b"invalid")):
            bad = copy.deepcopy(snp)
            change(bad)
            before = self.env.data.__getstate__()
            with self.assertRaises(ValueError):
                restore(bad, self.env)
            self.assertEqual(self.env.data.__getstate__(), before)

    def test_model_and_profile_mismatch_rejected(self):
        snp = self.snapshot()
        self.env.model.geom_size[0, 0] = .2
        with self.assertRaisesRegex(ValueError, "identity"):
            restore(snp, self.env)

    def test_malformed_scalar_state_rejected_without_mutation(self):
        self.env._action_scale = 2.
        snp = self.snapshot()
        for name, value in (("_speed", "fast"), ("_speed", False), ("_speed", self.np.float32("nan")),
                            ("_action_scale", 0.), ("_action_scale", -.1), ("_t", True)):
            bad = copy.deepcopy(snp)
            bad["environment"]["values"][name] = value
            before = self.env.data.__getstate__()
            with self.assertRaises(ValueError):
                restore(bad, self.env)
            self.assertEqual(self.env.data.__getstate__(), before)

    def test_safe_exclusive_disk_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot-v1.snp"
            save_snapshot(self.snapshot(), path)
            with self.assertRaises(FileExistsError):
                save_snapshot(self.snapshot(), path)
            loaded = read_snapshot(path)
            obs, app = restore(loaded, self.env)
            self.assertEqual(app, self.app)
            self.np.testing.assert_array_equal(obs["cam_left"], self.obs["cam_left"])

    def test_object_arrays_and_arbitrary_objects_rejected(self):
        for value in (object(), self.np.array([object()], dtype=object)):
            with self.assertRaises((TypeError, ValueError)):
                capture(self.env, self.obs, application={"bad": value})

    def test_disk_rejects_huge_array_header_before_allocation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.snp"
            save_snapshot(self.snapshot(), path)
            with zipfile.ZipFile(path) as archive:
                payloads = {name: archive.read(name) for name in archive.namelist()}
            metadata = json.loads(payloads["metadata.json"])
            # Locate the integration audit's reference in the typed root dict.
            node = dict(metadata["container"]["items"])["integration"]
            buffer = io.BytesIO()
            self.np.lib.format.write_array_header_1_0(buffer,
                {"descr": "<f8", "fortran_order": False, "shape": (2**60,)})
            payloads[node["entry"]] = buffer.getvalue()
            node["size"] = len(buffer.getvalue())
            node["sha256"] = hashlib.sha256(buffer.getvalue()).hexdigest()
            payloads["metadata.json"] = json.dumps(metadata).encode()
            invalid = Path(tmp) / "invalid.snp"
            with zipfile.ZipFile(invalid, "w") as archive:
                for name, payload in payloads.items():
                    archive.writestr(name, payload)
            with self.assertRaisesRegex(ValueError, "byte count"):
                read_snapshot(invalid)


@unittest.skipUnless(HAS_SIM and os.environ.get("PALIMPSEST_SIMULATION_TESTS") == "1",
                     "opt-in actual upstream EGL continuation: PALIMPSEST_SIMULATION_TESTS=1")
class TeacherContinuation(unittest.TestCase):
    def _actual_scene(self, max_steps=600, teacher_options=None):
        from palimpsest.flynn import import_upstream
        env_class = import_upstream(REPO, "environment.mujoco_two_cam_env_random_obstacles").MuJoCoTwoCamEnv
        teacher_class = import_upstream(REPO, "agents.teacher_analytic_agent").PlannerAnalyticTeacher
        env = env_class(width=32, height=32, n_obstacles=2, frame_skip=2,
                        max_episode_steps=max_steps)
        self.addCleanup(lambda: env.renderer.close())
        teacher = teacher_class(arena_half_extent=env.arena, device="cpu", **(teacher_options or {}))
        observation = env.reset(seed=19)
        return env, teacher, observation

    def _transition(self, env, teacher):
        import mujoco
        import numpy as np
        action = teacher.act(env)
        observation, reward, done, trunc, info = env.step(action)
        integration = np.empty(mujoco.mj_stateSize(env.model, mujoco.mjtState.mjSTATE_INTEGRATION))
        mujoco.mj_getState(env.model, env.data, integration, mujoco.mjtState.mjSTATE_INTEGRATION)
        return {"action": action.copy(), "observation": observation, "reward": reward,
                "done": done, "trunc": trunc, "info": info, "integration": integration,
                "xpos": env.data.xpos.copy(), "contact_positions": env.data.contact.pos.copy(),
                "visited": env.visited.copy(), "teacher": copy.deepcopy({
                    "phase": teacher._rec_phase, "count": teacher._rec_step_count,
                    "direction": teacher._rec_turn_dir, "contact_edge": teacher._prev_bad_contact,
                    "contact_point": teacher.contact_point, "contact_angle": teacher.contact_angle,
                    "xy_prev": teacher._xy_prev, "path": teacher._path,
                    "pid_integral": teacher.pid_state.integral, "pid_error": teacher.pid_state.last_error,
                    "steering": teacher.planner.prev_steering_dir, "path_direction": teacher.planner.prev_path_dir})}

    def _same_transition(self, actual, expected):
        import numpy as np
        for key in ("action", "integration", "xpos", "contact_positions"):
            np.testing.assert_array_equal(actual[key], expected[key], err_msg=key)
        for key in ("reward", "done", "trunc", "visited", "info"):
            self.assertEqual(actual[key], expected[key], key)
        for key, value in expected["observation"].items():
            if key == "sensors":
                for name, sensor in value.items():
                    np.testing.assert_array_equal(actual["observation"][key][name], sensor, err_msg=name)
            else:
                np.testing.assert_array_equal(actual["observation"][key], value, err_msg=key)
        for key, value in expected["teacher"].items():
            np.testing.assert_array_equal(actual["teacher"][key], value, err_msg=key)

    def test_real_active_contact_and_recovery_continue_through_phase_exit(self):
        import mujoco
        import numpy as np
        options = {"recovery_back_steps": 2, "recovery_turn_steps": 2}
        env, teacher, _ = self._actual_scene(teacher_options=options)
        # Real overlap/contact, not a synthetic recovery flag or mocked sensor.
        obstacle = env._obstacle_xy[0]
        env.place_robot(float(obstacle[0]), float(obstacle[1]), 0.,
                        env.data.qpos.copy(), env.data.qvel.copy())
        mujoco.mj_forward(env.model, env.data)
        self.assertTrue(env._has_collision()[0])
        first = self._transition(env, teacher)
        self.assertEqual(teacher._rec_phase, "back")
        self.assertEqual(teacher._rec_step_count, 1)
        self.assertTrue(teacher._prev_bad_contact)
        self.assertGreater(env.data.ncon, 0)
        snapshot = capture(env, first["observation"], teacher=teacher,
                           application={"next_tick": 1, "phase": "paused"})
        expected = [self._transition(env, teacher) for _ in range(4)]
        self.assertTrue(any(row["teacher"]["phase"] is None for row in expected))
        destination, other_teacher, _ = self._actual_scene(teacher_options=options)
        observation, application = restore(snapshot, destination, teacher=other_teacher)
        self.assertEqual(application, {"next_tick": 1, "phase": "paused"})
        np.testing.assert_array_equal(observation["cam_right"], first["observation"]["cam_right"])
        self.assertEqual(other_teacher._rec_step_count, 1)
        self.assertTrue(other_teacher._prev_bad_contact)
        for row in expected:
            self._same_transition(self._transition(destination, other_teacher), row)

    def test_goal_termination_and_time_limit_crossing_match_after_restore(self):
        import mujoco
        import numpy as np
        for reason in ("goal", "time_limit"):
            with self.subTest(reason=reason):
                max_steps = 3 if reason == "time_limit" else 600
                env, teacher, _ = self._actual_scene(max_steps=max_steps)
                prefix = [self._transition(env, teacher) for _ in range(2)]
                self.assertFalse(prefix[-1]["done"] or prefix[-1]["trunc"])
                observation = prefix[-1]["observation"]
                if reason == "goal":
                    env._goal_xy[:] = env._base_xy().astype(np.float32)
                    env.model.site_pos[env.goal_site_id, :2] = env._goal_xy
                    mujoco.mj_forward(env.model, env.data)
                    observation = env._get_obs()
                snapshot = capture(env, observation, teacher=teacher,
                    application={"next_tick": 2, "phase": "paused", "terminal": False})
                expected = self._transition(env, teacher)
                self.assertEqual((bool(expected["done"]), bool(expected["trunc"])),
                                 (reason == "goal", reason == "time_limit"))
                destination, other_teacher, _ = self._actual_scene(max_steps=max_steps)
                _, application = restore(snapshot, destination, teacher=other_teacher)
                self.assertFalse(application["terminal"])
                self._same_transition(self._transition(destination, other_teacher), expected)

    def test_actual_environment_teacher_continuation(self):
        import numpy as np
        from palimpsest.flynn import import_upstream
        env_class = import_upstream(REPO, "environment.mujoco_two_cam_env_random_obstacles").MuJoCoTwoCamEnv
        teacher_class = import_upstream(REPO, "agents.teacher_analytic_agent").PlannerAnalyticTeacher
        env = env_class(width=32, height=32, n_obstacles=2, frame_skip=2)
        self.addCleanup(lambda: env.renderer.close())
        teacher = teacher_class(arena_half_extent=env.arena, device="cpu")
        observation = env.reset(seed=19)
        for _ in range(3):
            observation, *_ = env.step(teacher.act(env))
        teacher.pid_state.integral = .31
        teacher.pid_state.last_error = -.2
        snapshot = capture(env, observation, teacher=teacher, application={"next_tick": 3})
        expected = []
        for _ in range(4):
            action = teacher.act(env)
            observation, reward, done, trunc, _ = env.step(action)
            expected.append((action.copy(), observation, reward, done, trunc, env.data.qpos.copy()))
        # Restore into a separately constructed scene/controller with another
        # seeded layout, not just rewind the original Python objects.
        destination = env_class(width=32, height=32, n_obstacles=2, frame_skip=2)
        self.addCleanup(lambda: destination.renderer.close())
        destination.reset(seed=73)
        destination_teacher = teacher_class(arena_half_extent=destination.arena, device="cpu")
        for field, value in (("integral", "invalid"), ("last_error", np.float32("nan"))):
            invalid = copy.deepcopy(snapshot)
            invalid["teacher"]["pid"]["values"][field] = value
            before = destination.data.__getstate__()
            with self.assertRaisesRegex(ValueError, "numeric"):
                restore(invalid, destination, teacher=destination_teacher)
            self.assertEqual(destination.data.__getstate__(), before)
        invalid = copy.deepcopy(snapshot)
        invalid["teacher"]["state"]["values"]["_rec_phase"] = "unknown"
        with self.assertRaisesRegex(ValueError, "recovery"):
            restore(invalid, destination, teacher=destination_teacher)
        restore(snapshot, destination, teacher=destination_teacher)
        self.assertEqual(destination_teacher.pid_state.integral, .31)
        for action, observation, reward, done, trunc, qpos in expected:
            np.testing.assert_array_equal(destination_teacher.act(destination), action)
            actual, r, d, t, _ = destination.step(action)
            np.testing.assert_array_equal(actual["cam_left"], observation["cam_left"])
            np.testing.assert_array_equal(actual["cam_right"], observation["cam_right"])
            np.testing.assert_array_equal(destination.data.qpos, qpos)
            self.assertEqual((r, d, t), (reward, done, trunc))


@unittest.skipUnless(HAS_SIM and importlib.util.find_spec("torch") and importlib.util.find_spec("pandas"),
                     "upstream tiny Flynn fixture requires simulation dependencies")
class FlynnContinuation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Reuse the real upstream 12-neuron graph fixture, never mock the cell.
        import test_flynn
        cls.fixture = test_flynn.FlynnTests
        cls.fixture.setUpClass()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.tearDownClass()

    def setUp(self):
        PhysicsSnapshots.setUp(self)
        fixture = self.fixture(methodName="test_loader_records_order_and_structural_identity")
        fixture.setUp()
        self.policy, self.obs = fixture.policy, fixture.obs

    def test_real_upstream_hidden_retina_and_torch_rng_continue(self):
        import torch
        self.policy.act(self.obs)
        self.obs["cam_left"].fill(23)
        self.policy.act(self.obs)
        snp = capture(self.env, self.obs, policy=self.policy, application=self.app)
        expected_draw = torch.rand(4)
        expected = []
        for intensity in (200, 39, 172):
            self.obs["cam_left"].fill(intensity)
            result = self.policy.act(self.obs)
            expected.append((result, self.policy._state()))
        obs, _ = restore(snp, self.env, policy=self.policy)
        self.assertTrue(torch.equal(torch.rand(4), expected_draw))
        for intensity, (result, state) in zip((200, 39, 172), expected):
            obs["cam_left"].fill(intensity)
            actual = self.policy.act(obs)
            for key in ("encoded_input", "raw_output", "action"):
                self.np.testing.assert_array_equal(actual[key], result[key])
            self.assertTrue(torch.equal(self.policy.hidden, state[0]))
            for index, name in ((1, "state_vision_left"), (2, "state_vision_right")):
                for layer, value in getattr(self.policy.agent, name).items():
                    self.assertTrue(torch.equal(value, state[index][layer]))

    def test_bad_recurrent_shape_rejected_without_mutation(self):
        snp = capture(self.env, self.obs, policy=self.policy, application=self.app)
        snp["policy"]["hidden"] = self.np.zeros((1, 11), dtype=self.np.float32)
        native, hidden = self.env.data.__getstate__(), self.policy.hidden.clone()
        with self.assertRaisesRegex(ValueError, "tensor"):
            restore(snp, self.env, policy=self.policy)
        self.assertEqual(self.env.data.__getstate__(), native)
        self.assertTrue(self.policy.torch.equal(self.policy.hidden, hidden))

    def test_pre_act_snapshot_preserves_none_retinas(self):
        self.assertEqual(self.policy.failure_diagnostics, {})
        snp = capture(self.env, self.obs, policy=self.policy, application=self.app)
        expected = self.policy.act(self.obs)
        restore(snp, self.env, policy=self.policy)
        self.assertIsNone(self.policy.agent.state_vision_left)
        self.assertIsNone(self.policy.agent.state_vision_right)
        actual = self.policy.act(self.obs)
        self.np.testing.assert_array_equal(actual["action"], expected["action"])

    def test_numeric_profile_binds_cuda_flags_without_initializing_cuda(self):
        torch = self.policy.torch
        initialized = torch.cuda.is_initialized()
        snp = capture(self.env, self.obs, policy=self.policy, application=self.app)
        profile = snp["identity"]["torch"]
        self.assertEqual(profile["cuda_runtime"], torch.version.cuda)
        self.assertIn("cudnn_version", profile)
        self.assertEqual(torch.cuda.is_initialized(), initialized)
        for name in ("CUBLAS_WORKSPACE_CONFIG", "CUDA_VISIBLE_DEVICES", "NVIDIA_TF32_OVERRIDE"):
            self.assertEqual(profile[name], os.environ.get(name))
            with patch.dict(os.environ, {name: "snapshot-mismatch"}):
                native = self.env.data.__getstate__()
                with self.assertRaisesRegex(ValueError, "identity"):
                    restore(snp, self.env, policy=self.policy)
                self.assertEqual(self.env.data.__getstate__(), native)
                self.assertEqual(torch.cuda.is_initialized(), initialized)


if __name__ == "__main__":
    unittest.main()
