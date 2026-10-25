"""Exercise the real shell runner without starting pytest, models or namespaces."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
FLAGS = (
    'PALIMPSEST_SIMULATION_TESTS', 'PALIMPSEST_MALE_TORCH_CHECKS',
    'PALIMPSEST_MALE_RUNTIME_TESTS', 'PALIMPSEST_TEST_PUCK_TORCH',
    'PALIMPSEST_BUILD_NAMESPACE_TEST', 'PALIMPSEST_INSTALL_FIXTURE',
)
PATHS = ('PALIMPSEST_MALE_RUNTIME_OUTPUT', 'PALIMPSEST_TEST_ASSETS')


@pytest.mark.parametrize('arguments,calls', [([], 4), (['--', 'tests/test_probe.py'], 1),
                                           (['--integration'], 1)])
@pytest.mark.parametrize('value', [None, '', '0', '1'])
def test_runner_preserves_explicit_opt_ins_and_isolates_ambient_environment(tmp_path, arguments, calls, value):
    project = tmp_path / 'project with spaces'
    (project / 'scripts').mkdir(parents=True)
    (project / 'tests').mkdir()
    for name in ('test_probe.py', 'test_probe_integration.py'):
        (project / 'tests' / name).touch()
    runner = project / 'scripts/run_tests.sh'
    shutil.copyfile(ROOT / 'scripts/run_tests.sh', runner)
    spy = tmp_path / 'python-spy'
    spy.write_text(f'#!{sys.executable} -B\n'
                   'import json, os, sys\n'
                   'print(json.dumps({"env": dict(os.environ), "argv": sys.argv[1:]}))\n')
    spy.chmod(0o700)
    environment = {key: item for key, item in os.environ.items() if key not in (*FLAGS, *PATHS)}
    expected = {} if value is None else dict.fromkeys(FLAGS, value)
    if value is not None:
        expected.update({key: str(tmp_path / (key + ' with spaces')) for key in PATHS})
    environment.update(expected)
    environment.update(
        PALIMPSEST_PYTHON=str(spy), PALIMPSEST_TEST_BASETEMP=str(tmp_path / 'outside'),
        PALIMPSEST_TMPFS_BASETEMP=str(tmp_path / 'tmpfs'),
        PYTHONPATH='ambient-path', PYTEST_ADDOPTS='--invalid-ambient-option', LD_PRELOAD='',
        OMP_NUM_THREADS='8', OPENBLAS_NUM_THREADS='8', MKL_NUM_THREADS='8', NUMEXPR_NUM_THREADS='8',
        MUJOCO_GL='ambient-renderer', CUDA_VISIBLE_DEVICES='0', PALIMPSEST_UNRECOGNIZED='ambient')
    result = subprocess.run(['/bin/bash', str(runner), *arguments], cwd=project,
                            env=environment, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stderr
    invocations = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(invocations) == calls
    for invocation in invocations:
        child = invocation['env']
        assert {key: child[key] for key in (*FLAGS, *PATHS) if key in child} == expected
        assert child['PYTHONPATH'] == ':'.join(str(project / name) for name in ('src', 'scripts', 'tests'))
        assert all(key not in child for key in ('PYTEST_ADDOPTS', 'LD_PRELOAD', 'PALIMPSEST_UNRECOGNIZED'))
        assert all(child[key] == '1' for key in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                                               'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'))
        assert child['MUJOCO_GL'] == 'egl' and child['CUDA_VISIBLE_DEVICES'] == ''
        assert invocation['argv'][:3] == ['-B', '-m', 'pytest']
