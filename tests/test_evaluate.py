import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import subprocess

from palimpsest.evaluate import bounded_process, evaluate, outcome


class EvaluationTests(unittest.TestCase):
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
            args = SimpleNamespace(output=output, controller='teacher', device='cpu', episodes=1,
                                   max_steps=1, seed=0, parity=False, max_bytes=1024**2, threads=1, timeout=2)
            with patch('palimpsest.evaluate.bounded_process', return_value={'status': 'completed'}):
                report = evaluate(Path(directory), Path(directory), args)
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(json.loads((output / 'supervisor.json').read_text())['status'], 'failed')
