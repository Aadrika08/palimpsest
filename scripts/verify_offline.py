"""Verify cached CPU lab operation in an isolated Linux network namespace.

Only the child namespace's loopback interface is enabled. No host interface,
route, firewall or sysctl is changed. A namespace denial is reported as blocked.
This short API smoke does not qualify browser performance or full Flynn offline.
"""

import argparse
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import time

from verify_endurance import descendants, process, source_identity, write_json


def namespace(kind, pid='self'):
    return os.readlink(f'/proc/{pid}/ns/{kind}')


def inside(args):
    proof = {'version': 1, 'status': 'running', 'host_net': args.host_net, 'host_user': args.host_user,
             'child_net': namespace('net'), 'child_user': namespace('user')}
    proof_path = args.output / 'network.json'
    child = None
    try:
        # Check both boundaries before the only network mutation in this script.
        mapping = Path('/proc/self/uid_map').read_text().split()
        proof['uid_map'] = mapping
        if (not args.host_net or not args.host_user or proof['child_net'] == args.host_net
                or proof['child_user'] == args.host_user or os.getuid() != 0
                or len(mapping) != 3 or mapping[0] != '0' or mapping[2] != '1'):
            raise RuntimeError('Refusing loopback setup outside a mapped user/network namespace')
        with open('/proc/self/ns/net', 'rb') as net:
            owner = fcntl.ioctl(net.fileno(), 0xb701)  # Linux NS_GET_USERNS.
            try:
                if os.fstat(owner).st_ino != os.stat('/proc/self/ns/user').st_ino:
                    raise RuntimeError('The network namespace is not owned by the mapped child user namespace')
                proof['network_owned_by_child_user'] = True
            finally:
                os.close(owner)
        subprocess.run(['ip', 'link', 'set', 'lo', 'up'], check=True, capture_output=True, text=True, timeout=5.)
        proof['interfaces'] = json.loads(subprocess.check_output(['ip', '-j', 'address'], text=True, timeout=5.))
        proof['routes_v4'] = json.loads(subprocess.check_output(['ip', '-j', 'route', 'show', 'table', 'all'], text=True, timeout=5.))
        proof['routes_v6'] = json.loads(subprocess.check_output(['ip', '-j', '-6', 'route', 'show', 'table', 'all'], text=True, timeout=5.))
        if {row['ifname'] for row in proof['interfaces']} != {'lo'}:
            raise RuntimeError('The isolated namespace unexpectedly has a non-loopback interface')
        if any(row.get('dev') != 'lo' for row in proof['routes_v4'] + proof['routes_v6']):
            raise RuntimeError('The isolated namespace unexpectedly has a non-loopback route')
        proof['external_connects'] = []
        for family, address in ((socket.AF_INET, ('1.1.1.1', 443)),
                                (socket.AF_INET6, ('2606:4700:4700::1111', 443))):
            with socket.socket(family, socket.SOCK_STREAM) as connection:
                connection.settimeout(2.)
                try:
                    connection.connect(address)
                except OSError as error:
                    proof['external_connects'].append({'address': address[0], 'errno': error.errno, 'message': str(error)})
                    if error.errno != errno.ENETUNREACH:
                        raise RuntimeError(f'External connection did not fail with ENETUNREACH: {error}') from error
                else:
                    raise RuntimeError('An external connection unexpectedly succeeded')
        proof['status'] = 'isolated'
        write_json(proof_path, proof)
        command = [sys.executable, str(Path(__file__).with_name('verify_endurance.py')), '--repo', str(args.repo),
                   '--assets', str(args.assets), '--output', str(args.output / 'api-smoke'),
                   '--duration', str(args.duration), '--cycle-seconds', '15', '--pause-seconds', '0',
                   '--sample-seconds', '2', '--controllers', 'manual', 'teacher']
        child = subprocess.Popen(command)
        observed = {}
        while child.poll() is None:
            for row in descendants(os.getpid()):
                try:
                    key = f"{row['pid']}:{row['start_ticks']}"
                    observed[key] = {'pid': row['pid'], 'command': row['command'], 'net': namespace('net', row['pid'])}
                except (FileNotFoundError, ProcessLookupError):
                    pass
            time.sleep(.1)
        proof['observed_processes'] = list(observed.values())
        proof['all_observed_descendants_isolated'] = bool(observed) and all(row['net'] == proof['child_net'] for row in observed.values())
        proof['smoke_returncode'] = child.returncode
        proof['status'] = 'passed' if child.returncode == 0 and proof['all_observed_descendants_isolated'] else 'failed'
    except Exception as error:
        proof.update(status='failed', error={'type': type(error).__name__, 'message': str(error)})
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGTERM)
            try:
                child.wait(timeout=35.)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=5.)
    write_json(proof_path, proof)
    return 0 if proof['status'] == 'passed' else 1


def main(args):
    args.output.mkdir(parents=True, exist_ok=False)
    host = {'net': namespace('net'), 'user': namespace('user')}
    report = {'version': 1, 'status': 'running', 'scope': 'OS network isolation + actual cached CPU manual/teacher API smoke',
              'limitations': ['Short smoke, not 60-minute endurance', 'No browser or full-Flynn offline qualification'],
              'host_before': host, 'duration': args.duration,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    write_json(args.output / 'report.json', report)
    child, interrupted, known = None, [], {}
    previous = {sig: signal.signal(sig, lambda number, frame: interrupted.append(number)) for sig in (signal.SIGINT, signal.SIGTERM)}
    started = time.monotonic()
    try:
        report['runtime_source'] = source_identity(args.repo)
        command = ['unshare', '--user', '--map-root-user', '--net', sys.executable, str(Path(__file__).resolve()),
                   '--inside', '--host-net', host['net'], '--host-user', host['user'], '--repo', str(args.repo),
                   '--assets', str(args.assets), '--output', str(args.output), '--duration', str(args.duration)]
        with (args.output / 'stdout.log').open('x') as stdout, (args.output / 'stderr.log').open('x') as stderr:
            child = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            while child.poll() is None:
                for row in descendants(child.pid):
                    known[row['pid']] = row
                if interrupted:
                    raise InterruptedError(f'Interrupted by signal {interrupted[0]}')
                if time.monotonic() - started > args.duration + 90.:
                    raise TimeoutError('Offline gate exceeded its bounded deadline')
                time.sleep(.1)
        proof_path = args.output / 'network.json'
        if proof_path.exists():
            proof = json.loads(proof_path.read_text())
            report.update(status='passed' if proof['status'] == 'passed' and child.returncode == 0 else 'failed',
                          network_proof='network.json', child_returncode=child.returncode)
        else:
            report.update(status='blocked', child_returncode=child.returncode,
                          reason=(args.output / 'stderr.log').read_text()[-4096:])
    except Exception as error:
        report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)})
    finally:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=35.)  # The API driver closes its own server group.
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5.)
        cleanup_deadline = time.monotonic() + 35.
        while time.monotonic() < cleanup_deadline:
            live = [current for pid, row in known.items() if (current := process(pid))
                    and current['state'] != 'Z' and current['start_ticks'] == row['start_ticks']]
            if not live:
                break
            time.sleep(.1)
        survivors = []
        for pid, row in known.items():
            current = process(pid)
            if current and current['state'] != 'Z' and current['start_ticks'] == row['start_ticks']:
                survivors.append(pid)
                os.kill(pid, signal.SIGKILL)
        report['owned_survivors_requiring_kill'] = survivors
        report['host_after'] = {'net': namespace('net'), 'user': namespace('user')}
        if 'runtime_source' in report:
            report['runtime_source_at_end'] = source_identity(args.repo)
            report['runtime_source_unchanged'] = report['runtime_source_at_end'] == report['runtime_source']
            if not report['runtime_source_unchanged']:
                report['status'] = 'failed'
        if report['host_after'] != host or survivors:
            report['status'] = 'failed'
        report['wall_seconds'] = time.monotonic() - started
        for sig, handler in previous.items():
            signal.signal(sig, handler)
        write_json(args.output / 'report.json', report)
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--duration', type=float, default=55.)
    parser.add_argument('--inside', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--host-net', help=argparse.SUPPRESS)
    parser.add_argument('--host-user', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 45 <= args.duration <= 300:
        parser.error('This short offline smoke requires 45–300 seconds')
    args.repo, args.output = args.repo.resolve(), args.output.resolve()
    args.assets = (args.assets or args.repo / 'data/assets/flynn').resolve()
    raise SystemExit(inside(args) if args.inside else main(args))
