"""Versioned tmpfs admission uses authored forests and the real held worker."""
from contextlib import contextmanager
import copy
import json
import os
from pathlib import Path
import signal
import tempfile

import pytest

from test_puck_dependency_files import held, setup
from test_puck_worker_bootstrap import ROOT
from test_puck_worker_dependencies import dependency_fixture

POLICY = 'tmpfs-raw-dev-inode-v1'


def v3(reg, root=None):
    reg.update(kind='puck-worker-dependencies-v3', version=3, native_identity=POLICY,
        import_profile={'exports':[], 'module_changes':[], 'native_origins':[]})


@contextmanager
def authored(directory='/tmp'):
    with tempfile.TemporaryDirectory(prefix='palimpsest-tmpfs-deps-', dir=directory) as name:
        yield Path(name)


def test_v3_admits_tmpfs_forest_and_records_explicit_policy():
    with authored() as base:
        root, leaf, reg, path = setup(base)
        v3(reg)
        with held(reg, path) as holder:
            assert holder.read(0, 'demo/__init__.py') == b'value = 7\n'
            receipt = holder.snapshot()
            assert receipt['native_identity'] == POLICY
            assert receipt['protection_modes'] == ['linux_read_lease']
            assert receipt['runtime_qualified'] is receipt['executable'] is False
            assert receipt['collection_authorized'] is False


def test_v3_refuses_persistent_files_before_caller_entry():
    with authored(ROOT/'runs') as base:
        root, leaf, reg, path = setup(base)
        v3(reg)
        holder = held(reg, path)
        with pytest.raises(ValueError, match='tmpfs'):
            with holder:
                pytest.fail('unsupported dependency filesystem reached entry')
        assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL
        with pytest.raises(RuntimeError): holder.read(0, 'demo/__init__.py')


@pytest.mark.parametrize('defect', ['policy', 'missing-policy', 'extra', 'system-images', 'profile'])
def test_v3_rejects_invalid_schema_before_payload_io(defect):
    with authored() as base:
        root, leaf, reg, path = setup(base)
        v3(reg)
        if defect == 'policy': reg['native_identity'] = 'normalize-btrfs'
        elif defect == 'missing-policy': del reg['native_identity']
        elif defect == 'extra': reg['permission_fallback'] = True
        elif defect == 'system-images': reg['roots'][0]['kind'] = 'system_images'
        else: reg['import_profile']['unknown'] = []
        leaf.unlink()
        with pytest.raises(ValueError): held(reg, path)


@pytest.mark.parametrize('version', [1, 2])
def test_legacy_schemas_and_receipts_do_not_acquire_new_policy(version):
    with authored() as base:
        root, leaf, reg, path = setup(base)
        if version == 2:
            reg.update(kind='puck-worker-dependencies-v2', version=2,
                import_profile={'exports':[], 'module_changes':[], 'native_origins':[]})
        with held(reg, path) as holder:
            assert 'native_identity' not in holder.snapshot()
        reg['native_identity'] = POLICY
        with pytest.raises(ValueError): held(reg, path)


def test_every_leaf_is_checked_and_late_refusal_releases_all_leases(monkeypatch):
    from palimpsest import puck_native_identity
    original = puck_native_identity.require_tmpfs_descriptor
    checked = []
    def check(fd):
        identity = original(fd)
        checked.append(identity)
        if len(checked) == 2: raise OSError(1, 'authored fstatfs permission refusal')
        return identity
    monkeypatch.setattr(puck_native_identity, 'require_tmpfs_descriptor', check)
    with authored() as base:
        root, leaf, reg, path = setup(base)
        v3(reg)
        holder = held(reg, path)
        with pytest.raises(OSError, match='permission refusal'):
            with holder: pytest.fail('late leaf failure reached entry')
        assert len(checked) == 2
        assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL
        # A writable open proves no stale read lease remains on either leaf.
        for row in reg['roots'][0]['files']:
            fd = os.open(root/row['path'], os.O_WRONLY | os.O_NONBLOCK)
            os.close(fd)
        with pytest.raises(RuntimeError): holder.recheck()


def test_mixed_tmpfs_and_persistent_roots_refuse_without_success():
    with authored() as base, authored(ROOT/'runs') as persistent:
        root, leaf, reg, path = setup(base)
        other, _, other_reg, _ = setup(persistent)
        v3(reg)
        reg['roots'].append(copy.deepcopy(other_reg['roots'][0]))
        with pytest.raises(ValueError, match='tmpfs'):
            with held(reg, path): pytest.fail('persistent second root admitted')
        assert signal.getsignal(signal.SIGIO) == signal.SIG_DFL


def test_v3_complete_worker_preserves_raw_native_target_check():
    with authored() as base:
        result, package = dependency_fixture(base,
            'from fixture_dep import _native\nreturn {"answer":_native.answer()}',
            native=True, mutate=v3)
        assert result.returncode == 0, result.stderr
        receipt = json.loads(result.stdout)
        assert receipt['entry_result'] == {'answer':47}
        assert receipt['dependencies']['native_identity'] == POLICY
        assert receipt['dependencies']['images']['held_file_images']
        assert receipt['runtime_qualified'] is receipt['native_authorized'] is False


def test_v3_complete_worker_refuses_btrfs_before_python_dependency_exec():
    def mark(reg, root):
        v3(reg)
        leaf = root/'fixture_dep/__init__.py'
        leaf.write_text('raise AssertionError("DEPENDENCY_EXECUTED")\n')
        from test_puck_worker_bootstrap import descriptor
        reg['roots'][0]['files'] = [descriptor(root/row['path'], row['path'])
            for row in reg['roots'][0]['files']]
    with authored(ROOT/'runs') as base:
        result, _ = dependency_fixture(base, 'import fixture_dep\nreturn {}', mutate=mark)
        assert result.returncode != 0
        assert 'tmpfs' in result.stderr, result.stderr
        assert 'DEPENDENCY_EXECUTED' not in result.stderr
        assert result.stdout == ''
