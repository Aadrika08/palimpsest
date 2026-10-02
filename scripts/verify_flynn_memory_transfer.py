"""One fixed CPU FLYNN development case; preparation until explicit runtime GO.

The historical 22-stage manual verifier is an unchanged helper dependency.
Manual pose supervision ends before the empty-U neural anchor is captured.
"""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import numpy as np

from palimpsest import artifacts, assets as model_assets, memory, memory_experiment as experiment, memory_history, memory_task, memory_world
from palimpsest.evaluate import bounded_process
from palimpsest.replay import _initial_snapshot, _register_initial
from palimpsest.snapshots import capture, read_snapshot, state_digest
from palimpsest.storage import GiB, MiB, StorageBudget, StorageLimits

HELPER = Path(__file__).with_name('verify_memory_transfer.py')
spec = importlib.util.spec_from_file_location('manual_transfer_helpers', HELPER)
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)

STAGES = ('source', 'policy-anchor', 'anchor', *common.CONDITIONS)
PROTOCOL = {'version': 1, 'claim': 'fixed-cpu-flynn-development-mechanism-check',
    'seed': 16, 'regime': 'local_cue', 'kind': 'change', 'split': 'development-test',
    'stages': list(STAGES), 'total_stages': 12, 'controller': 'flynn', 'device': 'cpu',
    'source_controller': 'manual', 'source_ticks': 300, 'remaining_ticks': 300,
    'source_access': 'privileged-manual-pose-supervision',
    'continuation_access': 'unchanged-policy.act-declared-cameras-and-sensors-only',
    'allowed_branch_differences': ['u', 'declared-selector-configuration'],
    'target_limit': 1, 'retries': 0, 'timeout_seconds': 160, 'internal_wall_seconds': 150,
    'outer_timeout_seconds': 1980, 'recording_max_bytes': 192*MiB,
    'snapshot_max_bytes': 16*MiB, 'initial_snapshots_per_stage': 1,
    'log_max_bytes': MiB, 'aggregate_max_bytes': 4*GiB, 'min_free_bytes': 2*GiB,
    'concurrent_control_headroom_bytes': 64*MiB,
    'history_inputs': {k:list(v) for k,v in common.HISTORY_INPUTS.items()},
    'source_preparation': common.SOURCE_PREPARATION,
    'source_preparation_sha256': common.SOURCE_PREPARATION_SHA256,
    'acquisition_schedule_override': common.ACQUISITION_OVERRIDE,
    'goal_handoff': common.GOAL_HANDOFF, 'goal_handoff_sha256': common.GOAL_HANDOFF_SHA256,
    'helper_sha256': common._hash(HELPER), 'case_producer_sha256': experiment.SOURCE_SHA256,
    'memory_protocol_sha256': memory.PROTOCOL_SHA256,
    'resource_reference': {'run_id':'0ece98c75eb348c3b928aa818dbde15a',
        'manifest_sha256':'f19e44305b3b867e78c50d892b3748c56dd2e0ab3bd38546452ca2ea30a417ff',
        'encoded_input_shape':[4813], 'raw_output_shape':[2],
        'numeric_bytes_per_tick':216094, 'planning_bytes_per_300_ticks':121975592}}
PROTOCOL_SHA256 = memory.sha256(PROTOCOL)


def source_identity(repo, assets):
    result = common.source_identity(repo)
    result.update(driver_sha256=common._hash(Path(__file__)), helper_sha256=common._hash(HELPER))
    manifest_path = Path(repo)/'model_manifests/flynn-full-vision.json'
    manifest = json.loads(manifest_path.read_text())
    result['model_manifest_sha256'] = common._hash(manifest_path)
    upstream = Path(repo)/'upstream/fly-gym'
    def git(*args):
        return subprocess.run(['git','-C',str(upstream),*args],check=True,
            capture_output=True,text=True,timeout=10).stdout
    if git('rev-parse','HEAD').strip()!=manifest['upstream_commit'] or git('status','--porcelain','--untracked-files=no'):
        raise ValueError('Actual upstream checkout is absent, modified or not pinned')
    paths = git('ls-files','-z').rstrip('\0').split('\0')
    if len(paths)>2048 or any(not p or Path(p).is_absolute() or '..' in Path(p).parts for p in paths):
        raise ValueError('Unsupported upstream file inventory')
    result['upstream_files_sha256'] = {p:common._hash(artifacts._safe_path(upstream/p)) for p in paths}
    # Explicit manifest paths only; no discovery of credentials or unrelated files.
    result['asset_sha256'] = {f['path']: common._hash(Path(assets)/f['path']) for f in manifest['files']}
    if any(result['asset_sha256'][f['path']] != f['sha256'] for f in manifest['files']):
        raise ValueError('Pinned model asset hash differs')
    graph = manifest['graph']
    archive = next(f for f in manifest['files'] if f['id']=='graph_archive')
    directory = Path(assets)/('graph-'+archive['sha256'])/'drosophila adult connectome'
    model_assets._check_mappings(Path(repo),directory,graph['mapping_files'])
    for item in [dict(path=graph['edge_file'],**graph['edge_identity']), *graph['mapping_files']]:
        path = directory/item['path']
        digest = common._hash(path)
        expected = item.get('archive_identity',item)
        if digest!=expected['sha256'] or path.stat().st_size!=expected['size_bytes']:
            raise ValueError('Prepared graph/mapping identity differs')
        result['asset_sha256'][str(path.relative_to(assets))] = digest
    return result


def selector_config(stage, histories, oracle=None):
    if stage in ('source', 'policy-anchor'):
        return None
    result = common.selector_config(stage, histories, oracle)
    if stage not in ('anchor', 'own', 'sham', 'swapped', 'retrieval', 'oracle'):
        result['provenance_sha256'] = PROTOCOL_SHA256
    return result


def condition_u(stage, histories):
    return (memory.artifact(method='empty-v1') if stage in ('source','policy-anchor')
        else common.condition_u(stage, histories))


def replacement_preserved(native):
    """Only declared fresh controller/Torch/manual intent/recorder fields differ."""
    result = copy.deepcopy(native)
    result.pop('policy')
    for key in ('policy','torch'):
        result['identity'].pop(key)
    for key in ('torch_cpu','torch_cuda'):
        result['rng'].pop(key)
    for key in ('controller','controller_tensors','manual_action','pending_commands','receipts',
                'original_commands','revision','source_run_id','event_prefix'):
        result['application'].pop(key)
    return state_digest(result)


def budget(output):
    return StorageBudget((Path(output),), StorageLimits(max_bytes=4*GiB, min_free_bytes=2*GiB,
        max_runs=12, max_snapshots=1), headroom_bytes=64*MiB)


class _SnapshotBudget:
    """Apply a per-SNP cap before existing snapshot publication, without a new format."""
    def __init__(self, storage):
        self.storage = storage

    def check_count(self, *args):
        return self.storage.check_count(*args)

    def check(self, additional, *, path):
        if Path(path).name == 'initial.snp' and additional > PROTOCOL['snapshot_max_bytes']:
            raise ValueError('Initial snapshot exceeds its declared 16 MiB cap')
        return self.storage.check(additional, path=path)


def write(path, value, storage):
    memory._bounded(value, MiB)
    payload = json.dumps(value,indent=2,allow_nan=False)+'\n'
    if len(payload.encode())>MiB:
        raise ValueError('Control/report envelope exceeds 1 MiB')
    storage.check(len(payload.encode()), path=path)
    common._write(path, value)


def validate_job(job, *, prepared=False):
    memory._fields(job, 'repo assets history_root output root_output run_id stage case protocol_sha256 source_identity selector oracle_evidence snapshot_path snapshot_sha256 expected_non_u replacement_preserved')
    memory._bounded(job, 128*1024)
    case = experiment.validate_world_case(job['case'])
    expected = experiment.make_world_case(16, 'local_cue', 'development-test',
        acquisition=True, change_tick=300)
    artifacts._id(job['run_id'])
    if (memory.canonical_bytes(case) != memory.canonical_bytes(expected)
            or job['protocol_sha256'] != PROTOCOL_SHA256 or job['stage'] not in STAGES):
        raise ValueError('Unsupported fixed neural case/stage/protocol')
    if (Path(job['repo']) != Path(__file__).resolve().parents[1]
            or any(not Path(job[k]).is_absolute() for k in ('repo','assets','history_root','output','root_output'))
            or Path(job['output']) != Path(job['root_output'])/'runs'/job['run_id']):
        raise ValueError('Neural verifier checkout/run/path identity differs')
    if job['stage'] == 'source' or prepared:
        if any(job[k] is not None for k in ('snapshot_path','snapshot_sha256','expected_non_u','replacement_preserved')):
            raise ValueError('Unprepared job already contains a restore source')
    else:
        if not Path(job['snapshot_path']).is_absolute():
            raise ValueError('Restore snapshot path must be absolute')
        memory._digest(job['snapshot_sha256'])
        if job['stage']=='policy-anchor':
            memory._digest(job['replacement_preserved'])
            if job['expected_non_u'] is not None:
                raise ValueError('Controller replacement is not a U-only comparison')
        elif not isinstance(job['expected_non_u'], dict) or job['replacement_preserved'] is not None:
            raise ValueError('Neural fork lacks its identical controller/RNG anchor')
    if job['stage'] in ('source','policy-anchor') and job['selector'] is not None:
        raise ValueError('Evidence acquisition/controller replacement cannot use a selector')
    if job['stage']!='oracle' and job['oracle_evidence'] is not None:
        raise ValueError('Evaluator gold may only enter the oracle condition')
    if prepared and job['stage']=='oracle' and job['selector'] is not None:
        raise ValueError('Oracle cannot receive gold before actual post geometry exists')
    return copy.deepcopy(job)


def make_plan(repo, assets, output, history_root):
    repo, assets, output, history_root = [Path(p).resolve() for p in (repo,assets,output,history_root)]
    histories = common.load_histories(history_root)
    case = experiment.make_world_case(16,'local_cue','development-test',acquisition=True,change_tick=300)
    if experiment._ids(case) & (experiment._ids(histories['own']['e']) | experiment._ids(histories['swapped']['e'])):
        raise ValueError('Development instance and historical evidence IDs overlap')
    identity = source_identity(repo,assets)
    jobs = []
    for stage in STAGES:
        run_id = uuid.uuid4().hex
        jobs.append(validate_job({'repo':str(repo),'assets':str(assets),'history_root':str(history_root),
            'output':str(output/'runs'/run_id),'root_output':str(output),'run_id':run_id,
            'stage':stage,'case':case,'protocol_sha256':PROTOCOL_SHA256,'source_identity':identity,
            'selector':None if stage=='oracle' else selector_config(stage,histories),
            'oracle_evidence':None,'snapshot_path':None,'snapshot_sha256':None,
            'expected_non_u':None,'replacement_preserved':None},prepared=True))
    return {'protocol':copy.deepcopy(PROTOCOL),'protocol_sha256':PROTOCOL_SHA256,'output':str(output),
        'source_identity':identity,'case_sha256':memory.sha256(case),
        'semantic_case_sha256':memory.sha256(common.semantic_case(case)),
        'history_inputs':{r:{'path':str(history_root/h['path']),'sha256':h['sha256'],
            'e_sha256':memory.sha256(h['e']),'u_sha256':memory.sha256(h['u'])} for r,h in histories.items()},
        'jobs':jobs}


def read_prepared_plan(path, expected_sha256):
    memory._digest(expected_sha256)
    path = artifacts._safe_path(path)
    if common._hash(path)!=expected_sha256:
        raise ValueError('Prepared plan hash differs')
    plan = artifacts._json(artifacts._read(path,MiB))
    if common._hash(path)!=expected_sha256:
        raise ValueError('Prepared plan changed during reading')
    return plan


def policy_step(engine, tick):
    """No action argument, manual action command, privileged pose or rescue input."""
    command = {'id':f'neural-{tick}', 'kind':'step', 'expected_state':'paused','expected_episode':0}
    if engine.controller!='flynn' or engine.policy is None:
        raise ValueError('Continuation requires real FLYNN policy')
    if engine.submit(command)['status']!='queued':
        raise ValueError('Neural step command not queued')
    return engine.advance()


def audit_policy(engine):
    """Log the actual narrow policy call; return its original result untouched."""
    original = engine.policy.act
    def act(observation):
        if (set(observation)!={'cam_left','cam_right','sensors'} or
                set(observation['sensors'])!={'collision','collision_angle','wind_direction'}):
            raise ValueError('Policy received undeclared inputs')
        result = original(observation)
        engine._event('neural_policy_call', observation_sha256=state_digest(observation),
            cameras_sha256={k:state_digest(observation[k]) for k in ('cam_left','cam_right')},
            sensors=copy.deepcopy(observation['sensors']),
            result_sha256={k:state_digest(result[k]) for k in ('action','encoded_input','raw_output')})
        return result
    engine.policy.act = act


def task_failure(report):
    outcome = report.get('outcome') or {}
    return (report.get('final_phase')=='failed' and outcome.get('type')=='CueUnavailable'
        and outcome.get('message','').startswith('goal_cue_unavailable:'))


def worker(raw):
    from palimpsest.engine import Engine
    job = validate_job(raw)
    if source_identity(job['repo'],job['assets']) != job['source_identity']:
        raise ValueError('Worker source/assets changed before initialization')
    histories = common.load_histories(job['history_root'])
    run, stage, case = Path(job['output']), job['stage'], job['case']
    storage = budget(job['root_output'])  # Parent holds the lease; child is the sole payload writer.
    storage.check(PROTOCOL['recording_max_bytes']+PROTOCOL['snapshot_max_bytes'],path=run)
    engine = None
    started = time.monotonic()
    report = {'stage':stage,'status':'failed','run_path':str(run),'task_pass':False,'r2_complete':False}
    try:
        restoration = {}
        if stage!='source':
            path = Path(job['snapshot_path'])
            if common._hash(path)!=job['snapshot_sha256']:
                raise ValueError('Restore source snapshot hash differs')
            native = read_snapshot(path)
            if stage=='policy-anchor':
                if replacement_preserved(native)!=job['replacement_preserved']:
                    raise ValueError('Replacement source preservation identity differs')
                restoration = {'restore_snapshot':native,'replace_controller':True}
            else:
                if common.baseline_invariants(native)!=job['expected_non_u']:
                    raise ValueError('Neural source/controller/RNG invariant differs')
                restoration = {'restore_snapshot':native,'memory_u':condition_u(stage,histories)}
            if stage=='oracle':
                common.validate_oracle_evidence(job['oracle_evidence'],native['application']['memory']['m'],case)
        expected_selector = selector_config(stage,histories,job['oracle_evidence'])
        if memory.canonical_bytes(job['selector'])!=memory.canonical_bytes(expected_selector):
            raise ValueError('Selector condition/resource/provenance differs')
        engine = Engine.open(job['repo'],job['assets'],run/'recording',
            controller='manual' if stage=='source' else 'flynn',device='cpu',scenario='memory-passages',
            seed=16,run_id=job['run_id'],max_bytes=PROTOCOL['recording_max_bytes'],
            storage_budget=storage,memory_case=case,**restoration)
        engine.writer.manifest.update(neural_transfer_protocol=PROTOCOL,neural_transfer_protocol_sha256=PROTOCOL_SHA256,
            neural_transfer_stage=stage,neural_transfer_source_identity=job['source_identity'],
            selector_configuration=job['selector'],selector_configuration_sha256=memory.sha256(job['selector']),
            oracle_evidence=job['oracle_evidence'],source_preparation_protocol=common.SOURCE_PREPARATION,
            source_preparation_sha256=common.SOURCE_PREPARATION_SHA256,
            acquisition_schedule_override=common.ACQUISITION_OVERRIDE,
            goal_handoff_protocol=common.GOAL_HANDOFF,goal_handoff_sha256=common.GOAL_HANDOFF_SHA256)
        engine._event('source_preparation_declared',protocol=common.SOURCE_PREPARATION,
            source_preparation_sha256=common.SOURCE_PREPARATION_SHA256,override=common.ACQUISITION_OVERRIDE)
        if stage!='source':
            current = capture(engine.env,engine.observation,policy=engine.policy,application=engine.application_state())
            if stage=='policy-anchor':
                if (replacement_preserved(current)!=job['replacement_preserved']
                        or current['application']['revision']!=native['application']['revision']+1):
                    raise ValueError('Controller replacement changed preserved state or revision')
                report['replacement_preserved'] = replacement_preserved(current)
            else:
                if common.baseline_invariants(current)!=job['expected_non_u']:
                    raise ValueError('Atomic U-only restore changed neural/physical/task state')
                engine.memory = memory_task.configure_selector(engine.memory,job['selector'])
                engine._event('selector_configured',configuration=job['selector'],
                    configuration_sha256=memory.sha256(job['selector']))
                configured = capture(engine.env,engine.observation,policy=engine.policy,application=engine.application_state())
                if common.baseline_invariants(configured)!=job['expected_non_u']:
                    raise ValueError('Configuration changed state outside U/selector')
        if stage=='source':
            engine.writer.manifest['acquisition_access']='privileged-manual-pose-supervision'
            for tick in range(300):
                if time.monotonic()-started>150:
                    raise TimeoutError('Source internal wall bound')
                pose = [*map(float,engine.env._base_xy()),float(engine.env._base_yaw())]
                action = common.source_action(case['acquisition_schedule'],pose,tick)
                if tick>=200:
                    engine._event('source_preparation_input',pose=pose,action=action,
                        source_preparation_sha256=common.SOURCE_PREPARATION_SHA256)
                if common._command_step(engine,action,f'prefix-{tick}')['phase']!='paused':
                    raise ValueError('Manual source failed its exact acquisition prefix')
            events = artifacts._events(run)
            packet = common.preparation_packet(events,case,engine.memory,299)
            common.evidence_backed_source(engine.memory['m'],events,engine.memory['episode_id'])
            report['visibility_admission'] = {'299':memory.sha256(packet)}
            report['boundary_memory'] = {'299':common.packet_cursor(packet,engine.memory)}
            report['goal_handoff'] = common.apply_goal_handoff(engine,case)
        report['before_circles'] = memory_world.sensing_inputs(engine.env,engine.world_task_state)[2]
        _register_initial(engine,run,_SnapshotBudget(storage))
        initial = read_snapshot(run/'snapshots/initial.snp')
        report.update(snapshot_path=str(run/'snapshots/initial.snp'),snapshot_sha256=common._hash(run/'snapshots/initial.snp'),
            non_u=common.baseline_invariants(initial),pre_m=copy.deepcopy(engine.memory['m']))
        if stage in common.CONDITIONS:
            audit_policy(engine)
            engine.writer.manifest['continuation_access']=PROTOCOL['continuation_access']
            for _ in range(300):
                if time.monotonic()-started>150:
                    raise TimeoutError('Neural continuation internal wall bound')
                tick = engine.episode_step
                state = policy_step(engine,tick)
                if tick==300:
                    report['after_circles'] = memory_world.sensing_inputs(engine.env,engine.world_task_state)[2]
                    packet = common.preparation_packet(artifacts._events(run),case,engine.memory,300)
                    report['visibility_admission'] = {'300':memory.sha256(packet)}
                    report['boundary_memory'] = {'300':common.packet_cursor(packet,engine.memory)}
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
    write(run/'transfer-worker.json',report,storage)
    return 0 if report['status']=='recorded' and (report.get('final_phase')!='failed' or task_failure(report)) else 1


def policy_bindings(data):
    """Bind every recorded row to the actual unmodified policy call at that tick."""
    calls = [e for e in data['events'] if e['kind']=='neural_policy_call']
    if [e.get('episode_step') for e in calls] != [r['tick'] for r in data['rows']]:
        raise ValueError('Neural call/recorded tick linkage differs')
    if any(e['kind']=='transfer_driver_input' or e['kind']=='source_preparation_input' for e in data['events']):
        raise ValueError('Neural continuation used a manual/private driver')
    commands = [e['command'] for e in data['events'] if e['kind']=='command_received']
    if any(c['kind']!='step' for c in commands):
        raise ValueError('Neural continuation received a motor/intervention command')
    for row,event in zip(data['rows'],calls):
        if (event.get('tick')!=row['tick'] or event.get('episode')!=0
                or row['encoded_input'].dtype!=np.float32 or row['encoded_input'].shape!=(4813,)
                or row['raw_output'].dtype!=np.float32 or row['raw_output'].shape!=(2,)
                or row['action'].dtype!=np.float32
                or any(not np.isfinite(row[k]).all() for k in ('action','raw_output','encoded_input'))
                or event['result_sha256']!={k:state_digest(row[k]) for k in ('action','encoded_input','raw_output')}
                or event['cameras_sha256']!={k:state_digest(row[k]) for k in ('cam_left','cam_right')}):
            raise ValueError('Neural output/camera/dtype binding differs')
        sensors = event['sensors']
        projected = np.array([float(sensors['collision']),0. if sensors['collision_angle'] is None
            else float(sensors['collision_angle']),*sensors['wind_direction']],np.float32)
        observation = {'cam_left':row['cam_left'],'cam_right':row['cam_right'],'sensors':sensors}
        cues = [e['bearing'] for e in data['events'] if e['kind']=='memory_cue' and e.get('episode_step')==row['tick']]
        if (not np.array_equal(row['sensors'],projected) or cues!=[sensors['wind_direction']]
                or event['observation_sha256']!=state_digest(observation)):
            raise ValueError('Actual neural input differs from the current declared bearing/cameras')


def validate_stage(job, supervised):
    if supervised['status']!='completed' or supervised.get('returncode')!=0:
        raise ValueError('Infrastructure/worker failure; no retry or replacement')
    data = common.read_run(Path(job['output']))
    report = artifacts._json(artifacts._read(data['run']/'transfer-worker.json',MiB))
    manifest, events, stage = data['manifest'], data['events'], job['stage']
    native, entry, _ = _initial_snapshot(data)
    expected = {'memory_case':job['case'],'memory_case_sha256':memory.sha256(job['case']),
        'neural_transfer_protocol':PROTOCOL,'neural_transfer_protocol_sha256':PROTOCOL_SHA256,
        'neural_transfer_stage':stage,'neural_transfer_source_identity':job['source_identity'],
        'selector_configuration':job['selector'],'selector_configuration_sha256':memory.sha256(job['selector']),
        'oracle_evidence':job['oracle_evidence']}
    if (any(memory.canonical_bytes(manifest.get(k))!=memory.canonical_bytes(v) for k,v in expected.items())
            or manifest.get('controller')!=('manual' if stage=='source' else 'flynn')
            or manifest.get('requested_device')!='cpu' or manifest.get('seed')!=16
            or manifest.get('recording_max_bytes')!=192*MiB or report.get('status')!='recorded'
            or report.get('stage')!=stage or report.get('run_path')!=job['output'] or 'cleanup_error' in report
            or manifest.get('close_reason')!='operator_closed'
            or manifest.get('final_phase')!=report.get('final_phase')
            or memory.canonical_bytes(manifest.get('last_outcome'))!=memory.canonical_bytes(report.get('outcome'))
            or (manifest['status']=='failed')!=(report.get('final_phase')=='failed')
            or report.get('snapshot_sha256')!=entry['sha256']
            or Path(report.get('snapshot_path',''))!=data['run']/'snapshots/initial.snp'
            or (data['run']/'snapshots/initial.snp').stat().st_size>16*MiB):
        raise ValueError('Stage case/controller/resource/terminal/cleanup identity differs')
    environments = [e for e in events if e['kind']=='environment']
    if len(environments)!=1 or any(environments[0].get(k)!=job['source_identity'][k]
            for k in ('source_sha256','lock_sha256','upstream_commit')):
        raise ValueError('Recorded authoring-source identity differs')
    app, state = native['application'], memory_task.validate_state(native['application']['memory'])
    histories = common.load_histories(job['history_root'])
    if (memory.canonical_bytes(app['world_task_state'].get('case'))!=memory.canonical_bytes(job['case'])
            or memory.canonical_bytes(state['u'])!=memory.canonical_bytes(condition_u(stage,histories))
            or app['phase']!='paused' or (app['episode'],app['episode_step'],app['total_tick'])!=(0,300,300)
            or state['cursor']['tick']!=299 or state['detector']['tick']!=299
            or report['non_u']!=common.baseline_invariants(native)
            or not np.array_equal(native['environment']['values']['_goal_xy'],np.asarray(common.effective_goal(),np.float32))):
        raise ValueError('Native pre-event state/U/goal/invariants differ')
    declarations = [e for e in events if e['kind']=='source_preparation_declared']
    if (len(declarations)!=1 or declarations[0].get('source_preparation_sha256')!=common.SOURCE_PREPARATION_SHA256
            or memory.canonical_bytes(declarations[0].get('protocol'))!=memory.canonical_bytes(common.SOURCE_PREPARATION)
            or memory.canonical_bytes(declarations[0].get('override'))!=memory.canonical_bytes(common.ACQUISITION_OVERRIDE)
            or declarations[0]['sequence']>=app['event_prefix']['event_count']):
        raise ValueError('Native event prefix lacks the source-preparation declaration')
    if stage=='source':
        if (report['final_phase']!='paused' or manifest['status']!='completed'
                or report['steps']!=300 or manifest.get('total_tick')!=300
                or [r['tick'] for r in data['rows']]!=list(range(300))
                or state['version']!=1 or state['e']['episodes'] or state['u']['payload']['rules']
                or memory.canonical_bytes(state['initial_m'])!=memory.canonical_bytes(memory.seed_m(job['case']['facts'],[]))):
            raise ValueError('Source did not acquire real facts from unknown M with empty E/U')
        common.source_controls(data,job['case'])
        prefix, source = memory_history._source(data['run'],memory_history.MAX_INPUT_BYTES)
        episodes, links = memory_history._episodes(prefix,source)
        if episodes or len(links)!=1 or links[0].get('gap')!=['no_observed_trigger']:
            raise ValueError('Source history audit found prior U guidance or an event')
        packet = common.preparation_packet(events,job['case'],state,299)
        common.evidence_backed_source(state['m'],events,'episode-0')
        if (report['visibility_admission']!={'299':memory.sha256(packet)}
                or report['boundary_memory']!={'299':common.packet_cursor(packet,state)}
                or app['world_task_state']['applied']
                or report['pre_m']!=state['m']
                or any(f['estimate']!=common.occupancy(job['case'],report['before_circles'])[f['subject_id']]
                       for f in state['m']['facts'])):
            raise ValueError('Source visibility/evidence/geometry/boundary differs')
        common.validate_goal_handoff(data,native,job['case'],'source')
        if memory.canonical_bytes(report['goal_handoff'])!=memory.canonical_bytes(next(e['proof'] for e in events if e['kind']=='goal_handoff_probe')):
            raise ValueError('Source goal handoff report differs from its recorded proof')
    else:
        original = read_snapshot(job['snapshot_path'])
        if common._hash(job['snapshot_path'])!=job['snapshot_sha256']:
            raise ValueError('Ancestor native snapshot mutated')
        expected_admission = {'source_run_id':original['application']['source_run_id'],
            'source_controller':original['application']['controller'],'snapshot_state_sha256':state_digest(original),
            'native_sha256':original['native_sha256'],'case_sha256':memory.sha256(job['case']),
            'replace_controller':stage=='policy-anchor',
            'memory_u_sha256':None if stage=='policy-anchor' else memory.sha256(condition_u(stage,histories))}
        if (memory.canonical_bytes(manifest.get('memory_continuation_admission'))!=memory.canonical_bytes(expected_admission)
                or app['controller']!='flynn' or app['execution_mode']!='live'
                or native['policy'] is None or app['controller_tensors'] is None
                or native['identity']['policy']['device']!='cpu'):
            raise ValueError('Atomic neural admission/controller/tensors differ')
        if stage=='policy-anchor':
            changes = [e for e in events if e['kind']=='controller_replaced']
            if (replacement_preserved(native)!=job['replacement_preserved']
                    or report.get('replacement_preserved')!=job['replacement_preserved']
                    or app['revision']!=original['application']['revision']+1 or len(changes)!=1
                    or changes[0].get('old')!='manual' or changes[0].get('new')!='flynn'
                    or changes[0]['sequence']>=app['event_prefix']['event_count']
                    or app['original_commands'] or app['receipts'] or app['pending_commands']
                    or app['manual_action']!=[0.,0.] or state['version']!=1):
                raise ValueError('Controller replacement changed retained state or fresh intent')
        elif common.baseline_invariants(native)!=job['expected_non_u']:
            raise ValueError('Neural fork changed state outside U/declared selector')
        configured = [e for e in events if e['kind']=='selector_configured']
        if stage=='policy-anchor':
            if configured:
                raise ValueError('Empty-U neural anchor already used a selector')
        elif (len(configured)!=1 or state.get('selector')!=selector_config(stage,histories,job['oracle_evidence'])
                or configured[0].get('configuration')!=state['selector']
                or configured[0].get('configuration_sha256')!=memory.sha256(state['selector'])
                or configured[0].get('episode_step')!=300 or configured[0]['sequence']>=app['event_prefix']['event_count']):
            raise ValueError('Selector resource/provenance is not bound to the native boundary')
        if stage in ('policy-anchor','anchor'):
            if (data['rows'] or any(e['kind']=='neural_policy_call' for e in events)
                    or report['steps']!=300 or manifest.get('total_tick')!=300 or report['final_phase']!='paused' or manifest['status']!='completed'):
                raise ValueError('Zero-step neural anchor unexpectedly inferred/stepped/failed')
        else:
            rows = data['rows']
            if ([r['tick'] for r in rows]!=list(range(300,300+len(rows))) or not rows or len(rows)>300
                    or report['steps']!=300+len(rows) or manifest.get('total_tick')!=report['steps']
                    or (manifest['status']=='failed' and not task_failure(report))):
                raise ValueError('Neural continuation boundary or runtime failure differs')
            packet = common.preparation_packet(events,job['case'],state,300)
            if report['visibility_admission']!={'300':memory.sha256(packet)}:
                raise ValueError('Actual neural packet300 did not pass visibility admission')
            inspected = [e['memory'] for e in events if e['kind']=='memory_inspected' and e.get('episode_step')==300]
            bearings = [e['bearing'] for e in events if e['kind']=='memory_cue' and e.get('episode_step')==300]
            proof = report.get('boundary_memory',{}).get('300',{})
            if len(inspected)!=1 or len(bearings)!=1 or inspected[0].get('facts_truncated')!=0:
                raise ValueError('Packet300 lacks its complete committed supervisor/bearing')
            committed = {**proof,'active':inspected[0]['active'],'m':{'facts':inspected[0]['facts']}}
            if common.packet_cursor(packet,committed)!=proof or proof['cursor']['bearing']!=bearings[0]:
                raise ValueError('Packet300 committed cursor/detector/publication differs')
            world = artifacts._world_at(events,0,300)
            projected = memory_task.capture_symbolic({'cues':[],'passages':[],
                'common_goal_id':job['case']['common_goal_id'],
                'landmarks':[{'id':job['case']['common_goal_id'],'xy':world['goal'][:2]}]},
                rows[0]['pose'].tolist(),world['obstacles'],episode_id='episode-0',tick=300)
            if (world['goal'][:2]!=common.effective_goal() or projected['landmarks']!=[
                    next(v for v in packet['landmarks'] if v['id']==job['case']['common_goal_id'])]):
                raise ValueError('First neural observation does not use actual relocated goal geometry')
            policy_bindings(data)
            failures = [e for e in events if e['kind']=='runtime_failure']
            commands = [e['command'] for e in events if e['kind']=='command_received']
            if ([c['id'] for c in commands]!=[f'neural-{t}' for t in range(300,report['steps']+(manifest['status']=='failed'))]
                    or (manifest['status']=='failed' and (len(failures)!=1
                        or failures[0].get('episode_step')!=report['steps'] or failures[0].get('error')!=report['outcome']))):
                raise ValueError('Neural attempted-step/failed-boundary accounting differs')
    final = memory_task.validate_state(report['final_memory'])
    if any(memory.canonical_bytes(final.get(k))!=memory.canonical_bytes(state.get(k)) for k in ('e','u','selector')):
        raise ValueError('Live continuation changed E/U/selector resources')
    return data,report,native,entry


def run_verifier(plan):
    jobs = plan['jobs']
    if (memory.canonical_bytes(plan['protocol'])!=memory.canonical_bytes(PROTOCOL)
            or plan['protocol_sha256']!=PROTOCOL_SHA256 or [j['stage'] for j in jobs]!=list(STAGES)
            or len({j['run_id'] for j in jobs})!=12):
        raise ValueError('Exactly the frozen 12-stage neural plan is required')
    for job in jobs:
        validate_job(job,prepared=True)
        if (job['source_identity']!=plan['source_identity'] or job['root_output']!=plan['output']
                or any(job[k]!=jobs[0][k] for k in ('repo','assets','history_root'))):
            raise ValueError('Job source/output identity differs from its plan')
    if plan['case_sha256']!=memory.sha256(jobs[0]['case']) or plan['semantic_case_sha256']!=memory.sha256(common.semantic_case(jobs[0]['case'])):
        raise ValueError('Plan case identity differs')
    histories = common.load_histories(jobs[0]['history_root'])
    if experiment._ids(jobs[0]['case']) & (experiment._ids(histories['own']['e']) | experiment._ids(histories['swapped']['e'])):
        raise ValueError('Development instance and historical evidence IDs overlap')
    expected_history = {r:{'path':str(Path(jobs[0]['history_root'])/h['path']),'sha256':h['sha256'],
        'e_sha256':memory.sha256(h['e']),'u_sha256':memory.sha256(h['u'])} for r,h in histories.items()}
    if plan['history_inputs']!=expected_history:
        raise ValueError('Plan historical source identities differ')
    if source_identity(jobs[0]['repo'],jobs[0]['assets'])!=plan['source_identity']:
        raise ValueError('Source/assets changed after planning')
    output = Path(plan['output'])
    if output.exists():
        raise ValueError('Output must be fresh; no retries/replacement')
    existing = output.parent
    while not existing.exists():
        existing = existing.parent
    if shutil.disk_usage(existing).free < 6*GiB:
        raise ValueError('Neural batch requires 4 GiB allowance plus 2 GiB free floor')
    storage = budget(output)
    summaries, data, reports, natives = [], {}, {}, {}
    result = {'version':1,'claim':PROTOCOL['claim'],'protocol_sha256':PROTOCOL_SHA256,
        'status':'mechanism_unverified','runs':summaries,'history_inputs':plan['history_inputs'],
        'r2_complete':False,'held_out_executed':False,'replay_executed':False}
    env = os.environ.copy()
    env.update(PYTHONPATH=str(Path(jobs[0]['repo'])/'src'),MUJOCO_GL='egl',MPLBACKEND='Agg',OMP_NUM_THREADS='2')
    started = time.monotonic()
    with storage.lock():
        (output/'runs').mkdir()
        storage.check_count('runs',0,12)
        write(output/'transfer-plan.json',plan,storage)
        try:
            for raw in jobs:
                if time.monotonic()-started>PROTOCOL['outer_timeout_seconds']-160:
                    raise TimeoutError('Aggregate wall budget cannot admit another child')
                job = copy.deepcopy(raw)
                stage = job['stage']
                if stage!='source':
                    parent = 'source' if stage=='policy-anchor' else 'policy-anchor' if stage=='anchor' else 'anchor'
                    ancestor = reports[parent]
                    job.update(snapshot_path=ancestor['snapshot_path'],snapshot_sha256=ancestor['snapshot_sha256'])
                    if stage=='policy-anchor':
                        job['replacement_preserved']=replacement_preserved(natives[parent])
                    else:
                        job['expected_non_u']=ancestor['non_u']
                if stage=='oracle':
                    proof = common.oracle_evidence(job['case'],natives['source'],reports['source'],
                        data['own'],reports['own'],data['source'])
                    job.update(oracle_evidence=proof,selector=selector_config(stage,histories,proof))
                validate_job(job)
                write(output/f'{stage}-job.json',job,storage)
                print(json.dumps({'stage':stage,'run_id':job['run_id']}),flush=True)
                supervised = bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',json.dumps(job)],
                    Path(job['output']),160,env,log_max_bytes=MiB,storage_budget=storage)
                summary = {'stage':stage,'run_id':job['run_id'],'run_path':job['output'],'supervisor':supervised}
                summaries.append(summary)
                current, report, native, entry = validate_stage(job,supervised)
                data[stage],reports[stage],natives[stage] = current, report, native
                summary.update(recording_status=current['manifest']['status'],final_phase=report['final_phase'],
                    worker_report_sha256=common._hash(Path(job['output'])/'transfer-worker.json'),
                    snapshot_sha256=entry['sha256'],initial_non_u=common.baseline_invariants(native),
                    files=[{'path':str(p.relative_to(Path(job['output']))),'bytes':p.stat().st_size,'sha256':common._hash(p)} for p in current['paths']])
                if stage=='oracle':
                    result['comparison'] = common.evaluate_case(job['case'],natives['source'],reports['source'],
                        {c:data[c] for c in common.CONDITIONS},{c:reports[c] for c in common.CONDITIONS},histories,data['source'])
                    result['comparison']['controller_scope']='fixed CPU FLYNN; manual source acquisition and explicit replacement precede all neural branches'
            result['status']='mechanism_checked'
        except (OSError,ValueError,KeyError,TypeError,RuntimeError,TimeoutError) as error:
            result['first_failure']={'type':type(error).__name__,'message':str(error)}
        result['unattempted_stages']=[{'stage':j['stage'],'run_id':j['run_id'],'status':'unattempted',
            'reason':'earlier infrastructure/invariant failure; no retry'} for j in jobs[len(summaries):]]
        final, changed_retained = None, False
        try:
            final = source_identity(jobs[0]['repo'],jobs[0]['assets'])
            changed_retained = any(artifacts._fingerprint(d['paths'])!=d['fingerprint'] or
                common._hash(Path(reports[s]['snapshot_path']))!=reports[s]['snapshot_sha256'] or
                common._hash(d['run']/'transfer-worker.json')!=next(r['worker_report_sha256'] for r in summaries if r['stage']==s)
                for s,d in data.items())
            common.load_histories(jobs[0]['history_root'])
        except (OSError,ValueError,KeyError,TypeError) as error:
            changed_retained = True
            result.setdefault('first_failure',{'type':type(error).__name__,'message':str(error)})
        result.update(source_identity=plan['source_identity'],final_source_identity=final,
            source_unchanged=final==plan['source_identity'],wall_seconds=time.monotonic()-started,
            ownership_terminal='bounded_process cleanup completed; external owner survey still required',storage_usage=storage.usage())
        if not result['source_unchanged'] or changed_retained:
            result.update(status='mechanism_unverified',source_mutation=True)
        write(output/'transfer-report.json',result,storage)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker')
    parser.add_argument('--prepared-plan',type=Path)
    parser.add_argument('--prepared-plan-sha256')
    for name in ('repo','assets','output','history-root'):
        parser.add_argument('--'+name,type=Path)
    parser.add_argument('--plan-only',action='store_true')
    args = parser.parse_args()
    if args.worker is not None:
        return worker(json.loads(args.worker))
    if args.prepared_plan is not None:
        if args.prepared_plan_sha256 is None or args.plan_only or any(getattr(args,n) is not None for n in ('repo','assets','output','history_root')):
            parser.error('Prepared plan requires its hash and cannot be combined with planning arguments')
        plan = read_prepared_plan(args.prepared_plan,args.prepared_plan_sha256)
        return 0 if run_verifier(plan)['status']=='mechanism_checked' else 1
    if args.prepared_plan_sha256 is not None:
        parser.error('--prepared-plan required with its hash')
    if any(getattr(args,name) is None for name in ('repo','assets','output','history_root')):
        parser.error('--repo, --assets, --output and --history-root required')
    plan = make_plan(args.repo,args.assets,args.output,args.history_root)
    if args.plan_only:
        print(json.dumps(plan,indent=2,allow_nan=False))
        return 0
    return 0 if run_verifier(plan)['status']=='mechanism_checked' else 1


if __name__=='__main__':
    raise SystemExit(main())
