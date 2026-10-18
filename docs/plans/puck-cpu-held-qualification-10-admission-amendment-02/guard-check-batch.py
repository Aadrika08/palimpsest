from pathlib import Path
import hashlib,json,subprocess,sys,time
root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
base=root/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
label,template=sys.argv[1:]
out=base/'validation'/label;out.mkdir()
checker=base/'guard-path-check.py'
pins=[]
for name,path in [('guard-path-check.py',checker),('guard.py.in',base/template)]:
    raw=path.read_bytes();(out/name).write_bytes(raw)
    pins.append(dict(path=str(path.relative_to(root)),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
command=['/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11','-I','-S','-B',str(checker),str(base/template)]
env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
(out/'command.json').write_text(json.dumps(dict(command=command,cwd=str(root),environment=env,pins=pins,scope='single real history-read AST node on isolated fixture; entire guard compiled only; no admission/resource/payload/runtime execution'),indent=2,sort_keys=True)+'\n')
start=time.monotonic()
with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr:
    process=subprocess.run(command,cwd=root,env=env,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,timeout=15)
result=dict(exit_code=process.returncode,outer_timeout=False,elapsed_seconds=time.monotonic()-start)
(out/'terminal.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result));print((out/'stderr.log').read_text())
