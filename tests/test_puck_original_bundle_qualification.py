"""Authored model fixtures and public metadata, never actual retained bundles."""
import copy
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time

import pytest

ROOT=Path(__file__).parents[1]


def module():
    name='scripts.qualify_puck_original_bundles_v1'
    assert importlib.util.find_spec(name) is not None,'Original bundle qualification runner absent'
    return importlib.import_module(name)


def candidate():
    m=module()
    from palimpsest import puck_bundle_provenance as p
    report=json.loads((ROOT/'docs/reports/m6-puck-training-v2.json').read_bytes())
    def descriptor(name,raw):
        return {'path':name,'size_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    sources=[descriptor(name,(ROOT/name).read_bytes()) for name in m.source_paths()]
    history=ROOT/'docs/prerequisites/puck-original-producer-v1'
    historical=[descriptor(name,(history/name).read_bytes()) for name in sorted(p.HISTORICAL_SOURCES)]
    bundles=[]
    for row in report['models']:
        for name,value in sorted(row['files'].items()):
            bundles.append({'path':f"seed-{row['seed']}/{name}",
                'size_bytes':value['bytes'],'sha256':value['sha256']})
    return copy.deepcopy({'schema':m.SCHEMA,'attempt':1,'attempts':1,'repo_root':str(ROOT),
        'python_executable':m.PYTHON,'environment':m.ENVIRONMENT,
        'output':str(ROOT/'runs/puck-original-bundle-qualification-v1-attempt-01'),
        'seeds':[21,22,23],'model_calls':3,'native_owners':0,'physics_steps':0,
        'limits':m.LIMITS,'claims':m.CLAIMS,'inputs':{
            'sources':{'root':str(ROOT),'files':sources},
            'historical':{'root':str(history),'files':historical},
            'bundles':{'root':m.BUNDLE_ROOT,'files':bundles},
            'runtime':{'root':m.RUNTIME_ROOT,'files':[m.RUNTIME_PIN]}}})


def test_exact_public_freeze_validates_without_opening_actual_bundle_or_runtime(tmp_path):
    m=module();value=candidate();path=tmp_path/'freeze.json';raw=m.canonical(value)
    path.write_bytes(raw)
    assert m.read_freeze(path,hashlib.sha256(raw).hexdigest())==value
    assert value['model_calls']==3 and value['native_owners']==0


@pytest.mark.parametrize('field,value',[('attempt',True),('attempt',2),('model_calls',3.0),
    ('native_owners',1),('physics_steps',True),('seeds',[21,23,22]),
    ('claims',{'qualification_claims':['passed']}),('environment',{}),('limits',{})])
def test_changed_allocation_or_type_alias_refuses_before_reservation(tmp_path,field,value):
    m=module();sample=candidate();sample[field]=value
    raw=m.canonical(sample);path=tmp_path/'freeze.json';path.write_bytes(raw)
    with pytest.raises(ValueError):m.read_freeze(path,hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize('defect',['source-missing','source-extra','bundle-size','bundle-pin',
    'bundle-root','history-pin','history-extra','runtime-size','runtime-pin','runtime-root',
    'output','interpreter','extra-field','freeze-pin','noncanonical'])
def test_freeze_roles_and_original_public_identities_are_exact(tmp_path,defect):
    m=module();sample=candidate()
    if defect=='source-missing':sample['inputs']['sources']['files'].pop()
    elif defect=='source-extra':sample['inputs']['sources']['files'].append(
        {'path':'foreign.py','size_bytes':0,'sha256':'0'*64})
    elif defect=='bundle-size':sample['inputs']['bundles']['files'][0]['size_bytes']+=1
    elif defect=='bundle-pin':sample['inputs']['bundles']['files'][0]['sha256']='0'*64
    elif defect=='bundle-root':sample['inputs']['bundles']['root']='/substitute'
    elif defect=='history-pin':sample['inputs']['historical']['files'][0]['sha256']='0'*64
    elif defect=='history-extra':sample['inputs']['historical']['files'].append(
        {'path':'foreign.py','size_bytes':0,'sha256':'0'*64})
    elif defect=='runtime-size':sample['inputs']['runtime']['files'][0]['size_bytes']=1048576
    elif defect=='runtime-pin':sample['inputs']['runtime']['files'][0]['sha256']='0'*64
    elif defect=='runtime-root':sample['inputs']['runtime']['root']='/substitute'
    elif defect=='output':sample['output']=sample['inputs']['bundles']['root']+'/overlap'
    elif defect=='interpreter':sample['python_executable']='/other/python'
    elif defect=='extra-field':sample['retry']=True
    raw=m.canonical(sample)
    if defect=='noncanonical':raw+=b' '
    path=tmp_path/'freeze.json';path.write_bytes(raw)
    digest='0'*64 if defect=='freeze-pin' else hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError):m.read_freeze(path,digest)


@pytest.mark.parametrize('seed',[21,22,23])
def test_private_worker_uses_actual_cpu_mlp_and_six_fixed_negatives_on_authored_bytes(seed):
    module()
    script=r'''
import hashlib,time,sys
from test_puck_bundle_provenance import fixture
from palimpsest import puck_bundle_provenance as p
from scripts.qualify_puck_original_bundles_v1 import qualify_model
seed=int(sys.argv[1]);sample=fixture(seed)
pins={name:hashlib.sha256(value).hexdigest() for name,value in sample['bundle_payloads'].items()}
def admit(**values):
    if values['seed']!=seed:
        raise ValueError('Original model artifact pin differs: report.json')
    for name in ('report.json','protocol.json','checkpoint.npz'):
        if hashlib.sha256(values['bundle_payloads'][name]).hexdigest()!=pins[name]:
            raise ValueError('Original model artifact pin differs: '+name)
    return p._validate_lineage(seed=values['seed'],bundle_payloads=values['bundle_payloads'],
        historical_source_payloads=values['historical_source_payloads'],
        expected_source_hashes=sample['expected_source_hashes'],expected_collection_sha256='c'*64)
result=qualify_model(seed,b'authored index',sample['bundle_payloads'],sample['historical_source_payloads'],
    time.monotonic()+20,admitter=admit)
assert result['seed']==seed and result['model_calls']==1
assert len(result['negatives'])==6 and all(row['rejected'] is True for row in result['negatives'])
assert result['action_dtype']=='float64' and len(result['action'])==2
assert result['parameters_restored'] is True
assert result['runtime']=={'python':'3.11.15','numpy':'2.2.5','torch':'2.9.0',
    'threads':1,'device':'cpu','deterministic_algorithms':True,'cuda_initialized':False}
assert 'mujoco' not in sys.modules and 'palimpsest.engine' not in sys.modules
'''
    result=subprocess.run([sys.executable,'-c',script,str(seed)],capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stderr


def test_expired_private_core_refuses_before_admitter_or_torch_import():
    m=module();called=[]
    def admit(**kwargs):called.append(True);raise AssertionError('expired call entered')
    with pytest.raises(TimeoutError):m.qualify_model(21,b'',{}, {},time.monotonic()-1,admitter=admit)
    assert called==[]


def test_import_runner_does_not_import_numerical_or_native_runtime():
    module()
    result=subprocess.run([sys.executable,'-c',
        "import scripts.qualify_puck_original_bundles_v1,sys; assert 'torch' not in sys.modules; assert 'mujoco' not in sys.modules; assert 'numpy' not in sys.modules"],
        capture_output=True,text=True,timeout=10)
    assert result.returncode==0,result.stderr


def test_invocation_refuses_wrong_interpreter_and_environment_without_reservation(monkeypatch):
    m=module()
    with pytest.raises(ValueError,match='interpreter'):m.check_invocation({'python_executable':'/other/python'})
    for key,value in m.ENVIRONMENT.items():monkeypatch.setenv(key,value)
    m.check_invocation({'python_executable':sys.executable})
    monkeypatch.setenv('CUDA_VISIBLE_DEVICES','0')
    with pytest.raises(ValueError,match='environment'):m.check_invocation({'python_executable':sys.executable})


def test_terminal_publication_rechecks_still_held_input_after_fsync(tmp_path,monkeypatch):
    m=module()
    publish=getattr(m,'_publish_terminal',None)
    assert callable(publish),'Terminal publication custody operation absent'
    from palimpsest import bounded_qualification as guard
    from palimpsest.puck_execution_files import HeldCollectionFiles
    source=tmp_path/'source';source.mkdir();leaf=source/'input';leaf.write_bytes(b'authored')
    output=tmp_path/'output';output.mkdir()
    held=HeldCollectionFiles(source,[{'path':'input','size_bytes':8,
        'sha256':hashlib.sha256(b'authored').hexdigest()}],time.monotonic()+30)
    original=guard.write_new
    def change(path,value,**kwargs):
        original(path,value,**kwargs)
        leaf.write_bytes(b'changed')
    monkeypatch.setattr(guard,'write_new',change)
    held.__enter__();rejected=False
    try:
        try:publish({'source':held},output,'a'*64,time.monotonic(),time.monotonic()+30)
        except (ValueError,RuntimeError):rejected=True
    finally:
        held.__exit__(RuntimeError,RuntimeError('test cleanup'),None)
    assert rejected,'Changed input passed terminal close after publication'
    assert (output/'terminal.json').is_file()


@pytest.mark.parametrize('different',[False,True])
def test_running_image_binding_uses_held_file_object_not_launcher_text(tmp_path,different):
    m=module();bind=getattr(m,'_bind_running_image',None)
    assert callable(bind),'Running process image binding absent'
    from palimpsest.puck_execution_files import HeldCollectionFiles
    root=tmp_path/'runtime';root.mkdir();binary=root/'python3.11';binary.write_bytes(b'authored')
    other=tmp_path/'other';other.write_bytes(b'authored')
    with HeldCollectionFiles(root,[{'path':'python3.11','size_bytes':8,
            'sha256':hashlib.sha256(b'authored').hexdigest()}],time.monotonic()+30) as held:
        observation=other.stat() if different else binary.stat()
        if different:
            with pytest.raises(ValueError,match='running image'):bind(held,image_stat=observation)
        else:bind(held,image_stat=observation)
    with pytest.raises(RuntimeError):bind(held,image_stat=binary.stat())
