"""Admit one explicit family-v3 source/own pair into the pure oracle.

This reader never discovers donors or launches owners.  It validates the exact
paths supplied by the caller, then passes only decoded retained evidence to the
pure evaluator.
"""
from __future__ import annotations

import copy
import hashlib
import math
from pathlib import Path
import time
import uuid

from palimpsest import artifacts, memory, memory_decision_world as world
from palimpsest.profiles import validate_decision
from palimpsest.records import iter_ticks
from palimpsest.replay import _initial_snapshot
from scripts import memory_family_oracle_v3 as oracle


MiB = 1024 * 1024
SOURCE_RECORDING_MAX_BYTES = 512 * MiB
POST_RECORDING_MAX_BYTES = 384 * MiB
MAX_ROWS = 2_100
MAX_PLAN_BYTES = 4 * MiB
MAX_HISTORY_BYTES = 8 * MiB
MAX_REPORT_BYTES = MiB
ENVELOPE_SCHEMA = 'memory-family-oracle-admission-v3'
REPORT_SCHEMA = 'memory-family-owner-report-v3'
REPORT_FIELDS = {'schema', 'run_id', 'case_id', 'operation', 'condition',
    'status', 'acquired', 'snapshot_sha256', 'source_snapshot_sha256',
    'total_ticks', 'final_phase', 'world_state'}
ROW_FIELDS = {'episode', 'tick', 'pose', 'next_pose', 'action', 'encoded_input',
    'raw_output', 'cam_left', 'cam_right', 'sensors'}


def _deadline(deadline):
    if deadline is None:
        return
    if (type(deadline) not in (int, float) or not math.isfinite(deadline)):
        raise ValueError('Admission deadline must be finite')
    if time.monotonic() >= deadline:
        raise TimeoutError('Oracle admission deadline exhausted')


def _digest(value, label):
    try:
        return memory._digest(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'Invalid {label} SHA-256') from error


def _run_id(value):
    try:
        valid = type(value) is str and uuid.UUID(value).hex == value
    except (AttributeError, ValueError):
        valid = False
    if not valid:
        raise ValueError('Run ID must be canonical UUID hex')
    return value


def _descriptor(value, *, post=False):
    fields = {'run_id', 'run_path', 'condition', 'source_snapshot_sha256'} if post else {
        'run_id', 'run_path'}
    if type(value) is not dict or set(value) != fields:
        raise ValueError('Run descriptor has missing or unknown fields')
    run_id = _run_id(value['run_id'])
    try:
        run = artifacts._safe_path(value['run_path'])
    except (OSError, TypeError, ValueError) as error:
        raise ValueError('Run descriptor has an unsafe path') from error
    if not run.is_dir() or run.name != run_id:
        raise ValueError('Run descriptor path and identity differ')
    result = {'run_id': run_id, 'run': run}
    if post:
        if value['condition'] != 'own':
            raise ValueError('Oracle admission requires the retained own continuation')
        _digest(value['source_snapshot_sha256'], 'source snapshot')
        result.update(condition='own', source_snapshot_sha256=value['source_snapshot_sha256'])
    return result


def _file_sha(path, deadline):
    path = artifacts._safe_path(path)
    if not path.is_file():
        raise ValueError(f'Missing admission input: {path.name}')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(MiB):
            _deadline(deadline)
            digest.update(block)
    return digest.hexdigest()


def _bounded_json(path, maximum, label):
    try:
        return artifacts._json(artifacts._read(path, maximum))
    except (OSError, TypeError, ValueError) as error:
        raise ValueError(f'Invalid bounded {label}') from error


def _read_run(descriptor, deadline):
    """Decode one terminal recording with one stable, exhaustive chunk pass."""
    _deadline(deadline)
    run = descriptor['run']
    metadata_paths = [run / 'recording/manifest.json', run / 'recording/events.jsonl']
    metadata_fingerprint = artifacts._fingerprint(metadata_paths)
    manifest = artifacts._manifest(run)
    events = artifacts._events(run)
    if manifest.get('run_id') != descriptor['run_id']:
        raise ValueError('Recording manifest belongs to another run')
    chunks = [event for event in events if event.get('kind') == 'chunk']
    if len(chunks) > artifacts.MAX_CHUNKS:
        raise ValueError('Recording has too many chunks')
    paths = metadata_paths.copy()
    for index, event in enumerate(chunks):
        if event.get('path') != f'chunks/{index:06d}.npz':
            raise ValueError('Unsafe or out-of-order recording chunk')
        paths.append(run / 'recording' / event['path'])
    fingerprint = artifacts._fingerprint(paths)
    if fingerprint[:len(metadata_paths)] != metadata_fingerprint:
        raise ValueError('Recording metadata changed during decode')
    rows = []
    try:
        for row in iter_ticks(run / 'recording'):
            _deadline(deadline)
            if len(rows) >= MAX_ROWS:
                raise ValueError('Family recording exceeds the tick bound')
            if type(row) is not dict or not ROW_FIELDS.issubset(row):
                raise ValueError('Family recording lacks policy/audit row fields')
            rows.append(row)
    except (KeyError, OSError, TypeError) as error:
        raise ValueError('Invalid family recording chunks') from error
    if not rows:
        raise ValueError('Family recording has no control rows')
    if artifacts._fingerprint(paths) != fingerprint:
        raise ValueError('Recording changed during admission')
    if any(event.get('run_id') != descriptor['run_id']
            and (event.get('kind') != 'chunk' or 'run_id' in event)
            for event in events):
        raise ValueError('Recording event belongs to another run')
    return {'run': run, 'manifest': manifest, 'events': events, 'rows': rows,
            'paths': paths, 'fingerprint': fingerprint}


def _manifest(data, case, protocol_sha256, source_identity_sha256, *,
              operation, condition, source_snapshot_sha256):
    manifest = data['manifest']
    expected_envelope = {'schema': ENVELOPE_SCHEMA,
        'protocol_sha256': protocol_sha256,
        'source_identity_sha256': source_identity_sha256,
        'case': case, 'operation': operation, 'condition': condition,
        'source_snapshot_sha256': source_snapshot_sha256}
    expected_profile = validate_decision(
        world.SCENARIO, 'checker', 'flynn', profile_sha256=case['profile_sha256'])
    maximum = SOURCE_RECORDING_MAX_BYTES if operation == 'source' else POST_RECORDING_MAX_BYTES
    if (manifest.get('status') not in ('completed', 'failed')
            or manifest.get('controller') != 'flynn'
            or manifest.get('requested_device') != 'cpu'
            or manifest.get('teacher_privileged') is not False
            or manifest.get('texture') != 'checker'
            or manifest.get('scenario') != expected_profile
            or manifest.get('seed') != case['seed']
            or manifest.get('memory_case') != case
            or manifest.get('memory_case_sha256') != memory.sha256(case)
            or manifest.get('acquisition_protocol_sha256') != case['acquisition_protocol_sha256']
            or manifest.get('recording_max_bytes') != maximum
            or manifest.get('memory_family_oracle_admission_v3') != expected_envelope):
        raise ValueError('Recording manifest differs from the family-v3 admission contract')
    if sum(path.stat().st_size for path in data['paths']) > maximum:
        raise ValueError('Recording bytes exceed the declared ceiling')


def _support(data, case, *, operation, condition, source_snapshot_sha256, deadline):
    """Bind one report and its single registered initial snapshot to raw bytes."""
    _deadline(deadline)
    report_path = data['run'] / 'worker-report.json'
    snapshot_path = data['run'] / 'snapshots/initial.snp'
    index_path = data['run'] / 'snapshots/index.json'
    index_present = index_path.exists() or index_path.is_symlink()
    paths = [*data['paths'], report_path, snapshot_path]
    if index_present:
        paths.append(index_path)
    fingerprint = artifacts._fingerprint(paths)
    if fingerprint[:len(data['paths'])] != data['fingerprint']:
        raise ValueError('Recording changed before support admission')
    report = _bounded_json(report_path, MAX_REPORT_BYTES, 'worker report')
    if type(report) is not dict or not REPORT_FIELDS.issubset(report):
        raise ValueError('Worker report lacks required fields')
    for key in ('snapshot_sha256',):
        _digest(report[key], f'worker report {key}')
    if source_snapshot_sha256 is not None:
        _digest(report['source_snapshot_sha256'], 'worker report source snapshot')
    if (report['schema'] != REPORT_SCHEMA
            or report['run_id'] != data['manifest']['run_id']
            or report['case_id'] != case['case_id']
            or report['operation'] != operation or report['condition'] != condition
            or report['status'] != 'recorded' or report['acquired'] is not True
            or report['source_snapshot_sha256'] != source_snapshot_sha256
            or type(report['total_ticks']) is not int or report['total_ticks'] < 0
            or type(report['final_phase']) is not str):
        raise ValueError('Worker report identity/status differs')
    registrations = artifacts.registered_snapshots(data['run'], data['events'])
    if len(registrations) != 1 or registrations[0]['initial'] is not True:
        raise ValueError('Run requires exactly one registered initial snapshot')
    snapshot, entry, _ = _initial_snapshot(data)
    if entry != registrations[0] or report['snapshot_sha256'] != entry['sha256']:
        raise ValueError('Worker report snapshot differs from its registered bytes')
    if data['run'] / 'snapshots' / entry['filename'] != snapshot_path:
        raise ValueError('Registered initial snapshot path differs')
    try:
        state = world.validate_state(report['world_state'])
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Worker report has invalid world state') from error
    if state['case'] != case or state['profile_sha256'] != case['profile_sha256']:
        raise ValueError('Worker report belongs to another family case')
    manifest = data['manifest']
    expected_status = 'failed' if report['final_phase'] == 'failed' else 'completed'
    try:
        manifest_world = world.validate_state(manifest.get('world_state'))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Terminal manifest has invalid world state') from error
    if (manifest.get('status') != expected_status
            or manifest.get('final_phase') != report['final_phase']
            or manifest.get('total_tick') != report['total_ticks']
            or manifest_world != state):
        raise ValueError('Worker report differs from the terminal manifest')
    if 'outcome' in report and report['outcome'] != manifest.get('last_outcome'):
        raise ValueError('Worker report outcome differs from the terminal manifest')
    application = snapshot.get('application') if type(snapshot) is dict else None
    if type(application) is not dict:
        raise ValueError('Registered initial snapshot lacks its application state')
    if (index_path.exists() or index_path.is_symlink()) != index_present:
        raise ValueError('Snapshot registry changed during support admission')
    if artifacts._fingerprint(paths) != fingerprint:
        raise ValueError('Run support changed during admission')
    return {'report': report, 'report_path': report_path, 'snapshot': snapshot,
            'application': application, 'entry': entry, 'world_state': state,
            'paths': paths, 'fingerprint': fingerprint}


def _policy_bindings(data):
    try:
        from scripts.verify_flynn_memory_transfer import policy_bindings
        policy_bindings(data)
    except ValueError:
        raise
    except (AttributeError, IndexError, KeyError, TypeError) as error:
        raise ValueError('Recorded policy-call bindings are invalid') from error


def _rows(data):
    return [{'episode': int(row['episode']), 'tick': int(row['tick']),
             'pose': row['pose'].tolist(), 'next_pose': row['next_pose'].tolist()}
            for row in data['rows']]


def _recording_sha256(data, deadline):
    files = []
    for path in data['paths']:
        _deadline(deadline)
        files.append({'path': path.relative_to(data['run']).as_posix(),
                      'sha256': _file_sha(path, deadline)})
    return memory.sha256(files)


def _history(path, expected_sha256, deadline):
    path = artifacts._safe_path(path)
    _digest(expected_sha256, 'history bundle')
    if _file_sha(path, deadline) != expected_sha256:
        raise ValueError('History bundle checksum differs')
    bundle = _bounded_json(path, MAX_HISTORY_BYTES, 'history bundle')
    if type(bundle) is not dict or not {'e', 'u', 'history_sha256'}.issubset(bundle):
        raise ValueError('History bundle lacks its E/U identity')
    try:
        history = memory.validate_e(bundle['e'])
        fitted_record = memory.validate_u(bundle['u'])
        fitted = memory.fit(history)
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('History bundle identity/U is invalid') from error
    if (bundle['history_sha256'] != memory.sha256(history)
            or memory.canonical_bytes(fitted_record) != memory.canonical_bytes(fitted)):
        raise ValueError('History bundle identity/U differs from a fresh fit of E')
    return history, fitted


def _unchanged(paths, fingerprint, label):
    if artifacts._fingerprint(paths) != fingerprint:
        raise ValueError(f'{label} changed during oracle admission')


def admit_oracle_pair(case, source, post, *, plan_path, plan_sha256,
                      protocol_sha256, source_identity_sha256,
                      history_bundle_path, history_bundle_sha256, deadline=None):
    """Return proof/resource for one checksum-bound retained source/own pair."""
    _deadline(deadline)
    case = world.validate_case(copy.deepcopy(case))
    if case['version'] != 3:
        raise ValueError('Raw oracle admission requires a family-v3 case')
    for value, label in ((plan_sha256, 'plan'), (protocol_sha256, 'protocol'),
                         (source_identity_sha256, 'source identity'),
                         (history_bundle_sha256, 'history bundle')):
        _digest(value, label)
    source = _descriptor(source)
    post = _descriptor(post, post=True)
    if source['run'] == post['run'] or source['run_id'] == post['run_id']:
        raise ValueError('Source and post must be distinct runs')

    plan_path = artifacts._safe_path(plan_path)
    history_bundle_path = artifacts._safe_path(history_bundle_path)
    if plan_path.stat().st_size > MAX_PLAN_BYTES:
        raise ValueError('Frozen plan exceeds admission bound')
    inputs = [plan_path, history_bundle_path]
    input_fingerprint = artifacts._fingerprint(inputs)
    if _file_sha(plan_path, deadline) != plan_sha256:
        raise ValueError('Frozen plan checksum differs')
    history, fitted = _history(history_bundle_path, history_bundle_sha256, deadline)

    source_data = _read_run(source, deadline)
    post_data = _read_run(post, deadline)
    _manifest(source_data, case, protocol_sha256, source_identity_sha256,
              operation='source', condition=None, source_snapshot_sha256=None)
    _manifest(post_data, case, protocol_sha256, source_identity_sha256,
              operation='condition', condition='own',
              source_snapshot_sha256=post['source_snapshot_sha256'])
    source_support = _support(source_data, case, operation='source', condition=None,
                              source_snapshot_sha256=None, deadline=deadline)
    if post['source_snapshot_sha256'] != source_support['entry']['sha256']:
        raise ValueError('Post descriptor does not bind the admitted source snapshot')
    post_support = _support(post_data, case, operation='condition', condition='own',
                            source_snapshot_sha256=source_support['entry']['sha256'],
                            deadline=deadline)

    source_application = source_support['application']
    post_application = post_support['application']
    source_boundary = source_application.get('episode_step')
    if (source_support['report']['final_phase'] != 'paused'
            or source_support['report']['total_ticks'] != source_boundary
            or source_support['world_state'] != source_application.get('world_task_state')):
        raise ValueError('Source did not finish paused at its acquired snapshot boundary')
    normalized_source, normalized_post = copy.deepcopy(source_application), copy.deepcopy(post_application)
    for application in (normalized_source, normalized_post):
        if type(application) is not dict:
            raise ValueError('Initial snapshot application is invalid')
        application.pop('source_run_id', None)
        application.pop('event_prefix', None)
    if memory.canonical_bytes(normalized_source) != memory.canonical_bytes(normalized_post):
        raise ValueError('Post initial application differs from the source snapshot')
    if (post_data['manifest'].get('parent_run_id') != source['run_id']
            or post_data['manifest'].get('parent_event_prefix') != source_application.get('event_prefix')):
        raise ValueError('Post manifest restore lineage differs from the source snapshot')
    if (source_data['manifest'].get('parent_run_id') is not None
            or source_data['manifest'].get('parent_event_prefix') is not None):
        raise ValueError('Source recording unexpectedly has restore lineage')

    total_ticks = post_support['report']['total_ticks']
    last_tick = post_support['world_state']['last_tick']
    if last_tick not in (total_ticks - 1, total_ticks):
        raise ValueError('Post report world cursor differs from terminal tick count')
    if (last_tick == total_ticks) != (post_support['report']['final_phase'] == 'failed'):
        raise ValueError('Post sensor-only cursor does not match terminal failure status')

    _policy_bindings(source_data)
    _policy_bindings(post_data)
    configured = [event for event in post_data['events']
                  if event.get('kind') == 'memory_selector_configured']
    if len(configured) != 1:
        raise ValueError('Own continuation requires one selector configuration')
    recorded_u, recorded_selector = configured[0].get('u'), configured[0].get('selector')
    if (memory.canonical_bytes(recorded_u) != memory.canonical_bytes(fitted)
            or type(recorded_selector) is not dict
            or recorded_selector.get('provenance_sha256') != history_bundle_sha256):
        raise ValueError('Recorded own selector/U differs from the fitted history bundle')

    source_rows, post_rows = _rows(source_data), _rows(post_data)
    bindings = {'protocol_sha256': protocol_sha256, 'plan_sha256': plan_sha256,
        'source_identity_sha256': source_identity_sha256,
        'source': {'run_id': source['run_id'],
            'recording_sha256': _recording_sha256(source_data, deadline),
            'report_sha256': _file_sha(source_support['report_path'], deadline),
            'snapshot_sha256': source_support['entry']['sha256']},
        'post': {'run_id': post['run_id'], 'condition': 'own',
            'recording_sha256': _recording_sha256(post_data, deadline),
            'report_sha256': _file_sha(post_support['report_path'], deadline),
            'source_snapshot_sha256': source_support['entry']['sha256'],
            'selector_sha256': memory.sha256(recorded_selector),
            'u_sha256': memory.sha256(recorded_u),
            'history_sha256': memory.sha256(history),
            'history_bundle_sha256': history_bundle_sha256}}
    supplied = (case, source_application, source_data['events'], source_rows,
                post_data['events'], post_rows, post_support['world_state'], bindings)
    proof = oracle.oracle_evidence(*supplied)
    proof = oracle.validate_oracle_evidence(proof, *supplied)
    selector = oracle.selector_resource('oracle', proof, case=case,
        source_application=source_application, source_events=source_data['events'],
        source_rows=source_rows, post_events=post_data['events'], post_rows=post_rows,
        post_world_state=post_support['world_state'], bindings=bindings)

    _unchanged(inputs, input_fingerprint, 'Plan/history input')
    _unchanged(source_support['paths'], source_support['fingerprint'], 'Source evidence')
    _unchanged(post_support['paths'], post_support['fingerprint'], 'Post evidence')
    return {'proof': proof, 'proof_sha256': memory.sha256(proof),
            'selector_resource': selector}
