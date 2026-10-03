"""Verify cached CPU lab operation in an isolated Linux network namespace.

Only the child namespace's loopback interface is enabled. No host interface,
route, firewall or sysctl is changed. A namespace denial is reported as blocked.
The default short API smoke does not qualify browser performance or full Flynn.
--setup verifies a fresh checkout using local Git objects and cached packages.
--setup-only avoids simulation; --full-flynn adds the actual CPU lab verifier.
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


def cached_setup(args, run):
    """Fresh local checkout/environment; no source environment or assets copied."""
    checkout = args.output / 'checkout'
    run(['git', 'clone', '--shared', '--no-checkout', str(args.repo), str(checkout)], args.output)
    commit = source_identity(args.repo)['commit']
    run(['git', 'checkout', '--detach', commit], checkout)
    upstream = 'upstream/fly-gym'
    pinned = subprocess.check_output(['git', 'rev-parse', f'HEAD:{upstream}'], cwd=checkout, text=True, timeout=5.).strip()
    run(['git', 'config', f'submodule.{upstream}.url', str(args.repo / upstream)], checkout)
    run(['git', 'clone', '--shared', '--no-checkout', str(args.repo / upstream), str(checkout / upstream)], checkout)
    run(['git', 'checkout', '--detach', pinned], checkout / upstream)
    run(['git', 'submodule', 'status'], checkout)
    if source_identity(checkout) != source_identity(args.repo):
        raise RuntimeError('Fresh checkout differs from the measured source commit/files')
    environment = os.environ.copy()
    environment.pop('VIRTUAL_ENV', None)
    environment.update(UV_PROJECT_ENVIRONMENT=str(checkout / '.venv'), UV_PYTHON_DOWNLOADS='never',
                       UV_OFFLINE='true', PYTHONPATH=str(checkout / 'src'), MUJOCO_GL='egl',
                       MPLBACKEND='Agg', OMP_NUM_THREADS='2')
    run(['uv', '--version'], checkout, environment)
    run(['uv', 'sync', '--locked', '--offline', '--extra', 'simulation', '--extra', 'lab'], checkout, environment)
    run([str(checkout / '.venv/bin/python'), '--version'], checkout, environment)
    run(['uv', 'pip', 'freeze', '--offline', '--python', str(checkout / '.venv/bin/python')], checkout, environment)
    node = (checkout / 'ui/.node-version').read_text().strip()
    if node != '24.21.0':
        raise RuntimeError(f'Expected pinned Node 24.21.0, found {node}')
    run(['mise', 'exec', f'node@{node}', '--', 'node', '--version'], checkout, environment)
    run(['mise', 'exec', f'node@{node}', '--', 'npm', 'ci', '--offline', '--ignore-scripts'], checkout / 'ui', environment)
    run(['mise', 'exec', f'node@{node}', '--', 'npm', 'run', 'build'], checkout / 'ui', environment)
    run(['uv', 'run', '--offline', '--no-sync', 'palimpsest', '--help'], checkout, environment)
    run([str(checkout / '.venv/bin/python'), '-c',
         'import pathlib,palimpsest; print(pathlib.Path(palimpsest.__file__).resolve()); '
         f'assert pathlib.Path(palimpsest.__file__).resolve().is_relative_to(pathlib.Path({str(checkout / "src")!r}))'],
        checkout, environment)
    run(['git', 'diff', '--exit-code', '--submodule=short'], checkout, environment)
    paths = [checkout / 'uv.lock', checkout / 'ui/package-lock.json', checkout / 'ui/.node-version',
             *sorted((checkout / 'ui/dist').rglob('*'))]
    report = {'status': 'passed', 'checkout': str(checkout), 'source': source_identity(checkout),
              'upstream_commit': pinned, 'node_pin': node, 'assets': str(args.assets),
              'assets_shared_not_copied': True,
              'files_sha256': {str(p.relative_to(checkout)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in paths if p.is_file()},
              'limitations': ['Existing Git objects, Python/Node installations and package caches are required',
                              'Shared Git object sources must remain available', 'CLI help is not a live server launch']}
    write_json(args.output / 'setup.json', report)
    return checkout, environment


def inside(args):
    proof = {'version': 1, 'status': 'running', 'host_net': args.host_net, 'host_user': args.host_user,
             'child_net': namespace('net'), 'child_user': namespace('user')}
    proof_path = args.output / 'network.json'
    child = None
    observed = {}
    proof['commands'] = []

    def run(command, cwd, environment=None, timeout=300.):
        nonlocal child
        record = {'argv': command, 'cwd': str(cwd), 'started_unix': time.time()}
        proof['commands'].append(record)
        write_json(proof_path, proof)
        started = time.monotonic()
        child = subprocess.Popen(command, cwd=cwd, env=environment)
        while child.poll() is None:
            for row in descendants(os.getpid()):
                try:
                    key = f"{row['pid']}:{row['start_ticks']}"
                    observed[key] = {'pid': row['pid'], 'command': row['command'], 'net': namespace('net', row['pid'])}
                except (FileNotFoundError, ProcessLookupError):
                    pass
            if time.monotonic() - started > timeout:
                raise TimeoutError(f'Offline command exceeded {timeout} seconds: {command[0]}')
            time.sleep(.1)
        record.update(returncode=child.returncode, wall_seconds=time.monotonic() - started)
        write_json(proof_path, proof)
        if child.returncode:
            raise subprocess.CalledProcessError(child.returncode, command)
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
        root, environment = cached_setup(args, run) if args.setup else (args.repo, None)
        executable = str(root / '.venv/bin/python') if args.setup else sys.executable
        if args.full_flynn:
            run([executable, str(root / 'scripts/verify_lab.py'), '--repo', str(root), '--assets', str(args.assets),
                 '--controller', 'flynn', '--output', str(args.output / 'full-flynn')], root,
                environment or {**os.environ, 'PYTHONPATH': str(root / 'src'), 'MUJOCO_GL': 'egl',
                                'MPLBACKEND': 'Agg', 'OMP_NUM_THREADS': '2'}, timeout=1200.)
        command = [executable, str(root / 'scripts/verify_endurance.py'), '--repo', str(root),
                   '--assets', str(args.assets), '--output', str(args.output / 'api-smoke'),
                   '--duration', str(args.duration), '--cycle-seconds', '15', '--pause-seconds', '0',
                   '--sample-seconds', '2', '--controllers', 'manual', 'teacher']
        if not args.setup_only:
            run(command, root, environment, timeout=args.duration + 90.)
        proof['observed_processes'] = list(observed.values())
        proof['all_observed_descendants_isolated'] = bool(observed) and all(row['net'] == proof['child_net'] for row in observed.values())
        proof['smoke_returncode'] = None if args.setup_only else child.returncode
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
    scope = ['OS network isolation'] + (['fresh cached Python/Node setup'] if args.setup else [])
    if not args.setup_only:
        scope.append('actual cached CPU manual/teacher API smoke')
    if args.full_flynn:
        scope.append('actual CPU full-FLYNN lab verification')
    report = {'version': 1, 'status': 'running', 'scope': ' + '.join(scope),
              'limitations': ['Not 60-minute endurance or browser performance'] +
                            ([] if args.full_flynn else ['No full-Flynn offline qualification']),
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
        command += ['--setup'] if args.setup else []
        command += ['--setup-only'] if args.setup_only else []
        command += ['--full-flynn'] if args.full_flynn else []
        with (args.output / 'stdout.log').open('x') as stdout, (args.output / 'stderr.log').open('x') as stderr:
            child = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
            while child.poll() is None:
                for row in descendants(child.pid):
                    known[row['pid']] = row
                if interrupted:
                    raise InterruptedError(f'Interrupted by signal {interrupted[0]}')
                if time.monotonic() - started > args.duration + 90. + (900. if args.setup else 0.) + (1200. if args.full_flynn else 0.):
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
        report['evidence'] = {str(path.relative_to(args.output)): {
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'size_bytes': path.stat().st_size}
            for path in (args.output / 'network.json', args.output / 'setup.json',
                         args.output / 'full-flynn/verification.json', args.output / 'api-smoke/report.json',
                         args.output / 'stdout.log', args.output / 'stderr.log') if path.is_file()}
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
    parser.add_argument('--setup', action='store_true', help='Build a fresh shared local clone from cached Python/Node dependencies')
    parser.add_argument('--setup-only', action='store_true', help='Only verify namespace isolation and cached setup; no simulation')
    parser.add_argument('--full-flynn', action='store_true', help='Also run the actual CPU full-FLYNN lab verifier in the isolated namespace')
    parser.add_argument('--inside', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--host-net', help=argparse.SUPPRESS)
    parser.add_argument('--host-user', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 45 <= args.duration <= 300:
        parser.error('This short offline smoke requires 45–300 seconds')
    if args.setup_only:
        args.setup = True
    if args.setup_only and args.full_flynn:
        parser.error('--setup-only cannot run --full-flynn')
    args.repo, args.output = args.repo.resolve(), args.output.resolve()
    args.assets = (args.assets or args.repo / 'data/assets/flynn').resolve()
    raise SystemExit(inside(args) if args.inside else main(args))
