"""First navigation fits after correcting an implementation-only preflight pin.

The preserved initial rejection read no corpus and ran no fit. This continuation
consumes the remaining original reproduction allocation and the original nav
probe allocation; it does not retry a scientific fit or transfer puck time.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from datetime import datetime, timezone
from palimpsest.evaluate import bounded_process
from palimpsest.storage import StorageBudget, StorageLimits

ROOT = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/research-phase')
OUT = ROOT/'runs/research-capability-20261004T070529Z'
PYTHON = '/home/utkarsh/Work/shraddha/brain/.worktrees/lab-hardening/.venv/bin/python'
HISTORY = Path('/home/utkarsh/Work/shraddha/brain/.worktrees/male-navigation-training-v2')
initial_bytes = (OUT/'execution.json').read_bytes()
initial = json.loads(initial_bytes)
if initial['stages']['nav-reproduce']['runner_status'] != 'absent':
    raise ValueError('Continuation only admits the preserved pre-corpus HEAD rejection')
failure_log = (OUT/'nav-reproduce-supervisor/stderr.log').read_text()
if 'Pinned historical producer HEAD differs' not in failure_log:
    raise ValueError('Unexpected failed preflight; do not retry')
origin = datetime.strptime(initial['started_utc'], '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc).timestamp()
origin_age = time.time()-origin
started = time.monotonic()
phase_deadline = started+7200-origin_age
used_reproduction = sum(initial['stages'][name]['supervisor']['elapsed_seconds']
                        for name in ('puck-reproduce','nav-reproduce'))
remaining_reproduction = 1200-used_reproduction
env = dict(os.environ, PYTHONPATH=str(ROOT/'src')+':'+str(ROOT/'scripts'), PYTHONDONTWRITEBYTECODE='1',
           OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', CUDA_VISIBLE_DEVICES='')
budget = StorageBudget((OUT,), StorageLimits(max_bytes=2*1024**3, min_free_bytes=2*1024**3))
if (OUT/'nav-continuation.json').exists(): raise ValueError('Single continuation, no repeated fit')
receipt = {'label':'EXPLORATORY — not gate evidence', 'initial_execution_sha256':hashlib.sha256(initial_bytes).hexdigest(),
           'reason':'Correct producer publication HEAD; pinned reader sources unchanged; no earlier nav corpus read or fit',
           'implementation_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
           'initial_reproduction_seconds':used_reproduction, 'remaining_reproduction_seconds':remaining_reproduction,
           'origin_age_seconds':origin_age, 'stages':{}, 'qualification_claims':[], 'held_out_used':False}
shutil.copyfile(__file__, OUT/'nav-continuation-invocation.py')

def save():
    receipt['elapsed_seconds'] = time.monotonic()-started
    payload = json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False)+'\n'
    budget.check(len(payload.encode()),path=OUT/'nav-continuation.json')
    (OUT/'nav-continuation.json').write_text(payload)

def run(name, stage, seconds, extra):
    allocation = min(seconds,phase_deadline-time.monotonic()-600)
    if allocation < 30:
        receipt['stages'][name] = {'status':'unattempted','reason':'Original budget exhausted'}
        save(); return False
    budget.check(1024**3+10*1024**2,path=OUT/name)
    command = [PYTHON,str(ROOT/'scripts/nav_fit_ladder.py'),'--stage',stage,'--seconds',str(math.floor(allocation-20)),
               '--output',str(OUT/name),'--historical-root',str(HISTORY),
               '--historical-bundles',str(HISTORY/'runs/m7-navigation-training-v2-v2-6feade9-20261003/bundles'),*extra]
    print(json.dumps({'stage':name,'status':'starting','allocation_seconds':allocation}),flush=True)
    result = bounded_process(command,OUT/(name+'-supervisor'),allocation-5,env=env,storage_budget=budget)
    item = {'command':command,'supervisor':result}
    path = OUT/name/'report.json'
    if path.is_file():
        raw = path.read_bytes(); item.update(report_sha256=hashlib.sha256(raw).hexdigest(),report_path=str(path),runner_status=json.loads(raw)['status'])
    else: item['runner_status']='absent'
    receipt['stages'][name]=item; save()
    print(json.dumps({'stage':name,'runner_status':item['runner_status'],'supervisor_status':result['status'],
                      'elapsed_seconds':result['elapsed_seconds']}),flush=True)
    return result['status']=='completed' and item['runner_status']=='passed'

save()
try:
    passed=run('nav-reproduce-v2','reproduce',remaining_reproduction,[])
    if passed:
        run('nav-explore','explore',3000,['--reproduction-receipt',str(OUT/'nav-reproduce-v2/report.json')])
    else: receipt['stages']['nav-explore']={'status':'unattempted','reason':'Reproduction did not pass'}
    readout_start=time.monotonic()
    receipt['artifact_index']=[]
    for path in sorted(OUT.rglob('*')):
        if time.monotonic()-readout_start > 600-initial['readout_seconds'] or time.monotonic() >= phase_deadline:
            raise TimeoutError('Original readout or aggregate deadline exhausted')
        if path.is_file() and path!=OUT/'nav-continuation.json':
            receipt['artifact_index'].append({'path':str(path.relative_to(OUT)),'bytes':path.stat().st_size,
                                              'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    receipt.update(status='finished-bounded-exploration',readout_seconds=time.monotonic()-readout_start,storage=budget.usage())
except BaseException as error:
    receipt.update(status='execution-failed',error={'type':type(error).__name__,'message':str(error)[:1024]})
    raise
finally:
    save(); print(json.dumps({'status':receipt.get('status'),'receipt':str(OUT/'nav-continuation.json'),
                              'elapsed_seconds':receipt['elapsed_seconds']}),flush=True)
