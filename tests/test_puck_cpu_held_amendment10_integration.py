"""Authored preparation → q4epoch10 → API/CLI audits; no installed vendors."""
import copy
import json
import os
import subprocess
import time

import pytest

from test_puck_cpu_held_amendment05_integration import file_pin, publication05_fixture
from test_puck_cpu_held_amendment06_integration import AUTHORED_ROSTER06
from test_puck_cpu_held_amendment07 import PILLOW_ORIGINS
from test_puck_cpu_held_amendment08 import DIAGNOSTIC_SOURCES, QUALIFIER
from test_puck_cpu_held_parent_integration import ROOT, canonical, digest, load, run_cli


def test_authored10_binds_fifth_source_diagnostics_and_independent_audits(tmp_path):
    before=len(os.listdir('/proc/self/fd'))
    auditor_path=ROOT/'scripts/audit_puck_cpu_held_runtime.py'
    auditor=load(auditor_path,'cpu_authored_q4epoch10_auditor')
    with publication05_fixture(tmp_path,pillow_origins=True,phase_trace=True) as case:
        root,api,config,stage,prepbase=(case[k] for k in ('root','api','config','stage','prepbase'))
        historical_dep=(prepbase/'payload/dependencies.json').read_bytes()
        identities=[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        qualifier_pin=next(r for r in config['sources'] if r['path']==QUALIFIER)
        old_sources={r['path']:r for r in case['prepared']['sources']}
        assert {r['path'] for r in config['sources'] if r!=old_sources[r['path']]}==set(DIAGNOSTIC_SOURCES)
        assert qualifier_pin['sha256']==digest((ROOT/QUALIFIER).read_bytes())
        assert qualifier_pin!=old_sources[QUALIFIER]
        candidate=copy.deepcopy(case['candidate'])
        candidate['import_profile']['native_origins']=copy.deepcopy(PILLOW_ORIGINS)
        path=root/'docs/authored/candidate-q4epoch10.json';path.write_bytes(canonical(candidate))
        config['inputs']['candidate']=file_pin(root,path)
        config.update(kind='puck-cpu-held-runtime-allocation-v10',version=10,allocation_id=10,
            negative_imports=list(AUTHORED_ROSTER06))
        code,stdout,stderr=run_cli(root,api,'qualify10',config)
        base=root/'runs/puck-cpu-held-qualification-10'
        raw=(base/'result.json').read_bytes() if (base/'result.json').exists() else b''
        assert code==0,(code,stdout,stderr,raw)
        result=json.loads(raw)
        assert stdout==raw and (result['kind'],result['version'],result['allocation_id'],result['status'])==(
            'puck-cpu-held-runtime-outcome-v10',10,10,'imports_completed')
        worker=json.loads((base/'logs/stdout.log').read_bytes())
        assert [(r['name'],r['version']) for r in worker['entry_result']['imports']]==list(api.VERSIONS.items())
        records=[(line,json.loads(line)) for line in (base/'logs/stderr.log').read_bytes().splitlines()]
        trace=[row for _,row in records if row['kind']=='puck-worker-phase-v1']
        costs=[(line,row) for line,row in records if row['kind']=='puck-worker-guard-cost-v1']
        assert 0<len(costs)<=32 and sum(len(line)+1 for line,_ in costs)<=32*1024
        assert all(len(line)+1<=1024 and row['diagnostic_only'] is True for line,row in costs)
        assert [row['phase'] for row in trace]==[
            'bootstrap.enter','source.ready','dependencies.enter','dependencies.ready','bootstrap.ready','entry.enter',
            'import.numpy.enter','import.numpy.returned','import.torch.enter','import.torch.returned',
            'import.torchvision.enter','import.torchvision.returned','import.mujoco.enter','import.mujoco.returned',
            'entry.returned','entry.ready','close.enter','close.ready']
        registration=json.loads((base/'control/worker-registration.json').read_bytes())
        assert registration['qualification']['version']==4
        assert registration['qualification']['kind']=='puck-held-runtime-import-qualification-v4'
        assert worker['entry_result']['qualification_version']==4
        assert registration['source_files']==[r for r in config['sources'] if r['path'] in api.WORKER_SOURCES]
        assert (base/'worker-source'/QUALIFIER).read_bytes()==(ROOT/QUALIFIER).read_bytes()
        current_dep=(base/'control/dependencies.json').read_bytes()
        assert json.loads(current_dep)['roots']==json.loads(historical_dep)['roots']
        configuration=root/'authored-qualify10-configuration.json'
        transport=root/'authored-qualify10-transport.json'
        report=auditor.audit(configuration,digest(configuration.read_bytes()),transport,
            digest(transport.read_bytes()),deadline=time.monotonic()+30)
        assert (report['kind'],report['version'],report['allocation_id'],report['status'])==(
            'puck-cpu-held-runtime-independent-audit-v10',10,10,'PASS')
        (root/'authored-q4epoch10-api-audit.json').write_bytes(canonical(report))
        assert report['historical_dependencies_sha256']==digest(historical_dep)
        assert report['current_dependencies_sha256']==report['dependencies_sha256']==digest(current_dep)
        published=root/'authored-q4epoch10-cli-audit.json'
        command=[api.PYTHON,'-I','-S','-B',str(auditor_path),'--configuration',str(configuration),
            '--sha256',digest(configuration.read_bytes()),'--transport',str(transport),
            '--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
        cli_started=time.monotonic()
        process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
            env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
        (root/'authored-q4epoch10-cli-audit.stdout').write_bytes(process.stdout)
        (root/'authored-q4epoch10-cli-audit.stderr').write_bytes(process.stderr)
        (root/'authored-q4epoch10-cli-audit-transport.json').write_bytes(canonical(dict(
            kind='authored-cpu-held-auditor-cli-transport-v1',command=command,
            observed_returncode=process.returncode,elapsed_seconds=time.monotonic()-cli_started)))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        assert json.loads(process.stdout)['status']=='PASS' and json.loads(process.stdout)['version']==10
        for outcome in (result,report,json.loads(process.stdout)):
            assert all(outcome[key]==value for key,value in api.CLAIMS.items())
            assert outcome['closure']['active_children']==outcome['closure']['active_non_main_threads']==[]
            assert outcome['closure']['fd_count_before']==outcome['closure']['fd_count_after']
        # Optional diagnostics cannot become a new independent acceptance gate.
        diagnostic_log=base/'logs/stderr.log';original_diagnostics=diagnostic_log.read_bytes()
        try:
            diagnostic_log.write_bytes(b'\n'.join(line for line,row in records
                if row['kind']!='puck-worker-guard-cost-v1')+b'\n')
            without_costs=auditor.audit(configuration,digest(configuration.read_bytes()),transport,
                digest(transport.read_bytes()),deadline=time.monotonic()+30)
            assert without_costs['status']=='PASS' and without_costs['version']==10
            (root/'authored-q4epoch10-no-cost-api-audit.json').write_bytes(canonical(without_costs))
        finally:diagnostic_log.write_bytes(original_diagnostics)
        assert diagnostic_log.read_bytes()==original_diagnostics
        assert (prepbase/'payload/dependencies.json').read_bytes()==historical_dep
        assert identities==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        # Exercise independent q4 version gates directly with the real held reader.
        sources={row['path']:(base/'worker-source'/row['path']).read_bytes() for row in registration['source_files']}
        for filename,marker in (('control/worker-registration.json','Exact worker registration differs'),
                                ('logs/stdout.log','Four ordered import versions incomplete')):
            target=base/filename;original=target.read_bytes();changed=json.loads(original)
            if filename.startswith('control/'):
                changed['qualification'].update(kind='puck-held-runtime-import-qualification-v3',version=3)
            else:changed['entry_result']['qualification_version']=3
            try:
                payload=canonical(changed) if filename.startswith('logs/') else canonical(changed).rstrip(b'\n')
                target.write_bytes(payload)
                held=auditor.Held(time.monotonic()+30)
                try:
                    with pytest.raises(ValueError,match='^'+marker+'$'):
                        auditor.worker(held,base,config,json.loads(current_dep),current_dep,sources)
                finally:held.close()
            finally:target.write_bytes(original)
        legacy_config=copy.deepcopy(config)
        legacy_config.update(kind='puck-cpu-held-runtime-allocation-v9',version=9,allocation_id=9)
        auditor.configuration(legacy_config,True)
        held=auditor.Held(time.monotonic()+30)
        try:
            with pytest.raises(ValueError,match='^Exact worker registration differs$'):
                auditor.worker(held,base,legacy_config,json.loads(current_dep),current_dep,sources)
        finally:held.close()
        for name,previous in case['legacy_bytes'].items():assert (root/name).read_bytes()==previous
        code,_,stderr=run_cli(root,api,'qualify10-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert (base/'result.json').read_bytes()==raw
    assert len(os.listdir('/proc/self/fd'))==before
