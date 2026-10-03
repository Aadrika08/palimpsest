"""Pure admission/dispatch fixtures; no held-out corpus or runtime work."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from palimpsest import artifacts, male_recovery_heldout as held, male_recovery_research as recovery, male_research

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import evaluate_male_recovery_heldout as entry
import collect_male_teachers as collector
import evaluate_male_closed_loop as evaluator
spec = importlib.util.spec_from_file_location('recorded_runner', ROOT / 'scripts/male_research.py')
recorded = importlib.util.module_from_spec(spec); spec.loader.exec_module(recorded)


class RecoveryHeldout(unittest.TestCase):
    def test_reserved_plan_no_success_threshold_and_separate_disk_arithmetic(self):
        p = held.protocol()
        self.assertEqual(p['teacher_scene_seeds']['held_out'], [1012, 1013, 1014, 1015])
        self.assertEqual(p['closed_loop_scene_seeds'], {'held_out': list(range(1200, 1208))})
        self.assertEqual(held.planned('held_out'), male_research.planned('held_out'))
        self.assertEqual(len(held.planned('held_out')), 48)
        self.assertIsNone(p['held_out_capability_threshold'])
        self.assertEqual(p['qualification_claims'], [])
        self.assertEqual(p['combined_managed_ceiling_bytes'], p['collection_bytes'] + p['recorded_evaluation_bytes'] + p['evaluation_limits']['held_out_bytes'])
        self.assertEqual(p['combined_admission_bytes'], 52 * 160 * 1024**2 + 52 * 2 * 1024**2 + 64 * 1024**2 + 40 * 1024**2)
        self.assertEqual(p['combined_disk_required_bytes'], p['combined_admission_bytes'] + 1024**3)
        self.assertLess(p['combined_admission_bytes'], p['combined_managed_ceiling_bytes'])
        for stage in ('dev', None):
            with self.assertRaises(ValueError): held.planned(stage)
        with self.assertRaises(ValueError): recovery.planned('held_out')

    def test_locked_gate_precedes_heldout_reads_outputs_and_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for stage in ('collect', 'recorded', 'closed-loop'):
                args = SimpleNamespace(repo=root, assets=root, output=root/'never', collection=root/'unopened.json' if stage=='recorded' else None,
                    collection_sha256='a'*64 if stage=='recorded' else None, stage=stage)
                with patch.object(held, 'protocol'), patch.object(held, 'require_unlock', side_effect=ValueError('locked')), \
                     patch.object(held, 'heldout_paths') as paths, patch.object(collector, '_collect') as collect, \
                     patch.object(recorded, '_evaluate_heldout') as infer, patch.object(evaluator, '_evaluate') as native:
                    with self.assertRaisesRegex(ValueError, 'locked'): entry.run(args)
                    for mock in (paths, collect, infer, native): mock.assert_not_called()
                self.assertFalse(args.output.exists())
                if args.collection is not None:self.assertFalse(args.collection.exists())

    def test_pinned_normal_terminal_cleanup_required(self):
        p = held.protocol()['prerequisites']
        terminal = {'status':'passed-development', 'head':p['source_commit'], 'inventories_unchanged':True,
            'owners_completed':24, 'before_inventory_sha256':p['inventory_sha256'], 'after_inventory_sha256':p['inventory_sha256'],
            'evaluation_sha256':p['evaluation']['sha256'], 'development_sha256':p['development']['sha256'],
            'cleanup':{'sampler_stopped':True,'sample_errors':[],'forced_signals':[],'survivors':[]}}
        enclosing = {'status':'passed-development','terminal_sha256':p['terminal']['sha256'],
            'supervision':{'status':'completed','returncode':0,'elapsed_seconds':833.7}}
        development = {'status':'passed-development','qualification_claims':[], 'evaluation_sha256':p['evaluation']['sha256'],
            'research_manifest_sha256':recovery.INDEX_SHA256,'research_protocol_sha256':recovery.PROTOCOL_SHA256}
        docs = {'terminal':terminal, 'enclosing':enclosing, 'development':development, 'evaluation':{}}
        def read(path, pin, cap=held.MAX_JSON):
            key=next(k for k in docs if str(path).endswith(p[k]['path']));self.assertEqual(pin,p[key]['sha256']);return docs[key]
        with patch.object(recovery,'read_pin',side_effect=read):
            # protocol() is itself pinned; use its already-read immutable fixture.
            with patch.object(held,'protocol',return_value={'prerequisites':p}):
                held._prerequisites(ROOT)
                for changed in ('failure','nonzero','late','signal','inventory','wrong_report'):
                    bad=copy.deepcopy(docs)
                    if changed=='failure':bad['enclosing']['supervision']['failure']={'type':'LogLimit'}
                    if changed=='nonzero':bad['enclosing']['supervision']['returncode']=1
                    if changed=='late':bad['enclosing']['supervision']['elapsed_seconds']=1850.01
                    if changed=='signal':bad['terminal']['cleanup']['forced_signals']=['TERM']
                    if changed=='inventory':bad['terminal']['inventories_unchanged']=False
                    if changed=='wrong_report':bad['development']['evaluation_sha256']='f'*64
                    with patch.object(recovery,'read_pin',side_effect=lambda path,pin,cap=held.MAX_JSON: bad[next(k for k in bad if str(path).endswith(p[k]['path']))]):
                        with self.assertRaises(ValueError,msg=changed):held._prerequisites(ROOT)

    def test_output_overlap_and_raw_payload_disjointness(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'source';source.mkdir()
            with patch.object(held,'frozen_roots',return_value=[source]):
                for path in (source, source/'new', root):
                    with self.assertRaisesRegex(ValueError,'overlaps'):held.outside_sources(path,root)
                self.assertEqual(held.outside_sources(root/'safe',root),root/'safe')
        data={'ordered_sources':{'train':[{'run_id':'1'*32,'feature_target_sha256':'b'*64}], 'dev':[],'held_out':[]},
              'baseline_admission':{'splits':{'train':[{'feature_target_sha256':'a'*64}],'dev':[],'held_out':[]}}}
        import numpy as np
        prepared={'train':[],'dev':[],'held_out':[{'features':np.zeros((1,388),np.float32),'targets':np.zeros((1,2),np.float32)} for _ in range(4)]}
        rows=[{'run_id':str(n)*32,'feature_target_sha256':str(n)*64} for n in range(2,6)]
        value={'splits':{'train':[],'dev':[],'held_out':rows}}
        with patch.object(recovery,'_gate',return_value=(ROOT,data,{})),patch.object(male_research,'validate_collection'):
            held.disjoint_heldout(value,{'_directory':ROOT/'data/manifests'},prepared)
            import hashlib
            old=data['ordered_sources']['train'][0]['feature_target_sha256']
            data['ordered_sources']['train'][0]['feature_target_sha256']=hashlib.sha256(prepared['held_out'][0]['features'].tobytes()+prepared['held_out'][0]['targets'].tobytes()).hexdigest()
            with self.assertRaisesRegex(ValueError,'episode duplicates'):held.disjoint_heldout(value,{'_directory':ROOT/'data/manifests'},prepared)
            data['ordered_sources']['train'][0]['feature_target_sha256']=old
            for key,bad in (('run_id','1'*32),('feature_target_sha256','a'*64)):
                copy_=copy.deepcopy(value);copy_['splits']['held_out'][0][key]=bad
                with self.assertRaisesRegex(ValueError,'duplicates'):held.disjoint_heldout(copy_,{'_directory':ROOT/'data/manifests'},prepared)

    def test_new_worker_uses_truthful_binding_and_rejects_other_scenes(self):
        config={'seed':1200,'_male_research':{'manifest':str(ROOT/recovery.INDEX_PATH),'manifest_sha256':recovery.INDEX_SHA256,'training_seed':10}}
        from palimpsest.engine import Engine
        with patch('palimpsest.worker.run_worker') as worker:
            held.worker(config,None,None,None,None,None,None)
            factory=worker.call_args.kwargs['engine_factory']
            self.assertEqual(factory.func,Engine.open)
            self.assertIs(type(factory.keywords['research_binding']),held.Binding)
            self.assertIn('held-out evaluation',factory.keywords['research_binding'].provenance()['scope'])
            self.assertIn('development',recovery.Binding(ROOT/recovery.INDEX_PATH,recovery.INDEX_SHA256,10).provenance()['scope'])
            for bad in (1100,1208,1200.0):
                with self.assertRaises(ValueError):held.worker(config|{'seed':bad},None,None,None,None,None,None)

    def test_default_v2_recorded_and_collection_dispatch_preserved(self):
        args=SimpleNamespace()
        with patch.object(recorded,'_evaluate_heldout',return_value=0) as shared:
            self.assertEqual(recorded.evaluate_heldout(args),0)
            shared.assert_called_once_with(args,male_research)
        with patch.object(collector,'_collect',return_value=0) as shared:
            self.assertEqual(collector.collect(args),0);shared.assert_called_once_with(args)
        binding=held.Binding(ROOT/held.INDEX_PATH,held.INDEX_SHA256,10)
        with patch.object(recovery,'load_policy',return_value='fixture') as shared:
            self.assertEqual(binding.load_policy({'field':'unchanged'},7),'fixture')
            shared.assert_called_once_with(field='unchanged',seed=7)

    def test_missing_collection_hash_rejects_before_report_read(self):
        args=SimpleNamespace(repo=ROOT,collection=ROOT/'unused.json',collection_sha256=None)
        with patch.object(held,'outside_sources',return_value=args.collection),patch.object(artifacts,'_read') as read:
            with self.assertRaisesRegex(ValueError,'hash required'):held.heldout_paths(args,{'status':'held_out_evaluation_unlocked'})
            read.assert_not_called()

    def test_staged_functions_reach_adapters_and_retain_native_failure(self):
        # Real collector/evaluator/record reader, with owner/model execution replaced.
        from contextlib import nullcontext
        from unittest.mock import Mock
        from test_male_research import ResearchFixtures
        from test_male_evaluation import identity
        import train_male_reduced
        fixture=ResearchFixtures();fixture.setUp();self.addCleanup(fixture.doCleanups)
        paths=[fixture.teacher(seed,3) for seed in range(1012,1016)]
        receipt={'status':'held_out_evaluation_unlocked','identities':{
            f'{seed}:{controller}':identity(controller) for seed in held.PAIR_SEEDS for controller in held.CONTROLLERS}}
        data={'ordered_sources':{'train':[{'run_id':'1'*32,'feature_target_sha256':'b'*64}],'dev':[],'held_out':[]},
              'baseline_admission':{'splits':{'train':[{'feature_target_sha256':'a'*64}],'dev':[],'held_out':[]}}}
        source=SimpleNamespace(budget=SimpleNamespace(check=Mock(return_value={})),
            control_budget=SimpleNamespace(check=Mock()),workers={},shutdown=Mock(),
            start=Mock(side_effect=RuntimeError('injected native startup refusal')))
        args=SimpleNamespace(repo=ROOT,assets=fixture.root,output=fixture.root/'collect',research_stage='held_out',
            protocol=ROOT/held.PROTOCOL_PATH,research_manifest=ROOT/held.INDEX_PATH,research_manifest_sha256=held.INDEX_SHA256)
        with patch.object(held,'require_unlock',return_value=receipt),patch.object(held,'research_sources',return_value={}):
            with patch.object(collector,'LabSupervisor',return_value=source):
                self.assertEqual(collector._collect(args,held),1)
            report=json.loads((args.output/'collection.json').read_text())
            self.assertEqual([r['seed'] for r in report['runs']],list(range(1012,1016)))
            self.assertEqual([r['status'] for r in report['runs']],['failed']+['not_started']*3)
            self.assertTrue(report['research_sources_unchanged'])
            self.assertEqual(report['unlock'],receipt)
            args.output=fixture.root/'recorded';args.held_out=paths
            budget=SimpleNamespace(lock=lambda:nullcontext(),check=Mock())
            with patch.object(recorded,'StorageBudget',return_value=budget), \
                 patch.object(held,'_manifest',return_value=(ROOT/held.INDEX_PATH,{})), \
                 patch.object(recovery,'_gate',return_value=(ROOT,data,{})), \
                 patch.object(held,'resolve',side_effect=lambda root,assets,path,pin,seed,controller,*expected:(identity(controller),{})), \
                 patch.object(held.Binding,'load_policy',return_value=SimpleNamespace(agent='fixture model boundary')), \
                 patch.object(train_male_reduced,'evaluate',return_value={'ticks':12,'loss':0.}) as model:
                self.assertEqual(recorded._evaluate_heldout(args,held,held.disjoint_heldout),0)
            result=json.loads((args.output/'evaluation.json').read_text())
            self.assertEqual(result['status'],'completed');self.assertEqual(model.call_count,6)
            self.assertEqual([r['status'] for r in result['models']],['completed']*6)
            self.assertEqual(result['collection']['total_ticks'],12)
            args.output=fixture.root/'closed-loop';source.start.reset_mock()
            with patch.object(evaluator,'LabSupervisor',return_value=source) as owner, \
                 patch.object(held,'resolve',side_effect=lambda root,assets,path,pin,seed,controller,*expected:(identity(controller),{})):
                self.assertEqual(evaluator._evaluate(args,held),1)
            result=json.loads((args.output/'evaluation.json').read_text())
            self.assertEqual([r['status'] for r in result['runs']],['failed']+['not_started']*47,result.get('error'))
            self.assertEqual(owner.call_args.kwargs['worker_target'],held.worker)
            self.assertEqual(owner.call_args.kwargs['storage_limits'].max_bytes,8*1024**3)
            self.assertTrue(result['sources_unchanged']);self.assertTrue(result['model_identities_unchanged'])

    def test_fresh_lazy_import_and_help_no_torch_or_native(self):
        env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
        code="import palimpsest.male_recovery_heldout,sys; assert not ({'torch','mujoco'} & set(sys.modules))"
        result=subprocess.run([sys.executable,'-c',code],env=env,cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr[-500:])


if __name__=='__main__':unittest.main()
