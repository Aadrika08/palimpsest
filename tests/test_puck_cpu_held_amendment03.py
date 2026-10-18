"""Closed qualification03 roster and real authored failure-to-success custody."""
import copy
from contextlib import contextmanager
import json

import pytest

from test_puck_cpu_held_amendment import acceptance_case, amendment_fixture, rebind
from test_puck_cpu_held_parent_integration import canonical, digest, run_cli
from test_puck_cpu_runtime_entry import (
    CPU_VERSIONS, ORDER, authored, cpu_policy, cpu_setup, dependency_fixture, descriptor,
)


BASE_ROSTER=['numpy._distributor_init_local','org']
ROSTER03=['numpy._distributor_init_local','org','torch._rocm_init']


def rebind_historical_configuration(m,config,blobs,prior):
    raw=m.canonical(prior);pin=config['preparation_acceptance']['configuration']
    pin.update(size_bytes=len(raw),sha256=digest(raw));blobs['configuration']=raw
    prepared=json.loads(blobs['result']);prepared['configuration_sha256']=digest(raw)
    rebind(m,config,blobs,'result',prepared)
    audit=json.loads(blobs['independent_audit']);audit['configuration_sha256']=digest(raw)
    rebind(m,config,blobs,'independent_audit',audit)
    cli=json.loads(blobs['externally_observed_auditor_cli']);cli['command'][8]=digest(raw)
    rebind(m,config,blobs,'externally_observed_auditor_cli',cli)


def acceptance03_case():
    m,config,blobs=acceptance_case()
    prior=json.loads(blobs['configuration']);prior['negative_imports']=list(BASE_ROSTER)
    rebind_historical_configuration(m,config,blobs,prior)
    config.update(kind='puck-cpu-held-runtime-allocation-v3',version=3,allocation_id=3,negative_imports=list(ROSTER03))
    return m,config,blobs


def test_closed03_epoch_accepts_exact_one_name_delta_from_historical_preparation():
    m,config,blobs=acceptance03_case()
    m.validate_configuration(config)
    prior,prepared=m.validate_preparation_acceptance(config,blobs)
    assert prior['negative_imports']==BASE_ROSTER
    assert prepared['configuration_sha256']==config['preparation_acceptance']['configuration']['sha256']
    assert m.allocation_output(config)=='runs/puck-cpu-held-qualification-03'


@pytest.mark.parametrize('defect',['kind','version','id','bool-id','phase','output','limit'])
def test_03_schema_does_not_create_an_open_epoch_selector(defect):
    m,config,_=acceptance03_case()
    if defect=='kind':config['kind']='puck-cpu-held-runtime-allocation-v4'
    elif defect=='version':config['version']=2
    elif defect=='id':config['allocation_id']=4
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='phase':config['phase']='prepare';config['limits']=copy.deepcopy(m.LIMITS['prepare'])
    elif defect=='output':config['output']='runs/puck-cpu-held-qualification-01'
    else:config['limits']['normal_seconds']+=1
    with pytest.raises(ValueError):m.validate_configuration(config)


@pytest.mark.parametrize('roster',[BASE_ROSTER,['org','torch._rocm_init'],ROSTER03+['torch.other'],
    BASE_ROSTER+['torch.other'],ROSTER03+['torch._rocm_init.child']])
def test_03_only_accepts_the_observed_optional_name(roster):
    m,config,_=acceptance03_case();config['negative_imports']=roster
    with pytest.raises(ValueError):m.validate_configuration(config)


@pytest.mark.parametrize('defect',['historical-roster','data','foreign-source'])
def test_03_roster_delta_does_not_admit_other_history_data_or_source_changes(defect):
    m,config,blobs=acceptance03_case()
    if defect=='historical-roster':
        prior=json.loads(blobs['configuration']);prior['negative_imports']=list(ROSTER03)
        rebind_historical_configuration(m,config,blobs,prior)
    elif defect=='data':config['inputs']['candidate']['sha256']='0'*64
    else:next(r for r in config['sources'] if r['path'].endswith('puck_dependency_imports.py'))['sha256']='0'*64
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)


def test_legacy02_still_requires_identical_historical_missing_import_policy():
    m,config,blobs=acceptance03_case()
    config.update(kind='puck-cpu-held-runtime-allocation-v2',version=2,allocation_id=2)
    m.validate_configuration(config)
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)


@pytest.mark.parametrize('case',['declared-absent','undeclared-absent','declared-present'])
def test_existing_guard_handles_caught_relative_optional_import_without_policy_relaxation(case):
    def mutate(deps,root):
        cpu_setup(deps,root,'before-init' if case=='declared-present' else None)
        path=root/'torch/__init__.py'
        path.write_text(path.read_text()+'try:\n from . import _rocm_init\nexcept ImportError:\n pass\n')
        if case=='declared-present':
            target=root/'torch/_rocm_init.py';target.write_text('raise AssertionError("OPTIONAL_TARGET_RAN")\n')
            deps['modules'].append(dict(name='torch._rocm_init',root_index=0,path='torch/_rocm_init.py',kind='python',is_package=False))
            deps['roots'][0]['files'].append(descriptor(target,'torch/_rocm_init.py'))
        deps['roots'][0]['files']=sorted([descriptor(root/row['path'],row['path']) for row in deps['roots'][0]['files']],key=lambda row:row['path'])
    def policy(reg,source):
        cpu_policy(reg,source)
        if case!='undeclared-absent':reg['qualification']['negative_imports']=list(ROSTER03)
    with authored() as base:
        result,_=dependency_fixture(base,'raise AssertionError("DEFAULT_ENTRY_RAN")',mutate=mutate,source_change=policy)
        if case=='declared-absent':
            assert result.returncode==0,result.stderr
            receipt=json.loads(result.stdout);entry=receipt['entry_result']
            assert [r['name'] for r in entry['imports']]==ORDER
            assert {r['name']:r['version'] for r in entry['imports']}==CPU_VERSIONS
            assert receipt['expected_missing_imports']==receipt['denied_imports']==ROSTER03
            assert entry['status']=='imports_completed'
            for value in (receipt,entry):
                assert value['runtime_qualified'] is value['native_authorized'] is value['collection_authorized'] is value['executable'] is False
                assert value['qualification_claims']==[]
        else:
            assert result.returncode!=0 and result.stdout=='',result.stderr
            assert 'torch._rocm_init' in result.stderr,result.stderr
            assert 'DEFAULT_ENTRY_RAN' not in result.stderr
            if case=='declared-present':
                assert 'overlaps a registered module' in result.stderr
                assert 'NUMERICAL_INIT_RAN' not in result.stderr and 'OPTIONAL_TARGET_RAN' not in result.stderr


@contextmanager
def amendment03_fixture(tmp_path):
    with amendment_fixture(tmp_path,rocm_probe=True) as case:
        root,m,config=(case[k] for k in ('root','api','config'))
        code,stdout,stderr=run_cli(root,m,'qualify02',config)
        assert code==1,(code,stdout,stderr)
        output=root/'runs/puck-cpu-held-qualification-02'
        result=json.loads((output/'result.json').read_bytes())
        assert json.loads(stdout)==result and result['status']=='FAIL'
        assert result['held_four_imports_observed'] is False
        assert not (output/'baseline-after.json').exists()
        assert b'torch._rocm_init' in (output/'logs/stderr.log').read_bytes()
        for p in list(output.rglob('*'))+list(root.glob('authored-qualify02-*')):
            if p.is_file():case['legacy_bytes'][str(p.relative_to(root))]=p.read_bytes()
        updated=copy.deepcopy(config)
        updated.update(kind='puck-cpu-held-runtime-allocation-v3',version=3,allocation_id=3,
            negative_imports=['org','torch._rocm_init'])
        assert not (root/'runs/puck-cpu-held-qualification-03').exists()
        yield dict(case,config=updated)


@pytest.mark.runs_basetemp  # asserts a persistent basetemp under runs/ (see docs/testing.md)
def test_authored03_completes_after_real_failed01_02_without_changing_their_bytes(tmp_path):
    with amendment03_fixture(tmp_path) as case:
        root,m,config,stage=(case[k] for k in ('root','api','config','stage'))
        identities=[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        code,stdout,stderr=run_cli(root,m,'qualify03',config)
        output=root/'runs/puck-cpu-held-qualification-03'
        retained=(output/'result.json').read_bytes() if (output/'result.json').exists() else b''
        assert code==0,(code,stdout,stderr,retained)
        result=json.loads(retained)
        assert json.loads(stdout)==result
        assert (result['kind'],result['version'],result['allocation_id'],result['status'])==('puck-cpu-held-runtime-outcome-v3',3,3,'imports_completed')
        worker=json.loads((output/'logs/stdout.log').read_bytes())
        assert worker['expected_missing_imports']==['org','torch._rocm_init']
        assert worker['denied_imports']==['torch._rocm_init']
        registration=json.loads((output/'control/worker-registration.json').read_bytes())
        assert registration['qualification']['negative_imports']==config['negative_imports']
        assert registration['source_files']==[r for r in config['sources'] if r['path'] in m.WORKER_SOURCES]
        for row in registration['source_files']:
            raw=(output/'worker-source'/row['path']).read_bytes()
            assert len(raw)==row['size_bytes'] and digest(raw)==row['sha256']
        invocation=json.loads((output/'invocation.json').read_bytes())
        at=invocation['command'].index(str(output/'worker-source'))
        assert invocation['command'][at-1:at+2]==['--ro-bind',str(output/'worker-source'),'/puck/source']
        assert identities==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        for path,raw in case['legacy_bytes'].items():assert (root/path).read_bytes()==raw
        assert all(result[k]==v for k,v in m.CLAIMS.items())
        assert result['closure']['active_children']==result['closure']['active_non_main_threads']==[]
        assert result['closure']['fd_count_before']==result['closure']['fd_count_after']
        code,_,stderr=run_cli(root,m,'qualify03-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert (output/'result.json').read_bytes()==retained
        for path,raw in case['legacy_bytes'].items():assert (root/path).read_bytes()==raw
