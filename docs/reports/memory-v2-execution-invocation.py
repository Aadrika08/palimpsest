"""Single bounded invocation of the approved memory-v2 development phase.

This is an execution receipt, not a qualification framework. Stage allocations
cannot transfer time. Native stage parents own the user storage lease; their
detached workers are checked by exact PID/starttime/PGID after each stage.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

STARTED = time.monotonic()
from palimpsest.evaluate import bounded_process
from palimpsest.storage import StorageBudget, StorageLimits

def interrupted(signum, frame):
    raise RuntimeError('External phase deadline/interruption: '+str(signum))

signal.signal(signal.SIGTERM, interrupted)

ROOT = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/research-phase')
PYTHON = '/home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python'
HISTORY = ROOT.parent
ASSETS = HISTORY/'r0-reproduction/data/assets/flynn'
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT = ROOT/'runs'/('memory-v2-feasibility-'+STAMP)
ENV = dict(os.environ, PYTHONPATH=':'.join(map(str, (ROOT, ROOT/'src', ROOT/'scripts'))),
           PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1',
           OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='')
GiB, MiB = 1024**3, 1024**2
if shutil.disk_usage(ROOT).free < 10*GiB:
    raise RuntimeError('10 GiB initial free-space requirement failed')
OUT.mkdir(parents=True, exist_ok=False)
LIMITS = StorageLimits(max_bytes=8*GiB, min_free_bytes=2*GiB, max_runs=64, max_snapshots=2)
BUDGET = StorageBudget((OUT,), LIMITS, headroom_bytes=64*MiB)
CONTROL = StorageBudget((OUT,), LIMITS)
DEADLINE = STARTED+7200
RECEIPT = {'schema': 'memory-v2-phase-execution-v1', 'scope': 'exploratory feasibility',
    'started_utc': STAMP, 'output': str(OUT), 'max_seconds': 7200, 'max_bytes': 8*GiB,
    'caps': {'diagnostics': 600, 'prerequisites': 1800, 'pilot': 4200, 'readout': 600},
    'implementation_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'invocation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'stages': {}, 'qualification_claims': [], 'held_out_used': False, 'retries': 0,
    'detached_owner_cleanup': []}
shutil.copyfile(__file__, OUT/'invocation.py')

def save():
    RECEIPT['elapsed_seconds'] = time.monotonic()-STARTED
    payload = (json.dumps(RECEIPT, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    CONTROL.check(len(payload), path=OUT/'execution.json.pending')
    pending = OUT/'execution.json.pending'
    pending.write_bytes(payload)
    pending.replace(OUT/'execution.json')

def emit(item):
    print(json.dumps(item, sort_keys=True), flush=True)

def proc_identity(pid):
    raw = Path(f'/proc/{pid}/stat').read_text()
    fields = raw[raw.rfind(')')+2:].split()
    return int(fields[19]), os.getpgid(pid)

def cleanup(stage_output):
    # Kill only workers whose published PID identity still matches exactly.
    remaining = []
    for path in sorted(stage_output.rglob('owner.json')):
        owner = json.loads(path.read_bytes())
        pid, starttime, pgid = (owner[k] for k in ('pid', 'starttime', 'pgid'))
        if any(type(v) is not int or v <= 0 for v in (pid, starttime, pgid)) or pid != pgid:
            raise RuntimeError('Invalid detached owner identity')
        row = {'path': str(path.relative_to(OUT)), 'owner': owner}
        try:
            if proc_identity(pid) != (starttime, pgid):
                row['status'] = 'pid-reused-do-not-touch'
            else:
                os.killpg(pgid, signal.SIGTERM)
                remaining.append((pid, starttime, pgid, row))
                row['status'] = 'terminated-owned-worker'
        except ProcessLookupError:
            row['status'] = 'already-exited'
        except FileNotFoundError:
            row['status'] = 'already-exited'
        RECEIPT['detached_owner_cleanup'].append(row)
    if remaining:
        time.sleep(.5)
        for pid, starttime, pgid, row in remaining:
            try:
                if proc_identity(pid) == (starttime, pgid):
                    os.killpg(pgid, signal.SIGKILL)
                    row['status'] = 'killed-owned-worker'
            except (ProcessLookupError, FileNotFoundError):
                pass

def run(name, script, args, stage_deadline, cap_flag='--seconds-cap', lease=False):
    available = min(stage_deadline, DEADLINE)-time.monotonic()
    if available < 40:
        RECEIPT['stages'][name] = {'status': 'unattempted', 'reason': 'allocation exhausted'}
        save()
        return False
    # Existing bounded_process can spend 10 seconds draining/killing, and the
    # detached-owner survey needs additional time. Leave 20 seconds outside it.
    inner = math.floor(available-30)
    command = [PYTHON, str(ROOT/'scripts'/script), '--repo', str(ROOT), '--output', str(OUT/name),
               cap_flag, str(inner), *args]
    BUDGET.check(64*MiB, path=OUT/name)
    emit({'stage': name, 'status': 'starting', 'inner_seconds': inner})
    if lease:
        with BUDGET.lock():
            result = bounded_process(command, OUT/(name+'-supervisor'), available-20,
                env=ENV, log_max_bytes=MiB, storage_budget=BUDGET)
    else:
        result = bounded_process(command, OUT/(name+'-supervisor'), available-20,
            env=ENV, log_max_bytes=MiB, storage_budget=BUDGET)
    cleanup(OUT/name)
    report_path = OUT/name/'report.json'
    row = {'command': command, 'supervisor': result, 'report': str(report_path)}
    if report_path.is_file():
        payload = report_path.read_bytes()
        row.update(report_sha256=hashlib.sha256(payload).hexdigest(), runner_status=json.loads(payload).get('status'))
    else:
        row['runner_status'] = 'absent'
    RECEIPT['stages'][name] = row
    save()
    emit({'stage': name, 'runner_status': row['runner_status'], 'supervisor_status': result['status']})
    return result['status'] == 'completed' and row['runner_status'] in ('passed', 'completed')

save()
try:
    run('diagnostics', 'control_diagnostics_v2.py', [
        '--puck-producer', str(HISTORY/'research-puck-fit'),
        '--nav-producer', str(HISTORY/'male-navigation-training-v2'),
        '--output-limit-bytes', str(16*MiB)], STARTED+600, lease=True)
    native_args = ['--assets', str(ASSETS), '--history-root', str(HISTORY/'memory-experiments'),
                   '--phase-root', str(OUT)]
    prerequisites_deadline = min(DEADLINE, time.monotonic()+1800)
    ready = run('prerequisites', 'memory_decision_pilot.py', ['--stage', 'feasibility', *native_args], prerequisites_deadline)
    if ready:
        run('pilot', 'memory_decision_pilot.py', ['--stage', 'pilot', *native_args,
            '--feasibility-report', str(OUT/'prerequisites/report.json')], min(DEADLINE, time.monotonic()+4200))
    else:
        RECEIPT['stages']['pilot'] = {'status': 'unattempted', 'reason': 'mandatory prerequisites not passed'}
        save()
    readout_start = time.monotonic()
    readout_deadline = min(DEADLINE, readout_start+600)
    index = []
    for path in sorted(OUT.rglob('*')):
        if time.monotonic() >= readout_deadline:
            raise TimeoutError('Readout cap exhausted')
        if path.is_file() and path != OUT/'execution.json':
            digest = hashlib.sha256()
            with path.open('rb') as stream:
                while block := stream.read(MiB):
                    if time.monotonic() >= readout_deadline:
                        raise TimeoutError('Readout cap exhausted')
                    digest.update(block)
            index.append({'path': str(path.relative_to(OUT)), 'bytes': path.stat().st_size, 'sha256': digest.hexdigest()})
    RECEIPT.update(status='finished-bounded-attempt', artifact_index=index,
        readout_seconds=time.monotonic()-readout_start, storage=BUDGET.usage())
except BaseException as error:
    for name in ('prerequisites', 'pilot'):
        cleanup(OUT/name)
    RECEIPT.update(status='execution-failed', error={'type': type(error).__name__, 'message': str(error)[:2048]})
    raise
finally:
    save()
    emit({'status': RECEIPT.get('status'), 'receipt': str(OUT/'execution.json'), 'elapsed_seconds': RECEIPT['elapsed_seconds']})
