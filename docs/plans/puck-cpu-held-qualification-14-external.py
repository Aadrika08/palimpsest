"""Fixed bounded external coordinator for the three extended-clock qualification14 phases on preparation03."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

ROOT=Path('/home/utkarsh/.codex/worktrees/0071/brain')
FREEZE=ROOT/'docs/plans/puck-cpu-held-qualification-14-freeze.json'
FREEZE_SHA='7cecde69672e25b68ebff99f5e007d65d2a91da5d2ad896ee84d2e3f4ce27971'
PYTHON='/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'


def stream_pin(path):
    digest=hashlib.sha256();size=0
    with path.open('rb') as stream:
        while block:=stream.read(1024**2):
            size+=len(block);assert size<=16*1024**2;digest.update(block)
    return dict(path=str(path),size_bytes=size,sha256=digest.hexdigest())


def main():
    started=time.monotonic()
    assert len(sys.argv)==2 and sys.argv[1] in ('admission','observer','audit')
    assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
    assert Path(sys.executable).resolve()==Path(PYTHON)
    assert 'LD_PRELOAD' not in os.environ and 'LD_LIBRARY_PATH' not in os.environ
    phase=sys.argv[1];budget=440 if phase=='observer' else 145;deadline=started+budget
    with FREEZE.open('rb') as stream:raw=stream.read(1024**2+1)
    assert len(raw)==698687 and hashlib.sha256(raw).hexdigest()==FREEZE_SHA
    value=json.loads(raw)
    if phase=='audit':
        with Path('/tmp/palimpsest-held14-concrete-audit-command.json').open('rb') as stream:
            raw=stream.read(64*1024+1)
        assert len(raw)<=64*1024
        command=json.loads(raw)['command'];prefix=value['commands']['auditor_prefix']
        assert command[:len(prefix)]==prefix and command[-2:]==['--output',value['commands']['auditor_output']]
        assert len(command)==len(prefix)+3
    else:command=value['commands'][phase]
    stem=Path('/tmp/palimpsest-held14-'+phase+'-external')
    receipt_path=Path(str(stem)+'.json')
    streams={name:Path(str(stem)+'.'+name) for name in ('stdout','stderr')}
    assert all(not os.path.lexists(path) for path in [receipt_path,*streams.values()])
    with receipt_path.open('x') as receipt:
        with streams['stdout'].open('xb') as stdout,streams['stderr'].open('xb') as stderr:
            try:
                remaining=deadline-time.monotonic();assert remaining>0
                process=subprocess.run(command,cwd=ROOT,env=value['outer_environment'],stdin=subprocess.DEVNULL,
                    stdout=stdout,stderr=stderr,timeout=remaining,close_fds=True)
                result=dict(returncode=process.returncode,timed_out=False)
            except subprocess.TimeoutExpired:result=dict(returncode=None,timed_out=True)
            except OSError as error:
                result=dict(returncode=None,timed_out=False,error_type=type(error).__name__,error=str(error)[:1024])
        result.update(kind='puck-cpu-held14-external-transport-v1',phase=phase,
            command=command,cwd=str(ROOT),environment=value['outer_environment'],
            external_deadline_seconds=budget,
            stdout=stream_pin(streams['stdout']),stderr=stream_pin(streams['stderr']),
            implicit_retry=False,runtime_qualified=False,study_authorized=False)
        result['elapsed_seconds']=time.monotonic()-started
        if result['elapsed_seconds']>=budget:result['timed_out']=True
        result['normal_exit']=type(result['returncode']) is int and result['returncode']>=0 and not result['timed_out']
        raw=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n'
        assert len(raw.encode())<=64*1024
        receipt.write(raw);receipt.flush();os.fsync(receipt.fileno())
    accepted=result['returncode']==0 and not result['timed_out'] and time.monotonic()<deadline
    summary=json.dumps(dict(receipt=str(receipt_path),returncode=result['returncode'],timed_out=result['timed_out'],
        elapsed_seconds=time.monotonic()-started,accepted=accepted,stdout=result['stdout'],stderr=result['stderr']),
        sort_keys=True,allow_nan=False)
    assert len(summary.encode())<=4096
    print(summary,flush=True)
    return 0 if accepted and time.monotonic()<deadline else 1


if __name__=='__main__':raise SystemExit(main())
