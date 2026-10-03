"""Fixed old/advice-augmented original-graph pair; no production admission."""
import argparse
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import platform
import time

from palimpsest import artifacts, male_model
from palimpsest.storage import StorageBudget, StorageLimits
import prepare_male_navigation_v2 as data_reader
from train_male_reduced import fit, evaluate, make_model
from train_male_recovery import write_artifact, stage_report, publish_report

ROOT = Path(__file__).resolve().parents[1]
SELF_SHA = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
PLAN_SHA = '76a502de80b22d2592d8b4eb1e07f96cdaa3602fb64196eade4eb59e962a3928'
DATA_SHA = '47c4523c40e485ba4839cc80c9db891761791b801cc777755028122a1dbacb41'
GRAPH_MANIFEST_SHA = '7a205342b4ada8ab8b78d6ca866c61735003e601531c65a1c1b6c819df00026f'
ARMS = ('old-corpus', 'augmented')
MiB = 1024**2
MAX_REPORT, MAX_FILE = 4*MiB, 8*MiB


def protocol():
    return data_reader.read_json(ROOT/'docs/plans/m7-navigation-training-v2-protocol.json', expected=PLAN_SHA)


def fixed_training(seed, arm):
    if type(seed) is not int or seed not in (10, 11, 12) or arm not in ARMS:
        raise ValueError('Fixed seed 10/11/12 and old-corpus/augmented arm required')
    p = protocol()
    return {**p['training_inherited'], 'training_seed': seed, 'arm': arm,
        'graph_variant': 'original', 'data_manifest_sha256': DATA_SHA,
        'research_protocol_sha256': PLAN_SHA, 'train_rows': 2117 if arm == ARMS[0] else 7197,
        'dev_rows': 1228, 'wall_budget_seconds': 600, 'output_limit_bytes': 64*MiB,
        'qualification_claims': []}


def pinned_documents(p, deadline=math.inf):
    documents = {}
    for name, item in p['immutable_prerequisites'].items():
        path = ROOT/item['path']
        observed = {'bytes': path.stat().st_size, 'sha256': data_reader.file_sha(path, MAX_REPORT, deadline)}
        if observed != {key: item[key] for key in ('bytes', 'sha256')}:
            raise ValueError('Pinned prerequisite changed: '+name)
        # Only the data manifest is consumed as structured input; .md stays bytes.
        documents[name] = data_reader.read_json(path, expected=item['sha256']) if name == 'data_manifest' else observed
    return documents


def code_identity(manifest, deadline, *, enforce=True, p=None):
    expected = manifest['current_reader_sources']
    if not isinstance(expected, dict) or len(expected) != 95:
        raise ValueError('Exactly the admitted 95 named reader sources required')
    # The roster is historical admission, not a scan that includes this new trainer.
    named = {name: data_reader.file_sha(artifacts._safe_path(ROOT/name), MAX_REPORT, deadline)
        for name in expected}
    added = {name: data_reader.file_sha(ROOT/name, MAX_REPORT, deadline) for name in
        ('scripts/train_male_navigation_v2.py', 'tests/test_train_male_navigation_v2.py')}
    if enforce and (named != expected or added['scripts/train_male_navigation_v2.py'] != SELF_SHA):
        raise ValueError('Admitted named reader or loaded trainer source changed')
    p = protocol() if p is None else p
    lock = data_reader.file_sha(ROOT/'uv.lock', MAX_REPORT, deadline)
    if enforce and (lock != p['unchanged_code_sha256']['uv.lock'] or any(named.get(name) != value for name, value in p['unchanged_code_sha256'].items() if name.endswith('.py'))):
        raise ValueError('Unchanged helper source differs')
    return {'named_reader_sources': named, 'added_sources': added,
        'lock_sha256': lock}


def output_path(output, seed, manifest, p):
    output = artifacts._safe_path(output)
    if output.name != f'seed-{seed}' or output.exists():
        raise ValueError('Fresh fixed seed-N pair directory required; no resume')
    roots = [Path(manifest['historical_reader']['root'])]
    roots += [Path(s['path']) for s in manifest['old_sources'] + manifest['new_sources']]
    roots += [(ROOT/p['immutable_prerequisites']['data_manifest']['path']).resolve().parents[2]]
    roots += [Path(item['path']).parent for item in manifest['input_documents'].values()]
    for source in roots:
        source = artifacts._safe_path(source)
        if output.parent == source or output.parent in source.parents or source in output.parent.parents:
            raise ValueError('Managed output overlaps immutable input/producer tree')
    return output


def check_context(context, deadline, receipt=None, budget=None):
    """Fixed obtainable-after receipt; source refusal cannot erase changed hashes."""
    observed, errors = {}, []
    def obtain(name, operation):
        try: observed[name] = operation()
        except Exception as error: errors.append(name+': '+type(error).__name__+': '+str(error)[:256])
    obtain('code', lambda: code_identity(context['manifest'], deadline, enforce=False, p=context['plan']))
    observed['documents'] = {}
    for name, item in context['plan']['immutable_prerequisites'].items():
        try:
            path = ROOT/item['path']
            current = {'bytes': path.stat().st_size, 'sha256': data_reader.file_sha(path, MAX_REPORT, deadline)}
            observed['documents'][name] = current
            if current != {key: item[key] for key in ('bytes', 'sha256')}: errors.append('Changed document: '+name)
        except Exception as error: errors.append(name+': '+type(error).__name__+': '+str(error)[:256])
    obtain('protocol_sha256', lambda: data_reader.file_sha(ROOT/'docs/plans/m7-navigation-training-v2-protocol.json', MAX_REPORT, deadline))
    obtain('historical', lambda: data_reader.historical_identity(context['data_plan'], deadline, enforce=False))
    observed['prepared_outputs'] = {}
    for item in context['plan']['prepared_output_files']:
        path = artifacts._safe_path(ROOT/item['path'])
        def output_hash(path=path, item=item):
            value = {'bytes': path.stat().st_size, 'sha256': data_reader.file_sha(path, MAX_FILE, deadline)}
            if value != {key: item[key] for key in ('bytes', 'sha256')}: errors.append('Prepared output changed: '+str(path))
            return value
        obtain_key = str(path)
        try: observed['prepared_outputs'][obtain_key] = output_hash()
        except Exception as error: errors.append(obtain_key+': '+type(error).__name__+': '+str(error)[:256])
    observed['model_inputs'] = {}
    for name, pin in context['model_inputs'].items():
        try:
            actual = data_reader.file_sha(name, MAX_REPORT, deadline)
            observed['model_inputs'][name] = actual
            if actual != pin: errors.append('Graph/cell input changed: '+name)
        except Exception as error: errors.append(name+': '+type(error).__name__+': '+str(error)[:256])
    observed['sources'] = []
    _, _, _, old, _ = data_reader.helpers()
    for source in context['source_files']:
        row = {'path': source['path']}
        try: row['files'] = old.inventory(Path(source['path']), source['files'], deadline)
        except Exception as error:
            errors.append(source['path']+': '+type(error).__name__+': '+str(error)[:256])
            row['files'] = []
            for item in source['files']:
                current = {'path': item['path']}
                try:
                    path = Path(source['path'])/item['path']
                    current.update(bytes=path.stat().st_size, sha256=data_reader.file_sha(path, 160*MiB, deadline))
                except Exception as diagnostic: current['error'] = str(diagnostic)[:128]
                row['files'].append(current)
        observed['sources'].append(row)
    for name in ('code', 'historical'):
        if observed.get(name) != context[name]: errors.append(name+' differs from admitted initial identity')
    obtain('data_protocol_sha256', lambda: data_reader.file_sha(ROOT/data_reader.PROTOCOL, MAX_REPORT, deadline))
    if observed.get('protocol_sha256') != PLAN_SHA: errors.append('Prospective protocol source drift')
    if observed.get('data_protocol_sha256') != data_reader.PROTOCOL_SHA: errors.append('Data admission protocol drift')
    observed.update(status='obtained-after-training-inputs', errors=errors, qualification_claims=[])
    if receipt is not None:
        write_artifact(receipt, male_model.canonical(observed), math.inf, budget, MAX_REPORT)
    if errors: raise ValueError('; '.join(errors)[:1024])
    data_reader.check_deadline(deadline)


def prepare(args, deadline):
    fixed_training(args.training_seed, ARMS[0])
    p = protocol(); documents = pinned_documents(p, deadline); manifest = documents['data_manifest']
    if (manifest['status'] != 'prepared-navigation-advice-research-only' or
            manifest['counts'] != p['data_contract']['counts'] or manifest['labels'] !=
            {'old': 'unchanged executed targets', 'new': 'nav_advice_action'} or
            any(manifest['arms'][arm]['held_out'] for arm in ('old', 'augmented'))):
        raise ValueError('Exact admitted research arms/counts/labels required')
    output = output_path(args.output, args.training_seed, manifest, p)
    code = code_identity(manifest, deadline)
    _, _, iter_ticks, old, nav = data_reader.helpers()
    data_plan = data_reader.protocol()
    historical = data_reader.historical_identity(data_plan, deadline)
    data_root = (ROOT/p['immutable_prerequisites']['data_manifest']['path']).resolve().parent
    prepared = data_reader.read_json(data_root/'after-admission.json')
    if (prepared.get('errors') or prepared.get('reader') != manifest['current_reader_sources'] or
            prepared.get('historical') != historical or historical != manifest['historical_reader'] or
            len(prepared.get('sources', [])) != 26 or
            {s['path'] for s in prepared['sources']} != {s['path'] for s in manifest['old_sources']+manifest['new_sources']}):
        raise ValueError('Prepared source/import inventory differs')
    graph = male_model.load_graph(args.graph, args.graph_manifest)
    if graph['source_graph_sha256'] != p['training_inherited']['graph_sha256']:
        raise ValueError('Same pinned original graph required')
    model_inputs = {str(artifacts._safe_path(path)): data_reader.file_sha(path, MAX_REPORT, deadline)
        for path in (args.graph, args.graph_manifest, args.cell_source)}
    if model_inputs[str(artifacts._safe_path(args.graph_manifest))] != GRAPH_MANIFEST_SHA:
        raise ValueError('Pinned graph extraction manifest required')
    if model_inputs[str(artifacts._safe_path(args.cell_source))] != p['training_inherited']['cell_sha256']:
        raise ValueError('Pinned cell source required')
    context = {'plan': p, 'manifest': manifest, 'documents': documents, 'code': code,
        'historical': historical, 'data_plan': data_plan, 'source_files': prepared['sources'], 'model_inputs': model_inputs}
    check_context(context, deadline)  # Admission before array extraction or numerical work.
    old_manifest = data_reader.read_json(manifest['input_documents']['old_manifest']['path'],
        expected=manifest['old_manifest_sha256'])
    data = data_reader.read_old_transfer(data_root, old_manifest, historical)
    if old.validate_splits(data) != {'train': 2117, 'dev': 1228, 'held_out': 0}:
        raise ValueError('Unchanged old arm differs')
    augmented = {'train': list(data['train']), 'dev': list(data['dev']), 'held_out': []}
    collection = data_reader.admit_collection(data_reader.protocol(), data_reader.pinned_documents(data_reader.protocol(), deadline))
    collection_root = Path(manifest['input_documents']['accepted_collection']['path']).parent
    for case, source in zip(nav.CASES, manifest['new_sources'], strict=True):
        item = collection['cases'][case['id']]; run = artifacts._safe_path(item['run'])
        owner = data_reader.read_json(collection_root/case['id']/'result.json', expected=item['result_sha256'])
        count = nav.admit_record(run, owner, collection['identities_before'][str(case['learner_seed'])])
        features, targets = data_reader.advice_arrays(iter_ticks(run/'recording'), deadline)
        if (run != Path(source['path']) or run.name != source['run_id'] or source['episode'] != 0 or
                len(targets) != count or count != source['ticks'] or
                hashlib.sha256(features.tobytes()+targets.tobytes()).hexdigest() != source['feature_target_sha256']):
            raise ValueError('Complete advice source/features/targets differ')
        augmented['train'].append({'run_id': run.name, 'episode': 0, 'features': features, 'targets': targets})
    for name, arm in (('old', data), ('augmented', augmented)):
        actual = {split: [{'run_id': ep['run_id'], 'episode': ep['episode'], 'ticks': len(ep['targets']),
            'feature_target_sha256': hashlib.sha256(ep['features'].tobytes()+ep['targets'].tobytes()).hexdigest()}
            for ep in arm[split]] for split in ('train', 'dev', 'held_out')}
        if actual != manifest['arms'][name]: raise ValueError('Exact manifest arm order/bytes differ')
    if old.validate_splits(augmented, check_counts=False) != {'train': 7197, 'dev': 1228, 'held_out': 0}:
        raise ValueError('Augmented fixed counts differ')
    check_context(context, deadline)
    return output, {'old-corpus': data, 'augmented': augmented}, graph, context


def validate_fit(result, arm):
    expected = 2117 if arm == ARMS[0] else 7197 if arm == ARMS[1] else None
    history = result.get('history')
    if expected is None or not isinstance(history, list) or len(history) != 20 or any(
            type(row.get('epoch')) is not int for row in history) or [row['epoch'] for row in history] != list(range(1, 21)):
        raise ValueError('All 20 fixed epochs required')
    for row in history:
        if (type(row.get('train_ticks')) is not int or row['train_ticks'] != expected or
                type(row.get('dev', {}).get('ticks')) is not int or row['dev']['ticks'] != 1228):
            raise ValueError('Exact arm train/dev counts required')
        for value in (row.get('train_loss'), row['dev'].get('loss'), row['dev'].get('velocity_mae'), row['dev'].get('wrapped_heading_mae_radians')):
            if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
                raise ValueError('Finite nonnegative fit metrics required')
    if type(result.get('selected_epoch')) is not int or result['selected_epoch'] != min(range(1, 21), key=lambda i: history[i-1]['dev']['loss']):
        raise ValueError('Earliest strict dev minimum required')


def cpu_runtime(torch):
    value = {'python': platform.python_version(), 'numpy': importlib.metadata.version('numpy'),
        'torch_distribution': importlib.metadata.version('torch'), 'torch_build': torch.__version__,
        'compute': 'CPU one-thread; CUDA hidden/uninitialized'}
    if (value != protocol()['training_inherited']['runtime'] or torch.get_num_threads() != 1 or
            torch.cuda.is_initialized() or os.environ.get('CUDA_VISIBLE_DEVICES') != ''):
        raise ValueError('Exact frozen CPU runtime and hidden/uninitialized CUDA required')
    return value


def train(args):
    started = time.monotonic(); deadline = started+600
    output, data, graph, context = prepare(args, deadline)
    budget = StorageBudget((output.parent,), StorageLimits(max_bytes=256*MiB, min_free_bytes=1024**3,
        max_runs=3, max_snapshots=1, max_exports=1))
    report = {'status': 'running', 'training_completed': False, 'training_attempted': False,
        'models': {arm: {'status': 'not_started'} for arm in ARMS}, 'files': [],
        'data_manifest_sha256': DATA_SHA, 'study_protocol_sha256': PLAN_SHA,
        'held_out_status': 'locked_unopened', 'held_out_used_for_selection': False, 'qualification_claims': []}
    pair_budget = StorageBudget((output,), StorageLimits(max_bytes=64*MiB, min_free_bytes=1024**3))
    active = None; created = False
    try:
        with budget.lock():
            budget.check(64*MiB, path=output); output.mkdir(parents=True, exist_ok=False); created = True
            def write(name, payload):
                size = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
                if size+len(payload) > 64*MiB: raise ValueError('Fixed pair payload cap exceeded')
                item = write_artifact(output/name, payload, deadline, pair_budget)
                report['files'].append(item); return item
            check_context(context, deadline, output/'before-fit.json', pair_budget)
            import torch  # Explicit training entry only, after immutable data admission.
            torch.set_num_threads(1)
            report['runtime'] = cpu_runtime(torch)
            pair_protocol = {'id': 'male-navigation-advice-paired-original-v2', 'seed': args.training_seed,
                'training': {arm: fixed_training(args.training_seed, arm) for arm in ARMS},
                'source_code': context['code'], 'model_inputs': context['model_inputs'],
                'admitted_manifest_sha256': DATA_SHA, 'study_protocol_sha256': PLAN_SHA,
                'runtime': report['runtime'], 'feature_protocol': male_model.FEATURE_PROTOCOL, 'qualification_claims': []}
            report['protocol_sha256'] = male_model.digest(pair_protocol)
            write('protocol.json', male_model.canonical(pair_protocol))
            write('original-graph.json', male_model.canonical(graph))
            for arm in ARMS:
                active = arm; report['models'][arm] = {'status': 'running'}; report['training_attempted'] = True
                model, result = fit(graph, data[arm], args.cell_source, deadline, pair_protocol['training'][arm])
                validate_fit(result, arm)
                check_context(context, deadline, output/f'after-{arm}.json', pair_budget)
                checkpoint = {'format': 'palimpsest-male-reduced-v1', 'protocol_sha256': report['protocol_sha256'],
                    'graph_sha256': male_model.digest(graph), 'ordered_ids_sha256': graph['ordered_ids_sha256'],
                    'state_dict': model.state_dict()}
                buffer = io.BytesIO(); torch.save(checkpoint, buffer)
                item = write(arm+'.pt', buffer.getvalue())
                report['models'][arm] = {'status': 'completed', **result, 'checkpoint': item,
                    'graph_file': 'original-graph.json', 'graph_variant': 'original'}
                del model, checkpoint, buffer; active = None
            report.update(status='completed-navigation-research-training', training_completed=True)
            check_context(context, deadline, output/'after-fit.json', pair_budget)
            budget.check(0, path=output)
            stage_report(output, report, deadline, pair_budget)
        def final_admission():
            if cpu_runtime(torch) != report['runtime']: raise ValueError('Runtime changed during training')
            check_context(context, deadline, output/'after-final-sync.json', pair_budget)
            budget.check(0, path=output)
        publish_report(output, deadline, final_admission)
        return report
    except BaseException as error:
        report.update(status='failed-navigation-research-training', training_completed=False,
            error={'type': type(error).__name__, 'message': str(error)[:1024]})
        if active is not None: report['models'][active].update(status='failed', error=report['error'])
        if created:
            try: write_artifact(output/'failure.json', male_model.canonical(report), math.inf, pair_budget, MAX_REPORT)
            except BaseException as diagnostic: error.add_note('Failure retention also failed: '+str(diagnostic)[:256])
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--training-seed', type=int, choices=(10, 11, 12), required=True)
    parser.add_argument('--graph', type=Path, default=ROOT.parent/'r0-reproduction/data/assets/flynn/male-reduced-v1/source-graph.json')
    parser.add_argument('--graph-manifest', type=Path, default=ROOT/'data/manifests/malecns-reduced-neighborhood-v1.json')
    parser.add_argument('--cell-source', type=Path, default=ROOT/'upstream/fly-gym/models/connectome_rnn_model.py')
    parser.add_argument('--output', type=Path, required=True, help='Fresh aggregate-root/seed-N pair directory')
    train(parser.parse_args(argv))


if __name__ == '__main__': main()
