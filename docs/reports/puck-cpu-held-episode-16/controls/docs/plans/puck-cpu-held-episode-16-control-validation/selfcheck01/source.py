"""Use authenticated metadata readers; never run admission main, census, payloads, vendors, or touch the preparation04 stage."""
from pathlib import Path
import hashlib,json,os,subprocess,sys,time,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE='docs/plans/puck-cpu-held-episode-16'
def module(path):
    value=types.ModuleType('held16_selfcheck_'+path.stem);value.__file__=str(path)
    exec(compile(path.read_bytes(),str(path),'exec'),value.__dict__);return value
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
control=module(ROOT/(BASE+'-admission.py'))
authraw=control.AUDITOR.read_bytes();assert hashlib.sha256(authraw).hexdigest()==control.AUDITOR_SHA
auth=module(control.AUDITOR)
envelope=json.loads((ROOT/(BASE+'-execution.json')).read_bytes())
before=len(os.listdir('/proc/self/fd'));held=auth.Held(time.monotonic()+90)
try:
    config,configraw=held.json(control.CONFIGURATION,dict(size_bytes=control.CONFIGURATION.stat().st_size,sha256=control.CONFIG_SHA),1024**2,lf=True)
    frame,frameraw=held.json(ROOT/(BASE+'-freeze.json'),envelope['freeze'],1024**2)
    assert frameraw==(json.dumps(frame,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
    assert frame['kind']=='puck-cpu-held-episode16-frozen-controls-v1' and frame['source_commit']==envelope['source_commit']==control.SOURCE
    assert frame['actual16_invoked_at_freeze'] is frame['actual16_admission_invoked_at_freeze'] is False
    assert frame['runtime14_accepted_import_route_consumed'] is frame['admission14_admitted_consumed_by_runtime14'] is True
    assert frame['qualifications01_02_03_04_05_06_07_08_09_10_11_failed_consumed'] is True
    assert frame['attempt11_d83dab3']['status']=='NO_GO_NEVER_INVOKED' and frame['preparation01_superseded']['required'] is False
    assert frame['preparation02']['status']=='ACCEPTED_CONSUMED_BY_RUNTIME11_STAGE_RETIRED'
    assert frame['preparation03']['status']=='ACCEPTED_CONSUMED_BY_RUNTIME14_STAGE_RETIRED'
    episode_auditor=control.module(held,ROOT/'scripts/audit_puck_cpu_held_episode.py',control.EPISODE_AUDITOR_SHA)
    episode=control.module(held,ROOT/'scripts/run_puck_cpu_held_episode.py',control.EPISODE_PARENT_SHA)
    qrow=next(r for r in config['sources'] if r['path']=='scripts/qualify_puck_cpu_held_runtime.py');q=control.module(held,ROOT/qrow['path'],qrow['sha256'])
    acceptance={role:held.file(ROOT/row['path'],row,16*1024**2,raw=True) for role,row in config['preparation_acceptance'].items()}
    episode.validate_configuration(config,q);prior,prepared=episode.validate_acceptance(config,acceptance,q)
    episode_auditor.validate_configuration(config,prior);episode_auditor.validate_acceptance(config,episode_auditor.Reader(time.monotonic()+60))
    roles={row['path'] for row in config['inputs'].values()}|{row['path'] for row in config['preparation_acceptance'].values()}
    roles.update('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json' for i in range(1,7))
    for rows in (control.HISTORICAL07_JSON,control.HISTORICAL08_JSON,control.HISTORICAL09_JSON,control.HISTORICAL10_JSON,control.HISTORICAL11_JSON,
            control.HISTORICAL14_JSON,control.ADMISSION01_PINS,control.ADMISSION02_PINS,control.ADMISSION11B_PINS,control.ADMISSION14_PINS,
            control.CHARACTERIZATION04_JSON):roles.update(rows)
    roles.update(row['path'] for row in control.PREP02_ACCEPTANCE.values());roles.update(row['path'] for row in control.PREP03_ACCEPTANCE.values())
    roles.add(control.RETIREMENT)
    roles.update(packet+'/evidence-index.json' for packet in frame['evidence_index_binding']['packets'])
    control.hold_manifest(held,frame['pins'],roles)
    admitted10,_=held.json(ROOT/control.ADMITTED10_CONFIGURATION,dict(size_bytes=8988,sha256=control.HISTORICAL10_JSON[control.ADMITTED10_CONFIGURATION]),1024**2,lf=True)
    assert control.check_consumed_admission01(held,admitted10)['status']=='FAILED_CONSUMED'
    assert control.check_consumed_admission02(held,admitted10)['status']=='ADMITTED_CONSUMED_BY_RUNTIME10'
    for epoch in ('07','08','09','10','11'):assert getattr(control,'check_consumed'+epoch)(held)['status']=='FAILED_CONSUMED'
    admitted11,_=held.json(ROOT/'docs/plans/puck-cpu-held-qualification-11.json',dict(size_bytes=9048,sha256=control.HISTORICAL11_JSON['docs/plans/puck-cpu-held-qualification-11.json']),1024**2,lf=True)
    assert control.check_consumed_admission11b(held,admitted11)['status']=='ADMITTED_CONSUMED_BY_RUNTIME11'
    runtime14=control.check_runtime14(held);assert runtime14['status']=='ACCEPTED_IMPORT_ROUTE_CONSUMED'
    admitted14,_=held.json(ROOT/'docs/plans/puck-cpu-held-qualification-14.json',dict(size_bytes=9048,sha256=control.HISTORICAL14_JSON['docs/plans/puck-cpu-held-qualification-14.json']),1024**2,lf=True)
    admission14=control.check_consumed_admission14(held,admitted14);assert admission14['status']=='ADMITTED_CONSUMED_BY_RUNTIME14'
    preparation02=control.check_preparation02_consumed(held);preparation03=control.check_preparation03_consumed(held)
    assert preparation02['retirement']['status']==preparation03['retirement']['status']=='RETIRED'
    prep04,prep04raw,prep,prepraw,preparation04=control.check_preparation04(held,auth,prior,prepared)
    characterization04=control.check_characterization04(held,prep04)
    unexecuted=control.check_unexecuted11(held);empty=control.check_empty_directories();preparation01=control.record_preparation01()
    assert preparation04['status']=='ACCEPTED_PREPARATION04' and unexecuted['status']=='NEVER_INVOKED' and empty['directories']==46
    roster={r['path']:r for r in frame['pins']}
    assert len(roster)==len(frame['pins'])==2128
    # Every attempt-14 pin is retained, replaced by its archived f05bd69 copy, or bound through its packet's evidence index.
    old=json.loads((ROOT/'docs/plans/puck-cpu-held-qualification-14-freeze.json').read_bytes())
    replaced={row['historical_live_path']:row for row in frame['historical14_replaced_live_sources']}
    bound=frame['evidence_index_binding']['packets'];index_bound=0
    for row in old['pins']:
        if row['path'] in roster and (roster[row['path']]==row or row['path'] in replaced):continue
        packet=next(p for p in bound if row['path'].startswith(p+'/'))
        index=json.loads(held.file(ROOT/(packet+'/evidence-index.json'),bound[packet]['index'],16*1024**2,raw=True))
        listed={r['archived_path']:r for r in index['artifacts']}[row['path'][len(packet)+1:]]
        assert (listed['size_bytes'],listed['sha256'])==(row['size_bytes'],row['sha256']),row['path'];index_bound+=1
    assert index_bound==frame['evidence_index_binding']['index_bound_pins']==942 and len(replaced)==10
    for row in config['sources']+list(config['inputs'].values())+list(config['preparation_acceptance'].values()):assert roster[row['path']]==row
    prepbase=ROOT/control.PREP_OUTPUT;pblobs={};pdata={}
    for role,row in prep04['inputs'].items():
        pblobs[role]=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
        if role!='generated':pdata[role]=auth.decode(pblobs[role])
    auth.inputs_binding(prep04,pdata,pblobs);source,dependency,directories=auth.plan(prep04,pdata)
    copy,copyraw=held.json(prepbase/'control/copy-registration.json',lf=False);assert copyraw==auth.canonical(source,False)
    for role in ['candidate','layout']:assert held.file(prepbase/('control/'+role+'.json'),maximum=16*1024**2,raw=True)==pblobs[role]
    request,requestraw=held.json(prepbase/'control/stage-request.json',maximum=1024**2,lf=True)
    dep,depraw=held.json(prepbase/'payload/dependencies.json',prep['dependencies'],lf=False)
    assert auth.sha(depraw)==control.DEP_SHA and depraw==auth.canonical(dependency,False)
    stage,stageraw=held.json(prepbase/'payload/stage.json',maximum=1024**2,lf=True);auth.no_authority(stage)
    assert stage['status']=='prepared' and stage['staged_roots']==prep['staged_roots']==control.PREP_ROOTS
    assert held.file(prepbase/'logs/stdout.log',maximum=1024**2,raw=True)==stageraw
    baselines=[held.json(prepbase/name,lf=True)[0] for name in ('baseline-before.json','baseline-after.json')];assert baselines[0]==baselines[1]
    observed,_=held.json(prepbase/'supervision.json',maximum=1024**2,lf=True);auth.supervision(observed,'prepare')
    command=[auth.PYTHON,'-I','-S','-B','/puck/source/scripts/stage_puck_cpu_held_runtime.py',auth.sha(requestraw)]
    invocation,_=held.json(prepbase/'invocation.json',maximum=1024**2,lf=True)
    assert invocation==dict(command=auth.namespace_command(prep04,pdata,'prepare',command),configuration_sha256=control.PREP_SHA)
    episode.require_declared_misses(pdata['candidate'])
    negative=control.check_absences(dependency,directories,config['negative_imports'])
    totals=dict(file_count=sum(len(r['files']) for r in dependency['roots']),directory_count=sum(len(d) for d in directories),
        input_bytes=sum(f['size_bytes'] for r in dependency['roots'] for f in r['files']))
    assert totals==control.TOTALS
    absence=control.absent()
    assert absence['historical_missing_receipts']==19 and len(absence['new_paths'])==6
    history=json.loads((ROOT/(BASE+'-control-validation/historical-before-admission.json')).read_bytes())
    assert len(history['raw_run_files'])==151 and all(roster[row['path']]==row for row in history['raw_run_files'])
    assert len(history['historical_absent_paths'])==23 and all(not os.path.lexists(ROOT/p) for p in history['historical_absent_paths'])
    assert (len(history['preparation04_run_files']),len(history['preparation03_run_files']),len(history['preparation02_run_files']),len(history['characterization04_run_files']))==(114,51,51,40)
    for row in history['preparation04_run_files']+history['preparation03_run_files']+history['preparation02_run_files']+history['characterization04_run_files']:
        raw=(ROOT/row['path']).read_bytes();assert (len(raw),hashlib.sha256(raw).hexdigest())==(row['size_bytes'],row['sha256']),row['path']
    assert history['historical_empty_directories']==control.EMPTY_DIRECTORIES and history['attempt11_d83dab3_absent_outputs']==control.UNEXECUTED11['outputs']
    assert history['retired_stage_paths']==['/tmp/palimpsest-puck-cpu-held-02','/tmp/palimpsest-puck-cpu-held-03']
    for row in frame['attempt11_d83dab3']['git_files']:
        raw=subprocess.check_output(['git','-C',str(ROOT),'show',frame['attempt11_d83dab3']['control_commit']+':'+row['path']])
        assert (len(raw),hashlib.sha256(raw).hexdigest())==(row['size_bytes'],row['sha256']),row['path']
    for phase in envelope['phase_outputs'].values():assert all(not os.path.lexists(p) for p in phase.values())
    assert all(not os.path.lexists(envelope[k]) for k in ('admission_output','auditor_output','concrete_audit_command_path'))
    assert envelope['admission_output']==str(control.OUTPUT) and envelope['auditor_output']==frame['commands']['auditor_output']
    assert envelope['stage_guard']['staged_roots']==control.PREP_ROOTS and envelope['stage_guard']['boot_id']==frame['preparation04']['boot_id']==control.BOOT
    assert envelope['normal_external_caps_seconds']==dict(admission=145,audit=330,observer=1300)
    assert envelope['outer_term_seconds']==dict(admission=155,audit=340,observer=1310) and envelope['commands']['observer'][3]=='1310s'
    assert frame['commands']['observer'][4]==str(ROOT/'scripts/observe_puck_cpu_held_allocation.py') and frame['commands']['auditor_prefix'][4]==str(ROOT/'scripts/audit_puck_cpu_held_episode.py')
    for row in (envelope['wrapper'],):
        raw=Path(row['path']).read_bytes()
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'] and raw==(ROOT/row['tracked_copy']).read_bytes()
    held_counts=dict(files=len(held.files),directories=len(held.dirs),links=len(held.links),bytes=held.total)
    held.recheck();held.clock()
finally:held.close()
after=len(os.listdir('/proc/self/fd'))
assert before==after and not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split() and len(os.listdir('/proc/self/task'))==1
observer=module(ROOT/'scripts/observe_puck_cpu_held_allocation.py')
assert observer.EPISODE_SECONDS==(1260,1275) and observer.CLEANUP_SECONDS==5 and observer.EPISODE_OUTPUT=='runs/puck-cpu-held-episode-16'
assert (config['limits']['normal_seconds'],config['limits']['child_hard_seconds'],config['limits']['hard_seconds'])==(1200,1215,1230)
assert episode.WORKER_SECONDS==episode_auditor.WORKER_SECONDS==600 and episode_auditor.TRANSPORT_SECONDS==1260
assert config['negative_imports']==episode.NEGATIVE_IMPORTS==q.EPISODE_NEGATIVE_IMPORTS and config['hidden_imports']==episode.HIDDEN_IMPORTS==q.EPISODE_HIDDEN_IMPORTS
files=[r for r in config['sources'] if r['path'] in q.EPISODE_WORKER_SOURCES];bootstrap=(ROOT/'scripts/puck_worker_bootstrap.py').read_bytes()
registrations={}
for phase in ('source','replay'):
    value,raw,command=episode.registration(config,phase,files,depraw,bootstrap,q)
    independent,independent_raw,_=episode_auditor.registration(config,phase,files,depraw,bootstrap)
    assert raw==independent_raw and value['deadline_seconds']==600 and value['episode']['run_ids']==config['run_ids'] and value['episode']['phase']==phase
    registrations[phase]=hashlib.sha256(raw).hexdigest()
assert not any(n.split('.')[0] in {'numpy','torch','torchvision','mujoco','gymnasium'} for n in sys.modules)
for name in (BASE+'-admission.py',BASE+'-external.py'):compile((ROOT/name).read_bytes(),name,'exec')
result=dict(status='PASS_AUTHENTICATED_CONTROL_METADATA_ONLY',pins=len(frame['pins']),pinned_bytes=sum(r['size_bytes'] for r in frame['pins']),
    configuration=dict(size_bytes=len(configraw),sha256=control.CONFIG_SHA),freeze={k:envelope['freeze'][k] for k in ('size_bytes','sha256')},
    compact_configuration_authenticated=True,pretty_manifest_authenticated=True,full_manifest_warm_raw_roles=True,
    attempt14_pins_retained_replaced_or_index_bound=dict(replaced_live_sources=len(replaced),index_bound=index_bound),
    episode_parent_validators=True,episode_auditor_validators=True,run_ids=config['run_ids'],
    consumed=dict(qualifications07_11='FAILED_CONSUMED',admission10_01='FAILED_CONSUMED',admission10_02='ADMITTED_CONSUMED_BY_RUNTIME10',
        admission11b='ADMITTED_CONSUMED_BY_RUNTIME11',runtime14=runtime14['status'],admission14=admission14['status']),
    preparation04=dict(status=preparation04['status'],registration_invocation_receipts='MATCH',capsule_files=preparation04['capsule_files']),
    preparation03=preparation03['status'],preparation02=preparation02['status'],preparation01=preparation01['status'],
    characterization04=characterization04['status'],attempt11_d83dab3=unexecuted['status'],d83dab3_git_files=len(frame['attempt11_d83dab3']['git_files']),
    historical_empty_directories=empty['directories'],negative_absence_names=len(negative['names']),hidden_imports=config['hidden_imports'],
    episode16=dict(limits=config['limits'],worker_deadline_seconds=600,registration_sha256=registrations,parent_and_auditor_registrations_equal=True,
        observer_seconds=list(observer.EPISODE_SECONDS),wrapper_seconds=envelope['normal_external_caps_seconds'],outer_term_seconds=envelope['outer_term_seconds']),
    totals=totals,held_metadata_only=held_counts,historical_missing_receipts=19,new_helper_paths=6,historical_run_files=151,historical_absent_paths=23,
    preparation04_run_files=114,preparation03_run_files=51,preparation02_run_files=51,characterization04_run_files=40,
    closure=dict(fd_before=before,fd_after=after,children=[],threads=[]),
    admission_main_invoked=False,payload_census_or_rehash=False,episode_invoked=False,stages_touched=False)
with Path('/tmp/palimpsest-held16-control-selfcheck01.json').open('x') as out:json.dump(result,out,indent=2,sort_keys=True);out.write('\n')
print(json.dumps(result,sort_keys=True))
