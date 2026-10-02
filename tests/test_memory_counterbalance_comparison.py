"""Pure Stage C linkage fixtures; no recorded-data or model dependency."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
import tempfile
from types import SimpleNamespace

from palimpsest import memory


class CounterbalanceComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location('counterbalance_comparison',
            cls.repo / 'scripts/verify_memory_counterbalance_comparison.py')
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)

    def joined_fixture(self):
        r = self.runner
        jobs, rows = [], []
        for n, cell in enumerate(r.admission.CELLS):
            for s, stage in enumerate(r.admission.STAGES):
                run_id = f'{n * 3 + s + 1:032x}'
                output = '/fixture/runs/' + run_id
                jobs.append({'cell': list(cell), 'stage': stage, 'run_id': run_id, 'output': output})
                rows.append({'cell': r.admission.cell_key(cell), 'stage': stage, 'run_id': run_id,
                    'run_path': output, 'admission_pass': True, 'final_phase': 'paused',
                    'supervisor': {'status': 'completed', 'returncode': 0}})
        plan = {'jobs': jobs, 'protocol_sha256': memory.sha256('fixture'), 'source_identity': {'fixture': True}}
        report = {'status': 'admission_checked', 'runs': rows, 'source_unchanged': True,
            'retained_unchanged': True, 'protocol_sha256': plan['protocol_sha256'],
            'source_identity': plan['source_identity'], 'final_source_identity': plan['source_identity'],
            'unattempted_stages': []}
        return plan, report

    def test_unique_plan_report_join_rejects_probe_and_other_case_source(self):
        r = self.runner
        plan, report = self.joined_fixture()
        for cell in r.CELLS:
            joined = r.derive_anchor(plan, report, cell)
            self.assertEqual(joined['policy-anchor'][0]['stage'], 'policy-anchor')
            self.assertEqual(joined['policy-anchor'][0]['cell'], list(cell))
            for replacement in (joined['probe'][1], report['runs'][3]):
                altered = copy.deepcopy(report)
                target = next(v for v in altered['runs'] if v['cell'] == r.admission.cell_key(cell)
                              and v['stage'] == 'policy-anchor')
                target.update(run_id=replacement['run_id'], run_path=replacement['run_path'])
                with self.assertRaisesRegex(ValueError, 'substituted'):
                    r.derive_anchor(plan, altered, cell)
        altered = copy.deepcopy(report)
        altered['runs'].append(copy.deepcopy(altered['runs'][1]))
        with self.assertRaisesRegex(ValueError, 'not unique'):
            r.derive_anchor(plan, altered, r.CELLS[0])
        altered = copy.deepcopy(report); altered['source_unchanged'] = 1
        with self.assertRaises(ValueError): r.derive_anchor(plan, altered, r.CELLS[0])

    def test_policy_boundary_requires_zero_rows_and_last_sensor_299(self):
        r = self.runner
        case = {'fixture': 'not acquired evidence'}
        state = {'version': 1, 'cursor': {'tick': 299}, 'detector': {'tick': 299},
            'u': memory.artifact(method='empty-v1'), 'e': {'episodes': []},
            'requests': [], 'active': None}
        data = {'rows': [], 'events': [], 'manifest': {'controller': 'flynn', 'requested_device': 'cpu'}}
        native = {'application': {'memory': state, 'controller': 'flynn', 'execution_mode': 'live',
            'phase': 'paused', 'episode': 0, 'episode_step': 300, 'total_tick': 300,
            'controller_tensors': {'fixture': True}, 'world_task_state': {'case': case, 'applied': False}},
            'policy': {'fixture': True}, 'identity': {'policy': {'device': 'cpu'}}}
        with patch.object(r.memory_task, 'validate_state', side_effect=lambda x: copy.deepcopy(x)):
            self.assertEqual(r.policy_boundary(data, native, case), state)
            changes = [('rows', [300]), ('event', {'kind': 'selector_configured'}),
                       ('memory_tick', 300), ('device', 'cuda'), ('case', {'other': 'case'})]
            for name, value in changes:
                d, n = copy.deepcopy(data), copy.deepcopy(native)
                if name == 'rows': d['rows'] = value
                elif name == 'event': d['events'].append(value)
                elif name == 'memory_tick': n['application']['memory']['cursor']['tick'] = value
                elif name == 'device': n['identity']['policy']['device'] = value
                else: n['application']['world_task_state']['case'] = value
                with self.assertRaisesRegex(ValueError, 'zero-row pre-event'):
                    r.policy_boundary(d, n, case)

    def test_binding_rejects_missing_duplicate_pins_and_forged_before_geometry(self):
        r = self.runner; plan, terminal = self.joined_fixture(); digest = 'a'*64
        cell = r.CELLS[0]; key = r.admission.cell_key(cell); plan['output'] = '/fixture'
        for job in plan['jobs']: job['case'] = {'fixture': 'no actual geometry'}
        for row in terminal['runs']:
            row.update(snapshot_sha256=digest, worker_report_sha256=digest,
                initial_non_u={'fixture': True}, files=[{'path':'recording/manifest.json','bytes':1,'sha256':digest}])
        joined = r.derive_anchor(plan, terminal, cell); anchor, summary = joined['policy-anchor']
        paths = []
        for job, row in joined.values():
            run = Path(job['output'])
            paths.extend([str(run/'recording/manifest.json'), f"/fixture/{job['run_id']}-job.json",
                str(run/'admission-worker.json'), str(run/'snapshots/initial.snp'), str(run/'snapshots/index.json')])
        before = [[-1., 1., .2]]
        binding = {'cell':list(cell),'run_id':anchor['run_id'],'case':anchor['case'],
            'snapshot_path':str(Path(anchor['output'])/'snapshots/initial.snp'), 'snapshot_sha256':digest,
            'non_u':summary['initial_non_u'],'before_circles':before,
            'plan_path':'/fixture/plan.json','plan_sha256':r.B_PLAN_SHA256,
            'report_path':'/fixture/report.json','report_sha256':r.B_REPORT_SHA256,
            'pins':[{'path':p,'sha256':digest} for p in paths]}
        def pinned(path, *_):
            return plan if str(path)==binding['plan_path'] else terminal if str(path)==binding['report_path'] else {'before_circles':before}
        with patch.object(r,'pinned_json',side_effect=pinned), patch.object(r.admission,'validate_plan',side_effect=lambda p:p), \
                patch.object(r.common,'_hash',return_value=digest), patch.object(r.common,'read_run',return_value={}), \
                patch.object(r,'_initial_snapshot',return_value=({'fixture':True},{'sha256':digest},[])), \
                patch.object(r,'policy_boundary'):
            self.assertEqual(r.verify_binding(binding), {'fixture':True})
            changed = copy.deepcopy(binding); changed['pins'].pop()
            with self.assertRaisesRegex(ValueError,'path coverage'): r.verify_binding(changed)
            changed = copy.deepcopy(binding); changed['pins'].append(changed['pins'][0])
            with self.assertRaisesRegex(ValueError,'path coverage'): r.verify_binding(changed)
            changed = copy.deepcopy(binding); changed['before_circles'][0][0] = 99.
            with self.assertRaisesRegex(ValueError,'hash-pinned admission worker'): r.verify_binding(changed)

    def fixture(self, cell, condition='own'):
        """Synthetic sensor/retained-M fixture only, never an acquired recording."""
        from tests.test_memory_counterbalance import CounterbalanceAdmission
        from palimpsest import memory_task
        base = CounterbalanceAdmission(); base.runner = self.runner.admission
        case, native, report, data = base.fixture(cell)
        state = native['application']['memory']
        state.pop('selector'); state['version'] = 1
        histories = {'own':{'e':{'version':1,'episodes':[]},'u':memory.artifact(cell[1]),'sha256':'a'*64},
            'swapped':{'e':{'version':1,'episodes':[]},'u':memory.artifact(memory.RELATIONS[1-memory.RELATIONS.index(cell[1])]),'sha256':'b'*64}}
        state['u'] = self.runner.common.condition_u(condition,histories)
        config = self.runner.selector_config(condition,histories, {'gold_target_ids':[]} if condition=='oracle' else None)
        state = memory_task.configure_selector(state,config)
        native['application']['memory'] = state
        packet = data['events'][0]['packet']
        final, _, decisions = memory_task.advance_memory(state,packet)
        data['events'] = [data['events'][0]] + [{'kind':'memory_decision','episode':0,'episode_step':300,
            'tick':300,'detail':v} for v in decisions]
        data['manifest'] = {'status':'completed'}
        report.update(final_memory=final,steps=301,final_phase='paused',outcome=None,task_pass=None)
        return case,native,report,data,histories

    def test_change_null_no_event_accounting_and_confirmation_censoring(self):
        r = self.runner
        for cell in r.CELLS:
            case,native,report,data,histories = self.fixture(cell)
            state = native['application']['memory']; before = r.common.occupancy(case,report['before_circles'])
            after = r.common.occupancy(case,report['after_circles'])
            trigger,selections = r.observed_trigger(state,data,case)
            gold = r.experiment.gold_target_ids(state['m'],before,after,trigger)
            scores = r.common.score_nine(state['m'],trigger,histories,gold)
            score = next(v for v in scores if v['condition']=='own')
            row = r.condition_readout(case,state['m'],trigger,score,data,report,after)
            self.assertEqual(len(gold),int(cell[2]=='change'))
            self.assertEqual(row['selector_invocations'],int(cell[2]!='no-event'))
            self.assertEqual(row['selector_behavior_bytes']==0,cell[2]=='no-event')
            self.assertIsNone(row['goal_tick'])
            upper = next(t for t in row['timing'] if t['fact_id']==next(
                f['id'] for f in case['facts'] if f['subject_id']==case['subjects_by_side'][1]))
            self.assertEqual(upper['first_confirmation_tick'],300)
            self.assertIsNone(upper['first_stale_value_correction_tick'])
            lower = next(t for t in row['timing'] if t is not upper)
            self.assertIsNone(lower['first_correct_committed_tick'])
            if cell[2] in ('change','null'):
                self.assertTrue(lower['uncertainty_intervals'][-1]['censored'])
                self.assertIsNone(lower['uncertainty_intervals'][-1]['end_tick'])
            if cell[2]=='null': self.assertFalse(lower['stale_value_changed'])
            if cell[2]=='no-event':
                self.assertEqual(selections,[])
                self.assertTrue(all(s['behavior_input_bytes']==0 for s in scores))
                changed = copy.deepcopy(data)
                changed['events'].append({'kind':'memory_decision','episode':0,'episode_step':300,'tick':300,
                    'detail':{'kind':'memory_selection','selection':score['selection']}})
                with self.assertRaisesRegex(ValueError,'invocation'): r.observed_trigger(state,changed,case)
            else:
                changed = copy.deepcopy(data)
                found = next(e for e in changed['events'] if e['kind']=='memory_decision' and e['detail']['kind']=='memory_trigger')
                found['detail']['trigger']['before_observation_id'] = 'forged-observation'
                with self.assertRaisesRegex(ValueError,'invocation'): r.observed_trigger(state,changed,case)

    def test_fixed_plan_and_resource_access_use_shared_selectors(self):
        r = self.runner
        bindings = {r.admission.cell_key(c):{'cell':list(c),'case':r.admission.make_case(c)} for c in r.CELLS}
        histories = self.fixture(r.CELLS[0])[-1]
        for h in histories.values(): h['path']='fixture-history.json'
        with tempfile.TemporaryDirectory() as root, patch.object(r,'load_bindings',return_value=bindings), \
                patch.object(r.common,'load_histories',return_value=histories), \
                patch.object(r,'source_identity',return_value={'fixture':True}):
            plan = r.make_plan(self.repo,Path(root)/'assets',Path(root)/'output',Path(root)/'history',
                Path(root)/'B-plan.json',Path(root)/'B-report.json')
            self.assertEqual(r.validate_plan(plan),plan)
            self.assertEqual(len(plan['jobs']),40)
            self.assertEqual(len({j['run_id'] for j in plan['jobs']}),40)
            self.assertEqual(plan['protocol']['max_numeric_ticks'],10800)
            self.assertEqual(plan['protocol']['outer_timeout_seconds'],6460)
            self.assertEqual(plan['protocol']['aggregate_max_bytes'],10*1024**3)
            altered = copy.deepcopy(plan); altered['jobs'][1]['stage']='oracle'
            with self.assertRaises(ValueError): r.validate_plan(altered)
            altered = copy.deepcopy(plan); altered['protocol']['version']=True
            with self.assertRaises(ValueError): r.validate_plan(altered)
            altered = copy.deepcopy(plan)
            altered['bindings'][r.admission.cell_key(r.CELLS[0])]['case']['version']=True
            with self.assertRaises(ValueError): r.validate_plan(altered)
        snapshot = copy.deepcopy(histories)
        for condition in r.common.CONDITIONS:
            config = r.selector_config(condition,histories,{'gold_target_ids':[]} if condition=='oracle' else None)
            self.assertEqual(config['limit'],1)
            self.assertEqual(config['resource'],histories['own']['e'] if condition=='retrieval' else [] if condition=='oracle' else None)
        self.assertEqual(histories,snapshot)
        self.assertEqual(r.histories_for(r.CELLS[1],histories)['own'],histories['swapped'])

    def test_pre_next_owner_failure_preserves_prior_completion(self):
        r = self.runner; histories = self.fixture(r.CELLS[0])[-1]
        for h in histories.values(): h['path']='fixture-history.json'
        bindings = {r.admission.cell_key(c):{'cell':list(c),'case':r.admission.make_case(c),
            'snapshot_path':'/fixture/initial.snp','snapshot_sha256':'a'*64,'non_u':{'fixture':True},
            'plan_path':'/fixture/plan.json','report_path':'/fixture/report.json'} for c in r.CELLS}
        def original(binding):
            return {'application':{'memory':{'m':memory.seed_m(binding['case']['facts'],[])}}}
        calls = []
        def validate(job):
            calls.append(job['stage'])
            if job['stage']=='own': raise ValueError('fixture before-owner rejection')
            return job
        with tempfile.TemporaryDirectory() as root, patch.object(r,'load_bindings',return_value=bindings), \
                patch.object(r.common,'load_histories',return_value=histories), \
                patch.object(r,'source_identity',return_value={'fixture':True}), \
                patch.object(r,'verify_binding',side_effect=original), \
                patch.object(r.shutil,'disk_usage',return_value=SimpleNamespace(free=16*r.GiB)), \
                patch.object(r,'validate_job',side_effect=validate), \
                patch.object(r.common,'_hash',return_value='a'*64), \
                patch.object(r.common,'baseline_invariants',return_value={'fixture':True}), \
                patch.object(r,'bounded_process',return_value={'status':'completed','returncode':0}) as child:
            plan = r.make_plan(self.repo,Path(root)/'assets',Path(root)/'output',Path(root)/'history',
                               Path(root)/'B-plan.json',Path(root)/'B-report.json')
            first = plan['jobs'][0]; run = Path(plan['output'])/'runs'/first['run_id']
            data = {'run':run,'paths':[],'fingerprint':r.artifacts._fingerprint([])}
            report = {'snapshot_path':'/fixture/initial.snp','snapshot_sha256':'a'*64,
                      'final_phase':'paused','non_u':{'fixture':True}}
            with patch.object(r,'validate_stage',return_value=(data,report,{}, {'sha256':'a'*64})):
                result = r.run_verifier(plan)
            self.assertEqual(child.call_count,1)
            self.assertEqual(calls,['anchor','own'])
            self.assertTrue(result['runs'][0]['mechanism_pass'])
            self.assertNotIn('failure',result['runs'][0])
            self.assertEqual(result['first_failure']['scope'],'before-owner')
            self.assertEqual(result['first_failure']['stage'],'own')
            self.assertEqual(len(result['unattempted_stages']),39)
            self.assertEqual(result['unattempted_stages'][0]['run_id'],plan['jobs'][1]['run_id'])

    def test_real_job_validator_accepts_canonical_id_and_rejects_bad_id_or_path(self):
        r = self.runner; cell = r.CELLS[0]; histories = self.fixture(cell)[-1]
        for h in histories.values(): h['path']='fixture-history.json'
        with tempfile.TemporaryDirectory() as root, patch.object(r.common,'load_histories',return_value=histories):
            root = Path(root); run_id = '12345678123456781234567812345678'
            job = {'repo':str(self.repo),'assets':str(root/'assets'),'history_root':str(root/'history'),
                'root_output':str(root/'out'),'output':str(root/'out/runs'/run_id),'run_id':run_id,
                'cell':list(cell),'stage':'anchor','binding':{'cell':list(cell),'case':r.admission.make_case(cell)},
                'protocol_sha256':r.PROTOCOL_SHA256,'source_identity':{'fixture':True},
                'history_inputs':r.history_pins(root/'history',histories),
                'snapshot_path':str(root/'initial.snp'),'snapshot_sha256':'a'*64,'expected_non_u':{'fixture':True},
                'selector':r.selector_config('anchor',histories),'oracle_evidence':None}
            original = copy.deepcopy(job)
            self.assertEqual(r.validate_job(job),job)  # Real validator and artifacts._id; no recording dependency.
            self.assertEqual(job,original)
            changed = copy.deepcopy(job); changed['run_id']='not-a-uuid'
            with self.assertRaisesRegex(ValueError,'UUID'): r.validate_job(changed)
            changed = copy.deepcopy(job); changed['output']=str(root/'other/runs'/run_id)
            with self.assertRaisesRegex(ValueError,'comparison job'): r.validate_job(changed)
            changed = copy.deepcopy(job); changed['output']=str(root/'out/runs'/'87654321876543218765432187654321')
            with self.assertRaisesRegex(ValueError,'comparison job'): r.validate_job(changed)


if __name__ == '__main__':
    unittest.main()
