"""M7 navigation v4 S2/S3 evaluator: fresh development 3160-3163; held-out locked; plan-only by default.

Development (S2) runs the fixed 24 owners in scene 3160..3163, training seed 10/11/12,
old-corpus-then-augmented order. Every owner is a fresh, teacher-free episode of one
terminal S1 checkpoint. Admission per scene requires all six owners to share the exact
scientific initial (fingerprint and geometry), every scene to be disjoint from every
prior/S0 scene and from the other development scenes (geometry, initial input and
complete payload), and native goal scoring (``last_outcome.reason == 'goal'`` at a natural
boundary within 600 ticks). The gate is per augmented seed, >= 3/4; the old arm is
reported, never gated. A wall-clock kill or timeout is an operational failure: it stops
the stage, later owners stay ``not_started``, and nothing is scored as a non-goal.

Held-out (S3, scenes 3170..3177, 48 owners, >= 6/8 per augmented seed) is reachable only
through ``admit_held_out``: a published development pass, a separate S3 owner GO naming
that report, and a lane charge through S2 within the Amendment 1 ceiling. There is no
held-out constant to import and no CLI path around that admission.

The native owner (Amendment 2) is a port of the v2 owner worker: NavigationBindingV4, a fresh
spawned one-thread CPU process per owner, 180 s each, no teacher, no retry or replacement, the
first failure stops the stage. It is reachable only through the GO route inside a research stage;
the S2 GO must name both the base protocol sha and the amendment-2 file sha.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from palimpsest import artifacts, male_model
import run_research_stage as stage_runner
import train_male_navigation_v4 as trainer

ROOT = trainer.ROOT
PROTOCOL_SHA256 = trainer.PROTOCOL_SHA256
V3_PROTOCOL_SHA256 = trainer.V3_PROTOCOL_SHA256
LANE = 'navigation'
SEEDS, ARMS = trainer.SEEDS, trainer.ARMS
DEVELOPMENT_SCENES = (3160, 3161, 3162, 3163)
DEVELOPMENT_GOALS = 3
HELD_OUT_GOALS = 6
MAX_TICKS = 600
NATURAL = ('goal', 'collision', 'stalled', 'time_limit')
# Amendment 1 lane budget: S3 admitted only if measured charge through S2 <= 5643.168 CPU-s.
HELD_OUT_CHARGE_CEILING = 5643.168
PRIOR_CHARGE = 1.832
REPORT_ID = 'male-navigation-v4-evaluation-report-v1'
MAX_JSON = 4 * 1024**2


class Refusal(ValueError):
    """An admission refusal before any scene generation or owner."""


class OperationalFailure(RuntimeError):
    """Wall-clock kill/timeout or infrastructure fault; never a scientific non-goal."""


def _cases(prefix, scenes):
    return tuple({'id': f'{prefix}-{scene}-seed-{seed}-{arm}', 'scene_seed': scene,
                  'training_seed': seed, 'arm': arm}
                 for scene in scenes for seed in SEEDS for arm in ARMS)


CASES = _cases('dev', DEVELOPMENT_SCENES)


def _ranges(values):
    used = set()
    for text in values:
        bounds = text.split()[0].split('-')
        low, high = int(bounds[0]), int(bounds[-1])
        used.update(range(low, high + 1))
    return used


def check_protocol(study):
    """Frozen scene IDs, thresholds and ID disjointness from the protocol record."""
    fresh = study['fresh_evaluation']
    development, held_out = fresh['development'], fresh['held_out']
    used = _ranges(study['scene_id_disjointness']['candidate_screen']['used_ranges_on_record'])
    held = tuple(held_out['scene_ids'])
    if (tuple(development['scene_ids']) != DEVELOPMENT_SCENES or held != tuple(range(3170, 3178)) or
            development['owners'] != 24 or held_out['owners'] != 48 or
            held_out['threshold_change'] is not False or held_out['state'] != 'reserved, locked, unopened' or
            '>= 3 of 4' not in development['gate'] or '>= 6 of 8' not in held_out['gate']):
        raise Refusal('Frozen v4 scene IDs, owner counts or thresholds differ')
    if used & set(DEVELOPMENT_SCENES) or used & set(held) or set(DEVELOPMENT_SCENES) & set(held):
        raise Refusal('Fresh scene IDs collide with an ID on record')
    return used


def check_case(case, cases):
    if (not isinstance(case, dict) or set(case) != {'id', 'scene_seed', 'training_seed', 'arm'} or
            type(case['scene_seed']) is not int or type(case['training_seed']) is not int or
            case not in cases):
        raise Refusal('Exact fresh scene/seed/arm case required')


# --------------------------------------------------------------------------- scoring

def native_goal(result):
    """Native outcome at a natural boundary; True only for reason 'goal' within 600 ticks."""
    state, count = result.get('final_state'), result.get('ticks')
    if not isinstance(state, dict) or type(count) is not int or not 1 <= count <= MAX_TICKS:
        raise ValueError('Invalid native tick count or final state')
    reason = (state.get('last_outcome') or {}).get('reason')
    valid = (state.get('phase') == 'terminated' and reason in ('goal', 'collision', 'stalled') or
             state.get('phase') == 'truncated' and reason == 'time_limit' and count == MAX_TICKS)
    if (not valid or state.get('total_tick') != count or state.get('episode') != 0 or
            result.get('executed_ticks') != count):
        raise ValueError('Invalid natural/cap outcome; no arbitrary censoring')
    return reason == 'goal'


def scientific_initials(rows, cases):
    """All six owners of a scene share the exact scientific initial and geometry."""
    scenes = {}
    for case in cases:
        row = rows[case['id']]
        key = (row['initial_fingerprint'], row['geometry'])
        scenes.setdefault(case['scene_seed'], []).append(key)
    for scene, keys in scenes.items():
        if len(keys) != len(SEEDS) * len(ARMS):
            raise ValueError(f'Scene {scene} lacks all six owners')
        if any(key != keys[0] for key in keys[1:]):
            raise ValueError(f'Scene {scene} owners differ in scientific initial')
    return {str(scene): {'initial_fingerprint': keys[0][0], 'geometry': keys[0][1]}
            for scene, keys in scenes.items()}


def disjointness(rows, cases, prior):
    """No geometry, initial input or payload repeats prior/S0 scenes or another fresh scene."""
    prior_geometry = {(key, row['geometry'][key]) for row in prior['sources'] for key in ('layout', 'full_scene')}
    prior_inputs = {json.dumps(row['initial_fingerprint']['inputs'], sort_keys=True)
                    for row in prior['sources'] if 'initial_fingerprint' in row}
    prior_payloads = {row['raw_payload_sha256'] for row in prior['sources']}
    seen = {}
    for case in cases:
        row = rows[case['id']]
        inputs = json.dumps(row['initial_fingerprint']['inputs'], sort_keys=True)
        if any((key, row['geometry'][key]) in prior_geometry for key in ('layout', 'full_scene')):
            raise ValueError('Fresh geometry repeats a prior or S0 scene')
        if inputs in prior_inputs:
            raise ValueError('Fresh initial input repeats a prior or S0 scene')
        if row['raw_payload_sha256'] in prior_payloads:
            raise ValueError('Fresh complete payload repeats a prior or S0 scene')
        for scene, other in seen.items():
            if scene == case['scene_seed']:
                continue
            if (any(row['geometry'][key] == other['geometry'][key] for key in ('layout', 'full_scene')) or
                    inputs == other['inputs'] or row['raw_payload_sha256'] in other['payloads']):
                raise ValueError('Distinct fresh scenes repeat geometry, initial input or payload')
        entry = seen.setdefault(case['scene_seed'], {'geometry': row['geometry'], 'inputs': inputs,
                                                     'payloads': set()})
        entry['payloads'].add(row['raw_payload_sha256'])
    return True


def _admit_row(row, case):
    if (row.get('status') != 'completed-recording' or row.get('case') != case or
            not isinstance(row.get('initial_fingerprint'), dict) or
            'inputs' not in row['initial_fingerprint'] or not isinstance(row.get('geometry'), dict) or
            set(row['geometry']) != {'layout', 'full_scene'} or not trainer._hex64(row.get('raw_payload_sha256')) or
            row.get('teacher_queries') != 0):
        raise ValueError('Owner result is not a complete teacher-free admitted recording')
    return native_goal(row)


def reduce(rows, cases, prior, threshold, per_seed):
    """Per-seed goal counts; only augmented seeds gate; any non-normal owner is not admitted."""
    if list(rows) != [case['id'] for case in cases]:
        raise ValueError('Exact fixed case order differs')
    counts = {f'{seed}:{arm}': 0 for seed in SEEDS for arm in ARMS}
    complete = all(rows[case['id']].get('status') == 'completed-recording' for case in cases)
    result = {'owners': len(cases), 'scenes_per_seed': per_seed, 'goals_by_seed_arm': counts,
              'gated_arm': 'augmented', 'old_arm': 'reported-not-gated',
              'threshold_per_augmented_seed': threshold, 'qualification_claims': []}
    if not complete:
        return {**result, 'status': 'not-admitted-operational-failure', 'all_owners_normal': False}
    goals = {case['id']: _admit_row(rows[case['id']], case) for case in cases}
    initials = scientific_initials(rows, cases)
    disjointness(rows, cases, prior)
    for case in cases:
        counts[f"{case['training_seed']}:{case['arm']}"] += int(goals[case['id']])
    passed = all(counts[f'{seed}:augmented'] >= threshold for seed in SEEDS)
    return {**result, 'status': 'passed-gate' if passed else 'failed-gate', 'all_owners_normal': True,
            'matched_scene_initials': initials,
            'paired_scene_differences': {
                f"{case['scene_seed']}:{case['training_seed']}":
                    int(goals[case['id'].replace('old-corpus', 'augmented')]) - int(goals[case['id']])
                for case in cases if case['arm'] == 'old-corpus'}}


def reduce_development(rows, prior):
    value = reduce(rows, CASES, prior, DEVELOPMENT_GOALS, len(DEVELOPMENT_SCENES))
    value['held_out_status'] = ('eligible-pending-separate-owner-go' if value['status'] == 'passed-gate'
                                else 'locked-permanently')
    return value


# --------------------------------------------------------------------------- execution

def run_cases(cases, owner, rows):
    """Exact order; the first operational failure stops and leaves later owners not_started."""
    for case in cases:
        row = rows[case['id']]
        row['status'] = 'running'
        try:
            result = owner(case)
        except BaseException as error:
            row.update(status='operational-failure',
                       error={'type': type(error).__name__, 'message': str(error)[:1024]})
            return False
        if not isinstance(result, dict) or result.get('status') != 'completed-recording':
            row.update(status='operational-failure', error={'type': 'OwnerNotNormal',
                       'message': str((result or {}).get('status'))[:256]})
            return False
        row.update(result)
    return True


def evaluate(route, cases, owner, reducer):
    rows = {case['id']: {'case': case, 'status': 'not_started'} for case in cases}
    completed = run_cases(cases, owner, rows)
    try:
        admission = reducer(rows)
    except ValueError as error:
        admission = {'status': 'not-admitted', 'error': str(error)[:1024], 'qualification_claims': []}
    if route == 'development':
        admission.setdefault('held_out_status', 'locked-permanently')
    return {'id': REPORT_ID, 'route': route, 'protocol_sha256': PROTOCOL_SHA256,
            'status': 'completed' if completed else 'operational-failure',
            'cases': rows, 'admission': admission, 'qualification_claims': []}


def publish_report(output, report):
    """Exclusive, fsynced terminal report; an existing report or failure is never replaced."""
    output = Path(output)
    if (output / 'report.json').exists():
        raise FileExistsError('Evaluation report already published; one attempt')
    return trainer.write_exclusive(output / 'report.json', male_model.canonical(report), MAX_JSON)


def development(owner, prior):
    return evaluate('development', CASES, owner, lambda rows: reduce_development(rows, prior))


# --------------------------------------------------------------------------- held-out route

def _read_json(path):
    raw = artifacts._read(path, MAX_JSON)
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class HeldOutAdmission:
    """Capability returned only by admit_held_out; consumed by one held_out call."""
    cases: tuple
    development_report_sha256: str
    held_out_go_sha256: str
    lane_charge_through_s2: float


_ADMITTED, _KEEP = set(), []


def admit_held_out(development_report, held_out_go, ledger, development_go):
    """The only route to the held-out cases: dev pass + separate S3 GO + lane ceiling."""
    report, report_sha = _read_json(development_report)
    if (report.get('id') != REPORT_ID or report.get('route') != 'development' or
            report.get('status') != 'completed' or report.get('protocol_sha256') != PROTOCOL_SHA256 or
            report.get('admission', {}).get('status') != 'passed-gate' or
            report['admission'].get('held_out_status') != 'eligible-pending-separate-owner-go'):
        raise Refusal('Held-out requires a complete published development pass')
    go, go_sha = _read_json(held_out_go)
    _, dev_go_sha = _read_json(development_go)
    if go.get('protocol_sha256') == V3_PROTOCOL_SHA256:
        raise Refusal('Held-out GO names the v3 protocol')
    if (go.get('decision') != 'GO' or go.get('lane') != LANE or go.get('stage') != 'S3' or
            go.get('protocol_sha256') != PROTOCOL_SHA256 or go.get('development_report_sha256') != report_sha or
            go_sha == dev_go_sha or not str(go.get('granted_by', '')).strip() or
            not str(go.get('granted_at', '')).strip()):
        raise Refusal('A separate explicit S3 owner GO naming the development report is required')
    charged = PRIOR_CHARGE + stage_runner.lane_totals(stage_runner.read_ledger(ledger))[LANE]
    if not charged <= HELD_OUT_CHARGE_CEILING:
        raise Refusal(f'Lane charge through S2 {charged:.3f} exceeds {HELD_OUT_CHARGE_CEILING}')
    admission = HeldOutAdmission(_cases('held-out', tuple(range(3170, 3178))), report_sha, go_sha, charged)
    _ADMITTED.add(id(admission))
    _KEEP.append(admission)
    return admission


def held_out(owner, prior, admission):
    """Evaluate the 48 held-out owners; only an admission object from admit_held_out opens it."""
    if type(admission) is not HeldOutAdmission or id(admission) not in _ADMITTED or \
            [(c['scene_seed'], c['training_seed'], c['arm']) for c in admission.cases] != \
            [(scene, seed, arm) for scene in range(3170, 3178) for seed in SEEDS for arm in ARMS]:
        raise Refusal('Held-out is reachable only through admit_held_out')
    _ADMITTED.discard(id(admission))  # One attempt per admission.
    report = evaluate('held-out', admission.cases, owner,
                      lambda rows: reduce(rows, admission.cases, prior, HELD_OUT_GOALS, 8))
    report.update(development_report_sha256=admission.development_report_sha256,
                  held_out_go_sha256=admission.held_out_go_sha256)
    return report


# --------------------------------------------------------------------------- GO and CLI

def check_go(path, stage, s1_report_sha256):
    value, sha = _read_json(path)
    if value.get('protocol_sha256') == V3_PROTOCOL_SHA256:
        raise Refusal('GO record names the v3 protocol')
    if (value.get('decision') != 'GO' or value.get('lane') != LANE or value.get('stage') != stage or
            value.get('protocol_sha256') != PROTOCOL_SHA256 or value.get('amendment_2_sha256') != AMENDMENT_SHA256 or
            value.get('s1_report_sha256') != s1_report_sha256 or not str(value.get('granted_by', '')).strip() or not str(value.get('granted_at', '')).strip()):
        raise Refusal(f'GO record does not name lane navigation, stage {stage}, the base protocol and amendment 2 shas, and the S1 report')
    return sha


def admit_candidates(s1_output):
    """Six terminal S1 checkpoints behind a durable publication receipt."""
    from palimpsest import male_navigation_research_v4 as research
    if Path(s1_output).resolve() != Path(research.S1_OUTPUT).resolve():
        raise Refusal('S1 output must be the exact tree the binding loads (research.S1_OUTPUT)')
    report = trainer.success_admitted(s1_output)
    if report is None:
        raise Refusal('Six admitted terminal S1 checkpoints are required')
    payload = artifacts._read(Path(s1_output) / 'report.json', MAX_JSON)
    sha = hashlib.sha256(payload).hexdigest()
    if sha != research.REPORT_SHA256:
        raise Refusal('S1 report sha differs from the binding constant')
    return report, sha


# --------------------------------------------------------------------------- A2 native owner (S2 development only)
# Port of scripts/evaluate_male_navigation_v2.py (worker + verify) with v4 constants: NavigationBindingV4,
# the fixed v4 scenes and case table, v4 pins. Thresholds, scene lists and case tables live above, once;
# this block only executes them. Heavy imports stay inside functions: the parent never loads Torch/MuJoCo.

AMENDMENT_PATH = 'docs/plans/m7-navigation-v4-amendment-2.json'
AMENDMENT_SHA256 = 'c4cd3a506b0b468b0d6d4d359dff7ecbd3b3bf0c25c6fe9360207282249f8d6f'
PROFILE = 'male-navigation-development-v4'
OWNER_SECONDS, STAGE_SECONDS, MiB = 180, 1800, 1024**2
PINNED_SOURCES = ('src/palimpsest/engine.py', 'src/palimpsest/male_navigation_research_v4.py', 'src/palimpsest/male_policy.py',
                  'src/palimpsest/male_model.py', 'scripts/evaluate_male_navigation_v4.py', 'scripts/train_male_navigation_v4.py',
                  trainer.PROTOCOL_PATH, AMENDMENT_PATH)


def _lib():
    import collect_male_navigation as common
    import collect_male_navigation_v2 as contacts
    import evaluate_male_navigation_v2 as v2
    return common, contacts, v2


def check_amendment(root):
    """The amendment-2 file sha is checked by every S2 file; it is never trusted from arguments."""
    sha = hashlib.sha256(artifacts._read(Path(root) / AMENDMENT_PATH, MAX_JSON)).hexdigest()
    if sha != AMENDMENT_SHA256:
        raise Refusal('Amendment 2 file differs from the approved sha256')
    return sha


def source_pins(root):
    common, contacts, _ = _lib()
    root = Path(root)
    plan = contacts.plan(root)
    for name, pin in plan['generator']['source_sha256'].items():
        if common.digest(root / 'upstream/fly-gym' / name) != pin:
            raise ValueError('Frozen navigation generator changed')
    scripts = sorted((root / 'scripts').glob('*.py'))
    if len(scripts) > 256:
        raise ValueError('Current script inventory exceeds bound')
    return {'protocol_sha256': PROTOCOL_SHA256, 'amendment_2_sha256': check_amendment(root),
            'study_sha256': contacts.PLAN_SHA, 'contact_profile_sha256': contacts.PROFILE_SHA,
            'runtime_source': common.source_identity(root),
            'sources': {name: common.digest(root / name) for name in PINNED_SOURCES},
            'scripts': {p.name: common.digest(p) for p in scripts}, 'upstream': plan['generator']['source_sha256']}


def check_pins(root, expected):
    if source_pins(root) != expected:
        raise ValueError('Development source changed')


def prior_metadata(pin_path, pin_sha256):
    """Prior/S0 scene metadata from the S0z-pinned data manifest named by the S1 report."""
    record, actual = trainer.read_corpus_pin(pin_path)
    if actual != pin_sha256:
        raise Refusal('Corpus pin differs from the one the S1 report names')
    data = json.loads(trainer._pinned_bytes(record['data_manifest'], MAX_JSON))
    rows = data['old_sources'] + data['new_sources']
    if len(rows) != 26 or data.get('counts', {}).get('held_out_sources', 0) != 0:
        raise ValueError('Exact admitted parent source metadata required')
    return {'data_manifest_sha256': record['data_manifest']['sha256'], 'sources': [
        {key: row[key] for key in ('run_id', 'episode', 'geometry', 'raw_payload_sha256')} |
        ({'initial_fingerprint': row['initial_fingerprint']} if 'initial_fingerprint' in row else {}) for row in rows]}


def initial_admission(world, fingerprint, case, prior, earlier, expected=None):
    """Evaluator-only metadata checks; no scene mutation or teacher access."""
    from evaluate_male_closed_loop import require_matched_initial
    from prepare_male_navigation_v2 import geometry_digests
    check_case(case, CASES)
    geometry = geometry_digests(world)
    for row in prior['sources']:
        if any(geometry[key] == row['geometry'][key] for key in ('layout', 'full_scene')):
            raise ValueError('Development geometry repeats admitted parent data')
        if row.get('initial_fingerprint', {}).get('inputs') == fingerprint['inputs']:
            raise ValueError('Development initial input repeats admitted parent data')
    for scene, previous in earlier.items():
        if int(scene) != case['scene_seed'] and (any(geometry[key] == previous['geometry'][key] for key in geometry) or
                                                 fingerprint['inputs'] == previous['fingerprint']['inputs']):
            raise ValueError('Distinct development scenes repeat geometry or initial input')
    if expected is not None:
        require_matched_initial(expected, fingerprint)
    return geometry


def candidates(root, assets):
    """Six identities from the hard-coded S1 evidence; no Torch/model/native construction here."""
    from palimpsest import male_navigation_research_v4 as research
    return {f'{seed}:{arm}': research.resolve(Path(root), Path(assets), seed, arm, 'male-original')[0]
            for seed in research.PAIR_SEEDS for arm in research.ARMS}


def worker(config):
    """One fresh spawned one-thread CPU owner. The parent never repeats it."""
    common, contacts, v2 = _lib()
    started = time.monotonic(); deadline = started + OWNER_SECONDS
    root, run, stage = map(Path, (config['repo'], config['run'], config['stage']))
    budget = common.storage(config); engine = probe = None
    result = {'status': 'failed-infrastructure', 'case': config['case'], 'rows': [],
              'contact_incidence': contacts.empty_incidence(), 'executed_ticks': 0, 'published_rows': 0}
    try:
        check_case(config['case'], CASES); check_pins(root, config['source_pins'])
        if os.environ.get('CUDA_VISIBLE_DEVICES') != '':
            raise ValueError('CUDA must be explicitly hidden')
        import numpy as np
        import torch
        import mujoco
        from palimpsest import male_navigation_research_v4 as research
        from palimpsest.engine import Engine
        from palimpsest.replay import _register_initial
        from palimpsest.snapshots import _model_digest
        from palimpsest.profiles import validate_world
        torch.set_num_threads(1); torch.set_num_interop_threads(1)
        if (torch.cuda.is_initialized() or torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1 or
                mujoco.__version__ != '3.3.6' or mujoco.get_mjcb_control() is not None):
            raise ValueError('Fresh pinned one-thread CPU/native owner required')
        result['runtime'] = {**research.runtime_identity(), 'torch_build': torch.__version__, 'mujoco': mujoco.__version__,
                             'intraop_threads': torch.get_num_threads(), 'interop_threads': torch.get_num_interop_threads(),
                             'cuda_initialized': False}
        budget.check(v2.admission(contacts.plan(root))['recording_bytes'] + 16 * MiB, path=run)
        run.mkdir(exist_ok=False)
        case = config['case']; binding = research.Binding(case['training_seed'], case['arm'])
        engine = Engine.open(root, Path(config['assets']), run / 'recording', controller='male-original', device='cpu',
                             seed=case['scene_seed'], scenario='reproduction', texture='checker', run_id=run.name,
                             max_bytes=144 * MiB, storage_budget=budget, research_binding=binding,
                             expected_policy_identity=config['identity'])
        if (engine.total_tick or engine.episode or engine.phase != 'paused' or engine.teacher is not None or
                np.any(engine.env.data.qvel) or np.any(engine.env.data.ctrl) or engine.env.data.time or engine.env._t or
                engine.env._speed or engine.env._stall_steps or np.any(engine.env._last_action) or
                not np.array_equal(engine.env._prev_xy, engine.env._base_xy()) or engine.eyes != {'left': True, 'right': True} or
                engine.env.max_steps != MAX_TICKS or engine.env.n_obstacles != 20 or engine.env._action_scale != 2 or
                engine.env.end_on_collision):
            raise ValueError('Exact untouched reproduction boundary required')
        result['numeric_admission'] = common.numeric_admission([engine.observation[k] for k in ('cam_left', 'cam_right')],
                                                               engine.policy.agent.cell.Nin)
        validate_world(engine.env)
        probe = common.body.ContactProbe(mujoco, engine.env)
        ownership = contacts.compiled_ownership(mujoco, engine.env.model, _model_digest(engine.env.model))
        result['contact_ownership'] = ownership
        if (ownership['base_body_id'] != probe.ownership['base_body_id'] or
                ownership['robot_bodies'] != probe.ownership['robot_bodies'] or
                any({k: actual[k] for k in original} != original for actual, original in
                    zip(ownership['geometries'], probe.ownership['geometries'], strict=True))):
            raise ValueError('Probe and compiled contact ownership differ')
        metadata = {'study_sha256': contacts.PLAN_SHA, 's1_report_sha256': research.REPORT_SHA256,
                    'case': case, 'source_identity': config['identity'], 'contact_profile_sha256': contacts.PROFILE_SHA,
                    'contact_ownership': ownership, 'teacher_queries': 0, 'generic_replay_qualified': False,
                    'runtime': result['runtime'], 'data_manifest_sha256': config['prior']['data_manifest_sha256']}
        engine.writer.manifest.update(profile=PROFILE, navigation_development=metadata)
        _register_initial(engine, run, budget); common.initial_ready(run, 'ready')
        if (run / 'snapshots/initial.snp').stat().st_size > 16 * MiB:
            raise ValueError('Initial SNP exceeds cap')
        contacts.initial_contact_binding(run, ownership)
        result['initial_world'] = engine.world()
        fingerprint = common.initial_match(run, result['initial_world'], case, config['identity'], config.get('scene_initial'))
        result['initial_fingerprint'] = fingerprint
        result['geometry'] = initial_admission(result['initial_world'], fingerprint, case, config['prior'],
                                               config['earlier_scenes'], config.get('scene_initial'))
        metadata['initial_fingerprint'] = fingerprint; metadata['geometry'] = result['geometry']
        probe.install()  # All scientific initial/disjointness checks precede action 1.
        result['outcome'] = v2.run_episode(engine, probe, result, deadline, stage, budget)
        result['final_state'] = engine.public_state(); result['status'] = 'completed-recording'
    except BaseException as error:
        result.update(status='failed-infrastructure', error={'type': type(error).__name__, 'message': str(error)[:1024]})
    finally:
        if probe is not None:
            try:
                probe.close(); result['callback_restored'] = mujoco.get_mjcb_control() is None
            except Exception as error:
                result.update(status='failed-infrastructure', callback_error=str(error)[:512])
        if engine is not None:
            result['executed_ticks'] = engine.total_tick
            try:
                engine.close(); result['engine_closed'] = True
            except Exception as error:
                result.update(status='failed-infrastructure', cleanup_error=str(error)[:512])
    if not result.get('callback_restored') or not result.get('engine_closed') or result['executed_ticks'] != len(result['rows']):
        result['status'] = 'failed-infrastructure'
    result['wall_seconds'] = time.monotonic() - started
    try:
        v2.owner_payload(result)
        common.publish(stage / 'result.json', result, budget, deadline, lambda: check_pins(root, config['source_pins']))
    except Exception as error:
        common.write_json(stage / 'failure.json', {'status': 'failed-infrastructure', 'error': str(error)[:1024], 'result': result},
                          max_bytes=4 * MiB, storage_budget=budget)
        return False
    return result['status'] == 'completed-recording' and time.monotonic() <= deadline


def admit_record(run, result, config):
    """Parent-side re-admission of one owner's retained recording; port of v2 admit_record."""
    import numpy as np
    from evaluate_male_closed_loop import validate_recording, inventory
    from palimpsest import male_navigation_research_v4 as research
    from palimpsest.records import iter_ticks
    from prepare_male_navigation_v2 import raw_payload_update
    common, contacts, v2 = _lib()
    case = config['case']; check_case(case, CASES)
    manifest = common.read_json(run / 'recording/manifest.json', maximum=4 * MiB)
    meta = manifest.get('navigation_development', {})
    binding = research.Binding(case['training_seed'], case['arm'])
    if (result.get('status') != 'completed-recording' or result.get('case') != case or
            any(result.get(k) is not True for k in ('callback_restored', 'engine_closed', 'telemetry_wrappers_restored')) or
            manifest.get('profile') != PROFILE or manifest.get('teacher_privileged') is not False or
            meta.get('case') != case or meta.get('source_identity') != config['identity'] or
            meta.get('study_sha256') != contacts.PLAN_SHA or meta.get('s1_report_sha256') != research.REPORT_SHA256 or
            meta.get('contact_profile_sha256') != contacts.PROFILE_SHA or
            meta.get('contact_ownership') != result.get('contact_ownership') or
            meta.get('teacher_queries') != 0 or type(meta.get('teacher_queries')) is not int or
            meta.get('generic_replay_qualified') is not False or meta.get('runtime') != result.get('runtime') or
            meta.get('data_manifest_sha256') != config['prior']['data_manifest_sha256']):
        raise ValueError('Development model/contact/profile/cleanup lineage differs')
    common.initial_ready(run, 'ready'); contacts.initial_contact_binding(run, result['contact_ownership'])
    fingerprint = common.initial_match(run, result['initial_world'], case, config['identity'], config.get('scene_initial'))
    geometry = initial_admission(result['initial_world'], fingerprint, case, config['prior'], config['earlier_scenes'],
                                 config.get('scene_initial'))
    if (fingerprint != result['initial_fingerprint'] or fingerprint != meta.get('initial_fingerprint') or
            geometry != result.get('geometry') or geometry != meta.get('geometry')):
        raise ValueError('Initial scientific receipt differs')
    summary = validate_recording(run, case['scene_seed'], config['identity'], result['final_state'], fingerprint,
                                 research_provenance=binding.provenance())
    declared = result['numeric_admission']
    if common.numeric_admission([np.zeros((128, 128, 3), np.uint8)] * 2, declared['input_nodes']) != declared:
        raise ValueError('Numeric storage preflight differs')
    incidence = contacts.empty_incidence(); payload = hashlib.sha256(); count = 0
    for count, raw in enumerate(iter_ticks(run / 'recording'), 1):
        if count > MAX_TICKS or count > len(result['rows']):
            raise ValueError('Unexpected numeric row')
        if sum(np.asarray(value).nbytes for key, value in raw.items() if key not in ('episode', 'tick')) > declared['bytes_per_tick']:
            raise ValueError('Retained numeric interval exceeds cap')
        row = result['rows'][count - 1]; observed = v2.bind_interval(raw, row, result['contact_ownership'], count - 1)
        if row.get('contacts') != contacts.row_contacts(observed):
            raise ValueError('Cached contact receipt differs')
        contacts.add_incidence(incidence, observed); raw_payload_update(payload, raw)
    if (count != len(result['rows']) or type(result.get('executed_ticks')) is not int or result['executed_ticks'] != count or
            type(result.get('published_rows')) is not int or result['published_rows'] != count or summary['ticks'] != count or
            result.get('contact_incidence') != incidence or
            result.get('outcome') != common.natural_boundary(count, result['final_state']) or result['outcome'] != summary['outcome']):
        raise ValueError('Complete natural outcome/interval ledger differs')
    if payload.hexdigest() in {row['raw_payload_sha256'] for row in config['prior']['sources']}:
        raise ValueError('Complete development payload repeats admitted parent data')
    if list((run / 'snapshots').glob('*.snp')) != [run / 'snapshots/initial.snp'] or \
            (run / 'snapshots/initial.snp').stat().st_size > 16 * MiB:
        raise ValueError('Exactly one bounded initial SNP required')
    files, _, size = inventory(run)
    return {**summary, 'raw_payload_sha256': payload.hexdigest(), 'initial_fingerprint': fingerprint,
            'geometry': geometry, 'contact_incidence': incidence, 'files': files, 'source_bytes': size}


def native_owner(*_):
    """Direct calls stay refused: owners exist only inside ``run_development`` under a GO."""
    raise Refusal('Native owners run only through run_development under an admitted S2 GO')


def run_development(args):
    """S2 parent: 24 sequential owners, no retry/replacement, first failure stops, publication last."""
    import math
    import shutil
    import uuid
    from dataclasses import asdict
    from palimpsest.evaluate import bounded_process
    from palimpsest.storage import StorageBudget, StorageLimits
    common, contacts, v2 = _lib()
    started = time.monotonic(); deadline = started + STAGE_SECONDS
    root, assets, output = Path(args.repo).resolve(), Path(args.assets).resolve(), artifacts._safe_path(args.output)
    s1_output = Path(args.s1_output).resolve()
    if root != ROOT or not output.is_absolute() or output.exists() or not output.parent.is_dir():
        raise Refusal('Exact producer root and a fresh absolute output directory are required')
    if any(output == path or output.is_relative_to(path) or path.is_relative_to(output) for path in (s1_output, assets, root)):
        raise Refusal('Output overlaps S1 evidence, assets or the source tree')
    pins = source_pins(root); plan = contacts.plan(root); estimates = v2.admission(plan)
    report_s1, s1_sha = admit_candidates(s1_output)
    prior = prior_metadata(args.corpus_pin, report_s1['corpus_pin_sha256'])
    if prior['data_manifest_sha256'] != report_s1['data_manifest_sha256']:
        raise Refusal('Prior metadata manifest differs from the one S1 trained on')
    required_free = plan['limits']['combined_incremental_free_reservation_bytes'] + plan['limits']['free_floor_bytes']
    if shutil.disk_usage(output.parent).free < required_free:
        raise Refusal('Whole-study prospective capacity reservation is unavailable')
    output.mkdir(exist_ok=False)
    budget = StorageBudget((output,), StorageLimits(max_bytes=4 * 1024**3, min_free_bytes=1024**3, max_runs=len(CASES),
                                                    max_snapshots=1, max_exports=1), headroom_bytes=8 * MiB)
    config = {'repo': str(root), 'assets': str(assets), 'source_pins': pins, 'prior': prior,
              'storage': {'roots': [str(output)], 'limits': asdict(budget.limits), 'headroom_bytes': 8 * MiB}}
    extra = {'amendment_2_sha256': AMENDMENT_SHA256, 's1_report_sha256': s1_sha, 'source_pins': pins,
             'data_manifest_sha256': prior['data_manifest_sha256'], 'admission_estimate': estimates,
             'whole_study_free_required_bytes': required_free}
    report = {'id': REPORT_ID, 'route': 'development', 'protocol_sha256': PROTOCOL_SHA256, 'status': 'failed-infrastructure',
              'cases': {}, 'admission': {'status': 'not-admitted-operational-failure'}, 'qualification_claims': [], **extra}
    try:
        with budget.lock():
            from palimpsest.assets import verify_assets
            budget.check(estimates['aggregate_bytes'] + estimates['failure_extra_bytes'], path=output)
            assets_before = verify_assets(root, assets)
            if not assets_before['ok']:
                raise ValueError('Pinned runtime assets unavailable')
            identities = candidates(root, assets); scenes = {}; payloads = []

            def owner(case):
                if time.monotonic() >= deadline:
                    raise TimeoutError('Development stage deadline')
                check_pins(root, pins)
                stage = output / case['id']; stage.mkdir(); run = stage / uuid.uuid4().hex
                previous = scenes.get(case['scene_seed'])
                child = {**config, 'case': case, 'stage': str(stage), 'run': str(run),
                         'identity': identities[f"{case['training_seed']}:{case['arm']}"], 'earlier_scenes': scenes,
                         'scene_initial': previous['fingerprint'] if previous else None}
                allowance = min(float(OWNER_SECONDS), deadline - time.monotonic())
                if allowance <= 0:
                    raise TimeoutError('No remaining owner admission time')
                supervision = bounded_process(
                    [sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(child)], stage / 'supervision',
                    allowance, {**os.environ, 'PYTHONPATH': str(root / 'src'), 'MUJOCO_GL': 'egl', 'OMP_NUM_THREADS': '1',
                                'CUDA_VISIBLE_DEVICES': ''}, log_max_bytes=MiB, storage_budget=budget)
                elapsed = supervision.get('elapsed_seconds')
                if (supervision.get('status') != 'completed' or type(supervision.get('returncode')) is not int or
                        supervision['returncode'] != 0 or any(key in supervision for key in ('error', 'failure')) or
                        type(elapsed) not in (int, float) or not math.isfinite(elapsed) or not 0 <= elapsed <= allowance):
                    raise ValueError('Owner failed normal bounded disposition')
                result = common.read_json(stage / 'result.json', maximum=MiB)
                admitted = admit_record(run, result, child)
                if any(old != case['scene_seed'] and digest == admitted['raw_payload_sha256'] for old, digest in payloads):
                    raise ValueError('Distinct development scene repeats complete payload')
                payloads.append((case['scene_seed'], admitted['raw_payload_sha256']))
                scenes.setdefault(case['scene_seed'], {'geometry': admitted['geometry'],
                                                       'fingerprint': admitted['initial_fingerprint']})
                if time.monotonic() > deadline:
                    raise TimeoutError('Late owner readmission')
                return {**admitted, 'status': 'completed-recording', 'case': case, 'teacher_queries': 0,
                        'final_state': result['final_state'], 'executed_ticks': result['executed_ticks'], 'run': str(run)}

            report = {**evaluate('development', CASES, owner, lambda rows: reduce_development(rows, prior)), **extra}
            errors = []
            for key, operation in (('assets_after', lambda: verify_assets(root, assets)),
                                   ('identities_after', lambda: candidates(root, assets)),
                                   ('final_source_pins', lambda: source_pins(root))):
                try:
                    report[key] = operation()
                except Exception as error:
                    errors.append(key + ': ' + str(error)[:512])
            if (report.get('assets_after') != assets_before or report.get('identities_after') != identities or
                    report.get('final_source_pins') != pins):
                errors.append('Final source/assets/candidates differ')
            if report['status'] == 'completed' and (len(scenes) != len(DEVELOPMENT_SCENES) or
                                                    len(list(output.rglob('*.snp'))) != len(CASES)):
                errors.append('Incomplete fixed owner/initial plan')
            report['finalization_errors'] = errors
            if errors:
                report.update(status='failed-infrastructure',
                              admission={'status': 'not-admitted-operational-failure', 'qualification_claims': []})
            budget.check(0, path=output)
        if time.monotonic() > deadline:
            raise TimeoutError('Late development finalization/lease release')
        # Publication: the source-pin recheck is the last check before the final rename.
        common.publish(output / 'report.json', report, budget, deadline, lambda: check_pins(root, pins))
    except BaseException as error:
        report.update(status='failed-infrastructure', error={'type': type(error).__name__, 'message': str(error)[:1024]},
                      admission={'status': 'not-admitted-operational-failure', 'qualification_claims': []})
        common.write_json(output / 'failure.json', report, max_bytes=4 * MiB, storage_budget=budget)
    return report


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 2 and argv[0] == '--worker':
        return 0 if worker(json.loads(argv[1])) else 1
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--plan-only', action='store_true', help='Default: print the plan only')
    parser.add_argument('--go', type=Path, help='S2 owner GO record')
    parser.add_argument('--s1-output', type=Path, help='Published S1 trainer output')
    parser.add_argument('--output', type=Path, help='Fresh evaluation output directory (absolute)')
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--assets', type=Path, help='Pinned runtime asset root')
    parser.add_argument('--corpus-pin', type=Path, help='S0z corpus pin record named by the S1 report')
    args = parser.parse_args(argv)
    try:
        study = trainer.protocol()
        check_protocol(study)
        check_amendment(ROOT)
        if args.plan_only and args.go is not None:
            raise Refusal('--plan-only and --go are mutually exclusive')
        if args.go is None:
            print(json.dumps({'mode': 'plan-only', 'route': 'development', 'protocol_sha256': PROTOCOL_SHA256,
                              'amendment_2_sha256': AMENDMENT_SHA256, 'owners': len(CASES), 'per_owner_seconds': OWNER_SECONDS,
                              'cases': list(CASES), 'gate': 'each augmented seed >= 3 of 4; old arm reported',
                              'held_out_status': 'locked: requires development pass and a separate S3 GO'},
                             indent=1))
            return 0
        if None in (args.s1_output, args.output, args.assets, args.corpus_pin):
            raise Refusal('--go requires --s1-output, --assets, --corpus-pin and a fresh --output')
        if not all(Path(p).is_absolute() for p in (args.s1_output, args.output, args.assets, args.corpus_pin, args.go)):
            raise Refusal('Absolute paths are required')
        _, s1_sha = admit_candidates(args.s1_output)
        check_go(args.go, 'S2', s1_sha)
        if not trainer.inside_research_stage():
            raise Refusal('S2 runs only inside a run_research_stage.py census unit')
        started = time.monotonic()
        report = run_development(args)
    except (Refusal, OSError, ValueError, KeyError) as error:
        print(json.dumps({'status': 'refused', 'reason': f'{type(error).__name__}: {error}'}))
        return 2
    print(json.dumps({'status': report['status'], 'admission': report['admission']}))
    return 0 if report['status'] == 'completed' and time.monotonic() - started <= STAGE_SECONDS else 1


if __name__ == '__main__':
    raise SystemExit(main())
