"""Bounded exact numerical enclosure for fixed paired loss contrasts.

This module verifies arithmetic and completeness, never sampling assumptions,
proof-receipt authenticity, a Lean theorem, or a simulator experiment.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import re

MAX_FAMILIES = 4096
MAX_CONTRASTS = 64
MAX_INPUT_BITS = 128
MAX_SUM_BITS = 4096
MAX_TAYLOR_BITS = 4096
MAX_TAYLOR_TERMS = 256
ID_PATTERN = re.compile(r'[A-Za-z0-9_.:-]{1,128}\Z')
HASH_PATTERN = re.compile(r'[0-9a-f]{64}\Z')
SPEC_FIELDS = {'schema', 'protocol_sha256', 'family_ids', 'family_count',
               'contrast_ids', 'alpha', 'fixed_lambda', 'upper_log_budget',
               'log_evidence'}
ROW_FIELDS = {'family_id', 'contrast_id', 'status', 'loss_difference'}


def _fields(value, expected, label):
    if type(value) is not dict or set(value) != expected:
        raise ValueError(f'{label}: missing or unrecognized fields')


def _hash(value, label):
    if type(value) is not str or HASH_PATTERN.fullmatch(value) is None:
        raise ValueError(f'{label}: expected lowercase SHA-256 identity')
    return value


def _integer(value, label):
    if type(value) is not int:
        raise ValueError(f'{label}: expected an integer, never boolean or float')
    if value.bit_length() > MAX_INPUT_BITS:
        raise ValueError(f'{label}: integer operand exceeds bounded bits')
    return value


def _fraction(value, label):
    _fields(value, {'numerator', 'denominator'}, label)
    numerator = _integer(value['numerator'], label)
    denominator = _integer(value['denominator'], label)
    if denominator <= 0:
        raise ValueError(f'{label}: denominator must be positive')
    return Fraction(numerator, denominator)


def _ids(values, limit, label):
    if type(values) is not list or not 0 < len(values) <= limit:
        raise ValueError(f'{label}: empty or excessive identity count')
    if any(type(value) is not str or ID_PATTERN.fullmatch(value) is None
           for value in values):
        raise ValueError(f'{label}: invalid identity')
    if len(values) != len(set(values)):
        raise ValueError(f'{label}: duplicate identity')
    return tuple(values)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=True, allow_nan=False).encode('ascii')


def _bounded_fraction(value, limit, label):
    if max(value.numerator.bit_length(), value.denominator.bit_length()) > limit:
        raise ValueError(f'{label}: exact rational work exceeds bounded bits')
    return value


def _rational(value):
    return {'numerator': value.numerator, 'denominator': value.denominator}


@dataclass(frozen=True)
class ImmutableAuditSpec:
    """Validated immutable parameters, bound to an externally supplied digest."""
    protocol_sha256: str
    spec_sha256: str
    family_ids: tuple[str, ...]
    contrast_ids: tuple[str, ...]
    alpha: Fraction
    fixed_lambda: Fraction
    upper_log_budget: Fraction
    taylor_terms: int
    proof_receipt_sha256: str


def parse_spec(raw, *, expected_protocol_sha256, expected_spec_sha256):
    """Validate schema, resource limits and independent expected identities."""
    _fields(raw, SPEC_FIELDS, 'immutableAuditSpec')
    if raw['schema'] != 'immutableAuditSpec-v1':
        raise ValueError('immutableAuditSpec: unsupported schema')
    protocol = _hash(raw['protocol_sha256'], 'protocol')
    if protocol != _hash(expected_protocol_sha256, 'expected protocol'):
        raise ValueError('protocol identity differs from expected protocol')
    families = _ids(raw['family_ids'], MAX_FAMILIES, 'family identities')
    count = _integer(raw['family_count'], 'family count')
    if count <= 0 or count != len(families):
        raise ValueError('family count must match positive complete family roster')
    contrasts = _ids(raw['contrast_ids'], MAX_CONTRASTS, 'contrast identities')
    alpha = _fraction(raw['alpha'], 'alpha')
    fixed_lambda = _fraction(raw['fixed_lambda'], 'fixed lambda')
    budget = _fraction(raw['upper_log_budget'], 'upper log budget')
    if not 0 < alpha < 1:
        raise ValueError('alpha must be strictly between zero and one')
    if not 0 < fixed_lambda <= 1:
        raise ValueError('fixed lambda must lie in the bounded interval (0,1]')
    if not 0 < budget <= 64:
        raise ValueError('upper log budget must lie in the bounded interval (0,64]')
    evidence = raw['log_evidence']
    _fields(evidence, {'method', 'terms', 'proof_receipt_sha256'}, 'log evidence')
    if evidence['method'] != 'exp-taylor-lower-v1':
        raise ValueError('log evidence: unsupported checking method')
    terms = _integer(evidence['terms'], 'Taylor terms')
    if not 1 <= terms <= MAX_TAYLOR_TERMS:
        raise ValueError('Taylor terms exceed bounded range 1..256')
    receipt = _hash(evidence['proof_receipt_sha256'], 'proof receipt')
    actual = hashlib.sha256(_canonical(raw)).hexdigest()
    if actual != _hash(expected_spec_sha256, 'expected spec'):
        raise ValueError('immutableAuditSpec identity differs from expected spec')
    return ImmutableAuditSpec(protocol, actual, families, contrasts, alpha,
                              fixed_lambda, budget, terms, receipt)


def check_log_budget(spec):
    """Check a conservative log upper bound using exact finite Taylor terms.

    For q>0, sum(q**k/k!, k=0..terms-1) < exp(q). Requiring this finite
    rational sum > K/alpha establishes q > log(K/alpha) without evaluating
    exp or log in floating point. An inconclusive lower sum refuses.
    """
    term = Fraction(1)
    lower = Fraction(1)
    for k in range(1, spec.taylor_terms):
        term = _bounded_fraction(term * spec.upper_log_budget / k,
                                 MAX_TAYLOR_BITS, 'Taylor term')
        lower = _bounded_fraction(lower + term, MAX_TAYLOR_BITS, 'Taylor sum')
    threshold = Fraction(len(spec.contrast_ids), 1) / spec.alpha
    if lower <= threshold:
        raise ValueError('Taylor evidence does not establish the upper log budget')
    return lower


def check_audit(raw_spec, rows, *, expected_protocol_sha256, expected_spec_sha256):
    """Return exact upper endpoints for a complete fixed family/contrast grid.

    Each family supplies one completed paired-loss difference per fixed contrast.
    Refused, failed, missing, extra and duplicate units invalidate the grid.
    ``numerical_improvement`` denotes an endpoint below zero only. Statistical
    eligibility and theorem/proof receipts remain unverified in every result.
    """
    spec = parse_spec(raw_spec, expected_protocol_sha256=expected_protocol_sha256,
                      expected_spec_sha256=expected_spec_sha256)
    taylor_lower = check_log_budget(spec)
    expected_count = len(spec.family_ids) * len(spec.contrast_ids)
    if type(rows) is not list or len(rows) != expected_count:
        raise ValueError('Missing or extra rows: complete family/contrast count required')
    family_set, contrast_set = set(spec.family_ids), set(spec.contrast_ids)
    seen = set()
    totals = {contrast: Fraction(0) for contrast in spec.contrast_ids}
    row_digest = hashlib.sha256()
    for row in rows:
        _fields(row, ROW_FIELDS, 'observation')
        family, contrast = row['family_id'], row['contrast_id']
        if (type(family) is not str or type(contrast) is not str
                or family not in family_set or contrast not in contrast_set):
            raise ValueError('Observation identity differs from registered family/contrast')
        key = family, contrast
        if key in seen:
            raise ValueError('duplicate family/contrast observation')
        seen.add(key)
        if type(row['status']) is not str or row['status'] != 'completed':
            raise ValueError('Only completed observations are admissible; other status refuses evaluation')
        loss = _fraction(row['loss_difference'], 'loss difference')
        if not -1 <= loss <= 1:
            raise ValueError('Paired loss difference lies outside closed range [-1,1]')
        totals[contrast] = _bounded_fraction(totals[contrast] + loss,
                                              MAX_SUM_BITS, 'Observation sum')
        row_digest.update(_canonical(row) + b'\n')
    n = len(spec.family_ids)
    results = []
    for contrast in spec.contrast_ids:
        mean = totals[contrast] / n
        upper = _bounded_fraction(mean + spec.upper_log_budget / (spec.fixed_lambda * n)
                                  + spec.fixed_lambda / 2, MAX_TAYLOR_BITS,
                                  'Upper endpoint')
        results.append({'contrast_id': contrast, 'family_count': n,
                        'mean': _rational(mean), 'upper_endpoint': _rational(upper),
                        'numerical_improvement': upper < 0})
    return {'schema': 'change-audit-numerical-enclosure-v1',
            'protocol_sha256': spec.protocol_sha256,
            'spec_sha256': spec.spec_sha256,
            'observations_sha256': row_digest.hexdigest(),
            'contrasts': results,
            'log_evidence': {'method': 'exp-taylor-lower-v1',
                             'terms': spec.taylor_terms,
                             'exp_lower': _rational(taylor_lower),
                             'threshold': _rational(Fraction(len(spec.contrast_ids), 1) / spec.alpha),
                             'proof_receipt_sha256': spec.proof_receipt_sha256,
                             'numerical_log_enclosure_verified': True},
            'sampling_eligibility_verified': False,
            'theorem_receipt_verified': False,
            'certified_improvement': False}
