"""Synthetic compact-pair admission checks; no owner or retained data is used."""
import copy
import hashlib
import importlib
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import numpy as np
import pytest

from palimpsest import artifacts, memory, memory_experiment, memory_task, snapshots
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_raw_audit_v4 as raw_audit
from test_memory_family_compact_v4 import _row
from test_memory_family_oracle_v3 import evidence


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


def _legacy(run_id, rows, supplied_events, *, status='completed'):
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
                 schedule, natural_failure=False):
    terminal = {
        'manifest_status': 'failed' if natural_failure else 'completed',
        'final_phase': 'failed' if natural_failure else 'paused',
        'total_ticks': rows[-1]['tick'] + 1,
        'last_tick': rows[-1]['tick'] + (1 if natural_failure else 0),
        'natural_failure': natural_failure, 'replacement': False,
        'world_state_sha256': 'f' * 64,
        'snapshot_sha256': snapshot_descriptor['sha256'],
        'source_run_id': source_run_id,
    }
    projected = _projection(rows)
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
            'call_count': sum(event['kind'] == 'neural_policy_call'
                              for event in events),
            'bindings_sha256': '1' * 64,
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
    for role, relation in (('own', case['regime']), ('swapped', other)):
        history = memory_experiment.make_history(200, relation)
        fitted = memory.fit(history)
        bundle = {'e': history, 'u': fitted,
                  'history_sha256': memory.sha256(history)}
        descriptor = _write(root, f'histories/{role}.json', bundle)
        result[role] = {'bundle': bundle, 'descriptor': descriptor}
    return result


def _condition_values(condition, case, histories, source_application):
    empty = memory.artifact(method='empty-v1')
    gold = ([] if case['kind'] != 'change' else [next(
        fact['id'] for fact in case['facts']
        if fact['subject_id'] == case['closure_subject_id'])])
    oracle_identity = {
        'case_sha256': case['case_sha256'],
        'gold_target_ids_sha256': memory.sha256(gold),
        'source_application_sha256': memory.sha256(source_application),
    }
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
        resource, resource_kind = gold, 'gold-target-ids'
    else:
        resource, resource_kind = None, 'none'
    provenance = (
        histories['swapped']['descriptor']['sha256'] if condition == 'swapped'
        else histories['own']['descriptor']['sha256']
        if condition in ('own', 'sham', 'retrieval')
        else memory.sha256(oracle_identity) if condition == 'oracle'
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
        'oracle_identity': oracle_identity,
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
    trigger = next(event['detail']['trigger'] for event in events
                   if event.get('detail', {}).get('kind') == 'memory_trigger')
    selection = memory_experiment.selection_for_condition(
        condition, source_application['memory']['m'], trigger,
        **memory_task.selector_resources(selector, u), limit=1)
    selected = next(event for event in events
                    if event.get('detail', {}).get('kind') == 'memory_selection')
    selected['detail']['selection'] = selection
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
    if natural_failure:
        tick = max(event.get('tick', 0) for event in events) + 1
        events.append({
            'kind': 'runtime_failure', 'run_id': run_id, 'episode': 0,
            'episode_step': tick, 'tick': tick,
            'error': {'reason': 'runtime_failure', 'episode': 0,
                      'steps': tick, 'type': 'CueUnavailable',
                      'message': 'selected_waypoint_unavailable: synthetic',
                      'policy_diagnostics': {}},
        })
    for sequence, event in enumerate(events):
        event['sequence'] = sequence
        event['run_id'] = run_id
    return events, copy.deepcopy(armed['schedule'])


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


def _fixture(root, condition='own', *, natural_failure=False):
    admission = _admission()
    root.mkdir(parents=True, exist_ok=True)
    sample = evidence(row=4, kind='change')
    case = sample['case']
    source_run_id = sample['bindings']['source']['run_id']
    condition_run_id = uuid.uuid5(uuid.NAMESPACE_URL,
                                  'compact-v4-' + condition).hex
    source_rows = _raw_rows(sample['source_rows'])
    condition_rows = _raw_rows(sample['post_rows'])
    source_manifest, source_event_bytes, source_events = _legacy(
        source_run_id, source_rows, sample['source_events'])
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
        source_application=source_application, schedule=None)
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
        condition, case, histories, source_application)
    condition_events_base, schedule = _condition_events(
        sample, condition, condition_run_id, selector, u,
        source_application, natural_failure=natural_failure)
    status = 'failed' if natural_failure else 'completed'
    condition_manifest, condition_event_bytes, condition_events = _legacy(
        condition_run_id, condition_rows, condition_events_base, status=status)
    condition_raw = _raw_receipt(
        run_id=condition_run_id, case=case, operation='condition',
        condition=condition, rows=condition_rows, events=condition_events,
        legacy_manifest=condition_manifest,
        legacy_events=condition_event_bytes, source_identity=source_identity,
        snapshot_descriptor=snapshot_descriptor, source_run_id=source_run_id,
        source_application=None, schedule=schedule,
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
    }


def _request(fixture):
    return {
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
            'status', 'source_events_sha256', 'source_rows_sha256',
            'condition_events_sha256', 'condition_rows_sha256',
            'schedule_sha256', 'source_application_sha256',
            'recorded_selection_sha256', 'gold_target_ids_sha256',
        ]},
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
    fixture = _fixture(tmp_path / condition, condition)
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
        fixture['expected']['oracle_identity']['gold_target_ids_sha256']
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
    result = admission.admit_compact_pair(**_request(fixture))
    assert result['condition'] == 'own'
    assert fixture['condition_raw']['terminal_state']['natural_failure'] is True

    changed = copy.deepcopy(fixture['condition_raw'])
    changed['terminal_state']['natural_failure'] = False
    _rebind_file(
        fixture, 'receipts/condition.raw-audit.json', changed)
    with pytest.raises(ValueError):
        admission.admit_compact_pair(**_request(fixture))


@pytest.mark.parametrize('defect', [
    'raw-count', 'raw-events-hash', 'conversion-manifest',
    'source-identity', 'snapshot-source-receipt', 'history', 'selection',
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
    else:
        payload = fixture['condition_bundle']['legacy-events.jsonl']
        events = [artifacts._json(line) for line in payload.splitlines()]
        selected = next(event for event in events
                        if event.get('detail', {}).get('kind') == 'memory_selection')
        selected['detail']['selection']['target_ids'] = []
        fixture['condition_bundle']['legacy-events.jsonl'] = b''.join(
            memory.canonical_bytes(event) + b'\n' for event in events)
    with pytest.raises((OSError, RuntimeError, ValueError)):
        admission.admit_compact_pair(**_request(fixture))


@pytest.mark.parametrize('defect', [
    'snapshot-mutation', 'snapshot-symlink', 'snapshot-hardlink',
    'receipt-symlink',
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
    else:
        path = fixture['root'] / fixture['condition_conversion_descriptor']['path']
        target = fixture['root'] / 'conversion-target.json'
        target.write_bytes(path.read_bytes())
        path.unlink()
        path.symlink_to(target)
    with pytest.raises((OSError, RuntimeError, ValueError)):
        admission.admit_compact_pair(**_request(fixture))

