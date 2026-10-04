"""EXPLORATORY — not gate evidence. CPU navigation capability probes.

Decision rules frozen here before execution: reproduce every epoch loss and all
selected-checkpoint recorded-dev responses of the six actual original old/aug
fits (absolute 1e-6); any mismatch stops this track. Explore requires that exact
passed receipt and unchanged admitted inputs. Advice scenes 3100/3101 train,
3102/3103 dev, all owners 10/11/12 in each, with old train as foundation and old
teacher dev a separate panel. Train-only normalization leaves contact binary
unchanged. Seeds 10/11/12, identical shuffled episode/window schedules and 2000
Adam updates per reached fit, lr .001 cosine to .00001, clip 1, batch 1/window 32.
Earliest strict combined recorded-dev loss minimum selects each checkpoint.

Ordered candidates: conditioned upstream endpoint model (both original/rewired),
MLP 388-64-64-2, GRU hidden64, then encoder injection also at output nodes in
both graph arms if original graph advice loss exceeds a passing baseline by 25%
in every seed. First candidate passing every seed is chosen; graph candidates
require both arms. Teacher-dev loss <= its recomputed .7/bearing-rule loss;
advice-dev loss <= .8*training-fitted constant loss; advice-dev negative-target
pre-action contact-onset reverse recall >= .8 and nonnegative-target reversals
outside teacher recovery <= .05. Empty/unknown required advice strata fail
eligibility. Old panels without phase metadata report recovery metrics unknown.

Output/readout variation and W removal are diagnostics, not topology evidence.
Degree rewiring preserves degree, not weighted strength. Advice is queried on
executed learner trajectories; retained data cannot establish counterfactual
teacher recovery success. GRU success cannot establish horizon causality, and
failure cannot establish teacher redesign necessity. No reserved scenes, native
rollout, GPU, camera copies, runtime promotion, reader exemptions, auto-retry,
deadline extension or automatic redistribution. qualification_claims=[] always.
"""
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time

SEEDS = (10, 11, 12)
ARMS = ('old-corpus', 'augmented')
MAX_UPDATES = 2000
GiB = 1024**3
HISTORICAL_HEAD = '6feade9770dc40efa567633412baec4347ee33cb'
BUNDLE_PINS = {
    10: ('b6dd3e4143aa7d5e3ab988bae6988e1c68cf680866b5758d897af9ef3b949640', '8ccee3be54f42910c3a2f34b61bc99e31cd8d7b518f891c3c67e297a495d63d6'),
    11: ('275675660aa8132271aa2886bbb5f75acc214f46b3fc394117ecdc2949ef21ae', '12c217942093d763d51e02fc1e03727a13367c4d83fd6e9f5755b320f1adeeb6'),
    12: ('8b68b7b123187d31b749cefe02b070756483894bc5f84b7b240eb8b61a2f7ace', '5c283107aa2e4beb4980a2c930baf3fe5d988254407b03867874d25069353c4d')}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)+'\n').encode()


def check_deadline(deadline):
    if time.monotonic() >= deadline: raise TimeoutError('Explicit navigation stage deadline exhausted')


def sha(path, maximum=160*1024**2, deadline=math.inf):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
        raise ValueError('Regular bounded nonsymlink input required: '+str(path))
    h = hashlib.sha256(); size = 0
    with path.open('rb') as stream:
        while block := stream.read(1024**2):
            check_deadline(deadline); size += len(block)
            if size > maximum: raise ValueError('Input exceeded bounded read')
            h.update(block)
    return h.hexdigest()


def read_json(path, expected=None):
    observed = sha(path, 4*1024**2)
    if expected is not None and observed != expected: raise ValueError('Pinned JSON changed: '+str(path))
    return json.loads(Path(path).read_bytes(), parse_constant=lambda x: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))


def guard_output(path, inputs):
    raw = Path(path).absolute()
    if any(p.is_symlink() for p in (raw, *raw.parents)): raise ValueError('Symlink output refused')
    actual = raw.resolve()
    if actual.exists(): raise ValueError('Fresh exclusive output required')
    for source in inputs:
        source = Path(source).resolve()
        if actual == source or actual.is_relative_to(source) or source.is_relative_to(actual):
            raise ValueError('Output overlaps immutable input tree')
    return actual


class Output:
    def __init__(self, path, inputs, *, max_bytes=GiB, min_free=2*GiB):
        self.path = guard_output(path, inputs)
        self.max_bytes, self.min_free, self.written = max_bytes, min_free, 0
        parent = self.path.parent
        while not parent.exists(): parent = parent.parent
        if shutil.disk_usage(parent).free < min_free: raise ValueError('2 GiB free floor')
        self.path.mkdir(parents=True, exist_ok=False)

    def write(self, name, payload):
        if Path(name).name != name or name in ('.', '..'): raise ValueError('Output basename required')
        if len(payload)+self.written > self.max_bytes: raise ValueError('Own output byte cap exceeded')
        if shutil.disk_usage(self.path).free-len(payload) < self.min_free: raise ValueError('Output free floor')
        with (self.path/name).open('xb') as stream:
            stream.write(payload); stream.flush(); os.fsync(stream.fileno())
        self.written += len(payload)
        return {'path': name, 'bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}


def historical_binding(args, deadline):
    root, bundles = args.historical_root.resolve(), args.historical_bundles.resolve()
    if subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, timeout=5).strip() != HISTORICAL_HEAD:
        raise ValueError('Pinned historical producer HEAD differs')
    protocols, reports, pins = {}, {}, {}
    for seed in SEEDS:
        b = bundles/f'seed-{seed}'
        protocols[seed] = read_json(b/'protocol.json', BUNDLE_PINS[seed][0])
        reports[seed] = read_json(b/'report.json', BUNDLE_PINS[seed][1])
        for name, pin in zip(('protocol.json', 'report.json'), BUNDLE_PINS[seed]): pins[str(b/name)] = pin
        p, r = protocols[seed], reports[seed]
        if p['seed'] != seed or r['status'] != 'completed-navigation-research-training':
            raise ValueError('Actual completed historical pair required')
        sources = p['source_code']
        for name, pin in {**sources['named_reader_sources'], **sources['added_sources']}.items():
            path = root/name
            if sha(path, deadline=deadline) != pin: raise ValueError('Historical reader source drift: '+name)
            pins[str(path)] = pin
        pins[str(root/'uv.lock')] = sources['lock_sha256']
        pins.update(p['model_inputs'])
        for arm in ARMS:
            item = r['models'][arm]['checkpoint']; path = b/item['path']
            if path.parent != b or sha(path, 8*1024**2, deadline) != item['sha256']:
                raise ValueError('Pinned historical checkpoint differs')
            pins[str(path)] = item['sha256']
    # Pin this runner as well: receipt cannot bless a different implementation.
    pins[str(Path(__file__).resolve())] = sha(__file__)
    binding = {'historical_root': str(root), 'historical_bundles': str(bundles), 'head': HISTORICAL_HEAD,
               'files': pins, 'qualification_claims': []}
    check_binding(binding, deadline)
    return binding, protocols, reports


def check_binding(binding, deadline):
    for name, expected in binding['files'].items():
        if sha(name, deadline=deadline) != expected: raise ValueError('Bound input changed: '+name)


def load_historical(root):
    # Physical ROOT is binding. Do not import the local helper then reassign ROOT.
    if any(n == 'palimpsest' or n.startswith('palimpsest.') or n in
           ('train_male_navigation_v2', 'train_male_reduced', 'prepare_male_navigation_v2') for n in sys.modules):
        raise ValueError('Historical runner must start before project imports')
    class NoNative:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] == 'mujoco': raise ImportError('Native runtime forbidden')
    sys.meta_path.insert(0, NoNative())
    sys.path[:0] = [str(root/'src'), str(root/'scripts')]
    import train_male_navigation_v2 as trainer
    import train_male_reduced as reduced
    if trainer.ROOT != root or Path(reduced.__file__).resolve() != root/'scripts/train_male_reduced.py':
        raise ValueError('Loaded producer helper path differs')
    return trainer, reduced


def prepare_historical(args, output, protocols, trainer, deadline):
    p = protocols[10]
    paths = p['model_inputs']
    graph = next(Path(x) for x in paths if x.endswith('source-graph.json'))
    graph_manifest = next(Path(x) for x in paths if x.endswith('malecns-reduced-neighborhood-v1.json'))
    cell = next(Path(x) for x in paths if x.endswith('connectome_rnn_model.py'))
    prepare_args = argparse.Namespace(training_seed=10, graph=graph, graph_manifest=graph_manifest,
        cell_source=cell, output=output.path/'admission'/'seed-10')
    _, data, graph, context = trainer.prepare(prepare_args, deadline)
    return data, graph, context, cell


def cpu_runtime(trainer):
    if any(os.environ.get(n) != '1' for n in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS')):
        raise ValueError('Explicit one-thread CPU environment required')
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '': raise ValueError('CUDA must be hidden')
    import torch
    torch.set_num_threads(1); torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    return trainer.cpu_runtime(torch)


def predict(model, episodes, deadline, *, activity=False):
    import numpy as np
    import torch
    model.eval()
    if hasattr(model, 'cell'): model.cell.invalidate_caches()
    responses, nodes = [], []
    with torch.no_grad():
        for ep in episodes:
            hidden = model.reset(); chunks, activations = [], []
            for start in range(0, len(ep['features']), 32):
                check_deadline(deadline)
                x = torch.from_numpy(ep['features'][start:start+32]).unsqueeze(1)
                hidden, actions = model(x, hidden)
                if not torch.isfinite(actions).all(): raise ValueError('Nonfinite prediction')
                chunks.append(actions[:, 0].numpy().copy())
                if activity and hasattr(model, 'cell'):
                    activations.append(hidden[0, model.cell.output_nodes].numpy().copy())
            responses.append(np.concatenate(chunks))
            if activations: nodes.append(np.stack(activations))
    summary = {'sample': 'output-node state at window ends only', 'count': sum(len(x) for x in nodes)}
    if nodes:
        values = np.concatenate(nodes)
        summary.update(mean_abs=float(np.abs(values).mean()), std=float(values.std()),
                       nonzero_fraction=float((np.abs(values) > 1e-8).mean()))
    return (responses, summary) if activity else responses


def compare_reproduction(actual, expected, responses, retained):
    import numpy as np
    if actual['selected_epoch'] != expected['selected_epoch'] or len(actual['history']) != len(expected['history']):
        raise ValueError('Historical epoch selection/history differs')
    maximum = 0.
    for a, b in zip(actual['history'], expected['history'], strict=True):
        if a['epoch'] != b['epoch']: raise ValueError('Historical epoch order differs')
        for left, right in ((a['train_loss'], b['train_loss']), (a['dev']['loss'], b['dev']['loss'])):
            if not math.isfinite(left) or not math.isfinite(right) or abs(left-right) > 1e-6:
                raise ValueError('Historical per-epoch loss mismatch')
            maximum = max(maximum, abs(left-right))
    if len(responses) != len(retained): raise ValueError('Historical response roster differs')
    for a, b in zip(responses, retained, strict=True):
        if a.shape != b.shape or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('Historical response shape/finite mismatch')
        delta = float(np.abs(a-b).max())
        if delta > 1e-6: raise ValueError('Historical selected-checkpoint response mismatch')
        maximum = max(maximum, delta)
    return maximum


def require_reproduction(receipt, binding):
    expected = {(s, a) for s in SEEDS for a in ARMS}
    actual = {(x.get('seed'), x.get('arm')) for x in receipt.get('models', []) if x.get('status') == 'passed'}
    if (receipt.get('stage') != 'reproduce' or receipt.get('status') != 'passed' or actual != expected or
            len(receipt['models']) != 6 or receipt.get('binding') != binding or
            receipt.get('inputs_unchanged_after') is not True or
            any(not math.isfinite(x.get('max_absolute_difference', math.inf)) or
                not 0 <= x['max_absolute_difference'] <= 1e-6 for x in receipt['models'])):
        raise ValueError('Exact passed six-fit reproduction receipt required')


def grouped_split(old_train, old_dev, advice):
    expected = {(scene, owner) for scene in range(3100, 3104) for owner in SEEDS}
    keys = [(ep['scene_seed'], ep['learner_seed']) for ep in advice]
    if len(keys) != 12 or set(keys) != expected: raise ValueError('All owners in exact seen scene groups required')
    episodes = [*old_train, *old_dev, *advice]
    identities = [(ep['run_id'], ep['episode']) for ep in episodes]
    if len(identities) != len(set(identities)): raise ValueError('Duplicate/cross-panel source episode')
    train = [ep for ep in advice if ep['scene_seed'] in (3100, 3101)]
    dev = [ep for ep in advice if ep['scene_seed'] in (3102, 3103)]
    return {'train': [*old_train, *train], 'teacher_dev': old_dev, 'advice_dev': dev}


def exploration_data(data, context, trainer, deadline):
    import numpy as np
    reader = trainer.data_reader
    manifest = context['manifest']
    collection_pin = manifest['input_documents']['accepted_collection']
    collection = reader.read_json(collection_pin['path'], expected=collection_pin['sha256'])
    by_run = {x['run_id']: x for x in data['augmented']['train']}
    by_owner = {x['run']: (case, x) for case, x in collection['cases'].items()}
    advice, audit = [], []
    for source in manifest['new_sources']:
        check_deadline(deadline)
        ep = dict(by_run[source['run_id']]); ep.update(scene_seed=source['scene_seed'], learner_seed=source['learner_seed'])
        case, owner_pin = by_owner[source['path']]
        path = Path(collection_pin['path']).parent/case/'result.json'
        owner = reader.read_json(path, expected=owner_pin['result_sha256'])
        rows = owner['rows']
        if len(rows) != len(ep['targets']): raise ValueError('Advice phase cursor mismatch')
        recovery, onset, differences = [], [], 0
        previous = False
        for tick, row in enumerate(rows):
            query = row['advice']; target = np.asarray(query['expert_action'], np.float32)
            if row['tick'] != tick or not np.array_equal(target, ep['targets'][tick]):
                raise ValueError('Advice pre-action label alignment differs')
            if trainer.data_reader.helpers()[4].recovery.validate_query(query) != query['transition']:
                raise ValueError('Advice recovery transition differs')
            bad = query['contact']['bad']
            if type(bad) is not bool or bool(ep['features'][tick, 384]) != bad: raise ValueError('Advice pre-action contact differs')
            recovery.append(query['before']['phase'] == 'back' or query['transition']['started'])
            onset.append(bad and not previous); previous = bad
            differences += not np.array_equal(target, np.asarray(row['executed_action'], np.float32))
        ep.update(recovery=np.asarray(recovery, bool), onset=np.asarray(onset, bool))
        advice.append(ep)
        context['model_inputs'][str(path)] = owner_pin['result_sha256']
        audit.append({'run_id': ep['run_id'], 'scene_seed': ep['scene_seed'], 'owner': ep['learner_seed'],
            'rows': len(rows), 'advice_vs_executed_different': differences,
            'pre_action_contact_onset_rows': int(ep['onset'].sum()),
            'pre_action_sustained_contact_rows': int(((ep['features'][:, 384] != 0) & ~ep['onset']).sum()),
            'teacher_recovery_emission_rows': int(ep['recovery'].sum()),
            'negative_target_contact_onset_rows': int((ep['onset'] & (ep['targets'][:, 0] < 0)).sum()),
            'label': 'validated queried advice on executed learner trajectory',
            'counterfactual_teacher_recovery_success': 'not identifiable from retained trajectory'})
    panels = grouped_split(data['old-corpus']['train'], data['old-corpus']['dev'], advice)
    for name, episodes in panels.items():
        for ep in episodes:
            if not np.isfinite(ep['features']).all() or not np.isfinite(ep['targets']).all(): raise ValueError('Nonfinite admitted arrays')
            if ep['features'].dtype != np.float32 or ep['targets'].dtype != np.float32: raise ValueError('CPU float32 arrays required')
    return panels, audit


def statistics(episodes):
    import numpy as np
    values = np.concatenate([x['features'] for x in episodes]).astype(np.float64)
    if not np.isfinite(values).all(): raise ValueError('Nonfinite training normalization')
    mean, scale = values.mean(0), values.std(0)
    scale[scale == 0] = 1; mean[384], scale[384] = 0, 1
    return mean.astype(np.float32), scale.astype(np.float32)


def constant_fit(episodes):
    import numpy as np
    y = np.concatenate([x['targets'] for x in episodes]).astype(np.float64)
    return np.array([y[:, 0].mean(), np.arctan2(np.sin(y[:, 1]).mean(), np.cos(y[:, 1]).mean())], np.float32)


def numpy_loss(a, y):
    import numpy as np
    return .5*((a[:, 0]-y[:, 0])**2/9+1-np.cos(a[:, 1]-y[:, 1]))


def panel_metrics(episodes, predictions, constant):
    import numpy as np
    target = np.concatenate([x['targets'] for x in episodes]); actions = np.concatenate(predictions)
    if actions.shape != target.shape or not len(actions) or not np.isfinite(actions).all() or not np.isfinite(target).all():
        raise ValueError('Invalid finite panel responses/targets')
    rule = np.concatenate([np.column_stack((np.full(len(x['targets']), .7),
                           np.arctan2(x['features'][:, 387], x['features'][:, 386]))) for x in episodes])
    delta = actions[:, 1]-target[:, 1]
    result = {'ticks': len(target), 'loss': float(numpy_loss(actions, target).mean()),
        'wrapped_heading_mae_radians': float(np.abs(np.arctan2(np.sin(delta), np.cos(delta))).mean()),
        'velocity_mae': float(np.abs(actions[:, 0]-target[:, 0]).mean()),
        'rule_loss': float(numpy_loss(rule, target).mean()),
        'constant_loss': float(numpy_loss(np.broadcast_to(constant, target.shape), target).mean()),
        'output_std': actions.std(0).tolist(), 'output_range': np.ptp(actions, axis=0).tolist(),
        'onset_negative_count': 0, 'onset_reverse_recall': None,
        'false_reverse_count': 0, 'false_reverse_rate': None, 'recovery_alignment': 'unknown', 'per_scene': []}
    if all('recovery' in x and 'onset' in x for x in episodes):
        recovery = np.concatenate([x['recovery'] for x in episodes]); onset = np.concatenate([x['onset'] for x in episodes])
        if recovery.dtype != bool or onset.dtype != bool or recovery.shape != (len(target),) or onset.shape != (len(target),):
            raise ValueError('Aligned boolean recovery/onset required')
        required = onset & (target[:, 0] < 0); outside = (target[:, 0] >= 0) & ~recovery
        result.update(onset_negative_count=int(required.sum()), false_reverse_count=int(outside.sum()), recovery_alignment='validated pre-action phase')
        if required.any(): result['onset_reverse_recall'] = float((actions[required, 0] < 0).mean())
        if outside.any(): result['false_reverse_rate'] = float((actions[outside, 0] < 0).mean())
    for ep, a in zip(episodes, predictions, strict=True):
        result['per_scene'].append({'scene': ep.get('scene_seed', ep['run_id']), 'run_id': ep['run_id'],
            'owner': ep.get('learner_seed'), 'ticks': len(a), 'loss': float(numpy_loss(a, ep['targets']).mean())})
    return result


def eligible(panels):
    t, a = panels['teacher_dev'], panels['advice_dev']
    return (t['loss'] <= t['rule_loss'] and a['loss'] <= .8*a['constant_loss'] and
            a['onset_reverse_recall'] is not None and a['onset_reverse_recall'] >= .8 and
            a['false_reverse_rate'] is not None and a['false_reverse_rate'] <= .05)


def windows(episodes, seed, updates):
    rng = random.Random(seed); completed = 0; epoch = 0
    if not episodes or any(not len(e['features']) for e in episodes): raise ValueError('Nonempty episodes required')
    while completed < updates:
        order = list(range(len(episodes))); rng.shuffle(order); epoch += 1
        for index in order:
            for start in range(0, len(episodes[index]['features']), 32):
                yield epoch, index, start, min(start+32, len(episodes[index]['features']))
                completed += 1
                if completed == updates: return


def make_probe(kind, graph, cell_source, seed, mean, scale, *, maker=None):
    import numpy as np
    import torch
    if mean.shape != (388,) or scale.shape != (388,) or not np.isfinite(mean).all() or not np.isfinite(scale).all() or np.any(scale <= 0):
        raise ValueError('Finite training-only normalization required')
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    base = None
    if kind in ('conditioned', 'injection'):
        if maker is None:
            from palimpsest.male_model import make_model
            maker = make_model
        base = maker(graph, cell_source, seed)
        if kind == 'injection':
            # Same actual upstream cell and endpoint head; enlarge only its input
            # injection list and artificial encoder, identically in both arms.
            base.cell.input_nodes = torch.cat((base.cell.input_nodes, base.cell.output_nodes))
            base.encoder = torch.nn.Sequential(torch.nn.Linear(388, len(base.cell.input_nodes)), torch.nn.Tanh())
    class Probe(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.register_buffer('mean', torch.from_numpy(mean.copy()))
            self.register_buffer('scale', torch.from_numpy(scale.copy()))
            if base is not None:
                self.encoder, self.cell = base.encoder, base.cell
            elif kind == 'mlp':
                self.network = torch.nn.Sequential(torch.nn.Linear(388, 64), torch.nn.Tanh(),
                    torch.nn.Linear(64, 64), torch.nn.Tanh(), torch.nn.Linear(64, 2))
            elif kind == 'gru':
                self.gru = torch.nn.GRU(388, 64); self.head = torch.nn.Linear(64, 2)
            else: raise ValueError('Unknown fixed probe')

        def reset(self):
            if base is not None: return base.reset()
            return torch.zeros((1, 1, 64) if kind == 'gru' else (1, 1), dtype=torch.float32)

        def forward(self, inputs, hidden):
            expected = self.reset().shape
            if (inputs.device.type != 'cpu' or inputs.dtype != torch.float32 or inputs.ndim != 3 or
                    inputs.shape[1:] != (1, 388) or not 1 <= inputs.shape[0] <= 32 or
                    hidden.device.type != 'cpu' or hidden.dtype != torch.float32 or hidden.shape != expected or
                    not torch.isfinite(inputs).all() or not torch.isfinite(hidden).all()):
                raise ValueError('Bounded finite CPU float32 probe input/state required')
            x = (inputs-self.mean)/self.scale
            if not torch.isfinite(x).all(): raise ValueError('Nonfinite conditioned feature window')
            if base is not None:
                hidden, raw, _ = self.cell(hidden, self.encoder(x), store_sequence=True, checkpoint_steps=False)
            elif kind == 'gru':
                out, hidden = self.gru(x, hidden); raw = self.head(out)
            else: raw = self.network(x)
            actions = torch.tanh(raw)*raw.new_tensor([3., math.pi])
            if not torch.isfinite(actions).all() or not torch.isfinite(hidden).all(): raise ValueError('Nonfinite probe output/state')
            return hidden, actions
    return Probe()


def fit_probe(model, panels, seed, deadline, reduced, *, updates=MAX_UPDATES):
    import torch
    if not 1 <= updates <= MAX_UPDATES: raise ValueError('Bounded fixed optimizer budget')
    parameters = [p for p in model.parameters() if p.requires_grad]
    optimizer = torch.optim.Adam(parameters, lr=.001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=updates, eta_min=.00001)
    best, state, selected, history = math.inf, None, None, []
    constant = constant_fit(panels['train'])
    previous_epoch = None; completed = 0; hidden = None
    def assess():
        nonlocal best, state, selected
        metrics = {name: panel_metrics(panels[name], predict(model, panels[name], deadline), constant)
                   for name in ('teacher_dev', 'advice_dev')}
        value = sum(x['loss']*x['ticks'] for x in metrics.values())/sum(x['ticks'] for x in metrics.values())
        history.append({'updates': completed, 'combined_dev_loss': value,
                        'teacher_dev_loss': metrics['teacher_dev']['loss'], 'advice_dev_loss': metrics['advice_dev']['loss']})
        if value < best:
            best, selected = value, completed
            state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    for epoch, index, start, stop in windows(panels['train'], seed, updates):
        check_deadline(deadline)
        if previous_epoch is not None and previous_epoch != epoch: assess()
        previous_epoch = epoch
        model.train()
        if hasattr(model, 'cell'): model.cell.invalidate_caches()
        if start == 0: hidden = model.reset()
        ep = panels['train'][index]
        optimizer.zero_grad(set_to_none=True)
        x = torch.from_numpy(ep['features'][start:stop]).unsqueeze(1)
        y = torch.from_numpy(ep['targets'][start:stop]).unsqueeze(1)
        hidden, actions = model(x, hidden.detach())
        loss = reduced.loss_for(actions, y).mean()
        if not torch.isfinite(loss): raise ValueError('Nonfinite exploratory loss')
        loss.backward(); torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
        optimizer.step(); scheduler.step(); completed += 1
        if any(not torch.isfinite(p).all() for p in parameters): raise ValueError('Nonfinite exploratory parameters')
    assess(); model.load_state_dict(state, strict=True)
    if hasattr(model, 'cell'): model.cell.invalidate_caches()
    metrics, predictions = {}, {}
    for name in ('teacher_dev', 'advice_dev'):
        actions, activity = predict(model, panels[name], deadline, activity=True)
        predictions[name] = actions
        metrics[name] = {**panel_metrics(panels[name], actions, constant), 'readout_activity': activity}
    diagnostic = {'interpretation': 'W removal is recorded-input sensitivity, not topology qualification', 'panels': {}}
    if hasattr(model, 'cell'):
        original = model.cell.W_values.detach().clone()
        try:
            with torch.no_grad(): model.cell.W_values.zero_()
            model.cell.invalidate_caches()
            import numpy as np
            for name in predictions:
                removed = predict(model, panels[name], deadline)
                changes = np.concatenate([a-b for a, b in zip(predictions[name], removed, strict=True)])
                diagnostic['panels'][name] = {'mean_abs_response_change': np.abs(changes).mean(0).tolist(),
                    'removed_W_loss': panel_metrics(panels[name], removed, constant)['loss']}
        finally:
            with torch.no_grad(): model.cell.W_values.copy_(original)
            model.cell.invalidate_caches()
    return {'updates': completed, 'selected_update': selected, 'history': history,
        'trainable_parameters': sum(p.numel() for p in parameters),
        'total_parameters': sum(p.numel() for p in model.parameters()),
        'schedule_sha256': hashlib.sha256(canonical(list(windows(panels['train'], seed, updates)))).hexdigest(), 'panels': metrics,
        'eligible': eligible(metrics), 'W_removal': diagnostic}, predictions


def run(args, actual_cli):
    started = time.monotonic(); deadline = started+args.seconds
    binding, protocols, retained = historical_binding(args, deadline)
    trainer, reduced = load_historical(args.historical_root.resolve())
    # Output guard includes all immutable source/collection parents, not merely
    # model paths. Admission itself runs only within this explicit stage cap.
    plan = trainer.protocol(); manifest = trainer.pinned_documents(plan, deadline)['data_manifest']
    inputs = [args.historical_root, args.historical_bundles, Path(manifest['historical_reader']['root'])]
    inputs += [Path(x['path']) for x in manifest['old_sources']+manifest['new_sources']]
    inputs += [Path(x['path']).parent for x in manifest['input_documents'].values()]
    inputs += [(trainer.ROOT/x['path']).resolve().parent for x in plan['immutable_prerequisites'].values()]
    if args.reproduction_receipt: inputs.append(args.reproduction_receipt.parent)
    output = Output(args.output, inputs)
    report = {'stage': args.stage, 'status': 'running', 'label': 'EXPLORATORY — not gate evidence',
        'actual_cli': actual_cli, 'binding': binding, 'seconds_cap': args.seconds, 'output_limit_bytes': GiB,
        'min_free_bytes': 2*GiB, 'models': [], 'qualification_claims': [], 'held_out': 'locked_unopened',
        'recipe': {'seeds': list(SEEDS), 'updates': MAX_UPDATES, 'window': 32, 'device': 'cpu', 'dtype': 'float32',
                   'threads': 1, 'lr': .001, 'cosine_end_lr': .00001, 'clip': 1,
                   'order': 'random.Random(seed) shuffles episodes each epoch; consecutive 32-tick windows; detach carry; episode reset'}, 'files': []}
    context = None; active = None
    try:
        if args.stage == 'explore':
            require_reproduction(read_json(args.reproduction_receipt), binding)
            report['reproduction_receipt_sha256'] = sha(args.reproduction_receipt)
        data, graph, context, cell = prepare_historical(args, output, protocols, trainer, deadline)
        report['admitted_input_identity'] = {'code': context['code'], 'historical': context['historical'],
            'documents': context['documents'], 'source_files': context['source_files'], 'model_inputs': context['model_inputs']}
        report['runtime'] = cpu_runtime(trainer)
        import torch
        if args.stage == 'reproduce':
            report['models'] = [{'seed': s, 'arm': a, 'status': 'unattempted'} for s in SEEDS for a in ARMS]
            for item in report['models']:
                check_deadline(deadline); active = item; item['status'] = 'running'
                s, arm = item['seed'], item['arm']
                model, result = reduced.fit(graph, data[arm], cell, deadline, protocols[s]['training'][arm])
                trainer.validate_fit(result, arm)
                historical = reduced.make_model(graph, cell, s)
                checkpoint = retained[s]['models'][arm]['checkpoint']
                payload = torch.load(args.historical_bundles/f'seed-{s}'/checkpoint['path'], map_location='cpu', weights_only=True)
                historical.load_state_dict(payload['state_dict'], strict=True)
                delta = compare_reproduction(result, retained[s]['models'][arm],
                    predict(model, data[arm]['dev'], deadline), predict(historical, data[arm]['dev'], deadline))
                item.update(status='passed', max_absolute_difference=delta, history=result['history'],
                            selected_epoch=result['selected_epoch'], response_ticks=sum(len(x['targets']) for x in data[arm]['dev']))
                trainer.check_context(context, deadline); check_binding(binding, deadline)
                del model, historical, payload; active = None
            report['status'] = 'passed'
        else:
            panels, audit = exploration_data(data, context, trainer, deadline)
            mean, scale = statistics(panels['train']); constant = constant_fit(panels['train'])
            report.update(advice_label_audit=audit, train_statistics={'mean': mean.tolist(), 'scale': scale.tolist(), 'constant': constant.tolist()},
                split_assignments={name: [{'run_id': e['run_id'], 'episode': e['episode'], 'scene_seed': e.get('scene_seed'),
                    'owner': e.get('learner_seed'), 'ticks': len(e['targets']),
                    'feature_target_sha256': hashlib.sha256(e['features'].tobytes()+e['targets'].tobytes()).hexdigest()} for e in eps]
                    for name, eps in panels.items()}, parent_manifest_sha256=trainer.DATA_SHA,
                limitations=['Degree rewiring preserves degree but not weighted strength', 'Old teacher recovery metadata unknown',
                    'Recorded-input imitation only; no counterfactual recovery success or topology qualification'])
            control, control_report = trainer.male_model.rewire(graph, 0)
            report['rewiring'] = control_report
            graphs = {'original': graph, 'degree_rewired': control}
            candidates = ('conditioned', 'mlp', 'gru', 'injection')
            report['models'] = [{'candidate': c, 'seed': s, 'arm': arm, 'status': 'unattempted'}
                for c in candidates for s in SEEDS for arm in (graphs if c in ('conditioned', 'injection') else ('graph-free',))]
            passing_baseline = None; chosen = None
            for candidate in candidates:
                if candidate == 'gru' and passing_baseline is not None:
                    for row in report['models']:
                        if row['candidate'] == candidate: row['reason'] = 'First passing graph-free baseline already reached'
                    continue
                if candidate == 'injection':
                    graph_rows = [x for x in report['models'] if x['candidate'] == 'conditioned' and x['arm'] == 'original']
                    baseline_rows = [x for x in report['models'] if x['candidate'] == passing_baseline]
                    reached = passing_baseline is not None and all(g['panels']['advice_dev']['loss'] >
                        1.25*b['panels']['advice_dev']['loss'] for g, b in zip(graph_rows, baseline_rows, strict=True))
                    if not reached:
                        for row in report['models']:
                            if row['candidate'] == candidate: row['reason'] = 'Conditional 25% graph-lag trigger not met in all seeds'
                        break
                rows = [x for x in report['models'] if x['candidate'] == candidate]
                for item in rows:
                    check_deadline(deadline); active = item; item['status'] = 'running'
                    model = make_probe(candidate, graphs.get(item['arm']), cell, item['seed'], mean, scale, maker=reduced.make_model)
                    result, predictions = fit_probe(model, panels, item['seed'], deadline, reduced)
                    item.update(result, status='completed')
                    prefix = f"{candidate}-{item['arm']}-seed-{item['seed']}"
                    stream = io.BytesIO(); torch.save({'format': 'exploratory-nav-probe-v1', 'state_dict': model.state_dict()}, stream)
                    item['checkpoint'] = output.write(prefix+'.pt', stream.getvalue())
                    import numpy as np
                    stream = io.BytesIO(); np.savez(stream, **{f'{name}_{i}': a for name, values in predictions.items() for i, a in enumerate(values)})
                    item['responses'] = output.write(prefix+'.npz', stream.getvalue())
                    report['files'].extend((item['checkpoint'], item['responses']))
                    trainer.check_context(context, deadline); check_binding(binding, deadline)
                    del model, predictions; active = None
                passed = all(x['eligible'] for x in rows)
                if passed and chosen is None: chosen = candidate
                if candidate == 'conditioned' and passed:
                    for row in report['models']:
                        if row['status'] == 'unattempted': row['reason'] = 'First candidate passed all seeds and both graph arms'
                    break
                if candidate in ('mlp', 'gru') and passed:
                    passing_baseline = candidate
                    # First passing baseline wins; reach conditional graph probe next.
                    if candidate == 'mlp': continue
                if candidate == 'gru' and passing_baseline is None:
                    for row in report['models']:
                        if row['candidate'] == 'injection': row['reason'] = 'No passing graph-free baseline for conditional graph probe'
                    break
            report.update(status='completed', chosen_candidate=chosen,
                decision='first passing candidate' if chosen else 'stop fitting: no passing reached candidate')
        trainer.check_context(context, deadline); check_binding(binding, deadline)
    except BaseException as error:
        report.update(status='incomplete' if isinstance(error, TimeoutError) else 'failed',
                      error={'type': type(error).__name__, 'message': str(error)[:1024]})
        if active is not None: active.update(status='incomplete' if isinstance(error, TimeoutError) else 'failed', error=report['error'])
        for item in report['models']:
            if item['status'] == 'unattempted': item.setdefault('reason', 'Stage stopped: '+report['error']['type'])
        raise
    finally:
        report['elapsed_seconds'] = time.monotonic()-started
        try:
            # Final admission also consumes this stage's cap; do not prolong an
            # expired cap to perform a full corpus rehash. Keep explicit unknown.
            check_deadline(deadline)
            if context is not None: trainer.check_context(context, deadline)
            check_binding(binding, deadline)
            report['inputs_unchanged_after'] = True
        except TimeoutError:
            report.update(status='incomplete', inputs_unchanged_after=None,
                final_input_error='Stage deadline exhausted; final full source inventory incomplete')
        except Exception as error:
            report.update(status='failed', inputs_unchanged_after=False, final_input_error=str(error)[:1024])
        output.write('report.json', canonical(report))
    if report['status'] not in ('passed', 'completed'): raise ValueError('Final input identity failed')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=('reproduce', 'explore'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=int, required=True)
    parser.add_argument('--historical-root', type=Path, required=True)
    parser.add_argument('--historical-bundles', type=Path, required=True)
    parser.add_argument('--reproduction-receipt', type=Path)
    args = parser.parse_args(argv)
    maximum = 1200 if args.stage == 'reproduce' else 3000
    if not 1 <= args.seconds <= maximum: parser.error(f'--seconds must be 1..{maximum}')
    if (args.stage == 'explore') != (args.reproduction_receipt is not None): parser.error('Only explore requires --reproduction-receipt')
    try:
        report = run(args, [sys.executable, str(Path(__file__).resolve()), *(sys.argv[1:] if argv is None else argv)])
        print(json.dumps({'status': report['status'], 'output': str(args.output), 'qualification_claims': []}))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError, TimeoutError) as error:
        print(json.dumps({'status': 'failed', 'type': type(error).__name__, 'error': str(error)[:1024]}), file=sys.stderr)
        return 1


if __name__ == '__main__': raise SystemExit(main())
