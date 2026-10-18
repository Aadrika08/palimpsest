"""Independent qualification02 schema/custody checks on authored inputs only."""
import copy
import json
import os
import subprocess
import time
from pathlib import Path

import pytest

from test_puck_cpu_held_runtime_audit import api


def configuration(m):
    row=lambda path:dict(path=path,size_bytes=1,sha256='a'*64)
    return dict(kind='puck-cpu-held-runtime-allocation-v2',version=2,phase='qualify',allocation_id=2,
        root='/authored',stage_parent='/tmp/palimpsest-puck-cpu-held-authored-schema',
        sources=[row(p) for p in m.SOURCES],inputs={k:row('inputs/'+k+'.json') for k in m.ROLES},
        interpreter=dict(m.INTERPRETER),environment=dict(m.ENVIRONMENT),expected_versions=dict(m.VERSIONS),
        limits=m.limits('qualify',True),negative_imports=['org'],claims=copy.deepcopy(m.CLAIMS),
        preparation_acceptance=dict(configuration=row('authored-prepare-configuration.json'),
            result=row(m.OUTPUTS['prepare']+'/result.json'),independent_audit=row('archive/preparation-audit.json'),
            externally_observed_auditor_cli=row('archive/preparation-audit-cli.json')))


def historical(m,current):
    old=copy.deepcopy(current);old.update(kind='puck-cpu-held-runtime-allocation-v1',version=1,phase='prepare',
        allocation_id=1,limits=m.limits('prepare',True));old.pop('preparation_acceptance')
    for row in old['sources']:
        if row['path'] in (m.PARENT,m.BOOTSTRAP):row['sha256']='b'*64
    prep=dict(m.CLAIMS,kind='puck-cpu-held-runtime-outcome-v1',version=1,phase='prepare',allocation_id=1,
        configuration_sha256='c'*64,status='prepared',held_four_imports_observed=False,stage_parent=old['stage_parent'],
        sources=copy.deepcopy(old['sources']),inputs=copy.deepcopy(old['inputs']))
    return old,prep


def test_v2_is_a_closed_qualification_only_configuration():
    m=api();value=configuration(m);m.configuration(value,True)


@pytest.mark.parametrize('field,value',[('kind','puck-cpu-held-runtime-allocation-v1'),('version',True),
    ('allocation_id',1),('allocation_id',True),('phase','prepare')])
def test_v2_aliases_and_wrong_allocation_refuse(field,value):
    m=api();config=configuration(m);config[field]=value
    with pytest.raises(ValueError):m.configuration(config,True)


@pytest.mark.parametrize('role',['configuration','result','independent_audit','externally_observed_auditor_cli'])
def test_v2_requires_each_historical_acceptance_pin(role):
    m=api();config=configuration(m);del config['preparation_acceptance'][role]
    with pytest.raises(ValueError):m.configuration(config,True)


def test_historical_source_epoch_is_distinct_but_data_stays_exact():
    m=api();current=configuration(m);old,prep=historical(m,current)
    m.preparation_epoch(current,old,prep)


@pytest.mark.parametrize('defect',['bootstrap-unchanged','foreign-source','input','environment','negative','stage','old-source'])
def test_source_amendment_cannot_inherit_changed_data_or_foreign_source(defect):
    m=api();current=configuration(m);old,prep=historical(m,current)
    if defect=='bootstrap-unchanged':
        next(r for r in current['sources'] if r['path']==m.BOOTSTRAP)['sha256']='b'*64
    elif defect=='foreign-source':
        next(r for r in current['sources'] if r['path']=='src/palimpsest/puck_runtime_qualification.py')['sha256']='d'*64
    elif defect=='old-source':prep['sources'][0]['sha256']='d'*64
    elif defect=='input':current['inputs']['candidate']['sha256']='d'*64
    elif defect=='environment':current['environment']['CUDA_VISIBLE_DEVICES']='0'
    elif defect=='negative':current['negative_imports'].append('guessed_optional')
    else:current['stage_parent']+='-other'
    with pytest.raises(ValueError):m.preparation_epoch(current,old,prep)


def acceptance_files(m,tmp_path,defect=None):
    current=configuration(m);current['root']=str(tmp_path)
    old,prep=historical(m,current);oldraw=m.canonical(old)
    prep.update(configuration_sha256=m.sha(oldraw),elapsed_seconds=1.0,
        dependencies=dict(path='payload/dependencies.json',size_bytes=2,sha256='d'*64),
        closure=dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5))
    prepraw=m.canonical(prep)
    receipt=dict(m.CLAIMS,kind='puck-cpu-held-runtime-independent-audit-v1',version=1,status='PASS',
        phase='prepare',observed_status='prepared',held_four_imports_observed=False,
        auditor_source_sha256=m.HISTORICAL_AUDITOR_SHA256,configuration_sha256=m.sha(oldraw),
        result_sha256=m.sha(prepraw),dependencies_sha256='d'*64,external_returncode=0,
        evidence_scope='AUTHORED fixture only',elapsed_seconds=1.0,root_count=4,transport_sha256='e'*64,
        closure=dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[]))
    if defect=='audit-source':receipt['auditor_source_sha256']='0'*64
    if defect=='audit-authority':receipt['runtime_qualified']=True
    if defect=='audit-result':receipt['result_sha256']='0'*64
    if defect=='audit-dependency':receipt['dependencies_sha256']='0'*64
    if defect=='audit-exit':receipt['external_returncode']=False
    if defect=='audit-closure':receipt['closure']['active_children']=[123]
    if defect=='audit-error':receipt['error_type']='OSError'
    araw=m.canonical(receipt);published=dict(path='/historical/audit.json',size_bytes=len(araw),sha256=m.sha(araw))
    cli=dict(kind='externally-observed-cpu-auditor-cli-v1',observed_returncode=0,elapsed_seconds=1.0,
        at='2026-10-15T14:11:55.277125+00:00',scope='fresh read-only current-byte audit of prepared data; no preparation or qualification allocation invoked',
        command=[m.PYTHON,'-I','-S','-B',str(tmp_path/'scripts/audit_puck_cpu_held_runtime.py'),
            '--configuration',str(tmp_path/current['preparation_acceptance']['configuration']['path']),
            '--sha256',m.sha(oldraw),'--transport',str(tmp_path/'authored-prepare-transport.json'),
            '--transport-sha256','e'*64,'--output',published['path']],published=published,
        stdout=dict(published,path='/historical/audit.stdout'),
        stderr=dict(path='/historical/audit.stderr',size_bytes=0,sha256=m.sha(b'')))
    if defect=='cli-unknown':cli['acceptance_override']=True
    if defect=='cli-metadata-type':cli['scope']=False
    if defect=='cli-exit':cli['observed_returncode']=False
    if defect=='cli-command':cli['command'][6]=str(tmp_path/'runs/puck-cpu-held-preparation-01/configuration.json')
    if defect=='cli-stdout':cli['stdout']['sha256']='0'*64
    if defect=='cli-stderr':cli['stderr']['size_bytes']=1
    blobs=dict(configuration=oldraw,result=prepraw,independent_audit=araw,
        externally_observed_auditor_cli=m.canonical(cli))
    for role,raw in blobs.items():
        pin=current['preparation_acceptance'][role];pin.update(size_bytes=len(raw),sha256=m.sha(raw))
        path=tmp_path/pin['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    return current


def test_historical_cli_labels_bind_relative_bytes_without_reopening_absolute_paths(tmp_path):
    m=api();current=acceptance_files(m,tmp_path);held=m.Held(time.monotonic()+10)
    try:
        old,prep,receipt=m.historical_acceptance(held,current,True)
        assert prep['sources']==old['sources']!=current['sources']
        assert receipt['auditor_source_sha256']==m.HISTORICAL_AUDITOR_SHA256
        held.recheck()
    finally:held.close()


@pytest.mark.parametrize('defect',['audit-source','audit-authority','audit-result','audit-dependency',
    'audit-exit','audit-closure','audit-error','cli-unknown','cli-metadata-type','cli-exit','cli-command','cli-stdout','cli-stderr'])
def test_reauthenticated_historical_receipt_tampering_still_refuses(tmp_path,defect):
    m=api();current=acceptance_files(m,tmp_path,defect);held=m.Held(time.monotonic()+10)
    try:
        with pytest.raises(ValueError):m.historical_acceptance(held,current,True)
    finally:held.close()


def test_real_authored02_has_independent_current_epoch_audit_and_exclusive_cli(tmp_path):
    from test_puck_cpu_held_amendment import amendment_fixture
    from test_puck_cpu_held_parent_integration import run_cli
    m=api()
    with amendment_fixture(tmp_path) as case:
        root,parent,config,stage=(case[k] for k in ('root','api','config','stage'))
        code,stdout,stderr=run_cli(root,parent,'qualify02',config)
        assert code==0,(code,stdout,stderr)
        path=root/'authored-qualify02-configuration.json';transport=root/'authored-qualify02-transport.json'
        configsha=m.sha(path.read_bytes());transportsha=m.sha(transport.read_bytes())
        def observe():
            before=len(os.listdir('/proc/self/fd'))
            try:return m.audit(path,configsha,transport,transportsha,deadline=time.monotonic()+30)
            finally:assert len(os.listdir('/proc/self/fd'))==before
        result=observe();(root/'authored-amendment-api-audit.json').write_bytes(m.canonical(result))
        assert (result['kind'],result['version'],result['allocation_id'],result['status'])==('puck-cpu-held-runtime-independent-audit-v2',2,2,'PASS')
        assert result['historical_source_epoch_sha256']!=result['current_source_epoch_sha256']
        assert result['evidence_scope']=='AUTHORED fixture only' and result['held_four_imports_observed'] is True
        assert result['file_count']==18 and result['root_count']==4
        assert result['auditor_source_sha256']==m.sha(Path(m.__file__).read_bytes())
        assert all(result[k]==value for k,value in m.CLAIMS.items())
        failures=[]
        capsule=root/'runs/puck-cpu-held-qualification-02/worker-source'/m.BOOTSTRAP
        original=capsule.read_bytes();capsule.write_bytes(original+b'\n# reauthenticated source cannot replace this capsule\n')
        try:
            with pytest.raises(ValueError,match='(?i)(pin|hash|SHA)') as error:observe()
            failures.append(dict(case='fresh-worker-capsule',error=str(error.value)))
        finally:capsule.write_bytes(original)
        original=transport.read_bytes();value=json.loads(original);value['observed_returncode']=1;transport.write_bytes(m.canonical(value))
        transportsha=m.sha(transport.read_bytes())
        try:
            with pytest.raises(ValueError,match='Normal external transport exit required') as error:observe()
            failures.append(dict(case='nonzero-transport',error=str(error.value)))
        finally:transport.write_bytes(original);transportsha=m.sha(original)
        (root/'authored-amendment-audit-refusals.json').write_bytes(m.canonical(dict(authored=True,cases=failures)))
        script=Path(m.__file__);output=root/'authored-amendment-audit-cli.json'
        command=[m.PYTHON,'-I','-S','-B',str(script),'--configuration',str(path),'--sha256',configsha,
            '--transport',str(transport),'--transport-sha256',transportsha,'--output',str(output)]
        started=time.monotonic();process=subprocess.run(command,capture_output=True,timeout=30)
        elapsed=time.monotonic()-started
        receipt=dict(kind='authored-amendment-audit-cli-observation-v1',authored_scope='AUTHORED fixture only',
            command=command,observed_returncode=process.returncode,elapsed_seconds=elapsed)
        for name,raw in (('stdout',process.stdout),('stderr',process.stderr)):
            channel=root/('authored-amendment-audit-cli.'+name);channel.write_bytes(raw)
            receipt[name]=dict(path=str(channel.relative_to(root)),size_bytes=len(raw),sha256=m.sha(raw))
        (root/'authored-amendment-audit-cli-external.json').write_bytes(m.canonical(receipt))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==output.read_bytes() and process.stderr==b''
        cli=json.loads(process.stdout);assert cli['status']=='PASS' and cli['auditor_source_sha256']==m.sha(script.read_bytes())
        assert cli['closure']==dict(active_children=[],active_non_main_threads=[],fd_count_before=4,fd_count_after=4)
        repeat=subprocess.run(command,capture_output=True,timeout=30)
        assert repeat.returncode!=0 and output.read_bytes()==process.stdout
        for relative,raw in case['legacy_bytes'].items():assert (root/relative).read_bytes()==raw
    assert not stage.exists()
