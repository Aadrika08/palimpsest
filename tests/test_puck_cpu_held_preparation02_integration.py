"""AUTHORED fresh preparation02 and its independent CLI audit; no installed vendors.

Mirrors the preparation01 fixtures with a separately named allocation. Current
sources prepare once into a new private stage; the current independent auditor,
whose bytes the parent pins, accepts it through an externally observed CLI.
"""
import copy
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import time

from test_puck_cpu_held_amendment05 import PUBLICATION_EXPORTS
from test_puck_cpu_held_amendment05_integration import file_pin, source_pins
from test_puck_cpu_held_amendment07 import PILLOW_ORIGINS
from test_puck_cpu_held_parent_integration import AUTHORED, ROOT, canonical, digest, load, project, run_cli


OUTPUT02='runs/puck-cpu-held-preparation-02'
AUDITOR='scripts/audit_puck_cpu_held_runtime.py'


@contextmanager
def preparation02_fixture(tmp_path):
    assert tmp_path.resolve().is_relative_to((ROOT/'runs').resolve()), 'Use persistent runs/ basetemp'
    root,api,inputs,_=project(tmp_path,autograd_publication=True,pillow_origins=True,stock_absence_probe=True)
    auditor_path=root/AUDITOR;auditor_path.write_bytes((ROOT/AUDITOR).read_bytes())
    assert digest(auditor_path.read_bytes())==api.PREPARATION02_AUDITOR_SHA256!=api.LEGACY_AUDITOR_SHA256
    stage=Path('/tmp')/('palimpsest-puck-cpu-held-02-authored-'+secrets.token_hex(12))
    assert not os.path.lexists(stage)
    try:
        prepare=api.configuration_template(phase='prepare',root=str(root),stage_parent=str(stage),
            sources=source_pins(root,api),inputs=inputs,negative_imports=['org'])
        prepare.update(kind='puck-cpu-held-runtime-allocation-v12',version=12,allocation_id=12)
        code,stdout,stderr=run_cli(root,api,'prepare02',prepare)
        prepbase=root/OUTPUT02;result_path=prepbase/'result.json'
        prepared_raw=result_path.read_bytes() if result_path.exists() else b''
        assert code==0,(code,stdout,stderr,prepared_raw)
        prepared=json.loads(prepared_raw)
        assert stdout==prepared_raw and prepared['status']=='prepared'
        configuration=root/'authored-prepare02-configuration.json'
        transport=root/'authored-prepare02-transport.json'
        published=root/'docs/authored/preparation02-audit.json'
        command=[api.PYTHON,'-I','-S','-B',str(auditor_path),
            '--configuration',str(configuration),'--sha256',digest(configuration.read_bytes()),
            '--transport',str(transport),'--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
        started=time.monotonic()
        process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
            env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
        channels={}
        for channel,raw in (('stdout',process.stdout),('stderr',process.stderr)):
            path=root/('authored-preparation02-audit.'+channel);path.write_bytes(raw)
            channels[channel]=dict(path=str(path),size_bytes=len(raw),sha256=digest(raw))
        assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
        assert process.stdout==published.read_bytes() and process.stderr==b''
        audit=json.loads(process.stdout)
        cli=root/'docs/authored/preparation02-audit-cli.json'
        cli.write_bytes(canonical(dict(kind='externally-observed-cpu-auditor-cli-v1',
            command=command,observed_returncode=process.returncode,elapsed_seconds=time.monotonic()-started,
            published=dict(path=str(published),size_bytes=published.stat().st_size,sha256=digest(published.read_bytes())),**channels)))
        acceptance={key:file_pin(root,path) for key,path in dict(configuration=configuration,
            result=result_path,independent_audit=published,externally_observed_auditor_cli=cli).items()}
        candidate=json.loads((root/inputs['candidate']['path']).read_bytes())
        candidate['import_profile']['exports']=copy.deepcopy(PUBLICATION_EXPORTS)
        candidate['import_profile']['native_origins']=copy.deepcopy(PILLOW_ORIGINS)
        candidate_path=root/'docs/authored/candidate-v5epoch11.json';candidate_path.write_bytes(canonical(candidate))
        updated_inputs=dict(copy.deepcopy(inputs),candidate=file_pin(root,candidate_path))
        yield dict(root=root,api=api,inputs=inputs,updated_inputs=updated_inputs,stage=stage,prepare=prepare,
            prepared=prepared,prepared_raw=prepared_raw,prepbase=prepbase,audit=audit,acceptance=acceptance)
    finally:
        if os.path.lexists(stage):
            assert stage.is_dir() and not stage.is_symlink()
            shutil.rmtree(stage)
        (root/'authored-preparation02-stage-cleanup.json').write_bytes(canonical(dict(
            authored_scope=AUTHORED,owned_stage=str(stage),absent=not os.path.lexists(stage),actual_vendor_imports=False)))
        assert not os.path.lexists(stage)


def test_authored_preparation02_is_a_fresh_separately_audited_allocation(tmp_path):
    before=len(os.listdir('/proc/self/fd'))
    with preparation02_fixture(tmp_path) as case:
        root,api,prepared,audit,stage=(case[k] for k in ('root','api','prepared','audit','stage'))
        assert (prepared['kind'],prepared['version'],prepared['allocation_id'],prepared['phase'])==(
            'puck-cpu-held-runtime-outcome-v12',12,12,'prepare')
        assert prepared['stage_parent']==str(stage) and prepared['held_four_imports_observed'] is False
        assert prepared['sources']==case['prepare']['sources'] and prepared['inputs']==case['inputs']
        assert [r['root_index'] for r in prepared['staged_roots']]==[0,1,2,3]
        for row in prepared['staged_roots']:
            state=(stage/'inputs'/('root-'+str(row['root_index']).zfill(4))).stat()
            assert (state.st_dev,state.st_ino)==(row['device'],row['inode'])
        assert (audit['kind'],audit['version'],audit['allocation_id'],audit['status'],audit['phase'])==(
            'puck-cpu-held-runtime-independent-audit-v12',12,12,'PASS','prepare')
        assert audit['auditor_source_sha256']==api.PREPARATION02_AUDITOR_SHA256
        assert audit['evidence_scope']=='AUTHORED fixture only' and audit['result_sha256']==digest(case['prepared_raw'])
        assert audit['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
        assert prepared['closure']==dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5)
        assert all(audit[k]==v and prepared[k]==v for k,v in api.CLAIMS.items())
        transport=json.loads((root/'authored-prepare02-transport.json').read_bytes())
        assert transport['stdout']['path']=='authored-prepare02-cli.stdout'
        assert not (root/'runs/puck-cpu-held-preparation-01').exists()
        assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-01')
        code,_,stderr=run_cli(root,api,'prepare02-rerun',case['prepare'])
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert (case['prepbase']/'result.json').read_bytes()==case['prepared_raw']
        # A preparation01 identity cannot claim the preparation02 stage family's evidence.
        legacy=dict(case['prepare'],kind='puck-cpu-held-runtime-allocation-v1',version=1,allocation_id=1)
        auditor=load(root/AUDITOR,'cpu_authored_preparation02_auditor')
        assert auditor.allocation_output(legacy)=='runs/puck-cpu-held-preparation-01'
    assert len(os.listdir('/proc/self/fd'))==before
