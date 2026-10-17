"""Build distinct14 frozen metadata once on accepted preparation03; no admission main or runtime."""
from pathlib import Path
import ast,copy,datetime,hashlib,json,stat,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
SOURCE='f05bd699af337e44de54584bb334690ec405f994'
SOURCE11='8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15'
CONTROL11B='27780dd5cbc096c26fb353faea7edfde878a4f74'
OUTCOME11B='92de987'
PREP03_EVIDENCE='44e9712'
MERGE='54c8b15df97f881570c6e1d6c50f1f8a4e2a45c8'
PREFIX='docs/plans/puck-cpu-held-qualification-14'
OLD='docs/plans/puck-cpu-held-qualification-11-freeze.json'
CONFIG11='docs/plans/puck-cpu-held-qualification-11.json'
TERMINAL11='docs/reports/puck-cpu-held-qualification-11b'
PREP03='docs/plans/puck-cpu-held-preparation-03'
PREP03_REPORT='docs/reports/puck-cpu-held-preparation-03'
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
PROOF=PREFIX+'-source-evidence'
def load(name):return json.loads((ROOT/name).read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def canonical(value,lf=True):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+('\n' if lf else '')).encode()
def pin(name):
    path=ROOT/name;stamp=path.lstat()
    assert stat.S_ISREG(stamp.st_mode) and stamp.st_nlink==1 and stamp.st_size<=16*1024**2,name
    raw=path.read_bytes();return dict(path=name,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
assert subprocess.run(['git','merge-base','--is-ancestor',MERGE,'HEAD'],cwd=ROOT).returncode==0
assert not (ROOT/(PREFIX+'-freeze.json')).exists()
assert (ROOT/PROOF/'freeze-builder.py').read_bytes()==Path(__file__).read_bytes()
old=load(OLD);config=load(PREFIX+'.json');previous=load(CONFIG11);prep03=load(PREP03+'.json')
assert (ROOT/OLD).read_bytes()==git('show',CONTROL11B+':'+OLD)
# Lesson 1 (admission10-01): the configuration must already be compact canonical bytes.
assert (ROOT/(PREFIX+'.json')).read_bytes()==canonical(config)
assert config['kind']=='puck-cpu-held-runtime-allocation-v14' and config['version']==config['allocation_id']==14
assert set(config)==set(previous) and sorted(k for k in previous if previous[k]!=config[k])==['allocation_id','kind','limits','preparation_acceptance','sources','stage_parent','version']
assert (config['limits']['normal_seconds'],config['limits']['child_hard_seconds'],config['limits']['hard_seconds'])==(360,375,390)
assert config['stage_parent']==prep03['stage_parent']=='/tmp/palimpsest-puck-cpu-held-03' and config['sources']==prep03['sources']
assert all(config['inputs'][k]==prep03['inputs'][k] for k in config['inputs'] if k!='candidate') and len(config['negative_imports'])==32
for row in config['sources']:
    assert pin(row['path'])==row and (ROOT/row['path']).read_bytes()==git('show',SOURCE+':'+row['path'])
acceptance=load(PREP03_REPORT+'/archive-record.json')['acceptance_pins']
assert config['preparation_acceptance']==acceptance and all(pin(r['path'])==r for r in acceptance.values())
qualifier=(ROOT/'scripts/qualify_puck_cpu_held_runtime.py').read_bytes()
literals={t.id:node.value for node in ast.parse(qualifier).body if isinstance(node,ast.Assign) for t in node.targets if isinstance(t,ast.Name)}
hidden=ast.literal_eval(literals['QUALIFY11_HIDDEN_IMPORTS'])
assert hidden==old['hidden_imports']==['networkx','pandas','sklearn','torch.utils._cxx_pytree']
pins={};changed=[]
def add(row):
    if isinstance(row,str):row=pin(row)
    assert pin(row['path'])==row,row['path']
    assert row['path'] not in pins or pins[row['path']]==row,row['path']
    pins[row['path']]=row
allowed={'scripts/qualify_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py',
    'scripts/puck_worker_bootstrap.py','src/palimpsest/puck_dependency_files.py'}
assert len({r['path'] for r in old['pins']})==len(old['pins'])==2463
for row in old['pins']:
    current=pin(row['path'])
    if current!=row:
        assert row['path'] in allowed,row['path']
        archive=dict(row,path=TERMINAL11+'/source/'+row['path'])
        assert (ROOT/archive['path']).read_bytes()==git('show',SOURCE11+':'+row['path'])
        add(archive)
        changed.append(dict(historical_live_path=row['path'],historical_pin=row,archived_pin=archive,current_pin=current))
    add(current)
assert {r['historical_live_path'] for r in changed}==allowed
for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):add(row)
for path in (OLD,PREFIX+'.json',PREFIX+'-admission.py'):add(path)
index=load(TERMINAL11+'/evidence-index.json')
assert index['control_commit']==CONTROL11B and index['source_commit']==SOURCE11 and index['artifact_count']==175 and index['status']=='FAILED_CONSUMED'
assert set(r['archived_path'] for r in index['artifacts'])=={str(p.relative_to(ROOT/TERMINAL11)) for p in (ROOT/TERMINAL11).rglob('*') if p.is_file() and p!=ROOT/TERMINAL11/'evidence-index.json'}
add(TERMINAL11+'/evidence-index.json');add(TERMINAL11+'.md')
assert (ROOT/(TERMINAL11+'.md')).read_bytes()==git('show',OUTCOME11B+':'+TERMINAL11+'.md')
for row in index['artifacts']:
    add(dict(path=TERMINAL11+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256']))
    origin=Path(row['original_path'])
    if origin.is_relative_to(ROOT/'runs') or str(origin).startswith(str(ROOT/'docs/plans/puck-cpu-held-qualification-11')):
        add(dict(path=str(origin.relative_to(ROOT)),size_bytes=row['size_bytes'],sha256=row['sha256']))
assert len(index['control_paths'])==86
for path in index['control_paths']:
    assert (ROOT/path).read_bytes()==git('show',CONTROL11B+':'+path),path
    add(path)
# Accepted preparation03 controls and evidence, Git-bound at its evidence commit.
preparation=[PREP03+'.json',PREP03+'-freeze.json']+git('ls-files','--',PREP03+'-tools',PREP03_REPORT).decode().splitlines()
for path in preparation:
    assert (ROOT/path).read_bytes()==git('show',PREP03_EVIDENCE+':'+path),path
    add(path)
for path in sorted((ROOT/PROOF).rglob('*')):
    if path.is_file():add(str(path.relative_to(ROOT)))
prep_result=load(acceptance['result']['path'])
roots=[dict(device=r['device'],inode=r['inode'],root_index=r['root_index']) for r in prep_result['staged_roots']]
assert roots==[dict(device=55,inode=43194+i,root_index=i) for i in range(4)]
new=copy.deepcopy(old)
for key in ('actual11_admission_invoked_at_freeze','actual11_invoked_at_freeze','qualifications01_02_03_04_05_06_07_08_09_10_failed_consumed','evidence_commit'):
    new.pop(key)
samples=[(r['pid'],r['start_ticks']) for r in old['process_identity_samples']]+[(325632,3798844),(325635,3798844),(325642,3798845)]
preparation02=dict(old['preparation02'],status='ACCEPTED_CONSUMED_BY_RUNTIME11',stage_inspected=False,
    stage_note='retained after runtime11; never read or stat-checked by attempt-14 controls')
new.update(kind='puck-cpu-held-qualification14-frozen-controls-v1',branch='research/puck-cpu-held-qualification-14',
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=SOURCE,implementation_source_commit=SOURCE,
    evidence_commits=dict(merge=MERGE,preparation03=git('rev-parse',PREP03_EVIDENCE).decode().strip(),runtime11_outcome=git('rev-parse',OUTCOME11B).decode().strip(),
        control11b=CONTROL11B),
    actual14_invoked_at_freeze=False,actual14_admission_invoked_at_freeze=False,actual11_invoked_before_freeze=True,
    qualifications01_02_03_04_05_06_07_08_09_10_11_failed_consumed=True,admission11b_admitted_consumed_by_runtime11=True,
    attempt11b=dict(control_commit=CONTROL11B,outcome_commit=git('rev-parse',OUTCOME11B).decode().strip(),status='FAILED_CONSUMED',
        failure='parent normal-return deadline at 180.30s during import mujoco; policy v5 imports returned through Torchvision',
        packet=pin(TERMINAL11+'/evidence-index.json'),report=pin(TERMINAL11+'.md')),
    historical11_missing_receipts=['runs/puck-cpu-held-qualification-11/'+leaf for leaf in ('result.json','baseline-after.json')],
    historical11b_replaced_live_sources=changed,previous11b_freeze=pin(OLD),
    limits=copy.deepcopy(config['limits']),preparation_acceptance=copy.deepcopy(acceptance),
    epoch14_clocks=dict(parent_normal=360,parent_child_hard=375,parent_hard=390,worker_deadline_seconds=360,observer_normal=400,observer_hard=415,
        observer_wrapper=440,observer_outer_term=450,audit_wrapper=145,admission_wrapper=145),
    control_revision=1,
    control_revision_reason='Distinct14 extended-clock controls on accepted preparation03; runtime11 and admission11b consumed; no admission or observer invocation.',
    scope='one separately admitted extended-clock policy-v5 held four-import qualification14 on preparation03; no episode, renderer, operator or scientific study',
    post03_scope='Dated DATA06/C retention only; does not replace fresh14/D full admission',
    helper_absence_scope=dict(historical=19,new=6,total=25,legacy_failure_loop_missing_baselines=6,
        overlapping_legacy_baselines=2,additional_coordinator_reservations='three exclusive files per phase; concrete audit command separate',negative_import_probes=32),
    process_identity_samples=[dict(pid=pid,start_ticks=ticks) for pid,ticks in samples],
    process_scope='eighteen recorded identities only; nonexhaustive non-atomic lifetime observation',
    preparation02=preparation02,
    preparation03=dict(acceptance=acceptance,stage_parent=prep03['stage_parent'],staged_roots=roots,boot_id=BOOT,
        source_review=pin(PREP03_REPORT+'/source-review-04.md'),archive_record=pin(PREP03_REPORT+'/archive-record.json'),
        stage_guard='before every one-shot step: boot_id equals the preparation boot and the stage parent, inputs and four roots are tmpfs directories, mode 0700, owned by the operator, with (st_dev,st_ino) equal to staged_roots'),
    pins=[pins[name] for name in sorted(pins)])
assert len(new['process_identity_samples'])==18 and new['observer_invocations']==1 and new['implicit_retry'] is False
oldsha=pin(CONFIG11)['sha256'];newsha=pin(PREFIX+'.json')['sha256']
def commands(value):
    if isinstance(value,str):
        value=value.replace(CONFIG11,PREFIX+'.json').replace('docs/plans/puck-cpu-held-qualification-11-admission.py',PREFIX+'-admission.py')
        value=value.replace('/tmp/palimpsest-puck-cpu-held-qualification-11b-audit-01.json','/tmp/palimpsest-puck-cpu-held-qualification-14-audit-01.json')
        return value.replace('runs/puck-cpu-held-qualification-11-external-cli','runs/puck-cpu-held-qualification-14-external-cli').replace(oldsha,newsha)
    if isinstance(value,list):return [commands(v) for v in value]
    if isinstance(value,dict):return {k:commands(v) for k,v in value.items()}
    raise TypeError(type(value).__name__)
new['commands']=commands(old['commands'])
text=json.dumps(new['commands'])
assert 'qualification-11' not in text and '11b' not in text and oldsha not in text
assert new['commands']['auditor_output']=='/tmp/palimpsest-puck-cpu-held-qualification-14-audit-01.json'
raw=(json.dumps(new,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();assert len(raw)<=1024**2
with (ROOT/(PREFIX+'-freeze.json')).open('xb') as stream:stream.write(raw)
print(json.dumps(dict(path=PREFIX+'-freeze.json',size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
    pin_count=len(pins),pinned_bytes=sum(r['size_bytes'] for r in pins.values()),retained_11b_pins=len(old['pins']),
    changed_live_sources=len(changed),preparation03_pins=len(preparation)+1,runs_pins=sum(name.startswith('runs/') for name in pins),
    admission_invoked=False,runtime_invoked=False,stages_touched=False)))
