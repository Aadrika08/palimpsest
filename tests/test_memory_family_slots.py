"""Synthetic slot accounting; no owners, artifacts or scientific observations."""
import copy
import importlib

import pytest

from palimpsest import memory
from palimpsest.memory_experiment import CONDITIONS, KINDS
from scripts.memory_confirmatory_v3 import summarize, validate_plan


def build(split='development', blocks=None, prerequisites=None):
    return importlib.import_module('scripts.memory_family_v3').build_slots(
        split, [0] if blocks is None else blocks,
        [{'id': 'declared-open-route', 'kind': 'open-route'}]
        if prerequisites is None else prerequisites)


def test_complete_block_binds_every_condition_and_case_without_claiming_evidence():
    result = build(blocks=[0])
    families = result['plan']['families']
    assert len(families) == 48
    assert len(result['cases']) == 144
    assert len(result['slots']) == 1296
    assert result['claim'] == 'software-candidate-only'
    assert result['native_allocation'] is False
    case_index, _ = validate_plan(result['plan'])
    cases = {c['case_id']: c for c in result['cases']}
    assert set(cases) == set(case_index)
    tuples = {(s['case_id'], s['condition']) for s in result['slots']}
    assert len(tuples) == len(result['slots'])
    assert tuples == {(cid, condition) for cid in cases for condition in CONDITIONS}
    for slot in result['slots']:
        case = cases[slot['case_id']]
        assert {k: slot[k] for k in slot if k != 'condition'} == {
            k: case[k] for k in ('family_id', 'case_id', 'case_sha256',
                'profile_sha256', 'seed', 'split', 'block', 'row', 'kind')}
    for family in families:
        twins = [cases[family['cases'][kind]] for kind in KINDS]
        assert len({c['seed'] for c in twins}) == 1
        assert len({c['case_id'] for c in twins}) == 3
        assert len({c['case_sha256'] for c in twins}) == 3
        assert {c['family_id'] for c in twins} == {family['id']}
    report = summarize(result['plan'], [], [])
    assert not report['readout_complete'] and report['contrasts'] is None
    assert len(report['missing_slots']) == len(result['slots'])
    assert report['scored_slots'] == 0
    assert report['unmet_prerequisites'] == [
        {'id': 'declared-open-route', 'reason': 'missing'}]


def test_assignment_table_warning_and_input_values_are_retained_deterministically():
    from palimpsest.memory_decision_world import family_assignment
    gates = [{'id': 'declared-restore', 'kind': 'restore'}]
    blocks = [2]
    before = copy.deepcopy((blocks, gates))
    result = build(blocks=blocks, prerequisites=gates)
    assert (blocks, gates) == before
    assert result == build(blocks=blocks, prerequisites=gates)
    assert result['assignment_table'] == [family_assignment(row) for row in range(48)]
    assert result['aliases'] == ['strength-2 public projection; interaction effects are not separately identified']
    result['plan']['prerequisites'][0]['id'] = 'changed'
    assert gates == before[1]


def test_explicit_synthetic_split_descriptors_have_disjoint_family_ids_and_seeds():
    development, held = build(), build(split='held-out')
    assert development['plan']['split'] == 'development'
    assert held['plan']['split'] == 'held-out'
    for key in ('family_id', 'case_id', 'seed'):
        assert {c[key] for c in development['cases']}.isdisjoint(
            {c[key] for c in held['cases']})
    assert memory.sha256(development) != memory.sha256(held)


@pytest.mark.parametrize('blocks', [[], [True], [False], [0, 0], [1, 0], [0, 1],
    [0, 1, 2], [-1], [2**23], [0.0], [0, '1'], (0,), 0])
def test_incomplete_duplicate_boolean_noncanonical_and_unbounded_blocks_refused(blocks):
    with pytest.raises(ValueError):
        build(blocks=blocks)


@pytest.mark.parametrize('split', [True, '', 'development-test', None])
def test_unknown_or_noncanonical_split_refused(split):
    with pytest.raises(ValueError):
        build(split=split)


@pytest.mark.parametrize('gates', [[], True, [{}],
    [{'id': 'gate', 'kind': 'invented'}],
    [{'id': 'gate', 'kind': 'prefix'}, {'id': 'gate', 'kind': 'restore'}],
    [{'id': 'gate', 'kind': 'prefix', 'passed': True}],
    [{'id': f'gate-{i}', 'kind': 'prefix'} for i in range(257)]])
def test_missing_malformed_duplicate_or_unbounded_prerequisites_refused(gates):
    with pytest.raises(ValueError):
        build(prerequisites=gates)
