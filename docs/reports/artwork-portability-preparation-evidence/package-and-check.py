"""One local fixed-source portability preparation; no exporter or inference."""
from datetime import datetime, timezone
import hashlib,json,stat,sys,time,zipfile
from pathlib import Path
import verify_artwork_handoff as h
from palimpsest.storage import StorageBudget,StorageLimits

started=time.monotonic()
root=Path(__file__).resolve().parent
inputs=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/artwork-handoff/runs/artwork-handoff-v1-inputs')
manifest=h.load_manifest(); expected={row['path']:row for row in manifest['files']}
budget=StorageBudget((root,),StorageLimits(max_bytes=32*1024**2,min_free_bytes=2*1024**3))
report={'schema':'artwork-portability-preparation-v1','observed_utc':datetime.now(timezone.utc).isoformat(),
 'scope':'Local byte-preserving package and relocated input admission only; no exporter, inference, native owner, public transfer or human acceptance',
 'manifest_sha256':h.MANIFEST_SHA256,'original_inputs':str(inputs),'qualification_claims':[],
 'human_acceptance':'unattempted','public_sharing':'unapproved','status':'failed'}
try:
 with budget.lock():
  before=h.admit(inputs,manifest)
  archives=[]
  for name in ('palimpsest-artwork-inputs-v1.zip','reproduction-check.zip'):
   path=root/name;budget.check(8*1024**2,path=path)
   with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_STORED) as archive:
    for member in sorted(expected):
     row=expected[member];raw=h.artifacts._read(inputs/member,row['size_bytes'])
     assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
     info=zipfile.ZipInfo(member,(1980,1,1,0,0,0));info.create_system=3
     info.external_attr=(stat.S_IFREG|0o644)<<16
     archive.writestr(info,raw)
   archives.append({'path':str(path),**h.fingerprint(path,8*1024**2)})
  assert archives[0]['sha256']==archives[1]['sha256']
  relocated=root/'relocated-inputs';relocated.mkdir(exist_ok=False)
  with zipfile.ZipFile(archives[0]['path'],'r') as archive:
   members=archive.infolist()
   assert len(members)==len(expected)==19 and {m.filename for m in members}==set(expected)
   for member in members:
    row=expected[member.filename]
    assert member.compress_type==zipfile.ZIP_STORED and member.file_size==row['size_bytes']
    assert stat.S_ISREG(member.external_attr>>16)
    raw=archive.read(member)
    assert hashlib.sha256(raw).hexdigest()==row['sha256']
    destination=relocated/member.filename
    assert not Path(member.filename).is_absolute() and '..' not in Path(member.filename).parts
    budget.check(len(raw),path=destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open('xb') as f:f.write(raw)
  assert h.admit(relocated,manifest)==before==h.admit(inputs,manifest)
  assert not {'torch','mujoco'}.intersection(sys.modules)
  assert time.monotonic()-started<120
  report.update(status='passed',files=19,source_bytes=manifest['source_bytes'],archives=archives,
   relocation=str(relocated),sources_unchanged=True,deterministic_archive=True,
   no_model_runtime_loaded=True,storage=budget.usage())
except BaseException as error:
 report['error']={'type':type(error).__name__,'message':str(error)}
 raise
finally:
 report['elapsed_seconds']=time.monotonic()-started
 with (root/'preparation.json').open('x') as f:json.dump(report,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({key:report[key] for key in ('status','files','source_bytes','deterministic_archive','sources_unchanged','elapsed_seconds')},indent=2))
