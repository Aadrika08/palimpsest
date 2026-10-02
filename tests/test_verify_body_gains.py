"""Pure fit and callback-boundary checks; no physics or owner launch."""
import copy
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import unittest

SPEC = importlib.util.spec_from_file_location('verify_body_gains', Path(__file__).resolve().parents[1] / 'scripts/verify_body_gains.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class GainChecks(unittest.TestCase):
    def trials(self):
        trials = {}
        for trial in verify.TRIALS:
            u = trial['action'][0] * 2
            gains = [12 * trial['left_gear_factor'], 12.]
            rows = [{'tick': tick, 'control': [u, u], 'dt_s': .02,
                     'increments_rad': [u * gain * .02 for gain in gains],
                     'contact': False, 'coverage_passed': True} for tick in range(120)]
            trials[trial['id']] = {'trial': trial, 'status': 'passed', 'rows': rows}
        return trials

    def test_fit_exact_coverage_and_rejection(self):
        trials = self.trials()
        result = verify.fit_trials(trials)
        self.assertTrue(result['accepted'])
        self.assertAlmostEqual(result['conditions']['left-08']['pooled']['gains_rad_s_per_control'][0], 9.6)
        for field, value in [('contact', True), ('coverage_passed', False)]:
            broken = copy.deepcopy(trials)
            broken[verify.TRIALS[0]['id']]['rows'][0][field] = value
            self.assertFalse(verify.fit_trials(broken)['accepted'])
        broken = copy.deepcopy(trials)
        broken[verify.TRIALS[0]['id']]['rows'][30]['increments_rad'][0] *= -1
        self.assertFalse(verify.fit_trials(broken)['accepted'])
        trials.pop(verify.TRIALS[0]['id'])
        self.assertFalse(verify.fit_trials(trials)['accepted'])

    def probe(self, existing=None):
        names = ['floor', 'left_wheel_geom', 'right_wheel_geom', 'caster_wheel_geom', 'obstacle',
                 'base_geom', 'caster_fork', 'cam_left_marker', 'cam_right_marker']
        bodies = ['world', 'base', 'left_wheel', 'right_wheel', 'front_caster_mount', 'caster_wheel', 'obstacle_body']
        mj = SimpleNamespace(__version__='3.3.6', callback=existing,
            mjtObj=SimpleNamespace(mjOBJ_GEOM=5, mjOBJ_BODY=1),
            mjtIntegrator=SimpleNamespace(mjINT_EULER=0),
            mjtDisableBit=SimpleNamespace(mjDSBL_CONTACT=16, mjDSBL_ACTUATION=2048),
            mj_id2name=lambda model, kind, index: (names if kind == 5 else bodies)[index],
            mj_name2id=lambda model, kind, name: (names if kind == 5 else bodies).index(name))
        mj.get_mjcb_control = lambda: mj.callback
        mj.set_mjcb_control = lambda value: setattr(mj, 'callback', value)
        model = SimpleNamespace(_address=10, ngeom=len(names), nbody=len(bodies),
            body_parentid=[0, 0, 1, 1, 1, 4, 0], geom_bodyid=[0, 2, 3, 5, 6, 1, 4, 1, 1],
            opt=SimpleNamespace(integrator=0, timestep=.002, disableflags=0))
        data = SimpleNamespace(_address=20, time=0., ctrl=[.4, .4], ncon=1,
            contact=[SimpleNamespace(geom1=0, geom2=1, dist=-.001)])
        env = SimpleNamespace(model=model, data=data, frame_skip=10)
        return mj, env

    def test_callback_coverage_end_cache_and_cleanup(self):
        mj, env = self.probe()
        probe = verify.ContactProbe(mj, env)
        probe.install(); probe.begin(0)
        for i in range(10):
            env.data.time = i * .002
            mj.callback(env.model, env.data)
        env.data.time = .02
        interval = probe.end()
        self.assertTrue(interval['coverage_passed'])
        self.assertFalse(interval['contact'])
        self.assertEqual(len(interval['stages']), 10)
        self.assertAlmostEqual(interval['end']['contact_cache_time_s'], .018)
        probe.close(); self.assertIsNone(mj.callback)

    def test_existing_callback_preserved_missing_stage_and_other_contact_rejected(self):
        existing = lambda m, d: None
        mj, env = self.probe(existing)
        with self.assertRaisesRegex(ValueError, 'existing'):
            verify.ContactProbe(mj, env).install()
        self.assertIs(mj.callback, existing)
        mj, env = self.probe()
        probe = verify.ContactProbe(mj, env); probe.install(); probe.begin(0)
        env.data.contact[0].geom1 = 1
        env.data.contact[0].geom2 = 4
        mj.callback(env.model, env.data)
        env.data.time = .02
        interval = probe.end()
        self.assertTrue(interval['contact']); self.assertFalse(interval['coverage_passed'])
        probe.close(); self.assertIsNone(mj.callback)

    def test_pipeline_and_pointer_mismatch_rejected(self):
        mj, env = self.probe()
        env.model.opt.integrator = 1
        with self.assertRaisesRegex(ValueError, 'Pinned Euler'):
            verify.ContactProbe(mj, env)
        env.model.opt.integrator = 0
        probe = verify.ContactProbe(mj, env); probe.install(); probe.begin(0)
        other = SimpleNamespace(_address=99)
        mj.callback(other, env.data)
        env.data.time = .02
        self.assertFalse(probe.end()['coverage_passed'])
        self.assertIn('unexpected model', probe.violations[0])
        probe.close()

    def test_manual_action_uses_float64_and_nonfinite_contacts_reject(self):
        import numpy as np
        trial = verify.TRIALS[0]
        self.assertTrue(verify.fixed_action_matches(np.asarray(trial['action'], np.float64).tolist(), trial))
        self.assertFalse(verify.fixed_action_matches(np.asarray(trial['action'], np.float32).tolist(), trial))
        mj, env = self.probe()
        probe = verify.ContactProbe(mj, env); probe.install(); probe.begin(0)
        env.data.contact[0].dist = float('nan')
        mj.callback(env.model, env.data)
        interval = probe.end()
        self.assertFalse(interval['coverage_passed'])
        self.assertEqual(len(interval['stages']), 1)
        self.assertIn('Nonfinite', probe.violations[0])
        probe.close(); self.assertIsNone(mj.callback)

    def test_world_only_retained_and_all_robot_descendants_guarded(self):
        mj, env = self.probe()
        probe = verify.ContactProbe(mj, env)
        env.data.contact[0].geom2 = 4  # Named obstacle is outside base subtree.
        pairs = probe._pairs(env.model, env.data)
        self.assertEqual(pairs[0]['classification'], 'world_only')
        self.assertFalse(pairs[0]['rejects_fit'])
        self.assertFalse(pairs[0]['allowed_ground_support'])
        robot_ids = {item['geom_id'] for item in probe.ownership['geometries'] if item['owner'] == 'robot'}
        self.assertEqual(robot_ids, {1, 2, 3, 5, 6, 7, 8})
        for robot in robot_ids:
            env.data.contact[0].geom1 = robot
            env.data.contact[0].geom2 = 4
            pair = probe._pairs(env.model, env.data)[0]
            self.assertEqual(pair['classification'], 'unexpected_robot_contact')
            self.assertTrue(pair['rejects_fit'])
        env.data.contact[0].geom1, env.data.contact[0].geom2 = 1, 2
        self.assertTrue(probe._pairs(env.model, env.data)[0]['rejects_fit'])

    def test_robot_detachment_cannot_turn_into_world_only_exclusion(self):
        mj, env = self.probe()
        env.model.body_parentid[5] = 0
        with self.assertRaisesRegex(ValueError, 'robot'):
            verify.ContactProbe(mj, env)


if __name__ == '__main__':
    unittest.main()
