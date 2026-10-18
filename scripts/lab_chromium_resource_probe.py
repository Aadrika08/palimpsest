"""Bounded, read-only sampler of Chromium resources during a lab browser run.

Runs a command (normally the Playwright lab workflow), and every ``--interval``
seconds records, for every Chromium descendant of that command: process type,
RSS, threads, open file descriptors, sockets, and the shared-memory backing
regions Chromium holds open or mapped (``.org.chromium.Chromium.*`` in TMPDIR
or /dev/shm, normally already unlinked, counted once per inode). It also records free bytes of the
filesystem that backs Chromium's shared memory. Output is one JSON object per
line, capped at ``--max-bytes``. Nothing is signalled, limited or reconfigured.

    python scripts/lab_chromium_resource_probe.py --out samples.jsonl \
        --shm-dir /tmp -- npx playwright test ...
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path


def children(pid):
    found = []
    try:
        for task in Path(f'/proc/{pid}/task').iterdir():
            raw = (task / 'children').read_text().split()
            found.extend(int(child) for child in raw)
    except OSError:
        pass
    return found


def descendants(root):
    seen, stack = [], [root]
    while stack:
        pid = stack.pop()
        for child in children(pid):
            if child not in seen:
                seen.append(child)
                stack.append(child)
    return seen


def process(pid):
    try:
        argv = Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
        status = Path(f'/proc/{pid}/status').read_text()
    except OSError:
        return None
    if len([arg for arg in argv if arg]) == 1:  # Chromium children rewrite their title
        argv = argv[0].split(b' ')
    exe = os.path.basename(argv[0].decode(errors='replace')) if argv and argv[0] else ''
    if 'chrom' not in exe:
        return None
    kind = 'browser'
    for arg in argv:
        if arg.startswith(b'--type='):
            kind = arg[7:].decode()
            if kind == 'utility':
                for other in argv:
                    if other.startswith(b'--utility-sub-type='):
                        kind = other.split(b'=', 1)[1].decode().rsplit('.', 1)[-1]
    fields = dict(line.split(':', 1) for line in status.splitlines() if ':' in line)
    row = {'pid': pid, 'type': kind, 'rss_kib': int(fields.get('VmRSS', '0 kB').split()[0]),
           'threads': int(fields.get('Threads', '0')), 'fds': 0, 'sockets': 0,
           'shm_fds': 0, 'memfd_fds': 0}
    shm = {}
    try:
        entries = os.listdir(f'/proc/{pid}/fd')
    except OSError:
        entries = []
    for name in entries:
        try:
            target = os.readlink(f'/proc/{pid}/fd/{name}')
        except OSError:
            continue
        row['fds'] += 1
        if target.startswith('socket:'):
            row['sockets'] += 1
        elif target.startswith('/memfd:') or '.org.chromium.' in target:
            try:
                info = os.stat(f'/proc/{pid}/fd/{name}')
            except OSError:
                continue
            row['memfd_fds' if target.startswith('/memfd:') else 'shm_fds'] += 1
            shm[info.st_ino] = max(shm.get(info.st_ino, 0), info.st_size)
    # Regions stay charged to the filesystem while mapped, even after the fd closes.
    try:
        maps = Path(f'/proc/{pid}/maps').read_text().splitlines()
    except OSError:
        maps = []
    for line in maps:
        parts = line.split(None, 5)
        if len(parts) == 6 and ('.org.chromium.' in parts[5] or parts[5].startswith('/memfd:')):
            low, high = (int(value, 16) for value in parts[0].split('-'))
            inode = int(parts[4])
            shm[inode] = max(shm.get(inode, 0), high - low)
    row['shm_regions'] = len(shm)
    row['shm_bytes'] = sum(shm.values())
    return row, shm
    for name in entries:
        try:
            target = os.readlink(f'/proc/{pid}/fd/{name}')
        except OSError:
            continue
        row['fds'] += 1
        if target.startswith('socket:'):
            row['sockets'] += 1
        elif target.startswith('/memfd:'):
            try:
                info = os.stat(f'/proc/{pid}/fd/{name}')
            except OSError:
                continue
            row['memfd_files'] += 1
            if info.st_ino not in seen:
                seen.add(info.st_ino)
                row['memfd_bytes'] += info.st_size
        elif '.org.chromium.' in target:
            try:
                info = os.stat(f'/proc/{pid}/fd/{name}')
            except OSError:
                continue
            row['shm_files'] += 1
            if info.st_ino not in seen:
                seen.add(info.st_ino)
                row['shm_bytes'] += info.st_size
                row['shm_alloc_bytes'] += info.st_blocks * 512
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--shm-dir', default=os.environ.get('TMPDIR', '/tmp'))
    parser.add_argument('--interval', type=float, default=.25)
    parser.add_argument('--max-bytes', type=int, default=8 * 1024**2)
    parser.add_argument('--timeout', type=float, default=240)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    start = time.monotonic()
    child = subprocess.Popen(command)
    written = 0
    peak = {}
    with args.out.open('w') as out:
        while True:
            found = [item for item in map(process, descendants(child.pid)) if item]
            rows = [row for row, _ in found]
            unique = {}
            for _, shm in found:
                for inode, size in shm.items():
                    unique[inode] = max(unique.get(inode, 0), size)
            disk = os.statvfs(args.shm_dir)
            sample = {'t': round(time.monotonic() - start, 3), 'shm_dir': args.shm_dir,
                      'shm_dir_free_bytes': disk.f_bavail * disk.f_frsize,
                      'unique_shm_regions': len(unique), 'unique_shm_bytes': sum(unique.values()),
                      'processes': rows}
            peak['unique_shm_regions'] = max(peak.get('unique_shm_regions', 0), len(unique))
            peak['unique_shm_bytes'] = max(peak.get('unique_shm_bytes', 0), sum(unique.values()))
            peak['min_shm_dir_free_bytes'] = min(peak.get('min_shm_dir_free_bytes', 1 << 62), sample['shm_dir_free_bytes'])
            for key in ('rss_kib', 'threads', 'fds', 'sockets'):
                peak[key] = max(peak.get(key, 0), sum(row[key] for row in rows))
            line = json.dumps(sample) + '\n'
            if written + len(line) <= args.max_bytes:
                out.write(line)
                written += len(line)
            if child.poll() is not None or time.monotonic() - start > args.timeout:
                break
            time.sleep(args.interval)
    if child.poll() is None:
        child.terminate()
        child.wait(10)
    summary = {'returncode': child.returncode, 'elapsed_seconds': round(time.monotonic() - start, 3),
               'peak_totals': peak, 'samples_bytes': written}
    print('CHROMIUM_RESOURCES ' + json.dumps(summary), file=sys.stderr)
    return child.returncode


if __name__ == '__main__':
    raise SystemExit(main())
