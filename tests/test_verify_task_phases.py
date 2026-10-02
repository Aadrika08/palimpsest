"""Prospective task-phase predicates and continuation guards; no native runtime."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(SCRIPTS))
spec = importlib.util.spec_from_file_location('verify_task_phases',SCRIPTS/'verify_task_phases.py')
verify = importlib.util.module_from_spec(spec);spec.loader.exec_module(verify)


class PhaseGuards(unittest.TestCase):
    def test_predicates_on_real_declared_task_state_transitions(self):
        from palimpsest.task_profiles import initialize, advance
        calibration={'radius_m':.1,'track_m':.4,'quantum_rad':.001}
        def packet(tick,angles,landmarks):
            return {'version':1,'episode_id':'episode-0','tick':tick,'time_s':tick*.02,
                    'angles_rad':angles,'landmarks':landmarks}
        far=[{'id':'inspect-a','bearing_rad':0.,'near':False},
             {'id':'inspect-b','bearing_rad':.1,'near':False}]
        state=initialize('exploration-landmarks','episode-0',[0.,0.],calibration)
        state,*_=advance(state,packet(0,[0.,0.],far))
        self.assertFalse(verify.phase_matches('selected',state,None,1))
        state,*_=advance(state,packet(1,[.1,.1],far))
        self.assertTrue(verify.phase_matches('selected',state,None,2))
        near=[{**far[0],'near':True},far[1]]
        state,*_=advance(state,packet(2,[.1,.1],near))
        self.assertTrue(verify.phase_matches('first-dwell',state,None,3))
        self.assertFalse(verify.phase_matches('second-dwell',state,None,3))
        for tick in range(3,7):
            state,*_=advance(state,packet(tick,[.1,.1],near))
        state,*_=advance(state,packet(7,[.1,.1],[{**far[1],'near':True}]))
        self.assertTrue(verify.phase_matches('second-dwell',state,None,8))
        home=initialize('encoder-homing','episode-0',[0.,0.],calibration)
        home,*_=advance(home,packet(0,[0.,0.],[]))
        home,*_=advance(home,packet(1,[1.,1.],[]))
        self.assertTrue(verify.phase_matches('outbound',home,None,8))
        self.assertFalse(verify.phase_matches('outbound',home,None,9))
        home,*_=advance(home,packet(2,[5.,5.],[]))
        home,*_=advance(home,packet(3,[10.,10.],[]))
        cue={'sensors':np.array([0.,0.,-1.,0.],np.float32)}
        self.assertTrue(verify.phase_matches('home-turn',home,cue,3))
        self.assertFalse(verify.phase_matches('home-turn',home,{'sensors':np.array([0.,0.,1.,0.])},3))
        home,*_=advance(home,packet(4,[5.,5.],[]))
        home,*_=advance(home,packet(5,[0.,0.],[]))
        home,*_=advance(home,packet(6,[0.,0.],[]))
        self.assertTrue(verify.phase_matches('home-dwell',home,{'sensors':np.zeros(4)},7))
        window=[]
        for tick in range(7,11):
            home,*_=advance(home,packet(tick,[0.,0.],[]))
            complete=home['phase']=='complete'
            window.append({'state':{'phase':'terminated' if complete else 'paused',
                           'task':copy.deepcopy(home),
                           'last_outcome':{'reason':'task_completed'} if complete else None}})
        self.assertEqual(home['dwell_ticks'],5)
        self.assertEqual(len(window),4)
        verify.valid_window(window)

    def test_terminal_crossing_may_shorten_only_legitimate_completion(self):
        paused={'state':{'phase':'paused','task':{'phase':'home'},'last_outcome':None}}
        terminal={'state':{'phase':'terminated','task':{'phase':'complete'},
                           'last_outcome':{'reason':'task_completed'}}}
        verify.valid_window([copy.deepcopy(paused) for _ in range(4)])
        verify.valid_window([paused,terminal])
        verify.valid_window([terminal])
        for items in ([],[paused],[terminal,paused],[paused]*5,
                      [{'state':{**terminal['state'],'last_outcome':{'reason':'collision'}}}],
                      [{'state':{**terminal['state'],'phase':'truncated'}}]):
            with self.subTest(items=items),self.assertRaises(ValueError):
                verify.valid_window(items)

    def test_camera_and_task_integer_equality_and_evaluator_float_tolerance(self):
        from palimpsest.replay import _same_json
        row={'episode':0,'tick':2,'cam_left':np.zeros((1,1,3),np.uint8),'sensors':np.zeros(4,np.float32)}
        verify.compare_tick(row,row,{'dwell_ticks':1},{'dwell_ticks':1})
        altered={**row,'cam_left':np.ones((1,1,3),np.uint8)}
        with self.assertRaises(Exception):
            verify.compare_tick(row,altered,{}, {})
        with self.assertRaises(Exception):
            verify.compare_tick(row,row,{'dwell_ticks':1},{'dwell_ticks':2})
        _same_json({'drift_m':.02},{'drift_m':.0200001})
        with self.assertRaises(Exception):
            _same_json({'drift_m':.02},{'drift_m':.021})

    def test_fixed_coverage_and_actual_camera_admission(self):
        self.assertEqual(len(verify.OWNERS),12)
        self.assertEqual(sum(len(p) for p in verify.PHASES.values()),6)
        self.assertEqual(verify.PROTOCOL['maximum_numeric_ticks'],2*600+6*4+4*600)
        self.assertEqual(verify.PROTOCOL['snapshot_files'],2+6+6+4)
        obs={key:np.zeros((128,128,3),np.uint8) for key in ('cam_left','cam_right')}
        estimate=verify.preflight(obs)
        self.assertLess(estimate['aggregate_bytes'],2*1024**3)
        self.assertLess(estimate['per_recording_bytes'],256*1024**2)
        with self.assertRaises(ValueError):
            verify.preflight({**obs,'cam_left':np.zeros((256,256,3),np.uint8)})

    def test_restored_step_uses_saved_command_without_previous_transition(self):
        from unittest.mock import patch
        from test_engine import SmallEnv
        from palimpsest.engine import Engine
        from palimpsest.records import RunWriter
        import tempfile
        with tempfile.TemporaryDirectory() as temp:
            env=SmallEnv();engine=Engine(env,RunWriter(Path(temp)/'recording',{'run_id':'phase-fixture'}),controller='manual')
            try:
                # This is a helper/receipt check; evaluator is isolated and no fixture physics claim is made.
                with patch.object(verify,'evaluator_sample',return_value={'pose':[0.,0.,0.],'angles':[0.,0.]}),patch.object(verify,'evaluator_record',return_value={'drift_m':0.}):
                    row=verify.successor(engine,'v2',recorded_action=[.4,.09])
                self.assertEqual(row['requested_action'],[.4,.09])
                np.testing.assert_array_equal(env.data.ctrl,[.4,.09])
                self.assertEqual(engine.total_tick,1);self.assertEqual(env.calls,1)
            finally:
                engine.close()


if __name__=='__main__':
    unittest.main()
