"""Synthetic fixtures only for puck v4 stage S1 (scene-ID admission).

Every root is a pytest tmp directory or a throwaway Git repository. No tracked
registry, retained input, model, simulator, or held-out scene payload is opened;
the only tracked file read is the hash-pinned v4 protocol document.
"""
import copy
import csv
import hashlib
import itertools
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


COMPANION = ROOT / 'docs/plans/m6-puck-navigation-v4-regenerated-on-policy-relabeling.md'
_LEDGERS = itertools.count()


def _go(tmp_path, *, stage='S1', sha=PROTOCOL_SHA, name='go.json', scope='S1', **extra):
    record = {'kind': 'puck-v4-stage-go-v1', 'version': 1, 'stage': stage, 'scope': scope,
              'protocol_sha256': sha, 'granted_by': 'fixture owner',
              'granted_at': '2026-11-08', **extra}
    return _write(tmp_path / 'gos' / name, record)


def _declaration(tmp_path, roots, name='comparison.json', unscanned=()):
    return _write(tmp_path / 'decl' / name,
                  {'kind': 'puck-v4-s1-comparison-set-v1', 'version': 1, 'roots': roots,
                   'unscanned': list(unscanned)})


def _dir_root(path, name='tree', **extra):
    return {'name': name, 'kind': 'directory', 'path': str(path), 'exclude': [],
            'held_out_payloads': False, 'lost_root_clone': False, **extra}


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


def _admit(tmp_path, roots, *, go=True, output=None, held_out_go=None, lost_root=None,
           ledger=None, unscanned=()):
    output = output or tmp_path / 'out' / 'admission.json'
    ledger = ledger or tmp_path / 'ledgers' / str(next(_LEDGERS))
    return s1.admit(protocol_path=PROTOCOL,
                    comparison_set_path=_declaration(tmp_path, roots, unscanned=unscanned),
                    output_path=output, execute=True,
                    go_record_path=_go(tmp_path) if go is True else go,
                    held_out_go_record_path=held_out_go,
                    lost_root=lost_root or str(tmp_path / 'lost-brain'),
                    attempt_ledger=str(ledger)), output


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
                    '--output', str(output)], attempt_ledger=str(tmp_path / 'ledger')) == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan['mode'] == 'plan-only'
    assert plan['writes'] == [] and plan['contents_read'] is False
    assert plan['required_go'] == {'stage': 'S1', 'scope': 'S1', 'protocol_sha256': PROTOCOL_SHA}
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
                    '--output', str(output)], attempt_ledger=str(tmp_path / 'ledger')) == 1
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
    ({'scope': 'S2'}, 'scope'),
    ({'supersedes_protocol_state': 'anything else'}, 'supersede'),
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
                    '--execute', '--go-record', str(_go(tmp_path))],
                   attempt_ledger=str(tmp_path / 'ledger'))
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


def test_companion_hash_frozen_at_drafting_commit():
    assert hashlib.sha256(COMPANION.read_bytes()).hexdigest() == s1.COMPANION_SHA256
    assert s1.COMPANION_SHA256.startswith('ed9c1c9d')
    assert {PROTOCOL_SHA, s1.COMPANION_SHA256} <= set(s1.LINEAGE_SHA256)


def test_v4_lineage_documents_are_matched_by_sha_at_any_path(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'copies/protocol.json', PROTOCOL.read_text())
    _write(tree / 'elsewhere/companion.md', COMPANION.read_text())
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'admitted'
    lineage = {row['path'] for row in _report(output)['lineage_documents']}
    assert lineage == {'copies/protocol.json', 'elsewhere/companion.md'}


def test_arbitrary_content_at_companion_path_is_not_lineage(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / s1.COMPANION_RELATIVE_PATH, '# v4\nScene IDs: 6510-6513\n')
    result, _ = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'refused'


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


def test_d2_go_must_name_scope_s1(tmp_path):
    tree = _prior_tree(tmp_path)
    root = _dir_root(tree, held_out_payloads=True)
    for scope in ('S2', 'S8a'):
        held = _go(tmp_path, stage=s1.HELD_OUT_GO_STAGE, scope=scope, name='ho.json')
        with pytest.raises(s1.AdmissionRefused, match='scope'):
            _admit(tmp_path, [root], held_out_go=held)
    held = _go(tmp_path, stage=s1.HELD_OUT_GO_STAGE, name='ho.json',
               supersedes_protocol_state=json.loads(PROTOCOL.read_bytes())['state'])
    with pytest.raises(s1.AdmissionRefused, match='supersede'):
        _admit(tmp_path, [root], held_out_go=held)


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


# Reviewer fixes: GO supersession -------------------------------------------------

def test_s1_go_may_supersede_protocol_state_for_s1_only(tmp_path):
    tree = _prior_tree(tmp_path)
    state = json.loads(PROTOCOL.read_bytes())['state']
    go = _go(tmp_path, supersedes_protocol_state=state)
    result, output = _admit(tmp_path, [_dir_root(tree)], go=go)
    assert result['verdict'] == 'admitted'
    assert _report(output)['inputs']['go_record']['supersedes_protocol_state_for_s1'] is True
    with pytest.raises(s1.AdmissionRefused, match='scope'):
        _admit(tmp_path, [_dir_root(tree)],
               go=_go(tmp_path, scope='S2', supersedes_protocol_state=state, name='g2.json'))


# Reviewer fixes: nested roots, walk safety ---------------------------------------

def test_nested_directory_roots_allowed_only_below_an_exclusion(tmp_path):
    tree = _prior_tree(tmp_path)
    inner = tree / 'runs'
    with pytest.raises(s1.AdmissionRefused, match='overlap'):
        _admit(tmp_path, [_dir_root(tree), _dir_root(inner, name='runs')])
    outer = _dir_root(tree, exclude=[{'path': str(inner), 'reason': 'declared separately'}])
    result, output = _admit(tmp_path, [outer, _dir_root(inner, name='runs')])
    assert result['verdict'] == 'admitted'
    assert [row['files_scanned'] for row in _report(output)['roots']] == [4, 1]


def test_unreadable_directory_refused_not_skipped(tmp_path):
    tree = _prior_tree(tmp_path)
    locked = tree / 'locked'
    locked.mkdir()
    locked.chmod(0)
    try:
        with pytest.raises(s1.AdmissionRefused, match='walk'):
            _admit(tmp_path, [_dir_root(tree)])
    finally:
        locked.chmod(0o755)


def test_uncovered_git_storage_directory_refused(tmp_path):
    tree = _prior_tree(tmp_path)
    (tree / 'vendored' / '.git').mkdir(parents=True)
    with pytest.raises(s1.AdmissionRefused, match='git storage'):
        _admit(tmp_path, [_dir_root(tree)])


def test_uncovered_gitfile_in_directory_root_refused(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'sub' / '.git', f'gitdir: {tmp_path}/other/.git\n')
    with pytest.raises(s1.AdmissionRefused, match='git storage'):
        _admit(tmp_path, [_dir_root(tree)])


def test_symlink_outside_declared_roots_refused_unless_excluded(tmp_path):
    tree = _prior_tree(tmp_path)
    outside = _write(tmp_path / 'outside' / 'x.json', {'scene_id': 6510})
    (tree / 'inside-link.json').symlink_to(tree / 'notes.md')
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert _report(output)['roots'][0]['unfollowed_symlinks'] == ['inside-link.json']
    (tree / 'out-link').symlink_to(outside.parent)
    with pytest.raises(s1.AdmissionRefused, match='symlink'):
        _admit(tmp_path, [_dir_root(tree)])
    excluded = _dir_root(tree, exclude=[{'path': str(tree / 'out-link'), 'reason': 'fixture'}])
    result, _ = _admit(tmp_path, [excluded], output=tmp_path / 'out2' / 'r.json')
    assert result['verdict'] == 'admitted'


def test_missing_git_object_refused(monkeypatch):
    oid = 'c' * 40
    outputs = iter([f'{oid} a.json\n'.encode(), f'{oid} missing\n'.encode()])
    monkeypatch.setattr(s1, '_git', lambda *args, **kwargs: next(outputs))
    with pytest.raises(s1.AdmissionRefused, match='missing'):
        s1._git_blobs('/repo', [oid])


# Reviewer fixes: ID detection ------------------------------------------------------

@pytest.mark.parametrize('text', ['6505-6515', '6505–6515', '6505—6515',
                                  '6505..6515', 'scenes 6512'])
def test_raw_new_ids_expand_ranges_and_dashes(text):
    assert s1._raw_new_ids(text.encode()) >= ({6512} if 'scenes' in text else {6510, 6513})


@pytest.mark.parametrize('relative, content', [
    ('docs/em.md', '# x\nScene IDs: 6505—6515\n'),
    ('docs/table.md', '| scene | 6512 |\n'),
    ('docs/en.json', {'scene_ids': '6505–6515'}),
    ('a.json', {'roster': [6510]}),
    ('b.json', {'split': {'held_out': [6521]}}),
    ('c.json', {'reservation': '6510-6513'}),
    ('d.json', {'collection': [6511]}),
    ('e.json', {'development': [6522]}),
    ('f.json', {'rows': [{'id': 6520, 'goal_xy': [1.0, 2.0]}]}),
    ('g.yaml', 'scene_id: 6512\n'),
    ('h.toml', 'layout = 6513\n'),
    ('i.txt', 'see 6510\n'),
    ('j.csv', 'scene,bytes\n6512,1\n'),
])
def test_broadened_detection_refuses(tmp_path, relative, content):
    tree = _prior_tree(tmp_path)
    _write(tree / relative, content)
    result, output = _admit(tmp_path, [_dir_root(tree)])
    report = _report(output)
    assert result['verdict'] == 'refused'
    assert (report['collisions'] or report['ambiguous'])[0]['path'] == relative


@pytest.mark.parametrize('relative, content', [
    ('g.yaml', 'bytes: 6512\n'),
    ('h.toml', 'retained_bytes = 6513\n'),
    ('j.csv', 'scene,bytes\n1,6512\n'),
])
def test_raw_only_hits_typed_as_non_scene_are_diagnostics(tmp_path, relative, content):
    tree = _prior_tree(tmp_path)
    _write(tree / relative, content)
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'admitted'
    assert relative in {row['path'] for row in _report(output)['untyped_new_id_mentions']}


# Reviewer fixes: reservation record, attempts, caps -------------------------------

def test_report_records_source_hashes_and_inventory_hashes(tmp_path):
    tree = _prior_tree(tmp_path)
    _, output = _admit(tmp_path, [_dir_root(tree)])
    report = _report(output)
    sources = report['sources']
    module = ROOT / 'src/palimpsest/puck_v4_scene_admission.py'
    assert sources['src/palimpsest/puck_v4_scene_admission.py'] == hashlib.sha256(
        module.read_bytes()).hexdigest()
    assert set(sources) >= {'src/palimpsest/puck_scene_markdown.py',
                            'scripts/admit_puck_v4_scene_ids.py', 'git_version'}
    root = report['roots'][0]
    assert len(root['inventory_before_sha256']) == 64
    assert root['inventory_before_sha256'] == root['inventory_after_sha256']
    assert report['reservation']['output_cap_bytes'] == 64 * 1024 ** 2


def test_attempt_receipt_written_before_reads_and_second_attempt_refused(tmp_path, monkeypatch):
    tree = _prior_tree(tmp_path)
    ledger = tmp_path / 'ledger'
    seen = []
    original = s1._Scan.scan_directory

    def spy(self, root, *args):
        seen.append((ledger / s1.ATTEMPT_RECEIPT_NAME).exists())
        return original(self, root, *args)
    monkeypatch.setattr(s1._Scan, 'scan_directory', spy)
    _, output = _admit(tmp_path, [_dir_root(tree)], ledger=ledger)
    assert seen == [True]
    receipt = (ledger / s1.ATTEMPT_RECEIPT_NAME).read_bytes()
    assert _report(output)['attempt']['receipt_sha256'] == hashlib.sha256(receipt).hexdigest()
    with pytest.raises(s1.AdmissionRefused, match='attempt'):
        _admit(tmp_path, [_dir_root(tree)], ledger=ledger, output=tmp_path / 'other' / 'r.json')
    assert not (tmp_path / 'other').exists()


def test_output_cap_refused(tmp_path, monkeypatch):
    tree = _prior_tree(tmp_path)
    monkeypatch.setattr(s1, 'MAX_OUTPUT_BYTES', 64)
    with pytest.raises(s1.AdmissionRefused, match='cap'):
        _admit(tmp_path, [_dir_root(tree)])
    assert not (tmp_path / 'out' / 'admission.json').exists()


def test_output_allowed_only_below_an_exclusion(tmp_path):
    tree = _prior_tree(tmp_path)
    out_dir = tree / 'puck-v4-s1-out'
    root = _dir_root(tree, exclude=[{'path': str(out_dir), 'reason': 'S1 output'}])
    result, output = _admit(tmp_path, [root], output=out_dir / 'admission.json')
    assert result['verdict'] == 'admitted' and output.exists()


def test_unscanned_projects_recorded(tmp_path):
    tree = _prior_tree(tmp_path)
    other = tmp_path / 'posthumus'
    other.mkdir()
    rows = [{'path': str(other), 'reason': 'unrelated project'}]
    _, output = _admit(tmp_path, [_dir_root(tree)], unscanned=rows)
    assert _report(output)['unscanned'] == rows
    with pytest.raises(s1.AdmissionRefused, match='unscanned'):
        _admit(tmp_path, [_dir_root(tree)], unscanned=[{'path': str(tree), 'reason': 'x'}])


# Reviewer fixes: plan-only preflight ------------------------------------------------

def _plan(tmp_path, roots, lost_root=None):
    return s1.admit(protocol_path=PROTOCOL, comparison_set_path=_declaration(tmp_path, roots),
                    output_path=tmp_path / 'out.json',
                    lost_root=lost_root or str(tmp_path / 'lost-brain'),
                    attempt_ledger=str(tmp_path / 'ledger'))


def test_plan_reports_uncovered_worktree_and_stale_advertisement(tmp_path):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6100}}])
    _git(repo, 'worktree', 'add', '-q', str(tmp_path / 'wt'), '-b', 'wt')
    _git(repo, 'remote', 'add', 'origin', str(tmp_path / 'nowhere'))
    advert = _write(tmp_path / 'advert.txt', ('b' * 40) + '\trefs/heads/main\n')
    plan = _plan(tmp_path, [_git_root(repo, advert), _dir_root(repo, name='work')])
    assert any('worktree' in b for b in plan['blockers'])
    assert any('advertis' in b for b in plan['blockers'])
    assert not (tmp_path / 'out.json').exists()
    plan = _plan(tmp_path, [_git_root(repo, advert), _dir_root(repo, name='work'),
                            _dir_root(tmp_path / 'wt', name='wt')])
    assert not any('worktree' in b for b in plan['blockers'])


def test_plan_accepts_worktree_excluded_with_reason(tmp_path):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6100}}])
    _git(repo, 'worktree', 'add', '-q', str(repo / 'nested' / 'wt'), '-b', 'wt')
    root = _dir_root(repo, name='work',
                     exclude=[{'path': str(repo / 'nested'), 'reason': 'agent scratch'}])
    plan = _plan(tmp_path, [_git_root(repo), root])
    assert plan['blockers'] == []
    assert plan['git'][0]['worktrees_excluded'] == [str(repo / 'nested' / 'wt')]


def test_plan_reports_lost_root_clones(tmp_path):
    lost = tmp_path / 'brain'
    clone = tmp_path / 'codex' / '0071' / 'brain'
    _write(clone / '.git', f'gitdir: {lost}/.git/worktrees/brain\n')
    _write(clone / 'x.md', 'hello\n')
    plan = _plan(tmp_path, [_dir_root(clone, name='codex-0071')], lost_root=str(lost))
    assert plan['lost_root_clones'] == [{'root': 'codex-0071', 'path': str(clone),
                                         'gitdir': f'{lost}/.git/worktrees/brain'}]
    assert any('lost_root_clone' in b for b in plan['blockers'])
    flagged = _dir_root(clone, name='codex-0071', lost_root_clone=True)
    assert _plan(tmp_path, [flagged], lost_root=str(lost))['blockers'] == []
    result, output = _admit(tmp_path, [flagged], lost_root=str(lost))
    assert result['verdict'] == 'admitted'
    assert _report(output)['lost_root']['clones_scanned'] == [str(clone)]


# Round 3: full inventory before the receipt, in plan-only too ---------------------

def _hazard(tree, kind, tmp_path):
    if kind == 'oversize':
        _write(tree / 'big.json', '{"x": "' + 'a' * 300 + '"}')
    elif kind == 'unreadable-file':
        _write(tree / 'secret.json', '{}').chmod(0)
    elif kind == 'unreadable-dir':
        (tree / 'locked').mkdir()
        (tree / 'locked').chmod(0)
    elif kind == 'symlink':
        (tree / 'escape').symlink_to(_write(tmp_path / 'outside' / 'x.md', 'x\n'))
    elif kind == 'git':
        (tree / 'vendored' / '.git').mkdir(parents=True)


@pytest.mark.parametrize('kind, message', [
    ('oversize', 'exceeds'), ('unreadable-file', 'unreadable'), ('unreadable-dir', 'walk'),
    ('symlink', 'symlink'), ('git', 'git storage')])
def test_inventory_hazards_are_plan_blockers_and_refused_before_receipt(
        tmp_path, monkeypatch, kind, message):
    monkeypatch.setattr(s1, 'MAX_FILE_BYTES', 256)
    tree = _prior_tree(tmp_path)
    _hazard(tree, kind, tmp_path)
    try:
        plan = _plan(tmp_path, [_dir_root(tree)])
        assert any(message in blocker for blocker in plan['blockers'])
        ledger = tmp_path / 'ledger-x'
        with pytest.raises(s1.AdmissionRefused, match=message):
            _admit(tmp_path, [_dir_root(tree)], ledger=ledger)
        assert not (ledger / s1.ATTEMPT_RECEIPT_NAME).exists()
    finally:
        for path in (tree / 'secret.json', tree / 'locked'):
            if path.exists():
                path.chmod(0o755)


def test_undecodable_file_name_is_a_blocker(tmp_path):
    tree = _prior_tree(tmp_path)
    with open(os.fsencode(tree) + b'/bad-\xff.json', 'wb') as stream:
        stream.write(b'{}')
    plan = _plan(tmp_path, [_dir_root(tree)])
    assert any('UTF-8' in blocker for blocker in plan['blockers'])


# Round 3: post-receipt crash safety -------------------------------------------------

def test_read_error_after_receipt_is_a_recorded_refusal(tmp_path, monkeypatch):
    tree = _prior_tree(tmp_path)
    original = Path.read_bytes

    def failing(self):
        if self.name == 'dev.md':
            raise PermissionError('vanished permission')
        return original(self)
    monkeypatch.setattr(Path, 'read_bytes', failing)
    result, output = _admit(tmp_path, [_dir_root(tree)])
    report = _report(output)
    assert result['verdict'] == 'refused' and report['reservation'] is None
    assert any('vanished permission' in reason for reason in report['refusal_reasons'])


def test_change_after_receipt_is_a_recorded_refusal(tmp_path, monkeypatch):
    tree = _prior_tree(tmp_path)
    original = s1._Scan.document

    def mutate(self, root, relative, raw, oid=None):
        _write(tree / 'late.json', {'x': 1})
        return original(self, root, relative, raw, oid)
    monkeypatch.setattr(s1._Scan, 'document', mutate)
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'refused'
    assert any('changed' in reason for reason in _report(output)['refusal_reasons'])


def test_oversized_csv_field_is_ambiguous_not_a_crash(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'wide.csv', 'scene,notes\n6512,"' + 'x' * 200000 + '"\n')
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'refused'
    assert _report(output)['ambiguous'][0]['path'] == 'wide.csv'


def test_deep_json_is_unparsed_and_ambiguous_not_a_crash(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'deep.json', '[' * 100000 + '6510' + ']' * 100000)
    _write(tree / 'deep-clean.json', '[' * 100000 + '1' + ']' * 100000)
    result, output = _admit(tmp_path, [_dir_root(tree)])
    report = _report(output)
    assert result['verdict'] == 'refused'
    assert [row['path'] for row in report['ambiguous']] == ['deep.json']
    assert {row['path'] for row in report['unparsed_documents']} >= {'deep.json'}


def test_walk_recursion_error_is_contained(monkeypatch):
    def boom(*args, **kwargs):
        raise RecursionError('too deep')
    monkeypatch.setattr(s1, '_walk', boom)
    assert s1._parse_document('a.json', b'{"scene_id": 6510}') is None


# Round 3: numeric keys holding geometry ---------------------------------------------

@pytest.mark.parametrize('content, scene_id', [
    ({'6510': {'puck_xy': [0.1, 0.2]}}, 6510),
    ({'rows': {'6511': {'rover_pose': [0.0, 0.0, 0.0]}}}, 6511),
])
def test_numeric_key_with_geometry_child_is_a_typed_scene_id(tmp_path, content, scene_id):
    tree = _prior_tree(tmp_path)
    _write(tree / 'layouts.json', content)
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'refused'
    assert [row['scene_id'] for row in _report(output)['collisions']] == [scene_id]


def test_numeric_key_with_held_out_geometry_is_a_held_out_payload(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'catalog.json', {'rows': {'6203': {'goal_xy': [1.0, 1.0]}}})
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'refused'
    assert _report(output)['held_out_payload_objects_not_compared'][0]['scene_id'] == 6203


# Round 3: raw-byte prefilter and throughput ----------------------------------------

@pytest.mark.parametrize('raw, hit', [
    (b'{"a": 1, "date": "2026-11-07"}', False),
    (b'{"scene_id": 6512}', True),
    (b'{"scene_id": 6205}', True),
    (b'{"scene_ids": "5000-7000"}', True),
    (b'{"scene_ids": "5000\xe2\x80\x937000"}', True),
    (b'{"scene_id": 6.51e3}', True),
    (b'{"h": "a6512b", "n": 16512}', False),
])
def test_prefilter(raw, hit):
    assert s1.prefilter_hit(raw) is hit


def test_prefiltered_files_are_digested_but_not_parsed(tmp_path, monkeypatch):
    tree = _prior_tree(tmp_path)
    _write(tree / 'plain.json', {'note': 'nothing numeric here'})
    parsed = []
    original = s1._parse_document
    s1._measure_rates()  # warm the synthetic-sample rate cache outside the spy
    monkeypatch.setattr(s1, '_parse_document',
                        lambda relative, raw: parsed.append(relative) or original(relative, raw))
    _, output = _admit(tmp_path, [_dir_root(tree)])
    report = _report(output)
    assert 'plain.json' not in parsed and 'docs/plans/v3.json' in parsed
    assert report['roots'][0]['files_scanned'] == 6
    assert report['roots'][0]['files_parsed_after_prefilter'] == len(parsed)


def test_typed_exponent_and_float_forms_collide(tmp_path):
    tree = _prior_tree(tmp_path)
    _write(tree / 'float.json', '{"scene_id": 6.51e3}')
    result, output = _admit(tmp_path, [_dir_root(tree)])
    assert result['verdict'] == 'refused'
    assert _report(output)['collisions'][0]['scene_id'] == 6510


def test_plan_projects_throughput_and_blocks_above_80_percent(tmp_path, monkeypatch):
    tree = _prior_tree(tmp_path)
    plan = _plan(tmp_path, [_dir_root(tree)])
    estimate = plan['throughput']
    assert estimate['limit_seconds'] == 660 and estimate['blocker_fraction'] == 0.8
    assert estimate['bytes_by_suffix']['.json'] > 0 and estimate['sample_mb_per_s'] > 0
    assert estimate['projected_cpu_seconds'] < 528
    monkeypatch.setattr(s1, '_sample_rate', lambda: 1e-9)
    plan = _plan(tmp_path, [_dir_root(tree)])
    assert any('throughput' in blocker for blocker in plan['blockers'])


# Round 3: execution requirements and smaller items ---------------------------------

def test_execution_requirements_in_report_and_bytecode_required(tmp_path, monkeypatch):
    tree = _prior_tree(tmp_path)
    _, output = _admit(tmp_path, [_dir_root(tree)])
    requirements = _report(output)['execution_requirements']
    assert any('-B' in row for row in requirements)
    assert any('no other process' in row.lower() for row in requirements)
    assert '-B' in s1.build_parser().format_help()
    monkeypatch.setattr(s1, '_bytecode_disabled', lambda: False)
    with pytest.raises(s1.AdmissionRefused, match='-B'):
        _admit(tmp_path, [_dir_root(tree)], output=tmp_path / 'o2' / 'r.json')


def test_empty_advertisement_is_a_blocker(tmp_path):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6100}}])
    _git(repo, 'remote', 'add', 'origin', str(tmp_path / 'nowhere'))
    advert = _write(tmp_path / 'advert.txt', '')
    plan = _plan(tmp_path, [_git_root(repo, advert), _dir_root(repo, name='work')])
    assert any('empty' in blocker for blocker in plan['blockers'])


def test_supersession_string_is_frozen():
    assert s1.SUPERSEDED_PROTOCOL_STATE == (
        'prospective-docs-only; no source or numerical execution authorized')
    assert json.loads(PROTOCOL.read_bytes())['state'] == s1.SUPERSEDED_PROTOCOL_STATE


def test_sources_bind_package_init_and_interpreter(tmp_path):
    tree = _prior_tree(tmp_path)
    _, output = _admit(tmp_path, [_dir_root(tree)])
    sources = _report(output)['sources']
    assert 'src/palimpsest/__init__.py' in sources
    assert sources['interpreter'] == {'path': sys.executable, 'version': sys.version}


# Round 4: content-addressed dedupe and deduplicated throughput ---------------------

def _duplicated_tree(tmp_path):
    tree = _prior_tree(tmp_path)
    contents = {
        'collide.json': {'scene_id': 6512},
        'payload.json': {'rows': [{'seed': 6203, 'puck_xy': [0.5, 0.5]}]},
        'ambiguous.yaml': 'scene_id: 6520\n',
        'reuse.md': '# r\nScene IDs: 6000..6003\n',
        'untyped.md': 'prose 6511\n',
        'broken.json': '{"scene_id": 6513,',
    }
    for copy in ('a', 'b/c', 'd'):
        for name, content in contents.items():
            _write(tree / copy / name, content)
    return tree


def _without_work_counters(report):
    report = copy.deepcopy(report)
    report.pop('prefilter')
    return report


def test_dedupe_preserves_every_detection_result(tmp_path, monkeypatch):
    repo = _repo(tmp_path, [{'docs/x.json': {'scene_id': 6512}, 'docs/y.md': '# y\nhello\n'}])
    tree = _duplicated_tree(tmp_path)
    _write(tree / 'x-copy.json', {'scene_id': 6512})  # same bytes as the git blob
    roots = [_git_root(repo), _dir_root(repo, name='work'), _dir_root(tree)]
    reports, analyses = {}, {}
    original = s1._analyze
    for dedupe in (True, False):
        monkeypatch.setattr(s1, 'DEDUPE', dedupe)
        calls = []
        monkeypatch.setattr(s1, '_analyze', lambda *a: calls.append(a[0]) or original(*a))
        _, output = _admit(tmp_path, roots, output=tmp_path / f'out-{dedupe}' / 'r.json')
        reports[dedupe], analyses[dedupe] = _report(output), len(calls)
    assert _without_work_counters(reports[True]) == _without_work_counters(reports[False])
    assert reports[True]['verdict'] == 'refused'
    paths = {row['path'] for row in reports[True]['collisions']}
    assert {'a/collide.json', 'b/c/collide.json', 'd/collide.json', 'x-copy.json',
            'docs/x.json'} <= paths
    assert analyses[True] < analyses[False]
    assert reports[True]['prefilter']['unique_contents_analyzed'] == analyses[True]
    assert reports[False]['prefilter']['unique_contents_analyzed'] == analyses[False]


def test_plan_projection_counts_clean_tracked_worktree_files_once(tmp_path):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6100}, 'b.md': '# b\n6001\n'}])
    _write(repo / 'b.md', '# b\n6001 modified\n')  # dirty tracked: counted fully
    _write(repo / 'c.json', {'scene_id': 6002})     # untracked: counted fully
    other_a = _write(tmp_path / 'plain1' / 'same.json', {'scene_id': 6003})
    other_b = _write(tmp_path / 'plain2' / 'same.json', {'scene_id': 6003})
    plan = _plan(tmp_path, [_git_root(repo), _dir_root(repo, name='work'),
                            _dir_root(other_a.parent, name='p1'),
                            _dir_root(other_b.parent, name='p2')])
    estimate = plan['throughput']
    size = {name: (repo / name).stat().st_size for name in ('a.json', 'b.md', 'c.json')}
    blob_md = len('# b\n6001\n')
    same = other_a.stat().st_size
    raw_json = size['a.json'] * 2 + size['c.json'] + 2 * same
    assert estimate['bytes_by_suffix'] == {'.json': raw_json, '.md': blob_md + size['b.md']}
    assert estimate['deduplicated_bytes_by_suffix'] == {
        '.json': size['a.json'] + size['c.json'] + 2 * same,
        '.md': blob_md + size['b.md']}
    assert estimate['covered_by_git_blobs_bytes'] == size['a.json']
    assert estimate['digest_mb_per_s'] > estimate['sample_mb_per_s'] > 0
    expected = (size['a.json'] / (estimate['digest_mb_per_s'] * 1e6)
                + sum(estimate['deduplicated_bytes_by_suffix'].values())
                / (estimate['sample_mb_per_s'] * 1e6))
    assert estimate['projected_cpu_seconds'] == pytest.approx(expected)
    assert 'conservative' in estimate['rate_model']


def test_plan_reads_no_root_contents(tmp_path, monkeypatch):
    repo = _repo(tmp_path, [{'a.json': {'scene_id': 6100}}])
    tree = _duplicated_tree(tmp_path)
    original = Path.read_bytes

    def guarded(self):
        if str(self).startswith((str(tree), str(repo))):
            raise AssertionError(f'plan read root content {self}')
        return original(self)
    monkeypatch.setattr(Path, 'read_bytes', guarded)
    monkeypatch.setattr(s1._Scan, 'document', lambda *a, **k: (_ for _ in ()).throw(
        AssertionError('plan analysed content')))
    plan = _plan(tmp_path, [_git_root(repo), _dir_root(repo, name='work'), _dir_root(tree)])
    assert plan['contents_read'] is False and plan['throughput']['total_bytes'] > 0


# Round 5: prefilter matches detector semantics -------------------------------------

def _relevant(monkeypatch, relative, raw):
    """Would the detector report anything puck-relevant if the prefilter let it through?"""
    with monkeypatch.context() as patch:
        patch.setattr(s1, 'prefilter_hit', lambda raw: True)
        result = s1._analyze(relative, raw, hashlib.sha256(raw).hexdigest())
    return bool(result['ambiguous'] or result['untyped'] or result['held_out'] or any(
        6000 <= scene_id <= 6999 for _, scene_id in result['occurrences']))


_TEMPLATES = [('a.json', '{"scene_id": %s}'), ('b.json', '{"scene_ids": "%s"}'),
              ('c.json', '{"%s": {"puck_xy": [1.0]}}'), ('d.jsonl', '{"layout_seed": %s}\n'),
              ('e.yaml', 'scene_id: %s\n'), ('f.toml', 'layout = %s\n'),
              ('g.csv', 'scene,x\n%s,1\n'), ('h.md', '# t\nScene IDs: %s\n'),
              ('i.txt', 'see %s\n'), ('j.md', '| scene | %s |\n')]
_ATOMS = ['6510', '6512', '6203', '6.51e3', '651e1', '6.51E+03', '65100e-1', '0.6512', '1e-05',
          '2026-11-05', '5999.99999999999999999', '06512', '6505-6515', '6505..6515',
          '6505–6515', '6505—6515', '5000-7000', '\\u0036510', '٦٥١٠',
          '-6510', '6510.0', '16512', 'a6512', '6512b', '_6512', '.6512', '-', '.', ',', ' ',
          'e', '0', '1', '6', '5', '9', '[', ']', '"']


@pytest.mark.parametrize('relative, template', _TEMPLATES)
def test_every_detection_requires_a_prefilter_hit(monkeypatch, relative, template):
    import random
    generator = random.Random(relative)
    samples = [atom for atom in _ATOMS[:20]]
    samples += [''.join(generator.choice(_ATOMS) for _ in range(generator.randint(1, 5)))
                for _ in range(300)]
    relevant = 0
    for text in samples:
        raw = (template % text).encode()
        if _relevant(monkeypatch, relative, raw):
            relevant += 1
            assert s1.prefilter_hit(raw), (relative, text)
    assert relevant > 20


@pytest.mark.parametrize('raw', [b'{"x": 1e-05}', b'{"x": 0.6512}', b'{"d": "2026-11-05"}',
                                 b'{"x": 1e-05, "y": 0.6512, "d": "2026-11-05", "z": 3.5e2}'])
def test_prefilter_no_longer_hits_routine_numbers(raw):
    assert s1.prefilter_hit(raw) is False


@pytest.mark.parametrize('raw', [b'{"s": 6.51e3}', b'{"s": 651e1}', b'{"s": 5999.99999999999999999}',
                                 '{"s": "٦٥١٠"}'.encode(),
                                 b'{"s": "\\u0036510"}', b'{"s": "06512"}'])
def test_prefilter_hits_exotic_forms_the_detector_finds(raw):
    assert s1.prefilter_hit(raw) is True


# Round 5: plan-time calibration -----------------------------------------------------

def _calibration_fixture(tmp_path):
    plain = tmp_path / 'plain'
    for index in range(40):
        _write(plain / f'n{index:02}.json', {'value': index, 'note': 'x' * (50 + index)})
    for index in range(4):
        _write(plain / f'h{index}.json', {'scene_id': 6100 + index})
    _write(plain / 'doc.md', '# d\nnothing\n')
    held = tmp_path / 'held'
    _write(held / 'catalog.json', {'rows': [{'seed': 6203, 'puck_xy': [0.5, 0.5]}]})
    repo = _repo(tmp_path, [{'r.json': {'scene_id': 6101}}])
    return plain, held, repo


def _calibrated_plan(tmp_path, roots):
    return s1.admit(protocol_path=PROTOCOL, comparison_set_path=_declaration(tmp_path, roots),
                    output_path=tmp_path / 'out.json', lost_root=str(tmp_path / 'lost-brain'),
                    attempt_ledger=str(tmp_path / 'ledger'), calibrate=True)


def test_calibration_never_reads_held_out_roots_or_git_blobs(tmp_path, monkeypatch):
    plain, held, repo = _calibration_fixture(tmp_path)
    original = Path.read_bytes

    def guarded(self):
        if str(self).startswith((str(held), str(repo))):
            raise AssertionError(f'calibration read protected content {self}')
        return original(self)
    monkeypatch.setattr(Path, 'read_bytes', guarded)
    monkeypatch.setattr(s1, '_git_blobs', lambda *a: (_ for _ in ()).throw(
        AssertionError('calibration read git blobs')))
    roots = [_git_root(repo), _dir_root(repo, name='work'), _dir_root(plain, name='plain'),
             _dir_root(held, name='held', held_out_payloads=True)]
    plan = _calibrated_plan(tmp_path, roots)
    calibration = plan['throughput']['calibration']
    assert calibration['read_scope'] == ['plain']
    assert plan['contents_read'] == 'calibration sample from non-held-out directory roots only'


def test_calibration_sample_rule_and_projection_formula(tmp_path):
    plain, held, repo = _calibration_fixture(tmp_path)
    roots = [_dir_root(plain, name='plain'),
             _dir_root(held, name='held', held_out_payloads=True)]
    estimate = _calibrated_plan(tmp_path, roots)['throughput']
    calibration = estimate['calibration']
    json_row = calibration['by_suffix']['.json']
    assert json_row['sample_bytes'] >= 0.1 * json_row['eligible_bytes']
    assert 0 <= json_row['pass_fraction'] <= 1
    assert json_row['pass_upper'] == min(1.0, 2 * json_row['pass_fraction'] + 0.05)
    assert calibration['by_suffix']['.md']['sample_bytes'] == \
        calibration['by_suffix']['.md']['eligible_bytes']
    assert 'pass_upper = min(1, 2 x observed pass fraction + 0.05)' in calibration['rule']
    assert calibration['cpu_seconds'] >= 0
    full, miss = calibration['full_mb_per_s'] * 1e6, calibration['miss_mb_per_s'] * 1e6
    expected = estimate['covered_by_git_blobs_bytes'] / (estimate['digest_mb_per_s'] * 1e6)
    for suffix, size in estimate['deduplicated_bytes_by_suffix'].items():
        upper = calibration['by_suffix'].get(suffix, {'pass_upper': 1.0})['pass_upper']
        expected += size * (upper / full + (1 - upper) / miss)
    assert calibration['projected_cpu_seconds'] == pytest.approx(expected)
    assert estimate['projected_cpu_seconds'] > 0  # the conservative figure is still reported
    assert calibration['full_mb_per_s'] <= estimate['sample_mb_per_s']


def test_calibration_sample_is_deterministic(tmp_path):
    plain, _, _ = _calibration_fixture(tmp_path)
    roots = [_dir_root(plain, name='plain')]
    first = _calibrated_plan(tmp_path, roots)['throughput']['calibration']
    second = _calibrated_plan(tmp_path, roots)['throughput']['calibration']
    assert first['sample_digest'] == second['sample_digest']


def _slow_full_rate(monkeypatch, plan):
    unique = plan['throughput']['deduplicated_total_bytes']
    monkeypatch.setattr(s1, '_sample_rate', lambda: unique / 1e6 / 1000.0)  # 1000 CPU-s


def test_blocker_uses_calibrated_projection(tmp_path, monkeypatch):
    plain, _, _ = _calibration_fixture(tmp_path)
    roots = [_dir_root(plain, name='plain')]
    _slow_full_rate(monkeypatch, _plan(tmp_path, roots))
    assert any('throughput' in b for b in _plan(tmp_path, roots)['blockers'])
    calibrated = _calibrated_plan(tmp_path, roots)
    assert calibrated['throughput']['calibration']['projected_cpu_seconds'] < 528
    assert not any('throughput' in b for b in calibrated['blockers'])


def test_execute_uses_only_a_matching_calibration_record(tmp_path, monkeypatch):
    plain, _, _ = _calibration_fixture(tmp_path)
    roots = [_dir_root(plain, name='plain')]
    _slow_full_rate(monkeypatch, _plan(tmp_path, roots))
    record = _write(tmp_path / 'records' / 'plan.json',
                    s1.canonical_bytes(_calibrated_plan(tmp_path, roots)).decode())
    with pytest.raises(s1.AdmissionRefused, match='throughput'):
        _admit(tmp_path, roots)
    declaration = _declaration(tmp_path, roots)

    def run(output):
        return s1.admit(protocol_path=PROTOCOL, comparison_set_path=declaration,
                        output_path=output, execute=True, go_record_path=_go(tmp_path),
                        lost_root=str(tmp_path / 'lost-brain'),
                        attempt_ledger=str(tmp_path / 'ledgers' / output.parent.name),
                        calibration_record_path=record)
    result = run(tmp_path / 'ok' / 'r.json')
    assert result['verdict'] == 'admitted'
    report = _report(tmp_path / 'ok' / 'r.json')
    assert report['inputs']['calibration_record']['sha256'] == hashlib.sha256(
        record.read_bytes()).hexdigest()
    _write(plain / 'late.json', {'value': 1})
    with pytest.raises(s1.AdmissionRefused, match='calibration record'):
        run(tmp_path / 'stale' / 'r.json')
