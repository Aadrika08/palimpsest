"""Pure checks for the actual-task verifier; no simulation/model launch."""
import importlib.util
import math
import tempfile
from pathlib import Path
import unittest

import numpy as np

SPEC = importlib.util.spec_from_file_location('verify_tasks', Path(__file__).resolve().parents[1] / 'scripts/verify_tasks.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class DriverChecks(unittest.TestCase):
    def test_initial_neutral_forward_and_turn_are_bounded(self):
        self.assertEqual(verify.cue_action(None), [0., 0.])
        self.assertEqual(verify.cue_action([0., 0.]), [0., 0.])
        self.assertEqual(verify.cue_action([1., 0.]), [.5, 0.])
        self.assertEqual(verify.cue_action([-1., 0.]), [0., math.pi])
        self.assertEqual(verify.cue_action([0., -1.]), [0., -math.pi / 2])
        for a in np.linspace(-math.pi, math.pi, 41):
            velocity, heading = verify.cue_action([math.cos(a), math.sin(a)])
            self.assertTrue(0. <= velocity <= .5)
            self.assertTrue(abs(heading) <= math.pi)

    def test_only_previous_effective_bearing_is_selected(self):
        transition = {'sensors': np.array([1., 7., 0., 1.], dtype=np.float32),
                      'pose': [100., -10., math.pi], 'goal': [900., 900.]}
        bearing = verify.previous_bearing(transition)
        transition['sensors'][2:] = [1., 0.]
        self.assertEqual(bearing, [0., 1.])
        self.assertEqual(verify.cue_action(bearing), [0., math.pi / 2])
        self.assertIsNone(verify.previous_bearing(None))

    def test_invalid_bearing_is_rejected_without_substitution(self):
        for value in ([float('nan'), 0.], [float('inf'), 0.], [1.], [2., 0.], [[1., 0.]], ['x', 'y']):
            with self.subTest(value=value), self.assertRaises(ValueError):
                verify.cue_action(value)
        with self.assertRaises(ValueError):
            verify.previous_bearing({'sensors': [1., 0., 1.]})

    def test_completion_requires_actual_task_reason_and_state(self):
        result = {'phase': 'terminated', 'last_outcome': {'reason': 'task_completed'},
                  'task': {'phase': 'complete'}}
        self.assertTrue(verify.task_completed(result))
        for change in ({'phase': 'truncated'}, {'last_outcome': {'reason': 'time_limit'}},
                       {'task': {'phase': 'home'}}, {'last_outcome': None}):
            self.assertFalse(verify.task_completed({**result, **change}))

    def test_motion_evaluator_does_not_hide_reverse_motion_or_dwell_drift(self):
        row = {'effective_action': [.5, 0.], 'measured_step_shaft_delta_rad': [.1, .1],
               'true_step_forward_m': -.02, 'estimate_error_m': .03, 'dwell_ticks': 1,
               'true_step_displacement_m': .02, 'true_step_yaw_change_rad': -.04}
        result = verify.evaluate_motion([row], {'radius_m': .06, 'track_m': .36, 'quantum_rad': .001})
        self.assertFalse(result['positive_shaft_and_forward_direction_observed'])
        self.assertEqual(result['measured_straight_body_forward_m'], -.02)
        self.assertEqual(result['max_dwell_true_displacement_m'], .02)
        self.assertEqual(result['max_dwell_true_yaw_change_rad'], .04)

    def test_real_engine_command_helper_applies_action_and_one_step(self):
        from test_engine import SmallEnv
        from palimpsest.engine import Engine
        from palimpsest.records import RunWriter
        with tempfile.TemporaryDirectory() as temp:
            env = SmallEnv()
            writer = RunWriter(Path(temp) / 'recording', {'run_id': 'command-helper'})
            engine = Engine(env, writer, controller='manual')
            try:
                verify.command(engine, 'manual-action', 'set_action', {'action': [.4, .2]})
                self.assertEqual(env.calls, 0)
                self.assertEqual(engine.total_tick, 0)
                verify.command(engine, 'one-step', 'step')
                self.assertEqual(env.calls, 1)
                self.assertEqual(engine.total_tick, 1)
                np.testing.assert_array_equal(env.data.ctrl, [.4, .2])
                engine.advance()
                self.assertEqual(env.calls, 1)
            finally:
                engine.close()
            self.assertTrue(env.closed)

    def test_continuation_uses_existing_exact_image_and_float_profile(self):
        tick = {'episode': 0, 'tick': 8, 'cam_left': np.zeros((1, 1, 3), np.uint8),
                'sensors': np.array([0., 0., 1., 0.], np.float32), 'latency': np.array(1.)}
        altered = {**tick, 'latency': np.array(99.), 'sensors': tick['sensors'] + 1e-7}
        verify.compare_tick(tick, altered, {'dwell_ticks': 1, 'x_m': .1}, {'dwell_ticks': 1, 'x_m': .1 + 1e-7})
        image = tick['cam_left'].copy();image[0, 0, 0] = 1
        with self.assertRaises(Exception):
            verify.compare_tick(tick, {**tick, 'cam_left': image}, {}, {})
        with self.assertRaises(Exception):
            verify.compare_tick(tick, tick, {'dwell_ticks': 1}, {'dwell_ticks': 2})


if __name__ == '__main__':
    unittest.main()
