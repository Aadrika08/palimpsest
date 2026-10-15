"""Dependency custody tests use authored temporary files, never installed models."""
import hashlib
import importlib
import importlib.util
import json
import os
import signal
import time

import pytest

NAME = 'palimpsest.puck_dependency_files'


def api():
    assert importlib.util.find_spec(NAME) is not None, 'HeldDependencyNamespace API missing'
    return importlib.import_module(NAME)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()


def setup(tmp_path):
    root = tmp_path / 'packages'; root.mkdir()
    (root / 'demo').mkdir(); (root / 'demo' / 'empty').mkdir()
    leaf = root / 'demo' / '__init__.py'; leaf.write_bytes(b'value = 7\n')
    metadata = root / 'demo.dist-info' / 'METADATA'; metadata.parent.mkdir()
    metadata.write_bytes(b'Name: demo\nVersion: 1.0\n\n')
    files = [{'path': str(p.relative_to(root)), 'size_bytes': p.stat().st_size,
              'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted(root.rglob('*')) if p.is_file()]
    registration = {'kind': 'puck-worker-dependencies-v1', 'version': 1,
        'roots': [{'root': str(root), 'kind': 'package', 'files': sorted(files, key=lambda v: v['path'])}],
        'modules': [{'name': 'demo', 'root_index': 0, 'path': 'demo/__init__.py',
                     'kind': 'python', 'is_package': True}], 'namespaces': [],
        'distributions': [{'name': 'demo', 'version': '1.0', 'root_index': 0,
                           'metadata_path': 'demo.dist-info/METADATA'}]}
    registration_path = tmp_path / 'registration.json'
    return root, leaf, registration, registration_path


def held(registration, path, raw=None):
    raw = encoded(registration) if raw is None else raw
    path.write_bytes(raw)
    return api().HeldDependencyNamespace(raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
        deadline=time.monotonic() + 30, registration_path=str(path))


def test_api_and_lifetime(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    with holder:
        assert holder.read(0, 'demo/__init__.py') == b'value = 7\n'
        receipt = holder.snapshot()
        assert receipt['file_count'] == 2
        assert not receipt['runtime_qualified'] and not receipt['collection_authorized']
        assert holder.module_records() == reg['modules']
        assert holder.distribution_records() == reg['distributions']
        assert holder.namespace_records() == []
        assert holder.retained_metadata_size_bytes() > 0
    with pytest.raises(RuntimeError): holder.recheck()


def test_external_hardlink_is_leased_not_claimed_censused(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    alias = tmp_path / 'cache-alias'; os.link(leaf, alias)
    before = signal.getsignal(signal.SIGIO)
    with held(reg, path) as holder:
        assert holder.read(0, 'demo/__init__.py') == alias.read_bytes()
        assert holder.snapshot()['external_hardlink_names_covered'] is False
    assert signal.getsignal(signal.SIGIO) == before


def test_writer_already_open_cannot_admit_timestamp_fallback(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    fd = os.open(leaf, os.O_WRONLY)
    count = len(os.listdir('/proc/self/fd'))
    try:
        with pytest.raises(OSError):
            with holder: pass
        assert len(os.listdir('/proc/self/fd')) == count
        assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL
    finally: os.close(fd)


def test_external_alias_write_attempt_breaks_lease_without_writing(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    alias = tmp_path / 'cache-alias'; os.link(leaf, alias)
    holder = held(reg, path)
    with pytest.raises(RuntimeError, match='lease'):
        with holder:
            with pytest.raises(BlockingIOError): os.open(alias, os.O_WRONLY | os.O_NONBLOCK)
            holder.recheck()
    assert leaf.read_bytes() == b'value = 7\n'
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


@pytest.mark.parametrize('kind', ['extra', 'missing', 'symlink', 'fifo', 'selected-alias'])
def test_exact_package_census_and_alias_selection(tmp_path, kind):
    root, leaf, reg, path = setup(tmp_path)
    if kind == 'extra': (root / 'extra').write_bytes(b'x')
    elif kind == 'missing': leaf.unlink()
    elif kind == 'symlink': (root / 'link').symlink_to(leaf)
    elif kind == 'fifo': os.mkfifo(root / 'fifo')
    else:
        os.link(leaf, root / 'alias')
        reg['roots'][0]['files'].insert(0, dict(reg['roots'][0]['files'][1], path='alias'))
    holder = held(reg, path)
    with pytest.raises((ValueError, OSError)):
        with holder: pass
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


@pytest.mark.parametrize('kind', ['replace', 'empty-dir', 'handler', 'owner', 'mask'])
def test_changes_poison_and_restore_signal_owner(tmp_path, kind):
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    with pytest.raises((RuntimeError, OSError)):
        with holder:
            if kind == 'replace':
                leaf.unlink(); leaf.write_bytes(b'value = 7\n')
            elif kind == 'empty-dir': (root / 'demo' / 'empty').rmdir()
            elif kind == 'handler': signal.signal(signal.SIGIO, signal.SIG_IGN)
            elif kind == 'owner':
                import fcntl
                fcntl.fcntl(holder._holders[0]._files['demo/__init__.py'][0], fcntl.F_SETOWN, 0)
            else: signal.pthread_sigmask(signal.SIG_BLOCK, {signal.SIGIO})
            holder.recheck()
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL
    assert signal.SIGIO not in signal.pthread_sigmask(signal.SIG_BLOCK, [])
    with pytest.raises(RuntimeError): holder.snapshot()


@pytest.mark.parametrize('args', [(True, 'demo/__init__.py', 100), (0, '../escape', 100),
                                   (0, 'missing.py', 100), (0, 'demo/__init__.py', True),
                                   (0, 'demo/__init__.py', 1), (0, 'demo/__init__.py', 4*1024**2+1)])
def test_invalid_public_read_poisoned_even_when_caught(tmp_path, args):
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    with pytest.raises(RuntimeError, match='failed before context exit'):
        with holder:
            with pytest.raises(ValueError): holder.read(*args)
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


@pytest.mark.parametrize('kind', ['unknown', 'boolean-version', 'stdlib', 'missing-module', 'bad-parent',
                                  'metadata-version', 'registration-pretty', 'overlap', 'root-bool'])
def test_registration_strictness_and_metadata(tmp_path, kind):
    root, leaf, reg, path = setup(tmp_path)
    if kind == 'unknown': reg['extra'] = True
    elif kind == 'boolean-version': reg['version'] = True
    elif kind == 'stdlib': reg['modules'][0]['name'] = 'json'
    elif kind == 'missing-module': reg['modules'][0]['path'] = 'absent.py'
    elif kind == 'bad-parent': reg['modules'][0]['name'] = 'absent.child'
    elif kind == 'metadata-version': reg['distributions'][0]['version'] = '2.0'
    elif kind == 'registration-pretty':
        raw = json.dumps(reg).encode()
        with pytest.raises(ValueError): held(reg, path, raw)
        return
    elif kind == 'overlap': reg['roots'].append(dict(reg['roots'][0]))
    else: reg['modules'][0]['root_index'] = True
    with pytest.raises(ValueError):
        with held(reg, path): pass
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


def test_system_image_user_writable_is_refused(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    reg['roots'][0]['kind'] = 'system_images'; reg['modules'] = []
    reg['distributions'] = []
    with pytest.raises(ValueError, match='trusted-root-owned'):
        with held(reg, path): pass


def test_registration_itself_is_leased(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    fd = os.open(path, os.O_WRONLY)
    try:
        with pytest.raises(OSError):
            with holder: pass
    finally: os.close(fd)


def test_second_owner_is_refused_without_disturbing_first(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    # Construct the second registration before first custody observes ancestors.
    other = api().HeldDependencyNamespace(encoded(reg), expected_sha256=hashlib.sha256(encoded(reg)).hexdigest(),
        deadline=time.monotonic()+30, registration_path=str(path))
    with holder:
        with pytest.raises(RuntimeError, match='fresh main-thread'):
            with other: pass
        holder.recheck()


def test_returned_maps_are_detached(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    with held(reg, path) as holder:
        holder.module_records()[0]['path'] = 'evil.py'
        holder.distribution_records()[0]['version'] = 'evil'
        assert holder.module_records() == reg['modules']
        assert holder.distribution_records() == reg['distributions']


@pytest.mark.parametrize('bound', ['metadata', 'files', 'bytes', 'census'])
def test_global_limits_cannot_admit(tmp_path, monkeypatch, bound):
    root, leaf, reg, path = setup(tmp_path)
    module = api()
    if bound == 'metadata': monkeypatch.setattr(module, 'MAX_METADATA_BYTES', 1)
    elif bound == 'files': monkeypatch.setattr(module, 'MAX_FILES', 1)
    elif bound == 'bytes': monkeypatch.setattr(module, 'MAX_TOTAL_BYTES', 1)
    else: monkeypatch.setattr(module, 'MAX_CENSUS_ENTRIES', 1)
    with pytest.raises(ValueError):
        with held(reg, path): pass
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


@pytest.mark.parametrize('deadline', [True, float('nan'), float('inf'), -1, 1000000000000])
def test_bad_absolute_deadline(tmp_path, deadline):
    root, leaf, reg, path = setup(tmp_path)
    raw = encoded(reg)
    with pytest.raises(ValueError):
        api().HeldDependencyNamespace(raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
            deadline=deadline, registration_path=str(path))


def test_module_map_parent_and_namespace(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    namespace = root / 'shared'; namespace.mkdir()
    child = namespace / 'child.py'; child.write_bytes(b'x = 2\n')
    reg['roots'][0]['files'].append({'path': 'shared/child.py', 'size_bytes': child.stat().st_size,
        'sha256': hashlib.sha256(child.read_bytes()).hexdigest()})
    reg['modules'].append({'name': 'shared.child', 'root_index': 0, 'path': 'shared/child.py',
                          'kind': 'python', 'is_package': False})
    reg['namespaces'].append({'name': 'shared', 'root_index': 0, 'path': 'shared'})
    with held(reg, path) as holder:
        assert holder.namespace_records() == reg['namespaces']
        assert holder.read(0, 'shared/child.py') == b'x = 2\n'


def test_strict_json_duplicate_and_nonfinite(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    for raw in [b'{"version":1,"version":1}', b'{"version":NaN}']:
        with pytest.raises(ValueError): held(reg, path, raw)


def test_registration_sha_mismatch_and_file_mismatch(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    raw = encoded(reg); path.write_bytes(raw)
    with pytest.raises(ValueError):
        api().HeldDependencyNamespace(raw, expected_sha256='0'*64,
            deadline=time.monotonic()+30, registration_path=str(path))
    reg['roots'][0]['files'][1]['sha256'] = '0'*64
    with pytest.raises(ValueError, match='SHA-256'):
        with held(reg, path): pass


def test_explicit_release_removes_even_private_duplicate_lease(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    duplicate = None
    with held(reg, path) as holder:
        duplicate = os.dup(holder._holders[0]._files['demo/__init__.py'][0])
    try:
        fd = os.open(leaf, os.O_WRONLY | os.O_NONBLOCK)
        os.close(fd)
    finally: os.close(duplicate)


@pytest.mark.parametrize('kind', ['leaf', 'ancestor', 'other-lease'])
def test_targeted_read_refuses_changed_consumption_or_global_break(tmp_path, kind):
    root, leaf, reg, path = setup(tmp_path)
    other_alias = tmp_path / 'other-alias'; os.link(root/'demo.dist-info/METADATA', other_alias)
    holder = held(reg, path)
    with pytest.raises(RuntimeError):
        with holder:
            if kind == 'leaf':
                leaf.unlink(); leaf.write_bytes(b'value = 7\n')
            elif kind == 'ancestor':
                leaf.parent.rename(root/'saved-demo')
            else:
                with pytest.raises(BlockingIOError): os.open(other_alias, os.O_WRONLY | os.O_NONBLOCK)
            holder.read(0, 'demo/__init__.py')
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


def test_targeted_read_checks_signal_each_hash_block(tmp_path, monkeypatch):
    root, leaf, reg, path = setup(tmp_path)
    leaf.write_bytes(b'x' * (2*1024**2))
    reg['roots'][0]['files'][1].update(size_bytes=leaf.stat().st_size,
        sha256=hashlib.sha256(leaf.read_bytes()).hexdigest())
    alias = tmp_path / 'hash-alias'; os.link(leaf, alias)
    holder = held(reg, path)
    with pytest.raises(RuntimeError, match='lease'):
        with holder:
            original_read = os.read
            calls = 0
            def read_then_break(fd, size):
                nonlocal calls
                value = original_read(fd, size); calls += 1
                if calls == 1:
                    with pytest.raises(BlockingIOError): os.open(alias, os.O_WRONLY | os.O_NONBLOCK)
                return value
            monkeypatch.setattr(os, 'read', read_then_break)
            holder.read(0, 'demo/__init__.py')
    assert calls == 1


def test_offthread_misuse_defers_cleanup_to_owner_and_cannot_nominally_close(tmp_path):
    import threading
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    baseline = len(os.listdir('/proc/self/fd'))
    errors = []
    with pytest.raises(RuntimeError, match='failed before context exit'):
        with holder:
            original_handler = signal.getsignal(signal.SIGIO)
            def misuse():
                try: holder.read(0, 'demo/__init__.py')
                except BaseException as error: errors.append(error)
            thread = threading.Thread(target=misuse); thread.start(); thread.join()
            assert len(errors) == 1 and 'original main thread' in str(errors[0])
            assert holder._deferred_cleanup
            assert signal.getsignal(signal.SIGIO) is original_handler
            assert len(os.listdir('/proc/self/fd')) > baseline
    assert len(os.listdir('/proc/self/fd')) == baseline
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL
    with held(reg, path) as fresh: assert fresh.read(0, 'demo/__init__.py') == b'value = 7\n'


def test_fork_misuse_does_not_release_parent_leases(tmp_path):
    import fcntl
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    with holder:
        pid = os.fork()
        if pid == 0:
            try:
                try: holder.read(0, 'demo/__init__.py')
                except RuntimeError:
                    valid = (holder._state == 'failed' and holder._deferred_cleanup
                        and api()._LEASE_OWNER is holder)
                    os._exit(0 if valid else 2)
                os._exit(3)
            except BaseException: os._exit(4)
        _, status = os.waitpid(pid, 0)
        assert os.waitstatus_to_exitcode(status) == 0
        assert fcntl.fcntl(holder._holders[0]._files['demo/__init__.py'][0], fcntl.F_GETLEASE) == fcntl.F_RDLCK
        holder.recheck()


def test_file_descriptor_depth_bound(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    reg['roots'][0]['files'][1]['path'] = '/'.join(['deep']*33)
    with pytest.raises(ValueError, match='depth'):
        held(reg, path)


def test_caught_active_reentry_poison_cannot_close_successfully(tmp_path):
    root, leaf, reg, path = setup(tmp_path)
    holder = held(reg, path)
    holder.__enter__()
    with pytest.raises(RuntimeError, match='once'): holder.__enter__()
    with pytest.raises(RuntimeError, match='failed|closed'): holder.read(0, 'demo/__init__.py')
    with pytest.raises(RuntimeError): holder.__exit__(None, None, None)
    assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL
