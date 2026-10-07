"""Tiny software fixtures; no retained inputs, leases, exporters or native owners."""
from contextlib import ExitStack, nullcontext
import html
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch


class ReachedAudio(Exception):
    pass


class MaterialTests(unittest.TestCase):
    def setUp(self):
        source = Path(__file__).resolve().parents[1] / 'scripts/prepare_artwork_material_v2.py'
        spec = importlib.util.spec_from_file_location('material_v2_fixture', source)
        self.m = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(source.parent), *sys.path]):
            spec.loader.exec_module(self.m)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.phase = self.root / 'fixture-phase'
        self.budget = Mock()
        self.budget.lock.side_effect = nullcontext
        self.budget.check.return_value = {}
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(self.m, 'PHASE', self.phase))
        self.stack.enter_context(patch.object(self.m, 'BUDGET', self.budget))

    def comparison_fixture(self):
        art = self.phase / 'artifacts'
        art.mkdir(parents=True)
        self.comparison = {'mode': 'offline recorded comparison', 'projection': {'arena': 10}, 'comparison': {}}
        worlds = []
        for side, run, count in [('left', self.m.IDS[0], 1268), ('right', self.m.IDS[1], 1293)]:
            trace = {'episode': 0, 'points': [[1., 2.]] * count}
            world = {'episode': 0, 'world': {'arena': 10, 'obstacles': [[3., 4., .5]], 'goal': [5., 6., .75]}}
            self.comparison['comparison'][side] = {'run_id': run, 'traces': [trace], 'worlds': [world]}
            worlds.append(world)
        route = {'run_id': self.m.IDS[0], 'traces': self.comparison['comparison']['left']['traces']}
        accessible = '<title id="t">Fixture</title><desc id="d">Fixture description</desc>'
        svg = '<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="t d">' + accessible
        (art / 'borrowed-body.svg').write_text(svg + '<metadata>' + json.dumps(route) + '</metadata><polyline points="' + ' '.join(['1.0,2.0'] * 1268) + '"/></svg>')
        for name in ('afterimage.svg', 'atlas.svg', 'space-between-two-flies.svg'):
            (art / name).write_text(svg + '</svg>')
        projection = '<g transform="translate(400 400) scale(36.0 -36.0)"><rect x="-10" y="-10" width="20" height="20"/>'
        overlay = svg.replace('t d', 'overlay-title overlay-description') + projection
        for side in ('left', 'right'):
            item = self.comparison['comparison'][side]
            overlay += '<polyline data-run-id="' + item['run_id'] + '" data-episode="0" points="' + ' '.join(['1.0,2.0'] * len(item['traces'][0]['points'])) + '"/>'
        self.views = [overlay + '</g></svg>']
        for side, label in [('left', 'A'), ('right', 'B')]:
            trace = self.comparison['comparison'][side]['traces'][0]
            self.views.append(svg.replace('t d', f'world-{label} world-{label}-description') + projection + '<g data-episode="0"><circle cx="3" cy="4" r="0.5"/><circle cx="5" cy="6" r="0.75"/><polyline points="' + ' '.join(['1.0,2.0'] * len(trace['points'])) + '"/></g></g></svg>')
        self.write_comparison()
        self.stack.enter_context(patch.object(self.m.wave, 'open', side_effect=ReachedAudio))

    def write_comparison(self):
        (self.phase / 'artifacts/one-map-many-lives.html').write_text(''.join(self.views) + '<pre id="comparison-metadata">' + html.escape(json.dumps(self.comparison)) + '</pre>')

    def test_valid_display_reaches_audio_checks(self):
        self.comparison_fixture()
        with self.assertRaises(ReachedAudio):
            self.m.check_and_package({})

    def test_display_route_corruption_rejected_with_unchanged_metadata(self):
        self.comparison_fixture()
        for index in range(3):
            with self.subTest(view=index):
                original = self.views[index]
                self.views[index] = original.replace('points="1.0,2.0', 'points="9.0,2.0', 1)
                self.write_comparison()
                with self.assertRaisesRegex(ValueError, 'route'):
                    self.m.check_and_package({})
                self.views[index] = original

    def test_display_world_corruption_rejected_with_unchanged_metadata(self):
        self.comparison_fixture()
        for index in (1, 2):
            with self.subTest(view=index):
                original = self.views[index]
                self.views[index] = original.replace('cx="3"', 'cx="9"', 1)
                self.write_comparison()
                with self.assertRaisesRegex(ValueError, 'world'):
                    self.m.check_and_package({})
                self.views[index] = original

    def test_export_child_interrupt_retains_failed_receipt(self):
        self.phase.mkdir()
        saved = []
        def capture(path, report, budget):
            saved.append(report)
        def interrupt(argv):
            saved[0]['status'] = 'passed'
            raise KeyboardInterrupt('fixture interruption after child provisional pass')
        reg = {'numpy_version': self.m.importlib.metadata.version('numpy'),
               'exports': [{'argv': [], 'output': 'fixture.svg'}]}
        for context in [patch.object(self.m, 'registration', return_value=reg),
                        patch.object(self.m, 'pins_match', return_value=True),
                        patch.object(self.m.h, 'process_identity', return_value={}),
                        patch.object(self.m.h, 'write_json', side_effect=capture),
                        patch.object(self.m.h.cli, 'main', side_effect=interrupt),
                        patch.object(sys, 'meta_path', list(sys.meta_path))]:
            self.stack.enter_context(context)
        self.assertEqual(self.m.export_child(0), 1)
        self.assertEqual(saved[-1]['status'], 'failed')
        self.assertIn('KeyboardInterrupt', saved[-1]['error'])

    def test_interrupt_after_provisional_pass_retains_failed_receipt(self):
        plan = self.root / 'docs/plans/artwork-material-v2.md'
        plan.parent.mkdir(parents=True)
        plan.write_text('Fixture plan')
        regpath = plan.with_name('artwork-material-v2-registration.json')
        regpath.write_text('{}')
        archive = self.root / 'tiny-input-placeholder'
        archive.write_bytes(b'x')
        pin = {'size_bytes': 1, 'sha256': 'fixture'}
        reg = {'python': {'resolved': str(Path(sys.executable).resolve())}, 'exports': [{}, {}, {}], 'reused': [],
               'input_archive': {'path': str(archive), 'pin': pin}, 'input_manifest': {'pin': pin}}
        def completed_child(argv, directory, *args, **kwargs):
            index = int(argv[-1])
            (self.phase / f'export-{index}.json').write_text(json.dumps({'status': 'passed', 'process': {}}))
            return {'status': 'completed', 'returncode': 0}
        def interrupt(result):
            # Inject the vulnerable provisional-pass state, then interrupt the guarded body.
            result['status'] = 'passed'
            raise KeyboardInterrupt('fixture interruption after provisional pass')
        patches = [patch.object(self.m.h, 'ROOT', self.root), patch.object(self.m, 'REGISTRATION', regpath),
                   patch.object(self.m, 'registration', return_value=reg), patch.object(self.m, 'digest', return_value=pin),
                   patch.object(self.m, 'pins_match', return_value=True), patch.object(self.m, 'relocate', return_value=[]),
                   patch.object(self.m, 'relocated_match', return_value=True), patch.object(self.m, 'check_clock'),
                   patch.object(self.m.h, 'bounded_process', side_effect=completed_child),
                   patch.object(self.m.h, 'cleanup_check', return_value={'passed': True}),
                   patch.object(self.m, 'check_and_package', side_effect=interrupt),
                   patch.object(self.m.subprocess, 'check_output', return_value=''),
                   patch.object(self.m.shutil, 'disk_usage', return_value=Mock(free=5 * 1024**3)),
                   patch.dict(self.m.os.environ, {key: '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')})]
        for context in patches:
            self.stack.enter_context(context)
        self.assertEqual(self.m.main(), 1)
        receipt = json.loads((self.phase / 'result.json').read_text())
        self.assertEqual(receipt['status'], 'failed')
        self.assertIn('KeyboardInterrupt', receipt['error'])
        self.assertEqual(receipt['qualification_claims'], [])
        self.assertEqual(len(receipt['exports']), 3)


if __name__ == '__main__':
    unittest.main()
