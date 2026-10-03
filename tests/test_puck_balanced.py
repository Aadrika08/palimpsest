"""Pure authored weighting/lineage fixtures; no fitted policy or task evidence."""
import copy
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import numpy as np
from palimpsest import puck_balanced as balanced, puck_learning, puck_model

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import train_puck


def examples():
    x = np.zeros((7, 9), np.float32)
    x[4:, 8] = 1
    y = np.array([[0, 0], [0, .4], [.25, .1], [-.25, -.1],
                  [0, -.4], [.2, .1], [-.2, .1]], np.float64)
    return x, y


def dataset():
    x, y = examples()
    ids = np.repeat(np.arange(7), balanced.COUNTS)
    return x[ids], y[ids]


def protocol_fixture():
    spec = balanced.load_protocol(ROOT);base = puck_learning.load_protocol(ROOT)
    names = (*train_puck.SOURCE_FILES, *balanced.SOURCE_FILES)
    return {'schema': balanced.SCHEMA, 'training_seed': 21,
        'balanced_objective': {'path': balanced.PROTOCOL_PATH, 'sha256': balanced.PROTOCOL_SHA256},
        'training_objective': spec['objective'], 'strata': spec['strata'],
        'learning_protocol_sha256': puck_learning.PROTOCOL_SHA256,
        'learning': base['learning'], 'action_arithmetic': base['action_arithmetic'],
        'collection_report': {'path': '/authored-fixture-only', 'sha256': spec['collection_report_sha256']},
        'limits': {'per_seed': base['limits']['training_per_seed'],
            'all_training_bytes': base['limits']['all_training_bytes'], 'min_free_bytes': base['limits']['min_free_bytes']},
        'source_hashes': {n: train_puck.file_sha(ROOT/n) for n in names},
        'sources': [{'seed': s, 'split': 'train' if s < 6016 else 'recorded_dev',
                     'ticks': (370 if s == 6015 else 356) if s < 6016 else (330 if s == 6019 else 328)}
                    for s in range(6000, 6020)],
        'held_out_used': False, 'qualification_claims': [], 'fixture': 'authored metadata, not teacher admission'}


class PuckBalancedTests(unittest.TestCase):
    def test_exact_partition_stop_priority_signs_and_fixed_weight_mass(self):
        x, y = examples()
        np.testing.assert_array_equal(balanced.stratum_ids(x, y), np.arange(7))
        x[0, 8] = 1;np.testing.assert_array_equal(balanced.stratum_ids(x, y), np.arange(7))
        y[1, 0] = np.nextafter(np.float64(0), np.float64(1))
        self.assertEqual(balanced.stratum_ids(x, y)[1], 2)
        x, y = dataset();before = x.tobytes(), y.tobytes()
        weights = balanced.row_weights(x, y);ids = balanced.stratum_ids(x, y)
        self.assertEqual(weights.dtype, np.float64)
        for code, count in enumerate(balanced.COUNTS):
            if count:self.assertAlmostEqual(float(weights[ids == code].sum()), 5710/6, places=10)
        self.assertAlmostEqual(float(weights.mean()), 1., places=14)
        self.assertEqual(before, (x.tobytes(), y.tobytes()))
        self.assertEqual(balanced.load_protocol(ROOT)['strata']['train_counts'], list(balanced.COUNTS))

    def test_bad_features_targets_counts_and_nontraining_rows_are_rejected(self):
        x, y = dataset()
        bad_inputs = [x.astype(np.float64), x[:, :8], x.copy(), x.copy(), x.copy()]
        bad_inputs[2][0, 8] = .5;bad_inputs[3][0, 6] = .5;bad_inputs[4][0, 7] = 1
        for bad in bad_inputs:
            with self.assertRaises(ValueError):balanced.row_weights(bad, y)
        for bad in (y.astype(np.float32), np.full(y.shape, np.inf), np.full(y.shape, .4000000001)):
            with self.assertRaises(ValueError):balanced.row_weights(x, bad)
        with self.assertRaisesRegex(ValueError, 'counts'):balanced.row_weights(x[:-1], y[:-1])
        wrong = y.copy();wrong[0] = [0, .4]
        with self.assertRaisesRegex(ValueError, 'counts'):balanced.row_weights(x, wrong)
        with self.assertRaisesRegex(ValueError, 'counts'):balanced.row_weights(x[:1314], y[:1314])

    def test_batch_math_uses_row_count_not_sum_of_weights(self):
        rows = np.array([.5, 2.], np.float64);weights = np.array([2., .5], np.float64)
        self.assertEqual(balanced.batch_mean(rows, weights), 1.)
        self.assertNotEqual(balanced.batch_mean(rows, weights), float((rows*weights).sum()/weights.sum()))
        self.assertEqual(balanced.batch_mean(rows[:1], weights[:1]), 1.)
        with self.assertRaises(ValueError):balanced.batch_mean(rows, weights[:1])
        with self.assertRaises(ValueError):balanced.batch_mean(rows[:0], weights[:0])
        x, y = dataset();ids = balanced.stratum_ids(x, y);w = balanced.row_weights(x, y)
        losses = np.arange(5710, dtype=np.float64)/5710
        self.assertAlmostEqual(float(balanced.batch_mean(losses, w)),
            sum(float(losses[ids == i].mean()) for i, n in enumerate(balanced.COUNTS) if n)/6, places=14)

    def test_invalid_fit_weights_fail_before_any_torch_import(self):
        x, y = dataset();weights = balanced.row_weights(x, y);weights[0] += .01
        with self.assertRaisesRegex(ValueError, 'Exact fixed'):
            train_puck.fit({'train': (x, y)}, 21, 0, row_weights=weights)

    def test_protocol_rejects_seed_types_objective_aliases_order_and_selection_changes(self):
        p = protocol_fixture();balanced.validate_protocol(p, ROOT)
        for mutation in ({'training_seed': True}, {'training_seed': 21.0}, {'schema': 'puck-training-v1'},
                         {'training_objective': {}}, {'held_out_used': True}):
            with self.assertRaises(ValueError):balanced.validate_protocol(p | mutation, ROOT)
        changed = copy.deepcopy(p);changed['strata']['train_counts'][0] = 381.0
        with self.assertRaises(ValueError):balanced.validate_protocol(changed, ROOT)
        changed = copy.deepcopy(p);changed['sources'][0], changed['sources'][1] = changed['sources'][1], changed['sources'][0]
        with self.assertRaises(ValueError):balanced.validate_protocol(changed, ROOT)
        changed = copy.deepcopy(p);changed['learning']['selection'] = 'latest minimum'
        with self.assertRaises(ValueError):balanced.validate_protocol(changed, ROOT)

    def test_prepare_requires_exact_collection_and_explicit_boolean_option(self):
        with patch.object(puck_learning, 'admit_batch') as admission:
            for seed, option in ((True, True), (21, 'yes'), (21, True)):
                with self.assertRaises(ValueError):train_puck.prepare(ROOT, '/unused', '0'*64, seed, balanced=option)
            admission.assert_not_called()

    def test_objective_source_and_protocol_byte_changes_are_rejected(self):
        p = protocol_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in p['source_hashes']:
                destination = root/name;destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT/name, destination)
            balanced.validate_protocol(p, root)
            source = root/'src/palimpsest/puck_balanced.py'
            original = source.read_bytes();source.write_bytes(original+b'\n')
            with self.assertRaisesRegex(ValueError, 'source differs'):balanced.validate_protocol(p, root)
            source.write_bytes(original)
            objective = root/balanced.PROTOCOL_PATH;objective.write_bytes(objective.read_bytes()+b' ')
            with self.assertRaisesRegex(ValueError, 'objective differs'):balanced.validate_protocol(p, root)

    def test_separate_reader_rejects_default_schema_corruption_and_wrong_epoch(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp);p = protocol_fixture()
            proto = puck_model.canonical(p);(directory/'protocol.json').write_bytes(proto)
            payload = puck_model.checkpoint_bytes({n: np.zeros(s, np.float32) for n, s in puck_model.SHAPES.items()})
            (directory/'checkpoint.npz').write_bytes(payload)
            report = {'status': 'completed', 'training_completed': True, 'training_seed': 21,
                'held_out_used': False, 'qualification_claims': [], 'finalization_errors': [],
                'training_objective_sha256': balanced.PROTOCOL_SHA256, 'protocol_sha256': puck_model.sha(proto),
                'selected_epoch': 2, 'history': [{'epoch': e, 'train_ticks': 5710, 'dev_ticks': 1314,
                    'weighted_train_loss': .4, 'dev_loss': .3 if e == 1 else .2} for e in range(1, 31)],
                'files': [{'path': n, 'bytes': len(b), 'sha256': puck_model.sha(b)}
                          for n, b in (('protocol.json', proto), ('checkpoint.npz', payload))]}
            def write(value):
                raw = puck_model.canonical(value);(directory/'report.json').write_bytes(raw);return puck_model.sha(raw)
            pin = write(report);arrays, identity = balanced.read_bundle(directory, pin, ROOT, 21)
            self.assertEqual(set(arrays), set(puck_model.SHAPES))
            self.assertEqual(identity['training_objective_sha256'], balanced.PROTOCOL_SHA256)
            with self.assertRaises(ValueError):puck_model.read_bundle(directory, pin, ROOT, 21)
            for change in ({'selected_epoch': 3}, {'selected_epoch': 2.0}, {'training_seed': True},
                           {'training_objective_sha256': '0'*64}, {'status': 'failed'}):
                with self.assertRaises(ValueError):balanced.read_bundle(directory, write(report | change), ROOT, 21)
            changed = copy.deepcopy(report);changed['history'][0]['train_loss'] = .4
            with self.assertRaises(ValueError):balanced.read_bundle(directory, write(changed), ROOT, 21)
            with self.assertRaises(ValueError):balanced.read_bundle(directory, '0'*64, ROOT, 21)
            (directory/'checkpoint.npz').write_bytes(b'broken')
            with self.assertRaises(ValueError):balanced.read_bundle(directory, write(report), ROOT, 21)


@unittest.skipUnless(os.environ.get('PALIMPSEST_TEST_PUCK_TORCH') == '1', 'explicit CPU model slot required')
class PuckBalancedTorchTests(unittest.TestCase):
    def test_weighted_gradient_default_loss_and_deterministic_fixed_fit(self):
        """Authored arrays only: mechanism evidence, never actual demonstration training."""
        import torch
        actions = torch.tensor([[.1, -.2], [.3, .05]], dtype=torch.float64, requires_grad=True)
        targets = torch.tensor([[0., .1], [.2, 0.]], dtype=torch.float64)
        weights = torch.tensor([2., .5], dtype=torch.float64)
        residual = actions.detach().numpy()-targets.numpy()
        value = train_puck.loss(actions, targets, weights=weights)
        expected = float(np.mean(weights.numpy()*np.mean((residual/.4)**2, axis=1)))
        self.assertAlmostEqual(float(value), expected, places=14)
        value.backward()
        np.testing.assert_allclose(actions.grad.numpy(), weights.numpy()[:,None]*residual/(.16*2), rtol=0, atol=1e-14)
        self.assertAlmostEqual(float(train_puck.loss(actions, targets)), float(np.mean((residual/.4)**2)), places=14)
        for invalid in (weights.float(), torch.tensor([1., float('nan')], dtype=torch.float64),
                        torch.tensor([1., 0.], dtype=torch.float64)):
            with self.assertRaises(ValueError):train_puck.loss(actions, targets, weights=invalid)
        x, y = dataset();w = balanced.row_weights(x,y)
        data = {'train': (x,y), 'recorded_dev': (x[:1314].copy(),y[:1314].copy())}
        first, report = train_puck.fit(data,21,time.monotonic()+30,row_weights=w)
        second, repeated = train_puck.fit(data,21,time.monotonic()+30,row_weights=w)
        self.assertEqual(report,repeated)
        for name in first:np.testing.assert_array_equal(first[name],second[name])
        self.assertEqual(len(report['history']),30)
        self.assertTrue(all('weighted_train_loss' in r and 'train_loss' not in r for r in report['history']))
        selected = min(report['history'],key=lambda r:r['dev_loss'])
        self.assertEqual(report['selected_epoch'],selected['epoch'])
        checkpoint = puck_model.read_checkpoint(puck_model.checkpoint_bytes(first))
        model = puck_model.make_model(21)
        model.load_state_dict({name:torch.from_numpy(value) for name,value in checkpoint.items()},strict=True)
        with torch.no_grad():
            dev = train_puck.loss(puck_model.actions(model,torch.from_numpy(data['recorded_dev'][0])),
                                  torch.from_numpy(data['recorded_dev'][1]))
        self.assertAlmostEqual(float(dev),selected['dev_loss'],places=8)


if __name__ == '__main__':unittest.main()
