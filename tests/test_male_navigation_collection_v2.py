"""Synthetic v2 contracts only: no model/native, corpus, scene or writer lease."""
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
import collect_male_navigation_v2 as nav
import test_male_navigation_collection as old


def model_fixture():
    bodies=['world',*(f'obstacle{x}_body' for x in range(20)),*nav.CONTACTS['expected_robot_body_tree']]
    ids={name:i for i,name in enumerate(bodies)}
    parents={**{f'obstacle{x}_body':'world' for x in range(20)},**nav.CONTACTS['expected_robot_body_tree']}
    geoms=list(nav.WORLD)+list(nav.CONTACTS['expected_geom_body_names'].keys())[:7]
    model=SimpleNamespace(nbody=26,ngeom=32,body_parentid=np.array([0,*[ids[parents[name]] for name in bodies[1:]]]),
        geom_bodyid=np.array([ids[nav.CONTACTS['expected_geom_body_names'][n]] for n in geoms]),
        geom_contype=np.array([nav.CONTACTS['expected_collision_masks'][n][0] for n in geoms]),
        geom_conaffinity=np.array([nav.CONTACTS['expected_collision_masks'][n][1] for n in geoms]))
    objects=SimpleNamespace(mjOBJ_BODY='body',mjOBJ_GEOM='geom')
    names={'body':bodies,'geom':geoms}
    mj=SimpleNamespace(mjtObj=objects,mj_name2id=lambda m,k,n:names[k].index(n),mj_id2name=lambda m,k,i:names[k][i])
    return mj,model


def ownership():
    mj,model=model_fixture()
    return nav.compiled_ownership(mj,model,'1'*64)


class NavigationV2(unittest.TestCase):
    def source(self,probe_type=old.Probe):
        engine=old.Engine();teacher=old.Teacher()
        result={'rows':[],'contact_ownership':ownership(),'contact_incidence':nav.empty_incidence(),
            'numeric_admission':nav.numeric_admission([np.zeros((128,128,3),np.uint8)]*2,138)}
        from palimpsest.engine import _teacher_fingerprint
        result['initial_teacher_sha256']=_teacher_fingerprint(teacher)
        with patch.object(nav,'isolation',side_effect=old.isolated),patch.object(nav,'sample',side_effect=old.sample):
            reason=nav.collect(engine,teacher,probe_type(engine),result,time.monotonic()+20)
        return engine,teacher,result,reason

    def test_all_125_pairs_preserve_three_support_classes_and_all_negatives(self):
        g=nav.ownership_map(ownership());ids={e['name']:i for i,e in g.items()};types={}
        for robot,world in nav.PAIRS:
            code=2 if world=='floor' and robot in nav.body.GROUND_SUPPORT else 3
            kind,pair=nav.pair_type([ids[robot],ids[world]],code,-.001,g)
            self.assertEqual(nav.pair_type([ids[world],ids[robot]],code,-.001,g),(kind,pair))
            types[kind]=types.get(kind,0)+1
            with self.assertRaises(ValueError):nav.pair_type([ids[robot],ids[world]],3 if code==2 else 2,0.,g)
        self.assertEqual(types,{'non_wheel_floor':2,'robot_wall':20,'robot_obstacle':100,'wheel_floor_support':3})
        for pair in [('base_geom','left_wheel_geom'),('base_geom','base_geom'),('cam_left_marker','obstacle0'),('cam_right_marker','floor')]:
            with self.assertRaises(ValueError):nav.admit_pair([ids[n] for n in pair],3,0.,g)
        for pair,distance in [([999,0],0.),([0,1],float('nan')),([0,1],float('inf'))]:
            with self.assertRaises(ValueError):nav.admit_pair(pair,1,distance,g)
        self.assertEqual(nav.pair_type([ids['floor'],ids['obstacle0']],1,-.01,g),('world_only',None))

    def test_real_shared_ownership_tree_masks_and_initial_snp_binding(self):
        mj,model=model_fixture();value=nav.compiled_ownership(mj,model,'1'*64)
        self.assertEqual((len(value['geometries']),len(value['robot_bodies'])+len(value['world_bodies'])),(32,26))
        for change in ('mask','marker','tree','count','index_type'):
            m=copy.deepcopy(model)
            if change=='mask':m.geom_contype[25]=0
            if change=='marker':m.geom_contype[30]=1
            if change=='tree':m.body_parentid[22]=0
            if change=='count':m.ngeom=31
            if change=='index_type':m.body_parentid=m.body_parentid.astype(float)
            with self.assertRaises(ValueError):nav.compiled_ownership(mj,m,'1'*64)
        for change in ('body','owner','duplicate','base_bool'):
            v=copy.deepcopy(value)
            if change=='body':v['geometries'][25]['body_name']='world'
            if change=='owner':v['geometries'][25]['owner']='world'
            if change=='duplicate':v['geometries'][25]['geom_id']=0
            if change=='base_bool':v['base_body_id']=True
            with self.assertRaises(ValueError):nav.ownership_map(v)
        with patch('palimpsest.snapshots.read_snapshot',return_value={'identity':{'model_sha256':'1'*64}}):
            self.assertEqual(nav.initial_contact_binding(Path('/fixture'),value),'1'*64)
        with patch('palimpsest.snapshots.read_snapshot',return_value={'identity':{'model_sha256':'2'*64}}):
            with self.assertRaisesRegex(ValueError,'initial SNP'):nav.initial_contact_binding(Path('/fixture'),value)

    def test_unchanged_noncontact_labels_controls_and_malformed_binding(self):
        loaded={name:sys.modules.get(name) for name in ('torch','mujoco')}
        engine,teacher,result,reason=self.source()
        previous=old.NavigationCollection().source()
        self.assertEqual((teacher.calls,len(engine.saved),reason),(3,3,'stalled'))
        for tick,(raw,original) in enumerate(zip(engine.saved,previous[0].saved)):
            for key in raw:self.assertTrue(np.array_equal(raw[key],original[key]),key)
            row=result['rows'][tick]
            self.assertEqual(row['contacts'],{'cached_bad':False})
            for field,value in [('nav_advice_action',np.array([.9,-.2],np.float32)),('control',np.array([0.,0.],np.float64)),
                ('body_contact_times',raw['body_contact_times']+.001),('nav_query_after',raw['nav_query_after']+1)]:
                with self.assertRaises(ValueError):nav.bind_row({**raw,field:value},row,result['contact_ownership'],tick)
        self.assertEqual(result['contact_incidence']['admitted_intervals'],3)
        self.assertEqual(loaded,{name:sys.modules.get(name) for name in ('torch','mujoco')})

    def test_full_stage_incidence_and_existing_array_guards(self):
        engine,_,result,_=self.source();raw=copy.deepcopy(engine.saved[0]);g=nav.ownership_map(result['contact_ownership']);ids={e['name']:i for i,e in g.items()}
        raw['body_contact_counts'][:]=2
        raw['body_contact_ids'][:,0]=[ids['floor'],ids['base_geom']]
        raw['body_contact_ids'][:,1]=[ids['wall_n'],ids['left_wheel_geom']]
        raw['body_contact_classes'][:,:2]=3;raw['body_contact_distances'][:,:2]=-.001
        summary=nav.admit_contacts(raw,result['contact_ownership'],0)
        self.assertEqual(summary['pair_instances_by_type_stage'][1],[1]*11)
        self.assertEqual(summary['pair_instances_by_type_stage'][3],[1]*11)
        self.assertFalse(summary['cached_bad']) # Floor metadata is never turned into a student sensor.
        aggregate=nav.empty_incidence();nav.add_incidence(aggregate,summary)
        self.assertEqual(sum(aggregate['robot_world_pair_instances']),22)
        for name,value in [('body_contact_counts',np.full(11,129)),('body_contact_distances',raw['body_contact_distances']*float('nan')),
            ('body_contact_ids',raw['body_contact_ids'].astype(float)),('body_stage_controls',raw['body_stage_controls']+.1)]:
            with self.assertRaises(ValueError):nav.admit_contacts({**raw,name:value},result['contact_ownership'],0)
        bad=copy.deepcopy(raw);bad['body_contact_ids'][0,127,0]=1
        with self.assertRaisesRegex(ValueError,'padding'):nav.admit_contacts(bad,result['contact_ownership'],0)
        bad=copy.deepcopy(raw);bad['body_contact_counts'][10]=1
        for field in ('body_contact_ids','body_contact_classes','body_contact_distances'):bad[field][10,1:]=0
        with self.assertRaisesRegex(ValueError,'Final contact cache'):nav.admit_contacts(bad,result['contact_ownership'],0)

    def test_first_rejected_packet_survives_and_prefix_does_not_include_it(self):
        g=nav.ownership_map(ownership());ids={e['name']:i for i,e in g.items()}
        class Contacts(old.Probe):
            def end(self):
                value=super().end()
                names=('floor','base_geom') if self.tick==0 else ('cam_left_marker','obstacle0')
                pair={'geom_ids':[ids[n] for n in names],'distance_m':-.001,'classification':'unexpected_robot_contact'}
                for packet in [*value['stages'],value['end']]:packet['pairs']=[pair]
                return value
        engine=old.Engine();teacher=old.Teacher();result={'rows':[],'contact_ownership':ownership(),
            'numeric_admission':nav.numeric_admission([np.zeros((128,128,3),np.uint8)]*2,138),'contact_incidence':nav.empty_incidence()}
        with patch.object(nav,'isolation',side_effect=old.isolated),patch.object(nav,'sample',side_effect=old.sample):
            with self.assertRaisesRegex(ValueError,'outside fixed v2'):nav.collect(engine,teacher,Contacts(engine),result,time.monotonic()+20)
        self.assertEqual((len(engine.saved),len(result['rows']),result['contact_incidence']['admitted_intervals']),(2,2,1))
        self.assertIn('interval_contacts',result['first_failure_packet'])
        self.assertEqual(sum(result['contact_incidence']['robot_world_pair_instances']),11)
        self.assertTrue(np.all(engine.saved[1]['body_contact_counts']==1))
        report={'cases':{c['id']:{'status':'not_started'} for c in nav.CASES},'owners_completed':0,'numeric_ticks':0}
        self.assertFalse(nav.run_cases(report,lambda c,i:(_ for _ in ()).throw(ValueError('contact failure'))))
        self.assertTrue(all(report['cases'][c['id']]['status']=='not_started' for c in nav.CASES[1:]))

    def test_incomplete_callback_and_command_failure_keep_original_packet(self):
        for fault in ('coverage','command'):
            engine=old.Engine();teacher=old.Teacher();result={'rows':[],'contact_ownership':ownership(),
                'numeric_admission':nav.numeric_admission([np.zeros((128,128,3),np.uint8)]*2,138),'contact_incidence':nav.empty_incidence()}
            class Broken(old.Probe):
                def end(self):
                    v=super().end()
                    if fault=='coverage':v.update(callback_count=9,coverage_passed=False,coverage_errors=['missing'])
                    return v
            if fault=='command':engine.advance=lambda:(_ for _ in ()).throw(RuntimeError('command failure'))
            with patch.object(nav,'isolation',side_effect=old.isolated),patch.object(nav,'sample',side_effect=old.sample):
                with self.assertRaises((ValueError,RuntimeError)):nav.collect(engine,teacher,Broken(engine),result,time.monotonic()+20)
            self.assertEqual(len(result['first_failure_packet']['interval_contacts']['stages']),10)
            self.assertEqual(result['contact_incidence']['admitted_intervals'],0)

    def test_parent_reconstructs_aggregate_and_source_profile_and_snp(self):
        engine,_,result,_=self.source();result.update(case=nav.CASES[0],status='completed-recording',engine_closed=True,callback_restored=True,
            final_state=engine.public_state(),outcome='stalled',initial_world={},initial_fingerprint={'fixture':'initial'})
        identity={'fixture':'original-only'}
        manifest={'status':'completed','profile':nav.PROFILE,'controller':'male-original','seed':3100,'scenario':{'id':'reproduction'},'texture':'checker',
            'navigation_collection':{'study_sha256':nav.PLAN_SHA,'contact_profile_sha256':nav.PROFILE_SHA,'source_identity':identity,'case':result['case'],
                'label_kind':'returned-analytic-teacher-advice','label_privileged':True,'generic_replay_qualified':False,
                'contact_ownership':result['contact_ownership'],'initial_fingerprint':result['initial_fingerprint'],'teacher_initial_sha256':result['initial_teacher_sha256']}}
        with tempfile.TemporaryDirectory() as tmp:
            run=Path(tmp);(run/'snapshots').mkdir();(run/'snapshots/initial.snp').write_bytes(b'fixture')
            def admitted(value=result,m=manifest,model_sha='1'*64):
                with patch.object(nav,'read_json',return_value=m),patch('palimpsest.records.iter_ticks',return_value=iter(engine.saved)),\
                     patch.object(nav,'initial_ready'),patch.object(nav,'initial_match',return_value=result['initial_fingerprint']),\
                     patch('palimpsest.snapshots.read_snapshot',return_value={'identity':{'model_sha256':model_sha}}):
                    return nav.admit_record(run,value,identity)
            self.assertEqual(admitted(),3)
            changed=copy.deepcopy(result);changed['contact_incidence']['admitted_intervals']=2
            with self.assertRaisesRegex(ValueError,'incidence'):admitted(changed)
            changed=copy.deepcopy(result);changed['contact_incidence']['robot_world_pair_instances'][0]=False
            with self.assertRaisesRegex(ValueError,'incidence'):admitted(changed)
            with self.assertRaisesRegex(ValueError,'initial SNP'):admitted(model_sha='2'*64)
            changed=copy.deepcopy(manifest);changed['navigation_collection']['contact_profile_sha256']='2'*64
            with self.assertRaisesRegex(ValueError,'profile'):admitted(m=changed)
            changed=copy.deepcopy(result);changed['rows'][0]['contacts']['cached_bad']=True
            with self.assertRaisesRegex(ValueError,'Row contact incidence'):admitted(changed)

    def test_source_binding_no_model_read_and_bounded_result_publication(self):
        with patch.object(nav,'digest',return_value='2'*64):
            with self.assertRaisesRegex(ValueError,'Frozen v2 navigation plan'):nav.source_pins(Path('/fixture'))
        with patch.object(nav,'plan',return_value={'prior_version':{'collector_sha256':'1'*64}}),patch.object(nav,'digest',return_value='2'*64):
            with self.assertRaisesRegex(ValueError,'Frozen v1 collector'):nav.source_pins(Path('/fixture'))
        engine,_,result,_=self.source();result['rows']=result['rows']*200
        self.assertLess(len((json.dumps(result,indent=2)+'\n').encode()),4*nav.MiB)
        class Budget:
            def check(self,n,*,path):pass
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'result.json'
            nav.publish(path,result,Budget(),time.monotonic()+20,lambda:None)
            self.assertEqual(len(json.loads(path.read_text())['rows']),600)
            with self.assertRaisesRegex(ValueError,'4MiB'):nav.publish(Path(tmp)/'large.json',{'bytes':'x'*(4*nav.MiB)},Budget(),time.monotonic()+20,lambda:None)
            self.assertFalse((Path(tmp)/'large.json').exists())


if __name__=='__main__':unittest.main()
