"""Pure accepted supervisor-attestation validation; no publication or execution.

Callers supply already validated terminal contracts and continuously held control
bytes. This function neither opens evidence nor grants custody/qualification.
"""
from __future__ import annotations
import copy
import hashlib
from pathlib import PurePosixPath
import re
import uuid
from palimpsest import artifacts, memory
from scripts import memory_family_analysis_v3 as analysis
from scripts import memory_family_compact_v4 as compact
from scripts import memory_case_execution_pins_v1 as pins

CONDITIONS = tuple(compact.PROTOCOL['analysis_contract']['conditions'])
AUDIT_KEYS = set('schema publication_protocol_sha256 case_slot source_commit condition_commits observer owners claims'.split())
OBSERVER_KEYS = set('source_sha256 qualification_sha256 boot_id pid_namespace clock ticks_per_second'.split())
OWNER_KEYS = set('operation condition run_id registration job owner supervisor cleanup commit pid starttime pgid launch_ns reaped_ns drained_ns returncode status'.split())
SUPERVISOR_KEYS = set('schema case_id run_id operation condition observer job pid starttime pgid launch_ns reaped_ns drained_ns returncode status'.split())
CLEANUP_KEYS = set('schema case_id run_id operation condition observer job pid starttime pgid drained_ns status'.split())
MAX_BYTES = 32 * 1024 * 1024


def _fields(value, keys, label):
    if type(value) is not dict or set(value) != set(keys):
        raise ValueError(f'{label} has missing or unknown fields')


def _integer(value, minimum, label):
    if type(value) is not int or value < minimum:
        raise ValueError(f'Invalid {label}')


def _digest(value):
    if type(value) is not str or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('Invalid SHA-256')


def _run_id(value):
    if type(value) is not str:
        raise ValueError('Invalid run ID')
    try:
        if uuid.UUID(value).hex != value: raise ValueError('Noncanonical run ID')
    except (ValueError, AttributeError) as error:
        raise ValueError('Invalid run ID') from error


def _descriptor(value):
    _fields(value, ('path', 'size_bytes', 'sha256'), 'Descriptor')
    path = value['path']
    if (type(path) is not str or not path or path.startswith('/') or '\\' in path
            or PurePosixPath(path).as_posix() != path or any(p in ('', '.', '..') for p in path.split('/'))):
        raise ValueError('Noncanonical relative descriptor path')
    _integer(value['size_bytes'], 0, 'descriptor size')
    _digest(value['sha256'])


def _equal(left, right, label):
    if memory.canonical_bytes(left) != memory.canonical_bytes(right):
        raise ValueError(f'{label} differs')


def _payload(descriptor, controls):
    _descriptor(descriptor)
    if descriptor['size_bytes'] > compact.MiB: raise ValueError('Control payload exceeds bound')
    payload = controls[descriptor['path']]
    if (type(payload) is not bytes or len(payload) != descriptor['size_bytes']
            or hashlib.sha256(payload).hexdigest() != descriptor['sha256']):
        raise ValueError('Held control bytes differ from descriptor')
    return payload


def _canonical(descriptor, controls, keys, label):
    payload = _payload(descriptor, controls)
    obj = artifacts._json(payload)
    _fields(obj, keys, label)
    if memory.canonical_bytes(obj) != payload: raise ValueError(f'{label} is not canonical JSON')
    return obj


def _require_execution_pin(audit):
    payload = memory.canonical_bytes(audit)
    if len(payload) > MAX_BYTES: raise ValueError('Execution audit exceeds combined case-file allowance')
    digest = hashlib.sha256(payload).hexdigest()
    if digest not in pins.ACCEPTED_EXECUTION_AUDIT_SHA256:
        raise PermissionError('Execution audit has no independently accepted pin')


def validate_execution_audit(audit, *, case_slot, source_commit, condition_commits,
                             contracts, control_payloads, publication_protocol_sha256):
    """Validate a pinned attestation against supplied contracts and held bytes.

    Trust admission precedes any access/copy of protected contracts or controls.
    Returned data is a deep copy and carries no live custody or authority.
    """
    audit = copy.deepcopy(audit)
    _require_execution_pin(audit)
    slot, source_commit, commits, contracts, controls = copy.deepcopy(
        (case_slot, source_commit, condition_commits, contracts, control_payloads))
    _fields(audit, AUDIT_KEYS, 'Execution audit')
    if audit['schema'] != 'memory-family-case-execution-audit-v1': raise ValueError('Old execution schema')
    _digest(publication_protocol_sha256)
    _equal(audit['publication_protocol_sha256'], publication_protocol_sha256, 'Publication protocol')
    _equal(audit['case_slot'], slot, 'Case slot')
    _fields(slot, ('case_id', 'case_sha256', 'source_run_id', 'condition_run_ids'), 'Case slot')
    memory._id(slot['case_id']); _digest(slot['case_sha256'])
    _fields(slot['condition_run_ids'], CONDITIONS, 'Condition run IDs')
    ids = [slot['source_run_id'], *slot['condition_run_ids'].values()]
    for run in ids: _run_id(run)
    if len(set(ids)) != 10: raise ValueError('Run identities overlap')
    _fields(commits, CONDITIONS, 'Condition commits')
    _fields(contracts, ('source', *CONDITIONS), 'Terminal contracts')
    _descriptor(source_commit)
    for value in commits.values(): _descriptor(value)
    _equal(audit['source_commit'], source_commit, 'Source commit')
    _equal(audit['condition_commits'], commits, 'Condition commits')
    _equal(audit['claims'], compact.PROTOCOL['claims'], 'All-false claims')
    observer = audit['observer']; _fields(observer, OBSERVER_KEYS, 'Observer')
    _digest(observer['source_sha256']); _digest(observer['qualification_sha256'])
    try:
        if str(uuid.UUID(observer['boot_id'])) != observer['boot_id']: raise ValueError('Noncanonical boot ID')
    except (ValueError, TypeError, AttributeError) as error: raise ValueError('Invalid observer boot ID') from error
    if type(observer['pid_namespace']) is not str or re.fullmatch(r'pid:\[[1-9][0-9]*\]',observer['pid_namespace']) is None:
        raise ValueError('Invalid PID namespace')
    if observer['clock'] != 'CLOCK_BOOTTIME': raise ValueError('Invalid observer clock')
    _integer(observer['ticks_per_second'], 1, 'tick frequency')
    row = contracts['own']['case']['row']
    order = analysis.condition_order(row)
    if order.index('own') > order.index('oracle'): raise ValueError('Registered order conflicts with prior-own')
    owners = audit['owners']
    if type(owners) is not list or len(owners) != 10: raise ValueError('Exactly ten owners required')
    identities = set(); previous = None; descriptors = set()
    for name, owner in zip(('source', *order), owners):
        _fields(owner, OWNER_KEYS, 'Owner attestation')
        condition = None if name == 'source' else name
        operation = 'source' if condition is None else 'condition'
        run = slot['source_run_id'] if condition is None else slot['condition_run_ids'][name]
        contract = contracts[name]
        if (owner['operation'] != operation or owner['condition'] != condition or owner['run_id'] != run):
            raise ValueError('Owner order/identity differs from registration')
        _equal(contract['case'], contracts['own']['case'], 'Shared case')
        if contract['case']['case_id'] != slot['case_id'] or contract['case']['case_sha256'] != slot['case_sha256'] or contract['run_id'] != run:
            raise ValueError('Terminal contract differs from case slot')
        expected_commit = source_commit if condition is None else commits[name]
        _equal(owner['commit'], expected_commit, 'Expected commit')
        for role in ('registration','job','owner','supervisor','cleanup','commit'):
            _descriptor(owner[role])
            if owner[role]['path'] in descriptors: raise ValueError('Repeated descriptor path')
            descriptors.add(owner[role]['path'])
        registration_bytes = _payload(owner['registration'], controls)
        if registration_bytes != memory.canonical_bytes(contract): raise ValueError('Terminal export bytes differ')
        for role in ('job','supervisor','cleanup'):
            _equal(owner[role], contract['controls'][role], f'{role} control descriptor')
            _payload(owner[role], controls)
        _equal(owner['owner'], contract['owner_record'], 'Owner record descriptor')
        source_fields = {'schema','case_id','run_id','owner_source_sha256','claims'}
        owner_fields = source_fields if condition is None else source_fields | {'condition','source_run_id'}
        record = _canonical(owner['owner'], controls, owner_fields, 'Compact owner record')
        expected = dict(schema='memory-family-source-owner-v4' if condition is None else 'memory-family-condition-owner-v1',
            case_id=slot['case_id'],run_id=run,owner_source_sha256=contract['owner_source_sha256'],claims=compact.PROTOCOL['claims'])
        if condition is not None: expected.update(condition=condition,source_run_id=slot['source_run_id'])
        _equal(record, expected, 'Compact owner identities')
        for key in ('pid','starttime','pgid'): _integer(owner[key],1,key)
        for key in ('launch_ns','reaped_ns','drained_ns'): _integer(owner[key],0,key)
        if owner['pid'] != owner['pgid']: raise ValueError('Owner PID must equal PGID')
        identity = owner['pid'], owner['starttime']
        if identity in identities: raise ValueError('Reused process identity')
        identities.add(identity)
        if type(owner['returncode']) is not int or owner['returncode'] != 0 or owner['status'] != 'completed':
            raise ValueError('Owner did not complete normally')
        if not owner['launch_ns'] <= owner['reaped_ns'] <= owner['drained_ns']:
            raise ValueError('Invalid owner lifetime')
        if previous is not None and previous > owner['launch_ns']: raise ValueError('Overlapping owners')
        previous = owner['drained_ns']
        ticks = observer['ticks_per_second']; start = owner['starttime']
        if owner['launch_ns']*ticks > (start+1)*10**9 or (start-1)*10**9 > owner['reaped_ns']*ticks:
            raise ValueError('Starttime is outside launch/reap bracket')
        supervisor = _canonical(owner['supervisor'], controls, SUPERVISOR_KEYS, 'Supervisor')
        expected = {k:owner[k] for k in SUPERVISOR_KEYS - {'schema','case_id','observer'}}
        expected.update(schema='memory-family-order-supervisor-v1',case_id=slot['case_id'],observer=observer)
        _equal(supervisor,expected,'Prospective supervisor')
        cleanup = _canonical(owner['cleanup'], controls, CLEANUP_KEYS, 'Cleanup')
        expected = {k:owner[k] for k in CLEANUP_KEYS - {'schema','case_id','observer','status'}}
        expected.update(schema='memory-family-order-cleanup-v1',case_id=slot['case_id'],observer=observer,status='drained')
        _equal(cleanup,expected,'Prospective cleanup')
    _require_execution_pin(audit)
    return copy.deepcopy(audit)
