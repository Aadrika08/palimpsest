"""Current source identity and unchanged scientific contract; no study admission."""
import copy
import hashlib
import json

from scripts import memory_family_compact_v4 as compact
from scripts import memory_condition_replay_admission_v1 as admission
from scripts import memory_family_condition_seal_v4 as seal

ROOT = compact.ROOT
PARENT = 'docs/plans/memory-family-compact-evidence-v4-directory-census-v1-protocol.json'
OLD_EXTENSION = 'docs/plans/memory-condition-seal-v1-directory-census-v1-protocol.json'


def test_current_profile_is_explicit_and_changes_only_source_identity():
    assert compact.PROTOCOL_PATH.name == 'memory-family-compact-evidence-v4-retained-condition-v1-protocol.json'
    parent_bytes = (ROOT / PARENT).read_bytes()
    assert hashlib.sha256(parent_bytes).hexdigest() == '434bd8bcdc6889a862f9c59e79f52cf9cf5d4cf7c07e15b0bf5c60eafb8c5947'
    parent = json.loads(parent_bytes)
    current = copy.deepcopy(compact.PROTOCOL)
    excluded = {'behavior_sources', 'source_revision'}
    assert {k: v for k, v in current.items() if k not in excluded} == {
        k: v for k, v in parent.items() if k not in excluded}
    before = {row['id']: row for row in parent['behavior_sources']}
    after = {row['id']: row for row in current['behavior_sources']}
    assert set(before) <= set(after)
    assert {key for key in before if before[key] != after[key]} == {
        'compact_reader_converter', 'engine', 'artifacts', 'records'}
    assert set(after) - set(before) == {
        'retained_condition_reader', 'retained_condition_plan', 'retained_condition_parent_protocol'}
    assert compact.behavior_source_identities(ROOT) == current['behavior_sources']
    assert current['source_revision']['scientific_contract_changed'] is False
    assert current['source_revision']['allocation_authorized'] is False


def test_condition_extension_preserves_previous_contract_and_empty_trust():
    old_bytes = (ROOT / OLD_EXTENSION).read_bytes()
    parent = json.loads(old_bytes)
    assert seal.EXTENSION_PATH == admission.EXTENSION_PATH == (
        'docs/plans/memory-condition-seal-v1-retained-condition-v1-protocol.json')
    current = json.loads((ROOT / seal.EXTENSION_PATH).read_bytes())
    excluded = {'source_pins', 'source_revision', 'base_protocol_sha256'}
    assert {k: v for k, v in current.items() if k not in excluded} == {
        k: v for k, v in parent.items() if k not in excluded}
    assert current['base_protocol_sha256'] == compact.PROTOCOL_SHA256
    parent_ref = current['source_revision']['parent_extension']
    assert parent_ref == {'path': OLD_EXTENSION, 'size_bytes': len(old_bytes),
                          'sha256': hashlib.sha256(old_bytes).hexdigest()}
    assert [row['path'] for row in current['source_pins']] == sorted(admission.EXTENSION_SOURCES)
    for row in current['source_pins']:
        payload = (ROOT / row['path']).read_bytes()
        assert len(payload) == row['size_bytes']
        assert hashlib.sha256(payload).hexdigest() == row['sha256']
    assert admission.TRUSTED_QUALIFICATION_PINS == ()
