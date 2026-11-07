"""Pure operational wrapper fixtures; no offline setup, model, or campaign jobs."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/run_offline_followup.py'
spec = importlib.util.spec_from_file_location('offline_followup', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


@pytest.fixture(autouse=True)
def clock_before_frozen_deadline(monkeypatch):
    """The follow-up's ORIGINAL_DEADLINE is a frozen historical instant; run the
    fixtures one hour before it so they keep testing guards, not today's date."""
    import time as real
    start, base = real.time(), m.ORIGINAL_DEADLINE - 3600
    monkeypatch.setattr(m, 'time', SimpleNamespace(**{
        k: getattr(real, k) for k in dir(real) if not k.startswith('_') and k != 'time'},
        time=lambda: base + (real.time() - start)))


def test_deadline_never_extends_unit_or_original_budget():
    assert m.deadline(100., 2000.) == 1000.
    assert m.deadline(m.ORIGINAL_DEADLINE - 100, m.ORIGINAL_DEADLINE + 200) == m.ORIGINAL_DEADLINE
    assert m.deadline(100., 150.) == 150.
    for value in (0., float('inf'), float('nan')):
        with pytest.raises(ValueError, match='deadline'):
            m.deadline(100., value)


@pytest.mark.parametrize('case', ['commit', 'hash', 'path'])
def test_source_pins_refuse_mismatch(tmp_path, monkeypatch, case):
    protocol = tmp_path / 'paper/studies/authority_replay_v1/protocol.json'
    monkeypatch.setattr(m, 'git', lambda *args: 'wrong' if case == 'commit' else m.FROZEN_COMMIT)
    monkeypatch.setattr(m, 'digest', lambda *args: 'wrong' if case == 'hash' else m.PROTOCOL_SHA256)
    with pytest.raises(ValueError, match='differs|protocol'):
        m.pins(tmp_path, tmp_path / 'wrong' if case == 'path' else protocol)


def test_locations_refuse_missing_roots_overlap_and_existing(tmp_path, monkeypatch):
    roots = [tmp_path / name for name in ('old', 'interrupted', 'final')]
    for path in roots:
        path.mkdir()
    monkeypatch.setattr(m, 'required_roots', lambda _: set(roots))
    m.locations(tmp_path, roots, tmp_path / 'new')
    for output, retained in ((roots[0] / 'new', roots), (tmp_path, roots),
                             (tmp_path / 'new', roots[:2]), (roots[0], roots)):
        with pytest.raises(ValueError):
            m.locations(tmp_path, retained, output)


def test_cumulative_guard_reserves_reports_and_preserves_all_roots(tmp_path):
    roots = [tmp_path / str(n) for n in range(3)]
    followup = tmp_path / 'followup'
    seen = []
    class Base:
        def check(self):
            seen.append('base')
        def check_identity(self):
            seen.append('identity')
    sizes = {root: 1 for root in roots}
    sizes[followup] = m.TOTAL_CAP - m.REPORT_RESERVE - 3
    sizes[followup / 'offline_reproduction'] = 1
    campaign = SimpleNamespace(tree_size=lambda root: sizes[root])
    guard = m.CumulativeGuard(Base(), campaign, roots, followup, m.ORIGINAL_DEADLINE, m.digest(m.SCRIPT))
    guard.check_identity()
    guard.check()
    assert seen == ['identity', 'base']
    sizes[followup] += 1
    with pytest.raises(ValueError, match='cumulative'):
        guard.check()
    sizes[followup] -= 1
    sizes[followup / 'offline_reproduction'] = 10 * m.GiB + 1
    with pytest.raises(ValueError, match='unit cap'):
        guard.check()


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    roots = [tmp_path / name for name in ('old', 'interrupted', 'final')]
    original = {}
    for root in roots:
        (root / 'analysis').mkdir(parents=True)
        (root / 'analysis/summary.json').write_text('{"scientific":"unchanged"}')
        original[root] = (root / 'analysis/summary.json').read_bytes()
    args = argparse.Namespace(frozen_repo=tmp_path / 'repo', protocol=tmp_path / 'protocol', assets=tmp_path,
                              retained_root=roots, output=tmp_path / 'followup',
                              deadline=m.ORIGINAL_DEADLINE, plan_only=False)
    monkeypatch.setattr(m, 'required_roots', lambda _: set(roots))
    monkeypatch.setattr(m, 'pins', lambda *args: None)
    monkeypatch.setattr(m, 'git', lambda *args: 'launcher-commit')
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda _: SimpleNamespace(free=100 * m.GiB))
    calls = []
    class Base:
        def __init__(self, *args):
            pass
        def check(self):
            pass
        def check_identity(self):
            pass
    def size(root):
        return sum(path.stat().st_size for path in root.rglob('*') if path.is_file()) if root.exists() else 0
    def launch(phase, **kwargs):
        calls.append(phase.command)
        phase.output.mkdir()
        (phase.output / 'report.json').write_text('{"status":"passed"}')
        return {'status': 'exited', 'returncode': 0}
    frozen = SimpleNamespace(Guard=Base, tree_size=size, campaign_identity=lambda *a: {'commit': m.FROZEN_COMMIT},
        plan=lambda p,a,o,d: [SimpleNamespace(kind='offline_reproduction', output=o/'offline_reproduction',
            command=['verify_offline.py', '--setup', '--full-flynn', '--duration', '55'])],
        run_phase=launch, offline_row=lambda *a: {'status': 'completed'})
    monkeypatch.setattr(m, 'load_frozen', lambda _: frozen)
    return args, roots, original, calls, frozen


def test_followup_separate_result_never_replaces_scientific_row(fixture):
    args, roots, original, calls, frozen = fixture
    assert m.run(args) == 0
    result = json.loads((args.output / 'operational-result.json').read_text())
    assert result['status'] == 'passed' and result['replaces_scientific_row'] is False
    assert result['scientific_campaign_unit_id'] is None
    assert len(calls) == 1 and calls[0][-4:] == ['--setup', '--full-flynn', '--duration', '55']
    assert not list(args.output.rglob('rows.jsonl'))
    assert all((root / 'analysis/summary.json').read_bytes() == original[root] for root in roots)
    assert result['retained_metadata_unchanged']


def test_plan_only_and_expired_deadline_do_not_launch_or_create_output(fixture, capsys):
    args, roots, original, calls, frozen = fixture
    args.plan_only = True
    assert m.run(args) == 0
    assert calls == [] and not args.output.exists()
    assert json.loads(capsys.readouterr().out)['replaces_scientific_row'] is False
    args.deadline = 0.
    with pytest.raises(ValueError, match='deadline'):
        m.run(args)
    assert calls == [] and not args.output.exists()


def test_refused_free_space_never_launches(fixture, monkeypatch):
    args, roots, original, calls, frozen = fixture
    monkeypatch.setattr(m.shutil, 'disk_usage', lambda _: SimpleNamespace(free=6*m.GiB))
    with pytest.raises(ValueError, match='reserve'):
        m.run(args)
    assert calls == [] and not args.output.exists()


def test_monitor_cleanup_failure_retained_as_failed_operational_result(fixture):
    args, roots, original, calls, frozen = fixture
    frozen.run_phase = lambda *a, **k: {'status': 'failed', 'returncode': 1, 'cleanup_error': 'fixture'}
    assert m.run(args) == 1
    report = json.loads((args.output / 'operational-result.json').read_text())
    assert report['status'] == 'failed' and 'cleanup' in report['error']['message']
    assert all((root / 'analysis/summary.json').read_bytes() == original[root] for root in roots)
