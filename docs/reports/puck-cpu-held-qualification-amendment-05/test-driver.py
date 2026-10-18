from pathlib import Path
import fcntl
import json
import os
import subprocess
import sys
import time

root = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
label, *targets = sys.argv[1:]
out = root / 'runs/source-validation/cpu-amendment05' / label
out.mkdir(parents=True, exist_ok=False)
temp = out / 'tmp' if label.startswith(('affected-parent', 'isolated-persistent')) else Path('/tmp') / ('palimpsest-amendment05-' + label)
assert not temp.exists()
command = ['/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', *targets, '--basetemp=' + str(temp)]
if label.startswith('isolated-'):
    command = ['/usr/bin/bwrap', '--unshare-user', '--uid', str(os.getuid()), '--gid', str(os.getgid()), '--bind', '/', '/', '--tmpfs', '/tmp', '--dev', '/dev', '--proc', '/proc', '--chdir', str(root), '--', *command]
env = os.environ.copy()
env.update(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1')
(out / 'command.json').write_text(json.dumps(dict(command=command, cwd=str(root), environment_delta=dict(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1'), scope='authored source checks only; no vendor stack or actual allocation'), sort_keys=True, indent=2) + '\n')
with (root / 'runs/source-validation/qualification-amendment03-test.lock').open('a') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    started = time.monotonic()
    process = subprocess.run(command, cwd=root, env=env, capture_output=True, timeout=300)
    elapsed = time.monotonic() - started
(out / 'stdout.log').write_bytes(process.stdout)
(out / 'stderr.log').write_bytes(process.stderr)
(out / 'result.json').write_text(json.dumps(dict(normal_return=True, returncode=process.returncode, elapsed_seconds=elapsed, scope='authored source checks; no new actual allocation'), sort_keys=True, indent=2) + '\n')
print(json.dumps(dict(label=label, returncode=process.returncode, elapsed_seconds=elapsed)), flush=True)
print('\n'.join(process.stdout.decode().splitlines()[-100:]), flush=True)
print(process.stderr.decode(), file=sys.stderr, flush=True)
raise SystemExit(process.returncode)
