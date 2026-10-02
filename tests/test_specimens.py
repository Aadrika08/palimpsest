import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from palimpsest import specimens


class SpecimenPair(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = {'version': 1, 'correspondence': {
            'curator': 'Fixture curator', 'evidence': 'Synthetic validation only',
            'uncertainty': 'No actual specimen correspondence', 'source_url': 'https://example.org/fixture'},
            'specimens': []}
        for name, units, text in [('a', 'nm', '1 0 0 0 0 1 -1\n2 0 1000 0 2000 1 1\n'),
                                  ('b', 'um', '1 0 0 0 0 1 -1\n2 0 1 0 2 1 1\n')]:
            (self.root/f'{name}.swc').write_text(text)
            self.manifest['specimens'].append(dict(dataset='fixture', version='1', specimen=name,
                sex='unknown', cell_id=name, cell_type='fixture', side='unknown', file=f'{name}.swc',
                sha256=hashlib.sha256(text.encode()).hexdigest(), units=units,
                coordinate_space='fixture space', coverage='synthetic', license='fixture only',
                attribution='Test fixture', source_url='https://example.org/fixture'))
        self.path = self.root/'pair.json'
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.manifest))

    def test_shared_units_topology_determinism_and_exclusive_output(self):
        output = specimens.export_specimens(self.path, self.root/'pair.svg')
        xml = ET.fromstring(output.read_bytes())
        ns = {'s': 'http://www.w3.org/2000/svg'}
        report = json.loads(xml.find('s:metadata', ns).text)
        self.assertEqual(report['structures'][0]['bounds_um'], report['structures'][1]['bounds_um'])
        self.assertEqual([x['edges'] for x in report['structures']], [1, 1])
        segments = xml.findall('.//s:path[@data-segments]', ns)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].attrib, segments[1].attrib)
        self.assertEqual(segments[0].attrib['d'], 'M1.0,2.0 L0.0,0.0')
        self.assertEqual(segments[0].attrib['data-segments'], '1')
        other = specimens.export_specimens(self.path, self.root/'again.svg')
        self.assertEqual(output.read_bytes(), other.read_bytes())
        before = output.read_bytes()
        with self.assertRaises(FileExistsError):
            specimens.export_specimens(self.path, output)
        self.assertEqual(output.read_bytes(), before)

    def test_invalid_input_and_graph_rejected(self):
        valid = copy.deepcopy(self.manifest)
        for change in (lambda m:m['specimens'][0].update(file='../a.swc'),
                       lambda m:m['specimens'][0].update(sha256='0'*64),
                       lambda m:m['specimens'][0].update(units='voxels'),
                       lambda m:m['correspondence'].update(uncertainty=''),
                       lambda m:m.update(version=True)):
            self.manifest = copy.deepcopy(valid);change(self.manifest);self.save()
            with self.assertRaises(ValueError):
                specimens.export_specimens(self.path, self.root/'bad.svg')
            self.assertFalse((self.root/'bad.svg').exists())
        for text in ('1 0 nan 0 0 1 -1\n', '1 0 0 0 0 1 2\n',
                     '1 0 0 0 0 1 2\n2 0 0 0 0 1 1\n',
                     '1 0 0 0 0 1 -1\n1 0 0 0 0 1 -1\n'):
            with self.assertRaises(ValueError):
                specimens.parse_swc(text.encode(), 'um')
        forest = specimens.parse_swc(b'1 0 0 0 0 1 -1\n2 0 0 0 0 1 -1\n', 'um')
        self.assertEqual(len(forest), 2)

    def test_escaping_and_write_failure_cleanup(self):
        from unittest.mock import patch
        self.manifest['correspondence']['evidence'] = '<script> & "quoted"'
        self.save()
        output = specimens.export_specimens(self.path, self.root/'escaped.svg')
        xml = ET.fromstring(output.read_bytes())
        self.assertFalse(any(x.tag.endswith('script') for x in xml.iter()))
        self.assertIn('&lt;script&gt;', output.read_text())
        original = Path.open
        class Broken:
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def write(self, data): self.stream.write(data[:20]); raise OSError('fixture write failure')
        def opening(path, mode='r', *args, **kwargs):
            stream = original(path, mode, *args, **kwargs)
            if mode == 'xb':
                result = Broken(); result.stream = stream; return result
            return stream
        with patch.object(Path, 'open', opening), self.assertRaises(OSError):
            specimens.export_specimens(self.path, self.root/'partial.svg')
        self.assertFalse((self.root/'partial.svg').exists())

    def test_cli_dispatch_uses_existing_storage_admission(self):
        import contextlib
        import io
        from unittest.mock import patch
        from palimpsest.cli import main
        output = self.root/'cli.svg'
        with patch('palimpsest.storage.StorageBudget.lock', return_value=contextlib.nullcontext()), \
             contextlib.redirect_stdout(io.StringIO()) as captured:
            code = main(['specimens', str(self.path), '--output', str(output)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(captured.getvalue())['artifact'], str(output))
        self.assertTrue(output.is_file())


if __name__ == '__main__':
    unittest.main()
