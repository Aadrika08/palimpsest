"""Epoch14 = epoch11 policy v5 on preparation03 with extended qualification clocks.

Authored metadata/transport only. Runtime11 failed only on the 180 s clock after
policy v5 imported Torchvision; epoch14 changes the clocks and nothing else.
"""
import copy
import json

import pytest

from test_puck_cpu_held_amendment import rebind
from test_puck_cpu_held_amendment05 import validate_both
from test_puck_cpu_held_amendment06 import OTHER_INPUTS
from test_puck_cpu_held_amendment10 import acceptance10_case
from test_puck_cpu_held_amendment11 import (
    HIDDEN11, ROSTER11, acceptance11_case, bind_preparation, worker_files,
)
from test_puck_cpu_held_observer import setup as observer_setup
from test_puck_cpu_held_parent import result_case
from test_puck_cpu_held_runtime_audit import api as auditor_api


# Independently authored contract; do not derive these from producer constants.
CLOCKS14=dict(normal_seconds=360,child_hard_seconds=375,hard_seconds=390)
CLOCKS_OLD=dict(normal_seconds=180,child_hard_seconds=190,hard_seconds=200)
PREPARATION03='runs/puck-cpu-held-preparation-03'
STAGE03='/tmp/palimpsest-puck-cpu-held-03-authored'


def acceptance14_case():
    m,config,blobs,old,candidate_c,candidate_d=acceptance10_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v14',version=14,allocation_id=14,
                  negative_imports=list(ROSTER11),limits=dict(copy.deepcopy(m.LIMITS['qualify']),**CLOCKS14))
    bind_preparation(m,config,blobs,allocation=13)
    return m,config,blobs,old,candidate_c,candidate_d


def test14_is_epoch11_with_extended_clocks_on_preparation03():
    m,config,blobs,old,_,candidate_d=acceptance14_case()
    prior,prepared=validate_both(m,config,blobs)
    assert m.allocation_output(config)==auditor_api().allocation_output(config)=='runs/puck-cpu-held-qualification-14'
    assert (prior['kind'],prior['version'],prior['allocation_id'],prior['phase'])==(
        'puck-cpu-held-runtime-allocation-v13',13,13,'prepare')
    assert config['preparation_acceptance']['result']['path']==PREPARATION03+'/result.json'
    assert config['stage_parent']==prior['stage_parent']==prepared['stage_parent']==STAGE03
    assert prior['sources']==config['sources']==prepared['sources']
    assert config['negative_imports']==m.QUALIFY11_NEGATIVE_IMPORTS==ROSTER11
    assert m.QUALIFY11_HIDDEN_IMPORTS==HIDDEN11
    assert config['limits']==m.QUALIFY14_LIMITS=={**m.LIMITS['qualify'],**CLOCKS14}
    assert {k:m.LIMITS['qualify'][k] for k in CLOCKS_OLD}==CLOCKS_OLD
    assert {k:v for k,v in config['limits'].items() if k not in CLOCKS14}=={
        k:v for k,v in m.LIMITS['qualify'].items() if k not in CLOCKS14}
    assert config['limits']['rss_bytes']==2048*1024**2 and config['limits']['min_available_ram_bytes']==2048*1024**2
    assert all(config['inputs'][key]==prior['inputs'][key] for key in OTHER_INPUTS)
    assert prior['inputs']['candidate']!=config['inputs']['candidate']
    m.validate_publication_candidate(old,candidate_d,pillow_origins=True)


def test14_mirrors_epoch11_except_identity_preparation_and_clocks():
    m,c11,*_=acceptance11_case();_,c14,*_=acceptance14_case()
    differing={k for k in c11 if c11[k]!=c14[k]}
    assert differing=={'kind','version','allocation_id','limits','stage_parent','preparation_acceptance'}
    assert {k for k in c11['limits'] if c11['limits'][k]!=c14['limits'][k]}==set(CLOCKS14)


@pytest.mark.parametrize('epoch',[11,14])
def test_extended_clocks_belong_only_to_epoch14(epoch):
    m,config,blobs,*_=acceptance11_case() if epoch==11 else acceptance14_case()
    config['limits']=dict(config['limits'],**(CLOCKS_OLD if epoch==14 else CLOCKS14))
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('defect',['old-kind','old-version','old-id','bool-version','bool-id','prepare','normal','child',
    'hard','rss','ram','roster06','roster-hidden','hidden-field','policy-field','deadline-field'])
def test14_refuses_identity_aliases_and_policy_expansion(defect):
    m,config,blobs,*_=acceptance14_case();validate_both(m,config,blobs)
    if defect=='old-kind':config['kind']='puck-cpu-held-runtime-allocation-v11'
    elif defect=='old-version':config['version']=11
    elif defect=='old-id':config['allocation_id']=11
    elif defect=='bool-version':config['version']=True
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='prepare':config.update(phase='prepare',limits=copy.deepcopy(m.LIMITS['prepare']))
    elif defect=='normal':config['limits']['normal_seconds']+=1
    elif defect=='child':config['limits']['child_hard_seconds']+=1
    elif defect=='hard':config['limits']['hard_seconds']+=1
    elif defect=='rss':config['limits']['rss_bytes']*=2
    elif defect=='ram':config['limits']['min_available_ram_bytes']//=2
    elif defect=='roster06':config['negative_imports']=list(m.QUALIFY06_NEGATIVE_IMPORTS)
    elif defect=='roster-hidden':config['negative_imports']=sorted(ROSTER11+['networkx'])
    elif defect=='hidden-field':config['hidden_imports']=list(HIDDEN11)
    elif defect=='policy-field':config['qualification_version']=5
    else:config['deadline_seconds']=360
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('path',['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py',
    'src/palimpsest/puck_dependency_files.py','src/palimpsest/puck_native_origins.py'])
def test14_refuses_any_source_change_after_preparation03(path):
    m,config,blobs,*_=acceptance14_case();prior,_=validate_both(m,config,blobs)
    next(row for row in config['sources'] if row['path']==path)['sha256']='0'*64
    with pytest.raises(ValueError,match='preparation03'):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError,match='preparation03'):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('role',OTHER_INPUTS)
def test14_preserves_every_noncandidate_input(role):
    m,config,blobs,*_=acceptance14_case();prior,_=validate_both(m,config,blobs)
    config['inputs'][role]['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


def test14_refuses_preparation01_acceptance():
    m,config,blobs,*_=acceptance10_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v14',version=14,allocation_id=14,
                  negative_imports=list(ROSTER11),limits=dict(copy.deepcopy(m.LIMITS['qualify']),**CLOCKS14))
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError,match='preparation03'):
        auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))
    bind_preparation(m,config,blobs,allocation=13,version=1);m.validate_configuration(config)
    with pytest.raises(ValueError,match='^Accepted CPU preparation03 required$'):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError,match='^Accepted preparation03 configuration required$'):
        auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))


def test14_refuses_preparation02_acceptance():
    m,config,blobs,*_=acceptance14_case()
    bind_preparation(m,config,blobs,allocation=12)
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)
    # A preparation02 identity at preparation03's paths is still refused.
    m,config,blobs,*_=acceptance14_case()
    prior=json.loads(blobs['configuration']);prior.update(kind='puck-cpu-held-runtime-allocation-v12',version=12,allocation_id=12)
    with pytest.raises(ValueError,match='^Accepted preparation03 configuration required$'):
        auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))
    bind_preparation(m,config,blobs,allocation=13,version=12,stage='/tmp/palimpsest-puck-cpu-held-03-authored')
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)


@pytest.mark.parametrize('epoch',[10,11])
def test_older_epochs_refuse_preparation03_acceptance(epoch):
    m,config,blobs,*_=acceptance10_case() if epoch==10 else acceptance11_case()
    bind_preparation(m,config,blobs,allocation=13)
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)
    with pytest.raises(ValueError,match='preparation0'+('1' if epoch==10 else '2')):
        auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))


@pytest.mark.parametrize('defect',['outcome-kind','outcome-id','audit-kind','audit-id','audit-prep02-auditor',
    'audit-legacy-auditor','audit-foreign-auditor','cli-prep02-transport','prior-stage02'])
def test14_preparation03_acceptance_identity_is_exact(defect):
    m,config,blobs,*_=acceptance14_case();validate_both(m,config,blobs)
    prepared=json.loads(blobs['result']);audit=json.loads(blobs['independent_audit'])
    cli=json.loads(blobs['externally_observed_auditor_cli'])
    if defect=='outcome-kind':prepared['kind']='puck-cpu-held-runtime-outcome-v12';rebind(m,config,blobs,'result',prepared)
    elif defect=='outcome-id':prepared['allocation_id']=12;rebind(m,config,blobs,'result',prepared)
    elif defect=='audit-kind':audit['kind']='puck-cpu-held-runtime-independent-audit-v12';rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='audit-id':audit['allocation_id']=12;rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='audit-prep02-auditor':
        audit['auditor_source_sha256']=m.PREPARATION02_AUDITOR_SHA256;rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='audit-legacy-auditor':
        audit['auditor_source_sha256']=m.LEGACY_AUDITOR_SHA256;rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='audit-foreign-auditor':
        audit['auditor_source_sha256']='0'*64;rebind(m,config,blobs,'independent_audit',audit)
    elif defect=='cli-prep02-transport':
        cli['command'][10]=str(m.ROOT/'authored-prepare02-transport.json')
        rebind(m,config,blobs,'externally_observed_auditor_cli',cli)
    else:bind_preparation(m,config,blobs,allocation=13,stage='/tmp/palimpsest-puck-cpu-held-02-authored')
    with pytest.raises(ValueError):
        m.validate_configuration(config);m.validate_preparation_acceptance(config,blobs)


def test14_worker_registration_adds_only_the_extended_worker_clock():
    m,_,_=result_case();files=worker_files(m)
    q11,_=m.worker_registration(files,b'{}',negative_imports=['org'],qualification_version=5,hidden_imports=list(HIDDEN11))
    q14,_=m.worker_registration(files,b'{}',negative_imports=['org'],qualification_version=5,hidden_imports=list(HIDDEN11),
                                deadline_seconds=360)
    assert 'deadline_seconds' not in q11 and q14['deadline_seconds']==360==m.QUALIFY14_WORKER_SECONDS
    assert {k:v for k,v in q14.items() if k!='deadline_seconds'}==q11


@pytest.mark.parametrize('version,seconds',[(5,180),(5,361),(5,True),(5,'360'),(5,360.0),(4,360),(3,360)])
def test14_worker_registration_refuses_other_worker_clocks(version,seconds):
    m,_,_=result_case();files=worker_files(m)
    with pytest.raises(ValueError):
        m.worker_registration(files,b'{}',negative_imports=['org'],qualification_version=version,
            hidden_imports=list(HIDDEN11) if version==5 else None,deadline_seconds=seconds)


@pytest.mark.parametrize('code',[0,7])
def test14_observer_reserves_once_with_clocks_beyond_the_parent_hard_clock(tmp_path,monkeypatch,code):
    m,path,_=observer_setup(tmp_path,monkeypatch,'import sys\nprint("AUTHORED14 transport")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v14',version=14,allocation_id=14,phase='qualify')
    raw=m.canonical(config);path.write_bytes(raw)
    waits=[];popen=m.subprocess.Popen
    class Recording(popen):
        def wait(self,timeout=None):
            waits.append(timeout);return super().wait(timeout=timeout)
    monkeypatch.setattr(m.subprocess,'Popen',Recording)
    result=m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['stdout']['path']=='runs/puck-cpu-held-qualification-14-external-cli.stdout'
    assert 390<waits[0]<=400 and m.EXTENDED_SECONDS=={14:(400,415)}
    assert m.signal.getitimer(m.signal.ITIMER_REAL)[0]==0
    with pytest.raises(FileExistsError):m.observe(path,m.hashlib.sha256(raw).hexdigest())


def test11_observer_keeps_its_original_clock(tmp_path,monkeypatch):
    m,path,_=observer_setup(tmp_path,monkeypatch,'print("AUTHORED11 transport")\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,phase='qualify')
    raw=m.canonical(config);path.write_bytes(raw)
    waits=[];popen=m.subprocess.Popen
    class Recording(popen):
        def wait(self,timeout=None):
            waits.append(timeout);return super().wait(timeout=timeout)
    monkeypatch.setattr(m.subprocess,'Popen',Recording)
    m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert 200<waits[0]<=210 and (m.NORMAL_SECONDS,m.HARD_SECONDS)==(210,225)


@pytest.mark.parametrize('field,value',[('phase','prepare'),('version',11),('version',True),('allocation_id',11),('allocation_id',True)])
def test14_observer_rejects_mixed_identity_before_launch(tmp_path,monkeypatch,field,value):
    m,path,_=observer_setup(tmp_path,monkeypatch,'raise AssertionError("must not launch")\n')
    config=json.loads(path.read_bytes());config.update(kind='puck-cpu-held-runtime-allocation-v14',version=14,allocation_id=14,phase='qualify')
    config[field]=value;raw=m.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]


@pytest.mark.parametrize('epoch,normal',[(11,180),(14,360),(1,180),(12,180),(13,180)])
def test_auditor_limits_mirror_the_parent_clock_per_allocation(epoch,normal):
    a=auditor_api();phase='prepare' if epoch in (1,12,13) else 'qualify'
    value=a.limits(phase,False,epoch)
    assert value['normal_seconds']==normal
    assert (value['child_hard_seconds'],value['hard_seconds'])==((375,390) if epoch==14 else (190,200))
