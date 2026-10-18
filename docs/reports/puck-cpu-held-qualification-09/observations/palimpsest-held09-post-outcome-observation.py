"""Preserve small terminal09 observations; never run a qualification or payload audit."""
from pathlib import Path
import datetime,hashlib,json,os,stat

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
ALLOCATION=ROOT/'runs/puck-cpu-held-qualification-09'
def read(path):
    path=Path(path);state=path.lstat()
    assert stat.S_ISREG(state.st_mode) and state.st_nlink==1 and state.st_size<=16*1024**2
    with path.open('rb') as stream:raw=stream.read(16*1024**2+1)
    fields=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
    assert len(raw)==state.st_size and all(getattr(path.lstat(),k)==getattr(state,k) for k in fields),str(path)
    return raw
def decode(path):return json.loads(read(path))
def pin(path):
    raw=read(path)
    return dict(path=str(path),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

transport=ROOT/'runs/puck-cpu-held-qualification-09-external-cli-transport.json'
audit=Path('/tmp/palimpsest-puck-cpu-held-qualification-09-audit-01.json')
t=decode(transport);a=decode(audit);supervision=decode(ALLOCATION/'supervision.json')
assert t['observed_returncode']==1 and t['timed_out'] is False
assert a['status']=='FAIL' and a['error']=='Normal external transport exit required'
assert a['transport_sha256']==pin(transport)['sha256']
assert supervision['status']=='failed' and supervision['failure']=='normal-return deadline'
assert supervision['returncode']==-15 and supervision['matching_survivors']==[]
missing=[str(ALLOCATION/name) for name in ('result.json','baseline-after.json')]
assert all(not os.path.lexists(path) for path in missing)
stdout=read(ALLOCATION/'logs/stdout.log');stderr=read(ALLOCATION/'logs/stderr.log')
assert stdout==b''
diagnostics=[json.loads(line) for line in stderr.splitlines()]
phases=[row for row in diagnostics if row['kind']=='puck-worker-phase-v1']
costs=[row for row in diagnostics if row['kind']=='puck-worker-guard-cost-v1']
assert len(diagnostics)==len(phases)+len(costs)
samples=[]
for identity in supervision['tracked_processes']:
    try:
        current=int((Path('/proc')/str(identity['pid'])/'stat').read_text().rsplit(')',1)[1].split()[19])
        present=current==identity['start_ticks']
    except FileNotFoundError:present=False
    samples.append(dict(identity,matching_identity_present=present))
paths=[];directories=0
for directory,dirs,files in os.walk(ALLOCATION,followlinks=False):
    directories+=1;assert directories<=128
    assert all(stat.S_ISDIR((Path(directory)/name).lstat().st_mode) for name in dirs)
    paths.extend(Path(directory)/name for name in files);assert len(paths)<=256
paths += [ROOT/('runs/puck-cpu-held-qualification-09-external-cli'+suffix) for suffix in ('.stdout','.stderr','-transport.json')]
paths += [Path('/tmp/palimpsest-held09-'+phase+'-external'+suffix) for phase in ('admission','observer','audit') for suffix in ('.json','.stdout','.stderr')]
paths += [Path('/tmp/palimpsest-held09-'+phase+'-tool-terminal.json') for phase in ('admission','observer','audit')]
paths += [audit,Path('/tmp/palimpsest-puck-cpu-held-qualification-09-admission-01.json')]
paths += [Path('/tmp/palimpsest-held09-'+name) for name in ('admission-receipt-review.json','pre-admission-guard.py','pre-admission-guard01.json','pre-observer-guard.py','pre-observer-guard01.json','bind-audit-command.py','concrete-audit-command.json')]
assert len(paths)==len(set(paths))
before=decode('/tmp/palimpsest-held09-before-source-rollout.json')
for row in before['raw_run_files']:
    actual=pin(ROOT/row['path']);assert all(actual[k]==row[k] for k in ('size_bytes','sha256'))
assert all(not os.path.lexists(ROOT/path) for path in before['historical_absent_paths'])
result=dict(kind='puck-cpu-held09-root-post-outcome-observation-v1',version=1,
    observed_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='FAILED_CONSUMED',
    qualification_status='FAIL',source_commit='96ace37062fd14e20ae1ebd2371b90fa88f8d7ab',
    control_commit='60e5756d8c670e898320b26b3a2cee267577e53c',configuration_sha256=t['configuration_sha256'],
    transport_sha256=pin(transport)['sha256'],independent_audit_sha256=pin(audit)['sha256'],
    observer_invocations=1,independent_auditor_invocations=1,transport=t,supervision=supervision,
    outer_transports={phase:decode('/tmp/palimpsest-held09-'+phase+'-external.json') for phase in ('admission','observer','audit')},
    worker_stdout_bytes=len(stdout),worker_stderr_bytes=len(stderr),diagnostic_records=len(diagnostics),
    phase_records=len(phases),cost_records=len(costs),last_diagnostic=diagnostics[-1] if diagnostics else None,
    phase_diagnostics=phases,last_phase=phases[-1] if phases else None,last_guard_cost=costs[-1] if costs else None,
    diagnostic_scope='Optional unauthenticated incomplete source-reported cumulative observations; sections may include nested checks and instrumentation. No full timeout-cause, exclusive-time or hard-timing claim.',
    process_identity_samples=samples,process_scope='Three recorded PID/start identities only; sequential nonexhaustive non-atomic observation.',
    missing_original_paths=missing,historical_run_records_unchanged=57,historical_missing_receipts_preserved=14,
    completed_four_import_receipt=False,parent_closure_receipt=False,post_failure_full_payload_custody=False,
    independent_audit_boundary='Early nonzero transport refusal; no complete post-run payload/byte audit.',
    runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,
    executable=False,qualification_claims=[],implicit_retry=False,all_seven_release_gates_open=True,
    pins=sorted((pin(path) for path in paths),key=lambda row:row['path']),payload_census_or_rehash=False,
    cause='Exact timeout cause remains unproved; final markers and cumulative counters do not identify all elapsed work.')
with Path('/tmp/palimpsest-held09-post-outcome-observation.json').open('x') as stream:
    stream.write(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
print(json.dumps(dict(status=result['status'],pins=len(result['pins']),allocation_files=len(paths)-24,
    phase_records=len(phases),cost_records=len(costs),worker_stderr_bytes=len(stderr),
    last_phase=result['last_phase'],last_guard_cost=result['last_guard_cost'],runtime_qualified=False),sort_keys=True))
