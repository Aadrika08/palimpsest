from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
import time

root=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
label,*targets=sys.argv[1:]
out=root/'runs/source-validation/cpu-amendment04'/label
out.mkdir(parents=True,exist_ok=False)
command=['/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python',
         '-m','pytest','-q','-p','no:cacheprovider',*targets,'--basetemp='+str(out/'tmp')]
env=os.environ.copy();env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
(out/'command.json').write_text(json.dumps(dict(command=command,cwd=str(root),
    environment_delta=dict(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1'),
    scope='authored source checks only; no installed runtime or actual allocation'),indent=2)+'\n')
with (root/'runs/source-validation/qualification-amendment03-test.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    before=time.monotonic()
    p=subprocess.run(command,cwd=root,env=env,capture_output=True,timeout=300)
    elapsed=time.monotonic()-before
(out/'stdout.log').write_bytes(p.stdout);(out/'stderr.log').write_bytes(p.stderr)
(out/'result.json').write_text(json.dumps(dict(returncode=p.returncode,elapsed_seconds=elapsed,
    normal_return=True,actual_qualification04_invoked=False),indent=2)+'\n')
print(json.dumps(dict(label=label,returncode=p.returncode,elapsed_seconds=elapsed)),flush=True)
lines=p.stdout.decode().splitlines()
print('\n'.join(lines[-80:]),flush=True)
print(p.stderr.decode(),file=sys.stderr,flush=True)
raise SystemExit(p.returncode)
