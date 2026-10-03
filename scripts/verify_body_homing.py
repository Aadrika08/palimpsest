"""Four-owner fitted-body/encoder-homing development composition; no truth feedback."""
import argparse
import copy
import json
import os
from pathlib import Path
import sys
import time
import uuid

from palimpsest import body_homing as homing, body_adaptation as adaptive, body_profile as body
from verify_body_adaptation import read_json, storage, snapshot_path
from verify_body_turns import load_reference
from verify_body_runtime import digest, audit_ticks
from verify_body_gains import write_json
from verify_task_phases import initial_ready
from verify_tasks import cue_action, previous_bearing, evaluator_sample, evaluator_record, evaluate_motion, file_hashes
from verify_endurance import source_identity

MiB = 1024**2
OWNERS = ('source', 'native', 'actions', 'policy')
PROTOCOL = {'id': 'BGT-HOMING-COMPOSE-1', 'version': 1, 'scenario': homing.SCENARIO,
    'composition_identity': homing.IDENTITY, 'reference': homing.REFERENCE,
    'driver': 'unchanged verify_tasks v2; previous recorded effective bearing only; initial zero',
    'source_max_homing_ticks': 600, 'reset_ticks': 1, 'continuation_max_ticks': 4,
    'owners': 4, 'maximum_numeric_ticks': 1807, 'snapshot_files': 5,
    'snapshot_max_bytes': 16*MiB, 'recording_max_bytes': 256*MiB,
    'result_max_bytes': 64*MiB, 'report_max_bytes': MiB, 'log_max_bytes': MiB,
    'output_max_bytes': 2048*MiB, 'min_free_bytes': 1024*MiB, 'headroom_bytes': 8*MiB,
    'child_timeout_seconds': 180, 'inner_timeout_seconds': 780,
    'outer_timeout_seconds': 840, 'normal_admission_seconds': 830,
    'actual_home_limit_m': .25, 'snapshot_boundary': 'first paused published home-phase interval',
    'continuation': 'up to four actual successor commands; shorten only for legitimate task completion',
    'reset': 'save natural outcome; ordinary reset clears session/task/derivation; publish one fixed probe',
    'claim': 'one fixed fitted simulator development composition; no task-level compensation benefit, unseen-body or physical qualification'}
PROTOCOL_SHA256 = adaptive._sha(PROTOCOL)


def harness_hashes():
    return {name: digest(Path(__file__).with_name(name)) for name in
        ('verify_body_homing.py', 'verify_body_turns.py', 'verify_body_adaptation.py',
         'verify_body_runtime.py', 'verify_body_gains.py', 'verify_body_compensation.py',
         'verify_body_calibration.py', 'verify_task_phases.py', 'verify_tasks.py', 'verify_endurance.py')}


def admitted_inputs(config):
    # The existing file/fit/report admission precedes decoding-derived setup.
    snapshot = load_reference(config)
    report_path = Path(config['calibration_report'])
    shot_path = snapshot_path(config['fitted_snapshot'], homing.REFERENCE['snapshot_sha256'])
    report_hash, shot_hash = digest(report_path), digest(shot_path)
    report = read_json(report_path)
    derived = homing.derive_snapshot(snapshot, snapshot_sha256=shot_hash,
                                    report=report, report_sha256=report_hash)
    return snapshot, report, derived, {'report': report_hash, 'snapshot': shot_hash}


def admission(observation=None):
    if observation is not None:
        import numpy as np
        if any(observation[k].dtype != np.uint8 or observation[k].shape != (128,128,3)
               for k in ('cam_left', 'cam_right')):
            raise ValueError('Actual camera schema exceeds frozen admission')
    allowances = {'numeric': 1807*233472, 'snapshots': 5*16*MiB, 'results': 4*64*MiB,
                  'logs': 12*MiB, 'controls': 24*MiB, 'staging': 128*MiB, 'headroom': 8*MiB}
    if body.MAX_TICK_BYTES > 32768 or sum(allowances.values()) != 954560512:
        raise ValueError('Frozen numeric/storage allowance differs')
    return {'aggregate_bytes': sum(allowances.values()), 'allowances': allowances,
            'per_recording_bytes': 601*233472+2*MiB}


def command(engine, identifier, kind, payload=None):
    before = engine.total_tick
    message = {'id': identifier, 'kind': kind, 'expected_state': engine.phase,
               'expected_episode': engine.episode, 'expected_revision': engine.revision}
    if payload is not None: message['payload'] = payload
    if engine.submit(message)['status'] != 'queued': raise ValueError('Command not queued')
    engine.advance()
    if engine.submit(message)['status'] != 'applied' or engine.total_tick != before+(kind == 'step'):
        raise ValueError('Single-boundary command/receipt failed')


def completed(state):
    return (state['phase'] == 'terminated' and (state['last_outcome'] or {}).get('reason') == 'task_completed'
            and state['task']['phase'] == 'complete')


def capability(state):
    distance = (state['last_outcome'] or {}).get('evaluator_actual_home_distance_m')
    return completed(state) and type(distance) in (int, float) and 0 <= distance <= .25


def validate_window(items):
    if not 1 <= len(items) <= 4: raise ValueError('Missing actual home continuation window')
    final=items[-1]['state']
    natural_limit=final['phase']=='truncated' and (final['last_outcome'] or {}).get('reason')=='time_limit'
    if (any(x['state']['phase'] != 'paused' for x in items[:-1]) or
            final['phase']!='paused' and not completed(final) and not natural_limit or
            len(items)<4 and not completed(final)):
        raise ValueError('Short/early continuation is not legitimate completion')


def window_admission(items):
    if not items:return {'admissible':False,'reason':'source has no home successor window'}
    final=items[-1]['state']
    if (len(items)<4 and final['phase']=='truncated' and
            (final['last_outcome'] or {}).get('reason')=='time_limit' and
            all(x['state']['phase']=='paused' for x in items[:-1])):
        return {'admissible':False,'reason':'valid natural time limit before four home successors'}
    validate_window(items)
    return {'admissible':True,'reason':None}


def worker(config):
    from palimpsest.engine import Engine
    from palimpsest.replay import _register_initial, replay_run
    from palimpsest.snapshots import capture, save_snapshot, read_snapshot, restore, state_digest
    import mujoco
    stage, run = Path(config['stage']), Path(config['run'])
    mode = config['mode']; budget = storage(config); engine = None; rows = []; window = []
    result = {'status': 'failed', 'mode': mode, 'run': str(run)}
    try:
        if source_identity(Path(config['repo'])) != config['runtime_source'] or harness_hashes() != config['harness_sha256']:
            raise ValueError('Frozen source/harness changed')
        historical, fit_report, derived, input_hashes = admitted_inputs(config)
        result['input_hashes'] = input_hashes
        budget.check(admission()['aggregate_bytes'] if mode == 'source' else admission()['per_recording_bytes']+16*MiB,path=run)
        if mode in ('actions', 'policy'):
            run.mkdir(exist_ok=False)
            replay = replay_run(Path(config['source_run']), run, mode=mode,
                repo_root=Path(config['repo']), asset_root=Path(config['assets']), storage_budget=budget,
                recording_max_bytes=PROTOCOL['recording_max_bytes'],
                progress=lambda status,state=None: initial_ready(run,status,state))
            result.update(status=replay['status'], compared_ticks=replay['compared_ticks'],
                          replay_report=str(run/'replay-report.json'))
        else:
            run.mkdir(exist_ok=False)
            engine = Engine.open(Path(config['repo']),Path(config['assets']),run/'recording',
                controller='manual',device='cpu',seed=1,scenario=homing.SCENARIO,texture='checker',
                run_id=run.name,max_bytes=PROTOCOL['recording_max_bytes'],storage_budget=budget)
            if mode == 'source':
                reference = engine.restore_homing_derivation(historical,
                    snapshot_sha256=input_hashes['snapshot'], report=fit_report, report_sha256=input_hashes['report'])
                if reference != homing.normalized_reference(derived): raise ValueError('Actual initial derivation mismatch')
                result['normalized_derivation_sha256'] = reference
            else:
                engine.restore_branch(read_snapshot(snapshot_path(config['snapshot'],config['snapshot_sha256'])))
            admission(engine.observation)
            engine.writer.manifest.update(body_homing_gate=PROTOCOL,body_homing_gate_sha256=PROTOCOL_SHA256)
            engine.writer.event('body_homing_gate',protocol=PROTOCOL,protocol_sha256=PROTOCOL_SHA256)
            _register_initial(engine,run,budget); initial_ready(run,'ready')
            origin = evaluator_sample(engine)['pose']
            if mode == 'source':
                for tick in range(600):
                    action = cue_action(previous_bearing(engine.last_transition),driver='v2')
                    before = evaluator_sample(engine)
                    command(engine,f'homing-action-{tick}','set_action',{'action':action})
                    command(engine,f'homing-step-{tick}','step')
                    rows.append(evaluator_record(engine,before,evaluator_sample(engine),origin,action))
                    if 'snapshot_sha256' in result and len(window) < 4:
                        window.append({'tick':tick,'action':action,'task':copy.deepcopy(engine.task_state),
                            'body_sha256':adaptive._sha(engine.body_state),'composition':copy.deepcopy(engine.composition),
                            'state':engine.public_state()})
                    if engine.phase != 'paused': break
                    if 'snapshot_sha256' not in result and engine.task_state['phase'] == 'home':
                        engine.writer.flush()
                        shot=capture(engine.env,engine.observation,application=engine.application_state())
                        save_snapshot(shot,stage/'progress.snp',storage_budget=budget)
                        snapshot_path(stage/'progress.snp');result['snapshot_sha256']=digest(stage/'progress.snp')
                state=engine.public_state()
                if state['phase'] not in ('terminated','truncated'): raise ValueError('Source lacks natural ending at frozen cap')
                result.update(homing_state=state,completion_passed=capability(state),homing_ticks=len(rows),
                    motion=evaluate_motion(rows,engine.task_state['odometry']['calibration']),continuation_ticks=len(window))
                result['window_admission']=window_admission(window)
                command(engine,'homing-reset','reset')
                if (engine.task_state is not None or engine.body_state['samples'] or
                        engine.composition != homing.context() or engine.manual_action.tolist() != [0.,0.]):
                    raise ValueError('Ordinary Reset did not clear composed state')
                command(engine,'homing-reset-probe','step')
                result.update(reset_cleared=True,reset_state=engine.public_state(),status='passed')
            else:
                expected=read_json(Path(config['source_stage'])/'continuation.json',maximum=64*MiB)
                validate_window(expected)
                guards=[]
                for field in ('identity','task'):
                    shot=capture(engine.env,engine.observation,application=engine.application_state())
                    before=state_digest(shot);bad=copy.deepcopy(shot)
                    if field=='identity':bad['application']['composition']['identity']['profile_sha256']='f'*64
                    else:bad['application']['task_state']['odometry']['wheel_angles_rad'][0]+=.1
                    try:restore(bad,engine.env)
                    except ValueError as error:
                        if state_digest(capture(engine.env,engine.observation,application=engine.application_state()))!=before:
                            raise ValueError('Malformed restore mutated destination') from error
                        guards.append({'field':field,'rejected':True,'unchanged':True,'reason':str(error)[:512]})
                    else:raise ValueError('Malformed composed restore admitted')
                for item in expected:
                    if engine.episode_step!=item['tick']:raise ValueError('Native continuation cursor differs')
                    command(engine,f"homing-action-{item['tick']}",'set_action',{'action':item['action']})
                    command(engine,f"homing-step-{item['tick']}",'step')
                    if (engine.task_state!=item['task'] or adaptive._sha(engine.body_state)!=item['body_sha256'] or
                            engine.composition!=item['composition']):raise ValueError('Native component continuation differs')
                result.update(status='passed',continuation_ticks=len(expected),restore_guards=guards)
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
        payloads=(('evaluator.json',rows),('continuation.json',window),('result.json',result))
        if sum(len((json.dumps(value,indent=2,allow_nan=False)+'\n').encode()) for _,value in payloads)>64*MiB:
            raise ValueError('Combined owner JSON result allowance exceeded')
        for name,value in payloads:
            write_json(stage/name,value,max_bytes=64*MiB,storage_budget=storage(config,control=True))
    return result['status']=='passed'


def verify(args):
    from dataclasses import asdict
    from palimpsest.assets import verify_assets
    from palimpsest.evaluate import bounded_process
    from palimpsest.records import iter_ticks
    from palimpsest.replay import _same_tick
    from palimpsest.storage import StorageBudget,StorageLimits
    started=time.monotonic();root=args.repo.resolve();assets=args.assets.resolve();output=args.output.resolve()
    inputs=[args.calibration_report.resolve(),args.fitted_snapshot.resolve()]
    if assets.is_relative_to(output) or output.is_relative_to(assets) or any(p.is_relative_to(output) or output.is_relative_to(p.parent) for p in inputs):
        raise ValueError('Managed output overlaps immutable inputs')
    output.mkdir(parents=True,exist_ok=False)
    limits=StorageLimits(max_bytes=2048*MiB,min_free_bytes=1024*MiB,max_runs=4,max_snapshots=1,max_exports=1)
    budget=StorageBudget((output,),limits,headroom_bytes=8*MiB)
    config={'repo':str(root),'assets':str(assets),'output':str(output),'calibration_report':str(inputs[0]),
        'fitted_snapshot':str(inputs[1]),'storage':{'roots':[str(output)],'limits':asdict(limits),'headroom_bytes':8*MiB},
        'runtime_source':source_identity(root),'harness_sha256':harness_hashes()}
    report={'status':'failed-infrastructure','protocol':PROTOCOL,'protocol_sha256':PROTOCOL_SHA256,
        'runtime_source':config['runtime_source'],'harness_sha256':config['harness_sha256'],
        'owners':{mode:{'status':'not_started'} for mode in OWNERS},'numeric_ticks':0}
    runs={};results={};ticks={}
    with budget.lock():
        try:
            admitted_inputs(config);report['assets_before']=verify_assets(root,assets)
            if not report['assets_before']['ok']:raise ValueError('Required assets absent')
            budget.check(admission()['aggregate_bytes'],path=output)
            env={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','OMP_NUM_THREADS':'2','MPLBACKEND':'Agg'}
            source_hashes=None
            for mode in OWNERS:
                if time.monotonic()-started>=780:raise TimeoutError('Whole inner gate deadline exceeded')
                if source_hashes is not None and file_hashes(runs['source'])!=source_hashes:
                    raise ValueError('Immutable source recording changed')
                if mode=='native' and not results['source']['window_admission']['admissible']:
                    report['owners'][mode]['reason']=results['source']['window_admission']['reason'];continue
                stage=output/mode;run=stage/uuid.uuid4().hex;runs[mode]=run
                child={**config,'mode':mode,'stage':str(stage),'run':str(run)}
                if mode!='source':child.update(source_run=str(runs['source']),source_stage=str(output/'source'))
                if mode=='native':child.update(snapshot=str(output/'source/progress.snp'),snapshot_sha256=results['source']['snapshot_sha256'])
                item=report['owners'][mode];item.update(status='running',run=str(run))
                write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
                payload=json.dumps(child,allow_nan=False)
                if len(payload.encode())>64*1024:raise ValueError('Bounded worker argv exceeded')
                remaining=780-(time.monotonic()-started)
                supervision=bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',payload],
                    stage,min(180,remaining),env,log_max_bytes=MiB,storage_budget=budget)
                item.update(status='failed-infrastructure',supervision=supervision)
                result=read_json(stage/'result.json',maximum=64*MiB);results[mode]=result
                item.update(result_path=str(stage/'result.json'),result_sha256=digest(stage/'result.json'))
                if (supervision.get('status')!='completed' or supervision.get('returncode')!=0 or
                        'failure' in supervision or 'error' in supervision or result['status']!='passed' or
                        not result['callback_restored'] or mode in ('source','native') and not result.get('engine_closed')):
                    raise ValueError(mode+': owner/invariant/lifecycle failure')
                ticks[mode]=list(iter_ticks(run/'recording'));initial_ready(run,'ready')
                if mode=='source':source_hashes=file_hashes(run)
                maximum=4 if mode=='native' else 601
                if not 0<len(ticks[mode])<=maximum:raise ValueError('Owner interval ceiling exceeded')
                report['numeric_ticks']+=len(ticks[mode]);item.update(status='passed',numeric_ticks=len(ticks[mode]))
                state=read_json(run/'recording/manifest.json')
                fitted=admitted_inputs(config)[0]['application']['body_state']
                def planner(row):
                    if int(row['episode'])==4:return adaptive.plan_action(fitted,row['body_nominal_action'].tolist())
                    if int(row['episode'])!=5 or int(row['tick'])!=0:raise ValueError('Unexpected reset probe cursor')
                    nominal=adaptive.probe_action(adaptive.initial_session(episode=5))
                    if row['body_nominal_action'].tolist()!=nominal:raise ValueError('Reset fixed probe differs')
                    control=body.effective_control(nominal)
                    return {'nominal_control':control,'applied_action':nominal,'applied_control':control}
                item['raw_audit']=audit_ticks(ticks[mode],state,identity=adaptive.IDENTITY,planner=planner)
                if mode=='native':
                    expected=read_json(output/'source/continuation.json',maximum=64*MiB)
                    by_tick={(int(r['episode']),int(r['tick'])):r for r in ticks['source']}
                    for spec,row in zip(expected,ticks[mode]):_same_tick(by_tick[(4,spec['tick'])],row,'policy',spec['tick'])
                    if len(expected)!=len(ticks[mode]):raise ValueError('Native row count differs')
                if mode in ('actions','policy') and len(ticks[mode])!=len(ticks['source']):raise ValueError('Replay coverage differs')
                if report['numeric_ticks']>1807 or len(list(output.rglob('*.snp')))>5:raise ValueError('Global interval/SNP ceiling exceeded')
            if file_hashes(runs['source'])!=source_hashes:raise ValueError('Immutable source recording changed')
            report['source_unchanged']=True
            functional=results['source']['completion_passed'] and report['owners']['native']['status']=='passed'
            shots=list(output.rglob('*.snp'))
            for shot in shots:snapshot_path(shot)
            if functional and len(shots)!=5:raise ValueError('Exact positive SNP coverage differs')
            report.update(status='passed' if functional else 'failed-functional',protocol_status='completed',snapshot_files=len(shots),
                actual_home=results['source']['homing_state']['last_outcome'],source_result=str(output/'source/result.json'))
        except Exception as error:
            report.update(status='failed-infrastructure',error={'type':type(error).__name__,'message':str(error)[:1024]})
        finally:
            report.update(final_source=source_identity(root),final_harness=harness_hashes(),wall_seconds=time.monotonic()-started)
            report['assets_after']=verify_assets(root,assets)
            if (report['final_source']!=config['runtime_source'] or report['final_harness']!=config['harness_sha256'] or
                    report['assets_after']!=report.get('assets_before') or report['wall_seconds']>=780):report['status']='failed-infrastructure'
            try:report['historical_inputs_at_end']=admitted_inputs(config)[3]
            except Exception as error:report.update(status='failed-infrastructure',historical_input_error=str(error)[:512])
            report['usage']=budget.usage()
            report['artifacts_sha256']={k:v for k,v in file_hashes(output).items() if k not in ('report.json','.palimpsest-storage.lock')}
            write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
    if time.monotonic()-started>=780:report['status']='failed-infrastructure';write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
    return report


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker':return 0 if worker(json.loads(sys.argv[2])) else 1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    for option in ('assets','calibration-report','fitted-snapshot','output'):parser.add_argument('--'+option,type=Path,required=True)
    report=verify(parser.parse_args());print(json.dumps({'status':report['status'],'numeric_ticks':report['numeric_ticks'],'error':report.get('error')},allow_nan=False))
    return 0 if report['status']=='passed' else 1

if __name__=='__main__':raise SystemExit(main())
