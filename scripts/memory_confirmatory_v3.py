"""Describe a complete registered matrix; never launch or qualify a study."""
import argparse
import copy
import json
import math
from pathlib import Path
from statistics import fmean

from palimpsest import memory
from palimpsest.memory_experiment import CONDITIONS, KINDS
from scripts.memory_decision_pilot import capped_score, prerequisite_pass

MAX_INPUT_BYTES = 32 * 1024**2
SUPERVISOR_FAILURES = ('continuation_timeout', 'waypoint_timeout', 'inspection_timeout',
    'no_route', 'attempt_limit')
ACQUISITION_FAILURES = ('acquisition_timeout', 'acquisition_incomplete', 'acquisition_blocked')


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_plan(plan):
    memory._fields(plan, 'schema split conditions families prerequisites')
    require(plan['schema'] == 'memory-confirmatory-readout-v3', 'Unknown readout schema')
    memory._enum(plan['split'], ('development', 'held-out'))
    require(plan['conditions'] == list(CONDITIONS), 'Exactly nine frozen conditions required')
    memory._list(plan['families'], 64)
    memory._list(plan['prerequisites'], 256)
    require(bool(plan['families']) and bool(plan['prerequisites']), 'Families and prerequisites must be declared')
    ids, cases, gates = set(), {}, {}

    def add(identifier):
        memory._id(identifier)
        require(identifier not in ids, 'Reused family, case or prerequisite ID')
        ids.add(identifier)

    for family in plan['families']:
        memory._fields(family, 'id cases')
        add(family['id'])
        memory._fields(family['cases'], ' '.join(KINDS))
        for kind in KINDS:
            identifier = family['cases'][kind]
            add(identifier)
            cases[identifier] = (family['id'], kind)
    for gate in plan['prerequisites']:
        memory._fields(gate, 'id kind')
        add(gate['id'])
        memory._enum(gate['kind'], ('prefix', 'open-route', 'retreat', 'restore'))
        gates[gate['id']] = gate['kind']
    return cases, gates


def owner_issue(row):
    memory._enum(row['owner_status'], ('completed', 'failed', 'timeout', 'unattempted', 'interrupted'))
    require(type(row['owner_exit_proved']) is bool, 'Owner exit flag must be Boolean')
    require(row['audit'] is None or type(row['audit']) is dict, 'Audit must be an object or null')
    if row['owner_status'] != 'completed' or not row['owner_exit_proved']:
        return 'owner-incomplete'
    if row['audit'] is None or row['audit'].get('raw_audit_pass') is not True:
        return 'raw-audit-incomplete'
    return None


def project_audit(audit):
    if audit.get('policy_binding_pass') is not True:
        return None, 'policy-binding-incomplete'
    fields = ('goal', 'continuation_ticks', 'path_length', 'outcome', 'trace_digest', 'invariant')
    require(set(fields) <= set(audit), 'Audited outcome projection is incomplete')
    score = capped_score(audit)
    for name in ('trace_digest', 'invariant'):
        memory._digest(audit[name])
    path = audit['path_length']
    require(type(path) in (int, float) and math.isfinite(path) and path >= 0, 'Invalid actual path length')
    outcome = audit['outcome']
    require(type(outcome) is dict, 'Terminal outcome must be an object')
    if audit['goal']:
        require(outcome.get('reason') == 'goal' and audit.get('retained_task_failure', False) is False,
                'Goal contradicts terminal outcome')
    else:
        reason = audit.get('retained_task_failure_reason')
        if audit.get('retained_task_failure') is not True:
            return None, 'natural-failure-proof-missing'
        if reason in ('stalled', 'time_limit'):
            require(outcome.get('reason') == reason, 'Natural terminal cause disagrees')
        elif reason == 'CueUnavailable':
            require(outcome.get('reason') == 'runtime_failure' and outcome.get('type') == reason
                    and type(outcome.get('message')) is str
                    and outcome['message'].startswith('selected_waypoint_unavailable: '),
                    'Cue failure contradicts terminal outcome')
        elif reason in SUPERVISOR_FAILURES + ACQUISITION_FAILURES:
            require(outcome.get('reason') == 'runtime_failure' and outcome.get('type') == 'ValueError'
                    and outcome.get('message') == 'Memory-v2 supervisor failure: '+reason,
                    'Supervisor failure contradicts terminal outcome')
            if reason in ACQUISITION_FAILURES:
                return None, 'acquisition-before-fork'
        else:
            return None, 'unknown-terminal-infrastructure'
    if 'capped_ticks' in audit:
        require(type(audit['capped_ticks']) is int and audit['capped_ticks'] == score,
                'Retained capped score disagrees')
    return {**{key: copy.deepcopy(audit[key]) for key in fields}, 'capped_ticks': score}, None


def summarize(plan, rows, prerequisites):
    """Audit flags are producer assertions; this function only checks accounting."""
    memory._bounded({'plan': plan, 'rows': rows, 'prerequisites': prerequisites}, MAX_INPUT_BYTES)
    cases, gates = validate_plan(plan)
    expected = {(case, condition) for case in cases for condition in CONDITIONS}
    memory._list(rows, len(expected)+1)
    memory._list(prerequisites, len(gates)+1)
    observed, runs, cells, unscored, seen_gates, unmet = set(), set(), {}, [], set(), []
    for row in rows:
        memory._fields(row, 'case_id condition run_id owner_status owner_exit_proved audit')
        memory._id(row['case_id']); memory._enum(row['condition'], CONDITIONS); memory._id(row['run_id'])
        slot = (row['case_id'], row['condition'])
        require(slot in expected and slot not in observed, 'Unregistered or duplicate condition slot')
        require(row['run_id'] not in runs, 'Run reused across condition slots')
        runs.add(row['run_id']); observed.add(slot)
        issue = owner_issue(row)
        cell = None
        if issue is None:
            cell, issue = project_audit(row['audit'])
        if issue:
            unscored.append({'case_id': slot[0], 'condition': slot[1], 'reason': issue})
        else:
            family, kind = cases[slot[0]]
            cells[slot] = {'family_id': family, 'case_id': slot[0], 'kind': kind,
                           'condition': slot[1], 'run_id': row['run_id'], **cell}
    for row in prerequisites:
        memory._fields(row, 'id owner_status owner_exit_proved audit')
        memory._id(row['id'])
        require(row['id'] in gates and row['id'] not in seen_gates, 'Unknown or duplicate prerequisite')
        seen_gates.add(row['id'])
        issue = owner_issue(row)
        if issue is None and not prerequisite_pass(gates[row['id']], row['audit']):
            issue = 'prerequisite-failed'
        if issue:
            unmet.append({'id': row['id'], 'reason': issue})
    unmet += [{'id': identifier, 'reason': 'missing'} for identifier in sorted(set(gates)-seen_gates)]
    for case in cases:
        present = [cells[case, c] for c in CONDITIONS if (case, c) in cells]
        require(len({r['invariant'] for r in present}) <= 1, 'Paired invariant differs')
        if (case, 'own') in cells and (case, 'sham') in cells:
            own, sham = cells[case, 'own'], cells[case, 'sham']
            require(all(own[k] == sham[k] for k in ('trace_digest', 'goal', 'continuation_ticks',
                        'path_length', 'outcome')), 'Own/sham mismatch, including retained failures')
    missing = [{'case_id': c, 'condition': k} for c, k in sorted(expected-observed)]
    complete = not (missing or unscored or unmet)
    contrasts = None
    if complete:
        contrasts = {}
        for reference in CONDITIONS[1:]:
            family_costs, family_goals, by_kind = [], [], {k: [] for k in KINDS}
            for family in plan['families']:
                differences = []
                for kind in KINDS:
                    case = family['cases'][kind]
                    own, other = cells[case, 'own'], cells[case, reference]
                    pair = (own['capped_ticks']-other['capped_ticks'], int(own['goal'])-int(other['goal']))
                    differences.append(pair); by_kind[kind].append(pair)
                family_costs.append(fmean(p[0] for p in differences))
                family_goals.append(fmean(p[1] for p in differences))
            contrasts[reference] = {'family_ids': [f['id'] for f in plan['families']],
                'family_cost_differences': family_costs, 'family_goal_differences': family_goals,
                'mean_cost_difference': fmean(family_costs), 'mean_goal_difference': fmean(family_goals),
                'by_kind': {k: {'mean_cost_difference': fmean(p[0] for p in values),
                    'mean_goal_difference': fmean(p[1] for p in values)} for k, values in by_kind.items()}}
    return {'schema': 'memory-confirmatory-readout-v3', 'plan_sha256': memory.sha256(plan),
        'split': plan['split'], 'readout_complete': complete, 'registered_family_count': len(plan['families']),
        'expected_slots': len(expected), 'scored_slots': len(cells), 'missing_slots': missing,
        'unscored_slots': unscored, 'unmet_prerequisites': unmet,
        'cells': [cells[key] for key in sorted(cells)], 'contrasts': contrasts,
        'primary_references': ['no-U', 'swapped'], 'family_independence_verified': False,
        'input_provenance_verified': False, 'r2_complete': False, 'qualification_claims': [],
        'scope': 'Descriptive registered-family accounting only; no raw verification, independence proof or inference'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    with args.input.open('rb') as stream:
        payload = stream.read(MAX_INPUT_BYTES+1)
    require(len(payload) <= MAX_INPUT_BYTES, 'Input exceeds 32 MiB')

    def reject(value):
        raise ValueError('Nonfinite JSON: '+value)

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key: '+key)
            result[key] = value
        return result

    data = json.loads(payload, parse_constant=reject, object_pairs_hook=unique_object)
    memory._fields(data, 'plan rows prerequisites')
    print(json.dumps(summarize(**data), sort_keys=True, allow_nan=False))
