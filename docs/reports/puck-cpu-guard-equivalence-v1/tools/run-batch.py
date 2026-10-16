"""Run one named authored batch with retained pre-execution source and streams."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time

ROOT=Path('/home/utkarsh/.codex/worktrees/f2fa/brain')
BASE=ROOT/'docs/plans/puck-cpu-guard-equivalence-v1'
PYTHON='/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python'
phase=sys.argv[1];assert len(sys.argv)==2 and phase in ('baseline01','candidate01')
production=ROOT/'scripts/puck_worker_bootstrap.py'
assert hashlib.sha256(production.read_bytes()).hexdigest()=='f137429398dc30270e67ef198c508231f9e2cf02d3aeedb98663630cafa51451'
out=BASE/'validation'/phase;assert not out.exists();out.mkdir(parents=True)
tests=['tests/test_puck_guard_union_dispatch.py','tests/test_puck_guard_cost.py']
args=['-q','-s','-p','no:cacheprovider','--basetemp','/tmp/puck-guard-equivalence-'+phase,
    '-k','not authored_cache_workload',*tests]
inner=[PYTHON,'-B','-m','pytest',*args]
if phase=='candidate01':
    inner=[PYTHON,'-B',str(BASE/'run_candidate.py'),str(BASE/'inplace-whitelist.py'),*args]
command=['/usr/bin/timeout','--signal=TERM','--kill-after=5s','60s','/usr/bin/bwrap',
    '--unshare-user','--uid','1000','--gid','1000','--bind','/','/','--tmpfs','/tmp',
    '--dev','/dev','--proc','/proc','--chdir',str(ROOT),'--',*inner]
paths=['scripts/puck_worker_bootstrap.py','docs/plans/puck-cpu-guard-equivalence-v1.md',*tests,
    'tests/test_puck_worker_bootstrap.py','tests/test_puck_worker_dependencies.py']
paths+=['src/palimpsest/'+name+'.py' for name in ('puck_execution_files','puck_dependency_files',
    'puck_dependency_imports','puck_dependency_bindings','puck_native_origins','puck_native_identity','puck_runtime_qualification')]
if phase=='candidate01':paths+=['docs/plans/puck-cpu-guard-equivalence-v1/'+name for name in ('run_candidate.py','inplace-whitelist.py')]
pins=[]
for name in sorted(paths):
    raw=(ROOT/name).read_bytes();p=out/'source'/name;p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as stream:stream.write(raw)
    pins.append(dict(path=name,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
overrides=dict(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1')
with (out/'command.json').open('x') as stream:
    stream.write(json.dumps(dict(command=command,cwd=str(ROOT),environment_overrides=overrides,pins=pins,
        scope='Seven authored semantic cases; no timing workload, installed imports, actual10 or qualification.'),sort_keys=True,indent=2)+'\n')
started=time.monotonic()
with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr:
    result=subprocess.run(command,cwd=ROOT,env=dict(os.environ,**overrides),stdin=subprocess.DEVNULL,
        stdout=stdout,stderr=stderr,timeout=70,close_fds=True)
terminal=dict(exit_code=result.returncode,elapsed_seconds=time.monotonic()-started,phase=phase,
    normal_outer_return=type(result.returncode) is int and result.returncode>=0,
    production_unchanged=hashlib.sha256(production.read_bytes()).hexdigest()=='f137429398dc30270e67ef198c508231f9e2cf02d3aeedb98663630cafa51451')
with (out/'terminal.json').open('x') as stream:stream.write(json.dumps(terminal,sort_keys=True,indent=2)+'\n')
print(json.dumps(terminal,sort_keys=True),flush=True)
raise SystemExit(result.returncode)
