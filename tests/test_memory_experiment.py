"""Development fixture/baseline checks, never held-out or embodied evidence."""

import copy
import unittest
from unittest.mock import patch

from palimpsest import memory, memory_experiment as experiment, memory_world


def histories():
    return experiment.make_history(0, 'local_cue'), experiment.make_history(100, 'paired_cue')


class SyntheticDevelopment(unittest.TestCase):
    def test_independent_reproducible_geometry_gold_and_identical_visible_regimes(self):
        with (patch.object(memory, 'fit', side_effect=AssertionError('Generator must not fit')),
              patch.object(memory, 'select', side_effect=AssertionError('Generator must not select'))):
            fixture, truth = experiment.make_case(12, 'local_cue', 'development-test')
            repeated = experiment.make_case(12, 'local_cue', 'development-test')
            other_fixture, other_truth = experiment.make_case(12, 'paired_cue', 'development-test')
        self.assertEqual((fixture, truth), repeated)
        self.assertEqual(fixture, other_fixture)
        self.assertNotEqual(truth['gold_target_ids'], other_truth['gold_target_ids'])
        self.assertEqual(len(truth['gold_target_ids']), 1)
        self.assertEqual(memory_world.passage_status(truth['before_geometry']), {'passage-a': 'open', 'passage-b': 'open'})
        self.assertEqual(list(truth['after_occupancy'].values()).count('blocked'), 1)
        self.assertNotIn('regime', fixture)
        m = copy.deepcopy(fixture['m'])
        for fact in m['facts']:
            fact.update(status='unknown', estimate=None, evidence=None, origin='initial_unknown')
        self.assertEqual(experiment.gold_target_ids(m, truth['before_occupancy'], truth['after_occupancy'], fixture['trigger']), [])

    def test_disjoint_ids_and_independent_side_relation_lexical_counterbalance(self):
        own, swapped = histories()
        fixture, truth = experiment.make_case(0, 'local_cue', 'development-test')
        self.assertFalse(experiment._ids(fixture) & (experiment._ids(own) | experiment._ids(swapped)))
        self.assertFalse(experiment._ids(own) & experiment._ids(swapped))
        combinations = set()
        for seed in range(8):
            case, labels = experiment.make_case(seed, 'local_cue', 'development-test')
            lower = labels['subjects_by_side'][0]
            fact = next(f for f in case['m']['facts'] if f['subject_id'] == lower)
            combinations.add((fact['associations'][0]['relation'], fact['id'] == case['m']['facts'][0]['id'],
                              lower == min(labels['subjects_by_side'])))
        self.assertEqual(len(combinations), 8)
        with self.assertRaisesRegex(ValueError, 'disjoint'):
            experiment.compare_conditions(fixture, own, own, truth)
        leaking = copy.deepcopy(own)
        leaking['episodes'][0]['trigger']['cue_id'] = fixture['trigger']['cue_id']
        with self.assertRaisesRegex(ValueError, 'disjoint'):
            experiment.compare_conditions(fixture, leaking, swapped, truth)

    def test_nine_conditions_fit_only_e_and_report_differing_information_budgets(self):
        own, swapped = histories()
        fixture, truth = experiment.make_case(8, 'local_cue', 'development-test')
        originals = copy.deepcopy((fixture, truth, own, swapped))
        with patch.object(memory, 'fit', wraps=memory.fit) as fit:
            report = experiment.compare_conditions(fixture, own, swapped, truth)
            self.assertEqual([call.args for call in fit.call_args_list], [(own,), (swapped,)])
            self.assertTrue(all(not call.kwargs for call in fit.call_args_list))
        self.assertEqual((fixture, truth, own, swapped), originals)
        results = {r['condition']: r for r in report['results']}
        self.assertEqual(tuple(results), experiment.CONDITIONS)
        self.assertEqual(results['own']['selection'], results['sham']['selection'])
        self.assertTrue(results['own']['exact_set'])
        self.assertFalse(results['swapped']['exact_set'])
        self.assertTrue(results['oracle']['exact_set'])
        self.assertTrue(results['oracle']['privileged'])
        self.assertFalse(results['hand-authored']['privileged'])
        self.assertEqual(results['retrieval']['runtime_history_bytes'], len(memory.canonical_bytes(own)))
        self.assertEqual(results['own']['runtime_history_bytes'], 0)
        self.assertGreater(results['own']['envelope_bytes'], results['own']['payload_bytes'])
        self.assertLess(results['own']['behavior_input_bytes'], results['own']['runtime_input_bytes'])
        self.assertNotIn('u', results['own']['behavior_access'])
        self.assertIn('u.payload', results['own']['behavior_access'])
        self.assertEqual(report['histories']['own'], own)
        self.assertTrue(all(len(r['selection']['target_ids']) <= 1 for r in results.values()))
        for limit in (0, 2, 8):
            bounded = experiment.compare_conditions(fixture, own, swapped, truth, limit=limit)
            self.assertTrue(all(len(r['selection']['target_ids']) <= limit for r in bounded['results']))

    def test_null_and_no_event_do_not_hide_false_targets_or_miscount_abstention(self):
        own, swapped = histories()
        fixture, truth = experiment.make_case(8, 'local_cue', 'development-test', kind='null')
        self.assertEqual(truth['gold_target_ids'], [])
        report = experiment.compare_conditions(fixture, own, swapped, truth)
        results = {r['condition']: r for r in report['results']}
        self.assertFalse(results['own']['exact_set'])
        self.assertEqual(results['own']['false_targets'], 1)
        self.assertTrue(results['no-U']['correct_abstention'])
        self.assertTrue(results['oracle']['correct_abstention'])
        self.assertIsNone(results['own']['recall'])
        fixture, truth = experiment.make_case(8, 'local_cue', 'development-test', kind='no-event')
        with patch.object(memory, 'select', side_effect=AssertionError('No event must not invoke selector')):
            report = experiment.compare_conditions(fixture, own, swapped, truth)
        self.assertTrue(all(r['exact_set'] and r['correct_abstention'] for r in report['results']))
        self.assertTrue(all(r['behavior_input_bytes'] == 0 for r in report['results']))

    def test_unobserved_history_is_not_a_negative_or_a_retrieval_completion(self):
        own = experiment.make_history(0, 'local_cue', unobserved_relation='paired_cue')
        u = memory.fit(own)
        self.assertEqual(u['payload']['rules'], [])
        self.assertEqual(u['provenance']['support']['paired_cue'], {'observed': 0, 'changed': 0})
        self.assertEqual(u['provenance']['support']['local_cue']['observed'], 4)
        fixture, truth = experiment.make_case(8, 'local_cue', 'development-test')
        report = experiment.compare_conditions(fixture, own, histories()[1], truth)
        retrieved = next(r for r in report['results'] if r['condition'] == 'retrieval')
        self.assertTrue(retrieved['abstained'])
        self.assertFalse(retrieved['exact_set'])

    def test_bounded_validation_rejects_held_out_tampering_and_bad_budgets(self):
        for seed in (-1, True, 2**32):
            with self.assertRaises(ValueError):
                experiment.make_case(seed, 'local_cue', 'development-test')
        with self.assertRaisesRegex(ValueError, 'held-out'):
            experiment.make_case(0, 'local_cue', 'held-out')
        own, swapped = histories()
        fixture, truth = experiment.make_case(8, 'local_cue', 'development-test')
        for limit in (-1, True, 9):
            with self.assertRaises(ValueError):
                experiment.compare_conditions(fixture, own, swapped, truth, limit=limit)
        bad = copy.deepcopy(truth)
        bad['after_occupancy'] = bad['before_occupancy']
        with self.assertRaisesRegex(ValueError, 'geometry'):
            experiment.validate_truth(bad, fixture)
        bad = copy.deepcopy(truth)
        bad['gold_target_ids'] = []
        with self.assertRaisesRegex(ValueError, 'gold'):
            experiment.validate_truth(bad, fixture)
        bad = copy.deepcopy(fixture)
        bad['future_regime'] = 'local_cue'
        with self.assertRaises(ValueError):
            experiment.validate_fixture(bad)
        bad = copy.deepcopy(fixture)
        bad['case_id'] = 'x' * experiment.MAX_CASE_BYTES
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            experiment.validate_fixture(bad)
        for key, value in (('kind', 'null'), ('regime', 'paired_cue'), ('seed', 9)):
            bad = copy.deepcopy(truth)
            bad[key] = value
            with self.assertRaisesRegex(ValueError, 'mechanism'):
                experiment.validate_truth(bad, fixture)
        bad = copy.deepcopy(fixture)
        bad['m']['facts'][0]['associations'][0]['relation'] = 'paired_cue'
        with self.assertRaisesRegex(ValueError, 'counterbalancing'):
            experiment.validate_truth(truth, bad)


if __name__ == '__main__':
    unittest.main()
