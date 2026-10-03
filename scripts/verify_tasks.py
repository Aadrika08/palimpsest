"""Bounded actual manual declared-cue task fixture; not learned/held-out competence."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

SCENARIOS = ('exploration-landmarks', 'encoder-homing')
DRIVER = {'version': 1, 'kind': 'artificial-manual-cue-following-fixture',
          'input': 'previous recorded effective sensors[2:4] only; no pose/goal/task-state input',
          'initial_action': [0., 0.], 'forward_max': .5, 'heading_gain': 1.,
          'rule': 'v=.5*clip(cos,0,1); heading=atan2(sin,cos); neutral cue gives zero',
          'max_ticks': 600, 'snapshot_tick': 8, 'continuation_ticks': 4,
          'claim': 'development fixture; no training, tuning, held-out or learned-policy result'}
DRIVERS = {'v1': DRIVER, 'v2': {**DRIVER, 'version': 2, 'forward_max': .4,
          'heading_turn_cap_rad': .4, 'align_threshold_rad': .1,
          'rule': 'if abs(atan2(sin,cos))>.1: v=0, heading=clip(angle,-.4,.4); else v=.4, heading=angle; neutral cue gives zero',
          'actual_home_max_distance_m': .25,
          'actual_home_gate': 'task_completed plus isolated evaluator true home distance<=.25m; no truth feedback',
          'claim': 'development manual fixture in independently measured command range; no transient/mixed generalization guarantee'}}


def cue_action(bearing, *, driver='v1'):
    import numpy as np
    if driver not in DRIVERS:
        raise ValueError('Unknown manual driver')
    if bearing is None:
        return [0., 0.]
    try:
        pair = np.asarray(bearing, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError('Expected finite [cos,sin] bearing') from error
    if pair.shape != (2,) or not np.isfinite(pair).all():
        raise ValueError('Expected finite [cos,sin] bearing')
    norm = float(np.linalg.norm(pair))
    if norm == 0.:
        return [0., 0.]
    if not math.isclose(norm, 1., abs_tol=1e-5, rel_tol=0.):
        raise ValueError('Bearing must be neutral or a unit direction')
    angle = math.atan2(float(pair[1]), float(pair[0]))
    if driver == 'v2':
        if abs(angle) > DRIVERS['v2']['align_threshold_rad']:
            return [0., max(-.4, min(.4, angle))]
        return [.4, angle]
    return [DRIVER['forward_max'] * min(1., max(0., float(pair[0]))), angle]


def previous_bearing(transition):
    if transition is None:
        return None
    import numpy as np
    sensors = np.asarray(transition['sensors'])
    if sensors.shape != (4,):
        raise ValueError('Recorded effective sensor vector must contain four values')
    bearing = sensors[2:4].astype(np.float64).tolist()
    cue_action(bearing)  # Reject malformed declared cues, never substitute one.
    return bearing


def task_completed(state):
    return (state.get('phase') == 'terminated' and
            (state.get('last_outcome') or {}).get('reason') == 'task_completed' and
            (state.get('task') or {}).get('phase') == 'complete')


def completion_passed(state, *, driver='v1'):
    if driver not in DRIVERS:
        raise ValueError('Unknown manual driver')
    if not task_completed(state):
        return False
    if driver == 'v2' and state.get('scenario') == 'encoder-homing':
        distance = state['last_outcome'].get('evaluator_actual_home_distance_m')
        return (type(distance) in (int, float) and math.isfinite(distance) and
                0 <= distance <= DRIVERS['v2']['actual_home_max_distance_m'])
    return True


def compare_tick(expected, actual, expected_task, actual_task):
    from palimpsest.replay import _same_tick, _same_json
    _same_tick(expected, actual, 'policy', int(actual['tick']))
    _same_json(expected_task, actual_task, 'task_state')


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')
    temporary.replace(path)


def file_hashes(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(path.rglob('*')) if p.is_file()}


def command(engine, identifier, kind, payload=None):
    before = engine.total_tick
    message = {'id': identifier, 'kind': kind, 'expected_state': 'paused',
               'expected_episode': engine.episode, 'expected_revision': engine.revision}
    if payload is not None:
        message['payload'] = payload
    receipt = engine.submit(message)
    if receipt['status'] != 'queued':
        raise ValueError('Command was not queued: ' + str(receipt['status']))
    engine.advance()
    receipt = engine.submit(message)  # Idempotent lookup; never applies twice.
    if receipt['status'] != 'applied' or engine.total_tick != before + (kind == 'step'):
        raise ValueError(f'{kind} failed its single-boundary contract: {receipt["status"]}')


def evaluator_sample(engine):
    """Evaluator only; this result is never an argument to cue_action."""
    from palimpsest.task_profiles import encoder_angles
    return {'pose': [*map(float, engine.env._base_xy()), float(engine.env._base_yaw())],
            'angles': encoder_angles(engine.env)}


def evaluator_record(engine, before, after, origin, action):
    pose = before['pose'];dx, dy = pose[0] - origin[0], pose[1] - origin[1]
    truth = [dx * math.cos(origin[2]) + dy * math.sin(origin[2]),
             -dx * math.sin(origin[2]) + dy * math.cos(origin[2])]
    odometry = engine.task_state['odometry']
    return {'tick': engine.episode_step - 1, 'true_pre_pose': pose,
            'measured_pre_shaft_angles_rad': before['angles'],
            'estimated_local_pose': [odometry['x_m'], odometry['y_m'], odometry['yaw_rad']],
            'true_local_xy': truth,
            'estimate_error_m': math.dist(truth, [odometry['x_m'], odometry['y_m']]),
            'true_step_displacement_m': math.dist(pose[:2], after['pose'][:2]),
            'true_step_forward_m': ((after['pose'][0] - pose[0]) * math.cos(pose[2]) +
                                    (after['pose'][1] - pose[1]) * math.sin(pose[2])),
            'true_step_yaw_change_rad': math.remainder(after['pose'][2] - pose[2], math.tau),
            'measured_step_shaft_delta_rad': [b - a for a, b in zip(before['angles'], after['angles'])],
            'requested_action': action, 'effective_action': engine.last_transition['action'].tolist(),
            'task_phase': engine.task_state['phase'], 'dwell_ticks': engine.task_state['dwell_ticks'],
            'control': engine.last_transition['control'].tolist()}


def evaluate_motion(rows, calibration):
    straight = [r for r in rows if r['effective_action'][0] > .05 and abs(r['effective_action'][1]) < .1]
    shaft = [sum(r['measured_step_shaft_delta_rad'][i] for r in straight) for i in range(2)]
    # Project actual per-step displacement along the pre-step body heading.
    forward = sum(r['true_step_forward_m'] for r in straight)
    dwell = [r for r in rows if r['dwell_ticks'] > 0]
    return {'loaded_body_calibration': calibration, 'straight_forward_intervals': len(straight),
            'measured_straight_shaft_delta_rad': shaft, 'measured_straight_body_forward_m': forward,
            'positive_shaft_and_forward_direction_observed': bool(straight) and min(shaft) > 0. and forward > 0.,
            'max_encoder_vs_true_local_error_m': max(r['estimate_error_m'] for r in rows),
            'dwell_intervals': len(dwell),
            'max_dwell_true_displacement_m': max((r['true_step_displacement_m'] for r in dwell), default=None),
            'max_dwell_true_yaw_change_rad': max((abs(r['true_step_yaw_change_rad']) for r in dwell), default=None),
            'scope': 'isolated evaluator measurements; no correction/input to driver. Quantized shaft rest does not prove body rest, slip-free travel or physical stopping.'}


def worker(config):
    from palimpsest.engine import Engine
    from palimpsest.replay import _register_initial, replay_run
    from palimpsest.snapshots import capture, restore, save_snapshot, read_snapshot
    stage, run = Path(config['stage']), Path(config['run'])
    driver = config.get('driver', 'v1'); protocol = DRIVERS[driver]
    if config['mode'] in ('actions', 'policy'):
        run.mkdir(exist_ok=False)
        result = replay_run(Path(config['source']), run, mode=config['mode'],
                            repo_root=Path(config['repo']), asset_root=Path(config['assets']))
        write_json(stage / 'result.json', {'status': result['status'], 'run': str(run),
                   'compared_ticks': result['compared_ticks'], 'report': str(run / 'replay-report.json')})
        return result['status'] == 'passed'
    engine = None
    result = {'status': 'running', 'run': str(run), 'mode': config['mode'], 'driver': protocol}
    rows = []
    try:
        run.mkdir(exist_ok=False)
        engine = Engine.open(Path(config['repo']), Path(config['assets']), run / 'recording',
                             controller='manual', device='cpu', seed=config['seed'],
                             scenario=config['scenario'], texture='checker', run_id=run.name,
                             max_bytes=config['max_bytes'])
        engine.writer.event('manual_driver_protocol', protocol=protocol,
                            script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        if config['mode'] == 'source':
            _register_initial(engine, run)
            origin = evaluator_sample(engine)['pose']
            continuation, snapshot = [], None
            for tick in range(protocol['max_ticks']):
                action = cue_action(previous_bearing(engine.last_transition), driver=driver)
                before = evaluator_sample(engine)
                command(engine, f'action-{tick}', 'set_action', {'action': action})
                command(engine, f'step-{tick}', 'step')
                if engine.last_transition is None:
                    raise ValueError('Missing recorded task transition')
                rows.append(evaluator_record(engine, before, evaluator_sample(engine), origin, action))
                if snapshot is not None and len(continuation) < protocol['continuation_ticks']:
                    continuation.append({'tick': tick, 'requested_action': action,
                                         'task': copy.deepcopy(engine.task_state)})
                if engine.phase != 'paused':
                    break
                if engine.total_tick == protocol['snapshot_tick']:
                    if engine.task_state['odometry']['travel_m'] <= 0.:
                        raise ValueError('Snapshot boundary has no measured encoder progress')
                    engine.writer.flush()
                    snapshot = capture(engine.env, engine.observation, policy=engine.policy,
                                       teacher=engine.teacher, application=engine.application_state())
                    save_snapshot(snapshot, stage / 'progress.snp')
                    result['snapshot_task'] = copy.deepcopy(engine.task_state)
            state = engine.public_state()
            result.update(final_state=state, task_completed=task_completed(state), recorded_ticks=len(rows),
                          motion=evaluate_motion(rows, engine.task_state['odometry']['calibration']))
            result['completion_gate_passed'] = completion_passed(state, driver=driver)
            if driver == 'v2' and config['scenario'] == 'encoder-homing':
                result['actual_home_closure'] = {
                    'distance_m': (state.get('last_outcome') or {}).get('evaluator_actual_home_distance_m'),
                    'threshold_m': protocol['actual_home_max_distance_m'],
                    'passed': result['completion_gate_passed'], 'evaluator_only': True}
            write_json(stage / 'evaluator.json', rows)
            write_json(stage / 'continuation.json', continuation)
            result['continuation_ticks'] = len(continuation)
            result['snapshot_sha256'] = (hashlib.sha256((stage / 'progress.snp').read_bytes()).hexdigest()
                                         if snapshot is not None else None)
            if not result['task_completed'] or snapshot is None or len(continuation) != 4:
                raise ValueError('Task did not complete with a four-tick progress-snapshot window')
            if not result['completion_gate_passed']:
                raise ValueError('Actual home closure failed the predeclared 0.25m evaluator gate')
        else:
            snapshot = read_snapshot(Path(config['snapshot']))
            engine.validate_application(snapshot['application'])
            observation, application = restore(snapshot, engine.env, policy=engine.policy, teacher=engine.teacher)
            engine.observation = observation
            engine.restore_application(application)
            from palimpsest.replay import _same_json
            _same_json(snapshot['application']['task_state'], engine.task_state, 'restored_task')
            expected = json.loads(Path(config['continuation']).read_text())
            states = []
            for item in expected:
                tick = item['tick']
                if engine.episode_step != tick:
                    raise ValueError('Restored continuation cursor differs')
                command(engine, f'action-{tick}', 'set_action', {'action': item['requested_action']})
                command(engine, f'step-{tick}', 'step')
                states.append(copy.deepcopy(engine.task_state))
            write_json(stage / 'task-states.json', states)
            result['continuation_ticks'] = len(states)
        result['status'] = 'passed'
    except Exception as error:
        result.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:2048]})
    finally:
        if engine is not None:
            try:
                result.setdefault('final_state', engine.public_state())
                if config['mode'] == 'source' and rows:
                    write_json(stage / 'evaluator.json', rows)
            except Exception as error:
                result.update(status='failed', diagnostic_error={'type': type(error).__name__, 'message': str(error)[:2048]})
            finally:
                try:
                    engine.close()
                    result['engine_closed'] = True
                except Exception as error:
                    result.update(status='failed', cleanup_error={'type': type(error).__name__, 'message': str(error)[:2048]})
        write_json(stage / 'result.json', result)
    return result['status'] == 'passed'


def verify(args):
    from palimpsest.evaluate import bounded_process
    from palimpsest.records import iter_ticks
    from verify_endurance import source_identity
    root, output = args.repo.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    protocol = DRIVERS[args.driver]
    report = {'version': 1, 'status': 'running', 'driver': protocol,
              'scope': 'actual manual declared-cue development fixture; no true-pose/goal feedback',
              'limitations': ['No learned policy, held-out, physical or full-FLYNN task qualification',
                             'One progress snapshot per task; dwell/home-phase snapshots remain pending'],
              'runtime_source': source_identity(root),
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'profiles': {}}
    started = time.monotonic()
    environment = {**os.environ, 'MUJOCO_GL': 'egl', 'MPLBACKEND': 'Agg', 'OMP_NUM_THREADS': '2'}
    try:
        for scenario in args.scenarios:
            base = output / scenario; base.mkdir()
            result = report['profiles'][scenario] = {'status': 'running', 'workers': {}}
            source_run = base / 'source' / uuid.uuid4().hex
            def launch(mode, **extra):
                stage = base / mode
                config = {'mode': mode, 'stage': str(stage), 'run': str(source_run if mode == 'source' else stage / uuid.uuid4().hex),
                          'repo': str(root), 'assets': str(args.assets.resolve()), 'scenario': scenario,
                          'seed': args.seed, 'max_bytes': args.max_bytes, 'driver': args.driver, **extra}
                supervision = bounded_process([sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(config)],
                                               stage, args.timeout, environment)
                result['workers'][mode] = supervision
                data = json.loads((stage / 'result.json').read_text()) if (stage / 'result.json').exists() else {}
                result[mode] = data
                if supervision['status'] != 'completed' or supervision['returncode'] != 0 or data.get('status') != 'passed':
                    raise ValueError(f'{scenario}/{mode} failed; inspect its result/supervisor/native logs')
                if mode in ('source', 'restored'):
                    manifest = json.loads((Path(data['run']) / 'recording/manifest.json').read_text())
                    if manifest['status'] != 'completed':
                        raise ValueError(f'{mode} recording did not close successfully')
                return data
            source = launch('source')
            immutable = file_hashes(source_run)
            restored = launch('restored', snapshot=str(base / 'source/progress.snp'),
                              continuation=str(base / 'source/continuation.json'))
            expected = json.loads((base / 'source/continuation.json').read_text())
            left = [row for row in iter_ticks(source_run / 'recording') if DRIVER['snapshot_tick'] <= int(row['tick']) < DRIVER['snapshot_tick'] + 4]
            right = list(iter_ticks(Path(restored['run']) / 'recording'))
            states = json.loads((base / 'restored/task-states.json').read_text())
            if not len(left) == len(right) == len(states) == len(expected) == 4:
                raise ValueError('Continuation record length differs')
            for a, b, expected_state, actual_state in zip(left, right, expected, states):
                compare_tick(a, b, expected_state['task'], actual_state)
            result['native_continuation'] = {'status': 'passed', 'ticks': 4, 'task_state': 'matched',
                                           'float_atol': 1e-6, 'float_rtol': 1e-6, 'cameras_and_integers': 'exact'}
            for mode in ('actions', 'policy'):
                launch(mode, source=str(source_run))
            if immutable != file_hashes(source_run):
                raise ValueError('Immutable source changed after branch/replays')
            result.update(status='passed', source_unchanged=True)
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:2048]})
    finally:
        report['runtime_source_at_end'] = source_identity(root)
        report['runtime_source_unchanged'] = report['runtime_source_at_end'] == report['runtime_source']
        report['script_unchanged'] = report['script_sha256'] == hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        if not report['runtime_source_unchanged'] or not report['script_unchanged']:
            report['status'] = 'failed'
        report['wall_seconds'] = time.monotonic() - started
        write_json(output / 'report.json', report)
    return report


def main():
    if len(sys.argv) == 3 and sys.argv[1] == '--worker':
        return 0 if worker(json.loads(sys.argv[2])) else 1
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--scenarios', choices=SCENARIOS, nargs='+', default=list(SCENARIOS))
    parser.add_argument('--driver', choices=tuple(DRIVERS), default='v1', help='v1 retains legacy estimate-only gate; v2 also requires actual home closure<=0.25m')
    parser.add_argument('--seed', type=int, default=0)
    parser.add_argument('--timeout', type=int, default=180, help='hard timeout for each of eight sequential owners')
    parser.add_argument('--max-bytes', type=int, default=2 * 1024**3, help='per-recording byte quota')
    args = parser.parse_args()
    if not 0 <= args.seed < 2**31 or not 1 <= args.timeout <= 600 or not 1024**2 <= args.max_bytes <= 2 * 1024**3:
        parser.error('bounded seed, timeout1–600s and recording quota1MiB–2GiB required')
    if len(set(args.scenarios)) != len(args.scenarios):
        parser.error('each scenario may be requested only once')
    result = verify(args)
    print(json.dumps({'status': result['status'], 'output': str(args.output), 'error': result.get('error')}, allow_nan=False))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
