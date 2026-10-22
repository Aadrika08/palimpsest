"""Read-only numerical audit of the one allocated source and portrait."""
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
from palimpsest.records import iter_ticks
from record_afterimage_material import pins

root = Path('runs/afterimage-material-2026-10-22-v1')
cfg = json.loads((root / 'registration.json').read_text())
assert pins() == cfg['sources']
source, portrait = root / cfg['run_id'], root / cfg['portrait_run_id']
index = json.loads((root / 'stimulus/afterimage-source.json').read_text())
frames = np.load(root / 'stimulus/frames.npy', allow_pickle=False)
assert frames.shape == (600, 128, 128, 3) and frames.dtype == np.uint8
source_bytes = 0
for name, digest in index['source_files_sha256'].items():
    path = source / name
    source_bytes += path.stat().st_size
    with path.open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == digest
assert source_bytes <= 1024**3
selected = 0
episodes = {}
for i, row in enumerate(iter_ticks(source / 'recording')):
    ep = episodes.setdefault(row['episode'], {'start_interval': i, 'end_interval_inclusive': i})
    ep['end_interval_inclusive'] = i
    if i >= 3000 or i % 5:
        continue
    entry = index['frames'][selected]
    assert entry['source_interval'] == i and entry['episode'] == row['episode'] and entry['tick'] == row['tick']
    assert entry['simulation_time_seconds'] == float(row['simulation_time'])
    assert entry['eyes'] == row['eyes'].tolist()
    assert np.array_equal(row['cam_left'], frames[selected])
    assert hashlib.sha256(frames[selected].tobytes()).hexdigest() == entry['frame_sha256']
    selected += 1
assert i + 1 == index['source_intervals'] == 3543 and selected == 600
svg = ET.parse(root / 'afterimage.svg').getroot()
ns = '{http://www.w3.org/2000/svg}'
meta = json.loads(svg.find(ns + 'metadata').text)
manifest = json.loads((portrait / 'recording/manifest.json').read_text())
assert manifest['seed'] == 0 and manifest['device'] == 'cpu'
assert manifest['policy_identity']['controller'] == 'male-original'
assert manifest['reset'] == 'once at sequence start; carried across every frame'
assert manifest['evidence'] == 'actual model inference'
record_bytes = sum(p.stat().st_size for p in (portrait / 'recording').rglob('*') if p.is_file())
assert record_bytes <= 96 * 1024**2
for n, row in enumerate(iter_ticks(portrait / 'recording')):
    assert np.array_equal(row['cam_left'], frames[n]) and np.array_equal(row['cam_right'], frames[n])
    assert row['source_frame_index'] == n and float(row['source_timestamp_seconds']) == n / 10
    assert float(row['model_time_seconds']) == (n + 1) * .02
    assert np.array_equal(row['sensors'], np.array([0, 0, 1, 0], np.float32))
    action = row['action'].astype(float).tolist()
    np.testing.assert_allclose(action, [3 * np.tanh(row['raw_output'][0]), math.pi * np.tanh(row['raw_output'][1])], rtol=1e-6, atol=1e-6)
    aligned = meta['alignment'][n]
    assert aligned['action'] == action and aligned['frame_sha256'] == index['frames'][n]['frame_sha256']
    assert aligned['point'] == [360 * action[0] / 3, -360 * action[1] / math.pi]
assert n + 1 == len(meta['alignment']) == 600
polyline = svg.find('.//' + ns + 'polyline').attrib['points']
assert polyline == ' '.join(f'{r["point"][0]:.9g},{r["point"][1]:.9g}' for r in meta['alignment'])
for name, digest in meta['recording_files_sha256'].items():
    with (portrait / name).open('rb') as stream:
        assert hashlib.file_digest(stream, 'sha256').hexdigest() == digest
supervisor = json.loads((portrait / 'supervisor.json').read_text())
assert supervisor['status'] == 'completed' and supervisor['returncode'] == 0 and supervisor['timeout_seconds'] == 120
assert pins() == cfg['sources']
result = {'status': 'passed', 'source_intervals': 3543, 'source_episodes': episodes,
          'selected_intervals': 3000, 'frames': 600, 'source_bytes': source_bytes,
          'npy_bytes': (root / 'stimulus/frames.npy').stat().st_size, 'record_bytes': record_bytes,
          'portrait_inference_seconds': supervisor['elapsed_seconds'], 'model_time_seconds': 12,
          'presentation_seconds': 60, 'source_sample_span_seconds': 59.9,
          'svg_bytes': (root / 'afterimage.svg').stat().st_size,
          'svg_sha256': hashlib.sha256((root / 'afterimage.svg').read_bytes()).hexdigest(),
          'all_frame_response_points_checked': True, 'source_pins_unchanged': True,
          'independent_model_forward_rerun': False, 'qualification_claims': []}
with (root / 'independent-audit.json').open('x') as stream:
    json.dump(result, stream, indent=2)
print(json.dumps(result))
