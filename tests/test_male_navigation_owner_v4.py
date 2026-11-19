"""A2 S2 owner worker and parent: orchestration on synthetic owners; no simulator, Torch, checkpoint or real data."""
import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

import evaluate_male_navigation_v4 as evaluator
from palimpsest import male_model
import test_male_navigation_development_v4 as dev

ROOT = Path(__file__).resolve().parents[1]
OWNER_BLOCK = inspect.getsource(evaluator).split('# --------------------------------------------------------------------------- A2 native owner')[1].split('\ndef main(')[0]


class Source(unittest.TestCase):
    def test_amendment_constant_is_the_pinned_file_and_base_protocol_is_untouched(self):
        raw = (ROOT / evaluator.AMENDMENT_PATH).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), evaluator.AMENDMENT_SHA256)
        self.assertEqual(evaluator.check_amendment(ROOT), evaluator.AMENDMENT_SHA256)
        base = (ROOT / evaluator.trainer.PROTOCOL_PATH).read_bytes()
        self.assertEqual(hashlib.sha256(base).hexdigest(), evaluator.PROTOCOL_SHA256)
        with tempfile.TemporaryDirectory() as folder:
            (Path(folder) / 'docs/plans').mkdir(parents=True)
            (Path(folder) / evaluator.AMENDMENT_PATH).write_bytes(raw + b' ')
            with self.assertRaises(evaluator.Refusal):
                evaluator.check_amendment(folder)

    def test_worker_defines_no_thresholds_scene_lists_or_case_tables_and_no_held_out_or_retry(self):
        for token in ('3160', '3161', '3170', '3177', 'DEVELOPMENT_GOALS =', 'HELD_OUT_GOALS =', '_cases(', "'held-out'"):
            self.assertNotIn(token, OWNER_BLOCK, token)
        self.assertEqual(len(re.findall(r'^CASES = ', inspect.getsource(evaluator), re.M)), 1)
        self.assertIn("evaluate('development', CASES, owner, lambda rows: reduce_development(rows, prior))", OWNER_BLOCK)
        self.assertIn('check_case(config', OWNER_BLOCK)
        self.assertIn('def reduce(', inspect.getsource(evaluator)); self.assertIn('def check_protocol(', inspect.getsource(evaluator))
        self.assertNotIn('evaluate_male_navigation_v2 import reduce', OWNER_BLOCK)
        self.assertNotIn('male_navigation_research import', OWNER_BLOCK)           # only the v4 binding module

    def test_v4_binding_and_v4_constants_only(self):
        self.assertIn('male_navigation_research_v4', OWNER_BLOCK)
        self.assertIn('research.Binding(case[', OWNER_BLOCK)
        self.assertEqual(evaluator.OWNER_SECONDS, 180); self.assertEqual(evaluator.STAGE_SECONDS, 1800)
        self.assertEqual({c['scene_seed'] for c in evaluator.CASES}, set(dev.DEV)); self.assertEqual(len(evaluator.CASES), 24)

    def test_every_owner_input_is_a_fixed_case_and_held_out_ids_are_refused(self):
        for scene in dev.HELD + (3159, 3164):
            case = {**evaluator.CASES[0], 'scene_seed': scene, 'id': f'dev-{scene}-seed-10-old-corpus'}
            with self.assertRaises(evaluator.Refusal):
                evaluator.check_case(case, evaluator.CASES)

    def test_parent_has_no_held_out_entry_point(self):
        self.assertNotIn('held_out(', inspect.getsource(evaluator.run_development))
        self.assertNotIn('admit_held_out', inspect.getsource(evaluator.run_development))
        with self.assertRaises(evaluator.Refusal):
            evaluator.native_owner(evaluator.CASES[0])

    def test_worker_refuses_a_visible_cuda_device_and_publishes_a_failure_result(self):
        with tempfile.TemporaryDirectory() as folder:
            stage, root = Path(folder) / 'stage', Path(folder)
            stage.mkdir()
            config = {'repo': str(ROOT), 'run': str(stage / 'run'), 'stage': str(stage), 'case': evaluator.CASES[0],
                      'source_pins': {}, 'storage': {'roots': [folder], 'headroom_bytes': 0,
                                                     'limits': {'max_bytes': 64 * 1024**2, 'min_free_bytes': 0, 'max_runs': 24,
                                                                'max_snapshots': 1, 'max_exports': 1}}}
            with patch.object(evaluator, 'check_pins'), patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '0'}):
                self.assertFalse(evaluator.worker(config))
            result = json.loads((stage / 'result.json').read_text())
            self.assertEqual(result['status'], 'failed-infrastructure'); self.assertIn('CUDA', result['error']['message'])
            config['case'] = {**evaluator.CASES[0], 'scene_seed': 3170}
            with patch.object(evaluator, 'check_pins'), patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': ''}):
                (stage / 'result.json').unlink()
                self.assertFalse(evaluator.worker(config))
            self.assertIn('Exact fresh scene', json.loads((stage / 'result.json').read_text())['error']['message'])


def prior():
    return dev.prior()


class Parent(unittest.TestCase):
    """run_development with the worker process, S1 admission, records and assets replaced by fakes."""

    def run_stage(self, fail_at=None, good=None):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        base = Path(folder.name); (base / 's1').mkdir(); (base / 'assets').mkdir(); output = base / 'out'
        calls = []

        def fake_process(command, out, timeout, env=None, **kw):
            stage = Path(command[-1] and json.loads(command[-1])['stage']); case = json.loads(command[-1])['case']
            calls.append({'case': case, 'timeout': timeout, 'env': env, 'command': command})
            (stage / f"{case['scene_seed']}.snp").write_bytes(b'x')
            if len(calls) == fail_at:
                return {'status': 'timeout', 'returncode': None, 'elapsed_seconds': timeout}
            goal = case['arm'] == 'augmented' and (good is None or case['scene_seed'] in good)
            (stage / 'result.json').write_text(json.dumps(dev.owner_result(case, goal)))
            return {'status': 'completed', 'returncode': 0, 'elapsed_seconds': 1.0}

        def fake_record(run, result, child):
            return {k: result[k] for k in ('geometry', 'initial_fingerprint', 'raw_payload_sha256', 'ticks')}

        args = argparse.Namespace(repo=ROOT, assets=base / 'assets', output=output, s1_output=base / 's1', corpus_pin=base / 'pin.json')
        fake_s1 = ({'corpus_pin_sha256': 'a' * 64, 'data_manifest_sha256': 'b' * 64}, 'c' * 64)
        pins = {'pinned': 'x'}
        with patch.object(evaluator, 'source_pins', return_value=pins), patch.object(evaluator, 'admit_candidates', return_value=fake_s1), \
                patch.object(evaluator, 'prior_metadata', return_value={**prior(), 'data_manifest_sha256': 'b' * 64}), \
                patch.object(evaluator, 'candidates', side_effect=lambda r, a: {f'{s}:{a_}': {'id': f'{s}{a_}'}
                                                                               for s in evaluator.SEEDS for a_ in evaluator.ARMS}), \
                patch.object(evaluator, 'admit_record', side_effect=fake_record), \
                patch('palimpsest.evaluate.bounded_process', side_effect=fake_process), \
                patch('palimpsest.assets.verify_assets', return_value={'ok': True}), \
                patch('shutil.disk_usage', return_value=type('U', (), {'free': 1 << 50})()):
            report = evaluator.run_development(args)
        return report, calls, output

    def test_full_stage_runs_24_fresh_one_thread_owners_in_order_and_publishes_last(self):
        report, calls, output = self.run_stage()
        self.assertEqual(report['status'], 'completed'); self.assertEqual(report['admission']['status'], 'passed-gate')
        self.assertEqual([c['case'] for c in calls], list(evaluator.CASES))
        for call in calls:
            self.assertLessEqual(call['timeout'], 180)
            self.assertEqual({k: call['env'][k] for k in ('MUJOCO_GL', 'OMP_NUM_THREADS', 'CUDA_VISIBLE_DEVICES', 'PYTHONPATH')},
                             {'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '1', 'CUDA_VISIBLE_DEVICES': '', 'PYTHONPATH': str(ROOT / 'src')})
            self.assertEqual(call['command'][-2], '--worker'); self.assertTrue(Path(call['command'][1]).is_absolute())
        published = json.loads((output / 'report.json').read_text())
        self.assertEqual((published['amendment_2_sha256'], published['protocol_sha256']),
                         (evaluator.AMENDMENT_SHA256, evaluator.PROTOCOL_SHA256))
        self.assertFalse((output / 'failure.json').exists()); self.assertFalse((output / 'report.pending').exists())

    def test_a_failing_development_locks_held_out_and_a_passing_one_only_marks_it_eligible(self):
        report, _, output = self.run_stage(good=set(dev.DEV[:2]))
        self.assertEqual(report['admission']['status'], 'failed-gate')
        self.assertEqual(report['admission']['held_out_status'], 'locked-permanently')
        report, _, output = self.run_stage()
        self.assertEqual(report['admission']['held_out_status'], 'eligible-pending-separate-owner-go')
        self.assertNotIn('held-out', json.dumps([c['case'] for c in report['cases'].values()]))
        self.assertEqual(sorted({c['case']['scene_seed'] for c in report['cases'].values()}), list(dev.DEV))

    def test_first_owner_failure_stops_with_no_retry_or_replacement(self):
        report, calls, output = self.run_stage(fail_at=5)
        self.assertEqual(len(calls), 5)                                  # no retry, no later owner
        self.assertEqual(report['status'], 'operational-failure')
        statuses = [row['status'] for row in report['cases'].values()]
        self.assertEqual(statuses[:4], ['completed-recording'] * 4); self.assertEqual(statuses[4], 'operational-failure')
        self.assertEqual(set(statuses[5:]), {'not_started'})
        self.assertNotEqual(report['admission']['status'], 'passed-gate')
        published = json.loads((output / 'report.json').read_text())          # retained, never replaced
        self.assertEqual(published['admission']['status'], 'not-admitted-operational-failure')

    def test_refuses_overlapping_or_existing_output_before_any_owner(self):
        base = Path(tempfile.mkdtemp()); self.addCleanup(lambda: __import__('shutil').rmtree(base))
        for output in (ROOT / 'x-out', base, base / 'assets' / 'out'):
            (base / 'assets').mkdir(exist_ok=True)
            args = argparse.Namespace(repo=ROOT, assets=base / 'assets', output=output, s1_output=base / 's1', corpus_pin=base / 'p')
            with patch('palimpsest.evaluate.bounded_process') as process, self.assertRaises(evaluator.Refusal):
                evaluator.run_development(args)
            process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
