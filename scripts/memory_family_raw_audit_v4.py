"""Read-only, pre-prune raw audit for one closed memory-family v1 run.

This executable does not launch an owner, convert or prune a recording, admit a
source/condition pair, or publish a case.  Every scientific claim stays false.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import math
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import uuid


# Direct-file and module entry points must resolve this worktree before imports.
REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO_ROOT / 'src'), str(REPO_ROOT)]

from palimpsest import artifacts, memory, memory_decision_world as world, snapshots
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_oracle_admission_v3 as admission
from scripts import memory_family_oracle_v3 as oracle


MiB = 1024**2
PROTOCOL = compact.PROTOCOL
PROTOCOL_BYTES = compact.PROTOCOL_BYTES
PROTOCOL_SHA256 = hashlib.sha256(PROTOCOL_BYTES).hexdigest()
RAW_CONTRACT = PROTOCOL['raw_audit']
RAW_LIMITS = copy.deepcopy(RAW_CONTRACT['limits'])
RECEIPT_SUFFIX = '.raw-audit.json'
FORBIDDEN_EVENTS = {
    'branch_created', 'controller_replaced', 'eyes_changed',
    'replay_divergence', 'replay_finished',
}


class PublicationIndeterminate(RuntimeError):
    """The final name was linked but durable rollback could not be proven."""


def _fields(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f'{label} has missing or unknown fields')


def _digest(value, label):
    try:
        memory._digest(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f'Invalid {label} SHA-256') from error
    return value


def _run_id(value):
    try:
        parsed = uuid.UUID(value) if type(value) is str else None
    except (AttributeError, TypeError, ValueError) as error:
        raise ValueError('Run ID must be a canonical UUID') from error
    if parsed is None or value != parsed.hex:
        raise ValueError('Run ID must use canonical UUID hex')
    return value


def _deadline(deadline):
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError('Raw-audit deadline must be finite')
    if time.monotonic() >= deadline:
        raise TimeoutError('Raw-audit deadline exhausted')


def _public_deadline(deadline):
    entered = time.monotonic()
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError('Raw-audit deadline must be finite')
    if deadline - entered > RAW_CONTRACT['deadline_seconds_max']:
        raise ValueError('Raw-audit deadline exceeds 300 seconds from entry')
    if entered >= deadline:
        raise TimeoutError('Raw-audit deadline exhausted')


def deadline_from_seconds(seconds):
    if (type(seconds) not in (int, float) or not math.isfinite(seconds)
            or not 0 < seconds <= RAW_CONTRACT['deadline_seconds_max']):
        raise ValueError('Raw-audit duration exceeds its frozen cap')
    return time.monotonic() + seconds


def _protocol_descriptor():
    return {
        'path': 'docs/plans/memory-family-compact-evidence-v4-protocol.json',
        'size_bytes': len(PROTOCOL_BYTES), 'sha256': PROTOCOL_SHA256,
    }


def canonical_source_identity(owner_source_sha256=None):
    """Return exact protocol/behavior identities without importing an owner."""
    if owner_source_sha256 is not None:
        _digest(owner_source_sha256, 'owner source identity')
    behavior = compact.behavior_source_identities(REPO_ROOT)
    return {
        'schema': 'memory-family-raw-audit-source-v1',
        'protocol': _protocol_descriptor(),
        'owner_source_sha256': owner_source_sha256,
        'behavior_sources': behavior,
        'behavior_sources_sha256': memory.sha256(behavior),
    }


def validate_raw_limits(operation, *, row_count, event_count, chunk_count,
                        event_bytes, recording_bytes, report_bytes,
                        snapshot_bytes, file_count):
    """Apply exact operation-specific raw tree limits, including equality."""
    if operation not in RAW_LIMITS:
        raise ValueError('Unknown raw-audit operation')
    values = {
        'row_count': row_count, 'event_count': event_count,
        'chunk_count': chunk_count, 'event_bytes': event_bytes,
        'recording_bytes': recording_bytes, 'report_bytes': report_bytes,
        'snapshot_bytes': snapshot_bytes, 'file_count': file_count,
    }
    if any(type(value) is not int or value < 0 for value in values.values()):
        raise ValueError('Raw-audit limits require nonnegative exact integers')
    limits = RAW_LIMITS[operation]
    if (not 1 <= row_count <= limits['max_rows']
            or not 1 <= event_count <= limits['max_events']
            or not 1 <= chunk_count <= limits['max_chunks']
            or chunk_count != (row_count + compact.CHUNK_ROWS - 1) // compact.CHUNK_ROWS
            or not 1 <= event_bytes <= limits['events_max_bytes']
            or not 1 <= recording_bytes <= limits['recording_max_bytes']
            or not 1 <= report_bytes <= limits['report_max_bytes']
            or not 1 <= file_count <= limits['max_files']):
        raise ValueError('Raw run exceeds its frozen operation limits')
    if operation == 'source':
        if not 1 <= snapshot_bytes <= limits['snapshot_max_bytes']:
            raise ValueError('Source snapshot exceeds its frozen limit')
    elif snapshot_bytes != 0:
        raise ValueError('Condition raw run cannot carry a local snapshot')


def _path_fingerprint(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


def _hash_file(path, deadline, maximum, *, expected=None):
    """Hash one regular file through O_NOFOLLOW and rebind its pathname."""
    path = artifacts._safe_path(path)
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0))
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or type(maximum) is not int or maximum < 0
                or before.st_size > maximum):
            raise ValueError('Raw inventory file type, links, or size are invalid')
        if expected is not None and _path_fingerprint(before) != expected:
            raise RuntimeError('Raw inventory file changed before hashing')
        digest = hashlib.sha256()
        total = 0
        with os.fdopen(descriptor, 'rb', closefd=False) as stream:
            while True:
                _deadline(deadline)
                block = stream.read(min(MiB, maximum + 1 - total))
                if not block:
                    break
                total += len(block)
                if total > maximum:
                    raise ValueError('Raw inventory file grew beyond its limit')
                digest.update(block)
        after = os.fstat(descriptor)
        named = os.stat(path, follow_symlinks=False)
    finally:
        os.close(descriptor)
    if (after.st_nlink != 1
            or _path_fingerprint(before) != _path_fingerprint(after)
            or _path_fingerprint(after) != _path_fingerprint(named)):
        raise RuntimeError('Raw inventory file changed while hashing')
    return ({'path': None, 'size_bytes': after.st_size,
             'sha256': digest.hexdigest()}, (after.st_dev, after.st_ino))


def _allowed_file(relative, operation):
    if relative in {
            Path('worker-report.json'), Path('recording/manifest.json'),
            Path('recording/events.jsonl')}:
        return True
    if (len(relative.parts) == 3
            and relative.parts[:2] == ('recording', 'chunks')
            and len(relative.stem) == 6 and relative.stem.isdigit()
            and relative.suffix == '.npz'):
        return True
    return operation == 'source' and relative == Path('snapshots/initial.snp')


def _file_limit(relative, operation):
    limits = RAW_LIMITS[operation]
    if relative == Path('recording/manifest.json'):
        return artifacts.MAX_MANIFEST
    if relative == Path('recording/events.jsonl'):
        return limits['events_max_bytes']
    if relative == Path('worker-report.json'):
        return limits['report_max_bytes']
    if relative == Path('snapshots/initial.snp'):
        return limits['snapshot_max_bytes']
    return limits['recording_max_bytes']


def _inventory(run, operation, deadline):
    limits = RAW_LIMITS[operation]
    allowed_directories = {
        Path('.'), Path('recording'), Path('recording/chunks'),
        *({Path('snapshots')} if operation == 'source' else set()),
    }
    candidates = []
    inodes = set()
    for directory, directories, names in os.walk(run, followlinks=False):
        _deadline(deadline)
        current = Path(directory)
        relative_directory = current.relative_to(run)
        relative_directory = Path('.') if not relative_directory.parts \
            else relative_directory
        if relative_directory not in allowed_directories:
            raise ValueError('Raw run contains an unregistered directory')
        directories.sort()
        names.sort()
        for name in directories:
            child = current / name
            if child.is_symlink() or not child.is_dir():
                raise ValueError('Raw run directory is a symlink or alias')
        for name in names:
            if len(candidates) >= limits['max_files']:
                raise ValueError('Raw run exceeds its file-count limit')
            path = current / name
            relative = path.relative_to(run)
            metadata = path.lstat()
            if (not _allowed_file(relative, operation)
                    or not stat.S_ISREG(metadata.st_mode)
                    or metadata.st_nlink != 1):
                raise ValueError('Raw run contains an unregistered, linked, or nonregular file')
            inode = (metadata.st_dev, metadata.st_ino)
            if inode in inodes:
                raise ValueError('Raw run contains a hard-link alias')
            inodes.add(inode)
            candidates.append((relative, path, _path_fingerprint(metadata)))

    candidates.sort(key=lambda value: value[0].as_posix())
    sizes = {relative.as_posix(): fingerprint[3]
             for relative, _, fingerprint in candidates}
    required = {'recording/manifest.json', 'recording/events.jsonl',
                'worker-report.json'}
    if not required.issubset(sizes):
        raise ValueError('Raw tree lacks required metadata or report files')
    recording_bytes = sum(size for name, size in sizes.items()
                          if name.startswith('recording/'))
    if (recording_bytes > limits['recording_max_bytes']
            or any(size > _file_limit(Path(name), operation)
                   for name, size in sizes.items())):
        raise ValueError('Raw tree exceeds a prehash byte limit')

    rows = []
    recording_remaining = limits['recording_max_bytes']
    for relative, path, fingerprint in candidates:
        maximum = _file_limit(relative, operation)
        if relative.parts[0] == 'recording':
            maximum = min(maximum, recording_remaining)
        descriptor, _ = _hash_file(
            path, deadline, maximum, expected=fingerprint)
        if relative.parts[0] == 'recording':
            recording_remaining -= descriptor['size_bytes']
        if recording_remaining < 0:
            raise ValueError('Raw recording grew beyond its aggregate limit')
        descriptor['path'] = relative.as_posix()
        rows.append(descriptor)
    return rows


def _inventory_value(files):
    recording = sum(row['size_bytes'] for row in files
                    if row['path'].startswith('recording/'))
    support = sum(row['size_bytes'] for row in files
                  if not row['path'].startswith('recording/'))
    return {
        'schema': 'memory-family-raw-inventory-v1',
        'files': copy.deepcopy(files), 'file_count': len(files),
        'recording_bytes': recording, 'support_bytes': support,
        'total_bytes': recording + support,
        'tree_sha256': memory.sha256(files),
    }


def _preflight_limits(run, operation, files):
    """Reject operation caps from bounded metadata before decoding a chunk."""
    by_path = {row['path']: row for row in files}
    required = {'recording/manifest.json', 'recording/events.jsonl',
                'worker-report.json'}
    if not required.issubset(by_path):
        raise ValueError('Raw tree lacks required metadata or report files')
    limits = RAW_LIMITS[operation]
    inventory = _inventory_value(files)
    snapshot_bytes = (by_path.get('snapshots/initial.snp', {})
                      .get('size_bytes', 0))
    if (by_path['recording/events.jsonl']['size_bytes'] > limits['events_max_bytes']
            or inventory['recording_bytes'] > limits['recording_max_bytes']
            or by_path['worker-report.json']['size_bytes'] > limits['report_max_bytes']
            or snapshot_bytes > limits['snapshot_max_bytes']):
        raise ValueError('Raw metadata or support bytes exceed predecode limits')
    manifest = artifacts._manifest(run)
    events = artifacts._events(run)
    chunks = [event for event in events if event.get('kind') == 'chunk']
    row_count = manifest.get('recorded_ticks')
    if (type(row_count) is not int
            or any(type(event.get('count')) is not int for event in chunks)
            or sum(event['count'] for event in chunks) != row_count):
        raise ValueError('Raw metadata row counts differ before decode')
    validate_raw_limits(
        operation, row_count=row_count, event_count=len(events),
        chunk_count=len(chunks),
        event_bytes=by_path['recording/events.jsonl']['size_bytes'],
        recording_bytes=inventory['recording_bytes'],
        report_bytes=by_path['worker-report.json']['size_bytes'],
        snapshot_bytes=snapshot_bytes,
        file_count=inventory['file_count'])


def _array(value, dtype, shape, label):
    import numpy as np

    array = np.asarray(value)
    if (array.dtype.str != dtype or array.shape != shape
            or array.dtype.kind in 'fc' and not np.isfinite(array).all()):
        raise ValueError(f'Invalid raw {label}')
    return array


def _audit_rows(rows, operation):
    import numpy as np

    if type(rows) is not list or not rows:
        raise ValueError('Raw audit requires one nonempty row trace')
    camera_sequence = hashlib.sha256()
    row_sequence = hashlib.sha256()
    projection = []
    start = None
    for offset, row in enumerate(rows):
        _fields(row, compact.RAW_FIELDS, 'Raw audit row')
        if type(row['episode']) is not int or row['episode'] != 0 \
                or type(row['tick']) is not int or row['tick'] < 0:
            raise ValueError('Raw row has an invalid episode or tick')
        start = row['tick'] if start is None else start
        if row['tick'] != start + offset:
            raise ValueError('Raw row ticks are not contiguous')
        for name, dtype, shape, _ in compact.ROW_FIELDS[:len(compact.RETAINED)]:
            _array(row[name], dtype, shape, name)
        cameras = {}
        for name in compact.CAMERAS:
            camera = _array(row[name], '|u1', (128, 128, 3), name)
            cameras[name] = camera
            camera_sequence.update(bytes.fromhex(snapshots.state_digest(camera)))
        if (not np.asarray(row['eyes']).all()
                or not np.array_equal(cameras['cam_left'], cameras['raw_cam_left'])
                or not np.array_equal(cameras['cam_right'], cameras['raw_cam_right'])):
            raise ValueError('Raw row eyes or effective cameras differ')
        for timing in ('latency', 'step_latency'):
            _array(row[timing], '<f8', (), timing)
        population = np.asarray(row['population_stats'])
        if (population.dtype.str != '<f8' or population.ndim != 2
                or population.shape[1:] != (4,)
                or not np.isfinite(population).all()):
            raise ValueError('Invalid raw population statistics')
        row_value = {key: value for key, value in row.items()
                     if key not in ('latency', 'step_latency')}
        row_sequence.update(bytes.fromhex(snapshots.state_digest(row_value)))
        projection.append({
            'episode': row['episode'], 'tick': row['tick'],
            'pose': row['pose'].tolist(),
            'next_pose': row['next_pose'].tolist(),
        })
    if operation == 'source' and start != 0:
        raise ValueError('Source raw rows must start at tick zero')
    oracle._rows(copy.deepcopy(projection), start, f'{operation} raw rows')
    return projection, camera_sequence.hexdigest(), row_sequence.hexdigest()


def _prefix(application, events_path):
    prefix = application.get('event_prefix') if type(application) is dict else None
    _fields(prefix, {'sha256', 'size_bytes', 'event_count'},
            'Source snapshot event prefix')
    size = prefix['size_bytes']
    payload = artifacts._read(events_path, RAW_LIMITS['source']['events_max_bytes'])
    if (type(size) is not int or not 1 <= size <= len(payload)
            or type(prefix['event_count']) is not int
            or prefix['event_count'] < 1):
        raise ValueError('Invalid source snapshot event prefix')
    retained = payload[:size]
    if (not retained.endswith(b'\n')
            or retained.count(b'\n') != prefix['event_count']
            or hashlib.sha256(retained).hexdigest() != prefix['sha256']):
        raise ValueError('Source snapshot event prefix differs from raw bytes')
    return copy.deepcopy(prefix)


def _terminal(data, report, case, operation, condition, source_run_id,
              source_snapshot_sha256):
    manifest = data['manifest']
    try:
        state = world.validate_state(copy.deepcopy(report['world_state']))
        manifest_state = world.validate_state(copy.deepcopy(manifest['world_state']))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Raw terminal world state is invalid') from error
    expected_status = 'failed' if report['final_phase'] == 'failed' else 'completed'
    if (report['schema'] != admission.REPORT_SCHEMA
            or report['run_id'] != manifest['run_id']
            or report['case_id'] != case['case_id']
            or report['operation'] != operation or report['condition'] != condition
            or report['status'] != 'recorded' or report['acquired'] is not True
            or type(report['total_ticks']) is not int or report['total_ticks'] < 1
            or type(report['final_phase']) is not str
            or manifest['status'] != expected_status
            or manifest.get('final_phase') != report['final_phase']
            or manifest.get('total_tick') != report['total_ticks']
            or manifest_state != state or state['case'] != case
            or state['profile_sha256'] != case['profile_sha256']):
        raise ValueError('Raw report and terminal manifest differ')
    _digest(report['snapshot_sha256'], 'worker snapshot')
    if operation == 'source':
        if (report['source_snapshot_sha256'] is not None
                or manifest.get('parent_run_id') is not None
                or manifest.get('parent_event_prefix') is not None
                or report['final_phase'] != 'paused'
                or manifest.get('last_outcome') is not None):
            raise ValueError('Source raw run has condition lineage or terminal state')
    else:
        _digest(report['source_snapshot_sha256'], 'worker source snapshot')
        if (report['source_snapshot_sha256'] != source_snapshot_sha256
                or report['snapshot_sha256'] != source_snapshot_sha256
                or manifest.get('parent_run_id') != source_run_id
                or type(manifest.get('parent_event_prefix')) is not dict):
            raise ValueError('Condition raw run has wrong source lineage')
    last_tick = state['last_tick']
    total_ticks = report['total_ticks']
    natural_failure = operation == 'condition' and report['final_phase'] == 'failed'
    if (operation == 'source' and last_tick != total_ticks - 1) \
            or operation == 'condition' and last_tick not in (total_ticks - 1, total_ticks) \
            or operation == 'condition' and (last_tick == total_ticks) != natural_failure:
        raise ValueError('Raw terminal cursor differs from retained failure status')
    return state, {
        'manifest_status': manifest['status'],
        'final_phase': report['final_phase'], 'total_ticks': total_ticks,
        'last_tick': last_tick, 'natural_failure': natural_failure,
        'replacement': False, 'world_state_sha256': memory.sha256(state),
        'snapshot_sha256': report['snapshot_sha256'],
        'source_run_id': source_run_id,
    }


def _source_application(value, case, run_id, report):
    value = oracle._bounded(value, 'source application')
    if type(value) is not dict or set(value) != oracle.APPLICATION_FIELDS:
        raise ValueError('Source application differs from the snapshot contract')
    boundary = value.get('episode_step')
    if (value.get('schema_version') != 8 or value.get('source_run_id') != run_id
            or value.get('scenario') != world.SCENARIO
            or value.get('controller') != 'flynn' or value.get('episode') != 0
            or type(boundary) is not int or boundary <= 0
            or value.get('total_tick') != boundary
            or boundary != report['total_ticks'] or value.get('phase') != 'paused'
            or value.get('seed') != case['seed'] or value.get('texture') != 'checker'
            or value.get('execution_mode') not in ('live', 'policy')
            or value.get('eyes') != {'left': True, 'right': True}
            or value.get('last_outcome') is not None
            or value.get('episode_finished') is not False
            or value.get('session_exhausted') is not False
            or value.get('recording_failed') is not False
            or value.get('pending_commands') != []
            or type(value.get('original_commands')) is not dict
            or type(value.get('receipts')) is not dict):
        raise ValueError('Source is not the paused acquired family boundary')
    task = oracle.memory_decision.validate_state(value['memory'])
    source_world = world.validate_state(value['world_task_state'])
    if (not oracle.memory_decision.acquired_boundary(task)
            or task['cursor']['tick'] != boundary - 1
            or source_world != report['world_state']
            or source_world['case'] != case
            or source_world['last_tick'] != boundary - 1
            or source_world['armed_boundary_tick'] is not None
            or source_world['event_tick'] is not None
            or source_world['decision_tick'] is not None
            or source_world['acquired_state_sha256'] is not None
            or source_world['applied']):
        raise ValueError('Source memory/world cursors differ from the boundary')
    return value, task, source_world, boundary


def _policy_calls(events):
    calls = [event for event in events
             if event.get('kind') == 'neural_policy_call']
    event_fields = {
        'sequence', 'kind', 'run_id', 'episode', 'episode_step', 'tick',
        'observation_sha256', 'cameras_sha256', 'sensors', 'result_sha256',
    }
    for event in calls:
        _fields(event, event_fields, 'Neural policy call')
        _fields(event['cameras_sha256'], {'cam_left', 'cam_right'},
                'Neural policy cameras')
        _fields(event['result_sha256'],
                {'action', 'encoded_input', 'raw_output'},
                'Neural policy result')
        _fields(event['sensors'],
                {'collision', 'collision_angle', 'wind_direction'},
                'Neural policy sensors')
        for name, value in {**event['cameras_sha256'],
                            **event['result_sha256']}.items():
            _digest(value, f'neural policy {name}')
        _digest(event['observation_sha256'], 'neural policy observation')
        sensors = event['sensors']
        angle = sensors['collision_angle']
        wind = sensors['wind_direction']
        if (type(sensors['collision']) is not bool
                or (angle is not None and (type(angle) not in (int, float)
                                           or not math.isfinite(angle)))
                or type(wind) is not list or len(wind) != 2
                or any(type(value) not in (int, float)
                       or not math.isfinite(value) for value in wind)):
            raise ValueError('Neural policy sensors have an invalid exact schema')
    return calls


def _normal_condition_terminal(events, manifest, terminal_state, schedule):
    finished = [(index, event) for index, event in enumerate(events)
                if event.get('kind') == 'episode_finished']
    outcome = manifest.get('last_outcome')
    if outcome is None:
        if (finished or terminal_state['manifest_status'] != 'completed'
                or terminal_state['final_phase'] != 'paused'):
            raise ValueError('Paused condition has a normal terminal event')
        return
    if len(finished) != 1 or terminal_state['manifest_status'] != 'completed':
        raise ValueError('Normal condition requires one completed terminal event')
    index, event = finished[0]
    _fields(event, {
        'sequence', 'kind', 'run_id', 'episode', 'episode_step', 'tick',
        'outcome', 'metrics',
    }, 'Normal episode terminal')
    _fields(outcome, {'reason', 'episode', 'steps', 'final_distance'},
            'Normal episode outcome')
    metrics = manifest.get('metrics')
    _fields(metrics, {'reward', 'contact_ticks', 'path_length'},
            'Normal episode metrics')
    total_ticks = terminal_state['total_ticks']
    reason = outcome['reason']
    expected_phase = 'truncated' if reason == 'time_limit' else 'terminated'
    cap = schedule['boundary_tick'] + 900
    if (reason not in ('goal', 'stalled', 'collision', 'time_limit')
            or type(outcome['episode']) is not int or outcome['episode'] != 0
            or type(outcome['steps']) is not int
            or outcome['steps'] != total_ticks
            or type(outcome['final_distance']) is not float
            or not math.isfinite(outcome['final_distance'])
            or outcome['final_distance'] < 0.0
            or terminal_state['final_phase'] != expected_phase
            or terminal_state['last_tick'] != total_ticks - 1
            or not schedule['decision_tick'] < total_ticks <= cap
            or reason == 'time_limit' and total_ticks != cap
            or event['kind'] != 'episode_finished'
            or event['run_id'] != manifest.get('run_id')
            or type(event['sequence']) is not int or event['sequence'] != index
            or event['outcome'] != outcome or event['metrics'] != metrics
            or type(metrics['reward']) is not float
            or not math.isfinite(metrics['reward'])
            or type(metrics['contact_ticks']) is not int
            or metrics['contact_ticks'] < 0
            or type(metrics['path_length']) is not float
            or not math.isfinite(metrics['path_length'])
            or metrics['path_length'] < 0.0
            or any(child.get('kind') != 'chunk'
                   for child in events[index + 1:])):
        raise ValueError('Normal condition terminal differs from engine output')
    oracle._event_boundary(event, total_ticks, 'episode_finished')


def _condition_terminal(data, case, projection, terminal_state, schedule):
    events = data['events']
    manifest = data['manifest']
    last_row = projection[-1]['tick']
    last_tick = terminal_state['last_tick']
    tail = terminal_state['natural_failure']
    expected_ticks = {row['tick'] for row in projection} | \
        ({last_tick} if tail else set())
    sensed = [(index, event) for index, event in enumerate(events)
              if event.get('kind') == 'memory_sensed']
    if (len(sensed) != len(expected_ticks)
            or {event.get('episode_step') for _, event in sensed}
            != expected_ticks):
        raise ValueError('Condition sensed packets differ from rows and terminal boundary')
    failures = [(index, event) for index, event in enumerate(events)
                if event.get('kind') == 'runtime_failure']
    if not tail:
        if failures:
            raise ValueError('Successful condition contains a terminal failure')
        _normal_condition_terminal(events, manifest, terminal_state, schedule)
        return
    if any(event.get('kind') == 'episode_finished' for event in events):
        raise ValueError('Natural condition failure contains a normal terminal event')
    if last_tick != last_row + 1 or last_tick <= schedule['decision_tick']:
        raise ValueError('Condition failure is not a terminal sensor-only tick')
    terminal_sensed = [(index, event) for index, event in sensed
                       if event.get('episode_step') == last_tick]
    if (len(terminal_sensed) != 1 or len(failures) != 1
            or terminal_sensed[0][0] + 1 != failures[0][0]
            or any(event.get('kind') != 'chunk'
                   for event in events[failures[0][0] + 1:])):
        raise ValueError('Terminal sensor-only tick has progress or wrong ordering')
    failure = failures[0][1]
    _fields(failure, {
        'sequence', 'kind', 'run_id', 'episode', 'episode_step', 'tick', 'error',
    }, 'Terminal runtime failure')
    _fields(terminal_sensed[0][1], {
        'sequence', 'kind', 'run_id', 'episode', 'episode_step', 'tick', 'packet',
    }, 'Terminal sensed packet')
    oracle._event_boundary(failure, last_tick, 'runtime_failure')
    error = failure.get('error')
    expected_fields = {
        'reason', 'episode', 'steps', 'type', 'message', 'policy_diagnostics',
    }
    if (type(error) is not dict or set(error) != expected_fields
            or error['reason'] != 'runtime_failure' or error['episode'] != 0
            or error['steps'] != last_tick or error['type'] != 'CueUnavailable'
            or error['policy_diagnostics'] != {}
            or manifest.get('last_outcome') != error):
        raise ValueError('Terminal sensor-only tick has an invalid runtime outcome')

    tail_row = {
        'episode': 0, 'tick': last_tick,
        'pose': projection[-1]['next_pose'],
        'next_pose': projection[-1]['next_pose'],
    }
    packets, _ = oracle._recorded_packets(
        case, events, [tail_row], 'episode-0',
        event_tick=schedule['event_tick'],
        gate_result=data['manifest']['world_state']['gate_result'])
    bridges = [event for event in events[:terminal_sensed[0][0]]
               if event.get('kind') == 'memory_decision'
               and type(event.get('detail')) is dict
               and event['detail'].get('kind') == 'memory_bridge']
    if not bridges:
        raise ValueError('Terminal CueUnavailable lacks its active bridge target')
    bridge = bridges[-1]
    oracle._event_boundary(bridge, last_row, 'terminal predecessor bridge')
    detail = bridge['detail']
    _fields(detail, {'kind', 'tick', 'landmark_id', 'bearing', 'phase'},
            'Terminal predecessor bridge')
    target = detail['landmark_id']
    visible = {landmark['id'] for landmark in packets[0]['landmarks']}
    if (detail['tick'] != last_row or target not in case['landmarks']
            or target in visible
            or error['message'] != 'selected_waypoint_unavailable: ' + target):
        raise ValueError('Terminal CueUnavailable differs from reconstructed geometry')


def _support_and_oracle(data, report, case, operation, condition,
                        source_run_id, source_snapshot_sha256, projection,
                        terminal_state, deadline):
    events = data['events']
    run = data['run']
    oracle._events(copy.deepcopy(events), data['manifest']['run_id'],
                   f'{operation} raw events')
    if operation == 'source':
        registered = [event for event in events
                      if event.get('kind') == 'snapshot_registered']
        if (len(registered) != 1 or registered[0].get('initial') is not True
                or registered[0].get('filename') != 'initial.snp'):
            raise ValueError('Source requires one registered initial snapshot')
        snapshot_path = run / 'snapshots/initial.snp'
        snapshot_sha256 = _hash_file(
            snapshot_path, deadline,
            RAW_LIMITS['source']['snapshot_max_bytes'])[0]['sha256']
        if (registered[0].get('sha256') != snapshot_sha256
                or report['snapshot_sha256'] != snapshot_sha256):
            raise ValueError('Source snapshot bytes differ from their registration')
        try:
            snapshot = snapshots.read_snapshot(snapshot_path)
        except (OSError, TypeError, ValueError) as error:
            raise ValueError('Source snapshot is invalid') from error
        application = snapshot.get('application') if type(snapshot) is dict else None
        _prefix(application, run / 'recording/events.jsonl')
        parsed, _, _, boundary = _source_application(
            application, case, data['manifest']['run_id'], report)
        packets, observations = oracle._source_evidence(
            case, parsed, events, copy.deepcopy(projection))
        result = {
            'status': 'source-boundary-pass', 'pair_admission': False,
            'events_sha256': memory.sha256(events),
            'rows_sha256': memory.sha256(projection),
            'schedule_sha256': None,
            'source_application_sha256': memory.sha256(application),
        }
        if not packets or not observations:
            raise ValueError('Source oracle projection is empty')
        return result

    if any(event.get('kind') == 'snapshot_registered' for event in events):
        raise ValueError('Condition raw run cannot register a local snapshot')
    restored = [event for event in events if event.get('kind') == 'application_restored']
    configured = [event for event in events
                  if event.get('kind') == 'memory_selector_configured']
    if (len(restored) != 1 or restored[0].get('parent_run_id') != source_run_id
            or restored[0].get('parent_event_prefix')
            != data['manifest'].get('parent_event_prefix')
            or len(configured) != 1
            or type(configured[0].get('selector')) is not dict
            or configured[0]['selector'].get('condition') != condition):
        raise ValueError('Condition restore or selector identity differs')
    boundary = projection[0]['tick']
    _, schedule = oracle._schedule(
        case, events, boundary, report['world_state'],
        report['world_state']['acquired_state_sha256'])
    _condition_terminal(data, case, projection, terminal_state, schedule)
    return {
        'status': 'condition-local-pass', 'pair_admission': False,
        'events_sha256': memory.sha256(events),
        'rows_sha256': memory.sha256(projection),
        'schedule_sha256': memory.sha256(schedule),
        'source_application_sha256': None,
    }


def _audit_candidate(run_path, *, run_id, case_id, operation, condition,
                     source_run_id, source_snapshot_sha256,
                     source_identity_sha256, deadline):
    _deadline(deadline)
    run_id = _run_id(run_id)
    memory._id(case_id)
    _digest(source_identity_sha256, 'owner source identity')
    if operation not in ('source', 'condition'):
        raise ValueError('Unknown raw-audit operation')
    if operation == 'source':
        if (condition is not None or source_run_id is not None
                or source_snapshot_sha256 is not None):
            raise ValueError('Source raw audit cannot carry condition lineage')
    else:
        if condition not in PROTOCOL['analysis_contract']['conditions']:
            raise ValueError('Unknown raw-audit condition')
        source_run_id = _run_id(source_run_id)
        if source_run_id == run_id:
            raise ValueError('Condition cannot name itself as its source')
        _digest(source_snapshot_sha256, 'source snapshot')
    run = artifacts._safe_path(run_path)
    if not run.is_dir() or run.name != run_id:
        raise ValueError('Raw run path and identity differ')
    source_identity = canonical_source_identity(source_identity_sha256)
    before = _inventory(run, operation, deadline)
    _preflight_limits(run, operation, before)
    descriptor = {'run_id': run_id, 'run': run}
    data = admission._read_run(descriptor, deadline)
    manifest = data['manifest']
    if manifest.get('status') not in ('completed', 'failed'):
        raise ValueError('Raw audit requires an already-closed terminal run')
    try:
        case = world.validate_case(copy.deepcopy(manifest.get('memory_case')))
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError('Raw manifest has an invalid family case') from error
    if case['version'] != 3 or case['case_id'] != case_id:
        raise ValueError('Raw manifest belongs to another family case')
    admission._manifest(
        data, case, PROTOCOL_SHA256, source_identity_sha256,
        operation=operation, condition=condition,
        source_snapshot_sha256=source_snapshot_sha256)
    if any(event.get('kind') in FORBIDDEN_EVENTS for event in data['events']):
        raise ValueError('Raw run contains a replacement, replay, or eye-mask event')
    if any((event.get('run_id') != run_id)
           for event in data['events'] if event.get('kind') != 'chunk') \
            or any(event.get('run_id') not in (None, run_id)
                   for event in data['events'] if event.get('kind') == 'chunk'):
        raise ValueError('Raw event belongs to another run')
    chunks = [event for event in data['events'] if event.get('kind') == 'chunk']
    expected_files = {
        'recording/manifest.json', 'recording/events.jsonl', 'worker-report.json',
        *(f"recording/{event['path']}" for event in chunks),
        *({'snapshots/initial.snp'} if operation == 'source' else set()),
    }
    if {row['path'] for row in before} != expected_files:
        raise ValueError('Raw inventory differs from its exact event/support tree')
    report_payload = artifacts._read(run / 'worker-report.json', admission.MAX_REPORT_BYTES)
    report = artifacts._json(report_payload)
    _fields(report, admission.REPORT_FIELDS, 'Raw worker report')
    if report_payload != memory.canonical_bytes(report):
        raise ValueError('Raw worker report must be canonical JSON')
    state, terminal_state = _terminal(
        data, report, case, operation, condition, source_run_id,
        source_snapshot_sha256)
    projection, camera_sequence_sha256, row_sequence_sha256 = _audit_rows(
        data['rows'], operation)
    if (projection[-1]['tick'] != report['total_ticks'] - 1
            or state['last_tick'] not in (
                projection[-1]['tick'], projection[-1]['tick'] + 1)):
        raise ValueError('Raw row interval differs from its terminal cursor')
    calls = _policy_calls(data['events'])
    admission._policy_bindings(data)
    policy_result = {
        'status': 'exhaustive-pass', 'call_count': len(calls),
        'bindings_sha256': memory.sha256([{
            key: event[key] for key in (
                'tick', 'observation_sha256', 'cameras_sha256', 'result_sha256')
        } for event in calls]),
    }
    oracle_result = _support_and_oracle(
        data, report, case, operation, condition, source_run_id,
        source_snapshot_sha256, projection, terminal_state, deadline)
    inventory = _inventory_value(before)
    by_path = {row['path']: row for row in before}
    limits = RAW_LIMITS[operation]
    validate_raw_limits(
        operation, row_count=len(data['rows']), event_count=len(data['events']),
        chunk_count=len(chunks),
        event_bytes=by_path['recording/events.jsonl']['size_bytes'],
        recording_bytes=inventory['recording_bytes'],
        report_bytes=by_path['worker-report.json']['size_bytes'],
        snapshot_bytes=(by_path['snapshots/initial.snp']['size_bytes']
                        if operation == 'source' else 0),
        file_count=inventory['file_count'])
    if len(data['rows']) > limits['max_rows']:
        raise ValueError('Raw row count exceeds its operation bound')
    after = _inventory(run, operation, deadline)
    if after != before:
        raise RuntimeError('Raw tree changed during exhaustive audit')
    receipt = {
        'schema': 'memory-family-raw-audit-v4',
        'protocol_sha256': PROTOCOL_SHA256,
        'run_id': run_id, 'case_id': case_id,
        'operation': operation, 'condition': condition,
        'row_count': len(data['rows']), 'chunk_count': len(chunks),
        'event_count': len(data['events']),
        'camera_sequence_sha256': camera_sequence_sha256,
        'row_sequence_sha256': row_sequence_sha256,
        'raw_inventory': inventory,
        'terminal_state': terminal_state,
        'policy_result': policy_result, 'oracle_result': oracle_result,
        'source_identity': source_identity,
        'claims': copy.deepcopy(PROTOCOL['claims']),
    }
    _fields(receipt, PROTOCOL['schemas']['raw_audit']['exact_keys'],
            'Raw-audit receipt')
    _validate_receipt_shape(receipt)
    return receipt


def _validate_receipt_shape(receipt):
    schemas = RAW_CONTRACT['nested_schemas']
    _fields(receipt, PROTOCOL['schemas']['raw_audit']['exact_keys'],
            'Raw-audit receipt')
    for name in ('raw_inventory', 'source_identity', 'terminal_state',
                 'policy_result', 'oracle_result'):
        _fields(receipt[name], schemas[name]['exact_keys'], name)
    for group, names in (
        (receipt, ('row_count', 'chunk_count', 'event_count')),
        (receipt['raw_inventory'], ('file_count', 'recording_bytes',
                                    'support_bytes', 'total_bytes')),
        (receipt['terminal_state'], ('total_ticks', 'last_tick')),
        (receipt['policy_result'], ('call_count',)),
    ):
        if any(type(group[name]) is not int or group[name] < 0 for name in names):
            raise ValueError('Raw-audit counts and ticks must be nonnegative integers')
    files = receipt['raw_inventory']['files']
    if type(files) is not list:
        raise ValueError('Raw inventory files must be a list')
    for row in files:
        _fields(row, schemas['file']['exact_keys'], 'Raw inventory file')
        compact._relative(row['path'], 'raw inventory path')
        if type(row['size_bytes']) is not int or row['size_bytes'] < 0:
            raise ValueError('Invalid raw inventory file size')
        _digest(row['sha256'], 'raw inventory file')
    for name in ('camera_sequence_sha256', 'row_sequence_sha256'):
        _digest(receipt[name], name)
    if (receipt['schema'] != 'memory-family-raw-audit-v4'
            or receipt['protocol_sha256'] != PROTOCOL_SHA256
            or receipt['claims'] != PROTOCOL['claims']):
        raise ValueError('Raw-audit receipt contract differs')


def _paths(run_path, receipt_root, run_id, *, published):
    run = artifacts._safe_path(run_path)
    root = artifacts._safe_path(receipt_root)
    if not run.is_dir() or not root.is_dir():
        raise ValueError('Raw run and receipt root must be existing directories')
    if (root == run or root.is_relative_to(run) or run.is_relative_to(root)):
        raise ValueError('Receipt root cannot overlap the immutable raw run')
    target = root / f'{run_id}{RECEIPT_SUFFIX}'
    if published:
        if not target.is_file() or target.is_symlink():
            raise ValueError('Raw-audit receipt is missing or not regular')
    elif target.exists() or target.is_symlink():
        raise FileExistsError('Raw-audit receipt already exists')
    return run, root, target


def _inode(path):
    value = path.lstat()
    if not stat.S_ISREG(value.st_mode):
        raise RuntimeError('Raw-audit publication is not a regular file')
    return value.st_dev, value.st_ino


def _fsync_directory(directory):
    descriptor = os.open(directory, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rollback(target, linked_inode):
    if _inode(target) != linked_inode:
        raise RuntimeError('Raw-audit publication inode changed before rollback')
    target.unlink()
    _fsync_directory(target.parent)


def audit_raw_run(run_path, receipt_root, *, run_id, case_id, operation,
                  condition, source_run_id, source_snapshot_sha256,
                  source_identity_sha256, deadline):
    """Audit one closed run and exclusively publish its immutable receipt."""
    _public_deadline(deadline)
    run_id = _run_id(run_id)
    run, root, target = _paths(
        run_path, receipt_root, run_id, published=False)
    values = dict(
        run_id=run_id, case_id=case_id, operation=operation,
        condition=condition, source_run_id=source_run_id,
        source_snapshot_sha256=source_snapshot_sha256,
        source_identity_sha256=source_identity_sha256, deadline=deadline)
    receipt = _audit_candidate(run, **values)
    payload = memory.canonical_bytes(receipt)
    if len(payload) > RAW_CONTRACT['receipt_max_bytes']:
        raise ValueError('Raw-audit receipt exceeds its frozen limit')
    payload_sha256 = hashlib.sha256(payload).hexdigest()
    temporary = None
    linked = False
    linked_inode = None
    try:
        with tempfile.NamedTemporaryFile(
                mode='wb', dir=root, prefix=f'.{target.name}.',
                suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        _deadline(deadline)
        os.link(temporary, target)
        linked = True
        linked_inode = _inode(temporary)
        if _inode(target) != linked_inode:
            raise RuntimeError('Exclusive raw-audit link changed before validation')
        temporary.unlink()
        temporary = None

        current = _audit_candidate(run, **values)
        if memory.canonical_bytes(current) != payload:
            raise RuntimeError('Raw-audit inputs changed after exclusive link')
        descriptor, _ = _hash_file(
            target, deadline, RAW_CONTRACT['receipt_max_bytes'])
        if (descriptor['size_bytes'] != len(payload)
                or descriptor['sha256'] != payload_sha256
                or _inode(target) != linked_inode):
            raise RuntimeError('Linked raw-audit receipt changed before commit')
        _deadline(deadline)
        _fsync_directory(root)
        _deadline(deadline)
    except BaseException as error:
        if linked:
            try:
                _rollback(target, linked_inode)
            except BaseException as rollback_error:
                raise PublicationIndeterminate(
                    'Raw-audit rollback failed; publication is indeterminate') \
                    from rollback_error
        raise error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return {'path': str(target), 'bytes': len(payload),
            'sha256': payload_sha256, 'receipt': copy.deepcopy(receipt)}


def validate_raw_receipt(run_path, receipt_root, *, run_id, case_id, operation,
                         condition, source_run_id, source_snapshot_sha256,
                         source_identity_sha256, deadline):
    """Read and recompute one published receipt; write nothing."""
    _public_deadline(deadline)
    run_id = _run_id(run_id)
    run, _, target = _paths(run_path, receipt_root, run_id, published=True)
    payload = artifacts._read(target, RAW_CONTRACT['receipt_max_bytes'])
    receipt = artifacts._json(payload)
    if payload != memory.canonical_bytes(receipt):
        raise ValueError('Raw-audit receipt is not canonical JSON')
    _validate_receipt_shape(receipt)
    expected = _audit_candidate(
        run, run_id=run_id, case_id=case_id, operation=operation,
        condition=condition, source_run_id=source_run_id,
        source_snapshot_sha256=source_snapshot_sha256,
        source_identity_sha256=source_identity_sha256, deadline=deadline)
    if memory.canonical_bytes(expected) != payload:
        raise ValueError('Raw-audit receipt differs from current immutable inputs')
    return copy.deepcopy(receipt)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--receipt-root', required=True, type=Path)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--case-id', required=True)
    parser.add_argument('--operation', required=True, choices=('source', 'condition'))
    parser.add_argument('--condition')
    parser.add_argument('--source-run-id')
    parser.add_argument('--source-snapshot-sha256')
    parser.add_argument('--source-identity-sha256', required=True)
    parser.add_argument('--deadline-seconds', required=True, type=float)
    args = parser.parse_args(argv)
    result = audit_raw_run(
        args.run, args.receipt_root, run_id=args.run_id,
        case_id=args.case_id, operation=args.operation,
        condition=args.condition, source_run_id=args.source_run_id,
        source_snapshot_sha256=args.source_snapshot_sha256,
        source_identity_sha256=args.source_identity_sha256,
        deadline=deadline_from_seconds(args.deadline_seconds))
    print(memory.canonical_bytes(result).decode('utf-8'))


if __name__ == '__main__':
    main()
