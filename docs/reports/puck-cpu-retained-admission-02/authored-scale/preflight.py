import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import sys
import time

CPU = Path('/home/utkarsh/.codex/worktrees/0071/brain')
BASE = CPU / 'runs/puck-retained-scale-fixture-01'
REPORT = Path('/tmp/palimpsest-retained-scale-report-01.json')
MiB = 1024 ** 2
started = time.monotonic()
deadline = started + 120
signal.signal(signal.SIGALRM, signal.SIG_DFL)
signal.alarm(130)
resource.setrlimit(resource.RLIMIT_AS, (2048 * MiB, 2048 * MiB))
resource.setrlimit(resource.RLIMIT_NOFILE, (40000, 40000))
sys.path[:0] = [str(CPU / 'src'), str(CPU / 'scripts')]
from palimpsest.puck_retained_installation import HeldInstalledFiles
from palimpsest.bounded_qualification import write_new
from admit_puck_retained_installation import Budget

source_names = ('src/palimpsest/puck_retained_installation.py',
                'src/palimpsest/puck_execution_files.py',
                'scripts/admit_puck_retained_installation.py')
source_hashes = {name: hashlib.sha256((CPU / name).read_bytes()).hexdigest()
                 for name in source_names}
report = dict(kind='authored-retained-installation-scale-preflight-v1',
              status='FAIL', provenance='authored-only-no-target-packages-or-data',
              fixture_root=str(BASE), limits=dict(normal_seconds=120, hard_seconds=130,
              address_space_bytes=2048*MiB, sampled_rss_stop_bytes=512*MiB,
              regular_fixture_bytes=128*MiB, max_fds=40000, max_children=0),
              source_sha256=source_hashes, phases=[], runtime_qualified=False,
              accepted_installation=False, study_authorized=False, collection_authorized=False)
budget = None
peak_fd = 0
last_observation = -1
phase = 'preflight'

def children():
    return Path(f'/proc/self/task/{os.getpid()}/children').read_text().split()

def check():
    global peak_fd, last_observation
    if time.monotonic() >= deadline:
        raise TimeoutError('Authored scale normal deadline')
    if budget is not None:
        budget.check()
        if budget.observations != last_observation:
            last_observation = budget.observations
            peak_fd = max(peak_fd, len(os.listdir('/proc/self/fd')))
            if children():
                raise ValueError('Authored scale spawned a child')

def finish_phase(name, phase_start):
    global peak_fd
    check()
    fds = len(os.listdir('/proc/self/fd'))
    peak_fd = max(peak_fd, fds)
    row = dict(name=name, seconds=time.monotonic()-phase_start,
               elapsed_seconds=time.monotonic()-started, fd_count=fds,
               peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    report['phases'].append(row)
    print(json.dumps(row, sort_keys=True), flush=True)

try:
    if BASE.exists() or REPORT.exists():
        raise FileExistsError('Fresh one-shot authored paths required')
    if children():
        raise ValueError('Pre-existing child process')
    BASE.mkdir(mode=0o700)
    site, output = BASE/'site', BASE/'output'
    site.mkdir(mode=0o700)
    output.mkdir(mode=0o700)
    budget = Budget(CPU, output, deadline)
    fd_before = len(os.listdir('/proc/self/fd'))
    phase = 'fixture_creation'; mark = time.monotonic()
    directories = [f'd{number:04d}' for number in range(2072)]
    directories += ['empty-a', 'empty-b']
    for name in directories:
        check()
        (site/name).mkdir(mode=0o700)
    payloads = (b'', b'authored\n')
    digests = [hashlib.sha256(value).hexdigest() for value in payloads]
    entries, regular_bytes = [], 0
    for number in range(27225):
        check()
        relative = f'd{number % 2072:04d}/f{number:05d}.dat'
        data = payloads[number % 2]
        regular_bytes += len(data)
        if regular_bytes > 128*MiB:
            raise ValueError('Authored regular fixture byte cap')
        with (site/relative).open('xb') as handle:
            handle.write(data)
        entries.append(dict(path=relative, size_bytes=len(data), sha256=digests[number % 2]))
    entries.sort(key=lambda row:row['path'])
    directories.sort()
    report['fixture'] = dict(file_count=len(entries), directory_count=len(directories),
                            nonempty_directories=2072, explicit_empty_directories=2,
                            regular_file_bytes=regular_bytes)
    finish_phase(phase, mark)
    mark = time.monotonic()
    holder = HeldInstalledFiles(site, entries, directories, deadline, check=check)
    finish_phase('holder_construction', mark)
    phase = 'enter'; mark = time.monotonic()
    with holder:
        finish_phase(phase, mark)
        phase = 'explicit_recheck'; mark = time.monotonic()
        holder.recheck()
        finish_phase(phase, mark)
        phase = 'snapshot_write'; mark = time.monotonic()
        write_new(output/'snapshot.json', dict(kind='authored-scale-snapshot-v1',
                  provenance='authored-only', fixture=report['fixture'],
                  runtime_qualified=False, accepted_installation=False))
        finish_phase(phase, mark)
        phase = 'post_snapshot_recheck'; mark = time.monotonic()
        holder.recheck()
        finish_phase(phase, mark)
        phase = 'exit'; mark = time.monotonic()
    finish_phase(phase, mark)
    if len(os.listdir('/proc/self/fd')) != fd_before:
        raise ValueError('Authored scale FD closure mismatch')
    if children():
        raise ValueError('Authored scale child remains')
    if any(hashlib.sha256((CPU/name).read_bytes()).hexdigest() != digest
           for name,digest in source_hashes.items()):
        raise ValueError('Scale source changed during run')
    report.update(status='PASS', fd_count_before=fd_before,
                  fd_count_after=len(os.listdir('/proc/self/fd')), active_children=[])
except BaseException as error:
    report['failure'] = dict(phase=phase, type=type(error).__name__, message=str(error))
finally:
    report.update(elapsed_seconds=time.monotonic()-started,
                  peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                  sampled_peak_rss_bytes=budget.peak if budget else None,
                  resource_observations=budget.observations if budget else 0,
                  sampled_peak_fd_count=peak_fd)
    try:
        with REPORT.open('x') as handle:
            json.dump(report, handle, sort_keys=True, indent=2)
            handle.write('\n')
            handle.flush()
            os.fsync(handle.fileno())
        if time.monotonic() >= deadline and report['status'] == 'PASS':
            raise TimeoutError('Terminal report crossed normal deadline')
        print(json.dumps(dict(status=report['status'], elapsed_seconds=report['elapsed_seconds'],
              report=str(REPORT), failure=report.get('failure')), sort_keys=True), flush=True)
    finally:
        signal.alarm(0)
sys.exit(0 if report['status'] == 'PASS' else 1)
