"""Offline comparison fixtures; browser layout and actual exhibition remain untested."""
import contextlib
import hashlib
from html.parser import HTMLParser
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import uuid
import xml.etree.ElementTree as ET

import numpy as np

from palimpsest import artifacts
import test_artifacts


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags, self.metadata, self.capturing = [], '', False
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == 'pre' and dict(attrs).get('id') == 'comparison-metadata':
            self.capturing = True

    def handle_endtag(self, tag):
        if tag == 'pre':
            self.capturing = False

    def handle_data(self, data):
        if self.capturing:
            self.metadata += data


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        artifacts._CACHE.clear()

    def fixture(self, **kwargs):
        return test_artifacts.ArtifactTests.run_fixture(self, **kwargs)

    def export(self, left, right, name='comparison.html', **kwargs):
        from palimpsest.comparison import export_comparison
        return export_comparison(left, right, self.root / name, **kwargs)

    def change_chunk(self, run, transform):
        chunk = run / 'recording/chunks/000000.npz'
        with np.load(chunk, allow_pickle=False) as archive:
            arrays = {name: archive[name].copy() for name in archive.files}
        transform(arrays)
        np.savez(chunk, **arrays)
        path = run / 'recording/events.jsonl'
        events = [json.loads(line) for line in path.read_text().splitlines()]
        next(event for event in events if event['kind'] == 'chunk')['sha256'] = hashlib.sha256(chunk.read_bytes()).hexdigest()
        path.write_text(''.join(json.dumps(event) + '\n' for event in events))

    def test_coincident_routes_survive_with_common_projection_and_both_source_identities(self):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.comparison'), 'offline comparison renderer is missing')
        left, right = self.fixture(), self.fixture()
        output = self.export(left, right)
        html = output.read_text()
        document = Document(html)
        metadata = json.loads(document.metadata)
        comparison = metadata['comparison']
        self.assertTrue(metadata['route_arrays_equal'])
        self.assertEqual((comparison['left_run_id'], comparison['right_run_id']), (left.name, right.name))
        self.assertEqual(comparison['left']['traces'], artifacts.compare_runs(left, right)['left']['traces'])
        svg = ET.fromstring(re.search(r'<svg\b.*?</svg>', html, re.S)[0])
        ns = {'s': 'http://www.w3.org/2000/svg'}
        traces = svg.findall('.//s:polyline', ns)
        self.assertEqual(len(traces), 2)
        self.assertEqual(traces[0].attrib['points'], traces[1].attrib['points'])
        self.assertNotIn('stroke-dasharray', traces[0].attrib)
        self.assertIn('stroke-dasharray', traces[1].attrib)
        self.assertEqual(svg.find('s:g', ns).attrib['transform'], 'translate(400 400) scale(51.42857142857143 -51.42857142857143)')
        self.assertIn('offline', html.lower())
        self.assertIn('do not establish causality', html)
        self.assertLess(html.index('Recorded differences'), html.index('Route overlay'))
        self.assertEqual(len(re.findall(r'<svg\b', html)), 3)
        self.assertIn(('html', {'lang': 'en'}), document.tags)
        self.assertFalse(any(tag in {'script', 'iframe', 'audio', 'video', 'img'} for tag, _ in document.tags))

    def test_stationary_routes_have_visible_markers_at_the_recorded_coordinate(self):
        left, right = self.fixture(), self.fixture()
        for run in (left, right):
            self.change_chunk(run, lambda arrays: (arrays['pose'].fill(0), arrays['next_pose'].fill(0)))
        html = self.export(left, right).read_text()
        svg = ET.fromstring(re.search(r'<svg\b.*?</svg>', html, re.S)[0])
        ns = {'s': 'http://www.w3.org/2000/svg'}
        markers = svg.findall('.//*[@data-start-marker]')
        self.assertEqual(len(markers), 2)
        self.assertEqual(markers[0].attrib['cx'], '0.0')
        self.assertEqual(markers[0].attrib['cy'], '0.0')
        self.assertEqual([line.attrib['points'] for line in svg.findall('.//s:polyline', ns)], ['0.0,0.0 0.0,0.0 0.0,0.0'] * 2)

    def test_actual_masks_u_swaps_and_parent_provenance_are_visible(self):
        from palimpsest.memory import artifact
        parent = uuid.uuid4().hex
        left, right = self.fixture(seed=1, parent=parent), self.fixture(seed=2, parent=parent)
        self.change_chunk(right, lambda arrays: arrays['eyes'].fill(True))
        path = right / 'recording/events.jsonl'
        events = [json.loads(line) for line in path.read_text().splitlines()]
        events.append({'sequence': len(events), 'kind': 'memory_u_replaced',
            'old_u': artifact(method='empty-v1'), 'new_u': artifact('local_cue'),
            'invariant_hashes': {'M': 'same', 'E': 'same', 'physics': 'same'}})
        path.write_text(''.join(json.dumps(event) + '\n' for event in events))
        manifest_path = right / 'recording/manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest.update(recorded_events=len(events), profile='manual', initial_memory={'u': 'fixture-u'})
        manifest_path.write_text(json.dumps(manifest))
        html = self.export(left, right).read_text()
        metadata = json.loads(Document(html).metadata)
        comparison = metadata['comparison']
        self.assertEqual(comparison['lineage']['shared_parent'], parent)
        self.assertEqual(comparison['left']['recorded_eye_masks'][0]['eyes'], {'left': True, 'right': False})
        self.assertEqual(comparison['right']['recorded_eye_masks'][0]['eyes'], {'left': True, 'right': True})
        self.assertEqual(len(comparison['right']['provenance']['memory_swaps']), 1)
        self.assertIn('recorded_eye_masks', [item['field'] for item in comparison['differences']])
        for label in ('Controller', 'Profile', 'Recorded eye masks', 'U-swap records', 'Parent run'):
            self.assertIn(label, html)
        self.assertIn('not a controlled U-only experiment', html)

    def test_incomplete_corrupt_empty_and_incompatible_projection_sources_fail_before_output(self):
        left = self.fixture()
        bad = [self.fixture(completed=False), self.fixture(count=0), self.fixture(), self.fixture()]
        chunk = bad[2] / 'recording/chunks/000000.npz'
        chunk.write_bytes(chunk.read_bytes() + b'corrupt')
        path = bad[3] / 'recording/events.jsonl'
        events = [json.loads(line) for line in path.read_text().splitlines()]
        events[0]['world']['arena'] = 9.
        path.write_text(''.join(json.dumps(event) + '\n' for event in events))
        for right in bad:
            with self.assertRaises(ValueError):
                self.export(left, right)
            self.assertFalse((self.root / 'comparison.html').exists())

    def test_hostile_text_is_escaped_and_credentials_are_not_exported(self):
        left, right = self.fixture(), self.fixture()
        path = left / 'recording/manifest.json'
        manifest = json.loads(path.read_text())
        manifest['profile'] = '</pre><script>alert(1)</script><img src=https://example.test/>'
        path.write_text(json.dumps(manifest))
        html = self.export(left, right).read_text()
        self.assertFalse(any(tag in {'script', 'img'} for tag, _ in Document(html).tags))
        self.assertEqual(json.loads(Document(html).metadata)['comparison']['left']['provenance']['profile'], manifest['profile'])
        manifest['profile'] = {'token': 'never publish'}
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'credential'):
            self.export(left, right, 'secret.html')
        self.assertFalse((self.root / 'secret.html').exists())

    def test_byte_budget_and_exclusive_output_preserve_existing_documents(self):
        from palimpsest import comparison
        from palimpsest.storage import StorageBudget, StorageLimits, StorageLimitError
        left, right = self.fixture(), self.fixture()
        with patch.object(comparison, 'MAX_HTML_BYTES', 1), self.assertRaises(ValueError):
            self.export(left, right)
        self.assertFalse((self.root / 'comparison.html').exists())
        with self.assertRaises(StorageLimitError):
            self.export(left, right, storage_budget=StorageBudget((self.root,), StorageLimits(max_bytes=1, min_free_bytes=0)))
        output = self.export(left, right)
        original = output.read_bytes()
        with self.assertRaises(FileExistsError):
            self.export(left, right)
        self.assertEqual(output.read_bytes(), original)

    def test_source_change_during_render_is_rejected_before_publication(self):
        from palimpsest import comparison
        left, right = self.fixture(), self.fixture()
        render = comparison._render
        def mutate_source(metadata, views):
            payload = render(metadata, views)
            path = right / 'recording/manifest.json'
            path.write_text(path.read_text() + '\n')
            return payload
        with patch.object(comparison, '_render', side_effect=mutate_source), self.assertRaisesRegex(ValueError, 'changed'):
            self.export(left, right)
        self.assertFalse((self.root / 'comparison.html').exists())

    def test_cli_keeps_json_default_and_exports_html_under_existing_storage_checks(self):
        from palimpsest.cli import main
        left, right = self.fixture(), self.fixture()
        argv = ['compare', str(left), str(right)]
        with contextlib.redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(main(argv), 0)
        self.assertEqual(json.loads(captured.getvalue()), artifacts.compare_runs(left, right))
        with patch.object(Path, 'home', return_value=self.root), contextlib.redirect_stdout(io.StringIO()) as captured:
            self.assertEqual(main([*argv, '--output', str(self.root / 'cli.html'), '--min-free-bytes', '0']), 0)
        self.assertEqual(json.loads(captured.getvalue())['artifact'], str(self.root / 'cli.html'))
        with patch.object(Path, 'home', return_value=self.root), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main([*argv, '--output', str(self.root / 'limited.html'), '--max-exports', '1']), 1)
        self.assertFalse((self.root / 'limited.html').exists())


if __name__ == '__main__':
    unittest.main()
