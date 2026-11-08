"""MaleCNS v4 Amendment 1 port trees: diff-restricted review and function-level equivalence.

No producer is run and no real or held-out data is opened. Real-repository reads are git
objects (producing commits and port branches) and plan documents. Equivalence tests compile
single functions out of the original and port blobs into namespaces whose collaborators are
synthetic stubs; the original runs with its original pins, the port with a synthetic v4
locator whose documents carry the original (v2) counts.
"""
import ast
import copy
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys
import time
import types

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import build_male_navigation_v4_ports as ports  # noqa: E402

PROTOCOL = ROOT/'docs/plans/m7-navigation-v4-regenerated-matched-budget-protocol.json'
SPEC = ports.load_spec()
ENV = SPEC['locator']['env']
TREE_FOR_BASE = {t['base'][:7]: k for k, t in SPEC['trees'].items()}


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def blob(rev, path):
    return subprocess.run(['git', 'show', f'{rev}:{path}'], cwd=ROOT, capture_output=True, check=True).stdout


def port_rev(tree_id):
    return SPEC['trees'][tree_id]['branch']


def git(cwd, *args):
    return subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', *args], cwd=cwd,
                          check=True, capture_output=True, text=True).stdout.strip()


# =================================================================== manifest vs. amendment_1

def amendment():
    raw = PROTOCOL.read_bytes()
    assert sha(raw) == SPEC['protocol_sha256'] == ports.PROTOCOL_SHA256
    return json.loads(raw)['amendment_1']


def test_manifest_lists_exactly_the_amendment_hunks_with_their_classes():
    listed = {(item['file'], h['lines'], h['class']) for item in amendment()['ports'] for h in item['hunks']}
    manifest = {(path, h['spec_lines'], h['class']) for path, f in SPEC['files'].items() for h in f['hunks']}
    assert manifest == listed


def test_manifest_trees_follow_the_amendment_port_trees():
    declared = {t['id']: t for t in amendment()['port_trees']}
    assert set(SPEC['trees']) == set(declared) == {'T-c', 'T-d', 'T-e', 'T-h', 'T-f'}
    for tree_id, tree in SPEC['trees'].items():
        assert tree['base'] == declared[tree_id]['base']
        assert tree['branch'] == f'port/male-v4-{tree_id.lower()}'
        listed = {p.split(' ')[0] for p in declared[tree_id]['ports']}
        assert set(tree['files']) <= listed, tree_id
    # The reader is ported into T-e only if imported there; at 736e0cf it is not.
    assert 'scripts/prepare_male_recovery_data.py' not in SPEC['trees']['T-e']['files']
    importers = subprocess.run(['git', 'grep', '-l', 'import prepare_male_recovery_data', SPEC['trees']['T-e']['base'],
                                '--', 'src', 'scripts/collect_male_navigation_v2.py', 'scripts/collect_male_navigation.py'],
                               cwd=ROOT, capture_output=True, text=True).stdout
    assert importers == ''
    # S0a (cc1cea9) and S0b (c382c86) run unchanged: no port tree.
    assert not {'cc1cea9', 'c382c86'} & set(TREE_FOR_BASE)


def test_every_hunk_classes_h1_to_h3_only_and_h4_is_not_code():
    classes = {h['class'] for f in SPEC['files'].values() for h in f['hunks']}
    assert classes == {'H1', 'H2', 'H3'}


# =================================================================== port branches

@pytest.mark.parametrize('tree_id', sorted(SPEC['trees']))
def test_port_branch_exists_at_recorded_deterministic_commit(tree_id):
    tree = SPEC['trees'][tree_id]
    assert tree['port_commit'] and ports.branch_commit(ROOT, tree['branch']) == tree['port_commit']
    assert ports.build_commit(ROOT, SPEC, tree_id) == tree['port_commit']


@pytest.mark.parametrize('tree_id', sorted(SPEC['trees']))
def test_exact_diff_is_only_the_listed_hunks(tree_id):
    tree = SPEC['trees'][tree_id]
    changed = git(ROOT, 'diff', '--no-renames', '--name-only', tree['base'], tree['branch']).split()
    assert sorted(changed) == sorted(tree['files'])
    for path in tree['files']:
        base, port = blob(tree['base'], path), blob(tree['branch'], path)
        assert port == ports.apply_hunks(base, SPEC['files'][path]['hunks'], name=path)
        hunks = SPEC['files'][path]['hunks']
        ranges = ports.diff_ranges(ROOT, tree['base'], tree['branch'], path)
        assert ranges and all(ports.contained(first, count, hunks) for first, count in ranges)
        # Every non-empty listed hunk changes something; unchanged lines keep their bytes.
        for hunk in hunks:
            if hunk.get('empty'): continue
            assert any(hunk['start'] - 1 <= first <= hunk['start'] + len(hunk['old']) - 1 for first, _ in ranges)
    assert ports.verify_port(ROOT, SPEC, tree_id, tree['port_commit'])['commit'] == tree['port_commit']


def test_reader_port_is_identical_in_every_tree_that_carries_it():
    payloads = {blob(SPEC['trees'][t]['branch'], 'scripts/prepare_male_recovery_data.py')
                for t in ('T-c', 'T-d', 'T-h', 'T-f')}
    assert len(payloads) == 1


def test_verify_cli_passes_on_the_real_branches(capsys):
    assert ports.main(['--verify']) == 0
    assert json.loads(capsys.readouterr().out)['status'] == 'verified'


def test_h2_relaunch_hunks_are_empty_and_the_child_is_the_port():
    found = {}
    for path, item in SPEC['files'].items():
        for hunk in item['hunks']:
            if hunk['class'] != 'H2': continue
            assert hunk.get('empty') and hunk['old'] == hunk['new'] == []
            tree_id = next(t for t, tree in SPEC['trees'].items() if path in tree['files'] and
                           tree['stage'] in ('S0e', 'S0f'))
            base = blob(SPEC['trees'][tree_id]['base'], path).decode().split('\n')
            port = blob(SPEC['trees'][tree_id]['branch'], path).decode().split('\n')
            # The relaunch line is byte-identical and still re-executes this very file (the port).
            line = base[hunk['start'] - 1]
            assert hunk['unchanged_line_contains'] in line and line in port
            found[path] = line
    assert set(found) == {'scripts/collect_male_navigation_v2.py', 'scripts/prepare_male_navigation_v2.py'}
    assert '__file__' in found['scripts/collect_male_navigation_v2.py']
    script = blob(SPEC['trees']['T-f']['branch'], 'scripts/prepare_male_navigation_v2.py').decode()
    assert 'SCRIPT = Path(__file__).resolve()' in script and 'str(SCRIPT)' in found['scripts/prepare_male_navigation_v2.py']
    # The locator reaches both children: bounded_process inherits os.environ and -I keeps non-PYTHON* vars.
    assert not ENV.startswith('PYTHON')
    child = blob(SPEC['trees']['T-e']['branch'], 'scripts/collect_male_navigation_v2.py').decode()
    assert "{**os.environ,'PYTHONPATH'" in child


def test_import_time_reads_touch_only_the_locator_documents():
    """Every replaced pin literal now reads the locator; no original pin literal survives in a port."""
    stale = ('091c4e98bf8bc4124383673783a21f5687112946ffeaa54c8a70c41e968f2b28',
             'cf50fd2f6a96cfb1afd43e23eae05b76522116abdcf544ef41735033dc52b6b5',
             '402d2676668e88bb998457ba0a9ea92f8a4c2a27b92a19d67ad76b80e3a67014',
             '29039e944f49dc1458d918dcd738a32ee5fbf5bfdbbee8fff2cd969e4703bab0',
             'a3612cdc23510fa2b866482e1d13ece123940911ccc2a186c74216c83177e47f',
             'd2b998cdd4763a4b173bfe712ba0c50d19c7cfd56b68e44c395c575cdcfa2feb',
             'data/manifests/male-recovery-research-development-v1.json',
             'docs/plans/m7-recovery-learning-protocol.json')
    v2 = ast.parse(blob(port_rev('T-e'), 'scripts/collect_male_navigation_v2.py'))
    used_from_v1 = {a.name for n in v2.body if isinstance(n, ast.ImportFrom) and n.module == 'collect_male_navigation'
                    for a in n.names}
    for tree_id, tree in SPEC['trees'].items():
        for path in tree['files']:
            text = blob(tree['branch'], path).decode()
            found = [s for s in stale if s in text]
            if path == 'scripts/collect_male_navigation.py':
                # v1's own worker/verify keep their inline index path; S0e (v2) never reaches them.
                holders = {f.name for f in ast.parse(text).body if isinstance(f, ast.FunctionDef)
                           and any(isinstance(c, ast.Constant) and c.value in stale for c in ast.walk(f))}
                assert holders == {'worker', 'verify'} and not holders & used_from_v1
                assert found == ['data/manifests/male-recovery-research-development-v1.json']
            else:
                assert not found, (tree_id, path)
            assert f"environ['{ENV}']" in text


# =================================================================== refusals of the builder

def test_hunk_that_does_not_apply_exactly_is_refused():
    base = blob(SPEC['trees']['T-c']['base'], 'scripts/prepare_male_recovery_data.py')
    hunks = copy.deepcopy(SPEC['files']['scripts/prepare_male_recovery_data.py']['hunks'])
    hunks[1]['old'][0] = hunks[1]['old'][0].replace('67', '68')
    with pytest.raises(ports.PortRefusal, match='does not apply exactly'):
        ports.apply_hunks(base, hunks)
    hunks = copy.deepcopy(SPEC['files']['scripts/prepare_male_recovery_data.py']['hunks'])
    hunks[1]['start'] += 1
    with pytest.raises(ports.PortRefusal, match='does not apply exactly'):
        ports.apply_hunks(base, hunks)
    empty = copy.deepcopy(SPEC['files']['scripts/collect_male_navigation_v2.py']['hunks'])
    next(h for h in empty if h.get('empty'))['start'] += 3
    with pytest.raises(ports.PortRefusal, match='empty hunk site'):
        ports.apply_hunks(blob(SPEC['trees']['T-e']['base'], 'scripts/collect_male_navigation_v2.py'), empty)


def test_changed_base_pin_is_refused():
    spec = copy.deepcopy(SPEC)
    spec['files']['scripts/train_male_recovery.py']['base_sha256'] = '0'*64
    with pytest.raises(ports.PortRefusal, match='base bytes differ'):
        ports.expected_files(ROOT, spec, 'T-d')


def synthetic_repo(tmp_path):
    repo = tmp_path/'repo'; (repo/'scripts').mkdir(parents=True)
    (repo/'scripts/a.py').write_text('X = 1\nY = 2\nZ = 3\n'); (repo/'scripts/b.py').write_text('B = 1\n')
    git(tmp_path, 'init', '-q', str(repo)); git(repo, 'add', '-A'); git(repo, 'commit', '-q', '-m', 'base')
    base = git(repo, 'rev-parse', 'HEAD')
    spec = {'schema': ports.SCHEMA, 'protocol_sha256': ports.PROTOCOL_SHA256,
            'commit_identity': SPEC['commit_identity'],
            'files': {'scripts/a.py': {'base_sha256': sha(b'X = 1\nY = 2\nZ = 3\n'), 'hunks': [
                {'spec_lines': '2', 'class': 'H3', 'start': 2, 'old': ['Y = 2'], 'new': ['Y = pins()']}]}},
            'trees': {'T-x': {'base': base, 'stage': 'S0x', 'files': ['scripts/a.py'], 'branch': 'port/male-v4-t-x',
                              'port_commit': None}}}
    return repo, base, spec


def test_builder_is_deterministic_and_creates_only_the_listed_change(tmp_path):
    repo, base, spec = synthetic_repo(tmp_path)
    first = ports.build(repo, spec)['T-x']
    assert ports.build_commit(repo, spec, 'T-x') == first
    assert git(repo, 'show', f'{first}:scripts/a.py') == 'X = 1\nY = pins()\nZ = 3'
    assert git(repo, 'rev-parse', 'port/male-v4-t-x') == first
    spec['trees']['T-x']['port_commit'] = first
    assert ports.verify(repo, spec)['T-x']['commit'] == first


def test_unlisted_byte_or_file_difference_on_a_port_branch_is_refused(tmp_path):
    repo, base, spec = synthetic_repo(tmp_path)
    git(repo, 'checkout', '-q', '-b', 'port/male-v4-t-x')
    (repo/'scripts/a.py').write_text('X = 1\nY = pins()\nZ = 4\n'); git(repo, 'commit', '-qam', 'extra byte')
    bad = git(repo, 'rev-parse', 'HEAD')
    with pytest.raises(ports.PortRefusal, match='port bytes differ'):
        ports.verify_port(repo, spec, 'T-x', bad)
    (repo/'scripts/a.py').write_text('X = 1\nY = pins()\nZ = 3\n'); (repo/'scripts/b.py').write_text('B = 2\n')
    git(repo, 'commit', '-qam', 'unlisted file')
    with pytest.raises(ports.PortRefusal, match='parent is not the producing commit'):
        ports.verify_port(repo, spec, 'T-x', git(repo, 'rev-parse', 'HEAD'))
    git(repo, 'reset', '-q', '--soft', base); git(repo, 'commit', '-qm', 'squashed')
    with pytest.raises(ports.PortRefusal, match='changed files'):
        ports.verify_port(repo, spec, 'T-x', git(repo, 'rev-parse', 'HEAD'))
    # An existing branch at another commit is never moved.
    with pytest.raises(ports.PortRefusal, match='exists at'):
        ports.build(repo, spec)
    assert git(repo, 'rev-parse', 'port/male-v4-t-x') == git(repo, 'rev-parse', 'HEAD')
    spec['trees']['T-x']['port_commit'] = ports.build_commit(repo, spec, 'T-x')
    with pytest.raises(ports.PortRefusal, match='not the recorded'):
        ports.verify(repo, spec)
