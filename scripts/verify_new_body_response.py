"""Fixed standalone two-owner study; private fit/task state is not restorable.

Actual invocation requires separately reviewed outer controls/runtime GO. Imports
and the pure functions below do not construct an environment or acquire a lease.
"""
import argparse
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

import numpy as np
from palimpsest import body_profile as body, task_profiles as task
from palimpsest.task_mechanics import fit_wheel_gains, compensate_wheels
from verify_body_gains import write_json
from verify_tasks import command, cue_action

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = Path('docs/plans/m6-new-body-response-protocol.json')
PROTOCOL_SHA256 = '8ea826bf4981d3db70bada1ea88db9a0d8707a3a9433e7c247e4254ec7f24672'
MiB = 1024**2


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path, limit):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError('Missing, linked or oversized study JSON')
    with path.open('rb') as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('Study JSON grew beyond limit')
    return json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def read_protocol(root):
    root = Path(root)
    if digest(root / PROTOCOL_PATH) != PROTOCOL_SHA256:
        raise ValueError('Fixed study protocol differs')
    result = read_json(root / PROTOCOL_PATH, MiB)
    for name, expected in result['protected_sources_sha256'].items():
        if digest(root / name) != expected:
            raise ValueError('Protected study source differs: ' + name)
    return result


PROTOCOL = read_protocol(ROOT)
LIMITS = PROTOCOL['limits']


def sources():
    from verify_endurance import source_identity
    result = source_identity(ROOT)
    for name in [*PROTOCOL['protected_sources_sha256'], str(PROTOCOL_PATH),
                 'scripts/verify_new_body_response.py', 'tests/test_new_body_response.py']:
        result['files_sha256'][name] = digest(ROOT / name)
    return result


def fit_samples(samples):
    if type(samples) is not list or len(samples) != 400:
        raise ValueError('Calibration requires all 400 ordered samples')
    values = []
    for index, sample in enumerate(samples):
        if (type(sample) is not dict or set(sample) != {'trial','tick','control','increments_rad','dt_s','contact'}
                or type(sample['trial']) is not int or type(sample['tick']) is not int
                or (sample['trial'], sample['tick']) != (index // 100, 20 + index % 100)
                or sample['control'] != body.effective_control(PROTOCOL['calibration']['trials'][index // 100]['action'])):
            raise ValueError('Calibration sample order/probe control differs')
        values.append({key: sample[key] for key in ('control','increments_rad','dt_s','contact')})
    fits = [fit_wheel_gains(values[i:i+100], **PROTOCOL['calibration']['fit_bounds']) for i in range(0,400,100)]
    pooled = fit_wheel_gains(values, **PROTOCOL['calibration']['fit_bounds'])
    agreement = []
    for wheel in range(2):
        gains = [item['gains_rad_s_per_control'][wheel] for item in fits]
        agreement.append((max(gains)-min(gains))/(sum(gains)/4))
    if any(value > .2 for value in agreement):
        raise ValueError('Four-trial gain agreement rejects calibration')
    compensate_wheels([0.,0.], pooled,
        nominal_gains_rad_s_per_control=PROTOCOL['calibration']['nominal_gains_rad_s_per_control'],
        max_compensation_ratio=1.5)
    return {'pooled':pooled, 'per_trial':fits, 'gain_range_over_mean':agreement}


def control_plan(requested, fitted, *, hold=False):
    requested = list(map(float, requested))
    nominal = [0.,0.] if hold else requested
    control = body.effective_control(nominal)
    corrected = control if fitted is None else compensate_wheels(control, fitted['pooled'],
        nominal_gains_rad_s_per_control=PROTOCOL['calibration']['nominal_gains_rad_s_per_control'],
        max_compensation_ratio=1.5)['control']
    inverse = body.inverse_control(corrected)
    return {'requested_action':requested, 'hold':bool(hold), 'nominal_action':nominal,
            'nominal_control':control, 'applied_action':inverse['action'],
            'applied_control':inverse['control_float32'], 'rounding_delta':inverse['rounding_delta']}


def study_action(state, packet, previous_cue, fitted):
    # Deliberately no Engine, observation, pose or evaluator argument.
    requested = cue_action(None if previous_cue is None else np.asarray(previous_cue, np.float32).astype(np.float64).tolist(), driver='v2')
    advanced, cue, hold, _ = task.advance(copy.deepcopy(state), packet)
    return advanced, np.asarray(cue, np.float32), control_plan(requested, fitted, hold=hold)


def validate_model_change(before, after, joints, positions, goal_site):
    keys = {'immutable_sha256','actuator_gear','jnt_range','geom_rgba','site_pos'}
    if set(before) != keys or set(after) != keys or before['immutable_sha256'] != after['immutable_sha256'] or before['immutable_sha256'] != PROTOCOL['initial_admission']['nominal_authored_model_sha256']:
        raise ValueError('Immutable native model differs')
    expected = {key: np.array(before[key], copy=True) for key in keys - {'immutable_sha256'}}
    if expected['actuator_gear'].shape != (2,6) or expected['actuator_gear'].tolist() not in (
            [[3.,0.,0.,0.,0.,0.],[3.,0.,0.,0.,0.,0.]], [[2.1,0.,0.,0.,0.,0.],[3.,0.,0.,0.,0.,0.]]):
        raise ValueError('Only nominal or this already-authored study gear admitted')
    expected['actuator_gear'][0,0] = 2.1
    if len(joints) != len(positions) or len({j for pair in joints for j in pair}) != 2*len(joints):
        raise ValueError('Named obstacle joint correspondence differs')
    for pair, xy in zip(joints, positions):
        if len(pair) != 2 or len(xy) != 2:
            raise ValueError('Obstacle authoring shape differs')
        for joint, coordinate in zip(pair, xy):
            width = float((before['jnt_range'][joint,1]-before['jnt_range'][joint,0])/2)
            if not math.isfinite(width) or not 0 < width <= .001 or not math.isfinite(coordinate):
                raise ValueError('Obstacle lock width/coordinate differs')
            expected['jnt_range'][joint] = [coordinate-width, coordinate+width]
    expected['site_pos'][goal_site,:2] = [-3.5,3.]
    for key, value in expected.items():
        candidate = np.asarray(after[key])
        if candidate.dtype != value.dtype or candidate.shape != value.shape or not np.isfinite(candidate).all() or not np.array_equal(candidate, value):
            raise ValueError('Undeclared native model mutation: ' + key)


def numeric_admission(arrays, extra):
    from palimpsest.records import CHUNK_TICKS, MAX_CHUNK_BYTES
    if set(arrays) & set(extra):
        raise ValueError('Study fields cannot replace Engine arrays')
    values = {key:np.asarray(value) for key,value in {**arrays,**extra}.items()}
    if any(value.dtype.kind not in 'biuf' or not np.isfinite(value).all() for value in values.values()):
        raise ValueError('Nonfinite/nonnumeric study packet')
    extra_bytes = sum(np.asarray(value).nbytes for value in extra.values())
    count = sum(value.nbytes for value in values.values())
    if extra_bytes > 32768 or count+4096 > LIMITS['bytes_per_interval_allowance'] or count*CHUNK_TICKS > MAX_CHUNK_BYTES:
        raise ValueError('Study row exceeds frozen field/chunk allowance')
    return count+4096


def capacity_numbers(used, free):
    required = LIMITS['output_max_bytes'] + LIMITS['min_free_bytes']
    if type(used) is not int or type(free) is not int or used < 0 or free < required or used+LIMITS['whole_study_admission_bytes'] > LIMITS['output_max_bytes']:
        raise ValueError('Fresh whole-study capacity unavailable')
    return {'used_bytes':used, 'free_bytes':free, 'required_free_bytes':required,
            'admission_bytes':LIMITS['whole_study_admission_bytes']}


def task_outcome(state, ticks, xy, engine_outcome):
    distance = math.dist(list(map(float,xy)), [-3.5,0.])
    complete = state['phase'] == 'complete' and state['outbound_reached'] is True and state['dwell_ticks'] == 5
    passed = complete and 0 < ticks <= 600 and math.isfinite(distance) and distance <= .25 and engine_outcome is None
    return {'passed':passed, 'study_outcome':'task_completed' if complete else 'time_limit' if ticks==600 else 'engine_terminal',
            'engine_outcome':copy.deepcopy(engine_outcome), 'ticks':ticks,
            'evaluator_actual_home_distance_m':distance, 'evaluator_only':True}


def reduce_rows(rows):
    if [row['id'] for row in rows] != ['calibration','homing']:
        raise ValueError('Exact fixed two-row ledger required')
    failed = any(row['status']=='failed-infrastructure' for row in rows)
    passed = all(row['status']=='completed' and row.get('functional_passed') is True for row in rows)
    return {'operational_status':'failed' if failed else 'completed', 'functional_status':'passed' if passed else 'failed',
            'status':'passed' if passed and not failed else 'failed-infrastructure' if failed else 'failed-functional'}


def encoder_sample(env):
    return task.encoder_angles(env)


def retain_rejected(path, pending, packet, budget):
    """Keep the complete unpublished numeric payload, not just its coordinates."""
    path = Path(path)
    if path.exists() or path.with_suffix('.npz').exists():
        raise ValueError('First rejection evidence already exists')
    packet = copy.deepcopy(packet)
    if pending:
        episode, tick, arrays = pending[0]
        values = {key:np.array(value,copy=True) for key,value in arrays.items()}
        if any(value.dtype.kind not in 'biuf' for value in values.values()) or sum(value.nbytes for value in values.values()) > LIMITS['bytes_per_interval_allowance']:
            raise ValueError('Rejected raw payload exceeds frozen bounded numeric input')
        with io.BytesIO() as stream:
            np.savez(stream, **values)
            raw = stream.getvalue()
        if len(raw) > LIMITS['bytes_per_interval_allowance']+65536:
            raise ValueError('Rejected NPZ exceeds bounded container allowance')
        destination = path.with_suffix('.npz')
        if budget is not None: budget.check(len(raw), path=destination)
        with destination.open('xb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        packet.update(pending_numeric={'episode':episode,'tick':tick},
            raw_pending={'path':destination.name, 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest(),
                'arrays':{key:{'dtype':value.dtype.str,'shape':list(value.shape),
                    'sha256':hashlib.sha256(value.tobytes()).hexdigest()} for key,value in values.items()}})
    write_json(path, packet, max_bytes=MiB, storage_budget=budget)


def measured_interval(engine, probe, plan, study_arrays, rejected_path, budget):
    original = engine.writer.tick
    pending = []
    episode, tick = engine.episode, engine.episode_step
    before = encoder_sample(engine.env); timestamp = float(engine.env.data.time)
    start_tick = engine.total_tick
    packet = {'episode':episode, 'tick':tick, 'interval':None, 'plan':plan, 'encoder_before':before}
    def defer(e, t, **arrays):
        if pending: raise ValueError('Only one pending study interval permitted')
        pending.append((e,t,{key:np.array(value,copy=True) for key,value in arrays.items()}))
    engine.writer.tick = defer
    try:
        command(engine, f'action-{episode}-{tick}', 'set_action', {'action':plan['applied_action']})
        probe.begin(tick)
        try:
            command(engine, f'step-{episode}-{tick}', 'step')
        finally:
            if probe.active: packet['interval'] = probe.end()
        after = encoder_sample(engine.env); dt = float(engine.env.data.time)-timestamp
        packet.update(encoder_after=after, dt_s=dt, control=engine.env.data.ctrl.tolist())
        interval = packet['interval']
        if (len(pending)!=1 or pending[0][:2]!=(episode,tick) or interval is None
                or interval['contact'] is not False or interval['coverage_passed'] is not True
                or packet['control']!=plan['applied_control']
                or engine.last_transition['action'].tolist()!=plan['applied_action']
                or not math.isclose(dt,.02,abs_tol=1e-9,rel_tol=0.)):
            raise ValueError('Rejected contact/control/timing/numeric interval')
        increments = np.asarray(after,np.float64)-np.asarray(before,np.float64)
        if not np.isfinite(increments).all() or np.any(np.abs(increments/dt)>100.):
            raise ValueError('Measured encoder rate outside fixed bound')
        extra = {**body.contact_arrays(interval), **study_arrays,
            'body_encoder_before':np.asarray(before,np.float64), 'body_encoder_after':np.asarray(after,np.float64),
            'body_encoder_increment':increments, 'body_dt':np.array(dt,np.float64),
            'body_nominal_action':np.asarray(plan['nominal_action'],np.float64),
            'body_nominal_control':np.asarray(plan['nominal_control'],np.float32),
            'study_requested_action':np.asarray(plan['requested_action'],np.float64),
            'study_hold':np.array(plan['hold'],np.bool_)}
        numeric_admission(pending[0][2], extra)
        original(episode,tick,**pending[0][2],**extra)
        pending.clear()
        return {'trial':episode,'tick':tick,'control':packet['control'],
                'increments_rad':increments.tolist(),'dt_s':dt,'contact':False}
    except BaseException as error:
        if probe.active:
            try: packet['interval'] = probe.end()
            except Exception as closing: packet['probe_end_error'] = str(closing)[:512]
        packet.update(error={'type':type(error).__name__,'message':str(error)[:1024]},
                      executed_interval=engine.total_tick-start_tick)
        retain_rejected(rejected_path,pending,packet,budget)
        raise
    finally:
        engine.writer.tick = original


def study_fields(state, cue, trial):
    odometry = None if state is None else state['odometry']
    return {'study_trial':np.array(trial,np.int64), 'study_cue':np.asarray(cue,np.float32),
            'study_phase':np.array(-1 if state is None else ('outbound','home','complete').index(state['phase']),np.int8),
            'study_odometry':np.array([0.]*4 if odometry is None else
                [odometry[key] for key in ('x_m','y_m','yaw_rad','travel_m')],np.float64),
            'study_dwell_ticks':np.array(0 if state is None else state['dwell_ticks'],np.int64),
            'study_outbound_reached':np.array(False if state is None else state['outbound_reached'],np.bool_)}


def row_preflight(observation):
    # Shape-only admission; these arrays are never emitted as measured data.
    cameras = {name:np.asarray(observation[name]) for name in ('cam_left','cam_right')}
    if any(value.dtype!=np.uint8 or value.shape!=(128,128,3) for value in cameras.values()):
        raise ValueError('Fixed 128x128 RGB recording required')
    base = {**cameras, **{'raw_'+name:value for name,value in cameras.items()},
        'sensors':np.zeros(4,np.float32), 'action':np.zeros(2), 'control':np.zeros(2),
        'pose':np.zeros(3), 'next_pose':np.zeros(3), 'reward':np.array(0.),
        'simulation_time':np.array(0.), 'latency':np.array(0.), 'step_latency':np.array(0.),
        'eyes':np.ones(2,np.bool_), 'revision':np.array(0), 'population_stats':np.zeros((0,4))}
    packet = {'coverage_passed':True, 'callback_count':10,
              'stages':[{'time_s':i*.002,'control':[0.,0.],'pairs':[]} for i in range(10)],
              'end':{'data_time_s':.02,'contact_cache_time_s':.018,'pairs':[]}}
    extra = {**body.contact_arrays(packet), **study_fields(None,[0.,0.],0),
        'body_encoder_before':np.zeros(2), 'body_encoder_after':np.zeros(2), 'body_encoder_increment':np.zeros(2),
        'body_dt':np.array(.02), 'body_nominal_action':np.zeros(2), 'body_nominal_control':np.zeros(2,np.float32),
        'study_requested_action':np.zeros(2), 'study_hold':np.array(False)}
    return {'row_allowance':numeric_admission(base,extra),
            'extra_bytes':sum(value.nbytes for value in extra.values()),
            'base_bytes':sum(value.nbytes for value in base.values()), 'scope':'shape admission, not recorded telemetry'}


def model_values(model):
    import mujoco
    from palimpsest.snapshots import _model_digest
    clone = mujoco.MjModel.__new__(mujoco.MjModel)
    clone.__setstate__(model.__getstate__())
    clone.actuator_gear[0,0] = 3.
    return {'immutable_sha256':_model_digest(clone),
            **{key:np.array(getattr(model,key),copy=True) for key in ('actuator_gear','jnt_range','geom_rgba','site_pos')}}


def fresh_state(engine):
    env = engine.env
    if (engine.controller!='manual' or engine.scenario!='reproduction' or engine.seed!=1 or engine.phase!='paused'
            or engine.policy is not None or engine.teacher is not None or engine.body_state is not None
            or engine.task_state is not None or engine.memory is not None or hasattr(env,'_body_profile_identity')
            or engine.episode_step!=0 or engine._pending or float(env.data.time)!=0.
            or env._t!=0 or env._speed!=0. or env._stall_steps!=0
            or np.any(env.data.qvel) or np.any(env.data.ctrl) or np.any(env._last_action)
            or np.any(engine.manual_action) or encoder_sample(env)!=[0.,0.]):
        raise ValueError('Fresh standalone reproduction state required')


def author_episode(engine, expected_model):
    import mujoco
    from palimpsest import memory_world
    from palimpsest.profiles import validate_world
    from palimpsest.snapshots import _model_digest
    fresh_state(engine)
    env = engine.env
    if mujoco.get_mjcb_control() is not None or env.n_obstacles!=20 or env.model.nu!=2:
        raise ValueError('Fixed body topology/callback admission failed')
    if tuple(mujoco.mj_name2id(env.model,mujoco.mjtObj.mjOBJ_ACTUATOR,name) for name in ('left_motor','right_motor'))!=(0,1):
        raise ValueError('Named motor ordering differs')
    before = model_values(env.model); old_world = engine.world()
    original_model_sha256 = _model_digest(env.model)
    original_full_model_sha256 = hashlib.sha256(env.model.__getstate__()).hexdigest()
    memory_world.configure(env,memory_world.initial_state(close_subject_id=None))
    env._goal_xy[:] = [-3.5,3.]
    env.model.site_pos[env.goal_site_id,:2] = [-3.5,3.]
    env.place_robot(-3.5,0.,0.,env.data.qpos.copy(),env.data.qvel.copy())
    env.model.actuator_gear[0,0] = 2.1
    mujoco.mj_forward(env.model,env.data)
    env._prev_xy = env._base_xy().copy()
    env._reset_exploration()
    engine.observation = env._get_obs()
    joints = list(map(list,zip(env.obstacle_x_joint_ids,env.obstacle_y_joint_ids)))
    authored_positions = memory_world.validate_layout()
    if env._obstacle_xy.dtype != np.float32 or not np.array_equal(env._obstacle_xy,np.asarray(authored_positions,np.float32)):
        raise ValueError('Authored obstacle cache differs')
    validate_model_change(before,model_values(env.model),joints,authored_positions,env.goal_site_id)
    validate_world(env); fresh_state(engine)
    calibration = task.body_calibration(env)
    if (calibration['radius_m']!=.06 or not math.isclose(calibration['track_m'],.36,rel_tol=0.,abs_tol=1e-12)
            or calibration['quantum_rad']!=.001 or float(env._action_scale)!=2.
            or math.dist(env._base_xy(),[-3.5,0.])>1e-7 or abs(math.remainder(float(env._base_yaw()),math.tau))>1e-7
            or not np.array_equal(env._prev_xy,env._base_xy()) or env._goal_xy.tolist()!=[-3.5,3.]):
        raise ValueError('Declared initial physical state/calibration differs')
    full_model = hashlib.sha256(env.model.__getstate__()).hexdigest()
    if expected_model is not None and full_model!=expected_model:
        raise ValueError('Fresh episode model differs from the fixed study body')
    engine.revision += 1
    context = {'protocol_sha256':PROTOCOL_SHA256,'original_world':old_world,'actual_world':engine.world(),
               'original_world_sha256':body._sha(old_world),'actual_world_sha256':body._sha(engine.world()),
               'original_model_sha256':original_model_sha256,'original_full_model_sha256':original_full_model_sha256,
               'full_model_sha256':full_model,'model_sha256':_model_digest(env.model),
               'gear':env.model.actuator_gear.tolist(),'calibration':calibration,
               'scope':'standalone override; original Engine sensors/outcome retained; no custom-state restore/replay'}
    engine.writer.manifest.update(standalone_body_study=PROTOCOL['id'],study_protocol_sha256=PROTOCOL_SHA256,
        initial_world=context['actual_world'],study_world_override=context,
        study_state_restore_supported=False,study_generic_replay_qualified=False)
    engine.writer.event('study_world_authored',context=context,episode=engine.episode,revision=engine.revision)
    return context


def save_initial(engine, run, budget):
    import mujoco
    from palimpsest.snapshots import capture, save_snapshot
    from palimpsest.storage import StorageBudget, StorageLimits
    if mujoco.get_mjcb_control() is not None:
        raise ValueError('Raw initial snapshot requires callback removed')
    destination = run/'snapshots'/f'episode-{engine.episode}'/'initial.snp'
    budget.check(LIMITS['snapshot_max_bytes'],path=destination)
    destination.parent.mkdir(parents=True,exist_ok=False)
    shot_budget = StorageBudget((destination.parent,),StorageLimits(max_bytes=LIMITS['snapshot_max_bytes'],
        min_free_bytes=LIMITS['min_free_bytes'],max_snapshots=1))
    snapshot = capture(engine.env,engine.observation,application=engine.application_state())
    raw_initial_admission(snapshot['application'])
    size = save_snapshot(snapshot,destination,storage_budget=shot_budget)
    item = {'path':str(destination.relative_to(run)),'sha256':digest(destination),'bytes':size,
            'episode':engine.episode,'tick':0,'raw_initial_only':True}
    engine.writer.event('study_raw_initial',**item)
    return item


def raw_initial_admission(application):
    if (application.get('schema_version')!=4 or application.get('scenario')!='reproduction'
            or application.get('controller')!='manual' or application.get('phase')!='paused'
            or 'task_state' not in application or application['task_state'] is not None
            or application.get('memory') is not None or 'body_state' in application):
        raise ValueError('Raw initial requires the unchanged default Engine application envelope')


def budget_for(output, *, control=False):
    from palimpsest.storage import StorageBudget, StorageLimits
    return StorageBudget((output,),StorageLimits(max_bytes=LIMITS['output_max_bytes'],
        min_free_bytes=LIMITS['min_free_bytes'],max_runs=2,max_snapshots=5,max_exports=1),
        headroom_bytes=0 if control else 8*MiB)


def capacity_check(output, budget, remaining_bytes):
    report = capacity_numbers(budget.usage()['used_bytes'],int(shutil.disk_usage(output).free))
    budget.check(remaining_bytes,path=output/'report.json')
    return report


def read_fit(reference, expected_sources):
    path = Path(reference['path'])
    if digest(path)!=reference['sha256']:
        raise ValueError('Study fit bytes changed')
    result = read_json(path,128*1024)
    expected = {'protocol_sha256','sources_sha256','producer_run_id','full_model_sha256','samples','samples_sha256','fit','fit_sha256'}
    if (set(result)!=expected or result['protocol_sha256']!=PROTOCOL_SHA256
            or result['sources_sha256']!=body._sha(expected_sources)
            or result['producer_run_id']!=reference['producer_run_id']
            or result['full_model_sha256']!=reference['full_model_sha256']
            or result['samples_sha256']!=body._sha(result['samples'])):
        raise ValueError('Study fit producer/source/model/sample identity differs')
    recomputed = fit_samples(result['samples'])
    if result['fit']!=recomputed or result['fit_sha256']!=body._sha(recomputed):
        raise ValueError('Study fit does not follow its ordered measured samples')
    return result


def validate_config(config):
    keys = {'kind','run_id','run','output','assets','sources','fit_ref'}
    if type(config) is not dict or set(config)!=keys or config['kind'] not in ('calibration','homing'):
        raise ValueError('Exact fresh-only study owner configuration required')
    if any(type(config[key]) is not str for key in ('run_id','run','output','assets')):
        raise ValueError('Study paths/IDs require strings')
    if uuid.UUID(config['run_id']).hex!=config['run_id']:
        raise ValueError('Study requires a canonical UUID run ID')
    output, run = Path(config['output']), Path(config['run'])
    if not output.is_absolute() or run!=output/config['kind']/config['run_id'] or not Path(config['assets']).is_absolute():
        raise ValueError('Study owner paths differ from fixed row')
    if config['sources']!=sources():
        raise ValueError('Study sources changed before owner')
    reference = config['fit_ref']
    if config['kind']=='calibration':
        if reference is not None: raise ValueError('Calibration cannot load any prior fit')
    else:
        if type(reference) is not dict or set(reference)!={'path','sha256','producer_run_id','full_model_sha256'}:
            raise ValueError('Homing requires the exact same-study calibration artifact')
        if (type(reference['producer_run_id']) is not str or uuid.UUID(reference['producer_run_id']).hex!=reference['producer_run_id']
                or Path(reference['path'])!=output/'calibration'/reference['producer_run_id']/'fit.json'):
            raise ValueError('Historical/external fits cannot enter this study')
    return output, run


def progress(path, config, ticks, phase, budget):
    from verify_endurance import process
    write_json(path,{'kind':config['kind'],'run_id':config['run_id'],'owner':process(os.getpid()),
        'executed_ticks':ticks,'phase':phase,'monotonic_s':time.monotonic()}, max_bytes=MiB,storage_budget=budget)


def interval_accounting(run, accepted, executed):
    if type(accepted) is not int or type(executed) is not int or accepted<0 or executed-accepted not in (0,1):
        raise ValueError('Engine/published interval accounting differs')
    result={'accepted_numeric_ticks':accepted,'executed_ticks':executed}
    rejected=run/'rejected.json'
    if rejected.exists():
        packet=read_json(rejected,MiB)
        if packet.get('executed_interval')!=executed-accepted:
            raise ValueError('Rejected interval count differs from Engine count')
        if executed>accepted and (packet.get('pending_numeric') is None or 'raw_pending' not in packet):
            raise ValueError('Unpublished executed interval lacks its full rejected packet')
        result['rejected_packet']={'path':'rejected.json','sha256':digest(rejected),
                                   'raw_pending':packet.get('raw_pending')}
    elif executed>accepted:
        raise ValueError('Unpublished executed interval lacks rejection evidence')
    return result


def worker(config):
    started = time.monotonic()
    output, run = validate_config(config)
    budget = budget_for(output)
    run.mkdir(parents=True,exist_ok=False)
    report = {'kind':config['kind'],'run_id':config['run_id'],'status':'failed-infrastructure',
              'functional_passed':False,'executed_ticks':0,'snapshots':[],'sources':config['sources'],
              'protocol_sha256':PROTOCOL_SHA256,'cleanup_errors':[]}
    engine = probe = None
    samples = []
    expected_model = None
    fitted = reference = None
    try:
        import mujoco
        from palimpsest.engine import Engine
        if sys.version_info[:3]!=(3,11,15) or np.__version__!='2.2.5' or mujoco.__version__!='3.3.6':
            raise ValueError('Pinned actual runtime differs')
        if mujoco.get_mjcb_control() is not None:
            raise ValueError('Existing callback rejected before environment construction')
        if config['kind']=='homing':
            reference = read_fit(config['fit_ref'],config['sources'])
            fitted, expected_model = reference['fit'], reference['full_model_sha256']
        progress(run/'progress.json',config,0,'constructing',budget)
        engine = Engine.open(ROOT,Path(config['assets']),run/'recording',controller='manual',device='cpu',seed=1,
            scenario='reproduction',texture='checker',run_id=config['run_id'],
            max_bytes=LIMITS['recording_max_bytes_per_owner'],storage_budget=budget)
        trials = PROTOCOL['calibration']['trials'] if config['kind']=='calibration' else [None]
        task_state = previous_cue = None
        for trial_index, trial in enumerate(trials):
            if trial_index:
                command(engine,f'reset-{trial_index}','reset',{'seed':1})
            capacity_check(output,budget,LIMITS['whole_study_admission_bytes']-report['executed_ticks']*233472)
            context = author_episode(engine,expected_model)
            expected_model = context['full_model_sha256']
            report['full_model_sha256'] = expected_model
            report['row_preflight'] = row_preflight(engine.observation)
            report['snapshots'].append(save_initial(engine,run,budget))
            if trial is None:
                task_state = task.initialize('encoder-homing',f'episode-{engine.episode}',encoder_sample(engine.env),context['calibration'])
            probe = body.ContactProbe(mujoco,engine.env)
            engine.writer.manifest['study_contact_ownership'] = copy.deepcopy(probe.ownership)
            probe.install()
            progress(run/'progress.json',config,report['executed_ticks'],'ready',budget)
            for tick in range(120 if trial is not None else 600):
                if time.monotonic()-started>=180:
                    raise ValueError('Owner normal deadline exceeded')
                advanced, cue = None, np.zeros(2,np.float32)
                if trial is not None:
                    plan = control_plan(trial['action'],None)
                else:
                    packet = task.capture(engine.env,task_state,tick)
                    advanced,cue,plan = study_action(task_state,packet,previous_cue,fitted)
                row = measured_interval(engine,probe,plan,study_fields(advanced,cue,trial_index if trial is not None else -1),
                                        run/'rejected.json',budget)
                report['executed_ticks'] += 1
                if trial is not None and tick>=20: samples.append(row)
                if trial is None:
                    task_state,previous_cue = advanced,cue.copy()
                    engine.writer.event('study_task',tick=tick,state=task_state,study_cue=cue.tolist(),
                                        requested_action=plan['requested_action'],hold=plan['hold'])
                if hashlib.sha256(engine.env.model.__getstate__()).hexdigest()!=expected_model:
                    raise ValueError('Native model mutated during measured interval')
                progress(run/'progress.json',config,report['executed_ticks'],'measured',budget)
                if engine.phase!='paused' or trial is None and task_state['phase']=='complete':
                    break
            probe.close(); probe = None
            if trial is not None and (engine.episode_step!=120 or engine.phase!='paused'):
                report.update(status='failed-functional',reason='early_calibration_termination',engine_outcome=engine.last_outcome)
                break
        else:
            if config['kind']=='calibration':
                try:
                    fitted = fit_samples(samples)
                except ValueError as error:
                    report.update(status='failed-functional',reason='calibration_rejected',fit_rejection=str(error)[:1024])
                else:
                    artifact = {'protocol_sha256':PROTOCOL_SHA256,'sources_sha256':body._sha(config['sources']),
                        'producer_run_id':config['run_id'],'full_model_sha256':expected_model,
                        'samples':samples,'samples_sha256':body._sha(samples),'fit':fitted,'fit_sha256':body._sha(fitted)}
                    write_json(run/'fit.json',artifact,max_bytes=128*1024,storage_budget=budget)
                    report.update(status='completed',functional_passed=True,sample_count=len(samples),
                        fit_ref={'path':str(run/'fit.json'),'sha256':digest(run/'fit.json'),
                            'producer_run_id':config['run_id'],'full_model_sha256':expected_model})
            else:
                result = task_outcome(task_state,report['executed_ticks'],engine.env._base_xy(),engine.last_outcome)
                report.update(status='completed' if result['passed'] else 'failed-functional',
                    functional_passed=result['passed'],task_outcome=result,final_task_state=task_state,
                    frozen_fit_sha256=reference['fit_sha256'],frozen_samples_sha256=reference['samples_sha256'])
                read_fit(config['fit_ref'],config['sources'])
        report['engine_outcome_before_close'] = copy.deepcopy(engine.last_outcome)
    except BaseException as error:
        report.update(status='failed-infrastructure',functional_passed=False,
                      error={'type':type(error).__name__,'message':str(error)[:2048]})
    finally:
        if probe is not None:
            try: probe.close()
            except Exception as error: report['cleanup_errors'].append('callback: '+str(error)[:512])
        if engine is not None:
            accepted=report['executed_ticks']
            report.update(accepted_numeric_ticks=accepted,executed_ticks=engine.total_tick)
            try:
                report.update(interval_accounting(run,accepted,engine.total_tick))
            except Exception as error: report['cleanup_errors'].append('interval accounting: '+str(error)[:512])
            try: engine.close(); report['engine_closed']=True
            except Exception as error: report['cleanup_errors'].append('engine: '+str(error)[:512])
        try:
            if 'mujoco' in locals() and mujoco.get_mjcb_control() is not None:
                raise ValueError('Native callback survives owner cleanup')
            report['callback_restored']=True
        except Exception as error: report['cleanup_errors'].append('callback receipt: '+str(error)[:512])
        try:
            report['sources_at_end']=sources()
            if report['sources_at_end']!=config['sources']: raise ValueError('Study sources changed during owner')
            report['source_unchanged']=True
        except Exception as error: report['cleanup_errors'].append('source: '+str(error)[:512])
        report['wall_seconds']=time.monotonic()-started
        if report['wall_seconds']>=180 or report['cleanup_errors']:
            report.update(status='failed-infrastructure',functional_passed=False)
        write_json(run/'result.json',report,max_bytes=LIMITS['owner_result_max_bytes'],storage_budget=budget_for(output,control=True))
    return report


def collect_rows(output, assets, rows, budget, source_start, started):
    """Only the fixed calibration -> homing sequence; no retries or selection."""
    from palimpsest.evaluate import bounded_process
    for row in rows:
        if time.monotonic()-started>=780: raise ValueError('Study internal deadline exceeded')
        if sources()!=source_start: raise ValueError('Sources changed before next owner')
        reference = None if row['id']=='calibration' else rows[0]['result']['fit_ref']
        if reference is not None:
            read_fit(reference,source_start)
        capacity_check(output,budget,LIMITS['whole_study_admission_bytes'])
        config = {'kind':row['id'],'run_id':row['run_id'],'run':row['run'],'output':str(output),
                  'assets':str(assets),'sources':source_start,'fit_ref':reference}
        validate_config(config)
        row['status']='running'
        write_json(output/'rows.json',rows,max_bytes=MiB,storage_budget=budget)
        try:
            environment = os.environ.copy()
            environment['PYTHONPATH']=str(ROOT/'src')+os.pathsep+str(ROOT/'scripts')
            supervision = bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',json.dumps(config)],
                output/(row['id']+'-supervisor'),180,env=environment,log_max_bytes=MiB,storage_budget=budget)
            row['supervision']=supervision
            if (supervision.get('status')!='completed' or supervision.get('returncode')!=0
                    or type(supervision.get('elapsed_seconds')) not in (int,float)
                    or not 0<=supervision['elapsed_seconds']<180):
                raise ValueError('Owner supervision did not complete normally within its limit')
            result_path=Path(row['run'])/'result.json'
            result=read_json(result_path,LIMITS['owner_result_max_bytes'])
            row['result_sha256']=digest(result_path)
            if (result.get('kind')!=row['id'] or result.get('run_id')!=row['run_id']
                    or result.get('protocol_sha256')!=PROTOCOL_SHA256 or result.get('sources')!=source_start
                    or result.get('source_unchanged') is not True or result.get('engine_closed') is not True
                    or result.get('callback_restored') is not True or result.get('cleanup_errors')!=[]
                    or result.get('status') not in ('completed','failed-functional')
                    or result.get('functional_passed') is not (result['status']=='completed')
                    or type(result.get('executed_ticks')) is not int or not 0<=result['executed_ticks']<=row['max_ticks']
                    or type(result.get('accepted_numeric_ticks')) is not int
                    or result['accepted_numeric_ticks']!=result['executed_ticks']):
                raise ValueError('Owner result/cleanup/interval identity differs')
            if result['status']=='completed':
                if row['id']=='calibration':
                    if result['executed_ticks']!=480 or result.get('sample_count')!=400 or len(result.get('snapshots',[]))!=4:
                        raise ValueError('Positive calibration coverage differs')
                    read_fit(result['fit_ref'],source_start)
                elif len(result.get('snapshots',[]))!=1:
                    raise ValueError('Positive homing initial coverage differs')
            row.update(status=result['status'],functional_passed=result['functional_passed'],result=result)
        except BaseException as error:
            row.update(status='failed-infrastructure',functional_passed=False,
                       error={'type':type(error).__name__,'message':str(error)[:2048]})
        if row['status']!='completed':
            if row['id']=='calibration': rows[1]['dependency_failed']='calibration'
        write_json(output/'rows.json',rows,max_bytes=MiB,storage_budget=budget)
        if row['status']!='completed':
            break
    return rows


def verify(args):
    started = time.monotonic()
    output, assets = args.output.absolute(), args.assets.absolute()
    if output.exists(): raise ValueError('Study output must be fresh')
    read_protocol(ROOT)
    source_start=sources()
    rows=[]
    for item in PROTOCOL['rows']:
        identifier=uuid.uuid4().hex
        rows.append({'id':item['id'],'run_id':identifier,'run':str(output/item['id']/identifier),
                     'max_ticks':item['max_ticks'],'status':'not_started'})
    report={'status':'failed-infrastructure','protocol_sha256':PROTOCOL_SHA256,'sources':source_start,
            'source_inventory_scope':'src Python files, pyproject/lock, 17 protected files, this script/test/protocol; outer controls must bind all tracked sources',
            'rows':rows,'finalization_errors':[],'qualification':'one standalone simulated body case only'}
    budget=budget_for(output)
    try:
        with budget.lock():
            capacity_check(output,budget,LIMITS['whole_study_admission_bytes'])
            write_json(output/'report.json',report,max_bytes=MiB,storage_budget=budget)
            try:
                collect_rows(output,assets,rows,budget,source_start,started)
                report.update(reduce_rows(rows))
            except BaseException as error:
                report.update(status='failed-infrastructure',operational_status='failed',functional_status='failed',
                              error={'type':type(error).__name__,'message':str(error)[:2048]})
            finally:
                try:
                    report['sources_at_end']=sources()
                    if report['sources_at_end']!=source_start: raise ValueError('Study sources changed')
                    report['source_unchanged']=True
                except Exception as error: report['finalization_errors'].append('source: '+str(error)[:512])
                try:
                    report['final_capacity']=capacity_check(output,budget,0)
                    report['storage']=budget.check(0,path=output/'report.json')
                    files = sorted(output.rglob('*'))
                    if len(files)>4096 or any(path.is_symlink() for path in files): raise ValueError('Study inventory admission failed')
                    report['artifacts']={str(path.relative_to(output)):{'sha256':digest(path),'bytes':path.stat().st_size}
                        for path in files if path.is_file() and path.name not in ('report.json','.palimpsest-storage.lock')}
                    shots=[path for path in files if path.suffix=='.snp']
                    if len(shots)>5 or any(path.stat().st_size>16*MiB for path in shots): raise ValueError('Raw initial snapshot budget exceeded')
                except Exception as error: report['finalization_errors'].append('inventory: '+str(error)[:512])
                report['wall_seconds']=time.monotonic()-started
                if report['wall_seconds']>=780 or report['finalization_errors']:
                    report.update(status='failed-infrastructure',operational_status='failed',functional_status='failed')
                write_json(output/'report.json',report,max_bytes=MiB,storage_budget=budget_for(output,control=True))
    except BaseException as error:
        report.update(status='failed-infrastructure',operational_status='failed',functional_status='failed',
                      outer_error={'type':type(error).__name__,'message':str(error)[:2048]})
        if output.is_dir():
            write_json(output/'report.json',report,max_bytes=MiB,storage_budget=budget_for(output,control=True))
    # Lease exit and report publication belong to the internal admission, too.
    if time.monotonic()-started>=780:
        report.update(status='failed-infrastructure',operational_status='failed',functional_status='failed',
                      final_deadline_exceeded=True)
        write_json(output/'report.json',report,max_bytes=MiB,storage_budget=budget_for(output,control=True))
    return report


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker':
        if len(sys.argv[2].encode())>MiB: raise ValueError('Owner configuration exceeds bound')
        result=worker(json.loads(sys.argv[2]))
        return 1 if result['status']=='failed-infrastructure' else 0
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    report=verify(parser.parse_args())
    print(json.dumps({'status':report['status'],'rows':[{'id':r['id'],'status':r['status']} for r in report['rows']]},allow_nan=False))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
