"""Record one exact characterization-04 parent CLI transport; grants no authority.

The parent's own clocks are 360/375/390 s. This observer waits up to 420 s for
the parent's normal return and arms an outer 435 s alarm, then records the exit,
both raw streams and their hashes in a private transport receipt.
"""
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
PARENT='scripts/characterize_puck_cpu_episode.py'
OUTPUT='runs/puck-cpu-runtime-characterization-04'
KIND='puck-cpu-runtime-characterization-v3'
TRANSPORT_KIND='puck-cpu-episode-characterization-cli-transport-v1'
NORMAL_SECONDS=420
HARD_SECONDS=435
CLEANUP_SECONDS=5
MAX_STREAM_BYTES=16*1024**2
ENVIRONMENT=dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')


def canonical(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def read(path,maximum):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>maximum:
            raise ValueError('Bounded single-link regular characterization-04 transport data required')
        with os.fdopen(os.dup(fd),'rb') as stream:raw=stream.read(maximum+1)
        stamp=lambda s:(s.st_dev,s.st_ino,s.st_mode,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
        if len(raw)!=before.st_size or stamp(before)!=stamp(os.fstat(fd)) or stamp(before)!=stamp(os.stat(path,follow_symlinks=False)):
            raise ValueError('Characterization-04 transport data changed while read')
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
        raise ValueError('Characterization-04 configuration must be inside its exact project root')
    raw=read(configuration,1024**2)
    if hashlib.sha256(raw).hexdigest()!=expected_sha256:raise ValueError('Characterization-04 configuration SHA differs')
    config=json.loads(raw)
    if (type(config) is not dict or config.get('kind')!=KIND or type(config.get('version')) is not int
            or config['version']!=3 or config.get('output')!=OUTPUT):
        raise ValueError('Exact characterization-04 identity required')
    paths={name:Path(OUTPUT+'-external-cli.'+name) for name in ('stdout','stderr')}
    receipt=Path(OUTPUT+'-external-cli-transport.json')
    if any(os.path.lexists(p) for p in [ROOT/OUTPUT,ROOT/receipt,*[ROOT/p for p in paths.values()]]):
        raise FileExistsError('Characterization-04 observation or allocation already reserved')
    command=[PYTHON,'-I','-S','-B',str(ROOT/PARENT),'--configuration',str(configuration),'--sha256',expected_sha256]
    process=None;timed_out=False
    with open(ROOT/paths['stdout'],'xb',buffering=0) as stdout:
        os.chmod(ROOT/paths['stdout'],0o600)
        with open(ROOT/paths['stderr'],'xb',buffering=0) as stderr:
            os.chmod(ROOT/paths['stderr'],0o600)
            try:
                remaining=started+NORMAL_SECONDS-time.monotonic()
                if remaining<=0:raise TimeoutError('Characterization-04 observation deadline before launch')
                process=subprocess.Popen(command,cwd=ROOT,env=ENVIRONMENT,stdin=subprocess.DEVNULL,
                    stdout=stdout,stderr=stderr,start_new_session=True,close_fds=True)
                try:process.wait(timeout=remaining)
                except subprocess.TimeoutExpired:timed_out=True;stop(process)
            finally:
                if process is not None and process.poll() is None:stop(process)
            os.fsync(stdout.fileno());os.fsync(stderr.fileno())
    result=dict(kind=TRANSPORT_KIND,configuration_sha256=expected_sha256,command=command,
        observed_returncode=process.returncode,elapsed_seconds=time.monotonic()-started,timed_out=timed_out)
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
    def alarm(signum,frame):raise TimeoutError('Characterization-04 observation outer alarm')
    signal.signal(signal.SIGALRM,alarm);signal.setitimer(signal.ITIMER_REAL,HARD_SECONDS)
    try:
        for key,value in (('NOFILE',40000),('AS',8192*1024**2),('FSIZE',1024**3)):
            resource.setrlimit(getattr(resource,'RLIMIT_'+key),(value,value))
        result=observe(args.configuration,args.sha256)
        print(canonical(result).decode(),end='',flush=True)
        return 0 if result['observed_returncode']==0 and not result['timed_out'] else 1
    finally:signal.setitimer(signal.ITIMER_REAL,0)


if __name__=='__main__':raise SystemExit(main())
