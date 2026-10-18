"""AUTHORED fresh preparations 02/03 and their independent CLI audits; no installed vendors.

Mirrors the preparation01 fixtures with separately named allocations. Current
sources prepare once into a new private stage; the auditor whose bytes the
parent pins for that preparation accepts it through an externally observed CLI.
Preparation02 was accepted by the retained 04192a3b auditor; preparation03 by
the retained 6292b550 auditor.
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

import pytest

from test_puck_cpu_held_amendment05 import PUBLICATION_EXPORTS
from test_puck_cpu_held_amendment05_integration import file_pin, source_pins
from test_puck_cpu_held_amendment07 import PILLOW_ORIGINS
from test_puck_cpu_held_parent_integration import AUTHORED, ROOT, canonical, digest, load, project, run_cli


PARENT='scripts/qualify_puck_cpu_held_runtime.py'
AUDITOR='scripts/audit_puck_cpu_held_runtime.py'
HISTORICAL_AUDITOR=ROOT/'tests/historical/audit_puck_cpu_held_runtime-04192a3b.py'
# The auditor bytes that accepted the real preparation03 (epoch14 binds them).
PREPARATION03_AUDITOR=ROOT/'tests/historical/audit_puck_cpu_held_runtime-6292b550.py'
OUTPUT={12:'runs/puck-cpu-held-preparation-02',13:'runs/puck-cpu-held-preparation-03'}
LABEL={12:'prepare02',13:'prepare03'}


def auditor_pin(api,allocation):
    return api.PREPARATION02_AUDITOR_SHA256 if allocation==12 else api.PREPARATION03_AUDITOR_SHA256


def prepare_and_audit(root,api,inputs,allocation,stage):
    """One authored preparation allocation plus its externally observed independent audit."""
    auditor_path=root/AUDITOR
    auditor_path.write_bytes((HISTORICAL_AUDITOR if allocation==12 else PREPARATION03_AUDITOR).read_bytes())
    assert digest(auditor_path.read_bytes())==auditor_pin(api,allocation)!=api.LEGACY_AUDITOR_SHA256
    assert not os.path.lexists(stage)
    prepare=api.configuration_template(phase='prepare',root=str(root),stage_parent=str(stage),
        sources=source_pins(root,api),inputs=inputs,negative_imports=['org'])
    prepare.update(kind='puck-cpu-held-runtime-allocation-v'+str(allocation),version=allocation,allocation_id=allocation)
    label=LABEL[allocation]
    code,stdout,stderr=run_cli(root,api,label,prepare)
    prepbase=root/OUTPUT[allocation];result_path=prepbase/'result.json'
    prepared_raw=result_path.read_bytes() if result_path.exists() else b''
    assert code==0,(code,stdout,stderr,prepared_raw)
    prepared=json.loads(prepared_raw)
    assert stdout==prepared_raw and prepared['status']=='prepared'
    configuration=root/('authored-'+label+'-configuration.json')
    transport=root/('authored-'+label+'-transport.json')
    published=root/('docs/authored/'+label+'-audit.json')
    command=[api.PYTHON,'-I','-S','-B',str(auditor_path),
        '--configuration',str(configuration),'--sha256',digest(configuration.read_bytes()),
        '--transport',str(transport),'--transport-sha256',digest(transport.read_bytes()),'--output',str(published)]
    started=time.monotonic()
    process=subprocess.run(command,cwd=root,capture_output=True,timeout=30,
        env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1'))
    channels={}
    for channel,raw in (('stdout',process.stdout),('stderr',process.stderr)):
        path=root/('authored-'+label+'-audit.'+channel);path.write_bytes(raw)
        channels[channel]=dict(path=str(path),size_bytes=len(raw),sha256=digest(raw))
    assert process.returncode==0,(process.returncode,process.stdout,process.stderr)
    assert process.stdout==published.read_bytes() and process.stderr==b''
    audit=json.loads(process.stdout)
    cli=root/('docs/authored/'+label+'-audit-cli.json')
    cli.write_bytes(canonical(dict(kind='externally-observed-cpu-auditor-cli-v1',
        command=command,observed_returncode=process.returncode,elapsed_seconds=time.monotonic()-started,
        published=dict(path=str(published),size_bytes=published.stat().st_size,sha256=digest(published.read_bytes())),**channels)))
    acceptance={key:file_pin(root,path) for key,path in dict(configuration=configuration,
        result=result_path,independent_audit=published,externally_observed_auditor_cli=cli).items()}
    return dict(allocation=allocation,stage=stage,prepare=prepare,prepared=prepared,prepared_raw=prepared_raw,
                prepbase=prepbase,audit=audit,acceptance=acceptance)


def candidate_d_inputs(root,inputs):
    candidate=json.loads((root/inputs['candidate']['path']).read_bytes())
    candidate['import_profile']['exports']=copy.deepcopy(PUBLICATION_EXPORTS)
    candidate['import_profile']['native_origins']=copy.deepcopy(PILLOW_ORIGINS)
    path=root/'docs/authored/candidate-v5epoch11.json';path.write_bytes(canonical(candidate))
    return dict(copy.deepcopy(inputs),candidate=file_pin(root,path))


@contextmanager
def authored_preparations(tmp_path,allocations,*,mutate_parent=None,**project_options):
    assert tmp_path.resolve().is_relative_to((ROOT/'runs').resolve()), 'Use persistent runs/ basetemp'
    root,api,inputs,_=project(tmp_path,autograd_publication=True,pillow_origins=True,stock_absence_probe=True,
                              **project_options)
    if mutate_parent is not None:
        path=root/PARENT;path.write_bytes(mutate_parent(path.read_bytes()))
        api=load(path,'cpu_authored_mutated_parent_'+secrets.token_hex(4))
    stages=[]
    try:
        cases={}
        for allocation in allocations:
            stage=Path('/tmp')/('palimpsest-puck-cpu-held-'+LABEL[allocation][-2:]+'-authored-'+secrets.token_hex(12))
            stages.append(stage);cases[allocation]=prepare_and_audit(root,api,inputs,allocation,stage)
        yield dict(root=root,api=api,inputs=inputs,updated_inputs=candidate_d_inputs(root,inputs),cases=cases)
    finally:
        for stage in stages:
            if os.path.lexists(stage):
                assert stage.is_dir() and not stage.is_symlink()
                shutil.rmtree(stage)
        (root/'authored-preparation-stage-cleanup.json').write_bytes(canonical(dict(
            authored_scope=AUTHORED,owned_stages=[str(s) for s in stages],
            absent=not any(os.path.lexists(s) for s in stages),actual_vendor_imports=False)))
        assert not any(os.path.lexists(s) for s in stages)


@contextmanager
def preparation_fixture(tmp_path,allocation):
    with authored_preparations(tmp_path,(allocation,)) as env:
        yield dict(env,**env['cases'][allocation])


def preparation02_fixture(tmp_path):
    return preparation_fixture(tmp_path,12)


def preparation03_fixture(tmp_path):
    return preparation_fixture(tmp_path,13)


@pytest.mark.parametrize('allocation',[12,13])
def test_authored_preparation_is_a_fresh_separately_audited_allocation(tmp_path,allocation):
    before=len(os.listdir('/proc/self/fd'))
    with preparation_fixture(tmp_path,allocation) as case:
        root,api,prepared,audit,stage=(case[k] for k in ('root','api','prepared','audit','stage'))
        assert (prepared['kind'],prepared['version'],prepared['allocation_id'],prepared['phase'])==(
            'puck-cpu-held-runtime-outcome-v'+str(allocation),allocation,allocation,'prepare')
        assert prepared['stage_parent']==str(stage) and prepared['held_four_imports_observed'] is False
        assert prepared['sources']==case['prepare']['sources'] and prepared['inputs']==case['inputs']
        assert case['prepare']['limits']==api.LIMITS['prepare'] and case['prepare']['limits']['normal_seconds']==180
        assert [r['root_index'] for r in prepared['staged_roots']]==[0,1,2,3]
        for row in prepared['staged_roots']:
            state=(stage/'inputs'/('root-'+str(row['root_index']).zfill(4))).stat()
            assert (state.st_dev,state.st_ino)==(row['device'],row['inode'])
        assert (audit['kind'],audit['version'],audit['allocation_id'],audit['status'],audit['phase'])==(
            'puck-cpu-held-runtime-independent-audit-v'+str(allocation),allocation,allocation,'PASS','prepare')
        assert audit['auditor_source_sha256']==auditor_pin(api,allocation)
        assert audit['evidence_scope']=='AUTHORED fixture only' and audit['result_sha256']==digest(case['prepared_raw'])
        assert audit['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
        assert prepared['closure']==dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5)
        assert all(audit[k]==v and prepared[k]==v for k,v in api.CLAIMS.items())
        transport=json.loads((root/('authored-'+LABEL[allocation]+'-transport.json')).read_bytes())
        assert transport['stdout']['path']=='authored-'+LABEL[allocation]+'-cli.stdout'
        for other in ('runs/puck-cpu-held-preparation-01',*(v for k,v in OUTPUT.items() if k!=allocation)):
            assert not (root/other).exists()
        assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-01')
        code,_,stderr=run_cli(root,api,LABEL[allocation]+'-rerun',case['prepare'])
        assert code!=0 and b'CPU allocation already reserved' in stderr
        assert (case['prepbase']/'result.json').read_bytes()==case['prepared_raw']
    assert len(os.listdir('/proc/self/fd'))==before
