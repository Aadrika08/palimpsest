from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
import time

root = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
label, *targets = sys.argv[1:]
out = root / 'runs/source-validation/cpu-binding-diagnostics-v1' / label
out.mkdir(parents=True, exist_ok=False)
command = [
    '/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python',
    '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *targets,
    '--basetemp=/tmp/palimpsest-cpu-binding-diagnostics-' + label,
]
environment = os.environ.copy()
environment.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1')
(out / 'command.json').write_text(json.dumps({
    'command': command, 'cwd': str(root),
    'environment_delta': {'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONDONTWRITEBYTECODE': '1'},
    'scope': 'authored source checks, no installed CPU runtime or actual allocation',
}, indent=2) + '\n')
with (root / 'runs/source-validation/qualification-amendment03-test.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    before = time.monotonic()
    process = subprocess.run(command, cwd=root, env=environment, capture_output=True, timeout=240)
    elapsed = time.monotonic() - before
(out / 'stdout.log').write_bytes(process.stdout)
(out / 'stderr.log').write_bytes(process.stderr)
(out / 'result.json').write_text(json.dumps({
    'returncode': process.returncode, 'elapsed_seconds': elapsed,
    'normal_return': True, 'actual_qualification04_invoked': False,
}, indent=2) + '\n')
print(json.dumps({'label': label, 'returncode': process.returncode, 'elapsed_seconds': elapsed}), flush=True)
print(process.stdout.decode(), end='', flush=True)
print(process.stderr.decode(), end='', file=sys.stderr, flush=True)
raise SystemExit(process.returncode)
