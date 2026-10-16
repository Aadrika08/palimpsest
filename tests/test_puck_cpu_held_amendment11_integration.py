"""Authored preparation → policy-v5 epoch11 → API/CLI audits; no installed vendors."""
import copy
import json
import os
import subprocess
import time

import pytest

from test_puck_cpu_held_amendment05_integration import file_pin, publication05_fixture
from test_puck_cpu_held_amendment07 import PILLOW_ORIGINS
from test_puck_cpu_held_amendment08 import DIAGNOSTIC_SOURCES, QUALIFIER
from test_puck_cpu_held_amendment11 import HIDDEN11, ROSTER11
from test_puck_cpu_held_parent_integration import ROOT, canonical, digest, load, run_cli


AUTHORED_ROSTER11=[name for name in ROSTER11 if name!='numpy._distributor_init_local']
PROBED=['backports_abc','networkx','pandas','sklearn','tabulate']


def test_authored11_binds_policy_v5_rosters_and_independent_audits(tmp_path):
    before=len(os.listdir('/proc/self/fd'))
    auditor_path=ROOT/'scripts/audit_puck_cpu_held_runtime.py'
    auditor=load(auditor_path,'cpu_authored_v5epoch11_auditor')
    with publication05_fixture(tmp_path,pillow_origins=True,phase_trace=True,stock_absence_probe=True) as case:
        root,api,config,stage,prepbase=(case[k] for k in ('root','api','config','stage','prepbase'))
        historical_dep=(prepbase/'payload/dependencies.json').read_bytes()
        identities=[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        old_sources={r['path']:r for r in case['prepared']['sources']}
        assert {r['path'] for r in config['sources'] if r!=old_sources[r['path']]}==set(DIAGNOSTIC_SOURCES)
        assert next(r for r in config['sources'] if r['path']==QUALIFIER)['sha256']==digest((ROOT/QUALIFIER).read_bytes())
        candidate=copy.deepcopy(case['candidate'])
        candidate['import_profile']['native_origins']=copy.deepcopy(PILLOW_ORIGINS)
        path=root/'docs/authored/candidate-v5epoch11.json';path.write_bytes(canonical(candidate))
        config['inputs']['candidate']=file_pin(root,path)
        assert len(AUTHORED_ROSTER11)==31 and api.QUALIFY11_NEGATIVE_IMPORTS==AUTHORED_ROSTER11
        config.update(kind='puck-cpu-held-runtime-allocation-v11',version=11,allocation_id=11,
            negative_imports=list(AUTHORED_ROSTER11))
        code,stdout,stderr=run_cli(root,api,'qualify11',config)
        base=root/'runs/puck-cpu-held-qualification-11'
        raw=(base/'result.json').read_bytes() if (base/'result.json').exists() else b''
        assert code==0,(code,stdout,stderr,raw,(base/'logs/stderr.log').read_bytes() if (base/'logs/stderr.log').exists() else b'')
        result=json.loads(raw)
        assert stdout==raw and (result['kind'],result['version'],result['allocation_id'],result['status'])==(
            'puck-cpu-held-runtime-outcome-v11',11,11,'imports_completed')
        worker=json.loads((base/'logs/stdout.log').read_bytes())
        assert [(r['name'],r['version']) for r in worker['entry_result']['imports']]==list(api.VERSIONS.items())
        assert worker['entry_result']['qualification_version']==5
        assert worker['expected_missing_imports']==AUTHORED_ROSTER11
        assert worker['expected_hidden_imports']==HIDDEN11
        assert worker['denied_imports']==PROBED
        records=[(line,json.loads(line)) for line in (base/'logs/stderr.log').read_bytes().splitlines()]
        trace=[row for _,row in records if row['kind']=='puck-worker-phase-v1']
        assert [row['phase'] for row in trace]==[
            'bootstrap.enter','source.ready','dependencies.enter','dependencies.ready','bootstrap.ready','entry.enter',
            'import.numpy.enter','import.numpy.returned','import.torch.enter','import.torch.returned',
            'import.torchvision.enter','import.torchvision.returned','import.mujoco.enter','import.mujoco.returned',
            'entry.returned','entry.ready','close.enter','close.ready']
        registration=json.loads((base/'control/worker-registration.json').read_bytes())
        assert registration['qualification']['kind']=='puck-held-runtime-import-qualification-v5'
        assert registration['qualification']['version']==5
        assert registration['qualification']['negative_imports']==AUTHORED_ROSTER11
        assert registration['qualification']['hidden_imports']==HIDDEN11
        assert registration['source_files']==[r for r in config['sources'] if r['path'] in api.WORKER_SOURCES]
        current_dep=(base/'control/dependencies.json').read_bytes()
        assert json.loads(current_dep)['roots']==json.loads(historical_dep)['roots']
        configuration=root/'authored-qualify11-configuration.json'
        transport=root/'authored-qualify11-transport.json'
        report=auditor.audit(configuration,digest(configuration.read_bytes()),transport,
            digest(transport.read_bytes()),deadline=time.monotonic()+30)
        assert (report['kind'],report['version'],report['allocation_id'],report['status'])==(
            'puck-cpu-held-runtime-independent-audit-v11',11,11,'PASS')
        (root/'authored-v5epoch11-api-audit.json').write_bytes(canonical(report))
        assert report['historical_dependencies_sha256']==digest(historical_dep)
        assert report['current_dependencies_sha256']==report['dependencies_sha256']==digest(current_dep)
        published=root/'authored-v5epoch11-cli-audit.json'
        command=[api.PYTHON,'-I','-S','-B',str(auditor_path),'--configuration',str(configuration),
            '--sha256',digest(configuration.read_bytes()),'--transport',str(transport),
            '--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
        process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
            env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
        (root/'authored-v5epoch11-cli-audit.stdout').write_bytes(process.stdout)
        (root/'authored-v5epoch11-cli-audit.stderr').write_bytes(process.stderr)
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        assert json.loads(process.stdout)['status']=='PASS' and json.loads(process.stdout)['version']==11
        for outcome in (result,report,json.loads(process.stdout)):
            assert all(outcome[key]==value for key,value in api.CLAIMS.items())
            assert outcome['closure']['active_children']==outcome['closure']['active_non_main_threads']==[]
            assert outcome['closure']['fd_count_before']==outcome['closure']['fd_count_after']
        assert (prepbase/'payload/dependencies.json').read_bytes()==historical_dep
        assert identities==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        # Exercise the independent v5 roster gates directly with the real held reader.
        sources={row['path']:(base/'worker-source'/row['path']).read_bytes() for row in registration['source_files']}
        def registration_v4(value):
            value['qualification'].update(kind='puck-held-runtime-import-qualification-v4',version=4)
            del value['qualification']['hidden_imports']
        receipt='Worker bootstrap/source/negative-import receipt differs'
        for filename,change,marker in (
                ('control/worker-registration.json',registration_v4,'Exact worker registration differs'),
                ('control/worker-registration.json',lambda v:v['qualification']['hidden_imports'].pop(),
                 'Exact worker registration differs'),
                ('logs/stdout.log',lambda v:v['entry_result'].update(qualification_version=4),
                 'Four ordered import versions incomplete'),
                ('logs/stdout.log',lambda v:v.pop('expected_hidden_imports'),receipt),
                ('logs/stdout.log',lambda v:v['expected_hidden_imports'].pop(),receipt),
                ('logs/stdout.log',lambda v:v.update(denied_imports=PROBED+['unreviewed']),receipt)):
            target=base/filename;original=target.read_bytes();changed=json.loads(original);change(changed)
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
        legacy_config.update(kind='puck-cpu-held-runtime-allocation-v10',version=10,allocation_id=10,
            negative_imports=[name for name in legacy_config['negative_imports'] if name in api.QUALIFY06_NEGATIVE_IMPORTS])
        auditor.configuration(legacy_config,True)
        held=auditor.Held(time.monotonic()+30)
        try:
            with pytest.raises(ValueError,match='^Exact worker registration differs$'):
                auditor.worker(held,base,legacy_config,json.loads(current_dep),current_dep,sources)
        finally:held.close()
        for name,previous in case['legacy_bytes'].items():assert (root/name).read_bytes()==previous
        code,_,stderr=run_cli(root,api,'qualify11-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert (base/'result.json').read_bytes()==raw
    assert len(os.listdir('/proc/self/fd'))==before
