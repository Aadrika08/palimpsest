import hashlib,json,zipfile
from pathlib import Path
from record_choir_material import budget
from prepare_artwork_encounter import read_archive,encounter_html,ARCHIVE,ARCHIVE_PIN,choir_details
root=Path('runs/choir-material-2026-10-22-v1').absolute();out=root/'encounter'
audit=json.loads((root/'independent-audit.json').read_text());assert audit['status']=='passed'
store=budget(root)
with store.lock():
 assert not out.exists();out.mkdir()
 files=read_archive(ARCHIVE,ARCHIVE_PIN,lambda:store.check(0,path=out))
 files['counterfactual-choir.wav']=(root/'choir.wav').read_bytes()
 duration,voices,segments,prefix=choir_details(files['counterfactual-choir.wav'])
 assert duration==120 and len(segments)==18 and prefix
 notice='''# Choir material update — 22 October 2026

This encounter updates Counterfactual choir only. It contains 120 seconds from
6,000 actual CPU FLYNN control intervals in a 6,004-interval lab recording.
The 18 episodes include resets; the final episode uses a prefix. The population
mapping is fixed, with no normalization or crossfades. Start at low volume;
listening/artistic acceptance is pending. The other five artworks remain the
historical development material described below, including the short Afterimage.

The source recording is about 1.21 GiB and remains local outside this derivative
pack. choir-source.json retains source registration and independent audit details.
Public model acquisition and the bounded generation recipe are in repository
commit a8f7ac2; an independent rerun is not guaranteed to reproduce identical bytes.
No full six-mode exhibition or independent-operator acceptance is claimed.

## Historical guide for the other five modes

'''
 files['README.md']=notice.encode()+files['README.md']
 files['choir-source.json']=json.dumps({'registration':json.loads((root/'registration.json').read_text()),'audit':audit,'supervisor':json.loads((root/'result.json').read_text())},indent=2).encode()
 files['index.html']=encounter_html(files)
 files['checksums.json']=json.dumps({'qualification_claims':[],'files':{name:{'size_bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in files.items() if name!='checksums.json'}},indent=2).encode()
 assert sum(map(len,files.values()))<64*1024**2
 for name,raw in files.items():
  store.check(len(raw),path=out/name)
  with (out/name).open('xb') as f:f.write(raw)
 archive=root/'palimpsest-choir-encounter-2026-10-22.zip'
 store.check(sum(map(len,files.values()))+65536,path=archive)
 with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_STORED) as z:
  for name in sorted(files):z.writestr(name,files[name])
 with zipfile.ZipFile(archive) as z:
  assert set(z.namelist())==set(files)
  assert all(z.read(name)==raw for name,raw in files.items())
 print(json.dumps({'archive':str(archive),'size_bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(files)}))
