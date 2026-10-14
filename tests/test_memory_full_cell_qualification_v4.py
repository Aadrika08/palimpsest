"""Authored metadata and numeric endpoint tests; never consume retained inputs."""
import copy
import importlib
import importlib.util

import numpy as np
import pytest

from palimpsest import snapshots


def module():
    name = 'scripts.qualify_memory_full_cell_v4'
    assert importlib.util.find_spec(name) is not None, 'Full-model qualification runner is missing'
    return importlib.import_module(name)


def test_metadata_selection_retains_all_three_exact_indexed_trees():
    m = module()
    files = []
    for run in m.RUNS:
        for leaf in ('owner.json', 'recording/manifest.json'):
            files.append({'source': '/original/runs/' + run + '/' + leaf,
                          'member': 'output/stage/runs/' + run + '/' + leaf,
                          'bytes': 2, 'sha256': 'a' * 64, 'included': True})
    files.append({'source': '/original/runs/other/owner.json', 'member': 'other',
                  'bytes': 2, 'sha256': 'b' * 64, 'included': True})
    selected = m._selected_raw_descriptors({'files': files}, '/original/runs')
    assert len(selected) == 6
    assert all('/other/' not in row['path'] for row in selected)
    assert {row['path'].split('/')[0] for row in selected} == set(m.RUNS)


@pytest.mark.parametrize('defect', ['missing-role', 'duplicate', 'escape', 'mixed-root'])
def test_metadata_selection_refuses_missing_or_ambiguous_origin(defect):
    m = module()
    files = [{'source': '/original/runs/' + run + '/owner.json',
              'member': 'output/stage/runs/' + run + '/owner.json',
              'bytes': 2, 'sha256': 'a' * 64, 'included': True} for run in m.RUNS]
    if defect == 'missing-role': files.pop()
    elif defect == 'duplicate': files.append(copy.deepcopy(files[0]))
    elif defect == 'escape': files[0]['source'] = '/original/runs/' + m.RUNS[0] + '/../escape'
    else: files[0]['source'] = '/elsewhere/' + m.RUNS[0] + '/owner.json'
    with pytest.raises(ValueError): m._selected_raw_descriptors({'files': files}, '/original/runs')


def test_authentic_post_repeat_endpoint_must_match_computed_hidden():
    m = module()
    hidden = np.array([[1., 2.]], np.float32)
    proof = {'final_hidden_sha256': snapshots.state_digest(hidden)}
    m._endpoint(proof, {'policy': {'hidden': hidden}})
    with pytest.raises(ValueError):
        m._endpoint(proof, {'policy': {'hidden': hidden + 1}})


@pytest.mark.parametrize('kind', ['encoded-input', 'raw-output', 'initial-hidden'])
def test_prescribed_negative_is_separate_from_original_bytes(kind):
    m = module()
    rows = [{'episode': 0, 'tick': tick, 'encoded_input': np.zeros(3, np.float32),
             'raw_output': np.zeros(2, np.float32), 'action': np.zeros(2, np.float32)}
            for tick in range(711)]
    snapshot = {'policy': {'hidden': np.zeros((1, 4), np.float32)}}
    before = snapshots.state_digest({'rows': rows, 'snapshot': snapshot})
    modified_rows, modified_snapshot = m._negative_copy(kind, rows, snapshot)
    assert snapshots.state_digest({'rows': rows, 'snapshot': snapshot}) == before
    if kind == 'encoded-input':
        assert np.array_equal(modified_rows[710]['encoded_input'], np.full(3, 100, np.float32))
    elif kind == 'raw-output':
        assert np.array_equal(modified_rows[0]['raw_output'], np.full(2, 100, np.float32))
    else:
        assert np.array_equal(modified_snapshot['policy']['hidden'], np.full((1, 4), 100, np.float32))
