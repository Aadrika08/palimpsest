"""Offline, fixed mappings of recorded population means; no inference or playback."""
from fractions import Fraction
import hashlib
import json
import math
import struct
import wave

from . import artifacts
from .records import iter_ticks

FREQUENCIES = {'visual_left': 220., 'visual_right': 330., 'descending': 440.}
SAMPLE_RATE = 48_000
GAIN = .25
MAX_SECONDS = 120
MAX_SOURCE_BYTES = 512 * 1024**2
MAX_OUTPUT_BYTES = 16 * 1024**2
MAX_METADATA_BYTES = 64 * 1024
LABEL = 'Composed mapping of recorded model activity, not biological audio; offline derivative, not live inference.'


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _source(run_path):
    """Bound the existing whole-record validator before it reads numeric chunks."""
    run = artifacts._safe_path(run_path)
    manifest = artifacts._manifest(run)
    dt = manifest.get('control_interval_seconds')
    count = manifest.get('recorded_ticks')
    if type(dt) not in (int, float) or not math.isfinite(dt) or not 1 / SAMPLE_RATE <= dt <= MAX_SECONDS:
        raise ValueError('invalid recorded control interval')
    if type(count) is not int or not 1 <= count <= artifacts.MAX_TICKS or count * dt > MAX_SECONDS:
        raise ValueError('recording exceeds the sonification duration limit or has no ticks')
    events = artifacts._events(run)
    chunks = [event for event in events if event['kind'] == 'chunk']
    if len(chunks) > artifacts.MAX_CHUNKS or any(event.get('path') != f'chunks/{i:06d}.npz' for i, event in enumerate(chunks)):
        raise ValueError('invalid recording chunk paths')
    paths = [run / 'recording' / name for name in ('manifest.json', 'events.jsonl')]
    paths += [run / 'recording' / event['path'] for event in chunks]
    fingerprint = artifacts._fingerprint(paths)
    if sum(item[2] for item in fingerprint) > MAX_SOURCE_BYTES:
        raise ValueError('recording exceeds the sonification input byte limit')
    data = artifacts._load(run)
    if data['fingerprint'] != fingerprint:
        raise ValueError('recording changed during sonification validation')
    return data, dt


def _lineage(data):
    manifest, events = data['manifest'], data['events']
    run_id = artifacts._id(manifest['run_id'])
    if manifest.get('controller') != 'flynn' or manifest.get('profile') != 'flynn':
        raise ValueError('sonification requires recorded FLYNN neural telemetry')
    for event in events:
        if 'run_id' in event and artifacts._id(event['run_id']) != run_id:
            raise ValueError('recorded event run lineage differs')
    parent, prefix = manifest.get('parent_run_id'), manifest.get('parent_event_prefix')
    restored = [event for event in events if event['kind'] == 'application_restored']
    if parent is None:
        if prefix is not None or restored:
            raise ValueError('inconsistent parent lineage')
    else:
        if artifacts._id(parent) == run_id or not isinstance(prefix, dict) or not _hash(prefix.get('sha256')):
            raise ValueError('invalid parent lineage')
        if any(type(prefix.get(key)) is not int or prefix[key] < 0 for key in ('size_bytes', 'event_count')):
            raise ValueError('invalid parent event prefix')
        if len(restored) != 1 or any(restored[0].get(key) != manifest.get(key) for key in ('parent_run_id', 'parent_event_prefix')):
            raise ValueError('restored lineage differs from manifest')
    for key in ('source_snapshot_id', 'replay_source_run_id'):
        if manifest.get(key) is not None:
            artifacts._id(manifest[key])
    for event in events:
        if event['kind'] == 'branch_created':
            artifacts._id(event.get('parent_snapshot_id'))
            if parent is None:
                raise ValueError('branch lacks parent lineage')
    policies = [event.get('provenance') for event in events if event['kind'] == 'policy_loaded']
    if len(policies) != 1 or not isinstance(policies[0], dict) or any(
            not _hash(policies[0].get(key)) for key in ('edge_sha256', 'checkpoint_sha256', 'ordered_neuron_ids_sha256')):
        raise ValueError('missing or invalid model lineage hashes')
    return artifacts._provenance(data)


def sonify(run_path, output_path, *, populations, episode=0, storage_budget=None):
    """Write one exclusive mono WAV with an embedded ``plmp`` JSON RIFF chunk.

    All recording integrity and telemetry checks finish before creating output.
    A selected episode is rendered in simulation time, never measured wall time.
    """
    import numpy as np

    if not isinstance(populations, (tuple, list)) or not populations or any(
            not isinstance(name, str) or name not in FREQUENCIES for name in populations) or len(set(populations)) != len(populations):
        raise ValueError('select one or more distinct recorded populations')
    if type(episode) is not int or episode < 0:
        raise ValueError('episode must be a nonnegative integer')
    selected = [name for name in FREQUENCIES if name in populations]
    data, dt = _source(run_path)
    provenance = _lineage(data)
    manifest = data['manifest']
    names = manifest.get('population_names')
    if not isinstance(names, list) or not names or any(not isinstance(name, str) or name not in FREQUENCIES for name in names) or len(set(names)) != len(names):
        raise ValueError('invalid recorded population names')
    if manifest.get('population_columns') != ['count', 'mean', 'min', 'max'] or manifest.get('population_scale') != [-1., 1.]:
        raise ValueError('unsupported recorded population columns or scale')
    if not set(selected) <= set(names):
        raise ValueError('selected neural telemetry is missing')
    rows, counts, previous = [], None, None
    for row in iter_ticks(data['run'] / 'recording'):
        stats = np.asarray(row.get('population_stats'))
        if stats.shape != (len(names), 4) or stats.dtype.kind not in 'iuf' or not np.isfinite(stats).all():
            raise ValueError('missing or invalid neural population telemetry')
        numbers, means, minima, maxima = stats.T
        if (np.any(numbers < 1) or np.any(numbers != np.floor(numbers)) or
                np.any(minima < -1) or np.any(maxima > 1) or np.any(minima > means) or np.any(means > maxima)):
            raise ValueError('invalid neural population statistics or fixed scale')
        if counts is not None and not np.array_equal(numbers, counts):
            raise ValueError('recorded population membership counts changed')
        counts = numbers.copy()
        end = artifacts._scalar(row['simulation_time'], 'simulation time', True)
        if end + 1e-8 < dt or (previous is not None and row['episode'] == previous[0] and not math.isclose(end - previous[1], dt, rel_tol=0., abs_tol=1e-8)):
            raise ValueError('recorded time does not preserve the control interval')
        previous = row['episode'], end
        if row['episode'] == episode:
            rows.append((row['tick'], end, [float(means[names.index(name)]) for name in selected]))
    if not rows:
        raise ValueError('selected episode has no recorded neural telemetry')
    interval = Fraction(str(dt)) * SAMPLE_RATE
    boundaries = [int(index * interval + Fraction(1, 2)) for index in range(len(rows) + 1)]
    source_files = []
    for index, path in enumerate(data['paths']):
        digest = (hashlib.sha256(artifacts._read(path, artifacts.MAX_EVENTS)).hexdigest()
                  if index < 2 else data['chunks'][index - 2]['sha256'])
        source_files.append({'path': path.relative_to(data['run']).as_posix(), 'sha256': digest,
                             'size_bytes': data['fingerprint'][index][2]})
    metadata = {'version': 1, 'artwork': 'counterfactual choir', 'label': LABEL,
        'source': {'run_id': manifest['run_id'], 'profile': manifest['profile'],
            'evidence_class': manifest.get('evidence_class', 'recorded model telemetry; no new inference'),
            'recording_sha256': hashlib.sha256(_json(source_files)).hexdigest(),
            'files': source_files, 'provenance': provenance},
        'renderer': {'mapping_version': 'population-sine-v1', 'numpy_version': np.__version__},
        'timing': {'clock': 'simulation time', 'episode': episode, 'start_tick': rows[0][0],
            'end_tick_inclusive': rows[-1][0], 'control_interval_seconds': dt,
            'simulation_start_seconds': max(0., rows[0][1] - dt), 'simulation_end_seconds': rows[-1][1],
            'sample_boundaries': boundaries, 'boundary_rounding': 'nearest sample; half up; cumulative from output origin'},
        'mapping': {'statistic': 'signed recorded population mean; held constant for each control tick',
            'voices': [{'population': name, 'frequency_hz': FREQUENCIES[name], 'gain': GAIN} for name in selected],
            'carrier': 'sin(2*pi*frequency_hz*sample_index/sample_rate_hz)', 'phase_origin_sample': 0,
            'mix': 'sum of selected voices; no normalization, clipping, interpolation, or added activity',
            'pcm': 'round-to-nearest-even(32767 * mixed signal); signed little-endian int16',
            'sample_rate_hz': SAMPLE_RATE, 'channels': 1, 'sample_width_bytes': 2},
        'pcm_sha256': '0' * 64}
    artifacts._no_secrets(metadata)
    encoded = _json(metadata)
    bound = 44 + boundaries[-1] * 2 + 8 + len(encoded) + len(encoded) % 2
    if len(encoded) > MAX_METADATA_BYTES or bound > MAX_OUTPUT_BYTES:
        raise ValueError('sonification exceeds the output byte limit')
    output = artifacts._safe_path(output_path)
    if output.suffix.lower() != '.wav' or output.is_relative_to(data['run'] / 'recording'):
        raise ValueError('output must be a WAV outside the authoritative recording')
    if artifacts._fingerprint(data['paths']) != data['fingerprint']:
        raise ValueError('recording changed before sonification')
    if storage_budget is not None:
        storage_budget.check(bound, path=output)
    with output.open('xb') as stream:
        try:
            digest = hashlib.sha256()
            with wave.open(stream, 'wb') as audio:
                audio.setparams((1, 2, SAMPLE_RATE, boundaries[-1], 'NONE', 'not compressed'))
                for index, (_, _, means) in enumerate(rows):
                    positions = np.arange(boundaries[index], boundaries[index + 1], dtype=np.float64)
                    signal = np.zeros(len(positions))
                    for name, mean in zip(selected, means):
                        signal += GAIN * mean * np.sin(2 * np.pi * FREQUENCIES[name] * positions / SAMPLE_RATE)
                    pcm = np.rint(32767 * signal).astype('<i2').tobytes()
                    digest.update(pcm)
                    audio.writeframesraw(pcm)
            metadata['pcm_sha256'] = digest.hexdigest()
            encoded = _json(metadata)
            stream.write(struct.pack('<4sI', b'plmp', len(encoded)) + encoded + b'\0' * (len(encoded) % 2))
            size = stream.tell()
            stream.seek(4)
            stream.write(struct.pack('<I', size - 8))
            if size != bound or artifacts._fingerprint(data['paths']) != data['fingerprint']:
                raise ValueError('recording changed or output size differs during sonification')
        except BaseException:
            try:
                stream.close()
            finally:
                output.unlink()
            raise
    return output
