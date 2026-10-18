"""Implement the allocation-16 history helpers (GREEN) by one counted insertion into the RED admission.

Adds runtime14 (accepted import route, consumed), admission14 (consumed by runtime14), preparation03
(accepted, consumed by runtime14, stage retired), the shared retired-stage check, characterization-04
(accepted observation) and preparation04 (bound to the frozen allocation-16 configuration), with
their literal pins computed here from the committed evidence, plus the 21 process identities, the
planned staged totals and the source commit. Reads metadata only; never opens a stage.
"""
from pathlib import Path
import hashlib,json,subprocess,types
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
TARGET='docs/plans/puck-cpu-held-episode-16-admission.py'
RED='fbcbdf8'
P14='docs/reports/puck-cpu-held-qualification-14'
CHAR='docs/reports/puck-cpu-characterization-04'
SOURCE='cbda0d992c12320e2c9bd8a188f89d2c73d9f77e'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
def sha(raw):return hashlib.sha256(raw).hexdigest()
def pin(name):raw=(ROOT/name).read_bytes();return dict(size_bytes=len(raw),sha256=sha(raw))
text=(ROOT/TARGET).read_text();assert text.encode()==git('show',RED+':'+TARGET)
historical14={name:pin(name)['sha256'] for name in ('docs/plans/puck-cpu-held-qualification-14.json',
    'runs/puck-cpu-held-qualification-14-external-cli-transport.json','runs/puck-cpu-held-qualification-14/result.json',
    'runs/puck-cpu-held-qualification-14/supervision.json',P14+'/observations/palimpsest-puck-cpu-held-qualification-14-audit-01.json',
    P14+'/observations/palimpsest-held14-observer-external.json',P14+'/observations/palimpsest-held14-audit-external.json',
    P14+'/tools/palimpsest-held14-post-outcome-observation.json',P14+'/tools/palimpsest-held14-independent-outcome-review.json',
    P14+'/evidence-index.json')}
admission14={P14+'/observations/'+leaf:pin(P14+'/observations/'+leaf) for leaf in ('palimpsest-puck-cpu-held-qualification-14-admission-01.json',
    'palimpsest-held14-admission-external.json','palimpsest-held14-admission-tool-terminal.json','palimpsest-held14-independent-admission-review.json',
    'palimpsest-held14-admission-external.stdout','palimpsest-held14-admission-external.stderr')}
characterization={name:pin(name)['sha256'] for name in (CHAR+'/frozen-configuration.json',CHAR+'/raw/result.json',CHAR+'/outcome-audit-04.json',
    CHAR+'/evidence-index.json',CHAR+'-records/archive-record.json')}
prep03=json.loads((ROOT/'docs/plans/puck-cpu-held-qualification-14.json').read_bytes())['preparation_acceptance']
auditor=types.ModuleType('impl16_auditor');auditor.__file__=str(ROOT/'scripts/audit_puck_cpu_held_runtime.py')
exec(compile((ROOT/'scripts/audit_puck_cpu_held_runtime.py').read_bytes(),auditor.__file__,'exec'),auditor.__dict__)
prep04=json.loads((ROOT/'docs/plans/puck-cpu-held-preparation-04.json').read_bytes())
data={role:json.loads((ROOT/r['path']).read_bytes()) for role,r in prep04['inputs'].items() if role!='generated'}
_,dependency,directories=auditor.plan(prep04,data)
totals=dict(file_count=sum(len(r['files']) for r in dependency['roots']),directory_count=sum(len(d) for d in directories),
    input_bytes=sum(f['size_bytes'] for r in dependency['roots'] for f in r['files']))
assert totals['file_count']==27286 and totals['input_bytes']==1590197452
supervision=json.loads((ROOT/'runs/puck-cpu-held-qualification-14/supervision.json').read_bytes())
runtime14_identities=[(r['pid'],r['start_ticks']) for r in supervision['tracked_processes']]
assert runtime14_identities==[(493563,7246806),(493564,7246807),(493565,7246808)]
BLOCK='''HISTORICAL14_JSON=@H14@
ADMISSION14_PINS=@A14@
CHARACTERIZATION04_JSON=@C04@
PREP03_ACCEPTANCE=@P03@
SOURCE='@SOURCE@'
TOTALS=@TOTALS@
BOOT='7f875223-b4cf-421e-b04d-81e3c1f19460'
# The eighteen attempt-14 identities (runtimes 05-11) plus runtime14's three tracked processes.
PROCESS_IDENTITIES=[(3569912,53431366),(3569913,53431366),(3569914,53431367),(3798021,53913806),(3798022,53913806),(3798023,53913807),(3996069,54384185),(3996070,54384185),(3996071,54384186),(104005,55289090),(104006,55289091),(104007,55289092),(409732,56248873),(409733,56248874),(409734,56248875),(325632,3798844),(325635,3798844),(325642,3798845),(493563,7246806),(493564,7246807),(493565,7246808)]


def check_runtime14(held):
    """Runtime14 completed the held four-import route and its v14 audit passed; it consumed admission14 and preparation03."""
    rows=[]
    for path,expected in HISTORICAL14_JSON.items():
        value,raw=held.json(ROOT/path,maximum=1024**2)
        assert hashlib.sha256(raw).hexdigest()==expected,path
        rows.append(value)
    config,transport,result,supervision,audit,outer_observer,outer_audit,post,review,index=rows
    config_sha=HISTORICAL14_JSON['docs/plans/puck-cpu-held-qualification-14.json']
    transport_sha=HISTORICAL14_JSON['runs/puck-cpu-held-qualification-14-external-cli-transport.json']
    result_sha=HISTORICAL14_JSON['runs/puck-cpu-held-qualification-14/result.json']
    held.file(ROOT/'runs/puck-cpu-held-qualification-14/configuration.json',dict(size_bytes=9048,sha256=config_sha),64*1024)
    assert config['kind']=='puck-cpu-held-runtime-allocation-v14' and config['phase']=='qualify' and config['version']==config['allocation_id']==14
    assert config['root']==str(ROOT) and (config['limits']['normal_seconds'],config['limits']['hard_seconds'])==(360,390)
    assert config['stage_parent']=='/tmp/palimpsest-puck-cpu-held-03' and config['preparation_acceptance']==PREP03_ACCEPTANCE
    python=str(Path(sys.executable).resolve())
    parent_command=[python,'-I','-S','-B',str(ROOT/'scripts/qualify_puck_cpu_held_runtime.py'),
        '--configuration',str(ROOT/'docs/plans/puck-cpu-held-qualification-14.json'),'--sha256',config_sha]
    assert transport['kind']=='puck-cpu-held-cli-transport-v1' and transport['phase']=='qualify' and transport['command']==parent_command
    assert transport['configuration_sha256']==config_sha and transport['observed_returncode']==0 and transport['timed_out'] is False
    assert 0<transport['elapsed_seconds']<400
    streams={}
    for name in ('stdout','stderr'):
        row=transport[name];assert row['path']=='runs/puck-cpu-held-qualification-14-external-cli.'+name
        streams[name]=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
    assert streams['stderr']==b'' and hashlib.sha256(streams['stdout']).hexdigest()==result_sha
    assert result['kind']=='puck-cpu-held-runtime-outcome-v14' and result['status']=='imports_completed' and result['held_four_imports_observed'] is True
    assert result['configuration_sha256']==config_sha and result['version']==result['allocation_id']==14 and 0<result['elapsed_seconds']<360
    assert result['closure']==dict(active_children=[],active_non_main_threads=[],fd_count_after=5,fd_count_before=5)
    assert all(result[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    assert result['qualification_claims']==[] and not {'error','error_type'}&set(result)
    held.file(ROOT/'runs/puck-cpu-held-qualification-14/logs/stdout.log',dict(size_bytes=333922,sha256=result['worker_stdout_sha256']),16*1024**2)
    before,_=held.json(ROOT/'runs/puck-cpu-held-qualification-14/baseline-before.json',maximum=64*1024,lf=True)
    after,_=held.json(ROOT/'runs/puck-cpu-held-qualification-14/baseline-after.json',maximum=64*1024,lf=True)
    assert before==after and before['prefix_manifest_sha256']=='4d54b1dac0283b93ac036029c3cb669022b34a748a7f2bda019809930b5c9886'
    assert supervision['status']=='completed' and supervision['returncode']==0 and supervision['failure'] is None
    assert supervision['process_scope']=='descendants' and supervision['matching_survivors']==[]
    tracked=supervision['tracked_processes']
    assert [(row['pid'],row['start_ticks']) for row in tracked]==PROCESS_IDENTITIES[-3:]
    assert audit['kind']=='puck-cpu-held-runtime-independent-audit-v14' and audit['status']=='PASS' and audit['allocation_id']==14
    assert audit['auditor_source_sha256']=='6292b55088a8b4bfb60b2d65688970cd47e6a76e207f771c3d695dd463bae3cd'
    assert audit['configuration_sha256']==config_sha and audit['transport_sha256']==transport_sha and audit['result_sha256']==result_sha
    assert audit['held_four_imports_observed'] is True and audit['qualification_claims']==[]
    assert all(audit[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    environment=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    observer_command=[python,'-I','-S','-B',str(ROOT/'scripts/observe_puck_cpu_held_allocation.py'),*parent_command[5:]]
    audit_command=[python,'-I','-S','-B',str(ROOT/'scripts/audit_puck_cpu_held_runtime.py'),*parent_command[5:],
        '--transport',str(ROOT/'runs/puck-cpu-held-qualification-14-external-cli-transport.json'),
        '--transport-sha256',transport_sha,'--output','/tmp/palimpsest-puck-cpu-held-qualification-14-audit-01.json']
    audit_sha=HISTORICAL14_JSON['docs/reports/puck-cpu-held-qualification-14/observations/palimpsest-puck-cpu-held-qualification-14-audit-01.json']
    for phase,value,stdout_sha,budget,command in [('observer',outer_observer,transport_sha,440,observer_command),('audit',outer_audit,audit_sha,145,audit_command)]:
        assert value['kind']=='puck-cpu-held14-external-transport-v1' and value['phase']==phase and value['command']==command
        assert value['returncode']==0 and value['normal_exit'] is True and value['timed_out'] is False
        assert value['cwd']==str(ROOT) and value['environment']==environment
        assert value['external_deadline_seconds']==budget and 0<value['elapsed_seconds']<budget and value['stdout']['sha256']==stdout_sha
        assert value['stderr']['size_bytes']==0 and value['implicit_retry'] is False and value['runtime_qualified'] is False
    assert post['status']=='AUDIT_PASS_IMPORT_ROUTE_ONLY' and post['completed_four_import_receipt'] is True and post['runtime_qualified'] is False
    assert post['configuration_sha256']==config_sha and post['observer_invocations']==1 and post['independent_auditor_invocations']==1
    assert post['epoch14_clocks']['registration_deadline_seconds']==360 and post['epoch14_clocks']['imports_below_360'] is True
    assert review['status']=='PASS_IMPORT_ROUTE_OUTCOME_RECORD_ONLY' and review['findings']==[]
    assert index['kind']=='puck-cpu-held-qualification14-terminal-evidence-v1' and index['status']=='AUDIT_PASS_IMPORT_ROUTE_ONLY'
    assert index['control_commit']=='eb34d5c2a66730c248b00229c17ce84e197b3d68' and index['artifact_count']==169
    assert index['post_outcome_sha256']==HISTORICAL14_JSON['docs/reports/puck-cpu-held-qualification-14/tools/palimpsest-held14-post-outcome-observation.json']
    assert index['independent_outcome_review_sha256']==HISTORICAL14_JSON['docs/reports/puck-cpu-held-qualification-14/tools/palimpsest-held14-independent-outcome-review.json']
    return dict(status='ACCEPTED_IMPORT_ROUTE_CONSUMED',configuration_sha256=config_sha,transport_sha256=transport_sha,result_sha256=result_sha,
        completed_four_import_receipt=True,independent_audit_status='PASS',tracked_processes=tracked,runtime_qualified=False,
        parent_elapsed_seconds=result['elapsed_seconds'],consumed=['admission14','preparation03'],
        scope='accepted held four-import route only; no runtime, episode, renderer or study authority')


def check_consumed_admission14(held,admitted):
    names=list(ADMISSION14_PINS);values=[]
    for name in names[:4]:
        row=ADMISSION14_PINS[name]
        value,raw=held.json(ROOT/name,row,maximum=1024**2)
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],name
        values.append(value)
    receipt,external,tool,review=values
    receipt_raw=held.file(ROOT/names[0],ADMISSION14_PINS[names[0]],1024**2,raw=True)
    stdout=held.file(ROOT/names[4],ADMISSION14_PINS[names[4]],1024**2,raw=True)
    stderr=held.file(ROOT/names[5],ADMISSION14_PINS[names[5]],1024**2,raw=True)
    config_sha=HISTORICAL14_JSON['docs/plans/puck-cpu-held-qualification-14.json']
    canonical=(json.dumps(admitted,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\\n').encode()
    assert hashlib.sha256(canonical).hexdigest()==config_sha and stdout==receipt_raw
    assert receipt['kind']=='puck-cpu-held14-data-only-admission-v1' and receipt['status']=='DATA_ONLY_ADMITTED'
    assert receipt['admission_check_id']==1 and receipt['configuration_sha256']==config_sha and receipt['qualification14_invoked'] is False
    assert receipt['source_commit']=='f05bd699af337e44de54584bb334690ec405f994'
    assert receipt['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[])
    assert all(receipt[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    assert receipt['qualification_claims']==[]
    assert external['kind']=='puck-cpu-held14-external-transport-v1' and external['phase']=='admission'
    assert type(external['returncode']) is int and external['returncode']==0
    assert external['normal_exit'] is True and external['timed_out'] is external['implicit_retry'] is False
    assert 0<external['elapsed_seconds']<145 and external['external_deadline_seconds']==145
    assert external['command']==[str(Path(sys.executable).resolve()),'-I','-S','-B',str(ROOT/'docs/plans/puck-cpu-held-qualification-14-admission.py')]
    assert external['environment']==dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    assert external['runtime_qualified'] is external['study_authorized'] is False
    assert external['stdout']['sha256']==hashlib.sha256(stdout).hexdigest() and external['stdout']['size_bytes']==len(stdout)
    assert external['stderr']['sha256']==hashlib.sha256(stderr).hexdigest() and external['stderr']['size_bytes']==len(stderr)
    assert tool['exit_code']==0 and tool['outer_timeout'] is tool['runtime_invoked'] is False and tool['phase']=='admission'
    phases=[json.loads(line) for line in stderr.splitlines()]
    assert [row['phase'] for row in phases]==['controls/plans','SITEhash','hostbaseline/native','forest1','forest2','finalSITEcensus','fullrecheck','close/publication']
    assert all(row['kind']=='held14-data-admission-phase-v1' and row['check_id']==14 for row in phases)
    assert review['decision']=='GO' and review['findings']==[]
    # Consumed: the sole runtime14 followed this admission; check_runtime14 binds its accepted outcome.
    assert os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-14/result.json')
    return dict(status='ADMITTED_CONSUMED_BY_RUNTIME14',configuration_sha256=config_sha,
        receipt_sha256=hashlib.sha256(receipt_raw).hexdigest(),review_decision='GO',phases=len(phases),
        peak_held_files=phases[-2]['held']['files'],current_admission_authority=False,
        scope='genuine historical admission14 metadata only; grants no admission16')


def check_retired_stage(held,stage,result_sha):
    """A consumed stage retired by retire-consumed-stages.py on this boot; the stage itself is only checked absent."""
    value,raw=held.json(ROOT/RETIREMENT,maximum=64*1024)
    assert hashlib.sha256(raw).hexdigest()==RETIREMENT_SHA
    assert value['kind']=='palimpsest-prep04-consumed-stage-retirement-v1' and value['boot_id']==BOOT
    rows=[row for row in value['stages'] if row['path']==stage]
    assert len(rows)==1 and rows[0]['status']=='RETIRED' and rows[0]['result_sha256']==result_sha,stage
    census=rows[0]['census'];identity=rows[0]['identity']
    assert census['files']==27255 and census['file_bytes']==1318494346 and census['other']==census['symlinks']==0
    assert identity['exists'] is True and identity['directory'] is True and identity['path']==stage
    assert value['census']['path']=='runs/palimpsest-prep04-tools/retire-consumed-stages-census.json'
    assert not os.path.lexists(stage),stage
    return dict(status='RETIRED',stage_parent=stage,identity=identity,census_sha256=census['census_sha256'],
        census_record_sha256=value['census']['sha256'],retirement_record_sha256=RETIREMENT_SHA)


def check_preparation03_consumed(held):
    """Accepted preparation03 bound runtime14; its stage was retired after a recorded census and is never opened."""
    values={}
    for role,row in PREP03_ACCEPTANCE.items():
        value,raw=held.json(ROOT/row['path'],row,1024**2)
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],role
        values[role]=value
    config,result,audit,cli=(values[k] for k in ('configuration','result','independent_audit','externally_observed_auditor_cli'))
    assert config['kind']=='puck-cpu-held-runtime-allocation-v13' and config['stage_parent']=='/tmp/palimpsest-puck-cpu-held-03'
    assert result['kind']=='puck-cpu-held-runtime-outcome-v13' and result['status']=='prepared' and result['stage_parent']==config['stage_parent']
    assert result['staged_roots']==[dict(device=55,inode=43194+index,root_index=index) for index in range(4)]
    assert audit['kind']=='puck-cpu-held-runtime-independent-audit-v13' and audit['status']=='PASS' and audit['allocation_id']==13
    assert audit['auditor_source_sha256']=='6292b55088a8b4bfb60b2d65688970cd47e6a76e207f771c3d695dd463bae3cd'
    assert cli['kind']=='externally-observed-cpu-auditor-cli-v1' and cli['observed_returncode']==0
    # Consumed: runtime14 bound exactly these pins (check_runtime14 asserts its configuration carries them).
    assert os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-14/result.json')
    retired=check_retired_stage(held,config['stage_parent'],PREP03_ACCEPTANCE['result']['sha256'])
    return dict(status='ACCEPTED_CONSUMED_BY_RUNTIME14_STAGE_RETIRED',configuration_sha256=PREP03_ACCEPTANCE['configuration']['sha256'],
        result_sha256=PREP03_ACCEPTANCE['result']['sha256'],stage_parent=config['stage_parent'],staged_roots=result['staged_roots'],
        retirement=retired,scope='accepted preparation03 metadata; its stage was retired after a recorded identity and content census')


def check_characterization04(held,prep):
    """Accepted characterization-04 observation: the archive preparation04 binds, its PASS audit and archive record."""
    rows=[]
    for path,expected in CHARACTERIZATION04_JSON.items():
        value,raw=held.json(ROOT/path,maximum=1024**2)
        assert hashlib.sha256(raw).hexdigest()==expected,path
        rows.append(value)
    frozen,result,audit,index,record=rows;pins=prep['inputs']
    for role,path in (('observation_configuration','frozen-configuration.json'),('observation_result','raw/result.json'),
            ('observation_audit','outcome-audit-04.json'),('observation_index','evidence-index.json')):
        assert pins[role]['path']=='docs/reports/puck-cpu-characterization-04/'+path and pins[role]['sha256']==CHARACTERIZATION04_JSON[pins[role]['path']],role
    assert frozen['kind']=='puck-cpu-runtime-characterization-v3' and frozen['version']==3 and frozen['sources']==prep['sources']
    assert result['kind']=='puck-cpu-characterization-outcome-v3' and result['status']=='observed' and not {'error','error_type'}&set(result)
    assert result['process_creation_attempts']==0 and result['ticks_completed']==48 and 0<result['elapsed_seconds']<360
    assert result['replay']['status']=='passed' and result['replay']['compared_ticks']==48 and result['replay']['first_divergence'] is None
    assert all(result[key] is False for key in ('collection_authorized','executable','native_authorized','runtime_qualified','study_authorized'))
    assert audit['kind']=='cpu-episode-characterization-outcome-audit-v1' and audit['status']=='PASS'
    assert audit['auditor_source_sha256']=='1608a3d79a2ebb10723023b25c054401bbd598b2e95508422b1e6bfaa2efac46'
    assert audit['verified']['configuration_sha256']==pins['observation_configuration']['sha256']
    assert audit['verified']['result_sha256']==pins['observation_result']['sha256']
    assert audit['verified']['source_report_sha256']==pins['observation_report']['sha256']==result['source_report_sha256']
    assert audit['verified']['replay_report_sha256']==pins['observation_replay_report']['sha256']==result['replay_report_sha256']
    assert index['kind']=='cpu-episode-characterization-evidence-index-v1' and index['file_count']==len(index['entries'])==27
    assert record['status']=='PASS_ARCHIVED_AND_BOUND' and record['error'] is None and record['boot_id']==BOOT
    assert record['index']['sha256']==pins['observation_index']['sha256'] and record['binding']['undeclared_import_misses']==0
    return dict(status='ACCEPTED_OBSERVATION',configuration_sha256=pins['observation_configuration']['sha256'],
        result_sha256=pins['observation_result']['sha256'],audit_sha256=pins['observation_audit']['sha256'],
        ticks_completed=48,process_creation_attempts=0,undeclared_import_misses=0,replay=result['replay'],
        scope='accepted unguarded characterization-04 observation only; no runtime or episode authority')


def check_preparation04(held,m,prior,prepared):
    """Accepted preparation04 metadata exactly as allocation 16 binds it; its staged forest is re-hashed separately by forest()."""
    config,configraw=held.json(ROOT/PREP_CONFIGURATION,maximum=1024**2,lf=True)
    assert m.sha(configraw)==PREP_SHA and config==prior;m.configuration(config,False)
    assert config['root']==str(ROOT) and config['phase']=='prepare' and config['stage_parent']==PREP_STAGE and config['version']==15
    assert m.preparation_output(config)==PREP_OUTPUT
    prepbase=ROOT/PREP_OUTPUT
    prep,prepraw=held.json(prepbase/'result.json',maximum=1024**2,lf=True)
    assert m.sha(prepraw)==RESULT_SHA and prep==prepared;m.outcome(prep,config,PREP_SHA)
    assert prep['staged_roots']==PREP_ROOTS and prep['dependencies']['sha256']==DEP_SHA
    assert held.file(prepbase/'configuration.json',maximum=1024**2,raw=True)==configraw
    names=m.PREPARATION04_SOURCES;rows={r['path']:r for r in config['sources']}
    assert [r['path'] for r in config['sources']]==list(names) and not os.path.lexists(prepbase/'worker-source')
    for name in names:held.file(prepbase/'parent-source'/name,rows[name],1024**2)
    return config,configraw,prep,prepraw,dict(status='ACCEPTED_PREPARATION04',configuration_sha256=PREP_SHA,result_sha256=RESULT_SHA,
        dependencies_sha256=DEP_SHA,stage_parent=PREP_STAGE,staged_roots=PREP_ROOTS,capsule_files=len(names),
        scope='accepted preparation metadata only; staged bytes re-hashed by forest')


'''
block=(BLOCK.replace('@H14@',repr(historical14)).replace('@A14@',repr(admission14)).replace('@C04@',repr(characterization))
    .replace('@P03@',repr(prep03)).replace('@SOURCE@',SOURCE).replace('@TOTALS@',repr(totals)))
anchor='UNEXECUTED11='
assert text.count(anchor)==1
text=text.replace(anchor,block+anchor)
compile(text,TARGET,'exec')
(ROOT/TARGET).write_text(text)
print(json.dumps(dict(path=TARGET,size_bytes=len(text.encode()),sha256=sha(text.encode()),inserted_before=anchor,
    historical14=len(historical14),admission14=len(admission14),characterization04=len(characterization),totals=totals,
    process_identities=21,admission_invoked=False,stages_touched=False),indent=2,sort_keys=True))
