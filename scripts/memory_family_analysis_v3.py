"""Analyze one complete registered memory-family matrix; never run a study."""
import argparse
import copy
import json
import math
import sys
from pathlib import Path
from statistics import fmean, variance

from scipy.stats import t

from palimpsest import memory, memory_decision_world as world
from palimpsest.memory_experiment import CONDITIONS, KINDS


MAX_INPUT_BYTES = 32 * 1024**2
REFERENCES = ('no-U', 'swapped')
STRATA = ('south', 'north', 'tie')
CHECKS = ('family_sampling', 'input_provenance', 'assignment_balance',
          'condition_order', 'access_sequence', 'no_event_invariant')
PROTOCOL = {
    'execution_order': {
        'case_order': 'cyclic-change-null-no-event-by-row-v1',
        'conditions': list(CONDITIONS),
        'family_order': 'interleaved-rotating-cost-strata-v1',
        'method': 'cyclic-nine-condition-by-row-v1',
        'position_imbalance_max': 1,
        'prerequisites': 'registered-order-first',
        'source_before_forks': True,
    },
    'guardrails': {
        'claim': 'global-intersection-only-v1',
        'cost': {'one_sided_confidence': .95, 'upper_margin_ticks': 45},
        'individual_population_claims': False,
        'kinds': ['null'],
        'no_event': {
            'method': 'exact-all-nine-trace-outcome-equality-v1',
            'upstream_zero_selector_behavior_required': True,
        },
        'success_harm': {
            'method': 'independent-zero-event-upper-v1',
            'one_sided_confidence': .95,
            'upper_probability': .0625,
        },
    },
    'inference': {
        'critical_value': 'scipy.stats.t.ppf-v1',
        'familywise_alpha': .05,
        'meaningful_benefit_ticks': 90,
        'multiplicity': 'bonferroni-two-primary-v1',
        'null_bounds_ticks': {'lower': -90, 'upper': 45},
        'precision_half_width_ticks': 45,
        'primary_interval': 'blocked-satterthwaite-t-v1',
        'primary_references': list(REFERENCES),
        'primary_two_sided_confidence': .975,
        'zero_variance': 'fail-closed',
    },
    'population': {
        'development_block': 0,
        'families_per_phase': 48,
        'held_out_block_limit': 2**23,
        'held_out_block_selection': {
            'bytes': 3,
            'draw_count': 1,
            'mapping': 'big-endian-mask-high-bit-v1',
            'method': 'os.getrandom-v1',
            'publish': 'exclusive-before-case-construction',
            'raw_hex_digits': 6,
            'redraw_count': 0,
            'retain_source_runtime_hashes': True,
        },
        'sampling_model': 'approximate-normal-independent-families-within-cost-strata-v1',
        'strata': {'families_each': 16, 'names': list(STRATA)},
        'target': 'registered-memory-family-v3-generator-catalog',
    },
    'schema': 'memory-family-analysis-protocol-v3',
    'sequencing': {
        'development_claims': False,
        'development_use': 'technical-and-precision-gate-only',
        'held_out_access': 'after-complete-development-gates-and-protocol-hash-freeze',
        'pool_splits': False,
        'post_result_extension': False,
    },
    'stopping': {
        'acquisition_failure': 'unscored-stop-phase',
        'incomplete': 'descriptive-only',
        'interim_looks': 0,
        'natural_failure': 'score-900-and-continue',
        'outcome_stops': 0,
        'owner_or_invariant_failure': 'unscored-stop-phase',
        'replacements': 0,
        'retries': 0,
    },
}
_PROTOCOL_BYTES = memory.canonical_bytes(PROTOCOL)
_PROTOCOL_SHA256 = memory.sha256(PROTOCOL)


def require(value, message):
    if not value:
        raise ValueError(message)


def validate_protocol(protocol):
    memory._bounded(protocol, MAX_INPUT_BYTES)
    require(memory.canonical_bytes(protocol) == _PROTOCOL_BYTES,
            'Analysis protocol differs from the frozen contract')
    return copy.deepcopy(protocol)


def _row(value):
    if type(value) is not int or not 0 <= value < 48:
        raise ValueError('Invalid family row')
    return value


def _rotate(values, offset):
    values = list(values)
    return values[offset % len(values):] + values[:offset % len(values)]


def condition_order(row):
    return _rotate(CONDITIONS, _row(row))


def case_order(row):
    return _rotate(KINDS, _row(row))


def family_order():
    return [stratum * 16 + index
            for index in range(16)
            for stratum in _rotate(range(3), index)]


def _make_design(split, block):
    families = []
    for row in range(48):
        case = world.make_family_case(split, block, row, 'change')
        assignment = world.family_assignment(row)
        families.append({'family_id': case['family_id'], 'row': row,
                         'cost_stratum': assignment['cost_stratum']})
    owner_order = []
    for row in family_order():
        family_id = families[row]['family_id']
        for kind in case_order(row):
            case_id = f'{family_id}-{kind}'
            owner_order.append([case_id, 'source'])
            owner_order.extend([case_id, condition] for condition in condition_order(row))
    return {'schema': 'memory-family-analysis-design-v3', 'split': split, 'block': block,
        'protocol_sha256': _PROTOCOL_SHA256,
        'family_design_sha256': memory.sha256(world.FAMILY_DESIGN),
        'families': families, 'execution_rows': family_order(),
        'owner_order_sha256': memory.sha256(owner_order), 'family_count': 48}


def build_design(split, block, protocol):
    validate_protocol(protocol)
    memory._enum(split, ('development', 'held-out'))
    if type(block) is not int or not 0 <= block < 2**23:
        raise ValueError('Invalid analysis block')
    if split == 'development' and block != 0:
        raise ValueError('Development analysis is fixed to block zero')
    return _make_design(split, block)


def _validate_design(design, protocol):
    memory._bounded(design, MAX_INPUT_BYTES)
    memory._fields(design, ('schema split block protocol_sha256 family_design_sha256 '
                            'families execution_rows owner_order_sha256 family_count'))
    memory._enum(design['split'], ('development', 'held-out'))
    if type(design['block']) is not int or not 0 <= design['block'] < 2**23:
        raise ValueError('Invalid analysis design block')
    expected = build_design(design['split'], design['block'], protocol)
    require(memory.canonical_bytes(design) == memory.canonical_bytes(expected),
            'Analysis design differs from the generated family contract')
    return expected


def _validate_verification(verification, readout, protocol, design):
    memory._bounded(verification, MAX_INPUT_BYTES)
    memory._fields(verification, ('schema split block registration_sha256 plan_sha256 '
        'readout_sha256 protocol_sha256 design_sha256 checks development_gate held_out_selection'))
    require(verification['schema'] == 'memory-family-analysis-verification-v3',
            'Unknown analysis verification schema')
    require(verification['split'] == design['split'] == readout['split']
            and type(verification['block']) is int
            and verification['block'] == design['block'], 'Analysis split or block binding differs')
    for name in ('registration_sha256', 'plan_sha256', 'readout_sha256',
                 'protocol_sha256', 'design_sha256'):
        memory._digest(verification[name])
    require(verification['plan_sha256'] == readout['plan_sha256'], 'Plan receipt differs')
    require(verification['readout_sha256'] == memory.sha256(readout), 'Readout receipt differs')
    require(verification['protocol_sha256'] == memory.sha256(protocol), 'Protocol receipt differs')
    require(verification['design_sha256'] == memory.sha256(design), 'Design receipt differs')
    require(type(verification['checks']) is dict and set(verification['checks']) == set(CHECKS),
            'Analysis verification checks differ')
    for check in verification['checks'].values():
        memory._fields(check, 'passed sha256')
        require(check['passed'] is True, 'Analysis verification check did not pass')
        memory._digest(check['sha256'])
    if design['split'] == 'development':
        require(verification['development_gate'] is None
                and verification['held_out_selection'] is None,
                'Development input cannot carry held-out receipts')
        return
    gate = verification['development_gate']
    memory._fields(gate, 'passed sha256')
    require(gate['passed'] is True, 'Development gate did not pass')
    memory._digest(gate['sha256'])
    selection = verification['held_out_selection']
    memory._fields(selection, ('schema raw_hex selected_block draw_count redraw_count '
                               'source_sha256 runtime_sha256 publication_sha256'))
    require(selection['schema'] == 'memory-family-held-out-selection-v3',
            'Unknown held-out selection schema')
    raw = selection['raw_hex']
    require(type(raw) is str and len(raw) == 6
            and all(character in '0123456789abcdef' for character in raw),
            'Invalid held-out raw draw')
    require(type(selection['selected_block']) is int
            and selection['selected_block'] == int(raw, 16) & 0x7fffff
            and selection['selected_block'] == design['block'],
            'Held-out draw does not select the registered block')
    require(type(selection['draw_count']) is int and selection['draw_count'] == 1
            and type(selection['redraw_count']) is int and selection['redraw_count'] == 0,
            'Held-out selection permits rerolling')
    for name in ('source_sha256', 'runtime_sha256', 'publication_sha256'):
        memory._digest(selection[name])


def _validate_readout(readout, design):
    memory._bounded(readout, MAX_INPUT_BYTES)
    memory._fields(readout, ('schema plan_sha256 split readout_complete registered_family_count '
        'expected_slots scored_slots missing_slots unscored_slots unmet_prerequisites cells contrasts '
        'primary_references family_independence_verified input_provenance_verified r2_complete '
        'qualification_claims scope'))
    require(readout['schema'] == 'memory-confirmatory-readout-v3', 'Unknown readout schema')
    memory._digest(readout['plan_sha256'])
    require(readout['split'] == design['split'], 'Readout split differs from analysis design')
    require(readout['readout_complete'] is True, 'Analysis requires a complete readout')
    require(type(readout['registered_family_count']) is int
            and readout['registered_family_count'] == 48, 'Analysis requires 48 registered families')
    require(type(readout['expected_slots']) is int and readout['expected_slots'] == 1296
            and type(readout['scored_slots']) is int and readout['scored_slots'] == 1296,
            'Analysis requires the complete 1,296-cell matrix')
    require(readout['missing_slots'] == [] and readout['unscored_slots'] == []
            and readout['unmet_prerequisites'] == [], 'Incomplete readout cannot reach inference')
    require(readout['primary_references'] == list(REFERENCES), 'Primary references differ')
    require(readout['family_independence_verified'] is False
            and readout['input_provenance_verified'] is False
            and readout['r2_complete'] is False and readout['qualification_claims'] == [],
            'Descriptive readout overstates qualification')
    memory._list(readout['cells'], 1297)

    families = {row['family_id']: row for row in design['families']}
    expected, cells, run_ids = {}, {}, set()
    for family in design['families']:
        row = family['row']
        for kind in KINDS:
            case = world.make_family_case(design['split'], design['block'], row, kind)
            require(case['family_id'] == family['family_id'], 'Generated family identity differs')
            for condition in CONDITIONS:
                expected[(case['case_id'], condition)] = (family['family_id'], kind)
    for cell in readout['cells']:
        memory._fields(cell, ('family_id case_id kind condition run_id goal continuation_ticks '
            'path_length outcome trace_digest invariant capped_ticks'))
        for name in ('family_id', 'case_id', 'run_id'):
            memory._id(cell[name])
        memory._enum(cell['kind'], KINDS)
        memory._enum(cell['condition'], CONDITIONS)
        require(cell['run_id'] not in run_ids, 'Run ID is reused across analysis cells')
        run_ids.add(cell['run_id'])
        slot = (cell['case_id'], cell['condition'])
        require(slot in expected and slot not in cells, 'Unregistered or duplicate analysis cell')
        require(expected[slot] == (cell['family_id'], cell['kind']),
                'Cell family or case-kind binding differs')
        require(cell['family_id'] in families, 'Cell family is outside the design')
        require(type(cell['goal']) is bool
                and type(cell['continuation_ticks']) is int
                and 0 <= cell['continuation_ticks'] <= 900,
                'Invalid analysis score')
        require(type(cell['capped_ticks']) is int
                and cell['capped_ticks'] == (cell['continuation_ticks'] if cell['goal'] else 900),
                'Capped score differs from the registered rule')
        require(type(cell['path_length']) in (int, float)
                and math.isfinite(cell['path_length']) and cell['path_length'] >= 0,
                'Invalid path length')
        require(type(cell['outcome']) is dict, 'Invalid terminal outcome')
        memory._digest(cell['trace_digest']); memory._digest(cell['invariant'])
        cells[slot] = cell
    require(set(cells) == set(expected), 'Analysis cells do not cover the registered design')

    pair_equality = ('trace_digest', 'goal', 'continuation_ticks',
                     'path_length', 'outcome')
    for case_id in {case_id for case_id, _ in expected}:
        rows = [cells[case_id, condition] for condition in CONDITIONS]
        require(len({row['invariant'] for row in rows}) == 1,
                'Paired invariant differs across analysis cells')
        own, sham = cells[case_id, 'own'], cells[case_id, 'sham']
        require(all(own[name] == sham[name] for name in pair_equality),
                'Own/sham analysis cells differ')

    equality = ('trace_digest', 'goal', 'continuation_ticks', 'path_length',
                'capped_ticks', 'outcome')
    for family in design['families']:
        case_id = f'{family["family_id"]}-no-event'
        projections = [{name: cells[case_id, condition][name] for name in equality}
                       for condition in CONDITIONS]
        require(all(memory.canonical_bytes(value) == memory.canonical_bytes(projections[0])
                    for value in projections[1:]),
                'No-event conditions differ from the exact invariant')

    contrasts, values = {}, {}
    for reference in CONDITIONS[1:]:
        family_costs, family_goals = [], []
        by_kind = {kind: [] for kind in KINDS}
        for family in design['families']:
            pairs = []
            for kind in KINDS:
                case_id = f'{family["family_id"]}-{kind}'
                own, other = cells[case_id, 'own'], cells[case_id, reference]
                pair = (own['capped_ticks'] - other['capped_ticks'],
                        int(own['goal']) - int(other['goal']))
                pairs.append(pair); by_kind[kind].append(pair)
            family_costs.append(fmean(pair[0] for pair in pairs))
            family_goals.append(fmean(pair[1] for pair in pairs))
        contrasts[reference] = {
            'family_ids': [family['family_id'] for family in design['families']],
            'family_cost_differences': family_costs,
            'family_goal_differences': family_goals,
            'mean_cost_difference': fmean(family_costs),
            'mean_goal_difference': fmean(family_goals),
            'by_kind': {kind: {
                'mean_cost_difference': fmean(pair[0] for pair in pairs),
                'mean_goal_difference': fmean(pair[1] for pair in pairs),
            } for kind, pairs in by_kind.items()},
        }
        if reference in REFERENCES:
            values[reference] = {'primary': family_costs,
                **{kind: [pair[0] for pair in by_kind[kind]] for kind in KINDS}}
    require(memory.canonical_bytes(readout['contrasts']) == memory.canonical_bytes(contrasts),
            'Readout contrasts differ from their cells')
    return cells, values


def _blocked_interval(values, design, confidence, *, one_sided=False):
    groups = {name: [] for name in STRATA}
    for family, value in zip(design['families'], values, strict=True):
        groups[family['cost_stratum']].append(value)
    rows, components = [], []
    for name in STRATA:
        require(len(groups[name]) == 16, 'Cost stratum does not contain 16 families')
        mean, sample_variance = fmean(groups[name]), variance(groups[name])
        require(math.isfinite(mean) and math.isfinite(sample_variance),
                'Nonfinite blocked interval input')
        rows.append({'name': name, 'count': 16, 'mean': mean, 'variance': sample_variance})
        components.append(sample_variance / (9 * 16))
    estimate = fmean(row['mean'] for row in rows)
    standard_error = math.sqrt(sum(components))
    base = {'confidence': confidence, 'estimate': estimate,
            'standard_error': standard_error, 'strata': rows}
    if not math.isfinite(standard_error) or standard_error == 0:
        return {**base, 'degrees_of_freedom': None, 'critical': None,
                'half_width': None, 'lower': None, 'upper': None,
                'status': 'zero-variance' if standard_error == 0 else 'nonfinite'}
    denominator = sum(component**2 / 15 for component in components)
    degrees = sum(components)**2 / denominator
    probability = confidence if one_sided else 1 - (1 - confidence) / 2
    critical = float(t.ppf(probability, degrees))
    half_width = critical * standard_error
    require(all(math.isfinite(value) for value in
                (degrees, critical, half_width, estimate)), 'Nonfinite blocked interval')
    return {**base, 'degrees_of_freedom': degrees, 'critical': critical,
            'half_width': half_width,
            'lower': None if one_sided else estimate - half_width,
            'upper': estimate + half_width, 'status': 'ok'}


def _held_out_disposition(primary, guards):
    if guards.get('variance_unresolved') or any(
            row.get('status', 'ok') != 'ok' for row in primary.values()):
        return 'variance-unresolved', 'variance-unresolved'
    if any(row['lower'] > 45 for row in primary.values()):
        primary_disposition = 'primary-harm'
    elif all(row['upper'] < -90 for row in primary.values()):
        primary_disposition = 'benefit'
    elif all(row['lower'] > -90 and row['upper'] < 45 for row in primary.values()):
        primary_disposition = 'supported-null'
    else:
        primary_disposition = 'inconclusive'
    if primary_disposition == 'primary-harm':
        final = primary_disposition
    elif guards['observed_success_harm']:
        final = 'observed-guardrail-harm'
    elif primary_disposition in ('benefit', 'supported-null') and not guards['passed']:
        final = 'guardrail-not-established'
    else:
        final = primary_disposition
    return primary_disposition, final


def analyze(readout, protocol, design, verification):
    protocol = validate_protocol(protocol)
    design = _validate_design(design, protocol)
    cells, values = _validate_readout(readout, design)
    _validate_verification(verification, readout, protocol, design)

    primary = {reference: _blocked_interval(
        values[reference]['primary'], design,
        protocol['inference']['primary_two_sided_confidence'])
        for reference in REFERENCES}
    guardrails = {}
    for reference in REFERENCES:
        cost = _blocked_interval(values[reference]['null'], design,
            protocol['guardrails']['cost']['one_sided_confidence'], one_sided=True)
        cost['passed'] = (cost['status'] == 'ok'
                          and cost['upper'] < protocol['guardrails']['cost']['upper_margin_ticks'])
        events = 0
        for family in design['families']:
            case_id = f'{family["family_id"]}-null'
            events += int(not cells[case_id, 'own']['goal']
                          and cells[case_id, reference]['goal'])
        upper = -math.log(.05) / 48 if events == 0 else None
        success = {'confidence': .95, 'events': events, 'families': 48,
            'upper_bound': upper, 'margin': .0625,
            'passed': upper is not None and upper < .0625,
            'method': 'conservative-zero-event-exponential-bound-v1'}
        guardrails[reference] = {'null': {'cost': cost, 'success_harm': success},
            'no-event': {'passed': True, 'families': 48, 'conditions': 9,
                         'method': 'exact-all-nine-trace-outcome-equality-v1'}}

    endpoints = {f'{reference}:primary': primary[reference] for reference in REFERENCES}
    endpoints.update({f'{reference}:null': guardrails[reference]['null']['cost']
                      for reference in REFERENCES})
    precision_passed = all(row['status'] == 'ok'
                           and row['half_width'] <= protocol['inference']['precision_half_width_ticks']
                           for row in endpoints.values())
    guard_summary = {
        'passed': all(guardrails[reference]['null']['cost']['passed']
                      and guardrails[reference]['null']['success_harm']['passed']
                      and guardrails[reference]['no-event']['passed']
                      for reference in REFERENCES),
        'observed_success_harm': any(
            guardrails[reference]['null']['success_harm']['events'] > 0
            for reference in REFERENCES),
        'variance_unresolved': any(row['status'] != 'ok' for row in endpoints.values()),
    }
    inference_ready = not guard_summary['variance_unresolved']
    if design['split'] == 'development':
        primary_disposition, scientific_disposition = 'development-no-claim', 'development-no-claim'
        admissible = precision_passed
    else:
        primary_disposition, scientific_disposition = _held_out_disposition(primary, guard_summary)
        admissible = None
    return {'schema': 'memory-family-analysis-result-v3', 'split': design['split'],
        'block': design['block'], 'family_count': 48,
        'protocol_sha256': memory.sha256(protocol), 'design_sha256': memory.sha256(design),
        'readout_sha256': memory.sha256(readout),
        'verification_sha256': memory.sha256(verification),
        'registration_sha256': verification['registration_sha256'],
        'primary': primary, 'guardrails': guardrails,
        'guardrail_summary': guard_summary,
        'primary_disposition': primary_disposition,
        'scientific_disposition': scientific_disposition,
        'inference_ready': inference_ready,
        'precision_screen': {'passed': precision_passed, 'endpoints': endpoints,
                             'maximum_half_width_ticks': 45,
                             'no_event_invariant': True},
        'held_out_registration_admissible': admissible,
        'model_assumption': (
            'approximate normality of bounded family contrasts and independence across '
            'the 48 generated families within fixed cost strata, conditional on the '
            'registered generator and balanced assignment; IDs and hashes prove neither '
            'these assumptions nor generalization beyond the registered catalog'),
        'receipt_bindings_validated': True, 'receipt_truth_verified': False,
        'study_complete': False, 'r2_complete': False, 'qualification_claims': [],
        'scope': ('Model-conditional registered-catalog analysis only; receipt contents are '
                  'not independently observed truth, generalization is unestablished, and '
                  'no simulation release gate is closed')}


def _load(path):
    with path.open('rb') as stream:
        payload = stream.read(MAX_INPUT_BYTES + 1)
    require(len(payload) <= MAX_INPUT_BYTES, 'Input exceeds 32 MiB')

    def reject(value):
        raise ValueError('Nonfinite JSON: ' + value)

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'Duplicate JSON key: ' + key)
            result[key] = value
        return result

    data = json.loads(payload, parse_constant=reject, object_pairs_hook=unique_object)
    require(memory.canonical_bytes(data) == payload, 'Input must be canonical JSON')
    memory._fields(data, 'readout protocol design verification')
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    args = parser.parse_args(argv)
    sys.stdout.buffer.write(memory.canonical_bytes(analyze(**_load(args.input))) + b'\n')


if __name__ == '__main__':
    main()
