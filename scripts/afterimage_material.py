"""Select the approved left-eye source sequence for Afterimage."""
import hashlib
import json
import math

from palimpsest import artifacts
from palimpsest.records import iter_ticks

TARGET, MAX_TICKS, SOURCE_BYTES = 3000, 3600, 1024**3


def drive(engine):
    sequence = 0
    def command(kind, payload=None):
        nonlocal sequence
        sequence += 1
        receipt = engine.submit({'id': f'afterimage-{sequence}', 'kind': kind,
                                 'expected_state': engine.phase, 'expected_episode': engine.episode,
                                 'payload': payload or {}})
        if receipt['status'] != 'queued':
            raise ValueError('manual command not queued')
        engine.advance()
    while True:
        if engine.phase == 'paused':
            command('set_action', {'action': [1., .5]})
            command('run')
        elif engine.phase in ('terminated', 'truncated'):
            if engine.total_tick >= TARGET:
                return {'intervals': engine.total_tick, 'episodes': engine.episode + 1}
            if engine.episode >= 63:
                raise ValueError('manual episode allocation exhausted')
            command('reset', {'seed': engine.episode + 1})
        elif engine.phase == 'running' and engine.total_tick < MAX_TICKS:
            engine.advance()
        else:
            raise ValueError('manual source failed or interval ceiling reached')
        if engine.total_tick > MAX_TICKS:
            raise ValueError('manual interval ceiling exceeded')


def select(rows):
    import numpy as np
    frames, index = [], []
    previous = None
    count = 0
    for i, row in enumerate(rows):
        count += 1
        episode, tick = row['episode'], row['tick']
        if count > MAX_TICKS or type(episode) is not int or type(tick) is not int:
            raise ValueError('source interval ceiling or index type differs')
        expected = (0, 0) if previous is None else (previous[0], previous[1] + 1)
        if (episode, tick) != expected and (previous is None or (episode, tick) != (previous[0] + 1, 0)):
            raise ValueError('source gaps or episode order differs')
        native = row['simulation_time']
        frame, eyes = row['cam_left'], row['eyes']
        if (np.shape(native) != () or not math.isclose(float(native), (tick + 1) * .02, rel_tol=0, abs_tol=1e-7)
                or frame.shape != (128, 128, 3) or frame.dtype != np.uint8
                or eyes.shape != (2,) or eyes.dtype != np.bool_):
            raise ValueError('source time, left image or eye mask differs')
        if not eyes[0] and np.any(frame):
            raise ValueError('masked effective left camera must be zero')
        if i < TARGET and i % 5 == 0:
            frames.append(frame.copy())
            index.append({'frame': len(index), 'source_interval': i, 'episode': episode, 'tick': tick,
                          'simulation_time_seconds': float(native), 'observation_time_seconds': tick * .02,
                          'presentation_seconds': i / 50, 'eyes': eyes.tolist(),
                          'frame_sha256': hashlib.sha256(frame.tobytes()).hexdigest()})
        previous = episode, tick
    if count < TARGET:
        raise ValueError('3000 complete source intervals required')
    return np.stack(frames), index


def extract(source, output, store):
    """Whole-source validation before publishing the strict portrait stimulus."""
    import numpy as np
    from verify_afterimage import write_json
    manifest = artifacts._manifest(source)
    if (manifest.get('controller') != 'manual' or manifest.get('control_interval_seconds') != .02
            or type(manifest.get('recorded_ticks')) is not int
            or not TARGET <= manifest['recorded_ticks'] <= MAX_TICKS):
        raise ValueError('bounded 50 Hz manual source required')
    # The shared validator is bounded at 2 GiB; narrow this allocation before reading chunks.
    events = artifacts._events(source)
    chunks = [e for e in events if e['kind'] == 'chunk']
    if len(chunks) > MAX_TICKS or any(e['path'] != f'chunks/{i:06d}.npz' for i, e in enumerate(chunks)):
        raise ValueError('source chunk order differs')
    paths = [source / 'recording' / n for n in ('manifest.json', 'events.jsonl')]
    paths += [source / 'recording' / e['path'] for e in chunks]
    before = artifacts._fingerprint(paths)
    if sum(item[2] for item in before) > SOURCE_BYTES:
        raise ValueError('source exceeds 1 GiB')
    data = artifacts._load(source)
    if data['fingerprint'] != before:
        raise ValueError('source changed during validation')
    frames, index = select(iter_ticks(source / 'recording'))
    hashes = {}
    for path in paths:
        with path.open('rb') as stream:
            hashes[str(path.relative_to(source))] = hashlib.file_digest(stream, 'sha256').hexdigest()
    if artifacts._fingerprint(paths) != before:
        raise ValueError('source changed during selection')
    output.mkdir(exist_ok=False)
    frame_path = output / 'frames.npy'
    store.check(frames.nbytes + 4096, path=frame_path)
    with frame_path.open('xb') as stream:
        np.save(stream, frames, allow_pickle=False)
    digest = hashlib.sha256(frame_path.read_bytes()).hexdigest()
    spec = {'schema_version': 1, 'title': 'Sixty seconds of scripted manual lab left-camera footage',
            'creator': 'Palimpsest scripted manual lab recording', 'frame_file': 'frames.npy',
            'frame_file_sha256': digest, 'source_times_seconds': [r['presentation_seconds'] for r in index],
            'rights': {'basis': 'self_created', 'statement': 'Project-generated simulated camera footage; authorized local processing and retention.',
                       'attribution': 'Palimpsest simulator; upstream source notices retained in the encounter pack.',
                       'authorized_processing_and_retention': True, 'subject_consent': 'no_identifiable_people'}}
    provenance = {'schema_version': 1, 'source_run_id': manifest['run_id'], 'source_controller': 'manual',
                  'source_steering': 'scripted constant [1, 0.5] via public set_action; not human joystick input',
                  'camera': 'cam_left', 'source_intervals': manifest['recorded_ticks'], 'selected_intervals': TARGET,
                  'presentation_seconds': 60, 'clock': 'concatenated source time', 'frame_file_sha256': digest,
                  'source_files_sha256': hashes, 'frames': index,
                  'source_episode_resets': 'retained; portrait hidden state carries across source resets'}
    write_json(output / 'stimulus.json', spec, store)
    write_json(output / 'afterimage-source.json', provenance, store)
    return provenance
