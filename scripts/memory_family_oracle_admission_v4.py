"""Pure admission of one synthetic v4 compact source/condition pair.

The caller supplies immutable descriptor identities.  This module opens only
those descriptors beneath one direct evidence root, exhausts both compact
bundles, validates the shared source snapshot and replays the recorded selector.
It publishes nothing and never imports an owner, Engine, model, or simulator.
"""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
import copy
import hashlib
import math
import os
from pathlib import Path, PurePosixPath
import stat
import time
import uuid

from palimpsest import artifacts, memory, memory_decision
from palimpsest import memory_decision_world as world
from palimpsest import memory_experiment, memory_task, snapshots
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_raw_audit_v4 as raw_audit
from scripts import memory_family_oracle_v3 as oracle


PROTOCOL = compact.PROTOCOL
PROTOCOL_SHA256 = compact.PROTOCOL_SHA256
PAIR_CONTRACT = PROTOCOL['pair_admission']
MiB = 1024**2


def _fields(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f'{label} has missing or unknown fields')


def _digest(value, label='SHA-256'):
    try:
        memory._digest(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'Invalid {label}') from error
    return value


def _run_id(value):
    try:
        valid = type(value) is str and uuid.UUID(value).hex == value
    except (AttributeError, TypeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Run ID must be canonical UUID hex')
    return value


def _deadline(deadline):
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError('Pair-admission deadline must be finite')
    if time.monotonic() >= deadline:
        raise TimeoutError('Pair-admission deadline exhausted')


def _public_deadline(deadline):
    entered = time.monotonic()
    _deadline(deadline)
    if deadline - entered > PAIR_CONTRACT['deadline_seconds_max']:
        raise ValueError('Pair-admission deadline exceeds its frozen cap')


def deadline_from_seconds(seconds):
    if (type(seconds) not in (int, float) or not math.isfinite(seconds)
            or not 0 < seconds <= PAIR_CONTRACT['deadline_seconds_max']):
        raise ValueError('Pair-admission duration exceeds its frozen cap')
    return time.monotonic() + seconds


def _descriptor(value, label):
    fields = PAIR_CONTRACT['nested_schemas']['descriptor']['exact_keys']
    _fields(value, fields, label)
    relative = compact._relative(value['path'], f'{label} path')
    if type(value['size_bytes']) is not int or value['size_bytes'] < 1:
        raise ValueError(f'Invalid {label} size')
    _digest(value['sha256'], f'{label} SHA-256')
    return {**copy.deepcopy(value), 'path': relative}


def _fingerprint(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


def _read_fd(descriptor, maximum, deadline):
    digest = hashlib.sha256()
    payload = bytearray()
    while True:
        _deadline(deadline)
        block = os.read(descriptor, min(MiB, maximum + 1 - len(payload)))
        if not block:
            break
        payload.extend(block)
        digest.update(block)
        if len(payload) > maximum:
            raise ValueError('Descriptor payload exceeds its frozen limit')
    return bytes(payload), digest.hexdigest()


@contextmanager
def _bound_file(root, value, maximum, deadline, label):
    """Open one root-relative regular file without following any component."""
    descriptor_value = _descriptor(value, label)
    if descriptor_value['size_bytes'] > maximum:
        raise ValueError(f'{label} exceeds its frozen limit')
    root = Path(root)
    root_state = root.lstat()
    if not stat.S_ISDIR(root_state.st_mode) or root.is_symlink():
        raise ValueError('Evidence root must be one direct non-symlink directory')
    parts = PurePosixPath(descriptor_value['path']).parts
    opened = []
    directories = []
    try:
        opened.append(os.open(
            root, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
            | getattr(os, 'O_NOFOLLOW', 0)))
        if _fingerprint(os.fstat(opened[0])) != _fingerprint(root_state):
            raise RuntimeError('Evidence root changed before descriptor open')
        for part in parts[:-1]:
            opened.append(os.open(
                part, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0)
                | getattr(os, 'O_NOFOLLOW', 0), dir_fd=opened[-1]))
        directories = [_fingerprint(os.fstat(fd)) for fd in opened]
        file_descriptor = os.open(
            parts[-1], os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0),
            dir_fd=opened[-1])
        opened.append(file_descriptor)
        before = os.fstat(file_descriptor)
        named = os.stat(parts[-1], dir_fd=opened[-2], follow_symlinks=False)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or _fingerprint(before) != _fingerprint(named)
                or before.st_size != descriptor_value['size_bytes']):
            raise ValueError(f'{label} type, alias count, or size differs')
        payload, digest = _read_fd(file_descriptor, maximum, deadline)
        if digest != descriptor_value['sha256']:
            raise ValueError(f'{label} checksum differs')
        yield file_descriptor, payload, descriptor_value
        os.lseek(file_descriptor, 0, os.SEEK_SET)
        repeated, repeated_digest = _read_fd(file_descriptor, maximum, deadline)
        if _fingerprint(root.lstat()) != directories[0]:
            raise RuntimeError('Evidence root changed while admitted')
        for index, identity in enumerate(directories):
            current = os.fstat(opened[index])
            named = (root.lstat() if index == 0 else os.stat(
                parts[index - 1], dir_fd=opened[index - 1], follow_symlinks=False))
            if (_fingerprint(current) != identity
                    or _fingerprint(named) != identity):
                raise RuntimeError(f'{label} ancestor changed while admitted')
        after = os.fstat(file_descriptor)
        rebound = os.stat(parts[-1], dir_fd=opened[-2], follow_symlinks=False)
        if (repeated != payload or repeated_digest != digest
                or _fingerprint(before) != _fingerprint(after)
                or _fingerprint(after) != _fingerprint(rebound)):
            raise RuntimeError(f'{label} changed while admitted')
    finally:
        for opened_descriptor in reversed(opened):
            os.close(opened_descriptor)


def _canonical_file(root, descriptor, maximum, deadline, label, lifetime):
    _, payload, value = lifetime.enter_context(
        _bound_file(root, descriptor, maximum, deadline, label))
    parsed = artifacts._json(payload)
    if payload != memory.canonical_bytes(parsed):
        raise ValueError(f'{label} must be canonical JSON')
    return parsed, value


def _conversion(root, descriptor, bundle, operation, run_id, case_id,
                condition, expected_source_identity, deadline, lifetime):
    receipt, bound = _canonical_file(
        root, descriptor, PAIR_CONTRACT['receipt_max_bytes'], deadline,
        f'{operation} conversion receipt', lifetime)
    _fields(receipt, PROTOCOL['schemas']['conversion']['exact_keys'],
            'Conversion receipt')
    if (receipt['schema'] != PROTOCOL['schemas']['conversion']['name']
            or receipt['protocol_sha256'] != PROTOCOL_SHA256
            or receipt['run_id'] != run_id or receipt['case_id'] != case_id
            or receipt['operation'] != operation
            or receipt['condition'] != condition
            or memory.canonical_bytes(receipt['source_identity'])
            != memory.canonical_bytes(expected_source_identity)
            or memory.canonical_bytes(receipt['claims'])
            != memory.canonical_bytes(PROTOCOL['claims'])):
        raise ValueError('Conversion receipt identity differs')
    compact_manifest = _descriptor(
        receipt['compact_manifest'], 'compact manifest')
    if (compact_manifest['path'] != 'manifest.json'
            or compact_manifest['size_bytes'] != len(bundle.get('manifest.json', b''))
            or compact_manifest['sha256'] != hashlib.sha256(
                bundle.get('manifest.json', b'')).hexdigest()):
        raise ValueError('Conversion receipt does not bind the compact manifest')
    raw_descriptor = _descriptor(receipt['raw_audit'], 'raw-audit receipt')
    for name in ('compact_trace_digest', 'legacy_trace_digest'):
        _digest(receipt[name], name)
    return receipt, bound, raw_descriptor


def _inventory(receipt, read, events, snapshot_reference):
    inventory = receipt['raw_inventory']
    limits = raw_audit.RAW_LIMITS[receipt['operation']]
    if (inventory['schema'] != 'memory-family-raw-inventory-v1'
            or inventory['tree_sha256'] != memory.sha256(inventory['files'])
            or inventory['file_count'] != len(inventory['files'])
            or inventory['file_count'] > limits['max_files']
            or any(row['size_bytes'] < 1 for row in inventory['files'])):
        raise ValueError('Raw inventory aggregate differs')
    paths = [row['path'] for row in inventory['files']]
    if paths != sorted(paths) or len(paths) != len(set(paths)):
        raise ValueError('Raw inventory paths are not one sorted set')
    recording_bytes = sum(row['size_bytes'] for row in inventory['files']
                          if row['path'].startswith('recording/'))
    support_bytes = sum(row['size_bytes'] for row in inventory['files']) \
        - recording_bytes
    if (inventory['recording_bytes'] != recording_bytes
            or inventory['support_bytes'] != support_bytes
            or inventory['total_bytes'] != recording_bytes + support_bytes
            or recording_bytes > limits['recording_max_bytes']):
        raise ValueError('Raw inventory byte totals differ')
    by_path = {row['path']: row for row in inventory['files']}
    expected_paths = {
        'recording/manifest.json', 'recording/events.jsonl',
        'worker-report.json',
        *(f"recording/{event['path']}" for event in events
          if event['kind'] == 'chunk'),
        *({'snapshots/initial.snp'}
          if receipt['operation'] == 'source' else set()),
    }
    if set(by_path) != expected_paths:
        raise ValueError('Raw inventory paths differ from compact legacy evidence')
    if (by_path['recording/events.jsonl']['size_bytes']
            > limits['events_max_bytes']
            or by_path['worker-report.json']['size_bytes']
            > limits['report_max_bytes']):
        raise ValueError('Raw inventory metadata exceeds its frozen limit')
    for path, payload in (
        ('recording/manifest.json', read['legacy_manifest_bytes']),
        ('recording/events.jsonl', read['legacy_events_bytes']),
    ):
        if by_path[path] != {
                'path': path, 'size_bytes': len(payload),
                'sha256': hashlib.sha256(payload).hexdigest()}:
            raise ValueError('Raw metadata descriptor differs from compact bytes')
    for event in events:
        if event['kind'] == 'chunk' and by_path[f"recording/{event['path']}"][
                'sha256'] != event['sha256']:
            raise ValueError('Raw chunk inventory differs from its legacy event')
    if receipt['operation'] == 'source':
        snapshot = by_path['snapshots/initial.snp']
        if ({key: snapshot[key] for key in ('size_bytes', 'sha256')}
                != {key: snapshot_reference[key]
                    for key in ('size_bytes', 'sha256')}):
            raise ValueError('Raw snapshot inventory differs from compact reference')


def _projection(rows):
    return [{
        'episode': int(row['episode']), 'tick': int(row['tick']),
        'pose': row['pose'].tolist(), 'next_pose': row['next_pose'].tolist(),
    } for row in rows]


def _raw_receipt(root, descriptor, operation, run_id, case_id, condition,
                 expected_source_identity, deadline, lifetime):
    receipt, bound = _canonical_file(
        root, descriptor, raw_audit.RAW_CONTRACT['receipt_max_bytes'], deadline,
        f'{operation} raw-audit receipt', lifetime)
    raw_audit._validate_receipt_shape(receipt)
    if (receipt['run_id'] != run_id or receipt['case_id'] != case_id
            or receipt['operation'] != operation
            or receipt['condition'] != condition
            or memory.canonical_bytes(receipt['source_identity'])
            != memory.canonical_bytes(expected_source_identity)
            or receipt['policy_result']['status'] != 'exhaustive-pass'):
        raise ValueError('Raw-audit receipt identity differs')
    return receipt, bound


def _terminal(receipt, legacy_manifest, snapshot_reference, source_run_id, *,
              projection, application=None, case=None, events=None,
              schedule=None):
    terminal = receipt['terminal_state']
    status = legacy_manifest['status']
    _digest(terminal['world_state_sha256'], 'terminal world-state SHA-256')
    if (terminal['manifest_status'] != status
            or terminal['snapshot_sha256'] != snapshot_reference['sha256']
            or terminal['source_run_id'] != source_run_id
            or terminal['replacement'] is not False
            or legacy_manifest.get('final_phase') != terminal['final_phase']
            or legacy_manifest.get('total_tick') != terminal['total_ticks']
            or legacy_manifest.get('recorded_ticks') != len(projection)):
        raise ValueError('Raw terminal state differs from compact lineage')
    if receipt['operation'] == 'source':
        source_world = world.validate_state(legacy_manifest.get('world_state'))
        if (status != 'completed' or terminal['final_phase'] != 'paused'
                or terminal['natural_failure'] is not False
                or application is None
                or source_world != application['world_task_state']
                or terminal['world_state_sha256'] != memory.sha256(source_world)
                or terminal['total_ticks'] != application['episode_step']
                or terminal['last_tick'] != projection[-1]['tick']
                or source_world['last_tick'] != terminal['last_tick']):
            raise ValueError('Source terminal state is not a completed boundary')
        return source_world
    post_world = world.validate_state(legacy_manifest.get('world_state'))
    if (case is None or events is None or schedule is None
            or post_world['case'] != case
            or post_world['profile_sha256'] != case['profile_sha256']
            or terminal['world_state_sha256'] != memory.sha256(post_world)
            or terminal['last_tick'] != post_world['last_tick']):
        raise ValueError('Condition terminal world state differs')
    if status == 'failed':
        if (terminal['final_phase'] != 'failed'
                or terminal['natural_failure'] is not True):
            raise ValueError('Failed condition is not an admitted natural failure')
    elif (status != 'completed' or terminal['natural_failure'] is not False
          or terminal['final_phase'] == 'failed'):
        raise ValueError('Completed condition terminal state differs')
    raw_audit._condition_terminal(
        {'events': events, 'manifest': legacy_manifest}, case, projection,
        terminal, schedule)
    return post_world


def _cross_bind(receipt, read, events, projection, snapshot_reference,
                source_application, schedule):
    manifest = read['manifest']
    if (receipt['row_count'] != manifest['row_count']
            or receipt['chunk_count'] != manifest['chunk_count']
            or receipt['event_count'] != manifest['event_count']
            or receipt['camera_sequence_sha256']
            != manifest['camera_sequence_sha256']
            or receipt['row_sequence_sha256']
            != manifest['row_sequence_sha256']):
        raise ValueError('Raw receipt counts or sequences differ from compact')
    oracle_result = receipt['oracle_result']
    calls = raw_audit._policy_calls(events)
    bindings_sha256 = memory.sha256([{
        key: event[key] for key in (
            'tick', 'observation_sha256', 'cameras_sha256', 'result_sha256')
    } for event in calls])
    if (receipt['policy_result']['call_count'] != len(calls)
            or receipt['policy_result']['bindings_sha256']
            != bindings_sha256):
        raise ValueError('Raw policy result differs from compact events')
    expected_status = ('source-boundary-pass'
                       if receipt['operation'] == 'source'
                       else 'condition-local-pass')
    if (oracle_result['status'] != expected_status
            or oracle_result['pair_admission'] is not False
            or oracle_result['events_sha256'] != memory.sha256(events)
            or oracle_result['rows_sha256'] != memory.sha256(projection)
            or oracle_result['schedule_sha256']
            != (None if schedule is None else memory.sha256(schedule))
            or oracle_result['source_application_sha256']
            != (None if source_application is None
                else memory.sha256(source_application))):
        raise ValueError('Raw local oracle result differs from compact evidence')
    _inventory(receipt, read, events, snapshot_reference)


def _history(root, descriptor, deadline, role, lifetime):
    bundle, bound = _canonical_file(
        root, descriptor, PAIR_CONTRACT['history_max_bytes'], deadline,
        f'{role} history bundle', lifetime)
    _fields(bundle, {'e', 'u', 'history_sha256'}, 'History bundle')
    history = memory.validate_e(bundle['e'])
    recorded = memory.validate_u(bundle['u'])
    fitted = memory.fit(history)
    if (bundle['history_sha256'] != memory.sha256(history)
            or memory.canonical_bytes(recorded) != memory.canonical_bytes(fitted)):
        raise ValueError('History bundle differs from an E-only refit')
    return {'e': history, 'u': fitted,
            'history_sha256': bundle['history_sha256'],
            'descriptor': bound}


def _source_application(root, reference, source_read, source_events,
                        source_projection, case, source_run_id, deadline, lifetime):
    descriptor = {key: reference[key] for key in ('path', 'size_bytes', 'sha256')}
    file_descriptor, _, _ = lifetime.enter_context(_bound_file(
        root, descriptor, compact.SNAPSHOT_MAX_BYTES, deadline, 'source snapshot'))
    try:
        snapshot = snapshots.read_snapshot(Path(f'/proc/self/fd/{file_descriptor}'))
    except (OSError, TypeError, ValueError) as error:
        raise ValueError('Source snapshot is invalid') from error
    application = snapshot.get('application') if type(snapshot) is dict else None
    if type(application) is not dict or set(application) != oracle.APPLICATION_FIELDS:
        raise ValueError('Source snapshot lacks its exact application state')
    boundary = application['episode_step']
    if (application['schema_version'] != 8
            or application['source_run_id'] != source_run_id
            or application['scenario'] != world.SCENARIO
            or application['controller'] != 'flynn'
            or application['episode'] != 0
            or type(boundary) is not int or not 0 < boundary <= 2100
            or application['phase'] != 'paused'
            or application['seed'] != case['seed']
            or application['texture'] != 'checker'
            or application['execution_mode'] not in ('live', 'policy')
            or application['eyes'] != {'left': True, 'right': True}
            or application['last_outcome'] is not None
            or application['episode_finished'] is not False
            or application['session_exhausted'] is not False
            or application['recording_failed'] is not False
            or application['event_prefix']
            != source_read['manifest']['snapshot_event_prefix']
            or application['pending_commands'] != []
            or type(application['original_commands']) is not dict
            or type(application['receipts']) is not dict):
        raise ValueError('Source application identity differs')
    task = memory_decision.validate_state(application['memory'])
    source_world = world.validate_state(application['world_task_state'])
    if (application['total_tick'] != boundary
            or task['cursor']['tick'] != boundary - 1
            or source_world['case'] != case
            or source_world['last_tick'] != boundary - 1):
        raise ValueError('Source application boundary differs')
    oracle._source_evidence(
        case, application, source_events, copy.deepcopy(source_projection))
    return application, task, boundary


def _single(events, kind, label):
    found = [(index, event) for index, event in enumerate(events)
             if event.get('kind') == kind]
    if len(found) != 1:
        raise ValueError(f'{label} requires exactly one {kind} event')
    return found[0]


def _prior_own(root, descriptor, case, source_run_id, application,
               source_events, source_projection, snapshot_reference, deadline,
               source_receipt, histories, lifetime):
    receipt, bound = _canonical_file(
        root, descriptor, PAIR_CONTRACT['receipt_max_bytes'], deadline,
        'prior-own pair receipt', lifetime)
    _fields(receipt, PROTOCOL['schemas']['pair_admission']['exact_keys'],
            'Prior-own pair receipt')
    oracle_result = receipt.get('oracle_result')
    _fields(oracle_result,
            PAIR_CONTRACT['nested_schemas']['oracle_result']['exact_keys'],
            'Prior-own oracle result')
    digest_fields = (
        'proof_sha256', 'source_application_sha256',
        'source_events_sha256', 'source_rows_sha256',
        'condition_events_sha256', 'condition_rows_sha256',
        'condition_world_state_sha256', 'schedule_sha256',
        'recorded_selection_sha256', 'gold_target_ids_sha256',
    )
    for name in digest_fields:
        _digest(oracle_result[name], f'prior-own oracle {name}')
    _run_id(receipt.get('source_run_id'))
    _run_id(receipt.get('condition_run_id'))
    compact._snapshot(receipt['snapshot_reference'], 'condition',
                      receipt['condition_run_id'], case['case_id'])
    for name in ('source_receipt', 'condition_receipt'):
        _fields(receipt[name],
                PAIR_CONTRACT['nested_schemas']['receipt_identity']['exact_keys'],
                f'Prior-own {name}')
        for child in receipt[name].values():
            _descriptor(child, f'Prior-own {name} descriptor')
    for name in ('history_identity', 'resource_identity', 'selector_identity',
                 'u_identity'):
        _fields(receipt[name], PAIR_CONTRACT['nested_schemas'][name]['exact_keys'],
                f'Prior-own {name}')
    own_selector = {
        'version': 1, 'condition': 'own', 'limit': 1, 'resource': None,
        'resource_sha256': memory.sha256(None),
        'provenance_sha256': histories['own']['descriptor']['sha256'],
    }
    task = application['memory']
    expected_own = _condition_mapping('own', task, {
        'selector': own_selector, 'u': histories['own']['u'],
        'retained_memory_sha256': memory.sha256({
            key: value for key, value in task.items()
            if key not in ('u', 'selector')}),
    }, histories, None)
    if (receipt['source_receipt'] != source_receipt
            or any(receipt[name] != expected_own[name] for name in (
                'history_identity', 'resource_identity', 'selector_identity',
                'u_identity'))):
        raise ValueError('Prior own source descriptors or selector/U mapping differs')
    gold = oracle_result['gold_target_ids']
    if (receipt['schema'] != PROTOCOL['schemas']['pair_admission']['name']
            or receipt['protocol_sha256'] != PROTOCOL_SHA256
            or receipt['case_id'] != case['case_id']
            or receipt['source_run_id'] != source_run_id
            or receipt['condition_run_id'] == source_run_id
            or receipt['condition'] != 'own'
            or receipt['snapshot_reference'] != snapshot_reference
            or memory.canonical_bytes(receipt['claims'])
            != memory.canonical_bytes(PROTOCOL['claims'])
            or oracle_result['status'] != 'compact-pair-pass'
            or oracle_result['prior_own_receipt'] is not None
            or type(gold) is not list
            or any(type(identifier) is not str for identifier in gold)
            or len(gold) != len(set(gold))
            or oracle_result['gold_target_ids_sha256'] != memory.sha256(gold)
            or oracle_result['source_application_sha256']
            != memory.sha256(application)
            or oracle_result['source_events_sha256']
            != memory.sha256(source_events)
            or oracle_result['source_rows_sha256']
            != memory.sha256(source_projection)
            or receipt['history_identity']['role'] != 'own'
            or receipt['resource_identity'] != {
                'kind': 'none', 'sha256': memory.sha256(None)}
            or receipt['u_identity']['kind'] != 'own-history'):
        raise ValueError('Prior own oracle evidence differs from this source')
    return receipt, bound


def _condition_mapping(condition, task, configured, histories, prior_own):
    selector = configured.get('selector')
    u = memory.validate_u(configured.get('u'))
    selector = memory_task.validate_selector(selector, task['m'], u)
    retained = {key: value for key, value in task.items()
                if key not in ('u', 'selector')}
    if (selector['condition'] != condition
            or configured.get('retained_memory_sha256')
            != memory.sha256(retained)):
        raise ValueError('Condition selector or retained memory differs')

    if condition == 'oracle':
        if prior_own is None:
            raise ValueError('Oracle condition requires prior admitted own evidence')
        prior_result = prior_own[0]['oracle_result']
    else:
        if prior_own is not None:
            raise ValueError('Only the oracle condition accepts a prior-own receipt')
        prior_result = None

    empty = memory.artifact(method='empty-v1')
    if condition == 'swapped':
        role, expected_u = 'swapped', histories['swapped']['u']
    elif condition in ('own', 'sham'):
        role, expected_u = 'own', histories['own']['u']
    elif condition == 'hand-authored':
        role, expected_u = None, memory.artifact('local_cue')
    else:
        role, expected_u = None, empty
    if condition == 'retrieval':
        role, resource, resource_kind = 'own', histories['own']['e'], 'history'
    elif condition == 'oracle':
        resource = prior_result['gold_target_ids']
        resource_kind = 'gold-target-ids'
    else:
        resource, resource_kind = None, 'none'
    provenance = (
        histories['swapped']['descriptor']['sha256'] if condition == 'swapped'
        else histories['own']['descriptor']['sha256']
        if condition in ('own', 'sham', 'retrieval')
        else prior_result['proof_sha256'] if condition == 'oracle'
        else memory_experiment.PROTOCOL_SHA256)
    expected_selector = {
        'version': 1, 'condition': condition, 'limit': 1,
        'resource': copy.deepcopy(resource),
        'resource_sha256': memory.sha256(resource),
        'provenance_sha256': provenance,
    }
    if (memory.canonical_bytes(u) != memory.canonical_bytes(expected_u)
            or memory.canonical_bytes(selector)
            != memory.canonical_bytes(expected_selector)):
        raise ValueError('Recorded condition selector/U mapping differs')

    history_identity = {
        'role': role,
        'history_sha256': (None if role is None
                           else histories[role]['history_sha256']),
        'bundle_sha256': (None if role is None
                          else histories[role]['descriptor']['sha256']),
    }
    u_kind = ('own-history' if condition in ('own', 'sham')
              else 'swapped-history' if condition == 'swapped'
              else 'hand-authored' if condition == 'hand-authored'
              else 'empty')
    return {
        'selector': selector, 'u': u,
        'history_identity': history_identity,
        'resource_identity': {
            'kind': resource_kind, 'sha256': memory.sha256(resource)},
        'selector_identity': {
            'sha256': memory.sha256(selector),
            'provenance_sha256': provenance},
        'u_identity': {'kind': u_kind, 'sha256': memory.sha256(u)},
    }


def _trigger_evidence(condition, case, events, packets, schedule, m,
                      selector, u):
    details = [(index, event, event.get('detail', {}))
               for index, event in enumerate(events)
               if event.get('kind') == 'memory_decision']
    triggers = [(index, event, detail) for index, event, detail in details
                if detail.get('kind') == 'memory_trigger']
    selections = [(index, event, detail) for index, event, detail in details
                  if detail.get('kind') == 'memory_selection']
    if case['kind'] == 'no-event':
        if triggers or selections:
            raise ValueError('No-event condition invoked its selector')
        return None, None
    event_tick = schedule['event_tick']
    by_tick = {packet['tick']: packet for packet in packets}
    if event_tick - 1 not in by_tick or event_tick not in by_tick:
        raise ValueError('Scheduled trigger lacks consecutive recorded packets')
    before, after = by_tick[event_tick - 1]['cues'], by_tick[event_tick]['cues']
    if (len(before) != 1 or len(after) != 1
            or before[0]['id'] != case['cue_id']
            or after[0]['id'] != case['cue_id']
            or before[0]['state'] != 0 or after[0]['state'] != 1):
        raise ValueError('Scheduled trigger lacks consecutive visible cue observations')
    episode_id = next(fact['evidence']['episode_id'] for fact in m['facts'])
    trigger = memory.validate_trigger({
        'id': memory_task._sensor_id(
            episode_id, event_tick, 'trigger', case['cue_id']),
        'episode_id': episode_id, 'tick': event_tick,
        'kind': 'cue_changed', 'cue_id': case['cue_id'],
        'before': 0, 'after': 1,
        'before_observation_id': memory_task._sensor_id(
            episode_id, event_tick - 1, 'cue', case['cue_id']),
        'observation_id': memory_task._sensor_id(
            episode_id, event_tick, 'cue', case['cue_id']),
    })
    if len(triggers) != 1 or len(selections) != 1:
        raise ValueError('Cue event requires one recorded trigger and selection')
    sensed = [index for index, event in enumerate(events)
              if event.get('kind') == 'memory_sensed'
              and event.get('episode_step') == event_tick]
    if len(sensed) != 1 or not sensed[0] < triggers[0][0] < selections[0][0]:
        raise ValueError('Packet, trigger and selection are not ordered')
    for _, event, detail in (triggers[0], selections[0]):
        oracle._event_boundary(event, event_tick, detail['kind'])
    if triggers[0][2] != {
            'kind': 'memory_trigger', 'tick': event_tick,
            'trigger': trigger}:
        raise ValueError('Recorded trigger differs from consecutive cue packets')
    selection_detail = selections[0][2]
    if (set(selection_detail) != {'kind', 'tick', 'selection'}
            or selection_detail['tick'] != event_tick):
        raise ValueError('Recorded selector invocation has an invalid boundary')
    recorded = memory.validate_selection(
        selection_detail['selection'], m, trigger)
    expected = memory_experiment.selection_for_condition(
        condition, m, trigger,
        **memory_task.selector_resources(selector, u),
        limit=selector['limit'])
    if (memory.canonical_bytes(recorded)
            != memory.canonical_bytes(selection_detail['selection'])
            or memory.canonical_bytes(recorded)
            != memory.canonical_bytes(expected)):
        raise ValueError('Recorded selection differs from pure selector replay')
    return trigger, recorded


def _condition_identity(condition, case, application, task, source_events,
                        source_projection, events, projection, post_world,
                        source_run_id, condition_run_id, histories, prior_own):
    restored_index, restored = _single(
        events, 'application_restored', 'Condition continuation')
    configured_index, configured = _single(
        events, 'memory_selector_configured', 'Condition continuation')
    boundary = application['episode_step']
    for event, label in ((restored, 'application_restored'),
                         (configured, 'memory_selector_configured')):
        oracle._event_boundary(event, boundary, label)
    if (restored.get('parent_run_id') != source_run_id
            or restored.get('parent_event_prefix') != application['event_prefix']
            or restored.get('revision') != application['revision']
            or restored.get('eyes') != application['eyes']):
        raise ValueError('Condition did not restore the bound source application')

    mapping = _condition_mapping(
        condition, task, configured, histories, prior_own)
    acquired = copy.deepcopy(application)
    acquired.pop('source_run_id')
    acquired.pop('event_prefix')
    acquired['memory'].pop('u')
    acquired['memory'].pop('selector')
    acquired_state_sha256 = memory.sha256(acquired)
    arm_index, schedule = oracle._schedule(
        case, events, boundary, post_world, acquired_state_sha256)
    if not restored_index < configured_index < arm_index:
        raise ValueError('Condition restore/configure/arm events are not ordered')
    first_sensed = next((index for index, event in enumerate(events)
                         if event.get('kind') == 'memory_sensed'), None)
    if first_sensed is None or arm_index >= first_sensed:
        raise ValueError('Condition arm does not precede continuation sensing')
    if (projection[0]['tick'] != boundary
            or post_world['last_tick'] < schedule['decision_tick']):
        raise ValueError('Condition rows do not bind the declared boundary')

    source_actual_world = artifacts._world_at(
        source_events, 0, boundary - 1, source_projection[-1]['next_pose'])
    restored_world = artifacts._world_at(events, 0, boundary)
    if (source_actual_world != restored_world
            or projection[0]['pose'] != restored_world['pose']):
        raise ValueError('Restored world differs from the acquired source boundary')
    before_geometry, after_geometry = oracle._expected_geometry(case)
    if (source_actual_world['arena'] != world.PROFILE['arena']
            or source_actual_world['goal'][:2] != case['goal_xy']
            or source_actual_world['obstacles'] != before_geometry):
        raise ValueError('Source geometry differs from the frozen family case')
    cue_event, gate_event, intervention_event = oracle._gate_evidence(
        case, events, schedule, post_world)
    after_world = artifacts._world_at(events, 0, schedule['decision_tick'])
    if (after_world['arena'] != source_actual_world['arena']
            or after_world['goal'] != source_actual_world['goal']
            or after_world['obstacles'] != after_geometry):
        raise ValueError('Condition geometry differs at the decision boundary')

    all_packets, _ = oracle._recorded_packets(
        case, events, projection, task['episode_id'],
        event_tick=schedule['event_tick'], gate_result=post_world['gate_result'])
    decision_packets = [packet for packet in all_packets
                        if packet['tick'] <= schedule['decision_tick']]
    if any(sample['passability'] != 'unobserved'
           for packet in decision_packets for sample in packet['passages']):
        raise ValueError('Fresh passage evidence arrived before route commitment')
    trigger, recorded = _trigger_evidence(
        condition, case, events, decision_packets, schedule, task['m'],
        mapping['selector'], mapping['u'])
    commitments = [(index, event) for index, event in enumerate(events)
                   if event.get('kind') == 'memory_decision'
                   and event.get('detail', {}).get('kind') == 'memory_commitment'
                   and event.get('detail', {}).get('tick')
                   == schedule['decision_tick']]
    if len(commitments) != 1:
        raise ValueError('Condition lacks one decision-boundary commitment')
    oracle._event_boundary(
        commitments[0][1], schedule['decision_tick'], 'memory_commitment')
    decision_sensed = [index for index, event in enumerate(events)
                       if event.get('kind') == 'memory_sensed'
                       and event.get('episode_step') == schedule['decision_tick']]
    if len(decision_sensed) != 1 or commitments[0][0] <= decision_sensed[0]:
        raise ValueError('Decision commitment precedes its recorded packet')
    tail_tick = (post_world['last_tick']
                 if post_world['last_tick'] == projection[-1]['tick'] + 1
                 else None)
    replayed = oracle._replay_post(
        task, mapping['selector'], mapping['u'], boundary, all_packets,
        events, tail_tick)
    oracle._post_tail(
        case, events, projection, post_world, schedule, task['episode_id'],
        replayed)

    before_occupancy = oracle._occupancy(case, before_geometry)
    after_occupancy = oracle._occupancy(case, after_geometry)
    gold = memory_experiment.gold_target_ids(
        task['m'], before_occupancy, after_occupancy, trigger)
    if ((case['kind'] == 'change' and len(gold) != 1)
            or (case['kind'] != 'change' and gold)):
        raise ValueError('Family event does not produce its declared oracle target')
    event_packet_index = next((index for index, event in enumerate(events)
        if event.get('kind') == 'memory_sensed'
        and event.get('episode_step') == schedule['event_tick']), None)
    if (case['event_enabled']
            and (event_packet_index is None or cue_event[0] >= event_packet_index)):
        raise ValueError('Cue transition does not precede its symbolic packet')
    if gate_event is not None and gate_event[0] >= event_packet_index:
        raise ValueError('Gate edit does not precede its symbolic packet')
    if intervention_event is not None \
            and intervention_event[0] >= event_packet_index:
        raise ValueError('Intervention does not precede its symbolic packet')

    if prior_own is not None and (
            prior_own[0]['oracle_result']['gold_target_ids'] != gold
            or prior_own[0]['oracle_result']['gold_target_ids_sha256']
            != memory.sha256(gold)):
        raise ValueError('Prior own oracle result differs from derived condition oracle')
    mapping.pop('selector')
    mapping.pop('u')
    proof = {
        'case_id': case['case_id'], 'source_run_id': source_run_id,
        'condition_run_id': condition_run_id, 'condition': condition,
        'source_application_sha256': memory.sha256(application),
        'source_events_sha256': memory.sha256(source_events),
        'source_rows_sha256': memory.sha256(source_projection),
        'condition_events_sha256': memory.sha256(events),
        'condition_rows_sha256': memory.sha256(projection),
        'condition_world_state_sha256': memory.sha256(post_world),
        'schedule': schedule, 'selector_identity': mapping['selector_identity'],
        'u_identity': mapping['u_identity'],
        'trigger': trigger,
        'recorded_selection_sha256': memory.sha256(recorded),
        'before_world_sha256': memory.sha256(source_actual_world),
        'after_world_sha256': memory.sha256(after_world),
        'gold_target_ids': gold,
    }
    memory._bounded(proof, 256 * 1024)
    return {
        **mapping, 'schedule': schedule, 'proof_sha256': memory.sha256(proof),
        'recorded_selection_sha256': memory.sha256(recorded),
        'gold_target_ids': gold,
        'gold_target_ids_sha256': memory.sha256(gold),
        'condition_world_state_sha256': memory.sha256(post_world),
    }


def admit_compact_pair(*, case, source_bundle, condition_bundle,
                       source_run_id, condition_run_id, condition,
                       source_conversion_receipt,
                       condition_conversion_receipt, evidence_root,
                       history_bundles, owner_source_sha256, deadline,
                       prior_own_receipt=None):
    """Validate and return one exact compact-pair receipt without writing."""
    with ExitStack() as lifetime:
        _public_deadline(deadline)
        case = world.validate_case(copy.deepcopy(case))
        if case['version'] != 3 or case.get('split') != 'development':
            raise ValueError('Compact pair requires a development family-v3 case')
        source_run_id = _run_id(source_run_id)
        condition_run_id = _run_id(condition_run_id)
        if source_run_id == condition_run_id:
            raise ValueError('Source and condition runs must be distinct')
        if condition not in PROTOCOL['analysis_contract']['conditions']:
            raise ValueError('Unknown compact-pair condition')
        _digest(owner_source_sha256, 'owner source SHA-256')
        if type(history_bundles) is not dict or set(history_bundles) != {'own', 'swapped'}:
            raise ValueError('Compact pair requires exact own/swapped history descriptors')

        expected_source_identity = raw_audit.canonical_source_identity(
            owner_source_sha256)
        source_conversion, source_conversion_bound, source_raw_descriptor = _conversion(
            evidence_root, source_conversion_receipt, source_bundle, 'source',
            source_run_id, case['case_id'], None, expected_source_identity, deadline, lifetime)
        condition_conversion, condition_conversion_bound, condition_raw_descriptor = _conversion(
            evidence_root, condition_conversion_receipt, condition_bundle,
            'condition', condition_run_id, case['case_id'], condition,
            expected_source_identity, deadline, lifetime)
        source_raw, source_raw_bound = _raw_receipt(
            evidence_root, source_raw_descriptor, 'source', source_run_id,
            case['case_id'], None, expected_source_identity, deadline, lifetime)
        condition_raw, condition_raw_bound = _raw_receipt(
            evidence_root, condition_raw_descriptor, 'condition', condition_run_id,
            case['case_id'], condition, expected_source_identity, deadline, lifetime)
        receipt_paths = {
            source_conversion_bound['path'], condition_conversion_bound['path'],
            source_raw_bound['path'], condition_raw_bound['path'],
        }
        if len(receipt_paths) != 4:
            raise ValueError('Source and condition receipts must use distinct paths')

        source_read = compact.read_compact(
            source_bundle, raw_audit_receipt=source_raw)
        condition_read = compact.read_compact(
            condition_bundle, raw_audit_receipt=condition_raw)
        if (source_read['manifest']['run_id'] != source_run_id
                or source_read['manifest']['case_id'] != case['case_id']
                or source_read['manifest']['operation'] != 'source'
                or source_read['manifest']['condition'] is not None
                or condition_read['manifest']['run_id'] != condition_run_id
                or condition_read['manifest']['case_id'] != case['case_id']
                or condition_read['manifest']['operation'] != 'condition'
                or condition_read['manifest']['condition'] != condition):
            raise ValueError('Compact bundle identity differs')
        if (source_conversion['compact_trace_digest'] != source_read['trace_digest']
                or source_conversion['legacy_trace_digest'] != source_read['trace_digest']
                or condition_conversion['compact_trace_digest']
                != condition_read['trace_digest']
                or condition_conversion['legacy_trace_digest']
                != condition_read['trace_digest']):
            raise ValueError('Conversion trace digest differs from compact replay')

        source_reference = source_read['snapshot_reference']
        condition_reference = condition_read['snapshot_reference']
        if (condition_reference != {
                **source_reference, 'kind': 'shared-source',
                'source_receipt_sha256': source_conversion_bound['sha256']}):
            raise ValueError('Condition does not bind the one source snapshot/receipt')

        source_events = compact._legacy_events(
            source_read['legacy_events_bytes'], 'source')
        condition_events = compact._legacy_events(
            condition_read['legacy_events_bytes'], 'condition')
        oracle._events(copy.deepcopy(source_events), source_run_id, 'source compact events')
        oracle._events(copy.deepcopy(condition_events), condition_run_id,
                       'condition compact events')
        source_projection = _projection(source_read['rows'])
        condition_projection = _projection(condition_read['rows'])
        oracle._rows(copy.deepcopy(source_projection), 0, 'source compact rows')

        application, task, boundary = _source_application(
            evidence_root, source_reference, source_read, source_events,
            source_projection, case, source_run_id, deadline, lifetime)
        oracle._rows(copy.deepcopy(condition_projection), boundary,
                     'condition compact rows')
        histories = {
            role: _history(evidence_root, history_bundles[role], deadline, role, lifetime)
            for role in ('own', 'swapped')}
        if (histories['own']['descriptor']['path']
                == histories['swapped']['descriptor']['path']
                or memory_experiment._ids(histories['own']['e'])
                & memory_experiment._ids(histories['swapped']['e'])):
            raise ValueError('Own/swapped history namespaces must be disjoint')

        source_legacy_manifest = artifacts._json(
            source_read['legacy_manifest_bytes'])
        condition_legacy_manifest = artifacts._json(
            condition_read['legacy_manifest_bytes'])
        _terminal(
            source_raw, source_legacy_manifest, source_reference, None,
            projection=source_projection, application=application)
        post_world = world.validate_state(
            condition_legacy_manifest.get('world_state'))
        prior_own = None
        if condition == 'oracle':
            if prior_own_receipt is None:
                raise ValueError('Oracle condition requires a prior-own receipt')
            prior_own = _prior_own(
                evidence_root, prior_own_receipt, case, source_run_id,
                application, source_events, source_projection, condition_reference,
                deadline, {'conversion': source_conversion_bound,
                           'raw_audit': source_raw_bound}, histories, lifetime)
            if prior_own[1]['path'] in receipt_paths:
                raise ValueError('Prior-own and current receipt paths must be distinct')
        elif prior_own_receipt is not None:
            raise ValueError('Only the oracle condition accepts a prior-own receipt')
        identities = _condition_identity(
            condition, case, application, task, source_events, source_projection,
            condition_events, condition_projection, post_world, source_run_id,
            condition_run_id, histories, prior_own)
        _terminal(
            condition_raw, condition_legacy_manifest, condition_reference,
            source_run_id, projection=condition_projection, case=case,
            events=condition_events, schedule=identities['schedule'])
        _cross_bind(source_raw, source_read, source_events, source_projection,
                    source_reference, application, None)
        _cross_bind(condition_raw, condition_read, condition_events,
                    condition_projection, condition_reference, None,
                    identities['schedule'])

        receipt_schema = PAIR_CONTRACT['nested_schemas']['receipt_identity'][
            'exact_keys']
        source_receipt = {
            'conversion': source_conversion_bound, 'raw_audit': source_raw_bound}
        condition_receipt = {
            'conversion': condition_conversion_bound,
            'raw_audit': condition_raw_bound}
        _fields(source_receipt, receipt_schema, 'Source receipt identity')
        _fields(condition_receipt, receipt_schema, 'Condition receipt identity')
        result = {
            'schema': PROTOCOL['schemas']['pair_admission']['name'],
            'protocol_sha256': PROTOCOL_SHA256,
            'case_id': case['case_id'], 'source_run_id': source_run_id,
            'condition_run_id': condition_run_id, 'condition': condition,
            'source_receipt': source_receipt,
            'condition_receipt': condition_receipt,
            'snapshot_reference': copy.deepcopy(condition_reference),
            'history_identity': identities['history_identity'],
            'resource_identity': identities['resource_identity'],
            'selector_identity': identities['selector_identity'],
            'u_identity': identities['u_identity'],
            'oracle_result': {
                'status': 'compact-pair-pass',
                'proof_sha256': identities['proof_sha256'],
                'source_events_sha256': memory.sha256(source_events),
                'source_rows_sha256': memory.sha256(source_projection),
                'condition_events_sha256': memory.sha256(condition_events),
                'condition_rows_sha256': memory.sha256(condition_projection),
                'condition_world_state_sha256':
                    identities['condition_world_state_sha256'],
                'schedule_sha256': memory.sha256(identities['schedule']),
                'source_application_sha256': memory.sha256(application),
                'recorded_selection_sha256':
                    identities['recorded_selection_sha256'],
                'gold_target_ids': identities['gold_target_ids'],
                'gold_target_ids_sha256': identities['gold_target_ids_sha256'],
                'prior_own_receipt': (None if prior_own is None
                                      else prior_own[1]),
            },
            'claims': copy.deepcopy(PROTOCOL['claims']),
        }
        _fields(result, PROTOCOL['schemas']['pair_admission']['exact_keys'],
                'Compact-pair admission receipt')
        for name in ('history_identity', 'resource_identity', 'selector_identity',
                     'u_identity', 'oracle_result'):
            _fields(result[name], PAIR_CONTRACT['nested_schemas'][name]['exact_keys'],
                    name)
    _deadline(deadline)
    return result
