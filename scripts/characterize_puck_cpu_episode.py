"""Characterization-04: one frozen unguarded held-episode observation; no qualification.

Two fresh sandboxed workers run ``puck_held_episode.run`` over ordinary imports
from the accepted site, inside the native metadata v6 namespace with the staged
EGL vendor JSON and the frozen episode environment: worker A records the source
episode, worker B replays it from A's read-only output. Each records and refuses
every process creation and reports its module cache and mapped images. The result
is observation evidence only; it grants no runtime, native or collection authority.
"""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import shutil
import signal
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
MiB=1024**2
OUTPUT='runs/puck-cpu-runtime-characterization-04'
KIND='puck-cpu-runtime-characterization-v3'
VERSION=3
SITE='runs/puck-cpu-install-01/site'
WORKER='scripts/characterize_puck_episode_worker.py'
HELPER='scripts/characterize_puck_runtime_imports.py'
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
INTERPRETER=dict(path='python3.11',size_bytes=21662864,
    sha256='572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a')
ACCEPTED_SHA='32605ca0d48537a6eabf98a54d605ad23bf525456760d83726381aeaf38e3e96'
NATIVE_V6='puck-cpu-characterization-native-metadata-v6'
NATIVE_METADATA_PIN=dict(path='docs/plans/puck-cpu-characterization-native-metadata-06.json',size_bytes=17199,
    sha256='48ca37b1c45366bcd53ac195277ade6236537f89a720b50591906764eaf72569')
# Characterization-02's frozen configuration supplies the accepted package/baseline pins.
OBSERVATION02_PIN=dict(path='docs/reports/puck-cpu-characterization-02/frozen-configuration.json',size_bytes=13940,
    sha256='4b98ff368e97351b2079ff44c75cb910d08559e5e037a6afc4887c28cd38fea8')
INHERITED=('accepted_audit','accepted_configuration','accepted_index','accepted_result','accepted_snapshot',
    'baseline','inventory','layout')
ROLES=dict(baseline='docs/plans/puck-python-louvain-host-baseline-v1.json',
    inventory='runs/puck-cpu-retained-admission-02/inventory.json',
    layout='docs/reports/puck-cpu-install-01/wheel-layout.json',
    accepted_result='runs/puck-cpu-retained-admission-02/result.json',
    accepted_snapshot='runs/puck-cpu-retained-admission-02/snapshot.json',
    accepted_audit='docs/reports/puck-cpu-retained-admission-02/acceptance-audit-03.json',
    accepted_configuration='docs/plans/puck-cpu-retained-admission-02.json',
    accepted_index='docs/reports/puck-cpu-retained-admission-02/evidence-index.json',
    native_metadata=NATIVE_METADATA_PIN['path'],observation02_configuration=OBSERVATION02_PIN['path'])
VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',mujoco='3.3.6',gymnasium='1.2.1')
EGL_VENDOR_CONTROL='/puck/control/egl-vendor.json'
ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',
    HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/scratch',PATH='/nonexistent',TZ='UTC',
    CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',
    OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0',
    # The held episode additions; the unguarded site keeps its own path here.
    PYGLFW_LIBRARY=str(ROOT/SITE)+'/glfw/x11/libglfw.so',MESA_SHADER_CACHE_DISABLE='true',
    PYGAME_HIDE_SUPPORT_PROMPT='hide',__EGL_VENDOR_LIBRARY_FILENAMES=EGL_VENDOR_CONTROL)
LIMITS=dict(normal_seconds=360,child_hard_seconds=375,hard_seconds=390,
    rss_bytes=2048*MiB,address_space_bytes=8192*MiB,output_bytes=64*MiB,
    scratch_bytes=64*MiB,file_bytes=16*MiB,min_free_bytes=4096*MiB,
    min_available_ram_bytes=2048*MiB,max_processes=3,max_fds=40000)
# Sources and controls are bound file by file, so the retained tree stays within 16 directories.
OUTPUT_NAMESPACE=(128,16)
EPISODE=dict(upstream_commit='8d964599119b420de67ee259434d273651a1a76d',
    profile=dict(controller='manual',device='cpu',seed=7,scenario='reproduction',texture='checker'),
    schedule=dict(ticks=48,actions=[[0,1.0,0.0],[24,1.0,0.5]]),
    run_ids=dict(source='a6effc7912fec337875d13ae69445e43',replay='6c04b9ed22c383fda860fa3b4f8bab13'))
# The exact strings census v2 observed on this host's Mesa llvmpipe EGL context.
RENDERER=dict(vendor='Mesa',renderer_contains='llvmpipe',version='4.6 (Compatibility Profile) Mesa 26.2.2-arch1.1',
    egl_vendor='Mesa Project',egl_version='1.5',backend='egl')
REQUEST_KIND='puck-episode-characterization-request-v1'
REPORT_KIND='puck-episode-characterization-result-v1'
RESULT_KIND='puck-held-public-episode-result-v1'
REPORT_NAME='characterization.json'
REPORT_BYTES=4*MiB
# The held episode worker closure (qualifier EPISODE_WORKER_SOURCES) without its
# bootstrap, plus this worker and its cache/maps helper.
PALIMPSEST=('__init__','__main__','afterimage','artifacts','assets','atlas','body_adaptation','body_profile',
    'bounded_qualification','cli','comparison','doctor','engine','evaluate','flynn','held_provenance',
    'interventions','lab','male_model','male_policy','male_research','memory','memory_experiment',
    'memory_history','memory_reference','memory_task','memory_world','profiles','puck_balanced',
    'puck_balanced_development','puck_balanced_student','puck_build_inputs','puck_bundle_provenance',
    'puck_collection_admission','puck_collection_close','puck_collection_ledger','puck_cpu_namespace',
    'puck_cpu_registration','puck_dependency_bindings','puck_dependency_files','puck_dependency_imports',
    'puck_development','puck_execution','puck_execution_files','puck_held_episode','puck_learning',
    'puck_model','puck_native_identity','puck_native_origins','puck_on_policy','puck_package_payloads',
    'puck_profile','puck_retained_installation','puck_runtime_qualification','puck_runtime_registration',
    'puck_runtime_staging','puck_scene_catalog','puck_scene_git','puck_scene_inventory_scope',
    'puck_scene_markdown','puck_scene_reference_resolution','puck_scene_registry','puck_scene_reports',
    'puck_scene_retained','puck_scene_roots','puck_scene_training','puck_student','puck_teacher',
    'puck_worker_preflight','records','replay','snapshots','sonification','specimens','storage',
    'task_mechanics','task_profiles','worker')
CAPSULE=tuple(sorted((WORKER,HELPER,*('src/palimpsest/'+name+'.py' for name in PALIMPSEST),
    'upstream/fly-gym/core/__init__.py','upstream/fly-gym/core/astar.py','upstream/fly-gym/environment/__init__.py',
    'upstream/fly-gym/environment/mujoco_model_random_obstacles.xml',
    'upstream/fly-gym/environment/mujoco_two_cam_env_random_obstacles.py',
    'model_manifests/flynn-full-vision.json','pyproject.toml','uv.lock')))
SOURCES=tuple(sorted(set(CAPSULE)|{'scripts/characterize_puck_cpu_episode.py',
    'scripts/qualify_puck_cpu_held_runtime.py','scripts/build_puck_python_louvain.py',
    'scripts/install_puck_cpu.py','scripts/acquire_puck_cpu_payloads.py',
    'scripts/admit_puck_retained_installation.py'}))
CLAIMS=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,
    study_authorized=False,executable=False,qualification_claims=[])
EPISODE_CLAIMS=('runtime_qualified','native_authorized','collection_authorized','executable','qualification_claims')
CONFIGURATION_KEYS={'kind','version','output','site_root','sources','inputs','roles','limits','environment',
    'expected_versions','episode','renderer'}
REPORT_KEYS={'kind','version','status','phase','request_sha256','source_sha256','environment_sha256',
    'python_version','executable_path','pid','ppid','expected_versions','versions','episode_result',
    'process_creation_attempts','import_misses','rechecks','cache','maps','baseline_maps',
    'environment_unchanged','pycache_unchanged','observation_errors','seconds',*CLAIMS}
PROBE="""import json,os,pathlib,sys
parent_net,site,hidden=sys.argv[1:]
assert os.readlink('/proc/self/ns/net')!=parent_net
assert all(not line.split() or line.split()[0] in ('Iface','lo') for line in pathlib.Path('/proc/net/route').read_text().splitlines())
assert all(line.split()[-1]=='lo' for line in pathlib.Path('/proc/net/ipv6_route').read_text().splitlines() if line.split())
assert all(os.statvfs(p).f_flag & os.ST_RDONLY for p in (site,'/puck/source','/puck/control'))
assert not pathlib.Path(hidden).exists()
assert not pathlib.Path('/scratch/pycache').stat().st_mode & 0o077
assert not list(pathlib.Path('/scratch/pycache').iterdir())
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert sys.pycache_prefix=='/scratch/pycache'
p=pathlib.Path('/scratch/tmp/probe');p.write_bytes(b'bounded');p.unlink()
print(json.dumps(dict(kind='cpu-episode-characterization-namespace-v1',network_isolated=True,site_readonly=True,source_readonly=True,project_hidden=True,private_pycache_empty=True)))
"""


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def fingerprint(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)


def read(path,maximum,*,empty=False):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink!=1
                or not (0 if empty else 1)<=before.st_size<=maximum):
            raise ValueError('Bounded single-link input required')
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(maximum+1)
        if (len(raw)!=before.st_size or fingerprint(os.fstat(fd))!=fingerprint(before)
                or fingerprint(Path(path).lstat())!=fingerprint(before)):
            raise ValueError('Input changed while read')
        return raw
    finally:os.close(fd)


def write_raw(path,raw):
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        view=memoryview(raw)
        while view:view=view[os.write(fd,view):]
        os.fsync(fd)
    finally:os.close(fd)


def finite(value,maximum):
    return type(value) in (int,float) and math.isfinite(value) and 0<=value<maximum


def hexdigest(value):
    return type(value) is str and len(value)==64 and all(c in '0123456789abcdef' for c in value)


def same(left,right):return canonical(left)==canonical(right)


def source_rows():
    """Current source pins, for authoring the frozen configuration."""
    return [dict(path=path,size_bytes=len(raw),sha256=sha(raw))
            for path in SOURCES for raw in (read(ROOT/path,MiB,empty=True),)]


def required_inputs():
    """Eight accepted pins from frozen characterization02, plus native 06 and that configuration."""
    raw=read(ROOT/OBSERVATION02_PIN['path'],MiB)
    if len(raw)!=OBSERVATION02_PIN['size_bytes'] or sha(raw)!=OBSERVATION02_PIN['sha256']:
        raise ValueError('Frozen characterization02 configuration bytes differ')
    frozen=json.loads(raw);rows={row['path']:row for row in frozen['inputs']}
    result=[]
    for role in INHERITED:
        if frozen['roles'].get(role)!=ROLES[role] or ROLES[role] not in rows:
            raise ValueError('Frozen characterization02 role differs: '+role)
        result.append(dict(rows[ROLES[role]]))
    result+=[dict(NATIVE_METADATA_PIN),dict(OBSERVATION02_PIN)]
    return sorted(result,key=lambda row:row['path'])


def configuration(sources):
    return dict(kind=KIND,version=VERSION,output=OUTPUT,site_root=SITE,sources=copy.deepcopy(sources),
        inputs=required_inputs(),roles=dict(ROLES),limits=dict(LIMITS),environment=dict(ENVIRONMENT),
        expected_versions=dict(VERSIONS),episode=copy.deepcopy(EPISODE),renderer=dict(RENDERER))


def validate_configuration(config):
    if (type(config) is not dict or set(config)!=CONFIGURATION_KEYS or config['kind']!=KIND
            or type(config['version']) is not int or config['version']!=VERSION
            or config['output']!=OUTPUT or config['site_root']!=SITE
            or not same(config['roles'],ROLES) or not same(config['limits'],LIMITS)
            or not same(config['environment'],ENVIRONMENT) or not same(config['expected_versions'],VERSIONS)
            or not same(config['episode'],EPISODE) or not same(config['renderer'],RENDERER)
            or type(config['sources']) is not list or type(config['inputs']) is not list):
        raise ValueError('Exact characterization-04 configuration required')
    for row in config['sources']:
        if (type(row) is not dict or set(row)!={'path','size_bytes','sha256'}
                or type(row['size_bytes']) is not int or not 0<=row['size_bytes']<=MiB or not hexdigest(row['sha256'])):
            raise ValueError('Exact characterization-04 source pin required')
    if tuple(row['path'] for row in config['sources'])!=SOURCES:
        raise ValueError('Exact characterization-04 source closure required')
    if not same(config['inputs'],required_inputs()):
        raise ValueError('Exact characterization-04 input closure required')


def episode_request(phase,*,source_files,distributions):
    if phase not in ('source','replay'):raise ValueError('Episode phase must be source or replay')
    paths=dict(output_root='/output',asset_root='/scratch/assets',
               source_root='/output' if phase=='source' else '/puck/source-run')
    episode=dict(kind='puck-held-public-episode-v1',version=1,phase=phase,expected_versions=dict(VERSIONS),
                 paths=paths,**copy.deepcopy(EPISODE))
    return dict(kind=REQUEST_KIND,version=1,site_root=str(ROOT/SITE),source_root='/puck/source',
        output_root='/output',pycache_prefix='/scratch/pycache',environment=dict(ENVIRONMENT),
        expected_versions=dict(VERSIONS),runtime=dict(root=str(Path(PYTHON).parent),files=[dict(INTERPRETER)],
        python_version='3.11.15'),source_files=copy.deepcopy(source_files),
        distributions=copy.deepcopy(distributions),episode=episode)


def sandbox_command(baseline,native,*,phase,capsule,capsule_files,controls,payload,request,request_sha,
                    source_run=None,probe=False):
    if type(native) is not dict or native.get('kind')!=NATIVE_V6:
        raise ValueError('Characterization-04 requires native metadata v6')
    if phase not in ('source','replay') or (source_run is None)!=(phase=='source'):
        raise ValueError('Only the replay worker mounts the source run')
    if (any(type(p) is not str or p.startswith('/') or any(part in ('','.','..') for part in p.split('/')) for p in capsule_files)
            or any(type(n) is not str or not n or '/' in n or n in ('.','..') for n in controls)):
        raise ValueError('Capsule files and control names must be canonical relative names')
    cmd=['/usr/bin/bwrap','--unshare-all','--unshare-user','--as-pid-1',
        '--disable-userns','--die-with-parent','--cap-drop','ALL','--clearenv',
        '--hostname','palimpsest-cpu-episode-observation','--ro-bind',baseline['python_prefix'],baseline['python_prefix']]
    paths={row['path'] for row in native['native_files']}
    for row in baseline['external_libraries']:paths.add(row.get('realpath') or row['path'])
    for path in sorted(paths):cmd+=['--ro-bind',path,path]
    aliases=dict(baseline['host_path_aliases'])
    for path,target in native['aliases']:
        if path in aliases and aliases[path]!=target:raise ValueError('Conflicting host alias')
        aliases[path]=target
    for path,target in sorted(aliases.items(),key=lambda item:(item[0].count('/'),item[0])):
        cmd+=['--symlink',target,path]
    cmd+=['--ro-bind',str(ROOT/SITE),str(ROOT/SITE)]
    for path in sorted(capsule_files):cmd+=['--ro-bind',str(Path(capsule)/path),'/puck/source/'+path]
    for name,host in sorted(controls.items()):cmd+=['--ro-bind',str(host),'/puck/control/'+name]
    if source_run is not None:cmd+=['--ro-bind',str(source_run),'/puck/source-run']
    cmd+=['--bind',str(payload),'/output','--size',str(LIMITS['scratch_bytes']),'--tmpfs','/scratch']
    for name in ('home','tmp','pycache','assets'):cmd+=['--dir','/scratch/'+name,'--chmod','0700','/scratch/'+name]
    cmd+=['--symlink','scratch/tmp','/tmp','--proc','/proc','--remount-ro','/proc',
        '--dev','/dev','--remount-ro','/dev','--remount-ro','/']
    for key,value in sorted(ENVIRONMENT.items()):cmd+=['--setenv',key,value]
    cmd+=['--chdir','/scratch',PYTHON,'-I','-S','-B','-X','pycache_prefix=/scratch/pycache']
    if probe:return cmd+['-c',PROBE,os.readlink('/proc/self/ns/net'),str(ROOT/SITE),str(ROOT/'docs')]
    return cmd+['/puck/source/'+WORKER,'/puck/control/'+request,request_sha]


def validate_renderer(value):
    if (type(value) is not dict or set(value)!={'vendor','renderer','version','egl_vendor','egl_version','backend'}
            or any(type(v) is not str for v in value.values())
            or value['vendor']!=RENDERER['vendor'] or RENDERER['renderer_contains'] not in value['renderer']
            or any(value[k]!=RENDERER[k] for k in ('version','egl_vendor','egl_version','backend'))):
        raise ValueError('Episode renderer differs from the frozen Mesa llvmpipe EGL criteria')


def validate_episode_result(value,phase):
    common={'kind','version','phase','run_id','source_run_id','ticks_requested','provenance_sha256','versions','bundle',*EPISODE_CLAIMS}
    keys=common|({'ticks_completed','final_phase','initial_snapshot_id','renderer'} if phase=='source' else {'replay'})
    ticks=EPISODE['schedule']['ticks'];ids=EPISODE['run_ids']
    if (type(value) is not dict or set(value)!=keys or value['kind']!=RESULT_KIND
            or type(value['version']) is not int or value['version']!=1 or value['phase']!=phase
            or value['run_id']!=ids[phase] or value['source_run_id']!=ids['source']
            or type(value['ticks_requested']) is not int or value['ticks_requested']!=ticks
            or not hexdigest(value['provenance_sha256']) or not same(value['versions'],VERSIONS)
            or any(value[k] is not False for k in EPISODE_CLAIMS if k!='qualification_claims')
            or value['qualification_claims']!=[]):
        raise ValueError('Exact held episode '+phase+' result required')
    bundle=value['bundle']
    if (type(bundle) is not dict or set(bundle)!={'path','size_bytes','sha256'} or bundle['path']!=phase+'-bundle.zip'
            or type(bundle['size_bytes']) is not int or not 0<bundle['size_bytes']<=LIMITS['file_bytes']
            or not hexdigest(bundle['sha256'])):
        raise ValueError('Exact bounded '+phase+' bundle receipt required')
    if phase=='source':
        if (type(value['ticks_completed']) is not int or value['ticks_completed']!=ticks
                or type(value['final_phase']) is not str or not 0<len(value['final_phase'])<=64
                or type(value['initial_snapshot_id']) is not str or not 0<len(value['initial_snapshot_id'])<=128):
            raise ValueError('Held source episode must complete every scheduled tick')
        validate_renderer(value['renderer'])
    else:
        replay=value['replay']
        if (type(replay) is not dict or set(replay)!={'status','compared_ticks','compared_events','first_divergence'}
                or replay['status']!='passed' or type(replay['compared_ticks']) is not int or replay['compared_ticks']!=ticks
                or type(replay['compared_events']) is not int or replay['compared_events']<=0
                or replay['first_divergence'] is not None):
            raise ValueError('Held replay must pass every scheduled tick without divergence')


def validate_report(report,*,phase,request_sha256,worker_sha256):
    if (type(report) is not dict or set(report)!=REPORT_KEYS or report['kind']!=REPORT_KIND
            or type(report['version']) is not int or report['version']!=1
            or report['status']!='observed' or report['phase']!=phase
            or report['request_sha256']!=request_sha256 or report['source_sha256']!=worker_sha256
            or report['environment_sha256']!=sha(canonical(ENVIRONMENT))
            or any(report[k] is not False for k in CLAIMS if k!='qualification_claims')
            or report['qualification_claims']!=[]
            or not same(report['expected_versions'],VERSIONS) or not same(report['versions'],VERSIONS)
            or not same(report['process_creation_attempts'],dict(count=0,events=[]))
            or report['environment_unchanged'] is not True or report['pycache_unchanged'] is not True
            or report['observation_errors']!=[] or report['executable_path']!=PYTHON
            or type(report['python_version']) is not str or not report['python_version'].startswith('3.11.15 ')
            or type(report['pid']) is not int or report['pid']<=0 or type(report['ppid']) is not int or report['ppid']<0
            or type(report['rechecks']) is not int or report['rechecks']<1
            or not finite(report['seconds'],LIMITS['normal_seconds'])):
        raise ValueError('Complete observed characterization-04 '+phase+' report required')
    misses=report['import_misses']
    if (type(misses) is not list or len(misses)>4096 or misses!=sorted(set(misses))
            or any(type(n) is not str or not 0<len(n)<=512 for n in misses)):
        raise ValueError('Bounded sorted import misses required')
    cache=report['cache']
    if (type(cache) is not dict or type(cache.get('modules')) is not list or len(cache['modules'])>8192
            or any(type(r) is not dict or type(r.get('name')) is not str for r in cache['modules'])):
        raise ValueError('Bounded module cache observation required')
    names=[r['name'] for r in cache['modules']]
    if len(set(names))!=len(names) or any(n=='torchvision' or n.startswith('torchvision.') for n in names):
        raise ValueError('Episode module cache must be unique and exclude torchvision')
    for key in ('maps','baseline_maps'):
        if type(report[key]) is not dict or type(report[key].get('images')) is not list:
            raise ValueError('Mapped-image observation required')
    validate_episode_result(report['episode_result'],phase)


def execute(config,digest,started):
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
    import build_puck_python_louvain as build
    from palimpsest import bounded_qualification as bounds
    from palimpsest.puck_retained_installation import AdmissionInputs,HeldInstalledFiles
    from palimpsest.puck_cpu_registration import _native,egl_vendor_control
    from admit_puck_retained_installation import completion_state
    output=ROOT/OUTPUT;deadline=started+LIMITS['normal_seconds'];state={};result=dict(CLAIMS)
    rows=sorted(config['sources']+config['inputs']+[config['_configuration_row']],key=lambda r:r['path'])
    limits=resource.getrlimit(resource.RLIMIT_NOFILE)
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    if (min(limits)<LIMITS['max_fds'] or available<LIMITS['min_available_ram_bytes']
            or shutil.disk_usage(ROOT).free<LIMITS['min_free_bytes']):
        raise ValueError('Characterization-04 resource admission failed')
    resource.setrlimit(resource.RLIMIT_NOFILE,(LIMITS['max_fds'],LIMITS['max_fds']))
    resource.setrlimit(resource.RLIMIT_AS,(LIMITS['address_space_bytes'],LIMITS['address_space_bytes']))
    resource.setrlimit(resource.RLIMIT_FSIZE,(LIMITS['file_bytes'],LIMITS['file_bytes']))
    with AdmissionInputs(ROOT,rows,deadline):pass
    bounds.reserve_output(output,{'sources':{'root':str(ROOT),'files':rows},'installed':{'root':str(ROOT/SITE)}})
    for name in ('payload-source','payload-replay','probe-logs','source-logs','replay-logs'):
        (output/name).mkdir(mode=0o700)
    bounds.write_new(output/'configuration.json',{k:v for k,v in config.items() if not k.startswith('_')})
    before_fds=len(os.listdir('/proc/self/fd'))
    result.update(kind='puck-cpu-characterization-outcome-v3',version=3,status='FAIL',configuration_sha256=digest)
    last=[0.];parent_peak=[0]
    def check():
        now=time.monotonic()
        if now>=deadline:raise TimeoutError('Characterization-04 normal deadline')
        if now-last[0]<.05:return
        last[0]=now
        parent_rss=int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
        parent_peak[0]=max(parent_peak[0],parent_rss)
        if parent_rss>LIMITS['rss_bytes']:raise ValueError('Characterization-04 parent sampled RSS stop')
        if (shutil.disk_usage(ROOT).free<LIMITS['min_free_bytes'] or bounds._output_bytes(output,
                max_files=OUTPUT_NAMESPACE[0],max_directories=OUTPUT_NAMESPACE[1])>LIMITS['output_bytes']):
            raise ValueError('Characterization-04 disk/output limit')
    try:
        with bounds.hard_guard(started+LIMITS['hard_seconds'],state):
            with AdmissionInputs(ROOT,rows,deadline) as inputs:
                get=lambda role:inputs.read_json(ROLES[role])
                pins={row['path']:row for row in rows}
                old,audit,snapshot=(get(role) for role in ('accepted_result','accepted_audit','accepted_snapshot'))
                if (old['status']!='PASS' or old['claims']['package_preparation_accepted'] is not True
                        or any(old['claims'].get(k) is not False for k in ('runtime_qualified','numerical_imports_executed','study_authorized','collection_authorized'))
                        or audit['status']!='PASS' or audit['package_preparation_accepted'] is not True
                        or old['configuration_sha256']!=ACCEPTED_SHA or audit['verified']['configuration_sha256']!=ACCEPTED_SHA
                        or pins[ROLES['accepted_configuration']]['sha256']!=ACCEPTED_SHA
                        or old['snapshot_sha256']!=pins[ROLES['accepted_snapshot']]['sha256']
                        or snapshot['site_root']!=str(ROOT/SITE)):
                    raise ValueError('Accepted package preparation binding differs')
                inventory,layout,baseline,native=(get(role) for role in ('inventory','layout','baseline','native_metadata'))
                if native.get('kind')!=NATIVE_V6:raise ValueError('Characterization-04 requires native metadata v6')
                _native(native,deadline)
                files=inventory['entries'];directories=layout['predicted_destination_directories']
                if len(files)!=27225 or len(directories)!=2074 or sum(r['size_bytes'] for r in files)!=1304701872:
                    raise ValueError('Accepted measured namespace differs')
                vendor=egl_vendor_control(native,read(native['egl_vendor']['path'],MiB))
                write_raw(output/'egl-vendor.json',vendor)
                def native_checks():
                    for row in native['native_files']:
                        if build.file_row(Path(row['path']),deadline,single_link=False)!={k:row[k] for k in ('size_bytes','sha256')}:
                            raise ValueError('Native input identity changed')
                    for path,target in native['aliases']:
                        if os.readlink(path)!=target:raise ValueError('Native alias changed')
                    if read(native['egl_vendor']['path'],MiB)!=vendor:raise ValueError('EGL vendor JSON changed')
                native_checks();before=build.verify_baseline(baseline,deadline)
                bounds.write_new(output/'baseline-before.json',before)
                distributions=[dict(name=w['name'],version=w['version'],root_index=0,metadata_path=w['metadata_path'])
                               for w in layout['wheels']]
                with HeldInstalledFiles(ROOT/SITE,files,directories,deadline,check=check) as held:
                    for path in CAPSULE:
                        raw=read(ROOT/path,MiB,empty=True)
                        if len(raw)!=pins[path]['size_bytes'] or sha(raw)!=pins[path]['sha256']:
                            raise ValueError('Characterization-04 capsule source differs: '+path)
                    source_files=[dict(pins[path]) for path in CAPSULE]
                    reports={}
                    for name in ('probe','source','replay'):
                        phase='source' if name=='probe' else name;request_name=request_sha=None
                        controls={'egl-vendor.json':output/'egl-vendor.json'}
                        if name!='probe':
                            request_name='request-'+name+'.json'
                            raw=canonical(episode_request(name,source_files=source_files,distributions=distributions))
                            write_raw(output/request_name,raw);request_sha=sha(raw);controls[request_name]=output/request_name
                        command=sandbox_command(baseline,native,phase=phase,capsule=ROOT,capsule_files=CAPSULE,
                            controls=controls,payload=output/('payload-'+phase),request=request_name,request_sha=request_sha,
                            source_run=output/'payload-source' if name=='replay' else None,probe=name=='probe')
                        bounds.write_new(output/(name+'-invocation.json'),dict(command=command,configuration_sha256=digest))
                        observed=bounds.supervised(command,output/(name+'-logs'),cwd=ROOT,
                            normal_deadline=deadline,hard_deadline=started+LIMITS['child_hard_seconds'],
                            rss_bytes=LIMITS['rss_bytes'],output_bytes=LIMITS['output_bytes'],
                            min_free_bytes=LIMITS['min_free_bytes'],max_processes=LIMITS['max_processes'],
                            output_root=output,output_namespace_limits=OUTPUT_NAMESPACE,guard_state=state,log_mode='direct')
                        bounds.write_new(output/(name+'-supervision.json'),observed)
                        if observed['status']!='completed':raise RuntimeError('Characterization-04 '+name+' did not complete normally')
                        if name=='probe':
                            namespace=json.loads(read(output/'probe-logs/stdout.log',MiB))
                            if namespace!=dict(kind='cpu-episode-characterization-namespace-v1',network_isolated=True,
                                    site_readonly=True,source_readonly=True,project_hidden=True,private_pycache_empty=True):
                                raise ValueError('Namespace probe receipt differs')
                            bounds.write_new(output/'namespace.json',namespace);continue
                        report_raw=read(output/('payload-'+name)/REPORT_NAME,REPORT_BYTES);report=json.loads(report_raw)
                        if canonical(report)!=report_raw:raise ValueError('Canonical characterization-04 report required')
                        validate_report(report,phase=name,request_sha256=request_sha,worker_sha256=pins[WORKER]['sha256'])
                        bundle=report['episode_result']['bundle']
                        bundle_raw=read(output/('payload-'+name)/bundle['path'],LIMITS['file_bytes'])
                        if len(bundle_raw)!=bundle['size_bytes'] or sha(bundle_raw)!=bundle['sha256']:
                            raise ValueError('Characterization-04 '+name+' bundle bytes differ from its receipt')
                        reports[name]=(report,sha(report_raw))
                    source,replay=reports['source'][0],reports['replay'][0]
                    if source['episode_result']['provenance_sha256']!=replay['episode_result']['provenance_sha256']:
                        raise ValueError('Source and replay held provenance differ')
                    after=build.verify_baseline(baseline,deadline);native_checks()
                    if before!=after:raise ValueError('Trusted baseline changed')
                    bounds.write_new(output/'baseline-after.json',after)
                    held.recheck();inputs.recheck();check()
                    natives={row['path'] for row in native['native_files']}
                    mapped=sorted({image['path'] for report,_ in reports.values() for image in report['maps']['images']}&natives)
                    result.update(source_report_sha256=reports['source'][1],replay_report_sha256=reports['replay'][1],
                        versions=dict(VERSIONS),renderer=source['episode_result']['renderer'],
                        ticks_completed=source['episode_result']['ticks_completed'],
                        replay=replay['episode_result']['replay'],process_creation_attempts=0,
                        mapped_native_files=mapped,namespace_probe_completed=True,
                        accepted_package_preparation_preserved=True,worker_supervision_status='completed')
                inputs.recheck()
            result['status']='observed'
    except Exception as error:result.update(status='FAIL',error_type=type(error).__name__,error=str(error))
    result['closure']=completion_state(before_fds);result['elapsed_seconds']=time.monotonic()-started
    result['sampled_parent_peak_rss_bytes']=parent_peak[0]
    bounds.write_new(output/'result.json',result);check();completion_state(before_fds)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',required=True);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();started=time.monotonic()
    configuration=Path(args.configuration);raw=read(configuration,MiB)
    if sha(raw)!=args.sha256:raise ValueError('Configuration SHA differs')
    if os.getpgrp()!=os.getpid():os.setsid()
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,LIMITS['hard_seconds'])
    try:
        config=json.loads(raw);validate_configuration(config)
        if (str(configuration)!=args.configuration or not configuration.is_absolute()
                or not configuration.is_relative_to(ROOT) or configuration.resolve(strict=True)!=configuration
                or (json.dumps(config,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()!=raw):
            raise ValueError('Canonical root-contained frozen characterization-04 configuration required')
        for row in config['sources']:
            source=read(ROOT/row['path'],MiB,empty=True)
            if sha(source)!=row['sha256'] or len(source)!=row['size_bytes']:raise ValueError('Trusted source differs')
        if (Path(sys.executable).resolve()!=Path(PYTHON) or not(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode)
                or os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH')):
            raise ValueError('Original isolated CPU interpreter and loader environment required')
        if os.path.lexists(ROOT/OUTPUT):raise ValueError('Characterization-04 allocation already reserved')
        sys.pycache_prefix=str(ROOT/OUTPUT/'unused-parent-pycache')
        config['_configuration_row']=dict(path=configuration.relative_to(ROOT).as_posix(),size_bytes=len(raw),sha256=args.sha256)
        result=execute(config,args.sha256,started)
        print(json.dumps(result,sort_keys=True),flush=True)
        return 0 if (result['status']=='observed' and not any(k in result for k in ('error','error_type'))
                     and time.monotonic()-started<LIMITS['normal_seconds']) else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
