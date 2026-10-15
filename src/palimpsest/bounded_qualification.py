"""Operational output/process guards for separately frozen qualifications.

Sampled RSS and kill clocks are operational stop conditions, not a hostile-process
sandbox, deterministic resource proof, WCET, or permission to open native assets.
"""
from __future__ import annotations

from contextlib import contextmanager, suppress
import json
import math
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import threading
import time

MiB = 1024 ** 2


def _absolute(path):
    raw = os.fspath(path)
    if (type(raw) is not str or not raw.startswith('/')
            or any(part in ('.', '..') for part in raw.split('/'))):
        raise ValueError('Qualification path must be absolute without traversal')
    return Path(raw)


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


def _cap(value, label):
    if type(value) is not int or not 1 <= value <= MiB:
        raise ValueError(label + ' must be an exact positive integer at most one MiB')
    return value


@contextmanager
def publication_directory(path):
    """Hold directory names/inodes through return, allowing legitimate writes."""
    path = _absolute(path)
    opened = []
    entered = False
    def identity(value):
        return value.st_dev, value.st_ino, value.st_mode
    def recheck():
        for fd, parent, name, expected in opened:
            if (identity(os.fstat(fd)) != expected
                    or identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
                raise RuntimeError('Qualification publication directory edge changed')
    try:
        parent = None
        for name in ('/', *path.parts[1:]):
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            opened.append((fd, parent, name, identity(os.fstat(fd))))
            recheck()
            parent = fd
        entered = True
        yield parent
    finally:
        try:
            if entered:
                recheck()
        finally:
            first = None
            for fd, _, _, _ in reversed(opened):
                try:
                    os.close(fd)
                except OSError as error:
                    if first is None: first = error
            if first is not None: raise first


def write_new(path, value, max_bytes=MiB):
    path = _absolute(path)
    maximum = _cap(max_bytes, 'Control write cap')
    payload = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode('utf-8')
    if len(payload) > maximum:
        raise ValueError('Qualification control exceeds its registered cap')
    with publication_directory(path.parent) as parent:
        fd = os.open(path.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        try:
            remaining = memoryview(payload)
            while remaining:
                count = os.write(fd, remaining)
                if count < 1: raise OSError('Qualification publication made no write progress')
                remaining = remaining[count:]
            expected = _identity(os.fstat(fd))
            os.fsync(fd)
            os.fsync(parent)
            if (_identity(os.fstat(fd)) != expected
                    or _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False)) != expected
                    or os.fstat(fd).st_nlink != 1):
                raise RuntimeError('Qualification control changed during publication')
        finally:
            os.close(fd)


def read_control(path, max_bytes=MiB):
    path = _absolute(path)
    maximum = _cap(max_bytes, 'Control read cap')
    with publication_directory(path.parent) as parent:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
                raise ValueError('Qualification control is not a bounded single-link regular file')
            raw = bytearray()
            while True:
                block = os.read(fd, min(65536, maximum + 1 - len(raw)))
                if not block: break
                raw.extend(block)
                if len(raw) > maximum: raise ValueError('Qualification control exceeds its cap')
            if (len(raw) != before.st_size or _identity(before) != _identity(os.fstat(fd))
                    or _identity(before) != _identity(os.stat(path.name, dir_fd=parent, follow_symlinks=False))):
                raise RuntimeError('Qualification control changed during read')
        finally:
            os.close(fd)
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result: raise ValueError('Qualification control has duplicate keys')
            result[key] = value
        return result
    def nonfinite(value):
        raise ValueError('Qualification control has a nonfinite JSON number')
    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError('Qualification control is invalid JSON') from error


def reserve_output(output, inputs):
    output = _absolute(output)
    if type(inputs) is not dict or 'sources' not in inputs:
        raise ValueError('Qualification reservation requires a registered source root')
    repo = _absolute(inputs['sources']['root'])
    if output.parent != repo / 'runs':
        raise ValueError('Qualification output must have its exact registered repo/runs parent')
    for role, section in inputs.items():
        root = _absolute(section['root'])
        if role in ('sources', 'metadata'):
            protected = []
            for row in section.get('files', []):
                path = row['path']
                if (type(path) is not str or path.startswith('/') or '\\' in path
                        or any(part in ('', '.', '..') for part in path.split('/'))):
                    raise ValueError('Registered source path is noncanonical')
                protected.append(root / path)
        else:
            protected = [root]
        if any(output == path or output in path.parents or path in output.parents for path in protected):
            raise ValueError('Qualification output overlaps protected input storage')
    with publication_directory(repo) as held_repo:
        with suppress(FileExistsError): os.mkdir('runs', mode=0o700, dir_fd=held_repo)
        os.fsync(held_repo)
        with publication_directory(output.parent) as runs:
            os.mkdir(output.name, mode=0o700, dir_fd=runs)
            os.fsync(runs)
            with publication_directory(output) as own:
                os.mkdir('outer', mode=0o700, dir_fd=own)
                os.fsync(own)


def _group_members(group):
    result = {}
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            values = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(values[2]) == group and values[0] not in ('Z', 'X'):
                result[int(path.name)] = {'start_ticks': int(values[19]),
                                         'rss_bytes': int(values[21]) * os.sysconf('SC_PAGE_SIZE')}
        except (FileNotFoundError, ProcessLookupError):
            continue
    return result


def _output_bytes(root, *, max_files=32, max_directories=2):
    """Bound the entire attempt namespace, including both pairs of logs."""
    total = count = directories_seen = 0
    with publication_directory(root) as held:
        for directory, directories, files in os.walk(f'/proc/self/fd/{held}', followlinks=False):
            directories_seen += len(directories)
            if directories_seen > max_directories or any((Path(directory) / name).is_symlink() for name in directories):
                raise ValueError('Qualification output namespace differs')
            for name in files:
                count += 1
                value = (Path(directory) / name).lstat()
                if count > max_files or not stat.S_ISREG(value.st_mode) or value.st_nlink != 1:
                    raise ValueError('Qualification output namespace differs')
                total += value.st_size
    return total


@contextmanager
def _owned_logs(output, failures):
    from palimpsest.evaluate import bounded_logs
    with publication_directory(output) as held:
        with bounded_logs(Path(f'/proc/self/fd/{held}'), 1024**2, failures) as streams:
            yield streams


@contextmanager
def _owned_direct_logs(output):
    """Hold direct regular-file logs through synchronous sync and closure.

    Aggregate output is sampled and can overshoot between observations. A
    caller's hard_guard must cover a stalled synchronous fsync or close.
    """
    with publication_directory(output) as held:
        streams = []
        try:
            for name in ('stdout.log', 'stderr.log'):
                fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL |
                             os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=held)
                streams.append((fd, name, None))
                value = os.fstat(fd)
                identity = (value.st_dev, value.st_ino, value.st_mode)
                streams[-1] = (fd, name, identity)
                named = os.stat(name, dir_fd=held, follow_symlinks=False)
                if (not stat.S_ISREG(value.st_mode) or value.st_nlink != 1
                        or _identity(value) != _identity(named)):
                    raise ValueError('Qualification direct log identity differs')
            yield tuple(fd for fd, _, _ in streams)
        finally:
            first_error = None
            for fd, name, identity in streams:
                try:
                    os.fsync(fd)
                    value = os.fstat(fd)
                    named = os.stat(name, dir_fd=held, follow_symlinks=False)
                    if (not stat.S_ISREG(value.st_mode) or value.st_nlink != 1
                            or (value.st_dev, value.st_ino, value.st_mode) != identity
                            or _identity(value) != _identity(named)):
                        raise ValueError('Qualification direct log identity differs')
                except BaseException as error:
                    if first_error is None: first_error = error
                finally:
                    try:
                        os.close(fd)
                    except BaseException as error:
                        if first_error is None: first_error = error
            try:
                os.fsync(held)
            except BaseException as error:
                if first_error is None: first_error = error
            if first_error is not None: raise first_error


def _kill_owned_groups(state):
    # Kill the known group first, even if discovery of an in-flight launch fails.
    own_group = os.getpgrp()
    if state.get('group') and state['group'] != own_group:
        with suppress(ProcessLookupError):
            os.killpg(state['group'], signal.SIGKILL)
    # Popen can still be waiting for exec before returning its PID. Direct
    # children of this dedicated monitor are also its owned launches.
    for path in Path('/proc').iterdir():
        if not path.name.isdecimal():
            continue
        try:
            values = (path / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(values[1]) == os.getpid():
                with suppress(ProcessLookupError):
                    if int(values[2]) == own_group:
                        os.kill(int(path.name), signal.SIGKILL)
                    else:
                        os.killpg(int(values[2]), signal.SIGKILL)
        except (OSError, ValueError):
            continue


@contextmanager
def hard_guard(deadline, state):
    """Last operational kill clock, including outer monitor/publication stalls."""
    if type(deadline) not in (int, float) or not math.isfinite(deadline) or type(state) is not dict:
        raise ValueError('Hard guard requires a finite clock and owned state dictionary')
    own_group = os.getpgrp()
    if own_group != os.getpid():
        raise ValueError('Hard guard requires a dedicated outer process group')
    stop = threading.Event()
    def kill_all():
        try:
            _kill_owned_groups(state)
        finally:
            os.killpg(own_group, signal.SIGKILL)
            os._exit(124)
    def expire():
        if not stop.wait(max(0, deadline - time.monotonic())):
            kill_all()
    previous = signal.getsignal(signal.SIGTERM)
    def interrupted(signum, frame):
        raise InterruptedError('Qualification outside monitor was terminated')
    signal.signal(signal.SIGTERM, interrupted)
    guard = threading.Thread(target=expire, daemon=True)
    guard.start()
    try:
        yield
    except BaseException:
        _kill_owned_groups(state)
        raise
    finally:
        stop.set()
        signal.signal(signal.SIGTERM, previous)
        guard.join(timeout=.1)
        if time.monotonic() >= deadline:
            kill_all()


def supervised(command, output, *, cwd, normal_deadline, hard_deadline,
               rss_bytes, output_bytes, min_free_bytes, max_processes=1,
               output_root=None, guard_state=None, output_namespace_limits=(32, 2),
               log_mode='drained'):
    """Observe one owned group, bound retained logs and deny late/failing returns."""
    if type(log_mode) is not str or log_mode not in ('drained', 'direct'):
        raise ValueError('Qualification log mode is invalid')
    output = _absolute(output)
    output_root = _absolute(output_root) if output_root is not None else output
    cwd = _absolute(cwd)
    if (type(max_processes) is not int or not 1 <= max_processes <= 3
            or any(type(value) is not int or value < 1 for value in (rss_bytes, output_bytes))
            or type(min_free_bytes) is not int or min_free_bytes < 0
            or any(type(value) not in (int, float) or not math.isfinite(value)
                   for value in (normal_deadline, hard_deadline))
            or normal_deadline > hard_deadline):
        raise ValueError('Qualification process limits are invalid')
    if (type(output_namespace_limits) is not tuple or len(output_namespace_limits) != 2
            or type(output_namespace_limits[0]) is not int
            or not 1 <= output_namespace_limits[0] <= 512
            or type(output_namespace_limits[1]) is not int
            or not 1 <= output_namespace_limits[1] <= 16):
        raise ValueError('Qualification output namespace limits are invalid')
    max_files, max_directories = output_namespace_limits
    failure = []
    process = None
    peak = 0
    def failed(reason):
        if not failure: failure.append(reason)
    def observe(group=None):
        nonlocal peak
        members = _group_members(group) if group is not None else {}
        parent_rss = int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
        rss = parent_rss + sum(row['rss_bytes'] for row in members.values())
        peak = max(peak, rss)
        if len(members) > max_processes: failed('unexpected child process')
        elif rss > rss_bytes: failed('sampled RSS stop threshold')
        elif shutil.disk_usage(output_root).free < min_free_bytes: failed('free-space floor')
        elif _output_bytes(output_root, max_files=max_files, max_directories=max_directories) > output_bytes: failed('aggregate output cap')
        now = time.monotonic()
        if now >= hard_deadline: failed('hard deadline')
        elif now >= normal_deadline: failed('normal-return deadline')
        return members
    with publication_directory(output_root):
        logs = _owned_logs(output, failed) if log_mode == 'drained' else _owned_direct_logs(output)
        with logs as (stdout, stderr):
            observe()
            if not failure:
                process = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                    env=dict(os.environ), cwd=cwd, start_new_session=True)
                if guard_state is not None: guard_state['group'] = process.pid
                monitor_error = None
                try:
                    observe(process.pid)
                    while process.poll() is None and not failure:
                        observe(process.pid)
                        if not failure: time.sleep(.05)
                except BaseException as error:
                    monitor_error = error
                    failed('process monitor error')
                if failure:
                    with suppress(ProcessLookupError): os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=max(.001, hard_deadline - time.monotonic()))
                except subprocess.TimeoutExpired:
                    failed('hard deadline')
                    with suppress(ProcessLookupError): os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=1)
                members = _group_members(process.pid)
                if members:
                    failed('matching process-group survivors')
                    with suppress(ProcessLookupError): os.killpg(process.pid, signal.SIGKILL)
                if monitor_error is not None: raise monitor_error
        if process is not None:
            survivors = sorted(_group_members(process.pid))
            until = min(hard_deadline, time.monotonic() + .5)
            while survivors and time.monotonic() < until:
                with suppress(ProcessLookupError): os.killpg(process.pid, signal.SIGKILL)
                time.sleep(.01)
                survivors = sorted(_group_members(process.pid))
            if survivors: failed('matching process-group survivors after cleanup')
            elif guard_state is not None: guard_state['group'] = None
        else:
            survivors = []
        observe()
    # Include the final held-directory checks/teardown in the return clock.
    finished = time.monotonic()
    if finished >= hard_deadline: failed('hard deadline')
    elif finished >= normal_deadline: failed('normal-return deadline')
    return {'status': 'completed' if process is not None and process.returncode == 0 and not failure else 'failed',
            'returncode': process.returncode if process is not None else None,
            'failure': failure[0] if failure else None, 'matching_survivors': survivors,
            'sampled_peak_rss_bytes': peak, 'rss_sampling_seconds': .05,
            'pid': process.pid if process is not None else None,
            'finished_monotonic': finished}
