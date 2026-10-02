"""Pure transfer preparation checks; fixtures do not establish actual transfer."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import uuid

import numpy as np

from palimpsest import memory, memory_experiment as experiment


class VerifierBoundaries(unittest.TestCase):
    def setUp(self):
        self.repo = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('verify_memory_transfer',
            self.repo / 'scripts/verify_memory_transfer.py')
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.histories = {role: {'e': experiment.make_history(seed, relation)}
            for role, seed, relation in [('own', 0, 'local_cue'), ('swapped', 9, 'paired_cue')]}
        for role, value in self.histories.items():
            value.update(u=memory.fit(value['e']), path=role+'.json', sha256='0'*64)

    def plan(self, output=None):
        with patch.object(self.runner, 'load_histories', return_value=self.histories):
            return self.runner.make_plan(self.repo, self.root/'assets', output or self.root/'comparison')

    def test_goal_handoff_uses_paused_command_without_memory_or_physics_advance(self):
        from palimpsest.engine import Engine
        from palimpsest.records import RunWriter
        from test_engine import SmallEnv
        case=experiment.make_world_case(8,'local_cue','development-test',acquisition=True)
        run=self.root/uuid.uuid4().hex
        env=SmallEnv()
        engine=Engine(env,RunWriter(run/'recording',{'run_id':run.name}),scenario='sparse-navigation')
        env._goal_xy=np.asarray(case['goal_xy'],np.float32)
        env.model.site_pos=np.asarray([case['goal_xy']+[0.]],np.float64)
        env.model.jnt_range=np.zeros((1,2));env.model.geom_rgba=np.ones((1,4))
        env.data.qpos[:]=[-1.2342,.6054,math.pi/20]
        env.cached_xy=env.data.qpos[:2].astype(np.float32)+np.array([1e-6,-1e-6],np.float32)
        env._base_xy=lambda:env.cached_xy.copy()
        engine.episode_step=engine.total_tick=300
        engine.memory={'m':memory.seed_m(case['facts'],[]),'e':{'version':1,'episodes':[]},
            'u':memory.artifact(method='empty-v1'),'cursor':{'tick':299},'episode_id':'episode-0'}
        engine.world_task_state={}
        before=copy.deepcopy(engine.memory)
        def change(actual,payload,teacher=None):
            self.assertEqual(payload,{'kind':'move_goal','xy':[-.5,-2.7]})
            old=actual._goal_xy.tolist();actual._goal_xy[:]=payload['xy']
            actual.model.site_pos[0,:2]=actual._goal_xy
            actual.cached_xy=actual.data.qpos[:2].astype(np.float32)
            return {'kind':'move_goal','old':{'xy':old},'new':{'xy':actual._goal_xy.tolist()},'simulation_time':actual.data.time}
        def sensing(actual,state):
            world={'cues':[{'id':case['cue_id'],'xy':case['cue_xy'],'state':0}],
                'landmarks':[{'id':case['common_goal_id'],'xy':actual._goal_xy.tolist()}]+
                  [{'id':f['inspection_landmark_id'],'xy':xy} for f,xy in zip(case['facts'],case['inspection_xy'])],
                'passages':[{'subject_id':f['subject_id'],'inspection_landmark_id':f['inspection_landmark_id'],
                    'passability':'open'} for f in case['facts']], 'common_goal_id':case['common_goal_id']}
            return world,[*actual._base_xy().tolist(),float(actual._base_yaw())],[]
        try:
            with patch('palimpsest.interventions.apply_intervention',side_effect=change), \
                 patch.object(self.runner.memory_world,'sensing_inputs',side_effect=sensing), \
                 patch.object(self.runner,'integration_digest',return_value=(self.runner.state_digest(np.array([1.])),123)):
                proof=self.runner.apply_goal_handoff(engine,case)
            self.assertEqual(engine.memory,before)
            self.assertEqual((engine.total_tick,engine.episode_step,env.calls),(300,300,0))
            self.assertEqual(proof['receipt']['status'],'applied')
            self.assertEqual(proof['effective_goal_xy'],np.asarray([-.5,-2.7],np.float32).astype(float).tolist())
            events=self.runner.artifacts._events(run)
            self.assertFalse(any(e['kind']=='memory_sensed' for e in events))
            self.assertEqual(len([e for e in events if e['kind']=='goal_handoff_probe']),1)
            self.assertEqual(self.runner.PROTOCOL['version'],5)
            self.assertNotEqual(proof['before_world']['pose'],proof['world']['pose'])
            self.assertEqual(proof['authoritative_before_sha256'],proof['authoritative_after_sha256'])
            native={'environment':{'values':{'_goal_xy':env._goal_xy.copy()},'absent':[]},
                'integration':np.array([1.]),'integration_enum':123,'application':{
                'original_commands':copy.deepcopy(engine._originals),'receipts':engine.receipts,
                'memory':copy.deepcopy(engine.memory),'event_prefix':{'event_count':len(events)}}}
            data={'events':events,'rows':[{'next_pose':np.asarray(proof['before_world']['pose'])}]}
            self.runner.validate_goal_handoff(data,native,case,'source')
            for mutate in (
                lambda d,n:d['events'][-1]['proof'].__setitem__('memory_before_sha256','0'*64),
                lambda d,n:d['events'][-1]['proof']['packet']['landmarks'].pop(0),
                lambda d,n:n['environment']['values']['_goal_xy'].__setitem__(1,2.7),
                lambda d,n:n['application']['receipts'][self.runner.GOAL_HANDOFF['command_id']].__setitem__('applied_tick',299),
                lambda d,n:n['application']['receipts'][self.runner.GOAL_HANDOFF['command_id']].__setitem__('applied_episode',False),
                lambda d,n:n['application']['event_prefix'].__setitem__('event_count',0),
                lambda d,n:d['rows'][-1]['next_pose'].__setitem__(0,0.),
                lambda d,n:n['integration'].__setitem__(0,2.),
                lambda d,n:d['events'][-1]['proof'].__setitem__('authoritative_after_sha256','0'*64)):
                bad_data,bad_native=copy.deepcopy((data,native))
                mutate(bad_data,bad_native)
                with self.assertRaises(ValueError):
                    self.runner.validate_goal_handoff(bad_data,bad_native,case,'source')
        finally:
            engine.close()

        # A real authoritative position change cannot pass as a cache refresh.
        bad_run=self.root/uuid.uuid4().hex
        bad_env=SmallEnv();bad_env.model.site_pos=np.zeros((1,3))
        bad_env.model.jnt_range=np.zeros((1,2));bad_env.model.geom_rgba=np.ones((1,4))
        bad_engine=Engine(bad_env,RunWriter(bad_run/'recording',{'run_id':bad_run.name}),scenario='sparse-navigation')
        bad_engine.episode_step=bad_engine.total_tick=300
        bad_engine.memory=copy.deepcopy(before)
        def moved(actual,payload,teacher=None):
            actual.data.qpos[0]+=1e-6;actual._goal_xy=np.asarray(payload['xy'],np.float32)
            actual.model.site_pos[0,:2]=actual._goal_xy
            return {'kind':'move_goal','old':{'xy':[5.,0.]},'new':{'xy':actual._goal_xy.tolist()},'simulation_time':0.}
        try:
            with patch('palimpsest.interventions.apply_intervention',side_effect=moved), \
                 patch.object(self.runner,'integration_digest',return_value=('not-captured',123)):
                with self.assertRaisesRegex(ValueError,'changed memory/physics'):
                    self.runner.apply_goal_handoff(bad_engine,case)
            failed_events=self.runner.artifacts._events(bad_run)
            state=next(e['proof'] for e in failed_events if e['kind']=='goal_handoff_state')
            self.assertNotEqual(state['authoritative_before_sha256'],state['authoritative_after_sha256'])
            self.assertFalse(any(e['kind']=='goal_handoff_probe' for e in failed_events))
        finally:
            bad_engine.close()

    def test_authoritative_guard_covers_optional_inputs_and_integration_representation(self):
        from types import SimpleNamespace
        import sys
        from test_engine import SmallEnv
        env=SmallEnv();env.model.site_pos=np.ones((2,3));env.model.jnt_range=np.zeros((1,2));env.model.geom_rgba=np.ones((1,4))
        for name in ('act','mocap_pos','mocap_quat','qfrc_applied','xfrc_applied','eq_active'):
            setattr(env.data,name,np.zeros(2))
        base=self.runner.authoritative_digest(env)
        env.model.site_pos[0,:2]=[-.5,-2.7]
        self.assertEqual(self.runner.authoritative_digest(env),base)
        for owner,name in [(env.data,n) for n in ('qpos','qvel','ctrl','act','mocap_pos','mocap_quat',
                'qfrc_applied','xfrc_applied','eq_active')]+[(env.model,n) for n in ('jnt_range','geom_rgba','geom_size')]:
            old=getattr(owner,name).copy();getattr(owner,name).flat[0]+=1e-6
            self.assertNotEqual(self.runner.authoritative_digest(env),base,name)
            setattr(owner,name,old)
        env.model.site_pos[0,2]+=1e-6
        self.assertNotEqual(self.runner.authoritative_digest(env),base,'goal z cannot change')
        env.model.site_pos[0,2]-=1e-6
        env.model.site_pos[1,0]+=1e-6
        self.assertNotEqual(self.runner.authoritative_digest(env),base,'other site cannot change')
        env.model.site_pos[1,0]-=1e-6
        env.data.time=1e-6
        self.assertNotEqual(self.runner.authoritative_digest(env),base,'time cannot advance')
        def get(model,data,out,kind):out[:]=[1.,2.,3.]
        module=SimpleNamespace(mjtState=SimpleNamespace(mjSTATE_INTEGRATION=123),
            mj_stateSize=lambda model,kind:3,mj_getState=get)
        with patch.dict(sys.modules,{'mujoco':module}):
            self.assertEqual(self.runner.integration_digest(env),(self.runner.state_digest(np.array([1.,2.,3.])),123))

    def test_fixed_source_override_is_bounded_and_keeps_continuation_separate(self):
        case = experiment.make_world_case(8, 'local_cue', 'development-test', acquisition=True)
        other = experiment.make_world_case(9, 'paired_cue', 'development-test', acquisition=True)
        pose = [-1.3, .626, math.pi/2]
        schedule = case['acquisition_schedule']
        self.assertEqual(self.runner.source_action(schedule, pose, 199), experiment.acquisition_action(schedule, pose, 199))
        for tick in (200, 299):
            action = self.runner.source_action(schedule, pose, tick)
            self.assertEqual(action, [0., -.35])
            self.assertEqual(action, self.runner.source_action(other['acquisition_schedule'], pose, tick))
        self.assertEqual(self.runner.source_action(schedule, [-1.3,.626,math.pi/20], 299), [0.,0.])
        for tick in (True, -1, 300):
            with self.assertRaises(ValueError):
                self.runner.source_action(schedule, pose, tick)
        self.assertEqual(self.runner.cue_action([1.,0.]), [.65,0.])
        self.assertEqual(self.runner.PROTOCOL['version'], 5)
        self.assertEqual(self.runner.SOURCE_PREPARATION['access'], 'privileged-manual-pose-supervision')
        self.assertFalse(self.runner.SOURCE_PREPARATION['uses_u'])

    def test_visibility_admission_requires_recorded_cues_landmarks_and_evidence(self):
        from palimpsest import memory_task
        case = experiment.make_world_case(8, 'local_cue', 'development-test', acquisition=True)
        world = {'cues':[{'id':case['cue_id'],'xy':case['cue_xy'],'state':0}],
            'landmarks':[{'id':case['common_goal_id'],'xy':case['goal_xy']}] +
                [{'id':f['inspection_landmark_id'],'xy':case['inspection_xy'][i]} for i,f in enumerate(case['facts'])],
            'passages':[{'subject_id':f['subject_id'],'inspection_landmark_id':f['inspection_landmark_id'],
                'passability':'open'} for f in case['facts']], 'common_goal_id':case['common_goal_id']}
        packets = [memory_task.capture_symbolic(world,pose,[],episode_id='episode-0',tick=tick)
            for tick,pose in [(29,[-1.3,-1.1,math.pi/2]),(199,[-1.3,.626,math.pi/2]),
                              (299,[-1.3,.626,math.pi/20])]]
        m = memory.seed_m(case['facts'], [])
        for packet in packets[:2]:
            m = memory.revise(m, None, {'event_id':None,'target_ids':[],'reason':'no_rule'},
                packet['passages'],episode_id='episode-0',tick=packet['tick'])[0]
        state = {'m':m,'episode_id':'episode-0'}
        events = [{'kind':'memory_sensed','episode':0,'episode_step':p['tick'],'tick':p['tick'],'packet':p} for p in packets]
        admitted = self.runner.preparation_packet(events,case,state,299)
        self.assertEqual(admitted,packets[-1])
        self.runner.evidence_backed_source(m,events,'episode-0')
        angle=next(v['bearing_rad'] for v in packets[-1]['landmarks'] if v['id']==case['common_goal_id'])
        state.update(active=None,cursor={'episode_id':'episode-0','tick':299,
            'packet_sha256':memory.sha256(packets[-1]),'common_goal_id':case['common_goal_id'],
            'bearing':[math.cos(angle),math.sin(angle)]}, detector={'tick':299,'cues':[{
                'id':case['cue_id'],'state':0,'observation_id':memory_task._sensor_id('episode-0',299,'cue',case['cue_id'])}]})
        self.runner.packet_cursor(packets[-1],state)
        for section,key,value in [('cursor','packet_sha256','0'*64),('cursor','bearing',[1.,0.]),
                                  ('detector','tick',298)]:
            bad=copy.deepcopy(state)
            bad[section][key]=value
            with self.assertRaises(ValueError):
                self.runner.packet_cursor(packets[-1],bad)
        for mutate in (
            lambda p:p['landmarks'].pop(0),
            lambda p:p['cues'].clear(),
            lambda p:p['passages'][0].__setitem__('passability','open'),
            lambda p:p.__setitem__('tick',298)):
            bad = copy.deepcopy(events)
            mutate(bad[-1]['packet'])
            with self.assertRaises(ValueError):
                self.runner.preparation_packet(bad,case,state,299)
        bad_m = copy.deepcopy(m)
        bad_m['facts'][0]['evidence']['id']='fabricated-evidence'
        with self.assertRaises(ValueError):
            self.runner.evidence_backed_source(bad_m,events,'episode-0')

    def test_source_override_controls_and_declaration_cannot_be_relabelled(self):
        case = experiment.make_world_case(8,'local_cue','development-test',acquisition=True)
        pose=np.array([-1.3,.626,math.pi/2],np.float64)
        rows=[{'tick':t,'pose':pose.copy(),'action':np.array([0.,-.35],np.float64)} for t in range(200,300)]
        events=[{'kind':'source_preparation_input','episode':0,'episode_step':t,'tick':t,
            'pose':pose.tolist(),'action':[0.,-.35], 'source_preparation_sha256':self.runner.SOURCE_PREPARATION_SHA256}
            for t in range(200,300)]
        data={'rows':rows,'events':events}
        self.runner.source_controls(data,case)
        for mutate in (
            lambda d:d['events'].pop(),
            lambda d:d['rows'][0]['action'].__setitem__(0,.65),
            lambda d:d['events'][0]['pose'].__setitem__(2,0.),
            lambda d:d['events'][0].__setitem__('source_preparation_sha256','0'*64)):
            bad=copy.deepcopy(data)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.runner.source_controls(bad,case)
        fixture=self.fixture('anchor')
        self.admit(fixture)
        for mutate in (
            lambda f:f[1]['manifest'].__setitem__('source_preparation_sha256','0'*64),
            lambda f:next(e for e in f[1]['events'] if e['kind']=='source_preparation_declared')
                ['protocol'].__setitem__('uses_u',0),
            lambda f:next(e for e in f[1]['events'] if e['kind']=='source_preparation_declared')
                .__setitem__('sequence',1000)):
            bad=copy.deepcopy(fixture)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.admit(bad)

    def fixture(self, stage='own', *, failed=False):
        job = next(j for j in self.plan()['jobs'] if j['stage']==stage)
        job['expected_non_u'] = {'native': 'fixture-hash'}
        run = Path(job['output'])
        run.mkdir(parents=True)
        u = self.runner.condition_u(stage,self.histories)
        native = {'application': {'world_task_state': {'case': job['case']}, 'event_prefix':{'event_count':1000},
            'memory': {'u': u, 'cursor': {'bearing': [1., 0.],'tick':299,'episode_id':'episode-0',
                'packet_sha256':'0'*64,'common_goal_id':job['case']['common_goal_id']}, 'episode_id':'episode-0',
                       'm':memory.seed_m(job['case']['facts'],[])}}}
        native['application']['memory']['version']=1 if stage=='source' else 2
        native['application']['memory'].update(e={'version':1,'episodes':[]},
            initial_m=copy.deepcopy(native['application']['memory']['m']),requests=[],active=None,last_decisions=[],
            detector={'tick':299,'cues':[{'id':job['case']['cue_id'],'state':0,
                'observation_id':self.runner.memory_task._sensor_id('episode-0',299,'cue',job['case']['cue_id'])}]})
        if stage!='source':
            native['application']['memory']['selector']=job['selector']
        identifier=self.runner.GOAL_HANDOFF['command_id']
        native['environment']={'values':{'_goal_xy':np.asarray(self.runner.GOAL_HANDOFF['xy'],np.float32)},'absent':[]}
        native['application']['original_commands']={identifier:{'id':identifier,'kind':'intervene',
            'expected_state':'paused','expected_episode':0,'expected_revision':7,
            'payload':{'kind':'move_goal','xy':self.runner.GOAL_HANDOFF['xy']}}}
        native['application']['receipts']={identifier:{'id':identifier,'kind':'intervene','status':'applied',
            'received_tick':300,'applied_tick':300,'received_episode':0,'applied_episode':0,'applied_revision':8,
            'received_run_id':'source-fixture','applied_run_id':'source-fixture'}}
        outcome = ({'type': 'CueUnavailable', 'reason': 'runtime_failure',
            'message': 'goal_cue_unavailable: fixture', 'episode': 0, 'steps': 301} if failed else None)
        report = {'status': 'recorded', 'block':job['block'], 'stage': stage, 'run_path': str(run),
            'initial_non_u': job['expected_non_u'], 'final_phase': 'failed' if failed else 'paused',
            'outcome': outcome, 'steps': 300 if stage in ('source', 'anchor') else 301,
            'final_memory': {'requests': [{'fact_id': 'fixture-fact'}] if failed else [], 'active': None}}
        manifest = {'memory_case': job['case'], 'memory_case_sha256': memory.sha256(job['case']),
            'transfer_protocol': self.runner.PROTOCOL, 'transfer_protocol_sha256': self.runner.PROTOCOL_SHA256,
            'transfer_driver_sha256': job['source_identity']['driver_sha256'], 'transfer_stage': stage,
            'transfer_block':job['block'],'selector_configuration':job['selector'],
            'selector_configuration_sha256':memory.sha256(job['selector']),
            'oracle_evidence':job['oracle_evidence'],
            'semantic_case_sha256':memory.sha256(self.runner.semantic_case(job['case'])),
            'source_preparation_protocol':self.runner.SOURCE_PREPARATION,
            'source_preparation_sha256':self.runner.SOURCE_PREPARATION_SHA256,
            'acquisition_schedule_override':self.runner.ACQUISITION_OVERRIDE,
            'goal_handoff_protocol':self.runner.GOAL_HANDOFF,'goal_handoff_sha256':self.runner.GOAL_HANDOFF_SHA256,
            'controller': 'manual', 'requested_device': 'cpu', 'seed': 8,
            'recording_max_bytes': self.runner.PROTOCOL['recording_max_bytes'],
            'close_reason': 'operator_closed', 'status': 'failed' if failed else 'completed',
            'final_phase': report['final_phase'], 'last_outcome': outcome, 'total_tick': report['steps']}
        events = [{'kind': 'environment', **{k: job['source_identity'][k]
            for k in ('source_sha256', 'lock_sha256', 'upstream_commit')}}]
        rows = [] if stage=='anchor' else [{'episode': 0, 'tick': 300,
            'action': np.array([.65, 0.], dtype=np.float64),'pose':np.asarray([-1.3,.626,math.pi/20])}]
        if stage not in ('source', 'anchor'):
            events.append({'kind': 'transfer_driver_input', 'episode': 0, 'episode_step': 300,
                'bearing_tick': 299, 'bearing': [1., 0.], 'action': [.65, 0.]})
            if failed:
                events += [{'kind': 'memory_cue', 'episode_step': 300, 'bearing': [1., 0.]},
                    {'kind': 'transfer_driver_input', 'episode': 0, 'episode_step': 301,
                     'bearing_tick': 300, 'bearing': [1., 0.], 'action': [.65, 0.]},
                    {'kind': 'runtime_failure', 'episode': 0, 'episode_step': 301, 'error': outcome}]
        events.append({'kind':'source_preparation_declared','sequence':0,
            'protocol':self.runner.SOURCE_PREPARATION,'source_preparation_sha256':self.runner.SOURCE_PREPARATION_SHA256,
            'override':self.runner.ACQUISITION_OVERRIDE})
        if stage!='source':
            events.append({'kind':'selector_configured','sequence':1,'tick':300,'episode':0,'episode_step':300,
                'configuration':job['selector'],'configuration_sha256':memory.sha256(job['selector'])})
        if stage not in ('source','anchor'):
            from palimpsest import memory_task
            case=job['case']
            world={'cues':[{'id':case['cue_id'],'xy':case['cue_xy'],'state':1}],
                'landmarks':[{'id':case['common_goal_id'],'xy':self.runner.effective_goal()}]+
                    [{'id':f['inspection_landmark_id'],'xy':case['inspection_xy'][i]} for i,f in enumerate(case['facts'])],
                'passages':[{'subject_id':f['subject_id'],'inspection_landmark_id':f['inspection_landmark_id'],
                             'passability':'open'} for f in case['facts']], 'common_goal_id':case['common_goal_id']}
            packet=memory_task.capture_symbolic(world,[-1.3,.626,math.pi/20],[],episode_id='episode-0',tick=300)
            events.append({'kind':'memory_sensed','episode':0,'episode_step':300,'tick':300,'packet':packet})
            report['visibility_admission']={'300':memory.sha256(packet)}
            angle=next(v['bearing_rad'] for v in packet['landmarks'] if v['id']==case['common_goal_id'])
            bearing=[math.cos(angle),math.sin(angle)]
            state={'m':{'facts':case['facts']},'active':None,
                'cursor':{'episode_id':'episode-0','tick':300,'packet_sha256':memory.sha256(packet),
                          'common_goal_id':case['common_goal_id'],'bearing':bearing},
                'detector':{'tick':300,'cues':[{'id':case['cue_id'],'state':1,
                    'observation_id':memory_task._sensor_id('episode-0',300,'cue',case['cue_id'])}]}}
            report['boundary_memory']={'300':self.runner.packet_cursor(packet,state)}
            events.append({'kind':'memory_inspected','episode_step':300,
                'memory':{'active':None,'facts':case['facts'],'facts_truncated':0}})
            if failed:
                next(e for e in events if e['kind']=='memory_cue')['bearing']=bearing
                events[3]['bearing']=bearing
                events[3]['action']=self.runner.cue_action(bearing)
            else:
                events.append({'kind':'memory_cue','episode_step':300,'bearing':bearing})
            events.append({'kind':'application_restored','episode':0,'episode_step':300,'world':{
                'arena':7.,'pose':[-1.3,.626,math.pi/20],'obstacles':[],
                'goal':self.runner.effective_goal()+[.25]}})
        data = {'run': run, 'manifest': manifest, 'events': events, 'rows': rows}
        report['final_memory']=copy.deepcopy(native['application']['memory'])
        if stage not in ('source','anchor'):
            report['final_memory'].update(cursor=copy.deepcopy(state['cursor']),detector=copy.deepcopy(state['detector']))
            if failed:
                report['final_memory']['requests']=[{'event_id':'fixture-event',
                    'fact_id':job['case']['facts'][0]['id'],'requested_tick':300}]
        return job, data, report, native

    def admit(self, fixture):
        job, data, report, native = fixture
        (Path(job['output'])/'transfer-worker.json').write_text(json.dumps(report))
        # Numeric/native readers have separate real-format checks below and in
        # snapshot tests. These fixtures isolate admission, not physics.
        with patch.object(self.runner, 'read_run', return_value=data), \
             patch.object(self.runner, '_initial_snapshot', return_value=(native, {}, [])), \
             patch.object(self.runner, 'invariant_hashes', return_value={'native': 'fixture-hash'}), \
             patch.object(self.runner, 'load_histories', return_value=self.histories):
            return self.runner.validate_stage(job, {'status': 'completed', 'returncode': 0})

    def test_recorded_actions_exact_ticks_native_u_and_failed_attempt_boundary(self):
        for stage in ('swapped', 'sham', 'no-U'):
            self.admit(self.fixture(stage))
        good = self.fixture()
        self.admit(good)
        for mutate in (
            lambda f: f[1]['rows'][0]['action'].__setitem__(0, .66),
            lambda f: f[1]['rows'][0].__setitem__('action', np.array([.65, 0.], np.float32)),
            lambda f: f[1]['events'][1].__setitem__('episode_step', 301),
            lambda f: f[2]['boundary_memory']['300']['cursor'].__setitem__('packet_sha256','0'*64),
            lambda f: f[3]['application']['memory'].__setitem__('u', self.histories['swapped']['u']),
            lambda f: f[3]['application']['memory']['selector'].__setitem__('provenance_sha256','1'*64),
            lambda f: f[3]['environment']['values']['_goal_xy'].__setitem__(1,2.7),
            lambda f: f[3]['application']['receipts'][self.runner.GOAL_HANDOFF['command_id']].__setitem__('applied_episode',False),
            lambda f: next(e for e in f[1]['events'] if e['kind']=='application_restored')['world']['goal'].__setitem__(1,2.7),
            lambda f: next(e for e in f[1]['events'] if e['kind']=='memory_sensed')['packet']['landmarks'][0].__setitem__('bearing_rad',0.),
            lambda f: f[1]['manifest'].__setitem__('last_outcome', {'type': 'forged'})):
            bad = copy.deepcopy(good)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.admit(bad)
        failed = self.fixture(failed=True)
        self.admit(failed)
        for mutate in (
            lambda f: f[1]['events'].pop(3),  # missing last attempted driver tick
            lambda f: f[1]['events'].insert(4, copy.deepcopy(f[1]['events'][3])),
            lambda f: next(e for e in f[1]['events'] if e['kind']=='runtime_failure').__setitem__('episode_step', 302),
            lambda f: f[1]['manifest'].__setitem__('close_reason', 'forced_cleanup')):
            bad = copy.deepcopy(failed)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.admit(bad)

    def test_anchor_and_source_require_paused_exact_pre_event_boundary(self):
        anchor = self.fixture('anchor')
        self.admit(anchor)
        for mutate in (
            lambda f: f[2].__setitem__('steps', 299),
            lambda f: f[2].__setitem__('final_phase', 'terminated'),
            lambda f: f[3]['application']['memory']['cursor'].__setitem__('tick',298),
            lambda f: f[3]['application']['memory'].__setitem__('u', memory.artifact(method='empty-v1'))):
            bad = copy.deepcopy(anchor)
            mutate(bad)
            with self.assertRaises(ValueError):
                self.admit(bad)
        source = self.fixture('source')
        # A short/fabricated row list cannot enter collector/source checks.
        with self.assertRaisesRegex(ValueError, 'exact pre-event prefix'):
            self.admit(source)
        source[2]['final_phase'] = source[1]['manifest']['final_phase'] = 'terminated'
        with self.assertRaisesRegex(ValueError, 'finish paused'):
            self.admit(source)

    def test_history_pins_refit_identity_plan_bounds_and_first_failure_stop(self):
        inputs = {}
        for role, value in self.histories.items():
            path = self.root/(role+'.json')
            path.write_text(json.dumps({'e': value['e'], 'u': value['u'],
                'history_sha256': memory.sha256(value['e'])}))
            inputs[role] = (path.name, self.runner._hash(path))
        with patch.object(self.runner, 'HISTORY_INPUTS', inputs):
            self.assertEqual(self.runner.load_histories(self.root)['own']['u'], self.histories['own']['u'])
            bundle = json.loads((self.root/'own.json').read_text())
            bundle['u'] = self.histories['swapped']['u']
            (self.root/'own.json').write_text(json.dumps(bundle))
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                self.runner.load_histories(self.root)
            inputs['own'] = ('own.json', self.runner._hash(self.root/'own.json'))
            with self.assertRaisesRegex(ValueError, 'E-only refit'):
                self.runner.load_histories(self.root)
        plan = self.plan()
        self.assertEqual([(j['block'],j['stage']) for j in plan['jobs']],
                         [(b['id'],s) for b in self.runner.BLOCKS for s in self.runner.STAGES])
        self.assertEqual(len({j['run_id'] for j in plan['jobs']}), 22)
        self.assertEqual(plan['protocol']['source_prefix_ticks'], 300)
        self.assertEqual(plan['protocol']['remaining_ticks'], 300)
        self.assertEqual(plan['protocol']['retries'], 0)
        self.assertEqual({j['case']['seed'] for j in plan['jobs']},{8,9})
        self.assertTrue(all(j['case']['split']=='development-test' for j in plan['jobs']))
        self.assertTrue(all(j['selector'] is None for j in plan['jobs'] if j['stage'] in ('source','oracle')))
        for block in self.runner.BLOCKS:
            jobs={j['stage']:j for j in plan['jobs'] if j['block']==block['id']}
            own=self.histories['own' if block['seed']==8 else 'swapped']
            self.assertEqual(jobs['retrieval']['selector']['resource'],own['e'])
            self.assertTrue(all(j['selector']['resource'] is None for s,j in jobs.items()
                                if s not in ('retrieval','oracle','source')))
        self.assertFalse(Path(plan['output']).exists())
        forged=copy.deepcopy(plan)
        forged['case_identities']['local-8']['canonical_case_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'case provenance/semantic'):
            self.runner.run_verifier(forged)
        self.assertFalse(Path(plan['output']).exists())
        forged=copy.deepcopy(plan)
        oracle=next(j for j in forged['jobs'] if j['stage']=='oracle')
        oracle['selector']=self.runner.selector_config('oracle',self.histories,
            {'gold_target_ids':[oracle['case']['facts'][0]['id']]})
        with self.assertRaisesRegex(ValueError,'unacquired gold'):
            self.runner.run_verifier(forged)
        self.assertFalse(Path(plan['output']).exists())
        with patch.object(self.runner, 'bounded_process', return_value={'status': 'timeout', 'returncode': -15}) as child, \
             patch.object(self.runner, 'load_histories', return_value=self.histories), \
             patch.object(self.runner, 'print', create=True):
            result = self.runner.run_verifier(plan)
        self.assertEqual(child.call_count, 1)
        self.assertEqual(result['status'], 'mechanism_unverified')
        self.assertEqual(result['runs'][0]['stage'], 'source')
        self.assertEqual([(s['block'],s['stage']) for s in result['unattempted_stages']],
                         [(j['block'],j['stage']) for j in plan['jobs'][1:]])
        self.assertIn('no retry', result['first_failure']['message'])
        self.assertEqual(json.loads((Path(plan['output'])/'transfer-report.json').read_text()), result)
        for bearing in ([0., 0.], [True, 0.], [float('nan'), 0.], [1., 0., 99], {'pose': [0, 0, 0]}):
            with self.assertRaises(ValueError):
                self.runner.cue_action(bearing)
        self.assertEqual(self.runner.cue_action([0., -1.]), [.65, -math.pi/2])

    def test_expected_engine_failure_preserves_terminal_status_and_chunk_hashes(self):
        from palimpsest.engine import Engine
        from palimpsest.memory_task import CueUnavailable
        from palimpsest.records import RunWriter
        from test_engine import SmallEnv
        run = self.root/uuid.uuid4().hex
        engine = Engine(SmallEnv(), RunWriter(run/'recording', {'run_id': run.name}),
            scenario='sparse-navigation')
        self.runner._command_step(engine, [.65, .125], 'fixture')
        engine._fail(CueUnavailable('goal_cue_unavailable: fixture'))
        engine.close()
        data = self.runner.read_run(run)
        self.assertEqual(data['manifest']['status'], 'failed')
        self.assertEqual(data['manifest']['final_phase'], 'failed')
        self.assertEqual(data['manifest']['close_reason'], 'operator_closed')
        self.assertEqual(data['manifest']['last_outcome']['type'], 'CueUnavailable')
        np.testing.assert_array_equal(data['rows'][0]['action'], np.array([.65, .125], np.float64))
        chunk = next(p for p in data['paths'] if p.suffix=='.npz')
        chunk.write_bytes(chunk.read_bytes()+b'corruption')
        with self.assertRaises(ValueError):
            self.runner.read_run(run)

    def test_selector_normalization_preserves_all_other_scientific_state(self):
        from palimpsest import memory_task
        from palimpsest.snapshots import SNAPSHOT_KEYS
        case=experiment.make_world_case(8,'local_cue','development-test',acquisition=True)
        state=memory_task.initialize(memory.seed_m(case['facts'],[]),{'version':1,'episodes':[]},
            self.histories['own']['u'],'episode-0')
        native={key:None for key in SNAPSHOT_KEYS}
        native.update(integration=np.array([1.,2.]),application={'source_run_id':uuid.uuid4().hex,
            'event_prefix':{'event_count':1},'memory':state,'schema_version':3,'manual_intent':[.65,0.]})
        expected=self.runner.baseline_invariants(native)
        original=copy.deepcopy(state)
        for condition in self.runner.CONDITIONS[:-1]:
            branch=copy.deepcopy(native)
            branch['application']['memory']['u']=self.runner.condition_u(condition,self.histories)
            branch['application']['memory']=memory_task.configure_selector(branch['application']['memory'],
                self.runner.selector_config(condition,self.histories))
            self.assertEqual(self.runner.baseline_invariants(branch),expected)
        self.assertEqual(native['application']['memory'],original)
        branch=copy.deepcopy(native)
        branch['application']['memory']=memory_task.configure_selector(state,self.runner.selector_config('own',self.histories))
        for mutate in (
            lambda b:b['integration'].__setitem__(0,3.),
            lambda b:b['application']['manual_intent'].__setitem__(0,.5),
            lambda b:b['application']['memory']['m']['facts'][0]['associations'][0].__setitem__('relation','paired_cue'),
            lambda b:b['application']['memory'].__setitem__('e',self.histories['own']['e']),
            lambda b:b['application']['memory']['detector'].__setitem__('tick',1),
            lambda b:b['application']['memory'].__setitem__('cursor',{'tick':1}),
            lambda b:b['application']['memory']['requests'].append({'fact_id':'bad'}),
            lambda b:b['application']['memory'].__setitem__('active',{'fact_id':'bad'}),
            lambda b:b['application']['memory']['selector'].__setitem__('secret',True)):
            bad=copy.deepcopy(branch);mutate(bad)
            try:
                actual=self.runner.baseline_invariants(bad)
            except ValueError:
                continue
            self.assertNotEqual(actual,expected)

    def test_existing_engine_application_schema_restores_and_resets_nested_selector(self):
        from palimpsest import memory_task, memory_world
        from palimpsest.engine import Engine
        from palimpsest.records import RunWriter
        from test_engine import SmallEnv
        case=experiment.make_world_case(8,'local_cue','development-test',acquisition=True)
        def configure(env,state):
            env.data.qpos[:]=case['start_pose'];env._goal_xy[:]=case['goal_xy']
            return memory_world.validate_state(state)
        engines=[]
        with patch.object(memory_world,'configure',side_effect=configure):
            try:
                for _ in range(2):
                    run=self.root/uuid.uuid4().hex
                    engines.append(Engine(SmallEnv(),RunWriter(run/'recording',{'run_id':run.name}),
                        scenario='memory-passages',memory_case=case))
                source,destination=engines
                existing_schema=source.application_state()['schema_version']
                source.memory=memory_task.configure_selector(source.memory,self.runner.selector_config('retrieval',self.histories))
                saved=source.application_state()
                self.assertEqual(saved['schema_version'],existing_schema)  # No new top-level schema.
                self.assertEqual(destination.validate_application(saved),saved)
                bad=copy.deepcopy(saved);bad['memory']['selector']['resource_sha256']='1'*64
                with self.assertRaises(ValueError):destination.validate_application(bad)
                self.assertEqual(destination.total_tick,0)
                destination.restore_application(saved)
                self.assertEqual(destination.memory,saved['memory'])
                destination._reset_world()
                self.assertEqual(destination.memory['selector'],saved['memory']['selector'])
                self.assertEqual(destination.memory['e']['episodes'],[])
                self.assertEqual(destination.memory['version'],2)
                self.assertTrue(all(f['status']=='unknown' for f in destination.memory['m']['facts']))
            finally:
                for engine in engines:engine.close()

    def test_actual_geometry_gold_and_two_relation_blocks_drive_all_nine_fixtures(self):
        from palimpsest import memory_task, memory_world
        for block in self.runner.BLOCKS:
            with self.subTest(block=block['id']):
                case=experiment.make_world_case(block['seed'],block['regime'],'development-test',acquisition=True)
                self.assertEqual(memory.sha256(self.runner.semantic_case(case)),self.runner.SEMANTIC_CASE_SHA256[block['id']])
                histories=self.runner.block_histories(block['id'],self.histories)
                before=[xy+[.4] for xy in memory_world.POSTS+memory_world.PARKED_GATES+memory_world.PARKED_OTHERS]
                after=copy.deepcopy(before);after[3]=[0.,-1.,.4]
                def scene(token,circles,goal):
                    labels=self.runner.occupancy(case,circles)
                    return {'cues':[{'id':case['cue_id'],'xy':case['cue_xy'],'state':token}],
                        'landmarks':[{'id':case['common_goal_id'],'xy':goal}]+[
                            {'id':f['inspection_landmark_id'],'xy':xy} for f,xy in zip(case['facts'],case['inspection_xy'])],
                        'passages':[{'subject_id':f['subject_id'],'inspection_landmark_id':f['inspection_landmark_id'],
                            'passability':labels[f['subject_id']]} for f in case['facts']], 'common_goal_id':case['common_goal_id']}
                observations=[]
                for tick,pose in ((29,[-1.3,-1.1,math.pi/2]),(199,[-1.3,.626,math.pi/2])):
                    packet=memory_task.capture_symbolic(scene(0,before,case['goal_xy']),pose,before,episode_id='episode-0',tick=tick)
                    observations.extend(packet['passages'])
                state=memory_task.initialize(memory.seed_m(case['facts'],[]),{'version':1,'episodes':[]},
                    memory.artifact(method='empty-v1'),'episode-0')
                for tick in (29,199):
                    state['m']=memory.revise(state['m'],None,{'event_id':None,'target_ids':[],'reason':'no_rule'},
                        [o for o in observations if o['tick']==tick],episode_id='episode-0',tick=tick)[0]
                self.assertTrue(all(f['status']=='observed' for f in state['m']['facts']))
                packet299=memory_task.capture_symbolic(scene(0,before,case['goal_xy']),[-1.3,.626,math.pi/20],before,
                    episode_id='episode-0',tick=299)
                angle=next(x['bearing_rad'] for x in packet299['landmarks'] if x['id']==case['common_goal_id'])
                state.update(cursor={'episode_id':'episode-0','tick':299,'packet_sha256':memory.sha256(packet299),
                    'common_goal_id':case['common_goal_id'],'bearing':[math.cos(angle),math.sin(angle)]},
                    detector={'tick':299,'cues':[{'id':case['cue_id'],'state':0,
                    'observation_id':memory_task._sensor_id('episode-0',299,'cue',case['cue_id'])}]})
                state=memory_task.validate_state(state)
                source_id=uuid.uuid4().hex;source_run=self.root/source_id;source_run.mkdir()
                source_file=source_run/'transfer-worker.json';source_file.write_text('{}')
                source_native={'application':{'source_run_id':source_id,'memory':state}}
                source_data={'run':source_run,'paths':[source_file],'manifest':{'run_id':source_id},
                    'events':[{'kind':'application_restored','episode':0,'episode_step':300,'world':{
                        'arena':7.,'pose':[-1.3,.626,math.pi/20],'goal':self.runner.effective_goal()+[.25],'obstacles':before}}]}
                source_report={'snapshot_sha256':'1'*64,'before_circles':before}
                data,reports={},{}
                gold=[case['facts'][0]['id']]
                # Explicit pure sensor fixtures; these poses are not acquired traces.
                for condition in self.runner.CONDITIONS:
                    branch=copy.deepcopy(state);branch['u']=self.runner.condition_u(condition,histories)
                    config=self.runner.selector_config(condition,histories,
                        {'gold_target_ids':gold} if condition=='oracle' else None)
                    branch=memory_task.configure_selector(branch,config)
                    run_id=uuid.uuid4().hex;run=self.root/run_id;run.mkdir()
                    worker_file=run/'transfer-worker.json';worker_file.write_text('{}')
                    events=[{'kind':'application_restored','episode':0,'episode_step':300,'world':{
                        'arena':7.,'pose':[-1.3,.626,math.pi/20],'goal':self.runner.effective_goal()+[.25],'obstacles':after}}]
                    rows=[]
                    for tick,pose in ((300,[-1.3,.626,math.pi/20]),(301,[-1.3,-.6,0.])):
                        action=self.runner.cue_action(branch['cursor']['bearing'])
                        packet=memory_task.capture_symbolic(scene(1,after,self.runner.effective_goal()),pose,after,
                            episode_id='episode-0',tick=tick)
                        branch,_,audit=memory_task.advance_memory(branch,packet)
                        events.append({'kind':'memory_sensed','episode':0,'episode_step':tick,'tick':tick,'packet':packet})
                        events.extend({'kind':'memory_decision','detail':item} for item in audit)
                        rows.append({'episode':0,'tick':tick,'action':np.asarray(action,np.float64)})
                    data[condition]={'run':run,'paths':[worker_file],'manifest':{'run_id':run_id,'status':'completed'},
                        'events':events,'rows':rows}
                    reports[condition]={'after_circles':after,'final_memory':branch,'final_phase':'paused',
                        'outcome':None,'steps':302,'task_pass':False}
                with patch.object(memory,'fit',side_effect=AssertionError('Gold/evaluator cannot fit')):
                    proof=self.runner.oracle_evidence(case,source_native,source_report,data['own'],reports['own'],source_data)
                    comparison=self.runner.evaluate_case(case,source_native,source_report,data,reports,histories,source_data)
                self.assertEqual(proof['gold_target_ids'],gold)
                scored={row['condition']:row for row in comparison['targeting']}
                self.assertTrue(scored['own']['exact_set'])
                self.assertFalse(scored['swapped']['exact_set'])
                self.assertEqual(scored['hand-authored']['exact_set'],block['id']=='local-8')
                self.assertTrue(scored['retrieval']['exact_set'])
                self.assertEqual(len(comparison['runtime']),9)
                self.assertTrue(all(row['revision_pass'] and not row['task_pass'] for row in comparison['runtime']))
                timing=next(row for row in comparison['runtime'] if row['condition']=='own')['timing'][0]
                self.assertEqual((timing['first_correct_observed_tick'],timing['first_correct_committed_tick']),(301,301))
                self.assertEqual(timing['uncertainty_intervals'],[{'start_tick':300,'end_tick':301,'duration_ticks':1,'censored':False}])
                for mutate in (lambda p:p['gold_target_ids'].clear(),
                               lambda p:p['after_circles'].__setitem__(3,before[3]),
                               lambda p:p.__setitem__('pre_m_sha256','0'*64)):
                    bad=copy.deepcopy(proof);mutate(bad)
                    with self.assertRaises(ValueError):self.runner.validate_oracle_evidence(bad,state['m'],case)
                source_data['manifest'].update(transfer_block=block['id'],transfer_stage='source',
                    transfer_protocol_sha256=self.runner.PROTOCOL_SHA256,memory_case=case)
                data['own']['manifest'].update(transfer_block=block['id'],transfer_stage='own',
                    transfer_protocol_sha256=self.runner.PROTOCOL_SHA256,memory_case=case)
                source_file.write_text(json.dumps(source_report))
                (data['own']['run']/'transfer-worker.json').write_text(json.dumps(reports['own']))
                proof=self.runner.oracle_evidence(case,source_native,source_report,data['own'],reports['own'],source_data)
                job=next(j for j in self.plan()['jobs'] if j['block']==block['id'] and j['stage']=='oracle')
                job.update(oracle_evidence=proof,selector=self.runner.selector_config('oracle',histories,proof),
                           expected_non_u={'fixture':'same scientific state'})
                def donor(path):
                    return source_data if path.name==source_id else data['own']
                with patch.object(self.runner,'read_run',side_effect=donor), \
                     patch.object(self.runner,'_initial_snapshot',return_value=(source_native,{'sha256':'1'*64},[])), \
                     patch.object(self.runner,'baseline_invariants',return_value=job['expected_non_u']):
                    self.runner.check_oracle_sources(job)
                    source_file.write_text(json.dumps({**source_report,'tampered':True}))
                    with self.assertRaisesRegex(ValueError,'hash-validated actual donor'):
                        self.runner.check_oracle_sources(job)
                    source_file.write_text(json.dumps(source_report))
                    data['own']['manifest']['transfer_block']='unrelated-block'
                    with self.assertRaisesRegex(ValueError,'different case/block'):
                        self.runner.check_oracle_sources(job)
                bad_data=copy.deepcopy(data['own'])
                next(e for e in bad_data['events'] if e['kind']=='memory_decision' and e['detail']['kind']=='memory_trigger')\
                    ['detail']['trigger']['before_observation_id']='fabricated'
                with self.assertRaises(ValueError):self.runner.actual_trigger(state,bad_data,case)


class TransferPreparation(unittest.TestCase):
    def test_shared_selector_preserves_nine_conditions_and_no_event_bypass(self):
        fixture, truth = experiment.make_case(8, 'local_cue', 'development-test')
        own = experiment.make_history(0, 'local_cue')
        swapped = experiment.make_history(9, 'paired_cue')
        own_u, swapped_u = memory.fit(own), memory.fit(swapped)
        artifacts = {'own': own_u, 'swapped': swapped_u, 'sham': copy.deepcopy(own_u),
            'no-U': memory.artifact(method='empty-v1'), 'hand-authored': memory.artifact('local_cue')}
        facts = fixture['m']['facts']
        local = next(f['id'] for f in facts if f['associations'][0]['relation'] == 'local_cue')
        paired = next(f['id'] for f in facts if f['associations'][0]['relation'] == 'paired_cue')
        expected = dict(zip(experiment.CONDITIONS,
            ([local], [paired], [local], [], [local], [facts[0]['id']], [facts[0]['id']], [local], [local])))
        before = copy.deepcopy((fixture, own, artifacts))
        for condition in experiment.CONDITIONS:
            kwargs = {'u': artifacts[condition]} if condition in artifacts else (
                {'history': own} if condition == 'retrieval' else
                {'gold_target_ids': truth['gold_target_ids']} if condition == 'oracle' else {})
            with patch.object(memory, 'fit', side_effect=AssertionError('selector cannot fit')):
                selection = experiment.selection_for_condition(condition, fixture['m'], fixture['trigger'], **kwargs)
            self.assertEqual(selection['target_ids'], expected[condition])
            with patch.object(memory, 'select', side_effect=AssertionError('no-event must bypass')):
                null = experiment.selection_for_condition(condition, fixture['m'], None, **kwargs)
                self.assertEqual(null, {'event_id': None, 'target_ids': [], 'reason': 'no_rule'})
        self.assertEqual((fixture, own, artifacts), before)
        comparison = experiment.compare_conditions(fixture, own, swapped, truth)
        self.assertEqual({r['condition']: r['selection']['target_ids'] for r in comparison['results']}, expected)

    def test_selector_rejects_wrong_resources_and_dangling_gold(self):
        fixture, _ = experiment.make_case(8, 'local_cue', 'development-test')
        m, event = fixture['m'], fixture['trigger']
        for condition, kwargs in [('unknown', {}), ('own', {}), ('retrieval', {}),
                ('traversal', {'u': memory.artifact('local_cue')}),
                ('own', {'u': memory.artifact('local_cue'), 'gold_target_ids': []}),
                ('oracle', {'gold_target_ids': ['not-a-fact']}),
                ('oracle', {'gold_target_ids': [m['facts'][0]['id']] * 2})]:
            with self.subTest(condition=condition), self.assertRaises(ValueError):
                experiment.selection_for_condition(condition, m, event, **kwargs)
        with self.assertRaises(ValueError):
            experiment.selection_for_condition('no-U', m, event, u=memory.artifact(method='empty-v1'), limit=True)


if __name__ == '__main__':
    unittest.main()
