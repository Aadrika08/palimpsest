"""Prospective single-condition close; no owner launch, raw deletion or grant.

The public route currently refuses: no independently accepted qualification is
pinned. Private authored seams in tests prove orchestration, never a real model.
"""
from __future__ import annotations

from contextlib import ExitStack
import copy
import hashlib
import os
from pathlib import Path
import stat

from palimpsest import artifacts, memory, memory_decision_world as world, snapshots
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_producer_v4 as source
from scripts import memory_family_raw_audit_v4 as audit
from scripts import memory_family_oracle_admission_v3 as legacy
from scripts import memory_family_oracle_admission_v4 as pair
from scripts import memory_family_oracle_v3 as oracle
from scripts.memory_condition_replay_admission_v1 import (
    qualified_replay as _qualified_replay,
    require_qualification_pin as _require_qualification_pin,
)
from scripts.memory_directory_census_v1 import directory_names

ROOT = Path(__file__).resolve().parents[1]
MiB = compact.MiB
EXTENSION_PATH = 'docs/plans/memory-condition-seal-v1-retained-condition-v1-protocol.json'
REGISTRATION_KEYS = {'schema', 'protocol_sha256', 'extension_sha256', 'case',
    'run_id', 'condition', 'source_run_id', 'owner_source_sha256', 'source',
    'raw_audit', 'owner_record', 'controls', 'history_bundles',
    'prior_own_receipt', 'qualification', 'claims'}
MARKER_KEYS = {'schema', 'protocol_sha256', 'extension_sha256', 'case_id',
    'run_id', 'condition', 'source_run_id', 'conversion', 'snapshot_reference',
    'pair_admission', 'qualification', 'cell_replay', 'claims'}
REPLAY_KEYS = {'schema', 'protocol_sha256', 'case_id', 'run_id', 'operation',
    'trace_digest', 'source_snapshot_reference', 'rows_checked',
    'raw_output_equal', 'action_equal', 'source_endpoint_verified',
    'initial_hidden_sha256', 'final_hidden_sha256', 'claims'}
METADATA = {'manifest.json', 'legacy-manifest.json', 'legacy-events.jsonl',
            'chunk-index.json', 'audit-frames.npz'}


class SealIndeterminate(RuntimeError):
    """A failed attempt, including postcommit failure, never grants admission."""


class _ValidatingStack(ExitStack):
    """Drain every validation context without replacing a body failure."""
    def __exit__(self, error_type, error, traceback):
        try:
            result = super().__exit__(error_type, error, traceback)
        except BaseException as teardown:
            if error is None:
                raise
            error.add_note('Condition custody teardown also failed: '
                           + type(teardown).__name__ + ': ' + str(teardown))
            return False
        return False if error is not None else result


def _claims(value):
    if memory.canonical_bytes(value) != memory.canonical_bytes(compact.PROTOCOL['claims']):
        raise ValueError('Condition claims differ from the all-false contract')


def _canonical(payload, fields, label):
    return source._canonical(payload, fields, label)


def _descriptor(path, payload):
    return source._descriptor(path, payload)


def _production_replay(**values):
    # Loading this module is deliberately lazy: pin admission precedes numerical
    # imports, and the real public consumer is the only default execution route.
    from scripts.memory_family_cell_replay_v4 import replay_compact_cell
    return replay_compact_cell(**values)


def _bind(lifetime, root, value, maximum, deadline, *, allow_empty=False,
          case_id=None):
    if case_id is None or not value['path'].startswith('cases/'):
        return lifetime.enter_context(compact.bound_payload(
            root, value, maximum, deadline, allow_empty=allow_empty))
    portable = pair._descriptor(value, 'Staged condition descriptor')
    prefix = f'cases/{case_id}/'
    if not portable['path'].startswith(prefix):
        raise ValueError('Staged input belongs to another case')
    physical = {**portable, 'path': portable['path'][len(prefix):]}
    return lifetime.enter_context(compact.bound_payload(
        Path(root) / '.pending' / case_id, physical, maximum, deadline,
        allow_empty=allow_empty))


def _extension(lifetime, digest, deadline):
    compact._digest(digest)
    path = ROOT / EXTENSION_PATH
    payload = artifacts._read(path, MiB)
    descriptor = _descriptor(EXTENSION_PATH, payload)
    if descriptor['sha256'] != digest:
        raise ValueError('Condition extension identity differs')
    _, held, check = _bind(lifetime, ROOT, descriptor, MiB, deadline)
    value = artifacts._json(held)
    if (held != memory.canonical_bytes(value)
            or value.get('schema') != 'memory-condition-seal-v1-protocol'
            or value.get('base_protocol_sha256') != compact.PROTOCOL_SHA256
            or value.get('registration_schema') != 'memory-family-condition-finalization-registration-v1'
            or value.get('marker_schema') != 'memory-family-compact-condition-commit-v1'
            or set(value.get('registration_keys', ())) != REGISTRATION_KEYS
            or set(value.get('marker_keys', ())) != MARKER_KEYS):
        raise ValueError('Condition extension contract differs')
    _claims(value['claims'])
    pins = value.get('source_pins')
    if type(pins) is not list or not pins:
        raise ValueError('Condition extension must pin its source closure')
    paths = []
    checks = [check]
    for row in pins:
        pair._descriptor(row, 'Condition extension source')
        paths.append(row['path'])
        checks.append(_bind(lifetime, ROOT, row, 2 * MiB, deadline)[2])
    if paths != sorted(set(paths)) or not {
            'scripts/memory_family_condition_seal_v4.py',
            'scripts/memory_condition_replay_admission_v1.py',
            'docs/plans/memory-condition-seal-v1.md'} <= set(paths):
        raise ValueError('Condition extension source closure differs')
    return checks


def _registration(root, registration, case_id, condition, deadline, lifetime):
    audit._public_deadline(deadline)
    memory._id(case_id)
    if not compact._PATH_COMPONENT.fullmatch(case_id):
        raise ValueError('Invalid condition case identifier')
    if condition not in compact.PROTOCOL['analysis_contract']['conditions']:
        raise ValueError('Unknown condition')
    if registration['path'].startswith(('cases/', '.pending/')):
        raise ValueError('Condition terminal export must be outside its staged case')
    _, payload, check = _bind(lifetime, root, registration, MiB, deadline)
    contract = _canonical(payload, REGISTRATION_KEYS, 'Condition terminal export')
    case = world.validate_case(copy.deepcopy(contract['case']))
    run_id, source_id = pair._run_id(contract['run_id']), pair._run_id(contract['source_run_id'])
    if (contract['schema'] != 'memory-family-condition-finalization-registration-v1'
            or contract['protocol_sha256'] != compact.PROTOCOL_SHA256
            or case['version'] != 3 or case['split'] != 'development'
            or case['case_id'] != case_id or contract['condition'] != condition
            or run_id == source_id):
        raise ValueError('Condition terminal export identity differs')
    _claims(contract['claims'])
    compact._digest(contract['owner_source_sha256'])
    pair._fields(contract['source'], {'registration', 'commit', 'snapshot'}, 'Condition source')
    pair._fields(contract['controls'], source.CONTROL_ROLES, 'Condition controls')
    pair._fields(contract['history_bundles'], {'own', 'swapped'}, 'Condition histories')
    if contract['controls']['audit'] != contract['raw_audit']:
        raise ValueError('Condition raw audit must occupy the independent audit slot')
    base = f'cases/{case_id}'
    for value, expected in (
            (contract['source']['commit'], f'{base}/source/commit.json'),
            (contract['source']['snapshot'], f'{base}/source/snapshots/initial.snp'),
            (contract['owner_record'], f'{base}/conditions/{condition}/owner.json')):
        if pair._descriptor(value, 'Condition canonical descriptor')['path'] != expected:
            raise ValueError('Condition descriptor is outside its canonical path')
    external = [registration, contract['source']['registration'],
                *contract['controls'].values(), *contract['history_bundles'].values(),
                contract['qualification']]
    if contract['prior_own_receipt'] is not None:
        pair._descriptor(contract['prior_own_receipt'], 'Prior own descriptor')
        if condition != 'oracle':
            raise ValueError('Only oracle accepts prior-own evidence')
    elif condition == 'oracle':
        raise ValueError('Oracle requires its existing prior-own evidence')
    paths = []
    for value in external:
        if value in (contract['controls']['stdout'], contract['controls']['stderr']):
            compact._fields(value, compact.DESCRIPTOR_FIELDS, 'Condition log descriptor')
            if type(value['size_bytes']) is not int or not 0 <= value['size_bytes'] <= MiB:
                raise ValueError('Condition log descriptor size differs')
            compact._digest(value['sha256'])
            paths.append(compact._relative(value['path'], 'Condition log path'))
        else:
            paths.append(pair._descriptor(value, 'Condition external descriptor')['path'])
    if len(paths) != len(set(paths)) or any(p.startswith(('cases/', '.pending/')) for p in paths):
        raise ValueError('Condition external inputs must be distinct and outside the case')
    # This pure, non-IO gate precedes snapshot/raw decoding and output changes.
    _require_qualification_pin(contract['qualification'])
    checks = [check, *_extension(lifetime, contract['extension_sha256'], deadline)]
    control_bytes = registration['size_bytes']
    for role, value in contract['controls'].items():
        _, _, check = _bind(lifetime, root, value, MiB, deadline,
                            allow_empty=role in ('stdout', 'stderr'))
        checks.append(check)
        if role not in ('stdout', 'stderr', 'audit'):
            control_bytes += value['size_bytes']
    for value in contract['history_bundles'].values():
        checks.append(_bind(lifetime, root, value, 16 * MiB, deadline)[2])
    if contract['prior_own_receipt'] is not None:
        checks.append(_bind(lifetime, root, contract['prior_own_receipt'], MiB,
                            deadline, case_id=case_id)[2])
    return contract, checks, control_bytes


class _Anchor:
    """Keep publication descriptors independent of validating input contexts."""
    def __init__(self, root, case_id, condition):
        self.root = artifacts._safe_path(root)
        self.parts = ('.pending', case_id, 'conditions', condition)
        self.fds, self.identities = [], []
        try:
            self.fds.append(os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW))
            for name in self.parts:
                self.fds.append(os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                        dir_fd=self.fds[-1]))
            self.identities = [self.identity(os.fstat(fd)) for fd in self.fds]
            self.recheck()
        except BaseException:
            self.close()
            raise

    @staticmethod
    def identity(value):
        return value.st_dev, value.st_ino, value.st_mode

    @property
    def case_fd(self):
        return self.fds[2]

    @property
    def condition_fd(self):
        return self.fds[4]

    def recheck(self):
        for index, expected in enumerate(self.identities):
            named = self.root.lstat() if index == 0 else os.stat(
                self.parts[index - 1], dir_fd=self.fds[index - 1], follow_symlinks=False)
            if self.identity(os.fstat(self.fds[index])) != expected or self.identity(named) != expected:
                raise RuntimeError('Condition publication ancestor changed')
        if 'quarantine.json' in directory_names(self.case_fd, max_entries=64):
            raise ValueError('Condition case is quarantined')

    def close(self):
        first = None
        while self.fds:
            fd = self.fds.pop()
            try:
                os.close(fd)
            except OSError as error:
                first = first or error
        if first is not None:
            raise first


def _load_source(root, contract, deadline, lifetime):
    case_id = contract['case']['case_id']
    src = contract['source']
    values = source._inputs(root, src['registration'], case_id, deadline, lifetime)
    source_contract, case, run_id, raw_receipt, raw_bytes, snapshot_fd, checks, control_bytes = values
    if (case != contract['case'] or run_id != contract['source_run_id']
            or source_contract['snapshot'] != src['snapshot']
            or source_contract['owner_source_sha256'] != contract['owner_source_sha256']):
        raise ValueError('Condition binds another sealed source')
    fd, _, output_check = lifetime.enter_context(source._source_directory(root, case_id))
    marker_bytes = source._read_file(fd, 'commit.json', MiB, lifetime=lifetime, deadline=deadline)
    compact._check_descriptor(src['commit'], src['commit']['path'], marker_bytes)
    marker = _canonical(marker_bytes, compact.PROTOCOL['source_finalization']['marker_keys'], 'Source marker')
    bundle = source._disk_bundle(fd, extras={'commit.json'}, lifetime=lifetime, deadline=deadline)
    recording = os.open('recording', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    lifetime.callback(os.close, recording)
    conversion_bytes = source._read_file(recording, 'conversion.json', MiB,
                                         lifetime=lifetime, deadline=deadline)
    conversion = _canonical(conversion_bytes,
        compact.PROTOCOL['schemas']['conversion']['exact_keys'], 'Source conversion')
    expected_marker = {'schema': 'memory-family-compact-source-commit-v1',
        'protocol_sha256': compact.PROTOCOL_SHA256, 'case_id': case_id,
        'run_id': run_id, 'conversion': _descriptor(
            f'cases/{case_id}/source/recording/conversion.json', conversion_bytes),
        'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
    if marker != expected_marker or conversion['registration'] != src['registration']:
        raise ValueError('Source marker or registration differs')
    if source._read_file(recording, 'raw-audit.json', MiB,
            lifetime=lifetime, deadline=deadline) != raw_bytes:
        raise ValueError('Source raw audit differs from independent receipt')
    owner = source._read_file(fd, 'owner.json', MiB, lifetime=lifetime, deadline=deadline)
    worker = source._read_file(fd, 'worker-report.json', MiB, lifetime=lifetime, deadline=deadline)
    inventory = sorted([*[_descriptor('recording/' + p, b) for p, b in bundle.items()],
        _descriptor('recording/raw-audit.json', raw_bytes), src['snapshot']], key=lambda d: d['path'])
    support = sorted([_descriptor('owner.json', owner), _descriptor('worker-report.json', worker)],
                     key=lambda d: d['path'])
    if (conversion['inventory'] != inventory or conversion['support'] != support
            or conversion['raw_audit'] != source_contract['raw_audit']
            or _descriptor('worker-report.json', worker) != next(
                d for d in raw_receipt['raw_inventory']['files'] if d['path'] == 'worker-report.json')):
        raise ValueError('Sealed source retained inventory differs')
    source._bounds(bundle, raw_bytes, conversion_bytes, len(owner) + len(worker), control_bytes, len(marker_bytes))
    snapshot = snapshots.read_snapshot(Path(f'/proc/self/fd/{snapshot_fd}'))
    checks.append(output_check)
    return bundle, marker['conversion'], snapshot, checks


def _raw(root, contract, deadline, lifetime):
    case_id, run_id = contract['case']['case_id'], contract['run_id']
    request = dict(run_path=Path(root) / '.pending' / case_id / '.raw' / run_id,
        receipt_root=(Path(root) / contract['raw_audit']['path']).parent,
        run_id=run_id, case_id=case_id, operation='condition', condition=contract['condition'],
        source_run_id=contract['source_run_id'], source_snapshot_sha256=contract['source']['snapshot']['sha256'],
        source_identity_sha256=contract['owner_source_sha256'], deadline=deadline)
    _, raw_bytes, check = _bind(lifetime, root, contract['raw_audit'], MiB, deadline)
    receipt = artifacts._json(raw_bytes)
    audit._validate_receipt_shape(receipt)
    if audit.validate_raw_receipt(**request) != receipt:
        raise ValueError('Condition independent raw audit differs')
    inventory = audit._inventory(request['run_path'], 'condition', deadline)
    checks = [check]
    for value in inventory:
        _, _, check = lifetime.enter_context(compact.bound_payload(
            root, value, audit._file_limit(Path(value['path']), 'condition'), deadline,
            source_case=case_id, raw_run=run_id))
        checks.append(check)
    def recheck():
        if audit._inventory(request['run_path'], 'condition', deadline) != inventory:
            raise RuntimeError('Condition raw inventory changed while held')
    lifetime.callback(recheck)
    checks.append(recheck)
    data = legacy._read_run({'run_id': run_id, 'run': request['run_path']}, deadline)
    data['report'] = artifacts._json(artifacts._read(request['run_path'] / 'worker-report.json', MiB))
    return data, receipt, raw_bytes, checks


def _owner(root, contract, deadline, lifetime):
    _, payload, check = _bind(lifetime, root, contract['owner_record'], MiB,
                             deadline, case_id=contract['case']['case_id'])
    expected = {'schema': 'memory-family-condition-owner-v1',
        'case_id': contract['case']['case_id'], 'run_id': contract['run_id'],
        'condition': contract['condition'], 'source_run_id': contract['source_run_id'],
        'owner_source_sha256': contract['owner_source_sha256'],
        'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
    if _canonical(payload, set(expected), 'Condition owner') != expected:
        raise ValueError('Condition owner record differs')
    return payload, check


def _bundle(anchor, lifetime, deadline, expected_extra):
    directory = anchor.condition_fd
    expected = {'owner.json', 'recording', 'worker-report.json', 'snapshot-reference.json', *expected_extra}
    if set(directory_names(directory, max_entries=64, deadline=deadline)) != expected:
        raise ValueError('Condition output has unregistered or missing entries')
    recording = os.open('recording', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
    source._hold_directory(lifetime, directory, 'recording', recording)
    names = set(directory_names(recording, max_entries=64, deadline=deadline))
    if names != METADATA | {'chunks', 'raw-audit.json', 'conversion.json'}:
        raise ValueError('Condition recording namespace differs')
    maxima = {'manifest.json': MiB, 'legacy-manifest.json': MiB,
        'legacy-events.jsonl': 5 * MiB, 'chunk-index.json': MiB,
        'audit-frames.npz': compact.PROTOCOL['recordings']['condition']['audit_frames_max_bytes'] + MiB}
    bundle = {name: source._read_file(recording, name, maximum,
        lifetime=lifetime, deadline=deadline) for name, maximum in maxima.items()}
    chunks = os.open('chunks', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=recording)
    source._hold_directory(lifetime, recording, 'chunks', chunks)
    index = artifacts._json(bundle['chunk-index.json'])
    if type(index.get('chunks')) is not list or not 1 <= len(index['chunks']) <= 29:
        raise ValueError('Condition chunk count exceeds 29')
    expected_chunks = {f'{i:06d}.npz' for i in range(len(index['chunks']))}
    if set(directory_names(chunks, max_entries=64, deadline=deadline)) != expected_chunks:
        raise ValueError('Condition chunks differ from exact index')
    for name in sorted(expected_chunks):
        bundle['chunks/' + name] = source._read_file(chunks, name,
            compact.CHUNK_ROWS * compact.PROTOCOL['row']['bytes_per_tick'] + MiB,
            lifetime=lifetime, deadline=deadline)
        if sum(map(len, bundle.values())) > 25 * MiB:
            raise ValueError('Condition bundle exceeds 25 MiB before decode')
    support = {name: source._read_file(directory, name, MiB,
        lifetime=lifetime, deadline=deadline) for name in expected - {'recording', '.commit.tmp', 'commit.json'}}
    for name in ('raw-audit.json', 'conversion.json'):
        support['recording/' + name] = source._read_file(recording, name, MiB,
            lifetime=lifetime, deadline=deadline)
    # Directory checks permit only the owned marker's atomic rename transition.
    def check_namespace():
        now = {'commit.json' if 'commit.json' in directory_names(
            directory, max_entries=64, deadline=deadline) else '.commit.tmp'}
        extras = expected_extra - {'.commit.tmp', 'commit.json'}
        marker_expected = now if expected_extra & {'.commit.tmp', 'commit.json'} else set()
        current = set(directory_names(directory, max_entries=64, deadline=deadline))
        base = {'owner.json', 'recording', 'worker-report.json', 'snapshot-reference.json'}
        valid = (current == base | extras | marker_expected if expected_extra else
            base <= current <= base | {'pair-admission.json', '.commit.tmp', 'commit.json'}
            and not {'.commit.tmp', 'commit.json'} <= current)
        if (not valid
                or set(directory_names(recording, max_entries=64, deadline=deadline)) != names
                or set(directory_names(chunks, max_entries=64, deadline=deadline)) != expected_chunks):
            raise RuntimeError('Condition output namespace changed while held')
        anchor.recheck()
    lifetime.callback(check_namespace)
    if len(bundle) + len(support) + 1 > 41:
        raise ValueError('Condition output exceeds 41 files')
    return bundle, support


def _bounds(bundle, receipt_bytes, conversion_bytes, support_bytes, control_bytes, marker_bytes):
    read = compact.read_compact(bundle, raw_audit_receipt=artifacts._json(receipt_bytes))
    dense = len(read['rows']) * compact.PROTOCOL['row']['bytes_per_tick']
    frames = len(read['selected_frames']) * 98_304
    total = sum(map(len, bundle.values())) + len(receipt_bytes) + len(conversion_bytes)
    overhead = total - len(bundle['legacy-events.jsonl']) - dense - frames
    compact.validate_read_limits('condition', row_count=len(read['rows']),
        total_bytes=total, overhead_bytes=overhead)
    for value in (support_bytes, control_bytes, marker_bytes):
        if type(value) is not int or value < 0:
            raise ValueError('Condition support size must be an exact nonnegative integer')
    if support_bytes + control_bytes + marker_bytes > MiB:
        raise ValueError('Condition support and control exceeds its combined MiB')


def _validate_replay(result, contract, read):
    pair._fields(result, REPLAY_KEYS, 'Internally generated cell replay')
    if (result['schema'] != 'memory-family-cell-replay-v4'
            or result['protocol_sha256'] != compact.PROTOCOL_SHA256
            or result['case_id'] != contract['case']['case_id']
            or result['run_id'] != contract['run_id'] or result['operation'] != 'condition'
            or result['trace_digest'] != read['trace_digest']
            or result['source_snapshot_reference'] != read['snapshot_reference']
            or type(result['rows_checked']) is not int
            or result['rows_checked'] != read['manifest']['row_count']
            or result['raw_output_equal'] is not True or result['action_equal'] is not True
            or result['source_endpoint_verified'] is not False):
        raise ValueError('Internally generated cell replay identity differs')
    _claims(result['claims'])
    for field in ('initial_hidden_sha256', 'final_hidden_sha256'):
        compact._digest(result[field])


def _quarantine(anchor, contract, error):
    if 'quarantine.json' in directory_names(anchor.case_fd, max_entries=64):
        return
    source._write_file(anchor.case_fd, 'quarantine.json', memory.canonical_bytes({
        'schema': 'memory-family-condition-quarantine-v1',
        'case_id': contract['case']['case_id'], 'run_id': contract['run_id'],
        'condition': contract['condition'], 'error_type': type(error).__name__,
        'claims': copy.deepcopy(compact.PROTOCOL['claims'])}))
    os.fsync(anchor.case_fd)


def _marker_guard(lifetime, anchor, payload, state, deadline):
    fd = os.open('.commit.tmp', os.O_RDONLY | os.O_NOFOLLOW, dir_fd=anchor.condition_fd)
    lifetime.callback(os.close, fd)
    before = [compact._file_identity(os.fstat(fd))]
    def check():
        audit._deadline(deadline)
        name = 'commit.json' if state['committed'] else '.commit.tmp'
        named = os.stat(name, dir_fd=anchor.condition_fd, follow_symlinks=False)
        if (compact._file_identity(os.fstat(fd)) != before[0]
                or compact._file_identity(named) != before[0]):
            raise RuntimeError('Condition marker identity changed while held')
        os.lseek(fd, 0, os.SEEK_SET)
        value, _ = pair._read_fd(fd, MiB, deadline)
        if value != payload:
            raise RuntimeError('Condition marker bytes changed while held')
    lifetime.callback(check)
    check()
    def renamed():
        after = compact._file_identity(os.fstat(fd))
        # rename may advance ctime, but cannot change object, bytes, mode, mtime,
        # size or link count. Capture the new ctime only for this owned rename.
        if before[0][:5] != after[:5] or before[0][6:] != after[6:]:
            raise RuntimeError('Condition marker changed during rename')
        before[0] = after
        check()
    return check, renamed


def _consume(root, registration, case_id, condition, deadline, *, publish):
    registration = copy.deepcopy(registration)
    anchor = None
    state = {'committed': False, 'started': False}
    contract = None
    try:
        with _ValidatingStack() as lifetime:
            contract, checks, control_bytes = _registration(
                root, registration, case_id, condition, deadline, lifetime)
            anchor = _Anchor(root, case_id, condition)
            directory = anchor.condition_fd
            if publish:
                if set(directory_names(directory, max_entries=64, deadline=deadline)) != {'owner.json'}:
                    raise FileExistsError('Condition has a prior candidate, seal or quarantine')
                state['started'] = True
                os.mkdir('recording', 0o700, dir_fd=directory)
                rec = os.open('recording', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                lifetime.callback(os.close, rec)
                os.mkdir('chunks', 0o700, dir_fd=rec)
                chunks = os.open('chunks', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=rec)
                lifetime.callback(os.close, chunks)
            source_bundle, source_conversion, snapshot, source_checks = _load_source(
                root, contract, deadline, lifetime)
            checks.extend(source_checks)
            owner, check = _owner(root, contract, deadline, lifetime)
            checks.append(check)
            raw_data, receipt, raw_bytes, raw_checks = _raw(root, contract, deadline, lifetime)
            checks.extend(raw_checks)
            reference = {'kind': 'shared-source', 'source_run_id': contract['source_run_id'],
                'source_receipt_sha256': source_conversion['sha256'], **contract['source']['snapshot']}
            projection = pair._projection(raw_data['rows'])
            _, schedule = oracle._schedule(contract['case'], raw_data['events'],
                projection[0]['tick'], raw_data['report']['world_state'],
                raw_data['report']['world_state']['acquired_state_sha256'])
            bundle = compact.convert_synthetic(run_id=contract['run_id'], case_id=case_id,
                operation='condition', condition=condition, rows=raw_data['rows'],
                legacy_manifest_bytes=artifacts._read(raw_data['run'] / 'recording/manifest.json', MiB),
                legacy_events_bytes=artifacts._read(raw_data['run'] / 'recording/events.jsonl', 5 * MiB),
                snapshot_reference=reference, event_tick=schedule['event_tick'],
                decision_tick=schedule['decision_tick'], raw_audit_receipt=receipt)
            read = source._prove(raw_data, bundle, receipt)
            worker = artifacts._read(raw_data['run'] / 'worker-report.json', MiB)
            reference_bytes = memory.canonical_bytes(reference)
            base = f'cases/{case_id}/conditions/{condition}'
            support = sorted([_descriptor('worker-report.json', worker),
                _descriptor('owner.json', owner), _descriptor('snapshot-reference.json', reference_bytes)],
                key=lambda d: d['path'])
            conversion = {'schema': 'memory-family-compact-conversion-v1',
                'protocol_sha256': compact.PROTOCOL_SHA256, 'case_id': case_id,
                'run_id': contract['run_id'], 'operation': 'condition', 'condition': condition,
                'raw_audit': copy.deepcopy(contract['raw_audit']),
                'source_identity': audit.canonical_source_identity(contract['owner_source_sha256']),
                'legacy_trace_digest': read['trace_digest'], 'compact_trace_digest': read['trace_digest'],
                'compact_manifest': _descriptor('manifest.json', bundle['manifest.json']),
                'inventory': sorted([*[_descriptor('recording/' + p, b) for p, b in bundle.items()],
                    _descriptor('recording/raw-audit.json', raw_bytes)], key=lambda d: d['path']),
                'support': support, 'registration': copy.deepcopy(registration),
                'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
            conversion_bytes = memory.canonical_bytes(conversion)
            conversion_descriptor = _descriptor(base + '/recording/conversion.json', conversion_bytes)
            if publish:
                for path, payload in bundle.items():
                    audit._deadline(deadline)
                    source._write_file(chunks if path.startswith('chunks/') else rec,
                                       path.removeprefix('chunks/'), payload)
                source._write_file(rec, 'raw-audit.json', raw_bytes)
                source._write_file(rec, 'conversion.json', conversion_bytes)
                source._write_file(directory, 'worker-report.json', worker)
                source._write_file(directory, 'snapshot-reference.json', reference_bytes)
            expected_extra = set() if publish else {'pair-admission.json', 'commit.json'}
            disk, retained = _bundle(anchor, lifetime, deadline, expected_extra)
            if (disk != bundle or retained['recording/raw-audit.json'] != raw_bytes
                    or retained['recording/conversion.json'] != conversion_bytes
                    or retained['worker-report.json'] != worker or retained['owner.json'] != owner
                    or retained['snapshot-reference.json'] != reference_bytes):
                raise ValueError('Condition disk candidate differs from independently proved bytes')
            source._prove(raw_data, disk, receipt)
            session = lifetime.enter_context(_qualified_replay(root, contract['qualification'], deadline=deadline))
            if session.descriptor != contract['qualification']:
                raise ValueError('Qualification session identity differs')
            replay = _production_replay(policy=session.policy, bundle=disk,
                raw_audit_receipt=receipt, source_snapshot=snapshot, deadline=deadline)
            _validate_replay(replay, contract, read)
            session.recheck()
            pair_result = pair.admit_staged_compact_pair(source_commit=contract['source']['commit'],
                evidence_root=root, case=contract['case'], source_bundle=source_bundle,
                condition_bundle=disk, source_run_id=contract['source_run_id'],
                condition_run_id=contract['run_id'], condition=condition,
                source_conversion_receipt=source_conversion,
                condition_conversion_receipt=conversion_descriptor,
                history_bundles=contract['history_bundles'],
                owner_source_sha256=contract['owner_source_sha256'], deadline=deadline,
                prior_own_receipt=contract['prior_own_receipt'])
            pair_bytes = memory.canonical_bytes(pair_result)
            marker = {'schema': 'memory-family-compact-condition-commit-v1',
                'protocol_sha256': compact.PROTOCOL_SHA256, 'extension_sha256': contract['extension_sha256'],
                'case_id': case_id, 'run_id': contract['run_id'], 'condition': condition,
                'source_run_id': contract['source_run_id'], 'conversion': conversion_descriptor,
                'snapshot_reference': _descriptor(base + '/snapshot-reference.json', reference_bytes),
                'pair_admission': _descriptor(base + '/pair-admission.json', pair_bytes),
                'qualification': copy.deepcopy(contract['qualification']),
                'cell_replay': replay, 'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
            marker_bytes = memory.canonical_bytes(marker)
            _bounds(bundle, raw_bytes, conversion_bytes,
                sum(d['size_bytes'] for d in support) + len(pair_bytes), control_bytes, len(marker_bytes))
            if publish:
                source._write_file(directory, 'pair-admission.json', pair_bytes)
                source._write_file(directory, '.commit.tmp', marker_bytes)
                marker_check, renamed = _marker_guard(lifetime, anchor, marker_bytes, state, deadline)
            else:
                actual = source._read_file(directory, 'commit.json', MiB, lifetime=lifetime, deadline=deadline)
                if _canonical(actual, MARKER_KEYS, 'Condition marker') != marker or actual != marker_bytes:
                    raise ValueError('Sealed condition marker differs from fresh proof')
            # Rebind the complete final candidate, including the pair receipt.
            final_bundle, final_support = _bundle(anchor, lifetime, deadline,
                {'pair-admission.json', '.commit.tmp' if publish else 'commit.json'})
            if (final_bundle != bundle or final_support['pair-admission.json'] != pair_bytes):
                raise RuntimeError('Condition output changed before final publication')
            source._prove(raw_data, final_bundle, receipt)
            def final_checks():
                for check in checks:
                    check()
                session.recheck()
                anchor.recheck()
                audit._deadline(deadline)
            final_checks()
            if publish:
                for fd in (chunks, rec, directory, anchor.case_fd):
                    os.fsync(fd)
                marker_check()
                source._rename_noreplace(directory)
                state['committed'] = True
                renamed()
                os.fsync(directory)
                os.fsync(anchor.case_fd)
                final_checks()
            result = {'case_id': case_id, 'run_id': contract['run_id'],
                'condition': condition, 'marker': marker, 'read': read,
                'conversion': conversion, 'pair_admission': pair_result,
                'claims': copy.deepcopy(compact.PROTOCOL['claims'])}
        # Every input/output/model context above has now validated on exit.
        anchor.recheck()
        audit._deadline(deadline)
        return result
    except BaseException as error:
        if publish and state['started'] and anchor is not None:
            try:
                _quarantine(anchor, contract, error)
            except BaseException as quarantine_error:
                raise SealIndeterminate('Condition quarantine durability is indeterminate') from quarantine_error
        if publish and state['committed']:
            raise SealIndeterminate('Condition postcommit validation failed; marker retained and quarantined') from error
        raise
    finally:
        if anchor is not None:
            try:
                anchor.close()
                audit._deadline(deadline)
            except BaseException as error:
                # The final descriptor can already have closed when close(2)
                # reports an error. Reacquire only the exact original directory
                # objects to publish refusal; never write into a replacement.
                if publish and state['started']:
                    recovery = None
                    try:
                        recovery = _Anchor(root, case_id, condition)
                        if recovery.identities != anchor.identities:
                            raise RuntimeError('Condition recovery anchor was replaced')
                        _quarantine(recovery, contract, error)
                    except BaseException as quarantine_error:
                        raise SealIndeterminate('Condition teardown quarantine durability is indeterminate') from quarantine_error
                    finally:
                        if recovery is not None:
                            recovery.close()
                raise SealIndeterminate('Condition publication anchor teardown is indeterminate') from error


def seal_compact_condition(evidence_root, registration, *, case_id, condition, deadline):
    """Seal one authored/admitted condition; preserve raw and every false claim."""
    return _consume(evidence_root, registration, case_id, condition, deadline, publish=True)


def read_sealed_condition(evidence_root, registration, *, case_id, condition, deadline):
    """Read-only exhaustive rederivation; no pruned-raw or case-close authority."""
    return _consume(evidence_root, registration, case_id, condition, deadline, publish=False)
