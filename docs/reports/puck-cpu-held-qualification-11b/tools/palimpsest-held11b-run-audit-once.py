"""Run the reviewed fixed audit envelope once and retain tool transport."""
from pathlib import Path
import hashlib,json,subprocess,time
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
control='27780dd5cbc096c26fb353faea7edfde878a4f74'
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()==control
assert subprocess.check_output(['git','status','--porcelain'],cwd=root)==b''
envelope=json.loads((root/'docs/plans/puck-cpu-held-qualification-11-execution.json').read_bytes())
command=envelope['commands']['audit']
assert command==['/usr/bin/timeout','--signal=TERM','--kill-after=5s','155s',
    '/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11',
    '-I','-S','-B','/tmp/palimpsest-held11b-external.py','audit']
concrete=json.loads(Path(envelope['concrete_audit_command_path']).read_bytes())
assert concrete['command'][-2:]==['--output',envelope['auditor_output']]
stage_rel='docs/plans/puck-cpu-held-qualification-11-control-validation/tools/stage_guard.py'
stage_raw=(root/stage_rel).read_bytes()
assert stage_raw==subprocess.check_output(['git','show',control+':'+stage_rel],cwd=root)
stage_namespace={'__name__':'held11b_stage_guard'};exec(compile(stage_raw,str(root/stage_rel),'exec'),stage_namespace)
stage=stage_namespace['check'](root)
stem=Path('/tmp/palimpsest-held11b-audit-tool')
record=dict(command=command,cwd=str(root),environment=envelope['environment'],control_commit=control,stage_guard=stage,
    runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    scope='sole independent audit of the measured actual runtime11 transport')
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
