"""Fake native boundaries and real disk transactions; no native qualification."""
import copy
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import random
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from palimpsest import puck_on_policy as adapter, puck_learning as learning
from palimpsest import puck_model, puck_teacher, puck_profile as puck, snapshots
from palimpsest.records import RunWriter
from test_puck_profile import OWNERSHIP, raw_contacts

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import verify_puck_mechanics as gate


class Model:
    def __init__(self):
        self.jnt_range = np.zeros((1, 2)); self.geom_rgba = np.ones((1, 4)); self.site_pos = np.zeros((1, 3))
    def __getstate__(self):
        return json.dumps({k: getattr(self, k).tolist() for k in snapshots.MUTABLE_MODEL_ARRAYS}).encode()
    def __setstate__(self, raw):
        for k, v in json.loads(raw).items(): setattr(self, k, np.array(v))


class NativeIntervalTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(adapter, 'capture_query_state', None)), 'native capture seam missing')
        self.assertTrue(callable(getattr(adapter, 'PuckIntervalWriter', None)), 'durable interval writer missing')
        self.assertTrue(callable(getattr(gate, 'on_policy_interval', None)), 'actual interval seam missing')
        py_rng,np_rng=random.getstate(),np.random.get_state()
        self.addCleanup(random.setstate,py_rng);self.addCleanup(np.random.set_state,np_rng)
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'intervals'
        self.own = learning.initial_cursor(); self.mode = 'approach'
        self.world = {'time_s': 0., 'rover_pose': [-.55, 0., 0.], 'puck_xyz': [0., 0., .062],
                      'puck_velocity_xy': [0., 0.], 'goal_xy': [1., 0.]}
        self.sensors = np.array([.55/14, 0, 1.55/14, 0, 0, 0, 0, 0], np.float32)
        self.prediction = np.array([.125, -.25], np.float64)
        self.observation = {k: np.zeros((128, 128, 3), np.uint8) for k in ('cam_left','cam_right')}
        self.env = SimpleNamespace(model=Model(), window=None, _view_ctx=None,
            np_random=np.random.default_rng(2), _np_random_seed=2, _t=0,
            _puck_bindings={'fixture': 1}, _puck_profile_identity={'fixture': 2}, _puck_reset_seed=17,
            _obstacle_xy=np.zeros((1,2),np.float32), action_space=SimpleNamespace(_np_random=np.random.default_rng(3)),
            observation_space=SimpleNamespace(_np_random=np.random.default_rng(4)),
            data=SimpleNamespace(__getstate__=lambda: b'native fixture', time=0.,
                **{k: np.zeros(2,np.float64) for k in ('qpos','qvel','ctrl','qfrc_applied','xfrc_applied')}))
        self.fake_mj = SimpleNamespace(__version__='3.3.6', MjModel=Model, get_mjcb_control=lambda: None,
            mjtState=SimpleNamespace(mjSTATE_INTEGRATION=1), mj_stateSize=lambda *a: 2,
            mj_getState=lambda model,data,value,kind: value.fill(0))
        self.capture_modules = patch.dict(sys.modules, {'mujoco': self.fake_mj})
        self.capture_modules.start(); self.addCleanup(self.capture_modules.stop)
        self.app = {'fixture': 'application'}

    def staged(self, tick=0):
        own = copy.deepcopy(self.own)
        for completed in range(1,tick+1):
            own=learning.commit(own,learning.prepare(self.sensors,own),completed)
        with patch.object(puck_model, 'predict', return_value=self.prediction):
            return adapter.stage_interval(self.sensors, self.world, own['mode'], own, object(),
                terminal_reason=None, capture_query_state=lambda: adapter.capture_query_state(self.env, self.observation, application=self.app))

    def payload(self, staged):
        from palimpsest.body_profile import effective_control
        arrays = {k: v for k,v in staged['row'].items() if k not in ('episode','tick')}
        tick=staged['row']['tick'];before={**self.world,'time_s':tick*.02};after={**self.world,'time_s':(tick+1)*.02}
        def contact(n):return puck.classify_contacts(raw_contacts(n),OWNERSHIP,tick=n,time_s=n*.02)
        state=puck.initialize(self.world,'fixture')
        for n in range(1,tick+1):state,_=puck.advance(state,{**self.world,'time_s':n*.02},contact(n),self.prediction.tolist())
        next_state,reward=puck.advance(state,after,contact(tick+1),self.prediction.tolist())
        event = {'completed_tick': tick+1, 'state_before':state,'world_before':before,'contact_before':contact(tick),
                 'state':next_state,'world':after,'contact':contact(tick+1),'reward':reward,
                 'supervisor_mode_before': staged['own_pending']['before']['mode'],
                 'supervisor_mode_after': staged['own_pending']['after']['mode'],
                 'teacher_query_mode_before': staged['teacher_mode_before'],
                 'teacher_query_mode_after': staged['teacher_mode_after']}
        normalized=json.loads(adapter._canonical_bytes(event,'fixture'))
        task={'state':normalized['state'],'world':normalized['world'],'contact':normalized['contact'],
              'own_supervisor_cursor':{**staged['own_pending']['after'],'tick':tick+1}}
        arrays.update(qpos=np.zeros(2,np.float64),ctrl=np.asarray(effective_control(self.prediction.tolist()),np.float64),
            world_before=gate.world_array(before),world_after=gate.world_array(after),reward=np.asarray(reward,np.float64),
            native_completed_tick=np.asarray(tick+1,np.int64),native_data_time_s=np.asarray(after['time_s'],np.float64),
            task_sha256=np.frombuffer(bytes.fromhex(snapshots.state_digest(task)),np.uint8))
        return arrays,event

    def publish(self, writer, tick=0):
        staged=self.staged(tick); arrays,event=self.payload(staged)
        return writer.publish(staged, arrays, event, completed_tick=tick+1)

    def test_capture_reuses_native_snapshot_without_refreshing_observation_or_rng(self):
        before = snapshots.state_digest({'py':random.getstate(), 'np':np.random.get_state(), 'env':self.env.np_random.bit_generator.state})
        with patch.object(snapshots, 'capture', wraps=snapshots.capture) as capture:
            state=adapter.capture_query_state(self.env,self.observation,application=self.app)
        self.assertEqual(capture.call_count,1)
        self.assertEqual(set(state), adapter._QUERY_STATE_FIELDS)
        self.assertEqual(state['native_state']['full_model'],self.env.model.__getstate__())
        self.assertEqual(state['native_state']['snapshot']['native_data'],b'native fixture')
        self.assertEqual(before,snapshots.state_digest({'py':random.getstate(), 'np':np.random.get_state(), 'env':self.env.np_random.bit_generator.state}))
        self.observation['cam_left'][:]=1
        self.assertEqual(int(state['observation']['cam_left'][0,0,0]),0)
        self.env.model.site_pos[:]=1
        self.assertNotEqual(snapshots.state_digest(state),snapshots.state_digest(adapter.capture_query_state(self.env,self.observation,application=self.app)))

    def test_query_mutations_are_detected_for_exact_native_wrapper_model_observation_and_rng(self):
        changes = [lambda: setattr(self.env.data,'__getstate__',lambda:b'changed'),
                   lambda: self.env.model.jnt_range.fill(1), lambda: self.env.model.geom_rgba.fill(0),
                   lambda: self.env.model.site_pos.fill(2), lambda: self.env._puck_bindings.update(fixture=3),
                   lambda: self.env._obstacle_xy.fill(1), lambda: self.observation['cam_left'].fill(1),
                   lambda: random.random(), lambda: np.random.random(), lambda: self.env.np_random.random(),
                   lambda: self.env.action_space._np_random.random()]
        original=puck_teacher.decide
        for change in changes:
            with self.subTest(change=change):
                def teacher(*args):
                    result=original(*args);change();return result
                with patch.object(puck_teacher,'decide',side_effect=teacher):
                    with self.assertRaisesRegex(ValueError,'Teacher query changed'):
                        self.staged()

    def test_uninitialized_rng_and_callback_are_rejected_before_capture(self):
        for attr,value in (('np_random',None),):
            setattr(self.env,attr,value)
            with patch.object(snapshots,'capture') as capture:
                with self.assertRaises(ValueError):adapter.capture_query_state(self.env,self.observation,application=self.app)
                capture.assert_not_called()
        self.env.np_random=np.random.default_rng(2);self.fake_mj.get_mjcb_control=lambda: object()
        with self.assertRaises(ValueError):adapter.capture_query_state(self.env,self.observation,application=self.app)

    def test_fake_torch_and_recursive_space_rng_changes_are_observed_without_import(self):
        cpu=np.array([1,2,3],np.uint8)
        tensor=SimpleNamespace(cpu=lambda:SimpleNamespace(numpy=lambda:cpu))
        fake_torch=SimpleNamespace(get_rng_state=lambda:tensor,cuda=SimpleNamespace(is_initialized=lambda:False))
        child=SimpleNamespace(_np_random=np.random.default_rng(7))
        self.env.observation_space.spaces={'child':child}
        with patch.dict(sys.modules,{'torch':fake_torch}),patch.object(snapshots,'_torch_profile',return_value={'fixture':True}):
            before=adapter.capture_query_state(self.env,self.observation,application=self.app)
            cpu[0]=9;child._np_random.random()
            after=adapter.capture_query_state(self.env,self.observation,application=self.app)
        self.assertNotEqual(snapshots.state_digest(before['torch_rng']),snapshots.state_digest(after['torch_rng']))
        self.assertNotEqual(snapshots.state_digest(before['space_rng']),snapshots.state_digest(after['space_rng']))
        self.assertEqual(before['torch_rng']['cpu'].tolist(),[1,2,3])

    def test_query_capture_exceeding_8_mib_is_rejected(self):
        self.env.data.__getstate__=lambda:b'x'*(8*1024**2)
        with self.assertRaisesRegex(ValueError,'8 MiB'):
            adapter.capture_query_state(self.env,self.observation,application=self.app)

    def test_native_probe_and_packet_publication_failures_stop_before_cursors(self):
        from palimpsest.body_profile import effective_control
        for fault in ('probe','tick','event','fsync'):
            with self.subTest(fault=fault),tempfile.TemporaryDirectory() as temporary:
                self.env._t=0;self.env.data.time=0.
                path=Path(temporary)/'intervals';writer=adapter.PuckIntervalWriter(path,max_bytes=2*1024**2)
                closed=[]
                def step(action):
                    self.env._t=1;self.env.data.time=.02;self.env.data.ctrl[:]=effective_control(action)
                    return self.observation,0.,False,False,{'dist_to_goal':1.,'stalled':False}
                self.env.step=step
                def end():
                    if fault=='probe':raise OSError('probe end')
                    return raw_contacts(1)
                probe=SimpleNamespace(ownership=OWNERSHIP,install=lambda:None,begin=lambda tick:None,
                                      end=end,close=lambda:closed.append(True))
                contact=puck.classify_contacts(raw_contacts(0),OWNERSHIP,tick=0,time_s=0.)
                with ExitStack() as stack:
                    stack.enter_context(patch.object(gate,'world_from',return_value={**self.world,'time_s':.02}))
                    stack.enter_context(patch.object(puck_model,'predict',return_value=self.prediction))
                    if fault in ('tick','event'):stack.enter_context(patch.object(RunWriter,fault,side_effect=OSError(fault)))
                    elif fault=='fsync':stack.enter_context(patch.object(adapter.os,'fsync',side_effect=OSError(fault)))
                    with self.assertRaises(OSError):
                        gate.on_policy_interval(self.env,self.observation,puck.initialize(self.world,'fixture'),self.world,
                                                contact,self.own,self.mode,object(),probe,writer)
                self.assertEqual(closed,[True]);self.assertEqual(self.own['tick'],0)
                self.assertEqual(list(adapter.read_committed_intervals(path)),[])
                with self.assertRaises(ValueError):self.publish(writer)

    def test_real_disk_two_interval_prefix_binds_rows_and_events(self):
        writer=adapter.PuckIntervalWriter(self.path,max_bytes=2*1024**2)
        receipt=self.publish(writer);staged=self.staged()
        own,mode=adapter.admit_completed_interval(staged,self.own,self.mode,completed_tick=1,publication_receipt=receipt)
        self.assertEqual(own['tick'],1);self.assertEqual(mode,staged['teacher_mode_after'])
        self.publish(writer,1)
        rows=list(adapter.read_committed_intervals(self.path))
        self.assertEqual([r['completed_tick'] for r in rows],[1,2])
        self.assertEqual(rows[0]['row']['action'].tobytes(),self.prediction.tobytes())
        self.assertNotIn('teacher_mode_before',rows[0]['row'])
        for tick in (1,2):
            directory=self.path/f'{tick:06d}'
            self.assertEqual((directory/'commit.json').stat().st_ino,(directory/'commit.anchor.json').stat().st_ino)

    def test_faults_poison_writer_and_preserve_only_earlier_committed_prefix(self):
        for fault in ('tick','event','finish','fsync','anchor','publication'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                path=Path(temporary)/'intervals';writer=adapter.PuckIntervalWriter(path,max_bytes=2*1024**2)
                self.publish(writer)
                target={'tick':(RunWriter,'tick'),'event':(RunWriter,'event'),'finish':(RunWriter,'finish'),
                        'fsync':(adapter.os,'fsync'),'anchor':(adapter,'_write_bytes_new'),
                        'publication':(adapter,'_exclusive_publish')}[fault]
                with patch.object(*target,side_effect=OSError('injected '+fault)):
                    with self.assertRaises(OSError):self.publish(writer,1)
                with self.assertRaises(ValueError):self.publish(writer,1)
                self.assertEqual([r['completed_tick'] for r in adapter.read_committed_intervals(path)],[1])

    def test_torn_swapped_reordered_or_changed_committed_payload_is_rejected(self):
        for fault in ('marker','events','chunk','gap','swap'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                path=Path(temporary)/'intervals';writer=adapter.PuckIntervalWriter(path,max_bytes=2*1024**2)
                self.publish(writer);self.publish(writer,1)
                first,second=path/'000001',path/'000002'
                if fault=='marker':(first/'commit.json').write_bytes(b'{')
                elif fault=='events':(first/'recording/events.jsonl').write_bytes(b'{')
                elif fault=='chunk':(first/'recording/chunks/000000.npz').write_bytes(b'changed')
                elif fault=='gap':(first/'commit.json').unlink()
                else:
                    temporary_name=path/'swapped';first.rename(temporary_name);second.rename(first);temporary_name.rename(second)
                with self.assertRaises((ValueError,OSError)):list(adapter.read_committed_intervals(path))

    def test_packet_schema_and_small_budget_fail_before_row_admission(self):
        writer=adapter.PuckIntervalWriter(self.path,max_bytes=1024)
        with self.assertRaises((ValueError,RuntimeError)):self.publish(writer)
        self.assertEqual(list(adapter.read_committed_intervals(self.path)),[])
        with tempfile.TemporaryDirectory() as temporary:
            writer=adapter.PuckIntervalWriter(Path(temporary)/'rows',max_bytes=2*1024**2)
            staged=self.staged();arrays,event=self.payload(staged)
            arrays['teacher_mode_before']=np.uint8(1)
            with self.assertRaises(ValueError):writer.publish(staged,arrays,event,completed_tick=1)

    def test_completed_event_cannot_disagree_with_native_packet(self):
        writer=adapter.PuckIntervalWriter(self.path,max_bytes=2*1024**2)
        staged=self.staged();arrays,event=self.payload(staged)
        arrays.update(native_completed_tick=np.int64(1),native_data_time_s=np.float64(.02),
            world_after=np.zeros(12,np.float64),reward=np.float64(0.),task_sha256=np.zeros(32,np.uint8))
        with self.assertRaises(ValueError):writer.publish(staged,arrays,event,completed_tick=1)

    def test_output_root_replacement_during_publication_never_admits_new_interval(self):
        writer=adapter.PuckIntervalWriter(self.path,max_bytes=2*1024**2)
        self.publish(writer)
        real=adapter._write_bytes_new
        def replace_root(*args,**kwargs):
            result=real(*args,**kwargs)
            self.path.rename(self.path.with_name('moved'))
            self.path.mkdir()
            return result
        with patch.object(adapter,'_write_bytes_new',side_effect=replace_root):
            with self.assertRaises((ValueError,OSError)):self.publish(writer,1)
        self.assertEqual(list(adapter.read_committed_intervals(self.path)),[])
        moved=self.path.with_name('moved')
        self.assertEqual([r['completed_tick'] for r in adapter.read_committed_intervals(moved)],[1])

    def test_actual_interval_steps_only_student_and_commits_after_native_and_publication(self):
        writer=adapter.PuckIntervalWriter(self.path,max_bytes=2*1024**2)
        contact=puck.classify_contacts(raw_contacts(0),OWNERSHIP,tick=0,time_s=0.)
        state=puck.initialize(self.world,'fixture')
        calls=[]
        def step(action):
            calls.append(('step',action));self.env._t+=1;self.env.data.time=.02
            self.env.data.ctrl[:]=gate.effective_control(action) if hasattr(gate,'effective_control') else __import__('palimpsest.body_profile',fromlist=['effective_control']).effective_control(action)
            return self.observation,0.,False,False,{'dist_to_goal':1.,'stalled':False}
        self.env.step=step
        probe=SimpleNamespace(ownership=OWNERSHIP,install=lambda:calls.append(('install',)),begin=lambda tick:None,
            end=lambda:raw_contacts(1),close=lambda:calls.append(('close',)))
        after={**self.world,'time_s':.02}
        with patch.object(gate,'world_from',return_value=after), patch.object(puck_model,'predict',return_value=self.prediction), \
             patch.object(puck_teacher,'decide',wraps=puck_teacher.decide) as teacher:
            result=gate.on_policy_interval(self.env,self.observation,state,self.world,contact,self.own,self.mode,object(),probe,writer)
        self.assertEqual(teacher.call_count,1)
        self.assertEqual([c[0] for c in calls],['install','step','close'])
        self.assertEqual(calls[1][1],self.prediction.tolist())
        self.assertEqual(self.own['tick'],0);self.assertEqual(result['own']['tick'],1)
        self.assertEqual(len(list(adapter.read_committed_intervals(self.path))),1)

    def test_native_step_failure_stops_writer_without_cursor_or_row_admission(self):
        writer=adapter.PuckIntervalWriter(self.path,max_bytes=2*1024**2)
        contact=puck.classify_contacts(raw_contacts(0),OWNERSHIP,tick=0,time_s=0.)
        self.env.step=lambda action: (_ for _ in ()).throw(OSError('native step'))
        closed=[];probe=SimpleNamespace(install=lambda:None,begin=lambda tick:None,close=lambda:closed.append(True))
        with patch.object(puck_model,'predict',return_value=self.prediction):
            with self.assertRaisesRegex(OSError,'native step'):
                gate.on_policy_interval(self.env,self.observation,puck.initialize(self.world,'fixture'),self.world,contact,self.own,self.mode,object(),probe,writer)
        self.assertEqual(closed,[True]);self.assertEqual(self.own['tick'],0)
        self.assertEqual(list(adapter.read_committed_intervals(self.path)),[])
        with self.assertRaises(ValueError):self.publish(writer)

    def test_unqualified_owner_route_rejects_before_protected_imports(self):
        with patch.dict(sys.modules,{'torch':None,'mujoco':None}):
            with self.assertRaisesRegex(ValueError,'not qualified'):
                gate.owner({'puck_on_policy':adapter.PROTOCOL_SHA256,'scene_id':6200})


if __name__=='__main__':unittest.main()
