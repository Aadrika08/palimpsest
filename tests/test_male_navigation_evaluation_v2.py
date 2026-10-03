"""Authored runner fixtures only; no real scenes, models, corpus or writer lease."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import evaluate_male_navigation_v2 as runner
import test_male_navigation_collection as old
from test_male_navigation_collection_v2 import ownership, model_fixture
from palimpsest.records import RunWriter, iter_ticks


class Engine(old.Engine):
    def __init__(self):
        super().__init__(); self.teacher = None; self.env.engine = self; self.calls = 0
        def act(observation):
            self.calls += 1
            return {'action': np.array([.9, -.2], np.float32)}
        self.policy.act = act

    def advance(self):
        self.receipt = self.queued['id']; action = self.policy.act(self.observation)['action']
        raw = runner.common.input_row(self.observation) | {
            'raw_cam_left': self.observation['cam_left'].copy(), 'raw_cam_right': self.observation['cam_right'].copy(),
            'action': action, 'control': runner.common.expected_control(action).astype(np.float64),
            'pose': np.array([self.total_tick*.01, 0., 0.]), 'next_pose': np.array([(self.total_tick+1)*.01, 0., 0.]),
            'simulation_time': np.array((self.total_tick+1)*.02), 'eyes': np.ones(2, bool)}
        self.writer.tick(0, self.total_tick, **raw); self.total_tick += 1
        if self.total_tick == 3: self.phase = 'terminated'


def sample(env):
    tick = env.engine.total_tick
    return {'position_xyz': [tick*.01, 0., .1], 'quaternion': [1., 0., 0., 0.],
            'pose': [tick*.01, 0., 0.], 'time_s': tick*.02,
            'shaft_angles_rad': [0., 0.], 'contacts': 0}


def blank_report():
    return {'status': 'running', 'owners_completed': 0, 'numeric_ticks': 0,
            'cases': {case['id']: {'case': dict(case), 'status': 'not_started'} for case in runner.CASES}}


class NavigationRunner(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup); self.root = Path(temp.name)
        self.budget = SimpleNamespace(check=Mock(return_value={}))

    def run_fixture(self, probe_type=old.Probe, *, record=False, command=None):
        engine = Engine(); result = {'rows': [], 'contact_ownership': ownership(), 'contact_incidence': runner.contacts.empty_incidence(),
            'numeric_admission': runner.common.numeric_admission([np.zeros((128, 128, 3), np.uint8)]*2, 136)}
        writer = None
        if record:
            writer = RunWriter(self.root/'recording', {'run_id': '1'*32, 'profile': 'synthetic-navigation'})
            engine.writer = writer; self.addCleanup(writer.close)
        original_tick, original_act = engine.writer.tick, engine.policy.act
        self.engine, self.result, self.original_tick, self.original_act = engine, result, original_tick, original_act
        with patch.object(runner.common, 'sample', side_effect=sample):
            if command is None:
                outcome = runner.run_episode(engine, probe_type(engine), result, time.monotonic()+10, self.root, self.budget)
            else:
                with patch.object(runner.common, 'command', side_effect=command):
                    outcome = runner.run_episode(engine, probe_type(engine), result, time.monotonic()+10, self.root, self.budget)
        if writer: writer.finish({}); writer.close()
        return engine, result, outcome

    def test_fixed_order_limits_and_negative_gate_are_distinct_from_infrastructure(self):
        self.assertEqual(len(runner.CASES), 24)
        self.assertEqual([(c['scene_seed'], c['training_seed'], c['arm']) for c in runner.CASES],
            [(scene, seed, arm) for scene in range(3110, 3114) for seed in (10, 11, 12) for arm in ('old-corpus', 'augmented')])
        for field, value in (('scene_seed', 3120), ('scene_seed', 3110.), ('training_seed', True), ('arm', 'degree_rewired')):
            with self.assertRaises(ValueError): runner.check_case(runner.CASES[0] | {field: value})
        a = runner.admission(runner.contacts.plan())
        self.assertEqual(a['aggregate_bytes']+a['failure_extra_bytes']+a['unspent_headroom_bytes'], 4092*runner.MiB)
        report = blank_report(); self.assertTrue(runner.run_cases(report, lambda c, r: {'ticks': 600, 'outcome': 'time_limit'}))
        gate = runner.reduce_results(report)
        self.assertEqual((report['status'], gate['status'], gate['operational_status']),
                         ('completed-development', 'failed-development-gate', 'completed'))
        self.assertEqual(set(gate['goals_by_seed_arm'].values()), {0})
        for row in report['cases'].values():
            if row['case']['arm'] == 'augmented' and row['case']['scene_seed'] != 3113: row['outcome'] = 'goal'
        self.assertEqual(runner.reduce_results(report)['status'], 'passed-development-gate')
        report['cases']['dev-3112-seed-12-augmented']['outcome'] = 'stalled'
        self.assertEqual(runner.reduce_results(report)['status'], 'failed-development-gate')

    def test_first_parent_admission_failure_leaves_later_rows_unstarted(self):
        report = blank_report()
        def owner(case, row):
            if case == runner.CASES[2]: raise ValueError('retained contact refusal')
            return {'ticks': 3, 'outcome': 'stalled'}
        self.assertFalse(runner.run_cases(report, owner))
        self.assertEqual([r['status'] for r in report['cases'].values()], ['completed-recording']*2+['failed-infrastructure']+['not_started']*21)
        self.assertEqual(runner.reduce_results(report)['status'], 'not_admitted_infrastructure')
        self.assertEqual(report['numeric_ticks'], 6)

    def test_teacher_free_real_record_roundtrip_and_exact_once_predictions(self):
        modules = {name: sys.modules.get(name) for name in ('torch', 'mujoco')}
        engine, result, outcome = self.run_fixture(record=True)
        rows = list(iter_ticks(self.root/'recording'))
        self.assertEqual((engine.calls, len(rows), outcome, result['executed_ticks'], result['published_rows']), (3, 3, 'stalled', 3, 3))
        for tick, raw in enumerate(rows):
            runner.bind_interval(raw, result['rows'][tick], result['contact_ownership'], tick)
            self.assertEqual(raw['body_contact_counts'].shape, (11,))
            self.assertFalse(any(key.startswith('nav_teacher') or key == 'nav_advice_action' for key in raw))
        self.assertEqual(engine.writer.tick, self.original_tick); self.assertEqual(engine.policy.act, self.original_act)
        self.assertEqual(modules, {name: sys.modules.get(name) for name in ('torch', 'mujoco')})

    def test_contact_rejection_is_after_complete_record_publication_and_restores_wrappers(self):
        with patch.object(runner.contacts, 'admit_contacts', side_effect=ValueError('forbidden robot self contact')):
            with self.assertRaisesRegex(ValueError, 'forbidden robot'): self.run_fixture(record=True)
        self.engine.writer.finish({}); self.engine.writer.close()
        rows = list(iter_ticks(self.root/'recording'))
        self.assertEqual((len(rows), self.result['published_rows'], self.result['executed_ticks']), (1, 1, 1))
        self.assertEqual(rows[0]['body_contact_ids'].shape, (11, 128, 2))
        self.assertIn('interval_contacts', self.result['first_failure_packet'])
        self.assertEqual(self.engine.policy.act, self.original_act)
        self.assertEqual(self.engine.writer.tick, self.original_tick)

    def test_incomplete_contact_conversion_retains_full_unpublished_numeric_packet(self):
        class Incomplete(old.Probe):
            def end(self):
                packet = super().end(); packet.update(coverage_passed=False, callback_count=9, coverage_errors=['missing stage'])
                return packet
        with self.assertRaisesRegex(ValueError, 'Complete contact'): self.run_fixture(Incomplete)
        result = self.result
        self.assertEqual((len(self.engine.saved), result['published_rows'], result['executed_ticks']), (0, 0, 1))
        self.assertFalse(result['first_failure_packet']['interval_contacts']['coverage_passed'])
        pin = result['pending_packet']; raw = (self.root/pin['path']).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), pin['sha256'])
        with np.load(self.root/pin['path'], allow_pickle=False) as arrays:
            for name in ('cam_left', 'cam_right', 'raw_cam_left', 'raw_cam_right', 'sensors', 'action', 'control'):
                self.assertIn(name, arrays)
                self.assertEqual(hashlib.sha256(arrays[name].tobytes()).hexdigest(), pin['fields'][name]['sha256'])
        self.assertEqual(self.engine.writer.tick, self.original_tick)

    def test_command_error_survives_probe_end_failure_with_obtainable_stages(self):
        class Failing(old.Probe):
            stages = [{'stage': 0, 'pairs': []}]
            def end(self): raise ValueError('end diagnostic failure')
        def command(engine, identifier, kind):
            engine.queued = {'id': identifier}; engine.advance()
            raise RuntimeError('original step failure')
        with self.assertRaisesRegex(RuntimeError, 'original step failure'): self.run_fixture(Failing, command=command)
        row = self.result['first_failure_packet']
        self.assertIn('end diagnostic failure', row['contact_capture_error'])
        self.assertEqual(row['obtainable_stages'], Failing.stages)
        self.assertIn('pending_packet', self.result)
        self.assertEqual(self.engine.policy.act, self.original_act)

    def test_quaternion_control_call_count_and_teacher_fields_reject(self):
        engine, result, _ = self.run_fixture()
        raw, row = engine.saved[0], result['rows'][0]
        for change in ('quaternion', 'control', 'calls', 'teacher'):
            r, meta = copy.deepcopy(raw), copy.deepcopy(row)
            if change == 'quaternion':
                r['nav_dev_quaternion_before'] = np.array([2., 0., 0., 0.]); meta['before_sample']['quaternion'] = [2., 0., 0., 0.]
            if change == 'control': r['control'][0] += .1
            if change == 'calls': meta['policy_calls'] = 2
            if change == 'teacher': r['nav_advice_action'] = np.array([0., 0.])
            with self.assertRaises(ValueError): runner.bind_interval(r, meta, result['contact_ownership'], 0)

    def test_initial_disjointness_and_six_way_matching_before_action(self):
        world = {'arena': 7., 'pose': [0., 0., 0.], 'goal': [2., 2., .5], 'obstacles': [[4., 4., .5]]}
        fingerprint = {'inputs': 'a'*64, 'environment_rng': 'b'*64}
        geometry = runner.initial_admission(world, fingerprint, runner.CASES[0], {'sources': []}, {})
        for prior, earlier, expected in (({'sources': [{'geometry': geometry}]}, {}, None),
                ({'sources': []}, {3109: {'geometry': geometry, 'fingerprint': fingerprint}}, None),
                ({'sources': []}, {}, fingerprint | {'environment_rng': 'c'*64})):
            with self.assertRaises(ValueError): runner.initial_admission(world, fingerprint, runner.CASES[0], prior, earlier, expected)
        self.assertEqual(runner.initial_admission(world, fingerprint, runner.CASES[1], {'sources': []},
            {'3110': {'geometry': geometry, 'fingerprint': fingerprint}}, fingerprint), geometry)

    def test_full_600_row_actual_pretty_publication_and_parent_read_cap(self):
        _, result, _ = self.run_fixture()
        prototype = copy.deepcopy(result['rows'][0])
        for side in ('before_sample', 'after_sample'):
            prototype[side] = {'pose': [1.2345678901234567, -2.3456789012345678, 1.3456789012345678],
                'position_xyz': [1.2345678901234567, -2.3456789012345678, .12345678901234568],
                'quaternion': [.8040302522073697, .30151134457776363, -.40201512610368484, .30151134457776363],
                'time_s': 11.980000000000001}
        prototype['executed_action'] = [.12345679104328156, -1.2345678806304932]
        result.update(status='completed-recording', case=dict(runner.CASES[0]), executed_ticks=600, published_rows=600,
            callback_restored=True, engine_closed=True, outcome='time_limit', wall_seconds=179.12345678901235,
            runtime={'python': '3.11.15', 'numpy': '2.2.5', 'torch_distribution': '2.9.0', 'torch_build': '2.9.0+cu128',
                'mujoco': '3.3.6', 'intraop_threads': 1, 'interop_threads': 1, 'cuda_initialized': False},
            initial_fingerprint={key: 'f'*64 for key in ('world', 'integration', 'environment', 'environment_identity', 'inputs', 'features', 'environment_rng')},
            initial_world={'arena': 7., 'pose': prototype['before_sample']['pose'], 'goal': [4.123456789012346, -3.123456789012346, .5],
                'obstacles': [[1.2345678901234567, -2.3456789012345678, .8123456789012346] for _ in range(20)]},
            geometry={'layout': 'a'*64, 'full_scene': 'b'*64},
            final_state={'phase': 'truncated', 'episode': 0, 'total_tick': 600, 'episode_step': 600,
                'last_outcome': {'reason': 'time_limit', 'steps': 600}, 'metrics': {'path_length': 12.345678901234567},
                'policy_identity': {str(i): 'a'*64 for i in range(14)}})
        result['rows'] = [copy.deepcopy(prototype) | {'tick': tick} for tick in range(600)]
        result['contact_incidence']['admitted_intervals'] = 600
        result['contact_incidence']['pair_instances_by_type_stage'] = [[123456 for _ in range(11)] for _ in range(5)]
        result['contact_incidence']['intervals_by_type_stage'] = [[600 for _ in range(11)] for _ in range(5)]
        result['contact_incidence']['robot_world_pair_instances'] = [123456 for _ in range(125)]
        payload = runner.owner_payload(result)
        path = self.root/'result.json'
        runner.common.publish(path, result, self.budget, time.monotonic()+10, lambda: None)
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(runner.common.read_json(path, maximum=runner.MiB), result)
        self.assertLessEqual(len(payload), runner.MiB)
        with self.assertRaisesRegex(ValueError, 'one-MiB'): runner.owner_payload({'overflow': 'x'*runner.MiB})


if __name__ == '__main__': unittest.main()
