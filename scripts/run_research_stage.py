#!/usr/bin/env python3
"""Run one research stage under a delegated systemd user unit with a cgroup CPU census.

Outer (host): admit the stage against its lane ledger using the stage's worst-case
CPU, durably reserve that worst case, then run

    systemd-run --user --wait --collect -p Delegate=yes -p CPUQuota=<k*100>%
                -p RuntimeMaxSec=<s> -p TimeoutStopSec=5 <this script> --inner ...

Inner (inside the unit): move itself into a `sup` leaf, start the workload in a
sibling `work` leaf (every descendant inherits it), sample the leaf every 0.25 s,
drain it, and write a receipt with `work` and `sup` cpu.stat usage. The unit's
cgroup disappears on exit, so the inner supervisor is the registrar.

Charge: measured `work + sup` usage when a complete receipt exists; otherwise the
full reserved worst case (an unknown tail is never charged as zero). There are no
retries: a refused or killed stage is an operational failure for the caller.
"""
import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

LANE_CAPS = {'audit': 3600.0, 'memory': 43200.0, 'puck': 18000.0,
             'navigation': 14400.0, 'final': 7200.0}
AGGREGATE_CAP = 86400.0
STOP_TIMEOUT = 5
SAMPLE_SECONDS = 0.25


# Ledger ---------------------------------------------------------------------------

def read_ledger(path):
    rows = []
    if os.path.exists(path):
        with open(path, encoding='utf-8') as stream:
            for line in stream:
                if line.strip():
                    rows.append(json.loads(line))
    return rows


def charges(rows):
    """Per-stage charge: the final 'charged' row, else the reservation (worst case)."""
    by_stage = {}
    for row in rows:
        key = (row['lane'], row['stage'])
        if row['event'] == 'reserved':
            by_stage.setdefault(key, row['cpu_seconds'])
        elif row['event'] == 'charged':
            by_stage[key] = row['cpu_seconds']
    return by_stage


def lane_totals(rows):
    totals = {lane: 0.0 for lane in LANE_CAPS}
    for (lane, _), seconds in charges(rows).items():
        totals[lane] += seconds
    return totals


def admit(rows, lane, stage, worst_case):
    if lane not in LANE_CAPS:
        raise ValueError(f'unknown lane {lane!r}')
    if not worst_case > 0:
        raise ValueError('worst-case CPU must be positive')
    if any((row['lane'], row['stage']) == (lane, stage) for row in rows):
        raise ValueError(f'stage {lane}/{stage} already has a ledger entry; no retries')
    totals = lane_totals(rows)
    if totals[lane] + worst_case > LANE_CAPS[lane]:
        raise ValueError(f'lane {lane}: charged {totals[lane]:.3f} + worst case {worst_case} '
                         f'exceeds cap {LANE_CAPS[lane]}')
    if sum(totals.values()) + worst_case > AGGREGATE_CAP:
        raise ValueError('aggregate 24 CPU-hour cap would be exceeded')
    return totals


def append(path, row):
    with open(path, 'a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, sort_keys=True) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


# Inner registrar --------------------------------------------------------------------

def _cgroup_dir():
    line = open('/proc/self/cgroup', encoding='utf-8').read().strip()
    return '/sys/fs/cgroup' + line.split(':', 2)[2]


def _read(path):
    with open(path, encoding='utf-8') as stream:
        return stream.read()


def _usage(leaf):
    for line in _read(os.path.join(leaf, 'cpu.stat')).splitlines():
        key, value = line.split()
        if key == 'usage_usec':
            return int(value) / 1e6
    raise RuntimeError('cpu.stat lacks usage_usec')


def _pids(leaf):
    return [int(p) for p in _read(os.path.join(leaf, 'cgroup.procs')).split()]


def _write_atomic(path, value):
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, indent=1)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.rename(tmp, path)
    fd = os.open(os.path.dirname(path), os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def inner(receipt_dir, command):
    started = time.monotonic()
    base = _cgroup_dir()
    sup, work = os.path.join(base, 'sup'), os.path.join(base, 'work')
    os.mkdir(sup)
    os.mkdir(work)
    with open(os.path.join(sup, 'cgroup.procs'), 'w') as stream:
        stream.write(str(os.getpid()))
    with open(os.path.join(base, 'cgroup.subtree_control'), 'w') as stream:
        stream.write('+cpu +memory +pids')

    def enter_work():
        with open(os.path.join(work, 'cgroup.procs'), 'w') as stream:
            stream.write(str(os.getpid()))

    samples = {'count': 0, 'peak_pids': 0, 'peak_memory_bytes': 0}
    done = threading.Event()

    def sample():
        while not done.is_set():
            try:
                samples['peak_pids'] = max(samples['peak_pids'], len(_pids(work)))
                samples['peak_memory_bytes'] = max(samples['peak_memory_bytes'],
                                                   int(_read(os.path.join(work, 'memory.current'))))
                samples['count'] += 1
            except OSError:
                pass
            done.wait(SAMPLE_SECONDS)

    with open(os.path.join(receipt_dir, 'stdout.log'), 'wb') as out, \
            open(os.path.join(receipt_dir, 'stderr.log'), 'wb') as err:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                 preexec_fn=enter_work)
        sampler = threading.Thread(target=sample, daemon=True)
        sampler.start()
        returncode = child.wait()
    deadline = time.monotonic() + STOP_TIMEOUT
    while _pids(work) and time.monotonic() < deadline:
        time.sleep(0.05)
    survivors = _pids(work)
    if survivors:
        with open(os.path.join(work, 'cgroup.kill'), 'w') as stream:
            stream.write('1')
        while _pids(work) and time.monotonic() < deadline + STOP_TIMEOUT:
            time.sleep(0.05)
    done.set()
    sampler.join()
    receipt = {
        'kind': 'research-stage-receipt-v1', 'complete': True, 'returncode': returncode,
        'survivors_killed': survivors, 'drained': not _pids(work),
        'work_cpu_seconds': _usage(work), 'supervisor_cpu_seconds': _usage(sup),
        'peak_memory_bytes': max(samples['peak_memory_bytes'],
                                 int(_read(os.path.join(work, 'memory.peak')))
                                 if os.path.exists(os.path.join(work, 'memory.peak')) else 0),
        'peak_pids': samples['peak_pids'], 'samples': samples['count'],
        'sample_seconds': SAMPLE_SECONDS, 'wall_seconds': time.monotonic() - started,
        'command': command, 'cgroup': base}
    receipt['cpu_seconds'] = receipt['work_cpu_seconds'] + receipt['supervisor_cpu_seconds']
    _write_atomic(os.path.join(receipt_dir, 'receipt.json'), receipt)
    return 0 if returncode == 0 and receipt['drained'] and not survivors else 1


def user_bus_env():
    """systemd-run --user needs the user bus even under a cleared (env -i) environment."""
    env = dict(os.environ)
    runtime = env.get('XDG_RUNTIME_DIR') or f'/run/user/{os.getuid()}'
    if not os.path.isdir(runtime):
        raise ValueError(f'no user runtime dir {runtime}; a systemd user manager is required')
    env['XDG_RUNTIME_DIR'] = runtime
    env.setdefault('DBUS_SESSION_BUS_ADDRESS', f'unix:path={runtime}/bus')
    return env


# Outer -----------------------------------------------------------------------------

def load_go(path, lane, stage):
    record = json.loads(Path(path).read_text(encoding='utf-8'))
    if record.get('lane') != lane or record.get('stage') != stage:
        raise ValueError(f'GO record names {record.get("lane")}/{record.get("stage")}, '
                         f'not {lane}/{stage}')
    for key in ('granted_by', 'granted_at', 'protocol_sha256'):
        if not str(record.get(key, '')).strip():
            raise ValueError(f'GO record lacks {key}')
    return record


def outer(args):
    receipt_dir = os.path.abspath(args.receipt_dir)
    if os.path.lexists(receipt_dir):
        raise ValueError(f'receipt dir must be fresh: {receipt_dir}')
    go = load_go(args.go_record, args.lane, args.stage)
    rows = read_ledger(args.ledger)
    totals = admit(rows, args.lane, args.stage, args.worst_case_cpu)
    unit_wall_cap = args.runtime_max_sec + STOP_TIMEOUT
    if args.worst_case_cpu < args.cpu_quota_k * unit_wall_cap:
        raise ValueError('worst-case CPU must cover k x (RuntimeMaxSec + stop timeout)')
    os.makedirs(receipt_dir)
    base = {'lane': args.lane, 'stage': args.stage, 'go_record': os.path.abspath(args.go_record),
            'protocol_sha256': go['protocol_sha256'], 'receipt_dir': receipt_dir}
    append(args.ledger, dict(base, event='reserved', cpu_seconds=float(args.worst_case_cpu),
                             lane_charged_before=totals[args.lane], at=time.time()))
    unit = ['systemd-run', '--user', '--wait', '--collect', '--quiet',
            '-p', 'Delegate=yes', '-p', f'CPUQuota={100 * args.cpu_quota_k}%',
            '-p', f'RuntimeMaxSec={args.runtime_max_sec}', '-p', f'TimeoutStopSec={STOP_TIMEOUT}',
            sys.executable, '-I', '-B', os.path.abspath(__file__), '--inner',
            '--receipt-dir', receipt_dir, '--', *args.command]
    finished = subprocess.run(unit, stdin=subprocess.DEVNULL, env=user_bus_env())
    receipt_path = os.path.join(receipt_dir, 'receipt.json')
    receipt = json.loads(Path(receipt_path).read_text()) if os.path.exists(receipt_path) else None
    if receipt and receipt.get('complete'):
        charged, basis = round(float(receipt['cpu_seconds']), 6), 'measured work+sup cpu.stat'
    else:
        charged, basis = float(args.worst_case_cpu), 'no complete receipt: worst case charged'
    append(args.ledger, dict(base, event='charged', cpu_seconds=charged, basis=basis,
                             unit_returncode=finished.returncode, at=time.time()))
    print(json.dumps({'charged_cpu_seconds': charged, 'basis': basis,
                      'unit_returncode': finished.returncode, 'receipt': receipt_path}))
    return 0 if finished.returncode == 0 and receipt else 1


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--inner', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--receipt-dir', required=True)
    parser.add_argument('--ledger')
    parser.add_argument('--lane', choices=sorted(LANE_CAPS))
    parser.add_argument('--stage')
    parser.add_argument('--go-record')
    parser.add_argument('--worst-case-cpu', type=float)
    parser.add_argument('--cpu-quota-k', type=int, default=1)
    parser.add_argument('--runtime-max-sec', type=int)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.command[:1] == ['--']:
        args.command = args.command[1:]
    if not args.command:
        parser.error('a command is required after --')
    if args.inner:
        return inner(args.receipt_dir, args.command)
    for name in ('ledger', 'lane', 'stage', 'go_record', 'worst_case_cpu', 'runtime_max_sec'):
        if getattr(args, name) in (None, ''):
            parser.error(f'--{name.replace("_", "-")} is required')
    try:
        return outer(args)
    except ValueError as error:
        print(f'refused: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
