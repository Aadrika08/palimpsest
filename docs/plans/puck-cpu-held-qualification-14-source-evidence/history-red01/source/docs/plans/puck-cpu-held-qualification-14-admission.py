"""Fixed DATA-ONLY pre14 admission; no allocation, qualification or vendor import."""
import datetime
import importlib.machinery
import hashlib
import shutil
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import types

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
AUDITOR=ROOT/'docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'
AUDITOR_SHA='01bc2c99634cb3ec2e7bfc92f4fc96b219e07c8a5ea10351227a5cfb1181d4cf'
OUTPUT=Path('/tmp/palimpsest-puck-cpu-held-qualification-14-admission-01.json')
CONFIGURATION=ROOT/'docs/plans/puck-cpu-held-qualification-14.json'
CONFIG_SHA='32f8aeb553a534b463f2b7a594ca721273fa251ae743256d6fe23efa74f6bed2'
AUDITOR_CURRENT_SHA='6292b55088a8b4bfb60b2d65688970cd47e6a76e207f771c3d695dd463bae3cd'
OBS_AUDITOR_SHA='be7e1321356c554750baa6e0982dc939a23546eca1574b8f5f68b2bbdec3afa4'
PREP_SHA='1acfb10b40d561b8e56c96f4cd0d59ee1f00b4d0a14f62c80ffe64e22e1de3ed'
RESULT_SHA='4ef13965e6f312a0bcdef9c49e57190f6a9526988f20f1959357bcc31400e0d4'
DEP_SHA='25ea4e912919116b3196b8a8ed537f5dde02f40a35c295d97fe0c0509d67277f'


HISTORICAL07_JSON={
    'runs/puck-cpu-held-qualification-07-external-cli-transport.json':'9509cbbff66603e5906c57f72950fcc77f600d4dbcffb611462506a58360aca7',
    'runs/puck-cpu-held-qualification-07/supervision.json':'92da80ef71f86b3fd921c9d3febd35a1c9e1e795ca5b013435ef3cce61b35d61',
    'docs/reports/puck-cpu-held-qualification-07/observations/palimpsest-puck-cpu-held-qualification-07-audit-01.json':'adb464cdc5ec9d55676bad8524bb6fe9f98143e7914a2ed1344408a8a1988aea',
    'docs/reports/puck-cpu-held-qualification-07/external/palimpsest-held07-observer-external.json':'928bdc0f3090696bf9976e3b411cdb295b13f86c0e5c06ea9285c57613835857',
    'docs/reports/puck-cpu-held-qualification-07/external/palimpsest-held07-audit-external.json':'90d9cf0f63f884bf6047aa0487543c46e755135506bef554897d08157a6d09d3',
}


def hold_manifest(held,pins,raw_paths):
    raw_paths=set(raw_paths)
    for epoch in ('07','08','09','10'):
        raw_paths.update('runs/puck-cpu-held-qualification-'+epoch+'-external-cli.'+name for name in ('stdout','stderr'))
        raw_paths.update('runs/puck-cpu-held-qualification-'+epoch+'/logs/'+name+'.log' for name in ('stdout','stderr'))
    for row in pins:held.file(ROOT/row['path'],row,16*1024**2,raw=row['path'] in raw_paths)


def check_consumed07(held):
    rows=[]
    for path,expected in HISTORICAL07_JSON.items():
        value,raw=held.json(ROOT/path,maximum=64*1024)
        assert hashlib.sha256(raw).hexdigest()==expected,path
        rows.append(value)
    transport,supervision,refusal,outer_observer,outer_audit=rows
    config_sha='1ed4b198a38512c751cca43e11fdb1cd00e7683031be545e6ccd12016555ee60'
    transport_sha=HISTORICAL07_JSON['runs/puck-cpu-held-qualification-07-external-cli-transport.json']
    assert transport['kind']=='puck-cpu-held-cli-transport-v1' and transport['phase']=='qualify'
    assert transport['configuration_sha256']==config_sha and transport['observed_returncode']==1 and transport['timed_out'] is False
    assert 0<transport['elapsed_seconds']<210
    assert transport['command']==[str(Path(sys.executable).resolve()),'-I','-S','-B',str(ROOT/'scripts/qualify_puck_cpu_held_runtime.py'),
        '--configuration',str(ROOT/'docs/plans/puck-cpu-held-qualification-07.json'),'--sha256',config_sha]
    for name in ('stdout','stderr'):
        row=transport[name]
        assert row['path']=='runs/puck-cpu-held-qualification-07-external-cli.'+name
        raw=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
        assert raw==b'' if name=='stdout' else b'CPU allocation normal return deadline' in raw
    assert supervision['status']=='failed' and supervision['failure']=='normal-return deadline' and supervision['returncode']==-15
    assert supervision['process_scope']=='descendants' and supervision['matching_survivors']==[]
    assert supervision['tracked_processes']==[dict(pid=3798021,start_ticks=53913806),dict(pid=3798022,start_ticks=53913806),dict(pid=3798023,start_ticks=53913807)]
    for name in ('stdout','stderr'):
        assert held.file(ROOT/('runs/puck-cpu-held-qualification-07/logs/'+name+'.log'),maximum=16*1024**2,raw=True)==b''
    assert refusal['kind']=='puck-cpu-held-runtime-independent-audit-v1' and refusal['version']==1 and refusal['status']=='FAIL'
    assert refusal['configuration_sha256']==config_sha and refusal['transport_sha256']==transport_sha
    assert refusal['auditor_source_sha256']=='420c3d6f3b8c7ae799732184507e84177a546b74573fccf1f32728dbfc64440d'
    assert refusal['error']=='Normal external transport exit required' and refusal['qualification_claims']==[]
    assert all(refusal[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    for phase,value,stdout_sha,budget in [('observer',outer_observer,transport_sha,240),('audit',outer_audit,
            HISTORICAL07_JSON['docs/reports/puck-cpu-held-qualification-07/observations/palimpsest-puck-cpu-held-qualification-07-audit-01.json'],145)]:
        assert value['kind']=='puck-cpu-held07-external-transport-v1' and value['phase']==phase
        assert value['returncode']==1 and value['normal_exit'] is True and value['timed_out'] is False
        assert 0<value['elapsed_seconds']<budget and value['stdout']['sha256']==stdout_sha and value['stderr']['size_bytes']==0
        assert value['implicit_retry'] is False and value['runtime_qualified'] is False and value['study_authorized'] is False
    missing=['runs/puck-cpu-held-qualification-07/'+name for name in ('result.json','baseline-after.json')]
    assert all(not os.path.lexists(ROOT/path) for path in missing)
    return dict(status='FAILED_CONSUMED',configuration_sha256=config_sha,transport_sha256=transport_sha,
        parent_closure_receipt=False,completed_four_import_receipt=False,missing_receipts=missing,
        supervision='failed normal-return deadline; sampled matching_survivors empty',independent_audit_status='FAIL')


HISTORICAL08_JSON={
    'docs/plans/puck-cpu-held-qualification-08.json':'67076970caffe64b6162c4344f11d943b620dd2e0fb43ace72e39f508fa7ee60',
    'runs/puck-cpu-held-qualification-08-external-cli-transport.json':'d80f60a10cf611c660e5bda25bf6f055c49415686681db33ca6ae44f868841b4',
    'runs/puck-cpu-held-qualification-08/supervision.json':'2363163d5926cf8d8ce68c0ea9290671cd633e369cc10c1f5d3261b91e30cdb4',
    'docs/reports/puck-cpu-held-qualification-08/observations/palimpsest-puck-cpu-held-qualification-08-audit-01.json':'93fb936dcf82bcf46a592026e8744c5900bf5bd9b283465d5e5dfad13d346ba9',
    'docs/reports/puck-cpu-held-qualification-08/external/palimpsest-held08-observer-external.json':'e3dcff1660b44d0b9c940ea1b65782a484443032d2f79d9cb2c611b12726b8f6',
    'docs/reports/puck-cpu-held-qualification-08/external/palimpsest-held08-audit-external.json':'fa41490d8f91c2ea865d73ee4e668bd97dbd50ab85318a446680000f5a12595d',
}


def check_consumed08(held):
    rows=[]
    for path,expected in HISTORICAL08_JSON.items():
        value,raw=held.json(ROOT/path,maximum=64*1024)
        assert hashlib.sha256(raw).hexdigest()==expected,path
        rows.append(value)
    config,transport,supervision,refusal,outer_observer,outer_audit=rows
    config_sha=HISTORICAL08_JSON['docs/plans/puck-cpu-held-qualification-08.json']
    transport_sha=HISTORICAL08_JSON['runs/puck-cpu-held-qualification-08-external-cli-transport.json']
    held.file(ROOT/'runs/puck-cpu-held-qualification-08/configuration.json',
        dict(size_bytes=8985,sha256=config_sha),64*1024)
    assert config['kind']=='puck-cpu-held-runtime-allocation-v8' and config['phase']=='qualify'
    assert type(config['version']) is int and config['version']==8 and type(config['allocation_id']) is int and config['allocation_id']==8
    assert config['root']==str(ROOT) and config['limits']['normal_seconds']==180 and config['limits']['min_available_ram_bytes']==2<<30
    assert transport['kind']=='puck-cpu-held-cli-transport-v1' and transport['phase']=='qualify'
    assert transport['configuration_sha256']==config_sha and transport['observed_returncode']==1 and transport['timed_out'] is False
    assert 0<transport['elapsed_seconds']<210
    python=str(Path(sys.executable).resolve())
    parent_command=[python,'-I','-S','-B',str(ROOT/'scripts/qualify_puck_cpu_held_runtime.py'),
        '--configuration',str(ROOT/'docs/plans/puck-cpu-held-qualification-08.json'),'--sha256',config_sha]
    assert transport['command']==parent_command
    for name in ('stdout','stderr'):
        row=transport[name]
        assert row['path']=='runs/puck-cpu-held-qualification-08-external-cli.'+name
        raw=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
        assert raw==b'' if name=='stdout' else b'CPU allocation normal return deadline' in raw
    assert supervision['status']=='failed' and supervision['failure']=='normal-return deadline' and supervision['returncode']==-15
    assert supervision['process_scope']=='descendants' and supervision['matching_survivors']==[]
    assert supervision['tracked_processes']==[dict(pid=3996069,start_ticks=54384185),dict(pid=3996070,start_ticks=54384185),dict(pid=3996071,start_ticks=54384186)]
    empty_sha='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    assert held.file(ROOT/'runs/puck-cpu-held-qualification-08/logs/stdout.log',
        dict(size_bytes=0,sha256=empty_sha),16*1024**2,raw=True)==b''
    diagnostic_raw=held.file(ROOT/'runs/puck-cpu-held-qualification-08/logs/stderr.log',
        dict(size_bytes=1469,sha256='12fd091b446124bfd8c40a8ef0b962b81b7e3bbc0c94b716736cc3fddf34ca3f'),16*1024**2,raw=True)
    # This authenticates retained historical bytes, not marker authorship,
    # completeness, import/version acceptance, work location, timing or cause.
    # No optional marker from the prospective09 invocation is required here.
    diagnostics=[json.loads(line) for line in diagnostic_raw.splitlines()]
    assert refusal['kind']=='puck-cpu-held-runtime-independent-audit-v1' and refusal['version']==1 and refusal['status']=='FAIL'
    assert refusal['configuration_sha256']==config_sha and refusal['transport_sha256']==transport_sha
    assert refusal['auditor_source_sha256']=='0406bfa94f6b230fca440d57f65e5d429a30d70d054e2cdd29bafb0da1ca2b35'
    assert refusal['error']=='Normal external transport exit required' and refusal['qualification_claims']==[]
    assert all(refusal[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    observer_command=[python,'-I','-S','-B',str(ROOT/'scripts/observe_puck_cpu_held_allocation.py'),*parent_command[5:]]
    audit_command=[python,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),*parent_command[5:],
        '--transport',str(ROOT/'runs/puck-cpu-held-qualification-08-external-cli-transport.json'),
        '--transport-sha256',transport_sha,'--output','/tmp/palimpsest-puck-cpu-held-qualification-08-audit-01.json']
    for phase,value,stdout_sha,stdout_size,budget,command in [
            ('observer',outer_observer,transport_sha,951,240,observer_command),
            ('audit',outer_audit,HISTORICAL08_JSON['docs/reports/puck-cpu-held-qualification-08/observations/palimpsest-puck-cpu-held-qualification-08-audit-01.json'],616,145,audit_command)]:
        assert value['kind']=='puck-cpu-held08-external-transport-v1' and value['phase']==phase
        assert value['returncode']==1 and value['normal_exit'] is True and value['timed_out'] is False
        assert value['command']==command and value['cwd']==str(ROOT) and value['environment']==environment
        assert value['external_deadline_seconds']==budget and 0<value['elapsed_seconds']<budget
        assert value['stdout']['sha256']==stdout_sha and value['stdout']['size_bytes']==stdout_size
        assert value['stderr']['sha256']==empty_sha and value['stderr']['size_bytes']==0
        assert value['implicit_retry'] is False and value['runtime_qualified'] is False and value['study_authorized'] is False
    missing=['runs/puck-cpu-held-qualification-08/'+name for name in ('result.json','baseline-after.json')]
    assert all(not os.path.lexists(ROOT/path) for path in missing)
    return dict(status='FAILED_CONSUMED',configuration_sha256=config_sha,transport_sha256=transport_sha,
        parent_closure_receipt=False,completed_four_import_receipt=False,missing_receipts=missing,
        supervision='failed normal-return deadline; sampled matching_survivors empty',independent_audit_status='FAIL',
        post_failure_full_payload_custody=False,
        diagnostic_stream=dict(records=len(diagnostics),last_record=diagnostics[-1],
            scope='retained unauthenticated optional stderr bytes only; no completeness, cause or acceptance authority'))


HISTORICAL09_JSON={'docs/plans/puck-cpu-held-qualification-09.json': '2c441b2465c86baf2982a5c023ce5923c1c144bd5789576807ffee6f19beb6c0', 'runs/puck-cpu-held-qualification-09-external-cli-transport.json': '7e8396f9b44a83980459b5f59e2b544b7e02fc7da431e5a0e99e13b42b1feec1', 'runs/puck-cpu-held-qualification-09/supervision.json': '7b05d199e19f7906d3755571752be323fcd96464dcde54883901aba54bafa0bc', 'docs/reports/puck-cpu-held-qualification-09/observations/palimpsest-puck-cpu-held-qualification-09-audit-01.json': 'c2b6b6e7c8e4c93bb79e906a751038295b2135ad8551f029f3f18fdc8d21d009', 'docs/reports/puck-cpu-held-qualification-09/external/palimpsest-held09-observer-external.json': 'b11b02d3af9047d16353d25994989bc6766425255261bd99aac47f5d272a0338', 'docs/reports/puck-cpu-held-qualification-09/external/palimpsest-held09-audit-external.json': 'dca21e8573bc5e4b9a8d89ff580c0e85a482c5c3be1f51711a0e977c2ebcd78f'}


def check_consumed09(held):
    rows=[]
    for path,expected in HISTORICAL09_JSON.items():
        value,raw=held.json(ROOT/path,maximum=64*1024)
        assert hashlib.sha256(raw).hexdigest()==expected,path
        rows.append(value)
    config,transport,supervision,refusal,outer_observer,outer_audit=rows
    config_sha=HISTORICAL09_JSON['docs/plans/puck-cpu-held-qualification-09.json']
    transport_sha=HISTORICAL09_JSON['runs/puck-cpu-held-qualification-09-external-cli-transport.json']
    held.file(ROOT/'runs/puck-cpu-held-qualification-09/configuration.json',
        dict(size_bytes=8985,sha256=config_sha),64*1024)
    assert config['kind']=='puck-cpu-held-runtime-allocation-v9' and config['phase']=='qualify'
    assert type(config['version']) is int and config['version']==9 and type(config['allocation_id']) is int and config['allocation_id']==9
    assert config['root']==str(ROOT) and config['limits']['normal_seconds']==180 and config['limits']['min_available_ram_bytes']==2<<30
    assert transport['kind']=='puck-cpu-held-cli-transport-v1' and transport['phase']=='qualify'
    assert transport['configuration_sha256']==config_sha and transport['observed_returncode']==1 and transport['timed_out'] is False
    assert 0<transport['elapsed_seconds']<210
    python=str(Path(sys.executable).resolve())
    parent_command=[python,'-I','-S','-B',str(ROOT/'scripts/qualify_puck_cpu_held_runtime.py'),
        '--configuration',str(ROOT/'docs/plans/puck-cpu-held-qualification-09.json'),'--sha256',config_sha]
    assert transport['command']==parent_command
    for name in ('stdout','stderr'):
        row=transport[name]
        assert row['path']=='runs/puck-cpu-held-qualification-09-external-cli.'+name
        raw=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
        assert raw==b'' if name=='stdout' else b'CPU allocation normal return deadline' in raw
    assert supervision['status']=='failed' and supervision['failure']=='normal-return deadline' and supervision['returncode']==-15
    assert supervision['process_scope']=='descendants' and supervision['matching_survivors']==[]
    assert supervision['tracked_processes']==[dict(pid=104005,start_ticks=55289090),dict(pid=104006,start_ticks=55289091),dict(pid=104007,start_ticks=55289092)]
    empty_sha='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    assert held.file(ROOT/'runs/puck-cpu-held-qualification-09/logs/stdout.log',
        dict(size_bytes=0,sha256=empty_sha),16*1024**2,raw=True)==b''
    diagnostic_raw=held.file(ROOT/'runs/puck-cpu-held-qualification-09/logs/stderr.log',
        dict(size_bytes=11086,sha256='c548022a96e5cc22dfb8bbd9d9bb5c0c0ef446dc5a662401dc3e91bc06714a61'),16*1024**2,raw=True)
    # This authenticates retained historical bytes, not marker authorship,
    # completeness, import/version acceptance, work location, timing or cause.
    # No optional marker from the prospective09 invocation is required here.
    diagnostics=[json.loads(line) for line in diagnostic_raw.splitlines()]
    assert refusal['kind']=='puck-cpu-held-runtime-independent-audit-v1' and refusal['version']==1 and refusal['status']=='FAIL'
    assert refusal['configuration_sha256']==config_sha and refusal['transport_sha256']==transport_sha
    assert refusal['auditor_source_sha256']=='dffcec25696948da18b18abda32dae764fa933a1175c622f45d33a3bca27d234'
    assert refusal['error']=='Normal external transport exit required' and refusal['qualification_claims']==[]
    assert all(refusal[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    observer_command=[python,'-I','-S','-B',str(ROOT/'scripts/observe_puck_cpu_held_allocation.py'),*parent_command[5:]]
    audit_command=[python,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),*parent_command[5:],
        '--transport',str(ROOT/'runs/puck-cpu-held-qualification-09-external-cli-transport.json'),
        '--transport-sha256',transport_sha,'--output','/tmp/palimpsest-puck-cpu-held-qualification-09-audit-01.json']
    for phase,value,stdout_sha,stdout_size,budget,command in [
            ('observer',outer_observer,transport_sha,951,240,observer_command),
            ('audit',outer_audit,HISTORICAL09_JSON['docs/reports/puck-cpu-held-qualification-09/observations/palimpsest-puck-cpu-held-qualification-09-audit-01.json'],617,145,audit_command)]:
        assert value['kind']=='puck-cpu-held09-external-transport-v1' and value['phase']==phase
        assert value['returncode']==1 and value['normal_exit'] is True and value['timed_out'] is False
        assert value['command']==command and value['cwd']==str(ROOT) and value['environment']==environment
        assert value['external_deadline_seconds']==budget and 0<value['elapsed_seconds']<budget
        assert value['stdout']['sha256']==stdout_sha and value['stdout']['size_bytes']==stdout_size
        assert value['stderr']['sha256']==empty_sha and value['stderr']['size_bytes']==0
        assert value['implicit_retry'] is False and value['runtime_qualified'] is False and value['study_authorized'] is False
    missing=['runs/puck-cpu-held-qualification-09/'+name for name in ('result.json','baseline-after.json')]
    assert all(not os.path.lexists(ROOT/path) for path in missing)
    return dict(status='FAILED_CONSUMED',configuration_sha256=config_sha,transport_sha256=transport_sha,
        parent_closure_receipt=False,completed_four_import_receipt=False,missing_receipts=missing,
        supervision='failed normal-return deadline; sampled matching_survivors empty',independent_audit_status='FAIL',
        post_failure_full_payload_custody=False,
        diagnostic_stream=dict(records=len(diagnostics),last_record=diagnostics[-1],
            scope='retained unauthenticated optional stderr bytes only; no completeness, cause or acceptance authority'))


ADMITTED10_CONFIGURATION='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json'
HISTORICAL10_JSON={'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json': '4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170', 'runs/puck-cpu-held-qualification-10-external-cli-transport.json': '289d662ede04c0ae59d15e97aae6be11bda4ec3cdc8761991956ab919f197b94', 'runs/puck-cpu-held-qualification-10/supervision.json': '6718298d524490a1706b47518a97542691a5fef012cfb544d7f5730e5e38751b', 'runs/puck-cpu-held-qualification-10/result.json': '60680ac9668f392ac461ed595842ca1bda0d2faa9ec3b5df5aec25f5835893a1', 'docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-puck-cpu-held-qualification-10-audit-01.json': 'f17938df7352a2ccd369e338ce80e1fffa36592b0eb96b2f4ab0dfa2850daad9', 'docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-held10-amendment02-observer-external.json': 'aac5f5aed89fa1ec3445c17ad04b6e6c87fc94c773e7cff8ebef6d4512d81809', 'docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-held10-amendment02-audit-external.json': 'f3410c75c2bfb0c68315ebf29a6e85b31f2407a29795e6248587669151c74ab9'}


def check_consumed10(held):
    rows=[]
    for path,expected in HISTORICAL10_JSON.items():
        value,raw=held.json(ROOT/path,maximum=64*1024)
        assert hashlib.sha256(raw).hexdigest()==expected,path
        rows.append(value)
    config,transport,supervision,result,refusal,outer_observer,outer_audit=rows
    config_sha=HISTORICAL10_JSON[ADMITTED10_CONFIGURATION]
    transport_sha=HISTORICAL10_JSON['runs/puck-cpu-held-qualification-10-external-cli-transport.json']
    result_sha=HISTORICAL10_JSON['runs/puck-cpu-held-qualification-10/result.json']
    held.file(ROOT/'runs/puck-cpu-held-qualification-10/configuration.json',
        dict(size_bytes=8988,sha256=config_sha),64*1024)
    assert config['kind']=='puck-cpu-held-runtime-allocation-v10' and config['phase']=='qualify'
    assert type(config['version']) is int and config['version']==10 and type(config['allocation_id']) is int and config['allocation_id']==10
    assert config['root']==str(ROOT) and config['limits']['normal_seconds']==180 and config['limits']['min_available_ram_bytes']==2<<30
    assert transport['kind']=='puck-cpu-held-cli-transport-v1' and transport['phase']=='qualify'
    assert transport['configuration_sha256']==config_sha and transport['observed_returncode']==1 and transport['timed_out'] is False
    assert 0<transport['elapsed_seconds']<210
    python=str(Path(sys.executable).resolve())
    parent_command=[python,'-I','-S','-B',str(ROOT/'scripts/qualify_puck_cpu_held_runtime.py'),
        '--configuration',str(ROOT/ADMITTED10_CONFIGURATION),'--sha256',config_sha]
    assert transport['command']==parent_command
    streams={}
    for name in ('stdout','stderr'):
        row=transport[name]
        assert row['path']=='runs/puck-cpu-held-qualification-10-external-cli.'+name
        streams[name]=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
    # Normal nonzero parent return before its deadline: stdout is the genuine FAIL result.
    assert streams['stderr']==b'' and hashlib.sha256(streams['stdout']).hexdigest()==result_sha
    assert result['kind']=='puck-cpu-held-runtime-outcome-v10' and result['status']=='FAIL' and result['phase']=='qualify'
    assert type(result['version']) is int and result['version']==10 and result['allocation_id']==10
    assert result['configuration_sha256']==config_sha and result['held_four_imports_observed'] is False
    assert result['error_type']=='ValueError' and result['error']=='CPU qualify worker failed; retained logs are authoritative'
    assert result['closure']==dict(fd_count_before=5,fd_count_after=5,active_children=[],active_non_main_threads=[])
    assert all(result[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    assert result['qualification_claims']==[]
    assert supervision['status']=='failed' and supervision['failure'] is None and supervision['returncode']==1
    assert supervision['process_scope']=='descendants' and supervision['matching_survivors']==[]
    assert supervision['tracked_processes']==[dict(pid=409732,start_ticks=56248873),dict(pid=409733,start_ticks=56248874),dict(pid=409734,start_ticks=56248875)]
    empty_sha='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    assert held.file(ROOT/'runs/puck-cpu-held-qualification-10/logs/stdout.log',
        dict(size_bytes=0,sha256=empty_sha),16*1024**2,raw=True)==b''
    diagnostic_raw=held.file(ROOT/'runs/puck-cpu-held-qualification-10/logs/stderr.log',
        dict(size_bytes=17678,sha256='24442b7225751357f9a5c3e19d95d7a58e3516e9787bc6f3e82eb5b44206d9d1'),16*1024**2,raw=True)
    # This authenticates retained historical bytes, not marker authorship,
    # completeness, import/version acceptance, work location, timing or cause.
    # Runtime10 stderr mixes optional JSON rows with its genuine worker traceback.
    diagnostics=[];other=0
    for line in diagnostic_raw.splitlines():
        try:row=json.loads(line)
        except ValueError:other+=1;continue
        if type(row) is dict:diagnostics.append(row)
        else:other+=1
    first='Unregistered local or external dependency import: backports_abc'
    assert b'ImportError: '+first.encode() in diagnostic_raw
    assert refusal['kind']=='puck-cpu-held-runtime-independent-audit-v1' and refusal['version']==1 and refusal['status']=='FAIL'
    assert refusal['configuration_sha256']==config_sha and refusal['transport_sha256']==transport_sha
    assert refusal['auditor_source_sha256']=='7d87485b1bfcbeeb625a2fc71a59f697cdde5850dabec5a5d29bd7b7f7ac16fa'
    assert refusal['error']=='Normal external transport exit required' and refusal['qualification_claims']==[]
    assert all(refusal[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    observer_command=[python,'-I','-S','-B',str(ROOT/'scripts/observe_puck_cpu_held_allocation.py'),*parent_command[5:]]
    audit_command=[python,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),*parent_command[5:],
        '--transport',str(ROOT/'runs/puck-cpu-held-qualification-10-external-cli-transport.json'),
        '--transport-sha256',transport_sha,'--output','/tmp/palimpsest-puck-cpu-held-qualification-10-audit-01.json']
    for phase,value,stdout_sha,stdout_size,budget,command in [
            ('observer',outer_observer,transport_sha,988,240,observer_command),
            ('audit',outer_audit,HISTORICAL10_JSON['docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-puck-cpu-held-qualification-10-audit-01.json'],617,145,audit_command)]:
        assert value['kind']=='puck-cpu-held10-amendment02-external-transport-v1' and value['phase']==phase
        assert value['returncode']==1 and value['normal_exit'] is True and value['timed_out'] is False
        assert value['command']==command and value['cwd']==str(ROOT) and value['environment']==environment
        assert value['external_deadline_seconds']==budget and 0<value['elapsed_seconds']<budget
        assert value['stdout']['sha256']==stdout_sha and value['stdout']['size_bytes']==stdout_size
        assert value['stderr']['sha256']==empty_sha and value['stderr']['size_bytes']==0
        assert value['implicit_retry'] is False and value['runtime_qualified'] is False and value['study_authorized'] is False
    missing=['runs/puck-cpu-held-qualification-10/baseline-after.json']
    assert all(not os.path.lexists(ROOT/path) for path in missing)
    return dict(status='FAILED_CONSUMED',configuration_sha256=config_sha,transport_sha256=transport_sha,result_sha256=result_sha,
        parent_failure_result=True,parent_failure_closure=result['closure'],completed_four_import_receipt=False,
        missing_receipts=missing,supervision='failed normal worker return1 before deadline; sampled matching_survivors empty',
        independent_audit_status='FAIL',post_failure_full_payload_custody=False,first_refusal=first,
        diagnostic_stream=dict(records=len(diagnostics),non_json_lines=other,last_record=diagnostics[-1],
            scope='retained unauthenticated optional stderr bytes only; no completeness, cause or acceptance authority'))


ADMISSION01_PINS={'docs/plans/puck-cpu-held-qualification-10.json': {'size_bytes': 10951, 'sha256': 'b7da3957cd81f017f7c59beb764577551384d54c634062f9841053c839d12915'}, 'docs/reports/puck-cpu-held-qualification-10-admission-01/outcome.json': {'size_bytes': 1438, 'sha256': '26ab4b3b312d06790377b036774fcb89468d2c381f996f1f1b791628f4dde566'}, 'docs/reports/puck-cpu-held-qualification-10-admission-01/observations/palimpsest-held10-admission-external.json': {'size_bytes': 1114, 'sha256': '74942615a5f78018d5ff4a0758521fda0d9d34c09675fbd284034fc8ab4d2fa9'}, 'docs/reports/puck-cpu-held-qualification-10-admission-01/observations/palimpsest-held10-admission-tool-terminal.json': {'size_bytes': 141, 'sha256': '42fe28488780075d98765fd814f59aed889b1f02e52c7f53917663c1cb0ecc1e'}, 'docs/reports/puck-cpu-held-qualification-10-admission-01/observations/palimpsest-held10-admission-external.stderr': {'size_bytes': 1901, 'sha256': 'e171d09cca3d7925c14c93307f2c3134abe03a84097cc0c374f3f95e2911f6de'}, 'docs/reports/puck-cpu-held-qualification-10-admission-01/observations/palimpsest-held10-admission-external.stdout': {'size_bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}}

def check_consumed_admission01(held,current):
    values=[]
    # The old pretty config is immutable historical data, not the new input.
    for name in list(ADMISSION01_PINS)[:4]:
        row=ADMISSION01_PINS[name]
        value,raw=held.json(ROOT/name,row,maximum=1024**2)
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],name
        values.append(value)
    previous,outcome,external,tool=values
    assert previous==current
    assert outcome['status']=='DATA_ADMISSION_FAILED_CONSUMED' and outcome['admission_invocations']==1
    assert outcome['control_commit']=='b3d50f5d8efbd36c56337c323d66768831c0f43f'
    assert outcome['source_commit']=='e723db037ed1f790c2618798d59f56913054754f'
    assert outcome['actual_runtime10_invoked'] is outcome['full_payload_custody'] is False
    assert external['kind']=='puck-cpu-held10-external-transport-v1' and external['phase']=='admission'
    assert type(external['returncode']) is int and external['returncode']==1
    assert external['normal_exit'] is True and external['timed_out'] is external['implicit_retry'] is False
    assert 0<external['elapsed_seconds']<145 and external['external_deadline_seconds']==145
    assert external['command']==[str(Path(sys.executable).resolve()),'-I','-S','-B',str(ROOT/'docs/plans/puck-cpu-held-qualification-10-admission.py')]
    assert external['environment']==dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    assert external['runtime_qualified'] is external['study_authorized'] is False
    assert tool['exit_code']==1 and tool['outer_timeout'] is tool['runtime_invoked'] is False
    assert 0<tool['elapsed_seconds']<155
    stderr_name,stdout_name=list(ADMISSION01_PINS)[4:]
    stderr=held.file(ROOT/stderr_name,ADMISSION01_PINS[stderr_name],1024**2,raw=True)
    stdout=held.file(ROOT/stdout_name,ADMISSION01_PINS[stdout_name],1024**2,raw=True)
    assert stdout==b'' and hashlib.sha256(stderr).hexdigest()==external['stderr']['sha256']
    failure=json.loads(stderr.splitlines()[0])
    assert failure['kind']=='held10-data-admission-failure-v1' and failure['check_id']==10 and failure['status']=='FAIL'
    assert failure['error_type']=='ValueError' and failure['error']=='Canonical JSON bytes differ: '+str(ROOT/'docs/plans/puck-cpu-held-qualification-10.json')
    assert failure['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[],held_close_completed=True,scope='current process observations only')
    assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-qualification-10-admission-01.json')
    # Runtime10 later ran once under admission02 only; check_consumed10 binds that allocation.
    assert os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-10/result.json')
    return dict(status='FAILED_CONSUMED',actual_runtime10_invoked=False,full_payload_custody=False,
        failure='canonical configuration bytes',scope='genuine historical admission01 metadata only')


ADMISSION02_PINS={'docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-puck-cpu-held-qualification-10-admission-02.json': {'size_bytes': 7408, 'sha256': '33a425040db69d220fea247faf0077883ebd8c99644a20f929d3cbfe886567b9'}, 'docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-held10-amendment02-admission-external.json': {'size_bytes': 1175, 'sha256': '96e1e5912145b930b94e97417af700932dded36e4a2087381a45f07e12325fcd'}, 'docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-held10-amendment02-admission-tool-terminal.json': {'size_bytes': 140, 'sha256': '89f1160a160bed60de4be3e909796adbc9b652f97ecf574c32d269deef503543'}, 'docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-held10-amendment02-independent-admission-review.json': {'size_bytes': 6456, 'sha256': '06f5b8b5a7866b7da34716ecf69afc6804ccbf9c7cc1edf98d603b3df7dc6265'}, 'docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-held10-amendment02-admission-external.stdout': {'size_bytes': 7408, 'sha256': '33a425040db69d220fea247faf0077883ebd8c99644a20f929d3cbfe886567b9'}, 'docs/reports/puck-cpu-held-qualification-10/observations/palimpsest-held10-amendment02-admission-external.stderr': {'size_bytes': 1559, 'sha256': '1df7c6f42f1ca7ed8103ce400f244b3b76c9f4a1178b27557e39808c0afa92d2'}}


def check_consumed_admission02(held,admitted):
    names=list(ADMISSION02_PINS);values=[]
    for name in names[:4]:
        row=ADMISSION02_PINS[name]
        value,raw=held.json(ROOT/name,row,maximum=1024**2)
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],name
        values.append(value)
    receipt,external,tool,review=values
    receipt_raw=held.file(ROOT/names[0],ADMISSION02_PINS[names[0]],1024**2,raw=True)
    stdout=held.file(ROOT/names[4],ADMISSION02_PINS[names[4]],1024**2,raw=True)
    stderr=held.file(ROOT/names[5],ADMISSION02_PINS[names[5]],1024**2,raw=True)
    config_sha='4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170'
    canonical=(json.dumps(admitted,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
    assert hashlib.sha256(canonical).hexdigest()==config_sha and stdout==receipt_raw
    assert receipt['kind']=='puck-cpu-held10-admission02-data-only-admission-v1' and receipt['status']=='DATA_ONLY_ADMITTED'
    assert receipt['admission_check_id']==2 and receipt['configuration_sha256']==config_sha
    assert receipt['qualification10_invoked'] is False and receipt['admission01_failed_consumed'] is True
    assert receipt['source_commit']=='e723db037ed1f790c2618798d59f56913054754f'
    assert receipt['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
    assert all(receipt[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    assert receipt['qualification_claims']==[]
    assert external['kind']=='puck-cpu-held10-amendment02-external-transport-v1' and external['phase']=='admission'
    assert type(external['returncode']) is int and external['returncode']==0
    assert external['normal_exit'] is True and external['timed_out'] is external['implicit_retry'] is False
    assert 0<external['elapsed_seconds']<145 and external['external_deadline_seconds']==145
    assert external['command']==[str(Path(sys.executable).resolve()),'-I','-S','-B',str(ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/admission.py')]
    assert external['environment']==dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    assert external['runtime_qualified'] is external['study_authorized'] is False
    assert external['stdout']['sha256']==hashlib.sha256(stdout).hexdigest() and external['stdout']['size_bytes']==len(stdout)
    assert external['stderr']['sha256']==hashlib.sha256(stderr).hexdigest() and external['stderr']['size_bytes']==len(stderr)
    assert tool['exit_code']==0 and tool['outer_timeout'] is tool['runtime_invoked'] is False and tool['phase']=='admission'
    phases=[json.loads(line) for line in stderr.splitlines()]
    assert [row['phase'] for row in phases]==['controls/plans','SITEhash','hostbaseline/native','forest1','forest2','finalSITEcensus','fullrecheck','close/publication']
    assert all(row['kind']=='held10-admission02-data-admission-phase-v1' and row['check_id']==2 for row in phases)
    assert review['decision']=='GO' and review['findings']==[]
    # Consumed: the sole runtime10 followed this admission; check_consumed10 binds its failure.
    assert os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-10/result.json')
    assert not os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-10/baseline-after.json')
    return dict(status='ADMITTED_CONSUMED_BY_RUNTIME10',configuration_sha256=config_sha,
        receipt_sha256=hashlib.sha256(receipt_raw).hexdigest(),review_decision='GO',phases=len(phases),
        current_admission_authority=False,scope='genuine historical admission02 metadata only; grants no admission11')


PREP_CONFIGURATION='docs/plans/puck-cpu-held-preparation-02.json'
PREP_OUTPUT='runs/puck-cpu-held-preparation-02'
PREP_STAGE='/tmp/palimpsest-puck-cpu-held-02'
PREP_ROOTS=[{'device': 55, 'inode': 10400, 'root_index': 0}, {'device': 55, 'inode': 10401, 'root_index': 1}, {'device': 55, 'inode': 10402, 'root_index': 2}, {'device': 55, 'inode': 10403, 'root_index': 3}]
UNEXECUTED11={'control_commit': 'd83dab3c92387c80e81af528fea25dd3f8931598', 'review_commit': '0b9c67f5fbf70f7bd3af4277ae9a10fb9b60a7d3', 'branch': 'research/puck-cpu-held-qualification-11', 'review': {'path': 'docs/plans/puck-cpu-held-qualification-11-independent-controls-review-01.md', 'size_bytes': 2367, 'sha256': '7b8d8acbbc8a1b289a40510e2eca35ab9958c80a735f3f21b9667b345ee800e6'}, 'outputs': ['/tmp/palimpsest-held11-admission-external.json', '/tmp/palimpsest-held11-admission-external.stderr', '/tmp/palimpsest-held11-admission-external.stdout', '/tmp/palimpsest-held11-observer-external.json', '/tmp/palimpsest-held11-observer-external.stderr', '/tmp/palimpsest-held11-observer-external.stdout', '/tmp/palimpsest-held11-audit-external.json', '/tmp/palimpsest-held11-audit-external.stderr', '/tmp/palimpsest-held11-audit-external.stdout', '/tmp/palimpsest-puck-cpu-held-qualification-11-admission-01.json', '/tmp/palimpsest-puck-cpu-held-qualification-11-audit-01.json', '/tmp/palimpsest-held11-concrete-audit-command.json', '/tmp/palimpsest-held11-admission-tool-command.json', '/tmp/palimpsest-held11-admission-tool-terminal.json', '/tmp/palimpsest-held11-admission-tool.stdout', '/tmp/palimpsest-held11-admission-tool.stderr', '/tmp/palimpsest-held11-observer-tool-command.json', '/tmp/palimpsest-held11-observer-tool-terminal.json', '/tmp/palimpsest-held11-observer-tool.stdout', '/tmp/palimpsest-held11-observer-tool.stderr', '/tmp/palimpsest-held11-audit-tool-command.json', '/tmp/palimpsest-held11-audit-tool-terminal.json', '/tmp/palimpsest-held11-audit-tool.stdout', '/tmp/palimpsest-held11-audit-tool.stderr', '/tmp/palimpsest-held11-pre-admission-guard01.json', '/tmp/palimpsest-held11-pre-observer-guard01.json', '/tmp/palimpsest-held11-independent-admission-review.json', '/tmp/palimpsest-held11-independent-outcome-review.json', '/tmp/palimpsest-held11-post-outcome-observation.json', '/tmp/palimpsest-held11-archive-evidence.py', '/tmp/palimpsest-held11-bind-audit-command.py', '/tmp/palimpsest-held11-collect-outcome.py', '/tmp/palimpsest-held11-make-observer-guard.py', '/tmp/palimpsest-held11-pre-admission-guard.py', '/tmp/palimpsest-held11-run-admission-once.py', '/tmp/palimpsest-held11-run-audit-once.py', '/tmp/palimpsest-held11-run-observer-once.py', '/tmp/palimpsest-held11-pre-observer-guard.py', '/home/utkarsh/.codex/worktrees/0071/brain/docs/reports/puck-cpu-held-qualification-11']}
EMPTY_DIRECTORIES=['runs/puck-cpu-held-preparation-01/outer', 'runs/puck-cpu-held-preparation-01/parent-source/upstream/fly-gym', 'runs/puck-cpu-held-preparation-01/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-preparation-02/outer', 'runs/puck-cpu-held-preparation-02/parent-source/upstream/fly-gym', 'runs/puck-cpu-held-preparation-02/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-qualification-01/outer', 'runs/puck-cpu-held-qualification-01/payload', 'runs/puck-cpu-held-qualification-02/outer', 'runs/puck-cpu-held-qualification-02/payload', 'runs/puck-cpu-held-qualification-02/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-qualification-03/outer', 'runs/puck-cpu-held-qualification-03/payload', 'runs/puck-cpu-held-qualification-03/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-qualification-04/outer', 'runs/puck-cpu-held-qualification-04/payload', 'runs/puck-cpu-held-qualification-04/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-qualification-05/outer', 'runs/puck-cpu-held-qualification-05/payload', 'runs/puck-cpu-held-qualification-05/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-qualification-06/outer', 'runs/puck-cpu-held-qualification-06/payload', 'runs/puck-cpu-held-qualification-06/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-qualification-07/outer', 'runs/puck-cpu-held-qualification-07/payload', 'runs/puck-cpu-held-qualification-07/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-qualification-08/outer', 'runs/puck-cpu-held-qualification-08/payload', 'runs/puck-cpu-held-qualification-08/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-qualification-09/outer', 'runs/puck-cpu-held-qualification-09/payload', 'runs/puck-cpu-held-qualification-09/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-qualification-10/outer', 'runs/puck-cpu-held-qualification-10/payload', 'runs/puck-cpu-held-qualification-10/worker-source/upstream/fly-gym']


def check_preparation02(held,m,current,frozen):
    """Accepted preparation02 metadata only; its staged forest is re-hashed separately by forest()."""
    config,configraw=held.json(ROOT/PREP_CONFIGURATION,maximum=1024**2,lf=True)
    assert m.sha(configraw)==PREP_SHA;current.configuration(config,False)
    assert config['root']==str(ROOT) and config['phase']=='prepare' and config['stage_parent']==PREP_STAGE
    assert current.preparation_output(config)==current.preparation_output(frozen)==PREP_OUTPUT
    prepbase=ROOT/PREP_OUTPUT
    prep,prepraw=held.json(prepbase/'result.json',maximum=1024**2,lf=True)
    assert m.sha(prepraw)==RESULT_SHA;m.outcome(prep,config,PREP_SHA)
    assert prep['staged_roots']==PREP_ROOTS and prep['dependencies']['sha256']==DEP_SHA
    assert held.file(prepbase/'configuration.json',maximum=1024**2,raw=True)==configraw
    for folder,names in [('parent-source',m.SOURCES),('worker-source',m.WORKER)]:
        for row in config['sources']:
            if row['path'] in names:held.file(prepbase/folder/row['path'],row,1024**2)
    prior,accepted,audit=current.historical_acceptance(held,frozen,False)
    assert prior==config and accepted==prep and audit['allocation_id']==12 and audit['status']=='PASS'
    return config,configraw,prep,prepraw,dict(status='ACCEPTED_PREPARATION02',configuration_sha256=PREP_SHA,
        result_sha256=RESULT_SHA,independent_audit_sha256=frozen['preparation_acceptance']['independent_audit']['sha256'],
        stage_parent=PREP_STAGE,staged_roots=PREP_ROOTS,scope='accepted preparation metadata only; staged bytes re-hashed by forest')


def record_preparation01():
    # Preparation01's tmpfs forest was lost on reboot; it is history, not an input.
    return dict(status='ACCEPTED_SUPERSEDED_STAGE_LOST',required=False,stage_parent='/tmp/palimpsest-puck-cpu-held-01',
        stage_present=os.path.lexists('/tmp/palimpsest-puck-cpu-held-01'),
        configuration_sha256='38134e016eff974e06806f1ac74492dc51e0a5721d8cd13d1123a1fd950fe8a6',
        result_sha256='9d49c6ee3a0be61505cfe7d2267b659290be17365d6e35fb5fdbdc38e103f47d')


def check_unexecuted11(held):
    """The d83dab3 attempt-11 controls were reviewed NO-GO and never invoked; none of their outputs exist."""
    row=UNEXECUTED11['review'];held.file(ROOT/row['path'],row,1024**2)
    assert all(not os.path.lexists(path) for path in UNEXECUTED11['outputs'])
    return dict(status='NEVER_INVOKED',control_commit=UNEXECUTED11['control_commit'],review_commit=UNEXECUTED11['review_commit'],
        review='NO-GO: preparation01 stage lost on reboot',absent_outputs=len(UNEXECUTED11['outputs']),
        scope='absence of every d83dab3 /tmp output and archive; /tmp absence alone would not survive a reboot, the Git NO-GO record does')


def check_empty_directories():
    for name in EMPTY_DIRECTORIES:
        path=ROOT/name
        assert os.path.isdir(path) and not os.path.islink(path) and os.listdir(path)==[],name
    return dict(directories=len(EMPTY_DIRECTORIES),scope='historical allocation directories hold no unpinned entries')


def resources(minimum_ram_bytes=2<<30):
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    flags=__import__('os').statvfs('/tmp').f_flag
    value=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),mem_available_bytes=available,project_free_bytes=shutil.disk_usage(ROOT).free,tmpfs_free_bytes=shutil.disk_usage('/tmp').free,nofile_soft=soft,nofile_hard=hard)
    assert available>=minimum_ram_bytes and value['project_free_bytes']>=4<<30 and value['tmpfs_free_bytes']>=256<<20
    assert all(v==resource.RLIM_INFINITY or v>=40000 for v in (soft,hard)) and not flags & (os.ST_RDONLY|os.ST_NOEXEC)
    return value


def absent():
    paths=[ROOT/'runs/puck-cpu-held-qualification-14']+[ROOT/('runs/puck-cpu-held-qualification-14-external-cli'+suffix) for suffix in ('.stdout','.stderr','-transport.json')]
    paths+=[Path('/tmp/palimpsest-puck-cpu-held-qualification-14-audit-01.json'),OUTPUT]
    missing=[ROOT/'runs/puck-cpu-runtime-characterization-01/baseline-after.json']
    for allocation,leaves in [('puck-cpu-install-01',('inventory.json','licences.json','baseline-after.json','logs/namespace.json')),('puck-cpu-retained-admission-01',('inventory.json','snapshot.json','baseline-after.json'))]:
        missing.extend(ROOT/'runs'/allocation/leaf for leaf in leaves)
    missing.extend(ROOT/('runs/puck-cpu-held-qualification-'+n+'/baseline-after.json') for n in ('05','06'))
    missing.extend(ROOT/('runs/puck-cpu-held-qualification-'+epoch+'/'+name) for epoch in ('07','08','09') for name in ('result.json','baseline-after.json'))
    missing.append(ROOT/'runs/puck-cpu-held-qualification-10/baseline-after.json')
    assert all(not os.path.lexists(path) for path in paths+missing)
    return dict(new_paths=[str(p) for p in paths],historical_missing_receipts=len(missing))


def module(held,path,digest):
    raw=held.file(path,maximum=1024**2,raw=True)
    assert hashlib.sha256(raw).hexdigest()==digest
    value=types.ModuleType('_data_only_'+path.stem);value.__file__=str(path)
    exec(compile(raw,str(path),'exec'),value.__dict__)
    return value



def check_absences(dependency,directories,names):
    """Byte/declaration check; worker live custody checks remain separate."""
    assert type(names) is list and len(names)==32 and names==sorted(set(names))
    declared={row['name'] for row in dependency['modules']+dependency['namespaces']}
    declared.update(row['name'] for key in ('exports','native_cache') for row in dependency['import_profile'].get(key,[]))
    packages={row['name']:row for row in dependency['modules'] if row['is_package']}
    packages.update({row['name']:row for row in dependency['namespaces']})
    censuses={i:{row['path'] for row in root['files']}|set(directories[i])
              for i,root in enumerate(dependency['roots']) if root['kind']=='package'}
    for name in names:
        assert name.split('.')[0] not in sys.stdlib_module_names
        assert not any(known==name or known.startswith(name+'.') for known in declared),name
        candidates={(i,name.replace('.','/')) for i in censuses}
        parent,dot,leaf=name.rpartition('.')
        if dot:
            assert parent in packages,name
            row=packages[parent]
            directory=row['path'].rpartition('/')[0] if row.get('is_package') else row['path']
            candidates.add((row['root_index'],directory+'/'+leaf if directory else leaf))
        for i,stem in candidates:
            paths=censuses[i];directory,slash,leaf=stem.rpartition('/')
            cache=(directory+'/' if slash else '')+'__pycache__/'+leaf+'.'
            assert stem not in paths and not any(stem+suffix in paths for suffix in ('.py','.pyc',*importlib.machinery.EXTENSION_SUFFIXES)),name
            assert not any(p.startswith(cache) and p.endswith('.pyc') and '/' not in p[len(cache):] for p in paths),name
    return dict(names=names,scope='current declarations and re-censused held staged forests; not ambient or executed-request coverage')

_MARKER_COUNT=0
_MARKER_BYTES=0


def _stderr_record(value):
    global _MARKER_COUNT,_MARKER_BYTES
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    assert _MARKER_COUNT<12 and len(raw)<=8192 and _MARKER_BYTES+len(raw)<=64*1024
    written=os.write(2,raw)
    assert written==len(raw)
    _MARKER_COUNT+=1;_MARKER_BYTES+=len(raw)


def _phase(name,started,held):
    _stderr_record(dict(kind='held14-data-admission-phase-v1',check_id=14,
        status='phase_completed',phase=name,elapsed_seconds=time.monotonic()-started,
        held=dict(files=len(held.files),total=held.total)))


def _failure(error,started,before=None,held_closed=False):
    # Telemetry failure must never replace the original exception. Omit closure
    # unless this control observed a normal held.close and all fields below.
    try:
        value=dict(kind='held14-data-admission-failure-v1',check_id=14,status='FAIL',
            error_type=type(error).__name__,error=str(error)[:1024],
            elapsed_seconds=time.monotonic()-started)
        if held_closed and before is not None:
            try:
                after=len(os.listdir('/proc/self/fd'))
                children=Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split()
                threads=[name for name in os.listdir('/proc/self/task') if name!=str(os.getpid())]
                value['closure']=dict(fd_count_before=before,fd_count_after=after,
                    active_children=children,active_non_main_threads=threads,
                    held_close_completed=True,scope='current process observations only')
            except BaseException:pass
        if len((json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())>8192:
            value.pop('closure',None)
        _stderr_record(value)
    except BaseException:pass


def main():
    started=time.monotonic()
    try:
        assert len(sys.argv)==1 and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
        assert Path(sys.executable).resolve()==Path('/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11')
        assert 'LD_PRELOAD' not in os.environ and 'LD_LIBRARY_PATH' not in os.environ
        initial_resources=resources();absence=absent()
    except BaseException as error:
        _failure(error,started)
        raise
    started=time.monotonic();deadline=started+120
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,130)
    held=None;before=None;held_closed=False
    try:
        for key,value in [('AS',512*1024**2),('NOFILE',40000),('FSIZE',16*1024**2),('CORE',0)]:
            _,hard=resource.getrlimit(getattr(resource,'RLIMIT_'+key))
            chosen=value if hard==resource.RLIM_INFINITY else min(value,hard)
            resource.setrlimit(getattr(resource,'RLIMIT_'+key),(chosen,chosen))
        fd=os.open(AUDITOR,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            with os.fdopen(os.dup(fd),'rb') as handle:raw=handle.read(1024**2+1)
            assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()==AUDITOR_SHA
        finally:os.close(fd)
        m=types.ModuleType('authenticated_cpu_data_auditor');m.__file__=str(AUDITOR)
        exec(compile(raw,str(AUDITOR),'exec'),m.__dict__)
        before=len(os.listdir('/proc/self/fd'));held=m.Held(deadline);prepbase=ROOT/PREP_OUTPUT
        try:
            assert held.file(AUDITOR,dict(size_bytes=65522,sha256=AUDITOR_SHA),1024**2,raw=True)==raw
            own=held.file(Path(__file__).resolve(),maximum=1024**2)
            current=module(held,ROOT/'scripts/audit_puck_cpu_held_runtime.py',AUDITOR_CURRENT_SHA)
            observation=module(held,ROOT/'scripts/audit_puck_cpu_runtime_characterization.py',OBS_AUDITOR_SHA)
            p,a,r,helpers=observation.support()
            for row in observation.SUPPORT:held.file(ROOT/row['path'],row,1024**2)
            frozen,frozenraw=held.json(CONFIGURATION,dict(size_bytes=CONFIGURATION.stat().st_size,sha256=CONFIG_SHA),1024**2,lf=True)
            current.configuration(frozen,False)
            for row in frozen['sources']:held.file(ROOT/row['path'],row,1024**2)
            for row in frozen['preparation_acceptance'].values():held.file(ROOT/row['path'],row,16*1024**2,raw=True)
            manifest,manifest_raw=held.json(ROOT/'docs/plans/puck-cpu-held-qualification-14-freeze.json',maximum=1024**2)
            assert manifest_raw==(json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
            raw_paths={row['path'] for row in frozen['inputs'].values()}
            raw_paths.update(row['path'] for row in frozen['preparation_acceptance'].values())
            raw_paths.add('docs/plans/puck-cpu-observed-import-profile-candidate-01.json')
            raw_paths.update('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json' for i in range(1,7))
            raw_paths.update(HISTORICAL07_JSON)
            raw_paths.update(HISTORICAL08_JSON)
            raw_paths.update(HISTORICAL09_JSON)
            raw_paths.update(HISTORICAL10_JSON)
            raw_paths.update(ADMISSION01_PINS)
            raw_paths.update(ADMISSION02_PINS)
            hold_manifest(held,manifest['pins'],raw_paths)
            admitted10,_=held.json(ROOT/ADMITTED10_CONFIGURATION,dict(size_bytes=8988,sha256=HISTORICAL10_JSON[ADMITTED10_CONFIGURATION]),1024**2,lf=True)
            consumed_admission01=check_consumed_admission01(held,admitted10)
            consumed_admission02=check_consumed_admission02(held,admitted10)
            assert manifest['source_commit']=='f05bd699af337e44de54584bb334690ec405f994' and manifest['observer_invocations']==1 and manifest['implicit_retry'] is False
            config,configraw,prep,prepraw,preparation02=check_preparation02(held,m,current,frozen)
            blobs={};data={}
            for role,row in config['inputs'].items():
                blobs[role]=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
                if role!='generated':data[role]=m.decode(blobs[role])
            m.inputs_binding(config,data,blobs);source,dependency,directories=m.plan(config,data)
            selected=dict(data);selected_blobs=dict(blobs)
            candidate_raw=held.file(ROOT/frozen['inputs']['candidate']['path'],frozen['inputs']['candidate'],16*1024**2,raw=True)
            selected['candidate']=current.decode(candidate_raw);selected_blobs['candidate']=candidate_raw
            current.publication_candidate(data['candidate'],selected['candidate'],pillow_origins=True)
            current.inputs_binding(frozen,selected,selected_blobs)
            current_source,current_dependency,current_dirs=current.plan(frozen,selected)
            assert current_source==source and current_dirs==directories
            expected=json.loads(m.canonical(dependency));expected['import_profile']=selected['candidate']['import_profile']
            assert current_dependency==expected
            negative_absence=check_absences(current_dependency,current_dirs,frozen['negative_imports'])
            _phase('controls/plans',started,held)
            site=ROOT/'runs/puck-cpu-install-01/site'
            files,site_dirs,site_stamps=r.census(site)
            assert files==r.rows_to_map(data['inventory']['entries']) and site_dirs==set(data['layout']['predicted_destination_directories'])
            assert (len(files),len(site_dirs),sum(row['size_bytes'] for row in files.values()))==(27225,2074,1304701872)
            _phase('SITEhash',started,held)
            copy,copyraw=held.json(prepbase/'control/copy-registration.json',lf=False)
            assert copyraw==m.canonical(source,False)
            for role in ['candidate','layout']:
                assert held.file(prepbase/('control/'+role+'.json'),maximum=16*1024**2,raw=True)==blobs[role]
            request,requestraw=held.json(prepbase/'control/stage-request.json',maximum=1024**2,lf=True)
            assert request==dict(registration=dict(path='/puck/control/copy-registration.json',sha256=m.sha(copyraw)),candidate=dict(path='/puck/control/candidate.json',sha256=m.sha(blobs['candidate'])),layout=dict(path='/puck/control/layout.json',sha256=m.sha(blobs['layout'])))
            dep,depraw=held.json(prepbase/'payload/dependencies.json',prep['dependencies'],lf=False)
            assert m.sha(depraw)==DEP_SHA and depraw==m.canonical(dependency,False)
            stage,stageraw=held.json(prepbase/'payload/stage.json',maximum=1024**2,lf=True);m.no_authority(stage)
            assert stage['kind']=='puck-cpu-tmpfs-preparation-receipt-v1' and stage['status']=='prepared' and stage['dependencies']==prep['dependencies'] and stage['staged_roots']==prep['staged_roots']
            assert held.file(prepbase/'logs/stdout.log',maximum=1024**2,raw=True)==stageraw
            held.file(prepbase/'logs/stderr.log',maximum=16*1024**2)
            for row in data['native']['native_files']:held.file(row['path'],row,single=False)
            aliases=data['native']['aliases'];assert type(aliases) is list and len(aliases)<=256 and len({r[0] for r in aliases})==len(aliases)
            for path,target in aliases:held.symlink(path,target)
            summary=m.baseline(held,data['baseline'])
            for name in ['baseline-before.json','baseline-after.json']:
                value,_=held.json(prepbase/name,lf=True);assert value==summary
            observed,_=held.json(prepbase/'supervision.json',maximum=1024**2,lf=True);m.supervision(observed,'prepare')
            command=[m.PYTHON,'-I','-S','-B','/puck/source/scripts/stage_puck_cpu_held_runtime.py',m.sha(requestraw)]
            invocation,_=held.json(prepbase/'invocation.json',maximum=1024**2,lf=True)
            assert invocation==dict(command=current.namespace_command(config,data,'prepare',command),configuration_sha256=PREP_SHA)
            for allocation,expected in [('01','224cb9bdb18228f6e8da7a47e7455cd604a6e756df5fd017294b9221f26d9299'),('02','085d19bdd39d392aaeab0c1590ec92b99e0bb2a4e8945f5d23dd51733fbab56b'),('03','ba5cad51576c3dd593c479d052328fcb4181943d3f5acdbdaa7cdee145f1254b'),('04','d2db585f4851b916e7c632ca268d7527ce4604e6949918ea6d89408ddbcc3889'),('05','c5d2d2037ed248834d971278cbe2d6637b0324eb5b1518933e5201980b493e67'),('06','e88a7f3317ae15b709409cf04a30f969629b20c51454a5ad6ca72d63d6378b88')]:
                failurebase=ROOT/('runs/puck-cpu-held-qualification-'+allocation)
                failed,fraw=held.json(failurebase/'result.json',maximum=1024**2,lf=True)
                assert m.sha(fraw)==expected and failed['status']=='FAIL' and failed['allocation_id']==int(allocation)
                m.no_authority(failed)
                assert not os.path.lexists(failurebase/'baseline-after.json')
            consumed07=check_consumed07(held)
            consumed08=check_consumed08(held)
            consumed09=check_consumed09(held)
            consumed10=check_consumed10(held)
            unexecuted11=check_unexecuted11(held)
            empty_directories=check_empty_directories()
            preparation01=record_preparation01()
            _phase('hostbaseline/native',started,held)
            tree=m.forest(held,config,dependency,directories,prep['staged_roots'])
            _phase('forest1',started,held)
            assert m.forest(held,config,dependency,directories,prep['staged_roots'])==tree
            _phase('forest2',started,held)
            _,final_dirs,final_stamps=r.census(site,hashes=False)
            assert final_dirs==site_dirs and final_stamps==site_stamps
            _phase('finalSITEcensus',started,held)
            absence=absent();final_resources=resources()
            held.recheck();held.clock()
            _phase('fullrecheck',started,held)
            totals=dict(file_count=sum(len(r['files']) for r in dependency['roots']),directory_count=sum(len(d) for d in directories),input_bytes=sum(f['size_bytes'] for r in dependency['roots'] for f in r['files']))
            assert totals==dict(file_count=27255,directory_count=2076,input_bytes=1318494346)
        finally:
            held.close()
            held_closed=True
        after=len(os.listdir('/proc/self/fd'))
        assert before==after and not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split() and len(os.listdir('/proc/self/task'))==1
        sampled=[]
        for identity in [(3569912,53431366),(3569913,53431366),(3569914,53431367),(3798021,53913806),(3798022,53913806),(3798023,53913807),(3996069,54384185),(3996070,54384185),(3996071,54384186),(104005,55289090),(104006,55289091),(104007,55289092),(409732,56248873),(409733,56248874),(409734,56248875)]:
            path=Path('/proc')/str(identity[0])/'stat'
            try:
                current=int(path.read_text().rsplit(')',1)[1].split()[19])
                matches=current==identity[1]
            except FileNotFoundError:matches=False
            assert not matches
            sampled.append(dict(pid=identity[0],start_ticks=identity[1],matching_identity_present=matches))
        result=dict(m.CLAIMS,kind='puck-cpu-held14-data-only-admission-v1',version=1,status='DATA_ONLY_ADMITTED',scope='dated current14/D on preparation03 source/input/SITE/staged/native/interpreter bytes and resources only; no allocation, target import or preparation reacceptance',preparation_configuration_sha256=PREP_SHA,preparation_result_sha256=RESULT_SHA,dependencies_sha256=DEP_SHA,current_dependencies_sha256=m.sha(m.canonical(current_dependency,False)),current_candidate_sha256=m.sha(candidate_raw),auditor_source_sha256=AUDITOR_SHA,runner_sha256=own['sha256'],baseline=summary,root_count=4,historical_capsule_files=34,input_pins=16,**totals,closure=dict(fd_count_before=before,fd_count_after=after,active_children=[],active_non_main_threads=[]),elapsed_seconds=time.monotonic()-started,qualifications01_02_03_04_05_06_07_08_09_10_still_failed_consumed=True,qualification06_invoked=True,qualification07_invoked=True,qualification08_invoked=True,qualification09_invoked=True,qualification10_invoked=True,qualification11_invoked=False,admission_check_id=1,admission10_01_failed_consumed=True,admission10_01_failure=consumed_admission01,admission10_02_admitted_consumed=True,admission10_02=consumed_admission02,configuration_sha256=CONFIG_SHA,current_auditor_sha256=AUDITOR_CURRENT_SHA,resources_before=initial_resources,resources_after=final_resources,absence=absence,site_files=27225,site_directories=2074,site_bytes=1304701872,process_identity_samples=sampled,process_scope='fifteen recorded identities only; nonexhaustive non-atomic lifetime observation',qualification07_failure=consumed07,qualification08_failure=consumed08,qualification09_failure=consumed09,qualification10_failure=consumed10,preparation02=preparation02,preparation01=preparation01,attempt11_d83dab3=unexecuted11,historical_empty_directories=empty_directories,current_sources=24,current_inputs=16,negative_absence=negative_absence,source_commit='f05bd699af337e44de54584bb334690ec405f994')
        assert time.monotonic()<deadline;m.publish(OUTPUT,result)
        _phase('close/publication',started,held)
        assert time.monotonic()<deadline
        print(m.canonical(result).decode(),end='',flush=True)
        assert time.monotonic()<deadline
        return 0
    except BaseException as error:
        _failure(error,started,before,held_closed)
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
