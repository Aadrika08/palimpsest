"""Descriptor custody on temporary authored files; no model/native evidence."""
import hashlib
import importlib
import importlib.util
import os
from pathlib import Path
import time

import pytest

NAME = 'scripts.memory_family_replay_custody_v4'
MiB = 1024 ** 2


def custody():
    assert importlib.util.find_spec(NAME) is not None, 'HeldReplayFiles API is missing'
    module = importlib.import_module(NAME)
    assert callable(getattr(module, 'HeldReplayFiles', None)), 'HeldReplayFiles API is missing'
    return module


def descriptor(path, payload):
    return {'path': path, 'size_bytes': len(payload), 'sha256': hashlib.sha256(payload).hexdigest()}


def sample(tmp_path):
    root = tmp_path / 'root'
    leaf = root / 'runs/run-a/recording/value file.txt'
    leaf.parent.mkdir(parents=True)
    leaf.write_bytes(b'authored fixture')
    return root, leaf, [descriptor(leaf.relative_to(root).as_posix(), leaf.read_bytes())]


def open_files(root, entries, **extra):
    return custody().HeldReplayFiles(root, entries, time.monotonic() + 30, **extra)


def test_api_missing_red_and_readonly_success(tmp_path):
    root, leaf, entries = sample(tmp_path)
    before = leaf.stat()
    with open_files(root, entries, exact_subtrees=('runs/run-a',)) as held:
        assert held.read(entries[0]['path'], 128) == b'authored fixture'
        assert held.path(entries[0]['path']) == leaf
        assert Path(held.fd_path(entries[0]['path'])).read_bytes() == b'authored fixture'
        assert held.recheck() is None
    assert leaf.stat() == before
    for operation in (lambda: held.read(entries[0]['path'], 128),
                      lambda: held.path(entries[0]['path']),
                      lambda: held.fd_path(entries[0]['path']), held.recheck):
        with pytest.raises(RuntimeError): operation()
    with pytest.raises(RuntimeError):
        with held: pass


@pytest.mark.parametrize('name', ['../controls/x', '/absolute', 'a//b', 'a/./b', 'a/../b', 'a\\b', '', 'a/', 'a\x00b'])
def test_unsafe_relative_names_refuse_before_open(tmp_path, name):
    root, leaf, entries = sample(tmp_path)
    entries[0]['path'] = name
    with pytest.raises((ValueError, OSError)):
        with open_files(root, entries): pass


@pytest.mark.parametrize('defect', ['digest', 'size-bool', 'size-float', 'negative', 'over-file', 'unknown', 'duplicate', 'unsorted', 'too-many', 'aggregate'])
def test_bad_contract_bounds_and_order(tmp_path, defect):
    root, leaf, entries = sample(tmp_path)
    if defect == 'digest': entries[0]['sha256'] = 'Z' * 64
    elif defect == 'size-bool': entries[0]['size_bytes'] = True
    elif defect == 'size-float': entries[0]['size_bytes'] = 1.0
    elif defect == 'negative': entries[0]['size_bytes'] = -1
    elif defect == 'over-file': entries[0]['size_bytes'] = 1024 * MiB + 1
    elif defect == 'unknown': entries[0]['ignored'] = True
    elif defect == 'duplicate': entries = entries * 2
    elif defect == 'unsorted': entries = [descriptor('z', b'x'), descriptor('a', b'x')]
    elif defect == 'too-many': entries = [descriptor(f'{i:04d}', b'x') for i in range(513)]
    elif defect == 'aggregate': entries = [dict(descriptor(str(i), b'x'), size_bytes=1024 * MiB) for i in range(3)]
    with pytest.raises(ValueError):
        with open_files(root, entries): pass


@pytest.mark.parametrize('defect', ['missing-cap', 'over-cap', 'cap-bool', 'digest'])
def test_unknown_size_requires_registered_small_cap(tmp_path, defect):
    root, leaf, entries = sample(tmp_path)
    entries[0]['size_bytes'] = None
    if defect != 'missing-cap': entries[0]['max_bytes'] = MiB + 1 if defect == 'over-cap' else True if defect == 'cap-bool' else MiB
    if defect == 'digest': entries[0]['sha256'] = None
    with pytest.raises(ValueError):
        with open_files(root, entries): pass


def test_unknown_metadata_size_is_hash_bounded_and_empty_files_allowed(tmp_path):
    root, leaf, entries = sample(tmp_path)
    entries[0].update(size_bytes=None, max_bytes=MiB)
    with open_files(root, entries) as held:
        assert held.read(entries[0]['path'], MiB) == leaf.read_bytes()
    leaf.write_bytes(b'')
    entries = [descriptor(entries[0]['path'], b'')]
    with open_files(root, entries) as held:
        assert held.read(entries[0]['path'], 0) == b''


@pytest.mark.parametrize('kind', ['leaf-symlink', 'parent-symlink', 'root-symlink', 'hardlink', 'fifo'])
def test_alias_or_special_file_refusal(tmp_path, kind):
    root, leaf, entries = sample(tmp_path)
    if kind == 'leaf-symlink':
        target = root / 'target'; leaf.rename(target); leaf.symlink_to(target)
    elif kind == 'parent-symlink':
        target = root / 'target'; leaf.parent.rename(target); leaf.parent.symlink_to(target, target_is_directory=True)
    elif kind == 'root-symlink':
        target = tmp_path / 'target'; root.rename(target); root.symlink_to(target, target_is_directory=True)
    elif kind == 'hardlink': os.link(leaf, root / 'alias')
    else: leaf.unlink(); os.mkfifo(leaf)
    with pytest.raises((ValueError, OSError)):
        with open_files(root, entries): pass


@pytest.mark.parametrize('kind', ['leaf', 'parent', 'root', 'edit-restore'])
def test_same_bytes_replacement_or_restored_edit_is_detected(tmp_path, kind):
    root, leaf, entries = sample(tmp_path)
    held = open_files(root, entries)
    with pytest.raises((ValueError, RuntimeError, OSError)):
        with held:
            if kind == 'leaf':
                data = leaf.read_bytes(); leaf.unlink(); leaf.write_bytes(data)
            elif kind == 'parent':
                old = leaf.parent.with_name('saved'); leaf.parent.rename(old)
                leaf.parent.mkdir(); leaf.write_bytes((old / leaf.name).read_bytes())
            elif kind == 'root':
                old = root.with_name('saved'); root.rename(old)
                leaf.parent.mkdir(parents=True); leaf.write_bytes(b'authored fixture')
            else:
                data = leaf.read_bytes(); leaf.write_bytes(b'changed'); leaf.write_bytes(data)
    with pytest.raises(RuntimeError): held.read(entries[0]['path'], 128)


@pytest.mark.parametrize('kind', ['extra-file', 'empty-dir', 'late-extra', 'unknown-subtree'])
def test_exact_selected_namespace(tmp_path, kind):
    root, leaf, entries = sample(tmp_path)
    if kind == 'extra-file': (leaf.parent / 'extra').write_bytes(b'x')
    elif kind == 'empty-dir': (leaf.parent / 'empty').mkdir()
    subtrees = ('runs/unknown',) if kind == 'unknown-subtree' else ('runs/run-a',)
    with pytest.raises((ValueError, OSError, RuntimeError)):
        with open_files(root, entries, exact_subtrees=subtrees):
            if kind == 'late-extra': (leaf.parent / 'extra').write_bytes(b'x')


def test_other_run_allowed_and_read_cap_refuses(tmp_path):
    root, leaf, entries = sample(tmp_path)
    other = root / 'runs/run-b'; other.mkdir(); (other / 'ignored').write_bytes(b'other')
    with open_files(root, entries, exact_subtrees=('runs/run-a',)) as held:
        with pytest.raises(ValueError): held.read(entries[0]['path'], 2)
        with pytest.raises(ValueError): held.path('runs/run-b/ignored')


def test_context_failure_rechecks_closes_and_expiry_poison(tmp_path, monkeypatch):
    module = custody(); root, leaf, entries = sample(tmp_path)
    held = open_files(root, entries)
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises(RuntimeError, match='body'):
        with held: raise RuntimeError('body')
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): held.recheck()
    held = open_files(root, entries)
    with pytest.raises(TimeoutError):
        with held:
            monkeypatch.setattr(module.time, 'monotonic', lambda: held.deadline + 1)
    assert len(os.listdir('/proc/self/fd')) == before
    with pytest.raises(RuntimeError): held.fd_path(entries[0]['path'])


def test_failed_open_closes_every_descriptor(tmp_path):
    root, leaf, entries = sample(tmp_path)
    entries.append(descriptor('runs/run-a/recording/z-missing', b'x'))
    before = len(os.listdir('/proc/self/fd'))
    with pytest.raises(FileNotFoundError):
        with open_files(root, entries): pass
    assert len(os.listdir('/proc/self/fd')) == before
