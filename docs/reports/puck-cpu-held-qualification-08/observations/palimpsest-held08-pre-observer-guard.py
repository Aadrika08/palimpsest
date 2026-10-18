"""Refresh ordinary08 launch prerequisites; never invoke the observer."""
from pathlib import Path
import datetime,hashlib,json,os,stat,subprocess,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain');BASE='docs/plans/puck-cpu-held-qualification-08'
def load(path):return json.loads(path.read_bytes())
def hashed(path,size,sha):
    raw=path.read_bytes();assert len(raw)==size and hashlib.sha256(raw).hexdigest()==sha,path
    return raw
freeze_raw=hashed(ROOT/(BASE+'-freeze.json'),184287,'5b7d2b7814e9a3af61a1915f8b03f566949ae52c8cdc3e3ac912c22040e3d28a')
freeze=json.loads(freeze_raw);execution=load(ROOT/(BASE+'-execution.json'))
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='2f74653367f14f0156479a52314f625d7400fc57'
assert subprocess.check_output(['git','rev-parse','@{upstream}'],cwd=ROOT,text=True).strip()=='2f74653367f14f0156479a52314f625d7400fc57'
stamp=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
for row in freeze['pins']:
    path=ROOT/row['path'];before=path.lstat();assert stat.S_ISREG(before.st_mode) and before.st_nlink==1
    hashed(path,row['size_bytes'],row['sha256']);assert stamp(before)==stamp(path.lstat())
for row in (execution['wrapper'],execution['timeout_binary']):hashed(Path(row['path']),row['size_bytes'],row['sha256'])
assert Path(execution['wrapper']['path']).read_bytes()==(ROOT/execution['wrapper']['tracked_copy']).read_bytes()
admission_raw=hashed(Path(execution['admission_output']),4471,'099456da7ad8b2771566f753e5e58c8065061c9201357f789055399875aef4af')
assert admission_raw==Path(execution['phase_outputs']['admission']['stdout']).read_bytes()
admission=json.loads(admission_raw);external=load(Path(execution['phase_outputs']['admission']['json']))
assert admission['status']=='DATA_ONLY_ADMITTED' and admission['configuration_sha256']=='67076970caffe64b6162c4344f11d943b620dd2e0fb43ace72e39f508fa7ee60'
assert external['returncode']==0 and external['normal_exit'] is True and external['timed_out'] is False and external['elapsed_seconds']<145
assert external['stdout']['sha256']=='099456da7ad8b2771566f753e5e58c8065061c9201357f789055399875aef4af'
terminal=load(Path('/tmp/palimpsest-held08-admission-tool-terminal.json'))
assert terminal['chunk_id']=='b49266' and terminal['exit_code']==0
assert admission['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
future=[Path(p) for phase,rows in execution['phase_outputs'].items() if phase!='admission' for p in rows.values()]
future += [Path(execution[k]) for k in ('auditor_output','concrete_audit_command_path')]
future += [ROOT/p for p in ('runs/puck-cpu-held-qualification-08','runs/puck-cpu-held-qualification-08-external-cli.stdout','runs/puck-cpu-held-qualification-08-external-cli.stderr','runs/puck-cpu-held-qualification-08-external-cli-transport.json')]
assert len(future)==len(set(future))==12 and all(not os.path.lexists(p) for p in future)
assert all(not os.path.lexists(ROOT/('runs/puck-cpu-held-qualification-07/'+name)) for name in ('result.json','baseline-after.json'))
module=types.ModuleType('fresh_resource_guard');module.__file__=str(ROOT/(BASE+'-admission.py'))
exec(compile((ROOT/(BASE+'-admission.py')).read_bytes(),module.__file__,'exec'),module.__dict__)
resources=module.resources()
result=dict(status='PASS_PRE_OBSERVER_GUARD',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),control_commit='2f74653367f14f0156479a52314f625d7400fc57',frozen_pins=749,pinned_bytes=58476477,admission_sha256='099456da7ad8b2771566f753e5e58c8065061c9201357f789055399875aef4af',future_outputs_absent=12,resources=resources,observer_invoked=False)
Path('/tmp/palimpsest-held08-pre-observer-guard-01.json').open('x').write(json.dumps(result,indent=2,sort_keys=True)+'\n');print(json.dumps(result))
