"""Named once-only recovery held-out evaluation; never capability admission."""
from dataclasses import dataclass
from pathlib import Path
import json
import hashlib

from . import artifacts, male_policy, male_recovery_research as recovery, male_research

PROTOCOL_PATH = 'docs/plans/m7-recovery-heldout-protocol.json'
PROTOCOL_SHA256 = '097321aaf71baaf27bedf6eb3225b17b6345fb667548d19cb4810d08f87bdbed'
INDEX_PATH, INDEX_SHA256 = recovery.INDEX_PATH, recovery.INDEX_SHA256
PAIR_SEEDS, CONTROLLERS, MAX_JSON = recovery.PAIR_SEEDS, recovery.CONTROLLERS, recovery.MAX_JSON
training = male_research.training
sha = male_research.sha
write_json = male_research.write_json
load_policy = recovery.load_policy


def protocol(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    return recovery.read_pin(root / PROTOCOL_PATH, PROTOCOL_SHA256, 65536)


def planned(stage):
    if stage != 'held_out':
        raise ValueError('Named recovery held-out evaluation only')
    return male_research.planned('held_out')


def _manifest(path, pin):
    root = Path(path).resolve().parents[2]
    return artifacts._safe_path(path), recovery._index(root, path, pin)


def _prerequisites(root):
    """Small byte-pinned normal-completion gate, also checked in every owner."""
    p = protocol(root)['prerequisites']
    directory = artifacts._safe_path(Path(root) / p['producer_root'])
    values = {name: recovery.read_pin(directory / p[name]['path'], p[name]['sha256'])
              for name in ('evaluation', 'development', 'terminal', 'enclosing')}
    terminal, enclosing = values['terminal'], values['enclosing']
    supervision = enclosing.get('supervision', {})
    if (terminal.get('status') != 'passed-development' or terminal.get('head') != p['source_commit'] or
            terminal.get('inventories_unchanged') is not True or terminal.get('owners_completed') != 24 or
            terminal.get('before_inventory_sha256') != p['inventory_sha256'] or
            terminal.get('after_inventory_sha256') != p['inventory_sha256'] or
            enclosing.get('status') != 'passed-development' or enclosing.get('terminal_sha256') != p['terminal']['sha256'] or
            supervision.get('status') != 'completed' or type(supervision.get('returncode')) is not int or supervision['returncode'] != 0 or
            type(supervision.get('elapsed_seconds')) not in (int, float) or not 0 <= supervision['elapsed_seconds'] <= 1850 or
            'error' in supervision or 'failure' in supervision):
        raise ValueError('Exact normal unchanged recovery development required')
    cleanup = terminal.get('cleanup', {})
    if (cleanup.get('sampler_stopped') is not True or cleanup.get('sample_errors') != [] or
            cleanup.get('forced_signals') != [] or cleanup.get('survivors') != []):
        raise ValueError('Recovery development cleanup differs')
    receipt = values['development']
    if (receipt.get('status') != 'passed-development' or receipt.get('qualification_claims') != [] or
            receipt.get('evaluation_sha256') != p['evaluation']['sha256'] or
            receipt.get('research_manifest_sha256') != INDEX_SHA256 or receipt.get('research_protocol_sha256') != recovery.PROTOCOL_SHA256):
        raise ValueError('Exact recovery functional receipt required')
    if terminal.get('evaluation_sha256') != p['evaluation']['sha256'] or terminal.get('development_sha256') != p['development']['sha256']:
        raise ValueError('Recovery enclosing report binding differs')
    return directory, values


def resolve(root, assets, manifest_path, manifest_sha256, seed, controller, expected_identity=None):
    _prerequisites(root)
    return recovery.resolve(root, assets, manifest_path, manifest_sha256, seed, controller, expected_identity)


def require_unlock(args):
    """Rehash all prior development records/corpus before any held-out source read."""
    root = args.repo.resolve()
    directory, values = _prerequisites(root)
    identities = {f'{seed}:{controller}': recovery.resolve(root, args.assets, args.research_manifest,
        args.research_manifest_sha256, seed, controller)[0] for seed in PAIR_SEEDS for controller in CONTROLLERS}
    goals = recovery.passed_development(values['evaluation'], INDEX_SHA256, identities)
    if values['development']['goals_per_original_seed'] != {str(k): v for k, v in goals.items()}:
        raise ValueError('Recovery goal receipt differs')
    male_research._check_development_records(directory / Path(protocol(root)['prerequisites']['evaluation']['path']).parent,
        values['evaluation'], lambda seed: recovery.Binding(args.research_manifest, INDEX_SHA256, seed).provenance())
    index = recovery._index(root, args.research_manifest, args.research_manifest_sha256)
    _, data, _ = recovery._gate(root, index)
    if index['data_manifest']['sha256'] != protocol(root)['prerequisites']['data_manifest_sha256']:
        raise ValueError('Exact recovery training corpus required')
    recovery.corpus_sources(data)
    return {'status': 'held_out_evaluation_unlocked', 'research_protocol_sha256': PROTOCOL_SHA256,
        'research_manifest_sha256': INDEX_SHA256, 'development_report_sha256': protocol(root)['prerequisites']['evaluation']['sha256'],
        'original_goals_by_seed': goals, 'identities': identities, 'qualification_claims': []}


def frozen_roots(root):
    index = recovery._index(root, Path(root) / INDEX_PATH, INDEX_SHA256)
    producer, data, _ = recovery._gate(root, index)
    development, _ = _prerequisites(root)
    # The historical data report and all raw source directories are explicit.
    roots = [producer, development, Path(data['baseline_collection']['path']).parent,
             Path(data['recovery_report']['path']).parent]
    return [artifacts._safe_path(path) for path in roots]


def outside_sources(path, root):
    path = artifacts._safe_path(path)
    if any(path == source or source in path.parents or path in source.parents for source in frozen_roots(root)):
        raise ValueError('Held-out output/input overlaps a frozen development or training source tree')
    return path


def heldout_paths(args, receipt):
    """Check the fixed teacher report/IDs/seeds before reading any numeric chunk."""
    if receipt.get('status') != 'held_out_evaluation_unlocked':
        raise ValueError('Held-out source gate is locked')
    report_path = outside_sources(args.collection, args.repo)
    if not male_policy._hash(getattr(args, 'collection_sha256', None)):
        raise ValueError('Explicit held-out collection report hash required before reads')
    report = recovery.read_pin(report_path, args.collection_sha256)
    if (report.get('status') != 'completed' or report.get('stage') != 'held_out' or
            report.get('research_protocol_sha256') != PROTOCOL_SHA256 or report.get('unlock') != json.loads(json.dumps(receipt)) or
            report.get('finalization_errors') != [] or report.get('supervisor_shutdown') != 'completed' or
            any(report.get(k) is not True for k in ('runtime_source_unchanged', 'protocol_unchanged', 'script_unchanged',
                'recordings_unchanged', 'within_deadline', 'research_sources_unchanged')) or 'error' in report):
        raise ValueError('Normal fixed recovery held-out teacher collection required')
    from collect_male_teachers import identity as producer_identity
    if (report.get('runtime_source') != producer_identity(args.repo) or
            report.get('research_sources') != research_sources(args.repo) or
            report.get('protocol_sha256') != PROTOCOL_SHA256 or
            report.get('script_sha256') != male_policy._sha(artifacts._read(Path(args.repo) / 'scripts/collect_male_teachers.py', MAX_JSON))):
        raise ValueError('Held-out teacher producer software differs')
    rows = report.get('runs')
    if not isinstance(rows, list) or [row.get('seed') for row in rows] != [1012, 1013, 1014, 1015]:
        raise ValueError('All four reserved teacher scenes required')
    index = recovery._index(args.repo, args.research_manifest, INDEX_SHA256)
    _, data, _ = recovery._gate(args.repo, index)
    used = {row['run_id'] for split in data['ordered_sources'].values() for row in split}
    paths, ids = [], set()
    for row in rows:
        identity = artifacts._id(row.get('run_id')).hex
        run = report_path.parent / 'runs' / identity
        if (identity in used or identity in ids or row.get('split') != 'held_out' or row.get('status') != 'completed' or
                row.get('close_status') != 'closed' or type(row.get('owner_exitcode')) is not int or row['owner_exitcode'] != 0 or
                row.get('owner_alive') is not False or type(row.get('ticks')) is not int or not 1 <= row['ticks'] <= 600 or
                artifacts._safe_path(row.get('run_path')) != artifacts._safe_path(run)):
            raise ValueError('Independent normal held-out teacher owner required')
        outside_sources(run, args.repo)
        manifest = artifacts._manifest(run)
        if (manifest.get('seed') != row['seed'] or manifest.get('controller') != 'teacher' or
                manifest.get('recorded_ticks') != row['ticks'] or manifest.get('status') != 'completed'):
            raise ValueError('Held-out authoritative teacher identity differs')
        phase, outcome = manifest.get('final_phase'), manifest.get('last_outcome')
        if phase in ('terminated', 'truncated'):
            if (not isinstance(outcome, dict) or outcome.get('reason') not in protocol(args.repo)['natural_endings'] or
                    (phase == 'truncated') != (outcome['reason'] == 'time_limit')):
                raise ValueError('Unsupported held-out teacher natural outcome')
        elif phase != 'paused' or row['ticks'] != 600 or outcome is not None:
            raise ValueError('Held-out teacher recording is incomplete')
        entries = row.get('files')
        if not isinstance(entries, list) or not entries or len(entries) > 64:
            raise ValueError('Bounded held-out teacher file ledger required')
        actual = sorted(path.relative_to(run).as_posix() for folder in ('recording', 'snapshots')
                        for path in (run / folder).rglob('*') if artifacts._safe_path(path).is_file())
        if actual != [item.get('path') for item in entries]:
            raise ValueError('Held-out teacher inventory differs from collection')
        size = 0
        for item in entries:
            relative = Path(item['path'])
            if relative.is_absolute() or '..' in relative.parts:
                raise ValueError('Relative held-out source file required')
            path = artifacts._safe_path(run / relative); size += path.stat().st_size
            if path.stat().st_size != item.get('bytes') or size > 160 * 1024**2:
                raise ValueError('Held-out teacher bytes exceed recorded allowance')
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                while block := stream.read(1024**2): digest.update(block)
            if digest.hexdigest() != item.get('sha256'):
                raise ValueError('Held-out teacher bytes differ from collection')
        ids.add(identity); paths.append(run)
    return paths


def disjoint_heldout(collection, manifest, prepared=None):
    root = manifest['_directory'].parents[1]
    _, data, _ = recovery._gate(root, manifest)
    ids = {row['run_id'] for split in data['ordered_sources'].values() for row in split}
    payloads = {row['feature_target_sha256'] for split in data['baseline_admission']['splits'].values() for row in split}
    episode_payloads = {row['feature_target_sha256'] for split in data['ordered_sources'].values() for row in split}
    if set(collection.get('splits', {})) != {'train', 'dev', 'held_out'} or collection['splits']['train'] or collection['splits']['dev']:
        raise ValueError('Held-out sources only; no train/dev input')
    rows = collection['splits']['held_out']
    if len(rows) != 4:
        raise ValueError('Exactly four held-out teacher sources required')
    for row in rows:
        if row['run_id'] in ids or row['feature_target_sha256'] in payloads:
            raise ValueError('Held-out source duplicates admitted training/dev run or payload')
    if prepared is None:
        raise ValueError('Prepared held-out episodes required for exact payload disjointness')
    if prepared.get('train') or prepared.get('dev') or len(prepared.get('held_out', [])) != 4:
        raise ValueError('Exactly four prepared held-out episodes required')
    for episode in prepared['held_out']:
        if hashlib.sha256(episode['features'].tobytes() + episode['targets'].tobytes()).hexdigest() in episode_payloads:
            raise ValueError('Held-out episode duplicates admitted training/dev feature/target payload')
    male_research.validate_collection(collection, 'held_out')


def research_sources(root):
    directory, values = _prerequisites(root)
    p = protocol(root)['prerequisites']
    source = directory / Path(p['evaluation']['path']).parent
    male_research._check_development_records(source, values['evaluation'],
        lambda seed: recovery.Binding(Path(root) / INDEX_PATH, INDEX_SHA256, seed).provenance())
    ledger = {str(source / 'runs' / row['run_id'] / item['path']): item['sha256']
              for row in values['evaluation']['runs'] for item in row['files']}
    ledger |= {str(directory / p[k]['path']): p[k]['sha256'] for k in ('evaluation', 'development', 'terminal', 'enclosing')}
    return recovery.research_sources(root) | ledger | {
        name: male_policy._sha(artifacts._read(Path(root) / name, MAX_JSON)) for name in
        (PROTOCOL_PATH, 'src/palimpsest/male_recovery_heldout.py', 'scripts/evaluate_male_recovery_heldout.py')}


@dataclass(frozen=True)
class Binding(recovery.Binding):
    def resolve(self, root, assets, controller, device, scenario, texture, expected):
        if (device, scenario, texture) != ('cpu', 'reproduction', 'checker') or expected is None:
            raise ValueError('Held-out requires pinned CPU/reproduction/checker identity')
        return resolve(root, assets, self.manifest, self.manifest_sha256, self.training_seed, controller, expected)

    def provenance(self):
        return {'research_protocol_sha256': PROTOCOL_SHA256, 'research_manifest_sha256': self.manifest_sha256,
            'training_seed': self.training_seed, 'development_report_sha256': protocol()['prerequisites']['evaluation']['sha256'],
            'scope': 'fixed recovery held-out evaluation only; no capability qualification or production promotion'}


def worker(config, commands, replies, display, disconnected, stop, progress):
    from functools import partial
    from .engine import Engine
    from .worker import run_worker
    value = config.get('_male_research')
    if (not isinstance(value, dict) or set(value) != {'manifest', 'manifest_sha256', 'training_seed'} or
            (type(config.get('seed')) is not int or config['seed'] not in range(1200, 1208)) or
            any(config.get(key) is not None for key in ('job', 'snapshot_path', 'memory_u', 'intervention'))):
        raise ValueError('Held-out permits only the eight reserved fresh scene roots')
    binding = Binding(Path(value['manifest']), value['manifest_sha256'], value['training_seed'])
    run_worker(config, commands, replies, display, disconnected, stop, progress,
        engine_factory=partial(Engine.open, research_binding=binding))
