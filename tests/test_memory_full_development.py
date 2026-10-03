"""Pure fixed-profile admission; no writer lease, recorded data or model jobs."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from palimpsest import memory, memory_task


class FullDevelopment(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_memory_counterbalance_comparison import CounterbalanceComparison
        CounterbalanceComparison.setUpClass()
        cls.fixture = CounterbalanceComparison()
        cls.fixture.runner = CounterbalanceComparison.runner
        cls.r = cls.fixture.runner
        cls.a = cls.r.admission
        cls.repo = Path(__file__).resolve().parents[1]

    def identity(self):
        return {'fixture': True, 'driver_sha256': self.r.common._hash(Path(self.r.__file__)),
                'admission_helper_sha256': self.r.common._hash(self.r.HELPER)}

    def lineage(self, root, name):
        return {'version': 1, 'protocol_sha256': self.a.profile_digest(name),
                'plan_path': str(root/'admission-plan.json'), 'plan_sha256': 'a'*64,
                'report_path': str(root/'admission-report.json'), 'report_sha256': 'b'*64}

    def histories(self, cell):
        histories = self.fixture.fixture(cell)[-1]
        for h in histories.values():
            h['path'] = 'fixture-history.json'
        return histories

    def test_exact_complement_and_historical_protocol_bytes(self):
        a, r = self.a, self.r
        remaining = [cell for chunk in a.REMAINING_CHUNKS for cell in chunk]
        matrix = {(s, relation, kind) for s in range(24, 32)
                  for relation in memory.RELATIONS for kind in a.experiment.KINDS}
        self.assertEqual(len(remaining), 40)
        self.assertEqual(len(set(remaining)), 40)
        self.assertEqual(set(remaining), matrix-set(a.CELLS))
        self.assertEqual(remaining, sorted(matrix-set(a.CELLS), key=lambda c:
            (c[0], memory.RELATIONS.index(c[1]), a.experiment.KINDS.index(c[2]))))
        self.assertEqual(a.PROTOCOL_SHA256,
            '85f6ec028aefa4d02a4c61701452f2a5275f57744786adf8670ec238960ee214')
        self.assertEqual(r.PROTOCOL_SHA256,
            'bedda73b18ac5525b3ea4e667aa505d22d47decefac016947b190024337db134')
        self.assertEqual(r.C4_PROTOCOL_SHA256,
            '0ba97822d76ad34f7cea3662dac5cf7bfea5f7df68fba6b72f78945fab5653a3')
        self.assertEqual(a.fixed_profile(), (a.CELLS, a.PROTOCOL))
        self.assertEqual(r.fixed_profile(), (r.CELLS, r.PROTOCOL))
        self.assertEqual(r.admission_pins(None), (r.B_PLAN_SHA256, r.B_REPORT_SHA256))
        self.assertEqual(r.PROTOCOL['admission_helper_sha256'], r.LEGACY_ADMISSION_HELPER_SHA256)
        self.assertNotEqual(r.common._hash(r.HELPER), r.LEGACY_ADMISSION_HELPER_SHA256)
        for runner in (a, r):
            with self.assertRaisesRegex(ValueError, 'profile'):
                runner.profile_digest('remaining-11')
            with self.assertRaisesRegex(ValueError, 'protocol|profile'):
                runner.fixed_profile('f'*64)

    def test_real_admission_validators_bind_ten_fixed_chunks(self):
        a = self.a
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(a, 'source_identity', return_value={'fixture': True}):
            root = Path(directory)
            for name, cells in zip(a.REMAINING_NAMES, a.REMAINING_CHUNKS):
                digest = a.profile_digest(name)
                plan = a.make_plan(self.repo, root/'assets', root/name, protocol_sha256=digest)
                original = copy.deepcopy(plan)
                self.assertEqual(a.validate_plan(plan), plan)
                self.assertEqual(plan, original)
                self.assertEqual([j['cell'] for j in plan['jobs'][::3]], [list(c) for c in cells])
                self.assertEqual(len(plan['jobs']), 12)
                self.assertEqual(plan['protocol']['max_numeric_ticks'], 1204)
                self.assertEqual(plan['protocol']['outer_timeout_seconds'], 1980)
                self.assertEqual(plan['protocol']['aggregate_max_bytes'], 6*a.GiB)
                self.assertEqual(len(plan['coverage']), 48)
                self.assertTrue(all(f['status']=='unknown' and f['evidence'] is None
                    for j in plan['jobs'] for f in j['case']['facts']))
                self.assertTrue(all(j['snapshot_path'] is None for j in plan['jobs']))
                for mutate in (
                    lambda p: p['jobs'][0].update(repo=str(root/'wrong-repo')),
                    lambda p: p['jobs'][0].update(cell=list(a.CELLS[0])),
                    lambda p: p['jobs'][0].update(snapshot_path=str(root/'injected.snp')),
                    lambda p: p['protocol'].update(version=True),
                    lambda p: p['jobs'].reverse(),
                ):
                    bad = copy.deepcopy(plan); mutate(bad)
                    with self.assertRaises(ValueError):
                        a.validate_plan(bad)

    def test_comparison_validators_separate_lineage_from_current_executor(self):
        r = self.r
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, cells in zip(self.a.REMAINING_NAMES, self.a.REMAINING_CHUNKS):
                digest = r.profile_digest(name); lineage = self.lineage(root, name)
                bindings = {self.a.cell_key(c): {'cell': list(c), 'case': self.a.make_case(c),
                    **{k: lineage[k] for k in ('plan_path', 'plan_sha256', 'report_path', 'report_sha256')}}
                    for c in cells}
                histories = self.histories(cells[0]); original = copy.deepcopy(histories)
                with patch.object(r, 'load_bindings', return_value=bindings), \
                        patch.object(r.common, 'load_histories', return_value=histories), \
                        patch.object(r, 'source_identity', return_value=self.identity()):
                    plan = r.make_plan(self.repo, root/'assets', root/'out', root/'history',
                        Path(lineage['plan_path']), Path(lineage['report_path']),
                        protocol_sha256=digest, admission_lineage=lineage)
                    self.assertEqual(r.validate_plan(plan), plan)
                    self.assertEqual(len(plan['jobs']), 40)
                    self.assertEqual(plan['protocol']['max_numeric_ticks'], 10800)
                    self.assertEqual(plan['protocol']['aggregate_max_bytes'], 10*r.GiB)
                    self.assertEqual(plan['protocol']['admission_helper_sha256'], r.common._hash(r.HELPER))
                    self.assertIsNone(plan['protocol']['admission_plan_sha256'])
                    for cell in cells:
                        mapped = r.histories_for(cell, histories)
                        shared = r.selector_config('anchor', mapped, protocol_sha256=digest)
                        for stage in r.STAGES:
                            proof = {'gold_target_ids': []} if stage=='oracle' else None
                            config = r.selector_config(stage, mapped, proof, protocol_sha256=digest)
                            run_id = f'{r.STAGES.index(stage)+1:032x}'
                            job = {'repo': str(self.repo), 'assets': str(root/'assets'),
                                'history_root': str(root/'history'), 'root_output': str(root/'out'),
                                'output': str(root/'out/runs'/run_id), 'run_id': run_id,
                                'cell': list(cell), 'stage': stage, 'binding': bindings[self.a.cell_key(cell)],
                                'protocol_sha256': digest, 'source_identity': self.identity(),
                                'history_inputs': r.history_pins(root/'history', histories),
                                'snapshot_path': str(root/'initial.snp'), 'snapshot_sha256': 'c'*64,
                                'expected_non_u': {'fixture': True}, 'selector': config,
                                'oracle_evidence': proof, 'admission_lineage': lineage}
                            self.assertEqual(r.validate_job(job), job)
                            if stage in ('anchor', *r.CORE_CONDITIONS):
                                self.assertEqual(config, shared)
                            self.assertEqual(config['resource'], mapped['own']['e'] if stage=='retrieval'
                                             else [] if stage=='oracle' else None)
                    for mutate in (
                        lambda p: p.pop('admission_lineage'),
                        lambda p: p['admission_lineage'].update(protocol_sha256=self.a.PROTOCOL_SHA256),
                        lambda p: p['source_identity'].update(admission_helper_sha256=r.LEGACY_ADMISSION_HELPER_SHA256),
                        lambda p: p['source_identity'].update(driver_sha256='f'*64),
                        lambda p: p['bindings'][self.a.cell_key(cells[0])].update(plan_sha256='f'*64),
                        lambda p: p['bindings'][self.a.cell_key(cells[0])].update(report_path=str(root/'other-report')),
                        lambda p: p['jobs'][0].update(cell=list(r.CELLS[0])),
                    ):
                        bad = copy.deepcopy(plan); mutate(bad)
                        with self.assertRaises(ValueError):
                            r.validate_plan(bad)
                self.assertEqual(histories, original)
            with self.assertRaisesRegex(ValueError, 'Historical'):
                r.validate_lineage(lineage, r.C4_PROTOCOL_SHA256)

    def test_real_pinned_plan_report_join_rejects_wrong_chunk_or_probe(self):
        a, r = self.a, self.r; name = a.REMAINING_NAMES[0]
        digest = r.profile_digest(name)
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(a, 'source_identity', return_value={'fixture': True}):
            root = Path(directory)
            plan = a.make_plan(self.repo, root/'assets', root/'out', protocol_sha256=a.profile_digest(name))
            terminal = {'status': 'admission_checked', 'source_unchanged': True, 'retained_unchanged': True,
                'protocol_sha256': plan['protocol_sha256'], 'source_identity': plan['source_identity'],
                'final_source_identity': plan['source_identity'], 'unattempted_stages': [],
                'runs': [{'cell': a.cell_key(j['cell']), 'stage': j['stage'], 'run_id': j['run_id'],
                    'run_path': j['output'], 'admission_pass': True, 'final_phase': 'paused',
                    'supervisor': {'status': 'completed', 'returncode': 0}} for j in plan['jobs']]}
            for filename, value in (('plan.json', plan), ('report.json', terminal)):
                path = root/filename; path.write_text(json.dumps(value))
                self.assertEqual(r.pinned_json(path, r.common._hash(path)), value)
                with self.assertRaisesRegex(ValueError, 'hash differs'):
                    r.pinned_json(path, 'f'*64)
            plan = a.validate_plan(plan)
            cell = a.REMAINING_CHUNKS[0][0]
            self.assertEqual(r.derive_anchor(plan, terminal, cell, protocol_sha256=digest)
                             ['policy-anchor'][0]['stage'], 'policy-anchor')
            bad = copy.deepcopy(terminal); bad['runs'][1]['run_id'] = bad['runs'][2]['run_id']
            with self.assertRaisesRegex(ValueError, 'substituted'):
                r.derive_anchor(plan, bad, cell, protocol_sha256=digest)
            with self.assertRaisesRegex(ValueError, 'another fixed chunk'):
                r.derive_anchor(plan, terminal, cell, protocol_sha256=r.profile_digest('remaining-02'))
            lineage = self.lineage(root, name)
            binding = {k: lineage[k] for k in ('plan_path', 'plan_sha256', 'report_path', 'report_sha256')}
            r.validate_binding_lineage(binding, digest, lineage)
            bad = copy.deepcopy(binding); bad['report_sha256'] = 'f'*64
            with self.assertRaisesRegex(ValueError, 'lineage'):
                r.verify_binding(bad, protocol_sha256=digest, admission_lineage=lineage)

    def test_new_core_uses_full_invariants_without_reconfiguration(self):
        r = self.r
        for name in self.a.REMAINING_NAMES:
            digest = r.profile_digest(name)
            for stage in r.CORE_CONDITIONS:
                job, native, ancestor, events, histories = self.fixture.strict_fixture(stage)
                config = r.selector_config('anchor', histories, protocol_sha256=digest)
                for state in (ancestor, native):
                    state['application']['memory'] = memory_task.configure_selector(state['application']['memory'], config)
                job.update(protocol_sha256=digest, selector=config, expected_non_u=r.invariant_hashes(ancestor))
                job['binding']['non_u'] = r.common.baseline_invariants(ancestor)
                events[1]['invariant_hashes'] = job['expected_non_u']
                self.assertEqual(r.validate_selector_boundary(job, native, ancestor, events, histories),
                                 native['application']['memory'])
                for field in ('m', 'e', 'initial_m', 'detector', 'cursor', 'requests', 'active',
                              'last_decisions', 'selector', 'version'):
                    bad = copy.deepcopy(native); bad['application']['memory'][field] = {'changed': True}
                    self.assertNotEqual(r.branch_invariants(bad, job), job['expected_non_u'], field)
                for field in ('integration', 'policy', 'rng'):
                    bad = copy.deepcopy(native); bad[field] = {'changed': True}
                    self.assertNotEqual(r.branch_invariants(bad, job), job['expected_non_u'], field)
                bad = copy.deepcopy(native); bad['application']['memory']['u'] = memory.artifact(method='empty-v1')
                if stage!='no-U':
                    with self.assertRaisesRegex(ValueError, 'artifact'):
                        r.validate_selector_boundary(job, bad, ancestor, events, histories)
                with self.assertRaisesRegex(ValueError, 'inherit'):
                    r.validate_selector_boundary(job, native, ancestor,
                        [*events, {'kind': 'selector_configured'}], histories)

    def test_null_no_event_and_passive_correction_keep_existing_readouts(self):
        r = self.r
        for name, cells in zip(self.a.REMAINING_NAMES, self.a.REMAINING_CHUNKS):
            digest = r.profile_digest(name)
            for cell in cells:
                # The pure fixture is declared synthetic evidence, never a live bank seed.
                case, native, report, data, histories = self.fixture.fixture(cell, protocol_sha256=digest)
                state = native['application']['memory']
                trigger, selections = r.observed_trigger(state, data, case)
                before = r.common.occupancy(case, report['before_circles'])
                after = r.common.occupancy(case, report['after_circles'])
                gold = r.experiment.gold_target_ids(state['m'], before, after, trigger)
                scores = r.common.score_nine(state['m'], trigger, histories, gold)
                self.assertEqual(len(scores), 9)
                self.assertEqual(len(gold), int(cell[2]=='change'))
                row = r.condition_readout(case, state['m'], trigger, scores[0], data, report, after)
                self.assertEqual(row['selector_invocations'], int(cell[2]!='no-event'))
                self.assertIsNone(row['goal_tick'])
                self.assertIsNone(row['worker_task_pass'])
                if cell[2]=='no-event':
                    self.assertEqual((trigger, selections), (None, []))
                    self.assertEqual(row['selector_behavior_bytes'], 0)
                    self.assertTrue(all(s['behavior_input_bytes']==0 for s in scores))
                elif cell[2]=='null':
                    self.assertTrue(all(not t['stale_value_changed'] for t in row['timing']))
                    self.assertTrue(all(t['first_stale_value_correction_tick'] is None for t in row['timing']))


if __name__ == '__main__':
    unittest.main()
