"""Catalog occurrence assembly from authored bytes and temporary Git only."""
import copy
import hashlib
import importlib
import json
import time

import pytest

from test_puck_scene_catalog import catalog, raw


def subject():
    value = importlib.import_module('palimpsest.puck_scene_catalog')
    assert hasattr(value, 'assemble_task_catalog_occurrences'), 'Catalog occurrence assembly missing'
    return value


def document(value=None, *, commit='1', path='docs/tasks/puck.json', algorithm='sha1'):
    payload = raw(catalog() if value is None else value)
    oid = hashlib.new(algorithm, b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
    size = 40 if algorithm == 'sha1' else 64
    return {'repository': '/authored/repository', 'object_format': algorithm,
            'commit': commit * size, 'root_tree': '2' * size, 'path': path,
            'oid': oid, 'mode': '100644', 'raw': payload}


def assemble(values, **kwargs):
    return subject().assemble_task_catalog_occurrences(values,
        deadline=kwargs.get('deadline', time.monotonic() + 10))


def test_repeated_catalogs_preserve_each_occurrence_without_duplicate_scene_rows():
    values = [document(commit='1'), document(commit='3', path='historical/puck.json')]
    before = copy.deepcopy(values)
    result = assemble(values)
    assert values == before
    assert [row['scene_id'] for row in result['variants']] == [5100, 6000, 6200]
    assert [len(row['occurrences']) for row in result['variants']] == [2, 2, 2]
    train = result['variants'][1]
    assert {row['commit'] for row in train['occurrences']} == {'1' * 40, '3' * 40}
    assert {row['pointer'] for row in train['occurrences']} == {'/layouts/0'}
    assert result['id_variants'] == [] and result['identity_aliases'] == []
    assert result['legacy_scene_rows_compatible'] is True
    assert result['held_out_catalog_read'] is True
    for key in ('inventory_complete', 'source_closure_authenticated', 'executable',
                'reservation_authorized', 'held_out_runtime_opened', 'collection_authorized'):
        assert result[key] is False
    assert result['qualification_claims'] == []
    assert result['document_occurrences'] == 2 and result['scene_occurrences'] == 6
    assert b'rover_pose' not in json.dumps(result).encode()
    assert assemble(list(reversed(values))) == result


def test_same_id_geometry_variants_are_retained_and_report_v1_incompatibility():
    altered = catalog(); altered['layouts'][0]['goal_xy'][0] = 1.75
    result = assemble([document(), document(altered, commit='3')])
    assert len(result['variants']) == 4
    assert result['id_variants'] == [{'scene_id': 6000, 'variant_indices': [1, 2]}]
    assert result['legacy_scene_rows_compatible'] is False
    assert sum(len(row['occurrences']) for row in result['variants']) == 6


def test_different_id_same_geometry_keeps_payload_and_reports_identity_aliases():
    altered = catalog(); altered['layouts'][0]['seed'] = 6001
    result = assemble([document(), document(altered, commit='3')])
    assert len(result['variants']) == 4 and result['id_variants'] == []
    aliases = result['identity_aliases']
    assert {row['field'] for row in aliases} == {'canonical_scene_sha256', 'scientific_initial_sha256'}
    assert all(row['variant_indices'] == [1, 2] for row in aliases)
    assert result['variants'][1]['payload_sha256'] != result['variants'][2]['payload_sha256']
    assert result['legacy_scene_rows_compatible'] is False


def test_same_geometry_and_id_different_payload_is_not_silently_discarded():
    altered = catalog(); altered['layouts'][0]['rover_pose'] = [-1.0, 0.0, 0.0]
    result = assemble([document(), document(altered, commit='3')])
    assert len(result['variants']) == 4
    assert result['id_variants'] == [{'scene_id': 6000, 'variant_indices': [1, 2]}]
    assert len(result['identity_aliases']) == 2
    assert result['legacy_scene_rows_compatible'] is False


@pytest.mark.parametrize('algorithm', ['sha1', 'sha256'])
def test_actual_blob_frame_binding_supports_both_git_object_formats(algorithm):
    doc = document(algorithm=algorithm)
    result = assemble([doc])
    assert result['variants'][1]['occurrences'][0]['oid'] == doc['oid']
    assert result['variants'][1]['occurrences'][0]['document_sha256'] == hashlib.sha256(doc['raw']).hexdigest()
    doc['oid'] = hashlib.new(algorithm, doc['raw']).hexdigest()
    with pytest.raises(ValueError, match='blob'): assemble([doc])


@pytest.mark.parametrize('defect', ['unknown-key', 'missing-key', 'oid', 'commit', 'tree',
    'mode', 'format', 'repository', 'path', 'path-traversal', 'raw-type', 'raw-schema', 'duplicate'])
def test_unbound_or_ambiguous_catalog_occurrences_refuse(defect):
    doc = document()
    if defect == 'unknown-key': doc['complete'] = True
    elif defect == 'missing-key': del doc['root_tree']
    elif defect == 'oid': doc['oid'] = '0' * 40
    elif defect == 'commit': doc['commit'] = 'A' * 40
    elif defect == 'tree': doc['root_tree'] = '2' * 64
    elif defect == 'mode': doc['mode'] = '120000'
    elif defect == 'format': doc['object_format'] = 'md5'
    elif defect == 'repository': doc['repository'] = '/authored/../repository'
    elif defect == 'path': doc['path'] = 'docs/puck.md'
    elif defect == 'path-traversal': doc['path'] = '../puck.json'
    elif defect == 'raw-type': doc['raw'] = bytearray(doc['raw'])
    elif defect == 'raw-schema': doc = document({'id': 'unsupported', 'version': 1})
    values = [doc, copy.deepcopy(doc)] if defect == 'duplicate' else [doc]
    with pytest.raises(ValueError): assemble(values)


def test_conflicting_document_at_same_commit_and_path_is_not_another_occurrence():
    altered = catalog(); altered['layouts'][0]['goal_xy'][0] = 1.75
    with pytest.raises(ValueError): assemble([document(), document(altered)])


@pytest.mark.parametrize('deadline', [True, -1, float('nan'), float('inf')])
def test_invalid_or_expired_deadline_refuses(deadline):
    with pytest.raises((ValueError, TimeoutError)): assemble([document()], deadline=deadline)


def test_empty_or_unbounded_input_refuses():
    for values in ([], {}, [document()] * 4097):
        with pytest.raises(ValueError): assemble(values)


def test_output_mutation_cannot_change_a_later_result():
    docs = [document()]
    first = assemble(docs)
    first['variants'][1]['occurrences'].clear()
    assert len(assemble(docs)['variants'][1]['occurrences']) == 1


def test_actual_temporary_git_discovery_to_explicit_read_to_catalog_assembly(tmp_path):
    from test_puck_scene_git import git, held
    repo = tmp_path / 'repo'; remote = tmp_path / 'remote.git'
    repo.mkdir(); remote.mkdir()
    git(repo, 'init', '-q', '--initial-branch=main')
    (repo / 'puck.json').write_bytes(raw(catalog()))
    git(repo, 'add', '.'); git(repo, 'commit', '-qm', 'authored task')
    git(remote, 'init', '-q', '--bare')
    git(repo, 'remote', 'add', 'origin', str(remote)); git(repo, 'push', '-q', 'origin', 'main')
    with held(repo, remote) as sources:
        observation = sources.snapshot()
        assert observation['read_records'] == []
        documents = [dict(row, repository=str(repo), object_format=observation['object_format'],
                          raw=sources.read_blob(row['oid'])) for row in observation['documents']]
        result = assemble(documents)
        assert [row['scene_id'] for row in result['variants']] == [5100, 6000, 6200]
        assert result['source_closure_authenticated'] is False
        sources.recheck()


def test_one_commit_cannot_claim_two_root_trees_across_document_paths():
    first = document(); second = document(path='other/puck.json')
    second['root_tree'] = '3' * 40
    with pytest.raises(ValueError): assemble([first, second])


def test_one_repository_cannot_claim_conflicting_git_object_formats():
    with pytest.raises(ValueError): assemble([document(), document(algorithm='sha256')])


@pytest.mark.parametrize('cap', ['_MAX_DOCUMENT_OCCURRENCES', '_MAX_VARIANTS',
    '_MAX_SCENE_OCCURRENCES', '_MAX_OCCURRENCE_INPUT_BYTES', '_MAX_OCCURRENCE_METADATA_BYTES'])
def test_source_work_bounds_prevent_partial_success(monkeypatch, cap):
    monkeypatch.setattr(subject(), cap, 0)
    with pytest.raises(ValueError): assemble([document()])


def test_deadline_expiry_during_parser_cannot_return_a_receipt(monkeypatch):
    value = subject(); original = value.parse_task_catalog
    def expired(raw_bytes):
        result = original(raw_bytes)
        time.sleep(.02)
        return result
    monkeypatch.setattr(value, 'parse_task_catalog', expired)
    with pytest.raises(TimeoutError): assemble([document()], deadline=time.monotonic() + .01)
