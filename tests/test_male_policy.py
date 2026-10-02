"""Bounded artifact fixtures; Torch execution requires an explicit runtime gate."""
import copy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from palimpsest import male_policy
from palimpsest.male_model import CELL_SHA256, FEATURE_PROTOCOL, canonical, digest, reachability, rewire, validate_graph
from test_male_model import graph_fixture

ROOT = Path(__file__).resolve().parents[1]
CELL = ROOT.parent / 'memory-mechanics/upstream/fly-gym/models/connectome_rnn_model.py'


class PolicyArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        original = validate_graph(graph_fixture())
        original.update(source_graph_sha256='a' * 64, graph_manifest_sha256='b' * 64,
                        topology_sha256=digest(original['edges']))
        control, control_report = rewire(original, 0)
        self.graphs = {'original': original, 'degree_rewired': control}
        spec = importlib.util.spec_from_file_location('male_training_fixture', ROOT / 'scripts/train_male_reduced.py')
        trainer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(trainer)
        collection = {'fixture': 'not actual training data'}
        self.protocol = {'training': trainer.INITIAL_PROTOCOL, 'feature_protocol': FEATURE_PROTOCOL,
            'feature_protocol_sha256': digest(FEATURE_PROTOCOL), 'cell_source_sha256': CELL_SHA256,
            'collection': collection, 'collection_sha256': digest(collection),
            'source_code_sha256': {name: 'c' * 64 for name in ('male_model.py', 'artifacts.py', 'records.py', 'train_male_reduced.py')},
            'rewiring': control_report,
            'graphs': {name: {key: graph[key] for key in ('topology_sha256', 'ordered_ids_sha256',
                'source_graph_sha256', 'graph_manifest_sha256', 'type_missing_ids')} | {'reachability': reachability(graph)}
                for name, graph in self.graphs.items()}}
        self.payloads = {'protocol.json': canonical(self.protocol)}
        for variant in male_policy.VARIANTS:
            self.payloads[variant + '-graph.json'] = canonical(self.graphs[variant])
            self.payloads[variant + '.pt'] = b'fixture bytes; no Torch deserialization in pure checks'
        self.report = {'status': 'completed', 'training_completed': True, 'training_attempted': True,
                       'held_out_used_for_selection': False, 'qualification_claims': []}
        self.publish()
        self.graph_patch = patch.object(male_policy, 'load_graph', return_value=original)
        self.graph_patch.start()
        self.addCleanup(self.graph_patch.stop)

    def publish(self):
        self.report['protocol_sha256'] = digest(json.loads(self.payloads['protocol.json']))
        self.report['files'] = [{'path': name, 'sha256': hashlib.sha256(payload).hexdigest(), 'size_bytes': len(payload)}
                                for name, payload in self.payloads.items()]
        ledger = {item['path']: item for item in self.report['files']}
        self.report['models'] = {variant: {'graph_file': variant + '-graph.json', 'checkpoint': ledger[variant + '.pt']}
                                 for variant in male_policy.VARIANTS}
        for name, payload in self.payloads.items():
            (self.root / name).write_bytes(payload)
        return self.write_report()

    def write_report(self):
        payload = canonical(self.report)
        (self.root / 'report.json').write_bytes(payload)
        self.report_hash = hashlib.sha256(payload).hexdigest()
        return self.report_hash

    def arguments(self):
        return dict(expected_report_sha256=self.report_hash, graph_path='fixture-graph',
                    graph_manifest='fixture-manifest', cell_path=CELL)

    def bundle(self):
        args = self.arguments()
        args.pop('cell_path')
        return male_policy._bundle(self.root, 'original', **args)

    def test_import_is_lazy(self):
        result = subprocess.run([sys.executable, '-c',
            "import sys; import palimpsest.male_policy; assert not ({'torch', 'numpy', 'mujoco'} & set(sys.modules))"],
            capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_completed_fixture_binds_files_graphs_protocol_and_report_before_torch(self):
        with patch.dict('sys.modules', {'torch': None}):
            graph, payload, provenance = self.bundle()
        self.assertEqual(graph, self.graphs['original'])
        self.assertEqual(payload, self.payloads['original.pt'])
        self.assertEqual(provenance['training_report_sha256'], self.report_hash)
        self.assertEqual(provenance['type_missing_ids'], [3])
        self.assertFalse(provenance['biological_sensor_mapping'])
        with self.assertRaisesRegex(ValueError, 'report hash'):
            male_policy._bundle(self.root, 'original', '0' * 64, 'unused', 'unused')
        for variant in ('female', '../original.pt', None):
            with self.assertRaisesRegex(ValueError, 'variant'):
                male_policy.load_policy(self.root, variant, **self.arguments())
        with self.assertRaisesRegex(ValueError, 'CPU'):
            male_policy.load_policy(self.root, 'original', device='cuda', **self.arguments())

    def test_fixture_rejects_incomplete_tampered_and_inconsistent_artifacts(self):
        self.report['status'] = 'failed'
        self.write_report()
        with self.assertRaisesRegex(ValueError, 'completed'):
            self.bundle()
        self.report['status'] = 'completed'
        self.publish()
        (self.root / 'original.pt').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'hash or size'):
            self.bundle()
        self.publish()
        changed = copy.deepcopy(self.protocol)
        changed['feature_protocol'] = {'feature_count': 1}
        self.payloads['protocol.json'] = canonical(changed)
        self.publish()
        with self.assertRaisesRegex(ValueError, 'feature'):
            self.bundle()
        self.payloads['protocol.json'] = canonical(self.protocol)
        changed = copy.deepcopy(self.graphs['original'])
        changed['edges'][0][2] += 1
        self.payloads['original-graph.json'] = canonical(changed)
        self.publish()
        with self.assertRaisesRegex(ValueError, 'graph or checkpoint'):
            self.bundle()
        self.payloads['original-graph.json'] = canonical(self.graphs['original'])
        self.publish()
        self.report['files'][0]['path'] = '../protocol.json'
        self.write_report()
        with self.assertRaisesRegex(ValueError, 'unknown or duplicate'):
            self.bundle()

    def test_checkpoint_archive_preflight_is_bounded_without_torch(self):
        def archive(compression=zipfile.ZIP_STORED):
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, 'w', compression=compression) as target:
                target.writestr('archive/data.pkl', b'fixture only')
                target.writestr('archive/data/0', b'\0' * 64)
            return buffer.getvalue()
        with patch.dict('sys.modules', {'torch': None}):
            male_policy._check_archive(archive())
            with self.assertRaisesRegex(ValueError, 'ZIP format'):
                male_policy._check_archive(b'legacy pickle is not accepted')
            with self.assertRaisesRegex(ValueError, 'expanded size'):
                male_policy._check_archive(archive(zipfile.ZIP_DEFLATED))
            with patch.object(male_policy, 'MAX_FILE_BYTES', 16), self.assertRaisesRegex(ValueError, 'byte limit'):
                male_policy._check_archive(archive())

    @unittest.skipUnless(os.environ.get('PALIMPSEST_MALE_TORCH_CHECKS') == '1', 'Torch execution requires the released model window')
    def test_cpu_loader_state_guards_and_single_invocation_policy(self):
        if not CELL.is_file():
            self.skipTest('pinned upstream cell source is unavailable')
        import numpy as np
        import torch
        from palimpsest.male_model import features, make_model
        model = make_model(self.graphs['original'], CELL, 7)
        checkpoint = {'format': 'palimpsest-male-reduced-v1', 'protocol_sha256': digest(self.protocol),
            'graph_sha256': digest(self.graphs['original']), 'ordered_ids_sha256': self.graphs['original']['ordered_ids_sha256'],
            'state_dict': model.state_dict()}
        def publish_checkpoint(value):
            buffer = io.BytesIO()
            torch.save(value, buffer)
            self.payloads['original.pt'] = buffer.getvalue()
            self.publish()
        publish_checkpoint(checkpoint)
        policy = male_policy.load_policy(self.root, 'original', seed=9, **self.arguments())
        obs = {'cam_left': np.full((128, 128, 3), 123, np.uint8), 'cam_right': np.zeros((128, 128, 3), np.uint8),
               'sensors': {'collision': 0, 'collision_angle': None, 'wind_direction': [1., 0.]}}
        row = {**obs, 'sensors': np.array([0., 0., 1., 0.])}
        x = torch.from_numpy(features(row)).reshape(1, 1, 388)
        with torch.inference_mode():
            expected_hidden, expected_action, expected_diag = policy.agent(x, policy.agent.reset(), diagnostics=True)
        calls = []
        hook = policy.agent.register_forward_hook(lambda *args: calls.append(1))
        result = policy.act({**obs, 'privileged': [999], 'pose': [999, 999]})
        hook.remove()
        self.assertEqual(len(calls), 1)
        np.testing.assert_array_equal(result['action'], expected_action.reshape(-1).numpy())
        np.testing.assert_array_equal(result['encoded_input'], expected_diag['encoded_input'].reshape(-1).numpy())
        np.testing.assert_array_equal(result['raw_output'], expected_diag['raw_output'].reshape(-1).numpy())
        self.assertTrue(torch.equal(policy.hidden, expected_hidden))
        policy.reset()
        np.testing.assert_array_equal(result['action'], policy.act(obs)['action'])
        before = policy.hidden.clone()
        with self.assertRaises(ValueError):
            policy.act({**obs, 'sensors': {**obs['sensors'], 'wind_direction': [float('nan'), 0.]}})
        self.assertTrue(torch.equal(policy.hidden, before))
        with torch.no_grad():
            policy.agent.cell.readout_head[-1].bias.fill_(float('inf'))
        with self.assertRaisesRegex(ValueError, 'nonfinite male cell'):
            policy.act(obs)
        self.assertTrue(torch.equal(policy.hidden, before))
        for name, mutate in [('cell.W_values', lambda t: t + 1), ('cell.input_nodes', lambda t: t.flip(0)),
                             ('encoder.0.weight', lambda t: t.double()), ('cell.bias', lambda t: t[:-1]),
                             ('cell.readout_head.4.bias', lambda t: torch.full_like(t, float('nan')))]:
            broken = copy.deepcopy(checkpoint)
            broken['state_dict'][name] = mutate(broken['state_dict'][name])
            publish_checkpoint(broken)
            with self.assertRaisesRegex(ValueError, 'checkpoint .*tensor'):
                male_policy.load_policy(self.root, 'original', **self.arguments())


if __name__ == '__main__':
    unittest.main()
