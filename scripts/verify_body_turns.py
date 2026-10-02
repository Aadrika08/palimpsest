"""BGT-TURN-1: six fixed turn trials from one retained fit; no recalibration."""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import threading
import time
import uuid

from palimpsest import body_adaptation as adaptive, body_profile as body
from verify_body_adaptation import (read_json, storage, snapshot_path, match_reference,
                                    evaluator_row, cleanup_observed)
from verify_body_compensation import settled_response, paired_response
from verify_body_gains import collect_trial, write_json, FIT_BOUNDS
from verify_body_runtime import command, digest, audit_ticks
from verify_body_calibration import sample
from verify_task_phases import initial_ready
from verify_endurance import source_identity, descendants
from verify_tasks import file_hashes

MiB=1024**2
REFERENCE={'source_commit':'5f22c1c06edec7ab0ba27447e0c2360f6e09243d',
    'report_sha256':'231956442698655fc8f511018067a9515797b2baa7dd5e9f7d1a174374546121',
    'snapshot_sha256':'af42213e0bc0440906371a53fe23902b02c692e806c64b609621fed2feb63ca4',
    'samples_sha256':'8dcc254855a32bf41870fa4fb8660f6e96e4fbb3411077f816802985b4d4284c',
    'fit_sha256':'4d738e670b89cad1ca5db18dbb64d4465cc8f22663503d3c663fc6a6000a4428',
    'session_sha256':'2086d435f0bd40a5b85997ede4f7b8666ac042ecda8e135e34fba5ee239ba77b'}
TRIALS=[{'id':condition+'-'+direction,'condition':condition,'direction':direction,
          'left_gear_factor':factor,'action':[0.,sign*.2]}
        for direction,sign in (('left',1),('right',-1))
        for condition,factor in (('baseline',1.),('uncompensated',.8),('compensated',.8))]
PROTOCOL={'id':'BGT-TURN-1','version':1,'trials':TRIALS,'reference':REFERENCE,'identity':adaptive.IDENTITY,
    'seed':1,'start_pose':adaptive.PROTOCOL['start_pose'],'goal_xy':adaptive.PROTOCOL['goal_xy'],
    'ticks':120,'settling_ticks':20,'owners':6,'maximum_numeric_ticks':720,'snapshot_files':6,
    'snapshot_max_bytes':16*MiB,'recording_max_bytes':256*MiB,'output_max_bytes':2048*MiB,
    'min_free_bytes':1024*MiB,'result_max_bytes':64*MiB,'report_max_bytes':MiB,'log_max_bytes':MiB,
    'headroom_bytes':8*MiB,'child_timeout_seconds':180,'inner_timeout_seconds':1200,'outer_timeout_seconds':1260,
    'collection':'collect all six valid trials before metric acceptance; stop only infrastructure/invariant/contact failure',
    'comparison':'aligned100x2 wheel-rate RMSE, cumulative wrapped yaw and lane-Y deviation from same-direction baseline; strict improvement per metric per direction',
    'controls':'fixed nominal turns through existing converter/actual adaptive fitted path; no direct ctrl writes or truth feedback',
    'reference_contract':'existing native restore admission, unchanged accepted400 samples/fit; no historical recording replay or guard weakening',
    'pipeline':body.PROTOCOL['pipeline'],'contact_scope':body.PROTOCOL['contact_scope'],
    'scope':'one fixed fitted gear-.8 body/lane/seed; withheld opposite-wheel command regime, not new-body/task/general/physical qualification'}
PROTOCOL_SHA256=adaptive._sha(PROTOCOL)


def harness_hashes():
    return {name:digest(Path(__file__).with_name(name)) for name in ('verify_body_turns.py','verify_body_adaptation.py',
        'verify_body_runtime.py','verify_body_gains.py','verify_body_compensation.py','verify_body_calibration.py',
        'verify_task_phases.py','verify_tasks.py','verify_endurance.py')}


def load_reference(config):
    from palimpsest.snapshots import read_snapshot
    path=Path(config['calibration_report'])
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MiB or digest(path)!=REFERENCE['report_sha256']:
        raise ValueError('Exact bounded accepted calibration report required')
    report=read_json(path)
    snapshot=read_snapshot(snapshot_path(config['fitted_snapshot'],REFERENCE['snapshot_sha256']))
    state=snapshot['application']['body_state'];adaptive.validate_session(state,episode=4,episode_step=0)
    application=snapshot['application']
    if (report['status']!='passed' or report['source_unchanged'] is not True or report['assets_unchanged'] is not True or
            report['runtime_source']['commit']!=REFERENCE['source_commit'] or
            report['snapshots']['fitted']['sha256']!=REFERENCE['snapshot_sha256'] or
            application['schema_version']!=6 or application['scenario']!=adaptive.SCENARIO or application['controller']!='manual' or
            application['phase']!='paused' or application['total_tick']!=480 or application['manual_action']!=[0.,0.] or
            application['pending_commands'] or state['phase']!='fitted' or state['previous_angles_rad']!=[0.,0.] or state['time_s']!=0. or
            len(state['samples'])!=400 or state['samples_sha256']!=REFERENCE['samples_sha256'] or
            state['fit_sha256']!=REFERENCE['fit_sha256'] or adaptive._sha(state)!=REFERENCE['session_sha256'] or
            report['accepted_fit']['fit']!=state['fit'] or report['accepted_fit']['session_sha256']!=REFERENCE['session_sha256']):
        raise ValueError('Pinned fresh fitted native/session admission differs')
    return snapshot


def admission(observation):
    import numpy as np
    cameras=[observation[key] for key in ('cam_left','cam_right')]
    if any(a.dtype!=np.uint8 or a.shape!=(128,128,3) for a in cameras):
        raise ValueError('Turn gate requires actual uint8 128x128 cameras')
    per_tick=2*sum(a.nbytes for a in cameras)+body.MAX_TICK_BYTES+4096
    allowances={'numeric_bytes':720*per_tick,'snapshot_bytes':6*16*MiB,'result_bytes':6*64*MiB,
                'native_logs_bytes':16*MiB,'control_bytes':24*MiB,'staging_bytes':128*MiB,'headroom_bytes':8*MiB}
    total=sum(allowances.values());recording=120*per_tick+2*MiB
    if total>PROTOCOL['output_max_bytes'] or recording>PROTOCOL['recording_max_bytes']:
        raise ValueError('Frozen turn storage estimate exceeds unchanged quota')
    return {'aggregate_bytes':total,'per_recording_bytes':recording,'allowances':allowances}


def compare_turns(results):
    if set(results)!={trial['id'] for trial in TRIALS}:raise ValueError('Exact six turn trials required')
    prepared={}
    for trial in TRIALS:
        data=results[trial['id']];rows=data.get('rows',[])
        if (data.get('status')!='passed' or data.get('trial')!=trial or
                [row.get('tick') for row in rows]!=list(range(120)) or
                any(row.get('contact') is not False or row.get('coverage_passed') is not True or
                    row.get('fit_interval') is not (row['tick']>=20) or
                    not FIT_BOUNDS['dt_bounds_s'][0]<=row['dt_s']<=FIT_BOUNDS['dt_bounds_s'][1] for row in rows)):
            raise ValueError(trial['id']+': incomplete/rejected contact, cursor or settling interval')
        prepared[trial['id']]=settled_response(rows[20:],trial['id'])
    directions={}
    for direction in ('left','right'):
        baseline=prepared['baseline-'+direction]
        comparisons={condition:paired_response(baseline,prepared[condition+'-'+direction])
                     for condition in ('uncompensated','compensated')}
        improved={name:comparisons['compensated'][name]<comparisons['uncompensated'][name]
                  for name in ('wheel_rate_rmse','yaw_error','lateral_error')}
        directions[direction]={'accepted':all(improved.values()),'improved':improved,'comparisons':comparisons,
            'baseline':{'raw_yaw_rad':baseline['yaw_rad'],'raw_lateral_m':baseline['lateral_m']}}
    return {'accepted':all(value['accepted'] for value in directions.values()),'directions':directions}


def worker(config):
    import mujoco
    from palimpsest.engine import Engine
    from palimpsest.replay import _register_initial, _same_json
    from palimpsest.snapshots import _model_digest
    stage=Path(config['stage']);run=Path(config['run']);trial=config['trial'];budget=storage(config)
    result={'status':'failed','trial':trial,'run':str(run),'rows':[]};engine=None
    try:
        if source_identity(Path(config['repo']))!=config['runtime_source'] or harness_hashes()!=config['harness_sha256']:
            raise ValueError('Frozen runtime/harness changed before owner start')
        snapshot=load_reference(config)
        def ready(e):
            initial_ready(run,'ready');estimate=admission(e.observation)
            budget.check(estimate['aggregate_bytes'] if config['first_owner'] else estimate['per_recording_bytes']+16*MiB,path=run)
            return match_reference(e,snapshot)
        if trial['condition']!='compensated':
            return collect_trial(config,PROTOCOL,PROTOCOL_SHA256,harness=harness_hashes(),storage_budget=budget,
                result_max_bytes=PROTOCOL['result_max_bytes'],initial_guard=ready,record_body_arrays=True)
        if mujoco.get_mjcb_control() is not None:raise ValueError('Refusing existing global control callback')
        run.mkdir(exist_ok=False)
        engine=Engine.open(Path(config['repo']),Path(config['assets']),run/'recording',controller='manual',device='cpu',
            seed=1,scenario=adaptive.SCENARIO,texture='checker',run_id=run.name,max_bytes=256*MiB,storage_budget=budget)
        engine.restore_branch(snapshot)
        _same_json(snapshot['application']['body_state'],engine.body_state,'unchanged_fitted_reference')
        result.update(model_sha256=_model_digest(engine.env.model),reference=REFERENCE,
                      physical_calibration=__import__('palimpsest.task_profiles',fromlist=['body_calibration']).body_calibration(engine.env))
        engine.writer.manifest.update(turn_protocol=PROTOCOL,turn_trial=trial,turn_protocol_sha256=PROTOCOL_SHA256,
            turn_reference=REFERENCE,initial_world=engine.world())
        engine.writer.event('body_turn_protocol',protocol=PROTOCOL,trial=trial,reference=REFERENCE,harness_sha256=harness_hashes())
        _register_initial(engine,run,budget);result['matched_initial_state']=ready(engine)
        frozen=(engine.body_state['samples_sha256'],engine.body_state['fit_sha256'])
        command(engine,'turn-action','set_action',{'action':trial['action']})
        for tick in range(120):
            before=sample(engine.env);command(engine,f'turn-step-{tick}','step')
            result['rows'].append(evaluator_row(engine,tick,before))
            if engine.phase!='paused' or engine.body_state['phase']!='fitted' or frozen!=(engine.body_state['samples_sha256'],engine.body_state['fit_sha256']):
                raise ValueError('Turn evaluation terminated, rejected or changed immutable fitted samples/fit')
        if _model_digest(engine.env.model)!=result['model_sha256']:raise ValueError('Immutable fitted model changed')
        result.update(status='passed',fit_unchanged=True)
    except Exception as error:
        result.update(status='failed',error={'type':type(error).__name__,'message':str(error)[:1024]})
    finally:
        if engine is not None:
            try:
                result['final_state']=engine.public_state()
                result['failure_packet']=copy.deepcopy(getattr(engine.env,'_body_failure_packet',None))
            except Exception as error:result.update(status='failed',diagnostic_error=str(error)[:512])
            finally:
                try:engine.close();result['engine_closed']=True
                except Exception as error:result.update(status='failed',cleanup_error=str(error)[:512])
        result['callback_restored']=mujoco.get_mjcb_control() is None
        if not result['callback_restored']:result['status']='failed'
        if trial['condition']=='compensated' or not (stage/'result.json').exists():
            write_json(stage/'result.json',result,max_bytes=64*MiB,storage_budget=storage(config,control=True))
    return result['status']=='passed'


def bind_evaluator_rows(rows, ticks):
    """Bind offline metric inputs to their published numeric intervals exactly."""
    if len(rows)!=120 or len(ticks)!=120:raise ValueError('Exact evaluator/numeric coverage required')
    for row,raw in zip(rows,ticks):
        pairs=((row['before']['pose'],raw['pose'].tolist()),(row['after']['pose'],raw['next_pose'].tolist()),
            (row['before']['shaft_angles_rad'],raw['body_encoder_before'].tolist()),
            (row['after']['shaft_angles_rad'],raw['body_encoder_after'].tolist()),
            (row['increments_rad'],raw['body_encoder_increment'].tolist()),(row['dt_s'],float(raw['body_dt'])),
            (row['action'],raw['action'].tolist()),(row['control'],raw['control'].tolist()),
            (row['after']['time_s'],float(raw['simulation_time'])))
        if any(left!=right for left,right in pairs):raise ValueError('Evaluator differs from published numeric interval')


def owner_valid(trial,supervision,result,ticks):
    episode=4 if trial['condition']=='compensated' else 0
    if (supervision.get('status')!='completed' or supervision.get('returncode')!=0 or
            'error' in supervision or 'failure' in supervision or result.get('status')!='passed' or
            result.get('trial')!=trial or result.get('engine_closed') is not True or result.get('callback_restored') is not True or
            [(int(row['episode']),int(row['tick'])) for row in ticks]!=[(episode,tick) for tick in range(120)]):
        raise ValueError(trial['id']+': lifecycle/recording/coverage failed')


def gate(config):
    from palimpsest.evaluate import bounded_process
    from palimpsest.assets import verify_assets
    from palimpsest.records import iter_ticks
    root=Path(config['repo']);output=Path(config['output']);budget=storage(config);report=read_json(output/'report.json')
    results={};count=0
    try:
        snapshot=load_reference(config);accepted=snapshot['application']['body_state']
        report['assets_before']=verify_assets(root,Path(config['assets']))
        if not report['assets_before']['ok']:raise ValueError('Pinned assets unavailable')
        env={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','OMP_NUM_THREADS':'2','MPLBACKEND':'Agg'}
        for number,trial in enumerate(TRIALS):
            budget.check_count('runs',number);stage=output/trial['id'];run=stage/uuid.uuid4().hex
            item=report['trials'][trial['id']];item['status']='running'
            write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
            child={**config,'trial':trial,'stage':str(stage),'run':str(run),'first_owner':number==0,
                   'runtime_source':report['runtime_source'],'harness_sha256':report['harness_sha256']}
            payload=json.dumps(child)
            if len(payload.encode())>64*1024:raise ValueError('Bounded owner argv exceeded; no sample buffers in commands')
            supervision=bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',payload],stage,180,env,log_max_bytes=MiB,storage_budget=budget)
            item.update(status='failed-infrastructure',supervision=supervision)
            result=read_json(stage/'result.json',maximum=64*MiB)
            item.update(result_path=str(stage/'result.json'),result_sha256=digest(stage/'result.json'),
                        result={key:value for key,value in result.items() if key not in ('rows','failure_packet')})
            ticks=list(iter_ticks(run/'recording'));owner_valid(trial,supervision,result,ticks)
            manifest=read_json(run/'recording/manifest.json')
            if manifest['status']!='completed':raise ValueError('Valid turn recording did not finish normally')
            initial_ready(run,'ready')
            identity=adaptive.IDENTITY if trial['condition']=='compensated' else {'standalone':True,'protocol_sha256':PROTOCOL_SHA256}
            def plan(row):
                if row['body_nominal_action'].tolist()!=trial['action']:raise ValueError('Frozen nominal turn differs')
                if trial['condition']=='compensated':return adaptive.plan_action(accepted,trial['action'])
                control=body.effective_control(trial['action'])
                return {'nominal_control':control,'applied_action':trial['action'],'applied_control':control}
            item['raw_audit']=audit_ticks(ticks,manifest,identity=identity,planner=plan)
            bind_evaluator_rows(result['rows'],ticks)
            results[trial['id']]=result;count+=len(ticks)
            if count>720 or len(list(output.rglob('*.snp')))>6:raise ValueError('Frozen tick/snapshot count exceeded')
            item['status']='passed';report.update(numeric_ticks=count,owners_completed=len(results))
            write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
        calibrations=[result.get('physical_calibration') for result in results.values()]
        if any(value is None or value!=calibrations[0] for value in calibrations):
            raise ValueError('Physical wheel calibration differs across matched trials')
        report['physical_calibration']=calibrations[0]
        report['comparison']=compare_turns(results)  # Never reject metrics before all six valid owners finish.
        if len(list(output.rglob('*.snp')))!=6:raise ValueError('Exact six initial snapshots required')
        report.update(status='passed' if report['comparison']['accepted'] else 'failed-functional',protocol_status='completed',snapshot_files=6)
    except Exception as error:
        report.update(status='failed-infrastructure',protocol_status='incomplete',error={'type':type(error).__name__,'message':str(error)[:1024]},numeric_ticks=count)
    finally:
        try:
            load_reference(config);report['reference_unchanged']=True
            report['assets_after']=verify_assets(root,Path(config['assets']))
            if report.get('assets_before')!=report['assets_after']:raise ValueError('Pinned assets changed')
        except Exception as error:report.update(status='failed-infrastructure',input_error=str(error)[:512])
        write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
    return report['status']=='passed'


def supervision_matches(report,supervision):
    if 'error' in supervision or 'failure' in supervision:return False
    if report.get('status')=='passed':return supervision.get('status')=='completed' and supervision.get('returncode')==0
    return (report.get('status')=='failed-functional' and report.get('protocol_status')=='completed' and
        report.get('owners_completed')==6 and report.get('numeric_ticks')==720 and report.get('snapshot_files')==6 and
        report.get('comparison',{}).get('accepted') is False and supervision.get('status')=='failed' and supervision.get('returncode')==1 and
        all(report.get('trials',{}).get(trial['id'],{}).get('status')=='passed' for trial in TRIALS))


def verify(args):
    from dataclasses import asdict
    from palimpsest.storage import StorageBudget,StorageLimits
    from palimpsest.evaluate import bounded_process
    root=args.repo.resolve();assets=args.assets.resolve();output=args.output.resolve()
    if (assets.is_relative_to(output) or output.is_relative_to(assets) or
            any(Path(path).resolve().is_relative_to(output) for path in (args.calibration_report,args.fitted_snapshot))):
        raise ValueError('Managed output must not contain/overlap immutable inputs')
    output.mkdir(parents=True,exist_ok=False)
    limits=StorageLimits(max_bytes=2048*MiB,min_free_bytes=1024*MiB,max_runs=6,max_snapshots=1,max_exports=1)
    budget=StorageBudget((output,),limits,headroom_bytes=8*MiB)
    config={'repo':str(root),'assets':str(assets),'output':str(output),'calibration_report':str(args.calibration_report.resolve()),
            'fitted_snapshot':str(args.fitted_snapshot.resolve()),'storage':{'roots':[str(output)],'limits':asdict(limits),'headroom_bytes':8*MiB}}
    report={'status':'running','protocol':PROTOCOL,'protocol_sha256':PROTOCOL_SHA256,'runtime_source':source_identity(root),
            'harness_sha256':harness_hashes(),'numeric_ticks':0,'owners_completed':0,
            'trials':{trial['id']:{'status':'not_started','trial':trial} for trial in TRIALS}}
    known={};errors=[];stop=threading.Event()
    def sample_owned():
        try:
            while not stop.is_set():
                for row in descendants(os.getpid()):
                    if row['pid'] not in known and len(known)>=256:raise ValueError('Finite descendant inventory exceeds 256')
                    known[row['pid']]=row['start_ticks']
                stop.wait(.25)
        except Exception as error:errors.append(str(error)[:512]);stop.set()
    sampler=threading.Thread(target=sample_owned,daemon=True);started=time.monotonic()
    with budget.lock():
        write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True));sampler.start()
        try:
            env={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','OMP_NUM_THREADS':'2','MPLBACKEND':'Agg'}
            supervision=bounded_process([sys.executable,str(Path(__file__).resolve()),'--gate',json.dumps(config)],output/'inner-supervision',1200,env,log_max_bytes=MiB,storage_budget=budget)
            report=read_json(output/'report.json');report['inner_supervision']=supervision
            if not supervision_matches(report,supervision):report['status']='failed-infrastructure'
        except Exception as error:report.update(status='failed-infrastructure',error={'type':type(error).__name__,'message':str(error)[:1024]})
        finally:
            stop.set();sampler.join(timeout=2.)
            report['cleanup']={**cleanup_observed(dict(known)),'sampler_stopped':not sampler.is_alive(),'sample_errors':errors,
                'observed_owned_processes':[{'pid':pid,'start_ticks':start} for pid,start in sorted(known.items())],
                'scope':'finite .25s PID/start sampling, not universal transient-process proof'}
            report.update(wall_seconds=time.monotonic()-started,final_source=source_identity(root),final_harness=harness_hashes())
            if (report['cleanup']['forced_signals'] or report['cleanup']['survivors'] or errors or sampler.is_alive() or
                    report['runtime_source']!=report['final_source'] or report['harness_sha256']!=report['final_harness']):report['status']='failed-infrastructure'
            report['usage']=budget.usage();report['artifacts_sha256']={k:v for k,v in file_hashes(output).items() if k not in ('report.json','.palimpsest-storage.lock')}
            write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
    return report


def main():
    if len(sys.argv)==3 and sys.argv[1] in ('--worker','--gate'):
        return 0 if (worker if sys.argv[1]=='--worker' else gate)(json.loads(sys.argv[2])) else 1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    for option in ('assets','calibration-report','fitted-snapshot','output'):parser.add_argument('--'+option,type=Path,required=True)
    report=verify(parser.parse_args());print(json.dumps({'status':report['status'],'numeric_ticks':report.get('numeric_ticks'),'error':report.get('error')},allow_nan=False))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':raise SystemExit(main())
