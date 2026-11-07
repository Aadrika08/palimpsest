"""Unpatched prospective source identities; no actual qualification authority."""
import hashlib
import json
import time
from pathlib import Path
import pytest

from palimpsest import memory
from scripts import memory_family_compact_v4 as compact
from scripts import memory_family_condition_seal_v4 as seal
from scripts import memory_condition_replay_admission_v1 as admission
from scripts import memory_family_case_publication_v1 as publication
from scripts import memory_case_execution_pins_v1 as execution

ROOT = Path(__file__).resolve().parents[1]
BASE = 'docs/plans/memory-family-compact-evidence-v4-case-publication-v1-protocol.json'
CONDITION = 'docs/plans/memory-condition-seal-v1-case-publication-v1-protocol.json'
PUBLICATION = 'docs/plans/memory-case-publication-v1-protocol.json'
OLD_BASE = 'docs/plans/memory-family-compact-evidence-v4-retained-condition-v1-protocol.json'
OLD_CONDITION = 'docs/plans/memory-condition-seal-v1-retained-condition-v1-protocol.json'
OLD_HASHES = {
    OLD_BASE:'e71fc7ea6185f7de769b9879d4b581458074b925255b4712f0f6578fb0556261',
    OLD_CONDITION:'ca8f148526c4ce33a28583a33c4d0dc474e7264aba66e89946c8d2fe3cc6f93f'}


def descriptor(path):
    payload=(ROOT/path).read_bytes()
    return {'path':path,'size_bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}


def read(path):
    payload=(ROOT/path).read_bytes();value=json.loads(payload)
    assert memory.canonical_bytes(value)==payload
    return value


def test_prospective_profiles_exist_and_bind_exact_current_source():
    for path in (BASE,CONDITION,PUBLICATION):
        assert (ROOT/path).is_file(), 'Missing prospective publication profile: '+path
    assert compact.PROTOCOL_PATH==ROOT/BASE
    assert seal.EXTENSION_PATH==admission.EXTENSION_PATH==CONDITION
    assert publication.PUBLICATION_PATH==PUBLICATION
    base,condition,pub=read(BASE),read(CONDITION),read(PUBLICATION)
    assert compact.behavior_source_identities(ROOT)==base['behavior_sources']
    assert condition['base_protocol_sha256']==descriptor(BASE)['sha256']
    assert pub['base_protocol']==descriptor(BASE)
    assert pub['condition_extension']==descriptor(CONDITION)
    assert pub['schemas']==publication.PUBLICATION_SCHEMAS
    assert pub['bounds']==publication.PUBLICATION_BOUNDS
    assert pub['claims']==base['claims']
    for row in [*condition['source_pins'],*pub['source_pins']]:
        assert row==descriptor(row['path'])


def test_historical_bytes_and_scientific_contract_are_preserved():
    for path,expected in OLD_HASHES.items():
        assert descriptor(path)['sha256']==expected
    old=json.loads((ROOT/OLD_BASE).read_bytes());new=read(BASE)
    excluded={'behavior_sources','source_revision'}
    assert {k:v for k,v in old.items() if k not in excluded}=={
        k:v for k,v in new.items() if k not in excluded}
    old_condition=json.loads((ROOT/OLD_CONDITION).read_bytes());new_condition=read(CONDITION)
    excluded={'base_protocol_sha256','source_pins','source_revision'}
    assert {k:v for k,v in old_condition.items() if k not in excluded}=={
        k:v for k,v in new_condition.items() if k not in excluded}
    for profile in (new,new_condition):
        assert profile['source_revision']['scientific_contract_changed'] is False
        assert profile['source_revision']['allocation_authorized'] is False
    assert new['source_revision']['actual_runtime_qualified'] is False
    before={row['id']:row for row in old['behavior_sources']}
    after={row['id']:row for row in new['behavior_sources']}
    for name,row in before.items():
        assert after[name]['path']==row['path']
        if row['path'].endswith('.json'):
            assert after[name]==row


def test_complete_declared_closure_excludes_output_cycles_and_real_trust():
    from scripts import build_memory_case_publication_profile_v1 as generator
    base,condition,pub=read(BASE),read(CONDITION),read(PUBLICATION)
    paths=[row['path'] for row in base['behavior_sources']]
    assert len(paths)==len(set(paths))
    required={
        'scripts/memory_family_case_publication_v1.py',
        'scripts/memory_family_case_custody_v1.py',
        'scripts/memory_family_retained_case_v1.py',
        'scripts/memory_condition_replay_admission_v1.py',
        'tests/test_memory_family_case_publisher_v1.py',
        'tests/test_memory_case_publication_profile_v1.py',
        'tests/test_memory_family_producer_v4.py',
        'tests/test_memory_family_condition_close_v4.py',
        'tests/test_memory_family_retained_case_v1.py',
        'tests/memory_publication_authored_profiles.py',
        'tests/frozen_pins.py',
        'scripts/build_memory_case_publication_profile_v1.py'}
    assert required<=set(paths)
    assert generator.local_python_closure(ROOT,required)<=set(paths)
    excluded={BASE,CONDITION,PUBLICATION,publication.EXECUTION_POLICY_PATH,publication.QUALIFICATION_POLICY_PATH}
    for rows in (base['behavior_sources'],condition['source_pins'],pub['source_pins']):
        assert not excluded & {row['path'] for row in rows}
    assert [r['path'] for r in pub['source_pins']]==sorted(set(r['path'] for r in pub['source_pins']))
    assert execution.ACCEPTED_EXECUTION_AUDIT_SHA256==frozenset()
    assert admission.TRUSTED_QUALIFICATION_PINS==()


def test_profile_generator_checks_without_rewriting_registered_bytes():
    from scripts import build_memory_case_publication_profile_v1 as generator
    before={p:(ROOT/p).read_bytes() for p in (BASE,CONDITION,PUBLICATION)}
    assert generator.build_profiles(ROOT,write=False)=={
        p:descriptor(p) for p in (BASE,CONDITION,PUBLICATION)}
    assert before=={p:(ROOT/p).read_bytes() for p in before}


def test_initializer_source_binding_does_not_relax_evidence_paths():
    rows=compact.behavior_source_identities(ROOT)
    assert descriptor('src/palimpsest/__init__.py') in [
        {k:row[k] for k in ('path','size_bytes','sha256')} for row in rows]
    with pytest.raises(ValueError):
        compact._relative('cases/case-a/__init__.py','evidence leaf')
    registered=descriptor('src/palimpsest/__init__.py')
    with compact.bound_payload(ROOT,registered,2*compact.MiB,time.monotonic()+5) as (_,payload,recheck):
        assert payload==(ROOT/registered['path']).read_bytes()
        recheck()
    with pytest.raises(ValueError):
        with compact.bound_payload(ROOT,{**registered,'path':'src/unregistered/__init__.py'},
                2*compact.MiB,time.monotonic()+5):
            pytest.fail('An unregistered initializer must not be opened')


def test_generator_refuses_accepted_source_refresh_before_access(tmp_path,monkeypatch):
    from scripts import build_memory_case_publication_profile_v1 as generator
    monkeypatch.setattr(execution,'ACCEPTED_EXECUTION_AUDIT_SHA256',frozenset({'a'*64}))
    with pytest.raises(PermissionError):
        generator.build_profiles(tmp_path/'absent',write=True)
    assert not (tmp_path/'absent').exists()


def test_declared_profile_metadata_and_empty_real_trust_remain_active():
    """Check declared metadata and empty trust despite current source drift.

    This does not establish completeness of the current import closure.
    """
    base,condition,pub=read(BASE),read(CONDITION),read(PUBLICATION)
    paths=[row['path'] for row in base['behavior_sources']]
    assert len(paths)==len(set(paths))
    required={
        'scripts/memory_family_case_publication_v1.py',
        'scripts/memory_family_case_custody_v1.py',
        'scripts/memory_family_retained_case_v1.py',
        'scripts/memory_condition_replay_admission_v1.py',
        'tests/test_memory_family_case_publisher_v1.py',
        'tests/test_memory_case_publication_profile_v1.py',
        'tests/test_memory_family_producer_v4.py',
        'tests/test_memory_family_condition_close_v4.py',
        'tests/test_memory_family_retained_case_v1.py',
        'tests/memory_publication_authored_profiles.py',
        'tests/frozen_pins.py',
        'scripts/build_memory_case_publication_profile_v1.py'}
    assert required<=set(paths)
    excluded={BASE,CONDITION,PUBLICATION,publication.EXECUTION_POLICY_PATH,publication.QUALIFICATION_POLICY_PATH}
    for rows in (base['behavior_sources'],condition['source_pins'],pub['source_pins']):
        assert not excluded & {row['path'] for row in rows}
    assert [r['path'] for r in pub['source_pins']]==sorted(set(r['path'] for r in pub['source_pins']))
    assert execution.ACCEPTED_EXECUTION_AUDIT_SHA256==frozenset()
    assert admission.TRUSTED_QUALIFICATION_PINS==()
