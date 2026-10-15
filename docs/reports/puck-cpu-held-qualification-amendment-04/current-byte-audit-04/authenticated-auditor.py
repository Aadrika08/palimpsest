"""Independent byte-only audit of one frozen CPU held-allocation outcome.

No repository validator, installer, loader or vendor package is imported. PASS
means the specified ordinary outcome and its retained bytes were observed; all
scientific and executable authority remains false. Process/RSS receipts are
sampled operational observations, not historical continuous measurements.
"""
import argparse
import ast
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import stat
import sys
import time

MiB=1024**2
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
INTERPRETER=dict(path=PYTHON,size_bytes=21662864,sha256='572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a')
PARENT='scripts/qualify_puck_cpu_held_runtime.py'
HISTORICAL_AUDITOR_SHA256='19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9'
BOOTSTRAP='scripts/puck_worker_bootstrap.py'
OUTPUTS=dict(prepare='runs/puck-cpu-held-preparation-01',qualify='runs/puck-cpu-held-qualification-01')
VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',torchvision='0.24.0+cpu',mujoco='3.3.6')
CLAIMS=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,executable=False,qualification_claims=[])
ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/puck/source',PATH='/nonexistent',TZ='UTC',CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0')
WORKER=tuple(sorted((BOOTSTRAP,'src/palimpsest/__init__.py','src/palimpsest/puck_execution_files.py','src/palimpsest/puck_dependency_files.py','src/palimpsest/puck_dependency_bindings.py','src/palimpsest/puck_dependency_imports.py','src/palimpsest/puck_native_origins.py','src/palimpsest/puck_native_identity.py','src/palimpsest/puck_worker_preflight.py','src/palimpsest/puck_runtime_qualification.py')))
SOURCES=tuple(sorted(set(WORKER)|{PARENT,'scripts/stage_puck_cpu_held_runtime.py','scripts/qualify_puck_held_runtime.py','scripts/build_puck_python_louvain.py','scripts/acquire_puck_cpu_payloads.py','src/palimpsest/bounded_qualification.py','src/palimpsest/evaluate.py','src/palimpsest/puck_build_inputs.py','src/palimpsest/puck_package_payloads.py','src/palimpsest/puck_retained_installation.py','src/palimpsest/puck_runtime_registration.py','src/palimpsest/puck_runtime_staging.py','src/palimpsest/puck_cpu_registration.py','src/palimpsest/puck_cpu_namespace.py'}))
ROLES=tuple(sorted(('inventory','layout','candidate','native','baseline','generated','accepted_result','accepted_snapshot','accepted_audit','accepted_configuration','accepted_index','observation_configuration','observation_report','observation_result','observation_audit','observation_index')))


def require(value,message):
    if not value:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value,lf=True):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+('\n' if lf else '')).encode()


def integer(value,minimum=0,maximum=2**63-1):
    return type(value) is int and minimum<=value<=maximum


def finite(value,maximum):
    return type(value) in (int,float) and math.isfinite(value) and 0<value<maximum


def relative(value):
    require(type(value) is str and 0<len(value.encode('utf-8'))<=4096 and '\\' not in value and '\x00' not in value and not value.startswith('/') and len(value.split('/'))<=32 and all(p not in ('','.','..') and len(p.encode('utf-8'))<=255 for p in value.split('/')),'Canonical bounded relative path required')
    return value


def absolute(value):
    require(type(value) is str and value.startswith('/') and '\x00' not in value and str(Path(value))==value,'Canonical absolute path required')
    if value!='/':relative(value[1:])
    return value


def pin(row,maximum=16*MiB):
    require(type(row) is dict and set(row)=={'path','size_bytes','sha256'} and integer(row['size_bytes'],0,maximum) and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['sha256']) is not None,'Exact bounded descriptor pin required')
    relative(row['path']);return row


def decode(raw):
    def pairs(rows):
        result={}
        for key,value in rows:
            require(key not in result,'Duplicate JSON key');result[key]=value
        return result
    def bad(_):raise ValueError('Nonfinite JSON constant')
    try:value=json.loads(raw,object_pairs_hook=pairs,parse_constant=bad)
    except (UnicodeError,RecursionError,ValueError) as error:raise ValueError('Invalid bounded JSON') from error
    pending=[(value,0)];count=0
    while pending:
        item,depth=pending.pop();count+=1
        require(count<=524288 and depth<=32,'JSON tree ceiling exceeded')
        require(type(item) is not float or math.isfinite(item),'Nonfinite JSON number')
        if type(item) is dict:pending.extend((v,depth+1) for v in item.values())
        elif type(item) is list:pending.extend((v,depth+1) for v in item)
    require(type(value) is dict,'JSON object required');return value


def stamp(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


def edge(s):return s.st_dev,s.st_ino,s.st_mode


class Held:
    """Finite nofollow custody; outside ancestors retain identity, selected dirs full metadata."""
    def __init__(self,deadline):
        self.deadline=deadline;self.dirs={};self.files={};self.links={};self.total=0;self.metadata=0;self.identities={}
    def clock(self):
        if time.monotonic()>=self.deadline:raise TimeoutError('Independent CPU audit deadline exhausted')
    def directory(self,path,strict=False):
        self.clock();path=absolute(str(path))
        if path in self.dirs:
            row=self.dirs[path]
            if strict:row['strict']=True
            self.check_dir(path,row);return row['fd']
        parent=None if path=='/' else str(Path(path).parent)
        pfd=None if parent is None else self.directory(parent)
        fd=os.open('/' if parent is None else Path(path).name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=pfd)
        try:
            state=os.fstat(fd);require(stat.S_ISDIR(state.st_mode),'Directory required')
            require(len(self.dirs)+len(self.files)+len(self.links)<40000,'Audit descriptor/entry ceiling exceeded')
            self.dirs[path]=dict(fd=fd,stamp=stamp(state),strict=strict,parent=parent)
        except BaseException:os.close(fd);raise
        return fd
    def check_dir(self,path,row):
        state=os.fstat(row['fd']);expected=row['stamp'];actual=stamp(state)
        require(actual==expected if row['strict'] else actual[:3]==expected[:3],'Held directory changed: '+path)
        if row['parent'] is not None:
            named=os.stat(Path(path).name,dir_fd=self.dirs[row['parent']]['fd'],follow_symlinks=False)
            require((stamp(named)==expected if row['strict'] else edge(named)==expected[:3]),'Held directory edge changed: '+path)
    def file(self,path,expected=None,maximum=1024*MiB,*,raw=False,single=True):
        self.clock();path=absolute(str(path))
        if path in self.files:
            row=self.files[path];self.check_file(path,row)
            require(row['size']<=maximum and (not single or row['stamp'][3]==1),'Repeated file bound/link policy differs')
            if expected is not None:require(row['size']==expected['size_bytes'] and row['sha256']==expected['sha256'],'File hash/pin differs: '+path)
            if raw and row['raw'] is None:raise ValueError('Repeated metadata/data role differs')
            return row['raw'] if raw else dict(size_bytes=row['size'],sha256=row['sha256'])
        parent=str(Path(path).parent);pfd=self.directory(parent)
        fd=os.open(Path(path).name,os.O_RDONLY|os.O_NONBLOCK|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=pfd)
        try:
            state=os.fstat(fd)
            require(stat.S_ISREG(state.st_mode) and (not single or state.st_nlink==1) and 0<=state.st_size<=maximum,'Bounded regular file required: '+path)
            require(len(self.files)+len(self.dirs)+len(self.links)<40000 and self.total+state.st_size<=2048*MiB,'Audit file/byte ceiling exceeded')
            if raw:require(maximum<=16*MiB and self.metadata+state.st_size<=64*MiB,'Audit metadata ceiling exceeded')
            value,payload=self.hash_fd(fd,raw)
            require(value['size_bytes']==state.st_size,'File size changed: '+path)
            if expected is not None:require(value['size_bytes']==expected['size_bytes'] and value['sha256']==expected['sha256'],'File SHA/hash pin differs: '+path)
            row=dict(fd=fd,parent=parent,stamp=stamp(state),size=state.st_size,sha256=value['sha256'],raw=payload)
            self.check_file(path,row);self.files[path]=row;self.total+=state.st_size
            if raw:self.metadata+=state.st_size
        except BaseException:os.close(fd);raise
        return payload if raw else value
    def hash_fd(self,fd,raw=False):
        os.lseek(fd,0,os.SEEK_SET);digest=hashlib.sha256();size=0;parts=[] if raw else None
        while True:
            self.clock();chunk=os.read(fd,MiB)
            if not chunk:break
            size+=len(chunk);require(size<=1024*MiB,'File read ceiling exceeded');digest.update(chunk)
            if raw:parts.append(chunk)
        return dict(size_bytes=size,sha256=digest.hexdigest()),b''.join(parts) if raw else None
    def check_file(self,path,row):
        require(stamp(os.fstat(row['fd']))==row['stamp'] and stamp(os.stat(Path(path).name,dir_fd=self.dirs[row['parent']]['fd'],follow_symlinks=False))==row['stamp'],'Held file changed: '+path)
    def json(self,path,expected=None,maximum=16*MiB,*,lf=None):
        raw=self.file(path,expected,maximum,raw=True);value=decode(raw)
        if lf is not None:require(canonical(value,lf)==raw,'Canonical JSON bytes differ: '+str(path))
        return value,raw
    def symlink(self,path,target):
        self.clock();path=absolute(str(path));pfd=self.directory(str(Path(path).parent))
        state=os.stat(Path(path).name,dir_fd=pfd,follow_symlinks=False)
        require(stat.S_ISLNK(state.st_mode) and os.readlink(Path(path).name,dir_fd=pfd)==target,'Trusted alias differs: '+path)
        if path in self.links:require(self.links[path][0]==stamp(state),'Trusted alias changed: '+path)
        else:
            require(len(self.files)+len(self.dirs)+len(self.links)<40000,'Audit entry ceiling exceeded');self.links[path]=(stamp(state),target)
    def recheck(self):
        for path,row in self.dirs.items():self.clock();self.check_dir(path,row)
        for path,row in self.files.items():
            self.clock();self.check_file(path,row);value,_=self.hash_fd(row['fd']);require(value==dict(size_bytes=row['size'],sha256=row['sha256']),'Held content hash changed: '+path);self.check_file(path,row)
        for path,(_,target) in self.links.items():self.symlink(path,target)
    def close(self):
        error=None
        for row in [*reversed(list(self.files.values())),*reversed(list(self.dirs.values()))]:
            try:os.close(row['fd'])
            except OSError as exc:
                if error is None:error=exc
        self.files.clear();self.dirs.clear()
        if error is not None:raise error


def no_authority(value,keys=tuple(k for k in CLAIMS if k!='qualification_claims')):
    require(type(value) is dict and all(value.get(k) is False for k in keys) and value.get('qualification_claims')==[],'False authority/claims required')


def limits(phase,authored):
    return dict(normal_seconds=180,child_hard_seconds=190,hard_seconds=200,rss_bytes=2048*MiB,address_space_bytes=8192*MiB,output_bytes=64*MiB,scratch_bytes=64*MiB,file_bytes=(1024 if phase=='prepare' else 16)*MiB,min_free_bytes=4096*MiB,min_available_ram_bytes=(128 if authored else 4096 if phase=='prepare' else 2048)*MiB,min_tmpfs_free_bytes=(2048 if phase=='prepare' else 256)*MiB,max_processes=3,max_fds=40000)


def configuration(config,authored):
    phase=config.get('phase');amended=config.get('kind')=='puck-cpu-held-runtime-allocation-v2';version=2 if amended else 1
    keys={'kind','version','phase','allocation_id','root','stage_parent','sources','inputs','interpreter','environment','expected_versions','limits','negative_imports','claims'}
    if phase=='qualify':keys.add('preparation_acceptance' if amended else 'preparation')
    require(phase in OUTPUTS and (not amended or phase=='qualify') and set(config)==keys and config['kind']=='puck-cpu-held-runtime-allocation-v'+str(version) and type(config['version']) is int and config['version']==version and type(config['allocation_id']) is int and config['allocation_id']==version,'Exact allocation configuration required')
    absolute(config['root']);stage=absolute(config['stage_parent'])
    require(re.fullmatch('/tmp/palimpsest-puck-cpu-held-[A-Za-z0-9_-]+',stage) is not None,'Private direct tmpfs allocation required')
    require(config['interpreter']==INTERPRETER and canonical(config['environment'])==canonical(ENVIRONMENT) and config['expected_versions']==VERSIONS and canonical(config['limits'])==canonical(limits(phase,authored)),'Exact interpreter/environment/resource limits required')
    no_authority(config['claims'])
    require(type(config['sources']) is list and [pin(r,MiB)['path'] for r in config['sources']]==list(SOURCES) and type(config['inputs']) is dict and set(config['inputs'])==set(ROLES),'Exact 24-source/16-role closure required')
    rows=config['sources']+list(config['inputs'].values())
    for row in config['inputs'].values():pin(row)
    require(len({r['path'] for r in rows})==len(rows),'Overlapping source/input paths')
    expected=['org'] if authored else ['numpy._distributor_init_local','org']
    require(config['negative_imports']==expected,'Exact finite missing-import roster required')
    if amended:
        acceptance=config['preparation_acceptance']
        require(type(acceptance) is dict and set(acceptance)=={'configuration','result','independent_audit','externally_observed_auditor_cli'},'Exact historical preparation acceptance required')
        for row in acceptance.values():pin(row)
        require(acceptance['result']['path']==OUTPUTS['prepare']+'/result.json' and len({r['path'] for r in acceptance.values()})==4,'Exact distinct preparation01 acceptance pins required')
    elif phase=='qualify':require(pin(config['preparation'])['path']==OUTPUTS['prepare']+'/result.json','Exact preparation pin required')


def allocation_output(config):
    return 'runs/puck-cpu-held-qualification-02' if config['version']==2 else OUTPUTS[config['phase']]


def preparation_epoch(current,historical,prep):
    require(historical.get('kind')=='puck-cpu-held-runtime-allocation-v1' and type(historical.get('version')) is int and historical['version']==1 and historical.get('phase')=='prepare' and type(historical.get('allocation_id')) is int and historical['allocation_id']==1,'Historical preparation01 configuration required')
    shared=('root','stage_parent','inputs','interpreter','environment','expected_versions','negative_imports','claims')
    require(all(canonical(current[k])==canonical(historical[k]) for k in shared),'Historical preparation data or policy changed')
    require(prep.get('sources')==historical.get('sources') and prep.get('inputs')==historical.get('inputs'),'Preparation historical source/input binding differs')
    old={r['path']:r for r in historical['sources']};new={r['path']:r for r in current['sources']}
    require(list(old)==list(SOURCES) and list(new)==list(SOURCES),'Historical/current source roster differs')
    changed={name for name in old if canonical(old[name])!=canonical(new[name])}
    require(BOOTSTRAP in changed and changed<={PARENT,BOOTSTRAP},'Source amendment must change bootstrap and only parent/bootstrap')


def historical_acceptance(held,current,authored):
    root=Path(current['root']);pins=current['preparation_acceptance']
    old,oldraw=held.json(root/pins['configuration']['path'],pins['configuration'],MiB,lf=True)
    configuration(old,authored)
    prep,prepraw=held.json(root/pins['result']['path'],pins['result'],MiB,lf=True)
    outcome(prep,old,sha(oldraw));preparation_epoch(current,old,prep)
    audit,araw=held.json(root/pins['independent_audit']['path'],pins['independent_audit'],MiB)
    no_authority(audit)
    require(not {'error','error_type'}&set(audit),'Historical preparation audit contains an error')
    require(audit.get('kind')=='puck-cpu-held-runtime-independent-audit-v1' and type(audit.get('version')) is int and audit['version']==1 and audit.get('status')=='PASS' and audit.get('phase')=='prepare' and audit.get('observed_status')=='prepared' and audit.get('held_four_imports_observed') is False and audit.get('auditor_source_sha256')==HISTORICAL_AUDITOR_SHA256 and audit.get('configuration_sha256')==sha(oldraw) and audit.get('result_sha256')==sha(prepraw) and audit.get('dependencies_sha256')==prep.get('dependencies',{}).get('sha256') and type(audit.get('external_returncode')) is int and audit['external_returncode']==0 and audit.get('evidence_scope')==('AUTHORED fixture only' if authored else 'ordinary CPU held allocation only') and finite(audit.get('elapsed_seconds'),120),'Historical preparation PASS audit binding differs')
    require(audit.get('closure')==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[]) and type(audit.get('root_count')) is int and audit['root_count']==4,'Historical preparation audit closure/root count differs')
    cli,_=held.json(root/pins['externally_observed_auditor_cli']['path'],pins['externally_observed_auditor_cli'],64*1024)
    required={'kind','command','observed_returncode','elapsed_seconds','published','stdout','stderr'}
    require(set(cli) in (required,required|{'at','scope'}) and ('at' not in cli or type(cli['at']) is str and 0<len(cli['at'])<=128 and cli['scope']=='fresh read-only current-byte audit of prepared data; no preparation or qualification allocation invoked'),'Historical audit CLI fields/metadata differ')
    require(cli.get('kind')=='externally-observed-cpu-auditor-cli-v1' and type(cli.get('observed_returncode')) is int and cli['observed_returncode']==0 and finite(cli.get('elapsed_seconds'),130) and not {'error','error_type'}&set(cli),'Normal historical preparation audit CLI required')
    for channel in ('published','stdout','stderr'):
        row=cli.get(channel);require(type(row) is dict and set(row)=={'path','size_bytes','sha256'},'Historical audit stream descriptor differs');absolute(row['path'])
        require(type(row['size_bytes']) is int and row['size_bytes']==(0 if channel=='stderr' else len(araw)) and row['sha256']==(sha(b'') if channel=='stderr' else sha(araw)),'Historical audit published/stdout/stderr byte pin differs')
    transport='authored-prepare-transport.json' if authored else OUTPUTS['prepare']+'-external-cli-transport.json'
    expected=[PYTHON,'-I','-S','-B',str(root/'scripts/audit_puck_cpu_held_runtime.py'),'--configuration',str(root/pins['configuration']['path']),'--sha256',sha(oldraw),'--transport',str(root/transport),'--transport-sha256',audit.get('transport_sha256'),'--output',cli['published']['path']]
    require(type(audit.get('transport_sha256')) is str and re.fullmatch('[0-9a-f]{64}',audit['transport_sha256']) is not None and cli.get('command')==expected,'Historical preparation audit invocation differs')
    return old,prep,audit



def inputs_binding(config,data,blobs):
    pins=config['inputs'];accepted=data['accepted_result'];snapshot=data['accepted_snapshot'];audit=data['accepted_audit'];candidate=data['candidate'];observation=data['observation_report'];observed=data['observation_result'];audit02=data['observation_audit'];inv=data['inventory']
    require(accepted.get('kind')=='cpu-retained-installation-admission-result-v2' and accepted.get('status')=='PASS' and accepted.get('claims',{}).get('package_preparation_accepted') is True and all(accepted['claims'].get(k) is False for k in ('runtime_qualified','numerical_imports_executed','study_authorized','collection_authorized')),'Accepted package result differs')
    require(accepted.get('configuration_sha256')==pins['accepted_configuration']['sha256']==snapshot.get('configuration_sha256')==audit.get('verified',{}).get('configuration_sha256') and accepted.get('snapshot_sha256')==pins['accepted_snapshot']['sha256'] and audit.get('status')=='PASS' and audit.get('package_preparation_accepted') is True,'Accepted package receipt binding differs')
    require(accepted.get('site_root')==snapshot.get('site_root')==config['root']+'/runs/puck-cpu-install-01/site','Accepted SITE binding differs')
    require([accepted.get(k) for k in ('file_count','directory_count','regular_file_bytes')]==[inv.get(k) for k in ('file_count','directory_count','total_bytes')],'Accepted inventory totals differ')
    require([r for r in data['accepted_configuration'].get('inputs',[]) if r.get('path')==pins['layout']['path']]==[pins['layout']],'Accepted layout pin differs')
    require(observed.get('status')=='observed' and observed.get('report_sha256')==pins['observation_report']['sha256'] and observed.get('configuration_sha256')==pins['observation_configuration']['sha256'] and observation.get('kind')=='puck-runtime-import-characterization-result-v3' and observation.get('versions')==observed.get('versions')==candidate.get('expected_versions')==VERSIONS,'Ordinary observation binding differs')
    no_authority(observed)
    require(candidate.get('retained_inventory_sha256')==pins['inventory']['sha256'] and candidate.get('observation_report_sha256')==pins['observation_report']['sha256'] and candidate.get('configuration_sha256')==pins['observation_configuration']['sha256'] and candidate.get('outcome_audit_sha256')==pins['observation_audit']['sha256'] and audit02.get('status')=='PASS' and audit02.get('ordinary_imports_observed') is True and audit02.get('verified',{}).get('result_sha256')==pins['observation_result']['sha256'] and audit02['verified'].get('report_sha256')==pins['observation_report']['sha256'],'Candidate observation evidence differs')
    old=data['observation_configuration'];require(old.get('kind')=='puck-cpu-runtime-characterization-v1' and type(old.get('version')) is int and old['version']==1,'Observation configuration kind differs')
    oldrows=old.get('inputs');require(type(oldrows) is list,'Observation input rows required');indexed={r['path']:r for r in oldrows};require(len(indexed)==len(oldrows),'Duplicate observation input')
    for role in ('inventory','layout','native','baseline','accepted_result','accepted_snapshot','accepted_audit','accepted_configuration','accepted_index'):
        require(old.get('roles',{}).get('native_metadata' if role=='native' else role)==pins[role]['path'] and indexed.get(pins[role]['path'])==pins[role],'Observation role pin differs: '+role)
    for role,kind,names in (
        ('accepted_index','retained-admission-02-evidence-index-v1',{'inventory':'raw/inventory.json','accepted_result':'raw/result.json','accepted_snapshot':'raw/snapshot.json','accepted_audit':'acceptance-audit-03.json','accepted_configuration':'raw/configuration.json'}),
        ('observation_index','cpu-characterization-evidence-index-v2',{'observation_configuration':'frozen-configuration.json','observation_report':'raw/payload/imports.json','observation_result':'raw/result.json','observation_audit':'outcome-audit-02.json'})):
        value=data[role];entries=value.get('entries');require(value.get('kind')==kind and type(entries) is list and 1<=len(entries)<=512,'Evidence index schema differs');rows={r['path']:r for r in entries};require(len(rows)==len(entries),'Duplicate evidence index row')
        for name,path in names.items():
            expected=dict(pins[name],path=path)
            if name=='accepted_configuration':
                compact=canonical(data[name]);expected.update(size_bytes=len(compact),sha256=sha(compact))
            require(rows.get(path)==expected,'Evidence index binding differs: '+name)


def descriptors(rows,absolute_paths=False):
    require(type(rows) is list and 0<len(rows)<=40000,'Bounded file descriptor list required');paths=[]
    for row in rows:
        require(type(row) is dict and set(row)=={'path','size_bytes','sha256'},'File descriptor fields differ')
        (absolute if absolute_paths else relative)(row['path']);require(integer(row['size_bytes'],0,1024*MiB) and type(row['sha256']) is str and re.fullmatch('[0-9a-f]{64}',row['sha256']) is not None,'File descriptor size/hash differs');paths.append(row['path'])
    require(paths==sorted(set(paths)) and sum(r['size_bytes'] for r in rows)<=2048*MiB,'File ordering/byte ceiling differs');return {r['path']:r for r in rows}


def parents(files):
    result=set()
    for name in files:
        parent=str(Path(name).parent)
        while parent!='.':result.add(parent);parent=str(Path(parent).parent)
    return sorted(result)


def plan(config,data):
    inv,layout,candidate,native=(data[k] for k in ('inventory','layout','candidate','native'))
    require(set(inv)=={'kind','entries','file_count','directory_count','total_bytes'} and inv['kind']=='puck-cpu-installed-files-v1','Installed inventory schema differs');files=descriptors(inv['entries'])
    dirs=layout.get('predicted_destination_directories');require(layout.get('kind')=='palimpsest-cpu-wheel-install-layout-v1' and type(layout.get('version')) is int and layout['version']==1 and type(dirs) is list and dirs==sorted(set(dirs)),'Layout directory schema differs')
    for name in dirs:relative(name)
    require(not set(dirs)&set(files) and set(parents([*dirs,*files]))<=set(dirs),'File/directory ancestry differs')
    require(all(type(inv[k]) is int and inv[k]==v for k,v in (('file_count',len(files)),('directory_count',len(dirs)),('total_bytes',sum(r['size_bytes'] for r in files.values())))),'Inventory totals differ')
    nonempty={str(Path(p).parent) for p in [*dirs,*files]};require(layout.get('predicted_empty_destination_directories')==[p for p in dirs if p not in nonempty],'Empty directory plan differs')
    collisions=layout.get('collisions',{});flags={'case_sensitive_linux_paths','destination_directory_coownership_is_allowed'};empty={'destination_regular_directory_path_conflicts','destination_regular_path_collisions_including_entrypoint_wrappers','source_file_ancestor_conflicts','source_regular_directory_path_conflicts','source_regular_path_collisions'}
    require(set(collisions)==flags|empty and all(collisions[k] is True for k in flags) and all(collisions[k]==[] for k in empty),'Unresolved layout collision')
    dists=[];seen=set()
    for row in layout.get('wheels',[]):
        path=relative(row.get('metadata_path'));require(path.endswith('.dist-info/METADATA') and path in files and path not in seen and row.get('metadata_sha256')==files[path]['sha256'] and type(row.get('name')) is str and type(row.get('version')) is str,'Distribution METADATA pin differs');seen.add(path);dists.append(dict(name=row['name'],version=row['version'],root_index=0,metadata_path=path))
    require(seen=={p for p in files if p.endswith('.dist-info/METADATA')} and 0<len(dists)<=40000,'Distribution closure differs')
    require(native.get('kind')=='puck-cpu-characterization-native-metadata-v5' and native.get('status')=='COMPLETE' and native.get('root_scope')=='installed_shared_objects_and_interpreter' and all(native.get(k)==[] for k in ('errors','oversized_native_files','required_missing_names')),'Native metadata incomplete')
    nativefiles=descriptors(native.get('native_files'),True);groups=[inv['entries'],[],[],[]]
    for path,row in nativefiles.items():
        require(path.startswith('/usr/lib/') or path in ('/usr/bin/ldconfig','/etc/ld.so.cache'),'Native path outside fixed closure');index=1 if path.startswith('/usr/') else 2;groups[index].append(dict(row,path=path[5:]));
    require(groups[1] and groups[2],'Both native roots required')
    require(candidate.get('kind')=='puck-cpu-observed-import-profile-candidate-v1' and type(candidate.get('version')) is int and candidate['version']==1,'Candidate schema differs')
    no_authority(candidate,('native_phase_qualified','held_runtime_qualified','native_authorized','collection_authorized','study_authorized','executable'))
    extra=candidate.get('additional_package_inputs');require(type(extra) is list and len(extra)==1 and set(extra[0])=={'root','files'} and len(extra[0]['files'])==1,'One generated helper required');relative(extra[0]['root']);descriptors(extra[0]['files']);groups[3]=extra[0]['files']
    require(config['inputs']['generated']==dict(groups[3][0],path=extra[0]['root']+'/'+groups[3][0]['path']),'Generated helper attachment differs')
    profile=candidate.get('import_profile');require(type(profile) is dict and profile.get('kind')=='puck-producer-import-profile-v2' and type(profile.get('version')) is int and profile['version']==2 and all(type(profile.get(k)) is list for k in ('exports','module_changes','native_origins','native_cache')),'Enhanced import profile required')
    modules=candidate.get('module_paths');require(type(modules) is list and [r.get('name') for r in modules]==sorted({r.get('name') for r in modules}) and type(candidate.get('namespaces')) is list,'Module mapping order differs')
    for row in modules:
        require(integer(row.get('root_index'),0,3) and row.get('path') in {r['path'] for r in groups[row['root_index']]} and row.get('kind') in ('python','extension') and type(row.get('is_package')) is bool,'Module map is outside declared file plan')
    directories=[dirs,*[parents([r['path'] for r in group]) for group in groups[1:]]]
    require(sum(len(g)+len(d) for g,d in zip(groups,directories))<=40000 and sum(r['size_bytes'] for g in groups for r in g)<=2048*MiB,'Staged forest ceiling exceeded')
    source=dict(kind='puck-worker-dependencies-v2',version=2,roots=[dict(root=config['root']+'/runs/puck-cpu-install-01/site',kind='package',files=groups[0]),dict(root='/usr',kind='system_images',files=groups[1]),dict(root='/etc',kind='system_images',files=groups[2]),dict(root=str(Path(config['root'])/Path(config['inputs']['generated']['path']).parent),kind='package',files=groups[3])],modules=[],namespaces=[],distributions=dists,import_profile=dict(exports=[],module_changes=[],native_origins=[]))
    staged=dict(kind='puck-worker-dependencies-v3',version=3,native_identity='tmpfs-raw-dev-inode-v1',roots=[dict(root='/puck/staged/inputs/root-'+str(i).zfill(4),kind='package',files=g) for i,g in enumerate(groups)],modules=modules,namespaces=candidate['namespaces'],distributions=dists,import_profile=profile)
    return source,staged,directories


def tmpfs(fd):
    data=ctypes.create_string_buffer(256);libc=ctypes.CDLL(None,use_errno=True);libc.fstatfs.argtypes=(ctypes.c_int,ctypes.c_void_p);libc.fstatfs.restype=ctypes.c_int
    require(libc.fstatfs(fd,data)==0 and ctypes.c_long.from_buffer(data).value==0x01021994,'Staged descriptor is not tmpfs')


def forest(held,config,dependency,directories,identities):
    for path,names in ((config['stage_parent'],{'inputs'}),(config['stage_parent']+'/inputs',{'root-'+str(i).zfill(4) for i in range(4)})):
        fd=held.directory(path,True);state=os.fstat(fd);tmpfs(fd);require(stat.S_IMODE(state.st_mode)==0o700 and state.st_uid==os.getuid(),'Private owned staged parent required')
        require(set(os.listdir(fd))==names,'Exact private staged mount-wrapper namespace required')
    require(type(identities) is list and len(identities)==4,'Four retained root identities required');seen=set();tree=[]
    for i,root in enumerate(dependency['roots']):
        host=config['stage_parent']+'/inputs/root-'+str(i).zfill(4);fd=held.directory(host,True);state=os.fstat(fd);tmpfs(fd)
        expected=dict(root_index=i,device=state.st_dev,inode=state.st_ino)
        require(identities[i]==expected and all(type(v) is int for v in identities[i].values()) and stat.S_IMODE(state.st_mode)==0o700 and state.st_uid==os.getuid(),'Staged root identity/mode differs')
        require((state.st_dev,state.st_ino) not in seen,'Aliased staged root');seen.add((state.st_dev,state.st_ino))
        files={r['path']:r for r in root['files']};wanted=set(directories[i]);actualfiles=set();actualdirs=set();pending=[('',fd)]
        while pending:
            rel,dfd=pending.pop();held.clock();names=os.listdir(dfd);require(len(names)<=40000,'Directory census bound exceeded')
            for name in names:
                path=relative(name if not rel else rel+'/'+name);state=os.stat(name,dir_fd=dfd,follow_symlinks=False);full=host+'/'+path
                if stat.S_ISDIR(state.st_mode):
                    require(path in wanted and stat.S_IMODE(state.st_mode)==0o700,'Undeclared staged directory/mode: '+path);actualdirs.add(path);child=held.directory(full,True);pending.append((path,child))
                elif stat.S_ISREG(state.st_mode):
                    require(path in files,'Undeclared staged file: '+path);actualfiles.add(path);held.file(full,files[path]);row=held.files[full];tmpfs(row['fd']);ident=row['stamp'][:2];require(ident not in seen,'Aliased staged leaf');seen.add(ident)
                else:raise ValueError('Symlink/special staged entry refused: '+path)
        require(actualfiles==set(files) and actualdirs==wanted,'Staged census is incomplete')
        tree.append((host,sorted(actualfiles),sorted(actualdirs)))
    # Read only small distribution headers; the complete bodies were streamed.
    for distribution in dependency['distributions']:
        path=config['stage_parent']+'/inputs/root-0000/'+distribution['metadata_path'];row=held.files[path];os.lseek(row['fd'],0,os.SEEK_SET);header=os.read(row['fd'],64*1024).split(b'\n\n',1)[0];values={}
        for line in header.splitlines():
            if line.startswith((b'Name:',b'Version:')):
                key,value=line.split(b':',1);require(key not in values,'Duplicate METADATA header');values[key]=value.strip().decode('utf-8')
        require(values.get(b'Name')==distribution['name'] and values.get(b'Version')==distribution['version'],'Distribution Name/Version differs')
    return tree


def baseline(held,value):
    prefix=absolute(value.get('python_prefix'));files=value.get('files');links=value.get('symlinks')
    require(type(files) is list and type(links) is list and len(files)+len(links)<=10000,'Baseline manifest bound differs');expectedfiles={};expectedlinks={}
    for path,size,digest in files:pin(dict(path=path,size_bytes=size,sha256=digest),256*MiB);require(path not in expectedfiles,'Duplicate baseline file');expectedfiles[path]=(size,digest)
    for path,target in links:relative(path);require(path not in expectedlinks and type(target) is str,'Duplicate baseline link');expectedlinks[path]=target
    require(files==sorted(files) and links==sorted(links) and sum(v[0] for v in expectedfiles.values())<=256*MiB,'Baseline order/byte ceiling differs')
    observedfiles=[];observedlinks=[];pending=[('',held.directory(prefix,True))]
    while pending:
        rel,fd=pending.pop();held.clock()
        for name in os.listdir(fd):
            path=relative(name if not rel else rel+'/'+name);full=prefix+'/'+path;state=os.stat(name,dir_fd=fd,follow_symlinks=False)
            if stat.S_ISDIR(state.st_mode):pending.append((path,held.directory(full,True)))
            elif stat.S_ISREG(state.st_mode):
                require(path in expectedfiles,'Unexpected baseline file');size,digest=expectedfiles[path];row=held.file(full,dict(size_bytes=size,sha256=digest),256*MiB,single=False);observedfiles.append([path,row['size_bytes'],row['sha256']])
            elif stat.S_ISLNK(state.st_mode):
                require(path in expectedlinks,'Unexpected baseline alias');target=expectedlinks[path];held.symlink(full,target);resolved=Path(full).resolve(strict=True);require(resolved.is_relative_to(Path(prefix)),'Baseline alias escapes prefix');observedlinks.append([path,target])
            else:raise ValueError('Special trusted baseline entry')
    observedfiles.sort();observedlinks.sort();require(observedfiles==files and observedlinks==links,'Original baseline namespace differs')
    encoded=json.dumps(dict(files=observedfiles,symlinks=observedlinks),sort_keys=True,separators=(',',':')).encode();digest=sha(encoded)
    require(digest==value.get('prefix_manifest_sha256'),'Original baseline manifest hash differs')
    external=value.get('external_libraries');require(type(external) is list and len(external)<=128,'Baseline external closure bound')
    rows=list(external)
    if value.get('bwrap_executable') is not None:rows.append(value['bwrap_executable'])
    for row in rows:held.file(row.get('realpath',row.get('path')),dict(size_bytes=row['size'],sha256=row['sha256']),256*MiB,single=False)
    for path,target in value.get('host_path_aliases',[]):held.symlink(path,target)
    summary=dict(prefix_manifest_sha256=digest,regular_file_count=len(files),symlink_count=len(links),regular_file_bytes=sum(r[1] for r in files),external_file_count=len(rows))
    require(summary['regular_file_count']==value.get('regular_file_count') and summary['symlink_count']==value.get('symlink_count') and summary['regular_file_bytes']==value.get('regular_file_bytes'),'Baseline summary counts differ');return summary


def outcome(value,config,configsha):
    no_authority(value);phase=config['phase'];closure=value.get('closure');version=config['version']
    require(value.get('kind')=='puck-cpu-held-runtime-outcome-v'+str(version) and type(value.get('version')) is int and value['version']==version and value.get('phase')==phase and type(value.get('allocation_id')) is int and value['allocation_id']==config['allocation_id'] and value.get('configuration_sha256')==configsha and value.get('status')==('prepared' if phase=='prepare' else 'imports_completed') and value.get('held_four_imports_observed') is (phase=='qualify') and 'error' not in value and 'error_type' not in value and finite(value.get('elapsed_seconds'),180),'Normal successful parent outcome required')
    require(closure==dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5) and all(type(closure[k]) is int for k in ('fd_count_before','fd_count_after')),'Parent descriptor/process/thread closure differs')
    if phase=='prepare':require(value.get('stage_parent')==config['stage_parent'] and value.get('sources')==config['sources'] and value.get('inputs')==config['inputs'],'Preparation input/source custody differs')


def supervision(value,phase):
    require(value.get('status')=='completed' and type(value.get('returncode')) is int and value['returncode']==0 and value.get('failure') is None and value.get('matching_survivors')==[] and integer(value.get('pid'),1) and integer(value.get('sampled_peak_rss_bytes'),1,2048*MiB) and finite(value.get('rss_sampling_seconds'),1) and finite(value.get('finished_monotonic'),float('inf')),'Normal bounded supervision required')
    if phase=='qualify':
        rows=value.get('tracked_processes');require(value.get('process_scope')=='descendants' and type(rows) is list and len(rows)==3 and all(type(r) is dict and set(r)=={'pid','start_ticks'} and integer(r['pid'],1) and integer(r['start_ticks'],1) for r in rows) and len({(r['pid'],r['start_ticks']) for r in rows})==3,'Qualification descendant identities incomplete')


def binding_receipt(value,dependency):
    """Check the provider's actual snapshot schema, including nonempty profiles."""
    profile=dependency['import_profile'];mapped={r['name']:r for r in dependency['modules']+dependency['namespaces']}
    loaded=value.get('loaded_modules');require(type(loaded) is list and len(loaded)<=40000,'Loaded dependency receipt bound differs')
    names=[]
    for row in loaded:
        require(type(row) is dict and set(row)=={'name','path'} and row.get('name') in mapped and row.get('path')==mapped[row['name']]['path'],'Loaded dependency source mapping differs');names.append(row['name'])
    require(names==sorted(set(names)) and set(VERSIONS)<=set(names),'Four loaded dependency roots required')
    exports=[dict(name=r['name'],producer=r['producer']) for r in sorted(profile['exports'],key=lambda r:r['name'])]
    require(value.get('exported_modules')==exports,'Complete producer export receipt required')
    require(value.get('native_origin_policies')=={r['name']:r['policy'] for r in profile['native_origins']},'Complete native-origin policies required')
    require(value.get('native_cache_modules',[])==sorted(profile['native_cache'],key=lambda r:r['name']),'Complete native cache bindings required')
    dispatch=value.get('module_dispatch_bindings');require(type(dispatch) is list and [r.get('name') for r in dispatch]==names,'Loaded module dispatch receipt differs')
    changes={r['name']:r for r in profile['module_changes']}
    for row in dispatch:
        delegates=row.get('delegate_attributes');change=changes.get(row['name'])
        require(set(row)=={'name','original_metadata_bound','delegate_attributes'} and row['original_metadata_bound'] is bool(change and change['kind']=='replace') and type(delegates) is list and len(delegates)<=512 and len(set(delegates))==len(delegates) and all(type(v) is str and 0<len(v)<=512 for v in delegates) and (change is not None or delegates==[]),'Module dispatch/original-metadata binding differs')


def worker(held,base,config,dep,depraw,sources):
    registration,regraw=held.json(base/'control/worker-registration.json',lf=False);stdout,raw=held.json(base/'logs/stdout.log',maximum=MiB,lf=True)
    files=[r for r in config['sources'] if r['path'] in WORKER];modules=[]
    for row in files:
        if row['path']==BOOTSTRAP:continue
        name=row['path'][4:-3].replace('/','.');name=name[:-9] if name.endswith('.__init__') else name;modules.append(dict(name=name,path=row['path']))
    tree=ast.parse(sources[BOOTSTRAP]);seeds=[n.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SEED' for t in n.targets)];require(len(seeds)==1,'Frozen bootstrap SEED missing');seed=ast.literal_eval(seeds[0]);require(type(seed) is str,'Frozen bootstrap SEED not literal')
    bootstrap=next(r for r in files if r['path']==BOOTSTRAP)
    prefix=[PYTHON,'-I','-B','-S','-c',seed,'/puck/source/'+BOOTSTRAP,bootstrap['sha256'],'/puck/control/worker-registration.json']
    expected=dict(kind='puck-worker-source-bootstrap-v3',version=3,source_root='/puck/source',source_files=files,modules=modules,namespaces=[],runtime=dict(root=str(Path(PYTHON).parent),files=[dict(path='python3.11',size_bytes=INTERPRETER['size_bytes'],sha256=INTERPRETER['sha256'])],python_version='3.11.15'),environment=ENVIRONMENT,cwd='/puck/source',argv_prefix=prefix,dependencies=dict(path='/puck/control/dependencies.json',size_bytes=len(depraw),sha256=sha(depraw)),qualification=dict(kind='puck-held-runtime-import-qualification-v3',version=3,expected_versions=VERSIONS,stdlib_cache_aliases={'__mp_main__':'__main__'},negative_imports=config['negative_imports']),qualification_claims=[],executable=False)
    require(canonical(registration,False)==canonical(expected,False),'Exact worker registration differs')
    no_authority(stdout,('runtime_qualified','dependencies_qualified','native_authorized','collection_authorized','executable'))
    require(stdout.get('kind')=='puck-worker-source-bootstrap-receipt-v1' and type(stdout.get('version')) is int and stdout['version']==1 and stdout.get('registration_sha256')==sha(regraw) and stdout.get('environment_sha256')==sha(canonical(ENVIRONMENT,False)) and stdout.get('interpreter_object_bound') is True and stdout.get('python_version')=='3.11.15' and stdout.get('expected_missing_imports')==config['negative_imports'] and type(stdout.get('denied_imports')) is list and set(stdout['denied_imports'])<=set(config['negative_imports']),'Worker bootstrap/source/negative-import receipt differs')
    process=stdout.get('process',{});parent=stdout.get('parent',{});require([process.get(k) for k in ('pid','parent_pid','pgid','sid')]==[2,1,2,2] and [parent.get(k) for k in ('pid','parent_pid','pgid','sid')]==[1,0,0,0] and integer(process.get('start_tick'),1) and integer(parent.get('start_tick'),1),'Held namespace/session topology differs')
    entry=stdout.get('entry_result',{});no_authority(entry,('runtime_qualified','native_authorized','collection_authorized','executable'));rows=entry.get('imports')
    require(entry.get('kind')=='puck-held-runtime-import-qualification-result-v2' and type(entry.get('version')) is int and entry['version']==2 and type(entry.get('qualification_version')) is int and entry['qualification_version']==3 and entry.get('status')=='imports_completed' and entry.get('held_imports_observed') is True and type(rows) is list and [r.get('name') for r in rows]==list(VERSIONS) and {r['name']:r.get('version') for r in rows}==VERSIONS and all(finite(r.get('seconds'),180) for r in rows),'Four ordered import versions incomplete')
    value=stdout.get('dependencies',{});require(type(value) is dict and all(value.get(k) is False for k in ('runtime_qualified','collection_authorized','executable')) and value.get('claims')==[],'Dependency custody false authority/claims required')
    require(value.get('kind')=='puck-worker-dependency-custody-v1' and value.get('registration_sha256')==sha(depraw) and value.get('registration_bytes')==len(depraw) and value.get('root_count')==4 and value.get('file_count')==sum(len(r['files']) for r in dep['roots']) and value.get('input_bytes')==sum(f['size_bytes'] for r in dep['roots'] for f in r['files']) and value.get('native_identity')=='tmpfs-raw-dev-inode-v1' and value.get('native_cache_modules',[])==sorted(dep['import_profile']['native_cache'],key=lambda r:r['name']) and value.get('protection_modes')==['linux_read_lease']*4 and all(value.get(k) is False for k in ('reservation_authorized','hostile_root_protection','external_hardlink_names_covered','source_closure')),'Held dependency/native-cache custody differs')
    binding_receipt(value,dep)
    images=value.get('images',{});require(all(images.get(k) is False for k in ('anonymous_code_qualified','native_closure_qualified','transient_images_covered')) and type(images.get('baseline_file_images')) is int and images['baseline_file_images']==9,'Native image authority/baseline count differs')
    image_rows=images.get('held_file_images');require(type(image_rows) is list and len(image_rows)<=40000,'Held native image receipt bound differs');seen_images=set();held_images={r['stamp'][:2] for path,r in held.files.items() if path.startswith(config['stage_parent']+'/inputs/')}
    for row in image_rows:
        require(type(row) is dict and set(row)=={'device','inode','paths'} and integer(row['device'],1) and integer(row['inode'],1) and (row['device'],row['inode']) in held_images and (row['device'],row['inode']) not in seen_images and type(row['paths']) is list and 0<len(row['paths'])<=128 and row['paths']==sorted(set(row['paths'])),'Held native image identity differs')
        for path in row['paths']:absolute(path)
        seen_images.add((row['device'],row['inode']))
    loaded=stdout.get('loaded_modules');require(type(loaded) is list and len(loaded)<=64,'Worker loaded-source receipt bound')
    required=[]
    for row in files:
        if row['path'] in (BOOTSTRAP,'src/palimpsest/puck_worker_preflight.py'):continue
        name=row['path'][4:-3].replace('/','.');name=name[:-9] if name.endswith('.__init__') else name
        required.append(dict(name=name,path=row['path'],sha256=row['sha256']))
        if row['path']=='src/palimpsest/puck_execution_files.py':required.append(dict(name='_puck_held_file_bootstrap',path=row['path'],sha256=row['sha256']))
    require(loaded==sorted(required,key=lambda r:r['name']),'Complete loaded support-source roster/digests required')
    require(stdout.get('stdlib_cache_aliases') in ({},{'__mp_main__':'__main__'}) and stdout.get('trusted_boundary')==['CPython stdlib','interpreter ELF dependencies'],'Worker stdlib boundary/aliases differ')
    return sha(raw),[PYTHON,'-I','-B','-S','-c','import os,sys;os.setsid();os.execv(sys.argv[1],sys.argv[1:])']+prefix+[sha(regraw)]


def namespace_command(config,data,phase,worker_command):
    """Independently reconstruct the finite bwrap argv; no source execution."""
    prefix=data['baseline']['python_prefix'];paths=sorted(r['path'] for r in data['native']['native_files'])
    expected=sorted(['/etc/ld.so.cache',PYTHON]+['/usr/lib/'+n for n in ('ld-linux-x86-64.so.2','libc.so.6','libdl.so.2','libm.so.6','libpthread.so.0','librt.so.1','libutil.so.1')])
    require(sorted(r['path'] for r in data['observation_report'].get('baseline_maps',{}).get('images',[]))==expected and set(expected)-{PYTHON}<=set(paths),'Exact original nine baseline images required')
    aliases={}
    for rows in (data['baseline'].get('host_path_aliases'),data['native'].get('aliases')):
        require(type(rows) is list and len(rows)<=128,'Namespace alias bound differs')
        for path,target in rows:
            absolute(path);relative(target);require(path not in paths and (path not in aliases or aliases[path]==target),'Namespace alias shadows/contradicts native file');aliases[path]=target
    base=Path(config['root'])/(OUTPUTS['prepare'] if phase=='prepare' else allocation_output(config));prepared=Path(config['root'])/OUTPUTS['prepare'];stage=config['stage_parent']
    command=['/usr/bin/bwrap','--unshare-all','--unshare-user']
    if phase=='prepare':command+=['--as-pid-1']
    command+=['--disable-userns','--die-with-parent','--cap-drop','ALL','--clearenv','--hostname','palimpsest-cpu-held','--ro-bind',prefix,prefix]
    for path in paths:
        origin=path
        if phase=='qualify' and path not in expected:origin=stage+'/inputs/'+('root-0001' if path.startswith('/usr/') else 'root-0002')+'/'+path[5:]
        command+=['--ro-bind',origin,path]
    for path,target in sorted(aliases.items(),key=lambda item:(item[0].count('/'),item[0])):command+=['--symlink',target,path]
    source=base/'worker-source' if phase=='qualify' and config['version']==2 else prepared/('parent-source' if phase=='prepare' else 'worker-source')
    command+=['--ro-bind',str(source),'/puck/source','--ro-bind',str(base/'control'),'/puck/control']
    if phase=='prepare':
        command+=['--bind',stage,'/puck/staged']
        for path in (config['root']+'/runs/puck-cpu-install-01/site',str((Path(config['root'])/config['inputs']['generated']['path']).parent)):command+=['--ro-bind',path,path]
    else:command+=['--ro-bind',stage+'/inputs','/puck/staged/inputs']
    command+=['--bind',str(base/'payload'),'/output','--size',str(64*MiB),'--tmpfs','/scratch']
    for name in ('home','tmp','pycache'):command+=['--dir','/scratch/'+name,'--chmod','0700','/scratch/'+name]
    command+=['--symlink','scratch/tmp','/tmp','--proc','/proc','--remount-ro','/proc','--dev','/dev','--remount-ro','/dev','--remount-ro','/']
    for key,value in sorted(ENVIRONMENT.items()):command+=['--setenv',key,value]
    return command+['--chdir','/puck/source']+worker_command


def audit(config_path,expected_sha256,transport_path,expected_transport_sha256,*,deadline):
    started=time.monotonic();require(type(deadline) in (int,float) and math.isfinite(deadline) and 0<deadline-started<=120,'Audit requires one finite future deadline at most 120 seconds')
    before=len(os.listdir('/proc/self/fd'));require(Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split()==[] and len(os.listdir('/proc/self/task'))==1,'Auditor must have no children or other threads')
    held=Held(deadline);report=None
    try:
        require(type(expected_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_sha256) is not None and type(expected_transport_sha256) is str and re.fullmatch('[0-9a-f]{64}',expected_transport_sha256) is not None,'External SHA pins required')
        # Authenticate the external bytes before any JSON interpretation.
        raw=held.file(absolute(str(config_path)),maximum=MiB,raw=True);require(sha(raw)==expected_sha256,'Configuration SHA/hash pin differs');config=decode(raw);require(raw==canonical(config),'Canonical external configuration required')
        traw=held.file(absolute(str(transport_path)),maximum=64*1024,raw=True);require(sha(traw)==expected_transport_sha256,'Transport SHA/hash pin differs');transport=decode(traw);require(traw==canonical(transport),'Canonical transport receipt required')
        authored=transport.get('kind')=='authored-cpu-parent-cli-transport-v1';require(authored or transport.get('kind')=='puck-cpu-held-cli-transport-v1','External transport kind differs')
        if authored:require(type(transport.get('authored_scope')) is str and transport['authored_scope'].startswith('AUTHORED fixture only;'),'Explicit authored transport scope required')
        configuration(config,authored);root=Path(config['root']);phase=config['phase'];base=root/allocation_output(config)
        require(Path(config_path).is_relative_to(root) and Path(transport_path).is_relative_to(root),'External control files must belong to configuration root')
        require(transport.get('configuration_sha256')==expected_sha256 and type(transport.get('observed_returncode')) is int and transport['observed_returncode']==0 and finite(transport.get('elapsed_seconds'),210),'Normal external transport exit required')
        if not authored:require(transport.get('phase')==phase and transport.get('timed_out') is False,'Normal phase-matched external transport required')
        command=[PYTHON,'-I','-S','-B',str(root/PARENT),'--configuration',str(config_path),'--sha256',expected_sha256];require(transport.get('command')==command,'Exact isolated parent transport command required')
        for name in ('stdout','stderr'):
            row=pin(transport.get(name));expectedpath=('authored-'+('qualify02' if config['version']==2 else phase)+'-cli.'+name) if authored else allocation_output(config)+'-external-cli.'+name
            require(row['path']==expectedpath,'Exact external transport stream path required');held.file(root/row['path'],row,16*MiB,raw=True)
        retained,_=held.json(base/'configuration.json',maximum=MiB,lf=True);require(retained==config and held.files[str(base/'configuration.json')]['raw']==raw,'Retained configuration bytes differ')
        blobs={};data={};sources={}
        for row in config['sources']:sources[row['path']]=held.file(root/row['path'],row,MiB,raw=True)
        for role,row in config['inputs'].items():
            blobs[role]=held.file(root/row['path'],row,16*MiB,raw=True)
            if role!='generated':data[role]=decode(blobs[role])
        inputs_binding(config,data,blobs);source,dependency,directories=plan(config,data)
        for row in data['native']['native_files']:held.file(row['path'],row,single=False)
        aliases=data['native'].get('aliases');require(type(aliases) is list and len(aliases)<=256 and len({r[0] for r in aliases})==len(aliases),'Native alias closure differs')
        for path,target in aliases:held.symlink(path,target)
        summary=baseline(held,data['baseline'])
        for name in ('baseline-before.json','baseline-after.json'):value,_=held.json(base/name,lf=True);require(value==summary,'Retained baseline summary differs')
        result,result_raw=held.json(base/'result.json',maximum=MiB,lf=True);outcome(result,config,expected_sha256)
        require(held.files[str(root/transport['stdout']['path'])]['raw']==result_raw,'External stdout differs from retained parent result')
        observed,_=held.json(base/'supervision.json',maximum=MiB,lf=True);supervision(observed,phase)
        admission,_=held.json(base/'resource-admission.json',maximum=MiB,lf=True)
        require(all(integer(admission.get(k),config['limits'][limit]) for k,limit in (('mem_available_bytes','min_available_ram_bytes'),('tmpfs_available_bytes','min_tmpfs_free_bytes'),('disk_available_bytes','min_free_bytes'))),'Resource admission receipt below frozen floors')
        prepbase=root/OUTPUTS['prepare']
        if phase=='prepare':prep=result;prepconfig=config
        else:
            if config['version']==2:
                prepconfig,prep,prior_audit=historical_acceptance(held,config,authored)
                _,pcraw=held.json(prepbase/'configuration.json',maximum=MiB,lf=True)
                require(pcraw==held.files[str(root/config['preparation_acceptance']['configuration']['path'])]['raw'],'Historical retained configuration bytes differ')
            else:
                prep,prepraw=held.json(root/config['preparation']['path'],config['preparation'],MiB,lf=True);prepconfig,pcraw=held.json(prepbase/'configuration.json',maximum=MiB,lf=True);configuration(prepconfig,authored);outcome(prep,prepconfig,sha(pcraw))
                require(prepconfig['phase']=='prepare' and all(prepconfig[k]==config[k] for k in config if k not in ('phase','limits','preparation')),'Qualification preparation epoch/input binding differs')
            psummary,_=held.json(prepbase/'baseline-before.json',lf=True);asummary,_=held.json(prepbase/'baseline-after.json',lf=True);require(psummary==asummary==summary,'Preparation baseline summaries differ')
            pobs,_=held.json(prepbase/'supervision.json',maximum=MiB,lf=True);supervision(pobs,'prepare')
        for folder,names in (('parent-source',SOURCES),('worker-source',WORKER)):
            for name in names:
                row=next(r for r in prepconfig['sources'] if r['path']==name);held.file(prepbase/folder/name,row,MiB)
        if config['version']==2:
            for name in WORKER:
                row=next(r for r in config['sources'] if r['path']==name);held.file(base/'worker-source'/name,row,MiB)
        copy,_=held.json(prepbase/'control/copy-registration.json',lf=False);require(canonical(copy,False)==canonical(source,False),'Independent source file plan differs')
        for role in ('candidate','layout'):require(held.file(prepbase/('control/'+role+'.json'),maximum=16*MiB,raw=True)==blobs[role],'Retained preparation input differs')
        request,requestraw=held.json(prepbase/'control/stage-request.json',maximum=MiB,lf=True)
        require(request==dict(registration=dict(path='/puck/control/copy-registration.json',sha256=sha(canonical(source,False))),candidate=dict(path='/puck/control/candidate.json',sha256=sha(blobs['candidate'])),layout=dict(path='/puck/control/layout.json',sha256=sha(blobs['layout']))),'Preparation stage-request pins differ')
        ref=pin(prep.get('dependencies'));require(ref['path']=='payload/dependencies.json','Prepared dependency reference differs');dep,depraw=held.json(prepbase/ref['path'],ref,lf=False);require(canonical(dep,False)==canonical(dependency,False),'Independent staged dependency plan/profile differs')
        stage,stage_raw=held.json(prepbase/'payload/stage.json',maximum=MiB,lf=True);no_authority(stage);require(stage.get('kind')=='puck-cpu-tmpfs-preparation-receipt-v1' and stage.get('status')=='prepared' and stage.get('dependencies')==ref and stage.get('staged_roots')==prep.get('staged_roots'),'Preparation stage receipt differs')
        require(held.file(prepbase/'logs/stdout.log',maximum=MiB,raw=True)==stage_raw,'Preparation stdout/stage receipt differs')
        held.file(prepbase/'logs/stderr.log',maximum=16*MiB)
        if config['version']==2:
            require(prior_audit.get('file_count')==sum(len(r['files']) for r in dep['roots']) and prior_audit.get('input_bytes')==sum(f['size_bytes'] for r in dep['roots'] for f in r['files']) and prior_audit.get('directory_count')==sum(len(d) for d in directories),'Historical preparation audit data totals differ')
        tree=forest(held,config,dependency,directories,prep['staged_roots'])
        if phase=='qualify':
            require(held.file(base/'control/dependencies.json',maximum=16*MiB,raw=True)==depraw,'Qualification control dependency bytes differ')
            worker_sha,worker_command=worker(held,base,config,dep,depraw,sources);require(worker_sha==result.get('worker_stdout_sha256'),'Worker stdout digest differs');held.file(base/'logs/stderr.log',maximum=16*MiB)
        stage_command=[PYTHON,'-I','-S','-B','/puck/source/scripts/stage_puck_cpu_held_runtime.py',sha(requestraw)]
        pinv,_=held.json(prepbase/'invocation.json',maximum=MiB,lf=True);require(pinv==dict(command=namespace_command(prepconfig,data,'prepare',stage_command),configuration_sha256=prep['configuration_sha256']),'Preparation namespace invocation differs')
        if phase=='qualify':
            invocation,_=held.json(base/'invocation.json',maximum=MiB,lf=True);require(invocation==dict(command=namespace_command(config,data,'qualify',worker_command),configuration_sha256=expected_sha256),'Qualification namespace invocation differs')
        # Re-census every selected tree (names and strict directory identity), then
        # re-hash all held content and edges, including the original baseline.
        require(forest(held,config,dependency,directories,prep['staged_roots'])==tree,'Staged namespace changed during audit')
        own=held.file(absolute(str(Path(__file__).resolve())),maximum=MiB);held.recheck();held.clock()
        report=dict(CLAIMS,kind='puck-cpu-held-runtime-independent-audit-v1',version=1,status='PASS',phase=phase,evidence_scope='AUTHORED fixture only' if authored else 'ordinary CPU held allocation only',configuration_sha256=expected_sha256,transport_sha256=expected_transport_sha256,auditor_source_sha256=own['sha256'],result_sha256=sha(result_raw),dependencies_sha256=sha(depraw),root_count=4,file_count=sum(len(r['files']) for r in dep['roots']),directory_count=sum(len(d) for d in directories),input_bytes=sum(f['size_bytes'] for r in dep['roots'] for f in r['files']),baseline=summary,observed_status=result['status'],held_four_imports_observed=phase=='qualify',external_returncode=0,supervision_scope='descendants' if phase=='qualify' else 'group',configured_process_limit=3,tracked_process_identities=len(observed.get('tracked_processes',[])),limitations=['RSS and process enforcement are sampled operational observations; preparation has no retained process-count peak.','No numerical, model, renderer, collection, study or release authority is granted.'])
        if config['version']==2:
            report.update(kind='puck-cpu-held-runtime-independent-audit-v2',version=2,allocation_id=2,preparation_configuration_sha256=config['preparation_acceptance']['configuration']['sha256'],preparation_result_sha256=config['preparation_acceptance']['result']['sha256'],historical_source_epoch_sha256=sha(canonical(prepconfig['sources'],False)),current_source_epoch_sha256=sha(canonical(config['sources'],False)))
    finally:held.close()
    require(len(os.listdir('/proc/self/fd'))==before and not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split() and len(os.listdir('/proc/self/task'))==1,'Auditor closure failed')
    if time.monotonic()>=deadline:raise TimeoutError('Independent CPU audit final closure deadline')
    report.update(elapsed_seconds=time.monotonic()-started,closure=dict(fd_count_before=before,fd_count_after=before,active_children=[],active_non_main_threads=[]));return report


def publish(path,value):
    path=Path(absolute(str(path)));parent=os.open(str(path.parent),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);fd=None
    try:
        fd=os.open(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent);raw=canonical(value);require(len(raw)<=MiB,'Audit output ceiling exceeded')
        with os.fdopen(fd,'wb') as stream:fd=None;stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.fsync(parent)
    finally:
        if fd is not None:os.close(fd)
        os.close(parent)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('configuration','sha256','transport','transport-sha256','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();started=time.monotonic();deadline=started+120
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,130)
    try:
        for key,value in (('AS',512*MiB),('NOFILE',40000),('FSIZE',16*MiB),('CORE',0)):
            soft,hard=resource.getrlimit(getattr(resource,'RLIMIT_'+key));chosen=value if hard==resource.RLIM_INFINITY else min(value,hard);resource.setrlimit(getattr(resource,'RLIMIT_'+key),(chosen,chosen))
        try:
            result=audit(args.configuration,args.sha256,args.transport,args.transport_sha256,deadline=deadline);code=0
        except Exception as error:
            result=dict(CLAIMS,kind='puck-cpu-held-runtime-independent-audit-v1',version=1,status='FAIL',auditor_source_sha256=sha(Path(__file__).read_bytes()),configuration_sha256=args.sha256,transport_sha256=args.transport_sha256,error_type=type(error).__name__,error=str(error)[:2048],elapsed_seconds=time.monotonic()-started);code=1
        publish(args.output,result)
        if time.monotonic()>=deadline:raise TimeoutError('Audit publication exceeded normal deadline')
        print(canonical(result).decode(),end='',flush=True)
        if time.monotonic()>=deadline:raise TimeoutError('Audit terminal flush exceeded normal deadline')
        return code
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
