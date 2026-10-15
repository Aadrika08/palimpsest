"""One frozen ordinary CPU import observation; no held-runtime qualification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
OUTPUT='runs/puck-cpu-runtime-characterization-02'
SITE='runs/puck-cpu-install-01/site'
WORKER='scripts/characterize_puck_runtime_imports.py'
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
ACCEPTED_SHA='32605ca0d48537a6eabf98a54d605ad23bf525456760d83726381aeaf38e3e96'
ARCHIVE='docs/reports/puck-cpu-retained-admission-02'
PRIOR_ARCHIVE='docs/reports/puck-cpu-characterization-01'
PRIOR_PINS=dict(
    prior_configuration=dict(path=PRIOR_ARCHIVE+'/frozen-configuration.json',size_bytes=9898,
        sha256='b11daf4719daf3a838ece18cf6c0604875d3fcba65b0ab0b5354b9428be6b8ca'),
    prior_result=dict(path=PRIOR_ARCHIVE+'/raw/result.json',size_bytes=613,
        sha256='bd700625635bd47a170b70ce955097c47c0e4a27c1c3d9a04c137461d848288a'),
    prior_audit=dict(path=PRIOR_ARCHIVE+'/failure-audit-01.json',size_bytes=1509,
        sha256='26dd167d4d06ce4a8d45598a06dcd5c0e5a6c1b171550cfa11c0b039b655fbf9'))
NATIVE_METADATA_PIN=dict(path='docs/plans/puck-cpu-characterization-native-metadata-05.json',
    size_bytes=1618086,sha256='64a9e46f60700f12712262879547fbf26d785fb8a825098940e6494482dae2aa')
MiB=1024**2
VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',torchvision='0.24.0+cpu',mujoco='3.3.6')
ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',
    HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/scratch',PATH='/nonexistent',TZ='UTC',
    CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',
    OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0')
LIMITS=dict(normal_seconds=180,child_hard_seconds=190,hard_seconds=195,
    rss_bytes=1536*MiB,address_space_bytes=8192*MiB,output_bytes=64*MiB,
    scratch_bytes=64*MiB,file_bytes=8*MiB,min_free_bytes=4096*MiB,
    min_available_ram_bytes=2048*MiB,max_processes=3,max_fds=40000)
ROLES=dict(baseline='docs/plans/puck-python-louvain-host-baseline-v1.json',
    inventory='runs/puck-cpu-retained-admission-02/inventory.json',
    layout='docs/reports/puck-cpu-install-01/wheel-layout.json',
    accepted_result='runs/puck-cpu-retained-admission-02/result.json',
    accepted_snapshot='runs/puck-cpu-retained-admission-02/snapshot.json',
    accepted_audit=ARCHIVE+'/acceptance-audit-03.json',
    accepted_configuration='docs/plans/puck-cpu-retained-admission-02.json',
    accepted_index=ARCHIVE+'/evidence-index.json',
    native_metadata=NATIVE_METADATA_PIN['path'],
    **{role:row['path'] for role,row in PRIOR_PINS.items()})
SOURCES=tuple(sorted(('scripts/characterize_puck_cpu_runtime.py',WORKER,
    'scripts/build_puck_python_louvain.py','scripts/install_puck_cpu.py',
    'scripts/acquire_puck_cpu_payloads.py',
    'scripts/admit_puck_retained_installation.py','src/palimpsest/__init__.py',
    'src/palimpsest/bounded_qualification.py','src/palimpsest/evaluate.py',
    'src/palimpsest/puck_execution_files.py','src/palimpsest/puck_retained_installation.py',
    'src/palimpsest/puck_build_inputs.py','src/palimpsest/puck_package_payloads.py',
    'docs/plans/puck-cpu-characterization-v2.md')))
PRIOR_SOURCES=tuple(path.replace('puck-cpu-characterization-v2.md','puck-cpu-characterization-v1.md')
                    for path in SOURCES)
CLAIMS=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,
    study_authorized=False,executable=False,qualification_claims=[])
PROBE="""import json,os,pathlib,stat,sys
parent_net,site,hidden=sys.argv[1:]
assert os.readlink('/proc/self/ns/net')!=parent_net
assert all(not line.split() or line.split()[0] in ('Iface','lo') for line in pathlib.Path('/proc/net/route').read_text().splitlines())
assert all(line.split()[-1]=='lo' for line in pathlib.Path('/proc/net/ipv6_route').read_text().splitlines() if line.split())
assert os.statvfs(site).f_flag & os.ST_RDONLY
assert not pathlib.Path(hidden).exists()
assert not pathlib.Path('/scratch/pycache').stat().st_mode & 0o077
assert not list(pathlib.Path('/scratch/pycache').iterdir())
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert sys.pycache_prefix=='/scratch/pycache'
p=pathlib.Path('/scratch/tmp/probe');p.write_bytes(b'bounded');p.unlink()
print(json.dumps(dict(kind='cpu-characterization-namespace-v1',network_isolated=True,site_readonly=True,project_hidden=True,private_pycache_empty=True)))
"""


def fingerprint(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)


def read(path,maximum):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or not 0<before.st_size<=maximum:
            raise ValueError('Bounded single-link input required')
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(maximum+1)
        if (len(raw)!=before.st_size or fingerprint(os.fstat(fd))!=fingerprint(before)
                or fingerprint(Path(path).lstat())!=fingerprint(before)):
            raise ValueError('Input changed while read')
        return raw
    finally:os.close(fd)


def validate_configuration(config):
    if (set(config)!={'kind','version','output','site_root','sources','inputs','roles','limits','environment','expected_versions'}
            or type(config.get('version')) is not int or config.get('kind')!='puck-cpu-runtime-characterization-v1' or config.get('version')!=1
            or config.get('output')!=OUTPUT or config.get('site_root')!=SITE
            or config.get('roles')!=ROLES or config.get('limits')!=LIMITS
            or config.get('environment')!=ENVIRONMENT or config.get('expected_versions')!=VERSIONS
            or tuple(row['path'] for row in config['sources'])!=SOURCES):
        raise ValueError('Exact CPU characterization configuration required')
    if config['inputs']!=required_input_rows(read_prior_configuration()):
        raise ValueError('Exact CPU characterization input closure required')


def read_prior_configuration():
    row=PRIOR_PINS['prior_configuration'];raw=read(ROOT/row['path'],MiB)
    if len(raw)!=row['size_bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:
        raise ValueError('Frozen prior configuration bytes differ')
    return json.loads(raw)


def required_input_rows(prior):
    """Derive this epoch's 12 role pins and 16+14 historical source pins."""
    prior_roles={role:path for role,path in ROLES.items() if role not in PRIOR_PINS}
    prior_roles['native_metadata']='docs/plans/puck-cpu-characterization-native-metadata-04.json'
    if (prior.get('kind')!='puck-cpu-runtime-characterization-v1' or type(prior.get('version')) is not int
            or prior['version']!=1 or prior.get('output')!='runs/puck-cpu-runtime-characterization-01'
            or prior.get('site_root')!=SITE or prior.get('roles')!=prior_roles
            or prior.get('limits')!=LIMITS or prior.get('environment')!=ENVIRONMENT
            or prior.get('expected_versions')!=VERSIONS
            or tuple(row['path'] for row in prior['sources'])!=PRIOR_SOURCES):
        raise ValueError('Frozen prior characterization configuration differs')
    old_inputs={row['path']:row for row in prior['inputs']}
    accepted_caps={path for path in old_inputs if path.startswith(ARCHIVE+'/source/')}
    if (len(prior['inputs'])!=25 or len(accepted_caps)!=16
            or set(old_inputs)!=set(prior_roles.values())|accepted_caps):
        raise ValueError('Frozen prior characterization input closure differs')
    rows={path:dict(row) for path,row in old_inputs.items() if path!=prior_roles['native_metadata']}
    rows[NATIVE_METADATA_PIN['path']]=dict(NATIVE_METADATA_PIN)
    rows.update((row['path'],dict(row)) for row in PRIOR_PINS.values())
    for row in prior['sources']:
        path=PRIOR_ARCHIVE+'/source/'+row['path'];rows[path]=dict(row,path=path)
    if len(rows)!=42:raise ValueError('CPU characterization input closure differs')
    return [rows[path] for path in sorted(rows)]


def validate_prior_characterization(config,result,audit,pins):
    for row in required_input_rows(config):
        if pins.get(row['path'])!=row:
            raise ValueError('Prior characterization input pins differ')
    prior_sha=PRIOR_PINS['prior_configuration']['sha256']
    closure=result.get('closure',{});elapsed=result.get('elapsed_seconds')
    verified=audit.get('verified',{})
    if (result.get('kind')!='puck-cpu-characterization-outcome-v1' or result.get('status')!='FAIL'
            or result.get('configuration_sha256')!=prior_sha
            or result.get('error_type')!='RuntimeError' or result.get('error')!='CPU worker did not complete normally'
            or any(result.get(key) is not False for key in CLAIMS if key!='qualification_claims')
            or result.get('qualification_claims')!=[]
            or type(elapsed) not in (int,float) or not 0<elapsed<LIMITS['normal_seconds']
            or closure.get('active_children')!=[] or closure.get('active_non_main_threads')!=[]
            or closure.get('all_handles_closed') is not True or closure.get('all_receipts_fsynced') is not True
            or type(closure.get('fd_count_before')) is not int or closure['fd_count_before']<0
            or type(closure.get('fd_count_after')) is not int or closure['fd_count_before']!=closure['fd_count_after']
            or audit.get('kind')!='cpu-characterization-independent-failure-audit-v1'
            or audit.get('status')!='PRESERVED_FAILURE_VERIFIED'
            or any(audit.get(key) is not False for key in (*CLAIMS,'native_qualified','ordinary_imports_observed','target_code_executed_by_auditor') if key!='qualification_claims')
            or audit.get('qualification_claims')!=[] or verified.get('configuration_sha256')!=prior_sha
            or verified.get('parent_result_sha256')!=PRIOR_PINS['prior_result']['sha256']
            or type(verified.get('worker_returncode')) is not int or verified['worker_returncode']!=1
            or 'worker_failure' not in verified or verified['worker_failure'] is not None
            or verified.get('first_import')!='numpy'
            or verified.get('reported_error_type')!='builtins.ImportError'
            or verified.get('source_pins')!=14 or verified.get('input_pins')!=25
            or verified.get('archived_acceptance_source_pins')!=16):
        raise ValueError('Prior characterization must retain its exact normal failed outcome')


def validate_native_metadata(native):
    if (native.get('kind')!='puck-cpu-characterization-native-metadata-v5'
            or native.get('root_scope')!='installed_shared_objects_and_interpreter'
            or native.get('errors')!=[] or native.get('oversized_native_files')!=[]
            or native.get('status')!='COMPLETE' or native.get('required_missing_names')!=[]
            or type(native.get('native_files')) is not list or not 1<=len(native['native_files'])<=128
            or type(native.get('aliases')) is not list or len(native['aliases'])>256):
        raise ValueError('Incomplete native metadata cannot define a mount set')
    seen=set()
    for row in native['native_files']:
        path=row['path']
        if (type(path) is not str or not (path.startswith('/usr/lib/') or path in ('/usr/bin/ldconfig','/etc/ld.so.cache'))
                or str(Path(path))!=path or '..' in Path(path).parts or path in seen
                or type(row['size_bytes']) is not int or not 0<=row['size_bytes']<=64*MiB
                or type(row['sha256']) is not str or len(row['sha256'])!=64
                or any(c not in '0123456789abcdef' for c in row['sha256'])):
            raise ValueError('Unsupported native metadata file')
        seen.add(path)


def sandbox_command(baseline,native,payload,request,*,probe=False):
    cmd=['/usr/bin/bwrap','--unshare-all','--unshare-user','--as-pid-1',
        '--disable-userns','--die-with-parent','--cap-drop','ALL','--clearenv',
        '--hostname','palimpsest-cpu-observation','--ro-bind',baseline['python_prefix'],baseline['python_prefix']]
    paths={row['path'] for row in native['native_files']}
    for row in baseline['external_libraries']:paths.add((row.get('realpath') or row['path']))
    for path in sorted(paths):cmd+=['--ro-bind',path,path]
    aliases=dict(baseline['host_path_aliases'])
    for path,target in native['aliases']:
        if path in aliases and aliases[path]!=target:raise ValueError('Conflicting host alias')
        aliases[path]=target
    for path,target in sorted(aliases.items(),key=lambda item:(item[0].count('/'),item[0])):
        cmd+=['--symlink',target,path]
    cmd+=['--ro-bind',str(ROOT/SITE),str(ROOT/SITE),'--ro-bind',str(ROOT/WORKER),'/driver.py',
        '--ro-bind',str(request),'/request.json','--bind',str(payload),'/output',
        '--size',str(LIMITS['scratch_bytes']),'--tmpfs','/scratch']
    for name in ('home','tmp','pycache'):cmd+=['--dir','/scratch/'+name,'--chmod','0700','/scratch/'+name]
    cmd+=['--symlink','scratch/tmp','/tmp','--proc','/proc','--remount-ro','/proc',
        '--dev','/dev','--remount-ro','/dev','--remount-ro','/']
    for key,value in ENVIRONMENT.items():cmd+=['--setenv',key,value]
    cmd+=['--chdir','/scratch',PYTHON,'-I','-S','-B','-X','pycache_prefix=/scratch/pycache']
    return cmd+(['-c',PROBE,os.readlink('/proc/self/ns/net'),str(ROOT/SITE),str(ROOT/'docs')]
                if probe else ['/driver.py','/request.json',hashlib.sha256(request.read_bytes()).hexdigest()])


def execute(config,digest,started):
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
    import build_puck_python_louvain as build
    from palimpsest import bounded_qualification as bounds
    from palimpsest.puck_retained_installation import AdmissionInputs,HeldInstalledFiles
    from admit_puck_retained_installation import completion_state
    output=ROOT/OUTPUT;deadline=started+LIMITS['normal_seconds'];state={};result=dict(CLAIMS)
    rows=sorted(config['sources']+config['inputs']+[config['_configuration_row']],key=lambda r:r['path'])
    limits=resource.getrlimit(resource.RLIMIT_NOFILE)
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    if (min(limits)<LIMITS['max_fds'] or available<LIMITS['min_available_ram_bytes']
            or shutil.disk_usage(ROOT).free<LIMITS['min_free_bytes']):
        raise ValueError('CPU characterization resource admission failed')
    resource.setrlimit(resource.RLIMIT_NOFILE,(LIMITS['max_fds'],LIMITS['max_fds']))
    resource.setrlimit(resource.RLIMIT_AS,(LIMITS['address_space_bytes'],LIMITS['address_space_bytes']))
    resource.setrlimit(resource.RLIMIT_FSIZE,(LIMITS['file_bytes'],LIMITS['file_bytes']))
    with AdmissionInputs(ROOT,rows,deadline):pass
    bounds.reserve_output(output,{'sources':{'root':str(ROOT),'files':rows},'installed':{'root':str(ROOT/SITE)}})
    for name in ('payload','probe-logs','worker-logs'):(output/name).mkdir(mode=0o700)
    bounds.write_new(output/'configuration.json',{k:v for k,v in config.items() if not k.startswith('_')})
    before_fds=len(os.listdir('/proc/self/fd'))
    result.update(kind='puck-cpu-characterization-outcome-v1',status='FAIL',configuration_sha256=digest)
    last=[0.];parent_peak=[0]
    def check():
        now=time.monotonic()
        if now>=deadline:raise TimeoutError('CPU characterization normal deadline')
        if now-last[0]<.05:return
        last[0]=now
        parent_rss=int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
        parent_peak[0]=max(parent_peak[0],parent_rss)
        if parent_rss>LIMITS['rss_bytes']:raise ValueError('CPU parent sampled RSS stop')
        if (shutil.disk_usage(ROOT).free<LIMITS['min_free_bytes'] or
                bounds._output_bytes(output,max_files=64,max_directories=8)>LIMITS['output_bytes']):
            raise ValueError('CPU characterization disk/output limit')
    try:
        with bounds.hard_guard(started+LIMITS['hard_seconds'],state):
            with AdmissionInputs(ROOT,rows,deadline) as inputs:
                get=lambda role:inputs.read_json(ROLES[role])
                old,audit,snapshot,accepted=(get(role) for role in ('accepted_result','accepted_audit','accepted_snapshot','accepted_configuration'))
                pins={row['path']:row for row in rows}
                validate_prior_characterization(*(get(role) for role in ('prior_configuration','prior_result','prior_audit')),pins)
                if (old['status']!='PASS' or old['claims']['package_preparation_accepted'] is not True
                        or any(old['claims'].get(k) is not False for k in ('runtime_qualified','numerical_imports_executed','study_authorized','collection_authorized'))
                        or audit['status']!='PASS' or audit['package_preparation_accepted'] is not True
                        or old['configuration_sha256']!=ACCEPTED_SHA or audit['verified']['configuration_sha256']!=ACCEPTED_SHA
                        or pins[ROLES['accepted_configuration']]['sha256']!=ACCEPTED_SHA
                        or old['snapshot_sha256']!=pins[ROLES['accepted_snapshot']]['sha256']
                        or snapshot['site_root']!=str(ROOT/SITE)):
                    raise ValueError('Accepted package preparation binding differs')
                for row in accepted['sources']:
                    archived=pins[ARCHIVE+'/source/'+row['path']]
                    if any(archived[k]!=row[k] for k in ('size_bytes','sha256')):raise ValueError('Historical frozen source differs')
                inventory,layout,baseline,native=(get(role) for role in ('inventory','layout','baseline','native_metadata'))
                validate_native_metadata(native)
                files=inventory['entries'];directories=layout['predicted_destination_directories']
                if len(files)!=27225 or len(directories)!=2074 or sum(r['size_bytes'] for r in files)!=1304701872:
                    raise ValueError('Accepted measured namespace differs')
                def native_checks():
                    if len(native['native_files'])>128 or len(native['aliases'])>256:raise ValueError('Native metadata bound')
                    for row in native['native_files']:
                        if not (row['path'].startswith('/usr/lib/') or row['path'] in ('/usr/bin/ldconfig','/etc/ld.so.cache')):
                            raise ValueError('Unexpected native input path')
                        if build.file_row(Path(row['path']),deadline,single_link=False)!={k:row[k] for k in ('size_bytes','sha256')}:
                            raise ValueError('Native input identity changed')
                    for path,target in native['aliases']:
                        if os.readlink(path)!=target:raise ValueError('Native alias changed')
                native_checks();before=build.verify_baseline(baseline,deadline)
                bounds.write_new(output/'baseline-before.json',before)
                with HeldInstalledFiles(ROOT/SITE,files,directories,deadline,check=check) as held:
                    request=dict(kind='puck-runtime-import-characterization-v2',version=2,
                        site_root=str(ROOT/SITE),output_root='/output',environment=ENVIRONMENT,
                        expected_versions=VERSIONS,pycache_prefix='/scratch/pycache')
                    bounds.write_new(output/'request.json',request)
                    for probe,name in ((True,'probe'),(False,'worker')):
                        command=sandbox_command(baseline,native,output/'payload',output/'request.json',probe=probe)
                        bounds.write_new(output/(name+'-invocation.json'),dict(command=command,configuration_sha256=digest))
                        observed=bounds.supervised(command,output/(name+'-logs'),cwd=ROOT,
                            normal_deadline=deadline,hard_deadline=started+LIMITS['child_hard_seconds'],
                            rss_bytes=LIMITS['rss_bytes'],output_bytes=LIMITS['output_bytes'],
                            min_free_bytes=LIMITS['min_free_bytes'],max_processes=LIMITS['max_processes'],
                            output_root=output,output_namespace_limits=(64,8),guard_state=state,log_mode='direct')
                        bounds.write_new(output/(name+'-supervision.json'),observed)
                        if observed['status']!='completed':raise RuntimeError('CPU '+name+' did not complete normally')
                        if probe:
                            namespace=json.loads(read(output/'probe-logs/stdout.log',MiB))
                            if namespace!={'kind':'cpu-characterization-namespace-v1','network_isolated':True,'site_readonly':True,'project_hidden':True,'private_pycache_empty':True}:
                                raise ValueError('Namespace probe receipt differs')
                            bounds.write_new(output/'namespace.json',namespace)
                    report=json.loads(read(output/'payload/imports.json',MiB))
                    if (report['kind']!='puck-runtime-import-characterization-result-v3' or report['status']!='observed'
                            or report['request_sha256']!=hashlib.sha256(read(output/'request.json',MiB)).hexdigest()
                            or report['source_sha256']!=pins[WORKER]['sha256']
                            or report['versions']!=VERSIONS or [r['name'] for r in report['imports']]!=list(VERSIONS)
                            or any(report.get(k) is not False for k in ('runtime_qualified','native_authorized','collection_authorized','study_authorized','executable'))
                            or report['qualification_claims']!=[]):raise ValueError('CPU import observation differs')
                    after=build.verify_baseline(baseline,deadline);native_checks()
                    if before!=after:raise ValueError('Trusted baseline changed')
                    bounds.write_new(output/'baseline-after.json',after)
                    validate_prior_characterization(*(get(role) for role in ('prior_configuration','prior_result','prior_audit')),pins)
                    held.recheck();inputs.recheck();check()
                    result.update(report_sha256=hashlib.sha256(read(output/'payload/imports.json',MiB)).hexdigest(),
                        versions=VERSIONS,namespace_probe_completed=True,worker_supervision_status=observed['status'],
                        accepted_package_preparation_preserved=True)
                inputs.recheck()
            result['status']='observed'
    except Exception as error:result.update(status='FAIL',error_type=type(error).__name__,error=str(error))
    result['closure']=completion_state(before_fds);result['elapsed_seconds']=time.monotonic()-started
    result['sampled_parent_peak_rss_bytes']=parent_peak[0]
    bounds.write_new(output/'result.json',result);check();completion_state(before_fds)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',required=True,type=Path);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();started=time.monotonic()
    if os.getpgrp()!=os.getpid():os.setsid()
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,LIMITS['hard_seconds'])
    try:
        raw=read(args.configuration,MiB)
        if hashlib.sha256(raw).hexdigest()!=args.sha256:raise ValueError('Configuration SHA differs')
        config=json.loads(raw);validate_configuration(config)
        for row in config['sources']:
            if hashlib.sha256(read(ROOT/row['path'],MiB)).hexdigest()!=row['sha256']:raise ValueError('Trusted source differs')
        if (Path(sys.executable).resolve()!=Path(PYTHON) or not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode)
                or os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH')):
            raise ValueError('Original isolated CPU interpreter and loader environment required')
        if os.path.lexists(ROOT/OUTPUT):raise ValueError('CPU observation allocation already reserved')
        sys.pycache_prefix=str(ROOT/OUTPUT/'unused-parent-pycache')
        config['_configuration_row']=dict(path=args.configuration.relative_to(ROOT).as_posix(),size_bytes=len(raw),sha256=args.sha256)
        result=execute(config,args.sha256,started)
        print(json.dumps(result,sort_keys=True),flush=True)
        return 0 if (result['status']=='observed' and not any(k in result for k in ('error','error_type'))
                     and time.monotonic()-started<LIMITS['normal_seconds']) else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
