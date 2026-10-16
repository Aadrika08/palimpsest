"""Archive the terminal08 record only; never invoke a control or target runtime."""
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
PACKET=ROOT/'docs/reports/puck-cpu-held-qualification-08'
CONTROL='2f74653367f14f0156479a52314f625d7400fc57'
SOURCE='f5523dc69c8d05ee2f3ff1118c633512c4b6a2e0'
CONFIG='docs/plans/puck-cpu-held-qualification-08.json'
CONFIG_SHA='67076970caffe64b6162c4344f11d943b620dd2e0fb43ace72e39f508fa7ee60'
TRANSPORT_SHA='d80f60a10cf611c660e5bda25bf6f055c49415686681db33ca6ae44f868841b4'
AUDIT_SHA='93fb936dcf82bcf46a592026e8744c5900bf5bd9b283465d5e5dfad13d346ba9'
OUTCOME_REVIEW_SHA='f18ed67138057690b8f6b1c5b4101f7949b403860f17dca465fb4ece1e149741'
META_LIMIT=8*1024**2
LEAF_LIMIT=16*1024**2
TOTAL_LIMIT=64*1024**2
CONTROL_PATHS=tuple(sorted(('docs/plans/puck-cpu-held-qualification-08'+suffix for suffix in (
    '.json','-admission.py','-freeze.json','-execution.json','-external.py',
    '-review.md','-independent-review.json','-proof-roster-review.json'))))+tuple(
    'docs/plans/puck-cpu-held-qualification-08-source-evidence/'+name for name in (
    'control-revision02.py','control-selfcheck01.json','control-selfcheck01.py',
    'control-selfcheck02.json','control-selfcheck02.py','freeze-builder.py',
    'history-admission-before.py','history-check-record.json','history-check.py',
    'history-green01.stderr','history-green01.stdout','history-green02.stderr',
    'history-green02.stdout','history-red01.stderr','history-red01.stdout',
    'history-red02.stderr','history-red02.stdout','history-warm-check-record.json',
    'history-warm-check.py','pre-review01/admission-warm-red.py',
    'pre-review01/puck-cpu-held-qualification-08-admission.py',
    'pre-review01/puck-cpu-held-qualification-08-execution.json',
    'pre-review01/puck-cpu-held-qualification-08-external.py',
    'pre-review01/puck-cpu-held-qualification-08-freeze.json',
    'pre-review01/puck-cpu-held-qualification-08.json'))
# Final exact original paths; outcome review must exist before root runs this tool.
REQUIRED_TMP=tuple('palimpsest-held08-'+phase+'-tool-terminal.json'
    for phase in ('admission','observer','audit'))+(
    'palimpsest-puck-cpu-held-qualification-08-admission-01.json',
    'palimpsest-puck-cpu-held-qualification-08-audit-01.json',
    'palimpsest-held08-admission-receipt-review.json',
    'palimpsest-held08-pre-admission-guard-01.json',
    'palimpsest-held08-pre-observer-guard-01.json',
    'palimpsest-held08-pre-observer-guard.py',
    'palimpsest-held08-bind-audit-command.py',
    'palimpsest-held08-concrete-audit-command.json',
    'palimpsest-held08-post-outcome-observation.json',
    'palimpsest-held08-outcome-review.json')
# These controls reviews are already committed among the33 control files.
OPTIONAL_TMP=(
    'palimpsest-held08-proof-roster-review.json',
    'palimpsest-held08-independent-controls-review.json',
)
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
    global DEADLINE
    assert len(sys.argv)==1 and not os.path.lexists(PACKET)
    DEADLINE=time.monotonic()+60
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,70)
    assert git('rev-parse','HEAD').decode().strip()==CONTROL
    assert git('status','--porcelain')==b''
    assert len(CONTROL_PATHS)==len(set(CONTROL_PATHS))==33
    configraw=read(ROOT/CONFIG)
    assert hashlib.sha256(configraw).hexdigest()==CONFIG_SHA
    config=json.loads(configraw)
    assert config['kind']=='puck-cpu-held-runtime-allocation-v8' and config['version']==config['allocation_id']==8
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
    old_index_path='docs/reports/puck-cpu-held-qualification-07/evidence-index.json'
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
    allocation=ROOT/'runs/puck-cpu-held-qualification-08'
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
        p=ROOT/('runs/puck-cpu-held-qualification-08-external-cli'+suffix)
        reserve(p,'transport/'+p.name)
    for phase in ('admission','observer','audit'):
        for suffix in ('.json','.stdout','.stderr'):
            p=Path('/tmp/palimpsest-held08-'+phase+'-external'+suffix)
            reserve(p,'external/'+p.name)
    for name in REQUIRED_TMP:
        reserve(Path('/tmp')/name,('tools/' if name.endswith('-tool-terminal.json') else 'observations/')+name)
    missing_optional=[]
    for name in OPTIONAL_TMP:
        p=Path('/tmp')/name
        if os.path.lexists(p):reserve(p,'observations/'+name)
        else:missing_optional.append(str(p))
    reserve(Path(__file__).resolve(),'tools/archive_evidence.py')
    verifier='docs/reports/puck-cpu-held-qualification-07/verify_evidence.py'
    verifier_raw=read(ROOT/verifier)
    assert hashlib.sha256(verifier_raw).hexdigest()=='d5b874df818e72295d6951873e25a6fc8fc0deb0a79ec6183ca805508c19a759'
    assert verifier_raw==git('show',SOURCE+':'+verifier)
    reserve(ROOT/verifier,'verify_evidence.py')
    attributes='docs/reports/puck-cpu-held-preparation-01/.gitattributes'
    assert read(ROOT/attributes)==b'* -text\n' and read(ROOT/attributes)==git('show',SOURCE+':'+attributes)
    reserve(ROOT/attributes,'.gitattributes')
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
    transport_raw=payloads['transport/puck-cpu-held-qualification-08-external-cli-transport.json']
    assert len(transport_raw)==951 and hashlib.sha256(transport_raw).hexdigest()==TRANSPORT_SHA
    transport=json.loads(transport_raw)
    assert transport['kind']=='puck-cpu-held-cli-transport-v1' and transport['phase']=='qualify'
    assert transport['configuration_sha256']==CONFIG_SHA and type(transport['observed_returncode']) is int
    assert transport['observed_returncode']==1 and transport['timed_out'] is False
    for name in ('stdout','stderr'):
        row=transport[name];assert row['path']=='runs/puck-cpu-held-qualification-08-external-cli.'+name
        raw=payloads['transport/'+Path(row['path']).name]
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    for phase in ('admission','observer','audit'):
        terminal=json.loads(payloads['tools/palimpsest-held08-'+phase+'-tool-terminal.json'])
        assert terminal['kind']=='root-observed-tool-terminal-v1' and terminal['phase']==phase
        assert terminal['chunk_id']=={'admission':'b49266','observer':'53521c','audit':'01c752'}[phase]
        assert type(terminal['exit_code']) is int and terminal['exit_code']==(0 if phase=='admission' else 1)
        envelope=json.loads(payloads['controls/docs/plans/puck-cpu-held-qualification-08-execution.json'])
        assert terminal['command']==envelope['commands'][phase] and terminal['environment']==envelope['environment']
        receipt=json.loads(payloads['external/palimpsest-held08-'+phase+'-external.json'])
        assert receipt['phase']==phase and receipt['kind']=='puck-cpu-held08-external-transport-v1'
        assert receipt['returncode']==(0 if phase=='admission' else 1) and receipt['normal_exit'] is True and receipt['timed_out'] is False
        for name in ('stdout','stderr'):
            row=receipt[name];raw=payloads['external/palimpsest-held08-'+phase+'-external.'+name]
            assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
    audit_raw=payloads['observations/palimpsest-puck-cpu-held-qualification-08-audit-01.json']
    assert len(audit_raw)==616 and hashlib.sha256(audit_raw).hexdigest()==AUDIT_SHA
    audit=json.loads(audit_raw)
    assert audit['status']=='FAIL' and audit['kind']=='puck-cpu-held-runtime-independent-audit-v1'
    assert audit['configuration_sha256']==CONFIG_SHA and audit['transport_sha256']==TRANSPORT_SHA
    assert audit['error']=='Normal external transport exit required'
    assert payloads['raw/logs/stdout.log']==b''
    diagnostic_raw=payloads['raw/logs/stderr.log'];assert len(diagnostic_raw)==1469
    diagnostics=[json.loads(line) for line in diagnostic_raw.splitlines()]
    assert len(diagnostics)==11 and [v['sequence'] for v in diagnostics]==list(range(1,12))
    assert all(v['kind']=='puck-worker-phase-v1' and v['diagnostic_only'] is True for v in diagnostics)
    assert diagnostics[-1]['phase']=='import.torchvision.enter'
    supervision=json.loads(payloads['raw/supervision.json'])
    assert supervision['status']=='failed' and supervision['failure']=='normal-return deadline'
    assert supervision['returncode']==-15 and supervision['matching_survivors']==[]
    post=json.loads(payloads['observations/palimpsest-held08-post-outcome-observation.json'])
    assert post['status']=='FAILED_CONSUMED' and post['observer_invocations']==1
    assert post['diagnostic_records']==11 and post['last_diagnostic']==diagnostics[-1]
    assert post['supervision']==supervision and post['worker_stdout_bytes']==0 and post['worker_stderr_bytes']==1469
    assert post['completed_four_import_receipt'] is False and post['parent_closure_receipt'] is False
    assert post['post_failure_full_payload_custody'] is False and post['runtime_qualified'] is False
    outcome_review_raw=payloads['observations/palimpsest-held08-outcome-review.json']
    assert len(outcome_review_raw)==10835 and hashlib.sha256(outcome_review_raw).hexdigest()==OUTCOME_REVIEW_SHA
    outcome_review=json.loads(outcome_review_raw);assert type(outcome_review) is dict
    assert 'raw/result.json' not in payloads and 'raw/baseline-after.json' not in payloads
    missing=[str(allocation/name) for name in ('result.json','baseline-after.json')]
    assert all(not os.path.lexists(path) for path in missing)
    index=dict(kind='puck-cpu-held-qualification08-evidence-index-v1',version=1,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),control_commit=CONTROL,source_commit=SOURCE,
        source_paths=source_paths,control_paths=sorted(CONTROL_PATHS),artifact_count=len(rows),total_bytes=total,
        empty_files=sum(row['size_bytes']==0 for row in rows),artifacts=rows,missing_original_paths=missing,
        optional_missing_original_paths=missing_optional,actual08_invoked=True,archival_only=True,
        parent_status='ABSENT',independent_audit_status='FAIL',qualification_status='FAIL',
        qualifications01_08_consumed=True,observer_invocations_in_retained_record=1,
        parent_closure_receipt=False,completed_four_import_receipt=False,post_failure_full_payload_custody=False,
        diagnostic_records=11,worker_stderr_bytes=1469,worker_stdout_bytes=0,last_diagnostic=diagnostics[-1],
        retained_supervision=supervision,
        failure_phase='Last diagnostic is import.torchvision.enter; exact stalled operation and root cause remain unknown.',
        independent_audit_boundary='Early nonzero transport refusal; not a passing byte audit or post-run full custody proof.',
        observed_external_returncode=transport['observed_returncode'],observed_external_timed_out=transport['timed_out'],
        runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,
        executable=False,qualification_claims=[],implicit_retry=False,all_seven_release_gates_open=True,
        complete_post_run_payload_custody='NOT_ESTABLISHED_BY_ARCHIVAL',
        preserved_prior_evidence='Original07 index supplies27 unchanged input origins. Existing749-pin/source/history packets are not recursively duplicated.',
        limitations=['Byte-preserving terminal archive only; not an independent current-byte or runtime acceptance audit.',
            'Missing result/baseline-after remain explicitly missing; no receipt or cause is fabricated.',
            'No installed/staged/native payload was read or imported by this archive tool.'])
    clock();PACKET.mkdir()
    for archive,raw in payloads.items():
        clock();p=PACKET/archive;p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
        assert read(p,LEAF_LIMIT)==raw
    raw=(json.dumps(index,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    assert len(raw)<=META_LIMIT
    with (PACKET/'evidence-index.json').open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
    print(json.dumps(dict(packet=str(PACKET),artifacts=len(rows),bytes=total,
        index_sha256=hashlib.sha256(raw).hexdigest(),parent_status=index['parent_status'],
        independent_audit_status=index['independent_audit_status'],runtime_qualified=False),sort_keys=True))
    signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':main()
