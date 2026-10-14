"""Fixed CPU puck MLP and bounded numeric checkpoints; no native runtime."""
import hashlib
import io
import math
from pathlib import Path
import zipfile

from . import artifacts, puck_learning

SHAPES = {'0.weight': (32, 9), '0.bias': (32,), '2.weight': (32, 32),
          '2.bias': (32,), '4.weight': (2, 32), '4.bias': (2,)}
SEEDS = (21, 22, 23)
MAX_CHECKPOINT = 1024**2
MAX_EXPANDED = 2 * 1024**2


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def canonical(value):
    import json
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def validate_arrays(arrays):
    import numpy as np
    if not isinstance(arrays, dict) or set(arrays) != set(SHAPES):
        raise ValueError('Fixed puck parameter names required')
    for name, shape in SHAPES.items():
        value = arrays[name]
        if (not isinstance(value, np.ndarray) or value.dtype != np.float32 or
                value.shape != shape or not np.isfinite(value).all()):
            raise ValueError('Invalid puck parameter shape/dtype/value: ' + name)
    return {name: np.array(arrays[name], copy=True, order='C') for name in SHAPES}


def checkpoint_bytes(arrays):
    import numpy as np
    stream = io.BytesIO()
    np.savez(stream, **validate_arrays(arrays))
    payload = stream.getvalue()
    if len(payload) > MAX_CHECKPOINT:
        raise ValueError('Puck checkpoint byte limit')
    return payload


def read_checkpoint(payload):
    """Inspect fixed NPY headers before allocation, as the record reader does."""
    import numpy as np
    if type(payload) is not bytes or len(payload) > MAX_CHECKPOINT:
        raise ValueError('Puck checkpoint byte limit/type')
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            members = archive.infolist()
            if (len(members) != 6 or {m.filename for m in members} != {n+'.npy' for n in SHAPES} or
                    sum(m.file_size for m in members) > MAX_EXPANDED or
                    any(m.compress_type != zipfile.ZIP_STORED or m.flag_bits & 1 for m in members)):
                raise ValueError('Puck checkpoint archive members/size differ')
            for name, expected in SHAPES.items():
                with archive.open(name+'.npy') as stream:
                    version = np.lib.format.read_magic(stream)
                    if version not in ((1, 0), (2, 0)):
                        raise ValueError('Unsupported puck numeric format')
                    header = (np.lib.format.read_array_header_1_0 if version == (1, 0)
                              else np.lib.format.read_array_header_2_0)
                    shape, fortran, dtype = header(stream)
                    if (shape != expected or dtype != np.float32 or fortran or
                            stream.tell() + dtype.itemsize * int(np.prod(shape)) != archive.getinfo(name+'.npy').file_size):
                        raise ValueError('Puck numeric header/content differs')
        with np.load(io.BytesIO(payload), allow_pickle=False) as archive:
            return validate_arrays({name: archive[name] for name in SHAPES})
    except (zipfile.BadZipFile, EOFError) as error:
        raise ValueError('Invalid bounded puck checkpoint') from error


def make_model(seed):
    if type(seed) is not int or seed not in SEEDS:
        raise ValueError('Only the three frozen puck training seeds are allowed')
    import numpy as np
    import torch
    if torch.__version__.split('+')[0] != '2.9.0' or np.__version__ != '2.2.5':
        raise ValueError('Pinned Torch 2.9.0 / NumPy 2.2.5 runtime required')
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        layers = []
        for before, after in ((9, 32), (32, 32), (32, 2)):
            layers.extend((torch.nn.Linear(before, after, device='cpu', dtype=torch.float32), torch.nn.Tanh()))
        return torch.nn.Sequential(*layers)


def actions(model, inputs):
    """Shared differentiable training/inference arithmetic; no clipping."""
    import torch
    if (not isinstance(inputs, torch.Tensor) or inputs.device.type != 'cpu' or
            inputs.dtype != torch.float32 or inputs.ndim != 2 or inputs.shape[1] != 9 or
            not len(inputs) or not torch.isfinite(inputs).all() or torch.any(inputs.abs() > 1) or
            torch.any((inputs[:, 6] != 0) & (inputs[:, 6] != 1)) or torch.any(inputs[:, 7] != 0) or
            torch.any((inputs[:, 8] != 0) & (inputs[:, 8] != 1))):
        raise ValueError('Expected bounded CPU float32[N,9] puck inputs')
    normalized = model(inputs)
    if (normalized.dtype != torch.float32 or normalized.shape != (len(inputs), 2) or
            not torch.isfinite(normalized).all() or torch.any(normalized.abs() > 1)):
        raise ValueError('Invalid normalized puck model output')
    return normalized.to(torch.float64) * .4


def predict(model, inputs):
    import numpy as np
    import torch
    if not isinstance(inputs, np.ndarray) or inputs.dtype != np.float32 or inputs.shape != (9,):
        raise ValueError('Expected one float32[9] puck decision')
    with torch.no_grad():
        return actions(model, torch.from_numpy(inputs.copy()).unsqueeze(0))[0].numpy().copy()


def read_bundle(directory, expected_report_sha256, repo_root, seed):
    """Validate exact completed artifacts before any Torch import; no data reread."""
    if type(seed) is not int or seed not in SEEDS:
        raise ValueError('Unknown puck model seed')
    directory = artifacts._safe_path(directory)
    paths = [directory/name for name in ('report.json', 'protocol.json', 'checkpoint.npz')]
    before = artifacts._fingerprint(paths)
    payloads = [artifacts._read(p, MAX_CHECKPOINT if p.suffix == '.npz' else 4*1024**2) for p in paths]
    if sha(payloads[0]) != expected_report_sha256:
        raise ValueError('Pinned puck training report differs')
    report, protocol = map(artifacts._json, payloads[:2])
    if (report.get('status') != 'completed' or report.get('training_completed') is not True or
            type(report.get('training_seed')) is not int or report['training_seed'] != seed or report.get('held_out_used') is not False or
            report.get('qualification_claims') != [] or report.get('finalization_errors') != [] or
            report.get('protocol_sha256') != sha(payloads[1]) or
            protocol.get('schema') != 'puck-training-v1' or
            protocol.get('learning_protocol_sha256') != puck_learning.PROTOCOL_SHA256 or
            type(protocol.get('training_seed')) is not int or protocol['training_seed'] != seed or
            protocol.get('learning') != puck_learning.load_protocol(repo_root)['learning']):
        raise ValueError('Completed fixed puck training lineage required')
    entries = report.get('files')
    expected = [{'path': p.name, 'sha256': sha(raw), 'bytes': len(raw)} for p, raw in zip(paths[1:], payloads[1:])]
    if entries != expected:
        raise ValueError('Puck checkpoint/protocol ledger differs')
    history = report.get('history')
    if (type(history) is not list or len(history) != 30 or
            any(type(r) is not dict or type(r.get('epoch')) is not int for r in history) or
            [r['epoch'] for r in history] != list(range(1, 31)) or
            any(type(r.get('dev_loss')) not in (int, float) or not math.isfinite(r['dev_loss']) or r['dev_loss'] < 0 for r in history) or
            report.get('selected_epoch') != min(history, key=lambda r: r['dev_loss'])['epoch']):
        raise ValueError('Earliest fixed recorded-dev minimum differs')
    for name in ('src/palimpsest/puck_model.py', 'src/palimpsest/puck_learning.py', 'src/palimpsest/puck_profile.py'):
        if sha(artifacts._read(Path(repo_root)/name, 1024**2)) != protocol.get('source_hashes', {}).get(name):
            raise ValueError('Puck runtime/source identity differs: ' + name)
    arrays = read_checkpoint(payloads[2])
    if artifacts._fingerprint(paths) != before:
        raise ValueError('Puck bundle changed during admission')
    return arrays, {'training_seed': seed, 'training_report_sha256': expected_report_sha256,
                    'checkpoint_sha256': sha(payloads[2]), 'protocol_sha256': sha(payloads[1]),
                    'learning_protocol_sha256': puck_learning.PROTOCOL_SHA256,
                    'supervisor_source_sha256': protocol['source_hashes']['src/palimpsest/puck_learning.py']}


def load_model(directory, expected_report_sha256, repo_root, seed):
    arrays, identity = read_bundle(directory, expected_report_sha256, repo_root, seed)
    model = make_model(seed)
    import torch
    model.load_state_dict({name: torch.from_numpy(value) for name, value in arrays.items()}, strict=True)
    model.eval().requires_grad_(False)
    return model, identity
