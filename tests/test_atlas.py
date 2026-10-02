"""Structural/export mechanics on an authored graph; no anatomical claim."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

from palimpsest import atlas


class AtlasChecks(unittest.TestCase):
    def test_paths_interventions_and_bounded_provenance_export(self):
        graph = {'ids': [1, 2, 3, 4, 5], 'inputs': [1, 2], 'outputs': [4, 5],
                 'edges': [[1, 3, 1], [2, 3, 2], [3, 4, 3], [2, 5, 4]],
                 'type_labels': [None], 'type_ids': [0]*5,
                 'source_graph_sha256': 'a'*64, 'graph_manifest_sha256': 'b'*64,
                 'extraction_protocol_sha256': 'c'*64, 'license': 'fixture',
                 'attribution': 'authored test only', 'boundary': {'description': '<not anatomy>'}}
        original = copy.deepcopy(graph)
        report = atlas.analyze(graph, [3])
        self.assertEqual(report['lost_input_ids_by_output'], {'4': [1, 2], '5': []})
        self.assertEqual(report['removed_edges'], 3)
        self.assertEqual(atlas.analyze(graph, [])['lost_input_output_pairs'], 0)
        self.assertEqual(atlas.analyze(graph, [4])['lost_input_output_pairs'], 2)
        self.assertEqual(atlas.analyze(graph, [1])['lost_input_ids_by_output'], {'4': [1], '5': []})
        self.assertEqual(graph, original)
        for nodes in ([True], [999], [3, 3], '3', [1]*33):
            with self.assertRaises(ValueError):
                atlas.analyze(graph, nodes)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source, manifest = root/'graph.json', root/'manifest.json'
            source.write_text('{}'); manifest.write_text('{}'); output = root/'atlas.svg'
            with patch.object(atlas.male_model, 'load_graph', return_value=graph):
                atlas.export_atlas(source, manifest, output, cut_nodes=[3])
                tree = ET.fromstring(output.read_bytes())
                value = json.loads(tree.find('{http://www.w3.org/2000/svg}metadata').text)
                self.assertEqual(value['lost_input_output_pairs'], 2)
                self.assertEqual(value['graph']['edges'], graph['edges'])
                self.assertEqual(value['renderer']['source_sha256'], hashlib.sha256(Path(atlas.__file__).read_bytes()).hexdigest())
                self.assertNotIn(b'<not anatomy>', output.read_bytes())
                first = output.read_bytes()
                with self.assertRaises(FileExistsError):
                    atlas.export_atlas(source, manifest, output, cut_nodes=[])
                self.assertEqual(first, output.read_bytes())
                with patch.object(atlas, 'MAX_OUTPUT_BYTES', 1), self.assertRaisesRegex(ValueError, 'byte limit'):
                    atlas.export_atlas(source, manifest, root/'over.svg', cut_nodes=[])
                self.assertFalse((root/'over.svg').exists())
                with patch.object(atlas.artifacts, '_fingerprint', side_effect=[(1,), (1,), (2,)]), self.assertRaisesRegex(ValueError, 'changed'):
                    atlas.export_atlas(source, manifest, root/'changed.svg', cut_nodes=[])
                self.assertFalse((root/'changed.svg').exists())
                # A deferred flush/close failure is inside the cleanup boundary.
                original_open = Path.open
                class CloseFailure:
                    def __init__(self, stream): self.stream = stream
                    def __enter__(self): return self
                    def write(self, data): return self.stream.write(data)
                    def __exit__(self, *args):
                        self.stream.close()
                        raise OSError('deferred close failure')
                def opened(path, *args, **kwargs):
                    stream = original_open(path, *args, **kwargs)
                    return CloseFailure(stream) if path.name == 'close.svg' else stream
                with patch.object(Path, 'open', opened), self.assertRaisesRegex(OSError, 'deferred close'):
                    atlas.export_atlas(source, manifest, root/'close.svg', cut_nodes=[])
                self.assertFalse((root/'close.svg').exists())


if __name__ == '__main__':
    unittest.main()
