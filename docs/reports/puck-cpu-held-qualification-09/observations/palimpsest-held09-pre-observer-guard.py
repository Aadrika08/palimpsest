"""Read current fixed pins and resources before the sole runtime observer."""
from pathlib import Path
import datetime,hashlib,json,os,stat,subprocess,types

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONTROL='60e5756d8c670e898320b26b3a2cee267577e53c'
BASE='docs/plans/puck-cpu-held-qualification-09'
def pin(path):
    raw=path.read_bytes()
    return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
assert git('rev-parse','HEAD').decode().strip()==CONTROL
assert git('status','--porcelain')==b''
assert git('rev-parse','origin/research/puck-cpu-held-qualification-09').decode().strip()==CONTROL
controls=git('diff-tree','--no-commit-id','--name-only','-r',CONTROL).decode().splitlines()
assert len(controls)==39 and all(p.startswith(BASE) for p in controls)
for path in controls:assert (ROOT/path).read_bytes()==git('show',CONTROL+':'+path),path
envelope=json.loads((ROOT/(BASE+'-execution.json')).read_bytes())
freeze=json.loads((ROOT/(BASE+'-freeze.json')).read_bytes())
config=json.loads((ROOT/(BASE+'.json')).read_bytes())
assert pin(ROOT/(BASE+'-freeze.json'))=={k:envelope['freeze'][k] for k in ('size_bytes','sha256')}
assert len(freeze['pins'])==1259
for row in freeze['pins']:
    path=ROOT/row['path'];stamp=path.lstat()
    assert stat.S_ISREG(stamp.st_mode) and stamp.st_nlink==1,row['path']
    assert pin(path)=={k:row[k] for k in ('size_bytes','sha256')},row['path']
for row in (envelope['wrapper'],envelope['timeout_binary'],config['interpreter']):
    assert pin(Path(row['path']))=={k:row[k] for k in ('size_bytes','sha256')}
assert Path(envelope['wrapper']['path']).read_bytes()==(ROOT/envelope['wrapper']['tracked_copy']).read_bytes()
future=[path for phase in ('observer','audit') for path in envelope['phase_outputs'][phase].values()]
future += [envelope['auditor_output'],envelope['concrete_audit_command_path']]
prior_guard=json.loads(Path('/tmp/palimpsest-held09-pre-admission-guard01.json').read_bytes())
future += [path for path in prior_guard['absence']['new_paths'] if path not in (envelope['admission_output'],envelope['auditor_output'])]
assert len(future)==len(set(future))==12
assert all(not os.path.lexists(path) for path in future)
admission=Path(envelope['admission_output']).read_bytes()
assert admission==Path(envelope['phase_outputs']['admission']['stdout']).read_bytes()
assert len(admission)==5610 and hashlib.sha256(admission).hexdigest()=='ee2c52efc0dcf7ffdb14d826aca4569ccf6050e462088d6373dfaded85777e84'
a=json.loads(admission);assert a['status']=='DATA_ONLY_ADMITTED' and a['qualification09_invoked'] is False
review=json.loads(Path('/tmp/palimpsest-held09-admission-receipt-review.json').read_bytes())
assert review['material_findings']==[] and review['status']=='GO_PRE_OBSERVER_FRESH_GUARD_REQUIRED'
module=types.ModuleType('_held09_pre_admission_guard');path=ROOT/(BASE+'-admission.py');module.__file__=str(path)
exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
absence=dict(future_output_paths=future,historical_missing_receipts=14);resources=module.resources()
before=json.loads(Path('/tmp/palimpsest-held09-before-source-rollout.json').read_bytes())
for row in before['raw_run_files']:assert pin(ROOT/row['path'])=={k:row[k] for k in ('size_bytes','sha256')}
assert all(not os.path.lexists(ROOT/path) for path in before['historical_absent_paths'])
result=dict(status='PASS_PRE_OBSERVER_GUARD_ONLY',control_commit=CONTROL,source_commit=freeze['source_commit'],
    checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),control_files=len(controls),
    pins=len(freeze['pins']),pinned_bytes=sum(r['size_bytes'] for r in freeze['pins']),resources=resources,
    absence=absence,historical_records_unchanged=57,admission_main_invoked=True,admission_receipt_sha256=hashlib.sha256(admission).hexdigest(),runtime_invoked=False,
    payload_census_or_rehash=False)
with Path('/tmp/palimpsest-held09-pre-observer-guard01.json').open('x') as stream:
    stream.write(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,sort_keys=True))
