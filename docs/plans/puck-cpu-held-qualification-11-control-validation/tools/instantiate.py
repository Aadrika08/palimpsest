"""Instantiate one reviewed, Git-bound control template at its fixed /tmp path; never run it."""
from pathlib import Path
import hashlib,json,re,subprocess,sys
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='docs/plans/puck-cpu-held-qualification-11'
VALIDATION=BASE+'-control-validation'
TEMPLATES={'pre-admission-guard':VALIDATION+'/pre-admission-guard.py.in','external':BASE+'-external.py',
    'run-admission-once':VALIDATION+'/tools/run-admission-once.py.in','make-observer-guard':VALIDATION+'/tools/make-observer-guard.py',
    'run-observer-once':VALIDATION+'/tools/run-observer-once.py.in','bind-audit-command':VALIDATION+'/tools/bind-audit-command.py',
    'run-audit-once':VALIDATION+'/tools/run-audit-once.py.in','collect-outcome':VALIDATION+'/tools/collect-outcome.py.in',
    'archive-evidence':VALIDATION+'/tools/archive-evidence.py.in'}
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
name,control,count=sys.argv[1:]
assert name in TEMPLATES and re.fullmatch('[0-9a-f]{40}',control) and re.fullmatch('[1-9][0-9]*',count)
assert git('rev-parse','HEAD').decode().strip()==control and git('status','--porcelain')==b''
assert git('rev-parse','origin/research/puck-cpu-held-qualification-11').decode().strip()==control
raw=(ROOT/TEMPLATES[name]).read_bytes()
assert raw==git('show',control+':'+TEMPLATES[name])
text=raw.decode().replace('@CONTROL@',control).replace('@COUNT@',count)
assert '@CONTROL@' not in text and '@COUNT@' not in text
target=Path('/tmp/palimpsest-held11-'+name+'.py')
compile(text,str(target),'exec')
with target.open('x') as out:out.write(text)
print(json.dumps(dict(target=str(target),template=TEMPLATES[name],template_sha256=hashlib.sha256(raw).hexdigest(),
    sha256=hashlib.sha256(text.encode()).hexdigest(),size_bytes=len(text.encode()),control_commit=control,
    reviewed_control_count=int(count),invoked=False)))
