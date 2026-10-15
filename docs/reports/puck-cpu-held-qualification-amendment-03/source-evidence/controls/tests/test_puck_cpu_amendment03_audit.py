"""Closed qualification03 auditing with authored data only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import time

import pytest

from test_puck_cpu_held_runtime_audit import api
from test_puck_cpu_amendment_audit import configuration as configuration02, historical, acceptance_files


def configuration03(m,authored=True):
    value=configuration02(m)
    value.update(kind='puck-cpu-held-runtime-allocation-v3',version=3,allocation_id=3,
        limits=m.limits('qualify',authored),negative_imports=(['org'] if authored else ['numpy._distributor_init_local','org'])+['torch._rocm_init'])
    return value


@pytest.mark.parametrize('authored',[False,True])
def test_only_closed03_policy_can_reach_the_new_output(authored):
    m=api();value=configuration03(m,authored);m.configuration(value,authored)
    assert m.allocation_output(value)=='runs/puck-cpu-held-qualification-03'


@pytest.mark.parametrize('field,value',[('kind','puck-cpu-held-runtime-allocation-v4'),('version',2),
    ('version',True),('allocation_id',2),('allocation_id',True),('phase','prepare')])
def test03_identity_cannot_alias_other_epochs(field,value):
    m=api();config=configuration03(m);config[field]=value
    with pytest.raises(ValueError):m.configuration(config,True)


@pytest.mark.parametrize('names',[['org'],['torch._rocm_init'],['org','torch._rocm_init','unknown'],
    ['org','torch._other_init'],['org','org','torch._rocm_init'],['torch._rocm_init','org']])
def test03_roster_is_exact_and_ordered(names):
    m=api();config=configuration03(m);config['negative_imports']=names
    with pytest.raises(ValueError):m.configuration(config,True)


def test02_still_refuses_the_new_missing_name():
    m=api();value=configuration02(m);value['negative_imports'].append('torch._rocm_init')
    with pytest.raises(ValueError):m.configuration(value,True)


def epoch(m):
    old,prep=historical(m,configuration02(m));current=configuration03(m)
    return current,old,prep


def test03_only_changes_the_current_missing_roster_by_the_observed_name():
    m=api();current,old,prep=epoch(m);m.preparation_epoch(current,old,prep)
    assert old['negative_imports']==['org']


@pytest.mark.parametrize('defect',['not-added','extra','substitute','old-added','data','source'])
def test03_does_not_relabel_changed_historical_policy_or_inputs(defect):
    m=api();current,old,prep=epoch(m)
    if defect=='not-added':current['negative_imports']=['org']
    elif defect=='extra':current['negative_imports'].append('guess')
    elif defect=='substitute':current['negative_imports']=['org','torch._other_init']
    elif defect=='old-added':old['negative_imports'].append('torch._rocm_init')
    elif defect=='data':current['inputs']['candidate']['sha256']='0'*64
    else:next(r for r in current['sources'] if r['path'].endswith('puck_dependency_imports.py'))['sha256']='0'*64
    with pytest.raises(ValueError):m.preparation_epoch(current,old,prep)


def test03_keeps_the_original_preparation_auditor_identity(tmp_path):
    m=api();current=acceptance_files(m,tmp_path)
    current.update(kind='puck-cpu-held-runtime-allocation-v3',version=3,allocation_id=3,
        negative_imports=['org','torch._rocm_init'])
    before=len(os.listdir('/proc/self/fd'));held=m.Held(time.monotonic()+10)
    try:
        old,prep,audit=m.historical_acceptance(held,current,True)
        assert old['negative_imports']==['org'] and prep['sources']==old['sources']!=current['sources']
        assert audit['auditor_source_sha256']=='19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9'
    finally:held.close()
    assert len(os.listdir('/proc/self/fd'))==before


def test03_outcome_cannot_reuse02_identity():
    m=api();config=configuration03(m)
    value=dict(m.CLAIMS,kind='puck-cpu-held-runtime-outcome-v3',version=3,phase='qualify',allocation_id=3,
        configuration_sha256='a'*64,status='imports_completed',held_four_imports_observed=True,elapsed_seconds=1.0,
        closure=dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5))
    m.outcome(value,config,'a'*64)
    old=copy.deepcopy(value);old.update(kind='puck-cpu-held-runtime-outcome-v2',version=2,allocation_id=2)
    with pytest.raises(ValueError):m.outcome(old,config,'a'*64)


def test_real_authored03_audit_binds_new_policy_capsule_and_retains_both_failures(tmp_path):
    from test_puck_cpu_held_amendment03 import amendment03_fixture
    from test_puck_cpu_held_parent_integration import run_cli
    m=api()
    with amendment03_fixture(tmp_path) as case:
        root,parent,config,stage=(case[k] for k in ('root','api','config','stage'))
        for epoch in ('01','02'):
            prior=json.loads((root/('runs/puck-cpu-held-qualification-'+epoch+'/result.json')).read_bytes())
            assert prior['status']=='FAIL' and prior['held_four_imports_observed'] is False
        code,stdout,stderr=run_cli(root,parent,'qualify03',config)
        assert code==0,(code,stdout,stderr)
        output=root/'runs/puck-cpu-held-qualification-03'
        terminal=(output/'result.json').read_bytes()
        assert stdout==terminal and json.loads(terminal)['status']=='imports_completed'
        path=root/'authored-qualify03-configuration.json';transport=root/'authored-qualify03-transport.json'
        configsha=m.sha(path.read_bytes());transportsha=m.sha(transport.read_bytes())
        def observe():
            before=len(os.listdir('/proc/self/fd'))
            try:return m.audit(path,configsha,transport,transportsha,deadline=time.monotonic()+30)
            finally:assert len(os.listdir('/proc/self/fd'))==before
        result=observe();(root/'authored-amendment03-api-audit.json').write_bytes(m.canonical(result))
        assert (result['kind'],result['version'],result['allocation_id'],result['status'])==('puck-cpu-held-runtime-independent-audit-v3',3,3,'PASS')
        assert result['historical_source_epoch_sha256']!=result['current_source_epoch_sha256']
        assert result['evidence_scope']=='AUTHORED fixture only' and result['held_four_imports_observed'] is True
        assert result['file_count']==18 and result['root_count']==4
        assert result['auditor_source_sha256']==m.sha(Path(m.__file__).read_bytes())
        assert all(result[k]==value for k,value in m.CLAIMS.items())
        worker=json.loads((output/'logs/stdout.log').read_bytes())
        assert worker['expected_missing_imports']==['org','torch._rocm_init']
        failures=[]
        capsule=output/'worker-source'/m.BOOTSTRAP;original=capsule.read_bytes()
        capsule.write_bytes(original+b'\n# authored capsule tampering\n')
        try:
            with pytest.raises(ValueError,match='(?i)(pin|hash|SHA)') as error:observe()
            failures.append(dict(case='fresh03-worker-capsule',error=str(error.value)))
        finally:capsule.write_bytes(original)
        original=transport.read_bytes();value=json.loads(original);value['observed_returncode']=1
        transport.write_bytes(m.canonical(value));transportsha=m.sha(transport.read_bytes())
        try:
            with pytest.raises(ValueError,match='Normal external transport exit required') as error:observe()
            failures.append(dict(case='nonzero-transport',error=str(error.value)))
        finally:transport.write_bytes(original);transportsha=m.sha(original)
        (root/'authored-amendment03-audit-refusals.json').write_bytes(m.canonical(dict(authored=True,cases=failures)))
        script=Path(m.__file__);published=root/'authored-amendment03-audit-cli.json'
        command=[m.PYTHON,'-I','-S','-B',str(script),'--configuration',str(path),'--sha256',configsha,
            '--transport',str(transport),'--transport-sha256',transportsha,'--output',str(published)]
        started=time.monotonic();process=subprocess.run(command,capture_output=True,timeout=30)
        receipt=dict(kind='authored-amendment03-audit-cli-observation-v1',authored_scope='AUTHORED fixture only',
            command=command,observed_returncode=process.returncode,elapsed_seconds=time.monotonic()-started)
        for name,raw in (('stdout',process.stdout),('stderr',process.stderr)):
            channel=root/('authored-amendment03-audit-cli.'+name);channel.write_bytes(raw)
            receipt[name]=dict(path=str(channel.relative_to(root)),size_bytes=len(raw),sha256=m.sha(raw))
        (root/'authored-amendment03-audit-cli-external.json').write_bytes(m.canonical(receipt))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        cli=json.loads(process.stdout)
        assert (cli['kind'],cli['version'],cli['allocation_id'],cli['status'])==('puck-cpu-held-runtime-independent-audit-v3',3,3,'PASS')
        assert cli['auditor_source_sha256']==m.sha(script.read_bytes())
        assert cli['closure']==dict(active_children=[],active_non_main_threads=[],fd_count_before=4,fd_count_after=4)
        repeat=subprocess.run(command,capture_output=True,timeout=30)
        assert repeat.returncode!=0 and published.read_bytes()==process.stdout
        code,_,error=run_cli(root,parent,'qualify03-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in error and (output/'result.json').read_bytes()==terminal
        for relative,raw in case['legacy_bytes'].items():assert (root/relative).read_bytes()==raw
    assert not stage.exists()
