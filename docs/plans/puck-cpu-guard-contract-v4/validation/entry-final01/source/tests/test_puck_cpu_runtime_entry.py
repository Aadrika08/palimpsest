"""Prospective CPU entry uses four tiny authored packages, never installed code."""
import json

import pytest

from test_puck_held_runtime_entry import VERSIONS, qualify, setup
from test_puck_tmpfs_dependencies import POLICY, authored, v3
from test_puck_worker_bootstrap import descriptor
from test_puck_worker_dependencies import dependency_fixture

CPU_VERSIONS = {**VERSIONS, 'torchvision': 'authored-torchvision'}
ORDER = ['numpy', 'torch', 'torchvision', 'mujoco']


def cpu_policy(reg, source):
    qualify(reg, source)
    reg['qualification'].update(kind='puck-held-runtime-import-qualification-v3',
        version=3, expected_versions=dict(CPU_VERSIONS),
        negative_imports=['numpy._distributor_init_local', 'org'])


def cpu_setup(deps, root, defect=None, dependency_version=3):
    setup(deps, root)
    directory = root/'torchvision'; directory.mkdir()
    path = directory/'__init__.py'; path.write_text('__version__="authored-torchvision"\n')
    deps['modules'].append({'name':'torchvision', 'root_index':0,
        'path':'torchvision/__init__.py', 'kind':'python', 'is_package':True})
    deps['roots'][0]['files'].append(descriptor(path, 'torchvision/__init__.py'))
    for index, name in enumerate(ORDER):
        path = root/name/'__init__.py'
        code = path.read_text() + 'import sys\n'
        code += 'assert '+repr(ORDER[:index])+'==[name for name in '+repr(ORDER)+' if name in sys.modules and name!='+repr(name)+'], "WRONG_ORDER"\n'
        if name == 'numpy':
            code += ('import importlib\ntry:\n importlib.import_module("numpy._distributor_init_local")\n'
                     'except ModuleNotFoundError as error:\n'
                     ' assert type(error) is ModuleNotFoundError and error.name=="numpy._distributor_init_local"\n'
                     'else:\n raise AssertionError("EXPECTED_MISS_LOADED")\n')
            if defect == 'before-init': code = 'raise AssertionError("NUMERICAL_INIT_RAN")\n'
        if name == 'torchvision':
            if defect == 'wrong-version': code += '__version__="wrong"\n'
            elif defect == 'fail': code += 'raise RuntimeError("AUTHORED_TORCHVISION_FAILURE")\n'
            elif defect == 'caught-miss':
                code += 'try:\n import foreign_optional\nexcept ImportError:\n pass\n'
            elif defect == 'rewrite-version':
                code += ('__version__="wrong"\n'
                         'sys.meta_path[0].owner._reg["qualification"]["expected_versions"]["torchvision"]="wrong"\n')
        path.write_text(code)
    deps['roots'][0]['files'] = sorted([descriptor(root/row['path'], row['path'])
        for row in deps['roots'][0]['files']], key=lambda row:row['path'])
    if dependency_version == 3: v3(deps)
    elif dependency_version == 2:
        deps.update(kind='puck-worker-dependencies-v2', version=2,
            import_profile={'exports':[], 'module_changes':[], 'native_origins':[]})


def test_cpu_entry_runs_four_imports_in_order_with_tmpfs_receipt_and_no_authority():
    with authored() as base:
        result, _ = dependency_fixture(base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
            mutate=cpu_setup, source_change=cpu_policy)
        assert result.returncode == 0, result.stderr
        receipt = json.loads(result.stdout); entry = receipt['entry_result']
        assert entry['kind'] == 'puck-held-runtime-import-qualification-result-v2'
        assert entry['version'] == 2 and entry['qualification_version'] == 3
        assert [row['name'] for row in entry['imports']] == ORDER
        assert {row['name']:row['version'] for row in entry['imports']} == CPU_VERSIONS
        assert entry['status'] == 'imports_completed' and entry['held_imports_observed'] is True
        assert receipt['dependencies']['native_identity'] == POLICY
        assert receipt['denied_imports'] == receipt['expected_missing_imports'] == ['numpy._distributor_init_local', 'org']
        for output in (receipt, entry):
            assert output['runtime_qualified'] is output['collection_authorized'] is output['native_authorized'] is output['executable'] is False
            assert output['qualification_claims'] == []


@pytest.mark.parametrize('defect, reason', [('wrong-version', 'Runtime qualification version differs: torchvision'),
    ('fail', 'AUTHORED_TORCHVISION_FAILURE'), ('caught-miss', 'Unregistered local or external dependency import: foreign_optional'),
    ('rewrite-version', 'Runtime qualification version differs: torchvision')])
def test_cpu_entry_refuses_torchvision_failure_or_initializer_version_rewrite(defect, reason):
    with authored() as base:
        result, _ = dependency_fixture(base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
            mutate=lambda deps, root:cpu_setup(deps, root, defect), source_change=cpu_policy)
        assert result.returncode != 0 and result.stdout == ''
        assert reason in result.stderr, result.stderr
        assert 'DEFAULT_ENTRY_RAN' not in result.stderr


@pytest.mark.parametrize('dependency_version', [1, 2])
def test_cpu_entry_refuses_legacy_dependency_custody_before_numerical_initializers(dependency_version):
    with authored() as base:
        result, _ = dependency_fixture(base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
            mutate=lambda deps, root:cpu_setup(deps, root, 'before-init', dependency_version), source_change=cpu_policy)
        assert result.returncode != 0 and result.stdout == ''
        assert 'tmpfs' in result.stderr, result.stderr
        assert 'NUMERICAL_INIT_RAN' not in result.stderr and 'DEFAULT_ENTRY_RAN' not in result.stderr


@pytest.mark.parametrize('defect', ['missing-name', 'extra-name', 'version-bool', 'kind', 'extra-field',
    'empty-negatives', 'duplicate-negatives', 'unsorted-negatives', 'stdlib-negative', 'local-negative',
    'prefix-negatives', 'reserved-negative', 'nonascii-negative', 'too-many-negatives', 'bad-value'])
def test_cpu_descriptor_is_strict_before_package_execution(defect):
    def change(reg, source):
        cpu_policy(reg, source); q = reg['qualification']
        if defect == 'missing-name': del q['expected_versions']['torchvision']
        elif defect == 'extra-name': q['expected_versions']['arbitrary'] = 'no'
        elif defect == 'version-bool': q['version'] = True
        elif defect == 'kind': q['kind'] = 'puck-held-runtime-import-qualification-v2'
        elif defect == 'extra-field': q['entry'] = 'foreign.code'
        elif defect == 'empty-negatives': q['negative_imports'] = []
        elif defect == 'duplicate-negatives': q['negative_imports'] = ['org', 'org']
        elif defect == 'unsorted-negatives': q['negative_imports'] = ['org', 'numpy.optional']
        elif defect == 'stdlib-negative': q['negative_imports'] = ['json.optional', 'org']
        elif defect == 'local-negative': q['negative_imports'] = ['org', 'palimpsest.optional']
        elif defect == 'prefix-negatives': q['negative_imports'] = ['org', 'org.child']
        elif defect == 'reserved-negative': q['negative_imports'] = ['__main__', 'org']
        elif defect == 'nonascii-negative': q['negative_imports'] = ['négative', 'org']
        elif defect == 'too-many-negatives': q['negative_imports'] = ['missing_'+str(i).zfill(3) for i in range(129)]
        else: q['expected_versions']['torchvision'] = True
    with authored() as base:
        result, _ = dependency_fixture(base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
            mutate=lambda deps, root:cpu_setup(deps, root, 'before-init'), source_change=change)
        assert result.returncode != 0 and result.stdout == ''
        assert 'NUMERICAL_INIT_RAN' not in result.stderr and 'DEFAULT_ENTRY_RAN' not in result.stderr
        assert any(term in result.stderr.lower() for term in ('qualification', 'missing import', 'non-stdlib',
            'canonical registration')), result.stderr


def test_cpu_descriptor_proves_declared_absence_before_initializers():
    def change(reg, source):
        cpu_policy(reg, source); reg['qualification']['negative_imports'] = ['numpy', 'org']
    with authored() as base:
        result, _ = dependency_fixture(base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
            mutate=lambda deps, root:cpu_setup(deps, root, 'before-init'), source_change=change)
        assert result.returncode != 0 and result.stdout == ''
        assert 'overlaps a registered module' in result.stderr, result.stderr
        assert 'NUMERICAL_INIT_RAN' not in result.stderr


@pytest.mark.parametrize('version', [1, 2])
def test_legacy_qualification_keeps_three_imports_and_result_v1(version):
    def change(reg, source):
        qualify(reg, source)
        if version == 2:
            reg['qualification'].update(kind='puck-held-runtime-import-qualification-v2', version=2)
    with authored() as base:
        result, _ = dependency_fixture(base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
            mutate=setup, source_change=change)
        assert result.returncode == 0, result.stderr
        entry = json.loads(result.stdout)['entry_result']
        assert entry['kind'] == 'puck-held-runtime-import-qualification-result-v1'
        assert entry['version'] == 1 and 'qualification_version' not in entry
        assert [row['name'] for row in entry['imports']] == ['numpy', 'torch', 'mujoco']
