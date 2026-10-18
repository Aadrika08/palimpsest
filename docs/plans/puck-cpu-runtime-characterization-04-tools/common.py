"""Shared fail-closed helpers for the one-shot characterization-04 tools.

Importing this module runs nothing. Every path is fixed; every write is exclusive.
Helpers that inspect outputs take the project root so offline proofs can run them
on an authored project; the one-shot tools always pass the real ROOT.
"""
from pathlib import Path
import hashlib,json,os,stat,subprocess,time,types

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
BRANCH='research/puck-cpu-characterization-04'
TOOLS='docs/plans/puck-cpu-runtime-characterization-04-tools'
CONFIG='docs/plans/puck-cpu-runtime-characterization-04.json'
FREEZE='docs/plans/puck-cpu-runtime-characterization-04-freeze.json'
OUTPUT='runs/puck-cpu-runtime-characterization-04'
TRANSPORT=OUTPUT+'-external-cli-transport.json'
PARENT_STREAMS=(OUTPUT+'-external-cli.stdout',OUTPUT+'-external-cli.stderr')
PARENT='scripts/characterize_puck_cpu_episode.py'
OBSERVER='scripts/observe_puck_cpu_episode_characterization.py'
AUDITOR='scripts/audit_puck_cpu_episode_characterization.py'
ARCHIVER='scripts/archive_puck_episode_characterization.py'
QUALIFIER='scripts/qualify_puck_cpu_held_runtime.py'
AUDITOR_SHA='1608a3d79a2ebb10723023b25c054401bbd598b2e95508422b1e6bfaa2efac46'
UPSTREAM='8d964599119b420de67ee259434d273651a1a76d'
AUDIT_STEM='/tmp/palimpsest-puck-cpu-characterization-04-audit-01'
AUDIT_OUTPUT=AUDIT_STEM+'.json'
AUDIT_STDOUT=AUDIT_STEM+'.stdout'
AUDIT_STDERR=AUDIT_STEM+'.stderr'
AUDIT_RECORD=AUDIT_STEM+'.external-cli.json'
OBSERVER_STDOUT='/tmp/palimpsest-char04-observer.stdout'
OBSERVER_STDERR='/tmp/palimpsest-char04-observer.stderr'
OBSERVER_TERMINAL='/tmp/palimpsest-char04-observer-terminal.json'
AUDIT_TERMINAL='/tmp/palimpsest-char04-audit-terminal.json'
ARCHIVE_STDOUT='/tmp/palimpsest-char04-archive.stdout'
ARCHIVE_STDERR='/tmp/palimpsest-char04-archive.stderr'
ARCHIVE_TERMINAL='/tmp/palimpsest-char04-archive-terminal.json'
# Project-disk copies live in a gitignored, non-reserved directory so the worktree stays clean.
RECORDS='runs/palimpsest-char04-tools'
# The source archive tool owns ARCHIVE exactly; these controls' records go to a sibling directory.
ARCHIVE='docs/reports/puck-cpu-characterization-04'
RECORDS_ARCHIVE='docs/reports/puck-cpu-characterization-04-records'
# Derived later from this archive; it must not exist before characterization-04.
CANDIDATE='docs/plans/puck-cpu-episode-import-profile-candidate-02.json'
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
# Preparation02/03 evidence that must stay untouched: lstat identity only, never listed, opened or written.
UNTOUCHED=('/tmp/palimpsest-puck-cpu-held-02','/tmp/palimpsest-puck-cpu-held-03',
    'runs/puck-cpu-held-preparation-02','runs/puck-cpu-held-preparation-03')
# Outer bounds only for a wedged child: the observer's own alarm is 435 s, the auditor's 310 s.
OBSERVER_BOUND=460
AUDIT_BOUND=330
ARCHIVE_BOUND=120
ENVIRONMENT=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
RECORD_KEYS={'kind','command','observed_returncode','elapsed_seconds','published','stdout','stderr'}
FALSE=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,executable=False)
REPORTS=('source','replay')


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
    exec(compile(read(path,4*1024**2),str(path),'exec'),value.__dict__);return value


def untouched(root=ROOT):
    """lstat identity of the preparation02/03 stages and outputs; contents are never read."""
    rows=[]
    for name in UNTOUCHED:
        path=Path(name) if name.startswith('/') else Path(root)/name
        try:state=os.lstat(path)
        except FileNotFoundError:rows.append(dict(path=str(path),exists=False));continue
        rows.append(dict(path=str(path),exists=True,directory=stat.S_ISDIR(state.st_mode),device=state.st_dev,inode=state.st_ino,
            mode=state.st_mode,mtime_ns=state.st_mtime_ns,ctime_ns=state.st_ctime_ns))
    return rows


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
    root=Path(root)
    return [python,'-I','-S','-B',str(root/OBSERVER),'--configuration',str(root/CONFIG),'--sha256',config_sha]


def audit_command(root,config_sha,transport_sha,output,python=PYTHON):
    root=Path(root)
    return [python,'-I','-S','-B',str(root/AUDITOR),'--configuration',str(root/CONFIG),'--sha256',config_sha,
        '--transport',str(root/TRANSPORT),'--transport-sha256',transport_sha,'--output',str(output)]


def archive_command(root,audit_output,python=PYTHON):
    root=Path(root)
    return [python,'-I','-S','-B',str(root/ARCHIVER),'--configuration',str(root/CONFIG),'--audit',str(audit_output)]


def observed(root,config_raw,python=PYTHON):
    """The single normal observation: transport, parent stdout, result and both reports, bound by hash."""
    root=Path(root);config_sha=sha(config_raw)
    transport_raw=read(root/TRANSPORT,64*1024);transport=json.loads(transport_raw)
    require(type(transport) is dict and transport.get('kind')=='puck-cpu-episode-characterization-cli-transport-v1'
        and transport.get('configuration_sha256')==config_sha and transport.get('observed_returncode')==0
        and transport.get('timed_out') is False and type(transport.get('elapsed_seconds')) is float and 0<transport['elapsed_seconds']<420
        and transport.get('command')==[python,'-I','-S','-B',str(root/PARENT),'--configuration',str(root/CONFIG),'--sha256',config_sha],
        'Normal characterization-04 transport required')
    streams={}
    for name,path in zip(('stdout','stderr'),PARENT_STREAMS):
        raw=read(root/path);streams[name]=raw
        require(transport.get(name)==dict(path=path,size_bytes=len(raw),sha256=sha(raw)),'Parent '+name+' differs from its transport pin')
    result_raw=read(root/OUTPUT/'result.json',1024**2);result=json.loads(result_raw)
    require(json.loads(streams['stdout'])==result,'Parent stdout differs from result.json')
    reports={phase:read(root/OUTPUT/('payload-'+phase)/'characterization.json',4*1024**2) for phase in REPORTS}
    require(result.get('kind')=='puck-cpu-characterization-outcome-v3' and result.get('version')==3 and result.get('status')=='observed'
        and not {'error','error_type'}&set(result) and result.get('configuration_sha256')==config_sha
        and result.get('source_report_sha256')==sha(reports['source']) and result.get('replay_report_sha256')==sha(reports['replay'])
        and result.get('process_creation_attempts')==0 and all(result.get(k) is False for k in FALSE)
        and result.get('qualification_claims')==[],'Observed characterization-04 result required')
    return dict(transport_sha256=sha(transport_raw),result_sha256=sha(result_raw),source_report_sha256=sha(reports['source']),
        replay_report_sha256=sha(reports['replay']),elapsed_seconds=transport['elapsed_seconds'],ticks_completed=result.get('ticks_completed'),
        replay=result.get('replay'),import_misses={p:json.loads(r).get('import_misses') for p,r in reports.items()})


def build_record(command,returncode,elapsed,published,stdout,stderr):
    """The externally-observed-cpu-auditor-cli-v1 record in exactly preparation01's shape and bytes format."""
    require(type(command) is list and len(command)==15 and all(type(v) is str for v in command),'Bare 15-element auditor argv required')
    require(command[-2:]==['--output',str(published)] and command[0]==PYTHON and command[1:4]==['-I','-S','-B'],'Auditor argv/output differs')
    require(type(returncode) is int and returncode==0,'Normal zero auditor return required')
    require(type(elapsed) is float and 0<elapsed<AUDIT_BOUND,'External auditor elapsed must be below '+str(AUDIT_BOUND)+'s')
    published_raw,published_pin=channel(published);stdout_raw,stdout_pin=channel(stdout);stderr_raw,stderr_pin=channel(stderr)
    require(published_raw==stdout_raw and len(published_raw)>0,'Auditor stdout must equal published bytes')
    require(stderr_raw==b'','Auditor stderr must be empty')
    value=dict(kind='externally-observed-cpu-auditor-cli-v1',command=list(command),observed_returncode=returncode,
        elapsed_seconds=elapsed,published=published_pin,stdout=stdout_pin,stderr=stderr_pin)
    require(set(value)==RECORD_KEYS,'Record keys differ from preparation01')
    return value,pretty(value)


def check_audit(audit,*,observation,config_sha,auditor_sha=AUDITOR_SHA):
    """The PASS shape the archive tool, the derivation and preparation04 accept."""
    verified=audit.get('verified') if type(audit.get('verified')) is dict else {}
    require(audit.get('kind')=='cpu-episode-characterization-outcome-audit-v1' and audit.get('version')==1
        and audit.get('status')=='PASS' and not {'error','error_type'}&set(audit)
        and audit.get('auditor_source_sha256')==auditor_sha and audit.get('target_code_executed_by_auditor') is False
        and audit.get('configuration_sha256')==config_sha and audit.get('transport_sha256')==observation['transport_sha256']
        and all(audit.get(k) is False for k in FALSE)
        and type(audit.get('elapsed_seconds')) is float and 0<audit['elapsed_seconds']<300
        and verified.get('configuration_sha256')==config_sha and verified.get('result_sha256')==observation['result_sha256']
        and verified.get('source_report_sha256')==observation['source_report_sha256']
        and verified.get('replay_report_sha256')==observation['replay_report_sha256']
        and verified.get('transport_sha256')==observation['transport_sha256'],'Characterization-04 audit is not the accepted PASS shape')


def check_archive(root,config_raw,audit_raw,receipt_raw):
    """The source archive's evidence index binds exactly the archived bytes preparation04 pins."""
    root=Path(root);archive=root/ARCHIVE;index_raw=read(archive/'evidence-index.json',4*1024**2);index=json.loads(index_raw)
    receipt=json.loads(receipt_raw)
    require(receipt==dict(path=str(archive/'evidence-index.json'),size_bytes=len(index_raw),sha256=sha(index_raw),
        file_count=index.get('file_count')),'Archive receipt differs from the written evidence index')
    entries=index.get('entries')
    require(index.get('kind')=='cpu-episode-characterization-evidence-index-v1' and index.get('version')==1
        and index.get('original_output')==OUTPUT and type(entries) is list and 1<=len(entries)<=512
        and index.get('file_count')==len(entries)==len({r['path'] for r in entries}),'Characterization-04 evidence index schema differs')
    require(not any(p.is_symlink() for p in archive.rglob('*')),'Archive symlink found')
    on_disk=sorted(p.relative_to(archive).as_posix() for p in archive.rglob('*') if p.is_file() and p!=archive/'evidence-index.json')
    require(sorted(r['path'] for r in entries)==on_disk,'Archive members differ from the evidence index')
    for row in entries:
        raw=read(archive/row['path'],16*1024**2);require(row==dict(path=row['path'],size_bytes=len(raw),sha256=sha(raw)),'Archived bytes differ: '+row['path'])
    run=root/OUTPUT;same={'frozen-configuration.json':config_raw,'outcome-audit-04.json':audit_raw,'raw/result.json':read(run/'result.json',1024**2),
        'external/'+Path(TRANSPORT).name:read(root/TRANSPORT,64*1024)}
    for phase in REPORTS:same['raw/payload/'+phase+'/characterization.json']=read(run/('payload-'+phase)/'characterization.json',4*1024**2)
    for path,raw in same.items():require(read(archive/path,16*1024**2)==raw,'Archived copy differs from its source: '+path)
    return dict(path=ARCHIVE+'/evidence-index.json',size_bytes=len(index_raw),sha256=sha(index_raw),file_count=len(entries))


def binding(root,qualifier,parent,config_raw,candidate=None):
    """Preparation04's pure acceptance of the archive: validate_observation_links and validate_episode_observation.

    Without a derived candidate, a synthetic candidate bound to these pins stands in; the
    qualifier then still refuses any characterized import miss its episode rosters do not declare.
    """
    root=Path(root);frozen=json.loads(config_raw);rows={r['path']:r for r in frozen['inputs']}
    roles=('inventory','layout','native','baseline','accepted_result','accepted_snapshot','accepted_audit','accepted_configuration','accepted_index')
    pins={role:dict(rows[parent.ROLES['native_metadata' if role=='native' else role]]) for role in roles}
    def pin(path):raw=read(root/path,16*1024**2);return dict(path=path,size_bytes=len(raw),sha256=sha(raw))
    pins.update({role:pin(ARCHIVE+'/'+path) for role,path in qualifier.EPISODE_OBSERVATION_PATHS.items()},
        observation_index=pin(ARCHIVE+'/evidence-index.json'))
    blobs={role:read(root/row['path'],32*1024**2) for role,row in pins.items()}
    require([r['path'] for r in frozen['sources']]==list(qualifier.PREPARATION04_SOURCES),'Characterization-04 sources differ from PREPARATION04_SOURCES')
    config=dict(version=15,inputs=pins,sources=frozen['sources'])
    qualifier.validate_observation_links(config,blobs)
    reports=[json.loads(blobs[r]) for r in ('observation_report','observation_replay_report')]
    misses=sorted({n for r in reports for n in r.get('import_misses',[]) if type(n) is str and n.split('.')[0] not in qualifier.STDLIB_311})
    synthetic=candidate is None
    if synthetic:
        candidate=dict(kind='puck-cpu-episode-import-profile-candidate-v2',version=2,expected_versions=dict(qualifier.EPISODE_VERSIONS),
            characterization_configuration_sha256=pins['observation_configuration']['sha256'],
            observation_reports=dict(source=pins['observation_report']['sha256'],replay=pins['observation_replay_report']['sha256']),
            observation_result_sha256=pins['observation_result']['sha256'],outcome_audit_sha256=pins['observation_audit']['sha256'],
            retained_inventory_sha256=pins['inventory']['sha256'],native_metadata_sha256=pins['native']['sha256'],import_misses=misses)
    qualifier.validate_episode_observation(config,dict(blobs,candidate=pretty(candidate)))
    return dict(validate_observation_links='PASS',validate_episode_observation='PASS',candidate='synthetic' if synthetic else 'derived',
        import_misses=len(misses),undeclared_import_misses=0,pins={k:pins[k] for k in sorted(pins) if k.startswith('observation_')})
