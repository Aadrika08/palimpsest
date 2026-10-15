"""Prospective07 Pillow origin admission, authored metadata only.

No installed Pillow, actual07 controls or runtime allocation is used here.
"""
import copy
import json

import pytest

from test_puck_cpu_held_amendment import acceptance_case, rebind
from test_puck_cpu_held_amendment03 import BASE_ROSTER, ROSTER03, acceptance03_case
from test_puck_cpu_held_amendment04 import acceptance04_case
from test_puck_cpu_held_amendment05 import (
    acceptance05_case, bind_old_candidate, candidate_pin, validate_both,
)
from test_puck_cpu_held_amendment06 import (
    CHANGED_SOURCES, OTHER_INPUTS, ROSTER06, acceptance06_case,
)
from test_puck_cpu_held_runtime_audit import api as auditor_api


# Independently authored exact additions, never derived from production.
PILLOW_ORIGINS=[
    dict(name='PIL._imaging',policy='held-directory-observed-v1'),
    dict(name='PIL._imagingft',policy='held-directory-observed-v1'),
]
RETAINED_ORIGINS=[
    dict(name='authored_native_before',policy='exact-file-fd-v1'),
    dict(name='z_authored_native_after',policy='held-directory-observed-v1'),
]


def acceptance07_case():
    m,config,blobs,old,candidate_c=acceptance06_case()
    old['import_profile']['native_origins']=copy.deepcopy(RETAINED_ORIGINS)
    candidate_c['import_profile']['native_origins']=copy.deepcopy(RETAINED_ORIGINS)
    bind_old_candidate(m,config,blobs,old)
    candidate_d=copy.deepcopy(candidate_c)
    candidate_d['import_profile']['native_origins']=sorted(
        copy.deepcopy(RETAINED_ORIGINS+PILLOW_ORIGINS),key=lambda row:row['name'])
    config['inputs']['candidate']=candidate_pin(m,candidate_d,'docs/authored-candidate-07.json')
    config.update(kind='puck-cpu-held-runtime-allocation-v7',version=7,allocation_id=7)
    return m,config,blobs,old,candidate_c,candidate_d


def validator(m,provider):
    return m.validate_publication_candidate if provider=='parent' else auditor_api().publication_candidate


def test07_accepts_only_exact_origin_delta_with_old_preparation_and_same06_roster():
    m,config,blobs,old,candidate_c,candidate_d=acceptance07_case()
    prior,prepared=validate_both(m,config,blobs)
    assert prior['negative_imports']==BASE_ROSTER and config['negative_imports']==ROSTER06
    assert len(ROSTER06)==19
    assert m.allocation_output(config)==auditor_api().allocation_output(config)=='runs/puck-cpu-held-qualification-07'
    changed={row['path'] for row in config['sources']
        if row!=next(p for p in prior['sources'] if p['path']==row['path'])}
    assert changed==set(CHANGED_SOURCES)
    assert prepared['sources']==prior['sources'] and prepared['inputs']==prior['inputs']
    assert {role for role in config['inputs'] if config['inputs'][role]!=prior['inputs'][role]}=={'candidate'}
    assert all(config['inputs'][role]==prior['inputs'][role] for role in OTHER_INPUTS)
    assert candidate_d['import_profile']['exports']==candidate_c['import_profile']['exports']
    for provider in ('parent','independent'):
        check=validator(m,provider)
        check(old,candidate_c)
        check(old,candidate_d,pillow_origins=True)


@pytest.mark.parametrize('provider',['parent','independent'])
def test07_opt_in_is_keyword_only_and_legacy_default_remains_exactly_four_publications(provider):
    m,_,_,old,candidate_c,candidate_d=acceptance07_case();check=validator(m,provider)
    check(old,candidate_c)
    with pytest.raises(ValueError):check(old,candidate_d)
    with pytest.raises(ValueError):check(old,candidate_c,pillow_origins=True)
    check(old,candidate_d,pillow_origins=True)
    with pytest.raises(TypeError):check(old,candidate_d,True)


@pytest.mark.parametrize('provider',['parent','independent'])
@pytest.mark.parametrize('defect',[
    'missing-imaging','missing-imagingft','duplicate-imaging','duplicate-imagingft',
    'extra-origin','wrong-policy','wrong-name','extra-row-field','unsorted',
    'old-origin-removed','old-origin-policy','other-export','module-map','namespace',
    'helper','provenance','module-change','native-cache','extra-top-field',
])
def test07_rebound_candidate_hash_cannot_conceal_other_semantic_changes(provider,defect):
    m,config,blobs,old,_,candidate_d=acceptance07_case();check=validator(m,provider)
    validate_both(m,config,blobs);check(old,candidate_d,pillow_origins=True)
    origins=candidate_d['import_profile']['native_origins']
    imaging=next(row for row in origins if row['name']=='PIL._imaging')
    if defect.startswith('missing-'):
        name='PIL._imaging' if defect=='missing-imaging' else 'PIL._imagingft'
        origins[:]=[row for row in origins if row['name']!=name]
    elif defect.startswith('duplicate-'):
        name='PIL._imaging' if defect=='duplicate-imaging' else 'PIL._imagingft'
        origins.append(copy.deepcopy(next(row for row in origins if row['name']==name)))
    elif defect=='extra-origin':origins.append(dict(name='PIL._imagingmath',policy='held-directory-observed-v1'))
    elif defect=='wrong-policy':imaging['policy']='exact-file-fd-v1'
    elif defect=='wrong-name':imaging['name']='PIL._other'
    elif defect=='extra-row-field':imaging['allow_unobserved_target']=True
    elif defect=='unsorted':origins.reverse()
    elif defect=='old-origin-removed':origins[:]=[r for r in origins if r['name']!='authored_native_before']
    elif defect=='old-origin-policy':next(r for r in origins if r['name']=='authored_native_before')['policy']='held-directory-observed-v1'
    elif defect=='other-export':candidate_d['import_profile']['exports'][1]['attributes']=['foreign']
    elif defect=='module-map':candidate_d['module_paths'][0]['path']='foreign.py'
    elif defect=='namespace':candidate_d['namespaces'].append(dict(name='foreign',root_index=0,path='foreign'))
    elif defect=='helper':candidate_d['additional_package_inputs'][0]['files'][0]['sha256']='0'*64
    elif defect=='provenance':candidate_d['observation_report_sha256']='0'*64
    elif defect=='module-change':candidate_d['import_profile']['module_changes'].append(dict(name='foreign',kind='replace'))
    elif defect=='native-cache':candidate_d['import_profile']['native_cache'].append(dict(name='foreign'))
    else:candidate_d['caller_selected_policy']=True
    # Rebind the whole candidate pin; metadata authentication alone still passes.
    config['inputs']['candidate']=candidate_pin(m,candidate_d,'docs/authored-candidate-07.json')
    validate_both(m,config,blobs)
    with pytest.raises(ValueError):check(old,candidate_d,pillow_origins=True)


@pytest.mark.parametrize('provider',['parent','independent'])
@pytest.mark.parametrize('name',['PIL._imaging','PIL._imagingft'])
def test07_refuses_historical_candidate_that_already_declares_a_target_origin(provider,name):
    m,_,_,old,_,candidate_d=acceptance07_case();check=validator(m,provider)
    check(old,candidate_d,pillow_origins=True)
    old['import_profile']['native_origins'].append(dict(name=name,policy='exact-file-fd-v1'))
    old['import_profile']['native_origins'].sort(key=lambda row:row['name'])
    with pytest.raises(ValueError):check(old,candidate_d,pillow_origins=True)


@pytest.mark.parametrize('missing',ROSTER06)
def test07_does_not_shrink_the_exact06_missing_import_contract(missing):
    m,config,blobs,_,_,_=acceptance07_case();validate_both(m,config,blobs)
    config['negative_imports'].remove(missing)
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('defect',[
    'kind','version','bool-version','id','bool-id','phase','output',
    'allowlist','new-input-role','extra-missing-import',
])
def test07_has_closed_identity_and_no_caller_supplied_policy(defect):
    m,config,blobs,_,_,_=acceptance07_case();validate_both(m,config,blobs)
    if defect=='kind':config['kind']='puck-cpu-held-runtime-allocation-v6'
    elif defect=='version':config['version']=6
    elif defect=='bool-version':config['version']=True
    elif defect=='id':config['allocation_id']=6
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='phase':config['phase']='prepare';config['limits']=copy.deepcopy(m.LIMITS['prepare'])
    elif defect=='output':config['output']='runs/puck-cpu-held-qualification-06'
    elif defect=='allowlist':config['native_origin_allowlist']=copy.deepcopy(PILLOW_ORIGINS)
    elif defect=='new-input-role':config['inputs']['pillow_proof']=copy.deepcopy(config['inputs']['candidate'])
    else:config['negative_imports']=sorted(ROSTER06+['PIL._optional'])
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('path',CHANGED_SOURCES)
def test07_still_requires_exactly_the_four_existing_source_changes(path):
    m,config,blobs,_,_,_=acceptance07_case();prior,_=validate_both(m,config,blobs)
    old=next(row for row in prior['sources'] if row['path']==path)
    config['sources']=[copy.deepcopy(old) if row['path']==path else row for row in config['sources']]
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('role',OTHER_INPUTS)
def test07_keeps_all15_noncandidate_pins_fixed(role):
    m,config,blobs,_,_,_=acceptance07_case();prior,_=validate_both(m,config,blobs)
    config['inputs'][role]['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('limit',['normal_seconds','rss_bytes','file_bytes','max_fds'])
def test07_does_not_change_resource_limits(limit):
    m,config,blobs,_,_,_=acceptance07_case();validate_both(m,config,blobs)
    config['limits'][limit]+=1
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('defect',['foreign-source','historical-source','historical-input','stage'])
def test07_does_not_amend_other_sources_prepared_bytes_or_stage(defect):
    m,config,blobs,_,_,_=acceptance07_case();validate_both(m,config,blobs)
    if defect=='foreign-source':
        next(r for r in config['sources'] if r['path']=='src/palimpsest/puck_native_origins.py')['sha256']='0'*64
    elif defect in ('historical-source','historical-input'):
        prepared=json.loads(blobs['result'])
        if defect=='historical-source':prepared['sources'][0]['sha256']='0'*64
        else:prepared['inputs']['inventory']['sha256']='0'*64
        rebind(m,config,blobs,'result',prepared)
    else:config['stage_parent']='/tmp/palimpsest-puck-cpu-held-other'
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))


@pytest.mark.parametrize('version',[1,2,3,4,5,6])
def test07_preserves_every_prior_configuration_roster_and_output(version):
    if version==1:
        m,_,blobs,_,_=acceptance05_case();config=json.loads(blobs['configuration'])
    else:
        case={2:acceptance_case,3:acceptance03_case,4:acceptance04_case,
              5:acceptance05_case,6:acceptance06_case}[version]()
        m,config,blobs=case[:3]
        if version==2:config['negative_imports']=list(BASE_ROSTER)
    m.validate_configuration(config);auditor_api().configuration(config,False)
    assert config['negative_imports']==(BASE_ROSTER if version<=2 else ROSTER06 if version==6 else ROSTER03)
    suffix='preparation-01' if version==1 else 'qualification-'+str(version).zfill(2)
    assert m.allocation_output(config)==auditor_api().allocation_output(config)=='runs/puck-cpu-held-'+suffix
