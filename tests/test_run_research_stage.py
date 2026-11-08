"""Stage launcher: ledger admission (pure) and a real delegated-cgroup census (tiny workloads)."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

import run_research_stage as stage

SCRIPT = Path(stage.__file__).resolve()


def _go(tmp_path, lane='puck', name='S1'):
    path = tmp_path / f'go-{lane}-{name}.json'
    path.write_text(json.dumps({'lane': lane, 'stage': name, 'granted_by': 'test',
                                'granted_at': 'now', 'protocol_sha256': 'f' * 64}))
    return path


def test_admission_refuses_lane_cap_retry_and_counts_reservations():
    rows = [{'lane': 'puck', 'stage': 'S0a', 'event': 'reserved', 'cpu_seconds': 17000.0}]
    with pytest.raises(ValueError, match='exceeds cap'):
        stage.admit(rows, 'puck', 'S1', 1001)
    assert stage.admit(rows, 'puck', 'S1', 1000)['puck'] == 17000.0
    with pytest.raises(ValueError, match='no retries'):
        stage.admit(rows, 'puck', 'S0a', 1)
    rows.append({'lane': 'puck', 'stage': 'S0a', 'event': 'charged', 'cpu_seconds': 12.5})
    assert stage.lane_totals(rows)['puck'] == 12.5


def test_admission_refuses_aggregate_cap():
    rows = [{'lane': lane, 'stage': 'x', 'event': 'charged', 'cpu_seconds': cap}
            for lane, cap in stage.LANE_CAPS.items() if lane != 'final']
    rows.append({'lane': 'final', 'stage': 'x', 'event': 'charged', 'cpu_seconds': 7000.0})
    with pytest.raises(ValueError, match='lane final|aggregate'):
        stage.admit(rows, 'final', 'y', 300)


def _systemd_user_available():
    try:
        env = stage.user_bus_env()
    except ValueError:
        return False
    return bool(shutil.which('systemd-run')) and subprocess.run(
        ['systemctl', '--user', 'is-system-running'], capture_output=True,
        env=env).returncode in (0, 1)


needs_systemd = pytest.mark.skipif(not _systemd_user_available(),
                                   reason='needs a systemd user manager with cgroup delegation')


def _run(tmp_path, code, *, worst=60, runtime=20, name='S1'):
    ledger = tmp_path / 'ledger.jsonl'
    receipt = tmp_path / f'receipt-{name}'
    result = subprocess.run([sys.executable, '-B', str(SCRIPT), '--ledger', str(ledger),
                             '--lane', 'puck', '--stage', name, '--go-record',
                             str(_go(tmp_path, name=name)), '--worst-case-cpu', str(worst),
                             '--runtime-max-sec', str(runtime), '--receipt-dir', str(receipt),
                             '--', sys.executable, '-c', code], capture_output=True, text=True)
    return result, stage.read_ledger(ledger), receipt


@needs_systemd
def test_census_counts_grandchild_cpu_and_charges_measured(tmp_path):
    code = ("import subprocess,sys,time\n"
            "c=subprocess.Popen([sys.executable,'-c','t=__import__(\"time\").process_time\\n"
            "s=t()\\nwhile t()-s<0.4: pass'])\n"
            "c.wait()")
    result, rows, receipt = _run(tmp_path, code)
    assert result.returncode == 0, result.stderr
    data = json.loads((receipt / 'receipt.json').read_text())
    assert data['drained'] and data['returncode'] == 0
    assert 0.35 < data['work_cpu_seconds'] < 5
    charged = [row for row in rows if row['event'] == 'charged'][0]
    assert charged['cpu_seconds'] == round(data['cpu_seconds'], 6)
    assert charged['basis'].startswith('measured')


@needs_systemd
def test_runtime_kill_without_receipt_charges_worst_case(tmp_path):
    result, rows, receipt = _run(tmp_path, 'import time; time.sleep(30)', worst=10, runtime=3)
    assert result.returncode != 0
    assert (receipt / 'stdout.log').exists()  # the unit really started before its kill
    assert not (receipt / 'receipt.json').exists()
    charged = [row for row in rows if row['event'] == 'charged'][0]
    assert charged['cpu_seconds'] == 10.0 and 'worst case' in charged['basis']


def test_refuses_worst_case_below_wall_bound_and_wrong_go(tmp_path):
    result, rows, _ = _run(tmp_path, 'pass', worst=5, runtime=20)
    assert result.returncode == 2 and 'cover k x' in result.stderr and rows == []
    go = _go(tmp_path, name='S2')
    out = subprocess.run([sys.executable, '-B', str(SCRIPT), '--ledger', str(tmp_path / 'l'),
                          '--lane', 'puck', '--stage', 'S1', '--go-record', str(go),
                          '--worst-case-cpu', '60', '--runtime-max-sec', '20',
                          '--receipt-dir', str(tmp_path / 'r'), '--', 'true'],
                         capture_output=True, text=True)
    assert out.returncode == 2 and 'GO record names' in out.stderr
