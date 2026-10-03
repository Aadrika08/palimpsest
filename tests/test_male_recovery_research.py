"""Pure recovery admission/development fixtures; no runtime or model fitting."""
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
from palimpsest import artifacts,male_model,male_policy,male_research
from palimpsest import male_recovery_research as recovery
from test_male_research import development
from test_male_model import graph_fixture
from test_male_evaluation import identity

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import evaluate_male_closed_loop as evaluator


class RecoveryResearch(unittest.TestCase):
    def test_fixed_plan_and_no_heldout_or_winning_seed(self):
        self.assertEqual(recovery.planned('dev'),male_research.planned('dev'))
        self.assertEqual(len(recovery.planned('dev')),24)
        self.assertEqual(recovery.protocol()['closed_loop_scene_seeds'],{'dev':[1100,1101,1102,1103]})
        for stage in ('held_out',None,'train'):
            with self.assertRaises(ValueError):recovery.planned(stage)

    def test_new_reducer_preserves_each_original_threshold_and_exact_pairs(self):
        report,identities=development();report['research_protocol_sha256']=recovery.PROTOCOL_SHA256
        self.assertEqual(recovery.passed_development(report,'c'*64,identities),{10:2,11:2,12:2})
        with self.assertRaises(ValueError):male_research.passed_development(report,'c'*64,identities)
        for change in ('one_seed_loses','missing','pair','wrong_protocol','failed'):
            bad=copy.deepcopy(report)
            if change=='one_seed_loses':
                for row in bad['runs']:
                    if row['training_seed']==12 and row['controller']=='male-original':row.update(outcome='stalled',goal_reached=False)
            if change=='missing':bad['runs'].pop()
            if change=='pair':bad['paired_initial_states'].pop()
            if change=='wrong_protocol':bad['research_protocol_sha256']=male_research.PROTOCOL_SHA256
            if change=='failed':bad['runs'][0]['status']='failed'
            with self.assertRaises(ValueError,msg=change):recovery.passed_development(bad,'c'*64,identities)

    def test_named_recovery_entrypoint_rejects_heldout_before_outputs_or_owner(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);args=SimpleNamespace(repo=ROOT,assets=root,output=root/'never',research_stage='held_out')
            with patch.object(evaluator,'LabSupervisor') as owner,patch.object(recovery,'resolve') as read:
                with self.assertRaisesRegex(ValueError,'development only'):evaluator.evaluate_recovery(args)
                owner.assert_not_called();read.assert_not_called()
            self.assertFalse(args.output.exists())

    def test_named_entrypoint_selects_recovery_adapter_for_shared_spawn_path(self):
        from types import SimpleNamespace
        args=SimpleNamespace(research_stage='dev')
        with patch.object(evaluator,'_evaluate',return_value=0) as shared:
            self.assertEqual(evaluator.evaluate_recovery(args),0)
            shared.assert_called_once_with(args,recovery)

    def test_binding_rejects_unpinned_wrong_world_or_controller_before_load(self):
        binding=recovery.Binding(ROOT/recovery.INDEX_PATH,recovery.INDEX_SHA256,10)
        with patch.object(recovery,'resolve') as read:
            for value in (('cuda','reproduction','checker',{}),('cpu','reproduction','realistic',{}),('cpu','reproduction','checker',None)):
                with self.assertRaises(ValueError):binding.resolve(ROOT,ROOT,'male-original',*value)
            read.assert_not_called()
        with patch.object(male_policy,'_load_checked_policy') as shared:
            with self.assertRaises(ValueError):recovery.load_policy(directory=ROOT,variant='female',expected_report_sha256='a'*64,
                graph_path=ROOT,graph_manifest=ROOT,cell_path=ROOT,seed=0)
            shared.assert_not_called()

    def test_exact_runtime_resolve_and_no_tensor_fallback(self):
        fixed={'python':'3.11.15','numpy':'2.2.5','torch_distribution':'2.9.0'}
        index={'runtime':fixed,'producer_root':'../task-phases',
            'pairs':[{'directory':f'seed-{seed}','report_sha256':'b'*64} for seed in recovery.PAIR_SEEDS]}
        expected=identity()|{'model_manifest_sha256':recovery.INDEX_SHA256}
        provenance={key:expected[key] for key in male_policy.IDENTITY_HASHES if key!='model_manifest_sha256'}
        with patch.object(recovery,'_index',return_value=index),patch.object(recovery,'runtime_identity',return_value=fixed), \
                patch.object(recovery,'_bundle',return_value=({},b'fixture',provenance)) as bundle, \
                patch.object(artifacts,'_read',return_value=b'pinned cell fixture'), \
                patch.object(male_model,'CELL_SHA256',male_policy._sha(b'pinned cell fixture')),patch.object(recovery,'protocol'):
            actual,args=recovery.resolve(ROOT,ROOT,ROOT/recovery.INDEX_PATH,recovery.INDEX_SHA256,10,'male-original',expected)
            self.assertEqual(actual,expected);self.assertEqual(args['research_seed'],10)
            with patch.object(recovery,'runtime_identity',return_value=fixed|{'python':'3.11.16'}):
                bundle.reset_mock()
                with self.assertRaisesRegex(ValueError,'runtime'):recovery.resolve(ROOT,ROOT,ROOT/recovery.INDEX_PATH,recovery.INDEX_SHA256,10,'male-original')
                bundle.assert_not_called()
                with patch.object(male_policy,'_load_checked_policy') as shared:
                    with self.assertRaisesRegex(ValueError,'runtime'):recovery.load_policy(**args)
                    shared.assert_not_called()

    def test_native_loader_retains_small_reader_map_without_rescanning_corpus(self):
        from types import SimpleNamespace
        fixed={'python':'3.11.15','numpy':'2.2.5','torch_distribution':'2.9.0'}
        index={'runtime':fixed,'producer_root':'../task-phases',
            'pairs':[{'directory':f'seed-{seed}','report_sha256':'b'*64} for seed in recovery.PAIR_SEEDS]}
        policy=SimpleNamespace(provenance={});small={'current-reader.py':'a'*64}
        with patch.object(recovery,'_index',return_value=index),patch.object(recovery,'runtime_identity',return_value=fixed), \
                patch.object(artifacts,'_read',return_value=b'cell'),patch.object(male_model,'CELL_SHA256',male_policy._sha(b'cell')), \
                patch.object(recovery,'_bundle',return_value=({},b'checkpoint',{})), \
                patch.object(male_policy,'_load_checked_policy',return_value=policy), \
                patch.object(recovery,'reader_sources',return_value=small) as reader,patch.object(recovery,'corpus_sources') as corpus:
            actual=recovery.load_policy(ROOT.parent/'task-phases/seed-10','original',expected_report_sha256='b'*64,
                graph_path=ROOT,graph_manifest=ROOT,cell_path=ROOT,repo_root=ROOT,research_seed=10)
            self.assertEqual(actual.provenance['recovery_reader_sources'],small)
            reader.assert_called_once_with(ROOT);corpus.assert_not_called()

    def test_lazy_import_in_fresh_bounded_interpreter(self):
        env={**os.environ,'PYTHONPATH':str(ROOT/'src')}
        value=subprocess.run([sys.executable,'-c',"import palimpsest.male_recovery_research,sys; assert not ({'torch','mujoco'} & set(sys.modules))"],
            cwd=ROOT,env=env,capture_output=True,text=True,timeout=10)
        self.assertEqual(value.returncode,0,value.stderr[-512:])




    def test_spawned_worker_uses_exact_named_binding_and_preserves_v2(self):
        config={'_male_research':{'manifest':str(ROOT/recovery.INDEX_PATH),
            'manifest_sha256':recovery.INDEX_SHA256,'training_seed':10}}
        from palimpsest.engine import Engine
        for module in (recovery,male_research):
            with patch('palimpsest.worker.run_worker') as worker:
                module.worker(config,None,None,None,None,None,None)
                factory=worker.call_args.kwargs['engine_factory']
                self.assertEqual(factory.func,Engine.open)
                self.assertIs(type(factory.keywords['research_binding']),module.Binding)
                self.assertEqual(factory.keywords['research_binding'].training_seed,10)
        with patch('palimpsest.worker.run_worker') as worker:
            for key in ('job','snapshot_path','memory_u','intervention'):
                with self.assertRaises(ValueError):recovery.worker(config|{key:'forbidden'},None,None,None,None,None,None)
            worker.assert_not_called()

    def test_tensor_admission_tail_is_semantically_identical_to_original(self):
        tree=ast.parse((ROOT/'src/palimpsest/male_policy.py').read_text())
        body=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='_load_checked_policy').body[2:]
        actual=hashlib.sha256(ast.dump(ast.Module(body=body,type_ignores=[]),include_attributes=False).encode()).hexdigest()
        # Frozen pre-extraction load_policy tail, after its CPU guard and _bundle call.
        self.assertEqual(actual,'c812183fa137f25734b133fa092353f3e2dc1948beaabbbaa99d7ac4f07fb381')


class RecoveryAdmission(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.producer=self.root/'producer';self.producer.mkdir()
        artifacts._CACHE.clear()
        self.data={'status':'prepared-research-only','counts':{'train':2117,'dev':1228,'held_out':0},
            'ordered_sources':{'train':[{}]*10,'dev':[{}]*4,'held_out':[]},
            'recovery_admission':[{'windows':[32,32,3]},{'windows':[32,32,3]}]}
        self.index={'producer_root':'producer','training_source_commit':'a'*40,'before_after_inventory_sha256':'b'*64,
            'training_source_code':{'reader':{'current_reader_sources':{'src/palimpsest/male_model.py':''},
                'adapter_sha256':''},'trainer':{}},'model_inputs':{'fixture':'d'*64},
            'runtime':{'python':'3.11.15','numpy':'2.2.5','torch_distribution':'2.9.0'},
            'pairs':[{'training_seed':seed,'directory':f'seed-{seed}','report_sha256':''} for seed in recovery.PAIR_SEEDS]}
        for base in (self.root,self.producer):
            p=base/'src/palimpsest/male_model.py';p.parent.mkdir(parents=True);p.write_bytes(b'fixed numerical fixture')
        self.index['training_source_code']['reader']['current_reader_sources']['src/palimpsest/male_model.py']=male_policy._sha(b'fixed numerical fixture')
        p=self.producer/'scripts/prepare_male_recovery_data.py';p.parent.mkdir();p.write_bytes(b'fixed reader fixture')
        self.index['training_source_code']['reader']['adapter_sha256']=male_policy._sha(p.read_bytes())
        self.terminal={'status':'passed-research-training','head':'a'*40,'inventories_unchanged':True,
            'completed_pair_content_unchanged':True,'before_inventory_sha256':'b'*64,'after_inventory_sha256':'b'*64,
            'cleanup':{'sampler_stopped':True,'sample_errors':[],'forced_signals':[],'survivors':[]},
            'pairs':[{'training_seed':seed,'status':'completed','supervision':{'status':'completed','returncode':0}} for seed in recovery.PAIR_SEEDS]}
        self.outer={'status':'completed','returncode':0,'elapsed_seconds':200.}
        self.pin_gate()

    def pin_gate(self):
        for key,value in (('training_terminal',self.terminal),('training_supervisor',self.outer),('data_manifest',self.data)):
            path=self.producer/(key+'.json');path.write_bytes(male_model.canonical(value))
            self.index[key]={'path':path.name,'sha256':male_policy._sha(path.read_bytes())}

    def test_normal_enclosing_exit_cleanup_sources_and_data_gate(self):
        self.assertEqual(recovery._gate(self.root,self.index)[1],self.data)
        for change in ('child_failure','cleanup','changed_data'):
            terminal,outer,data=copy.deepcopy((self.terminal,self.outer,self.data))
            if change=='child_failure':self.terminal['pairs'][0]['supervision']['failure']={'type':'LogLimit'}
            if change=='cleanup':self.terminal['cleanup']['forced_signals']=[15]
            if change=='changed_data':self.data['counts']['train']=2116
            self.pin_gate()
            with self.assertRaises(ValueError,msg=change):recovery._gate(self.root,self.index)
            self.terminal,self.outer,self.data=terminal,outer,data;self.pin_gate()
        (self.producer/'scripts/prepare_male_recovery_data.py').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Historical producer'):recovery._gate(self.root,self.index)

    def test_all_fourteen_raw_inventories_reject_modified_or_extra_bytes(self):
        baseline=[];recovery_rows=[];expected=[];total=0
        for i in range(14):
            run=self.producer/f'raw-{i}'
            rows=[]
            for name,raw in (('recording/data',b'fixed recorded bytes'),('snapshots/initial.snp',b'fixed native bytes')):
                path=run/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
                rows.append({'path':name,'bytes':len(raw),'sha256':male_policy._sha(raw)});total+=len(raw)
            if i<12:
                # Baseline's declared report uses its usual runs/<id> location.
                target=self.producer/'runs'/f'raw-{i}';target.parent.mkdir(exist_ok=True);run.rename(target)
                baseline.append({'run_id':f'raw-{i}','files':rows})
            else:
                case=f'case-{i}';path=self.producer/case/'result.json';path.parent.mkdir();path.write_bytes(b'{}')
                expected.append({'case_id':case,'result_sha256':male_policy._sha(b'{}')})
                recovery_rows.append({'path':str(run),'files':rows})
        baseline_path=self.producer/'baseline.json';baseline_path.write_bytes(male_model.canonical({'runs':baseline}))
        report=self.producer/'recovery.json';report.write_bytes(b'{}')
        data={'baseline_collection':{'path':str(baseline_path),'sha256':male_policy._sha(baseline_path.read_bytes())},
            'recovery_report':{'path':str(report),'sha256':male_policy._sha(b'{}')},'protocol':{'recovery_sources':expected},
            'recovery_admission':recovery_rows,'baseline_admission':{},'total_source_bytes':total}
        with patch.object(male_model,'check_sources'):
            value=recovery.corpus_sources(data);self.assertEqual(len(value),32)
            path=self.producer/'runs/raw-0/recording/data';path.write_bytes(b'changed same length!')
            with self.assertRaisesRegex(ValueError,'bytes'):recovery.corpus_sources(data)
            path.write_bytes(b'fixed recorded bytes');(path.parent/'extra').write_bytes(b'extra')
            with self.assertRaisesRegex(ValueError,'inventory'):recovery.corpus_sources(data)

    def bundle_fixture(self):
        source=male_model.validate_graph(graph_fixture())
        source.update(source_graph_sha256='a'*64,graph_manifest_sha256='b'*64,topology_sha256=male_model.digest(source['edges']))
        control,rewiring=male_model.rewire(source,10);self.graphs={'original':source,'degree_rewired':control}
        learning=json.loads((ROOT/'docs/plans/m7-recovery-learning-protocol.json').read_text())
        path=self.root/'docs/plans/m7-recovery-learning-protocol.json';path.parent.mkdir(parents=True)
        path.write_bytes((ROOT/'docs/plans/m7-recovery-learning-protocol.json').read_bytes())
        settings={**learning['training'],'training_seed':10,'rewiring_seed':10,'variants':list(male_policy.VARIANTS),
            'data_manifest_sha256':self.index['data_manifest']['sha256'],
            'research_protocol_sha256':'091c4e98bf8bc4124383673783a21f5687112946ffeaa54c8a70c41e968f2b28',
            'order':learning['ordering'],'hidden_state':learning['right_censoring'],'wall_budget_seconds':600,
            'output_limit_bytes':64*1024**2,'qualification_claims':[]}
        self.training={'training':settings,'prepared_data':self.data,'data_manifest_sha256':self.index['data_manifest']['sha256'],
            'source_code':self.index['training_source_code'],'model_inputs':self.index['model_inputs'],'runtime':self.index['runtime'],
            'feature_protocol':male_model.FEATURE_PROTOCOL,'rewiring':rewiring,
            'graphs':{name:{key:g[key] for key in ('topology_sha256','ordered_ids_sha256','source_graph_sha256','graph_manifest_sha256','type_missing_ids')} for name,g in self.graphs.items()}}
        self.directory=self.producer/'seed-10';self.directory.mkdir()
        self.payloads={'protocol.json':male_model.canonical(self.training)}
        for name,g in self.graphs.items():
            self.payloads[name+'-graph.json']=male_model.canonical(g);self.payloads[name+'.pt']=b'fixture; no tensor decoding'
        self.report={'status':'completed-research-training','training_completed':True,'training_attempted':True,
            'held_out_status':'locked_unopened','held_out_used_for_selection':False,'qualification_claims':[],
            'data_manifest_sha256':self.index['data_manifest']['sha256'],'protocol_sha256':male_model.digest(self.training),
            'files':[{'path':name,'sha256':male_policy._sha(raw),'size_bytes':len(raw)} for name,raw in self.payloads.items()],
            'models':{name:{'status':'completed','graph_file':name+'-graph.json','checkpoint':None,'selected_epoch':1,
                'history':[{'epoch':i,'train_ticks':2117,'train_loss':.1,'dev':{'ticks':1228,'loss':.1,
                    'velocity_mae':.1,'wrapped_heading_mae_radians':.1}} for i in range(1,21)]} for name in self.graphs}}
        ledger={row['path']:row for row in self.report['files']}
        for name,model in self.report['models'].items():model['checkpoint']=ledger[name+'.pt']
        for name,raw in self.payloads.items():(self.directory/name).write_bytes(raw)
        self.publish_report()
        return source

    def publish_report(self):
        raw=male_model.canonical(self.report);(self.directory/'report.json').write_bytes(raw)
        self.index['pairs'][0]['report_sha256']=male_policy._sha(raw)

    def test_bundle_binds_report_ledger_topology_and_earliest_selection_before_torch(self):
        source=self.bundle_fixture()
        with patch.object(male_model,'load_graph',return_value=source),patch.dict(sys.modules,{'torch':None}):
            value=recovery._bundle(self.root,self.index,10,'original','fixture','fixture')
            self.assertEqual(value[0],source);self.assertEqual(value[1],self.payloads['original.pt'])
            for change in ('checkpoint','late_selection','failed','changed_graph'):
                saved=copy.deepcopy(self.report)
                if change=='checkpoint':self.report['files'][1]['sha256']='e'*64
                if change=='late_selection':self.report['models']['original']['selected_epoch']=2
                if change=='failed':self.report['training_completed']=False
                if change=='changed_graph':
                    bad=copy.deepcopy(source);bad['edges'][0][2]+=1
                    (self.directory/'original-graph.json').write_bytes(male_model.canonical(bad))
                self.publish_report()
                with self.assertRaises(ValueError,msg=change):recovery._bundle(self.root,self.index,10,'original','fixture','fixture')
                self.report=saved;self.publish_report()
                (self.directory/'original-graph.json').write_bytes(self.payloads['original-graph.json'])


if __name__=='__main__':unittest.main()
