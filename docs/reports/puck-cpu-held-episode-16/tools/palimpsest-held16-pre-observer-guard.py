"""Read current fixed pins and resources before the sole runtime observer."""
from pathlib import Path
import datetime,hashlib,json,os,stat,subprocess,types

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONTROL='e7c5a3e55dcbac8715a68025069e4ed6e5860fb1'
BASE='docs/plans/puck-cpu-held-episode-16'
def pin(path):
    raw=path.read_bytes()
    return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
assert git('rev-parse','HEAD').decode().strip()==CONTROL
assert git('status','--porcelain')==b''
assert git('rev-parse','origin/research/puck-cpu-held-episode-16').decode().strip()==CONTROL
controls=git('diff','--name-only','75df4dba55e435eee84d8a0f34b33967b0ac86bf',CONTROL).decode().splitlines()
assert len(controls)==105 and all(p.startswith(BASE) for p in controls)
for path in controls:assert (ROOT/path).read_bytes()==git('show',CONTROL+':'+path),path
stage_rel='docs/plans/puck-cpu-held-episode-16-control-validation/tools/stage_guard.py'
stage_raw=(ROOT/stage_rel).read_bytes()
assert stage_raw==subprocess.check_output(['git','show',CONTROL+':'+stage_rel],cwd=ROOT)
stage_namespace={'__name__':'held16_stage_guard'};exec(compile(stage_raw,str(ROOT/stage_rel),'exec'),stage_namespace)
stage=stage_namespace['check'](ROOT)
envelope=json.loads((ROOT/(BASE+'-execution.json')).read_bytes())
freeze=json.loads((ROOT/(BASE+'-freeze.json')).read_bytes())
config=json.loads((ROOT/(BASE+'.json')).read_bytes())
assert pin(ROOT/(BASE+'-freeze.json'))=={k:envelope['freeze'][k] for k in ('size_bytes','sha256')}
assert len(freeze['pins'])==2128
for row in freeze['pins']:
    path=ROOT/row['path'];stamp=path.lstat()
    assert stat.S_ISREG(stamp.st_mode) and stamp.st_nlink==1,row['path']
    assert pin(path)=={k:row[k] for k in ('size_bytes','sha256')},row['path']
for row in (envelope['wrapper'],envelope['timeout_binary'],config['interpreter']):
    assert pin(Path(row['path']))=={k:row[k] for k in ('size_bytes','sha256')}
assert Path(envelope['wrapper']['path']).read_bytes()==(ROOT/envelope['wrapper']['tracked_copy']).read_bytes()
future=[path for phase in ('observer','audit') for path in envelope['phase_outputs'][phase].values()]
future += [envelope['auditor_output'],envelope['concrete_audit_command_path']]
prior_guard=json.loads(Path('/tmp/palimpsest-held16-pre-admission-guard01.json').read_bytes())
assert prior_guard['control_commit']==CONTROL
future += [path for path in prior_guard['absence']['new_paths'] if path not in (envelope['admission_output'],envelope['auditor_output'])]
assert len(future)==len(set(future))==12
assert all(not os.path.lexists(path) for path in future)
assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-episode-16-admission-02.json')
admission=Path(envelope['admission_output']).read_bytes()
assert admission==Path(envelope['phase_outputs']['admission']['stdout']).read_bytes()
assert len(admission)==17446 and hashlib.sha256(admission).hexdigest()=='e0cdaea0d0a6782ddd12215d25ddc4b912f9612e9213c08234c4900e4b833b5b'
a=json.loads(admission)
assert a['status']=='DATA_ONLY_ADMITTED' and a['admission_check_id']==1 and a['episode16_invoked'] is False
assert a['runtime_qualified'] is False and a['closure']==dict(fd_count_before=5,fd_count_after=5,active_children=[],active_non_main_threads=[])
review_path=Path('/tmp/palimpsest-held16-independent-admission-review.json')
assert pin(review_path)==dict(size_bytes=11791,sha256='c19f8e8ee8fdb06b2870ea4ac86b1f86f1753221b7c1b5055b3d516ef86dd2cb')
review=json.loads(review_path.read_bytes());assert review['decision']=='GO'
module=types.ModuleType('_held16_pre_admission_guard');path=ROOT/(BASE+'-admission.py');module.__file__=str(path)
exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
absence=dict(future_output_paths=future,historical_missing_receipts=19);resources=module.resources()
before=json.loads((ROOT/(BASE+'-control-validation/historical-before-admission.json')).read_bytes())
for row in before['raw_run_files']:assert pin(ROOT/row['path'])=={k:row[k] for k in ('size_bytes','sha256')}
assert all(not os.path.lexists(ROOT/path) for path in before['historical_absent_paths'])
for row in before['preparation04_run_files']+before['preparation03_run_files']+before['preparation02_run_files']+before['characterization04_run_files']:assert pin(ROOT/row['path'])=={k:row[k] for k in ('size_bytes','sha256')},row['path']
for name in before['historical_empty_directories']:
    path=ROOT/name;assert path.is_dir() and not path.is_symlink() and not any(path.iterdir()),name
assert all(not os.path.lexists(path) for path in before['attempt11_d83dab3_absent_outputs'])
assert all(not os.path.lexists(path) for path in before['retired_stage_paths'])
for row in freeze['attempt11_d83dab3']['git_files']:
    raw=git('show',freeze['attempt11_d83dab3']['control_commit']+':'+row['path'])
    assert dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())=={k:row[k] for k in ('size_bytes','sha256')},row['path']
result=dict(status='PASS_PRE_OBSERVER_GUARD_ONLY',control_commit=CONTROL,source_commit=freeze['source_commit'],
    checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),control_files=len(controls),
    pins=len(freeze['pins']),pinned_bytes=sum(r['size_bytes'] for r in freeze['pins']),resources=resources,
    absence=absence,historical_records_unchanged=151,admission_main_invoked=True,admission_receipt_sha256=hashlib.sha256(admission).hexdigest(),runtime_invoked=False,
    payload_census_or_rehash=False,stage_guard=stage,preparation04_run_files=len(before['preparation04_run_files']),characterization04_run_files=len(before['characterization04_run_files']),retired_stages_absent=len(before['retired_stage_paths']),preparation03_run_files=len(before['preparation03_run_files']),preparation02_run_files=len(before['preparation02_run_files']),
    historical_empty_directories=len(before['historical_empty_directories']),attempt11_d83dab3='NEVER_INVOKED')
with Path('/tmp/palimpsest-held16-pre-observer-guard01.json').open('x') as stream:
    stream.write(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,sort_keys=True))
