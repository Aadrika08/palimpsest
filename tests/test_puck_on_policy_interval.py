"""Synthetic interval seam checks; no native/model execution evidence."""
import copy
import unittest
from unittest.mock import patch

import numpy as np

from palimpsest import puck_on_policy as adapter, puck_learning as learning
from palimpsest import puck_profile as puck, puck_model, puck_teacher as teacher
from palimpsest import puck_student as student
from palimpsest.snapshots import state_digest


class IntervalTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(adapter, 'stage_interval', None)), 'interval adapter is missing')
        self.assertTrue(callable(getattr(adapter, 'admit_completed_interval', None)), 'completion admission is missing')
        self.own = learning.initial_cursor()
        self.sensors = np.array([.55/14, 0, 1.55/14, 0, 0, 0, 0, 0], np.float32)
        self.world = {'time_s': 0., 'rover_pose': [-.55, 0., 0.],
                      'puck_xyz': [0., 0., .062], 'puck_velocity_xy': [0., 0.],
                      'goal_xy': [1., 0.]}
        self.capture = {'native_state': b'native fixture', 'observation': self.sensors.copy(),
                        'python_rng': [1], 'numpy_rng': np.array([2], np.uint32),
                        'torch_rng': b'synthetic torch rng', 'environment_rng': [3],
                        'space_rng': {'action': [4], 'observation': [5]}}
        self.prediction = np.array([.125, -.25], np.float64)

    def stage(self, **kwargs):
        with patch.object(puck_model, 'predict', return_value=self.prediction) as predict:
            result = adapter.stage_interval(self.sensors, self.world, 'approach', self.own,
                                            object(), terminal_reason=None,
                                            capture_query_state=lambda: self.capture, **kwargs)
        self.assertEqual(predict.call_count, 1)
        return result

    def receipt(self, staged, tick=1):
        return {'version': 1, 'kind': 'puck-on-policy-row-publication-v1',
                'protocol_sha256': adapter.PROTOCOL_SHA256, 'status': 'published',
                'completed_tick': tick, 'row_sha256': state_digest(staged['row']),
                'staged_sha256': state_digest(staged)}

    def test_exact_retained_bytes_one_teacher_then_student_and_no_live_cursor_change(self):
        before = copy.deepcopy(self.own)
        order = []
        original = teacher.decide
        def query(*args):
            order.append('teacher')
            return original(*args)
        def predict(model, inputs):
            order.append('student')
            self.assertEqual(inputs.tobytes(), learning.prepare(self.sensors, before)['inputs'].tobytes())
            return self.prediction
        with patch.object(teacher, 'decide', side_effect=query), patch.object(puck_model, 'predict', side_effect=predict):
            staged = adapter.stage_interval(self.sensors, self.world, 'approach', self.own, object(),
                                            terminal_reason=None, capture_query_state=lambda: self.capture)
        self.assertEqual(order, ['teacher', 'student'])
        self.assertEqual(self.own, before)
        row = staged['row']
        self.assertEqual(row['inputs'].dtype, np.float32)
        self.assertEqual(row['inputs'].tobytes(), self.sensors.tobytes())
        self.assertEqual(row['student_inputs'].dtype, np.float32)
        self.assertEqual(row['student_inputs'][-1], 0.)
        for name in ('teacher_action', 'predicted_action', 'action'):
            self.assertEqual(row[name].dtype, np.float64)
        self.assertEqual(row['action'].tobytes(), self.prediction.tobytes())
        self.assertNotEqual(row['teacher_action'].tobytes(), row['action'].tobytes())
        self.assertEqual(staged['query_before_sha256'], staged['query_after_sha256'])
        self.sensors[:] = 0
        self.prediction[:] = 0
        self.assertNotEqual(row['inputs'].tobytes(), self.sensors.tobytes())
        self.assertNotEqual(row['action'].tobytes(), self.prediction.tobytes())

    def test_each_query_state_component_and_effective_inputs_are_isolated(self):
        original = teacher.decide
        for key in self.capture:
            with self.subTest(key=key):
                def query(*args):
                    result = original(*args)
                    self.capture[key] = 'changed'
                    return result
                old = copy.deepcopy(self.capture)
                with patch.object(teacher, 'decide', side_effect=query), patch.object(puck_model, 'predict') as predict:
                    with self.assertRaises(ValueError):
                        adapter.stage_interval(self.sensors, self.world, 'approach', self.own, object(),
                                               terminal_reason=None, capture_query_state=lambda: self.capture)
                predict.assert_not_called()
                self.capture = old
        for target in ('sensors', 'own', 'features', 'world'):
            with self.subTest(target=target):
                def query(sensors, world, mode, own):
                    result = original(sensors, world, mode, own)
                    if target == 'sensors': self.sensors[0] = 0
                    elif target == 'own': own['tick'] = 5
                    elif target == 'features': result[2]['inputs'][0] = 0
                    else: world['time_s'] = 1.
                    return result
                with patch.object(teacher, 'decide', side_effect=query), patch.object(puck_model, 'predict') as predict:
                    with self.assertRaises(ValueError):
                        adapter.stage_interval(self.sensors, self.world, 'approach', self.own, object(),
                                               terminal_reason=None, capture_query_state=lambda: self.capture)
                predict.assert_not_called()
                self.setUp()

    def test_query_mode_inference_action_and_terminal_fail_without_admission(self):
        for reason in ('goal', 'failure', False):
            with patch.object(teacher, 'decide') as query:
                with self.assertRaises(ValueError):
                    adapter.stage_interval(self.sensors, self.world, 'approach', self.own, object(),
                                           terminal_reason=reason, capture_query_state=lambda: self.capture)
                query.assert_not_called()
        with self.assertRaises(ValueError):
            adapter.stage_interval(self.sensors, self.world, 'push', self.own, object(),
                                   terminal_reason=None, capture_query_state=lambda: self.capture)
        for boundary, error in ((teacher, 'decide'), (puck_model, 'predict')):
            with patch.object(boundary, error, side_effect=RuntimeError('fixture failure')):
                with self.assertRaises(RuntimeError):
                    adapter.stage_interval(self.sensors, self.world, 'approach', self.own, object(),
                                           terminal_reason=None, capture_query_state=lambda: self.capture)
            self.assertEqual(self.own, learning.initial_cursor())
        for action in (np.zeros(2, np.float32), np.array([np.nan, 0.]), np.array([.41, 0.])):
            self.prediction = action
            with self.assertRaises(ValueError): self.stage()
        for bad in ({}, self.capture | {'extra': 0}, self.capture | {'torch_rng': object()}):
            with self.assertRaises(ValueError):
                adapter.stage_interval(self.sensors, self.world, 'approach', self.own, object(),
                                       terminal_reason=None, capture_query_state=lambda: bad)

    def test_completion_requires_exact_successful_v3_receipt_and_contiguous_tick(self):
        staged = self.stage()
        receipt = self.receipt(staged)
        own, mode = adapter.admit_completed_interval(staged, self.own, 'approach',
                                                    completed_tick=1, publication_receipt=receipt)
        self.assertEqual(own['tick'], 1)
        self.assertEqual((own['mode'], mode), ('push', 'push'))
        self.assertEqual(self.own, learning.initial_cursor())
        for tick in (0, 2, True, 1.):
            with self.assertRaises(ValueError):
                adapter.admit_completed_interval(staged, self.own, 'approach',
                                                 completed_tick=tick, publication_receipt=receipt)
        for change in ({'version': True}, {'status': 'pending'}, {'completed_tick': True},
                       {'kind': 'puck-student-v1'}, {'protocol_sha256': '0'*64},
                       {'row_sha256': '0'*64}, {'staged_sha256': '0'*64}, {'extra': 0}):
            with self.assertRaises(ValueError):
                adapter.admit_completed_interval(staged, self.own, 'approach',
                                                 completed_tick=1, publication_receipt=receipt | change)
        for changed in ('teacher_action', 'student_inputs', 'action', 'teacher_mode_after'):
            bad = copy.deepcopy(staged)
            bad['row'][changed] = np.zeros(3)
            with self.assertRaises(ValueError):
                adapter.admit_completed_interval(bad, self.own, 'approach',
                                                 completed_tick=1, publication_receipt=receipt)

    def test_all_valid_intervals_remain_even_outside_motivating_condition(self):
        self.sensors[0] = 1./14
        self.world['rover_pose'][0] = -1.
        self.sensors[6] = 0
        staged = self.stage()
        own, mode = adapter.admit_completed_interval(staged, self.own, 'approach',
                                                    completed_tick=1, publication_receipt=self.receipt(staged))
        self.assertEqual((own['tick'], mode), (1, 'approach'))

    def test_inference_cannot_change_live_packet_world_or_cursor(self):
        for target in ('sensors', 'world', 'own'):
            self.setUp()
            with self.subTest(target=target):
                def predict(model, inputs):
                    if target == 'sensors': self.sensors[0] = 0
                    elif target == 'world': self.world['time_s'] = 1.
                    else: self.own['tick'] = 7
                    return self.prediction
                with patch.object(puck_model, 'predict', side_effect=predict):
                    with self.assertRaises(ValueError):
                        adapter.stage_interval(self.sensors, self.world, 'approach', self.own, object(),
                                               terminal_reason=None, capture_query_state=lambda: self.capture)

    def test_synthetic_owner_executes_only_student_then_publishes_before_cursor_admission(self):
        staged = self.stage()
        execution = []
        execution.append(staged['row']['action'].copy())  # Synthetic completed step only.
        self.assertEqual(execution[0].tobytes(), self.prediction.tobytes())
        self.assertEqual(self.own, learning.initial_cursor())
        with self.assertRaises(ValueError):
            adapter.admit_completed_interval(staged, self.own, 'approach',
                                             completed_tick=1, publication_receipt=None)
        self.assertEqual(self.own, learning.initial_cursor())
        own, mode = adapter.admit_completed_interval(staged, self.own, 'approach',
                                                    completed_tick=1, publication_receipt=self.receipt(staged))
        self.assertEqual((own['tick'], mode), (1, 'push'))
        with self.assertRaises(ValueError):
            adapter.admit_completed_interval(staged, own, mode,
                                             completed_tick=1, publication_receipt=self.receipt(staged))

    def test_budget_terminal_and_self_consistent_row_forgery_fail(self):
        for tick in (600,):
            self.own = self.own | {'tick': tick}
            with patch.object(teacher, 'decide') as query:
                with self.assertRaises(ValueError): self.stage()
                query.assert_not_called()
        self.setUp()
        staged = self.stage()
        for field, value in (('action', np.zeros(2, np.float64)),
                             ('teacher_mode_after', np.uint8(1)),
                             ('student_inputs', np.zeros(9, np.float32)),
                             ('tick', True)):
            bad = copy.deepcopy(staged)
            bad['row'][field] = value
            with self.assertRaises(ValueError):
                adapter.admit_completed_interval(bad, self.own, 'approach',
                                                 completed_tick=1, publication_receipt=self.receipt(bad))

    def test_historical_teacher_reader_rejects_v3_student_action_rows(self):
        row = self.stage()['row']
        self.assertNotEqual(row['action'].tobytes(), row['teacher_action'].tobytes())
        with self.assertRaises(ValueError):
            learning.admit_teacher_rows([row], 1)

    def test_historical_student_replay_rejects_v3_rows_without_inference(self):
        row = self.stage()['row']
        with patch.object(puck_model, 'predict', side_effect=AssertionError('No replay prediction')):
            with self.assertRaises(ValueError):
                student.decide(self.sensors, self.own, None, recorded=row)


if __name__ == '__main__':
    unittest.main()
