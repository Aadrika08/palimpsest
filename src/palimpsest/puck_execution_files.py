"""Read-only descriptor custody for a registered collection's filesystem inputs.

This holds actual files and every directory edge; it neither imports a model
runtime nor grants collection, allocation, pruning, or scientific qualification.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
import stat
import time

MiB = 1024 ** 2
MAX_FILE_BYTES = 32 * MiB
MAX_TOTAL_BYTES = 64 * MiB
MAX_FILES = 512


def _relative(value):
    if (type(value) is not str or not value or value.startswith('/')
            or '\\' in value or ':' in value
            or any(ord(char) < 32 or ord(char) == 127 for char in value)
            or any(part in ('', '.', '..') for part in value.split('/'))):
        raise ValueError('Collection input path must be canonical relative POSIX text')
    return value


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


@dataclass(frozen=True)
class _Entry:
    path: str
    size: int
    sha256: str


class HeldCollectionFiles:
    """One-shot read-only custody; an expired, failed or closed object is unusable.

    Fixed descriptors have exactly path/size_bytes/sha256. ``read`` copies at
    most four MiB; larger registered runtime files are hashed in one MiB blocks
    without a byte copy. No file pathname or descriptor escape API is provided.
    Callers must keep this context open through their final admission decision.
    """

    def __init__(self, root, entries, deadline, exact_subtrees=()):
        raw_root = os.fspath(root)
        if (type(raw_root) is not str or not raw_root.startswith('/')
                or any(part in ('.', '..') for part in raw_root.split('/'))):
            raise ValueError('Collection root must be absolute without traversal')
        self._root = Path(raw_root)
        if (type(deadline) not in (int, float) or not math.isfinite(deadline)):
            raise ValueError('Collection deadline must be finite')
        self._deadline_value = deadline
        if type(entries) not in (list, tuple) or not 1 <= len(entries) <= MAX_FILES:
            raise ValueError('Collection file count is outside the registered bound')
        parsed = []
        for row in entries:
            if type(row) is not dict:
                raise ValueError('Collection descriptor must be a dictionary')
            if set(row) != {'path', 'size_bytes', 'sha256'}:
                raise ValueError('Collection descriptor has missing or unknown fields')
            path = _relative(row['path'])
            digest = row['sha256']
            if (type(digest) is not str or len(digest) != 64
                    or any(char not in '0123456789abcdef' for char in digest)):
                raise ValueError('Collection descriptor requires exact lowercase SHA-256')
            size = row['size_bytes']
            if type(size) is not int or not 0 <= size <= MAX_FILE_BYTES:
                raise ValueError('Collection descriptor size exceeds its bound')
            parsed.append(_Entry(path, size, digest))
        paths = [row.path for row in parsed]
        if paths != sorted(set(paths)):
            raise ValueError('Collection descriptors must be sorted and distinct')
        if sum(row.size for row in parsed) > MAX_TOTAL_BYTES:
            raise ValueError('Collection aggregate exceeds 64 MiB')
        if type(exact_subtrees) not in (list, tuple):
            raise ValueError('Exact collection subtrees must be an ordered collection')
        subtrees = tuple(_relative(value) for value in exact_subtrees)
        if len(set(subtrees)) != len(subtrees):
            raise ValueError('Exact collection subtrees must be distinct')
        self._entries = {row.path: row for row in parsed}
        self._subtrees = subtrees
        self._fds = []
        self._dirs = {}
        self._files = {}
        self._state = 'new'

    @property
    def root(self):
        return self._root

    @property
    def deadline(self):
        return self._deadline_value

    def _clock(self):
        if time.monotonic() >= self.deadline:
            raise TimeoutError('Collection file custody deadline exhausted')

    def _active(self):
        if self._state != 'active':
            raise RuntimeError('Collection file custody is closed, failed or not entered')

    def _close(self):
        first = None
        while self._fds:
            fd = self._fds.pop()
            try:
                os.close(fd)
            except OSError as error:
                if first is None:
                    first = error
        if first is not None:
            raise first

    def _failed(self):
        self._state = 'failed'
        self._close()

    def _directory(self, key):
        if key in self._dirs:
            return self._dirs[key][0]
        self._clock()
        if not key:
            fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            parent, name = None, '/'
        else:
            parent = self._directory(key[:-1])
            name = key[-1]
            fd = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                         dir_fd=parent)
        self._fds.append(fd)
        before = _identity(os.fstat(fd))
        named = _identity(os.stat(name, dir_fd=parent, follow_symlinks=False))
        if before != named:
            raise RuntimeError('Collection directory edge changed during open')
        self._dirs[key] = (fd, parent, name, before)
        return fd

    def _check_dirs(self):
        for fd, parent, name, expected in self._dirs.values():
            self._clock()
            if (_identity(os.fstat(fd)) != expected
                    or _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
                raise RuntimeError('Collection root or ancestor changed while held')

    def _hash(self, fd, maximum, *, copy_bytes=False):
        os.lseek(fd, 0, os.SEEK_SET)
        digest = hashlib.sha256()
        count = 0
        payload = bytearray() if copy_bytes else None
        while True:
            self._clock()
            block = os.read(fd, min(MiB, maximum + 1 - count))
            if not block:
                break
            count += len(block)
            if count > maximum:
                raise ValueError('Collection file grew beyond its registered byte cap')
            digest.update(block)
            if payload is not None:
                payload.extend(block)
        return count, digest.hexdigest(), bytes(payload) if payload is not None else None

    def _check_file(self, relative, *, copy_bytes=False):
        entry = self._entries[relative]
        fd, parent, name, expected = self._files[relative]
        if (_identity(os.fstat(fd)) != expected
                or _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
            raise RuntimeError('Collection input file edge or metadata changed while held')
        count, digest, payload = self._hash(fd, entry.size, copy_bytes=copy_bytes)
        if (digest != entry.sha256 or count != entry.size
                or count != expected[3]):
            raise ValueError('Collection input file bytes or size differ')
        if (_identity(os.fstat(fd)) != expected
                or _identity(os.stat(name, dir_fd=parent, follow_symlinks=False)) != expected):
            raise RuntimeError('Collection input changed during byte read')
        return payload

    def _walk(self, relative, expected_files, expected_dirs):
        """Inventory only registered children; extra/deep namespaces fail early."""
        key = (*self.root.parts[1:], *relative.split('/'))
        directory = self._directory(key)
        allowed = {path[len(relative) + 1:].split('/')[0]
                   for path in expected_files | expected_dirs
                   if path.startswith(relative + '/')}
        names = set()
        with os.scandir(directory) as iterator:
            for item in iterator:
                self._clock()
                if item.name not in allowed or item.name in names:
                    raise ValueError('Exact collection subtree contains an unregistered entry')
                names.add(item.name)
        if names != allowed:
            raise ValueError('Exact collection subtree lacks a registered entry')
        found_files, found_dirs = set(), {relative}
        for name in sorted(names):
            self._clock()
            child = relative + '/' + name
            state = os.stat(name, dir_fd=directory, follow_symlinks=False)
            if child in expected_dirs and stat.S_ISDIR(state.st_mode):
                files, dirs = self._walk(child, expected_files, expected_dirs)
                found_files.update(files)
                found_dirs.update(dirs)
            elif child in expected_files and stat.S_ISREG(state.st_mode):
                found_files.add(child)
            else:
                raise ValueError('Exact collection subtree entry type differs from its contract')
        return found_files, found_dirs

    def _check_subtrees(self):
        for subtree in self._subtrees:
            expected_files = {path for path in self._entries if path.startswith(subtree + '/')}
            if not expected_files:
                raise ValueError('Exact collection subtree has no registered leaf files')
            expected_dirs = {subtree}
            for path in expected_files:
                parent = path.rsplit('/', 1)[0]
                while parent != subtree:
                    expected_dirs.add(parent)
                    parent = parent.rsplit('/', 1)[0]
            files, dirs = self._walk(subtree, expected_files, expected_dirs)
            if files != expected_files or dirs != expected_dirs:
                raise ValueError('Exact collection subtree contains missing or unregistered entries')

    def __enter__(self):
        if self._state != 'new':
            raise RuntimeError('Collection file custody can only be entered once')
        try:
            self._clock()
            root_key = self.root.parts[1:]
            self._directory(root_key)
            self._check_subtrees()
            identities = set()
            for entry in self._entries.values():
                parts = entry.path.split('/')
                parent = self._directory((*root_key, *parts[:-1]))
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                             dir_fd=parent)
                self._fds.append(fd)
                state = os.fstat(fd)
                expected = _identity(state)
                if (not stat.S_ISREG(state.st_mode) or state.st_nlink != 1
                        or state.st_size > entry.size
                        or state.st_size != entry.size
                        or (state.st_dev, state.st_ino) in identities):
                    raise ValueError('Collection leaf type, alias count or size differs')
                identities.add((state.st_dev, state.st_ino))
                self._files[entry.path] = (fd, parent, parts[-1], expected)
                self._check_file(entry.path)
            self._state = 'active'
            self.recheck()
            return self
        except BaseException:
            self._failed()
            raise

    def recheck(self):
        self._active()
        try:
            self._clock()
            self._check_dirs()
            self._check_subtrees()
            for relative in self._entries:
                self._check_file(relative)
            self._check_dirs()
            self._clock()
        except BaseException:
            self._failed()
            raise

    def _guard(self, relative):
        self._active()
        relative = _relative(relative)
        if relative not in self._entries:
            raise ValueError('Collection path was not registered')
        try:
            self._clock()
            self._check_dirs()
            self._check_subtrees()
            self._check_file(relative)
            self._check_dirs()
            self._clock()
        except BaseException:
            self._failed()
            raise
        return relative

    def read(self, relative, max_bytes):
        self._active()
        if type(max_bytes) is not int or not 0 <= max_bytes <= 4 * MiB:
            raise ValueError('Collection small read cap must be an integer at most four MiB')
        relative = self._guard(relative)
        if self._files[relative][3][3] > max_bytes:
            raise ValueError('Collection file exceeds the requested small read cap')
        try:
            payload = self._check_file(relative, copy_bytes=True)
            self._check_dirs()
            self._clock()
            return payload
        except BaseException:
            self._failed()
            raise

    def __exit__(self, kind, error, traceback):
        if self._state != 'active':
            if kind is None:
                raise RuntimeError('Collection custody failed before context exit')
            return False
        try:
            self.recheck()
        finally:
            if self._state == 'active':
                self._state = 'closed'
            self._close()
        return False
