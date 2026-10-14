"""One bounded original-byte facade qualification; no collection/native grant."""
import argparse
from contextlib import ExitStack
import copy
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
import time

ROOT=Path(__file__).absolute().parents[1]
MiB=1024**2
SCHEMA='puck-original-bundle-qualification-v1'
PYTHON='/home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python'
RUNTIME_ROOT='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin'
RUNTIME_PIN={'path':'python3.11','size_bytes':21662864,
    'sha256':'572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a'}
BUNDLE_ROOT='/home/utkarsh/Work/shraddha/brain/.worktrees/puck-training-v2/runs/puck-training-v2-20261003'
REPORT='docs/reports/m6-puck-training-v2.json'
REPORT_SHA='c0d941eedf3aa3e7a20bc3788348b877ce70e8deed225c31e0a7e3cf404dc48c'
INDEX='docs/plans/m6-puck-student-models-v1.json'
PLAN='docs/plans/puck-original-bundle-qualification-v1.md'
HISTORY='docs/prerequisites/puck-original-producer-v1'
ENVIRONMENT={'CUDA_VISIBLE_DEVICES':'','MKL_NUM_THREADS':'1','MUJOCO_GL':'egl',
    'NUMEXPR_NUM_THREADS':'1','OMP_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1',
    'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':'src:.'}
LIMITS={'internal_seconds':40,'normal_seconds':45,'hard_seconds':50,
    'sampled_rss_bytes':1024**3,'min_free_bytes':1024**3,'output_bytes':16*MiB,
    'log_bytes':MiB,'control_bytes':MiB,'workload_processes':1,'sampling_seconds':.05}
CLAIMS={'qualification_claims':[],'collection_admission':False,'native_execution':False,
        'held_out_opened':False}
_FIELDS={'schema','attempt','attempts','repo_root','python_executable','environment',
    'output','seeds','model_calls','native_owners','physics_steps','limits','claims','inputs'}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()+b'\n'


def equal(value,expected,label):
    if canonical(value)!=canonical(expected):raise ValueError(label+' differs')


def clock(deadline):
    if time.monotonic()>=deadline:raise TimeoutError('Original bundle qualification deadline exhausted')


def source_paths():
    paths={INDEX,REPORT,PLAN,'pyproject.toml','uv.lock'}
    deadline=time.monotonic()+5;visited=0
    for directory in ('src/palimpsest','scripts'):
        for path in (ROOT/directory).rglob('*'):
            clock(deadline);visited+=1
            if visited>4096 or len(path.relative_to(ROOT/directory).parts)>32:
                raise ValueError('Qualification source discovery count/depth exceeded')
            if path.is_symlink() or path.name=='__pycache__' or path.suffix=='.pyc':
                raise ValueError('Qualification source inventory has a link or bytecode')
            if path.is_file() and path.suffix=='.py':paths.add(path.relative_to(ROOT).as_posix())
    if len(paths)>512:raise ValueError('Qualification source inventory exceeds bound')
    return sorted(paths)


def _public_bundle_descriptors():
    from palimpsest import artifacts,puck_bundle_provenance as p
    from palimpsest.puck_execution_files import HeldCollectionFiles
    rows=[]
    for name,digest,cap in ((INDEX,p.MODEL_INDEX_SHA256,64*1024),(REPORT,REPORT_SHA,MiB)):
        size=(ROOT/name).lstat().st_size
        if not 0<size<=cap:raise ValueError('Public original metadata size differs')
        rows.append({'path':name,'size_bytes':size,'sha256':digest})
    with HeldCollectionFiles(ROOT,sorted(rows,key=lambda row:row['path']),time.monotonic()+5) as held:
        raw=held.read(REPORT,MiB);index_raw=held.read(INDEX,64*1024)
    report=artifacts._json(raw)
    index=artifacts._json(index_raw)
    rows=[]
    for recorded,entry in zip(report['models'],index['models'],strict=True):
        equal(recorded['seed'],entry['seed'],'Public model seed')
        for name,value in sorted(recorded['files'].items()):
            equal(value['sha256'],entry['files'][name],'Public original artifact pin')
            rows.append({'path':entry['directory']+'/'+name,'size_bytes':value['bytes'],
                         'sha256':value['sha256']})
    return sorted(rows,key=lambda row:row['path'])


def read_freeze(path,expected_sha256):
    from palimpsest import artifacts,puck_bundle_provenance as p
    from palimpsest.puck_execution_files import HeldCollectionFiles
    from palimpsest.puck_on_policy import _digest
    _digest(expected_sha256,'Expected original qualification freeze')
    path=Path(path).absolute();size=path.lstat().st_size
    if not 0<size<=MiB:raise ValueError('Qualification freeze size differs')
    with HeldCollectionFiles(path.parent,[{'path':path.name,'size_bytes':size,
            'sha256':expected_sha256}],time.monotonic()+10) as held:
        raw=held.read(path.name,MiB)
    value=artifacts._json(raw)
    if canonical(value)!=raw or type(value) is not dict or set(value)!=_FIELDS:
        raise ValueError('Exact canonical qualification freeze required')
    fixed={'schema':SCHEMA,'attempt':1,'attempts':1,'repo_root':str(ROOT),
        'python_executable':PYTHON,'environment':ENVIRONMENT,
        'output':str(ROOT/'runs/puck-original-bundle-qualification-v1-attempt-01'),
        'seeds':[21,22,23],'model_calls':3,'native_owners':0,'physics_steps':0,
        'limits':LIMITS,'claims':CLAIMS}
    for name,wanted in fixed.items():equal(value[name],wanted,name)
    roles=value['inputs']
    if type(roles) is not dict or set(roles)!={'sources','historical','bundles','runtime'}:
        raise ValueError('Exact qualification input roles required')
    for name,role in roles.items():
        if type(role) is not dict or set(role)!={'root','files'}:
            raise ValueError('Exact qualification input fields required')
        HeldCollectionFiles(role['root'],role['files'],time.monotonic()+10)
    equal(roles['sources']['root'],str(ROOT),'Source root')
    equal([row['path'] for row in roles['sources']['files']],source_paths(),'Source roster')
    equal(roles['bundles'],{'root':BUNDLE_ROOT,'files':_public_bundle_descriptors()},'Original bundles')
    equal(roles['runtime'],{'root':RUNTIME_ROOT,'files':[RUNTIME_PIN]},'Original runtime')
    equal(roles['historical']['root'],str(ROOT/HISTORY),'Historical source root')
    historical=roles['historical']['files']
    equal({row['path']:row['sha256'] for row in historical},p.HISTORICAL_SOURCES,'Historical source pins')
    for role in ('sources','historical'):
        if any(row['size_bytes']>MiB for row in roles[role]['files']):
            raise ValueError('Qualification source byte cap exceeded')
    if sum(row['size_bytes'] for role in roles.values() for row in role['files'])>64*MiB:
        raise ValueError('Qualification input aggregate exceeded')
    return value


def parameters(model,arrays):
    import torch
    if set(model.state_dict())!=set(arrays):raise ValueError('Loaded model parameter names differ')
    for name,value in model.state_dict().items():
        if (value.device.type!='cpu' or value.dtype!=torch.float32 or
                tuple(value.shape)!=arrays[name].shape or
                value.detach().numpy().tobytes()!=arrays[name].tobytes()):
            raise ValueError('Loaded model parameter bytes differ')


def qualify_model(seed,index_raw,bundle,historical,deadline,*,admitter=None):
    """Private test seam; CLI always uses the fixed production facade."""
    clock(deadline)
    from palimpsest import puck_bundle_provenance as p,puck_model
    admitter=p.admit_original_bundle_bytes if admitter is None else admitter
    arrays,identity=admitter(seed=seed,original_model_index_raw=index_raw,
        bundle_payloads=bundle,historical_source_payloads=historical)
    equal(identity['training_seed'],seed,'Admitted original seed')
    negatives=[]
    def rejected(kind,wanted,**changed):
        clock(deadline)
        arguments={'seed':seed,'original_model_index_raw':index_raw,
            'bundle_payloads':bundle,'historical_source_payloads':historical,**changed}
        try:admitter(**arguments)
        except ValueError as error:
            if str(error)!=wanted:raise
            negatives.append({'kind':kind,'rejected':True,'reason':str(error)})
        else:raise ValueError('Qualification negative did not discriminate: '+kind)
    for filename in ('report.json','protocol.json','checkpoint.npz'):
        changed={**bundle,filename:bundle[filename]+b'!'}
        rejected(filename,'Original model artifact pin differs: '+filename,bundle_payloads=changed)
    rejected('wrong-seed','Original model artifact pin differs: report.json',seed=21+(seed-20)%3)
    source='src/palimpsest/puck_model.py'
    rejected('historical-source','Historical source bytes differ: '+source,
             historical_source_payloads={**historical,source:historical[source]+b'!'})
    clock(deadline)
    import numpy as np
    import torch
    if platform.python_version()!='3.11.15':raise ValueError('Qualification Python version differs')
    model=puck_model.make_model(seed)
    model.load_state_dict({name:torch.from_numpy(value.copy()) for name,value in arrays.items()},strict=True)
    model.eval();parameters(model,arrays)
    parameter=model[0].bias
    before=parameter.detach().clone()
    try:
        with torch.no_grad():parameter[0]+=1
        try:parameters(model,arrays)
        except ValueError as error:
            if str(error)!='Loaded model parameter bytes differ':raise
            negatives.append({'kind':'live-parameter','rejected':True,'reason':str(error)})
        else:raise ValueError('Qualification parameter negative did not discriminate')
    finally:
        with torch.no_grad():parameter.copy_(before)
    parameters(model,arrays);clock(deadline)
    inputs=np.zeros(9,np.float32)
    action=puck_model.predict(model,inputs)
    if action.dtype!=np.float64 or action.shape!=(2,) or not np.isfinite(action).all() or np.any(np.abs(action)>.4):
        raise ValueError('Qualification original model probe differs')
    parameters(model,arrays);clock(deadline)
    if torch.cuda.is_initialized() or 'mujoco' in sys.modules or 'palimpsest.engine' in sys.modules:
        raise ValueError('Qualification loaded a forbidden runtime')
    return {'seed':seed,'model_calls':1,'identity':identity,'negatives':negatives,
        'parameter_hashes':{name:hashlib.sha256(value.tobytes()).hexdigest() for name,value in arrays.items()},
        'input_sha256':hashlib.sha256(inputs.tobytes()).hexdigest(),'action':action.tolist(),
        'action_dtype':'float64','action_sha256':hashlib.sha256(action.tobytes()).hexdigest(),
        'parameters_restored':True,'runtime':{'python':platform.python_version(),
            'numpy':np.__version__,'torch':torch.__version__.split('+')[0],
            'threads':torch.get_num_threads(),'device':str(next(model.parameters()).device),
            'deterministic_algorithms':torch.are_deterministic_algorithms_enabled(),
            'cuda_initialized':torch.cuda.is_initialized()}}


def _bind_running_image(runtime,*,image_stat=None):
    """Bind the executing image to custody; authored observations are test-only."""
    from palimpsest.puck_execution_files import _identity
    runtime._guard('python3.11')
    held=os.fstat(runtime._files['python3.11'][0])
    actual=os.stat('/proc/self/exe') if image_stat is None else image_stat
    if _identity(actual)!=_identity(held):
        raise ValueError('Qualification running image differs from held original runtime')
    runtime.recheck()


def held_inputs(freeze,deadline,stack):
    from palimpsest.puck_execution_files import HeldCollectionFiles
    from palimpsest.puck_execution import _unique_held_objects
    equal([row['path'] for row in freeze['inputs']['sources']['files']],source_paths(),'Current source roster')
    held={}
    for name in ('runtime','sources','historical','bundles'):
        role=freeze['inputs'][name]
        held[name]=stack.enter_context(HeldCollectionFiles(role['root'],role['files'],deadline))
        if name=='runtime':_bind_running_image(held[name])
    _unique_held_objects(held)
    return held


def worker(freeze,args,job):
    from palimpsest import bounded_qualification as guard,puck_bundle_provenance as p
    output=Path(freeze['output']);deadline=job['deadline']
    if (job['freeze_sha256']!=args.freeze_sha256 or type(job['supervisor_pid']) is not int
            or os.getppid()!=job['supervisor_pid'] or os.getpgrp()!=os.getpid()):
        raise ValueError('Qualification worker invocation origin differs')
    guard.write_new(output/'worker-started.json',{'pid':os.getpid(),'group':os.getpgrp()})
    with ExitStack() as stack:
        held=held_inputs(freeze,deadline,stack)
        index=held['sources'].read(INDEX,64*1024)
        historical={path:held['historical'].read(path,MiB) for path in p.HISTORICAL_SOURCES}
        positives=[]
        for seed in freeze['seeds']:
            bundle={name:held['bundles'].read(f'seed-{seed}/'+name,MiB if name.endswith('.npz') else 4*MiB)
                    for name in ('report.json','protocol.json','checkpoint.npz')}
            positives.append(qualify_model(seed,index,bundle,historical,deadline))
        for value in held.values():value.recheck()
    clock(deadline)
    guard.write_new(output/'worker-result.json',{'status':'passed','freeze_sha256':args.freeze_sha256,
        'positives':positives,'model_calls':3,'negative_checks':18,'claims':CLAIMS})
    clock(deadline)


def check_invocation(freeze):
    if sys.executable!=freeze['python_executable']:raise ValueError('Qualification interpreter differs')
    for name,value in ENVIRONMENT.items():
        if os.environ.get(name)!=value:raise ValueError('Qualification environment differs: '+name)


def _publish_terminal(held,output,freeze_sha256,started,deadline):
    from palimpsest import bounded_qualification as guard
    clock(deadline)
    guard.write_new(output/'terminal.json',{'status':'passed','freeze_sha256':freeze_sha256,
        'elapsed_seconds':time.monotonic()-started,'scope':'original-bundle-facade-and-model-only','claims':CLAIMS})
    for value in held.values():value.recheck()
    clock(deadline)


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--freeze',required=True);parser.add_argument('--freeze-sha256',required=True)
    parser.add_argument('--worker',action='store_true');args=parser.parse_args(argv)
    from palimpsest import bounded_qualification as guard
    if args.worker:
        freeze=read_freeze(args.freeze,args.freeze_sha256);check_invocation(freeze)
        output=Path(freeze['output'])
        job=guard.read_control(output/'attempt.json')
        try:return worker(freeze,args,job)
        except BaseException as error:
            guard.write_new(output/'worker-failure.json',{'status':'failed','error_type':type(error).__name__,
                'message':str(error),'claims':CLAIMS})
            raise
    if os.getpgrp()!=os.getpid():os.setsid()
    started=time.monotonic();deadline=started+40;state={'group':None}
    with guard.hard_guard(started+50,state):
        freeze=read_freeze(args.freeze,args.freeze_sha256);check_invocation(freeze)
        output=Path(freeze['output']);clock(deadline)
        guard.reserve_output(output,freeze['inputs'])
        guard.write_new(output/'attempt.json',{'attempt':1,'freeze_sha256':args.freeze_sha256,
            'started_monotonic':started,'deadline':deadline,'supervisor_pid':os.getpid()})
        try:
            with ExitStack() as stack:
                held=held_inputs(freeze,deadline,stack)
                command=[sys.executable,'-m','scripts.qualify_puck_original_bundles_v1',
                    '--freeze',str(Path(args.freeze).absolute()),'--freeze-sha256',args.freeze_sha256,'--worker']
                supervision=guard.supervised(command,output/'outer',cwd=ROOT,
                    normal_deadline=started+45,hard_deadline=started+50,rss_bytes=1024**3,
                    output_bytes=16*MiB,min_free_bytes=1024**3,max_processes=1,
                    output_root=output,guard_state=state)
                guard.write_new(output/'supervisor.json',supervision)
                if supervision['status']!='completed' or supervision['returncode']!=0 or supervision['matching_survivors']:
                    raise ValueError('Qualification worker failed; no retry')
                result=guard.read_control(output/'worker-result.json')
                equal({key:result[key] for key in ('status','freeze_sha256','model_calls','negative_checks','claims')},
                    {'status':'passed','freeze_sha256':args.freeze_sha256,'model_calls':3,'negative_checks':18,'claims':CLAIMS},'Worker result')
                equal([row['seed'] for row in result['positives']],[21,22,23],'Positive model order')
                if any(len(row['negatives'])!=6 or any(x['rejected'] is not True for x in row['negatives'])
                       for row in result['positives']):raise ValueError('Qualification negatives incomplete')
                for value in held.values():value.recheck()
                _publish_terminal(held,output,args.freeze_sha256,started,deadline)
            clock(deadline)
        except BaseException as error:
            guard.write_new(output/'failure.json',{'status':'failed','error_type':type(error).__name__,
                'message':str(error),'claims':CLAIMS})
            raise


if __name__=='__main__':main()
