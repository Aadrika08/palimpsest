"""Finite publication proof must survive both terminal validators unchanged."""
import copy
import hashlib
import time

import pytest

from test_puck_cpu_held_parent import result_case
from test_puck_cpu_held_runtime_audit import api as auditor_api, binding_fixture
from test_puck_runtime_registration import api as registration_api, row, setup
from test_puck_runtime_staging import canonical, forest, stage, tmpfs_base


def publication_rows():
    # Deliberately not declaration order: receipts must sort exact projections.
    declarations = [
        dict(name='torch.published', producer='torch', phase='module_exec_publish',
             attributes=['published'], class_binding=None, delegate_attributes=[]),
        dict(name='numpy.published', producer='numpy', phase='module_exec_publish',
             attributes=['namespace', 'published'], class_binding=None,
             delegate_attributes=['call', 'other']),
    ]
    expected = [
        dict(name='numpy.published', producer='numpy', phase='module_exec_publish',
             attributes=['namespace', 'published'], delegate_attributes=['call', 'other']),
        dict(name='torch.published', producer='torch', phase='module_exec_publish',
             attributes=['published'], delegate_attributes=[]),
    ]
    return declarations, expected


def receipt_case(*, published=True):
    parent, dependency, result = result_case()
    audit_dependency, receipt = binding_fixture()
    dependency.update(audit_dependency)
    profile = dependency['import_profile']
    profile.update(kind='puck-producer-import-profile-v2', version=2)
    profile['exports'] = [dict(name='torch.created', producer='torch',
                               phase='module_exec', attributes=['created'], class_binding=None)]
    if published:
        declarations, expected = publication_rows()
        profile['exports'].extend(declarations)
        receipt['exported_modules'] = [
            dict(name='numpy.published', producer='numpy'),
            dict(name='torch.created', producer='torch'),
            dict(name='torch.published', producer='torch'),
        ]
        receipt['published_export_modules'] = expected
    result['dependencies'].update(receipt)
    return parent, auditor_api(), dependency, result


def check_receipt(consumer, parent, auditor, dependency, result):
    if consumer == 'parent':
        parent.validate_worker_result(result, registration_sha256='a' * 64,
                                     dependency_sha256='b' * 64,
                                     dependencies=dependency, negative_imports=['org'])
    else:
        auditor.binding_receipt(result['dependencies'], dependency)


@pytest.mark.parametrize('consumer', ['parent', 'independent-auditor'])
def test_exact_sorted_closed_publication_proof_is_accepted(consumer):
    parent, auditor, dependency, result = receipt_case()
    check_receipt(consumer, parent, auditor, dependency, result)


@pytest.mark.parametrize('consumer', ['parent', 'independent-auditor'])
@pytest.mark.parametrize('defect', [
    'missing', 'empty', 'not-list', 'phase', 'producer', 'attributes', 'delegates',
    'name', 'extra-row', 'extra-field', 'missing-field', 'unsorted', 'duplicate',
    'phase-case', 'path-case', 'delegate-order',
])
def test_published_export_proof_cannot_be_missing_or_rebound(consumer, defect):
    parent, auditor, dependency, result = receipt_case()
    # Every negative starts from a terminal that meets all unrelated checks.
    check_receipt(consumer, parent, auditor, dependency, result)
    receipt = result['dependencies']
    proof = receipt['published_export_modules']
    if defect == 'missing':
        del receipt['published_export_modules']
    elif defect == 'empty':
        receipt['published_export_modules'] = []
    elif defect == 'not-list':
        receipt['published_export_modules'] = {}
    elif defect == 'phase':
        proof[0]['phase'] = 'module_exec'
    elif defect == 'producer':
        proof[0]['producer'] = 'torch'
    elif defect == 'attributes':
        proof[0]['attributes'] = ['unrelated']
    elif defect == 'delegates':
        proof[0]['delegate_attributes'] = ['call']
    elif defect == 'name':
        proof[0]['name'] = 'numpy.unrelated'
    elif defect == 'extra-row':
        proof.append(dict(name='torch.undeclared', producer='torch',
                          phase='module_exec_publish', attributes=['undeclared'],
                          delegate_attributes=[]))
    elif defect == 'extra-field':
        proof[0]['unreviewed'] = False
    elif defect == 'missing-field':
        del proof[0]['attributes']
    elif defect == 'unsorted':
        proof.reverse()
    elif defect == 'duplicate':
        proof.append(copy.deepcopy(proof[-1]))
    elif defect == 'phase-case':
        proof[0]['phase'] = 'MODULE_EXEC_PUBLISH'
    elif defect == 'path-case':
        proof[0]['attributes'] = ['namespace', 'Published']
    else:
        proof[0]['delegate_attributes'].reverse()
    with pytest.raises(ValueError):
        check_receipt(consumer, parent, auditor, dependency, result)


@pytest.mark.parametrize('consumer', ['parent', 'independent-auditor'])
def test_ordinary_exports_keep_legacy_receipt_without_publication_key(consumer):
    parent, auditor, dependency, result = receipt_case(published=False)
    assert 'published_export_modules' not in result['dependencies']
    check_receipt(consumer, parent, auditor, dependency, result)


@pytest.mark.parametrize('consumer', ['parent', 'independent-auditor'])
@pytest.mark.parametrize('proof', [[], publication_rows()[1]], ids=['empty', 'undeclared'])
def test_publication_receipt_key_is_forbidden_without_publication_declarations(consumer, proof):
    parent, auditor, dependency, result = receipt_case(published=False)
    check_receipt(consumer, parent, auditor, dependency, result)
    result['dependencies']['published_export_modules'] = copy.deepcopy(proof)
    with pytest.raises(ValueError):
        check_receipt(consumer, parent, auditor, dependency, result)


def demo_publication():
    return dict(name='demo.published', producer='demo', phase='module_exec_publish',
                attributes=['published'], class_binding=None, delegate_attributes=[])


def test_enhanced_registration_maps_published_child_to_its_declared_producer(tmp_path):
    site, observation, profile, _ = setup(tmp_path)
    profile.update(kind='puck-producer-import-profile-v2', version=2, native_cache=[])
    profile['exports'] = [demo_publication()]
    observation['cache']['modules'].append(row(site, 'demo.published', spec=False))
    api = registration_api()
    snapshot = api._Snapshot(time.monotonic() + 30)
    try:
        census = snapshot.census(str(site))
        modules, namespaces = api._module_maps(str(site), observation, profile, census,
                                               allow_native_cache=True)
    finally:
        snapshot.close()
    assert [record['name'] for record in modules] == ['demo', 'demo.core']
    assert namespaces == []


@pytest.mark.parametrize('legacy', ['plain-profile', 'dependency-v2'])
def test_publication_declaration_cannot_silently_extend_legacy_schema(tmp_path, legacy):
    from palimpsest.puck_dependency_files import HeldDependencyNamespace

    _, registration = forest(tmp_path, version=2 if legacy == 'dependency-v2' else 3)
    profile = registration['import_profile']
    if legacy == 'dependency-v2':
        profile.update(kind='puck-producer-import-profile-v2', version=2, native_cache=[])
    profile['exports'] = [demo_publication()]
    raw = canonical(registration)
    with pytest.raises(ValueError):
        HeldDependencyNamespace(raw, expected_sha256=hashlib.sha256(raw).hexdigest(),
                                deadline=time.monotonic() + 30,
                                registration_path=str(tmp_path / 'registration.json'))


def test_explicit_publication_declaration_survives_inert_tmpfs_staging(tmp_path):
    source, registration = forest(tmp_path, version=3)
    profile = registration['import_profile']
    profile.update(kind='puck-producer-import-profile-v2', version=2, native_cache=[])
    profile['exports'] = [demo_publication()]
    before = copy.deepcopy(registration)
    with tmpfs_base() as base:
        staged = stage(registration, base / 'stage')
        assert staged['import_profile'] == before['import_profile']
        assert registration == before
        assert staged['kind'] == 'puck-worker-dependencies-v3'
        assert staged['native_identity'] == 'tmpfs-raw-dev-inode-v1'
        from pathlib import Path

        staged_source = Path(staged['roots'][0]['root']) / 'demo/__init__.py'
        assert staged_source.read_bytes() == (source / 'demo/__init__.py').read_bytes()
