"""Stage P import-closure probe: synthetic worktrees and interpreters only; opens no data."""
import json
from pathlib import Path
import subprocess
import sys
import textwrap
import venv

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import probe_male_navigation_v4_imports as probe

V3_CHAIN = ['train_male_navigation_v3', 'train_male_navigation_v2', 'train_male_recovery',
            'prepare_male_recovery_data', 'collect_male_recovery', 'palimpsest.runtime_verification',
            'verify_endurance', 'httpx']


def write(root, name, text):
    path = Path(root)/name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def v3_chain_worktree(root):
    """Same module shape as the consumed v3 attempt-2 failure, without any real source."""
    write(root, 'scripts/train_male_navigation_v3.py', '''
        import train_male_navigation_v2
        def main():
            open('main-was-called', 'w').write('x')
    ''')
    write(root, 'scripts/train_male_navigation_v2.py', 'import train_male_recovery\n')
    write(root, 'scripts/train_male_recovery.py', 'import prepare_male_recovery_data\n')
    write(root, 'scripts/prepare_male_recovery_data.py', 'import collect_male_recovery\n')
    write(root, 'scripts/collect_male_recovery.py', 'from palimpsest import runtime_verification\n')
    write(root, 'src/palimpsest/__init__.py', '')
    write(root, 'src/palimpsest/runtime_verification.py', 'import verify_endurance\n')
    write(root, 'scripts/verify_endurance.py', 'import httpx\n')
    return Path(root)


@pytest.fixture(scope='module')
def stub_python(tmp_path_factory):
    """A stdlib-only interpreter: the locked base Python without the project packages."""
    target = tmp_path_factory.mktemp('stub-env')/'venv'
    venv.EnvBuilder(with_pip=False, symlinks=True, system_site_packages=False).create(target)
    python = target/'bin/python'
    check = subprocess.run([str(python), '-I', '-c', 'import httpx'], capture_output=True)
    assert check.returncode != 0
    return python


def test_stub_environment_reproduces_and_refuses_v3_httpx_chain(tmp_path, stub_python):
    root = v3_chain_worktree(tmp_path/'wt')
    result = probe.probe_entry(stub_python, root, 'train_male_navigation_v3')
    assert result['status'] == 'refused'
    assert result['unresolved'][0]['name'] == 'httpx'
    assert result['unresolved'][0]['chain'] == V3_CHAIN
    assert not (root/'main-was-called').exists()


def test_locked_environment_passes_same_chain(tmp_path):
    root = v3_chain_worktree(tmp_path/'wt')
    result = probe.probe_entry(sys.executable, root, 'train_male_navigation_v3')
    assert result['status'] == 'passed', result['reasons']
    assert result['unresolved'] == []
    assert result['versions']['httpx'] == '0.28.1'
    for name in V3_CHAIN[:-1]:
        assert Path(result['modules'][name]).is_relative_to(root)
    assert result['runtime']['python'].startswith('3.11.')
    assert result['runtime']['isolated'] is True
    assert not (root/'main-was-called').exists()


def test_real_v3_trainer_chain_resolves_in_locked_environment():
    result = probe.probe_entry(sys.executable, ROOT, 'train_male_navigation_v3',
                               thread_env={'OMP_NUM_THREADS': '1'})
    assert result['status'] == 'passed', result['reasons']
    assert 'verify_endurance' in result['modules'] and 'httpx' in result['modules']
    assert result['versions']['httpx'] == '0.28.1'
    assert result['runtime']['torch_cuda_initialized'] in (False, None)
    assert result['denied_opens'] == []


def test_function_level_import_is_part_of_closure(tmp_path):
    root = tmp_path/'wt'
    write(root, 'scripts/entry.py', '''
        try:
            import optional_never_installed_xyz
        except ImportError:
            optional_never_installed_xyz = None
        def later():
            import helper_lazy
    ''')
    write(root, 'scripts/helper_lazy.py', 'import missing_lazy_dependency_xyz\n')
    result = probe.probe_entry(sys.executable, root, 'entry')
    assert result['status'] == 'refused'
    names = [row['name'] for row in result['unresolved']]
    assert names == ['missing_lazy_dependency_xyz']
    assert result['unresolved'][0]['chain'] == ['entry', 'helper_lazy', 'missing_lazy_dependency_xyz']
    assert [row['name'] for row in result['optional_unresolved']] == ['optional_never_installed_xyz']


def test_import_time_data_open_is_blocked_and_refused(tmp_path):
    root = tmp_path/'wt'
    (root/'runs').mkdir(parents=True)
    (root/'runs/corpus.json').write_text('{}')
    write(root, 'scripts/entry.py', '''
        from pathlib import Path
        Path(__file__).resolve().parents[1].joinpath('runs/corpus.json').read_text()
    ''')
    result = probe.probe_entry(sys.executable, root, 'entry')
    assert result['status'] == 'refused'
    assert [Path(p).name for p in result['denied_opens']] == ['corpus.json']


def test_explicit_forbidden_root_is_never_opened(tmp_path):
    root, data = tmp_path/'wt', tmp_path/'held-out'
    data.mkdir(); (data/'scene.json').write_text('{}')
    write(root, 'scripts/entry.py', f'open({str(data/"scene.json")!r}).read()\n')
    result = probe.probe_entry(sys.executable, root, 'entry', forbid=(data,))
    assert result['status'] == 'refused' and len(result['denied_opens']) == 1


def test_local_package_resolving_outside_worktree_is_refused(tmp_path):
    root = tmp_path/'wt'
    write(root, 'scripts/entry.py', 'import palimpsest\n')
    write(root, 'src/palimpsest_marker/__init__.py', '')
    # The locked venv carries an editable palimpsest pointing at the main checkout.
    result = probe.probe_entry(sys.executable, root, 'entry', local_names=('palimpsest',))
    assert result['status'] == 'refused'
    assert any('outside the worktree' in reason for reason in result['reasons'])


def test_interpreter_path_assertions_are_recorded(tmp_path):
    root = tmp_path/'wt'
    write(root, 'scripts/entry.py', '''
        import sys
        def guard():
            if sys.executable != '/x/lab-hardening/.venv/bin/python':
                raise SystemExit('wrong interpreter')
    ''')
    result = probe.probe_entry(sys.executable, root, 'entry')
    assert result['status'] == 'passed', result['reasons']
    assert len(result['interpreter_path_assertions']) == 1
    assert result['interpreter_path_assertions'][0]['file'] == 'scripts/entry.py'


def test_thread_environment_is_recorded(tmp_path):
    root = tmp_path/'wt'
    write(root, 'scripts/entry.py', 'X = 1\n')
    result = probe.probe_entry(sys.executable, root, 'entry', thread_env={'OMP_NUM_THREADS': '2'})
    assert result['runtime']['environment']['OMP_NUM_THREADS'] == '2'


def test_declared_entrypoints_cover_s0_producers_at_commits_and_v4_stages():
    table = probe.ENTRYPOINTS
    assert {k: v['commit'][:7] for k, v in table.items() if v['commit']} == {
        'S0a': 'cc1cea9', 'S0b': 'c382c86', 'S0c': '7d5fc1f', 'S0d': '19d275d',
        'S0e': '736e0cf', 'S0f': '4ecb354', 'S0f-historical': '217cbee'}
    assert table['S1']['module'] == 'train_male_navigation_v4' and table['S1']['commit'] is None
    assert table['S2']['module'] == 'evaluate_male_navigation_v4'
    assert table['S0b']['thread_env'] == {'OMP_NUM_THREADS': '2'}
    assert table['S0e']['thread_env'] == {'OMP_NUM_THREADS': '1'}


def test_stage_worktree_at_wrong_commit_is_refused_without_child(tmp_path, monkeypatch):
    root = v3_chain_worktree(tmp_path/'wt')
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    calls = []
    monkeypatch.setattr(probe, 'probe_entry', lambda *a, **k: calls.append(a) or {})
    result = probe.probe_stage(sys.executable, 'S0c', root)
    assert result['status'] == 'refused' and calls == []


def test_planned_entrypoint_absent_is_refused(tmp_path):
    root = tmp_path/'wt'; (root/'scripts').mkdir(parents=True)
    result = probe.probe_stage(sys.executable, 'S1', root)
    assert result['status'] == 'refused'
    assert 'not present' in result['reasons'][0]


def test_cli_requires_absolute_existing_interpreter_and_exits_nonzero_on_refusal(tmp_path, capsys, stub_python):
    root = v3_chain_worktree(tmp_path/'wt')
    assert probe.main(['--python', 'python3', '--root', str(root), '--module', 'train_male_navigation_v3']) == 2
    assert probe.main(['--python', str(stub_python), '--root', str(root), '--module', 'train_male_navigation_v3']) == 1
    report = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert report['status'] == 'refused'
    assert probe.main(['--python', sys.executable, '--root', str(root), '--module', 'train_male_navigation_v3']) == 0
