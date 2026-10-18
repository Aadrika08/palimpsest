"""Derive the allocation-16 wrapper, envelope and history snapshot after the freeze; never invoke them.

The wrapper is the reviewed-GO attempt-14 wrapper with counted, exactly invertible edits (freeze pin,
held16 stems and receipt kind, and phase budgets observer 1300 s / audit 330 s / admission 145 s, each
above its child's own alarm: observer 1275 s + 5 s cleanup, episode auditor 310 s, admission 130 s).
The envelope wraps each budget in a GNU timeout 10 s longer. The snapshot lists historical run
files and absences the guards and collector re-check; the preparation04 stage is never opened.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PREFIX='docs/plans/puck-cpu-held-episode-16'
OLD='docs/plans/puck-cpu-held-qualification-14'
CONTROL14='eb34d5c2a66730c248b00229c17ce84e197b3d68'
VALIDATION=ROOT/(PREFIX+'-control-validation')
def pin(raw):return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
frame_raw=(ROOT/(PREFIX+'-freeze.json')).read_bytes();frame=json.loads(frame_raw);fp=pin(frame_raw)
assert fp==dict(size_bytes=542502,sha256='a40c0d1483486a59531149a63eaaaf968fc8d09ca1547480e1b8d71eddf67d35')
old=(ROOT/(OLD+'-external.py')).read_bytes();assert old==git('show',CONTROL14+':'+OLD+'-external.py')
changes=[
    (b"FREEZE=ROOT/'docs/plans/puck-cpu-held-qualification-14-freeze.json'",b"FREEZE=ROOT/'docs/plans/puck-cpu-held-episode-16-freeze.json'"),
    (b'7cecde69672e25b68ebff99f5e007d65d2a91da5d2ad896ee84d2e3f4ce27971',fp['sha256'].encode()),
    (b'len(raw)==698687',('len(raw)=='+str(fp['size_bytes'])).encode()),
    (b'/tmp/palimpsest-held14-',b'/tmp/palimpsest-held16-'),
    (b'puck-cpu-held14-external-transport-v1',b'puck-cpu-held16-external-transport-v1'),
    # Each budget outlasts its child's own alarm: observer 1275 s (+5 s cleanup), episode auditor 310 s, admission 130 s.
    (b"budget=440 if phase=='observer' else 145",b"budget=1300 if phase=='observer' else 330 if phase=='audit' else 145"),
    (b'the three extended-clock qualification14 phases on preparation03.',b'the three allocation-16 held-episode phases on preparation04.')]
wrapper=old
for a,b in changes:
    assert wrapper.count(a)==(2 if a==b'/tmp/palimpsest-held14-' else 1),a
    wrapper=wrapper.replace(a,b)
restored=wrapper
for a,b in reversed(changes):restored=restored.replace(b,a)
assert restored==old
compile(wrapper,PREFIX+'-external.py','exec')
wrapper_path=Path('/tmp/palimpsest-held16-external.py')
for path in (ROOT/(PREFIX+'-external.py'),wrapper_path):
    with path.open('xb') as out:out.write(wrapper)
envelope=json.loads((ROOT/(OLD+'-execution.json')).read_bytes())
assert pin(Path('/usr/bin/timeout').read_bytes())=={k:envelope['timeout_binary'][k] for k in ('size_bytes','sha256')}
caps=dict(admission=145,audit=330,observer=1300);terms={k:v+10 for k,v in caps.items()}
envelope.update(kind='puck-cpu-held-episode16-fixed-execution-envelope-v1',admission_check_id=1,
    scope='one distinct admission16-01 before the sole allocation-16 held episode on preparation04; no implicit retry or operator/collection/study',
    admission_output='/tmp/palimpsest-puck-cpu-held-episode-16-admission-01.json',
    auditor_output=frame['commands']['auditor_output'],concrete_audit_command_path='/tmp/palimpsest-held16-concrete-audit-command.json',
    source_commit=frame['source_commit'],evidence_commits=frame['evidence_commits'],
    stage_guard=dict(boot_id=frame['preparation04']['boot_id'],stage_parent=frame['preparation04']['stage_parent'],
        staged_roots=frame['preparation04']['staged_roots'],mode='0700',filesystem='tmpfs',result=frame['preparation04']['acceptance']['result']),
    episode16_clocks=frame['episode16_clocks'],normal_external_caps_seconds=caps,outer_term_seconds=terms)
envelope.pop('epoch14_clocks')
envelope['freeze']=dict(path=str(ROOT/(PREFIX+'-freeze.json')),**fp)
envelope['wrapper']=dict(path=str(wrapper_path),tracked_copy=PREFIX+'-external.py',**pin(wrapper))
for phase in ('admission','observer','audit'):
    command=['/usr/bin/timeout','--signal=TERM','--kill-after=5s',str(terms[phase])+'s',
        '/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11','-I','-S','-B',str(wrapper_path),phase]
    old_command=envelope['commands'][phase];assert old_command[4:8]==command[4:8] and old_command[-1]==phase
    envelope['commands'][phase]=command
    envelope['phase_outputs'][phase]={key:value.replace('/tmp/palimpsest-held14-','/tmp/palimpsest-held16-') for key,value in envelope['phase_outputs'][phase].items()}
c=frame['episode16_clocks']
assert caps['observer']>c['observer_hard']+c['observer_cleanup'] and caps['audit']>c['auditor_alarm'] and caps['admission']>130
assert (c['observer_wrapper'],c['observer_outer_term'],c['audit_wrapper'],c['audit_outer_term'])==(caps['observer'],terms['observer'],caps['audit'],terms['audit'])
assert envelope['runtime_invoked'] is False and envelope['status']=='PREPARED_NOT_INVOKED'
assert all(s not in json.dumps({k:v for k,v in envelope.items() if k!='evidence_commits'}) for s in ('held14','qualification-14','held-03'))
for outputs in envelope['phase_outputs'].values():assert all(not os.path.lexists(p) for p in outputs.values())
assert all(not os.path.lexists(envelope[k]) for k in ('admission_output','auditor_output','concrete_audit_command_path'))
with (ROOT/(PREFIX+'-execution.json')).open('x') as out:json.dump(envelope,out,indent=2,sort_keys=True);out.write('\n')
proof=dict(kind='held16-external-wrapper-compatibility-v1',status='PASS_WRAPPER_INVERSE_METADATA_ONLY',
    old=pin(old),new=pin(wrapper),source_previous=OLD+'-external.py (git '+CONTROL14+')',source_new=PREFIX+'-external.py',
    exact_inverse=True,budget_seconds=dict(previous=dict(observer=440,audit=145,admission=145),new=caps),outer_term_seconds=terms,
    timeout_version_observed=subprocess.check_output(['/usr/bin/timeout','--version'],text=True).splitlines()[0],
    scope='source inverse and local binary identity only; historical wrapper evidence separate',
    wrapper_invoked=False,admission16_invoked=False,episode16_invoked=False)
with (ROOT/(PREFIX+'-wrapper-proof.json')).open('x') as out:json.dump(proof,out,indent=2,sort_keys=True);out.write('\n')
spec=importlib.util.spec_from_file_location('postfreeze16_admission',ROOT/(PREFIX+'-admission.py'))
admission=importlib.util.module_from_spec(spec);spec.loader.exec_module(admission)
raw_runs=[row for row in frame['pins'] if row['path'].startswith('runs/')]
old_history=json.loads((ROOT/(OLD+'-control-validation/historical-before-admission.json')).read_bytes())
absent=list(old_history['historical_absent_paths']);assert len(absent)==23 and all(not os.path.lexists(ROOT/p) for p in absent)
def run_files(output,pinned,count):
    rows=[]
    for path in sorted((ROOT/output).rglob('*'))+[ROOT/(output+'-external-cli'+s) for s in ('.stdout','.stderr','-transport.json')]:
        if path.is_file() and not path.is_symlink():
            name=str(path.relative_to(ROOT))
            if name not in pinned:rows.append(dict(path=name,**pin(path.read_bytes())))
    assert len(rows)==count,(output,len(rows));return rows
pinned={r['path'] for r in frame['pins']}
prep04=run_files('runs/puck-cpu-held-preparation-04',pinned,114)
prep03=run_files('runs/puck-cpu-held-preparation-03',pinned,51)
prep02=run_files('runs/puck-cpu-held-preparation-02',pinned,51)
char04=run_files('runs/puck-cpu-runtime-characterization-04',pinned,40)
assert prep03==old_history['preparation03_run_files'] and prep02==old_history['preparation02_run_files']
assert all(os.path.isdir(ROOT/p) and not os.listdir(ROOT/p) for p in admission.EMPTY_DIRECTORIES) and len(admission.EMPTY_DIRECTORIES)==46
assert all(not os.path.lexists(p) for p in admission.UNEXECUTED11['outputs'])
retired=['/tmp/palimpsest-puck-cpu-held-02','/tmp/palimpsest-puck-cpu-held-03'];assert all(not os.path.lexists(p) for p in retired)
history=dict(kind='held16-historical-metadata-before-admission-v1',raw_run_files=raw_runs,pinned_historical_run_files=len(raw_runs),
    historical_absent_paths=absent,preparation04_run_files=prep04,preparation03_run_files=prep03,preparation02_run_files=prep02,
    characterization04_run_files=char04,historical_empty_directories=admission.EMPTY_DIRECTORIES,
    attempt11_d83dab3_absent_outputs=admission.UNEXECUTED11['outputs'],retired_stage_paths=retired,
    scope='only listed historical source/control/receipt/log metadata; no vendor SITE/staged/native reads; the preparation04 stage is untouched')
with (VALIDATION/'historical-before-admission.json').open('x') as out:json.dump(history,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(dict(freeze=fp,wrapper=pin(wrapper),historical_run_files=len(raw_runs),historical_absent_paths=len(absent),
    preparation04_run_files=len(prep04),preparation03_run_files=len(prep03),preparation02_run_files=len(prep02),characterization04_run_files=len(char04),
    empty_directories=46,d83dab3_absent_outputs=len(admission.UNEXECUTED11['outputs']),retired_stages=retired,caps=caps,outer_terms=terms,
    admission16_invoked=False,episode16_invoked=False,stages_touched=False)))
