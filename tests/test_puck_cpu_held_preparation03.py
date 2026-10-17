"""Fresh CPU preparation epoch 03 identity; authored metadata only, no allocation runs.

Preparation03 (allocation 13) is preparation02 with a new output, stage family,
kind, version and allocation id. Its prepare limits, including the 180 s clock
and the 4 GiB RAM floor, are unchanged; only qualification epoch14 extends time.
"""
import copy
import json

import pytest

from test_puck_cpu_held_preparation02 import FLOORS, preparation02_config
from test_puck_cpu_held_observer import setup as observer_setup
from test_puck_cpu_held_runtime_audit import api as auditor_api


# Independently authored identity; do not derive from producer constants.
KIND03='puck-cpu-held-runtime-allocation-v13'
OUTPUT03='runs/puck-cpu-held-preparation-03'
STAGE03='/tmp/palimpsest-puck-cpu-held-03'
CLOCKS=dict(normal_seconds=180,child_hard_seconds=190,hard_seconds=200)


def preparation03_config(stage=STAGE03):
    m,config,prior=preparation02_config(stage)
    config.update(kind=KIND03,version=13,allocation_id=13)
    return m,config,prior


def test_preparation03_has_a_distinct_identity_output_and_stage():
    m,config,prior=preparation03_config()
    m.validate_configuration(config);auditor_api().configuration(config,False)
    assert m.allocation_output(config)==auditor_api().allocation_output(config)==OUTPUT03
    assert m.PREPARATION03==auditor_api().PREPARATION03==OUTPUT03
    assert len({OUTPUT03,m.PREPARATION02,m.OUTPUTS['prepare']})==3
    assert (config['kind'],config['version'],config['allocation_id'],config['phase'])==(KIND03,13,13,'prepare')
    assert config['stage_parent'] not in ('/tmp/palimpsest-puck-cpu-held-01','/tmp/palimpsest-puck-cpu-held-02')
    assert 'preparation' not in config and 'preparation_acceptance' not in config


def test_preparation03_keeps_preparation_limits_clocks_and_roster():
    m,config,prior=preparation03_config()
    m.validate_configuration(config);auditor_api().configuration(config,False)
    assert config['limits']==m.LIMITS['prepare']==prior['limits']
    assert {k:config['limits'][k] for k in FLOORS}==FLOORS
    assert {k:config['limits'][k] for k in CLOCKS}==CLOCKS
    assert config['negative_imports']==m.PREPARATION_NEGATIVE_IMPORTS
    for key in ('root','inputs','interpreter','environment','expected_versions','claims','phase'):
        assert config[key]==prior[key]


@pytest.mark.parametrize('stage',['/tmp/palimpsest-puck-cpu-held-03','/tmp/palimpsest-puck-cpu-held-03-authored-0a1b'])
def test_preparation03_accepts_only_its_own_stage_family(stage):
    m,config,_=preparation03_config(stage)
    m.validate_configuration(config);auditor_api().configuration(config,False)


@pytest.mark.parametrize('defect',['stage01','stage02','stage02-family','stage-prefix','qualify','v12-version','v12-id',
    'v12-kind','bool-version','bool-id','preparation-key','acceptance-key','limits-clock','limits-q14','limits-ram',
    'roster','extra'])
def test_preparation03_refuses_aliases_reuse_and_policy_changes(defect):
    m,config,_=preparation03_config()
    if defect=='stage01':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-01'
    elif defect=='stage02':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-02'
    elif defect=='stage02-family':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-02-authored-0a1b'
    elif defect=='stage-prefix':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-030'
    elif defect=='qualify':config.update(phase='qualify',limits=copy.deepcopy(m.LIMITS['qualify']))
    elif defect=='v12-version':config['version']=12
    elif defect=='v12-id':config['allocation_id']=12
    elif defect=='v12-kind':config['kind']='puck-cpu-held-runtime-allocation-v12'
    elif defect=='bool-version':config['version']=True
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='preparation-key':config['preparation']=dict(path=OUTPUT03+'/result.json',size_bytes=1,sha256='a'*64)
    elif defect=='acceptance-key':config['preparation_acceptance']={}
    elif defect=='limits-clock':config['limits']['normal_seconds']=360
    elif defect=='limits-q14':config['limits']=dict(config['limits'],normal_seconds=360,child_hard_seconds=375,hard_seconds=390)
    elif defect=='limits-ram':config['limits']['min_available_ram_bytes']//=2
    elif defect=='roster':config['negative_imports']=['org']
    else:config['output']=m.PREPARATION02
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


def test_preparation02_cannot_claim_the_preparation03_stage_family():
    m,config,_=preparation02_config('/tmp/palimpsest-puck-cpu-held-03')
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


def test_preparation03_auditor_pin_is_the_current_independent_auditor():
    m,*_=preparation03_config()
    current=m.digest((m.ROOT/'scripts/audit_puck_cpu_held_runtime.py').read_bytes())
    assert m.PREPARATION03_AUDITOR_SHA256==current
    assert len({current,m.PREPARATION02_AUDITOR_SHA256,m.LEGACY_AUDITOR_SHA256})==3


@pytest.mark.parametrize('code',[0,7])
def test_observer_reserves_preparation03_once_with_unchanged_clocks(tmp_path,monkeypatch,code):
    m,path,_=observer_setup(tmp_path,monkeypatch,'import sys\nprint("AUTHORED prepare03 transport")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes());config.update(kind=KIND03,version=13,allocation_id=13,phase='prepare')
    raw=m.canonical(config);path.write_bytes(raw)
    earlier=tmp_path/'runs/puck-cpu-held-preparation-02';(earlier/'payload').mkdir(parents=True)
    (earlier/'result.json').write_bytes(b'AUTHORED consumed preparation02\n')
    previous={p:p.read_bytes() for p in earlier.rglob('*') if p.is_file()}
    waits=[];popen=m.subprocess.Popen
    class Recording(popen):
        def wait(self,timeout=None):
            waits.append(timeout);return super().wait(timeout=timeout)
    monkeypatch.setattr(m.subprocess,'Popen',Recording)
    result=m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert result['observed_returncode']==code and result['timed_out'] is False and result['phase']=='prepare'
    assert result['stdout']['path']==OUTPUT03+'-external-cli.stdout'
    assert 200<waits[0]<=210 and m.signal.getitimer(m.signal.ITIMER_REAL)[0]==0
    assert all(p.read_bytes()==data for p,data in previous.items())
    with pytest.raises(FileExistsError):m.observe(path,m.hashlib.sha256(raw).hexdigest())


@pytest.mark.parametrize('field,value',[('phase','qualify'),('version',12),('version',True),('allocation_id',12),
    ('allocation_id',True)])
def test_observer_rejects_mixed_preparation03_identity_before_launch(tmp_path,monkeypatch,field,value):
    m,path,_=observer_setup(tmp_path,monkeypatch,'raise AssertionError("must not launch")\n')
    config=json.loads(path.read_bytes());config.update(kind=KIND03,version=13,allocation_id=13,phase='prepare')
    config[field]=value;raw=m.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]
