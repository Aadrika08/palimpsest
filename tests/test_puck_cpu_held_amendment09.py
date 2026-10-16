"""Fixed accounting epoch09; authored metadata/transport only, no vendors."""
import copy
import json

import pytest

from test_puck_cpu_held_amendment05 import validate_both
from test_puck_cpu_held_amendment06 import OTHER_INPUTS, ROSTER06
from test_puck_cpu_held_amendment08 import DIAGNOSTIC_SOURCES, acceptance08_case
from test_puck_cpu_held_observer import setup as observer_setup
from test_puck_cpu_held_runtime_audit import api as auditor_api


def acceptance09_case():
    m,config,blobs,old,candidate_c,candidate_d=acceptance08_case()
    next(row for row in config['sources'] if row['path']=='scripts/puck_worker_bootstrap.py')['sha256']='9'*64
    config.update(kind='puck-cpu-held-runtime-allocation-v9',version=9,allocation_id=9)
    return m,config,blobs,old,candidate_c,candidate_d


@pytest.mark.parametrize('provider',['parent','independent'])
def test09_accepts_only_fixed_identity_and_five_source_projection(provider):
    m,config,blobs,old,_,candidate_d=acceptance09_case()
    if provider=='parent':
        m.validate_configuration(config)
        prior,prepared=m.validate_preparation_acceptance(config,blobs)
        output=m.allocation_output(config)
        m.validate_publication_candidate(old,candidate_d,pillow_origins=True)
    else:
        audit=auditor_api();audit.configuration(config,False)
        prior=json.loads(blobs['configuration']);prepared=json.loads(blobs['result'])
        audit.preparation_epoch(config,prior,prepared)
        output=audit.allocation_output(config)
        audit.publication_candidate(old,candidate_d,pillow_origins=True)
    assert output=='runs/puck-cpu-held-qualification-09'
    assert {r['path'] for r in config['sources'] if r!=next(p for p in prior['sources'] if p['path']==r['path'])}==set(DIAGNOSTIC_SOURCES)
    assert prepared['sources']==prior['sources'] and prepared['inputs']==prior['inputs']
    assert len(config['sources'])==24 and len(config['inputs'])==16
    assert config['negative_imports']==ROSTER06 and len(ROSTER06)==19
    assert all(config['inputs'][role]==prior['inputs'][role] for role in OTHER_INPUTS)


@pytest.mark.parametrize('path',DIAGNOSTIC_SOURCES)
def test09_requires_each_of_five_preparation_relative_source_changes(path):
    m,config,blobs,*_=acceptance09_case();prior,_=validate_both(m,config,blobs)
    old=next(row for row in prior['sources'] if row['path']==path)
    config['sources']=[copy.deepcopy(old) if row['path']==path else row for row in config['sources']]
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


def test09_rejects_sixth_preparation_relative_source_change():
    m,config,blobs,*_=acceptance09_case();prior,_=validate_both(m,config,blobs)
    next(row for row in config['sources'] if row['path']=='src/palimpsest/puck_native_origins.py')['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('defect',[
    'kind08','kind10','version08','bool-version','id08','bool-id','prepare',
    'output08','source-policy','roster','environment','limits',
])
def test09_rejects_identity_aliases_and_policy_expansion(defect):
    m,config,blobs,*_=acceptance09_case();validate_both(m,config,blobs)
    if defect=='kind08':config['kind']='puck-cpu-held-runtime-allocation-v8'
    elif defect=='kind10':config['kind']='puck-cpu-held-runtime-allocation-v10'
    elif defect=='version08':config['version']=8
    elif defect=='bool-version':config['version']=True
    elif defect=='id08':config['allocation_id']=8
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='prepare':config.update(phase='prepare',limits=copy.deepcopy(m.LIMITS['prepare']))
    elif defect=='output08':config['output']='runs/puck-cpu-held-qualification-08'
    elif defect=='source-policy':config['changed_source_paths']=list(DIAGNOSTIC_SOURCES)
    elif defect=='roster':config['negative_imports']=ROSTER06+['caller_selected']
    elif defect=='environment':config['environment']['DIAGNOSTICS']='1'
    else:config['limits']['normal_seconds']+=1
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('role',OTHER_INPUTS)
def test09_preserves_every_noncandidate_preparation_input(role):
    m,config,blobs,*_=acceptance09_case();prior,_=validate_both(m,config,blobs)
    config['inputs'][role]['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('code',[0,7])
def test09_observer_preserves_consumed07_08_and_reserves_once(tmp_path,monkeypatch,code):
    m,path,_=observer_setup(tmp_path,monkeypatch,
        'import sys\nprint("AUTHORED09 transport")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes())
    config.update(kind='puck-cpu-held-runtime-allocation-v9',version=9,allocation_id=9,phase='qualify')
    raw=m.canonical(config);path.write_bytes(raw)
    for epoch in ('07','08'):
        old=tmp_path/('runs/puck-cpu-held-qualification-'+epoch);(old/'logs').mkdir(parents=True)
        (old/'logs/stdout.log').write_bytes(b'')
        (old/'logs/stderr.log').write_bytes(b'' if epoch=='07' else b'AUTHORED historical08 diagnostic stream\n')
    prior={p:p.read_bytes() for p in (tmp_path/'runs').rglob('*') if p.is_file()}
    result=m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['stdout']['path']=='runs/puck-cpu-held-qualification-09-external-cli.stdout'
    assert (tmp_path/result['stdout']['path']).read_bytes()==b'AUTHORED09 transport\n'
    for epoch in ('07','08'):
        old=tmp_path/('runs/puck-cpu-held-qualification-'+epoch)
        assert not (old/'result.json').exists() and not (old/'baseline-after.json').exists()
    assert all(p.read_bytes()==before for p,before in prior.items())
    receipt=tmp_path/'runs/puck-cpu-held-qualification-09-external-cli-transport.json';saved=receipt.read_bytes()
    with pytest.raises(FileExistsError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert receipt.read_bytes()==saved and all(p.read_bytes()==before for p,before in prior.items())


@pytest.mark.parametrize('field,value',[
    ('phase','prepare'),('version',8),('version',True),('allocation_id',8),('allocation_id',True),
])
def test09_observer_rejects_alias_before_launch(tmp_path,monkeypatch,field,value):
    m,path,_=observer_setup(tmp_path,monkeypatch,'raise AssertionError("must not launch")\n')
    config=json.loads(path.read_bytes())
    config.update(kind='puck-cpu-held-runtime-allocation-v9',version=9,allocation_id=9,phase='qualify')
    config[field]=value;raw=m.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]
