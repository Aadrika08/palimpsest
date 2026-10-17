"""Independent byte audit of one allocation-16 held episode; never imports target code.

Stdlib only, plus the stdlib bundle/npz validator next to this file. It binds
the frozen configuration and every pin, preparation04's PASS v15 acceptance
(by the pinned auditor bytes), the v6 native leaves, the EGL vendor JSON and the
trusted prefix; reconstructs both v4 registrations and both episode namespace
argvs independently; checks supervision and bootstrap receipts (zero process
creation), both recordings (contiguous published chunks, one registered tick-0
snapshot, every camera frame a non-constant uint8[128,128,3]), the replay
comparison (cameras and integers exact, floats within 1e-6), the replay report,
both bundles against their run directories, the result and the transport. PASS
grants no runtime, renderer, collection or study authority.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import signal
import stat
import struct
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
MiB=1024**2
KIND='puck-cpu-held-episode-independent-audit-v1'
CONFIGURATION_KIND='puck-cpu-held-episode-allocation-v16'
OUTPUT='runs/puck-cpu-held-episode-16'
PREPARATION04='runs/puck-cpu-held-preparation-04'
PARENT='scripts/run_puck_cpu_held_episode.py'
BOOTSTRAP='scripts/puck_worker_bootstrap.py'
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
INTERPRETER=dict(path=PYTHON,size_bytes=21662864,sha256='572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a')
# The independent auditor bytes that must have accepted preparation04.
PREPARATION04_AUDITOR_SHA256='972ef46c0e94c24e234577b956ec2bf65730095de7ad05871dcedddb9e07eb47'
VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',mujoco='3.3.6',gymnasium='1.2.1')
ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',
    HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/puck/source',PATH='/nonexistent',TZ='UTC',
    CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',
    OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0',
    PYGLFW_LIBRARY='/puck/staged/inputs/root-0000/glfw/x11/libglfw.so',MESA_SHADER_CACHE_DISABLE='true',
    PYGAME_HIDE_SUPPORT_PROMPT='hide',__EGL_VENDOR_LIBRARY_FILENAMES='/puck/control/egl-vendor.json')
LIMITS=dict(normal_seconds=720,child_hard_seconds=735,hard_seconds=750,
    rss_bytes=2048*MiB,address_space_bytes=8192*MiB,output_bytes=64*MiB,
    scratch_bytes=64*MiB,file_bytes=16*MiB,min_free_bytes=4096*MiB,
    min_available_ram_bytes=2048*MiB,min_tmpfs_free_bytes=256*MiB,max_processes=3,max_fds=40000)
NEGATIVE_IMPORTS=sorted(['OpenGL_accelerate','accimage','av','backports_abc','colorama','defusedxml','dill','flint',
    'fx2trt_oss','gmpy','gmpy2','hypothesis','monkeytype','numpy._distributor_init_local','onnx','onnx_tf',
    'onnxruntime','opt_einsum','org','pydot','pynvml','tabulate','tensorflow','tensorrt','torch._rocm_init',
    'torch2trt','torchdistx','tqdm','tree','triton','tvm','xarray',
    'cffi','charset_normalizer','cython','glfw_preview','scikits','scipy._distributor_init_local',
    'scipy.linalg._cblas','scipy.linalg._clapack','scipy.linalg._fblas_64','scipy.linalg._flapack_64'])
HIDDEN_IMPORTS=['networkx','pandas','sklearn','torch.utils._cxx_pytree']
SYSCONFIGDATA=dict(name='_sysconfigdata__linux_x86_64-linux-gnu',
    path=str(Path(PYTHON).parent.parent/'lib/python3.11/_sysconfigdata__linux_x86_64-linux-gnu.py'),
    size_bytes=42136,sha256='afa518f786b425fc598b11adbf60d667bf7fe7f5f0662a0cd6bbf6f3e25c8d21')
EPISODE=dict(upstream_commit='8d964599119b420de67ee259434d273651a1a76d',
    profile=dict(controller='manual',device='cpu',seed=7,scenario='reproduction',texture='checker'),
    schedule=dict(ticks=48,actions=[[0,1.0,0.0],[24,1.0,0.5]]))
CHARACTERIZATION_RUN_IDS=('a6effc7912fec337875d13ae69445e43','6c04b9ed22c383fda860fa3b4f8bab13')
RENDERER=dict(vendor='Mesa',renderer_contains='llvmpipe',version='4.6 (Compatibility Profile) Mesa 26.2.2-arch1.1',
    egl_vendor='Mesa Project',egl_version='1.5',backend='egl')
CLAIMS=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,
    study_authorized=False,executable=False,qualification_claims=[])
EPISODE_CLAIMS=('runtime_qualified','native_authorized','collection_authorized','executable')
PHASES=('source','replay')
NINE=['/etc/ld.so.cache',PYTHON,*('/usr/lib/'+n for n in ('ld-linux-x86-64.so.2','libc.so.6','libdl.so.2','libm.so.6',
    'libpthread.so.0','librt.so.1','libutil.so.1'))]
PHYSICAL=('cam_left','cam_right','raw_cam_left','raw_cam_right','sensors','action','control','pose','next_pose',
          'reward','simulation_time','eyes','revision')
CAMERAS=('cam_left','cam_right','raw_cam_left','raw_cam_right')
FRAME=(128,128,3)
ATOL=RTOL=1e-6
# Independent copy of the held provenance (doctor-schema) record definition.
UPSTREAM='upstream/fly-gym/'
SIMULATION_DISTRIBUTIONS=('torch','torchvision','numpy','scipy','pandas','scikit-learn','mujoco','gymnasium','glfw',
    'opencv-python','matplotlib','seaborn','networkx','python-louvain','py7zr')
NOT_INSPECTED='not inspected in the held runtime'
MEMBERS={'outer','configuration.json','resource-admission.json','baseline-before.json','baseline-after.json','control',
    'logs-source','logs-replay','payload-source','payload-replay','result.json',
    *(phase+suffix for phase in PHASES for suffix in ('-invocation.json','-supervision.json'))}
CONTROL={'dependencies.json','egl-vendor.json','worker-registration-source.json','worker-registration-replay.json'}
LAUNCHER='import os,sys;os.setsid();os.execv(sys.argv[1],sys.argv[1:])'


def require(value,message):
    if not value:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value,lf=True):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+('\n' if lf else '')).encode()


def finite(value,maximum):return type(value) in (int,float) and math.isfinite(value) and 0<=value<maximum


def hexdigest(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def decode(raw):
    def pairs(rows):
        result={}
        for key,value in rows:
            require(key not in result,'Duplicate JSON key');result[key]=value
        return result
    def constant(_):raise ValueError('Nonfinite JSON constant')
    try:return json.loads(raw,object_pairs_hook=pairs,parse_constant=constant)
    except (UnicodeError,RecursionError,ValueError) as error:raise ValueError('Invalid bounded JSON') from error


def stamp(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)


class Reader:
    def __init__(self,deadline):self.deadline=deadline;self.seen={}
    def clock(self):
        if time.monotonic()>=self.deadline:raise TimeoutError('Held episode audit deadline')
    def bytes(self,path,maximum,expected=None,*,single=True,keep=True):
        self.clock();path=Path(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
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
        for path,value in self.seen.items():self.clock();require(stamp(path.lstat())==value,'Audited file changed: '+str(path))


def validator():
    spec=importlib.util.spec_from_file_location('_episode_bundle_validator',Path(__file__).resolve().parent/'validate_palimpsest_bundle.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def worker_files(sources):
    """The held worker closure, independently: the bootstrap, palimpsest, upstream fly-gym and the three data files."""
    return [r for r in sources if r['path'] in (BOOTSTRAP,'model_manifests/flynn-full-vision.json','pyproject.toml','uv.lock')
            or r['path'].startswith(('src/palimpsest/','upstream/fly-gym/'))]


def modules(files):
    result=[]
    for row in files:
        path=row['path']
        if path==BOOTSTRAP or not path.endswith('.py'):continue
        name=(path[4:] if path.startswith('src/') else path[len('upstream/fly-gym/'):])[:-3].replace('/','.')
        result.append(dict(name=name[:-9] if name.endswith('.__init__') else name,path=path))
    return result


def validate_configuration(config,prior):
    keys={'kind','version','allocation_id','root','stage_parent','sources','inputs','interpreter','environment',
          'expected_versions','limits','negative_imports','hidden_imports','claims','preparation_acceptance','run_ids'}
    require(type(config) is dict and set(config)==keys and config['kind']==CONFIGURATION_KIND and type(config['version']) is int
            and config['version']==16 and type(config['allocation_id']) is int and config['allocation_id']==16
            and config['root']==str(ROOT) and config['interpreter']==INTERPRETER and canonical(config['environment'])==canonical(ENVIRONMENT)
            and config['expected_versions']==VERSIONS and canonical(config['limits'])==canonical(LIMITS)
            and canonical(config['claims'])==canonical(CLAIMS) and config['negative_imports']==NEGATIVE_IMPORTS
            and config['hidden_imports']==HIDDEN_IMPORTS
            and re.fullmatch(r'/tmp/palimpsest-puck-cpu-held-04(?:-[A-Za-z0-9_-]+)?',config['stage_parent'] or '') is not None,
            'Exact allocation-16 configuration required')
    ids=config['run_ids']
    require(type(ids) is dict and set(ids)==set(PHASES) and all(type(v) is str and re.fullmatch('[0-9a-f]{32}',v) for v in ids.values())
            and ids['source']!=ids['replay'] and not set(ids.values())&set(CHARACTERIZATION_RUN_IDS),'Two fresh run ids required')
    rows={r['path']:r for r in config['sources']}
    require([r['path'] for r in config['sources']]==sorted(rows) and all(rows.get(r['path'])==r for r in prior['sources'])
            and set(rows)-{r['path'] for r in prior['sources']}=={PARENT},'Allocation-16 sources must be preparation04 sources plus its parent')
    require(prior['inputs']==config['inputs'] and prior['stage_parent']==config['stage_parent'] and prior['root']==config['root']
            and prior.get('kind')=='puck-cpu-held-runtime-allocation-v15' and prior.get('phase')=='prepare'
            and prior.get('expected_versions')==VERSIONS,'Allocation 16 must bind preparation04 data exactly')


def validate_acceptance(config,reader):
    acceptance=config['preparation_acceptance'];require(set(acceptance)=={'configuration','result','independent_audit',
        'externally_observed_auditor_cli'} and acceptance['result']['path']==PREPARATION04+'/result.json','Preparation04 acceptance pins differ')
    prior,prior_raw=reader.json(ROOT/acceptance['configuration']['path'],MiB,acceptance['configuration'])
    prep,prep_raw=reader.json(ROOT/acceptance['result']['path'],MiB,acceptance['result'])
    audit,audit_raw=reader.json(ROOT/acceptance['independent_audit']['path'],MiB,acceptance['independent_audit'])
    cli,_=reader.json(ROOT/acceptance['externally_observed_auditor_cli']['path'],MiB,acceptance['externally_observed_auditor_cli'])
    require(prior_raw==canonical(prior) and prep_raw==canonical(prep),'Canonical preparation04 bytes required')
    require(reader.bytes(ROOT/PREPARATION04/'configuration.json',MiB)==prior_raw,'Retained preparation04 configuration differs')
    false=lambda v:all(v.get(k) is False for k in CLAIMS if k!='qualification_claims') and v.get('qualification_claims')==[]
    require(prep.get('kind')=='puck-cpu-held-runtime-outcome-v15' and prep.get('status')=='prepared' and false(prep)
            and prep.get('configuration_sha256')==acceptance['configuration']['sha256'] and prep.get('stage_parent')==config['stage_parent']
            and not {'error','error_type'}&set(prep),'Preparation04 must be prepared')
    require(audit.get('kind')=='puck-cpu-held-runtime-independent-audit-v15' and audit.get('status')=='PASS' and false(audit)
            and audit.get('auditor_source_sha256')==PREPARATION04_AUDITOR_SHA256
            and audit.get('configuration_sha256')==acceptance['configuration']['sha256']
            and audit.get('result_sha256')==acceptance['result']['sha256']
            and audit.get('dependencies_sha256')==prep.get('dependencies',{}).get('sha256'),'Preparation04 independent audit binding differs')
    require(cli.get('kind')=='externally-observed-cpu-auditor-cli-v1' and cli.get('observed_returncode')==0
            and cli.get('published',{}).get('sha256')==cli.get('stdout',{}).get('sha256')==acceptance['independent_audit']['sha256']
            and cli.get('stderr',{}).get('size_bytes')==0,'Preparation04 auditor CLI did not return normally')
    return prior,prep


def native_set(native,reader):
    require(native.get('kind')=='puck-cpu-characterization-native-metadata-v6' and native.get('status')=='COMPLETE'
            and type(native.get('native_files')) is list and len(native['native_files'])<=256,'Native metadata v6 required')
    for row in native['native_files']:reader.bytes(row['path'],256*MiB,row,single=False,keep=False)
    for path,target in native['aliases']:require(os.readlink(path)==target,'Native alias changed: '+path)
    vendor=native['egl_vendor']
    return reader.bytes(vendor['path'],64*1024,dict(size_bytes=vendor['size_bytes'],sha256=vendor['sha256']))


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


def registration(config,phase,files,dependency_raw,bootstrap_raw):
    seeds=[n.value for n in ast.parse(bootstrap_raw).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='SEED' for t in n.targets)]
    require(len(seeds)==1,'Frozen bootstrap SEED missing');seed=ast.literal_eval(seeds[0])
    bootstrap=next(r for r in files if r['path']==BOOTSTRAP);path='/puck/control/worker-registration-'+phase+'.json'
    prefix=[PYTHON,'-I','-B','-S','-c',seed,'/puck/source/'+BOOTSTRAP,bootstrap['sha256'],path]
    episode=dict(kind='puck-held-public-episode-v1',version=1,phase=phase,expected_versions=VERSIONS,
        stdlib_cache_aliases={'__mp_main__':'__main__'},negative_imports=NEGATIVE_IMPORTS,hidden_imports=HIDDEN_IMPORTS,
        stdlib_exception=SYSCONFIGDATA,profile=EPISODE['profile'],schedule=EPISODE['schedule'],run_ids=config['run_ids'],
        paths=dict(output_root='/output',source_root='/output' if phase=='source' else '/puck/source-run',asset_root='/scratch/assets'),
        upstream_commit=EPISODE['upstream_commit'])
    value=dict(kind='puck-worker-source-bootstrap-v4',version=4,source_root='/puck/source',source_files=files,modules=modules(files),
        namespaces=[],runtime=dict(root=str(Path(PYTHON).parent),files=[{k:INTERPRETER[k] for k in ('size_bytes','sha256')}|{'path':'python3.11'}],
        python_version='3.11.15'),environment=ENVIRONMENT,cwd='/puck/source',argv_prefix=prefix,
        dependencies=dict(path='/puck/control/dependencies.json',size_bytes=len(dependency_raw),sha256=sha(dependency_raw)),
        episode=episode,qualification_claims=[],executable=False,deadline_seconds=360)
    raw=canonical(value,False)
    return value,raw,[PYTHON,'-I','-B','-S','-c',LAUNCHER]+prefix+[sha(raw)]


def namespace(config,baseline,native,observation,phase,files,worker_command):
    prefix=baseline['python_prefix'];paths=sorted(r['path'] for r in native['native_files']);stage=config['stage_parent']
    observed=sorted(r['path'] for r in observation['baseline_maps']['images'])
    nine=[p for p in observed if p not in set(native['dynamic_leaves'])]
    require(nine==sorted(NINE),'Exact original nine baseline images required')
    aliases={}
    for rows in (baseline['host_path_aliases'],native['aliases']):
        for path,target in rows:require(aliases.get(path,target)==target,'Conflicting alias');aliases[path]=target
    output=ROOT/OUTPUT
    cmd=['/usr/bin/bwrap','--unshare-all','--unshare-user','--disable-userns','--die-with-parent','--cap-drop','ALL','--clearenv',
         '--hostname','palimpsest-cpu-held','--ro-bind',prefix,prefix]
    for path in paths:
        origin=path if path in nine else stage+'/inputs/'+('root-0001' if path.startswith('/usr/') else 'root-0002')+'/'+path[5:]
        cmd+=['--ro-bind',origin,path]
    for path,target in sorted(aliases.items(),key=lambda item:(item[0].count('/'),item[0])):cmd+=['--symlink',target,path]
    for row in files:cmd+=['--ro-bind',str(ROOT/PREPARATION04/'parent-source')+'/'+row['path'],'/puck/source/'+row['path']]
    cmd+=['--ro-bind',str(output/'control'),'/puck/control','--ro-bind',stage+'/inputs','/puck/staged/inputs']
    if phase=='replay':cmd+=['--ro-bind',str(output/'payload-source'),'/puck/source-run']
    cmd+=['--bind',str(output/('payload-'+phase)),'/output','--size',str(LIMITS['scratch_bytes']),'--tmpfs','/scratch']
    for name in ('home','tmp','pycache'):cmd+=['--dir','/scratch/'+name,'--chmod','0700','/scratch/'+name]
    cmd+=['--symlink','scratch/tmp','/tmp','--proc','/proc','--remount-ro','/proc','--dev','/dev','--remount-ro','/dev','--remount-ro','/']
    for key,value in sorted(ENVIRONMENT.items()):cmd+=['--setenv',key,value]
    return cmd+['--chdir','/puck/source']+worker_command


def provenance_report(registration,distributions,pyproject_raw):
    """The held provenance record recomputed from the registration, dependency rows and pinned pyproject bytes."""
    import tomllib
    compact=lambda value:json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()
    normalized=lambda name:re.sub(r'[-_.]+','-',name).lower()
    runtime=registration['runtime'];pin=runtime['files'][0];episode=registration['episode'];environment=registration['environment']
    interpreter=dict(path=str(PurePosixPath(runtime['root'])/pin['path']),size_bytes=pin['size_bytes'],sha256=pin['sha256'],
                     python_version=runtime['python_version'])
    rows=[dict(path=r['path'][len(UPSTREAM):],size_bytes=r['size_bytes'],sha256=r['sha256'])
          for r in registration['source_files'] if r['path'].startswith(UPSTREAM)]
    require(rows and [r['path'] for r in rows]==sorted({r['path'] for r in rows}),'Registered upstream rows required')
    versions={}
    for row in distributions:
        require(normalized(row['name']) not in versions,'Registered distributions must be unique');versions[normalized(row['name'])]=row['version']
    lock=[r['sha256'] for r in registration['source_files'] if r['path']=='uv.lock'];require(len(lock)==1,'Registered uv.lock required')
    version=tomllib.loads(pyproject_raw.decode('utf-8'))['project']['version'];python=interpreter['python_version']
    checks=[dict(name='python',status='ok' if python.startswith('3.11.') else 'error',
                 detail=dict(version=python,executable=interpreter['path'],required='Python 3.11; uv sync --extra simulation')),
            dict(name='platform',status='info',detail=dict(platform=NOT_INSPECTED,machine=NOT_INSPECTED)),
            dict(name='dependency:palimpsest',status='ok',detail=version)]
    for name in SIMULATION_DISTRIBUTIONS:
        found=versions.get(normalized(name))
        checks.append(dict(name='dependency:'+name,status='missing',detail='Not a registered held distribution') if found is None
                      else dict(name='dependency:'+name,status='ok',detail=found))
    commit=episode['upstream_commit']
    checks+=[dict(name='upstream',status='ok' if commit==EPISODE['upstream_commit'] else 'error',
                  detail=dict(path=str(PurePosixPath(registration['source_root'])/UPSTREAM.rstrip('/')),commit=commit,
                              expected_commit=EPISODE['upstream_commit'],dirty=False,changes=[])),
             dict(name='ram',status='info',detail=NOT_INSPECTED),dict(name='disk',status='info',detail=NOT_INSPECTED),
             dict(name='gpu',status='info',detail=dict(devices=[],source=NOT_INSPECTED)),
             dict(name='assets',status='info',detail=NOT_INSPECTED),
             dict(name='renderer',status='info',detail=dict(requested_backend=environment.get('MUJOCO_GL','platform default'),
                  backend_selection='explicit MUJOCO_GL' if 'MUJOCO_GL' in environment else 'MuJoCo platform default',
                  probed=False,command='palimpsest doctor --probe-renderer')),
             dict(name='hardware',status='info',detail='Physical hardware has not been assessed; simulation setup does not qualify a rover'),
             dict(name='held-provenance',status='info',detail=dict(kind='puck-held-provenance-v1',interpreter=interpreter,
                  upstream=dict(commit=commit,file_count=len(rows),files_sha256=sha(compact(rows))),
                  distributions_sha256=sha(compact(sorted(versions.items()))),environment_sha256=sha(compact(environment)),
                  lock_sha256=lock[0],scope='authenticated registration pins; '+NOT_INSPECTED+' host'))]
    report=dict(schema_version=1,checks=checks,ready=all(c['status'] not in ('missing','error') for c in checks))
    return report,compact(report)


def validate_entry(value,config,phase):
    ids=config['run_ids'];ticks=EPISODE['schedule']['ticks']
    keys={'kind','version','phase','run_id','source_run_id','ticks_requested','provenance_sha256','versions','bundle',*EPISODE_CLAIMS,
          'qualification_claims'}|({'ticks_completed','final_phase','initial_snapshot_id','renderer'} if phase=='source' else {'replay'})
    require(type(value) is dict and set(value)==keys and value['kind']=='puck-held-public-episode-result-v1' and value['version']==1
            and value['phase']==phase and value['run_id']==ids[phase] and value['source_run_id']==ids['source']
            and value['ticks_requested']==ticks and hexdigest(value['provenance_sha256']) and value['versions']==VERSIONS
            and all(value[k] is False for k in EPISODE_CLAIMS) and value['qualification_claims']==[],'Exact '+phase+' episode result required')
    if phase=='source':
        renderer=value['renderer']
        require(value['ticks_completed']==ticks and type(renderer) is dict and renderer.get('vendor')==RENDERER['vendor']
                and RENDERER['renderer_contains'] in str(renderer.get('renderer'))
                and all(renderer.get(k)==RENDERER[k] for k in ('version','egl_vendor','egl_version','backend')),
                'Source episode must complete every tick on the frozen renderer')
    else:
        require(value['replay']==dict(status='passed',compared_ticks=ticks,compared_events=value['replay'].get('compared_events'),
                first_divergence=None) and type(value['replay']['compared_events']) is int and value['replay']['compared_events']>0,
                'Replay must pass every tick')


def recording(run,v,reader,ticks,provenance):
    """Validate one run's published recording; return per-tick array rows and the registered initial snapshot."""
    manifest,_=reader.json(run/'recording/manifest.json',MiB)
    require(manifest.get('status')=='completed' and manifest.get('recording_format')=='palimpsest-npz-v1'
            and manifest.get('recorded_ticks')==ticks and manifest.get('run_id')==run.name,'Completed recording of every tick required')
    raw=reader.bytes(run/'recording/events.jsonl',16*MiB);require(raw.endswith(b'\n'),'Terminal recording event stream required')
    events=[decode(line) for line in raw.splitlines()]
    require(all(type(e) is dict and e.get('sequence')==i and type(e.get('kind')) is str for i,e in enumerate(events))
            and manifest.get('recorded_events')==len(events),'Recording events must be contiguous')
    chunks=[e for e in events if e['kind']=='chunk'];rows=[];schema=None
    require(len(chunks)==manifest.get('recorded_chunks')>0,'Recording must publish its chunks')
    for index,event in enumerate(chunks):
        require(event.get('path')=='chunks/%06d.npz' % index and event.get('start')==len(rows) and 1<=event.get('count',0)<=32
                and type(event.get('episode')) is int and event['episode']==chunks[0].get('episode'),'Chunk path/range differs')
        payload=reader.bytes(run/'recording'/event['path'],128*MiB);require(sha(payload)==event.get('sha256'),'Chunk hash differs: '+event['path'])
        arrays=v.read_npz(payload);require(schema is None or event.get('arrays')==schema,'Recording schema changed');schema=event.get('arrays')
        require(set(arrays)==set(schema) and all(arrays[n].descr==schema[n]['dtype'] and list(arrays[n].shape)==[event['count'],*schema[n]['shape']]
                for n in arrays),'Chunk arrays differ from their declared schema')
        for name in CAMERAS:
            require(name in arrays and arrays[name].descr=='|u1' and arrays[name].shape[1:]==FRAME,'Camera '+name+' must be uint8[128,128,3]')
            for frame in arrays[name].rows():require(min(frame)!=max(frame),'Constant '+name+' frame refused')
        split={name:array.rows() for name,array in arrays.items()}
        for offset in range(event['count']):rows.append({name:(arrays[name],split[name][offset]) for name in arrays})
    require(len(rows)==ticks,'Recorded ticks differ from the schedule')
    diagnostics=[e for e in events if e['kind']=='diagnostics']
    require(len(diagnostics)==1 and diagnostics[0].get('run_id')==run.name and diagnostics[0].get('report')==provenance,
            'The '+run.name+' diagnostics event differs from the independently recomputed held provenance')
    # One step per tick; the action set at 0 and N//2 is held between.
    actions=EPISODE['schedule']['actions']
    for tick,row in enumerate(rows):
        array,raw=row['action'];expected=[values for start,*values in actions if start<=tick][-1]
        require(array.descr in ('<f8','<f4') and array.shape[1:]==(2,),'Recorded action must be two floats')
        code='d' if array.descr=='<f8' else 'f'
        require(list(struct.unpack('<2'+code,raw))==expected,'Recorded action differs from the frozen schedule at tick %d' % tick)
    snapshots=[e for e in events if e['kind']=='snapshot_registered']
    require(len(snapshots)==1 and snapshots[0].get('initial') is True and snapshots[0].get('filename')=='initial.snp','Exactly one initial snapshot required')
    record=snapshots[0];index,_=reader.json(run/'snapshots/index.json',MiB);entry=index.get('snapshots',{}).get(record['snapshot_id'],{})
    require(index.get('version')==1 and list(index.get('snapshots',{}))==[record['snapshot_id']] and type(entry) is dict
            and all(entry.get(k)==record[k] for k in ('filename','snapshot_id','sha256','initial')),'Snapshot index differs from its registration event')
    require(sha(reader.bytes(run/'snapshots/initial.snp',16*MiB))==record['sha256'],'Initial snapshot hash differs')
    return rows,record


def compare(source,replay):
    """Actions-mode comparison: cameras and integers exact, floats within 1e-6."""
    for tick,(left,right) in enumerate(zip(source,replay,strict=True)):
        for name in PHYSICAL:
            if name not in left and name not in right:continue
            require(name in left and name in right,'Replay lacks recorded field '+name)
            (a,araw),(b,braw)=left[name],right[name]
            require(a.descr==b.descr and a.shape[1:]==b.shape[1:],'Replay field type differs: '+name)
            if a.descr in ('<f4','<f8'):
                code='f' if a.descr=='<f4' else 'd';n=len(araw)//struct.calcsize(code)
                for x,y in zip(struct.unpack('<%d%s'%(n,code),araw),struct.unpack('<%d%s'%(n,code),braw)):
                    require(math.isfinite(x) and math.isfinite(y) and abs(x-y)<=ATOL+RTOL*abs(x),
                            'Replay diverged at tick %d field %s' % (tick,name))
            else:require(araw==braw,'Replay diverged at tick %d field %s' % (tick,name))


def audit(configuration,expected_sha,transport,transport_sha,deadline):
    reader=Reader(deadline);v=validator();output=ROOT/OUTPUT;configuration=Path(configuration);transport=Path(transport)
    raw=reader.bytes(configuration,MiB);config=decode(raw)
    require(sha(raw)==expected_sha and raw==canonical(config),'Frozen canonical configuration bytes differ')
    prior,prep=validate_acceptance(config,reader)
    validate_configuration(config,prior)
    pins={}
    for row in config['sources']+list(config['inputs'].values()):reader.bytes(ROOT/row['path'],32*MiB,row,single=False,keep=False);pins[row['path']]=row
    get=lambda role:reader.json(ROOT/config['inputs'][role]['path'],32*MiB,config['inputs'][role])[0]
    baseline,native,observation=get('baseline'),get('native'),get('observation_report')
    vendor=native_set(native,reader);summary=baseline_summary(baseline,reader)
    members={e.name for e in os.scandir(output)}
    require(members==MEMBERS,'Allocation-16 output members differ: '+str(sorted(members^MEMBERS)))
    require({e.name for e in os.scandir(output/'control')}==CONTROL,'Allocation-16 control members differ')
    require(reader.bytes(output/'configuration.json',MiB)==canonical(config),'Published configuration differs')
    for name in ('baseline-before.json','baseline-after.json'):require(reader.json(output/name)[0]==summary,'Baseline receipt differs: '+name)
    require(reader.bytes(output/'control/egl-vendor.json',64*1024)==vendor,'Staged EGL vendor JSON differs')
    dependency_raw=reader.bytes(output/'control/dependencies.json',16*MiB,prep['dependencies'])
    require(reader.bytes(ROOT/PREPARATION04/'payload/dependencies.json',16*MiB)==dependency_raw,'Prepared dependency registration differs')
    dependencies=decode(dependency_raw)
    for row in prep['staged_roots']:
        state=os.stat(config['stage_parent']+'/inputs/root-%04d' % row['root_index'],follow_symlinks=False)
        require((state.st_dev,state.st_ino)==(row['device'],row['inode']) and stat.S_IMODE(state.st_mode)==0o700,'Staged root changed')
    files=worker_files(config['sources']);bootstrap=reader.bytes(ROOT/BOOTSTRAP,MiB,pins[BOOTSTRAP])
    for row in files:reader.bytes(ROOT/PREPARATION04/'parent-source'/row['path'],MiB,row,keep=False)
    declared=set(NEGATIVE_IMPORTS)|set(HIDDEN_IMPORTS);count=sum(len(r['files']) for r in dependencies['roots'])
    total=sum(f['size_bytes'] for r in dependencies['roots'] for f in r['files']);entries={};recordings={};reports={}
    for phase in PHASES:
        registration_value,registration_raw,worker_command=registration(config,phase,files,dependency_raw,bootstrap)
        expected_report,expected_raw=provenance_report(registration_value,dependencies['distributions'],
                                                       reader.bytes(ROOT/'pyproject.toml',MiB,pins['pyproject.toml']))
        require(reader.bytes(output/('control/worker-registration-'+phase+'.json'),MiB)==registration_raw,'Independent '+phase+' registration differs')
        invocation=reader.json(output/(phase+'-invocation.json'))[0]
        require(invocation==dict(command=namespace(config,baseline,native,observation,phase,files,worker_command),configuration_sha256=expected_sha),
                'Independent '+phase+' namespace argv differs')
        supervision=reader.json(output/(phase+'-supervision.json'))[0];tracked=supervision.get('tracked_processes')
        require(supervision.get('status')=='completed' and supervision.get('returncode')==0 and supervision.get('failure') is None
                and supervision.get('matching_survivors')==[] and supervision.get('process_scope')=='descendants'
                and type(tracked) is list and len(tracked)==3,'Normal '+phase+' descendant supervision required')
        stdout=reader.bytes(output/('logs-'+phase)/'stdout.log',MiB);receipt=decode(stdout);reader.bytes(output/('logs-'+phase)/'stderr.log',16*MiB)
        dep=receipt.get('dependencies',{})
        require(stdout==canonical(receipt) and receipt.get('kind')=='puck-worker-source-bootstrap-receipt-v1'
                and receipt.get('registration_sha256')==sha(registration_raw) and receipt.get('interpreter_object_bound') is True
                and receipt.get('python_version')=='3.11.15' and receipt.get('episode_phase')==phase
                and all(receipt.get(k) is False for k in ('runtime_qualified','dependencies_qualified','native_authorized','collection_authorized','executable'))
                and receipt.get('qualification_claims')==[] and receipt.get('expected_missing_imports')==NEGATIVE_IMPORTS
                and receipt.get('expected_hidden_imports')==HIDDEN_IMPORTS and set(receipt.get('denied_imports',[None]))<=declared
                and receipt.get('process_creation_attempts')==dict(count=0,events=[])
                and dep.get('registration_sha256')==sha(dependency_raw) and dep.get('root_count')==4 and dep.get('file_count')==count
                and dep.get('input_bytes')==total and dep.get('native_identity')=='tmpfs-raw-dev-inode-v1','Held '+phase+' bootstrap receipt differs')
        entry=receipt['entry_result'];validate_entry(entry,config,phase);entries[phase]=(entry,sha(stdout),sha(registration_raw))
        require(entry['provenance_sha256']==sha(expected_raw),'The '+phase+' held provenance digest differs from the independent record')
        payload=output/('payload-'+phase);run=payload/config['run_ids'][phase];bundle=entry['bundle']
        require({e.name for e in os.scandir(payload)}=={bundle['path'],run.name} and stat.S_ISDIR(run.lstat().st_mode),'Payload members differ: '+phase)
        reader.bytes(payload/bundle['path'],LIMITS['file_bytes'],bundle,keep=False)
        checked=v.validate_bundle(payload/bundle['path'],run);require(checked['sha256']==bundle['sha256'],'Validated bundle differs: '+phase)
        recordings[phase]=recording(run,v,reader,EPISODE['schedule']['ticks'],expected_report)
    source_entry,replay_entry=entries['source'][0],entries['replay'][0]
    require(source_entry['initial_snapshot_id']==recordings['source'][1]['snapshot_id'],'Source snapshot identity differs from its registration')
    require(source_entry['provenance_sha256']==replay_entry['provenance_sha256'],'Held provenance differs between phases')
    compare(recordings['source'][0],recordings['replay'][0])
    replay_run=output/'payload-replay'/config['run_ids']['replay'];report_raw=reader.bytes(replay_run/'replay-report.json',MiB);report=decode(report_raw)
    require(report.get('status')=='passed' and report.get('compared_ticks')==EPISODE['schedule']['ticks'] and report.get('first_divergence') is None
            and report.get('mode')=='actions' and report.get('source_run_id')==config['run_ids']['source'] and report.get('run_id')==config['run_ids']['replay']
            and report.get('compared_events')==replay_entry['replay']['compared_events'],'Replay report differs')
    result_raw=reader.bytes(output/'result.json',MiB);result=decode(result_raw)
    def manifest(run):
        return sorted((dict(path=p.relative_to(run).as_posix(),size_bytes=p.stat().st_size,sha256=sha(reader.bytes(p,LIMITS['file_bytes'])))
                       for p in run.rglob('*') if p.is_file()),key=lambda row:row['path'])
    runs={phase:dict(run_id=config['run_ids'][phase],files=manifest(output/('payload-'+phase)/config['run_ids'][phase]),
                     bundle=entries[phase][0]['bundle']) for phase in PHASES}
    expected=dict(CLAIMS,kind='puck-cpu-held-episode-outcome-v16',version=16,allocation_id=16,configuration_sha256=expected_sha,
        status='episode_completed',held_episode_observed=True,run_ids=config['run_ids'],
        worker_stdout_sha256={p:entries[p][1] for p in PHASES},registration_sha256={p:entries[p][2] for p in PHASES},runs=runs,
        replay_report=dict(path='replay-report.json',size_bytes=len(report_raw),sha256=sha(report_raw)),replay=replay_entry['replay'],
        renderer=source_entry['renderer'],ticks_completed=source_entry['ticks_completed'],versions=VERSIONS,
        provenance_sha256=source_entry['provenance_sha256'],initial_snapshot_id=source_entry['initial_snapshot_id'],
        process_creation_attempts=0,dependencies_sha256=sha(dependency_raw))
    closure=result.get('closure',{})
    require(result_raw==canonical(result) and set(result)==set(expected)|{'closure','elapsed_seconds'}
            and all(canonical(result[k])==canonical(value) for k,value in expected.items())
            and closure==dict(active_children=[],active_non_main_threads=[],fd_count_before=closure.get('fd_count_before'),
                              fd_count_after=closure.get('fd_count_before')) and type(closure.get('fd_count_before')) is int
            and finite(result['elapsed_seconds'],LIMITS['normal_seconds']),'Completed allocation-16 outcome required')
    traw=reader.bytes(transport,64*1024);observed=decode(traw)
    require(sha(traw)==transport_sha and traw==canonical(observed),'Authenticated canonical transport required')
    authored=observed.get('kind')=='authored-cpu-parent-cli-transport-v1'
    require(authored or (observed.get('kind')=='puck-cpu-held-cli-transport-v1' and observed.get('phase')=='episode'
            and observed.get('timed_out') is False),'Episode transport kind differs')
    require(not authored or str(observed.get('authored_scope','')).startswith('AUTHORED fixture only;'),'Explicit authored transport scope required')
    require(observed.get('configuration_sha256')==expected_sha and observed.get('observed_returncode')==0
            and finite(observed.get('elapsed_seconds'),780) and observed.get('command')==[PYTHON,'-I','-S','-B',str(ROOT/PARENT),
            '--configuration',str(configuration),'--sha256',expected_sha],'Normal external episode transport required')
    for name in ('stdout','stderr'):
        path=('authored-episode16-cli.' if authored else OUTPUT+'-external-cli.')+name;row=observed.get(name,{})
        require(row.get('path')==path,'Exact transport stream path required')
        payload=reader.bytes(ROOT/path,16*MiB,row)
        if name=='stdout':require(payload==result_raw,'External stdout differs from the retained outcome')
    reader.recheck()
    return dict(configuration_sha256=expected_sha,result_sha256=sha(result_raw),transport_sha256=transport_sha,
        preparation04_audit_sha256=config['preparation_acceptance']['independent_audit']['sha256'],
        source_bundle_sha256=runs['source']['bundle']['sha256'],replay_bundle_sha256=runs['replay']['bundle']['sha256'],
        replay_report_sha256=sha(report_raw),compared_ticks=EPISODE['schedule']['ticks'],frames_checked=2*len(CAMERAS)*EPISODE['schedule']['ticks'],
        provenance_sha256=source_entry['provenance_sha256'],renderer=source_entry['renderer'],baseline=summary,
        validator_sha256=sha(Path(v.__file__).read_bytes()),evidence_scope='AUTHORED fixture only' if authored else 'held public episode allocation 16')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('configuration','sha256','transport','transport-sha256','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args();started=time.monotonic()
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,310)
    report=dict(CLAIMS,kind=KIND,version=1,status='FAIL',configuration_sha256=args.sha256,transport_sha256=args.transport_sha256,
                target_code_executed_by_auditor=False,auditor_source_sha256=sha(Path(__file__).read_bytes()))
    try:
        try:
            require(Path(sys.executable).resolve()==Path(PYTHON) and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
                    'Original isolated audit interpreter required')
            for value in (args.sha256,args.transport_sha256):require(hexdigest(value),'Explicit lowercase audit SHA required')
            report['verified']=audit(args.configuration,args.sha256,args.transport,args.transport_sha256,started+300)
            report['status']='PASS'
        except Exception as error:report.update(error_type=type(error).__name__,error=str(error)[:2048])
        report['elapsed_seconds']=time.monotonic()-started
        raw=canonical(report);fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            view=memoryview(raw)
            while view:view=view[os.write(fd,view):]
            os.fsync(fd)
        finally:os.close(fd)
        print(raw.decode(),end='',flush=True)
        return 0 if report['status']=='PASS' else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
