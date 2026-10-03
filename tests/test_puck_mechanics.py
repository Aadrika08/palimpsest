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
    return {'version': 2, 'teacher_mode': 'fixed', 'gate_protocol_sha256': gate.PROTOCOL_SHA256, 'case': 'zero',
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

    def test_historical_versions_and_protocol_pins_rejected_before_native_restore(self):
        app=application(1)
        variants=[]
        for version in (1,True,3):
            bad=copy.deepcopy(app);bad['version']=version;variants.append(bad)
        bad=copy.deepcopy(app);del bad['teacher_mode'];variants.append(bad)
        for filename in ('m6-puck-mechanics-v1.json','m6-puck-mechanics-v2.json','m6-puck-mechanics-v3.json',
                         'm6-puck-mechanics-v4.json'):
            import hashlib
            path=ROOT/'docs/plans'/filename;old=json.loads(path.read_text())
            for target,value in (('gate',hashlib.sha256(path.read_bytes()).hexdigest()),
                                 ('task',old['pushing_protocol_sha256'])):
                bad=copy.deepcopy(app)
                if target=='gate': bad['gate_protocol_sha256']=value
                else: bad['state']['protocol_sha256']=value
                variants.append(bad)
        for old in variants:
            with self.assertRaises(ValueError): gate.validate_application(old,'zero',1,state_digest(old))

    def test_historical_construction_pin_is_not_silently_promoted(self):
        import verify_puck_construction
        with self.assertRaisesRegex(ValueError,'module differs'):
            verify_puck_construction.protocol(ROOT)
        old=json.loads((ROOT/'docs/plans/m6-puck-mechanics-v1.json').read_text())
        new=gate.protocol(ROOT)
        for key in ('limits','environment_kwargs','runtime','owner_order','boundary_rules','watchdog'):
            self.assertEqual(new[key],old[key])
        self.assertNotEqual(new['pushing_protocol_sha256'],old['pushing_protocol_sha256'])
        v3=json.loads((ROOT/'docs/plans/m6-puck-mechanics-v3.json').read_text())
        self.assertEqual(new['recording'],v3['recording'])
        self.assertEqual(new['snapshot'],v3['snapshot'])

    def test_v5_mechanics_changes_only_identity_and_version_notes(self):
        old=json.loads((ROOT/'docs/plans/m6-puck-mechanics-v4.json').read_text())
        new=gate.protocol(ROOT)
        for key in ('id','pushing_protocol_sha256','puck_module_sha256','version_notes'):
            new[key]=old[key]
        new['profile_identity']['protocol_sha256']=old['profile_identity']['protocol_sha256']
        self.assertEqual(new,old)

    def test_application_dwell_is_not_command_zero(self):
        # Dwell remains an observed task predicate, independent of teacher recomputation.
        app = application(20)
        app['world'].update(puck_xyz=[1.01,0.,.062], rover_pose=[.46,0.,0.])
        app['state'].update(previous_puck_xy=[1.01,0.], previous_rover_xy=[.46,0.],
                            previous_distance=.18999999999999995, had_contact=True, dwell_ticks=1)
        app['inputs'] = puck.project(app['world'], app['contact'])
        with patch.object(puck,'demonstrate',side_effect=AssertionError('dwell must not call teacher')):
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

    def test_explicit_mode_selection_and_fixed_action_replay_never_calls_teacher(self):
        app=application(1)
        app['world']['rover_pose']=[-.55,0.,0.]
        for kind in ('root','native-continuation','policy-replay'):
            action,mode=gate.action_for({'kind':kind,'case':'teacher-positive'},app['world'],'approach')
            self.assertEqual((action,mode),([.2,0.],'push'))
        fixed={'kind':'root','case':'push-positive','action':[.25,0.]}
        recorded={'action':np.array([.25,0.]),'teacher_mode_before':np.array(0,np.uint8),
                  'teacher_mode_after':np.array(0,np.uint8)}
        with patch.object(puck,'demonstrate',side_effect=AssertionError('teacher called for fixed action')):
            self.assertEqual(gate.action_for(fixed,{},'fixed'),([.25,0.],'fixed'))
            self.assertEqual(gate.action_for(fixed|{'kind':'action-replay'}, {}, 'fixed', recorded),([.25,0.],'fixed'))
        for before,after in ((np.array(1,np.uint8),np.array(0,np.uint8)),
                             (np.array(0,np.uint8),np.array(2,np.uint8)),
                             (np.array(0,np.int64),np.array(0,np.uint8)),
                             (np.array([0],np.uint8),np.array(0,np.uint8))):
            bad=recorded|{'teacher_mode_before':before,'teacher_mode_after':after}
            with self.assertRaises(ValueError): gate.action_for(fixed|{'kind':'action-replay'}, {}, 'fixed', bad)
        with self.assertRaises(ValueError): gate.action_for(fixed,{},'approach')
        with self.assertRaises(ValueError): gate.action_for({'kind':'policy-replay','case':'teacher-positive'},app['world'],'fixed')

    def test_fixed_action_replay_accepts_record_reader_scalars_only_with_exact_mode_contract(self):
        from palimpsest.records import RunWriter, iter_ticks
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'recording'
            writer=RunWriter(path,{'schema':'puck-mechanics-v2'})
            writer.tick(0,0,action=np.array([.25,0.],np.float64),
                        teacher_mode_before=np.array(0,np.uint8),teacher_mode_after=np.array(0,np.uint8))
            writer.finish({'fixture':True});writer.close()
            recorded=next(iter_ticks(path))
        row={'kind':'action-replay','case':'push-positive'}
        for field in ('teacher_mode_before','teacher_mode_after'):
            self.assertIsInstance(recorded[field],np.uint8)
            self.assertNotIsInstance(recorded[field],np.ndarray)
        with patch.object(puck,'demonstrate',side_effect=AssertionError('action replay called teacher')):
            self.assertEqual(gate.action_for(row,{},'fixed',recorded),([.25,0.],'fixed'))
            for field in ('teacher_mode_before','teacher_mode_after'):
                for value in (np.uint8(1),np.uint8(2),np.int64(0),np.float32(0),
                              np.bool_(False),np.array([0],np.uint8),np.array([[0]],np.uint8),None):
                    with self.subTest(field=field,value=value):
                        with self.assertRaises(ValueError):
                            gate.action_for(row,{},'fixed',recorded|{field:value})
                missing=recorded.copy();del missing[field]
                with self.assertRaises(ValueError):gate.action_for(row,{},'fixed',missing)

    def test_snapshot_mode_admission_and_restored_policy_successors(self):
        app=application(1)
        app['case']=app['state']['episode_id']='teacher-positive'
        app['teacher_mode']='approach'
        app['world']['rover_pose']=[-.46742095296335834,.016918583801692796,.03331900718597027]
        app['state']['previous_rover_xy']=app['world']['rover_pose'][:2]
        app['inputs']=puck.project(app['world'],app['contact'])
        gate.validate_application(app,'teacher-positive',1,state_digest(app))
        # Serialize/read generic application without decoding any native bytes.
        from palimpsest.snapshots import save_snapshot, read_snapshot
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'fixture.snp'
            save_snapshot({'application':app},path)
            restored=read_snapshot(path)['application']
        gate.validate_application(restored,'teacher-positive',1,state_digest(app))
        for kind in ('native-continuation','policy-replay'):
            self.assertEqual(gate.action_for({'kind':kind,'case':'teacher-positive'},
                             restored['world'],restored['teacher_mode']),([0.,.16876197027012038],'approach'))
        for mode in ('fixed',None,True,1,[], 'recover'):
            bad=copy.deepcopy(app);bad['teacher_mode']=mode
            with self.assertRaises(ValueError): gate.validate_application(bad,'teacher-positive',1,state_digest(bad))
        bad=application(1);bad['teacher_mode']='approach'
        with self.assertRaises(ValueError): gate.validate_application(bad,'zero',1,state_digest(bad))
        # A changed valid mode must change the application hash.
        bad=copy.deepcopy(app);bad['teacher_mode']='push'
        with self.assertRaises(ValueError): gate.validate_application(bad,'teacher-positive',1,state_digest(app))
        initial=application(0);initial['case']=initial['state']['episode_id']='teacher-positive';initial['teacher_mode']='push'
        with self.assertRaises(ValueError): gate.validate_application(initial,'teacher-positive',0,state_digest(initial))

    def test_mode_packets_roundtrip_and_exact_policy_continuation(self):
        # Authored array fixtures, not simulated outcomes. Expected transitions
        # are literal so losing/restoring the wrong mode changes actual rows.
        from palimpsest.records import RunWriter, iter_ticks
        from palimpsest.snapshots import save_snapshot, read_snapshot
        app=application(0);app['case']=app['state']['episode_id']='teacher-positive'
        app['teacher_mode']='approach'
        worlds=[]
        for tick,pose in enumerate(([-.8,0.,0.],[-.55,0.,0.],[-.45,.07,0.],[-.4,0.,0.],[-.42,0.,0.])):
            value=copy.deepcopy(app['world']);value.update(time_s=tick*.02,rover_pose=pose);worlds.append(value)
        env=SimpleNamespace(data=SimpleNamespace(qpos=np.zeros(71),qvel=np.zeros(70),ctrl=np.zeros(2),
                            qfrc_applied=np.zeros(70),xfrc_applied=np.zeros((26,6))))
        observation={key:np.zeros((128,128,3),np.uint8) for key in ('cam_left','cam_right')}
        # atan2(-0, positive) retains negative zero in the aligned reverse heading.
        actions=([.25,0.],[.2,0.],[0.,.4],[-.25,-0.])
        modes=('approach','approach','push','approach','approach')
        state=app['state'];contact=app['contact'];source=[];cursors=[]
        for tick in range(4):
            cursors.append(copy.deepcopy(app|{'state':state,'world':worlds[tick],'contact':contact,
                'teacher_mode':modes[tick],'inputs':puck.project(worlds[tick],contact)}))
            next_contact=puck.classify_contacts(raw_contacts(tick+1),OWNERSHIP,tick=tick+1,time_s=(tick+1)*.02)
            state,reward=puck.advance(state,worlds[tick+1],next_contact,actions[tick])
            values=gate.packet(env,observation,worlds[tick],worlds[tick+1],puck.project(worlds[tick],contact),
                actions[tick],state,next_contact,raw_contacts(tick+1),reward,[0.,0.,0.,0.,0.],
                modes[tick],modes[tick+1],'teacher-positive')
            source.append({'episode':0,'tick':tick,**values});contact=next_contact
        with tempfile.TemporaryDirectory() as tmp:
            record=Path(tmp)/'recording'
            writer=RunWriter(record,{'schema':'puck-mechanics-v2'})
            for row in source: writer.tick(**row)
            writer.finish({'fixture':True});writer.close()
            rows=list(iter_ticks(record))
            for kind,start in (('policy-replay',0),('native-continuation',2)):
                path=Path(tmp)/(kind+'.snp');cursor=cursors[start]
                save_snapshot({'application':cursor},path)
                restored=read_snapshot(path)['application']
                gate.validate_application(restored,'teacher-positive',start,state_digest(cursor))
                mode=restored['teacher_mode']
                for row in gate.window(rows,start,4-start):
                    tick=row['tick']
                    action,next_mode=gate.action_for({'kind':kind,'case':'teacher-positive'},worlds[tick],mode)
                    actual=copy.deepcopy(row);actual.update(action=np.array(action,np.float64),
                        teacher_mode_before=np.array(gate.mode_code(mode,'teacher-positive'),np.uint8),
                        teacher_mode_after=np.array(gate.mode_code(next_mode,'teacher-positive'),np.uint8))
                    gate.same_row(row,actual);mode=next_mode
            for field in ('teacher_mode_before','teacher_mode_after'):
                self.assertEqual(rows[2][field].dtype,np.uint8);self.assertEqual(rows[2][field].shape,())
                bad=copy.deepcopy(rows[2]);bad[field]=np.array(0,np.uint8)
                with self.assertRaises(ValueError): gate.same_row(rows[2],bad)
        # State digest binds mode even with identical task/world/contact.
        different=gate.packet(env,observation,worlds[3],worlds[4],np.zeros(8,np.float32),actions[3],state,
            contact,raw_contacts(4),0.,[0.]*5,'approach','push','teacher-positive')
        self.assertNotEqual(source[3]['task_sha256'].tobytes(),different['task_sha256'].tobytes())

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
