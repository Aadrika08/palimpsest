"""Bounded dependency registration staging from an authenticated observation.

This hashes bytes and checks namespace stability only during construction. It
provides no lifetime custody, import authority, execution, or qualification;
the consuming child must independently rehash and lease its dependency files.
No installed package is imported or discovered through a metadata API.
"""
from __future__ import annotations

import copy
from email.parser import BytesParser
import hashlib
import importlib.machinery
import math
import os
from pathlib import Path
import stat
import sys
import time

from .puck_dependency_files import HeldDependencyNamespace, _absolute, _canonical, _NAME
from .puck_dependency_bindings import validate_profile
from .puck_execution_files import _identity, _relative

MiB = 1024 ** 2
MAX_REGISTRATION_BYTES = 16 * MiB
MAX_FILES = 32768
MAX_FILE_BYTES = 2 * 1024 ** 3
MAX_TOTAL_BYTES = 16 * 1024 ** 3
MAX_CENSUS_ENTRIES = 60000
MAX_METADATA_BYTES = 4 * MiB
MAX_DEPTH = 32


def _clock(deadline):
    if time.monotonic() >= deadline:
        raise TimeoutError('Dependency registration deadline exhausted')


def _image_rows(observation, key):
    value = observation.get(key)
    if type(value) is not dict or type(value.get('images')) is not list:
        raise ValueError('Dependency observation requires retained image maps')
    result = []
    if len(value['images']) > MAX_FILES:
        raise ValueError('Dependency observed image count exceeds bound')
    for row in value['images']:
        if type(row) is not dict:
            raise ValueError('Dependency image map row is invalid')
        result.append(_absolute(row.get('path')))
    if len(result) != len(set(result)):
        raise ValueError('Dependency observed image paths are duplicated')
    return result


def _system_paths(site_root, observation):
    """Select exact retained image paths; never enumerate a system namespace."""
    site_root = _absolute(site_root)
    baseline = set(_image_rows(observation, 'baseline_maps'))
    result = []
    for path in _image_rows(observation, 'maps'):
        if path in baseline or path.startswith(site_root + '/'):
            continue
        if not path.startswith('/usr/lib/'):
            raise ValueError('Dependency observed system image is outside /usr/lib')
        relative = _relative(path[len('/usr/lib/'):])
        if len(relative.split('/')) > MAX_DEPTH:
            raise ValueError('Dependency system image depth exceeds bound')
        result.append(relative)
    return sorted(result)


class _Snapshot:
    """Nofollow directory edges and bounded streams, closed before return."""
    def __init__(self, deadline):
        self.deadline = deadline
        self.dirs = {}
        self.identities = set()
        self.file_count = 0
        self.total_bytes = 0

    def close(self):
        first = None
        for fd, _, _, _ in reversed(tuple(self.dirs.values())):
            try:
                os.close(fd)
            except OSError as error:
                if first is None:
                    first = error
        self.dirs.clear()
        if first is not None:
            raise first

    def directory(self, parts):
        _clock(self.deadline)
        if parts in self.dirs:
            self.check_directory(self.dirs[parts])
            return self.dirs[parts][0]
        if not parts:
            parent, name = None, '/'
            fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        else:
            parent = self.directory(parts[:-1]); name = parts[-1]
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        try:
            state = os.fstat(fd)
            expected = _identity(state)
            if not stat.S_ISDIR(state.st_mode) or state.st_nlink < 1:
                raise ValueError('Dependency ancestor is not a live directory')
            entry = (fd, parent, name, expected)
            self.check_directory(entry)
        except BaseException:
            os.close(fd)
            raise
        self.dirs[parts] = entry
        return fd

    def check_directory(self, entry):
        _clock(self.deadline)
        fd, parent, name, expected = entry
        if (_identity(os.fstat(fd)) != expected or
                _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
            raise RuntimeError('Dependency ancestor edge or metadata changed during staging')

    def recheck_directories(self):
        for entry in self.dirs.values():
            self.check_directory(entry)

    def census(self, root):
        result = {}
        root_parts = tuple(Path(root).parts[1:])
        def walk(parts, relative):
            directory = self.directory(parts)
            names = []
            with os.scandir(directory) as entries:
                for entry in entries:
                    _clock(self.deadline)
                    if len(result) + len(names) >= MAX_CENSUS_ENTRIES:
                        raise ValueError('Dependency package census exceeds bound')
                    names.append(entry.name)
            for name in sorted(names):
                _clock(self.deadline)
                path = _relative(relative + '/' + name if relative else name)
                if len(path.split('/')) > MAX_DEPTH:
                    raise ValueError('Dependency package namespace depth exceeds bound')
                if len(result) >= MAX_CENSUS_ENTRIES:
                    raise ValueError('Dependency package census exceeds bound')
                state = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if not (stat.S_ISREG(state.st_mode) or stat.S_ISDIR(state.st_mode)):
                    raise ValueError('Dependency package contains a symlink or special entry')
                if state.st_nlink < 1:
                    raise ValueError('Dependency package contains an unlinked entry')
                result[path] = _identity(state)
                if stat.S_ISDIR(state.st_mode):
                    walk((*parts, name), path)
        walk(root_parts, '')
        return result

    def admit(self, expected):
        if not stat.S_ISREG(expected[2]) or expected[6] < 1:
            raise ValueError('Dependency selected leaf must be a linked regular file')
        if not 0 <= expected[3] <= MAX_FILE_BYTES:
            raise ValueError('Dependency file byte ceiling exceeded')
        key = expected[:2]
        if key in self.identities:
            raise ValueError('Dependency selected inode alias is duplicated')
        self.identities.add(key)
        self.file_count += 1; self.total_bytes += expected[3]
        if self.file_count > MAX_FILES or self.total_bytes > MAX_TOTAL_BYTES:
            raise ValueError('Dependency global file or byte ceiling exceeded')

    def leaf_state(self, root, path):
        parts = path.split('/')
        parent = self.directory((*Path(root).parts[1:], *parts[:-1]))
        return _identity(os.stat(parts[-1], dir_fd=parent, follow_symlinks=False))

    def hash_leaf(self, root, path, expected, *, metadata=False):
        _clock(self.deadline)
        if metadata and expected[3] > MAX_METADATA_BYTES:
            raise ValueError('Dependency distribution METADATA exceeds copy ceiling')
        parts = path.split('/')
        parent = self.directory((*Path(root).parts[1:], *parts[:-1]))
        name = parts[-1]
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        try:
            def check():
                _clock(self.deadline)
                if (_identity(os.fstat(fd)) != expected or
                        _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
                    raise RuntimeError('Dependency leaf edge or metadata changed during staging')
            check()
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError('Dependency selected leaf is not regular')
            digest = hashlib.sha256(); count = 0
            payload = bytearray() if metadata else None
            while True:
                _clock(self.deadline)
                block = os.read(fd, min(MiB, expected[3] + 1 - count))
                if not block:
                    break
                count += len(block)
                if count > expected[3]:
                    raise RuntimeError('Dependency selected leaf grew during staging')
                digest.update(block)
                if payload is not None:
                    payload.extend(block)
            if count != expected[3]:
                raise RuntimeError('Dependency selected leaf size changed during staging')
            check()
            return ({'path': path, 'size_bytes': count, 'sha256': digest.hexdigest()},
                    bytes(payload) if payload is not None else None)
        finally:
            os.close(fd)


def _distribution(path, raw):
    try:
        raw.decode('utf-8', errors='strict')
        metadata = BytesParser().parsebytes(raw)
    except (UnicodeError, ValueError) as error:
        raise ValueError('Dependency distribution metadata is invalid UTF-8/email') from error
    names, versions = metadata.get_all('Name', []), metadata.get_all('Version', [])
    if metadata.defects or len(names) != 1 or len(versions) != 1:
        raise ValueError('Dependency distribution requires single Name and Version headers')
    return {'name': names[0], 'version': versions[0], 'root_index': 0, 'metadata_path': path}


def _module_maps(site_root, observation, profile, census):
    cache = observation.get('cache')
    if type(cache) is not dict or type(cache.get('modules')) is not list:
        raise ValueError('Dependency observation lacks retained module cache')
    rows = cache['modules']
    if len(rows) > MAX_FILES:
        raise ValueError('Dependency retained cache count exceeds bound')
    if type(profile) is not dict or set(profile) != {'exports', 'module_changes', 'native_origins'}:
        raise ValueError('Dependency import profile fields differ')
    if any(type(value) is not list for value in profile.values()) or sum(map(len, profile.values())) > 1024:
        raise ValueError('Dependency import profile row bound exceeded')
    def profile_names(key):
        result = set()
        for item in profile[key]:
            if type(item) is not dict or type(item.get('name')) is not str:
                raise ValueError('Dependency import profile identity is invalid')
            if item['name'] in result:
                raise ValueError('Dependency import profile identity is duplicated')
            result.add(item['name'])
        return result
    exports = profile_names('exports'); changes = profile_names('module_changes')
    regular = {path for path, identity in census.items() if stat.S_ISREG(identity[2])}
    directories = {path for path, identity in census.items() if stat.S_ISDIR(identity[2])}
    physical = []; namespaces = []; seen = set()
    for row in rows:
        if type(row) is not dict:
            raise ValueError('Dependency retained cache row is invalid')
        name = row.get('name')
        if type(name) is not str or len(name) > 512 or not _NAME.fullmatch(name) or name in seen:
            raise ValueError('Dependency retained cache name is invalid or duplicated')
        seen.add(name)
        # These two identities belong to the controlled driver, not its packages.
        # The worker independently binds __mp_main__ to its captured __main__.
        if name in ('__main__', '__mp_main__') or name.split('.')[0] in sys.stdlib_module_names:
            continue
        if name in exports:
            continue
        file = row.get('file')
        if name in changes and file is None:
            stem = name.replace('.', '/')
            matches = [p for p in (stem + '.py', stem + '/__init__.py') if p in regular]
            if len(matches) != 1:
                raise ValueError('Dependency changed module requires exactly one physical source candidate')
            path = matches[0]
        elif row.get('spec_name') == name and type(file) is str:
            file = _absolute(file)
            if not file.startswith(site_root + '/'):
                raise ValueError('Dependency retained module source is outside package root')
            path = _relative(file[len(site_root) + 1:])
            if path not in regular:
                raise ValueError('Dependency retained module source is not attached to package bytes')
        elif row.get('spec_name') == name and 'file' in row and file is None and name not in changes:
            path = name.replace('.', '/')
            if path not in directories:
                raise ValueError('Dependency retained namespace has no matching censused directory')
            namespaces.append({'name': name, 'root_index': 0, 'path': path})
            continue
        else:
            raise ValueError('Dependency retained nonstdlib cache identity has no declared representation: ' + name)
        if path.endswith('.py'):
            kind = 'python'; package = path.endswith('/__init__.py')
        elif path.endswith(tuple(importlib.machinery.EXTENSION_SUFFIXES)):
            kind = 'extension'
            package = Path(path).name.startswith('__init__.')
        else:
            raise ValueError('Dependency physical module lacks a Python/native source suffix')
        physical.append({'name': name, 'root_index': 0, 'path': path, 'kind': kind, 'is_package': package})
    if not changes <= {row['name'] for row in physical}:
        raise ValueError('Dependency module-change identity is absent from retained cache')
    validate_profile(profile, physical, namespaces)
    return sorted(physical, key=lambda row: row['name']), sorted(namespaces, key=lambda row: row['name'])


def build_registration(site_root: str, observation: dict, profile: dict, *, deadline: float) -> dict:
    """Stage strict v2 registration; caller authenticates observation/profile.

    The site namespace is fully censused, while system images are selected only
    from retained, nonbaseline /usr/lib map paths. Every descriptor is closed
    before return. No authority is granted by this byte-staging operation.
    """
    if (type(deadline) not in (int, float) or not math.isfinite(deadline)
            or not 0 < deadline - time.monotonic() <= 180):
        raise ValueError('Dependency registration requires one future deadline at most 180 seconds')
    site_root = _absolute(site_root)
    if type(observation) is not dict:
        raise ValueError('Dependency observation must be a dictionary')
    system_paths = _system_paths(site_root, observation)
    snapshot = _Snapshot(deadline)
    try:
        before = snapshot.census(site_root)
        site_files = sorted(path for path, state in before.items() if stat.S_ISREG(state[2]))
        for path in site_files:
            snapshot.admit(before[path])
        selected_system = {}
        for path in system_paths:
            state = snapshot.leaf_state('/usr/lib', path)
            snapshot.admit(state); selected_system[path] = state
        modules, namespaces = _module_maps(site_root, observation, profile, before)
        files = []; distributions = []
        for path in site_files:
            metadata = path.endswith('.dist-info/METADATA')
            descriptor, raw = snapshot.hash_leaf(site_root, path, before[path], metadata=metadata)
            files.append(descriptor)
            if metadata:
                distributions.append(_distribution(path, raw))
        roots = [{'root': site_root, 'kind': 'package', 'files': files}]
        if selected_system:
            system_files = [snapshot.hash_leaf('/usr/lib', path, state)[0]
                            for path, state in selected_system.items()]
            roots.append({'root': '/usr/lib', 'kind': 'system_images', 'files': system_files})
        result = {'kind': 'puck-worker-dependencies-v2', 'version': 2, 'roots': roots,
                  'modules': modules, 'namespaces': namespaces,
                  'distributions': distributions, 'import_profile': copy.deepcopy(profile)}
        try:
            raw = _canonical(result)
        except (UnicodeError, RecursionError, TypeError) as error:
            raise ValueError('Dependency registration cannot be represented as canonical JSON') from error
        if len(raw) > MAX_REGISTRATION_BYTES:
            raise ValueError('Dependency registration exceeds serialized byte ceiling')
        # Construction validates the pure schema only: no __enter__, payload IO,
        # signal ownership, leases, or runtime imports occur here.
        HeldDependencyNamespace(raw, expected_sha256=hashlib.sha256(raw).hexdigest(), deadline=deadline,
            registration_path=str(Path(site_root).parent / '.puck-registration-schema-only.json'))
        snapshot.recheck_directories()
        if snapshot.census(site_root) != before:
            raise RuntimeError('Dependency package namespace changed during staging')
        for path, expected in selected_system.items():
            if snapshot.leaf_state('/usr/lib', path) != expected:
                raise RuntimeError('Dependency system image edge changed during staging')
        snapshot.recheck_directories()
        _clock(deadline)
        return result
    finally:
        snapshot.close()
