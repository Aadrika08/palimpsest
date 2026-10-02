"""Eight serialized development acquisitions; manual privileged pose supervision.

No held-out execution, retries, replay or tuning. Import and --plan-only are pure.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

from palimpsest import artifacts, memory, memory_experiment, memory_history
from palimpsest.evaluate import bounded_process
from palimpsest.memory_history import collect_history

PROTOCOL = {'version': 1, 'claim': 'development-recorded-acquisition-batch',
    'seeds': [0, 1, 2, 3], 'regimes': list(memory.RELATIONS),
    'split': 'development-history', 'kind': 'change', 'controller': 'manual',
    'access': 'privileged-manual-pose-supervision', 'uses_u': False,
    'max_ticks': 600, 'internal_wall_seconds': 150, 'timeout_seconds': 160,
    'recording_max_bytes': 192 * 1024**2, 'log_max_bytes': 1024**2,
    'retries': 0, 'collector_input_max_bytes': memory_history.MAX_INPUT_BYTES,
    'collector_protocol_sha256': memory_history.PROTOCOL_SHA256,
    'case_protocol_sha256': memory_experiment.PROTOCOL_SHA256,
    'schedule_sha256': memory_experiment.make_world_case(0, 'local_cue',
        'development-history', acquisition=True)['acquisition_protocol_sha256']}
PROTOCOL_SHA256 = memory.sha256(PROTOCOL)


def _hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def source_identity(repo):
    repo = Path(repo)
    manifest = json.loads((repo / 'model_manifests/flynn-full-vision.json').read_text())
    return {'source_sha256': {str(p.relative_to(repo)): _hash(p)
                for p in sorted((repo / 'src/palimpsest').glob('*.py'))},
        'lock_sha256': _hash(repo / 'uv.lock'), 'upstream_commit': manifest['upstream_commit'],
        'driver_sha256': _hash(Path(__file__))}


def validate_job(job):
    memory._fields(job, 'repo assets run_path run_id case batch_protocol_sha256')
    case = memory_experiment.validate_world_case(job['case'])
    if (case['seed'] not in PROTOCOL['seeds'] or case['split'] != 'development-history'
            or case['kind'] != 'change' or not case['acquisition']
            or case['acquisition_protocol_sha256'] != PROTOCOL['schedule_sha256']
            or job['batch_protocol_sha256'] != PROTOCOL_SHA256):
        raise ValueError('Unsupported acquisition job/protocol')
    if Path(job['repo']) != Path(__file__).resolve().parents[1]:
        raise ValueError('Acquisition must use the driver checkout')
    if artifacts._id(job['run_id']) != artifacts._id(Path(job['run_path']).name):
        raise ValueError('Acquisition run/path identity mismatch')
    if any(not Path(job[key]).is_absolute() for key in ('repo', 'assets', 'run_path')):
        raise ValueError('Acquisition paths must be absolute')
    return copy.deepcopy(job)


def make_plan(repo, assets, output):
    repo, assets, output = (Path(p).resolve() for p in (repo, assets, output))
    jobs = []
    for regime in PROTOCOL['regimes']:
        for seed in PROTOCOL['seeds']:
            run_id = uuid.uuid4().hex
            jobs.append(validate_job({'repo': str(repo), 'assets': str(assets),
                'run_path': str(output / 'runs' / run_id), 'run_id': run_id,
                'case': memory_experiment.make_world_case(seed, regime, 'development-history', acquisition=True),
                'batch_protocol_sha256': PROTOCOL_SHA256}))
    return {'output': str(output), 'protocol': copy.deepcopy(PROTOCOL),
        'protocol_sha256': PROTOCOL_SHA256, 'source_identity': source_identity(repo), 'jobs': jobs}


def _admit_run(job, identity):
    run = Path(job['run_path'])
    data = artifacts._load(run)  # Exhausts terminal counts and actual chunk checksums.
    manifest = data['manifest']
    driver = {'sha256': identity['driver_sha256'], 'name': Path(__file__).name,
        'access': PROTOCOL['access'], 'uses_u': False,
        'protocol_sha256': job['case']['acquisition_protocol_sha256'],
        'batch_protocol_sha256': PROTOCOL_SHA256}
    expected = {'memory_case': job['case'], 'memory_case_sha256': memory.sha256(job['case']),
        'acquisition_protocol_sha256': PROTOCOL['schedule_sha256'],
        'acquisition_batch_protocol': PROTOCOL, 'acquisition_driver': driver}
    if any(memory.canonical_bytes(manifest.get(k)) != memory.canonical_bytes(v) for k, v in expected.items()):
        raise ValueError('Recorded case/acquisition protocol identity mismatch')
    environments = [e for e in data['events'] if e['kind'] == 'environment']
    if len(environments) != 1 or any(environments[0].get(k) != identity[k]
            for k in ('source_sha256', 'lock_sha256', 'upstream_commit')):
        raise ValueError('Recorded software identity differs from frozen batch source')
    initial = {'m': memory.seed_m(job['case']['facts'], []),
        'e': {'version': 1, 'episodes': []}, 'u': memory.artifact(method='empty-v1')}
    if manifest.get('initial_memory') != {k: memory.sha256(v) for k, v in initial.items()}:
        raise ValueError('Acquisition did not begin with the exact unknown bank and empty E/U')
    if (manifest.get('controller') != 'manual' or manifest.get('requested_device') != 'cpu'
            or manifest.get('recording_max_bytes') != PROTOCOL['recording_max_bytes']
            or manifest.get('seed') != job['case']['seed']
            or set(data['episodes']) != {0} or not 331 <= manifest['recorded_ticks'] <= 600):
        raise ValueError('Recorded acquisition controller/budget/episode mismatch')
    report = artifacts._json(artifacts._read(run / 'acquisition-report.json', 1024**2))
    if report.get('run_path') != job['run_path'] or report.get('status') != 'coverage_observed':
        raise ValueError('Acquisition did not retain complete declared coverage')
    packets = [e['packet'] for e in data['events'] if e['kind'] == 'memory_sensed']
    if [p.get('tick') for p in packets] != list(range(manifest['recorded_ticks'])):
        raise ValueError('Acquisition lacks its consecutive declared sensor packets')
    expected_subjects = set(job['case']['subjects_by_side'])
    observed = {phase: {s['subject_id'] for p in packets for s in p['passages']
        if s['passability'] != 'unobserved' and
        (p['tick'] < 300 if phase == 'before' else p['tick'] >= 300)} for phase in ('before', 'after')}
    if any(subjects != expected_subjects for subjects in observed.values()):
        raise ValueError('Acquisition has missing pre/post passage evidence')
    triggers = [e['detail']['trigger'] for e in data['events']
        if e['kind'] == 'memory_decision' and e['detail']['kind'] == 'memory_trigger']
    if len(triggers) != 1 or triggers[0]['tick'] != 300 or triggers[0]['cue_id'] != job['case']['cue_id']:
        raise ValueError('Acquisition lacks its witnessed scheduled cue change')
    gates = [e['detail'] for e in data['events'] if e['kind'] == 'memory_world_changed'
        and e['detail']['kind'] == 'memory_gate_applied']
    if (report.get('gate_result') != 'closed' or len(gates) != 1 or gates[0]['tick'] != 300
            or gates[0]['subject_id'] != job['case']['closure_subject_id']):
        raise ValueError('Acquisition gate outcome failed or differs from case')
    return {'report_sha256': _hash(run / 'acquisition-report.json'),
        'recorded_ticks': manifest['recorded_ticks'], 'gate_result': report['gate_result']}


def run_batch(plan):
    expected = [(r, s) for r in PROTOCOL['regimes'] for s in PROTOCOL['seeds']]
    jobs = plan['jobs']
    if (memory.canonical_bytes(plan['protocol']) != memory.canonical_bytes(PROTOCOL)
            or plan['protocol_sha256'] != PROTOCOL_SHA256
            or [(j['case']['regime'], j['case']['seed']) for j in jobs] != expected
            or len({j['run_id'] for j in jobs}) != 8
            or any(Path(j['run_path']) != Path(plan['output']) / 'runs' / j['run_id'] for j in jobs)
            or len({(j['repo'], j['assets']) for j in jobs}) != 1):
        raise ValueError('Batch must contain exactly the fixed eight fresh acquisition jobs')
    for job in jobs:
        validate_job(job)
    output = Path(plan['output'])
    output.mkdir(parents=True, exist_ok=False)
    (output / 'runs').mkdir()
    _write(output / 'batch-plan.json', plan)
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path(plan['jobs'][0]['repo']) / 'src')
    env.setdefault('MUJOCO_GL', 'egl')
    env['MPLBACKEND'] = 'Agg'
    env['OMP_NUM_THREADS'] = '2'
    runs = []
    for raw in plan['jobs']:
        job = validate_job(raw)
        print(json.dumps({'stage': 'starting', 'seed': job['case']['seed'],
            'regime': job['case']['regime'], 'run_id': job['run_id']}), flush=True)
        supervised = bounded_process([sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(job)],
            Path(job['run_path']), PROTOCOL['timeout_seconds'], env, log_max_bytes=PROTOCOL['log_max_bytes'])
        result = {'run_id': job['run_id'], 'run_path': job['run_path'],
            'seed': job['case']['seed'], 'regime': job['case']['regime'],
            'status': 'failed', 'supervisor': supervised}
        try:
            if supervised['status'] != 'completed' or supervised.get('returncode') != 0:
                raise ValueError('Acquisition child failed or exceeded its bound')
            result.update(_admit_run(job, plan['source_identity']), status='completed')
        except (OSError, ValueError, KeyError) as error:
            result['error'] = {'type': type(error).__name__, 'message': str(error)}
        runs.append(result)
        _write(output / (job['run_id'] + '-result.json'), result)
    histories = []
    for regime in PROTOCOL['regimes']:
        jobs = [j for j in plan['jobs'] if j['case']['regime'] == regime]
        group = {'regime': regime, 'source_run_ids': [j['run_id'] for j in jobs], 'status': 'rejected'}
        try:
            bundle = collect_history([Path(j['run_path']) for j in jobs])
            path = output / (regime + '-history.json')
            _write(path, bundle)
            gaps = any(link.get('gap') or any(c.get('gap') for c in link['checks']) for link in bundle['links'])
            complete = not gaps and len(bundle['e']['episodes']) == 4 and all(
                r['status'] == 'completed' for r in runs if r['regime'] == regime)
            group.update(status='complete' if complete else 'incomplete',
                report_path=str(path), report_sha256=_hash(path), gaps=gaps,
                episodes=len(bundle['e']['episodes']), history_sha256=bundle['history_sha256'],
                support=bundle['u']['provenance']['support'], rules=bundle['u']['payload']['rules'])
        except (OSError, ValueError, KeyError) as error:
            group['error'] = {'type': type(error).__name__, 'message': str(error)}
        histories.append(group)
    final = source_identity(plan['jobs'][0]['repo'])
    unchanged = final == plan['source_identity']
    result = {'version': 1, 'claim': PROTOCOL['claim'], 'protocol_sha256': PROTOCOL_SHA256,
        'runs': runs, 'histories': histories, 'source_identity': plan['source_identity'],
        'final_source_identity': final, 'source_unchanged': unchanged,
        'status': 'complete' if unchanged and all(h['status'] == 'complete' for h in histories) else 'incomplete',
        'r2_complete': False, 'operator_blindness_verified': False}
    _write(output / 'batch-report.json', result)
    return result


def worker(raw):
    # Simulator import stays inside the exclusively authorized child execution.
    from palimpsest.engine import Engine
    job = validate_job(raw)
    case, run = job['case'], Path(job['run_path'])
    schedule = case['acquisition_schedule']
    before, after, triggers = set(), set(), set()
    engine = None
    started = time.monotonic()
    report = {'run_path': str(run), 'status': 'not_started', 'r2_complete': False,
        'acquisition_access': PROTOCOL['access'], 'operator_blindness_verified': False}
    try:
        engine = Engine.open(job['repo'], job['assets'], run / 'recording', controller='manual',
            scenario='memory-passages', seed=case['seed'], run_id=job['run_id'], device='cpu',
            max_bytes=PROTOCOL['recording_max_bytes'], memory_case=case)
        driver = {'sha256': _hash(Path(__file__)), 'name': Path(__file__).name,
            'access': PROTOCOL['access'], 'uses_u': False, 'protocol_sha256': case['acquisition_protocol_sha256'],
            'batch_protocol_sha256': PROTOCOL_SHA256}
        engine.writer.manifest.update(acquisition_driver=driver, acquisition_batch_protocol=PROTOCOL)
        engine._event('acquisition_driver_declared', detail=driver)
        for tick in range(schedule['max_ticks']):
            if time.monotonic() - started > PROTOCOL['internal_wall_seconds']:
                report['status'] = 'wall_budget_exceeded'
                break
            pose = [*map(float, engine.env._base_xy()), float(engine.env._base_yaw())]
            action = memory_experiment.acquisition_action(schedule, pose, tick)
            for kind, payload in (('set_action', {'action': action}), ('step', None)):
                command = {'id': f'acquire-{tick}-{kind}', 'kind': kind,
                    'expected_state': 'paused', 'expected_episode': 0}
                if payload is not None:
                    command['payload'] = payload
                engine.submit(command)
                state = engine.advance()
            if state['phase'] != 'paused':
                report['status'] = 'runtime_' + state['phase']
                break
            for fact in engine.memory['m']['facts']:
                evidence = fact['evidence']
                if evidence is not None and evidence['episode_id'] == 'episode-0':
                    (before if evidence['tick'] < schedule['reference_tick'] else after).add(fact['subject_id'])
            triggers.update(d['event_id'] for d in engine.memory['last_decisions'] if d['kind'] == 'memory_trigger')
            if tick >= schedule['return_tick'] and len(before) == len(after) == 2:
                report['status'] = 'coverage_observed'
                break
        else:
            report['status'] = 'tick_budget_exhausted'
    except Exception as error:
        report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)})
    finally:
        if engine is not None:
            report.update(steps=engine.episode_step, gate_result=engine.world_task_state['gate_result'],
                outcome=engine.last_outcome, actual_memory={k: copy.deepcopy(engine.memory[k]) for k in ('m', 'e', 'u')})
            try:
                engine.close()
            except Exception as error:
                report.update(status='cleanup_failed', cleanup_error={'type': type(error).__name__, 'message': str(error)})
    report.update(wall_seconds=time.monotonic() - started, before_observed_subjects=sorted(before),
        after_observed_subjects=sorted(after), witnessed_trigger_ids=sorted(triggers))
    if report['status'] == 'coverage_observed' and (len(triggers) != 1 or report.get('gate_result') != 'closed'):
        report['status'] = 'cue_or_gate_failure'
    _write(run / 'acquisition-report.json', report)
    return 0 if report['status'] == 'coverage_observed' else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker')
    parser.add_argument('--repo', type=Path)
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    if args.worker is not None:
        return worker(json.loads(args.worker))
    if any(p is None for p in (args.repo, args.assets, args.output)):
        parser.error('--repo, --assets and --output are required')
    plan = make_plan(args.repo, args.assets, args.output)
    if args.plan_only:
        print(json.dumps(plan, indent=2, allow_nan=False))
        return 0
    result = run_batch(plan)
    print(json.dumps(result, indent=2, allow_nan=False))
    return 0 if result['status'] == 'complete' else 1


if __name__ == '__main__':
    raise SystemExit(main())
