"""Observe actual04 PID/start identities after its completed external transport."""
from pathlib import Path
import datetime
import json
import os

root = Path('/home/utkarsh/.codex/worktrees/0071/brain')
base = root / 'runs/puck-cpu-held-qualification-04'
transport = json.loads(Path(str(base) + '-external-cli-transport.json').read_bytes())
result = json.loads((base / 'result.json').read_bytes())
supervision = json.loads((base / 'supervision.json').read_bytes())
assert transport['configuration_sha256'] == '6fa33667eb5c4d5ebe94f13a8e485be8ef3b2929f29c30ad1ee479baccfe47b8'
assert isinstance(transport['observed_returncode'], int)
identities = []
for row in supervision.get('tracked_processes', []):
    path = Path('/proc') / str(row['pid']) / 'stat'
    try:
        start = int(path.read_text().rpartition(')')[2].split()[19])
    except FileNotFoundError:
        start = None
    identities.append(dict(pid=row['pid'], start_ticks=row['start_ticks'], pid_exists=start is not None, current_start_ticks=start, matching_identity_alive=start == row['start_ticks']))
assert identities, 'No independent tracked identities available to observe'
report = dict(kind='qualification04-post-terminal-custody-observation-v1', at=datetime.datetime.now(datetime.timezone.utc).isoformat(), scope='dated host PID/start identity and artifact observation; no post-stage byte audit', proc_pid_namespace=os.readlink('/proc/self/ns/pid'), tracked_identities=identities, matching_survivors=[row for row in identities if row['matching_identity_alive']], baseline_after_absent=not os.path.lexists(base / 'baseline-after.json'), worker_stdout_bytes=(base / 'logs/stdout.log').stat().st_size, worker_stderr_bytes=(base / 'logs/stderr.log').stat().st_size)
target = Path(str(base) + '-post-terminal-custody-01.json')
with target.open('x') as stream:
    stream.write(json.dumps(report, sort_keys=True, indent=2) + '\n')
    stream.flush()
    os.fsync(stream.fileno())
print(json.dumps(report, sort_keys=True))
