"""Pure development configuration checks; fixture poses are not motion traces."""
import math
import hashlib
import tempfile
from pathlib import Path
import unittest
import uuid
from unittest.mock import patch

import numpy as np

from palimpsest import memory, memory_experiment as experiment, memory_task, memory_world as world
from palimpsest.engine import Engine
from palimpsest.records import RunWriter
from test_engine import SmallEnv, SmallPolicy
from test_memory_world import environment


class DevelopmentCases(unittest.TestCase):
    def case(self, seed=0, regime='local_cue', split='development-history', **kwargs):
        self.assertTrue(hasattr(experiment, 'make_world_case'), 'runtime case constructor missing')
        return experiment.make_world_case(seed, regime, split, **kwargs)

    def test_live_cases_counterbalance_ids_and_begin_unknown(self):
        ids = set()
        for seed in range(8):
            case = self.case(seed)
            state = world.initial_state(case=case)
            facts = world.initial_facts(state)
            self.assertTrue(all(f['estimate'] is None and f['evidence'] is None and f['origin'] == 'initial_unknown' for f in facts))
            self.assertTrue(ids.isdisjoint({f['id'] for f in facts}))
            ids.update(f['id'] for f in facts)
            closing = next(f for f in facts if f['subject_id'] == state['close_subject_id'])
            self.assertEqual(closing['associations'][0]['relation'], 'local_cue')
        first = self.case(0)
        other = self.case(0, split='development-test')
        self.assertNotEqual(first['case_id'], other['case_id'])
        self.assertEqual(world.initial_state()['change_tick'], 10)
        self.assertEqual([f['id'] for f in world.initial_facts()], ['fact-passage-a', 'fact-passage-b'])

    def test_hidden_regime_is_absent_from_sensing_and_gate_labels_are_geometric(self):
        packets = []
        for regime in memory.RELATIONS:
            case = self.case(0, regime)
            state = world.initial_state(case=case)
            public, pose, circles = world.sensing_inputs(environment(), state)
            self.assertEqual(set(public), {'cues', 'landmarks', 'passages', 'common_goal_id'})
            self.assertEqual({p['subject_id'] for p in public['passages']}, set(case['subjects_by_side']))
            packets.append(memory_task.capture_symbolic(public, pose, circles, episode_id='episode-0', tick=0))
        self.assertEqual(packets[0], packets[1])
        env = environment()
        env.data.geom_xpos[4][:2] = world.CLOSED_GATES[1]
        public, _, _ = world.sensing_inputs(env, world.initial_state(case=self.case()))
        labels = {p['subject_id']: p['passability'] for p in public['passages']}
        self.assertEqual(labels[self.case()['subjects_by_side'][1]], 'blocked')

    def test_change_null_and_no_event_apply_the_declared_mechanism(self):
        for kind in ('change', 'null', 'no-event'):
            for regime in memory.RELATIONS:
                env = environment()
                case = self.case(1, regime, kind=kind, change_tick=1)
                state = world.initial_state(case=case)
                state, _ = world.advance_world(env, state, 0)
                def edit(env, intervention):
                    env.data.geom_xpos[intervention['index']][:2] = intervention['xy']
                    return {'kind': 'move_obstacle', 'index': intervention['index'], 'new': {'xy': intervention['xy']}}
                with patch.object(world, 'apply_intervention', side_effect=edit) as apply:
                    state, events = world.advance_world(env, state, 1)
                    self.assertEqual(apply.call_count, int(kind == 'change'))
                self.assertEqual(state['cue_state'], int(kind != 'no-event'))
                if kind == 'no-event':
                    self.assertEqual(events, [])
                elif kind == 'change':
                    labels = events[-1]['after']
                    self.assertEqual(labels[state['close_subject_id']], 'blocked')
                else:
                    self.assertEqual(events[-1]['before'], events[-1]['after'])

    def test_acquisition_planned_poses_see_both_passages_and_goal_even_after_closure(self):
        case = self.case(acquisition=True)
        schedule = case['acquisition_schedule']
        self.assertEqual(schedule['access'], 'privileged-manual-pose-supervision')
        for side, pose in enumerate(([-1.3, -1.1, math.pi / 2], [-1.3, .6, math.pi / 2])):
            for closed in (None, 0, 1):
                env = environment()
                env._base_xy = lambda: pose[:2]
                env._base_yaw = lambda: pose[2]
                env._goal_xy = case['goal_xy']
                if closed is not None:
                    env.data.geom_xpos[closed + 3][:2] = world.CLOSED_GATES[closed]
                public, actual_pose, circles = world.sensing_inputs(env, world.initial_state(case=case))
                packet = memory_task.capture_symbolic(public, actual_pose, circles, episode_id='planned', tick=0)
                self.assertIn(case['common_goal_id'], {landmark['id'] for landmark in packet['landmarks']})
                passage = next(p for p in packet['passages'] if p['subject_id'] == case['subjects_by_side'][side])
                self.assertEqual(passage['passability'], 'blocked' if closed == side else 'open')
                self.assertEqual(len(packet['cues']), 1)
        paired = self.case(regime='paired_cue', acquisition=True)
        self.assertEqual(schedule, paired['acquisition_schedule'])
        forward = experiment.acquisition_action(schedule, [-1.3, -1.1, math.pi / 2], 20)
        backward = experiment.acquisition_action(schedule, [-1.3, .6, math.pi / 2], 330)
        self.assertGreater(forward[0], 0)
        self.assertLess(backward[0], 0)

    def test_case_tampering_held_out_and_synthetic_known_seeds_reject(self):
        with self.assertRaises(ValueError):
            self.case(split='held-out')
        for field, value in (('regime', 'paired_cue'), ('seed', 1), ('kind', 'null')):
            case = self.case()
            case[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                world.initial_state(case=case)
        case = self.case()
        case['facts'][0]['estimate'] = 'open'
        with self.assertRaises(ValueError):
            world.initial_state(case=case)

    def test_boolean_integer_aliases_cannot_forge_bound_case_or_schedule(self):
        case = self.case()
        case['version'] = True
        with self.assertRaises(ValueError):
            world.initial_state(case=case)
        schedule = self.case(acquisition=True)['acquisition_schedule']
        schedule['uses_u'] = 0
        with self.assertRaises(ValueError):
            experiment.acquisition_action(schedule, [-1.3, -1.1, math.pi / 2], 20)

    def test_engine_binds_case_and_resets_unknown_without_synthetic_evidence(self):
        case = self.case(acquisition=True)
        with tempfile.TemporaryDirectory() as directory:
            env = SmallEnv()
            def configure(env, state):
                env.data.qpos[:] = case['start_pose']
                env._goal_xy[:] = case['goal_xy']
                return world.validate_state(state)
            writer = RunWriter(Path(directory) / 'recording', {'run_id': 'fixture'})
            with patch.object(world, 'configure', side_effect=configure):
                engine = Engine(env, writer, scenario='memory-passages', memory_case=case)
                try:
                    self.assertEqual(engine.writer.manifest['memory_case'], case)
                    self.assertEqual(engine.writer.manifest['acquisition_protocol_sha256'], case['acquisition_protocol_sha256'])
                    self.assertEqual(engine.application_state()['world_task_state']['case'], case)
                    self.assertEqual(engine.memory['e']['episodes'], [])
                    self.assertEqual(engine.memory['u']['payload']['rules'], [])
                    self.assertTrue(all(f['status'] == 'unknown' for f in engine.memory['m']['facts']))
                    engine._reset_world()
                    self.assertEqual(engine.world_task_state['case'], case)
                finally:
                    engine.close()

    def test_policy_observation_has_no_private_case_or_geometry(self):
        case = self.case()
        env = SmallEnv()
        env.n_obstacles, env.obstacle_ids = 20, list(range(20))
        env.model.geom_size = np.array([[.4, .8, 0.]] * 20)
        env.model.geom_type = np.array([5] * 20)
        env.data.geom_xpos = np.array([[*xy, .8] for xy in world.validate_layout()])
        env._obstacle_xy = np.array(world.validate_layout())
        policy = SmallPolicy(action=(0., 0.))
        def configure(env, state):
            env.data.qpos[:] = case['start_pose']
            env._goal_xy[:] = case['goal_xy']
            return world.validate_state(state)
        with tempfile.TemporaryDirectory() as directory:
            writer = RunWriter(Path(directory) / 'recording', {'run_id': 'policy-fixture'})
            with patch.object(world, 'configure', side_effect=configure):
                engine = Engine(env, writer, controller='flynn', policy=policy, scenario='memory-passages', memory_case=case)
                try:
                    engine._step()
                    self.assertEqual(set(policy.seen), {'cam_left', 'cam_right', 'sensors'})
                    self.assertEqual(set(policy.seen['sensors']), {'collision', 'collision_angle', 'wind_direction'})
                finally:
                    engine.close()

    def test_replay_propagates_exact_case_and_rejects_manifest_snapshot_mismatch(self):
        from palimpsest.replay import replay_run
        from palimpsest.snapshots import save_snapshot
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for case, mismatch in ((None, False), (self.case(), False), (self.case(), True)):
                source, destination = root / uuid.uuid4().hex, root / uuid.uuid4().hex
                source.mkdir()
                destination.mkdir()
                manifest = {'run_id': source.name, 'controller': 'manual', 'requested_device': 'cpu',
                    'seed': 0, 'texture': 'checker', 'scenario': {'id': 'memory-passages'}}
                if case is not None:
                    manifest.update(memory_case=case, memory_case_sha256=memory.sha256(case),
                        acquisition_protocol_sha256=case['acquisition_protocol_sha256'])
                writer = RunWriter(source / 'recording', manifest)
                (source / 'snapshots').mkdir()
                filename = source / 'snapshots/initial.snp'
                snapshot_case = self.case(1) if mismatch else case
                save_snapshot({'application': {'source_run_id': source.name,
                    'event_prefix': {'sha256': hashlib.sha256(b'').hexdigest(), 'size_bytes': 0, 'event_count': 0},
                    'world_task_state': world.initial_state(case=snapshot_case)}}, filename)
                writer.event('snapshot_registered', run_id=source.name, initial=True, filename='initial.snp',
                    snapshot_id=uuid.uuid4().hex, sha256=hashlib.sha256(filename.read_bytes()).hexdigest())
                writer.finish({})
                seen = []
                def open_boundary(*args, **kwargs):
                    seen.append(kwargs.get('memory_case'))
                    raise InterruptedError('stop before actual runtime')
                with patch.object(Engine, 'open', side_effect=open_boundary):
                    report = replay_run(source, destination, mode='actions', repo_root=root, asset_root=root)
                self.assertEqual(report['status'], 'failed' if mismatch else 'cancelled', report)
                self.assertEqual(seen, [] if mismatch else [case])
                self.assertFalse((destination / 'recording').exists())


if __name__ == '__main__':
    unittest.main()
