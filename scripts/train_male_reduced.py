"""Frozen, offline CPU teacher imitation pilot; no lab/runtime integration.

--prepare-only validates source records and prints the frozen manifest without
importing Torch or producing a trained checkpoint. Actual training is explicit.
"""
import argparse
import hashlib
import importlib.metadata
import io
import json
import math
from pathlib import Path
import platform
import sys
import time

from palimpsest import artifacts
from palimpsest.male_model import (CELL_SHA256, FEATURE_PROTOCOL, MAX_RUN_BYTES,
    canonical, check_sources, digest, load_graph, make_model, prepare_splits, reachability, rewire)
from palimpsest.storage import StorageBudget, StorageLimits


INITIAL_PROTOCOL = {'version': 1, 'id': 'male-reduced-artificial-interface-pilot-v1',
    'scene_seeds': {'train': list(range(100, 108)), 'dev': list(range(108, 112)), 'held_out': list(range(112, 116))},
    'episodes_per_run': 1, 'max_ticks_per_run': 150, 'minimum_training_ticks_per_run': 32,
    'recording_plus_snapshot_limit_bytes': MAX_RUN_BYTES, 'aggregate_source_limit_bytes': 1024**3,
    'natural_endings': 'retain goal/stall/contact/time termination; no padding, reset, replacement, or held-out-driven collection',
    'training_seed': 0, 'rewiring_seed': 0, 'variants': ['original', 'degree_rewired'],
    'epochs': 5, 'window': 32, 'optimizer': 'Adam', 'learning_rate': .001, 'gradient_norm_cap': 1.,
    'order': 'frozen CLI run order, increasing episodes/ticks; identical across both variants',
    'hidden_state': 'zero at episode start; carry forward and detach only at training window boundaries',
    'loss': 'mean(0.5*((velocity_error/3)^2 + 1-cos(heading_error_radians)))',
    'selection': 'minimum dev loss across five epochs; first epoch wins exact ties',
    'held_out': 'evaluate once after both dev-selected checkpoints are written; no tuning or selection',
    'recurrent_weights': 'fixed positive connection counts; shared 0.9/original_max_incoming_weight scale for both topologies',
    'trainable': ['artificial encoder', 'upstream readout', 'per-neuron bias', 'recorded-type leak logits'],
    'wall_budget_seconds': 600, 'output_limit_bytes': 64 * 1024**2,
    'claim': 'single-seed compatibility and bounded recorded-input imitation evaluation only',
    'qualification_claims': [], 'biological_sensor_mapping': False, 'female_parameters_loaded': False}


def validate_initial_split(report):
    """Lock the scene assignment before observing any training/evaluation result."""
    for split, seeds in INITIAL_PROTOCOL['scene_seeds'].items():
        sources = report['splits'].get(split, [])
        actual = []
        for source in sources:
            scenario = source.get('scenario')
            if (scenario.get('id') if isinstance(scenario, dict) else scenario) != 'reproduction' or source.get('texture') != 'checker':
                raise ValueError('teacher world profile differs from the frozen reproduction/checker protocol')
            episodes = source['episodes']
            if len(episodes) != 1 or episodes[0]['episode'] != 0:
                raise ValueError('initial pilot requires one fresh episode per teacher run')
            episode = episodes[0]
            minimum = 32 if split == 'train' else 1
            if not minimum <= episode['ticks'] <= 150:
                raise ValueError('insufficient data or excessive ticks in the frozen initial pilot')
            if episode['ticks'] < 150 and source.get('final_phase') not in {'terminated', 'truncated'}:
                raise ValueError('short teacher recording lacks natural terminal outcome')
            if episode['ticks'] < 150 and not isinstance(source.get('last_outcome'), dict):
                raise ValueError('natural teacher ending lacks a recorded outcome')
            actual.append(episode['seed'])
        if sorted(actual) != seeds:
            raise ValueError(f'{split} scene seeds differ from the frozen initial protocol')


def prepare(args):
    graph = load_graph(args.graph, args.graph_manifest)
    cell = artifacts._read(args.cell_source, 1024**2)
    if hashlib.sha256(cell).hexdigest() != CELL_SHA256:
        raise ValueError('pinned upstream cell source hash differs')
    research = getattr(args, 'research_v2', False)
    training = INITIAL_PROTOCOL
    if research:
        from palimpsest.male_research import training as research_training
        training = research_training(args.training_seed)
    data, collection = prepare_splits({'train': args.train, 'dev': args.dev, 'held_out': args.held_out or []},
                                     research_stage='development' if research else None)
    if not research:
        validate_initial_split(collection)
    control, control_report = rewire(graph, training['rewiring_seed'])
    graphs = {'original': graph, 'degree_rewired': control}
    from palimpsest import male_model, records
    sources = {str(Path(module.__file__).name): hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
               for module in (male_model, artifacts, records)}
    sources[Path(__file__).name] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if research:
        from palimpsest import male_research
        sources['male_research.py'] = hashlib.sha256(Path(male_research.__file__).read_bytes()).hexdigest()
    protocol = {'training': training, 'feature_protocol': FEATURE_PROTOCOL,
        'feature_protocol_sha256': digest(FEATURE_PROTOCOL), 'cell_source_sha256': CELL_SHA256,
        'cell_source_path': str(Path(args.cell_source).absolute()), 'source_code_sha256': sources,
        'collection': collection, 'collection_sha256': digest(collection),
        'graphs': {key: {'topology_sha256': value['topology_sha256'], 'ordered_ids_sha256': value['ordered_ids_sha256'],
                        'source_graph_sha256': value['source_graph_sha256'], 'graph_manifest_sha256': value['graph_manifest_sha256'],
                        'type_missing_ids': value['type_missing_ids'], 'reachability': reachability(value)} for key, value in graphs.items()},
        'rewiring': control_report, 'runtime': {'python': platform.python_version(),
            'numpy': importlib.metadata.version('numpy'), 'torch_distribution': importlib.metadata.version('torch')}}
    return data, graphs, protocol


def check_code(protocol):
    root = Path(__file__).resolve().parents[1]
    paths = {path.name: path for path in (root / 'src/palimpsest').glob('*.py')}
    paths['train_male_reduced.py'] = Path(__file__)
    for name, expected in protocol['source_code_sha256'].items():
        if hashlib.sha256(artifacts._read(paths[name], 4 * 1024**2)).hexdigest() != expected:
            raise ValueError('training source changed: ' + name)
    if hashlib.sha256(artifacts._read(protocol['cell_source_path'], 1024**2)).hexdigest() != CELL_SHA256:
        raise ValueError('pinned cell source changed during training')


def loss_for(actions, targets):
    import torch
    return .5 * ((actions[..., 0] - targets[..., 0]).square() / 9 + 1 - torch.cos(actions[..., 1] - targets[..., 1]))


def evaluate(model, episodes, deadline, training=INITIAL_PROTOCOL):
    import torch
    model.eval()
    model.cell.invalidate_caches()
    total, count, velocity, heading = 0., 0, 0., 0.
    with torch.no_grad():
        for episode in episodes:
            hidden = model.reset()
            for start in range(0, len(episode['features']), training['window']):
                if time.monotonic() > deadline:
                    raise TimeoutError('male pilot exceeded the frozen wall budget')
                inputs = torch.from_numpy(episode['features'][start:start + 32]).unsqueeze(1)
                targets = torch.from_numpy(episode['targets'][start:start + 32]).unsqueeze(1)
                hidden, actions = model(inputs, hidden)
                values = loss_for(actions, targets)
                if not torch.isfinite(values).all():
                    raise ValueError('nonfinite male evaluation loss')
                total += float(values.sum())
                count += values.numel()
                velocity += float((actions[..., 0] - targets[..., 0]).abs().sum())
                delta = actions[..., 1] - targets[..., 1]
                heading += float(torch.atan2(torch.sin(delta), torch.cos(delta)).abs().sum())
    if not count:
        raise ValueError('evaluation split contains no samples')
    return {'ticks': count, 'loss': total / count, 'velocity_mae': velocity / count,
            'wrapped_heading_mae_radians': heading / count,
            'interpretation': 'recorded-input teacher imitation; not closed-loop navigation success'}


def fit(graph, data, cell_source, deadline, training=INITIAL_PROTOCOL):
    import torch
    model = make_model(graph, cell_source, training['training_seed'])
    parameters = [parameter for parameter in model.parameters() if parameter.requires_grad]
    optimizer = torch.optim.Adam(parameters, lr=training['learning_rate'])
    history, best_loss, best_state, best_epoch = [], math.inf, None, None
    for epoch in range(training['epochs']):
        model.train()
        model.cell.invalidate_caches()
        total, count = 0., 0
        for episode in data['train']:
            hidden = model.reset()
            for start in range(0, len(episode['features']), training['window']):
                if time.monotonic() > deadline:
                    raise TimeoutError('male pilot exceeded the frozen wall budget')
                optimizer.zero_grad(set_to_none=True)
                inputs = torch.from_numpy(episode['features'][start:start + 32]).unsqueeze(1)
                targets = torch.from_numpy(episode['targets'][start:start + 32]).unsqueeze(1)
                hidden, actions = model(inputs, hidden.detach())
                values = loss_for(actions, targets)
                loss = values.mean()
                if not torch.isfinite(loss):
                    raise ValueError('nonfinite male training loss')
                loss.backward()
                torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
                optimizer.step()
                if any(not torch.isfinite(parameter).all() for parameter in parameters):
                    raise ValueError('nonfinite male parameters after optimizer step')
                total += float(values.detach().sum())
                count += values.numel()
        dev = evaluate(model, data['dev'], deadline, training)
        history.append({'epoch': epoch + 1, 'train_ticks': count, 'train_loss': total / count, 'dev': dev})
        if dev['loss'] < best_loss:
            best_loss, best_epoch = dev['loss'], epoch + 1
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    model.load_state_dict(best_state, strict=True)
    model.cell.invalidate_caches()
    return model, {'selected_epoch': best_epoch, 'history': history,
        'trainable_parameters': sum(parameter.numel() for parameter in parameters),
        'trainable_names': [name for name, parameter in model.named_parameters() if parameter.requires_grad]}


def train(args, data, graphs, protocol):
    """Only call after the actual-runtime window is available; owns storage lease."""
    import torch
    training = protocol['training']
    research = training.get('research_protocol_sha256') is not None
    output = artifacts._safe_path(args.output)
    check_sources(protocol['collection'])
    check_code(protocol)
    if research and output.name != f"seed-{training['training_seed']}":
        raise ValueError('research pair output must use its fixed seed-N directory')
    if any(output.is_relative_to(Path(source['path'])) for split in protocol['collection']['splits'].values() for source in split):
        raise ValueError('training output cannot alter a teacher source run')
    budget = StorageBudget((output.parent,), StorageLimits(max_bytes=training['training_limits']['all_pair_output_bytes'] if research else 1024**3,
        min_free_bytes=1024**3 if research else 256 * 1024**2))
    with budget.lock():
        budget.check(training['output_limit_bytes'], path=output)
        output.mkdir(exist_ok=False)
        files, written = [], 0
        def write(name, payload):
            nonlocal written
            if len(payload) > 8 * 1024**2 or written + len(payload) > training['output_limit_bytes']:
                raise ValueError('male training artifact byte budget exceeded')
            path = output / name
            budget.check(len(payload), path=path)
            with path.open('xb') as stream:
                try:
                    stream.write(payload)
                    stream.flush()
                except BaseException:
                    try:
                        stream.close()
                    finally:
                        path.unlink()
                    raise
            written += len(payload)
            files.append({'path': name, 'sha256': hashlib.sha256(payload).hexdigest(), 'size_bytes': len(payload)})
        report = {'status': 'running', 'protocol_sha256': digest(protocol), 'training_completed': False,
                  'training_attempted': False,
                  'qualification_claims': [], 'models': {}, 'held_out_used_for_selection': False}
        if research:
            report['models'] = {variant: {'status': 'not_started'} for variant in training['variants']}
            report['held_out_status'] = 'locked_unopened'
        active_variant = None
        try:
            write('protocol.json', canonical(protocol))
            deadline = time.monotonic() + training['wall_budget_seconds']
            models = {}
            # Freeze both dev-selected checkpoints before any held-out evaluation.
            for variant in training['variants']:
                report['training_attempted'] = True
                active_variant = variant
                if research:
                    report['models'][variant] = {'status': 'running'}
                model, result = fit(graphs[variant], data, args.cell_source, deadline, training)
                check_sources(protocol['collection'])
                models[variant] = model
                graph_file = variant + '-graph.json'
                write(graph_file, canonical(graphs[variant]))
                checkpoint = {'format': 'palimpsest-male-reduced-v1', 'protocol_sha256': report['protocol_sha256'],
                    'graph_sha256': digest(graphs[variant]), 'ordered_ids_sha256': graphs[variant]['ordered_ids_sha256'],
                    'state_dict': model.state_dict()}
                buffer = io.BytesIO()
                torch.save(checkpoint, buffer)
                filename = variant + '.pt'
                write(filename, buffer.getvalue())
                report['models'][variant] = {**result, 'checkpoint': files[-1], 'graph_file': graph_file,
                    **({'status': 'completed'} if research else {})}
                active_variant = None
            if research:
                report['held_out_status'] = 'locked_unopened'
            else:
                for variant, model in models.items():
                    report['models'][variant]['held_out'] = evaluate(model, data['held_out'], deadline, training)
            check_sources(protocol['collection'])
            report.update(status='completed', training_completed=True)
        except BaseException as error:
            report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:2048]})
            if research and active_variant is not None:
                report['models'][active_variant].update(status='failed', error=report['error'])
            raise
        finally:
            report['finalization_errors'] = []
            for name, check in (('source_code_unchanged', lambda: check_code(protocol)),
                                ('teacher_sources_unchanged', lambda: check_sources(protocol['collection']))):
                report[name] = False
                try:
                    check()
                    report[name] = True
                except BaseException as error:
                    report.update(status='failed', training_completed=False)
                    report['finalization_errors'].append({'check': name, 'type': type(error).__name__, 'message': str(error)[:2048]})
            report['files'] = list(files)
            write('report.json', canonical(report))
    if report['status'] != 'completed':
        raise ValueError('training final source validation failed; retained report is failed')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parents[1]
    parser.add_argument('--graph', type=Path, default=root / 'data/assets/malecns-metadata/reduced-neighborhood-v1b/graph.json')
    parser.add_argument('--graph-manifest', type=Path, default=root / 'data/manifests/malecns-reduced-neighborhood-v1.json')
    parser.add_argument('--cell-source', type=Path, required=True)
    for split in ('train', 'dev', 'held-out'):
        parser.add_argument('--' + split, type=Path, action='append', required=split != 'held-out', help='repeat for each frozen root teacher run')
    parser.add_argument('--research-v2', action='store_true')
    parser.add_argument('--training-seed', type=int, choices=(10, 11, 12))
    parser.add_argument('--prepare-only', action='store_true', help='NumPy/stdlib validation only; no Torch execution or checkpoint')
    parser.add_argument('--output', type=Path, help='new directory required for actual training')
    args = parser.parse_args(argv)
    if (args.research_v2 and (args.training_seed is None or args.held_out)) or (not args.research_v2 and (args.training_seed is not None or not args.held_out)):
        parser.error('v2 requires one paired training seed and unopened held-out; v1 requires held-out and no seed override')
    if not args.prepare_only and args.output is None:
        parser.error('actual training requires an exclusive --output directory')
    try:
        data, graphs, protocol = prepare(args)
        if args.prepare_only:
            report = {'status': 'prepared', 'training_performed': False, 'protocol_sha256': digest(protocol), 'protocol': protocol}
        else:
            report = train(args, data, graphs, protocol)
        print(json.dumps(report, indent=2, allow_nan=False))
        return 0
    except (OSError, ValueError, RuntimeError, ImportError) as error:
        print(json.dumps({'status': 'failed', 'type': type(error).__name__, 'error': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
