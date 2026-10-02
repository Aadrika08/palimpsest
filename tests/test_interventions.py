import json
import os
from pathlib import Path
import pickle
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

from palimpsest.interventions import apply_intervention


class FixtureModel:
    def __init__(self):
        self.jnt_qposadr = np.array([0, 7, 8, 9, 10])
        self.jnt_dofadr = np.array([0, 6, 7, 8, 9])
        self.jnt_range = np.array([[0, 0], [-2.0001, -1.9999], [-.0001, .0001],
                                   [1.9999, 2.0001], [-.0001, .0001]])
        self.geom_size = np.array([[.4, .8, 0], [.4, .8, 0]])
        self.geom_type = np.array([5, 5])  # MuJoCo cylinders.
        self.site_pos = np.array([[0., 4., .25]])
        self.site_size = np.array([[.25, .25, .25]])

    def joint(self, name):
        if name != 'base_free':
            raise KeyError(name)
        return SimpleNamespace(id=0)


def fixture():
    qpos = np.zeros(11)
    qpos[3] = 1
    qpos[7:] = [-2, 0, 2, 0]
    env = SimpleNamespace(model=FixtureModel(), data=SimpleNamespace(qpos=qpos, qvel=np.arange(10.),
                          xpos=np.array([[0., 0., .1]]), time=1.25), arena=7., n_obstacles=2,
                          obstacle_ids=[0, 1], obstacle_x_joint_ids=[1, 3], obstacle_y_joint_ids=[2, 4],
                          _obstacle_x_qposadr=np.array([7, 9]), _obstacle_y_qposadr=np.array([8, 10]),
                          _obstacle_xy=np.array([[-2, 0], [2, 0]], dtype=np.float32),
                          _goal_xy=np.array([0, 4], dtype=np.float32), goal_site_id=0, goal_radius=.8,
                          path_to_draw=[1, 2], target_to_draw=[3, 4],
                          planner=SimpleNamespace(_cached_occ=np.ones((2, 2)), _cached_obstacles_hash=42,
                                                  _cached_clearance=np.ones((2, 2))))
    teacher = SimpleNamespace(_path=[1, 2], _rec_phase='back', _rec_step_count=7,
                              pid_state={'integral': 2}, planner=SimpleNamespace(prev_steering_dir=.2,
                                                                                prev_path_dir=.3))
    return env, teacher


class InterventionTests(unittest.TestCase):
    def setUp(self):
        self.env, self.teacher = fixture()
        self.forward = Mock()
        loader = patch('palimpsest.interventions.importlib.import_module',
                       return_value=SimpleNamespace(mj_forward=self.forward))
        loader.start()
        self.addCleanup(loader.stop)

    def test_rejected_inputs_leave_every_fixture_field_unchanged(self):
        invalid = [None, {}, {'kind': 'unknown', 'xy': [1, 2]},
                   {'kind': 'move_goal', 'xy': [1, 2], 'extra': True},
                   {'kind': 'move_obstacle', 'xy': [1, 2]},
                   {'kind': 'move_goal', 'xy': [0, 0]},
                   {'kind': 'move_goal', 'xy': [2, 0]},
                   {'kind': 'move_obstacle', 'index': 0, 'xy': [0, 0]},
                   {'kind': 'move_obstacle', 'index': 0, 'xy': [2, 0]},
                   {'kind': 'move_obstacle', 'index': 0, 'xy': [0, 4]},
                   {'kind': 'move_obstacle', 'index': 0, 'xy': [6.6, 0]}]
        for xy in ([float('nan'), 1], [float('inf'), 1], [True, 1], ['1', 1], [1], [1, 2, 3],
                   [7, 0], [10**1000, 0]):
            invalid.append({'kind': 'move_goal', 'xy': xy})
        for index in (-1, 2, True, 0., '0'):
            invalid.append({'kind': 'move_obstacle', 'index': index, 'xy': [-3, 3]})
        for command in invalid:
            with self.subTest(command=command):
                before = pickle.dumps((self.env, self.teacher))
                with self.assertRaises(ValueError):
                    apply_intervention(self.env, command, self.teacher)
                self.assertEqual(pickle.dumps((self.env, self.teacher)), before)
        self.forward.assert_not_called()

    def test_obstacle_edit_updates_locked_physics_and_caches_without_step(self):
        qpos, qvel, ranges = self.env.data.qpos.copy(), self.env.data.qvel.copy(), self.env.model.jnt_range.copy()
        event = apply_intervention(self.env, {'kind': 'move_obstacle', 'index': 0, 'xy': [-3, 3]}, self.teacher)
        np.testing.assert_array_equal(self.env.data.qpos[7:9], [-3, 3])
        np.testing.assert_array_equal(self.env._obstacle_xy[0], [-3, 3])
        np.testing.assert_allclose(self.env.model.jnt_range[1:3], [[-3.0001, -2.9999], [2.9999, 3.0001]])
        np.testing.assert_array_equal(self.env.data.qvel[6:8], [0, 0])
        np.testing.assert_array_equal(self.env.data.qvel[:6], qvel[:6])
        np.testing.assert_array_equal(self.env.data.qvel[8:], qvel[8:])
        np.testing.assert_array_equal(self.env.data.qpos[:7], qpos[:7])
        np.testing.assert_array_equal(self.env.model.jnt_range[3:], ranges[3:])
        self.forward.assert_called_once_with(self.env.model, self.env.data)
        self.assertEqual(self.env.data.time, 1.25)
        self.assertEqual(event['old']['xy'], [-2, 0])
        self.assertEqual(event['new']['xy'], [-3, 3])
        json.dumps(event, allow_nan=False)
        for name in ('_cached_occ', '_cached_obstacles_hash', '_cached_clearance'):
            self.assertIsNone(getattr(self.env.planner, name))
        self.assertIsNone(self.env.path_to_draw)
        self.assertIsNone(self.env.target_to_draw)
        self.assertIsNone(self.teacher._path)
        self.assertEqual(self.teacher._rec_phase, 'back')
        self.assertEqual(self.teacher._rec_step_count, 7)
        self.assertEqual(self.teacher.pid_state, {'integral': 2})
        self.assertEqual(self.teacher.planner.prev_steering_dir, .2)
        self.assertEqual(self.teacher.planner.prev_path_dir, .3)

    def test_preview_validates_geometry_and_leaves_all_state_unchanged(self):
        before = pickle.dumps((self.env, self.teacher))
        change = {'kind': 'move_obstacle', 'index': 0, 'xy': [-3, 3]}
        preview = apply_intervention(self.env, change, self.teacher, dry_run=True)
        self.assertEqual(pickle.dumps((self.env, self.teacher)), before)
        self.forward.assert_not_called()
        self.assertEqual(apply_intervention(self.env, change, self.teacher), preview)

    def test_clearance_uses_current_qpos_not_stale_world_or_cached_positions(self):
        self.env.data.qpos[:2] = [3, 3]
        with self.assertRaisesRegex(ValueError, 'rover'):
            apply_intervention(self.env, {'kind': 'move_obstacle', 'index': 0, 'xy': [3, 3]})
        self.env.data.qpos[9:11] = [-3, 3]
        with self.assertRaisesRegex(ValueError, 'obstacle'):
            apply_intervention(self.env, {'kind': 'move_goal', 'xy': [-3, 3]})

    def test_goal_geometry_and_declared_cue_match_and_nearby_goal_is_allowed(self):
        qpos, qvel = self.env.data.qpos.copy(), self.env.data.qvel.copy()
        event = apply_intervention(self.env, {'kind': 'move_goal', 'xy': [.7, 0]}, self.teacher)
        np.testing.assert_array_equal(self.env.model.site_pos[0, :2], self.env._goal_xy)
        self.assertEqual(self.env.model.site_pos[0, 2], .25)
        np.testing.assert_array_equal(self.env.data.qpos, qpos)
        np.testing.assert_array_equal(self.env.data.qvel, qvel)
        self.assertEqual(event['old']['xy'], [0, 4])
        self.assertEqual(event['new']['xy'], list(map(float, self.env._goal_xy)))
        self.forward.assert_called_once_with(self.env.model, self.env.data)
        self.assertEqual(self.env.data.time, 1.25)


@unittest.skipUnless(os.environ.get('PALIMPSEST_SIMULATION_TESTS') == '1',
                     'opt in with PALIMPSEST_SIMULATION_TESTS=1 and a working renderer')
class SimulationInterventionTests(unittest.TestCase):
    def test_real_upstream_edit_forwards_geometry_and_persists_after_step(self):
        from palimpsest.flynn import import_upstream
        root = Path(__file__).resolve().parents[1]
        cls = import_upstream(root, 'environment.mujoco_two_cam_env_random_obstacles').MuJoCoTwoCamEnv
        env = cls(width=32, height=32, n_obstacles=20, arena_half_extent=7, seed=5)
        try:
            before = env.data.time
            for x in (-5.5, -3, 0, 3, 5.5):
                for y in (-5.5, -3, 0, 3, 5.5):
                    try:
                        event = apply_intervention(env, {'kind': 'move_obstacle', 'index': 0, 'xy': [x, y]})
                        break
                    except ValueError:
                        continue
                else:
                    continue
                break
            else:
                self.fail('fixture layout has no valid obstacle destination')
            self.assertEqual(env.data.time, before)
            xy = event['new']['xy']
            np.testing.assert_allclose(env.data.geom_xpos[env.obstacle_ids[0], :2], xy)
            env.step(np.zeros(2, dtype=np.float32))
            np.testing.assert_allclose(env.data.geom_xpos[env.obstacle_ids[0], :2], xy, atol=1e-3)
            self.assertGreater(env.data.time, before)
        finally:
            env.renderer.close()
            env.close()


if __name__ == '__main__':
    unittest.main()
