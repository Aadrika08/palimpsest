"""Public, raw-backed numeric preservation; no owner, qualification or pruning.

The unchanged V4 closed-owner export is an input, not a qualified compact seal.
All source/raw/support files stay at their original paths. Only a fresh V2
candidate, its conversion receipt and provisional marker are written here.
"""
from __future__ import annotations

from contextlib import ExitStack
import copy
import os
from pathlib import Path, PurePosixPath

from palimpsest import artifacts, memory, snapshots
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_numeric_preservation_v2 as numeric
from scripts import memory_family_producer_v4 as producer
from scripts import memory_family_raw_audit_v4 as audit
from scripts.memory_directory_census_v1 import directory_names

MiB = compact.MiB
SealIndeterminate = producer.SealIndeterminate
_write_file = producer._write_file
_rename_noreplace = producer._rename_noreplace
_read_file = producer._read_file
RESERVES = {'conversion': 64 * 1024, 'commit': 16 * 1024,
            'quarantine': 8 * 1024, 'future_parent_terminal': 64 * 1024,
            'atomic_commit': 16 * 1024}
CONVERSION_FIELDS = {'schema', 'protocol', 'base_protocol', 'candidate_path',
    'case_id', 'run_id', 'registration', 'raw_audit', 'source_identity',
    'controls', 'additional_controls', 'owner_record', 'worker_report', 'snapshot', 'inventory',
    'legacy_trace_digest', 'compact_trace_digest', 'byte_ledger', 'claims', 'scope'}
MARKER_FIELDS = {'schema', 'protocol', 'candidate_path', 'case_id', 'run_id',
                 'conversion', 'claims', 'status', 'actual_source_qualified'}
STATUS = 'preserved-awaiting-lifetime-reconciliation'


def _protocol():
    """No caller profile or fallback; bind the current immutable new contract."""
    source = numeric.PROTOCOL['source_publication']
    if (source['reserves_bytes'] != RESERVES
            or source['conversion_keys'] != sorted(CONVERSION_FIELDS)
            or source['commit_keys'] != sorted(MARKER_FIELDS)
            or source['candidate_pattern'] != 'numeric-v2/{case_id}/{run_id}'
            or source['stage_peak_max_bytes'] != 640 * MiB
            or source['raw_max_bytes'] != 512 * MiB
            or source['admission_split'] != 'development'
            or source['publication_outcome_verified'] is not False
            or source['independent_finalization_required'] is not True
            or source['status'] != STATUS):
        raise ValueError('Numeric source publication contract differs')
    return compact._descriptor(numeric.PROTOCOL_PATH.relative_to(numeric.ROOT).as_posix(),
                               numeric.PROTOCOL_BYTES)


def _edge(value):
    return value.st_dev, value.st_ino, value.st_mode


def _directory(lifetime, parent, name, *, create=False):
    if create:
        os.mkdir(name, 0o700, dir_fd=parent)
        os.fsync(parent)
    fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
    before = _edge(os.fstat(fd))
    def check():
        if (before != _edge(os.fstat(fd)) or before != _edge(os.stat(
                name, dir_fd=parent, follow_symlinks=False))):
            raise RuntimeError('Numeric output ancestor edge changed')
    lifetime.callback(os.close, fd)
    lifetime.callback(check)
    check()
    return fd


def _names(fd, deadline=None):
    return set(directory_names(fd, max_entries=128, deadline=deadline))


def _output(root, case_id, run_id, lifetime, *, create, deadline):
    root = artifacts._safe_path(root)
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    before = _edge(os.fstat(fd))
    lifetime.callback(os.close, fd)
    def check_root():
        if before != _edge(root.lstat()) or before != _edge(os.fstat(fd)):
            raise RuntimeError('Numeric evidence root replaced')
    lifetime.callback(check_root)
    parent = fd
    ancestors = []
    for name, expected in [('numeric-v2', {case_id}), (case_id, {run_id})]:
        present = name in _names(parent, deadline)
        parent = _directory(lifetime, parent, name, create=create and not present)
        # These prospective ancestors admit exactly the registered case/run.
        if _names(parent, deadline) - expected:
            raise ValueError('Numeric output ancestor contains unregistered entries')
        ancestors.append((parent, expected))
    if create and run_id in _names(parent, deadline):
        raise FileExistsError('Numeric source has a prior output, partial or quarantine')
    result = _directory(lifetime, parent, run_id, create=create)
    _freeze_directory(lifetime, fd, _names(fd, deadline), deadline)
    for ancestor, expected in ancestors:
        _freeze_directory(lifetime, ancestor, expected, deadline)
    def check():
        check_root()
        if _names(parent, deadline) != {run_id}:
            raise RuntimeError('Numeric output run namespace changed')
    lifetime.callback(check)
    return result


def _freeze_directory(lifetime, fd, expected, deadline):
    before = compact._file_identity(os.fstat(fd))
    def check():
        audit._deadline(deadline)
        if before != compact._file_identity(os.fstat(fd)) or _names(fd, deadline) != expected:
            raise RuntimeError('Numeric held directory namespace changed')
    check()
    lifetime.callback(check)
    return check


def _source(lifetime, root, case_id, run_id, deadline):
    source, case, check = lifetime.enter_context(producer._source_directory(root, case_id))
    producer._case_tree(case, run_id)
    _freeze_directory(lifetime, source, {'snapshots', 'owner.json'}, deadline)
    _freeze_directory(lifetime, case, {'source', '.raw'}, deadline)
    snapshots_fd = _directory(lifetime, source, 'snapshots')
    _freeze_directory(lifetime, snapshots_fd, {'initial.snp'}, deadline)
    raw_parent = _directory(lifetime, case, '.raw')
    _freeze_directory(lifetime, raw_parent, {run_id}, deadline)
    return check


def _tree(lifetime, output, expected, deadline, *, preparing=False):
    """Read exact recursive membership and hold every file/edge until teardown."""
    if (len(expected) > 130 or sum(value['size_bytes'] for value in expected.values())
            > 32 * MiB + RESERVES['conversion'] + RESERVES['commit']):
        raise ValueError('Numeric disk inventory exceeds its aggregate predecode bound')
    result = {}
    def walk(fd, prefix):
        children = {}
        for path in expected:
            if path.startswith(prefix):
                tail = path[len(prefix):]
                children.setdefault(tail.split('/')[0], '/' in tail)
        if _names(fd, deadline) != set(children):
            raise ValueError('Numeric output has unknown or missing members')
        # The sole deliberate namespace mutation is our final marker rename.
        # All candidate files and child directories remain witnessed across it.
        if prefix or not preparing:
            _freeze_directory(lifetime, fd, set(children), deadline)
        for name, directory in sorted(children.items()):
            audit._deadline(deadline)
            path = prefix + name
            if directory:
                walk(_directory(lifetime, fd, name), path + '/')
            else:
                result[path] = _read_file(fd, name, 32 * MiB,
                    lifetime=None if preparing and path == '.commit.tmp' else lifetime,
                    deadline=deadline)
                compact._check_descriptor(expected[path], path, result[path])
    walk(output, '')
    return result


def _write_bundle(lifetime, output, bundle, deadline):
    directories = {'': output}
    for path in sorted(bundle):
        parts = PurePosixPath(path).parts
        parent = ''
        for part in parts[:-1]:
            child = parent + part + '/'
            if child not in directories:
                directories[child] = _directory(lifetime, directories[parent], part, create=True)
            parent = child
        audit._deadline(deadline)
        _write_file(directories[parent], parts[-1], bundle[path])
    for fd in reversed(list(directories.values())):
        os.fsync(fd)


def _physical(descriptor, case_id):
    prefix = f'cases/{case_id}/source/'
    path = descriptor['path']
    return (f'.pending/{case_id}/source/' + path[len(prefix):]
            if path.startswith(prefix) else path)


def _external(registration, contract, receipt, case_id, run_id, additional_controls):
    """Unique actual files. Worker is referenced in raw, never copied."""
    worker = next(value for value in receipt['raw_inventory']['files']
                  if value['path'] == 'worker-report.json')
    worker = {**worker, 'path': f'.pending/{case_id}/.raw/{run_id}/worker-report.json'}
    values = [registration, *contract['controls'].values(), contract['owner_record'], worker,
              *additional_controls]
    unique = {}
    for value in values:
        path = _physical(value, case_id)
        if path.startswith('numeric-v2/'):
            raise ValueError('Source input aliases the numeric output namespace')
        normalized = {**value, 'path': path}
        if path in unique and unique[path] != normalized:
            raise ValueError('Conflicting descriptors for one physical input')
        unique[path] = normalized
    return sorted(unique.values(), key=lambda item: item['path']), worker


def _account(bundle, receipt, external, snapshot):
    raw = receipt['raw_inventory']['files']
    raw_bytes = sum(value['size_bytes'] for value in raw)
    if raw_bytes != receipt['raw_inventory']['total_bytes'] or raw_bytes > 512 * MiB:
        raise ValueError('Numeric source raw physical ledger differs or exceeds cap')
    if snapshot['size_bytes'] > 16 * MiB:
        raise ValueError('Numeric source snapshot exceeds its separate cap')
    # The worker's support role consumes compact overhead conservatively. Its
    # physical bytes are already in raw_bytes and are counted once in stage.
    external_bytes = sum(value['size_bytes'] for value in external)
    reserves = sum(RESERVES.values())
    ledger = numeric.account_candidate(bundle, raw_audit_receipt=receipt,
        external_overhead_bytes=external_bytes + reserves)
    raw_paths = {f'.pending/{receipt["case_id"]}/.raw/{receipt["run_id"]}/{value["path"]}'
                 for value in raw}
    physical_external = sum(value['size_bytes'] for value in external
                            if value['path'] not in raw_paths)
    peak = raw_bytes + snapshot['size_bytes'] + ledger['bundle_bytes'] + physical_external + reserves
    if peak > 640 * MiB:
        raise ValueError('Numeric source enclosing stage peak exceeds 640 MiB')
    return {**ledger, 'stage_peak_accounted': False, 'snapshot_accounted': True,
        'raw_bytes': raw_bytes, 'snapshot_bytes': snapshot['size_bytes'],
        'external_physical_bytes_outside_raw': physical_external,
        'external_support_charge_bytes': external_bytes,
        'metadata_reserve_bytes': reserves, 'reserves_bytes': copy.deepcopy(RESERVES),
        'parent_terminal_max_bytes': RESERVES['future_parent_terminal'],
        'known_payload_physical_bytes': peak - reserves,
        'registered_peak_upper_bound_bytes': peak, 'physical_paths_deduplicated': True,
        'physical_domains': {
            'raw': [{**value, 'path': f'.pending/{receipt["case_id"]}/.raw/{receipt["run_id"]}/{value["path"]}'}
                    for value in raw],
            'snapshot': {**snapshot, 'path': _physical(snapshot, receipt['case_id'])},
            'registered_external': copy.deepcopy(external),
            'bundle': [compact._descriptor(f'numeric-v2/{receipt["case_id"]}/{receipt["run_id"]}/{path}',
                                            bundle[path]) for path in sorted(bundle)]},
        'scope': 'candidate, registered export and provided additional controls plus fixed future/atomic reserves; parent must prove complete census and bound terminal; no independent enclosing-stage proof'}


def _scope(read):
    return {**read['preservation'], 'stage_peak_accounted': False,
        'lifetime_reconciled': False, 'numerical_model_qualified': False,
        'publication_outcome_verified': False, 'independent_finalization_required': True,
        'stored_fields': sorted(set(compact.RETAINED) | set(numeric.NUMERIC_FIELDS)),
        'original_row_commitments_equal': True,
        'omissions': 'Full cameras remain omitted except selected pixels; commitments do not reconstruct omitted pixels or authenticate population labels.'}


def _records(registration, contract, receipt, bundle, read, case_id, run_id, additional_controls):
    path = f'numeric-v2/{case_id}/{run_id}'
    external, worker = _external(registration, contract, receipt, case_id, run_id, additional_controls)
    ledger = _account(bundle, receipt, external, contract['snapshot'])
    conversion = {'schema': 'memory-family-numeric-source-conversion-v2',
        'protocol': _protocol(), 'base_protocol': copy.deepcopy(numeric.BASE_PROTOCOL),
        'candidate_path': path, 'case_id': case_id, 'run_id': run_id,
        'registration': copy.deepcopy(registration), 'raw_audit': copy.deepcopy(contract['raw_audit']),
        'source_identity': copy.deepcopy(receipt['source_identity']),
        'controls': copy.deepcopy(contract['controls']), 'owner_record': copy.deepcopy(contract['owner_record']),
        'additional_controls': copy.deepcopy(additional_controls),
        'worker_report': worker, 'snapshot': copy.deepcopy(contract['snapshot']),
        'inventory': [compact._descriptor(name, bundle[name]) for name in sorted(bundle)],
        'legacy_trace_digest': read['trace_digest'], 'compact_trace_digest': read['trace_digest'],
        'byte_ledger': ledger, 'claims': copy.deepcopy(numeric.PROTOCOL['claims']), 'scope': _scope(read)}
    payload = memory.canonical_bytes(conversion)
    if len(payload) > RESERVES['conversion']:
        raise ValueError('Numeric conversion exceeds fixed metadata reserve')
    marker = {'schema': 'memory-family-numeric-source-commit-v2', 'protocol': _protocol(),
        'candidate_path': path, 'case_id': case_id, 'run_id': run_id,
        'conversion': compact._descriptor(path + '/conversion.json', payload),
        'claims': copy.deepcopy(numeric.PROTOCOL['claims']), 'status': STATUS,
        'actual_source_qualified': False}
    marker_bytes = memory.canonical_bytes(marker)
    if len(marker_bytes) > RESERVES['commit']:
        raise ValueError('Numeric marker exceeds fixed metadata reserve')
    return conversion, payload, marker, marker_bytes


def _prove(raw, bundle, receipt, contract, snapshot_fd):
    read = numeric.prove_numeric_preservation(raw, bundle, receipt)
    snapshot = snapshots.read_snapshot(Path(f'/proc/self/fd/{snapshot_fd}'))
    expected = {'kind': 'source', 'source_run_id': contract['run_id'],
                'source_receipt_sha256': None, **contract['snapshot']}
    if (read['snapshot_reference'] != expected or read['base_manifest']['snapshot_event_prefix']
            != snapshot['application']['event_prefix']):
        raise ValueError('Numeric source snapshot reference or event prefix differs from held SNP')
    return read


def _control_descriptor(value, label, *, allow_empty=False):
    compact._fields(value, {'path', 'size_bytes', 'sha256'}, label)
    path = compact._relative(value['path'], label + ' path')
    if PurePosixPath(path).parts[0] in {'.pending', 'cases', 'numeric-v2'}:
        raise ValueError(f'{label} must be outside source/raw/numeric output namespaces')
    minimum = 0 if allow_empty else 1
    if type(value['size_bytes']) is not int or not minimum <= value['size_bytes'] <= MiB:
        raise ValueError(f'Invalid {label} byte size')
    compact._digest(value['sha256'], label + ' SHA-256')
    return path


def _additional(lifetime, root, values, deadline):
    if type(values) not in (list, tuple) or len(values) > 128:
        raise ValueError('Additional numeric controls must be a bounded descriptor sequence')
    result = copy.deepcopy(list(values))
    paths = []
    for value in result:
        paths.append(_control_descriptor(value, 'Additional numeric control', allow_empty=True))
    if paths != sorted(set(paths)):
        raise ValueError('Additional numeric controls must be sorted and distinct')
    for value in result:
        lifetime.enter_context(compact.bound_payload(root, value, MiB, deadline, allow_empty=True))
    return result


def _raw_inputs(lifetime, root, registration, case_id, deadline, additional_controls):
    memory._id(case_id)
    if not compact._PATH_COMPONENT.fullmatch(case_id):
        raise ValueError('Invalid numeric source case identifier')
    _control_descriptor(registration, 'Numeric source registration')
    lifetime.enter_context(compact.bound_payload(numeric.ROOT, _protocol(), MiB, deadline))
    # Legacy _inputs constructs/validates a case before its split check. Refuse
    # protected/nondevelopment metadata before delegating, while holding this
    # original registration descriptor through all subsequent work.
    _, payload, _ = lifetime.enter_context(compact.bound_payload(
        root, registration, MiB, deadline))
    export = producer._canonical(payload,
        producer.PROTOCOL['source_finalization']['registration_keys'], 'Numeric source terminal export')
    case = export['case']
    if (type(case) is not dict or case.get('split') != 'development'
            or type(case.get('version')) is not int or case['version'] != 3
            or case.get('case_id') != case_id):
        raise ValueError('Numeric source registration must name its development V3 case')
    compact._fields(export['controls'], producer.CONTROL_ROLES, 'Numeric source controls')
    for role, descriptor in export['controls'].items():
        _control_descriptor(descriptor, 'Numeric source control ' + role,
                            allow_empty=role in {'stdout', 'stderr'})
    _control_descriptor(export['raw_audit'], 'Numeric source raw-audit control')
    values = producer._inputs(root, registration, case_id, deadline, lifetime)
    contract, case, run_id, receipt, raw_bytes, snapshot_fd, checks, _ = values
    additional = _additional(lifetime, root, additional_controls, deadline)
    _source(lifetime, root, case_id, run_id, deadline)
    request = producer._raw_request(root, contract, case_id, run_id, deadline)
    checks.extend(producer._bind_raw_inventory(lifetime, root, request['run_path'],
        case_id, run_id, receipt['raw_inventory']['files'], deadline))
    if audit.validate_raw_receipt(**request) != receipt:
        raise ValueError('Independent public raw-audit receipt differs')
    raw = producer.legacy._read_run({'run_id': run_id, 'run': request['run_path']}, deadline)
    if not raw['rows']:
        raise ValueError('Public numeric source requires nonempty raw rows')
    return contract, run_id, receipt, snapshot_fd, checks, request, raw, additional


def _quarantine(fd, case_id, run_id, error):
    if 'quarantine.json' not in _names(fd):
        payload = memory.canonical_bytes({'schema': 'memory-family-numeric-source-quarantine-v2',
            'case_id': case_id, 'run_id': run_id, 'error_type': type(error).__name__,
            'actual_source_qualified': False, 'claims': copy.deepcopy(numeric.PROTOCOL['claims'])})
        if len(payload) > RESERVES['quarantine']:
            raise ValueError('Numeric quarantine exceeds fixed reserve')
        _write_file(fd, 'quarantine.json', payload)
    os.fsync(fd)


def _result(read, conversion, marker, conversion_bytes, marker_bytes):
    return {'status': STATUS, 'actual_source_qualified': False,
        'publication_outcome_verified': False, 'independent_finalization_required': True,
        'case_id': marker['case_id'], 'run_id': marker['run_id'],
        'candidate_path': marker['candidate_path'], 'read': read,
        'conversion': conversion, 'marker': marker,
        'commit': compact._descriptor(marker['candidate_path'] + '/commit.json', marker_bytes),
        'byte_ledger': {**conversion['byte_ledger'],
            'actual_conversion_bytes': len(conversion_bytes), 'actual_commit_bytes': len(marker_bytes),
            'observed_physical_bytes_after_publication': conversion['byte_ledger']['known_payload_physical_bytes']
                + len(conversion_bytes) + len(marker_bytes)},
        'claims': copy.deepcopy(numeric.PROTOCOL['claims']), 'preservation': conversion['scope']}


def seal_numeric_source_v2(evidence_root, registration, *, case_id, deadline, additional_controls=()):
    """Write and raw-compare a sole fresh provisional candidate, marker last.

    Witnesses remain held across rename. Any late check/teardown/fsync failure
    refuses the result and quarantines retained evidence, including a marker
    whose durability became indeterminate. No accepted V1 seal is an input.
    """
    _protocol()
    output = rescue = None
    run_id = None
    try:
        with ExitStack() as lifetime:
            contract, run_id, receipt, snapshot_fd, checks, request, raw, additional = _raw_inputs(
                lifetime, evidence_root, registration, case_id, deadline, additional_controls)
            snapshot = snapshots.read_snapshot(Path(f'/proc/self/fd/{snapshot_fd}'))
            base = compact.convert_synthetic(run_id=run_id, case_id=case_id,
                operation='source', condition=None, rows=raw['rows'],
                legacy_manifest_bytes=artifacts._read(request['run_path'] / 'recording/manifest.json', MiB),
                legacy_events_bytes=artifacts._read(request['run_path'] / 'recording/events.jsonl', 7 * MiB),
                snapshot_reference={'kind': 'source', 'source_run_id': run_id,
                    'source_receipt_sha256': None, **contract['snapshot']},
                snapshot_event_prefix=snapshot['application']['event_prefix'], raw_audit_receipt=receipt)
            bundle = numeric.convert_candidate(base, raw['rows'], raw_audit_receipt=receipt)
            read = _prove(raw, bundle, receipt, contract, snapshot_fd)
            conversion, payload, marker, marker_bytes = _records(
                registration, contract, receipt, bundle, read, case_id, run_id, additional)
            for check in checks:
                check()
            output = _output(evidence_root, case_id, run_id, lifetime, create=True, deadline=deadline)
            rescue = os.dup(output)
            _write_bundle(lifetime, output, bundle, deadline)
            _write_file(output, 'conversion.json', payload)
            _write_file(output, '.commit.tmp', marker_bytes)
            os.fsync(output)
            expected = {**{p: compact._descriptor(p, b) for p, b in bundle.items()},
                'conversion.json': compact._descriptor('conversion.json', payload),
                '.commit.tmp': compact._descriptor('.commit.tmp', marker_bytes)}
            disk = _tree(lifetime, output, expected, deadline, preparing=True)
            marker_identity = _edge(os.stat('.commit.tmp', dir_fd=output, follow_symlinks=False))
            disk_bundle = {p: disk[p] for p in bundle}
            read = _prove(raw, disk_bundle, receipt, contract, snapshot_fd)
            if _records(registration, contract, receipt, disk_bundle, read,
                        case_id, run_id, additional) != (conversion, payload, marker, marker_bytes):
                raise ValueError('Actual disk source proof differs from created records')
            if audit.validate_raw_receipt(**request) != receipt:
                raise ValueError('Raw source changed before numeric publication')
            for check in checks:
                check()
            audit._deadline(deadline)
            _rename_noreplace(output)
            os.fsync(output)
            if marker_identity != _edge(os.stat('commit.json', dir_fd=output, follow_symlinks=False)):
                raise RuntimeError('Numeric marker inode changed during publication')
            final_expected = {**expected}
            del final_expected['.commit.tmp']
            final_expected['commit.json'] = compact._descriptor('commit.json', marker_bytes)
            disk = _tree(lifetime, output, final_expected, deadline)
            read = _prove(raw, {p: disk[p] for p in bundle}, receipt, contract, snapshot_fd)
            for check in checks:
                check()
            audit._deadline(deadline)
            result = _result(read, conversion, marker, payload, marker_bytes)
        # No success-shaped return before witness and descriptor teardown.
        os.close(rescue)
        rescue = None
        return result
    except BaseException as error:
        if output is not None:
            try:
                if rescue is not None:
                    # A close that raised after closing requires an identity-safe
                    # reopen; never silently ignore publication teardown errors.
                    try:
                        os.fstat(rescue)
                    except OSError:
                        rescue = None
                if rescue is None:
                    with ExitStack() as recovery:
                        fd = _output(evidence_root, case_id, run_id, recovery,
                                     create=False, deadline=audit.deadline_from_seconds(30))
                        _quarantine(fd, case_id, run_id, error)
                else:
                    _quarantine(rescue, case_id, run_id, error)
            except BaseException as quarantine_error:
                raise SealIndeterminate('Numeric source quarantine durability is indeterminate') from quarantine_error
        raise
    finally:
        if rescue is not None:
            try:
                os.close(rescue)
            except OSError as error:
                raise SealIndeterminate('Numeric source rescue descriptor teardown failed') from error


def read_numeric_source_v2(evidence_root, registration, *, case_id, deadline, additional_controls=()):
    """Repeat stored-field proof under raw custody, without finalizing an attempt.

    If every failure write was unavailable after a marker rename, a failed
    writer can leave a valid marker without durable quarantine. This reader
    verifies current bytes only: publication_outcome_verified remains false,
    independent_finalization_required remains true. It cannot establish that
    writer's process success, resume its attempt, or reconcile its lifetime.
    A present quarantine always makes the exact namespace unreadable here.
    """
    _protocol()
    with ExitStack() as lifetime:
        contract, run_id, receipt, snapshot_fd, checks, request, raw, additional = _raw_inputs(
            lifetime, evidence_root, registration, case_id, deadline, additional_controls)
        output = _output(evidence_root, case_id, run_id, lifetime, create=False, deadline=deadline)
        marker_bytes = _read_file(output, 'commit.json', RESERVES['commit'],
                                 lifetime=lifetime, deadline=deadline)
        marker = producer._canonical(marker_bytes, MARKER_FIELDS, 'Numeric source marker')
        payload = _read_file(output, 'conversion.json', RESERVES['conversion'],
                            lifetime=lifetime, deadline=deadline)
        conversion = producer._canonical(payload, CONVERSION_FIELDS, 'Numeric source conversion')
        inventory = conversion['inventory']
        if type(inventory) is not list or not 1 <= len(inventory) <= 128:
            raise ValueError('Invalid numeric source inventory')
        expected = {}
        for value in inventory:
            producer.pair._descriptor(value, 'Numeric source inventory entry')
            path = compact._relative(value['path'], 'Numeric inventory path')
            if path in expected or path in {'commit.json', 'conversion.json', '.commit.tmp', 'quarantine.json'}:
                raise ValueError('Duplicate or reserved numeric source inventory path')
            expected[path] = value
        if list(expected) != sorted(expected):
            raise ValueError('Numeric source inventory must be sorted')
        disk = _tree(lifetime, output, {**expected,
            'conversion.json': compact._descriptor('conversion.json', payload),
            'commit.json': compact._descriptor('commit.json', marker_bytes)}, deadline)
        bundle = {path: disk[path] for path in expected}
        read = _prove(raw, bundle, receipt, contract, snapshot_fd)
        if _records(registration, contract, receipt, bundle, read, case_id, run_id, additional) != (
                conversion, payload, marker, marker_bytes):
            raise ValueError('Numeric source marker/conversion differs from raw-backed proof')
        for check in checks:
            check()
        audit._deadline(deadline)
        result = _result(read, conversion, marker, payload, marker_bytes)
    return result


def prune_raw_source(*args, **kwargs):
    raise PermissionError('Source pruning remains forbidden for numeric preservation V2')
