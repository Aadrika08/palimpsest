"""Build distinct11b frozen metadata once on accepted preparation02; no admission main or runtime."""
from pathlib import Path
import ast,copy,datetime,hashlib,json,stat,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
SOURCE='8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15'
EVIDENCE='facc2a7'
SOURCE10='e723db037ed1f790c2618798d59f56913054754f'
CONTROL10='796359a099131157b5b91db38f14784628d5d7c5'
OLD11='d83dab3c92387c80e81af528fea25dd3f8931598'
REVIEW11='0b9c67f5fbf70f7bd3af4277ae9a10fb9b60a7d3'
PREFIX='docs/plans/puck-cpu-held-qualification-11'
OLD='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/freeze.json'
ORIGINAL10='docs/plans/puck-cpu-held-qualification-10-freeze.json'
ADMITTED10='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/configuration.json'
TERMINAL10='docs/reports/puck-cpu-held-qualification-10'
PREP02='docs/plans/puck-cpu-held-preparation-02'
PREP02_REPORT='docs/reports/puck-cpu-held-preparation-02'
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
PROOF=PREFIX+'-source-evidence'
NEW11=['backports_abc','fx2trt_oss','hypothesis','onnx','onnx_tf','onnxruntime','tabulate',
    'tensorflow','tensorrt','torch2trt','tree','tvm','xarray']
def load(name):return json.loads((ROOT/name).read_bytes())
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def canonical(value,lf=True):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+('\n' if lf else '')).encode()
def pin(name):
    path=ROOT/name;stamp=path.lstat()
    assert stat.S_ISREG(stamp.st_mode) and stamp.st_nlink==1 and stamp.st_size<=16*1024**2,name
    raw=path.read_bytes();return dict(path=name,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
assert subprocess.run(['git','merge-base','--is-ancestor',EVIDENCE,'HEAD'],cwd=ROOT).returncode==0
assert not (ROOT/(PREFIX+'-freeze.json')).exists()
assert (ROOT/PROOF/'freeze-builder.py').read_bytes()==Path(__file__).read_bytes()
old=load(OLD);original=load(ORIGINAL10);config=load(PREFIX+'.json');previous=load(ADMITTED10);prep02=load(PREP02+'.json')
# Lesson 1 (admission10-01): the configuration must already be compact canonical bytes.
assert (ROOT/(PREFIX+'.json')).read_bytes()==canonical(config)
assert config['kind']=='puck-cpu-held-runtime-allocation-v11' and config['version']==config['allocation_id']==11
assert set(config)==set(previous) and config['inputs']==previous['inputs']
for name in ('root','interpreter','environment','limits','expected_versions','claims','phase'):
    assert config[name]==previous[name],name
assert config['stage_parent']==prep02['stage_parent']=='/tmp/palimpsest-puck-cpu-held-02' and config['sources']==prep02['sources']
assert config['negative_imports']==sorted(previous['negative_imports']+NEW11) and len(config['negative_imports'])==32
changed_config=[a['path'] for a,b in zip(previous['sources'],config['sources']) if a!=b]
assert changed_config==['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py','src/palimpsest/puck_runtime_qualification.py']
for row in config['sources']:
    assert pin(row['path'])==row
    assert (ROOT/row['path']).read_bytes()==git('show',SOURCE+':'+row['path'])
acceptance=load(PREP02_REPORT+'/archive-record.json')['acceptance_pins']
assert config['preparation_acceptance']==acceptance and all(pin(r['path'])==r for r in acceptance.values())
qualifier=(ROOT/'scripts/qualify_puck_cpu_held_runtime.py').read_bytes()
literals={t.id:node.value for node in ast.parse(qualifier).body if isinstance(node,ast.Assign) for t in node.targets if isinstance(t,ast.Name)}
hidden=ast.literal_eval(literals['QUALIFY11_HIDDEN_IMPORTS'])
assert hidden==['networkx','pandas','sklearn','torch.utils._cxx_pytree']
pins={};changed=[]
def add(row):
    if isinstance(row,str):row=pin(row)
    assert pin(row['path'])==row,row['path']
    assert row['path'] not in pins or pins[row['path']]==row,row['path']
    pins[row['path']]=row
allowed={'scripts/qualify_puck_cpu_held_runtime.py','scripts/audit_puck_cpu_held_runtime.py',
    'scripts/observe_puck_cpu_held_allocation.py','scripts/puck_worker_bootstrap.py',
    'src/palimpsest/puck_runtime_qualification.py'}
roster={r['path']:r for r in old['pins']}
assert len(roster)==len(old['pins'])==2150 and all(roster[r['path']]==r for r in original['pins'])
for row in old['pins']:
    current=pin(row['path'])
    if current!=row:
        assert row['path'] in allowed,row['path']
        archive=dict(row,path=TERMINAL10+'/source/'+row['path'])
        assert (ROOT/archive['path']).read_bytes()==git('show',SOURCE10+':'+row['path'])
        add(archive)
        changed.append(dict(historical_live_path=row['path'],historical_pin=row,archived_pin=archive,current_pin=current))
    add(current)
assert {r['historical_live_path'] for r in changed}==allowed
for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):add(row)
for path in (OLD,ORIGINAL10,PREFIX+'.json',PREFIX+'-admission.py',PREFIX+'-independent-controls-review-01.md'):add(path)
assert (ROOT/(PREFIX+'-independent-controls-review-01.md')).read_bytes()==git('show',REVIEW11+':'+PREFIX+'-independent-controls-review-01.md')
index=load(TERMINAL10+'/evidence-index.json')
assert index['control_commit']==CONTROL10 and index['source_commit']==SOURCE10 and index['artifact_count']==165
assert set(r['archived_path'] for r in index['artifacts'])=={str(p.relative_to(ROOT/TERMINAL10)) for p in (ROOT/TERMINAL10).rglob('*') if p.is_file() and p!=ROOT/TERMINAL10/'evidence-index.json'}
add(TERMINAL10+'/evidence-index.json');add(TERMINAL10+'.md')
for row in index['artifacts']:
    add(dict(path=TERMINAL10+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256']))
    origin=Path(row['original_path'])
    if origin.is_relative_to(ROOT/'runs') or str(origin).startswith(str(ROOT/'docs/plans/puck-cpu-held-qualification-10')):
        add(dict(path=str(origin.relative_to(ROOT)),size_bytes=row['size_bytes'],sha256=row['sha256']))
assert len(index['control_paths'])==74
for path in index['control_paths']:
    assert (ROOT/path).read_bytes()==git('show',CONTROL10+':'+path),path
    add(path)
contract=['docs/plans/puck-cpu-optional-import-contract-v2.md']+sorted(str(p.relative_to(ROOT)) for p in (ROOT/'docs/reports/puck-cpu-optional-import-contract-v2').rglob('*') if p.is_file())
assert len(contract)==25
for path in contract:
    assert (ROOT/path).read_bytes()==git('show',SOURCE+':'+path),path
    add(path)
# Accepted preparation02 controls and evidence, Git-bound at the evidence commit. Its other run
# files are checked by the historical snapshot instead of pins, so admission raw roles stay unchanged.
preparation=[PREP02+'.json',PREP02+'-freeze.json']+git('ls-files','--',PREP02+'-tools',PREP02_REPORT).decode().splitlines()
assert len(preparation)==25
for path in preparation:
    assert (ROOT/path).read_bytes()==git('show',EVIDENCE+':'+path),path
    add(path)
for path in sorted((ROOT/PROOF).rglob('*')):
    if path.is_file():add(str(path.relative_to(ROOT)))
unexecuted=[]
for path in git('diff','--name-only','1126b710a372a82e932d08073cfc6c13308db437',OLD11).decode().splitlines():
    raw=git('show',OLD11+':'+path);unexecuted.append(dict(path=path,size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
assert len(unexecuted)==73
prep_result=load(acceptance['result']['path'])
roots=[dict(device=r['device'],inode=r['inode'],root_index=r['root_index']) for r in prep_result['staged_roots']]
new=copy.deepcopy(old)
for key in ('actual09_inputs_unchanged','actual10_admission_invoked_at_freeze','actual10_invoked_at_freeze',
    'admission01_failed_consumed','admission01_failure_packet','admission02_invoked_at_freeze','admission_check_id',
    'canonical_only_configuration_delta','control_revision','control_revision_reason','historical09_replaced_live_sources',
    'previous09_freeze','previous10_control_commit','previous10_freeze','qualifications01_02_03_04_05_06_07_08_09_failed_consumed'):
    new.pop(key)
samples=[(3569912,53431366),(3569913,53431366),(3569914,53431367),
    (3798021,53913806),(3798022,53913806),(3798023,53913807),
    (3996069,54384185),(3996070,54384185),(3996071,54384186),
    (104005,55289090),(104006,55289091),(104007,55289092),
    (409732,56248873),(409733,56248874),(409734,56248875)]
new.update(kind='puck-cpu-held-qualification11b-frozen-controls-v1',branch='research/puck-cpu-held-qualification-11b',
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=SOURCE,
    implementation_source_commit=SOURCE,evidence_commit=git('rev-parse',EVIDENCE).decode().strip(),
    actual11_invoked_at_freeze=False,actual11_admission_invoked_at_freeze=False,
    actual10_invoked_before_freeze=True,actual10_inputs_unchanged=True,
    qualifications01_02_03_04_05_06_07_08_09_10_failed_consumed=True,
    admission10_01_failed_consumed=True,admission10_02_admitted_consumed_by_runtime10=True,
    admission10_packets=dict(admission01=pin('docs/reports/puck-cpu-held-qualification-10-admission-01/evidence-index.json'),
        terminal10=pin(TERMINAL10+'/evidence-index.json')),
    historical10_replaced_live_sources=changed,previous10_freeze=pin(ORIGINAL10),previous10_admission02_freeze=pin(OLD),
    previous10_control_commit=CONTROL10,control_revision=1,
    control_revision_reason='Distinct11b policy-v5 controls on accepted preparation02; d83dab3 reviewed NO-GO and never invoked; no admission or observer invocation.',
    scope='one separately admitted policy-v5 held four-import qualification11 (packet 11b) on preparation02; no episode, renderer, operator or scientific study',
    post03_scope='Dated DATA06/C retention only; does not replace fresh11b/D full admission',
    historical10_missing_receipts=['runs/puck-cpu-held-qualification-10/baseline-after.json'],
    helper_absence_scope=dict(historical=17,new=6,total=23,legacy_failure_loop_missing_baselines=6,
        overlapping_legacy_baselines=2,additional_coordinator_reservations='three exclusive files per phase; concrete audit command separate',negative_import_probes=32),
    negative_imports=config['negative_imports'],missing_import_policy='v5',hidden_imports=hidden,
    hidden_import_scope='Present-but-unavailable names fixed by qualifier source, not configuration; enforced by the worker bootstrap; admission probes only the 32 absent names',
    process_identity_samples=[dict(pid=pid,start_ticks=ticks) for pid,ticks in samples],
    process_scope='fifteen recorded identities only; nonexhaustive non-atomic lifetime observation',
    source_support=pin('docs/plans/puck-cpu-optional-import-contract-v2.md'),
    preparation02=dict(acceptance=acceptance,stage_parent=prep02['stage_parent'],staged_roots=roots,boot_id=BOOT,
        source_review=pin(PREP02_REPORT+'/source-review-02.md'),archive_record=pin(PREP02_REPORT+'/archive-record.json'),
        stage_guard='before every one-shot step: boot_id equals the preparation boot and the stage parent, inputs and four roots are tmpfs directories, mode 0700, owned by the operator, with (st_dev,st_ino) equal to staged_roots'),
    preparation01_superseded=dict(configuration=pin('docs/plans/puck-cpu-held-preparation-01.json'),result=pin('runs/puck-cpu-held-preparation-01/result.json'),
        status='ACCEPTED_SUPERSEDED_STAGE_LOST',required=False),
    attempt11_d83dab3=dict(control_commit=OLD11,review_commit=REVIEW11,branch='research/puck-cpu-held-qualification-11',
        status='NO_GO_NEVER_INVOKED',review=pin(PREFIX+'-independent-controls-review-01.md'),git_files=unexecuted,
        scope='Git-object pins of the unexecuted packet; its paths are reused by the 11b packet with new bytes'),
    pins=[pins[name] for name in sorted(pins)])
assert new['limits']==old['limits'] and len(new['changed_preparation_source_paths'])==5
assert new['observer_invocations']==1 and new['implicit_retry'] is False
oldsha=pin(ADMITTED10)['sha256'];newsha=pin(PREFIX+'.json')['sha256']
def commands(value):
    if isinstance(value,str):
        value=value.replace(ADMITTED10,PREFIX+'.json').replace('docs/plans/puck-cpu-held-qualification-10-admission-amendment-02/admission.py',PREFIX+'-admission.py')
        value=value.replace('/tmp/palimpsest-puck-cpu-held-qualification-10-audit-01.json','/tmp/palimpsest-puck-cpu-held-qualification-11b-audit-01.json')
        return value.replace('puck-cpu-held-qualification-10','puck-cpu-held-qualification-11').replace(oldsha,newsha)
    if isinstance(value,list):return [commands(v) for v in value]
    if isinstance(value,dict):return {k:commands(v) for k,v in value.items()}
    raise TypeError(type(value).__name__)
new['commands']=commands(old['commands'])
assert 'qualification-10' not in json.dumps(new['commands']) and oldsha not in json.dumps(new['commands'])
assert new['commands']['auditor_output']=='/tmp/palimpsest-puck-cpu-held-qualification-11b-audit-01.json'
raw=(json.dumps(new,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();assert len(raw)<=1024**2
with (ROOT/(PREFIX+'-freeze.json')).open('xb') as stream:stream.write(raw)
print(json.dumps(dict(path=PREFIX+'-freeze.json',size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),
    pin_count=len(pins),pinned_bytes=sum(r['size_bytes'] for r in pins.values()),retained_amendment02_pins=len(old['pins']),
    changed_live_sources=len(changed),changed_config_sources=len(changed_config),preparation02_pins=len(preparation)+1,
    unexecuted_d83dab3_git_files=len(unexecuted),runs_pins=sum(name.startswith('runs/') for name in pins),
    admission_invoked=False,runtime_invoked=False,stage_touched=False)))
