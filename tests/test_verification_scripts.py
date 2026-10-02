"""Bounded verification startup failures without running a renderer or model."""

import importlib.util
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class VerificationScriptTests(unittest.TestCase):
    def test_explicit_natural_completion_does_not_request_operator_pause(self):
        # Supervisor-boundary fixture verifies verifier control flow only.
        # Its synthetic timing/rows are not simulation or performance evidence.
        with patch.object(sys, 'path', [str(ROOT / 'scripts'), *sys.path]):
            spec = importlib.util.spec_from_file_location('performance_protocol', ROOT / 'scripts/verify_performance.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        class OwnerBoundary:
            def __init__(self, root):
                self.root, self.kinds, self.receipts = root, [], []
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
                return {'status': 'closed'}
            def path(self, identifier):
                return self.root
            def shutdown(self):
                pass
        for finish in (False, True):
            with self.subTest(finish_episode=finish), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                owner = OwnerBoundary(root)
                args = SimpleNamespace(output=root / 'evidence', repo=ROOT, assets=root / 'assets', ticks=600,
                                       timeout=30., controllers=['teacher'], seed=0, finish_episode=finish)
                def rows(path):
                    return ({'episode': 0, 'tick': tick, 'simulation_time': (tick + 1) * .02,
                             'latency': .001, 'step_latency': .001} for tick in range(owner.state['total_tick']))
                with patch.object(module, 'LabSupervisor', return_value=owner), patch.object(module, 'iter_ticks', side_effect=rows):
                    report = module.measure(args)
                self.assertEqual(report['status'], 'passed', report.get('error'))
                self.assertEqual('pause' in owner.kinds, not finish)
                self.assertEqual(owner.state['phase'], 'truncated' if finish else 'paused')
                self.assertIn('natural-episode-completion' if finish else 'operator-pause', report['completion_protocol'])

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
