"""Read current fixed pins and resources before the sole runtime observer."""
from pathlib import Path
import datetime,hashlib,json,os,stat,subprocess,types

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
CONTROL='796359a099131157b5b91db38f14784628d5d7c5'
BASE='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
def pin(path):
    raw=path.read_bytes()
    return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
assert git('rev-parse','HEAD').decode().strip()==CONTROL
assert git('status','--porcelain')==b''
assert git('rev-parse','origin/research/puck-cpu-held-qualification-10').decode().strip()==CONTROL
controls=git('ls-tree','-r','--name-only',CONTROL,'--',BASE).decode().splitlines()
assert len(controls)==74 and all(p.startswith(BASE) for p in controls)
for path in controls:assert (ROOT/path).read_bytes()==git('show',CONTROL+':'+path),path
envelope=json.loads((ROOT/(BASE+'/execution.json')).read_bytes())
freeze=json.loads((ROOT/(BASE+'/freeze.json')).read_bytes())
config=json.loads((ROOT/(BASE+'/configuration.json')).read_bytes())
assert pin(ROOT/(BASE+'/freeze.json'))=={k:envelope['freeze'][k] for k in ('size_bytes','sha256')}
assert len(freeze['pins'])==2150
for row in freeze['pins']:
    path=ROOT/row['path'];stamp=path.lstat()
    assert stat.S_ISREG(stamp.st_mode) and stamp.st_nlink==1,row['path']
    assert pin(path)=={k:row[k] for k in ('size_bytes','sha256')},row['path']
for row in (envelope['wrapper'],envelope['timeout_binary'],config['interpreter']):
    assert pin(Path(row['path']))=={k:row[k] for k in ('size_bytes','sha256')}
assert Path(envelope['wrapper']['path']).read_bytes()==(ROOT/envelope['wrapper']['tracked_copy']).read_bytes()
future=[path for phase in ('observer','audit') for path in envelope['phase_outputs'][phase].values()]
future += [envelope['auditor_output'],envelope['concrete_audit_command_path']]
prior_guard=json.loads(Path('/tmp/palimpsest-held10-amendment02-pre-admission-guard01.json').read_bytes())
assert prior_guard['control_commit']==CONTROL
future += [path for path in prior_guard['absence']['new_paths'] if path not in (envelope['admission_output'],envelope['auditor_output'])]
assert len(future)==len(set(future))==12
assert all(not os.path.lexists(path) for path in future)
assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-qualification-10-admission-01.json')
admission=Path(envelope['admission_output']).read_bytes()
assert admission==Path(envelope['phase_outputs']['admission']['stdout']).read_bytes()
assert len(admission)==7408 and hashlib.sha256(admission).hexdigest()=='33a425040db69d220fea247faf0077883ebd8c99644a20f929d3cbfe886567b9'
a=json.loads(admission)
assert a['status']=='DATA_ONLY_ADMITTED' and a['admission_check_id']==2 and a['qualification10_invoked'] is False
assert a['runtime_qualified'] is False and a['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
review_path=Path('/tmp/palimpsest-held10-amendment02-independent-admission-review.json')
assert pin(review_path)==dict(size_bytes=6456,sha256='06f5b8b5a7866b7da34716ecf69afc6804ccbf9c7cc1edf98d603b3df7dc6265')
review=json.loads(review_path.read_bytes());assert review['decision']=='GO'
module=types.ModuleType('_held10_pre_admission_guard');path=ROOT/(BASE+'/admission.py');module.__file__=str(path)
exec(compile(path.read_bytes(),str(path),'exec'),module.__dict__)
absence=dict(future_output_paths=future,historical_missing_receipts=16);resources=module.resources()
before=json.loads((ROOT/(BASE+'/historical-before-admission.json')).read_bytes())
for row in before['raw_run_files']:assert pin(ROOT/row['path'])=={k:row[k] for k in ('size_bytes','sha256')}
assert all(not os.path.lexists(ROOT/path) for path in before['historical_absent_paths'])
result=dict(status='PASS_PRE_OBSERVER_GUARD_ONLY',control_commit=CONTROL,source_commit=freeze['source_commit'],
    checked_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),control_files=len(controls),
    pins=len(freeze['pins']),pinned_bytes=sum(r['size_bytes'] for r in freeze['pins']),resources=resources,
    absence=absence,historical_records_unchanged=79,admission_main_invoked=True,admission_receipt_sha256=hashlib.sha256(admission).hexdigest(),runtime_invoked=False,
    payload_census_or_rehash=False)
with Path('/tmp/palimpsest-held10-amendment02-pre-observer-guard01.json').open('x') as stream:
    stream.write(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,sort_keys=True))
