"""Pure generation of closed Lean numerical witnesses; never compile or certify.

Only validated rational literals and hexadecimal digest strings enter Lean text.
User IDs are retained in metadata and never become Lean names or code.
"""
from __future__ import annotations

import copy
from fractions import Fraction
import hashlib
import json

from paper.studies.change_audit_v1.check import check_audit, parse_spec

MAX_EXPORT_FAMILIES = 128
MAX_EXPORT_CONTRASTS = 8
MAX_EXPORT_TERMS = 32
MAX_CERTIFICATE_BYTES = 256 * 1024


def _fraction(value):
    # Invoked only after the existing checker validates exact types and bounds.
    return Fraction(value['numerator'], value['denominator'])


def _lean_q(value):
    return f'(({value.numerator} : ℚ) / {value.denominator})'


def _lean_r(value):
    return f'({_lean_q(value)} : ℝ)'


def _endpoint(index):
    return (f'(mean_{index} : ℝ) + ChangeAudit.conservativeRadius '
            '(upperLog : ℝ) (scale : ℝ) familyCount')


def emit_lean_certificate(raw_spec, rows, *, expected_protocol_sha256,
                          expected_spec_sha256):
    """Return bounded closed source plus explicitly unverified metadata.

    This performs no I/O or subprocess invocation. The generated text has not
    been accepted by Lean. Neither checking arithmetic nor compiling a generated
    witness establishes sampling eligibility or theorem applicability.
    """
    raw_spec, rows = copy.deepcopy((raw_spec, rows))
    result = check_audit(raw_spec, rows, expected_protocol_sha256=expected_protocol_sha256,
                         expected_spec_sha256=expected_spec_sha256)
    spec = parse_spec(raw_spec, expected_protocol_sha256=expected_protocol_sha256,
                      expected_spec_sha256=expected_spec_sha256)
    if (len(spec.family_ids) > MAX_EXPORT_FAMILIES
            or len(spec.contrast_ids) > MAX_EXPORT_CONTRASTS
            or spec.taylor_terms > MAX_EXPORT_TERMS):
        raise ValueError('Code generation export limits exceeded: 128 families, 8 contrasts, 32 terms')
    namespace = f'ChangeAudit.Generated.Certificate_{spec.spec_sha256}_{result["observations_sha256"]}'
    lines = [
        'import ChangeAudit.Numerical',
        '',
        '-- Closed numerical witness only; no sampling or runtime theorem application.',
        'noncomputable section',
        f'namespace {namespace}',
        '',
        f'def protocolSha256 : String := "{spec.protocol_sha256}"',
        f'def specSha256 : String := "{spec.spec_sha256}"',
        f'def observationsSha256 : String := "{result["observations_sha256"]}"',
        f'def referencedProofReceiptSha256 : String := "{spec.proof_receipt_sha256}"',
        f'def familyCount : ℕ := {len(spec.family_ids)}',
        f'def contrastCount : ℕ := {len(spec.contrast_ids)}',
        f'def taylorTerms : ℕ := {spec.taylor_terms}',
        f'def alpha : ℚ := {_lean_q(spec.alpha)}',
        f'def upperLog : ℚ := {_lean_q(spec.upper_log_budget)}',
        f'def scale : ℚ := {_lean_q(spec.fixed_lambda)}',
        '',
        'theorem log_budget_enclosure :',
        '    Real.log (1 / ((alpha : ℝ) / (contrastCount : ℝ))) ≤ (upperLog : ℝ) := by',
        '  exact ChangeAudit.rational_family_log_enclosure contrastCount alpha upperLog taylorTerms',
        '    (by norm_num [contrastCount])',
        '    (by norm_num [alpha])',
        '    (by norm_num [upperLog])',
        '    (by norm_num [contrastCount, alpha, upperLog, taylorTerms,',
        '      Finset.sum_range_succ, Nat.factorial])',
        '',
    ]
    lookup = {(row['family_id'], row['contrast_id']): _fraction(row['loss_difference'])
              for row in rows}
    for index, (contrast, checked) in enumerate(zip(spec.contrast_ids, result['contrasts'])):
        values = [lookup[(family, contrast)] for family in spec.family_ids]
        mean = _fraction(checked['mean'])
        upper = _fraction(checked['upper_endpoint'])
        lines += [
            f'def losses_{index} : List ℚ := [' + ', '.join(_lean_q(value) for value in values) + ']',
            f'def mean_{index} : ℚ := losses_{index}.sum / (familyCount : ℚ)',
            '',
            f'theorem losses_{index}_count : losses_{index}.length = familyCount := by',
            f'  norm_num [losses_{index}, familyCount]',
            '',
            f'theorem mean_{index}_exact : mean_{index} = {_lean_q(mean)} := by',
            f'  norm_num [mean_{index}, losses_{index}, familyCount]',
            '',
            f'theorem upper_{index}_exact :',
            f'    {_endpoint(index)} = {_lean_r(upper)} := by',
            f'  norm_num [mean_{index}, losses_{index}, familyCount, upperLog, scale,',
            '    ChangeAudit.conservativeRadius]',
            '',
        ]
        if checked['numerical_improvement']:
            lines += [f'theorem upper_{index}_strict_negative : {_endpoint(index)} < 0 := by',
                      f'  rw [upper_{index}_exact]', '  norm_num', '']
        else:
            lines += [f'theorem upper_{index}_nonnegative : 0 ≤ {_endpoint(index)} := by',
                      f'  rw [upper_{index}_exact]', '  norm_num', '']
    lines += [f'end {namespace}', '']
    source = '\n'.join(lines)
    metadata = {
        'schema': 'change-audit-generated-numerical-witness-v1',
        'source_status': 'generated_uncompiled_numerical_witness',
        'protocol_sha256': spec.protocol_sha256,
        'spec_sha256': spec.spec_sha256,
        'observations_sha256': result['observations_sha256'],
        'lean_source_sha256': hashlib.sha256(source.encode('utf-8')).hexdigest(),
        'family_ids': list(spec.family_ids),
        'contrast_ids': list(spec.contrast_ids),
        'row_encoding': 'exact rational values reduced and ordered by registered family within each contrast',
        'proof_receipt_reference_sha256': spec.proof_receipt_sha256,
        'numerical_result': result,
        'sampling_eligibility_verified': False,
        'theorem_application_verified': False,
        'theorem_receipt_verified': False,
        'certified_improvement': False,
        'source_compiled': False,
        'limits': {'families': MAX_EXPORT_FAMILIES, 'contrasts': MAX_EXPORT_CONTRASTS,
                   'taylor_terms': MAX_EXPORT_TERMS, 'total_certificate_bytes': MAX_CERTIFICATE_BYTES},
    }
    artifact = {'lean_source': source, 'metadata': metadata}
    serialized = json.dumps(artifact, sort_keys=True, separators=(',', ':'),
                            ensure_ascii=True, allow_nan=False).encode('ascii')
    if len(serialized) > MAX_CERTIFICATE_BYTES:
        raise ValueError('Generated certificate exceeds bounded 256 KiB serialized size in bytes')
    return artifact
