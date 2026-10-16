"""Closed04 diagnostic source transition; all inputs here are authored metadata."""
import copy
import json

import pytest

from test_puck_cpu_held_amendment import rebind
from test_puck_cpu_held_amendment03 import (
    BASE_ROSTER, ROSTER03, acceptance03_case, rebind_historical_configuration,
)


PARENT='scripts/qualify_puck_cpu_held_runtime.py'
BINDINGS='src/palimpsest/puck_dependency_bindings.py'


def acceptance04_case():
    m,config,blobs=acceptance03_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v4',version=4,allocation_id=4)
    next(row for row in config['sources'] if row['path']==BINDINGS)['sha256']='d'*64
    return m,config,blobs


@pytest.mark.parametrize('parent_changed',[False,True])
def test04_accepts_only_mandatory_bootstrap_bindings_and_optional_parent(parent_changed):
    m,config,blobs=acceptance04_case()
    historical=json.loads(blobs['configuration'])
    if not parent_changed:
        old=next(row for row in historical['sources'] if row['path']==PARENT)
        config['sources']=[copy.deepcopy(old) if row['path']==PARENT else row for row in config['sources']]
    m.validate_configuration(config)
    prior,prepared=m.validate_preparation_acceptance(config,blobs)
    assert prior['negative_imports']==BASE_ROSTER
    assert config['negative_imports']==ROSTER03
    assert prepared['sources']==prior['sources']!=config['sources']
    assert m.allocation_output(config)=='runs/puck-cpu-held-qualification-04'


@pytest.mark.parametrize('defect',['kind','version','id','bool-id','phase','output','allowlist','legacy-preparation'])
def test04_identity_and_fields_cannot_alias_other_allocations(defect):
    m,config,_=acceptance04_case()
    if defect=='kind':config['kind']='puck-cpu-held-runtime-allocation-v5'
    elif defect=='version':config['version']=3
    elif defect=='id':config['allocation_id']=3
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='phase':config['phase']='prepare';config['limits']=copy.deepcopy(m.LIMITS['prepare'])
    elif defect=='output':config['output']='runs/puck-cpu-held-qualification-03'
    elif defect=='allowlist':config['changed_source_paths']=[PARENT,m.BOOTSTRAP,BINDINGS]
    else:config['preparation']=config['preparation_acceptance']['result']
    with pytest.raises(ValueError):m.validate_configuration(config)


@pytest.mark.parametrize('role',['configuration','result','independent_audit','externally_observed_auditor_cli'])
def test04_requires_all_four_historical_acceptance_anchors(role):
    m,config,_=acceptance04_case();config['preparation_acceptance'].pop(role)
    with pytest.raises(ValueError):m.validate_configuration(config)


@pytest.mark.parametrize('limit',['normal_seconds','rss_bytes','file_bytes','max_fds'])
def test04_keeps_the_exact_qualification_resource_limits(limit):
    m,config,_=acceptance04_case();config['limits'][limit]+=1
    with pytest.raises(ValueError):m.validate_configuration(config)


@pytest.mark.parametrize('names',[BASE_ROSTER,['org','torch._rocm_init'],ROSTER03+['guess'],
    BASE_ROSTER+['torch._other_init']])
def test04_keeps03_exact_missing_import_roster(names):
    m,config,_=acceptance04_case();config['negative_imports']=names
    with pytest.raises(ValueError):m.validate_configuration(config)


@pytest.mark.parametrize('defect',['no-bindings','no-bootstrap','foreign-source','data','historical-roster','historical-source'])
def test04_diagnostic_epoch_cannot_inherit_other_source_data_or_history(defect):
    m,config,blobs=acceptance04_case()
    prior=json.loads(blobs['configuration'])
    if defect in ('no-bindings','no-bootstrap'):
        name=BINDINGS if defect=='no-bindings' else m.BOOTSTRAP
        old=next(row for row in prior['sources'] if row['path']==name)
        config['sources']=[copy.deepcopy(old) if row['path']==name else row for row in config['sources']]
    elif defect=='foreign-source':
        next(row for row in config['sources'] if row['path']=='src/palimpsest/puck_dependency_imports.py')['sha256']='e'*64
    elif defect=='data':config['inputs']['candidate']['sha256']='0'*64
    elif defect=='historical-roster':
        prior['negative_imports']=list(ROSTER03)
        rebind_historical_configuration(m,config,blobs,prior)
    else:
        prepared=json.loads(blobs['result'])
        next(row for row in prepared['sources'] if row['path']==BINDINGS)['sha256']='e'*64
        rebind(m,config,blobs,'result',prepared)
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)


@pytest.mark.parametrize('version',[2,3])
def test_legacy02_03_still_refuse_a_changed_bindings_support_source(version):
    m,config,blobs=acceptance04_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v'+str(version),version=version,allocation_id=version)
    if version==2:config['negative_imports']=list(BASE_ROSTER)
    m.validate_configuration(config)
    with pytest.raises(ValueError,match='source'):
        m.validate_preparation_acceptance(config,blobs)
