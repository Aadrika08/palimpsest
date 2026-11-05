"""Pure complete-campaign fixtures, never scientific evidence."""
import copy
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'paper/scripts'))
from paper.studies.authority_replay_v1.common import load_protocol, declared_units
from paper.studies.authority_replay_v1.analyze import summarize


def replay_report(mode, source):
    return dict(status='passed', mode=mode, source_run_id=source, compared_ticks=100,
                first_divergence=None, errors=[], comparison={'qpos': 'float32'},
                controller_reexecuted=mode == 'policy', inference_executed=mode == 'policy')


def complete_replay(row, protocol):
    from paper.studies.authority_replay_v1.repeatability import _paired
    source = 'source-' + str(row['seed'])
    meta = dict(run_path='/fixture/' + source, snapshot_path='/fixture/' + source + '/snapshots/prefix.snp',
                condition='background_storage', recording_writer='background', storage_accounting=True,
                seed=row['seed'], prefix_ticks=8, source_ticks=100)
    report = dict(status='passed', finite_scientific_arrays=True, prefix_ticks=8, continuation_ticks=92,
                  source_run_id=source, source=copy.deepcopy(meta), snapshot_path=meta['snapshot_path'],
                  snapshot_sha256='e'*64, snapshot_bytes=100,
                  continuation=dict(status='passed', max_abs_errors={'qpos': 0}, divergences=[]),
                  playback=dict(mode='playback', first_tick=8),
                  replays={mode: {'run_id': mode + '-' + source, 'report': replay_report(mode,source)}
                           for mode in ('actions','policy')})
    row.update(status='completed', first_divergence=None,
               metrics=dict(agreement=True, snapshot_sha256='e'*64, snapshot_bytes=100),
               source_manifest_sha256='d'*64, source=meta, verifier_report=report,
               paired_raw_values=_paired(report,100))


def complete_operation(row, replay):
    hashes = {'recording/manifest.json': replay['source_manifest_sha256'], 'snapshots/prefix.snp': 'e'*64}
    row.update(status='completed', timing_eligible=True, metrics={'capture_seconds': 0.1 + row['seed']},
               source=copy.deepcopy(replay['source']),
               source_row_sha256=hashlib.sha256((json.dumps(replay,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()).hexdigest(),
               source_hashes_before=hashes, source_hashes_after=copy.deepcopy(hashes), playback_tick_count=100,
               replay_reports={mode: replay_report(mode, replay['verifier_report']['source_run_id']) for mode in ('actions','policy')})


def fixture():
    protocol = load_protocol(ROOT / 'paper/studies/authority_replay_v1/protocol.json')
    identity = {'commit': 'cc57edf9f70323926237d887d766627d8c9cdd42',
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
        if row['kind'] == 'replay' and row['seed'] < 2:
            complete_replay(row, protocol)
    for row in rows:
        if row['kind'] == 'operation_cost' and row['seed'] < 2:
            complete_operation(row, next(r for r in rows if r['kind'] == 'replay' and r['seed'] == row['seed']))
    return protocol, summarize(protocol, rows), {'identity': identity, 'analysis_status': 'passed'}


class AuthorityEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (ROOT/'runs/paper-generator-tests').mkdir(parents=True, exist_ok=True)

    def builder(self):
        path = ROOT / 'paper/scripts/build_authority_evidence.py'
        self.assertTrue(path.exists(), 'authority evidence builder is not implemented')
        spec = importlib.util.spec_from_file_location('authority_builder', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_authorizes_only_exact_frozen_commit_protocol_pairs(self):
        module = self.builder()
        p,s,m = fixture()
        result = module.analyze(s,m,p)
        self.assertEqual(result['identity']['commit'], 'cc57edf9f70323926237d887d766627d8c9cdd42')
        self.assertIn(r'\newcommand{\StudyCommit}{cc57edf9f70323926237d887d766627d8c9cdd42}',
                      module.generate_outputs(result,{})['authority-claims.tex'])
        s['identity']['commit'] = 'd8658dda3fca37bb43b6dafc909114279f706f11'
        with self.assertRaises(ValueError): module.analyze(s,m,p)

    def test_accepts_archived_actual_attempt_with_its_original_protocol(self):
        module = self.builder()
        base = ROOT/'paper/evidence/authority-replay-v1/initial-attempt'
        p = load_protocol(base/'protocol.json')
        summary = json.loads((base/'summary.json').read_text())
        manifest = json.loads((base/'campaign-manifest.json').read_text())
        result = module.analyze(summary,manifest,p)
        self.assertEqual(result['declared'], 111)
        self.assertEqual(result['identity']['commit'], 'd8658dda3fca37bb43b6dafc909114279f706f11')
        macros = module.generate_outputs(result,{})['authority-claims.tex']
        self.assertIn(r'\newcommand{\StudyCommit}{d8658dda3fca37bb43b6dafc909114279f706f11}',macros)
        summary['identity']['commit'] = 'cc57edf9f70323926237d887d766627d8c9cdd42'
        manifest['identity'] = summary['identity']
        for row in summary['rows']: row['identity'] = summary['identity']
        with self.assertRaises(ValueError): module.analyze(summary,manifest,p)

    def test_counts_unknowns_and_failed_denominators(self):
        p, s, m = fixture()
        result = self.builder().analyze(s, m, p)
        self.assertEqual(result['declared'], 111)
        self.assertEqual(result['faults']['total']['baseline_false_accepts'], 1)
        self.assertEqual(result['faults']['total']['baseline_known'], 2)
        self.assertEqual(result['faults']['total']['baseline_unknown'], 1)
        self.assertEqual(result['faults']['total']['baseline_missing'], 47)
        self.assertEqual(result['faults']['total']['study_guard_detection'], 0)
        self.assertEqual(result['faults']['total']['production_detection'], 3)
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

    def test_plot_tick_labels_stay_separated_with_small_negative_and_large_tail(self):
        p,s,m = fixture()
        for row in s['rows']:
            if row['kind'] == 'execution_overhead':
                row['metrics']['wall_seconds_per_tick'] = {
                    'null':1., 'synchronous':1.68, 'background':.985, 'background_storage':2.86,
                }[row['condition']]
        module = self.builder()
        plot = module.generate_outputs(module.analyze(summarize(p,s['rows']),m,p),{})['overhead-plot.tex']
        ticks = sorted(float(y) for y in re.findall(r'\\node\[left\] at \(-0\.5,([0-9.]+)\)',plot))
        self.assertGreaterEqual(len(ticks),2)
        self.assertGreater(min(b-a for a,b in zip(ticks,ticks[1:])),.3)

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
                complete_replay(row, p)
        for row in s['rows']:
            if row['kind'] == 'operation_cost' and row['status'] == 'completed':
                complete_operation(row, next(r for r in s['rows'] if r['kind'] == 'replay' and r['seed'] == row['seed']))
        valid = summarize(p, s['rows'])
        result = module.analyze(valid, m, p)
        self.assertEqual((result['continuation']['passed'], result['replay']['passed']), (10, 5))
        for field, value in (('compared_ticks', 99), ('source_run_id', 'wrong'), ('first_divergence', {'tick': 4})):
            broken = copy.deepcopy(valid)
            replay = next(r for r in broken['rows'] if r['kind'] == 'replay')
            replay['paired_raw_values']['policy_replay']['raw'][field] = value
            with self.assertRaises(ValueError): module.analyze(summarize(p, broken['rows']), m, p)

    def test_serialized_replay_field_order_preserves_success_but_refuses_duplicates(self):
        from paper.studies.authority_replay_v1.repeatability import _paired
        module = self.builder()
        p,s,m = fixture()
        for row in s['rows']:
            if row['kind'] == 'replay' and row['status'] == 'completed':
                row['verifier_report']['continuation']['max_abs_errors'] = {'tick': 0, 'episode': 0, 'action': 0}
                row['paired_raw_values'] = _paired(row['verifier_report'],100)
        for row in s['rows']:
            if row['kind'] == 'operation_cost' and row['status'] == 'completed':
                complete_operation(row,next(r for r in s['rows'] if r['kind'] == 'replay' and r['seed'] == row['seed']))
        serialized = json.loads(json.dumps(summarize(p,s['rows']),sort_keys=True))
        replay = next(r for r in serialized['rows'] if r['kind'] == 'replay')
        self.assertEqual(list(replay['verifier_report']['continuation']['max_abs_errors']), ['action','episode','tick'])
        self.assertEqual(replay['paired_raw_values']['branch']['validated_fields'], ['tick','episode','action'])
        result = module.analyze(serialized,m,p)
        self.assertEqual(result['replay']['passed'], 2)
        replay['paired_raw_values']['branch']['validated_fields'].append('tick')
        with self.assertRaises(ValueError): module.analyze(summarize(p,serialized['rows']),m,p)

    def test_rejects_replay_assertions_disagreeing_with_verifier_evidence(self):
        module = self.builder()
        for mutation in ('branch', 'playback_mode', 'playback_tick', 'failed_replay', 'other_source', 'raw_flags', 'numeric_flags'):
            with self.subTest(mutation=mutation):
                p,s,m = fixture()
                row = next(r for r in s['rows'] if r['kind'] == 'replay')
                report = row['verifier_report']
                if mutation == 'branch': report['continuation']['divergences'] = [{'tick': 4}]
                elif mutation == 'playback_mode': report['playback']['mode'] = 'actions'
                elif mutation == 'playback_tick': report['playback']['first_tick'] = 99
                elif mutation == 'failed_replay': report['replays']['policy']['report']['status'] = 'failed'
                elif mutation == 'other_source': report['replays']['actions']['report']['source_run_id'] = 'other'
                elif mutation == 'raw_flags':
                    row['paired_raw_values']['policy_replay']['raw']['inference_executed'] = False
                elif mutation == 'numeric_flags':
                    row['paired_raw_values']['policy_replay']['raw']['inference_executed'] = 1
                with self.assertRaises(ValueError): module.analyze(summarize(p,s['rows']),m,p)

    def test_rejects_completed_operations_with_invalid_retained_source(self):
        module = self.builder()
        for mutation in ('seed', 'null', 'source_hashes', 'manifest', 'snapshot', 'source_row', 'failed_policy', 'ticks', 'flags', 'other_source', 'wrong_mode'):
            with self.subTest(mutation=mutation):
                p,s,m = fixture()
                row = next(r for r in s['rows'] if r['kind'] == 'operation_cost')
                if mutation == 'seed': row['source']['seed'] = 999
                elif mutation == 'null': row['source']['condition'] = 'null'
                elif mutation == 'source_hashes': row['source_hashes_after']['new'] = 'f'*64
                elif mutation == 'manifest':
                    row['source_hashes_before']['recording/manifest.json'] = 'f'*64
                    row['source_hashes_after']['recording/manifest.json'] = 'f'*64
                elif mutation == 'snapshot':
                    row['source_hashes_before']['snapshots/prefix.snp'] = 'f'*64
                    row['source_hashes_after']['snapshots/prefix.snp'] = 'f'*64
                elif mutation == 'source_row': row['source_row_sha256'] = 'f'*64
                elif mutation == 'failed_policy': row['replay_reports']['policy']['status'] = 'failed'
                elif mutation == 'ticks': row['replay_reports']['actions']['compared_ticks'] = 99
                elif mutation == 'flags': row['replay_reports']['policy']['controller_reexecuted'] = False
                elif mutation == 'other_source': row['replay_reports']['policy']['source_run_id'] = 'other'
                elif mutation == 'wrong_mode': row['replay_reports']['policy']['mode'] = 'actions'
                with self.assertRaises(ValueError): module.analyze(summarize(p,s['rows']),m,p)

    def test_failed_operation_metrics_are_retained_but_excluded(self):
        p,s,m = fixture()
        row = next(r for r in s['rows'] if r['kind'] == 'operation_cost')
        row.update(status='failed', source={'seed': 999}, replay_reports={})
        result = self.builder().analyze(summarize(p,s['rows']),m,p)
        self.assertEqual(result['operations']['capture_seconds']['n'], 1)
        self.assertEqual(len(result['operation_rows']), 5)
        self.assertEqual(result['operation_rows'][0]['metrics']['capture_seconds'], 0.1)

    def snapshot_fixture(self, root):
        import numpy as np
        p,s,m = fixture()
        for row in s['rows']:
            if row.get('case_id') != 'S1': continue
            folder = root / f"fault__S1__default__fault__seed-{row['seed']}"
            folder.mkdir()
            arrays = {}
            for label in ('expected','pose','full'):
                arrays[label+'__ticks'] = np.array(1,np.int64)
                arrays[label+'__0__action'] = np.array([1,2] if label != 'pose' else [2,4],np.float32)
                arrays[label+'__0__qpos'] = np.array([3,4],np.float64)
                arrays[label+'__0__revision'] = np.array(2 if label == 'pose' else 1,np.int64)
            path = folder/'continuation-pairs.npz'
            np.savez(path,**arrays)
            divergence = dict(field='action',tick=0,reason='value')
            row.update(status='completed',trace=dict(arrays_path=path.name,
                arrays_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),comparison_origin_tick=8,
                scientific_first_divergence=divergence,full_scientific_first_divergence=None,
                comparisons=dict(scientific_first_divergence=divergence,full_scientific_first_divergence=None)))
        return p,summarize(p,s['rows']),m

    def test_optional_snapshot_table_and_unchanged_base_outputs(self):
        module = self.builder()
        with tempfile.TemporaryDirectory(dir=ROOT/'runs/paper-generator-tests') as tmp:
            root = Path(tmp)
            p,s,m = self.snapshot_fixture(root)
            result = module.analyze(s,m,p)
            base = module.generate_outputs(result,{})
            outputs = module.generate_outputs(result,{},trace_root=root)
            self.assertEqual({k:v for k,v in outputs.items() if k != 'snapshot-ablation.tex'},base)
            table = outputs['snapshot-ablation.tex']
            self.assertIn('Pose: velocity cmd.',table)
            self.assertIn('Pose: heading (rad)',table)
            self.assertIn('2',table)
            for row in s['rows']:
                if row.get('case_id') == 'S1': self.assertIn(row['trace']['arrays_sha256'],table)
            values = module.analyze_snapshot_ablation(result,root)
            self.assertEqual([row['pose_action_error'] for row in values],[2,2,2])
            self.assertEqual([row['pose_velocity_error'] for row in values],[1,1,1])
            self.assertEqual([row['pose_heading_error'] for row in values],[2,2,2])
            self.assertEqual([row['full_action_error'] for row in values],[0,0,0])

    def test_snapshot_input_tamper_nonfinite_shape_and_escape_refused(self):
        import numpy as np
        module = self.builder()
        for mutation in ('tamper','nonfinite','shape','escape','symlink','ticks','full_diverged','object','missing','origin','trace_oracle'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory(dir=ROOT/'runs/paper-generator-tests') as tmp:
                root=Path(tmp);p,s,m=self.snapshot_fixture(root)
                row=next(r for r in s['rows'] if r.get('case_id') == 'S1')
                path=root/'fault__S1__default__fault__seed-0/continuation-pairs.npz'
                if mutation == 'escape': row['trace']['arrays_path'] = '../../continuation-pairs.npz'
                elif mutation == 'tamper': path.write_bytes(path.read_bytes()+b'changed')
                elif mutation == 'missing': path.unlink()
                elif mutation == 'symlink':
                    outside=root/'outside.npz';path.rename(outside);path.symlink_to(outside)
                elif mutation == 'origin': row['trace']['comparison_origin_tick']=9
                elif mutation == 'trace_oracle': row['trace']['scientific_first_divergence']['field']='qpos'
                else:
                    with np.load(path,allow_pickle=False) as loaded: arrays={key:loaded[key] for key in loaded.files}
                    if mutation == 'nonfinite': arrays['pose__0__qpos'][0]=float('nan')
                    elif mutation == 'shape': arrays['pose__0__action']=np.array([2,4,6],np.float32)
                    elif mutation == 'ticks': arrays['pose__ticks']=np.array(2,np.int64)
                    elif mutation == 'full_diverged': arrays['full__0__action'][0]+=1
                    elif mutation == 'object': arrays['pose__0__qpos']=np.array([object()],dtype=object)
                    np.savez(path,**arrays)
                    row['trace']['arrays_sha256']=hashlib.sha256(path.read_bytes()).hexdigest()
                result=module.analyze(summarize(p,s['rows']),m,p)
                with self.assertRaises(ValueError): module.analyze_snapshot_ablation(result,root)

    def test_snapshot_incomplete_rows_remain_not_estimable(self):
        module=self.builder();p,s,m=fixture()
        s['rows'][next(i for i,r in enumerate(s['rows']) if r.get('case_id')=='S1')]['status']='failed'
        result=module.analyze(summarize(p,s['rows']),m,p)
        with tempfile.TemporaryDirectory(dir=ROOT/'runs/paper-generator-tests') as tmp:
            rows=module.analyze_snapshot_ablation(result,Path(tmp))
            self.assertEqual(len(rows),3)
            self.assertTrue(all(row['pose_action_error'] is None for row in rows))
            self.assertIn('not estimable',module.generate_outputs(result,{},trace_root=Path(tmp))['snapshot-ablation.tex'])

    def test_detection_partition_distinguishes_interface_diagnostic_and_label(self):
        module=self.builder();p,s,m=fixture()
        for row in s['rows']:
            if row['kind']=='fault': row['explicit_detection']=row['case_id'] in ('S1','B2','R1','R2','A2')
        counts=module.analyze(summarize(p,s['rows']),m,p)['faults']['total']
        self.assertEqual((counts['production_detection'],counts['diagnostic_detection'],counts['study_guard_detection']),(3,6,6))

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
