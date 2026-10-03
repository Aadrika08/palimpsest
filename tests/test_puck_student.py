"""Pure student/owner fixtures; fake native/model resources are not rollout evidence."""
import copy
from contextlib import ExitStack
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from palimpsest import puck_student as student, puck_learning as learning, puck_model, puck_profile as puck
from palimpsest.records import RunWriter, iter_ticks
from palimpsest.snapshots import state_digest
from test_puck_profile import OWNERSHIP, raw_contacts, world, pair
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import verify_puck_mechanics as gate


def contact(tick):
    return puck.classify_contacts(raw_contacts(tick),OWNERSHIP,tick=tick,time_s=tick*.02)


def identity(seed=21):
    e=student.model_entry(ROOT,seed)
    return {'training_seed':seed,'training_report_sha256':e['files']['report.json'],
            'checkpoint_sha256':e['files']['checkpoint.npz'],'protocol_sha256':e['files']['protocol.json'],
            'learning_protocol_sha256':learning.PROTOCOL_SHA256,
            'supervisor_source_sha256':hashlib.sha256((ROOT/'src/palimpsest/puck_learning.py').read_bytes()).hexdigest()}


class StudentFixtures(unittest.TestCase):
    def test_fixed_plan_and_exact_envelope_before_any_model_or_native_load(self):
        rows=student.plan(ROOT)
        self.assertEqual([r['kind'] for r in rows],['root','native-continuation','action-replay','policy-replay'])
        self.assertEqual(sum(r['max_bytes'] for r in rows),224*1024**2)
        with tempfile.TemporaryDirectory() as tmp,patch.object(student,'admit_bundle',return_value=(Path(tmp),identity())):
            config={'repo':str(ROOT),'output':str(Path(tmp)/rows[0]['id']),'row':rows[0],
                    'sources':{},'learning_student':student.PROTOCOL_SHA256,'bundle_root':tmp}
            self.assertEqual(student.admit_config(config,ROOT)['id'],rows[0]['case'])
            for change in ({'seed':6000.0},{'model_seed':22},{'max_ticks':120.0},{'split':'closed_loop_dev'},{'seed':6200}):
                with self.assertRaises(ValueError):student.admit_config(config|{'row':rows[0]|change},ROOT)
            for change in ({'learning_teacher':learning.PROTOCOL_SHA256},{'ticks':1},{'learning_student':'0'*64}):
                with self.assertRaises(ValueError):student.admit_config(config|change,ROOT)
            receipt={'file':'tick1.snp','sha256':'a'*64,'bytes':100,'tick':1,'application_sha256':'b'*64,'world':{},'contact':{}}
            derived=config|{'row':rows[1],'output':str(Path(tmp)/rows[1]['id']),
                'source_output':str(Path(tmp)/rows[0]['id']),'source_snapshot':receipt,'start_tick':1,'ticks':4}
            student.admit_config(derived,ROOT)
            for changed in ({'file':'../initial.snp'},{'tick':1.0},{'bytes':0},{'sha256':'x'*64}):
                with self.assertRaises(ValueError):student.admit_config(derived|{'source_snapshot':receipt|changed},ROOT)
            with self.assertRaises(ValueError):student.admit_config(derived|{'start_tick':1.0},ROOT)

    def test_decision_uses_before_mode_once_and_saturation_reaches_real_task_boundary(self):
        inputs=puck.project(world(),contact(0));own=learning.initial_cursor();before=copy.deepcopy(own)
        with patch.object(puck,'demonstrate',side_effect=AssertionError('No expert at inference')),\
             patch.object(puck_model,'predict',return_value=np.array([.4,-.4],np.float64)) as predict:
            action,pending=student.decide(inputs,own,object())
        self.assertEqual(own,before);self.assertEqual(predict.call_count,1)
        self.assertEqual(predict.call_args.args[1].dtype,np.float32)
        self.assertEqual(predict.call_args.args[1].tolist(),[*inputs.tolist(),0.])
        self.assertEqual(pending['after']['mode'],'push')
        state,_=puck.advance(puck.initialize(world(),'fixture'),world(1),contact(1),action.tolist())
        after=learning.commit(own,pending,state['tick']);self.assertEqual(after['mode'],'push')
        self.assertEqual(own,before)
        with self.assertRaises(ValueError):student.action(np.array([.4,0.],np.float32).astype(np.float64))
        for value in (np.array([np.nan,0.]),np.zeros(2,np.float32),np.zeros((1,2)),np.array([.4000000001,0.])):
            with patch.object(puck_model,'predict',return_value=value):
                with self.assertRaises(ValueError):student.decide(inputs,own,object())
            self.assertEqual(own,before)

    def test_real_record_roundtrip_action_replay_and_policy_staging(self):
        inputs=puck.project(world(),contact(0));own=learning.initial_cursor()
        with patch.object(puck_model,'predict',return_value=np.array([.2,0.],np.float64)):
            action,pending=student.decide(inputs,own,object())
        state,_=puck.advance(puck.initialize(world(),'student-6000-seed21'),world(1),contact(1),action.tolist())
        env=SimpleNamespace(data=SimpleNamespace(**{k:np.zeros(1) for k in ('qpos','qvel','ctrl','qfrc_applied','xfrc_applied')}))
        obs={k:np.zeros((128,128,3),np.uint8) for k in ('cam_left','cam_right')}
        arrays=gate.packet(env,obs,world(),world(1),inputs,action,state,contact(1),raw_contacts(1),0.,
                           [0.,0.,0.,1.,0.],None,None,'student-6000-seed21',student_pending=pending)
        self.assertFalse(any(k.startswith('teacher') for k in arrays))
        with tempfile.TemporaryDirectory() as tmp:
            writer=RunWriter(Path(tmp)/'recording',{'fixture':True});writer.tick(0,0,**arrays);writer.finish({});writer.close()
            recorded=list(iter_ticks(Path(tmp)/'recording'))[0]
        self.assertIsInstance(recorded['supervisor_mode_before'],np.uint8)
        with patch.object(puck_model,'predict',side_effect=AssertionError('Action replay predicts nothing')),\
             patch.object(puck,'demonstrate',side_effect=AssertionError('No teacher')):
            replay,staged=student.decide(inputs,own,None,recorded)
        self.assertEqual(replay.tobytes(),action.tobytes());self.assertEqual(state_digest(staged),state_digest(pending))
        for change in ({'supervisor_mode_before':np.uint8(1)},{'supervisor_mode_after':np.array([1],np.uint8)},
                       {'action':action.astype(np.float32)},{'teacher_mode_after':np.uint8(2)}):
            with self.assertRaises(ValueError):student.decide(inputs,own,None,recorded|change)
        bad=copy.deepcopy(pending);bad['after']['mode']='approach'
        with self.assertRaises(ValueError):learning.commit(own,bad,1)
        self.assertEqual(own,learning.initial_cursor())

    def test_snapshot_pins_and_restored_cursor_reproduce_policy_input(self):
        row=student.plan(ROOT)[0];w=world();c=contact(0);state=puck.initialize(w,row['case']);pins=identity()
        app=student.application(ROOT,row,{}, {'fixture':True},'a'*64,pins,state,w,c,learning.initial_cursor())
        self.assertFalse(any(k.startswith('teacher') for k in app))
        student.validate_application(app,ROOT,row,{}, {'fixture':True},'a'*64,pins,0,state_digest(app))
        variants=[app|{key:value} for key,value in [('kind','puck-teacher-initial-v1'),('teacher_mode','approach'),
                  ('student_source_sha256','0'*64),('seed',6000.0),('source_hashes',{'bad':'source'})]]
        bad=copy.deepcopy(app);bad['own_supervisor_cursor']['tick']=1;variants.append(bad)
        bad=copy.deepcopy(app);bad['model_identity']['checkpoint_sha256']='0'*64;variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError):student.validate_application(bad,ROOT,row,{}, {'fixture':True},'a'*64,pins,0,state_digest(bad))
        with self.assertRaises(ValueError):gate.validate_application(app,row['case'],0,state_digest(app))
        with patch.object(puck_model,'predict',return_value=np.array([.2,0.])):
            a,pending=student.decide(app['inputs'],app['own_supervisor_cursor'],object())
        state,_=puck.advance(state,world(1),contact(1),a.tolist());cursor=learning.commit(app['own_supervisor_cursor'],pending,1)
        later=student.application(ROOT,row,{}, {'fixture':True},'a'*64,pins,state,world(1),contact(1),cursor)
        with patch.object(puck_model,'predict',return_value=np.array([.2,0.])):
            a,one=student.decide(puck.project(world(1),contact(1)),cursor,object())
            b,two=student.decide(later['inputs'],later['own_supervisor_cursor'],object())
        self.assertEqual(a.tobytes(),b.tobytes());self.assertEqual(state_digest(one),state_digest(two))

    def test_bundle_pin_failure_precedes_numeric_reader(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'seed-21';path.mkdir()
            for name in ('protocol.json','report.json','checkpoint.npz'):(path/name).write_bytes(b'fixture')
            entry={'seed':21,'directory':'seed-21','files':{n:'0'*64 for n in ('protocol.json','report.json','checkpoint.npz')}}
            with patch.object(student,'model_entry',return_value=entry),patch.object(puck_model,'read_bundle') as reader:
                with self.assertRaises(ValueError):student.admit_bundle(ROOT,tmp,21)
                reader.assert_not_called()

    def run_owner(self, output, *, bad_action=False, event_failure=False, bad_restore=False, derivative=None, source=None,
                  development_row=None, initial_reference=None, rng_mismatch=False):
        import palimpsest.flynn as flynn
        import palimpsest.body_profile as body
        import palimpsest.snapshots as snapshots
        from palimpsest.body_profile import effective_control
        spec=gate.protocol(ROOT);row=development_row or student.plan(ROOT)[derivative if derivative is not None else 1 if bad_restore else 0]
        pins=identity(row['model_seed']);model=object()
        class Renderer:
            _gl_context=True;_mjr_context=True
            def close(self):self._gl_context=self._mjr_context=None
        class Environment:
            def __init__(self):
                self.model=SimpleNamespace(__getstate__=lambda:b'fixture-model');self.renderer=Renderer();self.window=self._view_ctx=None
                self.data=SimpleNamespace(time=0.,qpos=np.zeros(1),qvel=np.zeros(1),ctrl=np.zeros(2),qfrc_applied=np.zeros(1),xfrc_applied=np.zeros((1,6)))
                self._t=0;self.steps=0;self._obstacle_xy=np.zeros((1,2),np.float32);self._puck_bindings={}
            def _get_obs(self):return {k:np.zeros((128,128,3),np.uint8) for k in ('cam_left','cam_right')}
            def step(self,action):
                self.steps+=1;self._t+=1;self.data.time=self._t*.02;self.data.ctrl[:]=effective_control(action)
                return self._get_obs(),0.,False,False,{'dist_to_goal':1.,'stalled':False}
            def close(self):pass
        class Model:
            def __getstate__(self):return b'fixture-model'
        env=Environment();env.model=Model()
        class Probe:
            def __init__(self,mj,env):self.env=env;self.ownership=OWNERSHIP;self.count=0;self.stages=[];self.violations=[]
            def _pairs(self,*args):return []
            def install(self):pass
            def begin(self,tick):pass
            def end(self):return raw_contacts(self.env._t,[pair('base_geom','obstacle0')])
            def close(self):pass
        def current(env,goal):
            if development_row is not None:
                from test_puck_development import initial_world
                value=initial_world(row);value['time_s']=env._t*.02
                if env._t:value['puck_xyz']=[*value['goal_xy'],.062]
                return value
            return world(env._t,puck=(1. if env._t else 0.,0.,.062))
        apps=[]
        def capture(env,obs,*,application):
            apps.append(copy.deepcopy(application))
            if development_row is not None:
                from test_puck_development import native_fixture
                import random
                snapshot=native_fixture(application,row)
                snapshot['rng']['python']=random.getstate();snapshot['rng']['numpy']=np.random.get_state()
                if rng_mismatch:snapshot['rng']['spaces']['action_space']={'fixture':'different'}
                return snapshot
            return {'fixture':True,'application':application}
        actual_event=RunWriter.event
        def event(writer,kind,**kwargs):
            if event_failure and kind=='puck_interval':raise OSError('fixture record staging failure')
            return actual_event(writer,kind,**kwargs)
        config={'repo':str(ROOT),'output':str(output),'row':row,'sources':{'fixture':'source'},
                'learning_student':student.PROTOCOL_SHA256,'bundle_root':str(output.parent/'models')}
        if development_row is not None:
            from palimpsest import puck_development as development
            config.pop('learning_student');config.update(learning_student_development=development.PROTOCOL_SHA256,initial_reference=initial_reference)
        if bad_restore:
            receipt={'file':'tick1.snp','bytes':100,'sha256':'a'*64,'application_sha256':'b'*64,'tick':1,'world':{},'contact':{}}
            config.update(source_output=str(output.parent/row['case']),source_snapshot=receipt,start_tick=1,ticks=4)
        if derivative is not None:
            source_out,source_report,source_apps=source
            boundary='tick1' if derivative==1 else 'initial'
            receipt=source_report['snapshots'][boundary]
            restored_app=source_apps[1 if derivative==1 else 0]
            config.update(source_output=str(source_out),source_snapshot=receipt,start_tick=receipt['tick'],
                          ticks=4 if derivative==1 else source_report['ticks'])
        def restore_fixture(snapshot,actual_env):
            app=copy.deepcopy(snapshot['application']);actual_env._t=app['state']['tick'];actual_env.data.time=app['world']['time_s']
            actual_env.data.ctrl[:]=[.4,.4] if actual_env._t else [0.,0.]
            return actual_env._get_obs(),app
        output.mkdir();actual_read_json=gate.read_json;actual_version=importlib.metadata.version
        with ExitStack() as stack:
            import random
            py_rng,np_rng=random.getstate(),np.random.get_state()
            stack.callback(random.setstate,py_rng);stack.callback(np.random.set_state,np_rng)
            stack.enter_context(patch.dict(sys.modules,{'mujoco':SimpleNamespace(__version__='3.3.6',get_mjcb_control=lambda:None)}))
            sys.modules.pop('torch',None)
            stack.enter_context(patch.object(gate.platform,'python_version',return_value=spec['runtime']['python']))
            stack.enter_context(patch.object(importlib.metadata,'version',side_effect=lambda name: '2.9.0' if name=='torch' else actual_version(name)))
            stack.enter_context(patch.dict(gate.os.environ,{'MUJOCO_GL':'egl'}))
            stack.enter_context(patch.object(gate,'development_sources' if development_row is not None else 'student_sources',return_value=config['sources']))
            stack.enter_context(patch.object(student,'admit_bundle',side_effect=lambda root,bundle,seed: (Path(bundle),identity(seed))))
            load=stack.enter_context(patch.object(student,'load',return_value=(model,pins)))
            stack.enter_context(patch.object(student,'check_parameters',return_value=pins))
            predict=stack.enter_context(patch.object(puck_model,'predict',return_value=np.array([np.nan if bad_action else .2,0.],np.float64)))
            expert=stack.enter_context(patch.object(puck,'demonstrate',side_effect=AssertionError('Student must not call teacher')))
            stack.enter_context(patch.object(flynn,'import_upstream',return_value=SimpleNamespace(MuJoCoTwoCamEnv=lambda **kw:env)))
            stack.enter_context(patch.object(puck,'install_fixed_model',return_value=spec['profile_identity']))
            stack.enter_context(patch.object(puck,'authored_reset',return_value=puck.initialize(current(env,None),row['case'])))
            stack.enter_context(patch.object(gate,'world_from',side_effect=current))
            stack.enter_context(patch.object(body,'ContactProbe',Probe));stack.enter_context(patch.object(snapshots,'capture',side_effect=capture))
            stack.enter_context(patch.object(RunWriter,'event',event));restore=stack.enter_context(patch.object(snapshots,'restore',side_effect=restore_fixture))
            stack.enter_context(patch.object(puck,'_fixed_bindings',return_value=({},{})))
            if derivative is not None:
                stack.enter_context(patch.object(gate,'read_bounded_snapshot',return_value={'application':restored_app}))
            if bad_restore:
                stack.enter_context(patch.object(gate,'read_bounded_snapshot',return_value={'application':{'kind':'puck-teacher-initial-v1'}}))
                stack.enter_context(patch.object(gate,'read_json',side_effect=lambda path,*args: {} if Path(path).name=='manifest.json' else actual_read_json(path,*args)))
                stack.enter_context(patch.object(student,'admit_source',return_value=10))
            code=gate.owner(config);expert.assert_not_called()
            if derivative is None:restore.assert_not_called()
            else:restore.assert_called_once()
            load.assert_called_once_with(ROOT,config['bundle_root'],row['model_seed'])
        r=json.loads((output/'result.json').read_text())
        self.assertEqual(r['finalization_errors'],[]);self.assertTrue(r['sources_unchanged']);self.assertTrue(r['callback_restored'])
        self.assertTrue(all(x['closed'] for x in r['cleanup']));self.assertEqual(env.data.ctrl.tolist(),[0.,0.])
        self.assertNotIn('controller_calls',r);self.assertNotIn('final_teacher_mode',r)
        return code,r,env,apps,predict.call_count

    def test_owner_actual_branch_keeps_teacher_fields_absent_and_commits_after_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/student.plan(ROOT)[0]['id'];code,r,env,apps,calls=self.run_owner(out)
            self.assertEqual(code,0);self.assertEqual((r['ticks'],r['model_calls'],env.steps,calls),(10,10,10,10))
            self.assertEqual(r['completion'],'puck_goal');self.assertEqual(r['own_supervisor_cursor']['tick'],10)
            self.assertEqual([a['own_supervisor_cursor']['tick'] for a in apps],[0,1])
            rows=list(iter_ticks(out/'recording'));self.assertEqual(len(rows),10)
            self.assertTrue(all(not any(k.startswith('teacher') for k in row) for row in rows))
            events=[json.loads(line) for line in (out/'recording/events.jsonl').read_text().splitlines()]
            self.assertTrue(all(not any(k.startswith('teacher') for k in row) for row in events))
            manifest=json.loads((out/'recording/manifest.json').read_text());self.assertEqual(manifest['schema'],'puck-student-v1')
            student.admit_source(manifest,ROOT,student.plan(ROOT)[2],{'fixture':'source'},identity())

    def test_owner_invalid_action_and_record_failure_keep_completed_cursor_uncommitted(self):
        for bad_action,event_failure in ((True,False),(False,True)):
            with self.subTest(bad_action=bad_action),tempfile.TemporaryDirectory() as tmp:
                code,r,env,_,calls=self.run_owner(Path(tmp)/student.plan(ROOT)[0]['id'],bad_action=bad_action,event_failure=event_failure)
                self.assertEqual(code,1);self.assertEqual(r['own_supervisor_cursor'],learning.initial_cursor())
                self.assertEqual(r['completed_control_tick'],0);self.assertEqual(calls,1)
                self.assertEqual(env.steps,0 if bad_action else 1)

    def test_owner_native_and_action_policy_replays_match_every_real_record_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);rows=student.plan(ROOT);out=root/rows[0]['id']
            code,original,_,apps,_=self.run_owner(out);self.assertEqual(code,0)
            reference=list(iter_ticks(out/'recording'))
            for index in (1,2,3):
                destination=root/rows[index]['id']
                code,result,env,_,calls=self.run_owner(destination,derivative=index,source=(out,original,apps))
                self.assertEqual(code,0,result.get('error'));self.assertEqual(result['model_calls'],0 if index==2 else 4 if index==1 else 10)
                self.assertEqual(calls,result['model_calls']);self.assertEqual(result['physics_steps_this_owner'],env.steps*10)
                actual=list(iter_ticks(destination/'recording'));expected=reference[1:5] if index==1 else reference
                self.assertEqual(len(actual),len(expected))
                for a,b in zip(expected,actual):gate.same_row(a,b)

    def test_fixture_restores_preloaded_torch_and_host_version(self):
        marker=SimpleNamespace(fixture='not actual Torch');version=gate.platform.python_version()
        with patch.dict(sys.modules,{'torch':marker}),patch.object(gate.platform,'python_version',return_value='3.11.16'),\
             patch.object(importlib.metadata,'version',return_value='2.9.0+cpu'):
            with tempfile.TemporaryDirectory() as tmp:
                code,_,_,_,_=self.run_owner(Path(tmp)/student.plan(ROOT)[0]['id'])
            self.assertEqual(code,0);self.assertIs(sys.modules['torch'],marker)
            self.assertEqual(gate.platform.python_version(),'3.11.16')
            self.assertEqual(importlib.metadata.version('torch'),'2.9.0+cpu')
        self.assertEqual(gate.platform.python_version(),version)

    def test_real_snapshot_restore_requires_matching_torch_profile_and_stages_rng(self):
        import random
        import palimpsest.snapshots as snapshots
        class NativeBoundary(RuntimeError):pass
        class FakeData:
            def __new__(cls):raise NativeBoundary('No native deserialization in pure fixture')
        staged=[]
        fake_torch=SimpleNamespace(from_numpy=lambda value:value.copy(),
            Generator=lambda device:SimpleNamespace(set_state=lambda value:staged.append((device,value.copy()))))
        native=b'fixture';env=SimpleNamespace()
        rng={'python':random.getstate(),'numpy':np.random.get_state(),'environment':None,
             'environment_seed':None,'spaces':{},'torch_cpu':np.array([1,2,3,4],np.uint8),'torch_cuda':[]}
        snp={'schema_version':snapshots.SCHEMA_VERSION,'identity':{'torch':{'fixture':'same loaded profile'}},
             'native_data':native,'native_sha256':hashlib.sha256(native).hexdigest(),'integration_enum':0,
             'integration':np.zeros(1),'environment':{'values':{},'absent':list(snapshots.ENV_STATE)},
             'policy':None,'teacher':None,'rng':rng,'observation':{},'application':{}}
        def current(*args):return {'torch':{'fixture':'same loaded profile'} if sys.modules.get('torch') is not None else None}
        with patch.dict(sys.modules,{'mujoco':SimpleNamespace(MjData=FakeData)}),patch.object(snapshots,'_identity',side_effect=current):
            sys.modules.pop('torch',None)
            with self.assertRaisesRegex(ValueError,'runtime/profile identity'):
                snapshots.restore(snp,env)
            self.assertEqual(staged,[])
            sys.modules['torch']=fake_torch
            with self.assertRaises(NativeBoundary):snapshots.restore(snp,env)
        self.assertEqual(len(staged),1);self.assertEqual(staged[0][0],'cpu')
        self.assertEqual(staged[0][1].tobytes(),rng['torch_cpu'].tobytes());self.assertEqual(vars(env),{})

    def test_live_parameter_guard_checks_exact_checkpoint_values(self):
        arrays={name:np.zeros(shape,np.float32) for name,shape in puck_model.SHAPES.items()}
        class Tensor:
            def __init__(self,value):self.value=value
            def detach(self):return self
            def cpu(self):return self
            def numpy(self):return self.value
        model=SimpleNamespace(state_dict=lambda:{k:Tensor(v) for k,v in arrays.items()})
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);(path/'checkpoint.npz').write_bytes(puck_model.checkpoint_bytes(arrays))
            with patch.object(student,'admit_bundle',return_value=(path,identity())):
                student.check_parameters(model,ROOT,path,21)
                arrays['0.bias'][0]=np.float32(-0.)
                with self.assertRaisesRegex(ValueError,'Live student parameters'):
                    student.check_parameters(model,ROOT,path,21)

    def test_owner_rejects_historical_application_before_restore(self):
        with tempfile.TemporaryDirectory() as tmp:
            code,r,env,_,calls=self.run_owner(Path(tmp)/student.plan(ROOT)[1]['id'],bad_restore=True)
            self.assertEqual(code,1);self.assertEqual((env.steps,calls),(0,0))
            self.assertIn('snapshot identity/schema',r['error']['message'])


if __name__=='__main__':unittest.main()
