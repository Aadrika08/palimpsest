"""Pure fixed-pair/data/publication checks; no real fit, corpus or writer lease."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import train_male_navigation_v2 as trainer
import train_male_reduced as fitter
import train_male_recovery as publication
import prepare_male_recovery_data as old


def history(arm):
    count = 2117 if arm == 'old-corpus' else 7197
    return {'selected_epoch': 3, 'history': [{'epoch': i, 'train_ticks': count,
        'train_loss': .1, 'dev': {'ticks': 1228, 'loss': .05 if i in (3, 4) else .1,
        'velocity_mae': .1, 'wrapped_heading_mae_radians': .1}} for i in range(1, 21)]}


class FakeBudget:
    """One fixture-local context; never calls real StorageBudget.lock."""
    held = False
    def __init__(self, *args, **kwargs): pass
    def check(self, *args, **kwargs): return None
    def lock(self): return self
    def __enter__(self): type(self).held = True; return self
    def __exit__(self, *args): type(self).held = False


class NavigationTraining(unittest.TestCase):
    def test_fixed_original_pair_reuses_helpers_and_settings(self):
        for name in ('fit', 'evaluate', 'make_model'):
            self.assertIs(getattr(trainer, name), getattr(fitter, name))
        for name in ('write_artifact', 'stage_report', 'publish_report'):
            self.assertIs(getattr(trainer, name), getattr(publication, name))
        self.assertFalse(hasattr(trainer, 'rewire'))
        for seed in (10, 11, 12):
            for arm in trainer.ARMS:
                p = trainer.fixed_training(seed, arm)
                self.assertEqual((p['training_seed'], p['graph_variant'], p['epochs'], p['window']), (seed, 'original', 20, 32))
                self.assertEqual(p['train_rows'], 2117 if arm == 'old-corpus' else 7197)
                self.assertEqual((p['dev_rows'], p['optimizer'], p['learning_rate'], p['gradient_norm_cap']), (1228, 'Adam', .001, 1.))
        for seed, arm in ((True, 'old-corpus'), (13, 'augmented'), (10, 'degree_rewired')):
            with self.assertRaises(ValueError): trainer.fixed_training(seed, arm)

    def test_all_epochs_counts_finite_losses_and_earliest_tie(self):
        for arm in trainer.ARMS:
            trainer.validate_fit(history(arm), arm)
            for mutation in ('count', 'dev', 'tie', 'epoch', 'nan'):
                value = history(arm)
                if mutation == 'count': value['history'][0]['train_ticks'] = 2117 if arm == 'augmented' else 7197
                if mutation == 'dev': value['history'][0]['dev']['ticks'] = True
                if mutation == 'tie': value['selected_epoch'] = 4
                if mutation == 'epoch': value['history'][0]['epoch'] = True
                if mutation == 'nan': value['history'][0]['train_loss'] = float('nan')
                with self.assertRaises(ValueError): trainer.validate_fit(value, arm)

    def test_prerequisite_markdown_is_bound_as_bytes_not_parsed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); md = root/'report.md'; md.write_text('# not JSON\n')
            manifest = root/'manifest.json'; manifest.write_text('{"fixture":true}')
            def pin(path): return {'path': str(path), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            p = {'immutable_prerequisites': {'evidence_report': pin(md), 'data_manifest': pin(manifest)}}
            value = trainer.pinned_documents(p)
            self.assertEqual(value['data_manifest'], {'fixture': True})
            self.assertEqual(value['evidence_report']['sha256'], p['immutable_prerequisites']['evidence_report']['sha256'])
            md.write_text('# changed\n')
            with self.assertRaises(ValueError): trainer.pinned_documents(p)

    def test_named_roster_ignores_added_files_but_refuses_lock_or_reader_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'src').mkdir(); (root/'scripts').mkdir(); (root/'tests').mkdir()
            expected = {}
            for i in range(95):
                n = f'src/frozen{i:03d}.py'; (root/n).write_bytes(str(i).encode())
                expected[n] = hashlib.sha256((root/n).read_bytes()).hexdigest()
            own = root/'scripts/train_male_navigation_v2.py'; own.write_bytes(b'own')
            (root/'tests/test_train_male_navigation_v2.py').write_bytes(b'fixture')
            (root/'scripts/extra.py').write_bytes(b'not an admitted reader')
            lock = root/'uv.lock'; lock.write_bytes(b'lock')
            p = {'unchanged_code_sha256': {'uv.lock': hashlib.sha256(b'lock').hexdigest()}}
            with patch.object(trainer, 'ROOT', root), patch.object(trainer, 'SELF_SHA', hashlib.sha256(b'own').hexdigest()), patch.object(trainer, 'protocol', return_value=p):
                value = trainer.code_identity({'current_reader_sources': expected}, time.monotonic()+2)
                self.assertEqual(len(value['named_reader_sources']), 95)
                lock.write_bytes(b'changed')
                with self.assertRaises(ValueError): trainer.code_identity({'current_reader_sources': expected}, time.monotonic()+2)
                current = trainer.code_identity({'current_reader_sources': expected}, time.monotonic()+2, enforce=False, p=p)
                self.assertEqual(current['lock_sha256'], hashlib.sha256(b'changed').hexdigest())
                lock.write_bytes(b'lock'); (root/'src/frozen000.py').write_bytes(b'changed-reader')
                with self.assertRaises(ValueError): trainer.code_identity({'current_reader_sources': expected}, time.monotonic()+2)

    def test_obtained_code_document_historical_hashes_survive_drift_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root/'docs/plans').mkdir(parents=True)
            (root/'docs/plans/m7-navigation-training-v2-protocol.json').write_bytes(b'changed protocol')
            (root/'docs/plans/m7-navigation-data-v2-protocol.json').write_bytes(b'changed data protocol')
            document = root/'input.json'; document.write_bytes(b'changed input')
            context = {'manifest': {}, 'code': {'sha': 'old'}, 'historical': {'sha': 'old'}, 'data_plan': {},
                'source_files': [], 'model_inputs': {}, 'plan': {'immutable_prerequisites': {'input': {'path': str(document), 'bytes': 3, 'sha256': 'old'}}, 'prepared_output_files': []}}
            receipt = root/'after.json'
            with patch.object(trainer, 'ROOT', root), patch.object(trainer, 'code_identity', return_value={'sha': 'changed'}) as code, patch.object(trainer.data_reader, 'historical_identity', return_value={'sha': 'changed'}) as historical:
                with self.assertRaises(ValueError): trainer.check_context(context, time.monotonic()+2, receipt)
            value = json.loads(receipt.read_text())
            self.assertEqual(value['code'], {'sha': 'changed'})
            self.assertEqual(value['historical'], {'sha': 'changed'})
            self.assertEqual(value['documents']['input']['sha256'], hashlib.sha256(b'changed input').hexdigest())
            self.assertTrue(value['errors'])
            self.assertFalse(code.call_args.kwargs['enforce']); self.assertFalse(historical.call_args.kwargs['enforce'])

    def test_cpu_runtime_recheck_does_not_reset_changed_threads(self):
        fake = types.SimpleNamespace(__version__='2.9.0+cu128', get_num_threads=lambda: 2,
            cuda=types.SimpleNamespace(is_initialized=lambda: False))
        versions = lambda n: '2.2.5' if n == 'numpy' else '2.9.0'
        with patch.object(trainer.platform, 'python_version', return_value='3.11.15'), patch.object(trainer.importlib.metadata, 'version', side_effect=versions), patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': ''}):
            with self.assertRaises(ValueError): trainer.cpu_runtime(fake)
            fake.get_num_threads = lambda: 1
            self.assertEqual(trainer.cpu_runtime(fake)['compute'], 'CPU one-thread; CUDA hidden/uninitialized')
            fake.cuda.is_initialized = lambda: True
            with self.assertRaises(ValueError): trainer.cpu_runtime(fake)

    def test_managed_output_excludes_producer_and_input_trees(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); producer = root/'producer'; run = root/'corpus/run'; historical = root/'historical'
            for path in (producer/'runs/data', run, historical): path.mkdir(parents=True)
            p = {'immutable_prerequisites': {'data_manifest': {'path': str(producer/'runs/data/manifest.json')}}}
            manifest = {'historical_reader': {'root': str(historical)}, 'old_sources': [{'path': str(run)}], 'new_sources': [], 'input_documents': {}}
            for parent in (producer/'runs/new', run/'new', historical/'new', root):
                with self.assertRaises(ValueError): trainer.output_path(parent/'seed-10', 10, manifest, p)
            self.assertEqual(trainer.output_path(root/'fresh/seed-10', 10, manifest, p), root/'fresh/seed-10')

    def test_mock_pair_uses_same_original_graph_and_fresh_seed_then_publishes_after_release(self):
        for failure in (None, 'fit', 'runtime', 'source'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                output = Path(directory)/'seed-10'; graph = {'ordered_ids_sha256': 'ids'}
                data = {'old-corpus': object(), 'augmented': object()}; context = {'code': {}, 'model_inputs': {}}
                args = types.SimpleNamespace(training_seed=10, cell_source=Path('pinned-cell'), output=output)
                fake = types.SimpleNamespace(set_num_threads=lambda n: None, save=lambda value, stream: stream.write(b'fixture-checkpoint'))
                calls = []
                def fit(g, d, cell, deadline, training):
                    calls.append((g, d, training['training_seed'], training['arm']))
                    if failure == 'fit': raise ValueError('injected first fit failure')
                    return types.SimpleNamespace(state_dict=lambda: {'fixture': 1}), history(training['arm'])
                def source(*args, **kwargs):
                    if failure == 'source' and len(calls) == 1: raise ValueError('injected source drift')
                runtime_calls = []
                def runtime(torch):
                    runtime_calls.append(FakeBudget.held)
                    if failure == 'runtime' and len(runtime_calls) == 2: raise ValueError('changed final runtime')
                    return {'fixture': 'CPU'}
                with patch.object(trainer, 'prepare', return_value=(output, data, graph, context)), patch.object(trainer, 'StorageBudget', FakeBudget), patch.object(trainer, 'check_context', side_effect=source), patch.object(trainer, 'cpu_runtime', side_effect=runtime), patch.object(trainer, 'fit', side_effect=fit), patch.dict(sys.modules, {'torch': fake}):
                    if failure:
                        with self.assertRaises(ValueError): trainer.train(args)
                    else: value = trainer.train(args)
                self.assertFalse(FakeBudget.held)
                if failure in ('fit', 'source'):
                    self.assertEqual(len(calls), 1)
                    retained = json.loads((output/'failure.json').read_text())
                    self.assertEqual(retained['models']['augmented']['status'], 'not_started')
                    self.assertFalse((output/'report.json').exists())
                elif failure == 'runtime':
                    self.assertTrue((output/'report.pending').exists()); self.assertFalse((output/'report.json').exists())
                else:
                    self.assertTrue((output/'report.json').exists())
                    self.assertEqual([row[3] for row in calls], ['old-corpus', 'augmented'])
                    self.assertTrue(all(row[0] is graph and row[2] == 10 for row in calls))
                    self.assertIs(calls[0][1], data['old-corpus']); self.assertIs(calls[1][1], data['augmented'])
                    self.assertEqual(runtime_calls, [True, False])
                    self.assertTrue(value['training_completed'])

    def test_pending_publication_refuses_sync_deadline_and_no_overwrite(self):
        for failure in ('sync', 'deadline', None):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                if failure == 'sync':
                    with patch.object(publication.os, 'fsync', side_effect=OSError('injected fsync')):
                        with self.assertRaises(OSError): trainer.stage_report(root, {}, time.monotonic()+2)
                else:
                    trainer.stage_report(root, {}, time.monotonic()+2)
                    if failure:
                        with self.assertRaises(TimeoutError): trainer.publish_report(root, 0, lambda: None)
                    else:
                        trainer.publish_report(root, time.monotonic()+2, lambda: None)
                        with self.assertRaises(FileExistsError): trainer.publish_report(root, time.monotonic()+2, lambda: None)
                self.assertEqual((root/'report.json').exists(), failure is None)
                self.assertEqual((root/'report.pending').exists(), failure is not None)

    def test_synthetic_loader_preserves_advice_targets_order_and_censored_tails(self):
        p = trainer.protocol(); cases = [dict(scene_seed=3100+i//3, learner_seed=10+i%3, id=f'case{i}') for i in range(12)]
        lengths = {'train': [277,182,315,245,199,265,243,257,67,67], 'dev': [189,338,319,382]}
        data = {'train': [], 'dev': [], 'held_out': []}; sources = []; offset = 0
        for split, rows in lengths.items():
            for n in rows:
                ep = {'run_id': f'{offset:032x}', 'episode': 0, 'features': np.full((n,388), offset/100, np.float32), 'targets': np.full((n,2), .1, np.float32)}
                data[split].append(ep); sources.append({'path': f'/fixture/old/{ep["run_id"]}'}); offset += 1
        raw = {}; new = []; augmented = {'train': list(data['train']), 'dev': data['dev'], 'held_out': []}
        ticks = [600,485,496,600,196,600,600,243,198,600,276,186]
        collection = {'cases': {}, 'identities_before': {str(i): {} for i in (10,11,12)}}
        for i, (case, n) in enumerate(zip(cases, ticks)):
            run_id = f'{i+20:032x}'; path = f'/fixture/new/{run_id}'
            rows = [{'features': np.full(388, (i+20)/100, np.float32), 'nav_advice_action': np.asarray([.2,.3], np.float32), 'action': np.asarray([.7,-.1], np.float32)} for _ in range(n)]
            raw[path+'/recording'] = rows
            ep = {'run_id': run_id, 'episode': 0, 'features': np.stack([x['features'] for x in rows]), 'targets': np.stack([x['nav_advice_action'] for x in rows])}
            augmented['train'].append(ep)
            new.append({'path': path, 'run_id': run_id, 'episode': 0, 'ticks': n, 'feature_target_sha256': hashlib.sha256(ep['features'].tobytes()+ep['targets'].tobytes()).hexdigest()})
            collection['cases'][case['id']] = {'run': path, 'result_sha256': 'synthetic'}
        def ordered(value): return {split: [{'run_id': ep['run_id'], 'episode': 0, 'ticks': len(ep['targets']), 'feature_target_sha256': hashlib.sha256(ep['features'].tobytes()+ep['targets'].tobytes()).hexdigest()} for ep in value[split]] for split in value}
        manifest = {'status': 'prepared-navigation-advice-research-only', 'counts': p['data_contract']['counts'], 'labels': {'old':'unchanged executed targets','new':'nav_advice_action'}, 'current_reader_sources': {}, 'historical_reader': {}, 'old_sources': sources, 'new_sources': new, 'arms': {'old': ordered(data), 'augmented': ordered(augmented)}, 'old_manifest_sha256': 'synthetic', 'input_documents': {'old_manifest': {'path':'/fixture/old-manifest.json'}, 'accepted_collection': {'path':'/fixture/report.json'}}}
        prepared = {'reader': {}, 'historical': {}, 'sources': [{'path': x['path'], 'files': []} for x in sources+new]}
        def read(path, **kwargs): return prepared if Path(path).name == 'after-admission.json' else {}
        nav = types.SimpleNamespace(CASES=cases, admit_record=lambda run, owner, identity: len(raw[str(run/'recording')]))
        helpers = (trainer.artifacts, types.SimpleNamespace(features=lambda row: row['features']), lambda path: iter(raw[str(path)]), old, nav)
        args = types.SimpleNamespace(training_seed=10, output=Path('/fixture/output/seed-10'), graph=Path('/fixture/graph'), graph_manifest=Path('/fixture/graph-manifest'), cell_source=Path('/fixture/cell'))
        def sha(path, *args): return trainer.GRAPH_MANIFEST_SHA if str(path).endswith('graph-manifest') else p['training_inherited']['cell_sha256']
        with patch.object(trainer, 'protocol', return_value=p), patch.object(trainer, 'pinned_documents', return_value={'data_manifest': manifest}), patch.object(trainer, 'output_path', return_value=args.output), patch.object(trainer, 'code_identity', return_value={}), patch.object(trainer, 'check_context'), patch.object(trainer.data_reader, 'helpers', return_value=helpers), patch.object(trainer.data_reader, 'historical_identity', return_value={}), patch.object(trainer.data_reader, 'read_json', side_effect=read), patch.object(trainer.data_reader, 'read_old_transfer', return_value=data) as transfer, patch.object(trainer.data_reader, 'admit_collection', return_value=collection), patch.object(trainer.data_reader, 'pinned_documents', return_value={}), patch.object(trainer.data_reader, 'file_sha', side_effect=sha), patch.object(trainer.male_model, 'load_graph', return_value={'source_graph_sha256':p['training_inherited']['graph_sha256']}):
            _, actual, _, _ = trainer.prepare(args, time.monotonic()+10)
            self.assertEqual(transfer.call_count, 1)
            self.assertEqual(len(actual['old-corpus']['train']), 10); self.assertEqual(len(actual['augmented']['train']), 22)
            np.testing.assert_array_equal(actual['augmented']['train'][10]['targets'][0], np.asarray([.2,.3], np.float32))
            self.assertEqual([len(ep['targets']) for ep in actual['old-corpus']['train'][-2:]], [67,67])
            changed = copy.deepcopy(manifest); changed['new_sources'][0]['feature_target_sha256'] = hashlib.sha256(b'wrong executed labels').hexdigest()
            with patch.object(trainer, 'pinned_documents', return_value={'data_manifest': changed}):
                with self.assertRaisesRegex(ValueError, 'advice'): trainer.prepare(args, time.monotonic()+10)

    def test_cli_has_no_heldout_route_and_fresh_import_stays_lazy(self):
        env = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(ROOT/'src'),str(ROOT/'scripts')))}
        result = subprocess.run([sys.executable, '-c', "import train_male_navigation_v2,sys; assert not ({'torch','mujoco'} & set(sys.modules))"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr[-1000:])
        rejected = subprocess.run([sys.executable, str(ROOT/'scripts/train_male_navigation_v2.py'), '--training-seed','10','--output','unused','--held-out','forbidden'], cwd=ROOT, env=env, capture_output=True, text=True, timeout=15)
        self.assertEqual(rejected.returncode, 2)
        self.assertFalse((ROOT/'unused').exists())


if __name__ == '__main__': unittest.main()
