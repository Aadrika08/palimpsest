"""Pure turn plan/packet/metric/supervision fixtures; no native owner launch."""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import verify_body_turns as verify
import test_body_adaptation as sessions
import test_verify_body_runtime as packets
from palimpsest import body_adaptation as adaptive, body_profile as body
from palimpsest.records import RunWriter
from palimpsest.storage import StorageLimits
from dataclasses import asdict


class TurnChecks(unittest.TestCase):
    def results(self):
        result={}
        for trial in verify.TRIALS:
            sign=1 if trial['direction']=='left' else -1
            error={'baseline':0.,'uncompensated':2.,'compensated':.5}[trial['condition']]
            rows=[];angles=[0.,0.]
            for tick in range(120):
                increment=[(-sign+error)*.02,sign*.02]
                after=[a+b for a,b in zip(angles,increment)]
                increment=[b-a for a,b in zip(angles,after)]
                yaw=sign*(1+error*.001)*tick
                y=error*tick*.002
                rows.append({'tick':tick,'fit_interval':tick>=20,'dt_s':.02,'increments_rad':increment,
                    'before':{'pose':[0.,y,yaw],'shaft_angles_rad':angles,'time_s':tick*.02},
                    'after':{'pose':[0.,y+error*.002,yaw+sign*(1+error*.001)],
                             'shaft_angles_rad':after,'time_s':(tick+1)*.02},
                    'contact':False,'coverage_passed':True})
                angles=after
            result[trial['id']]={'status':'passed','trial':trial,'rows':rows,'engine_closed':True,
                'callback_restored':True,'physical_calibration':{'radius_m':.06,'track_m':.36,'quantum_rad':.001}}
        return result

    def test_fixed_plan_budget_controls_and_identity(self):
        self.assertEqual(len(verify.TRIALS),6)
        self.assertEqual([t['action'] for t in verify.TRIALS],[[0.,.2]]*3+[[0.,-.2]]*3)
        self.assertEqual(verify.PROTOCOL['maximum_numeric_ticks'],720)
        self.assertEqual(verify.PROTOCOL['snapshot_files'],6)
        self.assertEqual([verify.PROTOCOL[key] for key in ('child_timeout_seconds','inner_timeout_seconds','outer_timeout_seconds')],[180,1200,1260])
        observation={key:np.zeros((128,128,3),np.uint8) for key in ('cam_left','cam_right')}
        estimate=verify.admission(observation)
        self.assertEqual(estimate['aggregate_bytes'],855965696)
        self.assertEqual(estimate['allowances']['numeric_bytes'],168099840)
        self.assertEqual(estimate['per_recording_bytes'],30113792)
        self.assertLess(estimate['aggregate_bytes'],verify.PROTOCOL['output_max_bytes'])
        for trial in verify.TRIALS:
            sign=1 if trial['direction']=='left' else -1
            self.assertEqual(body.effective_control(trial['action']),np.asarray([-sign*.2,sign*.2],np.float32).tolist())
        with self.assertRaises(ValueError):verify.admission({key:np.zeros((128,128,3),np.float32) for key in observation})
        self.assertEqual(verify.PROTOCOL_SHA256,adaptive._sha(verify.PROTOCOL))

    def test_strict_metrics_per_direction_and_invalid_packets_are_distinct(self):
        result=verify.compare_turns(self.results())
        self.assertTrue(result['accepted'])
        for direction in ('left','right'):
            metrics=result['directions'][direction]['comparisons']
            self.assertAlmostEqual(metrics['uncompensated']['wheel_rate_rmse'],math.sqrt(2))
            self.assertAlmostEqual(metrics['compensated']['wheel_rate_rmse'],.5/math.sqrt(2))
            self.assertAlmostEqual(metrics['uncompensated']['yaw_error'],.2)
            self.assertAlmostEqual(metrics['compensated']['lateral_error'],.1)
        bad=self.results()
        bad['compensated-right']['rows']=copy.deepcopy(bad['uncompensated-right']['rows'])
        rejected=verify.compare_turns(bad)
        self.assertFalse(rejected['accepted']);self.assertTrue(rejected['directions']['left']['accepted'])
        self.assertFalse(any(rejected['directions']['right']['improved'].values()))
        for key,value in [('contact',True),('coverage_passed',False),('fit_interval',False),('dt_s',0.)]:
            bad=self.results();bad['baseline-left']['rows'][25][key]=value
            with self.assertRaises(ValueError):verify.compare_turns(bad)
        for value in ([1.], [float('nan'),0.], [101.,0.]):
            bad=self.results();bad['baseline-left']['rows'][25]['increments_rad']=value
            with self.assertRaises(ValueError):verify.compare_turns(bad)
        bad=self.results();bad.pop('compensated-right')
        with self.assertRaises(ValueError):verify.compare_turns(bad)

    def test_cleanup_and_clean_functional_exit_contract(self):
        trial=verify.TRIALS[2];result=self.results()[trial['id']]
        ticks=[{'episode':4,'tick':tick} for tick in range(120)]
        supervision={'status':'completed','returncode':0}
        verify.owner_valid(trial,supervision,result,ticks)
        for bad in ({**supervision,'failure':{'type':'LogLimit'}},{'status':'timeout','returncode':0}):
            with self.assertRaises(ValueError):verify.owner_valid(trial,bad,result,ticks)
        with self.assertRaises(ValueError):verify.owner_valid(trial,supervision,{**result,'engine_closed':False},ticks)
        with self.assertRaises(ValueError):verify.owner_valid(trial,supervision,result,ticks[:-1])
        report={'status':'failed-functional','protocol_status':'completed','owners_completed':6,'numeric_ticks':720,
            'snapshot_files':6,'comparison':{'accepted':False},'trials':{t['id']:{'status':'passed'} for t in verify.TRIALS}}
        exit1={'status':'failed','returncode':1}
        self.assertTrue(verify.supervision_matches(report,exit1))
        for key,value in [('owners_completed',5),('numeric_ticks',600),('protocol_status','incomplete')]:
            self.assertFalse(verify.supervision_matches({**report,key:value},exit1))
        self.assertFalse(verify.supervision_matches(report,{**exit1,'failure':{'type':'LogLimit'}}))

    def gate_fixture(self, output, *, infrastructure_at=None):
        # Replace only the native snapshot reader and child-process boundary.
        # Every published packet still passes the real raw and metric guards.
        state=sessions.SessionState().fitted()
        snapshot={'application':{'body_state':state,'schema_version':6,'scenario':adaptive.SCENARIO,
            'controller':'manual','phase':'paused','total_tick':480,'manual_action':[0.,0.],'pending_commands':[]}}
        report_path=output.parent/'accepted.json';snp=output.parent/'accepted.snp';snp.write_bytes(b'native fixture container')
        reference={**verify.REFERENCE,'snapshot_sha256':verify.digest(snp),'samples_sha256':state['samples_sha256'],
                   'fit_sha256':state['fit_sha256'],'session_sha256':adaptive._sha(state)}
        accepted={'status':'passed','source_unchanged':True,'assets_unchanged':True,
                  'runtime_source':{'commit':reference['source_commit']},'snapshots':{'fitted':{'sha256':reference['snapshot_sha256']}},
                  'accepted_fit':{'fit':state['fit'],'session_sha256':reference['session_sha256']}}
        report_path.write_text(json.dumps(accepted));reference['report_sha256']=verify.digest(report_path)
        config={'repo':str(SCRIPTS.parent),'assets':str(output/'assets'),'output':str(output),
            'calibration_report':str(report_path),'fitted_snapshot':str(snp),
            'storage':{'roots':[str(output)],'limits':asdict(StorageLimits(max_bytes=2*1024**3,min_free_bytes=0,max_runs=6,max_snapshots=1)),
                       'headroom_bytes':8*1024**2}}
        report={'status':'running','runtime_source':{},'harness_sha256':{},
                'trials':{t['id']:{'status':'not_started'} for t in verify.TRIALS}}
        (output/'report.json').write_text(json.dumps(report))
        results=self.results();results['compensated-right']['rows']=copy.deepcopy(results['uncompensated-right']['rows'])
        template,manifest=packets.HarnessChecks().row();calls=[]
        def child(argv,stage,*args,**kwargs):
            body_config=json.loads(argv[-1]);trial=body_config['trial'];calls.append(trial['id'])
            stage.mkdir();run=Path(body_config['run']);(run/'snapshots').mkdir(parents=True)
            (run/'snapshots/initial.snp').write_bytes(b'fixture initial')
            if len(calls)==infrastructure_at:
                return {'status':'failed','returncode':1,'failure':{'type':'LogLimit'}}
            result=results[trial['id']]
            identity=adaptive.IDENTITY if trial['condition']=='compensated' else {'standalone':True,'protocol_sha256':verify.PROTOCOL_SHA256}
            writer=RunWriter(run/'recording',{'run_id':run.name,'body_profile_identity':identity,
                'body_contact_ownership':manifest['body_contact_ownership']})
            plan=adaptive.plan_action(state,trial['action']) if trial['condition']=='compensated' else {
                'applied_action':trial['action'],'applied_control':body.effective_control(trial['action'])}
            for row in result['rows']:
                tick=row['tick'];raw=copy.deepcopy(template)
                raw.pop('episode');raw.pop('tick')
                raw.update(pose=np.array(row['before']['pose']),next_pose=np.array(row['after']['pose']),
                    body_encoder_before=np.array(row['before']['shaft_angles_rad']),body_encoder_after=np.array(row['after']['shaft_angles_rad']),
                    body_encoder_increment=np.array(row['increments_rad']),body_nominal_action=np.array(trial['action']),
                    body_nominal_control=np.array(body.effective_control(trial['action']),np.float32),
                    action=np.array(plan['applied_action']),control=np.array(plan['applied_control']),simulation_time=np.array((tick+1)*.02))
                raw['body_contact_times']+=tick*.02;raw['body_stage_controls'][:]=plan['applied_control']
                raw['body_end_data_time']=np.array((tick+1)*.02)
                row.update(action=raw['action'].tolist(),control=raw['control'].tolist())
                writer.tick(4 if trial['condition']=='compensated' else 0,tick,**raw)
            writer.finish({});writer.close();(stage/'result.json').write_text(json.dumps(result))
            return {'status':'completed','returncode':0}
        return config,reference,snapshot,child,calls

    def test_six_valid_owners_finish_before_functional_scoring_and_packet_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'output';output.mkdir();config,reference,snapshot,child,calls=self.gate_fixture(output)
            with patch.object(verify,'REFERENCE',reference),patch('palimpsest.snapshots.read_snapshot',return_value=snapshot), \
                    patch('palimpsest.assets.verify_assets',return_value={'ok':True}), \
                    patch('palimpsest.evaluate.bounded_process',side_effect=child):
                self.assertFalse(verify.gate(config))
            report=json.loads((output/'report.json').read_text())
            self.assertEqual(calls,[t['id'] for t in verify.TRIALS],report.get('error'))
            self.assertEqual(report['status'],'failed-functional',report.get('error'));self.assertEqual(report['numeric_ticks'],720)
            self.assertEqual(report['owners_completed'],6);self.assertEqual(report['snapshot_files'],6)
            from palimpsest.records import iter_ticks
            stage=output/verify.TRIALS[0]['id'];data=json.loads((stage/'result.json').read_text())
            run=next(path for path in stage.iterdir() if path.is_dir());ticks=list(iter_ticks(run/'recording'))
            verify.bind_evaluator_rows(data['rows'],ticks)
            data['rows'][30]['after']['pose'][1]+=.1
            with self.assertRaisesRegex(ValueError,'published numeric'):verify.bind_evaluator_rows(data['rows'],ticks)

    def test_infrastructure_failure_keeps_unstarted_remainder(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'output';output.mkdir();config,reference,snapshot,child,calls=self.gate_fixture(output,infrastructure_at=2)
            with patch.object(verify,'REFERENCE',reference),patch('palimpsest.snapshots.read_snapshot',return_value=snapshot), \
                    patch('palimpsest.assets.verify_assets',return_value={'ok':True}), \
                    patch('palimpsest.evaluate.bounded_process',side_effect=child):
                self.assertFalse(verify.gate(config))
            report=json.loads((output/'report.json').read_text())
            self.assertEqual(len(calls),2,report.get('error'));self.assertEqual(report['status'],'failed-infrastructure')
            self.assertEqual(report['numeric_ticks'],120)
            self.assertTrue(all(report['trials'][t['id']]['status']=='not_started' for t in verify.TRIALS[2:]))
            self.assertNotIn('comparison',report)

    def test_reference_rejects_changed_fit_and_file_bounds_before_spawn(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'output';output.mkdir();config,reference,snapshot,_,_=self.gate_fixture(output)
            with patch.object(verify,'REFERENCE',reference),patch('palimpsest.snapshots.read_snapshot',return_value=snapshot):
                verify.load_reference(config)
                snapshot['application']['body_state']['fit_sha256']='0'*64
                with self.assertRaises(ValueError):verify.load_reference(config)
            Path(config['calibration_report']).write_text('{}')
            with self.assertRaisesRegex(ValueError,'calibration report'):verify.load_reference(config)


if __name__=='__main__':unittest.main()
