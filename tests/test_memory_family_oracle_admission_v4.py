"""Synthetic compact-pair admission checks; no owner or retained data is used."""
import copy
import hashlib
import importlib
import math
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import numpy as np
import pytest

from palimpsest import artifacts, memory, memory_decision as decision
from palimpsest import memory_experiment, memory_task, snapshots
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_raw_audit_v4 as raw_audit
from test_memory_family_compact_v4 import _row
from test_memory_family_oracle_v3 import _packet, evidence


ROOT = Path(__file__).parents[1]
PROTOCOL_PATH = ROOT / 'docs/plans/memory-family-compact-evidence-v4-protocol.json'
OWNER_SOURCE_SHA256 = 'd' * 64
CONDITIONS = tuple(compact.PROTOCOL['analysis_contract']['conditions'])


def _admission():
    try:
        return importlib.import_module('scripts.memory_family_oracle_admission_v4')
    except ModuleNotFoundError:
        pytest.fail('memory_family_oracle_admission_v4 is not implemented',
                    pytrace=False)


def _descriptor(path, payload):
    return {'path': Path(path).as_posix(), 'size_bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest()}


def _write(root, relative, value):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = value if type(value) is bytes else memory.canonical_bytes(value)
    path.write_bytes(payload)
    return _descriptor(relative, payload)


def _tree_hashes(root):
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(
            path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*')) if path.is_file()
    }


def _raw_rows(projection):
    rows = []
    for projected in projection:
        row = _row(projected['tick'])
        row['pose'] = np.asarray(projected['pose'], np.float64)
        row['next_pose'] = np.asarray(projected['next_pose'], np.float64)
        rows.append(row)
    return rows


def _legacy(run_id, rows, supplied_events, *, status='completed',
            world_state, final_phase='paused', last_outcome=None,
            parent_run_id=None, parent_event_prefix=None):
    arrays = {
        name: {'dtype': value.dtype.str, 'shape': list(value.shape)}
        for name, value in rows[0].items() if name not in {'episode', 'tick'}
    }
    events = [copy.deepcopy(event) for event in supplied_events
              if event.get('kind') != 'chunk']
    chunks = []
    for index, offset in enumerate(range(0, len(rows), compact.CHUNK_ROWS)):
        chunks.append({
            'kind': 'chunk', 'path': f'chunks/{index:06d}.npz',
            'sha256': f'{index + 101:064x}', 'episode': 0,
            'start': rows[offset]['tick'],
            'count': min(compact.CHUNK_ROWS, len(rows) - offset),
            'arrays': arrays,
        })
    # A chunk before later semantic events proves admission reparses the full
    # legacy stream rather than requiring compact.read_compact()['events'] to
    # have contiguous sequence numbers.
    events[1:1] = chunks
    for sequence, event in enumerate(events):
        event['sequence'] = sequence
        if event['kind'] != 'chunk':
            event['run_id'] = run_id
    manifest = memory.canonical_bytes({
        'run_id': run_id, 'status': status,
        'recording_format': 'palimpsest-npz-v1',
        'recorded_ticks': len(rows), 'recorded_chunks': len(chunks),
        'recorded_events': len(events),
        'world_state': copy.deepcopy(world_state),
        'final_phase': final_phase, 'total_tick': rows[-1]['tick'] + 1,
        'last_outcome': copy.deepcopy(last_outcome),
        'parent_run_id': parent_run_id,
        'parent_event_prefix': copy.deepcopy(parent_event_prefix),
    }) + b'\n'
    event_bytes = b''.join(memory.canonical_bytes(event) + b'\n'
                           for event in events)
    return manifest, event_bytes, events


def _sequence_hash(rows, names):
    digest = hashlib.sha256()
    for row in rows:
        for name in names:
            if name == 'row':
                value = {key: child for key, child in row.items()
                         if key not in {'latency', 'step_latency'}}
                digest.update(bytes.fromhex(snapshots.state_digest(value)))
            else:
                digest.update(bytes.fromhex(snapshots.state_digest(row[name])))
    return digest.hexdigest()


def _projection(rows):
    return [{
        'episode': int(row['episode']), 'tick': int(row['tick']),
        'pose': row['pose'].tolist(), 'next_pose': row['next_pose'].tolist(),
    } for row in rows]


def _inventory(operation, legacy_manifest, legacy_events, events,
               snapshot_descriptor=None):
    files = [
        _descriptor('recording/manifest.json', legacy_manifest),
        _descriptor('recording/events.jsonl', legacy_events),
        {'path': 'worker-report.json', 'size_bytes': 1, 'sha256': 'e' * 64},
    ]
    files.extend({
        'path': f"recording/{event['path']}", 'size_bytes': 1,
        'sha256': event['sha256'],
    } for event in events if event['kind'] == 'chunk')
    if operation == 'source':
        files.append({
            'path': 'snapshots/initial.snp',
            'size_bytes': snapshot_descriptor['size_bytes'],
            'sha256': snapshot_descriptor['sha256'],
        })
    files.sort(key=lambda row: row['path'])
    recording_bytes = sum(row['size_bytes'] for row in files
                          if row['path'].startswith('recording/'))
    support_bytes = sum(row['size_bytes'] for row in files) - recording_bytes
    return {
        'schema': 'memory-family-raw-inventory-v1', 'files': files,
        'file_count': len(files), 'recording_bytes': recording_bytes,
        'support_bytes': support_bytes,
        'total_bytes': recording_bytes + support_bytes,
        'tree_sha256': memory.sha256(files),
    }


def _raw_receipt(*, run_id, case, operation, condition, rows, events,
                 legacy_manifest, legacy_events, source_identity,
                 snapshot_descriptor, source_run_id, source_application,
                 schedule, world_state, natural_failure=False):
    terminal = {
        'manifest_status': 'failed' if natural_failure else 'completed',
        'final_phase': 'failed' if natural_failure else 'paused',
        'total_ticks': rows[-1]['tick'] + 1,
        'last_tick': rows[-1]['tick'] + (1 if natural_failure else 0),
        'natural_failure': natural_failure, 'replacement': False,
        'world_state_sha256': memory.sha256(world_state),
        'snapshot_sha256': snapshot_descriptor['sha256'],
        'source_run_id': source_run_id,
    }
    projected = _projection(rows)
    calls = [event for event in events
             if event['kind'] == 'neural_policy_call']
    return {
        'schema': 'memory-family-raw-audit-v4',
        'protocol_sha256': compact.PROTOCOL_SHA256,
        'run_id': run_id, 'case_id': case['case_id'],
        'operation': operation, 'condition': condition,
        'row_count': len(rows),
        'chunk_count': sum(event['kind'] == 'chunk' for event in events),
        'event_count': len(events),
        'camera_sequence_sha256': _sequence_hash(
            rows, ('cam_left', 'cam_right', 'raw_cam_left', 'raw_cam_right')),
        'row_sequence_sha256': _sequence_hash(rows, ('row',)),
        'raw_inventory': _inventory(
            operation, legacy_manifest, legacy_events, events,
            snapshot_descriptor),
        'terminal_state': terminal,
        'policy_result': {
            'status': 'exhaustive-pass',
            'call_count': len(calls),
            'bindings_sha256': memory.sha256([{
                key: event[key] for key in (
                    'tick', 'observation_sha256', 'cameras_sha256',
                    'result_sha256')
            } for event in calls]),
        },
        'oracle_result': {
            'status': ('source-boundary-pass' if operation == 'source'
                       else 'condition-local-pass'),
            'pair_admission': False,
            'events_sha256': memory.sha256(events),
            'rows_sha256': memory.sha256(projected),
            'schedule_sha256': (None if schedule is None
                                else memory.sha256(schedule)),
            'source_application_sha256': (
                memory.sha256(source_application)
                if operation == 'source' else None),
        },
        'source_identity': copy.deepcopy(source_identity),
        'claims': copy.deepcopy(compact.PROTOCOL['claims']),
    }


def _histories(root, case):
    other = next(relation for relation in memory.RELATIONS
                 if relation != case['regime'])
    result = {}
    for role, relation, seed in (
            ('own', case['regime'], 200), ('swapped', other, 1200)):
        history = memory_experiment.make_history(seed, relation)
        fitted = memory.fit(history)
        bundle = {'e': history, 'u': fitted,
                  'history_sha256': memory.sha256(history)}
        descriptor = _write(root, f'histories/{role}.json', bundle)
        result[role] = {'bundle': bundle, 'descriptor': descriptor}
    return result


def _condition_values(condition, case, histories, source_application,
                      prior_own_result=None):
    empty = memory.artifact(method='empty-v1')
    gold = ([] if case['kind'] != 'change' else [next(
        fact['id'] for fact in case['facts']
        if fact['subject_id'] == case['closure_subject_id'])])
    if condition == 'swapped':
        role, u = 'swapped', histories['swapped']['bundle']['u']
    elif condition in ('own', 'sham'):
        role, u = 'own', histories['own']['bundle']['u']
    elif condition == 'hand-authored':
        role, u = None, memory.artifact('local_cue')
    else:
        role, u = None, empty
    if condition == 'retrieval':
        role = 'own'
        resource = histories['own']['bundle']['e']
        resource_kind = 'history'
    elif condition == 'oracle':
        if prior_own_result is None:
            raise ValueError('Oracle fixture requires prior independent evidence')
        resource = copy.deepcopy(
            prior_own_result['oracle_result']['gold_target_ids'])
        resource_kind = 'gold-target-ids'
    else:
        resource, resource_kind = None, 'none'
    provenance = (
        histories['swapped']['descriptor']['sha256'] if condition == 'swapped'
        else histories['own']['descriptor']['sha256']
        if condition in ('own', 'sham', 'retrieval')
        else prior_own_result['oracle_result']['proof_sha256']
        if condition == 'oracle'
        else memory_experiment.PROTOCOL_SHA256)
    selector = {
        'version': 1, 'condition': condition, 'limit': 1,
        'resource': copy.deepcopy(resource),
        'resource_sha256': memory.sha256(resource),
        'provenance_sha256': provenance,
    }
    history_identity = {
        'role': role,
        'history_sha256': (None if role is None else
                           histories[role]['bundle']['history_sha256']),
        'bundle_sha256': (None if role is None else
                          histories[role]['descriptor']['sha256']),
    }
    u_kind = ('own-history' if condition in ('own', 'sham')
              else 'swapped-history' if condition == 'swapped'
              else 'hand-authored' if condition == 'hand-authored'
              else 'empty')
    expected = {
        'history_identity': history_identity,
        'resource_identity': {
            'kind': resource_kind, 'sha256': memory.sha256(resource)},
        'selector_identity': {
            'sha256': memory.sha256(selector),
            'provenance_sha256': provenance,
        },
        'u_identity': {'kind': u_kind, 'sha256': memory.sha256(u)},
        'gold_target_ids_sha256': memory.sha256(gold),
    }
    return selector, u, expected


def _condition_events(sample, condition, run_id, selector, u,
                      source_application, *, natural_failure=False):
    events = copy.deepcopy(sample['post_events'])
    configured = next(event for event in events
                      if event['kind'] == 'memory_selector_configured')
    retained = {key: value for key, value in source_application['memory'].items()
                if key not in ('u', 'selector')}
    configured.update(selector=copy.deepcopy(selector), u=copy.deepcopy(u),
                      retained_memory_sha256=memory.sha256(retained))
    restored = next(event for event in events
                    if event['kind'] == 'application_restored')
    restored['parent_run_id'] = source_application['source_run_id']
    restored['parent_event_prefix'] = copy.deepcopy(
        source_application['event_prefix'])
    configured_memory = copy.deepcopy(source_application)
    configured_memory['memory'] = copy.deepcopy(source_application['memory'])
    configured_memory['memory']['u'] = copy.deepcopy(u)
    configured_memory['memory']['selector'] = copy.deepcopy(selector)
    configured_memory.pop('source_run_id')
    configured_memory.pop('event_prefix')
    configured_memory['memory'].pop('u')
    configured_memory['memory'].pop('selector')
    armed = next(event for event in events
                 if event['kind'] == 'memory_decision_armed')
    armed['schedule']['acquired_state_sha256'] = memory.sha256(configured_memory)
    state = decision.configure_selector(source_application['memory'], selector, u)
    state = decision.arm(state, source_application['episode_step'])
    replayed_events = []
    for event in events:
        if event['kind'] == 'memory_decision':
            continue
        replayed_events.append(event)
        if event['kind'] != 'memory_sensed':
            continue
        state, _, audit = decision.advance_memory(state, event['packet'])
        replayed_events.extend({
            'kind': 'memory_decision', 'run_id': run_id,
            'episode': 0, 'episode_step': event['episode_step'],
            'tick': event['tick'], 'detail': copy.deepcopy(detail),
        } for detail in audit)
    events = replayed_events
    last_outcome = None
    if natural_failure:
        supervisor = state['supervisor']
        unavailable = supervisor['waypoint_ids'][supervisor['waypoint_index']]
        pose = sample['post_rows'][-1]['next_pose'].copy()
        pose[2] = math.remainder(pose[2] + math.pi, 2 * math.pi)
        sample['post_rows'][-1]['next_pose'] = pose
        tick = sample['post_world_state']['last_tick'] + 1
        packet = _packet(
            sample['case'], pose, tick,
            event_tick=sample['post_world_state']['event_tick'],
            gate_result=sample['post_world_state']['gate_result'])
        events.append({
            'kind': 'memory_sensed', 'run_id': run_id, 'episode': 0,
            'episode_step': tick, 'tick': tick, 'packet': packet,
        })
        try:
            decision.advance_memory(state, packet)
        except Exception as error:
            if (type(error).__name__ != 'CueUnavailable'
                    or str(error) != 'selected_waypoint_unavailable: ' + unavailable):
                raise
            failure_type, failure_message = type(error).__name__, str(error)
        else:
            raise AssertionError('Natural-failure fixture did not fail naturally')
        last_outcome = {
            'reason': 'runtime_failure', 'episode': 0, 'steps': tick,
            'type': failure_type, 'message': failure_message,
            'policy_diagnostics': {},
        }
        events.append({
            'kind': 'runtime_failure', 'run_id': run_id, 'episode': 0,
            'episode_step': tick, 'tick': tick,
            'error': copy.deepcopy(last_outcome),
        })
        sample['post_world_state']['last_tick'] = tick
    for sequence, event in enumerate(events):
        event['sequence'] = sequence
        event['run_id'] = run_id
    return (events, copy.deepcopy(armed['schedule']),
            copy.deepcopy(sample['post_world_state']), last_outcome)


def _conversion(root, relative, *, run_id, case, operation, condition,
                bundle, raw_descriptor, source_identity):
    manifest = artifacts._json(bundle['manifest.json'])
    value = {
        'schema': 'memory-family-compact-conversion-v1',
        'protocol_sha256': compact.PROTOCOL_SHA256,
        'run_id': run_id, 'case_id': case['case_id'],
        'operation': operation, 'condition': condition,
        'raw_audit': copy.deepcopy(raw_descriptor),
        'compact_manifest': _descriptor('manifest.json', bundle['manifest.json']),
        'compact_trace_digest': manifest['trace_digest'],
        'legacy_trace_digest': manifest['trace_digest'],
        'source_identity': copy.deepcopy(source_identity),
        'claims': copy.deepcopy(compact.PROTOCOL['claims']),
    }
    return value, _write(root, relative, value)


def _fixture(root, condition='own', *, natural_failure=False,
             prior_own_result=None):
    admission = _admission()
    root.mkdir(parents=True, exist_ok=True)
    sample = evidence(row=4, kind='change')
    case = sample['case']
    source_run_id = sample['bindings']['source']['run_id']
    condition_run_id = uuid.uuid5(uuid.NAMESPACE_URL,
                                  'compact-v4-' + condition).hex
    source_rows = _raw_rows(sample['source_rows'])
    source_manifest, source_event_bytes, source_events = _legacy(
        source_run_id, source_rows, sample['source_events'],
        world_state=sample['source_application']['world_task_state'])
    source_application = copy.deepcopy(sample['source_application'])
    source_application['event_prefix'] = {
        'size_bytes': len(source_event_bytes),
        'sha256': hashlib.sha256(source_event_bytes).hexdigest(),
        'event_count': len(source_events),
    }
    snapshot_relative = (
        f"cases/{case['case_id']}/source/snapshots/initial.snp")
    snapshot_path = root / snapshot_relative
    snapshot_path.parent.mkdir(parents=True)
    snapshots.save_snapshot({'application': source_application}, snapshot_path)
    snapshot_payload = snapshot_path.read_bytes()
    snapshot_descriptor = _descriptor(snapshot_relative, snapshot_payload)
    histories = _histories(root, case)
    source_identity = raw_audit.canonical_source_identity(
        OWNER_SOURCE_SHA256)
    source_raw = _raw_receipt(
        run_id=source_run_id, case=case, operation='source', condition=None,
        rows=source_rows, events=source_events,
        legacy_manifest=source_manifest, legacy_events=source_event_bytes,
        source_identity=source_identity,
        snapshot_descriptor=snapshot_descriptor, source_run_id=None,
        source_application=source_application, schedule=None,
        world_state=source_application['world_task_state'])
    source_raw_descriptor = _write(
        root, 'receipts/source.raw-audit.json', source_raw)
    source_snapshot_reference = {
        'kind': 'source', 'source_run_id': source_run_id,
        'source_receipt_sha256': None, 'path': snapshot_relative,
        'size_bytes': snapshot_descriptor['size_bytes'],
        'sha256': snapshot_descriptor['sha256'],
    }
    source_bundle = compact.convert_synthetic(
        run_id=source_run_id, case_id=case['case_id'], operation='source',
        condition=None, rows=source_rows,
        legacy_manifest_bytes=source_manifest,
        legacy_events_bytes=source_event_bytes,
        snapshot_reference=source_snapshot_reference,
        snapshot_event_prefix=source_application['event_prefix'],
        raw_audit_receipt=source_raw)
    source_conversion, source_conversion_descriptor = _conversion(
        root, 'receipts/source.conversion.json', run_id=source_run_id,
        case=case, operation='source', condition=None, bundle=source_bundle,
        raw_descriptor=source_raw_descriptor, source_identity=source_identity)

    selector, u, expected = _condition_values(
        condition, case, histories, source_application, prior_own_result)
    condition_events_base, schedule, condition_world, last_outcome = _condition_events(
        sample, condition, condition_run_id, selector, u,
        source_application, natural_failure=natural_failure)
    condition_rows = _raw_rows(sample['post_rows'])
    status = 'failed' if natural_failure else 'completed'
    condition_manifest, condition_event_bytes, condition_events = _legacy(
        condition_run_id, condition_rows, condition_events_base, status=status,
        world_state=condition_world,
        final_phase='failed' if natural_failure else 'paused',
        last_outcome=last_outcome, parent_run_id=source_run_id,
        parent_event_prefix=source_application['event_prefix'])
    condition_raw = _raw_receipt(
        run_id=condition_run_id, case=case, operation='condition',
        condition=condition, rows=condition_rows, events=condition_events,
        legacy_manifest=condition_manifest,
        legacy_events=condition_event_bytes, source_identity=source_identity,
        snapshot_descriptor=snapshot_descriptor, source_run_id=source_run_id,
        source_application=None, schedule=schedule,
        world_state=condition_world,
        natural_failure=natural_failure)
    condition_raw_descriptor = _write(
        root, 'receipts/condition.raw-audit.json', condition_raw)
    condition_snapshot_reference = {
        'kind': 'shared-source', 'source_run_id': source_run_id,
        'source_receipt_sha256': source_conversion_descriptor['sha256'],
        'path': snapshot_relative, 'size_bytes': snapshot_descriptor['size_bytes'],
        'sha256': snapshot_descriptor['sha256'],
    }
    condition_bundle = compact.convert_synthetic(
        run_id=condition_run_id, case_id=case['case_id'],
        operation='condition', condition=condition, rows=condition_rows,
        legacy_manifest_bytes=condition_manifest,
        legacy_events_bytes=condition_event_bytes,
        snapshot_reference=condition_snapshot_reference,
        event_tick=schedule['event_tick'],
        decision_tick=schedule['decision_tick'],
        raw_audit_receipt=condition_raw)
    condition_conversion, condition_conversion_descriptor = _conversion(
        root, 'receipts/condition.conversion.json', run_id=condition_run_id,
        case=case, operation='condition', condition=condition,
        bundle=condition_bundle, raw_descriptor=condition_raw_descriptor,
        source_identity=source_identity)
    prior_own_descriptor = (None if prior_own_result is None else _write(
        root, 'receipts/prior-own.pair.json', prior_own_result))
    return {
        'root': root, 'case': case, 'condition': condition,
        'source_run_id': source_run_id,
        'condition_run_id': condition_run_id,
        'source_bundle': source_bundle, 'condition_bundle': condition_bundle,
        'source_conversion': source_conversion,
        'condition_conversion': condition_conversion,
        'source_conversion_descriptor': source_conversion_descriptor,
        'condition_conversion_descriptor': condition_conversion_descriptor,
        'source_raw': source_raw, 'condition_raw': condition_raw,
        'snapshot_path': snapshot_path,
        'history_bundles': {
            role: copy.deepcopy(value['descriptor'])
            for role, value in histories.items()},
        'expected': expected, 'natural_failure': natural_failure,
        'condition_world': condition_world, 'schedule': schedule,
        'prior_own_receipt': prior_own_descriptor,
    }


def _request(fixture):
    request = {
        'case': fixture['case'],
        'source_bundle': fixture['source_bundle'],
        'condition_bundle': fixture['condition_bundle'],
        'source_run_id': fixture['source_run_id'],
        'condition_run_id': fixture['condition_run_id'],
        'condition': fixture['condition'],
        'source_conversion_receipt': fixture['source_conversion_descriptor'],
        'condition_conversion_receipt': fixture['condition_conversion_descriptor'],
        'evidence_root': fixture['root'],
        'history_bundles': fixture['history_bundles'],
        'owner_source_sha256': OWNER_SOURCE_SHA256,
        'deadline': time.monotonic() + 30,
    }
    if fixture['prior_own_receipt'] is not None:
        request['prior_own_receipt'] = fixture['prior_own_receipt']
    return request


def _rebind_file(fixture, relative, value):
    descriptor = _write(fixture['root'], relative, value)
    if relative.endswith('source.raw-audit.json'):
        fixture['source_conversion']['raw_audit'] = descriptor
        fixture['source_raw'] = value
        fixture['source_conversion_descriptor'] = _write(
            fixture['root'], 'receipts/source.conversion.json',
            fixture['source_conversion'])
    elif relative.endswith('condition.raw-audit.json'):
        fixture['condition_conversion']['raw_audit'] = descriptor
        fixture['condition_raw'] = value
        fixture['condition_conversion_descriptor'] = _write(
            fixture['root'], 'receipts/condition.conversion.json',
            fixture['condition_conversion'])
    else:
        raise AssertionError(relative)


def _rebind_condition_events(fixture, events):
    payload = b''.join(memory.canonical_bytes(event) + b'\n'
                       for event in events)
    fixture['condition_bundle']['legacy-events.jsonl'] = payload
    manifest = artifacts._json(fixture['condition_bundle']['manifest.json'])
    manifest['legacy_events'] = _descriptor('legacy-events.jsonl', payload)
    fixture['condition_bundle']['manifest.json'] = memory.canonical_bytes(manifest)

    receipt = copy.deepcopy(fixture['condition_raw'])
    inventory = receipt['raw_inventory']
    row = next(value for value in inventory['files']
               if value['path'] == 'recording/events.jsonl')
    old_size = row['size_bytes']
    row.update(size_bytes=len(payload), sha256=hashlib.sha256(payload).hexdigest())
    inventory['recording_bytes'] += len(payload) - old_size
    inventory['total_bytes'] += len(payload) - old_size
    inventory['tree_sha256'] = memory.sha256(inventory['files'])
    receipt['oracle_result']['events_sha256'] = memory.sha256(events)
    _rebind_file(fixture, 'receipts/condition.raw-audit.json', receipt)
    fixture['condition_conversion']['compact_manifest'] = _descriptor(
        'manifest.json', fixture['condition_bundle']['manifest.json'])
    fixture['condition_conversion_descriptor'] = _write(
        fixture['root'], 'receipts/condition.conversion.json',
        fixture['condition_conversion'])


def test_protocol_promotes_pair_admission_and_freezes_nested_shapes():
    admission = _admission()
    protocol = artifacts._json(PROTOCOL_PATH.read_bytes())
    pair = next(row for row in protocol['behavior_sources']
                if row['id'] == 'pair_admission')
    payload = (ROOT / pair['path']).read_bytes()
    assert pair == {
        'id': 'pair_admission',
        'path': 'scripts/memory_family_oracle_admission_v4.py',
        'size_bytes': len(payload),
        'sha256': hashlib.sha256(payload).hexdigest(),
    }
    assert protocol['future_behavior_sources'] == [
        {'id': 'producer', 'path': 'scripts/memory_family_producer_v4.py'}]
    nested = protocol['pair_admission']['nested_schemas']
    assert nested == {
        'descriptor': {'exact_keys': ['path', 'size_bytes', 'sha256']},
        'receipt_identity': {'exact_keys': ['conversion', 'raw_audit']},
        'history_identity': {
            'exact_keys': ['role', 'history_sha256', 'bundle_sha256']},
        'resource_identity': {'exact_keys': ['kind', 'sha256']},
        'selector_identity': {
            'exact_keys': ['sha256', 'provenance_sha256']},
        'u_identity': {'exact_keys': ['kind', 'sha256']},
        'oracle_result': {'exact_keys': [
            'status', 'proof_sha256', 'source_events_sha256',
            'source_rows_sha256', 'condition_events_sha256',
            'condition_rows_sha256', 'condition_world_state_sha256',
            'schedule_sha256', 'source_application_sha256',
            'recorded_selection_sha256', 'gold_target_ids',
            'gold_target_ids_sha256', 'prior_own_receipt',
        ]},
    }
    assert protocol['pair_admission']['post_prune_inventory_authority'] == {
        'statement': (
            'The canonical immutable raw-audit receipt is the independently '
            'published pre-prune attestation. After raw pruning, pair admission '
            'revalidates its descriptor, inventory tree/totals/limits and every '
            'retained cross-binding. A field whose bytes are not retained is '
            'receipt-authoritative only; it is not a post-prune byte rehash or '
            'replay claim.'),
        'retained_cross_bindings': {
            'manifest': {
                'raw_path': 'recording/manifest.json',
                'compact_path': 'legacy-manifest.json',
                'identity': ['size_bytes', 'sha256'],
            },
            'events': {
                'raw_path': 'recording/events.jsonl',
                'compact_path': 'legacy-events.jsonl',
                'identity': ['size_bytes', 'sha256'],
            },
            'chunks': {
                'raw_path': 'recording/{legacy_path}',
                'compact_path': 'chunk-index.chunks[].legacy_path',
                'identity': ['path', 'sha256'],
            },
            'source_snapshot': {
                'raw_path': 'snapshots/initial.snp',
                'compact_path': 'snapshot_reference',
                'identity': ['size_bytes', 'sha256'],
            },
        },
        'receipt_only': {
            'legacy_chunk_size_bytes': {
                'path': 'recording/{legacy_path}',
                'meaning': 'pre-prune-auditor-attestation-not-post-prune-byte-replay',
            },
            'worker_report': {
                'path': 'worker-report.json',
                'identity': ['path', 'size_bytes', 'sha256'],
                'meaning': 'pre-prune-auditor-attestation-not-post-prune-byte-replay',
            },
        },
    }
    assert admission.PROTOCOL is compact.PROTOCOL


def test_import_is_pure_and_loads_no_native_model_or_v3_pair_entrypoint():
    code = (
        "import json,sys; import scripts.memory_family_oracle_admission_v4 as a; "
        "print(json.dumps({'origin':a.__file__,'forbidden':sorted(set(sys.modules)&"
        "{'torch','mujoco','palimpsest.engine','palimpsest.model'})}))")
    result = subprocess.run(
        [sys.executable, '-c', code], cwd=ROOT,
        env={**os.environ, 'PYTHONPATH': 'src:.', 'PYTHONDONTWRITEBYTECODE': '1'},
        text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    output = artifacts._json(result.stdout.encode())
    assert Path(output['origin']).resolve() == \
        ROOT / 'scripts/memory_family_oracle_admission_v4.py'
    assert output['forbidden'] == []


@pytest.mark.parametrize('condition', CONDITIONS)
def test_admits_all_nine_exact_condition_identity_mappings_read_only(
        tmp_path, monkeypatch, condition):
    admission = _admission()
    prior_own_result = None
    if condition == 'oracle':
        donor = _fixture(tmp_path / 'oracle-donor', 'own')
        prior_own_result = admission.admit_compact_pair(**_request(donor))
    fixture = _fixture(
        tmp_path / condition, condition, prior_own_result=prior_own_result)
    before = _tree_hashes(fixture['root'])
    from scripts import memory_family_oracle_admission_v3 as admission_v3
    monkeypatch.setattr(
        admission_v3, 'admit_oracle_pair',
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError('v4 called the own-only v3 pair entry point')))
    result = admission.admit_compact_pair(**_request(fixture))
    assert set(result) == set(
        compact.PROTOCOL['schemas']['pair_admission']['exact_keys'])
    assert result['schema'] == 'memory-family-compact-pair-admission-v1'
    assert result['condition'] == condition
    for name in ('history_identity', 'resource_identity',
                 'selector_identity', 'u_identity'):
        assert result[name] == fixture['expected'][name]
    assert result['claims'] == compact.PROTOCOL['claims']
    assert not any(result['claims'].values())
    assert result['oracle_result']['status'] == 'compact-pair-pass'
    assert result['oracle_result']['gold_target_ids_sha256'] == \
        fixture['expected']['gold_target_ids_sha256']
    assert _tree_hashes(fixture['root']) == before
    full = compact._legacy_events(
        fixture['condition_bundle']['legacy-events.jsonl'], 'condition')
    non_chunks = compact.read_compact(fixture['condition_bundle'])['events']
    assert len(full) > len(non_chunks)
    assert [event['sequence'] for event in non_chunks] != \
        list(range(len(non_chunks)))


def test_failed_condition_requires_and_accepts_only_exact_natural_failure_receipt(
        tmp_path):
    admission = _admission()
    fixture = _fixture(tmp_path / 'natural', natural_failure=True)
    read = compact.read_compact(
        fixture['condition_bundle'],
        raw_audit_receipt=fixture['condition_raw'])
    events = compact._legacy_events(read['legacy_events_bytes'], 'condition')
    raw_audit._condition_terminal(
        {'events': events,
         'manifest': artifacts._json(read['legacy_manifest_bytes'])},
        fixture['case'], _projection(read['rows']),
        fixture['condition_raw']['terminal_state'], fixture['schedule'])
    result = admission.admit_compact_pair(**_request(fixture))
    assert result['condition'] == 'own'
    assert fixture['condition_raw']['terminal_state']['natural_failure'] is True

    changed = copy.deepcopy(fixture['condition_raw'])
    changed['terminal_state']['natural_failure'] = False
    _rebind_file(
        fixture, 'receipts/condition.raw-audit.json', changed)
    with pytest.raises(ValueError):
        admission.admit_compact_pair(**_request(fixture))


def test_compact_reader_never_accepts_a_failed_source_and_requires_the_receipt(
        tmp_path):
    natural = _fixture(tmp_path / 'condition', natural_failure=True)
    with pytest.raises(ValueError):
        compact.read_compact(natural['condition_bundle'])
    assert compact.read_compact(
        natural['condition_bundle'],
        raw_audit_receipt=natural['condition_raw'])['manifest']['operation'] \
        == 'condition'

    source = _fixture(tmp_path / 'source')
    receipt = copy.deepcopy(source['source_raw'])
    receipt['terminal_state'].update(
        manifest_status='failed', final_phase='failed', natural_failure=True)
    bundle = dict(source['source_bundle'])
    legacy = artifacts._json(bundle['legacy-manifest.json'])
    legacy['status'] = 'failed'
    bundle['legacy-manifest.json'] = memory.canonical_bytes(legacy) + b'\n'
    manifest = artifacts._json(bundle['manifest.json'])
    manifest['legacy_manifest'] = _descriptor(
        'legacy-manifest.json', bundle['legacy-manifest.json'])
    bundle['manifest.json'] = memory.canonical_bytes(manifest)
    with pytest.raises(ValueError, match='Source legacy manifest'):
        compact.read_compact(bundle, raw_audit_receipt=receipt)


@pytest.mark.parametrize('defect', [
    'raw-count', 'raw-events-hash', 'conversion-manifest',
    'source-identity', 'snapshot-source-receipt', 'history', 'selection',
    'policy-result', 'chunk-sequence',
])
def test_rejects_receipt_compact_identity_and_selector_cross_binding(
        tmp_path, defect):
    admission = _admission()
    fixture = _fixture(tmp_path / defect)
    if defect == 'raw-count':
        changed = copy.deepcopy(fixture['condition_raw'])
        changed['row_count'] += 1
        _rebind_file(fixture, 'receipts/condition.raw-audit.json', changed)
    elif defect == 'raw-events-hash':
        changed = copy.deepcopy(fixture['condition_raw'])
        changed['oracle_result']['events_sha256'] = '0' * 64
        _rebind_file(fixture, 'receipts/condition.raw-audit.json', changed)
    elif defect == 'conversion-manifest':
        fixture['condition_conversion']['compact_manifest']['sha256'] = '0' * 64
        fixture['condition_conversion_descriptor'] = _write(
            fixture['root'], 'receipts/condition.conversion.json',
            fixture['condition_conversion'])
    elif defect == 'source-identity':
        changed = copy.deepcopy(fixture['condition_raw'])
        changed['source_identity']['owner_source_sha256'] = '0' * 64
        _rebind_file(fixture, 'receipts/condition.raw-audit.json', changed)
    elif defect == 'snapshot-source-receipt':
        manifest = artifacts._json(fixture['condition_bundle']['manifest.json'])
        manifest['snapshot_reference']['source_receipt_sha256'] = '0' * 64
        fixture['condition_bundle']['manifest.json'] = memory.canonical_bytes(manifest)
        fixture['condition_conversion']['compact_manifest'] = _descriptor(
            'manifest.json', fixture['condition_bundle']['manifest.json'])
        fixture['condition_conversion_descriptor'] = _write(
            fixture['root'], 'receipts/condition.conversion.json',
            fixture['condition_conversion'])
    elif defect == 'history':
        fixture['history_bundles']['own']['sha256'] = '0' * 64
    elif defect == 'selection':
        payload = fixture['condition_bundle']['legacy-events.jsonl']
        events = [artifacts._json(line) for line in payload.splitlines()]
        selected = next(event for event in events
                        if event.get('detail', {}).get('kind') == 'memory_selection')
        selected['detail']['selection']['target_ids'] = []
        _rebind_condition_events(fixture, events)
    elif defect == 'policy-result':
        changed = copy.deepcopy(fixture['condition_raw'])
        changed['policy_result']['bindings_sha256'] = '0' * 64
        _rebind_file(fixture, 'receipts/condition.raw-audit.json', changed)
    else:
        events = compact._legacy_events(
            fixture['condition_bundle']['legacy-events.jsonl'], 'condition')
        next(event for event in events if event['kind'] == 'chunk')[
            'sequence'] += 1
        _rebind_condition_events(fixture, events)
    with pytest.raises((OSError, RuntimeError, ValueError)):
        admission.admit_compact_pair(**_request(fixture))


@pytest.mark.parametrize('defect', [
    'snapshot-mutation', 'snapshot-symlink', 'snapshot-hardlink',
    'receipt-symlink', 'receipt-missing',
])
def test_rejects_snapshot_or_receipt_mutation_alias_and_path_following(
        tmp_path, defect):
    admission = _admission()
    fixture = _fixture(tmp_path / defect)
    if defect == 'snapshot-mutation':
        fixture['snapshot_path'].write_bytes(
            fixture['snapshot_path'].read_bytes() + b'changed')
    elif defect == 'snapshot-symlink':
        target = fixture['root'] / 'snapshot-target.snp'
        target.write_bytes(fixture['snapshot_path'].read_bytes())
        fixture['snapshot_path'].unlink()
        fixture['snapshot_path'].symlink_to(target)
    elif defect == 'snapshot-hardlink':
        os.link(fixture['snapshot_path'], fixture['root'] / 'snapshot-alias.snp')
    elif defect == 'receipt-symlink':
        path = fixture['root'] / fixture['condition_conversion_descriptor']['path']
        target = fixture['root'] / 'conversion-target.json'
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    else:
        (fixture['root'] / fixture['source_conversion_descriptor']['path']).unlink()
    with pytest.raises((OSError, RuntimeError, ValueError)):
        admission.admit_compact_pair(**_request(fixture))


def test_rejects_condition_snapshot_bound_to_another_source_run(tmp_path):
    admission = _admission()
    fixture = _fixture(tmp_path / 'wrong-source-run')
    manifest = artifacts._json(fixture['condition_bundle']['manifest.json'])
    manifest['snapshot_reference']['source_run_id'] = uuid.uuid4().hex
    fixture['condition_bundle']['manifest.json'] = memory.canonical_bytes(manifest)
    fixture['condition_conversion']['compact_manifest'] = _descriptor(
        'manifest.json', fixture['condition_bundle']['manifest.json'])
    fixture['condition_conversion_descriptor'] = _write(
        fixture['root'], 'receipts/condition.conversion.json',
        fixture['condition_conversion'])
    with pytest.raises(ValueError):
        admission.admit_compact_pair(**_request(fixture))


@pytest.mark.parametrize('defect', [
    'final-phase', 'total-ticks', 'last-tick', 'world-state-shape',
    'world-state-value',
])
def test_rejects_rebound_terminal_semantic_forgery(tmp_path, defect):
    admission = _admission()
    fixture = _fixture(tmp_path / defect)
    receipt = copy.deepcopy(fixture['condition_raw'])
    terminal = receipt['terminal_state']
    if defect == 'final-phase':
        terminal['final_phase'] = 'failed'
    elif defect == 'total-ticks':
        terminal['total_ticks'] += 100
    elif defect == 'last-tick':
        terminal['last_tick'] += 1
    elif defect == 'world-state-shape':
        terminal['world_state_sha256'] = {'forged': True}
    else:
        terminal['world_state_sha256'] = '0' * 64
    _rebind_file(fixture, 'receipts/condition.raw-audit.json', receipt)
    with pytest.raises(ValueError):
        admission.admit_compact_pair(**_request(fixture))


@pytest.mark.parametrize('defect', [
    'restored-revision', 'restored-eyes', 'commitment',
])
def test_rejects_rebound_restore_or_commitment_semantic_forgery(
        tmp_path, defect):
    admission = _admission()
    fixture = _fixture(tmp_path / defect)
    events = compact._legacy_events(
        fixture['condition_bundle']['legacy-events.jsonl'], 'condition')
    if defect in ('restored-revision', 'restored-eyes'):
        restored = next(event for event in events
                        if event['kind'] == 'application_restored')
        if defect == 'restored-revision':
            restored['revision'] += 1
        else:
            restored['eyes']['left'] = False
    else:
        commitment = next(
            event['detail'] for event in events
            if event.get('detail', {}).get('kind') == 'memory_commitment')
        commitment['route_id'] = 'forged-route'
    _rebind_condition_events(fixture, events)
    with pytest.raises(ValueError):
        admission.admit_compact_pair(**_request(fixture))


def test_oracle_requires_prior_own_receipt_and_non_oracle_rejects_one(tmp_path):
    admission = _admission()
    donor = _fixture(tmp_path / 'donor')
    prior = admission.admit_compact_pair(**_request(donor))
    oracle_fixture = _fixture(
        tmp_path / 'oracle', 'oracle', prior_own_result=prior)
    request = _request(oracle_fixture)
    request.pop('prior_own_receipt')
    with pytest.raises(ValueError, match='prior-own receipt'):
        admission.admit_compact_pair(**request)

    own = _fixture(tmp_path / 'own')
    request = _request(own)
    request['prior_own_receipt'] = _write(
        own['root'], 'receipts/unexpected-prior-own.json', prior)
    with pytest.raises(ValueError, match='Only the oracle'):
        admission.admit_compact_pair(**request)


@pytest.mark.parametrize('defect', [
    'mutation', 'symlink', 'hardlink', 'condition', 'claims', 'proof', 'gold',
])
def test_rejects_prior_own_receipt_alias_mutation_or_wrong_identity(
        tmp_path, defect):
    admission = _admission()
    donor = _fixture(tmp_path / f'{defect}-donor')
    prior = admission.admit_compact_pair(**_request(donor))
    fixture = _fixture(
        tmp_path / f'{defect}-oracle', 'oracle', prior_own_result=prior)
    path = fixture['root'] / fixture['prior_own_receipt']['path']
    if defect == 'mutation':
        path.write_bytes(path.read_bytes() + b'changed')
    elif defect == 'symlink':
        target = fixture['root'] / 'prior-own-target.json'
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    elif defect == 'hardlink':
        os.link(path, fixture['root'] / 'prior-own-alias.json')
    else:
        changed = copy.deepcopy(prior)
        if defect == 'condition':
            changed['condition'] = 'swapped'
        elif defect == 'claims':
            changed['claims']['compact_oracle_equivalent'] = True
        elif defect == 'proof':
            changed['oracle_result']['proof_sha256'] = '0' * 64
        else:
            changed['oracle_result']['gold_target_ids'] = []
            changed['oracle_result']['gold_target_ids_sha256'] = memory.sha256([])
        fixture['prior_own_receipt'] = _write(
            fixture['root'], 'receipts/prior-own.pair.json', changed)
    with pytest.raises((OSError, RuntimeError, ValueError)):
        admission.admit_compact_pair(**_request(fixture))


@pytest.mark.parametrize('defect', [
    'zero-worker-report', 'oversize-worker-report', 'zero-chunk',
    'oversize-recording',
])
def test_rejects_rebound_raw_inventory_outside_frozen_authority_limits(
        tmp_path, defect):
    admission = _admission()
    fixture = _fixture(tmp_path / defect)
    receipt = copy.deepcopy(fixture['condition_raw'])
    inventory = receipt['raw_inventory']
    if 'worker-report' in defect:
        row = next(value for value in inventory['files']
                   if value['path'] == 'worker-report.json')
        row['size_bytes'] = (0 if defect == 'zero-worker-report'
                             else raw_audit.RAW_LIMITS['condition'][
                                 'report_max_bytes'] + 1)
    else:
        row = next(value for value in inventory['files']
                   if value['path'].startswith('recording/chunks/'))
        row['size_bytes'] = (0 if defect == 'zero-chunk'
                             else raw_audit.RAW_LIMITS['condition'][
                                 'recording_max_bytes'] + 1)
    inventory['recording_bytes'] = sum(
        value['size_bytes'] for value in inventory['files']
        if value['path'].startswith('recording/'))
    inventory['support_bytes'] = sum(
        value['size_bytes'] for value in inventory['files']
        if not value['path'].startswith('recording/'))
    inventory['total_bytes'] = (
        inventory['recording_bytes'] + inventory['support_bytes'])
    inventory['tree_sha256'] = memory.sha256(inventory['files'])
    _rebind_file(fixture, 'receipts/condition.raw-audit.json', receipt)
    with pytest.raises(ValueError):
        admission.admit_compact_pair(**_request(fixture))


@pytest.mark.parametrize('defect', ['parent-rebind', 'late-receipt-write'])
def test_admission_keeps_all_input_bindings_until_return(tmp_path, monkeypatch, defect):
    admission = _admission()
    fixture = _fixture(tmp_path / defect)
    if defect == 'parent-rebind':
        original = artifacts._json
        swapped = (fixture['root'] / fixture['history_bundles']['swapped']['path']).read_bytes()
        def changed(payload):
            value = original(payload)
            if payload == swapped:
                directory = fixture['root'] / 'histories'
                directory.rename(fixture['root'] / 'renamed-histories')
                directory.write_bytes(b'{}')
            return value
        monkeypatch.setattr(artifacts, '_json', changed)
    else:
        original = admission._history
        def changed(*args, **kwargs):
            result = original(*args, **kwargs)
            (fixture['root'] / fixture['source_conversion_descriptor']['path']).write_bytes(b'{}')
            return result
        monkeypatch.setattr(admission, '_history', changed)
    with pytest.raises((OSError, RuntimeError, ValueError)):
        admission.admit_compact_pair(**_request(fixture))


@pytest.mark.parametrize('defect', ['source-conversion', 'source-raw', 'u-digest',
                                  'selector-digest', 'history', 'selector-provenance',
                                  'snapshot-size', 'claims-alias'])
def test_prior_own_nested_values_bind_current_source_and_own_mapping(tmp_path, defect):
    admission = _admission()
    donor = _fixture(tmp_path / 'donor')
    prior = admission.admit_compact_pair(**_request(donor))
    fixture = _fixture(tmp_path / 'oracle', 'oracle', prior_own_result=prior)
    changed = copy.deepcopy(prior)
    if defect.startswith('source-'):
        name = 'conversion' if defect == 'source-conversion' else 'raw_audit'
        changed['source_receipt'][name] = {'path': 'missing.json', 'size_bytes': 1, 'sha256': '0' * 64}
    elif defect == 'u-digest':
        changed['u_identity']['sha256'] = 'invalid'
    elif defect == 'selector-digest':
        changed['selector_identity']['sha256'] = 'invalid'
    elif defect == 'history':
        changed['history_identity']['bundle_sha256'] = '0' * 64
    elif defect == 'selector-provenance':
        changed['selector_identity']['provenance_sha256'] = '0' * 64
    elif defect == 'snapshot-size':
        changed['snapshot_reference']['size_bytes'] = float(changed['snapshot_reference']['size_bytes'])
    else:
        changed['claims']['compact_oracle_equivalent'] = 0
    fixture['prior_own_receipt'] = _write(fixture['root'], 'receipts/prior-own.pair.json', changed)
    with pytest.raises(ValueError):
        admission.admit_compact_pair(**_request(fixture))


@pytest.mark.parametrize('group,field', [
    (None, 'row_count'), (None, 'chunk_count'), (None, 'event_count'),
    ('raw_inventory', 'file_count'), ('raw_inventory', 'recording_bytes'),
    ('raw_inventory', 'support_bytes'), ('raw_inventory', 'total_bytes'),
    ('terminal_state', 'total_ticks'), ('terminal_state', 'last_tick'),
    ('policy_result', 'call_count'),
])
@pytest.mark.parametrize('alias', ['float', 'bool'])
def test_raw_receipt_integer_fields_reject_numeric_aliases(tmp_path, group, field, alias):
    admission = _admission()
    fixture = _fixture(tmp_path / f'{group}-{field}-{alias}')
    receipt = copy.deepcopy(fixture['condition_raw'])
    target = receipt if group is None else receipt[group]
    target[field] = float(target[field]) if alias == 'float' else bool(target[field])
    _rebind_file(fixture, 'receipts/condition.raw-audit.json', receipt)
    with pytest.raises(ValueError):
        admission.admit_compact_pair(**_request(fixture))
