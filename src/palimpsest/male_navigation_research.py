"""Six fixed same-graph navigation candidates; fresh research roots only.

Admission reads bounded published artifacts and historical source bytes, not the
raw training corpus. Its data claim binds the retained independent audit. Current
runtime source identity remains separate from the historical producer identity.
"""
from dataclasses import dataclass
import importlib.metadata
import math
import os
from pathlib import Path
import platform

from . import artifacts, male_model, male_policy, male_research

INDEX_PATH = 'data/manifests/male-navigation-research-development-v2.json'
INDEX_SHA256 = 'f938d9799b45b4c33d65a1d2c5363fea4e7b419ad9051722bff1a3df99ea77cf'
PROTOCOL_PATH = 'docs/plans/m7-navigation-training-v2-protocol.json'
PROTOCOL_SHA256 = '76a502de80b22d2592d8b4eb1e07f96cdaa3602fb64196eade4eb59e962a3928'
TRAINING_COMMIT = '6feade9770dc40efa567633412baec4347ee33cb'
PAIR_SEEDS = (10, 11, 12)
ARMS = ('old-corpus', 'augmented')
MAX_JSON = 4 * 1024**2
AFTER_FILES = ('before-fit.json', 'after-old-corpus.json', 'after-augmented.json',
               'after-fit.json', 'after-final-sync.json')


def _choice(training_seed, arm, controller='male-original'):
    if type(training_seed) is not int or training_seed not in PAIR_SEEDS or arm not in ARMS or controller != 'male-original':
        raise ValueError('Fixed navigation seed/arm and male-original required')


def _index(root, path, pin):
    if pin != INDEX_SHA256 or artifacts._safe_path(path) != artifacts._safe_path(Path(root)/INDEX_PATH):
        raise ValueError('Only the exact named navigation index is admitted')
    raw = artifacts._read(path, MAX_JSON)
    if male_policy._sha(raw) != INDEX_SHA256:
        raise ValueError('Navigation index bytes changed')
    index = artifacts._json(raw)
    if (index.get('id') != 'male-navigation-advice-paired-original-development-v2' or type(index.get('version')) is not int or
            index['version'] != 2 or index.get('training_source_commit') != TRAINING_COMMIT or
            index.get('held_out_status') != 'locked_unopened' or index.get('qualification_claims') != [] or
            [(m.get('training_seed'), m.get('arm')) for m in index.get('models', [])] !=
            [(seed, arm) for seed in PAIR_SEEDS for arm in ARMS] or
            [p.get('training_seed') for p in index.get('pairs', [])] != list(PAIR_SEEDS) or
            any(type(m.get('training_seed')) is not int or m.get('graph_variant') != 'original' for m in index['models'])):
        raise ValueError('All six ordered original-graph navigation candidates required')
    return index


def _read_pin(path, pin, observed, cap=MAX_JSON):
    path = artifacts._safe_path(path)
    if (not isinstance(pin, dict) or not male_policy._hash(pin.get('sha256')) or
            type(pin.get('size_bytes')) is not int or not 0 < pin['size_bytes'] <= cap):
        raise ValueError('Bounded artifact hash and byte count required')
    raw = artifacts._read(path, cap)
    if len(raw) != pin['size_bytes'] or male_policy._sha(raw) != pin['sha256']:
        raise ValueError('Frozen navigation artifact differs: '+str(path))
    observed[path] = (pin['sha256'], len(raw))
    return raw


def _document(item, observed, base=Path('.')):
    return artifacts._json(_read_pin(base/item['path'], item, observed))


def _supervision(value, limit):
    elapsed = value.get('elapsed_seconds')
    if (value.get('status') != 'completed' or type(value.get('returncode')) is not int or value['returncode'] != 0 or
            type(elapsed) not in (int, float) or not math.isfinite(elapsed) or not 0 <= elapsed <= limit or
            any(key in value for key in ('error', 'failure'))):
        raise ValueError('Normal bounded navigation training completion required')


def _cleanup(value):
    if (value.get('sampler_stopped') is not True or any(value.get(key) != [] for key in
            ('sample_errors', 'forced_signals', 'survivors', 'conflicting_owned_identities'))):
        raise ValueError('Normal navigation training cleanup required')


def _gate(root, index, observed):
    producer = artifacts._safe_path(Path(root)/index['producer_root'])
    docs = {name: _document(index[name], observed) for name in ('training_terminal', 'training_supervisor',
        'training_enclosing', 'training_end_session', 'independent_audit', 'before_inventory',
        'after_inventory', 'outer_after_inventory', 'data_manifest', 'study_protocol')}
    _read_pin(index['independent_auditor']['path'], index['independent_auditor'], observed)
    terminal, enclosing, end, audit = (docs[name] for name in
        ('training_terminal', 'training_enclosing', 'training_end_session', 'independent_audit'))
    status = 'passed-navigation-research-training'
    if (terminal.get('status') != status or terminal.get('head') != TRAINING_COMMIT or
            any(terminal.get(key) is not True for key in ('inventories_unchanged', 'completed_pair_content_unchanged', 'controls_unchanged')) or
            terminal.get('before_inventory_sha256') != index['before_inventory']['sha256'] or
            terminal.get('after_inventory_sha256') != index['after_inventory']['sha256'] or
            docs['before_inventory'] != docs['after_inventory'] or
            enclosing.get('status') != status or enclosing.get('terminal_sha256') != index['training_terminal']['sha256'] or
            enclosing.get('outer_after_sha256') != index['outer_after_inventory']['sha256'] or
            any(enclosing.get(key) is not True for key in ('outer_inventory_unchanged', 'controls_unchanged')) or
            end.get('status') != status or end.get('source_head') != TRAINING_COMMIT or
            type(end.get('exec_exit_code')) is not int or end['exec_exit_code'] != 0 or end.get('exec_session_fully_drained') is not True or
            audit.get('status') != 'passed' or audit.get('source') != TRAINING_COMMIT or
            audit.get('terminal_sha256') != index['training_terminal']['sha256'] or
            audit.get('enclosing_sha256') != index['training_enclosing']['sha256'] or
            audit.get('end_session_sha256') != index['training_end_session']['sha256']):
        raise ValueError('Exact completed terminal/inventory/audit lineage required')
    for item in (terminal, enclosing, end, audit):
        if any(key in item for key in ('error', 'failure')):
            raise ValueError('Failed training receipt is not admitted')
    for value in (terminal.get('wall_seconds'), enclosing.get('wall_seconds_before_publication')):
        if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 2150:
            raise ValueError('Normal training wall bound exceeded')
    _supervision(docs['training_supervisor'], 2150)
    if enclosing.get('supervision') != docs['training_supervisor']:
        raise ValueError('Enclosing supervision receipt differs')
    _cleanup(terminal.get('cleanup', {})); _cleanup(enclosing.get('outer_cleanup', {}))
    rows = terminal.get('pairs', [])
    if ([row.get('training_seed') for row in rows] != list(PAIR_SEEDS) or
            any(type(row.get('training_seed')) is not int or row.get('status') != 'completed' for row in rows)):
        raise ValueError('All three normal training pairs required')
    for row in rows:
        _supervision(row.get('supervision', {}), 660)
    code = index['training_source_code']
    if len(code['named_reader_sources']) != 95:
        raise ValueError('Exactly 95 historical reader source pins required')
    historical = {**code['named_reader_sources'], **code['added_sources'], 'uv.lock': code['lock_sha256']}
    # No current-HEAD requirement: the producer may have a documentation-only publication commit.
    for name, pin in historical.items():
        path = producer/name
        raw = artifacts._read(path, MAX_JSON)
        _read_pin(path, {'sha256': pin, 'size_bytes': len(raw)}, observed)
    for name in ('src/palimpsest/male_model.py', 'src/palimpsest/male_policy.py'):
        raw = artifacts._read(Path(root)/name, MAX_JSON)
        _read_pin(Path(root)/name, {'sha256': historical[name], 'size_bytes': len(raw)}, observed)
    plan = docs['study_protocol']; data = docs['data_manifest']
    _read_pin(Path(root)/PROTOCOL_PATH, dict(index['study_protocol'], sha256=PROTOCOL_SHA256), observed)
    if (data.get('status') != 'prepared-navigation-advice-research-only' or
            data.get('counts') != plan['data_contract']['counts'] or
            data.get('current_reader_sources') != code['named_reader_sources'] or
            data.get('feature_protocol') != male_model.FEATURE_PROTOCOL or
            data.get('labels') != {'old': 'unchanged executed targets', 'new': 'nav_advice_action'} or
            any(data['arms'][arm]['held_out'] for arm in ('old', 'augmented'))):
        raise ValueError('Exact admitted navigation data lineage required')
    return producer, docs, rows


def _history(model, arm):
    rows = model.get('history', [])
    if (model.get('status') != 'completed' or len(rows) != 20 or
            any(type(row.get('epoch')) is not int for row in rows) or [row['epoch'] for row in rows] != list(range(1, 21))):
        raise ValueError('All 20 navigation epochs required')
    for row in rows:
        if (type(row.get('train_ticks')) is not int or row['train_ticks'] != (2117 if arm == ARMS[0] else 7197) or
                type(row.get('dev', {}).get('ticks')) is not int or row['dev']['ticks'] != 1228):
            raise ValueError('Navigation epoch counts differ')
        for val in (row.get('train_loss'), row['dev'].get('loss'), row['dev'].get('velocity_mae'), row['dev'].get('wrapped_heading_mae_radians')):
            if type(val) not in (int, float) or not math.isfinite(val) or val < 0:
                raise ValueError('Finite navigation fit metrics required')
    if type(model.get('selected_epoch')) is not int or model['selected_epoch'] != min(range(1, 21), key=lambda n: rows[n-1]['dev']['loss']):
        raise ValueError('Earliest unweighted recorded-dev minimum required')


def _admit(root, assets, index):
    """Admit every candidate before returning any; never deserialize or predict."""
    observed = {}
    producer, docs, rows = _gate(root, index, observed)
    graph_path = Path(assets)/'male-reduced-v1/source-graph.json'
    graph_manifest = Path(root)/'data/manifests/malecns-reduced-neighborhood-v1.json'
    cell_path = Path(root)/'upstream/fly-gym/models/connectome_rnn_model.py'
    for path, historical_path in ((graph_path, next(p for p in index['model_inputs'] if p.endswith('/source-graph.json'))),
            (graph_manifest, str(producer/'data/manifests/malecns-reduced-neighborhood-v1.json')),
            (cell_path, str(producer/'upstream/fly-gym/models/connectome_rnn_model.py'))):
        raw = artifacts._read(path, MAX_JSON)
        _read_pin(path, {'sha256': index['model_inputs'][historical_path], 'size_bytes': len(raw)}, observed)
    graph = male_model.load_graph(graph_path, graph_manifest)
    result = {}
    for pair, row in zip(index['pairs'], rows, strict=True):
        seed = pair['training_seed']; directory = producer/pair['directory']
        payloads = {name: _read_pin(directory/name, pin, observed, male_policy.MAX_FILE_BYTES)
                    for name, pin in row['retained_files'].items()}
        if set(payloads) != {'report.json', 'protocol.json', 'original-graph.json', 'old-corpus.pt', 'augmented.pt', *AFTER_FILES}:
            raise ValueError('Exact pair payload and input-receipt files required')
        report = _document(pair['report'], observed, producer)
        training = _document(pair['protocol'], observed, producer)
        if (report.get('status') != 'completed-navigation-research-training' or
                any(report.get(key) is not True for key in ('training_attempted', 'training_completed')) or
                report.get('held_out_status') != 'locked_unopened' or report.get('held_out_used_for_selection') is not False or
                report.get('qualification_claims') != [] or report.get('data_manifest_sha256') != index['data_manifest']['sha256'] or
                report.get('study_protocol_sha256') != PROTOCOL_SHA256 or
                report.get('protocol_sha256') != male_model.digest(training) or report.get('models') != row.get('models') or
                row.get('report.json_sha256') != pair['report']['sha256'] or row.get('retained_status') != report['status'] or
                training.get('source_code') != index['training_source_code'] or training.get('model_inputs') != index['model_inputs'] or
                training.get('runtime') != index['runtime'] or report.get('runtime') != index['runtime'] or
                training.get('feature_protocol') != male_model.FEATURE_PROTOCOL or
                training.get('admitted_manifest_sha256') != index['data_manifest']['sha256'] or
                training.get('study_protocol_sha256') != PROTOCOL_SHA256 or type(training.get('seed')) is not int or training['seed'] != seed or
                set(report['models']) != set(ARMS) or artifacts._json(payloads['original-graph.json']) != graph):
            raise ValueError('Navigation report/protocol/original graph differs')
        if report['files'] != [dict(path=name, **row['retained_files'][name]) for name in
                ('protocol.json', 'original-graph.json', 'old-corpus.pt', 'augmented.pt')]:
            raise ValueError('Exact four training payload receipts required')
        before = artifacts._json(payloads[AFTER_FILES[0]])
        if (before.get('errors') != [] or before.get('status') != 'obtained-after-training-inputs' or
                before.get('code') != index['training_source_code'] or before.get('model_inputs') != index['model_inputs'] or
                before.get('protocol_sha256') != PROTOCOL_SHA256 or
                before.get('historical') != docs['data_manifest']['historical_reader'] or
                len(before.get('sources', [])) != 26 or
                any(artifacts._json(payloads[name]) != before for name in AFTER_FILES[1:])):
            raise ValueError('Unchanged before/after training inputs required')
        for arm in ARMS:
            candidate = index['models'][PAIR_SEEDS.index(seed)*2+ARMS.index(arm)]
            model = report['models'][arm]; _history(model, arm)
            expected = {**docs['study_protocol']['training_inherited'], 'training_seed': seed, 'arm': arm,
                'graph_variant': 'original', 'data_manifest_sha256': index['data_manifest']['sha256'],
                'research_protocol_sha256': PROTOCOL_SHA256, 'train_rows': 2117 if arm == ARMS[0] else 7197,
                'dev_rows': 1228, 'wall_budget_seconds': 600, 'output_limit_bytes': 64*1024**2, 'qualification_claims': []}
            if (training['training'].get(arm) != expected or candidate['training'] != expected or
                    candidate['directory'] != pair['directory'] or any(candidate[k] != pair[k] for k in ('report', 'protocol', 'graph')) or
                    candidate['runtime'] != index['runtime'] or candidate['feature_protocol'] != male_model.FEATURE_PROTOCOL or
                    candidate['cell_sha256'] != male_model.CELL_SHA256 or model.get('graph_variant') != 'original' or
                    model.get('graph_file') != 'original-graph.json' or candidate['selected_epoch'] != model['selected_epoch'] or
                    candidate['selected_recorded_dev'] != model['history'][model['selected_epoch']-1]['dev'] or
                    model.get('checkpoint') != dict(path=arm+'.pt', **row['retained_files'][arm+'.pt']) or
                    candidate['checkpoint'] != dict(path=pair['directory']+'/'+arm+'.pt', **row['retained_files'][arm+'.pt']) or
                    any(candidate[key] != graph[key] for key in ('topology_sha256', 'ordered_ids_sha256', 'source_graph_sha256'))):
                raise ValueError('Cross-arm, checkpoint, graph or fitting identity differs')
            audited = docs['independent_audit']['models'][PAIR_SEEDS.index(seed)*2+ARMS.index(arm)]
            if (audited.get('seed') != seed or audited.get('arm') != arm or audited.get('graph_buffers_and_frozen_weights_exact') is not True or
                    audited.get('checkpoint_sha256') != candidate['checkpoint']['sha256'] or
                    audited.get('report_sha256') != candidate['report']['sha256'] or
                    audited.get('protocol_sha256') != report['protocol_sha256'] or audited.get('graph_sha256') != male_model.digest(graph) or
                    audited.get('selected_epoch') != model['selected_epoch']):
                raise ValueError('Independent six-model tensor audit differs')
            male_policy._check_archive(payloads[arm+'.pt'])
            provenance = {'profile': male_policy.PROFILE, 'variant': 'original', 'training_seed': seed, 'arm': arm,
                'training_report_sha256': pair['report']['sha256'], 'protocol_sha256': report['protocol_sha256'],
                'checkpoint_sha256': candidate['checkpoint']['sha256'], 'graph_sha256': male_model.digest(graph),
                **{key: graph[key] for key in ('topology_sha256', 'ordered_ids_sha256', 'source_graph_sha256', 'graph_manifest_sha256', 'type_missing_ids')},
                'cell_source_sha256': male_model.CELL_SHA256, 'feature_protocol': male_model.FEATURE_PROTOCOL,
                'feature_protocol_sha256': male_model.digest(male_model.FEATURE_PROTOCOL),
                'data_manifest_sha256': index['data_manifest']['sha256'], 'training_source_code': index['training_source_code'],
                'training_runtime': index['runtime'], 'qualification_claims': [], 'biological_sensor_mapping': False,
                'evaluation_limit': 'fixed same-graph navigation research candidate; no task or production qualification'}
            result[seed, arm] = graph, payloads[arm+'.pt'], provenance
    for path, (pin, size) in observed.items():
        _read_pin(path, {'sha256': pin, 'size_bytes': size}, {}, male_policy.MAX_FILE_BYTES)
    return result


def runtime_identity():
    return {'python': platform.python_version(), 'numpy': importlib.metadata.version('numpy'),
            'torch_distribution': importlib.metadata.version('torch')}


def reader_sources(root):
    return male_research.research_sources(root) | {name: male_policy._sha(artifacts._read(Path(root)/name, MAX_JSON))
        for name in (INDEX_PATH, PROTOCOL_PATH, 'src/palimpsest/male_navigation_research.py')}


def resolve(root, assets, manifest_path, manifest_sha256, training_seed, arm, controller, expected_identity=None):
    _choice(training_seed, arm, controller)
    index = _index(root, manifest_path, manifest_sha256)
    if runtime_identity() != {key: index['runtime'][key] for key in ('python', 'numpy', 'torch_distribution')}:
        raise ValueError('Pinned navigation CPU runtime differs')
    _, _, provenance = _admit(root, assets, index)[training_seed, arm]
    identity = male_policy.validate_identity({'controller': controller, 'variant': 'original', 'profile': male_policy.PROFILE,
        'model_manifest_sha256': manifest_sha256, **{key: provenance[key] for key in male_policy.IDENTITY_HASHES if key != 'model_manifest_sha256'}}, controller)
    if expected_identity is not None and male_policy.validate_identity(expected_identity, controller) != identity:
        raise ValueError('Expected navigation candidate differs')
    return identity, {'repo_root': Path(root), 'asset_root': Path(assets), 'manifest_path': Path(manifest_path),
        'manifest_sha256': manifest_sha256, 'training_seed': training_seed, 'arm': arm, 'expected_identity': identity}


def load_policy(*, repo_root, asset_root, manifest_path, manifest_sha256, training_seed, arm, expected_identity, seed=0):
    if type(seed) is not int or not 0 <= seed < 2**31 or os.environ.get('CUDA_VISIBLE_DEVICES') != '':
        raise ValueError('Bounded scene seed and hidden CUDA required')
    _choice(training_seed, arm)
    index = _index(repo_root, manifest_path, manifest_sha256)
    if runtime_identity() != {key: index['runtime'][key] for key in ('python', 'numpy', 'torch_distribution')}:
        raise ValueError('Pinned navigation CPU runtime differs')
    graph, payload, provenance = _admit(repo_root, asset_root, index)[training_seed, arm]
    identity = male_policy.validate_identity({'controller': 'male-original', 'variant': 'original', 'profile': male_policy.PROFILE,
        'model_manifest_sha256': manifest_sha256, **{key: provenance[key] for key in male_policy.IDENTITY_HASHES if key != 'model_manifest_sha256'}}, 'male-original')
    if male_policy.validate_identity(expected_identity, 'male-original') != identity:
        raise ValueError('Expected navigation candidate differs')
    import torch  # Only explicit policy construction, after all six artifact admissions.
    if torch.__version__ != index['runtime']['torch_build'] or torch.cuda.is_initialized():
        raise ValueError('Pinned navigation Torch build/uninitialized CUDA required')
    policy = male_policy._load_checked_policy(graph, payload, provenance,
        Path(repo_root)/'upstream/fly-gym/models/connectome_rnn_model.py', device='cpu', seed=seed)
    policy.provenance['navigation_reader_sources'] = reader_sources(Path(repo_root))
    return policy


@dataclass(frozen=True)
class Binding:
    manifest: Path
    manifest_sha256: str
    training_seed: int
    arm: str

    def resolve(self, root, assets, controller, device, scenario, texture, expected):
        if (device, scenario, texture) != ('cpu', 'reproduction', 'checker') or expected is None:
            raise ValueError('Navigation requires pinned CPU/reproduction/checker identity')
        return resolve(root, assets, self.manifest, self.manifest_sha256, self.training_seed, self.arm, controller, expected)

    def load_policy(self, arguments, seed):
        return load_policy(**arguments, seed=seed)

    def provenance(self):
        _choice(self.training_seed, self.arm)
        return {'research_protocol_sha256': PROTOCOL_SHA256, 'research_manifest_sha256': self.manifest_sha256,
            'training_seed': self.training_seed, 'arm': self.arm,
            'scope': 'same-original-graph navigation research development; fresh roots only; held-out locked'}
