"""Pure complete-campaign fixtures, never scientific evidence."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'paper/scripts'))
from paper.studies.authority_replay_v1.common import load_protocol, declared_units
from paper.studies.authority_replay_v1.analyze import summarize


def fixture():
    protocol = load_protocol(ROOT / 'paper/studies/authority_replay_v1/protocol.json')
    identity = {'commit': 'd8658dda3fca37bb43b6dafc909114279f706f11',
                'protocol_sha256': protocol._content_sha256,
                **{k: {'fixture': 'a' * 64} for k in ('runtime_source_sha256', 'asset_manifest_sha256', 'asset_sha256')}}
    rows = [dict(schema_version=1, study_id=protocol.study_id, identity=identity,
                 status='incomplete', metrics={}, **u) for u in declared_units(protocol)]
    # Mixed truth deliberately proves acceptance is not the truth oracle.
    faults = [r for r in rows if r['kind'] == 'fault']
    for row, truth in zip(faults[:3], (True, False, 'unknown')):
        row.update(status='completed', baseline_claim_truth=truth,
                   baseline_outcome={'accepted': True, 'claim_truth': truth},
                   silent_acceptance=False, explicit_detection=True,
                   correct_recovery=False, benign_false_rejection=False,
                   outcome_scope='study_guard', palimpsest_outcome='accepted')
    for row in rows:
        if row['kind'] == 'execution_overhead':
            condition = row['condition']
            wall = {'null': 10, 'synchronous': 12, 'background': 9, 'background_storage': 11}[condition]
            row.update(status='completed', tick_count=220, actions_sha256='b'*64,
                       final_state_sha256='c'*64, matched_seed=True, timing_eligible=True,
                       metrics={'wall_seconds_per_tick': wall / 1000})
        if row['kind'] == 'operation_cost' and row['seed'] < 2:
            row.update(status='completed', metrics={'capture_seconds': 0.1 + row['seed']})
    return protocol, summarize(protocol, rows), {'identity': identity, 'analysis_status': 'passed'}


class AuthorityEvidenceTests(unittest.TestCase):
    def builder(self):
        path = ROOT / 'paper/scripts/build_authority_evidence.py'
        self.assertTrue(path.exists(), 'authority evidence builder is not implemented')
        spec = importlib.util.spec_from_file_location('authority_builder', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_counts_unknowns_and_failed_denominators(self):
        p, s, m = fixture()
        result = self.builder().analyze(s, m, p)
        self.assertEqual(result['declared'], 111)
        self.assertEqual(result['faults']['total']['baseline_false_accepts'], 1)
        self.assertEqual(result['faults']['total']['baseline_known'], 2)
        self.assertEqual(result['faults']['total']['baseline_unknown'], 1)
        self.assertEqual(result['faults']['total']['baseline_missing'], 47)
        self.assertEqual(result['faults']['total']['study_guard_detection'], 3)
        self.assertEqual(result['faults']['total']['production_detection'], 0)
        self.assertEqual(result['continuation']['passed'], 0)
        self.assertEqual(result['continuation']['declared'], 10)

    def test_paired_deltas_and_operation_sample_sizes(self):
        p, s, m = fixture()
        result = self.builder().analyze(s, m, p)
        self.assertEqual(result['overhead']['matched'], 10)
        self.assertAlmostEqual(result['overhead']['relative']['background']['median'], -10)
        self.assertEqual(result['overhead']['wall_ms']['null']['median'], 10)
        self.assertEqual(result['operations']['capture_seconds']['n'], 2)
        self.assertIsNone(result['operations']['save_seconds'])
        self.assertEqual(result['offline']['status'], 'incomplete')

    def test_rejects_invalid_identity_rows_truth_and_gates(self):
        module = self.builder()
        for mutation in ('commit', 'manifest', 'analysis', 'missing', 'duplicate', 'undeclared', 'nan', 'truth', 'gate', 'summary', 'protocol'):
            with self.subTest(mutation=mutation):
                p, s, m = fixture()
                if mutation == 'commit':
                    s['identity']['commit'] = 'f'*40
                elif mutation == 'manifest':
                    m['identity'] = dict(m['identity'], protocol_sha256='f'*64)
                elif mutation == 'analysis': m['analysis_status'] = 'failed'
                elif mutation == 'missing': s['rows'].pop()
                elif mutation == 'duplicate': s['rows'].append(copy.deepcopy(s['rows'][0]))
                elif mutation == 'undeclared': s['rows'][0]['unit_id'] = 'invented'
                elif mutation == 'nan': s['rows'][0]['metrics']['wall'] = float('nan')
                elif mutation == 'truth': s['rows'][0]['baseline_outcome']['claim_truth'] = 1
                elif mutation == 'gate':
                    next(r for r in s['rows'] if r['kind'] == 'execution_overhead')['tick_count'] = 219
                elif mutation == 'summary': s['declared_units'] = 110
                elif mutation == 'protocol':
                    object.__setattr__(p, '_content_sha256', 'e'*64)
                    s['identity']['protocol_sha256'] = 'e'*64
                with self.assertRaises(ValueError): module.analyze(s, m, p)

    def test_unmatched_whole_sets_remain_declared(self):
        p, s, m = fixture()
        group = [r for r in s['rows'] if r['kind'] == 'execution_overhead' and r['seed'] == 0]
        group[0]['status'] = 'failed'
        for r in group: r.update(matched_seed=False, timing_eligible=False)
        s = summarize(p, s['rows'])
        result = self.builder().analyze(s, m, p)
        self.assertEqual(result['overhead']['matched'], 9)
        self.assertEqual(result['overhead']['declared'], 10)
        self.assertEqual(len(result['overhead']['raw']), 10)

    def test_relative_statistics_are_per_seed_before_aggregation(self):
        p, s, m = fixture()
        for row in s['rows']:
            if row['kind'] == 'execution_overhead':
                base = row['seed'] + 1
                row['metrics']['wall_seconds_per_tick'] = base * (2 if row['seed'] >= 5 and row['condition'] == 'synchronous' else 1)
        result = self.builder().analyze(summarize(p, s['rows']), m, p)
        self.assertEqual(result['overhead']['relative']['synchronous']['median'], 50)
        self.assertEqual(result['overhead']['relative']['synchronous']['iqr'], 100)

    def test_no_matched_timings_are_not_estimable(self):
        p, s, m = fixture()
        for row in s['rows']:
            if row['kind'] == 'execution_overhead':
                row.update(status='incomplete', metrics={}, matched_seed=False, timing_eligible=False)
        result = self.builder().analyze(summarize(p, s['rows']), m, p)
        output = self.builder().generate_outputs(result, {})
        self.assertIn(r'\newcommand{\NullWallMedianMs}{not estimable}', output['authority-claims.tex'])
        self.assertIn('not estimable', output['overhead-plot.tex'])

    def test_passing_comparisons_require_exact_scope_and_no_divergence(self):
        module = self.builder()
        p, s, m = fixture()
        for row in s['rows']:
            if row['kind'] not in ('continuation', 'replay'): continue
            kind = row['kind']
            report = dict(status='passed', finite_scientific_arrays=True, prefix_ticks=8,
                          continuation_ticks=100 if kind == 'continuation' else 92,
                          first_divergence=None, max_abs_errors={'qpos': 0},
                          random_draws_match=True, source_event_prefix_unchanged=True,
                          branch_identity_distinct=True, queued_command_idempotency=True)
            row.update(status='completed', first_divergence=None, metrics={'agreement': True}, verifier_report=report)
            if kind == 'replay':
                report['source_run_id'] = 'source-' + str(row['seed'])
                row['source_manifest_sha256'] = 'd'*64
                pairs = {}
                for mode in p.replay['conditions']:
                    expected = mode in ('branch', 'policy_replay')
                    pairs[mode] = dict(agreement=True, first_divergence=None, validated_fields=['qpos'],
                                       executed_computation=dict(controller_reexecuted=expected, inference_executed=expected))
                    if mode in ('action_replay', 'policy_replay'):
                        pairs[mode]['raw'] = dict(status='passed', first_divergence=None, errors=[],
                            source_run_id=report['source_run_id'], compared_ticks=100,
                            mode='actions' if mode == 'action_replay' else 'policy')
                row['paired_raw_values'] = pairs
        valid = summarize(p, s['rows'])
        result = module.analyze(valid, m, p)
        self.assertEqual((result['continuation']['passed'], result['replay']['passed']), (10, 5))
        for field, value in (('compared_ticks', 99), ('source_run_id', 'wrong'), ('first_divergence', {'tick': 4})):
            broken = copy.deepcopy(valid)
            replay = next(r for r in broken['rows'] if r['kind'] == 'replay')
            replay['paired_raw_values']['policy_replay']['raw'][field] = value
            with self.assertRaises(ValueError): module.analyze(summarize(p, broken['rows']), m, p)

    def test_deterministic_escaped_outputs_and_cli_freshness(self):
        module = self.builder()
        p, s, m = fixture()
        with tempfile.TemporaryDirectory(dir=ROOT / 'runs/paper-generator-tests') as tmp:
            base = Path(tmp)
            for name, value in (('summary', s), ('manifest', m)):
                (base / (name + '.json')).write_text(json.dumps(value))
            args = ['--summary', str(base/'summary.json'), '--manifest', str(base/'manifest.json'),
                    '--protocol', str(ROOT/'paper/studies/authority_replay_v1/protocol.json'), '--output', str(base/'output')]
            self.assertEqual(module.main(args), 0)
            self.assertEqual(module.main(args + ['--check']), 0)
            files = {f.name: f.read_text() for f in (base/'output').iterdir()}
            self.assertEqual(set(files), {'authority-claims.tex','fault-matrix.tex','replay-table.tex','overhead-table.tex','operation-table.tex','overhead-plot.tex'})
            self.assertIn('not estimable', files['operation-table.tex'])
            self.assertIn('-10', files['overhead-plot.tex'])
            self.assertIn(hashlib.sha256((base/'summary.json').read_bytes()).hexdigest(), files['authority-claims.tex'])
            self.assertEqual(module.escape_latex('a_b%&'), r'a\_b\%\&')
            self.assertIn('Raw per-seed', files['overhead-table.tex'])
            self.assertLess(max(map(len, files['authority-claims.tex'].splitlines())), 2000)
            (base/'output/authority-claims.tex').write_text('stale')
            self.assertEqual(module.main(args + ['--check']), 1)


if __name__ == '__main__':
    unittest.main()
