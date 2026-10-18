"""Shared fail-closed helpers for the one-shot preparation04 tools.

Importing this module runs nothing. Every path is fixed; every write is exclusive.
Derived from the accepted preparation03 tools; helpers that inspect outputs take the
project root so offline proofs can run them on a fixture root.
"""
from pathlib import Path
import hashlib,json,os,stat,subprocess,time,types

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
BRANCH='research/puck-cpu-held-preparation-04'
TOOLS='docs/plans/puck-cpu-held-preparation-04-tools'
CONFIG='docs/plans/puck-cpu-held-preparation-04.json'
FREEZE='docs/plans/puck-cpu-held-preparation-04-freeze.json'
OUTPUT='runs/puck-cpu-held-preparation-04'
TRANSPORT=OUTPUT+'-external-cli-transport.json'
PARENT_STREAMS=(OUTPUT+'-external-cli.stdout',OUTPUT+'-external-cli.stderr')
QUALIFIER='scripts/qualify_puck_cpu_held_runtime.py'
OBSERVER='scripts/observe_puck_cpu_held_allocation.py'
AUDITOR='scripts/audit_puck_cpu_held_runtime.py'
EPISODE_PARENT='scripts/run_puck_cpu_held_episode.py'
EPISODE_AUDITOR='scripts/audit_puck_cpu_held_episode.py'
AUDITOR_SHA='4ef23799994785c2154aeedd83a03e0457cdfd7f9e4573d12d44e462fb782f7c'
UPSTREAM='8d964599119b420de67ee259434d273651a1a76d'
STAGE='/tmp/palimpsest-puck-cpu-held-04'
AUDIT_STEM='/tmp/palimpsest-puck-cpu-held-preparation-04-audit-01'
AUDIT_OUTPUT=AUDIT_STEM+'.json'
AUDIT_STDOUT=AUDIT_STEM+'.stdout'
AUDIT_STDERR=AUDIT_STEM+'.stderr'
AUDIT_RECORD=AUDIT_STEM+'.external-cli.json'
OBSERVER_STDOUT='/tmp/palimpsest-prep04-observer.stdout'
OBSERVER_STDERR='/tmp/palimpsest-prep04-observer.stderr'
OBSERVER_TERMINAL='/tmp/palimpsest-prep04-observer-terminal.json'
AUDIT_TERMINAL='/tmp/palimpsest-prep04-audit-terminal.json'
# Project-disk copies live in a gitignored, non-reserved directory so the worktree stays clean.
RECORDS='runs/palimpsest-prep04-tools'
ARCHIVE='docs/reports/puck-cpu-held-preparation-04'
ARCHIVED_AUDIT=ARCHIVE+'/audit/palimpsest-puck-cpu-held-preparation-04-audit-01.json'
ARCHIVED_RECORD=ARCHIVE+'/audit/palimpsest-puck-cpu-held-preparation-04-audit-01.external-cli.json'
# Preparation04 runs on the boot that held the consumed preparation02/03 stages.
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
# Consumed stages: retired only by retire-consumed-stages.py; never listed, opened or written by any other tool.
CONSUMED=('/tmp/palimpsest-puck-cpu-held-02','/tmp/palimpsest-puck-cpu-held-03')
CONSUMED_OUTPUTS=('runs/puck-cpu-held-preparation-02','runs/puck-cpu-held-preparation-03')
RETIREMENT=RECORDS+'/retire-consumed-stages.json'
# Outer bounds only for a wedged child: the observer's alarm is 225 s, the auditor's 130 s.
OBSERVER_BOUND=260
AUDIT_BOUND=150
RECORD_ELAPSED=130
ENVIRONMENT=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
RECORD_KEYS={'kind','command','observed_returncode','elapsed_seconds','published','stdout','stderr'}
CLAIMS=dict(collection_authorized=False,executable=False,native_authorized=False,qualification_claims=[],
    runtime_qualified=False,study_authorized=False)
# Two fresh 32-hex run ids for the synthetic allocation-16 proof only (never characterization-04's).
PROOF_RUN_IDS=dict(source='0f1e2d3c4b5a69788796a5b4c3d2e1f0',replay='1e2d3c4b5a69788796a5b4c3d2e1f00f')


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
    require(read(path,max(len(raw),16*1024**2))==raw,'Exclusive write did not persist: '+str(path))


def write_record(name,raw,root=ROOT):
    """Write one /tmp record and its project-disk copy, both exclusively."""
    write_new(name,raw)
    copies=Path(root)/RECORDS;copies.mkdir(mode=0o700,exist_ok=True)
    write_new(copies/Path(name).name,raw)


def boot_id():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def git(*args,root=ROOT):return subprocess.check_output(['git','-C',str(root),*args],timeout=30)


def load(path,name):
    path=Path(path);value=types.ModuleType(name);value.__file__=str(path)
    exec(compile(read(path,4*1024**2),str(path),'exec'),value.__dict__);return value


def identity(path):
    try:state=os.lstat(path)
    except FileNotFoundError:return dict(path=str(path),exists=False)
    return dict(path=str(path),exists=True,directory=stat.S_ISDIR(state.st_mode),device=state.st_dev,inode=state.st_ino,
        mode=state.st_mode,mtime_ns=state.st_mtime_ns,ctime_ns=state.st_ctime_ns)


def consumed(root=ROOT,retirement=None):
    """lstat identity of the consumed stages and their outputs; contents are never read.

    A consumed stage may be absent only when the retirement record says that exact path was
    retired (status RETIRED) on this boot; outputs under runs/ must always remain.
    """
    rows=[identity(p) for p in CONSUMED]+[identity(Path(root)/p) for p in CONSUMED_OUTPUTS]
    retired={r['path'] for r in (retirement or {}).get('stages',[]) if r.get('status')=='RETIRED'}
    for row in rows[:2]:
        require(row['exists'] and row['directory'] or (not row['exists'] and row['path'] in retired and (retirement or {}).get('boot_id')==BOOT),
            'Consumed stage must be present or recorded as retired: '+row['path'])
    require(all(r['exists'] and r['directory'] for r in rows[2:]),'Consumed preparation outputs must remain')
    return rows


def stat_roots(stage,rows):
    """Prove the stage parent and four staged roots are the identities preparation04 published."""
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


def observer_command(root,config_sha,python=PYTHON):
    root=Path(root);return [python,'-I','-S','-B',str(root/OBSERVER),'--configuration',str(root/CONFIG),'--sha256',config_sha]


def audit_command(root,config_sha,transport_sha,output,python=PYTHON):
    root=Path(root)
    return [python,'-I','-S','-B',str(root/AUDITOR),'--configuration',str(root/CONFIG),
        '--sha256',config_sha,'--transport',str(root/TRANSPORT),'--transport-sha256',transport_sha,'--output',str(output)]


def build_record(command,returncode,elapsed,published,stdout,stderr):
    """The externally-observed-cpu-auditor-cli-v1 record in exactly preparation01's shape and bytes format."""
    require(type(command) is list and len(command)==15 and all(type(v) is str for v in command),'Bare 15-element auditor argv required')
    require(command[-2:]==['--output',str(published)] and command[0]==PYTHON and command[1:4]==['-I','-S','-B'],'Auditor argv/output differs')
    require(type(returncode) is int and returncode==0,'Normal zero auditor return required')
    require(type(elapsed) is float and 0<elapsed<RECORD_ELAPSED,'External auditor elapsed must be below 130s')
    published_raw,published_pin=channel(published);stdout_raw,stdout_pin=channel(stdout);stderr_raw,stderr_pin=channel(stderr)
    require(published_raw==stdout_raw and len(published_raw)>0,'Auditor stdout must equal published bytes')
    require(stderr_raw==b'','Auditor stderr must be empty')
    value=dict(kind='externally-observed-cpu-auditor-cli-v1',command=list(command),observed_returncode=returncode,
        elapsed_seconds=elapsed,published=published_pin,stdout=stdout_pin,stderr=stderr_pin)
    require(set(value)==RECORD_KEYS,'Record keys differ from preparation01')
    return value,pretty(value)


def check_audit(audit,*,config_sha,transport_sha,result_sha,dependencies_sha,auditor_sha=AUDITOR_SHA):
    require(audit.get('kind')=='puck-cpu-held-runtime-independent-audit-v15' and audit.get('version')==15
        and audit.get('allocation_id')==15 and audit.get('status')=='PASS' and audit.get('phase')=='prepare'
        and audit.get('observed_status')=='prepared' and audit.get('held_four_imports_observed') is False
        and audit.get('evidence_scope')=='ordinary CPU held allocation only' and audit.get('external_returncode')==0
        and audit.get('auditor_source_sha256')==auditor_sha and audit.get('configuration_sha256')==config_sha
        and audit.get('transport_sha256')==transport_sha and audit.get('result_sha256')==result_sha
        and audit.get('dependencies_sha256')==dependencies_sha and audit.get('root_count')==4 and not {'error','error_type'}&set(audit)
        and type(audit.get('elapsed_seconds')) is float and 0<audit['elapsed_seconds']<120
        and audit.get('closure')==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
        and all(audit.get(k)==v and type(audit.get(k)) is type(v) for k,v in CLAIMS.items()),'Preparation04 audit is not the accepted PASS shape')


def allocation16(root,episode,q,prep04,acceptance,run_ids=PROOF_RUN_IDS):
    """A synthetic allocation-16 configuration that binds preparation04 exactly as run_puck_cpu_held_episode.py requires."""
    raw=read(Path(root)/EPISODE_PARENT,4*1024**2)
    sources=sorted(prep04['sources']+[dict(path=EPISODE_PARENT,size_bytes=len(raw),sha256=sha(raw))],key=lambda r:r['path'])
    return dict(kind=episode.KIND,version=16,allocation_id=16,root=str(root),stage_parent=prep04['stage_parent'],sources=sources,
        inputs=prep04['inputs'],interpreter=dict(q.INTERPRETER),environment=dict(episode.ENVIRONMENT),expected_versions=dict(episode.VERSIONS),
        limits=dict(episode.LIMITS),negative_imports=list(episode.NEGATIVE_IMPORTS),hidden_imports=list(episode.HIDDEN_IMPORTS),
        claims=dict(episode.CLAIMS),preparation_acceptance=acceptance,run_ids=dict(run_ids))


def prove_allocation16(root,acceptance_paths,blobs=None):
    """Allocation 16's parent (and, once archived on disk, its episode auditor) accept the preparation04 pins.

    Pure validators only, no run. With in-memory blobs (before the archive exists) only the
    parent's validators run, because the episode auditor reads every pin from disk.
    """
    root=Path(root);q=load(root/QUALIFIER,'prep04_proof_qualifier');episode=load(root/EPISODE_PARENT,'prep04_proof_episode')
    episode_auditor=blobs is None
    if blobs is None:blobs={role:read(root/path,16*1024**2) for role,path in acceptance_paths.items()}
    acceptance={role:dict(path=acceptance_paths[role],size_bytes=len(raw),sha256=sha(raw)) for role,raw in blobs.items()}
    prep04=q.decode(blobs['configuration']);config=allocation16(root,episode,q,prep04,acceptance)
    episode.validate_configuration(config,q);prior,prep=episode.validate_acceptance(config,blobs,q)
    candidate=json.loads(read(root/prep04['inputs']['candidate']['path']));episode.require_declared_misses(candidate)
    proof=dict(episode_validate_configuration='PASS',episode_validate_acceptance='PASS',require_declared_misses='PASS',
        sources=len(config['sources']),stage_parent=config['stage_parent'])
    if episode_auditor:
        auditor=load(root/EPISODE_AUDITOR,'prep04_proof_episode_auditor');auditor.validate_configuration(config,prior)
        reader=auditor.Reader(time.monotonic()+60);auditor.validate_acceptance(config,reader)
        proof.update(episode_auditor_validate_configuration='PASS',episode_auditor_validate_acceptance='PASS')
    return config,proof
