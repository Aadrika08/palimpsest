"""Synthetic raw-pair admission checks; no native runtime or model work."""
import copy
import hashlib
import json
from pathlib import Path
import uuid
from unittest.mock import patch

import numpy as np
import pytest

from palimpsest import memory, memory_experiment, snapshots
from palimpsest.records import RunWriter
from scripts import memory_family_oracle_admission_v3 as admission
from test_memory_family_oracle_v3 import evidence


def _file_sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _canonical_file(path, value):
    Path(path).write_bytes(memory.canonical_bytes(value))
    return _file_sha(path)


def _emit(writer, event):
    event = copy.deepcopy(event)
    kind = event.pop('kind')
    event.pop('sequence')
    writer.event(kind, **event)


def _policy_row(row, run_id):
    tick = row['tick']
    cameras = {
        'cam_left': np.full((1, 1, 3), tick % 251, np.uint8),
        'cam_right': np.full((1, 1, 3), (tick + 1) % 251, np.uint8),
    }
    sensors = {'collision': False, 'collision_angle': None,
               'wind_direction': [1.0, 0.0]}
    arrays = {
        **cameras,
        'sensors': np.array([0.0, 0.0, 1.0, 0.0], np.float32),
        'action': np.array([0.2, 0.0], np.float32),
        'encoded_input': np.full(4813, tick / 1000, np.float32),
        'raw_output': np.array([0.2, 0.0], np.float32),
        'pose': np.asarray(row['pose'], np.float64),
        'next_pose': np.asarray(row['next_pose'], np.float64),
        'reward': np.array(0.0),
        'simulation_time': np.array((tick + 1) * .02),
    }
    observation = {**cameras, 'sensors': sensors}
    event = {
        'run_id': run_id, 'episode': 0, 'episode_step': tick, 'tick': tick,
        'observation_sha256': snapshots.state_digest(observation),
        'cameras_sha256': {key: snapshots.state_digest(value)
                           for key, value in cameras.items()},
        'sensors': sensors,
        'result_sha256': {key: snapshots.state_digest(arrays[key])
                          for key in ('action', 'encoded_input', 'raw_output')},
    }
    return event, arrays


def _emit_trace(writer, events, rows):
    by_tick = {row['tick']: row for row in rows}
    for index, event in enumerate(events):
        _emit(writer, event)
        tick = event.get('episode_step')
        next_tick = events[index + 1].get('episode_step') if index + 1 < len(events) else None
        if tick in by_tick and tick != next_tick:
            policy, arrays = _policy_row(by_tick[tick], writer.manifest['run_id'])
            writer.event('memory_cue', run_id=writer.manifest['run_id'], episode=0,
                         episode_step=tick, tick=tick, bearing=[1.0, 0.0])
            writer.event('neural_policy_call', **policy)
            writer.tick(0, tick, **arrays)


def _prefix(writer):
    payload = (writer.path / 'events.jsonl').read_bytes()
    return {'sha256': hashlib.sha256(payload).hexdigest(),
            'size_bytes': len(payload), 'event_count': payload.count(b'\n')}


def _register_snapshot(writer, application):
    directory = writer.path.parent / 'snapshots'
    directory.mkdir()
    path = directory / 'initial.snp'
    snapshots.save_snapshot({'application': application}, path)
    digest = _file_sha(path)
    writer.event('snapshot_registered', run_id=writer.manifest['run_id'],
                 snapshot_id=uuid.uuid4().hex, filename='initial.snp',
                 initial=True, sha256=digest)
    return digest


def _manifest(case, run_id, envelope, max_bytes, *, parent_run_id=None,
              parent_event_prefix=None):
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
        'recording_max_bytes': max_bytes,
        'memory_family_oracle_admission_v3': envelope,
    }


def _finish(writer, total_ticks, world_state):
    writer.finish({
        'run_id': writer.manifest['run_id'],
        'parent_run_id': writer.manifest.get('parent_run_id'),
        'parent_event_prefix': writer.manifest.get('parent_event_prefix'),
        'final_phase': 'paused', 'last_outcome': None,
        'metrics': {'reward': 0.0, 'contact_ticks': 0, 'path_length': 0.0},
        'total_tick': total_ticks, 'close_reason': 'operator_closed',
        'world_state': world_state,
    })


def _report(path, *, run_id, case, operation, condition, snapshot_sha256,
            source_snapshot_sha256, total_ticks, world_state):
    value = {
        'schema': 'memory-family-owner-report-v3', 'run_id': run_id,
        'case_id': case['case_id'], 'operation': operation,
        'condition': condition, 'status': 'recorded', 'acquired': True,
        'snapshot_sha256': snapshot_sha256,
        'source_snapshot_sha256': source_snapshot_sha256,
        'total_ticks': total_ticks, 'final_phase': 'paused',
        'world_state': world_state,
    }
    _canonical_file(path, value)
    return value


def _tree_hashes(root):
    return {path.relative_to(root).as_posix(): _file_sha(path)
            for path in sorted(root.rglob('*')) if path.is_file()}


def _pair(root, row=4):
    root.mkdir(parents=True, exist_ok=True)
    sample = evidence(row=row)
    case = sample['case']
    protocol_sha256 = '4' * 64
    source_identity_sha256 = '6' * 64
    plan_path = root / 'plan.json'
    plan_sha256 = _canonical_file(plan_path, {'schema': 'fixture-plan-v1'})
    configured = next(event for event in sample['post_events']
                      if event['kind'] == 'memory_selector_configured')
    history = memory.validate_e(memory_experiment.make_history(200, case['regime']))
    bundle = {'version': 1, 'e': history, 'u': memory.fit(history),
              'history_sha256': memory.sha256(history)}
    history_path = root / 'history.json'
    history_sha256 = _canonical_file(history_path, bundle)
    configured['selector']['provenance_sha256'] = history_sha256
    configured['u'] = copy.deepcopy(bundle['u'])

    source_id = sample['bindings']['source']['run_id']
    post_id = sample['bindings']['post']['run_id']
    source_run, post_run = root / source_id, root / post_id
    source_envelope = {
        'schema': 'memory-family-oracle-admission-v3',
        'protocol_sha256': protocol_sha256,
        'source_identity_sha256': source_identity_sha256,
        'case': case, 'operation': 'source', 'condition': None,
        'source_snapshot_sha256': None,
    }
    source_writer = RunWriter(
        source_run / 'recording',
        _manifest(case, source_id, source_envelope,
                  admission.SOURCE_RECORDING_MAX_BYTES),
        max_bytes=admission.SOURCE_RECORDING_MAX_BYTES)
    _emit_trace(source_writer, sample['source_events'], sample['source_rows'])
    source_application = copy.deepcopy(sample['source_application'])
    source_application['event_prefix'] = _prefix(source_writer)
    source_sha256 = _register_snapshot(source_writer, source_application)
    _finish(source_writer, source_application['total_tick'],
            source_application['world_task_state'])
    _report(source_run / 'worker-report.json', run_id=source_id, case=case,
            operation='source', condition=None, snapshot_sha256=source_sha256,
            source_snapshot_sha256=None,
            total_ticks=source_application['total_tick'],
            world_state=source_application['world_task_state'])

    restored = next(event for event in sample['post_events']
                    if event['kind'] == 'application_restored')
    restored['parent_event_prefix'] = copy.deepcopy(source_application['event_prefix'])
    post_envelope = {
        'schema': 'memory-family-oracle-admission-v3',
        'protocol_sha256': protocol_sha256,
        'source_identity_sha256': source_identity_sha256,
        'case': case, 'operation': 'condition', 'condition': 'own',
        'source_snapshot_sha256': source_sha256,
    }
    post_writer = RunWriter(
        post_run / 'recording',
        _manifest(case, post_id, post_envelope,
                  admission.POST_RECORDING_MAX_BYTES,
                  parent_run_id=source_id,
                  parent_event_prefix=source_application['event_prefix']),
        max_bytes=admission.POST_RECORDING_MAX_BYTES)
    _emit(post_writer, sample['post_events'][0])
    post_application = copy.deepcopy(source_application)
    post_application['source_run_id'] = post_id
    post_application['event_prefix'] = _prefix(post_writer)
    post_sha256 = _register_snapshot(post_writer, post_application)
    _emit_trace(post_writer, sample['post_events'][1:], sample['post_rows'])
    total_ticks = sample['post_world_state']['last_tick'] + 1
    _finish(post_writer, total_ticks, sample['post_world_state'])
    _report(post_run / 'worker-report.json', run_id=post_id, case=case,
            operation='condition', condition='own', snapshot_sha256=post_sha256,
            source_snapshot_sha256=source_sha256, total_ticks=total_ticks,
            world_state=sample['post_world_state'])

    return {
        'root': root, 'sample': sample, 'case': case,
        'source': {'run_id': source_id, 'run_path': str(source_run)},
        'post': {'run_id': post_id, 'run_path': str(post_run),
                 'condition': 'own', 'source_snapshot_sha256': source_sha256},
        'plan_path': plan_path, 'plan_sha256': plan_sha256,
        'protocol_sha256': protocol_sha256,
        'source_identity_sha256': source_identity_sha256,
        'history_bundle_path': history_path,
        'history_bundle_sha256': history_sha256,
    }


def _admit(pair):
    return admission.admit_oracle_pair(
        pair['case'], pair['source'], pair['post'],
        plan_path=pair['plan_path'], plan_sha256=pair['plan_sha256'],
        protocol_sha256=pair['protocol_sha256'],
        source_identity_sha256=pair['source_identity_sha256'],
        history_bundle_path=pair['history_bundle_path'],
        history_bundle_sha256=pair['history_bundle_sha256'])


def _events_path(pair, part='post'):
    return Path(pair[part]['run_path']) / 'recording/events.jsonl'


def _edit_events(pair, edit, part='post'):
    path = _events_path(pair, part)
    events = [json.loads(line) for line in path.read_text().splitlines()]
    edit(events)
    path.write_text(''.join(json.dumps(event, allow_nan=False, sort_keys=True) + '\n'
                            for event in events))


def test_admits_one_change_pair_end_to_end_without_mutating_inputs(tmp_path):
    pair = _pair(tmp_path)
    before = _tree_hashes(tmp_path)
    result = _admit(pair)
    expected = [next(fact['id'] for fact in pair['case']['facts']
                     if fact['subject_id'] == pair['case']['closure_subject_id'])]
    assert set(result) == {'proof', 'proof_sha256', 'selector_resource'}
    assert result['proof']['gold_target_ids'] == expected
    assert result['proof_sha256'] == memory.sha256(result['proof'])
    assert result['selector_resource'] == {
        'resource': expected, 'resource_sha256': memory.sha256(expected),
        'provenance_sha256': result['proof_sha256'],
    }
    assert _tree_hashes(tmp_path) == before


@pytest.mark.parametrize('defect', ['byte', 'count', 'sequence', 'duplicate', 'unsafe'])
def test_rejects_raw_byte_count_sequence_and_json_path_tampering(tmp_path, defect):
    pair = _pair(tmp_path)
    run = Path(pair['post']['run_path'])
    if defect == 'byte':
        chunk = next((run / 'recording/chunks').iterdir())
        chunk.write_bytes(chunk.read_bytes() + b'corrupt')
    elif defect == 'count':
        path = run / 'recording/manifest.json'
        value = json.loads(path.read_text())
        value['recorded_ticks'] += 1
        path.write_text(json.dumps(value))
    elif defect == 'sequence':
        _edit_events(pair, lambda events: events[0].__setitem__('sequence', 1))
    elif defect == 'duplicate':
        path = run / 'worker-report.json'
        payload = path.read_text()
        path.write_text(payload.replace('{', '{"schema":"duplicate",', 1))
    else:
        _edit_events(pair, lambda events: next(event for event in events
            if event['kind'] == 'chunk').__setitem__('path', '../000000.npz'))
    with patch.object(admission.oracle, 'oracle_evidence') as oracle:
        with pytest.raises(ValueError):
            _admit(pair)
        oracle.assert_not_called()


def test_rejects_identity_non_own_substitute_and_snapshot_lineage(tmp_path):
    pair = _pair(tmp_path / 'first')
    other = _pair(tmp_path / 'other', row=5)
    defects = []
    wrong_run = copy.deepcopy(pair)
    wrong_run['source']['run_id'] = uuid.uuid4().hex
    defects.append(wrong_run)
    non_own = copy.deepcopy(pair)
    non_own['post']['condition'] = 'swapped'
    defects.append(non_own)
    substitute = copy.deepcopy(pair)
    substitute['post'] = copy.deepcopy(other['post'])
    substitute['post']['source_snapshot_sha256'] = pair['post']['source_snapshot_sha256']
    defects.append(substitute)
    wrong_snapshot = copy.deepcopy(pair)
    wrong_snapshot['post']['source_snapshot_sha256'] = 'f' * 64
    defects.append(wrong_snapshot)
    for defect in defects:
        with pytest.raises(ValueError):
            _admit(defect)

    manifest_path = Path(pair['post']['run_path']) / 'recording/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    manifest['parent_run_id'] = uuid.uuid4().hex
    manifest_path.write_text(json.dumps(manifest, allow_nan=False, sort_keys=True))
    with pytest.raises(ValueError):
        _admit(pair)


def test_rejects_history_selector_u_and_terminal_report_mismatch(tmp_path):
    messages = {'history': 'History bundle identity/U',
                'history-sha': 'History bundle identity/U',
                'selector': 'Oracle donor', 'u': 'selector/U',
                'report': 'terminal manifest'}
    for defect in ('history', 'history-sha', 'selector', 'u', 'report'):
        pair = _pair(tmp_path / defect)
        if defect in ('history', 'history-sha'):
            bundle = json.loads(pair['history_bundle_path'].read_text())
            if defect == 'history':
                bundle['u']['payload']['rules'] = []
            else:
                bundle['history_sha256'] = 'f' * 64
            pair['history_bundle_sha256'] = _canonical_file(
                pair['history_bundle_path'], bundle)
        elif defect == 'selector':
            _edit_events(pair, lambda events: next(event for event in events
                if event['kind'] == 'memory_selector_configured')['selector']
                .__setitem__('condition', 'swapped'))
        elif defect == 'u':
            _edit_events(pair, lambda events: next(event for event in events
                if event['kind'] == 'memory_selector_configured')['u']['provenance']
                .__setitem__('method', 'hand-authored-v1'))
        else:
            path = Path(pair['post']['run_path']) / 'worker-report.json'
            report = json.loads(path.read_text())
            report['total_ticks'] -= 1
            _canonical_file(path, report)
        with pytest.raises(ValueError, match=messages[defect]):
            _admit(pair)


def test_rejects_source_prefix_and_read_time_fingerprint_drift(tmp_path):
    pair = _pair(tmp_path / 'prefix')
    source = Path(pair['source']['run_path'])
    snapshot_path = source / 'snapshots/initial.snp'
    state = snapshots.read_snapshot(snapshot_path)
    state['application']['event_prefix']['sha256'] = 'e' * 64
    snapshot_path.unlink()
    snapshots.save_snapshot(state, snapshot_path)
    digest = _file_sha(snapshot_path)
    _edit_events(pair, lambda events: next(event for event in events
        if event['kind'] == 'snapshot_registered').__setitem__('sha256', digest), 'source')
    pair['post']['source_snapshot_sha256'] = digest
    with pytest.raises(ValueError):
        _admit(pair)

    pair = _pair(tmp_path / 'drift')
    original = admission.iter_ticks

    def drifting(recording):
        yield from original(recording)
        path = Path(recording) / 'events.jsonl'
        path.write_bytes(path.read_bytes() + b' ')
    with patch.object(admission, 'iter_ticks', side_effect=drifting), \
         patch.object(admission.oracle, 'oracle_evidence') as oracle, \
         pytest.raises(ValueError):
        _admit(pair)
    oracle.assert_not_called()
