"""Twelve sequential owners: bounded measured-calibration development gate.

No truth feedback, historical perturbed fit, neural inference, or physical claim.
Normal invocation holds one writer lease and supervises the whole gate for 2160s.
"""
import argparse
import copy
import hashlib
import json
import os
import signal
import math
from pathlib import Path
import sys
import threading
import time
import uuid

from palimpsest import body_adaptation as adaptive, body_profile as body
from verify_body_runtime import command, digest, audit_ticks
from verify_body_gains import write_json, collect_trial
from verify_body_compensation import TRIALS, compare_trials
from verify_body_calibration import sample
from verify_endurance import source_identity, descendants, process
from verify_tasks import file_hashes

MiB = 1024**2
OWNERS = [('source',516), ('collecting',4), ('fitted',4), ('actions',516), ('policy',516)] + [
    (trial['id'],120) for trial in TRIALS] + [('expected-rejection',0)]
PROTOCOL = {'version':2, 'scenario':adaptive.SCENARIO, 'identity':adaptive.IDENTITY,
    'session_protocol':adaptive.PROTOCOL, 'owners':[{'id':name,'numeric_ticks':ticks,
        'deadline_seconds':60 if name=='expected-rejection' else 180} for name,ticks in OWNERS],
    'source_ticks':516, 'positive_numeric_ticks':2276, 'maximum_physics_intervals':2277,
    'snapshot_files':14, 'snapshots_per_run':3, 'snapshot_max_bytes':16*MiB,
    'outer_deadline_seconds':2160, 'output_max_bytes':2048*MiB, 'min_free_bytes':1024*MiB,
    'recording_max_bytes':256*MiB, 'log_max_bytes':MiB, 'report_max_bytes':MiB,
    'result_max_bytes':64*MiB, 'storage_headroom_bytes':8*MiB,
    'source':'four fresh120-tick probes; collecting snapshot24 + continuation4 inside first probe; four explicit next transitions; fresh fitted snapshot; continuation4; reset24 + reset8',
    'continuation':'run1/pause/step3, identical IDs, effective arrays/cameras and full session',
    'comparison':'100 settled intervals per direction, strict wheel-rate/yaw/lateral improvement over uncompensated versus matched baseline',
    'negative':'separate final owner: declared max_steps600->1 before first probe; raw interval/outcome retained, accepted cursor unchanged',
    'float_atol':1e-6, 'float_rtol':1e-6, 'cameras_and_integers':'exact',
    'scope':'one development seed/world; discrete contact caches, fitted simulator response; no held-out, continuous collision, online truth feedback, browser, neural learning or physical qualification'}
PROTOCOL_SHA256 = adaptive._sha(PROTOCOL)


def harness_hashes():
    return {name:digest(Path(__file__).with_name(name)) for name in ('verify_body_adaptation.py',
        'verify_body_runtime.py','verify_body_gains.py','verify_body_compensation.py',
        'verify_body_calibration.py','verify_tasks.py','verify_endurance.py')}


def read_json(path, *, maximum=MiB):
    with Path(path).open('rb') as stream:
        raw=stream.read(maximum+1)
    if len(raw)>maximum:
        raise ValueError('Verifier JSON exceeds declared read bound')
    return json.loads(raw)


def storage(config, *, control=False):
    from palimpsest.storage import StorageBudget, StorageLimits
    value=config['storage']
    return StorageBudget(tuple(Path(p) for p in value['roots']),StorageLimits(**value['limits']),
                         headroom_bytes=0 if control else value['headroom_bytes'])


def snapshot_path(path, expected_sha=None):
    path=Path(path)
    if path.is_symlink() or not path.is_file() or not 0<path.stat().st_size<=PROTOCOL['snapshot_max_bytes']:
        raise ValueError('Native snapshot missing, linked, or exceeds16MiB bound')
    if expected_sha is not None and digest(path)!=expected_sha:
        raise ValueError('Native snapshot changed')
    return path


def inventory(output, *, complete=False):
    """Exact gate inventory supplements aggregate fresh storage recounts."""
    output=Path(output)
    runs=list(output.glob('*/*/recording/manifest.json'))
    shots=list(output.rglob('*.snp'))
    if len(runs)>12 or len(shots)>14 or (complete and (len(runs)!=12 or len(shots)!=14)):
        raise ValueError('Gate run/snapshot count differs from bounded plan')
    for path in shots:
        snapshot_path(path)
    for manifest in runs:
        if len(list((manifest.parent.parent/'snapshots').glob('*.snp')))>3:
            raise ValueError('Per-run registered snapshot cap exceeded')
    return {'runs':len(runs),'snapshot_files':len(shots),'snapshot_bytes':sum(p.stat().st_size for p in shots)}


def preflight_bytes(observation):
    import numpy as np
    cameras=[observation[key] for key in ('cam_left','cam_right')]
    if any(a.dtype!=np.uint8 or a.ndim!=3 or a.shape[2]!=3 for a in cameras):
        raise ValueError('Actual camera schema invalid before first physics interval')
    # Each tick records raw and effective cameras. Include full raw body arrays,
    # record overhead, all14 maximum native files, atomic chunk staging, logs,
    # bounded evaluator results and control reports (no payload compression claim).
    records=2276*(2*sum(a.nbytes for a in cameras)+body.MAX_TICK_BYTES+4096)
    return {'numeric_estimate_bytes':records, 'total_admission_bytes':records+14*16*MiB+
            24*MiB+12*64*MiB+128*MiB+8*MiB}


def rejected_command(engine, identifier, kind, payload=None, *, stale=False):
    """Receipt rejection may change receipts, never native/session/reset cursor."""
    before=(engine.episode,engine.episode_step,engine.total_tick,engine.env.data.time,
            engine.env.model._address,engine.env.data._address,copy.deepcopy(engine.body_state))
    message={'id':identifier,'kind':kind,'expected_state':engine.phase,'expected_episode':engine.episode,
             'expected_revision':engine.revision-(1 if stale else 0)}
    if payload is not None:
        message['payload']=payload
    receipt=engine.submit(message)
    if receipt['status']=='queued':
        engine.advance();receipt=engine.submit(message)
    after=(engine.episode,engine.episode_step,engine.total_tick,engine.env.data.time,
           engine.env.model._address,engine.env.data._address,engine.body_state)
    if receipt['status']!='rejected' or before!=after:
        raise ValueError('Intentional command guard applied or mutated physical/session state')
    return {'id':identifier,'status':'rejected','reason':receipt.get('reason'),'native_cursor_unchanged':True}


def continuation(engine, prefix):
    states=[]
    command(engine,prefix+'-run','run');states.append(copy.deepcopy(engine.body_state))
    command(engine,prefix+'-pause','pause')
    for index in range(1,4):
        command(engine,f'{prefix}-step-{index}','step');states.append(copy.deepcopy(engine.body_state))
    return states


def source_session(engine, save_boundary):
    """Exactly516 source intervals; callback saves the two explicit native files."""
    guards=[rejected_command(engine,'guard-manual','set_action',{'action':[.2,0.]}),
            rejected_command(engine,'guard-early-next','calibration-next')]
    command(engine,'warm-run','run')
    command(engine,'warm-pause','pause')
    for index in range(1,24):
        command(engine,f'probe0-{index}','step')
    if len(engine.body_state['samples'])!=4:
        raise ValueError('Collecting snapshot sample count differs')
    save_boundary('collecting',engine)
    collecting=continuation(engine,'collecting-continuation')
    for index in range(28,120):
        command(engine,f'probe0-{index}','step')
    guards.append(rejected_command(engine,'guard-stale-next','calibration-next',stale=True))
    for trial in range(4):
        if engine.body_state['phase']!=('fit_complete' if trial==3 else 'trial_complete'):
            raise ValueError('Calibration trial rejected or did not finish exactly120 intervals')
        identifier=f'next-{trial}'
        message={'id':identifier,'kind':'calibration-next','expected_state':'paused',
                 'expected_episode':engine.episode,'expected_revision':engine.revision}
        command(engine,identifier,'calibration-next')
        cursor=(engine.episode,engine.total_tick,engine.revision,copy.deepcopy(engine.body_state))
        receipt=engine.submit(message)
        if receipt['status']!='applied' or cursor!=(engine.episode,engine.total_tick,engine.revision,engine.body_state):
            raise ValueError('Repeated accepted next ID reset or applied twice')
        guards.append({'id':identifier,'idempotent_receipt':True,'native_cursor_unchanged':True})
        if trial<3:
            for tick in range(120):
                command(engine,f'probe{trial+1}-{tick}','step')
    accepted=copy.deepcopy(engine.body_state)
    if accepted['phase']!='fitted' or len(accepted['samples'])!=400 or engine.episode_step!=0:
        raise ValueError('Fourth next did not create one fresh accepted fitted episode')
    guards.append(rejected_command(engine,'guard-fitted-next','calibration-next'))
    save_boundary('fitted',engine)
    command(engine,'fitted-forward','set_action',{'action':[.3,0.]})
    fitted=continuation(engine,'fitted-continuation')
    command(engine,'ordinary-reset-full','reset',{'seed':1})
    if engine.body_state['samples'] or engine.body_state['fit'] is not None or engine.body_state['trial_index']!=0:
        raise ValueError('Ordinary reset retained accepted calibration')
    for tick in range(24):
        command(engine,f'reset-partial-{tick}','step')
    if len(engine.body_state['samples'])!=4:
        raise ValueError('Partial-reset fixture did not collect four samples')
    command(engine,'ordinary-reset-partial','reset',{'seed':1})
    if engine.body_state['samples'] or engine.body_state['fit'] is not None:
        raise ValueError('Ordinary reset retained partial calibration')
    for tick in range(8):
        command(engine,f'reset-fresh-{tick}','step')
    if engine.total_tick!=516 or engine.episode_step!=8 or engine.phase!='paused':
        raise ValueError('Exact source accounting failed')
    return {'guards':guards,'accepted_session':accepted,'collecting_continuation':collecting,'fitted_continuation':fitted,
            'reset_cleared':True}


def native_encoder_mismatch(snapshot, env):
    """Keep the valid application unchanged; stage a self-consistent bad native cursor."""
    import mujoco
    import numpy as np
    malformed=copy.deepcopy(snapshot)
    adaptive.validate_session(malformed['application']['body_state'],
        episode=malformed['application']['episode'],episode_step=malformed['application']['episode_step'])
    data=mujoco.MjData.__new__(mujoco.MjData)
    data.__setstate__(malformed['native_data'])
    data.qpos[int(data.model.jnt_qposadr[env.left_hinge_id])]+=.1
    malformed['native_data']=data.__getstate__()
    malformed['native_sha256']=hashlib.sha256(malformed['native_data']).hexdigest()
    enum=mujoco.mjtState.mjSTATE_INTEGRATION
    audit=np.empty(mujoco.mj_stateSize(data.model,enum),np.float64)
    mujoco.mj_getState(data.model,data,audit,enum)
    malformed['integration']=audit
    return malformed


def malformed_guards(engine, snapshot):
    from palimpsest.snapshots import capture, state_digest
    before=capture(engine.env,engine.observation,application=engine.application_state())
    expected=state_digest(before);addresses=(engine.env.model._address,engine.env.data._address)
    guards=[]
    for kind in ('typed_sample_hash','native_encoder_mismatch'):
        bad=copy.deepcopy(snapshot)
        state=bad['application']['body_state']
        if kind=='typed_sample_hash':
            state['samples_sha256']=True
        else:
            bad=native_encoder_mismatch(snapshot,engine.env)
        try:
            engine.restore_branch(bad)
        except ValueError as error:
            if kind=='native_encoder_mismatch' and 'raw encoder cursor differs from native data' not in str(error):
                raise ValueError('Malformed native case did not reach encoder binding') from error
            after=capture(engine.env,engine.observation,application=engine.application_state())
            if state_digest(after)!=expected or addresses!=(engine.env.model._address,engine.env.data._address):
                raise ValueError('Malformed adaptive restore mutated destination') from error
            guards.append({'case':kind,'rejected_before_mutation':True,'reason':str(error)[:256],
                           'destination_state_sha256':expected})
        else:
            raise ValueError('Malformed adaptive snapshot accepted')
    return guards


def canonical_model(model):
    """Evaluator comparison excludes ONLY the declared motor gear matrix."""
    import mujoco
    clone=mujoco.MjModel.__new__(mujoco.MjModel)
    clone.__setstate__(model.__getstate__());clone.actuator_gear[:]=0.
    return hashlib.sha256(clone.__getstate__()).hexdigest()


def match_reference(engine, snapshot):
    import numpy as np
    import mujoco
    from palimpsest import task_profiles
    from palimpsest.snapshots import ENV_PROFILE, _fields
    reference=mujoco.MjData.__new__(mujoco.MjData);reference.__setstate__(snapshot['native_data'])
    actual=np.empty(mujoco.mj_stateSize(engine.env.model,mujoco.mjtState.mjSTATE_INTEGRATION))
    mujoco.mj_getState(engine.env.model,engine.env.data,actual,mujoco.mjtState.mjSTATE_INTEGRATION)
    if (not np.array_equal(actual.view(np.uint8),snapshot['integration'].view(np.uint8)) or
            canonical_model(engine.env.model)!=canonical_model(reference.model)):
        raise ValueError('Diagnostic fresh physical state/model differs beyond declared gear')
    profile=_fields(engine.env,ENV_PROFILE)
    if profile!=snapshot['identity']['environment_profile']:
        raise ValueError('Diagnostic physical environment profile differs')
    calibration=task_profiles.body_calibration(engine.env)
    if calibration['radius_m']!=.06 or not math.isclose(calibration['track_m'],.36,abs_tol=1e-12,rel_tol=0.):
        raise ValueError('Physical radius/track changed')
    return {'integration_exact':True,'canonical_model_sha256':canonical_model(engine.env.model),
            'excluded_model_field':'actuator_gear only','physical_calibration':calibration}


def reference_guard(engine, snapshot, config):
    inventory(Path(config['output']))
    return match_reference(engine,snapshot)


def evaluator_row(engine, tick, before):
    arrays=engine.last_transition;after=sample(engine.env)
    return {'tick':tick,'fit_interval':tick>=20,'before':before,'after':after,
        'increments_rad':arrays['body_encoder_increment'].tolist(),'dt_s':float(arrays['body_dt']),
        'control':arrays['control'].tolist(),'action':arrays['action'].tolist(),
        'contact':bool((arrays['body_contact_classes']==3).any()),'coverage_passed':True}


def verify_rejection(engine, accepted, packet):
    import numpy as np
    interval=packet.get('interval') or {}
    if (engine.phase!='failed' or engine.total_tick!=0 or engine.body_state!=accepted or
            packet.get('outcome')!={'terminated':False,'truncated':True} or
            interval.get('coverage_passed') is not True or interval.get('contact') is not False or
            abs(engine.env.data.time-.02)>1e-9):
        raise ValueError('Expected rejection lacked measured outcome/unchanged accepted cursor')
    arrays=body.contact_arrays(interval)
    plan=packet['command']
    row={'episode':0,'tick':0,'simulation_time':np.array(engine.env.data.time),
         'action':np.asarray(plan['applied_action'],np.float64),'control':np.asarray(engine.env.data.ctrl,np.float64),
         'body_nominal_action':np.asarray(plan['nominal_action'],np.float64),
         'body_nominal_control':np.asarray(plan['nominal_control'],np.float32),
         'body_encoder_before':np.asarray(packet['encoder_before'],np.float64),
         'body_encoder_after':np.asarray(packet['encoder_after'],np.float64),
         'body_encoder_increment':np.asarray(packet['increments_rad'],np.float64),
         'body_dt':np.array(packet['dt_s'],np.float64),**arrays}
    return audit_ticks([row],{'body_profile_identity':adaptive.IDENTITY,
        'body_contact_ownership':engine.env._body_contact_ownership},identity=adaptive.IDENTITY,
        planner=lambda _:plan)


def worker(config):
    import mujoco
    from palimpsest.engine import Engine
    from palimpsest.replay import _register_initial, replay_run, _same_json
    from palimpsest.snapshots import capture, save_snapshot, read_snapshot, _model_digest
    mode=config['mode'];stage=Path(config['stage']);run=Path(config['run']);budget=storage(config)
    result={'status':'running','mode':mode,'run':str(run)};engine=None
    try:
        if source_identity(Path(config['repo']))!=config['runtime_source'] or harness_hashes()!=config['harness_sha256']:
            raise ValueError('Source/harness changed before owner startup')
        if mode in ('actions','policy'):
            run.mkdir()
            report=replay_run(Path(config['source']),run,mode=mode,repo_root=Path(config['repo']),
                asset_root=Path(config['assets']),storage_budget=budget,recording_max_bytes=PROTOCOL['recording_max_bytes'],
                progress=lambda stage,**kw:inventory(Path(config['output'])) if stage=='ready' else None)
            if report['status']!='passed' or report['compared_ticks']!=516:
                raise ValueError('Executable replay failed exact516-tick contract')
            result.update(status='passed',compared_ticks=516,replay_report_sha256=digest(run/'replay-report.json'),engine_closed=True)
        elif mode.startswith(('baseline-','uncompensated-')):
            snapshot=read_snapshot(snapshot_path(config['fitted_snapshot'],config['fitted_sha256']))
            trial=next(t for t in TRIALS if t['id']==mode)
            fixed_protocol={**PROTOCOL,'seed':1,'ticks':120,'settling_ticks':20,
                'start_pose':adaptive.PROTOCOL['start_pose'],'goal_xy':adaptive.PROTOCOL['goal_xy']}
            okay=collect_trial({**config,'trial':trial},fixed_protocol,PROTOCOL_SHA256,harness=harness_hashes(),
                storage_budget=budget,result_max_bytes=PROTOCOL['result_max_bytes'],
                initial_guard=lambda e:reference_guard(e,snapshot,config),record_body_arrays=True)
            return okay  # Shared collector closes engine/callback and writes retained result.
        else:
            run.mkdir()
            engine=Engine.open(Path(config['repo']),Path(config['assets']),run/'recording',controller='manual',
                device='cpu',seed=1,scenario=adaptive.SCENARIO,texture='checker',run_id=run.name,
                max_bytes=PROTOCOL['recording_max_bytes'],storage_budget=budget)
            result['model_sha256']=_model_digest(engine.env.model)
            if result['model_sha256']!=adaptive.IDENTITY['model_sha256']:
                raise ValueError('Actual adaptive model pin differs')
            engine.writer.event('body_verifier_protocol',protocol=PROTOCOL,harness_sha256=harness_hashes())
            def register(preflight_bytes=0):
                _register_initial(engine,run,budget,preflight_bytes=preflight_bytes)
                inventory(Path(config['output']))
            if mode=='source':
                admission=preflight_bytes(engine.observation)
                budget.check(admission['total_admission_bytes'],path=run/'recording')
                result['admission']=admission
                register(admission['total_admission_bytes'])
                snapshots={}
                def save_boundary(name,owner):
                    snp=capture(owner.env,owner.observation,application=owner.application_state())
                    path=stage/(name+'.snp');save_snapshot(snp,path,storage_budget=budget);snapshot_path(path)
                    snapshots[name]={'path':str(path),'sha256':digest(path),'session_sha256':adaptive._sha(owner.body_state)}
                    inventory(Path(config['output']))
                result.update(source_session(engine,save_boundary),snapshots=snapshots)
                continuation_file=stage/'continuation-states.json'
                write_json(continuation_file,{name:result[name+'_continuation'] for name in ('collecting','fitted')},
                           max_bytes=MiB,storage_budget=budget)
                result['continuation_file']={'path':str(continuation_file),'sha256':digest(continuation_file)}
                engine.writer.flush()
            elif mode=='expected-rejection':
                original=engine.env.max_steps
                if original!=600:
                    raise ValueError('Fault fixture requires pinned original600 step cap')
                engine.env.max_steps=1
                engine.writer.event('verifier_failure_injection',field='env.max_steps',old=original,new=1,
                                    scope='expected negative, not positive capability')
                register()
                accepted=copy.deepcopy(engine.body_state)
                message={'id':'fault-step','kind':'step','expected_state':'paused','expected_episode':0,
                         'expected_revision':engine.revision}
                engine.submit(message);engine.advance();engine.writer.flush()
                with (run/'recording/events.jsonl').open('rb') as stream:
                    raw=stream.read(MiB+1)
                if len(raw)>MiB:
                    raise ValueError('Negative event evidence exceeds1MiB read bound')
                events=[json.loads(line) for line in raw.splitlines()]
                failures=[event for event in events if event.get('kind')=='body_failed']
                if len(failures)!=1:
                    raise ValueError('Expected negative raw packet not retained once')
                packet=failures[0]['detail']
                negative_audit=verify_rejection(engine,accepted,packet)
                result.update(status='expected_rejection',expected_negative_verified=True,
                    failure_packet=packet,raw_rejected_interval_audit=negative_audit,
                    accepted_cursor_unchanged=True,physics_intervals=1)
            else:
                boundary='collecting' if mode=='collecting' else 'fitted'
                snapshot=read_snapshot(snapshot_path(config[boundary+'_snapshot'],config[boundary+'_sha256']))
                if mode in ('collecting','fitted'):
                    result['malformed_restore']=malformed_guards(engine,snapshot)
                engine.restore_branch(snapshot)
                _same_json(snapshot['application']['body_state'],engine.body_state,'native_session')
                register()
                if mode in ('collecting','fitted'):
                    if mode=='fitted':
                        command(engine,'fitted-forward','set_action',{'action':[.3,0.]})
                    states=continuation(engine,mode+'-continuation')
                    if digest(config['continuation_file'])!=config['continuation_sha256']:
                        raise ValueError('Immutable continuation state file changed')
                    _same_json(read_json(config['continuation_file'])[mode],states,'native_continuation')
                    result['continuation']=states
                else:
                    trial=next(t for t in TRIALS if t['id']==mode)
                    result.update(trial=trial,rows=[],physical_calibration=__import__('palimpsest.task_profiles',fromlist=['body_calibration']).body_calibration(engine.env),
                                  matched_initial_state=match_reference(engine,snapshot))
                    initial_hash=(engine.body_state['samples_sha256'],engine.body_state['fit_sha256'])
                    command(engine,'evaluation-action','set_action',{'action':trial['action']})
                    for tick in range(120):
                        before=sample(engine.env);command(engine,f'evaluation-{tick}','step')
                        result['rows'].append(evaluator_row(engine,tick,before))
                        if engine.phase!='paused' or (engine.body_state['samples_sha256'],engine.body_state['fit_sha256'])!=initial_hash:
                            raise ValueError('Evaluation terminated or changed frozen fitted samples/fit')
                    result['fit_unchanged']=True
            if result['status']=='running':
                result['status']='passed'
            result['final_model_sha256']=_model_digest(engine.env.model)
            if result['final_model_sha256']!=result['model_sha256']:
                raise ValueError('Adaptive immutable model changed')
            result['final_state']=engine.public_state()
    except Exception as error:
        result.update(status='failed',error={'type':type(error).__name__,'message':str(error)[:1024]})
    finally:
        if engine is not None:
            try:
                result.setdefault('final_state',engine.public_state());engine.close();result['engine_closed']=True
            except Exception as error:
                result.update(status='failed',cleanup_error={'type':type(error).__name__,'message':str(error)[:512]})
        result['callback_restored']=mujoco.get_mjcb_control() is None
        if not result['callback_restored']:
            result['status']='failed'
        # The shared collector already wrote the complete reference result.
        if not mode.startswith(('baseline-','uncompensated-')) or not (stage/'result.json').exists():
            write_json(stage/'result.json',result,max_bytes=PROTOCOL['result_max_bytes'],storage_budget=storage(config,control=True))
    return result['status'] in ('passed','expected_rejection')


def coverage(mode):
    if mode in ('source','actions','policy'):
        return [(episode,tick) for episode,length in [(0,120),(1,120),(2,120),(3,120),(4,4),(5,24),(6,8)] for tick in range(length)]
    if mode=='collecting':
        return [(0,tick) for tick in range(24,28)]
    if mode=='fitted':
        return [(4,tick) for tick in range(4)]
    if mode.startswith('compensated-'):
        return [(4,tick) for tick in range(120)]
    if mode=='expected-rejection':
        return []
    return [(0,tick) for tick in range(120)]


def planner(row, accepted_session):
    nominal=row['body_nominal_action'].tolist()
    if int(row['episode'])==4:
        return adaptive.plan_action(accepted_session,nominal)
    control=body.effective_control(nominal)
    return {'nominal_control':control,'applied_action':nominal,'applied_control':control}


def owner_result(mode, supervision, result, rows):
    """Positive, expected-negative and not-started are never interchangeable."""
    expected='expected_rejection' if mode=='expected-rejection' else 'passed'
    if (supervision.get('status')!='completed' or supervision.get('returncode')!=0 or
            result.get('status')!=expected or result.get('engine_closed') is not True or
            result.get('callback_restored') is not True or
            [(int(row['episode']),int(row['tick'])) for row in rows]!=coverage(mode)):
        raise ValueError(mode+' failed lifecycle/result/exact numeric coverage contract')
    if mode=='expected-rejection' and (result.get('expected_negative_verified') is not True or
            result.get('accepted_cursor_unchanged') is not True or result.get('physics_intervals')!=1):
        raise ValueError('Expected-negative result not verified or retained')


def gate(config):
    from palimpsest.evaluate import bounded_process
    from palimpsest.assets import verify_assets
    from palimpsest.records import iter_ticks
    from palimpsest.replay import _same_tick, _same_json
    root=Path(config['repo']);assets=Path(config['assets']);output=Path(config['output']);budget=storage(config)
    report=read_json(output/'report.json');started=time.monotonic();source_run=None
    comparison={};immutable=None;continuations={};snapshots={};accepted=None
    try:
        if source_identity(root)!=report['runtime_source'] or harness_hashes()!=report['harness_sha256']:
            raise ValueError('Frozen gate source changed before startup')
        report['assets']=verify_assets(root,assets)
        if not report['assets']['ok']:
            raise ValueError('Pinned cached asset verification failed')
        environment={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','OMP_NUM_THREADS':'2','MPLBACKEND':'Agg'}
        for number,(mode,expected_ticks) in enumerate(OWNERS):
            budget.check_count('runs',number)
            stage=output/mode;run=stage/uuid.uuid4().hex
            report['workers'][mode]['status']='running'
            write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
            child={**config,'mode':mode,'stage':str(stage),'run':str(run),'source':str(source_run),
                   'runtime_source':report['runtime_source'],'harness_sha256':report['harness_sha256']}
            if snapshots:
                for name,item in snapshots.items():
                    child[name+'_snapshot']=item['path'];child[name+'_sha256']=item['sha256']
                source_result=report['workers']['source']['result']
                child['continuation_file']=source_result['continuation_file']['path']
                child['continuation_sha256']=source_result['continuation_file']['sha256']
            payload=json.dumps(child)
            if len(payload.encode())>64*1024:
                raise ValueError('Owner configuration exceeds64KiB argv bound; no sample buffers in commands')
            supervision=bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',payload],
                stage,60 if mode=='expected-rejection' else 180,environment,
                log_max_bytes=MiB,storage_budget=budget)
            item=report['workers'][mode];item.update(status='failed',supervision=supervision)
            result_path=stage/'result.json'
            if result_path.exists():
                result=read_json(result_path,maximum=PROTOCOL['result_max_bytes'])
                item.update(result_sha256=digest(result_path),result_path=str(result_path),
                            result={key:value for key,value in result.items() if key not in
                                    ('rows','accepted_session','collecting_continuation','fitted_continuation','continuation','failure_packet')})
            else:
                raise ValueError(mode+' produced no bounded result; inspect retained native logs')
            rows=list(iter_ticks(run/'recording'))
            owner_result(mode,supervision,result,rows)
            manifest=read_json(run/'recording/manifest.json')
            if mode!='expected-rejection' and manifest.get('status')!='completed':
                raise ValueError(mode+' recording did not finish normally')
            inventory(output)
            if mode=='source':
                source_run=run;snapshots=result['snapshots'];accepted=result['accepted_session']
                adaptive.validate_session(accepted,episode=4,episode_step=0)
                continuations={name:result[name+'_continuation'] for name in ('collecting','fitted')}
                source_rows={name:[row for row in rows if (int(row['episode']),int(row['tick'])) in coverage(name)]
                             for name in ('collecting','fitted')}
                immutable=file_hashes(run)
                report['accepted_fit']={'fit':accepted['fit'],'fit_sha256':accepted['fit_sha256'],
                    'samples_sha256':accepted['samples_sha256'],'session_sha256':adaptive._sha(accepted),
                    'sample_count':len(accepted['samples']),'evaluation_data_reused':False}
                report['snapshots']=snapshots
            if mode!='expected-rejection':
                identity=adaptive.IDENTITY
                plan=lambda row:planner(row,accepted)
                if mode.startswith(('baseline-','uncompensated-')):
                    identity={'standalone':True,'protocol_sha256':PROTOCOL_SHA256}
                    plan=lambda row:{'nominal_control':body.effective_control(row['body_nominal_action'].tolist()),
                        'applied_action':row['body_nominal_action'].tolist(),'applied_control':body.effective_control(row['body_nominal_action'].tolist())}
                item['raw_audit']=audit_ticks(rows,manifest,identity=identity,planner=plan)
            if mode in ('collecting','fitted'):
                for left,right in zip(source_rows[mode],rows):
                    _same_tick(left,right,'policy',int(right['tick']))
                _same_json(continuations[mode],result['continuation'],mode+'_session')
                if len(result.get('malformed_restore',[]))!=2 or not all(g['rejected_before_mutation'] for g in result['malformed_restore']):
                    raise ValueError('Native malformed restore guards not observed twice')
                item['native_continuation']={'ticks':4,'raw_fields_and_cameras':'matched','full_session':'matched'}
            if mode in {trial['id'] for trial in TRIALS}:
                comparison[mode]=result
                if mode==TRIALS[-1]['id']:
                    report['comparison']=compare_trials(comparison)
                    if not report['comparison']['accepted']:
                        raise ValueError('Paired development metrics rejected; expected-negative remains not started')
            if mode!='source' and file_hashes(source_run)!=immutable:
                raise ValueError('Immutable source recording changed')
            for item_snapshot in snapshots.values():
                snapshot_path(item_snapshot['path'],item_snapshot['sha256'])
            item['status']='expected_rejection' if mode=='expected-rejection' else 'passed'
            if mode=='expected-rejection':
                report['expected_negative']={'status':'verified','result_sha256':item['result_sha256'],
                    'application_phase':'failed','numeric_ticks':0,'raw_rejected_physics_intervals':1,
                    'positive_capability':False}
            write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
        report['inventory']=inventory(output,complete=True)
        if sum(w['raw_audit']['ticks'] for w in report['workers'].values() if 'raw_audit' in w)!=2276:
            raise ValueError('Positive numeric interval total differs')
        report['status']='passed'
    except Exception as error:
        report.update(status='failed',error={'type':type(error).__name__,'message':str(error)[:1024]})
        for item in report['workers'].values():
            if item['status']=='not_started':
                item['reason']='Stopped after first real rejection/failure; no retry or relaxed bounds'
    finally:
        report.update(gate_wall_seconds=time.monotonic()-started,runtime_source_at_end=source_identity(root),
                      harness_sha256_at_end=harness_hashes())
        report['source_unchanged']=report['runtime_source']==report['runtime_source_at_end'] and report['harness_sha256']==report['harness_sha256_at_end']
        try:
            report['assets_at_end']=verify_assets(root,assets)
            report['assets_unchanged']=report.get('assets')==report['assets_at_end'] and report['assets_at_end']['ok']
            report['source_recording_unchanged']=immutable is not None and immutable==file_hashes(source_run)
            report['output_usage']=budget.usage()
            report['inventory']=inventory(output,complete=report['status']=='passed')
        except Exception as error:
            report.update(status='failed',final_audit_error={'type':type(error).__name__,'message':str(error)[:512]})
        if not report['source_unchanged'] or not report.get('assets_unchanged') or not report.get('source_recording_unchanged'):
            report['status']='failed'
        write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
    return report['status']=='passed'


def cleanup_observed(observed):
    """Contain only sampled owned PID/start identities; forced cleanup is failure."""
    actions=[]
    def remaining():
        return [row for pid,start in observed.items() if (row:=process(pid)) and row['start_ticks']==start]
    for number in (signal.SIGTERM,signal.SIGKILL):
        for row in remaining():
            if row['state']=='Z':
                continue
            # Recheck immediately before signalling to avoid using a stale survey.
            current=process(row['pid'])
            if current is None or current['start_ticks']!=observed[row['pid']]:
                continue
            try:
                if current['group']==current['pid']:
                    os.killpg(current['pid'],number)
                else:
                    os.kill(current['pid'],number)
            except ProcessLookupError:
                continue
            actions.append({'pid':current['pid'],'start_ticks':current['start_ticks'],
                            'signal':signal.Signals(number).name,'group':current['group']})
        deadline=time.monotonic()+2.
        while remaining() and time.monotonic()<deadline:
            time.sleep(.05)
    return {'forced_signals':actions,'survivors':remaining()}


def verify(args):
    from dataclasses import asdict
    from palimpsest.storage import StorageBudget, StorageLimits
    from palimpsest.evaluate import bounded_process
    root=args.repo.resolve();assets=args.assets.resolve();output=args.output.resolve()
    if assets.is_relative_to(output) or output.is_relative_to(assets):
        raise ValueError('Assets must be outside managed output')
    output.mkdir(parents=True,exist_ok=False)
    limits=StorageLimits(max_bytes=2048*MiB,min_free_bytes=1024*MiB,max_runs=12,max_snapshots=3,max_exports=1)
    budget=StorageBudget((output,),limits,headroom_bytes=8*MiB)
    config={'repo':str(root),'assets':str(assets),'output':str(output),
            'storage':{'roots':[str(output)],'limits':asdict(limits),'headroom_bytes':budget.headroom_bytes}}
    report={'version':1,'status':'running','protocol':PROTOCOL,'protocol_sha256':PROTOCOL_SHA256,
            'runtime_source':source_identity(root),'harness_sha256':harness_hashes(),
            'workers':{mode:{'status':'not_started','planned_numeric_ticks':ticks} for mode,ticks in OWNERS},'storage':config['storage']}
    known={};sample_errors=[];stop=threading.Event();lock=threading.Lock()
    def sample_owned():
        try:
            while not stop.is_set():
                with lock:
                    for row in descendants(os.getpid()):
                        if row['pid'] not in known and len(known)>=256:
                            raise ValueError('Finite owned-process inventory exceeds256')
                        known[row['pid']]=row['start_ticks']
                stop.wait(.25)
        except Exception as error:
            sample_errors.append(str(error)[:512]);stop.set()
    sampler=threading.Thread(target=sample_owned,daemon=True);started=time.monotonic()
    with budget.lock():
        write_json(output/'report.json',report,max_bytes=MiB,storage_budget=budget)
        sampler.start()
        try:
            environment={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','OMP_NUM_THREADS':'2','MPLBACKEND':'Agg'}
            supervision=bounded_process([sys.executable,str(Path(__file__).resolve()),'--gate',json.dumps(config)],
                output/'outer-supervision',2160,environment,log_max_bytes=MiB,storage_budget=budget)
            report=read_json(output/'report.json')
            report['outer_supervision']=supervision
            if supervision['status']!='completed' or supervision['returncode']!=0:
                report['status']='failed'
        except Exception as error:
            report.update(status='failed',outer_error={'type':type(error).__name__,'message':str(error)[:512]})
        finally:
            stop.set();sampler.join(timeout=2.)
            with lock:
                observed=dict(known)
            containment=cleanup_observed(observed)
            survivors=containment['survivors']
            report['cleanup']={'observed_owned_processes':[{'pid':pid,'start_ticks':start} for pid,start in sorted(observed.items())],
                **containment,'sampler_stopped':not sampler.is_alive(),'sample_errors':sample_errors,
                'scope':'finite .25s sampling and final PID/start check; not universal transient-process proof; no server/listener; bounded_process attempts owned-group TERM/KILL cleanup even after normal leader exit, signal delivery is not recorded'}
            report.update(wall_seconds=time.monotonic()-started,final_source=source_identity(root),final_harness=harness_hashes())
            if (survivors or containment['forced_signals'] or sampler.is_alive() or sample_errors or report['final_source']!=report['runtime_source'] or
                    report['final_harness']!=report['harness_sha256']):
                report['status']='failed'
            report['output_usage']=budget.usage()
            report['artifacts_sha256']={k:v for k,v in file_hashes(output).items() if k not in ('report.json','.palimpsest-storage.lock')}
            write_json(output/'report.json',report,max_bytes=MiB,storage_budget=storage(config,control=True))
    return report


def main():
    if len(sys.argv)==3 and sys.argv[1] in ('--worker','--gate'):
        function=worker if sys.argv[1]=='--worker' else gate
        return 0 if function(json.loads(sys.argv[2])) else 1
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
