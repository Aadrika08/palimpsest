"""Sequential, fresh-output campaign coordinator; --plan-only never runs a unit.

Driver storage guards cover cooperative output. Polling native output is monitoring,
not a strict filesystem quota. Results remain under output/analysis for review.
"""
import argparse
import csv
import errno
import ctypes
import hashlib
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from paper.studies.authority_replay_v1.common import (
    append_row, campaign_identity, declared_units, load_protocol, parse_json,
    read_rows, require, sha256_file)
from paper.studies.authority_replay_v1.analyze import load_complete_rows, summarize

REPO = Path(__file__).resolve().parents[3]
STUDY = REPO / 'paper/studies/authority_replay_v1'
GiB = 1024**3
MiB = 1024**2


@dataclass(frozen=True)
class Phase:
    name: str
    kind: str
    output: Path
    command: list[str]


def plan(protocol, assets, output, deadline):
    protocol, assets, output = map(lambda p: Path(p).absolute(), (protocol, assets, output))
    phases = []
    for name, kind, driver, extra in (
        ('fault_matrix', 'fault', 'fault_matrix.py', []),
        ('continuation', 'continuation', 'repeatability.py', ['--kind', 'continuation']),
        ('replay', 'replay', 'repeatability.py', ['--kind', 'replay']),
        ('execution_overhead', 'execution_overhead', 'overhead.py', ['--kind', 'execution']),
        ('operation_cost', 'operation_cost', 'overhead.py', ['--kind', 'operations', '--replay-root', str(output / 'replay')]),
    ):
        command = [sys.executable, str(STUDY / driver), '--protocol', str(protocol), '--assets', str(assets),
                   '--output', str(output / name), '--campaign-root', str(output),
                   '--campaign-deadline-epoch', str(float(deadline)), *extra]
        phases.append(Phase(name, kind, output / name, command))
    phases.append(Phase('offline_reproduction', 'offline_reproduction', output / 'offline_reproduction',
                        [sys.executable, str(REPO / 'scripts/verify_offline.py'), '--repo', str(REPO),
                         '--assets', str(assets), '--output', str(output / 'offline_reproduction'),
                         '--setup', '--full-flynn', '--duration', '55']))
    return phases


def write_json(path, value):
    path.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n')


def files(root):
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
        for name in sorted(names):
            path = Path(directory) / name
            if not path.is_symlink():
                yield path


def tree_size(root):
    total = 0
    for directory, _, names in os.walk(root, followlinks=False):
        for name in names:
            try:
                entry = (Path(directory) / name).lstat()
            except FileNotFoundError:
                continue  # An atomic publication renamed this temporary file.
            if stat.S_ISREG(entry.st_mode):
                total += entry.st_size
    return total


def boundary(row):
    if row.get('status') in ('timeout', 'refused', 'incomplete'):
        return f"unit {row['unit_id']}: {row.get('reason', row['status'])}"
    if (row.get('resource_boundary') or row.get('verifier_report', {}).get('resource_boundary')
            or row.get('process', {}).get('stop_reason') or row.get('error', {}).get('resource_limit')):
        return f"unit resource boundary: {row['unit_id']}"
    error = row.get('error', {})
    if error.get('type') in ('SourceMutation', 'IdentityDrift', 'OutputCap', 'CampaignOutputCap'):
        return f"unit identity/resource boundary: {row['unit_id']}"
    return None


def phase_stop_reason(phase, process, emitted, expected, identity):
    """Continue only after complete accounting and successful guardian cleanup.

    An ordinary scientific failure may give the driver a positive exit code.
    That is distinct from a monitor/cleanup failure, signal death, a resource
    boundary, or an unexplained unsuccessful exit with only successful rows.
    """
    ids = [row['unit_id'] for row in emitted]
    if len(ids) != len(set(ids)):
        return f'{phase.name}: duplicate emitted unit descriptors'
    if set(ids) != {unit['unit_id'] for unit in expected}:
        return f'{phase.name}: phase failed before all declared rows were emitted'
    descriptors = {unit['unit_id']: unit for unit in expected}
    for row in emitted:
        unit = descriptors[row['unit_id']]
        if row.get('identity') != identity or any(
                row.get(key) != value or type(row.get(key)) is not type(value)
                for key, value in unit.items()):
            return f'{phase.name}: emitted identity or unit descriptor drift'
        if row.get('status') not in ('completed', 'failed', 'refused', 'timeout', 'incomplete'):
            return f'{phase.name}: invalid emitted status'
        reason = boundary(row)
        if reason:
            return reason
    if process.get('status') != 'exited' or process.get('cleanup_error') or process.get('cleanup_errors'):
        return process.get('reason', f'{phase.name}: phase monitoring or cleanup failure')
    code = process.get('returncode')
    if type(code) is not int or code < 0:
        return f'{phase.name}: phase crashed or returned no exit status'
    if code != 0 and not any(row['status'] == 'failed' for row in emitted):
        return f'{phase.name}: nonzero exit without an accounted scientific failure'
    return None


def campaign_deadline(started, duration, requested=None):
    if requested is None:
        return started + duration
    require(math.isfinite(requested), 'campaign deadline must be finite')
    require(requested > started, 'campaign deadline already expired')
    return min(started + duration, requested)


class Guard:
    def __init__(self, root, protocol, assets, identity, deadline):
        self.root, self.protocol, self.assets = root, protocol, assets
        self.identity, self.deadline = identity, deadline
        self.resources = load_protocol(protocol).resources

    def check_identity(self):
        require(campaign_identity(REPO, self.protocol, self.assets) == self.identity, 'campaign identity drift')

    def check(self):
        require(time.time() < self.deadline, 'campaign deadline reached')
        require(tree_size(self.root) <= self.resources['campaign_max_output_bytes'], 'campaign output cap crossed')
        require(shutil.disk_usage(self.root).free >= self.resources['minimum_free_bytes'], 'filesystem free reserve crossed')
        # Unit directories are assigned by existing driver CLIs. Shared runtime-base
        # belongs to the aggregate budget, never to a single ordinary unit.
        for phase in plan(self.protocol, self.assets, self.root, self.deadline):
            if not phase.output.exists():
                continue
            if phase.kind == 'offline_reproduction':
                require(tree_size(phase.output) <= self.resources['offline_unit_max_output_bytes'], 'offline unit output cap crossed')
                continue
            for path in phase.output.iterdir():
                if path.is_dir() and not path.is_symlink() and not (phase.kind == 'fault' and path.name == 'runtime-base'):
                    require(tree_size(path) <= self.resources['ordinary_unit_max_output_bytes'], f'ordinary unit output cap crossed: {path.name}')
            rows = phase.output / 'rows.jsonl'
            if rows.exists():
                # Read only complete appends while the writer is running. Final
                # analysis reads the entire file strictly, including torn tails.
                content = rows.read_text()
                complete = content[:content.rfind('\n') + 1]
                for line in complete.splitlines():
                    row = parse_json(line)
                    require(row.get('identity') == self.identity, 'emitted row identity drift')
                    reason = boundary(row)
                    require(reason is None, reason or '')


def _processes():
    result = {}
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                fields = (entry / 'stat').read_text().rsplit(') ', 1)[1].split()
                result[int(entry.name)] = (int(fields[1]), int(fields[19]), fields[0])
            except (OSError, ValueError, IndexError):
                continue
    return result


def _remember(child, known, guardian_pid=None):
    current = _processes()
    # This adoption proof is available only inside the private guardian, a new
    # process which enables subreaping and launches exactly one phase child.
    # Kernel adoption there implies descent from that phase. The coordinator
    # never uses new/direct-child status as ownership evidence.
    if guardian_pid is not None:
        require(guardian_pid == os.getpid(), 'guardian provenance is local only')
        for pid, values in current.items():
            if values[0] == guardian_pid and pid != child.pid and pid not in known:
                known[pid] = {'start_ticks': values[1], 'provenance': 'private_guardian_adoption',
                              'parent_pid': guardian_pid}
    while True:
        found = {}
        for pid, values in current.items():
            parent = values[0]
            if pid in known or parent not in known or parent not in current:
                continue
            if current[parent][1] == known[parent]['start_ticks']:
                found[pid] = {'start_ticks': values[1], 'provenance': 'observed_phase_ancestry',
                              'parent_pid': parent, 'parent_start_ticks': current[parent][1]}
        if not found:
            break
        known.update(found)


def _open_pidfd(pid):
    libc = ctypes.CDLL(None, use_errno=True)
    descriptor = libc.pidfd_open(pid, 0)
    if descriptor < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return descriptor


def _send_pidfd(descriptor, number):
    # This prepared CPython omits both optional pidfd wrappers. glibc
    # supplies the same pinned-kernel-process operation.
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.pidfd_send_signal(descriptor, number, None, 0) != 0:
        error = ctypes.get_errno()
        if error != errno.ESRCH:
            raise OSError(error, os.strerror(error))


def _signal_owned(pid, start_ticks, number):
    """Pin the kernel process before checking its retained start identity."""
    try:
        descriptor = _open_pidfd(pid)
    except ProcessLookupError:
        return
    try:
        current = _processes().get(pid)
        if current is not None and current[1] == start_ticks:
            try:
                _send_pidfd(descriptor, number)
            except ProcessLookupError:
                pass
    finally:
        os.close(descriptor)


def _cleanup(child, known, guardian_pid=None):
    # No killpg: every signal uses a pinned, start-verified owned PID, including
    # the leader. Reaping the leader therefore cannot authorize a reused PGID.
    if not isinstance(guardian_pid, int):
        guardian_pid = None
    end = time.monotonic() + 2
    while True:
        _remember(child, known, guardian_pid)
        for pid, evidence in list(known.items()):
            _signal_owned(pid, evidence['start_ticks'], signal.SIGKILL)
        if child.pid in known:
            child.wait()
        current = _processes()
        pending = []
        for pid, evidence in list(known.items()):
            if pid == child.pid:
                continue
            if pid in current and current[pid][1] == evidence['start_ticks']:
                try:
                    os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    pass
                fresh = _processes().get(pid)
                if fresh is not None and fresh[1] == evidence['start_ticks']:
                    pending.append(pid)
        # Killing the leader may have just adopted formerly detached children.
        _remember(child, known, guardian_pid)
        current = _processes()
        pending = [pid for pid, item in known.items() if pid != child.pid
                   and pid in current and current[pid][1] == item['start_ticks']]
        if not pending:
            break
        require(time.monotonic() < end, f'owned descendants not reaped: {sorted(pending)}')
        time.sleep(.01)


def _supervise(command_path, result_path, coordinator_pid, admission_fd):
    """Private ownership guardian; never launches any non-phase subprocess."""
    libc = ctypes.CDLL(None, use_errno=True)
    result, child, known = {'status': 'failed', 'guardian_pid': os.getpid()}, None, {}
    stop_signals = []
    def interrupted(number, frame):
        stop_signals.append(number)  # Never lose Popen's child handle mid-launch.
    try:
        for number in (signal.SIGTERM, signal.SIGINT):
            signal.signal(number, interrupted)
        require(libc.prctl(36, 1, 0, 0, 0) == 0, 'cannot enable private child subreaper')
        require(libc.prctl(1, signal.SIGTERM, 0, 0, 0) == 0, 'cannot bind guardian parent death signal')
        require(os.getppid() == coordinator_pid, 'coordinator exited before guardian admission')
        # No scientific child exists until its coordinator pins this guardian
        # and sends GO. EOF on coordinator failure/death refuses admission.
        require(os.read(admission_fd, 3) == b'GO\n', 'guardian received no GO admission')
        result['admission'] = 'received_GO'
        config = parse_json(command_path.read_text())
        require(not stop_signals, 'guardian stopped before phase launch')
        child = subprocess.Popen(config['argv'], cwd=config['cwd'], start_new_session=True)
        initial = _processes().get(child.pid)
        require(initial is not None, 'phase leader identity unavailable')
        known[child.pid] = {'start_ticks': initial[1], 'provenance': 'guardian_launched_phase',
                            'parent_pid': os.getpid()}
        result['pid'] = child.pid
        # WNOWAIT preserves the exited leader's kernel identity until cleanup;
        # poll()/wait() here would reap it before descendant discovery finishes.
        while os.waitid(os.P_PID, child.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT) is None:
            if stop_signals:
                raise InterruptedError(f'guardian signal {stop_signals[0]}')
            _remember(child, known, os.getpid())
            time.sleep(.05)
        if stop_signals:
            raise InterruptedError(f'guardian signal {stop_signals[0]}')
        result.update(status='exited')
    except Exception as exc:
        result.update(reason=str(exc), error_type=type(exc).__name__)
    finally:
        os.close(admission_fd)
        # A repeated stop signal must not interrupt ownership cleanup itself.
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        if child is not None:
            try:
                _cleanup(child, known, os.getpid())
            except Exception as exc:
                result.update(status='failed', cleanup_error=str(exc))
            result['returncode'] = child.returncode
        result['owned_descendants'] = [{'pid': pid, **evidence} for pid, evidence in sorted(known.items())]
        write_json(result_path, result)
    return 0 if result['status'] == 'exited' else 1


def run_phase(phase, *, root, deadline, guard):
    log = root / 'commands' / phase.name
    log.mkdir(parents=True, exist_ok=False)
    command_path, result_path = log / 'command.json', log / 'supervisor.json'
    write_json(command_path, {'argv': phase.command, 'cwd': str(REPO), 'deadline_unix': deadline})
    record = {'command_record': str(command_path), 'supervisor_record': str(result_path),
              'stdout': str(log / 'stdout.log'), 'stderr': str(log / 'stderr.log'),
              'status': 'failed', 'started_unix': time.time()}
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join(map(str, (REPO, REPO / 'src', REPO / 'scripts'))),
           'MUJOCO_GL': 'egl', 'MPLBACKEND': 'Agg', 'OMP_NUM_THREADS': '2', 'CUDA_VISIBLE_DEVICES': ''}
    guardian_command = [sys.executable, '-B', str(Path(__file__).resolve()), '--supervise',
                        str(command_path), str(result_path), str(os.getpid())]
    child, descriptor, previous, failure = None, None, {}, None
    admission_read, admission_write = None, None
    stop_signals = []
    def interrupted(number, frame):
        stop_signals.append(number)
    try:
        for number in (signal.SIGINT, signal.SIGTERM):
            previous[number] = signal.signal(number, interrupted)
        admission_read, admission_write = os.pipe()
        guardian_command.append(str(admission_read))
        record['guardian_command'] = guardian_command
        with (log / 'stdout.log').open('xb') as stdout, (log / 'stderr.log').open('xb') as stderr:
            child = subprocess.Popen(guardian_command, cwd=REPO, env=env, stdout=stdout, stderr=stderr,
                                     pass_fds=(admission_read,))
            record['guardian_pid'] = child.pid
            record['pid'] = child.pid
            os.close(admission_read)
            admission_read = None
            descriptor = _open_pidfd(child.pid)
            require(not stop_signals, 'coordinator stopped before GO admission')
            timeout = min(deadline, record['started_unix'] + 900) if phase.kind == 'offline_reproduction' else deadline
            require(time.time() < timeout, 'deadline prevents GO admission')
            require(os.write(admission_write, b'GO\n') == 3, 'guardian GO write incomplete')
            os.close(admission_write)
            admission_write = None
            record['admission'] = 'sent_GO_after_pin'
            while child.poll() is None:
                if stop_signals:
                    raise InterruptedError(f'coordinator signal {stop_signals[0]}')
                guard.check()
                require(time.time() < timeout, 'offline unit timeout' if phase.kind == 'offline_reproduction' else 'campaign deadline')
                time.sleep(.1)
            if stop_signals:
                raise InterruptedError(f'coordinator signal {stop_signals[0]}')
            guard.check()  # Include fast native publication between monitor polls.
            require(time.time() < timeout, 'phase deadline crossed at exit')
    except Exception as exc:
        failure = {'status': 'failed', 'reason': str(exc), 'error_type': type(exc).__name__}
    finally:
        for number in previous:
            signal.signal(number, signal.SIG_IGN)
        cleanup_errors = []
        try:
            # Closing this write end is unconditional: an unadmitted guardian
            # observes EOF and cannot launch even if it outlives this cleanup.
            for channel in (admission_read, admission_write):
                if channel is not None:
                    try:
                        os.close(channel)
                    except OSError as exc:
                        cleanup_errors.append(str(exc))
            if child is not None:
                try:
                    if child.poll() is None:
                        if descriptor is not None:
                            _send_pidfd(descriptor, signal.SIGTERM)
                        else:
                            # This Popen's sole waiter has not reaped the child;
                            # its PID cannot be reused. Popen also checks/reaps
                            # an exited child before sending a direct signal.
                            child.terminate()
                    child.wait(timeout=5)
                except Exception as exc:
                    cleanup_errors.append(str(exc))
                    # Even failed pidfd acquisition/signaling must reach reap.
                    # Only the still-unreaped, directly spawned Popen is used.
                    try:
                        if child.poll() is None:
                            child.kill()
                        child.wait(timeout=5)
                    except Exception as reap_error:
                        cleanup_errors.append(str(reap_error))
                if result_path.exists():
                    record.update(parse_json(result_path.read_text()))
                else:
                    record.update(status='failed', reason='guardian exited before its process record')
                record['guardian_returncode'] = child.returncode
        except Exception as exc:
            cleanup_errors.append(str(exc))
        finally:
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError as exc:
                    cleanup_errors.append(str(exc))
            if failure:
                record.update(failure)
            if cleanup_errors:
                record.update(status='failed', cleanup_errors=cleanup_errors)
            for number, handler in previous.items():
                signal.signal(number, handler)
            record['ended_unix'] = time.time()
            write_json(log / 'process.json', record)
    return record


def offline_row(output, identity):
    row = dict(schema_version=1, study_id='authority_replay_v1', unit_id='offline_reproduction/0',
               kind='offline_reproduction', repetition=0, identity=identity, status='failed', metrics={},
               scope='same-host clean-checkout', independent_machine_reproduction=False)
    try:
        report = parse_json((output / 'report.json').read_text())
        row['report'] = report
        require(report.get('status') == 'passed', 'offline report did not pass')
        source = report.get('runtime_source', {})
        require(source.get('commit') == identity['commit'] and source.get('files_sha256'), 'offline source identity missing or mismatched')
        expected_source = {k: v for k, v in identity['runtime_source_sha256'].items()
                           if k in ('pyproject.toml', 'uv.lock') or Path(k).parent.as_posix() == 'src/palimpsest'}
        require(source['files_sha256'] == expected_source, 'offline source hashes incomplete or differ')
        require(report.get('runtime_source_at_end') == source and report.get('runtime_source_unchanged') is True, 'offline end source identity differs')
        setup = output / 'setup.json'
        require(setup.is_file(), 'offline fresh-checkout setup missing')
        fresh = parse_json(setup.read_text())
        require(fresh.get('status') == 'passed' and fresh.get('source') == source, 'offline fresh-checkout identity differs')
        verification = parse_json((output / 'full-flynn/verification.json').read_text())
        require(verification.get('status') == 'passed' and verification.get('controller') == 'flynn'
                and verification.get('device') == 'cpu', 'full CPU FLYNN result did not pass')
        row.update(status='completed', full_flynn_report=verification)
    except (OSError, ValueError, KeyError) as exc:
        row['reason'] = str(exc)
    return row


def _finish(protocol, output, identity, phases, records, stopped):
    analysis = output / 'analysis'
    analysis.mkdir()
    raw_rows, paths, row_errors = [], [], []
    for phase in phases:
        path = phase.output / 'rows.jsonl'
        if path.exists():
            paths.append(path)
            try:
                raw_rows.extend(read_rows(path))
            except (ValueError, OSError) as exc:
                row_errors.append(str(exc))
                # Recover descriptors for accounting only. The original strict
                # read error still prevents any successful final analysis.
                content = path.read_text()
                for line in content[:content.rfind('\n') + 1].splitlines():
                    try:
                        row = parse_json(line)
                        if isinstance(row, dict) and isinstance(row.get('unit_id'), str):
                            raw_rows.append(row)
                    except ValueError:
                        continue
    recovered = output / 'recovered-rows.jsonl'
    for phase in phases:
        for unit in declared_units(protocol):
            if unit['kind'] != phase.kind or phase.kind == 'offline_reproduction':
                continue
            if phase.kind in ('continuation', 'replay'):
                snapshot = phase.output / f"seed-{unit['seed']}" / 'row.json'
            elif phase.kind == 'fault':
                snapshot = phase.output / unit['unit_id'].replace('/', '__') / 'row.json'
            else:
                snapshot = phase.output / (unit['unit_id'].replace('/', '__') + '.json')
            if not snapshot.exists():
                continue
            try:
                row = parse_json(snapshot.read_text())
                require(isinstance(row, dict) and row.get('unit_id') == unit['unit_id'],
                        f'inconsistent unit snapshot descriptor: {snapshot}')
                matches = [r for r in raw_rows if r['unit_id'] == unit['unit_id']]
                if matches:
                    # Fault CLI appends dry_run after its per-unit snapshot. It
                    # is the sole non-scientific annotation excluded here.
                    annotations = {'dry_run'}
                    scientific = lambda r: {k: v for k, v in r.items() if k not in annotations}
                    require(scientific(row) == scientific(matches[0]),
                            f'inconsistent emitted unit snapshot: {snapshot}')
                else:
                    append_row(recovered, row)
                    raw_rows.append(row)
            except (ValueError, OSError) as exc:
                row_errors.append(str(exc))
    if recovered.exists():
        paths.append(recovered)
    seen = {r['unit_id'] for r in raw_rows}
    missing = output / 'unexecuted.jsonl'
    for unit in declared_units(protocol):
        if unit['unit_id'] not in seen:
            append_row(missing, dict(schema_version=1, study_id=protocol.study_id, **unit, identity=identity,
                                    status='incomplete', metrics={}, reason=stopped or 'phase emitted no row; unit not completed'))
    if missing.exists():
        paths.append(missing)
    manifest = {'identity': identity, 'phases': records, 'rows': [str(p) for p in paths],
                'stopped_reason': stopped, 'analysis_status': 'failed',
                'limitations': ['Same-host clean-checkout; independent machine reproduction remains external.',
                                'Polling native output is monitoring, not a strict filesystem quota.',
                                'Offline cache/link setup reserves 512 MiB physical headroom, monitors the 6 GiB free floor, '
                                'and limits logical directory inventory to the protocol cap; uv/npm output has no strict prewrite quota.'],
                'analysis_paths': [str(analysis / n) for n in ('summary.json', 'rows.csv', 'failures.json', 'fault-traces.jsonl', 'raw-inventory.json', 'campaign-manifest.json')]}
    try:
        require(not row_errors, '; '.join(row_errors))
        summary = summarize(protocol, load_complete_rows(protocol, paths, identity))
        require(summary['declared_units'] == 111, 'expected exactly 111 descriptors')
        write_json(analysis / 'summary.json', summary)
        write_json(analysis / 'failures.json', summary['failures'])
        with (analysis / 'rows.csv').open('w', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['unit_id', 'kind', 'status', 'row_json'])
            for row in summary['rows']:
                writer.writerow([row['unit_id'], row['kind'], row['status'], json.dumps(row, sort_keys=True, allow_nan=False)])
        with (analysis / 'fault-traces.jsonl').open('w') as stream:
            # Allowlist compact semantic evidence; raw trace strings/paths remain raw.
            keys = ('unit_id', 'case_id', 'seed', 'variant', 'condition', 'status', 'silent_acceptance',
                    'explicit_detection', 'correct_recovery', 'benign_false_rejection', 'palimpsest_outcome', 'outcome_scope')
            for row in summary['rows']:
                if row['kind'] == 'fault':
                    stream.write(json.dumps({k: row[k] for k in keys if k in row}, sort_keys=True) + '\n')
        manifest['analysis_status'] = 'passed'
        result = int(bool(stopped) or any(row['status'] != 'completed' for row in summary['rows']))
    except (ValueError, OSError) as exc:
        manifest['analysis_error'] = str(exc)
        result = 1
    write_json(analysis / 'campaign-manifest.json', manifest)
    inventory = [{'path': str(p.relative_to(output)), 'type': 'file', 'size_bytes': p.stat().st_size, 'sha256': sha256_file(p)}
                 for p in sorted(files(output)) if not p.is_relative_to(analysis)]
    for directory, dirs, names in os.walk(output, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_relative_to(analysis))
        for name in sorted([*dirs, *names]):
            path = Path(directory) / name
            if path.is_symlink():
                target = os.readlink(path)
                inventory.append({'path': str(path.relative_to(output)), 'type': 'symlink',
                                  'target': target, 'size_bytes': path.lstat().st_size,
                                  'sha256': hashlib.sha256(os.fsencode(target)).hexdigest()})
        dirs[:] = [d for d in dirs if not (Path(directory) / d).is_symlink()]
    write_json(analysis / 'raw-inventory.json', sorted(inventory, key=lambda item: item['path']))
    return result


def run(protocol_path, assets, output, campaign_deadline_epoch=None):
    require(not Path(output).is_symlink(), 'campaign requires a fresh nonsymlink output root')
    protocol_path, assets, output = map(lambda p: Path(p).resolve(), (protocol_path, assets, output))
    require(not output.exists() and not output.is_symlink(), 'campaign requires a fresh nonexistent output root')
    protocol = load_protocol(protocol_path)
    started = time.time()
    deadline = campaign_deadline(started, protocol.resources['campaign_timeout_seconds'], campaign_deadline_epoch)
    identity = campaign_identity(REPO, protocol_path, assets)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'identity.json', identity)
    write_json(output / 'preflight.json', {
        'resources': protocol.resources, 'available_free_bytes': shutil.disk_usage(output).free,
        'offline_admission_headroom_bytes': protocol.resources['ordinary_unit_max_output_bytes'],
        'cache_link_mode': {'UV_LINK_MODE': os.environ.get('UV_LINK_MODE', 'tool default; actual mode not inferred'),
                            'npm': 'existing cache required; installer output is monitored'},
        'offline_allocation_policy': 'Logical inventory cap; physical free reserve actively monitored. '
                                     'No worst-case reservation of the whole cached environment.',
    })
    write_json(output / 'campaign-clock.json', dict(identity=identity, started_unix=started, deadline_unix=deadline,
                                                   requested_deadline_unix=campaign_deadline_epoch))
    guard = Guard(output, protocol_path, assets, identity, deadline)
    phases, records, stopped = plan(protocol_path, assets, output, deadline), [], None
    for phase in phases:
        record = {'name': phase.name, 'kind': phase.kind, 'command': phase.command, 'output': str(phase.output),
                  'rows': str(phase.output / 'rows.jsonl'),
                  'process_record': str(output / 'commands' / phase.name / 'process.json')}
        if not stopped:
            try:
                guard.check_identity()
                guard.check()
                allowance = protocol.resources['offline_unit_max_output_bytes'] if phase.kind == 'offline_reproduction' else protocol.resources['ordinary_unit_max_output_bytes']
                require(tree_size(output) + allowance <= protocol.resources['campaign_max_output_bytes'], 'campaign output admission cap')
                headroom = protocol.resources['ordinary_unit_max_output_bytes'] if phase.kind == 'offline_reproduction' else allowance
                require(shutil.disk_usage(output).free - headroom >= protocol.resources['minimum_free_bytes'], 'free reserve insufficient for unit admission')
                process = run_phase(phase, root=output, deadline=deadline, guard=guard)
                record['process'] = process
                guard.check_identity()
                if phase.kind == 'offline_reproduction':
                    phase.output.mkdir(exist_ok=True)
                    row = offline_row(phase.output, identity)
                    if process['status'] != 'exited' or process.get('returncode') != 0:
                        row.update(status='failed', reason=process.get('reason', 'offline process failed'))
                    append_row(phase.output / 'rows.jsonl', row)
                path = phase.output / 'rows.jsonl'
                emitted = read_rows(path) if path.exists() else []
                expected = [u for u in declared_units(protocol) if u['kind'] == phase.kind]
                stopped = phase_stop_reason(phase, process, emitted, expected, identity)
                guard.check()
            except Exception as exc:
                stopped = str(exc)
                record['error'] = {'type': type(exc).__name__, 'message': str(exc)}
        else:
            record['not_executed_reason'] = stopped
        records.append(record)
    return _finish(protocol, output, identity, phases, records, stopped)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) == 5 and argv[0] == '--supervise':
        return _supervise(Path(argv[1]), Path(argv[2]), int(argv[3]), int(argv[4]))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--assets', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--campaign-deadline-epoch', type=float,
                        help='Absolute inherited deadline; can shorten but never extend the protocol budget')
    args = parser.parse_args(argv)
    if args.plan_only:
        protocol = load_protocol(args.protocol)
        print('# resources ' + json.dumps(protocol.resources, sort_keys=True))
        deadline = campaign_deadline(time.time(), protocol.resources['campaign_timeout_seconds'], args.campaign_deadline_epoch)
        for phase in plan(args.protocol, args.assets, args.output, deadline):
            print(shlex.join(phase.command))
        return 0
    return run(args.protocol, args.assets, args.output, args.campaign_deadline_epoch)


if __name__ == '__main__':
    raise SystemExit(main())
