"""Author fixed07 metadata only; never invoke admission or runtime controls."""
import copy
import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='f0b122db7ccc4fd0117b0f8527b48b3a5d3b1c61'
OLD='docs/plans/puck-cpu-held-qualification-06-freeze.json'
NEW='docs/plans/puck-cpu-held-qualification-07-freeze.json'

def load(path):return json.loads((ROOT/path).read_bytes())
def pin(path):
    raw=(ROOT/path).read_bytes()
    assert len(raw)<=16*1024**2,path
    return dict(path=path,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

old=load(OLD);config=load('docs/plans/puck-cpu-held-qualification-07.json')
assert pin(OLD)['sha256']=='54dfca9f7a2bccff7a436e12d232f80944f564fce48a66480dacb77d1693e61c'
assert pin('docs/plans/puck-cpu-held-qualification-07.json')['sha256']=='1ed4b198a38512c751cca43e11fdb1cd00e7683031be545e6ccd12016555ee60'
pins={};changed=[]
def add(row):
    if isinstance(row,str):row=pin(row)
    assert pin(row['path'])==row,row['path']
    assert row['path'] not in pins or pins[row['path']]==row,row['path']
    pins[row['path']]=row

allowed={'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py','scripts/qualify_puck_cpu_held_runtime.py'}
for row in old['pins']:
    current=pin(row['path'])
    if current!=row:
        assert row['path'] in allowed,row['path']
        archive=dict(row,path='docs/reports/puck-cpu-held-qualification-06/source/'+row['path'])
        add(archive)
        changed.append(dict(historical_live_path=row['path'],historical_pin=row,archived_pin=archive,current_pin=current))
    add(current)
assert {r['historical_live_path'] for r in changed}==allowed
for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):add(row)
prep=load(config['preparation_acceptance']['configuration']['path'])
add(prep['inputs']['candidate'])
for path in [
    OLD,'docs/plans/puck-cpu-held-qualification-07.json',
    'docs/plans/puck-cpu-held-qualification-07-admission.py',
    'docs/plans/puck-cpu-held-qualification-07-review.md',
    'docs/plans/puck-cpu-held-qualification-07-proof-roster-review.json',
    'docs/plans/puck-cpu-held-qualification-07-admission-source-review.json',
    'docs/plans/puck-cpu-pillow-origin-profile-v1.md',
    'docs/reports/puck-cpu-held-qualification-06.md',
    'docs/reports/puck-cpu-held-qualification-06/evidence-index.json',
    'docs/reports/puck-cpu-pillow-origin-profile-v1.md',
    'docs/reports/puck-cpu-post06-byte-custody-03.md',
]:add(path)
for path in sorted((ROOT/'docs/plans/puck-cpu-pillow-origin-profile-v1').rglob('*')):
    if path.is_file():add(str(path.relative_to(ROOT)))
for stem in ['puck-cpu-pillow-origin-profile-v1','puck-cpu-post06-byte-custody-03']:
    parent='docs/reports/'+stem;index=load(parent+'/evidence-index.json');add(parent+'/evidence-index.json')
    for row in index['artifacts']:
        add(dict(path=parent+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256']))
mapping=json.loads(Path('/tmp/palimpsest-held07-prospective-control-map.json').read_bytes())
for row in mapping['historical06_immutable_archives']:add({k:row[k] for k in ('path','size_bytes','sha256')})
for i in range(1,7):
    path='runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json'
    result=load(path);assert result['status']=='FAIL' and result['allocation_id']==i
    add(path)
new=copy.deepcopy(old)
for key in ['actual05_inputs_unchanged','actual06_invoked_at_freeze','qualifications01_02_03_04_05_failed_consumed']:new.pop(key)
new.update(kind='puck-cpu-held-qualification07-frozen-controls-v1',branch='research/puck-cpu-held-qualification-07',
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=BASE,
    actual07_invoked_at_freeze=False,actual07_admission_invoked_at_freeze=False,
    actual06_non_candidate_inputs_unchanged=True,qualifications01_02_03_04_05_06_failed_consumed=True,
    scope='one separately admitted held four-import qualification07; no episode, renderer, operator or scientific study',
    historical06_replaced_live_sources=changed,previous06_freeze=pin(OLD),current_candidate=config['inputs']['candidate'],
    post03_scope='Dated DATA06/C retention only; does not replace fresh07/D full admission',
    post03_index=pin('docs/reports/puck-cpu-post06-byte-custody-03/evidence-index.json'),
    post03_result=pin('docs/reports/puck-cpu-post06-byte-custody-03/result/success.json'),
    admission_limits=dict(normal_seconds=120,hard_seconds=130,address_space_bytes=512*1024**2,max_fds=40000,file_bytes=16*1024**2,core_bytes=0,initial_ram_bytes=2<<30,final_ram_bytes=2<<30),
    pins=[pins[path] for path in sorted(pins)])
old_sha='da630b05b871508686a4c92402725820b40b27253b2652b47c686a8f441a04e8';new_sha=pin('docs/plans/puck-cpu-held-qualification-07.json')['sha256']
new['commands']=json.loads(json.dumps(old['commands']).replace('puck-cpu-held-qualification-06','puck-cpu-held-qualification-07').replace(old_sha,new_sha))
assert new['limits']==config['limits']==old['limits'] and new['negative_imports']==config['negative_imports']==old['negative_imports']
assert new['preparation_acceptance']==config['preparation_acceptance']==old['preparation_acceptance']
raw=(json.dumps(new,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
(ROOT/NEW).open('xb').write(raw)
print(json.dumps(dict(path=NEW,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),pin_count=len(pins),pinned_bytes=sum(r['size_bytes'] for r in pins.values()),changed_live_sources=sorted(allowed),runtime_invoked=False)))
