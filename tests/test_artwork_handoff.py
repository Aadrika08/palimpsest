"""Handoff fixture verification only; no external records, lease or inference."""
from contextlib import ExitStack
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


class HandoffTests(unittest.TestCase):
    def setUp(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/verify_artwork_handoff.py'
        self.assertTrue(path.is_file(), 'fixed six-mode handoff driver is missing')
        spec = importlib.util.spec_from_file_location('artwork_handoff', path)
        self.h = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(path.parent), *sys.path]):
            spec.loader.exec_module(self.h)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        # Reuse a real completed record builder, not any retained experiment.
        from test_artifacts import ArtifactTests
        builder = ArtifactTests()
        builder.setUp()
        self.addCleanup(builder.doCleanups)
        run = builder.run_fixture(count=4)
        self.inputs = self.root / 'relocated'
        self.run = self.inputs / 'runs' / run.name
        shutil.copytree(run, self.run)
        for index in range(16):
            (self.inputs / f'support-{index}.txt').write_text('Authored handoff fixture only.\n')
        self.manifest = copy.deepcopy(self.h.load_manifest())
        self.manifest['run_ids']['left'] = run.name
        self.manifest['files'] = [dict(path=p.relative_to(self.inputs).as_posix(),
            **self.h.fingerprint(p, 1024**2), original_source='fixture, deliberately unavailable origin')
            for p in sorted(self.inputs.rglob('*')) if p.is_file()]
        self.manifest['source_bytes'] = sum(p['size_bytes'] for p in self.manifest['files'])
        self.budget = Mock()
        self.budget.check.return_value = {'used_bytes': 0}
        self.calls = []

    def fake_cli(self, argv):
        self.calls.append(argv)
        Path(argv[argv.index('--output') + 1]).write_text('Fixture export; no renderer or lease.\n')
        return 0

    def patches(self):
        stack = ExitStack()
        self.addCleanup(stack.close)
        # A full suite may already contain Torch. Isolate only this fake child.
        stack.enter_context(patch.dict(sys.modules))
        sys.modules.pop('torch', None)
        sys.modules.pop('mujoco', None)
        stack.enter_context(patch.object(self.h, 'sources', return_value={'fixture.py': {'sha256': 'a'*64}}))
        stack.enter_context(patch.object(self.h, 'process_identity', return_value={'pid': 123, 'start_ticks': 4, 'process_group': 123}))
        stack.enter_context(patch.object(self.h.cli, 'main', side_effect=self.fake_cli))
        stack.enter_context(patch.object(self.h, 'check_artifact', side_effect=lambda p, m: {'status': 'passed', **self.h.fingerprint(p, 1024)}))
        stack.enter_context(patch.object(self.h.StorageBudget, 'lock', side_effect=AssertionError('fixture must not acquire lease')))
        return stack

    def test_manifest_and_relocated_completed_record(self):
        real = self.h.load_manifest()
        self.assertEqual((len(real['files']), sum(row['size_bytes'] for row in real['files'])), (19, 4852480))
        self.assertTrue(all(value is None for value in real['declarations'].values()))
        admitted = self.h.admit(self.inputs, self.manifest)
        self.assertEqual(len(admitted), 19)
        from palimpsest import artifacts
        self.assertEqual(artifacts._load(self.run)['manifest']['recorded_ticks'], 4)
        altered = self.root / 'manifest.json'
        altered.write_text(json.dumps(real) + ' ')
        with patch.object(self.h, 'MANIFEST', altered), self.assertRaisesRegex(ValueError, 'manifest changed'):
            self.h.load_manifest()

    def test_six_fixed_commands_and_restored_runtime_marker(self):
        marker = object()
        with patch.dict(sys.modules, {'torch': marker}):
            with self.patches():
                output = self.root / 'out'; output.mkdir()
                report = self.h.worker(self.inputs, output, self.manifest, self.budget)
                self.assertEqual(report['status'], 'passed')
                self.assertEqual([r['status'] for r in report['rows']], ['passed']*6)
                self.assertEqual([a[2] for a in self.calls], ['afterimage','export','compare','sonify','atlas','specimens'])
                self.assertTrue(all(str(self.inputs) in ' '.join(a) for a in self.calls))
                self.assertEqual(report['inputs_before'], report['inputs_after'])
                self.assertEqual(report['qualification_claims'], [])
            self.assertIs(sys.modules['torch'], marker)

    def test_corruption_and_extra_symlink_refuse_before_any_command(self):
        with self.patches():
            path = self.run / 'recording/chunks/000000.npz'
            saved = path.read_bytes(); path.write_bytes(saved + b'corrupt')
            output = self.root / 'bad'; output.mkdir()
            report = self.h.worker(self.inputs, output, self.manifest, self.budget)
            self.assertEqual(report['status'], 'failed')
            self.assertEqual([r['status'] for r in report['rows']], ['not_started']*6)
            self.assertEqual(self.calls, [])
            path.write_bytes(saved)
            (self.inputs / 'unlisted').symlink_to(path)
            with self.assertRaisesRegex(ValueError, 'symlink'):
                self.h.admit(self.inputs, self.manifest)

    def test_failure_stops_next_commands_and_still_rehashes_inputs(self):
        with self.patches():
            def fail_second(argv):
                if len(self.calls) == 1:
                    self.calls.append(argv)
                    (self.inputs / 'support-0.txt').write_text('changed')
                    return 1
                return self.fake_cli(argv)
            with patch.object(self.h.cli, 'main', side_effect=fail_second):
                output = self.root / 'failure'; output.mkdir()
                report = self.h.worker(self.inputs, output, self.manifest, self.budget)
            self.assertEqual([r['status'] for r in report['rows']], ['passed','failed',*['not_started']*4])
            self.assertEqual(len(self.calls), 2)
            self.assertTrue((output / 'afterimage.svg').is_file())
            self.assertTrue(report.get('finalization_errors'))
            self.assertIn('CLI failed', report['error'])

    def test_supervised_main_uses_real_publication_and_refuses_reuse(self):
        with self.patches():
            output = self.root / 'parent'
            def supervise(command, directory, timeout, **kwargs):
                self.assertEqual(timeout, 120)
                self.assertEqual(kwargs['log_max_bytes'], 262144)
                directory.mkdir()
                child = self.h.worker(self.inputs, output, self.manifest, self.budget)
                return {'status': 'completed', 'returncode': 0 if child['status']=='passed' else 1, 'elapsed_seconds': .1}
            with patch.object(sys, 'argv', ['handoff','--inputs',str(self.inputs),'--output',str(output)]), \
                    patch.object(self.h, 'load_manifest', return_value=self.manifest), \
                    patch.object(self.h, 'StorageBudget', return_value=self.budget), \
                    patch.object(self.h, 'bounded_process', side_effect=supervise), \
                    patch.object(self.h, 'cleanup_check', return_value={'passed': True}):
                self.assertEqual(self.h.main(), 0)
                report = json.loads((output / 'report.json').read_text())
                self.assertEqual(report['status'], 'passed')
                self.assertEqual(report['supervisor']['returncode'], 0)
                with self.assertRaises(FileExistsError):
                    self.h.main()
                # Real final publication crosses the normal limit: fail and
                # preserve the late receipt, never an on-time success claim.
                output = self.root / 'late'
                clock, publish = [0.], self.h.write_json
                def late_publish(path, value, budget):
                    publish(path, value, budget)
                    if path.name == 'report.json':
                        clock[0] = 151.
                with patch.object(sys, 'argv', ['handoff','--inputs',str(self.inputs),'--output',str(output)]), \
                        patch.object(self.h.time, 'monotonic', side_effect=lambda: clock[0]), \
                        patch.object(self.h, 'write_json', side_effect=late_publish):
                    self.assertEqual(self.h.main(), 1)
                late = json.loads((output / 'report.json').read_text())
                self.assertEqual(late['status'], 'failed')
                self.assertIn('during publication', late['error'])
                # A completed zero exit is insufficient when the bounded
                # child receipt itself exceeds its 120-second normal limit.
                output = self.root / 'late-child'
                def late_zero(command, directory, timeout, **kwargs):
                    return {**supervise(command, directory, timeout, **kwargs), 'elapsed_seconds': 120.001}
                with patch.object(sys, 'argv', ['handoff','--inputs',str(self.inputs),'--output',str(output)]), \
                        patch.object(self.h, 'bounded_process', side_effect=late_zero):
                    self.assertEqual(self.h.main(), 1)
                child_late = json.loads((output / 'report.json').read_text())
                self.assertEqual(child_late['status'], 'failed')
                self.assertIn('child/export/cleanup', child_late['error'])

    def test_offline_import_guard_rejects_without_importing(self):
        with self.assertRaisesRegex(RuntimeError, 'forbids'):
            self.h.NoInference().find_spec('torch.nn')
        self.assertIsNone(self.h.NoInference().find_spec('numpy'))

    def test_real_route_readback_rejects_wrong_source_identity(self):
        from palimpsest import artifacts
        import xml.etree.ElementTree as ET
        output = self.root / 'borrowed-body.svg'
        artifacts.export_run(self.run, output, 'svg')  # Synthetic fixture, no CLI lease.
        self.assertEqual(self.h.check_artifact(output, self.manifest)['status'], 'passed')
        svg = ET.fromstring(output.read_bytes())
        node = svg.find('{http://www.w3.org/2000/svg}metadata')
        metadata = json.loads(node.text); metadata['run_id'] = '0'*32
        node.text = json.dumps(metadata); output.write_bytes(ET.tostring(svg))
        with self.assertRaisesRegex(ValueError, 'source/ticks'):
            self.h.check_artifact(output, self.manifest)


if __name__ == '__main__':
    unittest.main()
