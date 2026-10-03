"""Pure collection admission/owner fixtures; never native puck evidence."""
import copy
from contextlib import ExitStack, contextmanager
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from palimpsest import puck_profile as puck, puck_learning as learning, puck_teacher as teacher
from palimpsest.records import RunWriter, iter_ticks
from palimpsest.snapshots import state_digest
from test_puck_profile import OWNERSHIP, raw_contacts, world, pair

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_puck_mechanics as gate


def contact(tick):
    return puck.classify_contacts(raw_contacts(tick),OWNERSHIP,tick=tick,time_s=tick*.02)


def packet_arguments():
    before,after=world(),world(1)
    state,_=puck.advance(puck.initialize(before,'teacher-6000'),after,contact(1),[.2,0.])
    env=SimpleNamespace(data=SimpleNamespace(**{key:np.zeros((1,),np.float64)
          for key in ('qpos','qvel','ctrl','qfrc_applied','xfrc_applied')}))
    observation={name:np.zeros((128,128,3),np.uint8) for name in ('cam_left','cam_right')}
    return [env,observation,before,after,puck.project(before,contact(0)),[.2,0.],state,contact(1),
            raw_contacts(1),0.,[0.,False,False,1.,False],'approach','push','teacher-6000']


class CollectionFixtures(unittest.TestCase):
    def test_plan_only_exact_twenty_fresh_teacher_rows_and_budget(self):
        rows=teacher.plan(ROOT)
        self.assertEqual([r['seed'] for r in rows],list(range(6000,6020)))
        self.assertEqual([r['split'] for r in rows],['train']*16+['recorded_dev']*4)
        spec=learning.load_protocol(ROOT)
        self.assertLess(sum(r['max_bytes'] for r in rows)+8*gate.MiB,spec['limits']['teacher']['bytes'])
        self.assertLess(gate.record_estimate(600,1)+16*gate.MiB,rows[0]['max_bytes'])
        with tempfile.TemporaryDirectory() as tmp:
            config={'repo':str(ROOT),'output':str(Path(tmp)/rows[0]['id']),'row':rows[0],
                    'sources':{},'learning_teacher':learning.PROTOCOL_SHA256}
            self.assertEqual(teacher.admit_config(config,ROOT)['rover_pose'],[-1.3,-.6,.3])
            for key,value in [('ticks',1),('start_tick',0),('source_snapshot',{}),('source_output',tmp)]:
                with self.assertRaises(ValueError): teacher.admit_config(config|{key:value},ROOT)
            for change in ({'kind':'policy-replay'},{'seed':6200},{'max_ticks':599},{'max_bytes':1},
                           {'seed':6000.0},{'max_ticks':600.0},{'max_bytes':float(rows[0]['max_bytes'])}):
                with self.assertRaises(ValueError): teacher.admit_config(config|{'row':rows[0]|change},ROOT)
            output=Path(config['output']);output.mkdir();(output/'initial.snp').touch()
            with self.assertRaises(ValueError):teacher.admit_config(config,ROOT)

    def test_decision_retains_original_action_and_independent_cursor_on_disagreement(self):
        own=learning.initial_cursor();before=copy.deepcopy(own);w=world()
        inputs=puck.project(w,contact(0));action,mode,pending=teacher.decide(inputs,w,'approach',own)
        self.assertEqual((action,mode),([.2,0.],'push'));self.assertEqual(own,before)
        wrong=inputs.copy();wrong[0]=np.float32(.4/14)
        with patch.object(puck,'demonstrate',wraps=puck.demonstrate) as expert:
            with self.assertRaises(teacher.SensorModeDisagreement) as caught:
                teacher.decide(wrong,w,'approach',own)
            self.assertEqual(expert.call_count,1)
        evidence=caught.exception.evidence
        self.assertFalse(evidence['executed_interval']);self.assertEqual(evidence['completed_tick'],0)
        self.assertEqual(bytes.fromhex(evidence['inputs']['bytes_hex']),wrong.tobytes())
        np.testing.assert_array_equal(np.frombuffer(bytes.fromhex(evidence['expert_action']['bytes_hex']),np.float64),[.2,0.])
        self.assertEqual((evidence['teacher_mode_after'],evidence['supervisor_mode_after']),('push','approach'))
        self.assertEqual(own,before)

    def test_initial_only_envelope_rejects_restore_later_cursor_and_wrong_identity(self):
        row=teacher.plan(ROOT)[0];w=world();c=contact(0);state=puck.initialize(w,row['case'])
        app=teacher.initial_application(ROOT,row,{}, {'fixture':True},'a'*64,state,w,c,learning.initial_cursor())
        teacher.validate_initial(app,ROOT,row,{}, {'fixture':True},'a'*64,state_digest(app))
        variants=[]
        for key,value in [('kind','puck-hybrid-application-v1'),('teacher_mode','push'),
                          ('supervisor_source_sha256','0'*64),('version',True),('seed',6200),('split','held_out')]:
            variants.append(app|{key:value})
        bad=copy.deepcopy(app);bad['own_supervisor_cursor']['tick']=1;variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError):
                teacher.validate_initial(bad,ROOT,row,{}, {'fixture':True},'a'*64,state_digest(bad))
        with self.assertRaises(ValueError):gate.validate_application(app,row['case'],0,state_digest(app))

    def test_learning_packet_real_record_roundtrip_preserves_float64_label_and_cursor(self):
        args=packet_arguments();pending=learning.prepare(args[4],learning.initial_cursor())
        with self.assertRaises(ValueError):gate.mode_code('approach','teacher-6000')
        self.assertEqual(gate.mode_code('approach','teacher-6000',learning_teacher=True),1)
        for case in ('teacher-06000','teacher-6020','teacher-6200','teacher-positive'):
            with self.assertRaises(ValueError):gate.mode_code('approach',case,learning_teacher=True)
        arrays=gate.packet(*args,learning_pending=pending)
        self.assertEqual(arrays['action'].dtype,np.float64)
        self.assertEqual(arrays['student_inputs'].tobytes(),pending['inputs'].tobytes())
        expected=state_digest({'state':args[6],'world':args[3],'contact':args[7],
                              'teacher_mode':'push','own_supervisor_cursor':pending['after']})
        self.assertEqual(arrays['task_sha256'].tobytes().hex(),expected)
        with tempfile.TemporaryDirectory() as tmp:
            writer=RunWriter(Path(tmp)/'recording',{'fixture':True})
            writer.tick(0,0,**arrays);writer.finish({});writer.close()
            admitted=learning.admit_teacher_rows(iter_ticks(Path(tmp)/'recording'),1)
        self.assertEqual(admitted['targets'].dtype,np.float64)
        self.assertEqual(admitted['final_cursor'],pending['after'])
        old_args=args.copy();old_args[-1]='teacher-positive'
        old=gate.packet(*old_args)
        self.assertEqual(set(old),set(arrays)-{'student_inputs','supervisor_mode_before','supervisor_mode_after'})
        historical=state_digest({'state':args[6],'world':args[3],'contact':args[7],'teacher_mode':'push'})
        self.assertEqual(old['task_sha256'].tobytes().hex(),historical)


    def run_owner_fixture(self, output, *, mismatch=False, event_failure=False):
        """Fake only native resources; use real task, recording and owner loop."""
        from palimpsest.body_profile import effective_control
        import palimpsest.flynn as flynn
        import palimpsest.body_profile as body
        import palimpsest.snapshots as snapshots
        row=teacher.plan(ROOT)[0];spec=gate.protocol(ROOT)
        w=world(rover=(-.63 if mismatch else -.55,0.,0.))
        class Renderer:
            _gl_context=True;_mjr_context=True
            def close(self):self._gl_context=self._mjr_context=None
        class Model:
            def __getstate__(self):return b'fixture-native-model'
        class Environment:
            def __init__(self,**kwargs):
                self.model=Model();self.renderer=Renderer();self.window=self._view_ctx=None
                self.data=SimpleNamespace(time=0.,qpos=np.zeros(1),qvel=np.zeros(1),ctrl=np.zeros(2),
                    qfrc_applied=np.zeros(1),xfrc_applied=np.zeros((1,6)))
                self._t=0;self._obstacle_xy=np.zeros((1,2),np.float32);self.steps=0
            def _get_obs(self):return {name:np.zeros((128,128,3),np.uint8) for name in ('cam_left','cam_right')}
            def step(self,action):
                self.steps+=1;self._t+=1;self.data.time=self._t*.02;self.data.ctrl[:]=effective_control(action)
                return self._get_obs(),0.,False,False,{'dist_to_goal':1.,'stalled':False}
            def close(self):pass
        class Probe:
            def __init__(self,mj,env):
                self.env=env;self.ownership=OWNERSHIP;self.count=0;self.stages=[];self.violations=[]
            def _pairs(self,model,data):return []
            def install(self):pass
            def begin(self,tick):pass
            def end(self):return raw_contacts(self.env._t,[pair('obstacle0','wall_n')])
            def close(self):pass
        env=Environment();snapshot_calls=[]
        def capture(env,observation,*,application):
            snapshot_calls.append(copy.deepcopy(application));return {'fixture':True,'application':application}
        actual_event=RunWriter.event
        def event(writer,kind,**kwargs):
            if event_failure and kind=='puck_interval':raise OSError('fixture event failure')
            return actual_event(writer,kind,**kwargs)
        config={'repo':str(ROOT),'output':str(output),'row':row,'sources':{'fixture':'frozen'},
                'learning_teacher':learning.PROTOCOL_SHA256}
        output.mkdir()
        with ExitStack() as stack:
            stack.enter_context(patch.dict(sys.modules,{'mujoco':SimpleNamespace(__version__='3.3.6',get_mjcb_control=lambda:None)}))
            # A real owner is a fresh process. Isolate that import boundary only
            # inside the reversible module patch; never weaken the product guard.
            sys.modules.pop('torch',None)
            stack.enter_context(patch.dict(gate.os.environ,{'MUJOCO_GL':'egl'}))
            stack.enter_context(patch.object(gate,'teacher_sources',return_value=config['sources']))
            stack.enter_context(patch.object(flynn,'import_upstream',return_value=SimpleNamespace(MuJoCoTwoCamEnv=lambda **kwargs:env)))
            stack.enter_context(patch.object(puck,'install_fixed_model',return_value=spec['profile_identity']))
            reset=stack.enter_context(patch.object(puck,'authored_reset',return_value=puck.initialize(w,row['case'])))
            stack.enter_context(patch.object(gate,'world_from',side_effect=lambda env,goal:copy.deepcopy(w)|{'time_s':env.data.time}))
            stack.enter_context(patch.object(body,'ContactProbe',Probe))
            stack.enter_context(patch.object(snapshots,'capture',side_effect=capture))
            stack.enter_context(patch.object(RunWriter,'event',event))
            code=gate.owner(config)
        reset.assert_called_once_with(env,ROOT,6000,'train','teacher-6000')
        report=json.loads((output/'result.json').read_text())
        events=[json.loads(line) for line in (output/'recording/events.jsonl').read_text().splitlines()]
        self.assertEqual(report['finalization_errors'],[]);self.assertTrue(report['sources_unchanged'])
        self.assertTrue(report['callback_restored']);self.assertTrue(all(r['closed'] for r in report['cleanup']))
        self.assertEqual(env.data.ctrl.tolist(),[0.,0.]);self.assertEqual(len(snapshot_calls),1)
        self.assertEqual(snapshot_calls[0]['own_supervisor_cursor'],learning.initial_cursor())
        self.assertEqual(snapshot_calls[0]['kind'],'puck-teacher-initial-v1')
        return code,report,events,env

    def test_owner_discrepancy_is_retained_before_step_with_zero_executed_ticks(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'teacher-6000'
            code,report,events,env=self.run_owner_fixture(output,mismatch=True)
            self.assertEqual(code,1);self.assertEqual(report['controller_calls'],1)
            self.assertEqual((report['ticks'],report['physics_steps_this_owner'],env.steps),(0,0,0))
            self.assertEqual(report['own_supervisor_cursor'],learning.initial_cursor())
            self.assertEqual(list(iter_ticks(output/'recording')),[])
            evidence=next(e for e in events if e['kind']=='sensor_mode_disagreement')
            self.assertFalse(evidence['executed_interval'])
            self.assertEqual(evidence['inputs']['dtype'],'<f4')
            self.assertEqual(np.frombuffer(bytes.fromhex(evidence['expert_action']['bytes_hex']),np.float64).tolist(),[.2,0.])
            self.assertEqual((evidence['teacher_mode_after'],evidence['supervisor_mode_after']),('push','approach'))

    def test_owner_natural_task_failure_completes_record_then_data_admission_rejects(self):
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)/'teacher-6000'
            code,report,events,env=self.run_owner_fixture(output)
            self.assertEqual(code,0);self.assertEqual(report['completion'],'puck_wall_contact')
            self.assertEqual((report['ticks'],report['controller_calls'],env.steps),(1,1,1))
            manifest=json.loads((output/'recording/manifest.json').read_text())
            self.assertEqual(manifest['status'],'completed');self.assertEqual(manifest['outcome'],'puck_wall_contact')
            rows=list(iter_ticks(output/'recording'))
            self.assertEqual(rows[0]['action'].dtype,np.float64)
            self.assertEqual(report['own_supervisor_cursor']['mode'],'push')
            self.assertEqual(rows[0]['student_inputs'][-1],0.)
            self.assertEqual(manifest['initial_supervisor'],learning.initial_cursor())
            with self.assertRaisesRegex(ValueError,'outcome'):
                learning.admit_record(output/'recording',gate.digest(output/'recording/manifest.json'),6000,'train',ROOT)

    def test_fake_native_owner_isolates_and_restores_preexisting_torch_module(self):
        marker=SimpleNamespace(fixture='preexisting Torch marker; no Torch imported')
        with patch.dict(sys.modules,{'torch':marker}):
            with tempfile.TemporaryDirectory() as tmp:
                code,report,events,env=self.run_owner_fixture(Path(tmp)/'teacher-6000')
                self.assertEqual(code,0)
            self.assertIs(sys.modules['torch'],marker)

    def test_owner_record_failure_does_not_commit_own_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            code,report,events,env=self.run_owner_fixture(Path(tmp)/'teacher-6000',event_failure=True)
            self.assertEqual(code,1);self.assertEqual(env.steps,1)
            self.assertEqual(report['own_supervisor_cursor'],learning.initial_cursor())
            self.assertEqual(report['ticks'],0)
            self.assertEqual(report['last_native_completed_tick'],1)
            self.assertEqual(report['data_time_s'],.02)
            self.assertFalse(any(e['kind']=='puck_interval' for e in events))


    def run_stage_fixture(self, output, *, first_failure=False, natural_failure=False, late=False):
        import collect_puck_teachers as collector
        from palimpsest.storage import StorageBudget
        from test_puck_learning import PuckLearningTests
        spec=gate.protocol(ROOT);fixture=PuckLearningTests();calls=[]
        @contextmanager
        def lease(budget):
            for path in budget.roots:path.mkdir(parents=True)
            yield budget
        def supervisor(command,destination,environment,budget,row,start):
            calls.append(row['seed'])
            self.assertEqual(start,0);self.assertEqual(environment['OMP_NUM_THREADS'],'2')
            config=json.loads(command[-1]);self.assertEqual(config['learning_teacher'],learning.PROTOCOL_SHA256)
            self.assertEqual(set(config),{'repo','output','row','sources','learning_teacher'})
            if first_failure:raise RuntimeError('fixture supervisor admission failure')
            destination.mkdir()
            fixture.fixture(destination/'recording',row['seed'],row['split'])
            outcome='puck_wall_contact' if natural_failure else 'puck_goal'
            manifest_path=destination/'recording/manifest.json'
            manifest=json.loads(manifest_path.read_text());manifest['outcome']=outcome
            manifest_path.write_text(json.dumps(manifest))
            result={'status':'passed','row':row,'ticks':32,'controller_calls':32,'completed_control_tick':32,
                    'own_supervisor_cursor':learning.initial_cursor()|{'tick':32,'mode':'push'},
                    'snapshots':{'initial':{'fixture':True}},'completion':outcome,'final_state':{'reason':outcome}}
            (destination/'result.json').write_text(json.dumps(result))
            return {'passed':True,'fixture':'No real owner or process created'}
        args=SimpleNamespace(repo=ROOT,output=output,retention_root=output.parent,expected_commit='fixture')
        with ExitStack() as stack:
            stack.enter_context(patch.object(collector,'teacher_sources',return_value={'fixture':'frozen'}))
            stack.enter_context(patch.object(collector.subprocess,'check_output',side_effect=['fixture',spec['upstream_commit']]))
            stack.enter_context(patch.object(collector.subprocess,'run'))
            stack.enter_context(patch.object(StorageBudget,'lock',lease))
            stack.enter_context(patch.object(StorageBudget,'check',return_value={}))
            stack.enter_context(patch.object(collector,'supervised_owner',side_effect=supervisor))
            if late:stack.enter_context(patch.object(collector.time,'monotonic',side_effect=[0.]*21+[1501.]))
            code=collector.main(args)
        return code,json.loads((output/'report.json').read_text()),calls

    def test_stage_failure_retains_twenty_rows_and_final_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            code,report,calls=self.run_stage_fixture(Path(tmp)/'stage',first_failure=True)
        self.assertEqual(code,1);self.assertEqual(calls,[6000])
        self.assertEqual([r['status'] for r in report['owners']],['failed']+['not_started']*19)
        self.assertEqual(len(report['sources']),20)
        self.assertTrue(all(e['manifest_sha256'] is None for e in report['sources']))
        self.assertEqual(report['admission']['status'],'not_started')
        self.assertTrue(report['sources_unchanged']);self.assertEqual(report['finalization_errors'],[])
        self.assertIn('retained_inventory',report);self.assertIn('retention_storage',report)

    def test_natural_outcomes_complete_all_twenty_but_admission_blocks_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            code,report,calls=self.run_stage_fixture(Path(tmp)/'stage',natural_failure=True)
        self.assertEqual(code,1);self.assertEqual(calls,list(range(6000,6020)))
        self.assertEqual([r['status'] for r in report['owners']],['completed']*20)
        self.assertEqual([r['outcome'] for r in report['owners']],['puck_wall_contact']*20)
        self.assertEqual(report['admission']['status'],'failed')
        self.assertEqual([r['status'] for r in report['admission']['rows']],['failed']*20)
        self.assertTrue(all('outcome' in r['error'] for r in report['admission']['rows']))

    def test_fixture_success_report_is_exact_trainer_handoff_and_re_admits_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            code,report,calls=self.run_stage_fixture(Path(tmp)/'stage')
            self.assertEqual(code,0);self.assertEqual(report['status'],'passed')
            self.assertEqual(report['learning_protocol_sha256'],learning.PROTOCOL_SHA256)
            self.assertEqual(report['source_hashes'],{'fixture':'frozen'})
            self.assertEqual(report['admission']['status'],'passed');self.assertNotIn('data',report['admission'])
            self.assertTrue(all(set(e)=={'seed','split','path','manifest_sha256'} for e in report['sources']))
            for entry in report['sources']:
                self.assertEqual(entry['manifest_sha256'],gate.digest(Path(entry['path'])/'manifest.json'))
            self.assertEqual(learning.admit_batch(report['sources'],ROOT)['status'],'passed')

    def test_late_final_validation_cannot_publish_passed_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            code,report,calls=self.run_stage_fixture(Path(tmp)/'stage',late=True)
        self.assertEqual(calls,list(range(6000,6020)))
        self.assertEqual(report['admission']['status'],'passed')
        self.assertEqual(code,1);self.assertEqual(report['status'],'failed')
        self.assertEqual(report['elapsed_seconds'],1501.)
        self.assertTrue(any('deadline' in error for error in report['finalization_errors']))
        self.assertTrue(report['sources_unchanged']);self.assertIn('retained_inventory',report)


if __name__=='__main__':unittest.main()
