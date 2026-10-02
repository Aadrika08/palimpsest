"""Authored pure fixtures only; no native collection, model or learned qualification."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np
from palimpsest import puck_learning as learning
from palimpsest.records import RunWriter, iter_ticks

ROOT=Path(__file__).resolve().parents[1]

def sensors(puck=(.55,0.),goal=(1.75,0.)):
    return np.array([puck[0]/14,puck[1]/14,goal[0]/14,goal[1]/14,0.,0.,1.,0.],np.float32)

def cursor(mode='approach',tick=0):
    value=learning.initial_cursor();value.update(mode=mode,tick=tick);return value

class PuckLearningTests(unittest.TestCase):
    def test_protocol_preserves_all_frozen_layouts_training_and_bounds(self):
        new=learning.load_protocol(ROOT)
        old=json.loads((ROOT/'docs/plans/m6-puck-pushing-protocol-v4.json').read_text())
        self.assertEqual(new['layouts'],old['layouts']);self.assertEqual(len(new['layouts']),32)
        self.assertEqual(new['limits'],old['limits'])
        expected=copy.deepcopy(old['learning']);expected['architecture'][0]=9
        self.assertEqual(new['learning'],expected)
        for key,value in old['admission'].items():self.assertEqual(new['admission'][key],value)

    def test_prepare_uses_before_mode_and_commit_is_explicit(self):
        current=cursor();original=copy.deepcopy(current);observation=sensors()
        pending=learning.prepare(observation,current)
        self.assertEqual(current,original);self.assertEqual(pending['after']['mode'],'push')
        self.assertEqual(pending['inputs'].dtype,np.float32)
        np.testing.assert_array_equal(pending['inputs'],np.r_[observation,np.float32(0.)])
        self.assertEqual(learning.commit(current,pending,1),cursor('push',1))
        self.assertEqual(current,original)
        for completed in (0,2,True):
            with self.assertRaises(ValueError):learning.commit(current,pending,completed)
        tampered=copy.deepcopy(pending);tampered['inputs'][0]=.1
        with self.assertRaises(ValueError):learning.commit(current,tampered,1)
        changed=copy.deepcopy(pending);changed['after']['mode']='approach'
        with self.assertRaises(ValueError):learning.commit(current,changed,1)
        with self.assertRaises(ValueError):learning.commit(cursor('push',1),pending,2)
        self.assertEqual(current,original)

    def test_stop_precedes_division_and_quantized_boundary_is_frozen(self):
        for mode in ('approach','push'):
            current=cursor(mode,1)
            for observation in (sensors((.55,0.),(.55,0.)),sensors((0.,0.),(0.,0.))):
                self.assertEqual(learning.prepare(observation,current)['after']['mode'],mode)
        below=np.array([0.,0.,np.float32(.18/14),0.,0.,0.,0.,0.],np.float32)
        above=below.copy();above[2]=np.nextafter(below[2],np.float32(np.inf))
        self.assertEqual(float(below[2])*14.,.17999999970197678)
        self.assertEqual(float(above[2])*14.,.18000001274049282)
        self.assertEqual(learning.prepare(above,cursor('push',1))['after']['mode'],'approach')
        self.assertEqual(learning.prepare(below,cursor('push',1))['after']['mode'],'push')

    def test_adjacent_quantized_axial_lateral_and_arrival_boundaries(self):
        for nominal in (.35,.63):
            observation=sensors((nominal,0.),(nominal+1.2,0.))
            inside=observation.copy();outside=observation.copy()
            if nominal==.35:outside[0]=np.nextafter(observation[0],np.float32(-np.inf))
            else:inside[0]=np.nextafter(observation[0],np.float32(-np.inf))
            self.assertEqual(learning.prepare(inside,cursor('push',1))['after']['mode'],'push')
            self.assertEqual(learning.prepare(outside,cursor('push',1))['after']['mode'],'approach')
        inside=sensors((.55,.06),(1.75,.06));outside=inside.copy()
        outside[[1,3]]=np.nextafter(inside[[1,3]],np.float32(np.inf))
        self.assertEqual(learning.prepare(inside,cursor('push',1))['after']['mode'],'push')
        self.assertEqual(learning.prepare(outside,cursor('push',1))['after']['mode'],'approach')
        inside=sensors((.47,0.),(1.67,0.));outside=inside.copy()
        outside[0]=np.nextafter(inside[0],np.float32(-np.inf))
        self.assertEqual(learning.prepare(inside,cursor('approach',1))['after']['mode'],'push')
        self.assertEqual(learning.prepare(outside,cursor('approach',1))['after']['mode'],'approach')

    def test_cursor_carries_recovery_and_reflected_body_observations(self):
        # Same instantaneous sensor vector supports different carried modes.
        overlap=sensors((.4,0.),(1.6,0.))
        self.assertEqual(learning.prepare(overlap,cursor('approach',1))['after']['mode'],'approach')
        self.assertEqual(learning.prepare(overlap,cursor('push',1))['after']['mode'],'push')
        outside=sensors((.45,.07),(1.65,.07))
        self.assertEqual(learning.prepare(outside,cursor('push',1))['after']['mode'],'approach')
        reflected=outside.copy();reflected[[1,3,5]]*=-1
        self.assertEqual(learning.prepare(reflected,cursor('push',1))['after']['mode'],'approach')
        # A reflected WORLD produces the same body-frame sensors; no world/yaw input exists.
        self.assertEqual(learning.prepare(sensors(),cursor('approach',1))['after']['mode'],'push')

    def test_rejects_wrong_observation_cursor_and_exhaustion_without_mutation(self):
        good=sensors()
        for bad in (good.astype(np.float64),good.tolist(),good[:7],np.full(8,np.nan,np.float32),
                    good+np.float32(2),good.copy()):
            if isinstance(bad,np.ndarray) and np.array_equal(bad,good):bad[6]=.5
            with self.assertRaises(ValueError):learning.prepare(bad,cursor())
        bad=good.copy();bad[7]=1
        with self.assertRaises(ValueError):learning.prepare(bad,cursor())
        for change in ({'mode':'push'},{'mode':'fixed'},{'tick':True},{'tick':-1},
                       {'version':2},{'protocol_sha256':'0'*64},{'unexpected':1}):
            current=cursor();current.update(change)
            with self.assertRaises(ValueError):learning.prepare(good,current)
        with self.assertRaises(ValueError):learning.prepare(good,cursor('approach',600))

    def test_record_roundtrip_reconstructs_mode_and_rejects_each_corruption(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'recording';self.fixture(path)
            data=learning.admit_record(path,self.sha(path/'manifest.json'),6000,'train',ROOT)
            self.assertEqual(data['inputs'].shape,(32,9));self.assertEqual(data['targets'].shape,(32,2))
            self.assertEqual(data['targets'].dtype,np.float64)
            self.assertEqual(data['inputs'][0,8],0);self.assertTrue(np.all(data['inputs'][1:,8]==1))
            rows=list(iter_ticks(path));self.assertIsInstance(rows[0]['teacher_mode_before'],np.uint8)
            for field,value in [('teacher_mode_before',np.uint8(2)),('teacher_mode_after',np.uint8(1)),
                                ('supervisor_mode_before',np.uint8(1)),('supervisor_mode_after',np.uint8(0)),
                                ('teacher_mode_before',np.int64(1)),('teacher_mode_after',np.array([2],np.uint8)),
                                ('student_inputs',np.zeros(9,np.float32)),('action',np.array([np.nan,0.]))]:
                bad=copy.deepcopy(rows);bad[0][field]=value
                with self.subTest(field=field,value=value):
                    with self.assertRaises(ValueError):learning.admit_teacher_rows(bad,32)
            with self.assertRaises(ValueError):learning.admit_teacher_rows(rows[1:],31)
            with self.assertRaises(ValueError):learning.admit_record(path,'0'*64,6000,'train',ROOT)
            with self.assertRaises(ValueError):learning.admit_record(path,self.sha(path/'manifest.json'),6200,'held_out',ROOT)
            manifest=json.loads((path/'manifest.json').read_text());manifest['status']='running'
            (path/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):learning.admit_record(path,self.sha(path/'manifest.json'),6000,'train',ROOT)

    def test_promoted_output_scaling_matches_real_advance_boundary_without_clipping(self):
        from palimpsest import puck_profile as puck
        from palimpsest.body_profile import effective_control
        from test_puck_profile import OWNERSHIP, raw_contacts, world
        state=puck.initialize(world(),'output-boundary-fixture')
        contact=puck.classify_contacts(raw_contacts(1),OWNERSHIP,tick=1,time_s=.02)
        old=np.array([.4,-.4],np.float32).tolist()
        self.assertEqual(old[0],.4000000059604645)
        with self.assertRaises(ValueError):puck.advance(state,world(1),contact,old)
        action=learning.scale_action(np.array([1.,-1.],np.float32))
        self.assertEqual(action.dtype,np.float64);self.assertEqual(action.tolist(),[.4,-.4])
        self.assertEqual(puck.advance(state,world(1),contact,action.tolist())[0]['tick'],1)
        self.assertEqual(effective_control(action.tolist()),[float(np.float32(1.2)),float(np.float32(.4))])
        for normalized in (np.array([1.,0.],np.float64),np.array([np.nan,0.],np.float32),
                           np.array([np.nextafter(np.float32(1),np.float32(np.inf)),0],np.float32),
                           np.zeros((1,2),np.float32),[1.,0.]):
            with self.assertRaises(ValueError):learning.scale_action(normalized)
        with self.assertRaises(ValueError):
            puck.advance(state,world(1),contact,[float(np.nextafter(np.float64(.4),np.inf)),0.])
        self.assertTrue(np.signbit(learning.scale_action(np.array([-0.,0.],np.float32))[0]))

    def test_cursor_roundtrip_and_tampered_snapshot_admission_are_pure(self):
        from palimpsest.snapshots import save_snapshot, read_snapshot
        original=cursor('push',17)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'cursor.snp'
            save_snapshot({'application':{'own_supervisor_cursor':original}},path)
            restored=read_snapshot(path)['application']['own_supervisor_cursor']
        self.assertEqual(learning.validate_cursor(restored),original)
        self.assertEqual(learning.prepare(sensors((.4,0.),(1.6,0.)),restored)['after']['mode'],'push')
        for key,value in (('version',2),('protocol_sha256','0'*64),('tick',True),('mode','fixed')):
            changed=original|{key:value}
            with self.assertRaises(ValueError):learning.validate_cursor(changed)

    def test_fixed_batch_failure_keeps_all_plan_rows_and_returns_no_training_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            entries=[]
            for seed in range(6000,6020):
                split='train' if seed<6016 else 'recorded_dev';path=Path(tmp)/str(seed)/'recording'
                self.fixture(path,seed,split,bad=(seed==6001))
                entries.append({'seed':seed,'split':split,'path':str(path),'manifest_sha256':self.sha(path/'manifest.json')})
            before={str(p):self.sha(p) for p in Path(tmp).rglob('*') if p.is_file()}
            result=learning.admit_batch(entries,ROOT)
            self.assertEqual(result['status'],'failed');self.assertEqual(len(result['rows']),20)
            self.assertEqual([r['seed'] for r in result['rows']],list(range(6000,6020)))
            self.assertEqual([r['seed'] for r in result['rows'] if r['status']=='failed'],[6001])
            self.assertNotIn('data',result)
            self.assertEqual(before,{str(p):self.sha(p) for p in Path(tmp).rglob('*') if p.is_file()})
            with self.assertRaises(ValueError):learning.admit_batch(entries[::-1],ROOT)
            with self.assertRaises(ValueError):learning.admit_batch(entries[:-1],ROOT)

    def test_completed_fixed_fixture_batch_preserves_labels_and_source_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            entries=[]
            for seed in range(6000,6020):
                split='train' if seed<6016 else 'recorded_dev';path=Path(tmp)/str(seed)/'recording'
                self.fixture(path,seed,split)
                entries.append({'seed':seed,'split':split,'path':str(path),'manifest_sha256':self.sha(path/'manifest.json')})
            result=learning.admit_batch(entries,ROOT)
            self.assertEqual(result['status'],'passed');self.assertEqual(len(result['data']),20)
            self.assertEqual(sum(d['ticks'] for d in result['data'] if d['split']=='train'),512)
            for entry,data in zip(entries,result['data']):
                self.assertEqual(data['targets'].dtype,np.float64)
                for name,value in data['source_hashes'].items():self.assertEqual(self.sha(Path(entry['path'])/name),value)

    @staticmethod
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

    def fixture(self,path,seed=6000,split='train',bad=False):
        spec=learning.load_protocol(ROOT)
        writer=RunWriter(path,{'schema':'puck-demonstration-v1','learning_protocol_sha256':learning.PROTOCOL_SHA256,
            'pushing_protocol_sha256':spec['task_protocol']['sha256'],'teacher_source_sha256':spec['teacher_source_sha256'],
            'teacher_id':spec['teacher_id'],'seed':seed,'split':split,'episodes':1,'initial_supervisor':cursor(),
            'learning_feature_id':spec['learning_feature_id'],
            'supervisor_source_sha256':self.sha(ROOT/'src/palimpsest/puck_learning.py'),
            'fixture':'authored data contract only, no native or teacher execution'})
        writer.event('episode_start',episode=0,seed=seed,teacher_mode='approach',supervisor_cursor=cursor())
        own=cursor()
        for tick in range(32):
            observation=sensors() if tick<22 else sensors((.55,0.),(.65,0.))
            pending=learning.prepare(observation,own)
            before=0 if own['mode']=='approach' else 1;after=0 if pending['after']['mode']=='approach' else 1
            writer.tick(0,tick,inputs=observation,student_inputs=pending['inputs'],
                action=np.array([.2,0.] if tick<22 else [0.,0.],np.float64),
                teacher_mode_before=np.array(2 if bad and tick==0 else before+1,np.uint8),
                teacher_mode_after=np.array(after+1,np.uint8),supervisor_mode_before=np.array(before,np.uint8),
                supervisor_mode_after=np.array(after,np.uint8))
            writer.event('puck_interval',teacher_mode_before=own['mode'],teacher_mode_after=pending['after']['mode'],
                supervisor_mode_before=own['mode'],supervisor_mode_after=pending['after']['mode'],
                state={'tick':tick+1,'reason':'puck_goal' if tick==31 else None,
                'dwell_ticks':max(0,tick-21)},contact={'tick':tick+1,'rover_puck_contact':True,'failure':None})
            own=learning.commit(own,pending,tick+1)
        writer.finish({'outcome':'puck_goal','ticks':32});writer.close()
