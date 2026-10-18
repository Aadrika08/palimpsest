"""Fixed read-only custody after failed05; no runtime entrypoint or vendor import."""
import datetime
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
AUDITOR=ROOT/'docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'
AUDITOR_SHA='01bc2c99634cb3ec2e7bfc92f4fc96b219e07c8a5ea10351227a5cfb1181d4cf'
OUTPUT=Path('/tmp/palimpsest-held05-post-byte-custody-01.json')
POST_PINS=[{'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/baseline-before.json', 'size_bytes': 196, 'sha256': '8e69fa24c5367b19acfad5f5f3c12f1804eed23d0889df6a9e58f20da4376dfb'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/configuration.json', 'size_bytes': 8833, 'sha256': '584f687eeb11797eb48caf0514fc0ea7f5b7f8e46af0c6a5304ef59a714cb3b8'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/control/dependencies.json', 'size_bytes': 4253196, 'sha256': 'c3cf3b8579f476ff957e44bd47b57bc52fff4dd32674523baa0ce696851b420e'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/control/worker-registration.json', 'size_bytes': 4552, 'sha256': 'cfddb0c68d6b63d2dd3e871951a0c77ae9708cdb8b49cb5889106d6029abb5e3'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/invocation.json', 'size_bytes': 7029, 'sha256': 'ecfcc0bb528fb177bf7cbbbd38dd8afdf5c17a6098713b6c08a9136620d8f9ef'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/logs/stderr.log', 'size_bytes': 2509, 'sha256': '2b3774acb8b5946ebce7d9ee993d3ab4b48b576c3f8e1a73ac411fae4d24c048'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/logs/stdout.log', 'size_bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/resource-admission.json', 'size_bytes': 105, 'sha256': '4115790fc04475e1458e2a71473e128f8fd5e5872f06ee0611590f579fb761e1'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/result.json', 'size_bytes': 618, 'sha256': 'c5d2d2037ed248834d971278cbe2d6637b0324eb5b1518933e5201980b493e67'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/supervision.json', 'size_bytes': 357, 'sha256': 'ca663d925aa6f163843a4315d0a789a6081ab06a7add3b17fc074621a6175de7'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/scripts/puck_worker_bootstrap.py', 'size_bytes': 38375, 'sha256': '436b1ffe34b96fca166f6fb38022ad7392daef3517e58157092db2d9fd84c69f'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/src/palimpsest/__init__.py', 'size_bytes': 63, 'sha256': 'bb99e30d22e4662c4ded455b1b23f49b77ce811dcfa1b69bf358925487a566d8'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/src/palimpsest/puck_dependency_bindings.py', 'size_bytes': 28299, 'sha256': '7012888d030917434d1536285bb97fd2de15b5b83e9da87ee1503cda970a7147'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/src/palimpsest/puck_dependency_files.py', 'size_bytes': 33543, 'sha256': 'd1ca386780212b174a6e931a8ac4ce88e68c31b27fb1c0e16346a2150560fca1'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/src/palimpsest/puck_dependency_imports.py', 'size_bytes': 14868, 'sha256': 'e35b941c351971c15f225255170cd45530aa2304943fe2edd461b8d94080943b'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/src/palimpsest/puck_execution_files.py', 'size_bytes': 15001, 'sha256': 'ac059455bc45437c45330d01aaca761fd571d6de1637a4a8d7ebfbd796622062'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/src/palimpsest/puck_native_identity.py', 'size_bytes': 2837, 'sha256': '6e5b56e5c6494398dbd6a7c7d07e771e86c63d56e7374692d1d1d8213b721ebb'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/src/palimpsest/puck_native_origins.py', 'size_bytes': 1660, 'sha256': 'e6deea2bc378968371bf1093b869dfc442eeb7def27198695d1c0f872da519e1'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/src/palimpsest/puck_runtime_qualification.py', 'size_bytes': 2190, 'sha256': '45e1bca7f5420bd6dd4aed5a27af429783124a12f02def92e1db1db8d2199085'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05/worker-source/src/palimpsest/puck_worker_preflight.py', 'size_bytes': 465, 'sha256': 'dc5806d7f39913f4110b2aed8e4512c74f453b2f175f438771d72e78cca770f7'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05-external-cli-transport.json', 'size_bytes': 950, 'sha256': '7350fc1e7552205b73975b422f3241cf44e124d3d00617232569946c860dbe82'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05-external-cli.stderr', 'size_bytes': 0, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, {'path': '/home/utkarsh/.codex/worktrees/0071/brain/runs/puck-cpu-held-qualification-05-external-cli.stdout', 'size_bytes': 618, 'sha256': 'c5d2d2037ed248834d971278cbe2d6637b0324eb5b1518933e5201980b493e67'}, {'path': '/tmp/palimpsest-puck-cpu-held-qualification-05-audit-01.json', 'size_bytes': 617, 'sha256': 'cf0b4a4f2bcebe97c1e33695b864516ef029b8bd52f461de10ecc8d7a903b2cf'}]
CONFIGURATION=ROOT/'docs/plans/puck-cpu-held-qualification-05.json'
CONFIG_SHA='584f687eeb11797eb48caf0514fc0ea7f5b7f8e46af0c6a5304ef59a714cb3b8'
AUDITOR_CURRENT_SHA='5962e16b568633abff8916f6c1ee6c350087bc59f6bf1b5ff17d2983fbf3d229'
OBS_AUDITOR_SHA='be7e1321356c554750baa6e0982dc939a23546eca1574b8f5f68b2bbdec3afa4'
PREP_SHA='38134e016eff974e06806f1ac74492dc51e0a5721d8cd13d1123a1fd950fe8a6'
RESULT_SHA='9d49c6ee3a0be61505cfe7d2267b659290be17365d6e35fb5fdbdc38e103f47d'
DEP_SHA='25ea4e912919116b3196b8a8ed537f5dde02f40a35c295d97fe0c0509d67277f'


def resources():
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    flags=__import__('os').statvfs('/tmp').f_flag
    value=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),mem_available_bytes=available,project_free_bytes=shutil.disk_usage(ROOT).free,tmpfs_free_bytes=shutil.disk_usage('/tmp').free,nofile_soft=soft,nofile_hard=hard)
    assert available>=2<<30 and value['project_free_bytes']>=4<<30 and value['tmpfs_free_bytes']>=256<<20
    assert all(v==resource.RLIM_INFINITY or v>=40000 for v in (soft,hard)) and not flags & (os.ST_RDONLY|os.ST_NOEXEC)
    return value


def absent():
    paths=[OUTPUT]
    missing=[ROOT/'runs/puck-cpu-runtime-characterization-01/baseline-after.json']
    for allocation,leaves in [('puck-cpu-install-01',('inventory.json','licences.json','baseline-after.json','logs/namespace.json')),('puck-cpu-retained-admission-01',('inventory.json','snapshot.json','baseline-after.json'))]:
        missing.extend(ROOT/'runs'/allocation/leaf for leaf in leaves)
    assert all(not os.path.lexists(path) for path in paths+missing)
    return dict(new_paths=[str(p) for p in paths],historical_missing_receipts=len(missing))


def module(held,path,digest):
    raw=held.file(path,maximum=1024**2,raw=True)
    assert hashlib.sha256(raw).hexdigest()==digest
    value=types.ModuleType('_data_only_'+path.stem);value.__file__=str(path)
    exec(compile(raw,str(path),'exec'),value.__dict__)
    return value


def main():
    assert len(sys.argv)==1 and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    assert Path(sys.executable).resolve()==Path('/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11')
    assert 'LD_PRELOAD' not in os.environ and 'LD_LIBRARY_PATH' not in os.environ
    initial_resources=resources();absence=absent()
    started=time.monotonic();deadline=started+120
    signal.signal(signal.SIGALRM,signal.SIG_DFL);signal.setitimer(signal.ITIMER_REAL,130)
    try:
        for key,value in [('AS',512*1024**2),('NOFILE',40000),('FSIZE',16*1024**2),('CORE',0)]:
            _,hard=resource.getrlimit(getattr(resource,'RLIMIT_'+key))
            chosen=value if hard==resource.RLIM_INFINITY else min(value,hard)
            resource.setrlimit(getattr(resource,'RLIMIT_'+key),(chosen,chosen))
        fd=os.open(AUDITOR,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
        try:
            with os.fdopen(os.dup(fd),'rb') as handle:raw=handle.read(1024**2+1)
            assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()==AUDITOR_SHA
        finally:os.close(fd)
        m=types.ModuleType('authenticated_cpu_data_auditor');m.__file__=str(AUDITOR)
        exec(compile(raw,str(AUDITOR),'exec'),m.__dict__)
        before=len(os.listdir('/proc/self/fd'));held=m.Held(deadline);prepbase=ROOT/m.OUTPUTS['prepare']
        try:
            assert held.file(AUDITOR,dict(size_bytes=65522,sha256=AUDITOR_SHA),1024**2,raw=True)==raw
            own=held.file(Path(__file__).resolve(),maximum=1024**2)
            for row in POST_PINS:held.file(row['path'],row,16*1024**2,raw=True)
            current=module(held,ROOT/'scripts/audit_puck_cpu_held_runtime.py',AUDITOR_CURRENT_SHA)
            observation=module(held,ROOT/'scripts/audit_puck_cpu_runtime_characterization.py',OBS_AUDITOR_SHA)
            p,a,r,helpers=observation.support()
            for row in observation.SUPPORT:held.file(ROOT/row['path'],row,1024**2)
            frozen,frozenraw=held.json(CONFIGURATION,dict(size_bytes=CONFIGURATION.stat().st_size,sha256=CONFIG_SHA),1024**2,lf=True)
            current.configuration(frozen,False)
            for row in frozen['sources']:held.file(ROOT/row['path'],row,1024**2)
            for row in frozen['preparation_acceptance'].values():held.file(ROOT/row['path'],row,16*1024**2,raw=True)
            manifest,manifest_raw=held.json(ROOT/'docs/plans/puck-cpu-held-qualification-05-freeze.json',maximum=1024**2)
            assert manifest_raw==(json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
            for row in manifest['pins']:held.file(ROOT/row['path'],row,16*1024**2,raw=(row['path']==frozen['inputs']['candidate']['path']))
            assert manifest['source_commit']=='22b4180459d0782f0dd5d591a0ef460e477107c9' and manifest['observer_invocations']==1 and manifest['implicit_retry'] is False
            config,configraw=held.json(ROOT/'docs/plans/puck-cpu-held-preparation-01.json',maximum=1024**2,lf=True)
            assert m.sha(configraw)==PREP_SHA;m.configuration(config,False)
            assert config['root']==str(ROOT) and config['phase']=='prepare'
            prep,prepraw=held.json(prepbase/'result.json',maximum=1024**2,lf=True)
            assert m.sha(prepraw)==RESULT_SHA;m.outcome(prep,config,PREP_SHA)
            assert held.file(prepbase/'configuration.json',maximum=1024**2,raw=True)==configraw
            for folder,names in [('parent-source',m.SOURCES),('worker-source',m.WORKER)]:
                for row in config['sources']:
                    if row['path'] in names:held.file(prepbase/folder/row['path'],row,1024**2)
            blobs={};data={}
            for role,row in config['inputs'].items():
                blobs[role]=held.file(ROOT/row['path'],row,16*1024**2,raw=True)
                if role!='generated':data[role]=m.decode(blobs[role])
            m.inputs_binding(config,data,blobs);source,dependency,directories=m.plan(config,data)
            current.historical_acceptance(held,frozen,False)
            selected=dict(data);selected_blobs=dict(blobs)
            candidate_raw=held.file(ROOT/frozen['inputs']['candidate']['path'],frozen['inputs']['candidate'],16*1024**2,raw=True)
            selected['candidate']=current.decode(candidate_raw);selected_blobs['candidate']=candidate_raw
            current.publication_candidate(data['candidate'],selected['candidate'])
            current.inputs_binding(frozen,selected,selected_blobs)
            current_source,current_dependency,current_dirs=current.plan(frozen,selected)
            assert current_source==source and current_dirs==directories
            expected=json.loads(m.canonical(dependency));expected['import_profile']=selected['candidate']['import_profile']
            assert current_dependency==expected
            site=ROOT/'runs/puck-cpu-install-01/site'
            files,site_dirs,site_stamps=r.census(site)
            assert files==r.rows_to_map(data['inventory']['entries']) and site_dirs==set(data['layout']['predicted_destination_directories'])
            assert (len(files),len(site_dirs),sum(row['size_bytes'] for row in files.values()))==(27225,2074,1304701872)
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
            aliases=data['native']['aliases'];assert type(aliases) is list and len(aliases)<=256 and len({r[0] for r in aliases})==len(aliases)
            for path,target in aliases:held.symlink(path,target)
            summary=m.baseline(held,data['baseline'])
            for name in ['baseline-before.json','baseline-after.json']:
                value,_=held.json(prepbase/name,lf=True);assert value==summary
            observed,_=held.json(prepbase/'supervision.json',maximum=1024**2,lf=True);m.supervision(observed,'prepare')
            command=[m.PYTHON,'-I','-S','-B','/puck/source/scripts/stage_puck_cpu_held_runtime.py',m.sha(requestraw)]
            invocation,_=held.json(prepbase/'invocation.json',maximum=1024**2,lf=True)
            assert invocation==dict(command=m.namespace_command(config,data,'prepare',command),configuration_sha256=PREP_SHA)
            for allocation,expected in [('01','224cb9bdb18228f6e8da7a47e7455cd604a6e756df5fd017294b9221f26d9299'),('02','085d19bdd39d392aaeab0c1590ec92b99e0bb2a4e8945f5d23dd51733fbab56b'),('03','ba5cad51576c3dd593c479d052328fcb4181943d3f5acdbdaa7cdee145f1254b'),('04','d2db585f4851b916e7c632ca268d7527ce4604e6949918ea6d89408ddbcc3889')]:
                failurebase=ROOT/('runs/puck-cpu-held-qualification-'+allocation)
                failed,fraw=held.json(failurebase/'result.json',maximum=1024**2,lf=True)
                assert m.sha(fraw)==expected and failed['status']=='FAIL' and failed['allocation_id']==int(allocation)
                m.no_authority(failed)
                assert not os.path.lexists(failurebase/'baseline-after.json')
            tree=m.forest(held,config,dependency,directories,prep['staged_roots'])
            assert m.forest(held,config,dependency,directories,prep['staged_roots'])==tree
            _,final_dirs,final_stamps=r.census(site,hashes=False)
            assert final_dirs==site_dirs and final_stamps==site_stamps
            absence=absent();final_resources=resources()
            held.recheck();held.clock()
            totals=dict(file_count=sum(len(r['files']) for r in dependency['roots']),directory_count=sum(len(d) for d in directories),input_bytes=sum(f['size_bytes'] for r in dependency['roots'] for f in r['files']))
            assert totals==dict(file_count=27255,directory_count=2076,input_bytes=1318494346)
            failed,_=held.json(ROOT/'runs/puck-cpu-held-qualification-05/result.json',lf=True)
            transport,_=held.json(ROOT/'runs/puck-cpu-held-qualification-05-external-cli-transport.json',lf=True)
            refusal,_=held.json(Path('/tmp/palimpsest-puck-cpu-held-qualification-05-audit-01.json'),lf=True)
            assert failed['status']=='FAIL' and failed['held_four_imports_observed'] is False and failed['closure']==dict(active_children=[],active_non_main_threads=[],fd_count_before=5,fd_count_after=5)
            assert transport['observed_returncode']==1 and transport['timed_out'] is False and transport['elapsed_seconds']<210
            assert refusal['status']=='FAIL' and refusal['error']=='Normal external transport exit required'
            assert not os.path.lexists(ROOT/'runs/puck-cpu-held-qualification-05/baseline-after.json')
            observed05,_=held.json(ROOT/'runs/puck-cpu-held-qualification-05/supervision.json',lf=True)
            assert observed05['returncode']==1 and observed05['status']=='failed' and observed05['matching_survivors']==[] and observed05['process_scope']=='descendants'
            samples=[]
            for identity in observed05['tracked_processes']:
                stat_path=Path('/proc')/str(identity['pid'])/'stat'
                try:
                    fd=os.open(stat_path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
                    try:raw=os.read(fd,8193)
                    finally:os.close(fd)
                    assert len(raw)<=8192
                    ticks=int(raw.rsplit(b')',1)[1].split()[19]);assert ticks!=identity['start_ticks']
                    samples.append(dict(identity,current_start_ticks=ticks,matching_identity_present=False))
                except (FileNotFoundError,ProcessLookupError):samples.append(dict(identity,matching_identity_present=False))
            assert len(samples)==3
            held.recheck();held.clock()
        finally:held.close()
        after=len(os.listdir('/proc/self/fd'))
        assert before==after and not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split() and len(os.listdir('/proc/self/task'))==1
        result=dict(m.CLAIMS,kind='puck-cpu-held05-post-failure-custody-v1',version=1,status='CURRENT_BYTES_PRESERVED_AFTER_FAILED05',scope='dated current source/input/SITE/staged/native/interpreter bytes and known process identities after failed05; no runtime invocation or preparation reacceptance',preparation_configuration_sha256=PREP_SHA,preparation_result_sha256=RESULT_SHA,dependencies_sha256=DEP_SHA,auditor_source_sha256=AUDITOR_SHA,runner_sha256=own['sha256'],baseline=summary,root_count=4,historical_capsule_files=34,input_pins=16,**totals,closure=dict(fd_count_before=before,fd_count_after=after,active_children=[],active_non_main_threads=[]),elapsed_seconds=time.monotonic()-started,qualifications01_02_03_04_still_failed_consumed=True,qualification05_invoked=True,runtime_entrypoint_invoked_by_custody_check=False,failed05_artifact_pins=POST_PINS,tracked_identity_rechecks=samples,cleanup_limitation='Known recorded PID/start identities only; not exhaustive or atomic lifetime proof',configuration_sha256=CONFIG_SHA,current_auditor_sha256=AUDITOR_CURRENT_SHA,resources_before=initial_resources,resources_after=final_resources,absence=absence,site_files=27225,site_directories=2074,site_bytes=1304701872,current_sources=24,current_inputs=16,source_commit='22b4180459d0782f0dd5d591a0ef460e477107c9')
        assert time.monotonic()<deadline;m.publish(OUTPUT,result)
        assert time.monotonic()<deadline
        print(m.canonical(result).decode(),end='',flush=True)
        assert time.monotonic()<deadline
        return 0
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
