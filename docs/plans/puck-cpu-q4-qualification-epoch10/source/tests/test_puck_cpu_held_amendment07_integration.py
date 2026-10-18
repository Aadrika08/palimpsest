"""Authored06 exact-FD failure and07 Pillow-origin success, no installed vendors."""
import copy
import json
import os
import subprocess
import time

import pytest

from test_puck_cpu_held_amendment05 import PUBLICATION_EXPORTS
from test_puck_cpu_held_amendment05_integration import file_pin, publication05_fixture
from test_puck_cpu_held_amendment06_integration import AUTHORED_ROSTER06
from test_puck_cpu_held_amendment07 import PILLOW_ORIGINS
from test_puck_cpu_held_parent_integration import AUTHORED, ROOT, canonical, digest, load, run_cli


def test_authored07_binds_only_pillow_origins_after_real06_failure_and_independent_audits(tmp_path):
    auditor_path=ROOT/'scripts/audit_puck_cpu_held_runtime.py'
    auditor=load(auditor_path,'cpu_authored_pillow07_auditor')
    before_fds=len(os.listdir('/proc/self/fd'))
    with publication05_fixture(tmp_path,pillow_origins=True) as case:
        root,api,config,stage,prepbase=(case[k] for k in ('root','api','config','stage','prepbase'))
        config.update(kind='puck-cpu-held-runtime-allocation-v6',version=6,allocation_id=6,
            negative_imports=list(AUTHORED_ROSTER06))
        assert len(AUTHORED_ROSTER06)==18
        historical_dep=(prepbase/'payload/dependencies.json').read_bytes()
        root_ids=[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        old_candidate=root/config['inputs']['candidate']['path']
        old_candidate_raw=old_candidate.read_bytes()
        candidate_c=json.loads(old_candidate_raw)
        assert candidate_c['import_profile']['native_origins']==[]
        assert {row['name'] for row in candidate_c['module_paths'] if row['name'].startswith('PIL')}=={
            'PIL','PIL._imaging','PIL._imagingft'}
        inventory=json.loads((root/config['inputs']['inventory']['path']).read_bytes())
        elfs=[row for row in inventory['entries'] if row['path'].startswith(('PIL/','pillow.libs/')) and '.so' in row['path']]
        assert len(elfs)==4
        for row in elfs:
            raw=(root/api.SITE/row['path']).read_bytes()
            assert len(raw)==row['size_bytes'] and digest(raw)==row['sha256']

        code,stdout,stderr=run_cli(root,api,'qualify06',config)
        old_base=root/'runs/puck-cpu-held-qualification-06'
        failed_raw=(old_base/'result.json').read_bytes() if (old_base/'result.json').exists() else b''
        assert code==1,(code,stdout,stderr,failed_raw)
        failed=json.loads(failed_raw)
        assert stdout==failed_raw and failed['status']=='FAIL' and failed['held_four_imports_observed'] is False
        assert not (old_base/'baseline-after.json').exists()
        assert b'libpalimpsest_pillow_helper.so' in (old_base/'logs/stderr.log').read_bytes()
        old_config=root/'authored-qualify06-configuration.json'
        old_transport=root/'authored-qualify06-transport.json'
        with pytest.raises(ValueError):
            auditor.audit(old_config,digest(old_config.read_bytes()),old_transport,
                digest(old_transport.read_bytes()),deadline=time.monotonic()+30)
        consumed={p:p.read_bytes() for p in old_base.rglob('*') if p.is_file()}
        consumed.update({p:p.read_bytes() for p in root.glob('authored-qualify06-*') if p.is_file()})

        updated=copy.deepcopy(config)
        candidate_d=copy.deepcopy(candidate_c)
        candidate_d['import_profile']['native_origins']=copy.deepcopy(PILLOW_ORIGINS)
        path=root/'docs/authored/candidate-pillow07.json';path.write_bytes(canonical(candidate_d))
        updated['inputs']['candidate']=file_pin(root,path)
        updated.update(kind='puck-cpu-held-runtime-allocation-v7',version=7,allocation_id=7)
        assert updated['sources']==config['sources'] and updated['negative_imports']==config['negative_imports']
        assert {role for role in config['inputs'] if config['inputs'][role]!=updated['inputs'][role]}=={'candidate'}
        assert updated['preparation_acceptance']==config['preparation_acceptance']
        code,stdout,stderr=run_cli(root,api,'qualify07',updated)
        base=root/'runs/puck-cpu-held-qualification-07';result_path=base/'result.json'
        result_raw=result_path.read_bytes() if result_path.exists() else b''
        assert code==0,(code,stdout,stderr,result_raw)
        result=json.loads(result_raw)
        assert stdout==result_raw
        assert (result['kind'],result['version'],result['allocation_id'],result['status'])==(
            'puck-cpu-held-runtime-outcome-v7',7,7,'imports_completed')
        worker=json.loads((base/'logs/stdout.log').read_bytes())
        assert worker['expected_missing_imports']==AUTHORED_ROSTER06 and worker['denied_imports']==[]
        assert worker['dependencies']['native_origin_policies']=={row['name']:row['policy'] for row in PILLOW_ORIGINS}
        assert worker['dependencies']['published_export_modules']==[
            {key:value for key,value in row.items() if key!='class_binding'} for row in PUBLICATION_EXPORTS]
        assert [(row['name'],row['version']) for row in worker['entry_result']['imports']]==list(api.VERSIONS.items())
        current_dep=(base/'control/dependencies.json').read_bytes()
        assert current_dep!=historical_dep
        assert json.loads(current_dep)['roots']==json.loads(historical_dep)['roots']
        registration=json.loads((base/'control/worker-registration.json').read_bytes())
        assert registration['qualification']['version']==3
        assert registration['qualification']['negative_imports']==AUTHORED_ROSTER06
        assert registration['source_files']==[row for row in updated['sources'] if row['path'] in api.WORKER_SOURCES]
        assert registration['dependencies']['sha256']==digest(current_dep)
        for row in registration['source_files']:
            raw=(base/'worker-source'/row['path']).read_bytes()
            assert len(raw)==row['size_bytes'] and digest(raw)==row['sha256']

        configuration=root/'authored-qualify07-configuration.json'
        transport=root/'authored-qualify07-transport.json'
        count=len(os.listdir('/proc/self/fd'))
        report=auditor.audit(configuration,digest(configuration.read_bytes()),transport,
            digest(transport.read_bytes()),deadline=time.monotonic()+30)
        assert len(os.listdir('/proc/self/fd'))==count
        assert (report['kind'],report['version'],report['allocation_id'],report['status'])==(
            'puck-cpu-held-runtime-independent-audit-v7',7,7,'PASS')
        assert report['historical_dependencies_sha256']==digest(historical_dep)
        assert report['current_dependencies_sha256']==report['dependencies_sha256']==digest(current_dep)
        assert report['historical_candidate_sha256']==case['prepared']['inputs']['candidate']['sha256']
        assert report['current_candidate_sha256']==updated['inputs']['candidate']['sha256']
        (root/'authored-pillow07-api-audit.json').write_bytes(canonical(report))
        published=root/'authored-pillow07-cli-audit.json'
        command=[api.PYTHON,'-I','-S','-B',str(auditor_path),'--configuration',str(configuration),
            '--sha256',digest(configuration.read_bytes()),'--transport',str(transport),
            '--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
        started=time.monotonic()
        process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
            env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
        channels={}
        for channel,raw in (('stdout',process.stdout),('stderr',process.stderr)):
            target=root/('authored-pillow07-cli-audit.'+channel);target.write_bytes(raw)
            channels[channel]=dict(path=target.name,size_bytes=len(raw),sha256=digest(raw))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        cli_report=json.loads(process.stdout)
        assert cli_report['status']=='PASS' and cli_report['version']==7
        assert cli_report['auditor_source_sha256']==digest(auditor_path.read_bytes())
        (root/'authored-pillow07-cli-audit-transport.json').write_bytes(canonical(dict(
            kind='authored-cpu-held-auditor-cli-transport-v1',authored_scope=AUTHORED,
            command=command,observed_returncode=process.returncode,
            elapsed_seconds=time.monotonic()-started,**channels)))
        for outcome in (case['prepared'],failed,result,report,cli_report):
            assert all(outcome[key]==value for key,value in api.CLAIMS.items())
            assert outcome['closure']['active_children']==outcome['closure']['active_non_main_threads']==[]
            assert outcome['closure']['fd_count_before']==outcome['closure']['fd_count_after']
        assert old_candidate.read_bytes()==old_candidate_raw
        assert (prepbase/'payload/dependencies.json').read_bytes()==historical_dep
        assert root_ids==[(p.stat().st_dev,p.stat().st_ino) for p in sorted((stage/'inputs').iterdir())]
        assert all(path.read_bytes()==raw for path,raw in consumed.items())
        for name,raw in case['legacy_bytes'].items():assert (root/name).read_bytes()==raw
        code,_,stderr=run_cli(root,api,'qualify07-rerun',updated)
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert result_path.read_bytes()==result_raw
        assert all(path.read_bytes()==raw for path,raw in consumed.items())
        (root/'authored-pillow07-observations.json').write_bytes(canonical(dict(
            authored_scope=AUTHORED,actual_vendor_imports=False,authored_package_elfs=elfs,
            retained_failed06=True,held_imports07_completed=True,native_origins=PILLOW_ORIGINS,
            declared_actual_negative_import_count=19,authored_negative_imports=AUTHORED_ROSTER06,
            legacy_bytes_preserved=True,prepared_root_identities_unchanged=True,
            reentry_refused=True,stage_cleanup='owned fixture finally block')))
    assert len(os.listdir('/proc/self/fd'))==before_fds
