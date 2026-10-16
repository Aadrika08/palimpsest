"""Add consumed runtime10 and admission10 01/02 history to the baseline11 runner once."""
from pathlib import Path
import hashlib
import json

root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
path=root/'docs/plans/puck-cpu-held-qualification-11-admission.py'
text=path.read_text()
assert 'def check_consumed10' not in text and 'def check_consumed_admission02' not in text
packet='docs/reports/puck-cpu-held-qualification-10'
index=json.loads((root/packet/'evidence-index.json').read_bytes())
assert index['control_commit']=='796359a099131157b5b91db38f14784628d5d7c5' and index['artifact_count']==165
archived={row['original_path']:row for row in index['artifacts']}


def sha(name):
    raw=(root/name).read_bytes();return len(raw),hashlib.sha256(raw).hexdigest()


def genuine(name,original=None):
    # Bind each historical role to the published terminal10 archive row, not to a fresh guess.
    size,digest=sha(name);row=archived[original or str(root/name)]
    assert (size,digest)==(row['size_bytes'],row['sha256']),name
    return size,digest


observations=packet+'/observations/'
config='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json'
assert sha(config)==(8988,'4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170')
historical10={config:sha(config)[1]}
for name in ('runs/puck-cpu-held-qualification-10-external-cli-transport.json',
        'runs/puck-cpu-held-qualification-10/supervision.json','runs/puck-cpu-held-qualification-10/result.json'):
    historical10[name]=genuine(name)[1]
for leaf in ('palimpsest-puck-cpu-held-qualification-10-audit-01.json','palimpsest-held10-amendment02-observer-external.json',
        'palimpsest-held10-amendment02-audit-external.json'):
    name=observations+leaf;historical10[name]=sha(name)[1]
    assert genuine(name,'/tmp/'+leaf)[1]==historical10[name]
assert historical10['runs/puck-cpu-held-qualification-10-external-cli-transport.json']=='289d662ede04c0ae59d15e97aae6be11bda4ec3cdc8761991956ab919f197b94'
assert historical10['runs/puck-cpu-held-qualification-10/result.json']=='60680ac9668f392ac461ed595842ca1bda0d2faa9ec3b5df5aec25f5835893a1'
stderr_size,stderr_sha=genuine('runs/puck-cpu-held-qualification-10/logs/stderr.log')
assert stderr_size==17678
admission02={}
for leaf in ('palimpsest-puck-cpu-held-qualification-10-admission-02.json','palimpsest-held10-amendment02-admission-external.json',
        'palimpsest-held10-amendment02-admission-tool-terminal.json','palimpsest-held10-amendment02-independent-admission-review.json',
        'palimpsest-held10-amendment02-admission-external.stdout','palimpsest-held10-amendment02-admission-external.stderr'):
    name=observations+leaf;size,digest=genuine(name,'/tmp/'+leaf)
    admission02[name]=dict(size_bytes=size,sha256=digest)
assert admission02[observations+'palimpsest-puck-cpu-held-qualification-10-admission-02.json']==dict(size_bytes=7408,sha256='33a425040db69d220fea247faf0077883ebd8c99644a20f929d3cbfe886567b9')

block10='ADMITTED10_CONFIGURATION='+repr(config)+'\n'
block10+='HISTORICAL10_JSON='+repr(historical10)+'\n\n\n'
block10+='''def check_consumed10(held):
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
        dict(size_bytes=@STDERR_SIZE@,sha256='@STDERR_SHA@'),16*1024**2,raw=True)
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


'''
block10=block10.replace('@STDERR_SIZE@',str(stderr_size)).replace('@STDERR_SHA@',stderr_sha)
anchor='ADMISSION01_PINS='
assert text.count(anchor)==1
text=text.replace(anchor,block10+anchor)

block02='ADMISSION02_PINS='+repr(admission02)+'\n\n\n'
block02+='''def check_consumed_admission02(held,admitted):
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
    canonical=(json.dumps(admitted,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\\n').encode()
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


'''
anchor='def resources('
assert text.count(anchor)==1
text=text.replace(anchor,block02+anchor)


def replace(old,new,count=1):
    global text
    assert text.count(old)==count,(old,text.count(old))
    text=text.replace(old,new)


replace("    assert not os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-10')\n",
    "    # Runtime10 later ran once under admission02 only; check_consumed10 binds that allocation.\n"
    "    assert os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-10/result.json')\n")
replace("    for epoch in ('07','08','09'):\n","    for epoch in ('07','08','09','10'):\n")
replace("for epoch in ('07','08','09') for name in ('result.json','baseline-after.json'))\n",
    "for epoch in ('07','08','09') for name in ('result.json','baseline-after.json'))\n"
    "    missing.append(ROOT/'runs/puck-cpu-held-qualification-10/baseline-after.json')\n")
replace('raw_paths.update(HISTORICAL09_JSON)','raw_paths.update(HISTORICAL09_JSON)\n            raw_paths.update(HISTORICAL10_JSON)')
replace('raw_paths.update(ADMISSION01_PINS)','raw_paths.update(ADMISSION01_PINS)\n            raw_paths.update(ADMISSION02_PINS)')
replace('consumed_admission01=check_consumed_admission01(held,frozen)',
    'admitted10,_=held.json(ROOT/ADMITTED10_CONFIGURATION,dict(size_bytes=8988,sha256=HISTORICAL10_JSON[ADMITTED10_CONFIGURATION]),1024**2,lf=True)\n'
    '            consumed_admission01=check_consumed_admission01(held,admitted10)\n'
    '            consumed_admission02=check_consumed_admission02(held,admitted10)')
replace('consumed09=check_consumed09(held)','consumed09=check_consumed09(held)\n            consumed10=check_consumed10(held)')
replace('(104007,55289092)]:','(104007,55289092),(409732,56248873),(409733,56248874),(409734,56248875)]:')
replace('qualifications01_02_03_04_05_06_07_08_09_still_failed_consumed=True','qualifications01_02_03_04_05_06_07_08_09_10_still_failed_consumed=True')
replace('qualification10_invoked=False,admission_check_id=2,admission01_failed_consumed=True,admission01_failure=consumed_admission01,',
    'qualification10_invoked=True,qualification11_invoked=False,admission_check_id=1,admission10_01_failed_consumed=True,'
    'admission10_01_failure=consumed_admission01,admission10_02_admitted_consumed=True,admission10_02=consumed_admission02,')
replace("process_scope='twelve recorded identities only;","process_scope='fifteen recorded identities only;")
replace('qualification09_failure=consumed09,','qualification09_failure=consumed09,qualification10_failure=consumed10,')
compile(text,str(path),'exec')
path.write_text(text)
print(json.dumps(dict(new_history10=True,admission10_02_consumed=True,historical_missing_receipts=17,process_samples=15,
    historical10_roles=len(historical10),admission02_roles=len(admission02),admission_or_runtime_invoked=False)))
