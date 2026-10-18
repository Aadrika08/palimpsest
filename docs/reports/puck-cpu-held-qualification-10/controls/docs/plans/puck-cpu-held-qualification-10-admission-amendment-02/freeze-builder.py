"""Freeze one distinct admission02 control set; no admission/main execution."""
from pathlib import Path
import copy,datetime,hashlib,json,stat,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
REL='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
BASE=ROOT/REL
SOURCE='e723db037ed1f790c2618798d59f56913054754f'
IMPLEMENTATION='cbe48b339f4839ec4d2b5ef153d0dc0820be712e'
CONTROL01='b3d50f5d8efbd36c56337c323d66768831c0f43f'
def load(path):return json.loads((ROOT/path).read_bytes())
def pin(path):
    p=ROOT/path;s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_nlink==1 and s.st_size<=16*1024**2,path
    raw=p.read_bytes();return dict(path=path,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
pins={}
def add(row):
    if isinstance(row,str):row=pin(row)
    assert pin(row['path'])==row,row['path']
    assert row['path'] not in pins or pins[row['path']]==row,row['path']
    pins[row['path']]=row
assert not (BASE/'freeze.json').exists()
assert (BASE/'freeze-builder.py').read_bytes()==Path(__file__).read_bytes()
old_path='docs/plans/puck-cpu-held-qualification-10-freeze.json'
old=load(old_path);config=load(REL+'/configuration.json');prior=load('docs/plans/puck-cpu-held-qualification-10.json')
assert config==prior
raw=(BASE/'configuration.json').read_bytes()
assert len(raw)==8988 and hashlib.sha256(raw).hexdigest()=='4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170'
assert raw==(json.dumps(config,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()
for row in old['pins']:add(row)
assert len(pins)==1998
for row in config['sources']:
    assert pin(row['path'])==row
    for revision in (SOURCE,IMPLEMENTATION):assert (ROOT/row['path']).read_bytes()==subprocess.check_output(['git','show',revision+':'+row['path']],cwd=ROOT)
add(old_path)
packet='docs/reports/puck-cpu-held-qualification-10-admission-01'
index=load(packet+'/evidence-index.json')
assert index['control_commit']==CONTROL01 and index['artifact_count']==89
assert set(r['archived_path'] for r in index['artifacts'])=={str(p.relative_to(ROOT/packet)) for p in (ROOT/packet).rglob('*') if p.is_file() and p!=ROOT/packet/'evidence-index.json'}
add(packet+'/evidence-index.json');add(packet+'.md')
for row in index['artifacts']:add(dict(path=packet+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256']))
assert len(index['control_paths'])==47
for path in index['control_paths']:
    assert (ROOT/path).read_bytes()==subprocess.check_output(['git','show',CONTROL01+':'+path],cwd=ROOT)
    add(path)
for path in sorted(BASE.rglob('*')):
    if path.is_file():add(str(path.relative_to(ROOT)))
new=copy.deepcopy(old)
new.update(kind='puck-cpu-held-qualification10-admission02-controls-v1',admission_check_id=2,
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),control_revision=2,
    control_revision_reason='Separate canonical-only configuration and admission02 paths; preserve consumed admission01 and all original controls.',
    actual10_admission_invoked_at_freeze=True,admission01_failed_consumed=True,admission02_invoked_at_freeze=False,
    previous10_freeze=pin(old_path),previous10_control_commit=CONTROL01,
    admission01_failure_packet=pin(packet+'/evidence-index.json'),canonical_only_configuration_delta=True,
    scope='one fresh full data-only admission02 followed only after review/guard by sole runtime10; no operator/renderer/study',
    pins=[pins[name] for name in sorted(pins)])
def commands(value):
    if isinstance(value,str):return value.replace('docs/plans/puck-cpu-held-qualification-10.json',REL+'/configuration.json').replace('docs/plans/puck-cpu-held-qualification-10-admission.py',REL+'/admission.py').replace('b7da3957cd81f017f7c59beb764577551384d54c634062f9841053c839d12915','4cc0cf9ab118eba0cdb8522014ee9990c33502f44e3e32f9366c65ff4bd40170')
    if isinstance(value,list):return [commands(v) for v in value]
    if isinstance(value,dict):return {k:commands(v) for k,v in value.items()}
    raise TypeError(type(value).__name__)
new['commands']=commands(old['commands'])
assert new['source_commit']==SOURCE and new['observer_invocations']==1 and new['implicit_retry'] is False
assert new['limits']==config['limits'] and new['negative_imports']==config['negative_imports']
raw=(json.dumps(new,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();assert len(raw)<=1024**2
with (BASE/'freeze.json').open('xb') as out:out.write(raw)
print(json.dumps(dict(freeze=dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()),pins=len(pins),pinned_bytes=sum(r['size_bytes'] for r in pins.values()),admission02_invoked=False,runtime10_invoked=False)))
