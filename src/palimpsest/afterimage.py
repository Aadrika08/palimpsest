"""Bounded authored RGB stimulus -> recorded male response -> offline SVG.

No capture, simulator, codecs or model imports are used by the renderer.
"""
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid
import xml.etree.ElementTree as ET

from . import artifacts
from .records import RunWriter, iter_ticks

MiB = 1024**2
MAX_FRAMES = 600
MAX_INPUT_BYTES = 32 * MiB
MAX_RECORD_BYTES = 96 * MiB
MAX_RUN_BYTES = 128 * MiB
MAX_SVG_BYTES = 4 * MiB
TIMEOUT_SECONDS = 120
DT = .02
KIND = 'afterimage-v1'
LABEL = 'Authored model portrait — offline inference / recorded playback; not fly perception or biological activity.'
MAPPING = {'id': 'response-plane-v1', 'x': '360 * action[0] / 3',
           'y': '-360 * action[1] / pi', 'axis_limits': [-360, 360],
           'velocity_scale': 3., 'heading_scale': math.pi, 'line': 'chronological; no interpolation or smoothing'}
INTERFACE = {'eyes': 'same supplied RGB frame in both channels',
             'sensors': [0., 0., 1., 0.], 'sensor_order': ['contact', 'contact_angle', 'bearing_x', 'bearing_y'],
             'claim': 'authored artificial interface; no biological stereo or sensor mapping'}
SOURCE_NAMES = ('afterimage.py', 'records.py', 'artifacts.py', 'male_policy.py', 'male_model.py',
                'storage.py', 'evaluate.py', 'cli.py')


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _is_hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _text(value):
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 1024


def _spec(value):
    required = {'schema_version', 'title', 'creator', 'frame_file', 'frame_file_sha256', 'source_times_seconds', 'rights'}
    if not isinstance(value, dict) or set(value) != required or type(value['schema_version']) is not int or value['schema_version'] != 1:
        raise ValueError('unsupported stimulus manifest schema')
    name = value['frame_file']
    if (not all(_text(value[k]) for k in ('title', 'creator', 'frame_file')) or
            '/' in name or '\\' in name or Path(name).suffix != '.npy' or not _is_hash(value['frame_file_sha256'])):
        raise ValueError('stimulus requires title, creator, local NPY basename and SHA256')
    times = value['source_times_seconds']
    if (not isinstance(times, list) or not 1 <= len(times) <= MAX_FRAMES or
            any(type(t) not in (int, float) or not math.isfinite(t) or t < 0 or t > 1e12 for t in times) or
            any(b <= a for a, b in zip(times, times[1:])) or times[-1] - times[0] > 120):
        raise ValueError('source times must be finite, strictly increasing, 1–600 entries spanning at most 120 seconds')
    rights = value['rights']
    if (not isinstance(rights, dict) or set(rights) != {'basis', 'statement', 'attribution', 'authorized_processing_and_retention', 'subject_consent'} or
            rights['basis'] not in ('self_created', 'permission', 'licensed', 'public_domain') or
            not all(_text(rights[k]) for k in ('statement', 'attribution')) or
            rights['authorized_processing_and_retention'] is not True or
            rights['subject_consent'] not in ('no_identifiable_people', 'permission_confirmed')):
        raise ValueError('explicit operator rights and processing/retention declaration required')
    artifacts._no_secrets(value)
    return value


def load_stimulus(path):
    """Freeze bounded input bytes before model loading; never resize or convert."""
    import numpy as np
    path = artifacts._safe_path(path)
    payload = artifacts._read(path, MiB)
    spec = _spec(artifacts._json(payload))
    frame_path = path.parent / spec['frame_file']
    raw = artifacts._read(frame_path, MAX_INPUT_BYTES)
    if _sha(raw) != spec['frame_file_sha256']:
        raise ValueError('stimulus NPY checksum differs')
    stream = io.BytesIO(raw)
    version = np.lib.format.read_magic(stream)
    if version not in ((1, 0), (2, 0)):
        raise ValueError('stimulus requires NPY version 1 or 2')
    header = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
    shape, fortran, dtype = header(stream, max_header_size=4096)
    if (shape != (len(spec['source_times_seconds']), 128, 128, 3) or fortran or dtype != np.dtype('uint8') or
            stream.tell() + math.prod(shape) != len(raw)):
        raise ValueError('stimulus requires exact C-order uint8 T×128×128×3 bytes')
    frames = np.frombuffer(raw, dtype=np.uint8, offset=stream.tell()).reshape(shape)
    metadata = {'manifest': spec, 'manifest_sha256': _sha(payload), 'frame_file_bytes': len(raw),
                'frame_sha256': [_sha(frame.tobytes()) for frame in frames]}
    return {'frames': frames, 'metadata': metadata, 'paths': (path, frame_path),
            'fingerprints': artifacts._fingerprint((path, frame_path))}


def _source_hashes():
    return {name: _sha(artifacts._read(Path(__file__).with_name(name), MiB)) for name in SOURCE_NAMES}


def _unchanged(stimulus):
    if (artifacts._fingerprint(stimulus['paths']) != stimulus['fingerprints'] or
            _sha(artifacts._read(stimulus['paths'][0], MiB)) != stimulus['metadata']['manifest_sha256'] or
            _sha(artifacts._read(stimulus['paths'][1], MAX_INPUT_BYTES)) != stimulus['metadata']['manifest']['frame_file_sha256']):
        raise ValueError('stimulus source changed during inference')


def _response(result):
    import numpy as np
    if not isinstance(result, dict) or set(result) != {'action', 'encoded_input', 'raw_output'}:
        raise ValueError('response requires actual action, encoded input and raw readout')
    for name, size in (('action', 2), ('encoded_input', 136), ('raw_output', 2)):
        value = np.asarray(result[name])
        if value.shape != (size,) or value.dtype != np.dtype('float32') or not np.isfinite(value).all():
            raise ValueError('invalid response shape/dtype/finite values: ' + name)
    action = result['action']
    if (np.any(np.abs(action) > np.array([3., math.pi], dtype=np.float32)) or
            not np.allclose(action, np.tanh(result['raw_output']) * np.array([3., math.pi], dtype=np.float32), rtol=1e-6, atol=1e-6)):
        raise ValueError('response action differs from documented readout scaling')


def _record(stimulus, policy, destination, identity, *, storage_budget=None, evidence='actual model inference', before_finish=None):
    """Private recorder; the CLI supplies only the fixed pinned male wrapper."""
    import numpy as np
    from .male_policy import validate_identity
    destination = artifacts._safe_path(destination)
    if uuid.UUID(destination.name).hex != destination.name:
        raise ValueError('Afterimage run requires a canonical hexadecimal UUID directory')
    validate_identity(identity, identity.get('controller'))
    if evidence not in ('actual model inference', 'synthetic fixture verification'):
        raise ValueError('unknown inference evidence class')
    sources = _source_hashes()
    manifest = {'run_id': destination.name, 'kind': KIND, 'schema_version': 1, 'label': LABEL,
                'evidence': evidence, 'policy_identity': identity, 'device': 'cpu', 'seed': 0,
                'stimulus': stimulus['metadata'], 'interface': INTERFACE, 'model_dt_seconds': DT,
                'source_code_sha256': sources, 'reset': 'once at sequence start; carried across every frame',
                'timing': '20ms model index; external source timestamps and offline wall latency are separate'}
    writer = RunWriter(destination / 'recording', manifest, max_bytes=MAX_RECORD_BYTES, storage_budget=storage_budget)
    try:
        policy.reset()
        for index, frame in enumerate(stimulus['frames']):
            observation = {'cam_left': frame.copy(), 'cam_right': frame.copy(),
                           'sensors': {'collision': 0., 'collision_angle': 0., 'wind_direction': np.array([1., 0.])}}
            start = time.monotonic()
            result = policy.act(observation)
            latency = time.monotonic() - start
            _response(result)
            writer.tick(0, index, cam_left=frame, cam_right=frame,
                        sensors=np.array(INTERFACE['sensors'], dtype=np.float32), **result,
                        source_frame_index=np.array(index, dtype=np.int64),
                        source_timestamp_seconds=np.array(stimulus['metadata']['manifest']['source_times_seconds'][index], dtype=np.float64),
                        model_time_seconds=np.array((index + 1) * DT, dtype=np.float64),
                        inference_wall_seconds=np.array(latency, dtype=np.float64))
        _unchanged(stimulus)
        if _source_hashes() != sources:
            raise ValueError('inference source code changed')
        if before_finish is not None:
            before_finish()
        writer.finish({'sources_unchanged': True, 'input_frames': len(stimulus['frames'])})
    finally:
        writer.close()  # An interrupted/failed recording remains non-completed.
    return destination


def _load_recording(source):
    """Validate this non-physics schema before deriving a portrait."""
    import numpy as np
    from .male_policy import validate_identity
    source = artifacts._safe_path(source)
    manifest = artifacts._manifest(source)
    if (manifest.get('kind') != KIND or manifest.get('schema_version') != 1 or manifest.get('status') != 'completed' or
            manifest.get('sources_unchanged') is not True or manifest.get('model_dt_seconds') != DT or
            manifest.get('interface') != INTERFACE or manifest.get('label') != LABEL or
            manifest.get('device') != 'cpu' or manifest.get('seed') != 0 or
            manifest.get('evidence') not in ('actual model inference', 'synthetic fixture verification')):
        raise ValueError('completed, unchanged Afterimage recording required')
    identity = manifest.get('policy_identity')
    validate_identity(identity, identity.get('controller') if isinstance(identity, dict) else None)
    codes = manifest.get('source_code_sha256')
    if not isinstance(codes, dict) or set(codes) != set(SOURCE_NAMES) or not all(_is_hash(v) for v in codes.values()):
        raise ValueError('recording lacks source code provenance')
    stimulus = manifest.get('stimulus')
    if not isinstance(stimulus, dict) or set(stimulus) != {'manifest', 'manifest_sha256', 'frame_file_bytes', 'frame_sha256'}:
        raise ValueError('recording lacks stimulus provenance')
    spec = _spec(stimulus['manifest'])
    count = len(spec['source_times_seconds'])
    if (not _is_hash(stimulus['manifest_sha256']) or type(stimulus['frame_file_bytes']) is not int or
            not count * 128 * 128 * 3 < stimulus['frame_file_bytes'] <= MAX_INPUT_BYTES or
            not isinstance(stimulus['frame_sha256'], list) or len(stimulus['frame_sha256']) != count or
            not all(_is_hash(v) for v in stimulus['frame_sha256']) or
            manifest.get('recorded_ticks') != count or manifest.get('input_frames') != count):
        raise ValueError('recording stimulus counts or hashes differ')
    events = artifacts._events(source)
    if len(events) > 19 or any(event['kind'] != 'chunk' for event in events):
        raise ValueError('Afterimage accepts only bounded numeric chunks')
    paths = [source / 'recording/manifest.json', source / 'recording/events.jsonl']
    if manifest['evidence'] == 'actual model inference':
        receipt = source / 'supervisor.json'
        supervisor = artifacts._json(artifacts._read(receipt, MiB))
        if (not isinstance(supervisor, dict) or supervisor.get('status') != 'completed' or
                type(supervisor.get('returncode')) is not int or supervisor['returncode'] != 0 or
                supervisor.get('timeout_seconds') != TIMEOUT_SECONDS):
            raise ValueError('actual inference requires completed bounded supervisor evidence')
        paths.append(receipt)
    for index, event in enumerate(events):
        if event.get('path') != f'chunks/{index:06d}.npz':
            raise ValueError('invalid Afterimage chunk path')
        paths.append(source / 'recording' / event['path'])
    fingerprints = artifacts._fingerprint(paths)
    if sum(path.stat().st_size for path in paths) > MAX_RECORD_BYTES:
        raise ValueError('Afterimage recording exceeds byte cap')
    expected = {'cam_left': ('uint8', (128, 128, 3)), 'cam_right': ('uint8', (128, 128, 3)),
                'sensors': ('float32', (4,)), 'action': ('float32', (2,)), 'raw_output': ('float32', (2,)),
                'encoded_input': ('float32', (136,)), 'source_frame_index': ('int64', ()),
                'source_timestamp_seconds': ('float64', ()), 'model_time_seconds': ('float64', ()),
                'inference_wall_seconds': ('float64', ())}
    rows = []
    iterator = iter_ticks(source / 'recording')
    try:
        for index, row in enumerate(iterator):
            if index >= count or row['episode'] != 0 or row['tick'] != index or set(row) != {'episode', 'tick', *expected}:
                raise ValueError('recorded frame sequence differs')
            for name, (dtype, shape) in expected.items():
                value = row[name]
                if value.dtype != np.dtype(dtype) or value.shape != shape or not np.isfinite(value).all():
                    raise ValueError('invalid recorded frame field: ' + name)
            if (int(row['source_frame_index']) != index or float(row['source_timestamp_seconds']) != spec['source_times_seconds'][index] or
                    float(row['model_time_seconds']) != (index + 1) * DT or float(row['inference_wall_seconds']) < 0 or
                    not np.array_equal(row['sensors'], np.array(INTERFACE['sensors'], dtype=np.float32)) or
                    not np.array_equal(row['cam_left'], row['cam_right']) or
                    _sha(row['cam_left'].tobytes()) != stimulus['frame_sha256'][index]):
                raise ValueError('frame, source time or artificial interface alignment differs')
            _response({key: row[key] for key in ('action', 'encoded_input', 'raw_output')})
            action = row['action'].astype(float).tolist()
            rows.append({'frame': index, 'source_timestamp_seconds': float(row['source_timestamp_seconds']),
                         'frame_sha256': stimulus['frame_sha256'][index], 'model_time_seconds': float(row['model_time_seconds']),
                         'inference_wall_seconds': float(row['inference_wall_seconds']), 'action': action,
                         'raw_output': row['raw_output'].astype(float).tolist(),
                         'point': [360 * action[0] / 3, -360 * action[1] / math.pi]})
    finally:
        iterator.close()
    if len(rows) != count or artifacts._fingerprint(paths) != fingerprints:
        raise ValueError('recording count or source changed during reading')
    return manifest, rows, paths, fingerprints


def render(source, output, *, storage_budget=None):
    """Exclusive static SVG publication; no inference or source imagery embedding."""
    source, output = artifacts._safe_path(source), artifacts._safe_path(output)
    if output.suffix.lower() != '.svg' or output.is_relative_to(source) or 'recording' in output.parts:
        raise ValueError('portrait needs a new SVG outside authoritative recordings')
    manifest, rows, paths, fingerprints = _load_recording(source)
    provenance = {'kind': KIND, 'label': LABEL, 'evidence': manifest['evidence'], 'source_run_id': manifest['run_id'],
                  'recording_files_sha256': {str(path.relative_to(source)): _sha(artifacts._read(path, MAX_RECORD_BYTES)) for path in paths},
                  'policy_identity': manifest['policy_identity'], 'source_code_sha256': manifest['source_code_sha256'],
                  'stimulus': manifest['stimulus'], 'interface': INTERFACE, 'mapping': MAPPING,
                  'model_dt_seconds': DT, 'alignment': rows,
                  'rights_limit': 'Operator statement, not verified consent or exhibition permission.',
                  'limits': 'No biological perception/activity, physical trajectory or causal memory claim.'}
    svg = ET.Element('svg', {'xmlns': 'http://www.w3.org/2000/svg', 'viewBox': '0 0 900 940',
                            'role': 'img', 'aria-labelledby': 'title description'})
    ET.SubElement(svg, 'title', {'id': 'title'}).text = manifest['stimulus']['manifest']['title'] + ' — Afterimage'
    ET.SubElement(svg, 'desc', {'id': 'description'}).text = LABEL + ' Chronological response-plane line with a marked start; coincident points retained. Fixed axes ±360. Metadata contains every frame and response.'
    ET.SubElement(svg, 'metadata').text = json.dumps(provenance, sort_keys=True, allow_nan=False)
    ET.SubElement(svg, 'rect', {'width': '900', 'height': '940', 'fill': '#fcfaf4'})
    group = ET.SubElement(svg, 'g', {'transform': 'translate(450 430)'})
    for x1, y1, x2, y2 in ((-360, 0, 360, 0), (0, -360, 0, 360)):
        ET.SubElement(group, 'line', {'x1': str(x1), 'y1': str(y1), 'x2': str(x2), 'y2': str(y2), 'stroke': '#8c8a83', 'stroke-width': '1'})
    ET.SubElement(group, 'rect', {'x': '-360', 'y': '-360', 'width': '720', 'height': '720', 'fill': 'none', 'stroke': '#8c8a83'})
    ET.SubElement(group, 'polyline', {'points': ' '.join(f'{row["point"][0]:.9g},{row["point"][1]:.9g}' for row in rows),
                                     'fill': 'none', 'stroke': '#244c5a', 'stroke-width': '2'})
    x, y = rows[0]['point']
    ET.SubElement(group, 'circle', {'cx': str(x), 'cy': str(y), 'r': '4', 'fill': '#aa392b'})
    texts = [(28, 'Afterimage · authored model portrait'), (825, 'x = 360 × velocity / 3; y = −360 × heading / π · fixed axes ±360'),
             (850, f'{len(rows)} frames · {len(rows) * DT:.2f}s model index · offline inference / recorded playback'),
             (875, manifest['policy_identity']['controller'] + ' · ' + manifest['run_id']),
             (900, 'Not fly perception or biological activity. Red dot marks sequence start.'),
             (925, manifest['evidence'] + ' · operator rights statement retained; consent not verified')]
    for y, value in texts:
        ET.SubElement(svg, 'text', {'x': '40', 'y': str(y), 'font-family': 'sans-serif', 'font-size': '15', 'fill': '#213536'}).text = value
    payload = ET.tostring(svg, encoding='utf-8', xml_declaration=True)
    if len(payload) > MAX_SVG_BYTES:
        raise ValueError('portrait exceeds SVG byte cap')
    if storage_budget is not None:
        storage_budget.check(len(payload), path=output)
    stream = output.open('xb')
    try:
        with stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        if artifacts._fingerprint(paths) != fingerprints:
            raise ValueError('recording changed during portrait publication')
    except BaseException:
        output.unlink(missing_ok=True)
        raise
    return output


def worker(config):
    from .male_policy import load_pinned_policy, resolve_profile
    from .storage import StorageBudget, StorageLimits
    storage = config['storage']
    budget = StorageBudget(storage['roots'], StorageLimits(**storage['limits']), headroom_bytes=storage['headroom_bytes'])
    stimulus = load_stimulus(config['stimulus'])
    if stimulus['metadata'] != config['expected_stimulus'] or _source_hashes() != config['expected_sources']:
        raise ValueError('admitted stimulus or source code changed before inference')
    identity, _ = resolve_profile(config['repo'], config['assets'], config['controller'], config['identity'])
    policy = load_pinned_policy(config['repo'], config['assets'], config['controller'], 0, expected_identity=identity)
    def verify_assets():
        if _source_hashes() != config['expected_sources']:
            raise ValueError('admitted source code changed during loading or inference')
        resolve_profile(config['repo'], config['assets'], config['controller'], identity)
    destination = _record(stimulus, policy, config['output'], identity, storage_budget=budget, before_finish=verify_assets)
    print(json.dumps({'status': 'completed', 'run_id': destination.name, 'frames': len(stimulus['frames'])}))
    return 0


if __name__ == '__main__':
    raise SystemExit(worker(artifacts._json(sys.argv[1])))
