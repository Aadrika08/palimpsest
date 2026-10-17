"""Allocation 16 episode parent: identity, configuration, v4 registration and receipt checks.

Authored data only; no allocation runs here (see the _integration test).
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import types

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/run_puck_cpu_held_episode.py'
# Independently authored identity; do not derive from producer constants.
KIND16='puck-cpu-held-episode-allocation-v16'
OUTPUT16='runs/puck-cpu-held-episode-16'
STAGE04='/tmp/palimpsest-puck-cpu-held-04'
CLOCKS=dict(normal_seconds=720,child_hard_seconds=735,hard_seconds=750)
CENSUS_ABSENT={'cffi','charset_normalizer','cython','glfw_preview','scikits','scipy._distributor_init_local',
               'scipy.linalg._cblas','scipy.linalg._clapack','scipy.linalg._fblas_64','scipy.linalg._flapack_64'}


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def api():
    assert SCRIPT.is_file(),'allocation-16 episode parent is missing'
    return load(SCRIPT,'episode16_parent_fixture')


def qualifier():
    return load(ROOT/'scripts/qualify_puck_cpu_held_runtime.py','episode16_qualifier_fixture')


def config(m,q):
    sources=sorted([dict(path=p,size_bytes=0 if p.endswith('fly-gym/core/__init__.py') else 1,sha256='a'*64)
                    for p in [*q.PREPARATION04_SOURCES,m.PARENT]],key=lambda r:r['path'])
    inputs={role:dict(path='docs/authored-'+role+'.json',size_bytes=1,sha256='b'*64) for role in q.PREPARATION04_INPUT_ROLES}
    acceptance=dict(configuration=dict(path='authored-prepare04-configuration.json',size_bytes=1,sha256='c'*64),
        result=dict(path='runs/puck-cpu-held-preparation-04/result.json',size_bytes=1,sha256='d'*64),
        independent_audit=dict(path='docs/authored/prepare04-audit.json',size_bytes=1,sha256='e'*64),
        externally_observed_auditor_cli=dict(path='docs/authored/prepare04-audit-cli.json',size_bytes=1,sha256='f'*64))
    return dict(kind=KIND16,version=16,allocation_id=16,root=str(m.ROOT),stage_parent=STAGE04,sources=sources,inputs=inputs,
        interpreter=dict(q.INTERPRETER),environment=dict(m.ENVIRONMENT),expected_versions=dict(m.VERSIONS),limits=dict(m.LIMITS),
        negative_imports=list(m.NEGATIVE_IMPORTS),hidden_imports=list(m.HIDDEN_IMPORTS),claims=dict(m.CLAIMS),
        preparation_acceptance=acceptance,run_ids=dict(source='1'*32,replay='2'*32))


def test_allocation16_identity_clocks_environment_and_rosters():
    m=api();q=qualifier()
    assert (m.KIND,m.VERSION,m.OUTPUT)==(KIND16,16,OUTPUT16)
    assert {k:m.LIMITS[k] for k in CLOCKS}==CLOCKS and m.WORKER_SECONDS==360
    assert m.LIMITS['file_bytes']==16*1024**2 and m.LIMITS['output_bytes']==64*1024**2
    assert m.ENVIRONMENT['PYGLFW_LIBRARY']=='/puck/staged/inputs/root-0000/glfw/x11/libglfw.so'
    assert m.ENVIRONMENT['__EGL_VENDOR_LIBRARY_FILENAMES']=='/puck/control/egl-vendor.json'
    assert {k:v for k,v in m.ENVIRONMENT.items() if k in q.ENVIRONMENT}==q.ENVIRONMENT
    assert len(m.NEGATIVE_IMPORTS)==42 and set(m.NEGATIVE_IMPORTS)==set(q.QUALIFY11_NEGATIVE_IMPORTS)|CENSUS_ABSENT
    assert m.HIDDEN_IMPORTS==q.QUALIFY11_HIDDEN_IMPORTS and 'torchvision' not in m.VERSIONS
    raw=Path(m.SYSCONFIGDATA['path']).read_bytes()
    assert (len(raw),hashlib.sha256(raw).hexdigest())==(m.SYSCONFIGDATA['size_bytes'],m.SYSCONFIGDATA['sha256'])


def test_exact_configuration_is_admitted():
    m=api();q=qualifier();m.validate_configuration(config(m,q),q)


@pytest.mark.parametrize('defect',['kind','bool-version','stage03','limits','glfw-site','egl-path','torchvision',
    'roster','hidden','run-ids-equal','run-ids-char04','run-id-shape','no-parent','extra-source','no-replay-role',
    'acceptance-path','authority','extra-key'])
def test_configuration_refuses_drift(defect):
    m=api();q=qualifier();value=config(m,q)
    if defect=='kind':value['kind']='puck-cpu-held-runtime-allocation-v16'
    elif defect=='bool-version':value['version']=True
    elif defect=='stage03':value['stage_parent']='/tmp/palimpsest-puck-cpu-held-03'
    elif defect=='limits':value['limits']['normal_seconds']=360
    elif defect=='glfw-site':value['environment']['PYGLFW_LIBRARY']='/usr/lib/libglfw.so.3'
    elif defect=='egl-path':value['environment']['__EGL_VENDOR_LIBRARY_FILENAMES']='/usr/share/glvnd/egl_vendor.d/50_mesa.json'
    elif defect=='torchvision':value['expected_versions']['torchvision']='0.24.0+cpu'
    elif defect=='roster':value['negative_imports']=value['negative_imports'][1:]
    elif defect=='hidden':value['hidden_imports']=['networkx']
    elif defect=='run-ids-equal':value['run_ids']['replay']=value['run_ids']['source']
    elif defect=='run-ids-char04':value['run_ids']['source']='a6effc7912fec337875d13ae69445e43'
    elif defect=='run-id-shape':value['run_ids']['source']='G'*32
    elif defect=='no-parent':value['sources']=[r for r in value['sources'] if r['path']!=m.PARENT]
    elif defect=='extra-source':value['sources']=sorted(value['sources']+[dict(path='scripts/zz.py',size_bytes=1,sha256='a'*64)],key=lambda r:r['path'])
    elif defect=='no-replay-role':value['inputs'].pop('observation_replay_report')
    elif defect=='acceptance-path':value['preparation_acceptance']['result']['path']='runs/puck-cpu-held-preparation-03/result.json'
    elif defect=='authority':value['claims']['runtime_qualified']=True
    else:value['phase']='qualify'
    with pytest.raises(ValueError):m.validate_configuration(value,q)


@pytest.mark.parametrize('phase',['source','replay'])
def test_v4_registration_is_accepted_by_the_frozen_bootstrap(phase):
    m=api();q=qualifier();value=config(m,q)
    files=[dict(path=p,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
           for p in q.EPISODE_WORKER_SOURCES for raw in ((ROOT/p).read_bytes() if (ROOT/p).exists() else b'',)]
    bootstrap=(ROOT/m.BOOTSTRAP).read_bytes();dependency=b'{"authored":true}'
    registration,raw,command=m.registration(value,phase,files,dependency,bootstrap,q)
    api_=types.ModuleType('frozen_bootstrap');exec(compile(bootstrap,str(ROOT/m.BOOTSTRAP),'exec'),api_.__dict__)
    parsed,modules,_=api_._parse(raw,hashlib.sha256(raw).hexdigest())
    assert parsed['version']==4 and parsed['deadline_seconds']==360 and 'palimpsest.puck_held_episode' in modules
    episode=parsed['episode']
    assert episode['phase']==phase and episode['negative_imports']==m.NEGATIVE_IMPORTS and episode['hidden_imports']==m.HIDDEN_IMPORTS
    assert episode['paths']==dict(output_root='/output',asset_root='/scratch/assets',
                                  source_root='/output' if phase=='source' else '/puck/source-run')
    assert episode['run_ids']==value['run_ids'] and episode['stdlib_exception']==m.SYSCONFIGDATA
    assert command[-1]==hashlib.sha256(raw).hexdigest() and command[-2]=='/puck/control/worker-registration-'+phase+'.json'


def receipt(m,value,phase,registration_raw,dependency_raw,dependencies):
    bundle=dict(path=phase+'-bundle.zip',size_bytes=100,sha256='c'*64)
    claims=dict(runtime_qualified=False,native_authorized=False,collection_authorized=False,executable=False,qualification_claims=[])
    entry=dict(kind='puck-held-public-episode-result-v1',version=1,phase=phase,run_id=value['run_ids'][phase],
        source_run_id=value['run_ids']['source'],ticks_requested=48,provenance_sha256='d'*64,versions=dict(m.VERSIONS),bundle=bundle,**claims)
    if phase=='source':
        entry.update(ticks_completed=48,final_phase='paused',initial_snapshot_id='e'*32,
            renderer=dict(vendor='Mesa',renderer='llvmpipe (LLVM 22.1.8, 256 bits)',version='4.6 (Compatibility Profile) Mesa 26.2.2-arch1.1',
                          egl_vendor='Mesa Project',egl_version='1.5',backend='egl'))
    else:entry['replay']=dict(status='passed',compared_ticks=48,compared_events=100,first_divergence=None)
    return dict(kind='puck-worker-source-bootstrap-receipt-v1',registration_sha256=hashlib.sha256(registration_raw).hexdigest(),
        interpreter_object_bound=True,python_version='3.11.15',runtime_qualified=False,dependencies_qualified=False,
        native_authorized=False,collection_authorized=False,executable=False,qualification_claims=[],
        expected_missing_imports=list(m.NEGATIVE_IMPORTS),expected_hidden_imports=list(m.HIDDEN_IMPORTS),denied_imports=['org'],
        episode_phase=phase,process_creation_attempts=dict(count=0,events=[]),
        dependencies=dict(registration_sha256=hashlib.sha256(dependency_raw).hexdigest(),native_identity='tmpfs-raw-dev-inode-v1',
            root_count=4,file_count=1,input_bytes=2,native_cache_modules=[]),entry_result=entry)


@pytest.mark.parametrize('defect',[None,'spawn','phase','hidden','denied','short','diverged','renderer','torchvision',
    'registration','claims','bundle-size'])
def test_receipt_validation_requires_a_clean_complete_episode(defect):
    m=api();q=qualifier();value=config(m,q);dependencies=dict(roots=[dict(files=[dict(size_bytes=2)])],import_profile=dict(native_cache=[]))
    phase='replay' if defect=='diverged' else 'source';registration_raw=b'{"registration":1}';dependency_raw=b'{"dependencies":1}'
    item=receipt(m,value,phase,registration_raw,dependency_raw,dependencies);entry=item['entry_result']
    if defect=='spawn':item['process_creation_attempts']=dict(count=1,events=['os.posix_spawn'])
    elif defect=='phase':item['episode_phase']='replay'
    elif defect=='hidden':item['expected_hidden_imports']=[]
    elif defect=='denied':item['denied_imports']=['requests']
    elif defect=='short':entry['ticks_completed']=47
    elif defect=='diverged':entry['replay']['first_divergence']=dict(tick=4)
    elif defect=='renderer':entry['renderer']['version']='4.6 (Core Profile) Mesa 26.2.2'
    elif defect=='torchvision':entry['versions']['torchvision']='0.24.0+cpu'
    elif defect=='registration':item['registration_sha256']='0'*64
    elif defect=='claims':entry['executable']=True
    elif defect=='bundle-size':entry['bundle']['size_bytes']=16*1024**2+1
    if defect is None:m.validate_receipt(item,value,phase,registration_raw,dependency_raw,dependencies)
    else:
        with pytest.raises(ValueError):m.validate_receipt(item,value,phase,registration_raw,dependency_raw,dependencies)


def episode_observer(tmp_path,monkeypatch,body):
    from test_puck_cpu_held_observer import setup
    m,path,_=setup(tmp_path,monkeypatch,'raise AssertionError("the qualifier must not launch")\n')
    (tmp_path/'scripts/run_puck_cpu_held_episode.py').write_text(body)
    return m,path


@pytest.mark.parametrize('code',[0,7])
def test_observer_runs_the_episode_parent_once_with_clocks_beyond_750(tmp_path,monkeypatch,code):
    m,path=episode_observer(tmp_path,monkeypatch,'import sys\nprint("AUTHORED16 transport")\nsys.exit('+str(code)+')\n')
    raw=m.canonical(dict(kind=KIND16,version=16,allocation_id=16,root=str(tmp_path)));path.write_bytes(raw)
    waits=[];popen=m.subprocess.Popen
    class Recording(popen):
        def wait(self,timeout=None):
            waits.append(timeout);return super().wait(timeout=timeout)
    monkeypatch.setattr(m.subprocess,'Popen',Recording)
    result=m.observe(path,hashlib.sha256(raw).hexdigest())
    assert result['observed_returncode']==code and result['timed_out'] is False and result['phase']=='episode'
    assert result['command'][4]==str(tmp_path/'scripts/run_puck_cpu_held_episode.py')
    assert result['stdout']['path']==OUTPUT16+'-external-cli.stdout'
    assert 750<waits[0]<=780 and m.EPISODE_SECONDS==(780,795) and m.EXTENDED_SECONDS=={14:(400,415)}
    assert m.signal.getitimer(m.signal.ITIMER_REAL)[0]==0
    with pytest.raises(FileExistsError):m.observe(path,hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize('field,value',[('version',15),('version',True),('allocation_id',15),('phase','qualify'),('root','/elsewhere')])
def test_observer_rejects_mixed_episode_identity_before_launch(tmp_path,monkeypatch,field,value):
    m,path=episode_observer(tmp_path,monkeypatch,'raise AssertionError("must not launch")\n')
    config=dict(kind=KIND16,version=16,allocation_id=16,root=str(tmp_path));config[field]=value
    raw=m.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):m.observe(path,hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]
