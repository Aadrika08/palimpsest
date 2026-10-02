import copy
import unittest

from palimpsest import body_adaptation as adaptation
from palimpsest.body_profile import effective_control


class SessionState(unittest.TestCase):
    def interval(self, state, gains=(12., 14.), **overrides):
        action = adaptation.probe_action(state)
        control = effective_control(action)
        before = state['previous_angles_rad']
        after = [a + u*k*.02 for a,u,k in zip(before,control,gains)]
        values = dict(nominal_action=action, actual_control=control, before=before,
                      after=after, dt_s=.02, time_s=state['time_s']+.02,
                      contact=False, coverage_passed=True, terminated=False, truncated=False)
        values.update(overrides)
        return adaptation.observe_interval(state, **values)

    def finish_trial(self, state, gains=(12., 14.)):
        for _ in range(120-state['episode_step']):
            state = self.interval(state, gains)
        return state

    def completed_fit(self):
        if hasattr(self.__class__, '_accepted_fixture'):
            return copy.deepcopy(self.__class__._accepted_fixture)
        state = adaptation.initial_session(episode=0)
        for trial in range(4):
            state = self.finish_trial(state)
            if trial != 3:
                state = adaptation.calibration_next(state, application_phase='paused')
        self.__class__._accepted_fixture = copy.deepcopy(state)
        return state

    def fitted(self):
        return adaptation.calibration_next(self.completed_fit(),application_phase='paused')

    def test_fourth_transition_starts_one_fresh_fitted_episode_and_cannot_repeat(self):
        complete=self.completed_fit()
        self.assertEqual(complete['phase'],'fit_complete')
        self.assertEqual(complete['episode_step'],120)
        with self.assertRaises(ValueError):adaptation.plan_action(complete,[.3,0.])
        fitted=adaptation.calibration_next(complete,application_phase='paused')
        self.assertEqual(fitted['phase'],'fitted')
        self.assertEqual(fitted['episode'],4)
        self.assertEqual(fitted['episode_step'],0)
        self.assertEqual(fitted['previous_angles_rad'],[0.,0.])
        self.assertEqual(fitted['time_s'],0.)
        for key in ('samples','samples_sha256','fit','fit_sha256','identity'):
            self.assertEqual(fitted[key],complete[key])
        self.assertEqual(fitted,adaptation.calibration_next(complete,application_phase='paused'))
        with self.assertRaises(ValueError):adaptation.calibration_next(fitted,application_phase='paused')
        adaptation.validate_session(fitted,episode=4,episode_step=0,angles=[0.,0.],time_s=0.)

    def test_fixed_probes_next_trial_preserves_buffer_and_requires_paused_completion(self):
        state = adaptation.initial_session(episode=3)
        original = copy.deepcopy(state)
        with self.assertRaises(ValueError):
            adaptation.calibration_next(state, application_phase='paused')
        self.assertEqual(state, original)
        self.assertEqual(adaptation.probe_action(state), [.2, 0.])
        complete = self.finish_trial(state)
        self.assertEqual(complete['phase'], 'trial_complete')
        self.assertEqual(len(complete['samples']), 100)
        self.assertEqual([s['tick'] for s in complete['samples']], list(range(20,120)))
        with self.assertRaises(ValueError):
            adaptation.calibration_next(complete, application_phase='running')
        next_state = adaptation.calibration_next(complete, application_phase='paused')
        self.assertEqual(next_state['samples'], complete['samples'])
        self.assertEqual(next_state['samples_sha256'], complete['samples_sha256'])
        self.assertEqual(next_state['episode'], 4)
        self.assertEqual(next_state['episode_step'], 0)
        self.assertEqual(next_state['previous_angles_rad'], [0.,0.])
        self.assertEqual(next_state['time_s'], 0.)
        self.assertEqual(adaptation.probe_action(next_state), [.4,0.])

    def test_contact_pipeline_wrong_controls_and_user_actions_reject_without_mutation(self):
        state = adaptation.initial_session(episode=0)
        for change in ({'contact': True}, {'coverage_passed': False}, {'terminated': True},
                       {'truncated': True}, {'nominal_action':[0.,0.]}, {'actual_control':[0.,0.]},
                       {'before':[1.,0.]}, {'dt_s':True}, {'after':[float('nan'),0.]},
                       {'time_s':.03}):
            with self.subTest(change=change):
                before = copy.deepcopy(state)
                with self.assertRaises(ValueError):self.interval(state, **change)
                self.assertEqual(state,before)

    def test_all_four_fresh_trials_fit_only_new_measurements_and_compensate(self):
        state = self.fitted()
        self.assertEqual(state['phase'],'fitted')
        self.assertEqual(state['trial_index'],3)
        self.assertEqual(len(state['samples']),400)
        self.assertIsNone(state['rejection'])
        for actual,expected in zip(state['fit']['pooled']['gains_rad_s_per_control'],(12.,14.)):
            self.assertAlmostEqual(actual,expected)
        plan=adaptation.plan_action(state,[.3,0.])
        self.assertEqual(effective_control(plan['applied_action']),plan['applied_control'])
        self.assertNotEqual(plan['applied_control'],effective_control([.3,0.]))
        before=state['previous_angles_rad']
        after=[a+u*k*.02 for a,u,k in zip(before,plan['applied_control'],(12.,14.))]
        advanced=adaptation.observe_interval(state,nominal_action=[.3,0.],actual_control=plan['applied_control'],
            before=before,after=after,dt_s=.02,time_s=state['time_s']+.02,
            contact=False,coverage_passed=True,terminated=False,truncated=False)
        self.assertEqual(advanced['phase'],'fitted')
        self.assertEqual(advanced['samples_sha256'],state['samples_sha256'])
        self.assertEqual(advanced['fit_sha256'],state['fit_sha256'])
        self.assertEqual(advanced['episode_step'],1)

        with self.assertRaises(ValueError):adaptation.probe_action(state)
        with self.assertRaises(ValueError):adaptation.calibration_next(state,application_phase='paused')

    def test_ordinary_reset_aborts_partial_and_clears_fitted_session(self):
        partial=self.interval(adaptation.initial_session(episode=0))
        for state in (partial,self.fitted()):
            reset=adaptation.ordinary_reset(state,episode=state['episode']+1)
            self.assertEqual(reset['phase'],'collecting')
            self.assertEqual(reset['trial_index'],0)
            self.assertEqual(reset['samples'],[])
            self.assertIsNone(reset['fit'])
            self.assertIsNone(reset['fit_sha256'])
            self.assertEqual(reset['episode_step'],0)
            self.assertEqual(reset['identity'],state['identity'])

    def test_bad_direction_agreement_is_retained_rejection_without_fallback(self):
        state=adaptation.initial_session(episode=0)
        for trial in range(4):
            state=self.finish_trial(state,(8.,14.) if trial==3 else (12.,14.))
            if trial<3:state=adaptation.calibration_next(state,application_phase='paused')
        self.assertEqual(state['phase'],'rejected')
        self.assertEqual(len(state['samples']),400)
        self.assertIsNone(state['fit'])
        self.assertIsNone(state['fit_sha256'])
        self.assertIn('agreement',state['rejection'])
        with self.assertRaises(ValueError):adaptation.plan_action(state,[.3,0.])
        adaptation.validate_session(state)

    def test_partial_and_fitted_snapshot_validation_binds_sample_fit_and_native_cursor(self):
        partial=adaptation.initial_session(episode=2)
        for _ in range(21):partial=self.interval(partial)
        fitted=self.fitted()
        for state in (partial,fitted):
            validated=adaptation.validate_session(state,episode=state['episode'],
                episode_step=state['episode_step'],angles=state['previous_angles_rad'],time_s=state['time_s'])
            self.assertEqual(state,validated)
            self.assertIsNot(state,validated)
            with self.assertRaises(ValueError):adaptation.validate_session(state,angles=[1.,0.],time_s=state['time_s'])
        corruptions=[]
        for key,value in [('episode_step',True),('trial_index',4),('phase','fitted'),('samples_sha256','0'*64),('extra',1)]:
            bad=copy.deepcopy(partial);bad[key]=value;corruptions.append(bad)
        bad=copy.deepcopy(fitted);bad['fit']['pooled']['gains_rad_s_per_control'][0]+=.1;corruptions.append(bad)
        bad=copy.deepcopy(fitted);bad['fit']['pooled']['version']=True;corruptions.append(bad)
        bad=copy.deepcopy(fitted);bad['samples'][0]['increments_rad'][0]+=.1;corruptions.append(bad)
        bad=copy.deepcopy(fitted);bad['samples'].append(copy.deepcopy(bad['samples'][0]));corruptions.append(bad)
        for state in corruptions:
            with self.assertRaises(ValueError):adaptation.validate_session(state)

    def test_fitted_terminal_interval_retains_cursor_and_fit_then_cannot_advance(self):
        state = self.fitted()
        # Pure cursor fixture at the bound, not a claim of 599 physics intervals.
        state.update(episode_step=599,time_s=599*.02)
        plan = adaptation.plan_action(state,[.3,0.])
        after = [u*k*.02 for u,k in zip(plan['applied_control'],(12.,14.))]
        terminal = adaptation.observe_interval(state,nominal_action=[.3,0.],actual_control=plan['applied_control'],
            before=[0.,0.],after=after,dt_s=.02,time_s=600*.02,
            contact=False,coverage_passed=True,terminated=False,truncated=True)
        self.assertEqual(terminal['phase'],'fitted_terminal')
        self.assertEqual(terminal['terminal'],{'terminated':False,'truncated':True})
        self.assertEqual(terminal['episode_step'],600)
        self.assertEqual(terminal['previous_angles_rad'],after)
        for key in ('samples','samples_sha256','fit','fit_sha256'):
            self.assertEqual(state[key],terminal[key])
        adaptation.validate_session(terminal,episode=4,episode_step=600,angles=after,time_s=12.)
        with self.assertRaises(ValueError):adaptation.plan_action(terminal,[.3,0.])
        with self.assertRaises(ValueError):adaptation.calibration_next(terminal,application_phase='paused')
        with self.assertRaises(ValueError):adaptation.observe_interval(terminal,
            nominal_action=[.3,0.],actual_control=plan['applied_control'],before=after,after=after,
            dt_s=.02,time_s=12.02,contact=False,coverage_passed=True,terminated=False,truncated=False)
        malformed = copy.deepcopy(terminal)
        malformed.update(phase='fitted',terminal=None)
        with self.assertRaises(ValueError):adaptation.validate_session(malformed)
        reset = adaptation.ordinary_reset(terminal,episode=5)
        self.assertEqual(reset['phase'],'collecting')
        self.assertEqual(reset['samples'],[])


if __name__=='__main__':unittest.main()
