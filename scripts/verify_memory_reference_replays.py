"""Six fixed s24 reference executable replays; preparation requires a later GO."""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

from palimpsest import artifacts, memory, memory_reference as reference
from palimpsest.evaluate import bounded_process
from palimpsest.records import iter_ticks
from palimpsest.replay import _compatible, _initial_snapshot, _same_tick, replay_run
from palimpsest.snapshots import read_snapshot, state_digest
from palimpsest.storage import GiB, MiB, StorageBudget, StorageLimits

REPO = Path(__file__).resolve().parents[1]
PRODUCER = REPO.parent/'memory-controller-references'
SOURCE_ROOT = PRODUCER/'runs/m5-controller-references-20261003'
SOURCE_REPORT = SOURCE_ROOT/'reference-report.json'
SOURCE_REPORT_SHA256 = '982c287ea591f3906b0218a0e52263fd38b75aa35148500b6078bd4d728ccb05'
PRODUCER_COMMIT = '169e0c8ac75be713d9cda0bdd852b926ec1261cc'
SOURCES = (
    ('memory-reference-original-flynn', 'f1cefefc5e994f41a35ada0e8a5c2b18', 129,
     '50836512b963bed188a17d133367893d9f589204d9beec33d59f32b3ca87cd0b'),
    ('memory-reference-sensor-only', '54608f3879704eb4aa6eb794af4a0a48', 124,
     'e182973a62bead2034e1023b6010fefba9f7f1d5b798c716a11ec27fbf64d420'),
    ('memory-reference-teacher', 'cc6b99347a864452b158a21437a3a029', 118,
     '0e1dca845f5747ad1596ca6b071c9bc8a151002b5412553c81b8e07957171be1'))
MODES = ('actions', 'policy')
HELPER = REPO/'scripts/verify_memory_references.py'
spec = importlib.util.spec_from_file_location('reference_replay_helpers', HELPER)
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)
common, neural = helpers.common, helpers.neural
PROTOCOL = {'version': 1, 'claim': 'six-fixed-s24-reference-executable-replays',
    'producer_commit': PRODUCER_COMMIT, 'source_report_sha256': SOURCE_REPORT_SHA256,
    'sources': [list(s) for s in SOURCES], 'modes': list(MODES), 'owners': 6,
    'maximum_numeric_ticks': 742, 'initial_tick': 300,
    'reference_protocol_sha256': reference.PROTOCOL_SHA256,
    'timeout_seconds': 160, 'internal_wall_seconds': 150, 'outer_timeout_seconds': 1020,
    'recording_max_bytes': 192*MiB, 'snapshot_max_bytes_at_ready': 16*MiB,
    'aggregate_max_bytes': 2*GiB, 'min_free_bytes': 2*GiB, 'headroom_bytes': 64*MiB,
    'log_max_bytes': MiB, 'helper_sha256': common._hash(HELPER),
    'float_atol': 1e-6, 'float_rtol': 1e-6, 'retries': 0, 'held_out': False}
PROTOCOL_SHA256 = memory.sha256(PROTOCOL)


def normalized_snapshot(native):
    """Retain every state field except the three explicit replay recorder fields."""
    value = copy.deepcopy(native)
    for key in ('source_run_id', 'event_prefix', 'execution_mode'):
        value['application'].pop(key)
    return state_digest(value)


def source_identity(assets):
    value = neural.source_identity(REPO, assets)
    value['reference_replay_driver_sha256'] = common._hash(Path(__file__))
    value['reference_helper_sha256'] = common._hash(HELPER)
    return value


def source_evidence(assets):
    report = neural.read_prepared_plan(SOURCE_REPORT, SOURCE_REPORT_SHA256)
    if (report['status'] != 'reference_checked' or not report['source_unchanged']
            or not report['retained_unchanged'] or report['unattempted']):
        raise ValueError('Original reference gate is not authoritative and complete')
    identity = source_identity(assets)
    if (identity['asset_sha256'] != report['source_identity']['asset_sha256']
            or identity['upstream_files_sha256'] != report['source_identity']['upstream_files_sha256']):
        raise ValueError('Actual upstream/assets differ from the reference producer')
    results = []
    for mode, identifier, count, digest in SOURCES:
        matches = [r for r in report['runs'] if r['cell'] == 's24/local_cue/change' and r['mode'] == mode]
        if len(matches) != 1:
            raise ValueError('Reference source join is not unique')
        original = matches[0]
        run = SOURCE_ROOT/'runs'/identifier
        data = artifacts._load(run)
        native, entry, _ = _initial_snapshot(data)
        manifest = data['manifest']
        if (original['run_id'] != identifier or original['intervals'] != count
                or not original['admission_pass'] or not original['navigation_pass']
                or original['snapshot_sha256'] != digest or entry['sha256'] != digest
                or manifest['recorded_ticks'] != count or manifest['total_tick'] != 300+count
                or manifest['final_phase'] != 'terminated' or manifest['last_outcome']['reason'] != 'goal'
                or manifest['controller'] != reference.REFERENCES[mode][0]
                or manifest['scenario']['id'] != mode or manifest['requested_device'] != 'cpu'
                or manifest['memory_reference_admission']['protocol_sha256'] != reference.PROTOCOL_SHA256
                or common._hash(run/'reference-worker.json') != original['worker_sha256']):
            raise ValueError('Fixed source recording/native/mode identity differs')
        paths = [*data['paths'], run/'snapshots/initial.snp', run/'snapshots/index.json', run/'reference-worker.json']
        expected = {str(run/f['path']): f for f in original['files']}
        if set(expected) != {str(p) for p in data['paths']}:
            raise ValueError('Source recording index coverage differs')
        for path in data['paths']:
            pin = expected[str(path)]
            if path.stat().st_size != pin['bytes'] or common._hash(path) != pin['sha256']:
                raise ValueError('Source file differs from the producer report')
        current = copy.deepcopy(data['events'])
        env = next(e for e in current if e['kind'] == 'environment')
        for key in ('source_sha256', 'lock_sha256', 'upstream_commit'):
            env[key] = identity[key]
        _compatible(data['events'], current, manifest['controller'], mode)
        reference.validate_source(native, mode, manifest['controller'], 'cpu', False, None)
        helpers.input_bindings(common.read_run(run), mode)
        results.append({'mode': mode, 'run_id': identifier, 'path': str(run), 'ticks': count,
            'snapshot_id': entry['snapshot_id'], 'snapshot_sha256': digest,
            'snapshot_state_sha256': state_digest(native), 'native_sha256': native['native_sha256'],
            'initial_guard_sha256': normalized_snapshot(native), 'case': manifest['memory_case'],
            'files': [{'path': str(p), 'bytes': p.stat().st_size, 'sha256': common._hash(p)} for p in paths]})
    return results


def budget(output):
    return StorageBudget((Path(output),), StorageLimits(max_bytes=2*GiB, min_free_bytes=2*GiB,
        max_runs=6, max_snapshots=1), headroom_bytes=64*MiB)


def validate_job(job):
    memory._fields(job, 'repo assets root_output output run_id stage reference_mode protocol_sha256 source_identity source')
    memory._bounded(job, 128*1024)
    artifacts._id(job['run_id'])
    expected = next((s for s in SOURCES if s[0] == job['reference_mode']), None)
    source = job['source']
    if (job['repo'] != str(REPO) or job['stage'] not in MODES or expected is None
            or job['protocol_sha256'] != PROTOCOL_SHA256
            or any(not Path(job[k]).is_absolute() for k in ('assets', 'root_output', 'output'))
            or Path(job['output']) != Path(job['root_output'])/'runs'/job['run_id']
            or source['mode'] != expected[0] or source['run_id'] != expected[1]
            or source['ticks'] != expected[2] or source['snapshot_sha256'] != expected[3]
            or source['path'] != str(SOURCE_ROOT/'runs'/expected[1])):
        raise ValueError('Fixed reference replay job/path/source differs')
    return copy.deepcopy(job)


def make_plan(assets, output):
    assets, output = map(lambda p: artifacts._safe_path(Path(p).resolve()), (assets, output))
    identity, sources = source_identity(assets), source_evidence(assets)
    jobs = []
    for source in sources:
        for mode in MODES:
            identifier = uuid.uuid4().hex
            jobs.append(validate_job({'repo': str(REPO), 'assets': str(assets), 'root_output': str(output),
                'output': str(output/'runs'/identifier), 'run_id': identifier, 'stage': mode,
                'reference_mode': source['mode'], 'protocol_sha256': PROTOCOL_SHA256,
                'source_identity': identity, 'source': source}))
    return {'protocol': PROTOCOL, 'protocol_sha256': PROTOCOL_SHA256, 'output': str(output),
        'source_identity': identity, 'sources': sources, 'jobs': jobs}


def validate_plan(plan):
    memory._fields(plan, 'protocol protocol_sha256 output source_identity sources jobs')
    memory._bounded(plan, MiB)
    if (memory.canonical_bytes(plan['protocol']) != memory.canonical_bytes(PROTOCOL)
            or plan['protocol_sha256'] != PROTOCOL_SHA256 or len(plan['jobs']) != 6
            or [(j['reference_mode'], j['stage']) for j in plan['jobs']] != [(s[0], m) for s in SOURCES for m in MODES]
            or len({j['run_id'] for j in plan['jobs']}) != 6 or len(plan['sources']) != 3):
        raise ValueError('Fixed six-reference replay plan differs')
    for job in plan['jobs']:
        validate_job(job)
        if (job['source_identity'] != plan['source_identity'] or job['root_output'] != plan['output']
                or job['assets'] != plan['jobs'][0]['assets']
                or plan['sources'].count(job['source']) != 1):
            raise ValueError('Replay owner differs from its exact source/plan')
    return copy.deepcopy(plan)


def ready_guard(destination, job):
    source = job['source']
    events = artifacts._events(destination)
    entries = artifacts.registered_snapshots(destination, events)
    if len(entries) != 1 or not entries[0]['initial'] or entries[0]['filename'] != 'initial.snp':
        raise ValueError('Replay requires exactly one registered initial SNP')
    path = destination/'snapshots/initial.snp'
    if not 0 < path.stat().st_size <= 16*MiB or common._hash(path) != entries[0]['sha256']:
        raise ValueError('Replay SNP exceeds its ready cap or registered hash differs')
    native = read_snapshot(path)
    if (normalized_snapshot(native) != source['initial_guard_sha256']
            or native['application']['source_run_id'] != job['run_id']
            or native['application']['execution_mode'] != job['stage']):
        raise ValueError('Replay initial state changed outside the three recorder fields')
    _compatible(artifacts._events(Path(source['path'])), events, reference.REFERENCES[job['reference_mode']][0], job['reference_mode'])
    return {'snapshot_sha256': entries[0]['sha256'], 'snapshot_bytes': path.stat().st_size,
        'initial_guard_sha256': normalized_snapshot(native), 'native_sha256': native['native_sha256']}


def worker(raw):
    job = validate_job(raw); run = Path(job['output']); started = time.monotonic()
    if source_identity(job['assets']) != job['source_identity'] or job['source'] not in source_evidence(job['assets']):
        raise ValueError('Replay source/executor changed before initialization')
    ready = []
    def progress(stage, **values):
        if time.monotonic()-started > 150:
            raise TimeoutError('Replay callback exceeded its 150-second deadline')
        if stage == 'ready': ready.append(ready_guard(run, job))
        if stage == 'step' and (len(ready) != 1 or not 300 <= values['state']['total_tick'] <= 300+job['source']['ticks']):
            raise ValueError('Replay tick preceded admission or exceeded the fixed source')
    report = replay_run(job['source']['path'], run, mode=job['stage'], repo_root=REPO,
        asset_root=job['assets'], storage_budget=budget(job['root_output']),
        recording_max_bytes=192*MiB, progress=progress)
    unchanged = job['source'] in source_evidence(job['assets'])
    elapsed = time.monotonic()-started
    passed = report['status'] == 'passed' and report['compared_ticks'] == job['source']['ticks'] and len(ready) == 1 and unchanged and elapsed <= 150
    result = {'status': 'passed' if passed else 'failed', 'run_id': job['run_id'], 'stage': job['stage'],
        'reference_mode': job['reference_mode'], 'ready_guard': ready, 'source_unchanged': unchanged,
        'wall_seconds': elapsed, 'replay_report_sha256': common._hash(run/'replay-report.json')}
    neural.write(run/'worker-report.json', result, budget(job['root_output']))
    return 0 if passed else 1


def validate_stage(job, supervised):
    if supervised['status'] != 'completed' or supervised.get('returncode') != 0:
        raise ValueError('First replay owner failure retained')
    run = Path(job['output']); source = job['source']
    data = artifacts._load(run); native, entry, _ = _initial_snapshot(data)
    report = artifacts._json(artifacts._read(run/'replay-report.json', MiB))
    worker_report = artifacts._json(artifacts._read(run/'worker-report.json', MiB))
    manifest = data['manifest']; policy = job['stage'] == 'policy'
    inference = policy and job['reference_mode'] == SOURCES[0][0]
    admission = {'source_run_id': source['run_id'], 'source_controller': reference.REFERENCES[job['reference_mode']][0],
        'snapshot_state_sha256': source['snapshot_state_sha256'], 'native_sha256': source['native_sha256'],
        'case_sha256': memory.sha256(source['case']), 'replace_controller': False, 'memory_u_sha256': None,
        'mode': job['reference_mode'], 'protocol_sha256': reference.PROTOCOL_SHA256, 'source_scenario': job['reference_mode']}
    if (report['status'] != 'passed' or report['first_divergence'] is not None or report['errors']
            or report['source_run_id'] != source['run_id'] or report['run_id'] != job['run_id']
            or report['mode'] != job['stage'] or report['compared_ticks'] != source['ticks']
            or report['source_snapshot_sha256'] != source['snapshot_sha256']
            or report['source_snapshot_id'] != source['snapshot_id']
            or report['inference_executed'] is not inference or report['controller_reexecuted'] is not policy
            or manifest['memory_reference_admission'] != admission
            or manifest['memory_reference_protocol'] != reference.PROTOCOL
            or manifest['recording_max_bytes'] != 192*MiB or manifest['recorded_ticks'] != source['ticks']
            or manifest['total_tick'] != 300+source['ticks'] or manifest['final_phase'] != 'terminated'
            or manifest['last_outcome']['reason'] != 'goal' or manifest['execution_mode'] != job['stage']
            or manifest['inference_executed'] is not inference or manifest['controller_reexecuted'] is not policy
            or worker_report['status'] != 'passed' or worker_report['run_id'] != job['run_id']
            or worker_report['stage'] != job['stage'] or worker_report['reference_mode'] != job['reference_mode']
            or not worker_report['source_unchanged'] or not 0 <= worker_report['wall_seconds'] <= 150
            or worker_report['replay_report_sha256'] != common._hash(run/'replay-report.json')
            or worker_report['ready_guard'] != [ready_guard(run, job)]
            or normalized_snapshot(native) != source['initial_guard_sha256'] or entry['sha256'] != worker_report['ready_guard'][0]['snapshot_sha256']):
        raise ValueError('Replay mode/initial/native/terminal/cleanup contract differs')
    count = 0
    for expected, actual in zip(iter_ticks(Path(source['path'])/'recording'), iter_ticks(run/'recording'), strict=True):
        _same_tick(expected, actual, job['stage'], 300+count); count += 1
    if count != source['ticks']: raise ValueError('Independent replay row count differs')
    paths = [*data['paths'], run/'snapshots/initial.snp', run/'snapshots/index.json', run/'replay-report.json', run/'worker-report.json']
    return {'status': 'passed', 'compared_ticks': count, 'inference_executed': inference,
        'controller_reexecuted': policy, 'files': [{'path': str(p.relative_to(run)), 'bytes': p.stat().st_size, 'sha256': common._hash(p)} for p in paths]}


def run_verifier(raw):
    plan = validate_plan(raw); output = Path(plan['output']); first = plan['jobs'][0]
    if (source_identity(first['assets']) != plan['source_identity']
            or source_evidence(first['assets']) != plan['sources'] or output.exists()):
        raise ValueError('Replay source changed or output is not fresh')
    existing = output.parent
    while not existing.exists(): existing = existing.parent
    if shutil.disk_usage(existing).free < 4*GiB+64*MiB: raise ValueError('Replay storage preflight failed')
    storage = budget(output); started = time.monotonic()
    rows = [{'run_id': j['run_id'], 'reference_mode': j['reference_mode'], 'stage': j['stage'], 'status': 'unattempted'} for j in plan['jobs']]
    failure, current = None, None
    env = {**os.environ, 'PYTHONPATH': str(REPO/'src'), 'MUJOCO_GL': 'egl', 'MPLBACKEND': 'Agg', 'OMP_NUM_THREADS': '2'}
    with storage.lock():
        (output/'runs').mkdir(); storage.check_count('runs', 0, 6)
        neural.write(output/'replay-plan.json', plan, storage)
        try:
            for index, job in enumerate(plan['jobs']):
                current = rows[index]
                if time.monotonic()-started > 1020-160: raise TimeoutError('No wall budget for next replay owner')
                validate_job(job)
                neural.write(output/f"{job['run_id']}-job.json", job, storage)
                print(json.dumps(current), flush=True)
                supervised = bounded_process([sys.executable, str(Path(__file__)), '--worker', json.dumps(job)],
                    Path(job['output']), 160, env, log_max_bytes=MiB, storage_budget=storage)
                current.update(status='failed', supervisor=supervised)
                current['audit'] = validate_stage(job, supervised)
                current['status'] = 'passed'
        except (OSError, ValueError, TypeError, KeyError, RuntimeError, TimeoutError) as error:
            failure = {'type': type(error).__name__, 'message': str(error),
                'run_id': None if current is None else current['run_id'],
                'scope': 'before-owner' if current is None or current['status'] == 'unattempted' else 'attempted-owner'}
        try:
            after = source_identity(first['assets'])
            unchanged = after == plan['source_identity'] and source_evidence(first['assets']) == plan['sources']
        except Exception as error:
            after, unchanged = {'error': {'type': type(error).__name__, 'message': str(error)}}, False
        elapsed = time.monotonic()-started
        passed = failure is None and all(r['status'] == 'passed' for r in rows) and unchanged and elapsed <= 1020
        result = {'version': 1, 'status': 'reference_replay_checked' if passed else 'reference_replay_unverified',
            'protocol_sha256': PROTOCOL_SHA256, 'source_identity': plan['source_identity'], 'final_source_identity': after,
            'source_unchanged': unchanged, 'runs': rows, 'first_failure': failure, 'wall_seconds': elapsed,
            'aggregate_deadline_pass': elapsed <= 1020, 'r2_complete': False, 'held_out_executed': False}
        neural.write(output/'reference-replay-report.json', result, storage)
    return 0 if passed else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-only', action='store_true'); parser.add_argument('--assets', type=Path)
    parser.add_argument('--output', type=Path); parser.add_argument('--worker')
    parser.add_argument('--prepared-plan', type=Path); parser.add_argument('--prepared-plan-sha256')
    args = parser.parse_args()
    if args.worker is not None: return worker(json.loads(args.worker))
    if args.prepared_plan is not None: return run_verifier(neural.read_prepared_plan(args.prepared_plan, args.prepared_plan_sha256))
    if not args.plan_only or args.assets is None or args.output is None: parser.error('Use hash-bound prepared plan, worker or plan-only')
    print(json.dumps(make_plan(args.assets, args.output), indent=2, allow_nan=False)); return 0


if __name__ == '__main__':
    raise SystemExit(main())
