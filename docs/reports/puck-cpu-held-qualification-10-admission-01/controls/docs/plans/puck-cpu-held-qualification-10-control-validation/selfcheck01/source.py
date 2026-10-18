"""Validate frozen10 metadata only; never invoke admission/main or a vendor."""
from pathlib import Path
import hashlib,json,os,stat,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='docs/plans/puck-cpu-held-qualification-10'
FREEZE_SHA='f0e56235825dc549c43d58e02b9d47de9bd81edab122a5786bd8038a3a6d47fc'
def read(name):return json.loads((ROOT/name).read_bytes())
def pin(path):
    raw=path.read_bytes();return dict(size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def module(name):
    path=ROOT/name;raw=path.read_bytes();value=types.ModuleType('held10_control_'+path.stem);value.__file__=str(path)
    exec(compile(raw,str(path),'exec'),value.__dict__);return value
config=read(BASE+'.json');old=read('docs/plans/puck-cpu-held-qualification-09.json')
freeze=read(BASE+'-freeze.json');envelope=read(BASE+'-execution.json')
assert pin(ROOT/(BASE+'-freeze.json'))==dict(size_bytes=480590,sha256=FREEZE_SHA)
assert freeze['source_commit']==envelope['source_commit']=='e723db037ed1f790c2618798d59f56913054754f'
assert freeze['actual09_invoked_at_freeze'] is freeze['actual09_admission_invoked_at_freeze'] is False
assert freeze['qualifications01_02_03_04_05_06_07_08_09_failed_consumed'] is True
assert len(freeze['pins'])==len({r['path'] for r in freeze['pins']})==1998
for row in freeze['pins']:
    path=ROOT/row['path'];stamp=path.lstat()
    assert stat.S_ISREG(stamp.st_mode) and stamp.st_nlink==1,row['path']
    assert pin(path)=={k:row[k] for k in ('size_bytes','sha256')},row['path']
roster={r['path']:r for r in freeze['pins']}
for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):assert roster[row['path']]==row
assert config['inputs']==old['inputs'] and config['preparation_acceptance']==old['preparation_acceptance']
assert all(config[k]==old[k] for k in ('root','stage_parent','interpreter','environment','limits','expected_versions','negative_imports','claims'))
assert [a['path'] for a,b in zip(old['sources'],config['sources']) if a!=b]==['scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py','src/palimpsest/puck_runtime_qualification.py']
assert {r['historical_live_path'] for r in freeze['historical09_replaced_live_sources']}=={
 'scripts/puck_worker_bootstrap.py','scripts/qualify_puck_cpu_held_runtime.py',
 'scripts/audit_puck_cpu_held_runtime.py','scripts/observe_puck_cpu_held_allocation.py','src/palimpsest/puck_runtime_qualification.py'}
assert len(freeze['process_identity_samples'])==12 and freeze['limits']==config['limits']
assert config['limits']['min_available_ram_bytes']==2<<30 and config['limits']['normal_seconds']==180
assert len(config['negative_imports'])==19 and freeze['negative_imports']==config['negative_imports']
for stem in ('puck-cpu-held-qualification-08','puck-cpu-guard-cost-v1','puck-cpu-guard-accounting-v1','puck-cpu-diagnostic-epoch09-v1'):
    folder='docs/reports/'+stem;index=read(folder+'/evidence-index.json')
    for row in index['artifacts']:
        assert roster[folder+'/'+row['archived_path']]==dict(path=folder+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256'])
assert pin(ROOT/(BASE+'-freeze.json'))=={k:envelope['freeze'][k] for k in ('size_bytes','sha256')}
assert pin(Path(envelope['wrapper']['path']))==pin(ROOT/envelope['wrapper']['tracked_copy'])=={k:envelope['wrapper'][k] for k in ('size_bytes','sha256')}
for phase in ('admission','observer','audit'):
    assert envelope['commands'][phase][-2:]==[envelope['wrapper']['path'],phase]
    assert envelope['normal_external_caps_seconds'][phase]==(240 if phase=='observer' else 145)
    assert all(not os.path.lexists(p) for p in envelope['phase_outputs'][phase].values())
assert all(not os.path.lexists(envelope[k]) for k in ('admission_output','auditor_output','concrete_audit_command_path'))
parent=module('scripts/qualify_puck_cpu_held_runtime.py');auditor=module('scripts/audit_puck_cpu_held_runtime.py')
parent.validate_configuration(config);auditor.configuration(config,False)
assert len(parent.SOURCES)==24 and len(parent.WORKER_SOURCES)==10
blobs={role:(ROOT/row['path']).read_bytes() for role,row in config['preparation_acceptance'].items()}
prior,prepared=parent.validate_preparation_acceptance(config,blobs);auditor.preparation_epoch(config,prior,prepared)
assert parent.allocation_output(config)==auditor.allocation_output(config)=='runs/puck-cpu-held-qualification-10'
changed={a['path'] for a,b in zip(prior['sources'],config['sources']) if a!=b}
assert changed==set(freeze['changed_preparation_source_paths']) and len(changed)==5
historic=read(prior['inputs']['candidate']['path']);current=read(config['inputs']['candidate']['path'])
parent.validate_publication_candidate(historic,current,pillow_origins=True);auditor.publication_candidate(historic,current,pillow_origins=True)
admission=module(BASE+'-admission.py');absence=admission.absent()
assert absence['historical_missing_receipts']==16 and len(absence['new_paths'])==6
assert all(name in roster for name in set(admission.HISTORICAL07_JSON)|set(admission.HISTORICAL08_JSON)|set(admission.HISTORICAL09_JSON))
assert all(not os.path.lexists(ROOT/('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/baseline-after.json')) for i in range(1,7))
for folder in ('docs/reports/puck-cpu-held-qualification-09','docs/plans/puck-cpu-guard-contract-v4','docs/plans/puck-cpu-q4-qualification-epoch10'):
    index=read(folder+'/evidence-index.json')
    for row in index['artifacts']:
        assert roster[folder+'/'+row['archived_path']]==dict(path=folder+'/'+row['archived_path'],size_bytes=row['size_bytes'],sha256=row['sha256'])
files=[row for row in config['sources'] if row['path'] in parent.WORKER_SOURCES]
depraw=(ROOT/'runs/puck-cpu-held-preparation-01/payload/dependencies.json').read_bytes()
legacy,_=parent.worker_registration(files,depraw,negative_imports=config['negative_imports'])
q4,_=parent.worker_registration(files,depraw,negative_imports=config['negative_imports'],qualification_version=4)
assert legacy['qualification']['version']==3
assert q4['qualification']['kind']=='puck-held-runtime-import-qualification-v4' and q4['qualification']['version']==4
for name in (BASE+'-admission.py',BASE+'-external.py'):compile((ROOT/name).read_bytes(),name,'exec')
result=dict(status='PASS_CONTROL_METADATA_ONLY',pins=len(freeze['pins']),pinned_bytes=sum(r['size_bytes'] for r in freeze['pins']),
 configuration_sha256=pin(ROOT/(BASE+'.json'))['sha256'],freeze=pin(ROOT/(BASE+'-freeze.json')),
 preparation_relative_changed_source_paths=sorted(changed),changed_config_sources=3,changed_live_sources=5,
 historical_missing_receipts=16,new_helper_paths=6,legacy_failure_loop_baselines=6,process_identity_samples=12,
 wrapper_names_size_hash_only=True,runtime_invoked=False,admission_main_invoked=False,payload_census_or_rehash=False)
p=Path('/tmp/palimpsest-held10-control-selfcheck01.json');assert not p.exists();p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result,sort_keys=True))
