"""Authored source-shaped metadata; no native or retained input reads."""
import hashlib
import importlib
import json

import pytest

PIN = 'a' * 64
OTHER = 'b' * 64


def parse(value, kind='owner_result'):
    try:
        module = importlib.import_module('palimpsest.puck_scene_reports')
    except ModuleNotFoundError:
        pytest.fail('The pure report inventory API is not implemented')
    return module.parse_puck_report_document(json.dumps(value).encode(), kind=kind)


def row(seed=6000, split='closed_loop_dev', model_seed=21):
    value = {'id': f'student-dev-{seed}-seed{model_seed}',
        'case': f'student-dev-{seed}-seed{model_seed}', 'kind': 'root',
        'seed': seed, 'max_ticks': 600, 'max_bytes': 1000000}
    if split is not None:
        value['split'] = split
    if model_seed is not None:
        value['model_seed'] = model_seed
    return value


def world():
    return {'time_s': 0., 'rover_pose': [0., 0., 0.], 'puck_xyz': [1., 0., .062],
            'puck_velocity_xy': [0., 0.], 'goal_xy': [2., 0.]}


def state():
    return {'version': 1, 'protocol_sha256': PIN, 'episode_id': 'example', 'tick': 0,
        'initial_puck_xy': [1., 0.], 'previous_puck_xy': [1., 0.],
        'previous_rover_xy': [0., 0.], 'goal_xy': [2., 0.], 'previous_distance': 1.,
        'had_contact': False, 'dwell_ticks': 0, 'stall_ticks': 0, 'reason': None}


def snapshot():
    return {'file': 'initial.snp', 'sha256': PIN, 'bytes': 30, 'tick': 0,
        'application_sha256': OTHER, 'world': world(), 'contact': {'tick': 0}}


def owner_result(model_seed=21):
    return {'status': 'failed', 'row': row(model_seed=model_seed), 'snapshots': {},
        'cleanup': [], 'finalization_errors': [], 'qualification_claims': [],
        'model_calls': 0, 'student_identity': {'pushing_protocol_sha256': PIN,
            'model_identity': {'training_seed': model_seed, 'checkpoint_sha256': PIN}}}


def mechanics_report():
    r = row(5990, None, None)
    return {'status': 'failed', 'commit': '0' * 40, 'protocol_sha256': OTHER,
        'protocol': {'pushing_protocol_sha256': PIN, 'environment_kwargs': {'seed': 999},
                     'owner_order': [r['id']]},
        'sources': {'docs/plans/m6-puck-pushing-protocol.json': OTHER,
                    'docs/plans/m6-puck-pushing-protocol-v5.json': PIN},
        'owners': [{**r, 'status': 'not_started'}], 'qualification_claims': [],
        'finalization_errors': []}


def development_report():
    return {'status': 'failed', 'commit': '0' * 40, 'development_protocol_sha256': OTHER,
        'source_hashes': {'script.py': PIN},
        'models': {'21': {'training_seed': 21, 'checkpoint_sha256': PIN}},
        'owners': [{**row(), 'status': 'not_started'}], 'admission': {'status': 'not_started'},
        'held_out': 'locked', 'qualification_claims': [], 'finalization_errors': []}


def test_standalone_failed_student_preserves_scene_without_model_seed_mention():
    value = owner_result()
    result = parse(value)
    assert result['mentions'] == [{'scene_id': 6000, 'split': 'closed_loop_dev',
        'pointer': '/row/seed', 'catalog_sha256': PIN}]
    assert result['references'] == []
    assert result['executable'] is result['source_closure_authenticated'] is False
    assert value == owner_result()


def test_mechanics_keeps_unstarted_rows_and_true_catalog_pin():
    result = parse(mechanics_report(), 'mechanics_report')
    assert result['mentions'] == [{'scene_id': 5990, 'split': 'mechanics',
        'pointer': '/owners/0/seed', 'catalog_sha256': PIN}]


def test_mechanics_verifier_pin_does_not_become_catalog():
    value = mechanics_report()
    value['protocol'].pop('pushing_protocol_sha256')
    result = parse(value, 'mechanics_report')
    assert result['mentions'][0]['catalog_sha256'] is None
    assert '/protocol/pushing_protocol_sha256' in result['missing_pins']


def test_development_source_receipts_do_not_promote_catalog():
    value = development_report()
    value['source_hashes']['docs/plans/m6-puck-pushing-protocol-v5.json'] = PIN
    value['admission'] = {'status': 'failed', 'goals_each_model': {'21': 1},
        'required_each_model': 3, 'held_out': 'locked_pending_review'}
    result = parse(value, 'development_report')
    assert [(m['scene_id'], m['catalog_sha256']) for m in result['mentions']] == [(6000, None)]
    assert result['missing_pins'] == []


def test_report_result_refs_and_local_nested_catalog_binding():
    value = development_report()
    value['owners'][0].update(output='retained/scene21', result_sha256=PIN,
        manifest_sha256=OTHER, result=owner_result())
    result = parse(value, 'development_report')
    assert [m['catalog_sha256'] for m in result['mentions']] == [None, PIN]
    assert result['references'] == [
        {'kind': 'owner_result', 'path': 'retained/scene21/result.json', 'sha256': PIN,
         'scene_id': 6000, 'split': 'closed_loop_dev', 'pointer': '/owners/0', 'path_base': 'recorded_cwd'},
        {'kind': 'recording_manifest', 'path': 'retained/scene21/recording/manifest.json',
         'sha256': OTHER, 'scene_id': 6000, 'split': 'closed_loop_dev', 'pointer': '/owners/0',
         'path_base': 'recorded_cwd'}]


def test_standalone_snapshot_is_validated_without_json_reference():
    value = owner_result()
    value.update(snapshots={'initial': snapshot()}, final_world=world(), final_state=state())
    result = parse(value)
    assert result['references'] == []


def test_report_baseline_result_ref_uses_declared_output_without_snp_json_ref():
    value = development_report()
    current = owner_result(22)
    current['snapshots'] = {'initial': snapshot()}
    current['initial_match'] = {'status': 'failed', 'reference': {
        'owner_id': 'student-dev-6000-seed21', 'result_sha256': PIN, 'snapshot_sha256': OTHER}}
    value['owners'] = [{**row(model_seed=22), 'status': 'failed',
        'output': '/retained/student-dev-6000-seed22', 'result': current, 'result_sha256': PIN}]
    refs = parse(value, 'development_report')['references']
    assert [(r['kind'], r['path'], r['sha256']) for r in refs] == [
        ('owner_result', '/retained/student-dev-6000-seed22/result.json', PIN),
        ('owner_result', '/retained/student-dev-6000-seed21/result.json', PIN)]
    assert refs[-1]['expected_owner_id'] == 'student-dev-6000-seed21'
    assert refs[-1]['expected_snapshot_sha256'] == OTHER


def test_scientific_fingerprint_world_keys_are_hash_receipts():
    value = owner_result()
    fields = {k: PIN for k in ('native_identity', 'full_model_sha256', 'profile',
        'integration', 'environment', 'world', 'contact', 'task', 'sensors8',
        'inputs9', 'own_cursor', 'rng')}
    value['initial_match'] = {'status': 'passed', 'reference': None,
        'fingerprint': {'sha256': PIN, 'fields': fields}}
    assert len(parse(value)['mentions']) == 1


def test_construction_layout_alias_is_scene_and_task_state_is_geometry():
    value = {'status': 'failed', 'protocol_sha256': OTHER, 'protocol': {
        'layout_seed': 5990, 'layout_split': 'mechanics', 'environment_kwargs': {'seed': 999}},
        'sources': {'script.py': PIN}, 'owners': [{'id': 'fresh-a', 'status': 'failed',
            'output': '/retained/fresh-a', 'result_sha256': PIN,
            'result': {'status': 'failed', 'task_state': state(), 'cameras': {}}}]}
    result = parse(value, 'construction_report')
    assert [(m['scene_id'], m['split']) for m in result['mentions']] == [(5990, 'mechanics')]
    assert result['references'][0]['kind'] == 'construction_result'


def test_standalone_construction_result_inventories_no_scene():
    value = {'status': 'passed', 'task_state': state(), 'full_native_model': {'sha256': PIN, 'bytes': 1},
        'full_native_data': {'sha256': OTHER, 'bytes': 1}, 'cameras': {'overhead': {'sha256': PIN, 'bytes': 1}}}
    assert parse(value, 'construction_result')['mentions'] == []


@pytest.mark.parametrize('mutation', ['row', 'model', 'models_key', 'baseline', 'catalog'])
def test_rejects_conflicting_aliases(mutation):
    value = development_report()
    value['owners'][0]['result'] = owner_result()
    if mutation == 'row':
        value['owners'][0]['result']['row']['seed'] = 6001
    elif mutation == 'model':
        value['owners'][0]['result']['student_identity']['model_identity']['training_seed'] = 22
    elif mutation == 'models_key':
        value['models']['21']['training_seed'] = 22
    elif mutation == 'baseline':
        value['owners'][0]['result']['initial_match'] = {'status': 'failed', 'reference': {
            'owner_id': 'student-dev-6001-seed21', 'result_sha256': PIN, 'snapshot_sha256': PIN}}
    else:
        value['pushing_protocol_sha256'] = OTHER
    with pytest.raises(ValueError):
        parse(value, 'development_report')


@pytest.mark.parametrize('kind', ['owner_result', 'construction_result', 'mechanics_report',
                                 'construction_report', 'development_report'])
def test_rejects_unknown_scene_declarations_everywhere(kind):
    value = owner_result() if kind == 'owner_result' else {'status': 'failed'}
    if kind == 'mechanics_report':
        value = mechanics_report()
    elif kind == 'development_report':
        value = development_report()
    elif kind == 'construction_report':
        value.update(protocol={'layout_seed': 5990, 'layout_split': 'mechanics'}, owners=[])
    value['extra'] = {'SceneIDs': [6000]}
    with pytest.raises(ValueError):
        parse(value, kind)


def test_random_seed_exception_is_scoped_to_environment_kwargs():
    value = mechanics_report()
    value['protocol']['random_seed'] = 999
    with pytest.raises(ValueError):
        parse(value, 'mechanics_report')


def test_duplicate_json_and_nonfinite_are_rejected():
    module = importlib.import_module('palimpsest.puck_scene_reports')
    for raw in (b'{"status":"failed","status":"passed"}', b'{"x":NaN}'):
        with pytest.raises(ValueError):
            module.parse_puck_report_document(raw, kind='construction_result')


def test_nullable_result_pin_is_preserved():
    value = development_report()
    value['owners'][0].update(output='retained/owner', result_sha256=None)
    result = parse(value, 'development_report')
    assert result['references'][0]['sha256'] is None
    assert '/owners/0/result_sha256' in result['missing_pins']


def test_result_preserves_exact_raw_identity():
    value = owner_result()
    raw = json.dumps(value).encode()
    result = parse(value)
    assert result['document_sha256'] == hashlib.sha256(raw).hexdigest()
    assert result['document_bytes'] == len(raw)


def test_manifest_receipt_without_output_keeps_missing_context():
    value = development_report()
    value['owners'][0]['manifest_sha256'] = PIN
    result = parse(value, 'development_report')
    assert '/owners/0/output' in result['missing_pins']
    assert result['references'] == []


def test_manifest_receipt_without_output_still_validates_hash():
    value = development_report()
    value['owners'][0]['manifest_sha256'] = 'invalid'
    with pytest.raises(ValueError):
        parse(value, 'development_report')


def test_standalone_baseline_does_not_infer_current_working_directory():
    value = owner_result(22)
    value['initial_match'] = {'status': 'failed', 'reference': {
        'owner_id': 'student-dev-6000-seed21', 'result_sha256': None, 'snapshot_sha256': PIN}}
    result = parse(value)
    assert result['references'] == []
    assert result['missing_pins'] == ['/initial_match/reference/path',
                                      '/initial_match/reference/result_sha256']


@pytest.mark.parametrize('where', ['snapshot', 'fingerprint', 'model', 'protocol_rng'])
def test_hash_and_model_exceptions_do_not_hide_untyped_declarations(where):
    value = owner_result()
    if where == 'snapshot':
        value['snapshots']['initial'] = snapshot()
        value['snapshots']['initial']['contact']['scene_seed'] = 6000
    elif where == 'fingerprint':
        value['initial_match'] = {'status': 'failed', 'reference': None,
            'fingerprint': {'sha256': PIN, 'fields': {'scene_id': PIN}}}
    elif where == 'model':
        value['student_identity']['model_identity']['layout_seed'] = 6000
    else:
        value = mechanics_report()
        value['protocol']['environment_kwargs']['scene_id'] = 6000
    with pytest.raises(ValueError):
        parse(value, 'mechanics_report' if where == 'protocol_rng' else 'owner_result')


def test_report_nested_result_scene_cannot_change_held_out_membership():
    value = development_report()
    value['owners'][0]['result'] = owner_result()
    value['owners'][0]['result']['row']['split'] = 'held_out'
    with pytest.raises(ValueError):
        parse(value, 'development_report')


def test_held_out_result_remains_inventoried_without_qualification():
    value = owner_result()
    value['row']['split'] = 'held_out'
    result = parse(value)
    assert result['held_out_mentions'] is True
    assert result['inventory_complete'] is result['executable'] is False


def test_malformed_snapshot_world_and_model_boolean_are_rejected():
    value = owner_result()
    value['snapshots']['initial'] = snapshot()
    value['snapshots']['initial']['world']['goal_xy'] = [1.]
    with pytest.raises(ValueError):
        parse(value)
    value = owner_result()
    value['student_identity']['model_identity']['training_seed'] = True
    with pytest.raises(ValueError):
        parse(value)


def test_catalogless_plain_result_does_not_invent_a_mandatory_catalog_field():
    value = owner_result()
    value.pop('student_identity')
    result = parse(value)
    assert result['mentions'][0]['catalog_sha256'] is None
    assert result['missing_pins'] == []
