"""Bounded verification startup failures without running a renderer or model."""

import importlib.util
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
