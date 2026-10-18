"""Archive the sole failed data-only admission; never execute a target."""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONTROL='b3d50f5d8efbd36c56337c323d66768831c0f43f'
SOURCE='e723db037ed1f790c2618798d59f56913054754f'
packet=ROOT/'docs/reports/puck-cpu-held-qualification-10-admission-01'
packet.mkdir()
artifacts=[]
def save(name,origin):
    origin=Path(origin);raw=origin.read_bytes();assert len(raw)<2*1024**2,name
    target=packet/name;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as out:out.write(raw)
    assert target.read_bytes()==raw
    artifacts.append(dict(archived_path=name,original_path=str(origin),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
controls=subprocess.check_output(['git','diff','--name-only',SOURCE,CONTROL],cwd=ROOT,text=True).splitlines()
assert len(controls)==47 and all(p.startswith('docs/plans/puck-cpu-held-qualification-10') for p in controls)
for name in controls:
    assert (ROOT/name).read_bytes()==subprocess.check_output(['git','show',CONTROL+':'+name],cwd=ROOT)
    save('controls/'+name,ROOT/name)
config=json.loads((ROOT/'docs/plans/puck-cpu-held-qualification-10.json').read_bytes())
auth='docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'
sources=sorted({row['path'] for row in config['sources']}|{'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py',auth})
assert len(sources)==27
for name in sources:
    assert (ROOT/name).read_bytes()==subprocess.check_output(['git','show',SOURCE+':'+name],cwd=ROOT)
    save('source/'+name,ROOT/name)
for name in ('palimpsest-held10-pre-admission-guard.py','palimpsest-held10-pre-admission-guard01.json',
    'palimpsest-held10-historical-before-admission.json','palimpsest-held10-run-admission-once.py',
    'palimpsest-held10-admission-tool-command.json','palimpsest-held10-admission-tool-terminal.json',
    'palimpsest-held10-admission-tool.stdout','palimpsest-held10-admission-tool.stderr',
    'palimpsest-held10-admission-external.json','palimpsest-held10-admission-external.stdout',
    'palimpsest-held10-admission-external.stderr','palimpsest-held10-admission01-outcome-review.json'):
    save('observations/'+name,Path('/tmp')/name)
review=json.loads(Path('/tmp/palimpsest-held10-admission01-outcome-review.json').read_bytes())
external=json.loads(Path('/tmp/palimpsest-held10-admission-external.json').read_bytes())
tool=json.loads(Path('/tmp/palimpsest-held10-admission-tool-terminal.json').read_bytes())
assert external['returncode']==1 and external['normal_exit'] and not external['timed_out']
assert tool['exit_code']==1 and not tool['outer_timeout']
assert not (ROOT/'runs/puck-cpu-held-qualification-10').exists()
missing=[str(ROOT/'runs/puck-cpu-held-qualification-10'),'/tmp/palimpsest-puck-cpu-held-qualification-10-admission-01.json']
assert all(not Path(name).exists() for name in missing)
outcome=dict(kind='puck-cpu-held10-admission01-outcome-v1',status='DATA_ADMISSION_FAILED_CONSUMED',
    control_commit=CONTROL,source_commit=SOURCE,admission_invocations=1,actual_runtime10_invoked=False,
    failure='Canonical JSON bytes differ',failure_gate='admission.py:367, before freeze/manifest/plan/SITE/staged-payload checks',
    external_seconds=external['elapsed_seconds'],tool_seconds=tool['elapsed_seconds'],external_exit_code=1,outer_timeout=False,
    stdout_bytes=0,stderr_bytes=external['stderr']['size_bytes'],failure_telemetry_closure=dict(fd_before=4,fd_after=4,children=[],threads=[],scope='data-only admission process observations; no runtime-parent closure'),
    full_payload_custody=False,missing_required_results=missing,all_seven_release_gates_open=True,
    qualification_claims=[],runtime_qualified=False,study_authorized=False,collection_authorized=False,executable=False,
    next='Separate prospective admission amendment02: canonical-only config with identical parsed values, explicit preflight, distinct controls/outputs, independent review and fresh admission; no implicit retry')
outcome_path=packet/'outcome.json';outcome_path.write_text(json.dumps(outcome,indent=2,sort_keys=True)+'\n')
raw=outcome_path.read_bytes();artifacts.append(dict(archived_path='outcome.json',original_path=str(outcome_path),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
save('verify_evidence.py',ROOT/'docs/reports/puck-cpu-held-qualification-09/verify_evidence.py')
save('archive_evidence.py',Path(__file__))
assert sum(r['size_bytes'] for r in artifacts)<8*1024**2
index=dict(source_commit=SOURCE,source_paths=sources,control_commit=CONTROL,control_paths=controls,
    artifacts=artifacts,artifact_count=len(artifacts))
(packet/'evidence-index.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(artifacts=len(artifacts),bytes=sum(r['size_bytes'] for r in artifacts),
    empty_files=sum(r['size_bytes']==0 for r in artifacts),source_paths=len(sources),control_paths=len(controls))))
