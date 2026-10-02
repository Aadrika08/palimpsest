"""Synthetic declared-sensor/lifecycle checks; no EGL or trained model."""

import copy
import importlib
import importlib.util
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from palimpsest.engine import Engine
from palimpsest.records import RunWriter, iter_ticks
from test_engine import SmallEnv, SmallPolicy


class TaskProfileTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.task_profiles'),
                             'declared exploration/homing runtime profiles are missing')
        self.t = importlib.import_module('palimpsest.task_profiles')
        self.calibration = {'radius_m': .1, 'track_m': .4, 'quantum_rad': .001}

    def state(self, scenario='exploration-landmarks'):
        return self.t.initialize(scenario, 'episode-0', [0., 0.], self.calibration)

    def packet(self, tick, angles=(0., 0.), landmarks=None):
        return {'version': 1, 'episode_id': 'episode-0', 'tick': tick,
                'time_s': tick * .02, 'angles_rad': list(angles),
                'landmarks': [{'id': 'inspect-a', 'bearing_rad': .1, 'near': False},
                              {'id': 'inspect-b', 'bearing_rad': .2, 'near': False}]
                             if landmarks is None else landmarks}

    def test_exploration_retains_target_requires_stopped_dwell_and_completes(self):
        state = self.state()
        original = copy.deepcopy(state)
        state, cue, hold, events = self.t.advance(state, self.packet(0))
        self.assertEqual(state['active'], 'inspect-a')
        self.assertFalse(hold)
        self.assertEqual(state['completed_ids'], [])
        near = [{'id': 'inspect-a', 'bearing_rad': .1, 'near': True},
                {'id': 'inspect-b', 'bearing_rad': .2, 'near': False}]
        state, _, hold, _ = self.t.advance(state, self.packet(1, (.1, .1), near))
        self.assertTrue(hold)
        self.assertEqual(state['dwell_ticks'], 0)
        for tick in range(2, 7):
            state, _, hold, _ = self.t.advance(state, self.packet(tick, (.1, .1), near))
        self.assertEqual(state['completed_ids'], ['inspect-a'])
        self.assertIsNone(state['active'])
        state, _, hold, _ = self.t.advance(state, self.packet(7, (.1, .1), near))
        self.assertEqual(state['active'], 'inspect-b')
        self.assertFalse(hold)
        near_b = [{'id': 'inspect-b', 'bearing_rad': .2, 'near': True}]
        for tick in range(8, 13):
            state, _, hold, _ = self.t.advance(state, self.packet(tick, (.1, .1), near_b))
        self.assertEqual(state['phase'], 'complete')
        self.assertTrue(hold)
        self.assertEqual(state['completed_ids'], ['inspect-a', 'inspect-b'])
        self.assertEqual(original['active'], None)
        json.dumps(state, allow_nan=False)

    def test_missing_target_stale_packets_and_invalid_encoders_fail(self):
        state, *_ = self.t.advance(self.state(), self.packet(0))
        for packet in (self.packet(1, landmarks=[]), self.packet(0),
                       self.packet(2), self.packet(1, (float('nan'), 0.)),
                       self.packet(1, (100., 100.)), self.packet(1) | {'time_s': 0.},
                       self.packet(1) | {'true_pose': [0., 0., 0.]}):
            with self.subTest(packet=packet), self.assertRaises(ValueError):
                self.t.advance(state, packet)
        with self.assertRaises(ValueError):
            self.t.advance(self.state(), self.packet(0, landmarks=[]))

    def test_homing_transitions_only_after_encoder_departure_and_returns_by_estimate(self):
        state, cue, hold, _ = self.t.advance(self.state('encoder-homing'), self.packet(0, landmarks=[]))
        self.assertEqual(state['phase'], 'outbound')
        self.assertFalse(hold)
        state, _, _, _ = self.t.advance(state, self.packet(1, (5., 5.), []))
        state, cue, hold, events = self.t.advance(state, self.packet(2, (10., 10.), []))
        self.assertEqual(state['phase'], 'home')
        self.assertAlmostEqual(cue[0], -1.)
        self.assertFalse(hold)
        state, _, _, _ = self.t.advance(state, self.packet(3, (5., 5.), []))
        state, _, hold, _ = self.t.advance(state, self.packet(4, (0., 0.), []))
        self.assertTrue(hold)
        self.assertEqual(state['dwell_ticks'], 0)
        for tick in range(5, 10):
            state, _, hold, _ = self.t.advance(state, self.packet(tick, (0., 0.), []))
        self.assertEqual(state['phase'], 'complete')
        self.assertTrue(hold)
        self.assertEqual(state['odometry']['x_m'], 0.)

    def test_visibility_near_bit_uses_declared_threshold_and_no_hidden_range(self):
        env = SmallEnv()
        env.data.qpos[:2] = [-1.75, 0.]
        packet = self.t.capture(env, self.state(), 0, wheel_angles=[0., 0.])
        self.assertEqual(set(packet), {'version', 'episode_id', 'tick', 'time_s', 'angles_rad', 'landmarks'})
        self.assertTrue(next(p['near'] for p in packet['landmarks'] if p['id'] == 'inspect-a'))
        self.assertFalse(next(p['near'] for p in packet['landmarks'] if p['id'] == 'inspect-b'))
        self.assertEqual(set(packet['landmarks'][0]), {'id', 'bearing_rad', 'near'})
        env.data.qpos[2] = math.pi
        self.assertNotIn('inspect-b', [p['id'] for p in self.t.capture(env, self.state(), 0, wheel_angles=[0., 0.])['landmarks']])
        env.data.qpos[:] = [-2.5, 0., 0.]
        env.data.geom_xpos[0, :2] = [-2., 0.]
        self.assertEqual(self.t.capture(env, self.state(), 0, wheel_angles=[0., 0.])['landmarks'], [])
        env.data.qpos[:] = [-5.7501, 0., 0.]
        env.data.geom_xpos[0, :2] = [2., 2.]
        self.assertEqual(self.t.capture(env, self.state(), 0, wheel_angles=[0., 0.])['landmarks'], [])

    def test_calibration_comes_from_loaded_wheel_geometry_and_rejects_unknown_signs(self):
        ids = {'left_wheel_geom': 0, 'right_wheel_geom': 1,
               'left_wheel': 0, 'right_wheel': 1}
        model = SimpleNamespace(geom=lambda name: SimpleNamespace(id=ids[name]),
            body=lambda name: SimpleNamespace(id=ids[name]),
            geom_size=np.array([[.06, .02, 0.], [.06, .02, 0.]]), geom_type=np.array([5, 5]),
            body_pos=np.array([[-.05, .18, -.05], [-.05, -.18, -.05]]),
            body_quat=np.array([[1., 0., 0., 0.], [1., 0., 0., 0.]]),
            jnt_axis=np.array([[0., 1., 0.], [0., 1., 0.]]),
            jnt_type=np.array([3, 3]), jnt_qposadr=np.array([3, 4]))
        env = SimpleNamespace(model=model, left_hinge_id=0, right_hinge_id=1,
                              data=SimpleNamespace(qpos=np.array([9., 9., 9., .2, -.3])))
        self.assertEqual(self.t.body_calibration(env), {'radius_m': .06, 'track_m': .36, 'quantum_rad': .001})
        self.assertEqual(self.t.encoder_angles(env), [.2, -.3])
        model.jnt_axis[0, 1] = -1.
        with self.assertRaises(ValueError):
            self.t.body_calibration(env)


class TaskEngineTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.task_profiles'))
        self.t = importlib.import_module('palimpsest.task_profiles')
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engines = []
        self.addCleanup(lambda: [e.close() for e in self.engines])
        self.addCleanup(patch.stopall)
        patch('palimpsest.task_profiles.configure_world', side_effect=lambda env: None).start()
        patch('palimpsest.task_profiles.body_calibration', return_value={
            'radius_m': .1, 'track_m': .4, 'quantum_rad': .001}).start()
        patch('palimpsest.task_profiles.encoder_angles', side_effect=lambda env: env.encoder.copy()).start()

    def engine(self, name, scenario='encoder-homing', policy=None):
        env = SmallEnv(terminate_at=1)
        env.encoder = [0., 0.]
        writer = RunWriter(self.root / name, {'run_id': name})
        engine = Engine(env, writer, scenario=scenario,
                        controller='flynn' if policy else 'manual', policy=policy)
        self.engines.append(engine)
        return engine

    def step(self, engine, name):
        engine.submit({'id': name, 'kind': 'step', 'expected_state': 'paused', 'expected_episode': engine.episode})
        return engine.advance()

    def test_homing_allowlist_replaces_privileged_bearing_and_ignores_upstream_goal(self):
        policy = SmallPolicy()
        engine = self.engine('source', policy=policy)
        engine.observation['sensors']['wind_direction'] = [0., 1.]
        self.assertEqual(self.step(engine, 's0')['phase'], 'paused')
        self.assertEqual(set(policy.seen['sensors']), {'collision', 'collision_angle', 'wind_direction'})
        self.assertEqual(policy.seen['sensors']['wind_direction'], [1., 0.])
        engine.env.encoder = [5., 5.]
        self.step(engine, 's1')
        engine.env.encoder = [10., 10.]
        self.step(engine, 's2')
        self.assertAlmostEqual(policy.seen['sensors']['wind_direction'][0], -1.)
        self.assertEqual(engine.task_state['phase'], 'home')
        engine.close()
        self.assertEqual(len(list(iter_ticks(self.root / 'source'))), 3)

    def test_failure_clears_motor_control_before_another_physics_step(self):
        engine = self.engine('failure')
        self.step(engine, 's0')
        engine.env.data.ctrl[:] = 1.
        engine.env.encoder = [float('nan'), 0.]
        self.assertEqual(self.step(engine, 's1')['phase'], 'failed')
        self.assertEqual(engine.env.calls, 1)
        np.testing.assert_array_equal(engine.env.data.ctrl, [0., 0.])

    def test_application_restore_retains_task_cursor_and_rejects_tampering(self):
        source = self.engine('source')
        self.step(source, 's0')
        source.env.encoder = [2., 2.]
        self.step(source, 's1')
        app = source.application_state()
        branch = self.engine('branch')
        for task in (None, app['task_state'] | {'last_tick': 8},
                     app['task_state'] | {'profile_sha256': '0' * 64}):
            with self.assertRaises(ValueError):
                branch.validate_application(app | {'task_state': task})
        branch.restore_application(json.loads(json.dumps(app)))
        branch.env.data.time = source.env.data.time
        branch.env.encoder = [3., 3.]
        source.env.encoder = [3., 3.]
        self.step(source, 's2')
        self.step(branch, 'b2')
        self.assertEqual(source.task_state, branch.task_state)
        branch.submit({'id': 'reset', 'kind': 'reset', 'expected_state': 'paused', 'expected_episode': 0})
        branch.env.encoder = [0., 0.]
        branch.advance()
        self.assertEqual(branch.task_state['episode_id'], 'episode-1')
        self.assertIsNone(branch.task_state['last_tick'])
        self.assertEqual(branch.task_state['odometry']['x_m'], 0.)

    def test_profile_protocol_and_replay_register_tasks(self):
        from palimpsest.profiles import validate
        from palimpsest import replay
        for scenario in self.t.SCENARIOS:
            profile = validate(scenario, 'checker', 'flynn')
            self.assertIn('task_protocol_sha256', profile)
            with self.assertRaises(ValueError):
                validate(scenario, 'checker', 'teacher')
        self.assertIn('src/palimpsest/task_profiles.py', replay._RUNTIME)
        self.assertIn('src/palimpsest/task_mechanics.py', replay._RUNTIME)
        self.assertTrue({'task_sensed', 'task_decision', 'task_cue', 'task_inspected'} <= replay._EVENTS)

    def test_exploration_enforces_hold_retains_target_and_has_its_own_completion(self):
        engine = self.engine('exploration', scenario='exploration-landmarks', policy=SmallPolicy())
        engine.env.data.qpos[:] = [-2.5, 0., 0.]
        self.assertEqual(self.step(engine, 'initial')['phase'], 'paused')
        self.assertEqual(engine.task_state['active'], 'inspect-a')
        engine.env.data.qpos[:2] = [-1.75, 0.]
        engine.env.encoder = [.1, .1]
        self.step(engine, 'near-a')
        self.assertEqual(engine.task_state['dwell_ticks'], 0)
        np.testing.assert_array_equal(engine.last_transition['action'], [0., 0.])
        for tick in range(5):
            self.step(engine, f'a-dwell-{tick}')
        self.assertEqual(engine.task_state['completed_ids'], ['inspect-a'])
        self.step(engine, 'select-b')
        self.assertEqual(engine.task_state['active'], 'inspect-b')
        engine.env.data.qpos[:2] = [-1., 0.]
        engine.env.encoder = [.2, .2]
        self.step(engine, 'near-b')
        for tick in range(5):
            self.step(engine, f'b-dwell-{tick}')
        self.assertEqual(engine.phase, 'terminated')
        self.assertEqual(engine.last_outcome['reason'], 'task_completed')
        self.assertEqual(engine.task_state['completed_ids'], ['inspect-a', 'inspect-b'])
        np.testing.assert_array_equal(engine.env.data.ctrl, [0., 0.])
        calls = engine.env.calls
        engine.advance()
        self.assertEqual(engine.env.calls, calls)

    def test_worker_hides_unreplaced_goal_bearing_until_next_owned_tick(self):
        from palimpsest.worker import _sample
        engine = self.engine('sample')
        sample = _sample(engine, engine.run_id, [], 0.)
        self.assertEqual(sample['inputs']['stage'], 'pending-task')
        self.assertEqual(sample['inputs']['sensors'][2:], [None, None])
        self.assertEqual(sample['task'], engine.task_state)
        self.step(engine, 's0')
        sample = _sample(engine, engine.run_id, [], 0.)
        self.assertEqual(sample['inputs']['sensors'][2:], [1., 0.])

    def test_action_replay_bypasses_inference_but_cannot_override_dwell(self):
        policy = SmallPolicy()
        engine = self.engine('actions', scenario='exploration-landmarks', policy=policy)
        engine.env.data.qpos[:] = [-1.75, 0., 0.]
        engine.submit({'id': 's0', 'kind': 'step', 'expected_state': 'paused', 'expected_episode': 0})
        self.assertEqual(engine.advance(action_override=[0., 0.])['phase'], 'paused')
        self.assertIsNone(policy.seen)
        engine.submit({'id': 's1', 'kind': 'step', 'expected_state': 'paused', 'expected_episode': 0})
        self.assertEqual(engine.advance(action_override=[.1, 0.])['phase'], 'failed')
        self.assertIn('stopped-dwell', engine.last_outcome['message'])
        self.assertEqual(engine.env.calls, 1)
        np.testing.assert_array_equal(engine.env.data.ctrl, [0., 0.])

    def test_contact_at_acquisition_halts_without_an_extra_world_step(self):
        engine = self.engine('contact')
        engine.observation['sensors']['collision'] = True
        engine.env.data.ctrl[:] = 1.
        self.assertEqual(self.step(engine, 's0')['phase'], 'failed')
        self.assertEqual(engine.env.calls, 0)
        np.testing.assert_array_equal(engine.env.data.ctrl, [0., 0.])

    def test_paused_task_restores_same_events_and_actions_in_both_replay_modes(self):
        from palimpsest.replay import _same_json, _same_tick
        source = self.engine('source')
        self.step(source, 'prefix')
        snapshot_application = source.application_state()
        branches = [self.engine(mode) for mode in ('actions', 'policy')]
        for branch in branches:
            branch.restore_application(snapshot_application)
            branch.env.data.qpos[:] = source.env.data.qpos
            branch.env.data.time = source.env.data.time
            branch.env.calls = source.env.calls
            branch.observation = copy.deepcopy(source.observation)
        for tick, angle in enumerate([2., 4., 6.], 1):
            source.env.encoder = [angle, angle]
            self.step(source, f's{tick}')
            for branch in branches:
                branch.env.encoder = [angle, angle]
                branch.submit({'id': f'b{tick}', 'kind': 'step', 'expected_state': 'paused', 'expected_episode': 0})
                branch.advance(action_override=source.last_transition['action'] if branch.run_id == 'actions' else None)
                self.assertEqual(branch.task_state, source.task_state)
        for engine in [source, *branches]:
            engine.close()
        rows = list(iter_ticks(self.root / 'source'))[1:]
        expected_events = [json.loads(line) for line in (self.root / 'source/events.jsonl').read_text().splitlines()
                           if json.loads(line)['kind'].startswith('task_') and json.loads(line).get('episode_step', -1) >= 1]
        for branch in branches:
            for expected, actual in zip(rows, iter_ticks(self.root / branch.run_id)):
                _same_tick(expected, actual, branch.run_id, expected['tick'])
            events = [json.loads(line) for line in (self.root / branch.run_id / 'events.jsonl').read_text().splitlines()
                      if json.loads(line)['kind'].startswith('task_')]
            self.assertEqual(len(events), len(expected_events))
            for expected, actual in zip(expected_events, events):
                _same_json(expected, actual)

    def test_playback_projects_retained_task_state_from_recorded_sensor_decisions(self):
        import uuid
        from palimpsest.artifacts import playback
        run = self.root / uuid.uuid4().hex
        env = SmallEnv()
        env.encoder = [0., 0.]
        engine = Engine(env, RunWriter(run / 'recording', {'run_id': run.name,
            'controller': 'manual', 'population_names': []}), scenario='encoder-homing')
        self.engines.append(engine)
        self.step(engine, 's0')
        state = copy.deepcopy(engine.task_state)
        engine.close()
        sample = playback(run, 0, 0)
        self.assertEqual(sample['task'], state)
        self.assertEqual(sample['inputs']['sensors'][2:], [1., 0.])


if __name__ == '__main__':
    unittest.main()
