"""Pure fixed development checks; fake owners provide no task qualification."""
import copy
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from palimpsest import puck_development as dev, puck_student as student, puck_learning as learning, puck_profile as puck
from palimpsest.records import RunWriter, iter_ticks
from palimpsest.snapshots import state_digest, read_snapshot
from test_puck_student import ROOT, identity, contact, gate
import test_puck_student as student_fixtures
sys.path.insert(0,str(ROOT/'scripts'))
import evaluate_puck_development as evaluator


def initial_world(row):
    case=puck.layout(ROOT,row['seed'],row['split']);x,y,yaw=case['rover_pose'];qw,qz=math.cos(yaw/2),math.sin(yaw/2)
    return {'time_s':0.,'rover_pose':[x,y,math.atan2(2*(qw*qz),1-2*(qz*qz))],
            'puck_xyz':[*case['puck_xy'],.062],'puck_velocity_xy':[0.,0.],'goal_xy':case['goal_xy']}


def native_fixture(app,row):
    return {'schema_version':1,'application':app,'integration_enum':8191,'integration':np.zeros(440,np.float64),
            'native_data':b'fixture-native','native_sha256':hashlib.sha256(b'fixture-native').hexdigest(),
            'policy':None,'teacher':None,'environment':{'fixture':'fixed native caches'},
            'identity':{'mujoco':'3.3.6','numpy':'2.2.5','python':[3,11,15],'policy':None,'teacher':None,'torch':{'threads':1}},
            'rng':{'python':random.Random(row['seed']).getstate(),'numpy':np.random.RandomState(row['seed']).get_state(),
                   'environment':{'fixture':row['seed']},'environment_seed':row['seed'],'spaces':{'action_space':None},
                   'torch_cpu':np.array([row['model_seed']],np.uint8),'torch_cuda':[]}}


class DevelopmentFixtures(unittest.TestCase):
    run_owner=student_fixtures.StudentFixtures.run_owner

    def snapshot(self,row):
        world=initial_world(row);state=puck.initialize(world,row['case'])
        app=dev.application(ROOT,row,{'fixture':'source'},{'fixture':'profile'},'a'*64,identity(row['model_seed']),
                            state,world,contact(0),learning.initial_cursor())
        return native_fixture(app,row)

    def test_plan_and_fresh_typed_envelope_reject_before_bundle_read(self):
        rows=dev.plan(ROOT);self.assertEqual([(r['seed'],r['model_seed']) for r in rows],[(s,m) for s in range(6100,6104) for m in (21,22,23)])
        self.assertEqual(sum(r['max_bytes'] for r in rows),12*160*1024**2)
        self.assertLess(gate.record_estimate(600,1),rows[0]['max_bytes'])
        with tempfile.TemporaryDirectory() as tmp,patch.object(student,'admit_bundle',return_value=(Path(tmp),identity())) as bundle:
            config={'repo':str(ROOT),'output':str(Path(tmp)/rows[0]['id']),'row':rows[0],'sources':{},
                    'learning_student_development':dev.PROTOCOL_SHA256,'bundle_root':tmp,'initial_reference':None}
            self.assertEqual(dev.admit_config(config,ROOT)['ticks'],600)
            for change in ({'seed':6100.0},{'model_seed':21.0},{'max_ticks':600.0},{'max_bytes':float(rows[0]['max_bytes'])},
                           {'kind':'policy-replay'},{'seed':6200}):
                bundle.reset_mock()
                with self.assertRaises(ValueError):dev.admit_config(config|{'row':rows[0]|change},ROOT)
                bundle.assert_not_called()
            for change in ({'source_output':tmp},{'start_tick':0},{'learning_student':student.PROTOCOL_SHA256},
                           {'learning_student_development':'0'*64},{'initial_reference':{}}):
                with self.assertRaises(ValueError):dev.admit_config(config|change,ROOT)

    def test_scientific_match_includes_all_non_torch_rng_and_exact_defined_state(self):
        rows=dev.plan(ROOT);a=self.snapshot(rows[0]);b=self.snapshot(rows[1]);sources={'fixture':'source'}
        def fingerprint(s,row):return dev.scientific_initial(s,ROOT,row,sources,identity(row['model_seed']))
        original=fingerprint(a,rows[0]);self.assertEqual(original,fingerprint(b,rows[1]))
        # Raw allocations and Torch RNG are retained but explicitly not paired equality.
        changed=copy.deepcopy(b);changed['native_data']=b'different allocation';changed['native_sha256']=hashlib.sha256(changed['native_data']).hexdigest()
        changed['rng']['torch_cpu']=np.array([99],np.uint8);self.assertEqual(original,fingerprint(changed,rows[1]))
        for key in ('python','numpy','environment','spaces'):
            bad=copy.deepcopy(b);bad['rng'][key]={'fixture':'changed'}
            self.assertNotEqual(original,fingerprint(bad,rows[1]))
        for key in ('integration','environment','identity'):
            bad=copy.deepcopy(b)
            if key=='integration':bad[key][4]=1.
            else:bad[key]['fixture']='different'
            self.assertNotEqual(original,fingerprint(bad,rows[1]))
        for change in ({'integration':np.zeros(440,np.float32)},{'integration':np.zeros(439)},
                       {'integration':np.full(440,np.nan)},{'integration_enum':8191.0},{'native_sha256':'0'*64}):
            with self.assertRaises(ValueError):fingerprint(b|change,rows[1])
        bad=copy.deepcopy(b);bad['application']['own_supervisor_cursor']['tick']=1
        with self.assertRaises(ValueError):fingerprint(bad,rows[1])
        with self.assertRaises(ValueError):student.validate_application(a['application'],ROOT,rows[0],sources,{'fixture':'profile'},'a'*64,identity(),0,state_digest(a['application']))

    def test_actual_owner_initial_match_real_record_and_rng_mismatch_before_action_one(self):
        rows=dev.plan(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)/rows[0]['id'];code,result,env,apps,calls=self.run_owner(base,development_row=rows[0])
            self.assertEqual(code,0,result.get('error'));self.assertEqual((calls,env.steps,result['ticks']),(10,10,10))
            self.assertEqual(set(result['snapshots']),{'initial'});self.assertEqual(len(apps),1)
            actual_rng=read_snapshot(base/'initial.snp')['rng']
            self.assertEqual(state_digest(actual_rng['python']),state_digest(random.Random(rows[0]['seed']).getstate()))
            self.assertEqual(state_digest(actual_rng['numpy']),state_digest(np.random.RandomState(rows[0]['seed']).get_state()))
            reference={'owner_id':rows[0]['id'],'result_sha256':gate.digest(base/'result.json'),
                       'snapshot_sha256':result['snapshots']['initial']['sha256']}
            for row,mismatch in ((rows[1],False),(rows[2],True)):
                out=Path(tmp)/row['id'];code,r,env,apps,calls=self.run_owner(out,development_row=row,initial_reference=reference,rng_mismatch=mismatch)
                self.assertEqual(code,1 if mismatch else 0,r.get('error'))
                self.assertEqual((calls,env.steps),(0,0) if mismatch else (10,10));self.assertEqual(set(r['snapshots']),{'initial'})
                self.assertEqual(r['initial_match']['status'],'failed' if mismatch else 'passed')
                numeric=list(iter_ticks(out/'recording'));self.assertEqual(len(numeric),0 if mismatch else 10)
                self.assertTrue(all(not any(k.startswith('teacher') for k in n) for n in numeric))
                if mismatch:self.assertEqual(r['own_supervisor_cursor'],learning.initial_cursor())
            self.assertEqual(json.loads((base/'recording/manifest.json').read_text())['schema'],'puck-student-development-v1')
        with tempfile.TemporaryDirectory() as tmp:
            code,r,env,_,calls=self.run_owner(Path(tmp)/rows[0]['id'],development_row=rows[0],bad_action=True)
            self.assertEqual((code,calls,env.steps),(1,1,0));self.assertEqual(r['own_supervisor_cursor'],learning.initial_cursor())

    def test_each_model_threshold_all_rows_and_no_winning_seed_selection(self):
        rows=[r|{'status':'completed','result':{'final_state':{'reason':'puck_goal'}}} for r in dev.plan(ROOT)]
        for i in (0,1,2):rows[i]['result']['final_state']['reason']='time_limit'
        self.assertEqual(dev.admission(rows,ROOT)['status'],'passed')
        rows[3]['result']['final_state']['reason']='stalled'
        result=dev.admission(rows,ROOT);self.assertEqual(result['status'],'failed');self.assertEqual(result['goals_each_model'],{'21':2,'22':3,'23':3})
        self.assertIn('locked',result['held_out'])
        for wrong in (rows[:-1],list(reversed(rows)),[rows[0]|{'seed':6100.0}]+rows[1:]):
            with self.assertRaises(ValueError):dev.admission(wrong,ROOT)

    def run_stage(self,rootdir,*,fail_index=None,negative=False,late=False,late_exit=False,late_admission=False):
        from contextlib import contextmanager
        class Budget:
            def __init__(self,roots,*args,**kwargs):self.root=roots[0]
            def check(self,*args,**kwargs):return {'fixture':True}
            @contextmanager
            def lock(self):
                self.root.mkdir();yield self
                if late_exit:clock[0]=1201.
        rows=dev.plan(ROOT);calls=[];clock=[0.]
        def owned(command,destination,environment,budget,row,start):
            calls.append(row);destination.mkdir();config=json.loads(command[-1]);index=len(calls)-1
            self.assertEqual(config['initial_reference'] is None,row['model_seed']==21)
            if index==fail_index:
                gate.write_json(destination/'result.json',{'status':'failed','error':{'message':'fixture initial mismatch'}},budget)
                return {'passed':False}
            reason='time_limit' if negative and row['model_seed']==21 else 'puck_goal'
            result={'status':'passed','row':row,'ticks':1,'model_calls':1,'completed_control_tick':1,
                    'own_supervisor_cursor':{'tick':1},'snapshots':{'initial':{'sha256':'a'*64}},
                    'initial_match':{'status':'passed','reference':config['initial_reference']},'completion':reason,'final_state':{'reason':reason}}
            writer=RunWriter(destination/'recording',{'schema':'puck-student-development-v1','development_protocol_sha256':dev.PROTOCOL_SHA256,
                             'row':row,'source_hashes':config['sources'],'initial_reference':config['initial_reference'],
                             **student.identity(ROOT,identity(row['model_seed']))})
            writer.tick(0,0,action=np.zeros(2,np.float64));writer.finish({'outcome':reason});writer.close()
            gate.write_json(destination/'result.json',result,budget)
            return {'passed':True}
        actual_admission=dev.admission
        def admitted(*args):
            result=actual_admission(*args)
            if late:clock[0]=1201.
            return result
        def bundle(root,path,seed):
            if late_admission:clock[0]=1201.
            return path,identity(seed)
        args=SimpleNamespace(repo=ROOT,output=rootdir/'gate',retention_root=rootdir,expected_commit='fixture',bundle_root=rootdir/'models')
        with patch.object(evaluator,'StorageBudget',Budget),patch.object(evaluator,'development_sources',return_value={'fixture':'source'}),\
             patch.object(evaluator.subprocess,'check_output',side_effect=['fixture',gate.protocol(ROOT)['upstream_commit']]),\
             patch.object(evaluator.subprocess,'run'),patch.object(student,'admit_bundle',side_effect=bundle),\
             patch.object(evaluator,'supervised_owner',side_effect=owned),patch.object(dev,'admission',side_effect=admitted),\
             patch.object(evaluator.time,'monotonic',side_effect=lambda:clock[0]):
            code=evaluator.main(args)
        return code,json.loads((args.output/'report.json').read_text()),calls

    def test_real_filesystem_stage_all_outcomes_and_infra_stop_retains_unstarted_rows(self):
        for negative,fail_index,late in ((True,None,False),(False,1,False),(False,None,True)):
            with self.subTest(negative=negative,fail_index=fail_index,late=late),tempfile.TemporaryDirectory() as tmp:
                code,r,calls=self.run_stage(Path(tmp),negative=negative,fail_index=fail_index,late=late)
                self.assertEqual(len(r['owners']),12);self.assertEqual(code,1 if fail_index is not None or late else 0)
                self.assertEqual(len(calls),2 if fail_index is not None else 12)
                self.assertTrue(r['sources_unchanged']);self.assertTrue(r['models_unchanged']);self.assertEqual(r['held_out'],'locked')
                if fail_index is not None:self.assertEqual([o['status'] for o in r['owners']],['completed','failed']+['not_started']*10)
                if negative:
                    self.assertEqual(r['admission']['status'],'failed');self.assertEqual(r['status'],'completed')
                if late:self.assertIn('1200',r['finalization_errors'][0])

    def test_admission_and_lease_exit_are_inside_internal_deadline(self):
        for admission,exit_ in ((True,False),(False,True)):
            with tempfile.TemporaryDirectory() as tmp:
                code,r,calls=self.run_stage(Path(tmp),late_admission=admission,late_exit=exit_)
                self.assertEqual(code,1);self.assertEqual(r['status'],'failed')
                self.assertEqual(len(calls),0 if admission else 12)
                self.assertTrue(r['sources_unchanged']);self.assertTrue(r['models_unchanged'])
