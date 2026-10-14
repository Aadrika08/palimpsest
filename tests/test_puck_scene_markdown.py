"""Authored Markdown fixtures only; no repository documents or payload reads."""
import hashlib
import importlib
import importlib.util

import pytest


def parse(raw):
    name = 'palimpsest.puck_scene_markdown'
    assert importlib.util.find_spec(name), 'Pure Markdown scene inventory API is missing'
    return importlib.import_module(name).parse_puck_markdown_document(raw)


def test_api_is_pure_raw_inventory_with_no_grants():
    raw = b'# Authored fixture\nScene ID: 6110\n'
    result = parse(raw)
    assert result['document_sha256'] == hashlib.sha256(raw).hexdigest()
    assert result['document_bytes'] == len(raw)
    assert [r['scene_id'] for r in result['mentions']] == [6110]
    assert result['mentions'][0]['split'] is None
    assert result['mentions'][0]['catalog_sha256'] is None
    assert result['mentions'][0]['geometry_bound'] is False
    assert result['mentions'][0]['pointer'].startswith('/lines/2/')
    for flag in ('inventory_complete', 'source_closure_authenticated', 'executable',
                 'native_authorized', 'collection_authorized'):
        assert result[flag] is False
    assert result['qualification_claims'] == []


@pytest.mark.parametrize('declaration, ids, split', [
    ('scene_id: 6110', [6110], None),
    ('- **Scene IDs**: [10, 11, 14]', [10, 11, 14], None),
    ('held_out layout seeds: 7..9', [7, 8, 9], 'held_out'),
    ('Scene: 2-4; split: recorded_dev', [2, 3, 4], 'recorded_dev'),
    ('layout_id = 6', [6], None),
    ('`scene_id`: `8`', [8], None),
])
def test_explicit_decimal_scene_single_list_and_bounded_ranges(declaration, ids, split):
    result = parse((declaration + '\n').encode())
    assert [row['scene_id'] for row in result['mentions']] == ids
    assert {row['split'] for row in result['mentions']} == {split}
    assert result['unsupported_declarations'] == []


def test_model_training_rng_and_counters_never_become_scene_ids():
    result = parse(b'Model seed: 21\nTraining seeds: [21, 22]\nRNG seed: 6110\n'
                   b'Environment seed: 12\n6110 episodes were logged; 21 models.\n'
                   b'Run counter: 6110\nsha256: ' + b'6' * 64 + b'\n')
    assert result['mentions'] == []
    assert result['unsupported_declarations'] == []


@pytest.mark.parametrize('declaration', [
    'Scene ID: 1 or 2', 'scene_id: -1', 'scene_id: 01', 'scene_id: 1.5',
    'scene_id: true', 'scene_id: [1, 1]', 'scene ID is 6110',
    'seeds: [6110]', 'seed=21', 'scene IDs: 4-2', 'layout IDs: 1..4097',
    'scene_id: 2147483648', 'Scene 4; split: unknown',
    'held_out scene 4; split: train', '| scene_id | 6110 |',
    'geometry: [1, 2]', 'goal_xy: [1, 2]', '<!-- scene_id: 6110 -->',
])
def test_unknown_scene_geometry_and_numeric_seed_syntax_is_explicit(declaration):
    result = parse(declaration.encode())
    assert result['mentions'] == []
    assert result['unsupported_declarations'], declaration
    assert result['inventory_complete'] is False


def test_pins_and_geometry_are_claims_only():
    digest = 'a' * 64
    result = parse(('Scene ID: 6110; catalog_sha256: ' + digest + '\n'
                    'geometry: [1,2]\n').encode())
    assert result['mentions'][0]['catalog_sha256'] == digest
    assert result['mentions'][0]['identity_bound'] is False
    assert result['unsupported_declarations'][0]['reason'].startswith('Unbound')


def test_inline_reference_backtick_and_shortcut_local_links_keep_unhashed_pins():
    result = parse(b'[catalog](../catalog.json)\n[report][r]\n[r]: result.json\n'
                   b'Project path: `docs/scenes.md`\n[fixture]\n[fixture]: ../scenes.md\n')
    refs = result['references']
    assert [row['path'] for row in refs] == [
        '../catalog.json', 'result.json', 'result.json', 'docs/scenes.md',
        '../scenes.md', '../scenes.md']
    assert refs[3]['path_base'] == 'recorded_cwd'
    assert all(row['path_base'] == 'document_directory' for row in refs if row is not refs[3])
    assert all(row['sha256'] is None and row['pin_source'] == 'absent' for row in refs)
    assert all(row['kind'] is None for row in refs)
    assert result['missing_pins'] == []
    assert result['mentions'] == []


def test_one_explicit_document_hash_is_retained_but_not_authenticated():
    digest = 'b' * 64
    result = parse(('[fixture](scene.json) sha256: ' + digest).encode())
    assert result['references'][0]['sha256'] == digest
    assert result['references'][0]['pin_source'] == 'declared'
    assert result['source_closure_authenticated'] is False


@pytest.mark.parametrize('target', [
    'https://example.invalid/scene.json', '//example.invalid/scene.md',
    'docs//scene.json', 'docs/../scene.json', 'docs/%2e%2e/scene.json',
    'docs/scene.json?download=1', 'C:\\scene.json',
])
def test_external_or_noncanonical_links_are_explicit_diagnostics(target):
    result = parse(('[scene document](' + target + ')').encode())
    assert result['references'] == []
    assert result['unsupported_declarations']


def test_external_scene_link_without_document_extension_is_not_dropped():
    result = parse(b'[scene](https://example.invalid/scenes/6110)')
    assert result['mentions'] == []
    assert result['unsupported_declarations'][0]['reason'] == 'Declared external document link'


def test_reference_duplicate_is_ambiguous_and_does_not_select_last_definition():
    result = parse(b'[scene][r]\n[r]: one.json\n[r]: two.json\n')
    assert result['unsupported_declarations']
    assert all('/reference_links/' not in row['pointer'] for row in result['references'])


def test_document_paths_and_hash_digits_do_not_invent_scene_identity():
    result = parse(b'`docs/scene-6110.md`\n[scene-6110](scene-6110.json)\n'
                   b'checkpoint_sha256: ' + b'6' * 64)
    assert result['mentions'] == []
    assert result['unsupported_declarations'] == []


def test_strict_json_fence_retains_exact_bytes_value_pointer_and_utf8_offsets():
    raw = '前\n```json\r\n{"scene_id":6110,"geometry":[1,2]}\r\n```\n'.encode()
    result = parse(raw)
    row = result['embedded_json'][0]
    assert raw[row['byte_start']:row['byte_end']] == row['raw']
    assert row['raw'] == b'{"scene_id":6110,"geometry":[1,2]}\r\n'
    assert row['value'] == {'scene_id': 6110, 'geometry': [1, 2]}
    assert row['sha256'] == hashlib.sha256(row['raw']).hexdigest()
    assert row['pointer'] == '/lines/2/embedded_json'
    assert result['mentions'] == []


@pytest.mark.parametrize('content', [
    b'{"scene_id":1,"scene_id":2}', b'{"x":NaN}', b'{"x":1e999}', b'[1,2]',
    b'{"x":"\\ud800"}', b'{', b'{"x":' + b'[' * 33 + b'0' + b']' * 33 + b'}',
])
def test_json_fences_fail_closed_on_poison_or_tree_bounds(content):
    with pytest.raises(ValueError):
        parse(b'```json\n' + content + b'\n```\n')


def test_unknown_fence_or_comment_never_hides_scene_declarations():
    result = parse(b'```python\n# scene_id: 6110\n```\n'
                   b'```yaml\nlayout_seed: 12\n```\n'
                   b'```python\n# no relevant declaration\n```\n')
    assert result['mentions'] == []
    assert len(result['unsupported_declarations']) == 2


def test_unclosed_fence_is_explicit_even_without_known_scene_fields():
    assert parse(b'```json\n{}')['unsupported_declarations']


@pytest.mark.parametrize('raw', [
    'scene_id: 1', b'\xff', b'\x00', b'a' * (4 * 1024**2 + 1),
    b'\n' * 65536, b'\r' * 65537, b' ' * 129 + b'scene_id: 1',
    b'scene_id: 1\n' * 4097,
], ids=['text-not-bytes', 'invalid-utf8', 'nul', 'bytes', 'lf-nodes', 'cr-nodes',
        'nesting', 'items'])
def test_document_type_size_node_nesting_and_item_bounds(raw):
    with pytest.raises(ValueError):
        parse(raw)


def test_supplied_bytes_only_no_open_or_subprocess(monkeypatch):
    import builtins
    import subprocess

    parse(b'')  # Import before installing traps.

    def forbidden(*args, **kwargs):
        raise AssertionError('Parser touched filesystem or subprocess')

    monkeypatch.setattr(builtins, 'open', forbidden)
    monkeypatch.setattr(subprocess, 'run', forbidden)
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    result = parse(b'Scene ID: 6110\n[fixture](../fixture.md)\n')
    assert result['mentions'][0]['scene_id'] == 6110


@pytest.mark.parametrize('text', [
    'scene_number: 6110', 'layout_number: 6110', 'seed_id: 21',
    'geometry_center: [1,2]', 'initial_rover_xy: [1,2]',
    'split: held_out', '[catalog](nested(6110).json)', 'Bare docs/catalog.json',
    'scene: 1; split: train; split: held_out',
    'scene: 1; catalog_sha256: ' + 'a' * 64 + '; catalog_sha256: bad',
    '[fixture](scene.json) sha256: ' + 'A' * 64,
    '[fixture](scene.json) sha256: ' + 'a' * 64 + 'z',
])
def test_ambiguous_or_unknown_syntax_cannot_disappear_from_scope(text):
    result = parse(text.encode())
    assert result['unsupported_declarations']
    assert all(row['sha256'] is None for row in result['references'])


def test_one_pin_does_not_invent_binding_for_two_references():
    result = parse(('[a](one.json) [b](two.md) sha256: ' + 'a' * 64).encode())
    assert len(result['references']) == 2
    assert all(row['sha256'] is None for row in result['references'])
    assert result['unsupported_declarations']


def test_diagnostics_are_bounded_and_preserve_truncation():
    result = parse(b'scene: ' + b'?' * 10000)
    row = result['unsupported_declarations'][0]
    assert len(row['text'].encode()) <= 4096
    assert row['text_truncated'] is True


@pytest.mark.parametrize('character', [b'[', b'`'])
def test_unclosed_markdown_marker_poison_is_bounded(character):
    result = parse(character * 100000)
    assert result['mentions'] == []
    assert result['inventory_complete'] is False


@pytest.mark.parametrize('text', [
    '[Scene IDs: 6110](catalog.json)',
    '[Scene IDs: 6110][r]\n[r]: catalog.json',
    '[Scene IDs: 6110]\n[Scene IDs: 6110]: catalog.json',
    '[goal_xy: 1,2](catalog.json)',
    '[Scene IDs: 6110 catalog.json](catalog.json)',
])
def test_sensitive_link_labels_cannot_disappear_from_inventory(text):
    result = parse(text.encode())
    assert result['mentions'] or result['unsupported_declarations']
