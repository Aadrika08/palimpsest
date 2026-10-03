"""Pure/deterministic owner contracts, not native physics qualification."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from palimpsest import body_homing as homing, body_adaptation as adaptive, task_profiles as task
from palimpsest.engine import Engine
from palimpsest.profiles import validate
from palimpsest.records import RunWriter
from test_body_adaptation_engine import AdaptiveFixtureEnv, configure
import test_body_adaptation as session_fixtures


class Composition(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.engines=[];self.addCleanup(lambda:[x.close() for x in self.engines])

    def engine(self, fitted=False):
        env=AdaptiveFixtureEnv()
        with patch.object(adaptive,'configure',side_effect=configure):
            engine=Engine(env,RunWriter(Path(self.tmp.name)/str(len(self.engines)),{}),scenario=homing.SCENARIO,seed=1)
        self.engines.append(engine)
        if fitted:
            engine.body_state=session_fixtures.SessionState().fitted();engine.episode=4;engine.total_tick=480
            engine.task_state=homing.initial_task(engine.body_state)
        return engine

    def command(self, engine, kind, payload=None, override=None):
        message={'id':str(len(engine.receipts)), 'kind':kind,'payload':payload or {},
                 'expected_state':engine.phase,'expected_episode':engine.episode,'expected_revision':engine.revision}
        engine.submit(message)
        with patch.object(adaptive,'configure',side_effect=configure),patch.dict('sys.modules',mujoco=engine.env.mj):
            engine.advance(action_override=override)
        return engine.submit(message)

    def test_restrictions_and_reset_activation_only_after_fitted_boundary(self):
        self.assertEqual(validate(homing.SCENARIO,'checker','manual')['seed'],1)
        with self.assertRaises(ValueError):validate(homing.SCENARIO,'checker','teacher')
        engine=self.engine()
        self.assertIsNone(engine.task_state)
        self.assertEqual(self.command(engine,'set_action',{'action':[.4,0.]})['status'],'rejected')
        fitted=self.engine(True)
        self.assertEqual(fitted.task_state['phase'],'outbound')
        self.assertEqual(fitted.task_state['odometry']['x_m'],0.)
        self.assertEqual(self.command(fitted,'reset')['status'],'applied')
        self.assertIsNone(fitted.task_state);self.assertEqual(fitted.body_state['samples'],[])
        self.assertIsNone(fitted.composition['derivation']);self.assertIsNone(fitted.composition['encoder_packet'])
        self.assertEqual(self.command(fitted,'step')['status'],'applied')
        self.assertEqual(fitted.episode_step,1);self.assertIsNone(fitted.task_state)

    def test_post_hold_nominal_and_once_only_action_replay(self):
        source=self.engine(True); destination=self.engine(True)
        with patch('palimpsest.body_profile.plan_action',side_effect=AssertionError('legacy loaded prevalidation')):
            self.command(source,'set_action',{'action':[.4,0.]})
        self.command(source,'step')
        action=source.last_transition['action'].copy()
        self.command(destination,'set_action',{'action':[.4,0.]})
        self.command(destination,'step',override=action)
        self.assertNotEqual(action.tolist(),[.4,0.])
        np.testing.assert_array_equal(source.last_transition['control'],destination.last_transition['control'])
        self.assertEqual(source.body_state,destination.body_state)
        held=self.engine(True);self.command(held,'set_action',{'action':[.4,0.]})
        real=task.advance
        def hold(state,packet):
            state,bearing,_,events=real(state,packet)
            return state,[0.,0.],True,events
        with patch.object(task,'advance',side_effect=hold):self.command(held,'step')
        np.testing.assert_array_equal(held.last_transition['body_nominal_action'],[0.,0.])
        np.testing.assert_array_equal(held.last_transition['control'],[0.,0.])
        self.assertEqual(held.phase,'paused')

    def test_composed_native_admission_rejects_before_any_destination_change(self):
        source=self.engine(True);destination=self.engine()
        state=source.application_state()
        self.assertEqual(state['schema_version'],7)
        self.assertEqual(destination.validate_application(state),state)
        homing.validate_snapshot_application(state,source.env,source.env.model,source.env.data)
        before=destination.env.data.qpos.copy()
        for mutate in (lambda s:s['composition']['identity'].update(profile_sha256='f'*64),
                       lambda s:s['task_state']['odometry']['wheel_angles_rad'].__setitem__(0,.1),
                       lambda s:s['body_state']['previous_angles_rad'].__setitem__(0,.1)):
            bad=copy.deepcopy(state);mutate(bad)
            with self.assertRaises(ValueError):destination.validate_application(bad)
            np.testing.assert_array_equal(destination.env.data.qpos,before)
        self.command(source,'step')
        state=source.application_state()
        homing.validate_snapshot_application(state,source.env,source.env.model,source.env.data)
        for tick in (True, 0.):
            bad=copy.deepcopy(state);bad['composition']['encoder_packet']['tick']=tick
            with self.assertRaises(ValueError):homing.validate_components(bad)
        state['composition']['encoder_packet']['angles_rad'][0]+=.1
        with self.assertRaises(ValueError):homing.validate_components(state)

    def test_explicit_derivation_and_distinct_actual_world_metadata(self):
        # The actual ignored assets are deliberately not a fixture dependency.
        source=self.engine(True);session=source.body_state
        app=source.application_state();app.update(schema_version=6,scenario=adaptive.SCENARIO,task_state=None)
        app.pop('composition')
        snp={'application':app,'identity':{'model_sha256':adaptive.IDENTITY['model_sha256'],'body_profile':adaptive.IDENTITY}}
        report={'status':'passed','snapshots':{'fitted':{'sha256':homing.REFERENCE['snapshot_sha256']}},
                'accepted_fit':{'fit':session['fit']}}
        with patch.dict(homing.REFERENCE,{'session_sha256':adaptive._sha(session),
                    'fit_sha256':session['fit_sha256'],'samples_sha256':session['samples_sha256'],
                    'decoded_snapshot_sha256':homing.state_digest(snp)}):
            derived=homing.derive_snapshot(snp,snapshot_sha256=homing.REFERENCE['snapshot_sha256'],
                    report=report,report_sha256=homing.REFERENCE['report_sha256'])
            for key in ('native_data', 'environment'):
                forged=copy.deepcopy(snp);forged[key]='altered'
                with self.assertRaisesRegex(ValueError,'decoded state pin'):
                    homing.derive_snapshot(forged,snapshot_sha256=homing.REFERENCE['snapshot_sha256'],
                        report=report,report_sha256=homing.REFERENCE['report_sha256'])
            self.assertEqual(snp['application'],app)
            self.assertEqual(derived['application']['body_state'],session)
            self.assertEqual(derived['application']['task_state'],homing.initial_task(session))
            changed=copy.deepcopy(derived);changed['application']['source_run_id']='new'
            self.assertEqual(homing.normalized_reference(derived),homing.normalized_reference(changed))
            changed['application']['body_state']['previous_angles_rad'][0]=.1
            self.assertNotEqual(homing.normalized_reference(derived),homing.normalized_reference(changed))
            with self.assertRaises(ValueError):homing.derive_snapshot(snp,snapshot_sha256='f'*64,
                    report=report,report_sha256=homing.REFERENCE['report_sha256'])
        self.assertEqual(homing.PROTOCOL['encoder_component_protocol_sha256'],task.PROTOCOL_SHA256)
        self.assertEqual(homing.PROTOCOL['component_role'],'encoder-component-only; memory-world configuration not invoked')
        details=homing.provenance(source.env,source.world())
        self.assertEqual(details['actual_body_world'],source.world())
        self.assertIn('parent_authoring_profile',details)

if __name__=='__main__':unittest.main()
