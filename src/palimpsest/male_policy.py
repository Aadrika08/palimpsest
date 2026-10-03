"""CPU inference for one explicitly selected, completed male training artifact.

Fixed original/control lab profiles; no retina state or biological sensor mapping.
The tracked manifest supplies the expected report hash; no downloads or API paths.
"""
import hashlib
import io
import math
from pathlib import Path
import zipfile

from . import artifacts
from .male_model import (CELL_SHA256, FEATURE_PROTOCOL, digest, features,
                         load_graph, make_model, reachability, rewire)

VARIANTS = ('original', 'degree_rewired')
CONTROLLERS = {'male-original': 'original', 'male-control': 'degree_rewired'}
PROFILE = 'male-reduced-artificial-interface-v1'
ASSET_DIRECTORY = 'male-reduced-v1'
MANIFEST = 'data/manifests/male-reduced-policy-v1.json'
IDENTITY_HASHES = ('model_manifest_sha256', 'training_report_sha256', 'protocol_sha256', 'checkpoint_sha256',
                   'graph_sha256', 'topology_sha256', 'ordered_ids_sha256', 'feature_protocol_sha256',
                   'cell_source_sha256', 'source_graph_sha256', 'graph_manifest_sha256')
TRAINING_PROTOCOL_SHA256 = '3e6e2aea41bdce07581f0875288a1e20cc5379cbb41d89d3d387cac24db7832b'
MAX_FILE_BYTES = 8 * 1024**2


def _sha(payload):
    return hashlib.sha256(payload).hexdigest()


def _hash(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def validate_identity(value, controller):
    if (controller not in CONTROLLERS or not isinstance(value, dict) or
            set(value) != {'controller', 'variant', 'profile', *IDENTITY_HASHES} or
            value['controller'] != controller or value['variant'] != CONTROLLERS[controller] or
            value['profile'] != PROFILE or not all(_hash(value[key]) for key in IDENTITY_HASHES)):
        raise ValueError('invalid male policy identity')
    return dict(value)


def resolve_profile(repo_root, asset_root, controller, expected_identity=None):
    """Fixed server-side paths only; returns verified identity and loader arguments."""
    if controller not in CONTROLLERS:
        raise ValueError('unknown male controller')
    root, directory = artifacts._safe_path(repo_root), artifacts._safe_path(Path(asset_root) / ASSET_DIRECTORY)
    manifest_bytes = artifacts._read(root / MANIFEST, 1024**2)
    manifest = artifacts._json(manifest_bytes)
    names = {'report.json', 'protocol.json', 'original-graph.json', 'original.pt',
             'degree_rewired-graph.json', 'degree_rewired.pt', 'source-graph.json'}
    if (not isinstance(manifest, dict) or set(manifest) != {'schema_version', 'profile', 'controllers', 'files', 'qualification_claims'} or
            type(manifest['schema_version']) is not int or manifest['schema_version'] != 1 or
            manifest['profile'] != PROFILE or manifest['controllers'] != CONTROLLERS or
            manifest['qualification_claims'] != [] or not isinstance(manifest['files'], dict) or set(manifest['files']) != names):
        raise ValueError('unsupported pinned male model manifest')
    for name, item in manifest['files'].items():
        if (not isinstance(item, dict) or set(item) != {'sha256', 'size_bytes'} or not _hash(item['sha256']) or
                type(item['size_bytes']) is not int or not 0 < item['size_bytes'] <= MAX_FILE_BYTES):
            raise ValueError('invalid pinned male asset entry')
        payload = artifacts._read(directory / name, MAX_FILE_BYTES)
        if len(payload) != item['size_bytes'] or _sha(payload) != item['sha256']:
            raise ValueError('pinned male asset differs: ' + name)
    arguments = {'directory': directory, 'variant': CONTROLLERS[controller],
        'expected_report_sha256': manifest['files']['report.json']['sha256'],
        'graph_path': directory / 'source-graph.json',
        'graph_manifest': root / 'data/manifests/malecns-reduced-neighborhood-v1.json',
        'cell_path': root / 'upstream/fly-gym/models/connectome_rnn_model.py'}
    if _sha(artifacts._read(arguments['cell_path'], 1024**2)) != CELL_SHA256:
        raise ValueError('pinned male cell source differs')
    _, _, provenance = _bundle(**{key: value for key, value in arguments.items() if key != 'cell_path'})
    provenance['model_manifest_sha256'] = _sha(manifest_bytes)
    identity = validate_identity({'controller': controller, 'variant': CONTROLLERS[controller], 'profile': PROFILE,
                                 **{key: provenance[key] for key in IDENTITY_HASHES}}, controller)
    if expected_identity is not None and validate_identity(expected_identity, controller) != identity:
        raise ValueError('recorded male policy identity differs from pinned assets')
    return identity, arguments


def load_pinned_policy(repo_root, asset_root, controller, seed, expected_identity=None):
    identity, arguments = resolve_profile(repo_root, asset_root, controller, expected_identity)
    policy = load_policy(**arguments, seed=seed)
    policy.provenance.update(policy_identity=identity, model_manifest_sha256=identity['model_manifest_sha256'])
    return policy


def _check_archive(payload):
    """Only the bounded ZIP_STORED format emitted by the frozen Torch trainer."""
    if len(payload) > MAX_FILE_BYTES:
        raise ValueError('checkpoint archive exceeds byte limit')
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            names = [member.filename for member in members]
            if (not 1 <= len(members) <= 128 or len(set(names)) != len(names) or
                    sum(member.file_size for member in members) > MAX_FILE_BYTES or
                    any(member.compress_type != zipfile.ZIP_STORED or member.flag_bits & 1 for member in members) or
                    len([name for name in names if name.endswith('/data.pkl')]) != 1):
                raise ValueError('checkpoint archive members or expanded size differ')
    except zipfile.BadZipFile as error:
        raise ValueError('checkpoint requires the bounded Torch ZIP format') from error


def _bundle(directory, variant, expected_report_sha256, graph_path, graph_manifest, *, research_seed=None):
    """Validate retained bytes before importing Torch; never reread teacher data."""
    if variant not in VARIANTS or not _hash(expected_report_sha256):
        raise ValueError('explicit supported variant and expected report SHA256 required')
    directory = artifacts._safe_path(directory)
    names = ['report.json', 'protocol.json', 'original-graph.json', 'original.pt',
             'degree_rewired-graph.json', 'degree_rewired.pt']
    paths = [directory / name for name in names]
    before = artifacts._fingerprint(paths)
    payloads = {name: artifacts._read(path, MAX_FILE_BYTES) for name, path in zip(names, paths)}
    if _sha(payloads['report.json']) != expected_report_sha256:
        raise ValueError('training report hash differs')
    report = artifacts._json(payloads['report.json'])
    if (not isinstance(report, dict) or report.get('status') != 'completed' or
            report.get('training_completed') is not True or report.get('training_attempted') is not True or
            report.get('held_out_used_for_selection') is not False or report.get('qualification_claims') != []):
        raise ValueError('completed bounded training report required')
    ledger = report.get('files')
    if not isinstance(ledger, list) or len(ledger) != 5:
        raise ValueError('training file ledger differs')
    entries = {}
    for item in ledger:
        if not isinstance(item, dict) or set(item) != {'path', 'sha256', 'size_bytes'}:
            raise ValueError('invalid training file entry')
        name = item['path']
        if not isinstance(name, str) or name not in names[1:] or name in entries:
            raise ValueError('unknown or duplicate training file')
        if (type(item['size_bytes']) is not int or item['size_bytes'] != len(payloads[name]) or
                item['sha256'] != _sha(payloads[name])):
            raise ValueError('training file hash or size differs')
        entries[name] = item
    protocol = artifacts._json(payloads['protocol.json'])
    if not isinstance(protocol, dict) or report.get('protocol_sha256') != digest(protocol):
        raise ValueError('training protocol hash differs')
    training_ok = digest(protocol.get('training')) == TRAINING_PROTOCOL_SHA256
    source_names = {'male_model.py', 'artifacts.py', 'records.py', 'train_male_reduced.py'}
    if research_seed is not None:
        from .male_research import validate_training, validate_collection, PAIR_SEEDS
        if type(research_seed) is not int or research_seed not in PAIR_SEEDS or validate_training(protocol.get('training')) != research_seed:
            raise ValueError('research training seed differs')
        validate_collection(protocol.get('collection'), 'development')
        if report.get('held_out_status') != 'locked_unopened' or any('held_out' in item for item in report.get('models', {}).values()):
            raise ValueError('research training opened held-out data')
        if (report.get('source_code_unchanged') is not True or report.get('teacher_sources_unchanged') is not True or
                report.get('finalization_errors') != []):
            raise ValueError('research training final source checks differ')
        source_names.add('male_research.py')
        training_ok = True
    if (not training_ok or
            protocol.get('feature_protocol') != FEATURE_PROTOCOL or
            protocol.get('feature_protocol_sha256') != digest(FEATURE_PROTOCOL) or
            protocol.get('cell_source_sha256') != CELL_SHA256 or
            protocol.get('collection_sha256') != digest(protocol.get('collection'))):
        raise ValueError('training feature, collection, cell, or frozen protocol differs')
    source_hashes = protocol.get('source_code_sha256')
    if (not isinstance(source_hashes, dict) or set(source_hashes) != source_names or
            not all(_hash(value) for value in source_hashes.values())):
        raise ValueError('training source hashes are incomplete')
    original = load_graph(graph_path, graph_manifest)
    control, control_report = rewire(original, 0 if research_seed is None else research_seed)
    graphs = {'original': original, 'degree_rewired': control}
    descriptions = {name: {key: graph[key] for key in ('topology_sha256', 'ordered_ids_sha256',
                    'source_graph_sha256', 'graph_manifest_sha256', 'type_missing_ids')}
                    | {'reachability': reachability(graph)} for name, graph in graphs.items()}
    if protocol.get('graphs') != descriptions or protocol.get('rewiring') != control_report:
        raise ValueError('training topology, ordered IDs, types, or rewiring differs')
    if not isinstance(report.get('models'), dict) or set(report['models']) != set(VARIANTS):
        raise ValueError('completed paired model entries required')
    for name in VARIANTS:
        model = report['models'][name]
        if (not isinstance(model, dict) or model.get('graph_file') != name + '-graph.json' or
                model.get('checkpoint') != entries[name + '.pt'] or
                artifacts._json(payloads[name + '-graph.json']) != graphs[name]):
            raise ValueError('selected model graph or checkpoint identity differs')
    if research_seed is not None:
        for model in report['models'].values():
            history = model.get('history')
            if (model.get('status') != 'completed' or not isinstance(history, list) or len(history) != 20 or
                    [item.get('epoch') for item in history] != list(range(1, 21))):
                raise ValueError('research requires every frozen training epoch')
            losses = [item.get('dev', {}).get('loss') for item in history]
            if (any(type(value) not in (int, float) or not math.isfinite(value) or value < 0 for value in losses) or
                    model.get('selected_epoch') != min(range(1, 21), key=lambda epoch: losses[epoch - 1])):
                raise ValueError('research checkpoint selection differs from frozen dev rule')
    if artifacts._fingerprint(paths) != before:
        raise ValueError('training artifacts changed while loading')
    provenance = {'profile': 'male-reduced-artificial-interface-v1', 'variant': variant,
        'training_report_sha256': expected_report_sha256, 'protocol_sha256': report['protocol_sha256'],
        'checkpoint_sha256': entries[variant + '.pt']['sha256'], 'graph_sha256': digest(graphs[variant]),
        **descriptions[variant], 'cell_source_sha256': CELL_SHA256,
        'feature_protocol': FEATURE_PROTOCOL, 'feature_protocol_sha256': digest(FEATURE_PROTOCOL),
        'training_source_code_sha256': source_hashes, 'collection_sha256': protocol['collection_sha256'],
        'training_seed': protocol['training']['training_seed'], 'training_runtime': protocol.get('runtime'),
        'qualification_claims': [], 'biological_sensor_mapping': False,
        'interface_limit': 'authored learned RGB/contact/goal-bearing encoder; no biological sensor mapping',
        'evaluation_limit': 'single-seed recorded-input imitation; no topology advantage or navigation qualification'}
    if research_seed is not None:
        provenance['evaluation_limit'] = 'one fixed member of three paired research seeds; no topology advantage or navigation qualification'
    return graphs[variant], payloads[variant + '.pt'], provenance


def load_policy(directory, variant, *, expected_report_sha256, graph_path, graph_manifest,
                cell_path, device='cpu', seed=0, research_seed=None):
    """Load exact completed-artifact bytes, validating frozen graph and tensor state."""
    if device != 'cpu' or type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError('male policy requires explicit CPU and a bounded integer seed')
    graph, payload, provenance = _bundle(directory, variant, expected_report_sha256, graph_path, graph_manifest, research_seed=research_seed)
    return _load_checked_policy(graph, payload, provenance, cell_path, device=device, seed=seed)


def _load_checked_policy(graph, payload, provenance, cell_path, *, device='cpu', seed=0):
    """Shared tensor admission only; caller must already validate its bundle."""
    if device != 'cpu' or type(seed) is not int or not 0 <= seed < 2**31:
        raise ValueError('male policy requires explicit CPU and a bounded integer seed')
    _check_archive(payload)
    model = make_model(graph, cell_path, seed)
    import torch
    checkpoint = torch.load(io.BytesIO(payload), map_location='cpu', weights_only=True)
    if (not isinstance(checkpoint, dict) or set(checkpoint) !=
            {'format', 'protocol_sha256', 'graph_sha256', 'ordered_ids_sha256', 'state_dict'} or
            checkpoint['format'] != 'palimpsest-male-reduced-v1' or
            any(checkpoint[key] != provenance[key] for key in ('protocol_sha256', 'graph_sha256', 'ordered_ids_sha256'))):
        raise ValueError('checkpoint format or lineage differs')
    expected, state = model.state_dict(), checkpoint['state_dict']
    if not isinstance(state, dict) or set(state) != set(expected):
        raise ValueError('checkpoint tensor names differ')
    fixed = {name for name, _ in model.named_buffers()} | {'cell.W_values'}
    for name, value in state.items():
        reference = expected[name]
        if (not isinstance(value, torch.Tensor) or value.layout != torch.strided or value.device.type != 'cpu' or
                value.dtype != reference.dtype or value.shape != reference.shape or not torch.isfinite(value).all()):
            raise ValueError('checkpoint tensor shape/dtype/value differs: ' + name)
        if name in fixed and not torch.equal(value, reference):
            raise ValueError('checkpoint fixed graph tensor differs: ' + name)
    model.load_state_dict(state, strict=True)
    model.cell.invalidate_caches()
    model.eval()
    model.requires_grad_(False)
    provenance.update(seed=seed, device='cpu', requested_device='cpu', dtype='torch.float32',
        checkpoint_fixed_tensors=sorted(fixed),
        runtime_source_code_sha256={path.name: _sha(artifacts._read(path, MAX_FILE_BYTES))
            for path in (Path(__file__), Path(__file__).with_name('male_model.py'))})
    return MalePolicy(model, provenance)


class MalePolicy:
    """One-tick CPU wrapper; hidden state commits only after every output validates."""
    snapshot_kind = 'male-reduced-v1'
    def __init__(self, model, provenance):
        import torch
        self.torch, self.agent = torch, model
        self.device, self.dtype = torch.device('cpu'), torch.float32
        self.provenance, self.failure_diagnostics = provenance, {}
        self.reset()

    def reset(self):
        self.hidden = self.agent.reset()
        self.failure_diagnostics = {}

    def act(self, observation):
        import numpy as np
        torch = self.torch
        self.failure_diagnostics = {}
        try:
            if not isinstance(observation, dict) or not isinstance(observation.get('sensors'), dict):
                raise ValueError('declared camera and sensor observation required')
            sensors = observation['sensors']
            contact = np.asarray(sensors.get('collision'))
            angle = np.asarray(0. if sensors.get('collision_angle') is None else sensors['collision_angle'])
            bearing = np.asarray(sensors.get('wind_direction'))
            if (contact.shape != () or angle.shape != () or bearing.shape != (2,) or
                    any(value.dtype.kind not in 'biuf' for value in (contact, angle, bearing)) or
                    'collision_angle' not in sensors):
                raise ValueError('declared contact/bearing sensor shapes or types differ')
            vector = np.array([contact.item(), angle.item(), *bearing], dtype=np.float64)
            value = features({'cam_left': observation.get('cam_left'), 'cam_right': observation.get('cam_right'),
                              'sensors': vector})
            with torch.inference_mode():
                hidden, actions, diagnostics = self.agent(torch.from_numpy(value).reshape(1, 1, 388),
                                                         self.hidden.clone(), diagnostics=True)
                tensors = {'hidden': (hidden, (1, self.agent.cell.N)), 'action': (actions, (1, 1, 2)),
                           'encoded_input': (diagnostics['encoded_input'], (1, 1, self.agent.cell.Nin)),
                           'raw_output': (diagnostics['raw_output'], (1, 1, 2))}
                for name, (tensor, shape) in tensors.items():
                    if tensor.shape != shape or tensor.dtype != torch.float32 or tensor.device.type != 'cpu' or not torch.isfinite(tensor).all():
                        raise ValueError('invalid male inference tensor: ' + name)
                if torch.any(torch.abs(actions) > actions.new_tensor([3., math.pi])):
                    raise ValueError('male inference action units exceed bounds')
                result = {name: tensors[name][0].reshape(-1).cpu().numpy().copy()
                          for name in ('action', 'encoded_input', 'raw_output')}
                self.hidden = hidden.clone()
                return result
        except Exception as error:
            self.failure_diagnostics = {'type': type(error).__name__, 'message': str(error)[:512]}
            raise
