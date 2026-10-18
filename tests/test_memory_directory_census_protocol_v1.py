"""Prospective source-profile preservation; no actual numerical qualification."""
import copy
import hashlib
import json
from pathlib import Path

from scripts import memory_family_compact_v4 as compact

ROOT=Path(__file__).resolve().parents[1]
ORIGINAL='docs/plans/memory-family-compact-evidence-v4-protocol.json'
ACTIVE='docs/plans/memory-family-compact-evidence-v4-directory-census-v1-protocol.json'
OLD_EXTENSION='docs/plans/memory-condition-seal-v1-protocol.json'
EXTENSION='docs/plans/memory-condition-seal-v1-directory-census-v1-protocol.json'
ORIGINAL_SHA='cbdf034970963a847d42fabc879cc4596a99c8c1b58311561a6c678233e9c4fa'


def test_active_profile_preserves_original_and_all_scientific_fields():
    assert compact.PROTOCOL_PATH == ROOT/ACTIVE
    payload=(ROOT/ORIGINAL).read_bytes()
    assert hashlib.sha256(payload).hexdigest() == ORIGINAL_SHA
    original=json.loads(payload)
    active=copy.deepcopy(compact.PROTOCOL)
    assert set(active) == set(original) | {'source_revision'}
    assert {k:v for k,v in active.items() if k not in ('behavior_sources','source_revision')} == {
        k:v for k,v in original.items() if k != 'behavior_sources'}
    before={r['id']:r for r in original['behavior_sources']}
    after={r['id']:r for r in active['behavior_sources']}
    assert set(after)-set(before) == {'directory_census','directory_census_plan','directory_census_base_protocol'}
    changed={key for key in before if before[key] != after[key]}
    assert changed == {'compact_reader_converter','raw_audit','producer'}
    assert compact.behavior_source_identities(ROOT) == active['behavior_sources']
    parent=active['source_revision']['base_protocol']
    assert parent == {'path':ORIGINAL,'size_bytes':len(payload),'sha256':ORIGINAL_SHA}
    assert active['source_revision']['scientific_contract_changed'] is False


def test_every_audit_and_admission_reference_uses_selected_protocol():
    from scripts import memory_family_raw_audit_v4 as audit
    from scripts import memory_condition_replay_admission_v1 as admission
    expected={'path':ACTIVE,'size_bytes':len(compact.PROTOCOL_BYTES),'sha256':compact.PROTOCOL_SHA256}
    assert audit._protocol_descriptor() == expected
    assert admission._base_sources()[ACTIVE] == expected
    assert admission._base_sources()[ORIGINAL]['sha256'] == ORIGINAL_SHA
    assert admission.TRUSTED_QUALIFICATION_PINS == ()


def test_selected_condition_extension_preserves_all_prior_contract_fields():
    from scripts import memory_family_condition_seal_v4 as sealer
    from scripts import memory_condition_replay_admission_v1 as admission
    assert sealer.EXTENSION_PATH == admission.EXTENSION_PATH == EXTENSION
    parent=json.loads((ROOT/OLD_EXTENSION).read_bytes())
    payload=(ROOT/EXTENSION).read_bytes()
    value=json.loads(payload)
    assert payload == json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    assert set(value) == set(parent) | {'source_revision'}
    changed={'base_protocol_sha256','source_pins','source_revision'}
    assert {k:v for k,v in value.items() if k not in changed} == {
        k:v for k,v in parent.items() if k not in changed}
    assert value['base_protocol_sha256'] == compact.PROTOCOL_SHA256
    assert value['source_revision']['scientific_contract_changed'] is False
    assert [r['path'] for r in value['source_pins']] == sorted(admission.EXTENSION_SOURCES)
    for row in value['source_pins']:
        data=(ROOT/row['path']).read_bytes()
        assert len(data)==row['size_bytes']
        assert hashlib.sha256(data).hexdigest()==row['sha256']
