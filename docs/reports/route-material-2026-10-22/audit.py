"""Audit actual route coordinates, registered lineage and the sole goal edit."""
import hashlib
import html
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
import numpy as np
from palimpsest.records import iter_ticks
from palimpsest.artifacts import registered_snapshots
from palimpsest.snapshots import read_snapshot, state_digest
from record_route_material import pins

root = Path('runs/route-material-2026-10-22-v1')
cfg = json.loads((root / 'registration.json').read_text())
result = json.loads((root / 'generation/result.json').read_text())
assert result['status'] == 'passed' and pins() == cfg['sources']
parent, branch = (root / result[key] for key in ('parent_run_id', 'branch_run_id'))
entry = result['snapshot']
assert entry['snapshot_id'] in {s['snapshot_id'] for s in registered_snapshots(parent)}
snapshot_path = parent / 'snapshots' / entry['filename']
assert hashlib.sha256(snapshot_path.read_bytes()).hexdigest() == entry['sha256']
snapshot, initial = read_snapshot(snapshot_path), read_snapshot(branch / 'snapshots/initial.snp')
assert snapshot['application']['total_tick'] == initial['application']['total_tick'] == 100
assert state_digest(snapshot['policy']) == state_digest(initial['policy'])
assert state_digest(snapshot['rng']) == state_digest(initial['rng'])
assert np.array_equal(snapshot['integration'].view(np.uint8), initial['integration'].view(np.uint8))
assert initial['application']['revision'] == snapshot['application']['revision'] + 1
assert initial['application']['eyes'] == snapshot['application']['eyes'] == {'left': True, 'right': True}
prefix = snapshot['application']['event_prefix']
source_events = (parent / 'recording/events.jsonl').read_bytes()
assert hashlib.sha256(source_events[:prefix['size_bytes']]).hexdigest() == prefix['sha256']
assert len(source_events[:prefix['size_bytes']].splitlines()) == prefix['event_count']
events = [json.loads(line) for line in (branch / 'recording/events.jsonl').read_text().splitlines()]
restored = [e for e in events if e['kind'] == 'application_restored']
created = [e for e in events if e['kind'] == 'branch_created']
edits = [e for e in events if e['kind'] in ('intervention', 'eyes_changed', 'controller_replaced')]
assert len(restored) == len(created) == len(edits) == 1
assert restored[0]['parent_run_id'] == parent.name and restored[0]['parent_event_prefix'] == prefix
assert created[0]['parent_snapshot_id'] == entry['snapshot_id'] and created[0]['controller_replaced'] is False
assert edits[0]['episode_step'] == 100 and edits[0]['change']['kind'] == 'move_goal'
assert edits[0]['change']['new']['xy'] == [0., 0.]
ns = '{http://www.w3.org/2000/svg}'
svg = ET.parse(root / 'exports/borrowed-body.svg').getroot()
body = json.loads(svg.find(ns + 'metadata').text)
comparison_text = (root / 'exports/one-map-many-lives.html').read_text()
comparison = json.loads(html.unescape(re.search(r'<pre id="comparison-metadata">(.*?)</pre>', comparison_text, re.S)[1]))
counts, source_files = {}, {}
starts = {}
parent_boundary_pose = None
for label, run, start, expected in (('left', parent, 0, 375), ('right', branch, 100, 7)):
    points = []
    for i, row in enumerate(iter_ticks(run / 'recording')):
        assert row['episode'] == 0 and row['tick'] == start + i
        assert np.all(row['eyes'])
        assert abs(float(row['simulation_time']) - (start + i + 1) * .02) < 1e-7
        if not points:
            points.append(row['pose'][:2].tolist())
            starts[label] = row['pose'].copy()
        else:
            assert points[-1] == row['pose'][:2].tolist()
        points.append(row['next_pose'][:2].tolist())
        if label == 'left' and row['tick'] == 100:
            parent_boundary_pose = row['pose'].copy()
    assert i + 1 == expected
    side = comparison['comparison'][label]
    assert side['run_id'] == run.name
    assert side['traces'] == [{'episode': 0, 'start_tick': start, 'points': points}]
    if label == 'left':
        assert body['traces'] == side['traces']
        assert svg.find('.//' + ns + 'polyline').attrib['points'] == ' '.join(f'{x},{y}' for x, y in points)
    overlay = re.search(r'<[^>]*polyline\b[^>]*data-run-id="' + run.name + r'"[^>]*points="([^"]+)"', comparison_text)
    assert overlay and overlay[1] == ' '.join(f'{x},{y}' for x, y in points)
    files = comparison['sources'][0 if label == 'left' else 1]['files']
    for f in files:
        path = run / f['path']
        assert path.stat().st_size == f['size_bytes']
        with path.open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == f['sha256']
    counts[label] = {'run_id': run.name, 'start_tick': start, 'intervals': expected,
                     'points': expected + 1, 'simulation_seconds': expected * .02,
                     'outcome': side['last_outcome']}
    source_files[run.name] = files
# The goal edit calls mj_forward: refresh cached body xpos without advancing state.
import mujoco
native = mujoco.MjData.__new__(mujoco.MjData)
native.__setstate__(snapshot['native_data'])
base = mujoco.mj_name2id(native.model, mujoco.mjtObj.mjOBJ_BODY, 'base')
assert np.array_equal(np.array(native.xpos[base, :2], np.float32), parent_boundary_pose[:2])
mujoco.mj_forward(native.model, native)
assert np.array_equal(np.array(native.xpos[base, :2], np.float32), starts['right'][:2])
state = np.empty_like(snapshot['integration'])
mujoco.mj_getState(native.model, native, state, mujoco.mjtState.mjSTATE_INTEGRATION)
assert np.array_equal(state.view(np.uint8), snapshot['integration'].view(np.uint8))
boundary_delta = (starts['right'] - parent_boundary_pose).tolist()
assert comparison['comparison']['right']['provenance']['parent_run_id'] == parent.name
assert comparison['comparison']['right']['provenance']['source_snapshot_id'] == entry['snapshot_id']
assert pins() == cfg['sources']
audit = {'status': 'passed', 'routes': counts, 'snapshot_id': entry['snapshot_id'],
         'snapshot_sha256': entry['sha256'], 'branch_start_pose_matches_parent_tick_100': False,
         'branch_start_minus_parent_pose': boundary_delta,
         'pose_difference_reproduced_by_mj_forward_without_integrating': True,
         'integration_state_preserved_at_restore_and_edit': True,
         'controller_state_and_rng_preserved_at_restore': True, 'sole_edit': edits[0],
         'source_files': source_files, 'all_exported_coordinates_exact': True,
         'source_pins_unchanged': True, 'qualification_claims': []}
with (root / 'independent-audit.json').open('x') as stream:
    json.dump(audit, stream, indent=2)
source = {'parent_run_id': parent.name, 'branch_run_id': branch.name,
          'snapshot_id': entry['snapshot_id'], 'snapshot_sha256': entry['sha256'],
          'branch_tick': 100, 'intervention': result['intervention'],
          'branch_start_minus_parent_pose': boundary_delta,
          'boundary_note': 'Goal edit refreshes derived body position via mj_forward; integration state is unchanged. Recorded coordinates are retained without alignment.',
          'files_sha256': {name: hashlib.sha256((root / 'exports' / name).read_bytes()).hexdigest()
                           for name in ('borrowed-body.svg', 'one-map-many-lives.html')}}
with (root / 'routes-source.json').open('x') as stream:
    json.dump(source, stream, indent=2)
print(json.dumps({'status': 'passed', 'routes': counts, 'snapshot_id': entry['snapshot_id']}))
