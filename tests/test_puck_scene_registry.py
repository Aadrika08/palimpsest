"""Authored byte-only registry fixtures; no publications or native execution."""
import copy
import hashlib
import importlib
import importlib.util
import json
import os
import stat

import pytest

PROTOCOL = 'fe8b2615f965a114274a13aeb2d49c26d3f79e0920eee72bce4eb671adff3d13'
IDS = [6110, 6111, 6112, 6113, 6120, 6121, 6122, 6123]
HASH_FIELDS = ('canonical_scene_sha256', 'scientific_initial_sha256', 'payload_sha256')
KINDS = ('on_policy_inventory', 'on_policy_reservation', 'on_policy_scene_manifest',
         'on_policy_collection_projection', 'on_policy_publication_commit',
         'on_policy_publication_admission')


def canonical_bytes(value):
    return json.dumps(value, allow_nan=False, sort_keys=True,
                      separators=(',', ':')).encode() + b'\n'


def digest(value):
    return hashlib.sha256(value if type(value) is bytes else canonical_bytes(value)).hexdigest()


def inventory_scene(scene_id):
    return {'scene_id': scene_id, **{
        field: digest({'domain': field, 'scene': scene_id}) for field in HASH_FIELDS}}


def inventory_snapshot():
    # Authored roots are declarations only, never opened by this test suite.
    roots, records = [], []
    for kind in ('ref', 'worktree', 'raw_registry', 'manifest'):
        path = f'/synthetic/inventory/{kind}'
        roots.append({'kind': kind, 'path': path, 'resolved_path': path,
                      'exists': True, 'readable': True, 'is_directory': True,
                      'is_symlink': False, 'identity_sha256': digest({'root': kind})})
        records.append({'kind': kind, 'name': 'synthetic-' + kind, 'root': path,
                        'identity_sha256': digest({'record': kind}), 'role': 'prior',
                        'lineage_sha256': None, 'scenes': [inventory_scene(6000)]
                        if kind == 'raw_registry' else [],
                        'metadata': {'byte_count': 6110}})
    records[-1].update(role='self_reservation', lineage_sha256=PROTOCOL,
                      scenes=[{'scene_id': scene, **dict.fromkeys(HASH_FIELDS)} for scene in IDS])
    return {'version': 1, 'complete': True, 'remote_refs_fresh': True,
            'held_out_accessed': False, 'roots': roots, 'records': records}


def reservation():
    inventory = inventory_snapshot()
    prior = inventory['records'][2]['scenes'][0]
    return {'version': 1, 'kind': 'puck-on-policy-reservation-v1',
            'lineage_sha256': PROTOCOL, 'scene_ids': IDS.copy(),
            'inventory_before_sha256': digest(inventory),
            'inventory_after_sha256': digest(inventory), 'inventory': inventory,
            'occupied_scene_ids': [6000], **{
                'occupied_' + field: [prior[field]] for field in HASH_FIELDS}}


def fake_candidate(scene_id, slot, split):
    y = -0.7 + slot * 0.2
    return {'version': 1, 'kind': 'puck-on-policy-layout-v1', 'seed': scene_id,
            'split': split, 'slot': slot,
            'rover_pose': [-1.0, float(y + 0.25), float(-0.2 + slot * 0.05)],
            'puck_xy': [-0.25, float(y)], 'goal_xy': [1.0, float(y)],
            'initial_qvel': 'all zeros'}


def scene_entry(scene_id, slot):
    split = 'on_policy_collection' if slot < 4 else 'on_policy_development'
    layout = fake_candidate(scene_id, slot, split)
    canonical = {'version': 1, 'kind': 'puck-on-policy-canonical-scene-v1',
                 **{field: layout[field] for field in ('rover_pose', 'puck_xy', 'goal_xy')}}
    initial = {**canonical, 'kind': 'puck-on-policy-scientific-initial-v1',
               'initial_qvel': 'all zeros'}
    return {'scene_id': scene_id, 'slot': slot, 'split': split, 'layout': layout,
            'canonical_scene_sha256': digest(canonical),
            'scientific_initial_sha256': digest(initial), 'payload_sha256': digest(layout)}


def scene_manifest():
    return {'version': 1, 'kind': 'puck-on-policy-scene-manifest-v1',
            'lineage_sha256': PROTOCOL, 'reservation_sha256': digest(reservation()),
            'scene_ids': IDS.copy(), 'scenes': [scene_entry(scene, slot)
                                              for slot, scene in enumerate(IDS)]}


def collection_projection():
    return {'version': 1, 'kind': 'puck-on-policy-collection-projection-v1',
            'scene_ids': IDS[:4], 'scenes': scene_manifest()['scenes'][:4]}


def commit_receipt(target='scene-manifest.json'):
    manifest = reservation() if target == 'reservation.json' else scene_manifest()
    raw = canonical_bytes(manifest)
    return {'version': 1, 'kind': 'puck-on-policy-publication-commit-v1',
            'target': target, 'manifest_sha256': digest(raw), 'manifest_bytes': len(raw),
            'reservation_sha256': digest(reservation()), 'protocol_sha256': PROTOCOL}


def admission_receipt(target='scene-manifest.json'):
    receipt = commit_receipt(target)
    receipt_raw = canonical_bytes(receipt)
    return {**receipt, 'kind': 'puck-on-policy-publication-admission-v1',
            'receipt': target + '.commit.json', 'receipt_sha256': digest(receipt_raw),
            'receipt_bytes': len(receipt_raw),
            'manifest_identity': [7, 11, stat.S_IFREG | 0o600, 1, receipt['manifest_bytes'], 19, 23],
            'receipt_identity': [7, 12, stat.S_IFREG | 0o600, 1, len(receipt_raw), 29, 31]}


BUILDERS = dict(zip(KINDS, (inventory_snapshot, reservation, scene_manifest,
                          collection_projection, commit_receipt, admission_receipt)))


def parser():
    spec = importlib.util.find_spec('palimpsest.puck_scene_registry')
    assert spec is not None, 'pure registry byte parser API is missing'
    return importlib.import_module('palimpsest.puck_scene_registry').parse_puck_registry_document


def parse(value, kind):
    return parser()(canonical_bytes(value), kind=kind)


def test_pure_registry_parser_api_is_present():
    assert callable(parser())


@pytest.mark.parametrize('kind', KINDS)
def test_documents_preserve_byte_identity_and_never_grant_authority(kind):
    raw = canonical_bytes(BUILDERS[kind]())
    result = parser()(raw, kind=kind)
    assert result['kind'] == 'puck-registry-scene-identities-v1'
    assert result['document_kind'] == kind
    assert result['document_sha256'] == hashlib.sha256(raw).hexdigest()
    assert result['document_bytes'] == len(raw)
    assert {key: result[key] for key in ('inventory_complete', 'source_closure_authenticated',
            'executable', 'native_authorized', 'collection_authorized')} == dict.fromkeys(
                ('inventory_complete', 'source_closure_authenticated', 'executable',
                 'native_authorized', 'collection_authorized'), False)
    assert result['qualification_claims'] == []


@pytest.mark.parametrize('kind,prefix', [('on_policy_inventory', ''),
                                        ('on_policy_reservation', '/inventory')])
def test_declarations_preserve_unminted_self_hashes_and_prior_roles(kind, prefix):
    value = BUILDERS[kind]()
    result = parse(value, kind)
    scenes = result['scenes']
    assert [scene['scene_id'] for scene in scenes] == [6000] + IDS
    assert scenes[0] == {**inventory_scene(6000), 'pointer': prefix + '/records/2/scenes/0',
                         'split': None, 'role': 'prior', 'lineage_sha256': None,
                         'layout_bound': False}
    assert all(scene['role'] == 'self_reservation' and scene['lineage_sha256'] == PROTOCOL
               and scene['layout_bound'] is False and scene['split'] is None
               and all(scene[field] is None for field in HASH_FIELDS) for scene in scenes[1:])
    assert scenes[-1]['pointer'] == prefix + '/records/3/scenes/7'
    assert result['references'] == []


@pytest.mark.parametrize('kind,role,count', [('on_policy_scene_manifest', 'minted', 8),
                                           ('on_policy_collection_projection', 'collection', 4)])
def test_layouts_bind_exact_three_hash_domains_without_execution_permission(kind, role, count):
    value = BUILDERS[kind]()
    result = parse(value, kind)
    assert [scene['scene_id'] for scene in result['scenes']] == IDS[:count]
    for index, scene in enumerate(result['scenes']):
        assert scene == {'scene_id': IDS[index], 'pointer': f'/scenes/{index}',
                         'role': role, 'split': value['scenes'][index]['split'],
                         'lineage_sha256': PROTOCOL if count == 8 else None,
                         'layout_bound': True,
                         **{field: value['scenes'][index][field] for field in HASH_FIELDS}}
    if count == 8:
        assert result['references'] == [{'kind': 'on_policy_reservation',
            'sha256': digest(reservation()), 'path': None, 'path_base': 'content_digest',
            'pointer': '/reservation_sha256', 'relation': 'reservation'}]
    else:
        assert result['references'] == []


@pytest.mark.parametrize('kind,builder', [('on_policy_publication_commit', commit_receipt),
                                        ('on_policy_publication_admission', admission_receipt)])
@pytest.mark.parametrize('target,target_kind', [('reservation.json', 'on_policy_reservation'),
                                              ('scene-manifest.json', 'on_policy_scene_manifest')])
def test_receipt_references_pin_only_declared_target_commit_and_reservation(kind, builder, target, target_kind):
    value = builder(target)
    result = parse(value, kind)
    expected = [{'kind': target_kind, 'sha256': value['manifest_sha256'], 'path': target,
                 'path_base': 'document_directory', 'pointer': '/target',
                 'relation': 'publication_target'}]
    if kind == 'on_policy_publication_admission':
        expected.append({'kind': 'on_policy_publication_commit', 'sha256': value['receipt_sha256'],
                         'path': target + '.commit.json', 'path_base': 'document_directory',
                         'pointer': '/receipt', 'relation': 'commit_receipt'})
    if target == 'scene-manifest.json':
        expected.append({'kind': 'on_policy_reservation', 'sha256': value['reservation_sha256'],
                         'path': None, 'path_base': 'content_digest',
                         'pointer': '/reservation_sha256', 'relation': 'reservation'})
    assert result['references'] == expected
    assert result['scenes'] == []


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('mutation', ['extra', 'version_boolean', 'version_float', 'missing'])
def test_exact_top_level_fields_and_integer_version_are_required(kind, mutation):
    value = BUILDERS[kind]()
    if mutation == 'extra': value['unexpected'] = None
    elif mutation == 'missing': del value['version']
    elif mutation == 'version_boolean': value['version'] = True
    else: value['version'] = 1.0
    with pytest.raises(ValueError): parse(value, kind)


@pytest.mark.parametrize('kind', KINDS)
def test_dispatch_kind_cannot_alias_another_schema(kind):
    wrong = KINDS[(KINDS.index(kind) + 1) % len(KINDS)]
    with pytest.raises(ValueError): parse(BUILDERS[kind](), wrong)


@pytest.mark.parametrize('kind', ['on_policy_reservation', 'on_policy_scene_manifest'])
def test_frozen_lineage_is_required(kind):
    value = BUILDERS[kind]()
    value['lineage_sha256'] = '0' * 64
    with pytest.raises(ValueError): parse(value, kind)


@pytest.mark.parametrize('kind', ['on_policy_scene_manifest', 'on_policy_collection_projection'])
@pytest.mark.parametrize('mutation', ['heldout', 'reorder', 'extra', 'bool', 'layout_extra',
                                     'layout_int', 'negative_zero', 'domain', 'geometry', 'hash_uppercase'])
def test_layout_roster_geometry_and_hash_domains_reject_tampering(kind, mutation):
    value = BUILDERS[kind]()
    if mutation == 'heldout': value['scene_ids'][0] = 6200
    elif mutation == 'reorder': value['scenes'].reverse()
    elif mutation == 'extra': value['scenes'].append(scene_entry(6120, 4))
    elif mutation == 'bool': value['scenes'][0]['slot'] = False
    elif mutation == 'layout_extra': value['scenes'][0]['layout']['scene_id'] = 6110
    elif mutation == 'layout_int': value['scenes'][0]['layout']['rover_pose'][0] = -1
    elif mutation == 'negative_zero': value['scenes'][0]['layout']['rover_pose'][2] = -0.0
    elif mutation == 'domain': value['scenes'][0]['canonical_scene_sha256'] = value['scenes'][0]['payload_sha256']
    elif mutation == 'geometry': value['scenes'][0]['layout']['puck_xy'][0] += 0.01
    else: value['scenes'][0]['payload_sha256'] = value['scenes'][0]['payload_sha256'].upper()
    with pytest.raises(ValueError): parse(value, kind)


@pytest.mark.parametrize('kind', ['on_policy_scene_manifest', 'on_policy_collection_projection'])
def test_recomputed_cross_entry_geometry_collision_is_rejected(kind):
    value = BUILDERS[kind]()
    second = value['scenes'][1]
    first = value['scenes'][0]
    for field in ('rover_pose', 'puck_xy', 'goal_xy'):
        second['layout'][field] = first['layout'][field].copy()
    for field in HASH_FIELDS[:2]: second[field] = first[field]
    second['payload_sha256'] = digest(second['layout'])
    with pytest.raises(ValueError): parse(value, kind)


@pytest.mark.parametrize('mutation', ['planned_hash', 'prior_null', 'prior_reserved', 'root_alias',
                                     'role_alias', 'scene_extra', 'record_extra', 'bool_id', 'stale'])
def test_inventory_schema_roles_and_source_aliases_are_rejected(mutation):
    value = inventory_snapshot()
    if mutation == 'planned_hash': value['records'][3]['scenes'][0]['payload_sha256'] = '0' * 64
    elif mutation == 'prior_null': value['records'][2]['scenes'][0]['payload_sha256'] = None
    elif mutation == 'prior_reserved': value['records'][2]['scenes'][0]['scene_id'] = 6110
    elif mutation == 'root_alias': value['roots'][0]['path'] += '/..'
    elif mutation == 'role_alias': value['records'][3]['role'] = 'consumed_reservation'
    elif mutation == 'scene_extra': value['records'][2]['scenes'][0]['layout'] = {}
    elif mutation == 'record_extra': value['records'][0]['scene_ids'] = IDS
    elif mutation == 'bool_id': value['records'][2]['scenes'][0]['scene_id'] = True
    else: value['remote_refs_fresh'] = False
    with pytest.raises(ValueError): parse(value, 'on_policy_inventory')


@pytest.mark.parametrize('field', ['inventory_before_sha256', 'inventory_after_sha256',
                                   'occupied_payload_sha256', 'occupied_scene_ids'])
def test_reservation_embedded_binding_cannot_be_tampered(field):
    value = reservation()
    value[field] = '0' * 64 if field.endswith('sha256') and not field.startswith('occupied') else []
    with pytest.raises(ValueError): parse(value, 'on_policy_reservation')


@pytest.mark.parametrize('kind', ['on_policy_publication_commit', 'on_policy_publication_admission'])
@pytest.mark.parametrize('field,bad', [('target', '../scene-manifest.json'), ('target', '/scene-manifest.json'),
    ('target', 'scene-manifest.json/'), ('target', 'scene_manifest.json'),
    ('manifest_sha256', 'A' * 64), ('reservation_sha256', '0' * 63),
    ('protocol_sha256', '0' * 64), ('manifest_bytes', True), ('manifest_bytes', 0),
    ('manifest_bytes', 4 * 1024**2 + 1), ('manifest_bytes', 7.0)])
def test_receipt_target_digest_protocol_and_size_types_are_exact(kind, field, bad):
    value = BUILDERS[kind]()
    value[field] = bad
    with pytest.raises(ValueError): parse(value, kind)


@pytest.mark.parametrize('kind', ['on_policy_publication_commit', 'on_policy_publication_admission'])
def test_reservation_target_cannot_claim_another_reservation_digest(kind):
    builder = commit_receipt if kind.endswith('commit') else admission_receipt
    value = builder('reservation.json')
    value['reservation_sha256'] = '0' * 64
    with pytest.raises(ValueError): parse(value, kind)


@pytest.mark.parametrize('mutation', ['receipt_name', 'receipt_hash', 'receipt_size_bool', 'receipt_size_zero',
    'receipt_size_large', 'missing_identity', 'identity_bool', 'directory', 'nlink', 'identity_size', 'identity_float'])
def test_admission_historical_stat_tuple_and_receipt_shape_are_exact(mutation):
    value = admission_receipt()
    if mutation == 'receipt_name': value['receipt'] = './scene-manifest.json.commit.json'
    elif mutation == 'receipt_hash': value['receipt_sha256'] = 'f' * 65
    elif mutation == 'receipt_size_bool': value['receipt_bytes'] = True
    elif mutation == 'receipt_size_zero': value['receipt_bytes'] = 0
    elif mutation == 'receipt_size_large': value['receipt_bytes'] = 4 * 1024**2 + 1
    elif mutation == 'missing_identity': value['manifest_identity'].pop()
    elif mutation == 'identity_bool': value['manifest_identity'][0] = True
    elif mutation == 'directory': value['manifest_identity'][2] = stat.S_IFDIR | 0o700
    elif mutation == 'nlink': value['receipt_identity'][3] = 2
    elif mutation == 'identity_size': value['receipt_identity'][4] += 1
    else: value['receipt_identity'][5] = 1.0
    with pytest.raises(ValueError): parse(value, 'on_policy_publication_admission')


@pytest.mark.parametrize('raw', [b'', b'{}', b'{}\n\n', b'{"version":1,"version":1}\n',
    b'{"version":NaN}\n', b'{"version":Infinity}\n', b'{"version":1e999}\n',
    b'\xff\n', bytearray(b'{}\n'), b'x' * (4 * 1024**2 + 1)],
    ids=['empty', 'no-newline', 'extra-newline', 'duplicate', 'nan', 'infinity',
         'overflow-float', 'invalid-utf8', 'bytearray', 'oversized'])
def test_strict_bytes_json_and_canonical_limits(raw):
    with pytest.raises(ValueError): parser()(raw, kind='on_policy_inventory')


def test_well_formed_noncanonical_copy_is_rejected():
    value = inventory_snapshot()
    raw = json.dumps(value, sort_keys=True).encode() + b'\n'
    with pytest.raises(ValueError): parser()(raw, kind='on_policy_inventory')


@pytest.mark.parametrize('kind', [None, True, [], 'inventory', 'on_policy_inventory '])
def test_explicit_document_kind_has_no_alias_or_inference(kind):
    with pytest.raises(ValueError): parser()(canonical_bytes(inventory_snapshot()), kind=kind)


def test_structure_depth_and_node_caps_precede_inventory_validation():
    value = inventory_snapshot()
    nested = 0
    for _ in range(33): nested = [nested]
    value['records'][0]['metadata'] = nested
    with pytest.raises(ValueError): parse(value, 'on_policy_inventory')
    value = inventory_snapshot()
    for record in value['records']:
        record['metadata'] = [0] * 17000
    with pytest.raises(ValueError): parse(value, 'on_policy_inventory')


def test_aggregate_scene_cap_is_not_a_per_record_cap():
    value = inventory_snapshot()
    value['records'][2]['scenes'] = [inventory_scene(scene_id) for scene_id in range(4088)]
    assert len(parse(value, 'on_policy_inventory')['scenes']) == 4096
    value['records'][2]['scenes'].append(inventory_scene(4088))
    with pytest.raises(ValueError): parse(value, 'on_policy_inventory')


def test_document_byte_ceiling_rejects_an_otherwise_valid_inventory():
    value = inventory_snapshot()
    template = value['records'][0]
    for index in range(70):
        value['records'].append({**template, 'name': f'large-{index}', 'metadata': 'x' * 60000})
    raw = canonical_bytes(value)
    assert len(raw) > 4 * 1024**2
    with pytest.raises(ValueError): parser()(raw, kind='on_policy_inventory')


@pytest.mark.parametrize('kind', KINDS)
def test_parsing_authorized_bytes_needs_no_filesystem_access(kind, monkeypatch):
    parse_bytes = parser()
    raw = canonical_bytes(BUILDERS[kind]())

    def forbidden(*args, **kwargs):
        raise AssertionError('Registry parser attempted filesystem access')

    monkeypatch.setattr('builtins.open', forbidden)
    for name in ('open', 'stat', 'lstat'):
        monkeypatch.setattr(os, name, forbidden)
    assert parse_bytes(raw, kind=kind)['document_kind'] == kind


def test_results_are_fresh_views_without_mutating_or_retaining_fixture_objects():
    value = inventory_snapshot()
    pristine = copy.deepcopy(value)
    result = parse(value, 'on_policy_inventory')
    result['scenes'][0]['scene_id'] = 1
    result['qualification_claims'].append('untrusted caller change')
    assert value == pristine
    assert parse(value, 'on_policy_inventory')['scenes'][0]['scene_id'] == 6000
    assert parse(value, 'on_policy_inventory')['qualification_claims'] == []


@pytest.mark.parametrize('kind', ['on_policy_inventory', 'on_policy_reservation'])
@pytest.mark.parametrize('declaration', [
    {'scene_ids': [6110]}, {'scenes': [inventory_scene(6110)]},
    {'sceneIds': [6110]}, {'Scene-ID': 6110}, {'layout': {'seed': 6110}},
    {'seed': 6110}, {'canonical_scene_sha256': 'a'*64},
    {'initialPuckXY': [0.0, 0.0]},
])
def test_registry_metadata_cannot_hide_geometry_declarations(kind, declaration):
    value = inventory_snapshot() if kind == 'on_policy_inventory' else reservation()
    inventory = value if kind == 'on_policy_inventory' else value['inventory']
    inventory['records'][0]['metadata'] = {'nested': [declaration]}
    if kind == 'on_policy_reservation':
        value['inventory_before_sha256'] = value['inventory_after_sha256'] = digest(inventory)
    with pytest.raises(ValueError, match='metadata.*declaration'):
        parse(value, kind)
