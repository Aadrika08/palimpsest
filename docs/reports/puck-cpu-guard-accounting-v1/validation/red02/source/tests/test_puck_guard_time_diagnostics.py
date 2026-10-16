"""Bounded guard diagnostics with authored packages; no installed qualification."""
import json

import pytest

from test_puck_cpu_phase_trace import PHASES, run_cpu, traces


CONTEXTS = ['import.'+name+'.'+boundary for name in
            ('numpy', 'torch', 'torchvision', 'mujoco') for boundary in ('enter', 'returned')]
SECTIONS = {'bindings', 'cache', 'custody', 'images'}


def costs(stderr):
    rows = []
    for line in stderr.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get('kind') == 'puck-worker-guard-cost-v1':
            rows.append((line, row))
    return rows


def test_guard_costs_cover_import_boundaries_without_changing_phase_or_terminal():
    result = run_cpu()
    assert result.returncode == 0, result.stderr
    rows = costs(result.stderr)
    assert [row['context'] for _, row in rows] == CONTEXTS
    assert [row['sequence'] for _, row in rows] == list(range(1, 9))
    previous = {name: 0 for name in SECTIONS}
    for line, row in rows:
        assert len(line.encode())+1 <= 1024
        assert row['diagnostic_only'] is True and row['active'] is None
        assert set(row['sections']) == SECTIONS
        for name, section in row['sections'].items():
            assert type(section['nanoseconds']) is int and section['nanoseconds'] >= previous[name]
            assert type(section['visits']) is int and section['visits'] >= 1
            previous[name] = section['nanoseconds']
        for mode in ('full', 'light'):
            assert row[mode]['started'] == row[mode]['completed']
            assert row[mode]['completed'] > 0
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES
    receipt = json.loads(result.stdout)
    assert receipt['entry_result']['status'] == 'imports_completed'
    assert receipt['runtime_qualified'] is receipt['collection_authorized'] is False
    assert 'guard_cost' not in receipt


def test_periodic_checkpoint_records_active_guard_and_does_not_catch_up():
    result = run_cpu(code=('import sys\nowner = sys.meta_path[0].owner\n'
        'owner._guard_next = 0\nowner._import_recheck()\n'))
    assert result.returncode == 0, result.stderr
    rows = [row for _, row in costs(result.stderr)]
    active = [row for row in rows if row['active'] is not None]
    assert len(active) == 1
    assert active[0]['context'] == 'import.torchvision.enter'
    assert active[0]['active'] == {'section':'bindings', 'full':False}
    assert active[0]['light']['started'] == active[0]['light']['completed']+1


def test_cost_record_budget_is_independent_of_phase_budget():
    result = run_cpu(code=('import sys\nowner = sys.meta_path[0].owner\n'
        'for _ in range(40): owner._guard_emit(force=True)\n'))
    assert result.returncode == 0, result.stderr
    rows = costs(result.stderr)
    assert len(rows) == 32
    assert [row['sequence'] for _, row in rows] == list(range(1, 33))
    assert sum(len(line.encode())+1 for line, _ in rows) <= 32768
    assert all(len(line.encode())+1 <= 1024 for line, _ in rows)
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES


def test_cost_byte_budget_refuses_the_next_row_without_affecting_phase():
    result = run_cpu(code=('import sys\nowner = sys.meta_path[0].owner\n'
        'owner._guard_bytes = 32760\nowner._guard_emit(force=True)\n'))
    assert result.returncode == 0, result.stderr
    assert [row['context'] for _, row in costs(result.stderr)] == CONTEXTS[:5]
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES


@pytest.mark.parametrize('bad', ['-1', 'float("nan")'])
def test_bad_accounting_clock_disables_only_costs(bad):
    result = run_cpu(code=('import sys,time\nowner = sys.meta_path[0].owner\n'
        'original = time.monotonic_ns\ntime.monotonic_ns = lambda: '+bad+'\n'
        'try:\n owner._import_recheck()\nfinally:\n time.monotonic_ns = original\n'))
    assert result.returncode == 0, result.stderr
    assert [row['context'] for _, row in costs(result.stderr)] == CONTEXTS[:5]
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES


@pytest.mark.parametrize('field', ['_guard_sections', '_guard_checks'])
def test_malformed_accounting_state_preserves_real_operation(field):
    result = run_cpu(code=('import sys\nowner = sys.meta_path[0].owner\n'
        'setattr(owner, '+repr(field)+', None)\nowner._import_recheck()\n'))
    assert result.returncode == 0, result.stderr
    assert [row['context'] for _, row in costs(result.stderr)] == CONTEXTS[:5]
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES


@pytest.mark.parametrize('writer', ['short', 'error'])
@pytest.mark.parametrize('primary_failure', [False, True])
def test_cost_io_failure_latches_both_channels_and_preserves_outcome(writer, primary_failure):
    code = ('import os,sys\nowner = sys.meta_path[0].owner\noriginal = os.write\ncalls = 0\n'
        'def write(fd, payload):\n global calls\n calls += 1\n'
        ' if calls > 1: raise AssertionError("DIAGNOSTIC_IO_RETRIED")\n'
        + (' return len(payload)-1\n' if writer == 'short' else ' raise OSError("AUTHORED_COST_IO")\n')
        + 'os.write = write\nowner._guard_emit(force=True)\nowner._guard_emit(force=True)\n'
        'owner._phase("authored.no_retry")\nos.write = original\n'
        'assert calls == 1, "DIAGNOSTIC_IO_RETRIED"\n')
    if primary_failure:
        code += 'raise RuntimeError("AUTHORED_PRIMARY_FAILURE")\n'
    result = run_cpu(code=code)
    assert 'DIAGNOSTIC_IO_RETRIED' not in result.stderr, result.stderr
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:11]
    if primary_failure:
        assert result.returncode != 0 and result.stdout == ''
        assert 'AUTHORED_PRIMARY_FAILURE' in result.stderr
    else:
        assert result.returncode == 0, result.stderr


def test_nested_cost_write_is_suppressed():
    result = run_cpu(code=('import os,sys\nowner = sys.meta_path[0].owner\noriginal = os.write\ncalls = 0\n'
        'def write(fd, payload):\n global calls\n calls += 1\n'
        ' owner._guard_emit(force=True)\n return original(fd, payload)\n'
        'os.write = write\nowner._guard_emit(force=True)\nos.write = original\n'
        'assert calls == 1, "NESTED_COST_WRITE"\n'))
    assert result.returncode == 0, result.stderr
    assert len(costs(result.stderr)) == 9


def test_successful_cost_write_cannot_rearm_nested_phase_io_failure():
    result = run_cpu(code=('import os,sys\nowner = sys.meta_path[0].owner\noriginal = os.write\ncalls = 0\n'
        'def write(fd, payload):\n global calls\n calls += 1\n'
        ' if calls == 1:\n  owner._phase("authored.nested")\n  return len(payload)\n'
        ' raise OSError("AUTHORED_NESTED_PHASE_IO")\n'
        'os.write = write\nowner._guard_emit(force=True)\nowner._guard_emit(force=True)\n'
        'owner._phase("authored.no_retry")\nos.write = original\n'
        'assert calls == 2, "NESTED_IO_LATCH_REARMED"\n'))
    assert result.returncode == 0, result.stderr
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:11]


def test_cost_cancellation_propagates_after_owned_close():
    result = run_cpu(package='mujoco', code=('import os,sys\n'
        'def install():\n owner = sys.meta_path[0].owner\n original_close = owner._close\n original_write = os.write\n'
        ' def close(error=None):\n  result = original_close(error)\n  os.write = original_write\n'
        '  assert not owner._children and not owner._early_runtime_fds\n'
        '  original_write(2, b"AUTHORED_COST_CANCEL_CLOSED\\n")\n  return result\n'
        ' def cancel(fd, payload):\n  raise KeyboardInterrupt("AUTHORED_COST_CANCEL")\n'
        ' owner._close = close\n os.write = cancel\n owner._guard_emit(force=True)\ninstall()\n'))
    assert result.returncode != 0 and result.stdout == ''
    assert 'KeyboardInterrupt: AUTHORED_COST_CANCEL' in result.stderr, result.stderr
    assert 'AUTHORED_COST_CANCEL_CLOSED' in result.stderr
