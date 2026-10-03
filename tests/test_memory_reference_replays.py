"""Pure replay admission/invariant/deadline checks; no retained data or native jobs."""
import copy
from contextlib import contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import Mock, patch
import uuid

import numpy as np

PATH = Path(__file__).resolve().parents[1]/'scripts/verify_memory_reference_replays.py'
spec = importlib.util.spec_from_file_location('reference_replay_fixture', PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ReferenceReplays(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.sources = []
        for mode, identifier, count, digest in runner.SOURCES:
            self.sources.append({'mode': mode, 'run_id': identifier, 'ticks': count,
                'snapshot_sha256': digest, 'path': str(runner.SOURCE_ROOT/'runs'/identifier),
                'case': {}, 'initial_guard_sha256': 'a'*64})
        self.identity = {'fixture': True}
        jobs = []
        for source in self.sources:
            for mode in runner.MODES:
                identifier = uuid.uuid4().hex
                jobs.append({'repo': str(runner.REPO), 'assets': str(self.root/'assets'),
                    'root_output': str(self.root/'output'), 'output': str(self.root/'output/runs'/identifier),
                    'run_id': identifier, 'stage': mode, 'reference_mode': source['mode'],
                    'protocol_sha256': runner.PROTOCOL_SHA256, 'source_identity': self.identity, 'source': source})
        self.plan = {'protocol': runner.PROTOCOL, 'protocol_sha256': runner.PROTOCOL_SHA256,
            'output': str(self.root/'output'), 'source_identity': self.identity, 'sources': self.sources, 'jobs': jobs}

    def test_real_validators_bind_six_modes_paths_sources_and_leave_callers_unchanged(self):
        original = runner.memory.canonical_bytes(self.plan)
        self.assertEqual(runner.validate_plan(self.plan), self.plan)
        self.assertEqual(sum(j['source']['ticks'] for j in self.plan['jobs']), 742)
        for field, value in [('repo', str(runner.PRODUCER)), ('run_id', '../escape'),
                ('output', str(self.root/'elsewhere')), ('stage', 'playback'),
                ('reference_mode', runner.SOURCES[1][0])]:
            changed = copy.deepcopy(self.plan['jobs'][0]); changed[field] = value
            with self.assertRaises(ValueError): runner.validate_job(changed)
        for field, value in [('snapshot_sha256', '0'*64), ('ticks', 128), ('path', str(self.root/'other'))]:
            changed = copy.deepcopy(self.plan['jobs'][0]); changed['source'][field] = value
            with self.assertRaises(ValueError): runner.validate_job(changed)
        duplicate = copy.deepcopy(self.plan); duplicate['jobs'][1]['run_id'] = duplicate['jobs'][0]['run_id']
        with self.assertRaises(ValueError): runner.validate_plan(duplicate)
        forged = copy.deepcopy(self.plan); forged['protocol']['held_out'] = 0
        with self.assertRaises(ValueError): runner.validate_plan(forged)
        self.assertEqual(runner.memory.canonical_bytes(self.plan), original)

    def test_normalization_retains_memory_controller_rng_physics_and_commands(self):
        source = {'application': {'source_run_id': 'source', 'event_prefix': {'sha256': 'a'*64},
            'execution_mode': 'live', 'memory': {'u': {}, 'm': {'fact': 'open'}, 'cursor': 299},
            'pending_commands': [], 'revision': 301}, 'policy': {'hidden': np.array([1.], np.float32)},
            'rng': {'numpy': np.array([12], np.uint32)}, 'environment': {'qpos': np.array([.1], np.float64)}}
        destination = copy.deepcopy(source)
        destination['application'].update(source_run_id='destination', event_prefix={}, execution_mode='actions')
        expected = runner.normalized_snapshot(source)
        self.assertEqual(runner.normalized_snapshot(destination), expected)
        for category, field, value in [('application', 'memory', {'m': {}}),
                ('application', 'pending_commands', [{'kind': 'step'}]), ('application', 'revision', 302),
                ('policy', 'hidden', np.array([2.], np.float32)), ('rng', 'numpy', np.array([13], np.uint32)),
                ('environment', 'qpos', np.array([.2], np.float64))]:
            changed = copy.deepcopy(destination); changed[category][field] = value
            self.assertNotEqual(runner.normalized_snapshot(changed), expected)
        self.assertEqual(source['application']['execution_mode'], 'live')

    def test_real_ready_guard_reads_string_source_path_without_relaxing_events_api(self):
        """Real bounded snapshot/event files; synthetic state, no native decode/model."""
        from palimpsest.snapshots import save_snapshot
        job = copy.deepcopy(self.plan['jobs'][0]); destination = Path(job['output'])
        source = self.root/uuid.uuid4().hex
        (source/'recording').mkdir(parents=True)
        (destination/'recording').mkdir(parents=True); (destination/'snapshots').mkdir()
        native = {'application': {'source_run_id': job['run_id'], 'event_prefix': {},
            'execution_mode': job['stage'], 'memory': {'cursor': 299, 'fixture': True}},
            'native_sha256': hashlib.sha256(b'synthetic-native-not-decoded').hexdigest(),
            'policy': {'hidden': np.array([1.], np.float32)}}
        path = destination/'snapshots/initial.snp'; save_snapshot(native, path)
        job['source'].update(path=str(source), initial_guard_sha256=runner.normalized_snapshot(native))
        from palimpsest.replay import _RUNTIME, _REFERENCE_RUNTIME
        environment = {'sequence': 0, 'kind': 'environment', 'upstream_commit': 'fixture',
            'lock_sha256': 'a'*64, 'source_sha256': {k: 'b'*64 for k in _RUNTIME+_REFERENCE_RUNTIME}}
        (source/'recording/events.jsonl').write_text(json.dumps(environment)+'\n')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        registration = {'sequence': 1, 'kind': 'snapshot_registered', 'run_id': job['run_id'],
            'snapshot_id': uuid.uuid4().hex, 'initial': True, 'sha256': digest, 'filename': 'initial.snp'}
        (destination/'recording/events.jsonl').write_text(json.dumps(environment)+'\n'+json.dumps(registration)+'\n')
        (destination/'recording/manifest.json').write_text(json.dumps({'run_id': job['run_id'], 'recording_format': 'palimpsest-npz-v1'}))
        result = runner.ready_guard(destination, job)
        self.assertEqual(result['snapshot_sha256'], digest)
        self.assertEqual(result['initial_guard_sha256'], runner.normalized_snapshot(native))
        self.assertIs(type(job['source']['path']), str)
        with self.assertRaises(TypeError): runner.artifacts._events(str(source))
        altered = copy.deepcopy(job); altered['source']['initial_guard_sha256'] = '0'*64
        with self.assertRaises(ValueError): runner.ready_guard(destination, altered)

    def test_final_close_and_source_recheck_deadline_cannot_admit_worker_pass(self):
        job = self.plan['jobs'][0]; run = Path(job['output']); run.mkdir(parents=True)
        (run/'replay-report.json').write_text('{}')
        report = {'status': 'passed', 'compared_ticks': job['source']['ticks']}
        def replay(*args, **kwargs):
            self.assertEqual(kwargs['recording_max_bytes'], 192*runner.MiB)
            self.assertEqual(kwargs['mode'], 'actions')
            kwargs['progress']('ready')
            return report
        stored = []
        with patch.object(runner, 'source_identity', return_value=self.identity), \
                patch.object(runner, 'source_evidence', return_value=self.sources), \
                patch.object(runner, 'ready_guard', return_value={'fixture': True}), \
                patch.object(runner, 'replay_run', side_effect=replay), \
                patch.object(runner.neural, 'write', side_effect=lambda p,v,s: stored.append(v)), \
                patch.object(runner.time, 'monotonic', side_effect=[0., 1., 151.]):
            self.assertEqual(runner.worker(job), 1)
        self.assertEqual(stored[-1]['status'], 'failed')
        self.assertEqual(stored[-1]['wall_seconds'], 151.)
        self.assertTrue(stored[-1]['source_unchanged'])

    def test_before_next_owner_failure_preserves_previous_pass_and_unattempted_queue(self):
        storage = Mock()
        @contextmanager
        def lease():
            Path(self.plan['output']).mkdir()
            yield
        storage.lock.side_effect = lease
        stored = []
        with patch.object(runner, 'source_identity', return_value=self.identity), \
                patch.object(runner, 'source_evidence', return_value=self.sources), \
                patch.object(runner, 'budget', return_value=storage), \
                patch.object(runner.shutil, 'disk_usage', return_value=SimpleNamespace(free=10*runner.GiB)), \
                patch.object(runner, 'bounded_process', return_value={'status': 'completed', 'returncode': 0}) as child, \
                patch.object(runner, 'validate_stage', return_value={'status': 'passed'}), \
                patch.object(runner.neural, 'write', side_effect=lambda p,v,s: stored.append(copy.deepcopy(v))), \
                patch.object(runner.time, 'monotonic', side_effect=[0., 1., 861., 862.]):
            self.assertEqual(runner.run_verifier(self.plan), 1)
        child.assert_called_once()
        report = stored[-1]
        self.assertEqual(report['runs'][0]['status'], 'passed')
        self.assertEqual([r['status'] for r in report['runs'][1:]], ['unattempted']*5)
        self.assertEqual(report['first_failure']['run_id'], self.plan['jobs'][1]['run_id'])
        self.assertEqual(report['first_failure']['scope'], 'before-owner')


if __name__ == '__main__':
    unittest.main()
