"""Port the reviewed-GO, consumed attempt-14 admission to the allocation-16 episode admission (RED stage).

Keeps every attempt-14 history function byte-identical except the counted edits below, drops the
preparation03 binding (now consumed history), and writes a new header and main() for the episode
allocation on accepted preparation04. The new history helpers that main() calls (runtime14,
admission14, preparation03 consumed/retired, characterization-04, preparation04) are deliberately
absent here: history-check.py must fail on them first (RED). Writes only the new admission file.
"""
from pathlib import Path
import hashlib,json,subprocess
ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
OLD='docs/plans/puck-cpu-held-qualification-14-admission.py'
NEW='docs/plans/puck-cpu-held-episode-16-admission.py'
CONTROL14='eb34d5c2a66730c248b00229c17ce84e197b3d68'
def git(*args):return subprocess.check_output(['git','-C',str(ROOT),*args])
old=git('show',CONTROL14+':'+OLD).decode();assert (ROOT/OLD).read_text()==old and not (ROOT/NEW).exists()
start=old.index('HISTORICAL07_JSON={');end=old.index("PREP_CONFIGURATION='docs/plans/puck-cpu-held-preparation-03.json'")
history=old[start:end]
tail_start=old.index('UNEXECUTED11=');tail_end=old.index('def check_preparation03(')
unexecuted=old[tail_start:tail_end]
helpers_start=old.index('def record_preparation01():');helpers_end=old.index('def main():')
helpers=old[helpers_start:helpers_end]
EDITS=[
    # Preparation02's stage is retired now; the retirement census record binds it.
    (history,'    """Accepted preparation02 bound runtime11 (packet 11b); its retained stage is never inspected here."""',
     '    """Accepted preparation02 bound runtime11 (packet 11b); its stage was retired with a recorded census."""',1),
    (history,"    # Consumed: runtime11 bound exactly these pins; check_consumed11 binds its failure.\n    assert os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-11/supervision.json')\n    return dict(status='ACCEPTED_CONSUMED_BY_RUNTIME11',",
     "    # Consumed: runtime11 bound exactly these pins; check_consumed11 binds its failure.\n    assert os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-11/supervision.json')\n    retired=check_retired_stage(held,config['stage_parent'],PREP02_ACCEPTANCE['result']['sha256'])\n    return dict(status='ACCEPTED_CONSUMED_BY_RUNTIME11_STAGE_RETIRED',retirement=retired,",1),
    (history,"        stage_inspected=False,scope='accepted preparation02 metadata; its stage is retained and never read by these controls')",
     "        stage_inspected=False,scope='accepted preparation02 metadata; its stage was retired after a recorded identity and content census')",1),
    (unexecuted,"EMPTY_DIRECTORIES=[","EMPTY_DIRECTORIES=['runs/puck-cpu-held-qualification-14/outer', 'runs/puck-cpu-held-qualification-14/payload', 'runs/puck-cpu-held-qualification-14/worker-source/upstream/fly-gym', 'runs/puck-cpu-held-preparation-04/outer', 'runs/puck-cpu-runtime-characterization-04/outer', ",1),
    (helpers,"    paths=[ROOT/'runs/puck-cpu-held-qualification-14']+[ROOT/('runs/puck-cpu-held-qualification-14-external-cli'+suffix) for suffix in ('.stdout','.stderr','-transport.json')]\n    paths+=[Path('/tmp/palimpsest-puck-cpu-held-qualification-14-audit-01.json'),OUTPUT]",
     "    paths=[ROOT/'runs/puck-cpu-held-episode-16']+[ROOT/('runs/puck-cpu-held-episode-16-external-cli'+suffix) for suffix in ('.stdout','.stderr','-transport.json')]\n    paths+=[Path('/tmp/palimpsest-puck-cpu-held-episode-16-audit-01.json'),OUTPUT]",1),
    (helpers,"    assert type(names) is list and len(names)==32 and names==sorted(set(names))","    assert type(names) is list and len(names)==42 and names==sorted(set(names))",1),
    (helpers,"    _stderr_record(dict(kind='held14-data-admission-phase-v1',check_id=14,","    _stderr_record(dict(kind='held16-data-admission-phase-v1',check_id=16,",1),
    (helpers,"        value=dict(kind='held14-data-admission-failure-v1',check_id=14,status='FAIL',","        value=dict(kind='held16-data-admission-failure-v1',check_id=16,status='FAIL',",1)]
parts=dict(history=history,unexecuted=unexecuted,helpers=helpers)
for index,(text,a,b,count) in enumerate(EDITS):
    name=next(k for k,v in parts.items() if v is text or a in v)
    assert parts[name].count(a)==count,(index,name,parts[name].count(a))
    parts[name]=parts[name].replace(a,b)
    for k in parts:
        if k!=name:assert a not in parts[k] or count==0
history,unexecuted,helpers=parts['history'],parts['unexecuted'],parts['helpers']
# The 07-11 runtime history reads the same originals, but the docs/reports packets are now bound by their evidence indexes.
assert "def check_preparation02_consumed(held):" in history and 'config,result,audit,cli=' in history
HEAD='''"""Fixed DATA-ONLY admission before the sole allocation-16 held episode; no allocation, episode, renderer or vendor import.

Binds the frozen allocation-16 configuration, accepted preparation04 (v15, roots 317249-317252),
its staged forest re-hashed twice, the accepted SITE, v6 natives, EGL vendor JSON and trusted
interpreter prefix, and the consumed history: attempts 01-11 and runtime14, admissions 10-01/02,
11b and 14, preparations 01-03 (02/03 stages retired with a recorded census), characterization-04
and the never-invoked d83dab3 packet. Consumed docs/reports packets are bound through their
committed evidence-index hashes; the files the history checks read are re-hashed here.
"""
import datetime
import importlib.machinery
import hashlib
import shutil
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time
import types

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
# The preparation04 PASS auditor supplies Held, plan, forest and the v15 receipts checks.
AUDITOR=ROOT/'scripts/audit_puck_cpu_held_runtime.py'
AUDITOR_SHA='4ef23799994785c2154aeedd83a03e0457cdfd7f9e4573d12d44e462fb782f7c'
EPISODE_AUDITOR_SHA='4d8ac17f0577938ded9fa3845f0e26c1b52be8db11fa5327953c9446b156ba36'
EPISODE_PARENT_SHA='bd08543a0a8ad590f3fd7edbf20be2eeaf9e94dbf1dac5a5b9965d368002fd6c'
OBS_AUDITOR_SHA='be7e1321356c554750baa6e0982dc939a23546eca1574b8f5f68b2bbdec3afa4'
OUTPUT=Path('/tmp/palimpsest-puck-cpu-held-episode-16-admission-01.json')
CONFIGURATION=ROOT/'docs/plans/puck-cpu-held-episode-16.json'
FREEZE=ROOT/'docs/plans/puck-cpu-held-episode-16-freeze.json'
CONFIG_SHA='@CONFIG_SHA@'
PREP_CONFIGURATION='docs/plans/puck-cpu-held-preparation-04.json'
PREP_OUTPUT='runs/puck-cpu-held-preparation-04'
PREP_STAGE='/tmp/palimpsest-puck-cpu-held-04'
PREP_SHA='f43be9750cd4e7a45054143cc55565df3ac89b831025fc6380349b557dc92956'
RESULT_SHA='a76b61487a1e5c053032167f1602260a1184b6262fa86e0e62842f0a05e6ebc3'
DEP_SHA='@DEP_SHA@'
PREP_ROOTS=[{'device': 55, 'inode': 317249, 'root_index': 0}, {'device': 55, 'inode': 317250, 'root_index': 1}, {'device': 55, 'inode': 317251, 'root_index': 2}, {'device': 55, 'inode': 317252, 'root_index': 3}]
RETIREMENT='docs/reports/puck-cpu-held-preparation-04/records/retire-consumed-stages.json'
RETIREMENT_SHA='02fc84198b90a17ea3d2bde516889abcfece0b774e75441bbde8838652da8d2d'


'''
MAIN='''def main():
    started=time.monotonic()
    try:
        assert len(sys.argv)==1 and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
        assert Path(sys.executable).resolve()==Path(PYTHON)
        assert 'LD_PRELOAD' not in os.environ and 'LD_LIBRARY_PATH' not in os.environ
        initial_resources=resources();absence=absent()
    except BaseException as error:
        _failure(error,started)
        raise
    started=time.monotonic();deadline=started+120
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,130)
    held=None;before=None;held_closed=False
    try:
        for key,value in [('AS',512*1024**2),('NOFILE',40000),('FSIZE',16*1024**2),('CORE',0)]:
            _,hard=resource.getrlimit(getattr(resource,'RLIMIT_'+key))
            chosen=value if hard==resource.RLIM_INFINITY else min(value,hard)
            resource.setrlimit(getattr(resource,'RLIMIT_'+key),(chosen,chosen))
        fd=os.open(AUDITOR,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            with os.fdopen(os.dup(fd),'rb') as handle:raw=handle.read(1024**2+1)
            assert hashlib.sha256(raw).hexdigest()==AUDITOR_SHA
        finally:os.close(fd)
        m=types.ModuleType('authenticated_cpu_data_auditor');m.__file__=str(AUDITOR)
        exec(compile(raw,str(AUDITOR),'exec'),m.__dict__)
        before=len(os.listdir('/proc/self/fd'));held=m.Held(deadline);prepbase=ROOT/PREP_OUTPUT
        try:
            assert held.file(AUDITOR,dict(size_bytes=len(raw),sha256=AUDITOR_SHA),1024**2,raw=True)==raw
            own=held.file(Path(__file__).resolve(),maximum=1024**2)
            episode_auditor=module(held,ROOT/'scripts/audit_puck_cpu_held_episode.py',EPISODE_AUDITOR_SHA)
            episode=module(held,ROOT/'scripts/run_puck_cpu_held_episode.py',EPISODE_PARENT_SHA)
            observation=module(held,ROOT/'scripts/audit_puck_cpu_runtime_characterization.py',OBS_AUDITOR_SHA)
            p,a,r,helpers=observation.support()
            for row in observation.SUPPORT:held.file(ROOT/row['path'],row,1024**2)
            frozen,frozenraw=held.json(CONFIGURATION,dict(size_bytes=CONFIGURATION.stat().st_size,sha256=CONFIG_SHA),1024**2,lf=True)
            assert episode.canonical(frozen)==frozenraw==episode_auditor.canonical(frozen)
            # Allocation 16 only: parent 1200/1215/1230 s, each worker 600 s, observer 1260/1275 s.
            assert (frozen['limits']['normal_seconds'],frozen['limits']['child_hard_seconds'],frozen['limits']['hard_seconds'])==(1200,1215,1230)
            assert episode.WORKER_SECONDS==episode_auditor.WORKER_SECONDS==600 and episode_auditor.TRANSPORT_SECONDS==1260
            qualifier_row=next(r for r in frozen['sources'] if r['path']=='scripts/qualify_puck_cpu_held_runtime.py')
            q=module(held,ROOT/qualifier_row['path'],qualifier_row['sha256'])
            for row in frozen['sources']:held.file(ROOT/row['path'],row,1024**2)
            acceptance_blobs={role:held.file(ROOT/row['path'],row,16*1024**2,raw=True) for role,row in frozen['preparation_acceptance'].items()}
            episode.validate_configuration(frozen,q);prior,prepared=episode.validate_acceptance(frozen,acceptance_blobs,q)
            episode_auditor.validate_configuration(frozen,prior)
            episode_auditor.validate_acceptance(frozen,episode_auditor.Reader(deadline))
            manifest,manifest_raw=held.json(FREEZE,maximum=1024**2)
            assert manifest_raw==(json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False)+'\\n').encode()
            raw_paths={row['path'] for row in frozen['inputs'].values()}
            raw_paths.update(row['path'] for row in frozen['preparation_acceptance'].values())
            raw_paths.update('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json' for i in range(1,7))
            for rows in (HISTORICAL07_JSON,HISTORICAL08_JSON,HISTORICAL09_JSON,HISTORICAL10_JSON,HISTORICAL11_JSON,HISTORICAL14_JSON,
                    ADMISSION01_PINS,ADMISSION02_PINS,ADMISSION11B_PINS,ADMISSION14_PINS,CHARACTERIZATION04_JSON):raw_paths.update(rows)
            raw_paths.update(row['path'] for row in PREP02_ACCEPTANCE.values())
            raw_paths.update(row['path'] for row in PREP03_ACCEPTANCE.values())
            raw_paths.add(RETIREMENT)
            hold_manifest(held,manifest['pins'],raw_paths)
            admitted10,_=held.json(ROOT/ADMITTED10_CONFIGURATION,dict(size_bytes=8988,sha256=HISTORICAL10_JSON[ADMITTED10_CONFIGURATION]),1024**2,lf=True)
            consumed_admission01=check_consumed_admission01(held,admitted10)
            consumed_admission02=check_consumed_admission02(held,admitted10)
            assert manifest['source_commit']==SOURCE and manifest['observer_invocations']==1 and manifest['implicit_retry'] is False
            config,configraw,prep,prepraw,preparation04=check_preparation04(held,m,prior,prepared)
            blobs={};data={}
            for role,row in config['inputs'].items():
                blobs[role]=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
                if role!='generated':data[role]=m.decode(blobs[role])
            m.inputs_binding(config,data,blobs);source,dependency,directories=m.plan(config,data)
            episode.require_declared_misses(data['candidate'])
            negative_absence=check_absences(dependency,directories,frozen['negative_imports'])
            characterization04=check_characterization04(held,config)
            _phase('controls/plans',started,held)
            site=ROOT/'runs/puck-cpu-install-01/site'
            files,site_dirs,site_stamps=r.census(site)
            assert files==r.rows_to_map(data['inventory']['entries']) and site_dirs==set(data['layout']['predicted_destination_directories'])
            assert (len(files),len(site_dirs),sum(row['size_bytes'] for row in files.values()))==(27225,2074,1304701872)
            _phase('SITEhash',started,held)
            copy,copyraw=held.json(prepbase/'control/copy-registration.json',lf=False)
            assert copyraw==m.canonical(source,False)
            for role in ['candidate','layout']:
                assert held.file(prepbase/('control/'+role+'.json'),maximum=16*1024**2,raw=True)==blobs[role]
            request,requestraw=held.json(prepbase/'control/stage-request.json',maximum=1024**2,lf=True)
            assert request==dict(registration=dict(path='/puck/control/copy-registration.json',sha256=m.sha(copyraw)),candidate=dict(path='/puck/control/candidate.json',sha256=m.sha(blobs['candidate'])),layout=dict(path='/puck/control/layout.json',sha256=m.sha(blobs['layout'])))
            dep,depraw=held.json(prepbase/'payload/dependencies.json',prep['dependencies'],lf=False)
            assert m.sha(depraw)==DEP_SHA and depraw==m.canonical(dependency,False)
            stage,stageraw=held.json(prepbase/'payload/stage.json',maximum=1024**2,lf=True);m.no_authority(stage)
            assert stage['kind']=='puck-cpu-tmpfs-preparation-receipt-v1' and stage['status']=='prepared' and stage['dependencies']==prep['dependencies'] and stage['staged_roots']==prep['staged_roots']
            assert held.file(prepbase/'logs/stdout.log',maximum=1024**2,raw=True)==stageraw
            held.file(prepbase/'logs/stderr.log',maximum=16*1024**2)
            for row in data['native']['native_files']:held.file(row['path'],row,single=False)
            vendor=data['native']['egl_vendor']
            held.file(vendor['path'],dict(size_bytes=vendor['size_bytes'],sha256=vendor['sha256']),64*1024,single=False)
            aliases=data['native']['aliases'];assert type(aliases) is list and len(aliases)<=256 and len({r[0] for r in aliases})==len(aliases)
            for path,target in aliases:held.symlink(path,target)
            summary=m.baseline(held,data['baseline'])
            for name in ['baseline-before.json','baseline-after.json']:
                value,_=held.json(prepbase/name,lf=True);assert value==summary
            observed,_=held.json(prepbase/'supervision.json',maximum=1024**2,lf=True);m.supervision(observed,'prepare')
            command=[m.PYTHON,'-I','-S','-B','/puck/source/scripts/stage_puck_cpu_held_runtime.py',m.sha(requestraw)]
            invocation,_=held.json(prepbase/'invocation.json',maximum=1024**2,lf=True)
            assert invocation==dict(command=m.namespace_command(config,data,'prepare',command),configuration_sha256=PREP_SHA)
            for allocation,expected in [('01','224cb9bdb18228f6e8da7a47e7455cd604a6e756df5fd017294b9221f26d9299'),('02','085d19bdd39d392aaeab0c1590ec92b99e0bb2a4e8945f5d23dd51733fbab56b'),('03','ba5cad51576c3dd593c479d052328fcb4181943d3f5acdbdaa7cdee145f1254b'),('04','d2db585f4851b916e7c632ca268d7527ce4604e6949918ea6d89408ddbcc3889'),('05','c5d2d2037ed248834d971278cbe2d6637b0324eb5b1518933e5201980b493e67'),('06','e88a7f3317ae15b709409cf04a30f969629b20c51454a5ad6ca72d63d6378b88')]:
                failurebase=ROOT/('runs/puck-cpu-held-qualification-'+allocation)
                failed,fraw=held.json(failurebase/'result.json',maximum=1024**2,lf=True)
                assert m.sha(fraw)==expected and failed['status']=='FAIL' and failed['allocation_id']==int(allocation)
                m.no_authority(failed)
                assert not os.path.lexists(failurebase/'baseline-after.json')
            consumed07=check_consumed07(held)
            consumed08=check_consumed08(held)
            consumed09=check_consumed09(held)
            consumed10=check_consumed10(held)
            consumed11=check_consumed11(held)
            admitted11,_=held.json(ROOT/'docs/plans/puck-cpu-held-qualification-11.json',dict(size_bytes=9048,sha256=HISTORICAL11_JSON['docs/plans/puck-cpu-held-qualification-11.json']),1024**2,lf=True)
            consumed_admission11b=check_consumed_admission11b(held,admitted11)
            runtime14=check_runtime14(held)
            admitted14,_=held.json(ROOT/'docs/plans/puck-cpu-held-qualification-14.json',dict(size_bytes=9048,sha256=HISTORICAL14_JSON['docs/plans/puck-cpu-held-qualification-14.json']),1024**2,lf=True)
            consumed_admission14=check_consumed_admission14(held,admitted14)
            preparation02=check_preparation02_consumed(held)
            preparation03=check_preparation03_consumed(held)
            unexecuted11=check_unexecuted11(held)
            empty_directories=check_empty_directories()
            preparation01=record_preparation01()
            _phase('hostbaseline/native',started,held)
            tree=m.forest(held,config,dependency,directories,prep['staged_roots'])
            _phase('forest1',started,held)
            assert m.forest(held,config,dependency,directories,prep['staged_roots'])==tree
            _phase('forest2',started,held)
            _,final_dirs,final_stamps=r.census(site,hashes=False)
            assert final_dirs==site_dirs and final_stamps==site_stamps
            _phase('finalSITEcensus',started,held)
            absence=absent();final_resources=resources()
            held.recheck();held.clock()
            _phase('fullrecheck',started,held)
            totals=dict(file_count=sum(len(r['files']) for r in dependency['roots']),directory_count=sum(len(d) for d in directories),input_bytes=sum(f['size_bytes'] for r in dependency['roots'] for f in r['files']))
            assert totals==TOTALS
            held_entries=dict(files=len(held.files),directories=len(held.dirs),links=len(held.links),bytes=held.total)
        finally:
            held.close()
            held_closed=True
        after=len(os.listdir('/proc/self/fd'))
        assert before==after and not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split() and len(os.listdir('/proc/self/task'))==1
        sampled=[]
        for identity in PROCESS_IDENTITIES:
            path=Path('/proc')/str(identity[0])/'stat'
            try:
                current=int(path.read_text().rsplit(')',1)[1].split()[19])
                matches=current==identity[1]
            except FileNotFoundError:matches=False
            assert not matches
            sampled.append(dict(pid=identity[0],start_ticks=identity[1],matching_identity_present=matches))
        result=dict(m.CLAIMS,kind='puck-cpu-held-episode16-data-only-admission-v1',version=1,status='DATA_ONLY_ADMITTED',
            scope='dated allocation-16 configuration on accepted preparation04 source/input/SITE/staged/native/EGL/interpreter bytes and resources only; no allocation, episode, renderer, target import or preparation reacceptance',
            preparation_configuration_sha256=PREP_SHA,preparation_result_sha256=RESULT_SHA,dependencies_sha256=DEP_SHA,
            auditor_source_sha256=AUDITOR_SHA,episode_auditor_sha256=EPISODE_AUDITOR_SHA,episode_parent_sha256=EPISODE_PARENT_SHA,
            runner_sha256=own['sha256'],baseline=summary,root_count=4,input_pins=len(frozen['inputs']),current_sources=len(frozen['sources']),
            **totals,held_entries=held_entries,closure=dict(fd_count_before=before,fd_count_after=after,active_children=[],active_non_main_threads=[]),
            elapsed_seconds=time.monotonic()-started,qualifications01_02_03_04_05_06_07_08_09_10_11_still_failed_consumed=True,
            runtime14_accepted_consumed=True,episode16_invoked=False,admission_check_id=1,admission10_01_failure=consumed_admission01,
            admission10_02=consumed_admission02,configuration_sha256=CONFIG_SHA,resources_before=initial_resources,resources_after=final_resources,
            absence=absence,site_files=27225,site_directories=2074,site_bytes=1304701872,process_identity_samples=sampled,
            process_scope=str(len(PROCESS_IDENTITIES))+' recorded identities only; nonexhaustive non-atomic lifetime observation',
            qualification07_failure=consumed07,qualification08_failure=consumed08,qualification09_failure=consumed09,qualification10_failure=consumed10,
            qualification11_failure=consumed11,admission11b=consumed_admission11b,runtime14=runtime14,admission14=consumed_admission14,
            preparation04=preparation04,preparation03=preparation03,preparation02=preparation02,preparation01=preparation01,
            characterization04=characterization04,attempt11_d83dab3=unexecuted11,historical_empty_directories=empty_directories,
            negative_absence=negative_absence,run_ids=frozen['run_ids'],source_commit=SOURCE)
        assert time.monotonic()<deadline;m.publish(OUTPUT,result)
        _phase('close/publication',started,held)
        assert time.monotonic()<deadline
        print(m.canonical(result).decode(),end='',flush=True)
        assert time.monotonic()<deadline
        return 0
    except BaseException as error:
        _failure(error,started,before,held_closed)
        raise
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
'''
config_raw=(ROOT/'docs/plans/puck-cpu-held-episode-16.json').read_bytes()
prep_result=json.loads((ROOT/'runs/puck-cpu-held-preparation-04/result.json').read_bytes())
head=HEAD.replace('@CONFIG_SHA@',hashlib.sha256(config_raw).hexdigest()).replace('@DEP_SHA@',prep_result['dependencies']['sha256'])
text=head+history+unexecuted+helpers+MAIN
compile(text,NEW,'exec')
with (ROOT/NEW).open('x') as out:out.write(text)
print(json.dumps(dict(path=NEW,size_bytes=len(text.encode()),sha256=hashlib.sha256(text.encode()).hexdigest(),
    source=CONTROL14+':'+OLD,counted_edits=len(EDITS),dropped=['check_preparation03','attempt-14 main'],
    red_missing=['check_runtime14','check_consumed_admission14','check_preparation03_consumed','check_retired_stage',
        'check_characterization04','check_preparation04','HISTORICAL14_JSON','ADMISSION14_PINS','CHARACTERIZATION04_JSON',
        'PREP03_ACCEPTANCE','PROCESS_IDENTITIES','TOTALS','SOURCE'],admission_invoked=False),indent=2,sort_keys=True))
