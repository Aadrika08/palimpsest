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


# ------------------------------------------------------------------- P-time port locator (no S0 record yet)

import hashlib  # noqa: E402
import re  # noqa: E402

PINS = ROOT/'docs/plans/m7-navigation-v4-pins'
PORTS = json.loads((PINS/'ports.json').read_text())
MANIFEST = ROOT/'docs/reports/male-v4-stage-p/MANIFEST.md'


def blob(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:{path}'], cwd=ROOT, capture_output=True, check=True, text=True).stdout


def test_p_locator_names_every_port_document_by_absolute_path_with_current_bytes_and_pending_values():
    value = probe.p_time_locator()
    assert value['schema'] == PORTS['locator']['schema'] and value['stage'] == 'P'
    assert value['protocol_sha256'] == PORTS['protocol_sha256'] == probe.PROTOCOL_SHA256
    assert set(value['documents']) == {d for t in PORTS['trees'].values() for d in t['documents']}
    for name, entry in value['documents'].items():
        assert Path(entry['path']).is_absolute() and entry['path'] == str((PINS/name).resolve())
        assert entry['sha256'] == hashlib.sha256((PINS/name).read_bytes()).hexdigest()
    # S0c has not run: the only non-document locator value (T-d data_manifest) is an explicit placeholder.
    assert {k for t in PORTS['trees'].values() for k in t.get('locator_values', [])} == {'data_manifest'}
    assert value['data_manifest'] == {'path': 'PENDING-S0c', 'sha256': 'PENDING-S0c'}
    assert value['pending']['male-recovery-research-development-v1.json']        # the copies still hold placeholders


def test_every_locator_key_a_port_reads_is_present_in_the_p_locator():
    value, seen = probe.p_time_locator(), set()
    for tree in PORTS['trees'].values():
        for rel in tree['files']:
            for line in blob(tree['branch'], rel).splitlines():
                if 'PALIMPSEST_M7_V4_PINS' not in line and 'v4[' not in line: continue
                seen |= {('documents', n) for n in re.findall(r"\['([\w.-]+\.json)'\]", line)}
                seen |= {(k, None) for k in re.findall(r"read_bytes\(\)\)\['(\w+)'\]", line) if k != 'documents'}
    assert ('data_manifest', None) in seen and len(seen) >= 6
    for key, name in seen:
        assert (name in value['documents']) if key == 'documents' else (key in value), (key, name)


def test_the_only_import_time_document_open_accepts_the_pending_v4_contact_copy():
    """collect_male_navigation_v2.py:50 (T-e, T-f) runs plan() at import: digest + contact-profile identity only."""
    source = blob(PORTS['trees']['T-e']['branch'], 'scripts/collect_male_navigation_v2.py')
    assert "CONTACTS = plan()['contacts']" in source
    profile = re.search(r"PROFILE_SHA = '([0-9a-f]{64})'", source).group(1)
    copy = json.loads((PINS/'m7-navigation-contact-v2-protocol.json').read_bytes())
    identity = json.dumps(copy['contact_profile']['identity'], sort_keys=True, separators=(',', ':')).encode()
    assert copy['contact_profile']['sha256'] == profile == hashlib.sha256(identity).hexdigest()
    assert probe.p_time_locator()['pending']['m7-navigation-contact-v2-protocol.json']   # PENDING fields are not read there


def test_write_port_pins_is_fresh_absolute_exclusive_and_outside_every_root(tmp_path):
    roots = [tmp_path/'wt', tmp_path/'data']
    for root in roots: root.mkdir()
    for bad, reason in (('relative/port-pins.json', 'absolute'), (str(tmp_path/'wt/pins.json'), 'outside'),
                        (str(tmp_path/'data/x/pins.json'), 'outside'), (str(tmp_path/'missing/pins.json'), 'parent')):
        with pytest.raises(ValueError, match=reason): probe.write_port_pins(bad, roots)
    out = tmp_path/'p/port-pins.json'; out.parent.mkdir()
    written = probe.write_port_pins(str(out), roots)
    raw = out.read_bytes()
    assert written == {'path': str(out), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    assert json.loads(raw) == probe.p_time_locator()
    with pytest.raises(ValueError, match='fresh'): probe.write_port_pins(str(out), roots)


def test_cli_write_port_pins_writes_the_locator_and_never_probes(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(probe, 'probe_entry', lambda *a, **k: pytest.fail('no probe may run'))
    wt, data = tmp_path/'wt', tmp_path/'data'; wt.mkdir(); data.mkdir()
    out = tmp_path/'p-pins.json'
    argv = ['--python', sys.executable, '--stage', f'S0e-port={wt}', '--forbid', str(data), '--write-port-pins', str(out)]
    assert probe.main(argv) == 0 and json.loads(capsys.readouterr().out)['locator']['path'] == str(out)
    assert json.loads(out.read_text())['stage'] == 'P'
    assert probe.main([*argv[:-1], str(wt/'pins.json')]) == 2 and 'outside' in capsys.readouterr().out


def test_dry_synthetic_h1_entry_imports_against_the_p_locator_and_its_open_is_audited(tmp_path):
    """Command-shape validation only: one ad-hoc synthetic entry, never a real entry point."""
    out = tmp_path/'p-pins.json'
    probe.write_port_pins(str(out), [tmp_path/'wt'])
    root = tmp_path/'wt'
    write(root, 'scripts/entry.py', '''
        import hashlib, json, os
        from pathlib import Path
        LOCATOR = json.loads(Path(os.environ['PALIMPSEST_M7_V4_PINS']).read_bytes())
        PLAN = LOCATOR['documents']['m7-navigation-contact-v2-protocol.json']['path']
        DATA_SHA256 = LOCATOR['data_manifest']['sha256']
        if hashlib.sha256(Path(PLAN).read_bytes()).hexdigest() != LOCATOR['documents']['m7-navigation-contact-v2-protocol.json']['sha256']:
            raise ValueError('Frozen v2 navigation plan differs')
    ''')
    env = {probe.PORT_LOCATOR_ENV: str(out)}
    result = probe.probe_entry(sys.executable, root, 'entry', forbid=(tmp_path/'data',), extra_env=env)
    assert result['status'] == 'passed', result.get('reasons')
    blocked = probe.probe_entry(sys.executable, root, 'entry', forbid=(PINS,), extra_env=env)
    assert blocked['status'] == 'refused'


# ------------------------------------------------------------------- the stage P manifest

def manifest_command():
    text = MANIFEST.read_text()
    block = re.search(r'<!-- stage-p-command -->\n```sh\n(.*?)\n```', text, re.S).group(1)
    return text, block.replace('\\\n', ' ').split()


def test_stage_p_manifest_covers_every_entry_point_once_under_a_charged_navigation_p_unit():
    text, argv = manifest_command()
    unit = argv[:argv.index('--')]
    flag = lambda name, words=unit: words[words.index(name) + 1]
    assert unit[1].endswith('scripts/run_research_stage.py')
    assert (flag('--lane'), flag('--stage'), flag('--runtime-max-sec'), flag('--worst-case-cpu'), flag('--cpu-quota-k')) == \
        ('navigation', 'P', '120', '125', '1')
    command = argv[argv.index('--') + 1:]
    assert command[0] == '/home/utkarsh/Work/shraddha/palimpsest/.venv/bin/python' and flag('--python', command) == command[0]
    stages = [command[i + 1].partition('=') for i, w in enumerate(command) if w == '--stage']
    assert sorted(s for s, _, _ in stages) == sorted(probe.ENTRYPOINTS) and len(stages) == len(probe.ENTRYPOINTS)
    assert '--egl' in command and Path(flag('--port-pins', command)).is_absolute()
    roots = {w for _, _, w in stages}
    forbid = [command[i + 1] for i, w in enumerate(command) if w == '--forbid']
    outside = [flag('--receipt-dir'), flag('--ledger'), flag('--go-record'), flag('--port-pins', command)]
    for path in outside + forbid:
        assert Path(path).is_absolute()
    for path in outside:
        assert not any(Path(path) == Path(r) or Path(r) in Path(path).parents for r in roots | set(forbid)), path
    assert '/home/utkarsh/Work/shraddha/palimpsest/runs' in forbid and '/home/utkarsh/Work/shraddha/palimpsest/data/assets' in forbid
    assert all(f'{r}/runs' in forbid and f'{r}/data/assets' in forbid for r in roots)
    assert '--write-port-pins' in text and PORTS['trees']['T-e']['port_commit'] in text


def test_egl_stage_limits_the_single_context_to_one_declared_stage(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(probe, 'probe_stage', lambda python, stage, worktree, **kw: calls.append(
        (stage, kw['egl'])) or {'stage': stage, 'status': 'passed'})
    probe.main(['--python', sys.executable, '--egl', '--egl-stage', 'S2',
                '--stage', f'S1={tmp_path}', '--stage', f'S2={tmp_path}'])
    assert calls == [('S1', False), ('S2', True)]
