"""Bounded orchestration tests: no model, scientific driver or offline execution."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from paper.studies.authority_replay_v1 import common

STUDY = Path(__file__).resolve().parents[1]


def module():
    from paper.studies.authority_replay_v1 import campaign
    return campaign


@pytest.fixture
def setup(tmp_path, monkeypatch):
    c = module()
    identity = {'commit': 'a' * 40, 'protocol_sha256': common.sha256_file(STUDY / 'protocol.json'),
                'runtime_source_sha256': {'src/palimpsest/a.py': 'b' * 64},
                'asset_manifest_sha256': {'manifest': 'c' * 64}, 'asset_sha256': {'asset': 'd' * 64}}
    monkeypatch.setattr(c, 'campaign_identity', lambda *args: identity)
    monkeypatch.setattr(c.shutil, 'disk_usage', lambda _: type('Disk', (), {'free': 100 * 1024**3})())
    return c, identity, tmp_path / 'campaign'


def emit(c, identity, phase, status='completed'):
    phase.output.mkdir(parents=True)
    for unit in common.declared_units(common.load_protocol(STUDY / 'protocol.json')):
        if unit['kind'] == phase.kind:
            common.append_row(phase.output / 'rows.jsonl', dict(schema_version=1, study_id='authority_replay_v1',
                              **unit, identity=identity, status=status, metrics={}))


def test_plan_exact_order_interfaces_and_no_writes(tmp_path, capsys):
    c = module()
    output = tmp_path / 'absent'
    assert c.main(['--protocol', str(STUDY / 'protocol.json'), '--assets', str(tmp_path / 'assets'),
                   '--output', str(output), '--plan-only']) == 0
    assert not output.exists()
    phases = c.plan(STUDY / 'protocol.json', tmp_path / 'assets', output, 123.)
    assert [p.name for p in phases] == ['fault_matrix', 'continuation', 'replay', 'execution_overhead', 'operation_cost', 'offline_reproduction']
    assert phases[4].command[-4:] == ['--kind', 'operations', '--replay-root', str(output / 'replay')]
    for phase in phases[:-1]:
        assert phase.command[phase.command.index('--campaign-root') + 1] == str(output)
        assert phase.command[phase.command.index('--campaign-deadline-epoch') + 1] == '123.0'
    assert phases[-1].command[-4:] == ['--setup', '--full-flynn', '--duration', '55']
    assert '--duration 55' in capsys.readouterr().out


def test_existing_root_refused_even_empty(setup):
    c, identity, output = setup
    output.mkdir()
    with pytest.raises(ValueError, match='fresh'):
        c.run(STUDY / 'protocol.json', output.parent, output)
    assert list(output.iterdir()) == []


def test_complete_denominator_and_unique_logs(setup, monkeypatch):
    c, identity, output = setup
    calls = []
    def fake(phase, **kwargs):
        calls.append((phase, kwargs))
        if phase.kind != 'offline_reproduction':
            emit(c, identity, phase, 'failed' if phase.kind == 'replay' else 'completed')
        else:
            phase.output.mkdir()
            (phase.output / 'report.json').write_text(json.dumps({'status': 'blocked', 'reason': 'unshare denied'}))
        return {'returncode': 1, 'status': 'exited'}
    monkeypatch.setattr(c, 'run_phase', fake)
    assert c.run(STUDY / 'protocol.json', output.parent, output) == 1
    summary = json.loads((output / 'analysis/summary.json').read_text())
    assert summary['declared_units'] == 111
    assert summary['status_counts']['failed'] == 6
    assert len(calls) == 6  # scientific failures do not authorize replacement or stop
    clock = json.loads((output / 'campaign-clock.json').read_text())
    assert clock['deadline_unix'] - clock['started_unix'] == 14400
    assert all(k['deadline'] == clock['deadline_unix'] for _, k in calls)
    manifest = json.loads((output / 'analysis/campaign-manifest.json').read_text())
    assert len({p['process_record'] for p in manifest['phases']}) == 6
    assert (output / 'analysis/raw-inventory.json').is_file()
    assert (output / 'analysis/fault-traces.jsonl').is_file()


def test_crash_keeps_rows_and_only_missing_are_incomplete(setup, monkeypatch):
    c, identity, output = setup
    def fake(phase, **kwargs):
        emit(c, identity, phase, 'timeout')
        return {'returncode': 2, 'status': 'exited'}
    monkeypatch.setattr(c, 'run_phase', fake)
    c.run(STUDY / 'protocol.json', output.parent, output)
    summary = json.loads((output / 'analysis/summary.json').read_text())
    assert summary['status_counts']['timeout'] == 50
    assert summary['status_counts']['incomplete'] == 61
    assert len(json.loads((output / 'analysis/campaign-manifest.json').read_text())['phases']) == 6


def test_duplicate_rows_fail_analysis_without_suppression(setup, monkeypatch):
    c, identity, output = setup
    def fake(phase, **kwargs):
        emit(c, identity, phase)
        path = phase.output / 'rows.jsonl'
        with path.open('a') as stream:
            stream.write(path.read_text().splitlines()[0] + '\n')
        return {'returncode': 0, 'status': 'exited'}
    monkeypatch.setattr(c, 'run_phase', fake)
    assert c.run(STUDY / 'protocol.json', output.parent, output) == 1
    manifest = json.loads((output / 'analysis/campaign-manifest.json').read_text())
    assert 'duplicate' in manifest['analysis_error']
    assert not (output / 'analysis/summary.json').exists()


@pytest.mark.parametrize('cause', ['identity', 'protocol', 'deadline', 'bytes', 'reserve'])
def test_guard_refuses_drift_and_bounds(setup, monkeypatch, cause):
    c, identity, output = setup
    output.mkdir()
    guard = c.Guard(output, STUDY / 'protocol.json', output.parent, identity, time.time() + 30)
    if cause in ('identity', 'protocol'):
        monkeypatch.setattr(c, 'campaign_identity', lambda *a: {**identity, 'protocol_sha256': '0' * 64})
    elif cause == 'deadline':
        guard.deadline = 0
    elif cause == 'bytes':
        monkeypatch.setattr(c, 'tree_size', lambda _: 16 * 1024**3 + 1)
    else:
        monkeypatch.setattr(c.shutil, 'disk_usage', lambda _: type('Disk', (), {'free': 0})())
    with pytest.raises((ValueError, TimeoutError)):
        guard.check()


def test_offline_admission_requires_full_source_and_report(setup):
    c, identity, output = setup
    output.mkdir()
    source = {'commit': identity['commit'], 'files_sha256': {'src/palimpsest/a.py': 'b' * 64}}
    report = {'status': 'passed', 'runtime_source': source, 'runtime_source_at_end': source, 'runtime_source_unchanged': True}
    (output / 'report.json').write_text(json.dumps(report))
    assert c.offline_row(output, identity)['status'] == 'failed'
    (output / 'setup.json').write_text(json.dumps({'status': 'passed', 'source': source}))
    (output / 'full-flynn').mkdir()
    (output / 'full-flynn/verification.json').write_text(json.dumps({'status': 'passed', 'controller': 'flynn', 'device': 'cpu'}))
    assert c.offline_row(output, identity)['status'] == 'completed'
    report['runtime_source']['commit'] = 'e' * 40
    (output / 'report.json').write_text(json.dumps(report))
    assert c.offline_row(output, identity)['status'] == 'failed'


def test_monitor_exception_reaps_owned_process(setup):
    c, identity, output = setup
    output.mkdir()
    phase = c.Phase('fake', 'fault', output / 'unit', [sys.executable, '-c', 'import time; time.sleep(60)'])
    class BadGuard:
        def check(self):
            raise RuntimeError('monitor exploded')
    record = c.run_phase(phase, root=output, deadline=time.time() + 10, guard=BadGuard())
    assert record['status'] == 'failed'
    assert record['reason'] == 'monitor exploded'
    assert not Path('/proc', str(record['pid'])).exists()


def test_post_exit_cap_checked(setup):
    c, identity, output = setup
    output.mkdir()
    phase = c.Phase('fake', 'fault', output / 'unit', [sys.executable, '-c', 'pass'])
    class Guard:
        calls = 0
        def check(self):
            self.calls += 1
            if self.calls == 1:
                time.sleep(.1)  # Let this lightweight child finish between polls.
                return
            raise ValueError('post-exit cap')
    record = c.run_phase(phase, root=output, deadline=time.time() + 10, guard=Guard())
    assert record['status'] == 'failed'
    assert record['reason'] == 'post-exit cap'


def test_partial_phase_failure_preserves_single_emitted_row(setup, monkeypatch):
    c, identity, output = setup
    calls = []
    def fake(phase, **kwargs):
        calls.append(phase.name)
        phase.output.mkdir()
        unit = common.declared_units(common.load_protocol(STUDY / 'protocol.json'))[0]
        common.append_row(phase.output / 'rows.jsonl', dict(schema_version=1, study_id='authority_replay_v1',
                          **unit, identity=identity, status='failed', metrics={}, reason='original failure'))
        return {'status': 'exited', 'returncode': 2}
    monkeypatch.setattr(c, 'run_phase', fake)
    assert c.run(STUDY / 'protocol.json', output.parent, output) == 1
    rows = json.loads((output / 'analysis/summary.json').read_text())['rows']
    assert len(calls) == 1
    assert rows[0]['status'] == 'failed' and rows[0]['reason'] == 'original failure'
    assert sum(r['status'] == 'incomplete' for r in rows) == 110


def test_torn_append_retained_and_manifest_records_analysis_failure(setup, monkeypatch):
    c, identity, output = setup
    def fake(phase, **kwargs):
        phase.output.mkdir()
        (phase.output / 'rows.jsonl').write_text('{"unit_id":')
        return {'status': 'exited', 'returncode': 2}
    monkeypatch.setattr(c, 'run_phase', fake)
    assert c.run(STUDY / 'protocol.json', output.parent, output) == 1
    assert (output / 'fault_matrix/rows.jsonl').read_text() == '{"unit_id":'
    assert 'incomplete row append' in json.loads((output / 'analysis/campaign-manifest.json').read_text())['analysis_error']


def test_wrong_controller_cannot_pass_offline(setup):
    c, identity, output = setup
    output.mkdir()
    source = {'commit': identity['commit'], 'files_sha256': {'src/palimpsest/a.py': 'b' * 64}}
    (output / 'report.json').write_text(json.dumps({'status': 'passed', 'runtime_source': source,
        'runtime_source_at_end': source, 'runtime_source_unchanged': True}))
    (output / 'setup.json').write_text(json.dumps({'status': 'passed', 'source': source}))
    (output / 'full-flynn').mkdir()
    (output / 'full-flynn/verification.json').write_text(json.dumps({'status': 'passed', 'controller': 'manual'}))
    assert c.offline_row(output, identity)['status'] == 'failed'


def test_guard_checks_unit_cap_after_child_exit(setup, monkeypatch):
    c, identity, output = setup
    path = output / 'continuation/seed-0'
    path.mkdir(parents=True)
    original = c.tree_size
    monkeypatch.setattr(c, 'tree_size', lambda p: 512 * 1024**2 + 1 if p == path else original(p))
    guard = c.Guard(output, STUDY / 'protocol.json', output.parent, identity, time.time() + 30)
    with pytest.raises(ValueError, match='ordinary unit'):
        guard.check()


def test_parent_exit_reaps_detached_owned_descendant(setup):
    c, identity, output = setup
    output.mkdir()
    pidfile = output / 'descendant.pid'
    child_script = "import time; time.sleep(60)"
    script = ('import subprocess,sys,pathlib; '
              f'p=subprocess.Popen([sys.executable,"-c",{child_script!r}], start_new_session=True); '
              f'pathlib.Path({str(pidfile)!r}).write_text(str(p.pid))')
    phase = c.Phase('parent-exit', 'fault', output / 'unit', [sys.executable, '-c', script])
    class QuietGuard:
        def check(self):
            pass
    record = c.run_phase(phase, root=output, deadline=time.time() + 5, guard=QuietGuard())
    pid = int(pidfile.read_text())
    try:
        assert record['status'] == 'exited'
        assert not Path('/proc', str(pid)).exists()
    finally:
        try:
            os.kill(pid, 9)
        except ProcessLookupError:
            pass


def test_deadline_prevents_launch_and_accounts_all_units(setup, monkeypatch):
    c, identity, output = setup
    real_time = c.time.time
    ticks = iter([real_time(), real_time() + 14401])
    monkeypatch.setattr(c.time, 'time', lambda: next(ticks, real_time() + 14401))
    monkeypatch.setattr(c, 'run_phase', lambda *a, **k: pytest.fail('deadline must prevent phase launch'))
    assert c.run(STUDY / 'protocol.json', output.parent, output) == 1
    summary = json.loads((output / 'analysis/summary.json').read_text())
    assert summary['status_counts']['incomplete'] == 111


def test_shared_fault_runtime_base_uses_aggregate_budget(setup, monkeypatch):
    c, identity, output = setup
    base = output / 'fault_matrix/runtime-base'
    base.mkdir(parents=True)
    monkeypatch.setattr(c, 'tree_size', lambda path: 700 * 1024**2)
    c.Guard(output, STUDY / 'protocol.json', output.parent, identity, time.time() + 30).check()


def test_monitor_checks_identity_in_emitted_rows(setup):
    c, identity, output = setup
    phase = c.plan(STUDY / 'protocol.json', output.parent, output, time.time() + 30)[0]
    emit(c, {**identity, 'commit': '0' * 40}, phase)
    with pytest.raises(ValueError, match='row identity'):
        c.Guard(output, STUDY / 'protocol.json', output.parent, identity, time.time() + 30).check()


def test_offline_source_hashes_must_be_complete(setup):
    c, identity, output = setup
    output.mkdir()
    identity['runtime_source_sha256']['src/palimpsest/missing.py'] = 'e' * 64
    source = {'commit': identity['commit'], 'files_sha256': {'src/palimpsest/a.py': 'b' * 64}}
    (output / 'report.json').write_text(json.dumps({'status': 'passed', 'runtime_source': source,
        'runtime_source_at_end': source, 'runtime_source_unchanged': True}))
    (output / 'setup.json').write_text(json.dumps({'status': 'passed', 'source': source}))
    (output / 'full-flynn').mkdir()
    (output / 'full-flynn/verification.json').write_text(json.dumps({'status': 'passed', 'controller': 'flynn', 'device': 'cpu'}))
    assert c.offline_row(output, identity)['status'] == 'failed'


def test_plan_prints_amended_resource_preflight(tmp_path, capsys):
    c = module()
    c.main(['--protocol', str(STUDY / 'protocol.json'), '--assets', str(tmp_path),
            '--output', str(tmp_path / 'new'), '--plan-only'])
    text = capsys.readouterr().out
    assert '10737418240' in text and '17179869184' in text
    assert not (tmp_path / 'new').exists()


def test_offline_admission_monitors_physical_reserve_without_reserving_logical_cap(setup, monkeypatch):
    c, identity, output = setup
    monkeypatch.setattr(c.shutil, 'disk_usage', lambda _: type('Disk', (), {'free': 7 * 1024**3})())
    calls = []
    def fake(phase, **kwargs):
        calls.append(phase.kind)
        if phase.kind != 'offline_reproduction':
            emit(c, identity, phase)
        else:
            phase.output.mkdir()
        return {'status': 'exited', 'returncode': 0}
    monkeypatch.setattr(c, 'run_phase', fake)
    c.run(STUDY / 'protocol.json', output.parent, output)
    assert calls[-1] == 'offline_reproduction'
    preflight = json.loads((output / 'preflight.json').read_text())
    assert preflight['resources']['offline_unit_max_output_bytes'] == 10 * 1024**3
    assert preflight['offline_admission_headroom_bytes'] == 512 * 1024**2
    assert 'cache_link_mode' in preflight


def test_torn_tail_does_not_label_complete_prefix_as_unexecuted(setup, monkeypatch):
    c, identity, output = setup
    first = common.declared_units(common.load_protocol(STUDY / 'protocol.json'))[0]
    def fake(phase, **kwargs):
        phase.output.mkdir()
        common.append_row(phase.output / 'rows.jsonl', dict(schema_version=1, study_id='authority_replay_v1',
                          **first, identity=identity, status='failed', metrics={}))
        with (phase.output / 'rows.jsonl').open('a') as stream:
            stream.write('{"unit_id":')
        return {'status': 'exited', 'returncode': 1}
    monkeypatch.setattr(c, 'run_phase', fake)
    assert c.run(STUDY / 'protocol.json', output.parent, output) == 1
    synthetic = common.read_rows(output / 'unexecuted.jsonl')
    assert len(synthetic) == 110
    assert first['unit_id'] not in {r['unit_id'] for r in synthetic}


def test_inventory_records_symlinks_without_following_targets(setup, monkeypatch):
    c, identity, output = setup
    def fake(phase, **kwargs):
        emit(c, identity, phase, 'timeout')
        (phase.output / 'external-link').symlink_to('/outside/missing')
        return {'status': 'exited', 'returncode': 1}
    monkeypatch.setattr(c, 'run_phase', fake)
    c.run(STUDY / 'protocol.json', output.parent, output)
    inventory = json.loads((output / 'analysis/raw-inventory.json').read_text())
    item = next(p for p in inventory if p['path'] == 'fault_matrix/external-link')
    assert item['type'] == 'symlink' and item['target'] == '/outside/missing'
    assert len(item['sha256']) == 64


def test_unit_snapshot_recovered_when_phase_dies_before_canonical_append(setup, monkeypatch):
    c, identity, output = setup
    first = common.declared_units(common.load_protocol(STUDY / 'protocol.json'))[0]
    def fake(phase, **kwargs):
        unit = phase.output / first['unit_id'].replace('/', '__')
        unit.mkdir(parents=True)
        (unit / 'row.json').write_text(json.dumps(dict(schema_version=1, study_id='authority_replay_v1',
            **first, identity=identity, status='failed', metrics={}, reason='emitted before process crash')))
        return {'status': 'exited', 'returncode': 2}
    monkeypatch.setattr(c, 'run_phase', fake)
    c.run(STUDY / 'protocol.json', output.parent, output)
    summary = json.loads((output / 'analysis/summary.json').read_text())
    assert summary['status_counts']['failed'] == 1
    assert summary['status_counts']['incomplete'] == 110
    assert summary['rows'][0]['reason'] == 'emitted before process crash'


def test_inconsistent_unit_snapshot_fails_analysis(setup, monkeypatch):
    c, identity, output = setup
    first = common.declared_units(common.load_protocol(STUDY / 'protocol.json'))[0]
    def fake(phase, **kwargs):
        emit(c, identity, phase, 'timeout')
        unit = phase.output / first['unit_id'].replace('/', '__')
        unit.mkdir()
        (unit / 'row.json').write_text(json.dumps(dict(schema_version=1, study_id='authority_replay_v1',
            **first, identity=identity, status='completed', metrics={})))
        return {'status': 'exited', 'returncode': 0}
    monkeypatch.setattr(c, 'run_phase', fake)
    assert c.run(STUDY / 'protocol.json', output.parent, output) == 1
    manifest = json.loads((output / 'analysis/campaign-manifest.json').read_text())
    assert 'inconsistent' in manifest['analysis_error']
