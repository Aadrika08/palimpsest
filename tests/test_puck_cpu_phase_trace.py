"""Diagnostic CPU checkpoints with authored packages, never installed models."""
import json
import math

import pytest

from test_puck_cpu_runtime_entry import cpu_policy, cpu_setup
from test_puck_held_runtime_entry import qualify, setup
from test_puck_tmpfs_dependencies import authored
from test_puck_worker_bootstrap import descriptor
from test_puck_worker_dependencies import dependency_fixture


PHASES = [
    'bootstrap.enter', 'source.ready', 'dependencies.enter', 'dependencies.ready',
    'bootstrap.ready', 'entry.enter',
    'import.numpy.enter', 'import.numpy.returned',
    'import.torch.enter', 'import.torch.returned',
    'import.torchvision.enter', 'import.torchvision.returned',
    'import.mujoco.enter', 'import.mujoco.returned',
    'entry.returned', 'entry.ready', 'close.enter', 'close.ready',
]


def traces(stderr):
    rows = []
    for line in stderr.splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue  # An import failure may also retain its ordinary traceback.
        if isinstance(row, dict) and row.get('kind') == 'puck-worker-phase-v1':
            rows.append((line, row))
    return rows


def run_cpu(*, defect=None, dependency_version=3, code='', package='torchvision'):
    def packages(deps, root):
        cpu_setup(deps, root, defect, dependency_version=dependency_version)
        if code:
            path = root/package/'__init__.py'
            path.write_text(path.read_text()+code)
            deps['roots'][0]['files'] = [descriptor(root/row['path'], row['path'])
                for row in deps['roots'][0]['files']]
    with authored() as base:
        result, _ = dependency_fixture(base, 'raise AssertionError("DEFAULT_ENTRY_RAN")',
            mutate=packages, source_change=cpu_policy)
        return result


def test_cpu_trace_locates_each_return_without_changing_terminal_receipt():
    result = run_cpu()
    assert result.returncode == 0, result.stderr
    rows = traces(result.stderr)
    assert [row['phase'] for _, row in rows] == PHASES
    assert [row['sequence'] for _, row in rows] == list(range(1, 19))
    elapsed = [row['elapsed_seconds'] for _, row in rows]
    assert all(type(value) is float and math.isfinite(value) and value >= 0 for value in elapsed)
    assert elapsed == sorted(elapsed)
    assert all(row['diagnostic_only'] is True for _, row in rows)
    assert len(rows) <= 24 and sum(len(line.encode())+1 for line, _ in rows) <= 16384
    assert len(result.stdout.splitlines()) == 1
    receipt = json.loads(result.stdout)
    assert receipt['entry_result']['status'] == 'imports_completed'
    assert receipt['runtime_qualified'] is receipt['native_authorized'] is False
    assert receipt['qualification_claims'] == []


@pytest.mark.parametrize('version', [1, 2])
def test_legacy_qualification_has_no_new_diagnostic_output(version):
    def policy(reg, source):
        qualify(reg, source)
        if version == 2:
            reg['qualification'].update(kind='puck-held-runtime-import-qualification-v2', version=2)
    with authored() as base:
        result, _ = dependency_fixture(base, 'return {}', mutate=setup, source_change=policy)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ''
    assert json.loads(result.stdout)['entry_result']['version'] == 1


@pytest.mark.parametrize('defect,last,reason', [
    ('fail', 'import.torchvision.enter', 'AUTHORED_TORCHVISION_FAILURE'),
    ('wrong-version', 'import.torchvision.returned', 'Runtime qualification version differs'),
])
def test_import_return_marker_is_distinct_from_import_or_version_failure(defect, last, reason):
    result = run_cpu(defect=defect)
    assert result.returncode != 0 and result.stdout == ''
    phases = [row['phase'] for _, row in traces(result.stderr)]
    assert phases == PHASES[:PHASES.index(last)+1]
    assert reason in result.stderr and 'close.ready' not in phases


def test_dependency_admission_failure_does_not_announce_a_ready_worker():
    result = run_cpu(dependency_version=2)
    assert result.returncode != 0 and result.stdout == ''
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:3]
    assert 'Four-import qualification requires admitted v3' in result.stderr


def test_import_deadline_preserves_trace_prefix_and_no_completion():
    result = run_cpu(code='import sys\nsys.meta_path[0].owner._deadline = 0\n')
    assert result.returncode != 0 and result.stdout == ''
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:11]
    assert 'Fresh worker deadline exhausted' in result.stderr


def test_snapshot_failure_after_entry_return_cannot_publish_stdout():
    result = run_cpu(package='mujoco', code=(
        'import sys\ndef fail_snapshot():\n raise TimeoutError("AUTHORED_SNAPSHOT_FAILURE")\n'
        'sys.meta_path[0].owner.snapshot = fail_snapshot\n'))
    assert result.returncode != 0 and result.stdout == ''
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:15]
    assert 'AUTHORED_SNAPSHOT_FAILURE' in result.stderr


def test_close_failure_has_no_close_ready_or_terminal_receipt():
    result = run_cpu(package='mujoco', code=(
        'import sys\ndef install_close_failure():\n'
        ' owner = sys.meta_path[0].owner\n original = owner._close\n'
        ' def close(error=None):\n  result = original(error)\n'
        '  return result if error is not None else RuntimeError("AUTHORED_CLOSE_FAILURE")\n'
        ' owner._close = close\ninstall_close_failure()\n'))
    assert result.returncode != 0 and result.stdout == ''
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:17]
    assert 'AUTHORED_CLOSE_FAILURE' in result.stderr


def test_trace_record_budget_latches_off_without_changing_success():
    result = run_cpu(code=(
        'import sys\nfor index in range(30):\n'
        ' sys.meta_path[0].owner._phase("authored.extra")\n'))
    assert result.returncode == 0, result.stderr
    rows = traces(result.stderr)
    assert len(rows) == 24
    assert [row['sequence'] for _, row in rows] == list(range(1, 25))
    assert sum(len(line.encode())+1 for line, _ in rows) <= 16384
    assert rows[-1][1]['phase'] == 'authored.extra'
    assert json.loads(result.stdout)['entry_result']['status'] == 'imports_completed'


def test_trace_encoded_byte_budget_is_separate_from_record_count():
    result = run_cpu(code=(
        'import sys\nfor index in range(30):\n'
        ' sys.meta_path[0].owner._phase("\\U0001f33f"*512)\n'))
    assert result.returncode == 0, result.stderr
    rows = traces(result.stderr)
    assert 11 < len(rows) < 24
    assert sum(len(line.encode())+1 for line, _ in rows) <= 16384
    assert rows[-1][1]['phase'] == '\U0001f33f'*512
    assert json.loads(result.stdout)['entry_result']['status'] == 'imports_completed'


@pytest.mark.parametrize('writer', ['short', 'error'])
@pytest.mark.parametrize('fail_import', [False, True])
def test_trace_io_failure_is_not_retried_and_preserves_the_real_outcome(writer, fail_import):
    code = ('import os,sys\noriginal_write = os.write\nwrite_calls = 0\n'
        'def broken_write(fd, payload):\n global write_calls\n write_calls += 1\n'
        ' if write_calls > 1: raise AssertionError("TRACE_WRITE_RETRIED")\n'
        + (' return len(payload)-1\n' if writer == 'short' else ' raise OSError("AUTHORED_TRACE_IO_FAILURE")\n')
        + 'os.write = broken_write\nsys.meta_path[0].owner._phase("authored.io")\n'
        'sys.meta_path[0].owner._phase("authored.no_retry")\nos.write = original_write\n'
        'assert write_calls == 1, "TRACE_WRITE_RETRIED"\n')
    if fail_import:
        code += 'raise RuntimeError("AUTHORED_PRIMARY_FAILURE")\n'
    result = run_cpu(code=code)
    assert 'TRACE_WRITE_RETRIED' not in result.stderr
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:11]
    if fail_import:
        assert result.returncode != 0 and result.stdout == ''
        assert 'AUTHORED_PRIMARY_FAILURE' in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)['entry_result']['status'] == 'imports_completed'


def test_trace_cancellation_is_not_swallowed_and_closes_owned_holders():
    result = run_cpu(package='mujoco', code=(
        'import os,sys\ndef install_cancel():\n'
        ' owner = sys.meta_path[0].owner\n original_close = owner._close\n original_write = os.write\n'
        ' def close(error=None):\n  result = original_close(error)\n  os.write = original_write\n'
        '  assert not owner._children and not owner._early_runtime_fds\n'
        '  original_write(2, b"AUTHORED_CANCEL_CLOSED\\n")\n  return result\n'
        ' def cancel(fd, payload):\n  raise KeyboardInterrupt("AUTHORED_TRACE_CANCEL")\n'
        ' owner._close = close\n os.write = cancel\n owner._phase("authored.cancel")\n'
        'install_cancel()\n'))
    assert result.returncode != 0 and result.stdout == ''
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:13]
    assert 'AUTHORED_TRACE_CANCEL' in result.stderr and 'AUTHORED_CANCEL_CLOSED' in result.stderr


def test_dependency_setup_deadline_remains_terminal_before_imports():
    def policy(reg, source):
        cpu_policy(reg, source)
        relative = 'src/palimpsest/puck_dependency_imports.py'
        path = source/relative
        path.write_text(path.read_text()+'\nimport sys\nsys.meta_path[0].owner._deadline = 0\n')
        reg['source_files'] = [descriptor(source/row['path'], row['path'])
            for row in reg['source_files']]
    with authored() as base:
        result, _ = dependency_fixture(base, 'return {}', mutate=cpu_setup, source_change=policy)
    assert result.returncode != 0 and result.stdout == ''
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:3]
    assert 'Fresh worker deadline exhausted' in result.stderr


def test_snapshot_deadline_guard_remains_before_entry_ready():
    result = run_cpu(package='mujoco', code=(
        'import sys\ndef install_snapshot_deadline():\n'
        ' owner = sys.meta_path[0].owner\n original = owner.snapshot\n'
        ' def snapshot():\n  owner._deadline = 0\n  return original()\n'
        ' owner.snapshot = snapshot\ninstall_snapshot_deadline()\n'))
    assert result.returncode != 0 and result.stdout == ''
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:15]
    assert 'Fresh worker deadline exhausted' in result.stderr


def test_close_deadline_guard_runs_after_owned_holders_close():
    result = run_cpu(package='mujoco', code=(
        'import sys\ndef install_close_deadline():\n'
        ' owner = sys.meta_path[0].owner\n original = owner._close\n'
        ' def close(error=None):\n  result = original(error)\n'
        '  assert not owner._children and not owner._early_runtime_fds\n'
        '  if error is None: owner._deadline = 0\n  return result\n'
        ' owner._close = close\ninstall_close_deadline()\n'))
    assert result.returncode != 0 and result.stdout == ''
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:17]
    assert 'Fresh worker deadline exhausted' in result.stderr


def test_close_ready_marker_cannot_override_the_final_deadline():
    result = run_cpu(package='mujoco', code=(
        'import os,sys\ndef install_late_marker():\n'
        ' owner = sys.meta_path[0].owner\n original = os.write\n'
        ' def write(fd, payload):\n  result = original(fd, payload)\n'
        '  if b\'"phase":"close.ready"\' in payload: owner._deadline = 0\n'
        '  return result\n os.write = write\ninstall_late_marker()\n'))
    assert result.returncode != 0 and result.stdout == ''
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES
    assert 'Fresh worker deadline exhausted' in result.stderr


def test_successful_outer_write_cannot_rearm_a_nested_trace_failure():
    result = run_cpu(code=(
        'import os,sys\noriginal_write = os.write\nwrite_calls = 0\n'
        'def nested_write(fd, payload):\n global write_calls\n write_calls += 1\n'
        ' if write_calls == 1:\n  sys.meta_path[0].owner._phase("authored.nested")\n'
        '  return len(payload)\n if write_calls == 2: raise OSError("AUTHORED_NESTED_IO_FAILURE")\n'
        ' return original_write(fd, payload)\n'
        'os.write = nested_write\nsys.meta_path[0].owner._phase("authored.outer")\n'
        'sys.meta_path[0].owner._phase("authored.no_retry")\nos.write = original_write\n'
        'assert write_calls == 2, "TRACE_LATCH_REARMED"\n'))
    assert result.returncode == 0, result.stderr
    assert [row['phase'] for _, row in traces(result.stderr)] == PHASES[:11]
    assert json.loads(result.stdout)['entry_result']['status'] == 'imports_completed'
