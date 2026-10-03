"""Synthetic admission/binding checks; no real corpus, Torch or native runtime."""
import copy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from palimpsest import artifacts, male_model, male_policy
from palimpsest import male_navigation_research as nav
from test_male_model import graph_fixture

ROOT = Path(__file__).resolve().parents[1]


class AdmissionFixture(unittest.TestCase):
    def write(self, path, value):
        raw = value if isinstance(value, bytes) else male_model.canonical(value)
        path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
        return {'path': str(path), 'sha256': male_policy._sha(raw), 'size_bytes': len(raw)}

    def setUp(self):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.producer = self.root/'producer'; self.assets = self.root/'assets'
        # The tracked index supplies only the exact roster/schema; all external paths
        # and payloads are replaced by authored temporary bytes before any reader call.
        self.index = json.loads((ROOT/nav.INDEX_PATH).read_text())
        self.index['producer_root'] = 'producer'
        self.plan = json.loads((ROOT/nav.PROTOCOL_PATH).read_text())
        pin = self.write(self.root/nav.PROTOCOL_PATH, self.plan)
        self.addCleanup(patch.stopall)
        patch.object(nav, 'PROTOCOL_SHA256', pin['sha256']).start()
        self.index['study_protocol'] = pin
        code = self.index['training_source_code']
        for group in ('named_reader_sources', 'added_sources'):
            for name in code[group]:
                pin = self.write(self.producer/name, ('synthetic source '+name).encode())
                code[group][name] = pin['sha256']
        code['lock_sha256'] = self.write(self.producer/'uv.lock', b'fixture lock')['sha256']
        for name in ('src/palimpsest/male_model.py', 'src/palimpsest/male_policy.py'):
            self.write(self.root/name, (self.producer/name).read_bytes())
        graph_source = self.write(self.assets/'male-reduced-v1/source-graph.json', graph_fixture())
        graph_manifest = self.write(self.root/'data/manifests/malecns-reduced-neighborhood-v1.json', b'fixture graph manifest')
        cell = self.write(self.root/'upstream/fly-gym/models/connectome_rnn_model.py', b'fixture cell')
        self.index['model_inputs'] = {graph_source['path']: graph_source['sha256'],
            str(self.producer/'data/manifests/malecns-reduced-neighborhood-v1.json'): graph_manifest['sha256'],
            str(self.producer/'upstream/fly-gym/models/connectome_rnn_model.py'): cell['sha256']}
        self.graph = male_model.validate_graph(graph_fixture())
        self.graph.update(source_graph_sha256=graph_source['sha256'], graph_manifest_sha256=graph_manifest['sha256'],
                          topology_sha256=male_model.digest(self.graph['edges']))
        self.graph_loader = patch.object(male_model, 'load_graph', return_value=self.graph).start()
        self.data = {'status': 'prepared-navigation-advice-research-only', 'counts': self.plan['data_contract']['counts'],
            'current_reader_sources': code['named_reader_sources'], 'feature_protocol': male_model.FEATURE_PROTOCOL,
            'labels': {'old': 'unchanged executed targets', 'new': 'nav_advice_action'},
            'arms': {arm: {'held_out': []} for arm in ('old', 'augmented')},
            'historical_reader': {'head': 'fixture historical reader'}}
        self.index['data_manifest'] = self.write(self.producer/'data.json', self.data)
        self.rows = []; self.models = []; self.pairs = []; self.audited = []
        for seed in nav.PAIR_SEEDS:
            self.make_pair(seed)
        self.index.update(pairs=self.pairs, models=self.models)
        cleanup = {'sampler_stopped': True, 'sample_errors': [], 'forced_signals': [],
                   'survivors': [], 'conflicting_owned_identities': []}
        self.supervision = {'status': 'completed', 'returncode': 0, 'elapsed_seconds': 5.}
        self.terminal = {'status': 'passed-navigation-research-training', 'head': nav.TRAINING_COMMIT,
            'inventories_unchanged': True, 'completed_pair_content_unchanged': True, 'controls_unchanged': True,
            'wall_seconds': 15., 'pairs': self.rows, 'cleanup': cleanup}
        self.index['before_inventory'] = self.write(self.producer/'before.json', {'fixture': 'bounded inventory'})
        self.index['after_inventory'] = self.write(self.producer/'after.json', {'fixture': 'bounded inventory'})
        self.index['outer_after_inventory'] = self.write(self.producer/'outer-after.json', {'fixture': 'outer inventory'})
        self.terminal.update(before_inventory_sha256=self.index['before_inventory']['sha256'],
                             after_inventory_sha256=self.index['after_inventory']['sha256'])
        self.index['training_terminal'] = self.write(self.producer/'terminal.json', self.terminal)
        self.index['training_supervisor'] = self.write(self.producer/'supervisor.json', self.supervision)
        self.enclosing = {'status': self.terminal['status'], 'terminal_sha256': self.index['training_terminal']['sha256'],
            'outer_after_sha256': self.index['outer_after_inventory']['sha256'], 'outer_inventory_unchanged': True,
            'controls_unchanged': True, 'wall_seconds_before_publication': 16., 'supervision': self.supervision, 'outer_cleanup': cleanup}
        self.index['training_enclosing'] = self.write(self.producer/'enclosing.json', self.enclosing)
        self.index['training_end_session'] = self.write(self.producer/'end.json', {'status': self.terminal['status'],
            'source_head': nav.TRAINING_COMMIT, 'exec_exit_code': 0, 'exec_session_fully_drained': True})
        self.audit = {'status': 'passed', 'source': nav.TRAINING_COMMIT, 'models': self.audited,
            'terminal_sha256': self.index['training_terminal']['sha256'], 'enclosing_sha256': self.index['training_enclosing']['sha256'],
            'end_session_sha256': self.index['training_end_session']['sha256']}
        self.index['independent_audit'] = self.write(self.producer/'audit.json', self.audit)
        self.index['independent_auditor'] = self.write(self.producer/'audit.py', b'fixture retained auditor')
        self.publish_index()

    def publish_index(self):
        pin = self.write(self.root/nav.INDEX_PATH, self.index)
        patch.object(nav, 'INDEX_SHA256', pin['sha256']).start()

    def make_pair(self, seed):
        directory = f'bundles/seed-{seed}'; base = self.producer/directory
        expected = {arm: {**self.plan['training_inherited'], 'training_seed': seed, 'arm': arm, 'graph_variant': 'original',
            'data_manifest_sha256': self.index['data_manifest']['sha256'], 'research_protocol_sha256': nav.PROTOCOL_SHA256,
            'train_rows': 2117 if arm == 'old-corpus' else 7197, 'dev_rows': 1228, 'wall_budget_seconds': 600,
            'output_limit_bytes': 64*1024**2, 'qualification_claims': []} for arm in nav.ARMS}
        training = {'seed': seed, 'training': expected, 'source_code': self.index['training_source_code'],
            'model_inputs': self.index['model_inputs'], 'runtime': self.index['runtime'], 'feature_protocol': male_model.FEATURE_PROTOCOL,
            'admitted_manifest_sha256': self.index['data_manifest']['sha256'], 'study_protocol_sha256': nav.PROTOCOL_SHA256}
        ledger = {}
        for name, value in (('protocol.json', training), ('original-graph.json', self.graph)):
            ledger[name] = {k: v for k, v in self.write(base/name, value).items() if k != 'path'}
        models = {}
        for arm in nav.ARMS:
            stream = io.BytesIO()
            with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_STORED) as archive:
                archive.writestr('archive/data.pkl', f'authored unpickled fixture {seed} {arm}'.encode())
            ledger[arm+'.pt'] = {k: v for k, v in self.write(base/(arm+'.pt'), stream.getvalue()).items() if k != 'path'}
            history = [{'epoch': epoch, 'train_ticks': expected[arm]['train_rows'], 'train_loss': .5,
                'dev': {'ticks': 1228, 'loss': .1 if epoch in (2, 3) else .2, 'velocity_mae': .1,
                        'wrapped_heading_mae_radians': .1}} for epoch in range(1, 21)]
            models[arm] = {'status': 'completed', 'selected_epoch': 2, 'history': history,
                'checkpoint': dict(path=arm+'.pt', **ledger[arm+'.pt']), 'graph_file': 'original-graph.json', 'graph_variant': 'original'}
        report = {'status': 'completed-navigation-research-training', 'training_attempted': True, 'training_completed': True,
            'held_out_status': 'locked_unopened', 'held_out_used_for_selection': False, 'qualification_claims': [],
            'data_manifest_sha256': self.index['data_manifest']['sha256'], 'study_protocol_sha256': nav.PROTOCOL_SHA256,
            'protocol_sha256': male_model.digest(training), 'models': models, 'runtime': self.index['runtime'],
            'files': [dict(path=name, **value) for name, value in ledger.items()]}
        ledger['report.json'] = {k: v for k, v in self.write(base/'report.json', report).items() if k != 'path'}
        before = {'status': 'obtained-after-training-inputs', 'errors': [], 'code': self.index['training_source_code'],
            'model_inputs': self.index['model_inputs'], 'protocol_sha256': nav.PROTOCOL_SHA256,
            'historical': self.data['historical_reader'], 'sources': [{} for _ in range(26)]}
        for name in nav.AFTER_FILES:
            ledger[name] = {k: v for k, v in self.write(base/name, before).items() if k != 'path'}
        pair = {'training_seed': seed, 'directory': directory, **{key: dict(path=directory+'/'+name, **ledger[name])
            for key, name in (('report', 'report.json'), ('protocol', 'protocol.json'), ('graph', 'original-graph.json'))}}
        self.pairs.append(pair)
        self.rows.append({'training_seed': seed, 'status': 'completed', 'supervision': {'status': 'completed', 'returncode': 0, 'elapsed_seconds': 5.},
            'retained_files': ledger, 'models': models, 'report.json_sha256': ledger['report.json']['sha256'], 'retained_status': report['status']})
        for arm in nav.ARMS:
            self.models.append({**pair, 'arm': arm, 'graph_variant': 'original', 'training': expected[arm],
                'feature_protocol': male_model.FEATURE_PROTOCOL, 'runtime': self.index['runtime'], 'cell_sha256': male_model.CELL_SHA256,
                'selected_epoch': 2, 'selected_recorded_dev': models[arm]['history'][1]['dev'],
                'checkpoint': dict(path=directory+'/'+arm+'.pt', **ledger[arm+'.pt']),
                **{key: self.graph[key] for key in ('topology_sha256', 'ordered_ids_sha256', 'source_graph_sha256')}})
            self.audited.append({'seed': seed, 'arm': arm, 'graph_buffers_and_frozen_weights_exact': True,
                'checkpoint_sha256': ledger[arm+'.pt']['sha256'], 'report_sha256': ledger['report.json']['sha256'],
                'protocol_sha256': report['protocol_sha256'], 'graph_sha256': male_model.digest(self.graph), 'selected_epoch': 2})

    def admit(self):
        index = nav._index(self.root, self.root/nav.INDEX_PATH, nav.INDEX_SHA256)
        return nav._admit(self.root, self.assets, index)

    def test_all_six_are_admitted_with_distinct_arms_and_unchanged_identity_schema(self):
        values = self.admit()
        self.assertEqual(list(values), [(seed, arm) for seed in nav.PAIR_SEEDS for arm in nav.ARMS])
        self.assertEqual(len({v[2]['checkpoint_sha256'] for v in values.values()}), 6)
        self.assertTrue(all(v[2]['variant'] == 'original' for v in values.values()))
        with patch.object(nav, 'runtime_identity', return_value={k: self.index['runtime'][k] for k in ('python', 'numpy', 'torch_distribution')}):
            identity, args = nav.resolve(self.root, self.assets, self.root/nav.INDEX_PATH, nav.INDEX_SHA256, 11, 'augmented', 'male-original')
        self.assertEqual(set(identity), {'controller', 'variant', 'profile', *male_policy.IDENTITY_HASHES})
        self.assertEqual(args['training_seed'], 11); self.assertEqual(args['arm'], 'augmented')

    def test_incomplete_index_and_cross_arm_checkpoint_refuse(self):
        self.index['models'].pop(); self.publish_index()
        with self.assertRaisesRegex(ValueError, 'All six'): self.admit()
        self.index['models'] = copy.deepcopy(self.models)
        # models aliases the index list, so rebuild the missing sixth from its existing pair metadata.
        self.index['models'].append(copy.deepcopy(self.index['models'][-1]) | {'arm': 'augmented'})
        self.publish_index()
        with self.assertRaisesRegex(ValueError, 'Cross-arm'): self.admit()

    def test_any_other_pair_drift_refuses_even_when_first_model_requested(self):
        path = self.producer/self.models[-1]['checkpoint']['path']
        path.write_bytes(path.read_bytes()+b'changed')
        with self.assertRaisesRegex(ValueError, 'artifact differs'): self.admit()

    def test_historical_producer_pin_drift_refuses_without_head_requirement(self):
        name = next(iter(self.index['training_source_code']['named_reader_sources']))
        (self.producer/name).write_bytes(b'drift')
        with self.assertRaisesRegex(ValueError, 'artifact differs'): self.admit()

    def test_graph_and_failed_cleanup_refuse(self):
        changed = copy.deepcopy(self.graph); changed['edges'][0][2] += 1
        with patch.object(male_model, 'load_graph', return_value=changed):
            with self.assertRaisesRegex(ValueError, 'original graph'): self.admit()
        self.terminal['cleanup']['forced_signals'] = [15]
        self.index['training_terminal'] = self.write(self.producer/'terminal.json', self.terminal)
        self.enclosing['terminal_sha256'] = self.index['training_terminal']['sha256']
        self.index['training_enclosing'] = self.write(self.producer/'enclosing.json', self.enclosing)
        self.audit.update(terminal_sha256=self.index['training_terminal']['sha256'], enclosing_sha256=self.index['training_enclosing']['sha256'])
        self.index['independent_audit'] = self.write(self.producer/'audit.json', self.audit); self.publish_index()
        with self.assertRaisesRegex(ValueError, 'cleanup'): self.admit()

    def test_earliest_minimum_epoch_counts_and_finite_supervision(self):
        model = copy.deepcopy(self.rows[0]['models']['old-corpus'])
        nav._history(model, 'old-corpus')
        model['selected_epoch'] = 3
        with self.assertRaisesRegex(ValueError, 'Earliest'): nav._history(model, 'old-corpus')
        for value in (True, float('nan'), float('inf'), 660.001, -1):
            with self.assertRaises(ValueError): nav._supervision(self.supervision | {'elapsed_seconds': value}, 660)
        model['selected_epoch'] = 2; model['history'][0]['train_ticks'] = 7197
        with self.assertRaisesRegex(ValueError, 'counts'): nav._history(model, 'old-corpus')

    def test_expected_identity_runtime_and_bad_controller_reject_before_model(self):
        runtime = {k: self.index['runtime'][k] for k in ('python', 'numpy', 'torch_distribution')}
        with patch.object(nav, 'runtime_identity', return_value=runtime):
            identity, _ = nav.resolve(self.root, self.assets, self.root/nav.INDEX_PATH, nav.INDEX_SHA256, 10, 'old-corpus', 'male-original')
            wrong = identity | {'checkpoint_sha256': '0'*64}
            with self.assertRaisesRegex(ValueError, 'Expected'): nav.resolve(self.root, self.assets, self.root/nav.INDEX_PATH, nav.INDEX_SHA256, 10, 'old-corpus', 'male-original', wrong)
        with patch.object(nav, '_admit') as admission, patch.object(nav, 'runtime_identity', return_value=runtime | {'python': 'wrong'}):
            with self.assertRaisesRegex(ValueError, 'runtime'): nav.resolve(self.root, self.assets, self.root/nav.INDEX_PATH, nav.INDEX_SHA256, 10, 'old-corpus', 'male-original')
            admission.assert_not_called()
        for seed, arm, controller in ((True, 'old-corpus', 'male-original'), (10., 'old-corpus', 'male-original'),
                (10, 'unknown', 'male-original'), (10, 'augmented', 'male-control')):
            with self.assertRaises(ValueError): nav._choice(seed, arm, controller)


class BindingTests(unittest.TestCase):
    def test_profile_expected_identity_and_scene_seed_are_separate(self):
        binding = nav.Binding(ROOT/nav.INDEX_PATH, nav.INDEX_SHA256, 11, 'augmented')
        with patch.object(nav, 'resolve') as resolve:
            for values in (('cuda', 'reproduction', 'checker', {}), ('cpu', 'reproduction', 'realistic', {}),
                           ('cpu', 'homing', 'checker', {}), ('cpu', 'reproduction', 'checker', None)):
                with self.assertRaises(ValueError): binding.resolve(ROOT, ROOT, 'male-original', *values)
            resolve.assert_not_called()
        with patch.object(nav, 'load_policy', return_value='fixture') as load:
            self.assertEqual(binding.load_policy({'training_seed': 11, 'arm': 'augmented'}, 3110), 'fixture')
            load.assert_called_once_with(training_seed=11, arm='augmented', seed=3110)
        self.assertEqual(binding.provenance()['arm'], 'augmented')

    def test_engine_exact_type_and_default_resolver_preserved_before_owner_creation(self):
        from palimpsest.engine import Engine
        binding = nav.Binding(ROOT/nav.INDEX_PATH, nav.INDEX_SHA256, 10, 'old-corpus')
        class NotExact(nav.Binding): pass
        with patch.object(nav.Binding, 'resolve', side_effect=RuntimeError('admitted binding boundary')) as resolve, \
                patch('palimpsest.records.RunWriter') as writer:
            with self.assertRaisesRegex(RuntimeError, 'admitted binding boundary'):
                Engine.open(ROOT, ROOT, ROOT/'unused', controller='male-original', research_binding=binding, expected_policy_identity={})
            self.assertEqual(resolve.call_count, 1); writer.assert_not_called()
            with self.assertRaisesRegex(ValueError, 'unsupported trusted'):
                Engine.open(ROOT, ROOT, ROOT/'unused', controller='male-original', research_binding=NotExact(binding.manifest, binding.manifest_sha256, 10, 'old-corpus'))
            for kw in ({'restore_snapshot': {}}, {'replace_controller': True}, {'memory_u': {}}):
                with self.assertRaises(ValueError): Engine.open(ROOT, ROOT, ROOT/'unused', controller='male-original', research_binding=binding, **kw)
        with patch.object(male_policy, 'resolve_profile', side_effect=RuntimeError('default boundary')) as original:
            with self.assertRaisesRegex(RuntimeError, 'default boundary'):
                Engine.open(ROOT, ROOT, ROOT/'unused', controller='male-original', expected_policy_identity={'fixture': 'identity'})
            original.assert_called_once_with(ROOT.resolve(), ROOT.resolve(), 'male-original', {'fixture': 'identity'})


if __name__ == '__main__': unittest.main()
