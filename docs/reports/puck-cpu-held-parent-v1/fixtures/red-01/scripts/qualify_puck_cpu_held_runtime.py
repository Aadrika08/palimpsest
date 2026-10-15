"""Separately frozen CPU preparation and held four-import qualification.

The parent is trusted after its source freeze. A passing terminal observes held
imports only; it grants no numerical, renderer, collection or study authority.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import stat
import sys
import threading
import time
import types

ROOT=Path(__file__).resolve().parents[1]
MiB=1024**2
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
INTERPRETER=dict(path=PYTHON,size_bytes=21662864,sha256='572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a')
BOOTSTRAP='scripts/puck_worker_bootstrap.py'
SITE='runs/puck-cpu-install-01/site'
OUTPUTS=dict(prepare='runs/puck-cpu-held-preparation-01',qualify='runs/puck-cpu-held-qualification-01')
VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',torchvision='0.24.0+cpu',mujoco='3.3.6')
ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',
    HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/puck/source',PATH='/nonexistent',TZ='UTC',
    CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',
    OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0')
WORKER_SOURCES=tuple(sorted((BOOTSTRAP,'src/palimpsest/__init__.py',
    'src/palimpsest/puck_execution_files.py','src/palimpsest/puck_dependency_files.py',
    'src/palimpsest/puck_dependency_bindings.py','src/palimpsest/puck_dependency_imports.py',
    'src/palimpsest/puck_native_origins.py','src/palimpsest/puck_native_identity.py',
    'src/palimpsest/puck_worker_preflight.py','src/palimpsest/puck_runtime_qualification.py')))
SOURCES=tuple(sorted(set(WORKER_SOURCES)|{
    'scripts/qualify_puck_cpu_held_runtime.py','scripts/stage_puck_cpu_held_runtime.py',
    'scripts/qualify_puck_held_runtime.py','scripts/build_puck_python_louvain.py',
    'scripts/acquire_puck_cpu_payloads.py','src/palimpsest/bounded_qualification.py',
    'src/palimpsest/evaluate.py','src/palimpsest/puck_build_inputs.py',
    'src/palimpsest/puck_package_payloads.py','src/palimpsest/puck_retained_installation.py',
    'src/palimpsest/puck_runtime_registration.py','src/palimpsest/puck_runtime_staging.py',
    'src/palimpsest/puck_cpu_registration.py','src/palimpsest/puck_cpu_namespace.py'}))
INPUT_ROLES=tuple(sorted(('inventory','layout','candidate','native','baseline','generated',
    'accepted_result','accepted_snapshot','accepted_audit','accepted_configuration','accepted_index',
    'observation_configuration','observation_report','observation_result','observation_audit','observation_index')))
CLAIMS=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,
    study_authorized=False,executable=False,qualification_claims=[])
LIMITS={phase:dict(normal_seconds=180,child_hard_seconds=190,hard_seconds=200,
    rss_bytes=2048*MiB,address_space_bytes=8192*MiB,output_bytes=64*MiB,
    scratch_bytes=64*MiB,file_bytes=16*MiB,min_free_bytes=4096*MiB,
    min_available_ram_bytes=128*MiB,
    min_tmpfs_free_bytes=(2048 if phase=='prepare' else 256)*MiB,
    max_processes=3,max_fds=40000) for phase in ('prepare','qualify')}


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def digest(raw):return hashlib.sha256(raw).hexdigest()


def relative(value):
    if (type(value) is not str or not value or value.startswith('/') or '\\' in value
            or any(v in ('','.','..') for v in value.split('/')) or len(value)>4096):
        raise ValueError('Canonical relative CPU input path required')
    return value


def pin(row):
    if (type(row) is not dict or set(row)!={'path','size_bytes','sha256'}
            or type(row['size_bytes']) is not int or not 0<row['size_bytes']<=16*MiB
            or type(row['sha256']) is not str or re.fullmatch('[0-9a-f]{64}',row['sha256']) is None):
        raise ValueError('Exact bounded CPU input pin required')
    relative(row['path']);return row


def read(path,maximum,expected=None):
    """Initial bounded nofollow read before importing any repository helpers."""
    path=Path(path);fds=[]
    if not path.is_absolute() or str(path)!=os.fspath(path) or any(p in ('.','..') for p in path.parts):
        raise ValueError('Absolute CPU control path required')
    try:
        fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fds.append(fd)
        for name in path.parts[1:-1]:
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);fds.append(fd)
        leaf=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd);fds.append(leaf)
        before=os.fstat(leaf)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=maximum:
            raise ValueError('CPU control is not bounded single-link regular data')
        with os.fdopen(os.dup(leaf),'rb') as handle:raw=handle.read(maximum+1)
        identity=lambda v:(v.st_dev,v.st_ino,v.st_mode,v.st_size,v.st_mtime_ns,v.st_ctime_ns,v.st_nlink)
        if identity(before)!=identity(os.fstat(leaf)) or identity(before)!=identity(os.stat(path.name,dir_fd=fd,follow_symlinks=False)) or len(raw)!=before.st_size:
            raise ValueError('CPU control changed while read')
        if expected is not None and digest(raw)!=expected:raise ValueError('CPU input SHA differs')
        return raw
    finally:
        for fd in reversed(fds):os.close(fd)


def decode(raw):
    def pairs(rows):
        result={}
        for key,value in rows:
            if key in result:raise ValueError('Duplicate CPU control key')
            result[key]=value
        return result
    def bad(_):raise ValueError('Nonfinite CPU control value')
    value=json.loads(raw,object_pairs_hook=pairs,parse_constant=bad);pending=[(value,0)];count=0
    while pending:
        item,depth=pending.pop();count+=1
        if count>524288 or depth>32:raise ValueError('CPU control tree ceiling')
        if type(item) is float and not math.isfinite(item):raise ValueError('Nonfinite CPU control number')
        if type(item) is dict:pending.extend((v,depth+1) for v in item.values())
        elif type(item) is list:pending.extend((v,depth+1) for v in item)
    return value


def _negative_imports(names):
    if (type(names) is not list or not 1<=len(names)<=128 or names!=sorted(set(names))
            or any(type(n) is not str or len(n)>512 or re.fullmatch(r'[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*',n,flags=re.ASCII) is None
                   or n.split('.')[0] in ('palimpsest','__main__','__mp_main__','_puck_held_file_bootstrap') for n in names)
            or any(n.startswith(p+'.') for i,n in enumerate(names) for p in names[:i])):
        raise ValueError('Exact finite CPU missing-import roster required')


def configuration_template(*,phase,root,stage_parent,sources,inputs,negative_imports,preparation=None):
    result=dict(kind='puck-cpu-held-runtime-allocation-v1',version=1,phase=phase,allocation_id=1,
        root=root,stage_parent=stage_parent,sources=sources,inputs=inputs,interpreter=dict(INTERPRETER),
        environment=dict(ENVIRONMENT),expected_versions=dict(VERSIONS),limits=copy.deepcopy(LIMITS[phase]),
        negative_imports=negative_imports,claims=copy.deepcopy(CLAIMS))
    if phase=='qualify':result['preparation']=preparation
    return result


def validate_configuration(config):
    keys={'kind','version','phase','allocation_id','root','stage_parent','sources','inputs',
          'interpreter','environment','expected_versions','limits','negative_imports','claims'}
    phase=config.get('phase') if type(config) is dict else None
    if phase=='qualify':keys.add('preparation')
    if (phase not in LIMITS or set(config)!=keys or config['kind']!='puck-cpu-held-runtime-allocation-v1'
            or type(config['version']) is not int or config['version']!=1
            or type(config['allocation_id']) is not int or config['allocation_id']!=1
            or config['root']!=str(ROOT) or canonical(config['limits'])!=canonical(LIMITS[phase])
            or config['interpreter']!=INTERPRETER or canonical(config['environment'])!=canonical(ENVIRONMENT)
            or config['expected_versions']!=VERSIONS or canonical(config['claims'])!=canonical(CLAIMS)):
        raise ValueError('Exact CPU allocation configuration required')
    stage=config['stage_parent']
    if (type(stage) is not str or Path(stage).parent!=Path('/tmp') or str(Path(stage))!=stage
            or not re.fullmatch(r'/tmp/palimpsest-puck-cpu-held-[A-Za-z0-9_-]+',stage)):
        raise ValueError('Private CPU tmpfs allocation path required')
    sources=config['sources'];inputs=config['inputs']
    if (type(sources) is not list or [pin(r)['path'] for r in sources]!=list(SOURCES)
            or type(inputs) is not dict or set(inputs)!=set(INPUT_ROLES)):
        raise ValueError('Exact CPU source/input closure required')
    for row in inputs.values():pin(row)
    if phase=='qualify':
        pin(config['preparation'])
        if config['preparation']['path']!=OUTPUTS['prepare']+'/result.json':raise ValueError('Exact CPU preparation receipt required')
    _negative_imports(config['negative_imports'])


def worker_registration(source_files,dependency_raw,*,negative_imports):
    _negative_imports(negative_imports)
    if [pin(r)['path'] for r in source_files]!=list(WORKER_SOURCES):raise ValueError('Exact CPU worker source closure required')
    bootstrap=next(r for r in source_files if r['path']==BOOTSTRAP)
    raw=read(ROOT/BOOTSTRAP,MiB,bootstrap['sha256'])
    if len(raw)!=bootstrap['size_bytes']:raise ValueError('CPU bootstrap size differs')
    api=types.ModuleType('_frozen_cpu_bootstrap_api');api.__file__=str(ROOT/BOOTSTRAP)
    exec(compile(raw,api.__file__,'exec'),api.__dict__)
    prefix=api.command(PYTHON,'/puck/source/'+BOOTSTRAP,bootstrap['sha256'],'/puck/control/worker-registration.json','0'*64)[:-1]
    modules=[]
    for row in source_files:
        if row['path']==BOOTSTRAP:continue
        name=row['path'][4:-3].replace('/','.')
        if name.endswith('.__init__'):name=name[:-9]
        modules.append(dict(name=name,path=row['path']))
    result=dict(kind='puck-worker-source-bootstrap-v3',version=3,source_root='/puck/source',
        source_files=copy.deepcopy(source_files),modules=modules,namespaces=[],
        runtime=dict(root=str(Path(PYTHON).parent),files=[dict(api.RUNTIME_PIN)],python_version='3.11.15'),
        environment=dict(ENVIRONMENT),cwd='/puck/source',argv_prefix=prefix,
        dependencies=dict(path='/puck/control/dependencies.json',size_bytes=len(dependency_raw),sha256=digest(dependency_raw)),
        qualification=dict(kind='puck-held-runtime-import-qualification-v3',version=3,
            expected_versions=dict(VERSIONS),stdlib_cache_aliases={'__mp_main__':'__main__'},negative_imports=list(negative_imports)),
        qualification_claims=[],executable=False)
    worker_raw=api.canonical(result)
    return result,prefix+[digest(worker_raw)]


def validate_worker_result(result,*,registration_sha256,dependency_sha256,dependencies,negative_imports):
    dep=result.get('dependencies',{});entry=result.get('entry_result',{});imports=entry.get('imports',[])
    count=sum(len(r['files']) for r in dependencies['roots'])
    byte_count=sum(f['size_bytes'] for r in dependencies['roots'] for f in r['files'])
    caches=sorted(dependencies['import_profile'].get('native_cache',[]),key=lambda r:r['name'])
    if (result.get('kind')!='puck-worker-source-bootstrap-receipt-v1'
            or result.get('registration_sha256')!=registration_sha256
            or result.get('interpreter_object_bound') is not True or result.get('python_version')!='3.11.15'
            or any(result.get(k) is not False for k in ('runtime_qualified','dependencies_qualified','native_authorized','collection_authorized','executable'))
            or result.get('qualification_claims')!=[] or result.get('expected_missing_imports')!=negative_imports
            or type(result.get('denied_imports')) is not list or not set(result['denied_imports'])<=set(negative_imports)
            or dep.get('registration_sha256')!=dependency_sha256 or dep.get('native_identity')!='tmpfs-raw-dev-inode-v1'
            or type(dep.get('root_count')) is not int or dep['root_count']!=4
            or type(dep.get('file_count')) is not int or dep['file_count']!=count
            or type(dep.get('input_bytes')) is not int or dep['input_bytes']!=byte_count
            or dep.get('native_cache_modules',[])!=caches
            or entry.get('kind')!='puck-held-runtime-import-qualification-result-v2'
            or type(entry.get('version')) is not int or entry['version']!=2
            or type(entry.get('qualification_version')) is not int or entry['qualification_version']!=3
            or entry.get('status')!='imports_completed' or entry.get('held_imports_observed') is not True
            or [r.get('name') for r in imports]!=list(VERSIONS)
            or {r['name']:r.get('version') for r in imports}!=VERSIONS):
        raise ValueError('CPU held-import terminal is incomplete or differs from frozen request')


def validate_observation_links(config,blobs):
    pins=config['inputs'];frozen=decode(blobs['observation_configuration'])
    roles=('inventory','layout','native','baseline','accepted_result','accepted_snapshot',
           'accepted_audit','accepted_configuration','accepted_index')
    if (frozen.get('kind')!='puck-cpu-runtime-characterization-v1'
            or type(frozen.get('version')) is not int or frozen['version']!=1
            or type(frozen.get('roles')) is not dict or type(frozen.get('inputs')) is not list):
        raise ValueError('Authenticated CPU observation configuration differs')
    old_rows={r['path']:r for r in frozen['inputs']}
    if len(old_rows)!=len(frozen['inputs']):raise ValueError('Duplicated frozen CPU observation input')
    for role in roles:
        name='native_metadata' if role=='native' else role
        if frozen['roles'].get(name)!=pins[role]['path'] or old_rows.get(pins[role]['path'])!=pins[role]:
            raise ValueError('Current CPU metadata differs from frozen observation role: '+role)
    bindings={
        'accepted_index':('retained-admission-02-evidence-index-v1',{
            'inventory':'raw/inventory.json','accepted_result':'raw/result.json',
            'accepted_snapshot':'raw/snapshot.json','accepted_audit':'acceptance-audit-03.json',
            'accepted_configuration':'raw/configuration.json'}),
        'observation_index':('cpu-characterization-evidence-index-v2',{
            'observation_configuration':'frozen-configuration.json','observation_report':'raw/payload/imports.json',
            'observation_result':'raw/result.json','observation_audit':'outcome-audit-02.json'})}
    for role,(kind,paths) in bindings.items():
        index=decode(blobs[role]);entries=index.get('entries')
        if index.get('kind')!=kind or type(entries) is not list or not 1<=len(entries)<=512:
            raise ValueError('CPU evidence index schema differs')
        indexed={r['path']:r for r in entries}
        if len(indexed)!=len(entries):raise ValueError('Duplicated CPU evidence index row')
        for name,path in paths.items():
            expected=dict(pins[name],path=path)
            if role=='accepted_index' and name=='accepted_configuration':
                # The accepted parent retained compact JSON+LF, while its frozen
                # external configuration keeps its original pretty bytes.
                retained=canonical(decode(blobs[name]))
                expected=dict(path=path,size_bytes=len(retained),sha256=digest(retained))
            if indexed.get(path)!=expected:
                raise ValueError('CPU evidence index byte binding differs: '+name)


def verify_staged_roots(stage_parent,dependencies,expected):
    roots=dependencies.get('roots')
    names=['root-'+str(i).zfill(4) for i in range(4)]
    if (type(roots) is not list or len(roots)!=4 or type(expected) is not list or len(expected)!=4
            or [r.get('root') for r in roots]!=['/puck/staged/inputs/'+name for name in names]):
        raise ValueError('CPU prepared root ordering or private paths differ')
    parent=os.open(stage_parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);inputs=None
    try:
        inputs=os.open('inputs',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent)
        for i,name in enumerate(names):
            row=expected[i]
            if (type(row) is not dict or set(row)!={'root_index','device','inode'}
                    or any(type(v) is not int for v in row.values()) or row['root_index']!=i):
                raise ValueError('CPU prepared root identity schema differs')
            fd=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=inputs)
            try:
                state=os.fstat(fd);named=os.stat(name,dir_fd=inputs,follow_symlinks=False)
                if ((state.st_dev,state.st_ino)!=(row['device'],row['inode'])
                        or (named.st_dev,named.st_ino)!=(row['device'],row['inode'])
                        or not stat.S_ISDIR(state.st_mode) or stat.S_IMODE(state.st_mode)!=0o700):
                    raise ValueError('CPU prepared root object was replaced')
            finally:os.close(fd)
    finally:
        if inputs is not None:os.close(inputs)
        os.close(parent)


def validate_inputs(config,blobs):
    validate_observation_links(config,blobs)
    get=lambda role:decode(blobs[role]);pins=config['inputs']
    accepted,snapshot,audit,accepted_config=(get(k) for k in ('accepted_result','accepted_snapshot','accepted_audit','accepted_configuration'))
    candidate,observation,observed,audit02=(get(k) for k in ('candidate','observation_report','observation_result','observation_audit'))
    if (accepted.get('kind')!='cpu-retained-installation-admission-result-v2' or accepted.get('status')!='PASS'
            or accepted.get('claims',{}).get('package_preparation_accepted') is not True
            or any(accepted['claims'].get(k) is not False for k in ('runtime_qualified','numerical_imports_executed','study_authorized','collection_authorized'))
            or accepted.get('configuration_sha256')!=pins['accepted_configuration']['sha256']
            or accepted.get('snapshot_sha256')!=pins['accepted_snapshot']['sha256']
            or accepted.get('site_root')!=str(ROOT/SITE) or snapshot.get('site_root')!=str(ROOT/SITE)
            or audit.get('status')!='PASS' or audit.get('package_preparation_accepted') is not True
            or audit.get('verified',{}).get('configuration_sha256')!=pins['accepted_configuration']['sha256']
            or snapshot.get('configuration_sha256')!=pins['accepted_configuration']['sha256']):
        raise ValueError('Accepted CPU package data binding differs')
    inventory,layout=get('inventory'),get('layout')
    if (accepted.get('file_count')!=inventory.get('file_count') or accepted.get('directory_count')!=inventory.get('directory_count')
            or accepted.get('regular_file_bytes')!=inventory.get('total_bytes')
            or len(layout.get('predicted_destination_directories',[]))!=inventory.get('directory_count')):
        raise ValueError('Accepted CPU package size or directory binding differs')
    layout_pins=[r for r in accepted_config.get('inputs',[]) if r['path']==pins['layout']['path']]
    if layout_pins!=[pins['layout']]:raise ValueError('Accepted CPU layout pin differs')
    if (observed.get('status')!='observed' or observed.get('report_sha256')!=pins['observation_report']['sha256']
            or observed.get('configuration_sha256')!=pins['observation_configuration']['sha256']
            or observation.get('kind')!='puck-runtime-import-characterization-result-v3'
            or observation.get('versions')!=VERSIONS or observed.get('versions')!=VERSIONS
            or candidate.get('expected_versions')!=VERSIONS
            or candidate.get('observation_report_sha256')!=pins['observation_report']['sha256']
            or candidate.get('configuration_sha256')!=pins['observation_configuration']['sha256']
            or candidate.get('outcome_audit_sha256')!=pins['observation_audit']['sha256']
            or candidate.get('retained_inventory_sha256')!=pins['inventory']['sha256']
            or audit02.get('status')!='PASS' or audit02.get('ordinary_imports_observed') is not True
            or audit02.get('verified',{}).get('result_sha256')!=pins['observation_result']['sha256']
            or audit02['verified'].get('report_sha256')!=pins['observation_report']['sha256']
            or any(observed.get(k) is not False for k in CLAIMS if k!='qualification_claims')
            or observed.get('qualification_claims')!=[]):raise ValueError('Accepted ordinary CPU observation binding differs')
    additional=candidate.get('additional_package_inputs',[])
    if len(additional)!=1 or len(additional[0].get('files',[]))!=1:
        raise ValueError('Exact generated CPU helper input required')
    generated=additional[0]['files'][0]
    if pins['generated']!=dict(generated,path=additional[0]['root']+'/'+generated['path']):
        raise ValueError('Generated CPU helper pin differs')
    return inventory,layout,candidate,observation


def resource_admission(config):
    limits=config['limits'];parent=Path(config['stage_parent']).parent
    available=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    if (any(v!=resource.RLIM_INFINITY and v<limits['max_fds'] for v in (soft,hard))
            or available<limits['min_available_ram_bytes'] or shutil.disk_usage(ROOT).free<limits['min_free_bytes']
            or shutil.disk_usage(parent).free<limits['min_tmpfs_free_bytes']):
        raise ValueError('CPU held-runtime resource admission failed')
    flags=os.statvfs(parent).f_flag
    if flags & (os.ST_RDONLY|os.ST_NOEXEC):raise ValueError('CPU staging tmpfs must be writable and executable')
    from palimpsest.puck_native_identity import require_tmpfs_descriptor
    fd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:require_tmpfs_descriptor(fd)
    finally:os.close(fd)
    return dict(mem_available_bytes=available,tmpfs_available_bytes=shutil.disk_usage(parent).free,
                disk_available_bytes=shutil.disk_usage(ROOT).free)


def closure(before):
    children=Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split()
    threads=[t.name for t in threading.enumerate() if t is not threading.main_thread()]
    after=len(os.listdir('/proc/self/fd'))
    if children or threads or before!=after:raise ValueError('CPU parent process/thread/descriptor closure failed')
    return dict(active_children=[],active_non_main_threads=[],fd_count_before=before,fd_count_after=after)


def create_capsule(directory,names,source_bytes,write):
    for prefix in ('src/palimpsest','scripts','upstream/fly-gym'):
        (directory/prefix).mkdir(mode=0o700,parents=True,exist_ok=True)
    for name in names:
        target=directory/name;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        write(target,source_bytes[name])


def execute(config,raw,started):
    # All repository imports occur only after main authenticates their source bytes.
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
    import qualify_puck_held_runtime as controls
    import build_puck_python_louvain as baseline_api
    from palimpsest import bounded_qualification as bounds
    from palimpsest.puck_retained_installation import AdmissionInputs
    from palimpsest.puck_cpu_registration import build_cpu_source_registration,attach_cpu_candidate
    from palimpsest.puck_cpu_namespace import sandbox_command
    phase=config['phase'];limits=config['limits'];output=ROOT/OUTPUTS[phase];stage=Path(config['stage_parent'])
    rows=config['sources']+list(config['inputs'].values())
    unique={r['path']:r for r in rows}
    if len(unique)!=len(rows):raise ValueError('Overlapping CPU source/input pins')
    admission=resource_admission(config)
    if phase=='prepare' and os.path.lexists(stage):raise FileExistsError('CPU tmpfs allocation already exists')
    if phase=='qualify':rows=rows+[config['preparation']]
    deadline=started+limits['normal_seconds'];state={};before_fds=len(os.listdir('/proc/self/fd'))
    bounds.reserve_output(output,dict(sources=dict(root=str(ROOT),files=rows)))
    for name in ('logs','control','payload'):(output/name).mkdir(mode=0o700)
    result=dict(CLAIMS,kind='puck-cpu-held-runtime-outcome-v1',version=1,phase=phase,allocation_id=1,
                configuration_sha256=digest(raw),status='FAIL',held_four_imports_observed=False)
    bounds.write_new(output/'configuration.json',config)
    bounds.write_new(output/'resource-admission.json',admission)
    try:
        with bounds.hard_guard(started+limits['hard_seconds'],state):
            with AdmissionInputs(ROOT,sorted(rows,key=lambda r:r['path']),deadline) as inputs:
                blobs={role:read(ROOT/row['path'],16*MiB,row['sha256']) for role,row in config['inputs'].items()}
                inventory,layout,candidate,observation=validate_inputs(config,blobs)
                baseline=decode(blobs['baseline']);native=decode(blobs['native'])
                def native_checks():
                    for row in native['native_files']:
                        if baseline_api.file_row(Path(row['path']),deadline,single_link=False)!={k:row[k] for k in ('size_bytes','sha256')}:
                            raise ValueError('Original CPU native input changed')
                    for path,target in native['aliases']:
                        if os.readlink(path)!=target:raise ValueError('Original CPU native alias changed')
                native_checks()
                baseline_before=baseline_api.verify_baseline(baseline,deadline)
                bounds.write_new(output/'baseline-before.json',baseline_before)
                source_bytes={r['path']:read(ROOT/r['path'],MiB,r['sha256']) for r in config['sources']}
                generated_root=str((ROOT/config['inputs']['generated']['path']).parent)
                source_reg=build_cpu_source_registration(blobs['inventory'],blobs['layout'],blobs['candidate'],blobs['native'],
                    expected_pins={k:{x:config['inputs'][k][x] for x in ('size_bytes','sha256')} for k in ('inventory','layout','candidate','native')},
                    site_root=str(ROOT/SITE),generated_root=generated_root,deadline=deadline)
                if phase=='prepare':
                    os.mkdir(stage,0o700);os.chmod(stage,0o700)
                    driver_source=output/'parent-source';worker_source=output/'worker-source'
                    for directory,names in ((driver_source,SOURCES),(worker_source,WORKER_SOURCES)):
                        create_capsule(directory,names,source_bytes,controls.write)
                    copy_raw=json.dumps(source_reg,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode();controls.write(output/'control/copy-registration.json',copy_raw,16*MiB)
                    for role in ('candidate','layout'):controls.write(output/('control/'+role+'.json'),blobs[role],16*MiB)
                    request=dict(registration=dict(path='/puck/control/copy-registration.json',sha256=digest(copy_raw)),
                        candidate=dict(path='/puck/control/candidate.json',sha256=digest(blobs['candidate'])),
                        layout=dict(path='/puck/control/layout.json',sha256=digest(blobs['layout'])))
                    request_raw=canonical(request);controls.write(output/'control/stage-request.json',request_raw)
                    command=[PYTHON,'-I','-S','-B','/puck/source/scripts/stage_puck_cpu_held_runtime.py',digest(request_raw)]
                    sandbox_source=driver_source
                else:
                    prep=decode(read(ROOT/config['preparation']['path'],MiB,config['preparation']['sha256']))
                    if (prep.get('status')!='prepared' or prep.get('phase')!='prepare' or prep.get('stage_parent')!=str(stage)
                            or prep.get('sources')!=config['sources'] or prep.get('inputs')!=config['inputs']
                            or any(prep.get(k) is not False for k in CLAIMS if k!='qualification_claims')
                            or prep.get('qualification_claims')!=[]):raise ValueError('CPU preparation receipt differs or failed')
                    prepared=ROOT/OUTPUTS['prepare'];dep=prep['dependencies']
                    dependency_raw=read(prepared/'payload/dependencies.json',16*MiB,dep['sha256'])
                    if len(dependency_raw)!=dep['size_bytes']:raise ValueError('CPU prepared registration size differs')
                    dependencies=decode(dependency_raw)
                    attached=attach_cpu_candidate(dependencies,blobs['candidate'],expected_sha256=config['inputs']['candidate']['sha256'],deadline=deadline)
                    if (attached!=dependencies or dependencies.get('distributions')!=source_reg['distributions']
                            or any(a.get('files')!=b['files'] for a,b in zip(dependencies['roots'],source_reg['roots']))):
                        raise ValueError('CPU prepared bytes/profile differ from accepted source plan')
                    verify_staged_roots(str(stage),dependencies,prep['staged_roots'])
                    controls.write(output/'control/dependencies.json',dependency_raw,16*MiB)
                    files=[r for r in config['sources'] if r['path'] in WORKER_SOURCES]
                    for row in files:read(prepared/'worker-source'/row['path'],MiB,row['sha256'])
                    worker,command=worker_registration(files,dependency_raw,negative_imports=config['negative_imports'])
                    worker_raw=json.dumps(worker,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
                    controls.write(output/'control/worker-registration.json',worker_raw)
                    sandbox_source=prepared/'worker-source';generated_root=None
                command=sandbox_command(baseline,native,sorted(r['path'] for r in observation['baseline_maps']['images']),
                    phase=phase,stage_parent=str(stage),source_root=str(sandbox_source),control_root=str(output/'control'),
                    output_root=str(output/'payload'),command=command,environment=ENVIRONMENT,
                    site_root=str(ROOT/SITE) if phase=='prepare' else None,generated_root=generated_root,
                    scratch_bytes=limits['scratch_bytes'])
                bounds.write_new(output/'invocation.json',dict(command=command,configuration_sha256=digest(raw)))
                observed=bounds.supervised(command,output/'logs',cwd=ROOT,normal_deadline=deadline,
                    hard_deadline=started+limits['child_hard_seconds'],rss_bytes=limits['rss_bytes'],
                    output_bytes=limits['output_bytes'],min_free_bytes=limits['min_free_bytes'],
                    max_processes=limits['max_processes'],output_root=output,guard_state=state,
                    output_namespace_limits=(128,16),log_mode='direct')
                bounds.write_new(output/'supervision.json',observed)
                if observed['status']!='completed':raise ValueError('CPU '+phase+' worker failed; retained logs are authoritative')
                if phase=='prepare':
                    stage_receipt=decode(read(output/'payload/stage.json',MiB))
                    dependency_raw=read(output/'payload/dependencies.json',16*MiB,stage_receipt['dependencies']['sha256'])
                    if stage_receipt.get('status')!='prepared':raise ValueError('CPU staging terminal differs')
                    verify_staged_roots(str(stage),decode(dependency_raw),stage_receipt['staged_roots'])
                    result.update(status='prepared',stage_parent=str(stage),dependencies=stage_receipt['dependencies'],
                        staged_roots=stage_receipt['staged_roots'],sources=config['sources'],inputs=config['inputs'])
                else:
                    worker_result=decode(read(output/'logs/stdout.log',MiB))
                    validate_worker_result(worker_result,registration_sha256=digest(worker_raw),dependency_sha256=digest(dependency_raw),
                        dependencies=decode(dependency_raw),negative_imports=config['negative_imports'])
                    verify_staged_roots(str(stage),dependencies,prep['staged_roots'])
                    result.update(status='imports_completed',held_four_imports_observed=True,worker_stdout_sha256=digest(read(output/'logs/stdout.log',MiB)))
                native_checks()
                baseline_after=baseline_api.verify_baseline(baseline,deadline)
                if baseline_before!=baseline_after:raise ValueError('Original trusted CPU baseline changed')
                bounds.write_new(output/'baseline-after.json',baseline_after)
                inputs.recheck()
    except Exception as error:result.update(status='FAIL',error_type=type(error).__name__,error=str(error))
    result['closure']=closure(before_fds);result['elapsed_seconds']=time.monotonic()-started
    if time.monotonic()>=deadline:raise TimeoutError('CPU allocation normal return deadline')
    bounds.write_new(output/'result.json',result)
    closure(before_fds)
    if time.monotonic()>=deadline:raise TimeoutError('CPU publication return deadline')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--configuration',required=True,type=Path);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();started=time.monotonic()
    if os.getpgrp()!=os.getpid():os.setsid()
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,200)
    try:
        raw=read(args.configuration,MiB,args.sha256);config=decode(raw);validate_configuration(config)
        if canonical(config)!=raw:raise ValueError('Canonical CPU configuration bytes required')
        for row in config['sources']:
            if len(read(ROOT/row['path'],MiB,row['sha256']))!=row['size_bytes']:raise ValueError('CPU frozen source size differs')
        if (str(Path(sys.executable).resolve())!=PYTHON or not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode)
                or os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH')):
            raise ValueError('Original isolated CPU parent interpreter required')
        if os.path.lexists(ROOT/OUTPUTS[config['phase']]):raise FileExistsError('CPU allocation already reserved')
        sys.pycache_prefix=str(ROOT/OUTPUTS[config['phase']]/'unused-parent-pycache')
        for key in ('NOFILE','AS','FSIZE'):
            value=config['limits'][{'NOFILE':'max_fds','AS':'address_space_bytes','FSIZE':'file_bytes'}[key]]
            resource.setrlimit(getattr(resource,'RLIMIT_'+key),(value,value))
        result=execute(config,raw,started)
        print(canonical(result).decode(),end='',flush=True)
        return 0 if result['status'] in ('prepared','imports_completed') and time.monotonic()<started+180 else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
