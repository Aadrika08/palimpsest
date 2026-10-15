"""Observe the frozen acceptance auditor once against the completed04 transport."""
from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

root = Path('/home/utkarsh/.codex/worktrees/0071/brain')
freeze_raw = (root / 'docs/plans/puck-cpu-held-qualification-04-freeze.json').read_bytes()
assert hashlib.sha256(freeze_raw).hexdigest() == 'a34d83b15c41d8833daa9e28b63b406dd094472b41943d910326d663d4fc64e7'
freeze = json.loads(freeze_raw)
for name in ['configuration', 'auditor']:
    pin = freeze['pins'][name]
    data = (root / pin['path']).read_bytes()
    assert len(data) == pin['size_bytes'] and hashlib.sha256(data).hexdigest() == pin['sha256']
transport = Path(freeze['transport_path'])
transport_raw = transport.read_bytes()
transport_value = json.loads(transport_raw)
assert transport_value['configuration_sha256'] == freeze['pins']['configuration']['sha256']
assert isinstance(transport_value['observed_returncode'], int)
assert (root / 'runs/puck-cpu-held-qualification-04/result.json').is_file()
output = Path(freeze['audit']['output'])
prefix = str(output.with_suffix(''))
stdout, stderr, receipt = [Path(prefix + suffix) for suffix in ['.stdout', '.stderr', '.external-cli.json']]
assert all(not os.path.lexists(path) for path in [output, stdout, stderr, receipt])
command = freeze['audit']['command_prefix'] + ['--transport-sha256', hashlib.sha256(transport_raw).hexdigest(), '--output', str(output)]
started = time.monotonic()
timed_out = False
with stdout.open('xb', buffering=0) as out, stderr.open('xb', buffering=0) as err:
    process = subprocess.Popen(command, cwd=root, env=freeze['environment'], stdin=subprocess.DEVNULL, stdout=out, stderr=err, start_new_session=True, close_fds=True)
    try:
        process.wait(timeout=140)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=5)
    os.fsync(out.fileno())
    os.fsync(err.fileno())
elapsed = time.monotonic() - started
pin = lambda path: dict(path=str(path), size_bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
record = dict(kind='externally-observed-cpu-auditor-cli-v1', at=datetime.datetime.now(datetime.timezone.utc).isoformat(), command=command, observed_returncode=process.returncode, elapsed_seconds=elapsed, timed_out=timed_out, scope='actual qualification04 acceptance audit; preserves any refusal, not a passing failure audit', stdout=pin(stdout), stderr=pin(stderr), published=pin(output) if output.is_file() else None)
with receipt.open('x') as stream:
    stream.write(json.dumps(record, sort_keys=True, indent=2) + '\n')
    stream.flush()
    os.fsync(stream.fileno())
print(json.dumps(record, sort_keys=True), flush=True)
raise SystemExit(0 if process.returncode == 0 and not timed_out else 1)
