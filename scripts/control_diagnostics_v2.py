"""Frozen retained-input control diagnostics. Descriptive; no fits or promotion.

Puck arrays are evaluated with NumPy float32 affine/tanh arithmetic, never a
checkpoint model. Navigation uses saved response NPZs only. Historical physical
reader roots remain binding; no legacy reader is changed. Corpus phase unknown
stays unknown. The contact-only comparator resets the same recovery FSM per
episode, uses .7/wind-bearing outside recovery and has no panel routing.
"""
import argparse
import contextlib
import hashlib
import importlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import zipfile

MiB = 1024**2
LEDGER_SHA = {'puck': 'f5a28aeb782c521142656505076d97f5cf86f26ba2350270634e4e776105955b',
              'nav': '3204d11cec98a34146872c2a54b105c21d112c21f314f6546d94e2a084928a87'}
KINDS = ('all9', 'geometry_before_mode', 'exact_mode_geometry')
STRATA = ('stop', 'approach_turn_only', 'approach_positive', 'approach_negative',
          'push_turn_only', 'push_positive', 'push_negative')
HEADING_BINS = ('(0,1e-6]', '(1e-6,.01]', '(.01,.12]', '>.12')


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('Combined diagnostics deadline exhausted; no retry or extension')


def safe_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Symlink input/output refused: '+str(path))
    return path.resolve()


def file_sha(path, deadline, maximum=160*MiB):
    check_deadline(deadline); path = safe_path(path)
    if not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('Regular bounded immutable input required: '+str(path))
    digest = hashlib.sha256(); total = 0
    with path.open('rb') as stream:
        while True:
            check_deadline(deadline); block = stream.read(MiB)
            if not block: break
            total += len(block)
            if total > maximum: raise ValueError('Growing input exceeds bound')
            digest.update(block)
    check_deadline(deadline)
    return digest.hexdigest()


def verify_pins(pins, deadline):
    for path, expected in pins.items():
        if file_sha(path, deadline) != expected:
            raise ValueError('Immutable input identity changed: '+path)
    check_deadline(deadline)


def read_json(path, deadline, expected=None):
    observed = file_sha(path, deadline, 4*MiB)
    if expected is not None and observed != expected: raise ValueError('Frozen JSON hash differs: '+str(path))
    value = json.loads(Path(path).read_bytes(), parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))
    check_deadline(deadline)
    return value


def guard_output(path, inputs):
    actual = safe_path(path)
    for source in inputs:
        source = safe_path(source)
        if actual.is_relative_to(source) or source.is_relative_to(actual):
            raise ValueError('Output overlaps immutable input owner')
    if actual.exists(): raise ValueError('Fresh exclusive output directory required')
    return actual


class Output:
    def __init__(self, path, inputs, max_bytes, min_free=2*1024**3):
        self.path = guard_output(path, inputs)
        self.maximum, self.min_free = max_bytes, min_free
        parent = self.path.parent
        while not parent.exists(): parent = parent.parent
        if shutil.disk_usage(parent).free < min_free: raise ValueError('2 GiB free floor')
        self.path.mkdir(parents=True, exist_ok=False)
        self.written = 0

    def write(self, name, payload, deadline=math.inf):
        check_deadline(deadline)
        payload_sha = hashlib.sha256(payload).hexdigest()
        check_deadline(deadline)
        if Path(name).name != name or name in ('.', '..'): raise ValueError('Output basename required')
        if len(payload)+self.written > self.maximum: raise ValueError('Bounded output byte limit')
        if shutil.disk_usage(self.path).free-len(payload) < self.min_free: raise ValueError('2 GiB free floor')
        pending = self.path/(name+'.pending')
        with pending.open('xb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        pending.replace(self.path/name); self.written += len(payload)
        return {'path': name, 'bytes': len(payload), 'sha256': payload_sha}


def read_numeric(path, pin, shapes, deadline):
    """Frozen ledger hash/byte/shape/key descriptor; validate before allocation."""
    import numpy as np
    path = safe_path(path)
    if (not shapes or path.stat().st_size != pin['bytes'] or pin['bytes'] > 4*MiB or
            file_sha(path, deadline, 4*MiB) != pin['sha256']):
        raise ValueError('Frozen numeric artifact identity differs')
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if (len(members) != len(shapes) or {m.filename for m in members} != {key+'.npy' for key in shapes} or
                sum(m.file_size for m in members) > 4*MiB or
                any(m.compress_type != zipfile.ZIP_STORED or m.flag_bits & 1 for m in members)):
            raise ValueError('Unsafe or extra NPZ members')
        for name, expected in shapes.items():
            check_deadline(deadline)
            with archive.open(name+'.npy') as stream:
                version = np.lib.format.read_magic(stream)
                if version not in ((1, 0), (2, 0)): raise ValueError('Unsupported numeric header')
                reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
                shape, fortran, dtype = reader(stream, max_header_size=2048)
                if (shape != expected or fortran or dtype != np.float32 or
                        stream.tell()+dtype.itemsize*math.prod(shape) != archive.getinfo(name+'.npy').file_size):
                    raise ValueError('Frozen numeric shape/dtype/content differs')
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in shapes}
    if any(not np.isfinite(value).all() for value in arrays.values()): raise ValueError('Nonfinite numeric artifact')
    check_deadline(deadline)
    return arrays


def heading_bins(values):
    import numpy as np
    values = np.asarray(values)
    if not np.isfinite(values).all(): raise ValueError('Finite heading labels required')
    return np.where(values == 0, -1, np.digitize(np.abs(values), [1e-6, .01, .12], right=True))


def stratum_ids(x, y):
    import numpy as np
    stop = np.all(y == 0, axis=1)
    regime = np.where(y[:, 0] == 0, 0, np.where(y[:, 0] > 0, 1, 2))
    return np.where(stop, 0, 1+3*x[:, 8].astype(np.uint8)+regime)


def error_summary(y, actions):
    import numpy as np
    if actions.shape != y.shape or not np.isfinite(actions).all() or not np.isfinite(y).all():
        raise ValueError('Aligned finite action/target arrays required')
    if not len(y): return {'count': 0, 'normalized_mse': None, 'velocity_normalized_mse': None, 'heading_normalized_mse': None,
                           'velocity_mae': None, 'heading_mae_radians': None, 'heading_sign_agreement': None}
    squared = ((actions.astype(np.float64)-y)/.4)**2
    nz = y[:, 1] != 0
    return {'count': len(y), 'normalized_mse': float(squared.mean()),
            'velocity_normalized_mse': float(squared[:, 0].mean()), 'heading_normalized_mse': float(squared[:, 1].mean()),
            'velocity_mae': float(np.abs(actions[:, 0]-y[:, 0]).mean()),
            'heading_mae_radians': float(np.abs(actions[:, 1]-y[:, 1]).mean()),
            'heading_sign_agreement': float((np.sign(actions[nz, 1]) == np.sign(y[nz, 1])).mean()) if nz.any() else None}


def puck_metrics(x, y, actions):
    import numpy as np
    result = error_summary(y, actions); turn = stratum_ids(x, y) == 1; nz = y[:, 1] != 0
    leak = float((np.abs(actions[turn, 0]) > .05).mean()) if turn.any() else None
    sign = result['heading_sign_agreement']
    result.update(approach_turn_only_count=int(turn.sum()), approach_turn_only_leak=leak,
                  nonzero_target_heading_count=int(nz.sum()),
                  original_gate_eligible=bool(len(y) and result['normalized_mse'] <= .01 and leak is not None and
                                              leak <= .05 and sign is not None and sign >= .95))
    return result


def statistics(x):
    import numpy as np
    mean, scale = np.zeros(9, np.float32), np.ones(9, np.float32)
    mean[:6] = x[:, :6].mean(0, dtype=np.float64)
    sigma = x[:, :6].std(0, dtype=np.float64)
    scale[:6] = np.where(sigma == 0, 1, sigma)
    return mean, scale


def nearest(x, y, query, kind, deadline):
    """32-row chunks, train refs only, earliest-row ties; missing modes unsupported."""
    import numpy as np
    if kind not in KINDS or not len(x): raise ValueError('Declared nearest-neighbor kind/nonempty references required')
    check_deadline(deadline); mean, scale = statistics(x)
    columns = list(range(9)) if kind == 'all9' else [0, 1, 2, 3, 8] if kind == 'geometry_before_mode' else [0, 1, 2, 3]
    train = ((x-mean)/scale).astype(np.float64)[:, columns]
    dev = ((query-mean)/scale).astype(np.float64)[:, columns]
    actions = np.full((len(query), 2), np.nan); distances = np.full(len(query), np.inf); indices = np.full(len(query), -1, int)
    norm = (train*train).sum(1)
    for start in range(0, len(query), 32):
        check_deadline(deadline); rows = dev[start:start+32]
        d = rows@train.T; d *= -2; d += norm; d += (rows*rows).sum(1)[:, None]
        if kind == 'exact_mode_geometry': d[query[start:start+32, 8, None] != x[None, :, 8]] = np.inf
        selected = d.argmin(1); minimum = d[np.arange(len(rows)), selected]; valid = np.isfinite(minimum)
        cursor = start+np.flatnonzero(valid)
        indices[cursor] = selected[valid]; actions[cursor] = y[selected[valid]]
        distances[cursor] = np.sqrt(np.maximum(0, minimum[valid]))
    check_deadline(deadline)
    return actions, distances, indices


def distance_summary(values):
    import numpy as np
    values = np.asarray(values); finite = values[np.isfinite(values)]
    return {'rows': len(values), 'unsupported_rows': int((~np.isfinite(values)).sum()),
            'quantiles': dict(zip(('min', 'q10', 'q50', 'q90', 'max'), np.quantile(finite, [0, .1, .5, .9, 1]).tolist())) if len(finite) else None}


def support_calibration(x, y, layouts, kind, deadline):
    import numpy as np
    distance = np.full(len(x), np.inf); folds = []
    for layout in np.unique(layouts):
        check_deadline(deadline); held = layouts == layout
        if not (~held).any(): raise ValueError('LOTO support requires at least two training layouts')
        _, d, _ = nearest(x[~held], y[~held], x[held], kind, deadline)
        distance[held] = d; folds.append({'layout': int(layout), **distance_summary(d)})
    return {**distance_summary(distance), 'folds': folds,
            'scale_fit': 'references excluding the complete left-out training layout',
            'calibration': 'descriptive empirical distance distribution; no gate or OOD threshold',
            '_distances': distance}


def puck_boundaries(x):
    """Teacher geometry in rover coordinates; signed distances to existing branches."""
    import numpy as np
    p, g = x[:, :2].astype(np.float64)*14, x[:, 2:4].astype(np.float64)*14
    direction = g-p; distance = np.linalg.norm(direction, axis=1)
    unit = np.divide(direction, distance[:, None], out=np.zeros_like(direction), where=distance[:, None] != 0)
    axial = (p*unit).sum(1); lateral = np.abs(p[:, 0]*unit[:, 1]-p[:, 1]*unit[:, 0])
    approach = p-.55*unit; ready = (axial >= .35) & (axial <= .63) & (lateral <= .06)
    mode = x[:, 8] == 1
    after_push = np.where(mode, ready, ready & (np.linalg.norm(approach, axis=1) <= .08))
    heading = np.arctan2(np.where(after_push, unit[:, 1], approach[:, 1]), np.where(after_push, unit[:, 0], approach[:, 0]))
    reverse = np.arctan2(-approach[:, 1], -approach[:, 0])
    reverse_choice = (~after_push) & (np.abs(reverse) < np.abs(heading)); heading = np.where(reverse_choice, reverse, heading)
    return {'goal_distance_minus_.2': distance-.2, 'axial_minus_.35': axial-.35,
            '.63_minus_axial': .63-axial, '.06_minus_lateral': .06-lateral,
            '.08_minus_approach_distance': .08-np.linalg.norm(approach, axis=1),
            '.12_minus_abs_teacher_heading': .12-np.abs(heading),
            'ready': ready, 'after_push': after_push, 'reverse_approach': reverse_choice}


def puck_decomposition(x, y, actions, layouts, distances=None, calibration=None):
    import numpy as np
    ids = stratum_ids(x, y); bins = heading_bins(y[:, 1]); result = {'all': puck_metrics(x, y, actions)}
    groups = {'stratum': [(name, ids == i) for i, name in enumerate(STRATA)],
              'layout': [(str(int(seed)), layouts == seed) for seed in np.unique(layouts)],
              'target_heading_magnitude': [('exact_zero', bins == -1), *[(name, bins == i) for i, name in enumerate(HEADING_BINS)]]}
    for key, masks in groups.items():
        result[key] = {name: puck_metrics(x[mask], y[mask], actions[mask]) for name, mask in masks}
    result['teacher_boundaries'] = {}
    for name, values in puck_boundaries(x).items():
        masks = (('true', values), ('false', ~values)) if values.dtype == bool else (('positive_or_zero', values >= 0), ('negative', values < 0))
        row = {'sides': {label: puck_metrics(x[mask], y[mask], actions[mask]) for label, mask in masks}}
        if values.dtype != bool: row['signed_margin_quantiles'] = np.quantile(values, [0, .1, .5, .9, 1]).tolist()
        result['teacher_boundaries'][name] = row
    if distances is not None:
        result['nearest_support'] = distance_summary(distances)
        result['nearest_support']['per_layout'] = {str(int(seed)): distance_summary(distances[layouts == seed]) for seed in np.unique(layouts)}
        result['nearest_support']['per_stratum'] = {name: distance_summary(distances[ids == i]) for i, name in enumerate(STRATA)}
        if calibration is not None:
            reference = np.sort(calibration[np.isfinite(calibration)])
            finite = distances[np.isfinite(distances)]
            result['nearest_support']['loto_empirical_percentile_summary'] = distance_summary(np.searchsorted(reference, finite, side='right')/len(reference)) if len(reference) else None
            # Error associations use only training calibration quantiles. These
            # descriptive groups are not new support or eligibility thresholds.
            if len(reference):
                cutpoints = np.quantile(reference, [.25, .5, .75])
                support_ids = np.digitize(distances, cutpoints, right=True)
                result['nearest_support']['error_by_training_loto_distance_quartile'] = {
                    str(i+1): puck_metrics(x[support_ids == i], y[support_ids == i], actions[support_ids == i]) for i in range(4)}
                result['nearest_support']['training_loto_quartile_cutpoints'] = cutpoints.tolist()
    return result


def puck_arrays_response(arrays, x, deadline):
    import numpy as np
    values = []
    for start in range(0, len(x), 64):
        check_deadline(deadline); raw = x[start:start+64].copy()
        if 'mean' in arrays: raw = (raw-arrays['mean'])/arrays['scale']
        for i in (0, 2, 4): raw = np.tanh(raw@arrays[f'{i}.weight'].T+arrays[f'{i}.bias'])
        values.append(raw.astype(np.float64)*.4)
    return np.concatenate(values)


def initial_recovery():
    return {'phase': None, 'count': 0, 'direction': 1., 'previous_bad_contact': False}


def recovery_step(before, bad, angle, normal):
    """Exact declared-sensor FSM: active latch frozen; final old action may replace."""
    import numpy as np
    if (set(before) != set(initial_recovery()) or before['phase'] not in (None, 'back') or
            type(before['count']) is not int or before['count'] not in (range(1, 45) if before['phase'] else (0,)) or
            before['direction'] not in (-1., 1.) or type(before['previous_bad_contact']) is not bool or type(bad) is not bool or
            (bad and (angle is None or not math.isfinite(angle) or abs(angle) > math.pi)) or (not bad and angle is not None)):
        raise ValueError('Exact finite declared contact/FSM state required')
    after = dict(before); completed = before['phase'] == 'back' and before['count'] == 44
    started = False; action = np.asarray(normal, np.float32)
    if action.shape != (2,) or not np.isfinite(action).all(): raise ValueError('Finite normal action required')
    if before['phase'] == 'back':
        action = np.array([-.35, .1*before['direction']], np.float32)
        after['count'] += 1
        if completed: after.update(phase=None, count=0)
    if after['phase'] is None:
        started = bad and not after['previous_bad_contact']; after['previous_bad_contact'] = bad
        if started:
            after.update(phase='back', count=1, direction=-1. if angle > 0 else 1.)
            action = np.array([-.35, .1*after['direction']], np.float32)
    return after, action, {'started': started, 'completed': completed, 'old_label_replaced': completed and started}


def recovery_rule(features):
    import numpy as np
    if features.ndim != 2 or features.shape[1] != 388 or not np.isfinite(features).all(): raise ValueError('Finite navigation features required')
    state = initial_recovery(); actions = []; counts = dict.fromkeys(('started', 'completed', 'old_label_replaced'), 0)
    for row in features:
        if row[384] not in (0, 1): raise ValueError('Declared binary contact required')
        bad = bool(row[384]); angle = float(row[385])*math.pi if bad else None
        normal = [.7, math.atan2(float(row[387]), float(row[386]))]
        state, action, transition = recovery_step(state, bad, angle, normal); actions.append(action)
        for key in counts: counts[key] += int(transition[key])
    return np.asarray(actions, np.float32), counts


def nav_errors(y, actions):
    import numpy as np
    if actions.shape != y.shape or not np.isfinite(actions).all() or not np.isfinite(y).all(): raise ValueError('Aligned finite nav responses required')
    if not len(y): return {'count': 0, 'loss': None, 'velocity_loss': None, 'circular_heading_loss': None,
                           'velocity_mae': None, 'wrapped_heading_mae_radians': None, 'linear_heading_mae_radians': None, 'seam_crossing_rows': 0}
    # Historical NumPy arithmetic is float32 for retained float32 panels.
    delta = actions[:, 1]-y[:, 1]; velocity = .5*(actions[:, 0]-y[:, 0])**2/9; heading = .5*(1-np.cos(delta))
    return {'count': len(y), 'loss': float((velocity+heading).mean()), 'velocity_loss': float(velocity.mean()),
            'circular_heading_loss': float(heading.mean()), 'velocity_mae': float(np.abs(actions[:, 0]-y[:, 0]).mean()),
            'wrapped_heading_mae_radians': float(np.abs(np.arctan2(np.sin(delta), np.cos(delta))).mean()),
            'linear_heading_mae_radians': float(np.abs(delta).mean()), 'seam_crossing_rows': int((np.abs(delta) > math.pi).sum())}


def nav_decomposition(episodes, predictions):
    import numpy as np
    if len(episodes) != len(predictions): raise ValueError('Exact response episode roster required')
    y = np.concatenate([ep['targets'] for ep in episodes]); a = np.concatenate(predictions)
    result = {'all': nav_errors(y, a), 'owner': {}, 'episodes': []}
    for ep, action in zip(episodes, predictions, strict=True):
        result['episodes'].append({'run_id': ep['run_id'], 'scene': ep.get('scene_seed'), 'owner': ep.get('learner_seed'), **nav_errors(ep['targets'], action)})
    owners = [ep.get('learner_seed') for ep in episodes]
    for owner in dict.fromkeys(owners):
        ix = [i for i, value in enumerate(owners) if value == owner]
        result['owner'][str(owner) if owner is not None else 'unknown'] = nav_errors(np.concatenate([episodes[i]['targets'] for i in ix]), np.concatenate([predictions[i] for i in ix]))
    known = all('recovery' in ep and 'onset' in ep for ep in episodes)
    result.update(phase_status='validated queried advice' if known else 'unknown', active_recovery=None, outside_recovery=None, contact_onset=None, original_recovery_gates=None)
    seam = np.abs(a[:, 1]-y[:, 1]) > math.pi
    result['seam_crossing'] = nav_errors(y[seam], a[seam]); result['outside_seam'] = nav_errors(y[~seam], a[~seam])
    if known:
        recovery = np.concatenate([ep['recovery'] for ep in episodes]); onset = np.concatenate([ep['onset'] for ep in episodes])
        result.update(active_recovery=nav_errors(y[recovery], a[recovery]), outside_recovery=nav_errors(y[~recovery], a[~recovery]), contact_onset=nav_errors(y[onset], a[onset]))
        negative = onset & (y[:, 0] < 0); outside = ~recovery & (y[:, 0] >= 0)
        result['original_recovery_gates'] = {'onset_negative_count': int(negative.sum()),
            'onset_reverse_recall': float((a[negative, 0] < 0).mean()) if negative.any() else None,
            'false_reverse_denominator': int(outside.sum()), 'false_reverse_count': int((a[outside, 0] < 0).sum()),
            'false_reverse_rate': float((a[outside, 0] < 0).mean()) if outside.any() else None}
    return result


@contextlib.contextmanager
def historical_imports(root):
    """Load physical pinned readers, isolate project module names between tracks."""
    root = safe_path(root); old_path = list(sys.path); saved = {}
    if 'torch' in sys.modules or 'mujoco' in sys.modules:
        raise ValueError('No-fit diagnostics require a fresh process without native/model imports')
    for name, module in list(sys.modules.items()):
        if name == 'palimpsest' or name.startswith('palimpsest.') or name.startswith(('train_', 'prepare_', 'collect_', 'verify_', 'analyze_', 'acquire_')):
            saved[name] = module; del sys.modules[name]
    class NoCompute:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in ('mujoco', 'torch'): raise ImportError('Native/model runtime forbidden by no-fit diagnostics')
    blocker = NoCompute(); sys.meta_path.insert(0, blocker); sys.path[:0] = [str(root/'src'), str(root/'scripts')]
    try: yield
    finally:
        for name, module in list(sys.modules.items()):
            filename = getattr(module, '__file__', None)
            if filename and Path(filename).resolve().is_relative_to(root): del sys.modules[name]
        sys.modules.update(saved); sys.path[:] = old_path; sys.meta_path.remove(blocker)


def compare_metrics(actual, expected, keys, tolerance=1e-6):
    differences = {}
    for key in keys:
        left, right = actual.get(key), expected.get(key)
        if left is None or right is None:
            differences[key] = {'status': 'matched_unknown' if left is right else 'unmatched_unknown'}
        else:
            delta = abs(left-right); differences[key] = {'absolute_difference': delta, 'within_1e-6': delta <= tolerance}
    return {'status': 'matched_within_1e-6' if all(v.get('within_1e-6', v.get('status') == 'matched_unknown') for v in differences.values()) else 'differs', 'metrics': differences}


def ledger_inputs(args, ledgers):
    """Full frozen path roster guards output before readers or arrays are opened."""
    pins = {str(Path(__file__).resolve()): hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    protected = [args.repo/'src', args.repo/'scripts', args.repo/'docs', args.puck_producer, args.nav_producer]
    for track, ledger in ledgers.items():
        path = getattr(args, track+'_ledger'); pins[str(path)] = LEDGER_SHA[track]; protected.append(path.parent)
        for item in ledger['published_artifacts']:
            pinpath = safe_path(path.parent/item['path']); pins[str(pinpath)] = item['sha256']; protected.append(pinpath.parent)
    puck = ledgers['puck']['exploration']; identity = puck['identity']
    historical_runner = Path(puck['actual_command'][1]).parent.parent
    for name, pin in identity['source_hashes'].items():
        base = historical_runner if name in ('scripts/puck_fit_ladder.py', 'docs/plans/research-capability-phase.md') else args.puck_producer
        pins[str(base/name)] = pin
    command = puck['actual_command']; collection = Path(command[command.index('--collection-report')+1])
    pins[str(collection)] = identity['collection_report_sha256']; protected.append(collection.parent)
    for source in identity['sources']:
        root = Path(source['path']); protected.append(root)
        for name, pin in source['source_hashes'].items(): pins[str(root/name)] = pin
    nav = ledgers['nav']['exploration']; admitted = nav['admitted_input_identity']
    if str(args.nav_producer) != nav['binding']['historical_root']: raise ValueError('Exact retained physical navigation producer required')
    pins.update(nav['binding']['files'])
    for source in admitted['source_files']:
        root = Path(source['path']); protected.append(root)
        for item in source['files']: pins[str(root/item['path'])] = item['sha256']
    pins.update(admitted['model_inputs'])
    pins[str(args.nav_producer/'upstream/fly-gym/agents/teacher_analytic_agent.py')] = '5edca9a587dea0a2996856e42a96013aab1b1b0a277eacb74b7fc4270c55c586'
    historical = admitted['historical']; protected.append(Path(historical['root']))
    for name, pin in historical['sources'].items(): pins[str(Path(historical['root'])/name)] = pin
    for section in ('named_reader_sources', 'added_sources'):
        for name, pin in admitted['code'][section].items(): pins[str(args.nav_producer/name)] = pin
    pins[str(args.nav_producer/'uv.lock')] = admitted['code']['lock_sha256']
    for item in admitted['documents']['data_manifest']['input_documents'].values():
        pins[item['path']] = item['sha256']; protected.append(Path(item['path']).parent)
    return pins, protected, collection


def run_puck(args, ledger, collection, pins, deadline):
    import numpy as np
    retained = ledger['exploration']; identity = retained['identity']
    with historical_imports(args.puck_producer):
        trainer = importlib.import_module('train_puck')
        if Path(trainer.__file__).resolve() != args.puck_producer/'scripts/train_puck.py': raise ValueError('Physical puck reader path mismatch')
        collection_doc = read_json(collection, deadline, identity['collection_report_sha256'])
        expected = [(s, 'train' if s < 6016 else 'recorded_dev') for s in range(6000, 6020)]
        if [(s.get('seed'), s.get('split')) for s in collection_doc['sources']] != expected: raise ValueError('Exact retained puck roster required before admission')
        check_deadline(deadline)
        data, protocol = trainer.prepare(args.puck_producer, collection, identity['collection_report_sha256'], 21)
        from palimpsest import puck_balanced
        if protocol['sources'] != identity['sources']: raise ValueError('Puck historical reader source identity differs')
        for name, pair in data.items():
            if [hashlib.sha256(a.tobytes()).hexdigest() for a in pair] != identity['data_hashes'][name]: raise ValueError('Puck admitted data bytes differ')
            puck_balanced.stratum_ids(*pair)
            for a in pair: a.setflags(write=False)
    if set(data) != {'train', 'recorded_dev'} or [len(data[s][0]) for s in ('train', 'recorded_dev')] != [5710, 1314]: raise ValueError('Frozen puck row counts required')
    layouts = {name: np.concatenate([np.full(s['ticks'], s['seed']) for s in identity['sources'] if s['split'] == name]) for name in data}
    x, y = data['train']; q, target = data['recorded_dev']
    result = {'status': 'running', 'heading_bins_radians': list(HEADING_BINS), 'models': [], 'nearest_neighbor_contrasts': {},
              'limitations': ['Finite retained corpus only; branch geometry reconstructed from float32 features',
                             'NumPy float32 checkpoint arithmetic differs from Torch kernels; retained metric comparison qualified',
                             'Support calibration is descriptive, without a new support gate or generalization proof'],
              'train_statistics': dict(zip(('mean', 'scale'), [a.tolist() for a in statistics(x)]))}
    nearest_results = {}
    for kind in KINDS:
        check_deadline(deadline); calibration = support_calibration(x, y, layouts['train'], kind, deadline)
        actions, distance, indices = nearest(x, y, q, kind, deadline); valid = indices >= 0
        summary = puck_decomposition(q[valid], target[valid], actions[valid], layouts['recorded_dev'][valid], distance[valid], calibration['_distances']) if valid.any() else None
        result['nearest_neighbor_contrasts'][kind] = {'dev': summary, 'unsupported_dev_rows': int((~valid).sum()),
            'calibration': {k: v for k, v in calibration.items() if k != '_distances'}, 'references': 'training layouts only',
            'tie': 'earliest training row', 'train_self_neighbor_score_used': False}
        nearest_results[kind] = (distance, calibration['_distances'])
        if kind == 'all9':
            result['nearest_neighbor_contrasts'][kind]['prior_reproduction'] = compare_metrics(summary['all'], retained['nearest_neighbor_diagnostic']['dev'], ('normalized_mse', 'approach_turn_only_leak', 'heading_sign_agreement'))
    artifacts = {Path(item['path']).name: item for item in ledger['published_artifacts']}
    distance, calibration = nearest_results['exact_mode_geometry']
    for rung in retained['results']:
        if rung['name'] not in ('conditioned32', 'longer32', 'capacity256') or rung['width'] not in (32, 256): raise ValueError('Frozen puck rung descriptor required')
        for seed in rung['seeds']:
            check_deadline(deadline)
            if seed['status'] != 'completed' or seed['seed'] not in (21, 22, 23): raise ValueError('Exactly completed selected checkpoints required')
            name = f"{rung['name']}-seed-{seed['seed']}.npz"; pin = artifacts[name]; width = rung['width']
            shapes = {'0.weight': (width, 9), '0.bias': (width,), '2.weight': (width, width), '2.bias': (width,), '4.weight': (2, width), '4.bias': (2,)}
            if width == 256: shapes.update(mean=(9,), scale=(9,))
            arrays = read_numeric(args.puck_ledger.parent/pin['path'], pin, shapes, deadline)
            if width == 256 and (np.any(arrays['scale'] <= 0) or any(not np.array_equal(arrays[key], statistics(x)[i]) for i, key in enumerate(('mean', 'scale')))):
                raise ValueError('Wider descriptor normalization differs from frozen train-only statistics')
            actions = puck_arrays_response(arrays, q, deadline)
            decomposition = puck_decomposition(q, target, actions, layouts['recorded_dev'], distance, calibration)
            result['models'].append({'rung': rung['name'], 'seed': seed['seed'], 'selected_epoch': seed['selected_epoch'],
                'artifact_descriptor': {'path': pin['path'], 'sha256': pin['sha256'], 'keys_shapes': {k: list(v) for k, v in shapes.items()}, 'dtype': 'float32'},
                'dev': decomposition, 'retained_metric_comparison': compare_metrics(decomposition['all'], seed['dev'], ('normalized_mse', 'approach_turn_only_leak', 'heading_sign_agreement'))})
    if len(result['models']) != 9: raise ValueError('Exact nine selected puck checkpoints required')
    result['status'] = 'completed'; return result


def advice_replay(ep, rows, deadline):
    import numpy as np
    state = initial_recovery(); recovery, onset = [], []; prior_bad = False
    counts = dict.fromkeys(('started', 'completed', 'old_label_replaced'), 0); outside_difference = 0
    if len(rows) != len(ep['targets']): raise ValueError('Advice replay row cursor mismatch')
    for tick, row in enumerate(rows):
        check_deadline(deadline); query = row['advice']; bad = bool(ep['features'][tick, 384])
        angle = float(ep['features'][tick, 385])*math.pi if bad else None
        if row['tick'] != tick or query['before'] != state or type(query['contact']['bad']) is not bool or query['contact']['bad'] != bad:
            raise ValueError('Advice before-state/contact replay mismatch')
        if bad and not np.array_equal(np.float32(query['contact']['angle'])/np.float32(math.pi), ep['features'][tick, 385]): raise ValueError('Declared contact-angle alignment mismatch')
        # Retain independent scalar contact precision for exact recorded state/action replay.
        contact_angle = query['contact']['angle']
        after, action, transition = recovery_step(state, bad, contact_angle, query['expert_action'])
        active = state['phase'] == 'back' or transition['started']
        if (after != query['after'] or transition != query['transition'] or
                not np.array_equal(action, np.asarray(query['expert_action'], np.float32)) or
                not np.array_equal(action, ep['targets'][tick])):
            raise ValueError('Advice after-state/start/completion/replacement/action replay mismatch')
        recovery.append(active); onset.append(bad and not prior_bad); prior_bad = bad; state = after
        if not active:
            normal = np.array([.7, math.atan2(float(ep['features'][tick, 387]), float(ep['features'][tick, 386]))], np.float32)
            outside_difference += not np.array_equal(normal, action)
        for key in counts: counts[key] += int(transition[key])
    ep.update(recovery=np.asarray(recovery, bool), onset=np.asarray(onset, bool))
    return {'run_id': ep['run_id'], 'rows': len(rows), 'fsm_before_after_transitions': 'exact', 'recovery_actions': 'exact',
            'normal_actions': 'validated recorded advice, privileged planner not reconstructed',
            'normal_bearing_rule_different_rows': outside_difference,
            'pre_action_contact_onset_rows': int(ep['onset'].sum()),
            'teacher_recovery_emission_rows': int(ep['recovery'].sum()),
            'negative_target_contact_onset_rows': int((ep['onset'] & (ep['targets'][:, 0] < 0)).sum()), **counts}


def run_nav(args, ledger, output, pins, deadline):
    import numpy as np
    retained = ledger['exploration']; identity = retained['admitted_input_identity']
    actual_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=args.nav_producer, text=True, timeout=5).strip()
    if actual_head != retained['binding']['head']: raise ValueError('Frozen navigation producer HEAD differs')
    with historical_imports(args.nav_producer):
        trainer = importlib.import_module('train_male_navigation_v2')
        if trainer.ROOT != args.nav_producer: raise ValueError('Physical navigation reader ROOT differs')
        model_inputs = identity['model_inputs']
        graph = next(Path(p) for p in model_inputs if p.endswith('source-graph.json'))
        graph_manifest = next(Path(p) for p in model_inputs if p.endswith('malecns-reduced-neighborhood-v1.json'))
        cell = next(Path(p) for p in model_inputs if p.endswith('connectome_rnn_model.py'))
        preparation = argparse.Namespace(training_seed=10, graph=graph, graph_manifest=graph_manifest, cell_source=cell, output=output.path/'admission'/'seed-10')
        _, data, _, context = trainer.prepare(preparation, deadline)
        for item in context['plan']['prepared_output_files']:
            pins[str(safe_path(args.nav_producer/item['path']))] = item['sha256']
        for name, item in context['plan']['immutable_prerequisites'].items():
            pins[str(safe_path(args.nav_producer/item['path']))] = item['sha256']
        for key in ('code', 'historical', 'documents', 'source_files'):
            if context[key] != identity[key]: raise ValueError('Frozen navigation admission identity mismatch: '+key)
        reader = trainer.data_reader; manifest = context['manifest']; collection_pin = manifest['input_documents']['accepted_collection']
        collection = read_json(collection_pin['path'], deadline, collection_pin['sha256'])
        by_run = {ep['run_id']: ep for ep in data['augmented']['train']}; by_owner = {item['run']: (case, item) for case, item in collection['cases'].items()}
        panels = {'train': list(data['old-corpus']['train']), 'teacher_dev': list(data['old-corpus']['dev']), 'advice_dev': []}; replay = []
        for source in manifest['new_sources']:
            ep = dict(by_run[source['run_id']]); ep.update(scene_seed=source['scene_seed'], learner_seed=source['learner_seed'])
            case, owner = by_owner[source['path']]; path = Path(collection_pin['path']).parent/case/'result.json'
            pins[str(path)] = owner['result_sha256']; rows = read_json(path, deadline, owner['result_sha256'])['rows']
            audit = advice_replay(ep, rows, deadline)
            old_audit = next(item for item in retained['advice_label_audit'] if item['run_id'] == ep['run_id'])
            for key in ('rows', 'pre_action_contact_onset_rows', 'teacher_recovery_emission_rows', 'negative_target_contact_onset_rows'):
                if audit[key] != old_audit[key]: raise ValueError('Frozen advice audit count differs: '+key)
            audit['prior_audit_counts'] = 'exact'; replay.append(audit)
            split = 'train' if ep['scene_seed'] in (3100, 3101) else 'advice_dev' if ep['scene_seed'] in (3102, 3103) else None
            if split is None: raise ValueError('Unadmitted/reserved advice scene refused')
            panels[split].append(ep)
        actual = {name: [{'run_id': ep['run_id'], 'episode': ep['episode'], 'ticks': len(ep['targets']),
            'scene_seed': ep.get('scene_seed'), 'owner': ep.get('learner_seed'),
            'feature_target_sha256': hashlib.sha256(ep['features'].tobytes()+ep['targets'].tobytes()).hexdigest()} for ep in eps] for name, eps in panels.items()}
        if actual != retained['split_assignments']: raise ValueError('Exact grouped navigation panels/order/bytes required')
        trainer.check_context(context, deadline)
    for eps in panels.values():
        for ep in eps:
            for name in ('features', 'targets'): ep[name].setflags(write=False)
    result = {'status': 'running', 'advice_sensor_replay': replay, 'models': [], 'comparators': {},
              'limitations': ['Retained learner trajectories do not identify counterfactual teacher recovery success',
                             'Old teacher recovery/onset phase is unknown', 'Normal-mode teacher planner is not reconstructed',
                             '.7/bearing plus FSM is a sensor-only descriptive comparator, not a promoted controller']}
    for panel in ('teacher_dev', 'advice_dev'):
        eps = panels[panel]; rule, transitions = zip(*(recovery_rule(ep['features']) for ep in eps), strict=True)
        normal = [np.column_stack((np.full(len(ep['targets']), .7, np.float32), np.arctan2(ep['features'][:, 387], ep['features'][:, 386]))) for ep in eps]
        result['comparators'][panel] = {'normal_rule': nav_decomposition(eps, normal), 'same_fsm_rule': nav_decomposition(eps, list(rule)),
            'same_fsm_transitions': [dict(run_id=ep['run_id'], **count) for ep, count in zip(eps, transitions, strict=True)],
            'rule_loss_prior_comparison': compare_metrics({'rule_loss': nav_errors(np.concatenate([ep['targets'] for ep in eps]), np.concatenate(normal))['loss']}, retained['models'][0]['panels'][panel], ('rule_loss',))}
    artifacts = {(row.get('candidate'), row.get('arm'), row.get('seed')): row for row in ledger['published_artifacts'] if row.get('kind') == 'responses'}
    for model in retained['models']:
        if model['status'] == 'unattempted': continue
        if model['status'] != 'completed': raise ValueError('Only completed saved response panels admitted')
        key = (model['candidate'], model['arm'], model['seed']); pin = artifacts[key]
        if any(pin[k] != model['responses'][k] for k in ('bytes', 'sha256')): raise ValueError('Published response ledger disagrees with fit receipt')
        shapes = {f'{name}_{i}': (len(ep['targets']), 2) for name in ('teacher_dev', 'advice_dev') for i, ep in enumerate(panels[name])}
        arrays = read_numeric(args.nav_ledger.parent/pin['path'], pin, shapes, deadline); row = {'candidate': key[0], 'arm': key[1], 'seed': key[2], 'panels': {}}
        for panel in ('teacher_dev', 'advice_dev'):
            predictions = [arrays[f'{panel}_{i}'] for i in range(len(panels[panel]))]
            d = nav_decomposition(panels[panel], predictions)
            metrics = dict(d['all']); metrics.update(d['original_recovery_gates'] or {'onset_reverse_recall': None, 'false_reverse_rate': None})
            d['retained_metric_comparison'] = compare_metrics(metrics, model['panels'][panel], ('loss', 'onset_reverse_recall', 'false_reverse_rate'))
            row['panels'][panel] = d
        result['models'].append(row)
    if len(result['models']) != 12: raise ValueError('Exactly twelve completed navigation response artifacts required')
    result['status'] = 'completed'; return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds-cap', type=float, default=600); parser.add_argument('--output-limit-bytes', type=int, default=16*MiB)
    parser.add_argument('--puck-producer', type=Path, required=True); parser.add_argument('--nav-producer', type=Path, required=True)
    parser.add_argument('--puck-ledger', type=Path); parser.add_argument('--nav-ledger', type=Path)
    args = parser.parse_args(argv); started = time.monotonic()
    if not math.isfinite(args.seconds_cap) or not 0 < args.seconds_cap <= 600: parser.error('--seconds-cap must be finite in (0,600]')
    if not 1 <= args.output_limit_bytes <= 64*MiB: parser.error('--output-limit-bytes must be in 1..67108864')
    deadline = started+args.seconds_cap; output = None; pins = {}
    report = {'schema': 'offline-control-diagnostics-v2', 'status': 'failed', 'scope': 'descriptive retained-input diagnostics; no gate evidence',
              'held_out_used': False, 'qualification_claims': [], 'fit_performed': False, 'native_execution': False,
              'model_promoted': False, 'seconds_cap': args.seconds_cap, 'output_limit_bytes': args.output_limit_bytes,
              'actual_cli': [sys.executable, str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)],
              'puck': {'status': 'unattempted'}, 'navigation': {'status': 'unattempted'}}
    try:
        for name in ('repo', 'puck_producer', 'nav_producer'): setattr(args, name, safe_path(getattr(args, name)))
        for track, filename in (('puck', 'm6-puck-fit-ladder.json'), ('nav', 'm7-nav-fit-ladder.json')):
            setattr(args, track+'_ledger', safe_path(getattr(args, track+'_ledger') or args.repo/'docs/reports'/filename))
        # Output can be guarded/readmitted from the frozen JSON path roster without array admission.
        ledgers = {track: read_json(getattr(args, track+'_ledger'), deadline, LEDGER_SHA[track]) for track in ('puck', 'nav')}
        for ledger in ledgers.values():
            if ledger.get('held_out_used') is not False or ledger.get('qualification_claims') != [] or ledger['exploration']['status'] != 'completed': raise ValueError('Exact completed unqualified retained ledgers required')
        pins, protected, collection = ledger_inputs(args, ledgers)
        output = Output(args.output, protected, args.output_limit_bytes)
        report['input_identity'] = {'files': pins, 'status_before': 'pending', 'status_after': 'pending'}
        verify_pins(pins, deadline); report['input_identity']['status_before'] = 'verified'
        import numpy as np
        if np.__version__ != '2.2.5': raise ValueError('Pinned NumPy 2.2.5 required')
        if any(os.environ.get(key) != '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')) or os.environ.get('CUDA_VISIBLE_DEVICES') != '': raise ValueError('Explicit CPU one-thread environment required')
        report['runtime'] = {'python': sys.version.split()[0], 'numpy': np.__version__, 'threads': 1, 'torch_loaded': False}
        report['puck'] = {'status': 'running'}; report['puck'] = run_puck(args, ledgers['puck'], collection, pins, deadline)
        report['navigation'] = {'status': 'running'}; report['navigation'] = run_nav(args, ledgers['nav'], output, pins, deadline)
        verify_pins(pins, deadline); report['input_identity']['status_after'] = 'verified'
        report['status'] = 'completed'
    except (ValueError, OSError, RuntimeError, ImportError, TimeoutError, KeyError, TypeError, zipfile.BadZipFile) as error:
        report['status'] = 'incomplete' if isinstance(error, TimeoutError) else 'failed'
        report['error'] = {'type': type(error).__name__, 'message': str(error)[:2048]}
        for track in ('puck', 'navigation'):
            if report[track]['status'] == 'running': report[track]['status'] = report['status']
    if output is not None:
        try:
            verify_pins(pins, deadline); report['input_identity']['status_after'] = 'verified'
        except (ValueError, OSError, TimeoutError) as error:
            report['input_identity']['status_after'] = 'incomplete' if isinstance(error, TimeoutError) else 'failed'
            report['final_identity_error'] = str(error)[:2048]
            report['status'] = 'incomplete' if isinstance(error, TimeoutError) else 'failed'
        report['elapsed_seconds'] = time.monotonic()-started
        # A compact failure receipt is best effort even on deadline expiry. The
        # outer supervisor remains the hard wall and no scientific work continues.
        try:
            receipt = output.write('report.json', canonical(report), deadline if report['status'] == 'completed' else math.inf)
        except TimeoutError as error:
            report['status'] = 'incomplete'; report['publication_error'] = str(error)
            report['elapsed_seconds'] = time.monotonic()-started
            try: receipt = output.write('report.json', canonical(report))
            except (ValueError, OSError) as publication_error:
                print(canonical({'status': 'failed', 'error': str(publication_error)[:1024]}).decode(), file=sys.stderr); return 1
        except (ValueError, OSError) as error:
            print(canonical({'status': 'failed', 'error': str(error)[:1024]}).decode(), file=sys.stderr); return 1
        print(canonical({'status': report['status'], 'report': str(output.path/'report.json'), 'receipt': receipt}).decode())
    else:
        print(canonical(report).decode(), file=sys.stderr)
    return 0 if report['status'] == 'completed' else 1


if __name__ == '__main__': raise SystemExit(main())
