"""Small verifier fixtures exercise accounting without starting simulator owners."""
import importlib
import json
from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from paper.studies.authority_replay_v1.common import load_protocol, declared_units
from paper.studies.authority_replay_v1.analyze import summarize

REPO = Path(__file__).resolve().parents[4]
PROTOCOL = load_protocol(REPO / 'paper/studies/authority_replay_v1/protocol.json')
IDENTITY = {'commit': 'a' * 40, 'protocol_sha256': PROTOCOL._content_sha256,
            'runtime_source_sha256': {'fixture.py': 'b' * 64},
            'asset_manifest_sha256': {'manifest': 'c' * 64}, 'asset_sha256': {'asset': 'd' * 64}}


def driver():
    assert importlib.util.find_spec('paper.studies.authority_replay_v1.repeatability') is not None, 'repeatability driver missing'
    return importlib.import_module('paper.studies.authority_replay_v1.repeatability')


def fixture_runner(command, output, **limits):
    output.mkdir()
    options = dict(zip(command[2::2], command[3::2]))
    (output / 'continuation.snapshot').write_bytes(b'fixture snapshot')
    replay = 'verify_lab.py' in command[1]
    report = {'status': 'passed', 'snapshot_sha256': 'b' * 64, 'snapshot_bytes': 16,
              'prefix_ticks': int(options['--prefix']), 'continuation_ticks': int(options['--continuation']),
              'first_divergence': None, 'max_abs_errors': {'action': 0.0},
              'random_draws_match': True, 'source_event_prefix_unchanged': True,
              'branch_identity_distinct': True, 'queued_command_idempotency': True}
    if replay:
        report.update(continuation={'status': 'passed', 'divergences': [], 'max_abs_errors': {'action': 0.0}},
                      playback={'mode': 'playback', 'first_tick': 8},
                      replays={m: {'run_id': m, 'report': {'status': 'passed', 'first_divergence': None,
                          'compared_ticks': 100, 'compared_events': 2, 'comparison': {'fields': 'all'},
                          'controller_reexecuted': m == 'policy', 'inference_executed': m == 'policy'}}
                               for m in ('actions', 'policy')},
                      timings={'branch_seconds': .1, 'playback_seconds': .2, 'action_replay_seconds': .3,
                               'policy_replay_seconds': .4})
    (output / 'verification.json').write_text(json.dumps(report))
    return {'status': 'completed', 'returncode': 0}


@pytest.mark.parametrize('kind,seed,ticks', [('continuation', 9, 100), ('replay', 4, 92)])
def test_protocol_bounds_seed_and_paired_fields(tmp_path, kind, seed, ticks):
    m = driver()
    calls = []
    def run(command, output, **limits):
        calls.append((command, limits))
        return fixture_runner(command, output, **limits)
    row = getattr(m, f'run_{kind}_unit')(seed, tmp_path / kind, IDENTITY, protocol=PROTOCOL,
                                       repo=REPO, assets=tmp_path, runner=run)
    command, limits = calls[0]
    assert command[command.index('--seed') + 1] == str(seed)
    assert command[command.index('--prefix') + 1] == '8'
    assert command[command.index('--continuation') + 1] == str(ticks)
    assert row['status'] == 'completed'
    assert row['metrics']['agreement'] is True
    assert row['first_divergence'] is None
    assert row['metrics']['snapshot_bytes'] == 16
    assert limits['timeout'] <= 900 and limits['max_bytes'] < 512 * 1024**2
    assert row['comparison_policy'] == PROTOCOL.comparison_policy
    if kind == 'replay':
        assert list(row['paired_raw_values']) == PROTOCOL.replay['conditions']
        assert row['paired_raw_values']['policy_replay']['executed_computation']['inference_executed']
        assert not row['paired_raw_values']['action_replay']['executed_computation']['inference_executed']
        assert row['paired_raw_values']['playback']['validated_fields']
        assert row['metrics']['policy_replay_seconds'] == .4


def test_failure_retained_no_retry_and_analyzer_accepts(tmp_path):
    m = driver()
    calls = []
    def fail(command, output, **limits):
        calls.append(command)
        output.mkdir()
        (output / 'partial').write_text('retained')
        return {'status': 'failed', 'returncode': 7}
    failed = m.run_continuation_unit(0, tmp_path / 'unit', IDENTITY, protocol=PROTOCOL,
                                     repo=REPO, assets=tmp_path, runner=fail)
    assert failed['status'] == 'failed' and len(calls) == 1
    assert (tmp_path / 'unit/raw/partial').read_text() == 'retained'
    assert json.loads((tmp_path / 'unit/row.json').read_text()) == failed
    rows = [{'schema_version': 1, 'study_id': PROTOCOL.study_id, **u, 'identity': IDENTITY,
             'status': 'incomplete', 'metrics': {}} for u in declared_units(PROTOCOL)]
    rows = [failed if r['unit_id'] == failed['unit_id'] else r for r in rows]
    assert summarize(PROTOCOL, rows)['failures']
    with pytest.raises(ValueError, match='empty|fresh|non-empty'):
        m.run_continuation_unit(0, tmp_path / 'unit', IDENTITY, protocol=PROTOCOL, runner=fail)


def test_admission_refuses_without_starting(tmp_path, monkeypatch):
    m = driver()
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda p: SimpleNamespace(free=6 * 1024**3))
    def forbidden(*args, **kwargs):
        pytest.fail('unit started without reserve for its full output budget')
    row = m.run_replay_unit(0, tmp_path / 'unit', IDENTITY, protocol=PROTOCOL, runner=forbidden)
    assert row['status'] == 'refused' and row['metrics']['agreement'] is None


def test_failed_mode_preserves_all_four_conditions(tmp_path):
    m = driver()
    def fail_mode(command, output, **limits):
        result = fixture_runner(command, output, **limits)
        report = json.loads((output / 'verification.json').read_text())
        report['status'] = 'failed'
        report['replays']['policy']['report'].update(status='failed', first_divergence={'field': 'action', 'tick': 9})
        (output / 'verification.json').write_text(json.dumps(report))
        return result
    row = m.run_replay_unit(0, tmp_path / 'unit', IDENTITY, protocol=PROTOCOL, runner=fail_mode)
    assert row['status'] == 'failed'
    assert len(row['paired_raw_values']) == 4
    assert row['first_divergence'] == {'field': 'action', 'tick': 9}


def test_partial_report_cannot_claim_agreement(tmp_path):
    m = driver()
    def incomplete(command, output, **limits):
        output.mkdir()
        (output / 'verification.json').write_text('{"status": "passed"}')
        return {'status': 'completed', 'returncode': 0}
    row = m.run_replay_unit(0, tmp_path / 'unit', IDENTITY, protocol=PROTOCOL, runner=incomplete)
    assert row['status'] == 'failed' and row['metrics']['agreement'] is not True


def test_policy_mode_without_inference_is_never_policy_agreement(tmp_path):
    m = driver()
    def mislabeled(command, output, **limits):
        result = fixture_runner(command, output, **limits)
        report = json.loads((output / 'verification.json').read_text())
        report['replays']['policy']['report']['inference_executed'] = False
        (output / 'verification.json').write_text(json.dumps(report))
        return result
    row = m.run_replay_unit(0, tmp_path / 'unit', IDENTITY, protocol=PROTOCOL, runner=mislabeled)
    assert row['status'] == 'failed'
    assert row['paired_raw_values']['policy_replay']['agreement'] is False


def test_process_timeout_retains_logs(tmp_path):
    import sys
    m = driver()
    row = m._process([sys.executable, '-c', 'import time; print("started", flush=True); time.sleep(10)'],
                     tmp_path / 'raw', timeout=.2, max_bytes=1024**2, minimum_free_bytes=0)
    assert row['status'] == 'timeout'
    assert row['returncode'] != 0
    assert 'started' in (tmp_path / 'stdout.log').read_text()


def test_process_output_monitor_retains_failure(tmp_path):
    import sys
    m = driver()
    row = m._process([sys.executable, '-c', 'import time; print("x"*2048, flush=True); time.sleep(10)'],
                     tmp_path / 'raw', timeout=2, max_bytes=1024, minimum_free_bytes=0)
    assert row['status'] == 'failed' and row['stop_reason'] == 'unit output cap'
    assert (tmp_path / 'stdout.log').stat().st_size > 0


def test_timeout_kills_nested_worker_process_groups(tmp_path):
    import os
    import sys
    import time
    m = driver()
    pidfile = tmp_path / 'worker.pid'
    worker = 'import time; time.sleep(10)'
    code = ('import subprocess,sys,time,pathlib; '
            f'p=subprocess.Popen([sys.executable,"-c",{worker!r}],start_new_session=True); '
            f'pathlib.Path({str(pidfile)!r}).write_text(str(p.pid)); time.sleep(10)')
    m._process([sys.executable, '-c', code], tmp_path / 'raw', timeout=.3,
               max_bytes=1024**2, minimum_free_bytes=0)
    pid = int(pidfile.read_text())
    # A killed child can briefly remain a zombie until the host reaps it.
    state = Path(f'/proc/{pid}/stat')
    def alive():
        try:
            return state.read_text().split()[2] != 'Z'
        except (FileNotFoundError, ProcessLookupError):
            return False
    try:
        deadline = time.monotonic() + 1
        while alive() and time.monotonic() < deadline:
            time.sleep(.01)
        assert not alive()
    finally:
        if alive():
            os.killpg(pid, 9)  # Clean up only this test's known worker.


def test_timeout_with_partial_report_remains_timeout(tmp_path):
    m = driver()
    def timed_out(command, output, **limits):
        output.mkdir()
        (output / 'verification.json').write_text('{"status": "running"}')
        return {'status': 'timeout', 'returncode': -9, 'stop_reason': 'unit wall-clock cap'}
    row = m.run_replay_unit(0, tmp_path / 'unit', IDENTITY, protocol=PROTOCOL, runner=timed_out)
    assert row['status'] == 'timeout'
    assert len(row['paired_raw_values']) == 4


def test_fixture_dry_units_pass_complete_denominator_analysis(tmp_path):
    m = driver()
    rows = [{'schema_version': 1, 'study_id': PROTOCOL.study_id, **u, 'identity': IDENTITY,
             'status': 'incomplete', 'metrics': {}} for u in declared_units(PROTOCOL)]
    for kind in ('continuation', 'replay'):
        row = getattr(m, f'run_{kind}_unit')(0, tmp_path / kind, IDENTITY,
                                            protocol=PROTOCOL, runner=fixture_runner)
        assert row['status'] == 'completed'
        rows = [row if old['unit_id'] == row['unit_id'] else old for old in rows]
    summary = summarize(PROTOCOL, rows)
    assert summary['by_kind']['continuation']['status_counts']['completed'] == 1
    assert summary['by_kind']['replay']['status_counts']['completed'] == 1


def test_expired_shared_campaign_deadline_retains_every_seed(tmp_path, monkeypatch):
    import time
    m = driver()
    monkeypatch.setattr(m, '_unit', lambda *a, **k: pytest.fail('expired campaign launched a unit'))
    rows = m.run_campaign('replay', PROTOCOL, tmp_path / 'replay', IDENTITY,
                          deadline=time.time() - 1, campaign_root=tmp_path)
    assert [row['seed'] for row in rows] == list(range(5))
    assert all(row['status'] == 'incomplete' for row in rows)


def test_campaign_admission_counts_all_driver_subroots(tmp_path, monkeypatch):
    import time
    m = driver()
    scanned = []
    def size(root):
        scanned.append(Path(root))
        return PROTOCOL.resources['campaign_max_output_bytes']
    monkeypatch.setattr(m, '_size', size)
    monkeypatch.setattr(m, '_unit', lambda *a, **k: pytest.fail('full campaign launched a unit'))
    rows = m.run_campaign('replay', PROTOCOL, tmp_path / 'replay', IDENTITY,
                          deadline=time.time() + 100, campaign_root=tmp_path)
    assert all(row['status'] == 'incomplete' for row in rows)
    assert scanned and all(root == tmp_path for root in scanned)


def test_campaign_clock_is_reused_without_restarting(tmp_path, monkeypatch):
    m = driver()
    monkeypatch.setattr(m.time, 'time', lambda: 100.)
    first = m._campaign_deadline(tmp_path, IDENTITY, 14400)
    monkeypatch.setattr(m.time, 'time', lambda: 999.)
    assert m._campaign_deadline(tmp_path, IDENTITY, 14400) == first == 14500.


def test_continuation_divergence_exposes_field_and_tick(tmp_path):
    m = driver()
    def divergent(command, output, **limits):
        result = fixture_runner(command, output, **limits)
        report = json.loads((output / 'verification.json').read_text())
        report.update(status='failed', first_divergence={'component': 'action', 'tick': 8})
        (output / 'verification.json').write_text(json.dumps(report))
        return result
    row = m.run_continuation_unit(0, tmp_path / 'unit', IDENTITY, protocol=PROTOCOL, runner=divergent)
    assert row['first_divergence']['field'] == 'action' and row['first_divergence']['tick'] == 8


def test_explicit_deadline_cannot_extend_persisted_campaign_clock(tmp_path, monkeypatch):
    import time
    m = driver()
    (tmp_path / 'campaign-clock.json').write_text(json.dumps(
        {'identity': IDENTITY, 'started_unix': 0, 'deadline_unix': 1}))
    monkeypatch.setattr(m, '_unit', lambda *a, **k: pytest.fail('extended expired campaign clock'))
    rows = m.run_campaign('replay', PROTOCOL, tmp_path / 'replay', IDENTITY,
                          deadline=time.time() + 100, campaign_root=tmp_path)
    assert all(row['status'] == 'incomplete' for row in rows)


def test_nonfinite_report_is_retained_as_failed_row(tmp_path):
    m = driver()
    def nonfinite(command, output, **limits):
        result = fixture_runner(command, output, **limits)
        report = json.loads((output / 'verification.json').read_text())
        report['timings'] = {'policy_replay_seconds': float('nan')}
        (output / 'verification.json').write_text(json.dumps(report))
        return result
    row = m.run_replay_unit(0, tmp_path / 'unit', IDENTITY, protocol=PROTOCOL, runner=nonfinite)
    assert row['status'] == 'failed'
    assert json.loads((tmp_path / 'unit/row.json').read_text()) == row
