"""One fixed train-only weighting experiment; historical puck admission is unchanged."""
import math
from pathlib import Path

from . import artifacts, puck_learning, puck_model

PROTOCOL_PATH = 'docs/plans/m6-puck-balanced-loss-v1.json'
PROTOCOL_SHA256 = 'e21431626c59b2430d4eb0583d6f62f54dd9b2e9c3847c8bea06255528b34828'
SCHEMA = 'puck-balanced-training-v1'
COUNTS = (381, 578, 944, 170, 478, 3159, 0)
SOURCE_FILES = ('src/palimpsest/puck_balanced.py', PROTOCOL_PATH)


def load_protocol(root):
    raw = artifacts._read(Path(root)/PROTOCOL_PATH, 16*1024)
    if puck_model.sha(raw) != PROTOCOL_SHA256:
        raise ValueError('Frozen balanced objective differs')
    spec = artifacts._json(raw)
    base = puck_learning.load_protocol(root)
    if (spec['base_learning_protocol']['sha256'] != puck_learning.PROTOCOL_SHA256 or
            spec['task_protocol'] != base['task_protocol']):
        raise ValueError('Balanced base learning/task identity differs')
    return spec


def stratum_ids(inputs, targets):
    """Exact BEFORE phase and actual float64 label partition; no dev-dependent rule."""
    import numpy as np
    if (not isinstance(inputs, np.ndarray) or inputs.dtype != np.float32 or
            inputs.ndim != 2 or inputs.shape[1] != 9 or not 1 <= len(inputs) <= 9600 or
            not np.isfinite(inputs).all() or np.any(np.abs(inputs) > 1) or
            np.any((inputs[:, 6] != 0) & (inputs[:, 6] != 1)) or np.any(inputs[:, 7] != 0) or
            np.any((inputs[:, 8] != 0) & (inputs[:, 8] != 1)) or
            not isinstance(targets, np.ndarray) or targets.dtype != np.float64 or
            targets.shape != (len(inputs), 2) or not np.isfinite(targets).all() or
            np.any(np.abs(targets) > .4)):
        raise ValueError('Finite fixed puck features/float64 targets required')
    stop = np.all(targets == 0, axis=1)
    regime = np.where(targets[:, 0] == 0, 0, np.where(targets[:, 0] > 0, 1, 2))
    return np.where(stop, 0, 1 + 3*inputs[:, 8].astype(np.uint8) + regime).astype(np.uint8)


def row_weights(inputs, targets):
    import numpy as np
    ids = stratum_ids(inputs, targets)
    if tuple(np.bincount(ids, minlength=7)) != COUNTS:
        raise ValueError('Exact six training-stratum counts required')
    values = np.array([5710/(6*n) if n else 0. for n in COUNTS], np.float64)
    return values[ids]


def batch_mean(row_losses, weights):
    """Shared NumPy/Torch arithmetic: mean of weighted rows, never weight-normalized."""
    if row_losses.ndim != 1 or weights.shape != row_losses.shape or not len(row_losses):
        raise ValueError('One weight per nonempty loss row required')
    return (row_losses * weights).mean()


def validate_protocol(protocol, root):
    """Admit only this experiment identity; base teacher protocol is not rewritten."""
    spec = load_protocol(root)
    base = puck_learning.load_protocol(root)
    expected_limits = {'per_seed': base['limits']['training_per_seed'],
                       'all_training_bytes': base['limits']['all_training_bytes'],
                       'min_free_bytes': base['limits']['min_free_bytes']}
    if (type(protocol) is not dict or protocol.get('schema') != SCHEMA or type(protocol.get('training_seed')) is not int or
            protocol['training_seed'] not in puck_model.SEEDS or
            protocol.get('balanced_objective') != {'path': PROTOCOL_PATH, 'sha256': PROTOCOL_SHA256} or
            puck_model.canonical(protocol.get('training_objective')) != puck_model.canonical(spec['objective']) or
            puck_model.canonical(protocol.get('strata')) != puck_model.canonical(spec['strata']) or
            protocol.get('learning_protocol_sha256') != puck_learning.PROTOCOL_SHA256 or
            puck_model.canonical(protocol.get('learning')) != puck_model.canonical(base['learning']) or
            puck_model.canonical(protocol.get('action_arithmetic')) != puck_model.canonical(base['action_arithmetic']) or
            puck_model.canonical(protocol.get('limits')) != puck_model.canonical(expected_limits) or
            type(protocol.get('collection_report')) is not dict or type(protocol.get('source_hashes')) is not dict or
            protocol.get('collection_report', {}).get('sha256') != spec['collection_report_sha256'] or
            protocol.get('held_out_used') is not False or protocol.get('qualification_claims') != []):
        raise ValueError('Fixed balanced training identity differs')
    sources = protocol.get('sources')
    if (not isinstance(sources, list) or len(sources) != 20 or any(type(s) is not dict for s in sources) or
            [(s.get('seed'), s.get('split')) for s in sources] !=
            [(s, 'train' if s < 6016 else 'recorded_dev') for s in range(6000, 6020)] or
            any(type(s.get('seed')) is not int or type(s.get('ticks')) is not int for s in sources) or
            sum(s['ticks'] for s in sources[:16]) != 5710 or sum(s['ticks'] for s in sources[16:]) != 1314):
        raise ValueError('Fixed balanced train/dev sources differ')
    for name in ('src/palimpsest/puck_model.py', 'src/palimpsest/puck_learning.py',
                 'src/palimpsest/puck_profile.py', *SOURCE_FILES):
        if puck_model.sha(artifacts._read(Path(root)/name, 1024**2)) != protocol.get('source_hashes', {}).get(name):
            raise ValueError('Balanced numerical/objective source differs: ' + name)
    return spec


def read_bundle(directory, expected_report_sha256, root, seed):
    """Separate fixed experiment reader; default puck_model.read_bundle rejects its schema."""
    if type(seed) is not int or seed not in puck_model.SEEDS:
        raise ValueError('Unknown balanced model seed')
    directory = artifacts._safe_path(directory)
    paths = [directory/name for name in ('report.json', 'protocol.json', 'checkpoint.npz')]
    before = artifacts._fingerprint(paths)
    raw = [artifacts._read(p, puck_model.MAX_CHECKPOINT if p.suffix == '.npz' else 4*1024**2) for p in paths]
    if puck_model.sha(raw[0]) != expected_report_sha256:
        raise ValueError('Pinned balanced report differs')
    report, protocol = map(artifacts._json, raw[:2])
    validate_protocol(protocol, root)
    if (report.get('status') != 'completed' or report.get('training_completed') is not True or
            type(report.get('training_seed')) is not int or report['training_seed'] != seed or
            protocol['training_seed'] != seed or report.get('held_out_used') is not False or
            report.get('qualification_claims') != [] or report.get('finalization_errors') != [] or
            report.get('protocol_sha256') != puck_model.sha(raw[1]) or
            report.get('training_objective_sha256') != PROTOCOL_SHA256):
        raise ValueError('Completed balanced report/protocol required')
    expected = [{'path': p.name, 'sha256': puck_model.sha(payload), 'bytes': len(payload)}
                for p, payload in zip(paths[1:], raw[1:])]
    if report.get('files') != expected:
        raise ValueError('Balanced artifact ledger differs')
    history = report.get('history')
    if (not isinstance(history, list) or len(history) != 30 or
            any(type(r) is not dict or type(r.get('epoch')) is not int or r['epoch'] != i or
                type(r.get('train_ticks')) is not int or r['train_ticks'] != 5710 or
                type(r.get('dev_ticks')) is not int or r['dev_ticks'] != 1314 or 'train_loss' in r or
                any(type(r.get(k)) not in (int, float) or not math.isfinite(r[k]) or r[k] < 0
                    for k in ('weighted_train_loss', 'dev_loss')) for i, r in enumerate(history, 1)) or
            type(report.get('selected_epoch')) is not int or
            report['selected_epoch'] != min(history, key=lambda r: r['dev_loss'])['epoch']):
        raise ValueError('Thirty weighted histories and earliest unweighted dev minimum required')
    arrays = puck_model.read_checkpoint(raw[2])
    if artifacts._fingerprint(paths) != before:
        raise ValueError('Balanced bundle changed during admission')
    return arrays, {'training_seed': seed, 'training_report_sha256': expected_report_sha256,
                    'checkpoint_sha256': puck_model.sha(raw[2]), 'protocol_sha256': puck_model.sha(raw[1]),
                    'training_objective_sha256': PROTOCOL_SHA256,
                    'learning_protocol_sha256': puck_learning.PROTOCOL_SHA256}
