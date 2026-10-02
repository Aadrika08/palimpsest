"""One development transfer case; prepare-only until exclusive runtime GO.

Source acquisition uses privileged pose. Four continuations use declared bearing
only. Expected cue-loss/task failures remain failed terminal recordings.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import sys
import time
import uuid

from palimpsest import artifacts, memory, memory_experiment as experiment, memory_history, memory_task, memory_world
from palimpsest.evaluate import bounded_process
from palimpsest.records import iter_ticks
from palimpsest.replay import _initial_snapshot, _register_initial, _same_tick, Divergence
from palimpsest.snapshots import invariant_hashes, read_snapshot

HISTORY_INPUTS = {
    'own': ('runs/m5-acquisition-batch-20261002/local_cue-history.json',
        '016c5b5e9472b116d065fb922b32d64089db6e27839aec09d751238f8ce7ffc1'),
    'swapped': ('runs/m5-acquisition-batch-20261002/paired_cue-history.json',
        '64628e37cc6e861194f810baa92926eba8f57260047cdd8ad320a4601023d213')}
CONDITIONS = ('own', 'swapped', 'sham', 'no-U')
STAGES = ('source', 'anchor', *CONDITIONS)
SOURCE_PREPARATION = {'version': 2, 'name': 'fixed-visible-boundary-source-v2',
    'access': 'privileged-manual-pose-supervision', 'uses_u': False,
    'uses_regime': False, 'uses_gold': False, 'start_tick': 200, 'stop_tick': 300,
    'velocity': 0., 'target_yaw_rad': math.pi/20, 'max_heading_rad': .35,
    'base_acquisition_protocol_sha256': experiment.make_world_case(
        8, 'local_cue', 'development-test', acquisition=True)['acquisition_protocol_sha256']}
SOURCE_PREPARATION_SHA256 = memory.sha256(SOURCE_PREPARATION)
ACQUISITION_OVERRIDE = {'first_tick': 200, 'last_tick': 299,
    'replacement': 'fixed-source-orientation-only', 'source_preparation_sha256': SOURCE_PREPARATION_SHA256}
PROTOCOL = {'version': 2, 'claim': 'single-development-case-mechanism-check',
    'seed': 8, 'regime': 'local_cue', 'kind': 'change', 'split': 'development-test',
    'source_prefix_ticks': 300, 'remaining_ticks': 300, 'target_limit': 1,
    'controller': 'manual', 'device': 'cpu', 'velocity': .65,
    'driver': 'last-published-declared-bearing-only-one-tick-delay',
    'timeout_seconds': 160, 'internal_wall_seconds': 150,
    'recording_max_bytes': 192 * 1024**2, 'log_max_bytes': 1024**2,
    'retries': 0, 'history_inputs': {role: list(value) for role, value in HISTORY_INPUTS.items()},
    'source_preparation': SOURCE_PREPARATION, 'source_preparation_sha256': SOURCE_PREPARATION_SHA256,
    'acquisition_schedule_override': ACQUISITION_OVERRIDE,
    'case_producer_sha256': experiment.SOURCE_SHA256,
    'memory_protocol_sha256': memory.PROTOCOL_SHA256}
PROTOCOL_SHA256 = memory.sha256(PROTOCOL)


def _hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def source_identity(repo):
    repo = Path(repo)
    manifest = json.loads((repo / 'model_manifests/flynn-full-vision.json').read_text())
    return {'source_sha256': {str(p.relative_to(repo)): _hash(p)
        for p in sorted((repo / 'src/palimpsest').glob('*.py'))},
        'lock_sha256': _hash(repo / 'uv.lock'), 'upstream_commit': manifest['upstream_commit'],
        'driver_sha256': _hash(Path(__file__))}


def load_histories(repo):
    result = {}
    for role, (relative, expected) in HISTORY_INPUTS.items():
        path = Path(repo) / relative
        if _hash(path) != expected:
            raise ValueError('Historical collector bundle hash differs')
        bundle = artifacts._json(artifacts._read(path, memory_history.MAX_RESULT_BYTES))
        e, u = memory.validate_e(bundle['e']), memory.validate_u(bundle['u'])
        if (bundle['history_sha256'] != memory.sha256(e)
                or memory.canonical_bytes(memory.fit(e)) != memory.canonical_bytes(u)):
            raise ValueError('Historical E/U identity or E-only refit differs')
        result[role] = {'e': e, 'u': u, 'path': relative, 'sha256': expected}
    if experiment._ids(result['own']['e']) & experiment._ids(result['swapped']['e']):
        raise ValueError('Own/swapped historical namespaces overlap')
    return result


def cue_action(bearing):
    """No pose, map, regime, U, distance or hidden goal input is accepted."""
    if (type(bearing) is not list or len(bearing) != 2
            or any(type(x) not in (int, float) or not math.isfinite(x) for x in bearing)
            or not math.isclose(sum(x*x for x in bearing), 1., rel_tol=0., abs_tol=1e-6)):
        raise ValueError('Driver requires a finite declared unit bearing')
    return [.65, max(-math.pi, min(math.pi, math.atan2(bearing[1], bearing[0])))]


def source_action(schedule, pose, tick):
    """Fixed public source schedule + explicitly privileged pose; never U/gold."""
    memory._int(tick)
    if tick >= 300 or memory.sha256(schedule)!=SOURCE_PREPARATION['base_acquisition_protocol_sha256']:
        raise ValueError('Unsupported source preparation tick or base schedule')
    if tick < SOURCE_PREPARATION['start_tick']:
        return experiment.acquisition_action(schedule,pose,tick)
    _,_,yaw=memory_world._numbers(pose,3)
    error=math.remainder(SOURCE_PREPARATION['target_yaw_rad']-yaw,2*math.pi)
    bound=SOURCE_PREPARATION['max_heading_rad']
    return [0.,max(-bound,min(bound,error))]


def preparation_packet(events, case, state, tick):
    """Admit actual recorded visibility, not an ideal or recaptured pose."""
    if type(tick) is not int or tick not in (299,300):
        raise ValueError('Unsupported visibility admission boundary')
    found=[e for e in events if e['kind']=='memory_sensed' and e.get('episode_step')==tick]
    if (len(found)!=1 or type(found[0].get('tick')) is not int or found[0]['tick']!=tick
            or type(found[0].get('episode')) is not int or found[0]['episode']!=0):
        raise ValueError('Missing or inconsistent recorded visibility packet')
    packet=found[0]['packet']
    memory_task._validate_packet(packet,state)
    landmarks={case['common_goal_id'],*[f['inspection_landmark_id'] for f in case['facts']]}
    cues=packet['cues']
    if (packet['tick']!=tick or packet['common_goal_id']!=case['common_goal_id']
            or not landmarks.issubset({v['id'] for v in packet['landmarks']})
            or len(cues)!=1 or cues[0]['id']!=case['cue_id'] or cues[0]['state']!=int(tick==300)
            or next(v['passability'] for v in packet['passages']
                    if v['subject_id']==case['subjects_by_side'][0])!='unobserved'):
        raise ValueError('Source preparation visibility or unobserved lower passage is inadmissible')
    return copy.deepcopy(packet)


def evidence_backed_source(m, events, episode_id):
    m=memory.validate_m(m)
    samples=[v for e in events if e['kind']=='memory_sensed' for v in e['packet']['passages']]
    for fact in m['facts']:
        evidence=fact['evidence']
        if (fact['status']!='observed' or evidence is None or evidence['episode_id']!=episode_id
                or evidence['tick']>299):
            raise ValueError('Source facts lack retained observed evidence')
        matches=[v for v in samples if all(v.get(k)==evidence[k] for k in ('id','episode_id','tick'))
                 and v['subject_id']==fact['subject_id'] and v['passability']==fact['estimate']]
        if len(matches)!=1:
            raise ValueError('Source fact evidence differs from recorded declared observations')


def packet_cursor(packet, state):
    """Bind committed task cursor/detector exactly to its declared packet."""
    goal=packet['common_goal_id'] if state['active'] is None else next(
        f['inspection_landmark_id'] for f in state['m']['facts'] if f['id']==state['active']['fact_id'])
    angle=next(v['bearing_rad'] for v in packet['landmarks'] if v['id']==goal)
    cursor={'episode_id':packet['episode_id'],'tick':packet['tick'],'packet_sha256':memory.sha256(packet),
        'common_goal_id':packet['common_goal_id'],'bearing':[math.cos(angle),math.sin(angle)]}
    detector={'tick':packet['tick'],'cues':[{'id':c['id'],'state':c['state'],
        'observation_id':memory_task._sensor_id(packet['episode_id'],packet['tick'],'cue',c['id'])}
        for c in sorted(packet['cues'],key=lambda c:c['id'])]}
    if (memory.canonical_bytes(state['cursor'])!=memory.canonical_bytes(cursor)
            or memory.canonical_bytes(state['detector'])!=memory.canonical_bytes(detector)):
        raise ValueError('Committed task cursor/detector differs from its actual recorded packet')
    return {'cursor':cursor,'detector':detector}


def source_controls(data, case):
    """Bind the explicit override to the actual recorded pose and manual action."""
    import numpy as np
    inputs=[e for e in data['events'] if e['kind']=='source_preparation_input']
    if [e.get('episode_step') for e in inputs]!=list(range(200,300)):
        raise ValueError('Source override lacks its exact recorded control range')
    by_tick={e['episode_step']:e for e in inputs}
    for row in data['rows']:
        tick=row['tick']
        expected=np.asarray(source_action(case['acquisition_schedule'],row['pose'].tolist(),tick),np.float64)
        if row['action'].dtype!=expected.dtype or not np.array_equal(row['action'],expected):
            raise ValueError('Recorded source action differs from the declared schedule/override')
        if tick>=200:
            event=by_tick[tick]
            if (type(event.get('tick')) is not int or event['tick']!=tick
                    or type(event.get('episode')) is not int or event['episode']!=0
                    or event.get('source_preparation_sha256')!=SOURCE_PREPARATION_SHA256
                    or not np.array_equal(row['pose'],np.asarray(event.get('pose'),np.float64))
                    or not np.array_equal(expected,np.asarray(event.get('action'),np.float64))):
                raise ValueError('Source privileged preparation input differs from the actual row')
    lower=case['subjects_by_side'][0]
    if any(v['passability']!='unobserved' for e in data['events'] if e['kind']=='memory_sensed'
           and 200<=e['episode_step']<=299 for v in e['packet']['passages'] if v['subject_id']==lower):
        raise ValueError('Lower occupancy was newly observed during preparation')


def occupancy(case, circles):
    """Evaluator only: clearance from retained actual circles, independent of U."""
    labels = memory_world.passage_status(circles)
    return dict(zip(case['subjects_by_side'], (labels['passage-a'], labels['passage-b'])))


def score_nine(m, trigger, histories, gold):
    choices = {'own': histories['own']['u'], 'swapped': histories['swapped']['u'],
        'sham': copy.deepcopy(histories['own']['u']), 'no-U': memory.artifact(method='empty-v1'),
        'hand-authored': memory.artifact('local_cue')}
    result = []
    for condition in experiment.CONDITIONS:
        resources = {'u': choices[condition]} if condition in choices else (
            {'history': histories['own']['e']} if condition == 'retrieval' else
            {'gold_target_ids': gold} if condition == 'oracle' else {})
        selection = experiment.selection_for_condition(condition, m, trigger, **resources)
        targets, expected = set(selection['target_ids']), set(gold)
        access = {'m': m, 'trigger': trigger, **resources}
        behavior = copy.deepcopy(access)
        if 'u' in behavior:
            behavior['u.payload'] = behavior.pop('u')['payload']
        if trigger is None:
            behavior = {}
        result.append({'condition': condition, 'selection': selection, 'target_limit': 1,
            'exact_set': targets == expected, 'false_targets': len(targets-expected),
            'missed_targets': len(expected-targets), 'abstained': not targets,
            'correct_abstention': not targets and not expected,
            'precision': len(targets & expected)/len(targets) if targets else None,
            'recall': len(targets & expected)/len(expected) if expected else None,
            'privileged': condition == 'oracle', 'runtime_access': list(access),
            'validation_access': list(access), 'behavior_access': list(behavior),
            'validation_input_bytes': len(memory.canonical_bytes(access)),
            'behavior_input_bytes': len(memory.canonical_bytes(behavior)) if behavior else 0,
            'payload_bytes': len(memory.canonical_bytes(resources['u']['payload'])) if 'u' in resources else 0,
            'envelope_bytes': len(memory.canonical_bytes(resources['u'])) if 'u' in resources else 0,
            'runtime_history_bytes': len(memory.canonical_bytes(resources['history'])) if 'history' in resources else 0})
    return result


def validate_job(job, *, prepared=False):
    memory._fields(job, 'repo assets output run_id stage case source_identity protocol_sha256 snapshot_path snapshot_sha256 expected_non_u')
    if (job['stage'] not in STAGES or job['protocol_sha256'] != PROTOCOL_SHA256
            or Path(job['repo']) != Path(__file__).resolve().parents[1]
            or artifacts._id(job['run_id']) != artifacts._id(Path(job['output']).name)):
        raise ValueError('Unsupported transfer worker identity')
    expected = experiment.make_world_case(8, 'local_cue', 'development-test', acquisition=True)
    if memory.canonical_bytes(experiment.validate_world_case(job['case'])) != memory.canonical_bytes(expected):
        raise ValueError('Transfer requires the fixed fresh development case')
    if any(not Path(job[k]).is_absolute() for k in ('repo', 'assets', 'output')):
        raise ValueError('Worker paths must be absolute')
    bound = (job['snapshot_path'], job['snapshot_sha256'], job['expected_non_u'])
    if job['stage'] == 'source' and bound != (None, None, None):
        raise ValueError('Source cannot consume a snapshot')
    if job['stage'] != 'source' and not prepared and (any(x is None for x in bound)
            or not Path(job['snapshot_path']).is_absolute() or type(job['expected_non_u']) is not dict):
        raise ValueError('Continuation requires a hash-bound native snapshot')
    return copy.deepcopy(job)


def make_plan(repo, assets, output):
    repo, assets, output = (Path(p).resolve() for p in (repo, assets, output))
    histories = load_histories(repo)
    case = experiment.make_world_case(8, 'local_cue', 'development-test', acquisition=True)
    if experiment._ids(case) & (experiment._ids(histories['own']['e']) | experiment._ids(histories['swapped']['e'])):
        raise ValueError('Fresh test and history IDs overlap')
    identity = source_identity(repo)
    jobs = []
    for stage in STAGES:
        run_id = uuid.uuid4().hex
        jobs.append(validate_job({'repo': str(repo), 'assets': str(assets), 'output': str(output/'runs'/run_id),
            'run_id': run_id, 'stage': stage, 'case': case, 'source_identity': identity,
            'protocol_sha256': PROTOCOL_SHA256, 'snapshot_path': None,
            'snapshot_sha256': None, 'expected_non_u': None}, prepared=True))
    return {'output': str(output), 'protocol': PROTOCOL, 'protocol_sha256': PROTOCOL_SHA256,
        'source_identity': identity, 'history_inputs': {k: {'path': v['path'], 'sha256': v['sha256']} for k,v in histories.items()},
        'jobs': jobs}


def read_run(run):
    """Validate terminal failures without coercing them into completed artifacts."""
    run = artifacts._safe_path(run)
    manifest, events = artifacts._manifest(run), artifacts._events(run)
    if manifest.get('status') not in ('completed', 'failed'):
        raise ValueError('Transfer recording is not terminal')
    paths = [run/'recording'/name for name in ('manifest.json','events.jsonl')]
    for i,event in enumerate(e for e in events if e['kind']=='chunk'):
        if event.get('path') != f'chunks/{i:06d}.npz':
            raise ValueError('Unsafe transfer chunk path')
        paths.append(run/'recording'/event['path'])
    fingerprint = artifacts._fingerprint(paths)
    if sum(p.stat().st_size for p in paths) > PROTOCOL['recording_max_bytes']:
        raise ValueError('Transfer recording exceeds its cap')
    rows = list(iter_ticks(run/'recording'))  # Exhaust all checksums and terminal counts.
    if any(row['episode'] != 0 or not 0 <= row['tick'] < 600 for row in rows):
        raise ValueError('Unsupported transfer episode/tick')
    if any('run_id' in e and e['run_id'] != manifest['run_id'] for e in events):
        raise ValueError('Transfer event run identity differs')
    if rows:
        for row in (rows[0], rows[-1]):
            artifacts._world_at(events, 0, row['tick'])
            artifacts._vector(row['pose'],3,'pose')
            artifacts._vector(row['next_pose'],3,'next pose')
    if artifacts._fingerprint(paths) != fingerprint:
        raise ValueError('Recording changed during validation')
    return {'run': run, 'manifest': manifest, 'events': events, 'rows': rows,
        'paths': paths, 'fingerprint': fingerprint}


def _command_step(engine, action, identifier):
    for kind,payload in (('set_action',{'action':action}),('step',None)):
        command = {'id': identifier+'-'+kind, 'kind':kind, 'expected_state':'paused','expected_episode':0}
        if payload is not None:
            command['payload']=payload
        if engine.submit(command)['status'] != 'queued':
            raise ValueError('Driver command not queued')
        state=engine.advance()
    return state


def worker(raw):
    from palimpsest.engine import Engine
    job = validate_job(raw)
    if source_identity(job['repo']) != job['source_identity']:
        raise ValueError('Worker source changed before initialization')
    histories=load_histories(job['repo'])
    run,stage,case=Path(job['output']),job['stage'],job['case']
    engine=None
    started=time.monotonic()
    report={'stage':stage,'status':'failed','run_path':str(run),'task_pass':False,'r2_complete':False}
    try:
        engine=Engine.open(job['repo'],job['assets'],run/'recording',controller='manual',device='cpu',
            scenario='memory-passages',seed=8,run_id=job['run_id'],max_bytes=PROTOCOL['recording_max_bytes'],memory_case=case)
        engine.writer.manifest.update(transfer_protocol=PROTOCOL,transfer_protocol_sha256=PROTOCOL_SHA256,
            transfer_driver_sha256=job['source_identity']['driver_sha256'],transfer_stage=stage,
            source_preparation_protocol=SOURCE_PREPARATION,source_preparation_sha256=SOURCE_PREPARATION_SHA256,
            acquisition_schedule_override=ACQUISITION_OVERRIDE)
        engine._event('source_preparation_declared',protocol=SOURCE_PREPARATION,
            source_preparation_sha256=SOURCE_PREPARATION_SHA256,override=ACQUISITION_OVERRIDE)
        if stage != 'source':
            path=Path(job['snapshot_path'])
            if _hash(path) != job['snapshot_sha256']:
                raise ValueError('Snapshot hash differs before restore')
            native=read_snapshot(path)
            if invariant_hashes(native) != job['expected_non_u']:
                raise ValueError('Source snapshot scientific invariants differ')
            u=(histories['swapped']['u'] if stage=='swapped' else memory.artifact(method='empty-v1')
                if stage=='no-U' else copy.deepcopy(histories['own']['u']))
            engine.restore_memory_branch(native,u)
            from palimpsest.snapshots import capture
            initial=capture(engine.env,engine.observation,application=engine.application_state())
            if invariant_hashes(initial) != job['expected_non_u']:
                raise ValueError('Initial branch state changed outside U')
            report['initial_non_u']=invariant_hashes(initial)
            if stage in CONDITIONS:
                _register_initial(engine,run)
                report.update(initial_snapshot_sha256=_hash(run/'snapshots/initial.snp'))
        if stage=='source':
            engine.writer.manifest['acquisition_access']='privileged-manual-pose-supervision'
            for tick in range(300):
                if time.monotonic()-started >150:
                    raise TimeoutError('Source internal wall bound')
                pose=[*map(float,engine.env._base_xy()),float(engine.env._base_yaw())]
                action=source_action(case['acquisition_schedule'],pose,tick)
                if tick>=200:
                    engine._event('source_preparation_input',pose=pose,action=action,
                        source_preparation_sha256=SOURCE_PREPARATION_SHA256)
                state=_command_step(engine,action,f'prefix-{tick}')
                if state['phase']!='paused':
                    raise ValueError('Source terminated before pre-event capture')
            if not all(f['status']=='observed' for f in engine.memory['m']['facts']):
                raise ValueError('Source facts were not actually observed')
            events=artifacts._events(run)
            packet=preparation_packet(events,case,engine.memory,299)
            evidence_backed_source(engine.memory['m'],events,engine.memory['episode_id'])
            report['visibility_admission']={'299':memory.sha256(packet)}
            report['boundary_memory']={'299':packet_cursor(packet,engine.memory)}
        if stage in ('source','anchor'):
            report['before_circles']=memory_world.sensing_inputs(engine.env,engine.world_task_state)[2]
            _register_initial(engine,run)
            native=read_snapshot(run/'snapshots/initial.snp')
            report.update(snapshot_path=str(run/'snapshots/initial.snp'),snapshot_sha256=_hash(run/'snapshots/initial.snp'),
                non_u=invariant_hashes(native),pre_m=copy.deepcopy(engine.memory['m']),status='recorded')
        else:
            engine.writer.manifest['continuation_access']='last-published-declared-bearing-only'
            for _ in range(300):
                if time.monotonic()-started>150:
                    raise TimeoutError('Continuation internal wall bound')
                tick=engine.episode_step
                cursor=engine.memory['cursor']
                if cursor is None or cursor['tick']!=tick-1:
                    raise ValueError('Driver lacks its fresh published previous bearing')
                bearing=cursor['bearing'].copy()
                action=cue_action(bearing)
                engine._event('transfer_driver_input',bearing_tick=cursor['tick'],bearing=bearing,action=action)
                state=_command_step(engine,action,f'cue-{tick}')
                if tick==300:
                    report['after_circles']=memory_world.sensing_inputs(engine.env,engine.world_task_state)[2]
                    packet=preparation_packet(artifacts._events(run),case,engine.memory,300)
                    report['visibility_admission']={'300':memory.sha256(packet)}
                    report['boundary_memory']={'300':packet_cursor(packet,engine.memory)}
                if state['phase']!='paused':
                    break
            report['status']='recorded'
    except Exception as error:
        report['error']={'type':type(error).__name__,'message':str(error)}
    finally:
        if engine is not None:
            report.update(final_phase=engine.phase,outcome=engine.last_outcome,steps=engine.episode_step,
                final_memory=copy.deepcopy(engine.memory),gate_result=engine.world_task_state['gate_result'])
            try:
                engine.close()
            except Exception as error:
                report.update(status='cleanup_failed',cleanup_error={'type':type(error).__name__,'message':str(error)})
    report['wall_seconds']=time.monotonic()-started
    _write(run/'transfer-worker.json',report)
    expected_failure=(report.get('final_phase')=='failed' and (report.get('outcome') or {}).get('type')=='CueUnavailable'
        and report.get('final_memory',{}).get('requests') and report.get('final_memory',{}).get('active') is None)
    return 0 if report['status']=='recorded' and (report.get('final_phase')!='failed' or expected_failure) else 1


def validate_stage(job, supervised):
    if supervised['status']!='completed' or supervised.get('returncode')!=0:
        raise ValueError('Transfer child failed; no retry or replacement is allowed')
    run=Path(job['output'])
    data=read_run(run)
    manifest,events=data['manifest'],data['events']
    report=artifacts._json(artifacts._read(run/'transfer-worker.json',1024**2))
    expected={'memory_case':job['case'],'memory_case_sha256':memory.sha256(job['case']),
        'transfer_protocol':PROTOCOL,'transfer_protocol_sha256':PROTOCOL_SHA256,
        'transfer_driver_sha256':job['source_identity']['driver_sha256'],'transfer_stage':job['stage'],
        'source_preparation_protocol':SOURCE_PREPARATION,'source_preparation_sha256':SOURCE_PREPARATION_SHA256,
        'acquisition_schedule_override':ACQUISITION_OVERRIDE}
    if any(memory.canonical_bytes(manifest.get(k))!=memory.canonical_bytes(v) for k,v in expected.items()):
        raise ValueError('Recorded case/protocol/driver identity differs')
    environments=[e for e in events if e['kind']=='environment']
    if len(environments)!=1 or any(environments[0].get(k)!=job['source_identity'][k]
            for k in ('source_sha256','lock_sha256','upstream_commit')):
        raise ValueError('Recorded source identity differs')
    if (manifest.get('controller')!='manual' or manifest.get('requested_device')!='cpu' or manifest.get('seed')!=8
            or manifest.get('recording_max_bytes')!=PROTOCOL['recording_max_bytes']
            or report.get('status')!='recorded' or report.get('stage')!=job['stage']
            or report.get('run_path')!=str(run) or 'cleanup_error' in report
            or manifest.get('close_reason')!='operator_closed'):
        raise ValueError('Transfer controller, quota, cleanup or worker report differs')
    if (manifest.get('final_phase')!=report.get('final_phase')
            or memory.canonical_bytes(manifest.get('last_outcome'))!=memory.canonical_bytes(report.get('outcome'))
            or (manifest['status']=='failed')!=(report.get('final_phase')=='failed')):
        raise ValueError('Terminal recording and worker outcome differ')
    native,entry,_=_initial_snapshot(data)
    hashes=invariant_hashes(native)
    declarations=[e for e in events if e['kind']=='source_preparation_declared']
    if (len(declarations)!=1
            or memory.canonical_bytes(declarations[0].get('protocol'))!=memory.canonical_bytes(SOURCE_PREPARATION)
            or declarations[0].get('source_preparation_sha256')!=SOURCE_PREPARATION_SHA256
            or memory.canonical_bytes(declarations[0].get('override'))!=memory.canonical_bytes(ACQUISITION_OVERRIDE)
            or type(declarations[0].get('sequence')) is not int
            or declarations[0]['sequence']>=native['application']['event_prefix']['event_count']):
        raise ValueError('Native event prefix lacks the declared source preparation protocol')
    if memory.canonical_bytes(native['application']['world_task_state'].get('case'))!=memory.canonical_bytes(job['case']):
        raise ValueError('Native snapshot case identity differs')
    histories=load_histories(job['repo'])
    expected_u=(memory.artifact(method='empty-v1') if job['stage'] in ('source','no-U') else
        histories['swapped']['u'] if job['stage']=='swapped' else histories['own']['u'])
    if memory.canonical_bytes(native['application']['memory']['u'])!=memory.canonical_bytes(expected_u):
        raise ValueError('Registered native U differs from its declared condition')
    cursor=native['application']['memory']['cursor']
    if (type(cursor.get('tick')) is not int or cursor['tick']!=299
            or cursor.get('episode_id')!='episode-0' or cursor.get('common_goal_id')!=job['case']['common_goal_id']):
        raise ValueError('Native source/anchor cursor is not the admitted pre-event boundary')
    if job['stage'] in ('source','anchor') and (report['final_phase']!='paused' or manifest.get('final_phase')!='paused'):
        raise ValueError('Source/anchor did not finish paused')
    if job['stage']=='source':
        if (report['steps']!=300 or manifest.get('total_tick')!=300 or manifest['status']!='completed'
                or [r['tick'] for r in data['rows']]!=list(range(300))):
            raise ValueError('Source did not complete its exact pre-event prefix')
        source_controls(data,job['case'])
        # Existing collector admission checks all public samples/banks/empty U;
        # do not call fit on this current test source.
        prefix,source=memory_history._source(run,memory_history.MAX_INPUT_BYTES)
        episodes,links=memory_history._episodes(prefix,source)
        if episodes or len(links)!=1 or links[0].get('gap')!=['no_observed_trigger']:
            raise ValueError('Source witnessed an event before capture')
        app=native['application']
        state=app['memory']
        packet=preparation_packet(events,job['case'],state,299)
        evidence_backed_source(state['m'],events,state['episode_id'])
        if report.get('visibility_admission')!={'299':memory.sha256(packet)}:
            raise ValueError('Source visibility admission report differs from actual packet')
        if report.get('boundary_memory')!={'299':packet_cursor(packet,state)}:
            raise ValueError('Source native cursor report differs from its recorded packet')
        if (app['episode_step']!=300 or state['cursor']['tick']!=299 or app['world_task_state']['applied']
                or not all(f['status']=='observed' for f in state['m']['facts'])
                or state['e']['episodes'] or state['u']['payload']['rules']):
            raise ValueError('Source snapshot lacks real observed facts before the event')
        if memory.canonical_bytes(state['initial_m'])!=memory.canonical_bytes(memory.seed_m(job['case']['facts'],[])):
            raise ValueError('Native source initial bank differs from the actual case')
        if memory.canonical_bytes(state['m'])!=memory.canonical_bytes(report['pre_m']):
            raise ValueError('Source factual report differs from native state')
        if any(f['estimate']!=occupancy(job['case'],report['before_circles'])[f['subject_id']] for f in state['m']['facts']):
            raise ValueError('Source observed expectations contradict actual retained before geometry')
    elif job['stage']=='anchor':
        if manifest['status']!='completed' or data['rows'] or report['steps']!=300 or manifest.get('total_tick')!=300:
            raise ValueError('Own-U anchor unexpectedly stepped or failed')
    else:
        rows=data['rows']
        if not rows or [r['tick'] for r in rows]!=list(range(300,300+len(rows))) or len(rows)>300:
            raise ValueError('Branch has missing or invalid continuation ticks')
        packet=preparation_packet(events,job['case'],native['application']['memory'],300)
        if report.get('visibility_admission')!={'300':memory.sha256(packet)}:
            raise ValueError('Continuation visibility admission report differs from actual packet')
        inspected=[e['memory'] for e in events if e['kind']=='memory_inspected' and e.get('episode_step')==300]
        cues300=[e['bearing'] for e in events if e['kind']=='memory_cue' and e.get('episode_step')==300]
        proof=report.get('boundary_memory',{}).get('300',{})
        if len(inspected)!=1 or len(cues300)!=1 or inspected[0].get('facts_truncated')!=0:
            raise ValueError('First branch packet lacks its complete recorded task state')
        current={**proof,'active':inspected[0]['active'],'m':{'facts':inspected[0]['facts']}}
        if packet_cursor(packet,current)!=proof or proof['cursor']['bearing']!=cues300[0]:
            raise ValueError('First branch committed cursor differs from its recorded published bearing')
        outcome=report.get('outcome') or {}
        if manifest['status']=='failed' and not (report['final_phase']=='failed' and outcome.get('type')=='CueUnavailable'
                and outcome.get('message','').startswith('goal_cue_unavailable:')
                and report['final_memory']['requests'] and report['final_memory']['active'] is None):
            raise ValueError('Unexpected runtime failure; first failure retained')
        if report.get('steps')!=300+len(rows) or manifest.get('total_tick')!=report['steps']:
            raise ValueError('Continuation terminal control boundary differs')
        failures=[e for e in events if e['kind']=='runtime_failure']
        if manifest['status']=='failed' and (len(failures)!=1
                or failures[0].get('episode_step')!=report['steps']
                or failures[0].get('episode')!=0 or failures[0].get('error')!=outcome):
            raise ValueError('Expected cue loss lacks its exact recorded failure boundary')
        inputs=[e for e in events if e['kind']=='transfer_driver_input']
        cues={e['episode_step']:e['bearing'] for e in events if e['kind']=='memory_cue'}
        cues[299]=native['application']['memory']['cursor']['bearing']
        for event in inputs:
            if (event.get('bearing_tick')!=event['episode_step']-1 or event['bearing']!=cues.get(event['bearing_tick'])
                    or event['action']!=cue_action(event['bearing'])):
                raise ValueError('Continuation action was not declared-bearing-only')
        expected_ticks=list(range(300,300+len(rows)+(manifest['status']=='failed')))
        if ([e.get('episode_step') for e in inputs]!=expected_ticks
                or any(type(e.get('episode_step')) is not int or type(e.get('episode')) is not int
                       or e['episode']!=0 for e in inputs)):
            raise ValueError('Driver input/control boundary count or exact ticks differ')
        import numpy as np
        by_tick={e['episode_step']:e for e in inputs}
        for row in rows:
            # Engine._action preserves float64 for this manual controller.
            action=np.asarray(by_tick[row['tick']]['action'],dtype=np.float64)
            if row['action'].dtype!=action.dtype or not np.array_equal(row['action'],action):
                raise ValueError('Recorded action differs from its declared driver input at the exact tick')
    if job['stage']!='source' and hashes!=job['expected_non_u']:
        raise ValueError('Registered initial native state differs outside U')
    if report.get('initial_non_u',report.get('non_u'))!=hashes:
        raise ValueError('Worker/native invariant report differs')
    return data,report,native,entry


def evaluate_case(case,source_native,source_report,branch_data,branch_reports,histories):
    m=source_native['application']['memory']['m']
    reference=branch_data['own']
    triggers=[e['detail']['trigger'] for e in reference['events']
        if e['kind']=='memory_decision' and e['detail']['kind']=='memory_trigger']
    if len(triggers)!=1 or triggers[0]['tick']!=300:
        raise ValueError('Comparison lacks exactly one witnessed scheduled trigger')
    trigger=memory.validate_trigger(triggers[0])
    before=occupancy(case,source_report['before_circles'])
    after=occupancy(case,branch_reports['own']['after_circles'])
    gold=experiment.gold_target_ids(m,before,after,trigger)
    scored=score_nine(m,trigger,histories,gold)
    expected={r['condition']:r['selection'] for r in scored}
    runtime=[]
    for condition in CONDITIONS:
        data,report=branch_data[condition],branch_reports[condition]
        if occupancy(case,report['after_circles'])!=after:
            raise ValueError('Actual post-change geometry differs across conditions')
        selections=[e['detail']['selection'] for e in data['events']
            if e['kind']=='memory_decision' and e['detail']['kind']=='memory_selection']
        if len(selections)!=1 or selections[0]!=expected[condition]:
            raise ValueError('Actual branch selection differs from shared pure selector')
        inspections=[e['detail'] for e in data['events']
            if e['kind']=='memory_decision' and e['detail']['kind']=='memory_inspection']
        final=report['final_memory']
        unresolved=[r['fact_id'] for r in final['requests']]+([] if final['active'] is None else [final['active']['fact_id']])
        fresh_correct=[f['id'] for f in final['m']['facts'] if f['status']=='observed' and
            f['evidence']['tick']>=300 and f['estimate']==after[f['subject_id']]]
        requested=sum(e['status']=='requested' for e in inspections)
        started=sum(e['status']=='started' for e in inspections)
        navigation_pass=report['final_phase']=='terminated' and (report['outcome'] or {}).get('reason')=='goal'
        revision_pass=not unresolved and set(gold)<=set(fresh_correct)
        runtime.append({'condition':condition,'recording_status':data['manifest']['status'],
            'final_phase':report['final_phase'],'outcome':report['outcome'],'requested':requested,'started':started,
            'resolved':sum(e['status']=='resolved' for e in inspections),
            'timeouts':sum(e['status']=='timeout' for e in inspections),'unresolved_fact_ids':unresolved,
            'inspection_not_started':bool(requested and not started and unresolved),
            'fresh_correct_fact_ids':fresh_correct,'navigation_pass':navigation_pass,
            'revision_pass':revision_pass,'task_pass':navigation_pass and revision_pass})
    comparisons=[]
    for condition in ('swapped','sham','no-U'):
        left,right=reference['rows'],branch_data[condition]['rows']
        mismatch=None
        for a,b in zip(left,right):
            try:
                _same_tick(a,b,'policy',a['tick'])
            except Divergence as error:
                mismatch=error.detail
                break
        comparisons.append({'reference':'own','condition':condition,'shared_ticks':min(len(left),len(right)),
            'same_length':len(left)==len(right),'first_divergence':mismatch,
            'scope':'existing replay tolerances; frames are not independent samples'})
    sham=next(c for c in comparisons if c['condition']=='sham')
    if not sham['same_length'] or sham['first_divergence'] is not None:
        raise ValueError('Own/sham continuation differs')
    return {'pre_m_sha256':memory.sha256(m),'trigger':trigger,'before_occupancy':before,'after_occupancy':after,
        'gold_target_ids':gold,'targeting':scored,'runtime':runtime,'trajectory_comparisons':comparisons,
        'r2_complete':False,'held_out_executed':False,'operator_blindness_verified':False}


def run_verifier(plan):
    jobs=plan['jobs']
    if ([j['stage'] for j in jobs]!=list(STAGES) or len({j['run_id'] for j in jobs})!=6
            or any(Path(j['output'])!=Path(plan['output'])/'runs'/j['run_id'] for j in jobs)
            or memory.canonical_bytes(plan['protocol'])!=memory.canonical_bytes(PROTOCOL)
            or plan['protocol_sha256']!=PROTOCOL_SHA256):
        raise ValueError('Verifier requires the fixed six-stage plan')
    for job in jobs:
        validate_job(job,prepared=True)
    output=Path(plan['output'])
    output.mkdir(parents=True,exist_ok=False)
    (output/'runs').mkdir()
    _write(output/'transfer-plan.json',plan)
    env=os.environ.copy()
    env['PYTHONPATH']=str(Path(jobs[0]['repo'])/'src')
    env.setdefault('MUJOCO_GL','egl')
    env['MPLBACKEND']='Agg'
    env['OMP_NUM_THREADS']='2'
    summaries=[]
    data,reports,natives={}, {}, {}
    result={'version':1,'claim':PROTOCOL['claim'],'protocol_sha256':PROTOCOL_SHA256,
        'status':'mechanism_unverified','runs':summaries,'history_inputs':plan['history_inputs'],'r2_complete':False}
    try:
        for raw in jobs:
            job=copy.deepcopy(raw)
            if job['stage']!='source':
                parent='source' if job['stage']=='anchor' else 'anchor'
                job.update(snapshot_path=reports[parent]['snapshot_path'],snapshot_sha256=reports[parent]['snapshot_sha256'],
                    expected_non_u=reports[parent]['non_u'])
            validate_job(job)
            print(json.dumps({'stage':job['stage'],'run_id':job['run_id']}),flush=True)
            supervised=bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',json.dumps(job)],
                Path(job['output']),160,env,log_max_bytes=1024**2)
            summary={'stage':job['stage'],'run_id':job['run_id'],'run_path':job['output'],'supervisor':supervised}
            summaries.append(summary)
            current,report,native,entry=validate_stage(job,supervised)
            stage=job['stage']
            data[stage],reports[stage],natives[stage]=current,report,native
            summary.update(recording_status=current['manifest']['status'],final_phase=report['final_phase'],
                worker_report_sha256=_hash(Path(job['output'])/'transfer-worker.json'),
                snapshot_sha256=entry['sha256'],initial_non_u=invariant_hashes(native),
                files=[{'path':str(p.relative_to(Path(job['output']))),'bytes':p.stat().st_size,'sha256':_hash(p)} for p in current['paths']])
        histories=load_histories(jobs[0]['repo'])
        result['comparison']=evaluate_case(jobs[0]['case'],natives['source'],reports['source'],
            {c:data[c] for c in CONDITIONS},{c:reports[c] for c in CONDITIONS},histories)
        result['status']='mechanism_checked'
    except (OSError,ValueError,KeyError,TypeError) as error:
        result['first_failure']={'type':type(error).__name__,'message':str(error)}
    final=source_identity(jobs[0]['repo'])
    result.update(source_identity=plan['source_identity'],final_source_identity=final,
        source_unchanged=final==plan['source_identity'])
    if not result['source_unchanged'] or any(artifacts._fingerprint(d['paths'])!=d['fingerprint'] for d in data.values()):
        result.update(status='mechanism_unverified',source_mutation=True)
    _write(output/'transfer-report.json',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker')
    parser.add_argument('--repo',type=Path)
    parser.add_argument('--assets',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--plan-only',action='store_true')
    args=parser.parse_args()
    if args.worker is not None:
        return worker(json.loads(args.worker))
    if any(p is None for p in (args.repo,args.assets,args.output)):
        parser.error('--repo, --assets and --output required')
    plan=make_plan(args.repo,args.assets,args.output)
    if args.plan_only:
        print(json.dumps(plan,indent=2,allow_nan=False))
        return 0
    result=run_verifier(plan)
    print(json.dumps(result,indent=2,allow_nan=False))
    return 0 if result['status']=='mechanism_checked' else 1


if __name__=='__main__':
    raise SystemExit(main())
