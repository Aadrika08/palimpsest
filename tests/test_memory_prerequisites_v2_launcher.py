"""Campaign scheduling/publication only; completed records replace scientific work."""
import importlib.util
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace

import pytest
from palimpsest.storage import StorageBudget, StorageLimits


def launcher(version='v2'):
    source = Path(__file__).resolve().parents[1] / f'docs/reports/memory-prerequisites-{version}-evidence/execute-campaign.py'
    assert source.exists(), 'Fresh campaign launcher is not implemented'
    spec = importlib.util.spec_from_file_location('campaign_launcher_fixture', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('driver_code,audit_code,passed', [(0,0,True),(0,0,False),(1,0,True),(0,1,True)])
@pytest.mark.parametrize('version',['v2','v3'])
def test_campaign_pipeline_requires_all_three_results(tmp_path, monkeypatch, driver_code, audit_code, passed,version):
    module = launcher(version); root = tmp_path / 'output'; path = tmp_path / 'registration.json'
    reg = {'output': str(root)}
    monkeypatch.setattr(module.runner, 'admission', lambda value: reg)
    calls = []
    def run(value):
        assert value == path
        calls.append('driver'); root.mkdir()
        return driver_code
    def audit(value):
        assert value == path
        calls.append('audit')
        (root / 'scientific-close.json').write_text(json.dumps({'native_prerequisites_passed': passed}))
        return audit_code
    monkeypatch.setattr(module.m, 'run', run)
    monkeypatch.setattr(module.m, 'audit', audit)
    assert module.pipeline(path) == (0 if driver_code == audit_code == 0 and passed else 1)
    assert calls == ['driver', 'audit']


@pytest.mark.parametrize('code', [0, 124])
@pytest.mark.parametrize('version',['v2','v3'])
def test_whole_campaign_watchdog_invalidates_failed_close(tmp_path, monkeypatch, code,version):
    module = launcher(version); runner = module.runner
    evidence = tmp_path / f'docs/reports/memory-prerequisites-{version}-evidence'
    evidence.mkdir(parents=True)
    source = evidence / 'execute-campaign.py'
    root = tmp_path / 'runs/memory-prerequisites-v2-fixture'; root.mkdir(parents=True)
    (root / 'scientific-close.json').write_text(json.dumps({'native_prerequisites_passed': True}))
    reg = {'repo': str(tmp_path), 'output': str(root), 'python': sys.executable,
           'control_root': str(tmp_path / 'control'), 'publication_root': str(evidence)}
    (evidence / 'registration.json').write_text(json.dumps(reg))
    monkeypatch.setattr(runner, '__file__', str(source))
    monkeypatch.setattr(runner, 'admission', lambda *args, **kw: reg)
    monkeypatch.setattr(runner.d, 'restore_v2_budget', lambda value: StorageBudget(
        (root, evidence, tmp_path/'control'), StorageLimits(max_bytes=1024**2, min_free_bytes=0)))
    monkeypatch.setattr(runner.d, 'recheck_v2_inputs', lambda *args: None)
    monkeypatch.setattr(runner.subprocess, 'check_output', lambda *args, **kw: 'a'*40)
    calls = []
    def child(command, **kwargs):
        calls.append(command)
        assert command[:5] == ['timeout', '--foreground', '--signal=TERM', '--kill-after=5', '4890s']
        assert command[-3:] == [sys.executable, str(source), '--supervised']
        return SimpleNamespace(pid=999999999, wait=lambda **kw: code, poll=lambda: code)
    monkeypatch.setattr(runner.subprocess, 'Popen', child)
    assert module.main(['--bounded']) == (0 if code == 0 else 1)
    assert len(calls) == 1
    assert json.loads((root / 'scientific-close.json').read_text())['native_prerequisites_passed'] is (code == 0)
    if code:
        receipt = json.loads((evidence / 'invocation-result.json').read_text())
        assert receipt['native_exit_code'] == 1 and receipt['watchdog_exit_code'] == 124
        assert receipt['qualification_claims'] == []


def test_failed_invalidation_preserves_bytes_without_authoritative_success(tmp_path, monkeypatch):
    module = launcher(); root = tmp_path / 'root'; root.mkdir()
    before = b'{"native_prerequisites_passed":true,"qualification_claims":[]}\n'
    (root / 'scientific-close.json').write_bytes(before)
    def refuse(*args):
        raise OSError('fixture publication refusal')
    monkeypatch.setattr(module.runner.d, 'replace_control', refuse)
    module.runner.invalidate(root, None, 'late or interrupted')
    assert not (root / 'scientific-close.json').exists()
    assert (root / 'scientific-close.invalidated.json').read_bytes() == before


@pytest.mark.parametrize('code', [0, 124])
@pytest.mark.parametrize('version',['v2','v3'])
def test_absolute_watchdog_covers_parent_failure_recovery(monkeypatch, code,version):
    module = launcher(version); calls = []
    def child(command, **kwargs):
        calls.append(command)
        assert command[:3] == ['timeout','--signal=KILL','4900s']
        assert command[-3:] == [sys.executable, str(Path(module.__file__).resolve()), '--bounded']
        return SimpleNamespace(returncode=code)
    monkeypatch.setattr(module.runner.subprocess,'run',child)
    assert module.main([]) == (0 if code == 0 else 1)
    assert len(calls) == 1


def test_campaign_clock_includes_launcher_admission(tmp_path,monkeypatch):
    from test_memory_prerequisites_v2 import setup_campaign
    module,path,root,reg,launched,_ = setup_campaign(tmp_path,monkeypatch)
    marker = Path(reg['control_root'])/'launched.json'
    value = json.loads(marker.read_text()); original = time.monotonic()-60
    value['started_monotonic'] = original; marker.write_text(json.dumps(value))
    assert module.run(path) == 0
    receipt = json.loads((root/'execution.json').read_text())
    assert receipt['started_monotonic'] == original
    assert receipt['owner_deadline_monotonic'] == original+4300
    assert receipt['global_deadline_monotonic'] == original+4900


def test_auditor_refuses_self_consistent_rebased_deadlines(tmp_path,monkeypatch):
    from test_memory_prerequisites_v2 import setup_campaign
    module,path,root,reg,launched,_ = setup_campaign(tmp_path,monkeypatch)
    assert module.run(path) == 0
    receipt = json.loads((root/'execution.json').read_text())
    for key in ('started_monotonic','owner_deadline_monotonic','global_deadline_monotonic',
                'readout_started_monotonic','readout_deadline_monotonic'):
        receipt[key] -= 1
    (root/'execution.json').write_text(json.dumps(receipt))
    assert module.audit(path) == 1
    assert json.loads((root/'scientific-close.json').read_text())['native_prerequisites_passed'] is False


def test_changed_launcher_registration_refuses_before_owners(tmp_path,monkeypatch):
    from test_memory_prerequisites_v2 import setup_campaign
    module,path,root,reg,launched,_ = setup_campaign(tmp_path,monkeypatch)
    marker = Path(reg['control_root'])/'launched.json'
    value = json.loads(marker.read_text()); value['registration_sha256'] = 'f'*64
    marker.write_text(json.dumps(value))
    with pytest.raises(ValueError): module.run(path)
    assert not root.exists() and launched == []


@pytest.mark.parametrize('version',['v2','v3'])
def test_ancestor_hard_timeout_leaves_no_campaign_python_process(tmp_path,version):
    """Real runner spawning; the only worker is an exact-identity harmless sleeper."""
    import os
    import signal
    import subprocess

    repo = tmp_path/'repo'
    evidence = repo/f'docs/reports/memory-prerequisites-{version}-evidence'
    evidence.mkdir(parents=True)
    script = evidence/'execute.py'
    source = Path(__file__).resolve().parents[1]/f'docs/reports/memory-prerequisites-{version}-evidence/execute-campaign.py'
    reg = {'repo':str(repo),'output':str(repo/'runs/fixture'), 'python':sys.executable,
        'control_root':str(repo/'control'), 'publication_root':str(evidence)}
    (evidence/'registration.json').write_text(json.dumps(reg))
    script.write_text(f'''import importlib.util, json, os, signal, sys, time
from pathlib import Path
from types import SimpleNamespace
HERE = Path(__file__).resolve().parents[3]
def identity(role):
    fields = Path('/proc/self/stat').read_text().rsplit(')',1)[1].split()
    (HERE/(role+'.json')).write_text(json.dumps({{'pid':os.getpid(),
        'starttime':int(fields[19]),'pgid':os.getpgrp()}}))
role = 'pipeline' if '--pipeline' in sys.argv else 'supervised' if '--supervised' in sys.argv else 'controller'
identity(role)
SOURCE = Path({str(source)!r})
sys.path[:0] = [str(SOURCE.parents[3]),str(SOURCE.parents[3]/'src')]
spec = importlib.util.spec_from_file_location('actual_campaign',SOURCE)
module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
runner = module.runner; runner.__file__ = __file__; runner.WATCHDOG_SECONDS = 1.5
reg = json.loads((Path(__file__).parent/'registration.json').read_text())
runner.admission = lambda *args,**kw: reg
runner.shutil.disk_usage = lambda path: SimpleNamespace(free=16*runner.p.GiB)
runner.subprocess.check_output = lambda *args,**kw: '0'*40
from palimpsest.storage import StorageBudget,StorageLimits
runner.d.restore_v2_budget = lambda reg: StorageBudget(
    [reg[key] for key in ('output','control_root','publication_root')],
    StorageLimits(max_bytes=64*runner.p.MiB,min_free_bytes=0),headroom_bytes=0)
runner.d.recheck_v2_inputs = lambda *args: None
runner.d.cleanup_owners = lambda root: []
def harmless_run(path):
    signal.signal(signal.SIGTERM,signal.SIG_IGN)
    identity('pipeline-ready')
    while True: time.sleep(60)
module.m.run = harmless_run
raise SystemExit(runner.main(sys.argv[1:]))
''')

    def matching_live(record):
        try:
            fields = Path(f"/proc/{record['pid']}/stat").read_text().rsplit(')',1)[1].split()
            return (int(fields[19]),os.getpgid(record['pid'])) == (record['starttime'],record['pgid']) and fields[0] != 'Z'
        except (FileNotFoundError,ProcessLookupError):
            return False

    try:
        with (repo/'harness.log').open('wb') as log:
            result = subprocess.run(['timeout','--signal=KILL','5s',sys.executable,str(script)],
                cwd=repo,stdout=log,stderr=log,start_new_session=True,timeout=12)
        assert result.returncode != 0
        assert (repo/'pipeline-ready.json').exists(), (repo/'harness.log').read_text()
        records = {role:json.loads((repo/(role+'.json')).read_text())
                   for role in ('controller','supervised','pipeline')}
        survivors = {role:record for role,record in records.items() if matching_live(record)}
        assert not survivors, f'Python pipeline survived ancestor hard timeout: {survivors}'
    finally:
        # Touch only fixture PIDs whose starttime and PGID still match.
        for role in ('pipeline-ready','pipeline','supervised','controller'):
            path = repo/(role+'.json')
            if path.exists():
                record = json.loads(path.read_text())
                if matching_live(record):
                    try: os.kill(record['pid'],signal.SIGKILL)
                    except ProcessLookupError: pass
