"""Authored metadata and numeric endpoint tests; never consume retained inputs."""
import copy
import importlib
import importlib.util
import sys
import time
import os
from pathlib import Path
import json
import hashlib
from types import SimpleNamespace

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


def test_whole_parent_supervisor_kills_term_ignoring_child_after_timeout_parent_exit(tmp_path):
    m = module()
    child_path = tmp_path / 'child.pid'
    worker = 'import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(20)'
    parent = ('import subprocess,sys,time;from pathlib import Path;'
              f'p=subprocess.Popen([sys.executable,"-c",{worker!r}]);'
              f'Path({str(child_path)!r}).write_text(str(p.pid));time.sleep(20)')
    now = time.monotonic()
    command = ['/usr/bin/timeout', '--signal=TERM', '--kill-after=.2s', '.2s',
               sys.executable, '-c', parent]
    result = m._supervised(command, tmp_path, normal_deadline=now + 3,
                          hard_deadline=now + 4, min_free_bytes=0, max_processes=3)
    assert result['status'] == 'failed'
    assert result['returncode'] == 124
    assert result['matching_survivors'] == []
    assert child_path.exists(), 'Test must actually launch its TERM-ignoring child'
    pid = int(child_path.read_text())
    stat = Path('/proc') / str(pid) / 'stat'
    assert not stat.exists() or stat.read_text().rsplit(')', 1)[1].split()[0] in ('Z', 'X')


def test_whole_parent_supervisor_accepts_timely_parent_and_worker_return(tmp_path):
    m = module()
    parent = 'import subprocess,sys;subprocess.run([sys.executable,"-c","print(123)"],check=True)'
    now = time.monotonic()
    result = m._supervised(['/usr/bin/timeout', '--signal=TERM', '--kill-after=1s', '3s',
                           sys.executable, '-c', parent], tmp_path,
                          normal_deadline=now + 4, hard_deadline=now + 5,
                          min_free_bytes=0, max_processes=3)
    assert result['status'] == 'completed'
    assert result['matching_survivors'] == []
    assert (tmp_path / 'stdout.log').read_bytes() == b'123\n'


@pytest.mark.parametrize('field,value', [('positive_cells', 737.0), ('max_cells', 1470.0),
                                        ('model_seed', 400.0), ('attempts', True),
                                        ('native_owners', False), ('physics_steps', False)])
def test_execution_freeze_refuses_numeric_type_aliases(tmp_path, field, value):
    m = module()
    freeze = json.loads((m.ROOT / 'docs/plans/memory-full-cell-qualification-v4-execution.json').read_bytes())
    freeze[field] = value
    raw = m._canonical(freeze)
    path = tmp_path / 'freeze.json'
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        m._freeze(path, hashlib.sha256(raw).hexdigest())


def test_parent_late_close_fsync_cannot_leave_an_accepted_close(tmp_path, monkeypatch):
    m = module()
    assert hasattr(m, '_parent'), 'Whole-parent qualification boundary is missing'
    now = time.monotonic()
    clock = [now]
    job = {'deadline': now + 10, 'started_monotonic': now, 'freeze_sha256': 'a' * 64}
    freeze = {'output': str(tmp_path), 'claims': {'family_admission': False,
              'pruning_authorized': False, 'qualification_claims': []}}
    args = SimpleNamespace(freeze='fixture', freeze_sha256='a' * 64)
    real_write = m._write
    def write(path, value):
        real_write(path, value)
        if path.name == 'close.json':
            clock[0] = job['deadline'] + 1
    def worker(command, output, deadline):
        real_write(output / 'worker-result.json', {'positive_cells': 737,
                   'negatives': [{'rejected': True}] * 4})
    monkeypatch.setattr(m, '_require_parent_origin', lambda job: None)
    monkeypatch.setattr(m, '_held_inputs', lambda freeze, deadline, stack: {})
    monkeypatch.setattr(m, '_run_worker', worker)
    monkeypatch.setattr(m, '_write', write)
    monkeypatch.setattr(m.time, 'monotonic', lambda: clock[0])
    with pytest.raises(TimeoutError):
        m._parent(freeze, args, job)
    assert (tmp_path / 'failure.json').exists()
    assert json.loads((tmp_path / 'failure.json').read_bytes())['status'] == 'failed'


def test_parent_refuses_standalone_or_wrong_supervisor_origin():
    m = module()
    assert hasattr(m, '_require_parent_origin'), 'Parent origin admission is missing'
    with pytest.raises(ValueError):
        m._require_parent_origin({'supervisor_pid': -1})


def test_supervisor_checks_final_aggregate_output_outside_log_directory(tmp_path, monkeypatch):
    m = module()
    logs = tmp_path / 'outer'
    logs.mkdir()
    real_popen = m.subprocess.Popen
    def launch(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        process.wait(timeout=5)
        with (tmp_path / 'excess.bin').open('wb') as stream:
            stream.truncate(128 * 1024**2 + 1)
        return process
    monkeypatch.setattr(m.subprocess, 'Popen', launch)
    now = time.monotonic()
    result = m._supervised([sys.executable, '-c', 'pass'], logs,
                          normal_deadline=now + 3, hard_deadline=now + 4,
                          min_free_bytes=0, output_root=tmp_path)
    assert result['status'] == 'failed'
    assert result['failure'] == 'aggregate output cap'
    assert result['matching_survivors'] == []


def test_valid_current_freeze_loads_without_opening_its_protected_inputs():
    m = module()
    path = m.ROOT / 'docs/plans/memory-full-cell-qualification-v4-execution.json'
    value = m._freeze(path, hashlib.sha256(path.read_bytes()).hexdigest())
    assert value['positive_cells'] == 737
    assert value['limits']['workload_processes'] == 3


def test_hard_guard_ends_stalled_monitor_and_its_known_owned_group(tmp_path):
    import subprocess
    import signal
    m = module()
    path = tmp_path / 'owned.pid'
    code = f'''import subprocess,sys,time
from pathlib import Path
from scripts.qualify_memory_full_cell_v4 import _hard_guard
state={{"group":None}}
with _hard_guard(time.monotonic()+.4,state):
    child=subprocess.Popen([sys.executable,"-c","import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(20)"],start_new_session=True)
    state["group"]=child.pid
    Path({str(path)!r}).write_text(str(child.pid))
    time.sleep(20)
'''
    process = subprocess.Popen([sys.executable, '-c', code], cwd=m.ROOT,
                               env=dict(os.environ), start_new_session=True)
    try:
        process.wait(timeout=3)
        assert process.returncode == -signal.SIGKILL
        assert path.exists(), 'Test must actually start its owned child'
        stat = Path('/proc') / path.read_text() / 'stat'
        assert not stat.exists() or stat.read_text().rsplit(')', 1)[1].split()[0] in ('Z', 'X')
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        if path.exists():
            try: os.killpg(int(path.read_text()), signal.SIGKILL)
            except ProcessLookupError: pass
            try: os.kill(int(path.read_text()), signal.SIGKILL)
            except ProcessLookupError: pass


@pytest.mark.parametrize('isolate_child', [True, False])
def test_guard_term_interruption_cleans_its_group_before_monitor_exit(tmp_path, isolate_child):
    import subprocess
    import signal
    m = module()
    path = tmp_path / 'owned.pid'
    code = f'''import subprocess,sys,time
from pathlib import Path
from scripts.qualify_memory_full_cell_v4 import _hard_guard
state={{"group":None}}
with _hard_guard(time.monotonic()+5,state):
    child=subprocess.Popen([sys.executable,"-c","import signal,time;signal.signal(signal.SIGTERM,signal.SIG_IGN);time.sleep(20)"],start_new_session={isolate_child!r})
    state["group"]=child.pid if {isolate_child!r} else None
    Path({str(path)!r}).write_text(str(child.pid))
    time.sleep(20)
'''
    process = subprocess.Popen([sys.executable, '-c', code], cwd=m.ROOT,
                               env=dict(os.environ), start_new_session=True)
    try:
        until = time.monotonic() + 2
        while not path.exists() and process.poll() is None and time.monotonic() < until:
            time.sleep(.01)
        assert path.exists(), 'Test must actually launch its owned child'
        os.kill(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
        assert process.returncode != 0
        stat = Path('/proc') / path.read_text() / 'stat'
        until = time.monotonic() + .5
        while stat.exists() and stat.read_text().rsplit(')', 1)[1].split()[0] not in ('Z', 'X') and time.monotonic() < until:
            time.sleep(.01)
        assert not stat.exists() or stat.read_text().rsplit(')', 1)[1].split()[0] in ('Z', 'X')
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=3)
        if path.exists():
            try: os.killpg(int(path.read_text()), signal.SIGKILL)
            except ProcessLookupError: pass
            try: os.kill(int(path.read_text()), signal.SIGKILL)
            except ProcessLookupError: pass
