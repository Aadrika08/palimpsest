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
                     '.worktrees/authority-study-final/.venv/x', '.worktrees/paper/docs/b.md',
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
        'puck-v4-s1-out', 'puck-v4-s1-attempt-ledger'}
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
    (main / 'runs/temp').symlink_to('/var/tmp')
    declaration = builder.build(**paths)
    roots = {row['name']: row for row in declaration['roots']}
    excluded = {row['path']: row['reason'] for row in roots['palimpsest-main']['exclude']}
    assert 'dangling' in excluded[str(main / 'runs/dangling')]
    assert 'ephemeral' in excluded[str(main / 'runs/temp')]
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
        builder.build(**paths)


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
