"""Derive distinct11b wrapper/envelope/history snapshot after the freeze; never invoke them."""
from pathlib import Path
import hashlib,json,os,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PREFIX='docs/plans/puck-cpu-held-qualification-11'
OLD11='d83dab3c92387c80e81af528fea25dd3f8931598'
VALIDATION=ROOT/(PREFIX+'-control-validation')
def pin(raw):return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
frame_raw=(ROOT/(PREFIX+'-freeze.json')).read_bytes();frame=json.loads(frame_raw);fp=pin(frame_raw)
assert fp==dict(size_bytes=617268,sha256='19f930d09329c6bac668ca67b2301a844a8ab8971c8a459cbe1ec9e1c4b22592')
old=git('show',OLD11+':'+PREFIX+'-external.py')
changes=[
    (b'd9c34de3177fb3ea18849ece9133334e1abb963b6fc49f8e7b21988a47582983',fp['sha256'].encode()),
    (b'len(raw)==588680',('len(raw)=='+str(fp['size_bytes'])).encode()),
    (b'/tmp/palimpsest-held11-',b'/tmp/palimpsest-held11b-'),
    (b'puck-cpu-held11-external-transport-v1',b'puck-cpu-held11b-external-transport-v1'),
    (b'the three qualification11 phases.',b'the three qualification11 phases (packet 11b on preparation02).')]
wrapper=old
for a,b in changes:
    assert wrapper.count(a)==(2 if a==b'/tmp/palimpsest-held11-' else 1),a
    wrapper=wrapper.replace(a,b)
restored=wrapper
for a,b in reversed(changes):restored=restored.replace(b,a)
assert restored==old
compile(wrapper,PREFIX+'-external.py','exec')
wrapper_path=Path('/tmp/palimpsest-held11b-external.py')
for path in (ROOT/(PREFIX+'-external.py'),wrapper_path):
    with path.open('xb') as out:out.write(wrapper)
envelope=json.loads(git('show',OLD11+':'+PREFIX+'-execution.json'))
assert pin(Path('/usr/bin/timeout').read_bytes())=={k:envelope['timeout_binary'][k] for k in ('size_bytes','sha256')}
envelope.update(kind='puck-cpu-held-qualification11b-fixed-execution-envelope-v1',admission_check_id=1,
    scope='one distinct admission11b-01 before sole runtime11 on preparation02; no implicit retry or operator/renderer/study',
    admission_output='/tmp/palimpsest-puck-cpu-held-qualification-11b-admission-01.json',
    auditor_output='/tmp/palimpsest-puck-cpu-held-qualification-11b-audit-01.json',
    concrete_audit_command_path='/tmp/palimpsest-held11b-concrete-audit-command.json',source_commit=frame['source_commit'],
    evidence_commit=frame['evidence_commit'],stage_guard=dict(boot_id=frame['preparation02']['boot_id'],
        stage_parent=frame['preparation02']['stage_parent'],staged_roots=frame['preparation02']['staged_roots'],mode='0700',filesystem='tmpfs'))
envelope['freeze']=dict(path=str(ROOT/(PREFIX+'-freeze.json')),**fp)
envelope['wrapper']=dict(path=str(wrapper_path),tracked_copy=PREFIX+'-external.py',**pin(wrapper))
for phase in ('admission','observer','audit'):
    envelope['commands'][phase]=[str(wrapper_path) if x=='/tmp/palimpsest-held11-external.py' else x for x in envelope['commands'][phase]]
    assert envelope['commands'][phase][-2:]==[str(wrapper_path),phase]
    envelope['phase_outputs'][phase]={key:value.replace('/tmp/palimpsest-held11-','/tmp/palimpsest-held11b-') for key,value in envelope['phase_outputs'][phase].items()}
assert envelope['auditor_output']==frame['commands']['auditor_output'] and envelope['runtime_invoked'] is False
assert envelope['source_commit']=='8f3a13810d0444099c1bf3d2a7c3cb4a482b7b15' and envelope['status']=='PREPARED_NOT_INVOKED'
assert all(s not in json.dumps(envelope) for s in ('/tmp/palimpsest-held11-','qualification-11-admission','qualification-11-audit'))
for outputs in envelope['phase_outputs'].values():assert all(not os.path.lexists(p) for p in outputs.values())
assert all(not os.path.lexists(envelope[k]) for k in ('admission_output','auditor_output','concrete_audit_command_path'))
with (ROOT/(PREFIX+'-execution.json')).open('x') as out:json.dump(envelope,out,indent=2,sort_keys=True);out.write('\n')
proof=dict(kind='held11b-external-wrapper-compatibility-v1',status='PASS_WRAPPER_INVERSE_METADATA_ONLY',
    old=pin(old),new=pin(wrapper),source_previous='git '+OLD11+':'+PREFIX+'-external.py',source_new=PREFIX+'-external.py',
    exact_inverse=True,limits_unchanged=True,external_caps_unchanged=True,
    timeout_version_observed=subprocess.check_output(['/usr/bin/timeout','--version'],text=True).splitlines()[0],
    scope='source inverse and local binary identity only; historical wrapper evidence separate',
    wrapper_invoked=False,admission11b_invoked=False,runtime11_invoked=False)
with (ROOT/(PREFIX+'-wrapper-proof.json')).open('x') as out:json.dump(proof,out,indent=2,sort_keys=True);out.write('\n')
spec=__import__('importlib.util').util.spec_from_file_location('postfreeze_admission',ROOT/(PREFIX+'-admission.py'))
admission=__import__('importlib.util').util.module_from_spec(spec);spec.loader.exec_module(admission)
raw_runs=[row for row in frame['pins'] if row['path'].startswith('runs/')]
assert len(raw_runs)==103
absent=['runs/puck-cpu-runtime-characterization-01/baseline-after.json']
absent+=['runs/puck-cpu-install-01/'+leaf for leaf in ('inventory.json','licences.json','baseline-after.json','logs/namespace.json')]
absent+=['runs/puck-cpu-retained-admission-01/'+leaf for leaf in ('inventory.json','snapshot.json','baseline-after.json')]
absent+=['runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/baseline-after.json' for i in range(1,7)]
absent+=['runs/puck-cpu-held-qualification-'+epoch+'/'+leaf for epoch in ('07','08','09') for leaf in ('result.json','baseline-after.json')]
absent+=['runs/puck-cpu-held-qualification-10/baseline-after.json']
assert len(absent)==len(set(absent))==21 and all(not os.path.lexists(ROOT/p) for p in absent)
prep=[]
for path in sorted((ROOT/'runs/puck-cpu-held-preparation-02').rglob('*'))+[ROOT/('runs/puck-cpu-held-preparation-02-external-cli'+s) for s in ('.stdout','.stderr','-transport.json')]:
    if path.is_file() and not path.is_symlink():
        name=str(path.relative_to(ROOT))
        if name!=frame['preparation02']['acceptance']['result']['path']:prep.append(dict(path=name,**pin(path.read_bytes())))
assert len(prep)==51
assert all(os.path.isdir(ROOT/p) and not os.listdir(ROOT/p) for p in admission.EMPTY_DIRECTORIES) and len(admission.EMPTY_DIRECTORIES)==35
assert all(not os.path.lexists(p) for p in admission.UNEXECUTED11['outputs'])
history=dict(kind='held11b-historical-metadata-before-admission-v1',raw_run_files=raw_runs,pinned_historical_run_files=len(raw_runs),
    historical_absent_paths=absent,preparation02_run_files=prep,historical_empty_directories=admission.EMPTY_DIRECTORIES,
    attempt11_d83dab3_absent_outputs=admission.UNEXECUTED11['outputs'],
    scope='only listed historical source/control/receipt/log metadata; no vendor SITE/staged/native reads; preparation02 stage untouched')
with (VALIDATION/'historical-before-admission.json').open('x') as out:json.dump(history,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(dict(freeze=fp,wrapper=pin(wrapper),historical_run_files=len(raw_runs),historical_absent_paths=len(absent),
    preparation02_run_files=len(prep),empty_directories=35,d83dab3_absent_outputs=len(admission.UNEXECUTED11['outputs']),
    admission11b_invoked=False,runtime11_invoked=False,stage_touched=False)))
