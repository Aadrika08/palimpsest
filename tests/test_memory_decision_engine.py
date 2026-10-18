"""Headless admission/engine contracts using explicitly synthetic environments.

Native capture/restore remains a mocked boundary. No model or MuJoCo is run.
"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from palimpsest import memory, snapshots, memory_decision as decision, memory_decision_world as world
from palimpsest.engine import Engine
from palimpsest.records import RunWriter
from test_engine import SmallEnv,SmallPolicy
from test_memory_decision import config
import test_memory_decision as decision_fixtures


class DecisionEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.engines=[]
        self.addCleanup(lambda:[engine.close() for engine in self.engines])
        self.hashes=patch.object(snapshots,'controller_hashes',return_value={'graph_buffers':'1'*64,'parameters':'2'*64})
        self.hashes.start()
        self.addCleanup(self.hashes.stop)
        self.case=world.make_case(0,'local_cue','change')

    def engine(self,**restoration):
        env=SmallEnv()
        env.end_on_collision=False
        env.n_obstacles,env.obstacle_ids=20,list(range(20))
        env.model.geom_size=np.array([[.4,.8,0.]]*20)
        env.model.geom_type=np.array([5]*20)
        env.data.geom_xpos=np.array([[*xy,.8] for xy in world.PROFILE['obstacles']])
        env._obstacle_xy=np.array(world.PROFILE['obstacles'])
        policy=SmallPolicy(action=(.25,-.1))
        policy.device='cpu'
        writer=RunWriter(self.root/str(len(self.engines)),{'run_id':str(len(self.engines))})
        def configure(env,state):
            env.data.qpos[:]=self.case['start_pose']
            env._goal_xy[:]=self.case['goal_xy']
            return world.validate_state(state)
        with patch.object(world,'configure',side_effect=configure):
            engine=Engine(env,writer,'flynn',policy,seed=self.case['seed'],scenario=world.SCENARIO,memory_case=self.case,**restoration)
        self.engines.append(engine)
        return engine

    def acquired_engine(self):
        engine=self.engine()
        fixture=decision_fixtures.DecisionTests()
        fixture.setUp()
        engine.memory=fixture.acquired()
        engine.total_tick=engine.episode_step=fixture.tick
        engine.world_task_state['last_tick']=fixture.tick-1
        engine.env.data.qpos[:]=[*fixture.position,fixture.yaw]
        return engine

    def snapshot(self,engine):
        native=b'synthetic-not-native'
        result=dict.fromkeys(snapshots.SNAPSHOT_KEYS)
        import random,sys,platform,struct
        import torch
        profile={'max_steps':2100,'arena':7.,'n_obstacles':20}
        values={'_obstacle_xy':engine.env._obstacle_xy.copy(),'_goal_xy':engine.env._goal_xy.copy(),
            '_prev_xy':np.zeros(2),'_last_action':np.zeros(2),'_t':engine.episode_step,'_stall_steps':0,
            '_speed':0.,'_action_scale':1.,'visited':set(),'path_to_draw':None,'target_to_draw':None}
        identity={'mujoco':'3.3.6','numpy':np.__version__,'python':list(sys.version_info[:3]),'platform':sys.platform,
            'machine':platform.machine(),'byteorder':sys.byteorder,'pointer_bits':struct.calcsize('P')*8,
            'environment_class':'synthetic.SmallEnv','model_sha256':'a'*64,
            'environment_profile':{'values':profile,'absent':[k for k in snapshots.ENV_PROFILE if k not in profile]},
            'torch':{'threads':1,'initialized_cuda_devices':[]},
            'renderer':{'height':128,'width':128,'context_class':'synthetic.context','requested_backend':'egl','requested_egl_device':None},
            'policy':{'class':'palimpsest.flynn.FlynnPolicy','device':'cpu','dtype':'torch.float32','provenance':{'neuron_count':4}},'teacher':None}
        observation={'cam_left':np.zeros((128,128,3),np.uint8),'cam_right':np.zeros((128,128,3),np.uint8),
                     'sensors':{'collision':False,'collision_angle':None,'wind_direction':np.array([1.,0.])}}
        rng={'python':random.getstate(),'numpy':np.random.get_state(),'environment':np.random.default_rng(0).bit_generator.state,
             'environment_seed':0,'spaces':{},'torch_cpu':torch.get_rng_state().numpy().copy(),'torch_cuda':[]}
        result.update(schema_version=1,native_data=native,native_sha256=hashlib.sha256(native).hexdigest(),
            identity=identity,integration_enum=1,integration=np.zeros(1),environment={'values':values,'absent':[]},
            policy={'hidden':np.zeros((1,4),np.float32),'left':None,'right':None,'failure_diagnostics':{}},
            rng=rng,observation=observation,application=engine.application_state())
        return result

    def test_fresh_cpu_flynn_unknown_prefix_admission_and_private_profile(self):
        from palimpsest.profiles import validate,validate_decision,SCENARIOS
        self.assertNotIn(world.SCENARIO,SCENARIOS)
        with self.assertRaises(ValueError):
            validate(world.SCENARIO,'checker','flynn')
        profile=validate_decision(world.SCENARIO,'checker','flynn')
        self.assertEqual(profile['max_steps'],2100)
        self.assertEqual(validate('memory-passages','checker','flynn')['max_steps'],600)
        engine=self.engine()
        self.assertEqual(engine.memory['version'],3)
        self.assertEqual(engine.application_state()['schema_version'],8)
        self.assertTrue(all(f['status']=='unknown' for f in engine.memory['m']['facts']))
        self.assertEqual(Engine._memory_restore(self.case,world.SCENARIO,'flynn','cpu',None,False,None)[0],self.case)
        for controller,device in (('manual','cpu'),('teacher','cpu'),('flynn','cuda')):
            with self.assertRaises(ValueError):
                Engine._memory_restore(self.case,world.SCENARIO,controller,device,None,False,None)

    def test_acquired_arm_selector_invariants_and_exact_restore_revision(self):
        engine=self.acquired_engine()
        before=self.snapshot(engine)
        engine.configure_memory_selector(config('own'),memory.artifact('local_cue'))
        configured=self.snapshot(engine)
        self.assertEqual(decision.invariant_hashes(before),decision.invariant_hashes(configured))
        engine.arm_memory_decision()
        self.assertEqual(engine.world_task_state['decision_tick'],engine.episode_step+2)
        self.assertEqual(engine.world_task_state['event_tick'],engine.episode_step+1)
        with self.assertRaises(ValueError):
            engine.arm_memory_decision()
        with self.assertRaises(ValueError):
            engine.configure_memory_selector(config('no-U'),memory.artifact())
        source=self.snapshot(engine)
        with patch.object(snapshots,'restore',side_effect=lambda saved,env,**kwargs:(env._get_obs(),saved['application'])):
            branch=self.engine(restore_snapshot=source)
        self.assertEqual(branch.revision,engine.revision)
        self.assertEqual(branch.memory,engine.memory)
        self.assertEqual(branch.world_task_state,engine.world_task_state)
        self.assertEqual(decision.invariant_hashes(source),decision.invariant_hashes(self.snapshot(branch)))

    def test_bad_task_world_case_or_manual_source_rejected_before_writer_allocation(self):
        engine=self.acquired_engine()
        source=self.snapshot(engine)
        defects=[('memory','supervisor','waypoint_deadline_tick'),('memory','graph','profile_sha256'),
                 ('world_task_state','profile_sha256'),('world_task_state','case','seed')]
        bad_sources=[]
        for path in defects:
            bad=copy.deepcopy(source)
            target=bad['application']
            for field in path[:-1]:
                target=target[field]
            target[path[-1]]='broken'
            bad_sources.append(bad)
        bad=copy.deepcopy(source)
        bad['application']['controller']='manual'
        bad_sources.append(bad)
        for bad in bad_sources:
            with patch('palimpsest.records.RunWriter') as writer,self.assertRaises((ValueError,TypeError)):
                Engine.open(self.root,self.root,self.root/'not-created',controller='flynn',device='cpu',seed=0,
                    scenario=world.SCENARIO,memory_case=self.case,restore_snapshot=bad)
            writer.assert_not_called()

    def test_live_packet_bridge_retains_camera_contact_access_and_rejects_action_override(self):
        engine=self.engine()
        engine._step()
        self.assertEqual(engine.total_tick,1)
        self.assertEqual(set(engine.policy.seen),{'cam_left','cam_right','sensors'})
        self.assertEqual(set(engine.policy.seen['sensors']),{'collision','collision_angle','wind_direction'})
        self.assertFalse(engine.policy.seen['sensors']['collision'])
        with self.assertRaises(ValueError):
            engine._step([0.,0.])
        self.assertEqual(engine.total_tick,1)

    def test_selector_substitutions_keep_arm_schedule_proof_identical(self):
        own=self.acquired_engine()
        no_u=self.acquired_engine()
        own.configure_memory_selector(config('own'),memory.artifact('local_cue'))
        no_u.configure_memory_selector(config('no-U'),memory.artifact())
        own.arm_memory_decision()
        no_u.arm_memory_decision()
        self.assertEqual(own.world_task_state,no_u.world_task_state)
        self.assertEqual(decision.invariant_hashes(self.snapshot(own)),decision.invariant_hashes(self.snapshot(no_u)))

    def test_incomplete_rng_policy_observation_or_oversize_rejected_before_allocation(self):
        source=self.snapshot(self.acquired_engine())
        for field in ('identity','integration','environment','policy','rng','observation'):
            bad=copy.deepcopy(source)
            bad[field]=None
            with patch('palimpsest.records.RunWriter') as writer,self.assertRaises((ValueError,TypeError)):
                Engine.open(self.root,self.root,self.root/'never-created',controller='flynn',device='cpu',seed=0,
                    scenario=world.SCENARIO,memory_case=self.case,restore_snapshot=bad)
            writer.assert_not_called()
        bad=copy.deepcopy(source)
        bad['native_data']=b'x'*(16*1024**2+1)
        bad['native_sha256']=hashlib.sha256(bad['native_data']).hexdigest()
        with patch('palimpsest.records.RunWriter') as writer,self.assertRaises(ValueError):
            Engine.open(self.root,self.root,self.root/'never-created',controller='flynn',device='cpu',seed=0,
                scenario=world.SCENARIO,memory_case=self.case,restore_snapshot=bad)
        writer.assert_not_called()

    def test_float64_policy_snapshot_refused_by_frozen_float32_profile(self):
        source=self.snapshot(self.acquired_engine())
        source['identity']['policy']['dtype']='torch.float64'
        source['policy']['hidden']=source['policy']['hidden'].astype(np.float64)
        with self.assertRaises(ValueError):
            snapshots.validate_decision_snapshot(source)

    def test_maximum_admitted_command_bank_fits_container_guard(self):
        source=self.snapshot(self.acquired_engine())
        app=source['application']
        for index in range(Engine.MAX_IDS):
            identifier=f'fixture-pause-{index}'
            app['original_commands'][identifier]={'id':identifier,'kind':'pause','expected_state':'paused',
                'expected_episode':0,'expected_revision':0,'payload':{}}
            app['receipts'][identifier]={'id':identifier,'kind':'pause','status':'applied',
                'received_run_id':app['source_run_id'],'received_episode':0,'received_tick':0,
                'applied_run_id':app['source_run_id'],'applied_episode':0,'applied_tick':0,'applied_revision':0}
        self.assertLess(snapshots.validate_decision_snapshot(source),snapshots.DECISION_MAX_BYTES)
        self.assertEqual(Engine._memory_restore(self.case,world.SCENARIO,'flynn','cpu',source,False,None)[0],self.case)

    def test_direct_restore_cannot_replace_manual_controller_for_v2(self):
        engine=self.engine()
        source=self.snapshot(self.acquired_engine())
        source['application']['controller']='manual'
        with patch.object(snapshots,'restore') as restored,self.assertRaises(ValueError):
            engine.restore_branch(source,replace_controller=True)
        self.assertFalse(restored.called)
