import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import subprocess

from palimpsest.evaluate import _evaluation_preflight, bounded_process, evaluate, outcome
from palimpsest.storage import StorageBudget, StorageLimits, StorageLimitError


class EvaluationTests(unittest.TestCase):
    def args(self, output, **changes):
        return SimpleNamespace(**{'output': output, 'controller': 'teacher', 'device': 'cpu', 'episodes': 1,
            'max_steps': 1, 'seed': 0, 'parity': False, 'max_bytes': 1024**2, 'threads': 1, 'timeout': 2,
            **changes})

    def test_batch_preflight_counts_written_cameras_and_input_without_hidden_dump(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = {'output': str(root / 'run'), 'episodes': 2, 'max_steps': 3, 'max_bytes': 4 * 1024**2}
            observation = {'cam_left': memoryview(bytes(6)), 'cam_right': memoryview(bytes(12))}
            policy = SimpleNamespace(agent=SimpleNamespace(cell=SimpleNamespace(Nin=8)),
                                     hidden=SimpleNamespace(element_size=lambda: 4))
            budget = StorageBudget((root,), StorageLimits(max_bytes=8 * 1024**2, min_free_bytes=0))
            report = _evaluation_preflight(observation, policy, config, budget)
            self.assertEqual(report['planned_ticks'], 6)
            self.assertEqual(report['raw_camera_bytes_per_tick'], 18)
            self.assertEqual(report['neural_bytes_per_tick'], 40)
            self.assertEqual(report['recording_bytes_estimate'], 6 * (18 + 40 + 4096) + 1024**2)
            self.assertFalse((root / 'run').exists())
            with self.assertRaisesRegex(RuntimeError, 'per-recording quota'):
                _evaluation_preflight(observation, policy, {**config, 'max_bytes': 1024}, budget)
            small = StorageBudget((root,), StorageLimits(max_bytes=1024, min_free_bytes=0))
            with self.assertRaises(StorageLimitError):
                _evaluation_preflight(observation, policy, config, small)

    def test_evaluation_asset_overlap_rejected_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('palimpsest.evaluate.bounded_process') as launch:
                with self.assertRaisesRegex(ValueError, 'assets.*outside'):
                    evaluate(root, root / 'runs/assets', self.args(root / 'runs/new'))
                launch.assert_not_called()

    def test_evaluation_aggregate_exhaustion_preserves_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            previous = root / 'runs/previous'
            previous.mkdir(parents=True)
            (previous / 'evidence').write_bytes(b'preserve')
            args = self.args(root / 'runs/new', storage_max_bytes=1024**2, min_free_bytes=0)
            with patch('palimpsest.evaluate.bounded_process') as launch:
                with self.assertRaises(StorageLimitError):
                    evaluate(root, root / 'assets', args)
                launch.assert_not_called()
            self.assertEqual((previous / 'evidence').read_bytes(), b'preserve')
            self.assertFalse(args.output.exists())

    def test_evaluation_count_limit_includes_non_uuid_directories(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'runs/old-batch').mkdir(parents=True)
            with patch('palimpsest.evaluate.bounded_process') as launch:
                with self.assertRaisesRegex(StorageLimitError, 'runs count'):
                    evaluate(root, root / 'assets', self.args(root / 'runs/new', max_runs=1, min_free_bytes=0))
                launch.assert_not_called()

    def test_evaluation_shares_parent_lease_and_configuration_with_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            root, observed = Path(directory), {}
            args = self.args(root / 'runs/new', log_max_bytes=4096, min_free_bytes=0)
            def launch(command, output, timeout, env, *, log_max_bytes, storage_budget):
                observed.update(json.loads(command[-1]))
                self.assertEqual(log_max_bytes, 4096)
                competing = StorageBudget(storage_budget.roots, storage_budget.limits)
                with self.assertRaisesRegex(StorageLimitError, 'already owned'):
                    with competing.lock():
                        pass
                (output / 'recording').mkdir(parents=True)
                (output / 'recording/manifest.json').write_text(json.dumps({'status': 'completed'}))
                return {'status': 'completed'}
            with patch('palimpsest.evaluate.bounded_process', side_effect=launch):
                report = evaluate(root, root / 'assets', args)
            self.assertEqual(report['status'], 'completed')
            self.assertEqual(observed['storage']['roots'], [str(root / 'runs')])
            self.assertEqual(observed['storage']['limits']['max_runs'], 1024)
            self.assertEqual(observed['storage']['headroom_bytes'], 2 * 4096 + 8 * 1024**2)

    def test_bounded_process_checks_shared_budget_before_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            budget = StorageBudget((root,), StorageLimits(max_bytes=1, min_free_bytes=0))
            with patch('palimpsest.evaluate.subprocess.Popen') as launch:
                with self.assertRaises(StorageLimitError):
                    bounded_process(['fixture'], root / 'run', 1, storage_budget=budget)
                launch.assert_not_called()

    def test_native_and_python_log_floods_preserve_bounded_prefix_and_fail(self):
        for source, filename in (("import os; os.write(1,b'x'*1000000)", 'stdout.log'),
                                 ("import sys; sys.stderr.write('y'*1000000)", 'stderr.log')):
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'run'
                report = bounded_process([sys.executable, '-c', source], output, 5, log_max_bytes=4096)
                self.assertEqual(report['status'], 'failed')
                self.assertEqual(report['failure']['type'], 'LogLimit')
                self.assertEqual((output / filename).stat().st_size, 4096)

    def test_termination_has_priority_over_time_limit(self):
        self.assertEqual(outcome(True, True, {'dist_to_goal': .2, 'stalled': False}, .8), 'goal')
        self.assertEqual(outcome(True, False, {'dist_to_goal': 2, 'stalled': True}, .8), 'stalled')
        self.assertEqual(outcome(False, True, {'dist_to_goal': 2, 'stalled': False}, .8), 'time_limit')
        self.assertEqual(outcome(False, False, {'dist_to_goal': 2, 'stalled': False}, .8), None)

    def test_worker_is_bounded_and_existing_run_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'run'
            report = bounded_process([sys.executable, '-c', 'import time; time.sleep(30)'],
                                     output, timeout=.1)
            self.assertEqual(report['status'], 'timeout')
            self.assertIsNotNone(report['returncode'])
            self.assertEqual(json.loads((output / 'supervisor.json').read_text())['status'], 'timeout')
            with self.assertRaises(FileExistsError):
                bounded_process([sys.executable, '-c', 'pass'], output, timeout=1)

    def test_nonzero_worker_is_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            report = bounded_process([sys.executable, '-c', 'raise RuntimeError("fixture")'],
                                     Path(directory) / 'run', timeout=5)
            self.assertEqual(report['status'], 'failed')
            self.assertNotEqual(report['returncode'], 0)

    def test_exit_during_timeout_cleanup_still_records_terminal_supervisor(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'run'
            with patch('palimpsest.evaluate.subprocess.Popen') as popen:
                process = popen.return_value
                process.wait.side_effect = [subprocess.TimeoutExpired('fixture', .1), -15]
                process.poll.return_value = None
                process.pid, process.returncode = 123, -15
                with patch('palimpsest.evaluate.os.killpg', side_effect=ProcessLookupError):
                    report = bounded_process(['fixture'], output, .1)
            self.assertEqual(report['status'], 'timeout')
            self.assertEqual(json.loads((output / 'supervisor.json').read_text())['status'], 'timeout')

    def test_zero_exit_without_recording_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'run'
            output.mkdir()
            args = self.args(output)
            with patch('palimpsest.evaluate.bounded_process', return_value={'status': 'completed'}):
                report = evaluate(Path(directory), Path(directory).parent / 'assets-fixture', args)
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(json.loads((output / 'supervisor.json').read_text())['status'], 'failed')
