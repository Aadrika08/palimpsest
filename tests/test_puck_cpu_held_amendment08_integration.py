"""Authored historical preparation → traced08 → independent audits; no vendors."""
import copy
import json
import os
import subprocess
import time

from test_puck_cpu_held_amendment05_integration import file_pin, publication05_fixture
from test_puck_cpu_held_amendment06_integration import AUTHORED_ROSTER06
from test_puck_cpu_held_amendment07 import PILLOW_ORIGINS
from test_puck_cpu_held_amendment08 import DIAGNOSTIC_SOURCES, QUALIFIER
from test_puck_cpu_held_parent_integration import ROOT, canonical, digest, load, run_cli


def test_authored08_binds_fifth_source_diagnostics_and_independent_audits(tmp_path):
    before=len(os.listdir('/proc/self/fd'))
    auditor_path=ROOT/'scripts/audit_puck_cpu_held_runtime.py'
    auditor=load(auditor_path,'cpu_authored_diagnostic08_auditor')
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
        path=root/'docs/authored/candidate-diagnostic08.json';path.write_bytes(canonical(candidate))
        config['inputs']['candidate']=file_pin(root,path)
        config.update(kind='puck-cpu-held-runtime-allocation-v8',version=8,allocation_id=8,
            negative_imports=list(AUTHORED_ROSTER06))
        code,stdout,stderr=run_cli(root,api,'qualify08',config)
        base=root/'runs/puck-cpu-held-qualification-08'
        raw=(base/'result.json').read_bytes() if (base/'result.json').exists() else b''
        assert code==0,(code,stdout,stderr,raw)
        result=json.loads(raw)
        assert stdout==raw and (result['kind'],result['version'],result['allocation_id'],result['status'])==(
            'puck-cpu-held-runtime-outcome-v8',8,8,'imports_completed')
        worker=json.loads((base/'logs/stdout.log').read_bytes())
        assert [(r['name'],r['version']) for r in worker['entry_result']['imports']]==list(api.VERSIONS.items())
        trace=[json.loads(line) for line in (base/'logs/stderr.log').read_bytes().splitlines()]
        assert [row['phase'] for row in trace]==[
            'bootstrap.enter','source.ready','dependencies.enter','dependencies.ready','bootstrap.ready','entry.enter',
            'import.numpy.enter','import.numpy.returned','import.torch.enter','import.torch.returned',
            'import.torchvision.enter','import.torchvision.returned','import.mujoco.enter','import.mujoco.returned',
            'entry.returned','entry.ready','close.enter','close.ready']
        registration=json.loads((base/'control/worker-registration.json').read_bytes())
        assert registration['qualification']['version']==3
        assert registration['source_files']==[r for r in config['sources'] if r['path'] in api.WORKER_SOURCES]
        assert (base/'worker-source'/QUALIFIER).read_bytes()==(ROOT/QUALIFIER).read_bytes()
        current_dep=(base/'control/dependencies.json').read_bytes()
        assert json.loads(current_dep)['roots']==json.loads(historical_dep)['roots']
        configuration=root/'authored-qualify08-configuration.json'
        transport=root/'authored-qualify08-transport.json'
        report=auditor.audit(configuration,digest(configuration.read_bytes()),transport,
            digest(transport.read_bytes()),deadline=time.monotonic()+30)
        assert (report['kind'],report['version'],report['allocation_id'],report['status'])==(
            'puck-cpu-held-runtime-independent-audit-v8',8,8,'PASS')
        assert report['historical_dependencies_sha256']==digest(historical_dep)
        assert report['current_dependencies_sha256']==report['dependencies_sha256']==digest(current_dep)
        published=root/'authored-diagnostic08-cli-audit.json'
        command=[api.PYTHON,'-I','-S','-B',str(auditor_path),'--configuration',str(configuration),
            '--sha256',digest(configuration.read_bytes()),'--transport',str(transport),
            '--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
        process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
            env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
        (root/'authored-diagnostic08-cli-audit.stdout').write_bytes(process.stdout)
        (root/'authored-diagnostic08-cli-audit.stderr').write_bytes(process.stderr)
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        assert json.loads(process.stdout)['status']=='PASS' and json.loads(process.stdout)['version']==8
        for outcome in (result,report,json.loads(process.stdout)):
            assert all(outcome[key]==value for key,value in api.CLAIMS.items())
            assert outcome['closure']['active_children']==outcome['closure']['active_non_main_threads']==[]
            assert outcome['closure']['fd_count_before']==outcome['closure']['fd_count_after']
        assert (prepbase/'payload/dependencies.json').read_bytes()==historical_dep
        assert identities==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        for name,previous in case['legacy_bytes'].items():assert (root/name).read_bytes()==previous
        code,_,stderr=run_cli(root,api,'qualify08-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert (base/'result.json').read_bytes()==raw
    assert len(os.listdir('/proc/self/fd'))==before
