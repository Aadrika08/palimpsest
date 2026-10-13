"""Source-only post-close compact sealing; no owner launch or raw deletion."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
import copy
import ctypes
import sys
import hashlib
import os
from pathlib import Path
import stat
import time

from palimpsest import artifacts, memory, memory_decision_world as world, snapshots
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_raw_audit_v4 as audit
from scripts import memory_family_oracle_admission_v3 as legacy
from scripts import memory_family_oracle_admission_v4 as pair

PROTOCOL = compact.PROTOCOL
MiB = compact.MiB
CONTROL_ROLES = {'job', 'supervisor', 'stdout', 'stderr', 'cleanup', 'audit'}


class SealIndeterminate(RuntimeError):
    """Output evidence remains quarantined or quarantine durability is unknown."""


def _descriptor(path, payload):
    return {'path': path, 'size_bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}


def _canonical(payload, fields, label):
    value = artifacts._json(payload)
    compact._fields(value, fields, label)
    if payload != memory.canonical_bytes(value):
        raise ValueError(f'{label} must be canonical JSON')
    return value


def _inputs(root, descriptor, case_id, deadline, lifetime):
    audit._public_deadline(deadline)
    _, payload, check = lifetime.enter_context(compact.bound_payload(
        root, descriptor, MiB, deadline))
    checks = [check]
    contract = _canonical(payload, PROTOCOL['source_finalization']['registration_keys'],
                          'Source terminal export')
    case = world.validate_case(copy.deepcopy(contract['case']))
    run_id = pair._run_id(contract['run_id'])
    if (case['case_id'] != case_id or case['version'] != 3
            or case['split'] != 'development'
            or contract['schema'] != 'memory-family-source-finalization-registration-v4'
            or contract['protocol_sha256'] != compact.PROTOCOL_SHA256
            or memory.canonical_bytes(contract['claims']) != memory.canonical_bytes(PROTOCOL['claims'])):
        raise ValueError('Source terminal export identity differs')
    compact._digest(contract['owner_source_sha256'])
    compact._fields(contract['controls'], CONTROL_ROLES, 'Source owner controls')
    if contract['controls']['audit'] != contract['raw_audit']:
        raise ValueError('Raw audit must occupy the existing independent owner-audit slot')
    external = [descriptor, *contract['controls'].values()]
    paths = [value['path'] for value in external]
    if len(set(paths)) != len(paths):
        raise ValueError('Input descriptors must name distinct files')
    if any(path.startswith(('cases/', '.pending/')) for path in paths):
        raise ValueError('Control/export/raw-audit inputs must be outside the staged case')
    control_sizes = [descriptor['size_bytes']]
    for role, value in contract['controls'].items():
        _, _, recheck = lifetime.enter_context(compact.bound_payload(
            root, value, MiB, deadline, allow_empty=role in ('stdout', 'stderr')))
        checks.append(recheck)
        if role not in ('stdout', 'stderr', 'audit'):
            control_sizes.append(value['size_bytes'])
    owner_descriptor = contract['owner_record']
    if owner_descriptor['path'] != f'cases/{case_id}/source/owner.json':
        raise ValueError('Owner record is outside its sole staged source path')
    _, owner_bytes, check = lifetime.enter_context(compact.bound_payload(
        root, owner_descriptor, MiB, deadline, source_case=case_id))
    checks.append(check)
    owner = _canonical(owner_bytes, {'schema', 'case_id', 'run_id',
                                     'owner_source_sha256', 'claims'}, 'Source owner record')
    if (owner['schema'] != 'memory-family-source-owner-v4'
            or owner['run_id'] != run_id or owner['case_id'] != case_id
            or owner['owner_source_sha256'] != contract['owner_source_sha256']
            or memory.canonical_bytes(owner['claims']) != memory.canonical_bytes(PROTOCOL['claims'])):
        raise ValueError('Source owner record differs from the terminal export')
    snapshot = contract['snapshot']
    if snapshot['path'] != f'cases/{case_id}/source/snapshots/initial.snp':
        raise ValueError('Snapshot is outside its sole staged source path')
    snapshot_fd, snapshot_bytes, check = lifetime.enter_context(compact.bound_payload(
        root, snapshot, compact.SNAPSHOT_MAX_BYTES, deadline, source_case=case_id))
    checks.append(check)
    _, raw_bytes, check = lifetime.enter_context(compact.bound_payload(
        root, contract['raw_audit'], audit.RAW_CONTRACT['receipt_max_bytes'], deadline))
    checks.append(check)
    raw_receipt = artifacts._json(raw_bytes)
    audit._validate_receipt_shape(raw_receipt)
    if raw_receipt['snapshot_reference'] != snapshot:
        raise ValueError('Raw receipt binds another source snapshot')
    return contract, case, run_id, raw_receipt, raw_bytes, snapshot_fd, checks, sum(control_sizes)


@contextmanager
def _source_directory(root, case_id, *, check_exit=True, publication=None):
    memory._id(case_id)
    if not compact._PATH_COMPONENT.fullmatch(case_id):
        raise ValueError('Invalid registered source case')
    root = artifacts._safe_path(root)
    parts = ('.pending', case_id, 'source')
    opened = []
    identities = []
    def identity(value):
        return value.st_dev, value.st_ino, value.st_mode
    try:
        opened.append(os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
        identities.append(identity(os.fstat(opened[-1])))
        for name in parts:
            opened.append(os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                  dir_fd=opened[-1]))
            identities.append(identity(os.fstat(opened[-1])))
        def recheck():
            for index, expected in enumerate(identities):
                named = (root.lstat() if index == 0 else os.stat(
                    parts[index - 1], dir_fd=opened[index - 1], follow_symlinks=False))
                if identity(os.fstat(opened[index])) != expected or identity(named) != expected:
                    raise RuntimeError('Source publication ancestor replaced')
        recheck()
        yield opened[-1], opened[-2], recheck
        if check_exit:
            recheck()
    finally:
        first_error = None
        for fd in reversed(opened):
            try:
                os.close(fd)
            except OSError as error:
                if publication is not None and publication['committed']:
                    publication['teardown_errors'].append(type(error).__name__)
                elif first_error is None:
                    first_error = error
        if first_error is not None:
            raise first_error



def _case_tree(case_fd, run_id=None):
    if set(os.listdir(case_fd)) != {'source', '.raw'}:
        raise ValueError('Source stage contains unaccounted case entries')
    raw = os.open('.raw', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=case_fd)
    try:
        names = os.listdir(raw)
        if len(names) != 1:
            raise ValueError('Source stage contains unaccounted raw-parent entries')
        pair._run_id(names[0])
        if run_id is not None and names[0] != run_id:
            raise ValueError('Source stage belongs to another raw owner')
    finally:
        os.close(raw)


def _readonly_source_namespace(lifetime, source_fd, case_fd, run_id):
    if set(os.listdir(source_fd)) != {'snapshots', 'owner.json',
            'worker-report.json', 'recording', 'commit.json'}:
        raise ValueError('Source lacks the exact sealed namespace')
    source_before = compact._file_identity(os.fstat(source_fd))
    case_before = compact._file_identity(os.fstat(case_fd))
    def recheck():
        if (compact._file_identity(os.fstat(source_fd)) != source_before
                or compact._file_identity(os.fstat(case_fd)) != case_before
                or set(os.listdir(source_fd)) != {'snapshots', 'owner.json',
                    'worker-report.json', 'recording', 'commit.json'}):
            raise RuntimeError('Sealed source/case namespace changed while read')
        _case_tree(case_fd, run_id)
    recheck()
    lifetime.callback(recheck)


def _rename_noreplace(directory):
    if sys.platform != 'linux':
        raise NotImplementedError('Source marker publication requires Linux renameat2')
    libc = ctypes.CDLL(None, use_errno=True)
    try:
        rename = libc.renameat2
    except AttributeError as error:
        raise NotImplementedError('libc does not provide renameat2') from error
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                       ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(directory, b'.commit.tmp', directory, b'commit.json', 1) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))


def _bind_raw_inventory(lifetime, root, run, case_id, run_id, inventory, deadline):
    checks = []
    for value in inventory:
        _, _, check = lifetime.enter_context(compact.bound_payload(
            root, value, audit._file_limit(Path(value['path']), 'source'), deadline,
            source_case=case_id, raw_run=run_id))
        checks.append(check)
    def recheck():
        if audit._inventory(run, 'source', deadline) != inventory:
            raise RuntimeError('Raw source namespace or bytes changed while held')
    recheck()
    lifetime.callback(recheck)
    checks.append(recheck)
    return checks

def _write_file(directory, name, payload):
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                 0o600, dir_fd=directory)
    try:
        view = memoryview(payload)
        while view:
            count = os.write(fd, view)
            if count < 1:
                raise OSError('Source publication write made no progress')
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_file(directory, name, maximum, *, lifetime=None, deadline=None):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    retained = False
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
            raise ValueError('Source output is aliased or exceeds its limit')
        payload = bytearray()
        while len(payload) <= maximum:
            block = os.read(fd, min(MiB, maximum + 1 - len(payload)))
            if not block:
                break
            payload.extend(block)
        if (len(payload) > maximum or compact._file_identity(before) != compact._file_identity(os.fstat(fd))
                or compact._file_identity(before) != compact._file_identity(
                    os.stat(name, dir_fd=directory, follow_symlinks=False))):
            raise RuntimeError('Source output changed while read')
        payload = bytes(payload)
        if lifetime is not None:
            parent = os.dup(directory)
            def recheck():
                if (compact._file_identity(before) != compact._file_identity(os.fstat(fd))
                        or compact._file_identity(before) != compact._file_identity(
                            os.stat(name, dir_fd=parent, follow_symlinks=False))):
                    raise RuntimeError('Sealed output identity changed while held')
                os.lseek(fd, 0, os.SEEK_SET)
                repeated = bytearray()
                while len(repeated) <= maximum:
                    if deadline is not None:
                        audit._deadline(deadline)
                    block = os.read(fd, min(MiB, maximum + 1 - len(repeated)))
                    if not block:
                        break
                    repeated.extend(block)
                if bytes(repeated) != payload or compact._file_identity(before) != compact._file_identity(os.fstat(fd)):
                    raise RuntimeError('Sealed output bytes changed while held')
            lifetime.callback(os.close, parent)
            lifetime.callback(os.close, fd)
            lifetime.callback(recheck)
            retained = True
        return payload
    finally:
        if not retained:
            os.close(fd)


def _hold_directory(lifetime, parent, name, fd):
    before = compact._file_identity(os.fstat(fd))
    def recheck():
        if (compact._file_identity(os.fstat(fd)) != before
                or compact._file_identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != before):
            raise RuntimeError('Sealed output directory edge changed while held')
    lifetime.callback(os.close, fd)
    lifetime.callback(recheck)


def _disk_bundle(source_fd, *, extras, lifetime=None, deadline=None):
    if set(os.listdir(source_fd)) != {'snapshots', 'owner.json', 'worker-report.json', 'recording', *extras}:
        raise ValueError('Source output contains unregistered files')
    recording = os.open('recording', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
    if lifetime is not None:
        _hold_directory(lifetime, source_fd, 'recording', recording)
    chunks = None
    try:
        names = set(os.listdir(recording))
        metadata = {'manifest.json', 'legacy-manifest.json', 'legacy-events.jsonl',
                    'chunk-index.json', 'audit-frames.npz'}
        allowed = metadata | {'chunks', 'raw-audit.json', 'conversion.json'}
        if names - allowed or not metadata | {'chunks', 'raw-audit.json'} <= names:
            raise ValueError('Source recording contains unregistered or missing files')
        maxima = {'manifest.json': artifacts.MAX_MANIFEST, 'legacy-manifest.json': artifacts.MAX_MANIFEST,
                  'legacy-events.jsonl': 7 * MiB, 'chunk-index.json': MiB,
                  'audit-frames.npz': PROTOCOL['recordings']['source']['audit_frames_max_bytes'] + MiB}
        bundle = {name: _read_file(recording, name, maxima[name], lifetime=lifetime, deadline=deadline) for name in metadata}
        chunks = os.open('chunks', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=recording)
        if lifetime is not None:
            _hold_directory(lifetime, recording, 'chunks', chunks)
        index = artifacts._json(bundle['chunk-index.json'])
        if type(index.get('chunks')) is not list or not 1 <= len(index['chunks']) <= 38:
            raise ValueError('Source chunk count exceeds its frozen ceiling')
        expected = {f'{i:06d}.npz' for i in range(len(index['chunks']))}
        if set(os.listdir(chunks)) != expected:
            raise ValueError('Source chunk tree differs from its exact index')
        for name in sorted(expected):
            bundle[f'chunks/{name}'] = _read_file(chunks, name,
                compact.CHUNK_ROWS * PROTOCOL['row']['bytes_per_tick'] + MiB,
                lifetime=lifetime, deadline=deadline)
            if sum(map(len, bundle.values())) > PROTOCOL['recordings']['source']['ceiling_bytes']:
                raise ValueError('Source bundle exceeds its aggregate ceiling before decode')
        snapshots_fd = os.open('snapshots', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
        if lifetime is not None:
            _hold_directory(lifetime, source_fd, 'snapshots', snapshots_fd)
        try:
            if set(os.listdir(snapshots_fd)) != {'initial.snp'}:
                raise ValueError('Source contains duplicate or unregistered snapshots')
        finally:
            if lifetime is None:
                os.close(snapshots_fd)
        return bundle
    finally:
        if lifetime is None:
            if chunks is not None:
                os.close(chunks)
            os.close(recording)


def _prove(raw_data, bundle, receipt):
    import numpy as np
    read = compact.read_compact(bundle, raw_audit_receipt=receipt)
    if memory.canonical_bytes(read['manifest']['claims']) != memory.canonical_bytes(PROTOCOL['claims']):
        raise ValueError('Raw-to-compact claims differ')
    raw_rows = raw_data['rows']
    trace, row_sequence, camera_sequence = hashlib.sha256(), hashlib.sha256(), hashlib.sha256()
    if len(raw_rows) != len(read['rows']):
        raise ValueError('Raw-to-compact row count differs')
    for raw_row, converted in zip(raw_rows, read['rows']):
        for key in ('episode', 'tick', *compact.RETAINED):
            left, right = raw_row[key], converted[key]
            if key in ('episode', 'tick'):
                equal = left == right
            else:
                equal = left.dtype == right.dtype and left.shape == right.shape and left.tobytes() == right.tobytes()
            if not equal:
                raise ValueError(f'Raw-to-compact retained value differs: {key}')
        row_hex = snapshots.state_digest({key: value for key, value in raw_row.items()
                                        if key not in ('latency', 'step_latency')})
        row_digest = bytes.fromhex(row_hex)
        trace.update(row_hex.encode('ascii'))
        row_sequence.update(row_digest)
        if converted['row_digest'].tobytes() != row_digest:
            raise ValueError('Raw-to-compact legacy row digest differs')
        for name in compact.CAMERAS:
            digest = bytes.fromhex(snapshots.state_digest(raw_row[name]))
            camera_sequence.update(digest)
            if converted[f'{name}_sha256'].tobytes() != digest:
                raise ValueError('Raw-to-compact camera digest differs')
    if (read['trace_digest'] != trace.hexdigest()
            or read['manifest']['row_sequence_sha256'] != row_sequence.hexdigest()
            or row_sequence.hexdigest() != receipt['row_sequence_sha256']
            or read['manifest']['camera_sequence_sha256'] != camera_sequence.hexdigest()
            or camera_sequence.hexdigest() != receipt['camera_sequence_sha256']):
        raise ValueError('Raw-to-compact independent digest proof differs')
    for raw_path, compact_path, maximum in (
            ('manifest.json', 'legacy-manifest.json', MiB),
            ('events.jsonl', 'legacy-events.jsonl', 7 * MiB)):
        if artifacts._read(raw_data['run'] / 'recording' / raw_path, maximum) != bundle[compact_path]:
            raise ValueError('Raw-to-compact legacy bytes differ')
    for tick, frames in read['selected_frames'].items():
        raw = next(row for row in raw_data['rows'] if row['tick'] == tick)
        for name, frame in frames.items():
            if not np.array_equal(raw[name], frame):
                raise ValueError('Raw-to-compact selected frame differs')
    projection = pair._projection(read['rows'])
    if memory.sha256(projection) != receipt['oracle_result']['rows_sha256']:
        raise ValueError('Raw-to-compact oracle projection differs')
    return read


def _bounds(bundle, receipt_bytes, conversion_bytes, support_bytes, control_bytes, marker_bytes):
    read = compact.read_compact(bundle, raw_audit_receipt=artifacts._json(receipt_bytes))
    # The reader accounts numeric/container bytes; receipts add only overhead.
    dense = len(read['rows']) * PROTOCOL['row']['bytes_per_tick']
    frames = len(read['selected_frames']) * 98_304
    overhead = sum(map(len, bundle.values())) - len(bundle['legacy-events.jsonl']) - dense - frames
    extra = len(receipt_bytes) + len(conversion_bytes)
    compact.validate_read_limits('source', row_count=len(read['rows']),
        total_bytes=sum(map(len, bundle.values())) + extra, overhead_bytes=overhead + extra)
    if support_bytes + control_bytes + marker_bytes > MiB:
        raise ValueError('Owner support and control exceeds its combined MiB')


def _raw_request(root, contract, case_id, run_id, deadline):
    return dict(run_path=Path(root) / '.pending' / case_id / '.raw' / run_id,
        receipt_root=(Path(root) / contract['raw_audit']['path']).parent,
        run_id=run_id, case_id=case_id, operation='source', condition=None,
        source_run_id=None, source_snapshot_sha256=None,
        source_identity_sha256=contract['owner_source_sha256'], deadline=deadline,
        evidence_root=root, snapshot_reference=contract['snapshot'])


def _prepare_compact_source(evidence_root, registration, *, case_id, deadline):
    """Seal one staged source; retain all raw files and all false claims."""
    with ExitStack() as lifetime:
        values = _inputs(evidence_root, registration, case_id, deadline, lifetime)
        contract, case, run_id, receipt, receipt_bytes, snapshot_fd, checks, control_bytes = values
        root = Path(evidence_root)
        raw_request = _raw_request(root, contract, case_id, run_id, deadline)
        if audit.validate_raw_receipt(**raw_request) != receipt:
            raise ValueError('Separate raw-audit receipt differs from current inputs')
        raw_data = legacy._read_run({'run_id': run_id, 'run': raw_request['run_path']}, deadline)
        raw_inventory = audit._inventory(raw_request['run_path'], 'source', deadline)
        checks.extend(_bind_raw_inventory(lifetime, root, raw_request['run_path'],
            case_id, run_id, raw_inventory, deadline))
        worker = artifacts._read(raw_request['run_path'] / 'worker-report.json', MiB)
        snapshot = snapshots.read_snapshot(Path(f'/proc/self/fd/{snapshot_fd}'))
        reference = {'kind': 'source', 'source_run_id': run_id,
                     'source_receipt_sha256': None, **contract['snapshot']}
        bundle = compact.convert_synthetic(run_id=run_id, case_id=case_id,
            operation='source', condition=None, rows=raw_data['rows'],
            legacy_manifest_bytes=artifacts._read(raw_request['run_path'] / 'recording/manifest.json', MiB),
            legacy_events_bytes=artifacts._read(raw_request['run_path'] / 'recording/events.jsonl', 7 * MiB),
            snapshot_reference=reference, snapshot_event_prefix=snapshot['application']['event_prefix'],
            raw_audit_receipt=receipt)
        read = _prove(raw_data, bundle, receipt)
        inventory = [_descriptor(f'recording/{path}', payload) for path, payload in bundle.items()]
        inventory.extend([_descriptor('recording/raw-audit.json', receipt_bytes), contract['snapshot']])
        support = [_descriptor('worker-report.json', worker),
                   {**contract['owner_record'], 'path': 'owner.json'}]
        conversion = {
            'schema': 'memory-family-compact-conversion-v1', 'protocol_sha256': compact.PROTOCOL_SHA256,
            'run_id': run_id, 'case_id': case_id, 'operation': 'source', 'condition': None,
            'raw_audit': copy.deepcopy(contract['raw_audit']),
            'source_identity': audit.canonical_source_identity(contract['owner_source_sha256']),
            'legacy_trace_digest': read['trace_digest'], 'compact_trace_digest': read['trace_digest'],
            'compact_manifest': _descriptor('manifest.json', bundle['manifest.json']),
            'inventory': sorted(inventory, key=lambda value: value['path']),
            'support': sorted(support, key=lambda value: value['path']),
            'registration': copy.deepcopy(registration), 'claims': copy.deepcopy(PROTOCOL['claims']),
        }
        conversion_bytes = memory.canonical_bytes(conversion)
        marker = {
            'schema': 'memory-family-compact-source-commit-v1', 'protocol_sha256': compact.PROTOCOL_SHA256,
            'case_id': case_id, 'run_id': run_id,
            'conversion': _descriptor(f'cases/{case_id}/source/recording/conversion.json', conversion_bytes),
            'claims': copy.deepcopy(PROTOCOL['claims']),
        }
        marker_bytes = memory.canonical_bytes(marker)
        _bounds(bundle, receipt_bytes, conversion_bytes, sum(row['size_bytes'] for row in support), control_bytes, len(marker_bytes))
        # Raw worker report occupies the sole existing scratch entry; numeric conversion is in memory.
        if len(worker) > PROTOCOL['storage']['transient']['converter_scratch_bytes']:
            raise ValueError('Raw report exceeds sole converter scratch allowance')
        source_fd, case_fd, output_check = lifetime.enter_context(_source_directory(root, case_id))
        if ('quarantine.json' in os.listdir(case_fd)
                or set(os.listdir(source_fd)) != {'snapshots', 'owner.json'}):
            raise FileExistsError('Source has a prior seal, candidate or quarantine')
        recording = chunks = None
        started = False
        try:
            _case_tree(case_fd, run_id)
            for check in checks:
                check()
            output_check()
            os.mkdir('recording', 0o700, dir_fd=source_fd)
            started = True
            recording = os.open('recording', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
            os.mkdir('chunks', 0o700, dir_fd=recording)
            chunks = os.open('chunks', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=recording)
            for path, payload in bundle.items():
                audit._deadline(deadline)
                _write_file(chunks if path.startswith('chunks/') else recording,
                            path.removeprefix('chunks/'), payload)
            _write_file(recording, 'raw-audit.json', receipt_bytes)
            _write_file(source_fd, 'worker-report.json', worker)
            disk = _disk_bundle(source_fd, extras=set())
            if disk != bundle:
                raise ValueError('Disk compact candidate differs from converted bytes')
            _prove(raw_data, disk, receipt)
            if audit._inventory(raw_request['run_path'], 'source', deadline) != raw_inventory:
                raise RuntimeError('Raw source changed before seal')
            audit.validate_raw_receipt(**raw_request)
            for check in checks:
                check()
            output_check()
            for fd in (chunks, recording, source_fd, case_fd):
                os.fsync(fd)
            _write_file(recording, 'conversion.json', conversion_bytes)
            os.fsync(recording)
            for check in checks:
                check()
            output_check()
            if _disk_bundle(source_fd, extras=set()) != bundle:
                raise RuntimeError('Compact source changed before marker publication')
            if (_read_file(source_fd, 'worker-report.json', MiB) != worker
                    or _read_file(recording, 'raw-audit.json', MiB) != receipt_bytes
                    or _read_file(recording, 'conversion.json', MiB) != conversion_bytes):
                raise RuntimeError('Source support or receipt changed before commit')
            _case_tree(case_fd, run_id)
            audit._deadline(deadline)
            _write_file(source_fd, '.commit.tmp', marker_bytes)
            os.fsync(source_fd)
            os.fsync(case_fd)
            final_bundle = _disk_bundle(source_fd, extras={'.commit.tmp'},
                lifetime=lifetime, deadline=deadline)
            if final_bundle != bundle:
                raise RuntimeError('Prepared source output differs before publication')
            _prove(raw_data, final_bundle, receipt)
            for directory, name, expected in (
                    (source_fd, 'worker-report.json', worker),
                    (recording, 'raw-audit.json', receipt_bytes),
                    (recording, 'conversion.json', conversion_bytes),
                    (source_fd, '.commit.tmp', marker_bytes)):
                if _read_file(directory, name, MiB, lifetime=lifetime, deadline=deadline) != expected:
                    raise RuntimeError('Prepared source support or marker differs')
            for check in checks:
                check()
            output_check()
        except BaseException as error:
            if started:
                try:
                    quarantine = memory.canonical_bytes({
                        'schema': 'memory-family-source-quarantine-v1', 'case_id': case_id,
                        'run_id': run_id, 'error_type': type(error).__name__,
                        'claims': copy.deepcopy(PROTOCOL['claims'])})
                    _write_file(case_fd, 'quarantine.json', quarantine)
                    os.fsync(case_fd)
                except BaseException as quarantine_error:
                    raise SealIndeterminate('Source quarantine durability is indeterminate') from quarantine_error
            raise
        finally:
            if chunks is not None:
                os.close(chunks)
            if recording is not None:
                os.close(recording)
    return {'case_id': case_id, 'run_id': run_id, 'conversion': marker['conversion'],
            'claims': copy.deepcopy(PROTOCOL['claims'])}



def seal_compact_source(evidence_root, registration, *, case_id, deadline):
    # Keep the case descriptor through input-context exit errors as well as writes.
    publication = {'committed': False, 'teardown_errors': []}
    with _source_directory(evidence_root, case_id, check_exit=False,
                           publication=publication) as (source_fd, case_fd, recheck):
        if ('quarantine.json' in os.listdir(case_fd)
                or set(os.listdir(source_fd)) != {'snapshots', 'owner.json'}):
            raise FileExistsError('Source has a prior seal, candidate or quarantine')
        _case_tree(case_fd)
        try:
            result = _prepare_compact_source(evidence_root, registration,
                                          case_id=case_id, deadline=deadline)
            recheck()
            _case_tree(case_fd, result['run_id'])
            audit._deadline(deadline)
            result['descriptor_teardown_errors'] = publication['teardown_errors']
            _rename_noreplace(source_fd)
            publication['committed'] = True
            return result
        except BaseException as error:
            if 'recording' in os.listdir(source_fd) and 'quarantine.json' not in os.listdir(case_fd):
                try:
                    _write_file(case_fd, 'quarantine.json', memory.canonical_bytes({
                        'schema': 'memory-family-source-quarantine-v1', 'case_id': case_id,
                        'error_type': type(error).__name__, 'claims': copy.deepcopy(PROTOCOL['claims'])}))
                    os.fsync(case_fd)
                except BaseException as quarantine_error:
                    raise SealIndeterminate('Source quarantine durability is indeterminate') from quarantine_error
            raise

def read_sealed_source(evidence_root, registration, *, case_id, deadline):
    """Require the staged source marker and revalidate every sealed payload."""
    with ExitStack() as lifetime:
        contract, case, run_id, receipt, raw_bytes, _, checks, control_bytes = _inputs(
            evidence_root, registration, case_id, deadline, lifetime)
        source_fd, case_fd, output_check = lifetime.enter_context(_source_directory(evidence_root, case_id))
        _readonly_source_namespace(lifetime, source_fd, case_fd, run_id)
        if 'quarantine.json' in os.listdir(case_fd):
            raise ValueError('Source is quarantined')
        _case_tree(case_fd, run_id)
        marker_bytes = _read_file(source_fd, 'commit.json', MiB, lifetime=lifetime, deadline=deadline)
        marker = _canonical(marker_bytes, PROTOCOL['source_finalization']['marker_keys'], 'Source commit marker')
        recording = os.open('recording', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=source_fd)
        _hold_directory(lifetime, source_fd, 'recording', recording)
        conversion_bytes = _read_file(recording, 'conversion.json', MiB, lifetime=lifetime, deadline=deadline)
        conversion = _canonical(conversion_bytes, PROTOCOL['schemas']['conversion']['exact_keys'], 'Source conversion receipt')
        compact._check_descriptor(marker['conversion'],
            f'cases/{case_id}/source/recording/conversion.json', conversion_bytes)
        for name in ('registration', 'raw_audit', 'compact_manifest'):
            pair._descriptor(conversion[name], f'Source conversion {name}')
        for name in ('inventory', 'support'):
            values = conversion[name]
            if type(values) is not list:
                raise ValueError('Source inventory must be an ordered descriptor list')
            paths = []
            for value in values:
                paths.append(pair._descriptor(value, 'Source inventory entry')['path'])
            if paths != sorted(set(paths)):
                raise ValueError('Source inventory paths must be sorted and distinct')
        if (marker['schema'] != 'memory-family-compact-source-commit-v1'
                or marker['case_id'] != case_id or marker['run_id'] != run_id
                or marker['protocol_sha256'] != compact.PROTOCOL_SHA256
                or memory.canonical_bytes(marker['claims']) != memory.canonical_bytes(PROTOCOL['claims'])
                or marker['conversion'] != _descriptor(f'cases/{case_id}/source/recording/conversion.json', conversion_bytes)
                or conversion['registration'] != registration
                or conversion['raw_audit'] != contract['raw_audit']):
            raise ValueError('Source marker or conversion identity differs')
        disk_raw = _read_file(recording, 'raw-audit.json', MiB, lifetime=lifetime, deadline=deadline)
        if disk_raw != raw_bytes:
            raise ValueError('Sealed raw audit differs from separate publication')
        bundle = _disk_bundle(source_fd, extras={'commit.json'}, lifetime=lifetime, deadline=deadline)
        read = compact.read_compact(bundle, raw_audit_receipt=receipt)
        if (read['manifest']['run_id'] != run_id
                or read['manifest']['case_id'] != case_id
                or read['snapshot_reference'] != {'kind': 'source', 'source_run_id': run_id,
                    'source_receipt_sha256': None, **contract['snapshot']}):
            raise ValueError('Sealed compact source identity differs')
        raw_request = _raw_request(evidence_root, contract, case_id, run_id, deadline)
        checks.extend(_bind_raw_inventory(lifetime, evidence_root, raw_request['run_path'],
            case_id, run_id, receipt['raw_inventory']['files'], deadline))
        if audit.validate_raw_receipt(**raw_request) != receipt:
            raise ValueError('Sealed raw receipt differs from retained raw bytes')
        raw_data = legacy._read_run({'run_id': run_id, 'run': raw_request['run_path']}, deadline)
        _prove(raw_data, bundle, receipt)
        owner = _read_file(source_fd, 'owner.json', MiB, lifetime=lifetime, deadline=deadline)
        worker = _read_file(source_fd, 'worker-report.json', MiB, lifetime=lifetime, deadline=deadline)
        expected = sorted([*[_descriptor(f'recording/{p}', b) for p, b in bundle.items()],
                           _descriptor('recording/raw-audit.json', raw_bytes), contract['snapshot']], key=lambda d: d['path'])
        support = sorted([_descriptor('owner.json', owner), _descriptor('worker-report.json', worker)], key=lambda d: d['path'])
        if (conversion['inventory'] != expected or conversion['support'] != support
                or _descriptor('owner.json', owner) != {**contract['owner_record'], 'path': 'owner.json'}
                or conversion['source_identity'] != audit.canonical_source_identity(contract['owner_source_sha256'])
                or conversion['schema'] != 'memory-family-compact-conversion-v1'
                or conversion['run_id'] != run_id or conversion['case_id'] != case_id
                or conversion['operation'] != 'source' or conversion['condition'] is not None
                or conversion['protocol_sha256'] != compact.PROTOCOL_SHA256
                or memory.canonical_bytes(conversion['claims']) != memory.canonical_bytes(PROTOCOL['claims'])
                or conversion['compact_manifest'] != _descriptor('manifest.json', bundle['manifest.json'])
                or conversion['compact_trace_digest'] != read['trace_digest']
                or conversion['legacy_trace_digest'] != read['trace_digest']):
            raise ValueError('Sealed source inventory or derivation identity differs')
        raw_support = {value['path']: value for value in receipt['raw_inventory']['files']}
        if _descriptor('worker-report.json', worker) != raw_support['worker-report.json']:
            raise ValueError('Retained worker report differs from raw-auditor attestation')
        _bounds(bundle, raw_bytes, conversion_bytes, len(owner) + len(worker), control_bytes, len(marker_bytes))
        for check in checks:
            check()
        output_check()
        return {'read': read, 'conversion': conversion, 'marker': marker}


def prune_raw_source(*args, **kwargs):
    raise PermissionError('Source pruning remains forbidden by the frozen protocol')
