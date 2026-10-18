"""Build distinct10 frozen metadata once; no admission main or runtime."""
from pathlib import Path
import copy,datetime,hashlib,json,stat,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
SOURCE='e723db037ed1f790c2618798d59f56913054754f'
IMPLEMENTATION='cbe48b339f4839ec4d2b5ef153d0dc0820be712e'
PREFIX='docs/plans/puck-cpu-held-qualification-10'
OLD='docs/plans/puck-cpu-held-qualification-09-freeze.json'
PROOF=PREFIX+'-source-evidence'
def load(name):return json.loads((ROOT/name).read_bytes())
def pin(name):
    path=ROOT/name;stamp=path.lstat()
    assert stat.S_ISREG(stamp.st_mode) and stamp.st_nlink==1 and stamp.st_size<=16*1024**2,name
    raw=path.read_bytes();return dict(path=name,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
assert subprocess.run(['git','merge-base','--is-ancestor',SOURCE,'HEAD'],cwd=ROOT).returncode==0
assert not (ROOT/(PREFIX+'-freeze.json')).exists()
assert (ROOT/PROOF/'freeze-builder.py').read_bytes()==Path(__file__).read_bytes()
old=load(OLD);config=load(PREFIX+'.json');previous=load('docs/plans/puck-cpu-held-qualification-09.json')
assert config['kind']=='puck-cpu-held-runtime-allocation-v10' and config['version']==config['allocation_id']==10
assert set(config)==set(previous) and config['inputs']==previous['inputs'] and config['preparation_acceptance']==previous['preparation_acceptance']
for name in ('root','stage_parent','interpreter','environment','limits','expected_versions','negative_imports','claims'):
    assert config[name]==previous[name],name
changed_config=[a['path'] for a,b in zip(previous['sources'],config['sources']) if a!=b]
assert changed_config==['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py','src/palimpsest/puck_runtime_qualification.py']
for row in config['sources']:
    assert pin(row['path'])==row
    raw=(ROOT/row['path']).read_bytes()
    assert raw==subprocess.check_output(['git','show',SOURCE+':'+row['path']],cwd=ROOT)
    assert raw==subprocess.check_output(['git','show',IMPLEMENTATION+':'+row['path']],cwd=ROOT)
pins={};changed=[]
def add(row):
    if isinstance(row,str):row=pin(row)
    assert pin(row['path'])==row,row['path']
    assert row['path'] not in pins or pins[row['path']]==row,row['path']
    pins[row['path']]=row
allowed={'scripts/qualify_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_held_runtime.py',
    'scripts/observe_puck_cpu_held_allocation.py','scripts/puck_worker_bootstrap.py',
    'src/palimpsest/puck_runtime_qualification.py'}
for row in old['pins']:
    current=pin(row['path'])
    if current!=row:
        assert row['path'] in allowed,row['path']
        archive=dict(row,path='docs/reports/puck-cpu-held-qualification-09/source/'+row['path'])
        add(archive)
        changed.append(dict(historical_live_path=row['path'],historical_pin=row,archived_pin=archive,current_pin=current))
    add(current)
assert {r['historical_live_path'] for r in changed}==allowed
for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):add(row)
for path in (OLD,PREFIX+'.json',PREFIX+'-admission.py',PREFIX+'-review.md'):add(path)
for parent in ('docs/reports/puck-cpu-held-qualification-09',
    'docs/plans/puck-cpu-guard-contract-v4','docs/plans/puck-cpu-q4-qualification-epoch10'):
    index=load(parent+'/evidence-index.json');add(parent+'/evidence-index.json');add(parent+'.md')
    if parent.startswith('docs/plans/'):
        add('docs/reports/'+parent.rsplit('/',1)[1]+'.md')
    for row in index['artifacts']:
        add(dict(path=parent+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256']))
        if parent=='docs/reports/puck-cpu-held-qualification-09':
            origin=Path(row['original_path'])
            if origin.is_relative_to(ROOT/'runs') or str(origin).startswith(str(ROOT/'docs/plans/puck-cpu-held-qualification-09')):
                add(dict(path=str(origin.relative_to(ROOT)),size_bytes=row['size_bytes'],sha256=row['sha256']))
for path in sorted((ROOT/PROOF).rglob('*')):
    if path.is_file():add(str(path.relative_to(ROOT)))
new=copy.deepcopy(old)
for key in ('actual08_inputs_unchanged','actual09_admission_invoked_at_freeze','actual09_invoked_at_freeze',
    'qualifications01_02_03_04_05_06_07_08_failed_consumed','historical08_replaced_live_sources',
    'previous08_freeze','control_revision','control_revision_reason'):
    new.pop(key,None)
samples=[(3569912,53431366),(3569913,53431366),(3569914,53431367),
    (3798021,53913806),(3798022,53913806),(3798023,53913807),
    (3996069,54384185),(3996070,54384185),(3996071,54384186),
    (104005,55289090),(104006,55289091),(104007,55289092)]
new.update(kind='puck-cpu-held-qualification10-frozen-controls-v1',branch='research/puck-cpu-held-qualification-10',
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=SOURCE,
    implementation_source_commit=IMPLEMENTATION,actual10_invoked_at_freeze=False,actual10_admission_invoked_at_freeze=False,
    actual09_invoked_before_freeze=True,actual09_inputs_unchanged=True,
    qualifications01_02_03_04_05_06_07_08_09_failed_consumed=True,
    historical09_replaced_live_sources=changed,previous09_freeze=pin(OLD),control_revision=1,
    control_revision_reason='Distinct10 q4 controls and genuine consumed09 evidence; no admission or observer invocation.',
    scope='one separately admitted q4 held four-import qualification10; no episode, renderer, operator or scientific study',
    post03_scope='Dated DATA06/C retention only; does not replace fresh10/D full admission',
    historical09_missing_receipts=['runs/puck-cpu-held-qualification-09/'+leaf for leaf in ('result.json','baseline-after.json')],
    helper_absence_scope=dict(historical=16,new=6,total=22,legacy_failure_loop_missing_baselines=6,
        overlapping_legacy_baselines=2,additional_coordinator_reservations='three exclusive files per phase; concrete audit command separate',negative_import_probes=19),
    process_identity_samples=[dict(pid=pid,start_ticks=ticks) for pid,ticks in samples],
    process_scope='twelve recorded identities only; nonexhaustive non-atomic lifetime observation',
    source_support=pin('docs/plans/puck-cpu-q4-qualification-epoch10/evidence-index.json'),
    guard_contract_support=pin('docs/plans/puck-cpu-guard-contract-v4/evidence-index.json'),
    pins=[pins[name] for name in sorted(pins)])
assert new['limits']==config['limits']==old['limits'] and new['negative_imports']==config['negative_imports']==old['negative_imports']
assert len(new['changed_preparation_source_paths'])==5 and new['observer_invocations']==1 and new['implicit_retry'] is False
oldsha=pin('docs/plans/puck-cpu-held-qualification-09.json')['sha256'];newsha=pin(PREFIX+'.json')['sha256']
def commands(value):
    if isinstance(value,str):return value.replace('puck-cpu-held-qualification-09','puck-cpu-held-qualification-10').replace(oldsha,newsha)
    if isinstance(value,list):return [commands(v) for v in value]
    if isinstance(value,dict):return {k:commands(v) for k,v in value.items()}
    raise TypeError(type(value).__name__)
new['commands']=commands(old['commands'])
raw=(json.dumps(new,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();assert len(raw)<=1024**2
with (ROOT/(PREFIX+'-freeze.json')).open('xb') as stream:stream.write(raw)
print(json.dumps(dict(path=PREFIX+'-freeze.json',size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
    pin_count=len(pins),pinned_bytes=sum(r['size_bytes'] for r in pins.values()),
    changed_live_sources=len(changed),changed_config_sources=len(changed_config),admission_invoked=False,runtime_invoked=False)))
