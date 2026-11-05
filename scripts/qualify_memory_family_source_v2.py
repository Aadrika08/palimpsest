"""One source-only qualification parent. Verification reads freeze metadata only.

Actual execution requires an externally reviewed complete freeze and exact-stage
GO. Nothing in this module creates that authority. Private seams are exclusively
for authored software tests; the real CLI always uses the fixed source/audit jobs.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import stat
import sys
import time

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from palimpsest import memory
from scripts import memory_family_source_runtime_v2 as owner
from paper.studies.change_audit_v1.process import run_accounted

ROOT = Path(__file__).resolve().parents[1]
MiB = 1024**2
ALLOCATION = {'wall_seconds': 900, 'cpu_seconds': 1800,
    'memory_max_bytes': 8 * 1024**3, 'max_bytes': 640 * MiB,
    'min_free_bytes': 6 * 1024**3, 'owner_work_seconds': 360,
    'cleanup_seconds': 10, 'log_max_bytes': 256 * 1024,
    'control_max_bytes': 8 * MiB, 'candidate_max_bytes': 32 * MiB,
    'atomic_max_bytes': 8 * MiB, 'headroom_bytes': 64 * MiB}
FREEZE_FIELDS = {'schema', 'state', 'job', 'allocation', 'environment',
    'runtime_roots', 'namespace_projections',
    'prior_cpu', 'peak_bytes', 'runtime_cgroup', 'lifetime_contract'}
LOGICAL_SOURCES = ('pre-heldout-development-history', 'training-namespace')
MAX_JSON = 1024 * 1024


def _fields(value, keys, label):
    owner._fields(value, keys, label)


def _number(value, label):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError(label + ' must be a known finite nonnegative number')
    return value


def _deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('Enclosing deadline includes cleanup and final publication')


def _cpu():
    # Reaped descendant CPU is already aggregated here: never add worker CPU.
    return sum((getattr(resource.getrusage(kind), field) for kind in
        (resource.RUSAGE_SELF, resource.RUSAGE_CHILDREN)
        for field in ('ru_utime', 'ru_stime')))


def _read(path, expected=None, maximum=MAX_JSON):
    from palimpsest import artifacts
    path = owner._safe_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ValueError('Control is nonregular, aliased or oversized')
        with os.fdopen(fd, 'rb', closefd=False) as stream:
            payload = stream.read(maximum + 1)
        after = os.fstat(fd)
        identity = lambda item: (item.st_dev, item.st_ino, item.st_size, item.st_mtime_ns, item.st_ctime_ns, item.st_nlink)
        if identity(before) != identity(after) or identity(after) != identity(path.stat(follow_symlinks=False)):
            raise ValueError('Control changed while reading')
        if len(payload) > maximum or (expected is not None and
                hashlib.sha256(payload).hexdigest() != expected):
            raise ValueError('Pinned control bytes differ')
        value = artifacts._json(payload)
        owner._json(value)
        return value
    finally:
        os.close(fd)


def _write(path, value, budget):
    payload = memory.canonical_bytes(value)
    if len(payload) > MAX_JSON:
        raise ValueError('Control exceeds one MiB')
    budget.check(len(payload), path=path)
    path = owner._safe_path(path)
    with path.open('xb') as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    owner._fsync_directory(path.parent)


def _descriptor(path, root, *, logical=None):
    path = owner._safe_path(path)
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'path': logical or str(path.relative_to(root)),
            'size_bytes': path.stat().st_size, 'sha256': digest}


def _fresh_output(output):
    output = owner._safe_path(output)
    if output.exists():
        raise FileExistsError('Existing source qualification output is never a new attempt')
    return output


def _environment(job):
    root = job['paths']['evidence_root']
    return {'PATH': '/usr/bin:/bin', 'HOME': root + '/controls/home',
        'LANG': 'C.UTF-8', 'PYTHONDONTWRITEBYTECODE': '1',
        'PYTHONPYCACHEPREFIX': root + '/controls/unused-pycache',
        'PYTHONPATH': str(ROOT / 'src') + os.pathsep + str(ROOT),
        'MPLBACKEND': 'Agg', 'MPLCONFIGDIR': root + '/controls/matplotlib',
        'CUDA_VISIBLE_DEVICES': '', 'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'}


def verify_freeze(path, expected_sha256):
    """Read pinned metadata/public source contracts; no runtime/namespace/GO opens."""
    memory._digest(expected_sha256)
    value = _read(path, expected_sha256)
    _fields(value, FREEZE_FIELDS, 'Source freeze')
    if value['schema'] != 'memory-family-source-freeze-v2' or value['state'] != 'prepared':
        raise ValueError('Closed or unknown source freeze')
    job = owner.validate_source_template(value['job'])
    if value['allocation'] != ALLOCATION or any(type(value['allocation'][k]) is not int for k in ALLOCATION):
        raise ValueError('Qualification allocation differs; no silent limit increase')
    output = Path(job['paths']['evidence_root'])
    if output.parent != ROOT / 'runs' or not output.name.startswith('memory-family-source-v2-'):
        raise ValueError('Fresh qualification output must be under ROOT/runs')
    if value['environment'] != _environment(job):
        raise ValueError('Frozen source environment differs')
    roots = value['runtime_roots']
    if type(roots) is not list or not roots or len(roots) > 16:
        raise ValueError('Complete selected runtime/source prefixes are required')
    for root in roots:
        owner._path(root)
    if roots != sorted(set(roots)) or any(owner._overlap(Path(a), Path(b))
            for i, a in enumerate(roots) for b in roots[i+1:]):
        raise ValueError('Runtime prefixes must be distinct and nonoverlapping')
    projections = value['namespace_projections']
    _fields(projections, LOGICAL_SOURCES, 'Namespace-only projections')
    for item in projections.values():
        if item is not None:
            owner._descriptor(item)
    prior = value['prior_cpu']
    _fields(prior, {'project_seconds', 'memory_seconds'}, 'Prior CPU')
    for k, item in prior.items():
        if item is not None:
            _number(item, k)
    peak = value['peak_bytes']
    _fields(peak, {'raw', 'snapshot', 'candidate', 'controls', 'atomic', 'headroom'}, 'Peak storage')
    for k, item in peak.items():
        if type(item) is not int or item < 0:
            raise ValueError('Storage peak must be a concrete nonnegative byte count')
    if (peak['raw'] < owner.LIMITS['recording_max_bytes']
            or peak['snapshot'] < owner.LIMITS['snapshot_max_bytes']
            or peak['candidate'] < ALLOCATION['candidate_max_bytes']
            or peak['controls'] < ALLOCATION['control_max_bytes']
            or peak['atomic'] < ALLOCATION['atomic_max_bytes']
            or peak['headroom'] < ALLOCATION['headroom_bytes']
            or sum(peak.values()) > ALLOCATION['max_bytes']):
        raise ValueError('Complete raw/SNP/candidate/control/atomic peaks do not fit')
    cgroup = value['runtime_cgroup']
    if cgroup is not None:
        owner._path(cgroup)
        if not Path(cgroup).is_relative_to('/sys/fs/cgroup'):
            raise ValueError('Enforcement must be a real cgroup v2 path')
    if value['lifetime_contract'] is not None:
        owner._descriptor(value['lifetime_contract'])
    external = [*projections.values(), value['lifetime_contract']]
    if any(item is not None and owner._overlap(Path(item['path']), output) for item in external):
        raise ValueError('Pinned external control input overlaps fresh writer output')
    if all(item is not None for item in prior.values()) and prior['memory_seconds'] > prior['project_seconds']:
        raise ValueError('Memory lane CPU cannot exceed aggregate project CPU')
    from scripts import memory_family_allocation_v3 as allocation
    blockers = []
    try:
        allocation._coverage_contract()
    except allocation.AdmissionRefused as exc:
        blockers.append(str(exc))
    if any(item is None for item in projections.values()):
        blockers.append('Independently authorized namespace-only projections missing')
    if cgroup is None:
        blockers.append('Whole-runtime enforced memory cgroup missing')
    blockers.append('External full-parent lifetime supervision OS/receipt interface is not implemented')
    if value['lifetime_contract'] is None:
        blockers.append('External parent process-lifetime accounting contract missing')
    if any(item is None for item in prior.values()):
        blockers.append('Prior aggregate/memory-lane CPU reconciliation missing')
    return {'schema': 'memory-family-source-preparation-v2', 'status': 'metadata-verified',
        'freeze_sha256': expected_sha256, 'freeze': value, 'blockers': blockers,
        'payloads_opened': False, 'worker_invocations': 0, 'output_created': False,
        'qualification_claims': False, 'execution_authorized': False}


def _closed_accounting(value):
    if (type(value) is not dict or value.get('accounting_complete') is not True
            or value.get('tree_drained') is not True):
        raise ValueError('Unknown CPU or non-drained owner forbids further work')
    for k in ('subtree_cpu_seconds', 'parent_cpu_seconds'):
        _number(value.get(k), k)
    if (value.get('status') != 'completed' or type(value.get('returncode')) is not int
            or value['returncode'] != 0 or value.get('errors') != []):
        raise ValueError('Failed owner/supervisor outcome forbids audit/export/seal')
    return value


def _bind_inputs(value, lifetime):
    """Hold selected immutable bytes through the last recheck; execution only."""
    from contextlib import contextmanager
    from scripts import memory_family_allocation_v3 as allocation
    # The existing canonical coverage gate refuses before any external root or
    # runtime/model descriptor is opened; labels cannot resolve missing exports.
    coverage_contract = allocation._coverage_contract()

    @contextmanager
    def hold(item):
        path = owner._safe_path(item['path'])
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
                raise ValueError('Pinned input is nonregular or aliased')
            def check():
                current = os.fstat(fd)
                named = path.stat(follow_symlinks=False)
                identity = lambda row: (row.st_dev, row.st_ino, row.st_size, row.st_mtime_ns, row.st_ctime_ns, row.st_nlink)
                os.lseek(fd, 0, os.SEEK_SET)
                with os.fdopen(fd, 'rb', closefd=False) as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if (identity(before) != identity(current) or identity(current) != identity(named)
                        or identity(current) != identity(os.fstat(fd))
                        or current.st_size != item['size_bytes'] or digest != item['sha256']):
                    raise ValueError('Held runtime/input changed')
            check()
            yield check
            check()
        finally:
            os.close(fd)
    job = value['job']
    checks = []
    descriptors = [job['immutable']['python_elf'], job['immutable']['owner_source'],
        *job['immutable']['closure'], *value['namespace_projections'].values(),
        value['lifetime_contract']]
    for item in descriptors:
        checks.append(lifetime.enter_context(hold(item)))
    owner._check_identity(job)
    roster = {row['path'] for row in [job['immutable']['owner_source'], *job['immutable']['closure']]}
    # A fresh cache prefix prevents stale pyc selection without deleting history.
    # Runtime roots are a clean selected installation, not the mixed old venv.
    found = set()
    for root in value['runtime_roots']:
        for parent, directories, files in os.walk(owner._safe_path(root), followlinks=False):
            for name in directories:
                if (Path(parent) / name).is_symlink():
                    raise ValueError('Runtime prefix contains a symlink directory')
            for name in files:
                path = owner._safe_path(Path(parent) / name)
                if path.suffix in ('.pyc', '.pyo') or path.name == 'pyvenv.cfg':
                    # pyvenv.cfg controls prefix selection and must be pinned too.
                    if path.name != 'pyvenv.cfg':
                        raise ValueError('Selected runtime prefix contains old bytecode')
                found.add(str(path))
                if len(found) > 4096:
                    raise ValueError('Complete runtime closure exceeds current owner contract')
    if not found.issubset(roster) or not found:
        raise ValueError('Runtime/dependency closure omits selected prefix bytes')
    if str(Path(__file__).resolve()) not in roster:
        raise ValueError('Executing parent source missing from frozen closure')
    required = [ROOT / 'src', ROOT / 'scripts', ROOT / 'paper/studies/change_audit_v1',
        Path(sys.prefix) / f'lib/python{sys.version_info.major}.{sys.version_info.minor}/site-packages',
        Path(sys.base_prefix) / f'lib/python{sys.version_info.major}.{sys.version_info.minor}']
    if any(not any(path == Path(root) or path.is_relative_to(root)
                   for root in value['runtime_roots']) for path in required):
        raise ValueError('Frozen roots do not cover executing source/stdlib/environment prefixes')
    config = str(Path(job['immutable']['python_alias']).parent.parent / 'pyvenv.cfg')
    if config not in roster:
        raise ValueError('Venv prefix configuration missing from exact closure')
    sets = {name: set() for name in ('known_sources', 'historical_run_ids',
        'historical_authored_ids', 'training_seeds')}
    from scripts.memory_family_producer_v3 import _case_ids
    def namespace_recheck():
        for source in coverage_contract['sources']:
            descriptor = value['namespace_projections'][source['source_id']]
            path = Path(descriptor['path'])
            if path.name != 'namespace-export.json':
                raise ValueError('Only existing canonical namespace-export.json is allowed')
            _, export, receipt = allocation._read_export(
                {'source_id': source['source_id'], 'path': str(path.parent)},
                source, coverage_contract)
            if receipt['export_bytes'] != descriptor['size_bytes'] or receipt['export_sha256'] != descriptor['sha256']:
                raise ValueError('Namespace descriptor differs from reviewed canonical coverage')
        return None
    namespace_recheck()
    for source in coverage_contract['sources']:
        descriptor = value['namespace_projections'][source['source_id']]
        _, export, _ = allocation._read_export({'source_id': source['source_id'],
            'path': str(Path(descriptor['path']).parent)}, source, coverage_contract)
        for name, target in sets.items():
            if target.intersection(export[name]):
                raise ValueError('Duplicate namespace source identity')
            target.update(export[name])
    if (job['run_id'] in sets['historical_run_ids']
            or _case_ids(job['case']).intersection(sets['historical_authored_ids'])
            or job['case']['seed'] in sets['training_seeds']):
        raise ValueError('Selected source collides with historical/training namespace')
    checks.append(namespace_recheck)
    return checks


def _enforcement(value):
    """Require pre-established cgroup v2 memory bound over parent and children."""
    group = Path(value['runtime_cgroup'])
    membership = Path('/proc/self/cgroup').read_text().splitlines()
    actual = [line[3:] for line in membership if line.startswith('0::')]
    if len(actual) != 1 or Path('/sys/fs/cgroup' + actual[0]) != group:
        raise PermissionError('Parent is outside the frozen runtime cgroup')
    if (int((group / 'memory.max').read_text()) > ALLOCATION['memory_max_bytes']
            or int((group / 'memory.max').read_text()) <= 0
            or (group / 'memory.swap.max').read_text().strip() != '0'):
        raise PermissionError('Whole-runtime memory/swap bound is not established')
    # No unrelated process may share the allocation at admission.
    if (group / 'cgroup.procs').read_text().split() != [str(os.getpid())]:
        raise PermissionError('Qualification cgroup has unrelated owners')


def _validate_go(path, expected_sha, freeze_sha, job):
    memory._digest(expected_sha)
    authority = _read(path, expected_sha)
    _fields(authority, {'schema', 'stage', 'freeze_sha256', 'job_sha256',
        'decision', 'retry', 'approval_reference'}, 'Exact-stage GO')
    if (authority['schema'] != 'memory-family-source-exact-stage-go-v2'
            or authority['stage'] != 'single-development-source-qualification'
            or authority['freeze_sha256'] != freeze_sha
            or authority['job_sha256'] != owner.job_sha256(job)
            or authority['decision'] != 'GO' or authority['retry'] is not False
            or type(authority['approval_reference']) is not str
            or not 1 <= len(authority['approval_reference']) <= 1024):
        raise PermissionError('Exact-stage GO differs from frozen job/scope')
    return authority


def _execute_admission(value, freeze_sha, lifetime, *, go_path=None, go_sha=None):
    # Existing canonical coverage is unresolved: refuse before any external
    # namespace/runtime payload. Even future coverage needs a real outer owner.
    from scripts import memory_family_allocation_v3 as allocation
    allocation._coverage_contract()
    if go_path is None or go_sha is None:
        raise PermissionError('External exact-stage GO path/hash required')
    _validate_go(go_path, go_sha, freeze_sha, value['job'])
    raise PermissionError('External full-parent lifetime supervision OS/receipt interface is not implemented')


def _prospective_runtime_checks(value, freeze_sha, lifetime):
    """Unreachable from real execution until the external lifetime gate exists."""
    checks = _bind_inputs(value, lifetime)
    contract = _read(value['lifetime_contract']['path'], value['lifetime_contract']['sha256'])
    _fields(contract, {'schema', 'job_sha256', 'runtime_cgroup', 'wall_seconds', 'cpu_seconds', 'scope'}, 'Lifetime contract')
    if contract != {'schema': 'memory-family-source-external-lifetime-v2',
            'job_sha256': owner.job_sha256(value['job']), 'runtime_cgroup': value['runtime_cgroup'],
            'wall_seconds': 900, 'cpu_seconds': 1800,
            'scope': 'parent-through-exit-including-terminal-write-and-lease-release'}:
        raise PermissionError('External lifetime contract differs')
    if sys.executable != value['job']['immutable']['python_alias']:
        raise PermissionError('Executing interpreter alias differs from frozen venv')
    if Path('/proc/self/exe').resolve() != Path(value['job']['immutable']['python_elf']['path']):
        raise PermissionError('Actually executing ELF differs')
    if dict(os.environ) != value['environment'] or not sys.dont_write_bytecode:
        raise PermissionError('Parent must start with frozen fresh pycache prefix and -B')
    _enforcement(value)
    checks.append(lambda: _enforcement(value))
    return checks


def _owner_entry(job_path, digest, outcome_path):
    job = _read(job_path, digest)
    outcome = owner.run_source(job)
    _write(Path(outcome_path), outcome, owner._storage(job))
    if outcome['status'] != 'recorded':
        raise SystemExit(1)


def _commands(job, control, snapshot, deadline):
    alias = job['immutable']['python_alias']  # Never resolve this argv element.
    outcome = control / 'owner-outcome.json'
    job_path = control / 'job.json'
    digest = hashlib.sha256(job_path.read_bytes()).hexdigest()
    owner_command = [alias, '-B', '-c',
        'from scripts.qualify_memory_family_source_v2 import _owner_entry; import sys; _owner_entry(*sys.argv[1:])',
        str(job_path), digest, str(outcome)]
    audit_command = [alias, '-B', str(ROOT / 'scripts/memory_family_raw_audit_v4.py'),
        '--run', job['paths']['raw'], '--receipt-root', str(control / 'audit'),
        '--run-id', job['run_id'], '--case-id', job['case']['case_id'], '--operation', 'source',
        '--source-identity-sha256', job['source_identity_sha256'],
        '--evidence-root', job['paths']['evidence_root'], '--source-snapshot',
        memory.canonical_bytes(snapshot).decode(), '--deadline-seconds', str(min(180, max(.001, deadline - time.monotonic() - 10)))]
    return owner_command, audit_command


def _make_budget(output):
    from palimpsest.storage import StorageBudget, StorageLimits
    return StorageBudget([output], StorageLimits(max_bytes=ALLOCATION['max_bytes'],
        min_free_bytes=ALLOCATION['min_free_bytes']), headroom_bytes=ALLOCATION['headroom_bytes'])


def execute_freeze(path, expected_sha256, *, go_path=None, expected_go_sha256=None):
    """Explicit real entry. There is no arbitrary command or loader option."""
    prepared = verify_freeze(path, expected_sha256)
    if prepared['blockers']:
        raise PermissionError('; '.join(prepared['blockers']))
    if go_path is None or expected_go_sha256 is None:
        raise PermissionError('Explicit --go and --expected-go-sha256 are required')
    return _execute(prepared['freeze'], Path(path), expected_sha256,
        _admit=lambda value, sha, lifetime: _execute_admission(value, sha, lifetime,
            go_path=go_path, go_sha=expected_go_sha256))


def _execute(value, freeze_path, freeze_sha, *, _runner=run_accounted,
             _admit=_execute_admission, _budget_factory=_make_budget,
             _clock=time.monotonic, _cpu_meter=_cpu):
    """Private authored fixtures may replace supervision/admission, never CLI."""
    started, cpu_started = _clock(), _cpu_meter()
    deadline = started + ALLOCATION['wall_seconds']
    job = copy.deepcopy(value['job'])
    output = _fresh_output(job['paths']['evidence_root'])
    output.mkdir(exist_ok=False)
    budget = _budget_factory(output)
    report = {'schema': 'memory-family-source-parent-result-v2', 'status': 'stopped',
        'qualification_claims': False, 'science_qualified': False, 'pruning_authorized': False,
        'actual_source_qualified': False, 'jobs': [], 'error': None,
        'parent_lifetime_reconciled': False, 'accounting_complete': True}
    control = Path(job['paths']['control_root'])
    control.mkdir(parents=True, exist_ok=False)
    def quarantine_published(error):
        source = Path(job['paths']['owner']).parent
        quarantine = source.parent / 'quarantine.json'
        if (source / 'commit.json').exists() and not quarantine.exists():
            _write(quarantine, {'schema': 'memory-family-source-quarantine-v1',
                'case_id': job['case']['case_id'], 'run_id': job['run_id'],
                'error_type': type(error).__name__, 'claims': copy.deepcopy(owner.PROTOCOL['claims'])}, budget)
    def check():
        if _clock() >= deadline:
            raise TimeoutError('Whole qualification deadline includes final receipt')
        used = _number(_cpu_meter() - cpu_started, 'Whole parent CPU')
        prior = value['prior_cpu']
        if (used > ALLOCATION['cpu_seconds'] or used + prior['project_seconds'] > 24*3600
                or used + prior['memory_seconds'] > 12*3600):
            raise TimeoutError('Whole qualification CPU/lane ceiling exceeded')
        budget.check(0, path=output)
        return used
    with budget.lock(), ExitStack() as lifetime:
        try:
            _write(control / 'freeze.json', value, budget)
            checks = _admit(value, freeze_sha, lifetime)
            def recheck():
                check()
                if _read(freeze_path, freeze_sha) != value:
                    raise ValueError('Pinned freeze changed')
                for callback in checks:
                    callback()
                check()
            recheck()
            if (value['prior_cpu']['project_seconds'] + ALLOCATION['cpu_seconds'] > 24*3600
                    or value['prior_cpu']['memory_seconds'] + ALLOCATION['cpu_seconds'] > 12*3600):
                raise PermissionError('Full fixed allocation plus prior charges does not fit')
            # Already-written controls occupy the frozen controls allowance.
            budget.check(max(0, sum(value['peak_bytes'].values()) - ALLOCATION['headroom_bytes']
                - budget.usage()['used_bytes']), path=output)
            job['parent_admission'] = {'schema': 'memory-family-source-parent-admission-v2',
                'admitted': True, 'run_id': job['run_id'], 'job_sha256': owner.job_sha256(job),
                'allocation_sha256': memory.sha256(value['allocation']),
                'deadline_monotonic': min(deadline - 10, _clock() + 360)}
            owner.validate_source_job(job)
            _write(control / 'job.json', job, budget)
            def launch(role, command, seconds):
                recheck()
                remaining = deadline - _clock() - 10
                if remaining <= seconds:
                    raise TimeoutError('Insufficient wall for fixed job plus cleanup/publication')
                remaining_cpu = ALLOCATION['cpu_seconds'] - check()
                record = {'role': role, 'command': command, 'environment': value['environment'],
                    'wall_seconds': seconds, 'cpu_seconds': remaining_cpu,
                    'accounting': None}
                _write(control / (role + '-launch.json'), record, budget)
                def monitor(sample):
                    check()
                try:
                    accounting = _runner(command, cwd=str(ROOT), env=value['environment'],
                        stdout_path=control / (role + '.stdout'), stderr_path=control / (role + '.stderr'),
                        wall_seconds=seconds, cpu_seconds=remaining_cpu,
                        monitor=monitor, max_log_bytes=ALLOCATION['log_max_bytes'])
                except BaseException:
                    report['accounting_complete'] = False
                    raise
                try:
                    owner._json(accounting)
                    if type(accounting) is not dict:
                        raise ValueError('Accounting is not an object')
                except (ValueError, TypeError):
                    accounting = {'status': 'malformed-accounting',
                        'accounting_complete': False, 'tree_drained': False,
                        'subtree_cpu_seconds': None, 'parent_cpu_seconds': None,
                        'raw_result_repr': repr(accounting)[:2048]}
                record['accounting'] = accounting
                report['jobs'].append(record)
                _write(control / (role + '-supervisor.json'), record, budget)
                try:
                    _closed_accounting(accounting)
                except ValueError:
                    report['accounting_complete'] = False
                    raise
                recheck()
                return record
            # Snapshot descriptor is meaningful only after the closed owner.
            owner_command, _ = _commands(job, control, {}, deadline)
            owner_record = launch('owner', owner_command, 360)
            outcome = _read(control / 'owner-outcome.json')
            _fields(outcome, {'schema', 'status', 'run_id', 'report', 'error_path', 'qualification_claims'}, 'Owner outcome')
            if (outcome['schema'] != 'memory-family-source-owner-outcome-v2'
                    or outcome['status'] != 'recorded' or outcome['run_id'] != job['run_id']
                    or outcome['error_path'] is not None or outcome['qualification_claims'] is not False
                    or type(outcome['report']) is not dict
                    or _read(Path(job['paths']['raw']) / 'worker-report.json') != outcome['report']):
                raise ValueError('Failed/missing closed owner outcome forbids raw audit')
            case_id = job['case']['case_id']
            snapshot = _descriptor(Path(job['paths']['snapshot']), output,
                logical=f'cases/{case_id}/source/snapshots/initial.snp')
            from scripts import memory_family_raw_audit_v4 as audit
            from scripts import memory_family_producer_v4 as producer
            raw = Path(job['paths']['raw'])
            before = audit._inventory(raw, 'source', deadline)
            (control / 'audit').mkdir(exist_ok=False)
            _, audit_command = _commands(job, control, snapshot, deadline)
            audit_record = launch('audit', audit_command, min(180, deadline - _clock() - 20))
            public_result = _read(control / 'audit.stdout')
            raw_audit = Path(public_result['path'])
            if raw_audit != control / 'audit' / (job['run_id'] + '.raw-audit.json'):
                raise ValueError('Independent raw auditor returned another attempt')
            cleanup = {'schema': 'memory-family-source-cleanup-v2', 'run_id': job['run_id'],
                'owner_supervisor': _descriptor(control / 'owner-supervisor.json', output),
                'owner_outcome': _descriptor(control / 'owner-outcome.json', output),
                'audit_supervisor': _descriptor(control / 'audit-supervisor.json', output),
                'tree_drained': True, 'accounting_complete': True,
                'measurement_scope': 'owner and independent audit, including supervisor/reap/drain'}
            _write(control / 'cleanup.json', cleanup, budget)
            recheck()
            if audit._inventory(raw, 'source', deadline) != before:
                raise ValueError('Raw bytes changed during independent audit')
            roles = {'job': 'job.json', 'supervisor': 'owner-supervisor.json',
                'stdout': 'owner.stdout', 'stderr': 'owner.stderr', 'cleanup': 'cleanup.json'}
            controls = {k: _descriptor(control / name, output) for k, name in roles.items()}
            controls['audit'] = _descriptor(raw_audit, output)
            registration = {'schema': 'memory-family-source-finalization-registration-v4',
                'protocol_sha256': owner.PROTOCOL_SHA256, 'case': job['case'], 'run_id': job['run_id'],
                'owner_source_sha256': job['source_identity_sha256'], 'snapshot': snapshot,
                'raw_audit': controls['audit'], 'owner_record': _descriptor(Path(job['paths']['owner']),
                    output, logical=f'cases/{case_id}/source/owner.json'),
                'controls': controls, 'claims': copy.deepcopy(owner.PROTOCOL['claims'])}
            _write(control / 'terminal-export.json', registration, budget)
            registration_descriptor = _descriptor(control / 'terminal-export.json', output)
            request = dict(evidence_root=output, registration=registration_descriptor,
                           case_id=case_id, deadline=min(deadline - 10, time.monotonic() + 299))
            recheck()
            producer.seal_compact_source(**request)
            recheck()
            sealed = producer.read_sealed_source(**request)
            recheck()
            if audit._inventory(raw, 'source', deadline) != before:
                raise ValueError('Raw bytes changed during preservation')
            report.update(status='preserved-awaiting-lifetime-reconciliation',
                registration=registration_descriptor,
                preservation={'stored_fields': list(__import__('scripts.memory_family_compact_v4', fromlist=['RETAINED']).RETAINED),
                    'original_row_commitments_equal': sealed['conversion']['compact_trace_digest'] == sealed['conversion']['legacy_trace_digest'],
                    'omissions': 'Full cameras, latency and step_latency are not all retained compact fields; raw remains authoritative',
                    'raw_inventory_unchanged': True, 'source_raw_nonempty': bool(before)})
        except BaseException as exc:
            report['status'] = 'stopped'
            report['error'] = {'type': type(exc).__name__, 'message': str(exc)[:2048]}
            quarantine_published(exc)
        finally:
            # Like pilot.py, the receipt explicitly excludes its own write and
            # lease release. Only the externally pinned lifetime owner can close it.
            try:
                check()
            except BaseException as exc:
                report['status'] = 'stopped'
                report['error'] = {'type': type(exc).__name__, 'message': str(exc)[:2048]}
                quarantine_published(exc)
            report['phase_cpu_seconds_observed'] = _cpu_meter() - cpu_started
            report['phase_cpu_seconds'] = report['phase_cpu_seconds_observed'] if report['accounting_complete'] else None
            report['elapsed_seconds'] = _clock() - started
            report['unmetered_tail'] = 'terminal serialization/write/fsync, input release, lease release and process return; external lifetime reconciliation required'
            try:
                _write(control / 'parent-terminal.json', report, budget)
                check()
            except BaseException as exc:
                quarantine_published(exc)
                raise
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('verify', 'execute'), default='verify')
    parser.add_argument('--freeze', required=True, type=Path)
    parser.add_argument('--expected-freeze-sha256', required=True)
    parser.add_argument('--go', type=Path)
    parser.add_argument('--expected-go-sha256')
    args = parser.parse_args(argv)
    if args.mode == 'verify':
        result = verify_freeze(args.freeze, args.expected_freeze_sha256)
    else:
        result = execute_freeze(args.freeze, args.expected_freeze_sha256,
            go_path=args.go, expected_go_sha256=args.expected_go_sha256)
    # Avoid printing a full runtime/input roster into the caller's logs.
    print(memory.canonical_bytes({k: v for k, v in result.items() if k != 'freeze'}).decode())
    return 0 if result['status'] != 'stopped' else 1


if __name__ == '__main__':
    raise SystemExit(main())
