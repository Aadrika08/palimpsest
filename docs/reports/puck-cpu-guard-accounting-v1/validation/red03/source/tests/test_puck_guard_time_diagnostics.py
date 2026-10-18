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


def checkpoints(stderr):
    return [(line, row) for line, row in costs(stderr) if row['trigger'] == 'checkpoint']


def test_guard_costs_cover_import_boundaries_without_changing_phase_or_terminal():
    result = run_cpu()
    assert result.returncode == 0, result.stderr
    rows = checkpoints(result.stderr)
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
    result = run_cpu(code=('import sys,time\nowner = sys.meta_path[0].owner\n'
        'original = time.monotonic_ns\nanchor = original()\nbefore = owner._guard_count\n'
        'time.monotonic_ns = lambda: anchor\n'
        'try:\n owner._guard_next = 0\n owner._import_recheck()\n'
        ' assert owner._guard_count == before+1, "PERIODIC_CATCH_UP"\n'
        'finally:\n time.monotonic_ns = original\n'))
    assert result.returncode == 0, result.stderr
    rows = [row for _, row in costs(result.stderr)]
    active = [row for row in rows if row['active'] is not None]
    assert any(row['context'] == 'import.torchvision.enter'
        and row['active'] == {'section':'bindings', 'full':False}
        and row['light']['started'] == row['light']['completed']+1 for row in active)


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
    assert [row['context'] for _, row in checkpoints(result.stderr)] == CONTEXTS[:5]
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES


@pytest.mark.parametrize('bad', ['-1', 'float("nan")'])
def test_bad_accounting_clock_disables_only_costs(bad):
    result = run_cpu(code=('import sys,time\nowner = sys.meta_path[0].owner\n'
        'original = time.monotonic_ns\ntime.monotonic_ns = lambda: '+bad+'\n'
        'try:\n owner._import_recheck()\nfinally:\n time.monotonic_ns = original\n'))
    assert result.returncode == 0, result.stderr
    assert [row['context'] for _, row in checkpoints(result.stderr)] == CONTEXTS[:5]
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES


@pytest.mark.parametrize('field', ['_guard_sections', '_guard_checks'])
def test_malformed_accounting_state_preserves_real_operation(field):
    result = run_cpu(code=('import sys\nowner = sys.meta_path[0].owner\n'
        'setattr(owner, '+repr(field)+', None)\nowner._import_recheck()\n'))
    assert result.returncode == 0, result.stderr
    assert [row['context'] for _, row in checkpoints(result.stderr)] == CONTEXTS[:5]
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
    assert len(checkpoints(result.stderr)) == 9


def test_real_nested_guard_is_charged_to_outer_section_once():
    result = run_cpu(code=('import sys,types\nowner = sys.meta_path[0].owner\n'
        'triggered = False\n'
        'class NestedName(str):\n'
        ' def split(self, *args):\n  global triggered\n'
        '  if not triggered:\n   triggered = True\n   owner._import_recheck()\n'
        '  return super().split(*args)\n'
        'name = NestedName("fixture_nested_guard")\n'
        'before = list(owner._guard_checks[False])\nnested_before = owner._guard_nested\n'
        'owner._dependencies.loading.add(str(name))\nsys.modules[name] = types.ModuleType(str(name))\n'
        'try:\n owner._import_recheck()\n'
        ' assert owner._guard_nested == nested_before+1, "NESTED_GUARD_NOT_COUNTED"\n'
        ' assert owner._guard_checks[False] == [before[0]+1,before[1]+1], "NESTED_GUARD_DOUBLE_COUNTED"\n'
        ' assert owner._guard_depth == 0 and owner._guard_current is None\n'
        'finally:\n sys.modules.pop(name, None)\n owner._dependencies.loading.discard(str(name))\n'))
    assert result.returncode == 0, result.stderr
    assert any(row['nested_checks'] >= 1 for _, row in checkpoints(result.stderr))


def test_real_refusal_has_no_diagnostic_clock_or_write_after_poisoning():
    result = run_cpu(code=('import sys,types,time,os\nowner = sys.meta_path[0].owner\n'
        'original_clock = time.monotonic_ns\noriginal_write = os.write\n'
        'def clock():\n'
        ' if owner._state != "active": raise AssertionError("DIAGNOSTIC_AFTER_FAIL")\n'
        ' return original_clock()\n'
        'def write(fd, payload):\n'
        ' if owner._state != "active": raise AssertionError("DIAGNOSTIC_AFTER_FAIL")\n'
        ' return original_write(fd,payload)\n'
        'sys.modules["fixture_guard_refusal"] = types.ModuleType("fixture_guard_refusal")\n'
        'time.monotonic_ns = clock\nos.write = write\n'
        'try:\n owner._import_recheck()\n'
        'except RuntimeError as error:\n'
        ' assert str(error) == "Unregistered module cache entry: fixture_guard_refusal"\n'
        ' assert owner._first_failure is error and not owner._children\n'
        'else:\n raise AssertionError("CACHE_REFUSAL_SKIPPED")\n'
        'finally:\n time.monotonic_ns = original_clock\n os.write = original_write\n'
        ' sys.modules.pop("fixture_guard_refusal",None)\n'
        'os.write(2,b"GUARD_PRIMARY_FAILURE_RETAINED\\n")\n'))
    assert result.returncode != 0 and result.stdout == ''
    assert 'GUARD_PRIMARY_FAILURE_RETAINED' in result.stderr, result.stderr
    assert 'DIAGNOSTIC_AFTER_FAIL' not in result.stderr


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
