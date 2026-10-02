"""Bounded four-owner loaded-calibration continuation/replay development gate."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import threading
import time
import uuid

from verify_tasks import command as paused_command, file_hashes
from verify_body_gains import write_json as diagnostic_json
from verify_endurance import source_identity, descendants, process
from palimpsest import body_profile as body

PROTOCOL = {'version':1, 'scenario':body.SCENARIO, 'seed':1, 'controller':'manual', 'device':'cpu',
    'profile_identity':body.profile_identity(), 'warmup_ticks':24, 'continuation_ticks':4, 'reset_ticks':8,
    'source_ticks':36, 'forward_nominal':[.3,0.], 'reverse_nominal':[-.3,0.],
    'warmup':'run1 + pause + 23steps; capture at paused24',
    'continuation':'run1 + pause + 3steps; identical IDs after native restore',
    'reset':'seed1, zero nominal intent/fresh cursor, eight fixed reverse steps',
    'owners':['source','restored','actions','policy'], 'child_timeout_seconds':180,
    'recording_max_bytes':64*1024**2, 'output_max_bytes':1024**3, 'min_free_bytes':1024**3,
    'report_max_bytes':1024**2, 'result_max_bytes':1024**2, 'log_max_bytes':1024**2,
    'storage_headroom_bytes':8*1024**2, 'float_atol':1e-6, 'float_rtol':1e-6,
    'cameras_and_integers':'exact', 'truth_feedback':False,
    'scope':'one loaded-calibration simulator execution/continuation/replay development fixture; no online fit or task/physical qualification'}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def harness_hashes():
    return {name:digest(Path(__file__).with_name(name)) for name in
            ('verify_body_runtime.py','verify_tasks.py','verify_body_gains.py','verify_endurance.py')}


def write_json(path, value, budget):
    diagnostic_json(path, value, max_bytes=PROTOCOL['report_max_bytes'], storage_budget=budget)


def read_json(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(PROTOCOL['result_max_bytes']+1)
    if len(raw) > PROTOCOL['result_max_bytes']:
        raise ValueError('Verifier result exceeds read bound')
    return json.loads(raw)


def command(engine, identifier, kind, payload=None):
    if kind not in ('run','pause'):
        return paused_command(engine, identifier, kind, payload)
    before = engine.total_tick
    message = {'id':identifier, 'kind':kind, 'expected_state':engine.phase,
               'expected_episode':engine.episode, 'expected_revision':engine.revision}
    if engine.submit(message)['status'] != 'queued':
        raise ValueError('Run/pause command was not queued')
    engine.advance()
    receipt = engine.submit(message)
    if receipt['status'] != 'applied' or engine.total_tick != before+(kind=='run'):
        raise ValueError('Run/pause receipt or exact tick accounting failed')


def continuation(engine):
    states = []
    command(engine, 'continuation-run', 'run')
    states.append(copy.deepcopy(engine.body_state))
    command(engine, 'continuation-pause', 'pause')
    for index in range(1,4):
        command(engine, f'continuation-step-{index}', 'step')
        states.append(copy.deepcopy(engine.body_state))
    return states


def worker(config):
    import mujoco
    from palimpsest.engine import Engine
    from palimpsest.replay import _register_initial, replay_run, _same_json
    from palimpsest.snapshots import capture, save_snapshot, read_snapshot, state_digest
    from palimpsest.storage import StorageBudget, StorageLimits
    from palimpsest.snapshots import _model_digest
    storage = config['storage']
    budget = StorageBudget(tuple(Path(p) for p in storage['roots']), StorageLimits(**storage['limits']),
                           headroom_bytes=storage['headroom_bytes'])
    stage, run = Path(config['stage']), Path(config['run'])
    result = {'status':'running', 'mode':config['mode'], 'run':str(run), 'profile_identity':body.profile_identity()}
    engine = None
    try:
        run.mkdir(exist_ok=False)
        if config['mode'] in ('actions','policy'):
            report = replay_run(Path(config['source']), run, mode=config['mode'],
                repo_root=Path(config['repo']), asset_root=Path(config['assets']), storage_budget=budget)
            result.update(status=report['status'], compared_ticks=report['compared_ticks'],
                          replay_report_sha256=digest(run/'replay-report.json'), engine_closed=True,
                          callback_restored=mujoco.get_mjcb_control() is None)
            if result['status'] != 'passed' or result['compared_ticks'] != 36 or not result['callback_restored']:
                raise ValueError('Replay did not pass exact36tick/cleanup contract')
        else:
            engine = Engine.open(Path(config['repo']), Path(config['assets']), run/'recording',
                controller='manual', device='cpu', seed=1, scenario=body.SCENARIO, texture='checker',
                run_id=run.name, max_bytes=PROTOCOL['recording_max_bytes'], storage_budget=budget)
            result['model_sha256'] = _model_digest(engine.env.model)
            if result['model_sha256'] != body.ARTIFACT['model_sha256']:
                raise ValueError('Actual runtime model differs from accepted calibration')
            engine.writer.event('body_verifier_protocol', protocol=PROTOCOL, harness_sha256=harness_hashes())
            if config['mode']=='source':
                _register_initial(engine, run, budget)
                command(engine, 'forward', 'set_action', {'action':PROTOCOL['forward_nominal']})
                command(engine, 'warm-run', 'run')
                command(engine, 'warm-pause', 'pause')
                for index in range(1,24):
                    command(engine, f'warm-step-{index}', 'step')
                if engine.total_tick != 24 or engine.phase != 'paused':
                    raise ValueError('Snapshot boundary differs from declared24ticks')
                snapshot = capture(engine.env, engine.observation, application=engine.application_state())
                save_snapshot(snapshot, stage/'progress.snp', storage_budget=budget)
                result['snapshot_sha256'] = digest(stage/'progress.snp')
                result['snapshot_body_state'] = copy.deepcopy(engine.body_state)
                states = continuation(engine)
                write_json(stage/'continuation-states.json', states, budget)
                command(engine, 'reset', 'reset', {'seed':1})
                if (engine.body_state['episode_id']!='episode-1' or engine.body_state['last_tick'] is not None or
                        engine.manual_action.tolist()!=[0.,0.] or engine.total_tick!=28 or
                        _model_digest(engine.env.model)!=result['model_sha256']):
                    raise ValueError('Reset did not preserve fixed model/fit with fresh episodic intent')
                result['reset_body_state'] = copy.deepcopy(engine.body_state)
                command(engine, 'reverse', 'set_action', {'action':PROTOCOL['reverse_nominal']})
                for index in range(8):
                    command(engine, f'reverse-step-{index}', 'step')
                command(engine, 'clear', 'set_action', {'action':[0.,0.]})
                if engine.total_tick != 36 or engine.episode_step != 8 or engine.phase != 'paused':
                    raise ValueError('Source exact36tick protocol failed')
            else:
                if digest(config['snapshot']) != config['snapshot_sha256']:
                    raise ValueError('Immutable progress snapshot SHA differs')
                snapshot = read_snapshot(Path(config['snapshot']))
                rejected = []
                before = capture(engine.env, engine.observation, application=engine.application_state())
                before_hash = state_digest(before)
                addresses = (engine.env.model._address, engine.env.data._address)
                for kind in ('typed_encoder','native_encoder_mismatch'):
                    malformed = copy.deepcopy(snapshot)
                    angles = malformed['application']['body_state']['previous_angles_rad']
                    angles[0] = True if kind=='typed_encoder' else angles[0]+.1
                    try:
                        engine.restore_branch(malformed)
                    except ValueError as error:
                        after = capture(engine.env, engine.observation, application=engine.application_state())
                        if (state_digest(after)!=before_hash or
                                (engine.env.model._address,engine.env.data._address)!=addresses):
                            raise ValueError('Malformed body restore mutated fresh destination') from error
                        rejected.append({'case':kind, 'rejected_before_mutation':True,
                                         'reason':str(error)[:256], 'state_sha256':before_hash})
                    else:
                        raise ValueError('Malformed body snapshot was accepted')
                result['malformed_restore'] = rejected
                engine.restore_branch(snapshot)
                _same_json(snapshot['application']['body_state'],engine.body_state,'restored_body')
                _register_initial(engine, run, budget)
                states = continuation(engine)
                _same_json(read_json(Path(config['continuation'])),states,'continuation_body')
                write_json(stage/'continuation-states.json',states,budget)
                if engine.total_tick!=28 or engine.episode_step!=28 or engine.phase!='paused':
                    raise ValueError('Restored continuation cursor differs')
            result.update(status='passed', final_state=engine.public_state(), continuation_ticks=4)
    except Exception as error:
        result.update(status='failed', error={'type':type(error).__name__,'message':str(error)[:1024]})
    finally:
        if engine is not None:
            try:
                result.setdefault('final_state',engine.public_state())
                engine.close()
                result['engine_closed'] = True
            except Exception as error:
                result.update(status='failed', cleanup_error={'type':type(error).__name__,'message':str(error)[:1024]})
        result['callback_restored'] = mujoco.get_mjcb_control() is None
        if not result['callback_restored']:
            result['status']='failed'
        write_json(stage/'result.json', result, budget)
    return result['status']=='passed'


def audit_ticks(ticks, manifest):
    """Recheck every numeric contact/encoder slot; never infer unrecorded contact."""
    import numpy as np
    if manifest.get('body_profile_identity')!=body.profile_identity():
        raise ValueError('Recorded body identity differs')
    geometries = {item['geom_id']:item for item in manifest['body_contact_ownership']['geometries']}
    stages = pairs = 0
    previous = None
    for row in ticks:
        if not body.TICK_FIELDS <= row.keys():
            raise ValueError('Missing raw body fields')
        plan = body.plan_action(row['body_nominal_action'])
        if (not np.array_equal(row['action'],np.array(plan['applied_action'],np.float64)) or
                not np.array_equal(row['control'],np.array(plan['applied_control'],np.float64)) or
                not np.array_equal(row['body_nominal_control'],np.array(plan['nominal_control'],np.float32))):
            raise ValueError('Recorded nominal/effective control plan differs')
        shapes = {'body_contact_ids':((11,128,2),np.int16), 'body_contact_distances':((11,128),np.float64),
                  'body_contact_classes':((11,128),np.uint8), 'body_contact_counts':((11,),np.int16),
                  'body_contact_times':((11,),np.float64), 'body_stage_controls':((10,2),np.float64),
                  'body_encoder_before':((2,),np.float64),'body_encoder_after':((2,),np.float64),
                  'body_encoder_increment':((2,),np.float64),'body_nominal_action':((2,),np.float64),
                  'body_nominal_control':((2,),np.float32),'body_dt':((),np.float64),
                  'body_end_data_time':((),np.float64),'action':((2,),np.float64),'control':((2,),np.float64)}
        for key,(shape,dtype) in shapes.items():
            if row[key].shape!=shape or row[key].dtype!=dtype or not np.isfinite(row[key]).all():
                raise ValueError('Raw contact shape/dtype/nonfinite mismatch: '+key)
        counts=row['body_contact_counts']; ids=row['body_contact_ids']; distances=row['body_contact_distances']; classes=row['body_contact_classes']
        if np.any(counts<0) or np.any(counts>128):
            raise ValueError('Raw contact count overflow')
        for index,count in enumerate(counts):
            if any(np.any(array[index,int(count):]!=0) for array in (ids,distances,classes)):
                raise ValueError('Unused contact slots are not zero')
            for column in range(int(count)):
                left,right = [geometries.get(int(gid)) for gid in ids[index,column]]
                if left is None or right is None:
                    raise ValueError('Unknown recorded contact geometry')
                names={left['name'],right['name']}
                support='floor' in names and bool(names.intersection(body.GROUND_SUPPORT))
                incident=left['owner']=='robot' or right['owner']=='robot'
                expected=2 if support else 3 if incident else 1
                if classes[index,column]!=expected or expected==3:
                    raise ValueError('Unexpected/misclassified robot contact')
            pairs+=int(count)
        if counts[9]!=counts[10] or any(not np.array_equal(array[9],array[10]) for array in (ids,distances,classes)):
            raise ValueError('Final contact cache differs from last pre-integration stage')
        timestamp=float(row['simulation_time']); dt=float(row['body_dt'])
        expected=[timestamp-.02+i*.002 for i in range(10)]+[timestamp-.002]
        if (not np.allclose(row['body_contact_times'],expected,atol=1e-9,rtol=0.) or
                not np.array_equal(row['body_stage_controls'],np.tile(row['control'],(10,1))) or
                float(row['body_end_data_time'])!=timestamp or not math.isclose(dt,.02,abs_tol=1e-9,rel_tol=0.)):
            raise ValueError('Raw stage/control/time coverage differs')
        if (not np.array_equal(row['body_encoder_after']-row['body_encoder_before'],row['body_encoder_increment']) or
                not np.isfinite(row['body_encoder_increment']).all() or np.any(np.abs(row['body_encoder_increment']/dt)>100.)):
            raise ValueError('Raw encoder increment/rate differs')
        if previous is not None and row['episode']==previous['episode'] and not np.array_equal(row['body_encoder_before'],previous['body_encoder_after']):
            raise ValueError('Raw shaft record continuity differs')
        previous=row; stages+=10
    return {'ticks':len(ticks),'pre_control_stages':stages,'end_caches':len(ticks),'recorded_pairs_including_end_cache':pairs,
            'all_raw_slots_checked':True,'scope':'discrete contact caches only; no continuous collision claim'}


def verify(args):
    from palimpsest.storage import StorageBudget, StorageLimits
    from palimpsest.evaluate import bounded_process
    from palimpsest.assets import verify_assets
    from palimpsest.records import iter_ticks
    from palimpsest.replay import _same_tick, _same_json
    root,assets,output=args.repo.resolve(),args.assets.resolve(),args.output.resolve()
    if assets.is_relative_to(output) or output.is_relative_to(assets):
        raise ValueError('Assets must be outside managed output')
    output.mkdir(parents=True,exist_ok=False)
    limits=StorageLimits(max_bytes=PROTOCOL['output_max_bytes'],min_free_bytes=PROTOCOL['min_free_bytes'],max_runs=4,max_snapshots=2,max_exports=1)
    budget=StorageBudget((output,),limits,headroom_bytes=PROTOCOL['storage_headroom_bytes'])
    storage={'roots':[str(output)],'limits':limits.__dict__,'headroom_bytes':budget.headroom_bytes}
    report={'version':1,'status':'running','protocol':PROTOCOL,'runtime_source':source_identity(root),
            'harness_sha256':harness_hashes(),'workers':{mode:{'status':'pending'} for mode in PROTOCOL['owners']}}
    started=time.monotonic(); known={}; stop=threading.Event(); sample_errors=[]; sample_lock=threading.Lock()
    def sample():
        try:
            while not stop.is_set():
                rows=descendants(os.getpid())
                with sample_lock:
                    for row in rows:
                        if len(known)>=128 and row['pid'] not in known:
                            raise RuntimeError('Owned process sample exceeds bound')
                        known[row['pid']]=row['start_ticks']
                stop.wait(.25)
        except Exception as error:
            sample_errors.append({'type':type(error).__name__,'message':str(error)[:512]})
            stop.set()
    sampler=threading.Thread(target=sample,daemon=True)
    with budget.lock():
        sampler.start()
        try:
            report['assets']=verify_assets(root,assets)
            if not report['assets']['ok']:
                raise ValueError('Pinned cached assets failed verification')
            environment={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','MPLBACKEND':'Agg','OMP_NUM_THREADS':'2'}
            source_run=output/'source'/uuid.uuid4().hex
            write_json(output/'report.json',report,budget)
            for number,mode in enumerate(PROTOCOL['owners']):
                budget.check_count('runs',number)
                stage=output/mode
                config={'mode':mode,'stage':str(stage),'run':str(source_run if mode=='source' else stage/uuid.uuid4().hex),
                        'repo':str(root),'assets':str(assets),'storage':storage,'source':str(source_run),
                        'snapshot':str(output/'source/progress.snp'),
                        'snapshot_sha256':report['workers']['source'].get('result',{}).get('snapshot_sha256'),'continuation':str(output/'source/continuation-states.json')}
                supervision=bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',json.dumps(config)],
                    stage,PROTOCOL['child_timeout_seconds'],environment,log_max_bytes=PROTOCOL['log_max_bytes'],storage_budget=budget)
                item=report['workers'][mode]={'status':'failed','supervision':supervision}
                result_path=stage/'result.json'
                if result_path.exists():
                    item.update(result=read_json(result_path),result_sha256=digest(result_path))
                result=item.get('result',{})
                if (supervision['status']!='completed' or supervision['returncode']!=0 or result.get('status')!='passed' or
                        result.get('engine_closed') is not True or result.get('callback_restored') is not True):
                    raise ValueError(mode+' failed; inspect retained result/supervisor/native logs')
                run=Path(result['run']); manifest=read_json(run/'recording/manifest.json')
                if manifest['status']!='completed':
                    raise ValueError(mode+' recording did not finish normally')
                rows=list(iter_ticks(run/'recording'))
                expected=[(0,tick) for tick in range(24,28)] if mode=='restored' else [(0,tick) for tick in range(28)]+[(1,tick) for tick in range(8)]
                if [(r['episode'],r['tick']) for r in rows]!=expected:
                    raise ValueError(mode+' record coverage differs from exact protocol')
                item.update(status='passed',raw_audit=audit_ticks(rows,manifest))
                if sample_errors:
                    raise ValueError('Owned-process sampling failed; inspect final cleanup evidence')
                if mode=='source':
                    immutable=file_hashes(source_run)
                    left=[row for row in rows if row['episode']==0 and 24<=row['tick']<28]
                elif mode=='restored':
                    for a,b in zip(left,rows):
                        _same_tick(a,b,'policy',int(b['tick']))
                    _same_json(read_json(output/'source/continuation-states.json'),read_json(stage/'continuation-states.json'),'body_state')
                    report['native_continuation']={'status':'passed','ticks':4,'body_state':'matched','raw_arrays':'matched',
                        'float_atol':1e-6,'float_rtol':1e-6,'cameras_and_integers':'exact'}
                if mode!='source' and file_hashes(source_run)!=immutable:
                    raise ValueError('Immutable source changed after restore/replay')
                write_json(output/'report.json',report,budget)
            report['status']='passed'
        except Exception as error:
            report.update(status='failed',error={'type':type(error).__name__,'message':str(error)[:1024]})
        finally:
            stop.set();sampler.join(timeout=2.)
            with sample_lock:
                observed=dict(known)
            survivors=[row for pid,start in observed.items() if (row:=process(pid)) and row['start_ticks']==start]
            report['cleanup']={'observed_owned_processes':[{'pid':pid,'start_ticks':start} for pid,start in sorted(observed.items())],
                'survivors':survivors,'sampler_stopped':not sampler.is_alive(),'sample_errors':sample_errors,
                'scope':'finite .25s descendant sampling plus final PID/start-time check; no claim to observe every transient process; no server/listener created; existing bounded_process sends TERM/KILL to its owned groups after leader exit'}
            report.update(wall_seconds=time.monotonic()-started,runtime_source_at_end=source_identity(root),harness_sha256_at_end=harness_hashes())
            report['source_unchanged']=report['runtime_source']==report['runtime_source_at_end'] and report['harness_sha256']==report['harness_sha256_at_end']
            try:
                report['assets_at_end']=verify_assets(root,assets)
                report['assets_unchanged']=report.get('assets')==report['assets_at_end'] and report['assets_at_end']['ok']
                snapshot=output/'source/progress.snp'
                source_result=report['workers']['source'].get('result',{})
                report['source_progress_snapshot_unchanged']=snapshot.is_file() and digest(snapshot)==source_result.get('snapshot_sha256')
                report['output_usage']=budget.usage()
                report['artifacts_sha256']={name:value for name,value in file_hashes(output).items() if name not in ('report.json','.palimpsest-storage.lock')}
            except Exception as error:
                report.update(status='failed',final_audit_error={'type':type(error).__name__,'message':str(error)[:1024]})
            if survivors or sampler.is_alive() or sample_errors or not report['source_unchanged'] or not report.get('assets_unchanged') or not report.get('source_progress_snapshot_unchanged'):
                report['status']='failed'
            write_json(output/'report.json',report,budget)
    return report


def main():
    if len(sys.argv)==3 and sys.argv[1]=='--worker':
        return 0 if worker(json.loads(sys.argv[2])) else 1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();report=verify(args)
    print(json.dumps({'status':report['status'],'wall_seconds':report['wall_seconds'],
                      'report':str(args.output/'report.json'),'report_sha256':digest(args.output/'report.json')},allow_nan=False))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
