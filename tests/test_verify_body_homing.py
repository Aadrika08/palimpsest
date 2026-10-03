"""Admission/orchestration guards without a native owner or ignored-data dependency."""
import copy
from contextlib import nullcontext
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import verify_body_homing as gate
import verify_body_turns as turns
import test_body_homing as fixtures
from palimpsest import body_homing as homing, body_adaptation as adaptive
from palimpsest.snapshots import save_snapshot, state_digest


class GateGuards(unittest.TestCase):
    def test_real_bounded_file_admission_precedes_derivation(self):
        fixture=fixtures.Composition();fixture.setUp();self.addCleanup(fixture.doCleanups)
        engine=fixture.engine(True);app=engine.application_state()
        app.update(schema_version=6,scenario=adaptive.SCENARIO,task_state=None);app.pop('composition')
        snapshot={'application':app,'identity':{'model_sha256':adaptive.IDENTITY['model_sha256'],
            'body_profile':adaptive.IDENTITY},'native_data':b'fixture-native-not-physics',
            'environment':{'values':{'_goal_xy':[1.,2.]},'absent':[]}}
        with tempfile.TemporaryDirectory() as folder:
            shot=Path(folder)/'fitted.snp';report_path=Path(folder)/'report.json'
            save_snapshot(snapshot,shot)
            reference={**homing.REFERENCE,'snapshot_sha256':gate.digest(shot),
                'decoded_snapshot_sha256':state_digest(snapshot),'session_sha256':adaptive._sha(engine.body_state),
                'samples_sha256':engine.body_state['samples_sha256'],'fit_sha256':engine.body_state['fit_sha256']}
            report={'status':'passed','source_unchanged':True,'assets_unchanged':True,
                'runtime_source':{'commit':turns.REFERENCE['source_commit']},
                'snapshots':{'fitted':{'sha256':reference['snapshot_sha256']}},
                'accepted_fit':{'fit':engine.body_state['fit'],'session_sha256':reference['session_sha256']}}
            report_path.write_text(json.dumps(report));reference['report_sha256']=gate.digest(report_path)
            config={'calibration_report':str(report_path),'fitted_snapshot':str(shot)}
            with patch.dict(homing.REFERENCE,reference),patch.dict(turns.REFERENCE,reference):
                raw,loaded,derived,pins=gate.admitted_inputs(config)
                self.assertEqual(state_digest(raw),reference['decoded_snapshot_sha256'])
                self.assertEqual(loaded,report);self.assertEqual(pins['snapshot'],gate.digest(shot))
                self.assertEqual(derived['application']['task_state'],homing.initial_task(engine.body_state))
                altered=copy.deepcopy(raw);altered['environment']['values']['_goal_xy'][0]=99.
                with self.assertRaisesRegex(ValueError,'decoded state pin'):
                    homing.derive_snapshot(altered,snapshot_sha256=pins['snapshot'],report=loaded,
                                          report_sha256=pins['report'])
                report_path.write_text('{}')
                with self.assertRaisesRegex(ValueError,'calibration report'):gate.admitted_inputs(config)

    def test_fixed_bounds_and_legitimate_early_window(self):
        import numpy as np
        estimate=gate.admission({'cam_left':np.zeros((128,128,3),np.uint8),'cam_right':np.zeros((128,128,3),np.uint8)})
        self.assertEqual(estimate['aggregate_bytes'],954560512)
        self.assertEqual(estimate['per_recording_bytes'],142413824)
        self.assertEqual((gate.PROTOCOL['owners'],gate.PROTOCOL['maximum_numeric_ticks'],gate.PROTOCOL['snapshot_files']),(4,1807,5))
        with self.assertRaises(ValueError):gate.admission({'cam_left':np.zeros((256,128,3),np.uint8),'cam_right':np.zeros((128,128,3),np.uint8)})
        item={'state':{'phase':'terminated','task':{'phase':'complete'},'last_outcome':{'reason':'task_completed','evaluator_actual_home_distance_m':.25}}}
        gate.validate_window([item]);self.assertTrue(gate.capability(item['state']))
        item['state']['last_outcome']['evaluator_actual_home_distance_m']=.250001
        self.assertFalse(gate.capability(item['state']))
        item['state']['phase']='paused'
        with self.assertRaises(ValueError):gate.validate_window([item])
        gate.validate_window([item]*4)
        item['state'].update(phase='truncated',last_outcome={'reason':'time_limit'})
        self.assertFalse(gate.window_admission([item])['admissible'])
        self.assertFalse(gate.window_admission([])['admissible'])
        self.assertTrue(gate.window_admission([{'state':{'phase':'paused'}}]*3+[item])['admissible'])
        item['state']['last_outcome']['reason']='unsupported'
        with self.assertRaises(ValueError):gate.window_admission([item])

    def test_command_reset_from_terminal_and_step_applied_once(self):
        fixture=fixtures.Composition();fixture.setUp();self.addCleanup(fixture.doCleanups)
        engine=fixture.engine(True)
        with patch.dict('sys.modules',mujoco=engine.env.mj):
            gate.command(engine,'one-step','step')
        self.assertEqual(engine.total_tick,481)
        engine.phase='terminated'
        with patch.object(adaptive,'configure',side_effect=fixtures.configure):gate.command(engine,'clear','reset')
        self.assertIsNone(engine.task_state);self.assertEqual(engine.body_state['samples'],[])
        self.assertEqual(engine.composition,homing.context())

    def test_real_storage_api_admits_parent_and_worker_destinations(self):
        from palimpsest.engine import Engine
        from palimpsest.storage import StorageBudget, StorageLimits
        from dataclasses import asdict
        original_check=StorageBudget.check
        admitted=[]
        def checked(budget, additional_bytes, *, path):
            result=original_check(budget,additional_bytes,path=path)
            admitted.append((additional_bytes,Path(path)))
            return result
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);inputs=root/'inputs';inputs.mkdir();stage=root/'worker';stage.mkdir()
            args=SimpleNamespace(repo=Path(__file__).resolve().parents[1],assets=root/'assets',
                calibration_report=inputs/'report.json',fitted_snapshot=inputs/'fitted.snp',output=root/'parent')
            input_state=(None,None,None,{'report':'fixture','snapshot':'fixture'})
            with patch.object(gate,'source_identity',return_value={'fixture':True}),\
                patch.object(gate,'harness_hashes',return_value={'fixture':True}),\
                patch.object(gate,'admitted_inputs',return_value=input_state),\
                patch('palimpsest.assets.verify_assets',return_value={'ok':True}),\
                patch.object(StorageBudget,'check',checked),patch.object(StorageBudget,'lock',return_value=nullcontext()),\
                patch('palimpsest.evaluate.bounded_process',side_effect=RuntimeError('stop after real parent admission')) as child:
                report=gate.verify(args)
                child.assert_called_once()  # No process is created by this mocked boundary.
                self.assertIn((gate.admission()['aggregate_bytes'],args.output),admitted)
                self.assertEqual(report['error']['message'],'stop after real parent admission')
                for mode in ('source','native'):
                    run=stage/mode
                    config={'repo':str(args.repo),'assets':str(args.assets),'mode':mode,'stage':str(stage),'run':str(run),
                        'runtime_source':{'fixture':True},'harness_sha256':{'fixture':True},
                        'storage':{'roots':[str(stage)],'limits':asdict(StorageLimits(max_bytes=2*1024**3,min_free_bytes=1024**3)),
                            'headroom_bytes':8*1024**2}}
                    with patch.dict(sys.modules,mujoco=SimpleNamespace(get_mjcb_control=lambda:None)),\
                        patch.object(Engine,'open',side_effect=RuntimeError('stop after real worker admission')) as native:
                        self.assertFalse(gate.worker(config));native.assert_called_once()
                    amount=gate.admission()['aggregate_bytes'] if mode=='source' else gate.admission()['per_recording_bytes']+16*gate.MiB
                    self.assertIn((amount,run),admitted)
                    result=json.loads((stage/'result.json').read_text())
                    self.assertEqual(result['error']['message'],'stop after real worker admission')

if __name__=='__main__':unittest.main()
