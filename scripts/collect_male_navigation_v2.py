"""Separate v2 learner-advice collection; no trainer/evaluator/held-out route."""
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

import collect_male_navigation as v1
from collect_male_navigation import (MiB, ROOT, ISOLATION, ROBOT, OBSTACLES, CASES,
    body, recovery, read_json, write_json, digest, source_identity, storage,
    command, sample, file_hashes, initial_ready, numeric_admission, admission,
    check_case, initial_match, input_row, input_hashes, isolation, overlay,
    check_isolation, expected_control, hashes_array, natural_boundary, publish, run_cases)

PLAN = 'docs/plans/m7-navigation-contact-v2-protocol.json'
PLAN_SHA = '29039e944f49dc1458d918dcd738a32ee5fbf5bfdbbee8fff2cd969e4703bab0'
PROFILE = 'male-learner-advice-navigation-v2'
PROFILE_SHA = '1593421ae2cc1a12b0d9aeae6646fda77da1d11a885ffac3406e52dc6af12186'
TYPES = ('wheel_floor_support', 'non_wheel_floor', 'robot_obstacle', 'robot_wall', 'world_only')
WORLD = ('floor', 'wall_n', 'wall_s', 'wall_e', 'wall_w', *(f'obstacle{x}' for x in range(20)))
PAIRS = tuple((robot, world) for robot in ('base_geom', 'left_wheel_geom', 'right_wheel_geom', 'caster_fork', 'caster_wheel_geom') for world in WORLD)


def plan(root=ROOT):
    path = Path(root)/PLAN
    if digest(path) != PLAN_SHA: raise ValueError('Frozen v2 navigation plan differs')
    value = read_json(path, maximum=65536)
    identity = value['contact_profile']['identity']
    actual = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if value['contact_profile']['sha256'] != PROFILE_SHA or actual != PROFILE_SHA:
        raise ValueError('V2 contact profile differs')
    return value


def source_pins(root=ROOT):
    p = plan(root)
    if digest(Path(root)/'scripts/collect_male_navigation.py') != p['prior_version']['collector_sha256']:
        raise ValueError('Frozen v1 collector differs')
    previous = v1.source_pins(root)  # Unchanged fourteen readers and eight generator pins.
    return {**previous, 'plan_sha256': PLAN_SHA, 'profile_sha256': PROFILE_SHA,
            'v1_plan_sha256': previous['plan_sha256'],
            'harness': {**previous['harness'], 'collect_male_navigation_v2.py': digest(Path(root)/'scripts/collect_male_navigation_v2.py')}}


CONTACTS = plan()['contacts']


def ownership_map(ownership):
    """Revalidate the complete pinned tree/masks, never an observed-pair filter."""
    entries = ownership['geometries']
    bodies = ownership['robot_bodies'] + ownership['world_bodies']
    if (len(entries) != 32 or len(bodies) != 26 or
        len({e['geom_id'] for e in entries}) != 32 or len({e['name'] for e in entries}) != 32 or
        len({b['body_id'] for b in bodies}) != 26 or len({b['name'] for b in bodies}) != 26):
        raise ValueError('Ambiguous/incomplete compiled ownership')
    for value in entries:
        if (type(value['geom_id']) is not int or not 0 <= value['geom_id'] < 32 or
            type(value['body_id']) is not int or not 0 <= value['body_id'] < 26 or
            type(value['contype']) is not int or type(value['conaffinity']) is not int):
            raise ValueError('Invalid typed geometry/masks')
    for value in bodies:
        if (type(value['body_id']) is not int or not 0 <= value['body_id'] < 26 or
            type(value['parent_id']) is not int or not 0 <= value['parent_id'] < 26):
            raise ValueError('Invalid typed body tree')
    by_body = {b['body_id']: b for b in bodies}; body_names = {b['name']: b for b in bodies}
    if body_names.get('world') != {'body_id':0, 'name':'world', 'parent_id':0}:
        raise ValueError('Pinned world body differs')
    expected_tree = {**CONTACTS['expected_robot_body_tree'], **{f'obstacle{x}_body':'world' for x in range(20)}}
    if set(body_names) != {'world', *expected_tree}:
        raise ValueError('Pinned full body names differ')
    for name, parent in expected_tree.items():
        b = body_names[name]
        if by_body[b['parent_id']]['name'] != parent: raise ValueError('Pinned body ancestry differs')
    robot_ids = {body_names[n]['body_id'] for n in CONTACTS['expected_robot_body_tree']}
    if ({b['body_id'] for b in ownership['robot_bodies']} != robot_ids or
        type(ownership['base_body_id']) is not int or ownership['base_body_id'] != body_names['base']['body_id']):
        raise ValueError('Robot ownership partition differs')
    if type(ownership.get('model_sha256')) is not str or len(ownership['model_sha256']) != 64 or any(c not in '0123456789abcdef' for c in ownership['model_sha256']):
        raise ValueError('Invalid compiled model digest')
    names = {e['name']: e for e in entries}
    if set(names) != set(CONTACTS['expected_geom_body_names']): raise ValueError('Pinned full geometry names differ')
    for name, expected_body in CONTACTS['expected_geom_body_names'].items():
        e = names[name]
        if (e['body_name'] != expected_body or by_body[e['body_id']]['name'] != expected_body or
            e['owner'] != ('robot' if e['body_id'] in robot_ids else 'world') or
            [e['contype'], e['conaffinity']] != CONTACTS['expected_collision_masks'][name]):
            raise ValueError('Pinned geometry ownership/masks differ')
    for robot, world in PAIRS:
        r,w = names[robot],names[world]
        if not (r['contype'] & w['conaffinity'] or w['contype'] & r['conaffinity']):
            raise ValueError('Declared robot-world pair is disabled')
    return {e['geom_id']: e for e in entries}


def compiled_ownership(mj, model, model_sha256):
    import numpy as np
    if model.ngeom != 32 or model.nbody != 26: raise ValueError('Pinned compiled model counts differ')
    for name, size in (('body_parentid',26),('geom_bodyid',32)):
        a=np.asarray(getattr(model,name))
        if a.shape!=(size,) or a.dtype.kind not in 'iu':raise ValueError('Compiled body/geometry indices differ')
    masks = [np.asarray(getattr(model, name)) for name in ('geom_contype','geom_conaffinity')]
    if any(a.shape != (32,) or a.dtype.kind not in 'iu' for a in masks): raise ValueError('Compiled masks differ')
    value = body.contact_ownership(mj, model)
    robot_ids = {b['body_id'] for b in value['robot_bodies']}
    value['world_bodies'] = [{'body_id':i, 'name':mj.mj_id2name(model,mj.mjtObj.mjOBJ_BODY,i),
        'parent_id':int(model.body_parentid[i])} for i in range(model.nbody) if i not in robot_ids]
    for entry in value['geometries']:
        entry.update(contype=int(masks[0][entry['geom_id']]),conaffinity=int(masks[1][entry['geom_id']]))
    value['model_sha256'] = model_sha256
    ownership_map(value)
    return value


def pair_type(ids, code, distance, geometry):
    if (len(ids) != 2 or ids[0] == ids[1] or any(int(gid) not in geometry for gid in ids) or
        not math.isfinite(float(distance))): raise ValueError('Unknown/self/nonfinite contact pair')
    entries = [geometry[int(gid)] for gid in ids]
    incident = [e for e in entries if e['owner'] == 'robot']
    if len(incident) == 2: raise ValueError('Robot self/inter-body contact rejected')
    if not incident:
        if code != 1: raise ValueError('World-only class differs')
        return 'world_only', None
    robot = incident[0]['name']; world = next(e['name'] for e in entries if e['owner']=='world')
    if (robot,world) not in PAIRS: raise ValueError('Unexpected rover contact outside fixed v2 set')
    support = world=='floor' and robot in body.GROUND_SUPPORT
    if code != (2 if support else 3): raise ValueError('Contact class disagrees with model ownership')
    kind = 'wheel_floor_support' if support else 'non_wheel_floor' if world=='floor' else 'robot_obstacle' if world in OBSTACLES else 'robot_wall'
    return kind, PAIRS.index((robot,world))


def admit_pair(ids, code, distance, geometry):
    kind,_ = pair_type(ids,code,distance,geometry)
    return kind not in ('wheel_floor_support','world_only')


def empty_incidence():
    return {'scope':'fully admitted prefix only', 'admitted_intervals':0,
        'pair_instances_by_type_stage':[[0]*11 for _ in TYPES],
        'intervals_by_type_stage':[[0]*11 for _ in TYPES], 'robot_world_pair_instances':[0]*125}


def add_incidence(target, value):
    target['admitted_intervals'] += 1
    for i in range(5):
        for stage in range(11):
            n=value['pair_instances_by_type_stage'][i][stage]
            target['pair_instances_by_type_stage'][i][stage] += n
            target['intervals_by_type_stage'][i][stage] += int(n>0)
    for i,n in enumerate(value['robot_world_pair_instances']):target['robot_world_pair_instances'][i] += n


def row_contacts(value):
    # All incidence counters live once in owner metadata, not in every row.
    return {'cached_bad':value['cached_bad']}


def admit_contacts(raw, ownership, tick):
    import numpy as np
    geometry=ownership_map(ownership)
    counts,ids,classes,distances=[np.asarray(raw['body_contact_'+n]) for n in ('counts','ids','classes','distances')]
    if (counts.shape!=(11,) or counts.dtype.kind not in 'iu' or ids.shape!=(11,128,2) or ids.dtype.kind not in 'iu' or
        classes.shape!=(11,128) or classes.dtype.kind not in 'iu' or distances.shape!=(11,128) or distances.dtype.kind!='f' or
        np.any(counts<0) or np.any(counts>128) or not np.isfinite(distances).all()):raise ValueError('Incomplete bounded contact arrays')
    controls=np.asarray(raw['body_stage_controls']);times=np.asarray(raw['body_contact_times']);start=tick*.02
    if (controls.shape!=(10,2) or controls.dtype!=np.float64 or not np.isfinite(controls).all() or
        not np.array_equal(controls,np.tile(raw['control'],(10,1))) or times.shape!=(11,) or times.dtype!=np.float64 or
        not np.allclose(times,start+np.r_[np.arange(10)*.002,.018],atol=1e-9,rtol=0.) or
        not math.isclose(float(raw['body_end_data_time']),start+.02,abs_tol=1e-9,rel_tol=0.)):
        raise ValueError('Control/contact timing differs from pinned pipeline')
    by_type=[[0]*11 for _ in TYPES];by_pair=[0]*125
    for stage,count in enumerate(counts):
        count=int(count)
        if any(np.any(a[stage,count:]) for a in (ids,classes,distances)):raise ValueError('Nonzero unused contact padding')
        for j in range(count):
            kind,pair=pair_type(ids[stage,j],int(classes[stage,j]),distances[stage,j],geometry)
            by_type[TYPES.index(kind)][stage]+=1
            if pair is not None:by_pair[pair]+=1
    if counts[9]!=counts[10] or any(not np.array_equal(a[9],a[10]) for a in (ids,classes,distances)):
        raise ValueError('Final contact cache differs from final pre-control stage')
    return {'cached_bad':bool(float(raw['sensors'][0])), 'pair_instances_by_type_stage':by_type,
        'robot_world_pair_instances':by_pair}


def initial_contact_binding(run, ownership):
    from palimpsest.snapshots import read_snapshot
    ownership_map(ownership)
    snapshot=read_snapshot(run/'snapshots/initial.snp')
    if snapshot['identity']['model_sha256'] != ownership['model_sha256']:
        raise ValueError('Compiled contact metadata differs from initial SNP model')
    return ownership['model_sha256']


# This local interval/label glue preserves the frozen v1 producer byte-for-byte;
# v1 binds its contact validator through module globals. All other kernels reuse v1.

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
            contacts = bind_row({'episode':episode,'tick':recorded_tick,**raw},row,result['contact_ownership'],tick)
            row['contacts'] = row_contacts(contacts)
            if not interval['coverage_passed'] or interval['callback_count'] != 10: raise ValueError('Incomplete callback coverage')
            row.pop('interval_contacts',None)
            if tick and result['rows'][-2]['advice']['after'] != query['before']: raise ValueError('Teacher history discontinuity')
            add_incidence(result['contact_incidence'],contacts)
            result.pop('first_failure_packet',None)
            if engine.phase != 'paused': break
        return natural_boundary(len(result['rows']),engine.public_state())
    finally:
        engine.writer.tick = original_tick; engine.policy.act = original_act


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
    result = {'status':'failed-infrastructure','case':config['case'],'rows':[], 'contact_incidence':empty_incidence()}
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
        result['contact_ownership']=compiled_ownership(mujoco,engine.env.model,_model_digest(engine.env.model))
        if (result['contact_ownership']['base_body_id']!=probe.ownership['base_body_id'] or
            result['contact_ownership']['robot_bodies']!=probe.ownership['robot_bodies'] or
            any({k:actual[k] for k in original}!=original for actual,original in
                zip(result['contact_ownership']['geometries'],probe.ownership['geometries'],strict=True))):
            raise ValueError('Probe ownership differs from compiled v2 contract')
        engine.writer.manifest.update(profile=PROFILE,navigation_collection={'study_sha256':PLAN_SHA,'case':config['case'],
            'label_kind':'returned-analytic-teacher-advice','label_privileged':True,'executed_controller':'frozen-recovery-original',
            'source_identity':config['identity'],'teacher_initial_sha256':result['initial_teacher_sha256'],
            'contact_ownership':result['contact_ownership'],'contact_profile_sha256':PROFILE_SHA,'generic_replay_qualified':False})
        _register_initial(engine,run,budget);initial_ready(run,'ready')
        if (run/'snapshots/initial.snp').stat().st_size>16*MiB:raise ValueError('Initial SNP exceeds16MiB')
        initial_contact_binding(run,result['contact_ownership'])
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
        manifest.get('status')!='completed' or c.get('contact_profile_sha256')!=PROFILE_SHA or manifest.get('profile')!=PROFILE or c.get('study_sha256')!=PLAN_SHA or
        c.get('source_identity')!=identity or c.get('case')!=result['case'] or
        c.get('label_kind')!='returned-analytic-teacher-advice' or c.get('label_privileged') is not True or c.get('generic_replay_qualified') is not False or
        c.get('contact_ownership')!=result['contact_ownership'] or c.get('teacher_initial_sha256')!=result.get('initial_teacher_sha256') or result.get('status')!='completed-recording' or
        not result.get('engine_closed') or not result.get('callback_restored')):raise ValueError('Wrong source/profile/label/cleanup admission')
    import numpy as np
    declared=result['numeric_admission']
    if numeric_admission([np.zeros((128,128,3),np.uint8)]*2,declared['input_nodes'])!=declared:
        raise ValueError('Retained numeric admission differs')
    initial_contact_binding(run,result['contact_ownership'])
    incidence=empty_incidence()
    count=0; previous=None; previous_sha=result.get('initial_teacher_sha256')
    for count,raw in enumerate(iter_ticks(run/'recording'),1):
        if count>600 or count>len(result['rows']):raise ValueError('Collection exceeds row limit')
        if sum(np.asarray(a).nbytes for k,a in raw.items() if k not in ('episode','tick'))>declared['bytes_per_tick']:
            raise ValueError('Retained numeric interval exceeds admission')
        row=result['rows'][count-1]
        if row.get('coverage_passed') is not True or type(row.get('callback_count')) is not int or row['callback_count'] != 10 or row.get('coverage_errors') != []:
            raise ValueError('Parent callback coverage differs')
        contacts=bind_row(raw,row,result['contact_ownership'],count-1)
        if type(row.get('contacts',{}).get('cached_bad')) is not bool or row.get('contacts')!=row_contacts(contacts):raise ValueError('Row contact incidence differs')
        add_incidence(incidence,contacts)
        if previous is not None and previous!=row['advice']['before']:raise ValueError('Reconstructed teacher history differs')
        if previous_sha!=row['teacher_before_sha256']:raise ValueError('Reconstructed full teacher history differs')
        previous=row['advice']['after'];previous_sha=row['teacher_after_sha256']
    if json.dumps(result.get('contact_incidence'),sort_keys=True)!=json.dumps(incidence,sort_keys=True):raise ValueError('Owner admitted-prefix incidence differs')
    if count!=len(result['rows']):raise ValueError('Missing source/advice rows')
    if result.get('outcome') != natural_boundary(count,result['final_state']):raise ValueError('Recorded outcome differs from natural boundary')
    initial_ready(run,'ready')
    fingerprint=initial_match(run,result['initial_world'],result['case'],identity)
    if fingerprint!=result.get('initial_fingerprint') or fingerprint!=c.get('initial_fingerprint'):raise ValueError('Recorded scientific initial differs')
    if (run/'snapshots/initial.snp').stat().st_size>16*MiB:raise ValueError('Initial SNP exceeds16MiB')
    return count


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
        'cases':{c['id']:{'status':'not_started','case':c} for c in CASES},'contact_profile_sha256':PROFILE_SHA,'qualification_claims':[]}
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
                item.update(outcome=result['outcome'],run=str(run),initial_fingerprint=fingerprint,contact_incidence=result['contact_incidence'])
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
