"""Build the allocation-16 frozen metadata once on accepted preparation04; no admission main, observer or auditor.

Starts from the reviewed-GO attempt-14 freeze. Ten live sources that changed since f05bd69 are bound by
the runtime14 packet's source/ copies. By the user's decision, the consumed docs/reports packets of
attempts 05, 07-10, admission10-01, 11b and runtime14 are bound through their committed evidence-index
hashes instead of every archived file (each index is verified to list every packet file byte-identically
here), keeping the admission's Held entries and bytes well inside its 40,000-entry and 2 GiB ceilings;
every file the history checks read stays individually pinned. Adds the runtime14 outcome and runs/
originals, the attempt-14 controls (Git-bound at eb34d5c), characterization-04 and preparation04 controls
and evidence, candidate 02, the allocation-16 configuration, admission and source evidence.
"""
from pathlib import Path
import copy,datetime,hashlib,importlib.util,json,stat,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PREFIX='docs/plans/puck-cpu-held-episode-16'
PROOF=PREFIX+'-source-evidence'
OLD='docs/plans/puck-cpu-held-qualification-14-freeze.json'
CONFIG14='docs/plans/puck-cpu-held-qualification-14.json'
P14='docs/reports/puck-cpu-held-qualification-14'
CONTROL14='eb34d5c2a66730c248b00229c17ce84e197b3d68'
MERGE14='54c8b15df97f881570c6e1d6c50f1f8a4e2a45c8'
MERGE16='75df4dba55e435eee84d8a0f34b33967b0ac86bf'
OUTCOME14='4fd4f68de5f0350c22ac7d5e5c2432b28525bc64'
PREP04_EVIDENCE='4b22f2b'
SOURCE='cbda0d992c12320e2c9bd8a188f89d2c73d9f77e'
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
BOUND_PACKETS=['docs/reports/puck-cpu-held-qualification-'+n for n in ('05','07','08','09','10','10-admission-01','11b','14')]
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def load(name):return json.loads((ROOT/name).read_bytes())
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(name):
    path=ROOT/name;stamp=path.lstat()
    assert stat.S_ISREG(stamp.st_mode) and stamp.st_nlink==1 and stamp.st_size<=16*1024**2,name
    raw=path.read_bytes();return dict(path=name,size_bytes=len(raw),sha256=sha(raw))
assert git('rev-parse','HEAD').decode().strip()!=MERGE16 and subprocess.run(['git','merge-base','--is-ancestor',MERGE16,'HEAD'],cwd=ROOT).returncode==0
assert git('rev-parse','4fd4f68').decode().strip()==OUTCOME14
assert not (ROOT/(PREFIX+'-freeze.json')).exists() and (ROOT/PROOF/'freeze-builder.py').read_bytes()==Path(__file__).read_bytes()
spec=importlib.util.spec_from_file_location('freeze16_admission',ROOT/(PREFIX+'-admission.py'))
admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
old=load(OLD);config=load(PREFIX+'.json');assert (ROOT/OLD).read_bytes()==git('show',CONTROL14+':'+OLD)
assert len(old['pins'])==len({r['path'] for r in old['pins']})==2768
# The history checks read these individually; they stay pinned even inside an index-bound packet.
history={*admission.HISTORICAL07_JSON,*admission.HISTORICAL08_JSON,*admission.HISTORICAL09_JSON,*admission.HISTORICAL10_JSON,
    *admission.HISTORICAL11_JSON,*admission.HISTORICAL14_JSON,*admission.ADMISSION01_PINS,*admission.ADMISSION02_PINS,
    *admission.ADMISSION11B_PINS,*admission.ADMISSION14_PINS,*admission.CHARACTERIZATION04_JSON,admission.RETIREMENT,
    admission.UNEXECUTED11['review']['path']}
indexes={}
for packet in BOUND_PACKETS:
    index=load(packet+'/evidence-index.json');rows={r['archived_path']:r for r in index['artifacts']}
    files={str(p.relative_to(ROOT/packet)) for p in (ROOT/packet).rglob('*') if p.is_file()}-{'evidence-index.json'}
    assert set(rows)==files and len(rows)==len(index['artifacts']),packet
    for name,row in rows.items():assert pin(packet+'/'+name)=={'path':packet+'/'+name,'size_bytes':row['size_bytes'],'sha256':row['sha256']},packet+'/'+name
    indexes[packet]=dict(index=pin(packet+'/evidence-index.json'),artifacts=len(rows),artifact_bytes=sum(r['size_bytes'] for r in rows.values()),
        report=pin(packet+'.md') if (ROOT/(packet+'.md')).exists() else None)
def bound(path):return next((p for p in BOUND_PACKETS if path.startswith(p+'/')),None)
pins={};replaced=[];index_bound=[]
def add(row):
    if isinstance(row,str):row=pin(row)
    assert pin(row['path'])==row,row['path']
    assert row['path'] not in pins or pins[row['path']]==row,row['path']
    pins[row['path']]=row
for row in old['pins']:
    path=row['path'];packet=bound(path)
    if packet and path not in history and path!=packet+'/evidence-index.json':
        index=load(packet+'/evidence-index.json');listed={r['archived_path']:r for r in index['artifacts']}[path[len(packet)+1:]]
        assert (listed['size_bytes'],listed['sha256'])==(row['size_bytes'],row['sha256']),path
        index_bound.append(path);continue
    current=pin(path)
    if current!=row:
        archived=P14+'/source/'+path;listed={r['archived_path']:r for r in load(P14+'/evidence-index.json')['artifacts']}['source/'+path]
        assert (listed['size_bytes'],listed['sha256'])==(row['size_bytes'],row['sha256'])
        assert (ROOT/archived).read_bytes()==git('show','f05bd699af337e44de54584bb334690ec405f994:'+path),path
        replaced.append(dict(historical_live_path=path,historical_pin=row,archived_path=archived,bound_by=P14+'/evidence-index.json',current_pin=current))
    add(current)
assert len(replaced)==10
for packet,value in indexes.items():
    add(value['index'])
    if value['report']:add(value['report'])
for path in sorted(history):add(path)
# Runtime14 outcome: the packet is index-bound; its runs/ originals are pinned individually.
index14=load(P14+'/evidence-index.json');assert index14['control_commit']==CONTROL14 and index14['status']=='AUDIT_PASS_IMPORT_ROUTE_ONLY'
runtime14_runs=[]
for row in index14['artifacts']:
    origin=Path(row['original_path'])
    if origin.is_relative_to(ROOT/'runs'):
        name=str(origin.relative_to(ROOT));add(dict(path=name,size_bytes=row['size_bytes'],sha256=row['sha256']));runtime14_runs.append(name)
assert len(runtime14_runs)==24
controls14=git('diff','--name-only',MERGE14,CONTROL14).decode().splitlines()
assert len(controls14)==78
for path in controls14:assert (ROOT/path).read_bytes()==git('show',CONTROL14+':'+path),path;add(path)
for path in (OLD,CONFIG14,P14+'.md'):add(path)
# Characterization-04 and preparation04 controls and evidence, plus candidate 02, Git-bound at the preparation04 evidence commit.
evidence=git('ls-files','--','docs/plans/puck-cpu-runtime-characterization-04.json','docs/plans/puck-cpu-runtime-characterization-04-freeze.json',
    'docs/plans/puck-cpu-runtime-characterization-04-tools','docs/reports/puck-cpu-characterization-04','docs/reports/puck-cpu-characterization-04-records',
    'docs/plans/puck-cpu-held-preparation-04.json','docs/plans/puck-cpu-held-preparation-04-freeze.json','docs/plans/puck-cpu-held-preparation-04-tools',
    'docs/reports/puck-cpu-held-preparation-04','docs/plans/puck-cpu-episode-import-profile-candidate-02.json').decode().splitlines()
for path in evidence:assert (ROOT/path).read_bytes()==git('show',PREP04_EVIDENCE+':'+path),path;add(path)
for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):add(row)
for path in (PREFIX+'.json',PREFIX+'-admission.py'):add(path)
for path in sorted((ROOT/PROOF).rglob('*')):
    if path.is_file():add(str(path.relative_to(ROOT)))
prep_result=load(config['preparation_acceptance']['result']['path'])
roots=[dict(device=r['device'],inode=r['inode'],root_index=r['root_index']) for r in prep_result['staged_roots']]
assert roots==admission.PREP_ROOTS
new=copy.deepcopy(old)
for key in ('actual14_admission_invoked_at_freeze','actual14_invoked_at_freeze','epoch14_clocks','current_candidate','changed_preparation_source_paths',
        'missing_import_policy','unchanged_non_candidate_input_pins','post03_scope','hidden_import_scope'):new.pop(key)
run_ids=config['run_ids'];python='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
config_sha=pin(PREFIX+'.json')['sha256']
new.update(kind='puck-cpu-held-episode16-frozen-controls-v1',branch='research/puck-cpu-held-episode-16',
    created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=SOURCE,implementation_source_commit=SOURCE,
    evidence_commits=dict(merge=MERGE16,runtime14_outcome=OUTCOME14,control14=CONTROL14,preparation04=git('rev-parse',PREP04_EVIDENCE).decode().strip(),
        characterization04='5dc2010d9c429d860d80f505585a012d8cf92493',candidate02='e5551ee'),
    actual16_invoked_at_freeze=False,actual16_admission_invoked_at_freeze=False,actual14_invoked_before_freeze=True,
    runtime14_accepted_import_route_consumed=True,admission14_admitted_consumed_by_runtime14=True,
    runtime14=dict(control_commit=CONTROL14,outcome_commit=OUTCOME14,status='AUDIT_PASS_IMPORT_ROUTE_ONLY',
        outcome='imports_completed in 202.54 s; v14 audit PASS; independent outcome review PASS_IMPORT_ROUTE_OUTCOME_RECORD_ONLY',
        packet=pin(P14+'/evidence-index.json'),report=pin(P14+'.md'),runs_originals=len(runtime14_runs)),
    historical14_replaced_live_sources=replaced,previous14_freeze=pin(OLD),
    evidence_index_binding=dict(decision='user decision: bind consumed history through committed evidence-index hashes when the admission projection is tight; ceiling stays 40,000',
        packets=indexes,index_bound_pins=len(index_bound),individually_pinned_history_files=len(history)),
    limits=copy.deepcopy(config['limits']),preparation_acceptance=copy.deepcopy(config['preparation_acceptance']),
    negative_imports=list(config['negative_imports']),hidden_imports=list(config['hidden_imports']),run_ids=dict(run_ids),
    episode=dict(seed=7,ticks=48,actions=[[0,1.0,0.0],[24,1.0,0.5]],renderer='Mesa llvmpipe EGL as frozen in run_puck_cpu_held_episode.RENDERER',
        egl_vendor=load('docs/plans/puck-cpu-characterization-native-metadata-06.json')['egl_vendor']),
    episode16_clocks=dict(parent_normal=1200,parent_child_hard=1215,parent_hard=1230,worker_seconds=600,observer_normal=1260,observer_hard=1275,
        observer_cleanup=5,observer_wrapper=1300,observer_outer_term=1310,observer_tool_bound=1330,auditor_deadline=300,auditor_alarm=310,
        audit_wrapper=330,audit_outer_term=340,audit_tool_bound=360,admission_wrapper=145,admission_outer_term=155,admission_tool_bound=170),
    control_revision=1,
    control_revision_reason='Distinct allocation-16 held-episode controls on accepted preparation04; runtime14 accepted and consumed; no admission or observer invocation.',
    scope='one separately admitted held public manual episode (allocation 16) on preparation04; no operator, collection, study or release authority',
    helper_absence_scope=dict(historical=19,new=6,total=25,negative_import_probes=42),
    process_identity_samples=[dict(pid=pid,start_ticks=ticks) for pid,ticks in admission.PROCESS_IDENTITIES],
    process_scope='twenty-one recorded identities only; nonexhaustive non-atomic lifetime observation',
    preparation02=dict(old['preparation02'],status='ACCEPTED_CONSUMED_BY_RUNTIME11_STAGE_RETIRED',stage_inspected=False,
        stage_note='retired by retire-consumed-stages.py after a recorded identity and content census',retirement=pin(admission.RETIREMENT)),
    preparation03=dict(old['preparation03'],status='ACCEPTED_CONSUMED_BY_RUNTIME14_STAGE_RETIRED',
        stage_note='retired by retire-consumed-stages.py after a recorded identity and content census',retirement=pin(admission.RETIREMENT)),
    characterization04=dict(status='ACCEPTED_OBSERVATION',configuration=pin('docs/plans/puck-cpu-runtime-characterization-04.json'),
        archive_index=pin('docs/reports/puck-cpu-characterization-04/evidence-index.json'),archive_record=pin('docs/reports/puck-cpu-characterization-04-records/archive-record.json')),
    preparation04=dict(acceptance=copy.deepcopy(config['preparation_acceptance']),stage_parent=config['stage_parent'],staged_roots=roots,boot_id=BOOT,
        archive_record=pin('docs/reports/puck-cpu-held-preparation-04/archive-record.json'),
        stage_guard='before every one-shot step: boot_id equals the preparation boot and the stage parent, inputs and four roots are tmpfs directories, mode 0700, owned by the operator, with (st_dev,st_ino) equal to staged_roots'),
    commands=dict(admission=[python,'-I','-S','-B',str(ROOT/(PREFIX+'-admission.py'))],
        observer=[python,'-I','-S','-B',str(ROOT/'scripts/observe_puck_cpu_held_allocation.py'),'--configuration',str(ROOT/(PREFIX+'.json')),'--sha256',config_sha],
        auditor_prefix=[python,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_episode.py'),'--configuration',str(ROOT/(PREFIX+'.json')),'--sha256',config_sha,
            '--transport',str(ROOT/'runs/puck-cpu-held-episode-16-external-cli-transport.json'),'--transport-sha256'],
        auditor_output='/tmp/palimpsest-puck-cpu-held-episode-16-audit-01.json'),
    audit_required_kind='puck-cpu-held-episode-independent-audit-v1',
    pins=[pins[name] for name in sorted(pins)])
for key in ('preparation_acceptance',):assert all(pins[r['path']]==r for r in new[key].values())
assert new['observer_invocations']==1 and new['implicit_retry'] is False and len(new['process_identity_samples'])==21
text=json.dumps(new['commands'])
assert 'qualification-14' not in text and 'held14' not in text and 'audit_puck_cpu_held_runtime.py' not in text
raw=(json.dumps(new,sort_keys=True,indent=2,allow_nan=False)+'\n').encode();assert len(raw)<=1024**2
with (ROOT/(PREFIX+'-freeze.json')).open('xb') as stream:stream.write(raw)
print(json.dumps(dict(path=PREFIX+'-freeze.json',size_bytes=len(raw),sha256=sha(raw),pin_count=len(pins),pinned_bytes=sum(r['size_bytes'] for r in pins.values()),
    retained_14_pins=len(old['pins'])-len(index_bound),index_bound_14_pins=len(index_bound),bound_packets={k:v['artifacts'] for k,v in indexes.items()},
    replaced_live_sources=len(replaced),runtime14_runs_originals=len(runtime14_runs),controls14=len(controls14),preparation04_and_characterization04_evidence=len(evidence),
    runs_pins=sum(name.startswith('runs/') for name in pins),admission_invoked=False,runtime_invoked=False,stages_touched=False),indent=2,sort_keys=True))
