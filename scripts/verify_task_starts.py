"""TGT-HO-START-1: four frozen standalone manual task cases, not a public case API."""
import argparse
import copy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
import uuid

from verify_tasks import (SCENARIOS, DRIVERS, cue_action, previous_bearing, command,
                          evaluator_sample, evaluator_record, evaluate_motion, file_hashes)
from verify_task_phases import initial_ready, preflight as camera_preflight
from verify_body_adaptation import read_json, cleanup_observed
from verify_body_gains import write_json
from verify_body_runtime import digest
from verify_endurance import source_identity, descendants

MiB=1024**2
STARTS=[{'id':'ho-start-north-1001','start_pose':[-2.75,.15,.1],'seed':1001},
        {'id':'ho-start-south-1002','start_pose':[-2.75,-.15,-.1],'seed':1002}]
CASES=[{**copy.deepcopy(case),'scenario':scenario,'driver':'v1' if scenario==SCENARIOS[0] else 'v2'}
       for case in STARTS for scenario in SCENARIOS]
PROTOCOL={'id':'TGT-HO-START-1','version':1,'cases':CASES,'controller':'manual','device':'cpu','texture':'checker',
    'driver_input':'previous recorded effective sensors[2:4] only; initial zero; no task/pose/evaluator feedback',
    'drivers':DRIVERS,'source_max_ticks':600,'owners':8,'maximum_numeric_ticks':4800,'snapshot_files':8,
    'snapshot_max_bytes':16*MiB,'recording_max_bytes':256*MiB,'output_max_bytes':2048*MiB,'min_free_bytes':1024*MiB,
    'child_timeout_seconds':180,'inner_timeout_seconds':1560,'outer_timeout_seconds':1620,
    'row_result_max_bytes':64*MiB,'control_max_bytes':MiB,'log_max_bytes':MiB,'headroom_bytes':8*MiB,
    'homing_declared_origin_max_distance_m':.25,
    'source_outcomes':'Continue all four sources for completed collision/stalled/task_completed/time_limit recordings; stop only infrastructure/invariant/storage failure',
    'replay':'one actions replay for each completed source including unsuccessful task outcome; no policy replay or phase restoration repetition',
    'context':'standalone start override source manifest/event and registered initial native state; replay source-run link plus exact normalized initial SNP; no generic playback claim',
    'scope':'four fixed start/task cases on one authored layout; manual sensor-only demonstrations, not population, body adaptation, learned policy or physical qualification'}
PROTOCOL_SHA256=hashlib.sha256(json.dumps(PROTOCOL,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def case_key(case):
    return case['id']+'/'+case['scenario']


def geometry_preflight():
    from palimpsest import memory_world, memory_task, task_profiles
    result={}
    for case in STARTS:
        positions=memory_world.validate_layout(start_pose=case['start_pose'])
        world={'cues':[],'landmarks':copy.deepcopy(task_profiles.LANDMARKS),'passages':[],
               'common_goal_id':task_profiles.LANDMARKS[-1]['id']}
        packet=memory_task.capture_symbolic(world,case['start_pose'],
            [[*xy,memory_world.OBSTACLE_RADIUS] for xy in positions],episode_id='episode-0',tick=0)
        if {p['id'] for p in packet['landmarks']}!={p['id'] for p in task_profiles.LANDMARKS}:
            raise ValueError('Frozen start lacks both declared initial visible landmarks')
        result[case['id']]={'placement_valid':True,'initial_visible_landmarks':packet['landmarks']}
    return result


def admission(observation):
    # Reuse the unchanged camera-schema/numeric allowance guard, not its phase-gate totals.
    base=camera_preflight(observation);per_tick=base['per_tick_bytes']
    allowances={'numeric_bytes':4800*per_tick,'snapshot_bytes':8*16*MiB,'row_result_bytes':8*64*MiB,
                'native_logs_bytes':18*MiB,'control_bytes':24*MiB,'atomic_native_staging_bytes':128*MiB,'headroom_bytes':8*MiB}
    total=sum(allowances.values())
    if total>2*1024**3:
        raise ValueError('Frozen task-start admission exceeds 2 GiB')
    return {'aggregate_bytes':total,'per_recording_bytes':base['per_recording_bytes'],'allowances':allowances}


def natural_outcome(state):
    outcome=state.get('last_outcome') or {};reason=outcome.get('reason')
    if ((state['phase']=='terminated' and reason in ('collision','stalled','task_completed')) or
            (state['phase']=='truncated' and reason=='time_limit')):
        return reason
    raise ValueError('Missing/invalid normal outcome; infrastructure or task invariant failure')


def capability(state, case, endpoint):
    reason=natural_outcome(state)
    if (not isinstance(endpoint,(list,tuple)) or len(endpoint)!=3 or
            any(type(value) not in (int,float) or not math.isfinite(value) for value in endpoint)):
        raise ValueError('Invalid evaluator endpoint pose')
    distance=math.dist(endpoint[:2],case['start_pose'][:2])
    completed=reason=='task_completed' and state['task']['phase']=='complete'
    if case['scenario']==SCENARIOS[0]:
        passed=completed and set(state['task']['completed_ids'])=={'inspect-a','inspect-b'}
    else:
        passed=completed and distance<=.25
    return {'passed':passed,'natural_outcome':reason,
            'declared_origin_actual_home_distance_m':distance if case['scenario']==SCENARIOS[1] else None,
            'declared_origin_pose':case['start_pose'],'threshold_m':.25 if case['scenario']==SCENARIOS[1] else None,
            'engine_default_origin_outcome':copy.deepcopy(state['last_outcome']),
            'evaluator_only':True}


def fresh_boundary(engine):
    import numpy as np
    env=engine.env
    if (engine.phase!='paused' or engine.total_tick or engine.episode_step or engine.episode or
            env.data.time!=0. or env._t!=0 or env._speed!=0. or env._stall_steps!=0 or
            np.any(env.data.qvel) or np.any(env.data.ctrl) or np.any(env._last_action) or np.any(engine.manual_action) or
            engine.task_state['last_tick'] is not None or engine.task_state['odometry']['travel_m']!=0. or
            env.path_to_draw is not None or env.target_to_draw is not None or
            any(getattr(env.planner,name) is not None for name in ('_cached_occ','_cached_obstacles_hash','_cached_clearance','_W','_H','_origin')) or
            env.visited!={env._bin_of(env._base_xy(),env.explore_binsize)} or
            not np.array_equal(env._prev_xy,env._base_xy())):
        raise ValueError('Standalone override requires untouched fresh pose-dependent episode state')


def author_start(engine, case):
    import mujoco
    from palimpsest.profiles import validate_world
    from palimpsest.snapshots import _model_digest
    fresh_boundary(engine)
    env=engine.env;old_world=engine.world();old=evaluator_sample(engine);model=_model_digest(env.model)
    task=copy.deepcopy(engine.task_state)
    env.place_robot(*case['start_pose'],env.data.qpos.copy(),env.data.qvel.copy())
    mujoco.mj_forward(env.model,env.data)
    env._prev_xy=env._base_xy().copy();env._reset_exploration()
    engine.observation=env._get_obs()
    validate_world(env);fresh_boundary(engine)
    new=evaluator_sample(engine)
    if (not math.isclose(math.remainder(new['pose'][2]-case['start_pose'][2],math.tau),0.,abs_tol=1e-7) or
            math.dist(new['pose'][:2],case['start_pose'][:2])>1e-7 or new['angles']!=[0.,0.] or
            task!=engine.task_state or _model_digest(env.model)!=model):
        raise ValueError('Actual start/model/task differs from declared data-only override')
    engine.revision+=1
    context={'case':copy.deepcopy(case),'old_pose':old['pose'],'new_pose':new['pose'],
             'old_world':old_world,'new_world':engine.world(),'model_sha256':model,
             'profile_sha256':task['profile_sha256'],'protocol_sha256':PROTOCOL_SHA256,
             'scope':'standalone data-only start override; original episode_started is history; generic playback reader not qualified'}
    identity=hashlib.sha256(json.dumps(context,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
    engine.writer.manifest.update(standalone_task_case=case,standalone_task_override=context,
                                 standalone_task_override_sha256=identity,initial_world=context['new_world'])
    engine.writer.event('task_start_authored',context=context,override_sha256=identity,revision=engine.revision)
    return context,identity


def normalized_snapshot(value):
    from palimpsest.snapshots import state_digest
    value=copy.deepcopy(value)
    for key in ('source_run_id','event_prefix','execution_mode'):
        value['application'].pop(key)
    return state_digest(value)


def normalized_initial(run):
    from palimpsest.artifacts import _events
    from palimpsest.replay import _initial_snapshot
    value,registration,_=_initial_snapshot({'run':run,'events':_events(run),'manifest':read_json(run/'recording/manifest.json')})
    return normalized_snapshot(value),registration['sha256']


def storage(config, control=False):
    from palimpsest.storage import StorageBudget, StorageLimits
    value=config['storage']
    return StorageBudget(tuple(Path(p) for p in value['roots']),StorageLimits(**value['limits']),
                         headroom_bytes=0 if control else value['headroom_bytes'])


def save(path,value,config,maximum=MiB):
    write_json(path,value,max_bytes=maximum,storage_budget=storage(config,True))


def harness_hashes():
    return {name:digest(Path(__file__).with_name(name)) for name in ('verify_task_starts.py','verify_tasks.py',
        'verify_task_phases.py','verify_body_adaptation.py','verify_body_runtime.py','verify_body_gains.py',
        'verify_body_compensation.py','verify_body_calibration.py','verify_endurance.py')}


def worker(config):
    from palimpsest.engine import Engine
    from palimpsest.replay import _register_initial,replay_run
    case=config['case'];run=Path(config['run']);stage=Path(config['stage']);budget=storage(config)
    result={'status':'failed','run':str(run),'case':case};rows=[];engine=None
    try:
        run.mkdir(exist_ok=False)
        if config['mode']=='actions':
            source=Path(config['source']);manifest=read_json(source/'recording/manifest.json')
            context=manifest['standalone_task_override'];identity=manifest['standalone_task_override_sha256']
            computed=hashlib.sha256(json.dumps(context,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
            if (manifest['standalone_task_case']!=case or context['case']!=case or
                    identity!=computed or identity!=config['override_sha256']):
                raise ValueError('Immutable source case/override identity differs')
            replay=replay_run(source,run,mode='actions',repo_root=Path(config['repo']),asset_root=Path(config['assets']),
                storage_budget=budget,recording_max_bytes=256*MiB,
                progress=lambda stage,state=None:initial_ready(run,stage,state))
            destination=read_json(run/'recording/manifest.json')
            a,source_sha=normalized_initial(source);b,replay_sha=normalized_initial(run)
            if (replay['status']!='passed' or replay['compared_ticks']!=config['source_ticks'] or
                    destination['replay_source_run_id']!=source.name or a!=b):
                raise ValueError('Action replay/source-link/normalized initial native state differs')
            result.update(status='completed-recording',compared_ticks=replay['compared_ticks'],engine_closed=True,
                          source_case=case,source_override_sha256=identity,source_run_id=source.name,
                          normalized_initial_sha256=a,source_initial_sha256=source_sha,replay_initial_sha256=replay_sha)
        else:
            engine=Engine.open(Path(config['repo']),Path(config['assets']),run/'recording',controller='manual',device='cpu',
                seed=case['seed'],scenario=case['scenario'],texture='checker',run_id=run.name,max_bytes=256*MiB,storage_budget=budget)
            context,identity=author_start(engine,case)
            result.update(override=context,override_sha256=identity)
            estimate=admission(engine.observation);result['admission']=estimate
            budget.check(estimate['aggregate_bytes'] if config['first_source'] else estimate['per_recording_bytes']+20*MiB,path=run)
            engine.writer.event('task_start_verifier_protocol',protocol=PROTOCOL,harness_sha256=harness_hashes())
            _register_initial(engine,run,budget);initial_ready(run,'ready')
            for tick in range(600):
                action=cue_action(previous_bearing(engine.last_transition),driver=case['driver'])
                before=evaluator_sample(engine)
                command(engine,f'action-{tick}','set_action',{'action':action});command(engine,f'step-{tick}','step')
                rows.append({'task':copy.deepcopy(engine.task_state),'evaluator':evaluator_record(engine,before,
                    evaluator_sample(engine),case['start_pose'],action)})
                if engine.phase!='paused':break
            state=engine.public_state();endpoint=evaluator_sample(engine)['pose']
            result.update(status='completed-recording',recorded_ticks=len(rows),final_state=state,
                          criterion=capability(state,case,endpoint),actual_endpoint_pose=endpoint,
                          motion=evaluate_motion([r['evaluator'] for r in rows],engine.task_state['odometry']['calibration']))
    except Exception as error:
        result.update(status='failed-infrastructure',error={'type':type(error).__name__,'message':str(error)[:1024]})
    finally:
        if engine is not None:
            try:
                result['raw_boundary']={'task':copy.deepcopy(engine.task_state),'state':engine.public_state()}
                import numpy as np
                cameras={key:engine.observation[key] for key in ('cam_left','cam_right')}
                if any(a.dtype!=np.uint8 or a.shape!=(128,128,3) for a in cameras.values()):
                    raise ValueError('Raw boundary camera shape/dtype differs')
                buffer=io.BytesIO();np.savez(buffer,**cameras);payload=buffer.getvalue()
                if len(payload)>MiB:raise ValueError('Raw boundary cameras exceed 1 MiB')
                path=stage/'boundary-cameras.npz';budget.check(len(payload),path=path)
                with path.open('xb') as stream:stream.write(payload)
                result['raw_boundary_cameras_sha256']=digest(path)
            except Exception as error:
                result.update(status='failed-infrastructure',diagnostic_error=str(error)[:512])
            finally:
                try:
                    engine.close();result['engine_closed']=True
                except Exception as error:
                    result.update(status='failed-infrastructure',cleanup_error=str(error)[:512])
        save(stage/'rows.json',rows,config,64*MiB);save(stage/'result.json',result,config)
    return result['status']=='completed-recording'


def gate(config):
    from palimpsest.evaluate import bounded_process
    from palimpsest.assets import verify_assets
    from palimpsest.records import iter_ticks
    output=Path(config['output']);root=Path(config['repo']);report=read_json(output/'report.json');budget=storage(config)
    count=0;owners=0;attempted=0;completed=0
    try:
        report['geometry_preflight']=geometry_preflight();report['assets_before']=verify_assets(root,Path(config['assets']))
        if not report['assets_before']['ok']:raise ValueError('Pinned assets unavailable')
        env={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','OMP_NUM_THREADS':'2','MPLBACKEND':'Agg'}
        for case_index,case in enumerate(CASES):
            key=case_key(case);base=output/case['id']/case['scenario'];base.mkdir(parents=True)
            source=None;immutable=None
            for mode in ('source','actions'):
                stage=base/mode;child={**config,'case':case,'mode':mode,'stage':str(stage),
                    'run':str(stage/uuid.uuid4().hex),'first_source':case_index==0}
                if source is not None:
                    child.update(source=source['run'],source_ticks=source['recorded_ticks'],override_sha256=source['override_sha256'])
                budget.check_count('runs',owners);owners+=1
                if mode=='source':attempted+=1
                report.update(owners_started=owners,attempted_cases=attempted,executed_cases=completed)
                save(output/'report.json',report,config)
                supervision=bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',json.dumps(child)],
                    stage,180,env,log_max_bytes=MiB,storage_budget=budget)
                item=report['cases'][key][mode]={'status':'failed-infrastructure','supervision':supervision}
                if not(stage/'result.json').exists():raise ValueError(key+'/'+mode+' missing retained result')
                result=read_json(stage/'result.json');item.update(result=result,result_sha256=digest(stage/'result.json'))
                if supervision['status']!='completed' or result['status']!='completed-recording' or result.get('engine_closed') is not True:
                    raise ValueError(key+'/'+mode+' infrastructure/invariant failure')
                run=Path(result['run']);manifest=read_json(run/'recording/manifest.json');ticks=list(iter_ticks(run/'recording'))
                n=result.get('recorded_ticks',result.get('compared_ticks'))
                if (manifest['status']!='completed' or len(ticks)!=n or not 1<=n<=600 or
                        [int(row['tick']) for row in ticks]!=list(range(n)) or
                        any(int(row['episode'])!=0 for row in ticks)):
                    raise ValueError(key+'/'+mode+' invalid recording')
                count+=n
                if count>4800:raise ValueError('Numeric bound exceeded')
                item.update(status='completed-recording',numeric_ticks=n)
                report.update(numeric_ticks=count,owners_started=owners)
                if mode=='source':
                    source=result;immutable=file_hashes(run);report['cases'][key]['criterion']=result['criterion']
                    completed+=1;report['executed_cases']=completed
                elif immutable!=file_hashes(Path(source['run'])):
                    raise ValueError('Immutable source changed')
                save(output/'report.json',report,config)
        shots=list(output.rglob('*.snp'))
        if len(shots)!=8 or any(not 0<p.stat().st_size<=16*MiB for p in shots):raise ValueError('Exact initial snapshot bounds differ')
        criteria=[report['cases'][case_key(case)]['criterion']['passed'] for case in CASES]
        report.update(status='passed' if all(criteria) else 'failed-functional',protocol_status='completed',
                      capability_passed=all(criteria),executed_cases=4,successful_cases=sum(criteria),numeric_ticks=count,snapshot_files=8)
    except Exception as error:
        report.update(status='failed-infrastructure',protocol_status='incomplete',error={'type':type(error).__name__,'message':str(error)[:1024]},numeric_ticks=count)
    finally:
        report['assets_after']=verify_assets(root,Path(config['assets']))
        if report.get('assets_before')!=report['assets_after']:report['status']='failed-infrastructure'
        save(output/'report.json',report,config)
    return report['status']=='passed'


def supervision_matches(report, supervision):
    if 'failure' in supervision or 'error' in supervision:
        return False
    if report.get('status')=='passed':
        return supervision.get('status')=='completed' and supervision.get('returncode')==0
    return (report.get('status')=='failed-functional' and report.get('protocol_status')=='completed' and
            report.get('executed_cases')==len(CASES) and report.get('capability_passed') is False and
            supervision.get('status')=='failed' and supervision.get('returncode')==1 and
            all(report.get('cases',{}).get(case_key(case),{}).get(mode,{}).get('status')=='completed-recording'
                for case in CASES for mode in ('source','actions')))


def verify(args):
    from dataclasses import asdict
    from palimpsest.storage import StorageBudget,StorageLimits
    from palimpsest.evaluate import bounded_process
    root,assets,output=args.repo.resolve(),args.assets.resolve(),args.output.resolve()
    if assets.is_relative_to(output) or output.is_relative_to(assets):raise ValueError('Assets outside managed output required')
    geometry=geometry_preflight();output.mkdir(parents=True,exist_ok=False)
    limits=StorageLimits(max_bytes=2*1024**3,min_free_bytes=1024**3,max_runs=8,max_snapshots=1,max_exports=1)
    budget=StorageBudget((output,),limits,headroom_bytes=8*MiB)
    config={'repo':str(root),'assets':str(assets),'output':str(output),'storage':{'roots':[str(output)],'limits':asdict(limits),'headroom_bytes':8*MiB}}
    report={'status':'running','protocol':PROTOCOL,'protocol_sha256':PROTOCOL_SHA256,'runtime_source':source_identity(root),
            'harness_sha256':harness_hashes(),'geometry_preflight':geometry,'numeric_ticks':0,'owners_started':0,'attempted_cases':0,'executed_cases':0,
            'cases':{case_key(c):{'case':c,'source':{'status':'not_started'},'actions':{'status':'not_started'}} for c in CASES}}
    known={};errors=[];stop=threading.Event()
    def sample():
        try:
            while not stop.is_set():
                for row in descendants(os.getpid()):
                    if row['pid'] not in known and len(known)>=256:raise ValueError('Finite descendant inventory exceeds256')
                    known[row['pid']]=row['start_ticks']
                stop.wait(.25)
        except Exception as error:errors.append(str(error)[:512]);stop.set()
    sampler=threading.Thread(target=sample,daemon=True);started=time.monotonic()
    with budget.lock():
        save(output/'report.json',report,config);sampler.start()
        try:
            env={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','OMP_NUM_THREADS':'2','MPLBACKEND':'Agg'}
            supervision=bounded_process([sys.executable,str(Path(__file__).resolve()),'--gate',json.dumps(config)],
                output/'outer-supervision',1560,env,log_max_bytes=MiB,storage_budget=budget)
            report=read_json(output/'report.json');report['inner_supervision']=supervision
            if not supervision_matches(report,supervision):report['status']='failed-infrastructure'
        except Exception as error:
            report.update(status='failed-infrastructure',error={'type':type(error).__name__,'message':str(error)[:1024]})
        finally:
            stop.set();sampler.join(timeout=2.)
            report['cleanup']={**cleanup_observed(dict(known)),'sample_errors':errors,'sampler_stopped':not sampler.is_alive(),
                'observed_owned_processes':[{'pid':pid,'start_ticks':start} for pid,start in sorted(known.items())],
                'scope':'finite .25s sampling and final PID/start checks; no universal transient-process proof'}
            report.update(wall_seconds=time.monotonic()-started,final_source=source_identity(root),final_harness=harness_hashes())
            if (report['cleanup']['forced_signals'] or report['cleanup']['survivors'] or errors or sampler.is_alive() or
                    report['runtime_source']!=report['final_source'] or report['harness_sha256']!=report['final_harness']):
                report['status']='failed-infrastructure'
            report['usage']=budget.usage();report['artifacts_sha256']={k:v for k,v in file_hashes(output).items() if k not in ('report.json','.palimpsest-storage.lock')}
            save(output/'report.json',report,config)
    return report


def main():
    if len(sys.argv)==3 and sys.argv[1] in ('--worker','--gate'):
        callback=worker if sys.argv[1]=='--worker' else gate
        return 0 if callback(json.loads(sys.argv[2])) else 1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    result=verify(parser.parse_args());print(json.dumps({'status':result['status'],'successful_cases':result.get('successful_cases'),'error':result.get('error')},allow_nan=False))
    return 0 if result['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
