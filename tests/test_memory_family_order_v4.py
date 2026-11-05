"""Static-only order candidate checks: no cases, models, physics or solver."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'scripts/memory_family_order_v4.py'
CANDIDATE = ROOT / 'docs/reports/memory-v4-order-bounded-imbalance-candidate-2026-11-05.json'
SOURCE = ROOT / 'src/palimpsest/memory_decision_world.py'


def load_module():
    if not MODULE_PATH.exists():
        return None
    spec = importlib.util.spec_from_file_location('memory_family_order_v4_static', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


module = load_module()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                   allow_nan=False).encode('ascii')).hexdigest()


def assignments():
    # Read only literal factor tables from the pinned source AST, never import it.
    tree = ast.parse(SOURCE.read_text())
    node = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == 'FAMILY_DESIGN'
                        for target in node.targets))
    selected = {ast.literal_eval(key): ast.literal_eval(value)
                for key, value in zip(node.keys, node.values)
                if ast.literal_eval(key) in {'public_factor_names', 'public_factor_rows', 'cost_strata'}}
    rows = []
    for row in range(48):
        public, hidden = divmod(row, 4)
        factors = dict(zip(selected['public_factor_names'], selected['public_factor_rows'][public]))
        rows.append(dict(row=row, cost_stratum=selected['cost_strata'][public // 4],
                         regime=('local_cue', 'paired_cue')[hidden & 1],
                         relation_side=hidden >> 1, **factors))
    return rows


class StaticOrderChecks(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(module, 'Pure memory-v4 order validator is not implemented')
        self.candidate = json.loads(CANDIDATE.read_text())
        self.design = assignments()
        self.source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()

    def check(self, candidate=None, design=None, **pins):
        candidate = self.candidate if candidate is None else candidate
        design = self.design if design is None else design
        return module.validate_order_candidate(candidate, design,
            expected_source_sha256=pins.get('source_pin', self.source_hash),
            expected_design_sha256=pins.get('design_pin', digest(design)),
            expected_candidate_sha256=pins.get('candidate_pin', digest(candidate)))

    def test_existing_candidate_recomputes_static_counts(self):
        result = self.check()
        self.assertEqual(result['scope'], 'STATIC_ONLY')
        self.assertFalse(result['execution_authorized'])
        self.assertFalse(result['scientific_admission'])
        self.assertFalse(result['exact_public_factor_balance'])
        self.assertTrue(result['hidden_factor_position_balance'])
        self.assertEqual(result['shift_counts'], [6] * 8)
        for counts in result['stratum_shift_counts'].values():
            self.assertEqual(counts, [2] * 8)
        self.assertEqual(result['public_factor_one_count_range'], [2, 4])
        for row in result['row_orders']:
            self.assertEqual(row['order'][:2], ['source', 'own'])
            self.assertEqual(len(row['order']), 10)
            self.assertEqual(len(set(row['order'])), 10)
        for factors in result['factor_ones_by_condition_position'].values():
            self.assertEqual(factors['regimebit'], [3] * 8)
            self.assertEqual(factors['relation_side'], [3] * 8)
            for factor in module.PUBLIC_FACTORS:
                self.assertTrue(all(2 <= value <= 4 for value in factors[factor]))

    def test_naive_row_mod_eight_has_hidden_aliasing(self):
        self.candidate['row_shifts'] = [row % 8 for row in range(48)]
        with self.assertRaisesRegex(ValueError, 'hidden'):
            self.check()

    def test_claim_flags_do_not_substitute_for_recomputed_counts(self):
        self.candidate['row_shifts'] = [0] * 48
        self.candidate['integer_constraints_verified'] = True
        with self.assertRaisesRegex(ValueError, 'shift|position'):
            self.check()

    def test_balanced_fake_roster_fails_external_digest(self):
        expected = digest(self.design)
        self.design[0], self.design[1] = self.design[1], self.design[0]
        self.design[0]['row'], self.design[1]['row'] = 0, 1
        # Explicit original external hash, even though swap preserves marginals.
        with self.assertRaisesRegex(ValueError, 'design|roster'):
            module.validate_order_candidate(self.candidate, self.design,
                expected_source_sha256=self.source_hash, expected_design_sha256=expected,
                expected_candidate_sha256=digest(self.candidate))

    def test_mutated_candidate_or_source_digest_refuses(self):
        expected = digest(self.candidate)
        self.candidate['row_shifts'][0] = 2
        with self.assertRaisesRegex(ValueError, 'candidate'):
            self.check(candidate_pin=expected)
        with self.assertRaisesRegex(ValueError, 'source'):
            self.check(source_pin='f' * 64)

    def test_canonical_unique_complete_family_rows_required(self):
        for design in [self.design[:-1], self.design + [copy.deepcopy(self.design[0])],
                       list(reversed(self.design))]:
            with self.subTest(length=len(design)), self.assertRaises(ValueError):
                self.check(design=design)
        self.design[-1]['row'] = 0
        with self.assertRaisesRegex(ValueError, 'row|duplicate'):
            self.check(design=self.design)

    def test_strata_must_have_sixteen_canonical_rows(self):
        self.design[0]['cost_stratum'] = 'north'
        with self.assertRaisesRegex(ValueError, 'strat'):
            self.check()

    def test_boolean_or_out_of_range_shift_is_rejected(self):
        for invalid in [True, False, -1, 8, 1.0, '1']:
            candidate = copy.deepcopy(self.candidate)
            candidate['row_shifts'][0] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.check(candidate=candidate)

    def test_partial_or_extra_shift_list_is_rejected(self):
        for values in [self.candidate['row_shifts'][:-1], self.candidate['row_shifts'] + [1]]:
            candidate = copy.deepcopy(self.candidate)
            candidate['row_shifts'] = values
            with self.assertRaises(ValueError):
                self.check(candidate=candidate)

    def test_invalid_factor_and_row_types_are_rejected(self):
        for key, invalid in [('row', True), ('fact_first_side', True),
                             ('relation_side', 2), ('regime', 'oracle'),
                             ('route_first_side', 0.0)]:
            design = copy.deepcopy(self.design)
            design[0][key] = invalid
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(design=design)

    def test_bounded_solver_metadata_rejects_huge_integer_as_value_error(self):
        self.candidate['elapsed_seconds'] = 1 << 2000
        with self.assertRaises(ValueError):
            self.check()

    def test_candidate_cannot_grant_scientific_admission(self):
        self.candidate['scientific_admission'] = True
        with self.assertRaisesRegex(ValueError, 'admission|scope'):
            self.check()

    def test_inputs_are_unchanged_and_output_has_no_aliases(self):
        original = copy.deepcopy((self.candidate, self.design))
        result = self.check()
        result['row_orders'][0]['order'][0] = 'changed'
        self.assertEqual((self.candidate, self.design), original)


if __name__ == '__main__':
    unittest.main()
