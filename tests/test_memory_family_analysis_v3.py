"""Synthetic analysis-contract checks; no scientific or native evidence."""
import copy
import hashlib
import json
import math
from pathlib import Path
from statistics import fmean, variance
import subprocess
import sys

import pytest
from scipy.stats import t

from palimpsest import memory
from palimpsest.memory_experiment import CONDITIONS, KINDS
from scripts import memory_family_analysis_v3 as analysis
from scripts.memory_confirmatory_v3 import summarize
from scripts.memory_family_v3 import build_slots


PROTOCOL_PATH = Path(__file__).parents[1] / 'docs/plans/memory-family-analysis-v3-protocol.json'


def _protocol():
    return json.loads(PROTOCOL_PATH.read_bytes())


def _digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def _audit(case_id, condition, score, *, failed=False):
    trace_condition = ('own' if condition == 'sham' or
                       case_id.endswith('-no-event') else condition)
    if failed:
        return {'raw_audit_pass': True, 'policy_binding_pass': True,
            'goal': False, 'continuation_ticks': 7, 'path_length': .1,
            'invariant': _digest(case_id + '-invariant'),
            'trace_digest': _digest(case_id + '-' + trace_condition),
            'retained_task_failure': True,
            'retained_task_failure_reason': 'CueUnavailable',
            'outcome': {'reason': 'runtime_failure', 'type': 'CueUnavailable',
                        'message': 'selected_waypoint_unavailable: exit'}}
    return {'raw_audit_pass': True, 'policy_binding_pass': True,
        'goal': True, 'continuation_ticks': score, 'path_length': 4.,
        'invariant': _digest(case_id + '-invariant'),
        'trace_digest': _digest(case_id + '-' + trace_condition),
        'retained_task_failure': False, 'retained_task_failure_reason': None,
        'outcome': {'reason': 'goal'}}


def _readout(pattern, *, split='held-out', own_failure=None):
    block = 0 if split == 'development' else 17
    plan = build_slots(split, [block],
        [{'id': 'open', 'kind': 'open-route'}])['plan']
    families = plan['families']
    rows = []
    for index, family in enumerate(families):
        for kind, case_id in family['cases'].items():
            difference = pattern(index, kind)
            for condition in CONDITIONS:
                failed = own_failure == (index, kind) and condition in ('own', 'sham')
                if condition in ('own', 'sham'):
                    score = 450
                elif condition in ('no-U', 'swapped'):
                    score = 450 - difference
                else:
                    score = 450
                assert 0 < score < 900
                rows.append({'case_id': case_id, 'condition': condition,
                    'run_id': f'{case_id}-{condition}', 'owner_status': 'completed',
                    'owner_exit_proved': True,
                    'audit': _audit(case_id, condition, score, failed=failed)})
    prerequisites = [{'id': 'open', 'owner_status': 'completed',
        'owner_exit_proved': True,
        'audit': {'raw_audit_pass': True, 'acquired': True, 'goal': True}}]
    result = summarize(plan, rows, prerequisites)
    assert result['readout_complete']
    return result


def _verification(readout, protocol, design):
    split = readout['split']
    selection = None
    if split == 'held-out':
        selection = {'schema': 'memory-family-held-out-selection-v3',
            'raw_hex': f'{design["block"] | 0x800000:06x}',
            'selected_block': design['block'],
            'draw_count': 1, 'redraw_count': 0,
            'source_sha256': _digest('selection-source'),
            'runtime_sha256': _digest('selection-runtime'),
            'publication_sha256': _digest('selection-publication')}
    return {'schema': 'memory-family-analysis-verification-v3', 'split': split,
        'block': design['block'], 'registration_sha256': _digest('registration'),
        'plan_sha256': readout['plan_sha256'],
        'readout_sha256': memory.sha256(readout),
        'protocol_sha256': memory.sha256(protocol),
        'design_sha256': memory.sha256(design),
        'checks': {name: {'passed': True, 'sha256': _digest(name)} for name in (
            'family_sampling', 'input_provenance', 'assignment_balance',
            'condition_order', 'access_sequence', 'no_event_invariant')},
        'development_gate': None if split == 'development' else
            {'passed': True, 'sha256': _digest('development-gate')},
        'held_out_selection': selection}


def _analyze(pattern, *, split='held-out', own_failure=None):
    protocol = _protocol()
    readout = _readout(pattern, split=split, own_failure=own_failure)
    design = analysis.build_design(split, 0 if split == 'development' else 17, protocol)
    return analysis.analyze(
        readout, protocol, design, _verification(readout, protocol, design))


def test_protocol_is_exact_canonical_and_condition_order_is_minimally_balanced():
    protocol = _protocol()
    assert PROTOCOL_PATH.read_bytes() == memory.canonical_bytes(protocol)
    assert analysis.validate_protocol(protocol) == protocol == analysis.PROTOCOL
    before = copy.deepcopy(protocol)
    orders = [analysis.condition_order(row) for row in range(48)]
    family_rows = analysis.family_order()
    assert sorted(family_rows) == list(range(48))
    assert [row // 16 for row in family_rows[:9]] == [0, 1, 2, 1, 2, 0, 2, 0, 1]
    assert [analysis.case_order(row) for row in range(3)] == [
        ['change', 'null', 'no-event'], ['null', 'no-event', 'change'],
        ['no-event', 'change', 'null']]
    assert orders[0] == list(CONDITIONS)
    assert all(sorted(order) == sorted(CONDITIONS) for order in orders)
    for position in range(9):
        counts = [sum(order[position] == condition for order in orders)
                  for condition in CONDITIONS]
        assert min(counts) == 5 and max(counts) == 6
    assert protocol == before

    for mutation in ('missing', 'unknown', 'margin', 'boolean', 'nonfinite'):
        changed = copy.deepcopy(protocol)
        if mutation == 'missing': changed['stopping'].pop('retries')
        elif mutation == 'unknown': changed['unknown'] = False
        elif mutation == 'margin': changed['inference']['meaningful_benefit_ticks'] = 89
        elif mutation == 'boolean': changed['population']['families_per_phase'] = True
        else: changed['guardrails']['cost']['one_sided_confidence'] = float('nan')
        with pytest.raises(ValueError):
            analysis.validate_protocol(changed)

    frozen = copy.deepcopy(protocol)
    try:
        analysis.PROTOCOL['inference']['meaningful_benefit_ticks'] = 89
        assert analysis.validate_protocol(frozen) == frozen
        with pytest.raises(ValueError):
            analysis.validate_protocol(analysis.PROTOCOL)
        assert analysis.build_design('development', 0, frozen)['protocol_sha256'] == memory.sha256(frozen)
    finally:
        analysis.PROTOCOL.clear()
        analysis.PROTOCOL.update(frozen)


@pytest.mark.parametrize(('name', 'pattern', 'expected'), [
    ('benefit', lambda i, k: 0 if k == 'no-event' else
     (-155 if i % 2 == 0 else -145), 'benefit'),
    ('null', lambda i, k: 0 if k == 'no-event' else
     (-5 if i % 2 == 0 else 5), 'supported-null'),
    ('harm', lambda i, k: 0 if k == 'no-event' else
     (85 if i % 2 == 0 else 95), 'primary-harm'),
    ('inconclusive', lambda i, k: 0 if k == 'no-event' else
     (-440 if i % 2 == 0 else 300), 'inconclusive'),
])
def test_held_out_dispositions_use_families_strata_and_strict_primary_bounds(name, pattern, expected):
    result = _analyze(pattern)
    assert result['scientific_disposition'] == expected
    assert result['split'] == 'held-out' and result['family_count'] == 48
    assert result['r2_complete'] is False and result['qualification_claims'] == []
    assert result['receipt_bindings_validated'] is True
    assert result['receipt_truth_verified'] is False
    assert result['model_assumption'] == (
        'approximate normality of bounded family contrasts and independence across '
        'the 48 generated families within fixed cost strata, conditional on the '
        'registered generator and balanced assignment; IDs and hashes prove neither '
        'these assumptions nor generalization beyond the registered catalog')
    for reference in ('no-U', 'swapped'):
        interval = result['primary'][reference]
        assert interval['estimate'] == pytest.approx(
            sum(pattern(index, kind) for index in range(48) for kind in KINDS) / 144)
        assert interval['confidence'] == .975
        assert len(interval['strata']) == 3
    assert set(result['guardrails']) == {'no-U', 'swapped'}


def test_development_is_only_a_fixed_precision_gate_and_never_a_scientific_claim():
    precise = _analyze(lambda i, kind: 0 if kind == 'no-event' else
                       (i % 2) * 2 - 1 + KINDS.index(kind), split='development')
    imprecise = _analyze(
        lambda i, kind: 0 if kind == 'no-event' else
        (-440 if i % 2 == 0 else 300), split='development')
    assert precise['scientific_disposition'] == 'development-no-claim'
    assert precise['held_out_registration_admissible'] is True
    assert imprecise['scientific_disposition'] == 'development-no-claim'
    assert imprecise['held_out_registration_admissible'] is False
    assert precise['precision_screen']['passed'] is True
    assert imprecise['precision_screen']['passed'] is False
    assert set(precise['precision_screen']['endpoints']) == {
        'no-U:primary', 'swapped:primary', 'no-U:null', 'swapped:null'}


def test_margin_equality_never_passes_the_decision_table():
    guards = {'passed': True, 'observed_success_harm': False}
    assert analysis._held_out_disposition({
        'no-U': {'lower': -100, 'upper': -90},
        'swapped': {'lower': -100, 'upper': -90}}, guards) == ('inconclusive', 'inconclusive')
    assert analysis._held_out_disposition({
        'no-U': {'lower': -89, 'upper': 45},
        'swapped': {'lower': -89, 'upper': 45}}, guards) == ('inconclusive', 'inconclusive')


def test_overall_benefit_cannot_hide_null_cost_harm():
    result = _analyze(
        lambda i, kind: 0 if kind == 'no-event' else
        (50 if kind == 'null' else -400) + (1 if i % 2 else -1))
    assert all(row['upper'] < -90 for row in result['primary'].values())
    assert result['scientific_disposition'] == 'guardrail-not-established'
    assert not result['guardrails']['no-U']['null']['cost']['passed']


def test_one_own_only_null_failure_fails_the_zero_event_success_guard():
    result = _analyze(
        lambda i, kind: (-100 if kind == 'null' else -400) +
        (1 if i % 2 else -1) if kind != 'no-event' else 0,
        own_failure=(0, 'null'))
    assert all(row['upper'] < -90 for row in result['primary'].values())
    guard = result['guardrails']['no-U']['null']['success_harm']
    assert guard['events'] == 1 and guard['passed'] is False
    assert guard['upper_bound'] is None
    assert result['scientific_disposition'] == 'observed-guardrail-harm'


def test_zero_event_bound_is_attainable_but_explicitly_model_based():
    result = _analyze(lambda i, kind: 0 if kind == 'no-event' else
                      (-5 if i % 2 == 0 else 5))
    guard = result['guardrails']['no-U']['null']['success_harm']
    assert guard['events'] == 0
    assert guard['upper_bound'] == pytest.approx(-math.log(.05) / 48)
    assert guard['upper_bound'] < .0625 and guard['passed'] is True


def test_blocked_interval_uses_registered_satterthwaite_and_t_quantiles():
    pattern = lambda row, kind: 0 if kind == 'no-event' else row - 20 + KINDS.index(kind)
    result = _analyze(pattern)
    primary_values = [fmean(pattern(row, kind) for kind in KINDS) for row in range(48)]
    primary_variances = [variance(primary_values[start:start + 16])
                         for start in (0, 16, 32)]
    components = [sample_variance / (9 * 16) for sample_variance in primary_variances]
    degrees = sum(components)**2 / sum(component**2 / 15 for component in components)
    standard_error = math.sqrt(sum(components))
    critical = t.ppf(.9875, degrees)
    interval = result['primary']['no-U']
    assert interval['standard_error'] == pytest.approx(standard_error)
    assert interval['degrees_of_freedom'] == pytest.approx(degrees)
    assert interval['critical'] == pytest.approx(critical)
    assert interval['lower'] == pytest.approx(fmean(primary_values) - critical * standard_error)
    assert interval['upper'] == pytest.approx(fmean(primary_values) + critical * standard_error)

    null_values = [pattern(row, 'null') for row in range(48)]
    null_variances = [variance(null_values[start:start + 16]) for start in (0, 16, 32)]
    null_components = [sample_variance / (9 * 16) for sample_variance in null_variances]
    null_degrees = sum(null_components)**2 / sum(
        component**2 / 15 for component in null_components)
    null_error = math.sqrt(sum(null_components))
    cost = result['guardrails']['no-U']['null']['cost']
    assert cost['critical'] == pytest.approx(t.ppf(.95, null_degrees))
    assert cost['upper'] == pytest.approx(
        fmean(null_values) + t.ppf(.95, null_degrees) * null_error)


def test_zero_sample_variance_fails_inference_and_development_precision_closed():
    held = _analyze(lambda _i, _k: 0)
    development = _analyze(lambda _i, _k: 0, split='development')
    assert held['scientific_disposition'] == 'variance-unresolved'
    assert held['inference_ready'] is False
    assert all(row['status'] == 'zero-variance' for row in held['primary'].values())
    assert development['held_out_registration_admissible'] is False
    assert development['precision_screen']['passed'] is False

    null_only = _analyze(lambda i, kind: 0 if kind != 'change' else
                         (-200 if i % 2 == 0 else -180))
    assert all(row['status'] == 'ok' for row in null_only['primary'].values())
    assert all(null_only['guardrails'][reference]['null']['cost']['status'] == 'zero-variance'
               for reference in ('no-U', 'swapped'))
    assert null_only['scientific_disposition'] == 'variance-unresolved'


def test_no_event_difference_is_an_invariant_error_not_sampling_variation():
    protocol = _protocol()
    readout = _readout(lambda i, kind: (-1 if i % 2 == 0 else 1)
                       if kind == 'no-event' else -100)
    design = analysis.build_design('held-out', 17, protocol)
    verification = _verification(readout, protocol, design)
    with pytest.raises(ValueError, match='No-event'):
        analysis.analyze(readout, protocol, design, verification)

    readout = _readout(lambda i, kind: 0 if kind == 'no-event' else -100)
    changed = copy.deepcopy(readout)
    cell = next(cell for cell in changed['cells']
                if cell['kind'] == 'no-event' and cell['condition'] == 'oracle')
    cell['trace_digest'] = _digest('different-no-event-trace')
    verification = _verification(changed, protocol, design)
    with pytest.raises(ValueError, match='No-event'):
        analysis.analyze(changed, protocol, design, verification)


def test_primary_harm_overrides_failed_or_observed_guards():
    primary = {'no-U': {'lower': 46, 'upper': 60},
               'swapped': {'lower': -10, 'upper': 20}}
    assert analysis._held_out_disposition(primary, {
        'passed': False, 'observed_success_harm': True,
    }) == ('primary-harm', 'primary-harm')


def test_generated_design_and_recomputed_cell_contrasts_are_not_caller_assertions():
    protocol = _protocol()
    readout = _readout(lambda i, kind: 0 if kind == 'no-event' else i % 3 - 1)
    design = analysis.build_design('held-out', 17, protocol)
    verification = _verification(readout, protocol, design)

    changed_design = copy.deepcopy(design)
    changed_design['families'][0]['cost_stratum'] = 'north'
    changed_verification = copy.deepcopy(verification)
    changed_verification['design_sha256'] = memory.sha256(changed_design)
    with pytest.raises(ValueError):
        analysis.analyze(readout, protocol, changed_design, changed_verification)

    changed_readout = copy.deepcopy(readout)
    changed_readout['contrasts']['no-U']['family_cost_differences'][0] += 1
    changed_verification = copy.deepcopy(verification)
    changed_verification['readout_sha256'] = memory.sha256(changed_readout)
    with pytest.raises(ValueError):
        analysis.analyze(changed_readout, protocol, design, changed_verification)


@pytest.mark.parametrize('mutation', ['duplicate-run', 'case-invariant', 'own-sham'])
def test_analyzer_rejects_readouts_impossible_under_the_descriptive_contract(mutation):
    protocol = _protocol()
    readout = _readout(lambda i, kind: 0 if kind == 'no-event' else i % 3 - 1)
    design = analysis.build_design('held-out', 17, protocol)
    if mutation == 'duplicate-run':
        readout['cells'][1]['run_id'] = readout['cells'][0]['run_id']
    else:
        case_id = next(cell['case_id'] for cell in readout['cells']
                       if cell['kind'] == 'change')
        condition = 'no-U' if mutation == 'case-invariant' else 'sham'
        cell = next(cell for cell in readout['cells']
                    if cell['case_id'] == case_id and cell['condition'] == condition)
        cell['invariant' if mutation == 'case-invariant' else 'trace_digest'] = _digest(mutation)
    verification = _verification(readout, protocol, design)
    with pytest.raises(ValueError):
        analysis.analyze(readout, protocol, design, verification)


def test_own_sham_validation_preserves_upstream_numeric_equality():
    protocol = _protocol()
    readout = _readout(lambda i, kind: 0 if kind == 'no-event' else i % 3 - 1)
    cell = next(cell for cell in readout['cells']
                if cell['kind'] == 'change' and cell['condition'] == 'sham')
    cell['path_length'] = int(cell['path_length'])
    design = analysis.build_design('held-out', 17, protocol)
    verification = _verification(readout, protocol, design)
    assert analysis.analyze(readout, protocol, design, verification)['receipt_bindings_validated']


def test_result_binds_verification_receipt_lineage():
    protocol = _protocol()
    readout = _readout(lambda i, kind: 0 if kind == 'no-event' else i % 3 - 1)
    design = analysis.build_design('held-out', 17, protocol)
    verification = _verification(readout, protocol, design)
    first = analysis.analyze(readout, protocol, design, verification)
    changed = copy.deepcopy(verification)
    changed['checks']['condition_order']['sha256'] = _digest('different-order-receipt')
    second = analysis.analyze(readout, protocol, design, changed)
    assert first['verification_sha256'] == memory.sha256(verification)
    assert second['verification_sha256'] == memory.sha256(changed)
    assert first['verification_sha256'] != second['verification_sha256']


@pytest.mark.parametrize('mutation', [
    'incomplete', 'readout-digest', 'protocol-digest', 'failed-check',
    'missing-check', 'development-gate', 'split', 'family-count',
    'selection',
])
def test_incomplete_unbound_or_missequenced_input_never_reaches_inference(mutation):
    protocol = _protocol()
    readout = _readout(lambda _i, _k: 0)
    design = analysis.build_design('held-out', 17, protocol)
    verification = _verification(readout, protocol, design)
    if mutation == 'incomplete': readout['readout_complete'] = False
    elif mutation == 'readout-digest': verification['readout_sha256'] = 'f' * 64
    elif mutation == 'protocol-digest': verification['protocol_sha256'] = 'f' * 64
    elif mutation == 'failed-check': verification['checks']['condition_order']['passed'] = False
    elif mutation == 'missing-check': verification['checks'].pop('family_sampling')
    elif mutation == 'development-gate': verification['development_gate'] = None
    elif mutation == 'selection': verification['held_out_selection']['raw_hex'] = '000012'
    elif mutation == 'split': verification['split'] = 'development'
    else: readout['registered_family_count'] = 47
    with pytest.raises(ValueError):
        analysis.analyze(readout, protocol, design, verification)


def test_boolean_development_block_is_not_integer_zero():
    protocol = _protocol()
    readout = _readout(lambda _i, _kind: 0, split='development')
    design = analysis.build_design('development', 0, protocol)
    verification = _verification(readout, protocol, design)
    verification['block'] = False
    with pytest.raises(ValueError):
        analysis.analyze(readout, protocol, design, verification)


def test_analysis_is_deterministic_and_does_not_mutate_inputs():
    protocol = _protocol()
    readout = _readout(lambda i, kind: 0 if kind == 'no-event' else
                       (i % 5) * 10 - 40 + KINDS.index(kind))
    design = analysis.build_design('held-out', 17, protocol)
    verification = _verification(readout, protocol, design)
    before = copy.deepcopy((readout, protocol, design, verification))
    first = analysis.analyze(readout, protocol, design, verification)
    second = analysis.analyze(readout, protocol, design, verification)
    assert first == second
    assert (readout, protocol, design, verification) == before
    assert memory.canonical_bytes(first)


def test_cli_accepts_only_bounded_canonical_json(tmp_path):
    protocol = _protocol()
    readout = _readout(lambda i, kind: 0 if kind == 'no-event' else i % 3 - 1)
    design = analysis.build_design('held-out', 17, protocol)
    verification = _verification(readout, protocol, design)
    envelope = {'readout': readout, 'protocol': protocol, 'design': design,
                'verification': verification}
    path = tmp_path / 'analysis.json'
    path.write_bytes(memory.canonical_bytes(envelope))
    command = [sys.executable, '-m', 'scripts.memory_family_analysis_v3', str(path)]
    result = subprocess.run(command, capture_output=True, check=True)
    output = json.loads(result.stdout)
    assert result.stdout == memory.canonical_bytes(output) + b'\n'

    invalid = {
        'noncanonical': json.dumps(envelope).encode(),
        'nonfinite': b'{"x":NaN}',
        'duplicate': b'{"x":1,"x":2}',
        'oversize': b' ' * (analysis.MAX_INPUT_BYTES + 1),
    }
    for payload in invalid.values():
        path.write_bytes(payload)
        rejected = subprocess.run(command, capture_output=True)
        assert rejected.returncode != 0
