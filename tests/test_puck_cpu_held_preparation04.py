"""Preparation04 (allocation 15): the held episode's data, bound to characterization-04.

Authored metadata only, no allocation runs. Preparation04 keeps the preparation
clocks, floors and roster but prepares the episode closure: native metadata v6,
episode candidate 02 (numpy, torch, mujoco, gymnasium) and the characterization-04
observation roles, including the replay report. Every older allocation keeps its
characterization02 binding byte-for-byte.
"""
import copy
import hashlib
import json

import pytest

from test_puck_cpu_held_parent import link_case
from test_puck_cpu_held_preparation02 import FLOORS, preparation02_config
from test_puck_cpu_held_preparation03 import CLOCKS, preparation03_config


# Independently authored identity; do not derive from producer constants.
KIND04='puck-cpu-held-runtime-allocation-v15'
OUTPUT04='runs/puck-cpu-held-preparation-04'
STAGE04='/tmp/palimpsest-puck-cpu-held-04'
EPISODE_VERSIONS=dict(numpy='2.2.5',torch='2.9.0+cpu',mujoco='3.3.6',gymnasium='1.2.1')
REPLAY_ROLE='observation_replay_report'
EMPTY=('upstream/fly-gym/core/__init__.py','upstream/fly-gym/environment/__init__.py')
NINE=['/etc/ld.so.cache','/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11',
    *('/usr/lib/'+name for name in ('ld-linux-x86-64.so.2','libc.so.6','libdl.so.2','libm.so.6','libpthread.so.0',
                                    'librt.so.1','libutil.so.1'))]
LOCALE=['/usr/lib/gconv/gconv-modules.cache','/usr/lib/locale/C.utf8/LC_CTYPE','/usr/lib/locale/locale-archive']


def sha(raw):return hashlib.sha256(raw).hexdigest()


def preparation04_config(stage=STAGE04):
    m,config,prior=preparation02_config(stage)
    sources=[dict(path=p,size_bytes=0 if p in EMPTY else 1,sha256='a'*64) for p in m.PREPARATION04_SOURCES]
    inputs=copy.deepcopy(config['inputs'])
    inputs[REPLAY_ROLE]=dict(path='docs/authored-'+REPLAY_ROLE+'.json',size_bytes=1,sha256='b'*64)
    config.update(kind=KIND04,version=15,allocation_id=15,expected_versions=dict(EPISODE_VERSIONS),
                  sources=sources,inputs=inputs)
    return m,config,prior


def test_preparation04_has_a_distinct_identity_output_and_stage():
    m,config,_=preparation04_config();m.validate_configuration(config)
    assert m.allocation_output(config)==m.preparation_output(config)==OUTPUT04==m.PREPARATION04
    assert len({OUTPUT04,m.PREPARATION03,m.PREPARATION02,m.OUTPUTS['prepare']})==4
    assert m.bound_preparation(15)==15 and m.bound_preparation(14)==13 and m.bound_preparation(11)==12
    assert (config['kind'],config['version'],config['allocation_id'],config['phase'])==(KIND04,15,15,'prepare')
    assert 'preparation' not in config and 'preparation_acceptance' not in config


def test_preparation04_keeps_preparation_limits_and_roster_but_prepares_the_episode_closure():
    m,config,prior=preparation04_config();m.validate_configuration(config)
    assert config['limits']==m.LIMITS['prepare']==prior['limits']
    assert {k:config['limits'][k] for k in FLOORS}==FLOORS and {k:config['limits'][k] for k in CLOCKS}==CLOCKS
    assert config['negative_imports']==m.PREPARATION_NEGATIVE_IMPORTS
    assert m.EPISODE_VERSIONS==EPISODE_VERSIONS and config['expected_versions']==EPISODE_VERSIONS
    assert set(config['inputs'])==set(m.INPUT_ROLES)|{REPLAY_ROLE} and REPLAY_ROLE not in m.INPUT_ROLES
    assert set(m.PREPARATION04_SOURCES)==set(m.SOURCES)|set(m.EPISODE_WORKER_SOURCES)
    assert list(m.PREPARATION04_SOURCES)==sorted(m.PREPARATION04_SOURCES)
    for key in ('root','interpreter','environment','claims','phase'):assert config[key]==prior[key]


@pytest.mark.parametrize('stage',['/tmp/palimpsest-puck-cpu-held-04','/tmp/palimpsest-puck-cpu-held-04-authored-0a1b'])
def test_preparation04_accepts_only_its_own_stage_family(stage):
    m,config,_=preparation04_config(stage);m.validate_configuration(config)


@pytest.mark.parametrize('defect',['stage03','stage03-family','stage-prefix','qualify','v13-version','v13-id','v13-kind',
    'bool-version','bool-id','preparation-key','acceptance-key','limits-clock','limits-q14','torchvision','no-replay-role',
    'old-sources','roster','extra','empty-nonempty-size'])
def test_preparation04_refuses_aliases_reuse_and_policy_changes(defect):
    m,config,_=preparation04_config()
    if defect=='stage03':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-03'
    elif defect=='stage03-family':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-03-authored-0a1b'
    elif defect=='stage-prefix':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-040'
    elif defect=='qualify':config.update(phase='qualify',limits=copy.deepcopy(m.LIMITS['qualify']))
    elif defect=='v13-version':config['version']=13
    elif defect=='v13-id':config['allocation_id']=13
    elif defect=='v13-kind':config['kind']='puck-cpu-held-runtime-allocation-v13'
    elif defect=='bool-version':config['version']=True
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='preparation-key':config['preparation']=dict(path=OUTPUT04+'/result.json',size_bytes=1,sha256='a'*64)
    elif defect=='acceptance-key':config['preparation_acceptance']={}
    elif defect=='limits-clock':config['limits']['normal_seconds']=360
    elif defect=='limits-q14':config['limits']=dict(config['limits'],normal_seconds=360,child_hard_seconds=375,hard_seconds=390)
    elif defect=='torchvision':config['expected_versions']=dict(m.VERSIONS)
    elif defect=='no-replay-role':config['inputs'].pop(REPLAY_ROLE)
    elif defect=='old-sources':config['sources']=[dict(path=p,size_bytes=1,sha256='a'*64) for p in m.SOURCES]
    elif defect=='roster':config['negative_imports']=['org']
    elif defect=='extra':config['output']=m.PREPARATION03
    else:next(r for r in config['sources'] if r['path']=='pyproject.toml')['size_bytes']=-1
    with pytest.raises(ValueError):m.validate_configuration(config)


def test_older_allocations_keep_their_closures_and_bindings():
    m,config,_=preparation03_config();m.validate_configuration(config)
    for change in ('replay-role','episode-versions','empty-source','stage04'):
        value=copy.deepcopy(config)
        if change=='replay-role':value['inputs'][REPLAY_ROLE]=dict(path='docs/x.json',size_bytes=1,sha256='b'*64)
        elif change=='episode-versions':value['expected_versions']=dict(EPISODE_VERSIONS)
        elif change=='empty-source':value['sources'][0]['size_bytes']=0
        else:value['stage_parent']=STAGE04
        with pytest.raises(ValueError):m.validate_configuration(value)
    m,config,blobs=link_case();m.validate_observation_links(config,blobs)


# --- characterization-04 observation links and inputs -----------------------

ROLES=('inventory','layout','native','baseline','accepted_result','accepted_snapshot','accepted_audit',
       'accepted_configuration','accepted_index')
OBSERVATION_PATHS=dict(observation_configuration='frozen-configuration.json',
    observation_report='raw/payload/source/characterization.json',
    observation_replay_report='raw/payload/replay/characterization.json',
    observation_result='raw/result.json',observation_audit='outcome-audit-04.json')


def episode_case():
    """Authored characterization-04 links and every validate_inputs document for allocation 15."""
    m,config,blobs=link_case();inputs=config['inputs'];site=str(m.ROOT/m.SITE)
    canonical=m.canonical
    def put(role,value):
        raw=canonical(value);blobs[role]=raw;inputs[role]=dict(path='docs/'+role+'.json',size_bytes=len(raw),sha256=sha(raw))
    inventory=dict(kind='puck-cpu-installed-files-v1',entries=[],file_count=3,directory_count=2,total_bytes=30)
    put('inventory',inventory)
    put('layout',dict(kind='palimpsest-cpu-wheel-install-layout-v1',version=1,predicted_destination_directories=['a','b']))
    accepted_config=json.loads(blobs['accepted_configuration']);accepted_config['inputs']=[inputs['layout']]
    raw=(json.dumps(accepted_config,indent=2)+'\n').encode();blobs['accepted_configuration']=raw
    inputs['accepted_configuration']=dict(inputs['accepted_configuration'],size_bytes=len(raw),sha256=sha(raw))
    put('accepted_snapshot',dict(site_root=site,configuration_sha256=inputs['accepted_configuration']['sha256']))
    put('accepted_result',dict(kind='cpu-retained-installation-admission-result-v2',status='PASS',site_root=site,
        configuration_sha256=inputs['accepted_configuration']['sha256'],snapshot_sha256=inputs['accepted_snapshot']['sha256'],
        file_count=3,directory_count=2,regular_file_bytes=30,claims=dict(package_preparation_accepted=True,
        runtime_qualified=False,numerical_imports_executed=False,study_authorized=False,collection_authorized=False)))
    put('accepted_audit',dict(status='PASS',package_preparation_accepted=True,
        verified=dict(configuration_sha256=inputs['accepted_configuration']['sha256'])))
    put('native',dict(kind='puck-cpu-characterization-native-metadata-v6',dynamic_leaves=list(LOCALE)))
    accepted_names={'inventory':'raw/inventory.json','accepted_result':'raw/result.json','accepted_snapshot':'raw/snapshot.json',
        'accepted_audit':'acceptance-audit-03.json','accepted_configuration':'raw/configuration.json'}
    retained=canonical(json.loads(blobs['accepted_configuration']))
    entries=[dict(inputs[k],path=v) for k,v in accepted_names.items()]
    next(r for r in entries if r['path']=='raw/configuration.json').update(size_bytes=len(retained),sha256=sha(retained))
    put('accepted_index',dict(kind='retained-admission-02-evidence-index-v1',entries=entries))
    put('observation_configuration',dict(kind='puck-cpu-runtime-characterization-v3',version=3,
        roles={**{('native_metadata' if k=='native' else k):inputs[k]['path'] for k in ROLES},
               'observation02_configuration':'docs/reports/puck-cpu-characterization-02/frozen-configuration.json'},
        inputs=[inputs[k] for k in ROLES]))
    images=[dict(path=p) for p in sorted(NINE+LOCALE)]
    for role,phase in (('observation_report','source'),(REPLAY_ROLE,'replay')):
        put(role,dict(m.CLAIMS,kind='puck-episode-characterization-result-v1',version=1,status='observed',phase=phase,
            versions=dict(EPISODE_VERSIONS),expected_versions=dict(EPISODE_VERSIONS),baseline_maps=dict(images=images)))
    put('observation_result',dict(m.CLAIMS,kind='puck-cpu-characterization-outcome-v3',version=3,status='observed',
        configuration_sha256=inputs['observation_configuration']['sha256'],versions=dict(EPISODE_VERSIONS),
        source_report_sha256=inputs['observation_report']['sha256'],replay_report_sha256=inputs[REPLAY_ROLE]['sha256']))
    put('observation_audit',dict(kind='cpu-episode-characterization-outcome-audit-v1',status='PASS',
        verified=dict(configuration_sha256=inputs['observation_configuration']['sha256'],
            result_sha256=inputs['observation_result']['sha256'],source_report_sha256=inputs['observation_report']['sha256'],
            replay_report_sha256=inputs[REPLAY_ROLE]['sha256'])))
    put('observation_index',dict(kind='cpu-episode-characterization-evidence-index-v1',
        entries=[dict(inputs[k],path=v) for k,v in OBSERVATION_PATHS.items()]))
    generated=dict(path='_remote_module_non_scriptable.py',size_bytes=5,sha256='c'*64)
    inputs['generated']=dict(generated,path='docs/generated/_remote_module_non_scriptable.py')
    put('candidate',dict(kind='puck-cpu-episode-import-profile-candidate-v2',version=2,expected_versions=dict(EPISODE_VERSIONS),
        characterization_configuration_sha256=inputs['observation_configuration']['sha256'],
        observation_reports=dict(source=inputs['observation_report']['sha256'],replay=inputs[REPLAY_ROLE]['sha256']),
        observation_result_sha256=inputs['observation_result']['sha256'],outcome_audit_sha256=inputs['observation_audit']['sha256'],
        retained_inventory_sha256=inputs['inventory']['sha256'],native_metadata_sha256=inputs['native']['sha256'],
        additional_package_inputs=[dict(root='docs/generated',files=[generated])]))
    config=dict(config,version=15,inputs=inputs)
    return m,config,blobs


def test_preparation04_binds_characterization04_and_candidate02():
    m,config,blobs=episode_case()
    inventory,layout,candidate,observation=m.validate_inputs(config,blobs)
    assert candidate['kind']=='puck-cpu-episode-import-profile-candidate-v2'
    assert observation['phase']=='source'
    native=json.loads(blobs['native'])
    assert m.baseline_images(config,observation,native)==sorted(NINE)


@pytest.mark.parametrize('defect',['frozen-kind','frozen-role','index-kind','index-replay','result-replay','result-config',
    'result-failed','report-phase','report-torchvision','replay-status','audit-failed','audit-replay','candidate-kind',
    'candidate-replay','candidate-native','candidate-result','candidate-torchvision','generated'])
def test_preparation04_refuses_unbound_characterization04_evidence(defect):
    m,config,blobs=episode_case();inputs=config['inputs']
    def edit(role,function):
        value=json.loads(blobs[role]);function(value);blobs[role]=m.canonical(value)
    if defect=='frozen-kind':edit('observation_configuration',lambda v:v.update(kind='puck-cpu-runtime-characterization-v1',version=1))
    elif defect=='frozen-role':edit('observation_configuration',lambda v:v['roles'].update(native_metadata='docs/other.json'))
    elif defect=='index-kind':edit('observation_index',lambda v:v.update(kind='cpu-characterization-evidence-index-v2'))
    elif defect=='index-replay':edit('observation_index',lambda v:v.update(entries=[r for r in v['entries'] if 'replay' not in r['path']]))
    elif defect=='result-replay':edit('observation_result',lambda v:v.update(replay_report_sha256='0'*64))
    elif defect=='result-config':edit('observation_result',lambda v:v.update(configuration_sha256='0'*64))
    elif defect=='result-failed':edit('observation_result',lambda v:v.update(status='FAIL'))
    elif defect=='report-phase':edit('observation_report',lambda v:v.update(phase='replay'))
    elif defect=='report-torchvision':edit(REPLAY_ROLE,lambda v:v['versions'].update(torchvision='0.24.0+cpu'))
    elif defect=='replay-status':edit(REPLAY_ROLE,lambda v:v.update(status='failed'))
    elif defect=='audit-failed':edit('observation_audit',lambda v:v.update(status='FAIL'))
    elif defect=='audit-replay':edit('observation_audit',lambda v:v['verified'].update(replay_report_sha256='0'*64))
    elif defect=='candidate-kind':edit('candidate',lambda v:v.update(kind='puck-cpu-observed-import-profile-candidate-v1',version=1))
    elif defect=='candidate-replay':edit('candidate',lambda v:v['observation_reports'].update(replay='0'*64))
    elif defect=='candidate-native':edit('candidate',lambda v:v.update(native_metadata_sha256='0'*64))
    elif defect=='candidate-result':edit('candidate',lambda v:v.update(observation_result_sha256='0'*64))
    elif defect=='candidate-torchvision':edit('candidate',lambda v:v['expected_versions'].update(torchvision='0.24.0+cpu'))
    else:inputs['generated']=dict(inputs['generated'],sha256='0'*64)
    with pytest.raises(ValueError):m.validate_inputs(config,blobs)


def test_v15_baseline_admits_only_declared_dynamic_leaves_beyond_the_nine():
    m,config,blobs=episode_case();observation=json.loads(blobs['observation_report']);native=json.loads(blobs['native'])
    extra=dict(observation,baseline_maps=dict(images=[dict(path=p) for p in sorted(NINE+LOCALE+['/usr/lib/libstray.so'])]))
    assert '/usr/lib/libstray.so' in m.baseline_images(config,extra,native)
    old=dict(config,version=14)
    assert m.baseline_images(old,observation,native)==sorted(NINE+LOCALE)
