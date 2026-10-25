"""Real API/WebSocket endurance gate; a short duration is only a smoke test.

Example smoke: PYTHONPATH=src .venv/bin/python scripts/verify_endurance.py \
    --output runs/endurance-smoke --duration 45 --cycle-seconds 15 \
    --pause-seconds 0 --controllers manual

The default is 3600 seconds. This is a browser-independent client workload:
browser responsiveness and display FPS are separate. Optional CPU Flynn uses
the same mixed operations; its measured latency does not have a real-time gate.
"""

import argparse
import collections
import contextlib
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import threading
import time
import uuid

import httpx
from websockets.sync.client import connect


MAX_TIMINGS = 20_000


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, allow_nan=False, indent=2) + '\n')
    temporary.replace(path)


def source_identity(root):
    paths = [*sorted((root / 'src/palimpsest').glob('*.py')), root / 'pyproject.toml', root / 'uv.lock']
    files = {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
             for path in paths if path.is_file()}
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True, text=True, timeout=5.)
        commit = result.stdout.strip() if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        commit = None
    return {'commit': commit, 'files_sha256': files}


def summary(values):
    if not values:
        return {'count': 0}
    ordered = sorted(values)
    return {'count': len(values), 'min': ordered[0], 'mean': statistics.mean(values),
            'p50': ordered[math.ceil(len(values) * .5) - 1],
            'p95': ordered[math.ceil(len(values) * .95) - 1], 'max': ordered[-1]}


def process(pid):
    root = Path('/proc') / str(pid)

    def identity():
        fields = (root / 'stat').read_text().rsplit(') ', 1)[1].split()
        return {'pid': pid, 'ppid': int(fields[1]), 'group': int(fields[2]),
                'start_ticks': int(fields[19]), 'state': fields[0],
                'rss_bytes': 0, 'threads': int(fields[17]), 'fds': 0, 'command': ''}

    row = None
    try:
        row = identity()
        # Zombies retain identity but have released their address space and FDs.
        if row['state'] == 'Z':
            return row
        try:
            status = dict(line.split(':', 1) for line in (root / 'status').read_text().splitlines() if ':' in line)
            row.update(rss_bytes=int(status.get('VmRSS', '0 kB').split()[0]) * 1024,
                       threads=int(status['Threads']), fds=len(list((root / 'fd').iterdir())),
                       command=(root / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace')[:512])
            return row
        except PermissionError as error:
            # Exit can race resource inspection. Only an observed same-identity
            # zombie excuses denied access; an inaccessible live process does not.
            try:
                current = identity()
            except PermissionError:
                error.add_note('Process identity recheck was also inaccessible')
                raise error
            if current['state'] == 'Z' and all(current[key] == row[key] for key in ('start_ticks', 'group')):
                return current
            error.add_note(f'Process identity recheck: {current}')
            raise
    except (FileNotFoundError, ProcessLookupError):
        return None
    except PermissionError as error:
        error.add_note(f'Process inspection denied: pid={pid}, initial_identity={row}')
        raise


def descendants(server_pid):
    # Other users' FD directories may be protected: discover ancestry with stat,
    # then measure only our own descendants.
    ancestry = {}
    for path in Path('/proc').iterdir():
        if path.name.isdigit():
            try:
                ancestry[int(path.name)] = int((path / 'stat').read_text().rsplit(') ', 1)[1].split()[1])
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                continue
    selected, parents = {}, {server_pid}
    while parents:
        found = {pid for pid, parent in ancestry.items() if parent in parents and pid not in selected}
        selected.update({pid: process(pid) for pid in found})
        parents = found
    return [row for row in selected.values() if row is not None]


def root_bytes(root):
    total = 0
    for directory, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [name for name in dirs if not (Path(directory) / name).is_symlink()]
        for name in files:
            path = Path(directory) / name
            with contextlib.suppress(FileNotFoundError):
                if not path.is_symlink():
                    total += path.stat().st_size
    return total


def server_growth(path, duration):
    """Finite-window measurement, never a proof about arbitrary future runs."""
    warm, late = collections.defaultdict(list), collections.defaultdict(list)
    if not path.is_file():
        return {'status': 'unavailable'}
    with path.open() as stream:
        for line in stream:
            row = json.loads(line)
            target = warm if duration * .25 <= row['elapsed_seconds'] <= duration * .5 else (
                late if row['elapsed_seconds'] >= duration * .75 else None)
            if target is not None and row['server'] is not None:
                for name in ('rss_bytes', 'fds', 'threads'):
                    target[name].append(row['server'][name])
    if not warm or not late:
        return {'status': 'unavailable'}
    return {'status': 'measured', 'warm_window': [.25, .5], 'late_window': [.75, 1.],
            'scope': 'change in server p95 after warm-up; finite observation, not a mathematical growth bound',
            'p95_changes': {key: summary(late[key])['p95'] - summary(warm[key])['p95'] for key in warm}}


class DeadlineReached(Exception):
    pass


class Gate:
    def __init__(self, args, output, server):
        self.args, self.output, self.server = args, output, server
        self.started, self.deadline = time.monotonic(), time.monotonic() + args.duration
        self.stop, self.lock = threading.Event(), threading.Lock()
        self.failure, self.ws, self.active, self.signal = None, None, None, None
        self.known_children, self.resources, self.commands = {}, collections.deque(maxlen=1024), []
        self.stream_counts, self.controllers_seen, self.operations = collections.Counter(), set(), collections.Counter()
        self.http = httpx.Client(base_url=f'http://127.0.0.1:{args.port}/api/v1', trust_env=False,
                                 headers={'Origin': f'http://127.0.0.1:{args.port}'}, timeout=10.)

    def check(self):
        if self.failure:
            raise RuntimeError(self.failure)
        if self.signal is not None:
            raise InterruptedError(f'Interrupted by signal {self.signal}')
        if self.server.poll() is not None:
            raise RuntimeError(f'Lab server exited with code {self.server.returncode}')
        if time.monotonic() >= self.deadline:
            raise DeadlineReached()

    def request(self, method, path, value=None, *, allow_rejection=False):
        self.check()
        response = self.http.request(method, path, json=value, timeout=min(35., max(.1, self.deadline - time.monotonic())))
        if allow_rejection and response.status_code in (400, 409):
            return None
        response.raise_for_status()
        return response.json()

    def wait(self, identifier, predicate, timeout=180.):
        until = min(self.deadline, time.monotonic() + timeout)
        while time.monotonic() < until:
            view = self.request('GET', '/runs/' + identifier)
            if view['status'] == 'failed':
                raise RuntimeError(f'Owner {identifier} failed: {view.get("failure") or view.get("replay")}')
            if predicate(view):
                return view
            self.stop.wait(.025)
        self.check()
        raise TimeoutError(f'Owner {identifier} did not reach a boundary within {timeout:g}s')

    def command(self, identifier, kind, payload=None):
        state = self.request('GET', '/runs/' + identifier)['state']
        command_id = uuid.uuid4().hex
        before = time.monotonic()
        receipt = self.request('POST', f'/runs/{identifier}/commands', {
            'id': command_id, 'kind': kind, 'payload': payload or {}, 'expected_state': state['phase'],
            'expected_episode': state['episode'], 'expected_revision': state['revision']})
        acknowledgement = time.monotonic() - before
        view = self.wait(identifier, lambda v: any(r['id'] == command_id and r['status'] != 'queued' for r in v['receipts']))
        applied = next(r for r in view['receipts'] if r['id'] == command_id)
        if applied['status'] != 'applied':
            raise RuntimeError(f'Command not applied: {applied}')
        if len(self.commands) >= MAX_TIMINGS:
            raise RuntimeError('Bounded command timing limit reached')
        row = {'run_id': identifier, 'id': command_id, 'kind': kind,
               'http_receipt_seconds': acknowledgement, 'observed_application_seconds': time.monotonic() - before,
               'received_status': receipt['status'], 'receipt': applied}
        self.commands.append(row)
        with (self.output / 'commands.jsonl').open('a') as stream:
            stream.write(json.dumps(row, allow_nan=False) + '\n')
        self.operations[kind] += 1
        return view

    def close_run(self, identifier):
        view = self.request('POST', f'/runs/{identifier}/close', {})
        if view['status'] != 'closed':
            raise RuntimeError(f'Close failed: {view}')
        self.active = None

    def cycle(self, ordinal):
        controller = self.args.controllers[ordinal % len(self.args.controllers)]
        source = self.request('POST', '/runs', {'controller': controller, 'device': 'cpu',
            'scenario': 'sparse-navigation', 'texture': 'checker', 'seed': ordinal % 1000})['run_id']
        self.active = source
        view = self.wait(source, lambda v: v['status'] == 'ready' and v['sample'] is not None)
        self.controllers_seen.add(controller)
        goal = view['sample']['world']['goal'][:2]
        edit = None
        for xy in ([goal[0] + .1, goal[1]], [-5., -5.], [-5., 5.], [5., -5.], [5., 5.], [0., 3.]):
            payload = {'kind': 'move_goal', 'xy': xy}
            if self.request('POST', f'/runs/{source}/previews', {'payload': payload,
                    'expected_revision': view['state']['revision']}, allow_rejection=True) is not None:
                edit = payload
                break
        if edit is None:
            raise RuntimeError('Actual scenario has no valid tested goal placement')
        self.operations['preview'] += 1
        self.command(source, 'intervene', edit)
        self.command(source, 'set_eyes', {'left': False, 'right': True})
        if controller == 'manual':
            self.command(source, 'set_action', {'action': [.2, .1]})
        before = self.request('GET', '/runs/' + source)['state']['total_tick']
        view = self.command(source, 'step')
        if view['state']['total_tick'] != before + 1:
            raise RuntimeError('Paused step did not advance exactly one tick')
        simulation_start, run_started = view['state']['simulation_time'], time.monotonic()
        self.command(source, 'run')
        self.wait(source, lambda v: v['state']['total_tick'] >= before + 1 + self.args.burst_ticks)
        view = self.command(source, 'pause')
        run_wall = time.monotonic() - run_started
        run_simulated = view['state']['simulation_time'] - simulation_start
        snapshot = self.request('POST', f'/runs/{source}/snapshot', {'expected_revision': view['state']['revision']})['snapshot_id']
        self.operations['snapshot'] += 1
        self.command(source, 'reset', {'seed': ordinal % 1000})
        self.command(source, 'step')
        self.close_run(source)
        branch = self.request('POST', '/branches', {'source_run_id': source, 'snapshot_id': snapshot})['run_id']
        self.active = branch
        self.wait(branch, lambda v: v['status'] == 'ready' and v['sample'] is not None)
        self.operations['branch'] += 1
        self.command(branch, 'step')
        self.idle(min(self.args.pause_seconds, max(0., self.deadline - time.monotonic() - 15.)))
        self.close_run(branch)
        for mode in ('actions', 'policy'):
            replay = self.request('POST', f'/runs/{source}/replay', {'mode': mode})['run_id']
            self.active = replay
            view = self.wait(replay, lambda v: v['status'] == 'closed')
            if view.get('replay', {}).get('status') != 'passed':
                raise RuntimeError(f'{mode} replay failed: {view.get("replay")}')
            self.close_run(replay)
            self.operations['replay_' + mode] += 1
        playback = self.request('GET', f'/runs/{source}/playback?episode=0&tick=0')
        if playback['mode'] != 'playback':
            raise RuntimeError('Recorded playback was not labelled')
        self.operations['playback'] += 1
        return {'source_run_id': source, 'branch_run_id': branch, 'controller': controller, 'snapshot_id': snapshot,
                'active_run': {'simulated_seconds': run_simulated, 'observed_wall_seconds': run_wall,
                               'real_time_factor': run_simulated / run_wall,
                               'scope': 'small scheduled burst from run request to observed pause receipt; includes IPC/polling'}}

    def idle(self, seconds):
        until = min(self.deadline, time.monotonic() + seconds)
        while time.monotonic() < until:
            self.check()
            self.stop.wait(min(.2, until - time.monotonic()))

    def sample_resources(self):
        while not self.stop.is_set():
            try:
                server = process(self.server.pid)
                children = descendants(self.server.pid)
                with self.lock:
                    self.known_children.update({row['pid']: row['start_ticks'] for row in children})
                owners = [row for row in children if 'multiprocessing.spawn' in row['command'] and '--multiprocessing-fork' in row['command']]
                row = {'elapsed_seconds': time.monotonic() - self.started, 'server': server, 'children': children,
                       'owner_count': len(owners), 'root_bytes': root_bytes(self.output),
                       'free_disk_bytes': shutil.disk_usage(self.output).free}
                totals = [server] + children if server else children
                row.update(total_rss_bytes=sum(p['rss_bytes'] for p in totals),
                           total_fds=sum(p['fds'] for p in totals), total_threads=sum(p['threads'] for p in totals))
                with self.lock:
                    self.resources.append(row)
                with (self.output / 'resources.jsonl').open('a') as stream:
                    stream.write(json.dumps(row, allow_nan=False) + '\n')
                limits = [(len(owners) > 1, 'More than one simulation owner'),
                    (row['root_bytes'] > self.args.max_bytes, 'Evidence storage budget exceeded'),
                    (row['free_disk_bytes'] < self.args.min_free_bytes, 'Free disk below declared reserve'),
                    (row['total_rss_bytes'] > self.args.max_rss_mib * 1024**2, 'RSS budget exceeded'),
                    (row['total_fds'] > self.args.max_fds, 'FD budget exceeded'),
                    (row['total_threads'] > self.args.max_threads, 'Thread budget exceeded')]
                for exceeded, reason in limits:
                    if exceeded:
                        self.failure = reason
                        return
                print(json.dumps({'type': 'resource_sample', **{key: row[key] for key in
                    ('elapsed_seconds', 'owner_count', 'total_rss_bytes', 'total_fds', 'root_bytes', 'free_disk_bytes')}}), flush=True)
            except Exception as error:
                self.failure = f'Resource sampler failed: {type(error).__name__}: {error}'
                return
            self.stop.wait(self.args.sample_seconds)

    def stream(self, token):
        try:
            with connect(f'ws://127.0.0.1:{self.args.port}/api/v1/stream',
                         origin=f'http://127.0.0.1:{self.args.port}', proxy=None,
                         max_size=2 * 1024**2, max_queue=16, close_timeout=2.) as websocket:
                self.ws = websocket
                websocket.send(json.dumps({'token': token}))
                while not self.stop.is_set():
                    try:
                        message = json.loads(websocket.recv(timeout=.5))
                    except TimeoutError:
                        continue
                    if message.get('version') != 1:
                        raise RuntimeError('Unsupported stream message version')
                    self.stream_counts[message['type']] += 1
        except Exception as error:
            if not self.stop.is_set():
                self.failure = f'Authenticated stream failed: {type(error).__name__}: {error}'

    def cleanup(self):
        # Only our authenticated run and process groups are affected.
        if self.server is None:
            self.http.close()
            return {'server_exit_code': None, 'owned_survivors_requiring_kill': []}
        with contextlib.suppress(Exception):
            with self.lock:
                self.known_children.update({row['pid']: row['start_ticks'] for row in descendants(self.server.pid)})
        if self.active is not None and self.server.poll() is None:
            with contextlib.suppress(Exception):
                self.http.post(f'/runs/{self.active}/close', json={}, timeout=8.)
        self.stop.set()
        if self.ws is not None:
            with contextlib.suppress(Exception):
                self.ws.close()
        self.http.close()
        if self.server.poll() is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(self.server.pid, signal.SIGTERM)
            try:
                self.server.wait(timeout=12.)
            except subprocess.TimeoutExpired:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(self.server.pid, signal.SIGKILL)
                self.server.wait(timeout=3.)
        survivors = []
        with self.lock:
            known = dict(self.known_children)
        until = time.monotonic() + 3.
        while time.monotonic() < until:
            remaining = [pid for pid, start in known.items()
                         if (row := process(pid)) and row['start_ticks'] == start and row['state'] != 'Z']
            if not remaining:
                break
            time.sleep(.05)
        for pid, start in known.items():
            row = process(pid)
            if row and row['start_ticks'] == start and row['state'] != 'Z':
                survivors.append(pid)
                with contextlib.suppress(ProcessLookupError):
                    if row['group'] == pid:
                        os.killpg(pid, signal.SIGKILL)
                    else:
                        os.kill(pid, signal.SIGKILL)
        return {'server_exit_code': self.server.returncode, 'owned_survivors_requiring_kill': survivors}


def recorded_metrics(root):
    from palimpsest.records import iter_ticks
    policy, physics, intervals, runs = [], [], [], []
    for path in sorted((root / 'runs').glob('*/recording/manifest.json')):
        manifest = json.loads(path.read_text())
        if manifest['status'] != 'completed':
            runs.append({'run_id': path.parent.parent.name, 'status': manifest['status']})
            continue
        count, kernel_wall = 0, 0.
        for row in iter_ticks(path.parent):
            if len(policy) >= MAX_TIMINGS:
                raise RuntimeError('Bounded recorded timing limit reached')
            policy.append(float(row['latency']))
            physics.append(float(row['step_latency']))
            kernel_wall += float(row['latency']) + float(row['step_latency'])
            intervals.append(float(manifest['control_interval_seconds']))
            count += 1
        runs.append({'run_id': path.parent.parent.name, 'status': 'completed', 'recorded_ticks': count,
                     'simulated_seconds': count * float(manifest['control_interval_seconds']),
                     'controller_and_step_wall_seconds': kernel_wall})
    measured = sum(policy) + sum(physics)
    return {'policy_seconds': summary(policy), 'step_with_cameras_seconds': summary(physics),
            'recorded_ticks': len(policy), 'simulated_seconds': sum(intervals),
            'kernel_real_time_factor': sum(intervals) / measured if measured else None,
            'rtf_scope': 'recorded controller + physics/camera wall time; excludes loading, pause, IPC and recording', 'runs': runs}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--assets', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='exclusive new evidence directory')
    parser.add_argument('--duration', type=float, default=3600.)
    parser.add_argument('--cycle-seconds', type=float, default=60.)
    parser.add_argument('--pause-seconds', type=float, default=15.)
    parser.add_argument('--sample-seconds', type=float, default=5.)
    parser.add_argument('--burst-ticks', type=int, default=5)
    parser.add_argument('--controllers', nargs='+', choices=('manual', 'teacher', 'flynn'), default=['manual', 'teacher'])
    parser.add_argument('--port', type=int, default=0)
    parser.add_argument('--max-bytes', type=int, default=2 * 1024**3)
    parser.add_argument('--min-free-bytes', type=int, default=512 * 1024**2)
    parser.add_argument('--max-rss-mib', type=int, default=8192)
    parser.add_argument('--max-fds', type=int, default=1024)
    parser.add_argument('--max-threads', type=int, default=512)
    parser.add_argument('--max-server-growth-mib', type=int, default=128)
    parser.add_argument('--max-server-fd-growth', type=int, default=32)
    parser.add_argument('--max-server-thread-growth', type=int, default=16)
    args = parser.parse_args()
    if not (1 <= args.duration <= 86400 and 1 <= args.cycle_seconds <= 3600 and 0 <= args.pause_seconds <= 300
            and 1 <= args.sample_seconds <= 60 and 1 <= args.burst_ticks <= 50 and 0 <= args.port <= 65535):
        parser.error('Invalid duration, cadence, sample, tick or port bounds')
    if any(value <= 0 for value in (args.max_bytes, args.min_free_bytes, args.max_rss_mib, args.max_fds, args.max_threads,
                                   args.max_server_growth_mib, args.max_server_fd_growth, args.max_server_thread_growth)):
        parser.error('Resource budgets must be positive')
    if not 1024**2 <= args.max_bytes <= 100 * 1024**3 or args.min_free_bytes > 100 * 1024**3:
        parser.error('Storage bounds must fit the supported application quota flags')
    if not Path('/proc').is_dir():
        parser.error('This measured gate requires Linux /proc')
    root, output = args.repo.resolve(), args.output.resolve()
    args.assets = (args.assets or root / 'data/assets/flynn').resolve()
    output.mkdir(parents=True, exist_ok=False)
    if args.port == 0:
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            args.port = listener.getsockname()[1]
    environment = os.environ.copy()
    environment.update(PYTHONPATH=str(root / 'src'), MUJOCO_GL='egl', MPLBACKEND='Agg', OMP_NUM_THREADS='2')
    command = [sys.executable, '-m', 'palimpsest', '--repo', str(root), '--assets', str(args.assets),
               'lab', '--port', str(args.port), '--runs', str(output / 'runs'), '--exports', str(output / 'exports'),
               '--storage-max-bytes', str(args.max_bytes), '--min-free-bytes', str(args.min_free_bytes)]
    report = {'version': 1, 'status': 'running', 'qualification': 'endurance' if args.duration >= 3600 else 'short-smoke',
              'scope': 'actual loopback HTTP + authenticated WebSocket, CPU ' + ','.join(args.controllers) + '; browser-independent',
              'limitations': ['No browser FPS or sustained browser responsiveness claim',
                              'CPU Flynn only; no CUDA or full-model real-time qualification' if 'flynn' in args.controllers
                              else 'No full-FLYNN endurance claim',
                              'Observed application latency includes polling; receipt latency is measured separately'],
              'configuration': {key: value for key, value in vars(args).items() if not isinstance(value, Path)},
              'repo': str(root), 'cycles': [], 'source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    report['runtime_source'] = source_identity(root)
    write_json(output / 'report.json', report)
    with (output / 'server.stdout.log').open('x') as stdout, (output / 'server.stderr.log').open('x') as stderr:
        gate = Gate(args, output, None)
        previous = {sig: signal.signal(sig, lambda number, frame: setattr(gate, 'signal', number)) for sig in (signal.SIGINT, signal.SIGTERM)}
        threads = []
        try:
            server = subprocess.Popen(command, cwd=root, env=environment, stdout=stdout, stderr=stderr, start_new_session=True)
            gate.server = server
            startup = time.monotonic()
            while True:
                if gate.signal is not None:
                    raise InterruptedError(f'Interrupted by signal {gate.signal}')
                if server.poll() is not None or time.monotonic() - startup > 30.:
                    raise RuntimeError('Lab server failed to start within 30 seconds')
                try:
                    response = gate.http.get('/session', timeout=1.)
                    response.raise_for_status()
                    token = response.json()['token']
                    break
                except httpx.HTTPError:
                    time.sleep(.1)
            gate.http.headers['X-Palimpsest-Session'] = token
            gate.started = time.monotonic()
            gate.deadline = gate.started + args.duration
            for target in (gate.sample_resources, lambda: gate.stream(token)):
                thread = threading.Thread(target=target, daemon=True)
                threads.append(thread)
                thread.start()
            ordinal, last_cycle_seconds = 0, 0.
            while time.monotonic() < gate.deadline:
                if ordinal and gate.deadline - time.monotonic() < last_cycle_seconds + 5.:
                    gate.idle(gate.deadline - time.monotonic())
                    break
                before = time.monotonic()
                report['cycles'].append(gate.cycle(ordinal))
                last_cycle_seconds = time.monotonic() - before
                ordinal += 1
                report.update(completed_cycles=ordinal, operations=dict(gate.operations))
                write_json(output / 'report.json', report)
                gate.idle(max(0., args.cycle_seconds - last_cycle_seconds))
        except DeadlineReached:
            report['deadline_reached'] = True
        except Exception as error:
            report.update(status='failed', error={'type': type(error).__name__, 'message': str(error)})
        finally:
            report['measured_seconds'] = time.monotonic() - gate.started
            report['cleanup'] = gate.cleanup()
            for thread in threads:
                thread.join(timeout=3.)
            for sig, handler in previous.items():
                signal.signal(sig, handler)
            report.update(stream_messages=dict(gate.stream_counts), operations=dict(gate.operations),
                          controllers_seen=sorted(gate.controllers_seen), completed_cycles=len(report['cycles']))
            # A cycle is appended only after branch, both replays and playback succeed.
            report['completed_controllers'] = sorted({cycle['controller'] for cycle in report['cycles']})
            try:
                report['recorded'] = recorded_metrics(output)
                report['http_receipt_seconds'] = summary([row['http_receipt_seconds'] for row in gate.commands])
                report['observed_application_seconds'] = summary([row['observed_application_seconds'] for row in gate.commands])
                report['active_run_real_time_factor'] = {controller: summary([
                    cycle['active_run']['real_time_factor'] for cycle in report['cycles'] if cycle['controller'] == controller])
                    for controller in args.controllers}
                resources = list(gate.resources)
                report['resources'] = {key: summary([row[key] for row in resources]) for key in
                    ('total_rss_bytes', 'total_fds', 'total_threads', 'root_bytes', 'free_disk_bytes', 'owner_count')}
                report['resource_summary_scope'] = 'last 1024 periodic samples; resources.jsonl contains all bounded-duration samples'
                growth = server_growth(output / 'resources.jsonl', args.duration)
                report['server_growth'] = growth
                changes = growth.get('p95_changes', {})
                growth_gate = (growth['status'] == 'measured' and changes['rss_bytes'] <= args.max_server_growth_mib * 1024**2
                    and changes['fds'] <= args.max_server_fd_growth and changes['threads'] <= args.max_server_thread_growth)
                required = {'run', 'pause', 'step', 'reset', 'set_eyes', 'preview', 'intervene', 'snapshot', 'branch', 'replay_actions', 'replay_policy', 'playback'}
                functional = (required <= gate.operations.keys()
                    and set(args.controllers) <= set(report['completed_controllers'])
                    and gate.stream_counts['sample'] > 0)
                measured = report['measured_seconds'] >= args.duration - .5
                receipt_gate = report['http_receipt_seconds'].get('p95', float('inf')) < .150
                report['gates'] = {'duration_completed': measured, 'mixed_operations_completed': functional,
                    'http_receipt_p95_below_150ms': receipt_gate, 'one_owner': all(row['owner_count'] <= 1 for row in resources),
                    'resource_budgets': gate.failure is None and root_bytes(output) <= args.max_bytes,
                    'late_server_growth_within_budget': growth_gate if args.duration >= 3600 else None,
                    'clean_shutdown': not report['cleanup']['owned_survivors_requiring_kill']}
                report['runtime_source_at_end'] = source_identity(root)
                report['gates']['runtime_source_unchanged'] = report['runtime_source_at_end'] == report['runtime_source']
                if report['status'] != 'failed':
                    report['status'] = 'passed' if all(value for value in report['gates'].values() if value is not None) else 'failed'
            except Exception as error:
                report['status'] = 'failed'
                field = 'reporting_error' if 'error' in report else 'error'
                report[field] = {'type': type(error).__name__, 'message': str(error)}
            write_json(output / 'report.json', report)
    print(json.dumps({'status': report['status'], 'qualification': report['qualification'], 'output': str(output),
                      'error': report.get('error'), 'gates': report.get('gates')}, allow_nan=False, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
