"""Synthetic writer-shaped bytes only; retained metadata does not authenticate scenes."""
import copy
import hashlib
import json

import pytest

from palimpsest.puck_scene_retained import parse_retained_puck_document

PIN = 'a' * 64
OTHER = 'b' * 64


def encoded(document):
    return json.dumps(document, allow_nan=False).encode()


def row(seed=6000, split='train', student=False):
    value = {'id': 'teacher-6000', 'case': 'teacher-6000', 'kind': 'root',
             'seed': seed, 'split': split, 'max_ticks': 600, 'max_bytes': 1000000}
    if student:
        value['model_seed'] = 21
    return value


def manifest(schema='puck-demonstration-v1', status='running'):
    mechanics = schema == 'puck-mechanics-v2'
    r = row(student='student' in schema)
    if mechanics:
        r.pop('split')
    value = {'schema': schema, 'protocol_sha256': PIN, 'pushing_protocol_sha256': PIN,
             'row': r, 'source': None, 'source_hashes': {'script.py': PIN},
             'profile_identity': {'kind': 'puck-profile-v5'}, 'full_model_sha256': PIN,
             'contact_ownership': {'geometries': [{'geom_id': 0, 'name': 'floor',
                 'body_id': 0, 'body_name': 'world', 'owner': 'world'}]},
             'record_contract': 'numeric', 'status': status,
             'recording_format': 'palimpsest-npz-v1', 'recording_max_bytes': 1000000}
    if not mechanics:
        value.update(seed=6000, split='train', episodes=1, initial_supervisor={'tick': 0})
    if 'student' in schema:
        value['model_identity'] = {'training_seed': 21, 'training_report_sha256': PIN,
                                  'checkpoint_sha256': PIN, 'protocol_sha256': PIN,
                                  'learning_protocol_sha256': PIN, 'supervisor_source_sha256': PIN}
    if 'development' in schema:
        value.update(development_protocol_sha256=PIN, initial_reference=None)
    return value


def report(status='running'):
    return {'status': status, 'commit': '0' * 40, 'learning_protocol_sha256': OTHER,
            'pushing_protocol_sha256': PIN, 'teacher_source_sha256': PIN,
            'supervisor_source_sha256': PIN, 'learning_feature_id': 'numeric-v1',
            'teacher_id': 'teacher-v1', 'source_hashes': {'script.py': PIN},
            'sources': [{'seed': 6000, 'split': 'train', 'path': '/retained/teacher/recording',
                         'manifest_sha256': None}],
            'owners': [{**row(), 'status': 'not_started'}],
            'admission': {'status': 'not_started', 'rows': [
                {'seed': 6000, 'split': 'train', 'status': 'not_started'}]},
            'qualification_claims': [], 'finalization_errors': []}


def training(schema='puck-training-v1'):
    return {'schema': schema, 'learning_protocol_sha256': OTHER, 'training_seed': 21,
            'learning': {'epochs': 30}, 'action_arithmetic': 'float64', 'checkpoint': 'NPZ',
            'collection_report': {'path': '/retained/teacher/report.json', 'sha256': PIN},
            'sources': [{'seed': 6000, 'split': 'train', 'ticks': 120,
                'manifest_sha256': PIN, 'source_hashes': {'manifest.json': PIN},
                'feature_sha256': PIN, 'target_sha256': PIN, 'path': '/retained/teacher/recording'}],
            'source_hashes': {'train.py': PIN}, 'limits': {}, 'runtime': {'python': '3.11'},
            'held_out_used': False, 'qualification_claims': [], 'scope': 'imitation only'}


def parse(document, kind='recording_manifest'):
    return parse_retained_puck_document(encoded(document), kind=kind)


def test_manifest_preserves_raw_identity_and_explicit_nonqualification():
    document = manifest()
    raw = encoded(document)
    result = parse_retained_puck_document(raw, kind='recording_manifest')
    assert result == {'kind': 'puck-retained-scene-references-v1',
        'document_kind': 'recording_manifest', 'document_sha256': hashlib.sha256(raw).hexdigest(),
        'document_bytes': len(raw), 'mentions': [
            {'scene_id': 6000, 'split': 'train', 'pointer': '/row/seed', 'catalog_sha256': PIN},
            {'scene_id': 6000, 'split': 'train', 'pointer': '/seed', 'catalog_sha256': PIN}],
        'references': [], 'missing_pins': [], 'held_out_mentions': False,
        'inventory_complete': False, 'source_closure_authenticated': False,
        'executable': False, 'qualification_claims': []}
    assert document == manifest()
    result['mentions'][0]['scene_id'] = 999
    assert parse(document)['mentions'][0]['scene_id'] == 6000


@pytest.mark.parametrize('schema', ['puck-mechanics-v2', 'puck-demonstration-v1',
    'puck-student-v1', 'puck-balanced-student-v1', 'puck-student-development-v1',
    'puck-balanced-student-development-v1'])
@pytest.mark.parametrize('status', ['running', 'completed', 'failed', 'not_started'])
def test_historical_manifest_families_preserve_scene_despite_status(schema, status):
    result = parse(manifest(schema, status))
    assert result['mentions'][0]['scene_id'] == 6000
    assert result['mentions'][0]['split'] == ('mechanics' if schema == 'puck-mechanics-v2' else 'train')
    assert all(m['scene_id'] != 21 for m in result['mentions'])


@pytest.mark.parametrize('changes', [{'seed': True}, {'seed': 6001}, {'seed': 6000.0},
    {'split': 'held_out'}, {'split': 1}, {'model_seed': True}])
def test_rejects_invalid_or_conflicting_manifest_redundant_scene(changes):
    value = manifest()
    value.update(changes)
    with pytest.raises(ValueError):
        parse(value)


def test_mechanics_rejects_explicit_conflicting_split():
    value = manifest('puck-mechanics-v2')
    value['row']['split'] = 'train'
    with pytest.raises(ValueError):
        parse(value)


@pytest.mark.parametrize('seed', [True, -1, 2**31, 1.0, '6000', None])
def test_rejects_non_scene_integer(seed):
    value = manifest()
    value['row']['seed'] = value['seed'] = seed
    with pytest.raises(ValueError):
        parse(value)


@pytest.mark.parametrize('status', ['running', 'failed', 'passed'])
def test_teacher_report_keeps_unpinned_sources_and_roster_mentions(status):
    result = parse(report(status), 'teacher_collection_report')
    assert [m['pointer'] for m in result['mentions']] == [
        '/sources/0/seed', '/owners/0/seed', '/admission/rows/0/seed']
    assert all(m['catalog_sha256'] == PIN for m in result['mentions'])
    assert result['references'] == [{'kind': 'recording_manifest',
        'path': '/retained/teacher/recording/manifest.json', 'sha256': None,
        'scene_id': 6000, 'split': 'train', 'pointer': '/sources/0'}]
    assert result['missing_pins'] == ['/sources/0/manifest_sha256']


def test_teacher_partial_admission_rows_are_retained():
    value = report()
    value['admission']['rows'] = []
    assert len(parse(value, 'teacher_collection_report')['mentions']) == 2


@pytest.mark.parametrize('container', ['owners', 'admission'])
def test_rejects_conflicting_teacher_rosters(container):
    value = report()
    rows = value['owners'] if container == 'owners' else value['admission']['rows']
    rows[0]['seed'] = 6001
    with pytest.raises(ValueError):
        parse(value, 'teacher_collection_report')


@pytest.mark.parametrize('schema', ['puck-training-v1', 'puck-balanced-training-v1'])
def test_training_model_seed_is_not_scene_and_references_report_file(schema):
    result = parse(training(schema), 'training_protocol')
    assert result['mentions'] == [
        {'scene_id': 6000, 'split': 'train', 'pointer': '/sources/0/seed', 'catalog_sha256': None}]
    assert result['references'] == [
        {'kind': 'teacher_collection_report', 'path': '/retained/teacher/report.json',
         'sha256': PIN, 'scene_id': None, 'split': None, 'pointer': '/collection_report'},
        {'kind': 'recording_manifest', 'path': '/retained/teacher/recording/manifest.json',
         'sha256': PIN, 'scene_id': 6000, 'split': 'train', 'pointer': '/sources/0'}]


def test_held_out_mentions_and_missing_catalog_pin_are_explicit():
    value = manifest()
    value['seed'] = value['row']['seed'] = 6100
    value['split'] = value['row']['split'] = 'held_out'
    value.pop('pushing_protocol_sha256')
    result = parse(value)
    assert result['held_out_mentions'] is True
    assert result['missing_pins'] == ['/pushing_protocol_sha256']
    assert all(m['catalog_sha256'] is None for m in result['mentions'])


@pytest.mark.parametrize('key,value', [('scene_id', 6000), ('seed', 6000), ('split', 'train'),
    ('layout', {}), ('rover_pose', [0, 0, 0]), ('puck_xy', [0, 0]), ('goal_xy', [0, 0]),
    ('geometry', {'puck': [0, 0]}), ('environment_seed', 6000)])
def test_rejects_unknown_nested_scene_or_geometry_declarations(key, value):
    document = manifest()
    document['extra'] = {'nested': {key: value}}
    with pytest.raises(ValueError):
        parse(document)


def test_source_snapshot_world_is_receipt_not_new_scene():
    value = manifest('puck-student-v1')
    value['source'] = {'file': 'tick1.snp', 'sha256': PIN, 'bytes': 100, 'tick': 1,
        'application_sha256': PIN, 'world': {'time_s': .02, 'rover_pose': [0, 0, 0],
            'puck_xyz': [1, 0, .062], 'puck_velocity_xy': [0, 0], 'goal_xy': [2, 0]},
        'contact': {'tick': 1}}
    assert len(parse(value)['mentions']) == 2
    value['source']['world']['seed'] = 6000
    with pytest.raises(ValueError):
        parse(value)


@pytest.mark.parametrize('path', ['../recording', 'a/../recording', './recording',
    'a//recording', '/recording/', 'https://example.test/recording', 'a\\recording', '', '/', 'a\x00b'])
def test_rejects_noncanonical_reference_paths(path):
    value = report()
    value['sources'][0]['path'] = path
    with pytest.raises(ValueError):
        parse(value, 'teacher_collection_report')


def test_relative_reference_preserves_ambiguous_origin():
    value = report()
    value['sources'][0]['path'] = 'retained/teacher/recording'
    assert parse(value, 'teacher_collection_report')['references'][0]['path'] == 'retained/teacher/recording/manifest.json'


@pytest.mark.parametrize('pin', [None, '', 'A' * 64, 'g' * 64, 1])
def test_present_catalog_pin_is_strict(pin):
    value = manifest()
    value['pushing_protocol_sha256'] = pin
    with pytest.raises(ValueError):
        parse(value)


@pytest.mark.parametrize('mutation', ['schema', 'source_extra', 'training_seed', 'missing_hash'])
def test_training_rejects_unsupported_or_unpinned_source_identity(mutation):
    value = training()
    if mutation == 'schema': value['schema'] = 'puck-training-v3'
    elif mutation == 'source_extra': value['sources'][0]['scene_id'] = 6000
    elif mutation == 'training_seed': value['training_seed'] = True
    else: value['sources'][0].pop('manifest_sha256')
    with pytest.raises(ValueError):
        parse(value, 'training_protocol')


@pytest.mark.parametrize('raw', [b'{"schema":"one","schema":"two"}', b'{"x":NaN}',
    b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":1e10000}', b'[]', b'\xff'])
def test_rejects_duplicate_keys_nonfinite_and_nonobject_json(raw):
    with pytest.raises(ValueError):
        parse_retained_puck_document(raw, kind='recording_manifest')


def test_kind_is_explicit_and_bytes_are_required():
    with pytest.raises(ValueError): parse_retained_puck_document(encoded(manifest()), kind='guess')
    with pytest.raises(ValueError): parse_retained_puck_document('{}', kind='recording_manifest')


def test_bounded_bytes_nodes_depth_and_mentions():
    with pytest.raises(ValueError):
        parse_retained_puck_document(b' ' * (4 * 1024**2 + 1), kind='recording_manifest')
    value = manifest()
    value['padding'] = [0] * 65536
    with pytest.raises(ValueError): parse(value)
    value = manifest()
    nested = {}
    value['padding'] = nested
    for _ in range(33):
        nested['x'] = {}; nested = nested['x']
    with pytest.raises(ValueError): parse(value)
    value = report()
    value['sources'] *= 1400
    value['owners'] *= 1400
    value['admission']['rows'] *= 1400
    with pytest.raises(ValueError): parse(value, 'teacher_collection_report')


def world():
    return {'time_s': .02, 'rover_pose': [0, 0, 0], 'puck_xyz': [1, 0, .062],
            'puck_velocity_xy': [0, 0], 'goal_xy': [2, 0]}


def state():
    return {'version': 1, 'protocol_sha256': PIN, 'episode_id': 'teacher-6000', 'tick': 1,
            'initial_puck_xy': [1, 0], 'previous_puck_xy': [1, 0],
            'previous_rover_xy': [0, 0], 'goal_xy': [2, 0], 'previous_distance': 1.,
            'had_contact': False, 'dwell_ticks': 0, 'stall_ticks': 0, 'reason': None}


def snapshot():
    return {'file': 'initial.snp', 'sha256': PIN, 'bytes': 100, 'tick': 0,
            'application_sha256': OTHER, 'world': world(), 'contact': {'tick': 0}}


def test_completed_teacher_embedded_result_rows_and_world_receipts_are_inventory_only():
    value = report('passed')
    value['sources'][0]['manifest_sha256'] = OTHER
    value['owners'][0].update(status='completed', outcome='puck_goal', result_sha256=PIN,
        result={'status': 'passed', 'row': row(), 'snapshots': {'initial': snapshot()},
            'source_snapshot': snapshot(), 'final_state': state(), 'final_world': world(),
            'ticks': 1, 'completed_control_tick': 1, 'controller_calls': 1,
            'cleanup': [], 'finalization_errors': [], 'qualification_claims': [],
            'profile_identity': {'kind': 'puck-profile-v5'}, 'full_model_sha256': PIN,
            'completion': 'puck_goal', 'max_puck_displacement_m': .3})
    value['admission']['rows'][0].update(status='passed', ticks=1)
    result = parse(value, 'teacher_collection_report')
    assert [m['pointer'] for m in result['mentions']] == ['/sources/0/seed',
        '/owners/0/seed', '/owners/0/result/row/seed', '/admission/rows/0/seed']
    assert result['qualification_claims'] == []
    assert result['source_closure_authenticated'] is False
    assert result['references'][0]['sha256'] == OTHER
    value['owners'][0]['result']['row']['split'] = 'held_out'
    with pytest.raises(ValueError):
        parse(value, 'teacher_collection_report')


def test_completed_manifest_task_coordinates_do_not_create_scene_geometry_hash():
    value = manifest(status='completed')
    value.update(final_state=state(), ticks=1, outcome=None, completion='fixed_mechanics_horizon')
    result = parse(value)
    assert len(result['mentions']) == 2
    assert not any('geometry' in key or 'layout_hash' in key for key in result)
    value['final_state']['unknown'] = {'goal_xy': [0, 0]}
    with pytest.raises(ValueError): parse(value)


@pytest.mark.parametrize('mutation', ['world_extra', 'missing_world', 'receipt_extra', 'bad_tick',
                                      'wrong_coords', 'nonfinite_coords'])
def test_snapshot_receipt_cannot_smuggle_reset_declarations(mutation):
    value = manifest('puck-student-v1')
    value['source'] = snapshot()
    receipt = value['source']
    if mutation == 'world_extra': receipt['world']['reset'] = {'seed': 6000}
    elif mutation == 'missing_world': receipt.pop('world')
    elif mutation == 'receipt_extra': receipt['geometry'] = {'puck_xy': [0, 0]}
    elif mutation == 'bad_tick': receipt['tick'] = True
    elif mutation == 'wrong_coords': receipt['world']['rover_pose'] = [0, 0]
    else: receipt['world']['goal_xy'] = [True, 0]
    with pytest.raises(ValueError): parse(value)


def test_model_aliases_must_agree_without_becoming_scene_mentions():
    value = manifest('puck-student-v1')
    value['model_identity']['training_seed'] = 22
    with pytest.raises(ValueError): parse(value)
    value['model_identity']['training_seed'] = True
    with pytest.raises(ValueError): parse(value)


@pytest.mark.parametrize('mutation', ['invented_schema', 'missing_lineage', 'invalid_lineage',
                                      'missing_owners', 'missing_rows', 'extra_source', 'missing_pin'])
def test_teacher_report_requires_actual_writer_lineage_and_source_shape(mutation):
    value = report()
    if mutation == 'invented_schema': value['schema'] = 'puck-teacher-report-v1'
    elif mutation == 'missing_lineage': value.pop('learning_protocol_sha256')
    elif mutation == 'invalid_lineage': value['learning_protocol_sha256'] = 'X' * 64
    elif mutation == 'missing_owners': value.pop('owners')
    elif mutation == 'missing_rows': value['admission'].pop('rows')
    elif mutation == 'extra_source': value['sources'][0]['ticks'] = 3
    else: value['sources'][0].pop('manifest_sha256')
    with pytest.raises(ValueError): parse(value, 'teacher_collection_report')


def test_nullable_training_references_retain_missing_pins_and_scene():
    value = training()
    value['collection_report']['sha256'] = None
    value['sources'][0]['manifest_sha256'] = None
    result = parse(value, 'training_protocol')
    assert result['missing_pins'] == ['/collection_report/sha256', '/sources/0/manifest_sha256']
    assert len(result['references']) == 2
    assert result['mentions'][0]['scene_id'] == 6000


@pytest.mark.parametrize('split', ['closed_loop_dev', 'recorded_dev', 'held_out'])
def test_historical_scene_splits_are_preserved(split):
    value = manifest()
    value['row']['split'] = value['split'] = split
    assert parse(value)['mentions'][0]['split'] == split


@pytest.mark.parametrize('split', ['v3_train', 'transfer', '', True])
def test_unsupported_scene_splits_fail_closed(split):
    value = manifest()
    value['row']['split'] = value['split'] = split
    with pytest.raises(ValueError): parse(value)


def test_exact_combined_mention_reference_limit_and_next_item():
    value = report()
    value['sources'] *= 1024
    value['owners'] *= 1024
    value['admission']['rows'] *= 1024
    result = parse(value, 'teacher_collection_report')
    assert len(result['mentions']) + len(result['references']) == 4096
    value['owners'][0]['result'] = {'row': row()}
    with pytest.raises(ValueError): parse(value, 'teacher_collection_report')


def test_json_pointer_escaping_keeps_unknown_declaration_location_unambiguous():
    value = manifest()
    value['a/b~c'] = {'seed': 6000}
    with pytest.raises(ValueError, match='/a~1b~0c/seed'): parse(value)


@pytest.mark.parametrize('pin', [None, '', 'A' * 64, True])
def test_training_optional_pushing_pin_is_still_strict(pin):
    value = training()
    value['pushing_protocol_sha256'] = pin
    with pytest.raises(ValueError): parse(value, 'training_protocol')


@pytest.mark.parametrize('ticks', [True, 1.5, -1, None])
def test_training_source_tick_receipt_is_strict_integer(ticks):
    value = training()
    value['sources'][0]['ticks'] = ticks
    with pytest.raises(ValueError): parse(value, 'training_protocol')


def test_training_source_hash_container_cannot_carry_invalid_hash():
    value = training()
    value['sources'][0]['source_hashes']['manifest.json'] = None
    with pytest.raises(ValueError): parse(value, 'training_protocol')


@pytest.mark.parametrize('declaration', ['scene_geometry', 'authored_scene_id', 'reset_geometry',
                                        'other_seed', 'layout_seed', 'sceneId', 'scene_ids'])
def test_unknown_scene_declaration_aliases_are_not_silently_ignored(declaration):
    value = manifest()
    value['extra'] = {declaration: 6000}
    with pytest.raises(ValueError): parse(value)


def test_manifest_schema_object_is_rejected_as_validation_error():
    value = manifest()
    value['schema'] = {}
    with pytest.raises(ValueError): parse(value)


@pytest.mark.parametrize('key', ['scene.id', 'authored.scene_id', 'reset-geometry', 'namespace/seed'])
def test_punctuation_cannot_hide_scene_declarations(key):
    value = manifest()
    value['extra'] = {key: 6000}
    with pytest.raises(ValueError): parse(value)


def test_actual_source_hash_file_names_are_hash_receipts_not_scene_declarations():
    value = manifest()
    value['source_hashes']['src/palimpsest/scene_seed.py'] = PIN
    assert len(parse(value)['mentions']) == 2
    value['source_hashes']['src/palimpsest/scene_seed.py'] = {'seed': 6000}
    with pytest.raises(ValueError): parse(value)


def test_huge_coordinate_integer_is_rejected_without_overflow_exception():
    value = manifest('puck-student-v1')
    value['source'] = snapshot()
    value['source']['world']['goal_xy'][0] = 10**1000
    with pytest.raises(ValueError): parse(value)


def test_matching_explicit_mechanics_split_needs_no_invented_top_scene():
    value = manifest('puck-mechanics-v2')
    value['split'] = 'mechanics'
    value['row']['split'] = 'mechanics'
    result = parse(value)
    assert result['mentions'] == [{'scene_id': 6000, 'split': 'mechanics',
        'pointer': '/row/seed', 'catalog_sha256': PIN}]
    value['split'] = 'train'
    with pytest.raises(ValueError): parse(value)


@pytest.mark.parametrize('kind', ['recording_manifest', 'teacher_collection_report'])
@pytest.mark.parametrize('catalog_path', ['docs/plans/m6-puck-pushing-protocol.json',
    'docs/plans/m6-puck-pushing-protocol-v1.json', 'docs/plans/m6-puck-pushing-protocol-v5.json'])
def test_root_source_hash_catalog_receipt_must_agree_with_pushing_pin(kind, catalog_path):
    value = manifest() if kind == 'recording_manifest' else report()
    value['source_hashes'][catalog_path] = OTHER
    with pytest.raises(ValueError): parse(value, kind)
    value['source_hashes'][catalog_path] = PIN
    assert all(item['catalog_sha256'] == PIN for item in parse(value, kind)['mentions'])


def test_mechanics_source_hash_catalog_pin_conflict_is_rejected():
    value = manifest('puck-mechanics-v2')
    value['source_hashes']['docs/plans/m6-puck-pushing-protocol-v5.json'] = OTHER
    with pytest.raises(ValueError): parse(value)


@pytest.mark.parametrize('kind', ['recording_manifest', 'teacher_collection_report'])
def test_historical_base_and_matching_versioned_catalog_receipts_are_preserved(kind):
    value = manifest() if kind == 'recording_manifest' else report()
    value['source_hashes'].update({'docs/plans/m6-puck-pushing-protocol.json': OTHER,
                                 'docs/plans/m6-puck-pushing-protocol-v5.json': PIN})
    assert parse(value, kind)['mentions'][0]['catalog_sha256'] == PIN
    value['source_hashes']['docs/plans/m6-puck-pushing-protocol-v5.json'] = OTHER
    with pytest.raises(ValueError): parse(value, kind)


def test_source_hash_receipts_do_not_invent_missing_top_catalog_pin():
    value = manifest('puck-mechanics-v2')
    value.pop('pushing_protocol_sha256')
    value['source_hashes']['docs/plans/m6-puck-pushing-protocol-v5.json'] = PIN
    result = parse(value)
    assert result['missing_pins'] == ['/pushing_protocol_sha256']
    assert result['mentions'][0]['catalog_sha256'] is None
    value['source_hashes']['docs/plans/m6-puck-pushing-protocol-v4.json'] = OTHER
    result = parse(value)
    assert result['missing_pins'] == ['/pushing_protocol_sha256']
    assert result['mentions'][0]['catalog_sha256'] is None


def test_mechanics_accepts_matching_catalog_alongside_historical_base_hash():
    value = manifest('puck-mechanics-v2')
    value['source_hashes'].update({'docs/plans/m6-puck-pushing-protocol.json': OTHER,
                                 'docs/plans/m6-puck-pushing-protocol-v5.json': PIN})
    result = parse(value)
    assert result['mentions'][0]['catalog_sha256'] == PIN
    assert result['source_closure_authenticated'] is False


def test_root_helper_hashes_and_training_record_hashes_are_not_catalog_aliases():
    value = report()
    value['source_hashes'].update({'src/palimpsest/puck_profile.py': OTHER,
        'docs/plans/m6-puck-pushing-protocol-v6.json': OTHER,
        'unrelated/docs/plans/m6-puck-pushing-protocol-v5.json': OTHER})
    assert parse(value, 'teacher_collection_report')['mentions'][0]['catalog_sha256'] == PIN
    value = training()
    value['sources'][0]['source_hashes']['docs/plans/m6-puck-pushing-protocol-v5.json'] = OTHER
    assert parse(value, 'training_protocol')['mentions'][0]['catalog_sha256'] is None
