"""Synthetic readouts only: paired censoring, strata, coverage and input refusal."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts import analyze_memory_matrix as analysis


def report(profile):
    r = analysis.verifier
    digest = r.profile_digest(profile)
    fixed, protocol = r.fixed_profile(digest)
    value = {'protocol_sha256': digest, 'status': 'comparison_checked', 'claim': protocol['claim'],
             'source_unchanged': True, 'retained_unchanged': True,
             'source_identity': {'synthetic_fixture': True}, 'final_source_identity': {'synthetic_fixture': True},
             'held_out_executed': False, 'r2_complete': False, 'unattempted_stages': [],
             'runs': [], 'comparisons': [], 'bindings': {}}
    for parameters in fixed:
        case = r.admission.make_case(parameters)
        key = r.admission.cell_key(parameters)
        value['runs'].extend([{'mechanism_pass': True, 'cell': key, 'stage': stage,
                              'run_id': f"{len(value['runs'])+index:032x}"} for index, stage in enumerate(r.STAGES)])
        gold = [f['id'] for f in case['facts'] if parameters[2] == 'change' and f['subject_id'] == case['closure_subject_id']]
        cell = {'cell': key, 'gold_target_ids': gold, 'runtime': [], 'targeting': []}
        for condition in r.common.CONDITIONS:
            cell['runtime'].append({'condition': condition, 'task_pass': True, 'navigation_pass': True,
                'goal_tick': 430, 'outcome': {'reason': 'goal'}, 'target_ids': gold[:],
                'selector_invocations': int(parameters[2] != 'no-event'),
                'selector_behavior_bytes': int(parameters[2] != 'no-event'),
                'requested': 0, 'started': 0, 'resolved': 0, 'timeouts': 0,
                'timing': [{'fact_id': f['id'], 'stale_value_changed': f['id'] in gold,
                    'first_stale_value_correction_tick': 358 if f['id'] in gold else None,
                    'first_confirmation_tick': None if f['id'] in gold else 300} for f in case['facts']]})
            cell['targeting'].append({'condition': condition, 'exact_set': True, 'false_targets': 0,
                                     'missed_targets': 0, 'precision': 1.0 if gold else None,
                                     'recall': 1.0 if gold else None, 'selection': {'target_ids': gold[:]}})
        value['bindings'][key] = {'case': case}
        value['comparisons'].append(cell)
    return value


class MatrixAnalysis(unittest.TestCase):
    def test_paired_analysis_censoring_coverage_and_refusal(self):
        c3, c4 = report('c3'), report('c4')
        missed = next(r for r in c4['comparisons'][0]['runtime'] if r['condition'] == 'no-U')
        missed.update(task_pass=False, navigation_pass=False, goal_tick=None, outcome={'reason': 'time_limit'})
        for timing in missed['timing']:
            if timing['stale_value_changed']:
                timing['first_stale_value_correction_tick'] = None
        result = analysis.summarize([c3, c4])
        self.assertEqual(result['status'], 'partial-development-readout')
        self.assertEqual((result['completed_cells'], len(result['missing_cells'])), (8, 40))
        self.assertEqual(len(result['seed_blocks']), 8)
        self.assertEqual(len(result['paired_readouts']), 64)
        pair = next(p for p in result['paired_readouts'] if p['cell'] == c4['comparisons'][0]['cell'] and p['reference'] == 'no-U')
        self.assertEqual(pair['pair_contract'], 'strict-u-only')
        self.assertEqual(pair['task_pass_difference'], 1)
        self.assertIsNone(pair['goal_boundary']['own_minus_reference'])
        self.assertEqual(pair['stale_correction_boundary']['missing'], 'reference')
        self.assertTrue(all(p['stale_correction_boundary']['missing'] == 'not-applicable'
                            for p in result['paired_readouts'] if p['kind'] != 'change'))
        self.assertTrue(all(p['core_contract'] == 'historical-broader-core'
                            for p in result['paired_readouts'] if p['cell'] in {c['cell'] for c in c3['comparisons']}))
        complete = analysis.summarize([c3, report('c4'), *(report(n) for n in analysis.verifier.admission.REMAINING_NAMES)])
        self.assertEqual(complete['status'], 'complete-development-readout')
        self.assertEqual(complete['completed_cells'], 48)
        self.assertFalse(complete['r2_complete'])
        self.assertEqual(set(complete['seed_blocks'].values()), {6})
        with self.assertRaisesRegex(ValueError, 'duplicate profile'):
            analysis.summarize([c3, c3])
        for label, mutate in (
            ('held-out', lambda v: v.update(held_out_executed=True)),
            ('failed', lambda v: v.update(status='failed')),
            ('incomplete', lambda v: v['comparisons'].pop()),
            ('confirmation', lambda v: v['comparisons'][0]['runtime'][0]['timing'][0].update(first_confirmation_tick=300)),
            ('no-event', lambda v: v['comparisons'][-1]['runtime'][0].update(selector_invocations=1)),
            ('wrong-gold-side', lambda v: v['comparisons'][0].update(gold_target_ids=[v['comparisons'][0]['runtime'][0]['timing'][1]['fact_id']])),
            ('precision', lambda v: v['comparisons'][0]['targeting'][0].update(precision=0.0)),
            ('selection', lambda v: v['comparisons'][0]['targeting'][0]['selection'].update(target_ids=[])),
        ):
            with self.subTest(label=label), self.assertRaises(ValueError):
                broken = copy.deepcopy(c3)
                mutate(broken)
                analysis.summarize([broken])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'report.json'
            path.write_text(json.dumps(c3))
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(analysis.verifier.pinned_json(path, digest), c3)
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                analysis.verifier.pinned_json(path, digest)


if __name__ == '__main__':
    unittest.main()
