"""TGT-PHASE-1: bounded native task-phase continuation, development only."""
import argparse
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import threading
import time
import uuid

from verify_tasks import (SCENARIOS, DRIVERS, cue_action, previous_bearing, command,
                          evaluator_sample, evaluator_record, evaluate_motion,
                          completion_passed, task_completed, compare_tick, file_hashes)
from verify_body_gains import write_json
from verify_body_runtime import digest
from verify_body_adaptation import read_json, cleanup_observed, snapshot_path
from verify_endurance import source_identity, descendants

MiB = 1024**2
PHASES = {SCENARIOS[0]: ('selected', 'first-dwell', 'second-dwell'),
          SCENARIOS[1]: ('outbound', 'home-turn', 'home-dwell')}
PROTOCOL = {'id': 'TGT-PHASE-1', 'version': 1, 'seed': 0,
    'drivers': {SCENARIOS[0]: DRIVERS['v1'], SCENARIOS[1]: DRIVERS['v2']},
    'predicates': {
        'selected': 'first paused boundary: active target, no completed IDs, dwell0, encoder travel>0',
        'first-dwell': 'first paused boundary: active target, no completed IDs, dwell1',
        'second-dwell': 'first paused boundary: active target, exactly one completed ID, dwell1',
        'outbound': 'paused boundary after exactly8 numeric ticks, phase outbound, encoder travel>0',
        'home-turn': 'first paused home boundary, dwell0, previous effective bearing requests v2 in-place turn',
        'home-dwell': 'first paused home boundary with dwell1'},
    'continuation': 'next up to4 set_action/step pairs from unchanged previous-bearing driver; stop only at legitimate task completion; compare identical IDs/actions, raw numeric cameras/task/outcome/evaluator',
    'controller': 'manual', 'device': 'cpu', 'texture': 'checker',
    'source_max_ticks': 600, 'successor_max_commands': 4, 'owners': 12,
    'maximum_numeric_ticks': 3624, 'snapshot_files': 18, 'snapshots_per_run': 4,
    'snapshot_max_bytes': 16*MiB, 'recording_max_bytes': 256*MiB,
    'output_max_bytes': 2048*MiB, 'min_free_bytes': 1024*MiB,
    'child_timeout_seconds': 180, 'outer_timeout_seconds': 2280,
    'result_max_bytes': 64*MiB, 'report_max_bytes': MiB, 'log_max_bytes': MiB,
    'storage_headroom_bytes': 8*MiB, 'float_atol': 1e-6, 'float_rtol': 1e-6,
    'cameras_and_integers': 'exact', 'truth_feedback': False,
    'scope': 'fixed authored world/manual development lifecycle fixture; no held-out, learned-policy, exact body rest or physical claim'}
PROTOCOL_SHA256 = hashlib.sha256(json.dumps(PROTOCOL, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
OWNERS = [(scenario, mode) for scenario in SCENARIOS
          for mode in ('source', *PHASES[scenario], 'actions', 'policy')]


def phase_matches(name, state, transition, tick):
    """Snapshot scheduling only. Never supplies an input to the driver."""
    if state['phase'] == 'explore':
        active, completed, dwell = state['active'], len(state['completed_ids']), state['dwell_ticks']
        return ((name == 'selected' and active is not None and completed == 0 and dwell == 0 and state['odometry']['travel_m'] > 0.) or
                (name == 'first-dwell' and active is not None and completed == 0 and dwell == 1) or
                (name == 'second-dwell' and active is not None and completed == 1 and dwell == 1))
    if name == 'outbound':
        return tick == 8 and state['phase'] == 'outbound' and state['odometry']['travel_m'] > 0.
    if state['phase'] != 'home':
        return False
    if name == 'home-dwell':
        return state['dwell_ticks'] == 1
    action = cue_action(previous_bearing(transition), driver='v2')
    return name == 'home-turn' and state['dwell_ticks'] == 0 and action[0] == 0. and abs(action[1]) > .1


def valid_window(items):
    if not 1 <= len(items) <= 4:
        raise ValueError('Phase window must contain one to four actual successor commands')
    for index, item in enumerate(items):
        if item['state']['phase'] != 'paused' and (index != len(items)-1 or not task_completed(item['state'])):
            raise ValueError('Unexpected early outcome in phase window')
    if len(items) < 4 and not task_completed(items[-1]['state']):
        raise ValueError('Short window requires legitimate task completion')


def storage(config, *, control=False):
    from palimpsest.storage import StorageBudget, StorageLimits
    value = config['storage']
    return StorageBudget(tuple(Path(p) for p in value['roots']), StorageLimits(**value['limits']),
                         headroom_bytes=0 if control else value['headroom_bytes'])


def output_json(path, value, config, *, control=False, maximum=MiB):
    write_json(path, value, max_bytes=maximum, storage_budget=storage(config, control=control))


def harness_hashes():
    return {name: digest(Path(__file__).with_name(name)) for name in
            ('verify_task_phases.py', 'verify_tasks.py', 'verify_body_adaptation.py',
             'verify_body_runtime.py', 'verify_body_gains.py', 'verify_body_compensation.py',
             'verify_body_calibration.py', 'verify_endurance.py')}


def preflight(observation):
    import numpy as np
    cameras = [observation[key] for key in ('cam_left', 'cam_right')]
    if any(a.dtype != np.uint8 or a.shape != (128, 128, 3) for a in cameras):
        raise ValueError('Task gate requires actual uint8 128x128 cameras')
    per_tick = 2*sum(a.nbytes for a in cameras) + 8192  # effective + raw cameras, numeric/task/event allowance
    per_run = 600*per_tick + 2*MiB
    if per_run > PROTOCOL['recording_max_bytes']:
        raise ValueError('Actual camera recording estimate exceeds per-run quota')
    allowances = {'numeric_bytes': 3624*per_tick, 'snapshot_bytes': 18*16*MiB,
                  'row_results_bytes': 12*64*MiB, 'native_logs_bytes': 26*MiB,
                  'control_results_bytes': 32*MiB, 'atomic_native_staging_bytes': 128*MiB,
                  'supervisor_headroom_bytes': 8*MiB}
    total = sum(allowances.values())
    if total > PROTOCOL['output_max_bytes']:
        raise ValueError('Actual camera/snapshot/control/log estimate exceeds aggregate quota')
    return {'per_tick_bytes': per_tick, 'per_recording_bytes': per_run,
            'aggregate_bytes': total, 'allowances': allowances}


def initial_ready(run, stage, state=None):
    # Published under the aggregate budget. Validate before the first numeric step.
    if stage == 'ready':
        snapshot_path(Path(run)/'snapshots/initial.snp')


def successor(engine, driver, *, recorded_action=None):
    tick = engine.episode_step
    action = (cue_action(previous_bearing(engine.last_transition), driver=driver)
              if recorded_action is None else list(recorded_action))
    before = evaluator_sample(engine)
    command(engine, f'action-{tick}', 'set_action', {'action': action})
    command(engine, f'step-{tick}', 'step')
    # Isolated evaluator origin is fixed world start and cannot enter cue_action.
    from palimpsest.memory_world import START_POSE
    evaluation = evaluator_record(engine, before, evaluator_sample(engine), START_POSE, action)
    return {'tick': tick, 'requested_action': action, 'task': copy.deepcopy(engine.task_state),
            'state': {'phase': engine.phase, 'task': copy.deepcopy(engine.task_state),
                      'last_outcome': copy.deepcopy(engine.last_outcome)}, 'evaluator': evaluation}


def worker(config):
    from palimpsest.engine import Engine
    from palimpsest.replay import _register_initial, replay_run, _same_json
    from palimpsest.snapshots import capture, save_snapshot, read_snapshot
    stage, run = Path(config['stage']), Path(config['run'])
    scenario, mode = config['scenario'], config['mode']
    driver = 'v1' if scenario == SCENARIOS[0] else 'v2'
    budget = storage(config); engine = None; rows = []; windows = {}
    result = {'status': 'running', 'run': str(run), 'mode': mode, 'scenario': scenario}
    try:
        run.mkdir(exist_ok=False)
        if mode in ('actions', 'policy'):
            replay = replay_run(Path(config['source']), run, mode=mode,
                repo_root=Path(config['repo']), asset_root=Path(config['assets']), storage_budget=budget,
                recording_max_bytes=PROTOCOL['recording_max_bytes'],
                progress=lambda stage,state=None: initial_ready(run,stage,state))
            result.update(status=replay['status'], compared_ticks=replay['compared_ticks'], engine_closed=True)
            if replay['status'] != 'passed' or replay['compared_ticks'] != config['source_ticks']:
                raise ValueError('Executable replay did not compare all source ticks')
        else:
            engine = Engine.open(Path(config['repo']), Path(config['assets']), run/'recording',
                controller='manual', device='cpu', seed=0, scenario=scenario, texture='checker',
                run_id=run.name, max_bytes=PROTOCOL['recording_max_bytes'], storage_budget=budget)
            engine.writer.event('task_phase_verifier_protocol', protocol=PROTOCOL, protocol_sha256=PROTOCOL_SHA256,
                                harness_sha256=harness_hashes())
            if mode == 'source':
                result['preflight'] = admission = preflight(engine.observation)
                # Reserve the whole plan once; later sources admit only their own remaining writes.
                requested = (admission['aggregate_bytes'] if config['aggregate_preflight'] else
                             admission['per_recording_bytes'] + 4*16*MiB + 4*MiB)
                budget.check(requested, path=run)
                _register_initial(engine, run, budget)
                initial_ready(run, 'ready')
                snapshots = {}
                result['snapshots'] = snapshots
                for _ in range(600):
                    item = successor(engine, driver); rows.append(item)
                    for name, items in windows.items():
                        if len(items) < 4 and (not items or items[-1]['state']['phase'] == 'paused'):
                            items.append(copy.deepcopy(item))
                    if engine.phase != 'paused':
                        break
                    for name in PHASES[scenario]:
                        if name not in windows and phase_matches(name, engine.task_state, engine.last_transition, engine.episode_step):
                            engine.writer.flush()
                            snp = capture(engine.env, engine.observation, application=engine.application_state())
                            path = stage/(name+'.snp')
                            save_snapshot(snp, path, storage_budget=budget)
                            snapshot_path(path)
                            snapshots[name] = {'path': str(path), 'sha256': digest(path),
                                'tick': engine.episode_step, 'task': copy.deepcopy(engine.task_state)}
                            windows[name] = []
                result.update(final_state=engine.public_state(), recorded_ticks=len(rows),
                              motion=evaluate_motion([r['evaluator'] for r in rows],engine.task_state['odometry']['calibration']))
                if set(windows) != set(PHASES[scenario]):
                    raise ValueError('Source did not reach every prospective phase predicate')
                for items in windows.values():
                    valid_window(items)
                if not completion_passed(engine.public_state(), driver=driver):
                    raise ValueError('Source task/actual-home completion gate failed')
                result['status'] = 'passed'
            else:
                snp = read_snapshot(snapshot_path(config['snapshot'], config['snapshot_sha256']))
                engine.restore_branch(snp)
                _same_json(snp['application']['task_state'], engine.task_state, 'initial_restored_task')
                _register_initial(engine, run, budget)
                initial_ready(run, 'ready')
                expected = read_json(config['window'], maximum=64*MiB)
                valid_window(expected)
                for item in expected:
                    if engine.episode_step != item['tick'] or engine.phase != 'paused':
                        raise ValueError('Restored successor cursor/phase differs')
                    actual = successor(engine, driver, recorded_action=item['requested_action']); rows.append(actual)
                    _same_json(item, actual, 'successor_state_outcome_evaluator')
                result.update(status='passed', recorded_ticks=len(rows), final_state=engine.public_state())
    except Exception as error:
        result.update(status='failed', error={'type': type(error).__name__, 'message': str(error)[:1024]})
    finally:
        if engine is not None:
            try:
                result['raw_boundary'] = {'task': copy.deepcopy(engine.task_state), 'state': engine.public_state()}
                import numpy as np
                cameras = {key: engine.observation[key] for key in ('cam_left','cam_right')}
                if any(a.dtype != np.uint8 or a.shape != (128,128,3) for a in cameras.values()):
                    raise ValueError('Raw boundary camera shape/dtype differs')
                buffer = io.BytesIO(); np.savez(buffer, **cameras)
                payload = buffer.getvalue()
                if len(payload)>MiB:
                    raise ValueError('Raw boundary cameras exceed1MiB')
                path = stage/'boundary-cameras.npz'; budget.check(len(payload),path=path)
                with path.open('xb') as stream:
                    stream.write(payload)
                result['raw_boundary_cameras_sha256'] = digest(path)
            except Exception as error:
                result.update(status='failed',diagnostic_error=str(error)[:512])
            finally:
                try:
                    engine.close(); result['engine_closed'] = True
                except Exception as error:
                    result.update(status='failed', cleanup_error=str(error)[:512])
        output_json(stage/'rows.json', rows, config, maximum=64*MiB)
        for name, items in windows.items():
            output_json(stage/(name+'-window.json'), items, config)
        output_json(stage/'result.json', result, config)
    return result['status'] == 'passed'


def inventory(output):
    shots = list(output.rglob('*.snp'))
    runs = list(output.glob('*/*/*/recording/manifest.json'))
    if len(shots) > 18 or len(runs) > 12:
        raise ValueError('Snapshot/owner inventory exceeds prospective bound')
    for path in shots:
        snapshot_path(path)
    return {'snapshot_files': len(shots), 'runs': len(runs)}


def gate(config):
    from palimpsest.evaluate import bounded_process
    from palimpsest.assets import verify_assets
    from palimpsest.records import iter_ticks
    from palimpsest.artifacts import _events
    from palimpsest.replay import _same_json
    root, output = Path(config['repo']), Path(config['output'])
    report = read_json(output/'report.json'); budget = storage(config)
    started = time.monotonic(); numeric = 0
    try:
        report['assets_before'] = verify_assets(root, Path(config['assets']))
        if not report['assets_before']['ok']:
            raise ValueError('Pinned assets unavailable')
        environment = {**os.environ, 'PYTHONPATH': str(root/'src'), 'MUJOCO_GL': 'egl', 'MPLBACKEND': 'Agg', 'OMP_NUM_THREADS': '2'}
        for scenario in SCENARIOS:
            base = output/scenario; base.mkdir()
            source = None; immutable = None; source_rows = None
            for mode in ('source', *PHASES[scenario], 'actions', 'policy'):
                budget.check_count('runs', len(list(output.glob('*/*/*/recording/manifest.json'))))
                stage = base/mode
                child = {**config, 'scenario': scenario, 'mode': mode, 'stage': str(stage),
                         'run': str(stage/uuid.uuid4().hex),
                         'aggregate_preflight': scenario == SCENARIOS[0] and mode == 'source'}
                if source is not None:
                    child.update(source=source['run'], source_ticks=source['recorded_ticks'])
                if mode in PHASES[scenario]:
                    snp = source['snapshots'][mode]
                    child.update(snapshot=snp['path'], snapshot_sha256=snp['sha256'],
                                 window=str(base/'source'/(mode+'-window.json')))
                key = scenario+'/'+mode
                supervision = bounded_process([sys.executable, str(Path(__file__).resolve()), '--worker', json.dumps(child)],
                    stage,180,environment,log_max_bytes=MiB,storage_budget=budget)
                item = report['workers'][key] = {'status':'failed', 'supervision':supervision}
                if (stage/'result.json').exists():
                    item['result'] = data = read_json(stage/'result.json')
                    item['result_sha256'] = digest(stage/'result.json')
                else:
                    raise ValueError(key+' missing retained result')
                if supervision['status']!='completed' or data['status']!='passed' or data.get('engine_closed') is not True:
                    raise ValueError(key+' failed; inspect retained result/logs')
                run = Path(data['run']); records = list(iter_ticks(run/'recording'))
                count = data.get('recorded_ticks',data.get('compared_ticks'))
                if len(records)!=count or count> (4 if mode in PHASES[scenario] else 600):
                    raise ValueError(key+' numeric coverage differs')
                numeric += count
                if numeric>3624:
                    raise ValueError('Aggregate numeric ceiling exceeded')
                if read_json(run/'recording/manifest.json')['status']!='completed':
                    raise ValueError(key+' recording incomplete')
                if mode=='source':
                    source=data; source_rows=records; immutable=file_hashes(run)
                else:
                    if mode in PHASES[scenario]:
                        expected=read_json(child['window'],maximum=64*MiB)
                        actual=read_json(stage/'rows.json',maximum=64*MiB)
                        left=[row for row in source_rows if source['snapshots'][mode]['tick']<=int(row['tick'])<source['snapshots'][mode]['tick']+len(expected)]
                        if not len(left)==len(records)==len(expected)==len(actual):
                            raise ValueError('Native continuation window coverage differs')
                        for a,b,c,d in zip(left,records,expected,actual):
                            compare_tick(a,b,c['task'],d['task'])
                        start=source['snapshots'][mode]['tick']
                        packets=lambda path:[e['packet'] for e in _events(path) if e['kind']=='task_sensed' and start<=e['episode_step']<start+len(expected)]
                        source_packets, restored_packets=packets(Path(source['run'])),packets(run)
                        if len(source_packets)!=len(expected) or len(restored_packets)!=len(expected):
                            raise ValueError('Raw task packet continuation coverage differs')
                        _same_json(source_packets,restored_packets,'raw_task_packets')
                        item['native_continuation']={'ticks':len(records),'raw_task_packets':'matched',
                            'task_outcome_evaluator':'matched','numeric_cameras':'matched',
                            'early_task_completed':len(records)<4}
                    if immutable!=file_hashes(Path(source['run'])):
                        raise ValueError('Immutable source recording changed')
                    for snp in source['snapshots'].values():
                        snapshot_path(snp['path'],snp['sha256'])
                item['status']='passed'; report['numeric_ticks']=numeric
                item['numeric_ticks']=count
                report['inventory']=inventory(output)
                output_json(output/'report.json',report,config,control=True)
        if inventory(output)!={'snapshot_files':18,'runs':12}:
            raise ValueError('Final exact snapshot/run counts differ')
        report['status']='passed'
    except Exception as error:
        report.update(status='failed',error={'type':type(error).__name__,'message':str(error)[:1024]})
    finally:
        report['assets_after']=verify_assets(root,Path(config['assets']))
        report['assets_unchanged']=report.get('assets_before')==report['assets_after']
        if not report['assets_unchanged']:
            report['status']='failed'
        report['gate_wall_seconds']=time.monotonic()-started
        output_json(output/'report.json',report,config,control=True)
    return report['status']=='passed'


def verify(args):
    from dataclasses import asdict
    from palimpsest.storage import StorageBudget, StorageLimits
    from palimpsest.evaluate import bounded_process
    root, assets, output = args.repo.resolve(),args.assets.resolve(),args.output.resolve()
    if assets.is_relative_to(output) or output.is_relative_to(assets):
        raise ValueError('Assets must be outside managed output')
    output.mkdir(parents=True,exist_ok=False)
    limits=StorageLimits(max_bytes=2048*MiB,min_free_bytes=1024*MiB,max_runs=12,max_snapshots=4,max_exports=1)
    budget=StorageBudget((output,),limits,headroom_bytes=8*MiB)
    config={'repo':str(root),'assets':str(assets),'output':str(output),
            'storage':{'roots':[str(output)],'limits':asdict(limits),'headroom_bytes':budget.headroom_bytes}}
    report={'status':'running','protocol':PROTOCOL,'protocol_sha256':PROTOCOL_SHA256,
            'runtime_source':source_identity(root),'harness_sha256':harness_hashes(),
            'workers':{s+'/'+m:{'status':'not_started'} for s,m in OWNERS}}
    observed={}; errors=[]; stop=threading.Event()
    def sample():
        try:
            while not stop.is_set():
                for row in descendants(os.getpid()):
                    if row['pid'] not in observed and len(observed)>=256:
                        raise ValueError('Owned process sample exceeds256 identities')
                    observed[row['pid']]=row['start_ticks']
                stop.wait(.25)
        except Exception as error:
            errors.append(str(error)[:512]); stop.set()
    sampler=threading.Thread(target=sample,daemon=True); started=time.monotonic()
    with budget.lock():
        output_json(output/'report.json',report,config,control=True); sampler.start()
        try:
            environment={**os.environ,'PYTHONPATH':str(root/'src'),'MUJOCO_GL':'egl','MPLBACKEND':'Agg','OMP_NUM_THREADS':'2'}
            supervision=bounded_process([sys.executable,str(Path(__file__).resolve()),'--gate',json.dumps(config)],
                output/'outer-supervision',2280,environment,log_max_bytes=MiB,storage_budget=budget)
            report=read_json(output/'report.json'); report['outer_supervision']=supervision
            if supervision['status']!='completed':
                report['status']='failed'
        except Exception as error:
            report.update(status='failed',outer_error=str(error)[:512])
        finally:
            stop.set();sampler.join(timeout=2.)
            report['cleanup']={**cleanup_observed(dict(observed)),'sample_errors':errors,
                'sampler_stopped':not sampler.is_alive(),'observed_owned_processes':[{'pid':pid,'start_ticks':start} for pid,start in sorted(observed.items())],
                'scope':'finite .25s descendant sampling; only PID/start-matching owned cleanup; no universal transient-process proof'}
            report.update(wall_seconds=time.monotonic()-started,final_source=source_identity(root),final_harness=harness_hashes())
            if (report['cleanup']['forced_signals'] or report['cleanup']['survivors'] or errors or sampler.is_alive() or
                    report['final_source']!=report['runtime_source'] or report['final_harness']!=report['harness_sha256']):
                report['status']='failed'
            report['output_usage']=budget.usage()
            report['artifacts_sha256']={k:v for k,v in file_hashes(output).items() if k not in ('report.json','.palimpsest-storage.lock')}
            output_json(output/'report.json',report,config,control=True)
    return report


def main():
    if len(sys.argv)==3 and sys.argv[1] in ('--worker','--gate'):
        callback=worker if sys.argv[1]=='--worker' else gate
        return 0 if callback(json.loads(sys.argv[2])) else 1
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    report=verify(parser.parse_args())
    print(json.dumps({'status':report['status'],'error':report.get('error')},allow_nan=False))
    return 0 if report['status']=='passed' else 1


if __name__=='__main__':
    raise SystemExit(main())
