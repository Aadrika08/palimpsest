"""Independent CPU auditor against real CLI output from AUTHORED modules only.

These tests do not accept the installed vendors or authorize a real allocation.
"""
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time

import pytest

from test_puck_cpu_held_parent_integration import (
    AUTHORED, ROOT, canonical, digest, load, project, run_cli,
)


AUDITOR=ROOT/'scripts/audit_puck_cpu_held_runtime.py'


def test_actual_authored_prepare_qualify_and_independent_audit(tmp_path):
    assert AUDITOR.is_file(), 'Independent CPU held-runtime auditor is not implemented'
    auditor=load(AUDITOR,'cpu_authored_independent_auditor')
    assert tmp_path.resolve().is_relative_to((ROOT/'runs').resolve()), 'Use a persistent runs/ pytest basetemp, outside /tmp'
    root,api,inputs,sources=project(tmp_path)
    stage=Path('/tmp')/('palimpsest-puck-cpu-held-authored-'+secrets.token_hex(12))
    assert not stage.exists()
    reports={}

    def audit_phase(phase):
        configuration=root/('authored-'+phase+'-configuration.json')
        transport=root/('authored-'+phase+'-transport.json')
        before=len(os.listdir('/proc/self/fd'))
        try:
            return auditor.audit(configuration,digest(configuration.read_bytes()),
                transport,digest(transport.read_bytes()),deadline=time.monotonic()+120)
        finally:
            assert len(os.listdir('/proc/self/fd'))==before

    try:
        config=api.configuration_template(phase='prepare',root=str(root),stage_parent=str(stage),
            sources=sources,inputs=inputs,negative_imports=['org'])
        code,stdout,stderr=run_cli(root,api,'prepare',config)
        result_path=root/api.OUTPUTS['prepare']/'result.json'
        retained=result_path.read_bytes() if result_path.exists() else b''
        assert code==0,(code,stdout,stderr,retained)
        prepared=json.loads(retained)
        assert json.loads(stdout)==prepared and prepared['status']=='prepared'
        assert stage.is_dir()
        identities=[(stage/'inputs'/('root-'+str(i).zfill(4))).stat() for i in range(4)]
        reports['prepare']=audit_phase('prepare')
        assert reports['prepare']['status']=='PASS'
        (root/'authored-prepare-independent-audit.json').write_bytes(canonical(reports['prepare']))
        assert (stage/'inputs/root-0000/numpy.py').is_file()

        # Exercise the real auditor CLI's resource limits, alarm, exclusive
        # publication, final flush and normal external return on this same tree.
        configuration=root/'authored-prepare-configuration.json'
        transport=root/'authored-prepare-transport.json'
        audit_output=root/'authored-prepare-audit-cli.json'
        command=[api.PYTHON,'-I','-S','-B',str(AUDITOR),'--configuration',str(configuration),
            '--sha256',digest(configuration.read_bytes()),'--transport',str(transport),
            '--transport-sha256',digest(transport.read_bytes()),'--output',str(audit_output)]
        started=time.monotonic()
        process=subprocess.run(command,cwd=root,env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'),capture_output=True,timeout=30)
        elapsed=time.monotonic()-started;channels={}
        for name,payload in (('stdout',process.stdout),('stderr',process.stderr)):
            leaf='authored-prepare-audit-cli.'+name;(root/leaf).write_bytes(payload)
            channels[name]=dict(path=leaf,size_bytes=len(payload),sha256=digest(payload))
        (root/'authored-prepare-audit-cli-transport.json').write_bytes(canonical(dict(
            kind='authored-cpu-held-auditor-cli-transport-v1',authored_scope=AUTHORED,command=command,
            observed_returncode=process.returncode,elapsed_seconds=elapsed,**channels)))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==audit_output.read_bytes()
        published=json.loads(process.stdout);assert published['status']=='PASS'
        assert published['auditor_source_sha256']==digest(AUDITOR.read_bytes())
        assert published['closure']['fd_count_before']==published['closure']['fd_count_after']
        assert published['closure']['active_children']==published['closure']['active_non_main_threads']==[]

        preparation=dict(path=str(result_path.relative_to(root)),size_bytes=len(retained),sha256=digest(retained))
        config=api.configuration_template(phase='qualify',root=str(root),stage_parent=str(stage),
            sources=sources,inputs=inputs,negative_imports=['org'],preparation=preparation)
        code,stdout,stderr=run_cli(root,api,'qualify',config)
        final_path=root/api.OUTPUTS['qualify']/'result.json'
        final_raw=final_path.read_bytes() if final_path.exists() else b''
        assert code==0,(code,stdout,stderr,final_raw)
        final=json.loads(final_raw)
        assert json.loads(stdout)==final and final['status']=='imports_completed'
        reports['qualify']=audit_phase('qualify')
        (root/'authored-qualify-independent-audit.json').write_bytes(canonical(reports['qualify']))
        for report in reports.values():
            assert report['status']=='PASS'
            assert all(report[k] is False for k in api.CLAIMS if k!='qualification_claims')
            assert report['qualification_claims']==[]
        for i,before in enumerate(identities):
            after=(stage/'inputs'/('root-'+str(i).zfill(4))).stat()
            assert (before.st_dev,before.st_ino)==(after.st_dev,after.st_ino)

        # Rebind all enclosing byte hashes, so this probes the independent
        # semantic support-source proof rather than a trivial digest mismatch.
        worker_path=root/api.OUTPUTS['qualify']/'logs/stdout.log'
        stdout_path=root/'authored-qualify-cli.stdout'
        transport_path=root/'authored-qualify-transport.json'
        originals={p:p.read_bytes() for p in (worker_path,final_path,stdout_path,transport_path)}
        try:
            changed=json.loads(originals[worker_path]);changed['loaded_modules']=[]
            worker_raw=canonical(changed);worker_path.write_bytes(worker_raw)
            changed_final=json.loads(final_raw);changed_final['worker_stdout_sha256']=digest(worker_raw)
            changed_final_raw=canonical(changed_final);final_path.write_bytes(changed_final_raw);stdout_path.write_bytes(changed_final_raw)
            changed_transport=json.loads(originals[transport_path]);changed_transport['stdout'].update(size_bytes=len(changed_final_raw),sha256=digest(changed_final_raw))
            transport_path.write_bytes(canonical(changed_transport))
            with pytest.raises(ValueError,match='(?i)(loaded|source|support)'):
                audit_phase('qualify')
        finally:
            for path,raw in originals.items():path.write_bytes(raw)

        transport=root/'authored-qualify-transport.json'
        transport_raw=transport.read_bytes()
        changed=json.loads(transport_raw)
        assert changed['authored_scope']==AUTHORED
        changed['observed_returncode']=7
        try:
            transport.write_bytes(canonical(changed))
            with pytest.raises(ValueError,match='(?i)(transport|returncode|exit|observed)'):
                audit_phase('qualify')
        finally:
            transport.write_bytes(transport_raw)

        staged=stage/'inputs/root-0000/numpy.py'
        staged_raw=staged.read_bytes();mode=staged.stat().st_mode & 0o777
        try:
            staged.chmod(mode | 0o200)
            staged.write_bytes(bytes([staged_raw[0] ^ 1])+staged_raw[1:])
            staged.chmod(mode)
            assert staged.stat().st_size==len(staged_raw)
            with pytest.raises(ValueError,match='(?i)(hash|sha|bytes|content|changed)'):
                audit_phase('qualify')
        finally:
            staged.chmod(mode | 0o200);staged.write_bytes(staged_raw);staged.chmod(mode)
        assert final_path.read_bytes()==final_raw and result_path.read_bytes()==retained
        (root/'authored-audit-test-observations.json').write_bytes(canonical(dict(authored_scope=AUTHORED,prepare_audit='PASS',qualify_audit='PASS',auditor_cli_returncode=process.returncode,auditor_cli_stdout_matches_publication=True,missing_support_source_rejected=True,nonzero_transport_rejected=True,staged_byte_change_rejected=True,fd_counts_unchanged=True)))
        print(dict(authored_prepare_audit=reports['prepare']['status'],
            authored_qualify_audit=reports['qualify']['status'],
            nonzero_transport_rejected=True,staged_byte_change_rejected=True,actual_vendor_imports=False))
    finally:
        if stage.exists():
            assert stage.is_dir() and not stage.is_symlink()
            shutil.rmtree(stage)
            (root/'authored-stage-cleanup.json').write_bytes(canonical(dict(authored_scope=AUTHORED,owned_stage=str(stage),absent=not stage.exists())))
