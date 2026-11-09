"""Synthetic trees only: the S1 comparison-set builder lists directories, never reads payloads."""
import json
from pathlib import Path

import pytest

import build_puck_v4_s1_comparison_set as builder


def _touch(path, text=''):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _machine(tmp_path):
    shraddha = tmp_path / 'shraddha'
    main = shraddha / 'palimpsest'
    for relative in ('.git/HEAD', '.venv/pyvenv.cfg', 'docs/a.md', 'ui/node_modules/x.json',
                     '.worktrees/authority-study-final/runs/r.json',
                     '.worktrees/authority-study-final/.venv/pyvenv.cfg', '.worktrees/paper/docs/b.md',
                     'worktrees/memory/docs/c.md', '.claude/worktrees/agent-1/docs/d.md',
                     '.claude/settings.json'):
        _touch(main / relative)
    _touch(main / 'upstream/fly-gym/.git', 'gitdir: ../../.git/modules/upstream/fly-gym\n')
    evidence = shraddha / 'palimpsest-authored-test-evidence'
    _touch(evidence / 'log.txt')
    (evidence / 'puck-v4-s1-out').mkdir()
    (evidence / 'puck-v4-s1-attempt-ledger').mkdir()
    for name in ('.palimpsest-a', '.palimpsest-b', 'aadrikas-archiv', 'decision-aware-tsfm',
                 'decision-aware-tsfm-aadrika3', 'posthumus', 'checks'):
        (shraddha / name).mkdir()
    codex = tmp_path / 'codex'
    for name in ('0071', '293b'):
        _touch(codex / name / 'brain' / '.git', 'gitdir: /lost/brain/.git/worktrees/x\n')
    (codex / '1fcb').mkdir()
    return dict(shraddha=str(shraddha), main=str(main), codex_worktrees=str(codex),
                advertisement=str(tmp_path / 'advert.txt'),
                submodule_advertisement=str(tmp_path / 'sub-advert.txt'))


def test_builder_declares_expected_roots(tmp_path):
    paths = _machine(tmp_path)
    declaration = builder.build(**paths)
    roots = {row['name']: row for row in declaration['roots']}
    main = paths['main']
    assert roots['palimpsest-git'] == {
        'name': 'palimpsest-git', 'kind': 'git', 'path': main,
        'advertisement': paths['advertisement'], 'held_out_payloads': True}
    assert roots['palimpsest-git-upstream-fly-gym']['advertisement'] == \
        paths['submodule_advertisement']
    tree = roots['palimpsest-main']
    excluded = {row['path']: row['reason'] for row in tree['exclude']}
    for relative in ('.venv', 'ui/node_modules', '.worktrees', 'worktrees', '.claude/worktrees'):
        assert main + '/' + relative in excluded and excluded[main + '/' + relative].strip()
    asf = roots['worktree-.worktrees-authority-study-final']
    assert asf['path'] == main + '/.worktrees/authority-study-final'
    assert {row['path'] for row in asf['exclude']} == {asf['path'] + '/.venv',
                                                       asf['path'] + '/runs'}
    assert roots['worktree-.worktrees-authority-study-final-runs']['held_out_payloads'] is True
    assert 'worktree-worktrees-memory' in roots and 'worktree-.claude-worktrees-agent-1' in roots
    for name in ('0071', '293b'):
        assert roots[f'codex-{name}-brain']['lost_root_clone'] is True
    assert 'codex-1fcb-brain' not in roots
    evidence = roots['palimpsest-authored-test-evidence']
    assert evidence['held_out_payloads'] is True
    assert {row['path'].rsplit('/', 1)[1] for row in evidence['exclude']} == {
        'puck-v4-s1-out', 'puck-v4-s1-attempt-ledger', 'puck-v4-s1-attempt-2-ledger'}
    assert {'fixture-.palimpsest-a', 'fixture-.palimpsest-b'} <= set(roots)
    assert sorted(Path(row['path']).name for row in declaration['unscanned']) == sorted(
        builder.UNRELATED_PROJECTS)


def test_builder_output_passes_admission_schema_and_overlap_rules(tmp_path):
    from palimpsest import puck_v4_scene_admission as s1
    path = tmp_path / 'decl.json'
    path.write_bytes(builder.render(builder.build(**_machine(tmp_path))))
    _, declaration = s1._load_declaration(path)
    assert len(declaration['roots']) == len(builder.build(**_machine_paths(tmp_path))['roots'])


def _machine_paths(tmp_path):
    shraddha = tmp_path / 'shraddha'
    return dict(shraddha=str(shraddha), main=str(shraddha / 'palimpsest'),
                codex_worktrees=str(tmp_path / 'codex'),
                advertisement=str(tmp_path / 'advert.txt'),
                submodule_advertisement=str(tmp_path / 'sub-advert.txt'))


def test_builder_is_deterministic(tmp_path):
    paths = _machine(tmp_path)
    assert builder.render(builder.build(**paths)) == builder.render(builder.build(**paths))


def test_builder_refuses_unknown_sibling(tmp_path):
    paths = _machine(tmp_path)
    (Path(paths['shraddha']) / 'surprise').mkdir()
    with pytest.raises(ValueError, match='surprise'):
        builder.build(**paths)


def test_builder_cli_writes_fresh_file_only(tmp_path):
    paths = _machine(tmp_path)
    output = tmp_path / 'decl.json'
    argv = ['--shraddha', paths['shraddha'], '--main', paths['main'],
            '--codex-worktrees', paths['codex_worktrees'],
            '--advertisement', paths['advertisement'],
            '--submodule-advertisement', paths['submodule_advertisement'],
            '--output', str(output)]
    assert builder.main(argv) == 0
    assert json.loads(output.read_bytes())['kind'] == 'puck-v4-s1-comparison-set-v1'
    with pytest.raises(SystemExit):
        builder.main(argv)


def test_hazard_pass_excludes_only_dangling_temp_and_lost_root_git(tmp_path):
    paths = _machine(tmp_path)
    main = Path(paths['main'])
    (main / 'runs').mkdir()
    (main / 'runs/dangling').symlink_to('/outside/missing')
    ephemeral = tmp_path / 'eph'
    (ephemeral / 'pytest-of-u' / 'pytest-1').mkdir(parents=True)
    (main / 'runs/temp').symlink_to(ephemeral / 'pytest-of-u' / 'pytest-1')
    declaration = builder.build(**paths, ephemeral=(str(ephemeral),))
    roots = {row['name']: row for row in declaration['roots']}
    excluded = {row['path']: row['reason'] for row in roots['palimpsest-main']['exclude']}
    assert 'dangling' in excluded[str(main / 'runs/dangling')]
    assert 'ephemeral' in excluded[str(main / 'runs/temp')]
    assert {row['path']: row['reason'] for row in declaration['unscanned']}[
        str(ephemeral / 'pytest-of-u')].startswith('pytest temporary base directory')
    codex = roots['codex-0071-brain']
    assert any(row['path'].endswith('/brain/.git') and 'lost-root' in row['reason']
               for row in codex['exclude'])


def test_hazard_pass_refuses_symlink_leaving_declared_roots(tmp_path):
    paths = _machine(tmp_path)
    outside = tmp_path / 'elsewhere'
    outside.mkdir()
    main = Path(paths['main'])
    (main / 'docs/escape').symlink_to(outside)
    with pytest.raises(ValueError, match='leaves declared roots'):
        builder.build(**paths, ephemeral=('/nonexistent-ephemeral-prefix',))


def test_hazard_pass_refuses_uncovered_git_metadata(tmp_path):
    paths = _machine(tmp_path)
    _touch(Path(paths['main']) / '.worktrees/paper/vendor/.git', 'gitdir: /x\n')
    with pytest.raises(ValueError, match='uncovered git metadata'):
        builder.build(**paths)


def test_hazard_pass_excludes_shared_clone_git_only_with_declared_alternates(tmp_path):
    paths = _machine(tmp_path)
    main = Path(paths['main'])
    (main / '.git/objects').mkdir(parents=True)
    clone = main / 'runs/repro/checkout/.git'
    _touch(clone / 'objects/info/alternates', str(main / '.git/objects') + '\n')
    declaration = builder.build(**paths)
    excluded = {row['path']: row['reason'] for row in
                {r['name']: r for r in declaration['roots']}['palimpsest-main']['exclude']}
    assert 'shared clone' in excluded[str(clone)]
    _touch(clone / 'objects/info/alternates', str(tmp_path / 'foreign/objects') + '\n')
    with pytest.raises(ValueError, match='uncovered git metadata'):
        builder.build(**paths)


ASSET_REASON = 'third-party FlyWire/FLYNN asset copy, not a scene registry'


def test_connectome_asset_copies_excluded_with_reason(tmp_path):
    paths = _machine(tmp_path)
    main = Path(paths['main'])
    graph = 'graph-' + 'a' * 64
    for parent in (main / 'data/assets/flynn', main / 'runs/r1/copied-assets',
                   main / '.worktrees/paper/runs/t/assets'):
        _touch(parent / graph / 'drosophila adult connectome' / 'connections_princeton.csv')
    declaration = builder.build(**paths)
    roots = {row['name']: row for row in declaration['roots']}
    reasons = {row['path']: row['reason'] for root in roots.values()
               if root['kind'] == 'directory' for row in root['exclude']}
    for parent in (main / 'data/assets/flynn', main / 'runs/r1/copied-assets',
                   main / '.worktrees/paper/runs/t/assets'):
        assert reasons[str(parent / graph)] == ASSET_REASON


def test_graph_directory_without_connectome_is_not_excluded(tmp_path):
    paths = _machine(tmp_path)
    main = Path(paths['main'])
    _touch(main / 'runs' / ('graph-' + 'b' * 64) / 'scenes.json')
    roots = {row['name']: row for row in builder.build(**paths)['roots']}
    assert not any('graph-' in row['path'] for row in roots['palimpsest-main']['exclude'])


def test_venv_named_directory_needs_pyvenv_cfg(tmp_path):
    paths = _machine(tmp_path)
    main = Path(paths['main'])
    _touch(main / 'docs/venv/scenes.json')
    roots = {row['name']: row for row in builder.build(**paths)['roots']}
    excluded = {row['path'] for row in roots['palimpsest-main']['exclude']}
    assert str(main / '.venv') in excluded and str(main / 'docs/venv') not in excluded


def test_compare_manifest_accepts_identical_and_rejects_drift(tmp_path, capsys):
    paths = _machine(tmp_path)
    reviewed = tmp_path / 'reviewed.json'
    reviewed.write_bytes(builder.render(builder.build(**paths)))
    argv = ['--shraddha', paths['shraddha'], '--main', paths['main'],
            '--codex-worktrees', paths['codex_worktrees'],
            '--advertisement', paths['advertisement'],
            '--submodule-advertisement', paths['submodule_advertisement'],
            '--compare-manifest', str(reviewed)]
    assert builder.main(argv) == 0
    (Path(paths['main']) / '.worktrees/new-tree').mkdir()
    assert builder.main(argv) == 1
    assert 'new-tree' in capsys.readouterr().out


def test_pytest_basetemp_trees_under_runs_are_excluded_but_mixed_dirs_are_not(tmp_path):
    paths = _machine(tmp_path)
    main = Path(paths['main'])
    _touch(main / 'runs/paper-tests/test_campaign_identity_binds_c0/x.json', '{}')
    _touch(main / 'runs/paper-tests/test_other0/y.json', '{}')
    _touch(main / 'runs/registry/test_roster0/r.json', '{}')
    _touch(main / 'runs/registry/scenes/s.json', '{}')
    declaration = builder.build(**paths)
    excluded = {row['path']: row['reason'] for row in
                {r['name']: r for r in declaration['roots']}['palimpsest-main']['exclude']}
    assert 'pytest temporary tree' in excluded[str(main / 'runs/paper-tests')]
    assert str(main / 'runs/registry') not in excluded
