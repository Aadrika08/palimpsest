"""Six fixed development reference owners; preparation until explicit native GO."""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import numpy as np
from palimpsest import artifacts, memory, memory_reference as reference, memory_task, memory_world
from palimpsest.evaluate import bounded_process
from palimpsest.replay import _initial_snapshot, _register_initial
from palimpsest.snapshots import capture, read_snapshot, state_digest
from palimpsest.storage import GiB, MiB, StorageBudget, StorageLimits

REPO = Path(__file__).resolve().parents[1]
HISTORICAL = REPO.parent / 'memory-flynn-continuation'
HISTORICAL_COMMIT = '9393215c7a706810e053b20928aea132b91f495a'
B_ROOT = HISTORICAL / 'runs/m5-counterbalance-stage-b-20261003'
B_PLAN = B_ROOT / 'admission-plan.json'
B_REPORT = B_ROOT / 'admission-report.json'
B_PLAN_SHA256 = 'ecaedc5c9341063eaa619635da69bda2149dd66e46ed1d01a7ffe13834515131'
B_REPORT_SHA256 = '2eaba8d84f4d206c0f415362088ba7cec3139b77e10829b6cdc84b055624ea1f'
HELPER = REPO / 'scripts/verify_flynn_memory_transfer.py'
spec = importlib.util.spec_from_file_location('reference_owner_helpers', HELPER)
neural = importlib.util.module_from_spec(spec)
spec.loader.exec_module(neural)
common = neural.common
CELLS = ((24, 'local_cue', 'change'), (25, 'local_cue', 'change'))
MODES = tuple(reference.REFERENCES)
PROTOCOL = {'version': 1, 'claim': 'six-fixed-development-controller-references',
    'cells': [list(c) for c in CELLS], 'modes': list(MODES), 'owners': 6,
    'reference_protocol_sha256': reference.PROTOCOL_SHA256,
    'historical_plan_sha256': B_PLAN_SHA256, 'historical_report_sha256': B_REPORT_SHA256,
    'historical_reader_commit': HISTORICAL_COMMIT, 'remaining_intervals': 300,
    'maximum_numeric_ticks': 1800, 'timeout_seconds': 160, 'internal_wall_seconds': 150,
    'outer_timeout_seconds': 1020, 'recording_max_bytes': 192*MiB, 'snapshot_max_bytes': 16*MiB,
    'aggregate_max_bytes': 2*GiB, 'min_free_bytes': 2*GiB, 'headroom_bytes': 64*MiB,
    'log_max_bytes': MiB, 'retries': 0, 'held_out': False,
    'helper_sha256': common._hash(HELPER),
    'memory': 'frozen-unused-audit-state', 'resource_reference': neural.PROTOCOL['resource_reference']}
PROTOCOL_SHA256 = memory.sha256(PROTOCOL)

# Run solely with the historical PYTHONPATH; it never imports the current Engine.
READER_CODE = '''import importlib.util,json,sys
from pathlib import Path
root=Path(sys.argv[1])
spec=importlib.util.spec_from_file_location("frozen_reference_provenance",root/"scripts/verify_memory_counterbalance_comparison.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
plan=root/"runs/m5-counterbalance-stage-b-20261003/admission-plan.json"
report=root/"runs/m5-counterbalance-stage-b-20261003/admission-report.json"
a=m.load_bindings(plan,report);b=m.load_bindings(plan,report,protocol_sha256=m.C4_PROTOCOL_SHA256)
bindings={"s24/local_cue/change":a["s24/local_cue/change"],"s25/local_cue/change":b["s25/local_cue/change"]}
if any(k in sys.modules for k in ("torch","mujoco","palimpsest.engine")):raise ValueError("Historical reader imported native/model code")
print(json.dumps(bindings,allow_nan=False,sort_keys=True))
'''


def key(cell):
    return f's{cell[0]}/{cell[1]}/{cell[2]}'


def historical_identity():
    """Pin actual transitive reader files against their unchanged historical commit."""
    def git(*args):
        return subprocess.run(['git', '-C', str(HISTORICAL), *args], check=True,
            capture_output=True, timeout=10).stdout
    if git('rev-parse', 'HEAD').decode().strip() != HISTORICAL_COMMIT or git('status', '--porcelain'):
        raise ValueError('Historical reader checkout changed')
    if common._hash(B_PLAN) != B_PLAN_SHA256 or common._hash(B_REPORT) != B_REPORT_SHA256:
        raise ValueError('Fixed historical B plan/report changed')
    files = git('ls-files', '-z').decode().rstrip('\0').split('\0')
    files = [p for p in files if p.startswith(('src/palimpsest/', 'scripts/')) and p.endswith('.py')]
    import hashlib
    hashes = {}
    for name in files:
        expected = hashlib.sha256(git('show', f'{HISTORICAL_COMMIT}:{name}')).hexdigest()
        if common._hash(HISTORICAL/name) != expected:
            raise ValueError('Historical transitive reader source differs from commit')
        hashes[name] = expected
    return {'repo': str(HISTORICAL), 'commit': HISTORICAL_COMMIT, 'files_sha256': hashes,
        'plan_sha256': common._hash(B_PLAN), 'report_sha256': common._hash(B_REPORT),
        'reader_code_sha256': hashlib.sha256(READER_CODE.encode()).hexdigest()}


def prepare_bindings(output):
    before = historical_identity()
    env = {**os.environ, 'PYTHONPATH': str(HISTORICAL/'src'), 'OMP_NUM_THREADS': '2'}
    supervised = bounded_process([sys.executable, '-c', READER_CODE, str(HISTORICAL)], output, 40,
        env, log_max_bytes=MiB)
    after = historical_identity()
    if supervised['status'] != 'completed' or supervised.get('returncode') != 0 or before != after:
        raise ValueError('Bounded historical provenance reader failed or changed')
    bindings = artifacts._json(artifacts._read(Path(output)/'stdout.log', MiB))
    result = {'version': 1, 'reader_identity': before, 'bindings': bindings}
    validate_bindings(result)
    common._write(Path(output)/'bindings.json', result)
    return result


def validate_bindings(value):
    memory._fields(value, 'version reader_identity bindings')
    memory._bounded(value, MiB)
    if type(value['version']) is not int or value['version'] != 1 or set(value['bindings']) != {key(c) for c in CELLS}:
        raise ValueError('Reference binding cells differ')
    identity = value['reader_identity']
    if identity != historical_identity():
        raise ValueError('Historical reader identity differs')
    for cell in CELLS:
        binding = value['bindings'][key(cell)]
        if (binding['cell'] != list(cell) or binding['plan_path'] != str(B_PLAN)
                or binding['report_path'] != str(B_REPORT)
                or binding['plan_sha256'] != identity['plan_sha256'] or binding['report_sha256'] != identity['report_sha256']
                or Path(binding['snapshot_path']) != B_ROOT/'runs'/binding['run_id']/'snapshots/initial.snp'):
            raise ValueError('Historical source/binding paths differ')
        paths = [pin['path'] for pin in binding['pins']]
        if len(paths) != len(set(paths)) or not paths:
            raise ValueError('Duplicate or empty historical input pins')
        for pin in binding['pins']:
            if common._hash(artifacts._safe_path(pin['path'])) != pin['sha256']:
                raise ValueError('Historical source artifact changed')
        original = read_snapshot(binding['snapshot_path'])
        if (common._hash(binding['snapshot_path']) != binding['snapshot_sha256']
                or common.baseline_invariants(original) != binding['non_u']
                or original['application']['world_task_state']['case'] != binding['case']):
            raise ValueError('Bound original native source differs')
        reference.validate_source(original, MODES[0], 'flynn', 'cpu', False, None)
    return copy.deepcopy(value)


def source_identity(assets):
    result = neural.source_identity(REPO, assets)
    result['reference_driver_sha256'] = common._hash(Path(__file__))
    return result


def budget(output):
    return StorageBudget((Path(output),), StorageLimits(max_bytes=2*GiB, min_free_bytes=2*GiB,
        max_runs=6, max_snapshots=1), headroom_bytes=64*MiB)


def validate_job(job):
    memory._fields(job, 'repo assets root_output output run_id cell stage protocol_sha256 source_identity bindings_path bindings_sha256 binding')
    memory._bounded(job, 128*1024)
    artifacts._id(job['run_id'])
    if (job['repo'] != str(REPO) or tuple(job['cell']) not in CELLS or job['stage'] not in MODES
            or job['protocol_sha256'] != PROTOCOL_SHA256 or any(not Path(job[k]).is_absolute()
                for k in ('repo', 'assets', 'root_output', 'output', 'bindings_path'))
            or Path(job['output']) != Path(job['root_output'])/'runs'/job['run_id']):
        raise ValueError('Fixed reference owner/path/protocol differs')
    memory._digest(job['bindings_sha256'])
    raw = neural.read_prepared_plan(job['bindings_path'], job['bindings_sha256'])
    if memory.canonical_bytes(job['binding']) != memory.canonical_bytes(raw['bindings'][key(job['cell'])]):
        raise ValueError('Owner substituted a prepared binding')
    return copy.deepcopy(job)


def make_plan(assets, output, bindings_path, digest):
    assets, output, bindings_path = map(lambda p: artifacts._safe_path(Path(p).resolve()), (assets, output, bindings_path))
    binding_data = validate_bindings(neural.read_prepared_plan(bindings_path, digest))
    identity = source_identity(assets)
    jobs = []
    for cell in CELLS:
        for mode in MODES:
            run_id = uuid.uuid4().hex
            jobs.append(validate_job({'repo': str(REPO), 'assets': str(assets), 'root_output': str(output),
                'output': str(output/'runs'/run_id), 'run_id': run_id, 'cell': list(cell), 'stage': mode,
                'protocol_sha256': PROTOCOL_SHA256, 'source_identity': identity,
                'bindings_path': str(bindings_path), 'bindings_sha256': digest,
                'binding': binding_data['bindings'][key(cell)]}))
    return {'protocol': PROTOCOL, 'protocol_sha256': PROTOCOL_SHA256, 'output': str(output),
        'source_identity': identity, 'reader_identity': binding_data['reader_identity'], 'jobs': jobs}


def validate_plan(plan):
    memory._fields(plan, 'protocol protocol_sha256 output source_identity reader_identity jobs')
    memory._bounded(plan, MiB)
    if (memory.canonical_bytes(plan['protocol']) != memory.canonical_bytes(PROTOCOL)
            or plan['protocol_sha256'] != PROTOCOL_SHA256 or len(plan['jobs']) != 6
            or [(j['cell'], j['stage']) for j in plan['jobs']] != [(list(c), m) for c in CELLS for m in MODES]
            or len({j['run_id'] for j in plan['jobs']}) != 6):
        raise ValueError('Fixed six-owner plan differs')
    for job in plan['jobs']:
        validate_job(job)
        if (job['source_identity'] != plan['source_identity'] or job['root_output'] != plan['output']
                or any(job[k] != plan['jobs'][0][k] for k in ('repo', 'assets', 'bindings_path', 'bindings_sha256'))):
            raise ValueError('Owner source/output identity differs')
    return copy.deepcopy(plan)


def reference_step(engine, tick):
    command = {'id': f'reference-{tick}', 'kind': 'step', 'expected_state': 'paused', 'expected_episode': 0}
    if engine.submit(command)['status'] != 'queued':
        raise ValueError('Reference step was not queued')
    return engine.advance()


def task_failure(report):
    outcome = report.get('outcome') or {}
    return (report.get('mode') == 'memory-reference-sensor-only' and report.get('final_phase') == 'failed'
        and outcome.get('type') == 'CueUnavailable'
        and outcome.get('message') == 'Sensor-only reference common goal is not visible')


def audit_original(engine):
    """Existing policy sampler pattern; preserve typed upstream input, log JSON scalars."""
    act = engine.policy.act
    def traced(observation):
        sensors = observation['sensors']
        wind = sensors['wind_direction']
        if (set(observation) != {'cam_left', 'cam_right', 'sensors'}
                or set(sensors) != {'collision', 'collision_angle', 'wind_direction'}
                or type(sensors['collision']) is not bool or not isinstance(wind, np.ndarray)
                or wind.dtype != np.float32 or wind.shape != (2,)):
            raise ValueError('Original reference upstream policy input differs')
        result = act(observation)
        serialized = {'collision': sensors['collision'], 'collision_angle': sensors['collision_angle'],
                      'wind_direction': list(map(float, wind))}
        engine._event('neural_policy_call', observation_sha256=state_digest(observation),
            cameras_sha256={k: state_digest(observation[k]) for k in ('cam_left', 'cam_right')},
            sensors=serialized, wind_container='numpy.float32[2]',
            result_sha256={k: state_digest(result[k]) for k in ('action', 'encoded_input', 'raw_output')})
        return result
    engine.policy.act = traced


def worker(raw):
    from palimpsest.engine import Engine
    if Path(sys.modules[Engine.__module__].__file__).resolve() != REPO/'src/palimpsest/engine.py':
        raise ValueError('Executor imported a historical or foreign Engine')
    job = validate_job(raw)
    bindings = validate_bindings(neural.read_prepared_plan(job['bindings_path'], job['bindings_sha256']))
    if job['binding'] != bindings['bindings'][key(job['cell'])] or source_identity(job['assets']) != job['source_identity']:
        raise ValueError('Executor source/binding changed')
    binding, mode, run = job['binding'], job['stage'], Path(job['output'])
    original = read_snapshot(binding['snapshot_path'])
    controller = reference.REFERENCES[mode][0]
    storage = budget(job['root_output']); storage.check(208*MiB, path=run)
    engine = None; started = time.monotonic()
    report = {'status': 'failed', 'mode': mode, 'run_path': str(run), 'task_pass': None}
    try:
        engine = Engine.open(REPO, job['assets'], run/'recording', run_id=job['run_id'],
            controller=controller, device='cpu', scenario=mode, seed=binding['case']['seed'],
            memory_case=binding['case'], restore_snapshot=original, replace_controller=controller != 'flynn',
            max_bytes=192*MiB, storage_budget=storage)
        engine.writer.manifest.update(reference_verifier_protocol=PROTOCOL, reference_verifier_protocol_sha256=PROTOCOL_SHA256,
            reference_verifier_job_sha256=memory.sha256(job), reference_source_identity=job['source_identity'],
            reference_historical_reader=bindings['reader_identity'], reference_binding=binding)
        current = capture(engine.env, engine.observation, policy=engine.policy, teacher=engine.teacher,
            application=engine.application_state())
        expected = reference.preservation_hash(original, controller != 'flynn')
        if reference.preservation_hash(current, controller != 'flynn') != expected:
            raise ValueError('Reference transaction failed original-source invariants')
        _register_initial(engine, run, storage)
        if (run/'snapshots/initial.snp').stat().st_size > 16*MiB:
            raise ValueError('Registered initial reference SNP exceeds 16 MiB before first tick')
        report.update(snapshot_sha256=common._hash(run/'snapshots/initial.snp'), preserved_sha256=expected)
        if controller == 'flynn': audit_original(engine)
        elif controller == 'teacher':
            act = engine.teacher.act
            def traced(env):
                action = act(env)
                engine._event('reference_teacher_call', action_sha256=state_digest(np.asarray(action, dtype=np.float32)),
                    retained_control_sha256=reference.teacher_control_hash(engine.teacher))
                return action
            engine.teacher.act = traced
        for _ in range(PROTOCOL['remaining_intervals']):
            if time.monotonic()-started > 150: raise TimeoutError('Reference internal wall limit')
            state = reference_step(engine, engine.episode_step)
            if state['phase'] != 'paused': break
        report['status'] = 'recorded'
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        if engine is not None:
            report.update(final_phase=engine.phase, outcome=engine.last_outcome, steps=engine.episode_step,
                final_memory=copy.deepcopy(engine.memory), final_world=copy.deepcopy(engine.world_task_state))
            try: engine.close()
            except Exception as error:
                report.update(status='cleanup_failed', cleanup_error={'type': type(error).__name__, 'message': str(error)})
    report['wall_seconds'] = time.monotonic()-started
    if report['wall_seconds'] > 150:
        report.update(status='deadline_failed', finalization_error={'type': 'TimeoutError',
            'message': 'Reference step/cleanup/report elapsed exceeds 150 seconds'})
    neural.write(run/'reference-worker.json', report, storage)
    return 0 if report['status'] == 'recorded' and (report.get('final_phase') != 'failed' or task_failure(report)) else 1


def input_bindings(data, mode):
    rows, events = data['rows'], data['events']
    inputs = [e for e in events if e['kind'] == 'memory_reference_input']
    packets = [e for e in events if e['kind'] == 'memory_reference_sensed']
    expected = [r['tick'] for r in rows]
    # A missing-goal failure has one actual packet but no motor input or numeric row.
    if [e['episode_step'] for e in inputs] != expected or [e['episode_step'] for e in packets[:len(rows)]] != expected:
        raise ValueError('Reference input/packet/row linkage differs')
    calls = [e for e in events if e['kind'] == ('neural_policy_call' if mode == MODES[0] else 'reference_teacher_call')]
    if mode != MODES[1] and [e['episode_step'] for e in calls] != expected:
        raise ValueError('Reference actual call/row linkage differs')
    for i, (row, event) in enumerate(zip(rows, inputs)):
        if any((e.get('episode'), e.get('tick'), e.get('episode_step')) != (0, row['tick'], row['tick'])
                for e in (event, packets[i])):
            raise ValueError('Reference outer event episode/tick differs')
        if mode == MODES[1]:
            actual = reference.sensor_input(packets[i]['packet'], bool(row['sensors'][0]))
            if (row['action'].dtype != np.float64 or actual != event['inputs']
                    or not np.array_equal(row['action'], np.asarray(reference.sensor_action(actual), np.float64))):
                raise ValueError('Sensor-only actual input/action differs')
        elif mode == MODES[0]:
            call = calls[i]; sensors = call['sensors']; actual = event['inputs']
            typed = {**sensors, 'wind_direction': np.asarray(sensors['wind_direction'], np.float32)}
            projected = np.asarray([float(sensors['collision']), 0. if sensors['collision_angle'] is None else float(sensors['collision_angle']),
                *sensors['wind_direction']], np.float32)
            if (any((call.get(k) != v) for k,v in (('episode', 0), ('tick', row['tick'])))
                    or any(row[k].dtype != np.float32 or row[k].shape != shape or not np.isfinite(row[k]).all()
                        for k,shape in (('action', (2,)), ('encoded_input', (4813,)), ('raw_output', (2,))))
                    or actual != sensors or call.get('wind_container') != 'numpy.float32[2]' or not np.array_equal(row['sensors'], projected)
                    or call['result_sha256'] != {k: state_digest(row[k]) for k in ('action', 'encoded_input', 'raw_output')}
                    or call['cameras_sha256'] != {k: state_digest(row[k]) for k in ('cam_left', 'cam_right')}
                    or call['observation_sha256'] != state_digest({'cam_left': row['cam_left'], 'cam_right': row['cam_right'], 'sensors': typed})):
                raise ValueError('Original checkpoint actual upstream input/output differs')
        elif (calls[i].get('episode') != 0 or calls[i].get('tick') != row['tick']
                or calls[i]['action_sha256'] != state_digest(row['action'])):
            raise ValueError('Teacher actual output/row differs')


def validate_stage(job, supervised):
    if supervised['status'] != 'completed' or supervised.get('returncode') != 0:
        raise ValueError('Reference infrastructure/owner failure; no retry')
    data = common.read_run(Path(job['output']))
    report = artifacts._json(artifacts._read(data['run']/'reference-worker.json', MiB))
    native, entry, _ = _initial_snapshot(data)
    controller = reference.REFERENCES[job['stage']][0]
    original = read_snapshot(job['binding']['snapshot_path'])
    expected = reference.preservation_hash(original, controller != 'flynn')
    manifest, events, rows = data['manifest'], data['events'], data['rows']
    if (manifest.get('run_id') != job['run_id'] or manifest.get('controller') != controller
            or manifest.get('scenario', {}).get('id') != job['stage'] or manifest.get('requested_device') != 'cpu'
            or manifest.get('recording_max_bytes') != 192*MiB or manifest.get('close_reason') != 'operator_closed'
            or manifest.get('reference_verifier_job_sha256') != memory.sha256(job)
            or manifest.get('reference_verifier_protocol_sha256') != PROTOCOL_SHA256
            or manifest.get('reference_verifier_protocol') != PROTOCOL
            or manifest.get('reference_source_identity') != job['source_identity']
            or manifest.get('reference_binding') != job['binding']
            or report.get('status') != 'recorded' or report.get('mode') != job['stage'] or report.get('run_path') != job['output']
            or type(report.get('wall_seconds')) not in (int, float) or not 0 <= report['wall_seconds'] <= 150
            or 'cleanup_error' in report or report.get('snapshot_sha256') != entry['sha256']
            or report.get('preserved_sha256') != expected or reference.preservation_hash(native, controller != 'flynn') != expected
            or native['application']['scenario'] != job['stage'] or native['application']['controller'] != controller
            or native['application']['revision'] != original['application']['revision']+1
            or report['final_memory'] != original['application']['memory'] or native['application']['memory'] != original['application']['memory']
            or report.get('steps') != 300+len(rows) or manifest.get('total_tick') != report['steps']
            or report.get('final_phase') != manifest.get('final_phase') or report.get('outcome') != manifest.get('last_outcome')
            or len(rows) > 300 or [r['tick'] for r in rows] != list(range(300, 300+len(rows)))
            or (data['run']/'snapshots/initial.snp').stat().st_size > 16*MiB):
        raise ValueError('Reference source/native/terminal/cleanup/quota identity differs')
    environments = [e for e in events if e['kind'] == 'environment']
    if len(environments) != 1 or any(environments[0].get(k) != job['source_identity'][k]
            for k in ('source_sha256', 'lock_sha256', 'upstream_commit')):
        raise ValueError('Reference recorded executor identity differs')
    if any(e['kind'] in ('memory_sensed', 'memory_decision', 'memory_cue', 'memory_inspected', 'selector_configured') for e in events):
        raise ValueError('Reference invoked memory guidance')
    final_world = memory_world.validate_state(report['final_world'])
    applied = [e for e in events if e['kind'] == 'memory_world_changed'
               and e['detail']['kind'] == 'memory_gate_applied']
    if (final_world['case'] != job['binding']['case'] or final_world['gate_result'] != 'closed'
            or len(applied) != 1 or (applied[0]['episode'], applied[0]['tick'], applied[0]['episode_step']) != (0,300,300)):
        raise ValueError('Reference original gate/case schedule did not apply exactly')
    commands = [e['command'] for e in events if e['kind'] == 'command_received']
    if any(c['kind'] != 'step' for c in commands): raise ValueError('Reference received undeclared control')
    failures = [e for e in events if e['kind'] == 'runtime_failure']
    packets = [e for e in events if e['kind'] == 'memory_reference_sensed']
    if report['final_phase'] == 'failed':
        if (not task_failure(report) or manifest['status'] != 'failed' or len(failures) != 1
                or failures[0]['episode_step'] != report['steps'] or len(packets) != len(rows)+1):
            raise ValueError('Unsupported reference failure boundary')
        with_goal = [l for l in packets[-1]['packet']['landmarks'] if l['id'] == packets[-1]['packet']['common_goal_id']]
        if with_goal: raise ValueError('Missing-goal outcome had a visible goal')
    elif manifest['status'] != 'completed' or failures or len(packets) != len(rows):
        raise ValueError('Reference terminal recording differs')
    input_bindings(data, job['stage'])
    return data, report, native, entry


def run_verifier(raw):
    plan = validate_plan(raw); output = Path(plan['output']); first = plan['jobs'][0]
    validate_bindings(neural.read_prepared_plan(first['bindings_path'], first['bindings_sha256']))
    if source_identity(first['assets']) != plan['source_identity'] or output.exists():
        raise ValueError('Changed source or nonfresh reference output')
    existing = output.parent
    while not existing.exists(): existing = existing.parent
    if shutil.disk_usage(existing).free < 4*GiB+64*MiB: raise ValueError('Reference storage preflight failed')
    storage = budget(output); summaries = []; retained = []; started = time.monotonic()
    result = {'version': 1, 'status': 'reference_unverified', 'protocol_sha256': PROTOCOL_SHA256,
        'source_identity': plan['source_identity'], 'reader_identity': plan['reader_identity'], 'runs': summaries,
        'r2_complete': False, 'held_out_executed': False}
    env = {**os.environ, 'PYTHONPATH': str(REPO/'src'), 'MUJOCO_GL': 'egl', 'MPLBACKEND': 'Agg', 'OMP_NUM_THREADS': '2'}
    with storage.lock():
        (output/'runs').mkdir(); storage.check_count('runs', 0, 6)
        neural.write(output/'reference-plan.json', plan, storage)
        current = summary = None
        try:
            for job in plan['jobs']:
                current, summary = job, None
                if time.monotonic()-started > 1020-160: raise TimeoutError('No wall budget for next reference')
                validate_job(job)
                neural.write(output/f"{job['run_id']}-job.json", job, storage)
                print(json.dumps({'cell': key(job['cell']), 'mode': job['stage'], 'run_id': job['run_id']}), flush=True)
                supervised = bounded_process([sys.executable, str(Path(__file__)), '--worker', json.dumps(job)],
                    Path(job['output']), 160, env, log_max_bytes=MiB, storage_budget=storage)
                summary = {'cell': key(job['cell']), 'mode': job['stage'], 'run_id': job['run_id'], 'supervisor': supervised}
                summaries.append(summary)
                data, report, native, entry = validate_stage(job, supervised)
                retained.append(data)
                navigation = report['final_phase'] == 'terminated' and (report['outcome'] or {}).get('reason') == 'goal'
                summary.update(admission_pass=True, navigation_pass=navigation, memory_revision_pass=None, task_pass=None,
                    final_phase=report['final_phase'], outcome=report['outcome'], intervals=len(data['rows']),
                    gate_result=report['final_world']['gate_result'],
                    before_occupancy=common.occupancy(job['binding']['case'], job['binding']['before_circles']),
                    after_occupancy=common.occupancy(job['binding']['case'],
                        artifacts._world_at(data['events'], 0, 300)['obstacles']),
                    goal_tick=report['steps'] if navigation else None, censored=report['final_phase'] == 'paused',
                    snapshot_sha256=entry['sha256'], worker_sha256=common._hash(data['run']/'reference-worker.json'),
                    files=[{'path': str(p.relative_to(data['run'])), 'bytes': p.stat().st_size, 'sha256': common._hash(p)} for p in data['paths']])
            result['status'] = 'reference_checked'
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, TimeoutError) as error:
            result['first_failure'] = {'type': type(error).__name__, 'message': str(error),
                'run_id': None if current is None else current['run_id'], 'scope': 'before-owner' if summary is None else 'attempted-owner'}
            if summary is not None: summary.update(admission_pass=False, failure=result['first_failure'])
        result['unattempted'] = [{'run_id': j['run_id'], 'cell': key(j['cell']), 'mode': j['stage']} for j in plan['jobs'][len(summaries):]]
        try:
            result['final_source_identity'] = source_identity(first['assets'])
            validate_bindings(neural.read_prepared_plan(first['bindings_path'], first['bindings_sha256']))
            result['source_unchanged'] = result['final_source_identity'] == plan['source_identity']
            result['retained_unchanged'] = all(artifacts._fingerprint(d['paths']) == d['fingerprint'] for d in retained)
        except Exception as error:
            result.update(source_unchanged=False, retained_unchanged=False, after_error={'type': type(error).__name__, 'message': str(error)})
        result['wall_seconds'] = time.monotonic()-started
        if result['wall_seconds'] > 1020:
            result.update(status='reference_unverified', aggregate_deadline_error={'type': 'TimeoutError',
                'message': 'Reference owners/final source rechecks exceeded 1020 seconds'})
        neural.write(output/'reference-report.json', result, storage)
    return 0 if result['status'] == 'reference_checked' and result['source_unchanged'] and result['retained_unchanged'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--read-bindings', type=Path)
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--assets', type=Path); parser.add_argument('--output', type=Path)
    parser.add_argument('--bindings', type=Path); parser.add_argument('--bindings-sha256')
    parser.add_argument('--worker'); parser.add_argument('--prepared-plan', type=Path); parser.add_argument('--prepared-plan-sha256')
    args = parser.parse_args()
    if args.worker is not None: return worker(json.loads(args.worker))
    if args.read_bindings is not None: prepare_bindings(args.read_bindings); return 0
    if args.prepared_plan is not None: return run_verifier(neural.read_prepared_plan(args.prepared_plan, args.prepared_plan_sha256))
    if not args.plan_only or any(v is None for v in (args.assets, args.output, args.bindings, args.bindings_sha256)):
        parser.error('Only fixed binding preparation, hash-bound plan-only, worker or frozen prepared plan is supported')
    print(json.dumps(make_plan(args.assets, args.output, args.bindings, args.bindings_sha256), indent=2, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
