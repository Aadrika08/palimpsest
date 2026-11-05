"""Harmless process fixtures only; these are software checks, not study runs."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('change_audit_process', Path(__file__).parents[1] / 'process.py')
process = importlib.util.module_from_spec(SPEC) if SPEC else None
if process and SPEC.loader and Path(SPEC.origin).exists():
    SPEC.loader.exec_module(process)
else:
    process = None


class ProcessChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(process, 'process accounting helper is not implemented')
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)

    def run_python(self, source, **kw):
        return process.run_accounted([sys.executable, '-c', source], cwd=self.root,
            env=dict(os.environ), stdout_path=self.root / 'stdout', stderr_path=self.root / 'stderr',
            wall_seconds=kw.pop('wall_seconds', 3), cpu_seconds=kw.pop('cpu_seconds', 2), **kw)

    def assert_drained(self, result):
        self.assertTrue(result['tree_drained'], result)
        self.assertTrue(result['accounting_complete'], result)
        self.assertGreaterEqual(result['worker_cpu_seconds'], 0)
        self.assertGreaterEqual(result['supervisor_cpu_seconds'], 0)
        self.assertGreaterEqual(result['parent_cpu_seconds'], 0)
        json.dumps(result, allow_nan=False)
        for row in result['resources']:
            self.assertFalse(Path('/proc', str(row['pid'])).exists())

    def test_success_and_exclusive_logs(self):
        result = self.run_python("print('hello')")
        self.assert_drained(result)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['returncode'], 0)
        self.assertEqual((self.root / 'stdout').read_text(), 'hello\n')
        with self.assertRaises(FileExistsError):
            self.run_python("print('overwrite')")
        self.assertEqual((self.root / 'stdout').read_text(), 'hello\n')

    def test_nonzero_exit(self):
        result = self.run_python("raise SystemExit(7)")
        self.assert_drained(result)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['returncode'], 7)

    def test_exec_failure_is_accounted(self):
        result = process.run_accounted(['/no/such/audit-test-executable'], cwd=self.root,
            env=dict(os.environ), stdout_path=self.root / 'stdout', stderr_path=self.root / 'stderr',
            wall_seconds=2, cpu_seconds=1)
        self.assert_drained(result)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['returncode'], 127)
        self.assertIn('exec/setup error', (self.root / 'stderr').read_text())

    def test_each_log_retains_only_bounded_prefix_and_stops(self):
        result = self.run_python("import os; os.write(1, b'a' * 200000); os.write(2, b'b' * 200000)",
                                 max_log_bytes=1024)
        self.assert_drained(result)
        self.assertEqual(result['status'], 'log_limit')
        self.assertEqual((self.root / 'stdout').read_bytes(), b'a' * 1024)
        self.assertLessEqual((self.root / 'stderr').stat().st_size, 1024)
        self.assertTrue(result['logs']['stdout']['clipped'])
        self.assertGreater(result['logs']['stdout']['observed_bytes'], 1024)
        self.assertEqual(result['logs']['stdout']['retained_bytes'], 1024)

    def test_parent_wait4_total_includes_worker_exactly_once(self):
        result = self.run_python("import time; start=time.process_time();\nwhile time.process_time()-start < .1: pass")
        self.assert_drained(result)
        self.assertAlmostEqual(result['worker_cpu_seconds'] + result['supervisor_cpu_seconds'],
                               result['subtree_cpu_seconds'], places=6)
        self.assertAlmostEqual(result['worker_cpu_seconds'],
                               sum(row['cpu_seconds'] for row in result['resources']), places=6)

    def test_existing_child_refuses_before_creating_logs(self):
        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(write_fd)
            os.read(read_fd, 1)
            os._exit(0)
        os.close(read_fd)
        try:
            with self.assertRaisesRegex(RuntimeError, 'preexisting children'):
                self.run_python('pass')
            self.assertFalse((self.root / 'stdout').exists())
        finally:
            os.close(write_fd)
            os.waitpid(pid, 0)

    def test_wall_timeout_preserves_partial_output(self):
        result = self.run_python("import time; print('partial', flush=True); time.sleep(10)", wall_seconds=.15)
        self.assert_drained(result)
        self.assertEqual(result['status'], 'wall_limit')
        self.assertEqual((self.root / 'stdout').read_text(), 'partial\n')

    def test_cpu_burn_is_accounted_and_capped(self):
        result = self.run_python("while True: pass", cpu_seconds=.15)
        self.assert_drained(result)
        self.assertEqual(result['status'], 'cpu_limit')
        self.assertGreater(result['worker_cpu_seconds'], .1)
        self.assertLess(result['worker_cpu_seconds'], 1.5)

    def test_waited_grandchild_cpu_is_included_once(self):
        source = """import os, time
p = os.fork()
if p == 0:
    start = time.process_time()
    while time.process_time() - start < .12: pass
    os._exit(0)
os.waitpid(p, 0)
"""
        result = self.run_python(source)
        self.assert_drained(result)
        self.assertGreater(result['worker_cpu_seconds'], .11)
        self.assertLess(result['worker_cpu_seconds'], .5)
        self.assertEqual(len(result['resources']), 1)

    def test_detached_nested_orphans_are_drained_and_charged(self):
        source = """import os, time
p = os.fork()
if p == 0:
    os.setsid()
    p = os.fork()
    if p == 0:
        print(os.getpid(), flush=True)
        while True: pass
    os._exit(0)
time.sleep(.15)
os._exit(0)
"""
        result = self.run_python(source)
        self.assert_drained(result)
        self.assertEqual(result['status'], 'completed')
        self.assertGreaterEqual(len(result['resources']), 2)
        self.assertGreater(result['worker_cpu_seconds'], .09)
        self.assertFalse(Path('/proc', (self.root / 'stdout').read_text().strip()).exists())

    def test_monitor_exception_stops_and_accounts(self):
        def broken(snapshot):
            raise ValueError('storage probe broke')
        result = self.run_python('import time; time.sleep(10)', monitor=broken)
        self.assert_drained(result)
        self.assertEqual(result['status'], 'monitor_error')
        self.assertIn('storage probe broke', ' '.join(result['errors']))

    def test_monitor_stop(self):
        result = self.run_python('import time; time.sleep(10)', monitor=lambda snapshot: 'storage reserve')
        self.assert_drained(result)
        self.assertEqual(result['status'], 'monitor_stop')
        self.assertEqual(result['stop_reason'], 'storage reserve')

    def test_pidfd_failure_prevents_admission_and_reports_unknown(self):
        with patch.object(process, '_open_pidfd', side_effect=OSError('pidfd unavailable')):
            result = self.run_python("print('should not launch')")
        self.assertFalse(result['accounting_complete'])
        self.assertIsNone(result['worker_cpu_seconds'])
        self.assertEqual((self.root / 'stdout').read_bytes(), b'')

    def test_output_write_failure_still_drains_owned_tree(self):
        with patch.object(process, '_write_output', side_effect=OSError('simulated ENOSPC')):
            result = self.run_python("import time; print('partial', flush=True); time.sleep(10)")
        self.assertTrue(result['tree_drained'], result)
        self.assertFalse(result['accounting_complete'])
        self.assertIsNone(result['worker_cpu_seconds'])
        self.assertEqual(result['status'], 'supervisor_error')
        self.assertIn('simulated ENOSPC', ' '.join(result['errors']))
        with self.assertRaises(ChildProcessError):
            os.waitpid(-1, os.WNOHANG)

    def test_proc_sampling_failure_still_drains_owned_tree(self):
        with patch.object(process, '_sample_cpu', side_effect=OSError('simulated proc scan failure')):
            result = self.run_python('import time; time.sleep(10)')
        self.assertTrue(result['tree_drained'], result)
        self.assertFalse(result['accounting_complete'])
        self.assertEqual(result['status'], 'supervisor_error')

    def test_worker_pin_failure_never_admits_exec_and_reaps_gate_child(self):
        caller = os.getpid()
        original = process._open_pidfd
        def unavailable_in_supervisor(pid):
            if os.getpid() != caller:
                raise OSError('worker pidfd unavailable')
            return original(pid)
        with patch.object(process, '_open_pidfd', side_effect=unavailable_in_supervisor):
            result = self.run_python("print('should not launch')")
        self.assertFalse(result['accounting_complete'])
        self.assertTrue(result['tree_drained'], result)
        self.assertIsNone(result['worker_cpu_seconds'])
        self.assertEqual((self.root / 'stdout').read_bytes(), b'')
        with self.assertRaises(ChildProcessError):
            os.waitpid(-1, os.WNOHANG)

    def test_zero_log_quota_preserves_empty_prefix(self):
        result = self.run_python("print('discard me')", max_log_bytes=0)
        self.assert_drained(result)
        self.assertEqual(result['status'], 'log_limit')
        self.assertEqual((self.root / 'stdout').stat().st_size, 0)

    def test_reused_identity_never_gets_signalled(self):
        with patch.object(process, '_stat', side_effect=[{'ppid': os.getpid(), 'start_ticks': 1},
                                                       {'ppid': os.getpid(), 'start_ticks': 2}]), \
             patch.object(process, '_open_pidfd', return_value=123), \
             patch.object(process.os, 'close') as close, \
             patch.object(process, '_send_pidfd') as send:
            with self.assertRaises(RuntimeError):
                process._pin_child(12345)
            send.assert_not_called()
            close.assert_called_once_with(123)

    def check_parent_read_failure(self, error_type):
        caller = os.getpid()
        original_read = os.read
        def broken_parent_read(fd, size):
            if os.getpid() == caller:
                deadline = time.monotonic() + 1
                while not (self.root / 'descendant').exists() and time.monotonic() < deadline:
                    time.sleep(.005)
                raise error_type('simulated coordinator read failure')
            return original_read(fd, size)
        source = """import os, time
from pathlib import Path
Path('started').write_text(str(os.getpid()))
pid = os.fork()
if pid == 0:
    os.setsid()
    Path('descendant').write_text(str(os.getpid()))
time.sleep(10)
"""
        before = set(os.listdir('/proc/self/fd'))
        with patch.object(process.os, 'read', side_effect=broken_parent_read):
            result = self.run_python(source, wall_seconds=2)
        self.assertFalse(result['accounting_complete'], result)
        self.assertIsNone(result['worker_cpu_seconds'])
        self.assertIsNone(result['subtree_cpu_seconds'])
        self.assertIn('coordinator read failure', ' '.join(result['errors']))
        self.assertTrue((self.root / 'descendant').exists())
        for filename in ('started', 'descendant'):
            pid = (self.root / filename).read_text()
            self.assertFalse(Path('/proc', pid).exists(), (filename, pid, result))
        self.assertEqual(before, set(os.listdir('/proc/self/fd')))
        with self.assertRaises(ChildProcessError):
            os.waitpid(-1, os.WNOHANG)

    def test_parent_read_oserror_stops_and_reaps_started_tree(self):
        self.check_parent_read_failure(OSError)

    def test_parent_read_memoryerror_stops_and_reaps_started_tree(self):
        self.check_parent_read_failure(MemoryError)

    def test_parent_setup_error_after_fork_stops_and_reaps_before_raise(self):
        caller = os.getpid()
        original = os.set_blocking
        def broken_parent_setup(fd, blocking):
            if os.getpid() == caller:
                deadline = time.monotonic() + 1
                while not (self.root / 'started').exists() and time.monotonic() < deadline:
                    time.sleep(.005)
                raise OSError('simulated parent transport setup failure')
            return original(fd, blocking)
        source = "import os,time; from pathlib import Path; Path('started').write_text(str(os.getpid())); time.sleep(10)"
        before = set(os.listdir('/proc/self/fd'))
        with patch.object(process.os, 'set_blocking', side_effect=broken_parent_setup):
            with self.assertRaisesRegex(OSError, 'parent transport setup failure'):
                self.run_python(source)
        self.assertTrue((self.root / 'started').exists())
        self.assertFalse(Path('/proc', (self.root / 'started').read_text()).exists())
        self.assertEqual(before, set(os.listdir('/proc/self/fd')))
        with self.assertRaises(ChildProcessError):
            os.waitpid(-1, os.WNOHANG)

    def test_parent_wall_guard_interrupts_blocked_monitor_and_drains(self):
        def blocked(snapshot):
            time.sleep(5)
        started = time.monotonic()
        result = self.run_python('import time; time.sleep(10)', wall_seconds=.1, monitor=blocked)
        self.assert_drained(result)
        self.assertEqual(result['status'], 'wall_limit')
        self.assertLess(time.monotonic() - started, 2)

    def test_no_descriptor_or_child_leaks(self):
        before = set(os.listdir('/proc/self/fd'))
        result = self.run_python('pass')
        self.assert_drained(result)
        self.assertEqual(before, set(os.listdir('/proc/self/fd')))
        with self.assertRaises(ChildProcessError):
            os.waitpid(-1, os.WNOHANG)


if __name__ == '__main__':
    unittest.main()
