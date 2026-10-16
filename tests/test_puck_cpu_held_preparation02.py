"""Fresh CPU preparation epoch 02 identity; authored metadata only, no allocation runs.

Preparation01's tmpfs forest is gone, so recreating its identities would forge
custody. Preparation02 is a separately named allocation with its own output,
stage parent, kind, version and allocation id; its behavior is otherwise 01's.
"""
import copy
import json

import pytest

from test_puck_cpu_held_amendment import acceptance_case
from test_puck_cpu_held_observer import setup as observer_setup
from test_puck_cpu_held_runtime_audit import api as auditor_api


# Independently authored identity; do not derive from producer constants.
KIND02='puck-cpu-held-runtime-allocation-v12'
OUTPUT02='runs/puck-cpu-held-preparation-02'
STAGE02='/tmp/palimpsest-puck-cpu-held-02'
FLOORS=dict(min_available_ram_bytes=4096*1024**2,min_free_bytes=4096*1024**2,
            min_tmpfs_free_bytes=2048*1024**2,file_bytes=1024*1024**2,normal_seconds=180)


def preparation02_config(stage=STAGE02):
    m,current,blobs=acceptance_case()
    prior=json.loads(blobs['configuration'])
    config=m.configuration_template(phase='prepare',root=prior['root'],stage_parent=stage,
        sources=copy.deepcopy(current['sources']),inputs=copy.deepcopy(prior['inputs']),
        negative_imports=list(m.PREPARATION_NEGATIVE_IMPORTS))
    config.update(kind=KIND02,version=12,allocation_id=12)
    return m,config,prior


def test_preparation02_has_a_distinct_identity_output_and_stage():
    m,config,prior=preparation02_config()
    m.validate_configuration(config);auditor_api().configuration(config,False)
    assert m.allocation_output(config)==auditor_api().allocation_output(config)==OUTPUT02
    assert OUTPUT02!=m.OUTPUTS['prepare']=='runs/puck-cpu-held-preparation-01'
    assert m.PREPARATION02==OUTPUT02 and auditor_api().PREPARATION02==OUTPUT02
    assert (config['kind'],config['version'],config['allocation_id'],config['phase'])==(KIND02,12,12,'prepare')
    assert (prior['kind'],prior['version'],prior['allocation_id'])==('puck-cpu-held-runtime-allocation-v1',1,1)
    assert config['stage_parent']!='/tmp/palimpsest-puck-cpu-held-01'
    assert 'preparation' not in config and 'preparation_acceptance' not in config


def test_preparation02_keeps_preparation01_behavior_limits_and_roster():
    m,config,prior=preparation02_config()
    m.validate_configuration(config);auditor_api().configuration(config,False)
    assert config['limits']==m.LIMITS['prepare']==prior['limits']
    assert {k:config['limits'][k] for k in FLOORS}==FLOORS
    assert config['negative_imports']==m.PREPARATION_NEGATIVE_IMPORTS==['numpy._distributor_init_local','org']
    for key in ('root','inputs','interpreter','environment','expected_versions','claims','phase'):
        assert config[key]==prior[key]


@pytest.mark.parametrize('stage',['/tmp/palimpsest-puck-cpu-held-02','/tmp/palimpsest-puck-cpu-held-02-authored-0a1b'])
def test_preparation02_accepts_only_its_own_stage_family(stage):
    m,config,_=preparation02_config(stage)
    m.validate_configuration(config);auditor_api().configuration(config,False)


@pytest.mark.parametrize('defect',['stage01','stage-other','stage-prefix','qualify','v1-version','v1-id','bool-version',
    'bool-id','old-kind','preparation-key','acceptance-key','limits-ram','limits-tmpfs','roster','roster-q11','extra'])
def test_preparation02_refuses_aliases_reuse_and_policy_changes(defect):
    m,config,_=preparation02_config()
    if defect=='stage01':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-01'
    elif defect=='stage-other':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-authored'
    elif defect=='stage-prefix':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-020'
    elif defect=='qualify':config.update(phase='qualify',limits=copy.deepcopy(m.LIMITS['qualify']))
    elif defect=='v1-version':config['version']=1
    elif defect=='v1-id':config['allocation_id']=1
    elif defect=='bool-version':config['version']=True
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='old-kind':config['kind']='puck-cpu-held-runtime-allocation-v1'
    elif defect=='preparation-key':config['preparation']=dict(path=m.OUTPUTS['prepare']+'/result.json',size_bytes=1,sha256='a'*64)
    elif defect=='acceptance-key':config['preparation_acceptance']={}
    elif defect=='limits-ram':config['limits']['min_available_ram_bytes']//=2
    elif defect=='limits-tmpfs':config['limits']['min_tmpfs_free_bytes']//=2
    elif defect=='roster':config['negative_imports']=['org']
    elif defect=='roster-q11':config['negative_imports']=list(m.QUALIFY11_NEGATIVE_IMPORTS)
    else:config['output']=m.OUTPUTS['prepare']
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


def test_preparation01_identity_and_output_are_unchanged():
    m,_,prior=preparation02_config()
    m.validate_configuration(prior)
    assert m.allocation_output(prior)==auditor_api().allocation_output(prior)=='runs/puck-cpu-held-preparation-01'


@pytest.mark.parametrize('code',[0,7])
def test_observer_reserves_preparation02_once_without_touching_preparation01(tmp_path,monkeypatch,code):
    m,path,_=observer_setup(tmp_path,monkeypatch,'import sys\nprint("AUTHORED prepare02 transport")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes());config.update(kind=KIND02,version=12,allocation_id=12,phase='prepare')
    raw=m.canonical(config);path.write_bytes(raw)
    old=tmp_path/'runs/puck-cpu-held-preparation-01';(old/'payload').mkdir(parents=True)
    (old/'result.json').write_bytes(b'AUTHORED consumed preparation01\n')
    previous={p:p.read_bytes() for p in old.rglob('*') if p.is_file()}
    result=m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert result['observed_returncode']==code and result['timed_out'] is False and result['phase']=='prepare'
    assert result['stdout']['path']==OUTPUT02+'-external-cli.stdout'
    assert (tmp_path/result['stdout']['path']).read_bytes()==b'AUTHORED prepare02 transport\n'
    assert (tmp_path/(OUTPUT02+'-external-cli-transport.json')).is_file()
    assert all(p.read_bytes()==data for p,data in previous.items())
    assert not (tmp_path/'runs/puck-cpu-held-preparation-01-external-cli-transport.json').exists()
    with pytest.raises(FileExistsError):m.observe(path,m.hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize('field,value',[('phase','qualify'),('version',1),('version',True),('allocation_id',1),
    ('allocation_id',True)])
def test_observer_rejects_mixed_preparation02_identity_before_launch(tmp_path,monkeypatch,field,value):
    m,path,_=observer_setup(tmp_path,monkeypatch,'raise AssertionError("must not launch")\n')
    config=json.loads(path.read_bytes());config.update(kind=KIND02,version=12,allocation_id=12,phase='prepare')
    config[field]=value;raw=m.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]
