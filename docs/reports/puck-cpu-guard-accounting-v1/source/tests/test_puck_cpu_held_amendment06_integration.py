"""AUTHORED caught-optional05 failure to06 success, never installed vendors.

The fixture uses a tiny authored CPU extension and four Python creators. Its
05 failure and06 success concern the finite import contract, not model or
numerical capability. No actual allocation controls are constructed here.
"""
import copy
import json
import os
import subprocess
import time

import pytest

from test_puck_cpu_held_amendment05 import PUBLICATION_EXPORTS
from test_puck_cpu_held_amendment05_integration import publication05_fixture
from test_puck_cpu_held_amendment06 import ROSTER06
from test_puck_cpu_held_parent_integration import AUTHORED, ROOT, canonical, digest, load, run_cli


# The shared authored preparation omits NumPy's vendor-only distributor hook.
AUTHORED_ROSTER06=[name for name in ROSTER06 if name!='numpy._distributor_init_local']


def test_authored06_declares_caught_optional_absence_without_changing05_candidate_or_old_evidence(tmp_path):
    auditor_path=ROOT/'scripts/audit_puck_cpu_held_runtime.py'
    auditor=load(auditor_path,'cpu_authored_optional06_auditor')
    before_fds=len(os.listdir('/proc/self/fd'))
    with publication05_fixture(tmp_path,caught_optional_import=True) as case:
        root,api,five,stage,prepbase=(case[k] for k in ('root','api','config','stage','prepbase'))
        historical_dep=(prepbase/'payload/dependencies.json').read_bytes()
        root_ids=[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        candidate_path=root/five['inputs']['candidate']['path']
        candidate_raw=candidate_path.read_bytes()

        # This is a separately invoked, genuinely failed authored05 attempt.
        # Torch catches ImportError; undeclared imports must still poison05.
        code,stdout,stderr=run_cli(root,api,'qualify05',five)
        failed_base=root/'runs/puck-cpu-held-qualification-05'
        failed_raw=(failed_base/'result.json').read_bytes() if (failed_base/'result.json').exists() else b''
        assert code==1,(code,stdout,stderr,failed_raw)
        failed=json.loads(failed_raw)
        assert stdout==failed_raw and failed['status']=='FAIL'
        assert failed['held_four_imports_observed'] is False
        assert not (failed_base/'baseline-after.json').exists()
        assert b'pynvml' in (failed_base/'logs/stderr.log').read_bytes()
        five_config=root/'authored-qualify05-configuration.json'
        five_transport=root/'authored-qualify05-transport.json'
        with pytest.raises(ValueError):
            auditor.audit(five_config,digest(five_config.read_bytes()),five_transport,
                digest(five_transport.read_bytes()),deadline=time.monotonic()+30)
        prior={p:p.read_bytes() for p in failed_base.rglob('*') if p.is_file()}
        prior.update({p:p.read_bytes() for p in root.glob('authored-qualify05-*') if p.is_file()})
        assert prior

        config=copy.deepcopy(five)
        config.update(kind='puck-cpu-held-runtime-allocation-v6',version=6,
                      allocation_id=6,negative_imports=list(AUTHORED_ROSTER06))
        assert len(AUTHORED_ROSTER06)==18
        assert config['inputs']==five['inputs'] and config['sources']==five['sources']
        assert config['preparation_acceptance']==five['preparation_acceptance']
        assert not (root/'runs/puck-cpu-held-qualification-06').exists()
        code,stdout,stderr=run_cli(root,api,'qualify06',config)
        base=root/'runs/puck-cpu-held-qualification-06';result_path=base/'result.json'
        result_raw=result_path.read_bytes() if result_path.exists() else b''
        assert code==0,(code,stdout,stderr,result_raw)
        result=json.loads(result_raw)
        assert stdout==result_raw
        assert (result['kind'],result['version'],result['allocation_id'],result['status'])==(
            'puck-cpu-held-runtime-outcome-v6',6,6,'imports_completed')
        assert result['held_four_imports_observed'] is True
        worker=json.loads((base/'logs/stdout.log').read_bytes())
        assert worker['expected_missing_imports']==AUTHORED_ROSTER06
        assert worker['denied_imports']==['pynvml']
        assert [(r['name'],r['version']) for r in worker['entry_result']['imports']]==list(api.VERSIONS.items())
        expected=[{k:v for k,v in row.items() if k!='class_binding'} for row in PUBLICATION_EXPORTS]
        assert worker['dependencies']['published_export_modules']==expected
        assert [len(row['delegate_attributes']) for row in expected]==[41,11,69,29]
        assert worker['dependencies']['exported_modules']==[
            dict(name=row['name'],producer=row['producer']) for row in PUBLICATION_EXPORTS]

        current_dep=(base/'control/dependencies.json').read_bytes()
        assert current_dep!=historical_dep
        assert json.loads(current_dep)['roots']==json.loads(historical_dep)['roots']
        assert json.loads(current_dep)['distributions']==json.loads(historical_dep)['distributions']
        registration=json.loads((base/'control/worker-registration.json').read_bytes())
        assert registration['qualification']['kind']=='puck-held-runtime-import-qualification-v3'
        assert registration['qualification']['version']==3
        assert registration['qualification']['negative_imports']==AUTHORED_ROSTER06
        assert registration['source_files']==[r for r in config['sources'] if r['path'] in api.WORKER_SOURCES]
        assert registration['dependencies']['sha256']==digest(current_dep)
        for row in registration['source_files']:
            raw=(base/'worker-source'/row['path']).read_bytes()
            assert len(raw)==row['size_bytes'] and digest(raw)==row['sha256']

        configuration=root/'authored-qualify06-configuration.json'
        transport=root/'authored-qualify06-transport.json'
        count=len(os.listdir('/proc/self/fd'))
        report=auditor.audit(configuration,digest(configuration.read_bytes()),transport,
            digest(transport.read_bytes()),deadline=time.monotonic()+30)
        assert len(os.listdir('/proc/self/fd'))==count
        assert (report['kind'],report['version'],report['allocation_id'],report['status'])==(
            'puck-cpu-held-runtime-independent-audit-v6',6,6,'PASS')
        assert report['historical_dependencies_sha256']==digest(historical_dep)
        assert report['current_dependencies_sha256']==report['dependencies_sha256']==digest(current_dep)
        assert report['historical_candidate_sha256']==case['prepared']['inputs']['candidate']['sha256']
        assert report['current_candidate_sha256']==five['inputs']['candidate']['sha256']
        (root/'authored-optional06-api-audit.json').write_bytes(canonical(report))

        published=root/'authored-optional06-cli-audit.json'
        command=[api.PYTHON,'-I','-S','-B',str(auditor_path),'--configuration',str(configuration),
            '--sha256',digest(configuration.read_bytes()),'--transport',str(transport),
            '--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
        started=time.monotonic()
        process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
            env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
        channels={}
        for channel,raw in (('stdout',process.stdout),('stderr',process.stderr)):
            path=root/('authored-optional06-cli-audit.'+channel);path.write_bytes(raw)
            channels[channel]=dict(path=path.name,size_bytes=len(raw),sha256=digest(raw))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        cli_report=json.loads(process.stdout)
        assert cli_report['status']=='PASS' and cli_report['version']==6
        assert cli_report['auditor_source_sha256']==digest(auditor_path.read_bytes())
        (root/'authored-optional06-cli-audit-transport.json').write_bytes(canonical(dict(
            kind='authored-cpu-held-auditor-cli-transport-v1',authored_scope=AUTHORED,
            command=command,observed_returncode=process.returncode,
            elapsed_seconds=time.monotonic()-started,**channels)))

        for outcome in (case['prepared'],failed,result,report,cli_report):
            assert all(outcome[k]==value for k,value in api.CLAIMS.items())
            assert outcome['closure']['active_children']==outcome['closure']['active_non_main_threads']==[]
            assert outcome['closure']['fd_count_before']==outcome['closure']['fd_count_after']
        assert candidate_path.read_bytes()==candidate_raw
        assert (prepbase/'payload/dependencies.json').read_bytes()==historical_dep
        assert root_ids==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        assert all(path.read_bytes()==raw for path,raw in prior.items())
        for path,raw in case['legacy_bytes'].items():assert (root/path).read_bytes()==raw
        code,_,stderr=run_cli(root,api,'qualify06-rerun',config)
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert result_path.read_bytes()==result_raw
        assert all(path.read_bytes()==raw for path,raw in prior.items())
        for path,raw in case['legacy_bytes'].items():assert (root/path).read_bytes()==raw
        (root/'authored-optional06-observations.json').write_bytes(canonical(dict(
            authored_scope=AUTHORED,actual_vendor_imports=False,
            retained_failed05=True,held_imports06_completed=True,
            declared_optional_imports=AUTHORED_ROSTER06,actually_denied=['pynvml'],
            publication_exports=PUBLICATION_EXPORTS,candidate_and_noncandidate_inputs_unchanged=True,
            legacy_bytes_preserved=True,prepared_root_identities_unchanged=True,
            reentry_refused=True,stage_cleanup='owned fixture finally block')))
    assert len(os.listdir('/proc/self/fd'))==before_fds
