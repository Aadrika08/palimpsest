"""Synthetic accounting examples, not experimental or independence evidence."""
import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from palimpsest.memory_experiment import CONDITIONS, KINDS


def example():
    plan = {'schema': 'memory-confirmatory-readout-v3', 'split': 'development',
            'conditions': list(CONDITIONS), 'families': [
                {'id': f'family-{i}', 'cases': {k: f'case-{i}-{k}' for k in KINDS}}
                for i in range(2)], 'prerequisites': [{'id': 'open', 'kind': 'open-route'}]}
    rows = []
    for i, family in enumerate(plan['families']):
        for kind, case_id in family['cases'].items():
            for condition in CONDITIONS:
                failure = i == 0 and kind == 'null' and condition in ('own', 'sham')
                ticks = 7 if failure else 100 + 30*i + (30 if condition in ('own', 'sham') else 0)
                audit = {'raw_audit_pass': True, 'policy_binding_pass': True,
                    'goal': not failure, 'continuation_ticks': ticks,
                    'path_length': .1 if failure else 4., 'invariant': 'a'*64,
                    'trace_digest': 'b'*64, 'retained_task_failure': failure,
                    'retained_task_failure_reason': 'CueUnavailable' if failure else None,
                    'outcome': {'reason': 'runtime_failure', 'type': 'CueUnavailable',
                        'message': 'selected_waypoint_unavailable: exit'} if failure else {'reason': 'goal'}}
                rows.append({'case_id': case_id, 'condition': condition,
                    'run_id': f'{case_id}-{condition}', 'owner_status': 'completed',
                    'owner_exit_proved': True, 'audit': audit})
    prerequisites = [{'id': 'open', 'owner_status': 'completed', 'owner_exit_proved': True,
                      'audit': {'raw_audit_pass': True, 'acquired': True, 'goal': True}}]
    return plan, rows, prerequisites


def summarize(*args):
    return importlib.import_module('scripts.memory_confirmatory_v3').summarize(*args)


def test_complete_family_readout_preserves_failure_and_equal_weighting():
    plan, rows, prerequisites = example()
    before = copy.deepcopy((plan, rows, prerequisites))
    result = summarize(plan, rows, prerequisites)
    assert (plan, rows, prerequisites) == before
    assert result['readout_complete'] and result['registered_family_count'] == 2
    assert result['expected_slots'] == result['scored_slots'] == 54
    failed = next(r for r in result['cells'] if r['case_id'] == 'case-0-null' and r['condition'] == 'own')
    assert failed['capped_ticks'] == 900 and failed['continuation_ticks'] == 7
    assert failed['path_length'] == .1 and failed['outcome']['type'] == 'CueUnavailable'
    contrast = result['contrasts']['no-U']
    assert contrast['family_cost_differences'] == pytest.approx([860/3, 30])
    assert contrast['mean_cost_difference'] == pytest.approx(475/3)
    assert contrast['mean_goal_difference'] == pytest.approx(-1/6)
    assert contrast['by_kind']['null']['mean_cost_difference'] == 415
    assert result['primary_references'] == ['no-U', 'swapped']
    assert result['r2_complete'] is False and result['qualification_claims'] == []
    assert result['family_independence_verified'] is False


@pytest.mark.parametrize('mutation', ['missing', 'owner-timeout', 'owner-exit', 'raw-audit', 'unknown-exception', 'acquisition-timeout', 'prerequisite-failed', 'prerequisite-missing'])
def test_incomplete_matrix_never_imputes_task_score_or_aggregates(mutation):
    plan, rows, gates = example()
    target = rows[0]
    if mutation == 'missing': rows.pop()
    elif mutation == 'owner-timeout': rows[0].update(owner_status='timeout', audit=None)
    elif mutation == 'owner-exit': rows[0]['owner_exit_proved'] = False
    elif mutation == 'raw-audit': rows[0]['audit']['raw_audit_pass'] = False
    elif mutation == 'unknown-exception':
        rows[0]['audit'].update(goal=False, retained_task_failure=True,
            retained_task_failure_reason='MemoryError', outcome={'reason':'runtime_failure','type':'MemoryError'})
    elif mutation == 'acquisition-timeout':
        target = next(row for row in rows if row['condition'] == 'swapped')
        target['audit'].update(goal=False, retained_task_failure=True,
            retained_task_failure_reason='acquisition_timeout',
            outcome={'reason':'runtime_failure','type':'ValueError',
                     'message':'Memory-v2 supervisor failure: acquisition_timeout'})
    elif mutation == 'prerequisite-failed': gates[0]['audit']['goal'] = False
    else: gates.clear()
    result = summarize(plan, rows, gates)
    assert not result['readout_complete'] and result['contrasts'] is None
    assert result['missing_slots'] or result['unscored_slots'] or result['unmet_prerequisites']
    if mutation in ('owner-timeout', 'owner-exit', 'raw-audit', 'unknown-exception', 'acquisition-timeout'):
        assert not any(c['case_id'] == target['case_id'] and c['condition'] == target['condition'] for c in result['cells'])
    if mutation == 'acquisition-timeout':
        assert next(row for row in result['unscored_slots']
                    if row['case_id'] == target['case_id'] and
                    row['condition'] == target['condition'])['reason'] == 'acquisition-before-fork'


@pytest.mark.parametrize('mutation', ['duplicate-slot', 'extra-slot', 'reused-run', 'case-alias', 'four-conditions', 'failed-sham', 'invariant', 'boolean-ticks', 'nan-path', 'goal-cause', 'failure-cause'])
def test_contradictory_or_ambiguous_evidence_is_rejected(mutation):
    plan, rows, gates = example()
    if mutation == 'duplicate-slot': rows.append(copy.deepcopy(rows[0]))
    elif mutation == 'extra-slot': rows[-1]['case_id'] = 'unregistered'
    elif mutation == 'reused-run': rows[-1]['run_id'] = rows[0]['run_id']
    elif mutation == 'case-alias': plan['families'][1]['cases']['null'] = 'case-0-null'
    elif mutation == 'four-conditions': plan['conditions'] = list(CONDITIONS[:4])
    elif mutation == 'failed-sham': next(r for r in rows if r['case_id'] == 'case-0-null' and r['condition'] == 'sham')['audit']['trace_digest'] = 'c'*64
    elif mutation == 'invariant': rows[-1]['audit']['invariant'] = 'd'*64
    elif mutation == 'boolean-ticks': rows[0]['audit']['continuation_ticks'] = True
    elif mutation == 'nan-path': rows[0]['audit']['path_length'] = float('nan')
    elif mutation == 'goal-cause': rows[0]['audit']['outcome']['reason'] = 'time_limit'
    else:
        r = next(r for r in rows if r['audit']['retained_task_failure'])
        r['audit']['retained_task_failure_reason'] = 'waypoint_timeout'
    with pytest.raises(ValueError): summarize(plan, rows, gates)


def test_cli_uses_only_synthetic_json_and_rejects_nonfinite(tmp_path):
    plan, rows, prerequisites = example()
    path = tmp_path/'input.json'
    path.write_text(json.dumps({'plan':plan,'rows':rows,'prerequisites':prerequisites}))
    command = [sys.executable, '-m', 'scripts.memory_confirmatory_v3', str(path)]
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    assert json.loads(result.stdout)['readout_complete']
    data = {'plan':plan,'rows':rows,'prerequisites':prerequisites}
    path.write_text('{"plan":'+json.dumps(plan)+','+json.dumps(data)[1:])
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode != 0 and not result.stdout
    path.write_text('{"invalid":NaN}')
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode != 0 and not result.stdout
    with path.open('wb') as f: f.truncate(32*1024**2+1)
    result = subprocess.run(command, text=True, capture_output=True)
    assert result.returncode != 0 and not result.stdout
