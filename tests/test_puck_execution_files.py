"""Execution input custody on authored temporary files only."""
import hashlib
import importlib
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

NAME = 'palimpsest.puck_execution_files'
MiB = 1024 ** 2


def module():
    assert importlib.util.find_spec(NAME) is not None, 'HeldCollectionFiles is missing'
    result = importlib.import_module(NAME)
    assert callable(getattr(result, 'HeldCollectionFiles', None))
    return result


def descriptor(path, payload):
    return {'path': path, 'size_bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}


def fixture(tmp_path):
    root = tmp_path / 'root'
    leaf = root / 'input/profile with space.json'
    leaf.parent.mkdir(parents=True)
    leaf.write_bytes(b'authored fixture')
    return root, leaf, [descriptor(leaf.relative_to(root).as_posix(), leaf.read_bytes())]


def held(root, entries, **kwargs):
    return module().HeldCollectionFiles(root, entries, time.monotonic() + 30, **kwargs)


def test_missing_api_red_then_readonly_lifetime(tmp_path):
    root, leaf, entries = fixture(tmp_path)
    before = leaf.stat()
    with held(root, entries, exact_subtrees=('input',)) as files:
        assert files.read(entries[0]['path'], 128) == b'authored fixture'
        assert files.recheck() is None
        assert not hasattr(files, 'path') and not hasattr(files, 'fd_path')
    assert leaf.stat() == before
    with pytest.raises(RuntimeError): files.read(entries[0]['path'], 128)
    with pytest.raises(RuntimeError): files.recheck()
    with pytest.raises(RuntimeError):
        with files: pass


@pytest.mark.parametrize('path', ['../controls/x', '/absolute', 'a//b', 'a/./b', 'a/../b', 'a\\b', '', 'a/', 'a\x00b'])
def test_canonical_relative_names(tmp_path, path):
    root, leaf, entries = fixture(tmp_path); entries[0]['path'] = path
    with pytest.raises(ValueError):
        with held(root, entries): pass


@pytest.mark.parametrize('defect', ['bool', 'float', 'negative', 'unknown-size', 'over-file', 'unknown-key', 'bad-hash', 'duplicate', 'unsorted', 'too-many', 'aggregate'])
def test_fixed_contract_refuses_type_aliases_bounds_and_order(tmp_path, defect):
    root, leaf, entries = fixture(tmp_path)
    if defect == 'bool': entries[0]['size_bytes'] = True
    elif defect == 'float': entries[0]['size_bytes'] = 1.0
    elif defect == 'negative': entries[0]['size_bytes'] = -1
    elif defect == 'unknown-size': entries[0]['size_bytes'] = None
    elif defect == 'over-file': entries[0]['size_bytes'] = 32 * MiB + 1
    elif defect == 'unknown-key': entries[0]['optional'] = True
    elif defect == 'bad-hash': entries[0]['sha256'] = 'Z' * 64
    elif defect == 'duplicate': entries *= 2
    elif defect == 'unsorted': entries = [descriptor('z', b'x'), descriptor('a', b'x')]
    elif defect == 'too-many': entries = [descriptor(f'{i:04d}', b'x') for i in range(513)]
    elif defect == 'aggregate': entries = [dict(descriptor(str(i), b'x'), size_bytes=32 * MiB) for i in range(3)]
    with pytest.raises(ValueError):
        with held(root, entries): pass


@pytest.mark.parametrize('kind', ['leaf-symlink', 'parent-symlink', 'root-symlink', 'outer-ancestor-symlink', 'hardlink', 'fifo'])
def test_aliases_and_special_entries_refused_without_blocking(tmp_path, kind):
    root, leaf, entries = fixture(tmp_path)
    if kind == 'leaf-symlink':
        target = root / 'target'; leaf.rename(target); leaf.symlink_to(target)
    elif kind == 'parent-symlink':
        target = root / 'target'; leaf.parent.rename(target); leaf.parent.symlink_to(target, target_is_directory=True)
    elif kind == 'root-symlink':
        target = tmp_path / 'target'; root.rename(target); root.symlink_to(target, target_is_directory=True)
    elif kind == 'outer-ancestor-symlink':
        alias = tmp_path / 'alias'; alias.symlink_to(tmp_path, target_is_directory=True); root = alias / root.name
    elif kind == 'hardlink': os.link(leaf, root / 'alias')
    else: leaf.unlink(); os.mkfifo(leaf)
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises((ValueError, OSError)):
        with held(root, entries): pass
    assert len(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('kind', ['leaf', 'parent', 'root', 'edit-restore'])
def test_same_bytes_swaps_and_edit_restore_are_stale(tmp_path, kind):
    root, leaf, entries = fixture(tmp_path)
    files = held(root, entries)
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises((RuntimeError, ValueError, OSError)):
        with files:
            if kind == 'leaf':
                data = leaf.read_bytes(); leaf.unlink(); leaf.write_bytes(data)
            elif kind == 'parent':
                saved = root / 'saved'; leaf.parent.rename(saved)
                leaf.parent.mkdir(); leaf.write_bytes((saved / leaf.name).read_bytes())
            elif kind == 'root':
                root.rename(tmp_path / 'saved'); leaf.parent.mkdir(parents=True); leaf.write_bytes(b'authored fixture')
            else:
                data = leaf.read_bytes(); leaf.write_bytes(b'changed'); leaf.write_bytes(data)
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): files.read(entries[0]['path'], 128)


@pytest.mark.parametrize('kind', ['extra-file', 'empty-dir', 'late-extra', 'missing', 'unknown-subtree'])
def test_exact_namespace_before_and_after(tmp_path, kind):
    root, leaf, entries = fixture(tmp_path)
    if kind == 'extra-file': (leaf.parent / 'extra').write_bytes(b'x')
    elif kind == 'empty-dir': (leaf.parent / 'empty').mkdir()
    elif kind == 'missing': leaf.unlink()
    subtrees = ('unknown',) if kind == 'unknown-subtree' else ('input',)
    with pytest.raises((ValueError, OSError, RuntimeError)):
        with held(root, entries, exact_subtrees=subtrees):
            if kind == 'late-extra': (leaf.parent / 'extra').write_bytes(b'x')


def test_unconsumed_sibling_and_empty_file_allowed(tmp_path):
    root, leaf, entries = fixture(tmp_path)
    (root / 'unconsumed').mkdir(); (root / 'unconsumed/value').write_bytes(b'other')
    leaf.write_bytes(b''); entries = [descriptor(entries[0]['path'], b'')]
    with held(root, entries, exact_subtrees=('input',)) as files:
        assert files.read(entries[0]['path'], 0) == b''
        with pytest.raises(ValueError): files.read('unconsumed/value', 128)


@pytest.mark.parametrize('deadline', [None, True, float('inf'), float('nan')])
def test_invalid_deadline(tmp_path, deadline):
    root, leaf, entries = fixture(tmp_path)
    with pytest.raises(ValueError): module().HeldCollectionFiles(root, entries, deadline)


def test_expiry_and_failed_body_close_descriptors_and_poison(tmp_path, monkeypatch):
    root, leaf, entries = fixture(tmp_path); files = held(root, entries)
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises(LookupError, match='body'):
        with files: raise LookupError('body')
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): files.recheck()
    files = held(root, entries)
    with pytest.raises(TimeoutError):
        with files: monkeypatch.setattr(module().time, 'monotonic', lambda: files.deadline + 1)
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): files.read(entries[0]['path'], 128)


def test_failed_body_still_rechecks_mutated_input(tmp_path):
    root, leaf, entries = fixture(tmp_path); files = held(root, entries)
    with pytest.raises((RuntimeError, ValueError), match='changed|differs'):
        with files:
            leaf.write_bytes(b'mutated'); raise LookupError('body')
    with pytest.raises(RuntimeError): files.recheck()


def test_caught_drift_cannot_become_success(tmp_path):
    root, leaf, entries = fixture(tmp_path); files = held(root, entries)
    with pytest.raises(RuntimeError, match='failed before context exit'):
        with files:
            leaf.write_bytes(b'mutated')
            with pytest.raises((RuntimeError, ValueError)): files.recheck()
            with pytest.raises(RuntimeError): files.read(entries[0]['path'], 128)


@pytest.mark.parametrize('defect', ['hash', 'size', 'relative-root', 'no-files'])
def test_actual_byte_binding_and_initial_failure_cleanup(tmp_path, defect):
    root, leaf, entries = fixture(tmp_path)
    if defect == 'hash': entries[0]['sha256'] = '0' * 64
    elif defect == 'size': entries[0]['size_bytes'] += 1
    elif defect == 'relative-root': root = Path('relative')
    else: entries = []
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises(ValueError):
        with held(root, entries): pass
    assert len(os.listdir('/proc/self/fd')) == before


def test_temp_sparse_runtime_stream_only_and_four_mib_read(tmp_path, monkeypatch):
    mod = module(); root = tmp_path / 'root'; root.mkdir()
    runtime = root / 'runtime-fixture'
    with runtime.open('wb') as stream:
        stream.seek(21_662_864 - 1); stream.write(b'\0')
    big_hash = hashlib.sha256()
    with runtime.open('rb') as stream:
        while block := stream.read(MiB): big_hash.update(block)
    profile = root / 'profile'; payload = b'p' * (4 * MiB); profile.write_bytes(payload)
    entries = [descriptor('profile', payload), {'path':'runtime-fixture', 'size_bytes':21_662_864,'sha256':big_hash.hexdigest()}]
    original = mod.os.read
    sizes = []
    def bounded(fd, count):
        assert 0 < count <= MiB
        sizes.append(count); return original(fd, count)
    monkeypatch.setattr(mod.os, 'read', bounded)
    with held(root, entries) as files:
        assert files.read('profile', 4 * MiB) == payload
        with pytest.raises(ValueError): files.read('runtime-fixture', 4 * MiB)
        with pytest.raises(ValueError): files.read('profile', 4 * MiB + 1)
    assert len(sizes) > 60


def test_contract_equality_without_allocating_large_fixtures(tmp_path):
    mod = module()
    entries = [dict(descriptor(str(i), b'x'), size_bytes=32 * MiB) for i in range(2)]
    assert mod.HeldCollectionFiles(tmp_path, entries, time.monotonic() + 30)
    entries = [descriptor(f'{i:04d}', b'') for i in range(512)]
    assert mod.HeldCollectionFiles(tmp_path, entries, time.monotonic() + 30)


def test_import_is_stdlib_only():
    result = subprocess.run([sys.executable,'-c',f'import sys; import {NAME}; assert not {{"torch","mujoco","numpy","palimpsest.engine"}} & set(sys.modules)'],capture_output=True,text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('cap', [True, 1.0, -1, None, 4 * MiB + 1])
def test_small_read_cap_requires_exact_bounded_integer(tmp_path, cap):
    root, leaf, entries = fixture(tmp_path)
    with held(root, entries) as files:
        with pytest.raises(ValueError): files.read(entries[0]['path'], cap)


def test_edit_restore_during_copy_is_refused_and_poisoned(tmp_path, monkeypatch):
    mod = module(); root, leaf, entries = fixture(tmp_path); files = held(root, entries)
    data = leaf.read_bytes(); original = mod.os.read
    count = 0
    def changing(fd, size):
        nonlocal count
        block = original(fd, size)
        count += 1
        # Guard hash reads one block plus EOF; the third read copies the bytes.
        if count == 3:
            leaf.write_bytes(b'changed'); leaf.write_bytes(data)
        return block
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises(RuntimeError):
        with files:
            monkeypatch.setattr(mod.os, 'read', changing)
            files.read(entries[0]['path'], 128)
    assert count >= 3
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): files.recheck()


def test_extra_selected_directory_is_not_opened(tmp_path, monkeypatch):
    mod = module(); root, leaf, entries = fixture(tmp_path)
    (leaf.parent / 'unregistered').mkdir()
    original = mod.os.open
    def guarded(path, flags, *args, **kwargs):
        assert path != 'unregistered', 'Unexpected selected directory was opened'
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(mod.os, 'open', guarded)
    with pytest.raises(ValueError, match='unregistered'):
        with held(root, entries, exact_subtrees=('input',)): pass


def test_partial_open_failure_closes_already_held_files(tmp_path):
    root, leaf, entries = fixture(tmp_path)
    entries.append(descriptor('input/z-missing', b'x'))
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises(FileNotFoundError):
        with held(root, entries): pass
    assert len(os.listdir('/proc/self/fd')) == before
