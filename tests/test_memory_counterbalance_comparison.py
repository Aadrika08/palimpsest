"""Pure Stage C linkage fixtures; no recorded-data or model dependency."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

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


if __name__ == '__main__':
    unittest.main()
