"""Synthetic fixtures only for puck v4 stage S1 (scene-ID admission).

Every root is a pytest tmp directory or a throwaway Git repository. No tracked
registry, retained input, model, simulator, or held-out scene payload is opened;
the only tracked file read is the hash-pinned v4 protocol document.
"""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from palimpsest import puck_v4_scene_admission as s1

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / 'docs/plans/m6-puck-navigation-v4-regenerated-on-policy-relabeling-protocol.json'
CLI = ROOT / 'scripts/admit_puck_v4_scene_ids.py'
PROTOCOL_SHA = 'f885fc8d857cc47ec696ad65501b70ac80e16dfa5439fd5bf62919f868bc286b'
GIT = '/usr/bin/git'


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(value, (dict, list)):
        value = json.dumps(value)
    path.write_text(value)
    return path


def _go(tmp_path, *, stage='S1', sha=PROTOCOL_SHA, name='go.json', **extra):
    record = {'kind': 'puck-v4-stage-go-v1', 'version': 1, 'stage': stage,
              'protocol_sha256': sha, 'granted_by': 'fixture owner',
              'granted_at': '2026-11-08', **extra}
    return _write(tmp_path / 'gos' / name, record)


def _declaration(tmp_path, roots, name='comparison.json'):
    return _write(tmp_path / 'decl' / name,
                  {'kind': 'puck-v4-s1-comparison-set-v1', 'version': 1, 'roots': roots})


def _dir_root(path, name='tree', **extra):
    return {'name': name, 'kind': 'directory', 'path': str(path), 'exclude': [],
            'held_out_payloads': False, **extra}


def _prior_tree(tmp_path):
    tree = tmp_path / 'tree'
    _write(tree / 'docs/reports/teacher.json',
           {'train_scenes': list(range(6000, 6016)), 'recorded_dev_scene_ids': [6016, 6019],
            'bytes': 6512, 'sha256': '6510' + 'a' * 60})
    _write(tree / 'docs/reports/dev.md', '# Dev\nScene IDs: 6100..6103\n')
    _write(tree / 'docs/plans/v3.json', {'scene_reservations': {'collection': [6110, 6111],
                                                                'development': '6120-6123'}})
    _write(tree / 'runs/reg/events.jsonl',
           json.dumps({'scene_id': 1003}) + '\n' + json.dumps({'layout_seed': 3130}) + '\n')
    _write(tree / 'notes.md', 'We spent 6512 bytes on prose.\n')
    return tree


def _admit(tmp_path, roots, *, go=True, output=None, held_out_go=None, lost_root=None):
    output = output or tmp_path / 'out' / 'admission.json'
    return s1.admit(protocol_path=PROTOCOL, comparison_set_path=_declaration(tmp_path, roots),
                    output_path=output, execute=True,
                    go_record_path=_go(tmp_path) if go is True else go,
                    held_out_go_record_path=held_out_go,
                    lost_root=lost_root or str(tmp_path / 'lost-brain')), output


def _report(path):
    return json.loads(Path(path).read_bytes())


# Protocol and roster ---------------------------------------------------------

def test_protocol_is_hash_pinned_and_roster_derived():
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == PROTOCOL_SHA
    roster = s1.derive_roster(json.loads(PROTOCOL.read_bytes()))
    assert roster['new_scene_ids'] == [6510, 6511, 6512, 6513, 6520, 6521, 6522, 6523]
    assert roster['intentional_reuse'] == {'S0a': list(range(6000, 6020)),
                                           'S0d': [6100, 6101, 6102, 6103]}
    assert roster['held_out_authored'] == list(range(6200, 6208))
    assert roster['max_historical_puck_id'] == 6207


def test_tampered_protocol_hash_refused(tmp_path):
    copy_path = _write(tmp_path / 'protocol.json', PROTOCOL.read_text() + ' ')
    with pytest.raises(s1.AdmissionRefused, match='protocol sha256'):
        s1.admit(protocol_path=copy_path, comparison_set_path=_declaration(tmp_path, []),
                 output_path=tmp_path / 'o.json', execute=False)


@pytest.mark.parametrize('mutate, message', [
    (lambda p: p['contamination_admission_before_mint']['intentional_reuse_exceptions']
     .__setitem__('6510-6513', 'smuggled'), 'intentional reuse'),
    (lambda p: p['contamination_admission_before_mint']['intentional_reuse_exceptions']
     .__setitem__('6000-6020', 'S0a regenerates'), 'intentional reuse'),
    (lambda p: p['contamination_admission_before_mint']['intentional_reuse_exceptions']
     .pop('6100-6103'), 'intentional reuse'),
    (lambda p: p['scene_reservations'].__setitem__('collection', [6510, 6511, 6512, 6100]),
     'collection'),
    (lambda p: p['owner_decisions_resolution']['choices'].__setitem__('D9_order', 'S0 first'),
     'D9'),
])
def test_roster_accepts_intentional_reuse_only_for_declared_ranges(mutate, message):
    protocol = json.loads(PROTOCOL.read_bytes())
    mutate(protocol)
    with pytest.raises(s1.AdmissionRefused, match=message):
        s1.derive_roster(protocol)


# GO records and plan-only ----------------------------------------------------

def test_plan_only_is_default_and_never_writes_or_reads_contents(tmp_path, capsys):
    tree = _prior_tree(tmp_path)
    _write(tree / 'collide.json', {'scene_id': 6512})  # would collide if read
    output = tmp_path / 'out' / 'admission.json'
    declaration = _declaration(tmp_path, [_dir_root(tree)])
    assert s1.main(['--protocol', str(PROTOCOL), '--comparison-set', str(declaration),
                    '--output', str(output)]) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan['mode'] == 'plan-only'
    assert plan['writes'] == [] and plan['contents_read'] is False
    assert plan['required_go'] == {'stage': 'S1', 'protocol_sha256': PROTOCOL_SHA}
    assert plan['roster']['new_scene_ids'][0] == 6510
    assert plan['lost_root']['status'] == 'absent-recorded-not-scanned'
    assert not output.exists() and not output.parent.exists()


def test_plan_only_cli_subprocess_writes_nothing(tmp_path):
    tree = _prior_tree(tmp_path)
    output = tmp_path / 'out.json'
    result = subprocess.run(
        [sys.executable, str(CLI), '--protocol', str(PROTOCOL), '--comparison-set',
         str(_declaration(tmp_path, [_dir_root(tree)])), '--output', str(output)],
        capture_output=True, text=True, env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')})
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['mode'] == 'plan-only'
    assert not output.exists()


def test_plan_only_reports_blockers_without_writing(tmp_path, capsys):
    output = tmp_path / 'out.json'
    declaration = _declaration(tmp_path, [_dir_root(tmp_path / 'missing')])
    assert s1.main(['--protocol', str(PROTOCOL), '--comparison-set', str(declaration),
                    '--output', str(output)]) == 1
    plan = json.loads(capsys.readouterr().out)
    assert any('missing' in blocker for blocker in plan['blockers'])
    assert not output.exists()


def test_execute_without_go_record_refused(tmp_path):
    tree = _prior_tree(tmp_path)
    with pytest.raises(s1.AdmissionRefused, match='GO record'):
        _admit(tmp_path, [_dir_root(tree)], go=None)
    assert not (tmp_path / 'out').exists()


@pytest.mark.parametrize('kwargs, message', [
    ({'stage': 'S2'}, 'stage'),
    ({'stage': 's1'}, 'stage'),
    ({'sha': 'f' * 64}, 'protocol_sha256'),
    ({'sha': PROTOCOL_SHA[:-1] + '0'}, 'protocol_sha256'),
    ({'extra_field': True}, 'fields'),
])
def test_go_record_mismatch_refused(tmp_path, kwargs, message):
    tree = _prior_tree(tmp_path)
    with pytest.raises(s1.AdmissionRefused, match=message):
        _admit(tmp_path, [_dir_root(tree)], go=_go(tmp_path, **kwargs))
    assert not (tmp_path / 'out').exists()


def test_held_out_go_cannot_stand_in_for_s1_go(tmp_path):
    tree = _prior_tree(tmp_path)
    with pytest.raises(s1.AdmissionRefused, match='stage'):
        _admit(tmp_path, [_dir_root(tree)], go=_go(tmp_path, stage=s1.HELD_OUT_GO_STAGE))


# Clean admission, reuse and determinism --------------------------------------

def test_clean_comparison_admitted_with_reservation_and_input_hashes(tmp_path):
    tree = _prior_tree(tmp_path)
    result, output = _admit(tmp_path, [_dir_root(tree)])
    report = _report(output)
    assert result['verdict'] == report['verdict'] == 'admitted'
    assert report['reservation']['scene_ids'] == [6510, 6511, 6512, 6513,
                                                  6520, 6521, 6522, 6523]
    assert report['collisions'] == []
    reuse = report['intentional_reuse_occurrences']
    assert {row['scene_id'] for row in reuse} >= {6000, 6015, 6016, 6019, 6100, 6103}
    assert all(row['stage'] in ('S0a', 'S0d') for row in reuse)
    inputs = report['inputs']
    assert inputs['protocol']['sha256'] == PROTOCOL_SHA
    assert len(inputs['comparison_set']['sha256']) == 64
    assert len(inputs['go_record']['sha256']) == 64
    assert inputs['held_out_go_record'] is None
    assert report['roots'][0]['files_scanned'] == 5
    assert len(report['roots'][0]['content_digest']) == 64
    # Untyped prose and byte counts are diagnostics, never collisions.
    assert {row['path'] for row in report['untyped_new_id_mentions']} == {
        'notes.md', 'docs/reports/teacher.json'}


def test_report_is_deterministic(tmp_path):
    tree = _prior_tree(tmp_path)
    roots = [_dir_root(tree)]
    _, first = _admit(tmp_path, roots, output=tmp_path / 'a' / 'r.json')
    _, second = _admit(tmp_path, roots, output=tmp_path / 'b' / 'r.json')
    assert first.read_bytes() == second.read_bytes()
    assert first.read_bytes() == s1.canonical_bytes(_report(first))


def test_existing_output_or_output_inside_root_refused(tmp_path):
    tree = _prior_tree(tmp_path)
    existing = _write(tmp_path / 'out' / 'admission.json', '{}')
    with pytest.raises(s1.AdmissionRefused, match='fresh'):
        _admit(tmp_path, [_dir_root(tree)], output=existing)
    with pytest.raises(s1.AdmissionRefused, match='inside'):
        _admit(tmp_path, [_dir_root(tree)], output=tree / 'admission.json')


# Collisions ------------------------------------------------------------------

@pytest.mark.parametrize('relative, content', [
    ('registry/scenes.json', {'scenes': [{'scene_id': 6512, 'split': 'train'}]}),
    ('registry/events.jsonl', json.dumps({'tick': 3}) + '\n' + json.dumps({'layout_seed': 6520})),
    ('docs/old.md', '# Old\n- Scene IDs: 6521-6523\n'),
    ('docs/keys.json', {'scene_reservations': {'6513': 'positive control'}}),
    ('docs/range.json', {'scene_ids': '6505-6515'}),
])
def test_collision_detected_and_refused(tmp_path, relative, content):
    tree = _prior_tree(tmp_path)
    _write(tree / relative, content)
    result, output = _admit(tmp_path, [_dir_root(tree)])
    report = _report(output)
    assert result['verdict'] == report['verdict'] == 'refused'
    assert report['reservation'] is None
    assert report['collisions'] and all(row['path'] == relative for row in report['collisions'])
    assert {row['scene_id'] for row in report['collisions']} <= set(s1.NEW_SCENE_IDS)
    assert any('collision' in reason for reason in report['refusal_reasons'])


def test_cli_exit_code_on_collision(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'x.json', {'scene_id': 6510})
    output = tmp_path / 'out.json'
    code = s1.main(['--protocol', str(PROTOCOL), '--comparison-set',
                    str(_declaration(tmp_path, [_dir_root(tree)])), '--output', str(output),
                    '--execute', '--go-record', str(_go(tmp_path))])
    assert code == 1 and _report(output)['verdict'] == 'refused'


def test_ambiguous_unparsed_document_with_new_id_refused(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'broken.json', '{"scene_id": 6511,')
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'refused'
    assert _report(output)['ambiguous'][0]['path'] == 'broken.json'


def test_prior_puck_id_above_6207_breaks_lost_root_mitigation(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'later.json', {'scene_id': 6300})
    result, output = _admit(tmp_path, [_dir_root(tree)])
    report = _report(output)
    assert result['verdict'] == 'refused'
    assert report['lost_root']['mitigation_holds'] is False


def test_v4_lineage_documents_are_not_collisions(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / s1.PROTOCOL_RELATIVE_PATH, PROTOCOL.read_text())
    _write(tree / s1.COMPANION_RELATIVE_PATH, '# v4\nScene IDs: 6510-6513\n')
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'admitted'
    lineage = {row['path'] for row in _report(output)['lineage_documents']}
    assert lineage == {s1.PROTOCOL_RELATIVE_PATH, s1.COMPANION_RELATIVE_PATH}


def test_altered_protocol_at_lineage_path_is_not_lineage(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / s1.PROTOCOL_RELATIVE_PATH, {'scene_reservations': {'collection': [6510]}})
    result, _ = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'refused'


# Roots and the frozen lost-root exception ------------------------------------

def test_missing_non_exempt_root_refused(tmp_path):
    with pytest.raises(s1.AdmissionRefused, match='missing'):
        _admit(tmp_path, [_dir_root(tmp_path / 'absent')])
    assert not (tmp_path / 'out').exists()


def test_symlinked_root_refused(tmp_path):
    tree = _prior_tree(tmp_path)
    link = tmp_path / 'link'
    link.symlink_to(tree)
    with pytest.raises(s1.AdmissionRefused, match='symlink'):
        _admit(tmp_path, [_dir_root(link)])


def test_lost_root_absence_recorded_not_fatal_with_risk(tmp_path):
    tree = _prior_tree(tmp_path)
    result, output = _admit(tmp_path, [_dir_root(tree)])
    lost = _report(output)['lost_root']
    assert result['verdict'] == 'admitted'
    assert lost['path'] == str(tmp_path / 'lost-brain')
    assert lost['status'] == 'absent-recorded-not-scanned'
    assert lost['treated_as_clean'] is False
    assert 'undetected' in lost['risk']
    assert lost['mitigation_holds'] is True and lost['max_observed_prior_puck_id'] == 6123


def test_protocol_lost_root_is_the_frozen_brain_path():
    protocol = json.loads(PROTOCOL.read_bytes())
    assert s1.lost_root_from_protocol(protocol) == '/home/utkarsh/Work/shraddha/brain'


def test_present_lost_root_refused(tmp_path):
    tree = _prior_tree(tmp_path)
    present = tmp_path / 'brain'
    present.mkdir()
    with pytest.raises(s1.AdmissionRefused, match='lost root'):
        _admit(tmp_path, [_dir_root(tree)], lost_root=str(present))


def test_declared_root_inside_lost_root_refused(tmp_path):
    lost = tmp_path / 'brain'
    with pytest.raises(s1.AdmissionRefused, match='lost root'):
        _admit(tmp_path, [_dir_root(lost / '.worktrees' / 'x' / 'runs')], lost_root=str(lost))


def test_excluded_subtree_recorded_and_skipped(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / '.venv/lib/x.json', {'scene_id': 6510})
    root = _dir_root(tree, exclude=[{'path': str(tree / '.venv'), 'reason': 'interpreter'}])
    result, output = _admit(tmp_path, [root])
    assert result['verdict'] == 'admitted'
    assert _report(output)['roots'][0]['excluded'] == [
        {'path': str(tree / '.venv'), 'reason': 'interpreter'}]


# Held-out payloads (D2) ------------------------------------------------------

def test_held_out_ids_alone_need_no_extra_go(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'v3.json', {'held_out_scene_ids': list(range(6200, 6208))})
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'admitted'
    assert _report(output)['held_out_payload_objects_not_compared'] == []


def test_undeclared_held_out_payload_refused_without_d2_go(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'catalog.json', {'rows': [{'seed': 6203, 'puck_xy': [0.5, 0.5]}]})
    result, output = _admit(tmp_path, [_dir_root(tree)])
    report = _report(output)
    assert result['verdict'] == 'refused'
    assert report['held_out_payload_objects_not_compared'] == [
        {'root': 'tree', 'path': 'catalog.json', 'pointer': '/rows/0', 'scene_id': 6203}]
    assert 'puck_xy' not in json.dumps(report) and '0.5' not in json.dumps(report)


def test_held_out_payload_root_requires_separate_d2_go(tmp_path):
    tree = _prior_tree(tmp_path)
    root = _dir_root(tree, held_out_payloads=True)
    with pytest.raises(s1.AdmissionRefused, match='D2'):
        _admit(tmp_path, [root])
    with pytest.raises(s1.AdmissionRefused, match='stage'):
        _admit(tmp_path, [root], held_out_go=_go(tmp_path, name='ho.json'))
    with pytest.raises(s1.AdmissionRefused, match='protocol_sha256'):
        _admit(tmp_path, [root], held_out_go=_go(
            tmp_path, stage=s1.HELD_OUT_GO_STAGE, sha='0' * 64, name='ho.json'))
    assert not (tmp_path / 'out').exists()


def test_held_out_payload_with_d2_go_recorded_never_compared(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'catalog.json', {'rows': [{'seed': 6203, 'puck_xy': [0.5, 0.5]}]})
    held = _go(tmp_path, stage=s1.HELD_OUT_GO_STAGE, name='ho.json')
    result, output = _admit(tmp_path, [_dir_root(tree, held_out_payloads=True)], held_out_go=held)
    report = _report(output)
    assert result['verdict'] == 'admitted'
    assert report['inputs']['held_out_go_record']['sha256'] == hashlib.sha256(
        held.read_bytes()).hexdigest()
    assert report['held_out_payload_objects_not_compared'][0]['scene_id'] == 6203
    assert report['claims']['held_out_payloads_compared'] is False


# Git roots ---------------------------------------------------------------------

def _git(repo, *args):
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(repo), 'GIT_CONFIG_NOSYSTEM': '1',
           'GIT_AUTHOR_NAME': 'f', 'GIT_AUTHOR_EMAIL': 'f@x', 'GIT_COMMITTER_NAME': 'f',
           'GIT_COMMITTER_EMAIL': 'f@x', 'GIT_AUTHOR_DATE': '2026-01-01T00:00:00Z',
           'GIT_COMMITTER_DATE': '2026-01-01T00:00:00Z'}
    return subprocess.run([GIT, '-C', str(repo), *args], env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def _repo(tmp_path, history):
    repo = tmp_path / 'repo'
    repo.mkdir()
    _git(repo, 'init', '-q', '-b', 'main')
    for files in history:
        for relative, content in files.items():
            if content is None:
                (repo / relative).unlink()
            else:
                _write(repo / relative, content)
        _git(repo, 'add', '-A')
        _git(repo, 'commit', '-q', '-m', 'c', '--allow-empty')
    return repo


def _git_root(repo, advertisement=None):
    return {'name': 'git', 'kind': 'git', 'path': str(repo),
            'advertisement': None if advertisement is None else str(advertisement),
            'held_out_payloads': False}


def test_git_history_collision_refused_even_if_deleted(tmp_path):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6522}}, {'a.json': None, 'b.md': 'x\n'}])
    result, output = _admit(tmp_path, [_git_root(repo), _dir_root(repo, name='work')])
    report = _report(output)
    assert result['verdict'] == 'refused'
    assert report['collisions'][0]['root'] == 'git'
    assert report['collisions'][0]['scene_id'] == 6522


def test_git_clean_history_admitted_with_tips(tmp_path):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6100}}])
    _git(repo, 'branch', 'side')
    result, output = _admit(tmp_path, [_git_root(repo), _dir_root(repo, name='work')])
    report = _report(output)
    assert result['verdict'] == 'admitted'
    git_root = next(row for row in report['roots'] if row['kind'] == 'git')
    assert sorted(git_root['refs']) == ['refs/heads/main', 'refs/heads/side']
    assert git_root['blobs_scanned'] == 1


def test_git_worktree_must_be_covered(tmp_path):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6100}}])
    _git(repo, 'worktree', 'add', '-q', str(tmp_path / 'wt'), '-b', 'wt')
    with pytest.raises(s1.AdmissionRefused, match='worktree'):
        _admit(tmp_path, [_git_root(repo), _dir_root(repo, name='work')])


def test_git_worktree_under_lost_root_recorded(tmp_path):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6100}}])
    lost = tmp_path / 'brain'
    _git(repo, 'worktree', 'add', '-q', str(lost / '.worktrees' / 'w'), '-b', 'w')
    import shutil
    shutil.rmtree(lost)
    result, output = _admit(tmp_path, [_git_root(repo), _dir_root(repo, name='work')],
                            lost_root=str(lost))
    report = _report(output)
    assert result['verdict'] == 'admitted'
    assert report['lost_root']['git_worktrees_excluded'] == [str(lost / '.worktrees' / 'w')]


def test_stale_remote_advertisement_refused(tmp_path):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6100}}])
    _git(repo, 'remote', 'add', 'origin', str(tmp_path / 'nowhere'))
    with pytest.raises(s1.AdmissionRefused, match='advertisement'):
        _admit(tmp_path, [_git_root(repo), _dir_root(repo, name='work')])
    advert = _write(tmp_path / 'advert.txt', ('b' * 40) + '\trefs/heads/main\n')
    with pytest.raises(s1.AdmissionRefused, match='advertis'):
        _admit(tmp_path, [_git_root(repo, advert), _dir_root(repo, name='work')])
    head = _git(repo, 'rev-parse', 'HEAD')
    good = _write(tmp_path / 'advert2.txt', head + '\trefs/heads/main\n')
    result, output = _admit(tmp_path, [_git_root(repo, good), _dir_root(repo, name='work')])
    assert result['verdict'] == 'admitted'
    git_root = next(row for row in _report(output)['roots'] if row['kind'] == 'git')
    assert git_root['advertisement_sha256'] == hashlib.sha256(good.read_bytes()).hexdigest()
