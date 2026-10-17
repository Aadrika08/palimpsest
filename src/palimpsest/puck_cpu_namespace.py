"""The fixed private paths shared by CPU preparation and held qualification.

This only builds a command. The parent authenticates the supplied baseline,
metadata and nine observed paths, admits tmpfs capacity, supervises the child
and owns cleanup. Building a command grants no runtime qualification.
"""
import os
from pathlib import PurePosixPath
import stat

_SCRATCH_BYTES = 64 * 1024 ** 2
# Held episode workers: A records under /output; B replays A's run read-only.
_PHASES = ('prepare', 'qualify', 'episode-source', 'episode-replay')
_SOURCE_RUN = '/puck/source-run'
_NATIVE_V6 = 'puck-cpu-characterization-native-metadata-v6'
_FIXED = ('/puck', '/output', '/scratch', '/tmp', '/proc', '/dev')
_BASE_LIBRARIES = ('ld-linux-x86-64.so.2', 'libc.so.6', 'libdl.so.2',
                   'libm.so.6', 'libpthread.so.0', 'librt.so.1', 'libutil.so.1')


def _text(value, *, empty=False):
    return (type(value) is str and (bool(value) or empty) and len(value) <= 4096
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


def _argument(value):
    # execve receives an argv list, so trusted Python -c source is data here.
    # Keep its existing byte ceiling while allowing normal Python whitespace.
    return (type(value) is str and bool(value) and len(value.encode()) <= 4096
            and not any((ord(c) < 32 and c not in '\t\n\r\f') or ord(c) == 127
                        for c in value))


def _absolute(value):
    if (not _text(value) or value == '/' or not value.startswith('/')
            or str(PurePosixPath(value)) != value or '\\' in value or ':' in value
            or any(part in ('', '.', '..') for part in value.split('/')[1:])):
        raise ValueError('Namespace path must be canonical absolute POSIX text')
    return value


def _overlap(left, right):
    return left == right or left.startswith(right + '/') or right.startswith(left + '/')


def _aliases(baseline, native, files):
    result = {}
    for rows in (baseline.get('host_path_aliases'), native.get('aliases')):
        if type(rows) is not list or len(rows) > 128:
            raise ValueError('Namespace alias rows are invalid')
        seen = set()
        for row in rows:
            if type(row) not in (list, tuple) or len(row) != 2:
                raise ValueError('Namespace alias row is invalid')
            path, target = row
            _absolute(path)
            if (path in seen or not _text(target) or target.startswith('/')
                    or '\\' in target or ':' in target
                    or any(part in ('', '.', '..') for part in target.split('/'))
                    or (path not in ('/lib', '/lib64', '/sbin', '/usr/lib64', '/usr/sbin')
                        and not (path.startswith('/usr/lib/') and path.count('/') == 3))
                    or path in files):
                raise ValueError('Namespace alias is unsafe, duplicated or shadows a native file')
            seen.add(path)
            if path in result and result[path] != target:
                raise ValueError('Conflicting namespace alias')
            destination = str(PurePosixPath(path).parent / target)
            if not destination.startswith('/usr/'):
                raise ValueError('Namespace alias target is outside native paths')
            result[path] = target
    return result


def sandbox_command(baseline, native, baseline_paths, *, phase, stage_parent,
                    source_root, control_root, output_root, command, environment,
                    site_root=None, generated_root=None,
                    scratch_bytes=_SCRATCH_BYTES, source_run_root=None, source_files=None) -> list[str]:
    """Bind one admitted host tmpfs tree into two separate private namespaces.

    Preparation sees only explicitly supplied source trees and host native
    leaves. Qualification sees the copied inputs, with only the authenticated
    original interpreter/stdlib baseline exempted from staged native bindings.
    No filesystem walk, package discovery or baseline inference is performed.
    """
    if type(baseline) is not dict or type(native) is not dict:
        raise ValueError('Namespace requires authenticated baseline and native metadata')
    prefix = _absolute(baseline.get('python_prefix'))
    if any(_overlap(prefix, path) for path in _FIXED + ('/usr', '/etc', '/lib', '/lib64')):
        raise ValueError('Namespace interpreter prefix overlaps fixed mount paths')
    expected = sorted(['/etc/ld.so.cache', prefix + '/bin/python3.11']
                      + ['/usr/lib/' + name for name in _BASE_LIBRARIES])
    if (type(baseline_paths) not in (list, tuple) or list(baseline_paths) != expected):
        raise ValueError('Namespace baseline paths must be the exact sorted original nine paths')
    if phase not in _PHASES:
        raise ValueError('Namespace phase must be prepare, qualify or an episode worker')
    if (source_run_root is None) != (phase != 'episode-replay'):
        raise ValueError('Only the episode replay worker mounts the source run')
    # Episode workers bind exactly their registered files from the prepared capsule.
    if (source_files is None) != (not phase.startswith('episode-')):
        raise ValueError('Episode workers, and only they, bind an explicit source file list')
    if source_files is not None and (type(source_files) not in (list, tuple) or not 1 <= len(source_files) <= 512
            or list(source_files) != sorted(set(source_files))
            or any(not _text(path) or path.startswith('/') or '\\' in path or ':' in path
                   or any(part in ('', '.', '..') for part in path.split('/')) for path in source_files)):
        raise ValueError('Episode source files must be sorted distinct canonical relative paths')
    if type(scratch_bytes) is not int or not 0 < scratch_bytes <= _SCRATCH_BYTES:
        raise ValueError('Namespace scratch exceeds the 64 MiB ceiling')
    if (type(command) not in (list, tuple) or not 1 <= len(command) <= 128
            or not all(_argument(arg) for arg in command)):
        raise ValueError('Namespace command must be explicit bounded text arguments')
    _absolute(command[0])
    if (type(environment) is not dict or len(environment) > 128
            or any(not _text(key) or '=' in key or not _text(value, empty=True)
                   for key, value in environment.items())):
        raise ValueError('Namespace environment must be explicit bounded text')
    if phase != 'prepare' and (site_root is not None or generated_root is not None):
        raise ValueError('Namespace source trees are available only in prepare phase')
    if phase == 'prepare' and site_root is None:
        raise ValueError('Namespace prepare phase requires the explicit site source root')
    hosts = [stage_parent, source_root, control_root, output_root]
    hosts += [path for path in (site_root, generated_root, source_run_root) if path is not None]
    checked = []
    for path in hosts:
        _absolute(path)
        if any(_overlap(path, old) for old in checked + [prefix]):
            raise ValueError('Namespace host roots overlap')
        if (path in ('/home', '/tmp', '/var') or any(_overlap(path, fixed) for fixed in
                ('/usr', '/etc', '/proc', '/dev', '/sys', '/puck', '/output', '/scratch', '/lib', '/lib64', '/bin', '/sbin'))):
            raise ValueError('Namespace cannot expose a broad host root')
        checked.append(path)
    for path in (site_root, generated_root):
        if path is not None and any(_overlap(path, fixed) for fixed in _FIXED + ('/usr', '/etc', '/lib', '/lib64')):
            raise ValueError('Namespace source host path overlaps a fixed namespace path')
    stage = os.stat(stage_parent, follow_symlinks=False)
    if (not stat.S_ISDIR(stage.st_mode) or stage.st_uid != os.getuid()
            or stat.S_IMODE(stage.st_mode) != 0o700):
        raise ValueError('Namespace stage parent must be an owned 0700 directory')
    if phase == 'prepare' and os.path.lexists(stage_parent + '/inputs'):
        raise ValueError('Namespace preparation inputs must not already exist')
    files = native.get('native_files')
    if type(files) is not list or len(files) > (256 if native.get('kind') == _NATIVE_V6 else 128):
        raise ValueError('Namespace native file rows are invalid')
    paths = set()
    for row in files:
        if type(row) is not dict:
            raise ValueError('Namespace native file row is invalid')
        path = _absolute(row.get('path'))
        if (path in paths or not path.startswith(('/usr/', '/etc/'))
                or any(_overlap(path, old) for old in paths)):
            raise ValueError('Namespace native file path is unsafe or duplicated')
        paths.add(path)
    if not (set(expected) - {prefix + '/bin/python3.11'}).issubset(paths):
        raise ValueError('Namespace native files omit an original baseline path')
    aliases = _aliases(baseline, native, paths)
    cmd = ['/usr/bin/bwrap', '--unshare-all', '--unshare-user']
    if phase == 'prepare':
        cmd += ['--as-pid-1']
    # Qualification keeps PID1 as reaper/parent. Its caller supplies the
    # setsid+exec launcher and supervises descendants across process groups.
    cmd += ['--disable-userns', '--die-with-parent', '--cap-drop', 'ALL', '--clearenv',
           '--hostname', 'palimpsest-cpu-held', '--ro-bind', prefix, prefix]
    for path in sorted(paths):
        origin = path
        if phase != 'prepare' and path not in baseline_paths:
            root, relative = ('root-0001', path[5:]) if path.startswith('/usr/') else ('root-0002', path[5:])
            origin = stage_parent + '/inputs/' + root + '/' + relative
        cmd += ['--ro-bind', origin, path]
    for path, target in sorted(aliases.items(), key=lambda item: (item[0].count('/'), item[0])):
        cmd += ['--symlink', target, path]
    if source_files is None:
        cmd += ['--ro-bind', source_root, '/puck/source']
    else:
        for path in source_files:
            cmd += ['--ro-bind', source_root + '/' + path, '/puck/source/' + path]
    cmd += ['--ro-bind', control_root, '/puck/control']
    if phase == 'prepare':
        cmd += ['--bind', stage_parent, '/puck/staged']
        for path in (site_root, generated_root):
            if path is not None:
                cmd += ['--ro-bind', path, path]
    else:
        cmd += ['--ro-bind', stage_parent + '/inputs', '/puck/staged/inputs']
    if source_run_root is not None:
        cmd += ['--ro-bind', source_run_root, _SOURCE_RUN]
    cmd += ['--bind', output_root, '/output', '--size', str(scratch_bytes), '--tmpfs', '/scratch']
    for name in ('home', 'tmp', 'pycache'):
        cmd += ['--dir', '/scratch/' + name, '--chmod', '0700', '/scratch/' + name]
    cmd += ['--symlink', 'scratch/tmp', '/tmp', '--proc', '/proc', '--remount-ro', '/proc',
            '--dev', '/dev', '--remount-ro', '/dev', '--remount-ro', '/']
    for key, value in sorted(environment.items()):
        cmd += ['--setenv', key, value]
    return cmd + ['--chdir', '/puck/source'] + list(command)
