"""Closed05 candidate transition, using authored metadata and no vendor imports."""
import copy
import json

import pytest

from test_puck_cpu_held_amendment import rebind
from test_puck_cpu_held_amendment03 import (
    BASE_ROSTER, ROSTER03, rebind_historical_configuration,
)
from test_puck_cpu_held_amendment04 import BINDINGS, PARENT, acceptance04_case
from test_puck_cpu_held_runtime_audit import api as auditor_api


IMPORTS='src/palimpsest/puck_dependency_imports.py'
TARGET='torch._C._autograd'
DELEGATES=[
    'CreationMeta','DeviceType','ProfilerEvent','SavedTensor','TensorGeometry',
    '_InputMetadata','_KinetoEvent','_ProfilerDisableOptions','_ProfilerResult',
    '_add_metadata_json','_clear_callbacks','_disable_profiler','_disable_profiler_legacy',
    '_enable_profiler','_enable_profiler_legacy','_enable_record_function',
    '_get_creation_meta','_get_current_graph_task_keep_graph','_get_data_attr',
    '_get_sequence_nr','_kineto_step','_pop_saved_tensors_default_hooks',
    '_prepare_profiler','_profiler_enabled','_profiler_type',
    '_push_saved_tensors_default_hooks','_record_function_with_args_enter',
    '_record_function_with_args_exit','_saved_tensors_hooks_disable',
    '_saved_tensors_hooks_enable','_saved_tensors_hooks_get_disabled_error_message',
    '_saved_tensors_hooks_is_enabled','_saved_tensors_hooks_set_tracing',
    '_set_creation_meta','_set_empty_test_observer','_soft_assert_raises',
    '_supported_activities','_toggle_collection_dynamic','_top_saved_tensors_default_hooks',
    '_unsafe_set_version_counter','kineto_available',
]


def candidate_pair():
    old=dict(kind='puck-cpu-observed-import-profile-candidate-v1',version=1,
        observation_report_sha256='1'*64,configuration_sha256='2'*64,
        outcome_audit_sha256='3'*64,retained_inventory_sha256='4'*64,
        expected_versions=dict(numpy='2.2.5',torch='2.9.0+cpu',torchvision='0.24.0+cpu',mujoco='3.3.6'),
        native_phase_qualified=False,held_runtime_qualified=False,native_authorized=False,
        collection_authorized=False,study_authorized=False,executable=False,qualification_claims=[],
        additional_package_inputs=[dict(root='docs/authored-generated',files=[
            dict(path='helper.py',size_bytes=7,sha256='5'*64)])],
        static_source_inputs=[dict(path='torch/autograd/__init__.py',size_bytes=19,sha256='6'*64)],
        module_paths=[dict(name='torch.autograd',root_index=0,path='torch/autograd/__init__.py',kind='python',is_package=True)],
        namespaces=[],import_profile=dict(kind='puck-producer-import-profile-v2',version=2,
            exports=[dict(name=TARGET,producer='torch._C',phase='native_create',
                attributes=['_autograd'],class_binding=None),
                dict(name='torch.authored_other',producer='torch',phase='module_exec',
                    attributes=['authored_other'],class_binding=None)],
            module_changes=[],native_origins=[],native_cache=[]))
    new=copy.deepcopy(old)
    new['import_profile']['exports'][0]=dict(name=TARGET,producer='torch.autograd',
        phase='module_exec_publish',attributes=['torch','_C','_autograd'],
        class_binding=None,delegate_attributes=list(DELEGATES))
    return old,new


def candidate_pin(m,value,path):
    raw=m.canonical(value)
    return dict(path=path,size_bytes=len(raw),sha256=m.digest(raw))


def bind_old_candidate(m,config,blobs,old):
    prior=json.loads(blobs['configuration'])
    prior['inputs']['candidate']=candidate_pin(m,old,'docs/authored-candidate-01.json')
    prepared=json.loads(blobs['result']);prepared['inputs']=copy.deepcopy(prior['inputs'])
    rebind(m,config,blobs,'result',prepared)
    rebind_historical_configuration(m,config,blobs,prior)


def acceptance05_case():
    m,config,blobs=acceptance04_case();old,new=candidate_pair()
    bind_old_candidate(m,config,blobs,old)
    config['inputs']=copy.deepcopy(json.loads(blobs['configuration'])['inputs'])
    config['inputs']['candidate']=candidate_pin(m,new,'docs/authored-candidate-05.json')
    config.update(kind='puck-cpu-held-runtime-allocation-v5',version=5,allocation_id=5)
    next(row for row in config['sources'] if row['path']==IMPORTS)['sha256']='e'*64
    return m,config,blobs,old,new


def validate_both(m,config,blobs):
    m.validate_configuration(config)
    prior,prepared=m.validate_preparation_acceptance(config,blobs)
    independent=auditor_api();independent.configuration(config,False)
    independent.preparation_epoch(config,prior,prepared)
    return prior,prepared


def test05_accepts_only_explicit_source_and_candidate_epochs():
    m,config,blobs,old,new=acceptance05_case()
    prior,prepared=validate_both(m,config,blobs)
    assert prior['negative_imports']==BASE_ROSTER and config['negative_imports']==ROSTER03
    assert prepared['sources']==prior['sources']!=config['sources']
    assert prepared['inputs']==prior['inputs']!=config['inputs']
    assert {p for p in config['inputs'] if config['inputs'][p]!=prior['inputs'][p]}=={'candidate'}
    assert m.allocation_output(config)==auditor_api().allocation_output(config)=='runs/puck-cpu-held-qualification-05'
    assert len(DELEGATES)==41 and DELEGATES==sorted(set(DELEGATES))
    m.validate_publication_candidate(old,new)
    auditor_api().publication_candidate(old,new)


@pytest.mark.parametrize('defect',['kind','version','id','bool-id','phase','output','allowlist','legacy-preparation'])
def test05_has_closed_identity_and_no_caller_supplied_allowlist(defect):
    m,config,_,_,_=acceptance05_case()
    if defect=='kind':config['kind']='puck-cpu-held-runtime-allocation-v6'
    elif defect=='version':config['version']=4
    elif defect=='id':config['allocation_id']=4
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='phase':config['phase']='prepare';config['limits']=copy.deepcopy(m.LIMITS['prepare'])
    elif defect=='output':config['output']='runs/puck-cpu-held-qualification-04'
    elif defect=='allowlist':config['changed_source_paths']=[PARENT,m.BOOTSTRAP,BINDINGS,IMPORTS]
    else:config['preparation']=config['preparation_acceptance']['result']
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('role',['configuration','result','independent_audit','externally_observed_auditor_cli'])
def test05_requires_all_historical_acceptance_anchors(role):
    m,config,_,_,_=acceptance05_case();config['preparation_acceptance'].pop(role)
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('limit',['normal_seconds','rss_bytes','file_bytes','max_fds'])
def test05_keeps_qualification_resource_limits(limit):
    m,config,_,_,_=acceptance05_case();config['limits'][limit]+=1
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('names',[BASE_ROSTER,['org','torch._rocm_init'],ROSTER03+['guess'],BASE_ROSTER+['torch._other_init']])
def test05_keeps_exact_missing_import_roster(names):
    m,config,_,_,_=acceptance05_case();config['negative_imports']=names
    with pytest.raises(ValueError):m.validate_configuration(config)
    with pytest.raises(ValueError):auditor_api().configuration(config,False)


@pytest.mark.parametrize('path',[PARENT,'scripts/puck_worker_bootstrap.py',BINDINGS,IMPORTS])
def test05_requires_every_changed_source(path):
    m,config,blobs,_,_=acceptance05_case();prior=json.loads(blobs['configuration'])
    old=next(row for row in prior['sources'] if row['path']==path)
    config['sources']=[copy.deepcopy(old) if row['path']==path else row for row in config['sources']]
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('defect',['foreign-source','historical-source','historical-input','historical-roster','stage'])
def test05_cannot_inherit_changed_preparation_history_or_other_source(defect):
    m,config,blobs,_,_=acceptance05_case();prior=json.loads(blobs['configuration'])
    if defect=='foreign-source':
        next(row for row in config['sources'] if row['path']=='src/palimpsest/puck_cpu_registration.py')['sha256']='0'*64
    elif defect=='historical-source':
        prepared=json.loads(blobs['result']);prepared['sources'][0]['sha256']='0'*64
        rebind(m,config,blobs,'result',prepared)
    elif defect=='historical-input':
        prepared=json.loads(blobs['result']);prepared['inputs']['candidate']['sha256']='0'*64
        rebind(m,config,blobs,'result',prepared)
    elif defect=='historical-roster':
        prior['negative_imports']=list(ROSTER03)
        rebind_historical_configuration(m,config,blobs,prior)
    else:config['stage_parent']='/tmp/palimpsest-puck-cpu-held-other'
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,prior,json.loads(blobs['result']))


@pytest.mark.parametrize('role',[
    'inventory','layout','native','baseline','generated','accepted_result','accepted_snapshot',
    'accepted_audit','accepted_configuration','accepted_index','observation_configuration',
    'observation_report','observation_result','observation_audit','observation_index',
])
def test05_refuses_every_other_input_pin_change(role):
    m,config,blobs,_,_=acceptance05_case();config['inputs'][role]['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))


@pytest.mark.parametrize('defect',['unchanged','same-path','same-hash'])
def test05_requires_distinct_candidate_path_and_hash(defect):
    m,config,blobs,_,_=acceptance05_case();old=json.loads(blobs['configuration'])['inputs']['candidate']
    if defect=='unchanged':config['inputs']['candidate']=copy.deepcopy(old)
    else:config['inputs']['candidate']['path' if defect=='same-path' else 'sha256']=old['path' if defect=='same-path' else 'sha256']
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
    with pytest.raises(ValueError):auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))


@pytest.mark.parametrize('version',[1,2,3,4])
def test_legacy_epochs_cannot_admit05_source_and_candidate_delta(version):
    m,config,blobs,_,_=acceptance05_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v'+str(version),version=version,allocation_id=version)
    if version==1:
        with pytest.raises(ValueError):m.validate_configuration(config)
        with pytest.raises(ValueError):auditor_api().configuration(config,False)
    else:
        if version==2:config['negative_imports']=list(BASE_ROSTER)
        m.validate_configuration(config)
        with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)
        with pytest.raises(ValueError):auditor_api().preparation_epoch(config,json.loads(blobs['configuration']),json.loads(blobs['result']))


@pytest.mark.parametrize('provider',['parent','independent'])
@pytest.mark.parametrize('defect',[
    'other-row','module-map','namespace','helper','provenance','top-field','native-cache',
    'module-change','missing-target','duplicate-target','old-missing-target','old-duplicate-target',
    'old-row','creator','path','phase','class','missing-delegates','extra-delegates',
    'unsorted-delegates','duplicate-delegates','missing-delegate-field','extra-row-field',
])
def test05_semantic_candidate_delta_refuses_fully_rebound_tampering(provider,defect):
    m,config,blobs,old,new=acceptance05_case()
    validator=m.validate_publication_candidate if provider=='parent' else auditor_api().publication_candidate
    validator(old,new)
    target=new['import_profile']['exports'][0]
    if defect=='other-row':new['import_profile']['exports'][1]['attributes']=['foreign']
    elif defect=='module-map':new['module_paths'][0]['path']='foreign.py'
    elif defect=='namespace':new['namespaces'].append(dict(name='foreign',root_index=0,path='foreign'))
    elif defect=='helper':new['additional_package_inputs'][0]['files'][0]['sha256']='0'*64
    elif defect=='provenance':new['observation_report_sha256']='0'*64
    elif defect=='top-field':new['caller_selected_policy']=True
    elif defect=='native-cache':new['import_profile']['native_cache'].append(dict(name='foreign'))
    elif defect=='module-change':new['import_profile']['module_changes'].append(dict(name='foreign',kind='replace'))
    elif defect=='missing-target':new['import_profile']['exports'].pop(0)
    elif defect=='duplicate-target':new['import_profile']['exports'].append(copy.deepcopy(target))
    elif defect=='old-missing-target':old['import_profile']['exports'].pop(0)
    elif defect=='old-duplicate-target':old['import_profile']['exports'].append(copy.deepcopy(old['import_profile']['exports'][0]))
    elif defect=='old-row':old['import_profile']['exports'][0]['producer']='foreign'
    elif defect=='creator':target['producer']='torch._C'
    elif defect=='path':target['attributes']=['_autograd']
    elif defect=='phase':target['phase']='module_exec'
    elif defect=='class':target['class_binding']={'name':'foreign'}
    elif defect=='missing-delegates':target['delegate_attributes'].pop()
    elif defect=='extra-delegates':target['delegate_attributes']=sorted(DELEGATES+['_authored_extra'])
    elif defect=='unsorted-delegates':target['delegate_attributes'].reverse()
    elif defect=='duplicate-delegates':target['delegate_attributes']=sorted(DELEGATES+[DELEGATES[0]])
    elif defect=='missing-delegate-field':target.pop('delegate_attributes')
    else:target['caller_selected_policy']=True
    bind_old_candidate(m,config,blobs,old)
    config['inputs']['candidate']=candidate_pin(m,new,'docs/authored-candidate-05.json')
    validate_both(m,config,blobs)
    assert config['inputs']['candidate']['sha256']==m.digest(m.canonical(new))
    with pytest.raises(ValueError):validator(old,new)
