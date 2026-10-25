"""Bounded verification startup failures without running a renderer or model."""

import importlib.util
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]


class EnduranceProcessTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('endurance_process', ROOT / 'scripts/verify_endurance.py')
        self.reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.reader)
        self.child = subprocess.Popen([sys.executable, '-B', '-c', 'import sys; sys.stdin.read()'],
                                      stdin=subprocess.PIPE, start_new_session=True)
        self.root = Path('/proc') / str(self.child.pid)
        fields = (self.root / 'stat').read_text().rsplit(') ', 1)[1].split()
        self.start = int(fields[19])
        self.addCleanup(self.reap)

    def reap(self):
        if self.child.poll() is None:
            self.child.kill()
        self.child.wait(timeout=5)
        self.child.stdin.close()

    def zombie(self):
        self.child.stdin.close()
        until = time.monotonic() + 5
        while time.monotonic() < until:
            if (self.root / 'stat').read_text().rsplit(') ', 1)[1].split()[0] == 'Z':
                return
            time.sleep(.01)
        self.fail('Bounded child did not exit')

    def assert_zombie(self, row):
        self.assertEqual(set(row), {'pid', 'ppid', 'group', 'start_ticks', 'state',
                                   'rss_bytes', 'threads', 'fds', 'command'})
        self.assertEqual((row['pid'], row['ppid'], row['group'], row['start_ticks'], row['state']),
                         (self.child.pid, os.getpid(), self.child.pid, self.start, 'Z'))
        self.assertEqual((row['rss_bytes'], row['fds'], row['command']), (0, 0, ''))
        self.assertIsInstance(row['threads'], int)

    def deny_fds(self, transition=None):
        original = Path.iterdir
        def inspect(path):
            if path == self.root / 'fd':
                if transition:
                    transition()
                raise PermissionError(13, 'Authored procfs permission boundary', str(path))
            return original(path)
        return patch.object(Path, 'iterdir', inspect)

    def test_observed_zombie_keeps_identity_without_fd_access(self):
        self.zombie()
        with self.deny_fds():
            self.assert_zombie(self.reader.process(self.child.pid))

    def test_permission_race_accepts_only_same_identity_now_zombie(self):
        with self.deny_fds(self.zombie):
            self.assert_zombie(self.reader.process(self.child.pid))

    def test_inaccessible_live_process_still_raises_with_identity_context(self):
        with self.deny_fds(), self.assertRaises(PermissionError) as caught:
            self.reader.process(self.child.pid)
        notes = ' '.join(getattr(caught.exception, '__notes__', []))
        self.assertIn(str(self.child.pid), notes)
        self.assertIn(str(self.start), notes)

    def test_permission_race_does_not_accept_reused_pid_as_old_zombie(self):
        original = Path.read_text
        def read(path, *args, **kwargs):
            value = original(path, *args, **kwargs)
            if path == self.root / 'stat':
                prefix, tail = value.rsplit(') ', 1)
                fields = tail.split()
                if fields[0] == 'Z':
                    fields[19] = str(self.start + 1)
                    return prefix + ') ' + ' '.join(fields)
            return value
        with self.deny_fds(self.zombie), patch.object(Path, 'read_text', read), \
                self.assertRaises(PermissionError):
            self.reader.process(self.child.pid)


class VerificationScriptTests(unittest.TestCase):
    def test_memory_gate_retains_startup_failure_without_runtime(self):
        with patch.object(sys, 'path', [str(ROOT / 'scripts'), *sys.path]):
            spec = importlib.util.spec_from_file_location('memory_gate', ROOT / 'scripts/verify_memory.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'evidence'
            args = SimpleNamespace(repo=ROOT, assets=Path(temporary), output=output, controller='manual')
            with patch.object(module, 'create_app', side_effect=OSError('startup fixture')):
                result = module.verify(args)
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['error'], {'type': 'OSError', 'message': 'startup fixture'})
            self.assertEqual(result, json.loads((output / 'report.json').read_text()))
            self.assertNotIn('supervisor_shutdown_completed', result)
            self.assertEqual(result['branches'], {})
            self.assertEqual(len(result['script_sha256']), 64)

    def test_endurance_requires_completed_cycle_per_controller(self):
        # Verifier-boundary fixture only; no server, renderer or policy is launched.
        spec = importlib.util.spec_from_file_location('endurance_coverage', ROOT / 'scripts/verify_endurance.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        controllers = ['manual', 'teacher', 'flynn']
        required = ('run', 'pause', 'step', 'reset', 'set_eyes', 'preview', 'intervene',
                    'snapshot', 'branch', 'replay_actions', 'replay_policy', 'playback')
        for complete in (controllers[:2], controllers):
            with self.subTest(completed=complete), tempfile.TemporaryDirectory() as temporary:
                gate = MagicMock()
                gate.controllers_seen = set(controllers)  # Flynn source-ready is observed in both cases.
                gate.operations = dict.fromkeys(required, 1)
                gate.stream_counts = {'sample': 1}
                gate.commands = [{'http_receipt_seconds': .01, 'observed_application_seconds': .02}]
                gate.resources, gate.failure = [], None
                gate.signal, gate.started = None, module.time.monotonic()
                gate.http.get.return_value.json.return_value = {'token': 'fixture'}
                gate.cleanup.return_value = {'server_exit_code': 0, 'owned_survivors_requiring_kill': []}
                gate.cycle.side_effect = [
                    *({'controller': controller, 'active_run': {'real_time_factor': .5}}
                      for controller in complete), module.DeadlineReached()]
                server = MagicMock()
                server.poll.return_value = None
                output = Path(temporary) / 'evidence'
                argv = ['verify_endurance.py', '--output', str(output), '--duration', '30',
                        '--cycle-seconds', '1', '--controllers', *controllers]
                with patch.object(sys, 'argv', argv), patch.object(module, 'Gate', return_value=gate), \
                        patch.object(module.subprocess, 'Popen', return_value=server), \
                        patch.object(module.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='fixture')), \
                        patch.object(module.threading, 'Thread'), patch.object(module, 'recorded_metrics', return_value={}):
                    with contextlib.redirect_stdout(io.StringIO()):
                        module.main()
                report = json.loads((output / 'report.json').read_text())
                self.assertEqual(report['controllers_seen'], sorted(controllers))
                self.assertEqual(report['completed_controllers'], sorted(complete))
                self.assertEqual(report['completed_cycles'], len(complete))
                self.assertEqual(report['gates']['mixed_operations_completed'], complete == controllers)

    def test_optional_cpu_flynn_report_scope_without_launching_runtime(self):
        spec = importlib.util.spec_from_file_location('endurance_selection', ROOT / 'scripts/verify_endurance.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'evidence'
            argv = ['verify_endurance.py', '--output', str(output), '--duration', '1', '--controllers', 'flynn']
            with patch.object(sys, 'argv', argv), patch.object(module.subprocess, 'Popen', side_effect=OSError('startup fixture')):
                with contextlib.redirect_stdout(io.StringIO()):
                    code = module.main()
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(code, 1)
            self.assertEqual(report['qualification'], 'short-smoke')
            self.assertEqual(report['configuration']['controllers'], ['flynn'])
            self.assertIn('CPU flynn', report['scope'])
            self.assertIn('CPU Flynn only; no CUDA or full-model real-time qualification', report['limitations'])
            self.assertNotIn('No full-FLYNN endurance claim', report['limitations'])
            self.assertFalse(any('rtf' in name or 'real_time' in name for name in report['gates']))
            self.assertEqual(report['cleanup']['owned_survivors_requiring_kill'], [])

    def test_completion_protocol_preserves_unqualified_diagnostics_on_failed_close(self):
        # Supervisor-boundary fixture verifies verifier control flow only.
        # Its synthetic timing/rows are not simulation or performance evidence.
        with patch.object(sys, 'path', [str(ROOT / 'scripts'), *sys.path]):
            spec = importlib.util.spec_from_file_location('performance_protocol', ROOT / 'scripts/verify_performance.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        class OwnerBoundary:
            def __init__(self, root, fail_close):
                self.root, self.kinds, self.receipts = root, [], []
                self.fail_close, self.persisted_before_close = fail_close, None
                self.state = {'phase': 'paused', 'episode': 0, 'episode_step': 0, 'total_tick': 0,
                              'revision': 0, 'last_outcome': None}
            def start(self, config):
                return 'owner'
            def describe(self, identifier):
                if self.state['phase'] == 'running':
                    self.state['total_tick'] += 1
                    self.state['episode_step'] = self.state['total_tick']
                    if self.state['total_tick'] == 603:
                        self.state.update(phase='truncated', last_outcome={'reason': 'fixture-time-limit'})
                simulated = self.state['total_tick'] * .02
                return {'status': 'ready', 'state': copy.deepcopy(self.state), 'receipts': self.receipts.copy(),
                        'sample': {'state': copy.deepcopy(self.state), 'wall_elapsed': simulated,
                                   'performance': {'advanced_simulation_seconds': simulated,
                                                   'active_wall_seconds': simulated, 'rtf': 1.}}}
            def call(self, identifier, operation, body):
                self.kinds.append(body['kind'])
                self.receipts.append({'id': body['id'], 'status': 'applied'})
                if body['kind'] == 'run':
                    self.state.update(phase='running', total_tick=599)
                elif body['kind'] == 'pause':
                    self.state['phase'] = 'paused'
            def close(self, identifier):
                self.persisted_before_close = json.loads((self.root / 'evidence/report.json').read_text())
                if self.fail_close:
                    return {'status': 'failed', 'failure': {'type': 'CloseTimeout', 'message': 'fixture close timeout'},
                            'sample': {'inputs': 'oversized-image-sentinel' + 'x' * 200000}}
                return {'status': 'closed'}
            def path(self, identifier):
                return self.root
            def shutdown(self):
                pass
        for finish, fail_close in ((False, False), (True, False), (True, True)):
            with self.subTest(finish_episode=finish, fail_close=fail_close), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                owner = OwnerBoundary(root, fail_close)
                args = SimpleNamespace(output=root / 'evidence', repo=ROOT, assets=root / 'assets', ticks=600,
                                       timeout=30., controllers=['teacher'], seed=0, finish_episode=finish)
                def rows(path):
                    return ({'episode': 0, 'tick': tick, 'simulation_time': (tick + 1) * .02,
                             'latency': .001, 'step_latency': .001} for tick in range(owner.state['total_tick']))
                with patch.object(module, 'LabSupervisor', return_value=owner), patch.object(module, 'iter_ticks', side_effect=rows):
                    with patch.dict(os.environ, {'OMP_NUM_THREADS': '3', 'OPENBLAS_NUM_THREADS': '4', 'MKL_NUM_THREADS': '5'}):
                        with patch.object(module.os, 'sched_getaffinity', return_value={1, 3}), patch.object(
                                module.os, 'getloadavg', side_effect=[(1., 2., 3.), (4., 5., 6.)]):
                            report = module.measure(args)
                self.assertEqual(report['status'], 'failed' if fail_close else 'passed', report.get('error'))
                self.assertEqual('pause' in owner.kinds, not finish)
                self.assertEqual(owner.state['phase'], 'truncated' if finish else 'paused')
                self.assertIn('natural-episode-completion' if finish else 'operator-pause', report['completion_protocol'])
                observation = owner.persisted_before_close['pre_close_observations']['teacher']
                self.assertEqual(observation['qualification'], 'unqualified')
                self.assertEqual(observation['final_ticks'], owner.state['total_tick'])
                self.assertEqual(observation['final_phase'], owner.state['phase'])
                self.assertEqual(observation['worker_active']['rtf'], 1.)
                self.assertEqual(report['host_at_start']['cpu_affinity'], [1, 3])
                self.assertEqual(report['host_at_start']['load_average_1_5_15_minutes'], [1., 2., 3.])
                self.assertEqual(report['host_at_end']['load_average_1_5_15_minutes'], [4., 5., 6.])
                self.assertEqual(report['host_at_end']['thread_environment'],
                                 {'OMP_NUM_THREADS': '3', 'OPENBLAS_NUM_THREADS': '4', 'MKL_NUM_THREADS': '5'})
                if fail_close:
                    self.assertEqual(report['controllers'], {})
                    self.assertIn('fixture close timeout', report['error']['message'])
                    self.assertNotIn('oversized-image-sentinel', json.dumps(report))
                    self.assertLess(len(report['error']['message']), 1000)

    def test_performance_constructor_failure_persists_failed_report(self):
        scripts = str(ROOT / 'scripts')
        with patch.object(sys, 'path', [scripts, *sys.path]):
            spec = importlib.util.spec_from_file_location('performance_probe', ROOT / 'scripts/verify_performance.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temporary:
            args = SimpleNamespace(output=Path(temporary) / 'evidence', repo=ROOT,
                                   assets=Path(temporary) / 'assets', ticks=600, timeout=30., controllers=['manual'])
            with patch.object(module, 'LabSupervisor', side_effect=OSError('startup fault')):
                report = module.measure(args)
            persisted = json.loads((args.output / 'report.json').read_text())
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(persisted['error']['type'], 'OSError')
            self.assertIn('startup fault', persisted['error']['message'])

    @unittest.skipUnless(Path('/proc/self/ns/net').exists(), 'Linux namespaces required')
    def test_offline_namespace_denial_is_blocked_and_keeps_host_boundary(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            unshare = directory / 'unshare'
            unshare.write_text('#!/bin/sh\nprintf "%s\\n" "unshare: namespace denied by fixture" >&2\nexit 1\n')
            unshare.chmod(0o700)
            output = directory / 'evidence'
            environment = {**os.environ, 'PATH': str(directory)}
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/verify_offline.py'), '--output', str(output)],
                                    env=environment, capture_output=True, text=True, timeout=15.)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(report['status'], 'blocked')
            self.assertIn('namespace denied by fixture', report['reason'])
            self.assertEqual(report['host_before'], report['host_after'])
            self.assertEqual(report['owned_survivors_requiring_kill'], [])

    @unittest.skipUnless(Path('/proc/self/ns/net').exists(), 'Linux namespaces required')
    def test_inside_on_host_refuses_before_loopback_command(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/verify_offline.py'), '--inside',
                '--output', temporary, '--host-net', os.readlink('/proc/self/ns/net'),
                '--host-user', os.readlink('/proc/self/ns/user')], capture_output=True, text=True, timeout=15.)
            self.assertEqual(result.returncode, 1, result.stderr)
            proof = json.loads((Path(temporary) / 'network.json').read_text())
            self.assertEqual(proof['status'], 'failed')
            self.assertIn('Refusing loopback', proof['error']['message'])
            self.assertNotIn('interfaces', proof)


if __name__ == '__main__':
    unittest.main()
