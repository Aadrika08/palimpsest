"""Frozen development capsule; ordinary imports, no runtime/study authority."""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
SOURCES = ('scripts/characterize_puck_runtime_imports.py',
           'src/palimpsest/bounded_qualification.py',
           'src/palimpsest/evaluate.py', 'src/palimpsest/__init__.py',
           'docs/reports/puck-v3-runtime-interop/characterization-parent.py')
LIMITS = {'normal_seconds': 60, 'hard_seconds': 70, 'rss_bytes': 1073741824,
          'output_bytes': 67108864, 'min_free_bytes': 1073741824, 'max_processes': 1}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_nlink,
            value.st_size, value.st_mtime_ns, value.st_ctime_ns)


def bounded_read(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or not 0 < before.st_size <= maximum:
            raise ValueError('Capsule input is not bounded regular data')
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            raw = handle.read(maximum + 1)
        after = os.fstat(fd)
        if len(raw) != before.st_size or len(raw) > maximum or identity(before) != identity(after):
            raise ValueError('Capsule input changed during read')
        return raw
    finally:
        os.close(fd)


def main():
    if len(sys.argv) != 3:
        raise ValueError('Expected frozen input path and its external SHA')
    raw = bounded_read(sys.argv[1], 65536)
    if sha(raw) != sys.argv[2]:
        raise ValueError('Freeze SHA mismatch')
    freeze = json.loads(raw)
    if (type(freeze) is not dict or canonical(freeze) != raw
            or set(freeze) != {'kind', 'version', 'root', 'request', 'sources',
                              'interpreter_sha256', 'limits'}
            or freeze['kind'] != 'puck-runtime-import-characterization-freeze-v1'
            or type(freeze['version']) is not int or freeze['version'] != 1
            or freeze['root'] != str(ROOT) or freeze['limits'] != LIMITS):
        raise ValueError('Freeze profile mismatch')
    if (type(freeze['sources']) is not list or len(freeze['sources']) != len(SOURCES)
            or {row['path'] for row in freeze['sources']} != set(SOURCES)):
        raise ValueError('Source closure mismatch')
    for row in freeze['sources']:
        if set(row) != {'path', 'sha256'} or sha(bounded_read(ROOT / row['path'], 1024**2)) != row['sha256']:
            raise ValueError('Source SHA mismatch')
    with open('/proc/self/exe', 'rb') as handle:
        if hashlib.file_digest(handle, 'sha256').hexdigest() != freeze['interpreter_sha256']:
            raise ValueError('Original interpreter SHA mismatch')
    output = ROOT / 'runs/puck-runtime-import-characterization-01'
    request = freeze['request']
    if (type(request) is not dict or request.get('output_root') != str(output / 'payload')
            or type(request.get('environment')) is not dict):
        raise ValueError('Request output/environment mismatch')
    sys.path.insert(0, str(ROOT / 'src'))
    from palimpsest import bounded_qualification as bounds
    # Exclusive directory is the one-attempt marker, including failed invocations.
    output.parent.mkdir(mode=0o700, exist_ok=True)
    output.mkdir(mode=0o700)
    (output / 'payload').mkdir(mode=0o700)
    (output / 'outer').mkdir(mode=0o700)
    bounds.write_new(output / 'freeze.json', freeze)
    bounds.write_new(output / 'request.json', request)
    command = [sys.executable, '-I', '-B', '-S', str(ROOT / SOURCES[0]),
               str(output / 'request.json'), sha(canonical(request))]
    bounds.write_new(output / 'invocation.json', {'command': command, 'cwd': str(ROOT),
                      'freeze_sha256': sys.argv[2], 'limits': LIMITS,
                      'environment_sha256': sha(canonical(request['environment']))})
    os.environ.clear()
    os.environ.update(request['environment'])
    if os.getpgrp() != os.getpid():
        os.setsid()
    started = time.monotonic()
    state = {}
    with bounds.hard_guard(started + 70, state):
        result = bounds.supervised(command, output / 'outer', cwd=ROOT,
            normal_deadline=started + 60, hard_deadline=started + 70,
            rss_bytes=LIMITS['rss_bytes'], output_bytes=LIMITS['output_bytes'],
            min_free_bytes=LIMITS['min_free_bytes'], max_processes=1,
            output_root=output, guard_state=state)
        result.update(seconds=time.monotonic() - started, runtime_qualified=False,
                      collection_authorized=False, qualification_claims=[])
        bounds.write_new(output / 'supervision.json', result)
    print(canonical(result).decode(), end='', flush=True)
    return 0 if result['status'] == 'completed' else 1


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error)[:2048], file=sys.stderr, flush=True)
        raise SystemExit(1)
