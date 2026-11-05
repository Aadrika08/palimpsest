"""Internal, parent-admitted CPU FLYNN source owner for one frozen family case.

JOB_FIELDS is exact. No history, condition, restore, retry or CLI entry exists.
Validation is metadata only: it neither reads payloads nor allocates output.
The parent must independently freeze/hold the complete runtime/assets closure,
lease storage, authorize this exact job and supervise/reap/drain this owner.
An admission object is that enclosing parent's assertion, not execution authority
or a production qualification pin. This owner never creates an allocation.
"""
from __future__ import annotations

import copy
import hashlib
import math
import os
from pathlib import Path
import stat
import time
import uuid

from palimpsest import memory, memory_decision_world as world
from scripts.memory_family_compact_v4 import PROTOCOL, PROTOCOL_SHA256

REPO_ROOT = Path(__file__).resolve().parents[1]
MiB = 1024**2
JOB_FIELDS = {
    'schema', 'operation', 'condition', 'split', 'block', 'row', 'kind', 'case',
    'run_id', 'protocol_sha256', 'source_identity_sha256', 'immutable', 'paths',
    'limits', 'parent_admission',
}
LIMITS = {
    'source_steps': 1200, 'internal_seconds': 360, 'cleanup_seconds': 10,
    'recording_max_bytes': 512 * MiB, 'snapshot_max_bytes': 16 * MiB,
    'max_bytes': 640 * MiB, 'min_free_bytes': 6 * 1024**3,
    'headroom_bytes': 64 * MiB,
}


def _fields(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f'{label} has missing or unknown fields')


def _json(value, depth=0, count=None):
    count = [0] if count is None else count
    count[0] += 1
    if depth > 32 or count[0] > 20000:
        raise ValueError('Source job JSON exceeds structural limits')
    if type(value) is dict:
        for key, item in value.items():
            if type(key) is not str or len(key) > 1024:
                raise ValueError('Source job requires bounded string JSON keys')
            _json(item, depth + 1, count)
    elif type(value) is list:
        for item in value:
            _json(item, depth + 1, count)
    elif type(value) is str:
        if len(value) > 4096:
            raise ValueError('Source job string exceeds limit')
    elif type(value) is float:
        if not math.isfinite(value):
            raise ValueError('Source job JSON must be finite')
    elif value is not None and type(value) not in (int, bool):
        raise ValueError('Source job must contain exact JSON types')


def job_sha256(value):
    """Hash the frozen job content; admission cannot recursively bind itself."""
    _json(value)
    payload = memory.canonical_bytes({k: v for k, v in value.items()
                                      if k != 'parent_admission'})
    if len(payload) > 256 * 1024:
        raise ValueError('Source job exceeds 256 KiB')
    return hashlib.sha256(payload).hexdigest()


def _path(value):
    if (type(value) is not str or not value or '\x00' in value
            or value.startswith('//') or not Path(value).is_absolute()
            or os.path.normpath(value) != value
            or str(Path(value)) != value):
        raise ValueError('Source paths must be canonical absolute paths')
    return Path(value)


def _overlap(left, right):
    return left == right or left.is_relative_to(right) or right.is_relative_to(left)


def _descriptor(value):
    _fields(value, {'path', 'size_bytes', 'sha256'}, 'Immutable descriptor')
    _path(value['path'])
    memory._digest(value['sha256'])
    if type(value['size_bytes']) is not int or not 1 <= value['size_bytes'] <= 16 * 1024**3:
        raise ValueError('Immutable descriptor size is invalid')


def _validate_metadata(value: dict) -> dict:
    """Common metadata checks; never supplies parent execution admission."""
    _fields(value, JOB_FIELDS, 'Source job')
    job_sha256(value)
    job = copy.deepcopy(value)
    if (job['schema'] != 'memory-family-source-job-v2'
            or job['operation'] != 'source' or job['condition'] is not None
            or job['split'] != 'development' or job['kind'] != 'change'
            or type(job['block']) is not int or job['block'] != 0
            or type(job['row']) is not int or job['row'] != 0
            or job['protocol_sha256'] != PROTOCOL_SHA256):
        raise ValueError('Only the frozen development/0/0/change source is admitted')
    expected = world.make_family_case('development', 0, 0, 'change')
    if memory.canonical_bytes(job['case']) != memory.canonical_bytes(expected):
        raise ValueError('Source case differs from the frozen generator case')
    try:
        valid_run = type(job['run_id']) is str and uuid.UUID(job['run_id']).hex == job['run_id']
    except (ValueError, AttributeError):
        valid_run = False
    if not valid_run:
        raise ValueError('Source run requires canonical UUID hex')
    memory._digest(job['source_identity_sha256'])
    immutable = job['immutable']
    _fields(immutable, {'python_alias', 'python_elf', 'owner_source', 'closure'}, 'Immutable runtime')
    inputs = [_path(immutable['python_alias'])]
    if type(immutable['closure']) is not list or not 1 <= len(immutable['closure']) <= 4096:
        raise ValueError('An externally pinned bounded immutable closure is required')
    descriptors = [immutable['python_elf'], immutable['owner_source'], *immutable['closure']]
    for descriptor in descriptors:
        _descriptor(descriptor)
    files = [_path(descriptor['path']) for descriptor in descriptors]
    if (len(files) != len(set(files)) or immutable['closure'] != sorted(
            immutable['closure'], key=lambda row: row['path'])):
        raise ValueError('Immutable file descriptors alias one another')
    if (files[1] != Path(__file__).resolve()
            or immutable['owner_source']['sha256'] != job['source_identity_sha256']):
        raise ValueError('Owner source identity differs from its pinned descriptor')
    paths = job['paths']
    _fields(paths, {'repo', 'assets', 'evidence_root', 'control_root', 'raw', 'snapshot', 'owner', 'error'}, 'Source paths')
    parsed = {key: _path(item) for key, item in paths.items()}
    evidence, control = parsed['evidence_root'], parsed['control_root']
    base = evidence / '.pending' / expected['case_id']
    if parsed['repo'] != REPO_ROOT or _overlap(parsed['assets'], evidence):
        raise ValueError('Source checkout or immutable asset root differs/aliases')
    inputs.append(parsed['assets'])
    exact = {'raw': base / '.raw' / job['run_id'],
             'snapshot': base / 'source/snapshots/initial.snp',
             'owner': base / 'source/owner.json',
             'error': control / (job['run_id'] + '.error.json')}
    if any(parsed[key] != path for key, path in exact.items()) or control != evidence / 'controls' / job['run_id']:
        raise ValueError('Source raw, sole snapshot, owner or external control path differs')
    if any(_overlap(root, source) for root in (evidence, control)
           for source in [*inputs, *files]):
        raise ValueError('Source output overlaps immutable runtime/assets')
    _fields(job['limits'], LIMITS, 'Source limits')
    if any(type(job['limits'][key]) is not int or job['limits'][key] != limit
           for key, limit in LIMITS.items()):
        raise ValueError('Source limits differ from the fixed parent allocation')
    return job


def validate_source_template(value: dict) -> dict:
    """Validate a preparation template without payload reads or admission."""
    job = _validate_metadata(value)
    if job['parent_admission'] is not None:
        raise PermissionError('Source template must have null parent admission')
    return job


def validate_source_job(value: dict) -> dict:
    """Validate finite exact metadata and a live enclosing parent assertion."""
    job = _validate_metadata(value)
    digest = job_sha256(job)
    admission = job['parent_admission']
    if admission is None:
        raise PermissionError('Missing enclosing source admission')
    _fields(admission, {'schema', 'admitted', 'run_id', 'job_sha256',
                        'allocation_sha256', 'deadline_monotonic'}, 'Parent admission')
    memory._digest(admission['allocation_sha256'])
    deadline = admission['deadline_monotonic']
    if (admission['schema'] != 'memory-family-source-parent-admission-v2'
            or admission['admitted'] is not True or admission['run_id'] != job['run_id']
            or admission['job_sha256'] != digest
            or type(deadline) not in (int, float) or not math.isfinite(deadline)
            or deadline <= time.monotonic()):
        raise PermissionError('Enclosing source admission differs from this frozen job')
    return job


def _safe_path(value):
    from palimpsest.artifacts import _safe_path as safe
    return safe(value)


def _fsync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_json(path, value, storage):
    payload = memory.canonical_bytes(value)
    if len(payload) > MiB:
        raise ValueError('Source control exceeds 1 MiB')
    path = _safe_path(path)
    storage.check(len(payload), path=path)
    with path.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_directory(path.parent)


def _check_identity(job):
    immutable = job['immutable']
    for name in ('repo', 'assets'):
        if not _safe_path(job['paths'][name]).is_dir():
            raise ValueError('Pinned runtime/asset directory is absent')
    alias = Path(immutable['python_alias'])
    if alias.resolve(strict=True) != Path(immutable['python_elf']['path']):
        raise ValueError('Executable venv alias differs from frozen ELF')
    inodes = set()
    for expected in [immutable['python_elf'], immutable['owner_source'], *immutable['closure']]:
        path = _safe_path(expected['path'])
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(descriptor)
            inode = (before.st_dev, before.st_ino)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or inode in inodes:
                raise ValueError('Immutable source is nonregular or aliased')
            inodes.add(inode)
            with os.fdopen(descriptor, 'rb', closefd=False) as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            after = os.fstat(descriptor)
            named = path.stat(follow_symlinks=False)
            identity = lambda item: (item.st_dev, item.st_ino, item.st_size,
                                     item.st_mtime_ns, item.st_ctime_ns, item.st_nlink)
            if (identity(before) != identity(after) or identity(after) != identity(named)
                    or after.st_size != expected['size_bytes'] or digest != expected['sha256']):
                raise ValueError('Immutable source/runtime/assets changed')
        finally:
            os.close(descriptor)


def _load_engine():
    from palimpsest.engine import Engine
    return Engine.open


def _storage(job):
    from palimpsest.storage import StorageBudget, StorageLimits
    return StorageBudget([job['paths']['evidence_root'], job['paths']['control_root']],
        StorageLimits(max_bytes=LIMITS['max_bytes'], min_free_bytes=LIMITS['min_free_bytes'],
                      max_runs=1, max_snapshots=1), headroom_bytes=LIMITS['headroom_bytes'])


def _capture(engine):
    from palimpsest import snapshots
    return snapshots.capture(engine.env, engine.observation, policy=engine.policy,
                             teacher=engine.teacher, application=engine.application_state())


def _register_snapshot(engine, job, storage):
    from palimpsest import snapshots
    from scripts.memory_decision_pilot import SnapshotBudget
    path = _safe_path(job['paths']['snapshot'])
    storage.check_count('snapshots', 0)
    snapshot = _capture(engine)
    from scripts.memory_family_raw_audit_v4 import _source_application
    application = snapshot.get('application') if type(snapshot) is dict else None
    if (type(application) is not dict
            or any(type(application.get(key)) is not int
                   for key in ('episode', 'episode_step', 'total_tick'))
            or type(application.get('eyes')) is not dict
            or any(type(enabled) is not bool for enabled in application['eyes'].values())
            or type(engine.total_tick) is not int or type(engine.episode_step) is not int
            or engine.total_tick != engine.episode_step
            or str(engine.policy.device) != 'cpu'):
        raise ValueError('Source boundary has invalid typed cursors, eyes or CPU identity')
    _source_application(application, job['case'], job['run_id'], {
        'total_ticks': engine.episode_step, 'world_state': engine.world_task_state})
    snapshots.save_snapshot(snapshot, path, storage_budget=SnapshotBudget(storage))
    _fsync_directory(path.parent)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    engine._event('snapshot_registered', snapshot_id=uuid.uuid4().hex,
                  filename='initial.snp', initial=True, sha256=digest)
    return digest


def _run_admitted(job, storage, open_engine, check_identity):
    """Owner core; authored tests supply objects here, never through public CLI."""
    from scripts.memory_decision_pilot import audit_policy, policy_step
    from palimpsest import memory_decision
    started = time.monotonic()
    deadline = min(started + LIMITS['internal_seconds'], job['parent_admission']['deadline_monotonic'])
    paths = job['paths']
    run = _safe_path(paths['raw'])
    engine = None
    report = None
    error = None

    def check_time():
        if time.monotonic() >= deadline:
            raise TimeoutError('Source allocation exhausted, including close and report')

    try:
        check_time()
        check_identity()
        # Neither an existing attempt nor an already captured source is reusable.
        for key in ('raw', 'snapshot', 'owner', 'error'):
            path = _safe_path(paths[key])
            if path.exists():
                raise FileExistsError('Source output already exists; no retry or replacement')
        storage.check(LIMITS['recording_max_bytes'] + LIMITS['snapshot_max_bytes'], path=run)
        storage.check_count('runs', 0)
        run.mkdir(parents=True, exist_ok=False)
        snapshot = _safe_path(paths['snapshot'])
        snapshot.parent.mkdir(parents=True, exist_ok=False)
        _safe_path(paths['control_root']).mkdir(parents=True, exist_ok=True)
        _write_json(Path(paths['owner']), {
            'schema': 'memory-family-source-owner-v4', 'case_id': job['case']['case_id'],
            'run_id': job['run_id'], 'owner_source_sha256': job['source_identity_sha256'],
            'claims': copy.deepcopy(PROTOCOL['claims'])}, storage)
        engine = open_engine(paths['repo'], paths['assets'], run / 'recording',
            controller='flynn', device='cpu', texture='checker', seed=job['case']['seed'],
            scenario=world.SCENARIO, memory_case=job['case'], run_id=job['run_id'],
            max_bytes=LIMITS['recording_max_bytes'], storage_budget=storage)
        engine.writer.manifest['memory_family_oracle_admission_v3'] = {
            'schema': 'memory-family-oracle-admission-v3',
            'protocol_sha256': PROTOCOL_SHA256,
            'source_identity_sha256': job['source_identity_sha256'],
            'case': copy.deepcopy(job['case']), 'operation': 'source',
            'condition': None, 'source_snapshot_sha256': None,
        }
        audit_policy(engine)
        for _ in range(LIMITS['source_steps']):
            check_time()
            if engine.phase != 'paused' or memory_decision.acquired_boundary(engine.memory):
                break
            if (engine.controller != 'flynn' or str(engine.policy.device) != 'cpu'
                    or engine.eyes != {'left': True, 'right': True}):
                raise ValueError('Source requires CPU FLYNN and full unmasked eyes')
            policy_step(engine)
        check_time()
        if (engine.phase != 'paused' or not memory_decision.acquired_boundary(engine.memory)
                or not 1 <= engine.episode_step <= LIMITS['source_steps']):
            raise ValueError('Source step limit/termination without acquired boundary is unscored')
        digest = _register_snapshot(engine, job, storage)
        state = world.validate_state(copy.deepcopy(engine.world_task_state))
        engine.writer.manifest['world_state'] = copy.deepcopy(state)
        report = {'schema': 'memory-family-owner-report-v3', 'run_id': job['run_id'],
            'case_id': job['case']['case_id'], 'operation': 'source', 'condition': None,
            'status': 'recorded', 'acquired': True, 'snapshot_sha256': digest,
            'source_snapshot_sha256': None, 'total_ticks': engine.episode_step,
            'final_phase': engine.phase, 'world_state': state}
    except Exception as caught:
        error = caught
    finally:
        if engine is not None:
            try:
                engine.close()
            except Exception as caught:
                error = error or caught
        try:
            check_identity()
            check_time()
        except Exception as caught:
            error = error or caught
    if error is None:
        try:
            _write_json(run / 'worker-report.json', report, storage)
            check_time()
            check_identity()
            check_time()
        except Exception as caught:
            error = caught
    if error is not None:
        # A report written before a failed final recheck must not remain accepted.
        # Preserve its bytes by retaining a separate explicit failure marker;
        # the parent may never export/audit/seal a failed owner outcome.
        failure = {'schema': 'memory-family-source-owner-failure-v2',
            'run_id': job['run_id'], 'job_sha256': job_sha256(job), 'status': 'failed',
            'error': {'type': type(error).__name__, 'message': str(error)},
            'qualification_claims': False}
        error_path = _safe_path(paths['error'])
        error_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(error_path, failure, storage)
        return {'schema': 'memory-family-source-owner-outcome-v2', 'status': 'failed',
                'run_id': job['run_id'], 'report': None, 'error_path': str(error_path),
                'qualification_claims': False}
    return {'schema': 'memory-family-source-owner-outcome-v2', 'status': 'recorded',
            'run_id': job['run_id'], 'report': report, 'error_path': None,
            'qualification_claims': False}


def run_source(job: dict) -> dict:
    """Internal parent-only owner. The enclosing parent supplies execution GO."""
    job = validate_source_job(job)
    # Loading is deferred even past filesystem/source admission.
    _check_identity(job)
    for key in ('raw', 'snapshot', 'owner', 'error'):
        if _safe_path(job['paths'][key]).exists():
            raise FileExistsError('Source output already exists; no retry or replacement')
    if time.monotonic() >= job['parent_admission']['deadline_monotonic']:
        raise TimeoutError('Source enclosing deadline exhausted before loading')
    storage = _storage(job)
    return _run_admitted(job, storage, _load_engine(), lambda: _check_identity(job))
