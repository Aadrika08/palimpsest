"""Characterization-04: one unguarded held-episode observation in the v6 namespace.

Authored data only; no characterization allocation runs here. The parent freezes
a new output identity, the v6 native metadata, the episode environment and the
held descriptor (seed 7, 48 ticks, actions at 0 and 24). The worker runs
``puck_held_episode.run`` with a stand-in admission, records and refuses every
process creation, and records the module cache and mapped images.
"""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/characterize_puck_cpu_episode.py'
WORKER=ROOT/'scripts/characterize_puck_episode_worker.py'
HELPER=ROOT/'scripts/characterize_puck_runtime_imports.py'

# Independently authored identity; do not derive from producer constants.
OUTPUT04='runs/puck-cpu-runtime-characterization-04'
KIND04='puck-cpu-runtime-characterization-v3'
VERSIONS04=dict(numpy='2.2.5',torch='2.9.0+cpu',mujoco='3.3.6',gymnasium='1.2.1')
NATIVE06=dict(path='docs/plans/puck-cpu-characterization-native-metadata-06.json',size_bytes=17199,
    sha256='48ca37b1c45366bcd53ac195277ade6236537f89a720b50591906764eaf72569')
GL_VERSION='4.6 (Compatibility Profile) Mesa 26.2.2-arch1.1'
REPORT_KIND='puck-episode-characterization-result-v1'
FAKE_RESULT_KIND='puck-held-public-episode-result-v1'


def api():
    assert SCRIPT.is_file(),'characterization-04 parent is missing'
    spec=importlib.util.spec_from_file_location('cpu_episode_parent_fixture',SCRIPT)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def sha(raw):return hashlib.sha256(raw).hexdigest()


def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def authored_sources(m):
    return [dict(path=path,size_bytes=0 if path.endswith('__init__.py') else 1,sha256='a'*64) for path in m.SOURCES]


def test_characterization04_identity_is_the_next_characterization():
    m=api()
    assert (m.OUTPUT,m.KIND,m.VERSION)==(OUTPUT04,KIND04,3)
    assert m.OUTPUT not in ('runs/puck-cpu-runtime-characterization-02','runs/puck-cpu-runtime-characterization-03')
    assert m.VERSIONS==VERSIONS04 and 'torchvision' not in m.VERSIONS
    assert m.NATIVE_METADATA_PIN==NATIVE06
    raw=(ROOT/NATIVE06['path']).read_bytes();assert (len(raw),sha(raw))==(NATIVE06['size_bytes'],NATIVE06['sha256'])
    assert m.LIMITS['file_bytes']==16*1024**2 and m.LIMITS['output_bytes']==64*1024**2
    assert m.WORKER=='scripts/characterize_puck_episode_worker.py' and m.WORKER in m.SOURCES and m.WORKER in m.CAPSULE


def test_environment_freezes_the_episode_additions():
    m=api();env=m.ENVIRONMENT
    assert env['PYGLFW_LIBRARY']==str(m.ROOT/m.SITE)+'/glfw/x11/libglfw.so'
    assert env['__EGL_VENDOR_LIBRARY_FILENAMES']=='/puck/control/egl-vendor.json'
    assert env['MESA_SHADER_CACHE_DISABLE']=='true' and env['PYGAME_HIDE_SUPPORT_PROMPT']=='hide'
    assert env['MUJOCO_GL']=='egl' and env['PYOPENGL_PLATFORM']=='egl' and env['PATH']=='/nonexistent'
    assert env['HOME']=='/scratch/home' and env['TMPDIR']=='/scratch/tmp'


def test_capsule_is_the_held_worker_closure_without_the_bootstrap():
    m=api()
    spec=importlib.util.spec_from_file_location('qualifier_fixture',ROOT/'scripts/qualify_puck_cpu_held_runtime.py')
    q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
    assert set(m.CAPSULE)==set(q.EPISODE_WORKER_SOURCES)-{q.BOOTSTRAP}|{m.WORKER,m.HELPER}
    assert list(m.CAPSULE)==sorted(m.CAPSULE) and set(m.CAPSULE)<=set(m.SOURCES)
    assert {'scripts/characterize_puck_cpu_episode.py','scripts/qualify_puck_cpu_held_runtime.py'}<=set(m.SOURCES)


def test_configuration_is_exact_and_binds_the_frozen_characterization02_pins():
    m=api();config=m.configuration(authored_sources(m));m.validate_configuration(config)
    rows={r['path']:r for r in config['inputs']}
    assert rows[NATIVE06['path']]==NATIVE06
    assert rows['docs/plans/puck-cpu-retained-admission-02.json']['sha256']=='32605ca0d48537a6eabf98a54d605ad23bf525456760d83726381aeaf38e3e96'
    assert rows['docs/reports/puck-cpu-characterization-02/frozen-configuration.json']['sha256']=='4b98ff368e97351b2079ff44c75cb910d08559e5e037a6afc4887c28cd38fea8'
    assert 'docs/plans/puck-cpu-characterization-native-metadata-05.json' not in rows and len(rows)==10
    assert config['episode']['schedule']==dict(ticks=48,actions=[[0,1.0,0.0],[24,1.0,0.5]])
    assert config['episode']['profile']==dict(controller='manual',device='cpu',seed=7,scenario='reproduction',texture='checker')
    ids=config['episode']['run_ids']
    assert set(ids)=={'source','replay'} and ids['source']!=ids['replay'] and all(len(v)==32 for v in ids.values())
    assert config['renderer']==dict(vendor='Mesa',renderer_contains='llvmpipe',version=GL_VERSION,
        egl_vendor='Mesa Project',egl_version='1.5',backend='egl')


@pytest.mark.parametrize('defect',['kind','bool-version','output02','torchvision','native05','limits','glfw','egl',
    'ticks','seed','run-ids','renderer','source-missing','input-pin','extra-key','authority'])
def test_configuration_refuses_drift(defect):
    m=api();config=m.configuration(authored_sources(m));m.validate_configuration(config)
    if defect=='kind':config['kind']='puck-cpu-runtime-characterization-v2'
    elif defect=='bool-version':config['version']=True
    elif defect=='output02':config['output']='runs/puck-cpu-runtime-characterization-02'
    elif defect=='torchvision':config['expected_versions']['torchvision']='0.24.0+cpu'
    elif defect=='native05':config['roles']['native_metadata']='docs/plans/puck-cpu-characterization-native-metadata-05.json'
    elif defect=='limits':config['limits']['normal_seconds']+=1
    elif defect=='glfw':config['environment']['PYGLFW_LIBRARY']='/usr/lib/libglfw.so.3'
    elif defect=='egl':config['environment']['__EGL_VENDOR_LIBRARY_FILENAMES']='/usr/share/glvnd/egl_vendor.d/50_mesa.json'
    elif defect=='ticks':config['episode']['schedule']['ticks']=47
    elif defect=='seed':config['episode']['profile']['seed']=8
    elif defect=='run-ids':config['episode']['run_ids']['replay']=config['episode']['run_ids']['source']
    elif defect=='renderer':config['renderer']['version']='4.6 (Core Profile) Mesa 26.2.2'
    elif defect=='source-missing':config['sources']=[r for r in config['sources'] if r['path']!=m.WORKER]
    elif defect=='input-pin':next(r for r in config['inputs'] if r['path']==NATIVE06['path'])['sha256']='0'*64
    elif defect=='extra-key':config['qualification']=True
    else:config['runtime_qualified']=True
    with pytest.raises(ValueError):m.validate_configuration(config)


def test_requests_mirror_the_held_episode_descriptor():
    m=api();source=m.episode_request('source',source_files=[],distributions=[])
    replay=m.episode_request('replay',source_files=[],distributions=[])
    assert source['kind']=='puck-episode-characterization-request-v1' and source['version']==1
    for request,phase in ((source,'source'),(replay,'replay')):
        episode=request['episode']
        assert episode['kind']=='puck-held-public-episode-v1' and episode['phase']==phase
        assert episode['expected_versions']==VERSIONS04 and request['expected_versions']==VERSIONS04
        assert episode['upstream_commit']=='8d964599119b420de67ee259434d273651a1a76d'
        assert episode['paths']['output_root']=='/output' and episode['paths']['asset_root']=='/scratch/assets'
        assert request['environment']==m.ENVIRONMENT and request['source_root']=='/puck/source'
        assert request['runtime']['files']==[dict(path='python3.11',size_bytes=21662864,
            sha256='572cfa2a8597e2f431c785613539b1d219fa99eecf5ffb5765731a2ebc3e692a')]
    assert source['episode']['paths']['source_root']=='/output'
    assert replay['episode']['paths']['source_root']=='/puck/source-run'


def native(m):
    return dict(kind='puck-cpu-characterization-native-metadata-v6',
        native_files=[dict(path='/usr/lib/libEGL_mesa.so.0.0.0'),dict(path='/usr/lib/libLLVM.so.22.1')],
        aliases=[['/usr/lib/libEGL_mesa.so.0','libEGL_mesa.so.0.0.0']])


def binds(command,flag):
    return [(command[i+1],command[i+2]) for i,arg in enumerate(command) if arg==flag]


def test_sandbox_binds_v6_natives_control_capsule_and_the_source_run_only_for_replay(tmp_path):
    m=api();baseline=dict(python_prefix='/trusted/python',external_libraries=[],host_path_aliases=[['/lib','usr/lib']])
    paths={k:tmp_path/k for k in ('capsule','control','payload','run')}
    files=('pyproject.toml','scripts/characterize_puck_episode_worker.py')
    controls={'egl-vendor.json':paths['control']/'egl-vendor.json'}
    source=m.sandbox_command(baseline,native(m),phase='source',capsule=paths['capsule'],capsule_files=files,
        controls=dict(controls,**{'request-source.json':paths['control']/'request-source.json'}),
        payload=paths['payload'],request='request-source.json',request_sha='a'*64)
    replay=m.sandbox_command(baseline,native(m),phase='replay',capsule=paths['capsule'],capsule_files=files,
        controls=controls,payload=paths['payload'],source_run=paths['run'],request='request-replay.json',request_sha='b'*64)
    for command in (source,replay):
        readonly=binds(command,'--ro-bind')
        assert ('/usr/lib/libLLVM.so.22.1','/usr/lib/libLLVM.so.22.1') in readonly
        # Bound file by file: no capsule or control copy enters the retained output tree.
        assert (str(paths['capsule']/'pyproject.toml'),'/puck/source/pyproject.toml') in readonly
        assert not any(target=='/puck/source' for _,target in readonly)
        assert (str(paths['control']/'egl-vendor.json'),'/puck/control/egl-vendor.json') in readonly
        assert (str(m.ROOT/m.SITE),str(m.ROOT/m.SITE)) in readonly
        assert binds(command,'--bind')==[(str(paths['payload']),'/output')]
        assert ('libEGL_mesa.so.0.0.0','/usr/lib/libEGL_mesa.so.0') in binds(command,'--symlink')
        assert '--unshare-all' in command and '--clearenv' in command and '--share-net' not in command
        # Like the held episode namespace, no asset directory exists; the manual episode reads none.
        assert '/scratch/assets' not in command
        for key,value in m.ENVIRONMENT.items():
            assert any(command[i:i+3]==['--setenv',key,value] for i in range(len(command)))
        assert command[-6:-2]==['-B','-X','pycache_prefix=/scratch/pycache','/puck/source/'+m.WORKER]
    assert (str(paths['run']),'/puck/source-run') in binds(replay,'--ro-bind')
    assert not any(target=='/puck/source-run' for _,target in binds(source,'--ro-bind'))
    assert source[-2:]==['/puck/control/request-source.json','a'*64]
    assert (str(paths['control']/'request-source.json'),'/puck/control/request-source.json') in binds(source,'--ro-bind')
    for changes in (dict(source_run=paths['run']),dict(native=dict(native(m),kind='puck-cpu-characterization-native-metadata-v5')),
                    dict(capsule_files=('../escape.py',)),dict(controls={'../x':paths['control']})):
        arguments=dict(phase='source',capsule=paths['capsule'],capsule_files=files,controls=controls,
            payload=paths['payload'],request='r.json',request_sha='a'*64,native=native(m));arguments.update(changes)
        value=arguments.pop('native')
        with pytest.raises(ValueError):m.sandbox_command(baseline,value,**arguments)


# --- worker reports ---------------------------------------------------------

def report(m,phase,request_sha='a'*64,worker_sha='b'*64):
    config=m.configuration(authored_sources(m));episode=config['episode']
    bundle=dict(path=phase+'-bundle.zip',size_bytes=10085154,sha256='c'*64)
    claims=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,executable=False,qualification_claims=[])
    if phase=='source':
        result=dict(kind=FAKE_RESULT_KIND,version=1,phase='source',run_id=episode['run_ids']['source'],
            source_run_id=episode['run_ids']['source'],ticks_requested=48,ticks_completed=48,final_phase='paused',
            initial_snapshot_id='d'*64,provenance_sha256='e'*64,versions=dict(VERSIONS04),
            renderer=dict(vendor='Mesa',renderer='llvmpipe (LLVM 22.1.8, 256 bits)',version=GL_VERSION,
                egl_vendor='Mesa Project',egl_version='1.5',backend='egl'),bundle=bundle,**claims)
    else:
        result=dict(kind=FAKE_RESULT_KIND,version=1,phase='replay',run_id=episode['run_ids']['replay'],
            source_run_id=episode['run_ids']['source'],ticks_requested=48,provenance_sha256='e'*64,
            versions=dict(VERSIONS04),replay=dict(status='passed',compared_ticks=48,compared_events=100,first_divergence=None),
            bundle=bundle,**claims)
    images=dict(images=[dict(device='00:1f',inode=7,path='/usr/lib/libLLVM.so.22.1',segments=4,executable=True)],
        map_bytes=100,map_lines=4,persistent_snapshot_only=True,transient_anonymous_jit_closure_qualified=False)
    return dict(kind=REPORT_KIND,version=1,status='observed',phase=phase,request_sha256=request_sha,source_sha256=worker_sha,
        environment_sha256=sha(canonical(m.ENVIRONMENT)),python_version='3.11.15 (main) [authored]',executable_path=m.PYTHON,
        pid=1,ppid=0,runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,
        executable=False,qualification_claims=[],expected_versions=dict(VERSIONS04),versions=dict(VERSIONS04),
        episode_result=result,process_creation_attempts=dict(count=0,events=[]),import_misses=['org'],rechecks=9,
        cache=dict(modules=[dict(name='gymnasium',spec_name='gymnasium',file=str(m.ROOT/m.SITE)+'/gymnasium/__init__.py',
            classification='module',exports=[])],attribute_edges=1,module_objects=1,cache_entries=1,
            export_scope='exceptional_cache_identities'),
        maps=copy.deepcopy(images),baseline_maps=copy.deepcopy(images),environment_unchanged=True,pycache_unchanged=True,
        native_cache_dispatch=dict(events=[],unattributed=[],errors=[]),observation_errors=[],seconds=6.5)


@pytest.mark.parametrize('phase',['source','replay'])
def test_report_validation_accepts_the_exact_observation(phase):
    m=api();m.validate_report(report(m,phase),phase=phase,request_sha256='a'*64,worker_sha256='b'*64)


@pytest.mark.parametrize('defect',['spawn','spawn-events','short','diverged','compared','torchvision','gl-version','renderer',
    'egl','versions','failed','observation-error','claims','phase','request-sha','worker-sha','environment','bundle-size',
    'run-id','error-key','slow','dispatch-unattributed','dispatch-error','dispatch-missing'])
def test_report_validation_refuses_incomplete_or_unsafe_observation(defect):
    m=api();phase='replay' if defect in ('diverged','compared') else 'source';value=report(m,phase)
    result=value['episode_result']
    if defect=='spawn':value['process_creation_attempts']=dict(count=1,events=['subprocess.Popen'])
    elif defect=='spawn-events':value['process_creation_attempts']=dict(count=0,events=['os.fork'])
    elif defect=='short':result['ticks_completed']=47
    elif defect=='diverged':result['replay']['first_divergence']=dict(tick=3)
    elif defect=='compared':result['replay']['compared_ticks']=47
    elif defect=='torchvision':value['cache']['modules'].append(dict(name='torchvision',spec_name='torchvision',file='/x.py',classification='module',exports=[]))
    elif defect=='gl-version':result['renderer']['version']='4.6 (Core Profile) Mesa 26.2.2'
    elif defect=='renderer':result['renderer']['renderer']='softpipe'
    elif defect=='egl':result['renderer']['egl_version']='1.4'
    elif defect=='versions':value['versions']['gymnasium']='1.2.0'
    elif defect=='failed':value['status']='failed'
    elif defect=='observation-error':value['observation_errors']=[dict(stage='maps',type='OSError',message='x')]
    elif defect=='claims':result['runtime_qualified']=True
    elif defect=='phase':value['phase']='replay'
    elif defect=='request-sha':value['request_sha256']='f'*64
    elif defect=='worker-sha':value['source_sha256']='f'*64
    elif defect=='environment':value['environment_unchanged']=False
    elif defect=='bundle-size':result['bundle']['size_bytes']=16*1024**2+1
    elif defect=='run-id':result['run_id']='0'*32
    elif defect=='error-key':value['error']=dict(type='x',message='y')
    elif defect=='dispatch-unattributed':value['native_cache_dispatch']['unattributed']=[dict(cache='_cython_x',keys=['late'])]
    elif defect=='dispatch-error':value['native_cache_dispatch']['errors']=[dict(error='dispatch changed or removed')]
    elif defect=='dispatch-missing':value.pop('native_cache_dispatch')
    else:value['seconds']=float(m.LIMITS['normal_seconds'])
    with pytest.raises(ValueError):m.validate_report(value,phase=phase,request_sha256='a'*64,worker_sha256='b'*64)


# --- real worker over authored packages -------------------------------------

FAKE_EPISODE='''import os,sys
MODE={mode!r}
def run(admission):
    admission.recheck()
    episode=admission._reg['episode']
    assert admission._source.read('pyproject.toml',1024)==b'[project]\\nversion = "0.0.0"\\n'
    assert len(admission._dependencies.distributions)==1 and admission._reg['runtime']['python_version']=='3.11.15'
    import numpy,torch,mujoco,gymnasium
    if MODE=='dispatch':
        import authoredcy._creator,authoredcy._fused
    if MODE=='spawn':
        import subprocess
        try:subprocess.run(['/bin/true'])
        except RuntimeError:pass
    if MODE=='environment':os.environ['AUTHORED']='1'
    if MODE=='raise':raise RuntimeError('authored episode failure')
    if episode['phase']=='replay':
        assert os.path.isdir(os.path.join(episode['paths']['source_root'],episode['run_ids']['source']))
    else:
        os.mkdir(os.path.join(episode['paths']['output_root'],episode['run_ids']['source']))
    return dict(kind='{kind}',phase=episode['phase'],ticks=episode['schedule']['ticks'])
'''


def capsule(tmp_path,mode):
    root=tmp_path/'capsule';site=tmp_path/'site'
    if root.exists():
        files=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file())
        return root,site,[dict(path=p,size_bytes=(root/p).stat().st_size,sha256=sha((root/p).read_bytes())) for p in files]
    (root/'src/palimpsest').mkdir(parents=True);(root/'scripts').mkdir()
    (root/'src/palimpsest/__init__.py').write_text('')
    (root/'src/palimpsest/puck_held_episode.py').write_text(FAKE_EPISODE.format(mode=mode,kind=FAKE_RESULT_KIND))
    (root/'pyproject.toml').write_bytes(b'[project]\nversion = "0.0.0"\n')
    for path in (WORKER,HELPER):shutil.copyfile(path,root/'scripts'/path.name)
    for name,version in VERSIONS04.items():
        (site/name).mkdir(parents=True);(site/name/'__init__.py').write_text('__version__='+repr(version)+'\n')
    if mode=='dispatch':
        from puck_episode_authored import authored_cython
        authored_cython(site)
    files=sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file())
    pins=[dict(path=p,size_bytes=(root/p).stat().st_size,sha256=sha((root/p).read_bytes())) for p in files]
    return root,site,pins


def run_worker(m,tmp_path,mode='ok',phase='source',tamper=None):
    root,site,pins=capsule(tmp_path,mode)
    output=tmp_path/('out-'+phase);output.mkdir();pycache=tmp_path/'pycache';pycache.mkdir(mode=0o700,exist_ok=True)
    request=m.episode_request(phase,source_files=pins,distributions=[dict(name='gymnasium',version='1.2.1',root_index=0,
        metadata_path='gymnasium-1.2.1.dist-info/METADATA')])
    request.update(site_root=str(site),source_root=str(root),output_root=str(output),pycache_prefix=str(pycache))
    request['episode']['paths'].update(output_root=str(output),asset_root=str(tmp_path/'assets'),
        source_root=str(output) if phase=='source' else str(tmp_path/'out-source'))
    raw=canonical(request);path=tmp_path/('request-'+phase+'.json');path.write_bytes(raw)
    digest=tamper or sha(raw)
    observed=subprocess.run([m.PYTHON,'-I','-S','-B','-X','pycache_prefix='+str(pycache),str(root/'scripts'/WORKER.name),str(path),digest],
        env=m.ENVIRONMENT,capture_output=True,text=True,timeout=30,cwd=tmp_path)
    target=output/'characterization.json'
    return observed,(json.loads(target.read_bytes()) if target.exists() else None),sha(raw),root


def test_worker_observes_the_authored_episode_cache_and_maps(tmp_path):
    m=api();observed,value,request_sha,root=run_worker(m,tmp_path)
    assert observed.returncode==0,observed.stderr
    assert value['kind']==REPORT_KIND and value['status']=='observed' and value['phase']=='source'
    assert value['request_sha256']==request_sha and value['source_sha256']==sha(WORKER.read_bytes())
    assert value['versions']==VERSIONS04 and value['episode_result']['kind']==FAKE_RESULT_KIND
    assert value['process_creation_attempts']==dict(count=0,events=[]) and value['rechecks']>=1
    names={r['name']:r for r in value['cache']['modules']}
    assert names['gymnasium']['file']==str(tmp_path/'site/gymnasium/__init__.py')
    assert names['palimpsest.puck_held_episode']['file']==str(root/'src/palimpsest/puck_held_episode.py')
    assert 'characterize_puck_runtime_imports' not in names and '_episode_characterization_helpers' not in names
    assert value['baseline_maps']['images'] and value['maps']['images']
    assert value['environment_unchanged'] is True and value['observation_errors']==[]
    assert json.loads(observed.stdout)['report_sha256']==sha((tmp_path/'out-source/characterization.json').read_bytes())


def test_worker_replay_phase_reads_the_source_run(tmp_path):
    m=api();first,_,_,_=run_worker(m,tmp_path)
    assert first.returncode==0,first.stderr
    observed,value,_,_=run_worker(m,tmp_path,phase='replay')
    assert observed.returncode==0,observed.stderr
    assert value['status']=='observed' and value['phase']=='replay'


@pytest.mark.parametrize('mode,expected',[('spawn','process creation'),('environment','environment'),('raise','authored episode failure')])
def test_worker_records_refused_process_creation_and_failures(tmp_path,mode,expected):
    m=api();observed,value,_,_=run_worker(m,tmp_path,mode=mode)
    assert observed.returncode==1 and value['status']=='failed'
    assert expected in value['error']['message']
    if mode=='spawn':
        assert value['process_creation_attempts']['count']==1
        assert value['process_creation_attempts']['events']==['subprocess.Popen']
    if mode=='environment':assert value['environment_unchanged'] is False


def test_worker_refuses_a_request_with_a_different_external_sha(tmp_path):
    m=api();observed,value,_,_=run_worker(m,tmp_path,tamper='0'*64)
    assert observed.returncode==1 and value is None


def test_importing_the_worker_installs_no_audit_hook():
    script=f"""import importlib.util,subprocess,sys
s=importlib.util.spec_from_file_location('worker_import_only',{str(WORKER)!r})
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
subprocess.run(['/bin/true'],check=True);print('spawned')
"""
    observed=subprocess.run([api().PYTHON,'-I','-S','-B','-c',script],capture_output=True,text=True,timeout=20)
    assert observed.returncode==0 and observed.stdout.strip()=='spawned',observed.stderr


@pytest.mark.skipif(shutil.which('bwrap') is None and not os.path.exists('/usr/bin/bwrap'),reason='bwrap unavailable')
def test_real_namespace_probe_and_both_authored_phases(tmp_path,monkeypatch):
    m=api();baseline=json.loads((ROOT/'docs/plans/puck-python-louvain-host-baseline-v1.json').read_bytes())
    root,site,pins=capsule(tmp_path,'ok');(tmp_path/'docs').mkdir()
    monkeypatch.setattr(m,'ROOT',tmp_path);monkeypatch.setattr(m,'SITE','site')
    monkeypatch.setattr(m,'ENVIRONMENT',dict(m.ENVIRONMENT,PYGLFW_LIBRARY=str(site)+'/glfw/x11/libglfw.so'))
    control=tmp_path/'control';control.mkdir();payloads={}
    empty=dict(kind='puck-cpu-characterization-native-metadata-v6',native_files=[],aliases=[])
    files=[row['path'] for row in pins];(control/'egl-vendor.json').write_bytes(b'{}\n')
    controls={'egl-vendor.json':control/'egl-vendor.json'}
    probe=subprocess.run(m.sandbox_command(baseline,empty,phase='source',capsule=root,capsule_files=files,controls=controls,
        payload=tmp_path,request=None,request_sha=None,probe=True),capture_output=True,text=True,timeout=30)
    assert probe.returncode==0,probe.stderr
    assert json.loads(probe.stdout)['network_isolated'] is True
    for phase in ('source','replay'):
        payloads[phase]=tmp_path/('payload-'+phase);payloads[phase].mkdir()
        request=m.episode_request(phase,source_files=pins,distributions=[dict(name='gymnasium',version='1.2.1',
            root_index=0,metadata_path='gymnasium-1.2.1.dist-info/METADATA')])
        raw=canonical(request);(control/('request-'+phase+'.json')).write_bytes(raw)
        command=m.sandbox_command(baseline,empty,phase=phase,capsule=root,capsule_files=files,
            controls=dict(controls,**{'request-'+phase+'.json':control/('request-'+phase+'.json')}),payload=payloads[phase],
            source_run=payloads['source'] if phase=='replay' else None,request='request-'+phase+'.json',request_sha=sha(raw))
        observed=subprocess.run(command,capture_output=True,text=True,timeout=60)
        assert observed.returncode==0,observed.stderr
        value=json.loads((payloads[phase]/'characterization.json').read_bytes())
        assert value['status']=='observed' and value['phase']==phase and value['versions']==VERSIONS04


def test_main_refuses_a_different_configuration_sha_before_any_reservation(tmp_path):
    m=api();config=m.configuration(authored_sources(m));raw=(json.dumps(config,sort_keys=True,indent=2)+'\n').encode()
    path=tmp_path/'configuration.json';path.write_bytes(raw)
    observed=subprocess.run([m.PYTHON,'-I','-S','-B',str(SCRIPT),'--configuration',str(path),'--sha256','0'*64],
        capture_output=True,text=True,timeout=30,start_new_session=True)
    assert observed.returncode!=0 and 'Configuration SHA differs' in observed.stderr
    assert not (ROOT/OUTPUT04).exists()


def test_worker_attributes_shared_cache_dispatch_to_each_producer_phase(tmp_path):
    m=api();observed,value,_,_=run_worker(m,tmp_path,mode='dispatch')
    assert observed.returncode==0,observed.stderr
    dispatch=value['native_cache_dispatch']
    assert dispatch['unattributed']==[] and dispatch['errors']==[]
    assert [e for e in dispatch['events'] if e['cache']=='_cython_authored']==[
        dict(cache='_cython_authored',producer='authoredcy._creator',phase='module_exec',added=['cython_function_or_method'],first=True),
        dict(cache='_cython_authored',producer='authoredcy._fused',phase='module_exec',added=['fused_cython_function'],first=False)]
