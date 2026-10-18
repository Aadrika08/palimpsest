"""Read-only admission of installed package data; no installer or runtime execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import signal
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
OUTPUT='runs/puck-cpu-retained-admission-01'
SITE='runs/puck-cpu-install-01/site'
MiB=1024**2
LIMITS=dict(normal_seconds=180,hard_seconds=195,address_space_bytes=1024*MiB,rss_bytes=512*MiB,
            output_bytes=32*MiB,min_free_bytes=4096*MiB,min_available_ram_bytes=2048*MiB,
            max_files=40000,max_directories=5000,max_file_bytes=1024*MiB,total_bytes=3072*MiB,max_fds=40000)
INERT=dict(path='numpy/distutils/__pycache__/conv_template.cpython-311.pyc',size_bytes=14203,
           sha256='6bfa3ef61560b422e0ef918673b642803b958f21edcd27c882ba4857e63d5177')
CLAIMS=dict(package_preparation_accepted=False,runtime_qualified=False,numerical_imports_executed=False,
            study_authorized=False,collection_authorized=False)
CODE_PATHS=tuple(sorted((
    'scripts/admit_puck_retained_installation.py','scripts/build_puck_python_louvain.py',
    'scripts/install_puck_cpu.py','scripts/acquire_puck_cpu_payloads.py',
    'src/palimpsest/__init__.py','src/palimpsest/bounded_qualification.py','src/palimpsest/evaluate.py',
    'src/palimpsest/puck_execution_files.py','src/palimpsest/puck_package_payloads.py',
    'src/palimpsest/puck_build_inputs.py','src/palimpsest/puck_retained_installation.py',
    'docs/plans/puck-cpu-retained-installation-admission-v1.md',
    'docs/plans/puck-cpu-retained-installation-admission-execution-v1.md','pyproject.toml','uv.lock')))


def require_fd_budget(needed):
    soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    if needed>LIMITS['max_fds'] or min(soft,hard)<LIMITS['max_fds']:
        raise ValueError('Insufficient admitted file descriptor budget')


def completion_state(before):
    children=Path(f'/proc/self/task/{os.getpid()}/children').read_text().split()
    threads=[t.name for t in threading.enumerate() if t is not threading.main_thread()]
    if children:raise ValueError('Unexpected admission child process')
    if threads:raise ValueError('Admission thread still active')
    after=len(os.listdir('/proc/self/fd'))
    if after!=before:raise ValueError('Admission file descriptor closure mismatch')
    return dict(active_children=[],active_non_main_threads=[],all_receipts_fsynced=True,
                all_handles_closed=True,fd_count_before=before,fd_count_after=after)


class Budget:
    def __init__(self,root,output,deadline):
        self.root,self.output,self.deadline=root,output,deadline
        self.last=0.;self.peak=0;self.observations=0

    def check(self):
        now=time.monotonic()
        if now>=self.deadline:raise TimeoutError('Retained admission normal deadline')
        if now-self.last<.05:return
        self.last=now;self.observations+=1
        rss=int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
        self.peak=max(self.peak,rss)
        if rss>LIMITS['rss_bytes']:raise ValueError('Sampled admission RSS stop')
        if shutil.disk_usage(self.root).free<LIMITS['min_free_bytes']:raise ValueError('Admission disk floor')
        if self.output.exists():
            from palimpsest.bounded_qualification import _output_bytes
            if _output_bytes(self.output,max_files=16,max_directories=1)>LIMITS['output_bytes']:
                raise ValueError('Admission aggregate output cap')


def parent(path,digest,started):
    sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
    import acquire_puck_cpu_payloads as a
    import build_puck_python_louvain as build
    import install_puck_cpu as installation
    from palimpsest.bounded_qualification import reserve_output,write_new,_group_members
    from palimpsest.puck_retained_installation import AdmissionInputs,HeldInstalledFiles,validate_inert_files
    normal=started+LIMITS['normal_seconds']
    if Path(sys.executable).resolve()!=Path(PYTHON) or os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH'):
        raise ValueError('Admission interpreter or loader environment differs')
    row=dict(path=path.relative_to(ROOT).as_posix(),size_bytes=path.lstat().st_size,sha256=digest)
    with AdmissionInputs(ROOT,[row],normal) as inputs:config=inputs.read_json(row['path'])
    if (config['kind']!='cpu-retained-installation-admission-v1' or config['version']!=1
            or config['output']!=OUTPUT or config['site_root']!=SITE or config['limits']!=LIMITS
            or config['data_only_pyc']!=INERT or config['empty_directories']!=['mujoco.libs','pandas.libs']
            or tuple(r['path'] for r in config['sources'])!=CODE_PATHS):
        raise ValueError('Unsupported retained admission configuration')
    entries=sorted([*config['sources'],*config['inputs'],row],key=lambda r:r['path'])
    available=int(next(line.split()[1] for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:')))*1024
    if available<LIMITS['min_available_ram_bytes'] or shutil.disk_usage(ROOT).free<LIMITS['min_free_bytes']:
        raise ValueError('Retained admission resource preflight')
    require_fd_budget(30000)
    resource.setrlimit(resource.RLIMIT_NOFILE,(LIMITS['max_fds'],LIMITS['max_fds']))
    resource.setrlimit(resource.RLIMIT_AS,(LIMITS['address_space_bytes'],LIMITS['address_space_bytes']))
    output=ROOT/OUTPUT
    with AdmissionInputs(ROOT,entries,normal):pass
    reserve_output(output,{'sources':{'root':str(ROOT),'files':entries},'installed':{'root':str(ROOT/SITE)}})
    write_new(output/'configuration.json',config)
    write_new(output/'invocation.json',dict(kind='cpu-retained-admission-invocation-v1',configuration_sha256=digest,
                                           started_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))
    before_fds=len(os.listdir('/proc/self/fd'));budget=Budget(ROOT,output,normal)
    result=dict(kind='cpu-retained-installation-admission-result-v1',status='FAIL',claims=dict(CLAIMS),
                configuration_sha256=digest,original_allocation_status='FAIL')
    try:
        with AdmissionInputs(ROOT,entries,normal) as inputs:
            get=lambda role:inputs.read_json(config['roles'][role])
            old,proof,inventory,layout,licences,baseline=(get(role) for role in ('original_result','proof','inventory','layout','licences','baseline'))
            if (old['status']!='FAIL' or old['claims']['installed'] is not False
                    or proof['status']!='PRESERVED_FAILURE_VERIFIED' or proof['accepted_installation'] is not False):
                raise ValueError('Original failed evidence differs')
            original=ROOT/'runs/puck-cpu-install-01'
            for name in ('inventory.json','licences.json','baseline-after.json','logs/namespace.json'):
                if os.path.lexists(original/name):raise ValueError('Original missing receipt was replaced')
            if _group_members(2370311) or _group_members(2370341):raise ValueError('Original worker group still active')
            files=inventory['entries'];directories=layout['predicted_destination_directories']
            if (len(files)!=27225 or len(directories)!=2074 or len(files)+len(directories)+len(entries)+512>LIMITS['max_fds']
                    or sum(r['size_bytes'] for r in files)!=1304701872
                    or sum(r['size_bytes'] for r in files)+sum(r['size_bytes'] for r in entries)>LIMITS['total_bytes']):
                raise ValueError('Measured namespace/resource binding differs')
            validate_inert_files(files,INERT)
            actual={r['path']:r for r in files};pins={r['path']:r for r in config['inputs']}
            if len(licences['entries'])!=96:raise ValueError('Licence count differs')
            for item in licences['entries']:
                relative=item['path'].removeprefix('licences/')
                copy='docs/reports/puck-cpu-install-01/failure-audit/'+item['path']
                if (not item['path'].startswith('licences/') or copy not in pins or relative not in actual
                        or any(item[k]!=actual[relative][k] or item[k]!=pins[copy][k] for k in ('size_bytes','sha256'))):
                    raise ValueError('Licence copy/source binding differs')
            uvpin=config['uv']
            if installation.file_hash(Path(uvpin['path']),normal)!={k:uvpin[k] for k in ('size_bytes','sha256')}:
                raise ValueError('Trusted installer pin changed')
            before=build.verify_baseline(baseline,normal);write_new(output/'baseline-before.json',before)
            with HeldInstalledFiles(ROOT/SITE,files,directories,normal,check=budget.check) as installed:
                budget.check()
                a.write_report(output/'inventory.json',dict(kind='puck-cpu-installed-files-v1',entries=files,
                    file_count=len(files),directory_count=len(directories),total_bytes=1304701872),16*MiB)
                after=build.verify_baseline(baseline,normal)
                if before!=after:raise ValueError('Trusted host baseline changed')
                if installation.file_hash(Path(uvpin['path']),normal)!={k:uvpin[k] for k in ('size_bytes','sha256')}:
                    raise ValueError('Trusted installer changed during admission')
                write_new(output/'baseline-after.json',after)
                installed.recheck();inputs.recheck();budget.check()
                snapshot=dict(kind='cpu-retained-installation-snapshot-v1',configuration_sha256=digest,
                    site_root=str(ROOT/SITE),data_only_pyc=INERT,original_allocation_status='FAIL',
                    custody=dict(file_count=len(files),directory_count=len(directories),regular_file_bytes=1304701872,exact_namespace=True))
                write_new(output/'snapshot.json',snapshot)
                installed.recheck();inputs.recheck()
            inputs.recheck()
        closure=completion_state(before_fds);budget.check()
        result.update(status='PASS',snapshot_sha256=installation.file_hash(output/'snapshot.json',normal)['sha256'],closure=closure,
                      sampled_peak_rss_bytes=budget.peak,resource_observations=budget.observations,
                      file_count=27225,directory_count=2074,regular_file_bytes=1304701872,
                      data_only_pyc=INERT,site_root=str(ROOT/SITE))
        result['claims']['package_preparation_accepted']=True
    except Exception as error:
        result.update(error_type=type(error).__name__,error=str(error))
    result['elapsed_seconds']=time.monotonic()-started
    write_new(output/'result.json',result)
    budget.check()
    completion_state(before_fds)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',type=Path,required=True);parser.add_argument('--sha256',required=True)
    args=parser.parse_args();started=time.monotonic()
    if os.getpgrp()!=os.getpid():os.setsid()
    previous=signal.signal(signal.SIGALRM,signal.SIG_DFL)
    signal.setitimer(signal.ITIMER_REAL,LIMITS['hard_seconds'])
    try:
        result=parent(args.configuration,args.sha256,started)
        print(json.dumps(result,sort_keys=True),flush=True)
        if time.monotonic()>=started+LIMITS['normal_seconds']:return 1
        return 0 if result['status']=='PASS' else 1
    finally:
        signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)


if __name__=='__main__':raise SystemExit(main())
