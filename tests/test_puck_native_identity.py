"""Authored descriptor checks only; no installed native payloads are read."""
from __future__ import annotations

from contextlib import contextmanager, suppress
import ctypes
import errno
import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import pytest


def _api():
    return importlib.import_module('palimpsest.puck_native_identity')


@contextmanager
def _authored_file(directory='/tmp'):
    with tempfile.TemporaryDirectory(prefix='palimpsest-native-identity-', dir=directory) as root:
        path = Path(root) / 'authored.bin'
        path.write_bytes(b'authored descriptor identity fixture\n')
        fd = os.open(path, os.O_RDWR)
        try:
            yield fd, path
        finally:
            with suppress(OSError):
                os.close(fd)


def _at_fstatfs_boundary(monkeypatch, action, *, before=False):
    """Keep the real syscall; author a lifetime change at its call boundary."""
    original_cdll = ctypes.CDLL
    libc = original_cdll(None, use_errno=True)
    real_fstatfs = libc.fstatfs
    real_fstatfs.argtypes = (ctypes.c_int, ctypes.c_void_p)
    real_fstatfs.restype = ctypes.c_int

    def invoke(fd, buffer):
        if before:
            action(fd)
        result = real_fstatfs(fd, buffer)
        if not before:
            action(fd)
        return result

    monkeypatch.setattr(ctypes, 'CDLL', lambda *args, **kwargs: SimpleNamespace(fstatfs=invoke))


def test_tmpfs_descriptor_returns_raw_identity_and_remains_open():
    with _authored_file() as (fd, _):
        state = os.fstat(fd)
        assert _api().require_tmpfs_descriptor(fd) == (state.st_dev, state.st_ino)
        assert os.fstat(fd) == state


def test_same_contents_in_distinct_tmpfs_objects_keep_distinct_identities():
    with _authored_file() as (first_fd, _), _authored_file() as (second_fd, _):
        first = _api().require_tmpfs_descriptor(first_fd)
        second = _api().require_tmpfs_descriptor(second_fd)
        assert first != second
        assert first == (os.fstat(first_fd).st_dev, os.fstat(first_fd).st_ino)
        assert second == (os.fstat(second_fd).st_dev, os.fstat(second_fd).st_ino)


def test_persistent_repository_file_is_refused():
    runs = Path(__file__).resolve().parents[1] / 'runs'
    with _authored_file(runs) as (fd, _):
        with pytest.raises(ValueError, match='tmpfs'):
            _api().require_tmpfs_descriptor(fd)
        assert os.fstat(fd).st_nlink == 1


class _DescriptorSubclass(int):
    pass


@pytest.mark.parametrize('fd', [-1, True, None, 1.0, '3', _DescriptorSubclass(3), 1 << 80])
def test_descriptor_must_be_exact_nonnegative_c_int(fd):
    with pytest.raises(ValueError, match='descriptor'):
        _api().require_tmpfs_descriptor(fd)


def test_directory_descriptor_is_refused():
    fd = os.open('/tmp', os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(ValueError, match='regular'):
            _api().require_tmpfs_descriptor(fd)
    finally:
        os.close(fd)


def test_unlinked_regular_descriptor_is_refused():
    with _authored_file() as (fd, path):
        path.unlink()
        with pytest.raises(ValueError, match='named|link'):
            _api().require_tmpfs_descriptor(fd)


def test_closed_descriptor_preserves_ebadf():
    with _authored_file() as (fd, _):
        os.close(fd)
        with pytest.raises(OSError) as raised:
            _api().require_tmpfs_descriptor(fd)
        assert raised.value.errno == errno.EBADF


def test_descriptor_closed_before_real_fstatfs_preserves_ebadf(monkeypatch):
    with _authored_file() as (fd, _):
        _at_fstatfs_boundary(monkeypatch, os.close, before=True)
        with pytest.raises(OSError) as raised:
            _api().require_tmpfs_descriptor(fd)
        assert raised.value.errno == errno.EBADF


@pytest.mark.parametrize('change', ['content', 'mode', 'links'])
def test_descriptor_change_during_fstatfs_is_refused(monkeypatch, change):
    with _authored_file() as (fd, path):
        actions = {
            'content': lambda live_fd: os.ftruncate(live_fd, 1),
            'mode': lambda live_fd: os.fchmod(live_fd, 0o400),
            'links': lambda live_fd: path.unlink(),
        }
        _at_fstatfs_boundary(monkeypatch, actions[change])
        with pytest.raises(ValueError, match='changed|stable'):
            _api().require_tmpfs_descriptor(fd)


def test_descriptor_closed_after_real_fstatfs_preserves_ebadf(monkeypatch):
    with _authored_file() as (fd, _):
        _at_fstatfs_boundary(monkeypatch, os.close)
        with pytest.raises(OSError) as raised:
            _api().require_tmpfs_descriptor(fd)
        assert raised.value.errno == errno.EBADF


def test_unsupported_platform_is_refused_before_loading_libc(monkeypatch):
    with _authored_file() as (fd, _):
        monkeypatch.setattr(sys, 'platform', 'darwin')

        def unexpected_load(*args, **kwargs):
            pytest.fail('unsupported platform attempted to load libc')

        monkeypatch.setattr(ctypes, 'CDLL', unexpected_load)
        with pytest.raises(ValueError, match='ABI|Linux'):
            _api().require_tmpfs_descriptor(fd)


def test_module_import_keeps_ctypes_lazy():
    completed = subprocess.run(
        [sys.executable, '-B', '-c',
         "import sys; assert 'ctypes' not in sys.modules; "
         "import palimpsest.puck_native_identity; assert 'ctypes' not in sys.modules"],
        capture_output=True, text=True, check=False, timeout=15,
    )
    assert completed.returncode == 0, completed.stderr
