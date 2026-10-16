"""Bind the future audit to the completed measured08 observer transport only."""
from pathlib import Path
import datetime,hashlib,json,os,stat
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
freeze_raw=(ROOT/'docs/plans/puck-cpu-held-qualification-08-freeze.json').read_bytes()
assert len(freeze_raw)==184287 and hashlib.sha256(freeze_raw).hexdigest()=='5b7d2b7814e9a3af61a1915f8b03f566949ae52c8cdc3e3ac912c22040e3d28a'
freeze=json.loads(freeze_raw)
path=ROOT/'runs/puck-cpu-held-qualification-08-external-cli-transport.json'
before=path.lstat();assert stat.S_ISREG(before.st_mode) and before.st_nlink==1 and before.st_size<=64*1024
raw=path.read_bytes();after=path.lstat()
stamp=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
assert stamp(before)==stamp(after) and len(raw)==before.st_size
transport=json.loads(raw)
assert raw==(json.dumps(transport,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
assert transport['kind']=='puck-cpu-held-cli-transport-v1' and transport['phase']=='qualify'
assert transport['configuration_sha256']=='67076970caffe64b6162c4344f11d943b620dd2e0fb43ace72e39f508fa7ee60'
assert type(transport['observed_returncode']) is int and type(transport['timed_out']) is bool
for name in ('stdout','stderr'):
    row=transport[name];p=ROOT/row['path'];st=p.lstat()
    assert row['path']=='runs/puck-cpu-held-qualification-08-external-cli.'+name
    assert stat.S_ISREG(st.st_mode) and st.st_nlink==1 and st.st_size==row['size_bytes']<=16*1024**2
    data=p.read_bytes();assert len(data)==row['size_bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
sha=hashlib.sha256(raw).hexdigest();command=freeze['commands']['auditor_prefix']+[sha,'--output',freeze['commands']['auditor_output']]
record=dict(kind='measured08-concrete-auditor-command-v1',at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),command=command,
    transport=dict(path=str(path),size_bytes=len(raw),sha256=sha),observer_returncode=transport['observed_returncode'],observer_timed_out=transport['timed_out'],
    source_commit=freeze['source_commit'],control_commit='2f74653367f14f0156479a52314f625d7400fc57',audit_invoked=False,runtime_qualified=False)
Path('/tmp/palimpsest-held08-concrete-audit-command.json').open('x').write(json.dumps(record,indent=2,sort_keys=True)+'\n')
print(json.dumps(record))
