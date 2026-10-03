"""Synthetic source checks only; no native owner, model load or writer lease."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_new_body_response as study
from palimpsest import body_profile as body, task_profiles as task
from palimpsest.records import RunWriter, iter_ticks


def samples():
    result = []
    for trial, action in enumerate(study.PROTOCOL['calibration']['trials']):
        control = body.effective_control(action['action'])
        for tick in range(20, 120):
            result.append({'trial': trial, 'tick': tick, 'control': control,
                           'increments_rad': [v * k * .02 for v, k in zip(control, (11., 14.))],
                           'dt_s': .02, 'contact': False})
    return result


def model():
    return {'immutable_sha256': study.PROTOCOL['initial_admission']['nominal_authored_model_sha256'],
            'actuator_gear': np.array([[3., 0, 0, 0, 0, 0], [3., 0, 0, 0, 0, 0]]),
            'jnt_range': np.tile([-.0001, .0001], (5, 1)),
            'geom_rgba': np.ones((3, 4)), 'site_pos': np.zeros((2, 3))}


def interval(tick=0, rejected=False):
    pair = {'geom_ids': [0, 1], 'geom_names': ['floor', 'left_wheel_geom'],
            'distance_m': 0., 'classification': 'unexpected_robot_contact' if rejected else 'rover_ground_support',
            'rejects_fit': rejected}
    stages = [{'time_s': tick * .02 + i * .002, 'control': [0., 0.], 'pairs': [pair]} for i in range(10)]
    return {'tick': tick, 'start_time_s': tick * .02, 'callback_count': 10, 'stages': stages,
            'end': {'data_time_s': (tick + 1) * .02, 'contact_cache_time_s': tick * .02 + .018,
                    'pairs': [pair]}, 'contact': rejected, 'coverage_passed': True, 'coverage_errors': []}


class NewBodyChecks(unittest.TestCase):
    def test_exact_protocol_and_old_sources(self):
        self.assertEqual(study.read_protocol(ROOT), study.PROTOCOL)
        self.assertEqual(study.LIMITS['whole_study_admission_bytes'], 644317184)

    def test_fit_exact_order_and_all_four_trials(self):
        fitted = study.fit_samples(samples())
        np.testing.assert_allclose(fitted['pooled']['gains_rad_s_per_control'], [11., 14.], rtol=1e-14)
        self.assertEqual(fitted['pooled']['sample_count'], 400)
        for corrupt in ('order', 'short', 'bool', 'control', 'contact'):
            values = samples()
            if corrupt == 'order': values[0], values[1] = values[1], values[0]
            if corrupt == 'short': values.pop()
            if corrupt == 'bool': values[0]['trial'] = False
            if corrupt == 'control': values[0]['control'] = [.2, .2]
            if corrupt == 'contact': values[0]['contact'] = True
            with self.subTest(corrupt=corrupt), self.assertRaises(ValueError):
                study.fit_samples(values)

    def test_gain_agreement_and_ratio_are_not_relaxed(self):
        values = samples()
        for row in values[:100]: row['increments_rad'][0] *= .7
        with self.assertRaises(ValueError): study.fit_samples(values)
        values = samples()
        for row in values: row['increments_rad'][0] *= .5
        with self.assertRaises(ValueError): study.fit_samples(values)

    def test_private_cue_ignores_poisoned_upstream_truth(self):
        state = task.initialize('encoder-homing', 'episode-0', [0., 0.],
                                {'radius_m': .06, 'track_m': .36, 'quantum_rad': .001})
        class Poison:
            data = types.SimpleNamespace(time=0.)
            def _base_xy(self): raise AssertionError('true pose read by controller')
            def __getattr__(self, key): raise AssertionError('upstream/private input read: ' + key)
        packet = task.capture(Poison(), state, 0, wheel_angles=[0., 0.])
        fitted = study.fit_samples(samples())
        advanced, cue, plan = study.study_action(state, packet, None, fitted)
        self.assertEqual(plan['requested_action'], [0., 0.])
        self.assertEqual(plan['applied_action'], [0., 0.])
        self.assertEqual(cue.dtype, np.dtype('float32'))
        packet.update(tick=1, time_s=.02)
        _, _, plan = study.study_action(advanced, packet, cue, fitted)
        self.assertEqual(plan['requested_action'], [.4, 0.])
        self.assertNotEqual(plan['applied_action'], [.4, 0.])
        self.assertLessEqual(max(abs(v) for v in plan['applied_control']), 2.)

    def test_hold_precedes_compensation(self):
        state = task.initialize('encoder-homing', 'episode-0', [0., 0.],
                                {'radius_m': .06, 'track_m': .36, 'quantum_rad': .001})
        for tick, angle in enumerate([0., 6., 12., 18., 12., 6., 0.]):
            packet = {'version':1,'episode_id':'episode-0','tick':tick,'time_s':tick*.02,
                      'angles_rad':[angle,angle],'landmarks':[]}
            state, _, _, _ = task.advance(state, packet)
        packet.update(tick=7,time_s=.14)
        _, cue, plan = study.study_action(state, packet, np.array([1., 0.], np.float32), study.fit_samples(samples()))
        self.assertEqual(plan['requested_action'], [.4, 0.])
        self.assertTrue(plan['hold'])
        self.assertEqual(plan['nominal_action'], [0., 0.])
        self.assertEqual(plan['applied_control'], [0., 0.])
        np.testing.assert_array_equal(cue, [0., 0.])

    def test_model_allowlist_is_exact(self):
        before = model(); after = copy.deepcopy(before)
        positions = [[-1., 2.], [3., 4.]]; joints = [[0, 1], [2, 3]]
        after['actuator_gear'][0, 0] = 2.1
        for ids, xy in zip(joints, positions):
            for j, x in zip(ids, xy): after['jnt_range'][j] = [x-.0001, x+.0001]
        after['site_pos'][1, :2] = [-3.5, 3.]
        study.validate_model_change(before, after, joints, positions, 1)
        for field in ('gear', 'rgba', 'joint', 'site', 'mass'):
            bad = copy.deepcopy(after)
            if field == 'gear': bad['actuator_gear'][1, 1] = .1
            if field == 'rgba': bad['geom_rgba'][0, 0] = .2
            if field == 'joint': bad['jnt_range'][4, 0] += .01
            if field == 'site': bad['site_pos'][1, 2] = 1.
            if field == 'mass': bad['immutable_sha256'] = '0'*64
            with self.subTest(field=field), self.assertRaises(ValueError):
                study.validate_model_change(before, bad, joints, positions, 1)

    def test_author_episode_uses_authored_ranges_and_checks_float32_cache(self):
        from palimpsest import memory_world, profiles, snapshots
        from unittest.mock import Mock

        class Model(types.SimpleNamespace):
            def __getstate__(self):
                return self.jnt_range.tobytes()+self.actuator_gear.tobytes()

        class Env:
            def __init__(self):
                self.n_obstacles, self.arena, self.goal_site_id = 20, 7., 0
                self.obstacle_ids = list(range(20))
                self.obstacle_x_joint_ids = list(range(0,40,2))
                self.obstacle_y_joint_ids = list(range(1,40,2))
                self.model = Model(nu=2, actuator_gear=np.array([[3.,0,0,0,0,0],[3.,0,0,0,0,0]]),
                    jnt_range=np.tile([-.0001,.0001],(40,1)), jnt_qposadr=np.arange(40),
                    jnt_dofadr=np.arange(40), geom_rgba=np.ones((20,4)), site_pos=np.zeros((1,3)),
                    site_size=np.array([[.25,0,0]]), geom_type=np.full(20,5),
                    geom_size=np.tile([.4,1.,0.],(20,1)))
                self.data = types.SimpleNamespace(qpos=np.zeros(40),qvel=np.zeros(40),ctrl=np.zeros(2),time=0.)
                self._obstacle_xy = np.zeros((20,2),np.float32)
                self._goal_xy = np.zeros(2,np.float32)
                self._xy = self._prev_xy = np.zeros(2)
                self._yaw = self._t = self._speed = self._stall_steps = 0
                self._last_action = np.zeros(2); self._action_scale = 2.
                self.planner = types.SimpleNamespace()
            def place_robot(self,x,y,yaw,*unused): self._xy,self._yaw=np.array([x,y]),yaw
            def _base_xy(self): return self._xy
            def _base_yaw(self): return self._yaw
            def _reset_exploration(self): pass
            def _get_obs(self): return {}

        native = types.SimpleNamespace(get_mjcb_control=lambda:None,mjtObj=types.SimpleNamespace(mjOBJ_ACTUATOR=0),
            mj_name2id=lambda model,kind,name:('left_motor','right_motor').index(name),mj_forward=lambda *args:None)
        original_configure = memory_world.configure
        def values(model):
            return {'immutable_sha256':study.PROTOCOL['initial_admission']['nominal_authored_model_sha256'],
                **{k:np.array(getattr(model,k),copy=True) for k in ('actuator_gear','jnt_range','geom_rgba','site_pos')}}

        for corruption in (None,'cache','native'):
            with self.subTest(corruption=corruption):
                env = Env()
                engine = types.SimpleNamespace(env=env,controller='manual',scenario='reproduction',seed=1,phase='paused',
                    policy=None,teacher=None,body_state=None,task_state=None,memory=None,episode_step=0,_pending=[],
                    manual_action=np.zeros(2),revision=0,episode=0,writer=types.SimpleNamespace(manifest={},event=Mock()),
                    world=lambda:{'pose':[*env._base_xy().tolist(),env._base_yaw()]})
                def configure(*args):
                    result=original_configure(*args)
                    if corruption=='cache': env._obstacle_xy[0,0]=np.nextafter(np.float32(0),np.float32(1))
                    if corruption=='native': env.model.jnt_range[0,0]+=1e-12
                    return result
                with patch.dict(sys.modules,{'mujoco':native}),patch.object(memory_world,'configure',side_effect=configure), \
                        patch.object(study,'model_values',side_effect=values),patch.object(study,'encoder_sample',return_value=[0.,0.]), \
                        patch.object(snapshots,'_model_digest',return_value='a'*64),patch.object(profiles,'validate_world'), \
                        patch.object(task,'body_calibration',return_value={'radius_m':.06,'track_m':.36,'quantum_rad':.001}):
                    if corruption is not None:
                        with self.assertRaisesRegex(ValueError,'cache' if corruption=='cache' else 'jnt_range'):
                            study.author_episode(engine,None)
                        engine.writer.event.assert_not_called()
                    else:
                        context=study.author_episode(engine,None)
                        self.assertEqual(float(env._obstacle_xy[5,0]),3.700000047683716)
                        np.testing.assert_array_equal(env.model.jnt_range[10],[3.7-.0001,3.7+.0001])
                        self.assertEqual(context['gear'][0][0],2.1)
                        engine.writer.event.assert_called_once()

    def test_numeric_and_whole_study_quota_refusal(self):
        arrays = {name: np.zeros((128, 128, 3), np.uint8) for name in
                  ('cam_left','cam_right','raw_cam_left','raw_cam_right')}
        extras = body.contact_arrays(interval())
        self.assertLess(study.numeric_admission(arrays, extras), study.LIMITS['bytes_per_interval_allowance'])
        with self.assertRaises(ValueError): study.numeric_admission(arrays, {'study_big': np.zeros(32769, np.uint8)})
        self.assertEqual(study.capacity_numbers(0, 3*1024**3)['required_free_bytes'], 3*1024**3)
        with self.assertRaises(ValueError): study.capacity_numbers(0, 3*1024**3-1)
        with self.assertRaises(ValueError): study.capacity_numbers(2*1024**3, 10*1024**3)

    def test_full_augmented_row_admitted_before_runtime(self):
        observation={name:np.zeros((128,128,3),np.uint8) for name in ('cam_left','cam_right')}
        receipt=study.row_preflight(observation)
        self.assertLessEqual(receipt['extra_bytes'],32768)
        self.assertLessEqual(receipt['row_allowance'],233472)
        self.assertEqual(receipt['row_allowance'],receipt['extra_bytes']+receipt['base_bytes']+4096)
        observation['cam_left']=np.zeros((2,2,3),np.uint8)
        with self.assertRaises(ValueError): study.row_preflight(observation)

    def test_fresh_initial_guard_never_relables_old_body(self):
        env=types.SimpleNamespace(data=types.SimpleNamespace(time=0.,qvel=np.zeros(2),ctrl=np.zeros(2)),
            _t=0,_speed=0.,_stall_steps=0,_last_action=np.zeros(2))
        engine=types.SimpleNamespace(env=env,controller='manual',scenario='reproduction',seed=1,phase='paused',
            policy=None,teacher=None,body_state=None,task_state=None,memory=None,
            episode_step=0,_pending=[],manual_action=np.zeros(2))
        with patch.object(study,'encoder_sample',return_value=[0.,0.]):
            study.fresh_state(engine)
            env._body_profile_identity={'old':'identity'}
            with self.assertRaises(ValueError): study.fresh_state(engine)
            self.assertEqual(env._body_profile_identity,{'old':'identity'})
            del env._body_profile_identity
            env.data.qvel[0]=.001
            with self.assertRaises(ValueError): study.fresh_state(engine)

    def test_fixed_fresh_configuration_refuses_other_routes(self):
        source={'fixture':'source'}
        with tempfile.TemporaryDirectory() as temp,patch.object(study,'sources',return_value=source):
            root=Path(temp)
            config={'kind':'calibration','run_id':'1'*32,'run':str(root/'calibration'/('1'*32)),
                    'output':str(root),'assets':str(root/'assets'),'sources':source,'fit_ref':None}
            self.assertEqual(study.validate_config(config),(root,Path(config['run'])))
            for change in ({'restore':True},{'seed':1.0},{'fit_ref':{}},{'run_id':True},{'sources':{}}):
                with self.subTest(change=change),self.assertRaises((ValueError,TypeError)):
                    study.validate_config({**config,**change})

    def test_real_default_engine_application_raw_initial(self):
        # Engine construction around a pure fixture, not Engine.open/native loading.
        from palimpsest.engine import Engine
        from test_engine import SmallEnv
        with tempfile.TemporaryDirectory() as temp:
            writer=RunWriter(Path(temp)/'recording',{'run_id':'fixture'})
            engine=Engine(SmallEnv(),writer,seed=1)
            try:
                application=engine.application_state()
                self.assertIn('task_state',application)
                self.assertIsNone(application['task_state'])
                self.assertNotIn('body_state',application)
                study.raw_initial_admission(application)
                for change in ({'task_state':{}},{'body_state':None},{'scenario':'encoder-homing'}):
                    with self.subTest(change=change),self.assertRaises(ValueError):
                        study.raw_initial_admission({**application,**change})
            finally: engine.close()

    def test_real_fit_container_pins_and_order(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'fit.json'; source={'fixture':'source'}
            artifact={'protocol_sha256':study.PROTOCOL_SHA256,'sources_sha256':body._sha(source),
                'producer_run_id':'1'*32,'full_model_sha256':'a'*64,'samples':samples(),
                'samples_sha256':body._sha(samples()),'fit':study.fit_samples(samples())}
            artifact['fit_sha256']=body._sha(artifact['fit'])
            study.write_json(path,artifact,max_bytes=128*1024)
            reference={'path':str(path),'sha256':study.digest(path),'producer_run_id':'1'*32,'full_model_sha256':'a'*64}
            self.assertEqual(study.read_fit(reference,source),artifact)
            with self.assertRaises(ValueError): study.read_fit(reference,{'fixture':'changed'})
            path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaises(ValueError): study.read_fit(reference,source)

    def stage_fixture(self, root, failure):
        source={'fixture':'source'}; changed=False
        rows=[{'id':kind,'run_id':str(index)*32,'run':str(root/kind/(str(index)*32)),
               'max_ticks':limit,'status':'not_started'}
              for index,(kind,limit) in enumerate((('calibration',480),('homing',600)),1)]
        def child(argv,*args,**kwargs):
            nonlocal changed
            config=json.loads(argv[-1]); run=Path(config['run']); run.mkdir(parents=True)
            functional=failure=='negative'
            result={'kind':config['kind'],'run_id':config['run_id'],'protocol_sha256':study.PROTOCOL_SHA256,
                'sources':source,'source_unchanged':True,'engine_closed':True,'callback_restored':True,
                'cleanup_errors':[],'status':'failed-functional' if functional else 'completed',
                'functional_passed':not functional,'executed_ticks':50 if functional else 480,
                'accepted_numeric_ticks':50 if functional else 480,'sample_count':400,'snapshots':[{}]*4,
                'fit_ref':{'path':str(run/'fit.json'),'sha256':'b'*64,
                           'producer_run_id':config['run_id'],'full_model_sha256':'a'*64}}
            if failure=='malformed': result['run_id']='wrong'
            if failure=='coverage': result['sample_count']=399
            study.write_json(run/'result.json',result,max_bytes=study.MiB)
            changed=failure=='source-drift'
            return {'status':'completed','returncode':0,'elapsed_seconds':181. if failure=='late' else .1}
        with patch.object(study,'sources',side_effect=lambda: {'fixture':'changed'} if changed else source), \
                patch.object(study,'capacity_check'), \
                patch.object(study,'read_fit',side_effect=ValueError('fit changed') if failure=='fit-drift' else None), \
                patch('palimpsest.evaluate.bounded_process',side_effect=child) as invoked:
            if failure=='source-drift':
                with self.assertRaisesRegex(ValueError,'Sources changed'):
                    study.collect_rows(root,root/'assets',rows,None,source,time.monotonic())
            else:
                study.collect_rows(root,root/'assets',rows,None,source,time.monotonic())
            self.assertEqual(invoked.call_count,1)
        self.assertEqual(rows[1]['status'],'not_started')
        self.assertNotEqual(rows[0]['status'],'running')
        return rows

    def test_clean_negative_calibration_stops_homing_without_infrastructure_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            rows=self.stage_fixture(Path(temp),'negative')
            self.assertEqual(rows[0]['status'],'failed-functional')
            self.assertEqual(study.reduce_rows(rows),{'status':'failed-functional',
                'operational_status':'completed','functional_status':'failed'})

    def test_parent_admission_terminalizes_malformed_coverage_or_fit_drift(self):
        for failure in ('malformed','coverage','fit-drift','late'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as temp:
                rows=self.stage_fixture(Path(temp),failure)
                self.assertEqual(rows[0]['status'],'failed-infrastructure')
                self.assertIn('error',rows[0])
                self.assertEqual(study.reduce_rows(rows)['operational_status'],'failed')

    def test_source_drift_before_homing_leaves_it_unstarted(self):
        with tempfile.TemporaryDirectory() as temp:
            rows=self.stage_fixture(Path(temp),'source-drift')
            self.assertEqual(rows[0]['status'],'completed')

    def test_outcome_is_distinct_from_engine_and_requires_true_closure(self):
        state = {'phase': 'complete', 'outbound_reached': True, 'dwell_ticks': 5}
        self.assertTrue(study.task_outcome(state, 200, [-3.4, 0.], None)['passed'])
        self.assertFalse(study.task_outcome(state, 200, [-3., 0.], None)['passed'])
        self.assertFalse(study.task_outcome(state, 200, [-3.4, 0.], {'reason':'stalled'})['passed'])
        self.assertFalse(study.task_outcome({'phase':'home','outbound_reached':True,'dwell_ticks':4}, 600, [-3.5,0.], None)['passed'])
        rows = [{'id':'calibration','status':'failed-functional'}, {'id':'homing','status':'not_started'}]
        self.assertEqual(study.reduce_rows(rows)['functional_status'], 'failed')
        self.assertEqual(rows[1]['status'], 'not_started')

    def test_real_writer_reject_packet_is_retained_without_publication(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); writer = RunWriter(root/'recording', {'run_id':'fixture'}, max_bytes=1024**2)
            engine = types.SimpleNamespace(writer=writer, episode=0, episode_step=0, total_tick=0,
                env=types.SimpleNamespace(data=types.SimpleNamespace(time=0., ctrl=np.zeros(2))),
                last_transition=None, phase='paused')
            probe = types.SimpleNamespace(active=False, stages=[], count=0)
            def begin(tick): probe.active=True
            def end(): probe.active=False; return interval(rejected=True)
            probe.begin=begin;probe.end=end
            def command(e, identifier, kind, payload=None):
                if kind=='step':
                    e.writer.tick(0,0,action=np.zeros(2),control=np.zeros(2),
                                  cam_left=np.arange(48,dtype=np.uint8).reshape(4,4,3),
                                  sensors=np.array([0.,0.,-1.,0.],np.float32))
                    e.env.data.time=.02;e.total_tick=1;e.episode_step=1
                    e.last_transition={'action':np.zeros(2),'control':np.zeros(2)}
            plan=study.control_plan([0.,0.], None)
            with patch.object(study,'command',command), patch.object(study,'encoder_sample',return_value=[0.,0.]):
                with self.assertRaises(ValueError):
                    study.measured_interval(engine, probe, plan, {}, root/'rejected.json', None)
            writer.finish({'fixture':True})
            self.assertEqual(list(iter_ticks(root/'recording')), [])
            rejected=json.loads((root/'rejected.json').read_text())
            self.assertTrue(rejected['interval']['contact'])
            self.assertEqual(rejected['executed_interval'], 1)
            self.assertEqual(rejected['pending_numeric'], {'episode':0,'tick':0})
            accounting=study.interval_accounting(root,0,engine.total_tick)
            self.assertEqual(accounting['accepted_numeric_ticks'],0)
            self.assertEqual(accounting['executed_ticks'],1)
            self.assertEqual(accounting['rejected_packet']['raw_pending'],rejected['raw_pending'])
            with self.assertRaises(ValueError): study.interval_accounting(root,1,1)
            with self.assertRaises(ValueError): study.interval_accounting(root,0,2)
            retained=root/rejected['raw_pending']['path']
            self.assertEqual(hashlib.sha256(retained.read_bytes()).hexdigest(), rejected['raw_pending']['sha256'])
            with np.load(retained,allow_pickle=False) as raw:
                self.assertEqual(set(raw.files), {'action','control','cam_left','sensors'})
                np.testing.assert_array_equal(raw['cam_left'],np.arange(48,dtype=np.uint8).reshape(4,4,3))
                np.testing.assert_array_equal(raw['control'],np.zeros(2))
                np.testing.assert_array_equal(raw['sensors'],[0.,0.,-1.,0.])
                for name in raw.files:
                    self.assertEqual(hashlib.sha256(raw[name].tobytes()).hexdigest(),
                                     rejected['raw_pending']['arrays'][name]['sha256'])
                    self.assertEqual(raw[name].dtype.str,rejected['raw_pending']['arrays'][name]['dtype'])
            self.assertFalse(probe.active)
            self.assertEqual(writer.tick.__func__, RunWriter.tick)


if __name__ == '__main__':
    unittest.main()
