"""Independent byte audit of one characterization-04 outcome; never imports target code.

Stdlib only. It re-reads the frozen configuration and every pinned source and
input, re-hashes the accepted site, the v6 native leaves, the EGL vendor JSON and
the trusted interpreter prefix, reconstructs both phase requests and all three
namespace argvs independently, and checks the parent result, both worker
reports and receipts, both bundles and the external transport. PASS means the
retained observation is internally consistent; it grants no runtime, native,
renderer or collection authority.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import stat
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
MiB=1024**2
KIND='cpu-episode-characterization-outcome-audit-v1'
OUTPUT='runs/puck-cpu-runtime-characterization-04'
CONFIGURATION_KIND='puck-cpu-runtime-characterization-v3'
SITE='runs/puck-cpu-install-01/site'
PARENT='scripts/characterize_puck_cpu_episode.py'
WORKER='scripts/characterize_puck_episode_worker.py'
HELPER='scripts/characterize_puck_runtime_imports.py'
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
INTERPRETER=dict(path='python3.11',size_bytes=21662864,
    sha256='572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a')
ACCEPTED_SHA='32605ca0d48537a6eabf98a54d605ad23bf525456760d83726381aeaf38e3e96'
SITE_COUNTS=(27225,2074,1304701872)
NATIVE_METADATA_PIN=dict(path='docs/plans/puck-cpu-characterization-native-metadata-06.json',size_bytes=17199,
    sha256='48ca37b1c45366bcd53ac195277ade6236537f89a720b50591906764eaf72569')
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
ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',
    HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/scratch',PATH='/nonexistent',TZ='UTC',
    CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',
    OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0',
    PYGLFW_LIBRARY=str(ROOT/SITE)+'/glfw/x11/libglfw.so',MESA_SHADER_CACHE_DISABLE='true',
    PYGAME_HIDE_SUPPORT_PROMPT='hide',__EGL_VENDOR_LIBRARY_FILENAMES='/puck/control/egl-vendor.json')
LIMITS=dict(normal_seconds=360,child_hard_seconds=375,hard_seconds=390,
    rss_bytes=2048*MiB,address_space_bytes=8192*MiB,output_bytes=64*MiB,
    scratch_bytes=64*MiB,file_bytes=16*MiB,min_free_bytes=4096*MiB,
    min_available_ram_bytes=2048*MiB,max_processes=3,max_fds=40000)
EPISODE=dict(upstream_commit='8d964599119b420de67ee259434d273651a1a76d',
    profile=dict(controller='manual',device='cpu',seed=7,scenario='reproduction',texture='checker'),
    schedule=dict(ticks=48,actions=[[0,1.0,0.0],[24,1.0,0.5]]),
    run_ids=dict(source='a6effc7912fec337875d13ae69445e43',replay='6c04b9ed22c383fda860fa3b4f8bab13'))
RENDERER=dict(vendor='Mesa',renderer_contains='llvmpipe',version='4.6 (Compatibility Profile) Mesa 26.2.2-arch1.1',
    egl_vendor='Mesa Project',egl_version='1.5',backend='egl')
# Sources the parent runs but never binds into the worker capsule.
PARENT_ONLY={PARENT,'scripts/qualify_puck_cpu_held_runtime.py','scripts/build_puck_python_louvain.py',
    'scripts/install_puck_cpu.py','scripts/acquire_puck_cpu_payloads.py','scripts/admit_puck_retained_installation.py'}
CAPSULE_REQUIRED={WORKER,HELPER,'src/palimpsest/__init__.py','src/palimpsest/puck_held_episode.py',
    'src/palimpsest/held_provenance.py','pyproject.toml','uv.lock','model_manifests/flynn-full-vision.json',
    'upstream/fly-gym/core/__init__.py','upstream/fly-gym/core/astar.py','upstream/fly-gym/environment/__init__.py',
    'upstream/fly-gym/environment/mujoco_model_random_obstacles.xml',
    'upstream/fly-gym/environment/mujoco_two_cam_env_random_obstacles.py'}
EMPTY_SOURCES=('upstream/fly-gym/core/__init__.py','upstream/fly-gym/environment/__init__.py')
DATA=('model_manifests/flynn-full-vision.json','pyproject.toml','uv.lock')
NINE=sorted(['/etc/ld.so.cache',PYTHON,*('/usr/lib/'+n for n in ('ld-linux-x86-64.so.2','libc.so.6','libdl.so.2',
    'libm.so.6','libpthread.so.0','librt.so.1','libutil.so.1'))])
FALSE=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,
    study_authorized=False,executable=False,qualification_claims=[])
EPISODE_CLAIMS=('runtime_qualified','native_authorized','collection_authorized','executable')
NAMESPACE=dict(kind='cpu-episode-characterization-namespace-v1',network_isolated=True,site_readonly=True,
    source_readonly=True,project_hidden=True,private_pycache_empty=True)
MEMBERS={'outer','configuration.json','egl-vendor.json','baseline-before.json','baseline-after.json',
    'request-source.json','request-replay.json','namespace.json','result.json','payload-source','payload-replay',
    *(name+suffix for name in ('probe','source','replay') for suffix in ('-invocation.json','-supervision.json','-logs'))}
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


def require(value,message):
    if not value:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def same(left,right):return canonical(left)==canonical(right)


def finite(value,maximum):return type(value) in (int,float) and math.isfinite(value) and 0<=value<maximum


def hexdigest(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def decode(raw):
    def pairs(rows):
        result={}
        for key,value in rows:
            require(key not in result,'Duplicate JSON key');result[key]=value
        return result
    def constant(_):raise ValueError('Nonfinite JSON constant')
    try:value=json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
    except (UnicodeError,RecursionError,ValueError) as error:raise ValueError('Invalid bounded JSON') from error
    return value


def stamp(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


class Reader:
    """Nofollow reads that remember each file's identity for a final recheck."""
    def __init__(self,deadline):self.deadline=deadline;self.seen={}
    def clock(self):
        if time.monotonic()>=self.deadline:raise TimeoutError('Characterization-04 audit deadline')
    def bytes(self,path,maximum,expected=None,*,single=True,keep=True):
        self.clock();path=Path(path)
        fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
        try:
            before=os.fstat(fd)
            require(stat.S_ISREG(before.st_mode) and (not single or before.st_nlink==1) and before.st_size<=maximum,
                    'Bounded regular file required: '+str(path))
            digest=hashlib.sha256();parts=[];size=0
            while True:
                self.clock();chunk=os.read(fd,MiB)
                if not chunk:break
                size+=len(chunk);require(size<=maximum,'File grew beyond its bound: '+str(path));digest.update(chunk)
                if keep:parts.append(chunk)
            require(size==before.st_size and stamp(os.fstat(fd))==stamp(before),'File changed while read: '+str(path))
        finally:os.close(fd)
        require(stamp(path.lstat())==stamp(before),'File edge changed while read: '+str(path))
        if expected is not None:
            require(size==expected['size_bytes'] and digest.hexdigest()==expected['sha256'],'Pinned bytes differ: '+str(path))
        self.seen[path]=stamp(before)
        return b''.join(parts) if keep else dict(size_bytes=size,sha256=digest.hexdigest())
    def json(self,path,maximum=16*MiB,expected=None):
        raw=self.bytes(path,maximum,expected);return decode(raw),raw
    def recheck(self):
        for path,value in self.seen.items():
            self.clock();require(stamp(path.lstat())==value,'Audited file changed during audit: '+str(path))


def validate_configuration(config,sources_ok=True):
    require(type(config) is dict and set(config)=={'kind','version','output','site_root','sources','inputs','roles',
        'limits','environment','expected_versions','episode','renderer'} and config['kind']==CONFIGURATION_KIND
        and type(config['version']) is int and config['version']==3 and config['output']==OUTPUT
        and config['site_root']==SITE and same(config['roles'],ROLES) and same(config['limits'],LIMITS)
        and same(config['environment'],ENVIRONMENT) and same(config['expected_versions'],VERSIONS)
        and same(config['episode'],EPISODE) and same(config['renderer'],RENDERER),'Exact characterization-04 configuration required')
    for rows,limit in ((config['sources'],MiB),(config['inputs'],32*MiB)):
        require(type(rows) is list and rows==sorted(rows,key=lambda r:r['path']) and len({r['path'] for r in rows})==len(rows),
                'Sorted distinct pins required')
        for row in rows:
            require(type(row) is dict and set(row)=={'path','size_bytes','sha256'} and type(row['size_bytes']) is int
                    and (0 if (rows is config['sources'] and row['path'] in EMPTY_SOURCES) else 1)<=row['size_bytes']<=limit
                    and hexdigest(row['sha256']) and type(row['path']) is str
                    and not row['path'].startswith('/') and '..' not in row['path'].split('/'),'Exact bounded pin required')
    paths={r['path'] for r in config['sources']}
    # The worker capsule: its two scripts, every palimpsest module, upstream fly-gym and three data files.
    capsule={p for p in paths if p in (WORKER,HELPER,*DATA) or p.startswith(('src/palimpsest/','upstream/fly-gym/'))}
    require(PARENT_ONLY<=paths and CAPSULE_REQUIRED<=capsule
            and all(p in CAPSULE_REQUIRED or re.fullmatch(r'src/palimpsest/[a-z_]+\.py',p) for p in capsule)
            and all(re.fullmatch(r'scripts/[a-z_]+\.py',p) for p in paths-capsule),'Exact characterization-04 source closure required')
    require([r['path'] for r in config['inputs']]==sorted(ROLES.values()),'Exact characterization-04 input roles required')
    pins={r['path']:r for r in config['inputs']}
    require(pins[NATIVE_METADATA_PIN['path']]==NATIVE_METADATA_PIN and pins[OBSERVATION02_PIN['path']]==OBSERVATION02_PIN,
            'Native metadata 06 and characterization02 pins required')
    return sorted(capsule)


def validate_native(native,reader):
    keys={'kind','status','root_scope','errors','oversized_native_files','required_missing_names','native_files',
          'aliases','dynamic_leaves','egl_vendor','provenance','limitations'}
    require(type(native) is dict and set(native)==keys and native['kind']=='puck-cpu-characterization-native-metadata-v6'
            and native['status']=='COMPLETE' and native['root_scope']=='installed_shared_objects_interpreter_and_declared_dynamic_leaves'
            and native['errors']==native['oversized_native_files']==native['required_missing_names']==[],'Complete native metadata v6 required')
    files=native['native_files'];require(type(files) is list and 1<=len(files)<=256,'Bounded v6 native files required')
    paths=[]
    for row in files:
        require(type(row) is dict and set(row)=={'path','size_bytes','sha256'} and type(row['path']) is str
                and (row['path'].startswith('/usr/lib/') or row['path'] in ('/usr/bin/ldconfig','/etc/ld.so.cache'))
                and '..' not in row['path'].split('/') and type(row['size_bytes']) is int and 0<=row['size_bytes']<=256*MiB
                and hexdigest(row['sha256']),'Native v6 leaf pin differs');paths.append(row['path'])
        reader.bytes(row['path'],256*MiB,row,single=False,keep=False)
    require(paths==sorted(set(paths)),'Native v6 leaves must be sorted and distinct')
    leaves=native['dynamic_leaves'];require(type(leaves) is list and leaves==sorted(set(leaves)) and set(leaves)<=set(paths),'Declared dynamic leaves differ')
    for path,target in native['aliases']:
        require(os.readlink(path)==target,'Native alias changed: '+path)
    vendor=native['egl_vendor']
    require(type(vendor) is dict and set(vendor)=={'path','size_bytes','sha256','library_path'}
            and vendor['path'].startswith('/usr/share/glvnd/egl_vendor.d/'),'EGL vendor declaration differs')
    raw=reader.bytes(vendor['path'],64*1024,dict(size_bytes=vendor['size_bytes'],sha256=vendor['sha256']))
    require(decode(raw)=={'file_format_version':decode(raw).get('file_format_version'),'ICD':{'library_path':vendor['library_path']}},
            'EGL vendor JSON names another library')
    return set(paths),raw


def baseline_summary(baseline,reader):
    prefix=baseline['python_prefix'];files=[];links=[]
    for directory,names,leaves in os.walk(prefix,followlinks=False):
        reader.clock()
        for name in sorted(names+leaves):
            full=Path(directory)/name;relative=full.relative_to(prefix).as_posix();state=full.lstat()
            if stat.S_ISLNK(state.st_mode):links.append([relative,os.readlink(full)])
            elif stat.S_ISREG(state.st_mode):
                row=reader.bytes(full,256*MiB,single=False,keep=False);files.append([relative,row['size_bytes'],row['sha256']])
            else:require(stat.S_ISDIR(state.st_mode),'Special trusted prefix entry')
    files.sort();links.sort()
    require(files==baseline['files'] and links==baseline['symlinks'],'Trusted interpreter prefix differs')
    digest=sha(json.dumps(dict(files=files,symlinks=links),sort_keys=True,separators=(',',':')).encode())
    require(digest==baseline['prefix_manifest_sha256'],'Trusted prefix manifest differs')
    rows=list(baseline['external_libraries'])+([baseline['bwrap_executable']] if baseline.get('bwrap_executable') else [])
    for row in rows:reader.bytes(row.get('realpath') or row['path'],256*MiB,dict(size_bytes=row['size'],sha256=row['sha256']),single=False,keep=False)
    return dict(prefix_manifest_sha256=digest,regular_file_count=len(files),symlink_count=len(links),
                regular_file_bytes=sum(r[1] for r in files),external_file_count=len(rows))


def site_census(inventory,layout,reader):
    site=ROOT/SITE;expected={r['path']:r for r in inventory['entries']};files={};directories=set()
    for directory,names,leaves in os.walk(site,followlinks=False):
        reader.clock()
        for name in names:
            full=Path(directory)/name;require(stat.S_ISDIR(full.lstat().st_mode),'Site directory type differs')
            directories.add(full.relative_to(site).as_posix())
        for name in leaves:
            full=Path(directory)/name;relative=full.relative_to(site).as_posix()
            require(relative in expected,'Unexpected site file: '+relative)
            files[relative]=dict(path=relative,**reader.bytes(full,2048*MiB,expected[relative],single=False,keep=False))
    require(files==expected and directories==set(layout['predicted_destination_directories'])
            and (len(files),len(directories),sum(r['size_bytes'] for r in files.values()))==SITE_COUNTS,'Accepted site differs')


def request(phase,source_files,distributions):
    paths=dict(output_root='/output',asset_root='/scratch/assets',source_root='/output' if phase=='source' else '/puck/source-run')
    episode=dict(kind='puck-held-public-episode-v1',version=1,phase=phase,expected_versions=VERSIONS,paths=paths,**EPISODE)
    return dict(kind='puck-episode-characterization-request-v1',version=1,site_root=str(ROOT/SITE),source_root='/puck/source',
        output_root='/output',pycache_prefix='/scratch/pycache',environment=ENVIRONMENT,expected_versions=VERSIONS,
        runtime=dict(root=str(Path(PYTHON).parent),files=[INTERPRETER],python_version='3.11.15'),
        source_files=source_files,distributions=distributions,episode=episode)


def namespace(baseline,native,capsule,name,request_sha=None):
    output=ROOT/OUTPUT;phase='source' if name=='probe' else name;prefix=baseline['python_prefix']
    cmd=['/usr/bin/bwrap','--unshare-all','--unshare-user','--as-pid-1','--disable-userns','--die-with-parent','--cap-drop',
         'ALL','--clearenv','--hostname','palimpsest-cpu-episode-observation','--ro-bind',prefix,prefix]
    paths={r['path'] for r in native['native_files']}|{r.get('realpath') or r['path'] for r in baseline['external_libraries']}
    for path in sorted(paths):cmd+=['--ro-bind',path,path]
    aliases=dict(baseline['host_path_aliases'])
    for path,target in native['aliases']:
        require(aliases.get(path,target)==target,'Conflicting host alias');aliases[path]=target
    for path,target in sorted(aliases.items(),key=lambda item:(item[0].count('/'),item[0])):cmd+=['--symlink',target,path]
    cmd+=['--ro-bind',str(ROOT/SITE),str(ROOT/SITE)]
    for path in capsule:cmd+=['--ro-bind',str(ROOT/path),'/puck/source/'+path]
    controls={'egl-vendor.json':output/'egl-vendor.json'}
    if name!='probe':controls['request-'+name+'.json']=output/('request-'+name+'.json')
    for key,host in sorted(controls.items()):cmd+=['--ro-bind',str(host),'/puck/control/'+key]
    if name=='replay':cmd+=['--ro-bind',str(output/'payload-source'),'/puck/source-run']
    cmd+=['--bind',str(output/('payload-'+phase)),'/output','--size',str(LIMITS['scratch_bytes']),'--tmpfs','/scratch']
    for item in ('home','tmp','pycache'):cmd+=['--dir','/scratch/'+item,'--chmod','0700','/scratch/'+item]
    cmd+=['--symlink','scratch/tmp','/tmp','--proc','/proc','--remount-ro','/proc','--dev','/dev','--remount-ro','/dev','--remount-ro','/']
    for key,value in sorted(ENVIRONMENT.items()):cmd+=['--setenv',key,value]
    cmd+=['--chdir','/scratch',PYTHON,'-I','-S','-B','-X','pycache_prefix=/scratch/pycache']
    if name=='probe':return cmd+['-c',PROBE,os.readlink('/proc/self/ns/net'),str(ROOT/SITE),str(ROOT/'docs')]
    return cmd+['/puck/source/'+WORKER,'/puck/control/request-'+name+'.json',request_sha]


def validate_report(report,phase,request_sha,worker_sha,dynamic_leaves):
    keys={'kind','version','status','phase','request_sha256','source_sha256','environment_sha256','python_version',
          'executable_path','pid','ppid','expected_versions','versions','episode_result','process_creation_attempts',
          'import_misses','rechecks','cache','maps','baseline_maps','environment_unchanged','pycache_unchanged',
          'native_cache_dispatch','observation_errors','seconds',*FALSE}
    require(type(report) is dict and set(report)==keys and report['kind']=='puck-episode-characterization-result-v1'
            and type(report['version']) is int and report['version']==1 and report['status']=='observed'
            and report['phase']==phase and report['request_sha256']==request_sha and report['source_sha256']==worker_sha
            and report['environment_sha256']==sha(canonical(ENVIRONMENT)) and same({k:report[k] for k in FALSE},FALSE)
            and same(report['expected_versions'],VERSIONS) and same(report['versions'],VERSIONS)
            and same(report['process_creation_attempts'],dict(count=0,events=[]))
            and report['environment_unchanged'] is True and report['pycache_unchanged'] is True
            and report['observation_errors']==[] and report['executable_path']==PYTHON
            and type(report['python_version']) is str and report['python_version'].startswith('3.11.15 ')
            and type(report['rechecks']) is int and report['rechecks']>=1 and finite(report['seconds'],LIMITS['normal_seconds']),
            'Complete observed '+phase+' report required')
    names=[row.get('name') for row in report['cache']['modules']]
    require(len(names)==len(set(names))<=8192 and all(type(n) is str for n in names)
            and not any(n=='torchvision' or n.startswith('torchvision.') for n in names),'Episode module cache differs')
    require(type(report['maps'].get('images')) is list and type(report['baseline_maps'].get('images')) is list,'Mapped images required')
    baseline=sorted(row.get('path') for row in report['baseline_maps']['images'] if type(row) is dict)
    require([p for p in baseline if p not in set(dynamic_leaves)]==NINE,'Baseline maps must be the nine originals plus declared dynamic leaves')
    dispatch=report['native_cache_dispatch']
    require(type(dispatch) is dict and set(dispatch)=={'events','unattributed','errors'} and dispatch['unattributed']==[]
            and dispatch['errors']==[] and type(dispatch['events']) is list and len(dispatch['events'])<=4096
            and all(type(e) is dict and set(e)=={'cache','producer','phase','added','first','closed'} and type(e['cache']) is str
                    and ((type(e['producer']) is str and e['phase'] in ('native_create','module_exec'))
                         or (e['producer'] is None and e['phase'] is None))
                    and type(e['first']) is bool and type(e['closed']) is bool and type(e['added']) is list
                    and all(type(k) is str for k in e['added']) and e['added']==sorted(set(e['added']))
                    for e in dispatch['events']),'Complete attributed native cache dispatch record required')
    misses=report['import_misses'];require(type(misses) is list and misses==sorted(set(misses)) and len(misses)<=4096,'Import misses differ')
    value=report['episode_result'];ids=EPISODE['run_ids'];ticks=EPISODE['schedule']['ticks']
    common={'kind','version','phase','run_id','source_run_id','ticks_requested','provenance_sha256','versions','bundle',
            *EPISODE_CLAIMS,'qualification_claims'}
    extra={'ticks_completed','final_phase','initial_snapshot_id','renderer'} if phase=='source' else {'replay'}
    require(type(value) is dict and set(value)==common|extra and value['kind']=='puck-held-public-episode-result-v1'
            and type(value['version']) is int and value['version']==1 and value['phase']==phase
            and value['run_id']==ids[phase] and value['source_run_id']==ids['source']
            and type(value['ticks_requested']) is int and value['ticks_requested']==ticks
            and hexdigest(value['provenance_sha256']) and same(value['versions'],VERSIONS)
            and all(value[k] is False for k in EPISODE_CLAIMS) and value['qualification_claims']==[],'Exact '+phase+' episode result required')
    bundle=value['bundle']
    require(type(bundle) is dict and set(bundle)=={'path','size_bytes','sha256'} and bundle['path']==phase+'-bundle.zip'
            and type(bundle['size_bytes']) is int and 0<bundle['size_bytes']<=LIMITS['file_bytes'] and hexdigest(bundle['sha256']),
            'Exact bounded '+phase+' bundle receipt required')
    if phase=='source':
        renderer=value['renderer']
        require(type(value['ticks_completed']) is int and value['ticks_completed']==ticks and type(value['final_phase']) is str
                and type(value['initial_snapshot_id']) is str and 0<len(value['initial_snapshot_id'])<=128
                and type(renderer) is dict and set(renderer)=={'vendor','renderer','version','egl_vendor','egl_version','backend'}
                and all(type(v) is str for v in renderer.values()) and renderer['vendor']==RENDERER['vendor']
                and RENDERER['renderer_contains'] in renderer['renderer']
                and all(renderer[k]==RENDERER[k] for k in ('version','egl_vendor','egl_version','backend')),
                'Source episode must complete every tick on the frozen renderer')
    else:
        replay=value['replay']
        require(type(replay) is dict and set(replay)=={'status','compared_ticks','compared_events','first_divergence'}
                and replay['status']=='passed' and type(replay['compared_ticks']) is int and replay['compared_ticks']==ticks
                and type(replay['compared_events']) is int and replay['compared_events']>0 and replay['first_divergence'] is None,
                'Replay must pass every tick without divergence')


def supervision(value):
    require(type(value) is dict and set(value)=={'failure','finished_monotonic','matching_survivors','pid','returncode',
            'rss_sampling_seconds','sampled_peak_rss_bytes','status'} and value['status']=='completed'
            and type(value['returncode']) is int and value['returncode']==0 and value['failure'] is None
            and value['matching_survivors']==[] and type(value['pid']) is int and value['pid']>0
            and type(value['sampled_peak_rss_bytes']) is int and 0<=value['sampled_peak_rss_bytes']<=LIMITS['rss_bytes'],
            'Normal child supervision required')


def audit(configuration,expected_sha,transport,transport_sha,deadline):
    reader=Reader(deadline);configuration=Path(configuration);transport=Path(transport);output=ROOT/OUTPUT
    require(configuration.is_absolute() and configuration.is_relative_to(ROOT)
            and transport==ROOT/(OUTPUT+'-external-cli-transport.json'),'Exact characterization-04 control paths required')
    raw=reader.bytes(configuration,MiB);config=decode(raw)
    require(sha(raw)==expected_sha and raw==(json.dumps(config,sort_keys=True,indent=2,allow_nan=False)+'\n').encode(),
            'Frozen configuration bytes differ')
    capsule=validate_configuration(config)
    pins={}
    for row in config['sources']+config['inputs']:
        reader.bytes(ROOT/row['path'],32*MiB,row,keep=False);pins[row['path']]=row
    frozen,_=reader.json(ROOT/OBSERVATION02_PIN['path'],MiB,OBSERVATION02_PIN);rows={r['path']:r for r in frozen['inputs']}
    for role in INHERITED:
        require(frozen['roles'].get(role)==ROLES[role] and rows.get(ROLES[role])==pins[ROLES[role]],'Characterization02 pin differs: '+role)
    get=lambda role:reader.json(ROOT/ROLES[role],32*MiB,pins[ROLES[role]])[0]
    old,proof,snapshot=get('accepted_result'),get('accepted_audit'),get('accepted_snapshot')
    require(pins[ROLES['accepted_configuration']]['sha256']==ACCEPTED_SHA and old.get('status')==proof.get('status')=='PASS'
            and old.get('claims',{}).get('package_preparation_accepted') is True and proof.get('package_preparation_accepted') is True
            and old.get('configuration_sha256')==proof.get('verified',{}).get('configuration_sha256')==ACCEPTED_SHA
            and old.get('snapshot_sha256')==pins[ROLES['accepted_snapshot']]['sha256'] and snapshot.get('site_root')==str(ROOT/SITE),
            'Accepted package preparation binding differs')
    inventory,layout,baseline,native=(get(r) for r in ('inventory','layout','baseline','native_metadata'))
    site_census(inventory,layout,reader)
    natives,vendor=validate_native(native,reader)
    summary=baseline_summary(baseline,reader)
    members={entry.name for entry in os.scandir(output)}
    require(members==MEMBERS,'Characterization-04 output members differ: '+str(sorted(members^MEMBERS)))
    require(reader.bytes(output/'configuration.json',MiB)==canonical(config),'Published configuration differs')
    require(reader.bytes(output/'egl-vendor.json',64*1024)==vendor,'Staged EGL vendor JSON differs')
    for name in ('baseline-before.json','baseline-after.json'):
        require(reader.json(output/name)[0]==summary,'Baseline receipt differs: '+name)
    require(reader.json(output/'namespace.json')[0]==NAMESPACE==reader.json(output/'probe-logs/stdout.log')[0],'Namespace probe receipt differs')
    source_files=[pins[path] for path in capsule]
    distributions=[dict(name=w['name'],version=w['version'],root_index=0,metadata_path=w['metadata_path']) for w in layout['wheels']]
    reports={}
    for name in ('probe','source','replay'):
        request_sha=None
        if name!='probe':
            request_raw=reader.bytes(output/('request-'+name+'.json'),MiB)
            require(request_raw==canonical(request(name,source_files,distributions)),'Independent '+name+' request differs')
            request_sha=sha(request_raw)
        invocation=reader.json(output/(name+'-invocation.json'))[0]
        require(invocation==dict(command=namespace(baseline,native,capsule,name,request_sha),configuration_sha256=expected_sha),
                'Independent '+name+' namespace argv differs')
        supervision(reader.json(output/(name+'-supervision.json'))[0])
        reader.bytes(output/(name+'-logs')/'stderr.log',16*MiB)
        if name=='probe':continue
        payload=output/('payload-'+name);report_raw=reader.bytes(payload/'characterization.json',4*MiB);report=decode(report_raw)
        require(report_raw==canonical(report),'Canonical '+name+' report required')
        validate_report(report,name,request_sha,pins[WORKER]['sha256'],native['dynamic_leaves'])
        require(reader.json(output/(name+'-logs')/'stdout.log')[0]==dict(report_sha256=sha(report_raw),report_bytes=len(report_raw),
                status='observed'),'Worker publication receipt differs: '+name)
        bundle=report['episode_result']['bundle']
        reader.bytes(payload/bundle['path'],LIMITS['file_bytes'],bundle,keep=False)
        run_id=EPISODE['run_ids'][name]
        require({e.name for e in os.scandir(payload)}=={'characterization.json',bundle['path'],run_id}
                and stat.S_ISDIR((payload/run_id).lstat().st_mode),'Payload members differ: '+name)
        reports[name]=(report,sha(report_raw))
    source,replay=reports['source'][0],reports['replay'][0]
    require(source['episode_result']['provenance_sha256']==replay['episode_result']['provenance_sha256'],'Held provenance differs between phases')
    result_raw=reader.bytes(output/'result.json',MiB);result=decode(result_raw)
    mapped=sorted({image['path'] for report,_ in reports.values() for image in report['maps']['images']}&natives)
    expected=dict(FALSE,kind='puck-cpu-characterization-outcome-v3',version=3,status='observed',configuration_sha256=expected_sha,
        source_report_sha256=reports['source'][1],replay_report_sha256=reports['replay'][1],versions=VERSIONS,
        renderer=source['episode_result']['renderer'],ticks_completed=EPISODE['schedule']['ticks'],
        replay=replay['episode_result']['replay'],process_creation_attempts=0,mapped_native_files=mapped,
        namespace_probe_completed=True,accepted_package_preparation_preserved=True,worker_supervision_status='completed')
    closure=result.get('closure',{})
    require(result_raw==canonical(result) and set(result)==set(expected)|{'closure','elapsed_seconds','sampled_parent_peak_rss_bytes'}
            and all(same(result[k],v) for k,v in expected.items()) and finite(result['elapsed_seconds'],LIMITS['normal_seconds'])
            and type(result['sampled_parent_peak_rss_bytes']) is int
            and closure.get('active_children')==[] and closure.get('active_non_main_threads')==[]
            and closure.get('all_handles_closed') is True and closure.get('all_receipts_fsynced') is True
            and type(closure.get('fd_count_before')) is int and closure.get('fd_count_after')==closure['fd_count_before'],
            'Observed characterization-04 parent outcome required')
    traw=reader.bytes(transport,64*1024);observed=decode(traw)
    require(sha(traw)==transport_sha and traw==canonical(observed),'Authenticated canonical transport required')
    streams={name:Path(OUTPUT+'-external-cli.'+name) for name in ('stdout','stderr')}
    require(type(observed) is dict and set(observed)=={'kind','configuration_sha256','command','observed_returncode','elapsed_seconds',
            'timed_out','stdout','stderr'} and observed['kind']=='puck-cpu-episode-characterization-cli-transport-v1'
            and observed['configuration_sha256']==expected_sha and observed['command']==[PYTHON,'-I','-S','-B',str(ROOT/PARENT),
            '--configuration',str(configuration),'--sha256',expected_sha] and type(observed['observed_returncode']) is int
            and observed['observed_returncode']==0 and observed['timed_out'] is False and finite(observed['elapsed_seconds'],420)
            and all(observed[name]['path']==str(streams[name]) for name in streams),'Normal external transport required')
    for name,path in streams.items():
        payload=reader.bytes(ROOT/path,16*MiB,dict(size_bytes=observed[name]['size_bytes'],sha256=observed[name]['sha256']))
        require(stat.S_IMODE((ROOT/path).lstat().st_mode)==0o600,'Private external stream required')
        if name=='stdout':require(decode(payload)==result,'Observed parent stdout differs from the saved outcome')
    reader.recheck()
    return dict(configuration_sha256=expected_sha,result_sha256=sha(result_raw),source_report_sha256=reports['source'][1],
        replay_report_sha256=reports['replay'][1],transport_sha256=transport_sha,native_metadata_sha256=NATIVE_METADATA_PIN['sha256'],
        source_pins=len(config['sources']),input_pins=len(config['inputs']),capsule_files=len(capsule),
        native_files=len(natives),mapped_native_files=mapped,site_file_count=SITE_COUNTS[0],baseline=summary,
        provenance_sha256=source['episode_result']['provenance_sha256'],renderer=source['episode_result']['renderer'],
        replay=replay['episode_result']['replay'],import_misses=sorted(set(source['import_misses'])|set(replay['import_misses'])))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('configuration','sha256','transport','transport-sha256','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();started=time.monotonic()
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,310)
    report=dict(FALSE,kind=KIND,version=1,status='FAIL',configuration_sha256=args.sha256,transport_sha256=args.transport_sha256,
                target_code_executed_by_auditor=False,auditor_source_sha256=sha(Path(__file__).read_bytes()))
    try:
        try:
            require(Path(sys.executable).resolve()==Path(PYTHON) and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
                    'Original isolated audit interpreter required')
            for digest in (args.sha256,args.transport_sha256):require(hexdigest(digest),'Explicit lowercase audit SHA required')
            report['verified']=audit(args.configuration,args.sha256,args.transport,args.transport_sha256,started+300)
            report['status']='PASS'
        except Exception as error:report.update(error_type=type(error).__name__,error=str(error)[:2048])
        report['elapsed_seconds']=time.monotonic()-started
        raw=canonical(report);output=Path(args.output)
        fd=os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            view=memoryview(raw)
            while view:view=view[os.write(fd,view):]
            os.fsync(fd)
        finally:os.close(fd)
        print(raw.decode(),end='',flush=True)
        return 0 if report['status']=='PASS' else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
