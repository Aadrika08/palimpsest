"""Pure admission fixtures: no MuJoCo model, Torch, checkpoint or acquired evidence.

Native restore and immutable tensor hashing are explicit mocked boundaries. These
checks establish current application contracts, not actual FLYNN continuation.
"""

import copy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from palimpsest import memory, memory_experiment, memory_task, memory_world, snapshots
from palimpsest.engine import Engine
from palimpsest.records import RunWriter
from test_engine import SmallEnv, SmallPolicy


class FlynnMemoryAdmission(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.engines = []
        self.addCleanup(self.close_engines)
        self.hashes = patch.object(snapshots, 'controller_hashes',
            side_effect=lambda policy: None if policy is None else
            {'graph_buffers': '1' * 64, 'parameters': '2' * 64})
        self.hashes.start()
        self.addCleanup(self.hashes.stop)

    def close_engines(self):
        for engine in self.engines:
            engine.close()

    def case(self, *, acquisition=False):
        return memory_experiment.make_world_case(16, 'local_cue',
            'development-test', acquisition=acquisition, change_tick=300)

    def engine(self, case, *, controller='manual', **restoration):
        env = SmallEnv()
        env.n_obstacles, env.obstacle_ids = 20, list(range(20))
        env.model.geom_size = np.array([[.4, .8, 0.]] * 20)
        env.model.geom_type = np.array([5] * 20)
        env.data.geom_xpos = np.array([[*xy, .8] for xy in memory_world.validate_layout()])
        env._obstacle_xy = np.array(memory_world.validate_layout())
        policy = SmallPolicy(action=(.25, -.1)) if controller == 'flynn' else None
        if policy is not None:
            policy.device = 'cpu'
        path = self.root / str(len(self.engines))
        writer = RunWriter(path / 'recording', {'run_id': path.name})

        def configure(env, state):
            env.data.qpos[:] = case['start_pose']
            env._goal_xy[:] = case['goal_xy']
            return memory_world.validate_state(state)

        with patch.object(memory_world, 'configure', side_effect=configure):
            engine = Engine(env, writer, controller=controller, policy=policy,
                seed=case['seed'], scenario='memory-passages', memory_case=case, **restoration)
        self.engines.append(engine)
        return engine

    def packet(self, engine, tick):
        # Explicit synthetic visible samples, not a physical acquisition trace.
        facts = engine.memory['m']['facts']
        public = {'common_goal_id': engine.memory_case['common_goal_id'],
            'cues': [{'id': engine.memory_case['cue_id'], 'xy': [.4, .05], 'state': 0}],
            'landmarks': [{'id': engine.memory_case['common_goal_id'], 'xy': [.5, .1]}] +
                [{'id': f['inspection_landmark_id'], 'xy': [.2, .1]} for f in facts],
            'passages': [{'subject_id': f['subject_id'],
                'inspection_landmark_id': f['inspection_landmark_id'], 'passability': 'open'}
                for f in facts]}
        return memory_task.capture_symbolic(public, [0., 0., 0.], [],
            episode_id='episode-0', tick=tick)

    def observed_source(self, case):
        engine = self.engine(case)
        for tick in range(2):
            engine.memory, _, _ = memory_task.advance_memory(engine.memory, self.packet(engine, tick))
        engine.world_task_state['last_tick'] = 1
        engine.world_task_state = memory_world.validate_state(engine.world_task_state)
        engine.episode_step = engine.total_tick = engine.revision = 2
        engine.manual_action[:] = [1., .2]
        self.assertTrue(all(f['status'] == 'observed' for f in engine.memory['m']['facts']))
        return engine

    def snapshot(self, engine):
        # Full container shape with explicitly synthetic native bytes; never decode it.
        result = dict.fromkeys(snapshots.SNAPSHOT_KEYS)
        native = b'pure-fixture-not-mujoco-native'
        result.update(schema_version=snapshots.SCHEMA_VERSION,
            native_data=native, native_sha256=hashlib.sha256(native).hexdigest(),
            application=engine.application_state())
        return result

    def test_atomic_acquisition_replacement_returns_only_restored_engine(self):
        case = self.case(acquisition=True)
        source = self.observed_source(case)
        native = self.snapshot(source)
        before = snapshots.state_digest(native)
        with patch.object(snapshots, 'restore',
                side_effect=lambda saved, env, **kwargs: (env._get_obs(), saved['application'])) as restore:
            destination = self.engine(case, controller='flynn',
                restore_snapshot=native, replace_controller=True)
        restore.assert_called_once()
        self.assertTrue(restore.call_args.kwargs['replace_controller'])
        self.assertEqual((destination.controller, destination.total_tick, destination.episode_step),
            ('flynn', 2, 2))
        self.assertTrue(destination._restored)
        self.assertIsNone(destination.policy.seen)
        self.assertEqual(destination.memory, source.memory)
        self.assertEqual(destination.world_task_state, source.world_task_state)
        self.assertEqual(snapshots.state_digest(native), before)
        proof = destination.writer.manifest['memory_continuation_admission']
        self.assertEqual(proof['snapshot_state_sha256'], before)
        self.assertEqual(proof['case_sha256'], memory.sha256(case))
        self.assertEqual(proof['source_controller'], 'manual')
        self.assertIsNone(proof['memory_u_sha256'])

        anchor = self.snapshot(destination)
        own = memory.artifact('local_cue')
        current = []
        def restored(saved, env, **kwargs):
            self.assertFalse(kwargs['replace_controller'])
            return env._get_obs(), saved['application']
        def captured(env, observation, *, policy, teacher, application):
            result = copy.deepcopy(anchor)
            result['application'] = application
            current.append(result)
            return result
        with patch.object(snapshots, 'restore', side_effect=restored) as restore, \
                patch.object(snapshots, 'capture', side_effect=captured):
            branch = self.engine(case, controller='flynn', restore_snapshot=anchor, memory_u=own)
        restore.assert_called_once()
        self.assertEqual(branch.memory['u'], own)
        self.assertEqual(branch.memory['m'], destination.memory['m'])
        self.assertEqual(branch.memory['e'], destination.memory['e'])
        self.assertTrue(all(snapshots.invariant_hashes(s) == snapshots.invariant_hashes(anchor)
            for s in current))
        self.assertEqual(branch.writer.manifest['memory_continuation_admission']['memory_u_sha256'], memory.sha256(own))
        self.assertIsNone(branch.policy.seen)

    def test_narrow_atomic_preflight_rejects_invalid_routes_before_allocation(self):
        case = self.case(acquisition=True)
        source = self.observed_source(case)
        native = self.snapshot(source)
        invalid = [
            {'device': 'cuda'}, {'controller': 'manual'}, {'scenario': 'reproduction'}, {'seed': 17},
            {'replace_controller': 1}, {'memory_u': memory.artifact('local_cue')},
            {'restore_snapshot': None}, {'memory_case': self.case()},
        ]
        for altered in ('controller', 'phase', 'execution_mode', 'native_sha256', 'case'):
            bad = copy.deepcopy(native)
            if altered == 'native_sha256':
                bad[altered] = '0' * 64
            elif altered == 'case':
                bad['application']['world_task_state']['case'] = self.case()
            else:
                bad['application'][altered] = {'controller': 'flynn', 'phase': 'running',
                    'execution_mode': 'actions'}[altered]
            invalid.append({'restore_snapshot': bad})
        for index, update in enumerate(invalid):
            args = {'controller': 'flynn', 'device': 'cpu', 'scenario': 'memory-passages',
                'seed': case['seed'], 'memory_case': case, 'restore_snapshot': native, 'replace_controller': True}
            args.update(update)
            with self.subTest(route=index), patch('palimpsest.records.RunWriter') as writer, \
                    patch('palimpsest.doctor.diagnose') as diagnose, self.assertRaises((ValueError, TypeError)):
                Engine.open(self.root, self.root, self.root / 'not-allocated', **args)
            writer.assert_not_called()
            diagnose.assert_not_called()
        with self.assertRaises(ValueError):
            Engine._memory_restore(None, 'reproduction', 'manual', 'cpu', None, False, memory.artifact())

    def test_atomic_open_failure_closes_owned_runtime_without_model_import(self):
        case = self.case(acquisition=True)
        source = self.observed_source(case)
        native = self.snapshot(source)
        source_before = snapshots.state_digest(native)
        env = SmallEnv()
        env.renderer = Mock()
        policy = SmallPolicy()
        policy.device = 'cpu'
        policy.provenance = {'requested_device': 'cpu', 'claim': 'pure-policy-fixture'}
        torch_stub = SimpleNamespace(manual_seed=Mock(), set_num_threads=Mock())
        backend_before = {key: os.environ.get(key) for key in ('MUJOCO_GL', 'MPLBACKEND')}
        output = self.root / 'failed-atomic'
        def configure(env, state):
            env.data.qpos[:] = case['start_pose']
            env._goal_xy[:] = case['goal_xy']
            return memory_world.validate_state(state)
        with patch.dict('os.environ'), patch.dict('sys.modules', {'torch': torch_stub}), \
                patch('palimpsest.doctor.diagnose', return_value={'checks': []}), \
                patch('palimpsest.profiles.configure_world'), \
                patch('palimpsest.assets.verify_assets', return_value={'ok': True}), \
                patch('palimpsest.assets.prepare_graph', return_value=self.root / 'graph'), \
                patch('palimpsest.assets.load_manifest', return_value={'files': [{'id': 'checkpoint', 'path': 'fixture'}], 'upstream_commit': 'fixture'}), \
                patch('palimpsest.flynn.import_upstream', return_value=SimpleNamespace(_make_env=lambda *a, **kw: env)), \
                patch('palimpsest.flynn.load_policy', return_value=policy), \
                patch.object(memory_world, 'configure', side_effect=configure), \
                patch.object(snapshots, 'restore', side_effect=ValueError('pure native failure')) as restore:
            with self.assertRaisesRegex(ValueError, 'pure native failure'):
                Engine.open(Path(__file__).resolve().parents[1], self.root, output,
                    controller='flynn', seed=case['seed'], scenario='memory-passages', memory_case=case,
                    restore_snapshot=native, replace_controller=True)
        self.assertEqual({key: os.environ.get(key) for key in backend_before}, backend_before)
        restore.assert_called_once()
        self.assertTrue(env.closed)
        env.renderer.close.assert_called_once()
        self.assertIsNone(policy.seen)
        self.assertFalse(source.env.closed)
        self.assertEqual(snapshots.state_digest(native), source_before)
        failed = json.loads((output / 'manifest.json').read_text())
        self.assertEqual(failed['status'], 'failed')
        self.assertEqual(failed['recorded_ticks'], 0)
        self.assertIn('pure native failure', failed['error']['message'])

    def test_replay_uses_atomic_route_only_for_acquisition_flynn(self):
        from palimpsest import replay
        for controller, acquisition in (('flynn', True), ('manual', True), ('flynn', False)):
            for mode in ('actions', 'policy'):
                with self.subTest(controller=controller, acquisition=acquisition, mode=mode):
                    source = self.root / uuid.uuid4().hex
                    destination = self.root / uuid.uuid4().hex
                    source.mkdir()
                    destination.mkdir()
                    case = self.case(acquisition=acquisition)
                    writer = RunWriter(source / 'recording', {'run_id': source.name,
                        'controller': controller, 'requested_device': 'cpu', 'seed': 16,
                        'texture': 'checker', 'scenario': {'id': 'memory-passages'},
                        'memory_case': case, 'memory_case_sha256': memory.sha256(case),
                        'acquisition_protocol_sha256': case['acquisition_protocol_sha256']})
                    (source / 'snapshots').mkdir()
                    filename = source / 'snapshots/initial.snp'
                    snapshot = {'application': {'source_run_id': source.name,
                        'event_prefix': {'sha256': hashlib.sha256(b'').hexdigest(), 'size_bytes': 0, 'event_count': 0},
                        'world_task_state': memory_world.initial_state(case=case)}}
                    snapshots.save_snapshot(snapshot, filename)
                    writer.event('snapshot_registered', run_id=source.name, initial=True,
                        filename='initial.snp', snapshot_id=uuid.uuid4().hex,
                        sha256=hashlib.sha256(filename.read_bytes()).hexdigest())
                    writer.finish({})
                    fake = Mock()
                    fake.run_id = destination.name
                    fake.writer.manifest = {}
                    with patch.object(Engine, 'open', return_value=fake) as opened, \
                            patch.object(replay, '_compatible'), patch.object(replay, '_events', return_value=[]), \
                            patch.object(replay, '_register_initial', side_effect=InterruptedError('pure boundary')):
                        report = replay.replay_run(source, destination, mode=mode,
                            repo_root=self.root, asset_root=self.root)
                    self.assertEqual(report['status'], 'cancelled', report)
                    self.assertEqual(opened.call_args.kwargs['memory_case'], case)
                    atomic = controller == 'flynn' and acquisition
                    self.assertEqual('restore_snapshot' in opened.call_args.kwargs, atomic)
                    if atomic:
                        self.assertEqual(opened.call_args.kwargs['restore_snapshot'], snapshot)
                        fake.restore_branch.assert_not_called()
                    else:
                        fake.restore_branch.assert_called_once_with(snapshot)
                    self.assertEqual(report['inference_executed'], mode == 'policy' and controller == 'flynn')
                    fake.close.assert_called_once()

    def test_acquisition_flynn_rejects_before_runtime_allocation(self):
        case = self.case(acquisition=True)
        self.assertEqual(Engine._validate_memory_case(case, 'memory-passages', 'manual'), case)
        with patch('palimpsest.records.RunWriter') as writer, \
                patch('palimpsest.doctor.diagnose') as diagnose, \
                patch('palimpsest.flynn.load_policy') as load_policy:
            with self.assertRaisesRegex(ValueError, 'manual acquisition controller'):
                Engine.open(self.root, self.root, self.root / 'actual-not-created',
                    controller='flynn', device='cpu', scenario='memory-passages', memory_case=case)
            writer.assert_not_called()
            diagnose.assert_not_called()
            load_policy.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'manual acquisition controller'):
            Engine._validate_memory_case(case, 'memory-passages', 'flynn')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_changing_acquisition_cannot_repair_source_case_identity(self):
        acquired = self.case(acquisition=True)
        forged = copy.deepcopy(acquired)
        forged['acquisition'] = False
        with self.assertRaises(ValueError):
            memory_experiment.validate_world_case(forged)
        regenerated = self.case(acquisition=False)
        for field in ('case_sha256', 'start_pose', 'goal_xy', 'cue_xy', 'acquisition_schedule'):
            self.assertNotEqual(acquired[field], regenerated[field], field)
        source = self.observed_source(acquired)
        destination = self.engine(regenerated, controller='flynn')
        snapshot = {'application': source.application_state()}
        before_source = copy.deepcopy(snapshot)
        before_destination = destination.env.data.qpos.copy()
        with patch.object(snapshots, 'restore') as native:
            with self.assertRaisesRegex(ValueError, 'case differs from destination'):
                destination.restore_branch(snapshot, replace_controller=True)
            native.assert_not_called()
        self.assertEqual(snapshot, before_source)
        np.testing.assert_array_equal(destination.env.data.qpos, before_destination)
        self.assertFalse(destination._restored)
        self.assertIsNone(destination.policy.seen)

    def test_existing_replacement_preserves_application_and_executes_policy_path(self):
        # Existing permitted non-acquisition geometry isolates replacement semantics.
        # It is not substituted for the rejected acquisition case above.
        case = self.case()
        source = self.observed_source(case)
        source.submit({'id': 'cancel-source-intent', 'kind': 'set_action',
            'expected_state': 'paused', 'expected_episode': 0, 'payload': {'action': [.5, .1]}})
        snapshot = {'application': source.application_state()}
        source_digest = snapshots.state_digest(snapshot)
        destination = self.engine(case, controller='flynn')
        physical = {key: getattr(source.env.data, key).copy() for key in ('qpos', 'qvel', 'ctrl')}

        def native_restore(saved, env, *, policy, teacher, replace_controller):
            self.assertIs(saved, snapshot)
            self.assertIs(env, destination.env)
            self.assertIs(policy, destination.policy)
            self.assertIsNone(teacher)
            self.assertTrue(replace_controller)
            for key, value in physical.items():
                getattr(env.data, key)[:] = value
            return env._get_obs(), copy.deepcopy(saved['application'])

        with patch.object(snapshots, 'restore', side_effect=native_restore) as native:
            destination.restore_branch(snapshot, replace_controller=True)
            native.assert_called_once()
        self.assertEqual(snapshots.state_digest(snapshot), source_digest)
        self.assertEqual(destination.memory, snapshot['application']['memory'])
        self.assertEqual(destination.world_task_state, snapshot['application']['world_task_state'])
        self.assertEqual(destination.eyes, snapshot['application']['eyes'])
        self.assertEqual((destination.total_tick, destination.episode_step), (2, 2))
        self.assertEqual(destination.revision, 3)
        self.assertEqual(destination.parent_run_id, source.run_id)
        self.assertEqual(destination.receipts, {})
        self.assertEqual(destination._originals, {})
        self.assertEqual(list(destination._pending), [])
        np.testing.assert_array_equal(destination.manual_action, [0., 0.])
        self.assertIsNone(destination.policy.seen)  # Zero-step replacement never infers.
        events = [json.loads(line) for line in (destination.writer.path / 'events.jsonl').read_text().splitlines()]
        replaced = next(e for e in events if e['kind'] == 'controller_replaced')
        self.assertEqual((replaced['old'], replaced['new']), ('manual', 'flynn'))
        self.assertEqual(replaced['cancelled_source_commands'], ['cancel-source-intent'])
        self.assertEqual(replaced['fresh_state'], ['controller', 'torch_rng', 'manual_intent', 'command_history'])

        packet = self.packet(destination, 2)
        with patch.object(memory_task, 'capture_symbolic', return_value=packet), \
                patch.object(destination, '_population_stats', return_value=[]):
            destination._step()  # No action override: existing production policy.act.
        self.assertEqual(set(destination.policy.seen), {'cam_left', 'cam_right', 'sensors'})
        self.assertEqual(set(destination.policy.seen['sensors']),
            {'collision', 'collision_angle', 'wind_direction'})
        np.testing.assert_array_equal(destination.last_transition['action'],
            np.array(destination.policy.action, dtype=np.float32))
        self.assertIn('encoded_input', destination.last_transition)
        self.assertIn('raw_output', destination.last_transition)
        self.assertEqual(destination.total_tick, 3)
        self.assertEqual(destination.writer.manifest['execution_mode'], 'live')

    def test_post_replacement_anchor_does_not_exclude_hidden_rng_or_memory(self):
        source = self.observed_source(self.case())
        anchor = dict.fromkeys(snapshots.SNAPSHOT_KEYS)
        anchor.update(application=source.application_state(), native_data=b'fixture-native',
            integration=np.array([1., 2.]), observation=source.observation,
            policy={'h': np.array([.25], dtype=np.float32)},
            rng={'python': ['fixture'], 'numpy': np.array([1], dtype=np.uint32),
                 'torch_cpu': np.array([2], dtype=np.uint8)},
            identity={'fixed_checkpoint': '1' * 64})
        expected = snapshots.invariant_hashes(anchor)
        swapped = copy.deepcopy(anchor)
        swapped['application']['source_run_id'] = 'other-fixture'
        swapped['application']['event_prefix'] = {'sha256': '2' * 64}
        swapped['application']['memory']['u'] = memory.artifact('paired_cue')
        self.assertEqual(snapshots.invariant_hashes(swapped), expected)
        mutations = [
            lambda a: a['policy']['h'].__setitem__(0, .5),
            lambda a: a['rng']['torch_cpu'].__setitem__(0, 3),
            lambda a: a['rng']['numpy'].__setitem__(0, 4),
            lambda a: a.__setitem__('native_data', b'changed-native'),
            lambda a: a['application']['memory']['m']['facts'][0].__setitem__('estimate', 'blocked'),
            lambda a: a['application']['memory']['e']['episodes'].append('changed-fixture'),
            lambda a: a['application']['memory']['cursor'].__setitem__('tick', 2),
            lambda a: a['application']['memory']['detector'].__setitem__('tick', 2),
            lambda a: a['application']['memory']['requests'].append('changed-fixture'),
            lambda a: a['application']['memory'].__setitem__('active', {'changed': True}),
        ]
        for index, mutate in enumerate(mutations):
            changed = copy.deepcopy(swapped)
            mutate(changed)
            with self.subTest(mutation=index):
                self.assertNotEqual(snapshots.invariant_hashes(changed), expected)


if __name__ == '__main__':
    unittest.main()
