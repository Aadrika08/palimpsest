"""Record one ordinary CPU characterization transport; grants no runtime authority."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PYTHON = '/home/utkarsh/.local/share/uv/python/cpython-3.11.15-linux-x86_64-gnu/bin/python3.11'
PARENT = 'scripts/characterize_puck_cpu_runtime.py'
WORKER = 'scripts/characterize_puck_runtime_imports.py'
OBSERVER = 'scripts/observe_puck_cpu_runtime_characterization.py'
OUTPUT = 'runs/puck-cpu-runtime-characterization-03'
SITE = 'runs/puck-cpu-install-01/site'
NORMAL_SECONDS = 210
CLEANUP_SECONDS = 5
HARD_SECONDS = 225
MAX_STREAM_BYTES = 16 * 1024**2
MAX_RECEIPT_BYTES = 64 * 1024
MAX_IDENTITIES = 64
ENVIRONMENT = dict(PATH='/usr/bin:/bin', LANG='C.UTF-8', LC_ALL='C.UTF-8',
                   PYTHONDONTWRITEBYTECODE='1')
CLAIMS = dict(runtime_qualified=False, native_authorized=False, collection_authorized=False,
              study_authorized=False, executable=False, qualification_claims=[])


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=False, allow_nan=False) + '\n').encode()


def _parts(relative):
    if (type(relative) is not str or not relative or len(relative.encode()) > 4096
            or '\0' in relative or not Path(relative).parts or Path(relative).is_absolute()
            or str(Path(relative)) != relative or '..' in Path(relative).parts):
        raise ValueError('Canonical root-relative CPU transport path required')
    return Path(relative).parts


def _open(relative, flags, mode=0o600):
    parts = _parts(relative)
    directory = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                            dir_fd=directory)
            os.close(directory)
            directory = child
        return os.open(parts[-1], flags | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC,
                       mode, dir_fd=directory)
    finally:
        os.close(directory)


def _stamp(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


def read(relative, maximum):
    fd = _open(relative, os.O_RDONLY)
    try:
        before = os.fstat(fd)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
                or not 0 <= before.st_size <= maximum):
            raise ValueError('Bounded single-link regular CPU transport data required')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(maximum + 1)
        current = _open(relative, os.O_RDONLY)
        try:
            if (len(raw) != before.st_size or _stamp(before) != _stamp(os.fstat(fd))
                    or _stamp(before) != _stamp(os.fstat(current))):
                raise ValueError('CPU transport data changed while read')
        finally:
            os.close(current)
        return raw
    finally:
        os.close(fd)


def _configuration(configuration, expected_sha256):
    supplied = str(configuration)
    configuration = Path(configuration)
    if (supplied != str(configuration) or not configuration.is_absolute() or not configuration.is_relative_to(ROOT)
            or str(configuration) != str(ROOT / configuration.relative_to(ROOT))
            or '..' in configuration.parts):
        raise ValueError('Canonical absolute CPU configuration inside its exact root required')
    relative = configuration.relative_to(ROOT).as_posix()
    raw = read(relative, 1024**2)
    if (type(expected_sha256) is not str or len(expected_sha256) != 64
            or any(c not in '0123456789abcdef' for c in expected_sha256)
            or hashlib.sha256(raw).hexdigest() != expected_sha256):
        raise ValueError('CPU configuration SHA differs')
    config = json.loads(raw)
    if (type(config) is not dict or (json.dumps(config, sort_keys=True, indent=2,
                                               allow_nan=False) + '\n').encode() != raw):
        raise ValueError('Canonical sorted indent-two CPU configuration required')
    if (set(config) != {'kind', 'version', 'output', 'site_root', 'sources', 'inputs',
                        'roles', 'limits', 'environment', 'expected_versions'}
            or config['kind'] != 'puck-cpu-runtime-characterization-v2'
            or type(config['version']) is not int or config['version'] != 2
            or config['output'] != OUTPUT or config['site_root'] != SITE):
        raise ValueError('Exact ordinary CPU characterization03 configuration required')
    sources = config['sources']
    if type(sources) is not list or not 3 <= len(sources) <= 128:
        raise ValueError('Bounded CPU source pin list required')
    names = []
    for row in sources:
        if (type(row) is not dict or set(row) != {'path', 'size_bytes', 'sha256'}
                or type(row['size_bytes']) is not int or not 0 < row['size_bytes'] <= 1024**2
                or type(row['sha256']) is not str or len(row['sha256']) != 64
                or any(c not in '0123456789abcdef' for c in row['sha256'])):
            raise ValueError('Exact CPU source pin required')
        _parts(row['path'])
        names.append(row['path'])
    if names != sorted(set(names)) or not {PARENT, WORKER, OBSERVER} <= set(names):
        raise ValueError('Unique sorted CPU parent, worker and observer source pins required')
    for row in sources:
        source = read(row['path'], 1024**2)
        if len(source) != row['size_bytes'] or hashlib.sha256(source).hexdigest() != row['sha256']:
            raise ValueError('CPU transport source bytes differ')
    return configuration, dict(path=relative, size_bytes=len(raw), sha256=expected_sha256)


def _process_record(pid):
    try:
        raw = Path('/proc/' + str(pid) + '/stat').read_bytes()
        if len(raw) > 4096:
            raise ValueError('Bounded process identity required')
        fields = raw[raw.rindex(b')') + 2:].split()
        return dict(pid=pid, start_ticks=int(fields[19]), ppid=int(fields[1]),
                    pgrp=int(fields[2]), session=int(fields[3]))
    except (FileNotFoundError, ProcessLookupError):
        return None


def process_identity(pid):
    row = _process_record(pid)
    return None if row is None else dict(pid=row['pid'], start_ticks=row['start_ticks'])


def terminate_identity(identity):
    """Refuse stale sampled PIDs; this is sampled cleanup, not atomic pidfd proof."""
    if process_identity(identity['pid']) != identity:
        return False
    try:
        os.kill(identity['pid'], signal.SIGKILL)
        return True
    except ProcessLookupError:
        return False


def _sample(parent_identity, identities):
    records = {}
    entries = list(Path('/proc').iterdir())
    if len(entries) > 65536:
        raise ValueError('CPU process sampling table limit exceeded')
    for path in entries:
        if path.name.isdecimal():
            row = _process_record(int(path.name))
            if row is not None:
                records[row['pid']] = row
    owned = {parent_identity['pid']}
    owned.update(row['pid'] for row in identities if process_identity(row['pid']) == row)
    while True:
        added = {pid for pid, row in records.items() if row['ppid'] in owned
                 or (row['pgrp'] == parent_identity['pid'] and row['session'] == parent_identity['pid'])}
        if added <= owned:
            break
        owned.update(added)
    for pid in sorted(owned):
        row = records.get(pid)
        if row is None:
            continue
        identity = dict(pid=pid, start_ticks=row['start_ticks'])
        if identity not in identities:
            if len(identities) >= MAX_IDENTITIES:
                raise ValueError('CPU sampled process identity limit exceeded')
            identities.append(identity)


def _survivors(identities):
    return [row for row in identities if process_identity(row['pid']) == row]


def _stop(process, parent_identity, identities):
    deadline = time.monotonic() + CLEANUP_SECONDS
    # Give the still-owned parent a chance to reap children before it is killed.
    children = [row for row in identities if row != parent_identity]
    for row in children:
        terminate_identity(row)
    if children and process.poll() is None:
        until = min(deadline, time.monotonic() + .1)
        while _survivors(children) and time.monotonic() < until:
            time.sleep(.01)
    if process.poll() is None:
        if parent_identity is not None and process_identity(process.pid) == parent_identity:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            # Popen still owns this unreaped child even if its stat could not be captured.
            process.kill()
    process.wait(timeout=max(.01, deadline - time.monotonic()))
    while _survivors(identities) and time.monotonic() < deadline:
        for row in _survivors(identities):
            terminate_identity(row)
        time.sleep(.01)


def observe(configuration, expected_sha256):
    started = time.monotonic()
    configuration, configuration_row = _configuration(configuration, expected_sha256)
    paths = {name: OUTPUT + '-external-cli.' + name for name in ('stdout', 'stderr')}
    receipt = OUTPUT + '-external-cli-transport.json'
    # Reject symlinked ancestors before examining or reserving any allocation path.
    directory = _open('runs', os.O_RDONLY | os.O_DIRECTORY)
    os.close(directory)
    if any(os.path.lexists(ROOT / path) for path in (OUTPUT, receipt, *paths.values())):
        raise FileExistsError('CPU external observation or allocation already reserved')
    command = [PYTHON, '-I', '-S', '-B', str(ROOT / PARENT),
               '--configuration', str(configuration), '--sha256', expected_sha256]
    result = dict(CLAIMS, kind='puck-cpu-characterization-cli-transport-v1', version=1,
                  root=str(ROOT), allocation_id=3, configuration=configuration_row,
                  command=command, environment=dict(ENVIRONMENT), observed_returncode=None,
                  elapsed_seconds=0., timed_out=False, parent_identity=None,
                  sampled_identities=[], sampled_survivors=[], sampled_cleanup_only=True,
                  sampling_limitation='Sampled PID/start identities only; not exhaustive unseen-process proof. '
                                      'PID/start recheck and signal are not atomic lifetime proof. '
                                      'Parent process-group supervision and closure require independent audit.')
    process = None
    descriptors = {}
    receipt_fd = _open(receipt, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        os.fchmod(receipt_fd, 0o600)
        try:
            for name, path in paths.items():
                descriptors[name] = _open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                os.fchmod(descriptors[name], 0o600)
            if os.path.lexists(ROOT / OUTPUT):
                raise FileExistsError('CPU allocation appeared before launch')
            if time.monotonic() >= started + NORMAL_SECONDS:
                result['timed_out'] = True
                raise TimeoutError('CPU transport deadline before launch')
            process = subprocess.Popen(command, cwd=ROOT, env=ENVIRONMENT,
                                       stdin=subprocess.DEVNULL, stdout=descriptors['stdout'],
                                       stderr=descriptors['stderr'], start_new_session=True, close_fds=True,
                                       preexec_fn=apply_limits)
            result['parent_identity'] = process_identity(process.pid)
            if result['parent_identity'] is None:
                raise RuntimeError('CPU parent process identity was not captured')
            while True:
                _sample(result['parent_identity'], result['sampled_identities'])
                if any(os.fstat(fd).st_size > MAX_STREAM_BYTES for fd in descriptors.values()):
                    raise ValueError('CPU transport raw stream limit exceeded')
                if process.poll() is not None:
                    break
                if time.monotonic() >= started + NORMAL_SECONDS:
                    result['timed_out'] = True
                    raise TimeoutError('CPU parent transport exceeded its normal deadline')
                time.sleep(min(.05, max(0., started + NORMAL_SECONDS - time.monotonic())))
            if _survivors(result['sampled_identities']):
                raise RuntimeError('Sampled CPU processes survived the parent exit')
            if process.returncode != 0:
                raise RuntimeError('CPU parent did not exit normally with code zero')
            if time.monotonic() >= started + NORMAL_SECONDS:
                result['timed_out'] = True
                raise TimeoutError('CPU parent transport finished after its normal deadline')
        except Exception as exc:
            result.update(error_type=type(exc).__name__, error=str(exc)[:1024])
        finally:
            if process is not None:
                try:
                    if process.poll() is None or _survivors(result['sampled_identities']):
                        _stop(process, result['parent_identity'], result['sampled_identities'])
                    result['observed_returncode'] = process.returncode
                except Exception as exc:
                    result.update(error_type=type(exc).__name__, error=str(exc)[:1024])
                result['sampled_survivors'] = _survivors(result['sampled_identities'])
            for fd in descriptors.values():
                os.fsync(fd)
                os.close(fd)
            descriptors.clear()
        for name, path in paths.items():
            raw = read(path, MAX_STREAM_BYTES)
            result[name] = dict(path=path, size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        result['elapsed_seconds'] = time.monotonic() - started
        if not math.isfinite(result['elapsed_seconds']):
            raise ValueError('Finite CPU transport duration required')
        raw = canonical(result)
        if len(raw) > MAX_RECEIPT_BYTES:
            raise ValueError('CPU transport receipt limit exceeded')
        with os.fdopen(os.dup(receipt_fd), 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        return result
    finally:
        for fd in descriptors.values():
            os.close(fd)
        os.close(receipt_fd)


def apply_limits():
    for name, value in (('NOFILE', 40000), ('AS', 8 * 1024**3), ('FSIZE', MAX_STREAM_BYTES)):
        resource.setrlimit(getattr(resource, 'RLIMIT_' + name), (value, value))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--configuration', required=True)
    parser.add_argument('--sha256', required=True)
    args = parser.parse_args()
    if (Path(sys.executable).resolve() != Path(PYTHON)
            or not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode)
            or os.environ.get('LD_PRELOAD') or os.environ.get('LD_LIBRARY_PATH')):
        raise ValueError('Original isolated CPU interpreter and loader environment required')

    def alarm(signum, frame):
        raise TimeoutError('CPU transport outer deadline')

    signal.signal(signal.SIGALRM, alarm)
    signal.setitimer(signal.ITIMER_REAL, HARD_SECONDS)
    try:
        apply_limits()
        result = observe(args.configuration, args.sha256)
        print(canonical(result).decode(), end='', flush=True)
        return 0 if (result['observed_returncode'] == 0 and not result['timed_out']
                     and result['parent_identity'] is not None and not result['sampled_survivors']
                     and 'error' not in result and result['elapsed_seconds'] < NORMAL_SECONDS) else 1
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)


if __name__ == '__main__':
    raise SystemExit(main())
