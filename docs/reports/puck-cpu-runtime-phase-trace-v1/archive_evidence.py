"""Retain source validation; never invoke a test, helper or runtime allocation."""
from pathlib import Path
import datetime
import hashlib
import json
import subprocess

ROOT=Path('/home/utkarsh/Work/shraddha/brain/.worktrees/puck-cpu-runtime-phase-trace-v1')
PACKET=ROOT/'docs/reports/puck-cpu-runtime-phase-trace-v1'
CORE=['tests/test_puck_cpu_phase_trace.py','tests/test_puck_worker_bootstrap.py',
      'tests/test_puck_cpu_runtime_entry.py','tests/test_puck_held_runtime_entry.py']
CONSUMERS=['tests/test_puck_worker_dependencies.py','tests/test_puck_expected_missing_imports.py',
    'tests/test_puck_cpu_optional_import_contract.py','tests/test_puck_cpu_held_parent.py',
    'tests/test_puck_cpu_held_runtime_audit.py','tests/test_puck_cpu_held_observer.py']
INTEGRATIONS=['tests/test_puck_cpu_held_amendment05_integration.py',
    'tests/test_puck_cpu_held_amendment06_integration.py','tests/test_puck_cpu_held_amendment07_integration.py']


def main():
    assert not PACKET.exists()
    terminal=json.loads(Path('/tmp/palimpsest-phase-trace-publication-terminal.json').read_bytes())
    assert terminal['exit_code']==0 and terminal['pytest_result'].startswith('3 passed in ')
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    batches=[
        ('baseline-01',90,False,CORE[1:3],0,'62a516','52 passed in 23.68s'),
        ('red-01',90,False,CORE[:1],1,'f24fc5','13 failed, 2 passed in 26.19s'),
        ('cancel-red-01',30,False,[CORE[0]+'::test_trace_cancellation_is_not_swallowed_and_closes_owned_holders'],1,'f7e9a3','1 failed in 1.75s'),
        ('green-01',90,False,CORE,1,'671723','1 failed, 80 passed in 57.12s'),
        ('private-root-diagnostic-01',30,True,CORE[3:],0,'6ee8da','13 passed in 9.96s'),
        ('green-02',120,True,CORE,0,'400f69','85 passed in 65.00s'),
        ('reentrant-red-01',30,True,[CORE[0]+'::test_successful_outer_write_cannot_rearm_a_nested_trace_failure'],1,'034147','1 failed in 1.71s'),
        ('green-03',120,True,CORE,0,'3158e7','86 passed in 66.08s'),
        ('consumers-01',240,False,CONSUMERS+INTEGRATIONS,1,'7650a1','4 failed, 127 passed in 72.25s'),
        ('private-consumers-02',180,True,CORE+CONSUMERS,0,'733a2f','214 passed in 119.86s'),
        ('publication-integrations-02',120,False,INTEGRATIONS,0,terminal['chunk_id'],terminal['pytest_result']),
    ]
    pairs={};validation=[]
    def add(original,name):
        assert name not in pairs and not Path(name).is_absolute() and '..' not in Path(name).parts
        pairs[name]=Path(original)
    source_paths=['scripts/puck_worker_bootstrap.py','src/palimpsest/puck_runtime_qualification.py',
                  'tests/test_puck_cpu_phase_trace.py']
    for name in source_paths:
        assert subprocess.check_output(['git','show',source_commit+':'+name],cwd=ROOT)==(ROOT/name).read_bytes()
        add(ROOT/name,'source/'+name)
    for label,seconds,private,tests,code,chunk,result in batches:
        label='phase-trace-'+label;directory=ROOT/'runs/source-validation'/label
        output=(directory/'stdout.log').read_bytes();assert result.encode() in output,(label,result)
        assert (directory/'stderr.log').read_bytes()==b'',label
        temporary=('/tmp/'+label) if private else str(directory/'tmp')
        argv=['/usr/bin/timeout','--signal=TERM','--kill-after=5s',str(seconds)+'s',
            '/usr/bin/bwrap','--unshare-user','--uid','1000','--gid','1000','--bind','/','/',
            '--tmpfs','/tmp','--dev','/dev','--proc','/proc','--chdir',str(ROOT),'--',
            '/home/utkarsh/Work/shraddha/brain/.worktrees/r0-reproduction/.venv/bin/python',
            '-m','pytest','-q','-p','no:cacheprovider','--basetemp',temporary,*tests]
        validation.append(dict(label=label,argv=argv,cwd=str(ROOT),
            environment_overlay=dict(PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',PYTHONDONTWRITEBYTECODE='1'),
            root_observed_terminal_chunk=chunk,root_observed_exit_code=code,pytest_reported_result=result,
            scope='authored source validation; inherited environment is not fully recorded'))
        for channel in ('stdout','stderr'):add(directory/(channel+'.log'),'validation/'+label+'/'+channel+'.log')
    snapshots=ROOT/'runs/source-validation/phase-trace-reentrant-red-01/source'
    for name in [*source_paths,'pins.json']:add(snapshots/name,'pre-fix-reentrant/'+name)
    for name in ('palimpsest-phase-trace-final-source-review.json',
                 'palimpsest-phase-trace-final-source-review-02.json',
                 'palimpsest-phase-trace-final-validation-review.json',
                 'palimpsest-phase-trace-publication-terminal.json'):
        add(Path('/tmp')/name,'reviews/'+name)
    record=dict(kind='cpu-phase-trace-root-validation-observations-v1',batches=validation,
        final_disjoint_passes=217,final_batches=['phase-trace-private-consumers-02','phase-trace-publication-integrations-02'],
        limitations=['Root tool observations and pytest-reported durations; not independent process transport or timing benchmarks.',
            'RED test source evolved before the separate cancellation and later-clock cases; do not assign initial REDs to final test bytes.',
            'All intermediate failures remain failures. Private storage passes do not identify the ancestor that changed in green01.',
            'Persistent native-image failure remains observed; final native fixtures use admitted private tmpfs, while historical integrations require persistent project paths.'])
    record_path=Path('/tmp/palimpsest-phase-trace-validation-record.json')
    with record_path.open('x') as stream:json.dump(record,stream,sort_keys=True,indent=2);stream.write('\n')
    add(record_path,'validation-record.json')
    add(Path(__file__).resolve(),'archive_evidence.py')
    add(ROOT/'docs/reports/puck-cpu-held-qualification-07/verify_evidence.py','verify_evidence.py')
    rows=[];total=0
    PACKET.mkdir()
    for name,original in sorted(pairs.items()):
        assert original.is_file() and not original.is_symlink() and original.stat().st_size<=1024**2,str(original)
        raw=original.read_bytes();total+=len(raw);assert total<=4*1024**2
        target=PACKET/name;target.parent.mkdir(parents=True,exist_ok=True)
        with target.open('xb') as stream:stream.write(raw)
        rows.append(dict(archived_path=name,original_path=str(original),size_bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
    index=dict(kind='cpu-phase-trace-source-evidence-index-v1',version=1,
        created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_commit=source_commit,
        source_paths=source_paths,artifacts=rows,artifact_count=len(rows),total_bytes=total,
        empty_files=sum(row['size_bytes']==0 for row in rows),
        source_review='GO',final_disjoint_authored_passes=217,actual08_controls_created=False,
        runtime_qualified=False,native_authorized=False,collection_authorized=False,study_authorized=False,
        qualification_claims=[],all_seven_release_gates_open=True)
    with (PACKET/'evidence-index.json').open('x') as stream:json.dump(index,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps(dict(artifacts=len(rows),bytes=total,empty_files=index['empty_files'],source_commit=source_commit),sort_keys=True))


if __name__=='__main__':main()
