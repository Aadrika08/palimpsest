"""Frozen start, evaluator and subprocess-outcome fixtures; no native physics proof."""
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
spec=importlib.util.spec_from_file_location('verify_task_starts',SCRIPTS/'verify_task_starts.py')
verify=importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)


class StartGuards(unittest.TestCase):
    def test_actual_pure_geometry_and_complete_budget(self):
        layout=verify.geometry_preflight()
        self.assertEqual(set(layout),{case['id'] for case in verify.STARTS})
        for row in layout.values():
            self.assertTrue(row['placement_valid'])
            self.assertEqual({p['id'] for p in row['initial_visible_landmarks']},{'inspect-a','inspect-b'})
        estimate=verify.admission({k:np.zeros((128,128,3),np.uint8) for k in ('cam_left','cam_right')})
        self.assertEqual(estimate['aggregate_bytes'],1840775168)
        self.assertEqual(estimate['allowances']['row_result_bytes'],8*64*verify.MiB)
        self.assertEqual(estimate['allowances']['atomic_native_staging_bytes'],128*verify.MiB)
        self.assertEqual(len(verify.CASES)*2,8)
        self.assertEqual(verify.PROTOCOL['maximum_numeric_ticks'],8*600)
        self.assertLess(estimate['aggregate_bytes'],2*1024**3)
        with self.assertRaises(ValueError):
            verify.admission({k:np.zeros((256,256,3),np.uint8) for k in ('cam_left','cam_right')})

    def test_declared_origin_is_separate_and_never_rewrites_engine_outcome(self):
        case=verify.CASES[1]
        state={'phase':'terminated','task':{'phase':'complete'},
               'last_outcome':{'reason':'task_completed','evaluator_actual_home_distance_m':.9}}
        original=copy.deepcopy(state)
        row=verify.capability(state,case,list(case['start_pose']))
        self.assertTrue(row['passed']);self.assertEqual(row['declared_origin_actual_home_distance_m'],0.)
        self.assertEqual(row['engine_default_origin_outcome'],state['last_outcome'])
        self.assertEqual(state,original)
        endpoint=copy.deepcopy(case['start_pose']);endpoint[0]+=.3
        self.assertFalse(verify.capability(state,case,endpoint)['passed'])
        for endpoint in ([0.,0.],[0.,float('nan'),0.],[0.,0.,float('inf')]):
            with self.assertRaises(ValueError):verify.capability(state,case,endpoint)
        for phase,reason in (('terminated','collision'),('terminated','stalled'),('truncated','time_limit')):
            failed={**state,'phase':phase,'last_outcome':{'reason':reason}}
            self.assertFalse(verify.capability(failed,case,case['start_pose'])['passed'])
        with self.assertRaises(ValueError):verify.natural_outcome({**state,'phase':'failed'})

    def test_real_fixture_engine_records_natural_time_limit_as_completed(self):
        from test_engine import SmallEnv
        from palimpsest.engine import Engine
        from palimpsest.records import RunWriter,iter_ticks
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'recording';env=SmallEnv(truncate_at=1)
            engine=Engine(env,RunWriter(path,{'run_id':'natural-failure-fixture'}),controller='manual')
            try:
                verify.command(engine,'step-0','step')
                self.assertEqual(verify.natural_outcome(engine.public_state()),'time_limit')
                self.assertEqual(engine.total_tick,1)
            finally:engine.close()
            self.assertTrue(env.closed)
            self.assertEqual(json.loads((path/'manifest.json').read_text())['status'],'completed')
            self.assertEqual(len(list(iter_ticks(path))),1)

    def test_fresh_cursor_pose_and_planner_fields_are_required_not_cleared(self):
        env=SimpleNamespace(data=SimpleNamespace(time=0.,qvel=np.zeros(3),ctrl=np.zeros(2)),
            _t=0,_speed=0.,_stall_steps=0,_last_action=np.zeros(2),path_to_draw=None,target_to_draw=None,
            planner=SimpleNamespace(**{k:None for k in ('_cached_occ','_cached_obstacles_hash','_cached_clearance','_W','_H','_origin')}),
            visited={(0,0)},explore_binsize=.2,_prev_xy=np.zeros(2),
            _base_xy=lambda:np.zeros(2),_bin_of=lambda xy,size:(0,0))
        engine=SimpleNamespace(env=env,phase='paused',episode=0,total_tick=0,episode_step=0,
            manual_action=np.zeros(2),task_state={'last_tick':None,'odometry':{'travel_m':0.}})
        verify.fresh_boundary(engine)
        for name,value in (('_W',4),('_cached_occ',np.ones(1))):
            setattr(env.planner,name,value)
            with self.assertRaises(ValueError):verify.fresh_boundary(engine)
            self.assertIs(getattr(env.planner,name),value)
            setattr(env.planner,name,None)
        env._prev_xy[0]=1.
        with self.assertRaises(ValueError):verify.fresh_boundary(engine)
        self.assertEqual(env._prev_xy[0],1.)

    def test_native_normalization_excludes_only_three_transport_fields(self):
        source={'application':{'source_run_id':'source','event_prefix':{'offset':1},'execution_mode':'live',
                               'scenario':'encoder-homing','task_state':{'last_tick':None}},
                'observation':{'cam_left':np.zeros((1,1,3),np.uint8)},'native':np.arange(4,dtype=np.float64)}
        original=copy.deepcopy(source);other=copy.deepcopy(source)
        other['application'].update(source_run_id='replay',event_prefix={'offset':9},execution_mode='actions')
        self.assertEqual(verify.normalized_snapshot(source),verify.normalized_snapshot(other))
        for location in ('native','task','camera'):
            changed=copy.deepcopy(other)
            if location=='native':changed['native'][0]=1.
            elif location=='task':changed['application']['task_state']['last_tick']=0
            else:changed['observation']['cam_left'][0,0,0]=1
            self.assertNotEqual(verify.normalized_snapshot(source),verify.normalized_snapshot(changed))
        self.assertEqual(source['application'],original['application'])

    def test_functional_exit_is_clean_complete_exit_one_only(self):
        report={'status':'failed-functional','protocol_status':'completed','executed_cases':4,'capability_passed':False,
            'cases':{verify.case_key(c):{mode:{'status':'completed-recording'} for mode in ('source','actions')} for c in verify.CASES}}
        supervisor={'status':'failed','returncode':1}
        self.assertTrue(verify.supervision_matches(report,supervisor))
        for change in ({'failure':{'type':'LogLimit'}},{'failure':{}},{'error':'final fsync'},{'error':None},{'status':'timeout'},{'returncode':-15}):
            self.assertFalse(verify.supervision_matches(report,{**supervisor,**change}))
        report['cases'][verify.case_key(verify.CASES[-1])]['actions']['status']='not_started'
        self.assertFalse(verify.supervision_matches(report,supervisor))

    def test_natural_failed_source_replays_all_cases_but_infrastructure_stops(self):
        # Mock subprocess/file boundaries; no fabricated simulation outcome is claimed.
        def exercise(infrastructure):
            with tempfile.TemporaryDirectory() as temp:
                output=Path(temp);report={'cases':{verify.case_key(c):{m:{'status':'not_started'} for m in ('source','actions')} for c in verify.CASES}}
                (output/'report.json').write_text(json.dumps(report))
                calls=[];counts=[]
                budget=SimpleNamespace(check_count=lambda kind,current:counts.append((kind,current)))
                def bounded(argv,stage,*args,**kwargs):
                    child=json.loads(argv[-1]);stage.mkdir(parents=True)
                    calls.append((verify.case_key(child['case']),child['mode']))
                    run=Path(child['run']);(run/'recording').mkdir(parents=True)
                    (run/'recording/manifest.json').write_text(json.dumps({'status':'completed'}))
                    (run/'snapshots').mkdir();(run/'snapshots/initial.snp').write_bytes(b'fixture')
                    result={'status':'completed-recording','run':str(run),'engine_closed':True}
                    if child['mode']=='source':result.update(recorded_ticks=1,override_sha256='fixture',criterion={'passed':len(calls)>1})
                    else:result['compared_ticks']=1
                    if infrastructure and len(calls)==1:result['status']='failed-infrastructure'
                    (stage/'result.json').write_text(json.dumps(result))
                    return {'status':'completed','returncode':0}
                def save(path,value,config,maximum=verify.MiB):path.write_text(json.dumps(value))
                with patch.object(verify,'storage',return_value=budget),patch.object(verify,'save',side_effect=save),\
                     patch('palimpsest.evaluate.bounded_process',side_effect=bounded),\
                     patch('palimpsest.assets.verify_assets',return_value={'ok':True,'files':[]}),\
                     patch('palimpsest.records.iter_ticks',return_value=iter(())) as ticks:
                    ticks.side_effect=lambda path:iter([{'episode':0,'tick':0}])
                    result=verify.gate({'repo':str(output),'assets':str(output/'assets'),'output':str(output)})
                final=json.loads((output/'report.json').read_text())
                self.assertFalse(result)
                if infrastructure:
                    self.assertEqual(len(calls),1);self.assertEqual(final['status'],'failed-infrastructure')
                    self.assertEqual(final['cases'][verify.case_key(verify.CASES[0])]['actions']['status'],'not_started')
                else:
                    self.assertEqual(len(calls),8);self.assertEqual(final['status'],'failed-functional')
                    self.assertEqual(final['executed_cases'],4);self.assertEqual(final['successful_cases'],3)
                    self.assertEqual([m for _,m in calls],['source','actions']*4)
                    self.assertEqual(counts,[('runs',n) for n in range(8)])
        exercise(False);exercise(True)


if __name__=='__main__':unittest.main()
