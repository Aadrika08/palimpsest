"""Fixed external transport for DATA-ONLY post06 byte/custody check03."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time


ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
SOURCE=Path('/tmp/palimpsest-held06-post-byte-custody-03.py')
SOURCE_SHA='96e496cef4ba2b1c2250e8a2a45737cb930b18cb019c8cc2b32d565830c522ff'
FREEZE=ROOT/'docs/plans/puck-cpu-held-qualification-06-freeze.json'
FREEZE_SHA='54dfca9f7a2bccff7a436e12d232f80944f564fce48a66480dacb77d1693e61c'
CONFIGURATION=ROOT/'docs/plans/puck-cpu-held-qualification-06.json'
CONFIGURATION_SHA='da630b05b871508686a4c92402725820b40b27253b2652b47c686a8f441a04e8'
SUCCESS=Path('/tmp/palimpsest-held06-post-byte-custody-03.json')
STDOUT=Path('/tmp/palimpsest-held06-post-byte-custody-03-external.stdout')
STDERR=Path('/tmp/palimpsest-held06-post-byte-custody-03-external.stderr')
RECEIPT=Path('/tmp/palimpsest-held06-post-byte-custody-03-external.json')
ABSENT07=[ROOT/'docs/plans'/name for name in (
    'puck-cpu-held-qualification-07.json','puck-cpu-held-qualification-07-admission.py',
    'puck-cpu-held-qualification-07-freeze.json')]+[
    ROOT/'runs'/('puck-cpu-held-qualification-07'+suffix) for suffix in (
        '', '-external-cli.stdout','-external-cli.stderr','-external-cli-transport.json')]+[
    Path('/tmp/palimpsest-puck-cpu-held-qualification-07-audit-01.json')]


def authenticate(path,size,digest):
    with path.open('rb') as stream:raw=stream.read(size+1)
    assert len(raw)==size and hashlib.sha256(raw).hexdigest()==digest
    return raw


def stream_pin(path):
    digest=hashlib.sha256();size=0
    with path.open('rb') as stream:
        while block:=stream.read(1024**2):
            size+=len(block);assert size<=16*1024**2;digest.update(block)
    return dict(path=str(path),size_bytes=size,sha256=digest.hexdigest())


def main():
    started=time.monotonic();deadline=started+145
    assert len(sys.argv)==1 and sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    assert Path(sys.executable).resolve()==Path(PYTHON)
    assert 'LD_PRELOAD' not in os.environ and 'LD_LIBRARY_PATH' not in os.environ
    authenticate(SOURCE,19086,SOURCE_SHA)
    frozen=json.loads(authenticate(FREEZE,73052,FREEZE_SHA))
    authenticate(CONFIGURATION,8995,CONFIGURATION_SHA)
    environment=frozen['outer_environment']
    assert environment==dict(PATH='/usr/bin:/bin',LANG='C.UTF-8',LC_ALL='C.UTF-8',PYTHONDONTWRITEBYTECODE='1')
    command=[PYTHON,'-I','-S','-B',str(SOURCE)]
    assert all(not os.path.lexists(path) for path in [SUCCESS,STDOUT,STDERR,RECEIPT,*ABSENT07])
    # Reserve the receipt before launch as well as both raw streams. A partial
    # reservation/failure remains consumed and cannot be overwritten by reentry.
    with RECEIPT.open('x') as receipt:
        with STDOUT.open('xb') as stdout,STDERR.open('xb') as stderr:
            try:
                remaining=deadline-time.monotonic();assert remaining>0
                process=subprocess.run(command,cwd=ROOT,env=environment,stdin=subprocess.DEVNULL,
                    stdout=stdout,stderr=stderr,timeout=remaining,close_fds=True)
                result=dict(returncode=process.returncode,timed_out=False)
            except subprocess.TimeoutExpired:result=dict(returncode=None,timed_out=True)
            except OSError as error:
                result=dict(returncode=None,timed_out=False,error_type=type(error).__name__,error=str(error)[:1024])
        result.update(kind='held06-post-byte-custody03-external-transport-v1',version=1,check_id=3,
            command=command,cwd=str(ROOT),environment=environment,external_deadline_seconds=145,
            source=dict(path=str(SOURCE),size_bytes=19086,sha256=SOURCE_SHA),
            configuration=dict(path=str(CONFIGURATION),size_bytes=8995,sha256=CONFIGURATION_SHA),
            freeze=dict(path=str(FREEZE),size_bytes=73052,sha256=FREEZE_SHA),
            stdout=stream_pin(STDOUT),stderr=stream_pin(STDERR),
            runtime_qualified=False,new_allocation_authorized=False,study_authorized=False,
            qualification_claims=[],implicit_retry=False)
        result['elapsed_seconds']=time.monotonic()-started
        if result['elapsed_seconds']>=145:result['timed_out']=True
        result['normal_exit']=type(result['returncode']) is int and result['returncode']>=0 and not result['timed_out']
        raw=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n'
        assert len(raw.encode())<=64*1024
        receipt.write(raw);receipt.flush();os.fsync(receipt.fileno())
    accepted=result['returncode']==0 and not result['timed_out'] and time.monotonic()<deadline
    summary=json.dumps(dict(receipt=str(RECEIPT),returncode=result['returncode'],
        timed_out=result['timed_out'],elapsed_seconds=time.monotonic()-started,
        accepted=accepted,stdout=result['stdout'],stderr=result['stderr']),sort_keys=True,allow_nan=False)
    assert len(summary.encode())<=4096
    print(summary,flush=True)
    return 0 if accepted and time.monotonic()<deadline else 1


if __name__=='__main__':raise SystemExit(main())
