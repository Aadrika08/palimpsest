"""Use authenticated metadata readers; never run admission, payloads or vendors."""
from pathlib import Path
import hashlib,json,os,sys,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE=ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
def module(path):
    value=types.ModuleType('held10_amendment02_'+path.stem);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
control=module(BASE/'admission.py')
authraw=control.AUDITOR.read_bytes()
assert len(authraw)==65522 and hashlib.sha256(authraw).hexdigest()==control.AUDITOR_SHA
auth=module(control.AUDITOR)
envelope=json.loads((BASE/'execution.json').read_bytes())
before=len(os.listdir('/proc/self/fd'));held=auth.Held(time.monotonic()+60)
try:
    config,configraw=held.json(control.CONFIGURATION,dict(size_bytes=8988,sha256=control.CONFIG_SHA),1024**2,lf=True)
    frame,frameraw=held.json(BASE/'freeze.json',envelope['freeze'],1024**2)
    assert frameraw==(json.dumps(frame,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    assert frame['kind']=='puck-cpu-held-qualification10-admission02-controls-v1' and frame['admission_check_id']==2
    assert frame['admission01_failed_consumed'] is True and frame['admission02_invoked_at_freeze'] is False
    current=control.module(held,ROOT/'scripts/audit_puck_cpu_held_runtime.py',control.AUDITOR_CURRENT_SHA)
    current.configuration(config,False)
    roles={row['path'] for row in config['inputs'].values()}
    roles.update(row['path'] for row in config['preparation_acceptance'].values())
    roles.add('docs/plans/puck-cpu-observed-import-profile-candidate-01.json')
    roles.update('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json' for i in range(1,7))
    for rows in (control.HISTORICAL07_JSON,control.HISTORICAL08_JSON,control.HISTORICAL09_JSON,control.ADMISSION01_PINS):roles.update(rows)
    control.hold_manifest(held,frame['pins'],roles)
    assert control.check_consumed_admission01(held,config)['status']=='FAILED_CONSUMED'
    for epoch in ('07','08','09'):assert getattr(control,'check_consumed'+epoch)(held)['status']=='FAILED_CONSUMED'
    old=json.loads((ROOT/'docs/plans/puck-cpu-held-qualification-10-freeze.json').read_bytes())
    roster={r['path']:r for r in frame['pins']}
    assert len(roster)==len(frame['pins']) and all(roster[row['path']]==row for row in old['pins'])
    previous,previousraw=held.json(ROOT/'docs/plans/puck-cpu-held-preparation-01.json',maximum=1024**2,lf=True)
    prepared,_=held.json(ROOT/'runs/puck-cpu-held-preparation-01/result.json',maximum=1024**2,lf=True)
    current.preparation_epoch(config,previous,prepared)
    prior_candidate=json.loads((ROOT/previous['inputs']['candidate']['path']).read_bytes())
    candidate=json.loads((ROOT/config['inputs']['candidate']['path']).read_bytes())
    current.publication_candidate(prior_candidate,candidate,pillow_origins=True)
    assert control.absent()['historical_missing_receipts']==16
    for phase in envelope['phase_outputs'].values():assert all(not os.path.lexists(p) for p in phase.values())
    assert all(not os.path.lexists(envelope[k]) for k in ('admission_output','auditor_output','concrete_audit_command_path'))
    for row in (envelope['wrapper'],):
        raw=Path(row['path']).read_bytes()
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
        assert raw==(ROOT/row['tracked_copy']).read_bytes()
    held.recheck();held.clock()
finally:held.close()
after=len(os.listdir('/proc/self/fd'))
assert before==after and not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split()
assert len(os.listdir('/proc/self/task'))==1
assert not any(n.split('.')[0] in {'numpy','torch','torchvision','mujoco'} for n in sys.modules)
result=dict(status='PASS_AUTHENTICATED_CONTROL_METADATA_ONLY',pins=len(frame['pins']),pinned_bytes=sum(r['size_bytes'] for r in frame['pins']),
    compact_configuration_authenticated=True,pretty_manifest_authenticated=True,full_manifest_warm_raw_roles=True,
    prior_1998_pins_preserved=True,admission01_failed_consumed=True,closure=dict(fd_before=before,fd_after=after,children=[],threads=[]),
    admission_main_invoked=False,payload_census_or_rehash=False,runtime_invoked=False)
with Path('/tmp/palimpsest-held10-amendment02-control-selfcheck01.json').open('x') as out:json.dump(result,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(result,sort_keys=True))
