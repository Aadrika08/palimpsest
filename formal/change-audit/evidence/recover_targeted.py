"""Serial targeted cache recovery. No lake update or broad dependency build."""
import datetime, json, os, re, resource, shutil, signal, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CACHE = Path.home()/'.cache/mathlib'
MATHLIB = ROOT/'.lake/packages/mathlib'
LEAN = Path.home()/'.elan/toolchains/leanprover--lean4---v4.31.0/bin/leantar'
LIMIT = 4*1024**3
RESERVE = 6*1024**3
STEP = 256*1024**2

def size(p):
    total=0
    for base, ds, fs in os.walk(p):
        for f in fs:
            try: total += (Path(base)/f).lstat().st_size
            except FileNotFoundError: pass
    return total

def usage():
    return size(ROOT/'.lake')+size(CACHE)

BASE=json.loads((ROOT/'evidence/targeted-corrective-wave-01.json').read_text())['baseline_combined_logical_bytes']
start=time.monotonic()
record={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'baseline_combined_logical_bytes':BASE,'max_incremental_bytes':LIMIT,
        'minimum_free_bytes':RESERVE,'reserve_before_each_serial_step':STEP,
        'scope':'Only exact-pinned cache archives for actual missing imports. Serial extraction/download. No full lake update.', 'steps':[]}
name='targeted-corrective-wave-03'
path=ROOT/'evidence'/f'{name}.json'
with path.open('x') as f: json.dump(record,f,indent=2)

def write():
    record['current_combined_logical_bytes']=usage()
    record['incremental_logical_bytes']=record['current_combined_logical_bytes']-BASE
    record['disk_free_bytes']=shutil.disk_usage(ROOT).free
    path.write_text(json.dumps(record,indent=2)+'\n')

def guard():
    u=usage()
    if u-BASE+STEP>LIMIT or shutil.disk_usage(ROOT).free<RESERVE+STEP:
        raise RuntimeError('resource admission refused')

def call(cmd, timeout=30):
    def limits():
        resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
    p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                     timeout=timeout,preexec_fn=limits)
    return p.returncode,p.stdout

def stopped(signum, frame):
    raise RuntimeError('terminated by signal '+str(signum))
signal.signal(signal.SIGTERM,stopped)
target='ChangeAudit/Contrast.lean'
seen=set()
try:
  for i in range(256):
    if time.monotonic()-start>600: raise RuntimeError('600 second wave deadline')
    guard()
    rc,out=call(['lake','env','lean','-j1','-M2048',target])
    (ROOT/'evidence'/f'{name}-compile-{i:03}.log').write_text(out)
    if rc==0:
        record['status']='target_compiles'; write(); print('TARGET_COMPILES',flush=True); break
    m=re.search("of module ([A-Za-z0-9_'.]+) does not exist",out)
    if not m:
        record['status']='proof_errors'; write(); print(out,flush=True); break
    mod=m.group(1)
    if mod in seen: raise RuntimeError('same missing module after one recovery: '+mod)
    seen.add(mod)
    rc,look=call(['lake','env',str(MATHLIB/'.lake/build/bin/cache'),'lookup',mod])
    h=re.search(r'(/[^\n ]+/([0-9a-f]{16})\.ltar)',look)
    if not h: raise RuntimeError('lookup did not identify exact archive: '+look[:1000])
    archive=Path(h.group(1))
    step={'module':mod,'archive':str(archive),'lookup':look[:1500]}
    record['steps'].append(step);write()
    if not archive.exists():
        guard()
        rc,out=call(['curl','--fail','--silent','--show-error','--max-time','25','--max-filesize',str(64*1024**2),
                     'https://lakecache.blob.core.windows.net/mathlib4/f/'+archive.name,'-o',str(archive)])
        step['download_exit']=rc
        if rc: raise RuntimeError(out)
    guard()
    base=MATHLIB if mod.startswith('Mathlib.') or mod=='Mathlib' else ROOT
    step['extraction_base']=str(base)
    rc,out=call([str(LEAN),'--jobs','1','-C',str(base),'-x',str(archive)])
    step['unpack_exit']=rc; step['unpack_output']=out[:1500]
    write()
    if rc: raise RuntimeError(out)
    if len(record['steps'])%5==0: print(f"recovered {len(record['steps'])}: {mod}; incremental={record['incremental_logical_bytes']}",flush=True)
  else: record['status']='step_cap';write()
except Exception as e:
  record['status']='stopped'; record['reason']=str(e);write();raise
