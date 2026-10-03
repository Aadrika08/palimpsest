"""Pure frozen-stream admission fixtures; no model/native or retained data."""
import copy
import importlib.util
import hashlib
import json
import tempfile
import uuid
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
import numpy as np
from palimpsest import memory, memory_task
from test_memory_task import bank, world

PATH=Path(__file__).resolve().parents[1]/'scripts/verify_memory_observation_stream.py'
spec=importlib.util.spec_from_file_location('observation_stream_fixture',PATH)
r=importlib.util.module_from_spec(spec); spec.loader.exec_module(r)


class ObservationStream(unittest.TestCase):
    def state(self):
        return memory_task.initialize(bank(),{'version':1,'episodes':[]},memory.artifact('local_cue'),'live')

    def packet(self,tick,token=0):
        return memory_task.capture_symbolic(world(token),[0.,0.,0.],[],episode_id='live',tick=tick)

    def frame(self,tick,packet=None):
        frame={'tick':tick,'packet':self.packet(tick) if packet is None else packet,
            'observation':{'cam_left':np.zeros((2,2,3),np.uint8),'cam_right':np.zeros((2,2,3),np.uint8),
                'sensors':{'collision':False,'collision_angle':None,'wind_direction':[1.,0.]}},
            'source_decisions':[], 'source_inspect':None,
            'source_result':{k:np.zeros(shape,np.float32) for k,shape in [('action',(2,)),('raw_output',(2,)),('encoded_input',(4813,))]}}
        frame['source_input_sha256']=r.state_digest(frame['observation'])
        frame['source_result_sha256']={k:r.state_digest(v) for k,v in frame['source_result'].items()}
        return frame

    def test_cue_unavailable_is_uncommitted_and_never_calls_policy(self):
        state,_,_=memory_task.advance_memory(self.state(),self.packet(0))
        packet=self.packet(1,1); packet['landmarks']=[]
        before=copy.deepcopy(state); policy=Mock()
        value=r.advance_frame(state,self.frame(1,packet),policy)
        self.assertEqual(value['status'],'censored_cue_unavailable')
        self.assertEqual(value['state'],before); self.assertEqual(state,before)
        self.assertIsNone(value['result']); self.assertEqual(value['decisions'],[])
        policy.act.assert_not_called()

    def test_no_event_never_selects_and_malformed_stream_rejects_before_inference(self):
        frames=[self.frame(0),self.frame(1)]
        r.audit_frames(self.state(),frames)
        policy=Mock(); policy.act.side_effect=lambda obs:copy.deepcopy(frames[0]['source_result'])
        state=self.state()
        with patch.object(r.memory_experiment,'selection_for_condition',side_effect=AssertionError('unexpected selector')):
            for frame in frames:
                value=r.advance_frame(state,frame,policy);state=value['state']
                self.assertFalse(any(d['kind']=='memory_selection' for d in value['decisions']))
        self.assertEqual(policy.act.call_count,2)
        for change in ('future','private','nan','bad_shape'):
            bad=copy.deepcopy(frames)
            if change=='future': bad[1]['packet']=self.packet(3)
            elif change=='private': bad[0]['observation']['pose']=[0,0,0]
            elif change=='nan': bad[0]['observation']['sensors']['collision_angle']=float('nan')
            else: bad[0]['observation']['cam_left']=np.zeros((2,2),np.uint8)
            with self.assertRaises((ValueError,TypeError)): r.audit_frames(self.state(),bad)
        self.assertEqual(policy.act.call_count,2)

    def test_selector_only_preparation_retains_every_other_task_field(self):
        state,_,_=memory_task.advance_memory(self.state(),self.packet(0))
        state=memory_task.configure_selector(state,r.shared_selector())
        before=copy.deepcopy(state); changed=copy.deepcopy(state)
        changed['selector']['provenance_sha256']='a'*64
        self.assertEqual(r.task_without_selector(changed),r.task_without_selector(before))
        for field,value in [('detector',{'tick':None,'cues':[]}),('cursor',None),('requests',[{'unsupported':True}]),
                ('active',{'unsupported':True}),('m',{'changed':True}),('e',{'version':1,'episodes':[{}]}),('version',1)]:
            forged=copy.deepcopy(changed);forged[field]=value
            self.assertNotEqual(r.task_without_selector(forged),r.task_without_selector(before),field)
        self.assertEqual(state,before)

    def test_fixed_join_rejects_probe_duplicate_wrong_source_and_bool_protocol(self):
        source=r.SOURCES['A'][0]
        cell,identifier,digest,count=source
        rows=[{'cell':cell,'stage':'own','run_id':identifier,'snapshot_sha256':digest}]
        jobs=[{'cell':list(r.cell_tuple(cell)),'stage':'own','run_id':identifier}]
        self.assertEqual(r.join_own(rows,jobs,source),rows[0])
        for invalid in ([{**rows[0],'stage':'probe'}],rows+rows,[{**rows[0],'run_id':'0'*32}]):
            with self.assertRaises(ValueError):r.join_own(invalid,jobs,source)
        forged=copy.deepcopy(r.protocol('A'));forged['held_out']=0
        self.assertNotEqual(memory.canonical_bytes(forged),memory.canonical_bytes(r.protocol('A')))

    def test_structural_admission_changes_only_existing_schema_fields(self):
        native={'application':{'schema_version':3,'scenario':'memory-passages',
            'memory':self.state(),'controller':'flynn','cursor_fixture':299},'policy':np.array([1.],np.float32),
            'rng':{'numpy':np.array([2],np.uint32)}}
        original=copy.deepcopy(native);admitted=r.admitted_native(native)
        self.assertEqual(admitted['application']['schema_version'],4)
        self.assertIsNone(admitted['application']['task_state'])
        admitted['application'].pop('task_state');admitted['application']['schema_version']=3
        self.assertEqual(r.state_digest(admitted),r.state_digest(original))
        self.assertEqual(r.state_digest(native),r.state_digest(original))
        for field,value in [('schema_version',True),('schema_version',4),('task_state',None),('scenario','encoder-homing')]:
            forged=copy.deepcopy(native);forged['application'][field]=value
            with self.assertRaises(ValueError):r.admitted_native(forged)

    def test_real_zero_row_recording_snapshot_and_derivative_admission(self):
        from palimpsest.records import RunWriter
        from palimpsest.snapshots import SNAPSHOT_KEYS,save_snapshot
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);identifier=uuid.uuid4().hex;run=root/identifier;run.mkdir()
            state,_,_=memory_task.advance_memory(self.state(),self.packet(0))
            ancestor={k:None for k in SNAPSHOT_KEYS}
            ancestor['application']={'schema_version':3,'scenario':'memory-passages','memory':state,
                'source_run_id':uuid.uuid4().hex,'event_prefix':{'sha256':'0'*64,'size_bytes':0,'event_count':0},'execution_mode':'live'}
            source=root/'source.snp';save_snapshot(ancestor,source)
            admitted=r.admitted_native(ancestor)
            writer=RunWriter(run/'recording',{'run_id':identifier,'requested_device':'cpu','controller':'flynn'})
            writer.event('application_restored',parent_run_id=ancestor['application']['source_run_id'],parent_event_prefix=ancestor['application']['event_prefix'])
            writer.event('memory_u_replaced',old_u=state['u'],new_u=state['u'],invariant_hashes=r.invariant_hashes(admitted))
            writer.event('diagnostic_source_admission',raw_source_snp_sha256=r.common._hash(source),
                source_state_sha256=r.state_digest(ancestor),admitted_state_sha256=r.state_digest(admitted))
            writer.flush();prefix=(run/'recording/events.jsonl').read_bytes()
            native=copy.deepcopy(admitted);native['application'].update(source_run_id=identifier,event_prefix={
                'sha256':hashlib.sha256(prefix).hexdigest(),'size_bytes':len(prefix),'event_count':prefix.count(b'\n')})
            fake=SimpleNamespace(env=None,observation={},policy=None,teacher=None,writer=writer,revision=1,episode=0,
                episode_step=300,seed=31,scenario='memory-passages',texture='cylinder',controller='flynn',run_id=identifier,
                application_state=lambda:copy.deepcopy(native['application']))
            with patch('palimpsest.snapshots.capture',return_value=native):r._register_initial(fake,run)
            writer.finish({'final_phase':'paused','total_tick':300,'close_reason':'operator_closed','last_outcome':None});writer.close()
            frame=self.frame(1);final,bearing,decisions=memory_task.advance_memory(state,frame['packet']);frame['source_decisions']=decisions
            trace={'tick':1,'packet_sha256':memory.sha256(frame['packet']),'status':'committed',
                'task_before_sha256':memory.sha256(state),'task_after_sha256':memory.sha256(final),'decisions':decisions,'bearing':bearing,
                'input_sha256':frame['source_input_sha256'],'result_sha256':frame['source_result_sha256'],
                'maximum_abs_difference':{k:0. for k in frame['source_result']}}
            storage=Mock();published=r.publish_derivative(run,[trace],[frame['source_result']],storage)
            report={'status':'diagnostic_checked','wall_seconds':1.,'snapshot_sha256':r.common._hash(run/'snapshots/initial.snp'),
                'initial_non_u':r.invariant_hashes(native),'initial_u_sha256':memory.sha256(state['u']),
                'derivative':published,'policy_calls':1,'final_memory':final}
            worker_path=run/'diagnostic-worker.json';worker_path.write_text(json.dumps(report))
            job={'output':str(run),'snapshot_path':str(source),'snapshot_sha256':r.common._hash(source),
                'wave':'A','stage':'own','cell':'s31/local_cue/no-event','expected_non_u':r.invariant_hashes(admitted),
                'source':{'snapshot_path':str(source),'case':{},'ticks':1,'gold_proof':{'gold_target_ids':[],'after_circles':[],'trigger':None}}}
            with patch.object(r,'read_stream',return_value=([frame],ancestor)),patch.object(r,'condition_u',return_value=state['u']), \
                    patch.object(r.common,'occupancy',return_value={'passage-a':'blocked','passage-b':'open'}):
                checked=r.validate_stage(job,{'status':'completed','returncode':0})
                self.assertEqual(checked[0]['readout']['committed_selector_decisions'],0)
                self.assertEqual(checked[0]['readout']['behavior_input_bytes_if_witnessed'],0)
                self.assertEqual(r.artifacts._load(run)['manifest']['recorded_ticks'],0)
                for fault in ('truncated','false_censor','extra_arrays'):
                    r.publish_derivative(run,[trace],[frame['source_result']],storage)
                    broken=copy.deepcopy(report)
                    if fault=='truncated':(run/'diagnostic-trace.jsonl').write_bytes(b'')
                    elif fault=='false_censor':
                        malformed={**trace,'status':'censored_cue_unavailable','decisions':[],'bearing':None,'error':'invented'}
                        (run/'diagnostic-trace.jsonl').write_text(json.dumps(malformed)+'\n')
                        broken.update(status='diagnostic_censored',censored_boundary=1)
                    else:
                        arrays=r.numeric_results([frame['source_result']]);arrays['private']=np.zeros(1)
                        np.savez(run/'diagnostic-arrays.npz',**arrays)
                    for name,label in [('diagnostic-trace.jsonl','trace'),('diagnostic-arrays.npz','arrays')]:
                        broken['derivative'][label+'_sha256']=r.common._hash(run/name)
                        broken['derivative'][label+'_bytes']=(run/name).stat().st_size
                    worker_path.write_text(json.dumps(broken))
                    with self.assertRaises(ValueError):r.validate_stage(job,{'status':'completed','returncode':0})

    def test_final_print_boundary_cannot_pass_after_parent_deadline(self):
        with tempfile.TemporaryDirectory(dir=PATH.parents[1]/'runs') as directory:
            root=Path(directory);plan={'protocol':r.protocol('A'),'output':str(root)}
            report={'status':'diagnostic_checked','policy_calls':0};clock={'now':0.}
            r.write_report(root/'diagnostic-report.json',report,r.budget(root,'A'))
            with patch.object(r.sys,'argv',['verifier','--prepared-plan','/tmp/synthetic-plan','--prepared-plan-sha256','a'*64]), \
                    patch.object(r.neural,'read_prepared_plan',return_value=plan),patch.object(r,'validate_plan',return_value=plan), \
                    patch.object(r,'run_verifier',return_value=report),patch.object(r.time,'monotonic',side_effect=lambda:clock['now']), \
                    patch('builtins.print',side_effect=lambda *a,**kw:clock.update(now=2620.000001)):
                self.assertEqual(r.main(),1)
            stored=json.loads((root/'diagnostic-report.json').read_text())
            self.assertEqual(stored['status'],'diagnostic_unverified');self.assertTrue(stored['deadline_exceeded'])
            self.assertFalse((root/'diagnostic-report.json.tmp').exists())

    def test_real_worker_parent_and_worker_return_late_updates_keep_bounded_report(self):
        from palimpsest.snapshots import SNAPSHOT_KEYS,save_snapshot
        with tempfile.TemporaryDirectory(dir=PATH.parents[1]/'runs') as directory:
            root=Path(directory);clock={'now':0.};original=r.write_report
            def delayed_write(path,value,storage):
                original(path,value,storage)
                if not value.get('deadline_exceeded'):
                    clock['now']=150.000001 if Path(path).name=='diagnostic-worker.json' else 2620.000001
            job={'assets':str(root),'source_identity':{},'root_output':str(root),'wave':'A',
                'output':str(root/'worker'),'run_id':uuid.uuid4().hex,'stage':'own','cell':'s25/local_cue/change'}
            Path(job['output']).mkdir()
            with patch.object(r,'validate_job',return_value=job),patch.object(r,'source_identity',return_value={'fixture':True}), \
                    patch.object(r,'write_report',side_effect=delayed_write), \
                    patch.object(r.time,'monotonic',side_effect=lambda:clock['now']):
                self.assertEqual(r.worker(job),1)
            stored=json.loads((Path(job['output'])/'diagnostic-worker.json').read_text())
            self.assertTrue(stored['deadline_exceeded']);self.assertEqual(stored['status'],'failed')
            # Parent uses its real lease/mkdir/plan/job/report publication with a mocked, unstarted child.
            native={k:None for k in SNAPSHOT_KEYS};native['application']={'schema_version':3,'scenario':'memory-passages','memory':self.state()}
            source=root/'source.snp';save_snapshot(native,source);output=root/'nested'/'parent';clock['now']=0.
            prepared={**job,'output':str(output/'runs'/job['run_id']),'root_output':str(output),
                'source':{'snapshot_path':str(source),'snapshot_sha256':r.common._hash(source)},
                'bindings_path':str(root/'unused-bindings'),'bindings_sha256':'a'*64}
            plan={'protocol':r.protocol('A'),'output':str(output),'source_identity':{'fixture':True},'jobs':[prepared]}
            with patch.object(r,'validate_plan',return_value=plan),patch.object(r,'validate_job',side_effect=lambda value:value), \
                    patch.object(r,'source_identity',return_value=plan['source_identity']),patch.object(r,'validate_bindings',return_value={}), \
                    patch.object(r.neural,'read_prepared_plan',return_value={}), \
                    patch.object(r,'bounded_process',side_effect=RuntimeError('fixture before child')), \
                    patch.object(r,'write_report',side_effect=delayed_write), \
                    patch.object(r.time,'monotonic',side_effect=lambda:clock['now']):
                result=r.run_verifier(plan)
            self.assertTrue((output/'runs').is_dir());self.assertEqual(list((output/'runs').iterdir()),[])
            self.assertEqual(len(result['unattempted']),1);self.assertTrue(result['deadline_exceeded'])
            stored=json.loads((output/'diagnostic-report.json').read_text())
            self.assertEqual(stored['status'],'diagnostic_unverified');self.assertTrue(stored['deadline_exceeded'])
            # main's worker-return guard also updates an already existing real report.
            clock['now']=0.
            def finish_worker(value):
                clock['now']=150.000001;return 0
            with patch.object(r.sys,'argv',['verifier','--worker',json.dumps(job)]), \
                    patch.object(r,'worker',side_effect=finish_worker),patch.object(r.time,'monotonic',side_effect=lambda:clock['now']):
                self.assertEqual(r.main(),1)
            stored=json.loads((Path(job['output'])/'diagnostic-worker.json').read_text())
            self.assertTrue(stored['return_wall_seconds']>150);self.assertTrue(stored['deadline_exceeded'])
            # Existing frozen create-only writer remains exclusive; local report replacement stays bounded.
            frozen=root/'frozen.json';r.neural.write(frozen,{'first':True},r.budget(root,'A'))
            with self.assertRaises(FileExistsError):r.neural.write(frozen,{'second':True},r.budget(root,'A'))
            with self.assertRaises(ValueError):r.write_report(frozen,{'oversized':'x'*(1024*1024)},r.budget(root,'A'))
            self.assertEqual(json.loads(frozen.read_text()),{'first':True});self.assertFalse(frozen.with_suffix('.json.tmp').exists())

    def test_successful_frame_only_replaces_declared_bearing_and_keeps_inputs(self):
        frame=self.frame(0); before=copy.deepcopy(frame);policy=Mock()
        policy.act.return_value=frame['source_result']
        value=r.advance_frame(self.state(),frame,policy)
        self.assertEqual(value['status'],'committed');self.assertEqual(value['bearing'],[1.,0.])
        self.assertEqual(r.state_digest(frame),r.state_digest(before))
        self.assertEqual(set(policy.act.call_args.args[0]),{'cam_left','cam_right','sensors'})
        self.assertEqual(policy.act.call_args.args[0]['sensors']['collision_angle'],None)

if __name__=='__main__':unittest.main()
