"""Q4 entry through tiny authored packages; no installed runtime or real controls.

The shared CPU fixture uses two authored missing-import declarations. The actual
nineteen-name policy remains a separate frozen parent/admission requirement.
"""
import json

import pytest

from test_puck_cpu_runtime_entry import cpu_policy, cpu_setup
from test_puck_tmpfs_dependencies import POLICY, authored
from test_puck_worker_dependencies import dependency_fixture


def q4_policy(registration, source):
    cpu_policy(registration, source)
    registration['qualification'].update(
        kind='puck-held-runtime-import-qualification-v4', version=4)


def run_q4(*, defect=None, dependency_version=3, policy=q4_policy):
    with authored() as base:
        result, _ = dependency_fixture(
            base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
            mutate=lambda deps, root: cpu_setup(
                deps, root, defect, dependency_version),
            source_change=policy)
    return result


def test_q4_runs_four_expected_imports_and_emits_explicit_version_without_authority():
    result = run_q4()
    assert result.returncode == 0, result.stderr
    assert len(result.stdout.splitlines()) == 1
    receipt = json.loads(result.stdout)
    entry = receipt['entry_result']
    assert entry['kind'] == 'puck-held-runtime-import-qualification-result-v2'
    assert entry['version'] == 2 and entry['qualification_version'] == 4
    assert entry['status'] == 'imports_completed'
    assert entry['held_imports_observed'] is True
    assert [row['name'] for row in entry['imports']] == [
        'numpy', 'torch', 'torchvision', 'mujoco']
    assert {row['name']: row['version'] for row in entry['imports']} == {
        'numpy': 'authored-numpy', 'torch': 'authored-torch',
        'torchvision': 'authored-torchvision', 'mujoco': 'authored-mujoco'}
    assert receipt['dependencies']['native_identity'] == POLICY
    assert receipt['stdlib_cache_aliases'] == {'__mp_main__': '__main__'}
    assert receipt['denied_imports'] == receipt['expected_missing_imports'] == [
        'numpy._distributor_init_local', 'org']
    for value in (receipt, entry):
        for name in ('runtime_qualified', 'native_authorized',
                     'collection_authorized', 'executable'):
            assert value[name] is False
        assert value['qualification_claims'] == []
    assert receipt['dependencies_qualified'] is False


@pytest.mark.parametrize('defect', [
    'missing-torchvision', 'extra-version', 'version-bool',
    'kind-mismatch', 'extra-field'])
def test_q4_malformed_descriptor_refuses_before_any_authored_initializer(defect):
    def malformed(registration, source):
        q4_policy(registration, source)
        qualification = registration['qualification']
        if defect == 'missing-torchvision':
            del qualification['expected_versions']['torchvision']
        elif defect == 'extra-version':
            qualification['expected_versions']['foreign'] = 'authored-foreign'
        elif defect == 'version-bool':
            qualification['version'] = True
        elif defect == 'kind-mismatch':
            qualification['kind'] = 'puck-held-runtime-import-qualification-v3'
        else:
            qualification['entry'] = 'foreign.qualify'

    result = run_q4(defect='before-init', policy=malformed)
    assert result.returncode != 0 and result.stdout == ''
    assert 'qualification' in result.stderr.lower(), result.stderr
    assert 'NUMERICAL_INIT_RAN' not in result.stderr
    assert 'DEFAULT_ENTRY_RAN' not in result.stderr


@pytest.mark.parametrize('dependency_version', [1, 2])
def test_q4_requires_v3_tmpfs_custody_before_authored_initializers(dependency_version):
    result = run_q4(defect='before-init', dependency_version=dependency_version)
    assert result.returncode != 0 and result.stdout == ''
    reason = 'Four-import qualification requires admitted v3 tmpfs dependency custody'
    assert reason in result.stderr, result.stderr
    assert 'NUMERICAL_INIT_RAN' not in result.stderr
    assert 'DEFAULT_ENTRY_RAN' not in result.stderr


def test_q4_initializer_cannot_rewrite_the_captured_expected_version():
    result = run_q4(defect='rewrite-version')
    assert result.returncode != 0 and result.stdout == ''
    assert 'Runtime qualification version differs: torchvision' in result.stderr, result.stderr
    assert 'DEFAULT_ENTRY_RAN' not in result.stderr
