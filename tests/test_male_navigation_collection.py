"""Synthetic source checks only: no checkpoints, new scenes, Torch/native or lease."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import collect_male_navigation as nav


def ownership():
    names=['floor',*sorted(nav.body.ROBOT_GEOMS),*sorted(nav.OBSTACLES),'wall']
    return {'geometries':[{'geom_id':i,'name':n,'owner':'robot' if n in nav.body.ROBOT_GEOMS else 'world'} for i,n in enumerate(names)]}


class Teacher:
    def __init__(self):
        self._rec_phase=None;self._rec_step_count=0;self._rec_turn_dir=1.;self._prev_bad_contact=False
        self.recovery_back_steps=40;self.recovery_turn_steps=5;self.calls=0
    def act(self,env):
        self.calls+=1;env.path_to_draw=np.array([[0.,0.],[1.,1.]]);env.target_to_draw=np.array([1.,1.])
        return np.array([.7,.4],np.float32)


class Engine:
    def __init__(self):
        self.env=SimpleNamespace(path_to_draw=None,target_to_draw=None,_has_collision=lambda:(False,None,None))
        self.observation={'cam_left':np.zeros((128,128,3),np.uint8),'cam_right':np.zeros((128,128,3),np.uint8),
            'sensors':{'collision':False,'collision_angle':None,'wind_direction':np.array([1.,0.])}}
        self.policy=SimpleNamespace(act=lambda obs:{'action':np.array([.9,-.2],np.float32)})
        self.saved=[];self.writer=SimpleNamespace(tick=lambda e,t,**kw:self.saved.append({'episode':e,'tick':t,**kw}))
        self.total_tick=0;self.episode=0;self.revision=0;self.phase='paused';self.receipt=None
    def submit(self,message):
        if self.receipt==message['id']:return {'status':'applied'}
        self.queued=message;return {'status':'queued'}
    def advance(self):
        self.receipt=self.queued['id'];action=self.policy.act(self.observation)['action']
        raw=nav.input_row(self.observation)|{'action':action,'control':nav.expected_control(action).astype(np.float64)}
        self.writer.tick(0,self.total_tick,**raw);self.total_tick+=1
        if self.total_tick==3:self.phase='terminated'
    def public_state(self):
        return {'phase':self.phase,'last_outcome':{'reason':'stalled'} if self.phase=='terminated' else None,
            'episode':0,'total_tick':self.total_tick}


class Probe:
    def __init__(self,engine):self.engine=engine
    def begin(self,tick):self.tick=tick
    def end(self):
        control=nav.expected_control(np.array([.9,-.2],np.float32)).tolist()
        return {'tick':self.tick,'start_time_s':self.tick*.02,'callback_count':10,'coverage_passed':True,'coverage_errors':[],
            'stages':[{'stage':i,'time_s':self.tick*.02+i*.002,'control':control,'pairs':[]} for i in range(10)],
            'end':{'data_time_s':(self.tick+1)*.02,'contact_cache_time_s':self.tick*.02+.018,'pairs':[]}}


def isolated(engine):
    return {**{k:'1'*64 for k in nav.ISOLATION},'student_input':nav.input_hashes(nav.input_row(engine.observation))['input']}


def sample(env):
    return {'position_xyz':[0.,0.,.1],'quaternion':[1.,0.,0.,0.]}


class NavigationCollection(unittest.TestCase):
    def source(self):
        engine=Engine();teacher=Teacher();result={'rows':[],'contact_ownership':ownership(),'numeric_admission':nav.numeric_admission([np.zeros((128,128,3),np.uint8)]*2,138)}
        from palimpsest.engine import _teacher_fingerprint
        result['initial_teacher_sha256']=_teacher_fingerprint(teacher)
        with patch.object(nav,'isolation',side_effect=isolated),patch.object(nav,'sample',side_effect=sample):
            reason=nav.collect(engine,teacher,Probe(engine),result,time.monotonic()+20)
        return engine,teacher,result,reason

    def test_actual_loop_queries_and_executes_once_separate_float32_labels(self):
        loaded_before={name:sys.modules.get(name) for name in ('torch','mujoco')}
        engine,teacher,result,reason=self.source()
        self.assertEqual((teacher.calls,len(engine.saved),reason),(3,3,'stalled'))
        self.assertNotIn('first_failure_packet',result)
        for tick,(row,raw) in enumerate(zip(result['rows'],engine.saved)):
            self.assertEqual((row['teacher_queries'],row['policy_calls']),(1,1))
            self.assertEqual(raw['nav_advice_action'].tolist(),np.array([.7,.4],np.float32).tolist())
            self.assertNotEqual(raw['nav_advice_action'].tolist(),raw['action'].tolist())
            nav.bind_row(raw,row,result['contact_ownership'],tick)
            for key,value in [('nav_advice_action',np.array([.9,-.2],np.float32)),('control',np.array([0.,0.],np.float32)),
                              ('body_contact_times',raw['body_contact_times']+.001)]:
                with self.assertRaises(ValueError):nav.bind_row({**raw,key:value},row,result['contact_ownership'],tick)
            changed=copy.deepcopy(row);changed['query_after']['rng']='2'*64
            with self.assertRaisesRegex(ValueError,'altered'):nav.bind_row(raw,changed,result['contact_ownership'],tick)
            changed=copy.deepcopy(row);changed['policy_calls']=2
            with self.assertRaisesRegex(ValueError,'call binding'):nav.bind_row(raw,changed,result['contact_ownership'],tick)
        self.assertEqual(loaded_before,{name:sys.modules.get(name) for name in ('torch','mujoco')})

    def test_query_isolation_failure_keeps_packet_without_student_step(self):
        engine=Engine();teacher=Teacher();result={'rows':[],'contact_ownership':ownership(),'numeric_admission':nav.numeric_admission([np.zeros((128,128,3),np.uint8)]*2,138)}
        n=0
        def bad(engine):
            nonlocal n
            n+=1;v=isolated(engine)
            if n==2:v['native']='2'*64
            return v
        with patch.object(nav,'isolation',side_effect=bad),patch.object(nav,'sample',side_effect=sample):
            with self.assertRaisesRegex(ValueError,'altered'):nav.collect(engine,teacher,Probe(engine),result,time.monotonic()+20)
        self.assertEqual((teacher.calls,len(engine.saved)),(1,0))
        self.assertEqual(result['first_failure_packet']['query_after']['native'],'2'*64)
        self.assertEqual(result['rows'],[])

    def test_named_contact_set_support_world_and_rejections(self):
        engine,_,result,_=self.source();raw=copy.deepcopy(engine.saved[0]);g=nav.ownership_map(ownership());ids={v['name']:k for k,v in g.items()}
        for robot in nav.ROBOT:
            for obstacle in nav.OBSTACLES:self.assertTrue(nav.admit_pair([ids[robot],ids[obstacle]],3,-.01,g))
        for wheel in nav.body.GROUND_SUPPORT:self.assertFalse(nav.admit_pair([ids['floor'],ids[wheel]],2,0.,g))
        self.assertFalse(nav.admit_pair([ids['floor'],ids['obstacle0']],1,-.01,g))
        for pair in [('floor','base_geom'),('floor','caster_fork'),('wall','left_wheel_geom'),
                     ('cam_left_marker','obstacle0'),('base_geom','left_wheel_geom')]:
            with self.assertRaises(ValueError):nav.admit_pair([ids[n] for n in pair],3,-.01,g)
        with self.assertRaises(ValueError):nav.admit_pair([ids['floor'],ids['obstacle0']],1,float('nan'),g)
        # Unexpected contact is published before rejection, not silently suppressed.
        raw['body_contact_counts'][:]=1;raw['body_contact_ids'][:,0]=[ids['floor'],ids['base_geom']]
        raw['body_contact_classes'][:,0]=3;raw['body_contact_distances'][:,0]=-.001
        with self.assertRaisesRegex(ValueError,'Unexpected'):nav.admit_contacts(raw,ownership(),0)
        raw=copy.deepcopy(engine.saved[0]);raw['body_contact_counts'][0]=129
        with self.assertRaisesRegex(ValueError,'bounded'):nav.admit_contacts(raw,ownership(),0)
        raw=copy.deepcopy(engine.saved[0]);raw['body_contact_ids'][0,127,0]=1
        with self.assertRaisesRegex(ValueError,'padding'):nav.admit_contacts(raw,ownership(),0)

    def test_unexpected_contact_preserves_published_first_packet(self):
        engine=Engine();teacher=Teacher();result={'rows':[],'contact_ownership':ownership(),'numeric_admission':nav.numeric_admission([np.zeros((128,128,3),np.uint8)]*2,138)}
        g=nav.ownership_map(ownership());ids={v['name']:k for k,v in g.items()}
        class BadProbe(Probe):
            def end(self):
                interval=super().end()
                pair={'geom_ids':[ids['floor'],ids['base_geom']],'distance_m':-.01,'classification':'unexpected_robot_contact'}
                for packet in [*interval['stages'],interval['end']]:packet['pairs']=[pair]
                return interval
        with patch.object(nav,'isolation',side_effect=isolated),patch.object(nav,'sample',side_effect=sample):
            with self.assertRaisesRegex(ValueError,'Unexpected'):nav.collect(engine,teacher,BadProbe(engine),result,time.monotonic()+20)
        self.assertEqual(len(engine.saved),1);self.assertEqual(len(result['rows']),1)
        self.assertIn('first_failure_packet',result)
        self.assertTrue(np.all(engine.saved[0]['body_contact_counts']==1))
        self.assertTrue(np.all(engine.saved[0]['body_contact_distances'][:,0]==-.01))

    def test_incomplete_coverage_and_command_failure_keep_contact_packet(self):
        for fault in ('coverage','command'):
            engine=Engine();teacher=Teacher();result={'rows':[],'contact_ownership':ownership(),
                'numeric_admission':nav.numeric_admission([np.zeros((128,128,3),np.uint8)]*2,138)}
            class BrokenProbe(Probe):
                def end(self):
                    interval=super().end()
                    if fault=='coverage':interval.update(coverage_passed=False,callback_count=9,coverage_errors=['missing'])
                    return interval
            if fault=='command':engine.advance=lambda:(_ for _ in ()).throw(RuntimeError('primary command failure'))
            with patch.object(nav,'isolation',side_effect=isolated),patch.object(nav,'sample',side_effect=sample):
                with self.assertRaises((ValueError,RuntimeError)):nav.collect(engine,teacher,BrokenProbe(engine),result,time.monotonic()+20)
            packet=result['first_failure_packet']['interval_contacts']
            self.assertEqual(len(packet['stages']),10);self.assertEqual(len(engine.saved),0)
            report={'cases':{c['id']:{'status':'not_started'} for c in nav.CASES},'owners_completed':0,'numeric_ticks':0}
            self.assertFalse(nav.run_cases(report,lambda c,i:(_ for _ in ()).throw(ValueError(fault))))
            self.assertTrue(all(report['cases'][c['id']]['status']=='not_started' for c in nav.CASES[1:]))

    def test_numeric_admission_and_real_scientific_initial_comparison(self):
        images=[np.zeros((128,128,3),np.uint8)]*2
        limits=nav.numeric_admission(images,138)
        self.assertEqual(limits['navigation_bytes'],555)
        self.assertEqual(limits['bytes_per_tick'],sum(limits[k] for k in ('engine_bytes','contact_bytes','navigation_bytes')))
        self.assertLess(limits['recording_bytes'],144*nav.MiB)
        for bad in (True,0,139):
            with self.assertRaises(ValueError):nav.numeric_admission(images,bad)
        from evaluate_male_closed_loop import initial_fingerprint
        identity={'controller':'male-original','fixture':'old-original'}
        snapshot={'application':{'seed':3100,'controller':'male-original','episode':0,'total_tick':0,'episode_step':0,
                      'phase':'paused','eyes':{'left':True,'right':True}},
            'policy':{'kind':'male-reduced-v1','failure_diagnostics':{},'hidden':np.zeros((1,138),np.float32)},
            'identity':{'policy':{'provenance':{'policy_identity':identity}},'environment_profile':{'fixture':1}},
            'observation':Engine().observation,'integration':np.zeros(4,np.float64),'environment':{},
            'rng':{'environment':{},'environment_seed':3100,'spaces':{}}}
        world={'pose':[0.,0.,0.],'goal':[1.,0.,.25],'obstacles':[],'arena':6.}
        # Only the file decoding boundary is stubbed: actual fingerprint and mismatch helper run.
        with patch('palimpsest.snapshots.read_snapshot',return_value=snapshot):
            first=nav.initial_match(Path('/fixture'),world,nav.CASES[0],identity)
            self.assertEqual(nav.initial_match(Path('/fixture'),world,nav.CASES[0],identity,first),first)
            altered=copy.deepcopy(snapshot);altered['integration'][0]=1.
            with patch('palimpsest.snapshots.read_snapshot',return_value=altered):
                with self.assertRaisesRegex(ValueError,'Paired initial'):nav.initial_match(Path('/fixture'),world,nav.CASES[0],identity,first)

    def test_pinned_reader_failure_does_not_read_inputs(self):
        p={'current_reusable_source_sha256':{'src/fixture.py':'1'*64},'generator':{'source_sha256':{}}}
        with patch.object(nav,'plan',return_value=p),patch.object(nav,'digest',return_value='2'*64):
            with self.assertRaisesRegex(ValueError,'Pinned study reader'):nav.source_pins(Path('/fixture'))

    def test_natural_outcomes_no_censoring_or_replacement(self):
        for reason in ('goal','collision','stalled'):
            self.assertEqual(nav.natural_boundary(2,{'phase':'terminated','last_outcome':{'reason':reason},'episode':0,'total_tick':2}),reason)
        nav.natural_boundary(600,{'phase':'truncated','last_outcome':{'reason':'time_limit'},'episode':0,'total_tick':600})
        for state in [{'phase':'paused','last_outcome':None},{'phase':'terminated','last_outcome':{'reason':'coverage_complete'}},
                      {'phase':'truncated','last_outcome':{'reason':'time_limit'}}]:
            with self.assertRaises(ValueError):nav.natural_boundary(2,{**state,'episode':0,'total_tick':2})
        for bad in [{**nav.CASES[0],'scene_seed':3120},{**nav.CASES[0],'learner_seed':True}]:
            with self.assertRaises(ValueError):nav.check_case(bad)
        report={'cases':{c['id']:{'status':'not_started'} for c in nav.CASES},'owners_completed':0,'numeric_ticks':0};calls=[]
        def owner(case,item):
            calls.append(case)
            if len(calls)==2:raise ValueError('first infrastructure failure')
            return 3
        self.assertFalse(nav.run_cases(report,owner));self.assertEqual((len(calls),report['owners_completed'],report['numeric_ticks']),(2,1,3))
        self.assertTrue(all(report['cases'][c['id']]['status']=='not_started' for c in nav.CASES[2:]))
        report={'cases':{c['id']:{'status':'not_started'} for c in nav.CASES},'owners_completed':0,'numeric_ticks':0}
        self.assertTrue(nav.run_cases(report,lambda c,i:3));self.assertEqual(report['numeric_ticks'],36)

    def test_real_parent_admission_refuses_wrong_source_and_label(self):
        engine,_,result,_=self.source();result.update(case=nav.CASES[0],status='completed-recording',engine_closed=True,
            callback_restored=True,final_state=engine.public_state(),outcome='stalled',initial_world={},initial_fingerprint={'fixture':'initial'})
        identity={'fixture':'original-only'}
        manifest={'status':'completed','profile':nav.PROFILE,'controller':'male-original','seed':3100,'scenario':{'id':'reproduction'},
            'texture':'checker','navigation_collection':{'study_sha256':nav.PLAN_SHA,'source_identity':identity,'case':result['case'],
             'label_kind':'returned-analytic-teacher-advice','label_privileged':True,'generic_replay_qualified':False,'contact_ownership':result['contact_ownership'],'initial_fingerprint':result['initial_fingerprint'],'teacher_initial_sha256':result['initial_teacher_sha256']}}
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'snapshots').mkdir();(run/'snapshots/initial.snp').write_bytes(b'fixture')
            with patch.object(nav,'read_json',return_value=manifest),patch('palimpsest.records.iter_ticks',return_value=iter(engine.saved)),patch.object(nav,'initial_ready'),patch.object(nav,'initial_match',return_value=result['initial_fingerprint']):
                self.assertEqual(nav.admit_record(run,result,identity),3)
            for field,value in [('coverage_passed',False),('callback_count',9),('coverage_errors',['missing'])]:
                altered=copy.deepcopy(result);altered['rows'][0][field]=value
                with patch.object(nav,'read_json',return_value=manifest),patch('palimpsest.records.iter_ticks',return_value=iter(engine.saved)):
                    with self.assertRaisesRegex(ValueError,'callback coverage'):nav.admit_record(run,altered,identity)
            altered=copy.deepcopy(result);altered['rows'][1]['teacher_before_sha256']='2'*64
            with patch.object(nav,'read_json',return_value=manifest),patch('palimpsest.records.iter_ticks',return_value=iter(engine.saved)):
                with self.assertRaisesRegex(ValueError,'full teacher history'):nav.admit_record(run,altered,identity)
            altered=copy.deepcopy(result);altered['outcome']='goal'
            with patch.object(nav,'read_json',return_value=manifest),patch('palimpsest.records.iter_ticks',return_value=iter(engine.saved)):
                with self.assertRaisesRegex(ValueError,'outcome differs'):nav.admit_record(run,altered,identity)
            for change in [('profile','teacher'),('seed',3110),('controller','teacher')]:
                altered=copy.deepcopy(manifest);altered[change[0]]=change[1]
                with patch.object(nav,'read_json',return_value=altered):
                    with self.assertRaisesRegex(ValueError,'source/profile'):nav.admit_record(run,result,identity)
            altered=copy.deepcopy(manifest);altered['navigation_collection']['label_kind']='executed-target'
            with patch.object(nav,'read_json',return_value=altered):
                with self.assertRaisesRegex(ValueError,'source/profile'):nav.admit_record(run,result,identity)

    def test_pending_publication_final_sync_source_and_deadline(self):
        class Budget:
            def check(self,n,*,path):self.path=path
        for fault in ('source','late','sync',None):
            with tempfile.TemporaryDirectory() as tmp:
                path=Path(tmp)/'report.json';budget=Budget()
                def check():
                    if fault=='source':raise ValueError('source drift')
                with patch.object(nav.os,'fsync',side_effect=OSError('sync') if fault=='sync' else None),\
                     patch.object(nav.time,'monotonic',return_value=11 if fault=='late' else 9):
                    if fault:
                        with self.assertRaises((ValueError,TimeoutError,OSError)):nav.publish(path,{'status':'completed-collection'},budget,10,check)
                        self.assertFalse(path.exists());self.assertTrue(path.with_suffix('.pending').exists())
                    else:
                        nav.publish(path,{'status':'completed-collection'},budget,10,check);self.assertTrue(path.exists())
                        with self.assertRaises(FileExistsError):nav.publish(path,{},budget,10,check)
        self.assertLess(nav.admission()['recording_bytes'],144*nav.MiB)
        self.assertEqual(nav.admission()['aggregate_bytes'],2150*nav.MiB)


if __name__=='__main__':unittest.main()
