from pathlib import Path
import datetime
import hashlib
import json
import subprocess
import time

root=Path('/home/utkarsh/.codex/worktrees/0071/brain')
folder=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03/runs/source-validation/cpu-amendment04/prepared-byte-audit04-01')
runner=folder/'runner.py'
assert len(runner.read_bytes())==7847
assert hashlib.sha256(runner.read_bytes()).hexdigest()=='43f50ea4fbe008ba8889f746a491a1f16e3a73725e286ddf2ebd3214a0774956'
output=Path('/tmp/palimpsest-puck-cpu-prepared-byte-audit-04-01.json')
assert not output.exists() and not output.is_symlink()
assert not (folder/'external-cli.json').exists()
command=['/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11','-I','-S','-B',str(runner)]
environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
(folder/'command.json').write_text(json.dumps(dict(command=command,cwd=str(root),environment=environment),indent=2)+'\n')
at=datetime.datetime.now(datetime.timezone.utc).isoformat();before=time.monotonic()
p=subprocess.run(command,cwd=root,env=environment,capture_output=True,timeout=140)
elapsed=time.monotonic()-before
(folder/'stdout.log').write_bytes(p.stdout);(folder/'stderr.log').write_bytes(p.stderr)
def pin(path):
    data=path.read_bytes()
    return dict(path=str(path),size_bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
receipt=dict(kind='externally-observed-pre04-data-only-census-cli-v1',at=at,command=command,
    observed_returncode=p.returncode,elapsed_seconds=elapsed,scope='dated current prepared bytes only; no preparation/qualification allocation invoked',
    stdout=pin(folder/'stdout.log'),stderr=pin(folder/'stderr.log'),publication=pin(output) if output.is_file() else None)
(folder/'external-cli.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps(receipt),flush=True)
assert p.returncode==0 and elapsed<120 and p.stderr==b''
assert output.read_bytes()==p.stdout
result=json.loads(p.stdout)
assert result['status']=='PASS' and result['runner_sha256']=='43f50ea4fbe008ba8889f746a491a1f16e3a73725e286ddf2ebd3214a0774956'
assert result['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
assert result['file_count']==27255 and result['input_bytes']==1318494346 and result['root_count']==4
assert result['qualifications01_02_03_still_failed_consumed'] and result['qualification04_invoked'] is False
