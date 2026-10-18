from pathlib import Path
import hashlib,json,subprocess,sys,time
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
proof=root/'docs/plans/puck-cpu-held-qualification-10-source-evidence'
label=sys.argv[1];out=proof/label;out.mkdir()
python='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
names=['docs/plans/puck-cpu-held-qualification-10-admission.py',str((proof/'history-check.py').relative_to(root))]
pins=[]
for name in names:
    raw=(root/name).read_bytes();p=out/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    pins.append(dict(path=name,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
command=[python,'-I','-S','-B',str(proof/'history-check.py')]
env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
(out/'command.json').write_text(json.dumps(dict(command=command,cwd=str(root),environment=env,pins=pins,scope='small historical records only; no admission/main or vendor'),indent=2,sort_keys=True)+'\n')
start=time.monotonic()
with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr:
    run=subprocess.run(command,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=30)
terminal=dict(label=label,exit_code=run.returncode,elapsed_seconds=time.monotonic()-start,outer_timeout=False)
(out/'terminal.json').write_text(json.dumps(terminal,indent=2,sort_keys=True)+'\n')
print(json.dumps(terminal));print((out/'stderr.log').read_text()[-6000:])
