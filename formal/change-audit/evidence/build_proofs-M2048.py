"""Compile only project proof sources; never build/fetch dependencies."""
import datetime, hashlib, json, os, re, shutil, signal, subprocess, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
modules=('Contrast','Ville','Exponential','FreshBounded','Anytime','Numerical','Targets','FixedHorizon','Audit')
label=sys.argv[1] if len(sys.argv)==2 else ''
if not re.fullmatch(r'[a-z0-9-]{1,50}',label):raise SystemExit('unique lowercase evidence label required')
report=ROOT/'evidence'/f'build-{label}.json'
if report.exists():raise SystemExit('refuse replacing existing build evidence')
inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/'ChangeAudit').glob('*.lean'))}
inputs['ChangeAudit.lean']=hashlib.sha256((ROOT/'ChangeAudit.lean').read_bytes()).hexdigest()
for config in ('lean-toolchain','lakefile.toml','lake-manifest.json'):
 inputs[config]=hashlib.sha256((ROOT/config).read_bytes()).hexdigest()
for path in inputs:
 if not path.endswith('.lean'):continue
 text=(ROOT/path).read_text()
 if re.search(r'\b(sorry|admit|native_decide)\b|^\s*axiom\s',text,re.M):raise SystemExit('prohibited proof escape: '+path)
version=subprocess.check_output(['lake','env','lean','--version'],cwd=ROOT,text=True,timeout=15).strip()
mathlib=subprocess.check_output(['git','-C',str(ROOT/'.lake/packages/mathlib'),'rev-parse','HEAD'],text=True,timeout=15).strip()
if mathlib!='fabf563a7c95a166b8d7b6efca11c8b4dc9d911f' or 'version 4.31.0' not in version:raise SystemExit('unexpected proof environment')
record={'lean_version':version,'mathlib_revision':mathlib,'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_sha256':inputs,
 'scope':'Serial own-source lean compilation only, no automatic dependency build or acquisition', 'commands':[]}
report.write_text(json.dumps(record,indent=2)+'\n')
out=ROOT/'.lake/build/lib/lean/ChangeAudit';out.mkdir(parents=True,exist_ok=True)
start=time.monotonic()
try:
 for mod in modules:
  if shutil.disk_usage(ROOT).free<6*1024**3+64*1024**2:raise RuntimeError('6GiB disk reserve')
  cmd=['lake','env','lean','-j1','-M2048','-o',str(out/f'{mod}.olean'),f'ChangeAudit/{mod}.lean']
  t=time.monotonic()
  p=subprocess.run(cmd,cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
  log=ROOT/'evidence'/f'build-{label}-{mod}.log';log.write_text(p.stdout)
  record['commands'].append({'module':mod,'command':cmd,'exit_code':p.returncode,'elapsed_seconds':time.monotonic()-t,'log':str(log.relative_to(ROOT))})
  report.write_text(json.dumps(record,indent=2)+'\n')
  print(mod,'exit',p.returncode,flush=True)
  if p.returncode:print(p.stdout,flush=True);raise RuntimeError('compile failed: '+mod)
 record['status']='compiled'
except Exception as e:
 record['status']='failed';record['reason']=str(e)
finally:
 record['elapsed_seconds']=time.monotonic()-start
 record['sources_unchanged']=all(hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h for p,h in inputs.items())
 report.write_text(json.dumps(record,indent=2)+'\n')
if record['status']!='compiled':raise SystemExit(1)
