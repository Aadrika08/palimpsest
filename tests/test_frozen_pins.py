"""Historical frozen pins are checked against main's history, never against the current tree.

Each protocol in tests/frozen_pins.py froze exact file bytes (or a repository location)
before main's integration. Its listed tests are skipped as historical while the current
checkout differs; these checks keep the pins meaningful: every byte pin must name the
exact bytes of the file at some commit in HEAD's history.
"""
from pathlib import Path

import pytest

import frozen_pins

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('name', sorted(frozen_pins.PROTOCOLS))
def test_every_byte_pin_names_the_file_at_a_commit_in_history(name):
    pins = frozen_pins.pins(name)
    for path, digest in sorted(pins.items()):
        commit = frozen_pins.commit_holding(path, digest)
        assert commit is not None, f'{name}: no commit in history holds {path} with sha256 {digest}'
        assert frozen_pins.sha256(frozen_pins.show(commit, path)) == digest


@pytest.mark.parametrize('name', sorted(frozen_pins.PROTOCOLS))
def test_every_protocol_declares_a_pin_and_an_absolute_frozen_root(name):
    root = frozen_pins.frozen_root(name)
    assert frozen_pins.pins(name) or root is not None
    assert root is None or root.startswith('/')


def test_every_listed_test_exists_once():
    affected = frozen_pins.affected_tests()
    for nodeid in affected:
        path, *parts = nodeid.split('::')
        source = (ROOT / path).read_text()
        assert f"def {parts[-1].split('[', 1)[0]}(" in source, nodeid
        if len(parts) == 2:
            assert f'class {parts[0]}(' in source, nodeid


def test_skip_reason_is_explicit_and_only_names_real_drift():
    for name in frozen_pins.PROTOCOLS:
        if frozen_pins.drift(name):
            reason = frozen_pins.skip_reason(name)
            assert reason.startswith(f'historical frozen pin ({name}): ')
            assert frozen_pins.POLICY in reason and 're-pinning' in reason


PUBLICATION = 'memory-family-compact-v4-case-publication-v1'
PUBLICATION_DOCUMENTS = (
    ('docs/plans/memory-family-compact-evidence-v4-case-publication-v1-protocol.json', 'behavior_sources'),
    ('docs/plans/memory-condition-seal-v1-case-publication-v1-protocol.json', 'source_pins'),
    ('docs/plans/memory-case-publication-v1-protocol.json', 'source_pins'),
)


@pytest.fixture
def authored_policy(tmp_path, monkeypatch):
    """Only test-owned source bytes; no production reader or protected payloads."""
    source = tmp_path / 'authored.py'
    source.write_bytes(b'authored source\n')
    digest = frozen_pins.sha256(source.read_bytes())
    monkeypatch.setattr(frozen_pins, 'ROOT', tmp_path)
    monkeypatch.setattr(frozen_pins, 'PROTOCOLS', {
        'authored': (lambda: {'authored.py': digest}, None, ('tests/authored.py::test_case',)),
    })
    frozen_pins.drift.cache_clear()
    yield source
    frozen_pins.drift.cache_clear()


def markers_for(*nodeids):
    """Run the real collection hook over authored item identities, without fixtures."""
    from types import SimpleNamespace
    from conftest import pytest_collection_modifyitems
    items = []
    for nodeid in nodeids:
        marks = []
        items.append(SimpleNamespace(nodeid=nodeid, marks=marks, add_marker=marks.append))
    pytest_collection_modifyitems(None, items)
    return [item.marks for item in items]


def test_matching_authored_source_does_not_skip(authored_policy):
    assert frozen_pins.drift('authored') == ()
    assert markers_for('tests/authored.py::test_case[one]') == [[]]


@pytest.mark.parametrize('change', ['missing', 'drift'])
def test_changed_authored_source_skips_only_its_owned_node(authored_policy, change):
    if change == 'missing':
        authored_policy.unlink()
    else:
        authored_policy.write_bytes(b'changed source\n')
    owned, unrelated = markers_for('tests/authored.py::test_case[one]', 'tests/authored.py::test_other')
    assert unrelated == []
    assert len(owned) == 1 and owned[0].name == 'skip'
    reason = owned[0].kwargs['reason']
    assert reason.startswith('historical frozen pin (authored): authored.py differs from its pin ')
    assert frozen_pins.POLICY in reason


def test_authored_drift_cache_is_isolated_between_source_states(authored_policy):
    assert frozen_pins.drift('authored') == ()
    authored_policy.write_bytes(b'changed source\n')
    frozen_pins.drift.cache_clear()
    assert len(frozen_pins.drift('authored')) == 1
    authored_policy.write_bytes(b'authored source\n')
    frozen_pins.drift.cache_clear()
    assert frozen_pins.drift('authored') == ()


def test_pin_union_accepts_equal_duplicates_and_rejects_conflicts():
    first = [{'path': 'authored.py', 'sha256': 'a' * 64}]
    assert frozen_pins.merge_pin_rows(first, first, [{'path': 'other.py', 'sha256': 'b' * 64}]) == {
        'authored.py': 'a' * 64, 'other.py': 'b' * 64,
    }
    with pytest.raises(ValueError, match='Conflicting frozen pin: authored.py'):
        frozen_pins.merge_pin_rows(first, [{'path': 'authored.py', 'sha256': 'b' * 64}])


def test_exact_node_lookup_precedes_function_fallback_and_leaves_siblings_active():
    mapping = {'t.py::test_exact[a]': 'exact', 't.py::test_base': 'base'}
    assert frozen_pins.protocol_for('t.py::test_exact[a]', mapping) == 'exact'
    assert frozen_pins.protocol_for('t.py::test_exact[b]', mapping) is None
    assert frozen_pins.protocol_for('t.py::test_base[a]', mapping) == 'base'
    assert frozen_pins.protocol_for('t.py::test_base', mapping) == 'base'
    assert frozen_pins.protocol_for('t.py::test_other', mapping) is None


def test_real_hook_marks_exact_node_without_marking_its_sibling(authored_policy, monkeypatch):
    monkeypatch.setattr(frozen_pins, 'PROTOCOLS', {
        'authored': (lambda: {'authored.py': '0' * 64}, None, ('tests/authored.py::test_case[late]',)),
    })
    selected, sibling = markers_for('tests/authored.py::test_case[late]', 'tests/authored.py::test_case[early]')
    assert len(selected) == 1 and selected[0].name == 'skip'
    assert sibling == []


@pytest.mark.parametrize('same_group', [False, True])
@pytest.mark.parametrize('other', ['t.py::test_case', 't.py::test_case[late]'])
def test_duplicate_or_base_exact_ownership_is_rejected(monkeypatch, same_group, other):
    first = 't.py::test_case'
    protocols = {'one': (None, None, (first, other))} if same_group else {
        'one': (None, None, (first,)), 'two': (None, None, (other,)),
    }
    monkeypatch.setattr(frozen_pins, 'PROTOCOLS', protocols)
    with pytest.raises(ValueError, match='(listed|Ambiguous)'):
        frozen_pins.affected_tests()


def test_publication_group_uses_actual_document_union_and_keeps_old_ownership():
    import json
    rows = [json.loads((ROOT / path).read_bytes())[key] for path, key in PUBLICATION_DOCUMENTS]
    expected = frozen_pins.merge_pin_rows(*rows)
    assert len(expected) == 93
    assert frozen_pins.pins(PUBLICATION) == expected
    entries = frozen_pins.PROTOCOLS[PUBLICATION][2]
    assert len(entries) == len(set(entries)) == 100
    mapping = frozen_pins.affected_tests()
    assert mapping['tests/test_memory_family_compact_v4.py::test_protocol_binds_exact_present_sources_including_source_producer'] == 'memory-family-compact-v4'
    assert frozen_pins.protocol_for('tests/test_memory_family_raw_audit_v4.py::test_rejects_size_caps_before_hashing_oversized_file[snapshot]') is None
    assert frozen_pins.protocol_for('tests/test_memory_family_raw_audit_v4.py::test_rejects_size_caps_before_hashing_oversized_file[report]') == PUBLICATION


def test_publication_pins_are_real_bytes_at_the_fixed_main_ancestor():
    commit = '5547efc6dd7210e7a35aa02536140c351c7104b1'
    frozen_pins.git('merge-base', '--is-ancestor', commit, 'HEAD')
    for path, digest in frozen_pins.pins(PUBLICATION).items():
        assert frozen_pins.sha256(frozen_pins.show(commit, path)) == digest, path
