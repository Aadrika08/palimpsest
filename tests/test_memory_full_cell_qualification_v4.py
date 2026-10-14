"""Authored metadata and numeric endpoint tests; never consume retained inputs."""
import copy
import importlib
import importlib.util
import sys
import time
import os

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


def test_actual_qualification_supervisor_drains_and_bounds_logs(tmp_path):
    m = module()
    now = time.monotonic()
    result = m._supervised([sys.executable, '-c', "print('qualified fixture')"], tmp_path,
                           normal_deadline=now + 5, hard_deadline=now + 6,
                           min_free_bytes=0)
    assert result['status'] == 'completed'
    assert result['returncode'] == 0
    assert result['matching_survivors'] == []
    assert (tmp_path / 'stdout.log').read_bytes() == b'qualified fixture\n'


def test_qualification_supervisor_kills_overdue_owned_process(tmp_path):
    m = module()
    now = time.monotonic()
    result = m._supervised([sys.executable, '-c', 'import time;time.sleep(10)'], tmp_path,
                           normal_deadline=now + .05, hard_deadline=now + 1,
                           min_free_bytes=0)
    assert result['status'] == 'failed'
    assert result['matching_survivors'] == []
    assert result['failure'] == 'normal-return deadline'


def test_supervisor_refuses_already_exited_worker_observed_after_deadlines(tmp_path, monkeypatch):
    m = module()
    real_popen = m.subprocess.Popen
    def launch(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        # Simulate the monitor being descheduled until its real child has exited.
        process.wait(timeout=5)
        time.sleep(.03)
        return process
    monkeypatch.setattr(m.subprocess, 'Popen', launch)
    now = time.monotonic()
    result = m._supervised([sys.executable, '-c', 'pass'], tmp_path,
                           normal_deadline=now + .005, hard_deadline=now + .01,
                           min_free_bytes=0)
    assert result['status'] == 'failed'
    assert result['failure'] == 'hard deadline'
    assert result['returncode'] == 0
    assert result['matching_survivors'] == []


def test_supervisor_includes_final_log_drain_in_return_deadline(tmp_path, monkeypatch):
    from contextlib import contextmanager
    from palimpsest.evaluate import bounded_logs
    m = module()
    real_logs = bounded_logs
    deadline = time.monotonic() + .3
    @contextmanager
    def delayed_logs(*args, **kwargs):
        with real_logs(*args, **kwargs) as streams:
            yield streams
        # The worker is successful; only final drainage misses normal return.
        time.sleep(max(0, deadline - time.monotonic()) + .01)
    monkeypatch.setattr('palimpsest.evaluate.bounded_logs', delayed_logs)
    result = m._supervised([sys.executable, '-c', "print('fixture')"], tmp_path,
                           normal_deadline=deadline, hard_deadline=deadline + 3,
                           min_free_bytes=0)
    assert result['status'] == 'failed'
    assert result['failure'] == 'normal-return deadline'
    assert result['matching_survivors'] == []


def test_supervisor_monitor_error_cannot_leave_its_worker_running(tmp_path, monkeypatch):
    m = module()
    spawned = []
    real_popen = m.subprocess.Popen
    real_members = m._group_members
    def launch(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        spawned.append(process.pid)
        return process
    count = [0]
    def failed(group):
        count[0] += 1
        if count[0] == 1:
            raise RuntimeError('injected proc monitor failure')
        return real_members(group)
    monkeypatch.setattr(m.subprocess, 'Popen', launch)
    monkeypatch.setattr(m, '_group_members', failed)
    now = time.monotonic()
    try:
        with pytest.raises(RuntimeError):
            m._supervised([sys.executable, '-c', 'import time;time.sleep(10)'], tmp_path,
                          normal_deadline=now + 5, hard_deadline=now + 6, min_free_bytes=0)
        with pytest.raises(ProcessLookupError):
            os.kill(spawned[0], 0)
    finally:
        # The failing RED must itself clean its deliberately leaked test child.
        for pid in spawned:
            try: os.killpg(pid, 9)
            except ProcessLookupError: pass
