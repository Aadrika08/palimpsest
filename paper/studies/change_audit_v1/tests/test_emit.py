"""Pure closed-witness generation tests; never invoke Lean or a simulator."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).parents[1]


def load(name, path):
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


emitter = load('change_audit_v1_emit', ROOT / 'emit.py')
fixtures = load('change_audit_v1_emit_fixtures', ROOT / 'tests/test_check.py')


class EmissionChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(emitter, 'Closed Lean numerical witness emitter is not implemented')

    def emit(self, spec, rows, *, protocol='a' * 64, spec_hash=None):
        return emitter.emit_lean_certificate(spec, rows, expected_protocol_sha256=protocol,
            expected_spec_sha256=fixtures.digest(spec) if spec_hash is None else spec_hash)

    def test_closed_negative_example_binds_exact_arithmetic_and_identity(self):
        spec, rows = fixtures.fixture()
        artifact = self.emit(spec, rows)
        source, metadata = artifact['lean_source'], artifact['metadata']
        self.assertIn('import ChangeAudit.Numerical', source)
        self.assertIn('rational_family_log_enclosure', source)
        self.assertIn('theorem mean_0_exact', source)
        self.assertIn('theorem upper_0_exact', source)
        self.assertIn('theorem upper_0_strict_negative', source)
        self.assertIn('((-1 : ℚ) / 4)', source)
        self.assertEqual(metadata['spec_sha256'], fixtures.digest(spec))
        self.assertEqual(metadata['lean_source_sha256'], hashlib.sha256(source.encode()).hexdigest())
        self.assertEqual(metadata['numerical_result']['contrasts'][0]['upper_endpoint'], fixtures.rat(-1, 4))
        for key in ['sampling_eligibility_verified', 'theorem_application_verified',
                    'certified_improvement', 'source_compiled']:
            self.assertFalse(metadata[key])
        for forbidden in ['sorry', 'admit', 'native_decide', 'axiom ']:
            self.assertNotIn(forbidden, source)
        self.assertNotIn('candidate-a', source)

    def test_rows_encoded_in_declared_family_order_not_input_order(self):
        spec, rows = fixtures.fixture()
        rows[0]['loss_difference'] = fixtures.rat(-1, 2)
        rows.reverse()
        artifact = self.emit(spec, rows)
        source = artifact['lean_source']
        self.assertIn('def losses_0 : List ℚ := [((-1 : ℚ) / 2), ((-1 : ℚ) / 1)', source)
        self.assertIn('((-31 : ℚ) / 32)', source)
        self.assertEqual(artifact['metadata']['numerical_result']['contrasts'][0]['mean'], fixtures.rat(-31, 32))
        self.assertEqual(artifact['metadata']['family_ids'], spec['family_ids'])
        self.assertEqual(artifact['metadata']['contrast_ids'], spec['contrast_ids'])

    def test_nonnegative_endpoint_has_no_negative_theorem_or_false_certificate(self):
        spec, rows = fixtures.fixture(0)
        artifact = self.emit(spec, rows)
        self.assertIn('theorem upper_0_nonnegative', artifact['lean_source'])
        self.assertNotIn('theorem upper_0_strict_negative', artifact['lean_source'])
        self.assertFalse(artifact['metadata']['certified_improvement'])
        self.assertFalse(artifact['metadata']['numerical_result']['contrasts'][0]['numerical_improvement'])

    def test_zero_endpoint_generates_nonnegative_witness(self):
        spec, rows = fixtures.fixture()
        for row in rows:
            row['loss_difference'] = fixtures.rat(-3, 4)
        artifact = self.emit(spec, rows)
        self.assertIn('theorem upper_0_nonnegative', artifact['lean_source'])
        self.assertFalse(artifact['metadata']['certified_improvement'])

    def test_valid_but_code_like_ids_never_enter_lean_source(self):
        spec, rows = fixtures.fixture()
        original = spec['contrast_ids'][0]
        spec['contrast_ids'][0] = 'evil:namespace'
        for row in rows:
            if row['contrast_id'] == original:
                row['contrast_id'] = 'evil:namespace'
        artifact = self.emit(spec, rows)
        self.assertNotIn('evil:namespace', artifact['lean_source'])
        self.assertIn('evil:namespace', artifact['metadata']['contrast_ids'])

    def test_malicious_ids_and_partial_grid_refuse(self):
        spec, rows = fixtures.fixture()
        rows[0]['family_id'] = 'x\naxiom injected : False'
        with self.assertRaises(ValueError):
            self.emit(spec, rows)
        spec, rows = fixtures.fixture()
        with self.assertRaises(ValueError):
            self.emit(spec, rows[:-1])

    def test_protocol_and_spec_drift_refuse(self):
        spec, rows = fixtures.fixture()
        with self.assertRaises(ValueError):
            self.emit(spec, rows, protocol='c' * 64)
        with self.assertRaises(ValueError):
            self.emit(spec, rows, spec_hash='d' * 64)

    def test_codegen_family_contrast_and_term_limits(self):
        spec, _ = fixtures.fixture()
        spec['family_ids'] = [f'f-{i}' for i in range(129)]
        spec['family_count'] = 129
        rows = [{'family_id': f, 'contrast_id': c, 'status': 'completed',
                 'loss_difference': fixtures.rat(-1)}
                for f in spec['family_ids'] for c in spec['contrast_ids']]
        with self.assertRaisesRegex(ValueError, 'generation|export'):
            self.emit(spec, rows)
        spec, _ = fixtures.fixture()
        spec['contrast_ids'] = [f'contrast-{i}' for i in range(9)]
        spec['upper_log_budget'] = fixtures.rat(6)
        rows = [{'family_id': f, 'contrast_id': c, 'status': 'completed',
                 'loss_difference': fixtures.rat(-1)}
                for f in spec['family_ids'] for c in spec['contrast_ids']]
        with self.assertRaisesRegex(ValueError, 'generation|export'):
            self.emit(spec, rows)
        spec, rows = fixtures.fixture()
        spec['log_evidence']['terms'] = 33
        with self.assertRaisesRegex(ValueError, 'generation|export'):
            self.emit(spec, rows)

    def test_total_certificate_byte_limit_is_fail_closed(self):
        spec, rows = fixtures.fixture()
        with patch.object(emitter, 'MAX_CERTIFICATE_BYTES', 128):
            with self.assertRaisesRegex(ValueError, 'bytes|size'):
                self.emit(spec, rows)

    def test_deterministic_and_input_preserving(self):
        spec, rows = fixtures.fixture()
        original = copy.deepcopy((spec, rows))
        first, second = self.emit(spec, rows), self.emit(spec, rows)
        self.assertEqual(first, second)
        self.assertEqual((spec, rows), original)
        self.assertLessEqual(len(json.dumps(first, sort_keys=True, separators=(',', ':'),
                                            ensure_ascii=True).encode()), 256 * 1024)

if __name__ == '__main__':
    unittest.main()
