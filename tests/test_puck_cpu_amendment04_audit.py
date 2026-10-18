"""Qualification04 admits only the reviewed diagnostic source transition."""
import copy
import json
import os
from pathlib import Path
import subprocess
import time

import pytest

from test_puck_cpu_held_runtime_audit import api
from test_puck_cpu_amendment_audit import configuration as configuration02, historical, acceptance_files
from test_puck_cpu_amendment03_audit import configuration03


BINDINGS='src/palimpsest/puck_dependency_bindings.py'


def configuration04(m,authored=True):
    value=configuration03(m,authored)
    value.update(kind='puck-cpu-held-runtime-allocation-v4',version=4,allocation_id=4)
    next(r for r in value['sources'] if r['path']==BINDINGS)['sha256']='d'*64
    return value


def epoch04(m):
    old,prep=historical(m,configuration02(m))
    return configuration04(m),old,prep


@pytest.mark.parametrize('authored',[False,True])
def test04_closed_identity_reaches_only_its_fresh_output(authored):
    m=api();value=configuration04(m,authored);m.configuration(value,authored)
    assert m.allocation_output(value)=='runs/puck-cpu-held-qualification-04'


@pytest.mark.parametrize('field,value',[('kind','puck-cpu-held-runtime-allocation-v5'),('version',3),
    ('version',True),('allocation_id',3),('allocation_id',True),('phase','prepare')])
def test04_cannot_alias_prior_or_future_allocation(field,value):
    m=api();config=configuration04(m);config[field]=value
    with pytest.raises(ValueError):m.configuration(config,True)


@pytest.mark.parametrize('parent_changes',[False,True])
def test04_requires_bootstrap_and_binding_delta_with_optional_parent(parent_changes):
    m=api();current,old,prep=epoch04(m)
    if not parent_changes:
        next(r for r in current['sources'] if r['path']==m.PARENT).update(next(r for r in old['sources'] if r['path']==m.PARENT))
    m.preparation_epoch(current,old,prep)


@pytest.mark.parametrize('defect',['bindings-unchanged','bootstrap-unchanged','foreign-source','input',
    'environment','negative','old-negative','old-source'])
def test04_source_transition_keeps_all_other_data_and_policy_exact(defect):
    m=api();current,old,prep=epoch04(m)
    if defect in ('bindings-unchanged','bootstrap-unchanged'):
        path=BINDINGS if defect=='bindings-unchanged' else m.BOOTSTRAP
        next(r for r in current['sources'] if r['path']==path).update(next(r for r in old['sources'] if r['path']==path))
    elif defect=='foreign-source':next(r for r in current['sources'] if r['path'].endswith('puck_dependency_imports.py'))['sha256']='0'*64
    elif defect=='input':current['inputs']['candidate']['sha256']='0'*64
    elif defect=='environment':current['environment']['CUDA_VISIBLE_DEVICES']='0'
    elif defect=='negative':current['negative_imports'].append('guessed_optional')
    elif defect=='old-negative':old['negative_imports'].append('torch._rocm_init')
    else:prep['sources'][0]['sha256']='0'*64
    with pytest.raises(ValueError):m.preparation_epoch(current,old,prep)


@pytest.mark.parametrize('version',[2,3])
def test_legacy_amendment_epochs_still_refuse_diagnostic_binding_delta(version):
    m=api();current,old,prep=epoch04(m)
    current.update(kind='puck-cpu-held-runtime-allocation-v'+str(version),version=version,allocation_id=version)
    if version<3:current['negative_imports']=['org']
    m.configuration(current,True)
    with pytest.raises(ValueError):m.preparation_epoch(current,old,prep)


@pytest.mark.parametrize('defect',['missing-name','extra-name','limit'])
def test04_keeps03_roster_and_resource_bounds(defect):
    m=api();current=configuration04(m)
    if defect=='missing-name':current['negative_imports']=['org']
    elif defect=='extra-name':current['negative_imports'].append('torch._other_optional')
    else:current['limits']['rss_bytes']+=1
    with pytest.raises(ValueError):m.configuration(current,True)


def test04_historical_acceptance_retains_the_original_auditor_and_capsule_epoch(tmp_path):
    m=api();current=acceptance_files(m,tmp_path)
    current.update(kind='puck-cpu-held-runtime-allocation-v4',version=4,allocation_id=4,
        negative_imports=['org','torch._rocm_init'])
    next(r for r in current['sources'] if r['path']==BINDINGS)['sha256']='d'*64
    before=len(os.listdir('/proc/self/fd'));held=m.Held(time.monotonic()+10)
    try:
        old,prepared,audit=m.historical_acceptance(held,current,True)
        assert old['negative_imports']==['org'] and prepared['sources']==old['sources']!=current['sources']
        assert audit['auditor_source_sha256']=='19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9'
    finally:held.close()
    assert len(os.listdir('/proc/self/fd'))==before


def test04_success_cannot_reuse03_outcome_identity():
    m=api();config=configuration04(m)
    value=dict(m.CLAIMS,kind='puck-cpu-held-runtime-outcome-v4',version=4,phase='qualify',allocation_id=4,
        configuration_sha256='a'*64,status='imports_completed',held_four_imports_observed=True,elapsed_seconds=1.0,
        closure=dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5))
    m.outcome(value,config,'a'*64)
    old=copy.deepcopy(value);old.update(kind='puck-cpu-held-runtime-outcome-v3',version=3,allocation_id=3)
    with pytest.raises(ValueError):m.outcome(old,config,'a'*64)


@pytest.mark.runs_basetemp  # asserts a persistent basetemp under runs/ (see docs/testing.md)
def test_real_authored04_independent_audits_fresh_bindings_and_preserves_history(tmp_path):
    from test_puck_cpu_held_amendment04_integration import amendment04_fixture
    from test_puck_cpu_held_parent_integration import run_cli
    m=api()
    with amendment04_fixture(tmp_path) as case:
        root,parent,config,stage=(case[k] for k in ('root','api','config','stage'))
        code,stdout,stderr=run_cli(root,parent,'qualify04',config)
        assert code==0,(code,stdout,stderr)
        output=root/'runs/puck-cpu-held-qualification-04';terminal=(output/'result.json').read_bytes()
        assert stdout==terminal and json.loads(terminal)['status']=='imports_completed'
        path=root/'authored-qualify04-configuration.json';transport=root/'authored-qualify04-transport.json'
        configsha=m.sha(path.read_bytes())
        def observe(transport_path=transport):
            before=len(os.listdir('/proc/self/fd'))
            try:return m.audit(path,configsha,transport_path,m.sha(transport_path.read_bytes()),deadline=time.monotonic()+30)
            finally:assert len(os.listdir('/proc/self/fd'))==before
        result=observe();(root/'authored-amendment04-api-audit.json').write_bytes(m.canonical(result))
        assert (result['kind'],result['version'],result['allocation_id'],result['status'])==('puck-cpu-held-runtime-independent-audit-v4',4,4,'PASS')
        assert result['historical_source_epoch_sha256']!=result['current_source_epoch_sha256']
        assert result['evidence_scope']=='AUTHORED fixture only' and result['held_four_imports_observed'] is True
        assert result['root_count']==4 and result['file_count']==18
        assert result['auditor_source_sha256']==m.sha(Path(m.__file__).read_bytes())
        assert all(result[k]==v for k,v in m.CLAIMS.items())
        failures=[]
        for source in (m.BOOTSTRAP,BINDINGS):
            capsule=output/'worker-source'/source;original=capsule.read_bytes()
            capsule.write_bytes(original+b'\n# authored fresh04 capsule tampering\n')
            try:
                with pytest.raises(ValueError,match='(?i)(pin|hash|SHA)') as error:observe()
                failures.append(dict(case='fresh04-capsule',source=source,error=str(error.value)))
            finally:capsule.write_bytes(original)
        value=json.loads(transport.read_bytes());value['observed_returncode']=1
        failed_transport=root/'authored-amendment04-nonzero-transport.json';failed_transport.write_bytes(m.canonical(value))
        with pytest.raises(ValueError,match='Normal external transport exit required') as error:observe(failed_transport)
        failures.append(dict(case='nonzero-transport',error=str(error.value)))
        (root/'authored-amendment04-audit-refusals.json').write_bytes(m.canonical(dict(authored=True,cases=failures)))
        script=Path(m.__file__)
        def run_auditor(label,transport_path,published):
            command=[m.PYTHON,'-I','-S','-B',str(script),'--configuration',str(path),'--sha256',configsha,
                '--transport',str(transport_path),'--transport-sha256',m.sha(transport_path.read_bytes()),'--output',str(published)]
            started=time.monotonic();process=subprocess.run(command,capture_output=True,timeout=30)
            receipt=dict(kind='authored-amendment04-audit-cli-observation-v1',authored_scope='AUTHORED fixture only',
                command=command,observed_returncode=process.returncode,elapsed_seconds=time.monotonic()-started)
            for name,raw in (('stdout',process.stdout),('stderr',process.stderr)):
                channel=root/('authored-amendment04-'+label+'.'+name);channel.write_bytes(raw)
                receipt[name]=dict(path=str(channel.relative_to(root)),size_bytes=len(raw),sha256=m.sha(raw))
            (root/('authored-amendment04-'+label+'-external.json')).write_bytes(m.canonical(receipt))
            return process
        published=root/'authored-amendment04-audit-cli.json'
        process=run_auditor('audit-cli',transport,published)
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        cli=json.loads(process.stdout)
        assert (cli['kind'],cli['version'],cli['allocation_id'],cli['status'])==('puck-cpu-held-runtime-independent-audit-v4',4,4,'PASS')
        assert cli['auditor_source_sha256']==m.sha(script.read_bytes())
        assert cli['closure']==dict(active_children=[],active_non_main_threads=[],fd_count_before=4,fd_count_after=4)
        repeat=run_auditor('audit-cli-repeat-refusal',transport,published)
        assert repeat.returncode!=0 and published.read_bytes()==process.stdout
        rejected=root/'authored-amendment04-nonzero-audit-cli.json'
        failed=run_auditor('nonzero-audit-cli',failed_transport,rejected)
        assert failed.returncode==1 and failed.stdout==rejected.read_bytes() and failed.stderr==b''
        failure=json.loads(failed.stdout)
        assert failure['kind']=='puck-cpu-held-runtime-independent-audit-v1' and failure['status']=='FAIL'
        assert failure['error']=='Normal external transport exit required'
        assert all(failure[k]==v for k,v in m.CLAIMS.items())
        code,_,error=run_cli(root,parent,'qualify04-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in error and (output/'result.json').read_bytes()==terminal
        for relative,raw in case['legacy_bytes'].items():assert (root/relative).read_bytes()==raw
    assert not stage.exists()
