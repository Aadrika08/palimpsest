#!/usr/bin/env python3
"""One unguarded held-episode phase observation (characterization-04); never qualification.

Runs ``palimpsest.puck_held_episode.run`` with a stand-in admission over ordinary
imports from one explicit site. Like the v4 bootstrap, an audit hook records and
refuses every process creation for the whole run. The report records the module
cache and mapped images that profile derivation and native metadata need. The
outer parent supplies the namespace and time/RSS/output limits.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import types

REPORT_KIND = 'puck-episode-characterization-result-v1'
REQUEST_KIND = 'puck-episode-characterization-request-v1'
REPORT_NAME = 'characterization.json'
REQUEST_BYTES = 1024 ** 2
REPORT_BYTES = 4 * 1024 ** 2
MISSES = 4096
PROCESS_EVENTS = frozenset({'subprocess.Popen', 'os.posix_spawn', 'os.fork', 'os.forkpty', 'os.system',
                            'pty.spawn', 'os.spawn'})
REQUEST_KEYS = {'kind', 'version', 'site_root', 'source_root', 'output_root', 'pycache_prefix', 'environment',
                'expected_versions', 'runtime', 'source_files', 'distributions', 'episode'}
CLAIMS = dict(runtime_qualified=False, native_authorized=False, collection_authorized=False,
              study_authorized=False, executable=False, qualification_claims=[])
attempts = dict(count=0, events=[])


def refuse_process_creation(event, args):
    if event in PROCESS_EVENTS or event.startswith('os.exec'):
        attempts['count'] += 1
        if len(attempts['events']) < 64:
            attempts['events'].append(str(event)[:128])
        raise RuntimeError('Characterized held episode refuses process creation: ' + event)


def helpers():
    """Cache/maps helpers loaded by path, never published into sys.modules."""
    path = Path(__file__).resolve().parent / 'characterize_puck_runtime_imports.py'
    spec = importlib.util.spec_from_file_location('_episode_characterization_helpers', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_bounded(path, maximum):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        state = os.fstat(fd)
        if not 0 < state.st_size <= maximum:
            raise ValueError('Bounded worker input required')
        with os.fdopen(os.dup(fd), 'rb') as stream:
            raw = stream.read(maximum + 1)
        if len(raw) != state.st_size:
            raise ValueError('Worker input changed while read')
        return raw
    finally:
        os.close(fd)


def request_at(path, expected):
    raw = read_bounded(path, REQUEST_BYTES)
    if sha(raw) != expected:
        raise ValueError('Request SHA differs from its external pin')
    value = json.loads(raw)
    if (type(value) is not dict or set(value) != REQUEST_KEYS or value['kind'] != REQUEST_KIND
            or type(value['version']) is not int or value['version'] != 1 or canonical(value) != raw):
        raise ValueError('Exact canonical episode characterization request required')
    episode = value['episode']
    if type(episode) is not dict or episode.get('phase') not in ('source', 'replay'):
        raise ValueError('Episode characterization phase must be source or replay')
    if dict(os.environ) != value['environment']:
        raise ValueError('Exact environment mismatch')
    if not (sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode):
        raise ValueError('Worker must use -I -B -S')
    prefix = Path(value['pycache_prefix'])
    state = prefix.lstat()
    if (sys.pycache_prefix != str(prefix) or not prefix.is_dir() or prefix.is_symlink()
            or state.st_uid != os.geteuid() or state.st_mode & 0o077 or any(prefix.iterdir())):
        raise ValueError('Private empty pycache prefix required')
    output = Path(value['output_root'])
    if os.path.lexists(output / REPORT_NAME):
        raise ValueError('Output already contains a report')
    return value


class _Source:
    def __init__(self, root, rows):
        self._root = Path(root)
        self._pins = {row['path']: row for row in rows}

    def read(self, path, limit):
        pin = self._pins.get(path)
        if pin is None:
            raise ValueError('Episode source read is not registered: ' + str(path))
        raw = read_bounded(self._root / path, limit)
        if len(raw) != pin['size_bytes'] or sha(raw) != pin['sha256']:
            raise ValueError('Episode source bytes differ from their pin: ' + path)
        return raw


class _Dependencies:
    def __init__(self, distributions):
        self.distributions = distributions


class _Admission:
    """Stand-in for the held admission: same registration fields, no guard."""

    def __init__(self, request):
        self._reg = dict(source_root=request['source_root'], source_files=request['source_files'],
                         runtime=request['runtime'], environment=dict(request['environment']),
                         episode=request['episode'])
        self._source = _Source(request['source_root'], request['source_files'])
        self._dependencies = _Dependencies(request['distributions'])
        self.rechecks = 0

    def recheck(self):
        self.rechecks += 1


class _DispatchWatch:
    """Attribute shared native-cache dispatch keys exactly where the held guard checks them.

    A head finder enables a profile hook only while an import runs. It keeps the
    stack of open held phases (site extension create/exec, site Python module
    bodies) and snapshots the dispatch keys (module, class or function values) of
    every virtual cache module at the held guard's check points: each site
    extension's create/exec start and every phase close. Each new key goes to the
    innermost open phase, and ``closed`` records whether its cache's creator phase
    had already closed, so later keys are distinguishable from creator keys.
    """
    DELEGATES = (types.ModuleType, type, types.FunctionType, types.BuiltinFunctionType)

    def __init__(self, site_root):
        import _imp
        self.site = site_root.rstrip('/') + '/'; self.create = _imp.create_dynamic; self.execute = _imp.exec_dynamic
        self.depth = 0; self.active = False; self.state = {}; self.events = []; self.errors = []; self.code = None
        self.stack = []; self.creators = {}; self.closed = set()

    def find_spec(self, fullname, path=None, target=None):
        if not self.active:
            frame = sys._getframe(1)
            while frame is not None and frame.f_code.co_name != '_find_and_load':
                frame = frame.f_back
            if frame is not None:
                self.code = frame.f_code; self.depth = 1; self.active = True; sys.setprofile(self.profile)
        return None

    def invalidate_caches(self):
        pass

    def caches(self):
        result = {}
        for name, value in list(sys.modules.items()):
            if type(value) is not types.ModuleType or '.' in name or name in ('__main__', '__mp_main__'):
                continue
            raw = types.ModuleType.__dict__['__dict__'].__get__(value)
            if raw.get('__spec__') is None and raw.get('__file__') is None:
                result[name] = {key: item for key, item in raw.items() if isinstance(item, self.DELEGATES)}
        return result

    def check(self):
        producer, phase = self.stack[-1] if self.stack else (None, None)
        current = self.caches()
        for cache, keys in current.items():
            before = self.state.get(cache)
            if before is None:
                self.creators[cache] = (producer, phase)
                self.events.append(dict(cache=cache, producer=producer, phase=phase, added=sorted(keys), first=True, closed=False))
                continue
            if any(key not in keys or keys[key] is not value for key, value in before.items()):
                self.errors.append(dict(cache=cache, producer=producer, phase=phase, error='dispatch changed or removed'))
            added = sorted(set(keys) - set(before))
            if added:
                self.events.append(dict(cache=cache, producer=producer, phase=phase, added=added, first=False,
                                        closed=cache in self.closed))
        self.state = current

    def close(self, key):
        self.check()
        if not self.stack or self.stack[-1] != key:
            raise RuntimeError('Observed held phase stack differs')
        self.closed.update(cache for cache, creator in self.creators.items() if creator == key)
        self.stack.pop()

    def profile(self, frame, event, arg):
        try:
            if event == 'call' and frame.f_code is self.code:
                self.depth += 1
            elif event == 'return' and frame.f_code is self.code:
                self.depth -= 1
                if self.depth <= 0:
                    self.active = False; sys.setprofile(None)
            elif event in ('call', 'return') and frame.f_code.co_name == '<module>':
                path = frame.f_globals.get('__file__')
                # Only a site file's own module body (not exec'd strings in its globals) is a held phase.
                if type(path) is str and path.startswith(self.site) and frame.f_code.co_filename == path:
                    key = (frame.f_globals.get('__name__'), 'module_exec')
                    if event == 'call': self.stack.append(key)
                    else: self.close(key)
            elif event in ('c_call', 'c_return', 'c_exception') and (arg is self.create or arg is self.execute):
                target = frame.f_locals.get('args', (None,))[0]
                if arg is self.create:
                    name, origin, phase = getattr(target, 'name', None), getattr(target, 'origin', None), 'native_create'
                else:
                    raw = types.ModuleType.__dict__['__dict__'].__get__(target)
                    name, origin, phase = raw.get('__name__'), raw.get('__file__'), 'module_exec'
                if type(origin) is str and origin.startswith(self.site):
                    if event == 'c_call': self.check(); self.stack.append((name, phase))
                    else: self.close((name, phase))
        except BaseException as error:
            if len(self.errors) < 64:
                self.errors.append(dict(error=type(error).__name__ + ': ' + str(error)[:512]))

    def report(self):
        final = self.caches(); unattributed = []
        for cache, keys in final.items():
            before = self.state.get(cache, {})
            if set(keys) != set(before) or any(keys[k] is not before[k] for k in before if k in keys):
                unattributed.append(dict(cache=cache, keys=sorted(set(keys) ^ set(before))))
        return dict(events=self.events[:4096], unattributed=unattributed, errors=self.errors)


class _Misses:
    """Passive tail finder: records names no finder resolved."""

    def __init__(self):
        self.names = set()

    def find_spec(self, fullname, path=None, target=None):
        if len(self.names) < MISSES:
            self.names.add(str(fullname)[:512])
        return None

    def invalidate_caches(self):
        pass


def observe(request, request_sha, h):
    report = dict(kind=REPORT_KIND, version=1, status='failed', phase=request['episode']['phase'],
                  request_sha256=request_sha, source_sha256=sha(read_bounded(__file__, REPORT_BYTES)),
                  environment_sha256=sha(canonical(request['environment'])), python_version=sys.version,
                  executable_path=sys.executable, pid=os.getpid(), ppid=os.getppid(),
                  expected_versions=dict(request['expected_versions']), versions={}, episode_result=None,
                  process_creation_attempts=attempts, import_misses=[], rechecks=0, cache=None, maps=None,
                  baseline_maps=None, environment_unchanged=None, pycache_unchanged=None,
                  native_cache_dispatch=None, observation_errors=[], **CLAIMS)
    started = time.monotonic(); error = None; admission = None; misses = _Misses()
    dispatch = _DispatchWatch(request['site_root'])
    try:
        report['baseline_maps'] = h.mapped_images()
        sys.path.extend([request['site_root'], str(Path(request['source_root']) / 'src')])
        sys.meta_path.append(misses); sys.meta_path.insert(0, dispatch)
        admission = _Admission(request)
        from palimpsest import puck_held_episode
        report['episode_result'] = puck_held_episode.run(admission)
        for name, expected in sorted(request['expected_versions'].items()):
            module = sys.modules.get(name)
            value = h.text_value(h.module_dict(module).get('__version__'), 128) if module is not None else None
            if value != expected:
                raise ValueError('Episode package version differs: ' + name)
            report['versions'][name] = value
    except BaseException as failure:
        error = h.failure_detail(failure)
        try:
            report['error_chain'] = h.cpu_error_chain(failure)
        except BaseException as diagnostic:
            report['error_chain'] = dict(entries=[], complete=False, truncation='diagnostic_error',
                                         error_type=h.class_name(diagnostic))
    sys.setprofile(None)
    for finder in (misses, dispatch):
        if finder in sys.meta_path:
            sys.meta_path.remove(finder)
    report['native_cache_dispatch'] = dispatch.report()
    report['import_misses'] = sorted(misses.names)
    report['rechecks'] = admission.rechecks if admission is not None else 0
    for stage, snapshot in (('cache', lambda: h.describe_cache(sys.modules)), ('maps', h.mapped_images)):
        try:
            report[stage] = snapshot()
        except BaseException as failure:
            report['observation_errors'].append(dict(h.failure_detail(failure), stage=stage))
    report['environment_unchanged'] = dict(os.environ) == request['environment']
    report['pycache_unchanged'] = sys.pycache_prefix == request['pycache_prefix']
    report['process_creation_attempts'] = dict(count=attempts['count'], events=list(attempts['events']))
    if error is None and attempts['count']:
        error = dict(type='RuntimeError', message='Characterized episode attempted process creation')
    if error is None and not report['environment_unchanged']:
        error = dict(type='ValueError', message='Exact environment changed during observation')
    if error is None and not report['pycache_unchanged']:
        error = dict(type='ValueError', message='Pycache prefix changed during observation')
    report['seconds'] = time.monotonic() - started
    if error is not None:
        report['error'] = error
    elif report['observation_errors']:
        report['error'] = dict(report['observation_errors'][0])
    else:
        report['status'] = 'observed'
    if len(canonical(report)) > REPORT_BYTES:
        report.update(status='failed', cache=None, maps=None, baseline_maps=None)
        report.setdefault('error', dict(type='report_limit', message='Full observation exceeded four MiB'))
    return report


def publish(output, report):
    raw = canonical(report)
    root = os.open(output, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        fd = os.open(REPORT_NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=root)
        try:
            view = memoryview(raw)
            while view:
                view = view[os.write(fd, view):]
            os.fsync(fd)
            os.fsync(root)
        finally:
            os.close(fd)
    finally:
        os.close(root)
    return dict(report_sha256=sha(raw), report_bytes=len(raw), status=report['status'])


def main(argv):
    # Installed before any request or package code runs; active until exit.
    sys.addaudithook(refuse_process_creation)
    try:
        if len(argv) != 2:
            raise ValueError('Expected request path and external SHA')
        h = helpers()
        request = request_at(argv[0], argv[1])
        report = observe(request, argv[1], h)
        receipt = publish(request['output_root'], report)
        print(canonical(receipt).decode(), end='', flush=True)
        return 0 if report['status'] == 'observed' else 1
    except Exception as error:
        print(type(error).__name__ + ': ' + str(error)[:2048], file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
