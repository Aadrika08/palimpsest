"""Explicit q4 admission in epoch10; authored metadata/transport, no vendors."""
import copy
import json

import pytest

from test_puck_cpu_held_amendment05 import validate_both
from test_puck_cpu_held_amendment06 import OTHER_INPUTS, ROSTER06
from test_puck_cpu_held_amendment08 import DIAGNOSTIC_SOURCES
from test_puck_cpu_held_amendment09 import acceptance09_case
from test_puck_cpu_held_observer import setup as observer_setup
from test_puck_cpu_held_parent import result_case
from test_puck_cpu_held_runtime_audit import api as auditor_api


def acceptance10_case():
    m,config,blobs,old,candidate_c,candidate_d=acceptance09_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v10',version=10,allocation_id=10)
    return m,config,blobs,old,candidate_c,candidate_d


def test10_preserves_exact_preparation_projection_candidate_and_limits():
    m,config,blobs,old,_,candidate_d=acceptance10_case()
    prior,prepared=validate_both(m,config,blobs)
    assert m.allocation_output(config)==auditor_api().allocation_output(config)=='runs/puck-cpu-held-qualification-10'
    assert {r['path'] for r in config['sources'] if r!=next(p for p in prior['sources'] if p['path']==r['path'])}==set(DIAGNOSTIC_SOURCES)
    assert len(config['sources'])==24 and len(config['inputs'])==16
    assert config['negative_imports']==ROSTER06 and len(ROSTER06)==19
    assert all(config['inputs'][key]==prior['inputs'][key] for key in OTHER_INPUTS)
    assert prepared['sources']==prior['sources'] and prepared['inputs']==prior['inputs']
    assert config['limits']==m.LIMITS['qualify']
    m.validate_publication_candidate(old,candidate_d,pillow_origins=True)
    auditor_api().publication_candidate(old,candidate_d,pillow_origins=True)


@pytest.mark.parametrize('path',DIAGNOSTIC_SOURCES)
def test10_refuses_missing_preparation_relative_source_changes(path):
    m,config,blobs,*_=acceptance10_case();prior,_=validate_both(m,config,blobs)
    original=next(row for row in prior['sources'] if row['path']==path)
    config['sources']=[copy.deepcopy(original) if row['path']==path else row for row in config['sources']]
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


def test10_refuses_an_additional_source_change():
    m,config,blobs,*_=acceptance10_case();prior,_=validate_both(m,config,blobs)
    next(row for row in config['sources'] if row['path']=='src/palimpsest/puck_native_origins.py')['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('defect',['old-kind','old-version','old-id','bool-version','bool-id','prepare','limits','roster','environment','extra-field'])
def test10_refuses_identity_aliases_and_policy_expansion(defect):
    m,config,blobs,*_=acceptance10_case();validate_both(m,config,blobs)
    if defect=='old-kind':config['kind']='puck-cpu-held-runtime-allocation-v9'
    elif defect=='old-version':config['version']=9
    elif defect=='old-id':config['allocation_id']=9
    elif defect=='bool-version':config['version']=True
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='prepare':config.update(phase='prepare',limits=copy.deepcopy(m.LIMITS['prepare']))
    elif defect=='limits':config['limits']['normal_seconds']+=1
    elif defect=='roster':config['negative_imports']=ROSTER06+['unreviewed']
    elif defect=='environment':config['environment']['UNREVIEWED']='1'
    else:config['qualification_version']=4
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('role',OTHER_INPUTS)
def test10_preserves_every_noncandidate_input(role):
    m,config,blobs,*_=acceptance10_case();prior,_=validate_both(m,config,blobs)
    config['inputs'][role]['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


def test10_worker_registration_requires_explicit_q4_selection_and_keeps_default_q3():
    m,_,_=result_case()
    files=[dict(path=p,size_bytes=(m.ROOT/p).stat().st_size,sha256=m.digest((m.ROOT/p).read_bytes())) for p in m.WORKER_SOURCES]
    old,_=m.worker_registration(files,b'{}',negative_imports=['org'])
    selected,_=m.worker_registration(files,b'{}',negative_imports=['org'],qualification_version=4)
    assert old['qualification']['version']==3
    assert selected['qualification']['kind']=='puck-held-runtime-import-qualification-v4'
    assert selected['qualification']['version']==4
    for key in selected:
        if key!='qualification':assert selected[key]==old[key]
    for key in selected['qualification']:
        if key not in ('kind','version'):assert selected['qualification'][key]==old['qualification'][key]


@pytest.mark.parametrize('expected,observed',[(4,4),(3,3),(4,3),(3,4),(4,True)])
def test10_parent_binds_worker_result_to_selected_qualification(expected,observed):
    m,deps,result=result_case();result['entry_result']['qualification_version']=observed
    def check():
        m.validate_worker_result(result,registration_sha256='a'*64,dependency_sha256='b'*64,
            dependencies=deps,negative_imports=['org'],qualification_version=expected)
    if expected==observed and type(observed) is int:check()
    else:
        with pytest.raises(ValueError):check()


@pytest.mark.parametrize('code',[0,7])
def test10_observer_reserves_once_without_modifying_consumed09(tmp_path,monkeypatch,code):
    m,path,_=observer_setup(tmp_path,monkeypatch,'import sys\nprint("AUTHORED10 transport")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v10',version=10,allocation_id=10,phase='qualify')
    raw=m.canonical(config);path.write_bytes(raw)
    old=tmp_path/'runs/puck-cpu-held-qualification-09';(old/'logs').mkdir(parents=True)
    (old/'logs/stdout.log').write_bytes(b'');(old/'logs/stderr.log').write_bytes(b'AUTHORED consumed09\n')
    previous={p:p.read_bytes() for p in old.rglob('*') if p.is_file()}
    result=m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['stdout']['path']=='runs/puck-cpu-held-qualification-10-external-cli.stdout'
    assert (tmp_path/result['stdout']['path']).read_bytes()==b'AUTHORED10 transport\n'
    assert all(p.read_bytes()==data for p,data in previous.items())
    assert not (old/'result.json').exists() and not (old/'baseline-after.json').exists()
    with pytest.raises(FileExistsError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert all(p.read_bytes()==data for p,data in previous.items())


@pytest.mark.parametrize('field,value',[('phase','prepare'),('version',9),('version',True),('allocation_id',9),('allocation_id',True)])
def test10_observer_rejects_mixed_identity_before_launch(tmp_path,monkeypatch,field,value):
    m,path,_=observer_setup(tmp_path,monkeypatch,'raise AssertionError("must not launch")\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v10',version=10,allocation_id=10,phase='qualify')
    config[field]=value;raw=m.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]


@pytest.mark.parametrize('selected',[True,3.0,5,None,'4'])
def test10_refuses_unsupported_helper_qualification_versions(selected):
    m,deps,result=result_case()
    files=[dict(path=p,size_bytes=(m.ROOT/p).stat().st_size,sha256=m.digest((m.ROOT/p).read_bytes())) for p in m.WORKER_SOURCES]
    with pytest.raises(ValueError):
        m.worker_registration(files,b'{}',negative_imports=['org'],qualification_version=selected)
    with pytest.raises(ValueError):
        m.validate_worker_result(result,registration_sha256='a'*64,dependency_sha256='b'*64,
            dependencies=deps,negative_imports=['org'],qualification_version=selected)
