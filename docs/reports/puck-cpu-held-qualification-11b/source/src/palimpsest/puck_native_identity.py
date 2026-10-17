"""Admit raw descriptor identities only on the supported tmpfs ABI.

This check grants no execution authority. The caller retains custody of the
live descriptor and must prevent concurrent closure or descriptor replacement.
"""
from __future__ import annotations

import os
import stat
import sys


TMPFS_IDENTITY_POLICY = 'tmpfs-raw-dev-inode-v1'
_TMPFS_MAGIC = 0x01021994


def _stat_identity(state: os.stat_result) -> tuple:
    # stat_result's sequence omits nanoseconds and these Linux stat fields.
    return tuple(state) + (
        state.st_atime_ns, state.st_mtime_ns, state.st_ctime_ns,
        state.st_rdev, state.st_blksize, state.st_blocks,
    )


def require_tmpfs_descriptor(fd: int) -> tuple[int, int]:
    """Require a stable, linked regular tmpfs file and return its raw identity.

    The fstatfs layout is deliberately limited to Linux x86-64 LP64: glibc
    bits/statfs.h starts with signed native-long f_type; its 120-byte structure
    fits in the aligned 256-byte buffer. No pathname is resolved.
    """
    if type(fd) is not int or fd < 0 or fd > 0x7fffffff:
        raise ValueError('Native identity requires an exact nonnegative int descriptor')
    if (sys.platform != 'linux' or sys.maxsize != 0x7fffffffffffffff
            or sys.byteorder != 'little' or os.uname().machine != 'x86_64'):
        raise ValueError('Native identity requires the supported Linux x86-64 LP64 ABI')

    # Legacy providers must not import ctypes or load its extension eagerly.
    import ctypes

    if (ctypes.sizeof(ctypes.c_void_p) != 8 or ctypes.sizeof(ctypes.c_long) != 8
            or ctypes.sizeof(ctypes.c_int) != 4):
        raise ValueError('Native identity requires the supported Linux x86-64 LP64 ABI')

    before = os.fstat(fd)
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('Native identity requires a regular file descriptor')
    if before.st_nlink < 1:
        raise ValueError('Native identity requires a named file with a live link')

    libc = ctypes.CDLL(None, use_errno=True)
    try:
        fstatfs = libc.fstatfs
    except AttributeError as error:
        raise ValueError('Native identity requires libc fstatfs support') from error
    fstatfs.argtypes = (ctypes.c_int, ctypes.c_void_p)
    fstatfs.restype = ctypes.c_int
    buffer = (ctypes.c_long * 32)()
    ctypes.set_errno(0)
    if fstatfs(fd, buffer) != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, 'fstatfs: ' + os.strerror(error_number))
    if buffer[0] != _TMPFS_MAGIC:
        raise ValueError('Native identity requires tmpfs; observed f_type=' + hex(buffer[0]))

    after = os.fstat(fd)
    if _stat_identity(before) != _stat_identity(after):
        raise ValueError('Native descriptor identity changed during filesystem admission')
    return before.st_dev, before.st_ino
