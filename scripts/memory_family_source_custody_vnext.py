"""Shared bounded custody primitives for source producer and later consumers.

This module deliberately owns only path/FD custody.  It grants no source
attempt, acceptance, or execution authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import stat
import threading
import time

from scripts import memory_family_source_records_vnext as wire
from scripts.memory_family_replay_custody_v4 import HeldReplayFiles, _identity
from scripts.memory_source_runtime_closure_v1 import RuntimeHandle


_DIRECTORY_TOKEN = object()
_REGISTRY_TOKEN = object()


@dataclass
class _Binding:
    descriptor: dict
    owner: object | None
    fd: int | None
    identity: tuple | None
    roles: set


class _SourcePathRegistry:
    def __init__(self, token, deadline_ns):
        if token is not _REGISTRY_TOKEN:
            raise ValueError('Private source registry')
        self._thread_id = threading.get_ident()
        self._deadline_ns = deadline_ns
        self._active = True
        self._paths = {}
        self._inodes = {}
        self._directory_inodes = {}
        self._runtime_registered = False

    def _check(self):
        if not self._active or self._thread_id != threading.get_ident():
            raise RuntimeError('Inactive/cross-thread source registry')
        if time.monotonic_ns() >= self._deadline_ns:
            raise TimeoutError('Source registry deadline')

    def claim(self, descriptor, role):
        self._check()
        descriptor = wire.descriptor(descriptor, True)
        wire.text(role, 96)
        path = descriptor['path']
        current = self._paths.get(path)
        if current is not None:
            if wire.encode(current.descriptor) != wire.encode(descriptor):
                raise ValueError('Conflicting source descriptors')
            current.roles.add(role)
            return 'reuse'
        if len(self._paths) >= 60000:
            raise ValueError('Source registry leaf cap')
        self._paths[path] = _Binding(descriptor, None, None, None, {role})
        return 'new'

    def _register(self, holder):
        for relative, entry in holder._entries.items():
            path = '/' + relative
            descriptor = dict(path=path, size_bytes=entry.size, sha256=entry.sha256)
            self.claim(descriptor, 'held')
            binding = self._paths[path]
            fd, _, _, expected = holder._files[relative]
            actual = _identity(os.fstat(fd))
            if actual != expected or not stat.S_ISREG(actual[2]) or actual[6] != 1:
                raise ValueError('Held source leaf identity')
            inode = actual[:2]
            if inode in self._inodes and self._inodes[inode] != path:
                raise ValueError('Global source inode alias')
            if binding.owner is not None and (binding.owner is not holder or binding.fd != fd):
                raise ValueError('Duplicate source FD owner')
            binding.owner = holder
            binding.fd = fd
            binding.identity = actual
            self._inodes[inode] = path

    def register_runtime(self, handle):
        self._check()
        if (type(handle) is not RuntimeHandle or self._runtime_registered
                or any(binding.owner is not None for binding in self._paths.values())):
            raise TypeError('Genuine runtime must be registered first once')
        handle.recheck()
        for holder in handle._holders:
            self._register(holder)
        handle.recheck()
        self._runtime_registered = True

    def register_batch(self, holder):
        self._check()
        if type(holder) is not HeldReplayFiles:
            raise TypeError('Genuine replay batch required')
        holder.recheck()
        self._register(holder)
        holder.recheck()

    def binding(self, path):
        self._check()
        wire.path(path, True)
        binding = self._paths.get(path)
        if binding is None or binding.owner is None:
            raise ValueError('Source path is not held')
        return binding

    def recheck(self):
        self._check()
        try:
            for binding in self._paths.values():
                if binding.owner is None:
                    raise RuntimeError('Unbound source claim')
                if (binding.owner._state != 'active'
                        or _identity(os.fstat(binding.fd)) != binding.identity):
                    raise RuntimeError('Source owner/FD no longer active')
            self._check()
        except BaseException:
            self._active = False
            raise

    def invalidate(self):
        if self._thread_id != threading.get_ident():
            raise RuntimeError('Cross-thread registry invalidate')
        self._active = False


class _HeldDirectoryClosure:
    def __init__(self, token, *, trees, ancestor_targets, deadline_ns, registry):
        if token is not _DIRECTORY_TOKEN or type(registry) is not _SourcePathRegistry:
            raise ValueError('Private directory closure')
        if type(trees) is not tuple or type(ancestor_targets) is not tuple:
            raise ValueError('Immutable directory inputs')
        self._state = 'new'
        self._thread_id = threading.get_ident()
        self._deadline_ns = deadline_ns
        self._registry = registry
        self._dirs = {}
        self._fds = []
        self._children = {}
        self._directory_inodes = registry._directory_inodes
        targets = set(ancestor_targets)
        for tree in trees:
            wire.fields(tree, ('root', 'directories', 'files'))
            root = wire.path(tree['root'], True)
            directories = tree['directories']
            if type(directories) is not list or directories != sorted(set(directories)) or len(directories) > 60000:
                raise ValueError('Directory roster')
            local = {root: {}}
            for relative in directories:
                wire.path(relative)
                local[root + '/' + relative] = {}
            for directory in list(local):
                if directory == root:
                    continue
                parent, name = directory.rsplit('/', 1)
                if parent not in local:
                    raise ValueError('Directory parent closure missing')
                local[parent][name] = 'directory'
            for descriptor in tree['files']:
                wire.descriptor(descriptor, True)
                path = descriptor['path']
                parent, name = path.rsplit('/', 1)
                if not path.startswith(root + '/') or parent not in local or name in local[parent]:
                    raise ValueError('File/dir closure conflict')
                local[parent][name] = 'file'
            for directory, children in local.items():
                if directory in self._children and self._children[directory] != children:
                    raise ValueError('Contradictory closed trees')
                self._children[directory] = children
                targets.add(directory)
        if len(self._children) > 60000:
            raise ValueError('Directory closure cap')
        for target in targets:
            wire.path(target, True)
        self._targets = tuple(sorted(targets))

    def _check(self, active=True):
        if self._thread_id != threading.get_ident() or (active and self._state != 'active'):
            raise RuntimeError('Inactive/cross-thread directory custody')
        if time.monotonic_ns() >= self._deadline_ns:
            raise TimeoutError('Directory custody deadline')

    def _open_directory(self, path):
        self._check(False)
        wire.path(path, True)
        if path in self._dirs:
            return self._dirs[path][0]
        parent_path, name = path.rsplit('/', 1) if path != '/' else ('', '/')
        parent = self._open_directory(parent_path or '/') if path != '/' else None
        before = _identity(os.stat(name, dir_fd=parent, follow_symlinks=False))
        if not stat.S_ISDIR(before[2]):
            raise ValueError('Non-directory ancestor')
        fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
        self._fds.append(fd)
        if (_identity(os.fstat(fd)) != before
                or _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != before):
            raise RuntimeError('Directory changed while opening')
        inode = before[:2]
        if inode in self._directory_inodes and self._directory_inodes[inode] != path:
            raise ValueError('Directory inode alias')
        self._directory_inodes[inode] = path
        self._dirs[path] = (fd, parent, name, before)
        return fd

    def _edges(self):
        for directory, (fd, parent, name, identity) in self._dirs.items():
            self._check()
            if (_identity(os.fstat(fd)) != identity
                    or _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != identity):
                raise RuntimeError('Full-stat source ancestor changed: ' + directory)

    def _census(self):
        for directory, expected in self._children.items():
            fd = self._dirs[directory][0]
            names = set()
            scan = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                with os.scandir(scan) as entries:
                    for entry in entries:
                        self._check()
                        if len(names) >= len(expected) or entry.name not in expected or entry.name in names:
                            raise ValueError('Unexpected closed directory child')
                        names.add(entry.name)
                        state = entry.stat(follow_symlinks=False)
                        if expected[entry.name] == 'directory':
                            good = stat.S_ISDIR(state.st_mode)
                        else:
                            good = stat.S_ISREG(state.st_mode) and state.st_nlink == 1
                        if not good:
                            raise ValueError('Closed directory child kind/link differs')
            finally:
                os.close(scan)
            if names != set(expected):
                raise ValueError('Missing closed directory child')

    def _drain(self, primary=None):
        failures = [primary] if primary is not None else []
        while self._fds:
            try:
                os.close(self._fds.pop())
            except BaseException as error:
                failures.append(error)
        self._state = 'closed' if not failures else 'poisoned'
        if failures and (primary is None or len(failures) > 1):
            raise wire.errors('Source directory teardown', failures)

    def __enter__(self):
        self._check(False)
        if self._state != 'new':
            raise RuntimeError('Directory closure one-shot')
        try:
            for target in self._targets:
                self._open_directory(target)
            self._state = 'active'
            self.recheck()
            return self
        except BaseException as error:
            self._state = 'poisoned'
            self._drain(error)
            raise

    def recheck(self):
        self._check()
        try:
            self._edges()
            self._census()
            self._edges()
            self._check()
        except BaseException as error:
            self._state = 'poisoned'
            self._drain(error)
            raise

    def require_children(self, directory):
        self.recheck()
        if directory not in self._children:
            raise ValueError('Not a closed directory')
        return tuple(sorted(self._children[directory].items()))

    def __exit__(self, kind, error, traceback):
        failures = [error] if error is not None else []
        if self._state == 'active':
            try:
                self.recheck()
            except BaseException as failure:
                failures.append(failure)
        self._state = 'closing'
        try:
            self._drain()
        except BaseException as failure:
            failures.append(failure)
        if failures and (error is None or len(failures) > 1):
            raise wire.errors('Source directory exit', failures)
        return False


def _batches(descriptors):
    batch = []
    size = 0
    for row in sorted(descriptors, key=lambda value: value['path']):
        wire.descriptor(row, True, 1024 * wire.MiB)
        if batch and (len(batch) == 512 or size + row['size_bytes'] > 2048 * wire.MiB):
            yield batch
            batch = []
            size = 0
        batch.append(dict(row, path=row['path'][1:]))
        size += row['size_bytes']
    if batch:
        yield batch
