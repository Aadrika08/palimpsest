"""Pure batch orchestration checks; no simulator or acquisition children."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from palimpsest import memory, memory_history
import test_memory_history as history_fixtures


class AcquisitionBatchTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/acquire_memory_history.py'
        spec = importlib.util.spec_from_file_location('acquire_memory_history', path)
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)
        quiet = patch.object(self.runner, 'print', create=True)
        quiet.start()
        self.addCleanup(quiet.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = Path(__file__).resolve().parents[1]

    def test_fixed_fresh_cases_budgets_and_protocol_identity(self):
        plan = self.runner.make_plan(self.repo, self.root / 'assets', self.root / 'batch')
        self.assertEqual([(j['case']['regime'], j['case']['seed']) for j in plan['jobs']],
                         [(r, s) for r in memory.RELATIONS for s in range(4)])
        self.assertEqual(len({j['run_id'] for j in plan['jobs']}), 8)
        self.assertEqual(len({j['run_path'] for j in plan['jobs']}), 8)
        schedules = [j['case']['acquisition_schedule'] for j in plan['jobs']]
        self.assertTrue(all(s == schedules[0] for s in schedules))
        self.assertEqual(plan['protocol']['timeout_seconds'], 160)
        self.assertEqual(plan['protocol']['recording_max_bytes'], 192 * 1024**2)
        self.assertEqual(plan['protocol']['collector_input_max_bytes'], 512 * 1024**2)
        self.assertEqual(plan['protocol_sha256'], memory.sha256(plan['protocol']))
        self.assertTrue(all(j['case']['split'] == 'development-history' and j['case']['kind'] == 'change'
                            for j in plan['jobs']))
        bad_plan = copy.deepcopy(plan)
        bad_plan['jobs'].append(bad_plan['jobs'][0])
        with self.assertRaises(ValueError):
            self.runner.run_batch(bad_plan)
        self.assertFalse(Path(plan['output']).exists())
        bad = dict(plan['jobs'][0], batch_protocol_sha256='0' * 64)
        with self.assertRaises(ValueError):
            self.runner.validate_job(bad)

    def test_serial_failures_are_retained_without_retry_or_partial_substitution(self):
        plan = self.runner.make_plan(self.repo, self.root / 'assets', self.root / 'batch')
        calls = []
        def failed(command, output, timeout, env, **kwargs):
            calls.append((json.loads(command[-1]), output, timeout, kwargs))
            return {'status': 'timeout', 'returncode': -15}
        with patch.object(self.runner, 'bounded_process', side_effect=failed), \
             patch.object(self.runner, 'collect_history', side_effect=ValueError('missing source')) as collect:
            result = self.runner.run_batch(plan)
        self.assertEqual(len(calls), 8)
        self.assertEqual([call[0]['run_id'] for call in calls], [j['run_id'] for j in plan['jobs']])
        self.assertTrue(all(call[2] == 160 and call[3]['log_max_bytes'] == 1024**2 for call in calls))
        self.assertEqual(len(result['runs']), 8)
        self.assertTrue(all(run['status'] == 'failed' for run in result['runs']))
        self.assertEqual(collect.call_count, 2)
        for args, jobs in zip(collect.call_args_list, (plan['jobs'][:4], plan['jobs'][4:])):
            self.assertEqual(args.args, ([Path(j['run_path']) for j in jobs],))
        self.assertEqual(result['status'], 'incomplete')
        self.assertTrue(all(g['status'] == 'rejected' for g in result['histories']))
        self.assertEqual(json.loads((self.root / 'batch/batch-report.json').read_text()), result)
        with self.assertRaises(FileExistsError):
            self.runner.run_batch(plan)

    def test_admission_binds_case_driver_sources_and_actual_coverage(self):
        # Mock only the already-tested numeric reader; metadata/packets are fixtures.
        plan = self.runner.make_plan(self.repo, self.root / 'assets', self.root / 'batch')
        job, identity = plan['jobs'][0], plan['source_identity']
        run = Path(job['run_path'])
        run.mkdir(parents=True)
        report = {'run_path': str(run), 'status': 'coverage_observed', 'gate_result': 'closed'}
        (run / 'acquisition-report.json').write_text(json.dumps(report))
        case = job['case']
        manifest = {'memory_case': case, 'memory_case_sha256': memory.sha256(case),
            'acquisition_protocol_sha256': self.runner.PROTOCOL['schedule_sha256'],
            'acquisition_batch_protocol': self.runner.PROTOCOL,
            'acquisition_driver': {'sha256': identity['driver_sha256'], 'name': 'acquire_memory_history.py',
                'access': self.runner.PROTOCOL['access'], 'uses_u': False,
                'protocol_sha256': case['acquisition_protocol_sha256'],
                'batch_protocol_sha256': self.runner.PROTOCOL_SHA256},
            'initial_memory': {'m': memory.sha256(memory.seed_m(case['facts'], [])),
                'e': memory.sha256({'version': 1, 'episodes': []}),
                'u': memory.sha256(memory.artifact(method='empty-v1'))},
            'controller': 'manual', 'requested_device': 'cpu', 'seed': 0,
            'recording_max_bytes': 192 * 1024**2, 'recorded_ticks': 331}
        events = [{'kind': 'environment', **{k: identity[k] for k in
            ('source_sha256', 'lock_sha256', 'upstream_commit')}}]
        events += [{'kind': 'memory_sensed', 'packet': {'tick': tick, 'passages':
            [{'subject_id': subject, 'passability': 'open'} for subject in case['subjects_by_side']]}}
            for tick in range(331)]
        events += [{'kind': 'memory_decision', 'detail': {'kind': 'memory_trigger',
            'trigger': {'tick': 300, 'cue_id': case['cue_id']}}},
            {'kind': 'memory_world_changed', 'detail': {'kind': 'memory_gate_applied',
                'tick': 300, 'subject_id': case['closure_subject_id']}}]
        data = {'manifest': manifest, 'events': events, 'episodes': {0: {}}}
        with patch.object(self.runner.artifacts, '_load', return_value=data):
            self.assertEqual(self.runner._admit_run(job, identity)['recorded_ticks'], 331)
        for defect in ('case', 'driver', 'source', 'initial', 'coverage', 'trigger'):
            bad = copy.deepcopy(data)
            if defect == 'case':
                bad['manifest']['memory_case']['version'] = True
            elif defect == 'driver':
                bad['manifest']['acquisition_driver']['uses_u'] = 0
            elif defect == 'source':
                bad['events'][0]['lock_sha256'] = '0' * 64
            elif defect == 'initial':
                bad['manifest']['initial_memory']['m'] = '0' * 64
            elif defect == 'trigger':
                bad['events'][-2]['detail']['trigger']['tick'] = 299
            else:
                for event in bad['events']:
                    if event['kind'] == 'memory_sensed' and event['packet']['tick'] >= 300:
                        event['packet']['passages'][0]['passability'] = 'unobserved'
            with self.subTest(defect=defect), patch.object(self.runner.artifacts, '_load', return_value=bad):
                with self.assertRaises(ValueError):
                    self.runner._admit_run(job, identity)

    def test_real_fixture_collection_retains_gaps_and_fits_e_only(self):
        # Children/admission are mocked; these numeric recordings are synthetic.
        fixtures = history_fixtures.HistoryTests()
        fixtures.setUp()
        self.addCleanup(fixtures.doCleanups)
        plan = self.runner.make_plan(self.repo, self.root / 'assets', self.root / 'batch')
        count = 0
        def recorded(command, output, timeout, env, **kwargs):
            nonlocal count
            job = json.loads(command[-1])
            run = fixtures.recording(missing=count == 0)
            manifest_path = run / 'recording/manifest.json'
            manifest = json.loads(manifest_path.read_text())
            manifest['run_id'] = job['run_id']
            manifest_path.write_text(json.dumps(manifest))
            fixtures.edit_events(run, lambda events: [event.update(run_id=job['run_id'])
                for event in events if 'run_id' in event])
            run.rename(output)
            count += 1
            return {'status': 'completed', 'returncode': 0}
        with patch.object(self.runner, 'bounded_process', side_effect=recorded), \
             patch.object(self.runner, '_admit_run', return_value={'fixture_admission_mock': True}), \
             patch.object(memory, 'fit', wraps=memory.fit) as fit:
            result = self.runner.run_batch(plan)
        self.assertEqual(fit.call_count, 2)
        self.assertTrue(all(set(call.args[0]) == {'version', 'episodes'} and len(call.args) == 1
                            and not call.kwargs for call in fit.call_args_list))
        own, other = result['histories']
        self.assertEqual(own['status'], 'incomplete')
        self.assertTrue(own['gaps'])
        self.assertEqual(own['support']['local_cue'], {'observed': 3, 'changed': 3})
        self.assertEqual(own['rules'], [])
        # Fixture evidence stays local even in the paired-labelled group:
        # regime metadata cannot manufacture a paired rule.
        self.assertEqual(other['rules'], [{'trigger': 'cue_changed', 'relation': 'local_cue'}])
        bundle = json.loads(Path(own['report_path']).read_text())
        self.assertEqual(len(bundle['sources']), 4)
        self.assertEqual(bundle['u']['provenance']['history_sha256'], memory.sha256(bundle['e']))

    def test_source_mutation_fails_batch_without_claiming_qualification(self):
        plan = self.runner.make_plan(self.repo, self.root / 'assets', self.root / 'batch')
        with patch.object(self.runner, 'bounded_process', return_value={'status': 'failed', 'returncode': 1}), \
             patch.object(self.runner, 'collect_history', side_effect=ValueError('failed recording')), \
             patch.object(self.runner, 'source_identity', return_value={'changed': True}):
            result = self.runner.run_batch(plan)
        self.assertFalse(result['source_unchanged'])
        self.assertEqual(result['status'], 'incomplete')
        self.assertFalse(result['r2_complete'])


if __name__ == '__main__':
    unittest.main()
