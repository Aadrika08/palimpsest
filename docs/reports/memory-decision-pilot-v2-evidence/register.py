"""One 180-second registration preparation; byte-only checks, no native owner."""
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time

from scripts import memory_decision_pilot as p, memory_selected_pilot as m


@contextmanager
def preparation_lease():
    # Reuse the real-user lease without budget.lock() creating fresh output roots.
    path = p.checked_path(Path.home()/'.cache/palimpsest/writer.lock')
    descriptor = os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(descriptor,'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise ValueError('Preparation requires the real-user writer lease')
        fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
        try:
            yield
        finally:
            fcntl.flock(stream,fcntl.LOCK_UN)


def prepare():
    started = time.monotonic();deadline = started+180
    evidence = Path(__file__).resolve().parent;repo = evidence.parents[2]
    path = evidence/'registration.json'
    control = repo/'.superpowers/sdd/memory-decision-pilot-v2-runtime'
    if path.exists() or control.exists():
        raise FileExistsError('Pilot registration/control already exists; no retry')
    if subprocess.check_output(['git','status','--porcelain'],cwd=repo):
        raise ValueError('Preparation requires clean committed software')
    prerequisite = repo.parent/'memory-prerequisites-v3/docs/reports/memory-prerequisites-v3-evidence/registration.json'
    with preparation_lease():
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        reg = m.build_registration(repo,prerequisite,stamp=stamp,deadline=deadline)
        p.safe_output(reg['output'],reg['protected_roots'])
        m.recheck_inputs(reg,deadline)
        storage = m.budget(reg)
        free = shutil.disk_usage(repo).free
        reserve = 8*p.GiB+2*p.GiB+64*p.MiB
        if free < reserve:
            raise ValueError('Preparation requires the 8 GiB reservation, 2 GiB floor and 64 MiB headroom')
        storage.check(0,path=path)
        p.deadline_check(deadline)
        reg.update(prepared_utc=datetime.now(timezone.utc).isoformat(),
            preparation_started_monotonic=started,preparation_deadline_monotonic=deadline,
            preparation_seconds_cap=180,preparation_seconds_before_write=time.monotonic()-started,
            preparation_free_bytes=free,reservation_bytes=8*p.GiB)
        p.write_control(path,reg,storage)
        p.deadline_check(deadline)
        # Commit only this machine registration; failure consumes this preparation.
        subprocess.run(['git','add',str(path)],cwd=repo,check=True,
                       timeout=max(.01,deadline-time.monotonic()))
        subprocess.run(['git','commit','-m','docs(memory): freeze one selected decision pilot allocation'],
                       cwd=repo,check=True,timeout=max(.01,deadline-time.monotonic()))
        p.deadline_check(deadline)
        print(json.dumps({'registration':str(path),'sha256':p.file_hash(path),
            'preserved_files':sum(len(row['files']) for row in reg['preserved_sets']),
            'elapsed_seconds':time.monotonic()-started,'qualification_claims':[]}),flush=True)
    return 0


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ['--bounded']:
        return prepare()
    if args:
        raise ValueError('Only one bounded preparation is supported')
    command = ['timeout','--signal=KILL','180s',sys.executable,
               str(Path(__file__).resolve()),'--bounded']
    return 0 if subprocess.run(command,cwd=Path(__file__).resolve().parents[3]).returncode == 0 else 1


if __name__ == '__main__':
    raise SystemExit(main())
