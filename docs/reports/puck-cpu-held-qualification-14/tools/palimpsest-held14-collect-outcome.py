"""Retain terminal metadata only; never execute/import/re-hash runtime payloads."""
from pathlib import Path
import datetime,hashlib,json,os,stat,subprocess,time
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
base=root/'docs/plans/puck-cpu-held-qualification-14-control-validation'
control='eb34d5c2a66730c248b00229c17ce84e197b3d68'
source='f05bd699af337e44de54584bb334690ec405f994'
# M1: every present receipt must name exactly the frozen epoch-11 configuration.
config_sha='32f8aeb553a534b463f2b7a594ca721273fa251ae743256d6fe23efa74f6bed2'
allocation=root/'runs/puck-cpu-held-qualification-14'
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

def optional(path):
    # Outcome-neutral: an absent receipt is recorded as missing, never fabricated.
    return json.loads(read(path)) if os.path.lexists(path) else None

paths=[]
# I1: a refusal during resource admission leaves no allocation directory; record it as missing.
allocation_present=os.path.lexists(allocation)
if allocation_present:
    assert allocation.is_dir() and not allocation.is_symlink()
    for directory,dirs,files in os.walk(allocation,followlinks=False):
        assert all(stat.S_ISDIR((Path(directory)/name).lstat().st_mode) for name in dirs)
        paths.extend(Path(directory)/name for name in files)
assert len(paths)<=256
paths += [root/('runs/puck-cpu-held-qualification-14-external-cli'+suffix) for suffix in ('.stdout','.stderr','-transport.json')]
terminals={}
for phase in ('admission','observer','audit'):
    stem=Path('/tmp/palimpsest-held14-'+phase)
    paths.extend(Path(str(stem)+'-external'+suffix) for suffix in ('.json','.stdout','.stderr'))
    paths.extend(Path(str(stem)+'-tool'+suffix) for suffix in ('-command.json','-terminal.json','.stdout','.stderr'))
    # I1: an observer timeout or refusal can leave no later terminal; record it as missing.
    terminal=optional(Path(str(stem)+'-tool-terminal.json'))
    assert terminal is None or (terminal['phase']==phase and type(terminal['outer_timeout']) is bool)
    terminals[phase]=terminal
assert terminals['admission'] is not None and terminals['admission']['exit_code']==0 and terminals['admission']['outer_timeout'] is False
assert terminals['observer'] is not None or terminals['audit'] is None
paths += [Path('/tmp/palimpsest-puck-cpu-held-qualification-14-'+phase+'-'+number+'.json') for phase,number in (('admission','01'),('audit','01'))]
paths += [Path('/tmp/palimpsest-held14-'+name+'.json') for name in ('pre-admission-guard01','pre-observer-guard01','independent-admission-review','concrete-audit-command')]
assert len(paths)==len(set(paths))
pins=[];total=0;absent_evidence=[]
for path in sorted(paths):
    if not os.path.lexists(path):absent_evidence.append(str(path));continue
    raw=read(path);total+=len(raw);assert total<=32*1024**2
    pins.append(dict(path=str(path),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
transport_path=root/'runs/puck-cpu-held-qualification-14-external-cli-transport.json'
transport_raw=read(transport_path) if os.path.lexists(transport_path) else None
transport=None if transport_raw is None else json.loads(transport_raw)
result=optional(allocation/'result.json');supervision=optional(allocation/'supervision.json')
audit_path=Path('/tmp/palimpsest-puck-cpu-held-qualification-14-audit-01.json')
audit_raw=read(audit_path) if os.path.lexists(audit_path) else None
audit=None if audit_raw is None else json.loads(audit_raw)
admission=json.loads(read(Path('/tmp/palimpsest-puck-cpu-held-qualification-14-admission-01.json')))
for name,value in (('admission',admission),('transport',transport),('result',result),('audit',audit)):
    assert value is None or value.get('configuration_sha256')==config_sha,'Configuration SHA differs in '+name
observer_stdout=Path('/tmp/palimpsest-held14-observer-external.stdout')
if transport_raw is not None and os.path.lexists(observer_stdout):assert read(observer_stdout)==transport_raw
if audit_raw is not None:
    assert read(Path('/tmp/palimpsest-held14-audit-external.stdout'))==audit_raw
    assert transport_raw is not None and audit['transport_sha256']==hashlib.sha256(transport_raw).hexdigest()
def normal(phase):
    terminal=terminals[phase];return terminal is not None and terminal['exit_code']==0 and terminal['outer_timeout'] is False
passed=(normal('observer') and normal('audit')
    and transport is not None and transport['observed_returncode']==0 and transport['timed_out'] is False
    and result is not None and result['status']=='imports_completed' and result['held_four_imports_observed'] is True
    and audit is not None and audit['status']=='PASS' and audit['kind']=='puck-cpu-held-runtime-independent-audit-v14')
# Review-04 Important 2: extended-clock epoch-14 bounds decide PASS; a wrong registration clock is refused.
registration=optional(allocation/'control/worker-registration.json')
assert registration is None or registration.get('deadline_seconds')==360,'Epoch-14 worker registration must carry deadline_seconds 360'
worker_receipt=None
if os.path.lexists(allocation/'logs/stdout.log'):
    worker_raw=read(allocation/'logs/stdout.log')
    try:worker_receipt=json.loads(worker_raw) if worker_raw else None
    except ValueError:worker_receipt=None
import_seconds=[row.get('seconds') for row in ((worker_receipt or {}).get('entry_result') or {}).get('imports',[])] if isinstance(worker_receipt,dict) else []
clocks=dict(parent_elapsed_below_360=result is not None and type(result.get('elapsed_seconds')) in (int,float) and 0<result['elapsed_seconds']<360,
    transport_elapsed_below_400=transport is not None and type(transport.get('elapsed_seconds')) in (int,float) and 0<transport['elapsed_seconds']<400,
    registration_deadline_seconds=None if registration is None else registration.get('deadline_seconds'),
    import_seconds=import_seconds,imports_below_360=len(import_seconds)==4 and all(type(s) in (int,float) and 0<s<360 for s in import_seconds))
passed=(passed and clocks['parent_elapsed_below_360'] and clocks['transport_elapsed_below_400']
    and clocks['registration_deadline_seconds']==360 and clocks['imports_below_360'])
status='AUDIT_PASS_IMPORT_ROUTE_ONLY' if passed else 'FAILED_CONSUMED'
before=json.loads(read(base/'historical-before-admission.json'))
for row in before['raw_run_files']+before['preparation03_run_files']+before['preparation02_run_files']:
    raw=read(root/row['path']);assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
for name in before['historical_empty_directories']:
    path=root/name;assert path.is_dir() and not path.is_symlink() and not any(path.iterdir()),name
missing=[str(root/p) for p in before['historical_absent_paths']]+before['attempt11_d83dab3_absent_outputs']+['/tmp/palimpsest-puck-cpu-held-qualification-14-admission-02.json']
assert len(missing)==len(set(missing)) and all(not os.path.lexists(p) for p in missing)
if not allocation_present:missing.append(str(allocation))
for leaf in ('result.json','baseline-after.json','supervision.json'):
    if not os.path.lexists(allocation/leaf):missing.append(str(allocation/leaf))
for phase,terminal in terminals.items():
    if terminal is None:missing.append('/tmp/palimpsest-held14-'+phase+'-tool-terminal.json')
missing += [p for p in absent_evidence if p not in missing]
stage_after=None
try:
    stage_rel='docs/plans/puck-cpu-held-qualification-14-control-validation/tools/stage_guard.py'
    stage_raw=(root/stage_rel).read_bytes()
    assert stage_raw==subprocess.check_output(['git','show',control+':'+stage_rel],cwd=root)
    stage_namespace={'__name__':'held14_stage_guard'};exec(compile(stage_raw,str(root/stage_rel),'exec'),stage_namespace)
    stage_after=stage_namespace['check'](root)
except Exception as error:stage_after=dict(status='STAGE_OR_BOOT_CHANGED',error=type(error).__name__+': '+str(error)[:512])
samples=[]
for row in (supervision or {}).get('tracked_processes',[]):
    p=Path('/proc')/str(row['pid'])/'stat'
    try:
        text=p.read_text();fields=text[text.rfind(')')+2:].split();matching=int(fields[19])==row['start_ticks']
    except FileNotFoundError:matching=False
    samples.append(dict(**row,matching_identity_present=matching))
raw=read(allocation/'logs/stderr.log') if os.path.lexists(allocation/'logs/stderr.log') else b'';diagnostics=[];other=[]
for line in raw.splitlines():
    try:
        row=json.loads(line)
        if isinstance(row,dict):diagnostics.append(row)
        else:other.append(line)
    except (ValueError,UnicodeError):other.append(line)
phases=[r for r in diagnostics if r.get('kind')=='puck-worker-phase-v1']
costs=[r for r in diagnostics if r.get('kind')=='puck-worker-guard-cost-v1']
errors=[line.decode('utf-8','replace')[:1024] for line in other if b'Error' in line.split(b':',1)[0]]
value=dict(kind='root-terminal-qualification14-metadata-v1',status=status,at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_commit=source,control_commit=control,configuration_sha256=config_sha,
    observer_invocations=1,independent_auditor_invocations=0 if terminals['audit'] is None else 1,admission14_status=admission['status'],terminals=terminals,
    allocation_present=allocation_present,transport=transport,transport_sha256=None if transport_raw is None else hashlib.sha256(transport_raw).hexdigest(),
    parent_result=result,supervision=supervision,independent_audit=audit,
    independent_audit_sha256=None if audit_raw is None else hashlib.sha256(audit_raw).hexdigest(),
    pins=pins,total_pinned_bytes=total,missing_original_paths=missing,historical_records_unchanged=len(before['raw_run_files']),
    preparation03_run_files_unchanged=len(before['preparation03_run_files']),preparation02_run_files_unchanged=len(before['preparation02_run_files']),stage_after=stage_after,epoch14_clocks=clocks,
    process_identity_samples=samples,process_scope='sequential recorded PID/start identity samples only; nonexhaustive non-atomic observation',
    worker_stderr_bytes=len(raw),phase_records=len(phases),cost_records=len(costs),non_json_lines=len(other),
    last_phase=phases[-1] if phases else None,last_cost=costs[-1] if costs else None,exception_lines=errors[:8],
    completed_four_import_receipt=passed,runtime_qualified=False,qualification_claims=[],all_seven_release_gates_open=True,
    limits='Terminal metadata only; no target import, installed/staged/native payload read, replay/model/study/renderer/physical acceptance. A passing audit is import-route evidence only, not runtime/operator/episode acceptance.')
path=Path('/tmp/palimpsest-held14-post-outcome-observation.json')
with path.open('x') as out:out.write(json.dumps(value,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(path=str(path),status=status,pins=len(pins),bytes=total,missing=len(missing),phase_records=len(phases),
    cost_records=len(costs),parent_status=None if result is None else result['status'],matching_process_samples=samples)))
