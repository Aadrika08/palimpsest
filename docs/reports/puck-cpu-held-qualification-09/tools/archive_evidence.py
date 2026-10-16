"""PREPARED ONLY. Archive measured terminal09 FAIL, never run a control/runtime.

Root must fill OUTCOME_REVIEW_SHA after independent review. POST_SHA binds the
root43-pin post observation; that manifest authenticates measured small records.
Source/control/input origins have separate Git/previous-index proofs. No optional
phase/cost count becomes acceptance, and no current full-payload custody is claimed.
"""
from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import stat
import subprocess
import sys
import time

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PACKET=ROOT/'docs/reports/puck-cpu-held-qualification-09'
CONTROL='60e5756d8c670e898320b26b3a2cee267577e53c'
SOURCE='96ace37062fd14e20ae1ebd2371b90fa88f8d7ab'
CONFIG='docs/plans/puck-cpu-held-qualification-09.json'
CONFIG_SHA='2c441b2465c86baf2982a5c023ce5923c1c144bd5789576807ffee6f19beb6c0'
TRANSPORT_SHA=None
AUDIT_SHA=None
OUTCOME_REVIEW_SHA='322da785615245e03f497570cc102be61dad7f87dbbdb4bf5cd7ffa1340c5f3e'
POST_SHA='ccc44e35bb01a6abbfbe02f1d086915929d1cbfea759e34f31252b86e86a179a'
POST=Path('/tmp/palimpsest-held09-post-outcome-observation.json')
META_LIMIT=8*1024**2
LEAF_LIMIT=16*1024**2
TOTAL_LIMIT=64*1024**2
CONTROL_PATHS=tuple('docs/plans/puck-cpu-held-qualification-09'+suffix for suffix in ('-admission.py', '-control-selfcheck.py', '-control-selfcheck01.json', '-execution.json', '-external.py', '-freeze.json', '-independent-controls-review.json', '-proof-roster-review.json', '-review.md', '-source-evidence/admission-before08-extension.py', '-source-evidence/admission-before08-raw-roles.py', '-source-evidence/authoring-setup-failure01.json', '-source-evidence/before-source-rollout.json', '-source-evidence/consumed08-assembly-fragment.py', '-source-evidence/freeze-builder.py', '-source-evidence/freeze-map.json', '-source-evidence/history-check-record.json', '-source-evidence/history-check.py', '-source-evidence/history-green01/admission.py', '-source-evidence/history-green01/command.json', '-source-evidence/history-green01/history-check.py', '-source-evidence/history-green01/stderr.log', '-source-evidence/history-green01/stdout.log', '-source-evidence/history-green01/terminal.json', '-source-evidence/history-red01/command.json', '-source-evidence/history-red02/admission-before.py', '-source-evidence/history-red02/command.json', '-source-evidence/history-red02/history-check.py', '-source-evidence/history-red02/stderr.log', '-source-evidence/history-red02/stdout.log', '-source-evidence/history-red02/terminal.json', '-source-evidence/history-red03/admission-before.py', '-source-evidence/history-red03/command.json', '-source-evidence/history-red03/history-check.py', '-source-evidence/history-red03/stderr.log', '-source-evidence/history-red03/stdout.log', '-source-evidence/history-red03/terminal.json', '-wrapper-proof.json', '.json'))
# Outcome utility authoring failures are evidence, not allocation retries.
REQUIRED_TMP=tuple('palimpsest-held09-'+phase+'-tool-terminal.json' for phase in ('admission','observer','audit'))+(
    'palimpsest-puck-cpu-held-qualification-09-admission-01.json',
    'palimpsest-puck-cpu-held-qualification-09-audit-01.json',
    'palimpsest-held09-admission-receipt-review.json',
    'palimpsest-held09-pre-admission-guard01.json','palimpsest-held09-pre-admission-guard.py',
    'palimpsest-held09-pre-observer-guard01.json','palimpsest-held09-pre-observer-guard.py',
    'palimpsest-held09-bind-audit-command.py','palimpsest-held09-concrete-audit-command.json',
    'palimpsest-held09-post-outcome-observation.json','palimpsest-held09-outcome-review.json',
    'palimpsest-held09-post-outcome-observation-before-readstamp-fix.py',
    'palimpsest-held09-post-outcome-observation.py',
    'palimpsest-held09-post-observation-authoring-failure01.json',
    'palimpsest-held09-readstamp-observation01.json')
OPTIONAL_TMP=()
DEADLINE=None


def clock():
    if DEADLINE is not None and time.monotonic()>=DEADLINE:
        raise TimeoutError('Finite evidence archive deadline')


def stamp(value):
    return (value.st_dev,value.st_ino,value.st_mode,value.st_nlink,value.st_size,
            value.st_mtime_ns,value.st_ctime_ns)


def read(path,maximum=META_LIMIT):
    clock();path=Path(path)
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and 0<=before.st_size<=maximum,str(path)
        parts=[];size=0
        while True:
            clock();block=os.read(fd,1024**2)
            if not block:break
            size+=len(block);assert size<=maximum,str(path);parts.append(block)
        raw=b''.join(parts)
        assert len(raw)==before.st_size and stamp(before)==stamp(os.fstat(fd))==stamp(path.lstat()),str(path)
        return raw
    finally:os.close(fd)


def git(*arguments):
    clock()
    return subprocess.check_output(['/usr/bin/git',*arguments],cwd=ROOT,timeout=10)


def main():
    global DEADLINE,TRANSPORT_SHA,AUDIT_SHA
    assert len(sys.argv)==1 and not os.path.lexists(PACKET)
    assert len(OUTCOME_REVIEW_SHA)==64 and all(c in '0123456789abcdef' for c in OUTCOME_REVIEW_SHA), 'Root must pin independent outcome review'
    DEADLINE=time.monotonic()+60
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,70)
    assert git('rev-parse','HEAD').decode().strip()==CONTROL
    assert git('status','--porcelain')==b''
    assert len(CONTROL_PATHS)==len(set(CONTROL_PATHS))==39
    assert git('diff','--name-only',SOURCE,CONTROL).decode().splitlines()==list(CONTROL_PATHS)
    # No allocation tree is opened until all three measured tool records are final.
    post_raw=read(POST);assert hashlib.sha256(post_raw).hexdigest()==POST_SHA
    post=json.loads(post_raw);assert post['source_commit']==SOURCE and post['control_commit']==CONTROL
    assert post['status']=='FAILED_CONSUMED' and post['qualification_status']=='FAIL'
    assert post['configuration_sha256']==CONFIG_SHA and post['observer_invocations']==1 and post['independent_auditor_invocations']==1
    assert type(post['pins']) is list and len(post['pins'])==43
    post_pins={}
    for row in post['pins']:
        path=Path(row['path']);digest=row['sha256']
        assert path.is_absolute() and '..' not in path.parts and str(path) not in post_pins
        assert type(row['size_bytes']) is int and 0<=row['size_bytes']<=LEAF_LIMIT
        assert len(digest)==64 and all(c in '0123456789abcdef' for c in digest)
        post_pins[str(path)]=row
    TRANSPORT_SHA=post['transport_sha256'];AUDIT_SHA=post['independent_audit_sha256']
    for phase in ('admission','observer','audit'):
        path=Path('/tmp/palimpsest-held09-'+phase+'-tool-terminal.json');raw=read(path);pin=post_pins[str(path)]
        assert len(raw)==pin['size_bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256']
        terminal=json.loads(raw)
        assert terminal['kind']=='root-observed-held09-tool-terminal-v1' and terminal['phase']==phase
        assert terminal['observed_complete'] is True and terminal['implicit_retry'] is False
        assert type(terminal['exit_code']) is int and terminal['exit_code']==(0 if phase=='admission' else 1)
        assert type(terminal['initial_tool_chunk']) is str and terminal['initial_tool_chunk']
        assert type(terminal['final_tool_chunk']) is str and terminal['final_tool_chunk']
        assert terminal['session_id'] is None or type(terminal['session_id']) is int
    configraw=read(ROOT/CONFIG)
    assert hashlib.sha256(configraw).hexdigest()==CONFIG_SHA
    config=json.loads(configraw)
    assert config['kind']=='puck-cpu-held-runtime-allocation-v9' and config['version']==config['allocation_id']==9
    assert config['root']==str(ROOT) and config['phase']=='qualify'
    assert len(config['sources'])==24 and len(config['inputs'])==16 and len(config['preparation_acceptance'])==4
    pairs={};expected={};git_origins={}
    def reserve(original,archive,pin=None,revision=None):
        original=Path(original);relative=Path(archive)
        assert original.is_absolute() and not relative.is_absolute() and '..' not in relative.parts
        assert archive not in pairs,archive
        pairs[archive]=original
        if pin is not None:expected[archive]=pin
        if revision is not None:git_origins[archive]=revision
    source_paths=sorted([row['path'] for row in config['sources']]+[
        'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py'])
    assert len(source_paths)==len(set(source_paths))==26
    for name in source_paths:
        blob=git('show',SOURCE+':'+name);assert len(blob)<=META_LIMIT and read(ROOT/name)==blob,name
        reserve(ROOT/name,'source/'+name,dict(size_bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()),SOURCE)
    for name in sorted(CONTROL_PATHS):
        blob=git('show',CONTROL+':'+name);assert len(blob)<=META_LIMIT and read(ROOT/name)==blob,name
        reserve(ROOT/name,'controls/'+name,dict(size_bytes=len(blob),sha256=hashlib.sha256(blob).hexdigest()),CONTROL)
    old_index_path='docs/reports/puck-cpu-held-qualification-08/evidence-index.json'
    old_index_raw=read(ROOT/old_index_path)
    assert old_index_raw==git('show',SOURCE+':'+old_index_path)
    old_inputs={str(Path(row['original_path']).relative_to(ROOT)):row
        for row in json.loads(old_index_raw)['artifacts'] if row['archived_path'].startswith('inputs/')}
    raw_paths={row['path'] for row in config['inputs'].values()}
    raw_paths.update(row['path'] for row in config['preparation_acceptance'].values())
    raw_paths.add('docs/plans/puck-cpu-observed-import-profile-candidate-01.json')
    raw_paths.update('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json' for i in range(1,7))
    assert set(old_inputs)==raw_paths and len(raw_paths)==27
    for name in sorted(raw_paths):reserve(ROOT/name,'inputs/'+name,old_inputs[name])
    allocation=ROOT/'runs/puck-cpu-held-qualification-09'
    state=allocation.lstat();assert stat.S_ISDIR(state.st_mode)
    file_count=directory_count=0
    for directory,dirs,files in os.walk(allocation,topdown=True,followlinks=False):
        clock();directory_count+=1;assert directory_count<=128
        for name in dirs:
            assert stat.S_ISDIR((Path(directory)/name).lstat().st_mode)
        for name in files:
            original=Path(directory)/name;file_count+=1;assert file_count<=256
            reserve(original,'raw/'+str(original.relative_to(allocation)))
    assert file_count>0
    for suffix in ('.stdout','.stderr','-transport.json'):
        p=ROOT/('runs/puck-cpu-held-qualification-09-external-cli'+suffix)
        reserve(p,'transport/'+p.name)
    for phase in ('admission','observer','audit'):
        for suffix in ('.json','.stdout','.stderr'):
            p=Path('/tmp/palimpsest-held09-'+phase+'-external'+suffix)
            reserve(p,'external/'+p.name)
    for name in REQUIRED_TMP:
        reserve(Path('/tmp')/name,('tools/' if name.endswith('-tool-terminal.json') else 'observations/')+name)
    missing_optional=[]
    for name in OPTIONAL_TMP:
        p=Path('/tmp')/name
        if os.path.lexists(p):reserve(p,'observations/'+name)
        else:missing_optional.append(str(p))
    reserve(Path(__file__).resolve(),'tools/archive_evidence.py')
    verifier='docs/reports/puck-cpu-held-qualification-08/verify_evidence.py'
    verifier_raw=read(ROOT/verifier)
    assert hashlib.sha256(verifier_raw).hexdigest()=='d5b874df818e72295d6951873e25a6fc8fc0deb0a79ec6183ca805508c19a759'
    assert verifier_raw==git('show',SOURCE+':'+verifier)
    reserve(ROOT/verifier,'verify_evidence.py')
    attributes='docs/reports/puck-cpu-held-preparation-01/.gitattributes'
    assert read(ROOT/attributes)==b'* -text\n' and read(ROOT/attributes)==git('show',SOURCE+':'+attributes)
    reserve(ROOT/attributes,'.gitattributes')
    measured={str(path) for archive,path in pairs.items() if archive.startswith(('raw/','transport/','external/'))}
    measured.update('/tmp/palimpsest-held09-'+phase+'-tool-terminal.json' for phase in ('admission','observer','audit'))
    measured.update('/tmp/palimpsest-puck-cpu-held-qualification-09-'+phase+'-01.json' for phase in ('admission','audit'))
    assert measured<=set(post_pins),sorted(measured-set(post_pins))
    for archive,path in pairs.items():
        if str(path) in post_pins:
            pin=post_pins[str(path)]
            if archive in expected:assert all(expected[archive][key]==pin[key] for key in ('size_bytes','sha256'))
            expected[archive]=pin
    payloads={};rows=[];total=0
    for archive,original in sorted(pairs.items()):
        raw=read(original,LEAF_LIMIT if archive.startswith(('raw/','transport/','external/')) else META_LIMIT)
        digest=hashlib.sha256(raw).hexdigest();pin=expected.get(archive)
        if pin is not None:assert len(raw)==pin['size_bytes'] and digest==pin['sha256'],archive
        total+=len(raw);assert total<=TOTAL_LIMIT
        payloads[archive]=raw
        row=dict(archived_path=archive,original_path=str(original),size_bytes=len(raw),sha256=digest)
        if archive in git_origins:row['original_git_revision']=git_origins[archive]
        rows.append(row)
    transport_raw=payloads['transport/puck-cpu-held-qualification-09-external-cli-transport.json']
    assert hashlib.sha256(transport_raw).hexdigest()==TRANSPORT_SHA
    transport=json.loads(transport_raw)
    assert transport['kind']=='puck-cpu-held-cli-transport-v1' and transport['phase']=='qualify'
    assert transport['configuration_sha256']==CONFIG_SHA and type(transport['observed_returncode']) is int
    assert transport['observed_returncode']==1 and transport['timed_out'] is False
    for name in ('stdout','stderr'):
        row=transport[name];assert row['path']=='runs/puck-cpu-held-qualification-09-external-cli.'+name
        raw=payloads['transport/'+Path(row['path']).name]
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    freeze=json.loads(payloads['controls/docs/plans/puck-cpu-held-qualification-09-freeze.json'])
    concrete=json.loads(payloads['observations/palimpsest-held09-concrete-audit-command.json'])
    command=concrete['command'];prefix=freeze['commands']['auditor_prefix']
    assert command[:len(prefix)]==prefix and command[len(prefix)]==TRANSPORT_SHA
    assert command[-2:]==['--output',freeze['commands']['auditor_output']] and len(command)==len(prefix)+3
    for phase in ('admission','observer','audit'):
        terminal=json.loads(payloads['tools/palimpsest-held09-'+phase+'-tool-terminal.json'])
        assert terminal['kind']=='root-observed-held09-tool-terminal-v1' and terminal['phase']==phase
        assert terminal['observed_complete'] is True and terminal['implicit_retry'] is False
        assert type(terminal['exit_code']) is int and terminal['exit_code']==(0 if phase=='admission' else 1)
        receipt=json.loads(payloads['external/palimpsest-held09-'+phase+'-external.json'])
        assert receipt==post['outer_transports'][phase]
        assert receipt['phase']==phase and receipt['kind']=='puck-cpu-held09-external-transport-v1'
        assert receipt['returncode']==(0 if phase=='admission' else 1) and receipt['normal_exit'] is True and receipt['timed_out'] is False
        assert receipt['command']==(command if phase=='audit' else freeze['commands'][phase])
        assert receipt['environment']==freeze['outer_environment'] and receipt['cwd']==str(ROOT)
        assert receipt['implicit_retry'] is False and receipt['runtime_qualified'] is False and receipt['study_authorized'] is False
        for name in ('stdout','stderr'):
            row=receipt[name];assert row['path']=='/tmp/palimpsest-held09-'+phase+'-external.'+name
            raw=payloads['external/palimpsest-held09-'+phase+'-external.'+name]
            assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    admission_raw=payloads['observations/palimpsest-puck-cpu-held-qualification-09-admission-01.json'];admission=json.loads(admission_raw)
    assert admission['status']=='DATA_ONLY_ADMITTED' and admission['configuration_sha256']==CONFIG_SHA
    assert payloads['external/palimpsest-held09-admission-external.stdout']==admission_raw
    assert payloads['external/palimpsest-held09-observer-external.stdout']==transport_raw
    audit_raw=payloads['observations/palimpsest-puck-cpu-held-qualification-09-audit-01.json']
    assert hashlib.sha256(audit_raw).hexdigest()==AUDIT_SHA
    audit=json.loads(audit_raw)
    assert audit['status']=='FAIL' and audit['kind']=='puck-cpu-held-runtime-independent-audit-v1'
    assert audit['configuration_sha256']==CONFIG_SHA and audit['transport_sha256']==TRANSPORT_SHA
    assert audit['error']=='Normal external transport exit required'
    assert audit['version']==1 and audit['auditor_source_sha256']==hashlib.sha256(payloads['source/scripts/audit_puck_cpu_held_runtime.py']).hexdigest()
    assert payloads['external/palimpsest-held09-audit-external.stdout']==audit_raw
    for value in (admission,audit,post):
        assert value['qualification_claims']==[]
        assert all(value[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    assert payloads['raw/configuration.json']==configraw
    assert payloads['raw/logs/stdout.log']==b''
    diagnostic_raw=payloads['raw/logs/stderr.log'];diagnostics=[];unparsed=0
    # Diagnostic content is retained/described, never a runtime acceptance gate.
    for line in diagnostic_raw.splitlines():
        try:
            value=json.loads(line)
            if type(value) is dict:diagnostics.append(value)
            else:unparsed+=1
        except (ValueError,UnicodeError):unparsed+=1
    phases=[v for v in diagnostics if v.get('kind')=='puck-worker-phase-v1']
    costs=[v for v in diagnostics if v.get('kind')=='puck-worker-guard-cost-v1']
    supervision=json.loads(payloads['raw/supervision.json'])
    assert supervision['status']=='failed' and supervision['failure']=='normal-return deadline'
    assert supervision['returncode']==-15 and supervision['matching_survivors']==[] and supervision==post['supervision']
    assert payloads['observations/'+POST.name]==post_raw
    assert post['completed_four_import_receipt'] is False and post['parent_closure_receipt'] is False
    assert post['post_failure_full_payload_custody'] is False and post['runtime_qualified'] is False
    outcome_review_raw=payloads['observations/palimpsest-held09-outcome-review.json']
    assert hashlib.sha256(outcome_review_raw).hexdigest()==OUTCOME_REVIEW_SHA
    outcome_review=json.loads(outcome_review_raw);assert type(outcome_review) is dict
    assert outcome_review['status']=='PASS_FAILED_OUTCOME_RECORD_NO_RUNTIME_ACCEPTANCE'
    assert outcome_review['material_findings']==[]
    assert 'raw/result.json' not in payloads and 'raw/baseline-after.json' not in payloads
    missing=[str(allocation/name) for name in ('result.json','baseline-after.json')]
    assert all(not os.path.lexists(path) for path in missing) and post['missing_original_paths']==missing
    index=dict(kind='puck-cpu-held-qualification09-evidence-index-v1',version=1,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),control_commit=CONTROL,source_commit=SOURCE,
        source_paths=source_paths,control_paths=sorted(CONTROL_PATHS),artifact_count=len(rows),total_bytes=total,
        empty_files=sum(row['size_bytes']==0 for row in rows),artifacts=rows,missing_original_paths=missing,
        optional_missing_original_paths=missing_optional,actual09_invoked=True,archival_only=True,
        parent_status='ABSENT',independent_audit_status='FAIL',qualification_status='FAIL',
        qualifications01_09_consumed=True,observer_invocations_in_retained_record=1,
        parent_closure_receipt=False,completed_four_import_receipt=False,post_failure_full_payload_custody=False,
        diagnostic_records=len(diagnostics),phase_records=len(phases),cost_records=len(costs),unparsed_diagnostic_lines=unparsed,worker_stderr_bytes=len(diagnostic_raw),worker_stdout_bytes=0,last_diagnostic=diagnostics[-1] if diagnostics else None,last_phase=phases[-1] if phases else None,last_guard_cost=costs[-1] if costs else None,root_post_observation_sha256=POST_SHA,independent_outcome_review_sha256=OUTCOME_REVIEW_SHA,
        retained_supervision=supervision,
        failure_phase=post['cause'],
        independent_audit_boundary='Early nonzero transport refusal; not a passing byte audit or post-run full custody proof.',
        observed_external_returncode=transport['observed_returncode'],observed_external_timed_out=transport['timed_out'],
        runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,
        executable=False,qualification_claims=[],implicit_retry=False,all_seven_release_gates_open=True,
        complete_post_run_payload_custody='NOT_ESTABLISHED_BY_ARCHIVAL',
        preserved_prior_evidence='Original08 index supplies27 unchanged input origins. Prior frozen/source/history packets are not recursively duplicated.',
        limitations=['Byte-preserving terminal archive only; not an independent current-byte or runtime acceptance audit.',
            'Missing result/baseline-after remain explicitly missing; no receipt or cause is fabricated.',
            'Optional diagnostics are unauthenticated/incomplete cumulative observations, not acceptance, exclusive time, exhaustive work or timeout-cause proof.',
            'Recorded process samples are sequential and nonexhaustive, not complete lifetime closure.',
            'No installed/staged/native payload was read or imported by this archive tool.'])
    clock();PACKET.mkdir()
    for archive,raw in payloads.items():
        clock();p=PACKET/archive;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        assert read(p,LEAF_LIMIT)==raw
    raw=(json.dumps(index,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    assert len(raw)<=META_LIMIT
    with (PACKET/'evidence-index.json').open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    assert read(PACKET/'evidence-index.json')==raw
    clock()
    print(json.dumps(dict(packet=str(PACKET),artifacts=len(rows),bytes=total,
        index_sha256=hashlib.sha256(raw).hexdigest(),parent_status=index['parent_status'],
        independent_audit_status=index['independent_audit_status'],runtime_qualified=False),sort_keys=True))
    clock();signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':main()
