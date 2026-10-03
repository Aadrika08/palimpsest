"""Fixed M7 v2 research protocol and identities; never a production asset registry."""
import hashlib
import json
from pathlib import Path

from . import artifacts

PROTOCOL_PATH = 'docs/plans/m7-training-v2-protocol.json'
PROTOCOL_SHA256 = '8f360289ce286f56e31051c7bcfc6932a8f413dce662b83ddb9817b3e509d69b'
PAIR_SEEDS = (10, 11, 12)
CONTROLLERS = ('male-original', 'male-control')
MAX_JSON = 4 * 1024**2


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def protocol(root=None):
    root = Path(root) if root else Path(__file__).resolve().parents[2]
    payload = artifacts._read(root / PROTOCOL_PATH, 65536)
    if sha(payload) != PROTOCOL_SHA256:
        raise ValueError('frozen v2 research protocol changed')
    return artifacts._json(payload)


def training(seed):
    if type(seed) is not int or seed not in PAIR_SEEDS:
        raise ValueError('v2 requires paired seed 10, 11 or 12')
    p = protocol()
    return {**p, 'training_seed': seed, 'rewiring_seed': seed,
            'research_protocol_sha256': PROTOCOL_SHA256,
            'scene_seeds': {key: value for key, value in p['teacher_scene_seeds'].items() if key != 'held_out'},
            'wall_budget_seconds': p['training_limits']['pair_seconds'],
            'output_limit_bytes': p['training_limits']['pair_output_bytes']}


def validate_training(value):
    if not isinstance(value, dict) or value != training(value.get('training_seed')):
        raise ValueError('training differs from a frozen v2 paired protocol')
    return value['training_seed']


def validate_collection(collection, stage):
    p = protocol()
    allowed = {'development': ('train', 'dev'), 'held_out': ('held_out',)}
    if stage not in allowed or not isinstance(collection, dict) or set(collection.get('splits', {})) != {'train', 'dev', 'held_out'}:
        raise ValueError('explicit v2 collection stage required')
    for split, sources in collection['splits'].items():
        expected = p['teacher_scene_seeds'][split] if split in allowed[stage] else []
        seeds = []
        for source in sources:
            scenario = source.get('scenario')
            if (scenario.get('id') if isinstance(scenario, dict) else scenario) != 'reproduction' or source.get('texture') != 'checker':
                raise ValueError('v2 teacher profile differs')
            episodes = source.get('episodes')
            if not isinstance(episodes, list) or len(episodes) != 1 or episodes[0].get('episode') != 0:
                raise ValueError('v2 requires one episode zero')
            episode = episodes[0]
            ticks = episode.get('ticks')
            if type(ticks) is not int or not (32 if split == 'train' else 1) <= ticks <= 600:
                raise ValueError('v2 source has insufficient data or excessive ticks')
            if ticks < 600 and (source.get('final_phase') not in ('terminated', 'truncated') or
                    not isinstance(source.get('last_outcome'), dict) or
                    source['last_outcome'].get('reason') not in p['natural_endings']):
                raise ValueError('v2 short source lacks natural terminal outcome')
            seeds.append(episode.get('seed'))
        if seeds != expected:
            raise ValueError('v2 split seeds differ or held-out was opened early: ' + split)


def write_json(path, value, budget=None):
    path = artifacts._safe_path(path)
    payload = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(payload) > MAX_JSON:
        raise ValueError('research JSON exceeds 4 MiB')
    if budget:
        budget.check(len(payload), path=path)
    with path.open('xb') as stream:
        stream.write(payload)
    return path


def planned(stage):
    p = protocol()
    if stage not in ('dev', 'held_out'):
        raise ValueError('unknown closed-loop research stage')
    return [{'training_seed': pair, 'seed': scene, 'controller': controller, 'status': 'not_started'}
            for pair in PAIR_SEEDS for scene in p['closed_loop_scene_seeds'][stage] for controller in CONTROLLERS]


def _manifest(path, expected_sha256):
    from .male_policy import _hash
    path = artifacts._safe_path(path)
    payload = artifacts._read(path, MAX_JSON)
    if not _hash(expected_sha256) or sha(payload) != expected_sha256:
        raise ValueError('explicit research manifest hash differs')
    value = artifacts._json(payload)
    if (not isinstance(value, dict) or set(value) != {'version', 'research_protocol_sha256', 'pairs', 'qualification_claims'} or
            type(value['version']) is not int or value['version'] != 2 or
            value['research_protocol_sha256'] != PROTOCOL_SHA256 or value['qualification_claims'] != [] or
            not isinstance(value['pairs'], list) or len(value['pairs']) != 3):
        raise ValueError('invalid v2 research manifest')
    for seed, item in zip(PAIR_SEEDS, value['pairs']):
        if (not isinstance(item, dict) or set(item) != {'training_seed', 'directory', 'report_sha256'} or
                type(item['training_seed']) is not int or item['training_seed'] != seed or
                item['directory'] != f'seed-{seed}' or not _hash(item['report_sha256'])):
            raise ValueError('research pair must use fixed seed directory and report pin')
    return path, value


def resolve(root, assets, manifest_path, manifest_sha256, seed, controller, expected_identity=None):
    """Pure bounded validation; all production model pins stay unchanged."""
    from .male_policy import CONTROLLERS as variants, PROFILE, IDENTITY_HASHES, _bundle, validate_identity
    from .male_model import CELL_SHA256
    if seed not in PAIR_SEEDS or type(seed) is not int or controller not in CONTROLLERS:
        raise ValueError('unsupported research pair/controller')
    root, assets = artifacts._safe_path(root), artifacts._safe_path(assets)
    protocol(root)
    path, value = _manifest(manifest_path, manifest_sha256)
    matched_collections(path, value)
    pair = next(item for item in value['pairs'] if item['training_seed'] == seed)
    args = {'directory': path.parent / pair['directory'], 'variant': variants[controller],
            'expected_report_sha256': pair['report_sha256'],
            'graph_path': assets / 'male-reduced-v1/source-graph.json',
            'graph_manifest': root / 'data/manifests/malecns-reduced-neighborhood-v1.json',
            'cell_path': root / 'upstream/fly-gym/models/connectome_rnn_model.py', 'research_seed': seed}
    if sha(artifacts._read(args['cell_path'], 1024**2)) != CELL_SHA256:
        raise ValueError('pinned cell source changed')
    _, _, provenance = _bundle(**{key: item for key, item in args.items() if key != 'cell_path'})
    provenance['model_manifest_sha256'] = manifest_sha256
    identity = validate_identity({'controller': controller, 'variant': variants[controller], 'profile': PROFILE,
                                  **{key: provenance[key] for key in IDENTITY_HASHES}}, controller)
    if expected_identity is not None and validate_identity(expected_identity, controller) != identity:
        raise ValueError('research policy identity changed')
    return identity, args


def matched_collections(path, value):
    signatures = []
    for item in value['pairs']:
        p = artifacts._json(artifacts._read(path.parent / item['directory'] / 'protocol.json', 8 * 1024**2))
        signatures.append((p.get('collection_sha256'), p.get('source_code_sha256')))
    if any(value != signatures[0] for value in signatures[1:]):
        raise ValueError('all paired seeds must use identical frozen sources and training code')


def publish_manifest(root, assets, output):
    """Pin all six completed checkpoints before any development rollout."""
    from .male_policy import _bundle
    path = artifacts._safe_path(output)
    p = protocol(root)
    pairs = []
    for seed in PAIR_SEEDS:
        directory = path.parent / f'seed-{seed}'
        report_hash = sha(artifacts._read(directory / 'report.json', MAX_JSON))
        for variant in p['variants']:
            _bundle(directory, variant, report_hash, Path(assets) / 'male-reduced-v1/source-graph.json',
                    Path(root) / 'data/manifests/malecns-reduced-neighborhood-v1.json', research_seed=seed)
        pairs.append({'training_seed': seed, 'directory': directory.name, 'report_sha256': report_hash})
    value = {'version': 2, 'research_protocol_sha256': PROTOCOL_SHA256, 'pairs': pairs, 'qualification_claims': []}
    matched_collections(path, value)
    write_json(path, value)
    return sha(path.read_bytes())


def passed_development(report, manifest_sha256, identities):
    """The unchanged v2 gate; recovery uses the private fixed-plan reducer."""
    return _passed_development(report, manifest_sha256, identities, PROTOCOL_SHA256, planned('dev'))


def _passed_development(report, manifest_sha256, identities, expected_protocol_sha256, plan):
    """Shared exact 24-owner/paired-start/per-original-seed acceptance math."""
    from .male_policy import validate_identity
    if (not isinstance(report, dict) or report.get('status') != 'completed' or report.get('stage') != 'dev' or
            report.get('research_protocol_sha256') != expected_protocol_sha256 or report.get('research_manifest_sha256') != manifest_sha256 or
            report.get('sources_unchanged') is not True or report.get('model_identities_unchanged') is not True or
            report.get('recording_fingerprints_unchanged') is not True or report.get('supervisor_shutdown') != 'completed' or
            report.get('finalization_errors') != [] or report.get('qualification_claims') != []):
        raise ValueError('completed unchanged development report required')
    rows = report.get('runs')
    if not isinstance(rows, list) or len(rows) != len(plan):
        raise ValueError('development requires all 24 owners')
    goals = {seed: 0 for seed in PAIR_SEEDS}
    run_ids, scene_initials = set(), {}
    matched = report.get('paired_initial_states')
    if not isinstance(matched, list) or len(matched) != 12:
        raise ValueError('development requires twelve matched initial pairs')
    for row, intended in zip(rows, plan):
        if any(row.get(key) != intended[key] for key in ('training_seed', 'seed', 'controller')):
            raise ValueError('development scene/model assignment changed')
        key = f'{row["training_seed"]}:{row["controller"]}'
        identity = validate_identity(row.get('model_identity'), row['controller'])
        if identity != identities.get(key):
            raise ValueError('development used another model identity')
        if (row.get('status') != 'completed' or row.get('close_status') != 'closed' or
                type(row.get('owner_exitcode')) is not int or row['owner_exitcode'] != 0 or row.get('owner_alive') is not False or
                type(row.get('ticks')) is not int or not 1 <= row['ticks'] <= 600 or
                row.get('outcome') not in (*protocol()['natural_endings'], 'evaluation_tick_cap') or
                row.get('goal_reached') is not (row.get('outcome') == 'goal')):
            raise ValueError('development contains a missing, failed or malformed owner')
        run_id = str(artifacts._id(row.get('run_id')))
        if run_id in run_ids:
            raise ValueError('duplicate development owner')
        run_ids.add(run_id)
        initial = row.get('initial_fingerprint')
        keys = {'world', 'integration', 'environment', 'environment_identity', 'inputs', 'features', 'environment_rng'}
        from .male_policy import _hash
        if not isinstance(initial, dict) or set(initial) != keys or not all(_hash(value) for value in initial.values()):
            raise ValueError('development initial fingerprint incomplete')
        if row['seed'] in scene_initials and initial != scene_initials[row['seed']]:
            raise ValueError('development initial worlds/inputs differ across models')
        scene_initials[row['seed']] = initial
        if row['controller'] == 'male-original':
            goals[row['training_seed']] += int(row['goal_reached'])
    for index, pair in enumerate(matched):
        original, control = rows[2 * index:2 * index + 2]
        expected = {'training_seed': original['training_seed'], 'seed': original['seed'],
                    'original_run_id': original['run_id'], 'control_run_id': control['run_id'],
                    'status': 'exact_match', 'fingerprint': original['initial_fingerprint']}
        if pair != expected:
            raise ValueError('development paired initial receipt differs')
    if any(count < 2 for count in goals.values()):
        raise ValueError('development threshold failed; held-out stages remain locked')
    return goals


def unlock(root, assets, manifest_path, manifest_sha256, development_path, development_sha256):
    """Revalidate a pinned successful dev report and every declared record hash."""
    from .male_policy import _hash
    data = artifacts._read(development_path, MAX_JSON)
    if not _hash(development_sha256) or sha(data) != development_sha256:
        raise ValueError('explicit development report hash differs')
    report = artifacts._json(data)
    identities = {f'{seed}:{controller}': resolve(root, assets, manifest_path, manifest_sha256, seed, controller)[0]
                  for seed in PAIR_SEEDS for controller in CONTROLLERS}
    goals = passed_development(report, manifest_sha256, identities)
    directory = artifacts._safe_path(development_path).parent
    for row in report['runs']:
        run = directory / 'runs' / artifacts._id(row['run_id']).hex
        manifest = artifacts._manifest(run)
        outcome = manifest.get('last_outcome')
        reason = outcome.get('reason') if isinstance(outcome, dict) else 'evaluation_tick_cap'
        if (manifest.get('status') != 'completed' or manifest.get('policy_identity') != row['model_identity'] or
                manifest.get('seed') != row['seed'] or manifest.get('recorded_ticks') != row['ticks'] or
                manifest.get('final_phase') != row['final_phase'] or outcome != row['last_outcome'] or reason != row['outcome'] or
                manifest.get('research') != Binding(Path(manifest_path), manifest_sha256, row['training_seed']).provenance()):
            raise ValueError('development authoritative run differs')
        files = row.get('files')
        if not isinstance(files, list) or not files or len(files) > 64:
            raise ValueError('development source inventory differs')
        actual = sorted(path.relative_to(run).as_posix() for folder in ('recording', 'snapshots')
                        for path in (run / folder).rglob('*') if path.is_file())
        if actual != [entry.get('path') for entry in files] or sum(entry.get('size_bytes', 0) for entry in files) > 160 * 1024**2:
            raise ValueError('development source inventory or byte count differs')
        for entry in files:
            relative = entry.get('path')
            if not isinstance(relative, str) or Path(relative).is_absolute() or '..' in Path(relative).parts:
                raise ValueError('invalid development artifact path')
            payload = artifacts._read(run / relative, 160 * 1024**2)
            if len(payload) != entry.get('size_bytes') or sha(payload) != entry.get('sha256'):
                raise ValueError('development artifact changed')
    return {'research_protocol_sha256': PROTOCOL_SHA256, 'research_manifest_sha256': manifest_sha256,
            'development_report_sha256': development_sha256, 'original_goals_by_seed': goals,
            'identities': identities, 'status': 'held_out_unlocked'}


from dataclasses import dataclass


@dataclass(frozen=True)
class Binding:
    """Trusted Python-only capability, not a REST/UI configuration option."""
    manifest: Path
    manifest_sha256: str
    training_seed: int

    def resolve(self, root, assets, controller, device, scenario, texture, expected):
        if (device, scenario, texture) != ('cpu', 'reproduction', 'checker') or expected is None:
            raise ValueError('research requires pinned identity and CPU/reproduction/checker')
        return resolve(root, assets, self.manifest, self.manifest_sha256, self.training_seed, controller, expected)

    def load_policy(self, arguments, seed):
        from .male_policy import load_policy
        return load_policy(**arguments, seed=seed)

    def provenance(self):
        return {'research_protocol_sha256': PROTOCOL_SHA256,
                'research_manifest_sha256': self.manifest_sha256, 'training_seed': self.training_seed,
                'scope': 'research candidate; no production admission or topology/generalization qualification'}


def worker(config, commands, replies, display, disconnected, stop, progress):
    """Existing owner lifecycle with an explicitly reviewed research-only factory."""
    from functools import partial
    from .engine import Engine
    from .worker import run_worker
    value = config.get('_male_research')
    if (not isinstance(value, dict) or set(value) != {'manifest', 'manifest_sha256', 'training_seed'} or
            any(config.get(key) is not None for key in ('job', 'snapshot_path', 'memory_u', 'intervention'))):
        raise ValueError('research wrapper permits only fresh pinned root runs')
    binding = Binding(Path(value['manifest']), value['manifest_sha256'], value['training_seed'])
    run_worker(config, commands, replies, display, disconnected, stop, progress,
               engine_factory=partial(Engine.open, research_binding=binding))


def require_unlock(args):
    if not all(getattr(args, key, None) for key in ('research_manifest', 'research_manifest_sha256', 'development_report', 'development_sha256')):
        raise ValueError('held-out remains locked without explicit manifest and successful dev report pins')
    return unlock(args.repo, args.assets, args.research_manifest, args.research_manifest_sha256,
                  args.development_report, args.development_sha256)


def add_arguments(parser, *, stages):
    parser.add_argument('--research-stage', choices=stages)
    parser.add_argument('--research-manifest', type=Path)
    parser.add_argument('--research-manifest-sha256')
    parser.add_argument('--development-report', type=Path)
    parser.add_argument('--development-sha256')


def research_sources(root):
    """Every v2 protocol/runner/helper byte needed for a stage, bounded individually."""
    paths = [PROTOCOL_PATH, 'scripts/train_male_reduced.py', 'scripts/collect_male_teachers.py',
             'scripts/evaluate_male_closed_loop.py', 'scripts/male_research.py']
    paths += [path.relative_to(root).as_posix() for path in sorted((root / 'src/palimpsest').glob('*.py'))]
    return {name: sha(artifacts._read(root / name, MAX_JSON)) for name in paths}
