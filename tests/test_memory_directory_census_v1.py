"""Tiny authored namespace checks; no model, qualification or study execution."""
from __future__ import annotations

from contextlib import contextmanager
import importlib
import importlib.util
import os
from pathlib import Path
import tempfile
import time

import pytest


def module():
    name = 'scripts.memory_directory_census_v1'
    assert importlib.util.find_spec(name) is not None, 'Fresh directory census is missing'
    return importlib.import_module(name)


@contextmanager
def directory(path):
    path.mkdir()
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        yield fd
    finally:
        os.close(fd)


def fdinfo(fd):
    return (Path('/proc/self/fdinfo') / str(fd)).read_text()


class WrappedScan:
    def __init__(self, original, before_next=None, close_error=None):
        self.original = original
        self.before_next = before_next
        self.close_error = close_error

    def __iter__(self):
        return self

    def __next__(self):
        if self.before_next is not None:
            self.before_next()
        return next(self.original)

    def close(self):
        self.original.close()
        if self.close_error is not None:
            raise self.close_error


@pytest.mark.parametrize('filesystem', ['project', 'tmpfs'])
def test_created_entries_are_visible_on_first_census(tmp_path, filesystem):
    m = module()
    with tempfile.TemporaryDirectory(prefix='memory-census-authored-',
            dir=tmp_path if filesystem == 'project' else '/tmp') as temporary:
        path = Path(temporary) / 'tree'
        path.mkdir()
        (path / 'owner.json').write_bytes(b'{}')
        (path / 'snapshots').mkdir()
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            assert set(os.listdir(fd)) == {'owner.json', 'snapshots'}
            (path / 'recording').mkdir()
            (path / 'worker-report.json').write_bytes(b'{}')
            assert set(m.directory_names(fd, max_entries=4)) == {
                'owner.json', 'snapshots', 'recording', 'worker-report.json'}
            (path / 'worker-report.json').unlink()
            (path / 'second.json').write_bytes(b'{}')
            assert set(m.directory_names(fd, max_entries=4)) == {
                'owner.json', 'snapshots', 'recording', 'second.json'}
            assert os.fstat(fd).st_ino == path.stat().st_ino
        finally:
            os.close(fd)


def test_census_keeps_a_live_callers_directory_cursor_and_fd(tmp_path):
    m = module()
    path = tmp_path / 'tree'
    path.mkdir()
    for name in ('a', 'b', 'c'):
        (path / name).write_bytes(b'')
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        with os.scandir(fd) as caller_scan:
            first = next(caller_scan).name
            before = fdinfo(fd)
            assert set(m.directory_names(fd, max_entries=3)) == {'a', 'b', 'c'}
            assert fdinfo(fd) == before
            assert {first, *(entry.name for entry in caller_scan)} == {'a', 'b', 'c'}
        os.fstat(fd)
    finally:
        os.close(fd)


def test_empty_directory_accepts_zero_bound(tmp_path):
    m = module()
    with directory(tmp_path / 'tree') as fd:
        assert m.directory_names(fd, max_entries=0) == []


def test_extra_entry_stops_after_bound_plus_one(tmp_path, monkeypatch):
    m = module()
    path = tmp_path / 'tree'
    with directory(path) as fd:
        for name in ('a', 'b', 'c', 'd', 'e'):
            (path / name).write_bytes(b'')
        original = os.scandir
        calls = []
        with monkeypatch.context() as patch:
            patch.setattr(m.os, 'scandir', lambda scan_fd: WrappedScan(
                original(scan_fd), lambda: calls.append('next')))
            with pytest.raises(ValueError, match='bound|limit|entries'):
                m.directory_names(fd, max_entries=2)
        assert len(calls) == 3
        os.fstat(fd)


def test_fresh_open_must_bind_the_original_directory(tmp_path, monkeypatch):
    m = module()
    with directory(tmp_path / 'tree') as fd, directory(tmp_path / 'other') as other:
        wrong = os.open('.', os.O_RDONLY | os.O_DIRECTORY, dir_fd=other)
        with monkeypatch.context() as patch:
            patch.setattr(m.os, 'open', lambda *args, **kwargs: wrong)
            with pytest.raises(RuntimeError, match='identity|changed|differ'):
                m.directory_names(fd, max_entries=1)
        with pytest.raises(OSError):
            os.fstat(wrong)
        os.fstat(fd)
        os.fstat(other)


def test_mutation_during_scan_is_rejected(tmp_path, monkeypatch):
    m = module()
    path = tmp_path / 'tree'
    with directory(path) as fd:
        (path / 'a').write_bytes(b'')
        original = os.scandir
        calls = []
        def mutate():
            calls.append('next')
            if len(calls) == 2:
                (path / 'injected').write_bytes(b'')
        with monkeypatch.context() as patch:
            patch.setattr(m.os, 'scandir', lambda scan_fd: WrappedScan(original(scan_fd), mutate))
            with pytest.raises(RuntimeError, match='identity|changed|differ'):
                m.directory_names(fd, max_entries=5)


@pytest.mark.parametrize('fd', [True, False, None, '4', 1.5])
def test_fd_must_be_an_exact_integer(fd):
    m = module()
    with pytest.raises(ValueError, match='descriptor|fd|integer'):
        m.directory_names(fd, max_entries=1)


@pytest.mark.parametrize('maximum', [True, False, -1, 4097, 1.5, '2', None])
def test_entry_bound_must_be_an_exact_bounded_integer(tmp_path, maximum):
    m = module()
    with directory(tmp_path / 'tree') as fd:
        with pytest.raises(ValueError, match='bound|limit|entries|integer'):
            m.directory_names(fd, max_entries=maximum)


@pytest.mark.parametrize('deadline', [True, False, float('nan'), float('inf'), -float('inf'), 'soon'])
def test_deadline_must_be_finite_numeric(tmp_path, deadline):
    m = module()
    with directory(tmp_path / 'tree') as fd:
        with pytest.raises(ValueError, match='deadline'):
            m.directory_names(fd, max_entries=1, deadline=deadline)


def test_closed_descriptor_is_rejected_and_file_is_not_a_directory(tmp_path):
    m = module()
    path = tmp_path / 'file'
    path.write_bytes(b'authored')
    fd = os.open(path, os.O_RDONLY)
    try:
        with pytest.raises(NotADirectoryError):
            m.directory_names(fd, max_entries=1)
    finally:
        os.close(fd)
    with pytest.raises((ValueError, OSError)):
        m.directory_names(fd, max_entries=1)


def test_expired_deadline_refuses_before_open(tmp_path, monkeypatch):
    m = module()
    with directory(tmp_path / 'tree') as fd:
        with monkeypatch.context() as patch:
            patch.setattr(m.os, 'open', lambda *a, **k: pytest.fail('Expired census opened a directory'))
            with pytest.raises(TimeoutError, match='deadline'):
                m.directory_names(fd, max_entries=1, deadline=time.monotonic() - 1)


def test_deadline_is_checked_during_enumeration(tmp_path, monkeypatch):
    m = module()
    path = tmp_path / 'tree'
    with directory(path) as fd:
        (path / 'a').write_bytes(b'')
        (path / 'b').write_bytes(b'')
        original = os.scandir
        clock = [0.0]
        calls = []
        def advance():
            calls.append('next')
            if len(calls) == 2:
                clock[0] = 2.0
        with monkeypatch.context() as patch:
            patch.setattr(m.time, 'monotonic', lambda: clock[0])
            patch.setattr(m.os, 'scandir', lambda scan_fd: WrappedScan(original(scan_fd), advance))
            with pytest.raises(TimeoutError, match='deadline'):
                m.directory_names(fd, max_entries=2, deadline=1.0)


def test_only_the_owned_fresh_descriptor_is_closed(tmp_path, monkeypatch):
    m = module()
    with directory(tmp_path / 'tree') as fd:
        original_open, original_close = os.open, os.close
        opened, closed = [], []
        def opening(path, flags, **kwargs):
            assert path == '.' and kwargs == {'dir_fd': fd}
            assert flags & os.O_DIRECTORY and flags & os.O_NOFOLLOW and flags & os.O_CLOEXEC
            fresh = original_open(path, flags, **kwargs)
            opened.append(fresh)
            return fresh
        def closing(value):
            closed.append(value)
            original_close(value)
        with monkeypatch.context() as patch:
            patch.setattr(m.os, 'open', opening)
            patch.setattr(m.os, 'close', closing)
            assert m.directory_names(fd, max_entries=0) == []
        assert len(opened) == 1 and opened == closed and fd not in closed
        os.fstat(fd)


def test_scan_error_survives_iterator_and_descriptor_cleanup_errors(tmp_path, monkeypatch):
    m = module()
    with directory(tmp_path / 'tree') as fd:
        original_scan, original_close = os.scandir, os.close
        primary = RuntimeError('authored scan failure')
        def fail():
            raise primary
        def closing(value):
            original_close(value)
            raise OSError('authored descriptor cleanup failure')
        with monkeypatch.context() as patch:
            patch.setattr(m.os, 'scandir', lambda scan_fd: WrappedScan(
                original_scan(scan_fd), fail, OSError('authored iterator cleanup failure')))
            patch.setattr(m.os, 'close', closing)
            with pytest.raises(RuntimeError, match='authored scan failure') as caught:
                m.directory_names(fd, max_entries=1)
        assert caught.value is primary
        notes = '\n'.join(caught.value.__notes__)
        assert 'iterator cleanup failure' in notes and 'descriptor cleanup failure' in notes
        os.fstat(fd)


def test_descriptor_cleanup_error_cannot_return_success(tmp_path, monkeypatch):
    m = module()
    with directory(tmp_path / 'tree') as fd:
        original_close = os.close
        def closing(value):
            original_close(value)
            raise OSError('authored cleanup failure')
        with monkeypatch.context() as patch:
            patch.setattr(m.os, 'close', closing)
            with pytest.raises(OSError, match='authored cleanup failure'):
                m.directory_names(fd, max_entries=0)
        os.fstat(fd)


def test_expiration_during_owned_cleanup_cannot_return_success(tmp_path, monkeypatch):
    m = module()
    with directory(tmp_path / 'tree') as fd:
        original_close = os.close
        clock = [0.0]
        def closing(value):
            original_close(value)
            clock[0] = 2.0
        with monkeypatch.context() as patch:
            patch.setattr(m.time, 'monotonic', lambda: clock[0])
            patch.setattr(m.os, 'close', closing)
            with pytest.raises(TimeoutError, match='deadline'):
                m.directory_names(fd, max_entries=0, deadline=1.0)
        os.fstat(fd)
