"""Authored data/parameter fixtures; the opt-in CPU check is not task evidence."""
import copy
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import zipfile

import numpy as np
from palimpsest import puck_learning, puck_model

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import train_puck


class PuckCheckpointTests(unittest.TestCase):
    def test_failed_report_sync_or_expired_staging_cannot_publish_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp); report = {'status': 'completed', 'training_completed': True}
            with patch.object(train_puck.os, 'fsync', side_effect=OSError('injected fsync failure')):
                with self.assertRaises(OSError):
                    train_puck.publish_report(output, report, Mock(), 1024, time.monotonic()+30)
            self.assertFalse((output/'report.json').exists())
            self.assertTrue((output/'report.pending').exists())
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            with self.assertRaises(TimeoutError):
                train_puck.publish_report(output, report, Mock(), 1024, time.monotonic()-1)
            self.assertFalse((output/'report.json').exists())
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            train_puck.publish_report(output, report, Mock(), 1024, time.monotonic()+30)
            self.assertEqual(json.loads((output/'report.json').read_text()), report)
            self.assertFalse((output/'report.pending').exists())
            with self.assertRaises(FileExistsError):
                train_puck.publish_report(output, report, Mock(), 1024, time.monotonic()+30)

    def test_fixed_numeric_archive_roundtrip_and_admission(self):
        arrays = {n: np.zeros(s, np.float32) for n, s in puck_model.SHAPES.items()}
        arrays['0.weight'] = np.asfortranarray(arrays['0.weight'])
        payload = puck_model.checkpoint_bytes(arrays)
        decoded = puck_model.read_checkpoint(payload)
        for name in arrays:
            np.testing.assert_array_equal(arrays[name], decoded[name])
        for replacement in (np.zeros((32, 8), np.float32), np.zeros((32, 9), np.float64),
                            np.full((32, 9), np.inf, np.float32), np.zeros((32, 9), object)):
            stream = io.BytesIO(); np.savez(stream, **(arrays | {'0.weight': replacement}))
            with self.assertRaises(ValueError): puck_model.read_checkpoint(stream.getvalue())
        stream = io.BytesIO(); np.savez_compressed(stream, **arrays)
        for bad in (stream.getvalue(), b'broken', b'x'*(puck_model.MAX_CHECKPOINT+1)):
            with self.assertRaises(ValueError): puck_model.read_checkpoint(bad)
        # Reject a huge declared shape before array allocation, even with tiny content.
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as out, zipfile.ZipFile(io.BytesIO(payload)) as original:
            for item in original.infolist():
                raw = original.read(item)
                if item.filename == '0.weight.npy':
                    header = io.BytesIO()
                    np.lib.format.write_array_header_1_0(header, {'descr': '<f4', 'fortran_order': False,
                                                                 'shape': (2**40, 9)})
                    raw = header.getvalue()
                out.writestr(item.filename, raw)
        with self.assertRaisesRegex(ValueError, 'header'): puck_model.read_checkpoint(stream.getvalue())

    def test_prepare_and_pinned_bundle_use_all_twenty_sources_without_torch(self):
        from test_puck_learning import PuckLearningTests
        fixture = PuckLearningTests()
        with tempfile.TemporaryDirectory() as tmp:
            entries = []
            for seed in range(6000, 6020):
                split = 'train' if seed < 6016 else 'recorded_dev'
                path = Path(tmp)/str(seed)/'recording'; fixture.fixture(path, seed, split)
                entries.append({'seed': seed, 'split': split, 'path': str(path),
                                'manifest_sha256': train_puck.file_sha(path/'manifest.json')})
            collection = Path(tmp)/'collection.json'
            collection.write_text(json.dumps({'status': 'passed', 'admission': {'status': 'passed'},
                'learning_protocol_sha256': puck_learning.PROTOCOL_SHA256, 'sources': entries,
                'fixture': 'authored data only, no native collection'}))
            data, protocol = train_puck.prepare(ROOT, collection, train_puck.file_sha(collection), 21)
            self.assertEqual(data['train'][0].shape, (512, 9))
            self.assertEqual(data['recorded_dev'][1].dtype, np.float64)
            self.assertEqual(len(protocol['sources']), 20)
            task = puck_learning.load_protocol(ROOT)['task_protocol']
            self.assertIn(task['path'], protocol['source_hashes'])
            self.assertEqual(protocol['source_hashes'][task['path']], task['sha256'])
            self.assertNotIn('docs/plans/m6-puck-pushing-protocol-v4.json', protocol['source_hashes'])
            bundle = Path(tmp)/'seed-21'; bundle.mkdir()
            raw = puck_model.canonical(protocol); (bundle/'protocol.json').write_bytes(raw)
            checkpoint = puck_model.checkpoint_bytes({n: np.zeros(s, np.float32) for n, s in puck_model.SHAPES.items()})
            (bundle/'checkpoint.npz').write_bytes(checkpoint)
            report = {'status': 'completed', 'training_completed': True, 'training_seed': 21,
                'held_out_used': False, 'qualification_claims': [], 'finalization_errors': [],
                'protocol_sha256': puck_model.sha(raw), 'selected_epoch': 1,
                'history': [{'epoch': e, 'dev_loss': .25} for e in range(1, 31)],
                'files': [{'path': name, 'bytes': len(value), 'sha256': puck_model.sha(value)}
                          for name, value in (('protocol.json', raw), ('checkpoint.npz', checkpoint))],
                'fixture': 'authored bundle, no optimization'}
            def write_report(value):
                raw = puck_model.canonical(value); (bundle/'report.json').write_bytes(raw)
                return puck_model.sha(raw)
            report_sha = write_report(report)
            _, identity = puck_model.read_bundle(bundle, report_sha, ROOT, 21)
            self.assertEqual(identity['checkpoint_sha256'], puck_model.sha(checkpoint))
            for mutation in ({'status': 'failed'}, {'held_out_used': True}, {'selected_epoch': 2},
                             {'training_seed': 21.0}, {'history': report['history'][:-1]}):
                changed = report | mutation
                with self.assertRaises(ValueError): puck_model.read_bundle(bundle, write_report(changed), ROOT, 21)
            with self.assertRaises(ValueError): puck_model.read_bundle(bundle, '0'*64, ROOT, 21)
            # Both final training revalidation and pure loading bind the active task file.
            copied = Path(tmp)/'repo'
            for name in protocol['source_hashes']:
                target = copied/name; target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, target)
            report_sha = write_report(report)
            train_puck.check_sources(copied, protocol)
            puck_model.read_bundle(bundle, report_sha, copied, 21)
            task_path = copied/task['path']; task_path.write_bytes(task_path.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'Training code/protocol changed'):
                train_puck.check_sources(copied, protocol)
            with self.assertRaisesRegex(ValueError, 'Frozen task/teacher source differs'):
                puck_model.read_bundle(bundle, report_sha, copied, 21)
            original_collection = collection.read_bytes()
            for change in ({'status':'failed'}, {'learning_protocol_sha256':
                    '513c7f5045b919241d7fdc6fa6ab058bd94134f8d168661b6453fadfb3b6b158'}):
                collection.write_text(json.dumps(json.loads(original_collection)|change))
                with self.assertRaisesRegex(ValueError, 'Passed frozen teacher collection/admission required'):
                    train_puck.prepare(ROOT, collection, train_puck.file_sha(collection), 21)
            collection.write_bytes(original_collection)
            with self.assertRaises(ValueError): train_puck.prepare(ROOT, collection, train_puck.file_sha(collection), 22.0)
            with self.assertRaisesRegex(ValueError, 'output'):
                train_puck.train(ROOT, Path(tmp)/'wrong-output', data, protocol)
            source = Path(entries[0]['path'])/'manifest.json'
            source.write_bytes(source.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'source changed'): train_puck.check_sources(ROOT, protocol)


@unittest.skipUnless(os.environ.get('PALIMPSEST_TEST_PUCK_TORCH') == '1', 'explicit CPU model slot required')
class PuckTorchTests(unittest.TestCase):
    def test_exact_scaling_gradient_seeded_fit_and_reloaded_predictions(self):
        import torch
        from test_puck_learning import sensors
        values = puck_learning.prepare(sensors(), puck_learning.initial_cursor())['inputs']
        model = puck_model.make_model(21)
        initial = puck_model.predict(model, values)
        np.testing.assert_array_equal(initial, puck_model.predict(puck_model.make_model(21), values))
        with torch.no_grad():
            for parameter in model.parameters(): parameter.zero_()
            model[4].bias[:] = torch.tensor([100., -100.])
        self.assertEqual(puck_model.predict(model, values).tolist(), [.4, -.4])
        model = puck_model.make_model(21)
        x = torch.from_numpy(np.stack([values, values]))
        prediction = puck_model.actions(model, x)
        self.assertEqual(prediction.dtype, torch.float64)
        train_puck.loss(prediction, torch.zeros((2, 2), dtype=torch.float64)).backward()
        self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in model.parameters()))
        data = {'train': (x.numpy(), np.array([[.2, 0.], [.2, 0.]], np.float64)),
                'recorded_dev': (x.numpy(), np.array([[.2, 0.], [.2, 0.]], np.float64))}
        first, report = train_puck.fit(data, 21, time.monotonic()+30)
        second, other = train_puck.fit(data, 21, time.monotonic()+30)
        self.assertEqual(report, other); self.assertEqual(len(report['history']), 30)
        self.assertEqual(report['selected_epoch'], min(report['history'], key=lambda r: r['dev_loss'])['epoch'])
        for name in first: np.testing.assert_array_equal(first[name], second[name])
        restored = puck_model.read_checkpoint(puck_model.checkpoint_bytes(first))
        model.load_state_dict({n: torch.from_numpy(v) for n, v in first.items()})
        loaded = puck_model.make_model(21)
        loaded.load_state_dict({n: torch.from_numpy(v) for n, v in restored.items()})
        np.testing.assert_array_equal(puck_model.predict(model, values), puck_model.predict(loaded, values))
        with self.assertRaises(TimeoutError): train_puck.fit(data, 21, time.monotonic()-1)
        bad = values.copy(); bad[8] = .5
        with self.assertRaises(ValueError): puck_model.predict(model, bad)


if __name__ == '__main__': unittest.main()
