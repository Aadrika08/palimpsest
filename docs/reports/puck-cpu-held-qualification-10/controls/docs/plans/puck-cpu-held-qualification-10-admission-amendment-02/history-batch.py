from pathlib import Path
import hashlib,json,subprocess,sys,time
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE=ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
label=sys.argv[1];out=BASE/'validation'/label;out.mkdir()
names=['admission.py','history-check.py'];pins=[]
for name in names:
    raw=(BASE/name).read_bytes();(out/name).write_bytes(raw)
    pins.append(dict(path=name,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
command=['/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11','-I','-S','-B',str(BASE/'history-check.py')]
env=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
(out/'command.json').write_text(json.dumps(dict(command=command,cwd=str(ROOT),environment=env,pins=pins,scope='small history metadata only; no admission/main, census, vendor or runtime'),indent=2,sort_keys=True)+'\n')
started=time.monotonic()
with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr:
    process=subprocess.run(command,cwd=ROOT,env=env,stdout=stdout,stderr=stderr,timeout=30)
t=dict(exit_code=process.returncode,elapsed_seconds=time.monotonic()-started,outer_timeout=False)
(out/'terminal.json').write_text(json.dumps(t,indent=2,sort_keys=True)+'\n')
print(json.dumps(t));print((out/'stderr.log').read_text()[-5500:])
