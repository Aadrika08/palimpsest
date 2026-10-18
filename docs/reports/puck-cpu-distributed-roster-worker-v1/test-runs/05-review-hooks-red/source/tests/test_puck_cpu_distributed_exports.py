"""Authored three-child metadata fixtures; no installed numerical imports."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/characterize_puck_runtime_imports.py'
NAMES = tuple('torch._C.' + name for name in (
    '_distributed_autograd', '_distributed_c10d', '_distributed_rpc'))
VERSIONS = dict(numpy='2.2.5', torch='2.9.0+cpu',
                torchvision='0.24.0+cpu', mujoco='3.3.6')


def api():
    spec = importlib.util.spec_from_file_location('distributed_worker_fixture', SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def capture(module, cache, expected):
    function = vars(module).get('describe_distributed_exports')
    assert callable(function), 'Fixed distributed terminal metadata projection is missing'
    return function(cache, expected)


def authored_cache():
    torch = types.ModuleType('torch')
    native = types.ModuleType('torch._C')
    torch._C = native
    cache = {'torch': torch, 'torch._C': native}
    expected = {}
    for name in NAMES:
        child = types.ModuleType(name)
        child.function = lambda: (_ for _ in ()).throw(AssertionError('called member'))
        child.builtin = len
        child.module = types.ModuleType('authored.delegate')
        child.Class = type('AuthoredClass', (), {})
        child.data = 17
        setattr(native, name.rsplit('.', 1)[1], child)
        cache[name] = child
        expected[name] = ['Class', 'builtin', 'function', 'module']
    return cache, expected


def test_capture_retains_exact_three_raw_dispatch_rosters_and_comparisons():
    module = api()
    cache, expected = authored_cache()
    projection, seal = capture(module, cache, expected)
    assert projection['kind'] == 'puck-cpu-distributed-exports-v1'
    assert projection['capture_point'] == 'after_four_fixed_imports'
    assert projection['stable'] is False
    assert projection['profile_accepted'] is projection['runtime_qualified'] is False
    assert [row['name'] for row in projection['modules']] == list(NAMES)
    for row in projection['modules']:
        assert row['delegate_attributes'] == expected[row['name']]
        assert row['raw_attribute_identity'] is row['cache_identity'] is True
        assert row['metadata']['name'] == row['name']
        assert row['comparison'] == dict(expected=expected[row['name']], missing=[], extra=[], matches=True)
    assert module.recheck_distributed_exports(cache, seal) is None


def test_comparison_retains_complete_missing_and_extra_sets_without_acceptance():
    module = api()
    cache, expected = authored_cache()
    expected[NAMES[0]] = ['Class', 'missing']
    projection, seal = capture(module, cache, expected)
    assert projection['modules'][0]['comparison'] == dict(
        expected=['Class', 'missing'], missing=['missing'],
        extra=['builtin', 'function', 'module'], matches=False)
    assert projection['profile_accepted'] is False
    module.recheck_distributed_exports(cache, seal)


def test_reader_never_calls_object_class_property_or_loader_hooks():
    module = api()
    cache, expected = authored_cache()

    class DataTrap:
        @property
        def __class__(self):
            raise AssertionError('data __class__ hook invoked')

    class LoaderMeta(type):
        def __getattribute__(cls, name):
            raise AssertionError('loader metaclass hook invoked: ' + name)

    class Loader(metaclass=LoaderMeta):
        def __getattribute__(self, name):
            raise AssertionError('loader instance hook invoked: ' + name)

        def __eq__(self, other):
            raise AssertionError('loader equality invoked')

    cache[NAMES[0]].data = DataTrap()
    cache[NAMES[0]].__loader__ = Loader()
    projection, seal = capture(module, cache, expected)
    assert projection['modules'][0]['metadata']['loader_type'].endswith('.Loader')
    module.recheck_distributed_exports(cache, seal)


def test_bad_raw_name_is_rejected_before_value_equality_hooks():
    module = api()
    cache, expected = authored_cache()

    class EqualityTrap:
        def __eq__(self, other):
            raise AssertionError('raw name equality hook invoked')

    vars(cache[NAMES[0]])['__name__'] = EqualityTrap()
    with pytest.raises(ValueError):
        capture(module, cache, expected)


@pytest.mark.parametrize('target', ['cache', 'torch', 'native', 'spec', 'expected'])
def test_control_dictionary_collisions_never_invoke_key_equality(target):
    module = api()
    cache, expected = authored_cache()
    if target == 'cache':
        dictionary, key = cache, 'torch'
    elif target == 'torch':
        dictionary, key = vars(cache['torch']), '_C'
    elif target == 'native':
        dictionary, key = vars(cache['torch._C']), '_distributed_autograd'
    elif target == 'expected':
        dictionary, key = expected, NAMES[0]
    else:
        spec = importlib.util.spec_from_loader(NAMES[0], None)
        cache[NAMES[0]].__spec__ = spec
        dictionary, key = vars(spec), 'loader'

    class Collision:
        def __hash__(self):
            return hash(key)

        def __eq__(self, other):
            raise AssertionError('control dictionary key hook invoked')

    value = dictionary.pop(key)
    dictionary[Collision()] = value
    with pytest.raises(ValueError):
        capture(module, cache, expected)


def test_spec_dictionary_subclass_is_rejected_without_get_override():
    module = api()
    cache, expected = authored_cache()
    spec = importlib.util.spec_from_loader(NAMES[0], None)

    class Dictionary(dict):
        def get(self, key, default=None):
            raise AssertionError('spec dictionary get hook invoked')

    spec.__dict__ = Dictionary(vars(spec))
    cache[NAMES[0]].__spec__ = spec
    with pytest.raises(ValueError):
        capture(module, cache, expected)


@pytest.mark.parametrize('defect', [
    'missing-child', 'missing-raw-child', 'cache-raw-mismatch', 'root-cache-mismatch',
    'nonmodule-child', 'module-subclass', 'wrong-name', 'custom-spec', 'metadata-text',
    'bad-package', 'bad-key', 'long-key', 'dict-limit', 'bad-path', 'path-limit',
])
def test_capture_refuses_incomplete_or_unbounded_raw_metadata(defect):
    module = api()
    cache, expected = authored_cache()
    child = cache[NAMES[0]]
    if defect == 'missing-child':
        del cache[NAMES[0]]
    elif defect == 'missing-raw-child':
        del cache['torch._C']._distributed_autograd
    elif defect == 'cache-raw-mismatch':
        cache[NAMES[0]] = types.ModuleType(NAMES[0])
    elif defect == 'root-cache-mismatch':
        cache['torch']._C = types.ModuleType('torch._C')
    elif defect == 'nonmodule-child':
        cache[NAMES[0]] = cache['torch._C']._distributed_autograd = object()
    elif defect == 'module-subclass':
        class Proxy(types.ModuleType):
            def __getattribute__(self, key):
                raise AssertionError('proxy hook called')
        cache[NAMES[0]] = cache['torch._C']._distributed_autograd = Proxy(NAMES[0])
    elif defect == 'wrong-name':
        child.__name__ = 'authored.foreign'
    elif defect == 'custom-spec':
        child.__spec__ = object()
    elif defect == 'metadata-text':
        child.__file__ = 'x' * 4097
    elif defect == 'bad-package':
        child.__package__ = object()
    elif defect == 'bad-key':
        vars(child)[17] = object()
    elif defect == 'long-key':
        vars(child)['x' * 513] = object()
    elif defect == 'dict-limit':
        vars(child).update({f'data{i}': i for i in range(4097)})
    elif defect == 'bad-path':
        child.__path__ = object()
    else:
        child.__path__ = ['x'] * 129
    with pytest.raises(ValueError):
        capture(module, cache, expected)


@pytest.mark.parametrize('defect', [
    'missing', 'extra', 'not-dict', 'tuple', 'empty', 'duplicate', 'unsorted',
    'nontext', 'subclass', 'nul', 'long', 'too-many',
])
def test_expected_sets_are_exact_bounded_controls_before_capture(defect):
    module = api()
    cache, expected = authored_cache()
    if defect == 'missing':
        del expected[NAMES[0]]
    elif defect == 'extra':
        expected['authored.foreign'] = ['member']
    elif defect == 'not-dict':
        expected = []
    elif defect == 'tuple':
        expected[NAMES[0]] = ('member',)
    elif defect == 'empty':
        expected[NAMES[0]] = []
    elif defect == 'duplicate':
        expected[NAMES[0]] = ['member', 'member']
    elif defect == 'unsorted':
        expected[NAMES[0]] = ['z', 'a']
    elif defect == 'nontext':
        expected[NAMES[0]] = [17]
    elif defect == 'subclass':
        class Text(str):
            pass
        expected[NAMES[0]] = [Text('member')]
    elif defect == 'nul':
        expected[NAMES[0]] = ['x\0y']
    elif defect == 'long':
        expected[NAMES[0]] = ['x' * 513]
    else:
        expected[NAMES[0]] = sorted(f'm{i}' for i in range(4097))
    with pytest.raises(ValueError):
        capture(module, cache, expected)


@pytest.mark.parametrize('defect', [
    'cache-rebind', 'native-rebind', 'delegate-rebind', 'delegate-add', 'delegate-remove',
    'metadata-file', 'metadata-loader', 'metadata-spec', 'spec-name', 'spec-loader',
    'spec-origin', 'spec-search-path', 'module-path',
])
def test_terminal_recheck_refuses_identity_metadata_or_dispatch_changes(defect):
    module = api()
    cache, expected = authored_cache()
    child = cache[NAMES[0]]
    spec = importlib.util.spec_from_loader(NAMES[0], None, origin='/authored/original')
    child.__spec__ = spec
    projection, seal = capture(module, cache, expected)
    if defect == 'cache-rebind':
        cache[NAMES[0]] = types.ModuleType(NAMES[0])
    elif defect == 'native-rebind':
        cache['torch']._C = cache['torch._C'] = types.ModuleType('torch._C')
    elif defect == 'delegate-rebind':
        child.function = lambda: None
    elif defect == 'delegate-add':
        child.new = abs
    elif defect == 'delegate-remove':
        del child.function
    elif defect == 'metadata-file':
        child.__file__ = '/authored/new'
    elif defect == 'metadata-loader':
        child.__loader__ = object()
    elif defect == 'metadata-spec':
        child.__spec__ = importlib.util.spec_from_loader(NAMES[0], None, origin='/authored/original')
    elif defect == 'spec-name':
        spec.name = 'authored.foreign'
    elif defect == 'spec-loader':
        spec.loader = object()
    elif defect == 'spec-origin':
        spec.origin = '/authored/changed'
    elif defect == 'spec-search-path':
        spec.submodule_search_locations = ['/authored/new']
    else:
        child.__path__ = ['/authored/new']
    with pytest.raises(ValueError):
        module.recheck_distributed_exports(cache, seal)
    assert projection['stable'] is False


def test_projection_byte_ceiling_refuses_before_partial_success(monkeypatch):
    module = api()
    cache, expected = authored_cache()
    assert hasattr(module, 'DISTRIBUTED_REPORT_BYTES'), 'Projection byte budget is missing'
    monkeypatch.setattr(module, 'DISTRIBUTED_REPORT_BYTES', 64)
    with pytest.raises(ValueError, match='projection'):
        capture(module, cache, expected)


def test_observe_rechecks_after_independent_cache_observation(monkeypatch):
    module = api()
    cache, expected = authored_cache()
    for name, version in VERSIONS.items():
        cache.setdefault(name, types.ModuleType(name)).__version__ = version
    monkeypatch.setattr(module, 'sys', types.SimpleNamespace(
        path=[], modules=cache, version='authored', executable='/authored/python',
        pycache_prefix='/authored/cache'))
    monkeypatch.setattr(module, 'importlib', types.SimpleNamespace(import_module=cache.__getitem__))
    monkeypatch.setattr(module, 'mapped_images', lambda: dict(images=[]))
    original = module.describe_cache

    def mutate_after_capture(values):
        values[NAMES[0]].function = abs
        return original(values)

    monkeypatch.setattr(module, 'describe_cache', mutate_after_capture)
    request = dict(version=3, expected_versions=VERSIONS,
        environment=dict(os.environ), site_root='/authored/site',
        pycache_prefix='/authored/cache', distributed_expected=expected)
    report = module.observe(request, '0' * 64)
    assert report['versions'] == VERSIONS
    assert report['status'] == 'failed'
    assert report['distributed_exports']['stable'] is False
    assert any(row['stage'] == 'distributed_exports_recheck' for row in report['observation_errors'])


def launch(tmp_path, defect=None, version=3):
    module = api()
    site = tmp_path / 'site'
    site.mkdir()
    output = tmp_path / 'output'
    output.mkdir()
    prefix = tmp_path / 'pycache'
    prefix.mkdir(mode=0o700)
    marker = tmp_path / 'imports-started'
    expected = {name: ['call', 'late'] for name in NAMES}
    for name, value in VERSIONS.items():
        body = '__version__=' + repr(value) + '\n'
        if name == 'numpy':
            body += 'open(' + repr(str(marker)) + ',"w").write("started")\n'
        if name == 'torch':
            body += ('import sys,types\n_C=types.ModuleType("torch._C")\n'
                     'sys.modules["torch._C"]=_C\n'
                     'for name in ' + repr(NAMES) + ':\n'
                     ' child=types.ModuleType(name)\n'
                     ' def forbidden(): raise RuntimeError("member invoked")\n'
                     ' child.call=forbidden\n'
                     ' setattr(_C,name.rsplit(".",1)[1],child)\n'
                     ' sys.modules[name]=child\n')
        if name == 'torchvision' and defect == 'version':
            body += '__version__="wrong"\n'
        if name == 'mujoco':
            body += ('import sys\nfor name in ' + repr(NAMES) + ':\n'
                     ' sys.modules[name].late=abs\n')
            if defect == 'missing-child':
                body += 'del sys.modules[' + repr(NAMES[0]) + ']\n'
        package = site / name
        package.mkdir()
        (package / '__init__.py').write_text(body)
    if defect == 'comparison':
        expected[NAMES[0]] = ['call', 'missing']
    if defect == 'bad-expected':
        expected['authored.foreign'] = ['call']
    request = dict(kind='puck-runtime-import-characterization-v' + str(version),
                   version=version, site_root=str(site), output_root=str(output),
                   environment=dict(PYTHONDONTWRITEBYTECODE='1', LC_ALL='C.UTF-8', LANG='C.UTF-8'),
                   expected_versions=VERSIONS, pycache_prefix=str(prefix),
                   distributed_expected=expected)
    path = tmp_path / 'request.json'
    raw = module.canonical(request)
    path.write_bytes(raw)
    result = subprocess.run([
        sys.executable, '-I', '-B', '-S', '-X', 'pycache_prefix=' + str(prefix),
        str(SCRIPT), str(path), module.sha(raw)], env=request['environment'],
        capture_output=True, text=True, timeout=15)
    report = json.loads((output / 'imports.json').read_bytes()) if (output / 'imports.json').exists() else None
    return result, report, marker


@pytest.mark.parametrize('defect', [None, 'comparison'])
def test_new_isolated_worker_captures_only_after_four_imports_without_authority(tmp_path, defect):
    result, report, marker = launch(tmp_path, defect)
    assert result.returncode == 0, result.stderr
    assert marker.is_file()
    assert report['kind'] == 'puck-runtime-import-characterization-result-v4'
    assert report['version'] == 4 and report['profile'] == 'cpu-distributed-terminal-v1'
    assert report['versions'] == VERSIONS
    assert [row['name'] for row in report['imports']] == list(VERSIONS)
    projection = report['distributed_exports']
    assert projection['stable'] is True
    assert projection['profile_accepted'] is report['runtime_qualified'] is False
    assert all(row['delegate_attributes'] == ['call', 'late'] for row in projection['modules'])
    assert projection['modules'][0]['comparison']['matches'] is (defect is None)


@pytest.mark.parametrize('defect', ['missing-child', 'version'])
def test_new_worker_preserves_import_or_metadata_failure_without_retry(tmp_path, defect):
    result, report, marker = launch(tmp_path, defect)
    assert result.returncode == 1
    assert marker.is_file() and report['status'] == 'failed'
    assert report['distributed_exports'] is None
    if defect == 'missing-child':
        assert report['versions'] == VERSIONS
        assert any(row['stage'] == 'distributed_exports' for row in report['observation_errors'])
    else:
        assert 'mujoco' not in report['versions']


@pytest.mark.parametrize('version,defect', [(3, 'bad-expected'), (2, None), (1, None)])
def test_new_projection_controls_cannot_enter_legacy_requests_or_start_imports(tmp_path, version, defect):
    result, report, marker = launch(tmp_path, defect, version)
    assert result.returncode == 1 and report is None
    assert not marker.exists()
