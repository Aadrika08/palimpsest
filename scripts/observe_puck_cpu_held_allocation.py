"""Record one exact CPU-parent CLI transport; grants no runtime authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
NORMAL_SECONDS=210
CLEANUP_SECONDS=5
HARD_SECONDS=225
MAX_STREAM_BYTES=16*1024**2
MAX_INHERITED_FILE_BYTES=1024**3
OUTPUTS=dict(prepare='runs/puck-cpu-held-preparation-01',qualify='runs/puck-cpu-held-qualification-01')
ENVIRONMENT=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def read(path,maximum):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>maximum:
            raise ValueError('Bounded single-link regular CPU transport data required')
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(maximum+1)
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if len(raw)!=before.st_size or stamp(before)!=stamp(os.fstat(fd)) or stamp(before)!=stamp(os.stat(path,follow_symlinks=False)):
            raise ValueError('CPU transport data changed while read')
        return raw
    finally:os.close(fd)


def stop(process):
    if process.poll() is None:
        try:os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError:pass
    process.wait(timeout=CLEANUP_SECONDS)


def observe(configuration,expected_sha256):
    started=time.monotonic();configuration=Path(configuration)
    if not configuration.is_absolute() or not configuration.is_relative_to(ROOT):
        raise ValueError('CPU configuration must be inside its exact project root')
    raw=read(configuration,1024**2)
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('CPU configuration SHA differs')
    config=json.loads(raw)
    if canonical(config)!=raw:raise ValueError('Canonical CPU configuration required')
    phase=config.get('phase')
    version={'puck-cpu-held-runtime-allocation-v2':2,'puck-cpu-held-runtime-allocation-v3':3,'puck-cpu-held-runtime-allocation-v4':4}.get(config.get('kind'))
    amended=version is not None
    if amended:
        if (phase!='qualify' or type(config.get('version')) is not int or config['version']!=version
                or type(config.get('allocation_id')) is not int or config['allocation_id']!=version):
            raise ValueError('Exact amended qualification allocation identity required')
        output_name={2:'runs/puck-cpu-held-qualification-02',3:'runs/puck-cpu-held-qualification-03',4:'runs/puck-cpu-held-qualification-04'}[version]
    else:
        if config.get('kind')!='puck-cpu-held-runtime-allocation-v1' or phase not in OUTPUTS:
            raise ValueError('Exact CPU parent allocation root and phase required')
        output_name=OUTPUTS[phase]
    if config.get('root')!=str(ROOT):raise ValueError('Exact CPU parent allocation root required')
    output=ROOT/output_name
    paths={name:Path(output_name+'-external-cli.'+name) for name in ('stdout','stderr')}
    receipt=Path(output_name+'-external-cli-transport.json')
    if any(os.path.lexists(p) for p in [output,ROOT/receipt,*[ROOT/p for p in paths.values()]]):
        raise FileExistsError('CPU external observation or allocation already reserved')
    command=[PYTHON,'-I','-S','-B',str(ROOT/'scripts/qualify_puck_cpu_held_runtime.py'),
             '--configuration',str(configuration),'--sha256',expected_sha256]
    process=None;timed_out=False
    with open(ROOT/paths['stdout'],'xb',buffering=0) as stdout:
        os.chmod(ROOT/paths['stdout'],0o600)
        with open(ROOT/paths['stderr'],'xb',buffering=0) as stderr:
            os.chmod(ROOT/paths['stderr'],0o600)
            try:
                remaining=started+NORMAL_SECONDS-time.monotonic()
                if remaining<=0:raise TimeoutError('CPU observation deadline before launch')
                process=subprocess.Popen(command,cwd=ROOT,env=ENVIRONMENT,
                    stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True,close_fds=True)
                try:process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:timed_out=True;stop(process)
            finally:
                if process is not None and process.poll() is None:stop(process)
            os.fsync(stdout.fileno());os.fsync(stderr.fileno())
    elapsed=time.monotonic()-started
    result=dict(kind='puck-cpu-held-cli-transport-v1',phase=phase,
        configuration_sha256=expected_sha256,command=command,
        observed_returncode=process.returncode,elapsed_seconds=elapsed,timed_out=timed_out)
    for name,path in paths.items():
        payload=read(ROOT/path,MAX_STREAM_BYTES)
        result[name]=dict(path=str(path),size_bytes=len(payload),sha256=hashlib.sha256(payload).hexdigest())
    with open(ROOT/receipt,'xb') as stream:
        os.chmod(ROOT/receipt,0o600);stream.write(canonical(result));stream.flush();os.fsync(stream.fileno())
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration',required=True,type=Path);parser.add_argument('--sha256',required=True)
    args=parser.parse_args()
    def alarm(signum,frame):raise TimeoutError('CPU observation outer alarm')
    signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,HARD_SECONDS)
    try:
        # Permit the parent's preparation payload ceiling; qualification narrows it.
        for key,value in (('NOFILE',40000),('AS',8192*1024**2),('FSIZE',MAX_INHERITED_FILE_BYTES)):
            resource.setrlimit(getattr(resource,'RLIMIT_'+key),(value,value))
        result=observe(args.configuration,args.sha256)
        print(canonical(result).decode(),end='',flush=True)
        return 0 if result['observed_returncode']==0 and not result['timed_out'] else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
