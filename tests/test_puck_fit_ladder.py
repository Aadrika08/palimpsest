"""Synthetic tests only: never open a retained recording or fit the real corpus."""
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import puck_fit_ladder as ladder
from palimpsest import puck_model


def tiny():
    x = np.zeros((8, 9), np.float32)
    x[:, 0] = np.linspace(.01, .08, 8)
    x[:, 2] = .1
    x[4:, 8] = 1
    y = np.zeros((8, 2), np.float64)
    y[:4, 1] = .4
    return {'train': (x, y), 'recorded_dev': (x.copy(), y.copy())}


class PuckLadderTests(unittest.TestCase):
    def test_train_only_stats_and_constant_flags(self):
        data = tiny()
        mean, scale = ladder.statistics(data['train'][0])
        self.assertAlmostEqual(float(mean[0]), .045, places=6)
        self.assertEqual(float(scale[1]), 1.)
        np.testing.assert_array_equal(mean[6:], 0)
        np.testing.assert_array_equal(scale[6:], 1)
        changed = tiny(); changed['recorded_dev'][0][:, 0] = 1
        np.testing.assert_array_equal(ladder.statistics(changed['train'][0])[0], mean)

    @unittest.skipUnless(os.environ.get('PALIMPSEST_TEST_PUCK_TORCH') == '1', 'explicit CPU model slot required')
    def test_normalization_inside_guards_and_folded_export(self):
        import torch
        x = tiny()['train'][0]
        mean, scale = ladder.statistics(x)
        model = ladder.make_model(21, 32, mean, scale)
        folded, parity = ladder.folded_export(model, x)
        puck_model.validate_arrays(folded)
        self.assertLessEqual(parity, 1e-6)
        bad = x.copy(); bad[0, 0] = 1.01
        with self.assertRaises(ValueError):
            puck_model.actions(model, torch.from_numpy(bad))

    def test_exact_grouped_split_and_heldout_preflight(self):
        sources = [{'seed': s, 'split': 'train' if s < 6016 else 'recorded_dev',
                    'ticks': 1, 'path': '/synthetic/' + str(s)} for s in range(6000, 6020)]
        ladder.check_split(sources)
        for key, value in [('seed', 6020), ('split', 'held_out')]:
            bad = [dict(s) for s in sources]; bad[-1][key] = value
            with self.assertRaises(ValueError):
                ladder.check_split(bad)

    def test_finite_and_immutable_arrays(self):
        data = tiny(); ladder.validate_data(data)
        self.assertFalse(data['train'][0].flags.writeable)
        data = tiny(); data['recorded_dev'][1][0, 1] = np.nan
        with self.assertRaises(ValueError):
            ladder.validate_data(data)

    def test_metrics_empty_turn_stratum_ineligible_and_zero_heading_excluded(self):
        x, y = tiny()['recorded_dev']; prediction = y.copy()
        result = ladder.metrics(x, y, prediction)
        self.assertEqual(result['heading_sign_agreement'], 1.)
        self.assertTrue(result['eligible'])
        y[:] = 0
        result = ladder.metrics(x, y, y.copy())
        self.assertFalse(result['eligible'])
        self.assertIsNone(result['approach_turn_only_leak'])

    def test_reproduction_checks_every_epoch_and_response(self):
        history = [{'epoch': i, 'train_ticks': 8, 'dev_ticks': 8,
                    'train_loss': .1, 'dev_loss': .2} for i in range(1, 31)]
        result = {'selected_epoch': 1, 'history': history}
        ladder.compare_reproduction(result, result, np.zeros((8, 2)), np.zeros((8, 2)))
        changed = json.loads(json.dumps(result)); changed['history'][18]['train_loss'] += 2e-6
        with self.assertRaises(ValueError):
            ladder.compare_reproduction(result, changed, np.zeros((8, 2)), np.zeros((8, 2)))
        with self.assertRaises(ValueError):
            ladder.compare_reproduction(result, result, np.zeros((8, 2)), np.ones((8, 2))*2e-6)

    def test_receipt_requires_all_seeds_and_exact_identity(self):
        identity = {'collection': 'x', 'sources': {'a': 'b'}}
        receipt = {'schema': ladder.SCHEMA, 'stage': 'reproduce', 'status': 'passed',
                   'identity': identity, 'held_out_used': False, 'qualification_claims': [],
                   'results': [{'seed': s, 'status': 'passed'} for s in (21, 22, 23)]}
        ladder.require_receipt(receipt, identity)
        for receipt_change in ({'status': 'failed'}, {'identity': {}}, {'results': receipt['results'][:2]}):
            with self.assertRaises(ValueError):
                ladder.require_receipt(receipt | receipt_change, identity)

    def test_deadline_stops_fit_and_nn(self):
        with self.assertRaises(TimeoutError):
            ladder.fit_probe(tiny(), 21, 32, 1, False, time.monotonic()-1)
        with self.assertRaises(TimeoutError):
            ladder.nearest_neighbor(tiny(), time.monotonic()-1, memory_bytes=1024)

    def test_chunked_nn_is_train_only(self):
        data = tiny(); data['recorded_dev'] = (data['train'][0][::-1].copy(), data['recorded_dev'][1])
        prediction = ladder.nearest_neighbor(data, time.monotonic()+5, memory_bytes=1024)
        np.testing.assert_array_equal(prediction, data['train'][1][::-1])

    @unittest.skipUnless(os.environ.get('PALIMPSEST_TEST_PUCK_TORCH') == '1', 'explicit CPU model slot required')
    def test_one_epoch_synthetic_fit_and_selected_final_loss(self):
        arrays, result, model = ladder.fit_probe(tiny(), 21, 32, 1, True, time.monotonic()+10)
        self.assertEqual(result['selected_epoch'], 1)
        self.assertIn('online_train_loss', result['history'][0])
        self.assertIn('selected_checkpoint_train_loss', result)
        self.assertEqual(set(arrays), set(puck_model.SHAPES))

    def test_cli_fresh_output_deadline_and_receipt_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); existing = root/'existing'; existing.mkdir()
            base = ['--stage', 'explore', '--repo', str(root), '--training-root', str(root/'inputs'/'original'),
                    '--collection-report', str(root/'inputs'/'collection.json'), '--collection-sha256', ladder.COLLECTION_SHA,
                    '--seconds', '1']
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ladder.main(base + ['--output', str(existing)]), 1)
                self.assertEqual(ladder.main(base + ['--output', str(root/'new')]), 1)
                self.assertFalse((root/'new').exists())
                self.assertEqual(ladder.main(base + ['--output', str(root/'new'), '--seconds', '2401']), 1)

    @unittest.skipUnless(os.environ.get('PALIMPSEST_TEST_PUCK_TORCH') == '1', 'explicit CPU model slot required')
    def test_actual_cli_with_injected_synthetic_admission(self):
        import train_puck
        data = tiny(); originals = {s: train_puck.fit(data, s, time.monotonic()+10) for s in puck_model.SEEDS}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'inputs'; source.mkdir()
            receipt_path = source/'receipt.json'
            base = ['--repo', str(root), '--training-root', str(source/'original'),
                    '--collection-report', str(source/'collection.json'), '--collection-sha256', ladder.COLLECTION_SHA,
                    '--seconds', '10']
            identity = {'synthetic': True}
            with patch.object(ladder, 'admit', return_value=(data, {}, originals, identity)), \
                    patch.object(ladder, 'check_identity'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ladder.main(base + ['--stage', 'reproduce', '--output', str(root/'reproduction')]), 0)
                receipt = json.loads((root/'reproduction'/'report.json').read_text())
                self.assertEqual(receipt['status'], 'passed')
                self.assertEqual([r['status'] for r in receipt['results']], ['passed']*3)
                self.assertEqual(len(receipt['files']), 3)
                self.assertFalse(any('inputs' in f['path'] for f in receipt['files']))
                receipt_path.write_text(json.dumps(receipt | {'identity': {'changed': True}}))
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(ladder.main(base + ['--stage', 'explore', '--output', str(root/'explore'),
                                                          '--reproduction-report', str(receipt_path)]), 1)
                self.assertFalse((root/'explore').exists())
                receipt_path.write_text(json.dumps(receipt))
                actual_fit = ladder.fit_probe
                def one_epoch(data, seed, width, epochs, cosine, deadline):
                    return actual_fit(data, seed, width, 1, cosine, deadline)
                with patch.object(ladder, 'fit_probe', side_effect=one_epoch):
                    self.assertEqual(ladder.main(base + ['--stage', 'explore', '--output', str(root/'explore'),
                                                          '--reproduction-report', str(receipt_path)]), 0)
                explored = json.loads((root/'explore'/'report.json').read_text())
                self.assertEqual([len(r['seeds']) for r in explored['results']], [3, 3, 3])
                self.assertEqual(explored['nearest_neighbor_diagnostic']['status'], 'completed')
                self.assertIsNone(explored['selected_neural_rung'])
                with np.load(root/'explore'/'capacity256-seed-21.npz', allow_pickle=False) as checkpoint:
                    self.assertEqual(checkpoint['0.weight'].shape, (256, 9))
                    with self.assertRaises(ValueError):
                        puck_model.validate_arrays({name: checkpoint[name] for name in puck_model.SHAPES})

    def test_deadline_outcomes_preserve_attempted_and_unattempted_seeds(self):
        results = []
        with patch.object(ladder, 'fit_probe', side_effect=TimeoutError('synthetic deadline')):
            outcome = ladder.run_stage(SimpleNamespace(stage='explore'), tiny(), {}, time.monotonic()+5,
                                       lambda name, payload: None, results)
        self.assertEqual(outcome['status'], 'budget_exhausted')
        self.assertEqual([r['status'] for r in results], ['incomplete', 'unattempted', 'unattempted'])
        self.assertEqual([s['status'] for s in results[0]['seeds']], ['incomplete', 'unattempted', 'unattempted'])

    def test_reconstruction_calls_teacher_with_guarded_canonical_world(self):
        x, _ = tiny()['train']
        prediction, unsupported = ladder.reconstruct_labels(x, time.monotonic()+5)
        self.assertEqual(unsupported, [])
        np.testing.assert_array_equal(prediction[:3, 0], -.25)
        self.assertEqual(prediction[3, 0], .2)
        self.assertTrue(np.isfinite(prediction).all())

    def test_output_overlap_refused_and_byte_floor_enforced(self):
        from palimpsest.storage import StorageBudget, StorageLimits, StorageLimitError
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'out'
            budget = StorageBudget((output,), StorageLimits(max_bytes=10, min_free_bytes=0))
            with self.assertRaises(StorageLimitError):
                budget.check(11, path=output/'file')
            with patch('palimpsest.storage.shutil.disk_usage', return_value=SimpleNamespace(free=10)):
                budget = StorageBudget((output,), StorageLimits(max_bytes=100, min_free_bytes=10))
                with self.assertRaises(StorageLimitError):
                    budget.check(1, path=output/'file')

    def test_cli_nonfinite_injected_data_and_heldout_preflight(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'inputs'; source.mkdir()
            collection = source/'collection.json'
            sources = [{'seed': s, 'split': 'train' if s < 6016 else 'recorded_dev'} for s in range(6000, 6020)]
            sources[-1]['seed'] = 6020
            collection.write_text(json.dumps({'sources': sources}))
            base = ['--stage', 'reproduce', '--repo', str(root), '--training-root', str(source/'original'),
                    '--collection-report', str(collection), '--collection-sha256', ladder.COLLECTION_SHA,
                    '--seconds', '10', '--output', str(root/'run')]
            with patch.object(ladder.train_puck, 'file_sha', return_value=ladder.COLLECTION_SHA), \
                    patch.object(ladder.train_puck, 'prepare') as prepare, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ladder.main(base), 1)
                prepare.assert_not_called()
            self.assertFalse((root/'run').exists())
            data = tiny(); data['train'][0][0, 0] = np.inf
            with patch.object(ladder, 'admit', return_value=(data, {}, {}, {})), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ladder.main(base), 1)
            self.assertFalse((root/'run').exists())

    def test_reproduction_failure_stops_track_and_preserves_attempt(self):
        results = []
        with patch.object(ladder.train_puck, 'fit', side_effect=ValueError('synthetic mismatch')) as fit:
            with self.assertRaises(ValueError):
                ladder.run_stage(SimpleNamespace(stage='reproduce'), tiny(), {}, time.monotonic()+5,
                                 lambda name, payload: None, results)
        fit.assert_called_once()
        self.assertEqual([r['status'] for r in results], ['incomplete', 'unattempted', 'unattempted'])

    def test_expired_finalization_does_not_open_or_rehash_inputs(self):
        with patch.object(Path, 'open', side_effect=AssertionError('No reads after deadline')):
            with self.assertRaises(TimeoutError):
                ladder.bounded_sha('/unused/input', time.monotonic()-1)
            with self.assertRaises(TimeoutError):
                ladder.check_identity(SimpleNamespace(), {}, {}, {}, time.monotonic()-1)

    def test_cli_finalization_timeout_records_immutability_unknown(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'inputs'; source.mkdir()
            args = ['--stage', 'reproduce', '--repo', str(root), '--training-root', str(source/'original'),
                    '--collection-report', str(source/'collection.json'), '--collection-sha256', ladder.COLLECTION_SHA,
                    '--seconds', '10', '--output', str(root/'run')]
            with patch.object(ladder, 'admit', return_value=(tiny(), {}, {}, {})), \
                    patch.object(ladder, 'audit', return_value={}), \
                    patch.object(ladder, 'run_stage', return_value={'status': 'passed'}), \
                    patch.object(ladder, 'check_identity', side_effect=TimeoutError('expired source verification')), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ladder.main(args), 0)
            report = json.loads((root/'run'/'report.json').read_text())
            self.assertEqual(report['status'], 'budget_exhausted')
            self.assertEqual(report['inputs_unchanged_after']['status'], 'incomplete')

    def test_cli_output_in_admitted_recording_refused_before_mkdir(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); raw = root/'raw-recording'; raw.mkdir()
            output = raw/'pollution'
            args = ['--stage', 'reproduce', '--repo', str(root), '--training-root', str(root/'inputs'/'original'),
                    '--collection-report', str(root/'inputs'/'collection.json'), '--collection-sha256', ladder.COLLECTION_SHA,
                    '--seconds', '10', '--output', str(output)]
            with patch.object(ladder, 'admit', return_value=(tiny(), {'sources': [{'path': str(raw)}]}, {}, {})), \
                    contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(ladder.main(args), 1)
            self.assertIn('Output overlaps immutable input owner', error.getvalue())
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
