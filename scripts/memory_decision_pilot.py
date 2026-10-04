"""Bounded, headless memory-v2 DEVELOPMENT feasibility and paired pilot.

Only CPU FLYNN acts; no manual rescue, training, held-out IDs or retries. The CLI
parent owns the storage lease and sequential bounded_process owners. There is no
nested phase process group. owner.json records PID/start-time/PGID for an external
orchestrator to survey after parent interruption. All failed raw runs are kept.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

MiB, GiB = 1024**2, 1024**3
CONDITIONS = ('own', 'swapped', 'no-U', 'sham')
STAGE_SECONDS = {'preflight': 1800, 'feasibility': 1800, 'pilot': 4200}
QUALIFIER = ('Exploratory correlated development variants; no inferential independence, '
             'R2 benefit, held-out confirmation, biological learning or physical qualification.')
PROTOCOL = {'version': 1, 'scenario': 'memory-decision-v2', 'conditions': list(CONDITIONS),
    'controller': 'flynn', 'device': 'cpu', 'retries': 0, 'acquisition_cap': 1200,
    'continuation_cap': 900, 'phase_max_bytes': 8*GiB, 'start_free_bytes': 10*GiB,
    'min_free_bytes': 2*GiB, 'headroom_bytes': 64*MiB,
    'prefix_max_bytes': 512*MiB, 'continuation_max_bytes': 384*MiB,
    'snapshot_max_bytes': 16*MiB, 'log_max_bytes': MiB,
    'feasibility_internal_seconds': 150, 'feasibility_external_seconds': 160,
    'pilot_internal_seconds': 120, 'pilot_external_seconds': 130,
    'cleanup_seconds': 10, 'qualifier': QUALIFIER}
JOB_FIELDS = {'version', 'repo', 'assets', 'history_root', 'output', 'stage_output', 'phase_root',
    'run_id', 'stage', 'operation', 'condition', 'spec', 'case', 'source_identity',
    'protocol_sha256', 'snapshot_path', 'snapshot_sha256', 'expected_invariant'}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


PROTOCOL_SHA256 = sha(PROTOCOL)


def condition_digest(snapshot):
    """Keep version, supervisor, world/native/controller/RNG and command state."""
    from palimpsest.snapshots import state_digest
    value = copy.deepcopy(snapshot)
    app = value['application']
    state = app['memory']
    for key in ('u', 'selector'):
        state.pop(key, None)
    for key in ('source_run_id', 'event_prefix'):
        app.pop(key, None)
    return state_digest(value)


def repeat_post_digest(snapshot, source_receipt_ids):
    """Normalize only destination recorder IDs added by the five new commands."""
    value = copy.deepcopy(snapshot)
    app = value['application']
    destination = app['source_run_id']
    for identifier, receipt in app['receipts'].items():
        if identifier in source_receipt_ids:
            continue
        for field in ('received_run_id', 'applied_run_id'):
            if field in receipt:
                if receipt[field] != destination:
                    raise ValueError('New command receipt belongs to a different recorder')
                receipt[field] = 'destination-recorder'
    return condition_digest(value)


def capped_score(record):
    ticks, goal = record.get('continuation_ticks'), record.get('goal')
    if type(ticks) is not int or not 0 <= ticks <= 900 or type(goal) is not bool:
        raise ValueError('Continuation score requires boolean goal and integer ticks in [0,900]')
    return ticks if goal else 900


def prerequisite_pass(kind, result):
    if kind == 'restore':
        return (result.get('invariants_preserved') is True and result.get('repeat_matches') is True)
    if kind not in ('prefix', 'open-route', 'retreat'):
        raise ValueError('Unknown mandatory prerequisite')
    if result.get('acquired') is not True:
        return False
    if kind == 'prefix':
        return True
    return result.get('goal') is True and (kind != 'retreat' or result.get('retreat_completed') is True)


def admit_time(now, deadline, outer_seconds, cleanup_seconds=10.):
    values = (now, deadline, outer_seconds, cleanup_seconds)
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
        raise ValueError('Finite owner allocation required')
    if outer_seconds <= 0 or cleanup_seconds < 0:
        raise ValueError('Invalid owner/cleanup allocation')
    return deadline-now >= outer_seconds+cleanup_seconds


def stage_cap(stage, seconds):
    if stage not in STAGE_SECONDS:
        raise ValueError('Unknown public stage')
    seconds = STAGE_SECONDS[stage] if seconds is None else seconds
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or not 0 < seconds <= STAGE_SECONDS[stage]:
        raise ValueError('Stage allocation cannot exceed its frozen cap or transfer time')
    return seconds


def checked_path(path):
    result = Path(os.path.abspath(path))
    if any(p.is_symlink() for p in (result, *result.parents)):
        raise ValueError('Paths may not traverse symlinks')
    return result


def overlaps(left, right):
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def safe_output(path, sources):
    result = checked_path(path)
    if result.exists():
        raise ValueError('Output must be absent; existing evidence is immutable')
    if any(overlaps(result, checked_path(source)) for source in sources):
        raise ValueError('Output overlaps a source input')
    return result


def phase_budget(root):
    from palimpsest.storage import StorageBudget, StorageLimits
    return StorageBudget((checked_path(root),), StorageLimits(max_bytes=8*GiB,
        min_free_bytes=2*GiB, max_runs=38, max_snapshots=1), headroom_bytes=64*MiB)


class SnapshotBudget:
    def __init__(self, storage):
        self.storage = storage

    def check_count(self, *args):
        return self.storage.check_count(*args)

    def check(self, additional, *, path):
        if Path(path).suffix == '.snp' and additional > 16*MiB:
            raise ValueError('Snapshot exceeds frozen 16 MiB publication cap')
        return self.storage.check(additional, path=path)


def deadline_check(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('Stage/owner allocation exhausted, including admission and audits')


def write_control(path, value, storage):
    payload = json.dumps(value, indent=2, sort_keys=True, allow_nan=False).encode()+b'\n'
    if len(payload) > MiB:
        raise ValueError('Control envelope exceeds 1 MiB')
    # Control files consume the reserved concurrent headroom, like bounded_process
    # logs/status; payload writers retain the full 64 MiB reserve.
    from palimpsest.storage import StorageBudget
    StorageBudget(storage.roots, storage.limits).check(len(payload), path=path)
    with checked_path(path).open('xb') as stream:
        stream.write(payload)


def read_json(path, limit=MiB):
    path = checked_path(path)
    if not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Missing or oversized bounded JSON input')
    def invalid(value):
        raise ValueError('Nonfinite JSON number')
    return json.loads(path.read_bytes(), parse_constant=invalid)


def read_raw(run, deadline=None):
    """Use the checksum/count-verifying reader without legacy artifact tick limits."""
    from palimpsest.records import iter_ticks
    run = checked_path(run)
    manifest = read_json(run/'recording/manifest.json')
    events = []
    path = checked_path(run/'recording/events.jsonl')
    if path.stat().st_size > 32*MiB:
        raise ValueError('Raw events exceed bound')
    with path.open('rb') as stream:
        for sequence, line in enumerate(stream):
            deadline_check(deadline)
            if len(line) > MiB or sequence >= 50000:
                raise ValueError('Raw event count/envelope exceeds bound')
            if not line.endswith(b'\n'):
                if manifest.get('status') == 'running':
                    break
                raise ValueError('Terminal run contains torn event')
            event = json.loads(line)
            if event.get('sequence') != sequence:
                raise ValueError('Raw event sequence differs')
            events.append(event)
    rows = []
    for row in iter_ticks(run/'recording'):
        deadline_check(deadline)
        if len(rows) >= 2100:
            raise ValueError('Memory-v2 raw tick allocation exceeded')
        rows.append(row)
    return {'run': run, 'manifest': manifest, 'events': events, 'rows': rows}


def feasibility_specs():
    specs = []
    for mirrored in (False, True):
        for kind in ('no-event', 'change'):
            specs.append({'id': ('north' if mirrored else 'south')+'-'+kind,
                'seed': 400, 'regime': 'local_cue', 'kind': kind, 'mirrored': mirrored,
                'operation': 'full', 'mandatory': 'retreat' if kind == 'change' else 'open-route'})
    for mirrored in (False, True):
        specs.append({'id': ('north' if mirrored else 'south')+'-prefix', 'seed': 400,
            'regime': 'local_cue', 'kind': 'change', 'mirrored': mirrored,
            'operation': 'prefix', 'mandatory': 'prefix'})
    for index in (1, 2):
        specs.append({'id': f'restore-{index}', 'seed': 400, 'regime': 'local_cue',
            'kind': 'change', 'mirrored': False, 'operation': 'repeat', 'mandatory': 'restore',
            'source': 'south-prefix'})
    return specs


def pilot_specs():
    specs = [{'id': regime+('-north' if mirrored else '-south'), 'seed': 401,
        'regime': regime, 'kind': 'change', 'mirrored': mirrored}
        for regime in ('local_cue', 'paired_cue') for mirrored in (False, True)]
    specs.extend([{'id': 'local-null', 'seed': 402, 'regime': 'local_cue', 'kind': 'null', 'mirrored': False},
        {'id': 'paired-no-event', 'seed': 403, 'regime': 'paired_cue', 'kind': 'no-event', 'mirrored': True}])
    return specs


def audit_pair(records):
    if len(records) != 4 or {r.get('condition') for r in records} != set(CONDITIONS):
        raise ValueError('Pair audit requires exactly the four fixed conditions')
    conditions = {r['condition']: r for r in records}
    own, sham = conditions['own'], conditions['sham']
    identical = own.get('trace_digest') is not None and own.get('trace_digest') == sham.get('trace_digest')
    fields = ('goal', 'continuation_ticks', 'path_length', 'route_commits', 'post_event_samples')
    identical = identical and all(own.get(k) == sham.get(k) for k in fields)
    fresh = True
    for record in records:
        commits = record.get('route_commits', [])
        event = record.get('event_tick')
        commit = commits[0]['tick'] if commits else None
        samples = record.get('post_event_samples', [])
        if commit is None or any(tick <= commit for tick in samples if event is not None and tick >= event):
            fresh = False
    decisions_differ = bool(own.get('route_commits') and conditions['no-U'].get('route_commits') and
        own['route_commits'][0]['route_id'] != conditions['no-U']['route_commits'][0]['route_id'])
    return {'own_sham_identical': identical, 'commitment_before_fresh_sample': fresh,
        'm_caused_route_difference': decisions_differ,
        'scores': {c: capped_score(r) for c, r in conditions.items()}}


def common_helpers():
    from scripts import verify_memory_transfer as common
    return common


def source_identity(repo, assets):
    # This helper hashes prepared graph/assets and pinned source without preparing
    # or downloading them. Engine later receives these exact immutable paths.
    from scripts.verify_flynn_memory_transfer import source_identity as identity
    result = identity(repo, assets)
    result['pilot_driver_sha256'] = file_hash(Path(__file__))
    manifest = read_json(Path(repo)/'model_manifests/flynn-full-vision.json')
    archive = next(f for f in manifest['files'] if f['id'] == 'graph_archive')
    metadata = checked_path(Path(assets)/('graph-'+archive['sha256'])/'palimpsest-prepared.json')
    result['prepared_metadata_sha256'] = file_hash(metadata)
    return result


def source_paths(repo, assets, history_root):
    repo = checked_path(repo)
    return [checked_path(assets), checked_path(history_root), repo/'src', repo/'scripts',
        repo/'model_manifests', repo/'upstream', repo/'uv.lock', repo/'docs/plans']


def mapped_histories(regime, histories):
    return histories if regime == 'local_cue' else {'own': histories['swapped'], 'swapped': histories['own']}


def selector_for(condition, histories):
    result = common_helpers().selector_config(condition, histories)
    if condition not in ('own', 'swapped', 'sham'):
        result['provenance_sha256'] = PROTOCOL_SHA256
    return result


def u_for(condition, histories):
    return common_helpers().condition_u(condition, histories)


def preflight(repo, assets, history_root, output, phase_root, deadline=None):
    from palimpsest import memory_decision_world as world
    repo, assets, history_root, phase_root = [checked_path(p) for p in (repo, assets, history_root, phase_root)]
    if repo != Path(__file__).resolve().parents[1]:
        raise ValueError('Runner checkout and --repo must match exactly')
    output = safe_output(output, source_paths(repo, assets, history_root))
    if not output.is_relative_to(phase_root):
        raise ValueError('Output must be inside the global phase root')
    if any(overlaps(phase_root, source) for source in source_paths(repo, assets, history_root)):
        raise ValueError('Global phase root overlaps immutable source inputs')
    existing = phase_root
    while not existing.exists():
        existing = existing.parent
    if shutil.disk_usage(existing).free < 10*GiB:
        raise ValueError('Phase execution requires at least 10 GiB free at admission')
    deadline_check(deadline)
    identity = source_identity(repo, assets)
    histories = common_helpers().load_histories(history_root)
    deadline_check(deadline)
    geometry = []
    for spec in feasibility_specs()[:6]+pilot_specs():
        case = world.make_case(spec['seed'], spec['regime'], spec['kind'], mirrored=spec['mirrored'])
        historical_ids = common_helpers().experiment._ids(histories['own']['e']) | common_helpers().experiment._ids(histories['swapped']['e'])
        if common_helpers().experiment._ids(case) & historical_ids:
            raise ValueError('Development case and frozen historical episode namespaces overlap')
        check = world.geometry_check(case)
        geometry.append({'id': spec['id'], 'case': case, 'check': check})
        deadline_check(deadline)
    return {'version': 1, 'protocol': PROTOCOL, 'protocol_sha256': PROTOCOL_SHA256,
        'repo': str(repo), 'assets': str(assets), 'history_root': str(history_root),
        'output': str(output), 'phase_root': str(phase_root), 'source_identity': identity,
        'history_inputs': {key: {'path': str(history_root/value['path']), 'sha256': value['sha256'],
            'e_sha256': sha(value['e']), 'u_sha256': sha(value['u']), 'lineage': 'frozen-v1-historical-acquisition'}
            for key, value in histories.items()}, 'geometry': geometry,
        'geometry_valid': all(row['check'].get('valid') is True for row in geometry),
        'qualifier': QUALIFIER, 'r2_complete': False}


def validate_job(raw):
    if type(raw) is not dict or set(raw) != JOB_FIELDS or len(canonical(raw)) > 256*1024:
        raise ValueError('Unknown/missing or oversized private worker fields')
    job = copy.deepcopy(raw)
    if job['version'] != 1 or job['protocol_sha256'] != PROTOCOL_SHA256:
        raise ValueError('Worker protocol differs')
    if job['stage'] not in ('feasibility', 'pilot') or job['operation'] not in ('prefix', 'full', 'repeat', 'condition'):
        raise ValueError('Unsupported worker stage/operation')
    if job['condition'] not in (*CONDITIONS, None):
        raise ValueError('Unsupported condition')
    if job['operation'] == 'condition' and (job['stage'] != 'pilot' or job['condition'] is None):
        raise ValueError('Scored branches require pilot condition')
    if job['operation'] != 'condition' and job['condition'] is not None:
        raise ValueError('Acquisition/prerequisites have no selector condition')
    specs = feasibility_specs() if job['stage'] == 'feasibility' else pilot_specs()
    if job['spec'] not in specs:
        raise ValueError('Unfrozen development spec or held-out case')
    if job['stage'] == 'feasibility' and job['operation'] != job['spec']['operation']:
        raise ValueError('Prerequisite operation differs')
    if job['stage'] == 'pilot' and job['operation'] not in ('prefix', 'condition'):
        raise ValueError('Pilot cannot use prerequisite controls')
    for key in ('repo', 'assets', 'history_root', 'output', 'stage_output', 'phase_root'):
        if not Path(job[key]).is_absolute() or str(checked_path(job[key])) != job[key]:
            raise ValueError('Worker paths must be absolute and have no symlinks')
    if Path(job['repo']) != Path(__file__).resolve().parents[1] or uuid.UUID(job['run_id']).hex != job['run_id']:
        raise ValueError('Worker checkout/run identity differs')
    if Path(job['output']) != Path(job['stage_output'])/'runs'/job['run_id'] or not Path(job['stage_output']).is_relative_to(Path(job['phase_root'])):
        raise ValueError('Worker output escapes stage/phase allocation')
    safe_output(job['output'], source_paths(job['repo'], job['assets'], job['history_root']))
    restore = job['operation'] in ('condition', 'repeat')
    if restore:
        path = checked_path(job['snapshot_path'])
        if not path.is_relative_to(Path(job['stage_output'])) or path.suffix != '.snp':
            raise ValueError('Restore source must be an acquired snapshot in this stage')
        for key in ('snapshot_sha256', 'expected_invariant'):
            if type(job[key]) is not str or len(job[key]) != 64 or any(c not in '0123456789abcdef' for c in job[key]):
                raise ValueError('Missing restore hash/invariant')
    elif any(job[key] is not None for key in ('snapshot_path', 'snapshot_sha256', 'expected_invariant')):
        raise ValueError('Fresh prefix cannot receive a restore source')
    from palimpsest import memory_decision_world as world
    spec = job['spec']
    expected = world.make_case(spec['seed'], spec['regime'], spec['kind'], mirrored=spec['mirrored'])
    if canonical(job['case']) != canonical(expected) or world.geometry_check(expected).get('valid') is not True:
        raise ValueError('Worker case differs or frozen geometry is invalid')
    return job


def policy_step(engine):
    command = {'id': f'neural-{engine.episode_step}', 'kind': 'step',
        'expected_state': 'paused', 'expected_episode': engine.episode}
    if engine.controller != 'flynn' or engine.policy is None or engine.phase != 'paused':
        raise ValueError('Only paused CPU FLYNN stepping is admitted')
    if engine.submit(command).get('status') != 'queued':
        raise ValueError('Policy step refused')
    return engine.advance()


def audit_policy(engine):
    from palimpsest.snapshots import state_digest
    original = engine.policy.act
    def act(observation):
        if set(observation) != {'cam_left', 'cam_right', 'sensors'} or set(observation['sensors']) != {'collision', 'collision_angle', 'wind_direction'}:
            raise ValueError('CPU policy received undeclared inputs')
        result = original(observation)
        engine._event('neural_policy_call', observation_sha256=state_digest(observation),
            cameras_sha256={k: state_digest(observation[k]) for k in ('cam_left', 'cam_right')},
            sensors=copy.deepcopy(observation['sensors']),
            result_sha256={k: state_digest(result[k]) for k in ('action', 'encoded_input', 'raw_output')})
        return result
    engine.policy.act = act


def native_owner(run_id):
    pid = os.getpid()
    stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
    return {'pid': pid, 'starttime': int(stat[19]), 'pgid': os.getpgid(pid), 'run_id': run_id}


def capture_engine(engine):
    from palimpsest.snapshots import capture
    return capture(engine.env, engine.observation, policy=engine.policy, teacher=engine.teacher,
        application=engine.application_state())


def worker(raw):
    started = time.monotonic()
    job = validate_job(raw)  # Must precede model import, allocation and any write.
    internal = PROTOCOL[job['stage']+'_internal_seconds']
    deadline = started+internal
    if source_identity(job['repo'], job['assets']) != job['source_identity']:
        raise ValueError('Worker source/prepared assets changed before writer admission')
    histories = mapped_histories(job['spec']['regime'], common_helpers().load_histories(job['history_root']))
    deadline_check(deadline)
    from palimpsest.engine import Engine
    from palimpsest.snapshots import read_snapshot
    from palimpsest.replay import _register_initial
    run = Path(job['output'])
    storage = phase_budget(job['phase_root'])  # Parent lease; no child lock.
    limit = 384*MiB if job['operation'] == 'condition' else 512*MiB
    storage.check(limit+16*MiB, path=run)
    native = None
    if job['snapshot_path'] is not None:
        if file_hash(job['snapshot_path']) != job['snapshot_sha256']:
            raise ValueError('Acquired restore source checksum differs')
        native = read_snapshot(job['snapshot_path'])
        if condition_digest(native) != job['expected_invariant']:
            raise ValueError('Acquired source invariant differs')
        if native['application']['memory']['supervisor']['phase'] != 'await_decision':
            raise ValueError('Source is not the real acquired decision boundary')
    run.mkdir(parents=True, exist_ok=False)
    write_control(run/'owner.json', native_owner(job['run_id']), storage)
    engine = None
    report = {'version': 1, 'run_id': job['run_id'], 'run': str(run), 'case_id': job['spec']['id'],
        'operation': job['operation'], 'condition': job['condition'], 'status': 'failed',
        'acquired': False, 'goal': False, 'continuation_ticks': 0, 'invariants_preserved': False,
        'qualifier': QUALIFIER, 'r2_complete': False}
    try:
        engine = Engine.open(job['repo'], job['assets'], run/'recording', controller='flynn', device='cpu',
            seed=job['case']['seed'], scenario='memory-decision-v2', memory_case=job['case'],
            run_id=job['run_id'], max_bytes=limit, storage_budget=storage,
            **({'restore_snapshot': native} if native is not None else {}))
        engine.writer.manifest.update(memory_decision_pilot_protocol_sha256=PROTOCOL_SHA256,
            memory_decision_pilot_job=job, historical_lineage='frozen-v1-historical-acquisition')
        audit_policy(engine)
        if native is not None:
            if condition_digest(capture_engine(engine)) != job['expected_invariant']:
                raise ValueError('Restore changed native/model/RNG/M/E/supervisor state')
            report['invariants_preserved'] = True
        else:
            for _ in range(1200):
                deadline_check(deadline)
                if engine.memory['supervisor']['phase'] == 'await_decision' or engine.phase != 'paused':
                    break
                policy_step(engine)
        report['acquired'] = (engine.phase == 'paused' and engine.memory['supervisor']['phase'] == 'await_decision')
        if not report['acquired']:
            raise ValueError('Real CPU FLYNN prefix did not obtain both open observations and return')
        _register_initial(engine, run, SnapshotBudget(storage))
        initial = read_snapshot(run/'snapshots/initial.snp')
        report.update(snapshot_path=str(run/'snapshots/initial.snp'), snapshot_sha256=file_hash(run/'snapshots/initial.snp'),
            invariant=condition_digest(initial), acquisition_ticks=engine.episode_step)
        if job['operation'] in ('condition', 'full', 'repeat'):
            if job['operation'] != 'repeat':
                condition = job['condition'] or 'no-U'
                engine.configure_memory_selector(selector_for(condition, histories), u=u_for(condition, histories))
                if condition_digest(capture_engine(engine)) != report['invariant']:
                    raise ValueError('Selector/U substitution changed preserved continuation state')
            engine.arm_memory_decision()
            report['event_tick'] = engine.episode_step+1
            start_tick = engine.episode_step
            for _ in range(5 if job['operation'] == 'repeat' else 900):
                deadline_check(deadline)
                if engine.phase != 'paused':
                    break
                policy_step(engine)
            report['continuation_ticks'] = engine.episode_step-start_tick
            if job['operation'] == 'repeat' and engine.phase == 'paused':
                report['post_state_digest'] = repeat_post_digest(capture_engine(engine), set(initial['application']['receipts']))
        report['status'] = 'recorded'
    except Exception as error:
        report['error'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        if engine is not None:
            report.update(final_phase=engine.phase, outcome=copy.deepcopy(engine.last_outcome),
                final_memory=copy.deepcopy(engine.memory), world_state=copy.deepcopy(engine.world_task_state),
                total_ticks=engine.episode_step)
            report['goal'] = engine.memory['supervisor']['phase'] == 'goal'
            try:
                engine.close()
            except Exception as error:
                report.update(status='cleanup_failed', cleanup_error={'type': type(error).__name__, 'message': str(error)})
        try:
            if source_identity(job['repo'], job['assets']) != job['source_identity']:
                raise ValueError('Source/prepared asset identity changed during native owner')
            deadline_check(deadline)
        except Exception as error:
            report.update(status='failed', identity_or_time_error={'type': type(error).__name__, 'message': str(error)})
    report['wall_seconds'] = time.monotonic()-started
    report['capped_ticks'] = capped_score(report)
    write_control(run/'worker-report.json', report, storage)
    return 0 if report['status'] == 'recorded' else 1


def trace_digest(rows):
    from palimpsest.snapshots import state_digest
    digest = hashlib.sha256()
    for row in rows:
        # Timing measurements never change neural/motor/geometry equivalence.
        value = {k: v for k, v in row.items() if k not in ('latency', 'step_latency')}
        digest.update(state_digest(value).encode())
    return digest.hexdigest()


def policy_bindings(data):
    from scripts.verify_flynn_memory_transfer import policy_bindings as validate
    validate(data)


def audit_commitment(detail):
    """Recompute the fixed categorical policy from retained public/M inputs."""
    inputs = detail.get('inputs')
    if not isinstance(inputs, list) or len(inputs) != 2:
        raise ValueError('Commitment does not retain both public route/M inputs')
    viable = []
    for row in inputs:
        estimate, status = row['estimate'], row['status']
        category = 'blocked' if estimate == 'blocked' and status == 'observed' else 'open' if estimate == 'open' and status == 'observed' else 'uncertain'
        if row['category'] != category or not math.isfinite(row['cost']) or row['cost'] <= 0:
            raise ValueError('Commitment categorical/public-cost input differs')
        if category != 'blocked':
            viable.append((category != 'open', row['cost'], row['route_id']))
    if not viable or min(viable)[2] != detail.get('route_id'):
        raise ValueError('Commitment violates shared categorical/public-cost/lexical policy')


def replay_memory_audit(job, data, snapshot, report):
    """Reconsume independently reconstructed packets and bind exact M/route decisions."""
    from palimpsest import memory_decision
    state = (copy.deepcopy(snapshot['application']['memory']) if job['snapshot_path'] is not None
             else memory_decision.initialize(job['case']))
    expected_details, bearing = [], None
    for event in data['events']:
        kind = event['kind']
        if kind == 'snapshot_registered':
            if state != snapshot['application']['memory']:
                raise ValueError('Acquired snapshot M/supervisor differs from actual packet replay')
        elif kind == 'memory_selector_configured':
            histories = mapped_histories(job['spec']['regime'], common_helpers().load_histories(job['history_root']))
            condition = job['condition'] or 'no-U'
            if event['selector'] != selector_for(condition, histories) or event['u'] != u_for(condition, histories):
                raise ValueError('Retained selector substitution differs from frozen v1 resources')
            state = memory_decision.configure_selector(state, event['selector'], event['u'])
        elif kind == 'memory_decision_armed':
            boundary = snapshot['application']['episode_step']
            schedule = event['schedule']
            if schedule['boundary_tick'] != boundary or schedule['decision_tick'] != boundary+2 or schedule['event_tick'] != (boundary+1 if job['case']['event_enabled'] else None):
                raise ValueError('Decision/event schedule differs from identical acquired boundary')
            state = memory_decision.arm(state, boundary)
        elif kind == 'memory_sensed':
            if expected_details:
                raise ValueError('Recorded decision details were omitted')
            try:
                state, bearing, expected_details = memory_decision.advance_memory(state, event['packet'])
            except memory_decision.CueUnavailable:
                if report.get('final_phase') != 'failed' or (report.get('outcome') or {}).get('type') != 'CueUnavailable':
                    raise ValueError('Unrecorded sensor contract failure')
                expected_details = []
        elif kind == 'memory_decision':
            if not expected_details or event['detail'] != expected_details.pop(0):
                raise ValueError('Recorded commitment/M/selector/transition differs from independent packet replay')
        elif kind == 'memory_cue':
            if expected_details or event['bearing'] != bearing:
                raise ValueError('Bearing bridge differs from shared supervisor replay')
    if expected_details:
        raise ValueError('Final supervisor decisions omitted')
    if report['goal']:
        state = memory_decision.mark_goal(state)
    if state != report['final_memory']:
        raise ValueError('Final M/E/requests/supervisor differs from independent declared-packet replay')


def native_manifest_matches(job, manifest):
    from palimpsest.profiles import validate_decision
    expected_limit = 384*MiB if job['operation'] == 'condition' else 512*MiB
    return (manifest.get('controller') == 'flynn' and manifest.get('requested_device') == 'cpu'
        and manifest.get('run_id') == job['run_id']
        and manifest.get('scenario') == validate_decision('memory-decision-v2', 'checker', 'flynn')
        and manifest.get('recording_max_bytes') == expected_limit
        and manifest.get('memory_decision_pilot_job') == job)


def gate_evidence(case, operation, state, applied, report):
    """Distinguish an executed gate obligation from a scored pre-event failure."""
    if case['kind'] != 'change' or operation == 'prefix':
        return False
    event_tick = state['event_tick']
    reached = event_tick is not None and state['last_tick'] is not None and state['last_tick'] >= event_tick
    if reached:
        if state['gate_result'] != 'closed' or len(applied) != 1 or applied[0].get('tick') != event_tick:
            raise ValueError('Actual gate closure proof differs from frozen schedule')
        if 'subjects_by_side' in case:
            from palimpsest import memory_decision_world as world
            side = case['subjects_by_side'].index(case['closure_subject_id'])
            proof = applied[0]
            edit = proof.get('intervention', {})
            if (proof.get('subject_id') != case['closure_subject_id'] or edit.get('kind') != 'move_obstacle'
                    or edit.get('index') != len(world.POSTS)+side
                    or edit.get('old', {}).get('xy') != world.PARKED_GATES[side]
                    or edit.get('new', {}).get('xy') != world.CLOSED_GATES[side]):
                raise ValueError('Actual gate edit differs from frozen cylinder and closure coordinates')
        return False
    if report.get('final_phase') == 'failed' and not report['goal'] and not applied and state['gate_result'] == 'pending':
        return True
    raise ValueError('Scheduled event unexecuted without a retained pre-event task failure')


def audit_run(job, supervised, deadline=None):
    from palimpsest import memory_decision_world as world, memory_decision
    from palimpsest.snapshots import read_snapshot
    from palimpsest.replay import _initial_snapshot
    data = read_raw(job['output'], deadline)
    report = read_json(Path(job['output'])/'worker-report.json')
    manifest = data['manifest']
    if (supervised.get('status') != 'completed' or supervised.get('returncode') != 0
            or report.get('status') != 'recorded' or 'cleanup_error' in report
            or manifest.get('status') == 'running'
            or not native_manifest_matches(job, manifest)):
        raise ValueError('Native owner, terminal recording, source/controller or job identity differs')
    environments = [e for e in data['events'] if e['kind'] == 'environment']
    if len(environments) != 1 or any(environments[0].get(k) != job['source_identity'].get(k)
            for k in ('source_sha256', 'lock_sha256', 'upstream_commit')):
        raise ValueError('Actual environment source provenance differs')
    expected_limit = 384*MiB if job['operation'] == 'condition' else 512*MiB
    if manifest.get('recording_max_bytes') != expected_limit:
        raise ValueError('Native recording cap differs')
    policy_bindings(data)
    snapshot, entry, _ = _initial_snapshot(data)
    if (entry['sha256'] != report.get('snapshot_sha256')
            or file_hash(report['snapshot_path']) != entry['sha256']
            or condition_digest(snapshot) != report.get('invariant')
            or snapshot['application'].get('schema_version') != 8
            or snapshot['application']['memory'].get('version') != 3
            or snapshot['application']['memory']['supervisor']['phase'] != 'await_decision'):
        raise ValueError('Registered acquired snapshot or task/application version differs')
    if job['snapshot_path'] is not None and condition_digest(snapshot) != job['expected_invariant']:
        raise ValueError('Restore/configuration changed preserved snapshot state')
    state = report.get('world_state') or {}
    event_tick, gate_result = state.get('event_tick'), state.get('gate_result')
    # Verify scheduled gate application against retained actual intervention proof.
    changes = [e.get('detail', {}) for e in data['events'] if e['kind'] == 'memory_world_changed']
    applied = [e for e in changes if e.get('kind') == 'memory_gate_applied']
    scheduled_unexecuted = gate_evidence(job['case'], job['operation'], state, applied, report)
    sensed = {e['episode_step']: e['packet'] for e in data['events'] if e['kind'] == 'memory_sensed'}
    if len(sensed) != len([e for e in data['events'] if e['kind'] == 'memory_sensed']):
        raise ValueError('Duplicate symbolic packet tick')
    observations = []
    bypasses = []
    path = 0.
    for row in data['rows']:
        deadline_check(deadline)
        tick = int(row['tick'])
        inputs = world.reconstruct_inputs(job['case'], row['pose'].tolist(), tick,
            event_tick=event_tick, gate_result=gate_result or 'not_requested')
        expected = memory_decision.capture_symbolic(inputs[0], inputs[1], inputs[2], episode_id='episode-0', tick=tick)
        if sensed.get(tick) != expected:
            raise ValueError('Recorded packet/arrival differs from independent actual-pose frozen geometry reconstruction')
        observations.extend(item for item in expected['passages'] if item['passability'] != 'unobserved')
        x, y = map(float, row['pose'][:2]); nx, ny = map(float, row['next_pose'][:2])
        path += math.hypot(nx-x, ny-y)
        if x*nx <= 0 and x != nx:
            crossing_y = y+(ny-y)*(-x)/(nx-x)
            if abs(abs(crossing_y)-1.) > .3+1e-6:
                bypasses.append({'tick': tick, 'y': crossing_y})
    if bypasses:
        raise ValueError('Actual motor trace crosses separator outside admitted apertures')
    # A sensor-only acquired boundary can have no motor row; its boundary packet
    # must still be reconstructed using the actual snapshot observation pose.
    extra = set(sensed)-{int(row['tick']) for row in data['rows']}
    if extra:
        if extra != {report.get('total_ticks')} or report.get('final_phase') != 'failed':
            raise ValueError(f'Unsupported symbolic packets without control rows: {sorted(extra)}')
        source_rows = data['rows']
        if not source_rows and job['snapshot_path'] is not None:
            source_rows = read_raw(Path(job['snapshot_path']).parents[1], deadline)['rows']
        if not source_rows:
            raise ValueError('Failed symbolic boundary has no retained actual pose')
        tick = next(iter(extra))
        inputs = world.reconstruct_inputs(job['case'], source_rows[-1]['next_pose'].tolist(), tick,
            event_tick=event_tick, gate_result=gate_result or 'not_requested')
        expected = memory_decision.capture_symbolic(*inputs, episode_id='episode-0', tick=tick)
        if sensed[tick] != expected:
            raise ValueError('Failed boundary symbolic packet does not match retained actual pose')
        observations.extend(p for p in expected['passages'] if p['passability'] != 'unobserved')
    facts = snapshot['application']['memory']['m']['facts']
    prefix_sensed = [e['packet'] for e in data['events'] if e['kind'] == 'memory_sensed'
        and e['episode_step'] < snapshot['application']['episode_step']]
    if job['snapshot_path'] is None:
        for fact in facts:
            evidence = fact.get('evidence')
            candidates = [p for packet in prefix_sensed for p in packet['passages']
                if p['subject_id'] == fact['subject_id'] and p['passability'] == 'open']
            if fact.get('estimate') != 'open' or evidence is None or not candidates:
                raise ValueError('Acquired belief lacks a real initial open sample')
    replay_memory_audit(job, data, snapshot, report)
    details = [e['detail'] for e in data['events'] if e['kind'] == 'memory_decision']
    commits = [d for d in details if d['kind'] == 'memory_commitment']
    graph = world.public_graph(job['case'])
    routes = {r['route_id']: r for r in graph['routes']}
    for detail in commits:
        audit_commitment(detail)
        if detail['route_id'] not in routes or detail['subject_id'] != routes[detail['route_id']]['subject_id']:
            raise ValueError('Commitment selected private/non-public route')
        for row in detail['inputs']:
            route = routes.get(row['route_id'])
            if route is None or row['cost'] != route['cost'] or row['fact_id'] != route['fact_id']:
                raise ValueError('Commitment changed frozen public graph cost/fact mapping')
        if detail.get('tick') is None:
            raise ValueError('Commitment lacks public tick')
    transitions = [d for d in details if d['kind'] == 'memory_transition']
    inspections = [d for d in details if d['kind'] == 'memory_inspection']
    scored_start = snapshot['application']['episode_step']
    scored = [row for row in data['rows'] if int(row['tick']) >= scored_start]
    if report['continuation_ticks'] != len(scored):
        raise ValueError('Capped score count differs from actual scored motor rows')
    if report['goal']:
        goal_xy = job['case']['goal_xy']
        radius = snapshot['identity']['environment_profile']['values']['goal_radius']
        if (not scored or (report.get('outcome') or {}).get('reason') != 'goal'
                or math.hypot(*(float(scored[-1]['next_pose'][i])-goal_xy[i] for i in range(2))) >= radius):
            raise ValueError('Goal label lacks actual declared geometric termination')
    result = {**report, 'job_id': job['spec']['id']+('/'+job['condition'] if job['condition'] else ''),
        'event_tick': event_tick, 'path_length': path, 'bypasses': [],
        'scheduled_event_unexecuted_task_failure': scheduled_unexecuted,
        'trace_digest': trace_digest(scored), 'raw_audit_pass': True, 'policy_binding_pass': True,
        'native_policy_replay_scope': ('acquired-snapshot-continuation' if job['snapshot_path'] is not None
            else 'full-prefix-policy-replay-unsupported-first-registered-snapshot-is-after-prefix'),
        'commitment_inputs': [d['inputs'] for d in commits],
        'route_commits': [{'tick': d['tick'], 'route_id': d['route_id'], 'subject_id': d['subject_id']}
            for d in commits], 'post_event_samples': sorted({p['tick'] for p in observations
                if event_tick is not None and p['tick'] >= event_tick}),
        'inspection_count': len(inspections), 'replans': sum(t['to'] == 'replan' for t in transitions),
        'retreat_completed': any(t['from'] == 'retreat' and t['to'] == 'replan' for t in transitions),
        'unavailable_cues': int((report.get('outcome') or {}).get('type') == 'CueUnavailable'),
        'first_commitment_blocked': bool(commits and gate_result == 'closed' and
            commits[0]['subject_id'] == job['case'].get('closure_subject_id'))}
    if job['operation'] == 'repeat' and (len(scored) != 5 or not report.get('post_state_digest')):
        raise ValueError('Deterministic restore prerequisite did not complete exactly five real policy ticks')
    result['capped_ticks'] = capped_score(result)
    return result


def hash_ledger(root, deadline=None):
    root = checked_path(root)
    result = []
    for directory, dirs, names in os.walk(root, followlinks=False):
        if any((Path(directory)/name).is_symlink() for name in dirs+names):
            raise ValueError('Output ledger contains symlink')
        for name in sorted(names):
            deadline_check(deadline)
            path = Path(directory)/name
            if len(result) >= 100000 or not path.is_file():
                raise ValueError('Output ledger exceeds regular-file inventory bound')
            result.append({'path': str(path.relative_to(root)), 'bytes': path.stat().st_size, 'sha256': file_hash(path)})
    return result


def make_job(stage, spec, plan, operation, condition=None, source=None):
    from palimpsest import memory_decision_world as world
    identifier = uuid.uuid4().hex
    return {'version': 1, 'repo': plan['repo'], 'assets': plan['assets'], 'history_root': plan['history_root'],
        'stage_output': plan['output'], 'phase_root': plan['phase_root'],
        'output': str(Path(plan['output'])/'runs'/identifier), 'run_id': identifier,
        'stage': stage, 'operation': operation, 'condition': condition, 'spec': spec,
        'case': world.make_case(spec['seed'], spec['regime'], spec['kind'], mirrored=spec['mirrored']),
        'source_identity': plan['source_identity'], 'protocol_sha256': PROTOCOL_SHA256,
        'snapshot_path': None if source is None else source['snapshot_path'],
        'snapshot_sha256': None if source is None else source['snapshot_sha256'],
        'expected_invariant': None if source is None else source['invariant']}


def launch_owner(stage, spec, plan, storage, deadline, *, operation=None, condition=None, source=None):
    from palimpsest.evaluate import bounded_process
    operation = operation or spec['operation']
    outer = PROTOCOL[stage+'_external_seconds']
    if not admit_time(time.monotonic(), deadline, outer, PROTOCOL['cleanup_seconds']):
        raise TimeoutError('Remaining stage allocation cannot accommodate owner and cleanup; no time transfer')
    job = validate_job(make_job(stage, spec, plan, operation, condition, source))
    output = Path(plan['output'])
    (output/'jobs').mkdir(exist_ok=True)
    write_control(output/'jobs'/(job['run_id']+'.json'), job, storage)
    environment = {**os.environ, 'PYTHONPATH': str(Path(plan['repo'])/'src')+os.pathsep+plan['repo'],
        'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1',
        'NUMEXPR_NUM_THREADS': '1', 'MUJOCO_GL': 'egl', 'CUDA_VISIBLE_DEVICES': ''}
    supervised = bounded_process([sys.executable, str(Path(__file__).resolve()), '--stage', 'worker',
        '--worker', canonical(job).decode()], output/'supervision'/job['run_id'], outer,
        environment, log_max_bytes=MiB, storage_budget=storage)
    result = {'job_id': spec['id']+('/'+condition if condition else ''), 'run': job['output'],
        'run_id': job['run_id'], 'operation': operation, 'condition': condition, 'goal': False,
        'continuation_ticks': 0, 'capped_ticks': 900, 'status': 'failed', 'supervision': supervised}
    try:
        deadline_check(deadline)
        result.update(audit_run(job, supervised, deadline))
        if operation == 'repeat':
            result['repeat_matches'] = False  # Reconciled only after both independently audited repeats.
    except Exception as error:
        result['audit_error'] = {'type': type(error).__name__, 'message': str(error)}
        # Keep even interrupted/failed publication in the ledger; no promotion.
        worker_path = Path(job['output'])/'worker-report.json'
        if worker_path.exists():
            result['failed_worker_report'] = read_json(worker_path)
    return result


def validate_feasibility(path, plan):
    report = read_json(path)
    if (report.get('version') != 1 or report.get('stage') != 'feasibility'
            or report.get('protocol_sha256') != PROTOCOL_SHA256 or report.get('mandatory_pass') is not True
            or report.get('source_identity') != plan['source_identity'] or report.get('unattempted')
            or len(report.get('attempted', [])) != 8
            or any(r.get('raw_audit_pass') is not True for r in report['attempted'])):
        raise ValueError('Pilot requires complete independently audited native feasibility report')
    if not checked_path(path).is_relative_to(Path(plan['phase_root'])):
        raise ValueError('Prerequisite evidence must belong to the same global byte phase')
    # Recheck every retained output identity before admitting pilot writers.
    root = checked_path(report['output'])
    for entry in report['hash_ledger']:
        source = checked_path(root/entry['path'])
        if not source.is_relative_to(root) or source.stat().st_size != entry['bytes'] or file_hash(source) != entry['sha256']:
            raise ValueError('Native prerequisite retained evidence changed')
    for spec, result in zip(feasibility_specs(), report['attempted']):
        if not prerequisite_pass(spec['mandatory'], result):
            raise ValueError('Mandatory native prerequisite not satisfied')
    return {'path': str(checked_path(path)), 'sha256': file_hash(path)}


def execute_stage(stage, plan, storage, deadline):
    specs = feasibility_specs() if stage == 'feasibility' else pilot_specs()
    report = {'version': 1, 'stage': stage, 'output': plan['output'], 'phase_root': plan['phase_root'],
        'protocol_sha256': PROTOCOL_SHA256, 'source_identity': plan['source_identity'],
        'attempted': [], 'unattempted': [], 'errors': [], 'pair_audits': [], 'mandatory_pass': False,
        'qualifier': QUALIFIER, 'r2_complete': False}
    if not plan.get('geometry_valid'):
        report['errors'].append({'type': 'GeometryInvalid', 'message': 'Frozen candidate failed; no native owner or replacement layout'})
        report['unattempted'] = ([spec['id'] for spec in specs] if stage == 'feasibility' else
            [spec['id'] for spec in specs]+[spec['id']+'/'+condition for spec in specs for condition in CONDITIONS])
        return report
    sources, repeats = {}, []
    next_index = 0
    try:
        for index, spec in enumerate(specs):
            next_index = index
            deadline_check(deadline)
            if stage == 'feasibility':
                result = launch_owner(stage, spec, plan, storage, deadline,
                    source=sources.get(spec.get('source')))
                report['attempted'].append(result)
                next_index = index+1
                if spec['operation'] == 'repeat':
                    repeats.append(result)
                    if len(repeats) == 2:
                        equal = (all(r.get('invariants_preserved') is True and r.get('raw_audit_pass') is True for r in repeats)
                            and repeats[0].get('trace_digest') == repeats[1].get('trace_digest')
                            and repeats[0].get('post_state_digest') == repeats[1].get('post_state_digest')
                            and repeats[0].get('post_state_digest') is not None)
                        for repeat in repeats:
                            repeat['repeat_matches'] = equal
                        if not equal:
                            raise ValueError('Independent five-tick restore state/actions/raw/camera repeats differ')
                    elif result.get('status') != 'recorded' or not result.get('raw_audit_pass'):
                        raise ValueError('First deterministic restore prerequisite failed')
                elif not prerequisite_pass(spec['mandatory'], result) or result.get('raw_audit_pass') is not True:
                    raise ValueError('Mandatory native prerequisite failed; later launch prohibited')
                sources[spec['id']] = result
            else:
                prefix = launch_owner(stage, spec, plan, storage, deadline, operation='prefix')
                report['attempted'].append(prefix)
                if not prerequisite_pass('prefix', prefix) or prefix.get('raw_audit_pass') is not True:
                    raise ValueError('Pilot real-prefix prerequisite failed')
                records = []
                for condition in CONDITIONS:
                    result = launch_owner(stage, spec, plan, storage, deadline,
                        operation='condition', condition=condition, source=prefix)
                    report['attempted'].append(result)
                    records.append(result)
                    if result.get('status') != 'recorded' or result.get('raw_audit_pass') is not True:
                        raise ValueError('Pilot infrastructure/raw audit failure; no partial pair promotion')
                pair = audit_pair(records)
                own, no_u = records[0], records[2]
                pair['m_caused_route_difference'] = bool(pair['m_caused_route_difference']
                    and own.get('commitment_inputs') and no_u.get('commitment_inputs')
                    and own['commitment_inputs'][0] != no_u['commitment_inputs'][0]
                    and own['invariant'] == no_u['invariant'])
                pair['case_id'] = spec['id']
                pair['kind'] = spec['kind']
                pair['closed_route_cost_observed'] = (spec['kind'] == 'change' and records[2].get('first_commitment_blocked')
                    and records[2].get('retreat_completed') and records[2]['path_length'] > records[0]['path_length'])
                pair['false_targeting_cost_observed'] = (spec['kind'] == 'null' and
                    records[0]['path_length'] > records[2]['path_length'])
                report['pair_audits'].append(pair)
                next_index = index+1
                if not pair['own_sham_identical'] or not pair['commitment_before_fresh_sample']:
                    raise ValueError('Paired continuation identity/opportunity audit failed')
        report['mandatory_pass'] = True
        if stage == 'pilot':
            report['mechanism_observed'] = (any(a['m_caused_route_difference'] for a in report['pair_audits'] if a['kind'] == 'change')
                and any(a['closed_route_cost_observed'] for a in report['pair_audits'])
                and any(a['false_targeting_cost_observed'] for a in report['pair_audits']))
    except Exception as error:
        report['errors'].append({'type': type(error).__name__, 'message': str(error)})
        report['unattempted'] = [spec['id'] for spec in specs[next_index:]]
        if stage == 'pilot':
            attempted_ids = {r['job_id'] for r in report['attempted']}
            report['unattempted'] = [spec['id'] for spec in specs if spec['id'] not in attempted_ids]
            report['unattempted'] += [spec['id']+'/'+condition for spec in specs for condition in CONDITIONS
                if spec['id']+'/'+condition not in attempted_ids]
    return report


def main(argv=None):
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True, choices=('preflight', 'feasibility', 'pilot', 'worker'))
    for name in ('repo', 'assets', 'history-root', 'output', 'phase-root', 'feasibility-report'):
        parser.add_argument('--'+name, type=Path)
    parser.add_argument('--seconds-cap', type=float)
    parser.add_argument('--worker', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.stage == 'worker':
        if args.worker is None:
            parser.error('Private worker requires its fixed job JSON')
        return worker(json.loads(args.worker))
    if args.worker is not None or any(getattr(args, key) is None for key in ('repo', 'assets', 'history_root', 'output', 'phase_root')):
        parser.error('Public stages require --repo --assets --history-root --output --phase-root')
    if args.stage == 'pilot' and args.feasibility_report is None:
        parser.error('Pilot requires --feasibility-report')
    deadline = started+stage_cap(args.stage, args.seconds_cap)
    plan = preflight(args.repo, args.assets, args.history_root, args.output, args.phase_root, deadline)
    prerequisite = validate_feasibility(args.feasibility_report, plan) if args.stage == 'pilot' else None
    deadline_check(deadline)
    storage = phase_budget(args.phase_root)
    with storage.lock():
        output = Path(plan['output'])
        output.mkdir(parents=True, exist_ok=False)
        write_control(output/'preflight.json', plan, storage)
        if args.stage == 'preflight':
            report = {**plan, 'stage': 'preflight', 'attempted': [], 'unattempted': [],
                'mandatory_pass': plan['geometry_valid'], 'errors': []}
        else:
            report = execute_stage(args.stage, plan, storage, deadline)
        report['prerequisite'] = prerequisite
        try:
            deadline_check(deadline)
            report['hash_ledger'] = hash_ledger(output, deadline)
            report['storage_usage'] = storage.usage()
            report['source_identity_unchanged'] = source_identity(args.repo, args.assets) == plan['source_identity']
            if not report['source_identity_unchanged']:
                raise ValueError('Source/prepared asset identity changed during stage')
            deadline_check(deadline)
        except Exception as error:
            report['mandatory_pass'] = False
            report.setdefault('errors', []).append({'type': type(error).__name__, 'message': str(error)})
        report['status'] = 'passed' if report['mandatory_pass'] else 'failed'
        report['wall_seconds'] = time.monotonic()-started
        report['seconds_cap'] = stage_cap(args.stage, args.seconds_cap)
        write_control(output/'report.json', report, storage)
    print(json.dumps({'report': str(output/'report.json'), 'mandatory_pass': report['mandatory_pass'], 'qualifier': QUALIFIER}))
    return 0 if report['mandatory_pass'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
