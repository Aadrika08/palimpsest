"""Use authenticated metadata readers; never run admission, payloads or vendors."""
from pathlib import Path
import hashlib,json,os,sys,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='docs/plans/puck-cpu-held-qualification-11'
AMENDMENT='docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
def module(path):
    value=types.ModuleType('held11_selfcheck_'+path.stem);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
control=module(ROOT/(BASE+'-admission.py'))
authraw=control.AUDITOR.read_bytes()
assert len(authraw)==65522 and hashlib.sha256(authraw).hexdigest()==control.AUDITOR_SHA
auth=module(control.AUDITOR)
envelope=json.loads((ROOT/(BASE+'-execution.json')).read_bytes())
before=len(os.listdir('/proc/self/fd'));held=auth.Held(time.monotonic()+60)
try:
    config,configraw=held.json(control.CONFIGURATION,dict(size_bytes=9130,sha256=control.CONFIG_SHA),1024**2,lf=True)
    frame,frameraw=held.json(ROOT/(BASE+'-freeze.json'),envelope['freeze'],1024**2)
    assert frameraw==(json.dumps(frame,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    assert frame['kind']=='puck-cpu-held-qualification11-frozen-controls-v1' and frame['source_commit']==envelope['source_commit']
    assert frame['actual11_invoked_at_freeze'] is frame['actual11_admission_invoked_at_freeze'] is False
    assert frame['qualifications01_02_03_04_05_06_07_08_09_10_failed_consumed'] is True
    assert frame['admission10_01_failed_consumed'] is frame['admission10_02_admitted_consumed_by_runtime10'] is True
    current=control.module(held,ROOT/'scripts/audit_puck_cpu_held_runtime.py',control.AUDITOR_CURRENT_SHA)
    current.configuration(config,False)
    roles={row['path'] for row in config['inputs'].values()}
    roles.update(row['path'] for row in config['preparation_acceptance'].values())
    roles.add('docs/plans/puck-cpu-observed-import-profile-candidate-01.json')
    roles.update('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json' for i in range(1,7))
    for rows in (control.HISTORICAL07_JSON,control.HISTORICAL08_JSON,control.HISTORICAL09_JSON,control.HISTORICAL10_JSON,
            control.ADMISSION01_PINS,control.ADMISSION02_PINS):roles.update(rows)
    control.hold_manifest(held,frame['pins'],roles)
    admitted10,_=held.json(ROOT/control.ADMITTED10_CONFIGURATION,dict(size_bytes=8988,sha256=control.HISTORICAL10_JSON[control.ADMITTED10_CONFIGURATION]),1024**2,lf=True)
    assert control.check_consumed_admission01(held,admitted10)['status']=='FAILED_CONSUMED'
    assert control.check_consumed_admission02(held,admitted10)['status']=='ADMITTED_CONSUMED_BY_RUNTIME10'
    for epoch in ('07','08','09','10'):assert getattr(control,'check_consumed'+epoch)(held)['status']=='FAILED_CONSUMED'
    roster={r['path']:r for r in frame['pins']}
    assert len(roster)==len(frame['pins'])==2427
    replaced={row['historical_live_path'] for row in frame['historical10_replaced_live_sources']}
    for name in (AMENDMENT+'/freeze.json','docs/plans/puck-cpu-held-qualification-10-freeze.json'):
        old=json.loads((ROOT/name).read_bytes())
        assert all(roster[row['path']]==row for row in old['pins'] if row['path'] not in replaced)
    assert all(roster['docs/reports/puck-cpu-held-qualification-10/source/'+r['historical_pin']['path']]==r['archived_pin'] for r in frame['historical10_replaced_live_sources'])
    previous=json.loads((ROOT/(AMENDMENT+'/configuration.json')).read_bytes())
    assert admitted10==previous and all(config[k]==previous[k] for k in ('root','stage_parent','inputs','preparation_acceptance','interpreter','environment','expected_versions','limits','claims'))
    for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):assert roster[row['path']]==row
    prepared_config,_=held.json(ROOT/'docs/plans/puck-cpu-held-preparation-01.json',maximum=1024**2,lf=True)
    prepared,_=held.json(ROOT/'runs/puck-cpu-held-preparation-01/result.json',maximum=1024**2,lf=True)
    current.preparation_epoch(config,prepared_config,prepared)
    blobs={};data={}
    for role,row in config['inputs'].items():
        blobs[role]=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
        if role!='generated':data[role]=current.decode(blobs[role])
    prior_candidate=current.decode(held.file(ROOT/prepared_config['inputs']['candidate']['path'],prepared_config['inputs']['candidate'],16*1024**2,raw=True))
    current.publication_candidate(prior_candidate,data['candidate'],pillow_origins=True)
    current.inputs_binding(config,data,blobs)
    _,dependency,directories=current.plan(config,data)
    negative=control.check_absences(dependency,directories,config['negative_imports'])
    declared={row['name'] for row in dependency['modules']+dependency['namespaces']}
    declared.update(row['name'] for key in ('exports','native_cache') for row in dependency['import_profile'].get(key,[]))
    hidden=current.HIDDEN11_IMPORTS
    assert hidden==frame['hidden_imports'] and not set(hidden)&set(config['negative_imports'])
    assert all(name.split('.')[0] not in sys.stdlib_module_names and not any(k==name or k.startswith(name+'.') for k in declared) for name in hidden)
    absence=control.absent()
    assert absence['historical_missing_receipts']==17 and len(absence['new_paths'])==6
    history=json.loads((ROOT/(BASE+'-control-validation/historical-before-admission.json')).read_bytes())
    assert len(history['raw_run_files'])==102 and all(roster[row['path']]==row for row in history['raw_run_files'])
    assert len(history['historical_absent_paths'])==21 and all(not os.path.lexists(ROOT/p) for p in history['historical_absent_paths'])
    for phase in envelope['phase_outputs'].values():assert all(not os.path.lexists(p) for p in phase.values())
    assert all(not os.path.lexists(envelope[k]) for k in ('admission_output','auditor_output','concrete_audit_command_path'))
    assert envelope['admission_output']==str(control.OUTPUT) and envelope['auditor_output']==frame['commands']['auditor_output']
    for row in (envelope['wrapper'],):
        raw=Path(row['path']).read_bytes()
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
        assert raw==(ROOT/row['tracked_copy']).read_bytes()
    held.recheck();held.clock()
finally:held.close()
after=len(os.listdir('/proc/self/fd'))
assert before==after and not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split()
assert len(os.listdir('/proc/self/task'))==1
parent=module(ROOT/'scripts/qualify_puck_cpu_held_runtime.py')
parent.validate_configuration(config)
assert config['negative_imports']==parent.QUALIFY11_NEGATIVE_IMPORTS and hidden==parent.QUALIFY11_HIDDEN_IMPORTS
assert parent.allocation_output(config)==current.allocation_output(config)=='runs/puck-cpu-held-qualification-11'
pblobs={role:(ROOT/row['path']).read_bytes() for role,row in config['preparation_acceptance'].items()}
prior,_=parent.validate_preparation_acceptance(config,pblobs)
changed={a['path'] for a,b in zip(prior['sources'],config['sources']) if a!=b}
assert changed==set(frame['changed_preparation_source_paths']) and len(changed)==5
files=[row for row in config['sources'] if row['path'] in parent.WORKER_SOURCES]
depraw=(ROOT/'runs/puck-cpu-held-preparation-01/payload/dependencies.json').read_bytes()
q5,_=parent.worker_registration(files,depraw,negative_imports=config['negative_imports'],qualification_version=5,hidden_imports=hidden)
assert q5['qualification']['kind']=='puck-held-runtime-import-qualification-v5' and q5['qualification']['hidden_imports']==hidden
assert not any(n.split('.')[0] in {'numpy','torch','torchvision','mujoco'} for n in sys.modules)
for name in (BASE+'-admission.py',BASE+'-external.py'):compile((ROOT/name).read_bytes(),name,'exec')
result=dict(status='PASS_AUTHENTICATED_CONTROL_METADATA_ONLY',pins=len(frame['pins']),pinned_bytes=sum(r['size_bytes'] for r in frame['pins']),
    configuration=dict(size_bytes=len(configraw),sha256=control.CONFIG_SHA),freeze={k:envelope['freeze'][k] for k in ('size_bytes','sha256')},
    compact_configuration_authenticated=True,pretty_manifest_authenticated=True,full_manifest_warm_raw_roles=True,
    prior_amendment02_and_original10_pins_preserved=True,replaced_live_sources_archived=sorted(replaced),
    consumed=dict(qualifications07_10='FAILED_CONSUMED',admission10_01='FAILED_CONSUMED',admission10_02='ADMITTED_CONSUMED_BY_RUNTIME10'),
    qualifier_validate_configuration=True,preparation_relative_changed_source_paths=sorted(changed),
    negative_absence_names=len(negative['names']),hidden_imports_undeclared=hidden,worker_qualification='v5',
    historical_missing_receipts=17,new_helper_paths=6,historical_run_files=102,historical_absent_paths=21,
    closure=dict(fd_before=before,fd_after=after,children=[],threads=[]),
    admission_main_invoked=False,payload_census_or_rehash=False,runtime_invoked=False)
with Path('/tmp/palimpsest-held11-control-selfcheck01.json').open('x') as out:json.dump(result,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(result,sort_keys=True))
