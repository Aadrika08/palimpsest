"""Pure diagnostic fitting check; no simulator, ML or native owner launch."""
import copy
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('verify_body_calibration', Path(__file__).resolve().parents[1] / 'scripts/verify_body_calibration.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class CalibrationChecks(unittest.TestCase):
    def test_accepts_supported_consistent_fits_and_rejects_bad_residuals_agreement_and_direction(self):
        trials = {}
        for trial in verify.TRIALS:
            turn = trial['kind'] == 'turn'
            direction = 1 if not turn or trial['action'][1] > 0 else -1
            rows = []
            for tick in range(120):
                x = direction * (.02 + tick * .0001)
                rows.append({'tick': tick, 'shaft_delta_rad': [-x / 2, x / 2] if turn else [x, x],
                             'body_forward_m': 0. if turn else .06 * x,
                             'body_yaw_change_rad': x / 6 if turn else 0.})
            trials[trial['id']] = {'status': 'passed', 'trial': trial, 'rows': rows}
        result = verify.fit_trials(trials)
        self.assertTrue(result['accepted'])
        self.assertAlmostEqual(result['accepted_coefficients']['translation_m_per_mean_shaft_rad'], .06)
        self.assertAlmostEqual(result['accepted_coefficients']['yaw_rad_per_differential_shaft_rad'], 1 / 6)
        first_turn = next(trial['id'] for trial in verify.TRIALS if trial['kind'] == 'turn')
        residuals = copy.deepcopy(trials)
        for row in residuals[first_turn]['rows'][20:]:
            row['body_yaw_change_rad'] *= .1 if row['tick'] % 2 else 1.9
        result = verify.fit_trials(residuals)
        self.assertFalse(result['accepted']); self.assertIsNone(result['accepted_coefficients'])
        self.assertGreater(result['per_trial'][first_turn]['relative_rms'], .2)
        inconsistent = copy.deepcopy(trials)
        for row in inconsistent[first_turn]['rows']:
            row['body_yaw_change_rad'] *= 1.5
        result = verify.fit_trials(inconsistent)
        self.assertFalse(result['accepted']); self.assertIsNone(result['accepted_coefficients'])
        self.assertGreater(result['groups']['turn']['coefficient_range_over_mean'], .2)
        reversed_direction = copy.deepcopy(trials)
        for row in reversed_direction[first_turn]['rows']:
            row['body_yaw_change_rad'] *= -1
        result = verify.fit_trials(reversed_direction)
        self.assertFalse(result['accepted']); self.assertFalse(result['per_trial'][first_turn]['direction_supported'])
        missing = copy.deepcopy(trials); missing[first_turn]['rows'].pop()
        self.assertFalse(verify.fit_trials(missing)['accepted'])
        self.assertFalse(verify.fit_pairs([(0., 0.)] * 100, 'turn', 1)['accepted'])


if __name__ == '__main__':
    unittest.main()
