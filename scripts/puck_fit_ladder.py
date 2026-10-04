"""Bounded retained-data puck probes: EXPLORATORY — not gate evidence.

Prospective rules: reproduce all three historical seeds before exploration;
every epoch loss and selected response must agree within absolute 1e-6, otherwise
stop this track. Explore conditioned32/30, longer32/300, capacity256/300 in that
order, all seeds21/22/23, earliest strict recorded-dev minimum, no winning seed.
Each seed requires dev normalized MSE<=.01, approach turn-only |v|>.05 leak<=5%,
and heading-sign agreement>=95% (exclude exactly zero target headings). Empty
required strata are ineligible. Choose the first all-seed passing neural rung.
If time remains run train-only standardized 1NN as a diagnostic; its success is
a question, never runtime promotion or proof of classification/horizon causality.
No resplit, reserve access, collection, native execution, GPU, retry, or cap
extension. Incomplete candidates remain incomplete; qualification_claims=[].
"""
import argparse
import hashlib
import io
import math
import os
from pathlib import Path
import sys
import time

from palimpsest import artifacts, puck_balanced, puck_model, puck_profile
from palimpsest.storage import StorageBudget, StorageLimits
import train_puck

SCHEMA = 'exploratory-puck-fit-ladder-v1'
COLLECTION_SHA = '3cf5044ac12fa80ebfed9aa044d0e983a94fcddb4e177da779a4684b944b518b'
ORIGINAL_SHAS = ('70683df96f286c54311ed678d61beef7c929744d43d0116be792656e99f30205',
                 '956106fe819d3c0da7115141223b1af328f5ca524932e2b8775c0bf86c6fdc0a',
                 '3db238c42b635b20ae4c0eba66f6d5048007851076070072c5bca0fabd7ed924')
RUNGS = (('conditioned32', 32, 30, False), ('longer32', 32, 300, True),
         ('capacity256', 256, 300, True))
SOURCE_FILES = (*train_puck.SOURCE_FILES, 'src/palimpsest/puck_balanced.py',
                'scripts/puck_fit_ladder.py', 'docs/plans/research-capability-phase.md')


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('Stage deadline exhausted; no retry or cap extension')


def guard_output(output, protected):
    if any(output.is_relative_to(p) or p.is_relative_to(output) for p in protected):
        raise ValueError('Output overlaps immutable input owner')


def check_split(sources):
    expected = [(s, 'train' if s < 6016 else 'recorded_dev') for s in range(6000, 6020)]
    if (not isinstance(sources, list) or len(sources) != 20 or
            any(type(s) is not dict or type(s.get('seed')) is not int for s in sources) or
            [(s.get('seed'), s.get('split')) for s in sources] != expected):
        raise ValueError('Only exact retained train6000-6015 / recorded-dev6016-6019 allowed')


def validate_data(data):
    if set(data) != {'train', 'recorded_dev'}:
        raise ValueError('Only retained train and recorded_dev arrays allowed')
    for x, y in data.values():
        puck_balanced.stratum_ids(x, y)  # Includes CPU feature guards and finite checks.
        x.setflags(write=False); y.setflags(write=False)


def statistics(x):
    import numpy as np
    mean, scale = np.zeros(9, np.float32), np.ones(9, np.float32)
    mean[:6] = x[:, :6].mean(axis=0, dtype=np.float64)
    sigma = x[:, :6].std(axis=0, dtype=np.float64)
    scale[:6] = np.where(sigma == 0, 1, sigma)
    if not np.isfinite(mean).all() or not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError('Invalid train-only normalization statistics')
    return mean, scale


def make_model(seed, width, mean, scale):
    import torch
    historical = puck_model.make_model(seed)  # Enforces pinned runtime/CPU/one thread.
    if width == 32:
        network = historical
    elif width == 256:
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            network = torch.nn.Sequential(torch.nn.Linear(9, width, device='cpu', dtype=torch.float32), torch.nn.Tanh(),
                torch.nn.Linear(width, width, device='cpu', dtype=torch.float32), torch.nn.Tanh(),
                torch.nn.Linear(width, 2, device='cpu', dtype=torch.float32), torch.nn.Tanh())
    else:
        raise ValueError('Only approved widths32/256')

    class Conditioned(torch.nn.Module):
        def __init__(self):
            super().__init__(); self.network = network
            self.register_buffer('mean', torch.tensor(mean, dtype=torch.float32))
            self.register_buffer('scale', torch.tensor(scale, dtype=torch.float32))

        def forward(self, raw):
            return self.network((raw-self.mean)/self.scale)
    return Conditioned()


def responses(model, x, deadline=None):
    import numpy as np
    import torch
    result = []
    with torch.no_grad():
        for start in range(0, len(x), 64):
            if deadline is not None:
                check_deadline(deadline)
            result.append(puck_model.actions(model, torch.from_numpy(x[start:start+64].copy())).numpy())
    return np.concatenate(result)


def folded_export(model, x, deadline=None):
    import numpy as np
    import torch
    arrays = {k: v.detach().numpy().copy() for k, v in model.network.state_dict().items()}
    mean, scale = model.mean.numpy(), model.scale.numpy()
    weight = arrays['0.weight'].copy()
    arrays['0.weight'] = (weight/scale).astype(np.float32)
    arrays['0.bias'] = (arrays['0.bias']-weight@(mean/scale)).astype(np.float32)
    puck_model.validate_arrays(arrays)
    folded = puck_model.make_model(21)
    folded.load_state_dict({k: torch.from_numpy(v) for k, v in arrays.items()})
    parity = float(np.max(np.abs(responses(model, x, deadline)-responses(folded, x, deadline))))
    if parity > 1e-6:
        raise ValueError('Folded float32 export response parity exceeds1e-6')
    return arrays, parity


def metrics(x, y, prediction):
    import numpy as np
    if prediction.shape != y.shape or not np.isfinite(prediction).all() or np.any(np.abs(prediction) > .4):
        raise ValueError('Finite bounded action predictions required')
    ids = puck_balanced.stratum_ids(x, y)
    turn = ids == 1; heading = y[:, 1] != 0
    mse = float(np.mean(((prediction-y)/.4)**2))
    leak = float(np.mean(np.abs(prediction[turn, 0]) > .05)) if turn.any() else None
    sign = float(np.mean(np.sign(prediction[heading, 1]) == np.sign(y[heading, 1]))) if heading.any() else None
    return {'normalized_mse': mse, 'approach_turn_only_count': int(turn.sum()),
            'approach_turn_only_leak': leak, 'nonzero_target_heading_count': int(heading.sum()),
            'heading_sign_agreement': sign, 'stratum_counts': np.bincount(ids, minlength=7).tolist(),
            'gate_denominators': {'approach_turn_only': int(turn.sum()), 'nonzero_target_heading': int(heading.sum())},
            'push_negative_status': 'observed' if np.any(ids == 6) else 'untested — empty retained stratum',
            'stratum_normalized_mse': [float(np.mean(((prediction[ids == i]-y[ids == i])/.4)**2))
                                      if np.any(ids == i) else None for i in range(7)],
            'eligible': bool(mse <= .01 and leak is not None and leak <= .05 and sign is not None and sign >= .95)}


def fit_probe(data, seed, width, epochs, cosine, deadline):
    check_deadline(deadline)
    import numpy as np
    import torch
    mean, scale = statistics(data['train'][0]); model = make_model(seed, width, mean, scale)
    x, y = (torch.from_numpy(a.copy()) for a in data['train'])
    optimizer = torch.optim.Adam(model.parameters(), lr=.001, weight_decay=0.)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(1, epochs-1), eta_min=.00001) if cosine else None
    generator = torch.Generator(device='cpu').manual_seed(seed)
    history, best, saved, selected = [], math.inf, None, None
    for epoch in range(1, epochs+1):
        model.train(); total = 0.; lr = optimizer.param_groups[0]['lr']
        for indices in torch.randperm(len(x), generator=generator).split(64):
            check_deadline(deadline); optimizer.zero_grad(set_to_none=True)
            value = train_puck.loss(puck_model.actions(model, x[indices]), y[indices])
            if not torch.isfinite(value):
                raise ValueError('Nonfinite probe loss')
            value.backward(); torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True)
            optimizer.step(); total += float(value.detach())*len(indices)
            if any(not torch.isfinite(p).all() for p in model.parameters()):
                raise ValueError('Nonfinite probe parameter')
        model.eval()
        dev = metrics(*data['recorded_dev'], responses(model, data['recorded_dev'][0], deadline))
        history.append({'epoch': epoch, 'online_train_loss': total/len(x), 'dev_loss': dev['normalized_mse'], 'lr': lr})
        if dev['normalized_mse'] < best:
            best, selected = dev['normalized_mse'], epoch
            saved = {k: v.detach().clone() for k, v in model.network.state_dict().items()}
        if scheduler and epoch < epochs:
            scheduler.step()
    model.network.load_state_dict(saved); model.eval()
    arrays = {k: v.numpy().copy() for k, v in saved.items()}
    result = {'selected_epoch': selected, 'history': history,
              'selected_checkpoint_train_loss': metrics(*data['train'], responses(model, data['train'][0], deadline))['normalized_mse'],
              'dev': metrics(*data['recorded_dev'], responses(model, data['recorded_dev'][0], deadline))}
    return arrays, result, model


def nearest_neighbor(data, deadline, *, memory_bytes=32*1024**2):
    """Train references only; <=memory_bytes temporary squared-distance matrix."""
    import numpy as np
    check_deadline(deadline)
    mean, scale = statistics(data['train'][0])
    train = ((data['train'][0]-mean)/scale).astype(np.float64)
    dev = ((data['recorded_dev'][0]-mean)/scale).astype(np.float64)
    if memory_bytes < 16*len(train):
        raise ValueError('1NN distance budget cannot fit one dev row')
    # Reserve two matrices for einsum/matmul arithmetic, plus bounded feature arrays.
    chunk = max(1, min(64, memory_bytes//(16*len(train))))
    result = []; norm = np.sum(train*train, axis=1)
    for start in range(0, len(dev), chunk):
        check_deadline(deadline); rows = dev[start:start+chunk]
        distances = rows@train.T
        distances *= -2; distances += norm; distances += np.sum(rows*rows, axis=1)[:, None]
        result.append(data['train'][1][np.argmin(distances, axis=1)].copy())
    check_deadline(deadline)
    return np.concatenate(result)


def reconstruct_labels(x, deadline):
    """Scoped reconstruction from finite sensor geometry and BEFORE mode.

    Rotate/translate a canonical world to satisfy the existing teacher arena
    guards. Float32 projection may lose boundary precision; report residuals,
    never infer privileged-state observability outside these retained rows.
    """
    import numpy as np
    result, unsupported = [], []
    for index, row in enumerate(x):
        if index % 64 == 0:
            check_deadline(deadline)
        points = np.array([[0, 0], row[:2].astype(np.float64)*14, row[2:4].astype(np.float64)*14])
        found = None
        for angle in (0., *(i*math.pi/180 for i in range(1, 180))):
            c, s = math.cos(angle), math.sin(angle)
            rotated = points@np.array([[c, s], [-s, c]])
            if np.all(np.ptp(rotated, axis=0) <= 10):
                rotated -= (rotated.max(axis=0)+rotated.min(axis=0))/2
                found = (angle, rotated); break
        if found is None:
            unsupported.append(index); result.append([0., 0.]); continue
        angle, points = found
        velocity = row[4:6].astype(np.float64)*2
        world = {'time_s': 0., 'rover_pose': [*points[0].tolist(), angle],
                 'puck_xyz': [*points[1].tolist(), .062], 'goal_xy': points[2].tolist(),
                 'puck_velocity_xy': [float(c*velocity[0]-s*velocity[1]), float(s*velocity[0]+c*velocity[1])]}
        try:
            result.append(puck_profile.demonstrate(world, 'push' if row[8] else 'approach')[0])
        except ValueError:
            # Canonical reconstruction cannot relax the existing world's guards.
            unsupported.append(index); result.append([0., 0.])
    return np.asarray(result, np.float64), unsupported


def audit(data, deadline):
    import numpy as np
    mean, scale = statistics(data['train'][0]); constant = data['train'][1].mean(axis=0)
    output = {'train_mean': mean.tolist(), 'train_scale': scale.tolist(),
              'constant_sigma_one': np.flatnonzero(data['train'][0][:, :6].std(axis=0, dtype=np.float64) == 0).tolist(),
              'reconstruction_scope': 'Existing teacher on canonical worlds from nine float32 inputs and BEFORE mode; finite retained rows only.',
              'panels': {}}
    groups = {}
    for split, (x, y) in data.items():
        reconstructed, unsupported = reconstruct_labels(x, deadline)
        supported = np.ones(len(x), bool); supported[unsupported] = False
        residual = np.abs(reconstructed[supported]-y[supported])
        panel = {'ticks': len(x), 'feature_min': x.min(axis=0).tolist(), 'feature_max': x.max(axis=0).tolist(),
                 'feature_std': x.std(axis=0, dtype=np.float64).tolist(),
                 'training_constant_baseline': metrics(x, y, np.tile(constant, (len(x), 1))),
                 'reconstruction_unsupported_rows': unsupported,
                 'reconstruction_max_abs': float(residual.max()) if len(residual) else None,
                 'reconstruction_mean_abs': float(residual.mean()) if len(residual) else None,
                 'reconstruction_rows_over_1e-6': int(np.any(residual > 1e-6, axis=1).sum()),
                 'reconstructed_labels': metrics(x[supported], y[supported], reconstructed[supported]) if supported.any() else None}
        for row, target in zip(x, y):
            canonical = row.astype('<f4', copy=True); canonical[canonical == 0] = 0
            groups.setdefault(canonical.tobytes(), []).append((split, target))
        output['panels'][split] = panel
    duplicate = [values for values in groups.values() if len(values) > 1]
    output['duplicates'] = {'canonical_features': 'little-endian float32, signed zero canonicalized',
        'groups': len(duplicate), 'rows': sum(len(g) for g in duplicate),
        'cross_split_groups': sum(len({s for s, _ in g}) > 1 for g in duplicate),
        'conflicting_target_groups_over_1e-6': sum(bool(np.ptp(np.stack([y for _, y in g]), axis=0).max() > 1e-6) for g in duplicate)}
    return output


def compare_reproduction(actual, original, actual_response, original_response):
    import numpy as np
    if actual['selected_epoch'] != original['selected_epoch'] or len(actual['history']) != 30 or len(original['history']) != 30:
        raise ValueError('Historical selected epoch/history length differs')
    maximum = 0.
    for a, b in zip(actual['history'], original['history'], strict=True):
        if any(a[k] != b[k] for k in ('epoch', 'train_ticks', 'dev_ticks')):
            raise ValueError('Historical epoch/split differs')
        for key in ('train_loss', 'dev_loss'):
            difference = abs(a[key]-b[key]); maximum = max(maximum, difference)
            if not math.isfinite(difference) or difference > 1e-6:
                raise ValueError('Historical every-epoch loss differs: '+key)
    if actual_response.shape != original_response.shape:
        raise ValueError('Historical response shape differs')
    response_error = float(np.max(np.abs(actual_response-original_response)))
    if not math.isfinite(response_error) or response_error > 1e-6:
        raise ValueError('Historical selected-checkpoint responses differ')
    return {'max_epoch_loss_abs_difference': maximum, 'max_response_abs_difference': response_error}


def require_receipt(receipt, identity):
    if (receipt.get('schema') != SCHEMA or receipt.get('stage') != 'reproduce' or receipt.get('status') != 'passed' or
            receipt.get('identity') != identity or receipt.get('held_out_used') is not False or
            receipt.get('qualification_claims') != [] or
            [(r.get('seed'), r.get('status')) for r in receipt.get('results', [])] != [(s, 'passed') for s in puck_model.SEEDS]):
        raise ValueError('Exact passed all-three-seed reproduction receipt required')


def admit(args, deadline):
    check_deadline(deadline)
    if args.collection_sha256 != COLLECTION_SHA:
        raise ValueError('Exact admitted retained collection hash required')
    collection = artifacts._json(artifacts._read(args.collection_report, 4*1024**2))
    if train_puck.file_sha(args.collection_report) != COLLECTION_SHA:
        raise ValueError('Collection report hash differs')
    check_split(collection.get('sources'))  # Refuse reserve IDs before prepare opens recordings.
    data, protocol = train_puck.prepare(args.repo, args.collection_report, COLLECTION_SHA, 21)
    validate_data(data); check_split(protocol['sources'])
    if [len(data[s][0]) for s in ('train', 'recorded_dev')] != [5710, 1314]:
        raise ValueError('Retained 5710 train / 1314 recorded-dev ticks required')
    originals, bundles = {}, []
    for seed, report_sha in zip(puck_model.SEEDS, ORIGINAL_SHAS, strict=True):
        check_deadline(deadline); directory = args.training_root/f'seed-{seed}'
        arrays, identity = puck_model.read_bundle(directory, report_sha, args.repo, seed)
        originals[seed] = (arrays, artifacts._json(artifacts._read(directory/'report.json', 4*1024**2)))
        bundles.append(identity)
    identity = {'collection_report_sha256': COLLECTION_SHA, 'sources': protocol['sources'],
                'source_hashes': {name: train_puck.file_sha(args.repo/name) for name in SOURCE_FILES},
                'data_hashes': {s: [puck_model.sha(a.tobytes()) for a in pair] for s, pair in data.items()},
                'original_bundles': bundles, 'runtime': protocol['runtime']}
    check_deadline(deadline)
    return data, protocol, originals, identity


def bounded_sha(path, deadline):
    check_deadline(deadline)
    digest = hashlib.sha256()
    with artifacts._safe_path(path).open('rb') as stream:
        while True:
            check_deadline(deadline)
            chunk = stream.read(1024**2)
            if not chunk:
                break
            digest.update(chunk)
    check_deadline(deadline)
    return digest.hexdigest()


def check_identity(args, protocol, identity, data, deadline):
    check_deadline(deadline)
    paths = [(args.repo/name, expected) for name, expected in protocol['source_hashes'].items()]
    paths.append((protocol['collection_report']['path'], protocol['collection_report']['sha256']))
    for source in protocol['sources']:
        paths.extend((Path(source['path'])/name, expected) for name, expected in source['source_hashes'].items())
    for path, expected in paths:
        if bounded_sha(path, deadline) != expected:
            raise ValueError('Admitted source changed: '+str(path))
    for name, expected in identity['source_hashes'].items():
        if bounded_sha(args.repo/name, deadline) != expected:
            raise ValueError('Runner source changed: '+name)
    for split, expected in identity['data_hashes'].items():
        check_deadline(deadline)
        if [puck_model.sha(a.tobytes()) for a in data[split]] != expected:
            raise ValueError('Admitted arrays changed')
    for seed, expected in zip(puck_model.SEEDS, identity['original_bundles'], strict=True):
        check_deadline(deadline)
        _, current = puck_model.read_bundle(args.training_root/f'seed-{seed}', expected['training_report_sha256'], args.repo, seed)
        if current != expected:
            raise ValueError('Original training bundle changed')
    check_deadline(deadline)


def run_stage(args, data, originals, deadline, write, results):
    import numpy as np
    if args.stage == 'reproduce':
        if not results:
            results.extend({'seed': s, 'status': 'unattempted'} for s in puck_model.SEEDS)
        for item in results:
            seed = item['seed']; item['status'] = 'incomplete'
            # Torch cannot enforce NumPy's read-only flag. Give the historical
            # arithmetic an owned working copy; retain/hash the admitted arrays.
            working = {split: tuple(a.copy() for a in pair) for split, pair in data.items()}
            arrays, result = train_puck.fit(working, seed, deadline)
            import torch
            old_arrays, old_result = originals[seed]
            model, old = puck_model.make_model(seed), puck_model.make_model(seed)
            model.load_state_dict({k: torch.from_numpy(v) for k, v in arrays.items()})
            old.load_state_dict({k: torch.from_numpy(v) for k, v in old_arrays.items()})
            differences = []
            for split, (x, _) in data.items():
                differences.append(compare_reproduction(result, old_result, responses(model, x, deadline), responses(old, x, deadline)))
            write(f'reproduction-seed-{seed}.npz', puck_model.checkpoint_bytes(arrays))
            item.update({'seed': seed, 'status': 'passed', **result, 'response_panels': differences,
                            'selected_checkpoint_train_loss': metrics(*data['train'], responses(model, data['train'][0], deadline))['normalized_mse'],
                            'dev': metrics(*data['recorded_dev'], responses(model, data['recorded_dev'][0], deadline))})
        return {'status': 'passed', 'results': results}
    selected = None
    if not results:
        results.extend({'name': name, 'width': w, 'epochs': e, 'cosine': c, 'status': 'unattempted',
                        'seeds': [{'seed': s, 'status': 'unattempted'} for s in puck_model.SEEDS]} for name, w, e, c in RUNGS)
    for rung in results:
        name, width, epochs, cosine = (rung[k] for k in ('name', 'width', 'epochs', 'cosine'))
        if selected is not None:
            rung['reason'] = 'Earlier neural rung passed all three seeds'; continue
        try:
            check_deadline(deadline)
            rung['status'] = 'incomplete'
            for item in rung['seeds']:
                seed = item['seed']; item['status'] = 'incomplete'
                arrays, result, model = fit_probe(data, seed, width, epochs, cosine, deadline)
                if width == 32:
                    all_x = np.concatenate([data[s][0] for s in ('train', 'recorded_dev')])
                    arrays, parity = folded_export(model, all_x, deadline)
                    payload = puck_model.checkpoint_bytes(arrays); result['folded_export_max_abs'] = parity
                else:
                    stream = io.BytesIO(); np.savez(stream, **arrays, mean=model.mean.numpy(), scale=model.scale.numpy())
                    payload = stream.getvalue()
                write(f'{name}-seed-{seed}.npz', payload)
                item.update({'seed': seed, 'status': 'completed', **result})
            rung['status'] = 'completed'; rung['all_seeds_eligible'] = all(s['dev']['eligible'] for s in rung['seeds'])
            if rung['all_seeds_eligible']:
                selected = name
        except TimeoutError as error:
            rung['reason'] = str(error)
            # Later rungs remain explicit unattempted, without redistributing time.
            for later in results[results.index(rung)+1:]:
                later['reason'] = 'Stage deadline exhausted'
            break
    diagnostic = {'status': 'unattempted', 'reason': 'Stage deadline exhausted', 'train_self_neighbor_scores_are_evidence': False}
    try:
        prediction = nearest_neighbor(data, deadline)
        diagnostic = {'status': 'completed', 'dev': metrics(*data['recorded_dev'], prediction),
                      'references': 'train only', 'tie': 'earliest train row', 'train_self_neighbor_scores_are_evidence': False}
    except TimeoutError:
        pass
    return {'status': 'completed' if all(r['status'] != 'incomplete' for r in results) else 'budget_exhausted',
            'results': results, 'selected_neural_rung': selected, 'nearest_neighbor_diagnostic': diagnostic}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('reproduce', 'explore'), required=True)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--collection-report', type=Path, required=True)
    parser.add_argument('--collection-sha256', required=True)
    parser.add_argument('--training-root', type=Path, required=True, help='Legacy directory containing seed-{21,22,23} bundles')
    parser.add_argument('--reproduction-report', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='Fresh exclusive directory outside all inputs')
    parser.add_argument('--seconds', type=float, required=True, help='Stage cap: reproduce<=1200, explore<=2400')
    args = parser.parse_args(argv)
    started = time.monotonic(); report = None; write = None
    try:
        cap = 1200 if args.stage == 'reproduce' else 2400
        if not math.isfinite(args.seconds) or not 0 < args.seconds <= cap:
            raise ValueError('Seconds must be finite, positive, and within the fixed stage cap')
        deadline = started+args.seconds
        for name in ('repo', 'collection_report', 'training_root', 'output', 'reproduction_report'):
            value = getattr(args, name)
            if value is not None:
                setattr(args, name, artifacts._safe_path(value))
        if args.output.exists():
            raise FileExistsError('Fresh output directory required')
        protected = [args.collection_report.parent, args.training_root]
        if args.reproduction_report:
            protected.append(args.reproduction_report.parent)
        guard_output(args.output, protected)
        receipt = None
        if args.stage == 'explore':
            if args.reproduction_report is None:
                raise ValueError('Explore requires --reproduction-report')
            receipt_raw = artifacts._read(args.reproduction_report, 4*1024**2)
            receipt = artifacts._json(receipt_raw)
            if receipt.get('stage') != 'reproduce' or receipt.get('status') != 'passed':
                raise ValueError('Passed reproduction receipt required before data admission')
        data, protocol, originals, identity = admit(args, deadline)
        validate_data(data)
        guard_output(args.output, [artifacts._safe_path(s['path']) for s in protocol.get('sources', [])])
        if receipt is not None:
            require_receipt(receipt, identity)
        budget = StorageBudget((args.output,), StorageLimits(max_bytes=1024**3, min_free_bytes=2*1024**3))
        budget.check(0, path=args.output); args.output.mkdir(parents=True, exist_ok=False)
        ledger = []
        def write(name, payload):
            if len(payload) > 4*1024**2:
                raise ValueError('Compact artifact cap exceeded')
            path = args.output/name; staging = path.with_suffix(path.suffix+'.pending')
            budget.check(len(payload), path=staging)
            with staging.open('xb') as stream:
                stream.write(payload); stream.flush(); os.fsync(stream.fileno())
            staging.replace(path)
            ledger.append({'path': name, 'bytes': len(payload), 'sha256': puck_model.sha(payload)})
        command = [sys.executable, str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)]
        settings = {'stage': args.stage, 'seconds': args.seconds, 'cpu': True, 'dtype': 'float32', 'threads': 1,
                    'seeds': list(puck_model.SEEDS), 'batch': 64, 'clip': 1, 'lr': .001, 'cosine_min_lr': .00001,
                    'rungs': [list(r) for r in RUNGS], 'per_runner_bytes': 1024**3, 'min_free_bytes': 2*1024**3}
        report = {'schema': SCHEMA, 'stage': args.stage, 'status': 'failed', 'scope': 'EXPLORATORY — not gate evidence',
                  'held_out_used': False, 'qualification_claims': [], 'identity': identity, 'settings': settings,
                  'actual_command': command, 'command_sha256': puck_model.sha(puck_model.canonical(command)),
                  'settings_sha256': puck_model.sha(puck_model.canonical(settings)), 'results': []}
        report['results'] = ([{'seed': s, 'status': 'unattempted'} for s in puck_model.SEEDS] if args.stage == 'reproduce' else
            [{'name': name, 'width': w, 'epochs': e, 'cosine': c, 'status': 'unattempted',
              'seeds': [{'seed': s, 'status': 'unattempted'} for s in puck_model.SEEDS]} for name, w, e, c in RUNGS])
        if receipt is not None:
            report['reproduction_report_sha256'] = puck_model.sha(receipt_raw)
        report['audit'] = audit(data, deadline)
        report.update(run_stage(args, data, originals, deadline, write, report['results']))
        if report['status'] in ('passed', 'completed'):
            check_deadline(deadline)
    except (ValueError, OSError, RuntimeError, TimeoutError) as error:
        if report is None:
            print(puck_model.canonical({'status': 'failed', 'error': str(error)[:2048]}).decode(), file=sys.stderr)
            return 1
        report['status'] = 'budget_exhausted' if isinstance(error, TimeoutError) else 'failed'
        report['error'] = {'type': type(error).__name__, 'message': str(error)[:2048]}
    if report is not None:
        try:
            check_identity(args, protocol, identity, data, deadline)
            if receipt is not None and bounded_sha(args.reproduction_report, deadline) != report['reproduction_report_sha256']:
                raise ValueError('Reproduction receipt changed during exploration')
            if report['status'] in ('passed', 'completed'):
                check_deadline(deadline)
            report['inputs_unchanged_after'] = {'status': 'verified'}
        except (ValueError, OSError, RuntimeError) as error:
            if not isinstance(error, TimeoutError) or report['status'] != 'failed':
                report['status'] = 'budget_exhausted' if isinstance(error, TimeoutError) else 'failed'
            report['finalization_error'] = str(error)[:2048]
            report['inputs_unchanged_after'] = {'status': 'incomplete' if isinstance(error, TimeoutError) else 'failed',
                                               'reason': str(error)[:2048]}
        report['elapsed_seconds'] = time.monotonic()-started; report['files'] = list(ledger)
        try:
            write('report.json', puck_model.canonical(report))
        except (ValueError, OSError, RuntimeError) as error:
            print(str(error), file=sys.stderr); return 1
        print(puck_model.canonical({'status': report['status'], 'report': str(args.output/'report.json')}).decode())
        return 0 if report['status'] in ('passed', 'completed', 'budget_exhausted') else 1


if __name__ == '__main__':
    raise SystemExit(main())
