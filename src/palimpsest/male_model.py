"""Bounded male-neighborhood preparation with an explicitly artificial interface.

NumPy preparation is independent of Torch. This module does not integrate with
the lab, import the female retina/agent, or load pretrained female parameters.
"""
from collections import Counter
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import random

from . import artifacts
from .records import iter_ticks

GRAPH_SHA256 = '5aba0fef99afba666b88e40fc535091454e46d9330580d9280b203e8da0abac0'
CELL_SHA256 = '707cba79e7bf92923618ccc596e3d7a2d779edc02a970b0949f6dd3c0d28ae80'
MAX_SOURCE_BYTES = 1024**3
MAX_RUN_BYTES = 32 * 1024**2
MAX_TICKS = 6000
MAX_RUNS = 16
FEATURE_PROTOCOL = {'version': 1, 'id': 'artificial-two-eye-boundary-v1',
    'cameras': ['cam_left', 'cam_right'], 'camera_shape': [128, 128, 3],
    'image_mapping': 'uint8 RGB; mean each nonoverlapping 16x16 block; divide by 255; flatten 8x8x3 in C order, left then right',
    'sensors': ['collision', 'collision_angle/pi', 'wind_cos', 'wind_sin'],
    'feature_count': 388, 'privileged_inputs': [],
    'encoder': 'learned Linear(388, number_of_artificial_input_nodes), tanh',
    'biological_sensor_mapping': False,
    'action': ['velocity scalar = 3*tanh(raw[0])', 'relative heading radians = pi*tanh(raw[1])']}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def validate_graph(raw):
    if not isinstance(raw, dict):
        raise ValueError('male graph must be an object')
    nodes, edges, inputs, outputs = (raw.get(key) for key in ('nodes', 'edges', 'input_candidates', 'endpoints'))
    if raw.get('dataset') != 'male-cns:v1.0' or not isinstance(nodes, list) or not 3 <= len(nodes) <= 256:
        raise ValueError('unsupported or oversized male graph')
    if any(not isinstance(node, dict) or type(node.get('bodyId')) is not int or node['bodyId'] <= 0 or
           (node.get('type') is not None and (not isinstance(node['type'], str) or not node['type'])) for node in nodes):
        raise ValueError('invalid male node identity/type')
    ids = [node['bodyId'] for node in nodes]
    if ids != sorted(set(ids)) or outputs != [12781, 556329]:
        raise ValueError('ordered male node/output identities differ')
    if not isinstance(inputs, list) or not inputs or any(type(identifier) is not int for identifier in inputs):
        raise ValueError('invalid artificial boundary inputs')
    if inputs != sorted(set(inputs)) or not set(inputs) <= set(ids) or set(inputs) & set(outputs) or not set(outputs) <= set(ids):
        raise ValueError('invalid artificial boundary input/output identities')
    if not isinstance(edges, list) or not 1 <= len(edges) <= 4096 or any(
            not isinstance(edge, list) or len(edge) != 3 or any(type(n) is not int or n <= 0 for n in edge) or
            edge[0] not in ids or edge[1] not in ids or edge[0] == edge[1] for edge in edges):
        raise ValueError('invalid male directed edges')
    if len({tuple(edge[:2]) for edge in edges}) != len(edges):
        raise ValueError('duplicate male directed edges')
    type_labels = sorted({node['type'] for node in nodes if node.get('type') is not None})
    type_index = {label: i + 1 for i, label in enumerate(type_labels)}
    incoming = Counter()
    for _, post, weight in edges:
        incoming[post] += weight
    return {'ids': ids, 'edges': sorted(edges), 'inputs': list(inputs), 'outputs': list(outputs),
        'type_labels': [None, *type_labels], 'type_ids': [type_index.get(node.get('type'), 0) for node in nodes],
        'type_missing_ids': [node['bodyId'] for node in nodes if node.get('type') is None],
        'neurotransmitter_signs': 'not acquired; positive anatomical counts, not physiological signed weights',
        'weight_scale': .9 / max(incoming.values()), 'boundary': copy.deepcopy(raw.get('boundary')),
        'ordered_ids_sha256': hashlib.sha256(''.join(f'{identifier}\n' for identifier in ids).encode()).hexdigest(),
        'biological_sensor_mapping': False}


def load_graph(graph_path, manifest_path):
    payload = artifacts._read(graph_path, 4 * 1024**2)
    manifest_bytes = artifacts._read(manifest_path, 1024**2)
    manifest, raw = artifacts._json(manifest_bytes), artifacts._json(payload)
    if not isinstance(manifest, dict) or not isinstance(raw, dict):
        raise ValueError('graph and extraction manifest must be objects')
    if hashlib.sha256(payload).hexdigest() != GRAPH_SHA256 or manifest.get('graph_sha256') != GRAPH_SHA256:
        raise ValueError('pinned male graph hash differs')
    if len(payload) != manifest.get('graph_size_bytes') or raw.get('protocol_sha256') != manifest.get('protocol_sha256'):
        raise ValueError('graph and extraction manifest differ')
    graph = validate_graph(raw)
    if (len(graph['ids']), len(graph['edges'])) != (manifest.get('nodes'), manifest.get('edges')):
        raise ValueError('graph and manifest counts differ')
    graph.update(source_graph_sha256=GRAPH_SHA256, graph_manifest_sha256=hashlib.sha256(manifest_bytes).hexdigest(),
        extraction_protocol_sha256=raw['protocol_sha256'], license=manifest['license'], attribution=manifest['attribution'])
    graph['topology_sha256'] = digest(graph['edges'])
    return graph


def dense_weights(graph):
    """Small capped graph only: W[post, pre], never W[pre, post]."""
    import numpy as np
    index = {identifier: i for i, identifier in enumerate(graph['ids'])}
    matrix = np.zeros((len(index), len(index)), dtype=np.float32)
    for pre, post, weight in graph['edges']:
        matrix[index[post], index[pre]] = weight * graph['weight_scale']
    return matrix


def reachability(graph):
    incoming = {identifier: [] for identifier in graph['ids']}
    for pre, post, _ in graph['edges']:
        incoming[post].append(pre)
    reached = set()
    by_output = {}
    for output in graph['outputs']:
        visited, pending = {output}, [output]
        while pending:
            for pre in incoming[pending.pop()]:
                if pre not in visited:
                    visited.add(pre)
                    pending.append(pre)
        inputs = sorted(set(graph['inputs']) & visited)
        by_output[str(output)] = inputs
        reached.update(inputs)
    return {'reachable_input_ids': sorted(reached), 'unreachable_input_ids': sorted(set(graph['inputs']) - reached),
            'by_output': by_output, 'interpretation': 'directed graph paths only; not a biological sensor mapping or behavioural qualification'}


def rewire(graph, seed):
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError('rewiring seed must be a bounded integer')
    rng = random.Random(seed)
    edges = copy.deepcopy(graph['edges'])
    pairs = {tuple(edge[:2]) for edge in edges}
    target, swaps, attempts = 10 * len(edges), 0, 0
    while swaps < target and attempts < 200 * len(edges):
        attempts += 1
        i, j = rng.sample(range(len(edges)), 2)
        a, b, w = edges[i]
        c, d, v = edges[j]
        if a == c or b == d or a == d or c == b or (a, d) in pairs or (c, b) in pairs:
            continue
        pairs.remove((a, b)); pairs.remove((c, d))
        pairs.update(((a, d), (c, b)))
        edges[i], edges[j] = [a, d, w], [c, b, v]
        swaps += 1
    if swaps != target:
        raise ValueError('degree-preserving control did not meet the frozen swap budget')
    if any(Counter(edge[index] for edge in edges) != Counter(edge[index] for edge in graph['edges']) for index in (0, 1, 2)):
        raise ValueError('rewiring changed degrees or the weight multiset')
    control = {**graph, 'edges': sorted(edges), 'topology_sha256': digest(sorted(edges))}
    if control['edges'] == graph['edges']:
        raise ValueError('rewiring did not change topology')
    return control, {'seed': seed, 'successful_swaps': swaps, 'attempts': attempts,
        'in_out_degrees_and_weight_multiset_preserved': True, 'weighted_in_strength_preserved': False,
        'reachability': reachability(control)}


def features(row):
    import numpy as np
    images = []
    for key in FEATURE_PROTOCOL['cameras']:
        image = np.asarray(row.get(key))
        if image.shape != (128, 128, 3) or image.dtype != np.uint8:
            raise ValueError('artificial encoder requires recorded 128x128 uint8 RGB eyes')
        images.append((image.reshape(8, 16, 8, 16, 3).mean(axis=(1, 3)) / 255).astype(np.float32).ravel())
    sensor = np.asarray(row.get('sensors'))
    if sensor.shape != (4,) or sensor.dtype.kind not in 'iuf' or not np.isfinite(sensor).all():
        raise ValueError('invalid declared recorded sensors')
    if sensor[0] not in (0, 1) or abs(sensor[1]) > math.pi + 1e-6 or not np.isclose(np.linalg.norm(sensor[2:]), 1., atol=1e-4, rtol=0):
        raise ValueError('recorded contact/relative-goal-bearing units differ')
    return np.concatenate([*images, sensor.astype(np.float32) / np.array([1, math.pi, 1, 1], dtype=np.float32)])


def prepare_splits(paths):
    import numpy as np
    if set(paths) != {'train', 'dev', 'held_out'} or any(not isinstance(value, list) or not value for value in paths.values()):
        raise ValueError('explicit nonempty train/dev/held_out run lists are required')
    if sum(map(len, paths.values())) > MAX_RUNS:
        raise ValueError('teacher run count exceeds limit')
    result, report = {}, {'splits': {}, 'total_ticks': 0, 'total_source_bytes': 0}
    identifiers, scene_splits, payload_splits = set(), {}, {}
    for split in ('train', 'dev', 'held_out'):
        result[split], report['splits'][split] = [], []
        for path in paths[split]:
            run = artifacts._safe_path(path)
            manifest = artifacts._manifest(run)
            identity = str(artifacts._id(manifest['run_id']))
            if identity in identifiers:
                raise ValueError('teacher run overlaps frozen splits')
            identifiers.add(identity)
            if (manifest.get('controller') != 'teacher' or manifest.get('profile') != 'teacher' or
                    manifest.get('teacher_privileged') is not True or manifest.get('parent_run_id') is not None or
                    manifest.get('replay_mode') is not None or manifest.get('replay_source_run_id') is not None or
                    manifest.get('initial_memory') is not None):
                raise ValueError('training requires independent root teacher recordings, without replay or memory supervision')
            if (manifest.get('observation_profile') != 'two-rgb-eyes-contact-relative-goal-bearing-v1' or
                    manifest.get('sensor_order') != ['collision', 'collision_angle', 'wind_cos', 'wind_sin'] or
                    manifest.get('control_interval_seconds') != .02):
                raise ValueError('teacher observation/control profile differs')
            events = artifacts._events(run)
            chunks = [event for event in events if event['kind'] == 'chunk']
            if len(chunks) > artifacts.MAX_CHUNKS or any(event.get('path') != f'chunks/{i:06d}.npz' for i, event in enumerate(chunks)):
                raise ValueError('invalid teacher chunk sequence')
            source_paths = [run / 'recording' / name for name in ('manifest.json', 'events.jsonl')]
            source_paths += [run / 'recording' / event['path'] for event in chunks]
            before = artifacts._fingerprint(source_paths)
            snapshot_paths = []
            snapshots = artifacts._safe_path(run / 'snapshots')
            if snapshots.exists():
                for index, snapshot in enumerate(snapshots.iterdir()):
                    if index >= 65 or not artifacts._safe_path(snapshot).is_file():
                        raise ValueError('snapshot inventory exceeds the bounded teacher profile')
                    snapshot_paths.append(snapshot)
            snapshot_fingerprint = artifacts._fingerprint(snapshot_paths)
            run_bytes = sum(item[2] for item in (*before, *snapshot_fingerprint))
            if run_bytes > MAX_RUN_BYTES:
                raise ValueError('teacher recording and snapshots exceed 32 MiB')
            report['total_source_bytes'] += run_bytes
            count = manifest.get('recorded_ticks')
            if type(count) is not int or count < 1 or report['total_ticks'] + count > MAX_TICKS or report['total_source_bytes'] > MAX_SOURCE_BYTES:
                raise ValueError('teacher recording duration/byte budget exceeded or recording incomplete')
            data = artifacts._load(run)
            if data['fingerprint'] != before:
                raise ValueError('teacher source changed during validation')
            starts = {}
            for event in events:
                if 'run_id' in event and str(artifacts._id(event['run_id'])) != identity:
                    raise ValueError('teacher event identity differs')
                if event['kind'] == 'episode_started':
                    episode, seed = event.get('episode'), event.get('seed')
                    if type(episode) is not int or episode < 0 or type(seed) is not int or not 0 <= seed < 2**31 or episode in starts:
                        raise ValueError('teacher episode lacks a unique recorded seed')
                    starts[episode] = seed
                if event['kind'] in {'application_restored', 'controller_replaced', 'replay_started', 'intervention', 'eyes_changed'} or event['kind'].startswith('memory_'):
                    raise ValueError('teacher has unsupported restored/controller/intervention/memory lineage')
            if type(manifest.get('seed')) is not int or starts.get(0) != manifest['seed']:
                raise ValueError('teacher manifest and initial episode seed differ')
            episodes = {}
            for row in iter_ticks(run / 'recording'):
                episode = row['episode']
                if episode not in starts:
                    raise ValueError('teacher ticks lack episode start provenance')
                values = episodes.setdefault(episode, {'features': [], 'targets': [], 'episode': episode, 'run_id': manifest['run_id']})
                if row['tick'] != len(values['features']):
                    raise ValueError('teacher episodes must start at tick zero without missing steps')
                if 'eyes' in row:
                    eyes = np.asarray(row['eyes'])
                    if eyes.shape != (2,) or eyes.dtype.kind != 'b' or not eyes.all():
                        raise ValueError('initial teacher pilot requires both recorded eye channels enabled')
                target = np.asarray(row.get('action'))
                if target.shape != (2,) or target.dtype.kind not in 'iuf' or not np.isfinite(target).all() or np.any(np.abs(target) > np.array([3., math.pi]) + 1e-6):
                    raise ValueError('invalid teacher action or action units')
                if not math.isclose(artifacts._scalar(row['simulation_time'], 'simulation time'), (row['tick'] + 1) * .02, rel_tol=0., abs_tol=1e-8):
                    raise ValueError('teacher control-time contract differs')
                values['features'].append(features(row))
                values['targets'].append(target.astype(np.float32))
            source_hash = hashlib.sha256()
            for episode, values in episodes.items():
                scene = digest([manifest.get('scenario'), manifest.get('texture'), starts[episode]])
                if scene in scene_splits and scene_splits[scene] != split:
                    raise ValueError('scene seed overlaps teacher splits')
                scene_splits[scene] = split
                values['features'] = np.stack(values['features'])
                values['targets'] = np.stack(values['targets'])
                payload = values['features'].tobytes() + values['targets'].tobytes()
                payload_hash = hashlib.sha256(payload).hexdigest()
                if payload_hash in payload_splits and payload_splits[payload_hash] != split:
                    raise ValueError('copied feature/target episode overlaps teacher splits')
                payload_splits[payload_hash] = split
                source_hash.update(canonical({'episode': episode, 'ticks': len(values['features'])}))
                source_hash.update(payload)
                result[split].append(values)
            files = [{'path': file.relative_to(run).as_posix(), 'size_bytes': before[index][2],
                      'sha256': (hashlib.sha256(artifacts._read(file, artifacts.MAX_EVENTS)).hexdigest() if index < 2 else chunks[index - 2]['sha256'])}
                     for index, file in enumerate(source_paths)]
            if artifacts._fingerprint(source_paths) != before or artifacts._fingerprint(snapshot_paths) != snapshot_fingerprint:
                raise ValueError('teacher source changed during feature preparation')
            report['splits'][split].append({'run_id': manifest['run_id'], 'path': str(run), 'files': files,
                'recording_sha256': digest(files), 'feature_target_sha256': source_hash.hexdigest(),
                'recording_and_snapshot_bytes': run_bytes, 'final_phase': manifest.get('final_phase'),
                'scenario': manifest.get('scenario'), 'texture': manifest.get('texture'),
                'last_outcome': manifest.get('last_outcome'),
                'validation_files': [file.relative_to(run).as_posix() for file in (*source_paths, *snapshot_paths)],
                'validation_fingerprint': [list(item) for item in (*before, *snapshot_fingerprint)],
                'snapshot_inventory': sorted(path.name for path in snapshot_paths),
                'episodes': [{'episode': item['episode'], 'seed': starts[item['episode']], 'ticks': len(item['features'])} for item in episodes.values()]})
            report['total_ticks'] += count
    check_sources(report)
    return result, report


def check_sources(collection):
    """Recheck every source, including those prepared before a later source."""
    for sources in collection['splits'].values():
        for source in sources:
            run = artifacts._safe_path(source['path'])
            actual = artifacts._fingerprint([run / name for name in source['validation_files']])
            if [list(item) for item in actual] != source['validation_fingerprint']:
                raise ValueError('teacher source changed after frozen feature preparation')
            directory = artifacts._safe_path(run / 'snapshots')
            names = sorted(path.name for path in directory.iterdir()) if directory.exists() else []
            if names != source['snapshot_inventory']:
                raise ValueError('teacher snapshot inventory changed after preparation')


def make_model(graph, cell_path, seed):
    """Explicit Torch entry point; CPU only, fresh training, pinned cell source only."""
    source = artifacts._read(cell_path, 1024**2)
    if hashlib.sha256(source).hexdigest() != CELL_SHA256:
        raise ValueError('upstream cell source hash differs')
    import numpy as np
    import torch
    if type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError('training seed must be a bounded integer')
    if torch.__version__.split('+')[0] != '2.9.0' or np.__version__ != '2.2.5':
        raise ValueError('training requires the pinned Torch 2.9.0 / NumPy 2.2.5 runtime')
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    # Execute exactly the bytes whose hash was checked, not a second mutable read.
    spec = importlib.util.spec_from_loader('_palimpsest_pinned_male_cell', loader=None)
    upstream = importlib.util.module_from_spec(spec)
    exec(compile(source, str(cell_path), 'exec'), upstream.__dict__)
    index = {identifier: i for i, identifier in enumerate(graph['ids'])}

    class MaleReducedModel(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder = torch.nn.Sequential(torch.nn.Linear(388, len(graph['inputs'])), torch.nn.Tanh())
            self.cell = upstream.LeakyConnectomeRNNCell(torch.from_numpy(dense_weights(graph)).to_sparse_coo(),
                [index[n] for n in graph['inputs']], [index[n] for n in graph['outputs']],
                torch.tensor(graph['type_ids'], dtype=torch.long), len(graph['type_labels']),
                train_rnn_weights=False, train_readout_head=True, dtype=torch.float32, compile_step_fn=False)

        def reset(self):
            return torch.zeros(1, len(graph['ids']), dtype=torch.float32)

        def forward(self, inputs, hidden):
            if inputs.device.type != 'cpu' or inputs.dtype != torch.float32 or inputs.ndim != 3 or inputs.shape[1:] != (1, 388) or not 1 <= inputs.shape[0] <= 64:
                raise ValueError('male model requires a bounded CPU float32 feature window')
            if hidden.device.type != 'cpu' or hidden.dtype != torch.float32 or hidden.shape != (1, len(graph['ids'])):
                raise ValueError('male hidden state shape/device differs')
            if not torch.isfinite(inputs).all() or not torch.isfinite(hidden).all():
                raise ValueError('nonfinite male input/hidden state')
            encoded = self.encoder(inputs)
            if not torch.isfinite(encoded).all():
                raise ValueError('nonfinite artificial encoder output')
            next_hidden, raw, _ = self.cell(hidden, encoded, store_sequence=True, checkpoint_steps=False)
            if not torch.isfinite(next_hidden).all() or not torch.isfinite(raw).all():
                raise ValueError('nonfinite male cell/readout output; no action emitted')
            actions = torch.tanh(raw) * raw.new_tensor([3., math.pi])
            if not torch.isfinite(actions).all():
                raise ValueError('nonfinite male action')
            return next_hidden, actions

    return MaleReducedModel()
