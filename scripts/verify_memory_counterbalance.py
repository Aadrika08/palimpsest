"""Eight DEVELOPMENT admission cells; source preparation only until explicit GO."""
import argparse
import copy
import importlib.util
import json
import os
import shutil

import numpy as np
from pathlib import Path
import sys
import time
import uuid

from palimpsest import artifacts, memory, memory_experiment as experiment, memory_task, memory_world
from palimpsest.evaluate import bounded_process
from palimpsest.replay import _initial_snapshot, _register_initial
from palimpsest.snapshots import capture, read_snapshot, state_digest
from palimpsest.storage import GiB, MiB, StorageBudget, StorageLimits

HELPER=Path(__file__).with_name('verify_flynn_memory_transfer.py')
spec=importlib.util.spec_from_file_location('fixed_flynn_helpers',HELPER)
neural=importlib.util.module_from_spec(spec);spec.loader.exec_module(neural)
common=neural.common
CELLS=((24,'local_cue','change'),(25,'local_cue','change'),
       (26,'paired_cue','null'),(27,'paired_cue','no-event'),
       (28,'paired_cue','change'),(29,'paired_cue','change'),
       (30,'local_cue','null'),(31,'local_cue','no-event'))
STAGES=('source','policy-anchor','probe')
PROTOCOL={'version':1,'claim':'development-admission-only','cells':[list(c) for c in CELLS],
    'source_ticks':300,'probe_ticks':1,'total_owners':24,'controller':'flynn','device':'cpu',
    'source_access':'privileged-manual-pose-supervision','continuation_access':'policy.act-declared-sensing-only',
    'target_limit':1,'retries':0,'timeout_seconds':160,'internal_wall_seconds':150,
    'outer_timeout_seconds':3900,'recording_max_bytes':192*MiB,'snapshot_max_bytes':16*MiB,
    'aggregate_max_bytes':6*GiB,'min_free_bytes':2*GiB,'headroom_bytes':64*MiB,'log_max_bytes':MiB,
    'source_preparation':common.SOURCE_PREPARATION,'source_preparation_sha256':common.SOURCE_PREPARATION_SHA256,
    'goal_handoff':common.GOAL_HANDOFF,'goal_handoff_sha256':common.GOAL_HANDOFF_SHA256,
    'neural_helper_sha256':common._hash(HELPER),'manual_helper_sha256':common._hash(neural.HELPER),
    'case_producer_sha256':experiment.SOURCE_SHA256,'world_profile_sha256':memory_world.PROFILE_SHA256}
PROTOCOL_SHA256=memory.sha256(PROTOCOL)

# Only the predeclared forty-cell complement; no arbitrary cells/schedules.
REMAINING_CHUNKS = (
 ((24,'local_cue','null'),(24,'local_cue','no-event'),(24,'paired_cue','change'),(24,'paired_cue','null')),
 ((24,'paired_cue','no-event'),(25,'local_cue','null'),(25,'local_cue','no-event'),(25,'paired_cue','change')),
 ((25,'paired_cue','null'),(25,'paired_cue','no-event'),(26,'local_cue','change'),(26,'local_cue','null')),
 ((26,'local_cue','no-event'),(26,'paired_cue','change'),(26,'paired_cue','no-event'),(27,'local_cue','change')),
 ((27,'local_cue','null'),(27,'local_cue','no-event'),(27,'paired_cue','change'),(27,'paired_cue','null')),
 ((28,'local_cue','change'),(28,'local_cue','null'),(28,'local_cue','no-event'),(28,'paired_cue','null')),
 ((28,'paired_cue','no-event'),(29,'local_cue','change'),(29,'local_cue','null'),(29,'local_cue','no-event')),
 ((29,'paired_cue','null'),(29,'paired_cue','no-event'),(30,'local_cue','change'),(30,'local_cue','no-event')),
 ((30,'paired_cue','change'),(30,'paired_cue','null'),(30,'paired_cue','no-event'),(31,'local_cue','change')),
 ((31,'local_cue','null'),(31,'paired_cue','change'),(31,'paired_cue','null'),(31,'paired_cue','no-event')))
REMAINING_NAMES = tuple(f'remaining-{i:02d}' for i in range(1,11))
REMAINING_PROTOCOLS = {name: {**copy.deepcopy(PROTOCOL), 'version':2,
    'claim':'fixed-remaining-development-admission-only','chunk':i,
    'cells':[list(c) for c in cells],'total_owners':12,'max_numeric_ticks':1204,
    'outer_timeout_seconds':1980} for i,(name,cells) in enumerate(zip(REMAINING_NAMES,REMAINING_CHUNKS),1)}


def profile_digest(name=None):
    if name is None or name=='b':return PROTOCOL_SHA256
    if name not in REMAINING_PROTOCOLS:raise ValueError('Unknown fixed admission profile')
    return memory.sha256(REMAINING_PROTOCOLS[name])


def fixed_profile(protocol_sha256=None):
    if protocol_sha256 is None or protocol_sha256==PROTOCOL_SHA256:
        return CELLS,copy.deepcopy(PROTOCOL)
    for name,cells in zip(REMAINING_NAMES,REMAINING_CHUNKS):
        value=REMAINING_PROTOCOLS[name]
        if protocol_sha256==memory.sha256(value):return cells,copy.deepcopy(value)
    raise ValueError('Unknown fixed admission protocol')


def cell_key(cell):
    return f's{cell[0]}/{cell[1]}/{cell[2]}'


def make_case(cell):
    return experiment.make_world_case(*cell[:2],'development-test',kind=cell[2],acquisition=True,change_tick=300)


def coverage():
    """Independent synthetic geometry diagnostic; never passed to a live Engine."""
    result=[]
    for seed in range(24,32):
        for regime in memory.RELATIONS:
            for kind in experiment.KINDS:
                cell=(seed,regime,kind);case=experiment.validate_world_case(make_case(cell))
                fixture,truth=experiment.make_case(seed,regime,'development-test',kind=kind)
                before,after=truth['before_occupancy'],truth['after_occupancy']
                changed=[subject for subject in before if before[subject]!=after[subject]]
                if len(changed)!=int(kind=='change') or (fixture['trigger'] is None)!=(kind=='no-event'):
                    raise ValueError('Counterbalance geometry/schedule coverage differs')
                result.append({'cell':cell_key(cell),'case_id':case['case_id'],
                    'case_sha256':memory.sha256(case),'semantic_case_sha256':memory.sha256(common.semantic_case(case)),
                    'factors':[seed&1,(seed>>1)&1,(seed>>2)&1],
                    'synthetic_gold_count':len(truth['gold_target_ids']),
                    'claim':'synthetic-diagnostic-only; live bank unknown'})
    return result


def source_identity(repo,assets):
    result=neural.source_identity(repo,assets)
    result.update(driver_sha256=common._hash(Path(__file__)),neural_helper_sha256=common._hash(HELPER))
    return result


def budget(output, *, protocol_sha256=None):
    _,p=fixed_profile(protocol_sha256)
    return StorageBudget((Path(output),),StorageLimits(max_bytes=6*GiB,min_free_bytes=2*GiB,
        max_runs=p['total_owners'],max_snapshots=1),headroom_bytes=64*MiB)


def write(path,value,storage):
    return neural.write(path,value,storage)


def selector(protocol_sha256=None):
    _,p=fixed_profile(protocol_sha256)
    return {'version':1,'condition':'no-U','limit':1,'resource':None,
        'resource_sha256':memory.sha256(None),'provenance_sha256':memory.sha256(p)}


def validate_job(job,*,prepared=False):
    memory._fields(job,'repo assets output root_output run_id cell stage case protocol_sha256 source_identity snapshot_path snapshot_sha256 expected_non_u replacement_preserved')
    memory._bounded(job,128*1024)
    cells,p=fixed_profile(job['protocol_sha256'])
    if (type(job['cell']) is not list or tuple(job['cell']) not in cells or job['stage'] not in STAGES
            or job['protocol_sha256']!=memory.sha256(p)
            or Path(job['repo'])!=Path(__file__).resolve().parents[1]
            or str(artifacts._id(job['run_id']))!=str(artifacts._id(Path(job['output']).name))):
        raise ValueError('Unsupported fixed admission job')
    case=experiment.validate_world_case(job['case'])
    if memory.canonical_bytes(case)!=memory.canonical_bytes(make_case(tuple(job['cell']))):
        raise ValueError('Admission case differs from its exact declared cell')
    if any(not Path(job[key]).is_absolute() for key in ('repo','assets','output','root_output')):
        raise ValueError('Admission paths must be absolute')
    if Path(job['output'])!=Path(job['root_output'])/'runs'/job['run_id']:
        raise ValueError('Admission run path differs from root/ID')
    bound=[job[key] for key in ('snapshot_path','snapshot_sha256','expected_non_u','replacement_preserved')]
    if (job['stage']=='source' or prepared) and any(v is not None for v in bound):
        raise ValueError('Source may not restore a snapshot')
    if job['stage']!='source' and not prepared:
        if type(job['snapshot_path']) is not str or not Path(job['snapshot_path']).is_absolute():raise ValueError('Missing native ancestor path')
        memory._digest(job['snapshot_sha256'])
        if (job['stage']=='policy-anchor' and (type(job['replacement_preserved']) is not str or job['expected_non_u'] is not None)
                or job['stage']=='probe' and (type(job['expected_non_u']) is not dict or job['replacement_preserved'] is not None)):
            raise ValueError('Wrong controller/native restoration contract')
    return copy.deepcopy(job)


def make_plan(repo,assets,output, *, protocol_sha256=None):
    cells,p=fixed_profile(protocol_sha256);digest=memory.sha256(p)
    repo,assets,output=map(lambda p:artifacts._safe_path(p),(repo,assets,output))
    identity=source_identity(repo,assets);jobs=[]
    for cell in cells:
        for stage in STAGES:
            run_id=uuid.uuid4().hex
            jobs.append(validate_job({'repo':str(repo),'assets':str(assets),'output':str(output/'runs'/run_id),
                'root_output':str(output),'run_id':run_id,'cell':list(cell),'stage':stage,'case':make_case(cell),
                'protocol_sha256':digest,'source_identity':identity,'snapshot_path':None,
                'snapshot_sha256':None,'expected_non_u':None,'replacement_preserved':None},prepared=True))
    return {'protocol':p,'protocol_sha256':digest,'source_identity':identity,
        'coverage':coverage(),'jobs':jobs,'output':str(output)}


def validate_plan(plan):
    memory._fields(plan,'protocol protocol_sha256 source_identity coverage jobs output')
    memory._bounded(plan,MiB)
    cells,p=fixed_profile(plan['protocol_sha256'])
    if memory.canonical_bytes(plan['protocol'])!=memory.canonical_bytes(p) or plan['protocol_sha256']!=memory.sha256(p):
        raise ValueError('Frozen admission protocol differs')
    if memory.canonical_bytes(plan['coverage'])!=memory.canonical_bytes(coverage()) or len(plan['jobs'])!=p['total_owners']:
        raise ValueError('Admission design coverage differs')
    expected=[(list(c),s) for c in cells for s in STAGES]
    if [(j['cell'],j['stage']) for j in plan['jobs']]!=expected or len({j['run_id'] for j in plan['jobs']})!=p['total_owners']:
        raise ValueError('Admission owner IDs/order differ')
    for job in plan['jobs']:
        validate_job(job,prepared=True)
        if (job['source_identity']!=plan['source_identity'] or job['root_output']!=plan['output']
                or any(job[k]!=plan['jobs'][0][k] for k in ('repo','assets'))):
            raise ValueError('Admission job/source/root identity differs')
    return copy.deepcopy(plan)


def admit_packet(events,case,state,tick):
    """Validate actual packets without altering no-event state to fit old helpers."""
    if type(tick) is not int or tick not in (299,300):raise ValueError('Unsupported sensing boundary')
    found=[e for e in events if e['kind']=='memory_sensed' and e.get('episode_step')==tick]
    if len(found)!=1 or any(type(found[0].get(k)) is not int or found[0][k]!=v for k,v in [('tick',tick),('episode',0)]):
        raise ValueError('Missing or inconsistent actual sensing packet')
    packet=found[0]['packet'];memory_task._validate_packet(packet,state)
    expected=int(tick==300 and case['event_enabled'])
    required={case['common_goal_id'],*[f['inspection_landmark_id'] for f in case['facts']]}
    if (packet['tick']!=tick or packet['common_goal_id']!=case['common_goal_id']
            or not required.issubset({v['id'] for v in packet['landmarks']})
            or len(packet['cues'])!=1 or packet['cues'][0]['id']!=case['cue_id']
            or packet['cues'][0]['state']!=expected):
        raise ValueError('Actual cue/goal/both-landmark visibility differs')
    lower=next(v for v in packet['passages'] if v['subject_id']==case['subjects_by_side'][0])
    if lower['passability']!='unobserved':raise ValueError('Lower passage was newly observed at preparation boundary')
    return copy.deepcopy(packet)


def observed_trigger(source_state,data,case):
    packet=admit_packet(data['events'],case,source_state,300)
    before=source_state['detector'];cue=packet['cues'][0]
    if before['tick']!=299 or len(before['cues'])!=1 or before['cues'][0]['id']!=cue['id'] or before['cues'][0]['state']!=0:
        raise ValueError('Trigger lacks an actual consecutive native cue sample')
    recorded=[e for e in data['events'] if e['kind']=='memory_decision']
    if any((e.get('episode'),e.get('episode_step'),e.get('tick'))!=(0,300,300) for e in recorded):
        raise ValueError('Decision episode/boundary differs')
    decisions=[e['detail'] for e in recorded]
    triggers=[d['trigger'] for d in decisions if d['kind']=='memory_trigger']
    selections=[d['selection'] for d in decisions if d['kind']=='memory_selection']
    if not case['event_enabled']:
        if cue['state']!=0 or triggers or selections:raise ValueError('No-event contains a trigger/selection invocation')
        return None,[]
    episode=source_state['episode_id']
    expected=memory.validate_trigger({'id':memory_task._sensor_id(episode,300,'trigger',cue['id']),
        'episode_id':episode,'tick':300,'kind':'cue_changed','cue_id':cue['id'],'before':0,'after':1,
        'before_observation_id':before['cues'][0]['observation_id'],
        'observation_id':memory_task._sensor_id(episode,300,'cue',cue['id'])})
    if triggers!=[expected] or len(selections)!=1 or selections[0]!=memory.select(source_state['m'],expected,source_state['u']):
        raise ValueError('Actual recorded trigger/selection differs from consecutive cues')
    return expected,selections


def probe_result(case,source_native,report,data):
    """Actual clearance + retained expectations; never selector/regime-derived gold."""
    state=source_native['application']['memory'];trigger,selections=observed_trigger(state,data,case)
    before=common.occupancy(case,report['before_circles']);after=common.occupancy(case,report['after_circles'])
    gold=experiment.gold_target_ids(state['m'],before,after,trigger)
    targets=[] if not selections else selections[0]['target_ids']
    inspections=[e['detail'] for e in data['events'] if e['kind']=='memory_decision' and e['detail']['kind']=='memory_inspection']
    if targets or inspections or report['final_memory']['requests'] or report['final_memory']['active'] is not None:
        raise ValueError('Empty-U admission probe requested inspection')
    changed=[subject for subject in before if before[subject]!=after[subject]]
    expected_result='closed' if case['kind']=='change' else 'not_requested'
    if report['gate_result']!=expected_result or len(changed)!=int(case['kind']=='change'):
        raise ValueError('Actual gate/clearance differs from declared schedule')
    packet=admit_packet(data['events'],case,state,300)
    actual=[v for v in packet['passages'] if v['passability']!='unobserved']
    confirmations=[v['subject_id'] for v in actual if before[v['subject_id']]==after[v['subject_id']]]
    corrections=[v['subject_id'] for v in actual if before[v['subject_id']]!=after[v['subject_id']]]
    revisions=[e['detail']['revision'] for e in data['events'] if e['kind']=='memory_decision'
               and e['detail']['kind']=='memory_revision']
    return {'actual_recorded_revisions':revisions,'gold_target_ids':gold,'target_ids':targets,'selector_invocations':len(selections),
        'selector_behavior_bytes':0 if trigger is None else len(memory.canonical_bytes(
            {'m':state['m'],'trigger':trigger,'u.payload':state['u']['payload']})),
        'correct_abstention':not gold,'false_targets':0,'missed_targets':len(gold),
        'precision':None,'recall':0. if gold else None,'trigger':trigger,
        'actual_post_event_confirmations':confirmations,'actual_stale_value_observations':corrections,
        'before_occupancy':before,'after_occupancy':after,'observation_tick':300,
        'task_pass':None,'correction_completion_tick':None,'goal_tick':None,
        'scope':'one-tick admission coverage; no completed task or correction-time evaluation'}


def worker(raw):
    """Three fixed stages; only the source reads privileged pose."""
    from palimpsest.engine import Engine
    job=validate_job(raw)
    _,p=fixed_profile(job['protocol_sha256'])
    if source_identity(job['repo'],job['assets'])!=job['source_identity']:
        raise ValueError('Worker authoring source/assets changed')
    run,stage,case=Path(job['output']),job['stage'],job['case']
    storage=budget(job['root_output'],protocol_sha256=job['protocol_sha256']);storage.check(208*MiB,path=run)
    engine=None;started=time.monotonic()
    report={'stage':stage,'status':'failed','task_pass':None,'run_path':str(run)}
    try:
        restoration={}
        if stage!='source':
            if common._hash(job['snapshot_path'])!=job['snapshot_sha256']:
                raise ValueError('Ancestor snapshot changed')
            original=read_snapshot(job['snapshot_path'])
            preservation=(neural.replacement_preserved(original) if stage=='policy-anchor'
                          else common.baseline_invariants(original))
            if preservation!=job['replacement_preserved' if stage=='policy-anchor' else 'expected_non_u']:
                raise ValueError('Ancestor preservation guard differs')
            restoration={'restore_snapshot':original,'replace_controller':stage=='policy-anchor'}
        engine=Engine.open(job['repo'],job['assets'],run/'recording',run_id=job['run_id'],
            controller='manual' if stage=='source' else 'flynn',device='cpu',scenario='memory-passages',
            seed=case['seed'],memory_case=case,max_bytes=192*MiB,storage_budget=storage,**restoration)
        engine.writer.manifest.update(counterbalance_protocol=p,counterbalance_protocol_sha256=job['protocol_sha256'],
            counterbalance_cell=job['cell'],counterbalance_stage=stage,counterbalance_source_identity=job['source_identity'],
            source_preparation_protocol=common.SOURCE_PREPARATION,source_preparation_sha256=common.SOURCE_PREPARATION_SHA256,
            acquisition_schedule_override=common.ACQUISITION_OVERRIDE,
            goal_handoff_protocol=common.GOAL_HANDOFF,goal_handoff_sha256=common.GOAL_HANDOFF_SHA256,
            acquisition_access=p['source_access'],continuation_access=p['continuation_access'],
            selector_configuration=selector(job['protocol_sha256']) if stage=='probe' else None)
        engine._event('source_preparation_declared',protocol=common.SOURCE_PREPARATION,
            source_preparation_sha256=common.SOURCE_PREPARATION_SHA256,override=common.ACQUISITION_OVERRIDE)
        if stage=='source':
            for tick in range(300):
                if time.monotonic()-started>150:raise TimeoutError('Source wall bound')
                pose=[*map(float,engine.env._base_xy()),float(engine.env._base_yaw())]
                action=common.source_action(case['acquisition_schedule'],pose,tick)
                if tick>=200:engine._event('source_preparation_input',pose=pose,action=action,
                    source_preparation_sha256=common.SOURCE_PREPARATION_SHA256)
                if common._command_step(engine,action,f'prefix-{tick}')['phase']!='paused':
                    raise ValueError('Source acquisition/preparation did not remain paused')
            packet=admit_packet(artifacts._events(run),case,engine.memory,299)
            common.evidence_backed_source(engine.memory['m'],artifacts._events(run),engine.memory['episode_id'])
            report['packet299_sha256']=memory.sha256(packet)
            report['goal_handoff']=common.apply_goal_handoff(engine,case)
        else:
            current=capture(engine.env,engine.observation,policy=engine.policy,application=engine.application_state())
            if stage=='policy-anchor':
                if (neural.replacement_preserved(current)!=job['replacement_preserved']
                        or current['application']['revision']!=original['application']['revision']+1):
                    raise ValueError('Controller replacement changed preserved state')
            else:
                if common.baseline_invariants(current)!=job['expected_non_u']:
                    raise ValueError('Atomic neural restore changed non-U state')
                engine.memory=memory_task.configure_selector(engine.memory,selector(job['protocol_sha256']))
                engine._event('selector_configured',configuration=selector(job['protocol_sha256']),configuration_sha256=memory.sha256(selector(job['protocol_sha256'])))
                current=capture(engine.env,engine.observation,policy=engine.policy,application=engine.application_state())
                if common.baseline_invariants(current)!=job['expected_non_u']:
                    raise ValueError('No-U configuration changed non-selector state')
        report['before_circles']=memory_world.sensing_inputs(engine.env,engine.world_task_state)[2]
        _register_initial(engine,run,neural._SnapshotBudget(storage))
        initial=read_snapshot(run/'snapshots/initial.snp')
        report.update(snapshot_path=str(run/'snapshots/initial.snp'),snapshot_sha256=common._hash(run/'snapshots/initial.snp'),
            non_u=common.baseline_invariants(initial))
        if stage=='probe':
            neural.audit_policy(engine)
            if time.monotonic()-started>150:raise TimeoutError('Probe wall bound')
            if neural.policy_step(engine,300)['phase']!='paused':
                raise ValueError('One-tick probe did not remain paused; retained task/runtime failure')
            packet=admit_packet(artifacts._events(run),case,engine.memory,300)
            report['packet300_sha256']=memory.sha256(packet)
            report['after_circles']=memory_world.sensing_inputs(engine.env,engine.world_task_state)[2]
        report['status']='recorded'
    except Exception as error:
        report['error']={'type':type(error).__name__,'message':str(error)}
    finally:
        if engine is not None:
            report.update(final_phase=engine.phase,outcome=engine.last_outcome,steps=engine.episode_step,
                final_memory=copy.deepcopy(engine.memory),final_world=copy.deepcopy(engine.world_task_state))
            report['gate_result']=engine.world_task_state['gate_result']
            try:engine.close()
            except Exception as error:
                report.update(status='cleanup_failed',cleanup_error={'type':type(error).__name__,'message':str(error)})
    report['wall_seconds']=time.monotonic()-started
    write(run/'admission-worker.json',report,storage)
    return 0 if report['status']=='recorded' and report['final_phase']=='paused' else 1


def actual_packet(data,case,state):
    """Recompute the declared sensor from recorded pose and physical world only."""
    world=artifacts._world_at(data['events'],0,300)
    labels=common.occupancy(case,world['obstacles']);facts={f['subject_id']:f for f in case['facts']}
    symbolic={'common_goal_id':case['common_goal_id'],
        'cues':[{'id':case['cue_id'],'xy':case['cue_xy'],'state':int(case['event_enabled'])}],
        'landmarks':[{'id':case['common_goal_id'],'xy':world['goal'][:2]}]+
            [{'id':facts[s]['inspection_landmark_id'],'xy':xy} for s,xy in zip(case['subjects_by_side'],case['inspection_xy'])],
        'passages':[{'subject_id':s,'inspection_landmark_id':facts[s]['inspection_landmark_id'],'passability':labels[s]}
                    for s in case['subjects_by_side']]}
    expected=memory_task.capture_symbolic(symbolic,data['rows'][0]['pose'].tolist(),world['obstacles'],
        episode_id=state['episode_id'],tick=300)
    packet=admit_packet(data['events'],case,state,300)
    if memory.canonical_bytes(packet)!=memory.canonical_bytes(expected) or world['goal'][:2]!=common.effective_goal():
        raise ValueError('Actual packet differs from retained pose/clearance/LOS/FOV/range geometry')
    return packet,world['obstacles']


def validate_stage(job,supervised):
    """Authoritative readers and existing native/policy guards, with local schedule checks."""
    if supervised['status']!='completed' or supervised.get('returncode')!=0:
        raise ValueError('Worker/infrastructure failure; no retry')
    data=common.read_run(Path(job['output']));manifest,events=data['manifest'],data['events']
    report=artifacts._json(artifacts._read(data['run']/'admission-worker.json',MiB))
    native,entry,_=_initial_snapshot(data);app=native['application'];state=memory_task.validate_state(app['memory'])
    _,p=fixed_profile(job['protocol_sha256'])
    stage,case=job['stage'],job['case'];expected_steps=301 if stage=='probe' else 300
    expected={'memory_case':case,'memory_case_sha256':memory.sha256(case),'counterbalance_protocol':p,
        'counterbalance_protocol_sha256':job['protocol_sha256'],'counterbalance_cell':job['cell'],'counterbalance_stage':stage,
        'counterbalance_source_identity':job['source_identity'],'selector_configuration':selector(job['protocol_sha256']) if stage=='probe' else None,
        'source_preparation_protocol':common.SOURCE_PREPARATION,'source_preparation_sha256':common.SOURCE_PREPARATION_SHA256,
        'acquisition_schedule_override':common.ACQUISITION_OVERRIDE,'goal_handoff_protocol':common.GOAL_HANDOFF,
        'goal_handoff_sha256':common.GOAL_HANDOFF_SHA256,'acquisition_access':p['source_access'],
        'continuation_access':p['continuation_access']}
    if (any(memory.canonical_bytes(manifest.get(k))!=memory.canonical_bytes(v) for k,v in expected.items())
            or manifest.get('run_id')!=job['run_id'] or manifest.get('controller')!=('manual' if stage=='source' else 'flynn')
            or manifest.get('seed')!=case['seed'] or manifest.get('requested_device')!='cpu'
            or manifest.get('recording_max_bytes')!=192*MiB or manifest.get('status')!='completed'
            or manifest.get('close_reason')!='operator_closed' or manifest.get('final_phase')!='paused'
            or manifest.get('total_tick')!=expected_steps or report.get('steps')!=expected_steps
            or report.get('status')!='recorded' or report.get('final_phase')!='paused' or 'cleanup_error' in report
            or report.get('outcome')!=manifest.get('last_outcome') or report.get('stage')!=stage
            or report.get('run_path')!=job['output'] or report.get('task_pass') is not None
            or report.get('snapshot_sha256')!=entry['sha256']
            or report.get('snapshot_path')!=str(data['run']/'snapshots/initial.snp')
            or (data['run']/'snapshots/initial.snp').stat().st_size>16*MiB):
        raise ValueError('Stage terminal/controller/source/case/quota identity differs')
    environments=[e for e in events if e['kind']=='environment']
    if len(environments)!=1 or any(environments[0].get(k)!=job['source_identity'][k]
                                  for k in ('source_sha256','lock_sha256','upstream_commit')):
        raise ValueError('Recording authoring source differs')
    if (app['phase']!='paused' or (app['episode'],app['episode_step'],app['total_tick'])!=(0,300,300)
            or state['cursor']['tick']!=299 or state['detector']['tick']!=299
            or state['e']['episodes'] or state['u']!=memory.artifact(method='empty-v1')
            or state['requests'] or state['active'] is not None
            or state['initial_m']!=memory.seed_m(case['facts'],[]) or app['world_task_state'].get('case')!=case
            or app['world_task_state']['applied'] or report['non_u']!=common.baseline_invariants(native)
            or not np.array_equal(native['environment']['values']['_goal_xy'],np.asarray(common.effective_goal(),np.float32))):
        raise ValueError('Native source M/E/U/cursor/world/goal boundary differs')
    declarations=[e for e in events if e['kind']=='source_preparation_declared']
    if (len(declarations)!=1 or declarations[0].get('protocol')!=common.SOURCE_PREPARATION
            or declarations[0].get('source_preparation_sha256')!=common.SOURCE_PREPARATION_SHA256
            or declarations[0].get('override')!=common.ACQUISITION_OVERRIDE
            or declarations[0]['sequence']>=app['event_prefix']['event_count']):
        raise ValueError('Native prefix lacks its declared privileged source preparation')
    final=memory_task.validate_state(report['final_memory']);world=memory_world.validate_state(report['final_world'])
    if world.get('case')!=case or report['gate_result']!=world['gate_result']:
        raise ValueError('Final world case/gate identity differs')
    if any(memory.canonical_bytes(final.get(k))!=memory.canonical_bytes(state.get(k)) for k in ('e','u','selector','initial_m')):
        raise ValueError('Probe mutated its empty resources or initial bank')
    rows=[r['tick'] for r in data['rows']]
    if stage=='source':
        if (state['version']!=1 or rows!=list(range(300)) or app['controller']!='manual'
                or native['policy'] is not None or app['controller_tensors'] is not None
                or any(e['kind']=='neural_policy_call' for e in events)):
            raise ValueError('Manual source row/controller scope differs')
        common.source_controls(data,case);common.evidence_backed_source(state['m'],events,state['episode_id'])
        inspected=[e['memory'] for e in events if e['kind']=='memory_inspected']
        if (len(inspected)!=300 or any(v['u']!=state['u'] or v['hashes']['e']!=memory.sha256(state['e'])
                or v['counts']['episodes']!=0 or v['counts']['requests']!=0 for v in inspected)
                or any(e['kind']=='memory_decision' and e['detail']['kind'] in
                       ('memory_trigger','memory_selection','memory_inspection') for e in events)):
            raise ValueError('Source acquired history under selector/U guidance or missing audit packets')
        packet=admit_packet(events,case,state,299);common.packet_cursor(packet,state)
        if report['packet299_sha256']!=memory.sha256(packet):raise ValueError('Source packet299 hash differs')
        common.validate_goal_handoff(data,native,case,'source')
        probes=[e['proof'] for e in events if e['kind']=='goal_handoff_probe']
        if probes!=[report['goal_handoff']]:raise ValueError('Source goal handoff proof differs')
        if any(f['estimate']!=common.occupancy(case,report['before_circles'])[f['subject_id']] for f in state['m']['facts']):
            raise ValueError('Acquired before expectations disagree with actual source clearance')
    else:
        original=read_snapshot(job['snapshot_path'])
        if common._hash(job['snapshot_path'])!=job['snapshot_sha256']:raise ValueError('Ancestor snapshot mutated')
        expected_admission={'source_run_id':original['application']['source_run_id'],
            'source_controller':original['application']['controller'],'snapshot_state_sha256':state_digest(original),
            'native_sha256':original['native_sha256'],'case_sha256':memory.sha256(case),
            'replace_controller':stage=='policy-anchor','memory_u_sha256':None}
        if (manifest.get('memory_continuation_admission')!=expected_admission or app['controller']!='flynn'
                or app['execution_mode']!='live' or native['policy'] is None or app['controller_tensors'] is None
                or native['identity']['policy']['device']!='cpu'):
            raise ValueError('Atomic CPU policy admission differs')
        if stage=='policy-anchor':
            changes=[e for e in events if e['kind']=='controller_replaced']
            if (neural.replacement_preserved(native)!=job['replacement_preserved']
                    or app['revision']!=original['application']['revision']+1 or state['version']!=1
                    or len(changes)!=1 or changes[0].get('old')!='manual' or changes[0].get('new')!='flynn'
                    or changes[0]['sequence']>=app['event_prefix']['event_count']
                    or any(app[k] for k in ('pending_commands','receipts','original_commands')) or app['manual_action']!=[0.,0.]):
                raise ValueError('Replacement changed preserved physical/memory state or fresh intent')
        elif common.baseline_invariants(native)!=job['expected_non_u'] or state.get('selector')!=selector(job['protocol_sha256']):
            raise ValueError('Probe changed non-selector policy/native/RNG/task state')
        configured=[e for e in events if e['kind']=='selector_configured']
        if stage=='policy-anchor':
            if rows or configured or any(e['kind']=='neural_policy_call' for e in events):
                raise ValueError('Zero-step empty-U policy anchor stepped/configured')
        else:
            if rows!=[300] or len(configured)!=1 or configured[0].get('configuration')!=selector(job['protocol_sha256']) or \
                    configured[0].get('configuration_sha256')!=memory.sha256(selector(job['protocol_sha256'])) or \
                    configured[0]['sequence']>=app['event_prefix']['event_count']:
                raise ValueError('One-tick no-U probe/configuration boundary differs')
            neural.policy_bindings(data)
            packet,circles=actual_packet(data,case,state)
            if report['packet300_sha256']!=memory.sha256(packet) or report['after_circles']!=circles:
                raise ValueError('Probe packet/actual after geometry report differs')
            inspected=[e['memory'] for e in events if e['kind']=='memory_inspected']
            if inspected!=[memory_task.inspect(final)] or common.packet_cursor(packet,final) is None:
                raise ValueError('Recorded inspection differs from committed actual final memory')
            recorded_world=[e['detail'] for e in events if e['kind']=='memory_world_changed']
            if world['cue_state']!=int(case['event_enabled']) or world['applied']!=case['event_enabled'] or world['last_tick']!=300:
                raise ValueError('Actual final world schedule state differs')
            expected_kinds=[] if not case['event_enabled'] else ['memory_cue_changed']+(
                ['memory_gate_applied'] if case['kind']=='change' else [])+['memory_passage_geometry']
            if [e['kind'] for e in recorded_world]!=expected_kinds or any(e['tick']!=300 for e in recorded_world):
                raise ValueError('Actual cue/gate schedule receipt differs')
            boundary=[e for e in events if e['kind'] in ('memory_sensed','memory_cue','memory_inspected',
                'memory_world_changed','memory_decision','neural_policy_call')]
            if any(any(type(e.get(k)) is not int or e[k]!=v for k,v in
                       (('episode',0),('episode_step',300),('tick',300))) for e in boundary):
                raise ValueError('Probe recorded event episode/tick lineage differs')
            if recorded_world and (recorded_world[-1]['before']!=common.occupancy(case,report['before_circles'])
                    or recorded_world[-1]['after']!=common.occupancy(case,circles)):
                raise ValueError('Schedule receipt clearance differs from actual retained circles')
            observed_trigger(state,data,case)
    if stage!='probe' and (final!=state or world!=app['world_task_state']):
        raise ValueError('Zero-continuation source/anchor changed after native capture')
    before=(report['goal_handoff']['world']['obstacles'] if stage=='source' else
        artifacts._world_at([e for e in events if e.get('origin')!='memory_world_schedule'],0,300)['obstacles'])
    if report['before_circles']!=before:
        raise ValueError('Reported pre-event geometry differs from recorded actual world')
    return data,report,native,entry


def run_verifier(raw):
    plan=validate_plan(raw);_,p=fixed_profile(plan['protocol_sha256']);jobs=plan['jobs'];output=Path(plan['output'])
    if source_identity(jobs[0]['repo'],jobs[0]['assets'])!=plan['source_identity']:
        raise ValueError('Source/assets changed after planning')
    if output.exists():raise ValueError('Output must be fresh; no retries')
    existing=output.parent
    while not existing.exists():existing=existing.parent
    if shutil.disk_usage(existing).free<8*GiB+64*MiB:
        raise ValueError('Admission requires 6 GiB allowance + 2 GiB floor + headroom')
    storage=budget(output,protocol_sha256=plan['protocol_sha256']);summaries=[];retained=[];parents={};started=time.monotonic()
    result={'version':1,'claim':p['claim'],'protocol_sha256':plan['protocol_sha256'],
        'status':'admission_unverified','runs':summaries,'r2_complete':False,'held_out_executed':False,
        'full_comparison_executed':False,'coverage':plan['coverage']}
    env={**os.environ,'PYTHONPATH':str(Path(jobs[0]['repo'])/'src'),
        'MUJOCO_GL':'egl','MPLBACKEND':'Agg','OMP_NUM_THREADS':'2'}
    with storage.lock():  # One parent lease; one serialized child is the only payload writer.
        (output/'runs').mkdir();storage.check_count('runs',0,p['total_owners'])
        write(output/'admission-plan.json',plan,storage)
        current_job=None;current_summary=None
        try:
            for raw_job in jobs:
                current_job=raw_job;current_summary=None
                if time.monotonic()-started>p['outer_timeout_seconds']-160:
                    raise TimeoutError('No aggregate wall budget for another owner')
                job=copy.deepcopy(raw_job);key,stage=cell_key(job['cell']),job['stage']
                if stage!='source':
                    ancestor=parents[(key,'source' if stage=='policy-anchor' else 'policy-anchor')]
                    job.update(snapshot_path=ancestor[1]['snapshot_path'],snapshot_sha256=ancestor[1]['snapshot_sha256'])
                    job['replacement_preserved' if stage=='policy-anchor' else 'expected_non_u']=(
                        neural.replacement_preserved(ancestor[2]) if stage=='policy-anchor' else ancestor[1]['non_u'])
                validate_job(job);write(output/f"{job['run_id']}-job.json",job,storage)
                print(json.dumps({'cell':key,'stage':stage,'run_id':job['run_id']}),flush=True)
                supervised=bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',json.dumps(job)],
                    Path(job['output']),160,env,log_max_bytes=MiB,storage_budget=storage)
                summary={'cell':key,'stage':stage,'run_id':job['run_id'],'run_path':job['output'],'supervisor':supervised}
                summaries.append(summary);current_summary=summary
                data,report,native,entry=validate_stage(job,supervised)
                parents[(key,stage)]=(data,report,native);retained.append((data,report,summary))
                summary.update(admission_pass=True,task_pass=None,final_phase=report['final_phase'],
                    worker_report_sha256=common._hash(data['run']/'admission-worker.json'),snapshot_sha256=entry['sha256'],
                    initial_non_u=common.baseline_invariants(native),
                    files=[{'path':str(p.relative_to(data['run'])),'bytes':p.stat().st_size,'sha256':common._hash(p)} for p in data['paths']])
                if stage=='probe':
                    source=parents[(key,'source')]
                    if report['before_circles']!=source[1]['before_circles']:
                        raise ValueError('Shared source/probe pre-event geometry differs')
                    summary['readout']=probe_result(job['case'],source[2],report,data)
            result['status']='admission_checked'
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,TimeoutError) as error:
            result['first_failure']={'type':type(error).__name__,'message':str(error),
                'cell':None if current_job is None else cell_key(current_job['cell']),
                'stage':None if current_job is None else current_job['stage'],
                'run_id':None if current_job is None else current_job['run_id'],
                'scope':'before-owner' if current_summary is None else 'attempted-owner'}
            if current_summary is not None:current_summary.update(admission_pass=False,failure=result['first_failure'])
        result['unattempted_stages']=[{'cell':cell_key(j['cell']),'stage':j['stage'],'run_id':j['run_id'],
            'status':'unattempted','reason':'first failure; no retries/replacements'} for j in jobs[len(summaries):]]
        final=None;changed=False
        try:
            final=source_identity(jobs[0]['repo'],jobs[0]['assets'])
            changed=any(artifacts._fingerprint(d['paths'])!=d['fingerprint'] or
                common._hash(r['snapshot_path'])!=r['snapshot_sha256'] or
                common._hash(d['run']/'admission-worker.json')!=s['worker_report_sha256'] for d,r,s in retained)
        except (OSError,ValueError,KeyError,TypeError) as error:
            changed=True;result.setdefault('first_failure',{'type':type(error).__name__,'message':str(error)})
        result.update(source_identity=plan['source_identity'],final_source_identity=final,
            source_unchanged=final==plan['source_identity'],retained_unchanged=not changed,
            wall_seconds=time.monotonic()-started,storage_usage=storage.usage(),
            ownership_terminal='serialized bounded_process cleanup; independent outer PID/start survey still required')
        if changed or not result['source_unchanged']:result['status']='admission_unverified'
        write(output/'admission-report.json',result,storage)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixed-profile',choices=('b',*REMAINING_NAMES))
    parser.add_argument('--worker');parser.add_argument('--prepared-plan',type=Path)
    parser.add_argument('--prepared-plan-sha256');parser.add_argument('--plan-only',action='store_true')
    for name in ('repo','assets','output'):parser.add_argument('--'+name,type=Path)
    args=parser.parse_args()
    if args.worker is not None:
        if args.fixed_profile is not None:parser.error('Worker profile comes only from its validated job')
        return worker(json.loads(args.worker))
    if args.prepared_plan is not None:
        if args.prepared_plan_sha256 is None or args.plan_only or args.fixed_profile is not None or any(getattr(args,n) is not None for n in ('repo','assets','output')):
            parser.error('Prepared plan requires its hash and no planning arguments')
        plan=neural.read_prepared_plan(args.prepared_plan,args.prepared_plan_sha256)
        return 0 if run_verifier(plan)['status']=='admission_checked' else 1
    if args.prepared_plan_sha256 is not None or not args.plan_only or any(getattr(args,n) is None for n in ('repo','assets','output')):
        parser.error('Only --plan-only --repo --assets --output or a hash-bound prepared plan is supported')
    print(json.dumps(make_plan(args.repo,args.assets,args.output,protocol_sha256=profile_digest(args.fixed_profile)),indent=2,allow_nan=False));return 0


if __name__=='__main__':
    raise SystemExit(main())
