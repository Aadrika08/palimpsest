"""Fixed recorded-observation U diagnostic; source preparation only until GO."""
import argparse
import copy
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sys
import time
import uuid

import numpy as np
from palimpsest import artifacts, memory, memory_experiment, memory_task
from palimpsest.evaluate import bounded_process
from palimpsest.replay import _initial_snapshot, _register_initial
from palimpsest.snapshots import capture, invariant_hashes, read_snapshot, state_digest
from palimpsest.storage import GiB, MiB, StorageBudget, StorageLimits

REPO=Path(__file__).resolve().parents[1]
HELPER=REPO/'scripts/verify_memory_references.py'
spec=importlib.util.spec_from_file_location('observation_owner_helpers',HELPER)
refs=importlib.util.module_from_spec(spec);spec.loader.exec_module(refs)
neural,common=refs.neural,refs.common
HISTORICAL=refs.HISTORICAL
CONDITIONS=('own','swapped','sham','no-U')
# Exact own recordings, not favorable streams chosen after counterfactual outcomes.
SOURCES={
 'A':(
 ('s25/local_cue/change','3738f98942f94a058e8910fc950801c0','89605ddd9b23bcec98307172ab2359f17681f91b81168a82a4d4dc08664d4d82',131),
 ('s28/paired_cue/change','961bb028d2ae44d984e54818d52de01d','5bfcdf48d99ab46d2d3c6685fe415c4d96a887228da41476d390bf7eac03d643',132),
 ('s26/paired_cue/null','c40bde4304174a8eb2551f684de59001','1e9417e9402e2bd60514cd1d9f7097bc3aa728d38ea2230750ba3d47f6829c61',128),
 ('s31/local_cue/no-event','092810659ed8484eb082559f69df015d','fb25ea25e6008e7ec3631630240eb75287136ebdb91cdd54886adf04384261dc',130)),
 'B':(
 ('s24/local_cue/change','4a91588188f3490798ea213f2b583796','19f0952a70ac42276967950f5ef856f9f34bb498b68012a14df7ef164e60130a',130),
 ('s29/paired_cue/change','9e7b594954934d028b4a9302ab7eb270','1a544119dc928cbc81ecea17b5033631fbd0a0cc6ed59c333431f88b643ee0fb',131),
 ('s30/local_cue/null','027b3827af224839969285c70d161840','e94a0a4aab923bbf5a64b4e64afc759e27badf9a8ebf5b0a2681a6dfe40745ef',129),
 ('s27/paired_cue/no-event','49392deba7b74096a9b59b830c719a24','4d126dcc434bcc6fc44bd7dcacc96ae9b09f72c8051764ab501d4471e01b70fa',128))}
PRODUCERS={
 'A':('m5-counterbalance-stage-c4-20261003','f0ce3790bec39c29f59d7ea4490e35d669e4293d5565a68b9eddceca9a43d1a4','91aa2aa30ae5a25daf0286f880b4372d66eca9eb98ee0b29fb4b8a54f5aefaf1'),
 'B':('m5-counterbalance-stage-c-v3-20261003','f2389333ddbf0c6a0af00e38034261cadf735ecbd1da163bf1fb180f1cc03125','c8ba721b0b861cb554811d78791a5f90a5bb2b7d2f2f4ff32e691db106aa376d')}

# This subprocess uses only the frozen historical PYTHONPATH and helper graph.
READER_CODE='''import importlib.util,json,sys
from pathlib import Path
root=Path(sys.argv[1]);fixed=json.loads(sys.argv[2]);result={}
spec=importlib.util.spec_from_file_location("frozen_stream_reader",root/"scripts/verify_memory_counterbalance_comparison.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
for wave,info in fixed.items():
 folder,plan_sha,report_sha,sources=info;path=root/"runs"/folder
 plan=m.pinned_json(path/"comparison-plan.json",plan_sha)
 terminal=m.pinned_json(path/"comparison-report.json",report_sha)
 if terminal["status"]!="comparison_checked" or terminal["unattempted_stages"] or not terminal["source_unchanged"] or not terminal["retained_unchanged"]:raise ValueError("Historical gate not complete")
 histories=m.common.load_histories(plan["history_root"])
 if m.history_pins(plan["history_root"],histories)!=plan["history_inputs"]:raise ValueError("Historical E pins changed")
 for cell,identifier,digest,count in sources:
  rows=[r for r in terminal["runs"] if r["cell"]==cell and r["stage"]=="own"]
  jobs=[j for j in plan["jobs"] if m.admission.cell_key(j["cell"])==cell and j["stage"]=="own"]
  if len(rows)!=1 or len(jobs)!=1 or rows[0]["run_id"]!=identifier or jobs[0]["run_id"]!=identifier or rows[0]["snapshot_sha256"]!=digest:raise ValueError("Own join changed")
  row=rows[0];run=path/"runs"/identifier;job=m.pinned_json(path/(identifier+"-job.json"),m.common._hash(path/(identifier+"-job.json")))
  for k,v in jobs[0].items():
   if job[k]!=v:raise ValueError("Job not from fixed plan")
  if job["output"]!=str(run) or job["binding"]!=plan["bindings"][cell] or job["history_inputs"]!=plan["history_inputs"] or job["source_identity"]!=plan["source_identity"]:raise ValueError("Job lineage changed")
  original=m.verify_binding(job["binding"],protocol_sha256=plan["protocol_sha256"])
  data=m.common.read_run(run);native,entry,_=m._initial_snapshot(data)
  worker=m.pinned_json(run/"comparison-worker.json",row["worker_report_sha256"])
  if entry["sha256"]!=digest or len(data["rows"])!=count or data["manifest"]["final_phase"]!="terminated" or data["manifest"]["last_outcome"]["reason"]!="goal" or worker["snapshot_sha256"]!=digest or data["manifest"]["controller"]!="flynn" or data["manifest"]["requested_device"]!="cpu":raise ValueError("Own source terminal/native differs")
  anchors=[r for r in terminal["runs"] if r["cell"]==cell and r["stage"]=="anchor"]
  if len(anchors)!=1 or job["snapshot_path"]!=str(path/"runs"/anchors[0]["run_id"]/"snapshots/initial.snp") or job["snapshot_sha256"]!=anchors[0]["snapshot_sha256"]:raise ValueError("Wrong own ancestor")
  for k in ("repo","assets","history_root","source_identity","history_inputs"):
   if job[k]!=plan[k]:raise ValueError("Runtime job differs from frozen plan")
  if job["root_output"]!=str(path) or job["protocol_sha256"]!=plan["protocol_sha256"] or job["oracle_evidence"] is not None or job["selector"]!=m.selector_config("own",m.histories_for(job["cell"],histories),protocol_sha256=plan["protocol_sha256"]):raise ValueError("Own runtime condition/config differs")
  ancestor=m.read_snapshot(job["snapshot_path"])
  if job["expected_non_u"]!=(m.invariant_hashes(ancestor) if wave=="A" else job["binding"]["non_u"]):raise ValueError("Own ancestor guard changed")
  m.validate_selector_boundary(job,native,ancestor,data["events"],m.histories_for(job["cell"],histories))
  if m.common.baseline_invariants(native)!=job["binding"]["non_u"]:raise ValueError("Own boundary changed outside selector/U")
  m.neural.policy_bindings(data)
  comparison=[c for c in terminal["comparisons"] if c["cell"]==cell]
  if len(comparison)!=1:raise ValueError("Missing evaluator gold")
  # Independent acquired-expectation/actual-clearance proof, never select/fit.
  proof=m.gold_proof(job["binding"],original,data,worker)
  if proof["gold_target_ids"]!=comparison[0]["gold_target_ids"]:raise ValueError("Recorded gold inconsistent")
  pins=[*job["binding"]["pins"],*[{"path":str(path/n),"sha256":m.common._hash(path/n)} for n in ("comparison-plan.json","comparison-report.json",identifier+"-job.json")]]
  pins += [{"path":str(p),"sha256":m.common._hash(p)} for p in [*data["paths"],run/"snapshots/initial.snp",run/"snapshots/index.json",run/"comparison-worker.json",Path(job["snapshot_path"])]]
  for pin in plan["history_inputs"].values():pins.append({"path":pin["path"],"sha256":pin["sha256"]})
  distinct={}
  for pin in pins:
   if pin["path"] in distinct and distinct[pin["path"]]!=pin["sha256"]:raise ValueError("Conflicting pin")
   distinct[pin["path"]]=pin["sha256"]
  result[cell]={"wave":wave,"path":str(run),"run_id":identifier,"ticks":count,"snapshot_path":str(run/"snapshots/initial.snp"),"snapshot_sha256":digest,"case":job["binding"]["case"],"history_inputs":plan["history_inputs"],"history_root":plan["history_root"],"gold_proof":proof,"pins":[{"path":p,"sha256":h} for p,h in sorted(distinct.items())]}
if any(k in sys.modules for k in ("torch","mujoco","palimpsest.engine")):raise ValueError("Reader imported model/native")
print(json.dumps(result,sort_keys=True,allow_nan=False))
'''


def cell_tuple(cell):
    seed,relation,kind=cell.split('/')
    return int(seed[1:]),relation,kind


def protocol(wave):
    if wave not in SOURCES:raise ValueError('Only fixed A/C4 or B/C3 wave')
    return {'version':1,'claim':'frozen-observation-controller-diagnostic-not-a-trajectory',
        'wave':wave,'sources':[list(s) for s in SOURCES[wave]],'producer':list(PRODUCERS[wave]),
        'conditions':list(CONDITIONS),'owners':16 if wave=='A' else 20,'maximum_policy_calls':4800,
        'maximum_intervals_per_owner':300,'timeout_seconds':160,'internal_wall_seconds':150,
        'outer_timeout_seconds':2620 if wave=='A' else 3260,'snapshot_max_bytes':16*MiB,
        'derivative_max_bytes':192*MiB,'aggregate_max_bytes':(4 if wave=='A' else 5)*GiB,
        'min_free_bytes':2*GiB,'headroom_bytes':64*MiB,'log_max_bytes':MiB,
        'historical_commit':refs.HISTORICAL_COMMIT,'reader_sha256':memory.sha256(READER_CODE),
        'float_atol':1e-6,'float_rtol':1e-6,'held_out':False,'retries':0,
        'resource_reference':neural.PROTOCOL['resource_reference'],
        'normalization':'none' if wave=='A' else 'one-time-selector-only-preparation',
        'source_context':'recorded-own-policy-dependent-RGB-contact-symbolic-packets',
        'helper_sha256':common._hash(HELPER)}


def shared_selector():
    return {'version':1,'condition':'own','limit':1,'resource':None,
        'resource_sha256':memory.sha256(None),'provenance_sha256':memory.sha256(protocol('B'))}


def task_without_selector(state):
    value=copy.deepcopy(state);value.pop('selector',None)
    return state_digest(value)


def selector_only_native(native):
    value=copy.deepcopy(native);value['application']['memory'].pop('selector')
    return invariant_hashes(value)


def join_own(rows,jobs,source):
    cell,identifier,digest,_=source
    row=[r for r in rows if r['cell']==cell and r['stage']=='own']
    job=[j for j in jobs if tuple(j['cell'])==cell_tuple(cell) and j['stage']=='own']
    if len(row)!=1 or len(job)!=1 or row[0]['run_id']!=identifier or job[0]['run_id']!=identifier or row[0]['snapshot_sha256']!=digest:
        raise ValueError('Fixed unique own-stream/plan/native join differs')
    return copy.deepcopy(row[0])


def validate_observation(observation):
    if (set(observation)!={'cam_left','cam_right','sensors'} or
            set(observation['sensors'])!={'collision','collision_angle','wind_direction'}):
        raise ValueError('Undeclared policy input')
    for name in ('cam_left','cam_right'):
        a=observation[name]
        if not isinstance(a,np.ndarray) or a.dtype!=np.uint8 or a.ndim!=3 or a.shape[2]!=3 or min(a.shape[:2])==0:
            raise ValueError('Frozen camera must be original HWC uint8 RGB')
    for name in ('collision','collision_angle'):
        x=observation['sensors'][name]
        if name=='collision_angle' and x is None:continue
        a=np.asarray(x)
        if a.size!=1 or a.dtype.kind not in 'biuf' or not np.isfinite(a).all():raise ValueError('Invalid frozen contact')
    x=np.asarray(observation['sensors']['wind_direction'])
    if x.shape!=(2,) or x.dtype.kind not in 'iuf' or not np.isfinite(x).all():raise ValueError('Invalid recorded bearing')


def validate_frame(frame):
    memory._fields(frame,'tick packet observation source_decisions source_inspect source_result source_input_sha256 source_result_sha256')
    validate_observation(frame['observation'])
    if state_digest(frame['observation'])!=frame['source_input_sha256'] or frame['source_result_sha256']!={k:state_digest(v) for k,v in frame['source_result'].items()}:
        raise ValueError('Frozen frame input/result hashes differ before inference')
    numeric_results([frame['source_result']])
    if type(frame['tick']) is not int or frame['tick']!=frame['packet']['tick']:raise ValueError('Packet/row tick differs')


def audit_frames(state,frames):
    """Audit ALL packets and raw input structure before the first policy call."""
    task=memory_task.validate_state(state)
    if not 1<=len(frames)<=300:raise ValueError('Frozen stream length outside cap')
    for frame in frames:
        validate_frame(frame)
        task,_,_=memory_task.advance_memory(task,frame['packet'])
    return state_digest(task)


def advance_frame(state,frame,policy):
    """A failed cue lookup commits neither task state nor a policy invocation."""
    validate_frame(frame)
    try:
        task,bearing,decisions=memory_task.advance_memory(state,frame['packet'])
    except memory_task.CueUnavailable as error:
        return {'status':'censored_cue_unavailable','error':str(error),'state':copy.deepcopy(state),
            'bearing':None,'decisions':[],'result':None}
    observation={**frame['observation'],'sensors':{**copy.deepcopy(frame['observation']['sensors']),
        'wind_direction':bearing.copy()}}
    result=policy.act(observation)
    return {'status':'committed','state':task,'bearing':bearing,'decisions':decisions,'result':result,
        'input_sha256':state_digest(observation)}


def prepare_bindings(output):
    before=refs.historical_identity()
    fixed={w:[*PRODUCERS[w],[list(s) for s in SOURCES[w]]] for w in SOURCES}
    env={**os.environ,'PYTHONPATH':str(HISTORICAL/'src'),'OMP_NUM_THREADS':'2'}
    supervised=bounded_process([sys.executable,'-c',READER_CODE,str(HISTORICAL),json.dumps(fixed)],output,40,env,log_max_bytes=MiB)
    if supervised['status']!='completed' or supervised.get('returncode')!=0 or refs.historical_identity()!=before:
        raise ValueError('Fixed historical reader failed or drifted')
    value={'version':1,'reader_identity':before,'reader_sha256':memory.sha256(READER_CODE),
        'sources':artifacts._json(artifacts._read(Path(output)/'stdout.log',MiB))}
    validate_bindings(value);common._write(Path(output)/'bindings.json',value)
    return value


def validate_bindings(value):
    memory._fields(value,'version reader_identity reader_sha256 sources');memory._version(value['version'])
    memory._bounded(value,MiB)
    if value['reader_identity']!=refs.historical_identity() or value['reader_sha256']!=memory.sha256(READER_CODE):
        raise ValueError('Historical reader identity changed')
    expected={s[0]:(w,s) for w,ss in SOURCES.items() for s in ss}
    if set(value['sources'])!=set(expected):raise ValueError('Eight fixed sources required')
    for cell,(wave,source) in expected.items():
        b=value['sources'][cell];memory._fields(b,'wave path run_id ticks snapshot_path snapshot_sha256 case history_inputs history_root gold_proof pins');_,identifier,digest,count=source
        path=HISTORICAL/'runs'/PRODUCERS[wave][0]/'runs'/identifier
        if (b['wave']!=wave or b['path']!=str(path) or b['run_id']!=identifier or b['ticks']!=count
                or b['snapshot_path']!=str(path/'snapshots/initial.snp') or b['snapshot_sha256']!=digest):
            raise ValueError('Fixed stream identity/path/count changed')
        if len({p['path'] for p in b['pins']})!=len(b['pins']) or not b['pins']:raise ValueError('Pin coverage duplicates/empty')
        for pin in b['pins']:
            if common._hash(artifacts._safe_path(pin['path']))!=pin['sha256']:raise ValueError('Frozen input changed')
        path_root=path.parents[1]
        plan=neural.read_prepared_plan(path_root/'comparison-plan.json',PRODUCERS[wave][1])
        terminal=neural.read_prepared_plan(path_root/'comparison-report.json',PRODUCERS[wave][2])
        summary=join_own(terminal['runs'],plan['jobs'],source)
        data=artifacts._load(path)
        controls=[path_root/'comparison-plan.json',path_root/'comparison-report.json',path_root/(identifier+'-job.json')]
        job=artifacts._json(artifacts._read(controls[2],128*1024))
        if job['binding']!=plan['bindings'][cell] or job['history_inputs']!=plan['history_inputs'] or b['case']!=job['binding']['case'] or b['history_root']!=plan['history_root'] or b['history_inputs']!=plan['history_inputs']:
            raise ValueError('Binding metadata differs from pinned producer')
        expected_paths={p['path'] for p in plan['bindings'][cell]['pins']}|{str(p) for p in [*controls,*data['paths'],path/'snapshots/initial.snp',path/'snapshots/index.json',path/'comparison-worker.json',Path(job['snapshot_path'])]}|{p['path'] for p in plan['history_inputs'].values()}
        if {p['path'] for p in b['pins']}!=expected_paths:raise ValueError('Exact frozen input-pin path coverage differs')
        pins={p['path']:p['sha256'] for p in b['pins']}
        if pins[str(path/'comparison-worker.json')]!=summary['worker_report_sha256']:raise ValueError('Worker pin not bound to terminal')
        proof=b['gold_proof'];comparison=next(c for c in terminal['comparisons'] if c['cell']==cell)
        if proof!=comparison['oracle_evidence']:raise ValueError('Gold proof differs from independently retained geometry evaluation')
        native=read_snapshot(b['snapshot_path']);app=native['application'];task=memory_task.validate_state(app['memory'])
        if (common._hash(b['snapshot_path'])!=digest or app['controller']!='flynn' or native['identity']['policy']['device']!='cpu'
                or app['phase']!='paused' or app['episode_step']!=300 or app['total_tick']!=300
                or task['cursor']['tick']!=299 or task['detector']['tick']!=299
                or app['world_task_state']['case']!=b['case'] or b['case']['seed']!=cell_tuple(cell)[0]):
            raise ValueError('Actual native pre-event/controller/case boundary differs')
        if task['selector']['condition']!='own' or task['selector']['resource'] is not None or task['selector']['limit']!=1:
            raise ValueError('Source has another selector/resource')
    return copy.deepcopy(value)


def read_stream(binding):
    """Verified published inputs and exact raw contact, with no private steering."""
    run=Path(binding['path']);data=common.read_run(run)
    native,entry,_=_initial_snapshot(data)
    if entry['sha256']!=binding['snapshot_sha256'] or len(data['rows'])!=binding['ticks']:raise ValueError('Stream changed')
    neural.policy_bindings(data)
    events=data['events'];frames=[]
    sensed=[e for e in events if e['kind']=='memory_sensed']
    if [e['episode_step'] for e in sensed]!=[r['tick'] for r in data['rows']]:raise ValueError('Extra/missing sensed boundary')
    calls=[e for e in events if e['kind']=='neural_policy_call']
    source_task=copy.deepcopy(native['application']['memory'])
    for row,packet_event,call in zip(data['rows'],sensed,calls):
        tick=row['tick']
        if any((e.get('episode'),e.get('episode_step'),e.get('tick'))!=(0,tick,tick) for e in (packet_event,call)):
            raise ValueError('Stream outer/local boundary differs')
        packet=packet_event['packet']
        if packet['tick']!=tick or packet['episode_id']!=source_task['episode_id']:raise ValueError('Packet identity differs')
        observation={k:row[k] for k in ('cam_left','cam_right')};observation['sensors']=copy.deepcopy(call['sensors'])
        if state_digest(observation)!=call['observation_sha256']:raise ValueError('Recorded actual policy input hash differs')
        decisions=[e['detail'] for e in events if e['kind']=='memory_decision' and e.get('episode_step')==tick]
        inspected=[e['memory'] for e in events if e['kind']=='memory_inspected' and e.get('episode_step')==tick]
        source_task,bearing,audit=memory_task.advance_memory(source_task,packet)
        if audit!=decisions or inspected!=[memory_task.inspect(source_task)] or bearing!=call['sensors']['wind_direction']:
            raise ValueError('Source task prefix not reproduced exactly')
        frames.append({'tick':tick,'packet':copy.deepcopy(packet),'observation':observation,
            'source_decisions':decisions,'source_inspect':inspected[0],
            'source_result':{k:row[k] for k in ('action','encoded_input','raw_output')},
            'source_input_sha256':call['observation_sha256'],'source_result_sha256':call['result_sha256']})
    audit_frames(native['application']['memory'],frames)
    worker=artifacts._json(artifacts._read(run/'comparison-worker.json',MiB))
    if source_task!=worker['final_memory']:raise ValueError('Source final task state differs from full reproduced prefix')
    return frames,native


def admitted_native(native):
    """Only the existing schema3 -> schema4/null-task compatibility admission."""
    value=copy.deepcopy(native);app=value['application']
    if type(app['schema_version']) is not int or app['schema_version']!=3 or 'task_state' in app or app['scenario']!='memory-passages':
        raise ValueError('Pinned source requires exactly legacy memory schema3 without task_state')
    app.update(schema_version=4,task_state=None)
    original=copy.deepcopy(value);original['application'].pop('task_state');original['application']['schema_version']=3
    if state_digest(original)!=state_digest(native):raise ValueError('Compatibility admission changed unrelated source state')
    return value


def source_identity(assets):
    value=neural.source_identity(REPO,assets)
    value['observation_stream_driver_sha256']=common._hash(Path(__file__))
    value['historical_reader_identity']=refs.historical_identity()
    return value


def budget(output,wave):
    p=protocol(wave)
    return StorageBudget((Path(output),),StorageLimits(max_bytes=p['aggregate_max_bytes'],min_free_bytes=2*GiB,
        max_runs=p['owners'],max_snapshots=1),headroom_bytes=64*MiB)


def validate_job(job,*,prepared=False):
    memory._fields(job,'repo assets root_output output run_id wave cell stage protocol_sha256 source_identity bindings_path bindings_sha256 source snapshot_path snapshot_sha256 expected_non_u')
    memory._bounded(job,128*1024);artifacts._id(job['run_id'])
    p=protocol(job['wave']);stages=('prepare',*CONDITIONS) if job['wave']=='B' else CONDITIONS
    if (job['repo']!=str(REPO) or job['cell'] not in [s[0] for s in SOURCES[job['wave']]] or job['stage'] not in stages
            or job['protocol_sha256']!=memory.sha256(p) or Path(job['output'])!=Path(job['root_output'])/'runs'/job['run_id']
            or any(not Path(job[k]).is_absolute() for k in ('assets','root_output','output','bindings_path'))):
        raise ValueError('Fixed diagnostic job/path/condition differs')
    raw=neural.read_prepared_plan(job['bindings_path'],job['bindings_sha256'])
    if memory.canonical_bytes(raw['sources'][job['cell']])!=memory.canonical_bytes(job['source']):raise ValueError('Prepared source substituted')
    if not prepared:
        memory._digest(job['snapshot_sha256'])
        if not Path(job['snapshot_path']).is_absolute():raise ValueError('Snapshot path must be absolute')
        if job['wave']=='A' or job['stage']=='prepare':
            if (job['snapshot_path']!=job['source']['snapshot_path'] or job['snapshot_sha256']!=job['source']['snapshot_sha256']):
                raise ValueError('Owner not using its fixed historical snapshot')
        if common._hash(job['snapshot_path'])!=job['snapshot_sha256']:raise ValueError('Ancestor snapshot changed')
        native=read_snapshot(job['snapshot_path'])
        current=admitted_native(native) if job['wave']=='A' or job['stage']=='prepare' else native
        if invariant_hashes(current)!=job['expected_non_u']:raise ValueError('Expected full non-U guard differs')
    elif any(job[k] is not None for k in ('snapshot_path','snapshot_sha256','expected_non_u')):raise ValueError('Prepared jobs cannot bind unacquired preparation')
    return copy.deepcopy(job)


def make_plan(assets,output,bindings_path,digest,wave):
    p=protocol(wave);raw=validate_bindings(neural.read_prepared_plan(bindings_path,digest))
    assets,output,bindings_path=map(lambda x:artifacts._safe_path(Path(x).resolve()),(assets,output,bindings_path))
    identity=source_identity(assets);jobs=[]
    for source in SOURCES[wave]:
        for stage in (('prepare',*CONDITIONS) if wave=='B' else CONDITIONS):
            identifier=uuid.uuid4().hex
            jobs.append(validate_job({'repo':str(REPO),'assets':str(assets),'root_output':str(output),
                'output':str(output/'runs'/identifier),'run_id':identifier,'wave':wave,'cell':source[0],'stage':stage,
                'protocol_sha256':memory.sha256(p),'source_identity':identity,'bindings_path':str(bindings_path),
                'bindings_sha256':digest,'source':raw['sources'][source[0]],
                'snapshot_path':None,'snapshot_sha256':None,'expected_non_u':None},prepared=True))
    return {'version':1,'protocol':p,'protocol_sha256':memory.sha256(p),'output':str(output),'source_identity':identity,'jobs':jobs}


def validate_plan(plan):
    memory._fields(plan,'version protocol protocol_sha256 output source_identity jobs');memory._version(plan['version']);memory._bounded(plan,2*MiB)
    wave=plan['protocol']['wave'];p=protocol(wave)
    expected=[(s[0],stage) for s in SOURCES[wave] for stage in (('prepare',*CONDITIONS) if wave=='B' else CONDITIONS)]
    if (memory.canonical_bytes(plan['protocol'])!=memory.canonical_bytes(p) or plan['protocol_sha256']!=memory.sha256(p)
            or [(j['cell'],j['stage']) for j in plan['jobs']]!=expected or len({j['run_id'] for j in plan['jobs']})!=len(expected)):
        raise ValueError('Exact fixed diagnostic plan/owners required')
    for job in plan['jobs']:
        validate_job(job,prepared=True)
        if job['source_identity']!=plan['source_identity'] or job['root_output']!=plan['output'] or job['assets']!=plan['jobs'][0]['assets']:
            raise ValueError('Plan owner identity differs')
    return copy.deepcopy(plan)


def condition_u(job):
    # Verify bundles for audit; only validated U crosses into task/policy behavior.
    histories=common.load_histories(job['source']['history_root'])
    mapping=histories if cell_tuple(job['cell'])[1]=='local_cue' else {'own':histories['swapped'],'swapped':histories['own']}
    for pin in job['source']['history_inputs'].values():
        value=artifacts._json(artifacts._read(Path(pin['path']),32*MiB))
        if common._hash(pin['path'])!=pin['sha256'] or memory.sha256(value['e'])!=pin['e_sha256'] or memory.sha256(value['u'])!=pin['u_sha256']:
            raise ValueError('E-only historical bundle pin differs')
    return common.condition_u('own' if job['stage']=='prepare' else job['stage'],mapping)


def same_result(actual,expected):
    for key in ('action','encoded_input','raw_output'):
        a,b=np.asarray(actual[key]),np.asarray(expected[key])
        if a.dtype!=b.dtype or a.shape!=b.shape or not np.isfinite(a).all() or not np.allclose(a,b,atol=1e-6,rtol=1e-6):
            raise ValueError('Own diagnostic neural result differs from fixed recorded stream')


def numeric_results(results):
    shapes={'action':(2,),'raw_output':(2,),'encoded_input':(4813,)}
    arrays={k:np.stack([r[k] for r in results]) if results else np.empty((0,*shape),np.float32) for k,shape in shapes.items()}
    for k,shape in shapes.items():
        if arrays[k].dtype!=np.float32 or arrays[k].shape!=(len(results),*shape) or not np.isfinite(arrays[k]).all():raise ValueError('Diagnostic result shape/dtype differs')
    return arrays


def publish_derivative(run,traces,results,storage):
    # No duplicate cameras, fabricated physical tick, or executable trajectory format.
    trace=b''.join(memory.canonical_bytes(t)+b'\n' for t in traces)
    buf=io.BytesIO();np.savez(buf,**numeric_results(results));arrays=buf.getvalue()
    recording_bytes=sum(p.stat().st_size for p in (run/'recording').rglob('*') if p.is_file())
    if recording_bytes+len(trace)+len(arrays)>192*MiB:raise ValueError('Derivative exceeds per-owner cap')
    for name,payload in (('diagnostic-trace.jsonl',trace),('diagnostic-arrays.npz',arrays)):
        path=run/name;storage.check(len(payload),path=path)
        temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_bytes(payload);temporary.replace(path)
    return {'trace_sha256':common._hash(run/'diagnostic-trace.jsonl'),'arrays_sha256':common._hash(run/'diagnostic-arrays.npz'),
        'trace_bytes':len(trace),'arrays_bytes':len(arrays)}


def write_report(path,value,storage):
    temporary=Path(path).with_suffix(Path(path).suffix+'.tmp')
    neural.write(temporary,value,storage);temporary.replace(path)


def worker(raw):
    started=time.monotonic();job=validate_job(raw);run=Path(job['output']);storage=budget(job['root_output'],job['wave'])
    engine=None;results=[];traces=[]
    report={'status':'failed','run_id':job['run_id'],'stage':job['stage'],'cell':job['cell'],'policy_calls':0,'task_success':None}
    try:
        if source_identity(job['assets'])!=job['source_identity']:raise ValueError('Executor/assets drifted')
        validate_bindings(neural.read_prepared_plan(job['bindings_path'],job['bindings_sha256']))
        frames,source_native=read_stream(job['source'])  # Complete hashes/packets before policy/model initialization.
        native=read_snapshot(job['snapshot_path']);u=condition_u(job)
        admission=admitted_native(native) if job['wave']=='A' or job['stage']=='prepare' else copy.deepcopy(native)
        if job['stage']=='prepare' and u!=native['application']['memory']['u']:raise ValueError('Preparation would replace U')
        from palimpsest.engine import Engine
        if Path(sys.modules['palimpsest.engine'].__file__).resolve()!=REPO/'src/palimpsest/engine.py':raise ValueError('Wrong executor module')
        storage.check(208*MiB,path=run)
        engine=Engine.open(REPO,job['assets'],run/'recording',run_id=job['run_id'],controller='flynn',device='cpu',
            seed=job['source']['case']['seed'],scenario='memory-passages',memory_case=job['source']['case'],
            max_bytes=192*MiB,storage_budget=storage,restore_snapshot=admission,memory_u=None if job['stage']=='prepare' else u)
        engine._event('diagnostic_source_admission',raw_source_snp_sha256=job['snapshot_sha256'],
            source_state_sha256=state_digest(native),admitted_state_sha256=state_digest(admission),
            structural_fields=['application.schema_version','application.task_state'] if admission['application']['schema_version']!=native['application']['schema_version'] else [])
        initial=capture(engine.env,engine.observation,policy=engine.policy,application=engine.application_state())
        if invariant_hashes(initial)!=job['expected_non_u'] or engine.memory['u']!=u:raise ValueError('Atomic admission/U-only invariant changed')
        report['structural_admission']={'source_schema':native['application']['schema_version'],
            'source_snp_sha256':job['snapshot_sha256'],'post_schema':initial['application']['schema_version'],
            'exact_non_u':invariant_hashes(initial)}
        if job['stage']=='prepare':
            before=copy.deepcopy(engine.memory);engine.memory=memory_task.configure_selector(engine.memory,shared_selector())
            if task_without_selector(before)!=task_without_selector(engine.memory):raise ValueError('Preparation changed task beyond selector')
            engine._event('diagnostic_selector_prepared',configuration=shared_selector(),protocol_sha256=job['protocol_sha256'])
            prepared=capture(engine.env,engine.observation,policy=engine.policy,application=engine.application_state())
            if selector_only_native(initial)!=selector_only_native(prepared) or before['u']!=engine.memory['u']:
                raise ValueError('Preparation changed physics/policy/RNG/task beyond selector')
            report['selector_preparation']={'before':before['selector'],'after':engine.memory['selector'],
                'other_task_fields_sha256':task_without_selector(before),'other_native_fields':selector_only_native(initial)}
            initial=prepared
        _register_initial(engine,run,neural._SnapshotBudget(storage))
        registered=read_snapshot(run/'snapshots/initial.snp')
        if invariant_hashes(registered)!=invariant_hashes(initial):raise ValueError('Registered native changed')
        report.update(initial_non_u=invariant_hashes(registered),initial_u_sha256=memory.sha256(engine.memory['u']),
            snapshot_sha256=common._hash(run/'snapshots/initial.snp'),snapshot_path=str(run/'snapshots/initial.snp'))
        task=copy.deepcopy(engine.memory);frozen_physics=state_digest({k:initial[k] for k in ('native_data','integration','environment','observation')})
        if job['stage']!='prepare':
            for frame in frames:
                if time.monotonic()-started>150:raise TimeoutError('Diagnostic worker deadline')
                value=advance_frame(task,frame,engine.policy)
                trace={'tick':frame['tick'],'packet_sha256':memory.sha256(frame['packet']),
                    'status':value['status'],'task_before_sha256':memory.sha256(task),'decisions':value['decisions'],
                    'bearing':value['bearing'],'task_after_sha256':memory.sha256(value['state'])}
                if value['status']!='committed':
                    trace['error']=value['error'];traces.append(trace);report['censored_boundary']=frame['tick'];break
                task=value['state'];results.append(value['result'])
                trace.update(input_sha256=value['input_sha256'],result_sha256={k:state_digest(value['result'][k]) for k in ('action','encoded_input','raw_output')},
                    maximum_abs_difference={k:float(np.max(np.abs(value['result'][k]-frame['source_result'][k]))) for k in ('action','encoded_input','raw_output')})
                traces.append(trace)
                if job['stage'] in ('own','sham'):
                    if value['decisions']!=frame['source_decisions'] or value['bearing']!=frame['observation']['sensors']['wind_direction']:
                        raise ValueError('Own/sham task/cue prefix differs')
                    observed=memory_task.inspect(task);expected=copy.deepcopy(frame['source_inspect'])
                    if job['wave']=='B':expected['selector']=memory_task.inspect(task)['selector']
                    if observed!=expected:raise ValueError('Own/sham task fields differ beyond declared C3 selector')
                    same_result(value['result'],frame['source_result'])
        # Memory is local diagnostic state; world/task clocks and Engine memory never advance.
        final=capture(engine.env,engine.observation,policy=engine.policy,application=engine.application_state())
        if (state_digest({k:final[k] for k in ('native_data','integration','environment','observation')})!=frozen_physics
                or engine.episode_step!=300 or engine.total_tick!=300 or state_digest(engine.memory)!=state_digest(initial['application']['memory'])):
            raise ValueError('Diagnostic advanced world/Engine memory')
        report.update(status='diagnostic_censored' if 'censored_boundary' in report else 'diagnostic_checked',
            policy_calls=len(results),source_intervals=len(frames),final_memory=task,world_advanced=False,
            derived_prefix_only=True,final_local_cursor=task['cursor']['tick'],engine_boundary=engine.total_tick,
            final_policy_sha256=state_digest(final['policy']),final_rng_sha256=state_digest(final['rng']))
    except Exception as error:
        report['error']={'type':type(error).__name__,'message':str(error)}
    finally:
        if engine is not None:
            try:engine.close()
            except Exception as error:report.update(status='failed',cleanup_error={'type':type(error).__name__,'message':str(error)})
    report['policy_calls']=len(results)
    try:
        report['derivative']=publish_derivative(run,traces,results,storage)
        validate_bindings(neural.read_prepared_plan(job['bindings_path'],job['bindings_sha256']))
        if source_identity(job['assets'])!=job['source_identity']:raise ValueError('Executor drifted after diagnostic')
        report['wall_seconds']=time.monotonic()-started
        if report['wall_seconds']>150:raise TimeoutError('Final diagnostic admission exceeds150 seconds')
    except Exception as error:report.update(status='failed',final_error={'type':type(error).__name__,'message':str(error)})
    write_report(run/'diagnostic-worker.json',report,storage)
    final_elapsed=time.monotonic()-started
    if final_elapsed>150:
        report.update(status='failed',final_wall_seconds=final_elapsed,deadline_exceeded=True)
        write_report(run/'diagnostic-worker.json',report,storage)
    return 0 if report['status'] in ('diagnostic_checked','diagnostic_censored') else 1


def derivative_readout(job,traces,final_memory):
    """Evaluator-only occupancy truth; these are supplied-stream times, not navigation."""
    proof=job['source']['gold_proof'];gold=set(proof['gold_target_ids'])
    selections=[d['selection'] for t in traces for d in t['decisions'] if d['kind']=='memory_selection']
    inspections=[d for t in traces for d in t['decisions'] if d['kind']=='memory_inspection']
    before=read_snapshot(job['source']['snapshot_path'])['application']['memory']['m']
    after=common.occupancy(job['source']['case'],proof['after_circles'])
    revisions=[d['revision'] for t in traces for d in t['decisions'] if d['kind']=='memory_revision']
    timing=[]
    for fact in before['facts']:
        samples=[v for v in revisions if v['fact_id']==fact['id'] and v['after']['status']=='observed' and v['after']['estimate']==after[fact['subject_id']]]
        first=min((v['tick'] for v in samples),default=None);changed=fact['estimate']!=after[fact['subject_id']]
        timing.append({'fact_id':fact['id'],'stale_value_changed':changed,'first_correct_commit_in_supplied_stream':first,
            'first_stale_value_correction_tick':first if changed else None,'first_confirmation_tick':first if not changed else None})
    targets=set().union(*(set(s['target_ids']) for s in selections))
    source_trigger=proof['trigger'];u=condition_u(job)
    access={'m':before,'trigger':source_trigger,'u':u}
    behavior={} if source_trigger is None else {'m':before,'trigger':source_trigger,'u.payload':u['payload']}
    if cell_tuple(job['cell'])[2]=='no-event' and (selections or inspections or behavior):raise ValueError('No-event invoked selection/inspection')
    return {'committed_selector_decisions':len(selections),'committed_target_ids':sorted(targets),
        'targeting_censored':bool(traces and traces[-1]['status']!='committed'),
        'false_targets':len(targets-gold),'missed_targets':len(gold-targets),
        'precision':len(targets&gold)/len(targets) if targets else None,'recall':len(targets&gold)/len(gold) if gold else None,
        'gold_target_ids':sorted(gold),'timing':timing,'inspection_counts':{k:sum(d['status']==k for d in inspections) for k in ('requested','started','resolved','timeout')},
        'validation_input_bytes':len(memory.canonical_bytes(access)),
        'behavior_input_bytes_if_witnessed':len(memory.canonical_bytes(behavior)) if behavior else 0,
        'payload_bytes':len(memory.canonical_bytes(u['payload'])),'envelope_bytes':len(memory.canonical_bytes(u)),
        'runtime_history_bytes':0,'final_memory_sha256':memory.sha256(final_memory),
        'source_context_goal_boundary':300+job['source']['ticks'],'diagnostic_goal_tick':None,'task_success':None}


def validate_stage(job,supervised):
    if supervised['status']!='completed' or supervised.get('returncode')!=0:raise ValueError('Diagnostic owner infrastructure failure')
    run=Path(job['output']);report=artifacts._json(artifacts._read(run/'diagnostic-worker.json',MiB))
    data=artifacts._load(run);native,entry,_=_initial_snapshot(data)
    ancestor=read_snapshot(job['snapshot_path']);admitted=admitted_native(ancestor) if job['wave']=='A' or job['stage']=='prepare' else ancestor
    if (report['status'] not in ('diagnostic_checked','diagnostic_censored') or report['wall_seconds']>150
            or report['snapshot_sha256']!=entry['sha256'] or entry['sha256']!=common._hash(run/'snapshots/initial.snp')
            or (run/'snapshots/initial.snp').stat().st_size>16*MiB or data['manifest']['recorded_ticks']!=0
            or data['manifest']['total_tick']!=300 or data['manifest']['final_phase']!='paused'
            or any(e['kind'] in ('memory_sensed','neural_policy_call','memory_world_changed','command_received') for e in data['events'])):
        raise ValueError('Zero-physical-row derivative recording/native/deadline differs')
    restored=[e for e in data['events'] if e['kind']=='application_restored']
    substitutions=[e for e in data['events'] if e['kind']=='memory_u_replaced']
    admissions=[e for e in data['events'] if e['kind']=='diagnostic_source_admission']
    if (len(restored)!=1 or restored[0]['parent_run_id']!=ancestor['application']['source_run_id']
            or restored[0]['parent_event_prefix']!=ancestor['application']['event_prefix']
            or len(admissions)!=1 or admissions[0]['raw_source_snp_sha256']!=job['snapshot_sha256']
            or admissions[0]['source_state_sha256']!=state_digest(ancestor) or admissions[0]['admitted_state_sha256']!=state_digest(admitted)
            or any(e['sequence']>=native['application']['event_prefix']['event_count'] for e in [*restored,*substitutions,*admissions])):
        raise ValueError('Initial source/admission/event prefix not bound')
    if job['stage']!='prepare' and (len(substitutions)!=1 or substitutions[0]['old_u']!=ancestor['application']['memory']['u']
            or substitutions[0]['new_u']!=native['application']['memory']['u'] or substitutions[0]['invariant_hashes']!=job['expected_non_u']):
        raise ValueError('Exact U-only substitution proof differs')
    configured=[e for e in data['events'] if e['kind']=='diagnostic_selector_prepared']
    if job['stage']=='prepare':
        if (selector_only_native(native)!=selector_only_native(admitted) or native['application']['memory']['u']!=ancestor['application']['memory']['u']
                or native['application']['memory']['selector']!=shared_selector() or report['policy_calls']!=0):
            raise ValueError('C3 preparation changed non-selector fields')
        if substitutions or len(configured)!=1 or configured[0]['configuration']!=shared_selector() or configured[0]['protocol_sha256']!=job['protocol_sha256'] or configured[0]['sequence']>=native['application']['event_prefix']['event_count']:
            raise ValueError('C3 selector preparation prefix differs')
    elif configured or invariant_hashes(native)!=job['expected_non_u'] or native['application']['memory']['u']!=condition_u(job):
        raise ValueError('Strict full non-U/U fork differs')
    if report['initial_non_u']!=invariant_hashes(native) or report['initial_u_sha256']!=memory.sha256(native['application']['memory']['u']):raise ValueError('Initial report/native differs')
    trace_path=run/'diagnostic-trace.jsonl';array_path=run/'diagnostic-arrays.npz';published=report['derivative']
    recording_bytes=sum(p.stat().st_size for p in (run/'recording').rglob('*') if p.is_file())
    if (recording_bytes+trace_path.stat().st_size+array_path.stat().st_size>192*MiB or common._hash(trace_path)!=published['trace_sha256']
            or common._hash(array_path)!=published['arrays_sha256'] or trace_path.stat().st_size!=published['trace_bytes']
            or array_path.stat().st_size!=published['arrays_bytes']):raise ValueError('Derivative hashes/bytes differ')
    payload=artifacts._read(trace_path,192*MiB)
    if payload and not payload.endswith(b'\n'):raise ValueError('Incomplete diagnostic trace')
    traces=[artifacts._json(line) for line in payload.splitlines()]
    with np.load(array_path,allow_pickle=False) as archive:
        if set(archive.files)!={'action','encoded_input','raw_output'}:raise ValueError('Unknown derivative array')
        arrays={k:archive[k].copy() for k in archive.files}
    results=[{k:v[i] for k,v in arrays.items()} for i in range(report['policy_calls'])]
    if any(len(v)!=report['policy_calls'] for v in arrays.values()) or state_digest(numeric_results(results))!=state_digest(arrays):raise ValueError('Policy call/count/arrays differ')
    frames,_=read_stream(job['source']);task=copy.deepcopy(native['application']['memory'])
    if job['stage']=='prepare':
        if traces or results or report['final_memory']!=task:raise ValueError('Zero-tick preparation ran policy/task')
    else:
        if not 1<=len(traces)<=len(frames):raise ValueError('Missing/extra derivative frames')
        index=0
        for frame,trace in zip(frames,traces):
            if trace['tick']!=frame['tick'] or trace['packet_sha256']!=memory.sha256(frame['packet']) or trace['task_before_sha256']!=memory.sha256(task):raise ValueError('Trace source/task boundary differs')
            try:next_task,bearing,decisions=memory_task.advance_memory(task,frame['packet'])
            except memory_task.CueUnavailable as error:
                if (trace is not traces[-1] or trace['status']!='censored_cue_unavailable' or trace['error']!=str(error)
                        or trace['decisions'] or trace['bearing'] is not None or trace['task_after_sha256']!=memory.sha256(task)
                        or report['status']!='diagnostic_censored' or report['censored_boundary']!=frame['tick']):raise ValueError('Censor/no-commit boundary differs')
                break
            if trace['status']!='committed' or trace['decisions']!=decisions or trace['bearing']!=bearing or trace['task_after_sha256']!=memory.sha256(next_task):raise ValueError('Recorded task decision/revision differs')
            observation={**frame['observation'],'sensors':{**copy.deepcopy(frame['observation']['sensors']),'wind_direction':bearing}}
            result=results[index];index+=1
            expected_difference={k:float(np.max(np.abs(result[k]-frame['source_result'][k]))) for k in result}
            if (trace['input_sha256']!=state_digest(observation) or trace['result_sha256']!={k:state_digest(v) for k,v in result.items()}
                    or trace['maximum_abs_difference']!=expected_difference):raise ValueError('Actual policy-input/output binding differs')
            if job['stage'] in ('own','sham'):
                if decisions!=frame['source_decisions'] or state_digest(observation)!=state_digest(frame['observation']):raise ValueError('Own/sham source input/task differs')
                same_result(result,frame['source_result'])
            task=next_task
        if index!=len(results) or report['final_memory']!=task or (report['status']=='diagnostic_checked' and len(traces)!=len(frames)):
            raise ValueError('Diagnostic terminal prefix differs')
    report['readout']=derivative_readout(job,traces,task) if job['stage']!='prepare' else None
    return report,native,traces,arrays


def compare_treatments(rows):
    own=rows['own'];comparisons=[]
    for condition in CONDITIONS[1:]:
        other=rows[condition];first=None
        for a,b in zip(own[2],other[2]):
            if (a['decisions'],a['bearing'],a['status'])!=(b['decisions'],b['bearing'],b['status']):
                first={'tick':a['tick'],'kind':'task-or-cue'};break
            if a['status']=='committed':
                i=a['tick']-300
                if any(not np.allclose(own[3][k][i],other[3][k][i],atol=1e-6,rtol=1e-6) for k in own[3]):
                    first={'tick':a['tick'],'kind':'neural-output-or-action'};break
        comparisons.append({'condition':condition,'shared_prefix':min(len(own[2]),len(other[2])),
            'same_length':len(own[2])==len(other[2]),'first_difference':first,
            'scope':'supplied-observation sensitivity, not navigation or independent frames'})
    sham=comparisons[1]
    if (not sham['same_length'] or sham['first_difference'] is not None or
            any(own[0][k]!=rows['sham'][0][k] for k in ('final_policy_sha256','final_rng_sha256'))):raise ValueError('Own/sham diagnostic differs')
    return comparisons


def run_verifier(raw,*,started=None):
    if started is None:started=time.monotonic()
    plan=validate_plan(raw);wave=plan['protocol']['wave'];p=protocol(wave);output=Path(plan['output'])
    if output.exists():raise ValueError('Fresh output required; no retry')
    if source_identity(plan['jobs'][0]['assets'])!=plan['source_identity']:raise ValueError('Source/assets changed')
    bindings=validate_bindings(neural.read_prepared_plan(plan['jobs'][0]['bindings_path'],plan['jobs'][0]['bindings_sha256']))
    existing=output.parent
    while not existing.exists():existing=existing.parent
    if shutil.disk_usage(existing).free<p['aggregate_max_bytes']+2*GiB+64*MiB:raise ValueError('Insufficient bounded retention/floor/headroom')
    storage=budget(output,wave);summaries=[];parents={};retained=[]
    result={'version':1,'status':'diagnostic_unverified','claim':p['claim'],'wave':wave,'runs':summaries,
        'comparisons':[],'r2_complete':False,'full_matrix_executed':False,'held_out_executed':False}
    env={**os.environ,'PYTHONPATH':str(REPO/'src'),'MUJOCO_GL':'egl','MPLBACKEND':'Agg','OMP_NUM_THREADS':'2'}
    with storage.lock():
        (output/'runs').mkdir();neural.write(output/'diagnostic-plan.json',plan,storage)
        current_job=current_summary=None
        try:
            for prepared in plan['jobs']:
                current_job=prepared;current_summary=None
                if time.monotonic()-started>p['outer_timeout_seconds']-160:raise TimeoutError('No wall allowance for another owner')
                source=prepared['source'];cell=prepared['cell'];stage=prepared['stage'];rows=parents.setdefault(cell,{})
                native=read_snapshot(source['snapshot_path'])
                ancestor=source if wave=='A' or stage=='prepare' else rows['prepare'][0]
                expected=admitted_native(native) if wave=='A' or stage=='prepare' else rows['prepare'][1]
                job={**prepared,'snapshot_path':ancestor['snapshot_path'],'snapshot_sha256':ancestor['snapshot_sha256'],
                    'expected_non_u':invariant_hashes(expected)}
                validate_job(job);neural.write(output/(job['run_id']+'-job.json'),job,storage)
                print(json.dumps({'cell':cell,'stage':stage,'run_id':job['run_id']}),flush=True)
                supervised=bounded_process([sys.executable,str(Path(__file__).resolve()),'--worker',json.dumps(job)],
                    Path(job['output']),160,env,log_max_bytes=MiB,storage_budget=storage)
                summary={'cell':cell,'stage':stage,'run_id':job['run_id'],'supervisor':supervised};summaries.append(summary);current_summary=summary
                checked=validate_stage(job,supervised);rows[stage]=checked;retained.append((job,checked))
                report,native,_,_=checked
                summary.update(status=report['status'],policy_calls=report['policy_calls'],readout=report['readout'],
                    snapshot_sha256=report['snapshot_sha256'],worker_sha256=common._hash(Path(job['output'])/'diagnostic-worker.json'))
                if stage=='no-U':result['comparisons'].append({'cell':cell,'treatments':compare_treatments(rows)})
            result['status']='diagnostic_checked'
        except (OSError,ValueError,TypeError,KeyError,RuntimeError,TimeoutError) as error:
            failure={'type':type(error).__name__,'message':str(error),'cell':None if current_job is None else current_job['cell'],
                'stage':None if current_job is None else current_job['stage'],'scope':'before-owner' if current_summary is None else 'attempted-owner'}
            result['first_failure']=failure
            if current_summary is not None:current_summary.update(status='failed',failure=failure)
        result['unattempted']=[{'cell':j['cell'],'stage':j['stage'],'run_id':j['run_id']} for j in plan['jobs'][len(summaries):]]
        try:
            result['final_source_identity']=source_identity(plan['jobs'][0]['assets'])
            validate_bindings(neural.read_prepared_plan(plan['jobs'][0]['bindings_path'],plan['jobs'][0]['bindings_sha256']))
            for job,checked in retained:
                current=validate_stage(job,{'status':'completed','returncode':0})
                if state_digest(current)!=state_digest(checked):raise ValueError('Retained derivative changed after owner')
            if result['final_source_identity']!=plan['source_identity']:raise ValueError('Final source/assets changed')
            result['source_unchanged']=True
        except (OSError,ValueError,TypeError,KeyError) as error:
            result.update(status='diagnostic_unverified',final_error={'type':type(error).__name__,'message':str(error)})
        result.update(policy_calls=sum(s.get('policy_calls',0) for s in summaries),wall_seconds=time.monotonic()-started,
            ownership_terminal='inner bounded_process completed; outer exact PID/start/group survey required')
        if result['wall_seconds']>p['outer_timeout_seconds']:result.update(status='diagnostic_unverified',deadline_exceeded=True)
        write_report(output/'diagnostic-report.json',result,storage)
    elapsed=time.monotonic()-started
    if elapsed>p['outer_timeout_seconds']:
        result.update(status='diagnostic_unverified',wall_seconds=elapsed,deadline_exceeded=True)
        write_report(output/'diagnostic-report.json',result,storage)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-bindings',type=Path);parser.add_argument('--worker')
    parser.add_argument('--plan-only',action='store_true');parser.add_argument('--wave',choices=('A','B'))
    for name in ('assets','output','bindings','prepared-plan'):parser.add_argument('--'+name,type=Path)
    parser.add_argument('--bindings-sha256');parser.add_argument('--prepared-plan-sha256')
    args=parser.parse_args()
    if args.prepare_bindings:prepare_bindings(args.prepare_bindings);return 0
    if args.worker:
        started=time.monotonic();job=artifacts._json(args.worker);code=worker(job)
        elapsed=time.monotonic()-started
        if elapsed>150:
            path=Path(job['output'])/'diagnostic-worker.json'
            report=artifacts._json(artifacts._read(path,MiB));report.update(status='failed',return_wall_seconds=elapsed,deadline_exceeded=True)
            write_report(path,report,budget(job['root_output'],job['wave']));return 1
        return code
    started=time.monotonic()
    if args.prepared_plan:
        plan=validate_plan(neural.read_prepared_plan(args.prepared_plan,args.prepared_plan_sha256))
    else:plan=make_plan(args.assets,args.output,args.bindings,args.bindings_sha256,args.wave)
    if args.plan_only:print(json.dumps(plan,indent=2,allow_nan=False));return 0
    report=run_verifier(plan,started=started)
    print(json.dumps({'status':report['status'],'policy_calls':report['policy_calls'],'phase':'provisional-return-boundary'}),flush=True)
    elapsed=time.monotonic()-started
    if elapsed>protocol(plan['protocol']['wave'])['outer_timeout_seconds']:
        report.update(status='diagnostic_unverified',return_wall_seconds=elapsed,deadline_exceeded=True)
        write_report(Path(plan['output'])/'diagnostic-report.json',report,budget(plan['output'],plan['protocol']['wave']));return 1
    return 0 if report['status']=='diagnostic_checked' else 1

if __name__=='__main__':raise SystemExit(main())
