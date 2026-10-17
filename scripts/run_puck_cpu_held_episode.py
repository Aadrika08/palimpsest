"""Allocation 16: one held public manual episode over accepted preparation04.

Worker A records the source episode and worker B replays it from A's read-only
output, each inside the held, import-guarded v4 bootstrap with a 360 s clock,
over preparation04's staged roots and its single source capsule. The parent
admits only the exact frozen configuration, binds preparation04's independent
acceptance, and requires zero process-creation attempts, every scheduled tick,
a passing replay, the exact versions and the frozen renderer. The result binds
both bootstrap receipts, both run directories, both bundles and the replay
report. It grants no runtime, renderer, collection or study authority.
"""
import argparse
import copy
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
import types

ROOT=Path(__file__).resolve().parents[1]
MiB=1024**2
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
QUALIFIER='scripts/qualify_puck_cpu_held_runtime.py'
PARENT='scripts/run_puck_cpu_held_episode.py'
BOOTSTRAP='scripts/puck_worker_bootstrap.py'
KIND='puck-cpu-held-episode-allocation-v16'
VERSION=16
OUTPUT='runs/puck-cpu-held-episode-16'
PREPARATION04='runs/puck-cpu-held-preparation-04'
SITE='runs/puck-cpu-install-01/site'
STAGED_SITE='/puck/staged/inputs/root-0000'
VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',mujoco='3.3.6',gymnasium='1.2.1')
INTERPRETER=dict(path=PYTHON,size_bytes=21662864,sha256='572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a')
# The held worker environment: the qualifier's plus the four episode additions.
ENVIRONMENT=dict(PYTHONDONTWRITEBYTECODE='1',LC_ALL='C.UTF-8',LANG='C.UTF-8',
    HOME='/scratch/home',TMPDIR='/scratch/tmp',PWD='/puck/source',PATH='/nonexistent',TZ='UTC',
    CUDA_VISIBLE_DEVICES='',MUJOCO_GL='egl',PYOPENGL_PLATFORM='egl',MPLBACKEND='Agg',
    OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    OPENBLAS_MAIN_FREE='1',GOTOBLAS_MAIN_FREE='1',TORCH_DEVICE_BACKEND_AUTOLOAD='0',
    PYGLFW_LIBRARY=STAGED_SITE+'/glfw/x11/libglfw.so',MESA_SHADER_CACHE_DISABLE='true',
    PYGAME_HIDE_SUPPORT_PROMPT='hide',__EGL_VENDOR_LIBRARY_FILENAMES='/puck/control/egl-vendor.json')
LIMITS=dict(normal_seconds=720,child_hard_seconds=735,hard_seconds=750,
    rss_bytes=2048*MiB,address_space_bytes=8192*MiB,output_bytes=64*MiB,
    scratch_bytes=64*MiB,file_bytes=16*MiB,min_free_bytes=4096*MiB,
    min_available_ram_bytes=2048*MiB,min_tmpfs_free_bytes=256*MiB,max_processes=3,max_fds=40000)
WORKER_SECONDS=360
# Policy v5 absent names (epoch14's 32) plus the ten the offline episode census requested.
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
# Characterization-04's run ids; allocation 16 must use two other fresh ids.
CHARACTERIZATION_RUN_IDS=('a6effc7912fec337875d13ae69445e43','6c04b9ed22c383fda860fa3b4f8bab13')
RENDERER=dict(vendor='Mesa',renderer_contains='llvmpipe',version='4.6 (Compatibility Profile) Mesa 26.2.2-arch1.1',
    egl_vendor='Mesa Project',egl_version='1.5',backend='egl')
CLAIMS=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,
    study_authorized=False,executable=False,qualification_claims=[])
EPISODE_CLAIMS=('runtime_qualified','native_authorized','collection_authorized','executable')
KEYS={'kind','version','allocation_id','root','stage_parent','sources','inputs','interpreter','environment',
      'expected_versions','limits','negative_imports','hidden_imports','claims','preparation_acceptance','run_ids'}
PHASES=('source','replay')


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def digest(raw):return hashlib.sha256(raw).hexdigest()


def hexdigest(value):return type(value) is str and re.fullmatch('[0-9a-f]{64}',value) is not None


def finite(value,maximum):return type(value) in (int,float) and math.isfinite(value) and 0<=value<maximum


def require(value,message):
    if not value:raise ValueError(message)


def read(path,maximum,expected=None,*,empty=False):
    """Bounded nofollow read before any repository helper is imported."""
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_nlink==1 and (0 if empty else 1)<=before.st_size<=maximum,
                'Bounded single-link episode input required: '+str(path))
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(maximum+1)
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink)
        require(len(raw)==before.st_size and stamp(os.fstat(fd))==stamp(before)
                and stamp(os.stat(path,follow_symlinks=False))==stamp(before),'Episode input changed while read: '+str(path))
    finally:os.close(fd)
    require(expected is None or digest(raw)==expected,'Episode input SHA differs: '+str(path))
    return raw


def qualifier():
    import qualify_puck_cpu_held_runtime as q
    return q


def validate_configuration(config,q=None):
    q=q or qualifier()
    require(type(config) is dict and set(config)==KEYS and config['kind']==KIND and type(config['version']) is int
            and config['version']==VERSION and type(config['allocation_id']) is int and config['allocation_id']==VERSION
            and config['root']==str(ROOT) and config['interpreter']==INTERPRETER
            and canonical(config['environment'])==canonical(ENVIRONMENT) and config['expected_versions']==VERSIONS
            and canonical(config['limits'])==canonical(LIMITS) and canonical(config['claims'])==canonical(CLAIMS)
            and config['negative_imports']==NEGATIVE_IMPORTS and config['hidden_imports']==HIDDEN_IMPORTS,
            'Exact allocation-16 episode configuration required')
    q._hidden_imports(HIDDEN_IMPORTS,NEGATIVE_IMPORTS)
    stage=config['stage_parent']
    require(type(stage) is str and re.fullmatch(r'/tmp/palimpsest-puck-cpu-held-04(?:-[A-Za-z0-9_-]+)?',stage) is not None,
            'Preparation04 tmpfs stage required')
    expected=sorted(set(q.PREPARATION04_SOURCES)|{PARENT})
    require(type(config['sources']) is list and [q.pin(r,empty=True)['path'] for r in config['sources']]==expected,
            'Preparation04 sources plus this parent required')
    require(type(config['inputs']) is dict and set(config['inputs'])==set(q.PREPARATION04_INPUT_ROLES),'Preparation04 input roles required')
    for row in config['inputs'].values():q.pin(row)
    acceptance=config['preparation_acceptance']
    require(type(acceptance) is dict and set(acceptance)=={'configuration','result','independent_audit','externally_observed_auditor_cli'},
            'Exact preparation04 acceptance required')
    for row in acceptance.values():q.pin(row)
    require(acceptance['result']['path']==PREPARATION04+'/result.json','Exact preparation04 receipt required')
    ids=config['run_ids']
    require(type(ids) is dict and set(ids)==set(PHASES) and all(type(v) is str and re.fullmatch('[0-9a-f]{32}',v) for v in ids.values())
            and ids['source']!=ids['replay'] and not set(ids.values())&set(CHARACTERIZATION_RUN_IDS),
            'Two fresh distinct allocation-16 run ids required')


def validate_acceptance(config,blobs,q):
    """Preparation04's configuration, prepared result, independent v15 audit and its observed CLI."""
    acceptance=config['preparation_acceptance'];values={}
    for role,row in acceptance.items():
        raw=blobs[role];require(len(raw)==row['size_bytes'] and digest(raw)==row['sha256'],'Preparation04 acceptance pin differs')
        value=q.decode(raw);require(type(value) is dict,'Preparation04 acceptance object required')
        if role in ('configuration','result'):require(canonical(value)==raw,'Canonical preparation04 bytes required')
        values[role]=value
    prior,prep,audit,cli=(values[k] for k in ('configuration','result','independent_audit','externally_observed_auditor_cli'))
    q.validate_configuration(prior)
    require(prior['version']==15 and prior['phase']=='prepare' and all(prior[k]==config[k] for k in ('root','stage_parent','inputs','expected_versions'))
            and prior['interpreter']==q.INTERPRETER and canonical(prior['claims'])==canonical(CLAIMS),
            'Allocation 16 must bind exactly accepted preparation04 data')
    rows={r['path']:r for r in config['sources']}
    require(all(rows.get(r['path'])==r for r in prior['sources']) and set(rows)-{r['path'] for r in prior['sources']}=={PARENT},
            'Allocation 16 must reuse preparation04 sources exactly')
    def closed(value,count):
        row=value.get('closure',{})
        return (row.get('active_children')==[] and row.get('active_non_main_threads')==[] and type(row.get('fd_count_before')) is int
                and row['fd_count_before']==count and row.get('fd_count_after')==count)
    false=lambda value:all(value.get(k) is False for k in CLAIMS if k!='qualification_claims') and value.get('qualification_claims')==[]
    require(prep.get('kind')=='puck-cpu-held-runtime-outcome-v15' and prep.get('version')==15 and prep.get('allocation_id')==15
            and prep.get('phase')=='prepare' and prep.get('status')=='prepared' and not {'error','error_type'}&set(prep)
            and false(prep) and prep.get('configuration_sha256')==acceptance['configuration']['sha256']
            and prep.get('stage_parent')==prior['stage_parent'] and prep.get('sources')==prior['sources']
            and prep.get('inputs')==prior['inputs'] and closed(prep,5) and finite(prep.get('elapsed_seconds'),180),
            'Preparation04 receipt differs or failed')
    dep=q.pin(prep.get('dependencies'));require(dep['path']=='payload/dependencies.json','Preparation04 dependency path differs')
    require(audit.get('kind')=='puck-cpu-held-runtime-independent-audit-v15' and audit.get('version')==15
            and audit.get('allocation_id')==15 and audit.get('status')=='PASS' and audit.get('phase')=='prepare'
            and audit.get('observed_status')=='prepared' and not {'error','error_type'}&set(audit) and false(audit)
            and audit.get('auditor_source_sha256')==q.PREPARATION04_AUDITOR_SHA256
            and audit.get('configuration_sha256')==acceptance['configuration']['sha256']
            and audit.get('result_sha256')==acceptance['result']['sha256'] and audit.get('dependencies_sha256')==dep['sha256']
            and type(audit.get('external_returncode')) is int and audit['external_returncode']==0 and closed(audit,4)
            and audit.get('evidence_scope') in ('ordinary CPU held allocation only','AUTHORED fixture only'),
            'Preparation04 independent audit failed or differs')
    require(cli.get('kind')=='externally-observed-cpu-auditor-cli-v1' and type(cli.get('observed_returncode')) is int
            and cli['observed_returncode']==0 and all(type(cli.get(k)) is dict for k in ('published','stdout','stderr'))
            and cli['stdout'].get('sha256')==cli['published'].get('sha256')==acceptance['independent_audit']['sha256']
            and cli['stderr'].get('size_bytes')==0,'Preparation04 auditor CLI did not return normally')
    command=cli.get('command')
    require(type(command)==list and len(command)==15 and command[:5]==[PYTHON,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_runtime.py')]
            and command[5:9]==['--configuration',str(ROOT/acceptance['configuration']['path']),'--sha256',acceptance['configuration']['sha256']]
            and command[10] in (str(ROOT/'authored-prepare04-transport.json'),str(ROOT/PREPARATION04)+'-external-cli-transport.json')
            and command[11:]==['--transport-sha256',audit.get('transport_sha256'),'--output',cli['published'].get('path')],
            'Preparation04 auditor CLI command differs')
    return prior,prep


def descriptor(config,phase):
    source='/output' if phase=='source' else '/puck/source-run'
    return dict(kind='puck-held-public-episode-v1',version=1,phase=phase,expected_versions=dict(VERSIONS),
        stdlib_cache_aliases={'__mp_main__':'__main__'},negative_imports=list(NEGATIVE_IMPORTS),
        hidden_imports=list(HIDDEN_IMPORTS),stdlib_exception=dict(SYSCONFIGDATA),
        profile=copy.deepcopy(EPISODE['profile']),schedule=copy.deepcopy(EPISODE['schedule']),
        run_ids=dict(config['run_ids']),paths=dict(output_root='/output',source_root=source,asset_root='/scratch/assets'),
        upstream_commit=EPISODE['upstream_commit'])


def registration(config,phase,source_files,dependency_raw,bootstrap_raw,q):
    """The exact v4 bootstrap registration; argv prefix and canonical bytes come from the frozen bootstrap."""
    api=types.ModuleType('_frozen_episode_bootstrap_api');api.__file__=str(ROOT/BOOTSTRAP)
    exec(compile(bootstrap_raw,api.__file__,'exec'),api.__dict__)
    bootstrap=next(r for r in source_files if r['path']==BOOTSTRAP)
    path='/puck/control/worker-registration-'+phase+'.json'
    prefix=api.command(PYTHON,'/puck/source/'+BOOTSTRAP,bootstrap['sha256'],path,'0'*64)[:-1]
    value=dict(kind='puck-worker-source-bootstrap-v4',version=4,source_root='/puck/source',source_files=copy.deepcopy(source_files),
        modules=q.source_modules(source_files),namespaces=[],
        runtime=dict(root=str(Path(PYTHON).parent),files=[dict(api.RUNTIME_PIN)],python_version='3.11.15'),
        environment=dict(ENVIRONMENT),cwd='/puck/source',argv_prefix=prefix,
        dependencies=dict(path='/puck/control/dependencies.json',size_bytes=len(dependency_raw),sha256=digest(dependency_raw)),
        episode=descriptor(config,phase),qualification_claims=[],executable=False,deadline_seconds=WORKER_SECONDS)
    raw=api.canonical(value)
    return value,raw,prefix+[digest(raw)]


def validate_renderer(value):
    require(type(value) is dict and set(value)=={'vendor','renderer','version','egl_vendor','egl_version','backend'}
            and all(type(v) is str for v in value.values()) and value['vendor']==RENDERER['vendor']
            and RENDERER['renderer_contains'] in value['renderer']
            and all(value[k]==RENDERER[k] for k in ('version','egl_vendor','egl_version','backend')),
            'Episode renderer differs from the frozen Mesa llvmpipe EGL criteria')


def validate_entry(value,config,phase):
    ids=config['run_ids'];ticks=EPISODE['schedule']['ticks']
    common={'kind','version','phase','run_id','source_run_id','ticks_requested','provenance_sha256','versions','bundle',
            *EPISODE_CLAIMS,'qualification_claims'}
    extra={'ticks_completed','final_phase','initial_snapshot_id','renderer'} if phase=='source' else {'replay'}
    require(type(value) is dict and set(value)==common|extra and value['kind']=='puck-held-public-episode-result-v1'
            and type(value['version']) is int and value['version']==1 and value['phase']==phase
            and value['run_id']==ids[phase] and value['source_run_id']==ids['source']
            and type(value['ticks_requested']) is int and value['ticks_requested']==ticks
            and hexdigest(value['provenance_sha256']) and value['versions']==VERSIONS
            and all(value[k] is False for k in EPISODE_CLAIMS) and value['qualification_claims']==[],
            'Exact held episode '+phase+' result required')
    bundle=value['bundle']
    require(type(bundle) is dict and set(bundle)=={'path','size_bytes','sha256'} and bundle['path']==phase+'-bundle.zip'
            and type(bundle['size_bytes']) is int and 0<bundle['size_bytes']<=LIMITS['file_bytes'] and hexdigest(bundle['sha256']),
            'Exact bounded '+phase+' bundle receipt required')
    if phase=='source':
        require(type(value['ticks_completed']) is int and value['ticks_completed']==ticks and type(value['final_phase']) is str
                and type(value['initial_snapshot_id']) is str and 0<len(value['initial_snapshot_id'])<=128,
                'Held source episode must complete every scheduled tick')
        validate_renderer(value['renderer'])
    else:
        replay=value['replay']
        require(type(replay) is dict and set(replay)=={'status','compared_ticks','compared_events','first_divergence'}
                and replay['status']=='passed' and type(replay['compared_ticks']) is int and replay['compared_ticks']==ticks
                and type(replay['compared_events']) is int and replay['compared_events']>0 and replay['first_divergence'] is None,
                'Held replay must pass every scheduled tick without divergence')


def validate_receipt(receipt,config,phase,registration_raw,dependency_raw,dependencies):
    declared=set(NEGATIVE_IMPORTS)|set(HIDDEN_IMPORTS);dep=receipt.get('dependencies',{})
    count=sum(len(r['files']) for r in dependencies['roots']);total=sum(f['size_bytes'] for r in dependencies['roots'] for f in r['files'])
    require(receipt.get('kind')=='puck-worker-source-bootstrap-receipt-v1' and receipt.get('registration_sha256')==digest(registration_raw)
            and receipt.get('interpreter_object_bound') is True and receipt.get('python_version')=='3.11.15'
            and all(receipt.get(k) is False for k in ('runtime_qualified','dependencies_qualified','native_authorized','collection_authorized','executable'))
            and receipt.get('qualification_claims')==[] and receipt.get('expected_missing_imports')==NEGATIVE_IMPORTS
            and receipt.get('expected_hidden_imports')==HIDDEN_IMPORTS and type(receipt.get('denied_imports')) is list
            and set(receipt['denied_imports'])<=declared and receipt.get('episode_phase')==phase
            and receipt.get('process_creation_attempts')==dict(count=0,events=[])
            and dep.get('registration_sha256')==digest(dependency_raw) and dep.get('native_identity')=='tmpfs-raw-dev-inode-v1'
            and dep.get('root_count')==4 and dep.get('file_count')==count and dep.get('input_bytes')==total
            and dep.get('native_cache_modules',[])==sorted(dependencies['import_profile'].get('native_cache',[]),key=lambda r:r['name']),
            'Held episode '+phase+' bootstrap receipt differs or attempted process creation')
    validate_entry(receipt.get('entry_result'),config,phase)


def run_manifest(path,maximum=64):
    """Every regular file of one run directory, by relative path, size and SHA-256."""
    rows=[]
    for directory,names,files in os.walk(path,followlinks=False):
        for name in names:require(not os.path.islink(os.path.join(directory,name)),'Run directory symlink refused')
        for name in files:
            full=Path(directory)/name;state=full.lstat();require(stat.S_ISREG(state.st_mode),'Run directory special file refused')
            rows.append(dict(path=full.relative_to(path).as_posix(),size_bytes=state.st_size,sha256=digest(read(full,LIMITS['file_bytes'],empty=True))))
    require(0<len(rows)<=maximum,'Bounded nonempty run directory required')
    return sorted(rows,key=lambda r:r['path'])


def execute(config,raw,started):
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
    q=qualifier()
    import qualify_puck_held_runtime as controls
    import build_puck_python_louvain as baseline_api
    from palimpsest import bounded_qualification as bounds
    from palimpsest.puck_retained_installation import AdmissionInputs
    from palimpsest.puck_cpu_registration import build_cpu_source_registration,attach_cpu_candidate,native_leaf_row,egl_vendor_control
    from palimpsest.puck_cpu_namespace import sandbox_command
    validate_configuration(config,q)
    output=ROOT/OUTPUT;stage=Path(config['stage_parent']);prepared=ROOT/PREPARATION04;acceptance=config['preparation_acceptance']
    rows=[*config['sources'],*config['inputs'].values(),*acceptance.values()]
    capsule=[dict(row,path=PREPARATION04+'/parent-source/'+row['path']) for row in config['sources'] if row['path']!=PARENT]
    rows+=capsule+[dict(acceptance['configuration'],path=PREPARATION04+'/configuration.json')]
    require(len({r['path'] for r in rows})==len(rows),'Overlapping allocation-16 pins')
    admission=q.resource_admission(config)
    deadline=started+LIMITS['normal_seconds'];state={};before_fds=len(os.listdir('/proc/self/fd'))
    bounds.reserve_output(output,dict(sources=dict(root=str(ROOT),files=rows)))
    for name in ('control','logs-source','logs-replay','payload-source','payload-replay'):(output/name).mkdir(mode=0o700)
    result=dict(CLAIMS,kind='puck-cpu-held-episode-outcome-v16',version=VERSION,allocation_id=VERSION,
                configuration_sha256=digest(raw),status='FAIL',held_episode_observed=False)
    bounds.write_new(output/'configuration.json',config);bounds.write_new(output/'resource-admission.json',admission)
    try:
        with bounds.hard_guard(started+LIMITS['hard_seconds'],state):
            with AdmissionInputs(ROOT,sorted(rows,key=lambda r:r['path']),deadline) as inputs:
                blobs={role:q.read(ROOT/row['path'],16*MiB,row['sha256']) for role,row in config['inputs'].items()}
                old={role:q.read(ROOT/row['path'],MiB,row['sha256']) for role,row in acceptance.items()}
                prior,prep=validate_acceptance(config,old,q)
                require(q.read(prepared/'configuration.json',MiB,acceptance['configuration']['sha256'])==old['configuration'],
                        'Preparation04 retained configuration differs')
                inventory,layout,candidate,observation=q.validate_inputs(prior,blobs)
                baseline=q.decode(blobs['baseline']);native=q.decode(blobs['native'])
                vendor=egl_vendor_control(native,read(native['egl_vendor']['path'],64*1024))
                def native_checks():
                    for row in native['native_files']:
                        require(native_leaf_row(row['path'],deadline)=={k:row[k] for k in ('size_bytes','sha256')},'Native leaf changed')
                    for path,target in native['aliases']:require(os.readlink(path)==target,'Native alias changed')
                    require(read(native['egl_vendor']['path'],64*1024)==vendor,'EGL vendor JSON changed')
                native_checks();baseline_before=baseline_api.verify_baseline(baseline,deadline)
                bounds.write_new(output/'baseline-before.json',baseline_before)
                source_bytes={r['path']:q.read(ROOT/r['path'],MiB,r['sha256'],empty=True) for r in config['sources']}
                for row in capsule:q.read(ROOT/row['path'],MiB,row['sha256'],empty=True)
                source_reg=build_cpu_source_registration(blobs['inventory'],blobs['layout'],blobs['candidate'],blobs['native'],
                    expected_pins={k:{x:config['inputs'][k][x] for x in ('size_bytes','sha256')} for k in ('inventory','layout','candidate','native')},
                    site_root=str(ROOT/SITE),generated_root=str((ROOT/config['inputs']['generated']['path']).parent),deadline=q.planning(deadline))
                dep=prep['dependencies'];dependency_raw=q.read(prepared/'payload/dependencies.json',16*MiB,dep['sha256'])
                dependencies=q.decode(dependency_raw)
                require(attach_cpu_candidate(dependencies,blobs['candidate'],expected_sha256=config['inputs']['candidate']['sha256'],
                        deadline=q.planning(deadline))==dependencies and dependencies.get('distributions')==source_reg['distributions']
                        and all(a.get('files')==b['files'] for a,b in zip(dependencies['roots'],source_reg['roots'])),
                        'Prepared bytes/profile differ from the accepted source plan')
                q.verify_staged_roots(str(stage),dependencies,prep['staged_roots'])
                controls.write(output/'control/dependencies.json',dependency_raw,16*MiB)
                controls.write(output/'control/egl-vendor.json',vendor)
                files=[r for r in config['sources'] if r['path'] in q.EPISODE_WORKER_SOURCES]
                receipts={};payloads={}
                for phase in PHASES:
                    value,registration_raw,command=registration(config,phase,files,dependency_raw,source_bytes[BOOTSTRAP],q)
                    controls.write(output/('control/worker-registration-'+phase+'.json'),registration_raw)
                    command=sandbox_command(baseline,native,q.baseline_images(prior,observation,native),phase='episode-'+phase,
                        stage_parent=str(stage),source_root=str(prepared/'parent-source'),control_root=str(output/'control'),
                        output_root=str(output/('payload-'+phase)),command=q.qualification_command(command),environment=ENVIRONMENT,
                        scratch_bytes=LIMITS['scratch_bytes'],source_run_root=str(output/'payload-source') if phase=='replay' else None,
                        source_files=[r['path'] for r in files])
                    bounds.write_new(output/(phase+'-invocation.json'),dict(command=command,configuration_sha256=digest(raw)))
                    began=time.monotonic()
                    observed=bounds.supervised(command,output/('logs-'+phase),cwd=ROOT,normal_deadline=min(deadline,began+WORKER_SECONDS+5),
                        hard_deadline=min(started+LIMITS['child_hard_seconds'],began+WORKER_SECONDS+15),rss_bytes=LIMITS['rss_bytes'],
                        output_bytes=LIMITS['output_bytes'],min_free_bytes=LIMITS['min_free_bytes'],max_processes=LIMITS['max_processes'],
                        output_root=output,guard_state=state,output_namespace_limits=(128,16),log_mode='direct',process_scope='descendants')
                    bounds.write_new(output/(phase+'-supervision.json'),observed)
                    require(observed['status']=='completed','Held episode '+phase+' worker failed; retained logs are authoritative')
                    stdout=q.read(output/('logs-'+phase)/'stdout.log',MiB);receipt=q.decode(stdout)
                    validate_receipt(receipt,config,phase,registration_raw,dependency_raw,dependencies)
                    entry=receipt['entry_result'];payload=output/('payload-'+phase);bundle=entry['bundle']
                    require(len(q.read(payload/bundle['path'],LIMITS['file_bytes'],bundle['sha256']))==bundle['size_bytes'],
                            'Held '+phase+' bundle bytes differ from the receipt')
                    run_id=config['run_ids'][phase]
                    require({e.name for e in os.scandir(payload)}=={bundle['path'],run_id},'Held '+phase+' payload members differ')
                    receipts[phase]=dict(stdout_sha256=digest(stdout),registration_sha256=digest(registration_raw),entry=entry)
                    payloads[phase]=dict(run_id=run_id,files=run_manifest(payload/run_id),bundle=bundle)
                require(receipts['source']['entry']['provenance_sha256']==receipts['replay']['entry']['provenance_sha256'],
                        'Held provenance differs between source and replay')
                report=next((r for r in payloads['replay']['files'] if r['path']=='replay-report.json'),None)
                require(report is not None,'Held replay report is missing')
                q.verify_staged_roots(str(stage),dependencies,prep['staged_roots']);native_checks()
                baseline_after=baseline_api.verify_baseline(baseline,deadline)
                require(baseline_before==baseline_after,'Original trusted CPU baseline changed')
                bounds.write_new(output/'baseline-after.json',baseline_after)
                inputs.recheck()
                source=receipts['source']['entry'];replay=receipts['replay']['entry']
                result.update(status='episode_completed',held_episode_observed=True,run_ids=dict(config['run_ids']),
                    worker_stdout_sha256={p:receipts[p]['stdout_sha256'] for p in PHASES},
                    registration_sha256={p:receipts[p]['registration_sha256'] for p in PHASES},
                    runs={p:payloads[p] for p in PHASES},replay_report=report,replay=replay['replay'],
                    renderer=source['renderer'],ticks_completed=source['ticks_completed'],versions=dict(VERSIONS),
                    provenance_sha256=source['provenance_sha256'],initial_snapshot_id=source['initial_snapshot_id'],
                    process_creation_attempts=0,dependencies_sha256=digest(dependency_raw))
    except Exception as error:result.update(status='FAIL',error_type=type(error).__name__,error=str(error))
    result['closure']=q.closure(before_fds);result['elapsed_seconds']=time.monotonic()-started
    if time.monotonic()>=deadline:raise TimeoutError('Allocation-16 normal return deadline')
    bounds.write_new(output/'result.json',result);q.closure(before_fds)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',required=True,type=Path);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();started=time.monotonic()
    raw=read(args.configuration,MiB,args.sha256)
    if os.getpgrp()!=os.getpid():os.setsid()
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,LIMITS['hard_seconds'])
    try:
        config=json.loads(raw);require(canonical(config)==raw,'Canonical allocation-16 configuration bytes required')
        require(type(config.get('sources')) is list and [r.get('path') for r in config['sources']]==sorted({r.get('path') for r in config['sources']})
                and QUALIFIER in {r['path'] for r in config['sources']},'Sorted allocation-16 sources including the qualifier required')
        for row in config['sources']:
            require(len(read(ROOT/row['path'],MiB,row['sha256'],empty=True))==row['size_bytes'],'Allocation-16 source differs')
        sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
        validate_configuration(config)
        require(Path(sys.executable).resolve()==Path(PYTHON) and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
                and not os.environ.get('LD_PRELOAD') and not os.environ.get('LD_LIBRARY_PATH'),'Original isolated CPU parent interpreter required')
        if os.path.lexists(ROOT/OUTPUT):raise FileExistsError('Allocation 16 already reserved')
        sys.pycache_prefix=str(ROOT/OUTPUT/'unused-parent-pycache')
        for key,value in (('NOFILE',LIMITS['max_fds']),('AS',LIMITS['address_space_bytes']),('FSIZE',LIMITS['file_bytes'])):
            resource.setrlimit(getattr(resource,'RLIMIT_'+key),(value,value))
        result=execute(config,raw,started)
        print(canonical(result).decode(),end='',flush=True)
        return 0 if result['status']=='episode_completed' and time.monotonic()<started+LIMITS['normal_seconds'] else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
