"""Bounded fresh directory enumeration without moving a caller's held cursor.

The caller retains responsibility for binding the held directory's named edges.
This checks the held directory and a fresh open description during one census;
it grants no replay, publication, pruning or qualification authority. Deadlines
are cooperative checks, not a bound on filesystem syscall duration.
"""
from __future__ import annotations

import math
import os
import stat
import time


def _identity(value):
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns, value.st_nlink)


def _check_deadline(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('Directory census deadline exhausted')


def directory_names(fd, *, max_entries, deadline=None) -> list[str]:
    """List at most ``max_entries`` names from an independently opened directory.

    A duplicate FD shares per-open directory state and is insufficient after
    publication writes on supported Btrfs. Opening "." relative to the retained
    descriptor obtains a fresh description while avoiding pathname traversal.
    Both descriptions must retain the same full directory identity throughout.
    Only the fresh description and its iterator are closed here.
    """
    if type(fd) is not int or fd < 0:
        raise ValueError('Directory census requires an exact nonnegative fd integer')
    if type(max_entries) is not int or not 0 <= max_entries <= 4096:
        raise ValueError('Directory census entry bound must be an integer from 0 to 4096')
    if (deadline is not None and (type(deadline) not in (int, float)
            or type(deadline) is float and not math.isfinite(deadline))):
        raise ValueError('Directory census deadline must be finite numeric time')
    _check_deadline(deadline)
    before = os.fstat(fd)
    if not stat.S_ISDIR(before.st_mode):
        raise NotADirectoryError('Directory census descriptor is not a directory')
    expected = _identity(before)
    fresh = None
    iterator = None
    failure = None
    names = []
    try:
        fresh = os.open('.', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC,
                        dir_fd=fd)
        if _identity(os.fstat(fresh)) != expected:
            raise RuntimeError('Directory census fresh identity differs from held directory')
        _check_deadline(deadline)
        iterator = os.scandir(fresh)
        while True:
            _check_deadline(deadline)
            try:
                entry = next(iterator)
            except StopIteration:
                break
            _check_deadline(deadline)
            if len(names) == max_entries:
                raise ValueError('Directory census exceeds its entry bound')
            names.append(entry.name)
        owned_iterator, iterator = iterator, None
        owned_iterator.close()
        _check_deadline(deadline)
        if (_identity(os.fstat(fd)) != expected
                or _identity(os.fstat(fresh)) != expected):
            raise RuntimeError('Directory census identity or namespace metadata changed')
    except BaseException as error:
        failure = error
    # Always attempt both cleanups. Preserve an existing primary failure and
    # attach secondary cleanup errors instead of replacing its evidence.
    for cleanup in ((iterator.close if iterator is not None else None),
                    (lambda: os.close(fresh)) if fresh is not None else None):
        if cleanup is not None:
            try:
                cleanup()
            except BaseException as error:
                if failure is None:
                    failure = error
                else:
                    failure.add_note('Directory census cleanup also failed: '
                                     + type(error).__name__ + ': ' + str(error))
    if failure is not None:
        raise failure
    _check_deadline(deadline)
    return names
