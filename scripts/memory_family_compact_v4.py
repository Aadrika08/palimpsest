"""Pure family-v3 compact schema, synthetic converter, and strict reader.

This module publishes nothing and never imports the Engine, model, or simulator.
The converter accepts already-decoded synthetic legacy rows only; raw admission,
producer close, pruning, and allocation remain separate future gates.
"""
from __future__ import annotations

import copy
import hashlib
import io
from pathlib import Path, PurePosixPath
import uuid
import zipfile

from palimpsest import artifacts, memory, snapshots


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / 'docs/plans/memory-family-compact-evidence-v4-protocol.json'
MiB = 1024**2
CHUNK_ROWS = 32
CAMERAS = ('cam_left', 'cam_right', 'raw_cam_left', 'raw_cam_right')
RETAINED = (
    'encoded_input', 'sensors', 'action', 'control', 'pose', 'next_pose',
    'reward', 'simulation_time', 'raw_output', 'eyes', 'revision',
)
DIGEST_FIELDS = tuple(f'{name}_sha256' for name in CAMERAS) + ('row_digest',)
ROW_FIELDS = (
    ('encoded_input', '<f4', (4813,), 19_252),
    ('sensors', '<f4', (4,), 16),
    ('action', '<f4', (2,), 8),
    ('control', '<f8', (2,), 16),
    ('pose', '<f8', (3,), 24),
    ('next_pose', '<f8', (3,), 24),
    ('reward', '<f8', (), 8),
    ('simulation_time', '<f8', (), 8),
    ('raw_output', '<f4', (2,), 8),
    ('eyes', '|b1', (2,), 2),
    ('revision', '<i8', (), 8),
    ('cam_left_sha256', '|u1', (32,), 32),
    ('cam_right_sha256', '|u1', (32,), 32),
    ('raw_cam_left_sha256', '|u1', (32,), 32),
    ('raw_cam_right_sha256', '|u1', (32,), 32),
    ('row_digest', '|u1', (32,), 32),
)
RAW_FIELDS = {'episode', 'tick', *RETAINED, *CAMERAS,
              'latency', 'step_latency', 'population_stats'}
DESCRIPTOR_FIELDS = {'path', 'size_bytes', 'sha256'}
SNAPSHOT_FIELDS = {
    'kind', 'source_run_id', 'source_receipt_sha256',
    'path', 'size_bytes', 'sha256',
}
MANIFEST_FIELDS = {
    'schema', 'recording_format', 'protocol_sha256', 'run_id', 'case_id',
    'operation', 'condition', 'row_count', 'chunk_count', 'event_count',
    'first_tick', 'last_tick', 'legacy_manifest', 'legacy_events',
    'chunk_index', 'audit_frames', 'audit_schedule',
    'snapshot_event_prefix', 'snapshot_reference',
    'non_chunk_sequences_sha256', 'legacy_chunks_sha256',
    'camera_sequence_sha256', 'row_sequence_sha256', 'trace_digest', 'claims',
}
INDEX_FIELDS = {'schema', 'chunks'}
INDEX_ENTRY_FIELDS = {
    'index', 'path', 'sha256', 'episode', 'start', 'count', 'arrays',
    'legacy_sequence', 'legacy_path', 'legacy_sha256',
}
FRAME_FIELDS = {
    'tick': ('<i8', ()),
    'raw_cam_left': ('|u1', (128, 128, 3)),
    'raw_cam_right': ('|u1', (128, 128, 3)),
}


def _fields(value, expected, label):
    if type(value) is not dict or set(value) != set(expected):
        raise ValueError(f'{label} has missing or unknown fields')


def _digest(value, label='SHA-256'):
    if (type(value) is not str or len(value) != 64
            or any(character not in '0123456789abcdef' for character in value)):
        raise ValueError(f'Invalid {label}')


def _run_id(value):
    if type(value) is not str:
        raise ValueError('Invalid run ID')
    try:
        parsed = uuid.UUID(value)
    except ValueError as error:
        raise ValueError('Invalid run ID') from error
    if value not in (parsed.hex, str(parsed)):
        raise ValueError('Run ID is not canonical')


def _relative(value, label):
    if type(value) is not str or not value or '\\' in value:
        raise ValueError(f'Invalid relative {label}')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or path.as_posix() != value:
        raise ValueError(f'Invalid relative {label}')
    return value


def _descriptor(path, payload):
    if type(payload) is not bytes:
        raise TypeError('Compact payloads must be bytes')
    return {
        'path': path,
        'size_bytes': len(payload),
        'sha256': hashlib.sha256(payload).hexdigest(),
    }


def _check_descriptor(value, path, payload):
    _fields(value, DESCRIPTOR_FIELDS, 'Payload descriptor')
    if value != _descriptor(path, payload):
        raise ValueError('Compact payload descriptor differs')


def _canonical(payload, label):
    if type(payload) is not bytes:
        raise TypeError(f'{label} must be bytes')
    value = artifacts._json(payload)
    if memory.canonical_bytes(value) != payload:
        raise ValueError(f'{label} is not canonical JSON')
    return value


def _array(value, dtype, shape, label):
    import numpy as np

    array = np.asarray(value)
    if (array.dtype.str != dtype or array.shape != shape
            or array.dtype.kind in 'fc' and not np.isfinite(array).all()):
        raise ValueError(f'Invalid compact {label}')
    return array


def _npz(values):
    import numpy as np

    with io.BytesIO() as stream:
        np.savez(stream, **values)
        return stream.getvalue()


def _read_npz(payload, schema, count, label):
    import numpy as np

    if type(payload) is not bytes:
        raise TypeError(f'{label} must be bytes')
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            expected = {f'{name}.npy' for name in schema}
            if (len(members) != len(expected)
                    or {member.filename for member in members} != expected
                    or any(member.compress_type != zipfile.ZIP_STORED
                           for member in members)
                    or sum(member.file_size for member in members) > 128 * MiB):
                raise ValueError(f'Invalid {label} archive members')
        with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
            if set(archive.files) != set(schema) or len(archive.files) != len(schema):
                raise ValueError(f'Invalid {label} arrays')
            result = {}
            for name, (dtype, shape) in schema.items():
                array = archive[name]
                expected_shape = (count, *shape)
                if (array.dtype.str != dtype or array.shape != expected_shape
                        or array.dtype.kind in 'fc' and not np.isfinite(array).all()):
                    raise ValueError(f'Invalid {label} array {name}')
                result[name] = array.copy()
            return result
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        if isinstance(error, ValueError) and str(error).startswith('Invalid '):
            raise
        raise ValueError(f'Invalid {label} archive') from error


def validate_protocol(value):
    """Accept only the byte-for-byte canonical protocol loaded by this module."""
    if type(value) is not dict or memory.canonical_bytes(value) != PROTOCOL_BYTES:
        raise ValueError('Compact protocol differs from the frozen contract')
    if (value.get('schema') != 'memory-family-compact-protocol-v4'
            or value.get('recording_format') != 'palimpsest-family-compact-v1'
            or value.get('row', {}).get('bytes_per_tick') != 19_534
            or value.get('claims', {}).get('qualification_claims') != []
            or any(item is not False for key, item in value['claims'].items()
                   if key != 'qualification_claims')):
        raise ValueError('Invalid compact protocol semantics')
    expected_fields = [
        {'name': name, 'dtype': dtype, 'shape': list(shape), 'bytes': size}
        for name, dtype, shape, size in ROW_FIELDS
    ]
    if value['row']['fields'] != expected_fields:
        raise ValueError('Compact row schema differs')
    return copy.deepcopy(value)


def behavior_source_identities(repo_root):
    """Rehash only protocol-listed local sources; import or execute none."""
    root = artifacts._safe_path(repo_root)
    result = []
    for expected in PROTOCOL['behavior_sources']:
        _fields(expected, {'id', 'path', 'size_bytes', 'sha256'},
                'Behavior source identity')
        relative = _relative(expected['path'], 'behavior source path')
        path = artifacts._safe_path(root / relative)
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('Behavior source is missing or outside the repository')
        payload = artifacts._read(path, 2 * MiB)
        actual = {'id': expected['id'], **_descriptor(relative, payload)}
        if actual != expected:
            raise ValueError(f"Behavior source differs: {expected['id']}")
        result.append(actual)
    return result


def audit_ticks(ticks, *, event_tick=None, decision_tick=None):
    """Return the frozen ordered audit union for one contiguous interval."""
    values = list(ticks)
    if (not values or any(type(value) is not int or value < 0 for value in values)
            or values != list(range(values[0], values[0] + len(values)))):
        raise ValueError('Audit ticks must be one nonempty contiguous interval')
    for value in (event_tick, decision_tick):
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError('Scheduled audit ticks must be nonnegative integers')
    selected = {values[(point * (len(values) - 1)) // 5] for point in range(6)}
    present = set(values)
    for scheduled in (event_tick, decision_tick):
        if scheduled is not None:
            selected.update(candidate for candidate in range(scheduled - 1, scheduled + 2)
                            if candidate in present)
    selected.update(values[-2:])
    result = tuple(value for value in values if value in selected)
    if len(result) > PROTOCOL['audit_ticks']['maximum']:
        raise ValueError('Audit tick selection exceeds the frozen limit')
    return result


def _legacy_manifest(payload, run_id):
    if type(payload) is not bytes or len(payload) > MiB:
        raise ValueError('Invalid legacy manifest bytes')
    value = artifacts._json(payload)
    if (type(value) is not dict or value.get('run_id') != run_id
            or value.get('recording_format') != 'palimpsest-npz-v1'
            or value.get('status') != 'completed'):
        raise ValueError('Legacy manifest identity or terminal state differs')
    return value


def _legacy_events(payload, operation):
    cap = PROTOCOL['recordings'][operation]['legacy_events_max_bytes']
    if (type(payload) is not bytes or not payload or len(payload) > cap
            or not payload.endswith(b'\n')):
        raise ValueError('Invalid legacy event bytes')
    result = []
    for sequence, line in enumerate(payload.splitlines()):
        if not line or len(line) > MiB:
            raise ValueError('Invalid legacy event line')
        event = artifacts._json(line)
        if (type(event) is not dict or event.get('sequence') != sequence
                or type(event.get('kind')) is not str or not event['kind']):
            raise ValueError('Invalid legacy event sequence')
        if event['kind'] == 'chunk':
            _fields(event, {
                'sequence', 'kind', 'path', 'sha256', 'episode', 'start',
                'count', 'arrays',
            }, 'Legacy chunk event')
            _relative(event['path'], 'legacy chunk path')
            _digest(event['sha256'], 'legacy chunk SHA-256')
            if (event['episode'] != 0 or type(event['start']) is not int
                    or event['start'] < 0 or type(event['count']) is not int
                    or not 1 <= event['count'] <= CHUNK_ROWS
                    or type(event['arrays']) is not dict or not event['arrays']):
                raise ValueError('Invalid legacy chunk mapping')
        result.append(event)
    return result


def _snapshot(value, operation, run_id):
    _fields(value, SNAPSHOT_FIELDS, 'Snapshot reference')
    expected_kind = 'source' if operation == 'source' else 'shared-source'
    if value['kind'] != expected_kind:
        raise ValueError('Snapshot reference kind differs from operation')
    _run_id(value['source_run_id'])
    if operation == 'source':
        if value['source_run_id'] != run_id or value['source_receipt_sha256'] is not None:
            raise ValueError('Source snapshot reference is inconsistent')
    else:
        _digest(value['source_receipt_sha256'], 'source receipt SHA-256')
        if value['source_run_id'] == run_id:
            raise ValueError('Condition snapshot must reference the source run')
    _relative(value['path'], 'snapshot path')
    if type(value['size_bytes']) is not int or value['size_bytes'] <= 0:
        raise ValueError('Invalid snapshot size')
    _digest(value['sha256'], 'snapshot SHA-256')
    return copy.deepcopy(value)


def _project_rows(rows, operation):
    import numpy as np

    if type(rows) is not list or not 1 <= len(rows) <= \
            PROTOCOL['recordings'][operation]['max_rows']:
        raise ValueError('Invalid compact row count')
    result = []
    start = None
    for offset, row in enumerate(rows):
        _fields(row, RAW_FIELDS, 'Synthetic legacy row')
        if row['episode'] != 0 or type(row['tick']) is not int or row['tick'] < 0:
            raise ValueError('Compact rows require episode zero and nonnegative ticks')
        if start is None:
            start = row['tick']
        if row['tick'] != start + offset:
            raise ValueError('Compact ticks must be contiguous')
        compact = {}
        for name, dtype, shape, _ in ROW_FIELDS[:len(RETAINED)]:
            compact[name] = _array(row[name], dtype, shape, name).copy()
        for name in CAMERAS:
            camera = _array(row[name], '|u1', (128, 128, 3), name)
            compact[f'{name}_sha256'] = np.frombuffer(
                bytes.fromhex(snapshots.state_digest(camera)), np.uint8).copy()
        if (not compact['eyes'].all()
                or not np.array_equal(row['cam_left'], row['raw_cam_left'])
                or not np.array_equal(row['cam_right'], row['raw_cam_right'])):
            raise ValueError('Family compact conversion requires unmasked equal eyes')
        for timing in ('latency', 'step_latency'):
            _array(row[timing], '<f8', (), timing)
        population = np.asarray(row['population_stats'])
        if (population.dtype.str != '<f8' or population.ndim != 2
                or population.shape[1:] != (4,) or not np.isfinite(population).all()):
            raise ValueError('Invalid population statistics')
        legacy_value = {key: value for key, value in row.items()
                        if key not in ('latency', 'step_latency')}
        compact['row_digest'] = np.frombuffer(
            bytes.fromhex(snapshots.state_digest(legacy_value)), np.uint8).copy()
        result.append({'episode': 0, 'tick': row['tick'], **compact})
    return result


def _sequence_hash(rows, names):
    digest = hashlib.sha256()
    for row in rows:
        for name in names:
            digest.update(row[name].tobytes())
    return digest.hexdigest()


def _trace_digest(rows):
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row['row_digest'].tobytes().hex().encode('ascii'))
    return digest.hexdigest()


def _row_schema():
    return {name: {'dtype': dtype, 'shape': list(shape)}
            for name, dtype, shape, _ in ROW_FIELDS}


def _prefix(value, legacy_events):
    if value is None:
        return None
    _fields(value, {'size_bytes', 'sha256', 'event_count'},
            'Snapshot event prefix')
    size = value['size_bytes']
    if type(size) is not int or not 1 <= size <= len(legacy_events):
        raise ValueError('Invalid snapshot event-prefix size')
    payload = legacy_events[:size]
    if (not payload.endswith(b'\n')
            or payload.count(b'\n') != value['event_count']
            or hashlib.sha256(payload).hexdigest() != value['sha256']):
        raise ValueError('Snapshot event prefix differs')
    return copy.deepcopy(value)


def convert_synthetic(*, run_id, case_id, operation, condition, rows,
                      legacy_manifest_bytes, legacy_events_bytes,
                      snapshot_reference, event_tick=None, decision_tick=None,
                      snapshot_event_prefix=None):
    """Build an in-memory compact candidate from synthetic decoded legacy rows."""
    import numpy as np

    _run_id(run_id)
    memory._id(case_id)
    if operation not in ('source', 'condition'):
        raise ValueError('Unknown compact operation')
    conditions = PROTOCOL['analysis_contract']['conditions']
    if ((operation == 'source' and condition is not None)
            or (operation == 'condition' and condition not in conditions)):
        raise ValueError('Compact condition differs from operation')
    if operation == 'source' and (event_tick is not None or decision_tick is not None):
        raise ValueError('Source conversion has no continuation schedule')
    if operation == 'condition' and decision_tick is None:
        raise ValueError('Condition conversion requires a decision tick')
    compact_rows = _project_rows(rows, operation)
    legacy_manifest = _legacy_manifest(legacy_manifest_bytes, run_id)
    events = _legacy_events(legacy_events_bytes, operation)
    chunks = [event for event in events if event['kind'] == 'chunk']
    if (legacy_manifest.get('recorded_ticks') != len(rows)
            or legacy_manifest.get('recorded_chunks') != len(chunks)
            or legacy_manifest.get('recorded_events') != len(events)):
        raise ValueError('Legacy terminal counts differ')
    expected_chunks = (len(rows) + CHUNK_ROWS - 1) // CHUNK_ROWS
    if len(chunks) != expected_chunks:
        raise ValueError('Legacy chunk count differs from compact partition')
    snapshot_reference = _snapshot(snapshot_reference, operation, run_id)
    snapshot_event_prefix = _prefix(snapshot_event_prefix, legacy_events_bytes)
    if (operation == 'source') != (snapshot_event_prefix is not None):
        raise ValueError('Only a source binds its snapshot event prefix')

    schema = _row_schema()
    payloads = {
        'legacy-manifest.json': legacy_manifest_bytes,
        'legacy-events.jsonl': legacy_events_bytes,
    }
    index_rows = []
    cursor = 0
    for index, legacy in enumerate(chunks):
        count = min(CHUNK_ROWS, len(rows) - cursor)
        start = compact_rows[cursor]['tick']
        if (legacy['episode'], legacy['start'], legacy['count']) != (0, start, count):
            raise ValueError('Legacy chunk range differs from compact partition')
        values = {name: np.stack([row[name] for row in compact_rows[cursor:cursor + count]])
                  for name in schema}
        path = f'chunks/{index:06d}.npz'
        payload = _npz(values)
        payloads[path] = payload
        index_rows.append({
            'index': index, 'path': path,
            'sha256': hashlib.sha256(payload).hexdigest(),
            'episode': 0, 'start': start, 'count': count, 'arrays': schema,
            'legacy_sequence': legacy['sequence'],
            'legacy_path': legacy['path'], 'legacy_sha256': legacy['sha256'],
        })
        cursor += count
    index = {'schema': 'memory-family-compact-chunk-index-v1',
             'chunks': index_rows}
    payloads['chunk-index.json'] = memory.canonical_bytes(index)

    selected = audit_ticks(
        [row['tick'] for row in rows], event_tick=event_tick,
        decision_tick=decision_tick,
    )
    by_tick = {row['tick']: row for row in rows}
    frames = {
        'tick': np.asarray(selected, np.int64),
        'raw_cam_left': np.stack([by_tick[tick]['raw_cam_left'] for tick in selected]),
        'raw_cam_right': np.stack([by_tick[tick]['raw_cam_right'] for tick in selected]),
    }
    payloads['audit-frames.npz'] = _npz(frames)

    non_chunks = [event['sequence'] for event in events if event['kind'] != 'chunk']
    legacy_tuples = [[event[key] for key in (
        'sequence', 'path', 'sha256', 'episode', 'start', 'count', 'arrays')]
        for event in chunks]
    manifest = {
        'schema': 'memory-family-compact-manifest-v1',
        'recording_format': PROTOCOL['recording_format'],
        'protocol_sha256': PROTOCOL_SHA256,
        'run_id': run_id, 'case_id': case_id,
        'operation': operation, 'condition': condition,
        'row_count': len(rows), 'chunk_count': len(chunks),
        'event_count': len(events), 'first_tick': rows[0]['tick'],
        'last_tick': rows[-1]['tick'],
        'legacy_manifest': _descriptor('legacy-manifest.json', legacy_manifest_bytes),
        'legacy_events': _descriptor('legacy-events.jsonl', legacy_events_bytes),
        'chunk_index': _descriptor('chunk-index.json', payloads['chunk-index.json']),
        'audit_frames': _descriptor('audit-frames.npz', payloads['audit-frames.npz']),
        'audit_schedule': {'event_tick': event_tick, 'decision_tick': decision_tick},
        'snapshot_event_prefix': snapshot_event_prefix,
        'snapshot_reference': snapshot_reference,
        'non_chunk_sequences_sha256': memory.sha256(non_chunks),
        'legacy_chunks_sha256': memory.sha256(legacy_tuples),
        'camera_sequence_sha256': _sequence_hash(compact_rows, DIGEST_FIELDS[:-1]),
        'row_sequence_sha256': _sequence_hash(compact_rows, ('row_digest',)),
        'trace_digest': _trace_digest(compact_rows),
        'claims': copy.deepcopy(PROTOCOL['claims']),
    }
    payloads['manifest.json'] = memory.canonical_bytes(manifest)
    ceiling = PROTOCOL['recordings'][operation]['ceiling_bytes']
    if sum(len(payload) for payload in payloads.values()) > ceiling:
        raise ValueError('Synthetic compact candidate exceeds recording ceiling')
    return payloads


def _read_manifest(bundle):
    required = {
        'manifest.json', 'legacy-manifest.json', 'legacy-events.jsonl',
        'chunk-index.json', 'audit-frames.npz',
    }
    if (type(bundle) is not dict or not required.issubset(bundle)
            or any(type(path) is not str or type(payload) is not bytes
                   for path, payload in bundle.items())):
        raise ValueError('Invalid compact bundle')
    manifest = _canonical(bundle['manifest.json'], 'Compact manifest')
    _fields(manifest, MANIFEST_FIELDS, 'Compact manifest')
    if (manifest['schema'] != 'memory-family-compact-manifest-v1'
            or manifest['recording_format'] != PROTOCOL['recording_format']
            or manifest['protocol_sha256'] != PROTOCOL_SHA256
            or manifest['claims'] != PROTOCOL['claims']):
        raise ValueError('Compact manifest contract differs')
    _run_id(manifest['run_id'])
    memory._id(manifest['case_id'])
    return manifest


def read_compact(bundle):
    """Exhaustively validate and decode one in-memory compact candidate."""
    import numpy as np

    manifest = _read_manifest(bundle)
    operation = manifest['operation']
    if operation not in ('source', 'condition'):
        raise ValueError('Unknown compact operation')
    if ((operation == 'source' and manifest['condition'] is not None)
            or (operation == 'condition'
                and manifest['condition'] not in PROTOCOL['analysis_contract']['conditions'])):
        raise ValueError('Compact condition differs from operation')
    for name, path in (
        ('legacy_manifest', 'legacy-manifest.json'),
        ('legacy_events', 'legacy-events.jsonl'),
        ('chunk_index', 'chunk-index.json'),
        ('audit_frames', 'audit-frames.npz'),
    ):
        _check_descriptor(manifest[name], path, bundle[path])
    legacy_manifest = _legacy_manifest(
        bundle['legacy-manifest.json'], manifest['run_id'])
    events = _legacy_events(bundle['legacy-events.jsonl'], operation)
    legacy_chunks = [event for event in events if event['kind'] == 'chunk']
    if (legacy_manifest.get('recorded_ticks') != manifest['row_count']
            or legacy_manifest.get('recorded_chunks') != manifest['chunk_count']
            or legacy_manifest.get('recorded_events') != manifest['event_count']
            or len(legacy_chunks) != manifest['chunk_count']
            or len(events) != manifest['event_count']):
        raise ValueError('Compact and legacy terminal counts differ')

    index = _canonical(bundle['chunk-index.json'], 'Compact chunk index')
    _fields(index, INDEX_FIELDS, 'Compact chunk index')
    if index['schema'] != 'memory-family-compact-chunk-index-v1' \
            or type(index['chunks']) is not list:
        raise ValueError('Invalid compact chunk index')
    expected_paths = {
        'manifest.json', 'legacy-manifest.json', 'legacy-events.jsonl',
        'chunk-index.json', 'audit-frames.npz',
        *(f'chunks/{index_:06d}.npz' for index_ in range(len(index['chunks']))),
    }
    if set(bundle) != expected_paths:
        raise ValueError('Compact bundle files differ from chunk index')
    schema = _row_schema()
    rows = []
    cursor = manifest['first_tick']
    for position, (entry, legacy) in enumerate(zip(index['chunks'], legacy_chunks)):
        _fields(entry, INDEX_ENTRY_FIELDS, 'Compact chunk entry')
        path = f'chunks/{position:06d}.npz'
        expected_count = min(CHUNK_ROWS, manifest['row_count'] - len(rows))
        if (entry['index'] != position or entry['path'] != path
                or entry['episode'] != 0 or entry['start'] != cursor
                or entry['count'] != expected_count or entry['arrays'] != schema
                or entry['legacy_sequence'] != legacy['sequence']
                or entry['legacy_path'] != legacy['path']
                or entry['legacy_sha256'] != legacy['sha256']
                or hashlib.sha256(bundle[path]).hexdigest() != entry['sha256']):
            raise ValueError('Compact chunk mapping differs')
        arrays = _read_npz(
            bundle[path],
            {name: (description['dtype'], tuple(description['shape']))
             for name, description in schema.items()},
            entry['count'], 'compact chunk',
        )
        for offset in range(entry['count']):
            rows.append({'episode': 0, 'tick': cursor + offset,
                         **{name: value[offset].copy()
                            for name, value in arrays.items()}})
        cursor += entry['count']
    if (len(rows) != manifest['row_count'] or not rows
            or rows[0]['tick'] != manifest['first_tick']
            or rows[-1]['tick'] != manifest['last_tick']):
        raise ValueError('Compact row interval differs')

    schedule = manifest['audit_schedule']
    _fields(schedule, {'event_tick', 'decision_tick'}, 'Audit schedule')
    selected = audit_ticks(
        [row['tick'] for row in rows], event_tick=schedule['event_tick'],
        decision_tick=schedule['decision_tick'],
    )
    frame_arrays = _read_npz(
        bundle['audit-frames.npz'], FRAME_FIELDS, len(selected), 'audit frame')
    if frame_arrays['tick'].tolist() != list(selected):
        raise ValueError('Audit frame ticks differ from frozen selection')
    by_tick = {row['tick']: row for row in rows}
    selected_frames = {}
    for offset, tick in enumerate(selected):
        frames = {name: frame_arrays[name][offset].copy()
                  for name in ('raw_cam_left', 'raw_cam_right')}
        row = by_tick[tick]
        for raw, effective in (
            ('raw_cam_left', 'cam_left'), ('raw_cam_right', 'cam_right')):
            digest = np.frombuffer(
                bytes.fromhex(snapshots.state_digest(frames[raw])), np.uint8)
            if (not np.array_equal(digest, row[f'{raw}_sha256'])
                    or not np.array_equal(digest, row[f'{effective}_sha256'])):
                raise ValueError('Selected audit frame digest differs')
        selected_frames[tick] = frames

    non_chunks = [event['sequence'] for event in events if event['kind'] != 'chunk']
    legacy_tuples = [[event[key] for key in (
        'sequence', 'path', 'sha256', 'episode', 'start', 'count', 'arrays')]
        for event in legacy_chunks]
    if (manifest['non_chunk_sequences_sha256'] != memory.sha256(non_chunks)
            or manifest['legacy_chunks_sha256'] != memory.sha256(legacy_tuples)
            or manifest['camera_sequence_sha256'] != _sequence_hash(rows, DIGEST_FIELDS[:-1])
            or manifest['row_sequence_sha256'] != _sequence_hash(rows, ('row_digest',))
            or manifest['trace_digest'] != _trace_digest(rows)):
        raise ValueError('Compact sequence commitment differs')
    for name in ('non_chunk_sequences_sha256', 'legacy_chunks_sha256',
                 'camera_sequence_sha256', 'row_sequence_sha256', 'trace_digest'):
        _digest(manifest[name], name)
    snapshot_reference = _snapshot(
        manifest['snapshot_reference'], operation, manifest['run_id'])
    snapshot_event_prefix = _prefix(
        manifest['snapshot_event_prefix'], bundle['legacy-events.jsonl'])
    if (operation == 'source') != (snapshot_event_prefix is not None):
        raise ValueError('Compact snapshot event prefix differs')
    ceiling = PROTOCOL['recordings'][operation]['ceiling_bytes']
    if sum(len(payload) for payload in bundle.values()) > ceiling:
        raise ValueError('Compact bundle exceeds recording ceiling')
    return {
        'manifest': copy.deepcopy(manifest),
        'legacy_manifest_bytes': bundle['legacy-manifest.json'],
        'legacy_events_bytes': bundle['legacy-events.jsonl'],
        'events': [copy.deepcopy(event) for event in events
                   if event['kind'] != 'chunk'],
        'rows': rows, 'selected_frames': selected_frames,
        'snapshot_reference': snapshot_reference,
        'trace_digest': manifest['trace_digest'],
    }


PROTOCOL_BYTES = artifacts._read(PROTOCOL_PATH, MiB)
PROTOCOL = artifacts._json(PROTOCOL_BYTES)
if memory.canonical_bytes(PROTOCOL) != PROTOCOL_BYTES:
    raise ValueError('Compact protocol must be canonical JSON')
PROTOCOL_SHA256 = hashlib.sha256(PROTOCOL_BYTES).hexdigest()
validate_protocol(PROTOCOL)
