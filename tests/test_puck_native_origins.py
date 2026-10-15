"""Authored Linux/glibc origin probes; no installed model/runtime qualification."""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


class _Provider:
    def __init__(self):
        self._holders = [SimpleNamespace(_files={
            'package/native.so': (73, 71, 'native.so', (17, 23, 'remaining-identity')),
        })]
        self.checked = []
        self.error = None

    def _target_recheck(self, holder, path):
        assert holder is self._holders[0]
        assert path == 'package/native.so'
        self.checked.append(path)
        if self.error is not None:
            raise self.error


_ROW = {'root_index': 0, 'path': 'package/native.so'}


def _api():
    return importlib.import_module('palimpsest.puck_native_origins')


@pytest.mark.parametrize(('policy', 'expected'), [
    ('exact-file-fd-v1', '/proc/self/fd/73'),
    ('held-directory-observed-v1', '/proc/self/fd/71/native.so'),
])
def test_native_path_uses_selected_held_descriptor_and_checks_target(policy, expected):
    provider = _Provider()
    assert _api().native_load_path(provider, _ROW, policy) == expected
    assert provider.checked == ['package/native.so']


@pytest.mark.parametrize('operation', ['native_load_path', 'require_native_target'])
def test_unknown_policy_is_rejected_before_using_provider(operation):
    arguments = (object(), _ROW, 'physical-path-fallback')
    if operation == 'require_native_target':
        arguments += ({},)
    with pytest.raises(ValueError, match='policy'):
        getattr(_api(), operation)(*arguments)


def test_directory_policy_requires_target_device_inode_observation():
    provider = _Provider()
    # A similarly named image with the wrong inode cannot qualify the target.
    with pytest.raises(RuntimeError, match='[Nn]ative.*[Tt]arget|[Tt]arget.*[Ii]mage'):
        _api().require_native_target(provider, _ROW, 'held-directory-observed-v1',
                                     {(17, 24): {'/registered/package/native.so'}})


@pytest.mark.parametrize('policy', ['exact-file-fd-v1', 'held-directory-observed-v1'])
def test_observed_target_is_rechecked_and_guard_errors_propagate(policy):
    provider = _Provider()
    provider.error = RuntimeError('simulated target edge changed')
    with pytest.raises(RuntimeError, match='simulated target edge changed'):
        _api().require_native_target(provider, _ROW, policy,
                                     {(17, 23): {'/any/observed/path'}})
    assert provider.checked == ['package/native.so']


@pytest.mark.parametrize('policy', ['exact-file-fd-v1', 'held-directory-observed-v1'])
def test_path_guard_failure_prevents_returning_load_path(policy):
    provider = _Provider()
    provider.error = RuntimeError('simulated target edge changed')
    with pytest.raises(RuntimeError, match='simulated target edge changed'):
        _api().native_load_path(provider, _ROW, policy)


def test_exact_file_policy_preserves_absent_map_compatibility():
    provider = _Provider()
    assert _api().require_native_target(provider, _ROW, 'exact-file-fd-v1', {}) is None
    assert provider.checked == ['package/native.so']


# Fresh processes avoid loader caches. Only these authored C images are loaded.
_CHILD = r'''
import ctypes
import json
import os
import sys
from types import SimpleNamespace
from palimpsest.puck_native_origins import native_load_path, require_native_target

fd, parent_fd = map(int, sys.argv[1:3])
policy, expected_result = sys.argv[3:5]
state = os.fstat(fd)
identity = (state.st_dev, state.st_ino)
row = {'root_index': 0, 'path': 'package/native.so'}
holder = SimpleNamespace(_files={'package/native.so': (fd, parent_fd, 'native.so', identity)})
class Provider:
    _holders = [holder]
    checks = 0
    def _target_recheck(self, actual_holder, path):
        assert actual_holder is holder and path == row['path']
        target = os.stat('native.so', dir_fd=parent_fd, follow_symlinks=False)
        held = os.fstat(fd)
        assert (target.st_dev, target.st_ino) == identity
        assert (held.st_dev, held.st_ino) == identity
        self.checks += 1
provider = Provider()
path = native_load_path(provider, row, policy)
expected_path = ('/proc/self/fd/' + str(fd) if policy == 'exact-file-fd-v1'
                 else '/proc/self/fd/' + str(parent_fd) + '/native.so')
assert path == expected_path
try:
    image = ctypes.CDLL(path)
except OSError as error:
    if expected_result != 'missing-sibling':
        raise
    assert 'libpalimpsest_origin_helper.so' in str(error), str(error)
    print(json.dumps({'missing_sibling': True, 'checks': provider.checks}))
    sys.exit(0)
assert expected_result == '47', 'strict leaf descriptor unexpectedly loaded sibling'
image.palimpsest_origin_value.restype = ctypes.c_int
assert image.palimpsest_origin_value() == 47
observed = {}
with open('/proc/self/maps', 'rb') as stream:
    for line in stream:
        fields = line.split(None, 5)
        if len(fields) < 5 or not int(fields[4]):
            continue
        major, minor = (int(value, 16) for value in fields[3].split(b':'))
        key = (os.makedev(major, minor), int(fields[4]))
        observed.setdefault(key, set()).add(os.fsdecode(fields[5].strip()) if len(fields) == 6 else '')
assert identity in observed
require_native_target(provider, row, policy, observed)
assert provider.checks == 2
print(json.dumps({'return_value': 47, 'target_mapped': True, 'device': identity[0],
                  'inode': identity[1], 'checks': provider.checks}))
'''


def _authored_images(tmp_path, origin):
    compiler = shutil.which('cc')
    if compiler is None:
        pytest.skip('authored native-origin probe requires cc')
    package = tmp_path / 'package'
    package.mkdir()
    helper_dir = package if origin == '$ORIGIN' else tmp_path / 'lib'
    helper_dir.mkdir(exist_ok=True)
    helper_source = tmp_path / 'helper.c'
    helper_source.write_text('int palimpsest_helper(void) { return 40; }\n')
    native_source = tmp_path / 'native.c'
    native_source.write_text('extern int palimpsest_helper(void);\n'
                             'int palimpsest_origin_value(void) { return palimpsest_helper() + 7; }\n')
    helper = helper_dir / 'libpalimpsest_origin_helper.so'
    native = package / 'native.so'
    subprocess.run([compiler, '-shared', '-fPIC', str(helper_source), '-o', str(helper),
                    '-Wl,-soname,libpalimpsest_origin_helper.so'],
                   check=True, capture_output=True, text=True, timeout=15)
    subprocess.run([compiler, '-shared', '-fPIC', str(native_source), '-o', str(native),
                    '-L' + str(helper_dir), '-lpalimpsest_origin_helper', '-Wl,-z,origin',
                    '-Wl,-rpath,' + origin],
                   check=True, capture_output=True, text=True, timeout=15)
    return package, native


def _load_in_child(package, native, policy, expected_result):
    parent_fd = os.open(package, os.O_RDONLY | os.O_DIRECTORY)
    try:
        leaf_fd = os.open(native, os.O_RDONLY)
        try:
            state = os.fstat(leaf_fd)
            environment = dict(os.environ)
            # Neither inherited library search paths nor injected preload images
            # may make the authored sibling probe succeed accidentally.
            environment.pop('LD_LIBRARY_PATH', None)
            environment.pop('LD_PRELOAD', None)
            result = subprocess.run([sys.executable, '-c', _CHILD, str(leaf_fd),
                                     str(parent_fd), policy, expected_result],
                                    pass_fds=(leaf_fd, parent_fd), env=environment,
                                    check=True, capture_output=True, text=True, timeout=15)
            return json.loads(result.stdout), state
        finally:
            os.close(leaf_fd)
    finally:
        os.close(parent_fd)


@pytest.mark.parametrize('origin', ['$ORIGIN', '$ORIGIN/../lib'])
def test_held_directory_origin_loads_authored_sibling_and_observes_exact_target(tmp_path, origin):
    package, native = _authored_images(tmp_path, origin)
    result, state = _load_in_child(package, native, 'held-directory-observed-v1', '47')
    assert result == {'return_value': 47, 'target_mapped': True,
                      'device': state.st_dev, 'inode': state.st_ino, 'checks': 2}


def test_exact_leaf_descriptor_keeps_strict_sibling_dependency_failure(tmp_path):
    package, native = _authored_images(tmp_path, '$ORIGIN')
    result, _ = _load_in_child(package, native, 'exact-file-fd-v1', 'missing-sibling')
    assert result == {'missing_sibling': True, 'checks': 1}
