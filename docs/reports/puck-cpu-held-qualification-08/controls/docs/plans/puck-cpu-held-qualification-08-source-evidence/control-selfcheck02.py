from pathlib import Path
import hashlib,json,os,stat,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='docs/plans/puck-cpu-held-qualification-08'
def read(name):return json.loads((ROOT/name).read_bytes())
def pin(path):
    raw=path.read_bytes();return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
config=read(BASE+'.json');old=read('docs/plans/puck-cpu-held-qualification-07.json');freeze=read(BASE+'-freeze.json');envelope=read(BASE+'-execution.json')
assert len(freeze['pins'])==len({r['path'] for r in freeze['pins']})==749
for row in freeze['pins']:
    path=ROOT/row['path'];st=path.lstat()
    assert stat.S_ISREG(st.st_mode) and st.st_nlink==1
    assert pin(path)=={k:row[k] for k in ('size_bytes','sha256')},row['path']
for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):assert row in freeze['pins']
assert config['inputs']==old['inputs'] and config['preparation_acceptance']==old['preparation_acceptance']
assert all(config[k]==old[k] for k in ('root','stage_parent','interpreter','environment','limits','expected_versions','negative_imports','claims'))
assert freeze['limits']==config['limits'] and len(config['negative_imports'])==19
assert pin(ROOT/(BASE+'-freeze.json'))=={k:envelope['freeze'][k] for k in ('size_bytes','sha256')}
assert pin(Path(envelope['wrapper']['path']))==pin(ROOT/envelope['wrapper']['tracked_copy'])=={k:envelope['wrapper'][k] for k in ('size_bytes','sha256')}
for name in ('admission','observer','audit'):
    assert envelope['commands'][name][-2:]==[envelope['wrapper']['path'],name]
    assert envelope['normal_external_caps_seconds'][name]==(240 if name=='observer' else 145)
    assert all(not os.path.lexists(path) for path in envelope['phase_outputs'][name].values())
assert not os.path.lexists(envelope['admission_output']) and not os.path.lexists(envelope['auditor_output'])
for path in ('runs/puck-cpu-held-qualification-08','runs/puck-cpu-held-qualification-08-external-cli.stdout','runs/puck-cpu-held-qualification-08-external-cli.stderr','runs/puck-cpu-held-qualification-08-external-cli-transport.json'):
    assert not os.path.lexists(ROOT/path)
def module(path):
    raw=(ROOT/path).read_bytes();value=types.ModuleType('controls_'+Path(path).stem);value.__file__=str(ROOT/path)
    exec(compile(raw,str(ROOT/path),'exec'),value.__dict__);return value
parent=module('scripts/qualify_puck_cpu_held_runtime.py');auditor=module('scripts/audit_puck_cpu_held_runtime.py')
assert len(parent.SOURCES)==24 and len(parent.WORKER_SOURCES)==10
parent.validate_configuration(config);auditor.configuration(config,False)
blobs={role:(ROOT/row['path']).read_bytes() for role,row in config['preparation_acceptance'].items()}
prior,prepared=parent.validate_preparation_acceptance(config,blobs);auditor.preparation_epoch(config,prior,prepared)
assert parent.allocation_output(config)==auditor.allocation_output(config)=='runs/puck-cpu-held-qualification-08'
changed={a['path'] for a,b in zip(prior['sources'],config['sources']) if a!=b}
assert changed==set(freeze['changed_preparation_source_paths']) and len(changed)==5
historic_candidate=read(prior['inputs']['candidate']['path']);current_candidate=read(config['inputs']['candidate']['path'])
parent.validate_publication_candidate(historic_candidate,current_candidate,pillow_origins=True)
auditor.publication_candidate(historic_candidate,current_candidate,pillow_origins=True)
admission=module(BASE+'-admission.py')
assert all(name in {r['path'] for r in freeze['pins']} for name in admission.HISTORICAL07_JSON)
assert admission.absent()['historical_missing_receipts']==12
for path in (BASE+'-admission.py',BASE+'-external.py'):compile((ROOT/path).read_bytes(),str(ROOT/path),'exec')
result=dict(status='PASS_CONTROL_METADATA_ONLY',pins=len(freeze['pins']),pinned_bytes=sum(r['size_bytes'] for r in freeze['pins']),preparation_relative_changed_source_paths=sorted(changed),historical_missing_receipts=12,wrapper_names_and_pins_only=True,configuration_sha256=pin(ROOT/(BASE+'.json'))['sha256'],freeze=pin(ROOT/(BASE+'-freeze.json')),runtime_invoked=False,admission_main_invoked=False,payload_census_or_rehash=False)
Path('/tmp/palimpsest-held08-control-selfcheck02.json').open('x').write(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result))
