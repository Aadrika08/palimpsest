"""One fixed CPU puck training seed; prepare-only never imports Torch.

Actual invocation requires an exclusive seed-N output and a separately reviewed
bounded supervisor. This script never starts collection or opens held-out data.
"""
import argparse
import hashlib
import importlib.metadata
import math
import os
from pathlib import Path
import platform
import sys
import time

from palimpsest import artifacts, puck_learning, puck_model
from palimpsest.storage import StorageBudget, StorageLimits

SOURCE_FILES = ('scripts/train_puck.py', 'src/palimpsest/puck_model.py',
    'src/palimpsest/puck_learning.py', 'src/palimpsest/puck_profile.py',
    'src/palimpsest/artifacts.py', 'src/palimpsest/records.py', 'src/palimpsest/storage.py',
    puck_learning.PROTOCOL_PATH, 'docs/plans/m6-puck-pushing-protocol-v5.json')


def file_sha(path):
    with artifacts._safe_path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def prepare(root, collection_path, expected_sha256, seed):
    import numpy as np
    if type(seed) is not int or seed not in puck_model.SEEDS:
        raise ValueError('Only the three frozen training seeds are allowed')
    root, collection_path = artifacts._safe_path(root), artifacts._safe_path(collection_path)
    spec = puck_learning.load_protocol(root)
    raw = artifacts._read(collection_path, spec['limits']['report_bytes'])
    if puck_model.sha(raw) != expected_sha256:
        raise ValueError('Collection report hash differs')
    report = artifacts._json(raw)
    if (report.get('status') != 'passed' or report.get('admission', {}).get('status') != 'passed' or
            report.get('learning_protocol_sha256') != puck_learning.PROTOCOL_SHA256):
        raise ValueError('Passed frozen teacher collection/admission required')
    batch = puck_learning.admit_batch(report.get('sources'), root)
    if batch['status'] != 'passed':
        raise ValueError('Independent full teacher batch admission failed')
    data = {}
    for split, maximum in (('train', 9600), ('recorded_dev', 2400)):
        rows = [r for r in batch['data'] if r['split'] == split]
        inputs = np.concatenate([r['inputs'] for r in rows])
        targets = np.concatenate([r['targets'] for r in rows])
        if not 1 <= len(inputs) <= maximum or targets.dtype != np.float64:
            raise ValueError('Fixed split size/target precision differs')
        data[split] = (inputs, targets)
    sources = [{**{key: item[key] for key in ('seed', 'split', 'ticks', 'manifest_sha256',
                    'source_hashes', 'feature_sha256', 'target_sha256')}, 'path': entry['path']}
               for entry, item in zip(report['sources'], batch['data'], strict=True)]
    protocol = {'schema': 'puck-training-v1', 'learning_protocol_sha256': puck_learning.PROTOCOL_SHA256,
        'training_seed': seed, 'learning': spec['learning'], 'action_arithmetic': spec['action_arithmetic'],
        'checkpoint': 'six finite float32 parameter arrays; uncompressed NPZ; no pickle',
        'collection_report': {'path': str(collection_path), 'sha256': expected_sha256}, 'sources': sources,
        'source_hashes': {name: file_sha(root/name) for name in SOURCE_FILES},
        'limits': {'per_seed': spec['limits']['training_per_seed'],
                   'all_training_bytes': spec['limits']['all_training_bytes'],
                   'min_free_bytes': spec['limits']['min_free_bytes']},
        'runtime': {'python': platform.python_version(), 'numpy': np.__version__,
                    'torch_distribution': importlib.metadata.version('torch')},
        'held_out_used': False, 'qualification_claims': [],
        'scope': 'Hybrid fixed phase memory plus learned continuous actions; recorded-input imitation only.'}
    check_sources(root, protocol)
    return data, protocol


def check_sources(root, protocol):
    for name, expected in protocol['source_hashes'].items():
        if file_sha(Path(root)/name) != expected:
            raise ValueError('Training code/protocol changed: ' + name)
    receipt = protocol['collection_report']
    if file_sha(receipt['path']) != receipt['sha256']:
        raise ValueError('Collection report changed after admission')
    for source in protocol['sources']:
        for name, expected in source['source_hashes'].items():
            if file_sha(Path(source['path'])/name) != expected:
                raise ValueError('Teacher source changed after admission')


def loss(actions, targets):
    import torch
    if (targets.dtype != torch.float64 or targets.device.type != 'cpu' or targets.shape != actions.shape or
            not torch.isfinite(targets).all() or torch.any(targets.abs() > .4)):
        raise ValueError('Finite float64 teacher targets required')
    return ((actions-targets)/.4).square().mean()


def fit(data, seed, deadline):
    """Frozen 30-epoch procedure; no epoch/hyperparameter override or held-out path."""
    import torch
    model = puck_model.make_model(seed)
    train_x, train_y = map(torch.from_numpy, data['train'])
    dev_x, dev_y = map(torch.from_numpy, data['recorded_dev'])
    optimizer = torch.optim.Adam(model.parameters(), lr=.001, weight_decay=0.)
    generator = torch.Generator(device='cpu').manual_seed(seed)
    history, best, selected, saved = [], math.inf, None, None
    def deadline_check():
        if time.monotonic() >= deadline:
            raise TimeoutError('Puck training exceeded fixed 120-second internal limit')
    for epoch in range(1, 31):
        model.train(); total = 0.
        order = torch.randperm(len(train_x), generator=generator)
        for indices in order.split(64):
            deadline_check(); optimizer.zero_grad(set_to_none=True)
            value = loss(puck_model.actions(model, train_x[indices]), train_y[indices])
            if not torch.isfinite(value):
                raise ValueError('Nonfinite puck training loss')
            value.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(p).all() for p in model.parameters()):
                raise ValueError('Nonfinite puck parameter after optimizer step')
            total += float(value.detach()) * len(indices)
        model.eval(); dev_total = 0.
        with torch.no_grad():
            for start in range(0, len(dev_x), 64):
                deadline_check()
                value = loss(puck_model.actions(model, dev_x[start:start+64]), dev_y[start:start+64])
                if not torch.isfinite(value):
                    raise ValueError('Nonfinite recorded-dev loss')
                dev_total += float(value) * len(dev_x[start:start+64])
        dev_loss = dev_total / len(dev_x)
        history.append({'epoch': epoch, 'train_ticks': len(train_x), 'train_loss': total/len(train_x),
                        'dev_ticks': len(dev_x), 'dev_loss': dev_loss})
        if dev_loss < best:
            best, selected = dev_loss, epoch
            saved = {name: value.detach().cpu().numpy().copy() for name, value in model.state_dict().items()}
    deadline_check()
    return saved, {'selected_epoch': selected, 'history': history}


def publish_report(output, report, budget, remaining, deadline):
    """Publish only fully synced bytes; a failed staging file is never loadable."""
    payload = puck_model.canonical(report)
    if len(payload) > min(4*1024**2, remaining):
        raise ValueError('Puck report byte limit exceeded')
    target, staging = output/'report.json', output/'report.pending'
    if target.exists():
        raise FileExistsError(target)
    budget.check(len(payload), path=staging)
    with staging.open('xb') as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    if report['status'] == 'completed' and time.monotonic() >= deadline:
        raise TimeoutError('Puck report staging exceeded internal limit')
    # The fresh output directory has one writer under the existing storage lease.
    staging.replace(target)


def train(root, output, data, protocol):
    root, output = artifacts._safe_path(root), artifacts._safe_path(output)
    if (output.name != f"seed-{protocol['training_seed']}" or not output.is_relative_to(root/'runs') or
            any(output.is_relative_to(Path(s['path']).parent) or Path(s['path']).is_relative_to(output)
                for s in protocol['sources'])):
        raise ValueError('Exclusive runs/.../seed-N output outside teacher owners required')
    limits = protocol['limits']; maximum = limits['per_seed']['bytes']
    budget = StorageBudget((output.parent,), StorageLimits(max_bytes=limits['all_training_bytes'],
                           min_free_bytes=limits['min_free_bytes']))
    with budget.lock():
        budget.check(maximum, path=output); output.mkdir(exist_ok=False)
        ledger = []; written = 0
        def write(name, payload):
            nonlocal written
            cap = puck_model.MAX_CHECKPOINT if name.endswith('.npz') else 4*1024**2
            if len(payload) > cap or written+len(payload) > maximum:
                raise ValueError('Puck training output limit exceeded')
            path = output/name; budget.check(len(payload), path=path)
            with path.open('xb') as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            written += len(payload)
            ledger.append({'path': name, 'sha256': puck_model.sha(payload), 'bytes': len(payload)})
        report = {'status': 'failed', 'training_completed': False, 'training_seed': protocol['training_seed'],
                  'protocol_sha256': puck_model.sha(puck_model.canonical(protocol)),
                  'held_out_used': False, 'qualification_claims': [], 'finalization_errors': []}
        started = time.monotonic()
        try:
            check_sources(root, protocol)
            write('protocol.json', puck_model.canonical(protocol))
            arrays, result = fit(data, protocol['training_seed'], started+120)
            payload = puck_model.checkpoint_bytes(arrays)
            puck_model.read_checkpoint(payload)
            write('checkpoint.npz', payload)
            report.update(result, status='completed', training_completed=True)
        except BaseException as error:
            report['error'] = {'type': type(error).__name__, 'message': str(error)[:2048]}
        finally:
            try:
                check_sources(root, protocol)
                if time.monotonic()-started >= 120:
                    raise TimeoutError('Puck training finalization exceeded internal limit')
            except BaseException as error:
                report.update(status='failed', training_completed=False)
                report['finalization_errors'].append({'type': type(error).__name__, 'message': str(error)[:2048]})
            report['elapsed_seconds_before_report_staging'] = time.monotonic()-started
            report['files'] = list(ledger)
            publish_report(output, report, budget, maximum-written, started+120)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--collection-report', type=Path, required=True)
    parser.add_argument('--collection-sha256', required=True)
    parser.add_argument('--seed', type=int, choices=puck_model.SEEDS, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if not args.prepare_only and args.output is None:
        parser.error('Actual training requires an exclusive --output')
    try:
        data, protocol = prepare(args.repo, args.collection_report, args.collection_sha256, args.seed)
        report = ({'status': 'prepared', 'training_performed': False, 'protocol': protocol,
                   'protocol_sha256': puck_model.sha(puck_model.canonical(protocol))} if args.prepare_only else
                  train(args.repo, args.output, data, protocol))
        print(puck_model.canonical(report).decode())
        return 0 if report['status'] in ('prepared', 'completed') else 1
    except (ValueError, OSError, RuntimeError) as error:
        print(puck_model.canonical({'status': 'failed', 'error': str(error)[:2048]}).decode(), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
