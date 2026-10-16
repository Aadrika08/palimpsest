from pathlib import Path
import hashlib,json
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE=ROOT/'docs/plans/puck-cpu-held-qualification-10-admission-amendment-02'
path=BASE/'admission.py';text=path.read_text()
assert 'def check_consumed_admission01' not in text
prefix='docs/reports/puck-cpu-held-qualification-10-admission-01/observations/'
names=['docs/plans/puck-cpu-held-qualification-10.json',
    'docs/reports/puck-cpu-held-qualification-10-admission-01/outcome.json',
    prefix+'palimpsest-held10-admission-external.json',prefix+'palimpsest-held10-admission-tool-terminal.json',
    prefix+'palimpsest-held10-admission-external.stderr',prefix+'palimpsest-held10-admission-external.stdout']
pins={name:dict(size_bytes=(ROOT/name).stat().st_size,sha256=hashlib.sha256((ROOT/name).read_bytes()).hexdigest()) for name in names}
block='ADMISSION01_PINS='+repr(pins)+'\n\n'
block+='''def check_consumed_admission01(held,current):
    values=[]
    # The old pretty config is immutable historical data, not the new input.
    for name in list(ADMISSION01_PINS)[:4]:
        row=ADMISSION01_PINS[name]
        value,raw=held.json(ROOT/name,row,maximum=1024**2)
        assert len(raw)==row['size_bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256'],name
        values.append(value)
    previous,outcome,external,tool=values
    assert previous==current
    assert outcome['status']=='DATA_ADMISSION_FAILED_CONSUMED' and outcome['admission_invocations']==1
    assert outcome['control_commit']=='b3d50f5d8efbd36c56337c323d66768831c0f43f'
    assert outcome['source_commit']=='e723db037ed1f790c2618798d59f56913054754f'
    assert outcome['actual_runtime10_invoked'] is outcome['full_payload_custody'] is False
    assert external['kind']=='puck-cpu-held10-external-transport-v1' and external['phase']=='admission'
    assert type(external['returncode']) is int and external['returncode']==1
    assert external['normal_exit'] is True and external['timed_out'] is external['implicit_retry'] is False
    assert 0<external['elapsed_seconds']<145 and external['external_deadline_seconds']==145
    assert external['command']==[str(Path(sys.executable).resolve()),'-I','-S','-B',str(ROOT/'docs/plans/puck-cpu-held-qualification-10-admission.py')]
    assert external['environment']==dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    assert external['runtime_qualified'] is external['study_authorized'] is False
    assert tool['exit_code']==1 and tool['outer_timeout'] is tool['runtime_invoked'] is False
    assert 0<tool['elapsed_seconds']<155
    stderr_name,stdout_name=list(ADMISSION01_PINS)[4:]
    stderr=held.file(ROOT/stderr_name,ADMISSION01_PINS[stderr_name],1024**2,raw=True)
    stdout=held.file(ROOT/stdout_name,ADMISSION01_PINS[stdout_name],1024**2,raw=True)
    assert stdout==b'' and hashlib.sha256(stderr).hexdigest()==external['stderr']['sha256']
    failure=json.loads(stderr.splitlines()[0])
    assert failure['kind']=='held10-data-admission-failure-v1' and failure['check_id']==10 and failure['status']=='FAIL'
    assert failure['error_type']=='ValueError' and failure['error']=='Canonical JSON bytes differ: '+str(ROOT/'docs/plans/puck-cpu-held-qualification-10.json')
    assert failure['closure']==dict(fd_count_before=4,fd_count_after=4,active_children=[],active_non_main_threads=[],held_close_completed=True,scope='current process observations only')
    assert not os.path.lexists('/tmp/palimpsest-puck-cpu-held-qualification-10-admission-01.json')
    assert not os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-10')
    return dict(status='FAILED_CONSUMED',actual_runtime10_invoked=False,full_payload_custody=False,
        failure='canonical configuration bytes',scope='genuine historical admission01 metadata only')


'''
anchor='def resources('
assert text.count(anchor)==1
text=text.replace(anchor,block+anchor)
text=text.replace('raw_paths.update(HISTORICAL09_JSON)','raw_paths.update(HISTORICAL09_JSON)\n            raw_paths.update(ADMISSION01_PINS)')
text=text.replace("hold_manifest(held,manifest['pins'],raw_paths)","hold_manifest(held,manifest['pins'],raw_paths)\n            consumed_admission01=check_consumed_admission01(held,frozen)")
text=text.replace('qualification10_invoked=False,','qualification10_invoked=False,admission_check_id=2,admission01_failed_consumed=True,admission01_failure=consumed_admission01,')
compile(text,str(path),'exec');path.write_text(text)
print(json.dumps(dict(preserved_admission01_metadata_paths=len(pins),new_admission_or_runtime_invoked=False)))
