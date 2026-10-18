from pathlib import Path
import hashlib,json
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
REL='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
BASE=ROOT/REL
def pin(raw):return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
frame_raw=(BASE/'freeze.json').read_bytes();frame=json.loads(frame_raw);fp=pin(frame_raw)
old=(ROOT/'docs/plans/puck-cpu-held-qualification-10-external.py').read_bytes()
changes=[
    (b"ROOT/'docs/plans/puck-cpu-held-qualification-10-freeze.json'",("ROOT/'"+REL+"/freeze.json'").encode()),
    (b'f0e56235825dc549c43d58e02b9d47de9bd81edab122a5786bd8038a3a6d47fc',fp['sha256'].encode()),
    (b'len(raw)==480590',('len(raw)=='+str(fp['size_bytes'])).encode()),
    (b'/tmp/palimpsest-held10-',b'/tmp/palimpsest-held10-amendment02-'),
    (b'puck-cpu-held10-external-transport-v1',b'puck-cpu-held10-amendment02-external-transport-v1'),
    (b'the three qualification10 phases.',b'the three qualification10 phases under admission amendment02.')]
wrapper=old
for a,b in changes:wrapper=wrapper.replace(a,b)
restored=wrapper
for a,b in reversed(changes):restored=restored.replace(b,a)
assert restored==old
compile(wrapper,str(BASE/'external.py'),'exec')
wrapper_path=Path('/tmp/palimpsest-held10-amendment02-external.py')
for path in (BASE/'external.py',wrapper_path):
    with path.open('xb') as out:out.write(wrapper)
envelope=json.loads((ROOT/'docs/plans/puck-cpu-held-qualification-10-execution.json').read_bytes())
envelope.update(kind='puck-cpu-held-qualification10-admission02-fixed-execution-envelope-v1',
    admission_check_id=2,scope='one distinct admission02 before sole runtime10; no implicit retry or operator/renderer/study',
    admission_output='/tmp/palimpsest-puck-cpu-held-qualification-10-admission-02.json',
    concrete_audit_command_path='/tmp/palimpsest-held10-amendment02-concrete-audit-command.json')
envelope['freeze']=dict(path=str(BASE/'freeze.json'),**fp)
envelope['wrapper']=dict(path=str(wrapper_path),tracked_copy=REL+'/external.py',**pin(wrapper))
for phase in ('admission','observer','audit'):
    envelope['commands'][phase]=[str(wrapper_path) if x=='/tmp/palimpsest-held10-external.py' else x for x in envelope['commands'][phase]]
    envelope['phase_outputs'][phase]={key:value.replace('/tmp/palimpsest-held10-','/tmp/palimpsest-held10-amendment02-') for key,value in envelope['phase_outputs'][phase].items()}
assert envelope['source_commit']==frame['source_commit'] and envelope['runtime_invoked'] is False
for outputs in envelope['phase_outputs'].values():assert all(not Path(p).exists() for p in outputs.values())
with (BASE/'execution.json').open('x') as out:json.dump(envelope,out,indent=2,sort_keys=True);out.write('\n')
proof=dict(status='PASS_WRAPPER_INVERSE_METADATA_ONLY',old=pin(old),new=pin(wrapper),
    exact_inverse=True,limits_unchanged=True,wrapper_invoked=False,admission02_invoked=False,runtime10_invoked=False)
with (BASE/'wrapper-proof.json').open('x') as out:json.dump(proof,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(dict(freeze=fp,wrapper=pin(wrapper),admission02_invoked=False,runtime10_invoked=False)))
