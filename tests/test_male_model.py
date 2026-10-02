"""Tiny offline fixtures; opt-in Torch checks do not establish navigation competence."""
from collections import Counter
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import numpy as np
from palimpsest.records import RunWriter


ROOT = Path(__file__).resolve().parents[1]
GRAPH = ROOT / 'data/assets/malecns-metadata/reduced-neighborhood-v1b/graph.json'
MANIFEST = ROOT / 'data/manifests/malecns-reduced-neighborhood-v1.json'
CELL = ROOT.parent / 'memory-mechanics/upstream/fly-gym/models/connectome_rnn_model.py'


def graph_fixture():
    """Authored asymmetric graph; tests mechanics, not anatomical evidence."""
    ids = [3, 4, 5, 6, 7, 8, 12781, 556329]
    return {'dataset': 'male-cns:v1.0',
            'nodes': [{'bodyId': identifier, 'type': None if identifier == 3 else 'fixture'} for identifier in ids],
            'input_candidates': ids[:-2], 'endpoints': ids[-2:],
            'boundary': {'interpretation': 'synthetic test fixture'},
            'edges': [[3, 4, 1], [3, 6, 2], [4, 5, 3], [4, 12781, 4],
                      [5, 6, 5], [5, 8, 6], [6, 7, 7], [6, 556329, 8],
                      [7, 8, 9], [7, 3, 10], [8, 12781, 11], [8, 4, 12],
                      [12781, 556329, 13], [556329, 3, 14]]}


class MalePreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def teacher(self, seed=1, *, parent=None, completed=True):
        run = self.root / uuid.uuid4().hex
        writer = RunWriter(run / 'recording', dict(run_id=run.name, controller='teacher', profile='teacher',
            teacher_privileged=True, parent_run_id=parent, seed=seed, scenario='reproduction', texture='checker',
            observation_profile='two-rgb-eyes-contact-relative-goal-bearing-v1',
            sensor_order=['collision', 'collision_angle', 'wind_cos', 'wind_sin'], control_interval_seconds=.02))
        writer.event('episode_started', run_id=run.name, episode=0, episode_step=0, seed=seed,
            world={'arena': 7., 'pose': [0., 0., 0.], 'obstacles': [], 'goal': [3., 3., .5]})
        for tick in range(3):
            writer.tick(0, tick, cam_left=np.full((128, 128, 3), seed, dtype=np.uint8),
                cam_right=np.zeros((128, 128, 3), dtype=np.uint8), sensors=np.array([0., 0., 1., 0.]),
                action=np.array([1., seed * .1]), pose=np.array([tick * .1, 0., 0.]),
                next_pose=np.array([(tick + 1) * .1, 0., 0.]), reward=np.array(0.),
                simulation_time=np.array((tick + 1) * .02))
        if completed:
            writer.finish({})
        writer.close()
        return run

    def test_artificial_features_use_only_declared_channels_and_validate_units(self):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.male_model'), 'male model preparation is missing')
        from palimpsest.male_model import features
        row = {'cam_left': np.full((128, 128, 3), 255, dtype=np.uint8),
               'cam_right': np.zeros((128, 128, 3), dtype=np.uint8),
               'sensors': np.array([1., math.pi, 0., 1.])}
        value = features(row)
        self.assertEqual((value.shape, value.dtype), ((388,), np.float32))
        np.testing.assert_array_equal(value[:192], 1.)
        np.testing.assert_array_equal(value[192:384], 0.)
        np.testing.assert_allclose(value[-4:], [1., 1., 0., 1.])
        np.testing.assert_array_equal(value, features({**row, 'pose': [99, 99, 0], 'goal': [8, 8], 'privileged': 'ignored'}))
        for change in ({'cam_left': np.zeros((2, 2, 3), dtype=np.uint8)},
                       {'sensors': np.array([0., np.nan, 1., 0.])}, {'sensors': np.array([2., 0., 1., 0.])}):
            with self.assertRaises(ValueError):
                features({**row, **change})

    def test_fixture_graph_and_degree_control_are_fully_identified(self):
        from palimpsest.male_model import validate_graph, rewire, dense_weights, reachability
        graph = validate_graph(graph_fixture())
        self.assertEqual((len(graph['ids']), len(graph['edges']), len(graph['inputs'])), (8, 14, 6))
        self.assertEqual(graph['outputs'], [12781, 556329])
        self.assertEqual(graph['type_missing_ids'], [3])
        self.assertEqual(graph['type_labels'], [None, 'fixture'])
        self.assertEqual(graph['type_ids'], [0, 1, 1, 1, 1, 1, 1, 1])
        control, report = rewire(graph, 0)
        self.assertEqual(control, rewire(graph, 0)[0])
        self.assertNotEqual(control['edges'], graph['edges'])
        for index in (0, 1):
            self.assertEqual(Counter(edge[index] for edge in graph['edges']), Counter(edge[index] for edge in control['edges']))
        self.assertEqual(sorted(edge[2] for edge in graph['edges']), sorted(edge[2] for edge in control['edges']))
        self.assertTrue(all(pre != post for pre, post, _ in control['edges']))
        self.assertEqual(len({tuple(edge[:2]) for edge in control['edges']}), 14)
        self.assertEqual(report['successful_swaps'], 10 * 14)
        weights = dense_weights(graph)
        index = {identifier: i for i, identifier in enumerate(graph['ids'])}
        pre, post, count = graph['edges'][0]
        self.assertAlmostEqual(weights[index[post], index[pre]], count * graph['weight_scale'], places=7)
        self.assertEqual(weights[index[pre], index[post]], 0.)
        self.assertEqual(graph['weight_scale'], control['weight_scale'])
        paths = reachability(control)
        self.assertEqual(set(paths['reachable_input_ids']) | set(paths['unreachable_input_ids']), set(control['inputs']))
        self.assertEqual(reachability({'ids': [3, 12781, 556329], 'inputs': [3], 'outputs': [12781, 556329],
            'edges': [[3, 12781, 20]]})['by_output'], {'12781': [3], '556329': []})

    def test_pinned_actual_graph_when_fetched_asset_is_available(self):
        if not GRAPH.is_file():
            self.skipTest('optional fetched male graph is unavailable; fixture checks still run')
        from palimpsest.male_model import load_graph
        graph = load_graph(GRAPH, MANIFEST)
        self.assertEqual((len(graph['ids']), len(graph['edges']), len(graph['inputs'])), (138, 1647, 136))
        self.assertEqual(graph['outputs'], [12781, 556329])
        self.assertEqual(graph['type_missing_ids'], [])

    def test_graph_hash_and_invalid_topology_are_rejected(self):
        from palimpsest.male_model import load_graph, validate_graph
        broken = self.root / 'graph.json'
        broken.write_text(json.dumps(graph_fixture()))
        with self.assertRaisesRegex(ValueError, 'hash'):
            load_graph(broken, MANIFEST)
        raw = graph_fixture()
        raw['edges'].append(raw['edges'][0])
        with self.assertRaisesRegex(ValueError, 'edge'):
            validate_graph(raw)

    def test_split_preparation_is_numpy_only_and_binds_features_and_source_files(self):
        from palimpsest.male_model import prepare_splits
        paths = {'train': [self.teacher(1)], 'dev': [self.teacher(2)], 'held_out': [self.teacher(3)]}
        with patch.dict('sys.modules', {'torch': None}):
            data, report = prepare_splits(paths)
        self.assertEqual({key: len(value) for key, value in data.items()}, {'train': 1, 'dev': 1, 'held_out': 1})
        self.assertEqual(data['train'][0]['features'].shape, (3, 388))
        self.assertEqual(report['total_ticks'], 9)
        for split in paths:
            entry = report['splits'][split][0]
            self.assertEqual(entry['run_id'], paths[split][0].name)
            self.assertEqual(len(entry['feature_target_sha256']), 64)
            for source in entry['files']:
                self.assertEqual(source['sha256'], hashlib.sha256((paths[split][0] / source['path']).read_bytes()).hexdigest())

    def test_split_overlap_scene_reuse_branch_and_interruption_fail(self):
        from palimpsest.male_model import prepare_splits
        left, right, held = self.teacher(1), self.teacher(2), self.teacher(3)
        bad = [dict(train=[left], dev=[left], held_out=[held]),
               dict(train=[left], dev=[self.teacher(1)], held_out=[held]),
               dict(train=[left], dev=[self.teacher(2, parent=right.name)], held_out=[held]),
               dict(train=[left], dev=[self.teacher(2, completed=False)], held_out=[held])]
        for paths in bad:
            with self.assertRaises(ValueError):
                prepare_splits(paths)

    def test_source_changes_seed_disagreement_and_snapshot_budget_fail(self):
        from palimpsest import male_model
        paths = {'train': [self.teacher(1)], 'dev': [self.teacher(2)], 'held_out': [self.teacher(3)]}
        _, report = male_model.prepare_splits(paths)
        manifest_path = paths['train'][0] / 'recording/manifest.json'
        original = manifest_path.read_text()
        manifest_path.write_text(original + '\n')
        with self.assertRaisesRegex(ValueError, 'changed'):
            male_model.check_sources(report)
        manifest = json.loads(original)
        manifest['seed'] = 99
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'seed differ'):
            male_model.prepare_splits(paths)
        manifest_path.write_text(original)
        snapshots = paths['train'][0] / 'snapshots'
        snapshots.mkdir()
        (snapshots / 'initial.snp').write_bytes(b'x' * 1024**2)
        with patch.object(male_model, 'MAX_RUN_BYTES', 1024**2), self.assertRaisesRegex(ValueError, 'snapshots exceed'):
            male_model.prepare_splits(paths)

    def test_initial_protocol_freezes_scenes_and_accepts_natural_endings_without_padding(self):
        spec = importlib.util.spec_from_file_location('train_male_reduced', ROOT / 'scripts/train_male_reduced.py')
        trainer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(trainer)
        report = {'splits': {split: [{'episodes': [{'episode': 0, 'seed': seed, 'ticks': 150}],
            'scenario': 'reproduction', 'texture': 'checker', 'final_phase': 'paused', 'last_outcome': None} for seed in seeds]
            for split, seeds in trainer.INITIAL_PROTOCOL['scene_seeds'].items()}}
        trainer.validate_initial_split(report)
        report['splits']['dev'][0].update(final_phase='terminated', last_outcome={'reason': 'goal'})
        report['splits']['dev'][0]['episodes'][0]['ticks'] = 7
        trainer.validate_initial_split(report)
        report['splits']['train'][0]['episodes'][0]['ticks'] = 31
        with self.assertRaisesRegex(ValueError, 'insufficient data'):
            trainer.validate_initial_split(report)
        report['splits']['train'][0]['episodes'][0].update(ticks=150, seed=112)
        with self.assertRaisesRegex(ValueError, 'scene seeds'):
            trainer.validate_initial_split(report)

    @unittest.skipUnless(os.environ.get('PALIMPSEST_MALE_TORCH_CHECKS') == '1', 'Torch execution requires the released model window')
    def test_cpu_cell_forward_gradients_resets_and_guards(self):
        if not GRAPH.is_file() or not CELL.is_file():
            self.skipTest('optional fetched graph and pinned upstream cell are required')
        import torch
        from palimpsest.male_model import load_graph, make_model
        graph = load_graph(GRAPH, MANIFEST)
        first, second = make_model(graph, CELL, 7), make_model(graph, CELL, 7)
        x = torch.ones(4, 1, 388)
        h, actions = first(x, first.reset())
        _, repeat = second(x, second.reset())
        self.assertTrue(torch.equal(actions, repeat))
        self.assertTrue(torch.equal(actions, first(x, first.reset())[1]))
        self.assertEqual(tuple(h.shape), (1, 138))
        self.assertTrue(torch.all(torch.abs(actions[..., 0]) <= 3))
        self.assertTrue(torch.all(torch.abs(actions[..., 1]) <= math.pi))
        actions.square().sum().backward()
        self.assertIsNone(first.cell.W_values.grad)
        self.assertGreater(float(first.encoder[0].weight.grad.abs().sum()), 0.)
        self.assertTrue(all(torch.isfinite(p.grad).all() for p in first.parameters() if p.grad is not None))
        with self.assertRaises(ValueError):
            first(torch.full_like(x, float('nan')), first.reset())
        with torch.no_grad():
            first.cell.readout_head[-1].bias.fill_(float('inf'))
        with self.assertRaises(ValueError):
            first(x, first.reset())


if __name__ == '__main__':
    unittest.main()
