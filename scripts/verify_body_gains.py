"""Standalone fixed-command wheel-response diagnostic; no compensation."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

TRIALS = [{'id': f'{condition}-{direction}-{int(amplitude * 10):02}',
           'condition': condition, 'left_gear_factor': factor, 'action': [sign * amplitude, 0.]}
          for condition, factor in (('baseline', 1.), ('left-08', .8))
          for direction, sign in (('forward', 1), ('reverse', -1)) for amplitude in (.2, .4)]
FIT_BOUNDS = {'max_samples': 400, 'min_samples': 100, 'min_excitation': 1.,
              'gain_bounds': [1., 100.], 'control_limit': 2.,
              'dt_bounds_s': [.02 - 1e-9, .02 + 1e-9], 'max_rate_rad_s': 100.,
              'max_residual_rad_s': 2., 'max_relative_rmse': .2}
GROUND_SUPPORT = ['left_wheel_geom', 'right_wheel_geom', 'caster_wheel_geom']
ROBOT_BODIES = {'base', 'left_wheel', 'right_wheel', 'front_caster_mount', 'caster_wheel'}
ROBOT_GEOMS = {'base_geom', 'left_wheel_geom', 'right_wheel_geom', 'caster_fork',
               'caster_wheel_geom', 'cam_left_marker', 'cam_right_marker'}
PROTOCOL = {
    'version': 2, 'claim': 'standalone development gain diagnostic; no runtime integration',
    'trials': TRIALS, 'seed': 0, 'ticks': 120, 'settling_ticks': 20, 'fit_ticks': 100,
    'child_timeout_seconds': 120, 'recording_max_bytes': 64 * 1024**2,
    'start_pose': [-3.5, 0., 0.], 'goal_xy': [-3.5, 3.],
    'world': 'unchanged authored memory_world obstacle layout; explicit start/goal override',
    'engine_scenario': 'reproduction', 'world_override': True,
    'driver_input': 'fixed straight action only; no pose, goal, encoder or task feedback',
    'perturbation': 'multiply left_motor scalar gear by .8; right gear/physical radius/track unchanged',
    'fit': 'existing fit_wheel_gains: raw shaft increment / measured dt = gain * actual control',
    'fit_bounds': FIT_BOUNDS, 'between_trial_gain_range_over_mean_max': .2,
    'pipeline': {'mujoco_version': '3.3.6', 'integrator': 'Euler', 'physics_dt_s': .002,
                 'frame_skip': 10, 'control_dt_s': .02, 'max_contacts_per_stage': 128},
    'contact_allowlist': [['floor', name] for name in GROUND_SUPPORT],
    'contact_scope': 'unexpected robot-incident contacts only; all world-only pairs retained and classified separately',
    'robot_ownership': 'all descendants of pinned base body; exact robot body/geom names required',
    'contact_coverage': 'all ten pre-control position/velocity stages plus final cached pairs; '
                        'end pairs refer to last pre-integration stage, not a fresh endpoint evaluation',
    'rejection': 'any unknown or non-allowlisted robot-incident contact in any interval including settling, callback/pipeline '
                 'mismatch, early termination, incomplete support, fit bounds or gain disagreement',
    'threshold_scope': 'predeclared DEVELOPMENT rejection limits; not physical safety/sensor limits',
}
PROTOCOL_SHA256 = hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, data, *, max_bytes=None, storage_budget=None):
    payload = (json.dumps(data, indent=2, allow_nan=False) + '\n').encode()
    if max_bytes is not None and len(payload) > max_bytes:
        raise ValueError('Diagnostic JSON exceeds declared size bound')
    temporary = path.with_suffix('.tmp')
    if storage_budget is not None:
        storage_budget.check(len(payload), path=temporary)
    temporary.write_bytes(payload)
    temporary.replace(path)


def harness_hashes():
    return {name: digest(Path(__file__).with_name(name)) for name in
            ('verify_body_gains.py', 'verify_body_calibration.py', 'verify_tasks.py', 'verify_endurance.py')}


def fixed_action_matches(action, trial):
    import numpy as np
    return action == np.asarray(trial['action'], dtype=np.float64).tolist()


from palimpsest.body_profile import ContactProbe, contact_ownership

def fit_trials(trials):
    from palimpsest.task_mechanics import fit_wheel_gains
    expected = {trial['id']: trial for trial in TRIALS}
    result = {'accepted': False, 'per_trial': {}, 'conditions': {}, 'accepted_gains': None}
    try:
        if set(trials) != set(expected):
            raise ValueError('Exact eight-trial coverage required')
        for identifier, trial in expected.items():
            data = trials[identifier]
            rows = data.get('rows', [])
            if (data.get('status') != 'passed' or data.get('trial') != trial or len(rows) != 120 or
                    [row.get('tick') for row in rows] != list(range(120)) or
                    any(row.get('contact') is not False or row.get('coverage_passed') is not True for row in rows)):
                raise ValueError(identifier + ': incomplete or rejected interval support')
            samples = [{name: row[name] for name in ('control', 'increments_rad', 'dt_s', 'contact')}
                       for row in rows[20:]]
            result['per_trial'][identifier] = fit_wheel_gains(samples, **FIT_BOUNDS)
        for condition in ('baseline', 'left-08'):
            ids = [identifier for identifier, trial in expected.items() if trial['condition'] == condition]
            samples = [{name: row[name] for name in ('control', 'increments_rad', 'dt_s', 'contact')}
                       for identifier in ids for row in trials[identifier]['rows'][20:]]
            pooled = fit_wheel_gains(samples, **FIT_BOUNDS)
            agreement = []
            for wheel in range(2):
                gains = [result['per_trial'][identifier]['gains_rad_s_per_control'][wheel] for identifier in ids]
                agreement.append((max(gains) - min(gains)) / (sum(gains) / len(gains)))
            result['conditions'][condition] = {'pooled': pooled, 'gain_range_over_mean': agreement}
            if any(value > PROTOCOL['between_trial_gain_range_over_mean_max'] for value in agreement):
                raise ValueError(condition + ': direction/amplitude gain disagreement')
        result['accepted'] = True
        result['accepted_gains'] = {key: value['pooled']['gains_rad_s_per_control'] for key, value in result['conditions'].items()}
    except (ValueError, KeyError, TypeError) as error:
        result['reason'] = str(error)[:512]
    return result


def collect_trial(config, protocol, protocol_sha256, *, command_plan=None, harness=None,
                  storage_budget=None, result_max_bytes=None):
    """Shared fixed-action owner; optional prevalidated nominal/applied plan."""
    from palimpsest.engine import Engine
    from palimpsest import memory_world, task_profiles
    from palimpsest.profiles import validate_world
    from palimpsest.replay import _register_initial
    from palimpsest.snapshots import _model_digest
    from verify_body_calibration import sample
    from verify_tasks import command
    import mujoco

    stage, run = Path(config['stage']), Path(config['run'])
    trial = config['trial']; rows = []; engine = probe = None
    result = {'status': 'running', 'trial': trial, 'run': str(run), 'rows': rows}
    applied_action = trial['action'] if command_plan is None else command_plan['applied_action']
    try:
        if mujoco.get_mjcb_control() is not None:
            raise ValueError('Refusing existing global control callback before environment construction')
        run.mkdir(exist_ok=False)
        engine = Engine.open(Path(config['repo']), Path(config['assets']), run / 'recording',
                             controller='manual', device='cpu', seed=protocol['seed'], scenario='reproduction',
                             texture='checker', run_id=run.name, max_bytes=protocol['recording_max_bytes'],
                             **({'storage_budget': storage_budget} if storage_budget is not None else {}))
        env = engine.env
        if engine.task_state is not None or engine.memory is not None:
            raise ValueError('Diagnostic requires no task/memory supervisor')
        old_world = engine.world(); old_model = _model_digest(env.model)
        left = mujoco.mj_name2id(env.model, mujoco.mjtObj.mjOBJ_ACTUATOR, 'left_motor')
        right = mujoco.mj_name2id(env.model, mujoco.mjtObj.mjOBJ_ACTUATOR, 'right_motor')
        if (left, right) != (0, 1) or env.model.nu != 2:
            raise ValueError('Pinned two-motor ordering required')
        original_gear = env.model.actuator_gear.copy()
        if original_gear.tolist() != [[3., 0., 0., 0., 0., 0.], [3., 0., 0., 0., 0., 0.]]:
            raise ValueError('Pinned scalar motor gears required')
        memory_world.configure(env, memory_world.initial_state(close_subject_id=None))
        env._goal_xy[:] = protocol['goal_xy']
        env.model.site_pos[env.goal_site_id, :2] = protocol['goal_xy']
        env.place_robot(*protocol['start_pose'], env.data.qpos.copy(), env.data.qvel.copy())
        env.model.actuator_gear[left, 0] *= trial['left_gear_factor']
        mujoco.mj_forward(env.model, env.data)
        env._prev_xy = env._base_xy().copy()
        engine.observation = env._get_obs()
        validate_world(env)
        engine.revision += 1
        world = engine.world(); calibration = task_profiles.body_calibration(env)
        override = {'original_world': old_world, 'authored_world': world,
                    'world_protocol_sha256': memory_world.PROFILE_SHA256,
                    'original_model_sha256': old_model, 'actual_model_sha256': _model_digest(env.model),
                    'original_actuator_gear': original_gear.tolist(), 'actual_actuator_gear': env.model.actuator_gear.tolist(),
                    'start_pose': protocol['start_pose'], 'goal_xy': protocol['goal_xy']}
        headers = Path(mujoco.__file__).parent / 'include/mujoco'
        result['pipeline_evidence'] = {
            'mujoco_version': mujoco.__version__,
            'installed_headers_sha256': {name: digest(headers / name) for name in ('mjmodel.h', 'mujoco.h')},
            'upstream_files_sha256': {name: digest(Path(config['repo']) / 'upstream/fly-gym/environment' / name)
                for name in ('mujoco_two_cam_env_random_obstacles.py', 'mujoco_model_random_obstacles.xml')},
            'integrator_enum': int(env.model.opt.integrator), 'physics_dt_s': float(env.model.opt.timestep),
            'frame_skip': env.frame_skip, 'disableflags': int(env.model.opt.disableflags),
            'model_address': env.model._address, 'data_address': env.data._address}
        override_hash = hashlib.sha256(json.dumps(override, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        result.update(actual_initial_world=world, actual_initial_sample=sample(env), physical_calibration=calibration,
                      model_override=override, world_override_sha256=override_hash)
        probe = ContactProbe(mujoco, env)
        result['contact_ownership'] = {**probe.ownership, 'model_sha256': override['actual_model_sha256']}
        if command_plan is not None:
            if float(env._action_scale) != 2.:
                raise ValueError('Pinned control scale 2 required for inverse')
            result['command_plan'] = command_plan
            engine.writer.manifest['fixed_command_plan'] = command_plan
            engine.writer.event('fixed_command_declared', command_plan=command_plan)
        engine.writer.manifest.update(gain_protocol=protocol, gain_trial=trial, gain_protocol_sha256=protocol_sha256,
                                      standalone_calibration=True, initial_world=world,
                                      gain_world_override=override, gain_world_override_sha256=override_hash,
                                      gain_contact_ownership=result['contact_ownership'])
        engine.writer.event('gain_world_authored', protocol=protocol, trial=trial,
                            protocol_sha256=protocol_sha256, override=override, revision=engine.revision,
                            contact_ownership=result['contact_ownership'],
                            script_sha256=digest(__file__), harness_sha256=harness if harness is not None else harness_hashes())
        _register_initial(engine, run, **({'storage_budget': storage_budget} if storage_budget is not None else {}))
        result['initial_snapshot_sha256'] = digest(run / 'snapshots/initial.snp')
        probe.install()
        command(engine, 'fixed-action', 'set_action', {'action': applied_action})
        for tick in range(protocol['ticks']):
            before = sample(env)
            probe.begin(tick)
            command(engine, f'step-{tick}', 'step')
            interval = probe.end()
            after = sample(env)
            rows.append({'tick': tick, 'fit_interval': tick >= protocol['settling_ticks'], 'before': before, 'after': after,
                         'increments_rad': [b - a for a, b in zip(before['shaft_angles_rad'], after['shaft_angles_rad'])],
                         'dt_s': after['time_s'] - before['time_s'], 'control': env.data.ctrl.tolist(),
                         'action': engine.last_transition['action'].tolist(), 'contact': interval['contact'],
                         'coverage_passed': interval['coverage_passed'], 'interval_contacts': interval})
            if not fixed_action_matches(rows[-1]['action'], {'action': applied_action}):
                raise ValueError('Fixed effective action changed')
            if env.data.ctrl.tolist() != engine.last_transition['control'].tolist():
                raise ValueError('Recorded control differs from actual control')
            if command_plan is not None:
                rows[-1].update(nominal_action=command_plan['nominal_action'],
                                applied_action=rows[-1]['action'], nominal_control=command_plan['nominal_control'],
                                applied_control_target=command_plan['applied_control_float32'])
                if rows[-1]['control'] != command_plan['applied_control_float32']:
                    raise ValueError('Inverse failed exact float32 effective-control roundtrip')
            if not interval['coverage_passed'] or interval['contact'] or engine.phase != 'paused':
                raise ValueError('Rejected callback/contact/lifecycle interval; full packet retained')
        result['final_model_sha256'] = _model_digest(env.model)
        if result['final_model_sha256'] != override['actual_model_sha256']:
            raise ValueError('Immutable model changed during collection')
        result['status'] = 'passed'
    except Exception as error:
        result.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:2048]})
    finally:
        if probe is not None:
            result['callback_violations'] = probe.violations
            if probe.active:
                result['incomplete_interval'] = {'callback_count': probe.count, 'stages': probe.stages}
            try:
                probe.close(); result['callback_restored'] = True
            except Exception as error:
                result.update(status='failed', callback_cleanup_error=str(error)[:512])
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
        write_json(stage / 'result.json', result, max_bytes=result_max_bytes, storage_budget=storage_budget)
    return result['status'] == 'passed'


def worker(config):
    return collect_trial(config, PROTOCOL, PROTOCOL_SHA256)


def verify(args):
    from palimpsest.evaluate import bounded_process
    from verify_endurance import source_identity
    root, output = args.repo.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'status': 'running', 'protocol': PROTOCOL, 'protocol_sha256': PROTOCOL_SHA256,
              'runtime_source': source_identity(root), 'harness_sha256': harness_hashes(), 'trials': {}}
    write_json(output / 'protocol.json', report)
    started = time.monotonic()
    environment = {**os.environ, 'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '2', 'MPLBACKEND': 'Agg'}
    try:
        for trial in TRIALS:
            stage = output / trial['id']; run = stage / uuid.uuid4().hex
            config = {'repo': str(root), 'assets': str(args.assets.resolve()), 'stage': str(stage), 'run': str(run), 'trial': trial}
            supervision = bounded_process([sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(config)],
                                          stage, PROTOCOL['child_timeout_seconds'], environment)
            path = stage / 'result.json'
            data = json.loads(path.read_text()) if path.exists() else {'status': 'failed'}
            if supervision['status'] != 'completed' or supervision['returncode'] != 0:
                data['status'] = 'failed'
            report['trials'][trial['id']] = {'result': data, 'supervision': supervision,
                                           'result_path': str(path), 'result_sha256': digest(path) if path.exists() else None}
        calibrations = [item['result'].get('physical_calibration') for item in report['trials'].values()]
        if any(value is None or value != calibrations[0] for value in calibrations):
            raise ValueError('Physical wheel radius/track changed or missing')
        report['physical_calibration'] = calibrations[0]
        report['fit'] = fit_trials({key: item['result'] for key, item in report['trials'].items()})
        report['status'] = 'passed' if report['fit']['accepted'] else 'rejected'
        report['limitations'] = ['Empirical settled torque-control/shaft response; no universal velocity model.',
                                'Pre-control contact stages only; cached end contacts, no continuous collision claim.',
                                'World-only contacts remain recorded and may move; no static-world/no-world-contact claim.',
                                'Standalone authored/model override; no ordinary playback or snapshot restore qualification.',
                                'No compensation, online truth correction, held-out, learned or physical safety claim.']
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
