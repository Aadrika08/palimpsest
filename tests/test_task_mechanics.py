"""Run with PYTHONPATH=src python tests/test_task_mechanics.py.

Synthetic mechanism checks only; no controller or physical qualification.
"""

import copy
import importlib
import importlib.util
import json
import math
import unittest


class TaskMechanicsTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec('palimpsest.task_mechanics'),
                             'bounded M6 mechanisms are missing')
        self.m = importlib.import_module('palimpsest.task_mechanics')

    def exploration(self, **changes):
        return self.m.initial_exploration(**{
            'max_landmarks': 3, 'max_visits': 3, 'max_decisions': 6, **changes})

    def packet(self, *ids):
        return {'landmarks': [{'id': i, 'bearing_rad': .2} for i in ids]}

    def odometry(self, **changes):
        return self.m.initial_odometry([0., 0.], **{
            'radius_m': .1, 'track_m': .4, 'quantum_rad': math.pi / 2,
            'max_steps': 10, 'max_travel_m': 10., **changes})

    def fit(self, samples=None, **changes):
        if samples is None:
            samples = [
                {'control': [.25, .5], 'increments_rad': [.25, 1.], 'dt_s': .5, 'contact': False},
                {'control': [.5, .25], 'increments_rad': [.5, .5], 'dt_s': .5, 'contact': False},
                {'control': [-.25, -.5], 'increments_rad': [-.25, -1.], 'dt_s': .5, 'contact': False},
            ]
        return self.m.fit_wheel_gains(samples, **{
            'max_samples': 8, 'min_samples': 3, 'min_excitation': .1,
            'gain_bounds': [1., 5.], 'control_limit': 1., 'dt_bounds_s': [.1, 1.],
            'max_rate_rad_s': 10., 'max_residual_rad_s': .01,
            'max_relative_rmse': .01, **changes})

    def test_visible_choices_are_unseen_then_least_visited_with_stable_id_ties(self):
        state = self.exploration()
        original = copy.deepcopy(state)
        first = self.m.choose_landmark(state, self.packet('b', 'a'))
        self.assertEqual(first['landmark'], {'id': 'a', 'bearing_rad': .2})
        second = self.m.choose_landmark(first['state'], self.packet('a', 'b'))
        third = self.m.choose_landmark(second['state'], self.packet('b', 'a'))
        self.assertEqual(second['landmark']['id'], 'b')
        self.assertEqual(third['landmark']['id'], 'a')
        self.assertEqual(third['state']['visits'], {'a': 2, 'b': 1})
        self.assertEqual(state, original)
        json.dumps(third, allow_nan=False)

    def test_visible_cue_absence_and_malformed_or_exhausted_state_fail(self):
        state = self.exploration(max_visits=1, max_landmarks=1)
        with self.assertRaises(self.m.CueUnavailable):
            self.m.choose_landmark(state, self.packet())
        for packet in (self.packet('a', 'a'), {'landmarks': [], 'true_pose': [0, 0]},
                       {'landmarks': [{'id': 'a', 'bearing_rad': float('nan')}]},
                       {'landmarks': [{'id': 'a', 'bearing_rad': True}]}):
            with self.subTest(packet=packet), self.assertRaises(ValueError):
                self.m.choose_landmark(state, packet)
        selected = self.m.choose_landmark(state, self.packet('a'))['state']
        for packet in (self.packet('a'), self.packet('b')):
            with self.assertRaises(ValueError):
                self.m.choose_landmark(selected, packet)
        selected['decisions'] = 0
        with self.assertRaises(ValueError):
            self.m.choose_landmark(selected, self.packet('a'))

    def test_quantization_accumulates_sub_tick_angles_and_rejects_jumps(self):
        q = self.m.quantized_encoder_increments
        self.assertEqual(q([0., 0.], [.04, -.04], quantum_rad=.1,
                           max_increment_rad=.2), [0., 0.])
        self.assertEqual(q([.04, -.04], [.06, -.06], quantum_rad=.1,
                           max_increment_rad=.2), [.1, -.1])
        self.assertEqual(q([0., 0.], [.05, -.05], quantum_rad=.1,
                           max_increment_rad=.2), [.1, -.1])
        for angles in ([100., 0.], [float('nan'), 0.], [True, 0.]):
            with self.assertRaises(ValueError):
                q([0., 0.], angles, quantum_rad=.1, max_increment_rad=.2)

    def test_known_straight_arc_and_home_bearing_from_local_estimate(self):
        initial = self.odometry(quantum_rad=.1)
        state = self.m.odometry_step(initial, [10., 10.], max_increment_rad=11.)
        self.assertAlmostEqual(state['x_m'], 1.)
        self.assertEqual(state['y_m'], 0.)
        self.assertEqual(state['yaw_rad'], 0.)
        bearing = self.m.home_bearing(state, arrival_radius_m=.01)
        self.assertAlmostEqual(abs(bearing['bearing_rad']), math.pi)
        self.assertAlmostEqual(bearing['distance_m'], 1.)
        self.assertFalse(bearing['arrived'])
        self.assertEqual(initial['x_m'], 0.)
        arc = self.m.odometry_step(self.odometry(track_m=.2), [0., math.pi],
                                   max_increment_rad=4.)
        self.assertAlmostEqual(arc['x_m'], .1)
        self.assertAlmostEqual(arc['y_m'], .1)
        self.assertAlmostEqual(arc['yaw_rad'], math.pi / 2)

    def test_square_encoder_fixture_closes_estimate_and_has_no_home_direction(self):
        state = self.odometry()
        for left, right in [(2, 2), (1, 3), (3, 5), (2, 6),
                            (4, 8), (3, 9), (5, 11), (4, 12)]:
            state = self.m.odometry_step(state, [left * math.pi, right * math.pi],
                                         max_increment_rad=7.)
        self.assertAlmostEqual(state['x_m'], 0., places=12)
        self.assertAlmostEqual(state['y_m'], 0., places=12)
        home = self.m.home_bearing(state, arrival_radius_m=1e-10)
        self.assertTrue(home['arrived'])
        self.assertIsNone(home['bearing_rad'])
        json.dumps(state, allow_nan=False)

    def test_odometry_bounds_and_false_encoder_limit_are_explicit(self):
        for calibration in ({'radius_m': 0.}, {'track_m': -1.}, {'quantum_rad': 0.}):
            with self.assertRaises(ValueError):
                self.odometry(**calibration)
        with self.assertRaises(ValueError):
            self.m.odometry_step(self.odometry(), [100., 100.], max_increment_rad=7.)
        # A plausible but false stream is indistinguishable from real wheel angles.
        state = self.m.odometry_step(self.odometry(), [math.pi, math.pi], max_increment_rad=7.)
        self.assertAlmostEqual(state['x_m'], math.pi * .1)
        with self.assertRaises(ValueError):
            self.m.odometry_step(self.odometry(max_travel_m=.01),
                                 [math.pi, math.pi], max_increment_rad=7.)
        with self.assertRaises(ValueError):
            self.m.odometry_step(self.odometry(max_steps=1) | {'steps': 1},
                                 [0., 0.], max_increment_rad=7.)
        with self.assertRaises(ValueError):
            self.m.home_bearing(state | {'true_pose': [0., 0.]}, arrival_radius_m=.01)
        # A large raw jump must fail even when coarse quantization masks it.
        with self.assertRaises(ValueError):
            self.m.odometry_step(self.odometry(quantum_rad=100.), [10., 10.],
                                 max_increment_rad=1.)
        with self.assertRaises(ValueError):
            self.m.home_bearing(state | {'encoder_counts': [0, 0]}, arrival_radius_m=.01)

    def test_encoder_baseline_and_json_roundtrip_preserve_local_origin(self):
        state = self.m.initial_odometry([10., -5.], radius_m=.1, track_m=.4,
            quantum_rad=.1, max_steps=2, max_travel_m=2.)
        self.assertEqual([state['x_m'], state['y_m'], state['yaw_rad']], [0., 0., 0.])
        restored = json.loads(json.dumps(state, allow_nan=False))
        next_state = self.m.odometry_step(restored, [11., -4.], max_increment_rad=2.)
        self.assertAlmostEqual(next_state['x_m'], .1)
        self.assertEqual(next_state['y_m'], 0.)
        self.assertEqual(next_state['yaw_rad'], 0.)

    def test_known_wheel_gains_recover_and_compensate_without_mutation(self):
        fit = self.fit()
        self.assertEqual(fit['gains_rad_s_per_control'], [2., 4.])
        self.assertEqual(fit['rmse_rad_s'], [0., 0.])
        original = copy.deepcopy(fit)
        result = self.m.compensate_wheels([.5, .5], fit,
            nominal_gains_rad_s_per_control=[1., 2.], max_compensation_ratio=2.)
        self.assertEqual(result['control'], [.25, .25])
        self.assertFalse(result['saturated'])
        self.assertEqual(fit, original)
        json.dumps(fit, allow_nan=False)

    def test_gain_fit_rejects_weak_contact_nonfinite_and_bad_protocol(self):
        sample = {'control': [.5, .5], 'increments_rad': [.5, 1.],
                  'dt_s': .5, 'contact': False}
        for change in ({'control': [.5, 0.]}, {'contact': True}, {'dt_s': 0.},
                       {'increments_rad': [float('nan'), 1.]}, {'control': [True, .5]},
                       {'true_pose': [0., 0.]}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.fit([sample | change] * 3)
        for protocol in ({'min_excitation': 100.}, {'gain_bounds': [3., 5.]},
                         {'max_samples': 2}, {'dt_bounds_s': [1., .1]}):
            with self.assertRaises(ValueError):
                self.fit(**protocol)

    def test_gain_fit_rejects_outlier_and_poor_fit_separately(self):
        samples = [{'control': [.5, .5], 'increments_rad': [v, 1.],
                    'dt_s': .5, 'contact': False} for v in [.5, .5, 1.]]
        with self.assertRaisesRegex(ValueError, 'residual'):
            self.fit(samples)
        with self.assertRaisesRegex(ValueError, 'fit'):
            self.fit(samples, max_residual_rad_s=10., max_relative_rmse=.01)

    def test_compensation_rejects_saturation_ratio_and_corrupt_fit(self):
        fit = self.fit()
        with self.assertRaises(self.m.SaturationError):
            self.m.compensate_wheels([.75, .75], fit,
                nominal_gains_rad_s_per_control=[4., 4.], max_compensation_ratio=2.)
        with self.assertRaisesRegex(ValueError, 'ratio'):
            self.m.compensate_wheels([.1, .1], fit,
                nominal_gains_rad_s_per_control=[4., 4.], max_compensation_ratio=1.5)
        with self.assertRaises(ValueError):
            self.m.compensate_wheels([.1, .1], fit | {'gains_rad_s_per_control': [0., 4.]},
                nominal_gains_rad_s_per_control=[4., 4.], max_compensation_ratio=2.)

    def test_structural_and_numeric_limits_reject_unbounded_json_inputs(self):
        for limit in (True, 0, self.m.MAX_ITEMS + 1):
            with self.assertRaises(ValueError):
                self.exploration(max_landmarks=limit)
        with self.assertRaises(ValueError):
            self.m.choose_landmark(self.exploration(), self.packet('x' * 129))
        with self.assertRaises(ValueError):
            self.odometry(radius_m=10**1000)
        with self.assertRaises(ValueError):
            self.m.quantized_encoder_increments([0., 0.], [1., 1.],
                quantum_rad=1e-300, max_increment_rad=2.)
        with self.assertRaises(ValueError):
            self.fit(max_relative_rmse=2.)


if __name__ == '__main__':
    unittest.main()
