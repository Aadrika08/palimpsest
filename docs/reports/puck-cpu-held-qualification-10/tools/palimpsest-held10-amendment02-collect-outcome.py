"""Retain terminal metadata only; never execute/import/re-hash runtime payloads."""
from pathlib import Path
import datetime,hashlib,json,os,stat,time
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
base=root/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
allocation=root/'runs/puck-cpu-held-qualification-10'
end=time.monotonic()+45

def read(path):
    assert time.monotonic()<end
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    def stamp(s):return (s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    try:
        before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=16*1024**2
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(16*1024**2+1)
        assert len(raw)==before.st_size and stamp(before)==stamp(os.fstat(fd))==stamp(Path(path).lstat())
        return raw
    finally:os.close(fd)

paths=[]
for directory,dirs,files in os.walk(allocation,followlinks=False):
    assert all(stat.S_ISDIR((Path(directory)/name).lstat().st_mode) for name in dirs)
    paths.extend(Path(directory)/name for name in files)
assert 0<len(paths)<=256
paths += [root/('runs/puck-cpu-held-qualification-10-external-cli'+suffix) for suffix in ('.stdout','.stderr','-transport.json')]
for phase,code in (('admission',0),('observer',1),('audit',1)):
    stem=Path('/tmp/palimpsest-held10-amendment02-'+phase)
    paths.extend(Path(str(stem)+'-external'+suffix) for suffix in ('.json','.stdout','.stderr'))
    paths.extend(Path(str(stem)+'-tool'+suffix) for suffix in ('-command.json','-terminal.json','.stdout','.stderr'))
    terminal=json.loads(read(Path(str(stem)+'-tool-terminal.json')))
    assert terminal['exit_code']==code and terminal['outer_timeout'] is False and terminal['phase']==phase
paths += [Path('/tmp/palimpsest-puck-cpu-held-qualification-10-'+phase+'-'+number+'.json') for phase,number in (('admission','02'),('audit','01'))]
paths += [Path('/tmp/palimpsest-held10-amendment02-'+name+'.json') for name in ('pre-admission-guard01','pre-observer-guard01','independent-admission-review','concrete-audit-command')]
assert len(paths)==len(set(paths))
pins=[];total=0
for path in sorted(paths):
    raw=read(path);total+=len(raw);assert total<=32*1024**2
    pins.append(dict(path=str(path),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
transport_raw=read(root/'runs/puck-cpu-held-qualification-10-external-cli-transport.json')
transport=json.loads(transport_raw);result=json.loads(read(allocation/'result.json'))
audit_raw=read(Path('/tmp/palimpsest-puck-cpu-held-qualification-10-audit-01.json'));audit=json.loads(audit_raw)
supervision=json.loads(read(allocation/'supervision.json'))
assert transport['observed_returncode']==1 and transport['timed_out'] is False
assert result['status']=='FAIL' and result['held_four_imports_observed'] is False
assert audit['status']=='FAIL' and audit['error']=='Normal external transport exit required'
assert audit['transport_sha256']==hashlib.sha256(transport_raw).hexdigest()
assert supervision['status']=='failed' and supervision['returncode']==1 and supervision['failure'] is None
assert supervision['matching_survivors']==[]
assert read(Path('/tmp/palimpsest-held10-amendment02-observer-external.stdout'))==transport_raw
assert read(Path('/tmp/palimpsest-held10-amendment02-audit-external.stdout'))==audit_raw
missing=[str(allocation/'baseline-after.json'),'/tmp/palimpsest-puck-cpu-held-qualification-10-admission-01.json']
before=json.loads(read(base/'historical-before-admission.json'))
for row in before['raw_run_files']:
    raw=read(root/row['path']);assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
missing += [str(root/p) for p in before['historical_absent_paths']]
assert len(missing)==len(set(missing)) and all(not os.path.lexists(p) for p in missing)
samples=[]
for row in supervision['tracked_processes']:
    p=Path('/proc')/str(row['pid'])/'stat'
    try:
        text=p.read_text();fields=text[text.rfind(')')+2:].split();matching=int(fields[19])==row['start_ticks']
    except FileNotFoundError:matching=False
    samples.append(dict(**row,matching_identity_present=matching))
raw=read(allocation/'logs/stderr.log');diagnostics=[];other=0
for line in raw.splitlines():
    try:
        row=json.loads(line)
        if isinstance(row,dict):diagnostics.append(row)
        else:other+=1
    except (ValueError,UnicodeError):other+=1
phases=[r for r in diagnostics if r.get('kind')=='puck-worker-phase-v1']
costs=[r for r in diagnostics if r.get('kind')=='puck-worker-guard-cost-v1']
assert b'Unregistered local or external dependency import: backports_abc' in raw
value=dict(kind='root-terminal-qualification10-metadata-v1',status='FAILED_CONSUMED',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit='e723db037ed1f790c2618798d59f56913054754f',control_commit='796359a099131157b5b91db38f14784628d5d7c5',configuration_sha256=transport['configuration_sha256'],observer_invocations=1,independent_auditor_invocations=1,admission02_status='DATA_ONLY_ADMITTED',transport=transport,transport_sha256=hashlib.sha256(transport_raw).hexdigest(),parent_result=result,supervision=supervision,independent_audit=audit,independent_audit_sha256=hashlib.sha256(audit_raw).hexdigest(),pins=pins,total_pinned_bytes=total,missing_original_paths=missing,historical_records_unchanged=len(before['raw_run_files']),process_identity_samples=samples,process_scope='three sequential recorded PID/start identity samples; nonexhaustive non-atomic observation',worker_stderr_bytes=len(raw),phase_records=len(phases),cost_records=len(costs),non_json_traceback_lines=other,last_phase=phases[-1] if phases else None,last_cost=costs[-1] if costs else None,failure='retained worker traceback first refuses unregistered backports_abc during Torchvision -> torch._dynamo -> numpy.random -> bit_generator; bootstrap stays poisoned',deadline_failure=False,completed_four_import_receipt=False,post_failure_full_payload_custody=False,runtime_qualified=False,qualification_claims=[],all_seven_release_gates_open=True,limits='Terminal metadata and retained failure only; no target import, installed/staged/native payload read, replay/model/study/renderer/physical acceptance. Failure-result FD5->5/no child/thread is reported cleanup, not independently passing post-run custody.')
path=Path('/tmp/palimpsest-held10-amendment02-post-outcome-observation.json')
with path.open('x') as out:out.write(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(path=str(path),pins=len(pins),bytes=total,phase_records=len(phases),cost_records=len(costs),parent_status=result['status'],parent_failure_closure=result['closure'],matching_process_samples=samples,post_failure_full_payload_custody=False)))
