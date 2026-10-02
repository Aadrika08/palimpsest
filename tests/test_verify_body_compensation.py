"""Pure inverse/paired-metric checks; no physics, owner or model launch."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location('verify_body_compensation', SCRIPTS / 'verify_body_compensation.py')
verify = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verify)


class CompensationChecks(unittest.TestCase):
    def test_inverse_matches_pinned_upstream_without_normalization(self):
        import numpy as np
        upstream = SCRIPTS.parent / 'upstream/fly-gym/environment/mujoco_two_cam_env_random_obstacles.py'
        function = next(node for node in ast.parse(upstream.read_text()).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'vel_angle_to_action')
        namespace = {'np': np}
        exec(compile(ast.Module(body=[function], type_ignores=[]), str(upstream), 'exec'), namespace)
        for controls in ([.753, .621], [-.753, -.621], [-2., 2.], [2., 2.], [0., 0.]):
            inverse = verify.inverse_control(controls)
            actual = namespace['vel_angle_to_action'](*inverse['action']) * 2
            self.assertEqual(actual.tolist(), inverse['control_float32'])
        for bad in ([2.00001, 0.], [float('nan'), 0.], [0.], ['x', 0.]):
            with self.assertRaises(ValueError):
                verify.inverse_control(bad)

    def trials(self):
        result = {}
        for trial in verify.TRIALS:
            sign = 1 if trial['action'][0] > 0 else -1
            error = {'baseline': 0., 'uncompensated': 2., 'compensated': .5}[trial['condition']]
            rows = []
            for tick in range(120):
                yaw = sign * error * tick * .001
                y = sign * error * tick * .002
                rows.append({'tick': tick, 'fit_interval': tick >= 20,
                             'dt_s': .02, 'increments_rad': [sign * (8 - error) * .02, sign * 8 * .02],
                             'before': {'pose': [0., y, yaw]},
                             'after': {'pose': [0., y + sign * error * .002, yaw + sign * error * .001]},
                             'contact': False, 'coverage_passed': True})
            result[trial['id']] = {'status': 'passed', 'trial': trial, 'rows': rows}
        return result

    def test_each_direction_and_metric_must_improve(self):
        trials = self.trials()
        result = verify.compare_trials(trials)
        self.assertTrue(result['accepted'])
        bad = copy.deepcopy(trials)
        identifier = next(t['id'] for t in verify.TRIALS if t['condition'] == 'compensated' and t['action'][0] < 0)
        for row in bad[identifier]['rows']:
            row['increments_rad'][0] *= .01
        rejected = verify.compare_trials(bad)
        self.assertFalse(rejected['accepted'])
        self.assertTrue(rejected['directions']['forward']['accepted'])
        self.assertFalse(rejected['directions']['reverse']['improved']['wheel_rate_rmse'])
        missing = self.trials(); missing[identifier]['rows'].pop()
        self.assertFalse(verify.compare_trials(missing)['accepted'])
        malformed = self.trials(); malformed[identifier]['rows'][30]['increments_rad'].pop()
        self.assertFalse(verify.compare_trials(malformed)['accepted'])

    def test_extracted_kernel_preserves_old_straight_metrics_and_exact_guards(self):
        import math
        result = verify.compare_trials(self.trials())
        self.assertTrue(result['accepted'])
        for direction in ('forward', 'reverse'):
            metrics = result['directions'][direction]['comparisons']
            self.assertAlmostEqual(metrics['uncompensated']['wheel_rate_rmse'], math.sqrt(2))
            self.assertAlmostEqual(metrics['compensated']['wheel_rate_rmse'], .5/math.sqrt(2))
            self.assertAlmostEqual(metrics['uncompensated']['yaw_error'], .2)
            self.assertAlmostEqual(metrics['compensated']['lateral_error'], .1)
        for key, value in [('contact', True), ('coverage_passed', False), ('fit_interval', False), ('dt_s', 0.)]:
            bad = self.trials(); bad['baseline-forward']['rows'][30][key] = value
            self.assertFalse(verify.compare_trials(bad)['accepted'])
        bad = self.trials(); bad['baseline-forward']['trial'] = {**bad['baseline-forward']['trial'], 'action': [0., .2]}
        self.assertFalse(verify.compare_trials(bad)['accepted'])
        bad = self.trials(); bad['baseline-forward']['rows'][30]['increments_rad'] = [3., 0.]
        self.assertFalse(verify.compare_trials(bad)['accepted'])

    def test_artifact_hash_and_saturation_reject_before_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.json'; path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                verify.load_fits(path)
        fit = {'version': 1, 'gains_rad_s_per_control': verify.PERTURBED_GAINS,
               'excitation': [160., 160.], 'rmse_rad_s': [.4358, .3676],
               'relative_rmse': [.0581, .0405], 'sample_count': 400,
               'gain_bounds': [1., 100.], 'control_limit': 2.}
        trial = next(t for t in verify.TRIALS if t['condition'] == 'compensated')
        plan = verify.command_plan(trial, {'perturbed': fit, 'identity': {'sha256': verify.GAIN_REPORT_SHA256}})
        self.assertFalse(plan['compensation']['saturated'])
        self.assertNotEqual(plan['applied_action'], plan['nominal_action'])
        self.assertEqual(verify.effective_control(plan['applied_action']), plan['applied_control_float32'])
        saturated = {**trial, 'action': [1., 0.]}
        with self.assertRaisesRegex(ValueError, 'saturation'):
            verify.command_plan(saturated, {'perturbed': fit, 'identity': {'sha256': verify.GAIN_REPORT_SHA256}})

    def test_old_diagnostic_keeps_seed_bounds_and_failed_result_through_shared_collector(self):
        from palimpsest.engine import Engine
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            config = {'repo': str(SCRIPTS.parent), 'assets': str(stage / 'assets'),
                      'stage': str(stage), 'run': str(stage / 'run'), 'trial': verify.gains.TRIALS[0]}
            with patch.dict(sys.modules, {'mujoco': SimpleNamespace(get_mjcb_control=lambda: None)}), \
                    patch.object(Engine, 'open', side_effect=RuntimeError('fixture preflight stop')) as opened:
                self.assertFalse(verify.gains.worker(config))
            kwargs = opened.call_args.kwargs
            self.assertEqual(kwargs['seed'], 0)
            self.assertEqual(kwargs['max_bytes'], 64 * 1024**2)
            self.assertEqual(kwargs['controller'], 'manual')
            self.assertNotIn('storage_budget', kwargs)
            data = json.loads((stage / 'result.json').read_text())
            self.assertEqual(data['error']['message'], 'fixture preflight stop')
            self.assertEqual(data['rows'], [])
            self.assertNotIn('command_plan', data)

    def test_preflight_failure_keeps_all_six_planned_trials_without_spawn(self):
        from palimpsest.storage import StorageBudget, StorageLimits
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            args = SimpleNamespace(gains_report=output / 'missing.json')
            # Exercise the report body only; no global writer lease or child is taken.
            budget = StorageBudget((output,), StorageLimits(min_free_bytes=0))
            with patch('palimpsest.evaluate.bounded_process') as spawn:
                report = verify.verify_locked(args, SCRIPTS.parent, output, budget)
            spawn.assert_not_called()
            self.assertEqual(report['status'], 'failed')
            self.assertEqual(len(report['trials']), 6)
            self.assertTrue(all(item['result']['status'] == 'not_started' for item in report['trials'].values()))
            self.assertEqual(json.loads((output / 'report.json').read_text())['trials'], report['trials'])


if __name__ == '__main__':
    unittest.main()
