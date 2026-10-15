"""Authored CUDA/probe control flow; no installed package or allocation runs."""
import json

import pytest

from test_puck_cpu_runtime_entry import (
    CPU_VERSIONS, ORDER, authored, cpu_policy, cpu_setup, dependency_fixture, descriptor,
)


BASE_MISSING = ['numpy._distributor_init_local', 'org', 'torch._rocm_init']


def optional_fixture(base, *, declared, present=None, probe=False):
    def mutate(deps, root):
        cpu_setup(deps, root, 'before-init' if present else None)
        modules = {
            'torch.cuda': ('torch/cuda/__init__.py', True,
                'try:\n'
                ' try:\n  import pynvml\n'
                ' except ModuleNotFoundError:\n  pass\n'
                'except ImportError as error:\n _optional_error = error\n'
                'from .memory import READY\nassert READY is True\n'),
            'torch.cuda.memory': ('torch/cuda/memory.py', False, 'READY = True\n'),
        }
        if probe:
            modules['torch._import_utils'] = ('torch/_import_utils.py', False,
                'import importlib.util\n'
                'def dill_available():\n'
                ' try:\n  return importlib.util.find_spec("dill") is not None\n'
                ' except ImportError:\n  return False\n')
        for name, (relative, package, code) in modules.items():
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code)
            deps['modules'].append(dict(name=name, root_index=0, path=relative,
                                        kind='python', is_package=package))
            deps['roots'][0]['files'].append(descriptor(path, relative))
        initializer = root / 'torch/__init__.py'
        initializer.write_text(initializer.read_text() + 'from . import cuda\n' +
            ('from ._import_utils import dill_available\nassert dill_available() is False\n' if probe else ''))
        if present:
            path = root / 'pynvml.py'
            path.write_text('raise AssertionError("OPTIONAL_TARGET_RAN")\n')
            deps['roots'][0]['files'].append(descriptor(path, 'pynvml.py'))
            if present == 'registered':
                deps['modules'].append(dict(name='pynvml', root_index=0, path='pynvml.py',
                                            kind='python', is_package=False))
        deps['roots'][0]['files'] = sorted(
            [descriptor(root / row['path'], row['path']) for row in deps['roots'][0]['files']],
            key=lambda row: row['path'])

    def policy(reg, source):
        cpu_policy(reg, source)
        reg['qualification']['negative_imports'] = sorted(BASE_MISSING + declared)

    return dependency_fixture(base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
                              mutate=mutate, source_change=policy)[0]


@pytest.mark.parametrize('declared', [False, True])
def test_caught_cuda_optional_import_requires_declared_absence_before_memory(declared):
    with authored() as base:
        result = optional_fixture(base, declared=['pynvml'] if declared else [])
    if not declared:
        assert result.returncode != 0 and result.stdout == ''
        assert 'Unregistered local or external dependency import: pynvml' in result.stderr
        assert "ModuleNotFoundError: No module named 'torch.cuda.memory'" in result.stderr
        assert 'direct cause of the following exception' in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        receipt = json.loads(result.stdout)
        assert receipt['expected_missing_imports'] == sorted(BASE_MISSING + ['pynvml'])
        assert receipt['denied_imports'] == ['numpy._distributor_init_local', 'org', 'pynvml']
        assert [row['name'] for row in receipt['entry_result']['imports']] == ORDER
        assert {row['name']: row['version'] for row in receipt['entry_result']['imports']} == CPU_VERSIONS
        assert {'torch.cuda', 'torch.cuda.memory'} <= {
            row['name'] for row in receipt['dependencies']['loaded_modules']}
        assert receipt['runtime_qualified'] is receipt['native_authorized'] is False
        assert receipt['collection_authorized'] is receipt['executable'] is False
        assert receipt['qualification_claims'] == []


@pytest.mark.parametrize('present', ['registered', 'unregistered-file'])
def test_optional_declaration_refuses_a_present_target_before_any_initializer(present):
    with authored() as base:
        result = optional_fixture(base, declared=['pynvml'], present=present)
    assert result.returncode != 0 and result.stdout == ''
    assert 'pynvml' in result.stderr
    assert 'NUMERICAL_INIT_RAN' not in result.stderr
    assert 'OPTIONAL_TARGET_RAN' not in result.stderr
    assert 'DEFAULT_ENTRY_RAN' not in result.stderr


@pytest.mark.parametrize('declared_probe', [False, True])
def test_caught_find_spec_probe_keeps_the_same_absence_and_poison_contract(declared_probe):
    names = ['pynvml', 'dill'] if declared_probe else ['pynvml']
    with authored() as base:
        result = optional_fixture(base, declared=names, probe=True)
    if declared_probe:
        assert result.returncode == 0, result.stderr
        receipt = json.loads(result.stdout)
        assert receipt['expected_missing_imports'] == sorted(BASE_MISSING + names)
        assert receipt['denied_imports'] == ['dill', 'numpy._distributor_init_local', 'org', 'pynvml']
        assert receipt['entry_result']['status'] == 'imports_completed'
        assert receipt['runtime_qualified'] is receipt['collection_authorized'] is False
    else:
        assert result.returncode != 0 and result.stdout == ''
        assert 'Unregistered local or external dependency import: dill' in result.stderr
        assert 'Bootstrap inactive or poisoned' in result.stderr
