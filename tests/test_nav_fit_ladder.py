import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import nav_fit_ladder as ladder


def episode(run='a', ticks=40, scene=None, owner=None):
    return {'run_id': run, 'episode': 0, 'features': np.zeros((ticks, 388), np.float32),
            'targets': np.zeros((ticks, 2), np.float32), 'scene_seed': scene, 'learner_seed': owner}


class NavigationLadderTests(unittest.TestCase):
    def test_groups_keep_all_owners_and_refuse_missing_or_reserved(self):
        new = [episode(f'{scene}-{owner}', scene=scene, owner=owner)
               for scene in (3100, 3101, 3102, 3103) for owner in (10, 11, 12)]
        groups = ladder.grouped_split([episode('old')], [episode('dev')], new)
        self.assertEqual({x['scene_seed'] for x in groups['advice_dev']}, {3102, 3103})
        self.assertEqual(len(groups['train']), 7)
        with self.assertRaises(ValueError): ladder.grouped_split([], [], new[:-1])
        with self.assertRaises(ValueError): ladder.grouped_split([], [], [*new, episode('reserved', scene=3120, owner=10)])

    def test_normalization_is_training_only_constant_sigma_one_binary_unchanged(self):
        a = episode(); a['features'][:, 0] = np.arange(40); a['features'][:, 384] = 1
        mean, scale = ladder.statistics([a])
        self.assertEqual(mean[0], 19.5)
        self.assertEqual(scale[1], 1)
        self.assertEqual((mean[384], scale[384]), (0, 1))

    def test_recovery_alignment_preaction_target_negative_only(self):
        ep = episode(ticks=5)
        ep['targets'][:, 0] = [-.35, -.35, 0, 0, 0]
        ep['features'][:, 384] = [1, 1, 0, 0, 0]
        ep['recovery'] = np.array([True, True, True, False, False])
        ep['onset'] = np.array([True, False, False, False, False])
        actions = np.zeros((5, 2), np.float32); actions[:, 0] = [-1, 1, -1, -1, 1]
        metrics = ladder.panel_metrics([ep], [actions], np.zeros(2, np.float32))
        self.assertEqual(metrics['onset_negative_count'], 1)
        self.assertEqual(metrics['onset_reverse_recall'], 1)
        self.assertEqual(metrics['false_reverse_count'], 1)
        self.assertEqual(metrics['false_reverse_denominator'], 2)
        self.assertEqual(metrics['false_reverse_rate'], .5)
        ep.pop('recovery')
        self.assertIsNone(ladder.panel_metrics([ep], [actions], np.zeros(2, np.float32))['false_reverse_rate'])

    def test_reproduction_refuses_loss_and_response_disagreement(self):
        old = {'selected_epoch': 1, 'history': [{'epoch': 1, 'train_loss': .2, 'dev': {'loss': .3}}]}
        ladder.compare_reproduction(old, old, [np.zeros((1, 2))], [np.zeros((1, 2))])
        new = json.loads(json.dumps(old)); new['history'][0]['train_loss'] += .00001
        with self.assertRaises(ValueError): ladder.compare_reproduction(new, old, [], [])
        with self.assertRaises(ValueError): ladder.compare_reproduction(old, old, [np.ones((1, 2))], [np.zeros((1, 2))])

    def test_receipt_requires_all_six_and_own_binding(self):
        with self.assertRaises(ValueError): ladder.require_reproduction({'status': 'passed', 'models': []}, {})
        receipt = {'stage': 'reproduce', 'status': 'passed', 'binding': {}, 'inputs_unchanged_after': True,
                   'models': [{'seed': s, 'arm': a, 'status': 'passed', 'max_absolute_difference': 0}
                              for s in ladder.SEEDS for a in ladder.ARMS]}
        ladder.require_reproduction(receipt, {})
        receipt['models'][0]['max_absolute_difference'] = float('nan')
        with self.assertRaises(ValueError): ladder.require_reproduction(receipt, {})

    def test_rule_recomputed_from_wind_pair_not_contact_angle(self):
        ep = episode(ticks=3)
        ep['features'][:, 385] = 1
        ep['features'][:, 386] = 1
        ep['targets'][:, 0] = .7
        m = ladder.panel_metrics([ep], [ep['targets'].copy()], np.zeros(2, np.float32))
        self.assertAlmostEqual(m['rule_loss'], 0)
        self.assertFalse(ladder.eligible({'teacher_dev': m, 'advice_dev': m}))

    def test_tiny_actual_upstream_graph_arm_initialization_and_injection(self):
        import torch
        from palimpsest.male_model import make_model
        cell = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/male-navigation-training-v2/upstream/fly-gym/models/connectome_rnn_model.py')
        if not cell.exists(): self.skipTest('Pinned upstream source unavailable')
        graph = {'ids': [1, 2, 12781, 556329], 'inputs': [1, 2], 'outputs': [12781, 556329],
                 'edges': [[1, 12781, 1], [2, 556329, 2]], 'weight_scale': .45,
                 'type_ids': [0, 0, 0, 0], 'type_labels': ['type']}
        control = {**graph, 'edges': [[1, 556329, 1], [2, 12781, 2]]}
        mean, scale = ladder.statistics([episode()])
        a = ladder.make_probe('conditioned', graph, cell, 10, mean, scale, maker=make_model)
        b = ladder.make_probe('conditioned', control, cell, 10, mean, scale, maker=make_model)
        self.assertEqual(sum(p.numel() for p in a.parameters()), sum(p.numel() for p in b.parameters()))
        for (name, p), (_, q) in zip(a.named_parameters(), b.named_parameters(), strict=True):
            if not name.endswith('W_values'): self.assertTrue(torch.equal(p, q), name)
        injection = ladder.make_probe('injection', graph, cell, 10, mean, scale, maker=make_model)
        self.assertEqual(injection.cell.input_nodes.tolist(), [0, 1, 2, 3])
        h, actions = injection(torch.zeros((4, 1, 388)), injection.reset())
        self.assertEqual(tuple(actions.shape), (4, 1, 2)); self.assertTrue(torch.isfinite(h).all())

    def test_training_schedule_carries_within_episode_resets_at_start_equal_budget(self):
        import torch
        class Tiny(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.p = torch.nn.Parameter(torch.tensor(.1)); self.trace = []
            def reset(self): return torch.zeros((1, 1), dtype=torch.float32)
            def forward(self, x, h):
                if self.training: self.trace.append((len(x), float(h.item()), h.requires_grad))
                actions = self.p.expand(len(x), 1, 2)
                return h+1, actions
        def loss(a, y): return (a-y).square().mean(-1)
        panels = {'train': [episode('a', 40), episode('b', 40)],
                  'teacher_dev': [episode('d', 4)], 'advice_dev': [episode('e', 4)]}
        a, b = Tiny(), Tiny()
        ra, _ = ladder.fit_probe(a, panels, 10, time.monotonic()+10, SimpleNamespace(loss_for=loss), updates=7)
        rb, _ = ladder.fit_probe(b, panels, 10, time.monotonic()+10, SimpleNamespace(loss_for=loss), updates=7)
        self.assertEqual(ra['updates'], rb['updates']); self.assertEqual(ra['updates'], 7)
        self.assertEqual(ra['schedule_sha256'], rb['schedule_sha256'])
        self.assertEqual(a.trace, b.trace)
        self.assertEqual([x[1] for x in a.trace], [0, 1, 0, 1, 0, 1, 0])
        self.assertFalse(any(x[2] for x in a.trace))

    def test_stage_timeout_retains_exact_attempted_and_unattempted_roster(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'producer'; source.mkdir()
            args = SimpleNamespace(stage='reproduce', seconds=20, historical_root=source,
                historical_bundles=source/'bundles', reproduction_receipt=None, output=root/'out')
            trainer = SimpleNamespace(ROOT=source, protocol=lambda: {'immutable_prerequisites': {}},
                pinned_documents=lambda p, deadline: {'data_manifest': {'historical_reader': {'root': str(source)},
                    'old_sources': [], 'new_sources': [], 'input_documents': {}}}, check_context=lambda *a: None)
            reduced = SimpleNamespace(fit=lambda *a: (_ for _ in ()).throw(TimeoutError('synthetic deadline')))
            context = {x: {} for x in ('code', 'historical', 'documents', 'source_files', 'model_inputs')}
            protocols = {s: {'training': {a: {} for a in ladder.ARMS}} for s in ladder.SEEDS}
            actual_output = ladder.Output
            with patch.object(ladder, 'historical_binding', return_value=({'files': {}}, protocols, {})), \
                 patch.object(ladder, 'load_historical', return_value=(trainer, reduced)), \
                 patch.object(ladder, 'prepare_historical', return_value=({a: {} for a in ladder.ARMS}, {}, context, None)), \
                 patch.object(ladder, 'cpu_runtime', return_value={}), \
                 patch.object(ladder, 'Output', side_effect=lambda p, inputs: actual_output(p, inputs, min_free=0)):
                with self.assertRaises(TimeoutError): ladder.run(args, ['synthetic'])
            report = json.loads((root/'out/report.json').read_text())
            self.assertEqual(report['status'], 'incomplete')
            self.assertEqual([x['status'] for x in report['models']], ['incomplete']+['unattempted']*5)
            self.assertEqual(report['qualification_claims'], [])

    def test_schedule_equal_across_graphs_consecutive_windows(self):
        eps = [episode('a', 65), episode('b', 40)]
        a = list(ladder.windows(eps, 10, 11)); b = list(ladder.windows(eps, 10, 11))
        self.assertEqual(a, b)
        for i, (_, index, start, stop) in enumerate(a):
            self.assertLessEqual(stop-start, 32)
            if start: self.assertEqual(a[i-1][1], index); self.assertEqual(a[i-1][3], start)

    def test_output_guard_fresh_nonoverlap_and_caps(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root/'source'; source.mkdir()
            with self.assertRaises(ValueError): ladder.guard_output(source/'out', [source])
            with self.assertRaises(ValueError): ladder.guard_output(source, [])
            out = ladder.Output(root/'out', [source], max_bytes=4, min_free=0)
            out.write('a', b'1234')
            with self.assertRaises(ValueError): out.write('b', b'1')
            with self.assertRaises(ValueError): out.write('../c', b'')
            with self.assertRaises(TimeoutError): ladder.check_deadline(time.monotonic()-1)

    def test_tiny_gru_hidden_carry_and_reset_finite_guard(self):
        import torch
        torch.set_num_threads(1)
        mean, scale = ladder.statistics([episode()])
        model = ladder.make_probe('gru', None, None, 10, mean, scale)
        x = torch.zeros((32, 1, 388), dtype=torch.float32)
        h, a = model(x, model.reset())
        h2, _ = model(x, h.detach())
        h0, a0 = model(x, model.reset())
        self.assertTrue(torch.equal(h, h0)); self.assertTrue(torch.equal(a, a0))
        self.assertFalse(torch.equal(h, h2))
        x[0, 0, 0] = float('nan')
        with self.assertRaises(ValueError): model(x, h)
        with self.assertRaises(ValueError): model(torch.zeros((33, 1, 388)), h)
        with self.assertRaises(ValueError): model(torch.zeros((4, 1, 388), dtype=torch.float64), h)


if __name__ == '__main__': unittest.main()
