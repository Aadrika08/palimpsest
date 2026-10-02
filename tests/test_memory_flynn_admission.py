"""Pure admission fixtures: no MuJoCo model, Torch, checkpoint or acquired evidence.

Native restore and immutable tensor hashing are explicit mocked boundaries. These
checks establish current application contracts, not actual FLYNN continuation.
"""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

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

    def engine(self, case, *, controller='manual'):
        env = SmallEnv()
        env.n_obstacles, env.obstacle_ids = 20, list(range(20))
        env.model.geom_size = np.array([[.4, .8, 0.]] * 20)
        env.model.geom_type = np.array([5] * 20)
        env.data.geom_xpos = np.array([[*xy, .8] for xy in memory_world.validate_layout()])
        env._obstacle_xy = np.array(memory_world.validate_layout())
        policy = SmallPolicy(action=(.25, -.1)) if controller == 'flynn' else None
        path = self.root / str(len(self.engines))
        writer = RunWriter(path / 'recording', {'run_id': path.name})

        def configure(env, state):
            env.data.qpos[:] = case['start_pose']
            env._goal_xy[:] = case['goal_xy']
            return memory_world.validate_state(state)

        with patch.object(memory_world, 'configure', side_effect=configure):
            engine = Engine(env, writer, controller=controller, policy=policy,
                scenario='memory-passages', memory_case=case)
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
