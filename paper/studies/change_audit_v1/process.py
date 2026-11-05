"""Linux trusted-job accounting. No study policy, retries, or process-group kills.

See process-accounting.md for ownership, accounting, and limit boundaries.
"""
import ctypes
import errno
import json
import math
import os
from pathlib import Path
import resource
import select
import signal
import threading
import time

_LOCK = threading.Lock()
_TICK = os.sysconf('SC_CLK_TCK')


class _MonitorInterrupted(BaseException):
    pass


def _cpu(usage):
    return usage.ru_utime + usage.ru_stime


def _stat(pid):
    values = Path(f'/proc/{pid}/stat').read_text().rsplit(') ', 1)[1].split()
    return {'ppid': int(values[1]), 'start_ticks': int(values[19]),
            'cpu_ticks': sum(int(values[i]) for i in (11, 12, 13, 14))}


def _children():
    return [int(p) for p in Path(f'/proc/self/task/{os.getpid()}/children').read_text().split()]


def _open_pidfd(pid):
    libc = ctypes.CDLL(None, use_errno=True)
    fd = libc.pidfd_open(pid, 0)
    if fd < 0:
        number = ctypes.get_errno()
        raise OSError(number, os.strerror(number))
    return fd


def _send_pidfd(fd, number):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.pidfd_send_signal(fd, number, None, 0) < 0:
        error = ctypes.get_errno()
        if error != errno.ESRCH:
            raise OSError(error, os.strerror(error))


def _pin_child(pid):
    """Only a current direct child of this exclusive supervisor may be pinned."""
    before = _stat(pid)
    if before['ppid'] != os.getpid():
        raise RuntimeError('process is not an owned direct child')
    fd = _open_pidfd(pid)
    try:
        after = _stat(pid)
        if after['start_ticks'] != before['start_ticks'] or after['ppid'] != os.getpid():
            raise RuntimeError('child identity changed while pinning')
    except BaseException:
        os.close(fd)
        raise
    return {'pid': pid, 'start_ticks': before['start_ticks'], 'fd': fd}


def _close_except(keep):
    for entry in os.listdir('/proc/self/fd'):
        fd = int(entry)
        if fd > 2 and fd not in keep:
            try:
                os.close(fd)
            except OSError as exc:
                if exc.errno != errno.EBADF:
                    raise


def _sample_cpu():
    """Racy /proc lower-resolution estimate; never used for final accounting."""
    table = {}
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            try:
                table[int(entry.name)] = _stat(int(entry.name))
            except (OSError, ValueError, IndexError):
                pass
    owned = {os.getpid()}
    while True:
        extra = {pid for pid, item in table.items() if item['ppid'] in owned} - owned
        if not extra:
            break
        owned.update(extra)
    # Child fields cover descendants already waited by each live process.
    return sum(table[pid]['cpu_ticks'] for pid in owned if pid != os.getpid()) / _TICK


def _write_output(fd, data):
    return os.write(fd, data)


def _base_result():
    return {'status': 'supervisor_error', 'returncode': None,
            'worker_cpu_seconds': None, 'supervisor_cpu_seconds': None,
            'parent_cpu_seconds': None, 'subtree_cpu_seconds': None,
            'accounting_complete': False, 'tree_drained': False,
            'resources': [], 'errors': [], 'stop_reason': None,
            'logs': {}, 'sampled_worker_cpu_seconds': 0.0}


def _supervise(command, cwd, env, out, err, wall_seconds, cpu_seconds, monitor, max_log_bytes, parent):
    result = _base_result()
    known, reads = {}, {}
    leader = None
    worker_gate = None
    cleanup_at = None
    stopped = []
    started = time.monotonic()
    accounted = 0.0
    failed_accounting = False
    discard_logs = False
    monitor_active = False

    def error(exc):
        message = f'{type(exc).__name__}: {exc}'
        if message not in result['errors']:
            result['errors'].append(message)

    def stop(status, reason=None):
        nonlocal cleanup_at
        if cleanup_at is None:
            result['status'], result['stop_reason'] = status, reason
            cleanup_at = time.monotonic() + 3
        elif result['status'] in ('completed', 'failed') and status not in ('completed', 'failed'):
            # A final buffered log tail can overflow after the leader was reaped.
            result['status'], result['stop_reason'] = status, reason

    def drain_logs():
        for fd, info in list(reads.items()):
            try:
                data = os.read(fd, 65536)
            except BlockingIOError:
                continue
            except OSError:
                os.close(fd)
                del reads[fd]
                raise
            if not data:
                os.close(fd)
                del reads[fd]
                continue
            row = result['logs'][info['name']]
            row['observed_bytes'] += len(data)
            retained = data[:max(0, max_log_bytes - row['retained_bytes'])] if not discard_logs else b''
            if retained:
                view = memoryview(retained)
                while view:
                    count = _write_output(info['output'], view)
                    if count <= 0:
                        raise OSError('output write made no progress')
                    row['retained_bytes'] += count
                    view = view[count:]
            if not discard_logs and len(retained) != len(data):
                row['clipped'] = True
                stop('log_limit', info['name'])

    try:
        if _children() or len(os.listdir('/proc/self/task')) != 1:
            raise RuntimeError('supervisor is not an exclusive single-threaded context')
        signal.signal(signal.SIGCHLD, signal.SIG_DFL)
        def interrupted(number, frame):
            stopped.append(number)
            # Only callbacks are interruptible: never throw across a fork,
            # pinning, or wait4 accounting transition.
            if monitor_active:
                raise _MonitorInterrupted()
        for number in (signal.SIGINT, signal.SIGTERM):
            signal.signal(number, interrupted)
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
            raise OSError(ctypes.get_errno(), 'cannot enable private subreaper')
        # Parent death triggers the same bounded drain, including orphan adoption.
        if libc.prctl(1, signal.SIGTERM, 0, 0, 0) != 0:  # PR_SET_PDEATHSIG
            raise OSError(ctypes.get_errno(), 'cannot bind parent death signal')
        if os.getppid() != parent:
            raise RuntimeError('parent exited during supervisor setup')
        writes = []
        for name, output in (('stdout', out), ('stderr', err)):
            read_fd, write_fd = os.pipe()
            os.set_blocking(read_fd, False)
            reads[read_fd] = {'name': name, 'output': output}
            writes.append(write_fd)
            result['logs'][name] = {'observed_bytes': 0, 'retained_bytes': 0, 'clipped': False}
        gate_read, worker_gate = os.pipe()
        leader = os.fork()
        if leader == 0:
            try:
                os.close(worker_gate)
                _close_except({gate_read, *writes})
                if os.read(gate_read, 1) != b'G':
                    os._exit(125)
                os.close(gate_read)
                os.dup2(writes[0], 1)
                os.dup2(writes[1], 2)
                for fd in writes:
                    os.close(fd)
                null = os.open('/dev/null', os.O_RDONLY)
                os.dup2(null, 0)
                if null > 2:
                    os.close(null)
                ceiling = max(1, math.ceil(cpu_seconds))
                resource.setrlimit(resource.RLIMIT_CPU, (ceiling, ceiling + 1))
                os.chdir(cwd)
                os.execvpe(command[0], command, env)
            except BaseException as exc:
                os.write(2, f'exec/setup error: {exc}\n'.encode())
                os._exit(127)
        os.close(gate_read)
        for fd in writes:
            os.close(fd)
        try:
            known[leader] = _pin_child(leader)
            os.write(worker_gate, b'G')
        finally:
            os.close(worker_gate)
            worker_gate = None
        result['status'] = 'running'
    except BaseException as exc:
        error(exc)
        failed_accounting = True
        stop('supervisor_error', str(exc))
        if worker_gate is not None:
            os.close(worker_gate)  # No GO: unpinned child exits without exec.
            worker_gate = None

    def safe_drain():
        nonlocal discard_logs, failed_accounting
        try:
            drain_logs()
        except BaseException as exc:
            error(exc)
            failed_accounting = True
            discard_logs = True
            stop('supervisor_error', str(exc))

    # Keep cleanup independent of failing probes/writes: an ENOSPC or failed
    # proc scan must never prevent signalling pinned children and waiting them.
    while leader is not None:
        safe_drain()
        try:
            children = _children()
        except BaseException as exc:
            error(exc)
            failed_accounting = True
            stop('supervisor_error', str(exc))
            children = []
        for pid in children:
            if pid not in known:
                try:
                    known[pid] = _pin_child(pid)
                except BaseException as exc:
                    error(exc)
                    failed_accounting = True
                    stop('supervisor_error', str(exc))
        if stopped:
            stop('interrupted', f'signal {stopped[0]}')
        if cleanup_at is None:
            try:
                sampled = accounted + _sample_cpu()
                result['sampled_worker_cpu_seconds'] = max(result['sampled_worker_cpu_seconds'], sampled)
                if time.monotonic() - started >= wall_seconds:
                    stop('wall_limit')
                elif sampled >= cpu_seconds:
                    stop('cpu_limit')
                elif monitor is not None:
                    try:
                        monitor_active = True
                        reason = monitor({'elapsed_seconds': time.monotonic() - started,
                                          'sampled_worker_cpu_seconds': sampled,
                                          'logs': result['logs']})
                        if reason:
                            stop('monitor_stop', str(reason))
                    except _MonitorInterrupted:
                        stop('interrupted', f'signal {stopped[0]}')
                    except BaseException as exc:
                        error(exc)
                        stop('monitor_error', str(exc))
                    finally:
                        monitor_active = False
            except BaseException as exc:
                error(exc)
                failed_accounting = True
                stop('supervisor_error', str(exc))
        if cleanup_at is not None:
            for item in known.values():
                try:
                    _send_pidfd(item['fd'], signal.SIGKILL)
                    item['kill_requested'] = True
                except BaseException as exc:
                    error(exc)
                    failed_accounting = True
                    stop('supervisor_error', str(exc))
        try:
            # Never infer drain just from leader exit. Every exit is observed
            # WNOWAIT before its exact wait4, and only ECHILD proves drain.
            while True:
                try:
                    observation = os.waitid(os.P_ALL, 0, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                except ChildProcessError:
                    result['tree_drained'] = True
                    break
                if observation is None:
                    break
                pid, status, usage = os.wait4(observation.si_pid, 0)
                cpu = _cpu(usage)
                accounted += cpu
                identity = known.get(pid, {})
                result['resources'].append({'pid': pid, 'start_ticks': identity.get('start_ticks'),
                    'kill_requested': identity.get('kill_requested', False),
                    'returncode': os.waitstatus_to_exitcode(status),
                    'user_seconds': usage.ru_utime, 'system_seconds': usage.ru_stime,
                    'cpu_seconds': cpu, 'maximum_child_rss_kib': usage.ru_maxrss})
                if pid in known:
                    os.close(known.pop(pid)['fd'])
                if pid == leader:
                    result['returncode'] = os.waitstatus_to_exitcode(status)
                    if cleanup_at is None:
                        code = result['returncode']
                        stop('completed' if code == 0 else 'cpu_limit' if code == -signal.SIGXCPU else 'failed')
        except BaseException as exc:
            error(exc)
            failed_accounting = True
            stop('supervisor_error', str(exc))
        if result['tree_drained']:
            while reads:
                safe_drain()
            break
        if cleanup_at is not None and time.monotonic() >= cleanup_at:
            error(RuntimeError('owned tree did not drain within cleanup deadline'))
            failed_accounting = True
            break
        time.sleep(.01)
    if leader is None:
        result['tree_drained'] = not _children()
    for item in known.values():
        os.close(item['fd'])
    for fd in reads:
        os.close(fd)
    result['worker_cpu_seconds_observed'] = accounted
    result['accounting_complete'] = result['tree_drained'] and not failed_accounting
    result['worker_cpu_seconds'] = accounted if result['accounting_complete'] else None
    result['elapsed_seconds'] = time.monotonic() - started
    return result


def run_accounted(command, *, cwd, env, stdout_path, stderr_path, wall_seconds,
                  cpu_seconds, monitor=None, max_log_bytes=1024 * 1024):
    """Run one trusted Linux job; callback executes in the private supervisor.

    Return JSON-safe accounting even on job failure. Unknown CPU is None, never
    zero. Admission/preflight errors raise; no command starts in those cases.
    Final `subtree_cpu_seconds` includes supervisor AND worker, and must not be
    added to worker_cpu_seconds again. Add parent_cpu_seconds for total charge.
    """
    if not command or any(not isinstance(arg, str) or '\0' in arg for arg in command):
        raise ValueError('command must be a nonempty sequence of strings')
    if isinstance(command, (str, bytes)):
        raise ValueError('command must be an argument sequence')
    if any(isinstance(value, bool) or not math.isfinite(value) or value <= 0
           for value in (wall_seconds, cpu_seconds)):
        raise ValueError('wall_seconds and cpu_seconds must be finite and positive')
    if type(max_log_bytes) is not int or max_log_bytes < 0:
        raise ValueError('max_log_bytes must be a nonnegative integer per stream')
    if not _LOCK.acquire(blocking=False):
        raise RuntimeError('concurrent accounting is forbidden')
    fds = set()
    supervisor = supervisor_fd = read_fd = gate_write = None
    supervisor_reaped = False
    parent_started = _cpu(resource.getrusage(resource.RUSAGE_SELF))
    try:
        if len(os.listdir('/proc/self/task')) != 1 or _children():
            raise RuntimeError('caller must be single-threaded with no preexisting children')
        if signal.getsignal(signal.SIGCHLD) == signal.SIG_IGN:
            raise RuntimeError('SIGCHLD must not be ignored')
        out = os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        fds.add(out)
        err = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        fds.add(err)
        read_fd, write_fd = os.pipe()
        gate_read, gate_write = os.pipe()
        fds.update((read_fd, write_fd, gate_read, gate_write))
        coordinator_pid = os.getpid()
        supervisor = os.fork()
        if supervisor == 0:
            try:
                _close_except({write_fd, gate_read, out, err})
                if os.read(gate_read, 1) != b'G':
                    result = _base_result()
                    result['errors'].append('supervisor not admitted: no pinned identity')
                    result['tree_drained'] = True
                else:
                    os.close(gate_read)
                    result = _supervise(list(command), os.fspath(cwd), dict(env), out, err,
                                        wall_seconds, cpu_seconds, monitor, max_log_bytes, coordinator_pid)
                view = memoryview(json.dumps(result, allow_nan=False).encode())
                while view:
                    view = view[os.write(write_fd, view):]
                os._exit(0)
            except BaseException:
                os._exit(125)
        for fd in (write_fd, gate_read):
            os.close(fd)
            fds.remove(fd)
        supervisor_fd = None
        admission_error = None
        try:
            supervisor_fd = _pin_child(supervisor)['fd']
            fds.add(supervisor_fd)
            os.write(gate_write, b'G')
        except BaseException as exc:
            admission_error = f'{type(exc).__name__}: {exc}'
        finally:
            os.close(gate_write)
            fds.remove(gate_write)
        chunks = []
        parent_error = None
        wall_guard = False
        # The callback has its own contract, but a sleeping callback cannot
        # suspend the parent's independent wall clock. Allow ordinary supervisor
        # polling to enforce the first deadline before this backup fires.
        parent_deadline = time.monotonic() + wall_seconds + .25
        os.set_blocking(read_fd, False)
        try:
            while True:
                if not wall_guard and time.monotonic() >= parent_deadline:
                    wall_guard = True
                    if supervisor_fd is not None:
                        _send_pidfd(supervisor_fd, signal.SIGTERM)
                try:
                    data = os.read(read_fd, 65536)
                except BlockingIOError:
                    data = None
                if data == b'':
                    break
                if data is not None:
                    chunks.append(data)
                select.select([read_fd], [], [], .02)
        except BaseException as exc:
            parent_error = f'{type(exc).__name__}: {exc}'
            # Keep pinned stop authority until after exact wait4. Closing the
            # result reader prevents a drained supervisor blocking on a result
            # larger than the native pipe capacity after transport failure.
            if supervisor_fd is not None:
                _send_pidfd(supervisor_fd, signal.SIGTERM)
            os.close(read_fd)
            fds.remove(read_fd)
        _, status, usage = os.wait4(supervisor, 0)
        supervisor_reaped = True
        try:
            result = json.loads(b''.join(chunks))
        except (ValueError, TypeError):
            result = _base_result()
            result['errors'].append('supervisor result missing or malformed')
        if admission_error:
            result['errors'].append(admission_error)
        if parent_error:
            result['errors'].append(parent_error)
            result['accounting_complete'] = False
            result['tree_drained'] = False
            result['worker_cpu_seconds'] = None
        if wall_guard:
            result['status'] = 'wall_limit'
            result['stop_reason'] = 'independent parent wall guard'
        if os.waitstatus_to_exitcode(status) != 0:
            result['accounting_complete'] = False
            result['tree_drained'] = False
            result['worker_cpu_seconds'] = None
            result['errors'].append(f'supervisor exited with {os.waitstatus_to_exitcode(status)}')
        result['parent_cpu_seconds'] = _cpu(resource.getrusage(resource.RUSAGE_SELF)) - parent_started
        # wait4 includes descendants already waited by the supervisor. Subtract
        # worker accounting exactly once, rather than double charging it.
        total = _cpu(usage)
        result['subtree_cpu_seconds_observed'] = total
        if result['accounting_complete']:
            overhead = total - result['worker_cpu_seconds']
            if overhead < -1e-6:
                result['accounting_complete'] = False
                result['errors'].append('wait4 aggregate is smaller than accounted worker CPU')
                result['worker_cpu_seconds'] = None
            else:
                result['subtree_cpu_seconds'] = total
                result['supervisor_cpu_seconds'] = max(0.0, overhead)
        return result
    finally:
        # Any other post-fork exception (including allocation failures while
        # preparing transport) must contain the launched job before propagating.
        # An unadmitted supervisor exits on gate EOF; an admitted one receives
        # cooperative SIGTERM while its pidfd remains open through wait4.
        try:
            if supervisor is not None and not supervisor_reaped:
                if gate_write in fds:
                    os.close(gate_write)
                    fds.remove(gate_write)
                try:
                    if supervisor_fd is not None:
                        _send_pidfd(supervisor_fd, signal.SIGTERM)
                finally:
                    # Even a failed signal operation must not bypass reaping.
                    try:
                        if read_fd in fds:
                            os.close(read_fd)
                            fds.remove(read_fd)
                    finally:
                        while True:
                            try:
                                os.wait4(supervisor, 0)
                                break
                            except (InterruptedError, KeyboardInterrupt):
                                continue
        finally:
            try:
                for fd in fds:
                    os.close(fd)
            finally:
                _LOCK.release()
