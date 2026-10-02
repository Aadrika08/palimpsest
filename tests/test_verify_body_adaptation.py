"""Pure orchestration/guard fixtures; no real renderer, simulator or owners."""
import copy
import itertools
from types import SimpleNamespace
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
SCRIPTS=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
import verify_body_adaptation as verify
import test_body_adaptation_engine as fixtures
import test_verify_body_runtime as raw_fixtures
from palimpsest import body_adaptation as adaptive
from palimpsest.records import iter_ticks


class VerifierChecks(unittest.TestCase):
    def test_plan_exact_owners_ticks_deadlines_and_hard_caps(self):
        self.assertEqual(len(verify.OWNERS),12)
        self.assertEqual(sum(ticks for _,ticks in verify.OWNERS),2276)
        self.assertEqual(sum(len(verify.coverage(mode)) for mode,_ in verify.OWNERS),2276)
        self.assertEqual(verify.PROTOCOL['maximum_physics_intervals'],2277)
        self.assertEqual(verify.PROTOCOL['snapshot_files'],14)
        self.assertEqual(verify.PROTOCOL['output_max_bytes'],2*1024**3)
        self.assertEqual(sum(row['deadline_seconds'] for row in verify.PROTOCOL['owners']),2040)
        self.assertEqual(verify.PROTOCOL['outer_deadline_seconds'],2160)
        estimate=verify.preflight_bytes({key:np.zeros((128,128,3),np.uint8) for key in ('cam_left','cam_right')})
        self.assertEqual(estimate['numeric_estimate_bytes'],531382272)
        self.assertLess(estimate['total_admission_bytes'],verify.PROTOCOL['output_max_bytes'])
        with self.assertRaises(ValueError):
            verify.preflight_bytes({key:np.zeros((128,128,3),np.float32) for key in ('cam_left','cam_right')})

    def test_complete_source_sequence_preserves_next_then_clears_reset(self):
        fixture=fixtures.EngineContracts(methodName='test_final_next_preserves_new_fit_and_reset_clears_it')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        engine=fixture.engine();boundaries={}
        def capture(name,owner):
            boundaries[name]=copy.deepcopy(owner.body_state)
        with patch.object(adaptive,'configure',side_effect=fixtures.configure),patch.dict('sys.modules',mujoco=engine.env.mj):
            result=verify.source_session(engine,capture)
        self.assertEqual(engine.total_tick,516)
        self.assertEqual(engine.body_state['episode_step'],8)
        self.assertEqual(engine.body_state['samples'],[])
        self.assertIsNone(engine.body_state['fit'])
        self.assertEqual([(key,len(value['samples'])) for key,value in boundaries.items()], [('collecting',4),('fitted',400)])
        self.assertEqual(result['accepted_session'],boundaries['fitted'])
        self.assertEqual(len(result['guards']),8)
        self.assertTrue(all(row['native_cursor_unchanged'] for row in result['guards']))
        self.assertEqual(len(result['collecting_continuation']),4)
        self.assertEqual(len(result['fitted_continuation']),4)
        engine.writer.flush()
        rows=list(iter_ticks(engine.writer.path))
        self.assertEqual([(row['episode'],row['tick']) for row in rows],verify.coverage('source'))
        self.assertIsNone(engine.env.mj.callback)

    def test_native_mismatch_keeps_collecting_and_fitted_application_valid(self):
        # Typed byte-buffer fixture exercises mutation/checksum/audit bookkeeping,
        # not MuJoCo serialization, stepping or native restore qualification.
        class NativeFixture:
            def __setstate__(self,raw):
                self.qpos=np.frombuffer(raw,np.float64).copy()
                self.model=SimpleNamespace(jnt_qposadr=np.array([0,1]))
            def __getstate__(self):return self.qpos.tobytes()
        mj=SimpleNamespace(MjData=NativeFixture,mjtState=SimpleNamespace(mjSTATE_INTEGRATION=1),
            mj_stateSize=lambda model,enum:2,
            mj_getState=lambda model,data,array,enum:array.__setitem__(slice(None),data.qpos))
        state=adaptive.initial_session(episode=0)
        for _ in range(24):state=fixtures.session_fixtures.SessionState().interval(state)
        for state in (state,fixtures.session_fixtures.SessionState().fitted()):
            angles=np.asarray(state['previous_angles_rad'],np.float64)
            snapshot={'application':{'body_state':state,'episode':state['episode'],'episode_step':state['episode_step']},
                      'native_data':angles.tobytes(),'native_sha256':'initial','integration':angles.copy()}
            env=SimpleNamespace(left_hinge_id=0,right_hinge_id=1)
            original=copy.deepcopy(snapshot)
            with patch.dict('sys.modules',mujoco=mj):
                bad=verify.native_encoder_mismatch(snapshot,env)
            self.assertEqual(bad['application'],snapshot['application'])
            adaptive.validate_session(bad['application']['body_state'])
            decoded=NativeFixture();decoded.__setstate__(bad['native_data']);decoded.time=state['time_s']
            np.testing.assert_array_equal(bad['integration'],decoded.qpos)
            self.assertEqual(bad['native_sha256'],verify.hashlib.sha256(bad['native_data']).hexdigest())
            with self.assertRaisesRegex(ValueError,'raw encoder cursor differs from native data'):
                adaptive.validate_native(state,decoded.model,decoded,env)
            self.assertEqual(snapshot['native_data'],original['native_data'])
            np.testing.assert_array_equal(snapshot['integration'],original['integration'])

    def test_expected_negative_never_substitutes_for_positive_or_missing_owner(self):
        supervisor={'status':'completed','returncode':0}
        positive={'status':'passed','engine_closed':True,'callback_restored':True}
        with self.assertRaises(ValueError):verify.owner_result('source',supervisor,positive,[])
        with self.assertRaises(ValueError):verify.owner_result('expected-rejection',supervisor,positive,[])
        negative={**positive,'status':'expected_rejection','expected_negative_verified':True,
                  'accepted_cursor_unchanged':True,'physics_intervals':1}
        verify.owner_result('expected-rejection',supervisor,negative,[])
        for key,value in [('expected_negative_verified',False),('physics_intervals',0),('engine_closed',False)]:
            bad={**negative,key:value}
            with self.assertRaises(ValueError):verify.owner_result('expected-rejection',supervisor,bad,[])
        with self.assertRaises(ValueError):verify.owner_result('expected-rejection',{'status':'timeout','returncode':0},negative,[])

    def test_expected_rejection_retains_complete_packet_and_old_cursor(self):
        fixture=fixtures.EngineContracts(methodName='test_final_next_preserves_new_fit_and_reset_clears_it')
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        engine=fixture.engine(env=fixtures.AdaptiveFixtureEnv(truncate_at=1))
        accepted=copy.deepcopy(engine.body_state)
        fixture.command(engine,'step')
        engine.writer.flush()
        import json
        events=[json.loads(line) for line in (engine.writer.path/'events.jsonl').read_text().splitlines()]
        packet=next(row['detail'] for row in events if row['kind']=='body_failed')
        audit=verify.verify_rejection(engine,accepted,packet)
        self.assertEqual(audit['pre_control_stages'],10)
        self.assertEqual(audit['end_caches'],1)
        self.assertEqual(engine.body_state,accepted)
        bad=copy.deepcopy(packet);bad['outcome']['truncated']=False
        with self.assertRaises(ValueError):verify.verify_rejection(engine,accepted,bad)
        bad=copy.deepcopy(packet);bad['interval']['stages'].pop()
        with self.assertRaises(ValueError):verify.verify_rejection(engine,accepted,bad)
        self.assertIsNone(engine.env.mj.callback)

    def test_snapshot_file_inventory_and_json_read_bounds(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for index in range(12):
                run=root/str(index)/'a';(run/'recording').mkdir(parents=True)
                (run/'recording/manifest.json').write_text('{}')
                (run/'snapshots').mkdir();(run/'snapshots/initial.snp').write_bytes(b'fixture')
            (root/'source').mkdir();(root/'source/collecting.snp').write_bytes(b'fixture')
            (root/'source/fitted.snp').write_bytes(b'fixture')
            self.assertEqual(verify.inventory(root,complete=True)['snapshot_files'],14)
            (root/'extra.snp').write_bytes(b'overflow')
            with self.assertRaises(ValueError):verify.inventory(root)
            (root/'extra.snp').unlink()
            path=root/'oversize.snp'
            with path.open('wb') as stream:stream.truncate(16*1024**2+1)
            with self.assertRaises(ValueError):verify.snapshot_path(path)
            path.unlink();path.symlink_to(root/'source/fitted.snp')
            with self.assertRaises(ValueError):verify.snapshot_path(path)
            data=root/'bounded.json';data.write_text('{"x":1}')
            self.assertEqual(verify.read_json(data,maximum=7),{'x':1})
            with self.assertRaises(ValueError):verify.read_json(data,maximum=6)

    def test_containment_rechecks_owned_start_before_signalling(self):
        owned={'pid':321,'start_ticks':9,'group':321,'state':'R'}
        reused={**owned,'start_ticks':10}
        with patch.object(verify,'process',side_effect=itertools.chain([owned,reused],itertools.repeat(None))), patch.object(verify.os,'killpg') as kill:
            result=verify.cleanup_observed({321:9})
        kill.assert_not_called();self.assertEqual(result['forced_signals'],[])
        with patch.object(verify,'process',side_effect=itertools.chain([owned,owned],itertools.repeat(None))), patch.object(verify.os,'killpg') as kill:
            result=verify.cleanup_observed({321:9})
        kill.assert_called_once_with(321,verify.signal.SIGTERM)
        self.assertEqual(result['forced_signals'][0]['start_ticks'],9)
        self.assertEqual(result['survivors'],[])

    def test_shared_raw_audit_explicit_identity_and_fixed_plan_preserve_default(self):
        row,manifest=raw_fixtures.HarnessChecks().row()
        identity={'standalone':True,'protocol_sha256':verify.PROTOCOL_SHA256}
        manifest['body_profile_identity']=identity
        fixed=lambda value:{'nominal_control':[0.,0.],'applied_action':[0.,0.],'applied_control':[0.,0.]}
        self.assertEqual(verify.audit_ticks([row],manifest,identity=identity,planner=fixed)['ticks'],1)
        with self.assertRaises(ValueError):verify.audit_ticks([row],manifest)
        bad=copy.deepcopy(row);bad['body_contact_counts'][0]=129
        with self.assertRaises(ValueError):verify.audit_ticks([bad],manifest,identity=identity,planner=fixed)


if __name__=='__main__':
    unittest.main()
