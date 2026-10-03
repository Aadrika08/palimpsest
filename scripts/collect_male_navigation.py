"""M7-NAV-AGG-1 collection only; no training/development/held-out route."""
import argparse
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

from palimpsest import body_profile as body, male_model
from palimpsest.snapshots import state_digest
import collect_male_recovery as recovery
from verify_body_adaptation import read_json
from verify_body_gains import write_json
from verify_body_runtime import digest
from verify_task_starts import storage
from verify_task_phases import initial_ready
from verify_tasks import command, file_hashes
from verify_body_calibration import sample
from verify_endurance import source_identity

ROOT = Path(__file__).resolve().parents[1]
PLAN = 'docs/plans/m7-navigation-study-protocol.json'
PLAN_SHA = 'a3612cdc23510fa2b866482e1d13ece123940911ccc2a186c74216c83177e47f'
PROFILE = 'male-learner-advice-navigation-v1'
MiB = 1024**2
ISOLATION = ('native', 'model', 'environment', 'rng', 'student_input', 'student_hidden')
ROBOT = {'base_geom', 'left_wheel_geom', 'right_wheel_geom', 'caster_fork', 'caster_wheel_geom'}
OBSTACLES = {f'obstacle{x}' for x in range(20)}
CASES = [{'id': f'learner-{scene}-seed-{seed}', 'scene_seed': scene, 'learner_seed': seed}
         for scene in range(3100, 3104) for seed in (10, 11, 12)]


def plan(root=ROOT):
    path = Path(root)/PLAN
    if digest(path) != PLAN_SHA: raise ValueError('Frozen navigation study plan differs')
    return read_json(path, maximum=65536)


def source_pins(root=ROOT):
    p = plan(root)
    expected = p['current_reusable_source_sha256']
    for name, pin in expected.items():
        if digest(Path(root)/name) != pin: raise ValueError('Pinned study reader source differs: '+name)
    for name, pin in p['generator']['source_sha256'].items():
        if digest(Path(root)/'upstream/fly-gym'/name) != pin: raise ValueError('Pinned study generator differs: '+name)
    helpers = ('collect_male_navigation.py', 'collect_male_recovery.py', 'verify_task_starts.py',
        'verify_task_phases.py', 'verify_body_adaptation.py', 'verify_body_gains.py',
        'verify_body_runtime.py', 'verify_tasks.py', 'verify_endurance.py',
        'verify_body_calibration.py', 'evaluate_male_closed_loop.py')
    return {'plan_sha256': PLAN_SHA, 'runtime': source_identity(root),
            'harness': {name: digest(Path(root)/'scripts'/name) for name in helpers}}


def check_case(case):
    if case not in CASES or any(type(case.get(k)) is not int for k in ('scene_seed', 'learner_seed')):
        raise ValueError('Exact reserved collection case required')


def admission():
    # Same prospective numeric calculation as the already reviewed recovery collector.
    per_tick = 4*128*128*3 + body.MAX_TICK_BYTES + 8192
    recording = 600*per_tick + 4*MiB
    total = (12*160 + 12*4 + 12*2 + 6 + 16 + 128 + 8)*MiB
    if recording > 144*MiB or total > 3*1024**3: raise ValueError('Frozen collection estimate exceeds cap')
    return {'bytes_per_tick': per_tick, 'recording_bytes': recording, 'aggregate_bytes': total}



def numeric_admission(images, input_nodes):
    """Exact pinned Engine/body/navigation array bytes, before any numeric step."""
    import numpy as np
    if type(input_nodes) is not int or not 1 <= input_nodes <= 138:
        raise ValueError('Pinned bounded male input dimension differs')
    if len(images) != 2 or any(a.shape != (128,128,3) or a.dtype != np.uint8 for a in images):
        raise ValueError('Actual eyes differ from storage preflight')
    # Engine: float32 sensors/action/neural; float64 controls/poses/four scalars; int64 revision, eyes; empty populations.
    engine_bytes = 2*sum(a.nbytes for a in images) + (4+2+input_nodes+2)*4 + (2+3+3+4)*8 + 8 + 2
    contact_bytes = 11*128*(2*2+8+1) + 11*2 + 11*8 + 10*2*8 + 8
    # Advice, two counters, transitions, two 6x32 byte digests, two XYZ+quaternion samples.
    navigation_bytes = 2*4 + 2*3*8 + 3 + 2*6*32 + 2*(3+4)*8
    total = engine_bytes + contact_bytes + navigation_bytes
    if total > admission()['bytes_per_tick']: raise ValueError('Actual numeric schema exceeds preflight')
    return {'input_nodes':input_nodes, 'engine_bytes':engine_bytes, 'contact_bytes':contact_bytes,
            'navigation_bytes':navigation_bytes, 'bytes_per_tick':total, 'recording_bytes':600*total+4*MiB}


def initial_match(run, world, case, identity, expected=None):
    from evaluate_male_closed_loop import initial_fingerprint, require_matched_initial
    from palimpsest.snapshots import read_snapshot
    value = initial_fingerprint(read_snapshot(run/'snapshots/initial.snp'),world,case['scene_seed'],identity)
    if expected is not None: require_matched_initial(expected,value)
    return value

def input_row(observation):
    import numpy as np
    sensor = observation['sensors']
    return {key: observation[key] for key in ('cam_left', 'cam_right')} | {'sensors': np.asarray([
        float(sensor['collision']), 0. if sensor['collision_angle'] is None else float(sensor['collision_angle']),
        *sensor['wind_direction']], np.float32)}


def input_hashes(row):
    return {'input': state_digest({k: row[k] for k in ('cam_left', 'cam_right', 'sensors')}),
            'features': state_digest(male_model.features(row))}


def isolation(engine):
    from palimpsest.snapshots import _rng, _fields, ENV_STATE, ENV_PROFILE
    env = engine.env
    hidden = engine.policy.hidden.detach().cpu().numpy()
    return {'native': hashlib.sha256(env.data.__getstate__()).hexdigest(),
        'model': hashlib.sha256(env.model.__getstate__()).hexdigest(),
        'environment': state_digest({'state': _fields(env, tuple(n for n in ENV_STATE
            if n not in ('path_to_draw', 'target_to_draw'))), 'profile': _fields(env, ENV_PROFILE)}),
        'rng': state_digest(_rng(env)), 'student_input': input_hashes(input_row(engine.observation))['input'],
        'student_hidden': state_digest(hidden)}


def overlay(env):
    import numpy as np
    result = {}
    for name in ('path_to_draw', 'target_to_draw'):
        value = getattr(env, name)
        if value is None: result[name] = None; continue
        a = np.asarray(value)
        if a.dtype.kind not in 'iuf' or a.nbytes > 65536 or not np.isfinite(a).all():
            raise ValueError('Teacher overlay exceeds bounded finite diagnostic metadata')
        result[name] = {'shape': list(a.shape), 'dtype': a.dtype.str, 'sha256': state_digest(a)}
    return result


def check_isolation(before, after):
    if set(before) != set(ISOLATION) or set(after) != set(ISOLATION) or before != after:
        raise ValueError('Teacher query altered native/input/RNG/student state')
    if any(type(v) is not str or len(v) != 64 or any(c not in '0123456789abcdef' for c in v) for v in before.values()):
        raise ValueError('Invalid typed isolation digest')


def ownership_map(ownership):
    entries = ownership['geometries']
    if len({e['geom_id'] for e in entries}) != len(entries) or len({e['name'] for e in entries}) != len(entries):
        raise ValueError('Ambiguous contact ownership')
    if any(type(e['geom_id']) is not int or e['geom_id'] < 0 or e['owner'] not in ('robot', 'world') for e in entries):
        raise ValueError('Invalid contact ownership')
    by_id = {e['geom_id']: e for e in entries}
    if {e['name'] for e in entries if e['owner'] == 'robot'} != body.ROBOT_GEOMS:
        raise ValueError('Pinned robot ownership set differs')
    names = {e['name']: e for e in entries}
    if 'floor' not in names or names['floor']['owner'] != 'world' or not OBSTACLES <= set(names) or any(
            names[n]['owner'] != 'world' for n in OBSTACLES): raise ValueError('Pinned floor/obstacle ownership differs')
    return by_id


def admit_pair(ids, code, distance, geometry):
    if len(ids) != 2 or ids[0] == ids[1] or any(int(gid) not in geometry for gid in ids) or not math.isfinite(float(distance)):
        raise ValueError('Unknown/self/nonfinite contact pair')
    entries = [geometry[int(gid)] for gid in ids]; names = {e['name'] for e in entries}
    incident = [e for e in entries if e['owner'] == 'robot']
    support = len(incident) == 1 and 'floor' in names and incident[0]['name'] in body.GROUND_SUPPORT
    expected = 2 if support else 3 if incident else 1
    if code != expected: raise ValueError('Contact class disagrees with model ownership')
    intended = len(incident) == 1 and incident[0]['name'] in ROBOT and bool(names & OBSTACLES)
    if incident and not (support or intended): raise ValueError('Unexpected rover contact outside fixed study set')
    return intended


def admit_contacts(raw, ownership, tick):
    import numpy as np
    geometry = ownership_map(ownership)
    counts, ids, classes, distances = [np.asarray(raw['body_contact_'+n]) for n in ('counts', 'ids', 'classes', 'distances')]
    if (counts.shape != (11,) or counts.dtype.kind not in 'iu' or ids.shape != (11,128,2) or ids.dtype.kind not in 'iu' or
        classes.shape != (11,128) or classes.dtype.kind not in 'iu' or distances.shape != (11,128) or distances.dtype.kind != 'f' or
        np.any(counts < 0) or np.any(counts > 128) or not np.isfinite(distances).all()): raise ValueError('Incomplete bounded contact arrays')
    controls = np.asarray(raw['body_stage_controls']); times = np.asarray(raw['body_contact_times'])
    start = tick*.02
    if (controls.shape != (10,2) or controls.dtype!=np.float64 or not np.isfinite(controls).all() or not np.array_equal(controls, np.tile(raw['control'], (10,1))) or
        times.shape != (11,) or times.dtype!=np.float64 or not np.allclose(times, start+np.r_[np.arange(10)*.002,.018],atol=1e-9,rtol=0.) or
        not math.isclose(float(raw['body_end_data_time']),start+.02,abs_tol=1e-9,rel_tol=0.)):
        raise ValueError('Control/contact timing differs from pinned pipeline')
    intended = []
    for stage, count in enumerate(counts):
        count = int(count)
        if any(np.any(a[stage,count:]) for a in (ids, classes, distances)): raise ValueError('Nonzero unused contact padding')
        intended.append(any([admit_pair(ids[stage,j],int(classes[stage,j]),distances[stage,j],geometry) for j in range(count)]))
    if counts[9] != counts[10] or any(not np.array_equal(a[9],a[10]) for a in (ids,classes,distances)):
        raise ValueError('Final contact cache differs from final pre-control stage')
    return {'cached_bad': bool(float(raw['sensors'][0])), 'stage0_intended': intended[0], 'any_stage_intended': any(intended)}


def expected_control(action):
    import numpy as np
    v, h = np.asarray(action, np.float32)
    left, right = v - .5*h, v + .5*h
    maximum = max(abs(left), abs(right))
    if maximum > 1.: left, right = left/maximum, right/maximum
    return np.clip(np.asarray([left,right], np.float32), -1, 1)*2


def hashes_array(values):
    import numpy as np
    return np.asarray([list(bytes.fromhex(values[k])) for k in ISOLATION], np.uint8)


def bind_row(raw, row, ownership, tick):
    import numpy as np
    if type(row.get('tick')) is not int or row['tick'] != tick or int(raw['episode']) != 0 or int(raw['tick']) != tick:
        raise ValueError('Label interval cursor differs')
    check_isolation(row['query_before'], row['query_after'])
    if any(type(row.get(k)) is not str or len(row[k])!=64 or any(c not in '0123456789abcdef' for c in row[k])
           for k in ('teacher_before_sha256','teacher_after_sha256')):raise ValueError('Invalid full teacher fingerprint')
    query = row['advice']
    for value in (query['before'],query['after']):
        if (value['phase'] not in (None,'back') or type(value['count']) is not int or
            value['count'] not in (range(1,45) if value['phase'] else (0,)) or
            type(value['previous_bad_contact']) is not bool or value['direction'] not in (-1.,1.)):
            raise ValueError('Invalid typed teacher advice state')
    if type(query['contact']['bad']) is not bool:raise ValueError('Invalid typed advice contact')
    transition = recovery.validate_query(query)
    if transition != query['transition']: raise ValueError('Teacher advice transition differs')
    expected = {'nav_advice_action': np.asarray(query['expert_action'],np.float32),
        'nav_teacher_before': np.asarray([query['before'][k] for k in ('count','direction','previous_bad_contact')],np.float64),
        'nav_teacher_after': np.asarray([query['after'][k] for k in ('count','direction','previous_bad_contact')],np.float64),
        'nav_transitions': np.asarray([transition[k] for k in ('started','completed','old_label_replaced')],bool),
        'nav_query_before': hashes_array(row['query_before']), 'nav_query_after': hashes_array(row['query_after'])}
    for name, value in expected.items():
        a = np.asarray(raw[name])
        if a.dtype != value.dtype or not np.array_equal(a,value): raise ValueError('Advice/execution numeric binding differs: '+name)
    hashes = input_hashes(raw)
    if row['input_hashes'] != hashes or row['query_before']['student_input'] != hashes['input'] or type(row['policy_calls']) is not int or row['policy_calls'] != 1 or type(row['teacher_queries']) is not int or row['teacher_queries'] != 1:
        raise ValueError('Student input/feature/call binding differs')
    if (np.asarray(raw['action']).shape!=(2,) or np.asarray(raw['action']).dtype != np.dtype('float32') or
        not np.isfinite(raw['action']).all() or np.asarray(raw['control']).shape!=(2,) or np.asarray(raw['control']).dtype!=np.float64 or raw['action'].tolist() != row['executed_action'] or
        not np.array_equal(raw['control'],expected_control(raw['action']))):
        raise ValueError('Recorded student execution differs')
    sensor = np.asarray(raw['sensors'])
    if sensor[0] not in (0.,1.) or bool(sensor[0]) != query['contact']['bad'] or float(sensor[1]) != float(np.float32(query['contact']['angle'] or 0.)):
        raise ValueError('Advice contact does not bind actual student sensor')
    for phase in ('before','after'):
        position=np.asarray(raw['nav_position_xyz_'+phase]); quaternion=np.asarray(raw['nav_quaternion_'+phase])
        if (position.shape!=(3,) or quaternion.shape!=(4,) or position.dtype!=np.float64 or quaternion.dtype!=np.float64 or
            not np.isfinite(position).all() or not np.isfinite(quaternion).all() or
            not math.isclose(float(np.linalg.norm(quaternion)),1.,abs_tol=1e-8,rel_tol=0.) or
            position.tolist()!=row[phase+'_sample']['position_xyz'] or quaternion.tolist()!=row[phase+'_sample']['quaternion']):
            raise ValueError('Recorded evaluator XYZ/quaternion binding differs')
    return admit_contacts(raw,ownership,tick)


def natural_boundary(count, state):
    if type(count) is not int or not 1 <= count <= 600: raise ValueError('Invalid collection row count')
    reason = (state.get('last_outcome') or {}).get('reason')
    valid = (state.get('phase') == 'terminated' and reason in ('goal','collision','stalled') or
             state.get('phase') == 'truncated' and reason == 'time_limit' and count == 600)
    if not valid or state.get('total_tick') != count or state.get('episode') != 0:
        raise ValueError('Invalid natural/cap outcome; no arbitrary censoring')
    return reason


def collect(engine, teacher, probe, result, deadline):
    import numpy as np
    from palimpsest.engine import _teacher_fingerprint
    pending = []; original_tick = engine.writer.tick; original_act = engine.policy.act; calls = []
    def defer(episode, tick, **arrays):
        if pending: raise ValueError('More than one unpublished interval')
        pending.append((episode,tick,arrays))
    def act(observation):
        calls.append(input_hashes(input_row(observation)))
        if len(calls) != 1: raise ValueError('More than one student forward per interval')
        return original_act(observation)
    engine.writer.tick = defer; engine.policy.act = act
    try:
        for tick in range(600):
            if time.monotonic() > deadline: raise TimeoutError('Collection owner deadline')
            calls.clear(); row = {'tick':tick, 'query_before':isolation(engine), 'teacher_before_sha256':_teacher_fingerprint(teacher),
                'overlay_before':overlay(engine.env), 'before_sample':sample(engine.env)}
            result['first_failure_packet'] = row
            row['advice'] = recovery.query_teacher(teacher,engine.env); row['teacher_queries'] = 1
            row.update(query_after=isolation(engine),teacher_after_sha256=_teacher_fingerprint(teacher),overlay_after=overlay(engine.env))
            check_isolation(row['query_before'],row['query_after'])
            probe.begin(tick)
            try:
                command(engine,'learner-step-'+str(tick),'step')
            except Exception:
                try: row['interval_contacts'] = probe.end()
                except Exception as diagnostic: row['contact_capture_error'] = str(diagnostic)[:512]
                raise
            interval = probe.end()
            if len(pending) != 1 or pending[0][:2] != (0,tick): raise ValueError('Missing raw learner interval')
            episode, recorded_tick, raw = pending.pop()
            row.update(callback_count=interval['callback_count'],coverage_passed=interval['coverage_passed'],
                coverage_errors=interval['coverage_errors'],after_sample=sample(engine.env))
            query = row['advice']
            row['interval_contacts']=interval
            raw.update(body.contact_arrays(interval), nav_advice_action=np.asarray(query['expert_action'],np.float32),
                nav_teacher_before=np.asarray([query['before'][k] for k in ('count','direction','previous_bad_contact')],np.float64),
                nav_teacher_after=np.asarray([query['after'][k] for k in ('count','direction','previous_bad_contact')],np.float64),
                nav_transitions=np.asarray([query['transition'][k] for k in ('started','completed','old_label_replaced')],bool),
                nav_query_before=hashes_array(row['query_before']),nav_query_after=hashes_array(row['query_after']),
                nav_position_xyz_before=np.asarray(row['before_sample']['position_xyz'],np.float64),
                nav_quaternion_before=np.asarray(row['before_sample']['quaternion'],np.float64),
                nav_position_xyz_after=np.asarray(row['after_sample']['position_xyz'],np.float64),
                nav_quaternion_after=np.asarray(row['after_sample']['quaternion'],np.float64))
            if sum(np.asarray(a).nbytes for a in raw.values()) > result['numeric_admission']['bytes_per_tick']:
                raise ValueError('Actual numeric interval exceeds admitted schema')
            row.update(executed_action=raw['action'].tolist(), policy_calls=len(calls), input_hashes=calls[0] if calls else None)
            original_tick(episode,recorded_tick,**raw)  # Preserve full packet before contact/admission failure.
            result['rows'].append(row)
            row['contacts'] = bind_row({'episode':episode,'tick':recorded_tick,**raw},row,result['contact_ownership'],tick)
            if not interval['coverage_passed'] or interval['callback_count'] != 10: raise ValueError('Incomplete callback coverage')
            row.pop('interval_contacts',None)
            if tick and result['rows'][-2]['advice']['after'] != query['before']: raise ValueError('Teacher history discontinuity')
            result.pop('first_failure_packet',None)
            if engine.phase != 'paused': break
        return natural_boundary(len(result['rows']),engine.public_state())
    finally:
        engine.writer.tick = original_tick; engine.policy.act = original_act


def publish(path, value, budget, deadline, check):
    payload = (json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    if len(payload) > 4*MiB: raise ValueError('Collection JSON exceeds4MiB')
    if path.exists(): raise FileExistsError('No overwrite or resume')
    pending = path.with_suffix('.pending')
    budget.check(len(payload),path=pending)
    with pending.open('xb') as stream: stream.write(payload);stream.flush();os.fsync(stream.fileno())
    check()
    if time.monotonic() > deadline: raise TimeoutError('Late collection publication')
    if path.exists(): raise FileExistsError('Final collection destination appeared')
    pending.replace(path)


def worker(config):
    import numpy as np
    import mujoco
    import torch
    from palimpsest.engine import Engine, _teacher_fingerprint
    from palimpsest.flynn import import_upstream
    from palimpsest.male_recovery_research import Binding
    from palimpsest.replay import _register_initial
    from palimpsest.snapshots import _model_digest
    from palimpsest.profiles import validate_world
    root,run,stage = map(Path,(config['repo'],config['run'],config['stage']))
    budget = storage(config); deadline = time.monotonic()+180; engine = probe = None
    result = {'status':'failed-infrastructure','case':config['case'],'rows':[]}
    try:
        check_case(config['case']); pins=source_pins(root)
        if pins != config['source_pins']: raise ValueError('Source changed before learner owner')
        if mujoco.get_mjcb_control() is not None: raise ValueError('Existing control callback refused')
        budget.check(admission()['recording_bytes']+16*MiB,path=run)
        run.mkdir(exist_ok=False)
        binding=Binding(root/'data/manifests/male-recovery-research-development-v1.json',
            plan(root)['fixed_source_models']['index_sha256'],config['case']['learner_seed'])
        engine=Engine.open(root,Path(config['assets']),run/'recording',controller='male-original',device='cpu',
            seed=config['case']['scene_seed'],scenario='reproduction',texture='checker',run_id=run.name,
            max_bytes=144*MiB,storage_budget=budget,research_binding=binding,expected_policy_identity=config['identity'])
        if torch.get_num_threads()!=1 or torch.cuda.is_initialized(): raise ValueError('Pinned one-thread CPU learner required')
        if (engine.total_tick or engine.episode or engine.phase!='paused' or engine.teacher is not None or
            np.any(engine.env.data.qvel) or np.any(engine.env.data.ctrl) or engine.env.data.time or engine.env._t or
            engine.env._speed or engine.env._stall_steps or np.any(engine.env._last_action) or
            not np.array_equal(engine.env._prev_xy,engine.env._base_xy())): raise ValueError('Fresh learner boundary required')
        result['numeric_admission'] = numeric_admission([engine.observation[k] for k in ('cam_left','cam_right')],engine.policy.agent.cell.Nin)
        budget.check(result['numeric_admission']['recording_bytes']+16*MiB,path=run)
        validate_world(engine.env)  # Evaluator-only refusal; never move or resample the initial scene.
        if engine.eyes!={'left':True,'right':True}:raise ValueError('Collection eyes must remain unmasked')
        reference=import_upstream(root,'run_connectome_rnn_checkpoint')
        before=isolation(engine); teacher=reference.PlannerAnalyticTeacher(arena_half_extent=engine.env.arena,device='cpu')
        check_isolation(before,isolation(engine))
        if recovery.teacher_state(teacher)!={'phase':None,'count':0,'direction':1.,'previous_bad_contact':False}:raise ValueError('Fresh teacher baseline differs')
        if (engine.env.max_steps!=600 or engine.env.n_obstacles!=20 or engine.env._action_scale!=2 or engine.env.end_on_collision):
            raise ValueError('Pinned reproduction control/outcome profile differs')
        result['initial_teacher_sha256']=_teacher_fingerprint(teacher)
        probe=body.ContactProbe(mujoco,engine.env)
        result['contact_ownership']={**probe.ownership,'model_sha256':_model_digest(engine.env.model)}
        ownership_map(result['contact_ownership'])
        enabled={entry['name'] for entry in probe.ownership['geometries'] if entry['owner']=='robot' and
            (engine.env.model.geom_contype[entry['geom_id']] or engine.env.model.geom_conaffinity[entry['geom_id']])}
        if enabled!=ROBOT:raise ValueError('Actual robot collision masks differ')
        engine.writer.manifest.update(profile=PROFILE,navigation_collection={'study_sha256':PLAN_SHA,'case':config['case'],
            'label_kind':'returned-analytic-teacher-advice','label_privileged':True,'executed_controller':'frozen-recovery-original',
            'source_identity':config['identity'],'teacher_initial_sha256':result['initial_teacher_sha256'],
            'contact_ownership':result['contact_ownership'],'generic_replay_qualified':False})
        _register_initial(engine,run,budget);initial_ready(run,'ready')
        if (run/'snapshots/initial.snp').stat().st_size>16*MiB:raise ValueError('Initial SNP exceeds16MiB')
        result['initial_world']=engine.world()
        result['initial_fingerprint']=initial_match(run,result['initial_world'],config['case'],config['identity'],config.get('scene_initial'))
        engine.writer.manifest['navigation_collection']['initial_fingerprint']=result['initial_fingerprint']
        probe.install()
        result['outcome']=collect(engine,teacher,probe,result,deadline)
        result['final_state']=engine.public_state();result['status']='completed-recording'
    except Exception as error:
        result.update(status='failed-infrastructure',error={'type':type(error).__name__,'message':str(error)[:1024]})
        if engine is not None:
            try:
                buffer=io.BytesIO();np.savez(buffer,**{k:engine.observation[k] for k in ('cam_left','cam_right')})
                payload=buffer.getvalue()
                if len(payload)>MiB:raise ValueError('Failure camera packet exceeds1MiB')
                path=stage/'failure-cameras.npz';budget.check(len(payload),path=path)
                with path.open('xb') as stream:stream.write(payload);stream.flush();os.fsync(stream.fileno())
                result['failure_cameras_sha256']=digest(path)
            except Exception as diagnostic:result['diagnostic_error']=str(diagnostic)[:512]
    finally:
        if probe is not None:
            try: probe.close();result['callback_restored']=mujoco.get_mjcb_control() is None
            except Exception as error: result.update(status='failed-infrastructure',callback_error=str(error)[:512])
        if engine is not None:
            try: engine.close();result['engine_closed']=True
            except Exception as error: result.update(status='failed-infrastructure',cleanup_error=str(error)[:512])
    if not result.get('callback_restored') or not result.get('engine_closed'):result['status']='failed-infrastructure'
    try: publish(stage/'result.json',result,budget,deadline,lambda:check_pins(root,config['source_pins']))
    except Exception as error:
        write_json(stage/'failure.json',{'status':'failed-infrastructure','error':str(error)[:1024],'result':result},max_bytes=4*MiB,storage_budget=budget)
        return False
    return result['status']=='completed-recording'


def check_pins(root, expected):
    if source_pins(root)!=expected:raise ValueError('Collection source drift')


def admit_record(run, result, identity):
    from palimpsest.records import iter_ticks
    manifest=read_json(run/'recording/manifest.json',maximum=4*MiB)
    c=manifest.get('navigation_collection',{})
    if (manifest.get('controller')!='male-original' or manifest.get('seed')!=result['case']['scene_seed'] or
        manifest.get('scenario',{}).get('id')!='reproduction' or manifest.get('texture')!='checker' or
        manifest.get('status')!='completed' or manifest.get('profile')!=PROFILE or c.get('study_sha256')!=PLAN_SHA or
        c.get('source_identity')!=identity or c.get('case')!=result['case'] or
        c.get('label_kind')!='returned-analytic-teacher-advice' or c.get('label_privileged') is not True or c.get('generic_replay_qualified') is not False or
        c.get('contact_ownership')!=result['contact_ownership'] or c.get('teacher_initial_sha256')!=result.get('initial_teacher_sha256') or result.get('status')!='completed-recording' or
        not result.get('engine_closed') or not result.get('callback_restored')):raise ValueError('Wrong source/profile/label/cleanup admission')
    import numpy as np
    declared=result['numeric_admission']
    if numeric_admission([np.zeros((128,128,3),np.uint8)]*2,declared['input_nodes'])!=declared:
        raise ValueError('Retained numeric admission differs')
    count=0; previous=None; previous_sha=result.get('initial_teacher_sha256')
    for count,raw in enumerate(iter_ticks(run/'recording'),1):
        if count>600 or count>len(result['rows']):raise ValueError('Collection exceeds row limit')
        if sum(np.asarray(a).nbytes for k,a in raw.items() if k not in ('episode','tick'))>declared['bytes_per_tick']:
            raise ValueError('Retained numeric interval exceeds admission')
        row=result['rows'][count-1]
        if row.get('coverage_passed') is not True or type(row.get('callback_count')) is not int or row['callback_count'] != 10 or row.get('coverage_errors') != []:
            raise ValueError('Parent callback coverage differs')
        bind_row(raw,row,result['contact_ownership'],count-1)
        if previous is not None and previous!=row['advice']['before']:raise ValueError('Reconstructed teacher history differs')
        if previous_sha!=row['teacher_before_sha256']:raise ValueError('Reconstructed full teacher history differs')
        previous=row['advice']['after'];previous_sha=row['teacher_after_sha256']
    if count!=len(result['rows']):raise ValueError('Missing source/advice rows')
    if result.get('outcome') != natural_boundary(count,result['final_state']):raise ValueError('Recorded outcome differs from natural boundary')
    initial_ready(run,'ready')
    fingerprint=initial_match(run,result['initial_world'],result['case'],identity)
    if fingerprint!=result.get('initial_fingerprint') or fingerprint!=c.get('initial_fingerprint'):raise ValueError('Recorded scientific initial differs')
    if (run/'snapshots/initial.snp').stat().st_size>16*MiB:raise ValueError('Initial SNP exceeds16MiB')
    return count


def run_cases(report, owner):
    for case in CASES:
        item=report['cases'][case['id']]
        try:
            item['status']='running';count=owner(case,item)
            item['status']='completed-recording';report['owners_completed']+=1;report['numeric_ticks']+=count
        except Exception as error:
            item.update(status='failed-infrastructure',error=str(error)[:1024]);report['status']='failed-infrastructure';return False
    report['status']='completed-collection';return True


def verify(args):
    from dataclasses import asdict
    from palimpsest.evaluate import bounded_process
    from palimpsest.storage import StorageBudget,StorageLimits
    from palimpsest.assets import verify_assets
    from palimpsest.male_recovery_research import resolve
    root,assets,output=args.repo.resolve(),args.assets.resolve(),args.output.resolve();started=time.monotonic();deadline=started+2160
    if root!=ROOT or output.is_relative_to(assets) or assets.is_relative_to(output):raise ValueError('Exact producer/outside assets required')
    p=plan(root); producer=(root/p['fixed_source_models']['producer_root']).resolve()
    if output.is_relative_to(producer) or producer.is_relative_to(output):raise ValueError('Output overlaps immutable corpus/model producer')
    pins=source_pins(root);output.mkdir(parents=True,exist_ok=False)
    budget=StorageBudget((output,),StorageLimits(max_bytes=3*1024**3,min_free_bytes=1024**3,max_runs=12,max_snapshots=1,max_exports=1),headroom_bytes=8*MiB)
    config={'repo':str(root),'assets':str(assets),'storage':{'roots':[str(output)],'limits':asdict(budget.limits),'headroom_bytes':8*MiB},'source_pins':pins}
    report={'status':'running','study_sha256':PLAN_SHA,'profile':PROFILE,'source_pins':pins,'owners_completed':0,'numeric_ticks':0,
        'cases':{c['id']:{'status':'not_started','case':c} for c in CASES},'qualification_claims':[]}
    try:
        with budget.lock():
            budget.check(admission()['aggregate_bytes'],path=output)
            report['assets_before']=verify_assets(root,assets)
            if not report['assets_before']['ok']:raise ValueError('Frozen assets unavailable')
            identities={seed:resolve(root,assets,root/'data/manifests/male-recovery-research-development-v1.json',
                p['fixed_source_models']['index_sha256'],seed,'male-original')[0] for seed in (10,11,12)}
            scene_initials={}
            def owner(case,item):
                if time.monotonic()>deadline:raise TimeoutError('Collection stage deadline')
                check_pins(root,pins);stage=output/case['id'];stage.mkdir();run=stage/uuid.uuid4().hex
                child={**config,'case':case,'stage':str(stage),'run':str(run),'identity':identities[case['learner_seed']], 'scene_initial':scene_initials.get(case['scene_seed'])}
                write_json(output/'progress.json',report,max_bytes=4*MiB,storage_budget=budget)
                item['supervision']=bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',json.dumps(child)],stage/'supervision',
                    min(180,deadline-time.monotonic()),{**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','OMP_NUM_THREADS':'1'},
                    log_max_bytes=MiB,storage_budget=budget)
                result=read_json(stage/'result.json',maximum=4*MiB);item['result_path']=str(stage/'result.json');item['result_sha256']=digest(stage/'result.json')
                s=item['supervision']
                if s.get('status')!='completed' or s.get('returncode')!=0 or 'error' in s or 'failure' in s:raise ValueError('Owner failed normal disposition')
                n=admit_record(run,result,child['identity'])
                from evaluate_male_closed_loop import require_matched_initial
                fingerprint=result['initial_fingerprint']
                if case['scene_seed'] in scene_initials:require_matched_initial(scene_initials[case['scene_seed']],fingerprint)
                else:scene_initials[case['scene_seed']]=fingerprint
                item.update(outcome=result['outcome'],run=str(run),initial_fingerprint=fingerprint)
                if time.monotonic()>deadline:raise TimeoutError('Late owner admission')
                return n
            run_cases(report,owner)
            report['assets_after']=verify_assets(root,assets)
            if report['assets_before']!=report['assets_after']:raise ValueError('Assets changed')
            if report['status']=='completed-collection' and (report['owners_completed']!=12 or len(list(output.rglob('*.snp')))!=12):raise ValueError('Incomplete fixed owner/snapshot plan')
            report['identities_before']=identities
            report['identities_after']={seed:resolve(root,assets,root/'data/manifests/male-recovery-research-development-v1.json',
                p['fixed_source_models']['index_sha256'],seed,'male-original')[0] for seed in (10,11,12)}
            if report['identities_before']!=report['identities_after']:raise ValueError('Frozen learner source changed')
            report['artifacts_sha256']={k:v for k,v in file_hashes(output).items() if k not in ('progress.json','.palimpsest-storage.lock')}
            report['final_source_pins']=source_pins(root);report['wall_seconds_before_publication']=time.monotonic()-started
        # Lease release/source/deadline checks precede final admissible publication.
        if report['status']!='completed-collection':raise ValueError('Collection failed; retained prior/unstarted owners')
        publish(output/'report.json',report,budget,deadline,lambda:check_pins(root,pins))
    except Exception as error:
        report.update(status='failed-infrastructure',error={'type':type(error).__name__,'message':str(error)[:1024]})
        write_json(output/'failure.json',report,max_bytes=4*MiB,storage_budget=budget)
    return report


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker':return 0 if worker(json.loads(sys.argv[2])) else 1
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path,default=ROOT)
    parser.add_argument('--assets',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    report=verify(parser.parse_args());print(json.dumps({'status':report['status'],'owners_completed':report['owners_completed'],'numeric_ticks':report['numeric_ticks']}))
    return 0 if report['status']=='completed-collection' else 1


if __name__=='__main__':raise SystemExit(main())
