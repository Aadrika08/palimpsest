"""Pure reference-profile fixtures; synthetic native/observations, no model evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
import uuid
from unittest.mock import Mock, patch

import numpy as np

from palimpsest import memory, memory_experiment, memory_task, memory_world, snapshots
from palimpsest.engine import Engine
from palimpsest.records import RunWriter
import test_memory_flynn_admission as fixtures
from test_engine import SmallEnv, SmallPolicy


class SmallTeacher:
    device = 'cpu'

    def __init__(self):
        self.pid_state = SimpleNamespace(integral=.4, last_error=.1)
        self.planner = SimpleNamespace(primary_hist=np.array([1., 2.]), binary_hist=np.array([True, False]),
                                      prev_steering_dir=.3, prev_path_dir=.2)
        self._rec_phase, self._rec_step_count, self._rec_turn_dir = 'back', 3, -1.
        self._prev_bad_contact = True
        self.contact_point, self.contact_angle = [1., 2., 0.], .5
        self._xy_prev, self._path, self.seen = np.array([1., 2.]), [[1., 2.]], None

    def act(self, env):
        self.seen = env._obstacle_xy.copy()
        return np.array([.2, .1])


class MemoryReferences(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.FlynnMemoryAdmission('runTest')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.case = memory_experiment.make_world_case(24, 'local_cue', 'development-test',
            acquisition=True, change_tick=300)
        source = self.fixture.observed_source(self.case)
        for tick in range(2, 300):
            source.memory, _, _ = memory_task.advance_memory(source.memory, self.fixture.packet(source, tick))
        source.world_task_state['last_tick'] = 299
        source.episode_step = source.total_tick = source.revision = 300
        with patch.object(snapshots, 'restore', side_effect=lambda saved, env, **kw: (env._get_obs(), saved['application'])):
            policy = self.fixture.engine(self.case, controller='flynn',
                restore_snapshot=self.fixture.snapshot(source), replace_controller=True)
        self.source = self.fixture.snapshot(policy)
        self.source['identity'] = {'policy': {'device': 'cpu'}, 'teacher': None, 'torch': {'fixture': True}}
        self.source['rng'] = {'python': [1], 'numpy': [2], 'environment': [3], 'torch_cpu': b'fixture', 'torch_cuda': None}
        self.source['policy'] = {'hidden': np.array([.1, .2])}

    def test_fixed_reference_source_is_admitted_without_mutating_it(self):
        before = snapshots.state_digest(self.source)
        for scenario, controller, replacement in (
                ('memory-reference-original-flynn', 'flynn', False),
                ('memory-reference-sensor-only', 'manual', True),
                ('memory-reference-teacher', 'teacher', True)):
            error = None
            try:
                case, native, u = Engine._memory_restore(self.case, scenario, controller, 'cpu',
                    self.source, replacement, None)
            except ValueError as failed:
                error = str(failed)
            self.assertIsNone(error, error)
            self.assertEqual(case, self.case)
            self.assertEqual(snapshots.state_digest(native), snapshots.state_digest(self.source))
            self.assertIsNone(u)
        self.assertEqual(snapshots.state_digest(self.source), before)

    def reference_engine(self, scenario, *, capture_change=None):
        from palimpsest.memory_reference import REFERENCES
        controller = REFERENCES[scenario][0]
        env = SmallEnv()
        env.n_obstacles = 20
        env.model.geom_size = np.array([[.4, .8, 0.]] * 20)
        env.obstacle_ids = list(range(20))
        env._obstacle_xy = np.array(memory_world.validate_layout())
        env.data.geom_xpos = np.array([[*xy, .8] for xy in env._obstacle_xy])
        env.planner = SimpleNamespace(_cached_occ=[1], _cached_obstacles_hash='stale', _cached_clearance=[2])
        policy = SmallPolicy(action=(.25, -.1)) if controller == 'flynn' else None
        if policy is not None:
            policy.device = 'cpu'
        teacher = SmallTeacher() if controller == 'teacher' else None
        path = self.fixture.root / uuid.uuid4().hex
        writer = RunWriter(path / 'recording', {'run_id': path.name})
        def configure(env, state):
            env.data.qpos[:] = self.case['start_pose']
            env._goal_xy[:] = self.case['goal_xy']
            return state
        def capture(env, obs, *, application, **kwargs):
            result = copy.deepcopy(self.source)
            result['application'] = application
            if controller != 'flynn':
                result['identity'].update(policy=None, teacher={'fixture': controller}, torch={'destination': True})
                result['policy'] = None
                result['teacher'] = None if teacher is None else {'fixture': True}
                result['rng']['torch_cpu'] = b'fresh'
            if capture_change:
                capture_change(result)
            return result
        try:
            with patch.object(memory_world, 'configure', side_effect=configure), \
                    patch.object(snapshots, 'restore', side_effect=lambda saved, env, **kw: (env._get_obs(), saved['application'])), \
                    patch.object(snapshots, 'capture', side_effect=capture):
                result = Engine(env, writer, controller, policy, teacher, seed=24, scenario=scenario,
                    memory_case=self.case, restore_snapshot=self.source, replace_controller=controller != 'flynn')
        except BaseException:
            env.close()
            writer.close()
            raise
        self.fixture.engines.append(result)
        return result

    def test_invalid_reference_routes_reject_before_allocation_and_defaults_stay_closed(self):
        from palimpsest import profiles
        from palimpsest.memory_reference import REFERENCES
        for scenario, (controller, _) in REFERENCES.items():
            self.assertNotIn(scenario, profiles.SCENARIOS)
            with self.assertRaises(ValueError):
                profiles.validate(scenario, 'checker', controller)
            self.assertEqual(profiles.validate_reference(scenario, 'checker', controller)['id'], scenario)
            replacement = controller != 'flynn'
            for update in ({'restore_snapshot': None}, {'device': 'cuda'}, {'controller': 'male-original'},
                           {'replace_controller': not replacement}, {'memory_u': memory.artifact()}, {'seed': 25}):
                args = dict(controller=controller, device='cpu', scenario=scenario, seed=24,
                            memory_case=self.case, restore_snapshot=self.source, replace_controller=replacement)
                args.update(update)
                with patch('palimpsest.records.RunWriter') as writer, self.assertRaises(ValueError):
                    Engine.open(self.fixture.root, self.fixture.root, self.fixture.root / 'absent', **args)
                writer.assert_not_called()
        for mutate in (lambda n: n['application'].update(episode_step=301),
                       lambda n: n['application'].update(episode=False),
                       lambda n: n['application']['memory'].update(u=memory.artifact('local_cue')),
                       lambda n: n['application'].update(execution_mode='actions'),
                       lambda n: n['identity']['policy'].update(device='cuda'),
                       lambda n: n.update(native_sha256='0'*64)):
            bad = copy.deepcopy(self.source)
            mutate(bad)
            with self.assertRaises(ValueError):
                Engine._memory_restore(self.case, 'memory-reference-original-flynn', 'flynn', 'cpu', bad, False, None)
        with self.assertRaises(ValueError):
            profiles.validate('memory-passages', 'checker', 'teacher')

    def test_profile_transaction_preserves_memory_and_rejects_physics_or_supervisor_changes(self):
        from palimpsest import memory_reference as ref
        before = snapshots.state_digest(self.source)
        for scenario in ref.REFERENCES:
            engine = self.reference_engine(scenario)
            self.assertEqual(engine.memory, self.source['application']['memory'])
            self.assertEqual(engine.world_task_state, self.source['application']['world_task_state'])
            self.assertEqual(engine.episode_step, 300)
            self.assertEqual(engine.revision, self.source['application']['revision'] + 1)
        self.assertEqual(snapshots.state_digest(self.source), before)
        for mutation in (lambda n: n.update(native_data=b'altered'),
                         lambda n: n['rng'].update(numpy=[4]),
                         lambda n: n['application']['memory'].update(requests=[{'tampered': True}])):
            with self.assertRaisesRegex(ValueError, 'invariant'):
                self.reference_engine('memory-reference-original-flynn', capture_change=mutation)
        new = copy.deepcopy(self.source)
        new['teacher'] = {'fresh-control': True}
        self.assertNotEqual(ref.preservation_hash(new, False), ref.preservation_hash(self.source, False))
        self.assertEqual(ref.preservation_hash(new, True), ref.preservation_hash(self.source, True))

    def test_sensor_projection_uses_no_passage_map_or_private_fallback(self):
        from palimpsest import memory_reference as ref
        packet = self.fixture.packet(self.fixture.engines[-1], 300)
        original = copy.deepcopy(packet)
        inputs = ref.sensor_input(packet, False)
        self.assertEqual(set(inputs), {'bearing', 'collision'})
        self.assertEqual(ref.sensor_action(inputs)[0], .65)
        self.assertEqual(ref.sensor_action({**inputs, 'collision': True})[0], 0.)
        altered = copy.deepcopy(packet)
        altered['passages'] = [{'privileged-map': [100, 200]}]
        altered['cues'] = []
        self.assertEqual(ref.sensor_input(altered, False), inputs)
        self.assertEqual(packet, original)
        hidden = {**packet, 'landmarks': []}
        with self.assertRaises(memory_task.CueUnavailable):
            ref.sensor_input(hidden, False)
        with self.assertRaises(ValueError):
            ref.sensor_action({**inputs, 'geometry': [1, 2]})

    def step_reference(self, engine, *, hidden_goal=False, geometry_edit=True):
        packet = self.fixture.packet(engine, 300)
        if hidden_goal:
            packet['landmarks'] = []
        def advance(env, state, tick):
            state = copy.deepcopy(state)
            state['last_tick'] = tick
            state['applied'] = True
            state['cue_state'] = 1
            state['gate_result'] = 'closed'
            env._obstacle_xy[0] = [9., 8.]
            return state, ([{'kind': 'memory_gate_applied', 'intervention': {'fixture': True}}] if geometry_edit else [])
        with patch.object(memory_world, 'advance_world', side_effect=advance), \
                patch.object(memory_world, 'sensing_inputs', return_value=({}, [0., 0., 0.], [])), \
                patch.object(memory_task, 'capture_symbolic', return_value=packet), \
                patch.object(memory_task, 'advance_memory', side_effect=AssertionError('reference invoked memory supervision')):
            engine.submit({'id': uuid.uuid4().hex, 'kind': 'step', 'expected_state': 'paused', 'expected_episode': 0})
            return engine.advance()

    def test_live_reference_policy_and_teacher_inputs_and_frozen_memory(self):
        from palimpsest import memory_reference as ref
        for scenario in ref.REFERENCES:
            engine = self.reference_engine(scenario)
            memory_before = memory.canonical_bytes(engine.memory)
            teacher_hash = ref.teacher_control_hash(engine.teacher) if engine.teacher else None
            self.step_reference(engine)
            self.assertEqual(engine.episode_step, 301)
            self.assertEqual(memory.canonical_bytes(engine.memory), memory_before)
            self.assertEqual(engine.memory['cursor']['tick'], 299)
            self.assertEqual(engine.world_task_state['last_tick'], 300)
            if engine.policy:
                np.testing.assert_array_equal(engine.policy.seen['sensors']['wind_direction'], [1., 0.])
            if engine.teacher:
                np.testing.assert_array_equal(engine.teacher.seen[0], [9., 8.])
                self.assertIsNone(engine.teacher._path)
                self.assertEqual(ref.teacher_control_hash(engine.teacher), teacher_hash)
            for kind, payload in (('reset', {}), ('set_action', {'action': [0, 0]}), ('intervene', {'kind': 'move_goal', 'xy': [1, 2]})):
                receipt = engine.submit({'id': uuid.uuid4().hex, 'kind': kind, 'payload': payload,
                    'expected_state': 'paused', 'expected_episode': 0})
                engine.advance()
                self.assertEqual(engine.receipts[receipt['id']]['status'], 'rejected')

    def test_unavailable_sensor_goal_is_retained_failure_with_no_tick_or_memory_revision(self):
        engine = self.reference_engine('memory-reference-sensor-only')
        before = memory.canonical_bytes(engine.memory)
        self.step_reference(engine, hidden_goal=True)
        self.assertEqual(engine.phase, 'failed')
        engine.close()
        self.assertEqual(engine.writer.manifest['recorded_ticks'], 0)
        self.assertEqual(memory.canonical_bytes(engine.memory), before)
        self.assertEqual(engine.last_outcome['type'], 'CueUnavailable')

    def test_teacher_invalidation_does_not_touch_recovery_pid_or_hysteresis(self):
        from palimpsest.interventions import invalidate_geometry
        from palimpsest.memory_reference import teacher_control_hash
        env, teacher = SmallEnv(), SmallTeacher()
        env.planner = SimpleNamespace(_cached_occ=1, _cached_obstacles_hash=2, _cached_clearance=3)
        env.path_to_draw = env.target_to_draw = [1, 2]
        before = teacher_control_hash(teacher)
        invalidate_geometry(env, teacher)
        self.assertEqual(teacher_control_hash(teacher), before)
        self.assertIsNone(teacher._path)
        self.assertIsNone(env.planner._cached_occ)
        self.assertIsNone(env.target_to_draw)
        teacher.pid_state.integral += 1
        self.assertNotEqual(teacher_control_hash(teacher), before)

    def test_teacher_path_is_retained_without_a_scheduled_geometry_edit(self):
        engine = self.reference_engine('memory-reference-teacher')
        path = copy.deepcopy(engine.teacher._path)
        with patch('palimpsest.interventions.invalidate_geometry') as invalidate:
            self.step_reference(engine, geometry_edit=False)
        invalidate.assert_not_called()
        self.assertEqual(engine.teacher._path, path)
        captured = {'state': snapshots._fields(engine.teacher, snapshots.TEACHER_STATE),
                    'pid': snapshots._fields(engine.teacher.pid_state, ('integral', 'last_error')),
                    'planner': snapshots._fields(engine.teacher.planner, snapshots.VFH_STATE)}
        filename = self.fixture.root / 'synthetic-teacher.snp'
        snapshots.save_snapshot(captured, filename)
        restored = snapshots.read_snapshot(filename)
        self.assertEqual(snapshots.state_digest(restored), snapshots.state_digest(captured))
        for name, fields in (('state', snapshots.TEACHER_STATE),
                             ('pid', ('integral', 'last_error')), ('planner', snapshots.VFH_STATE)):
            self.assertEqual(snapshots.state_digest(snapshots._validate_fields(restored[name], fields)),
                             snapshots.state_digest(restored[name]))

    def test_reference_atomic_failure_closes_owned_resources_without_backend_leak(self):
        env = SmallEnv()
        env.renderer = Mock()
        policy = SmallPolicy()
        policy.device = 'cpu'
        policy.provenance = {'claim': 'synthetic-policy-fixture'}
        output = self.fixture.root / 'failed-reference'
        backend_before = {key: os.environ.get(key) for key in ('MUJOCO_GL', 'MPLBACKEND')}
        source_hash = snapshots.state_digest(self.source)
        torch = SimpleNamespace(manual_seed=Mock(), set_num_threads=Mock())
        with patch.dict(os.environ), patch.dict('sys.modules', {'torch': torch}), \
                patch('palimpsest.doctor.diagnose', return_value={'checks': []}), \
                patch('palimpsest.profiles.configure_world'), \
                patch('palimpsest.assets.verify_assets', return_value={'ok': True}), \
                patch('palimpsest.assets.prepare_graph', return_value=self.fixture.root / 'graph'), \
                patch('palimpsest.assets.load_manifest', return_value={'files': [{'id': 'checkpoint', 'path': 'fixture'}], 'upstream_commit': 'fixture'}), \
                patch('palimpsest.flynn.import_upstream', return_value=SimpleNamespace(_make_env=lambda *a, **kw: env)), \
                patch('palimpsest.flynn.load_policy', return_value=policy), \
                patch.object(memory_world, 'configure', return_value=memory_world.initial_state(case=self.case)), \
                patch.object(snapshots, 'restore', side_effect=ValueError('synthetic reference restore failure')):
            with self.assertRaisesRegex(ValueError, 'synthetic reference restore failure'):
                Engine.open(Path(__file__).resolve().parents[1], self.fixture.root, output,
                    controller='flynn', seed=24, scenario='memory-reference-original-flynn',
                    memory_case=self.case, restore_snapshot=self.source)
        self.assertEqual({key: os.environ.get(key) for key in backend_before}, backend_before)
        self.assertTrue(env.closed)
        env.renderer.close.assert_called_once()
        self.assertEqual(snapshots.state_digest(self.source), source_hash)
        retained = json.loads((output / 'manifest.json').read_text())
        self.assertEqual(retained['status'], 'failed')
        self.assertEqual(retained['recorded_ticks'], 0)
        self.assertIn('synthetic reference restore failure', retained['error']['message'])

    def test_reference_replay_reopens_atomically_and_preserves_default_route(self):
        from palimpsest import replay, memory_reference as ref
        for scenario, (controller, _) in ref.REFERENCES.items():
            source, destination = self.fixture.root / uuid.uuid4().hex, self.fixture.root / uuid.uuid4().hex
            source.mkdir(); destination.mkdir()
            writer = RunWriter(source / 'recording', {'run_id': source.name,
                'controller': controller, 'requested_device': 'cpu', 'seed': 24, 'texture': 'checker',
                'scenario': {'id': scenario}, 'memory_case': self.case, 'memory_case_sha256': memory.sha256(self.case),
                'acquisition_protocol_sha256': self.case['acquisition_protocol_sha256'],
                'memory_reference_admission': {'mode': scenario, 'protocol_sha256': ref.PROTOCOL_SHA256}})
            (source / 'snapshots').mkdir()
            native = {'application': {'source_run_id': source.name,
                'event_prefix': {'sha256': hashlib.sha256(b'').hexdigest(), 'size_bytes': 0, 'event_count': 0},
                'world_task_state': memory_world.initial_state(case=self.case)}}
            filename = source / 'snapshots/initial.snp'
            snapshots.save_snapshot(native, filename)
            writer.event('snapshot_registered', run_id=source.name, initial=True, filename='initial.snp',
                         snapshot_id=uuid.uuid4().hex, sha256=hashlib.sha256(filename.read_bytes()).hexdigest())
            writer.finish({})
            for mode in ('actions', 'policy'):
                destination = self.fixture.root / uuid.uuid4().hex
                destination.mkdir()
                fake = Mock(); fake.run_id = destination.name; fake.writer.manifest = {}
                with patch.object(Engine, 'open', return_value=fake) as opened, \
                        patch.object(replay, '_compatible'), patch.object(replay, '_events', return_value=[]), \
                        patch.object(replay, '_register_initial', side_effect=InterruptedError('pure boundary')):
                    report = replay.replay_run(source, destination, mode=mode, repo_root=self.fixture.root, asset_root=self.fixture.root)
                self.assertEqual(report['status'], 'cancelled')
                self.assertEqual(opened.call_args.kwargs['restore_snapshot'], native)
                fake.restore_branch.assert_not_called()
                fake.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
