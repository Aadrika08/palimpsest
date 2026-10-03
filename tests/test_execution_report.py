import importlib.util
from pathlib import Path
import unittest

import numpy as np

spec = importlib.util.spec_from_file_location('execution_report',
    Path(__file__).resolve().parents[1] / 'scripts/verify_execution.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ContinuationEvidenceTests(unittest.TestCase):
    def test_camera_and_integer_identity_stays_exact_and_float_tolerance_is_fixed(self):
        errors, divergences = {}, []
        module.compare_array(np.array([0.], dtype='f4'), np.array([1e-7], dtype='f4'),
                             'action', 9, errors, divergences)
        self.assertEqual(divergences, [])
        module.compare_array(np.array([137], dtype='u1'), np.array([138], dtype='u1'),
                             'cam_right', 10, errors, divergences)
        module.compare_array(np.array([0.], dtype='f4'), np.array([2e-5], dtype='f4'),
                             'final_hidden', None, errors, divergences)
        self.assertEqual([row['component'] for row in divergences], ['cam_right', 'final_hidden'])
        self.assertEqual(divergences[0]['tick'], 10)
        self.assertEqual(divergences[0]['max_abs_error'], 1.)
        self.assertGreater(errors['final_hidden'], 1e-6)
        with self.assertRaisesRegex(ValueError, 'type/shape'):
            module.compare_array(np.zeros(2), np.zeros(3), 'pose', 10, errors, divergences)
