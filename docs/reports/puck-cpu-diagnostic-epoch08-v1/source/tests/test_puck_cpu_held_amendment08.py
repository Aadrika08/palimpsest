"""Closed diagnostic epoch; authored metadata and transport, no installed vendors."""
import copy
import json

import pytest

from test_puck_cpu_held_amendment05 import acceptance05_case, validate_both
from test_puck_cpu_held_amendment06 import CHANGED_SOURCES, OTHER_INPUTS, ROSTER06, acceptance06_case
from test_puck_cpu_held_amendment07 import acceptance07_case
from test_puck_cpu_held_observer import setup as observer_setup
from test_puck_cpu_held_runtime_audit import api as auditor_api


QUALIFIER='src/palimpsest/puck_runtime_qualification.py'
DIAGNOSTIC_SOURCES=CHANGED_SOURCES+[QUALIFIER]


def acceptance08_case():
    m,config,blobs,old,candidate_c,candidate_d=acceptance07_case()
    next(row for row in config['sources'] if row['path']==QUALIFIER)['sha256']='8'*64
    config.update(kind='puck-cpu-held-runtime-allocation-v8',version=8,allocation_id=8)
    return m,config,blobs,old,candidate_c,candidate_d


def test08_accepts_five_source_changes_with_original_preparation_and_candidate_d():
    m,config,blobs,old,_,candidate_d=acceptance08_case()
    prior,prepared=validate_both(m,config,blobs)
    changed={row['path'] for row in config['sources']
             if row!=next(p for p in prior['sources'] if p['path']==row['path'])}
    assert changed==set(DIAGNOSTIC_SOURCES)
    assert prepared['sources']==prior['sources'] and prepared['inputs']==prior['inputs']
    assert config['negative_imports']==ROSTER06 and len(ROSTER06)==19
    assert all(config['inputs'][role]==prior['inputs'][role] for role in OTHER_INPUTS)
    assert m.allocation_output(config)==auditor_api().allocation_output(config)=='runs/puck-cpu-held-qualification-08'
    m.validate_publication_candidate(old,candidate_d,pillow_origins=True)
    auditor_api().publication_candidate(old,candidate_d,pillow_origins=True)


@pytest.mark.parametrize('path',DIAGNOSTIC_SOURCES)
def test08_rejects_each_missing_source_change(path):
    m,config,blobs,_,_,_=acceptance08_case();prior,_=validate_both(m,config,blobs)
    old=next(row for row in prior['sources'] if row['path']==path)
    config['sources']=[copy.deepcopy(old) if row['path']==path else row for row in config['sources']]
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


def test08_rejects_a_sixth_changed_source():
    m,config,blobs,_,_,_=acceptance08_case();prior,_=validate_both(m,config,blobs)
    next(row for row in config['sources'] if row['path']=='src/palimpsest/puck_native_origins.py')['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('factory',[acceptance05_case,acceptance06_case,acceptance07_case])
def test05_06_07_still_reject_the_new_qualifier_source_change(factory):
    m,config,blobs,*_=factory();prior,_=validate_both(m,config,blobs)
    next(row for row in config['sources'] if row['path']==QUALIFIER)['sha256']='8'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('defect',['identity','bool-version','bool-id','prepare','output','source-policy','roster','environment','limits'])
def test08_cannot_select_a_different_identity_or_expand_policy(defect):
    m,config,blobs,_,_,_=acceptance08_case();validate_both(m,config,blobs)
    if defect=='identity':config['allocation_id']=7
    elif defect=='bool-version':config['version']=True
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='prepare':config.update(phase='prepare',limits=copy.deepcopy(m.LIMITS['prepare']))
    elif defect=='output':config['output']='runs/puck-cpu-held-qualification-07'
    elif defect=='source-policy':config['changed_source_paths']=list(DIAGNOSTIC_SOURCES)
    elif defect=='roster':config['negative_imports']=ROSTER06+['caller_selected']
    elif defect=='environment':config['environment']['DIAGNOSTICS']='1'
    else:config['limits']['normal_seconds']+=1
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('role',OTHER_INPUTS)
def test08_preserves_each_noncandidate_input(role):
    m,config,blobs,_,_,_=acceptance08_case();prior,_=validate_both(m,config,blobs)
    config['inputs'][role]['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('code',[0,7])
def test08_observer_preserves_failed07_missing_receipts_and_reserves_once(tmp_path,monkeypatch,code):
    m,path,_=observer_setup(tmp_path,monkeypatch,
        'import sys\nprint("AUTHORED diagnostic transport")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes())
    config.update(kind='puck-cpu-held-runtime-allocation-v8',version=8,allocation_id=8,phase='qualify')
    raw=m.canonical(config);path.write_bytes(raw)
    old=tmp_path/'runs/puck-cpu-held-qualification-07';(old/'logs').mkdir(parents=True)
    for channel in ('stdout','stderr'):(old/('logs/'+channel+'.log')).write_bytes(b'')
    prior={p:p.read_bytes() for p in old.rglob('*') if p.is_file()}
    result=m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['stdout']['path']=='runs/puck-cpu-held-qualification-08-external-cli.stdout'
    assert not (old/'result.json').exists() and not (old/'baseline-after.json').exists()
    assert all(p.read_bytes()==before for p,before in prior.items())
    receipt=tmp_path/'runs/puck-cpu-held-qualification-08-external-cli-transport.json'
    saved=receipt.read_bytes()
    with pytest.raises(FileExistsError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert receipt.read_bytes()==saved and all(p.read_bytes()==before for p,before in prior.items())


@pytest.mark.parametrize('field,value',[('phase','prepare'),('version',7),('version',True),('allocation_id',7),('allocation_id',True)])
def test08_observer_rejects_alias_before_launch(tmp_path,monkeypatch,field,value):
    m,path,_=observer_setup(tmp_path,monkeypatch,'raise AssertionError("must not launch")\n')
    config=json.loads(path.read_bytes())
    config.update(kind='puck-cpu-held-runtime-allocation-v8',version=8,allocation_id=8,phase='qualify')
    config[field]=value;raw=m.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]
