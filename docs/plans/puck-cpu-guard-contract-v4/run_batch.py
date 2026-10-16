from pathlib import Path
import hashlib,json,os,subprocess,sys,time
ROOT=Path('/home/utkarsh/.codex/worktrees/293b/brain')
BASE=ROOT/'docs/plans/puck-cpu-guard-contract-v4'
PYTHON='/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python'
label=sys.argv[1];cap=int(sys.argv[2]);tests=sys.argv[3:]
assert label.replace('-','').isalnum() and 1<=cap<=360 and tests
out=BASE/'validation'/label;assert not out.exists();out.mkdir(parents=True)
command=['/usr/bin/timeout','--signal=TERM','--kill-after=5s',str(cap)+'s','/usr/bin/bwrap',
 '--unshare-user','--uid','1000','--gid','1000','--bind','/','/','--tmpfs','/tmp','--dev','/dev','--proc','/proc',
 '--chdir',str(ROOT),'--',PYTHON,'-B','-m','pytest','-q','-s','-p','no:cacheprovider','--basetemp','/tmp/q4-'+label,*tests]
paths=['scripts/puck_worker_bootstrap.py','docs/plans/puck-cpu-guard-v4-prospective.md',
 'tests/test_puck_worker_bootstrap.py','tests/test_puck_worker_dependencies.py','tests/test_puck_cpu_runtime_entry.py',
 'tests/test_puck_tmpfs_dependencies.py',*[p for p in tests if p.startswith('tests/') and '::' not in p]]
paths+=['src/palimpsest/'+name+'.py' for name in ('puck_execution_files','puck_dependency_files',
 'puck_dependency_imports','puck_dependency_bindings','puck_native_origins','puck_native_identity','puck_runtime_qualification')]
pins=[]
for name in sorted(set(paths)):
 raw=(ROOT/name).read_bytes();p=out/'source'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
 pins.append(dict(path=name,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
overrides=dict(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1',TMPDIR='/tmp')
(out/'command.json').write_text(json.dumps(dict(command=command,cwd=str(ROOT),environment_overrides=overrides,pins=pins,
 scope='Authored packages and real-worker guard semantics only. No installed runtime, actual10 or qualification authority.'),sort_keys=True,indent=2)+'\n')
started=time.monotonic();expired=False
with (out/'stdout.log').open('xb') as stdout,(out/'stderr.log').open('xb') as stderr:
 try:
  result=subprocess.run(command,cwd=ROOT,env=dict(os.environ,**overrides),stdin=subprocess.DEVNULL,
   stdout=stdout,stderr=stderr,timeout=cap+10,close_fds=True)
  code=result.returncode
 except subprocess.TimeoutExpired:
  code=None;expired=True
terminal=dict(exit_code=code,elapsed_seconds=time.monotonic()-started,label=label,outer_timeout=expired)
(out/'terminal.json').write_text(json.dumps(terminal,sort_keys=True,indent=2)+'\n')
print(json.dumps(terminal,sort_keys=True),flush=True)
raise SystemExit(1 if code is None else code)
