"""CPU compatibility using only authored stdlib subprocesses."""
import json
import math
import resource
import subprocess
import sys

import pytest

from scripts import qualify_memory_family_source_v2 as parent


@pytest.mark.parametrize('remaining,hard,want', [
    (1800, 10, 9), (8.25, 10, 8.25), (.25, 2, .25),
    (1800, 2, 1), (1800, resource.RLIM_INFINITY, 1800),
    (.25, resource.RLIM_INFINITY, .25),
])
def test_worker_budget_fits_inherited_hard_limit(remaining, hard, want):
    budget = parent._worker_cpu_budget(remaining, hard)
    assert budget == want
    if hard != resource.RLIM_INFINITY:
        assert max(1, math.ceil(budget)) + 1 <= hard


@pytest.mark.parametrize('remaining', [None, True, '1', 0, -1, 1800.01,
    float('nan'), float('inf'), -float('inf')])
def test_invalid_remaining_cpu_refuses(remaining):
    with pytest.raises(ValueError):
        parent._worker_cpu_budget(remaining, 10)


@pytest.mark.parametrize('hard', [None, True, False, '10', 10.0, 0, 1, -2,
    float('nan'), float('inf'), -float('inf')])
def test_unknown_invalid_or_inadequate_hard_limit_refuses(hard):
    with pytest.raises(ValueError):
        parent._worker_cpu_budget(1800, hard)


def _authored_finite_limit_run(tmp_path, *, clamp):
    # Only this fresh child lowers its limit; pytest's limits are untouched.
    script = '''
import json, os, resource, sys
from pathlib import Path
from paper.studies.change_audit_v1.process import run_accounted
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
budget = 1800
if sys.argv[2] == 'clamp':
    from scripts.qualify_memory_family_source_v2 import _worker_cpu_budget
    budget = _worker_cpu_budget(budget, resource.getrlimit(resource.RLIMIT_CPU)[1])
root = Path(sys.argv[1])
result = run_accounted([sys.executable, '-B', '-c', 'print("authored-exec-completed")'],
    cwd=os.getcwd(), env=dict(os.environ), stdout_path=root/'stdout',
    stderr_path=root/'stderr', wall_seconds=5, cpu_seconds=budget, max_log_bytes=4096)
print(json.dumps({'budget': budget, 'result': result}))
'''
    child = subprocess.run([sys.executable, '-B', '-c', script, str(tmp_path),
        'clamp' if clamp else 'unbounded'], capture_output=True, text=True, timeout=15)
    assert child.returncode == 0, child.stderr
    return json.loads(child.stdout), (tmp_path / 'stdout').read_text(), (tmp_path / 'stderr').read_text()


def test_unbounded_request_fails_before_authored_exec(tmp_path):
    before = resource.getrlimit(resource.RLIMIT_CPU)
    value, stdout, stderr = _authored_finite_limit_run(tmp_path, clamp=False)
    result = value['result']
    assert result['status'] == 'failed' and result['returncode'] == 127
    assert result['tree_drained'] is True and result['accounting_complete'] is True
    assert stdout == ''
    assert 'exec/setup error: not allowed to raise maximum limit' in stderr
    assert resource.getrlimit(resource.RLIMIT_CPU) == before


def test_clamped_request_completes_authored_exec(tmp_path):
    before = resource.getrlimit(resource.RLIMIT_CPU)
    value, stdout, stderr = _authored_finite_limit_run(tmp_path, clamp=True)
    result = value['result']
    assert value['budget'] == 9
    assert result['status'] == 'completed' and result['returncode'] == 0
    assert result['tree_drained'] is True and result['accounting_complete'] is True
    assert stdout == 'authored-exec-completed\n' and stderr == ''
    assert resource.getrlimit(resource.RLIMIT_CPU) == before
