"""One sequential execution of the approved four exploratory stages.

Reuses the existing bounded_process supervisor. No retries or cap transfer;
reproduction shares 1200 s, probes receive <=2400/3000 s, readout <=600 s.
Reserve each runner's full 1 GiB maximum plus logs before admitting it so serial
writes cannot exceed the shared 2 GiB cap. This is a local invocation receipt,
not a new qualification framework.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

from palimpsest.evaluate import bounded_process
from palimpsest.storage import StorageBudget, StorageLimits

ROOT = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/research-phase')
PYTHON = '/home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python'
HISTORY = Path('/home/utkarsh/Work/shraddha/brain/.worktrees')
STAMP = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT = ROOT/'runs'/('research-capability-'+STAMP)
OUT.mkdir(parents=True, exist_ok=False)
env = dict(os.environ, PYTHONPATH=str(ROOT/'src')+':'+str(ROOT/'scripts'),
           PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='1',
           OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='')
budget = StorageBudget((OUT,), StorageLimits(max_bytes=2*1024**3, min_free_bytes=2*1024**3))
started = time.monotonic()
phase_deadline = started+7200
receipt = {'label': 'EXPLORATORY — not gate evidence', 'started_utc': STAMP,
           'root': str(ROOT), 'output': str(OUT), 'max_seconds': 7200,
           'caps': {'combined_reproduction': 1200, 'puck_explore': 2400,
                    'nav_explore': 3000, 'readout': 600},
           'implementation_head': subprocess.check_output(['git','rev-parse','HEAD'], cwd=ROOT, text=True).strip(),
           'invocation_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'stages': {}, 'qualification_claims': [], 'held_out_used': False}
shutil.copyfile(__file__, OUT/'invocation.py')

def save():
    receipt['elapsed_seconds'] = time.monotonic()-started
    payload = json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False)+'\n'
    budget.check(len(payload.encode()), path=OUT/'execution.json')
    (OUT/'execution.json').write_text(payload)

def emit(value):
    print(json.dumps(value, sort_keys=True), flush=True)

def run(name, script, args, deadline):
    # Fit caps include admission; reserve 20 s inside the allocation for orderly
    # final receipt publication/cleanup. Never borrow another stage's allocation.
    available = min(deadline, phase_deadline)-time.monotonic()
    if available < 30:
        receipt['stages'][name] = {'status': 'unattempted', 'reason': 'allocation exhausted'}
        save(); return False
    inner = math.floor(available-20)
    budget.check(1024**3+10*1024**2, path=OUT/name)
    command = [PYTHON, str(ROOT/'scripts'/script), '--stage',
               'reproduce' if name.endswith('reproduce') else 'explore',
               '--seconds', str(inner), '--output', str(OUT/name), *args]
    emit({'stage': name, 'status': 'starting', 'inner_seconds': inner, 'output': str(OUT/name)})
    result = bounded_process(command, OUT/(name+'-supervisor'), available-5, env=env,
                             log_max_bytes=1024**2, storage_budget=budget)
    model_receipt = OUT/name/'report.json'
    item = {'command': command, 'supervisor': result}
    if model_receipt.is_file():
        raw = model_receipt.read_bytes()
        item.update(report_sha256=hashlib.sha256(raw).hexdigest(), report_path=str(model_receipt))
        item['runner_status'] = json.loads(raw).get('status')
    else:
        item['runner_status'] = 'absent'
    receipt['stages'][name] = item
    save()
    emit({'stage': name, 'runner_status': item['runner_status'], 'supervisor_status': result['status'],
          'elapsed_seconds': result['elapsed_seconds']})
    return result['status'] == 'completed' and item['runner_status'] == 'passed'

puck = ['--collection-report', str(HISTORY/'puck-stop-boundary/runs/m6-puck-teacher-collection-v2-20261003/gate/report.json'),
        '--collection-sha256', '3cf5044ac12fa80ebfed9aa044d0e983a94fcddb4e177da779a4684b944b518b',
        '--training-root', str(HISTORY/'puck-training-v2/runs/puck-training-v2-20261003')]
nav = ['--historical-root', str(HISTORY/'male-navigation-training-v2'),
       '--historical-bundles', str(HISTORY/'male-navigation-training-v2/runs/m7-navigation-training-v2-v2-6feade9-20261003/bundles')]
save()
reproduction_deadline = started+1200
try:
    puck_ok = run('puck-reproduce', 'puck_fit_ladder.py', puck, reproduction_deadline)
    nav_ok = run('nav-reproduce', 'nav_fit_ladder.py', nav, reproduction_deadline)
    if puck_ok:
        run('puck-explore', 'puck_fit_ladder.py', [*puck, '--reproduction-report', str(OUT/'puck-reproduce/report.json')],
            time.monotonic()+2400)
    else:
        receipt['stages']['puck-explore'] = {'status': 'unattempted', 'reason': 'reproduction not passed'}
    if nav_ok:
        run('nav-explore', 'nav_fit_ladder.py', [*nav, '--reproduction-receipt', str(OUT/'nav-reproduce/report.json')],
            time.monotonic()+3000)
    else:
        receipt['stages']['nav-explore'] = {'status': 'unattempted', 'reason': 'reproduction not passed'}
    readout_start = time.monotonic()
    index = []
    for path in sorted(OUT.rglob('*')):
        if time.monotonic()-readout_start > 600 or time.monotonic() >= phase_deadline:
            raise TimeoutError('Readout cap exhausted')
        if path.is_file() and path != OUT/'execution.json':
            index.append({'path': str(path.relative_to(OUT)), 'bytes': path.stat().st_size,
                          'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    receipt.update(status='finished-bounded-exploration', artifact_index=index,
                   readout_seconds=time.monotonic()-readout_start, storage=budget.usage())
except BaseException as error:
    receipt.update(status='execution-failed', error={'type': type(error).__name__, 'message': str(error)[:1024]})
    raise
finally:
    save(); emit({'status': receipt.get('status'), 'receipt': str(OUT/'execution.json'),
                  'elapsed_seconds': receipt['elapsed_seconds']})
