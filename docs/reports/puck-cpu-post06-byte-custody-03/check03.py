"""Fixed DATA-ONLY post-failure06 byte/custody check03; no runtime allocation or vendor import."""
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
AUDITOR=ROOT/'docs/reports/puck-cpu-held-qualification-amendment-03/source-evidence/validation/prepared-byte-audit03-01/authenticated-auditor.py'
AUDITOR_SHA='01bc2c99634cb3ec2e7bfc92f4fc96b219e07c8a5ea10351227a5cfb1181d4cf'
OUTPUT=Path('/tmp/palimpsest-held06-post-byte-custody-03.json')
CONFIGURATION=ROOT/'docs/plans/puck-cpu-held-qualification-06.json'
CONFIG_SHA='da630b05b871508686a4c92402725820b40b27253b2652b47c686a8f441a04e8'
AUDITOR_CURRENT_SHA='f910d6bdf592fe7b488591398332ac70131891bd4f7c95ea793d20be8b90f829'
OBS_AUDITOR_SHA='be7e1321356c554750baa6e0982dc939a23546eca1574b8f5f68b2bbdec3afa4'
PREP_SHA='38134e016eff974e06806f1ac74492dc51e0a5721d8cd13d1123a1fd950fe8a6'
RESULT_SHA='9d49c6ee3a0be61505cfe7d2267b659290be17365d6e35fb5fdbdc38e103f47d'
DEP_SHA='25ea4e912919116b3196b8a8ed537f5dde02f40a35c295d97fe0c0509d67277f'


def resources(minimum_ram_bytes=2<<30):
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    flags=__import__('os').statvfs('/tmp').f_flag
    value=dict(at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),mem_available_bytes=available,project_free_bytes=shutil.disk_usage(ROOT).free,tmpfs_free_bytes=shutil.disk_usage('/tmp').free,nofile_soft=soft,nofile_hard=hard)
    assert available>=minimum_ram_bytes and value['project_free_bytes']>=4<<30 and value['tmpfs_free_bytes']>=256<<20
    assert all(v==resource.RLIM_INFINITY or v>=40000 for v in (soft,hard)) and not flags & (os.ST_RDONLY|os.ST_NOEXEC)
    return value


def absent():
    paths=[OUTPUT]
    missing=[ROOT/'runs/puck-cpu-runtime-characterization-01/baseline-after.json']
    for allocation,leaves in [('puck-cpu-install-01',('inventory.json','licences.json','baseline-after.json','logs/namespace.json')),('puck-cpu-retained-admission-01',('inventory.json','snapshot.json','baseline-after.json'))]:
        missing.extend(ROOT/'runs'/allocation/leaf for leaf in leaves)
    missing.extend(ROOT/('runs/puck-cpu-held-qualification-'+n+'/baseline-after.json') for n in ('05','06'))
    assert all(not os.path.lexists(path) for path in paths+missing)
    return dict(new_paths=[str(p) for p in paths],historical_missing_receipts=len(missing))


def module(held,path,digest):
    raw=held.file(path,maximum=1024**2,raw=True)
    assert hashlib.sha256(raw).hexdigest()==digest
    value=types.ModuleType('_data_only_'+path.stem);value.__file__=str(path)
    exec(compile(raw,str(path),'exec'),value.__dict__)
    return value



def check_absences(dependency,directories,names):
    """Byte/declaration check; worker live custody checks remain separate."""
    assert type(names) is list and len(names)==19 and names==sorted(set(names))
    declared={row['name'] for row in dependency['modules']+dependency['namespaces']}
    declared.update(row['name'] for key in ('exports','native_cache') for row in dependency['import_profile'].get(key,[]))
    packages={row['name']:row for row in dependency['modules'] if row['is_package']}
    packages.update({row['name']:row for row in dependency['namespaces']})
    censuses={i:{row['path'] for row in root['files']}|set(directories[i])
              for i,root in enumerate(dependency['roots']) if root['kind']=='package'}
    for name in names:
        assert name.split('.')[0] not in sys.stdlib_module_names
        assert not any(known==name or known.startswith(name+'.') for known in declared),name
        candidates={(i,name.replace('.','/')) for i in censuses}
        parent,dot,leaf=name.rpartition('.')
        if dot:
            assert parent in packages,name
            row=packages[parent]
            directory=row['path'].rpartition('/')[0] if row.get('is_package') else row['path']
            candidates.add((row['root_index'],directory+'/'+leaf if directory else leaf))
        for i,stem in candidates:
            paths=censuses[i];directory,slash,leaf=stem.rpartition('/')
            cache=(directory+'/' if slash else '')+'__pycache__/'+leaf+'.'
            assert stem not in paths and not any(stem+suffix in paths for suffix in ('.py','.pyc',*importlib.machinery.EXTENSION_SUFFIXES)),name
            assert not any(p.startswith(cache) and p.endswith('.pyc') and '/' not in p[len(cache):] for p in paths),name
    return dict(names=names,scope='current declarations and re-censused held staged forests; not ambient or executed-request coverage')

_MARKER_COUNT=0
_MARKER_BYTES=0


def _stderr_record(value):
    global _MARKER_COUNT,_MARKER_BYTES
    raw=(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
    assert _MARKER_COUNT<12 and len(raw)<=8192 and _MARKER_BYTES+len(raw)<=64*1024
    written=os.write(2,raw)
    assert written==len(raw)
    _MARKER_COUNT+=1;_MARKER_BYTES+=len(raw)


def _phase(name,started,held):
    _stderr_record(dict(kind='held06-post-byte-custody-phase-v1',check_id=3,
        status='phase_completed',phase=name,elapsed_seconds=time.monotonic()-started,
        held=dict(files=len(held.files),total=held.total)))


def _failure(error,started,before=None,held_closed=False):
    # Telemetry failure must never replace the original exception. Omit closure
    # unless this control observed a normal held.close and all fields below.
    try:
        value=dict(kind='held06-post-byte-custody-failure-v1',check_id=3,status='FAIL',
            error_type=type(error).__name__,error=str(error)[:1024],
            elapsed_seconds=time.monotonic()-started)
        if held_closed and before is not None:
            try:
                after=len(os.listdir('/proc/self/fd'))
                children=Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split()
                threads=[name for name in os.listdir('/proc/self/task') if name!=str(os.getpid())]
                value['closure']=dict(fd_count_before=before,fd_count_after=after,
                    active_children=children,active_non_main_threads=threads,
                    held_close_completed=True,scope='current process observations only')
            except BaseException:pass
        if len((json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode())>8192:
            value.pop('closure',None)
        _stderr_record(value)
    except BaseException:pass


def main():
    started=time.monotonic()
    try:
        assert len(sys.argv)==1 and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
        assert Path(sys.executable).resolve()==Path('/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11')
        assert 'LD_PRELOAD' not in os.environ and 'LD_LIBRARY_PATH' not in os.environ
        initial_resources=resources(4<<30);absence=absent()
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
            assert len(raw)==65522 and hashlib.sha256(raw).hexdigest()==AUDITOR_SHA
        finally:os.close(fd)
        m=types.ModuleType('authenticated_cpu_data_auditor');m.__file__=str(AUDITOR)
        exec(compile(raw,str(AUDITOR),'exec'),m.__dict__)
        before=len(os.listdir('/proc/self/fd'));held=m.Held(deadline);prepbase=ROOT/m.OUTPUTS['prepare']
        try:
            assert held.file(AUDITOR,dict(size_bytes=65522,sha256=AUDITOR_SHA),1024**2,raw=True)==raw
            own=held.file(Path(__file__).resolve(),maximum=1024**2)
            current=module(held,ROOT/'scripts/audit_puck_cpu_held_runtime.py',AUDITOR_CURRENT_SHA)
            observation=module(held,ROOT/'scripts/audit_puck_cpu_runtime_characterization.py',OBS_AUDITOR_SHA)
            p,a,r,helpers=observation.support()
            for row in observation.SUPPORT:held.file(ROOT/row['path'],row,1024**2)
            frozen,frozenraw=held.json(CONFIGURATION,dict(size_bytes=CONFIGURATION.stat().st_size,sha256=CONFIG_SHA),1024**2,lf=True)
            current.configuration(frozen,False)
            for row in frozen['sources']:held.file(ROOT/row['path'],row,1024**2)
            for row in frozen['preparation_acceptance'].values():held.file(ROOT/row['path'],row,16*1024**2,raw=True)
            manifest,manifest_raw=held.json(ROOT/'docs/plans/puck-cpu-held-qualification-06-freeze.json',maximum=1024**2)
            assert manifest_raw==(json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()
            raw_paths={row['path'] for row in frozen['inputs'].values()}
            raw_paths.update(row['path'] for row in frozen['preparation_acceptance'].values())
            raw_paths.update('runs/puck-cpu-held-qualification-'+str(i).zfill(2)+'/result.json' for i in range(1,6))
            for row in manifest['pins']:held.file(ROOT/row['path'],row,16*1024**2,raw=row['path'] in raw_paths)
            assert manifest['source_commit']=='6a4ba958021c70f4ec310370b34923aa36324087' and manifest['observer_invocations']==1 and manifest['implicit_retry'] is False
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
            negative_absence=check_absences(current_dependency,current_dirs,frozen['negative_imports'])
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
            assert totals==dict(file_count=27255,directory_count=2076,input_bytes=1318494346)
        finally:
            held.close()
            held_closed=True
        after=len(os.listdir('/proc/self/fd'))
        assert before==after and not Path('/proc/self/task/'+str(os.getpid())+'/children').read_text().split() and len(os.listdir('/proc/self/task'))==1
        sampled=[]
        for identity in [(3569912,53431366),(3569913,53431366),(3569914,53431367)]:
            path=Path('/proc')/str(identity[0])/'stat'
            try:
                current=int(path.read_text().rsplit(')',1)[1].split()[19])
                matches=current==identity[1]
            except FileNotFoundError:matches=False
            assert not matches
            sampled.append(dict(pid=identity[0],start_ticks=identity[1],matching_identity_present=matches))
        result=dict(m.CLAIMS,kind='puck-cpu-held06-post-failure-byte-custody-v1',version=1,status='CURRENT_BYTES_PRESERVED_AFTER_FAILED06',scope='post-failure current source/input/SITE/staged/native/interpreter bytes only; no allocation, target import or runtime acceptance',preparation_configuration_sha256=PREP_SHA,preparation_result_sha256=RESULT_SHA,dependencies_sha256=DEP_SHA,auditor_source_sha256=AUDITOR_SHA,runner_sha256=own['sha256'],baseline=summary,root_count=4,historical_capsule_files=34,input_pins=16,**totals,closure=dict(fd_count_before=before,fd_count_after=after,active_children=[],active_non_main_threads=[]),elapsed_seconds=time.monotonic()-started,qualifications01_02_03_04_05_06_still_failed_consumed=True,qualification06_invoked=True,configuration_sha256=CONFIG_SHA,current_auditor_sha256=AUDITOR_CURRENT_SHA,resources_before=initial_resources,resources_after=final_resources,absence=absence,site_files=27225,site_directories=2074,site_bytes=1304701872,process_identity_samples=sampled,process_scope='three recorded identities only; nonexhaustive non-atomic lifetime observation',current_sources=24,current_inputs=16,negative_absence=negative_absence,source_commit='6a4ba958021c70f4ec310370b34923aa36324087')
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
