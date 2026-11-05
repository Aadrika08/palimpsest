"""Process exact pinned target-import closure serially under cumulative guards."""
import datetime, hashlib, json, os, re, resource, shutil, signal, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CACHE=Path.home()/'.cache/mathlib'
MATHLIB=ROOT/'.lake/packages/mathlib'
LEAN=Path.home()/'.elan/toolchains/leanprover--lean4---v4.31.0/bin/leantar'
BASE=json.loads((ROOT/'evidence/targeted-corrective-wave-01.json').read_text())['baseline_combined_logical_bytes']
LIMIT=4*1024**3; RESERVE=6*1024**3; STEP=256*1024**2
manifest=ROOT/'evidence/targeted-closure-03.tsv'
rows=[line.split('\t') for line in manifest.read_text().splitlines()]
for mod,archive,base,target,trace in rows:
    assert re.fullmatch(r'[A-Za-z0-9_.]+',mod) and re.fullmatch(r'[0-9a-f]{16}\.ltar',archive)
    assert base in ('mathlib','project') and '.lake/' in target and '.lake/' in trace
    assert Path(target).resolve().is_relative_to(ROOT) and Path(trace).resolve().is_relative_to(ROOT)
record={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'baseline_combined_logical_bytes':BASE,'max_incremental_bytes':LIMIT,'minimum_free_bytes':RESERVE,
 'manifest_sha256':hashlib.sha256(manifest.read_bytes()).hexdigest(),'target_modules':len(rows),
 'scope':'Serial exact pinned transitive imports only; same original corrective wave cumulative allocation', 'steps':[]}
path=ROOT/'evidence/targeted-corrective-wave-04.json'
with path.open('x') as f:json.dump(record,f,indent=2)
start=time.monotonic()
def size(p):
 total=0
 for b,ds,fs in os.walk(p):
  for f in fs:
   try:total+=(Path(b)/f).lstat().st_size
   except FileNotFoundError:pass
 return total
def write():
 record['combined_logical_bytes']=size(ROOT/'.lake')+size(CACHE)
 record['incremental_logical_bytes']=record['combined_logical_bytes']-BASE
 record['free_bytes']=shutil.disk_usage(ROOT).free
 path.write_text(json.dumps(record,indent=2)+'\n')
def guard():
 write()
 if record['incremental_logical_bytes']+STEP>LIMIT or record['free_bytes']<RESERVE+STEP:raise RuntimeError('resource admission refused')
 if time.monotonic()-start>1200:raise RuntimeError('1200second deadline')
def call(cmd):
 def bounds():resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
 p=subprocess.run(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=45,preexec_fn=bounds)
 return p.returncode,p.stdout
def stop(sig,frame):raise RuntimeError('terminated by signal '+str(sig))
signal.signal(signal.SIGTERM,stop)
try:
 for mod,name,base,target,trace in rows:
  if Path(target).exists() and Path(trace).exists():continue
  guard()
  archive=CACHE/name; step={'module':mod,'archive':str(archive),'base':base};record['steps'].append(step);write()
  if not archive.exists():
   part=CACHE/(name+'.corrective-wave04-download')
   if part.exists():raise RuntimeError('refuse replacing retained download '+str(part))
   rc,out=call(['curl','--fail','--silent','--show-error','--max-time','30','--max-filesize',str(64*1024**2),
     'https://lakecache.blob.core.windows.net/mathlib4/f/'+name,'-o',str(part)])
   step['download_exit']=rc;step['download_output']=out[:1000];write()
   if rc:raise RuntimeError(out)
   part.rename(archive)
  guard();step['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
  rc,out=call([str(LEAN),'--jobs','1','-C',str(MATHLIB if base=='mathlib' else ROOT),'-x',str(archive)])
  step['unpack_exit']=rc;step['unpack_output']=out[:1000];write()
  if rc or not Path(target).exists():raise RuntimeError('archive failed to supply target '+mod+': '+out)
  if len(record['steps'])%10==0:print(f"Recovered {len(record['steps'])}; cumulative incremental {record['incremental_logical_bytes']}",flush=True)
 record['status']='completed';write();print('TARGET_CLOSURE_COMPLETED',flush=True)
except Exception as e:
 record['status']='stopped';record['reason']=str(e);write();raise
