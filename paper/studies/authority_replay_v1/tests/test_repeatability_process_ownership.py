"""Harmless process fixtures for unit-supervisor ownership and reaping."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
from types import SimpleNamespace

import pytest

from paper.studies.authority_replay_v1 import campaign, repeatability as driver


def test_exited_leader_never_authorizes_raw_pid_or_group_signal(tmp_path, monkeypatch):
    """A completed/reaped Popen cannot grant ownership of its recycled PID."""
    child = SimpleNamespace(pid=43210, returncode=0, poll=lambda: 0, wait=lambda **kw: 0,
                            terminate=lambda: None, kill=lambda: None)
    sent = []
    monkeypatch.setattr(driver.subprocess, 'Popen', lambda *a, **kw: child)
    monkeypatch.setattr(driver.os, 'killpg', lambda *a: sent.append(('group', a)))
    monkeypatch.setattr(driver.os, 'kill', lambda *a: sent.append(('pid', a)))
    driver._process([sys.executable, '-c', 'pass'], tmp_path / 'raw', timeout=1,
                    max_bytes=1024**2, minimum_free_bytes=0)
    assert sent == []


def _alive(pid):
    current = campaign._processes().get(pid)
    return current is not None and current[2] != 'Z'


@pytest.mark.parametrize('detached', [False, True])
def test_fast_success_cleans_orphan_without_touching_callers_child(tmp_path, detached):
    unrelated = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(10)'])
    pidfile = tmp_path / 'owned.pid'
    code = ('import subprocess,sys,pathlib; '
            f'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(10)"],'
            f'start_new_session={detached!r}); '
            f'pathlib.Path({str(pidfile)!r}).write_text(str(p.pid))')
    try:
        result = driver._process([sys.executable, '-c', code], tmp_path / 'raw', timeout=3,
                                 max_bytes=1024**2, minimum_free_bytes=0)
        assert result == {'status': 'completed', 'returncode': 0, 'stop_reason': None, 'error': None}
        assert not _alive(int(pidfile.read_text()))
        assert unrelated.poll() is None
    finally:
        unrelated.kill()
        unrelated.wait()


def test_timeout_reaps_guardian_and_nested_detached_workers(tmp_path, monkeypatch):
    pidfile = tmp_path / 'owned.pid'
    worker = 'import time;time.sleep(10)'
    nested = ('import subprocess,sys,pathlib,time; '
              f'p=subprocess.Popen([sys.executable,"-c",{worker!r}],start_new_session=True); '
              f'pathlib.Path({str(pidfile)!r}).write_text(str(p.pid));time.sleep(10)')
    code = ('import subprocess,sys,time; '
            f'subprocess.Popen([sys.executable,"-c",{nested!r}],start_new_session=True);time.sleep(10)')
    children = []
    original = driver.subprocess.Popen
    def spawn(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child
    monkeypatch.setattr(driver.subprocess, 'Popen', spawn)
    result = driver._process([sys.executable, '-c', code], tmp_path / 'raw', timeout=.4,
                             max_bytes=1024**2, minimum_free_bytes=0)
    assert result['status'] == 'timeout'
    assert result['returncode'] == -signal.SIGKILL
    assert not _alive(int(pidfile.read_text()))
    with pytest.raises(ChildProcessError):
        os.waitpid(children[0].pid, os.WNOHANG)


def test_guardian_pin_failure_denies_admission_and_reaps(tmp_path, monkeypatch):
    marker = tmp_path / 'must-not-exist'
    children = []
    original = driver.subprocess.Popen
    def spawn(*args, **kwargs):
        child = original(*args, **kwargs)
        children.append(child)
        return child
    def exhausted(pid):
        raise OSError('pidfd admission unavailable')
    monkeypatch.setattr(driver.subprocess, 'Popen', spawn)
    monkeypatch.setattr(campaign, '_open_pidfd', exhausted)
    result = driver._process([sys.executable, '-c', f'from pathlib import Path;Path({str(marker)!r}).touch()'],
                             tmp_path / 'raw', timeout=2, max_bytes=1024**2, minimum_free_bytes=0)
    assert result['status'] == 'failed'
    assert 'pidfd admission unavailable' in result['error']['message']
    assert not marker.exists()
    with pytest.raises(ChildProcessError):
        os.waitpid(children[0].pid, os.WNOHANG)


@pytest.mark.parametrize('failure', ['identity', 'cleanup', 'pidfd'])
def test_private_guardian_failure_still_reaps_direct_unit(tmp_path, failure):
    """Inject guardian failures only in an isolated, harmless helper process."""
    command, result = tmp_path / 'command.json', tmp_path / 'result.json'
    command.write_text(json.dumps([sys.executable, '-c', 'import time;time.sleep(.1)']))
    harness = f'''
import os
from pathlib import Path
from paper.studies.authority_replay_v1 import campaign, repeatability as driver
children = []
original = driver.subprocess.Popen
def spawn(*args, **kwargs):
    child = original(*args, **kwargs)
    children.append(child)
    return child
driver.subprocess.Popen = spawn
def fail(*args, **kwargs):
    raise OSError('injected {failure} failure')
if {failure!r} == 'identity':
    campaign._processes = lambda: {{}}
elif {failure!r} == 'cleanup':
    campaign._cleanup = fail
else:
    campaign._open_pidfd = fail
read_fd, write_fd = os.pipe()
os.write(write_fd, b'GO\\n')
os.close(write_fd)
status = driver._supervise_unit(Path({str(command)!r}), Path({str(result)!r}), os.getppid(), read_fd)
assert status == 1
assert len(children) == 1
assert children[0].returncode is not None
try:
    os.waitpid(children[0].pid, os.WNOHANG)
except ChildProcessError:
    pass
else:
    raise AssertionError('direct unit was not reaped')
'''
    checked = subprocess.run([sys.executable, '-B', '-c', harness], capture_output=True, timeout=4)
    assert checked.returncode == 0, checked.stderr.decode()
    assert 'error' in json.loads(result.read_text())


@pytest.mark.parametrize('exit_code', [0, 7])
def test_unit_returncode_and_result_schema_are_preserved(tmp_path, exit_code):
    result = driver._process([sys.executable, '-c', f'raise SystemExit({exit_code})'],
                             tmp_path / 'raw', timeout=2, max_bytes=1024**2, minimum_free_bytes=0)
    assert result == {'status': 'failed' if exit_code else 'completed', 'returncode': exit_code,
                      'stop_reason': None, 'error': None}


def test_pidfd_stop_failure_still_allows_guardian_cleanup(tmp_path, monkeypatch):
    pidfile = tmp_path / 'unit.pid'
    code = ('import os,pathlib,time; '
            f'pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid()));time.sleep(10)')
    def unavailable(*args):
        raise OSError('pidfd stop unavailable')
    monkeypatch.setattr(campaign, '_send_pidfd', unavailable)
    result = driver._process([sys.executable, '-c', code], tmp_path / 'raw', timeout=.3,
                             max_bytes=1024**2, minimum_free_bytes=0)
    assert result['status'] == 'timeout'
    assert result['returncode'] == -signal.SIGKILL
    assert 'pidfd stop unavailable' in result['error']['message']
    assert not _alive(int(pidfile.read_text()))


def test_inner_pidfd_failure_cannot_execute_detached_spawning_command(tmp_path):
    command, result = tmp_path / 'command.json', tmp_path / 'result.json'
    marker = tmp_path / 'unauthorized-unit-started'
    code = ('import subprocess,sys,pathlib,time; '
            'subprocess.Popen([sys.executable,"-c","import time;time.sleep(.2)"],start_new_session=True); '
            f'pathlib.Path({str(marker)!r}).touch();time.sleep(.5)')
    command.write_text(json.dumps([sys.executable, '-c', code]))
    harness = f'''
import os,time
from pathlib import Path
from paper.studies.authority_replay_v1 import campaign, repeatability as driver
def unavailable(pid):
    end = time.monotonic() + .2
    while not Path({str(marker)!r}).exists() and time.monotonic() < end:
        time.sleep(.005)
    raise OSError('inner pidfd admission failed')
campaign._open_pidfd = unavailable
read_fd, write_fd = os.pipe()
os.write(write_fd, b'GO\\n')
os.close(write_fd)
assert driver._supervise_unit(Path({str(command)!r}), Path({str(result)!r}), os.getppid(), read_fd) == 1
# Pre-fix counterexample workers are harmless and self-exit; reap any adopted
# fixture here so even the failing regression leaves no child behind.
while True:
    try:
        os.waitpid(-1, 0)
    except ChildProcessError:
        break
'''
    checked = subprocess.run([sys.executable, '-B', '-c', harness], capture_output=True, timeout=4)
    assert checked.returncode == 0, checked.stderr.decode()
    assert not marker.exists(), 'unit executed before inner ownership admission'
    assert 'inner pidfd admission failed' in json.loads(result.read_text())['error']['message']


def test_cleanup_failure_reaps_adopted_worker_and_preserves_primary_error(tmp_path):
    command, result = tmp_path / 'command.json', tmp_path / 'result.json'
    pidfile = tmp_path / 'owned.pid'
    code = ('import subprocess,sys,pathlib,time; '
            'p=subprocess.Popen([sys.executable,"-c","import time;time.sleep(1)"],start_new_session=True); '
            f'pathlib.Path({str(pidfile)!r}).write_text(str(p.pid));time.sleep(.1)')
    command.write_text(json.dumps([sys.executable, '-c', code]))
    harness = f'''
import os
from pathlib import Path
from paper.studies.authority_replay_v1 import campaign, repeatability as driver
original = campaign._cleanup
attempts = []
def fail_once(*args, **kwargs):
    attempts.append(True)
    if len(attempts) == 1:
        raise OSError('primary cleanup failure')
    return original(*args, **kwargs)
campaign._cleanup = fail_once
read_fd, write_fd = os.pipe()
os.write(write_fd, b'GO\\n')
os.close(write_fd)
assert driver._supervise_unit(Path({str(command)!r}), Path({str(result)!r}), os.getppid(), read_fd) == 1
assert len(attempts) == 2
pid = int(Path({str(pidfile)!r}).read_text())
assert pid not in campaign._processes(), 'adopted worker not reaped after fallback'
'''
    checked = subprocess.run([sys.executable, '-B', '-c', harness], capture_output=True, timeout=4)
    assert checked.returncode == 0, checked.stderr.decode()
    error = json.loads(result.read_text())['error']
    assert error['type'] == 'OSError'
    assert error['message'].startswith('unit ownership cleanup failed: primary cleanup failure')


@pytest.mark.parametrize('boundary,reason', [('output', 'unit output cap'),
                                            ('free', 'filesystem free-space reserve')])
def test_fast_completion_rechecks_existing_resource_boundary(tmp_path, monkeypatch, boundary, reason):
    """Publish after the running inventory and exit before the next monitor poll."""
    import time
    original_size = driver._size
    scans, free_checks = [], []
    def running_inventory(root):
        scans.append(True)
        if len(scans) == 1:
            end = time.monotonic() + 2
            while not list(root.glob('.unit-supervision-*/result.json')):
                assert time.monotonic() < end, 'fixture guardian did not finish'
                time.sleep(.005)
            return 0  # Inventory was taken before the fast publication.
        return original_size(root)
    def free_space(root):
        free_checks.append(True)
        return SimpleNamespace(free=0 if boundary == 'free' and len(free_checks) > 1 else 1024**3)
    monkeypatch.setattr(driver, '_size', running_inventory)
    monkeypatch.setattr(driver.shutil, 'disk_usage', free_space)
    code = 'print("x"*2048)' if boundary == 'output' else 'pass'
    result = driver._process([sys.executable, '-c', code], tmp_path / 'raw', timeout=3,
                             max_bytes=1024 if boundary == 'output' else 1024**2,
                             minimum_free_bytes=100)
    assert result['returncode'] == 0
    assert result['status'] == 'failed'
    assert result['stop_reason'] == reason
