"""Run the reviewed fixed audit envelope once and retain tool transport."""
from pathlib import Path
import hashlib,json,subprocess,time
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
control='796359a099131157b5b91db38f14784628d5d7c5'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==control
assert subprocess.check_output(['git','status','--porcelain'],cwd=root)==b''
envelope=json.loads((root/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/execution.json').read_bytes())
command=envelope['commands']['audit']
assert command==['/usr/bin/timeout','--signal=TERM','--kill-after=5s','155s',
    '/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11',
    '-I','-S','-B','/tmp/palimpsest-held10-amendment02-external.py','audit']
concrete=json.loads(Path(envelope['concrete_audit_command_path']).read_bytes())
assert concrete['command'][-2:]==['--output',envelope['auditor_output']]
stem=Path('/tmp/palimpsest-held10-amendment02-audit-tool')
record=dict(command=command,cwd=str(root),environment=envelope['environment'],control_commit=control,
    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    scope='sole independent audit of the measured actual runtime10 transport')
with Path(str(stem)+'-command.json').open('x') as out:json.dump(record,out,indent=2,sort_keys=True);out.write('\n')
start=time.monotonic()
with Path(str(stem)+'.stdout').open('xb') as stdout,Path(str(stem)+'.stderr').open('xb') as stderr:
    try:
        process=subprocess.run(command,cwd=root,env=envelope['environment'],stdin=subprocess.DEVNULL,
            stdout=stdout,stderr=stderr,timeout=170)
        terminal=dict(exit_code=process.returncode,outer_timeout=False)
    except subprocess.TimeoutExpired:
        terminal=dict(exit_code=None,outer_timeout=True)
terminal.update(elapsed_seconds=time.monotonic()-start,phase='audit',runtime_invoked=True)
with Path(str(stem)+'-terminal.json').open('x') as out:json.dump(terminal,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(terminal),flush=True)
print(Path(str(stem)+'.stdout').read_text(),flush=True)
print(Path(str(stem)+'.stderr').read_text(),flush=True)
raise SystemExit(0 if terminal['exit_code']==0 and not terminal['outer_timeout'] else 1)
