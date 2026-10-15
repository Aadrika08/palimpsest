"""Two separately frozen allocations: dependency preparation, then held imports.

Parent source execution is trusted after frozen hash checks. Only the child uses
held source/dependency custody. Neither result grants collection/scientific use.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import stat
import sys
import time
import types

ROOT=Path(__file__).resolve().parents[1]
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
INTERPRETER={'path':PYTHON,'size_bytes':21662864,
    'sha256':'572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a'}
BOOTSTRAP='scripts/puck_worker_bootstrap.py'
OBSERVATION='docs/reports/puck-v3-runtime-amendment-02/observation-02/payload/imports.json'
CANDIDATE='docs/plans/puck-v3-observed-import-profile-candidate.json'
WORKER_SOURCES=tuple(sorted((BOOTSTRAP,'src/palimpsest/__init__.py',
    'src/palimpsest/puck_execution_files.py','src/palimpsest/puck_dependency_files.py',
    'src/palimpsest/puck_dependency_bindings.py','src/palimpsest/puck_dependency_imports.py',
    'src/palimpsest/puck_native_origins.py','src/palimpsest/puck_worker_preflight.py',
    'src/palimpsest/puck_runtime_qualification.py')))
SOURCES=tuple(sorted((*WORKER_SOURCES,'src/palimpsest/puck_runtime_registration.py',
    'src/palimpsest/bounded_qualification.py','src/palimpsest/evaluate.py',
    'scripts/qualify_puck_held_runtime.py')))
ENVIRONMENT={'PYTHONDONTWRITEBYTECODE':'1','LC_ALL':'C.UTF-8','LANG':'C.UTF-8',
    'CUDA_VISIBLE_DEVICES':'','MUJOCO_GL':'egl','MPLBACKEND':'Agg','OMP_NUM_THREADS':'1',
    'MKL_NUM_THREADS':'1','OPENBLAS_NUM_THREADS':'1','OPENBLAS_MAIN_FREE':'1',
    'GOTOBLAS_MAIN_FREE':'1','TORCH_DEVICE_BACKEND_AUTOLOAD':'0','PYOPENGL_PLATFORM':'egl'}
PREPARATION_LIMITS={'normal_seconds':180,'hard_seconds':190,'rss_bytes':2147483648,
    'artifact_bytes':100663296,'min_free_bytes':1073741824,'fd_floor':40000}
QUALIFICATION_LIMITS={'normal_seconds':180,'hard_seconds':200,'child_hard_seconds':190,
    'rss_bytes':2147483648,'output_bytes':67108864,'artifact_bytes':100663296,
    'min_free_bytes':1073741824,'max_processes':1,'fd_floor':40000}
MiB=1024**2
PREPARATION='runs/puck-held-runtime-preparation-01'
QUALIFICATION='runs/puck-held-runtime-qualification-01'


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def sha(raw):return hashlib.sha256(raw).hexdigest()


def path(value):
    if (type(value) is not str or not value.startswith('/') or str(Path(value))!=value
            or '\\' in value or ':' in value or len(value.encode())>4096
            or any(v in ('','..','.') for v in value.split('/')[1:])):
        raise ValueError('Canonical absolute allocation path required')
    return Path(value)


def identity(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)


def read(filename,maximum,expected=None):
    filename=path(str(filename));fds=[]
    try:
        fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
        for name in filename.parts[1:-1]:
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
        leaf=os.open(filename.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);fds.append(leaf)
        before=os.fstat(leaf)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=maximum:
            raise ValueError('Allocation input is not bounded single-link regular data')
        with os.fdopen(os.dup(leaf),'rb') as handle:raw=handle.read(maximum+1)
        if (len(raw)!=before.st_size or identity(os.fstat(leaf))!=identity(before)
                or identity(os.stat(filename.name,dir_fd=fd,follow_symlinks=False))!=identity(before)):
            raise RuntimeError('Allocation input changed during read')
        if expected is not None and sha(raw)!=expected:raise ValueError('Allocation input SHA differs')
        return raw
    finally:
        for fd in reversed(fds):os.close(fd)


def decode(raw):
    def pairs(rows):
        result={}
        for key,value in rows:
            if key in result:raise ValueError('Duplicate allocation JSON key')
            result[key]=value
        return result
    def bad(_):raise ValueError('Nonfinite allocation JSON')
    result=json.loads(raw.decode('utf-8'),object_pairs_hook=pairs,parse_constant=bad)
    stack=[(result,0)];count=0
    while stack:
        value,depth=stack.pop();count+=1
        if count>524288 or depth>32:raise ValueError('Allocation JSON tree ceiling exceeded')
        if type(value) is dict:stack.extend((v,depth+1) for v in value.values())
        elif type(value) is list:stack.extend((v,depth+1) for v in value)
    return result


def write(filename,raw,maximum=MiB):
    if type(raw) is not bytes or not 0<len(raw)<=maximum:raise ValueError('Allocation publication byte ceiling exceeded')
    fd=os.open(filename,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        remaining=memoryview(raw)
        while remaining:
            n=os.write(fd,remaining)
            if n<1:raise OSError('Allocation publication made no progress')
            remaining=remaining[n:]
        os.fsync(fd)
        before=identity(os.fstat(fd))
        if identity(os.stat(filename,follow_symlinks=False))!=before or before[-1]!=1:
            raise RuntimeError('Allocation publication edge changed')
        parent=os.open(filename.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:os.fsync(parent)
        finally:os.close(parent)
    finally:os.close(fd)


def descriptor(name,raw):return {'path':name,'size_bytes':len(raw),'sha256':sha(raw)}


def reference(row,relative,maximum):
    if (type(row) is not dict or set(row)!={'path','size_bytes','sha256'} or row['path']!=relative
            or type(row['size_bytes']) is not int or not 0<row['size_bytes']<=maximum
            or type(row['sha256']) is not str or re.fullmatch('[0-9a-f]{64}',row['sha256']) is None):
        raise ValueError('Exact allocation input reference required')
    raw=read(ROOT/relative,maximum,row['sha256'])
    if len(raw)!=row['size_bytes']:raise ValueError('Allocation input reference size differs')
    return raw


def validate_freeze(raw):
    f=decode(raw)
    common={'kind','version','allocation_id','root','sources','interpreter','environment','expected_versions','limits'}
    prepare=type(f) is dict and f.get('kind')=='puck-held-runtime-preparation-v1'
    expected=common|({'site_root','observation','candidate'} if prepare else {'preparation'})
    limits=PREPARATION_LIMITS if prepare else QUALIFICATION_LIMITS
    if (type(f) is not dict or set(f)!=expected or canonical(f)!=raw
            or f['kind']!=('puck-held-runtime-preparation-v1' if prepare else 'puck-held-runtime-qualification-v1')
            or type(f['version']) is not int or f['version']!=1
            or type(f['allocation_id']) is not int or f['allocation_id']!=1
            or f['root']!=str(ROOT) or canonical(f['limits'])!=canonical(limits)
            or f['interpreter']!=INTERPRETER or canonical(f['environment'])!=canonical(ENVIRONMENT)
            or type(f['expected_versions']) is not dict or set(f['expected_versions'])!={'numpy','torch','mujoco'}
            or any(type(v) is not str or not 1<=len(v)<=128 for v in f['expected_versions'].values())):
        raise ValueError('Exact held-runtime allocation freeze required')
    if (type(f['sources']) is not list or len(f['sources'])!=len(SOURCES)
            or {v.get('path') for v in f['sources'] if type(v) is dict}!=set(SOURCES)):
        raise ValueError('Exact allocation source closure required')
    if prepare:path(f['site_root'])
    return f,prepare


def checked_sources(f):
    result={v['path']:reference(v,v['path'],MiB) for v in f['sources']}
    if sum(map(len,result.values()))>16*MiB:raise ValueError('Allocation source closure byte ceiling exceeded')
    for directory in {str((ROOT/name).parent) for name in SOURCES}:
        if (Path(directory)/'__pycache__').exists():raise ValueError('Parent source bytecode alternative refused')
    if sys.executable!=PYTHON or sha(read(PYTHON,32*MiB))!=INTERPRETER['sha256']:
        raise ValueError('Original parent interpreter differs')
    return result


def artifacts(output,maximum):
    count=total=directories=0
    for directory,dirs,files in os.walk(output,followlinks=False):
        directories+=len(dirs)
        if directories>32:raise ValueError('Allocation artifact directory ceiling exceeded')
        if any((Path(directory)/v).is_symlink() for v in dirs):raise ValueError('Allocation artifact directory link refused')
        for name in files:
            count+=1;s=(Path(directory)/name).lstat()
            if count>64 or not stat.S_ISREG(s.st_mode) or s.st_nlink!=1:
                raise ValueError('Allocation artifact file namespace differs')
            total+=s.st_size
            if total>maximum:raise ValueError('Allocation artifact byte ceiling exceeded')
    return total


def capsule(output,sources):
    root=output/'source'
    for directory in ('src/palimpsest','scripts','upstream/fly-gym'):(root/directory).mkdir(mode=0o700,parents=True,exist_ok=True)
    for name in WORKER_SOURCES:write(root/name,sources[name])
    return root,[descriptor(name,sources[name]) for name in WORKER_SOURCES]


def execute(f,prepare,sources,freeze_raw,bounds):
    output=ROOT/(PREPARATION if prepare else QUALIFICATION)
    inputs={'sources':{'root':str(ROOT),'files':f['sources']}}
    if prepare:inputs['packages']={'root':f['site_root']}
    else:inputs['preparation']={'root':str(ROOT/PREPARATION)}
    bounds.reserve_output(output,inputs)  # Exclusive marker, no retry/overwrite.
    (output/'outer/logs').mkdir(mode=0o700)
    started=time.monotonic();state={};phase='admission';supervision=None
    base={'kind':'puck-held-runtime-allocation-outcome-v1','version':1,'allocation_id':1,
          'freeze_sha256':sha(freeze_raw),'runtime_qualified':False,'native_authorized':False,
          'collection_authorized':False,'executable':False,'qualification_claims':[]}
    try:
        with bounds.hard_guard(started+f['limits']['hard_seconds'],state):
            write(output/'freeze.json',freeze_raw)
            if resource.getrlimit(resource.RLIMIT_NOFILE)[0]<f['limits']['fd_floor']:
                raise ValueError('Held-runtime FD limit below frozen floor')
            if shutil.disk_usage(output).free<f['limits']['min_free_bytes']:
                raise ValueError('Held-runtime free-space floor failed')
            if prepare:
                phase='registration'
                observed_raw=reference(f['observation'],OBSERVATION,MiB);observed=decode(observed_raw)
                candidate=decode(reference(f['candidate'],CANDIDATE,MiB))
                if (observed.get('kind')!='puck-runtime-import-characterization-result-v2'
                        or observed.get('version')!=2 or observed.get('status')!='observed'
                        or observed.get('environment_sha256')!=sha(canonical(ENVIRONMENT))
                        or any(observed.get(k) is not False for k in ('runtime_qualified','collection_authorized','executable'))
                        or observed.get('qualification_claims')!=[]
                        or candidate.get('kind')!='puck-observed-import-profile-candidate-v1'
                        or candidate.get('version')!=1 or candidate.get('observation_report_sha256')!=sha(observed_raw)
                        or any(candidate.get(k) is not False for k in ('native_phase_qualified','held_runtime_qualified','collection_authorized','executable'))
                        or candidate.get('qualification_claims')!=[]):
                    raise ValueError('Retained observation/candidate authority or identity differs')
                from palimpsest.puck_runtime_registration import build_registration
                reg=build_registration(f['site_root'],observed,candidate['import_profile'],deadline=started+180)
                dep_raw=json.dumps(reg,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
                write(output/'dependencies.json',dep_raw,16*MiB)
                source_root,files=capsule(output,sources)
                receipt=dict(base,kind='puck-held-runtime-preparation-receipt-v1',status='prepared',
                    source_root=str(source_root),source_files=files,sources=f['sources'],
                    dependencies=descriptor('dependencies.json',dep_raw),site_root=f['site_root'],
                    interpreter=f['interpreter'],environment=f['environment'],expected_versions=f['expected_versions'],
                    file_count=sum(len(v['files']) for v in reg['roots']),
                    input_bytes=sum(v['size_bytes'] for r in reg['roots'] for v in r['files']))
            else:
                phase='prepared-inputs'
                prep=decode(reference(f['preparation'],PREPARATION+'/preparation.json',MiB))
                prepared=ROOT/PREPARATION
                if ((prepared/'outcome.json').exists() or prep.get('kind')!='puck-held-runtime-preparation-receipt-v1'
                        or prep.get('status')!='prepared' or prep.get('source_root')!=str(prepared/'source')
                        or any(prep.get(k)!=f[k] for k in ('sources','environment','expected_versions','interpreter'))
                        or any(prep.get(k) is not False for k in ('runtime_qualified','native_authorized','collection_authorized','executable'))
                        or prep.get('qualification_claims')!=[]):
                    raise ValueError('Frozen preparation receipt differs or failed')
                frozen_preparation=read(prepared/'freeze.json',65536,prep['freeze_sha256'])
                validate_freeze(frozen_preparation)
                dep=prep['dependencies'];dep_path=prepared/'dependencies.json'
                reference(dict(dep,path=PREPARATION+'/dependencies.json'),PREPARATION+'/dependencies.json',16*MiB)
                if (type(prep['source_files']) is not list or len(prep['source_files'])!=len(WORKER_SOURCES)
                        or {v.get('path') for v in prep['source_files'] if type(v) is dict}!=set(WORKER_SOURCES)):
                    raise ValueError('Frozen worker source closure differs')
                for row in prep['source_files']:
                    if row!=descriptor(row['path'],sources[row['path']]):raise ValueError('Prepared worker source differs from frozen source')
                    read(prepared/'source'/row['path'],MiB,row['sha256'])
                source_root=prepared/'source'
                api=types.ModuleType('_qualification_source_api');api.__file__=str(ROOT/BOOTSTRAP)
                exec(compile(sources[BOOTSTRAP],api.__file__,'exec'),api.__dict__)
                worker_path=output/'worker-registration.json'
                bootstrap_path=source_root/BOOTSTRAP;bootstrap_sha=sha(sources[BOOTSTRAP])
                command_prefix=api.command(PYTHON,str(bootstrap_path),bootstrap_sha,str(worker_path),'0'*64)[:-1]
                modules=[]
                for row in prep['source_files']:
                    if row['path']==BOOTSTRAP:continue
                    name=row['path'][len('src/'): -3].replace('/','.')
                    if name.endswith('.__init__'):name=name[:-len('.__init__')]
                    modules.append({'name':name,'path':row['path']})
                worker={'kind':'puck-worker-source-bootstrap-v3','version':3,'source_root':str(source_root),
                    'source_files':prep['source_files'],'modules':modules,'namespaces':[],
                    'runtime':{'root':str(Path(PYTHON).parent),'files':[dict(api.RUNTIME_PIN)],'python_version':'3.11.15'},
                    'environment':dict(ENVIRONMENT),'cwd':str(source_root),'argv_prefix':command_prefix,
                    'dependencies':dict(dep,path=str(dep_path)),
                    'qualification':{'kind':'puck-held-runtime-import-qualification-v1','version':1,
                        'expected_versions':f['expected_versions'],'stdlib_cache_aliases':{'__mp_main__':'__main__'},'negative_imports':['org']},
                    'qualification_claims':[],'executable':False}
                worker_raw=api.canonical(worker);write(worker_path,worker_raw)
                command=api.command(PYTHON,str(bootstrap_path),bootstrap_sha,str(worker_path),sha(worker_raw))
                write(output/'invocation.json',canonical({'command':command,'cwd':str(source_root),
                    'environment_sha256':sha(canonical(ENVIRONMENT)),'worker_registration_sha256':sha(worker_raw)}))
                phase='worker';os.environ.clear();os.environ.update(ENVIRONMENT)
                supervision=bounds.supervised(command,output/'outer/logs',cwd=source_root,
                    normal_deadline=started+180,hard_deadline=started+190,rss_bytes=f['limits']['rss_bytes'],
                    output_bytes=f['limits']['output_bytes'],min_free_bytes=f['limits']['min_free_bytes'],
                    max_processes=1,output_root=output/'outer',guard_state=state)
                write(output/'supervision.json',canonical(supervision))
                if supervision['status']!='completed':raise RuntimeError('Held-runtime worker did not complete; see retained stderr')
                worker_output=read(output/'outer/logs/stdout.log',MiB);result=decode(worker_output)
                entry=result.get('entry_result',{})
                if (entry.get('kind')!='puck-held-runtime-import-qualification-result-v1'
                        or entry.get('status')!='imports_completed' or entry.get('held_imports_observed') is not True
                        or [v.get('name') for v in entry.get('imports',[])]!=['numpy','torch','mujoco']
                        or {v['name']:v.get('version') for v in entry['imports']}!=f['expected_versions']
                        or result.get('registration_sha256')!=sha(worker_raw)
                        or any(result.get(k) is not False for k in ('runtime_qualified','dependencies_qualified','native_authorized','collection_authorized','executable'))
                        or result.get('qualification_claims')!=[]):
                    raise ValueError('Held-runtime terminal result differs from fixed request')
                receipt=dict(base,status='imports_completed',supervision=supervision,
                             worker_stdout_sha256=sha(worker_output),preparation_sha256=f['preparation']['sha256'])
            peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            if peak>f['limits']['rss_bytes']:raise RuntimeError('Preparation parent high-water RSS stop threshold')
            if time.monotonic()-started>=180:raise TimeoutError('Allocation normal deadline exhausted')
            artifacts(output,f['limits']['artifact_bytes']-MiB)
            receipt.update(seconds=time.monotonic()-started,parent_peak_rss_bytes=peak)
            write(output/('preparation.json' if prepare else 'outcome.json'),canonical(receipt))
        if time.monotonic()-started>=180:raise TimeoutError('Allocation return deadline exhausted')
        print(canonical(receipt).decode(),end='',flush=True)
        return 0
    except BaseException as error:
        failure=dict(base,status='failed',phase=phase,error={'type':type(error).__name__,'message':str(error)[:2048]},
                     seconds=time.monotonic()-started,supervision=supervision)
        # Never replace an already published terminal. A failed preparation is
        # rejected by any later qualification even if its prepared marker exists.
        if not (output/'outcome.json').exists():write(output/'outcome.json',canonical(failure))
        print(type(error).__name__+': '+str(error)[:2048],file=sys.stderr,flush=True)
        return 1


def main():
    if len(sys.argv)!=3:raise ValueError('Expected frozen input and external SHA')
    raw=read(path(sys.argv[1]),65536,sys.argv[2]);f,prepare=validate_freeze(raw)
    sources=checked_sources(f)
    sys.path.insert(0,str(ROOT/'src'))
    from palimpsest import bounded_qualification as bounds
    if os.getpgrp()!=os.getpid():os.setsid()
    return execute(f,prepare,sources,raw,bounds)


if __name__=='__main__':
    try:raise SystemExit(main())
    except Exception as error:
        print(type(error).__name__+': '+str(error)[:2048],file=sys.stderr,flush=True)
        raise SystemExit(1)
