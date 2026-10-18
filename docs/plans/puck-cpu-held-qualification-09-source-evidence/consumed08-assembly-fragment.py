# Prospective09 assembly fragment only; never an admission entry point.
# Keep HISTORICAL07_JSON and check_consumed07 byte-for-byte unchanged. Add the
# following08 dictionary/helper, and replace only hold_manifest as shown here.
# main must reserve set(HISTORICAL07_JSON)|set(HISTORICAL08_JSON), call both
# checks, retain both absent result/baseline-after pairs, and separately sample
# the three08 PID/start identities. Root owns that assembly and its freeze.

HISTORICAL08_JSON={
    'docs/plans/puck-cpu-held-qualification-08.json':'67076970caffe64b6162c4344f11d943b620dd2e0fb43ace72e39f508fa7ee60',
    'runs/puck-cpu-held-qualification-08-external-cli-transport.json':'d80f60a10cf611c660e5bda25bf6f055c49415686681db33ca6ae44f868841b4',
    'runs/puck-cpu-held-qualification-08/supervision.json':'2363163d5926cf8d8ce68c0ea9290671cd633e369cc10c1f5d3261b91e30cdb4',
    'docs/reports/puck-cpu-held-qualification-08/observations/palimpsest-puck-cpu-held-qualification-08-audit-01.json':'93fb936dcf82bcf46a592026e8744c5900bf5bd9b283465d5e5dfad13d346ba9',
    'docs/reports/puck-cpu-held-qualification-08/external/palimpsest-held08-observer-external.json':'e3dcff1660b44d0b9c940ea1b65782a484443032d2f79d9cb2c611b12726b8f6',
    'docs/reports/puck-cpu-held-qualification-08/external/palimpsest-held08-audit-external.json':'fa41490d8f91c2ea865d73ee4e668bd97dbd50ab85318a446680000f5a12595d',
}


def hold_manifest(held,pins,raw_paths):
    raw_paths=set(raw_paths)
    for epoch in ('07','08'):
        raw_paths.update('runs/puck-cpu-held-qualification-'+epoch+'-external-cli.'+name for name in ('stdout','stderr'))
        raw_paths.update('runs/puck-cpu-held-qualification-'+epoch+'/logs/'+name+'.log' for name in ('stdout','stderr'))
    for row in pins:held.file(ROOT/row['path'],row,16*1024**2,raw=row['path'] in raw_paths)


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
