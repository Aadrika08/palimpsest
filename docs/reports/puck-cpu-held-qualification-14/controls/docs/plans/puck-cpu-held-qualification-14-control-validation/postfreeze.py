"""Derive distinct14 wrapper/envelope/history snapshot after the freeze; never invoke them."""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PREFIX='docs/plans/puck-cpu-held-qualification-14'
OLD='docs/plans/puck-cpu-held-qualification-11'
CONTROL11B='27780dd5cbc096c26fb353faea7edfde878a4f74'
VALIDATION=ROOT/(PREFIX+'-control-validation')
def pin(raw):return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
frame_raw=(ROOT/(PREFIX+'-freeze.json')).read_bytes();frame=json.loads(frame_raw);fp=pin(frame_raw)
assert fp==dict(size_bytes=698687,sha256='7cecde69672e25b68ebff99f5e007d65d2a91da5d2ad896ee84d2e3f4ce27971')
old=(ROOT/(OLD+'-external.py')).read_bytes();assert old==git('show',CONTROL11B+':'+OLD+'-external.py')
changes=[
    (b"FREEZE=ROOT/'docs/plans/puck-cpu-held-qualification-11-freeze.json'",b"FREEZE=ROOT/'docs/plans/puck-cpu-held-qualification-14-freeze.json'"),
    (b'19f930d09329c6bac668ca67b2301a844a8ab8971c8a459cbe1ec9e1c4b22592',fp['sha256'].encode()),
    (b'len(raw)==617268',('len(raw)=='+str(fp['size_bytes'])).encode()),
    (b'/tmp/palimpsest-held11b-',b'/tmp/palimpsest-held14-'),
    (b'puck-cpu-held11b-external-transport-v1',b'puck-cpu-held14-external-transport-v1'),
    # Review-04 Important 2: the observer wrapper must outlast observer 400/415s; admission/audit stay 145s.
    (b"budget=240 if phase=='observer' else 145",b"budget=440 if phase=='observer' else 145"),
    (b'the three qualification11 phases (packet 11b on preparation02).',b'the three extended-clock qualification14 phases on preparation03.')]
wrapper=old
for a,b in changes:
    assert wrapper.count(a)==(2 if a==b'/tmp/palimpsest-held11b-' else 1),a
    wrapper=wrapper.replace(a,b)
restored=wrapper
for a,b in reversed(changes):restored=restored.replace(b,a)
assert restored==old
compile(wrapper,PREFIX+'-external.py','exec')
wrapper_path=Path('/tmp/palimpsest-held14-external.py')
for path in (ROOT/(PREFIX+'-external.py'),wrapper_path):
    with path.open('xb') as out:out.write(wrapper)
envelope=json.loads((ROOT/(OLD+'-execution.json')).read_bytes())
assert pin(Path('/usr/bin/timeout').read_bytes())=={k:envelope['timeout_binary'][k] for k in ('size_bytes','sha256')}
envelope.update(kind='puck-cpu-held-qualification14-fixed-execution-envelope-v1',admission_check_id=1,
    scope='one distinct admission14-01 before sole extended-clock runtime14 on preparation03; no implicit retry or operator/renderer/study',
    admission_output='/tmp/palimpsest-puck-cpu-held-qualification-14-admission-01.json',
    auditor_output='/tmp/palimpsest-puck-cpu-held-qualification-14-audit-01.json',
    concrete_audit_command_path='/tmp/palimpsest-held14-concrete-audit-command.json',source_commit=frame['source_commit'],
    evidence_commits=frame['evidence_commits'],stage_guard=dict(boot_id=frame['preparation03']['boot_id'],
        stage_parent=frame['preparation03']['stage_parent'],staged_roots=frame['preparation03']['staged_roots'],mode='0700',filesystem='tmpfs'),
    epoch14_clocks=frame['epoch14_clocks'])
envelope.pop('evidence_commit')
envelope['normal_external_caps_seconds']=dict(envelope['normal_external_caps_seconds'],observer=440)
envelope['outer_term_seconds']=dict(envelope['outer_term_seconds'],observer=450)
envelope['freeze']=dict(path=str(ROOT/(PREFIX+'-freeze.json')),**fp)
envelope['wrapper']=dict(path=str(wrapper_path),tracked_copy=PREFIX+'-external.py',**pin(wrapper))
for phase in ('admission','observer','audit'):
    command=[str(wrapper_path) if x=='/tmp/palimpsest-held11b-external.py' else x for x in envelope['commands'][phase]]
    if phase=='observer':
        assert command[3]=='250s';command[3]='450s'
    assert command[:4]==['/usr/bin/timeout','--signal=TERM','--kill-after=5s',str(envelope['outer_term_seconds'][phase])+'s']
    assert command[-2:]==[str(wrapper_path),phase];envelope['commands'][phase]=command
    envelope['phase_outputs'][phase]={key:value.replace('/tmp/palimpsest-held11b-','/tmp/palimpsest-held14-') for key,value in envelope['phase_outputs'][phase].items()}
assert envelope['normal_external_caps_seconds']==dict(admission=145,audit=145,observer=440) and envelope['outer_term_seconds']==dict(admission=155,audit=155,observer=450)
assert envelope['auditor_output']==frame['commands']['auditor_output'] and envelope['runtime_invoked'] is False
assert envelope['source_commit']=='f05bd699af337e44de54584bb334690ec405f994' and envelope['status']=='PREPARED_NOT_INVOKED'
assert all(s not in json.dumps({k:v for k,v in envelope.items() if k!='evidence_commits'}) for s in ('11b','qualification-11-'))
for outputs in envelope['phase_outputs'].values():assert all(not os.path.lexists(p) for p in outputs.values())
assert all(not os.path.lexists(envelope[k]) for k in ('admission_output','auditor_output','concrete_audit_command_path'))
with (ROOT/(PREFIX+'-execution.json')).open('x') as out:json.dump(envelope,out,indent=2,sort_keys=True);out.write('\n')
proof=dict(kind='held14-external-wrapper-compatibility-v1',status='PASS_WRAPPER_INVERSE_METADATA_ONLY',
    old=pin(old),new=pin(wrapper),source_previous=OLD+'-external.py (git '+CONTROL11B+')',source_new=PREFIX+'-external.py',
    exact_inverse=True,observer_budget_seconds=dict(previous=240,new=440),admission_and_audit_budget_seconds=145,
    timeout_version_observed=subprocess.check_output(['/usr/bin/timeout','--version'],text=True).splitlines()[0],
    scope='source inverse and local binary identity only; historical wrapper evidence separate',
    wrapper_invoked=False,admission14_invoked=False,runtime14_invoked=False)
with (ROOT/(PREFIX+'-wrapper-proof.json')).open('x') as out:json.dump(proof,out,indent=2,sort_keys=True);out.write('\n')
spec=importlib.util.spec_from_file_location('postfreeze14_admission',ROOT/(PREFIX+'-admission.py'))
admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
raw_runs=[row for row in frame['pins'] if row['path'].startswith('runs/')]
assert len(raw_runs)==126
absent=['runs/puck-cpu-runtime-characterization-01/baseline-after.json']
absent+=['runs/puck-cpu-install-01/'+leaf for leaf in ('inventory.json','licences.json','baseline-after.json','logs/namespace.json')]
absent+=['runs/puck-cpu-retained-admission-01/'+leaf for leaf in ('inventory.json','snapshot.json','baseline-after.json')]
absent+=['runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/baseline-after.json' for i in range(1,7)]
absent+=['runs/puck-cpu-held-qualification-'+epoch+'/'+leaf for epoch in ('07','08','09') for leaf in ('result.json','baseline-after.json')]
absent+=['runs/puck-cpu-held-qualification-10/baseline-after.json']
absent+=['runs/puck-cpu-held-qualification-11/'+leaf for leaf in ('result.json','baseline-after.json')]
assert len(absent)==len(set(absent))==23 and all(not os.path.lexists(ROOT/p) for p in absent)
def run_files(output,pinned):
    rows=[]
    for path in sorted((ROOT/output).rglob('*'))+[ROOT/(output+'-external-cli'+s) for s in ('.stdout','.stderr','-transport.json')]:
        if path.is_file() and not path.is_symlink():
            name=str(path.relative_to(ROOT))
            if name!=pinned:rows.append(dict(path=name,**pin(path.read_bytes())))
    assert len(rows)==51,(output,len(rows));return rows
prep03=run_files('runs/puck-cpu-held-preparation-03',frame['preparation03']['acceptance']['result']['path'])
prep02=run_files('runs/puck-cpu-held-preparation-02','runs/puck-cpu-held-preparation-02/result.json')
old_history=json.loads((ROOT/(OLD+'-control-validation/historical-before-admission.json')).read_bytes())
assert prep02==old_history['preparation02_run_files']
assert all(os.path.isdir(ROOT/p) and not os.listdir(ROOT/p) for p in admission.EMPTY_DIRECTORIES) and len(admission.EMPTY_DIRECTORIES)==41
assert all(not os.path.lexists(p) for p in admission.UNEXECUTED11['outputs'])
history=dict(kind='held14-historical-metadata-before-admission-v1',raw_run_files=raw_runs,pinned_historical_run_files=len(raw_runs),
    historical_absent_paths=absent,preparation03_run_files=prep03,preparation02_run_files=prep02,historical_empty_directories=admission.EMPTY_DIRECTORIES,
    attempt11_d83dab3_absent_outputs=admission.UNEXECUTED11['outputs'],
    scope='only listed historical source/control/receipt/log metadata; no vendor SITE/staged/native reads; preparation02/03 stages untouched')
with (VALIDATION/'historical-before-admission.json').open('x') as out:json.dump(history,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(dict(freeze=fp,wrapper=pin(wrapper),historical_run_files=len(raw_runs),historical_absent_paths=len(absent),
    preparation03_run_files=len(prep03),preparation02_run_files=len(prep02),empty_directories=41,
    d83dab3_absent_outputs=len(admission.UNEXECUTED11['outputs']),observer_wrapper_seconds=440,observer_outer_term_seconds=450,
    admission14_invoked=False,runtime14_invoked=False,stages_touched=False)))
