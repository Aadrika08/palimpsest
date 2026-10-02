"""Pure verifier fixtures; these do not exercise or qualify native puck physics."""
import copy
from contextlib import contextmanager
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from palimpsest import puck_profile as puck
from palimpsest.snapshots import state_digest
from test_puck_profile import OWNERSHIP, raw_contacts

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_puck_mechanics as gate


def application(tick=0):
    world = {'time_s': 0., 'rover_pose': [-.8, 0., 0.], 'puck_xyz': [0., 0., .062],
             'puck_velocity_xy': [0., 0.], 'goal_xy': [1.2, 0.]}
    state = puck.initialize(world, 'zero')
    contact = puck.classify_contacts(raw_contacts(0), OWNERSHIP, tick=0, time_s=0.)
    for n in range(tick):
        world['time_s'] = (n+1)*.02
        contact = puck.classify_contacts(raw_contacts(n+1), OWNERSHIP, tick=n+1, time_s=world['time_s'])
        state, _ = puck.advance(state, world, contact, [0., 0.])
    return {'version': 1, 'gate_protocol_sha256': gate.PROTOCOL_SHA256, 'case': 'zero',
            'profile_identity': {'fixture': True}, 'model_sha256': 'a'*64,
            'state': state, 'world': world, 'contact': contact,
            'inputs': puck.project(world, contact), 'paused': True}


class MechanicsFixtures(unittest.TestCase):
    def test_exact_ten_plan_and_storage_allowances(self):
        rows = gate.plan(puck.load_protocol(ROOT))
        self.assertEqual([r['id'] for r in rows], ['zero', 'push-positive', 'push-negative',
            'teacher-positive', 'teacher-negative', 'continue-tick1', 'continue-contact',
            'continue-dwell', 'replay-actions', 'replay-policy'])
        self.assertEqual([r['max_ticks'] for r in rows], [120,120,120,600,600,4,4,4,120,600])
        self.assertEqual(sum(r['max_bytes'] for r in rows), 832*1024**2)
        self.assertLess(sum(r['max_bytes'] for r in rows)+8*1024**2, 1024**3)
        for ticks,snapshots,cap in [(4,1,32),(120,1,64),(600,4,160),(600,1,160)]:
            # Includes worst-case already-written initial snapshot + concurrent headroom.
            self.assertLess(gate.record_estimate(ticks,snapshots)+16*1024**2,cap*1024**2)
        self.assertEqual(gate.record_estimate(120,1),27131904)

    def test_first_boundaries_never_replace(self):
        state = {'tick': 1, 'dwell_ticks': 0}
        seen = {'initial'}
        self.assertEqual(gate.boundaries(state, {'rover_puck_contact': False}, seen), ['tick1'])
        seen.add('tick1')
        state.update(tick=2, dwell_ticks=1)
        names = gate.boundaries(state, {'rover_puck_contact': True}, seen)
        self.assertEqual(names, ['contact', 'dwell'])
        seen.update(names)
        state['tick'] = 3
        self.assertEqual(gate.boundaries(state, {'rover_puck_contact': True}, seen), [])

    def test_four_successors_not_earlier_or_shorter(self):
        rows = [{'episode': 0, 'tick': n} for n in range(10)]
        self.assertEqual([r['tick'] for r in gate.window(rows, 2, 4)], [2,3,4,5])
        with self.assertRaises(ValueError): gate.window(rows, 8, 4)
        with self.assertRaises(ValueError): gate.window(rows, 0, True)
        rows[3]['tick'] = 4
        with self.assertRaises(ValueError): gate.window(rows, 2, 4)

    def test_application_projection_cursor_and_hash_admission(self):
        app = application(1)
        expected = state_digest(app)
        gate.validate_application(app, 'zero', 1, expected)
        for key, change in [('world', lambda x: x.update(time_s=0.)),
                            ('state', lambda x: x.update(previous_distance=3.)),
                            ('contact', lambda x: x.update(tick=0))]:
            bad = copy.deepcopy(app); change(bad[key])
            with self.assertRaises(ValueError): gate.validate_application(bad, 'zero', 1, state_digest(bad))
        bad = copy.deepcopy(app); bad['inputs'][0] += .01
        with self.assertRaises(ValueError): gate.validate_application(bad, 'zero', 1, state_digest(bad))
        with self.assertRaises(ValueError): gate.validate_application(app, 'zero', 1, '0'*64)
        with self.assertRaises(ValueError): gate.validate_application(app, 'push-positive', 1, expected)

    def test_v1_snapshot_gate_and_task_pins_rejected_before_native_restore(self):
        app=application(1)
        old_gate=copy.deepcopy(app)
        old_gate['gate_protocol_sha256']='27dac414c5828eaaf3b560114b7413aa5547175448a03bf22d42027fbe9914d9'
        old_task=copy.deepcopy(app)
        old_task['state']['protocol_sha256']='8a7f14ee69fe386fe1150b644e71737a5e39ab3c8c4987d7cdf61277796f3bac'
        for old in (old_gate,old_task):
            with self.assertRaises(ValueError): gate.validate_application(old,'zero',1,state_digest(old))

    def test_historical_construction_pin_is_not_silently_promoted(self):
        import verify_puck_construction
        with self.assertRaisesRegex(ValueError,'module differs'):
            verify_puck_construction.protocol(ROOT)
        old=json.loads((ROOT/'docs/plans/m6-puck-mechanics-v1.json').read_text())
        new=gate.protocol(ROOT)
        for key in ('limits','environment_kwargs','runtime','owner_order','boundary_rules','recording','snapshot','watchdog'):
            self.assertEqual(new[key],old[key])
        self.assertNotEqual(new['pushing_protocol_sha256'],old['pushing_protocol_sha256'])

    def test_application_dwell_is_not_command_zero(self):
        # The frozen dwell predicate can be valid at distance .19, outside teacher stop .18.
        app = application(20)
        app['world'].update(puck_xyz=[1.01,0.,.062], rover_pose=[.46,0.,0.])
        app['state'].update(previous_puck_xy=[1.01,0.], previous_rover_xy=[.46,0.],
                            previous_distance=.18999999999999995, had_contact=True, dwell_ticks=1)
        app['inputs'] = puck.project(app['world'], app['contact'])
        self.assertNotEqual(puck.demonstrate(app['world']), [0.,0.])
        gate.validate_application(app, 'zero', 20, state_digest(app))
        self.assertEqual(gate.boundaries(app['state'], app['contact'], {'initial','tick1','contact'}), ['dwell'])

    def test_exact_rows_reject_dtype_finite_and_changed_state(self):
        row = {'episode':0, 'tick':0, 'inputs':np.zeros(8,np.float32), 'qpos':np.zeros(71,np.float64)}
        gate.same_row(row, copy.deepcopy(row))
        for name, changed in [('inputs', np.zeros(8,np.float64)),
                              ('qpos', np.ones(71,np.float64)),
                              ('qpos', np.full(71,np.nan))]:
            bad=copy.deepcopy(row);bad[name]=changed
            with self.assertRaises(ValueError): gate.same_row(row,bad)

    def test_frozen_action_selection_calls_teacher_once_only_for_policy(self):
        row={'kind':'native-continuation'}; recorded={'action':np.array([.2,.1])}
        with patch.object(puck,'demonstrate',return_value=[.2,.1]) as teacher:
            self.assertEqual(gate.action_for(row, {}, recorded), [.2,.1]); teacher.assert_called_once()
        with patch.object(puck,'demonstrate',side_effect=AssertionError('not an action replay policy')):
            self.assertEqual(gate.action_for({'kind':'action-replay'}, {}, recorded), [.2,.1])

    def test_progress_binds_identity_and_monotonic_ticks(self):
        identity={'pid':321,'start_ticks':10,'process_group':321}
        receipt={**identity,'owner':'zero','phase':'ready','tick':2}
        self.assertEqual(gate.progress_update(receipt, None, identity, 'zero', 0, 120), receipt)
        for change in ({'pid':322},{'start_ticks':11},{'process_group':1},{'owner':'other'},
                       {'tick':1},{'tick':121},{'phase':'starting'},{'tick':True}):
            bad={**receipt,**change}
            with self.assertRaises(ValueError): gate.progress_update(bad,receipt,identity,'zero',0,120)
        later={**receipt,'tick':8}
        self.assertEqual(gate.progress_update(later,receipt,identity,'zero',0,120),later)

    def test_signal_admission_rejects_reused_shared_and_unrelated_process(self):
        expected={'pid':321,'start_ticks':10,'process_group':321}
        current={'pid':321,'start_ticks':10,'group':321,'ppid':123}
        self.assertTrue(gate.safe_owner(current, expected, 123, 111))
        for change in ({'pid':111},{'start_ticks':11},{'group':111},{'ppid':5}):
            self.assertFalse(gate.safe_owner({**current,**change},expected,123,111))

    def watchdog_fixture(self, ready):
        # No child or signal is real: reproduce missing startup/paused progress,
        # including the TERM->KILL path while bounded_process owns final reaping.
        proc={'pid':321,'start_ticks':10,'group':321,'ppid':123}
        future=MagicMock()
        future.done.side_effect=[False,False,False,True] if ready else [False,False,True]
        future.result.return_value={'status':'failed','returncode':-9}
        executor=MagicMock(); executor.__enter__.return_value.submit.return_value=future
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            command=['/python','/script','--child','fixed']
            if ready:
                (output/'progress.json').write_text(json.dumps({'pid':321,'start_ticks':10,'process_group':321,
                    'owner':'zero','phase':'ready','tick':0}))
            samples=[[],[proc],[proc],[proc]] if ready else [[],[proc],[proc]]
            with patch.object(gate,'ThreadPoolExecutor',return_value=executor), \
                 patch('verify_endurance.descendants',side_effect=samples), \
                 patch('verify_endurance.process',side_effect=[proc,proc,None]), \
                 patch.object(gate,'cleanup_check',return_value={'passed':True}), \
                 patch.object(gate.os,'getpid',return_value=123), patch.object(gate.os,'getpgrp',return_value=111), \
                 patch.object(gate.os,'killpg') as kill, patch.object(gate.time,'sleep'), \
                 patch.object(gate.time,'monotonic',side_effect=[0,1,32,36] if ready else [0,61,65]), \
                 patch.object(Path,'read_bytes',return_value=b'/python\0/script\0--child\0fixed\0'):
                result=gate.supervised_owner(command,output,{},None,{'id':'zero','max_ticks':120},0)
            self.assertFalse(result['passed'])
            self.assertEqual([x['signal'] for x in result['signals']],['SIGTERM','SIGKILL'])
            self.assertEqual([call.args[0] for call in kill.call_args_list],[321,321])
            self.assertEqual(result['identity'],{'pid':321,'start_ticks':10,'process_group':321})
            self.assertTrue(result['cleanup']['passed'])
            self.assertEqual(executor.__enter__.return_value.submit.call_args.args[3],180)

    def test_startup_timeout_identifies_owner_before_any_receipt(self):
        self.watchdog_fixture(False)

    def test_progress_timeout_forces_cleanup_and_never_passes(self):
        self.watchdog_fixture(True)

    def test_receipt_before_next_ancestry_poll_waits_for_independent_identity(self):
        proc={'pid':321,'start_ticks':10,'group':321,'ppid':123}
        future=MagicMock();future.done.side_effect=[False,False,True]
        future.result.return_value={'status':'completed','returncode':0}
        executor=MagicMock();executor.__enter__.return_value.submit.return_value=future
        with tempfile.TemporaryDirectory() as tmp:
            output=Path(tmp)
            (output/'progress.json').write_text(json.dumps({'pid':321,'start_ticks':10,'process_group':321,
                'owner':'zero','phase':'ready','tick':0}))
            with patch.object(gate,'ThreadPoolExecutor',return_value=executor), \
                 patch('verify_endurance.descendants',side_effect=[[],[],[proc]]), \
                 patch('verify_endurance.process',return_value=None), \
                 patch.object(gate,'cleanup_check',return_value={'passed':True}), \
                 patch.object(gate.os,'getpid',return_value=123),patch.object(gate.os,'getpgrp',return_value=111), \
                 patch.object(gate.os,'killpg') as kill,patch.object(gate.time,'sleep'), \
                 patch.object(gate.time,'monotonic',side_effect=[0,.1,.2]), \
                 patch.object(Path,'read_bytes',return_value=b'/python\0/script\0--child\0fixed\0'):
                result=gate.supervised_owner(['/python','/script','--child','fixed'],output,{},None,{'id':'zero','max_ticks':120},0)
            self.assertTrue(result['passed'])
            self.assertEqual(result['errors'],[])
            kill.assert_not_called()

    def test_snapshot_write_bound_before_publication_and_exclusive(self):
        from palimpsest.storage import StorageBudget, StorageLimits
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'snapshot.snp'
            budget=StorageBudget((Path(tmp),),StorageLimits(max_bytes=16*1024**2,min_free_bytes=0))
            with self.assertRaises(ValueError): gate.snapshot_budget(budget, path).check(8*1024**2+1,path=path)
            self.assertFalse(path.exists())
            from palimpsest.snapshots import save_snapshot
            save_snapshot({'small':np.zeros(2)},path,storage_budget=gate.snapshot_budget(budget,path))
            self.assertEqual(gate.read_bounded_snapshot(path,gate.digest(path))['small'].shape,(2,))
            with self.assertRaises(FileExistsError): save_snapshot({'small':1},path,storage_budget=gate.snapshot_budget(budget,path))
            with self.assertRaises(ValueError): gate.read_bounded_snapshot(path,'0'*64)

    def test_root_acceptance_does_not_relabel_natural_failure(self):
        case={'id':'teacher-positive','ticks':600}
        with self.assertRaises(ValueError): gate.accept_root(case,120,{'reason':'stalled'},.9,True,[.9,0.])
        gate.accept_root(case,120,{'reason':'puck_goal'},.9,True,[.9,0.])
        with self.assertRaises(ValueError): gate.accept_root({'id':'zero','ticks':120},120,{'reason':None},.002,False,[0.,0.])
        with self.assertRaises(ValueError): gate.accept_root({'id':'push-positive','ticks':120},120,{'reason':None},.2,False,[.2,0.])

    def test_first_supervisor_exception_retains_all_unstarted_rows(self):
        from palimpsest.storage import StorageBudget
        @contextmanager
        def fixture_lease(budget):
            for root in budget.roots: root.mkdir(parents=True)
            yield budget
        task=puck.load_protocol(ROOT); spec=gate.protocol(ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); output=root/'runs/gate'
            args=SimpleNamespace(repo=root,output=output,retention_root=root/'runs',expected_commit='fixture')
            with patch.object(gate,'__file__',str(root/'scripts/verify_puck_mechanics.py')), \
                 patch.object(gate,'protocol',return_value=spec), patch.object(puck,'load_protocol',return_value=task), \
                 patch.object(gate,'sources',return_value={'fixture':'frozen'}), \
                 patch.object(gate.subprocess,'check_output',side_effect=['fixture',spec['upstream_commit']]), \
                 patch.object(gate.subprocess,'run'), patch.object(StorageBudget,'lock',fixture_lease), \
                 patch.object(StorageBudget,'check',return_value={}), \
                 patch.object(gate,'supervised_owner',side_effect=RuntimeError('fixture startup failure')) as supervisor:
                self.assertEqual(gate.main(args),1)
            report=json.loads((output/'report.json').read_text())
            self.assertEqual([r['status'] for r in report['owners']],['failed']+['not_started']*9)
            self.assertTrue(report['sources_unchanged'])
            self.assertEqual(report['finalization_errors'],[])
            supervisor.assert_called_once()

if __name__=='__main__': unittest.main()
