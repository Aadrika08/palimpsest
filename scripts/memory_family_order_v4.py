"""Pure static check of a prospective memory-condition ordering candidate.

No case construction, model/native import, solver, file access or execution grant.
Callers independently freeze the source, exact assignment roster and candidate
hashes. Existing registered schedules and scientific profiles are never modified.
"""
from __future__ import annotations

from collections import Counter
import hashlib
import json
import math
import re

PUBLIC_FACTORS = ('fact_first_side', 'subject_first_side', 'route_first_side', 'schedule_index')
HIDDEN_FACTORS = ('regimebit', 'relation_side')
OTHER_CONDITIONS = ('swapped', 'sham', 'no-U', 'hand-authored',
                    'history-independent', 'traversal', 'retrieval', 'oracle')
STRATA = ('south', 'north', 'tie')
ASSIGNMENT_FIELDS = {'row', 'cost_stratum', 'regime', 'relation_side', *PUBLIC_FACTORS}
CANDIDATE_FIELDS = {'scope', 'source_sha256', 'solver_status', 'message', 'elapsed_seconds',
                    'scientific_admission', 'row_shifts', 'integer_constraints_verified',
                    'hidden_factors_per_position', 'public_binary_factor_counts_per_position',
                    'condition_position_count', 'stratum_condition_position_count', 'limitations'}


def _fields(value, expected, label):
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f'{label}: missing or unrecognized fields')


def _integer(value, low, high, label):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{label}: expected bounded integer, never boolean')
    return value


def _digest(value, label):
    if type(value) is not str or re.fullmatch(r'[0-9a-f]{64}', value) is None:
        raise ValueError(f'{label}: invalid SHA-256')
    return value


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _identity(value, expected, label):
    actual = hashlib.sha256(_canonical(value)).hexdigest()
    if actual != _digest(expected, f'expected {label}'):
        raise ValueError(f'{label} identity differs from externally registered digest')
    return actual


def _roster(assignments, expected_design_sha256):
    if type(assignments) is not list or len(assignments) != 48:
        raise ValueError('Assignment roster must contain exactly 48 rows')
    rows = []
    for index, assignment in enumerate(assignments):
        _fields(assignment, ASSIGNMENT_FIELDS, 'Assignment')
        if _integer(assignment['row'], 0, 47, 'row') != index:
            raise ValueError('Assignment rows must be canonical, unique and complete 0..47')
        stratum = assignment['cost_stratum']
        if type(stratum) is not str or stratum not in STRATA:
            raise ValueError('Assignment has an unregistered cost stratum')
        regime = assignment['regime']
        if type(regime) is not str or regime not in ('local_cue', 'paired_cue'):
            raise ValueError('Assignment regime is not a registered binary relation')
        factors = {name: _integer(assignment[name], 0, 1, name) for name in PUBLIC_FACTORS}
        factors['relation_side'] = _integer(assignment['relation_side'], 0, 1, 'relation_side')
        factors['regimebit'] = int(regime == 'paired_cue')
        rows.append((stratum, factors))
    if Counter(stratum for stratum, _ in rows) != Counter({name: 16 for name in STRATA}):
        raise ValueError('Cost strata must contain exactly sixteen rows each')
    return rows, _identity(assignments, expected_design_sha256, 'design roster')


def _candidate(candidate, expected_source_sha256, expected_candidate_sha256):
    _fields(candidate, CANDIDATE_FIELDS, 'Ordering candidate')
    if (candidate['scope'] != 'Outcome-blind prospective candidate, not study admission'
            or type(candidate['scientific_admission']) is not bool
            or candidate['scientific_admission'] is not False):
        raise ValueError('Candidate scope must deny scientific admission')
    if (_digest(candidate['source_sha256'], 'candidate source')
            != _digest(expected_source_sha256, 'expected source')):
        raise ValueError('Candidate source differs from independently registered source')
    shifts = candidate['row_shifts']
    if type(shifts) is not list or len(shifts) != 48:
        raise ValueError('Exactly 48 row shifts required')
    shifts = tuple(_integer(shift, 0, 7, 'row shift') for shift in shifts)
    _integer(candidate['solver_status'], -128, 128, 'solver status')
    if (type(candidate['message']) is not str or len(candidate['message']) > 1024
            or type(candidate['elapsed_seconds']) not in (int, float)
            or not 0 <= candidate['elapsed_seconds'] <= 86400
            or not math.isfinite(candidate['elapsed_seconds'])
            or type(candidate['integer_constraints_verified']) is not bool):
        raise ValueError('Malformed solver provenance; it is not checking authority')
    if (candidate['hidden_factors_per_position'] != '3/3 each'
            or type(candidate['public_binary_factor_counts_per_position']) is not list
            or candidate['public_binary_factor_counts_per_position'] != [2, 4]
            or any(type(value) is not int for value in candidate['public_binary_factor_counts_per_position'])
            or type(candidate['condition_position_count']) is not int
            or candidate['condition_position_count'] != 6
            or type(candidate['stratum_condition_position_count']) is not int
            or candidate['stratum_condition_position_count'] != 2):
        raise ValueError('Candidate declared position bounds differ from static contract')
    limitations = candidate['limitations']
    if (type(limitations) is not list or not 1 <= len(limitations) <= 16
            or any(type(item) is not str or not item or len(item) > 1024 for item in limitations)):
        raise ValueError('Candidate limitations are missing or unbounded')
    return shifts, _identity(candidate, expected_candidate_sha256, 'candidate')


def validate_order_candidate(candidate, assignments, *, expected_source_sha256,
                             expected_design_sha256, expected_candidate_sha256):
    """Recompute the bounded-imbalance design without trusting solver flags.

    Rows are already registered family assignments, not outcomes or generated
    cases. The eight positions below are relative to the eight non-own
    conditions; complete process order prepends source and own. Every positive
    result remains STATIC_ONLY and grants no study, runtime or protected access.
    """
    rows, design_digest = _roster(assignments, expected_design_sha256)
    shifts, candidate_digest = _candidate(candidate, expected_source_sha256,
                                           expected_candidate_sha256)
    shift_counts = [shifts.count(shift) for shift in range(8)]
    if shift_counts != [6] * 8:
        raise ValueError('Every shift must occur six times overall')
    stratum_shifts = {stratum: [sum(rows[row][0] == stratum and shifts[row] == shift
                                   for row in range(48)) for shift in range(8)]
                       for stratum in STRATA}
    if any(counts != [2] * 8 for counts in stratum_shifts.values()):
        raise ValueError('Every shift must occur twice in each cost stratum')
    factors = (*PUBLIC_FACTORS, *HIDDEN_FACTORS)
    position_counts = {condition: [0] * 8 for condition in OTHER_CONDITIONS}
    stratum_positions = {stratum: {condition: [0] * 8 for condition in OTHER_CONDITIONS}
                         for stratum in STRATA}
    factor_ones = {condition: {factor: [0] * 8 for factor in factors}
                   for condition in OTHER_CONDITIONS}
    row_orders = []
    for row, ((stratum, values), shift) in enumerate(zip(rows, shifts)):
        order = OTHER_CONDITIONS[shift:] + OTHER_CONDITIONS[:shift]
        row_orders.append({'row': row, 'cost_stratum': stratum, 'shift': shift,
                           'order': ['source', 'own', *order]})
        for position, condition in enumerate(order):
            position_counts[condition][position] += 1
            stratum_positions[stratum][condition][position] += 1
            for factor in factors:
                factor_ones[condition][factor][position] += values[factor]
    if (any(counts != [6] * 8 for counts in position_counts.values())
            or any(counts != [2] * 8 for positions in stratum_positions.values()
                   for counts in positions.values())):
        raise ValueError('Condition/position counts are not balanced')
    if any(counts[factor] != [3] * 8 for counts in factor_ones.values()
           for factor in HIDDEN_FACTORS):
        raise ValueError('hidden factor/condition/position counts must be exactly three ones')
    public_counts = [value for counts in factor_ones.values() for factor in PUBLIC_FACTORS
                     for value in counts[factor]]
    if any(not 2 <= value <= 4 for value in public_counts):
        raise ValueError('Public factor/condition/position counts exceed bounded imbalance')
    return {'schema': 'memory-v4-static-order-check-v1',
            'scope': 'STATIC_ONLY', 'scientific_admission': False,
            'execution_authorized': False, 'source_sha256': expected_source_sha256,
            'design_sha256': design_digest, 'candidate_sha256': candidate_digest,
            'family_count': 48, 'kinds_per_family': 3, 'condition_count': 9,
            'source_count_per_case': 1, 'shift_counts': shift_counts,
            'stratum_shift_counts': stratum_shifts,
            'condition_position_counts': position_counts,
            'stratum_condition_position_counts': stratum_positions,
            'factor_ones_by_condition_position': factor_ones,
            'public_factor_one_count_range': [min(public_counts), max(public_counts)],
            'hidden_factor_position_balance': True,
            'exact_public_factor_balance': all(value == 3 for value in public_counts),
            'own_position_counterbalanced': False,
            'higher_order_balance_verified': False,
            'wall_time_causal_claim_authorized': False,
            'row_orders': row_orders}
