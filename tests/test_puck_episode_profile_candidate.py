"""Episode import-profile candidate 02: schema and derivation from characterization-04.

Authored data only. The episode candidate (kind v2) expects numpy, torch, mujoco
and gymnasium (no torchvision) and keeps the one generated package root so the
four-root staged layout is unchanged. The derivation consumes characterization-04
reports, maps every site module through ``_module_maps``, leaves source-root
modules to the source registration, and filters the accepted template profile
to what the episode actually created.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import time

import pytest

from test_puck_cpu_registration import api as registration_api, attach, build, case, staged
from test_puck_cpu_characterization04 import LEAVES, api as parent_api, authored_sources, report

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/derive_puck_episode_profile.py'
KIND02='puck-cpu-episode-import-profile-candidate-v2'
SITE='/authored/site'
PREFIX='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu'


def sha(raw):return hashlib.sha256(raw).hexdigest()


def pretty(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


def canonical(value):return (json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()


def episode_candidate():
    value=case()['candidate']
    value.update(kind=KIND02,version=2,expected_versions=dict(numpy='1',torch='1+cpu',mujoco='1',gymnasium='1'))
    return value


def test_registration_plans_and_attaches_the_episode_candidate():
    data=case();data['candidate']=episode_candidate()
    plan=build(data)
    assert [r['kind'] for r in plan['roots']]==['package','system_images','system_images','package']
    attached=attach(staged(plan),episode_candidate())
    assert attached['import_profile']==episode_candidate()['import_profile']


@pytest.mark.parametrize('defect',['torchvision','no-gymnasium','v1-version','v1-kind-gymnasium','claims','two-roots'])
def test_registration_refuses_mixed_episode_candidate_schemas(defect):
    data=case();value=episode_candidate()
    if defect=='torchvision':value['expected_versions']['torchvision']='1+cpu'
    elif defect=='no-gymnasium':value['expected_versions'].pop('gymnasium')
    elif defect=='v1-version':value['version']=1
    elif defect=='v1-kind-gymnasium':value['kind']='puck-cpu-observed-import-profile-candidate-v1'
    elif defect=='claims':value['executable']=True
    else:value['additional_package_inputs']*=2
    data['candidate']=value
    with pytest.raises(ValueError):build(data)


def test_historical_candidate_schema_is_unchanged():
    plan=build();assert attach(staged(plan))['import_profile']==case()['candidate']['import_profile']
    data=case();data['candidate']['expected_versions']=dict(numpy='1',torch='1+cpu',mujoco='1',gymnasium='1')
    with pytest.raises(ValueError):build(data)


# --- derivation -------------------------------------------------------------

def api():
    assert SCRIPT.is_file(),'episode profile derivation is missing'
    spec=importlib.util.spec_from_file_location('episode_profile_derivation',SCRIPT)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def module(name,path,*,classification='module'):
    return dict(name=name,spec_name=name,file=path,classification=classification,exports=[])


SITE_FILES=('numpy/__init__.py','numpy/random/__init__.py','numpy/random/bit_generator.cpython-311-x86_64-linux-gnu.so',
    'torch/__init__.py','mujoco/__init__.py','gymnasium/__init__.py','gymnasium/envs/__init__.py','scipy/__init__.py',
    'scipy/_lib/__init__.py','scipy/_lib/_ccallback_c.cpython-311-x86_64-linux-gnu.so',
    'scipy/_lib/_fpumode.cpython-311-x86_64-linux-gnu.so')
CREATOR=dict(cache='_cython_3_0_12',producer='numpy.random.bit_generator',phase='module_exec',
             added=['cython_function_or_method','generator'],first=True)
LATER=dict(cache='_cython_3_0_12',producer='scipy._lib._ccallback_c',phase='module_exec',added=['fused_cython_function'],first=False)


def cache(extra=()):
    rows=[module(path[:-len('/__init__.py')].replace('/','.') if path.endswith('/__init__.py')
                 else path.split('.')[0].replace('/','.'),SITE+'/'+path) for path in SITE_FILES]
    rows+=[module('json',PREFIX+'/lib/python3.11/json/__init__.py'),module('__main__','/puck/source/scripts/w.py'),
        module('_sysconfigdata__linux_x86_64-linux-gnu',PREFIX+'/lib/python3.11/_sysconfigdata__linux_x86_64-linux-gnu.py'),
        module('palimpsest','/puck/source/src/palimpsest/__init__.py'),
        module('palimpsest.engine','/puck/source/src/palimpsest/engine.py'),
        module('core','/puck/source/upstream/fly-gym/core/__init__.py'),
        dict(name='_cython_3_0_12',spec_name=None,file=None,classification='virtual',exports=[]),*extra]
    return sorted(rows,key=lambda r:r['name'])


def template():
    profile=dict(kind='puck-producer-import-profile-v2',version=2,exports=[],
        module_changes=[dict(name='torch._dynamo.config',kind='reclassify',class_binding=dict(kind='direct',
            producer='torch',attributes=['Tensor']))],
        native_origins=[dict(name='PIL._imaging',policy='held-directory-observed-v1'),
                        dict(name='numpy.random.bit_generator',policy='held-directory-observed-v1')],
        native_cache=[dict(name='_cython_3_0_12',producer='numpy.random.bit_generator',phase='module_exec',
                           delegate_attributes=['cython_function_or_method','generator']),
                      dict(name='cython_runtime',producer='numpy.random.bit_generator',phase='module_exec',delegate_attributes=[])])
    value=case()['candidate'];value['import_profile']=profile
    value['expected_versions']=dict(numpy='2.2.5',torch='2.9.0+cpu',torchvision='0.24.0+cpu',mujoco='3.3.6')
    return value


def inventory():
    entries=[dict(path=p,size_bytes=1,sha256='a'*64) for p in sorted(SITE_FILES)]
    return dict(kind='puck-cpu-installed-files-v1',entries=entries,file_count=len(entries),directory_count=0,total_bytes=len(entries))


@pytest.fixture
def evidence(monkeypatch):
    m=api();parent=m.PARENT
    raws=dict(inventory=pretty(inventory()),template=pretty(template()),native=pretty(dict(dynamic_leaves=LEAVES)))
    pins={row['path']:row for row in parent.required_inputs()}
    for role in ('inventory','native'):
        path=parent.ROLES['native_metadata' if role=='native' else role]
        pins[path]=dict(path=path,size_bytes=len(raws[role]),sha256=sha(raws[role]))
    monkeypatch.setattr(parent,'required_inputs',lambda:[pins[p] for p in sorted(pins)])
    monkeypatch.setattr(parent,'ENVIRONMENT',dict(parent.ENVIRONMENT,PYGLFW_LIBRARY=SITE+'/glfw/x11/libglfw.so'))
    config=parent.configuration(authored_sources(parent));raws['configuration']=pretty(config)
    worker=next(r['sha256'] for r in config['sources'] if r['path']==parent.WORKER)
    for phase in ('source','replay'):
        value=report(parent,phase,worker_sha=worker)
        value['environment_sha256']=sha(canonical(parent.ENVIRONMENT))
        value['cache']['modules']=cache([module('palimpsest.body_profile','/puck/source/src/palimpsest/body_profile.py')] if phase=='replay' else [])
        value['import_misses']=['imp','json.tool_missing','org','scipy._distributor_init_local'] if phase=='source' else ['org','pandas']
        value['native_cache_dispatch']=dict(events=[dict(CREATOR),dict(LATER)],unattributed=[],errors=[])
        raws[phase]=canonical(value)
    result=dict(kind='puck-cpu-characterization-outcome-v3',version=3,status='observed',
        configuration_sha256=sha(raws['configuration']),source_report_sha256=sha(raws['source']),
        replay_report_sha256=sha(raws['replay']),runtime_qualified=False,native_authorized=False,
        collection_authorized=False,study_authorized=False,executable=False,qualification_claims=[])
    raws['result']=pretty(result)
    raws['audit']=pretty(dict(kind='cpu-episode-characterization-outcome-audit-v1',status='PASS',
        verified=dict(configuration_sha256=sha(raws['configuration']),result_sha256=sha(raws['result']),
            source_report_sha256=sha(raws['source']),replay_report_sha256=sha(raws['replay']))))
    return m,raws


def derive(m,raws,**changes):
    arguments=dict(configuration=raws['configuration'],result=raws['result'],source=raws['source'],
        replay=raws['replay'],audit=raws['audit'],template=raws['template'],inventory=raws['inventory'],
        native=raws['native'],site_root=SITE)
    arguments.update(changes)
    return m.derive(**arguments)


def test_derivation_maps_site_modules_and_filters_the_template(evidence):
    m,raws=evidence;candidate=derive(m,raws)
    assert candidate['kind']==KIND02 and candidate['version']==2
    assert candidate['expected_versions']==dict(numpy='2.2.5',torch='2.9.0+cpu',mujoco='3.3.6',gymnasium='1.2.1')
    names=[r['name'] for r in candidate['module_paths']]
    assert names==sorted(['gymnasium','gymnasium.envs','mujoco','numpy','numpy.random','numpy.random.bit_generator','scipy',
                          'scipy._lib','scipy._lib._ccallback_c','scipy._lib._fpumode','torch'])
    assert all(r['root_index']==0 for r in candidate['module_paths'])
    assert candidate['source_modules']==['core','palimpsest','palimpsest.body_profile','palimpsest.engine']
    profile=candidate['import_profile']
    assert profile['module_changes']==[] and profile['native_cache']==[dict(name='_cython_3_0_12',producer='numpy.random.bit_generator',
        phase='module_exec',delegate_attributes=['cython_function_or_method','generator'],
        late_delegates=[dict(attribute='fused_cython_function',producers=[dict(producer='scipy._lib._ccallback_c',phase='module_exec')])])]
    assert [r['name'] for r in profile['native_origins']]==['numpy.random.bit_generator']
    assert candidate['observation_reports']==dict(source=sha(raws['source']),replay=sha(raws['replay']))
    assert candidate['characterization_configuration_sha256']==sha(raws['configuration'])
    assert candidate['observation_result_sha256']==sha(raws['result'])
    assert candidate['outcome_audit_sha256']==sha(raws['audit'])
    assert candidate['retained_inventory_sha256']==sha(raws['inventory'])
    assert candidate['template_sha256']==sha(raws['template'])
    assert candidate['native_metadata_sha256']=='48ca37b1c45366bcd53ac195277ade6236537f89a720b50591906764eaf72569'
    # 3.11 stdlib names (imp, json.*) are not misses; every other miss is a declared absent or hidden name.
    assert candidate['import_misses']==['org','pandas','scipy._distributor_init_local']
    assert candidate['additional_package_inputs']==template()['additional_package_inputs']
    assert all(candidate[k] is False for k in ('native_phase_qualified','held_runtime_qualified','native_authorized',
        'collection_authorized','study_authorized','executable')) and candidate['qualification_claims']==[]
    registration_api()._candidate(candidate,time.monotonic()+30)


def test_derivation_writes_once(evidence,tmp_path):
    m,raws=evidence;target=tmp_path/'candidate-02.json'
    value=m.write(derive(m,raws),target);raw=target.read_bytes()
    assert raw==pretty(json.loads(raw)) and value['sha256']==sha(raw)
    with pytest.raises(FileExistsError):m.write(derive(m,raws),target)


@pytest.mark.parametrize('defect',['result-failed','result-config','report-spawn','report-sha','audit-failed','audit-result',
    'outside-site','unlisted-source','generated-helper','phase-conflict','unmapped-site-file','config-sha','site-root',
    'dispatch-creator','dispatch-base','dispatch-absent','dispatch-unlisted-cache','undeclared-miss','native-pin'])
def test_derivation_refuses_unbound_or_unmappable_evidence(evidence,defect):
    m,raws=evidence;changes={}
    def edit(name,function,encode=canonical):
        value=json.loads(raws[name]);function(value);changes[name]=encode(value)
    if defect=='result-failed':edit('result',lambda v:v.update(status='FAIL'),pretty)
    elif defect=='result-config':edit('result',lambda v:v.update(configuration_sha256='0'*64),pretty)
    elif defect=='report-spawn':edit('source',lambda v:v.update(process_creation_attempts=dict(count=1,events=['os.fork'])))
    elif defect=='report-sha':changes['source']=raws['source'].replace(b'"rechecks":9',b'"rechecks":10')
    elif defect=='audit-failed':edit('audit',lambda v:v.update(status='FAIL'),pretty)
    elif defect=='audit-result':edit('audit',lambda v:v['verified'].update(result_sha256='0'*64),pretty)
    elif defect=='outside-site':edit('source',lambda v:v['cache']['modules'].append(module('stray','/opt/stray.py')))
    elif defect=='unlisted-source':edit('source',lambda v:v['cache']['modules'].append(module('palimpsest.ghost','/puck/source/src/palimpsest/ghost.py')))
    elif defect=='generated-helper':edit('source',lambda v:v['cache']['modules'].append(module('_remote_module_non_scriptable','/scratch/tmp/x/_remote_module_non_scriptable.py')))
    elif defect=='phase-conflict':edit('replay',lambda v:next(r for r in v['cache']['modules'] if r['name']=='scipy').update(file=SITE+'/torch/__init__.py'))
    elif defect=='unmapped-site-file':edit('source',lambda v:v['cache']['modules'].append(module('torch.extra',SITE+'/torch/extra.py')))
    elif defect=='dispatch-creator':edit('source',lambda v:v['native_cache_dispatch']['events'][0].update(producer='numpy.random'))
    elif defect=='dispatch-base':edit('source',lambda v:v['native_cache_dispatch']['events'][0].update(added=['generator']))
    elif defect=='dispatch-absent':edit('replay',lambda v:v['native_cache_dispatch'].update(events=[]))
    elif defect=='dispatch-unlisted-cache':edit('source',lambda v:v['native_cache_dispatch']['events'].append(
        dict(LATER,cache='_cython_other',added=['x'],first=True)))
    elif defect=='undeclared-miss':edit('source',lambda v:v['import_misses'].append('requests'))
    elif defect=='native-pin':changes['native']=pretty(dict(dynamic_leaves=LEAVES[:1]))
    elif defect=='config-sha':changes['configuration']=raws['configuration'][:-1]+b' \n'
    else:changes['site_root']='/other/site'
    if defect in ('report-spawn','report-sha','outside-site','unlisted-source','generated-helper','phase-conflict','unmapped-site-file',
                  'dispatch-creator','dispatch-base','dispatch-absent','dispatch-unlisted-cache','undeclared-miss'):
        name='replay' if defect in ('phase-conflict','dispatch-absent') else 'source'
        result=json.loads(raws['result']);result[name+'_report_sha256']=sha(changes[name]);changes['result']=pretty(result)
        audit=json.loads(raws['audit']);audit['verified'][name+'_report_sha256']=sha(changes[name])
        audit['verified']['result_sha256']=sha(changes['result']);changes['audit']=pretty(audit)
        if defect=='report-sha':changes.update(result=raws['result'],audit=raws['audit'])
    with pytest.raises(ValueError):derive(m,raws,**changes)


def replay_producer(m,raws,producer):
    value=json.loads(raws['replay']);value['native_cache_dispatch']['events'][1]['producer']=producer
    replay=canonical(value);result=json.loads(raws['result']);result['replay_report_sha256']=sha(replay);result_raw=pretty(result)
    audit=json.loads(raws['audit']);audit['verified'].update(replay_report_sha256=sha(replay),result_sha256=sha(result_raw))
    return derive(m,raws,replay=replay,result=result_raw,audit=pretty(audit))


def test_a_later_key_seen_from_different_producers_declares_both(evidence):
    m,raws=evidence;candidate=replay_producer(m,raws,'scipy._lib._fpumode')
    assert candidate['import_profile']['native_cache'][0]['late_delegates']==[dict(attribute='fused_cython_function',
        producers=[dict(producer='scipy._lib._ccallback_c',phase='module_exec'),dict(producer='scipy._lib._fpumode',phase='module_exec')])]
    with pytest.raises(ValueError):replay_producer(m,raws,'scipy._lib')
