"""Serial module-target Lake verification; no dependency update/cache download."""
import datetime,hashlib,json,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
label='serial-lake-verification-01'
p=ROOT/'evidence'/f'{label}.json'
record={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'scope':'Each own module dependency readiness checked with --no-build; then serial own-module builds; --no-cache always; final default library build',
 'commands':[],'source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((ROOT/'ChangeAudit').glob('*.lean'))}}
for f in ('ChangeAudit.lean','lean-toolchain','lakefile.toml','lake-manifest.json'):record['source_sha256'][f]=hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
with p.open('x') as f:json.dump(record,f,indent=2)
start=time.monotonic()
def run(cmd,name):
 mem=dict(l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines())
 avail=int(mem['MemAvailable'].split()[0])*1024
 if avail<11*1024**3//2 or shutil.disk_usage(ROOT).free<6*1024**3+64*1024**2:raise RuntimeError('resource preflight')
 resource=ROOT/'evidence'/f'{label}-{name}.resources'
 wrapped=['/usr/bin/time','-v','-o',str(resource)]+cmd
 t=time.monotonic();r=subprocess.run(wrapped,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=180)
 log=ROOT/'evidence'/f'{label}-{name}.log';log.write_text(r.stdout)
 record['commands'].append({'command':wrapped,'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-t,'mem_available_before_bytes':avail,'log':str(log.relative_to(ROOT)),'resources':str(resource.relative_to(ROOT))})
 p.write_text(json.dumps(record,indent=2)+'\n');print(name,'exit',r.returncode,flush=True)
 if r.returncode:print(r.stdout,flush=True);raise RuntimeError('Lake failed '+name)
try:
 for name in ('Contrast','Ville','Exponential','FreshBounded','Anytime','Numerical','Targets','FixedHorizon','Audit'):
  mod='ChangeAudit.'+name
  run(['lake','--no-cache','--no-build','build','+'+mod+':deps'],name+'-deps')
  run(['lake','--no-cache','build','+'+mod+':olean'],name)
 run(['lake','--no-cache','build'], 'default')
 record['status']='passed'
except Exception as e:record['status']='failed';record['reason']=str(e)
finally:
 record['elapsed_seconds']=time.monotonic()-start
 record['sources_unchanged']=all(hashlib.sha256((ROOT/f).read_bytes()).hexdigest()==h for f,h in record['source_sha256'].items())
 p.write_text(json.dumps(record,indent=2)+'\n')
if record['status']!='passed':raise SystemExit(1)
