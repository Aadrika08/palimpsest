from pathlib import Path
import json
import os
import subprocess
import sys
import time

root = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-held-qualification-amendment-03')
label, *files = sys.argv[1:]
isolated = files and files[0] in ('--namespace', '--namespace-persistent')
persistent = isolated and files[0] == '--namespace-persistent'
if isolated:
    files.pop(0)
out = root / 'runs/source-validation/distributed-roster-worker' / label
out.mkdir(parents=True)
command = ['/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python',
           '-m', 'pytest', '-q', '-p', 'no:cacheprovider', '--basetemp',
           '/tmp/distributed-worker-check' if isolated and not persistent else str(out / 'tmp'), *files]
if isolated:
    command = ['/usr/bin/bwrap', '--unshare-user', '--uid', str(os.getuid()), '--gid',
               str(os.getgid()), '--bind', '/', '/', '--tmpfs', '/tmp', '--dev', '/dev',
               '--proc', '/proc', '--chdir', str(root), '--', *command]
overlay = {'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
(out / 'command.json').write_text(json.dumps(dict(argv=command, cwd=str(root),
    environment_overlay=overlay), indent=2) + '\n')
started = time.monotonic()
with (out / 'stdout.log').open('wb') as stdout, (out / 'stderr.log').open('wb') as stderr:
    try:
        result = subprocess.run(command, cwd=root, env=dict(os.environ, **overlay),
                                stdout=stdout, stderr=stderr, timeout=300)
        receipt = dict(returncode=result.returncode, timed_out=False)
    except subprocess.TimeoutExpired:
        receipt = dict(returncode=None, timed_out=True)
receipt['seconds'] = time.monotonic() - started
(out / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
print('\n'.join((out / 'stdout.log').read_text().splitlines()[-10:]))
print((out / 'stderr.log').read_text()[-2048:])
