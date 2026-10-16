"""Record bounded authored source validation; no installed allocation."""
import hashlib,json,os,re,subprocess,sys,time
from pathlib import Path
ROOT=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-diagnostic-epoch09-v1')
PYTHON='/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python'
label,seconds,storage,*tests=sys.argv[1:]
assert re.fullmatch('[a-z0-9-]+',label) and storage in ('private','persistent')
assert 1<=int(seconds)<=600 and tests and all(t.startswith(('tests/test_puck_','--deselect=tests/test_puck_')) for t in tests)
base=ROOT/'runs/source-validation'/('epoch09-'+label);base.mkdir(parents=True,exist_ok=False)
paths=['scripts/qualify_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_held_runtime.py',
 'scripts/observe_puck_cpu_held_allocation.py','scripts/puck_worker_bootstrap.py',
 'src/palimpsest/puck_runtime_qualification.py',
 'tests/test_puck_cpu_held_amendment09.py','tests/test_puck_cpu_held_observer09.py',
 'tests/test_puck_cpu_held_amendment09_integration.py']
pins={}
for name in paths:
 p=ROOT/name
 if not p.exists():continue
 raw=p.read_bytes();pins[name]=hashlib.sha256(raw).hexdigest();target=base/'source'/name
 target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
temporary=str(base/'tmp') if storage=='persistent' else '/tmp/puck-epoch09-'+label
command=['/usr/bin/timeout','--signal=TERM','--kill-after=5s',seconds+'s','/usr/bin/bwrap',
 '--unshare-user','--uid','1000','--gid','1000','--bind','/','/','--tmpfs','/tmp','--dev','/dev',
 '--proc','/proc','--chdir',str(ROOT),'--',PYTHON,'-m','pytest','-q','-p','no:cacheprovider',
 '--basetemp',temporary,*tests]
overrides={'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1','PYTHONDONTWRITEBYTECODE':'1'}
(base/'command.json').write_text(json.dumps(dict(command=command,environment_overrides=overrides,pins=pins,
 scope='Authored source tests only; inherited environment not fully recorded.'),indent=2)+'\n')
start=time.monotonic();result=subprocess.run(command,cwd=ROOT,env=dict(os.environ,**overrides),capture_output=True)
(base/'stdout.txt').write_bytes(result.stdout);(base/'stderr.txt').write_bytes(result.stderr)
terminal=dict(returncode=result.returncode,elapsed_seconds=time.monotonic()-start)
(base/'terminal.json').write_text(json.dumps(terminal,indent=2)+'\n')
print(json.dumps(dict(label=label,**terminal)))
print(result.stdout.decode(errors='replace')[-5000:]);print(result.stderr.decode(errors='replace')[-2000:])
sys.exit(result.returncode)
