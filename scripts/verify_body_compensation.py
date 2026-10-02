"""Fixed-artifact development compensation comparison; no online calibration."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

import verify_body_gains as gains

GAIN_REPORT_SHA256 = '9d2cd4729d32f84b490db3a6726764111989fcc80be74c7a2ba44a97cb419331'
BASELINE_GAINS = [14.878897911022118, 14.878897948225164]
PERTURBED_GAINS = [11.851776561760323, 14.374415787256368]
TRIALS = [{'id': f'{condition}-{direction}', 'condition': condition,
           'left_gear_factor': factor, 'action': [sign * .3, 0.]}
          for condition, factor in (('baseline', 1.), ('uncompensated', .8), ('compensated', .8))
          for direction, sign in (('forward', 1), ('reverse', -1))]
PROTOCOL = {**gains.PROTOCOL, 'version': 1, 'claim': 'standalone development fixed-artifact compensation comparison',
            'trials': TRIALS, 'seed': 1, 'gain_report_sha256': GAIN_REPORT_SHA256,
            'nominal_gains_rad_s_per_control': BASELINE_GAINS, 'measured_gains_rad_s_per_control': PERTURBED_GAINS,
            'max_compensation_ratio': 1.5, 'control_limit': 2.,
            'result_max_bytes': 64 * 1024**2, 'report_max_bytes': 1024**2,
            'output_max_bytes': 1024**3, 'min_free_bytes': 1024**3,
            'log_max_bytes': 1024**2, 'storage_headroom_bytes': 4 * 1024**2,
            'driver_input': 'fixed nominal action and pinned fitted gains only; no online sensor/pose feedback',
            'fit': 'no new fitting or coefficient updates; pinned v2 accepted pooled wheel gains',
            'inverse': 'ctrlL=2v-heading, ctrlR=2v+heading; explicit float32 target rounding and exact upstream roundtrip',
            'metrics': {'wheel_rate_rmse': 'sqrt(mean squared same-tick rate difference from same-direction baseline over 100x2 values)',
                        'yaw_error': 'absolute difference from baseline of cumulative wrapped yaw increments over ticks20..119',
                        'lateral_error': 'absolute difference from baseline of world-y displacement over ticks20..119; authored heading0'},
            'acceptance': 'strict improvement over uncompensated for all three errors separately in both directions',
            'rejection': 'artifact/control-roundtrip mismatch, contact/pipeline/support/rate/storage failure or any non-improving paired metric',
            'threshold_scope': 'development paired comparisons only; no physical safety or generalization claim'}
PROTOCOL_SHA256 = hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def harness_hashes():
    return {**gains.harness_hashes(), 'verify_body_compensation.py': gains.digest(__file__)}


def load_fits(path):
    path = Path(path)
    if path.stat().st_size > 1024**2:
        raise ValueError('Pinned gain report exceeds bounded size')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != GAIN_REPORT_SHA256:
        raise ValueError('Pinned gain report SHA256 mismatch')
    report = json.loads(raw)
    if (report['status'] != 'passed' or report['source_unchanged'] is not True or
            report['fit']['accepted'] is not True or report['protocol']['version'] != 2 or
            report['fit']['accepted_gains'] != {'baseline': BASELINE_GAINS, 'left-08': PERTURBED_GAINS}):
        raise ValueError('Accepted exact v2 gain artifact required')
    return {'baseline': report['fit']['conditions']['baseline']['pooled'],
            'perturbed': report['fit']['conditions']['left-08']['pooled'],
            'identity': {'sha256': GAIN_REPORT_SHA256, 'path': str(path.resolve()),
                         'source_commit': report['runtime_source']['commit'],
                         'protocol_sha256': report['protocol_sha256']}}


from palimpsest.body_profile import effective_control, inverse_control

def command_plan(trial, fits):
    from palimpsest.task_mechanics import compensate_wheels
    nominal = effective_control(trial['action'])
    compensation = None
    if trial['condition'] == 'compensated':
        compensation = compensate_wheels(nominal, fits['perturbed'],
            nominal_gains_rad_s_per_control=BASELINE_GAINS, max_compensation_ratio=1.5)
    proposed = nominal if compensation is None else compensation['control']
    inverse = inverse_control(proposed)
    applied = trial['action'] if compensation is None else inverse['action']
    if effective_control(applied) != inverse['control_float32']:
        raise ValueError('Fixed plan control roundtrip mismatch')
    return {'nominal_action': trial['action'], 'nominal_control': nominal, 'applied_action': applied,
            'proposed_control_float64': proposed, 'applied_control_float32': inverse['control_float32'],
            'float32_rounding_delta': inverse['rounding_delta'], 'compensation': compensation,
            'gain_artifact': fits['identity']}


def settled_response(fit, identifier):
    """Existing fixed 100-interval evaluator kernel; caller retains trial guards."""
    if len(fit) != 100:
        raise ValueError(identifier + ': 100 measured intervals required')
    if any(type(row['increments_rad']) is not list or len(row['increments_rad']) != 2 for row in fit):
        raise ValueError(identifier + ': two measured shaft increments required')
    rates = [[value / row['dt_s'] for value in row['increments_rad']] for row in fit]
    yaw = math.fsum(math.remainder(row['after']['pose'][2] - row['before']['pose'][2], math.tau) for row in fit)
    lateral = fit[-1]['after']['pose'][1] - fit[0]['before']['pose'][1]
    if any(not math.isfinite(value) for row in rates for value in row) or not math.isfinite(yaw) or not math.isfinite(lateral):
        raise ValueError(identifier + ': nonfinite evaluator input')
    if any(abs(value) > gains.FIT_BOUNDS['max_rate_rad_s'] for row in rates for value in row):
        raise ValueError(identifier + ': measured rate exceeds frozen bound')
    return {'rates': rates, 'yaw_rad': yaw, 'lateral_m': lateral}


def paired_response(baseline, actual):
    """Unchanged aligned 100x2 wheel, wrapped-yaw and lane-Y differences."""
    wheel_error = math.sqrt(math.fsum((a - b)**2 for row_a, row_b in zip(actual['rates'], baseline['rates'])
                                      for a, b in zip(row_a, row_b)) / 200)
    return {'wheel_rate_rmse': wheel_error,
            'yaw_error': abs(actual['yaw_rad'] - baseline['yaw_rad']),
            'lateral_error': abs(actual['lateral_m'] - baseline['lateral_m']),
            'raw_yaw_rad': actual['yaw_rad'], 'raw_lateral_m': actual['lateral_m']}


def compare_trials(trials):
    result = {'accepted': False, 'directions': {}}
    try:
        expected = {trial['id']: trial for trial in TRIALS}
        if set(trials) != set(expected):
            raise ValueError('Exact six-trial coverage required')
        prepared = {}
        for identifier, trial in expected.items():
            data = trials[identifier]; rows = data.get('rows', [])
            if (data.get('status') != 'passed' or data.get('trial') != trial or
                    [row.get('tick') for row in rows] != list(range(120)) or
                    any(row.get('contact') is not False or row.get('coverage_passed') is not True for row in rows)):
                raise ValueError(identifier + ': rejected/incomplete trial')
            fit = rows[20:]
            if any(row['fit_interval'] is not (row['tick'] >= 20) or
                   not gains.FIT_BOUNDS['dt_bounds_s'][0] <= row['dt_s'] <= gains.FIT_BOUNDS['dt_bounds_s'][1] for row in rows):
                raise ValueError(identifier + ': interval/settling protocol mismatch')
            prepared[identifier] = settled_response(fit, identifier)
        for direction in ('forward', 'reverse'):
            baseline = prepared['baseline-' + direction]; comparisons = {}
            for condition in ('uncompensated', 'compensated'):
                actual = prepared[condition + '-' + direction]
                comparisons[condition] = paired_response(baseline, actual)
            improved = {metric: comparisons['compensated'][metric] < comparisons['uncompensated'][metric]
                        for metric in ('wheel_rate_rmse', 'yaw_error', 'lateral_error')}
            result['directions'][direction] = {'accepted': all(improved.values()), 'improved': improved,
                'baseline': {'raw_yaw_rad': baseline['yaw_rad'], 'raw_lateral_m': baseline['lateral_m']},
                'comparisons': comparisons}
        result['accepted'] = all(item['accepted'] for item in result['directions'].values())
    except (ValueError, KeyError, TypeError, ZeroDivisionError) as error:
        result['reason'] = str(error)[:512]
    return result


def worker(config):
    from palimpsest.storage import StorageBudget, StorageLimits
    fits = load_fits(config['gains_report'])
    plan = command_plan(config['trial'], fits)
    body = config['storage']
    budget = StorageBudget(tuple(Path(p) for p in body['roots']), StorageLimits(**body['limits']),
                           headroom_bytes=body['headroom_bytes'])
    return gains.collect_trial(config, PROTOCOL, PROTOCOL_SHA256, command_plan=plan, harness=harness_hashes(),
                               storage_budget=budget, result_max_bytes=PROTOCOL['result_max_bytes'])


def verify(args):
    from palimpsest.storage import StorageBudget, StorageLimits
    root, output = args.repo.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    if args.assets.resolve().is_relative_to(output) or output.is_relative_to(args.assets.resolve()):
        raise ValueError('Assets must be outside the managed output root')
    budget = StorageBudget((output,), StorageLimits(max_bytes=PROTOCOL['output_max_bytes'],
        min_free_bytes=PROTOCOL['min_free_bytes'], max_runs=6, max_snapshots=1, max_exports=1),
        headroom_bytes=PROTOCOL['storage_headroom_bytes'])
    with budget.lock():
        return verify_locked(args, root, output, budget)


def verify_locked(args, root, output, budget):
    from palimpsest.evaluate import bounded_process
    from verify_endurance import source_identity
    from palimpsest.storage import StorageBudget
    from dataclasses import asdict
    storage = {'roots': [str(output)], 'limits': asdict(budget.limits), 'headroom_bytes': budget.headroom_bytes}
    planned = {trial['id']: {'result': {'status': 'not_started', 'trial': trial}, 'supervision': None,
                            'result_path': str(output / trial['id'] / 'result.json'), 'result_sha256': None}
               for trial in TRIALS}
    report = {'status': 'running', 'protocol': PROTOCOL, 'protocol_sha256': PROTOCOL_SHA256,
              'runtime_source': source_identity(root), 'harness_sha256': harness_hashes(), 'trials': planned,
              'storage': storage}
    started = time.monotonic()
    environment = {**os.environ, 'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '2', 'MPLBACKEND': 'Agg'}
    try:
        gains.write_json(output / 'protocol.json', report, max_bytes=PROTOCOL['report_max_bytes'], storage_budget=budget)
        fits = load_fits(args.gains_report); report['gain_artifact'] = fits['identity']
        for number, trial in enumerate(TRIALS):
            budget.check_count('runs', number)
            stage = output / trial['id']; run = stage / uuid.uuid4().hex
            config = {'repo': str(root), 'assets': str(args.assets.resolve()), 'stage': str(stage), 'run': str(run),
                      'trial': trial, 'gains_report': str(args.gains_report.resolve()), 'storage': storage}
            supervision = bounded_process([sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(config)],
                                          stage, PROTOCOL['child_timeout_seconds'], environment,
                                          log_max_bytes=PROTOCOL['log_max_bytes'], storage_budget=budget)
            path = stage / 'result.json'
            report['trials'][trial['id']] = {'result': {'status': 'failed', 'trial': trial,
                    'error': 'child result not yet accepted'}, 'supervision': supervision,
                    'result_path': str(path), 'result_sha256': None}
            if path.exists():
                with path.open('rb') as stream:
                    raw = stream.read(PROTOCOL['result_max_bytes'] + 1)
                if len(raw) > PROTOCOL['result_max_bytes']:
                    raise ValueError('Child result exceeds declared read bound')
                data = json.loads(raw)
            else:
                data = {'status': 'failed', 'trial': trial, 'error': 'child result absent; inspect bounded native logs'}
            if supervision['status'] != 'completed' or supervision['returncode'] != 0:
                data['status'] = 'failed'
            report['trials'][trial['id']] = {'result': data, 'supervision': supervision,
                                           'result_path': str(path), 'result_sha256': gains.digest(path) if path.exists() else None}
        calibrations = [item['result'].get('physical_calibration') for item in report['trials'].values()]
        if any(value is None or value != calibrations[0] for value in calibrations):
            raise ValueError('Physical wheel radius/track missing or changed')
        report['physical_calibration'] = calibrations[0]
        report['comparison'] = compare_trials({key: item['result'] for key, item in report['trials'].items()})
        report['status'] = 'passed' if report['comparison']['accepted'] else 'rejected'
        report['limitations'] = ['Fixed fitted gains, new command amplitudes, one development seed/world; not held-out generalization.',
            'Manual compensation via upstream converter only; no Engine/task-profile or odometry integration.',
            'Pose caches evaluator-only; no online true-pose correction, learned or physical hardware claim.',
            'Discrete robot-contact stages only; world-only contacts may move and remain recorded.',
            'Standalone authored/model override; ordinary playback/native restore not qualified.']
    except Exception as error:
        report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:2048]})
    finally:
        for item in report['trials'].values():
            item['result'].pop('rows', None)
        report.update(wall_seconds=time.monotonic() - started, runtime_source_at_end=source_identity(root),
                      harness_sha256_at_end=harness_hashes())
        report['source_unchanged'] = (report['runtime_source'] == report['runtime_source_at_end'] and
                                      report['harness_sha256'] == report['harness_sha256_at_end'])
        if not report['source_unchanged']:
            report['status'] = 'failed'
        if report.get('gain_artifact'):
            try:
                report['gain_artifact_changed'] = gains.digest(args.gains_report) != GAIN_REPORT_SHA256
            except OSError as error:
                report['gain_artifact_changed'] = True
                report['artifact_check_error'] = str(error)[:512]
            if report['gain_artifact_changed']:
                report['status'] = 'failed'
        # Final bounded control report may consume the reserved headroom.
        control_budget = StorageBudget(budget.roots, budget.limits)
        gains.write_json(output / 'report.json', report, max_bytes=PROTOCOL['report_max_bytes'], storage_budget=control_budget)
    return report


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        return 0 if worker(json.loads(sys.argv[2])) else 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--gains-report', type=Path, default=Path(__file__).resolve().parents[1] / 'runs/m6-body-gain-diagnostic-v2-20261002/report.json')
    result = verify(parser.parse_args())
    print(json.dumps({'status': result['status'], 'accepted': result.get('comparison', {}).get('accepted'), 'error': result.get('error')}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
