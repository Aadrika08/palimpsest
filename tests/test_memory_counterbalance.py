"""Pure counterbalance admission fixtures; no acquired history or neural inference."""
import copy
from contextlib import contextmanager
import importlib.util
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np
from unittest.mock import patch

from palimpsest import memory, memory_experiment as experiment, memory_task


class CounterbalanceAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('counterbalance',cls.repo/'scripts/verify_memory_counterbalance.py')
        cls.runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.runner)

    def fixture(self,cell):
        """Declared synthetic before evidence, with actual pure capture at 299/300."""
        r=self.runner;case=r.make_case(cell)
        _,truth=experiment.make_case(*cell[:2],'development-test',kind=cell[2])
        facts=copy.deepcopy(case['facts']);samples=[]
        for i,fact in enumerate(facts):
            tick=100+i
            samples.append({'id':memory_task._sensor_id('episode-0',tick,'passage',fact['subject_id']),
                'episode_id':'episode-0','tick':tick,'subject_id':fact['subject_id'],'passability':'open'})
        for fact,sample in zip(facts,samples):
            fact.update(estimate='open',status='observed',origin='observed',
                evidence={k:sample[k] for k in ('id','episode_id','tick')})
        m=memory.seed_m(facts,samples)
        state=memory_task.initialize(m,{'version':1,'episodes':[]},memory.artifact(method='empty-v1'),'episode-0')
        pose=[-1.23,.6,.157]  # Fixed pure geometry fixture; not an asserted actual source pose.
        world={'common_goal_id':case['common_goal_id'],
            'cues':[{'id':case['cue_id'],'xy':case['cue_xy'],'state':0}],
            'landmarks':[{'id':case['common_goal_id'],'xy':r.common.effective_goal()}]+
                [{'id':next(f for f in facts if f['subject_id']==subject)['inspection_landmark_id'],'xy':xy}
                 for subject,xy in zip(case['subjects_by_side'],case['inspection_xy'])],
            'passages':[{'subject_id':f['subject_id'],'inspection_landmark_id':f['inspection_landmark_id'],
                'passability':'open'} for f in facts]}
        packet=memory_task.capture_symbolic(world,pose,truth['before_geometry'],episode_id='episode-0',tick=299)
        bearing=next(v['bearing_rad'] for v in packet['landmarks'] if v['id']==case['common_goal_id'])
        state['cursor']={'episode_id':'episode-0','tick':299,'packet_sha256':memory.sha256(packet),
            'common_goal_id':case['common_goal_id'],'bearing':[math.cos(bearing),math.sin(bearing)]}
        state['detector']={'tick':299,'cues':[{'id':case['cue_id'],'state':0,
            'observation_id':memory_task._sensor_id('episode-0',299,'cue',case['cue_id'])}]}
        state=memory_task.configure_selector(state,r.selector())
        source=copy.deepcopy(state)
        world['cues'][0]['state']=int(case['event_enabled'])
        for value in world['passages']:value['passability']=r.common.occupancy(case,truth['after_geometry'])[value['subject_id']]
        packet=memory_task.capture_symbolic(world,pose,truth['after_geometry'],episode_id='episode-0',tick=300)
        final,_,decisions=memory_task.advance_memory(state,packet)
        events=[{'kind':'memory_sensed','episode':0,'episode_step':300,'tick':300,'packet':packet}]+[
            {'kind':'memory_decision','episode':0,'episode_step':300,'tick':300,'detail':d} for d in decisions]
        report={'before_circles':truth['before_geometry'],'after_circles':truth['after_geometry'],
            'final_memory':final,'gate_result':'closed' if case['kind']=='change' else 'not_requested'}
        return case,{'application':{'memory':source}},report,{'events':events,'rows':[]}

    def test_all_48_cells_and_fixed_eight_cell_resource_plan(self):
        r=self.runner;rows=r.coverage()
        self.assertEqual(len(rows),48)
        self.assertEqual(len({v['cell'] for v in rows}),48)
        self.assertEqual(len({v['case_id'] for v in rows}),8)
        self.assertEqual({tuple(v['factors']) for v in rows},{(a,b,c) for a in (0,1) for b in (0,1) for c in (0,1)})
        for row in rows:
            self.assertEqual(row['synthetic_gold_count'],int(row['cell'].endswith('/change')))
        previous=set().union(*(experiment._ids(experiment.make_world_case(seed,'local_cue','development-test',acquisition=True))
            for seed in (0,1,2,3,8,9,16)))
        for cell in r.CELLS:
            case=r.make_case(cell)
            self.assertFalse(experiment._ids(case)&previous)
            self.assertTrue(all(f['status']=='unknown' and f['evidence'] is None for f in case['facts']))
        with tempfile.TemporaryDirectory() as root,patch.object(r,'source_identity',return_value={'fixture':True}):
            plan=r.make_plan(self.repo,Path(root)/'assets',Path(root)/'output')
            self.assertEqual(r.validate_plan(plan),plan)
            self.assertEqual(len({j['run_id'] for j in plan['jobs']}),24)
            self.assertEqual([j['stage'] for j in plan['jobs']],list(r.STAGES)*8)
            self.assertTrue(all(j['snapshot_path'] is None for j in plan['jobs']))
            self.assertEqual(plan['protocol']['outer_timeout_seconds'],3900)
            self.assertEqual(plan['protocol']['aggregate_max_bytes'],6*1024**3)
            self.assertIsNone(r.selector()['resource'])
            altered=copy.deepcopy(plan);altered['jobs'][1]['snapshot_path']='/tmp/forged.snp'
            with self.assertRaises(ValueError):r.validate_plan(altered)
            altered=copy.deepcopy(plan);altered['protocol']['version']=True
            with self.assertRaises(ValueError):r.validate_plan(altered)
            altered=copy.deepcopy(plan);altered['jobs'][0]['case']['kind']='null'
            with self.assertRaises(ValueError):r.validate_plan(altered)

    def test_change_gold_is_geometry_and_stale_observed_expectations_not_selection(self):
        r=self.runner
        for cell in (r.CELLS[0],r.CELLS[1],r.CELLS[4],r.CELLS[5]):
            case,native,report,data=self.fixture(cell)
            result=r.probe_result(case,native,report,data)
            self.assertEqual(len(result['gold_target_ids']),1)
            self.assertEqual(result['target_ids'],[])
            self.assertEqual(result['selector_invocations'],1)
            self.assertEqual(result['missed_targets'],1)
            self.assertIsNone(result['task_pass']);self.assertIsNone(result['goal_tick'])
            self.assertIsNone(result['correction_completion_tick'])
            self.assertEqual(bool(result['actual_stale_value_observations']),case['closure_subject_id']==case['subjects_by_side'][1])
            unknown=copy.deepcopy(native)
            unknown['application']['memory']['m']=memory.seed_m(case['facts'],[])
            self.assertEqual(r.probe_result(case,unknown,report,data)['gold_target_ids'],[])
            bad=copy.deepcopy(report);bad['after_circles']=bad['before_circles']
            with self.assertRaisesRegex(ValueError,'gate/clearance'):r.probe_result(case,native,bad,data)

    def test_null_has_real_trigger_empty_gold_and_actual_confirmation(self):
        r=self.runner
        for cell in (r.CELLS[2],r.CELLS[6]):
            case,native,report,data=self.fixture(cell);original=copy.deepcopy((native,report,data))
            result=r.probe_result(case,native,report,data)
            self.assertEqual(result['selector_invocations'],1)
            self.assertEqual(result['gold_target_ids'],[]);self.assertTrue(result['correct_abstention'])
            self.assertGreater(result['selector_behavior_bytes'],0)
            self.assertIsNone(result['precision']);self.assertIsNone(result['recall'])
            self.assertEqual(result['actual_post_event_confirmations'],[case['subjects_by_side'][1]])
            self.assertTrue(result['actual_recorded_revisions'])
            self.assertEqual((native,report,data),original)
            bad=copy.deepcopy(data)
            next(e['detail'] for e in bad['events'] if e['kind']=='memory_decision'
                 and e['detail']['kind']=='memory_selection')['selection']['target_ids']=[case['facts'][0]['id']]
            with self.assertRaisesRegex(ValueError,'trigger/selection'):r.probe_result(case,native,report,bad)

    def test_actual_packet_geometry_joins_subjects_and_rejects_hidden_pose_changes(self):
        r=self.runner
        for cell in r.CELLS:
            case,native,report,data=self.fixture(cell)
            data['rows']=[{'tick':300,'pose':np.array([-1.23,.6,.157],np.float64)}]
            data['events'].insert(0,{'kind':'episode_started','episode':0,'episode_step':300,'tick':300,
                'world':{'arena':15.,'pose':data['rows'][0]['pose'].tolist(),'goal':r.common.effective_goal()+[.2],
                    'obstacles':report['after_circles']}})
            packet,circles=r.actual_packet(data,case,native['application']['memory'])
            self.assertEqual(circles,report['after_circles'])
            self.assertEqual(packet,data['events'][1]['packet'])
            bad=copy.deepcopy(data);bad['rows'][0]['pose'][2]+=math.pi
            with self.assertRaisesRegex(ValueError,'pose/clearance'):r.actual_packet(bad,case,native['application']['memory'])

    def test_pre_next_owner_deadline_preserves_prior_pass_and_current_unattempted_id(self):
        r=self.runner
        with tempfile.TemporaryDirectory() as directory,patch.object(r,'source_identity',return_value={'fixture':True}):
            root=Path(directory);plan=r.make_plan(self.repo,root/'assets',root/'output')
            first=plan['jobs'][0];run=Path(first['output'])
            def owner(*args,**kwargs):
                run.mkdir(parents=True)
                (run/'retained.json').write_text('{}')
                (run/'admission-worker.json').write_text('{}')
                (run/'initial.snp').write_bytes(b'pure fixture')
                return {'status':'completed','returncode':0}
            @contextmanager
            def lease():
                Path(plan['output']).mkdir()
                yield
            def admission(*args):
                paths=[run/'retained.json']
                data={'run':run,'paths':paths,'fingerprint':r.artifacts._fingerprint(paths)}
                report={'snapshot_path':str(run/'initial.snp'),'snapshot_sha256':r.common._hash(run/'initial.snp'),
                    'final_phase':'paused','non_u':{'fixture':'native'}}
                return data,report,{}, {'sha256':report['snapshot_sha256']}
            with patch.object(r,'bounded_process',side_effect=owner) as process, \
                    patch.object(r,'validate_stage',side_effect=admission), \
                    patch.object(r.common,'baseline_invariants',return_value={'fixture':'native'}), \
                    patch.object(r.StorageBudget,'lock',side_effect=lease), \
                    patch.object(r.shutil,'disk_usage',return_value=SimpleNamespace(free=16*r.GiB)), \
                    patch.object(r.time,'monotonic',side_effect=[0.,0.,4000.,4001.]):
                result=r.run_verifier(plan)
            process.assert_called_once()
            self.assertEqual(result['status'],'admission_unverified')
            self.assertTrue(result['runs'][0]['admission_pass'])
            self.assertNotIn('failure',result['runs'][0])
            self.assertEqual(result['first_failure']['scope'],'before-owner')
            self.assertEqual(result['first_failure']['run_id'],plan['jobs'][1]['run_id'])
            self.assertEqual(len(result['unattempted_stages']),23)
            self.assertEqual(result['unattempted_stages'][0]['run_id'],plan['jobs'][1]['run_id'])
            self.assertTrue(result['source_unchanged']);self.assertTrue(result['retained_unchanged'])

    def test_no_event_has_no_trigger_no_selector_cost_and_rejects_fabrication(self):
        r=self.runner
        for cell in (r.CELLS[3],r.CELLS[7]):
            case,native,report,data=self.fixture(cell);result=r.probe_result(case,native,report,data)
            self.assertIsNone(result['trigger']);self.assertEqual(result['selector_invocations'],0)
            self.assertEqual(result['selector_behavior_bytes'],0);self.assertEqual(result['gold_target_ids'],[])
            self.assertTrue(result['correct_abstention'])
            self.assertEqual(result['actual_post_event_confirmations'],[case['subjects_by_side'][1]])
            bad=copy.deepcopy(data);bad['events'].append({'kind':'memory_decision','episode':0,'episode_step':300,'tick':300,
                'detail':{'kind':'memory_selection','selection':{'event_id':None,'target_ids':[],'reason':'no_rule'}}})
            with self.assertRaisesRegex(ValueError,'No-event'):r.probe_result(case,native,report,bad)
            for change in (lambda p:p['cues'].clear(),lambda p:p['cues'][0].update(state=1),
                           lambda p:p['landmarks'].clear(),lambda p:p.update(episode_id='wrong')):
                bad=copy.deepcopy(data);change(bad['events'][0]['packet'])
                with self.assertRaises(ValueError):r.probe_result(case,native,report,bad)
            bad=copy.deepcopy(data);bad['events'][0]['tick']=301
            with self.assertRaisesRegex(ValueError,'sensing packet'):r.probe_result(case,native,report,bad)


if __name__=='__main__':unittest.main()
