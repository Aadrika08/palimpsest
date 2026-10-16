"""Derive distinct11 wrapper/envelope/history snapshot after the freeze; never invoke them."""
from pathlib import Path
import hashlib,json,os,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PREFIX='docs/plans/puck-cpu-held-qualification-11'
AMENDMENT='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
VALIDATION=ROOT/(PREFIX+'-control-validation')
def pin(raw):return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
frame_raw=(ROOT/(PREFIX+'-freeze.json')).read_bytes();frame=json.loads(frame_raw);fp=pin(frame_raw)
assert fp==dict(size_bytes=588680,sha256='d9c34de3177fb3ea18849ece9133334e1abb963b6fc49f8e7b21988a47582983')
old=(ROOT/(AMENDMENT+'/external.py')).read_bytes()
changes=[
    (("FREEZE=ROOT/'"+AMENDMENT+"/freeze.json'").encode(),("FREEZE=ROOT/'"+PREFIX+"-freeze.json'").encode()),
    (b'5ece09386a27e458534c4ccd46298f2bdd79dec7b85b5245b5aa99635b384265',fp['sha256'].encode()),
    (b'len(raw)==519552',('len(raw)=='+str(fp['size_bytes'])).encode()),
    (b'/tmp/palimpsest-held10-amendment02-',b'/tmp/palimpsest-held11-'),
    (b'puck-cpu-held10-amendment02-external-transport-v1',b'puck-cpu-held11-external-transport-v1'),
    (b'the three qualification10 phases under admission amendment02.',b'the three qualification11 phases.')]
wrapper=old
for a,b in changes:
    assert wrapper.count(a)==(2 if a==b'/tmp/palimpsest-held10-amendment02-' else 1),a
    wrapper=wrapper.replace(a,b)
restored=wrapper
for a,b in reversed(changes):restored=restored.replace(b,a)
assert restored==old
compile(wrapper,PREFIX+'-external.py','exec')
wrapper_path=Path('/tmp/palimpsest-held11-external.py')
for path in (ROOT/(PREFIX+'-external.py'),wrapper_path):
    with path.open('xb') as out:out.write(wrapper)
envelope=json.loads((ROOT/(AMENDMENT+'/execution.json')).read_bytes())
timeout=Path('/usr/bin/timeout').read_bytes()
assert pin(timeout)=={k:envelope['timeout_binary'][k] for k in ('size_bytes','sha256')}
envelope.update(kind='puck-cpu-held-qualification11-fixed-execution-envelope-v1',admission_check_id=1,
    scope='one distinct admission11-01 before sole runtime11; no implicit retry or operator/renderer/study',
    admission_output='/tmp/palimpsest-puck-cpu-held-qualification-11-admission-01.json',
    auditor_output='/tmp/palimpsest-puck-cpu-held-qualification-11-audit-01.json',
    concrete_audit_command_path='/tmp/palimpsest-held11-concrete-audit-command.json',source_commit=frame['source_commit'])
envelope['freeze']=dict(path=str(ROOT/(PREFIX+'-freeze.json')),**fp)
envelope['wrapper']=dict(path=str(wrapper_path),tracked_copy=PREFIX+'-external.py',**pin(wrapper))
for phase in ('admission','observer','audit'):
    envelope['commands'][phase]=[str(wrapper_path) if x=='/tmp/palimpsest-held10-amendment02-external.py' else x for x in envelope['commands'][phase]]
    assert envelope['commands'][phase][-2:]==[str(wrapper_path),phase]
    envelope['phase_outputs'][phase]={key:value.replace('/tmp/palimpsest-held10-amendment02-','/tmp/palimpsest-held11-') for key,value in envelope['phase_outputs'][phase].items()}
assert envelope['auditor_output']==frame['commands']['auditor_output'] and envelope['runtime_invoked'] is False
assert envelope['source_commit']=='1126b710a372a82e932d08073cfc6c13308db437' and envelope['status']=='PREPARED_NOT_INVOKED'
assert 'held10' not in json.dumps(envelope) and 'qualification-10' not in json.dumps(envelope)
for outputs in envelope['phase_outputs'].values():assert all(not os.path.lexists(p) for p in outputs.values())
assert all(not os.path.lexists(envelope[k]) for k in ('admission_output','auditor_output','concrete_audit_command_path'))
with (ROOT/(PREFIX+'-execution.json')).open('x') as out:json.dump(envelope,out,indent=2,sort_keys=True);out.write('\n')
proof=dict(kind='held11-external-wrapper-compatibility-v1',status='PASS_WRAPPER_INVERSE_METADATA_ONLY',
    old=pin(old),new=pin(wrapper),source_previous=AMENDMENT+'/external.py',source_new=PREFIX+'-external.py',
    exact_inverse=True,limits_unchanged=True,external_caps_unchanged=True,
    timeout_version_observed=subprocess.check_output(['/usr/bin/timeout','--version'],text=True).splitlines()[0],
    scope='source inverse and local binary identity only; historical wrapper evidence separate',
    wrapper_invoked=False,admission11_invoked=False,runtime11_invoked=False)
with (ROOT/(PREFIX+'-wrapper-proof.json')).open('x') as out:json.dump(proof,out,indent=2,sort_keys=True);out.write('\n')
raw_runs=[row for row in frame['pins'] if row['path'].startswith('runs/')]
assert len(raw_runs)==102
absent=['runs/puck-cpu-runtime-characterization-01/baseline-after.json']
absent+=['runs/puck-cpu-install-01/'+leaf for leaf in ('inventory.json','licences.json','baseline-after.json','logs/namespace.json')]
absent+=['runs/puck-cpu-retained-admission-01/'+leaf for leaf in ('inventory.json','snapshot.json','baseline-after.json')]
absent+=['runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/baseline-after.json' for i in range(1,7)]
absent+=['runs/puck-cpu-held-qualification-'+epoch+'/'+leaf for epoch in ('07','08','09') for leaf in ('result.json','baseline-after.json')]
absent+=['runs/puck-cpu-held-qualification-10/baseline-after.json']
assert len(absent)==len(set(absent))==21 and all(not os.path.lexists(ROOT/p) for p in absent)
history=dict(kind='held11-historical-metadata-before-admission-v1',raw_run_files=raw_runs,pinned_historical_run_files=len(raw_runs),
    historical_absent_paths=absent,scope='only listed historical source/control/receipt/log metadata; no vendor SITE/staged/native reads')
with (VALIDATION/'historical-before-admission.json').open('x') as out:json.dump(history,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(dict(freeze=fp,wrapper=pin(wrapper),historical_run_files=len(raw_runs),historical_absent_paths=len(absent),
    admission11_invoked=False,runtime11_invoked=False)))
