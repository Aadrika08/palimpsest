"""Prospective06 metadata admission; authored inputs, no installed vendors.

This file specifies a source-only epoch. It does not allocate actual06 or
grant authority to run it. Root captures RED/GREEN separately.
"""
import copy
import json

import pytest

from test_puck_cpu_held_amendment import acceptance_case, rebind
from test_puck_cpu_held_amendment03 import (
    BASE_ROSTER, ROSTER03, acceptance03_case, rebind_historical_configuration,
)
from test_puck_cpu_held_amendment04 import BINDINGS, PARENT, acceptance04_case
from test_puck_cpu_held_amendment05 import (
    IMPORTS, PUBLICATION_EXPORTS, acceptance05_case, validate_both,
)
from test_puck_cpu_held_observer import setup as observer_setup
from test_puck_cpu_held_runtime_audit import api as auditor_api


# Independently authored contract; do not derive this from a producer constant.
ROSTER06=[
    'OpenGL_accelerate','accimage','av','colorama','defusedxml','dill','flint',
    'gmpy','gmpy2','monkeytype','numpy._distributor_init_local','opt_einsum',
    'org','pydot','pynvml','torch._rocm_init','torchdistx','tqdm','triton',
]
OTHER_INPUTS=[
    'inventory','layout','native','baseline','generated','accepted_result',
    'accepted_snapshot','accepted_audit','accepted_configuration','accepted_index',
    'observation_configuration','observation_report','observation_result',
    'observation_audit','observation_index',
]
CHANGED_SOURCES=[PARENT,'scripts/puck_worker_bootstrap.py',BINDINGS,IMPORTS]


def acceptance06_case():
    m,config,blobs,old,new=acceptance05_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v6',version=6,
                  allocation_id=6,negative_imports=list(ROSTER06))
    return m,config,blobs,old,new


def test06_is_a_closed_roster_epoch_over_the_same_reviewed_publication_candidate():
    m,config,blobs,old,new=acceptance06_case()
    prior,prepared=validate_both(m,config,blobs)
    assert len(ROSTER06)==19 and ROSTER06==sorted(set(ROSTER06))
    assert prior['negative_imports']==BASE_ROSTER
    assert config['negative_imports']==ROSTER06
    assert {row['path'] for row in config['sources']
            if row!=next(p for p in prior['sources'] if p['path']==row['path'])}==set(CHANGED_SOURCES)
    assert prepared['sources']==prior['sources']
    assert prepared['inputs']==prior['inputs']
    assert {role for role in config['inputs']
            if config['inputs'][role]!=prior['inputs'][role]}=={'candidate'}
    _,five,_,_,_=acceptance05_case()
    assert config['sources']==five['sources'] and config['inputs']==five['inputs']
    assert m.allocation_output(config)==auditor_api().allocation_output(config)=='runs/puck-cpu-held-qualification-06'
    m.validate_publication_candidate(old,new)
    auditor_api().publication_candidate(old,new)
    assert len(PUBLICATION_EXPORTS)==4


@pytest.mark.parametrize('missing',ROSTER06)
def test06_requires_every_exact_optional_absence_name(missing):
    m,config,blobs,_,_=acceptance06_case();validate_both(m,config,blobs)
    config['negative_imports'].remove(missing)
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('names',[
    BASE_ROSTER,ROSTER03,ROSTER06+['guessed_optional'],list(reversed(ROSTER06)),
    sorted(ROSTER06+['pynvml']),
    sorted(['torch.cuda.memory' if n=='pynvml' else n for n in ROSTER06]),
    sorted(['torch._C._autograd' if n=='pynvml' else n for n in ROSTER06]),
    sorted(['OpenGL_accelerate.child' if n=='OpenGL_accelerate' else n for n in ROSTER06]),
    tuple(ROSTER06),None,
])
def test06_refuses_roster_broadening_prefixes_reordering_and_legacy_rosters(names):
    m,config,blobs,_,_=acceptance06_case();validate_both(m,config,blobs)
    config['negative_imports']=names
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('defect',[
    'kind','version','bool-version','id','bool-id','phase','output','source-allowlist',
    'optional-allowlist','legacy-preparation',
])
def test06_has_no_caller_selected_epoch_or_policy(defect):
    m,config,blobs,_,_=acceptance06_case();validate_both(m,config,blobs)
    if defect=='kind':config['kind']='puck-cpu-held-runtime-allocation-v5'
    elif defect=='version':config['version']=5
    elif defect=='bool-version':config['version']=True
    elif defect=='id':config['allocation_id']=5
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='phase':config['phase']='prepare';config['limits']=copy.deepcopy(m.LIMITS['prepare'])
    elif defect=='output':config['output']='runs/puck-cpu-held-qualification-05'
    elif defect=='source-allowlist':config['changed_source_paths']=list(CHANGED_SOURCES)
    elif defect=='optional-allowlist':config['optional_import_prefixes']=list(ROSTER06)
    else:config['preparation']=config['preparation_acceptance']['result']
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('role',[
    'configuration','result','independent_audit','externally_observed_auditor_cli',
])
def test06_requires_all_existing_preparation01_acceptance_anchors(role):
    m,config,blobs,_,_=acceptance06_case();validate_both(m,config,blobs)
    config['preparation_acceptance'].pop(role)
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('limit',['normal_seconds','rss_bytes','file_bytes','max_fds'])
def test06_keeps_the_existing_qualification_limits(limit):
    m,config,blobs,_,_=acceptance06_case();validate_both(m,config,blobs)
    config['limits'][limit]+=1
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('path',CHANGED_SOURCES)
def test06_keeps_exactly_the_existing_four_changed_source_paths(path):
    m,config,blobs,_,_=acceptance06_case();prior,_=validate_both(m,config,blobs)
    old=next(row for row in prior['sources'] if row['path']==path)
    config['sources']=[copy.deepcopy(old) if row['path']==path else row for row in config['sources']]
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('role',OTHER_INPUTS)
def test06_preserves_every_noncandidate_input_pin(role):
    m,config,blobs,_,_=acceptance06_case();prior,_=validate_both(m,config,blobs)
    config['inputs'][role]['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('defect',[
    'foreign-source','historical-source','historical-input','historical-roster','stage',
])
def test06_cannot_rewrite_accepted_preparation_or_change_other_sources(defect):
    m,config,blobs,_,_=acceptance06_case();prior,_=validate_both(m,config,blobs)
    if defect=='foreign-source':
        next(row for row in config['sources'] if row['path']=='src/palimpsest/puck_cpu_registration.py')['sha256']='0'*64
    elif defect=='historical-source':
        prepared=json.loads(blobs['result']);prepared['sources'][0]['sha256']='0'*64
        rebind(m,config,blobs,'result',prepared)
    elif defect=='historical-input':
        prepared=json.loads(blobs['result']);prepared['inputs']['candidate']['sha256']='0'*64
        rebind(m,config,blobs,'result',prepared)
    elif defect=='historical-roster':
        prior['negative_imports']=list(ROSTER06)
        rebind_historical_configuration(m,config,blobs,prior)
    else:config['stage_parent']='/tmp/palimpsest-puck-cpu-held-other'
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))


@pytest.mark.parametrize('version',[1,2,3,4,5])
def test06_does_not_change_any_legacy_roster_or_output(version):
    if version==1:
        m,_,blobs,_,_=acceptance05_case();config=json.loads(blobs['configuration'])
    else:
        case={2:acceptance_case,3:acceptance03_case,4:acceptance04_case,5:acceptance05_case}[version]()
        m,config,blobs=case[:3]
        if version==2:config['negative_imports']=list(BASE_ROSTER)
    independent=auditor_api()
    m.validate_configuration(config);independent.configuration(config,False)
    expected=BASE_ROSTER if version<=2 else ROSTER03
    assert config['negative_imports']==expected
    suffix='preparation-01' if version==1 else 'qualification-'+str(version).zfill(2)
    assert m.allocation_output(config)==independent.allocation_output(config)=='runs/puck-cpu-held-'+suffix
    config['negative_imports']=list(ROSTER06)
    if version<=2:
        # Preserve the old parent's generic finite syntax admission. The old
        # independent acceptance contract, and02 preparation binding, are exact.
        m.validate_configuration(config)
        if version==2:
            with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    else:
        with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):independent.configuration(config,False)


@pytest.mark.parametrize('code',[0,7])
def test06_observer_uses_new_exclusive_paths_without_rewriting_prior_allocations(tmp_path,monkeypatch,code):
    m,path,_=observer_setup(tmp_path,monkeypatch,'import sys\nprint("AUTHORED transport only")\nsys.exit('+str(code)+')\n')
    config=json.loads(path.read_bytes())
    config.update(kind='puck-cpu-held-runtime-allocation-v6',version=6,allocation_id=6,phase='qualify')
    raw=m.canonical(config);path.write_bytes(raw)
    old={}
    for number in range(1,6):
        for suffix in ('','-external-cli.stdout','-external-cli.stderr','-external-cli-transport.json'):
            entry=tmp_path/('runs/puck-cpu-held-qualification-'+str(number).zfill(2)+suffix)
            if suffix:entry.write_bytes(b'IMMUTABLE AUTHORED PRIOR\n');old[entry]=entry.read_bytes()
            else:entry.mkdir();(entry/'result.json').write_bytes(b'AUTHORED prior outcome\n');old[entry/'result.json']=(entry/'result.json').read_bytes()
    result=m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert result['observed_returncode']==code and result['timed_out'] is False
    assert result['stdout']['path']=='runs/puck-cpu-held-qualification-06-external-cli.stdout'
    assert all(p.read_bytes()==before for p,before in old.items())
    receipt=tmp_path/'runs/puck-cpu-held-qualification-06-external-cli-transport.json'
    saved=receipt.read_bytes()
    with pytest.raises(FileExistsError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert receipt.read_bytes()==saved and all(p.read_bytes()==before for p,before in old.items())


@pytest.mark.parametrize('field,value',[
    ('phase','prepare'),('version',5),('version',True),('allocation_id',5),('allocation_id',True),
])
def test06_observer_rejects_epoch_alias_before_launch(tmp_path,monkeypatch,field,value):
    m,path,_=observer_setup(tmp_path,monkeypatch,'raise AssertionError("must not launch")\n')
    config=json.loads(path.read_bytes())
    config.update(kind='puck-cpu-held-runtime-allocation-v6',version=6,allocation_id=6,phase='qualify')
    config[field]=value;raw=m.canonical(config);path.write_bytes(raw)
    with pytest.raises(ValueError):m.observe(path,m.hashlib.sha256(raw).hexdigest())
    assert list((tmp_path/'runs').iterdir())==[]
