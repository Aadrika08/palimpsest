"""Bind the fixed audit to the complete measured11 observer transport once."""
from pathlib import Path
import hashlib,json,os
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='docs/plans/puck-cpu-held-qualification-11'
freeze=json.loads((ROOT/(BASE+'-freeze.json')).read_bytes())
envelope=json.loads((ROOT/(BASE+'-execution.json')).read_bytes())
outer=json.loads(Path(envelope['phase_outputs']['observer']['json']).read_bytes())
assert outer['kind']=='puck-cpu-held11-external-transport-v1' and outer['phase']=='observer'
assert outer['command']==freeze['commands']['observer'] and outer['normal_exit'] is True and outer['timed_out'] is False
transport=ROOT/'runs/puck-cpu-held-qualification-11-external-cli-transport.json'
raw=transport.read_bytes();value=json.loads(raw)
assert raw==Path(envelope['phase_outputs']['observer']['stdout']).read_bytes()
assert len(raw)==outer['stdout']['size_bytes'] and hashlib.sha256(raw).hexdigest()==outer['stdout']['sha256']
assert value['kind']=='puck-cpu-held-cli-transport-v1' and value['phase']=='qualify'
assert value['configuration_sha256']=='6e28bef8bebd6daecfdf34e762584312f984e0d77c7a822a119e0c89e136b212'
assert value['command'][4]==str(ROOT/'scripts/qualify_puck_cpu_held_runtime.py')
assert type(value['observed_returncode']) is int and value['timed_out'] is False
assert outer['returncode']==value['observed_returncode']
for phase in ('audit',):assert all(not os.path.lexists(p) for p in envelope['phase_outputs'][phase].values())
assert not os.path.lexists(envelope['auditor_output'])
command=freeze['commands']['auditor_prefix']+[hashlib.sha256(raw).hexdigest(),'--output',freeze['commands']['auditor_output']]
with Path(envelope['concrete_audit_command_path']).open('x') as stream:
    stream.write(json.dumps(dict(command=command),sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status='BOUND_TO_COMPLETE_MEASURED_TRANSPORT',transport_bytes=len(raw),transport_sha256=hashlib.sha256(raw).hexdigest(),runtime_acceptance=False)))
