"""Fail-closed preflight for one characterization-04 step: observer, audit or archive.

Reads only. Standalone use writes one exclusive record unless --dry-run is given;
--dry-run (offline proof only) reports, instead of enforcing, a missing push or unmet floors.
Usage: python3.11 -I -S -B preflight.py observer|audit|archive [--dry-run]
"""
from pathlib import Path
import datetime,importlib.util,json,os,resource,shutil,subprocess,sys,time

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('char04_common',HERE/'common.py')
C=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(C)
require=C.require
PHASES=('observer','audit','archive')


def read_ok(name):return C.read(C.ROOT/name,16*1024**2)


def git_state(dry_run):
    status=C.git('status','--porcelain','--ignore-submodules=none');head=C.git('rev-parse','HEAD').decode().strip()
    try:origin=C.git('rev-parse','origin/'+C.BRANCH).decode().strip()
    except subprocess.CalledProcessError:origin=None
    branch=C.git('rev-parse','--abbrev-ref','HEAD').decode().strip()
    controls=[C.CONFIG,C.FREEZE]+C.git('ls-files','--',C.TOOLS).decode().splitlines()
    require(all(read_ok(name)==C.git('show','HEAD:'+name) for name in controls),'Controls differ from HEAD')
    require(str(HERE)==str(C.ROOT/C.TOOLS) and all((HERE/n).read_bytes()==C.git('show','HEAD:'+C.TOOLS+'/'+n) for n in ('common.py','preflight.py')),
        'Running tools are not the Git-bound copies')
    # The fly-gym submodule must sit at the episode's upstream commit with no local change.
    fly=C.ROOT/'upstream/fly-gym'
    upstream=dict(head=C.git('rev-parse','HEAD',root=fly).decode().strip(),gitlink=C.git('ls-files','-s','upstream/fly-gym').decode().split()[1],
        clean=C.git('status','--porcelain','--untracked-files=all',root=fly)==b'')
    require(upstream['head']==upstream['gitlink']==C.UPSTREAM and upstream['clean'],'fly-gym submodule differs from '+C.UPSTREAM)
    state=dict(head=head,origin=origin,branch=branch,clean=status==b'',controls_git_bound=len(controls),upstream=upstream)
    if not dry_run:require(status==b'' and origin==head and branch==C.BRANCH,'Clean worktree on '+C.BRANCH+' with origin == HEAD required')
    return state


def controls():
    parent=C.load(C.ROOT/C.PARENT,'char04_preflight_parent');auditor=C.load(C.ROOT/C.AUDITOR,'char04_preflight_auditor')
    qualifier=C.load(C.ROOT/C.QUALIFIER,'char04_preflight_qualifier')
    freeze=json.loads(read_ok(C.FREEZE));raw=read_ok(C.CONFIG);config=json.loads(raw)
    # The parent's own builder over current sources must reproduce the frozen pretty bytes exactly.
    rebuilt=(json.dumps(parent.configuration(parent.source_rows()),sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    require(rebuilt==raw,'Frozen configuration differs from the parent builder over current sources')
    parent.validate_configuration(config);capsule=auditor.validate_configuration(config)
    require(config['output']==C.OUTPUT and [r['path'] for r in config['sources']]==list(qualifier.PREPARATION04_SOURCES),'Characterization-04 identity differs')
    pins=freeze['pins'];sha=C.sha(raw)
    require(pins['configuration']==dict(path=C.CONFIG,size_bytes=len(raw),sha256=sha) and pins['sources']==config['sources']
        and pins['inputs']==config['inputs'],'Freeze/config pins differ')
    require(pins['auditor']['sha256']==C.AUDITOR_SHA==qualifier.CHARACTERIZATION04_AUDITOR_SHA256,'Auditor pin differs from the preparation04 pin')
    checked=0
    for key in ('configuration','parent','worker','observer','auditor','archive','derivation','qualifier','held_auditor'):
        row=pins[key];data=read_ok(row['path'])
        require(len(data)==row['size_bytes'] and C.sha(data)==row['sha256'],'Control pin differs: '+row['path']);checked+=1
    for row in config['sources']+config['inputs']:
        data=C.read(C.ROOT/row['path'],32*1024**2,single=False)
        require(len(data)==row['size_bytes'] and C.sha(data)==row['sha256'],'Pin differs: '+row['path']);checked+=1
    data=C.read(C.PYTHON,64*1024**2,single=False)
    require(len(data)==pins['interpreter']['size_bytes'] and C.sha(data)==pins['interpreter']['sha256'],'Interpreter pin differs');checked+=1
    require(freeze['command']==C.observer_command(C.ROOT,sha),'Observer command differs')
    require(freeze['audit']['command_prefix']==C.audit_command(C.ROOT,sha,'x',C.AUDIT_OUTPUT)[:11] and freeze['audit']['output']==C.AUDIT_OUTPUT,'Audit command differs')
    require(freeze['archive']['command']==C.archive_command(C.ROOT,C.AUDIT_OUTPUT),'Archive command differs')
    return parent,auditor,freeze,config,raw,dict(pins_checked=checked,capsule_files=len(capsule))


def host(auditor,config):
    """The auditor's own read-only native v6, EGL vendor, baseline and site checks."""
    rows={r['path']:r for r in config['inputs']};reader=auditor.Reader(time.monotonic()+290)
    get=lambda role:json.loads(C.read(C.ROOT/auditor.ROLES[role],32*1024**2))
    for role in ('native_metadata','baseline','inventory','layout'):
        raw=C.read(C.ROOT/auditor.ROLES[role],32*1024**2,single=False);row=rows[auditor.ROLES[role]]
        require(len(raw)==row['size_bytes'] and C.sha(raw)==row['sha256'],'Input pin differs: '+role)
    native=get('native_metadata');natives,vendor=auditor.validate_native(native,reader)
    summary=auditor.baseline_summary(get('baseline'),reader)
    auditor.site_census(get('inventory'),get('layout'),reader)
    reader.recheck()
    return dict(native_files=len(natives),native_aliases=len(native['aliases']),dynamic_leaves=len(native['dynamic_leaves']),
        egl_vendor=dict(path=native['egl_vendor']['path'],size_bytes=len(vendor),sha256=C.sha(vendor)),baseline=summary,
        site_file_count=auditor.SITE_COUNTS[0])


def resources(parent,enforce):
    limits=parent.LIMITS;nofile=resource.getrlimit(resource.RLIMIT_NOFILE)
    mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    value=dict(mem_available_bytes=mem,disk_available_bytes=shutil.disk_usage(C.ROOT).free,nofile=list(nofile),
        bwrap=os.access('/usr/bin/bwrap',os.X_OK))
    # The observer sets NOFILE to 40000/40000 for the parent, so only the hard limit must allow it.
    value['floors_met']=(mem>=limits['min_available_ram_bytes'] and value['disk_available_bytes']>=limits['min_free_bytes']
        and (nofile[1]==resource.RLIM_INFINITY or nofile[1]>=limits['max_fds']) and value['bwrap'])
    if enforce:require(value['floors_met'],'Characterization-04 resource floors not met')
    return value


def absent(paths):
    present=[str(p) for p in paths if os.path.lexists(p)]
    require(not present,'Reserved paths already exist: '+', '.join(present))
    return len(paths)


def records(name):
    return [Path(name),C.ROOT/C.RECORDS/Path(name).name]


def same_record(name):
    first,copy=(C.read(p) for p in records(name));require(first==copy,'Record copies differ: '+name);return json.loads(first)


def stages_unchanged(terminal,now):
    require(terminal.get('untouched_before')==terminal.get('untouched_after')==now,'Preparation02/03 stage or output identity changed')


def check(phase,dry_run=False):
    require(phase in PHASES,'Unknown preflight phase')
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and str(Path(sys.executable).resolve())==C.PYTHON
        and not os.environ.get('LD_PRELOAD') and not os.environ.get('LD_LIBRARY_PATH'),'Pinned isolated interpreter required')
    os.chdir(C.ROOT)
    require(C.boot_id()==C.BOOT,'Boot differs from the required characterization-04 boot '+C.BOOT)
    require(C.ROOT.resolve(strict=True)==C.ROOT and (C.ROOT/C.CONFIG).resolve(strict=True)==C.ROOT/C.CONFIG,'Symlink-free project root required')
    value=dict(kind='palimpsest-char04-preflight-v1',phase=phase,dry_run=dry_run,boot_id=C.boot_id(),
        at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),git=git_state(dry_run))
    parent,auditor,freeze,config,raw,pins=controls();value.update(pins);value['host']=host(auditor,config)
    value['resources']=resources(parent,enforce=phase=='observer' and not dry_run)
    value['untouched']=C.untouched()
    observer_paths=[C.ROOT/C.OUTPUT,C.ROOT/C.TRANSPORT,*[C.ROOT/p for p in C.PARENT_STREAMS],C.OBSERVER_STDOUT,C.OBSERVER_STDERR,*records(C.OBSERVER_TERMINAL)]
    audit_paths=[C.AUDIT_OUTPUT,C.AUDIT_STDOUT,C.AUDIT_STDERR,*records(C.AUDIT_RECORD),*records(C.AUDIT_TERMINAL)]
    archive_paths=[C.ROOT/C.ARCHIVE,C.ROOT/C.RECORDS_ARCHIVE,C.ARCHIVE_STDOUT,C.ARCHIVE_STDERR,*records(C.ARCHIVE_TERMINAL),C.ROOT/C.CANDIDATE]
    if phase=='observer':value['absent']=absent(observer_paths+audit_paths+archive_paths)
    else:
        terminal=same_record(C.OBSERVER_TERMINAL)
        require(terminal.get('status')=='PASS_OBSERVED' and terminal.get('boot_id_before')==terminal.get('boot_id_after')==value['boot_id'],
            'Observer terminal/boot differs')
        stages_unchanged(terminal,value['untouched'])
        value['observed']=C.observed(C.ROOT,raw)
        require(terminal['observation']==value['observed'],'Observation changed since the observer')
        if phase=='audit':value['absent']=absent(audit_paths+archive_paths)
        else:
            audit=same_record(C.AUDIT_TERMINAL)
            require(audit.get('status')=='PASS_RECORD_WRITTEN' and audit.get('boot_id_before')==audit.get('boot_id_after')==value['boot_id'],'Audit terminal differs')
            stages_unchanged(audit,value['untouched'])
            record=C.read(C.AUDIT_RECORD);require(record==C.read(C.ROOT/C.RECORDS/Path(C.AUDIT_RECORD).name) and C.sha(record)==audit['record']['sha256'],
                'Audit record differs from its terminal')
            audit_raw=C.read(C.AUDIT_OUTPUT);require(C.sha(audit_raw)==audit['audit']['sha256'],'Audit output changed')
            C.check_audit(json.loads(audit_raw),observation=value['observed'],config_sha=C.sha(raw))
            value['absent']=absent(archive_paths)
    value['status']='PASS_PREFLIGHT_'+phase.upper()
    return value


def main():
    args=sys.argv[1:];dry_run='--dry-run' in args;args=[a for a in args if a!='--dry-run']
    require(len(args)==1,__doc__);value=check(args[0],dry_run)
    raw=C.pretty(value)
    if not dry_run:
        copies=C.ROOT/C.RECORDS;copies.mkdir(mode=0o700,exist_ok=True)
        C.write_new(copies/('preflight-'+args[0]+'-'+value['at_utc'].replace(':','')+'.json'),raw)
    print(raw.decode(),end='')
    return 0


if __name__=='__main__':raise SystemExit(main())
