"""Qualification02 source epochs, using authored data and retained v1 proofs only."""
import copy
import json
from pathlib import Path

import pytest

from test_puck_cpu_held_parent import api


PARENT='scripts/qualify_puck_cpu_held_runtime.py'
LEGACY_AUDITOR_SHA='19723b4ec19c6cd8fd29d38b5cbabab60f89c136ee37564f6e94175439b4eed9'
EMPTY_SHA='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'


def acceptance_case():
    m=api()
    sources=[dict(path=p,size_bytes=1,sha256='a'*64) for p in m.SOURCES]
    inputs={role:dict(path='docs/authored-'+role+'.json',size_bytes=1,sha256='b'*64) for role in m.INPUT_ROLES}
    historical=m.configuration_template(phase='prepare',root=str(m.ROOT),
        stage_parent='/tmp/palimpsest-puck-cpu-held-authored',sources=sources,inputs=inputs,negative_imports=['org'])
    historical_raw=m.canonical(historical)
    preparation=dict(m.CLAIMS,kind='puck-cpu-held-runtime-outcome-v1',version=1,allocation_id=1,phase='prepare',
        status='prepared',held_four_imports_observed=False,configuration_sha256=m.digest(historical_raw),
        stage_parent=historical['stage_parent'],sources=copy.deepcopy(sources),inputs=copy.deepcopy(inputs),
        dependencies=dict(path='payload/dependencies.json',size_bytes=2,sha256='d'*64),
        staged_roots=[dict(root_index=i,device=1,inode=i+2) for i in range(4)],
        elapsed_seconds=1.0,closure=dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5))
    prepared_raw=m.canonical(preparation)
    audit=dict(m.CLAIMS,kind='puck-cpu-held-runtime-independent-audit-v1',version=1,status='PASS',phase='prepare',
        observed_status='prepared',held_four_imports_observed=False,external_returncode=0,
        auditor_source_sha256=LEGACY_AUDITOR_SHA,configuration_sha256=m.digest(historical_raw),
        result_sha256=m.digest(prepared_raw),dependencies_sha256='d'*64,transport_sha256='e'*64,
        evidence_scope='ordinary CPU held allocation only',
        root_count=4,file_count=18,input_bytes=100,elapsed_seconds=1.0,configured_process_limit=3,
        closure=dict(active_children=[],active_non_main_threads=[],fd_count_before=4,fd_count_after=4))
    audit_raw=m.canonical(audit)
    config_pin=dict(path='authored-prepare-configuration.json',size_bytes=len(historical_raw),sha256=m.digest(historical_raw))
    published=dict(path=str(m.ROOT/'authored-old-audit.json'),size_bytes=len(audit_raw),sha256=m.digest(audit_raw))
    cli=dict(kind='externally-observed-cpu-auditor-cli-v1',observed_returncode=0,elapsed_seconds=1.0,
        command=[m.PYTHON,'-I','-S','-B',str(m.ROOT/'scripts/audit_puck_cpu_held_runtime.py'),
            '--configuration',str(m.ROOT/config_pin['path']),'--sha256',config_pin['sha256'],
            '--transport',str(m.ROOT/'authored-prepare-transport.json'),'--transport-sha256','e'*64,
            '--output',published['path']],published=published,stdout=dict(published,path=str(m.ROOT/'authored-old-audit.stdout')),
        stderr=dict(path=str(m.ROOT/'authored-old-audit.stderr'),size_bytes=0,sha256=EMPTY_SHA))
    blobs=dict(configuration=historical_raw,result=prepared_raw,independent_audit=audit_raw,externally_observed_auditor_cli=m.canonical(cli))
    paths=dict(configuration=config_pin['path'],result='runs/puck-cpu-held-preparation-01/result.json',
        independent_audit='docs/authored-old-audit.json',externally_observed_auditor_cli='docs/authored-old-audit-cli.json')
    current=copy.deepcopy(historical)
    current.update(kind='puck-cpu-held-runtime-allocation-v2',version=2,phase='qualify',allocation_id=2,
        limits=copy.deepcopy(m.LIMITS['qualify']),preparation_acceptance={k:dict(path=paths[k],size_bytes=len(v),sha256=m.digest(v)) for k,v in blobs.items()})
    for row in current['sources']:
        if row['path']==m.BOOTSTRAP:row['sha256']='c'*64
        if row['path']==PARENT:row['sha256']='f'*64
    return m,current,blobs


def rebind(m,config,blobs,role,value):
    blobs[role]=m.canonical(value)
    config['preparation_acceptance'][role].update(size_bytes=len(blobs[role]),sha256=m.digest(blobs[role]))
    if role=='result':
        audit=json.loads(blobs['independent_audit']);audit['result_sha256']=m.digest(blobs[role])
        rebind(m,config,blobs,'independent_audit',audit)
    elif role=='independent_audit':
        cli=json.loads(blobs['externally_observed_auditor_cli'])
        for channel in ('published','stdout'):
            cli[channel].update(size_bytes=len(blobs[role]),sha256=m.digest(blobs[role]))
        cli['command'][12]=value['transport_sha256']
        rebind(m,config,blobs,'externally_observed_auditor_cli',cli)


def test_qualification02_accepts_separate_historical_and_current_source_epochs():
    m,config,blobs=acceptance_case()
    m.validate_configuration(config)
    historical,prepared=m.validate_preparation_acceptance(config,blobs)
    assert prepared['sources']==historical['sources']
    assert prepared['sources']!=config['sources']
    assert m.allocation_output(config)=='runs/puck-cpu-held-qualification-02'


def test_historical_cli_accepts_exact_retained_current_byte_audit_metadata():
    m,config,blobs=acceptance_case()
    retained=m.ROOT/'docs/reports/puck-cpu-held-qualification-amendment-02/current-byte-audit-02/palimpsest-puck-cpu-held-preparation-01-current-byte-audit-02.external-cli.json'
    recorded=json.loads(retained.read_bytes())
    cli=json.loads(blobs['externally_observed_auditor_cli'])
    cli.update({k:recorded[k] for k in ('at','scope')})
    rebind(m,config,blobs,'externally_observed_auditor_cli',cli)
    m.validate_preparation_acceptance(config,blobs)


@pytest.mark.parametrize('role',['result','independent_audit'])
@pytest.mark.parametrize('key',['error','error_type'])
def test_successful_receipt_with_rebound_error_fields_is_refused(role,key):
    m,config,blobs=acceptance_case()
    value=json.loads(blobs[role]);value[key]='contradictory failure'
    rebind(m,config,blobs,role,value)
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)


@pytest.mark.parametrize('defect',['kind','version','bool-id','id','phase','missing-role','absolute-role','result-path','unknown'])
def test_qualification02_has_one_closed_schema_and_output_epoch(defect):
    m,config,_=acceptance_case()
    if defect=='kind':config['kind']='puck-cpu-held-runtime-allocation-v3'
    elif defect=='version':config['version']=1
    elif defect=='bool-id':config['allocation_id']=True
    elif defect=='id':config['allocation_id']=3
    elif defect=='phase':config['phase']='prepare';config['limits']=copy.deepcopy(m.LIMITS['prepare'])
    elif defect=='missing-role':config['preparation_acceptance'].pop('independent_audit')
    elif defect=='absolute-role':config['preparation_acceptance']['independent_audit']['path']='/tmp/audit.json'
    elif defect=='result-path':config['preparation_acceptance']['result']['path']='runs/other/result.json'
    else:config['output']='runs/overwrite01'
    with pytest.raises(ValueError):m.validate_configuration(config)


@pytest.mark.parametrize('defect',['no-bootstrap-change','foreign-source','input','roster','stage','historical-source','audit-failed',
    'audit-authority','audit-source','audit-result','audit-dependency','audit-exit','audit-scope','audit-closure','audit-transport',
    'cli-exit','cli-bool-exit','cli-stdout','cli-stderr','cli-command','noncanonical'])
def test_amendment_rejects_rebound_semantic_tampering(defect):
    m,config,blobs=acceptance_case()
    historical=json.loads(blobs['configuration']);prepared=json.loads(blobs['result'])
    audit=json.loads(blobs['independent_audit']);cli=json.loads(blobs['externally_observed_auditor_cli'])
    if defect=='no-bootstrap-change':next(r for r in config['sources'] if r['path']==m.BOOTSTRAP)['sha256']='a'*64
    elif defect=='foreign-source':next(r for r in config['sources'] if r['path'].endswith('puck_dependency_imports.py'))['sha256']='f'*64
    elif defect=='input':config['inputs']['candidate']['sha256']='0'*64
    elif defect=='roster':config['negative_imports']=['missing','org']
    elif defect=='stage':config['stage_parent']='/tmp/palimpsest-puck-cpu-held-other'
    elif defect=='historical-source':prepared['sources'][0]['sha256']='0'*64;rebind(m,config,blobs,'result',prepared)
    elif defect.startswith('audit-'):
        key,value={'audit-failed':('status','FAIL'),'audit-authority':('runtime_qualified',True),
            'audit-source':('auditor_source_sha256','0'*64),'audit-result':('result_sha256','0'*64),
            'audit-dependency':('dependencies_sha256','0'*64),'audit-exit':('external_returncode',1),
            'audit-scope':('evidence_scope','unrelated'),'audit-closure':('closure',dict(active_children=[],active_non_main_threads=[],fd_count_before=0,fd_count_after=0)),
            'audit-transport':('transport_sha256','not-a-sha')}[defect]
        audit[key]=value;rebind(m,config,blobs,'independent_audit',audit)
    elif defect.startswith('cli-'):
        if defect=='cli-exit':cli['observed_returncode']=1
        elif defect=='cli-bool-exit':cli['observed_returncode']=False
        elif defect=='cli-stdout':cli['stdout']['sha256']='0'*64
        elif defect=='cli-stderr':cli['stderr']['size_bytes']=1
        else:cli['command'][4]='/unrelated/auditor.py'
        rebind(m,config,blobs,'externally_observed_auditor_cli',cli)
    else:
        blobs['configuration']=json.dumps(historical,indent=2).encode()
        config['preparation_acceptance']['configuration'].update(size_bytes=len(blobs['configuration']),sha256=m.digest(blobs['configuration']))
    with pytest.raises(ValueError):m.validate_preparation_acceptance(config,blobs)


# Shared with the independent audit lane. This executes only tiny authored
# modules, retaining a real legacy audit CLI before any amendment02 invocation.
from contextlib import contextmanager
import os
import secrets
import shutil
import subprocess
import time

from test_puck_cpu_held_parent_integration import ROOT, canonical, digest, load, project, run_cli


@contextmanager
def amendment_fixture(tmp_path,*,rocm_probe=False,historical_bindings=False,binding_failure=False):
    assert tmp_path.resolve().is_relative_to((ROOT/'runs').resolve()), 'Use persistent runs/ basetemp'
    root,current,inputs,_=project(tmp_path,rocm_probe=rocm_probe,binding_failure=binding_failure)
    legacy=ROOT/'docs/reports/puck-cpu-held-preparation-01'
    archived_auditor=legacy/'controls/scripts/audit_puck_cpu_held_runtime.py'
    archived_raw=archived_auditor.read_bytes()
    assert digest(archived_raw)==LEGACY_AUDITOR_SHA
    (root/'scripts/audit_puck_cpu_held_runtime.py').write_bytes(archived_raw)
    bootstrap=root/current.BOOTSTRAP
    fresh_bootstrap=bootstrap.read_bytes()
    old_bootstrap=(legacy/'raw/worker-source'/current.BOOTSTRAP).read_bytes()
    assert old_bootstrap!=fresh_bootstrap
    bootstrap.write_bytes(old_bootstrap)
    bindings=root/'src/palimpsest/puck_dependency_bindings.py'
    fresh_bindings=bindings.read_bytes()
    if historical_bindings:
        old_bindings=(legacy/'raw/worker-source/src/palimpsest/puck_dependency_bindings.py').read_bytes()
        assert old_bindings!=fresh_bindings
        bindings.write_bytes(old_bindings)
    sources=lambda:[dict(path=name,size_bytes=(root/name).stat().st_size,sha256=digest((root/name).read_bytes())) for name in current.SOURCES]
    stage=Path('/tmp')/('palimpsest-puck-cpu-held-authored-amendment-'+secrets.token_hex(12))
    assert not stage.exists()
    try:
        prepare=current.configuration_template(phase='prepare',root=str(root),stage_parent=str(stage),
            sources=sources(),inputs=inputs,negative_imports=['org'])
        code,stdout,stderr=run_cli(root,current,'prepare',prepare)
        assert code==0,(code,stdout,stderr)
        prepare_result=root/current.OUTPUTS['prepare']/'result.json'
        prepared_raw=prepare_result.read_bytes()
        assert json.loads(prepared_raw)['status']=='prepared'
        configuration=root/'authored-prepare-configuration.json'
        transport=root/'authored-prepare-transport.json'
        audit_output=root/'docs/authored/historical-audit.json'
        command=[current.PYTHON,'-I','-S','-B',str(root/'scripts/audit_puck_cpu_held_runtime.py'),
            '--configuration',str(configuration),'--sha256',digest(configuration.read_bytes()),
            '--transport',str(transport),'--transport-sha256',digest(transport.read_bytes()),'--output',str(audit_output)]
        started=time.monotonic()
        process=subprocess.run(command,cwd=root,env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True,timeout=30)
        elapsed=time.monotonic()-started
        channels={}
        for name,raw in (('stdout',process.stdout),('stderr',process.stderr)):
            path=root/('authored-historical-audit.'+name);path.write_bytes(raw)
            channels[name]=dict(path=str(path),size_bytes=len(raw),sha256=digest(raw))
        cli=dict(kind='externally-observed-cpu-auditor-cli-v1',command=command,observed_returncode=process.returncode,
            elapsed_seconds=elapsed,published=dict(path=str(audit_output),size_bytes=audit_output.stat().st_size,sha256=digest(audit_output.read_bytes())),**channels)
        cli_path=root/'docs/authored/historical-audit-cli.json';cli_path.write_bytes(canonical(cli))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==audit_output.read_bytes() and not process.stderr
        assert json.loads(process.stdout)['status']=='PASS'
        preparation=dict(path=str(prepare_result.relative_to(root)),size_bytes=len(prepared_raw),sha256=digest(prepared_raw))
        qualify=current.configuration_template(phase='qualify',root=str(root),stage_parent=str(stage),
            sources=sources(),inputs=inputs,negative_imports=['org'],preparation=preparation)
        code,stdout,stderr=run_cli(root,current,'qualify',qualify)
        assert code==(1 if rocm_probe else 0),(code,stdout,stderr)
        assert json.loads(stdout)['status']==('FAIL' if rocm_probe else 'imports_completed')
        if rocm_probe:
            assert not (root/current.OUTPUTS['qualify']/'baseline-after.json').exists()
            expected=(b'Dependency producer attribute binding is missing' if binding_failure else b'torch._rocm_init')
            assert expected in (root/current.OUTPUTS['qualify']/'logs/stderr.log').read_bytes()
        paths=[p for phase in ('prepare','qualify') for p in (root/current.OUTPUTS[phase]).rglob('*') if p.is_file()]
        paths += [configuration,transport,audit_output,cli_path]
        paths += list(root.glob('authored-prepare-cli.*'))+list(root.glob('authored-qualify-*'))+list(root.glob('authored-historical-audit.*'))
        legacy_bytes={str(p.relative_to(root)):p.read_bytes() for p in paths if p.is_file()}
        bootstrap.write_bytes(fresh_bootstrap)
        if historical_bindings:bindings.write_bytes(fresh_bindings)
        acceptance={role:dict(path=str(path.relative_to(root)),size_bytes=path.stat().st_size,sha256=digest(path.read_bytes()))
            for role,path in dict(configuration=configuration,result=prepare_result,independent_audit=audit_output,
                externally_observed_auditor_cli=cli_path).items()}
        config=current.configuration_template(phase='qualify',root=str(root),stage_parent=str(stage),
            sources=sources(),inputs=inputs,negative_imports=['org'],preparation_acceptance=acceptance)
        assert not (root/'runs/puck-cpu-held-qualification-02').exists()
        yield dict(root=root,api=current,config=config,stage=stage,legacy_bytes=legacy_bytes)
    finally:
        if stage.exists():
            assert stage.is_dir() and not stage.is_symlink()
            shutil.rmtree(stage)
            (root/'authored-amendment-stage-cleanup.json').write_bytes(canonical(dict(stage=str(stage),absent=not stage.exists(),actual_vendor_imports=False)))


def test_authored02_uses_fresh_capsule_preserves01_and_refuses_reentry(tmp_path):
    with amendment_fixture(tmp_path) as case:
        root,m,config,stage=(case[k] for k in ('root','api','config','stage'))
        before=[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        code,stdout,stderr=run_cli(root,m,'qualify02',config)
        output=root/'runs/puck-cpu-held-qualification-02'
        retained=(output/'result.json').read_bytes() if (output/'result.json').exists() else b''
        assert code==0,(code,stdout,stderr,retained)
        result=json.loads(retained)
        assert json.loads(stdout)==result
        assert (result['kind'],result['version'],result['allocation_id'],result['status'])==('puck-cpu-held-runtime-outcome-v2',2,2,'imports_completed')
        worker=json.loads((output/'control/worker-registration.json').read_bytes())
        assert worker['source_files']==[r for r in config['sources'] if r['path'] in m.WORKER_SOURCES]
        for row in worker['source_files']:
            raw=(output/'worker-source'/row['path']).read_bytes()
            assert len(raw)==row['size_bytes'] and digest(raw)==row['sha256']
        invocation=json.loads((output/'invocation.json').read_bytes())
        assert ['--ro-bind',str(output/'worker-source'),'/puck/source']==invocation['command'][invocation['command'].index(str(output/'worker-source'))-1:invocation['command'].index(str(output/'worker-source'))+2]
        assert before==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        for path,raw in case['legacy_bytes'].items():assert (root/path).read_bytes()==raw
        assert result['held_four_imports_observed'] is True
        assert all(result[k]==v for k,v in m.CLAIMS.items())
        assert result['closure']['active_children']==result['closure']['active_non_main_threads']==[]
        assert result['closure']['fd_count_before']==result['closure']['fd_count_after']
        code,_,stderr=run_cli(root,m,'qualify02-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert (output/'result.json').read_bytes()==retained
        for path,raw in case['legacy_bytes'].items():assert (root/path).read_bytes()==raw
