"""AUTHORED autograd transition; no installed vendor or real05 allocation."""
import copy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time

import pytest

from test_puck_cpu_held_amendment import LEGACY_AUDITOR_SHA
from test_puck_cpu_held_amendment04 import BINDINGS, PARENT
from test_puck_cpu_held_amendment05 import DELEGATES, IMPORTS, TARGET
from test_puck_cpu_held_parent_integration import (
    AUTHORED, ROOT, canonical, digest, load, project, run_cli,
)


def source_pins(root,api):
    return [dict(path=p,size_bytes=(root/p).stat().st_size,sha256=digest((root/p).read_bytes())) for p in api.SOURCES]


def file_pin(root,path):
    raw=path.read_bytes()
    return dict(path=str(path.relative_to(root)),size_bytes=len(raw),sha256=digest(raw))


@contextmanager
def publication05_fixture(tmp_path):
    assert tmp_path.resolve().is_relative_to((ROOT/'runs').resolve()), 'Use persistent runs/ basetemp'
    root,current,inputs,_=project(tmp_path,autograd_publication=True)
    legacy=ROOT/'docs/reports/puck-cpu-held-preparation-01'
    changed={PARENT,current.BOOTSTRAP,BINDINGS,IMPORTS}
    fresh={name:(root/name).read_bytes() for name in changed}
    for name in changed:
        folder='parent-source' if name==PARENT else 'worker-source'
        raw=(legacy/'raw'/folder/name).read_bytes()
        if name==PARENT:
            marker=b"min_available_ram_bytes=(4096 if phase=='prepare' else 2048)*MiB"
            replacement=b'min_available_ram_bytes=128*MiB'
            assert raw.count(marker)==1
            adapted=raw.replace(marker,replacement)
            assert adapted.replace(replacement,marker)==raw
            raw=adapted
        (root/name).write_bytes(raw)
    historical=load(root/PARENT,'cpu_authored_publication_old_parent')
    auditor_path=root/'scripts/audit_puck_cpu_held_runtime.py'
    auditor_raw=(legacy/'controls/scripts/audit_puck_cpu_held_runtime.py').read_bytes()
    assert digest(auditor_raw)==LEGACY_AUDITOR_SHA
    auditor_path.write_bytes(auditor_raw)
    stage=Path('/tmp')/('palimpsest-puck-cpu-held-authored-publication05-'+secrets.token_hex(12))
    assert not os.path.lexists(stage)
    try:
        prepare=historical.configuration_template(phase='prepare',root=str(root),stage_parent=str(stage),
            sources=source_pins(root,historical),inputs=inputs,negative_imports=['org'])
        code,stdout,stderr=run_cli(root,historical,'prepare',prepare)
        prepbase=root/historical.OUTPUTS['prepare'];result_path=prepbase/'result.json'
        prepared_raw=result_path.read_bytes() if result_path.exists() else b''
        assert code==0,(code,stdout,stderr,prepared_raw)
        prepared=json.loads(prepared_raw)
        assert stdout==prepared_raw and prepared['status']=='prepared'
        configuration=root/'authored-prepare-configuration.json'
        transport=root/'authored-prepare-transport.json'
        published=root/'docs/authored/historical-publication05-audit.json'
        command=[historical.PYTHON,'-I','-S','-B',str(auditor_path),
            '--configuration',str(configuration),'--sha256',digest(configuration.read_bytes()),
            '--transport',str(transport),'--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
        started=time.monotonic()
        process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
            env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
        channels={}
        for channel,raw in (('stdout',process.stdout),('stderr',process.stderr)):
            path=root/('authored-publication05-historical-audit.'+channel);path.write_bytes(raw)
            channels[channel]=dict(path=str(path),size_bytes=len(raw),sha256=digest(raw))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        assert json.loads(process.stdout)['status']=='PASS'
        cli=root/'docs/authored/historical-publication05-audit-cli.json'
        cli.write_bytes(canonical(dict(kind='externally-observed-cpu-auditor-cli-v1',
            command=command,observed_returncode=process.returncode,elapsed_seconds=time.monotonic()-started,
            published=dict(path=str(published),size_bytes=published.stat().st_size,sha256=digest(published.read_bytes())),**channels)))
        qualification=historical.configuration_template(phase='qualify',root=str(root),stage_parent=str(stage),
            sources=source_pins(root,historical),inputs=inputs,negative_imports=['org'],preparation=file_pin(root,result_path))
        code,stdout,stderr=run_cli(root,historical,'qualify',qualification)
        failed_base=root/historical.OUTPUTS['qualify']
        assert code==1,(code,stdout,stderr)
        failed=json.loads(stdout)
        assert failed['status']=='FAIL' and failed['held_four_imports_observed'] is False
        assert not (failed_base/'baseline-after.json').exists()
        assert b'Dependency producer attribute binding is missing' in (failed_base/'logs/stderr.log').read_bytes()
        paths=[p for p in (root/'runs').rglob('*') if p.is_file()]
        paths+=[configuration,transport,published,cli,root/inputs['candidate']['path'],auditor_path]
        paths+=list(root.glob('authored-prepare-cli.*'))+list(root.glob('authored-qualify-*'))
        paths+=list(root.glob('authored-publication05-historical-audit.*'))
        legacy_bytes={str(p.relative_to(root)):p.read_bytes() for p in paths}
        for name,raw in fresh.items():(root/name).write_bytes(raw)
        acceptance={key:file_pin(root,path) for key,path in dict(configuration=configuration,
            result=result_path,independent_audit=published,externally_observed_auditor_cli=cli).items()}
        updated_inputs=copy.deepcopy(inputs)
        candidate=json.loads((root/inputs['candidate']['path']).read_bytes())
        assert candidate['import_profile']['exports']==[dict(name=TARGET,producer='torch._C',
            phase='native_create',attributes=['_autograd'],class_binding=None)]
        candidate['import_profile']['exports'][0]=dict(name=TARGET,producer='torch.autograd',
            phase='module_exec_publish',attributes=['torch','_C','_autograd'],class_binding=None,
            delegate_attributes=list(DELEGATES))
        candidate_path=root/'docs/authored/candidate-publication05.json'
        candidate_path.write_bytes(canonical(candidate));updated_inputs['candidate']=file_pin(root,candidate_path)
        config=current.configuration_template(phase='qualify',root=str(root),stage_parent=str(stage),
            sources=source_pins(root,current),inputs=updated_inputs,negative_imports=['org','torch._rocm_init'],
            preparation_acceptance=acceptance)
        config.update(kind='puck-cpu-held-runtime-allocation-v5',version=5,allocation_id=5)
        old_sources={r['path']:r for r in prepare['sources']}
        assert {r['path'] for r in config['sources'] if r!=old_sources[r['path']]}==changed
        assert {role for role in inputs if inputs[role]!=updated_inputs[role]}=={'candidate'}
        assert not (root/'runs/puck-cpu-held-qualification-05').exists()
        yield dict(root=root,api=current,config=config,stage=stage,legacy_bytes=legacy_bytes,
            prepared=prepared,prepbase=prepbase,candidate=candidate)
    finally:
        for name,raw in fresh.items():(root/name).write_bytes(raw)
        if os.path.lexists(stage):
            assert stage.is_dir() and not stage.is_symlink()
            shutil.rmtree(stage)
        (root/'authored-publication05-stage-cleanup.json').write_bytes(canonical(dict(
            authored_scope=AUTHORED,owned_stage=str(stage),absent=not os.path.lexists(stage),actual_vendor_imports=False)))
        assert not os.path.lexists(stage)


def test_authored05_corrects_only_publication_profile_and_audits_both_epochs(tmp_path):
    auditor_path=ROOT/'scripts/audit_puck_cpu_held_runtime.py'
    auditor=load(auditor_path,'cpu_authored_publication05_auditor')
    before_fds=len(os.listdir('/proc/self/fd'))
    with publication05_fixture(tmp_path) as case:
        root,api,config,stage,prepbase=(case[k] for k in ('root','api','config','stage','prepbase'))
        identities=[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        historical_dep=(prepbase/'payload/dependencies.json').read_bytes()
        code,stdout,stderr=run_cli(root,api,'qualify05',config)
        base=root/'runs/puck-cpu-held-qualification-05';result_path=base/'result.json'
        result_raw=result_path.read_bytes() if result_path.exists() else b''
        assert code==0,(code,stdout,stderr,result_raw)
        result=json.loads(result_raw)
        assert stdout==result_raw and result['status']=='imports_completed'
        assert (result['version'],result['allocation_id'])==(5,5)
        current_dep=(base/'control/dependencies.json').read_bytes()
        assert current_dep!=historical_dep
        expected=dict(name=TARGET,producer='torch.autograd',phase='module_exec_publish',
            attributes=['torch','_C','_autograd'],delegate_attributes=list(DELEGATES))
        worker_path=base/'logs/stdout.log';worker=json.loads(worker_path.read_bytes())
        assert worker['dependencies']['published_export_modules']==[expected]
        assert [(r['name'],r['version']) for r in worker['entry_result']['imports']]==list(api.VERSIONS.items())
        registration=json.loads((base/'control/worker-registration.json').read_bytes())
        assert registration['source_files']==[r for r in config['sources'] if r['path'] in api.WORKER_SOURCES]
        assert registration['dependencies']['sha256']==digest(current_dep)
        for row in registration['source_files']:
            raw=(base/'worker-source'/row['path']).read_bytes()
            assert len(raw)==row['size_bytes'] and digest(raw)==row['sha256']
        assert json.loads(current_dep)['roots']==json.loads(historical_dep)['roots']
        assert json.loads(current_dep)['distributions']==json.loads(historical_dep)['distributions']
        configuration=root/'authored-qualify05-configuration.json'
        transport=root/'authored-qualify05-transport.json'

        def audit():
            count=len(os.listdir('/proc/self/fd'))
            try:
                return auditor.audit(configuration,digest(configuration.read_bytes()),transport,
                    digest(transport.read_bytes()),deadline=time.monotonic()+30)
            finally:assert len(os.listdir('/proc/self/fd'))==count

        report=audit()
        assert report['status']=='PASS' and report['version']==5
        assert report['historical_dependencies_sha256']==digest(historical_dep)
        assert report['current_dependencies_sha256']==report['dependencies_sha256']==digest(current_dep)
        assert report['historical_candidate_sha256']==case['prepared']['inputs']['candidate']['sha256']
        assert report['current_candidate_sha256']==config['inputs']['candidate']['sha256']
        (root/'authored-publication05-api-audit.json').write_bytes(canonical(report))
        published=root/'authored-publication05-cli-audit.json'
        command=[api.PYTHON,'-I','-S','-B',str(auditor_path),'--configuration',str(configuration),
            '--sha256',digest(configuration.read_bytes()),'--transport',str(transport),
            '--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
        started=time.monotonic()
        process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
            env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
        for channel,raw in (('stdout',process.stdout),('stderr',process.stderr)):
            (root/('authored-publication05-cli-audit.'+channel)).write_bytes(raw)
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        cli_report=json.loads(process.stdout)
        assert cli_report['status']=='PASS' and cli_report['auditor_source_sha256']==digest(auditor_path.read_bytes())
        (root/'authored-publication05-cli-audit-transport.json').write_bytes(canonical(dict(
            kind='authored-cpu-held-auditor-cli-transport-v1',authored_scope=AUTHORED,
            command=command,observed_returncode=process.returncode,elapsed_seconds=time.monotonic()-started)))

        stdout_path=root/'authored-qualify05-cli.stdout'
        originals={p:p.read_bytes() for p in (worker_path,result_path,stdout_path,transport)}
        try:
            changed=json.loads(originals[worker_path])
            changed['dependencies']['published_export_modules'][0]['delegate_attributes'].pop()
            changed_worker=canonical(changed);worker_path.write_bytes(changed_worker)
            changed_result=json.loads(result_raw);changed_result['worker_stdout_sha256']=digest(changed_worker)
            changed_result_raw=canonical(changed_result);result_path.write_bytes(changed_result_raw);stdout_path.write_bytes(changed_result_raw)
            changed_transport=json.loads(originals[transport]);changed_transport['stdout'].update(size_bytes=len(changed_result_raw),sha256=digest(changed_result_raw))
            transport.write_bytes(canonical(changed_transport))
            with pytest.raises(ValueError,match='(?i)publish'):audit()
        finally:
            for path,raw in originals.items():path.write_bytes(raw)

        candidate_path=root/config['inputs']['candidate']['path']
        invocation=base/'invocation.json';retained_config=base/'configuration.json'
        originals={p:p.read_bytes() for p in (candidate_path,configuration,retained_config,invocation,result_path,stdout_path,transport)}
        try:
            changed_candidate=json.loads(originals[candidate_path])
            changed_candidate['import_profile']['exports'][0]['attributes']=['foreign']
            changed_candidate_raw=canonical(changed_candidate);candidate_path.write_bytes(changed_candidate_raw)
            changed_config=json.loads(originals[configuration]);changed_config['inputs']['candidate']=file_pin(root,candidate_path)
            changed_config_raw=canonical(changed_config);configuration.write_bytes(changed_config_raw);retained_config.write_bytes(changed_config_raw)
            changed_result=json.loads(originals[result_path]);changed_result['configuration_sha256']=digest(changed_config_raw)
            changed_result_raw=canonical(changed_result);result_path.write_bytes(changed_result_raw);stdout_path.write_bytes(changed_result_raw)
            changed_transport=json.loads(originals[transport]);changed_transport['configuration_sha256']=digest(changed_config_raw)
            changed_transport['command'][-1]=digest(changed_config_raw)
            changed_transport['stdout'].update(size_bytes=len(changed_result_raw),sha256=digest(changed_result_raw));transport.write_bytes(canonical(changed_transport))
            changed_invocation=json.loads(originals[invocation]);changed_invocation['configuration_sha256']=digest(changed_config_raw);invocation.write_bytes(canonical(changed_invocation))
            with pytest.raises(ValueError,match='(?i)(autograd|publication)'):audit()
        finally:
            for path,raw in originals.items():path.write_bytes(raw)

        for path,raw in case['legacy_bytes'].items():assert (root/path).read_bytes()==raw
        assert (prepbase/'payload/dependencies.json').read_bytes()==historical_dep
        assert identities==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        for outcome in (case['prepared'],result,report,cli_report):
            assert all(outcome[k]==v for k,v in api.CLAIMS.items())
            assert outcome['closure']['active_children']==outcome['closure']['active_non_main_threads']==[]
            assert outcome['closure']['fd_count_before']==outcome['closure']['fd_count_after']
        code,_,stderr=run_cli(root,api,'qualify05-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert result_path.read_bytes()==result_raw
        for path,raw in case['legacy_bytes'].items():assert (root/path).read_bytes()==raw
        (root/'authored-publication05-observations.json').write_bytes(canonical(dict(
            authored_scope=AUTHORED,publication_delegates=DELEGATES,actual_vendor_imports=False,
            historical_v1_failed=True,qualification05_audited=True,rebound_proof_rejected=True,
            rebound_candidate_rejected=True,historical_bytes_preserved=True,consumed_reentry_refused=True)))
    assert len(os.listdir('/proc/self/fd'))==before_fds
