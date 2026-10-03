"""Fixed ten-owner pre-product puck mechanics gate; requires separate runtime GO.

This standalone verifier is the explicit exception to prospective LabSupervisor
ownership in the task plan. No production task/controller/snapshot API is added.
Use retained TERM660/+15 inside bounded_process680. No retries or extra owners.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import zipfile

from verify_afterimage import digest, write_json, process_identity, cleanup_check
from palimpsest import puck_profile as puck
from palimpsest.snapshots import state_digest

PROTOCOL_FILE = 'docs/plans/m6-puck-mechanics-v4.json'
PROTOCOL_SHA256 = 'e24a60ef1e2ddc74cf04e9d640e537fdeb157f7f0c781707a9d092bed421ddc7'
MiB = 1024**2


def read_json(path, cap=4*MiB):
    with Path(path).open('rb') as stream:
        raw = stream.read(cap+1)
    if len(raw) > cap:
        raise ValueError('Verifier JSON exceeds fixed bound')
    return json.loads(raw)


def protocol(root):
    path = root / PROTOCOL_FILE
    spec = read_json(path, 32768)
    if digest(path) != PROTOCOL_SHA256 or digest(root/'src/palimpsest/puck_profile.py') != spec['puck_module_sha256']:
        raise ValueError('Mechanics protocol/module differs from reviewed pin')
    if puck.PROTOCOL_SHA256 != spec['pushing_protocol_sha256']:
        raise ValueError('Original frozen task protocol differs')
    return spec


def sources(root):
    from verify_puck_construction import sources as construction_sources
    result = construction_sources(root)
    for name in (PROTOCOL_FILE, puck.PROTOCOL_PATH, 'scripts/verify_puck_mechanics.py', 'scripts/verify_endurance.py',
                 'tests/test_puck_mechanics.py'):
        result[name] = digest(root/name)
    return dict(sorted(result.items()))


def teacher_sources(root):
    from palimpsest import puck_learning
    result=sources(root)
    for name in (puck_learning.PROTOCOL_PATH,'scripts/collect_puck_teachers.py','tests/test_puck_collection.py'):
        result[name]=digest(root/name)
    return dict(sorted(result.items()))


def plan(task):
    limits = task['limits']
    rows = [{'id':case['id'], 'kind':'root', 'case':case['id'], 'seed':case['seed'],
             'max_ticks':case['ticks'], 'max_bytes':limits[f"per_{case['ticks']}_tick_record_and_snapshot_bytes"]}
            for case in task['physics_cases']]
    for derivative, name, boundary in zip(task['physics_derivatives'],
            ['continue-tick1','continue-contact','continue-dwell','replay-actions','replay-policy'],
            ['tick1','contact','dwell','initial','initial']):
        case = next(c for c in task['physics_cases'] if c['id'] == derivative['source'])
        ticks = derivative['ticks'] if type(derivative['ticks']) is int else case['ticks']
        cap = limits['per_short_branch_bytes'] if ticks == 4 else limits[f'per_{ticks}_tick_record_and_snapshot_bytes']
        rows.append({'id':name,'kind':derivative['kind'],'case':case['id'],'seed':case['seed'],
                     'boundary':boundary,'max_ticks':ticks,'max_bytes':cap})
    if len(rows) != 10 or sum(r['max_bytes'] for r in rows) != limits['physics']['planned_record_allowance_bytes']:
        raise ValueError('Fixed mechanics plan/allowances differ')
    return rows


def boundaries(state, contact, seen):
    return [name for name, hit in [('tick1',state['tick']==1),
            ('contact',contact['rover_puck_contact']), ('dwell',state['dwell_ticks']==1)] if hit and name not in seen]


def window(rows, start, count):
    if type(start) is not int or type(count) is not int or start < 0 or not 1 <= count <= 600:
        raise ValueError('Invalid bounded continuation window')
    selected = [r for r in rows if start <= r['tick'] < start+count]
    if [(r['episode'],r['tick']) for r in selected] != [(0,n) for n in range(start,start+count)]:
        raise ValueError('Missing, duplicated or noncontiguous source successor ticks')
    return selected


def same_row(expected, actual):
    import numpy as np
    if set(expected) != set(actual):
        raise ValueError('Replay numeric schema differs')
    for key in expected:
        a, b = np.asarray(expected[key]), np.asarray(actual[key])
        if (a.dtype != b.dtype or a.shape != b.shape or not np.isfinite(a).all() or
                not np.isfinite(b).all() or a.tobytes() != b.tobytes()):
            raise ValueError('Exact replay differs: ' + key)


def mode_code(mode, case, *, learning_teacher=False):
    if learning_teacher:
        if learning_teacher is not True or case not in {f'teacher-{n}' for n in range(6000,6020)}:
            raise ValueError('Unknown fixed learning teacher case')
        if type(mode) is not str or mode not in ('approach','push'):
            raise ValueError('Invalid learning teacher mode')
        return {'approach':1,'push':2}[mode]
    allowed = ('approach','push') if case in ('teacher-positive','teacher-negative') else (
        ('fixed',) if case in ('zero','push-positive','push-negative') else ())
    if type(mode) is not str or mode not in allowed:
        raise ValueError('Teacher mode differs from fixed mechanics case')
    return {'fixed':0, 'approach':1, 'push':2}[mode]


def action_for(row, world, mode, recorded=None):
    mode_code(mode, row['case'])
    if row['kind'] == 'action-replay':
        import numpy as np
        if mode != 'fixed' or recorded is None:
            raise ValueError('Only the fixed-action mechanics source admits action replay')
        for name in ('teacher_mode_before','teacher_mode_after'):
            value = np.asarray(recorded.get(name))
            if value.dtype != np.uint8 or value.shape != () or value.item() != 0:
                raise ValueError('Fixed action replay has incompatible recorded mode')
        return recorded['action'].tolist(), mode
    if row['kind'] == 'root' and 'action' in row:
        if mode != 'fixed': raise ValueError('Teacher source cannot use a fixed command')
        return list(row['action']), mode
    return puck.demonstrate(world, mode)  # Exactly once per teacher/policy interval.


def validate_application(app, case, tick, expected_hash):
    import numpy as np
    required={'version','gate_protocol_sha256','case','profile_identity','model_sha256',
              'state','world','contact','inputs','paused','teacher_mode'}
    if (type(app) is not dict or set(app) != required or type(app['version']) is not int or app['version'] != 2 or app['paused'] is not True or
            app['gate_protocol_sha256'] != PROTOCOL_SHA256 or app['case'] != case or state_digest(app) != expected_hash):
        raise ValueError('Puck verifier snapshot application identity differs')
    mode_code(app['teacher_mode'], case)
    if tick == 0 and case.startswith('teacher-') and app['teacher_mode'] != 'approach':
        raise ValueError('Initial teacher snapshot must retain approach mode')
    state, world, contact = app['state'], app['world'], app['contact']
    puck._world(world); puck._contact(contact, world['time_s'])
    if (type(tick) is not int or not 0 <= tick < 600 or state['tick'] != tick or contact['tick'] != tick or
            not math.isclose(world['time_s'], tick*.02, abs_tol=1e-9, rel_tol=0.) or
            state['episode_id'] != case or state['protocol_sha256'] != puck.PROTOCOL_SHA256 or state['reason'] is not None or
            state['previous_puck_xy'] != world['puck_xyz'][:2] or state['previous_rover_xy'] != world['rover_pose'][:2] or
            state['goal_xy'] != world['goal_xy'] or state['previous_distance'] != math.dist(world['puck_xyz'][:2],world['goal_xy']) or
            type(state['had_contact']) is not bool or type(state['dwell_ticks']) is not int or not 0 <= state['dwell_ticks'] <= min(tick,9) or
            type(state['stall_ticks']) is not int or not 0 <= state['stall_ticks'] <= min(tick,99)):
        raise ValueError('Puck cursor/world/contact disagree at paused boundary')
    expected = puck.project(world, contact)
    value = app['inputs']
    if not isinstance(value,np.ndarray) or value.dtype != expected.dtype or value.shape != expected.shape or value.tobytes() != expected.tobytes():
        raise ValueError('Puck snapshot declared input differs from projection')


def snapshot_budget(budget, destination):
    # save_snapshot supplies its exact serialized length before opening the file.
    class Limit:
        def check(self, additional_bytes, *, path):
            if Path(path) != destination or additional_bytes > 8*MiB:
                raise ValueError('Snapshot exceeds fixed 8 MiB bound or destination')
            return budget.check(additional_bytes, path=path)
    return Limit()


def read_bounded_snapshot(path, expected_hash):
    from palimpsest.snapshots import read_snapshot
    if path.is_symlink() or path.stat().st_size > 8*MiB or digest(path) != expected_hash:
        raise ValueError('Snapshot path/size/hash differs')
    with zipfile.ZipFile(path) as archive:
        if sum(x.file_size for x in archive.infolist()) > 8*MiB:
            raise ValueError('Expanded snapshot exceeds 8 MiB')
    return read_snapshot(path)


def accept_root(case, ticks, state, max_displacement, had_contact, displacement):
    name=case['id']
    if name.startswith('teacher-'):
        passed = state['reason'] == 'puck_goal' and 1 <= ticks <= 600
    else:
        passed = ticks == case['ticks'] and state['reason'] is None
        if name == 'zero': passed &= max_displacement <= .001 and not had_contact
        else: passed &= had_contact and displacement[0]*(1 if name=='push-positive' else -1) >= .1
    if not passed:
        raise ValueError('Natural mechanics acceptance failed: ' + name)


def record_estimate(ticks, snapshots):
    if type(ticks) is not int or not 1 <= ticks <= 600 or snapshots not in (1,4):
        raise ValueError('Invalid fixed recording admission')
    return ticks*(128*1024+16*1024)+MiB+8*MiB*snapshots


def safe_owner(current, identity, parent_pid, parent_group):
    return bool(current and current['pid'] == identity['pid'] == identity['process_group'] == current['group'] and
        current['start_ticks'] == identity['start_ticks'] and current['ppid'] == parent_pid and
        current['pid'] not in (parent_pid,parent_group))


def progress_update(receipt, previous, identity, owner_id, start, count):
    required={'pid','start_ticks','process_group','owner','phase','tick'}
    if (set(receipt) != required or any(receipt[k] != identity[k] for k in identity) or receipt['owner'] != owner_id or
            receipt['phase'] not in ('starting','ready') or type(receipt['tick']) is not int or
            not start <= receipt['tick'] <= start+count or
            previous and (receipt['tick'] < previous['tick'] or previous['phase']=='ready' and receipt['phase']!='ready')):
        raise ValueError('Owner progress identity/cursor regressed or differs')
    return receipt


def supervised_owner(command, output, environment, budget, row, start_tick):
    """One bounded_process plus fixed local ancestry/receipt watchdog; no server."""
    from verify_endurance import descendants, process
    from palimpsest.evaluate import bounded_process
    parent, group = os.getpid(), os.getpgrp()
    known, identity, previous, errors, signals = {}, None, None, [], []
    started=time.monotonic(); last=started; ready=False; term_time=None
    baseline={(p['pid'],p['start_ticks']) for p in descendants(parent)}
    with ThreadPoolExecutor(max_workers=1) as executor:
        future=executor.submit(bounded_process,command,output,180,environment,
                               log_max_bytes=MiB,storage_budget=budget)
        while not future.done():
            now=time.monotonic()
            try:
                for proc in descendants(parent):
                    key=(proc['pid'],proc['start_ticks'])
                    if key in baseline: continue
                    if len(known)>=128 and key not in known: raise ValueError('Descendant inventory exceeds 128')
                    known[key]=proc['group']
                    if identity is None and proc['ppid']==parent and proc['pid']==proc['group']:
                        try: argv=Path(f"/proc/{proc['pid']}/cmdline").read_bytes().split(b'\0')
                        except FileNotFoundError: continue
                        if argv == [os.fsencode(value) for value in command]+[b'']:
                            identity={'pid':proc['pid'],'start_ticks':proc['start_ticks'],'process_group':proc['group']}
                progress=output/'progress.json'
                if identity is not None and progress.is_file():
                    receipt=read_json(progress,4096)
                    current=progress_update(receipt,previous,identity,row['id'],start_tick,row['max_ticks'])
                    if current['phase']=='ready' and (not ready or previous is not None and current['tick']>previous['tick']):
                        last=now;ready=True
                    previous=current
                if not ready and now-started>=60 or ready and now-last>=30:
                    raise TimeoutError('Owner startup/progress deadline exceeded')
            except Exception as error:
                if not errors: errors.append({'type':type(error).__name__,'message':str(error)[:1024]})
            if errors and identity is not None:
                current=process(identity['pid'])
                if safe_owner(current,identity,parent,group):
                    sig=signal.SIGTERM if term_time is None else signal.SIGKILL if now-term_time>=3 else None
                    if sig is not None and (not signals or signals[-1]['signal'] != sig.name):
                        try: os.killpg(identity['process_group'],sig)
                        except ProcessLookupError: pass
                        signals.append({'signal':sig.name,'elapsed_seconds':now-started,**identity})
                        if term_time is None: term_time=now
            time.sleep(.1)
        supervision=future.result()
    # A fast successful owner can terminate between polls; bind its final receipt
    # only to an independently sampled direct-child identity (otherwise fail).
    if identity is None: errors.append({'type':'Identity','message':'Owner never independently observed'})
    elif (output/'progress.json').is_file():
        try: previous=progress_update(read_json(output/'progress.json',4096),previous,identity,row['id'],start_tick,row['max_ticks'])
        except Exception as error: errors.append({'type':type(error).__name__,'message':str(error)[:1024]})
    else: errors.append({'type':'Progress','message':'Final owner receipt missing'})
    if previous is None or previous['phase']!='ready':
        errors.append({'type':'Progress','message':'Owner never published a ready boundary'})
    survivors=[p for (pid,start) in known if (p:=process(pid)) and p['start_ticks']==start]
    cleanup=cleanup_check(identity) if identity is not None else {'passed':False}
    return {'supervisor':supervision,'identity':identity,'progress':previous,'errors':errors,'signals':signals,
            'observed':[{'pid':pid,'start_ticks':start,'group':g} for (pid,start),g in sorted(known.items())],
            'survivors':survivors,'cleanup':cleanup,'passed':not errors and not signals and not survivors and
                cleanup['passed'] and supervision['status']=='completed' and supervision['returncode']==0}


def world_from(env, goal):
    extra=env._puck_bindings
    return puck.native_state(env.data, **{k:extra[k] for k in ('base_qpos_adr','puck_qpos_adrs','puck_dof_adrs')},goal_xy=goal)


def world_array(world):
    import numpy as np
    return np.array([world['time_s'],*world['rover_pose'],*world['puck_xyz'],*world['puck_velocity_xy'],*world['goal_xy']],np.float64)


def packet(env, observation, before, after, inputs, action, state, contact, interval, reward, upstream,
           teacher_mode_before, teacher_mode_after, case, *, learning_pending=None):
    import numpy as np
    from palimpsest.body_profile import contact_arrays
    task_state={'state':state,'world':after,'contact':contact,'teacher_mode':teacher_mode_after}
    if learning_pending is not None:
        from palimpsest import puck_learning
        next_cursor=puck_learning.commit(learning_pending['before'],learning_pending,state['tick'])
        if (learning_pending['before']['mode']!=teacher_mode_before or next_cursor['mode']!=teacher_mode_after or
                inputs.tobytes()!=learning_pending['inputs'][:8].tobytes()):
            raise ValueError('Learning record mode/input differs before publication')
        task_state['own_supervisor_cursor']=next_cursor
    arrays={'inputs':inputs, 'action':np.asarray(action,np.float64),
        'teacher_mode_before':np.array(mode_code(teacher_mode_before,case,learning_teacher=learning_pending is not None),np.uint8),
        'teacher_mode_after':np.array(mode_code(teacher_mode_after,case,learning_teacher=learning_pending is not None),np.uint8),
        'world_before':world_array(before),'world_after':world_array(after),
        'reward':np.array(reward,np.float64),'upstream_diagnostics':np.asarray(upstream,np.float64),
        'task_sha256':np.frombuffer(bytes.fromhex(state_digest(task_state)),np.uint8),
        **{name:np.asarray(getattr(env.data,name)).copy() for name in
           ('qpos','qvel','ctrl','qfrc_applied','xfrc_applied')},**contact_arrays(interval)}
    if learning_pending is not None:
        arrays.update(student_inputs=learning_pending['inputs'],
            supervisor_mode_before=np.array(puck_learning.MODES[learning_pending['before']['mode']],np.uint8),
            supervisor_mode_after=np.array(puck_learning.MODES[next_cursor['mode']],np.uint8))
    for name in ('cam_left','cam_right'):
        value=observation[name]
        if value.dtype != np.uint8 or value.shape != (128,128,3): raise ValueError('Wrong actual camera shape/dtype')
        arrays[name]=value
    if any(not np.isfinite(value).all() for value in arrays.values()): raise ValueError('Nonfinite numeric record')
    return arrays


def owner(config):
    from palimpsest.storage import StorageBudget, StorageLimits
    root, output, row=Path(config['repo']),Path(config['output']),config['row']
    spec=protocol(root); task=puck.load_protocol(root)
    learning_teacher='learning_teacher' in config
    source_inventory=teacher_sources if learning_teacher else sources
    own=None
    budget=StorageBudget((output,),StorageLimits(max_bytes=row['max_bytes'],min_free_bytes=1024**3),headroom_bytes=8*MiB)
    identity=process_identity(); start_tick=config.get('start_tick',0)
    def progress(tick,phase='ready'):
        write_json(output/'progress.json',{**identity,'owner':row['id'],'phase':phase,'tick':tick},budget)
    progress(start_tick,'starting')
    result={'status':'running','snapshots':{},'cleanup':[],'finalization_errors':[],
            'qualification_claims':[],'controller_calls':0,'row':row}
    env=writer=probe=model_hash=None; renderers=[]; started=time.monotonic()
    try:
        if source_inventory(root)!=config['sources']: raise ValueError('Sources changed before owner admission')
        if learning_teacher:
            from palimpsest import puck_teacher, puck_learning
            case=puck_teacher.admit_config(config,root)
            own=puck_learning.initial_cursor()
            result.update(ticks=0,completed_control_tick=0,physics_steps_this_owner=0,own_supervisor_cursor=own)
        import numpy as np
        import mujoco as mj
        from palimpsest.flynn import import_upstream
        from palimpsest.body_profile import ContactProbe, effective_control
        from palimpsest.records import RunWriter, iter_ticks
        from palimpsest.snapshots import capture, restore, save_snapshot
        versions={'python':platform.python_version(),'numpy':np.__version__,'mujoco':mj.__version__,'backend':os.environ.get('MUJOCO_GL')}
        if versions!=spec['runtime'] or 'torch' in sys.modules: raise ValueError('Unreviewed native/model runtime')
        if not learning_teacher: case=next(c for c in task['physics_cases'] if c['id']==row['case'])
        cls=import_upstream(root,'environment.mujoco_two_cam_env_random_obstacles').MuJoCoTwoCamEnv
        env=cls(**{**spec['environment_kwargs'],'seed':row['seed']})
        renderers.append(env.renderer)
        identity_profile=puck.install_fixed_model(env,root)
        if identity_profile!=spec['profile_identity']: raise ValueError('Pinned fixed native profile identity differs')
        state=puck.authored_reset(env,root,row['seed'],row['split'] if learning_teacher else 'mechanics',case['id'])
        probe=ContactProbe(mj,env)
        world=world_from(env,case['goal_xy'])
        contact=puck.classify_contacts({'kind':'initial_forwarded','time_s':0.,'pairs':probe._pairs(env.model,env.data)},
                                      probe.ownership,tick=0,time_s=0.)
        observation=env._get_obs()
        model_hash=hashlib.sha256(env.model.__getstate__()).hexdigest()
        expected_rows=None
        if row['kind']=='root':
            teacher_mode='fixed' if 'action' in case else 'approach'
        else:
            source=Path(config['source_output']); receipt=config['source_snapshot']
            snapshot=read_bounded_snapshot(source/receipt['file'],receipt['sha256'])
            validate_application(snapshot['application'],case['id'],start_tick,receipt['application_sha256'])
            app=snapshot['application']
            if app['profile_identity']!=identity_profile or app['model_sha256']!=model_hash:
                raise ValueError('Source puck identity/full model differs from fixed authored destination')
            renderers.append(env.renderer)
            observation,app=restore(snapshot,env)
            bindings,extra=puck._fixed_bindings(env,env.model)
            if extra!=env._puck_bindings or any(not np.array_equal(getattr(env,k),v) for k,v in bindings.items()):
                raise ValueError('Restored named native bindings differ')
            if hashlib.sha256(env.model.__getstate__()).hexdigest()!=model_hash:
                raise ValueError('Restore changed fixed full model')
            state,world,contact=app['state'],app['world'],app['contact']
            teacher_mode=app['teacher_mode']
            if world_from(env,case['goal_xy'])!=world or env._t!=start_tick: raise ValueError('Restored current qpos/cursor differs')
            probe=ContactProbe(mj,env)
            source_rows=list(iter_ticks(source/'recording'))
            expected_rows=window(source_rows,start_tick,config['ticks'])
            result['source_snapshot']=receipt
        def application():
            if learning_teacher:
                return puck_teacher.initial_application(root,row,config['sources'],identity_profile,model_hash,
                                                         state,world,contact,own)
            return {'version':2,'gate_protocol_sha256':PROTOCOL_SHA256,'case':case['id'],
                    'teacher_mode':teacher_mode,
                    'profile_identity':identity_profile,'model_sha256':model_hash,'state':copy.deepcopy(state),
                    'world':copy.deepcopy(world),'contact':copy.deepcopy(contact),'inputs':puck.project(world,contact),'paused':True}
        def snapshot_at(name):
            writer.flush()
            app=application(); app_hash=state_digest(app)
            if learning_teacher:
                if name!='initial': raise ValueError('Learning teacher admits initial-only snapshots')
                puck_teacher.validate_initial(app,root,row,config['sources'],identity_profile,model_hash,app_hash)
            else: validate_application(app,case['id'],state['tick'],app_hash)
            if mj.get_mjcb_control() is not None: raise ValueError('Snapshot while global callback active')
            snap=capture(env,observation,application=app)
            path=output/(name+'.snp')
            size=save_snapshot(snap,path,storage_budget=snapshot_budget(budget,path))
            result['snapshots'][name]={'file':path.name,'sha256':digest(path),'bytes':size,'tick':state['tick'],
                'application_sha256':app_hash,'world':world,'contact':contact}
            writer.event('paused_snapshot',name=name,**result['snapshots'][name])
        manifest={'schema':'puck-mechanics-v2','protocol_sha256':PROTOCOL_SHA256,
            'pushing_protocol_sha256':puck.PROTOCOL_SHA256,'row':row,'source':config.get('source_snapshot'),
            'source_hashes':config['sources'],'profile_identity':identity_profile,'full_model_sha256':model_hash,
            'contact_ownership':probe.ownership,'record_contract':spec['recording']}
        start_event={'episode':0,'seed':row['seed'],'state':state,'world':world,'contact':contact,'teacher_mode':teacher_mode}
        if learning_teacher:
            manifest.update(schema='puck-demonstration-v1',**puck_teacher.identity(root),seed=row['seed'],
                            split=row['split'],episodes=1,initial_supervisor=own,
                            record_contract=puck_learning.load_protocol(root)['record'])
            start_event['supervisor_cursor']=own
        writer=RunWriter(output/'recording',manifest,max_bytes=row['max_bytes'],storage_budget=budget)
        writer.event('episode_start',**start_event)
        snapshot_at('initial')
        count=config.get('ticks',row['max_ticks'])
        estimate=record_estimate(count,4 if case['id']=='teacher-positive' and row['kind']=='root' else 1)
        budget.check(estimate,path=output/'recording')
        result['record_admission_estimate_bytes']=estimate
        progress(state['tick'])
        origin=list(state['initial_puck_xy']); max_displacement=math.dist(world['puck_xyz'][:2],origin)
        for index in range(count):
            if state['reason'] is not None: break
            before=world; inputs=puck.project(before,contact)
            reference=None if expected_rows is None else expected_rows[index]
            mode_before=teacher_mode
            pending=None
            if learning_teacher:
                result['controller_calls']+=1
                try: action,next_mode,pending=puck_teacher.decide(inputs,before,mode_before,own)
                except puck_teacher.SensorModeDisagreement as error:
                    result['mode_disagreement']=error.evidence
                    writer.event('sensor_mode_disagreement',**error.evidence)
                    raise
            else: action,next_mode=action_for({**row,**case},before,mode_before,reference)
            if len(action)!=2 or any(type(v) not in (int,float) or not math.isfinite(v) or abs(v)>.4 for v in action):
                raise ValueError('Command exceeds frozen task bounds before control')
            if not learning_teacher and row['kind']!='action-replay' and 'action' not in case: result['controller_calls']+=1
            control=effective_control(action)
            probe.install();probe.begin(state['tick'])
            try:
                next_observation,nav_reward,nav_done,nav_truncated,nav_info=env.step(action)
                if learning_teacher:
                    result.update(last_native_completed_tick=env._t,data_time_s=float(env.data.time))
                interval=probe.end()
            finally: probe.close()
            if list(env.data.ctrl)!=control: raise ValueError('Actual wheel control differs from fixed converter')
            world=world_from(env,case['goal_xy'])
            # Upstream diagnostic obstacle cache follows current qpos, never the reverse.
            env._obstacle_xy[0]=np.asarray(world['puck_xyz'][:2],np.float32)
            contact=puck.classify_contacts(interval,probe.ownership,tick=state['tick']+1,time_s=world['time_s'])
            state,reward=puck.advance(state,world,contact,action)
            if not learning_teacher: teacher_mode=next_mode
            arrays=packet(env,observation,before,world,inputs,action,state,contact,interval,reward,
                          [nav_reward,bool(nav_done),bool(nav_truncated),nav_info['dist_to_goal'],bool(nav_info['stalled'])],
                          mode_before,next_mode,case['id'],learning_pending=pending)
            if sum(a.nbytes for a in arrays.values())>128*1024:
                raise ValueError('Numeric row exceeds preflight allowance')
            event={'state':state,'world':world,'contact':contact,'reward':reward,
                   'teacher_mode_before':mode_before,'teacher_mode_after':next_mode}
            if learning_teacher:
                next_own=puck_learning.commit(own,pending,state['tick'])
                event.update(supervisor_mode_before=own['mode'],supervisor_mode_after=next_own['mode'])
            if len(json.dumps(event,allow_nan=False).encode())>16*1024:
                raise ValueError('Interval event exceeds preflight allowance')
            writer.tick(0,state['tick']-1,**arrays)
            writer.event('puck_interval',**event)
            if learning_teacher:
                own=next_own;teacher_mode=next_mode
                result.update(ticks=state['tick'],completed_control_tick=state['tick'],
                              physics_steps_this_owner=state['tick']*10,own_supervisor_cursor=own)
            observation=next_observation
            max_displacement=max(max_displacement,math.dist(world['puck_xyz'][:2],origin))
            if reference is not None: same_row(reference,{'episode':0,'tick':state['tick']-1,**arrays})
            if row['kind']=='root' and case['id']=='teacher-positive' and state['reason'] is None:
                for name in boundaries(state,contact,result['snapshots']): snapshot_at(name)
            progress(state['tick'])
        ticks=state['tick']-start_tick
        result.update(ticks=ticks,final_state=state,final_world=world,final_teacher_mode=teacher_mode,max_puck_displacement_m=max_displacement,
                      profile_identity=identity_profile,full_model_sha256=model_hash,
                      completed_control_tick=state['tick'],data_time_s=float(env.data.time),
                      physics_steps_this_owner=ticks*10)
        completion=state['reason'] or ('continuation_window_complete' if row['kind']=='native-continuation' else 'fixed_mechanics_horizon')
        result['completion']=completion
        writer.finish({'outcome':state['reason'],'completion':completion,'final_state':state,'teacher_mode':teacher_mode,'ticks':ticks})
        if learning_teacher:
            if state['reason'] is None: raise ValueError('Teacher stopped without natural task outcome')
        elif row['kind']=='root':
            accept_root(case,ticks,state,max_displacement,state['had_contact'],[world['puck_xyz'][i]-origin[i] for i in range(2)])
            if case['id']=='teacher-positive':
                if set(result['snapshots'])!={'initial','tick1','contact','dwell'}: raise ValueError('Required first snapshot boundary absent')
                for name in ('tick1','contact','dwell'): window(list(iter_ticks(output/'recording')),result['snapshots'][name]['tick'],4)
        elif ticks!=count: raise ValueError('Replay/continuation stopped before exact source window')
        if 'torch' in sys.modules: raise ValueError('Unexpected model import')
        result['status']='passed'
    except Exception as error:
        result.update(status='failed',error={'type':type(error).__name__,'message':str(error)[:4096]})
        if probe is not None:
            result['last_contact_probe']={'count':probe.count,'stages':probe.stages,'violations':probe.violations}
    finally:
        if probe is not None:
            try: probe.close()
            except Exception as error: result['finalization_errors'].append('callback: '+str(error)[:1024])
        if writer is not None:
            try: writer.close()
            except Exception as error: result['finalization_errors'].append('record: '+str(error)[:1024])
        if env is not None:
            try:
                result['full_model_sha256_at_end']=hashlib.sha256(env.model.__getstate__()).hexdigest()
                result['full_model_unchanged']=model_hash is not None and result['full_model_sha256_at_end']==model_hash
                if model_hash is not None and not result['full_model_unchanged']: raise ValueError('Fixed model changed during mechanics')
            except Exception as error: result['finalization_errors'].append('model: '+str(error)[:1024])
            try:
                env.data.ctrl[:]=0.  # Terminal halt after the immutable final record/snapshot.
            except Exception as error: result['finalization_errors'].append('halt: '+str(error)[:1024])
            renderers.append(env.renderer)
        seen=set()
        for renderer in renderers:
            if id(renderer) in seen: continue
            seen.add(id(renderer)); receipt={'closed':False}
            try:
                if renderer._gl_context is not None or renderer._mjr_context is not None: renderer.close()
                receipt['closed']=renderer._gl_context is None and renderer._mjr_context is None
                if not receipt['closed']: raise ValueError('Renderer context survived close')
            except Exception as error: result['finalization_errors'].append('renderer: '+str(error)[:1024])
            result['cleanup'].append(receipt)
        if env is not None:
            try:
                env.close()
                if env.window is not None or env._view_ctx is not None: raise ValueError('Unexpected native view resource')
            except Exception as error: result['finalization_errors'].append('environment: '+str(error)[:1024])
        try:
            result['sources_unchanged']=source_inventory(root)==config['sources']
            if not result['sources_unchanged']: raise ValueError('Frozen sources changed')
        except Exception as error: result['finalization_errors'].append('sources: '+str(error)[:1024])
        try:
            result['callback_restored']='mujoco' not in sys.modules or sys.modules['mujoco'].get_mjcb_control() is None
            if not result['callback_restored']: raise ValueError('Global callback survived')
        except Exception as error: result['finalization_errors'].append('callback audit: '+str(error)[:1024])
        result['elapsed_seconds']=time.monotonic()-started
        if result['finalization_errors']: result['status']='failed'
        write_json(output/'result.json',result,budget)
    return 0 if result['status']=='passed' else 1


def inventory(output):
    files=[p for p in sorted(output.rglob('*')) if p.is_file() and p.name!='.palimpsest-storage.lock']
    if len(files)>4096 or any(p.is_symlink() for p in files): raise ValueError('Retained file inventory outside bound')
    return {str(p.relative_to(output)):{'sha256':digest(p),'bytes':p.stat().st_size} for p in files}


def main(args):
    from palimpsest.storage import StorageBudget, StorageLimits, _safe_path
    from palimpsest.records import iter_ticks
    root,output,retained=args.repo.resolve(),_safe_path(args.output),_safe_path(args.retention_root)
    if Path(__file__).resolve()!=root/'scripts/verify_puck_mechanics.py': raise ValueError('Wrong verifier checkout')
    if output.exists() or not output.is_relative_to(retained): raise ValueError('Fresh output inside declared retention root required')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True,timeout=5).strip()
    if commit!=args.expected_commit: raise ValueError('Frozen source HEAD differs')
    subprocess.run(['git','diff','--exit-code','HEAD'],cwd=root,check=True,capture_output=True,timeout=5)
    spec=protocol(root); task=puck.load_protocol(root); rows=plan(task)
    if [r['id'] for r in rows]!=spec['owner_order']: raise ValueError('Owner order differs from reviewed protocol')
    upstream=root/'upstream/fly-gym'
    if subprocess.check_output(['git','rev-parse','HEAD'],cwd=upstream,text=True,timeout=5).strip()!=spec['upstream_commit']:
        raise ValueError('Pinned upstream revision differs')
    subprocess.run(['git','diff','--exit-code','HEAD'],cwd=upstream,check=True,capture_output=True,timeout=5)
    frozen=sources(root); started=time.monotonic(); limits=task['limits']
    budget=StorageBudget((output,),StorageLimits(max_bytes=limits['physics']['bytes'],min_free_bytes=1024**3,
                        max_runs=10,max_snapshots=4),headroom_bytes=8*MiB)
    retention=StorageBudget((retained,),StorageLimits(max_bytes=limits['total_retained_bytes'],min_free_bytes=1024**3))
    report={'status':'running','commit':commit,'protocol_sha256':PROTOCOL_SHA256,'protocol':spec,'sources':frozen,
            'owners':[{**row,'status':'not_started'} for row in rows],'qualification_claims':[],'finalization_errors':[]}
    completed={}; immutable={}
    with budget.lock():
        try:
            allowance=sum(r['max_bytes'] for r in rows)
            budget.check(allowance,path=output); retention.check(allowance+8*MiB,path=output)
            report['full_plan_admission_bytes']=allowance
            write_json(output/'report.json',report,budget)
            child_env={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','MPLBACKEND':'Agg',
                       'OMP_NUM_THREADS':'2','OPENBLAS_NUM_THREADS':'2','MKL_NUM_THREADS':'2'}
            for index,item in enumerate(report['owners']):
                if time.monotonic()-started+180>600: raise TimeoutError('Insufficient internal budget for another full owner')
                for name,previous in immutable.items():
                    if inventory(output/name)!=previous: raise ValueError('Prior owner evidence changed: '+name)
                remaining=sum(r['max_bytes'] for r in rows[index:])
                budget.check(remaining,path=output); retention.check(remaining+8*MiB,path=output)
                row=rows[index]; child_output=output/row['id']; start_tick=0
                config={'repo':str(root),'output':str(child_output),'row':row,'sources':frozen}
                if row['kind']!='root':
                    source=completed[row['case']]; receipt=source['result']['snapshots'][row['boundary']]
                    start_tick=receipt['tick']
                    count=row['max_ticks'] if row['kind']!='policy-replay' else source['result']['ticks']
                    window(list(iter_ticks(output/row['case']/'recording')),start_tick,count)
                    config.update(source_output=str(output/row['case']),source_snapshot=receipt,start_tick=start_tick,ticks=count)
                item.update(status='running',output=str(child_output));write_json(output/'report.json',report,budget)
                command=[sys.executable,str(Path(__file__).resolve()),'--child',json.dumps(config,separators=(',',':'))]
                item['supervision']=supervised_owner(command,child_output,child_env,budget,row,start_tick)
                item['status']='failed'
                if (child_output/'result.json').is_file():
                    item['result']=read_json(child_output/'result.json');item['result_sha256']=digest(child_output/'result.json')
                if not item['supervision']['passed'] or item.get('result',{}).get('status')!='passed':
                    raise RuntimeError(row['id']+': owner/mechanics/watchdog/cleanup failure')
                manifest=read_json(child_output/'recording/manifest.json')
                actual=list(iter_ticks(child_output/'recording'))
                window(actual,start_tick,item['result']['ticks'])
                if manifest['status']!='completed' or len(actual)!=item['result']['ticks']:
                    raise ValueError('Completed recording coverage differs')
                if row['kind']!='root':
                    reference=window(list(iter_ticks(output/row['case']/'recording')),start_tick,len(actual))
                    for a,b in zip(reference,actual): same_row(a,b)
                    item['exact_source_rows']=len(actual)
                item['status']='passed';completed[row['id']]=item;immutable[row['id']]=inventory(child_output)
                write_json(output/'report.json',report,budget)
            report['status']='passed'
        except Exception as error:
            report.update(status='failed',error={'type':type(error).__name__,'message':str(error)[:4096]})
            for item in report['owners']:
                if item['status']=='running':
                    item.update(status='failed',parent_error=report['error'])
        finally:
            try:
                report['sources_unchanged']=sources(root)==frozen
                if not report['sources_unchanged']: raise ValueError('Frozen source inventory changed')
            except Exception as error: report['finalization_errors'].append('sources: '+str(error)[:1024])
            try:
                report['prior_owner_evidence_unchanged']=all(inventory(output/name)==old for name,old in immutable.items())
                if not report['prior_owner_evidence_unchanged']: raise ValueError('Previously completed owner evidence changed')
            except Exception as error: report['finalization_errors'].append('immutable evidence: '+str(error)[:1024])
            try:
                report['retained_inventory']={k:v for k,v in inventory(output).items() if k!='report.json'}
                report['storage']=budget.check(0,path=output);report['retention_storage']=retention.check(0,path=output)
            except Exception as error: report['finalization_errors'].append('inventory/storage: '+str(error)[:1024])
            if report['finalization_errors']: report['status']='failed'
            report['elapsed_seconds']=time.monotonic()-started
            write_json(output/'report.json',report,budget)
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--child': raise SystemExit(owner(json.loads(sys.argv[2])))
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--expected-commit',required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--retention-root',type=Path,required=True)
    raise SystemExit(main(parser.parse_args()))
