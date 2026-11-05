"""Exact arithmetic and refusal boundaries; never execute a simulator."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

CHECK_PATH = Path(__file__).parents[1] / 'check.py'

def load_checker():
    if not CHECK_PATH.exists():
        return None
    spec = importlib.util.spec_from_file_location('change_audit_v1_check', CHECK_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

checker = load_checker()

def rat(n, d=1):
    return {'numerator': n, 'denominator': d}

def digest(spec):
    return hashlib.sha256(json.dumps(spec, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def fixture(loss=-1):
    spec = {
        'schema': 'immutableAuditSpec-v1',
        'protocol_sha256': 'a' * 64,
        'family_ids': [f'family-{i}' for i in range(16)],
        'family_count': 16,
        'contrast_ids': ['candidate-a', 'candidate-b'],
        'alpha': rat(1, 10),
        'fixed_lambda': rat(1, 2),
        'upper_log_budget': rat(4),
        'log_evidence': {'method': 'exp-taylor-lower-v1', 'terms': 16,
                         'proof_receipt_sha256': 'b' * 64},
    }
    rows = [{'family_id': family, 'contrast_id': contrast, 'status': 'completed',
             'loss_difference': rat(loss)}
            for family in spec['family_ids'] for contrast in spec['contrast_ids']]
    return spec, rows

class AuditChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(checker, 'Exact rational numerical audit checker is not implemented')

    def run_check(self, spec, rows, **kwargs):
        return checker.check_audit(spec, rows,
            expected_protocol_sha256=kwargs.get('protocol', 'a' * 64),
            expected_spec_sha256=kwargs.get('spec_hash', digest(spec)))

    def test_exact_negative_upper_endpoint_accepts_only_numerically(self):
        spec, rows = fixture()
        result = self.run_check(spec, rows)
        self.assertEqual(result['contrasts'][0]['upper_endpoint'], rat(-1, 4))
        self.assertEqual(result['contrasts'][0]['mean'], rat(-1))
        self.assertTrue(result['contrasts'][0]['numerical_improvement'])
        self.assertFalse(result['sampling_eligibility_verified'])
        self.assertFalse(result['theorem_receipt_verified'])
        self.assertFalse(result['certified_improvement'])
        self.assertEqual(result['spec_sha256'], digest(spec))

    def test_zero_mean_has_no_numerical_improvement(self):
        spec, rows = fixture(0)
        result = self.run_check(spec, rows)
        self.assertEqual(result['contrasts'][0]['upper_endpoint'], rat(3, 4))
        self.assertFalse(result['contrasts'][0]['numerical_improvement'])

    def test_zero_endpoint_is_inconclusive(self):
        spec, rows = fixture()
        for row in rows:
            row['loss_difference'] = rat(-3, 4)
        self.assertFalse(self.run_check(spec, rows)['contrasts'][0]['numerical_improvement'])

    def test_insufficient_log_budget_is_rejected(self):
        spec, rows = fixture()
        spec['upper_log_budget'] = rat(1)
        with self.assertRaisesRegex(ValueError, 'log|Taylor'):
            self.run_check(spec, rows)

    def test_insufficient_taylor_terms_are_rejected(self):
        spec, rows = fixture()
        spec['log_evidence']['terms'] = 1
        with self.assertRaisesRegex(ValueError, 'log|Taylor'):
            self.run_check(spec, rows)

    def test_protocol_drift_is_rejected(self):
        spec, rows = fixture()
        with self.assertRaisesRegex(ValueError, 'protocol'):
            self.run_check(spec, rows, protocol='c' * 64)

    def test_spec_identity_drift_is_rejected(self):
        spec, rows = fixture()
        original = digest(spec)
        spec['contrast_ids'][0] = 'different-candidate'
        with self.assertRaisesRegex(ValueError, 'spec|identity'):
            self.run_check(spec, rows, spec_hash=original)

    def test_missing_row_is_not_counted_as_smaller_sample(self):
        spec, rows = fixture()
        with self.assertRaisesRegex(ValueError, 'complete|count|missing'):
            self.run_check(spec, rows[:-1])

    def test_duplicate_family_contrast_is_rejected(self):
        spec, rows = fixture()
        rows[-1] = copy.deepcopy(rows[0])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.run_check(spec, rows)

    def test_incomplete_and_refused_rows_are_rejected(self):
        for status in ['incomplete', 'refused', 'failed', 'not_started']:
            with self.subTest(status=status):
                spec, rows = fixture()
                rows[0]['status'] = status
                with self.assertRaisesRegex(ValueError, 'completed|status'):
                    self.run_check(spec, rows)

    def test_extra_or_unknown_identity_is_rejected(self):
        spec, rows = fixture()
        rows[0]['family_id'] = 'unregistered-family'
        with self.assertRaisesRegex(ValueError, 'identity|family'):
            self.run_check(spec, rows)

    def test_negative_or_boolean_count_is_rejected(self):
        for count in [-1, 0, True]:
            spec, rows = fixture()
            spec['family_count'] = count
            with self.assertRaises(ValueError):
                self.run_check(spec, rows)

    def test_duplicate_planned_family_and_contrast_are_rejected(self):
        for key in ['family_ids', 'contrast_ids']:
            spec, rows = fixture()
            spec[key][-1] = spec[key][0]
            with self.assertRaisesRegex(ValueError, 'duplicate'):
                self.run_check(spec, rows)

    def test_loss_outside_closed_range_is_rejected(self):
        for loss in [rat(1001, 1000), rat(-1001, 1000)]:
            spec, rows = fixture()
            rows[0]['loss_difference'] = loss
            with self.assertRaisesRegex(ValueError, 'range|loss'):
                self.run_check(spec, rows)

    def test_float_boolean_and_nonfinite_observations_are_rejected(self):
        for bad in [0.5, float('nan'), float('inf'), True, rat(True), rat(1, True)]:
            spec, rows = fixture()
            rows[0]['loss_difference'] = bad
            with self.assertRaises(ValueError):
                self.run_check(spec, rows)

    def test_float_and_boolean_spec_parameters_are_rejected(self):
        for key in ['alpha', 'fixed_lambda', 'upper_log_budget']:
            for bad in [0.5, True, rat(True)]:
                spec, rows = fixture()
                spec[key] = bad
                with self.assertRaises(ValueError):
                    self.run_check(spec, rows)

    def test_zero_denominator_and_invalid_probabilities_are_rejected(self):
        for key, bad in [('alpha', rat(1, 0)), ('alpha', rat(0)), ('alpha', rat(1)),
                         ('fixed_lambda', rat(0)), ('fixed_lambda', rat(-1))]:
            spec, rows = fixture()
            spec[key] = bad
            with self.assertRaises(ValueError):
                self.run_check(spec, rows)

    def test_term_and_operand_resource_guards(self):
        for bad in [0, -1, 257, True]:
            spec, rows = fixture()
            spec['log_evidence']['terms'] = bad
            with self.assertRaises(ValueError):
                self.run_check(spec, rows)
        for key in ['upper_log_budget', 'fixed_lambda']:
            spec, rows = fixture()
            spec[key] = rat(1 << 10000)
            with self.assertRaisesRegex(ValueError, 'bound|large|bits'):
                self.run_check(spec, rows)

    def test_taylor_denominator_growth_is_bounded_before_output(self):
        spec, rows = fixture()
        denominator = (1 << 124) - 1
        spec['upper_log_budget'] = rat(4 * denominator + 1, denominator)
        spec['log_evidence']['terms'] = 256
        with self.assertRaisesRegex(ValueError, 'bounded bits'):
            self.run_check(spec, rows)

    def test_unrecognized_proof_boolean_is_not_a_guarantee(self):
        spec, rows = fixture()
        spec['log_evidence']['lean_certified'] = True
        with self.assertRaises(ValueError):
            self.run_check(spec, rows)

    def test_receipt_identity_must_be_a_hash(self):
        spec, rows = fixture()
        spec['log_evidence']['proof_receipt_sha256'] = 'trust me'
        with self.assertRaises(ValueError):
            self.run_check(spec, rows)

if __name__ == '__main__':
    unittest.main()
