"""Synthetic raw-auditor checks; never open retained data or run an owner."""
import copy
import hashlib
import importlib
import io
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid

import numpy as np
import pytest

from palimpsest import artifacts, memory, snapshots
from palimpsest.records import RunWriter
from scripts import memory_family_oracle_admission_v3 as admission
from test_memory_family_oracle_v3 import evidence


ROOT = Path(__file__).parents[1]
PROTOCOL_PATH = ROOT / 'docs/plans/memory-family-compact-evidence-v4-protocol.json'
CASE_ID = 'memory-family-v3-a54cb2f83098a2346a9cc46e-change'
SOURCE_IDENTITY_SHA256 = memory.sha256({
    'schema': 'synthetic-owner-source-identity-v1',
    'identity': 'raw-audit-fixture',
})


def _audit():
    try:
        return importlib.import_module('scripts.memory_family_raw_audit_v4')
    except ModuleNotFoundError:
        pytest.fail('memory_family_raw_audit_v4 is not implemented', pytrace=False)


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _tree_hashes(root):
    return {
        path.relative_to(root).as_posix(): _sha(path)
        for path in sorted(Path(root).rglob('*')) if path.is_file()
    }


def _emit(writer, event):
    value = copy.deepcopy(event)
    kind = value.pop('kind')
    value.pop('sequence')
    writer.event(kind, **value)


def _policy_row(row, run_id, pixel_shift=0):
    tick = row['tick']
    left = np.full((128, 128, 3), (tick + pixel_shift) % 251, np.uint8)
    right = np.full((128, 128, 3), (tick + pixel_shift + 1) % 251, np.uint8)
    sensors = {'collision': False, 'collision_angle': None,
               'wind_direction': [1.0, 0.0]}
    arrays = {
        'cam_left': left, 'cam_right': right,
        'raw_cam_left': left.copy(), 'raw_cam_right': right.copy(),
        'sensors': np.array([0.0, 0.0, 1.0, 0.0], np.float32),
        'action': np.array([0.2, 0.0], np.float32),
        'control': np.array([0.19, 0.0], np.float64),
        'encoded_input': np.full(4813, tick / 1000, np.float32),
        'raw_output': np.array([0.2, 0.0], np.float32),
        'pose': np.asarray(row['pose'], np.float64),
        'next_pose': np.asarray(row['next_pose'], np.float64),
        'reward': np.array(0.0, np.float64),
        'simulation_time': np.array((tick + 1) * .02, np.float64),
        'eyes': np.array([True, True], np.bool_),
        'revision': np.array(3, np.int64),
        'latency': np.array(.001, np.float64),
        'step_latency': np.array(.002, np.float64),
        'population_stats': np.array([[2.0, .5, 0.0, 1.0]], np.float64),
    }
    observation = {'cam_left': left, 'cam_right': right, 'sensors': sensors}
    event = {
        'run_id': run_id, 'episode': 0, 'episode_step': tick, 'tick': tick,
        'observation_sha256': snapshots.state_digest(observation),
        'cameras_sha256': {
            key: snapshots.state_digest(arrays[key])
            for key in ('cam_left', 'cam_right')
        },
        'sensors': sensors,
        'result_sha256': {
            key: snapshots.state_digest(arrays[key])
            for key in ('action', 'encoded_input', 'raw_output')
        },
    }
    return event, arrays


def _emit_trace(writer, events, rows, pixel_shift=0):
    by_tick = {row['tick']: row for row in rows}
    for index, event in enumerate(events):
        _emit(writer, event)
        tick = event.get('episode_step')
        next_tick = (events[index + 1].get('episode_step')
                     if index + 1 < len(events) else None)
        if tick in by_tick and tick != next_tick:
            policy, arrays = _policy_row(by_tick[tick], writer.manifest['run_id'],
                                         pixel_shift)
            writer.event(
                'memory_cue', run_id=writer.manifest['run_id'], episode=0,
                episode_step=tick, tick=tick, bearing=[1.0, 0.0])
            writer.event('neural_policy_call', **policy)
            writer.tick(0, tick, **arrays)


def _prefix(writer):
    payload = (writer.path / 'events.jsonl').read_bytes()
    return {'sha256': hashlib.sha256(payload).hexdigest(),
            'size_bytes': len(payload), 'event_count': payload.count(b'\n')}


def _register_source_snapshot(writer, application):
    directory = writer.path.parent / 'snapshots'
    directory.mkdir()
    path = directory / 'initial.snp'
    snapshots.save_snapshot({'application': application}, path)
    digest = _sha(path)
    writer.event(
        'snapshot_registered', run_id=writer.manifest['run_id'],
        snapshot_id=uuid.uuid4().hex, filename='initial.snp', initial=True,
        sha256=digest)
    return digest


def _manifest(audit, case, run_id, operation, condition, source_snapshot_sha256,
              *, parent_run_id=None, parent_event_prefix=None):
    maximum = (admission.SOURCE_RECORDING_MAX_BYTES if operation == 'source'
               else admission.POST_RECORDING_MAX_BYTES)
    envelope = {
        'schema': admission.ENVELOPE_SCHEMA,
        'protocol_sha256': audit.PROTOCOL_SHA256,
        'source_identity_sha256': SOURCE_IDENTITY_SHA256,
        'case': case, 'operation': operation, 'condition': condition,
        'source_snapshot_sha256': source_snapshot_sha256,
    }
    return {
        'run_id': run_id, 'controller': 'flynn', 'requested_device': 'cpu',
        'teacher_privileged': False,
        'scenario': admission.validate_decision(
            'memory-decision-v2', 'checker', 'flynn',
            profile_sha256=case['profile_sha256']),
        'texture': 'checker', 'seed': case['seed'], 'memory_case': case,
        'memory_case_sha256': memory.sha256(case),
        'acquisition_protocol_sha256': case['acquisition_protocol_sha256'],
        'parent_run_id': parent_run_id,
        'parent_event_prefix': parent_event_prefix,
        'recording_max_bytes': maximum,
        'memory_family_oracle_admission_v3': envelope,
    }


def _finish(writer, total_ticks, world_state, final_phase='paused'):
    writer.finish({
        'run_id': writer.manifest['run_id'],
        'parent_run_id': writer.manifest.get('parent_run_id'),
        'parent_event_prefix': writer.manifest.get('parent_event_prefix'),
        'final_phase': final_phase, 'last_outcome': None,
        'metrics': {'reward': 0.0, 'contact_ticks': 0, 'path_length': 0.0},
        'total_tick': total_ticks, 'close_reason': 'operator_closed',
        'world_state': world_state,
    }, status='failed' if final_phase == 'failed' else 'completed')


def _report(path, *, run_id, case, operation, condition, snapshot_sha256,
            source_snapshot_sha256, total_ticks, world_state,
            final_phase='paused'):
    value = {
        'schema': admission.REPORT_SCHEMA, 'run_id': run_id,
        'case_id': case['case_id'], 'operation': operation,
        'condition': condition, 'status': 'recorded', 'acquired': True,
        'snapshot_sha256': snapshot_sha256,
        'source_snapshot_sha256': source_snapshot_sha256,
        'total_ticks': total_ticks, 'final_phase': final_phase,
        'world_state': world_state,
    }
    Path(path).write_bytes(memory.canonical_bytes(value))


def _fixture(root, pixel_shift=0, *, natural_failure=False):
    audit = _audit()
    root.mkdir(parents=True)
    sample = evidence(row=4)
    case = sample['case']
    assert case['case_id'] == CASE_ID
    source_id = sample['bindings']['source']['run_id']
    condition_id = sample['bindings']['post']['run_id']

    source_run = root / source_id
    source_writer = RunWriter(
        source_run / 'recording',
        _manifest(audit, case, source_id, 'source', None, None),
        max_bytes=admission.SOURCE_RECORDING_MAX_BYTES)
    _emit_trace(source_writer, sample['source_events'], sample['source_rows'],
                pixel_shift)
    source_application = copy.deepcopy(sample['source_application'])
    source_application['event_prefix'] = _prefix(source_writer)
    source_snapshot_sha256 = _register_source_snapshot(
        source_writer, source_application)
    _finish(source_writer, source_application['total_tick'],
            source_application['world_task_state'])
    _report(
        source_run / 'worker-report.json', run_id=source_id, case=case,
        operation='source', condition=None,
        snapshot_sha256=source_snapshot_sha256,
        source_snapshot_sha256=None,
        total_ticks=source_application['total_tick'],
        world_state=source_application['world_task_state'])

    post_events = copy.deepcopy(sample['post_events'])
    restored = next(event for event in post_events
                    if event['kind'] == 'application_restored')
    restored['parent_event_prefix'] = copy.deepcopy(
        source_application['event_prefix'])
    post_world = copy.deepcopy(sample['post_world_state'])
    final_phase = 'paused'
    if natural_failure:
        failure_tick = post_world['last_tick'] + 1
        post_events.append({
            'sequence': len(post_events), 'kind': 'runtime_failure',
            'run_id': condition_id, 'episode': 0,
            'episode_step': failure_tick, 'tick': failure_tick,
            'error': {
                'reason': 'runtime_failure', 'episode': 0,
                'steps': failure_tick, 'type': 'CueUnavailable',
                'message': 'synthetic retained natural task failure',
                'policy_diagnostics': None,
            },
        })
        post_world['last_tick'] = failure_tick
        final_phase = 'failed'
    condition_run = root / condition_id
    condition_writer = RunWriter(
        condition_run / 'recording',
        _manifest(
            audit, case, condition_id, 'condition', 'own',
            source_snapshot_sha256, parent_run_id=source_id,
            parent_event_prefix=source_application['event_prefix']),
        max_bytes=admission.POST_RECORDING_MAX_BYTES)
    _emit_trace(condition_writer, post_events, sample['post_rows'], pixel_shift)
    total_ticks = sample['post_world_state']['last_tick'] + 1
    _finish(condition_writer, total_ticks, post_world, final_phase)
    _report(
        condition_run / 'worker-report.json', run_id=condition_id, case=case,
        operation='condition', condition='own',
        snapshot_sha256=source_snapshot_sha256,
        source_snapshot_sha256=source_snapshot_sha256,
        total_ticks=total_ticks, world_state=post_world,
        final_phase=final_phase)

    receipts = root / 'raw-audits'
    receipts.mkdir()
    return {
        'case': case, 'source_snapshot_sha256': source_snapshot_sha256,
        'source': {'run_id': source_id, 'run_path': source_run,
                   'operation': 'source', 'condition': None,
                   'source_run_id': None, 'source_snapshot_sha256': None},
        'condition': {'run_id': condition_id, 'run_path': condition_run,
                      'operation': 'condition', 'condition': 'own',
                      'source_run_id': source_id,
                      'source_snapshot_sha256': source_snapshot_sha256},
        'receipts': receipts,
    }


def _request(fixture, part, *, target=None):
    value = fixture[part]
    return {
        'run_path': value['run_path'],
        'receipt_root': target or fixture['receipts'],
        'run_id': value['run_id'], 'case_id': fixture['case']['case_id'],
        'operation': value['operation'], 'condition': value['condition'],
        'source_run_id': value['source_run_id'],
        'source_snapshot_sha256': value['source_snapshot_sha256'],
        'source_identity_sha256': SOURCE_IDENTITY_SHA256,
        'deadline': time.monotonic() + 30,
    }


def _receipt_path(request):
    return (Path(request['receipt_root']) /
            f"{request['run_id']}.raw-audit.json")


def _rewrite_events(run, edit):
    path = Path(run) / 'recording/events.jsonl'
    events = [artifacts._json(line) for line in path.read_bytes().splitlines()]
    edit(events)
    for sequence, event in enumerate(events):
        event['sequence'] = sequence
    path.write_bytes(b''.join(memory.canonical_bytes(event) + b'\n'
                              for event in events))
    manifest_path = Path(run) / 'recording/manifest.json'
    manifest = artifacts._json(manifest_path.read_bytes())
    manifest['recorded_events'] = len(events)
    manifest_path.write_text(
        memory.canonical_bytes(manifest).decode() + '\n')


def _rewrite_first_chunk(run, edit):
    run = Path(run)
    events_path = run / 'recording/events.jsonl'
    events = [artifacts._json(line) for line in events_path.read_bytes().splitlines()]
    event = next(value for value in events if value['kind'] == 'chunk')
    path = run / 'recording' / event['path']
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    edit(arrays)
    with io.BytesIO() as stream:
        np.savez(stream, **arrays)
        payload = stream.getvalue()
    path.write_bytes(payload)
    event['sha256'] = hashlib.sha256(payload).hexdigest()
    event['arrays'] = {
        name: {'dtype': value.dtype.str, 'shape': list(value.shape[1:])}
        for name, value in arrays.items()
    }
    events_path.write_bytes(b''.join(memory.canonical_bytes(value) + b'\n'
                                     for value in events))


def test_protocol_binds_raw_auditor_and_import_is_pure():
    audit = _audit()
    protocol = artifacts._json(PROTOCOL_PATH.read_bytes())
    entry = next(row for row in protocol['behavior_sources']
                 if row['id'] == 'raw_audit')
    payload = (ROOT / entry['path']).read_bytes()
    assert entry == {
        'id': 'raw_audit', 'path': 'scripts/memory_family_raw_audit_v4.py',
        'size_bytes': len(payload),
        'sha256': hashlib.sha256(payload).hexdigest(),
    }
    assert 'raw_audit' not in {
        row['id'] for row in protocol['future_behavior_sources']}
    assert audit.RAW_LIMITS == protocol['raw_audit']['limits']
    assert protocol['raw_audit']['receipt_max_bytes'] == 1024**2
    assert set(protocol['raw_audit']['nested_schemas']) == {
        'file', 'raw_inventory', 'source_identity', 'terminal_state',
        'policy_result', 'oracle_result',
    }
    assert audit.canonical_source_identity()['behavior_sources'] == \
        protocol['behavior_sources']

    code = (
        "import json,sys; import scripts.memory_family_raw_audit_v4 as a; "
        "print(json.dumps({'origin':a.__file__,'forbidden':sorted(set(sys.modules)&"
        "{'torch','mujoco','palimpsest.engine','palimpsest.model'})}))"
    )
    result = subprocess.run(
        [sys.executable, '-c', code], cwd=ROOT,
        env={**os.environ, 'PYTHONPATH': 'src:.', 'PYTHONDONTWRITEBYTECODE': '1'},
        text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    output = artifacts._json(result.stdout.encode())
    assert Path(output['origin']).resolve() == ROOT / entry['path']
    assert output['forbidden'] == []


@pytest.mark.parametrize('part', ['source', 'condition'])
def test_audits_one_closed_run_read_only_and_publishes_exclusively(tmp_path, part):
    audit = _audit()
    fixture = _fixture(tmp_path / part)
    request = _request(fixture, part)
    before = _tree_hashes(fixture[part]['run_path'])
    result = audit.audit_raw_run(**request)
    receipt = artifacts._json(Path(result['path']).read_bytes())

    assert receipt['schema'] == 'memory-family-raw-audit-v4'
    assert set(receipt) == set(audit.PROTOCOL['schemas']['raw_audit']['exact_keys'])
    assert receipt['operation'] == part
    assert receipt['claims'] == audit.PROTOCOL['claims']
    assert not any(receipt['claims'].values())
    assert receipt['policy_result']['status'] == 'exhaustive-pass'
    assert receipt['oracle_result']['pair_admission'] is False
    assert receipt['row_count'] > 0 and receipt['chunk_count'] == 1
    assert receipt['raw_inventory']['tree_sha256'] == memory.sha256(
        receipt['raw_inventory']['files'])
    assert Path(result['path']).stat().st_size <= \
        audit.PROTOCOL['raw_audit']['receipt_max_bytes']
    assert audit.validate_raw_receipt(**request) == receipt
    assert _tree_hashes(fixture[part]['run_path']) == before
    original = Path(result['path']).read_bytes()
    with pytest.raises(FileExistsError):
        audit.audit_raw_run(**request)
    assert Path(result['path']).read_bytes() == original


def test_retains_a_natural_condition_failure_without_a_replacement(tmp_path):
    audit = _audit()
    fixture = _fixture(tmp_path, natural_failure=True)
    request = _request(fixture, 'condition')
    receipt = audit.audit_raw_run(**request)['receipt']
    assert receipt['terminal_state']['manifest_status'] == 'failed'
    assert receipt['terminal_state']['final_phase'] == 'failed'
    assert receipt['terminal_state']['natural_failure'] is True
    assert receipt['terminal_state']['replacement'] is False


def test_direct_file_cli_publishes_the_same_source_contract(tmp_path):
    fixture = _fixture(tmp_path / 'cli')
    request = _request(fixture, 'source')
    command = [
        sys.executable, str(ROOT / 'scripts/memory_family_raw_audit_v4.py'),
        '--run', str(request['run_path']),
        '--receipt-root', str(request['receipt_root']),
        '--run-id', request['run_id'], '--case-id', request['case_id'],
        '--operation', 'source',
        '--source-identity-sha256', request['source_identity_sha256'],
        '--deadline-seconds', '30',
    ]
    result = subprocess.run(
        command, cwd=ROOT,
        env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
        text=True, capture_output=True, check=False)
    assert result.returncode == 0, result.stderr
    output = artifacts._json(result.stdout.encode())
    assert Path(output['path']) == _receipt_path(request)
    assert _receipt_path(request).is_file()


@pytest.mark.parametrize('field', [
    'run_id', 'case_id', 'condition', 'source_run_id',
    'source_snapshot_sha256', 'source_identity_sha256',
])
def test_rejects_wrong_run_case_condition_or_source_identity(tmp_path, field):
    audit = _audit()
    fixture = _fixture(tmp_path)
    request = _request(fixture, 'condition')
    if field in ('run_id', 'source_run_id'):
        request[field] = uuid.uuid4().hex
    elif field == 'case_id':
        request[field] = 'memory-family-v3-wrong-case'
    elif field == 'condition':
        request[field] = 'swapped'
    else:
        request[field] = 'f' * 64
    with pytest.raises(ValueError):
        audit.audit_raw_run(**request)
    assert not _receipt_path(request).exists()


@pytest.mark.parametrize('defect', [
    'chunk-byte', 'foreign-event', 'eyes-event', 'symlink', 'hardlink-alias',
    'extra-file',
])
def test_rejects_mutated_spliced_or_aliased_raw_tree(tmp_path, defect):
    audit = _audit()
    fixture = _fixture(tmp_path / 'fixture')
    request = _request(fixture, 'condition')
    run = request['run_path']
    if defect == 'chunk-byte':
        chunk = next((run / 'recording/chunks').iterdir())
        chunk.write_bytes(chunk.read_bytes() + b'changed')
    elif defect == 'foreign-event':
        _rewrite_events(run, lambda events: next(
            event for event in events if event['kind'] == 'neural_policy_call')
            .__setitem__('run_id', uuid.uuid4().hex))
    elif defect == 'eyes-event':
        _rewrite_events(run, lambda events: events.append({
            'sequence': len(events), 'kind': 'eyes_changed',
            'run_id': request['run_id'], 'episode': 0,
            'episode_step': 22, 'tick': 22,
        }))
    elif defect == 'symlink':
        alias = tmp_path / request['run_id']
        alias.symlink_to(run, target_is_directory=True)
        request['run_path'] = alias
    elif defect == 'hardlink-alias':
        os.link(next((run / 'recording/chunks').iterdir()), run / 'alias.npz')
    else:
        (run / 'unexpected.txt').write_text('unregistered\n')
    with pytest.raises((OSError, ValueError)):
        audit.audit_raw_run(**request)
    assert not _receipt_path(request).exists()


@pytest.mark.parametrize('defect', [
    'nonfinite', 'missing', 'eyes', 'camera', 'result-hash',
])
def test_rejects_invalid_or_unbound_all_tick_values(tmp_path, defect):
    audit = _audit()
    fixture = _fixture(tmp_path)
    request = _request(fixture, 'condition')
    run = request['run_path']
    if defect == 'nonfinite':
        _rewrite_first_chunk(
            run, lambda arrays: arrays['reward'].__setitem__(0, np.nan))
    elif defect == 'missing':
        _rewrite_first_chunk(run, lambda arrays: arrays.pop('control'))
    elif defect == 'eyes':
        _rewrite_first_chunk(
            run, lambda arrays: arrays['eyes'].__setitem__((0, 0), False))
    elif defect == 'camera':
        _rewrite_first_chunk(
            run, lambda arrays: arrays['raw_cam_left']
            .__setitem__((0, 0, 0, 0), 99))
    else:
        _rewrite_events(run, lambda events: next(
            event for event in events if event['kind'] == 'neural_policy_call')
            ['result_sha256'].__setitem__('action', '0' * 64))
    with pytest.raises(ValueError):
        audit.audit_raw_run(**request)
    assert not _receipt_path(request).exists()


@pytest.mark.parametrize('defect', [
    'running', 'report-ticks', 'world-cursor', 'selector-condition',
])
def test_rejects_terminal_and_condition_oracle_mismatch(tmp_path, defect):
    audit = _audit()
    fixture = _fixture(tmp_path)
    request = _request(fixture, 'condition')
    run = request['run_path']
    if defect in ('running', 'world-cursor'):
        path = run / 'recording/manifest.json'
        manifest = artifacts._json(path.read_bytes())
        if defect == 'running':
            manifest['status'] = 'running'
        else:
            manifest['world_state']['last_tick'] -= 1
        path.write_text(memory.canonical_bytes(manifest).decode() + '\n')
    elif defect == 'report-ticks':
        path = run / 'worker-report.json'
        report = artifacts._json(path.read_bytes())
        report['total_ticks'] -= 1
        path.write_bytes(memory.canonical_bytes(report))
    else:
        _rewrite_events(run, lambda events: next(
            event for event in events
            if event['kind'] == 'memory_selector_configured')['selector']
            .__setitem__('condition', 'swapped'))
    with pytest.raises(ValueError):
        audit.audit_raw_run(**request)
    assert not _receipt_path(request).exists()


def test_rejects_source_restore_lineage_or_snapshot_mutation(tmp_path):
    audit = _audit()
    for defect in ('lineage', 'snapshot'):
        fixture = _fixture(tmp_path / defect)
        request = _request(fixture, 'source')
        run = request['run_path']
        if defect == 'lineage':
            path = run / 'recording/manifest.json'
            manifest = artifacts._json(path.read_bytes())
            manifest['parent_run_id'] = uuid.uuid4().hex
            path.write_text(memory.canonical_bytes(manifest).decode() + '\n')
        else:
            path = run / 'snapshots/initial.snp'
            path.write_bytes(path.read_bytes() + b'mutated')
        with pytest.raises(ValueError):
            audit.audit_raw_run(**request)
        assert not _receipt_path(request).exists()


@pytest.mark.parametrize('operation', ['source', 'condition'])
def test_exact_raw_limits_accept_equality_and_reject_one_over(operation):
    audit = _audit()
    limits = audit.RAW_LIMITS[operation]
    values = {
        'row_count': limits['max_rows'],
        'event_count': limits['max_events'],
        'chunk_count': limits['max_chunks'],
        'event_bytes': limits['events_max_bytes'],
        'recording_bytes': limits['recording_max_bytes'],
        'report_bytes': limits['report_max_bytes'],
        'snapshot_bytes': limits['snapshot_max_bytes'],
        'file_count': limits['max_files'],
    }
    assert audit.validate_raw_limits(operation, **values) is None
    for field in values:
        changed = dict(values)
        changed[field] += 1
        with pytest.raises(ValueError):
            audit.validate_raw_limits(operation, **changed)
    with pytest.raises(ValueError):
        audit.validate_raw_limits(operation, **{**values, 'row_count': True})


def test_rejects_invalid_or_expired_deadlines_before_read(tmp_path):
    audit = _audit()
    fixture = _fixture(tmp_path)
    request = _request(fixture, 'source')
    for deadline in (None, float('nan'), time.monotonic() - 1):
        with pytest.raises((TimeoutError, ValueError)):
            audit.audit_raw_run(**{**request, 'deadline': deadline})
    for seconds in (0, 300.1, float('inf')):
        with pytest.raises(ValueError):
            audit.deadline_from_seconds(seconds)
    assert audit.deadline_from_seconds(300) > time.monotonic()
    assert not _receipt_path(request).exists()


def test_rejects_preexisting_converter_shaped_or_spliced_receipt(tmp_path):
    audit = _audit()
    fixture = _fixture(tmp_path / 'first')
    request = _request(fixture, 'source')
    converter = memory.canonical_bytes({
        'schema': 'memory-family-compact-conversion-v1',
        'claims': copy.deepcopy(audit.PROTOCOL['claims']),
    })
    _receipt_path(request).write_bytes(converter)
    with pytest.raises(FileExistsError):
        audit.audit_raw_run(**request)
    assert _receipt_path(request).read_bytes() == converter

    other = _fixture(tmp_path / 'other', pixel_shift=17)
    first_target = tmp_path / 'first-receipt'
    other_target = tmp_path / 'other-receipt'
    first_target.mkdir()
    other_target.mkdir()
    first_request = _request(fixture, 'source', target=first_target)
    other_request = _request(other, 'source', target=other_target)
    first = audit.audit_raw_run(**first_request)['receipt']
    second = audit.audit_raw_run(**other_request)['receipt']
    spliced = copy.deepcopy(first)
    spliced['raw_inventory'] = second['raw_inventory']
    splice_dir = tmp_path / 'splice'
    splice_dir.mkdir()
    splice_path = splice_dir / f"{fixture['source']['run_id']}.raw-audit.json"
    splice_path.write_bytes(memory.canonical_bytes(spliced))
    with pytest.raises(ValueError):
        audit.validate_raw_receipt(
            **{**first_request, 'receipt_root': splice_dir,
               'deadline': time.monotonic() + 30})


def test_mutation_after_initial_scan_rolls_back_exclusive_link(tmp_path, monkeypatch):
    audit = _audit()
    fixture = _fixture(tmp_path)
    request = _request(fixture, 'condition')
    original = audit._audit_candidate
    calls = 0

    def drift(*args, **kwargs):
        nonlocal calls
        value = original(*args, **kwargs)
        calls += 1
        if calls == 1:
            chunk = next((request['run_path'] / 'recording/chunks').iterdir())
            chunk.write_bytes(chunk.read_bytes() + b'drift')
        return value

    monkeypatch.setattr(audit, '_audit_candidate', drift)
    with pytest.raises((RuntimeError, ValueError)):
        audit.audit_raw_run(**request)
    assert calls == 2
    assert not _receipt_path(request).exists()
