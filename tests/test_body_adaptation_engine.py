"""Deterministic Engine/contact fixtures; these are not simulator evidence."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np

from palimpsest import body_adaptation as adaptation, body_profile as loaded
from palimpsest.engine import Engine
from palimpsest.records import RunWriter, iter_ticks
from palimpsest.profiles import validate
from test_body_profile import BodyFixtureEnv, fixture_configure
import test_body_adaptation as session_fixtures


class AdaptiveFixtureEnv(BodyFixtureEnv):
    def __init__(self, truncate_at=None):
        super().__init__()
        self.truncate_at = truncate_at

    def step(self, action):
        before = self.data.qpos[3:].copy()
        result = super().step(action)
        self.data.qpos[3:] = before + self.data.ctrl*np.array([12.,14.])*.02
        obs,reward,terminated,_,info = result
        return obs,reward,terminated,self.calls==self.truncate_at,info


def configure(env, *, episode, session=None):
    fixture_configure(env,f'episode-{episode}')
    env._body_profile_identity = copy.deepcopy(adaptation.IDENTITY)
    state = adaptation.initial_session(episode=episode) if session is None else adaptation.validate_session(session,episode=episode,episode_step=0)
    adaptation.validate_native(state,env.model,env.data,env)
    return state


class EngineContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.engines = []
        self.addCleanup(lambda:[engine.close() for engine in self.engines])

    def engine(self, **kwargs):
        env=kwargs.pop('env',AdaptiveFixtureEnv())
        with patch.object(adaptation,'configure',side_effect=configure):
            engine=Engine(env,RunWriter(Path(self.temp.name)/str(len(self.engines)),{}),
                          scenario=adaptation.SCENARIO,seed=1,**kwargs)
        self.engines.append(engine)
        return engine

    def command(self,engine,kind,payload=None,*,identifier=None,override=None,**expected):
        value={'id':identifier or str(len(engine.receipts)),'kind':kind,
               'expected_state':expected.get('phase',engine.phase),
               'expected_episode':expected.get('episode',engine.episode),
               'expected_revision':expected.get('revision',engine.revision), 'payload':payload or {}}
        engine.submit(value)
        with patch.object(adaptation,'configure',side_effect=configure),patch.dict('sys.modules',mujoco=engine.env.mj):
            engine.advance(action_override=override)
        return value,engine.submit(value)

    def fitted_engine(self, *, truncate_at=None):
        engine=self.engine(env=AdaptiveFixtureEnv(truncate_at=truncate_at))
        engine.body_state=session_fixtures.SessionState().fitted()
        engine.episode=4;engine.total_tick=480
        return engine

    def test_profile_and_conditional_schema_native_prevalidation(self):
        profile=validate(adaptation.SCENARIO,'checker','manual')
        self.assertEqual(profile['devices'],['cpu'])
        with self.assertRaises(ValueError):Engine.open(Path(self.temp.name),Path(self.temp.name),Path(self.temp.name)/'unused',
            scenario=adaptation.SCENARIO,seed=1,device='cuda')
        with self.assertRaises(ValueError):Engine.open(Path(self.temp.name),Path(self.temp.name),Path(self.temp.name)/'unused',
            scenario=adaptation.SCENARIO,seed=0)
        with self.assertRaises(ValueError):validate(adaptation.SCENARIO,'checker','teacher')
        source,destination=self.engine(),self.engine()
        application=source.application_state()
        self.assertEqual(application['schema_version'],6)
        self.assertEqual(destination.validate_application(application),application)
        adaptation.validate_snapshot_application(application,source.env,source.env.model,source.env.data)
        native_before=destination.env.data.qpos.copy()
        malformed=copy.deepcopy(application);malformed['body_state']['previous_angles_rad'][0]=.1
        with self.assertRaises(ValueError):destination.validate_application(malformed)
        np.testing.assert_array_equal(destination.env.data.qpos,native_before)
        with self.assertRaises(ValueError):adaptation.validate_snapshot_application(malformed,source.env,source.env.model,source.env.data)
        self.assertNotIn('samples',source.public_state()['body'])
        self.assertEqual(source.public_state()['body']['sample_count'],0)

    def test_probe_rejects_manual_and_world_commands_then_pauses_at_exact_completion(self):
        engine=self.engine()
        for kind,payload in [('set_action',{'action':[.2,0.]}),('intervene',{'kind':'move_goal','xy':[1.,1.]}),('calibration-next',{})]:
            _,receipt=self.command(engine,kind,payload)
            self.assertEqual(receipt['status'],'rejected')
        self.assertEqual(engine.env.calls,0)
        _,receipt=self.command(engine,'run')
        self.assertEqual(receipt['status'],'applied')
        with patch.dict('sys.modules',mujoco=engine.env.mj):
            for _ in range(119):engine.advance()
        self.assertEqual(engine.episode_step,120)
        self.assertEqual(engine.phase,'paused')
        self.assertEqual(engine.body_state['phase'],'trial_complete')
        self.assertEqual(len(engine.body_state['samples']),100)
        self.assertIsNone(engine.env.mj.callback)
        before=engine.env.calls
        _,receipt=self.command(engine,'step')
        self.assertEqual(receipt['status'],'rejected')
        self.assertEqual(engine.env.calls,before)
        with self.assertRaises(ValueError):engine.preview({'kind':'move_goal','xy':[1.,1.]})
        state=copy.deepcopy(engine.body_state)
        _,receipt=self.command(engine,'calibration-next',revision=engine.revision-1)
        self.assertEqual(receipt['status'],'rejected')
        self.assertEqual(engine.body_state,state)
        engine.env.data.qpos[3]+=.1
        _,receipt=self.command(engine,'calibration-next')
        self.assertEqual(receipt['status'],'rejected')
        self.assertEqual(engine.env.calls,before)
        self.assertEqual(engine.body_state,state)
        engine.env.data.qpos[3]=state['previous_angles_rad'][0]
        value,receipt=self.command(engine,'calibration-next',identifier='next')
        self.assertEqual(receipt['status'],'applied')
        self.assertEqual(engine.body_state['samples'],state['samples'])
        self.assertEqual(engine.body_state['trial_index'],1)
        self.assertEqual(engine.episode_step,0)
        self.assertEqual(engine.env.calls,0)
        self.assertEqual(engine.submit(value),receipt)
        self.assertEqual(engine.episode,1)
        _,receipt=self.command(engine,'reset')
        self.assertEqual(receipt['status'],'applied')
        self.assertEqual(engine.body_state['samples'],[])
        self.assertEqual(engine.body_state['trial_index'],0)

    def test_final_next_preserves_new_fit_and_reset_clears_it(self):
        engine=self.engine()
        engine.body_state=session_fixtures.SessionState().completed_fit()
        engine.episode=3;engine.total_tick=480;engine.episode_step=120
        engine.env.data.time=engine.body_state['time_s']
        engine.env.data.qpos[3:]=engine.body_state['previous_angles_rad']
        fit_digest=engine.body_state['fit_sha256']
        value,receipt=self.command(engine,'calibration-next')
        self.assertEqual(receipt['status'],'applied')
        self.assertEqual(engine.episode,4)
        self.assertEqual(engine.body_state['phase'],'fitted')
        self.assertEqual(engine.body_state['fit_sha256'],fit_digest)
        self.assertEqual(engine.body_state['previous_angles_rad'],[0.,0.])
        self.assertEqual(engine.env.data.time,0.)
        self.assertEqual(engine.submit(value),receipt)
        _,receipt=self.command(engine,'calibration-next')
        self.assertEqual(receipt['status'],'rejected')
        self.command(engine,'reset')
        self.assertEqual(engine.body_state['samples'],[])
        self.assertIsNone(engine.body_state['fit'])

    def test_fitted_actions_applied_once_and_final_valid_tick_recorded(self):
        source,actions=self.fitted_engine(truncate_at=2),self.fitted_engine(truncate_at=2)
        for engine in (source,actions):
            self.command(engine,'set_action',{'action':[.3,0.]})
        plan=adaptation.plan_action(source.body_state,[.3,0.])
        for _ in range(2):
            self.command(source,'step')
            self.command(actions,'step',override=plan['applied_action'])
            self.assertEqual(source.body_state,actions.body_state)
            for field in loaded.TICK_FIELDS|{'action','control'}:
                np.testing.assert_array_equal(source.last_transition[field],actions.last_transition[field])
        self.assertEqual(source.phase,'truncated')
        self.assertEqual(source.body_state['phase'],'fitted_terminal')
        self.assertEqual(source.body_state['episode_step'],2)
        self.assertEqual(source.total_tick,482)
        source.writer.flush()
        self.assertEqual(len(list(iter_ticks(source.writer.path))),2)
        self.assertIsNone(source.env.mj.callback)
        self.command(source,'reset')
        self.assertEqual(source.body_state['phase'],'collecting')
        self.assertEqual(source.body_state['samples'],[])

    def test_early_probe_outcome_keeps_failed_raw_interval_and_callback_cleanup(self):
        engine=self.engine(env=AdaptiveFixtureEnv(truncate_at=1))
        self.command(engine,'step')
        self.assertEqual(engine.phase,'failed')
        self.assertEqual(engine.total_tick,0)
        self.assertEqual(engine.body_state['episode_step'],0)
        self.assertEqual(engine.env.data.time,.02)
        events=[__import__('json').loads(line) for line in (engine.writer.path/'events.jsonl').read_text().splitlines()]
        failure=next(event for event in events if event['kind']=='body_failed')
        self.assertEqual(failure['detail']['outcome'],{'terminated':False,'truncated':True})
        self.assertEqual(failure['detail']['interval']['callback_count'],10)
        self.assertEqual(failure['detail']['encoder_after'],engine.env.data.qpos[3:].tolist())
        self.assertIsNone(engine.env.mj.callback)


if __name__=='__main__':unittest.main()
