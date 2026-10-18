"""Bind the baseline14 runner to preparation03 and record runtime11/admission11b/preparation02 as consumed (GREEN).

Edits the runner once. Reads retained metadata only; never runs admission, census, guards,
observer, auditor main or touches the preparation02/03 stages.
"""
from pathlib import Path
import hashlib,json,os
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='docs/plans/puck-cpu-held-qualification-14'
PACKET='docs/reports/puck-cpu-held-qualification-11b'
OBS=PACKET+'/observations/'
CONFIG11='docs/plans/puck-cpu-held-qualification-11.json'
def sha(name):
    raw=(ROOT/name).read_bytes();return len(raw),hashlib.sha256(raw).hexdigest()
path=ROOT/(BASE+'-admission.py');text=path.read_text()
assert 'def check_consumed11' not in text and 'def check_preparation03' not in text
index=json.loads((ROOT/PACKET/'evidence-index.json').read_bytes())
assert index['control_commit']=='27780dd5cbc096c26fb353faea7edfde878a4f74' and index['artifact_count']==175 and index['status']=='FAILED_CONSUMED'
archived={row['original_path']:row for row in index['artifacts']}
def genuine(name,original=None):
    size,digest=sha(name);row=archived[original or str(ROOT/name)]
    assert (size,digest)==(row['size_bytes'],row['sha256']),name
    return size,digest
assert sha(CONFIG11)==(9048,'4ab0ef1b3eab7a74d2f6dc03ab56293a65dea2d7363680b7e687aeb399d1afb5')
historical11={CONFIG11:sha(CONFIG11)[1]}
for name in ('runs/puck-cpu-held-qualification-11-external-cli-transport.json','runs/puck-cpu-held-qualification-11/supervision.json'):
    historical11[name]=genuine(name)[1]
for leaf in ('palimpsest-puck-cpu-held-qualification-11b-audit-01.json','palimpsest-held11b-observer-external.json','palimpsest-held11b-audit-external.json'):
    historical11[OBS+leaf]=genuine(OBS+leaf,'/tmp/'+leaf)[1]
stderr_size,stderr_sha=genuine('runs/puck-cpu-held-qualification-11/logs/stderr.log')
assert genuine('runs/puck-cpu-held-qualification-11/configuration.json')==(9048,historical11[CONFIG11])
admission11b={}
for leaf in ('palimpsest-puck-cpu-held-qualification-11b-admission-01.json','palimpsest-held11b-admission-external.json',
        'palimpsest-held11b-admission-tool-terminal.json','palimpsest-held11b-independent-admission-review.json',
        'palimpsest-held11b-admission-external.stdout','palimpsest-held11b-admission-external.stderr'):
    size,digest=genuine(OBS+leaf,'/tmp/'+leaf);admission11b[OBS+leaf]=dict(size_bytes=size,sha256=digest)
prep02=json.loads((ROOT/CONFIG11).read_bytes())['preparation_acceptance']
for row in prep02.values():assert sha(row['path'])==(row['size_bytes'],row['sha256']),row['path']
assert prep02['result']['sha256']=='4ef13965e6f312a0bcdef9c49e57190f6a9526988f20f1959357bcc31400e0d4'
empty=[]
for name in ['runs/puck-cpu-held-qualification-'+str(i).zfill(2) for i in range(1,12)]+['runs/puck-cpu-held-preparation-0'+str(i) for i in (1,2,3)]:
    for directory,dirs,files in os.walk(ROOT/name,followlinks=False):
        if not dirs and not files:empty.append(str(Path(directory).relative_to(ROOT)))
empty.sort();assert len(empty)==41
prep03=json.loads((ROOT/'runs/puck-cpu-held-preparation-03/result.json').read_bytes())
roots=[dict(device=r['device'],inode=r['inode'],root_index=r['root_index']) for r in prep03['staged_roots']]
assert roots==[dict(device=55,inode=43194+i,root_index=i) for i in range(4)]
block11='HISTORICAL11_JSON='+repr(historical11)+'\n\n\n'+'''def check_consumed11(held):
    rows=[]
    for path,expected in HISTORICAL11_JSON.items():
        value,raw=held.json(ROOT/path,maximum=64*1024)
        assert hashlib.sha256(raw).hexdigest()==expected,path
        rows.append(value)
    config,transport,supervision,refusal,outer_observer,outer_audit=rows
    config_sha=HISTORICAL11_JSON['docs/plans/puck-cpu-held-qualification-11.json']
    transport_sha=HISTORICAL11_JSON['runs/puck-cpu-held-qualification-11-external-cli-transport.json']
    held.file(ROOT/'runs/puck-cpu-held-qualification-11/configuration.json',dict(size_bytes=9048,sha256=config_sha),64*1024)
    assert config['kind']=='puck-cpu-held-runtime-allocation-v11' and config['phase']=='qualify'
    assert type(config['version']) is int and config['version']==11 and type(config['allocation_id']) is int and config['allocation_id']==11
    assert config['root']==str(ROOT) and config['limits']['normal_seconds']==180 and config['limits']['min_available_ram_bytes']==2<<30
    assert config['stage_parent']=='/tmp/palimpsest-puck-cpu-held-02'
    assert transport['kind']=='puck-cpu-held-cli-transport-v1' and transport['phase']=='qualify'
    assert transport['configuration_sha256']==config_sha and transport['observed_returncode']==1 and transport['timed_out'] is False
    assert 0<transport['elapsed_seconds']<210
    python=str(Path(sys.executable).resolve())
    parent_command=[python,'-I','-S','-B',str(ROOT/'scripts/qualify_puck_cpu_held_runtime.py'),
        '--configuration',str(ROOT/'docs/plans/puck-cpu-held-qualification-11.json'),'--sha256',config_sha]
    assert transport['command']==parent_command
    for name in ('stdout','stderr'):
        row=transport[name]
        assert row['path']=='runs/puck-cpu-held-qualification-11-external-cli.'+name
        raw=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
        assert raw==b'' if name=='stdout' else b'CPU allocation normal return deadline' in raw
    assert supervision['status']=='failed' and supervision['failure']=='normal-return deadline' and supervision['returncode']==-15
    assert supervision['process_scope']=='descendants' and supervision['matching_survivors']==[]
    assert supervision['tracked_processes']==[dict(pid=325632,start_ticks=3798844),dict(pid=325635,start_ticks=3798844),dict(pid=325642,start_ticks=3798845)]
    empty_sha='e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'
    assert held.file(ROOT/'runs/puck-cpu-held-qualification-11/logs/stdout.log',
        dict(size_bytes=0,sha256=empty_sha),16*1024**2,raw=True)==b''
    diagnostic_raw=held.file(ROOT/'runs/puck-cpu-held-qualification-11/logs/stderr.log',
        dict(size_bytes=@STDERR_SIZE@,sha256='@STDERR_SHA@'),16*1024**2,raw=True)
    # This authenticates retained historical bytes, not marker authorship,
    # completeness, import/version acceptance, work location, timing or cause.
    diagnostics=[json.loads(line) for line in diagnostic_raw.splitlines()]
    assert refusal['kind']=='puck-cpu-held-runtime-independent-audit-v1' and refusal['version']==1 and refusal['status']=='FAIL'
    assert refusal['configuration_sha256']==config_sha and refusal['transport_sha256']==transport_sha
    assert refusal['auditor_source_sha256']=='04192a3ba3d7020a5399465aa6da4f7d7ebe3d74172e4b448ea500b09aa9a62b'
    assert refusal['error']=='Normal external transport exit required' and refusal['qualification_claims']==[]
    assert all(refusal[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    observer_command=[python,'-I','-S','-B',str(ROOT/'scripts/observe_puck_cpu_held_allocation.py'),*parent_command[5:]]
    audit_command=[python,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),*parent_command[5:],
        '--transport',str(ROOT/'runs/puck-cpu-held-qualification-11-external-cli-transport.json'),
        '--transport-sha256',transport_sha,'--output','/tmp/palimpsest-puck-cpu-held-qualification-11b-audit-01.json']
    for phase,value,stdout_sha,stdout_size,budget,command in [
            ('observer',outer_observer,transport_sha,951,240,observer_command),
            ('audit',outer_audit,HISTORICAL11_JSON['docs/reports/puck-cpu-held-qualification-11b/observations/palimpsest-puck-cpu-held-qualification-11b-audit-01.json'],617,145,audit_command)]:
        assert value['kind']=='puck-cpu-held11b-external-transport-v1' and value['phase']==phase
        assert value['returncode']==1 and value['normal_exit'] is True and value['timed_out'] is False
        assert value['command']==command and value['cwd']==str(ROOT) and value['environment']==environment
        assert value['external_deadline_seconds']==budget and 0<value['elapsed_seconds']<budget
        assert value['stdout']['sha256']==stdout_sha and value['stdout']['size_bytes']==stdout_size
        assert value['stderr']['sha256']==empty_sha and value['stderr']['size_bytes']==0
        assert value['implicit_retry'] is False and value['runtime_qualified'] is False and value['study_authorized'] is False
    missing=['runs/puck-cpu-held-qualification-11/'+name for name in ('result.json','baseline-after.json')]
    assert all(not os.path.lexists(ROOT/path) for path in missing)
    return dict(status='FAILED_CONSUMED',configuration_sha256=config_sha,transport_sha256=transport_sha,
        parent_closure_receipt=False,completed_four_import_receipt=False,missing_receipts=missing,
        supervision='failed normal-return deadline; sampled matching_survivors empty',independent_audit_status='FAIL',
        post_failure_full_payload_custody=False,policy_v5_imports='Torchvision returned; killed during import mujoco at the 180s deadline',
        diagnostic_stream=dict(records=len(diagnostics),last_record=diagnostics[-1],
            scope='retained unauthenticated optional stderr bytes only; no completeness, cause or acceptance authority'))


ADMISSION11B_PINS='''+repr(admission11b)+'''


def check_consumed_admission11b(held,admitted):
    names=list(ADMISSION11B_PINS);values=[]
    for name in names[:4]:
        row=ADMISSION11B_PINS[name]
        value,raw=held.json(ROOT/name,row,maximum=1024**2)
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],name
        values.append(value)
    receipt,external,tool,review=values
    receipt_raw=held.file(ROOT/names[0],ADMISSION11B_PINS[names[0]],1024**2,raw=True)
    stdout=held.file(ROOT/names[4],ADMISSION11B_PINS[names[4]],1024**2,raw=True)
    stderr=held.file(ROOT/names[5],ADMISSION11B_PINS[names[5]],1024**2,raw=True)
    config_sha='4ab0ef1b3eab7a74d2f6dc03ab56293a65dea2d7363680b7e687aeb399d1afb5'
    canonical=(json.dumps(admitted,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\\n').encode()
    assert hashlib.sha256(canonical).hexdigest()==config_sha and stdout==receipt_raw
    assert receipt['kind']=='puck-cpu-held11b-data-only-admission-v1' and receipt['status']=='DATA_ONLY_ADMITTED'
    assert receipt['admission_check_id']==1 and receipt['configuration_sha256']==config_sha and receipt['qualification11_invoked'] is False
    assert receipt['source_commit']=='8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15'
    assert receipt['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
    assert all(receipt[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    assert receipt['qualification_claims']==[]
    assert external['kind']=='puck-cpu-held11b-external-transport-v1' and external['phase']=='admission'
    assert type(external['returncode']) is int and external['returncode']==0
    assert external['normal_exit'] is True and external['timed_out'] is external['implicit_retry'] is False
    assert 0<external['elapsed_seconds']<145 and external['external_deadline_seconds']==145
    assert external['command']==[str(Path(sys.executable).resolve()),'-I','-S','-B',str(ROOT/'docs/plans/puck-cpu-held-qualification-11-admission.py')]
    assert external['environment']==dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    assert external['runtime_qualified'] is external['study_authorized'] is False
    assert external['stdout']['sha256']==hashlib.sha256(stdout).hexdigest() and external['stdout']['size_bytes']==len(stdout)
    assert external['stderr']['sha256']==hashlib.sha256(stderr).hexdigest() and external['stderr']['size_bytes']==len(stderr)
    assert tool['exit_code']==0 and tool['outer_timeout'] is tool['runtime_invoked'] is False and tool['phase']=='admission'
    phases=[json.loads(line) for line in stderr.splitlines()]
    assert [row['phase'] for row in phases]==['controls/plans','SITEhash','hostbaseline/native','forest1','forest2','finalSITEcensus','fullrecheck','close/publication']
    assert all(row['kind']=='held11b-data-admission-phase-v1' and row['check_id']==11 for row in phases)
    assert review['decision']=='GO' and review['findings']==[]
    # Consumed: the sole runtime11 followed this admission; check_consumed11 binds its deadline failure.
    assert os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-11/supervision.json')
    assert not os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-11/result.json')
    return dict(status='ADMITTED_CONSUMED_BY_RUNTIME11',configuration_sha256=config_sha,
        receipt_sha256=hashlib.sha256(receipt_raw).hexdigest(),review_decision='GO',phases=len(phases),
        current_admission_authority=False,scope='genuine historical admission11b metadata only; grants no admission14')


PREP02_ACCEPTANCE='''+repr(prep02)+'''


def check_preparation02_consumed(held):
    """Accepted preparation02 bound runtime11 (packet 11b); its retained stage is never inspected here."""
    values={}
    for role,row in PREP02_ACCEPTANCE.items():
        value,raw=held.json(ROOT/row['path'],row,1024**2)
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],role
        values[role]=value
    config,result,audit,cli=(values[k] for k in ('configuration','result','independent_audit','externally_observed_auditor_cli'))
    assert config['kind']=='puck-cpu-held-runtime-allocation-v12' and config['stage_parent']=='/tmp/palimpsest-puck-cpu-held-02'
    assert result['kind']=='puck-cpu-held-runtime-outcome-v12' and result['status']=='prepared' and result['stage_parent']==config['stage_parent']
    assert result['staged_roots']==[dict(device=55,inode=10400+index,root_index=index) for index in range(4)]
    assert audit['kind']=='puck-cpu-held-runtime-independent-audit-v12' and audit['status']=='PASS' and audit['allocation_id']==12
    assert audit['auditor_source_sha256']=='04192a3ba3d7020a5399465aa6da4f7d7ebe3d74172e4b448ea500b09aa9a62b'
    assert cli['kind']=='externally-observed-cpu-auditor-cli-v1' and cli['observed_returncode']==0
    # Consumed: runtime11 bound exactly these pins; check_consumed11 binds its failure.
    assert os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-11/supervision.json')
    return dict(status='ACCEPTED_CONSUMED_BY_RUNTIME11',configuration_sha256=PREP02_ACCEPTANCE['configuration']['sha256'],
        result_sha256=PREP02_ACCEPTANCE['result']['sha256'],stage_parent=config['stage_parent'],staged_roots=result['staged_roots'],
        stage_inspected=False,scope='accepted preparation02 metadata; its stage is retained and never read by these controls')


'''
block11=block11.replace('@STDERR_SIZE@',str(stderr_size)).replace('@STDERR_SHA@',stderr_sha)
anchor="PREP_CONFIGURATION='docs/plans/puck-cpu-held-preparation-02.json'\n"
assert text.count(anchor)==1
text=text.replace(anchor,block11+anchor)


def replace(old,new,count=1):
    global text
    assert text.count(old)==count,(old[:90],text.count(old))
    text=text.replace(old,new)


replace("PREP_SHA='1acfb10b40d561b8e56c96f4cd0d59ee1f00b4d0a14f62c80ffe64e22e1de3ed'","PREP_SHA='f915023564ace5cfe61bd034fc24f8ee6f33ebce0c783875b52ce2cf49def54d'")
replace("RESULT_SHA='4ef13965e6f312a0bcdef9c49e57190f6a9526988f20f1959357bcc31400e0d4'","RESULT_SHA='c7e6c0e8baf8daf2d221b5a3510cd586fedc50de71c3bd2b21cc8c36e79dfebf'")
replace("PREP_CONFIGURATION='docs/plans/puck-cpu-held-preparation-02.json'\nPREP_OUTPUT='runs/puck-cpu-held-preparation-02'\nPREP_STAGE='/tmp/palimpsest-puck-cpu-held-02'\n",
    "PREP_CONFIGURATION='docs/plans/puck-cpu-held-preparation-03.json'\nPREP_OUTPUT='runs/puck-cpu-held-preparation-03'\nPREP_STAGE='/tmp/palimpsest-puck-cpu-held-03'\n")
old_roots=[dict(device=55,inode=10400+i,root_index=i) for i in range(4)]
replace('PREP_ROOTS='+repr(old_roots)+'\n','PREP_ROOTS='+repr(roots)+'\n')
start=text.index('EMPTY_DIRECTORIES=');end=text.index('\n',start)
text=text[:start]+'EMPTY_DIRECTORIES='+repr(empty)+text[end:]
replace('def check_preparation02(held,m,current,frozen):\n    """Accepted preparation02 metadata only;','def check_preparation03(held,m,current,frozen):\n    """Accepted preparation03 metadata only;')
replace("assert prior==config and accepted==prep and audit['allocation_id']==12 and audit['status']=='PASS'","assert prior==config and accepted==prep and audit['allocation_id']==13 and audit['status']=='PASS'")
replace("dict(status='ACCEPTED_PREPARATION02',","dict(status='ACCEPTED_PREPARATION03',")
replace("    for epoch in ('07','08','09','10'):\n","    for epoch in ('07','08','09','10','11'):\n")
replace("    missing.append(ROOT/'runs/puck-cpu-held-qualification-10/baseline-after.json')\n",
    "    missing.append(ROOT/'runs/puck-cpu-held-qualification-10/baseline-after.json')\n"
    "    missing.extend(ROOT/('runs/puck-cpu-held-qualification-11/'+name) for name in ('result.json','baseline-after.json'))\n")
replace('raw_paths.update(HISTORICAL10_JSON)','raw_paths.update(HISTORICAL10_JSON)\n            raw_paths.update(HISTORICAL11_JSON)')
replace('raw_paths.update(ADMISSION02_PINS)','raw_paths.update(ADMISSION02_PINS)\n            raw_paths.update(ADMISSION11B_PINS)\n            raw_paths.update(row[\'path\'] for row in PREP02_ACCEPTANCE.values())')
replace("            current.configuration(frozen,False)\n",
    "            current.configuration(frozen,False)\n"
    "            # Extended-clock epoch 14 only: parent 360/375/390s; worker 360s; observer 400/415s.\n"
    "            assert (frozen['limits']['normal_seconds'],frozen['limits']['child_hard_seconds'],frozen['limits']['hard_seconds'])==(360,375,390)\n")
replace('config,configraw,prep,prepraw,preparation02=check_preparation02(held,m,current,frozen)','config,configraw,prep,prepraw,preparation03=check_preparation03(held,m,current,frozen)')
replace("            consumed10=check_consumed10(held)\n","""            consumed10=check_consumed10(held)
            consumed11=check_consumed11(held)
            admitted11,_=held.json(ROOT/'docs/plans/puck-cpu-held-qualification-11.json',dict(size_bytes=9048,sha256=HISTORICAL11_JSON['docs/plans/puck-cpu-held-qualification-11.json']),1024**2,lf=True)
            consumed_admission11b=check_consumed_admission11b(held,admitted11)
            preparation02=check_preparation02_consumed(held)
""")
replace('(409733,56248874),(409734,56248875)]:','(409733,56248874),(409734,56248875),(325632,3798844),(325635,3798844),(325642,3798845)]:')
replace("process_scope='fifteen recorded identities only;","process_scope='eighteen recorded identities only;")
replace('qualifications01_02_03_04_05_06_07_08_09_10_still_failed_consumed=True','qualifications01_02_03_04_05_06_07_08_09_10_11_still_failed_consumed=True')
replace('qualification10_invoked=True,qualification11_invoked=False,','qualification10_invoked=True,qualification11_invoked=True,qualification14_invoked=False,')
replace('qualification10_failure=consumed10,preparation02=preparation02,',
    'qualification10_failure=consumed10,qualification11_failure=consumed11,admission11b=consumed_admission11b,preparation03=preparation03,preparation02=preparation02,')
compile(text,str(path),'exec');path.write_text(text)
print(json.dumps(dict(preparation03_bound=True,runtime11_consumed=True,admission11b_consumed=True,preparation02_consumed=True,
    historical11_roles=len(historical11),admission11b_roles=len(admission11b),empty_directories=len(empty),historical_missing_receipts=19,
    process_samples=18,admission_or_runtime_invoked=False,stages_touched=False),indent=2,sort_keys=True))
