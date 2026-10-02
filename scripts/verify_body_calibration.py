"""Independent development body calibration; fixed commands, offline truth only."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

TRIALS = [
    {'id': 'straight-02', 'kind': 'straight', 'action': [.2, 0.]},
    {'id': 'straight-04', 'kind': 'straight', 'action': [.4, 0.]},
    *[{'id': f'turn-{sign}-{int(amplitude * 10):02}', 'kind': 'turn',
       'action': [0., direction * amplitude]}
      for sign, direction in (('left', 1), ('right', -1)) for amplitude in (.1, .2, .4)],
]
PROTOCOL = {
    'version': 1, 'claim': 'standalone diagnostic development fitting; no runtime integration',
    'trials': TRIALS, 'seed': 0, 'ticks': 120, 'settling_ticks': 20, 'fit_ticks': 100,
    'child_timeout_seconds': 120, 'recording_max_bytes': 64 * 1024**2,
    'start_pose': [-5.5, 0., 0.], 'world': 'memory_world authored layout, no schedule; shifted start',
    'engine_scenario': 'reproduction', 'world_override': True,
    'driver_input': 'fixed trial action only; no pose, goal, encoder or task-state feedback',
    'fit': 'zero-intercept least squares: body forward / mean raw shaft increment; yaw / right-minus-left raw shaft increment',
    'relative_rms_max': .2, 'between_trial_range_over_mean_max': .2,
    'min_input_rms_rad': 1e-4, 'min_output_rms': {'straight': 1e-5, 'turn': 1e-5},
    'support': 'all 100 fit intervals finite; positive coefficient and cumulative input/output signs match command',
    'rejection': 'early termination/contact, missing support/excitation/direction, per-trial or pooled relative RMS, or coefficient disagreement',
    'threshold_scope': 'predeclared DEVELOPMENT rejection thresholds, not physical safety or sensor specifications',
}
PROTOCOL_SHA256 = hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def harness_hashes():
    return {name: digest(Path(__file__).with_name(name)) for name in
            ('verify_body_calibration.py', 'verify_tasks.py', 'verify_endurance.py')}


def fit_pairs(pairs, kind, direction):
    if len(pairs) < PROTOCOL['fit_ticks']:
        return {'accepted': False, 'reason': 'missing fit support'}
    if any(type(v) not in (int, float) or not math.isfinite(v) for pair in pairs for v in pair):
        return {'accepted': False, 'reason': 'nonfinite or malformed fit input'}
    xx = sum(x * x for x, _ in pairs); yy = sum(y * y for _, y in pairs)
    if math.sqrt(xx / len(pairs)) < PROTOCOL['min_input_rms_rad'] or math.sqrt(yy / len(pairs)) < PROTOCOL['min_output_rms'][kind]:
        return {'accepted': False, 'reason': 'insufficient excitation'}
    coefficient = sum(x * y for x, y in pairs) / xx
    residual = math.sqrt(sum((y - coefficient * x)**2 for x, y in pairs) / yy)
    directed = coefficient > 0 and direction * sum(x for x, _ in pairs) > 0 and direction * sum(y for _, y in pairs) > 0
    return {'accepted': directed and residual <= PROTOCOL['relative_rms_max'],
            'coefficient': coefficient, 'relative_rms': residual, 'direction_supported': directed,
            'input_rms_rad': math.sqrt(xx / len(pairs)), 'output_rms': math.sqrt(yy / len(pairs)),
            'sample_count': len(pairs)}


def fit_trials(trials):
    """Offline only. Rejected diagnostic slopes are retained, never accepted silently."""
    expected = {trial['id']: trial for trial in TRIALS}
    if set(trials) != set(expected):
        return {'accepted': False, 'reason': 'exact eight-trial coverage required', 'accepted_coefficients': None}
    per_trial, groups = {}, {}
    for kind in ('straight', 'turn'):
        pooled, coefficients = [], []
        for identifier, trial in expected.items():
            if trial['kind'] != kind:
                continue
            data = trials[identifier]
            if (data.get('status') != 'passed' or data.get('trial') != trial or
                    len(data.get('rows', [])) != 120 or
                    [row.get('tick') for row in data['rows']] != list(range(120))):
                return {'accepted': False, 'reason': f'{identifier}: incomplete/mismatched trial', 'accepted_coefficients': None}
            pairs = []
            for row in data['rows'][20:]:
                left, right = row['shaft_delta_rad']
                pairs.append(((left + right) / 2 if kind == 'straight' else right - left,
                              row['body_forward_m'] if kind == 'straight' else row['body_yaw_change_rad']))
            direction = 1 if kind == 'straight' or trial['action'][1] > 0 else -1
            fit = per_trial[identifier] = fit_pairs(pairs, kind, direction)
            if 'coefficient' in fit:
                coefficients.append(fit['coefficient'])
            # Remove the commanded sign for pooled direction testing only.
            pooled.extend((direction * x, direction * y) for x, y in pairs)
        combined = fit_pairs(pooled, kind, 1)
        mean = sum(coefficients) / len(coefficients) if coefficients else 0.
        disagreement = (max(coefficients) - min(coefficients)) / mean if mean > 0 else None
        trial_ids = [key for key, value in expected.items() if value['kind'] == kind]
        accepted = (all(per_trial[key]['accepted'] for key in trial_ids) and combined['accepted'] and
                    disagreement is not None and disagreement <= PROTOCOL['between_trial_range_over_mean_max'])
        groups[kind] = {'accepted': accepted, 'pooled_fit': combined, 'coefficient_range_over_mean': disagreement}
    accepted = all(group['accepted'] for group in groups.values())
    return {'accepted': accepted, 'per_trial': per_trial, 'groups': groups,
            'accepted_coefficients': ({'translation_m_per_mean_shaft_rad': groups['straight']['pooled_fit']['coefficient'],
                                       'yaw_rad_per_differential_shaft_rad': groups['turn']['pooled_fit']['coefficient']}
                                      if accepted else None)}


def sample(env):
    from palimpsest.task_profiles import encoder_angles
    return {'pose': [*map(float, env._base_xy()), float(env._base_yaw())],
            'time_s': float(env.data.time),
            'position_xyz': env.data.xpos[env.base_body_id].tolist(),
            'quaternion': env.data.xquat[env.base_body_id].tolist(),
            'shaft_angles_rad': encoder_angles(env), 'contacts': int(env.data.ncon)}


def worker(config):
    from palimpsest.engine import Engine
    from palimpsest import memory_world, task_profiles
    from palimpsest.profiles import validate_world
    from palimpsest.replay import _register_initial
    from verify_tasks import command
    import mujoco

    stage, run = Path(config['stage']), Path(config['run'])
    trial = config['trial']; rows = []; engine = None
    result = {'status': 'running', 'trial': trial, 'run': str(run), 'rows': rows}
    try:
        run.mkdir(exist_ok=False)
        engine = Engine.open(Path(config['repo']), Path(config['assets']), run / 'recording',
                             controller='manual', device='cpu', seed=0, scenario='reproduction',
                             texture='checker', run_id=run.name, max_bytes=PROTOCOL['recording_max_bytes'])
        if engine.task_state is not None or engine.memory is not None:
            raise ValueError('Calibration must have no task/memory supervisor')
        old_world = engine.world()
        memory_world.configure(engine.env, memory_world.initial_state(close_subject_id=None))
        engine.env.place_robot(*PROTOCOL['start_pose'], engine.env.data.qpos.copy(), engine.env.data.qvel.copy())
        mujoco.mj_forward(engine.env.model, engine.env.data)
        engine.env._prev_xy = engine.env._base_xy().copy()
        engine.observation = engine.env._get_obs()
        validate_world(engine.env)
        engine.revision += 1
        world = engine.world(); calibration = task_profiles.body_calibration(engine.env)
        result.update(actual_initial_world=world, actual_initial_sample=sample(engine.env), physical_calibration=calibration)
        override = {'original_world': old_world, 'authored_world': world,
                    'world_protocol_sha256': memory_world.PROFILE_SHA256, 'start_pose': PROTOCOL['start_pose']}
        override_sha256 = hashlib.sha256(json.dumps(override, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        result['world_override_sha256'] = override_sha256
        engine.writer.manifest.update(calibration_protocol=PROTOCOL, calibration_trial=trial,
                                      calibration_protocol_sha256=PROTOCOL_SHA256,
                                      standalone_calibration=True, initial_world=world,
                                      calibration_world_override=override, calibration_world_override_sha256=override_sha256)
        engine.writer.event('calibration_world_authored', protocol=PROTOCOL, trial=trial,
                            protocol_sha256=PROTOCOL_SHA256, world_override_sha256=override_sha256,
                            old_world=old_world, new_world=world, revision=engine.revision,
                            script_sha256=digest(__file__), harness_sha256=harness_hashes(),
                            world_protocol_sha256=memory_world.PROFILE_SHA256)
        _register_initial(engine, run)
        result['initial_snapshot_sha256'] = digest(run / 'snapshots/initial.snp')
        command(engine, 'fixed-action', 'set_action', {'action': trial['action']})
        for tick in range(PROTOCOL['ticks']):
            before = sample(engine.env)
            if engine.observation['sensors']['collision']:
                raise ValueError('Contact before calibration step')
            command(engine, f'step-{tick}', 'step')
            after = sample(engine.env)
            if not math.isclose(after['time_s'] - before['time_s'], .02, abs_tol=1e-9, rel_tol=0.):
                raise ValueError('Calibration control interval changed')
            yaw_delta = math.remainder(after['pose'][2] - before['pose'][2], math.tau)
            midpoint = before['pose'][2] + yaw_delta / 2
            dx, dy = [b - a for a, b in zip(before['pose'][:2], after['pose'][:2])]
            rows.append({'tick': tick, 'fit_interval': tick >= 20, 'before': before, 'after': after,
                         'shaft_delta_rad': [b - a for a, b in zip(before['shaft_angles_rad'], after['shaft_angles_rad'])],
                         'body_forward_m': dx * math.cos(midpoint) + dy * math.sin(midpoint),
                         'body_lateral_m': -dx * math.sin(midpoint) + dy * math.cos(midpoint),
                         'body_yaw_change_rad': yaw_delta, 'action': engine.last_transition['action'].tolist(),
                         'control': engine.last_transition['control'].tolist()})
            if rows[-1]['action'] != trial['action']:
                # Commands are represented in float32 by Engine; compare that explicit representation.
                import numpy as np
                if rows[-1]['action'] != np.asarray(trial['action'], dtype=np.float32).tolist():
                    raise ValueError('Effective calibration command changed')
            if engine.phase != 'paused' or engine.observation['sensors']['collision']:
                raise ValueError('Calibration terminated/contacted early: ' + str(engine.last_outcome))
        result['status'] = 'passed'
    except Exception as error:
        result.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:2048]})
    finally:
        if engine is not None:
            try:
                result['final_state'] = engine.public_state()
            except Exception as error:
                result.update(status='failed', diagnostic_error={'type': type(error).__name__, 'message': str(error)[:2048]})
            finally:
                try:
                    engine.close(); result['engine_closed'] = True
                except Exception as error:
                    result.update(status='failed', cleanup_error={'type': type(error).__name__, 'message': str(error)[:2048]})
        write_json(stage / 'result.json', result)
    return result['status'] == 'passed'


def verify(args):
    from palimpsest.evaluate import bounded_process
    from verify_endurance import source_identity
    root, output = args.repo.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'protocol': PROTOCOL, 'protocol_sha256': PROTOCOL_SHA256,
              'runtime_source': source_identity(root),
              'script_sha256': digest(__file__), 'harness_sha256': harness_hashes(), 'trials': {}}
    write_json(output / 'protocol.json', report)
    started = time.monotonic()
    environment = {**os.environ, 'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '2', 'MPLBACKEND': 'Agg'}
    try:
        for trial in TRIALS:
            stage = output / trial['id']; run = stage / uuid.uuid4().hex
            config = {'repo': str(root), 'assets': str(args.assets.resolve()), 'stage': str(stage),
                      'run': str(run), 'trial': trial}
            supervision = bounded_process([sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(config)],
                                          stage, PROTOCOL['child_timeout_seconds'], environment)
            data = json.loads((stage / 'result.json').read_text()) if (stage / 'result.json').exists() else {'status': 'failed'}
            if supervision['status'] != 'completed' or supervision['returncode'] != 0:
                data['status'] = 'failed'
            report['trials'][trial['id']] = {'result': data, 'supervision': supervision,
                                           'result_path': str(stage / 'result.json'),
                                           'result_sha256': digest(stage / 'result.json') if (stage / 'result.json').exists() else None}
        physical = [trial['result'].get('physical_calibration') for trial in report['trials'].values()]
        report['collection_passed'] = all(trial['result']['status'] == 'passed' for trial in report['trials'].values())
        if any(calibration is None or calibration != physical[0] for calibration in physical):
            raise ValueError('Physical loaded calibration missing/different between trials')
        report['physical_calibration'] = physical[0]
        report['fit'] = fit_trials({key: value['result'] for key, value in report['trials'].items()})
        report['status'] = 'passed' if report['fit']['accepted'] else 'rejected'
        report['limitations'] = ['Offline diagnostic fit only, no runtime calibration/integration.',
                                'Standalone authored override; ordinary reproduction/playback not qualified.',
                                'No held-out, learned-policy or physical safety claim.']
    except Exception as error:
        report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:2048]})
    finally:
        # Rows remain solely in authoritative child result files, including failures.
        for trial in report['trials'].values():
            trial['result'].pop('rows', None)
        report.update(wall_seconds=time.monotonic() - started, runtime_source_at_end=source_identity(root),
                      script_sha256_at_end=digest(__file__), harness_sha256_at_end=harness_hashes())
        report['source_unchanged'] = (report['runtime_source'] == report['runtime_source_at_end'] and
                                      report['harness_sha256'] == report['harness_sha256_at_end'])
        if not report['source_unchanged']:
            report['status'] = 'failed'
        write_json(output / 'report.json', report)
    return report


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        return 0 if worker(json.loads(sys.argv[2])) else 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    result = verify(parser.parse_args())
    print(json.dumps({'status': result['status'], 'fit_accepted': result.get('fit', {}).get('accepted'), 'error': result.get('error')}))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
