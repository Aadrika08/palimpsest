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

The native owner (Engine episode of a v4 checkpoint) is deliberately not bound here; the
GO route refuses before any scene is generated until a reviewed v4 Engine binding exists.
"""
import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

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
            value.get('protocol_sha256') != PROTOCOL_SHA256 or value.get('s1_report_sha256') != s1_report_sha256 or
            not str(value.get('granted_by', '')).strip() or not str(value.get('granted_at', '')).strip()):
        raise Refusal(f'GO record does not name lane navigation, stage {stage}, this protocol and the S1 report')
    return sha


def admit_candidates(s1_output):
    """Six terminal S1 checkpoints behind a durable publication receipt."""
    report = trainer.success_admitted(s1_output)
    if report is None:
        raise Refusal('Six admitted terminal S1 checkpoints are required')
    payload = artifacts._read(Path(s1_output) / 'report.json', MAX_JSON)
    return report, hashlib.sha256(payload).hexdigest()


def native_owner(*_):
    raise Refusal('No reviewed v4 Engine research binding exists; native owners are not bound')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--plan-only', action='store_true', help='Default: print the plan only')
    parser.add_argument('--go', type=Path, help='S2 owner GO record')
    parser.add_argument('--s1-output', type=Path, help='Published S1 trainer output')
    parser.add_argument('--output', type=Path, help='Fresh evaluation output directory')
    args = parser.parse_args(argv)
    try:
        study = trainer.protocol()
        check_protocol(study)
        if args.plan_only and args.go is not None:
            raise Refusal('--plan-only and --go are mutually exclusive')
        if args.go is None:
            print(json.dumps({'mode': 'plan-only', 'route': 'development', 'protocol_sha256': PROTOCOL_SHA256,
                              'cases': list(CASES), 'gate': 'each augmented seed >= 3 of 4; old arm reported',
                              'held_out_status': 'locked: requires development pass and a separate S3 GO'},
                             indent=1))
            return 0
        if args.s1_output is None or args.output is None:
            raise Refusal('--go requires --s1-output and a fresh --output')
        _, s1_sha = admit_candidates(args.s1_output)
        check_go(args.go, 'S2', s1_sha)
        if not trainer.inside_research_stage():
            raise Refusal('S2 runs only inside a run_research_stage.py census unit')
        native_owner()
    except (Refusal, OSError, ValueError, KeyError) as error:
        print(json.dumps({'status': 'refused', 'reason': f'{type(error).__name__}: {error}'}))
        return 2
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
