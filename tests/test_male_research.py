"""Pure fixtures for the frozen v2 stages; no Torch, owner, EGL, or training."""
import copy
from contextlib import nullcontext
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
import uuid

import numpy as np
from palimpsest import artifacts, male_model, male_policy, male_research as research
from palimpsest.engine import Engine
from palimpsest.records import RunWriter
import test_male_policy as policy_fixtures
from test_male_evaluation import evaluation, identity

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import collect_male_teachers as collector
import train_male_reduced as trainer
spec = importlib.util.spec_from_file_location('research_cli', ROOT / 'scripts/male_research.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


def collection(stage='development'):
    frozen = research.protocol()
    return {'splits': {split: [{'episodes': [{'episode': 0, 'seed': seed, 'ticks': 600}],
        'scenario': 'reproduction', 'texture': 'checker', 'final_phase': 'paused', 'last_outcome': None}
        for seed in seeds if split in frozen['teacher_collection_stages'][stage]]
        for split, seeds in frozen['teacher_scene_seeds'].items()}}


def development():
    identities = {f'{pair}:{controller}': identity(controller) | {'protocol_sha256': f'{pair:064x}'}
                  for pair in research.PAIR_SEEDS for controller in research.CONTROLLERS}
    rows = research.planned('dev')
    for index, row in enumerate(rows):
        goal = row['seed'] in (1100, 1101)
        row.update(run_id=f'{index + 1:032x}', status='completed', close_status='closed', owner_exitcode=0, owner_alive=False,
            ticks=20, goal_reached=goal, outcome='goal' if goal else 'stalled',
            model_identity=identities[f"{row['training_seed']}:{row['controller']}"],
            initial_fingerprint={key: f"{row['seed']:064x}" for key in
                ('world', 'integration', 'environment', 'environment_identity', 'inputs', 'features', 'environment_rng')})
    pairs = [{'training_seed': left['training_seed'], 'seed': left['seed'], 'original_run_id': left['run_id'],
              'control_run_id': right['run_id'], 'status': 'exact_match', 'fingerprint': left['initial_fingerprint']}
             for left, right in zip(rows[::2], rows[1::2])]
    return {'status': 'completed', 'stage': 'dev', 'research_protocol_sha256': research.PROTOCOL_SHA256,
        'research_manifest_sha256': 'c' * 64, 'sources_unchanged': True, 'model_identities_unchanged': True,
        'recording_fingerprints_unchanged': True, 'supervisor_shutdown': 'completed', 'finalization_errors': [],
        'qualification_claims': [], 'runs': rows, 'paired_initial_states': pairs}, identities


class ResearchFixtures(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        artifacts._CACHE.clear()

    def test_frozen_splits_matching_budgets_and_no_winning_seed(self):
        p = research.protocol()
        groups = [*p['teacher_scene_seeds'].values(), *p['closed_loop_scene_seeds'].values()]
        self.assertEqual(len(set(sum(groups, []))), sum(map(len, groups)))
        self.assertTrue(set(sum(groups, [])).isdisjoint(range(0, 136)))
        self.assertEqual((len(research.planned('dev')), len(research.planned('held_out'))), (24, 48))
        for stage in ('dev', 'held_out'):
            self.assertLess(len(research.planned(stage)) * 160 * 1024**2, p['evaluation_limits'][stage + '_bytes'])
        self.assertEqual(p['max_ticks_per_run'], 600)
        for seed in research.PAIR_SEEDS:
            t = research.training(seed)
            self.assertEqual((t['epochs'], t['window'], t['training_seed'], t['rewiring_seed']), (20, 32, seed, seed))
            self.assertEqual(research.validate_training(t), seed)
            t['epochs'] = 19
            with self.assertRaises(ValueError):
                research.validate_training(t)
        for seed in (0, 9, 13, True):
            with self.assertRaises(ValueError):
                research.training(seed)

    def test_collection_requires_exact_stage_order_counts_and_natural_short_outcomes(self):
        report = collection()
        research.validate_collection(report, 'development')
        row = report['splits']['dev'][0]
        row['episodes'][0]['ticks'] = 3
        row.update(final_phase='terminated', last_outcome={'reason': 'goal'})
        research.validate_collection(report, 'development')
        for change in ('missing_outcome', 'too_short_train', 'reorder', 'early_heldout'):
            bad = copy.deepcopy(report)
            if change == 'missing_outcome':
                bad['splits']['dev'][0]['last_outcome'] = None
            elif change == 'too_short_train':
                bad['splits']['train'][0]['episodes'][0]['ticks'] = 31
            elif change == 'reorder':
                bad['splits']['train'].reverse()
            else:
                bad['splits']['held_out'] = collection('held_out')['splits']['held_out']
            with self.assertRaises(ValueError, msg=change):
                research.validate_collection(bad, 'development')
        with patch.object(artifacts, '_manifest') as read, self.assertRaisesRegex(ValueError, 'before reading'):
            male_model.prepare_splits({'train': [Path('train')], 'dev': [Path('dev')], 'held_out': [Path('unopened')]}, research_stage='development')
        read.assert_not_called()

    def teacher(self, seed, ticks):
        run = self.root / uuid.uuid4().hex
        writer = RunWriter(run / 'recording', {'run_id': run.name, 'controller': 'teacher', 'profile': 'teacher',
            'teacher_privileged': True, 'seed': seed, 'scenario': 'reproduction', 'texture': 'checker',
            'observation_profile': 'two-rgb-eyes-contact-relative-goal-bearing-v1',
            'sensor_order': ['collision', 'collision_angle', 'wind_cos', 'wind_sin'], 'control_interval_seconds': .02})
        writer.event('episode_started', episode=0, episode_step=0, seed=seed, world={'arena': 7., 'pose': [0., 0., 0.], 'obstacles': [], 'goal': [3., 3., .5]})
        camera = np.full((128, 128, 3), seed % 255, np.uint8)
        for tick in range(ticks):
            writer.tick(0, tick, cam_left=camera, cam_right=camera, sensors=np.array([0., 0., .6, .8], np.float32),
                action=np.array([.7, .3], np.float32), pose=np.array([tick * .01, 0., 0.]),
                next_pose=np.array([(tick + 1) * .01, 0., 0.]), reward=np.array(0.), simulation_time=np.array((tick + 1) * .02))
        writer.finish({'final_phase': 'terminated', 'last_outcome': {'reason': 'goal', 'episode': 0, 'steps': ticks}})
        writer.close()
        return run

    def test_real_record_reader_retains_short_natural_metadata_and_float32_features(self):
        p = research.protocol()
        paths = {split: [self.teacher(seed, 32 if split == 'train' else 3) for seed in seeds]
                 for split, seeds in p['teacher_scene_seeds'].items() if split != 'held_out'} | {'held_out': []}
        with patch.dict('sys.modules', {'torch': None}):
            data, retained = male_model.prepare_splits(paths, research_stage='development')
        self.assertEqual(retained['total_ticks'], 268)
        self.assertEqual(data['train'][0]['features'].dtype, np.float32)
        self.assertEqual(data['train'][0]['features'].shape, (32, 388))
        self.assertEqual(retained['splits']['dev'][0]['final_phase'], 'terminated')
        self.assertEqual(retained['splits']['dev'][0]['last_outcome']['reason'], 'goal')
        self.assertEqual(data['held_out'], [])
        male_model.check_sources(retained)

    def test_unlock_threshold_applies_to_each_original_seed_and_all_owners(self):
        report, identities = development()
        self.assertEqual(research.passed_development(report, 'c' * 64, identities), {10: 2, 11: 2, 12: 2})
        for change in ('one_seed_loses', 'missing', 'failure', 'wrong_model', 'changed_initial', 'missing_pair', 'duplicate', 'source_changed'):
            bad = copy.deepcopy(report)
            if change == 'one_seed_loses':
                # Aggregate original goals remains >=6, yet seed12 must fail.
                for row in bad['runs']:
                    if row['controller'] == 'male-original' and row['training_seed'] in (10, 12):
                        row['goal_reached'] = row['training_seed'] == 10
                        row['outcome'] = 'goal' if row['goal_reached'] else 'stalled'
            elif change == 'missing':
                bad['runs'].pop()
            elif change == 'failure':
                bad['runs'][0]['status'] = 'failed'
            elif change == 'wrong_model':
                bad['runs'][0]['model_identity']['checkpoint_sha256'] = 'd' * 64
            elif change == 'changed_initial':
                bad['runs'][-1]['initial_fingerprint']['inputs'] = 'e' * 64
            elif change == 'missing_pair':
                bad['paired_initial_states'].pop()
            elif change == 'duplicate':
                bad['runs'][-1]['run_id'] = bad['runs'][0]['run_id']
            else:
                bad['sources_unchanged'] = False
            with self.assertRaises(ValueError, msg=change):
                research.passed_development(bad, 'c' * 64, identities)

    def test_heldout_routes_stop_before_source_reads_output_or_owner(self):
        args = SimpleNamespace(repo=ROOT, assets=self.root, output=self.root / 'unopened', research_stage='held_out',
            research_manifest=self.root / 'missing.json', research_manifest_sha256='a' * 64,
            development_report=None, development_sha256=None, protocol=ROOT / research.PROTOCOL_PATH, held_out=[Path('never')])
        with patch.object(collector, 'LabSupervisor') as owner, patch.object(cli, 'prepare_splits') as sources:
            for operation in (collector.collect, evaluation.evaluate, cli.evaluate_heldout):
                with self.assertRaisesRegex(ValueError, 'held-out remains locked'):
                    operation(args)
            owner.assert_not_called()
            sources.assert_not_called()
        self.assertFalse(args.output.exists())

    def test_research_binding_and_worker_reject_nonfresh_or_unpinned_requests(self):
        binding = research.Binding(self.root / 'manifest', 'a' * 64, 10)
        with patch.object(research, 'resolve') as resolver:
            for kwargs in (('cuda', 'reproduction', 'checker', identity()), ('cpu', 'reproduction', 'realistic', identity()),
                           ('cpu', 'reproduction', 'checker', None)):
                with self.assertRaises(ValueError):
                    binding.resolve(ROOT, self.root, 'male-original', *kwargs)
            resolver.assert_not_called()
        for key in ('job', 'snapshot_path', 'memory_u', 'intervention'):
            config = {'_male_research': {'manifest': 'fixed', 'manifest_sha256': 'a' * 64, 'training_seed': 10}, key: 'unsupported'}
            with patch('palimpsest.worker.run_worker') as owner, self.assertRaisesRegex(ValueError, 'fresh'):
                research.worker(config, None, None, None, None, None, None)
            owner.assert_not_called()
        with self.assertRaisesRegex(ValueError, 'trusted research binding'):
            Engine.open(ROOT, self.root, self.root / 'never', controller='male-original', research_binding={})
        self.assertFalse((self.root / 'never').exists())

    def test_development_startup_failure_retains_24_rows_and_all_final_checks(self):
        supervisor = SimpleNamespace(budget=SimpleNamespace(check=Mock(return_value={})), control_budget=SimpleNamespace(check=Mock()),
            workers={}, shutdown=Mock(side_effect=RuntimeError('fixture shutdown failed')), start=Mock(side_effect=RuntimeError('fixture startup failed')))
        args = SimpleNamespace(repo=ROOT, assets=self.root, output=self.root / 'dev', research_stage='dev',
            research_manifest=self.root / 'manifest', research_manifest_sha256='c' * 64)
        with patch.object(evaluation, 'LabSupervisor', return_value=supervisor) as owner, \
             patch.object(evaluation, 'sources', return_value={}), patch.object(research, 'research_sources', return_value={}), \
             patch.object(research, 'resolve', side_effect=lambda root, assets, path, hash, pair, controller: (identity(controller), {})) as models:
            self.assertEqual(evaluation.evaluate(args), 1)
        report = json.loads((args.output / 'evaluation.json').read_text())
        self.assertEqual([row['status'] for row in report['runs']], ['failed'] + ['not_started'] * 23)
        self.assertTrue(report['sources_unchanged'])
        self.assertTrue(report['model_identities_unchanged'])
        self.assertEqual(models.call_count, 12)
        self.assertEqual(owner.call_args.kwargs['worker_target'], research.worker)
        self.assertEqual(owner.call_args.kwargs['storage_limits'].max_runs, 24)
        supervisor.start.assert_called_once()

    def test_research_bundle_is_explicit_and_default_v1_path_rejects_it(self):
        fixture = policy_fixtures.PolicyArtifactTests('test_import_is_lazy')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        p = fixture.protocol
        p['training'], p['collection'] = research.training(10), collection()
        p['collection_sha256'] = male_model.digest(p['collection'])
        p['source_code_sha256']['male_research.py'] = 'd' * 64
        control, p['rewiring'] = male_model.rewire(fixture.graphs['original'], 10)
        fixture.graphs['degree_rewired'] = control
        p['graphs']['degree_rewired'] = {key: control[key] for key in ('topology_sha256', 'ordered_ids_sha256',
            'source_graph_sha256', 'graph_manifest_sha256', 'type_missing_ids')} | {'reachability': male_model.reachability(control)}
        fixture.payloads['degree_rewired-graph.json'] = male_model.canonical(control)
        fixture.payloads['protocol.json'] = male_model.canonical(p)
        fixture.report['held_out_status'] = 'locked_unopened'
        fixture.publish()
        fixture.report.update(source_code_unchanged=True, teacher_sources_unchanged=True, finalization_errors=[])
        for model in fixture.report['models'].values():
            model.update(status='completed', selected_epoch=20,
                history=[{'epoch': epoch, 'dev': {'loss': 1 / epoch}} for epoch in range(1, 21)])
        fixture.write_report()
        arguments = fixture.arguments()
        arguments.pop('cell_path')
        with patch.dict('sys.modules', {'torch': None}):
            graph, _, provenance = male_policy._bundle(fixture.root, 'degree_rewired', **arguments, research_seed=10)
            self.assertEqual(graph, control)
            self.assertEqual(provenance['training_seed'], 10)
            with self.assertRaisesRegex(ValueError, 'frozen protocol'):
                male_policy._bundle(fixture.root, 'degree_rewired', **arguments)
            with self.assertRaisesRegex(ValueError, 'seed differs'):
                male_policy._bundle(fixture.root, 'degree_rewired', **arguments, research_seed=11)

    def test_pair_trainer_never_opens_heldout_and_retains_second_model_after_failure(self):
        for fail in (False, True):
            output = self.root / ('failure' if fail else 'success') / 'seed-10'
            output.parent.mkdir()
            protocol = {'training': research.training(10), 'collection': {'splits': {'train': [], 'dev': [], 'held_out': []}}}
            fake_budget = SimpleNamespace(lock=lambda: nullcontext(), check=Mock())
            fake_model = SimpleNamespace(state_dict=lambda: {})
            fake_torch = SimpleNamespace(save=lambda checkpoint, stream: stream.write(b'fixture checkpoint, never deserialized'))
            graph = {'ordered_ids_sha256': 'a' * 64}
            fit = Mock(side_effect=RuntimeError('fixture fit failure')) if fail else Mock(return_value=(fake_model, {'selected_epoch': 20}))
            with patch.dict('sys.modules', {'torch': fake_torch}), patch.object(trainer, 'fit', fit), \
                 patch.object(trainer, 'evaluate') as heldout, patch.object(trainer, 'check_sources'), \
                 patch.object(trainer, 'check_code'), patch.object(trainer, 'StorageBudget', return_value=fake_budget):
                if fail:
                    with self.assertRaisesRegex(RuntimeError, 'fixture fit failure'):
                        trainer.train(SimpleNamespace(output=output, cell_source=Path('fixture')), {},
                            {'original': graph, 'degree_rewired': graph}, protocol)
                else:
                    trainer.train(SimpleNamespace(output=output, cell_source=Path('fixture')), {},
                        {'original': graph, 'degree_rewired': graph}, protocol)
                heldout.assert_not_called()
            report = json.loads((output / 'report.json').read_text())
            self.assertEqual(report['held_out_status'], 'locked_unopened')
            self.assertTrue(report['source_code_unchanged'])
            self.assertTrue(report['teacher_sources_unchanged'])
            if fail:
                self.assertEqual(report['models']['original']['status'], 'failed')
                self.assertEqual(report['models']['degree_rewired']['status'], 'not_started')
                self.assertEqual(fit.call_count, 1)
            else:
                self.assertEqual(report['status'], 'completed')
                self.assertEqual(fit.call_count, 2)
                for call in fit.call_args_list:
                    self.assertEqual(call.args[-1]['epochs'], 20)
                    self.assertEqual(call.args[-1]['window'], 32)

    def test_teacher_startup_failure_keeps_all12_rows_without_reset_or_replacement(self):
        supervisor = SimpleNamespace(budget=SimpleNamespace(check=Mock(return_value={})), control_budget=SimpleNamespace(check=Mock()),
            workers={}, shutdown=Mock(), start=Mock(side_effect=RuntimeError('fixture startup failed')))
        args = SimpleNamespace(repo=ROOT, assets=self.root, output=self.root / 'teachers', research_stage='development',
            protocol=ROOT / research.PROTOCOL_PATH)
        with patch.object(collector, 'LabSupervisor', return_value=supervisor), \
             patch.object(collector, 'identity', return_value={}), patch.object(research, 'research_sources', return_value={}):
            self.assertEqual(collector.collect(args), 1)
        report = json.loads((args.output / 'collection.json').read_text())
        self.assertEqual([row['status'] for row in report['runs']], ['failed'] + ['not_started'] * 11)
        self.assertEqual([row['seed'] for row in report['runs']], list(range(1000, 1012)))
        self.assertTrue(report['runtime_source_unchanged'])
        self.assertTrue(report['protocol_unchanged'])
        self.assertEqual(report['supervisor_shutdown'], 'completed')
        supervisor.start.assert_called_once()

    def test_publish_is_exclusive_and_all_six_precede_manifest(self):
        for seed in research.PAIR_SEEDS:
            directory = self.root / f'seed-{seed}'
            directory.mkdir()
            (directory / 'report.json').write_text('{}')
            (directory / 'protocol.json').write_text(json.dumps({'collection_sha256': 'a' * 64, 'source_code_sha256': {}}))
        target = self.root / 'research-manifest.json'
        with patch.object(male_policy, '_bundle') as bundle:
            digest = research.publish_manifest(ROOT, self.root, target)
            self.assertEqual(bundle.call_count, 6)
            self.assertEqual(research.sha(target.read_bytes()), digest)
            with self.assertRaises(FileExistsError):
                research.publish_manifest(ROOT, self.root, target)
        target.unlink()
        with patch.object(male_policy, '_bundle', side_effect=ValueError('incomplete pair')):
            with self.assertRaises(ValueError):
                research.publish_manifest(ROOT, self.root, target)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
