"""Pure fixed-owner/control/input fixtures; no model, native execution or history data."""
import copy
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

import numpy as np
from palimpsest import memory, snapshots
from palimpsest.engine import Engine
import test_memory_references as admission_fixtures

PATH = Path(__file__).resolve().parents[1]/'scripts/verify_memory_references.py'
spec = importlib.util.spec_from_file_location('reference_verifier_fixture', PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ReferenceVerifier(unittest.TestCase):
    def setUp(self):
        self.admission = admission_fixtures.MemoryReferences('runTest')
        self.admission.setUp()
        self.addCleanup(self.admission.doCleanups)
        self.root = self.admission.fixture.root
        self.source = self.admission.source

    def test_real_fixed_job_validator_rejects_substitution_and_wrong_paths(self):
        binding = {'cell': [24, 'local_cue', 'change'], 'case': self.admission.case}
        data = {'bindings': {runner.key(binding['cell']): binding}}
        filename = self.root/'bindings.json'
        runner.common._write(filename, data)
        run_id = uuid.uuid4().hex
        job = {'repo': str(runner.REPO), 'assets': str(self.root/'assets'), 'root_output': str(self.root/'output'),
            'output': str(self.root/'output/runs'/run_id), 'run_id': run_id, 'cell': binding['cell'],
            'stage': runner.MODES[0], 'protocol_sha256': runner.PROTOCOL_SHA256,
            'source_identity': {}, 'bindings_path': str(filename), 'bindings_sha256': runner.common._hash(filename),
            'binding': binding}
        self.assertEqual(runner.validate_job(job), job)
        before = memory.canonical_bytes(job)
        for field, value in [('run_id', '../escape'), ('repo', str(runner.HISTORICAL)),
                ('output', str(self.root/'wrong')), ('stage', 'custom'), ('bindings_sha256', '0'*64),
                ('binding', {**binding, 'cell': [25, 'local_cue', 'change']})]:
            altered = copy.deepcopy(job); altered[field] = value
            with self.assertRaises((ValueError, KeyError)): runner.validate_job(altered)
        self.assertEqual(memory.canonical_bytes(job), before)

    def test_original_sampler_preserves_raw_input_and_binds_numpy_audit_copy(self):
        recorded = []
        observation = {'cam_left': np.zeros((2,2,3), np.uint8), 'cam_right': np.ones((2,2,3), np.uint8),
            'sensors': {'collision': False, 'collision_angle': None,
                        'wind_direction': np.array([.8, .6], np.float32)}}
        result = {'action': np.array([.25, .1], np.float32), 'encoded_input': np.zeros(4813, np.float32),
                  'raw_output': np.zeros(2, np.float32)}
        policy = SimpleNamespace(act=Mock(return_value=result))
        original = policy.act
        def event(kind, **data):
            json.dumps(data, allow_nan=False)
            recorded.append({'kind': kind, 'episode': 0, 'tick': 300, 'episode_step': 300, **data})
        engine = SimpleNamespace(policy=policy, _event=event)
        before = snapshots.state_digest(observation)
        runner.audit_original(engine)
        self.assertIs(policy.act(observation), result)
        self.assertIs(original.call_args.args[0], observation)
        self.assertEqual(snapshots.state_digest(observation), before)
        row = {**result, 'tick': 300, 'cam_left': observation['cam_left'], 'cam_right': observation['cam_right'],
               'sensors': np.array([0., 0., .8, .6], np.float32)}
        events = [*recorded, {'kind': 'memory_reference_input', 'episode': 0, 'tick': 300, 'episode_step': 300, 'inputs': recorded[0]['sensors']},
            {'kind': 'memory_reference_sensed', 'episode': 0, 'tick': 300, 'episode_step': 300, 'packet': {}}]
        runner.input_bindings({'rows': [row], 'events': events}, runner.MODES[0])
        tampered = {**row, 'action': np.array([1., 0.], np.float32)}
        with self.assertRaises(ValueError):
            runner.input_bindings({'rows': [tampered], 'events': events}, runner.MODES[0])
        with self.assertRaises(ValueError):
            policy.act({**observation, 'sensors': {**observation['sensors'], 'wind_direction': [.8, .6]}})

    def test_sensor_action_binding_uses_existing_manual_float64_and_no_fallback(self):
        packet = self.admission.fixture.packet(self.admission.fixture.engines[-1], 300)
        packet['landmarks'][-1]['bearing_rad'] = .123456789
        inputs = runner.reference.sensor_input(packet, False)
        row = {'tick': 300, 'sensors': np.array([0, 0, *inputs['bearing']], np.float32),
               'action': np.asarray(runner.reference.sensor_action(inputs), np.float64)}
        events = [{'kind': 'memory_reference_input', 'episode': 0, 'tick': 300, 'episode_step': 300, 'inputs': inputs},
            {'kind': 'memory_reference_sensed', 'episode': 0, 'tick': 300, 'episode_step': 300, 'packet': packet}]
        runner.input_bindings({'rows': [row], 'events': events}, runner.MODES[1])
        with self.assertRaises(ValueError):
            runner.input_bindings({'rows': [{**row, 'action': row['action'].astype(np.float32)}], 'events': events}, runner.MODES[1])
        self.assertTrue(runner.task_failure({'mode': runner.MODES[1], 'final_phase': 'failed',
            'outcome': {'type': 'CueUnavailable', 'message': 'Sensor-only reference common goal is not visible'}}))
        for mode, message in [(runner.MODES[0], 'Sensor-only reference common goal is not visible'),
                              (runner.MODES[1], 'arbitrary failure')]:
            self.assertFalse(runner.task_failure({'mode': mode, 'final_phase': 'failed',
                'outcome': {'type': 'CueUnavailable', 'message': message}}))

    def test_final_step_cleanup_deadline_cannot_be_admitted(self):
        run = self.root/'late'; (run/'snapshots').mkdir(parents=True)
        snapshots.save_snapshot(self.source, run/'snapshots/initial.snp')
        ancestor = self.root/'source.snp'; snapshots.save_snapshot(self.source, ancestor)
        binding = {'snapshot_path': str(ancestor), 'case': self.admission.case}
        job = {'bindings_path': str(self.root/'fixture.json'), 'bindings_sha256': 'a'*64,
            'binding': binding, 'cell': [24, 'local_cue', 'change'], 'stage': runner.MODES[1],
            'output': str(run), 'root_output': str(self.root), 'assets': str(self.root),
            'source_identity': {'fixture': True}, 'run_id': run.name}
        engine = SimpleNamespace(env=None, observation=None, policy=None, teacher=None,
            application_state=lambda: self.source['application'], writer=SimpleNamespace(manifest={}),
            episode_step=301, phase='terminated', last_outcome={'reason': 'goal'},
            memory=self.source['application']['memory'], world_task_state=self.source['application']['world_task_state'], close=Mock())
        stored = []
        with patch.object(runner, 'validate_job', return_value=job), \
                patch.object(runner, 'validate_bindings', return_value={'bindings': {runner.key(job['cell']): binding}, 'reader_identity': {}}), \
                patch.object(runner.neural, 'read_prepared_plan', return_value={}), \
                patch.object(runner, 'source_identity', return_value=job['source_identity']), \
                patch.object(runner, 'budget', return_value=Mock()), \
                patch.object(Engine, 'open', return_value=engine), \
                patch.object(runner, 'capture', return_value=self.source), \
                patch.object(runner, '_register_initial'), \
                patch.object(runner, 'reference_step', return_value={'phase': 'terminated'}), \
                patch.object(runner.neural, 'write', side_effect=lambda p,v,s: stored.append(copy.deepcopy(v))), \
                patch.object(runner.time, 'monotonic', side_effect=[0., 1., 151.]):
            code = runner.worker(job)
        engine.close.assert_called_once()
        self.assertEqual(code, 1)
        self.assertEqual(stored[-1]['status'], 'deadline_failed')
        self.assertEqual(stored[-1]['wall_seconds'], 151.)

    def test_final_parent_rechecks_cannot_publish_a_late_pass(self):
        output = self.root/'aggregate'
        jobs = [{'run_id': uuid.uuid4().hex, 'cell': list(cell), 'stage': mode, 'assets': str(self.root),
                 'bindings_path': str(self.root/'bindings'), 'bindings_sha256': 'a'*64}
                for cell in runner.CELLS for mode in runner.MODES]
        for job in jobs: job['output'] = str(output/'runs'/job['run_id'])
        for job in jobs: job['binding'] = {'case': self.admission.case, 'before_circles': []}
        plan = {'output': str(output), 'jobs': jobs, 'source_identity': {'fixture': True}, 'reader_identity': {}}
        storage = Mock()
        @contextmanager
        def lease():
            output.mkdir()
            yield
        storage.lock.side_effect = lease
        def stage(job, supervised):
            data = {'run': Path(job['output']), 'rows': [], 'events': [], 'paths': [], 'fingerprint': runner.artifacts._fingerprint([])}
            return data, {'final_phase': 'paused', 'outcome': None, 'steps': 600,
                          'final_world': {'gate_result': 'closed'}}, {}, {'sha256': 'a'*64}
        stored = []
        with patch.object(runner, 'validate_plan', return_value=plan), \
                patch.object(runner, 'validate_job'), patch.object(runner, 'validate_bindings'), \
                patch.object(runner.neural, 'read_prepared_plan', return_value={}), \
                patch.object(runner, 'source_identity', return_value=plan['source_identity']), \
                patch.object(runner, 'budget', return_value=storage), \
                patch.object(runner.shutil, 'disk_usage', return_value=SimpleNamespace(free=10*runner.GiB)), \
                patch.object(runner, 'bounded_process', return_value={'status': 'completed', 'returncode': 0}), \
                patch.object(runner, 'validate_stage', side_effect=stage), \
                patch.object(runner.common, '_hash', return_value='a'*64), \
                patch.object(runner.common, 'occupancy', return_value={}), \
                patch.object(runner.artifacts, '_world_at', return_value={'obstacles': []}), \
                patch.object(runner.neural, 'write', side_effect=lambda p,v,s: stored.append(copy.deepcopy(v))), \
                patch.object(runner.time, 'monotonic', side_effect=[0., *([1.]*6), 1021.]), \
                patch('builtins.print'):
            code = runner.run_verifier(plan)
        self.assertEqual(code, 1)
        result = stored[-1]
        self.assertEqual(result['status'], 'reference_unverified')
        self.assertEqual(result['wall_seconds'], 1021.)
        self.assertTrue(all(r['admission_pass'] for r in result['runs']))
        self.assertEqual(len(result['runs']), 6)
        self.assertEqual(result['aggregate_deadline_error']['type'], 'TimeoutError')


if __name__ == '__main__':
    unittest.main()
