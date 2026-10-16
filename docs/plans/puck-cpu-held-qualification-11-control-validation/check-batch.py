"""Run one retained metadata-only control check; never admission, census or runtime."""
from pathlib import Path
import hashlib,json,subprocess,sys,time
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
base='docs/plans/puck-cpu-held-qualification-11'
validation=root/(base+'-control-validation')
label,kind=sys.argv[1:]
python='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
if kind=='selfcheck':
    sources=[('source.py',root/(base+'-control-selfcheck.py'))];command=[python,'-I','-S','-B',str(sources[0][1])]
    scope='authenticated metadata readers only; no admission/main, SITE/staged/native payloads or vendors'
elif kind=='tools':
    sources=[('tools-check.py',validation/'tools-check.py')];command=[python,'-I','-S','-B',str(sources[0][1])]
    scope='template compilation and isolated-fixture pre-observer derivation only; no /tmp tool instantiation, guard, admission or runtime'
else:
    assert kind=='guard'
    sources=[('guard-path-check.py',validation/'guard-path-check.py'),('guard.py.in',validation/'pre-admission-guard.py.in')]
    command=[python,'-I','-S','-B',str(sources[0][1]),str(sources[1][1])]
    scope='single real history-read AST node on isolated fixture; entire guard compiled only; no admission/resource/payload/runtime execution'
out=validation/label;out.mkdir()
pins=[]
for name,path in sources:
    raw=path.read_bytes();(out/name).write_bytes(raw)
    pins.append(dict(path=str(path.relative_to(root)),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
(out/'command.json').write_text(json.dumps(dict(command=command,cwd=str(root),environment=env,pins=pins,scope=scope),indent=2,sort_keys=True)+'\n')
start=time.monotonic()
with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr:
    process=subprocess.run(command,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=120)
result=dict(label=label,exit_code=process.returncode,outer_timeout=False,elapsed_seconds=time.monotonic()-start)
(out/'terminal.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result));print((out/'stdout.log').read_text()[-4000:]);print((out/'stderr.log').read_text()[-4000:])
