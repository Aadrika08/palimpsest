"""Shared fail-closed helpers for the one-shot preparation03 tools.

Importing this module runs nothing. Every path is fixed; every write is exclusive.
"""
from pathlib import Path
import copy,hashlib,json,os,stat,subprocess,time,types

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
BRANCH='research/puck-cpu-held-preparation-03'
TOOLS='docs/plans/puck-cpu-held-preparation-03-tools'
CONFIG='docs/plans/puck-cpu-held-preparation-03.json'
FREEZE='docs/plans/puck-cpu-held-preparation-03-freeze.json'
OUTPUT='runs/puck-cpu-held-preparation-03'
TRANSPORT=OUTPUT+'-external-cli-transport.json'
PARENT_STREAMS=(OUTPUT+'-external-cli.stdout',OUTPUT+'-external-cli.stderr')
STAGE='/tmp/palimpsest-puck-cpu-held-03'
AUDIT_STEM='/tmp/palimpsest-puck-cpu-held-preparation-03-audit-01'
AUDIT_OUTPUT=AUDIT_STEM+'.json'
AUDIT_STDOUT=AUDIT_STEM+'.stdout'
AUDIT_STDERR=AUDIT_STEM+'.stderr'
AUDIT_RECORD=AUDIT_STEM+'.external-cli.json'
OBSERVER_STDOUT='/tmp/palimpsest-prep03-observer.stdout'
OBSERVER_STDERR='/tmp/palimpsest-prep03-observer.stderr'
OBSERVER_TERMINAL='/tmp/palimpsest-prep03-observer-terminal.json'
AUDIT_TERMINAL='/tmp/palimpsest-prep03-audit-terminal.json'
# Project-disk copies live in a gitignored, non-reserved directory so the worktree stays clean.
RECORDS='runs/palimpsest-prep03-tools'
ARCHIVE='docs/reports/puck-cpu-held-preparation-03'
ARCHIVED_AUDIT=ARCHIVE+'/audit/palimpsest-puck-cpu-held-preparation-03-audit-01.json'
ARCHIVED_RECORD=ARCHIVE+'/audit/palimpsest-puck-cpu-held-preparation-03-audit-01.external-cli.json'
# Qualification14 consumes preparation03 with publication candidate D.
CANDIDATE_D_SOURCE='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json'
# Preparation03 runs on the boot that still holds preparation02's untouched stage.
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
ENVIRONMENT=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
RECORD_KEYS={'kind','command','observed_returncode','elapsed_seconds','published','stdout','stderr'}
CLAIMS=dict(collection_authorized=False,executable=False,native_authorized=False,qualification_claims=[],
    runtime_qualified=False,study_authorized=False)


def require(value,message):
    if not value:raise RuntimeError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def pretty(value):return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()


def read(path,maximum=16*1024**2,*,single=True,empty=True):
    """Bounded nofollow stable read of one regular file."""
    fd=os.open(str(path),os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and (not single or before.st_nlink==1) and before.st_size<=maximum
            and (empty or before.st_size>0),'Bounded regular file required: '+str(path))
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(maximum+1)
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        require(len(raw)==before.st_size and stamp(before)==stamp(os.fstat(fd))==stamp(os.stat(str(path),follow_symlinks=False)),
            'File changed while read: '+str(path))
        return raw
    finally:os.close(fd)


def channel(path):
    raw=read(path);return raw,dict(path=str(path),size_bytes=len(raw),sha256=sha(raw))


def write_new(path,raw):
    path=Path(path);fd=os.open(str(path),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
    with os.fdopen(fd,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    require(read(path)==raw,'Exclusive write did not persist: '+str(path))


def write_record(name,raw,root=ROOT):
    """Write one /tmp record and its project-disk copy, both exclusively."""
    write_new(name,raw)
    copies=Path(root)/RECORDS;copies.mkdir(mode=0o700,exist_ok=True)
    write_new(copies/Path(name).name,raw)


def boot_id():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def git(*args,root=ROOT):return subprocess.check_output(['git','-C',str(root),*args],timeout=30)


def load(path,name):
    path=Path(path);value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(read(path,1024**2),str(path),'exec'),value.__dict__);return value


def stat_roots(stage,rows):
    """Prove the stage parent and four staged roots are the identities preparation03 published."""
    require(type(rows) is list and [r.get('root_index') for r in rows]==[0,1,2,3],'Four ordered staged roots required')
    parent=os.lstat(stage);require(stat.S_ISDIR(parent.st_mode),'Stage parent directory required')
    observed=[]
    for row in rows:
        state=os.lstat(Path(stage)/'inputs'/('root-'+str(row['root_index']).zfill(4)))
        match=stat.S_ISDIR(state.st_mode) and (state.st_dev,state.st_ino)==(row['device'],row['inode'])
        observed.append(dict(root_index=row['root_index'],device=state.st_dev,inode=state.st_ino,matches=match))
    require(all(r['matches'] for r in observed),'Staged root identity differs from result.staged_roots')
    return dict(stage_parent=str(stage),stage_parent_device=parent.st_dev,stage_parent_inode=parent.st_ino,roots=observed)


def run_once(command,stdout_path,stderr_path,*,timeout,cwd=ROOT,env=ENVIRONMENT):
    """Run one exact argv with exclusive stream files; no retry, no shell, no wrapper."""
    terminal=dict(command=list(command),cwd=str(cwd),environment=dict(env))
    with open(stdout_path,'xb') as stdout,open(stderr_path,'xb') as stderr:
        started=time.monotonic()
        try:
            process=subprocess.run(command,cwd=cwd,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=timeout)
            terminal.update(returncode=process.returncode,outer_timeout=False)
        except subprocess.TimeoutExpired:terminal.update(returncode=None,outer_timeout=True)
        terminal['elapsed_seconds']=time.monotonic()-started
        stdout.flush();os.fsync(stdout.fileno());stderr.flush();os.fsync(stderr.fileno())
    for name,path in (('stdout',stdout_path),('stderr',stderr_path)):
        raw=read(path);terminal[name]=dict(path=str(path),size_bytes=len(raw),sha256=sha(raw))
    return terminal


def audit_command(root,config_sha,transport_sha,output,python=PYTHON):
    root=Path(root)
    return [python,'-I','-S','-B',str(root/'scripts/audit_puck_cpu_held_runtime.py'),'--configuration',str(root/CONFIG),
        '--sha256',config_sha,'--transport',str(root/TRANSPORT),'--transport-sha256',transport_sha,'--output',str(output)]


def build_record(command,returncode,elapsed,published,stdout,stderr):
    """The externally-observed-cpu-auditor-cli-v1 record in exactly preparation01's shape and bytes format."""
    require(type(command) is list and len(command)==15 and all(type(v) is str for v in command),'Bare 15-element auditor argv required')
    require(command[-2:]==['--output',str(published)] and command[0]==PYTHON and command[1:4]==['-I','-S','-B'],'Auditor argv/output differs')
    require(type(returncode) is int and returncode==0,'Normal zero auditor return required')
    require(type(elapsed) is float and 0<elapsed<130,'External auditor elapsed must be below 130s')
    published_raw,published_pin=channel(published);stdout_raw,stdout_pin=channel(stdout);stderr_raw,stderr_pin=channel(stderr)
    require(published_raw==stdout_raw and len(published_raw)>0,'Auditor stdout must equal published bytes')
    require(stderr_raw==b'','Auditor stderr must be empty')
    value=dict(kind='externally-observed-cpu-auditor-cli-v1',command=list(command),observed_returncode=returncode,
        elapsed_seconds=elapsed,published=published_pin,stdout=stdout_pin,stderr=stderr_pin)
    require(set(value)==RECORD_KEYS,'Record keys differ from preparation01')
    return value,pretty(value)


def check_audit(audit,*,config_sha,transport_sha,result_sha,auditor_sha):
    require(audit.get('kind')=='puck-cpu-held-runtime-independent-audit-v13' and audit.get('version')==13
        and audit.get('allocation_id')==13 and audit.get('status')=='PASS' and audit.get('phase')=='prepare'
        and audit.get('observed_status')=='prepared' and audit.get('held_four_imports_observed') is False
        and audit.get('evidence_scope')=='ordinary CPU held allocation only' and audit.get('external_returncode')==0
        and audit.get('auditor_source_sha256')==auditor_sha and audit.get('configuration_sha256')==config_sha
        and audit.get('transport_sha256')==transport_sha and audit.get('result_sha256')==result_sha
        and audit.get('root_count')==4 and not {'error','error_type'}&set(audit)
        and type(audit.get('elapsed_seconds')) is float and 0<audit['elapsed_seconds']<120
        and audit.get('closure')==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
        and all(audit.get(k)==v and type(audit.get(k)) is type(v) for k,v in CLAIMS.items()),'Preparation03 audit is not the accepted PASS shape')


def epoch14(prep03,acceptance,candidate,parent):
    """A synthetic extended-clock qualification14 configuration that consumes preparation03 exactly as epoch 14 will."""
    config=copy.deepcopy(prep03)
    config.update(kind='puck-cpu-held-runtime-allocation-v14',version=14,allocation_id=14,phase='qualify',
        limits=copy.deepcopy(parent.QUALIFY14_LIMITS),negative_imports=list(parent.QUALIFY11_NEGATIVE_IMPORTS),
        preparation_acceptance=copy.deepcopy(acceptance))
    config['inputs']=dict(copy.deepcopy(prep03['inputs']),candidate=copy.deepcopy(candidate))
    return config


def prove_parent(parent,auditor,prep03_raw,result_raw,audit_raw,record_raw,acceptance_paths,candidate):
    """Pure in-memory epoch-14 acceptance through the parent and the auditor's pure validators."""
    blobs=dict(configuration=prep03_raw,result=result_raw,independent_audit=audit_raw,externally_observed_auditor_cli=record_raw)
    acceptance={role:dict(path=acceptance_paths[role],size_bytes=len(raw),sha256=sha(raw)) for role,raw in blobs.items()}
    prep03=parent.decode(prep03_raw);config=epoch14(prep03,acceptance,candidate,parent)
    prior,prep=parent.validate_preparation_acceptance(config,blobs)
    auditor.configuration(config,False);auditor.preparation_epoch(config,prior,prep)
    require(config['limits']==parent.QUALIFY14_LIMITS and config['limits']['normal_seconds']==360 and len(config['negative_imports'])==32,'Epoch-14 clock/roster differs')
    require(parent.QUALIFY11_HIDDEN_IMPORTS==['networkx','pandas','sklearn','torch.utils._cxx_pytree'],'Epoch-14 hidden roster differs')
    return config,dict(parent_validate_preparation_acceptance='PASS',auditor_configuration='PASS',auditor_preparation_epoch='PASS',
        epoch=14,normal_seconds=360,negative_imports=32,hidden_imports=list(parent.QUALIFY11_HIDDEN_IMPORTS))


def prove_worker(parent,config,depraw):
    """Epoch-14 worker registration: policy v5, the hidden roster and the exact 360 s worker clock."""
    files=[row for row in config['sources'] if row['path'] in parent.WORKER_SOURCES]
    worker,_=parent.worker_registration(files,depraw,negative_imports=config['negative_imports'],qualification_version=5,
        hidden_imports=parent.QUALIFY11_HIDDEN_IMPORTS,deadline_seconds=parent.QUALIFY14_WORKER_SECONDS)
    require(worker['deadline_seconds']==360 and worker['qualification']['hidden_imports']==parent.QUALIFY11_HIDDEN_IMPORTS
        and worker['qualification']['version']==5,'Epoch-14 worker registration differs')
    return dict(worker_registration='PASS',worker_deadline_seconds=360)


def prove_auditor_files(auditor,config,deadline_seconds=60):
    """The auditor's historical_acceptance reads every acceptance pin from disk below config['root']."""
    held=auditor.Held(time.monotonic()+deadline_seconds)
    try:auditor.historical_acceptance(held,config,False)
    finally:held.close()
    return dict(auditor_historical_acceptance='PASS')
