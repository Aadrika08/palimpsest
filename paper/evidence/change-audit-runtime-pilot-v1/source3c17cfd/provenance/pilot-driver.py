"""Single bounded pilot invocation; never resume or retry an existing attempt."""
import json
import os
from pathlib import Path
import resource
import sys

from paper.studies.change_audit_v1.process import run_accounted
from palimpsest.storage import StorageBudget, StorageLimits

ROOT=Path('/home/utkarsh/Work/shraddha/palimpsest/.worktrees/authority-paper-rewrite')
BUNDLE=ROOT/'runs/change-audit-pilot-v1-20261105-source3c17cfd'
SOURCE='3c17cfda8aa4cb101d93c3936fee85625cbdea7d'
PRIOR=5.412801999999999
ROSTER_SHA='d6777f22057f99c227a8945f00656163d79a5d70cf508aaf7ced37c651b79470'
PROJECTION_SHA='3dd036e3fe319fa6b5553ce9cbc3900014375242da0e0eb60a483615eba838ff'
previous=json.loads((BUNDLE/'preparation-process-accounting.json').read_text())
accounting=previous['accounting']
if (previous['aggregate_research_cpu_seconds']!=PRIOR or accounting['accounting_complete'] is not True
        or accounting['tree_drained'] is not True or accounting['status']!='completed'
        or accounting['returncode']!=0):
    raise RuntimeError('Prior preparation charge is not complete and reconciled')
if (BUNDLE/'pilot').exists() or (BUNDLE/'pilot-process-accounting.json').exists():
    raise RuntimeError('Existing attempt cannot be resumed')
budget=StorageBudget([BUNDLE,ROOT/'runs/change-audit-pilot-v1-20261105-source9e6d5cf'],StorageLimits(max_bytes=512*1024**2,min_free_bytes=6*1024**3))
# The child owns the single-writer lease across the pilot; this outer monitor
# reads the combined namespace (inputs, logs and all pilot artifacts) only.
budget.check(154*1024**2,path=BUNDLE)
def monitor(sample):
    budget.check(256*1024,path=BUNDLE)
    own=resource.getrusage(resource.RUSAGE_SELF)
    aggregate=PRIOR+sample['sampled_worker_cpu_seconds']+own.ru_utime+own.ru_stime
    if aggregate>=3600-15:
        return 'aggregate audit CPU threshold with 15-second cleanup reserve'

command=[sys.executable,'-B',str(ROOT/'paper/studies/change_audit_v1/pilot.py'),
    '--mode','execute','--input-roster',str(BUNDLE/'inputs/input-roster.json'),
    '--expected-input-roster-sha256',ROSTER_SHA,
    '--namespace-projection',str(BUNDLE/'inputs/namespace-projection.json'),
    '--expected-namespace-projection-sha256',PROJECTION_SHA,
    '--source-commit',SOURCE,'--output',str(BUNDLE/'pilot'),
    '--project-cpu-used-seconds',str(PRIOR),'--audit-cpu-used-seconds',str(PRIOR)]
admission={'schema':'change-audit-outer-pilot-admission-v1','source_commit':SOURCE,
    'command':command,'prior_audit_and_project_cpu_seconds':PRIOR,
    'combined_retained_cap_bytes':512*1024**2,'min_free_bytes':6*1024**3,
    'wall_seconds':1800,'cpu_threshold_seconds':3600-PRIOR-15,
    'native_log_bytes_per_stream':512*1024,'automatic_retry':False,
    'scope':'engineering pilot only; no sampling, improvement or capability certification'}
with (BUNDLE/'outer-pilot-admission.json').open('x') as stream:
    json.dump(admission,stream,sort_keys=True,allow_nan=False);stream.write('\n');stream.flush();os.fsync(stream.fileno())
result=run_accounted(command,cwd=ROOT,env=dict(os.environ),
    stdout_path=BUNDLE/'pilot-stdout.log',stderr_path=BUNDLE/'pilot-stderr.log',
    wall_seconds=1800,cpu_seconds=3600-PRIOR-15,max_log_bytes=512*1024,monitor=monitor)
charge=result['subtree_cpu_seconds']+result['parent_cpu_seconds'] if result['accounting_complete'] and result['tree_drained'] else None
report={'schema':'change-audit-outer-pilot-accounting-v1','accounting':result,
    'pilot_process_cpu_seconds':charge,'prior_cpu_seconds':PRIOR,
    'aggregate_audit_and_project_cpu_seconds':None if charge is None else PRIOR+charge,
    'budget':budget.usage(),'scope':'whole parent CLI and waited descendants including terminal writes and lease release; helper parent interval sampled separately',
    'sampling_eligibility_verified':False,'certified_improvement':False,'runtime_qualification':False}
payload=(json.dumps(report,sort_keys=True,allow_nan=False)+'\n').encode()
budget.check(len(payload),path=BUNDLE/'pilot-process-accounting.json')
with (BUNDLE/'pilot-process-accounting.json').open('xb') as stream:
    stream.write(payload);stream.flush();os.fsync(stream.fileno())
print(json.dumps({'status':result['status'],'returncode':result['returncode'],
    'accounting_complete':result['accounting_complete'],'tree_drained':result['tree_drained'],
    'pilot_cpu_seconds':charge,'aggregate_cpu_seconds':report['aggregate_audit_and_project_cpu_seconds'],
    'retained_bytes_before_final_accounting':report['budget']['used_bytes']},sort_keys=True))
if result['status']!='completed' or result['returncode']!=0 or charge is None:sys.exit(1)
