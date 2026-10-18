"""Fail-closed preflight for one preparation03 step: observer, audit or archive.

Reads only. Standalone use writes one exclusive record unless --dry-run is given;
--dry-run (offline proof only) reports, instead of enforcing, a missing push.
Usage: python3.11 -I -S -B preflight.py observer|audit|archive [--dry-run]
"""
from pathlib import Path
import datetime,glob,importlib.util,json,os,resource,shutil,stat,subprocess,sys

HERE=Path(__file__).resolve().parent
_spec=importlib.util.spec_from_file_location('prep03_common',HERE/'common.py')
C=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(C)
require=C.require
PHASES=('observer','audit','archive')


def git_state(dry_run):
    status=C.git('status','--porcelain');head=C.git('rev-parse','HEAD').decode().strip()
    try:origin=C.git('rev-parse','origin/'+C.BRANCH).decode().strip()
    except subprocess.CalledProcessError:origin=None
    controls=[C.CONFIG,C.FREEZE]+C.git('ls-files','--',C.TOOLS).decode().splitlines()
    require(all(read_ok(name)==C.git('show','HEAD:'+name) for name in controls),'Controls differ from HEAD')
    require(str(HERE)==str(C.ROOT/C.TOOLS) and all((HERE/n).read_bytes()==C.git('show','HEAD:'+C.TOOLS+'/'+n) for n in ('common.py','preflight.py')),
        'Running tools are not the Git-bound copies')
    state=dict(head=head,origin=origin,clean=status==b'',controls_git_bound=len(controls))
    if not dry_run:require(status==b'' and origin==head,'Clean worktree with origin/'+C.BRANCH+' == HEAD required')
    return state


def read_ok(name):return C.read(C.ROOT/name,16*1024**2)


def controls():
    parent=C.load(C.ROOT/'scripts/qualify_puck_cpu_held_runtime.py','prep03_preflight_parent')
    auditor=C.load(C.ROOT/'scripts/audit_puck_cpu_held_runtime.py','prep03_preflight_auditor')
    freeze=json.loads(read_ok(C.FREEZE));raw=read_ok(C.CONFIG);config=parent.decode(raw)
    require(parent.canonical(config)==raw,'Canonical preparation03 configuration bytes required')
    parent.validate_configuration(config);auditor.configuration(config,False)
    require(parent.allocation_output(config)==auditor.allocation_output(config)==C.OUTPUT and config['stage_parent']==C.STAGE,'Preparation03 identity differs')
    pins=freeze['pins'];require(pins['sources']==config['sources'] and pins['interpreter']==config['interpreter'],'Freeze/config pins differ')
    require(pins['auditor']['sha256']==parent.PREPARATION03_AUDITOR_SHA256,'Auditor pin differs from the parent pin')
    checked=0
    for row in [pins['configuration'],pins['observer'],pins['auditor'],*config['sources'],*config['inputs'].values()]:
        data=read_ok(row['path']);require(len(data)==row['size_bytes'] and C.sha(data)==row['sha256'],'Pin differs: '+row['path']);checked+=1
    data=C.read(config['interpreter']['path'],64*1024**2,single=False)
    require(len(data)==config['interpreter']['size_bytes'] and C.sha(data)==config['interpreter']['sha256'],'Interpreter pin differs');checked+=1
    sha=pins['configuration']['sha256']
    require(freeze['command']==[C.PYTHON,'-I','-S','-B',str(C.ROOT/'scripts/observe_puck_cpu_held_allocation.py'),'--configuration',str(C.ROOT/C.CONFIG),'--sha256',sha],'Observer command differs')
    require(freeze['audit']['command_prefix']==C.audit_command(C.ROOT,sha,'x',C.AUDIT_OUTPUT)[:11] and freeze['audit']['output']==C.AUDIT_OUTPUT,'Audit command differs')
    return parent,freeze,config,raw,dict(pins_checked=checked)


def host(config):
    """Native, alias and interpreter-baseline pins the parent and auditor will re-check."""
    native=json.loads(read_ok(config['inputs']['native']['path']))
    for row in native['native_files']:
        data=C.read(row['path'],256*1024**2,single=False)
        require(len(data)==row['size_bytes'] and C.sha(data)==row['sha256'],'Native pin differs: '+row['path'])
    for path,target in native['aliases']:require(os.readlink(path)==target,'Native alias differs: '+path)
    baseline=json.loads(read_ok(config['inputs']['baseline']['path']));prefix=baseline['python_prefix']
    files={p:(s,d) for p,s,d in baseline['files']};links={p:t for p,t in baseline['symlinks']};seen_files=[];seen_links=[]
    for directory,dirs,names in os.walk(prefix,followlinks=False):
        for name in dirs+names:
            full=os.path.join(directory,name);rel=os.path.relpath(full,prefix);state=os.lstat(full)
            if stat.S_ISLNK(state.st_mode):
                require(rel in links and os.readlink(full)==links[rel],'Unexpected baseline alias: '+rel);seen_links.append([rel,links[rel]])
            elif stat.S_ISREG(state.st_mode):
                require(rel in files,'Unexpected baseline file: '+rel);data=C.read(full,256*1024**2,single=False)
                require((len(data),C.sha(data))==files[rel],'Baseline file differs: '+rel);seen_files.append([rel,len(data),C.sha(data)])
            else:require(stat.S_ISDIR(state.st_mode),'Special baseline entry: '+rel)
    seen_files.sort();seen_links.sort()
    require(seen_files==baseline['files'] and seen_links==baseline['symlinks'],'Baseline namespace differs')
    manifest=json.dumps(dict(files=seen_files,symlinks=seen_links),sort_keys=True,separators=(',',':')).encode()
    require(C.sha(manifest)==baseline['prefix_manifest_sha256'],'Baseline manifest hash differs')
    external=list(baseline['external_libraries'])+([baseline['bwrap_executable']] if baseline.get('bwrap_executable') else [])
    for row in external:
        data=C.read(row.get('realpath',row.get('path')),256*1024**2,single=False)
        require(len(data)==row['size'] and C.sha(data)==row['sha256'],'Baseline external file differs')
    for path,target in baseline.get('host_path_aliases',[]):require(os.readlink(path)==target,'Host alias differs: '+path)
    return dict(native_files=len(native['native_files']),native_aliases=len(native['aliases']),baseline_files=len(seen_files),
        baseline_links=len(seen_links),baseline_external_files=len(external))


def resources(config,enforce):
    limits=config['limits']
    mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024
    value=dict(mem_available_bytes=mem,tmpfs_available_bytes=shutil.disk_usage('/tmp').free,disk_available_bytes=shutil.disk_usage(C.ROOT).free,
        nofile=list(resource.getrlimit(resource.RLIMIT_NOFILE)),tmp_flags=os.statvfs('/tmp').f_flag)
    hard=value['nofile'][1]
    value['floors_met']=(mem>=limits['min_available_ram_bytes'] and value['tmpfs_available_bytes']>=limits['min_tmpfs_free_bytes']
        and value['disk_available_bytes']>=limits['min_free_bytes'] and (hard==resource.RLIM_INFINITY or hard>=limits['max_fds'])
        and not value['tmp_flags']&(os.ST_RDONLY|os.ST_NOEXEC))
    if enforce:require(value['floors_met'],'Preparation03 resource floors not met')
    return value


def absent(paths):
    present=[str(p) for p in paths if os.path.lexists(p)]
    require(not present,'Reserved paths already exist: '+', '.join(present))
    return len(paths)


def records(name):
    return [Path(name),C.ROOT/C.RECORDS/Path(name).name]


def same_record(name):
    first,copy=(C.read(p) for p in records(name));require(first==copy,'Record copies differ: '+name);return json.loads(first)


def prepared(config,raw):
    transport_raw=C.read(C.ROOT/C.TRANSPORT);transport=json.loads(transport_raw);sha=C.sha(raw)
    require(transport.get('kind')=='puck-cpu-held-cli-transport-v1' and transport.get('phase')=='prepare'
        and transport.get('configuration_sha256')==sha and transport.get('observed_returncode')==0 and transport.get('timed_out') is False
        and transport.get('command')==[C.PYTHON,'-I','-S','-B',str(C.ROOT/'scripts/qualify_puck_cpu_held_runtime.py'),'--configuration',str(C.ROOT/C.CONFIG),'--sha256',sha],
        'Normal preparation03 transport required')
    result_raw=C.read(C.ROOT/C.OUTPUT/'result.json');result=json.loads(result_raw)
    stdout=C.read(C.ROOT/C.PARENT_STREAMS[0])
    require(transport['stdout']==dict(path=C.PARENT_STREAMS[0],size_bytes=len(stdout),sha256=C.sha(stdout)) and stdout==result_raw,'Parent stdout differs from result')
    require(result.get('kind')=='puck-cpu-held-runtime-outcome-v13' and result.get('version')==13 and result.get('allocation_id')==13
        and result.get('phase')=='prepare' and result.get('status')=='prepared' and result.get('configuration_sha256')==sha
        and result.get('stage_parent')==C.STAGE and result.get('sources')==config['sources'] and result.get('inputs')==config['inputs']
        and not {'error','error_type'}&set(result),'Prepared preparation03 result required')
    terminal=same_record(C.OBSERVER_TERMINAL)
    require(terminal.get('returncode')==0 and terminal.get('outer_timeout') is False and terminal.get('stdout_equals_transport') is True
        and terminal['stdout']['sha256']==C.sha(transport_raw) and terminal.get('boot_id_before')==terminal.get('boot_id_after')==C.boot_id(),
        'Observer terminal/boot differs')
    roots=C.stat_roots(C.STAGE,result['staged_roots'])
    return dict(transport_sha256=C.sha(transport_raw),result_sha256=C.sha(result_raw),staged_roots=roots,observer_boot_id=terminal['boot_id_before'])


def check(phase,dry_run=False):
    require(phase in PHASES,'Unknown preflight phase')
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode and str(Path(sys.executable).resolve())==C.PYTHON
        and not os.environ.get('LD_PRELOAD') and not os.environ.get('LD_LIBRARY_PATH'),'Pinned isolated interpreter required')
    os.chdir(C.ROOT)
    require(C.boot_id()==C.BOOT,'Boot differs from the required preparation boot '+C.BOOT)
    value=dict(kind='palimpsest-prep03-preflight-v1',phase=phase,dry_run=dry_run,boot_id=C.boot_id(),
        at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),git=git_state(dry_run))
    parent,freeze,config,raw,pins=controls();value.update(pins);value['host']=host(config)
    value['resources']=resources(config,enforce=phase=='observer' and not dry_run)
    audit_paths=[C.AUDIT_OUTPUT,C.AUDIT_STDOUT,C.AUDIT_STDERR,*records(C.AUDIT_RECORD),*records(C.AUDIT_TERMINAL)]
    archive_paths=[C.ROOT/C.ARCHIVE/'audit',C.ROOT/C.ARCHIVE/'records',C.ROOT/C.ARCHIVE/'archive-record.json']
    if phase=='observer':
        value['absent']=absent([Path(C.STAGE),*map(Path,glob.glob('/tmp/palimpsest-puck-cpu-held-03*')),C.ROOT/C.OUTPUT,C.ROOT/C.TRANSPORT,
            *[C.ROOT/p for p in C.PARENT_STREAMS],C.OBSERVER_STDOUT,C.OBSERVER_STDERR,*records(C.OBSERVER_TERMINAL),*audit_paths,*archive_paths])
    else:
        value['prepared']=prepared(config,raw)
        require(value['prepared']['observer_boot_id']==value['boot_id'],'Boot changed since the observer')
        if phase=='audit':value['absent']=absent(audit_paths+archive_paths)
        else:
            terminal=same_record(C.AUDIT_TERMINAL)
            require(terminal.get('status')=='PASS_RECORD_WRITTEN' and terminal.get('boot_id_before')==terminal.get('boot_id_after')==value['boot_id'],'Audit terminal differs')
            record=C.read(C.AUDIT_RECORD);require(C.sha(record)==terminal['record']['sha256'],'Audit record differs from its terminal')
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
