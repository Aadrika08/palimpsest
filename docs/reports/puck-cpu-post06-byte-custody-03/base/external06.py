from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
freeze=root/'docs/plans/puck-cpu-held-qualification-06-freeze.json'
raw=freeze.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='54dfca9f7a2bccff7a436e12d232f80944f564fce48a66480dacb77d1693e61c'
value=json.loads(raw);phase=sys.argv[1];assert phase in ('admission','observer','audit')
if phase=='audit':
    command=json.loads(Path('/tmp/palimpsest-held06-concrete-audit-command.json').read_bytes())['command']
    prefix=value['commands']['auditor_prefix']
    assert command[:len(prefix)]==prefix and command[-2:]==['--output',value['commands']['auditor_output']]
    assert len(command)==len(prefix)+3
else:command=value['commands'][phase]
stem=Path('/tmp/palimpsest-held06-'+phase+'-external')
assert not stem.with_suffix('.json').exists()
started=time.monotonic()
with Path(str(stem)+'.stdout').open('xb') as stdout,Path(str(stem)+'.stderr').open('xb') as stderr:
    try:
        process=subprocess.run(command,cwd=root,env=value['outer_environment'],stdin=subprocess.DEVNULL,
            stdout=stdout,stderr=stderr,timeout=240 if phase=='observer' else 145,close_fds=True)
        result=dict(returncode=process.returncode,timed_out=False)
    except subprocess.TimeoutExpired:result=dict(returncode=None,timed_out=True)
result.update(command=command,cwd=str(root),environment=value['outer_environment'],elapsed_seconds=time.monotonic()-started)
for channel in ('stdout','stderr'):
    path=Path(str(stem)+'.'+channel);payload=path.read_bytes()
    result[channel]=dict(path=str(path),size_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
stem.with_suffix('.json').write_text(json.dumps(result,sort_keys=True,indent=2)+'\n')
print(json.dumps(result,sort_keys=True),flush=True)
for channel in ('stdout','stderr'):
    payload=Path(str(stem)+'.'+channel).read_text()
    print(channel+':\n'+payload[:20000],flush=True)
raise SystemExit(0 if result['returncode']==0 and not result['timed_out'] else 1)
