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


# =================================================================== function-level equivalence
# Original functions run with their original pins rebound in-process (module-level names set
# to the synthetic documents); port functions take every pin from the synthetic v4 locator.

V2_BASELINE, V2_DEV, V2_RECOVERY = [248]*7 + [247], [307]*4, [67, 67]
V2_ADVICE = [424]*4 + [423]*8
LEARNING, DATA_V2 = 'm7-recovery-learning-protocol.json', 'm7-navigation-data-v2-protocol.json'


def extract(source, names, namespace, assigns=()):
    """Compile only the named top-level functions (and module-level assignments) into ``namespace``."""
    tree = ast.parse(source)
    nodes = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in names) or
             (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in assigns for t in n.targets))]
    assert {n.name for n in nodes if isinstance(n, ast.FunctionDef)} == set(names)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<extracted>', 'exec'), namespace)
    return namespace


def write_doc(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, indent=1) + '\n').encode(); path.write_bytes(raw)
    return {'path': str(path), 'sha256': sha(raw)}


@pytest.fixture
def locator(tmp_path, monkeypatch):
    """Writes v4 documents and the port-pin locator; sets the locator variable."""
    def write(documents, data_manifest=None):
        entries = {name: write_doc(tmp_path/'v4'/name, value) for name, value in documents.items()}
        loc = tmp_path/'v4'/'port-pins.json'
        loc.write_text(json.dumps({'schema': SPEC['locator']['schema'], 'documents': entries, 'data_manifest': data_manifest}))
        monkeypatch.setenv(ENV, str(loc))
        return entries
    return write


def artifacts_stub(manifests=None):
    return types.SimpleNamespace(_read=lambda path, cap=None: Path(path).read_bytes(), _json=json.loads,
                                 _safe_path=lambda p: Path(p).absolute(), _manifest=lambda run: (manifests or {}).get(Path(run).name, {}),
                                 _load=lambda run: None, _id=lambda name: None)


def episodes(lengths, prefix, rng):
    return [{'run_id': f'{prefix}{i}', 'episode': 0, 'features': rng.random((n, 388), dtype=np.float32),
             'targets': rng.random((n, 2), dtype=np.float32)} for i, n in enumerate(lengths)]


def windows(n):
    return [32]*(n//32) + ([n % 32] if n % 32 else [])


def learning_doc(baseline, dev, recovery, *, hashes=None, recovery_runs=('rec-a', 'rec-b')):
    hashes = hashes or {}
    return {'preparation_limits': {'seconds': 180}, 'recovery_protocol_sha256': 'r'*64, 'baseline_protocol_sha256': 'b'*64,
            'baseline_collection_sha256': hashes.get('baseline'), 'recovery_report_sha256': hashes.get('report'),
            'recovery_source_commit': 'c'*40, 'source_limits': {'max_bytes': 3*1024**3},
            'recovery_sources': [{'case_id': f'case-{s}', 'seed': s, 'run_id': run, 'result_sha256': hashes.get(f'case-{s}')}
                                 for s, run in zip((2100, 2101), recovery_runs)],
            'counts': {'baseline_train': sum(baseline), 'dev': sum(dev), 'held_out': 0, 'recovery_train': sum(recovery),
                       'train': sum(baseline) + sum(recovery), 'per_source': {'baseline_train': list(baseline), 'dev': list(dev)},
                       'v2_reference_counts': {'baseline_train': 1983, 'dev': 1228, 'held_out': 0, 'recovery_train': 134, 'train': 2117}},
            'recovery_ticks_each': list(recovery), 'recovery_windows': [windows(n) for n in recovery]}


def outcome(function, *args, **kwargs):
    try: return ('ok', function(*args, **kwargs))
    except Exception as error: return ('refused', type(error).__name__, str(error))


# ------------------------------------------------------------------- S0c: prepare_male_recovery_data

READER_FUNCTIONS = ('protocol', 'frozen_json', 'validate_splits')


def reader_namespaces(learning_path, learning_sha, *, extra=(), stubs=None, port_tree='T-c'):
    """(original, port) namespaces of the reader functions (the reader port is identical in every tree)."""
    path, out = 'scripts/prepare_male_recovery_data.py', []
    for rev, port in ((SPEC['trees'][port_tree]['base'], False), (SPEC['trees'][port_tree]['branch'], True)):
        ns = {'json': json, 'os': __import__('os'), 'Path': Path, 'hashlib': hashlib, 'math': math, 'time': time,
              'np': np, 'MAX_JSON': 4*1024**2, 'ROOT': Path('/nonexistent-root'), 'artifacts': artifacts_stub(), **(stubs or {})}
        if port: extract(blob(rev, path), (), ns, assigns=('PROTOCOL_PATH', 'PROTOCOL_SHA256'))
        else: ns.update(PROTOCOL_PATH=learning_path, PROTOCOL_SHA256=learning_sha)  # original pins rebound in-process
        out.append(extract(blob(rev, path), READER_FUNCTIONS + tuple(extra), ns))
    return out


def s0c_fixture(tmp_path, locator, baseline=V2_BASELINE, dev=V2_DEV, recovery=V2_RECOVERY, *, data_baseline=None, pins=None):
    """Synthetic S0a/S0b documents and runs; returns (orig, port, baseline_path, report_path)."""
    rng = np.random.default_rng(7)
    data = {'train': episodes(data_baseline or baseline, 'base-', rng), 'dev': episodes(dev, 'dev-', rng), 'held_out': []}
    corpus, report_dir = tmp_path/'s0a', tmp_path/'s0b'
    runs = [{'run_id': f'base-{i}', 'split': 'train', 'status': 'completed', 'files': [{'path': 'recording/x', 'bytes': 1, 'sha256': 's'}]}
            for i in range(8)] + [{'run_id': f'dev-{i}', 'split': 'dev', 'status': 'completed', 'files': []} for i in range(4)]
    baseline_doc = write_doc(corpus/'collection.json', {'status': 'completed', 'stage': 'development',
                                                         'research_protocol_sha256': 'b'*64, 'runs': runs})
    hashes = {'baseline': baseline_doc['sha256']}
    for seed, run, n in zip((2100, 2101), ('rec-a', 'rec-b'), recovery):
        (report_dir/f'case-{seed}'/run/'recording').mkdir(parents=True)
        (report_dir/f'case-{seed}'/run/'recording'/'chunk').write_bytes(b'x'*n)
        hashes[f'case-{seed}'] = write_doc(report_dir/f'case-{seed}'/'result.json', {
            'status': 'completed-recording', 'case': {'seed': seed}, 'run': f'/x/{run}', 'engine_closed': True,
            'callback_restored': True, 'contact_ownership': 'own'})['sha256']
    report = write_doc(report_dir/'report.json', {
        'status': 'passed', 'protocol_status': 'completed', 'protocol_sha256': 'r'*64, 'numeric_ticks': sum(recovery),
        'owners_completed': 2, 'runtime_source': {'commit': 'c'*40}, 'harness_sha256': 'h',
        'cases': {f'case-{s}': {'status': 'completed-recording'} for s in (2100, 2101)},
        'artifacts_sha256': {f'case-{s}/{run}/recording/chunk': 'k'*64 for s, run in zip((2100, 2101), ('rec-a', 'rec-b'))}})
    hashes['report'] = report['sha256']
    entry = locator({LEARNING: learning_doc(*(pins or (baseline, dev, recovery)), hashes=hashes)})[LEARNING]
    manifests = {run: {'run_id': run, 'profile': 'male-recovery', 'controller': 'teacher', 'teacher_privileged': True,
                       'recorded_ticks': n, 'recovery_protocol_sha256': 'r'*64, 'recovery_collection_boundary': 'coverage_complete',
                       'recovery_contact_ownership': 'own'} for run, n in zip(('rec-a', 'rec-b'), recovery)}

    def admit_rows(raw_rows, result, run_id):
        n, local = manifests[run_id]['recorded_ticks'], np.random.default_rng(len(run_id) + ord(run_id[-1]))
        ep = {'run_id': run_id, 'episode': 0, 'features': local.random((n, 388), dtype=np.float32),
              'targets': local.random((n, 2), dtype=np.float32)}
        return ep, {'ending': 'right_censored_coverage_complete', 'windows': windows(n)}
    stubs = {'artifacts': artifacts_stub(manifests), 'reader_identity': lambda: {'current_reader_sources': {}, 'adapter_sha256': 'a'},
             'recovery': types.SimpleNamespace(PROTOCOL_SHA256='r'*64, PROFILE='male-recovery'),
             'male_model': types.SimpleNamespace(prepare_splits=lambda paths, research_stage: (copy.deepcopy(data), {'admitted': 12}),
                                                 check_sources=lambda admission: None, FEATURE_PROTOCOL={'f': 1},
                                                 digest=lambda value: 'feature-digest'),
             'inventory': lambda root, entries, deadline=math.inf: [dict(e) for e in entries],
             'iter_ticks': lambda path: [], 'admit_rows': admit_rows}
    orig, port = reader_namespaces(entry['path'], entry['sha256'], extra=('prepare',), stubs=stubs)
    return orig, port, Path(baseline_doc['path']), Path(report['path'])


def summary(result):
    """Comparable form of prepare()'s (data, manifest)."""
    if result[0] != 'ok': return result
    data, manifest = result[1]
    return ('ok', {k: [(e['run_id'], sha(e['features'].tobytes() + e['targets'].tobytes())) for e in v] for k, v in data.items()},
            json.dumps(manifest, sort_keys=True))


def test_s0c_prepare_port_equals_original_on_original_counts(tmp_path, locator):
    orig, port, baseline, report = s0c_fixture(tmp_path, locator)
    expected = summary(outcome(orig['prepare'], baseline, report))
    assert expected[0] == 'ok', expected
    assert summary(outcome(port['prepare'], baseline, report)) == expected
    assert json.loads(expected[2])['counts'] == {'train': 2117, 'dev': 1228, 'held_out': 0}
    assert port['PROTOCOL_PATH'] == orig['PROTOCOL_PATH'] and port['PROTOCOL_SHA256'] == orig['PROTOCOL_SHA256']


def test_s0c_validate_splits_port_equals_original_on_original_counts(tmp_path, locator):
    entry = locator({LEARNING: learning_doc(V2_BASELINE, V2_DEV, V2_RECOVERY)})[LEARNING]
    orig, port = reader_namespaces(entry['path'], entry['sha256'])
    rng = np.random.default_rng(3)
    data = {'train': episodes(V2_BASELINE + V2_RECOVERY, 't', rng), 'dev': episodes(V2_DEV, 'd', rng), 'held_out': []}
    for variant in (data, {**data, 'dev': data['dev'][:3]}, {**data, 'held_out': data['dev'][:1]}):
        assert outcome(port['validate_splits'], variant) == outcome(orig['validate_splits'], variant)
    assert outcome(port['validate_splits'], data)[1] == {'train': 2117, 'dev': 1228, 'held_out': 0}
    unchecked = {**data, 'train': data['train'][:5]}
    assert outcome(port['validate_splits'], unchecked, check_counts=False) == \
        outcome(orig['validate_splits'], unchecked, check_counts=False)


def test_s0c_admit_rows_length_gate_matches_original_and_follows_the_per_source_pin(tmp_path, locator):
    doc = learning_doc(V2_BASELINE, V2_DEV, [67, 70])
    entry = locator({LEARNING: doc})[LEARNING]
    stubs = {'recovery': types.SimpleNamespace()}
    orig, port = reader_namespaces(entry['path'], entry['sha256'], extra=('admit_rows',), stubs=stubs)
    rows = lambda n: ([{'episode': 1}]*n, {'rows': [{'tick': 0}]*n})  # the cursor check right after the gate refuses
    for n in (66, 67, 68):
        assert outcome(port['admit_rows'], *rows(n), 'rec-a') == outcome(orig['admit_rows'], *rows(n), 'rec-a')
    passed_gate = ('refused', 'ValueError', 'Recovery fresh cursor/actual target/time/eyes differs')
    assert outcome(port['admit_rows'], *rows(67), 'rec-a') == passed_gate
    assert outcome(port['admit_rows'], *rows(70), 'rec-b') == passed_gate
    assert outcome(port['admit_rows'], *rows(67), 'rec-b')[2] == 'Exact full 67-row fresh recovery sequence required'
    doc['recovery_ticks_each'] = [67, 121]
    entry = locator({LEARNING: doc})[LEARNING]
    _, port = reader_namespaces(entry['path'], entry['sha256'], extra=('admit_rows',), stubs=stubs)
    assert outcome(port['admit_rows'], *rows(121), 'rec-b')[2] == 'Exact full 67-row fresh recovery sequence required'


def test_s0c_off_v2_lengths_are_admitted_only_with_matching_per_source_pins(tmp_path, locator):
    baseline, recovery = [250, 240, 260, 230, 255, 245, 251, 249], [70, 64]
    orig, port, b, r = s0c_fixture(tmp_path, locator, baseline=baseline, recovery=recovery)
    accepted = outcome(port['prepare'], b, r)
    assert accepted[0] == 'ok', accepted
    assert accepted[1][1]['counts'] == {'train': sum(baseline) + 134, 'dev': 1228, 'held_out': 0}
    assert [s['ticks'] for s in accepted[1][1]['ordered_sources']['train']] == baseline + recovery
    assert outcome(orig['prepare'], b, r)[0] == 'refused'  # the original's fixed 1983/67 rejects off-v2 lengths


@pytest.mark.parametrize('case, match', [
    ('truncated', 'Baseline row counts differ'),
    ('reordered', 'Baseline row counts differ'),
    ('over_bound', 'Fixed research train/dev row counts differ'),
    ('pins_sum_only', 'Baseline row counts differ'),
])
def test_s0c_failure_fixtures_are_refused_by_the_ported_invariants(tmp_path, locator, case, match):
    if case == 'truncated':      # one source shorter than its pin
        kwargs = {'data_baseline': V2_BASELINE[:7] + [246]}
    elif case == 'reordered':    # same sum, swapped order
        kwargs = {'data_baseline': [247] + [248]*7}
    elif case == 'over_bound':   # consistent pins and data, but one recovery source > 120 rows
        kwargs = {'recovery': [67, 121]}
    else:                        # pins whose sums match but whose per-source split differs
        kwargs = {'pins': ([250] + [248]*5 + [247, 242], V2_DEV, V2_RECOVERY)}
    orig, port, b, r = s0c_fixture(tmp_path, locator, **kwargs)
    result = outcome(port['prepare'], b, r)
    assert result[0] == 'refused' and result[2] == match, result
    if case == 'reordered':
        assert summary(outcome(orig['prepare'], b, r))[0] == 'ok'  # sums alone cannot see the reorder


@pytest.mark.parametrize('field', ['recovery_ticks_each', 'counts'])
def test_s0c_pending_pin_values_are_refused(tmp_path, locator, field):
    _, port, b, r = s0c_fixture(tmp_path, locator)
    doc = json.loads(Path(port['PROTOCOL_PATH']).read_text()); doc[field] = 'PENDING-S0b'
    entry = locator({LEARNING: doc})[LEARNING]
    port.update(PROTOCOL_PATH=entry['path'], PROTOCOL_SHA256=entry['sha256'])
    assert outcome(port['prepare'], b, r)[0] == 'refused'


# ------------------------------------------------------------------- S0e: male_recovery_research._gate/_history

def research_namespaces(stubs=None):
    path = 'src/palimpsest/male_recovery_research.py'
    out = []
    for rev in (SPEC['trees']['T-e']['base'], SPEC['trees']['T-e']['branch']):
        ns = {'Path': Path, 'math': math, 'MAX_JSON': 4*1024**2, 'PAIR_SEEDS': (10, 11, 12), 'artifacts': artifacts_stub(),
              'male_policy': types.SimpleNamespace(_sha=sha), **(stubs or {})}
        out.append(extract(blob(rev, path), ('read_pin', '_gate', '_history'), ns))
    return out


def gate_fixture(tmp_path, locator, *, recovery=V2_RECOVERY, data_ticks=None, data_windows=None, pins=None):
    root, producer = tmp_path/'root', tmp_path/'root/producer'
    files = {'src/palimpsest/male_model.py': b'model', 'scripts/collect_male_recovery.py': b'collector',
             'scripts/prepare_male_recovery_data.py': b'adapter', 'scripts/train_male_reduced.py': b'fitter'}
    for rel, payload in files.items():
        for base in (root, producer):
            (base/rel).parent.mkdir(parents=True, exist_ok=True); (base/rel).write_bytes(payload)
    code = {'reader': {'current_reader_sources': {k: sha(files[k]) for k in ('src/palimpsest/male_model.py',
                                                                             'scripts/collect_male_recovery.py')},
                       'adapter_sha256': sha(files['scripts/prepare_male_recovery_data.py'])},
            'trainer': {'scripts/train_male_reduced.py': sha(files['scripts/train_male_reduced.py'])}}
    terminal = write_doc(producer/'terminal.json', {
        'status': 'passed-research-training', 'head': 'd'*40, 'inventories_unchanged': True,
        'completed_pair_content_unchanged': True, 'before_inventory_sha256': 'i'*64, 'after_inventory_sha256': 'i'*64,
        'cleanup': {'sampler_stopped': True, 'sample_errors': [], 'forced_signals': [], 'survivors': []},
        'pairs': [{'training_seed': s, 'status': 'completed', 'supervision': {'status': 'completed', 'returncode': 0}}
                  for s in (10, 11, 12)]})
    outer = write_doc(producer/'outer.json', {'status': 'completed', 'returncode': 0, 'elapsed_seconds': 1200.0})
    ticks = data_ticks or (V2_BASELINE + list(recovery), V2_DEV)
    data = write_doc(producer/'data-manifest.json', {
        'status': 'prepared-research-only', 'counts': {'train': sum(ticks[0]), 'dev': sum(ticks[1]), 'held_out': 0},
        'ordered_sources': {'train': [{'run_id': f't{i}', 'ticks': n} for i, n in enumerate(ticks[0])],
                            'dev': [{'run_id': f'd{i}', 'ticks': n} for i, n in enumerate(ticks[1])], 'held_out': []},
        'recovery_admission': [{'windows': w} for w in (data_windows or [windows(n) for n in recovery])]})
    rel = lambda doc: {'path': str(Path(doc['path']).relative_to(producer)), 'sha256': doc['sha256']}
    index = {'producer_root': 'producer', 'training_terminal': rel(terminal), 'training_supervisor': rel(outer),
             'training_source_commit': 'd'*40, 'before_after_inventory_sha256': 'i'*64, 'training_source_code': code,
             'data_manifest': rel(data)}
    locator({LEARNING: learning_doc(*(pins or (V2_BASELINE, V2_DEV, recovery)))})
    return root, index


def test_gate_port_equals_original_on_original_counts(tmp_path, locator):
    root, index = gate_fixture(tmp_path, locator)
    orig, port = research_namespaces()
    expected = outcome(orig['_gate'], root, index)
    assert expected[0] == 'ok', expected
    assert outcome(port['_gate'], root, index) == expected
    for mutate in (lambda i: i.update(training_source_commit='e'*40), lambda i: i.update(before_after_inventory_sha256='j'*64)):
        changed = copy.deepcopy(index); mutate(changed)
        assert outcome(port['_gate'], root, changed) == outcome(orig['_gate'], root, changed)
        assert outcome(port['_gate'], root, changed)[0] == 'refused'


def test_gate_derives_windows_from_pinned_lengths_and_refuses_reorder_and_over_bound(tmp_path, locator):
    orig, port = research_namespaces()
    root, index = gate_fixture(tmp_path/'a', locator, recovery=[70, 64])
    assert outcome(port['_gate'], root, index)[0] == 'ok'          # windows [32,32,6] and [32,32]
    assert outcome(orig['_gate'], root, index)[0] == 'refused'
    reordered = (list(reversed(V2_BASELINE)) + V2_RECOVERY, V2_DEV)  # same sums, other order
    root, index = gate_fixture(tmp_path/'b', locator, data_ticks=reordered)
    assert outcome(orig['_gate'], root, index)[0] == 'ok'
    assert outcome(port['_gate'], root, index)[2] == 'Exact executed-target censored data required'
    root, index = gate_fixture(tmp_path/'c', locator, recovery=[67, 121])
    assert outcome(port['_gate'], root, index)[2] == 'Exact executed-target censored data required'
    root, index = gate_fixture(tmp_path/'d', locator, recovery=[67, 70], data_windows=[[32, 32, 3]]*2)
    assert outcome(port['_gate'], root, index)[2] == 'Exact executed-target censored data required'


def test_history_port_equals_original_on_original_counts(tmp_path, locator):
    locator({LEARNING: learning_doc(V2_BASELINE, V2_DEV, V2_RECOVERY)})
    orig, port = research_namespaces()
    rows = [{'epoch': e, 'train_ticks': 2117, 'train_loss': 1.0/e, 'dev': {'ticks': 1228, 'loss': abs(e-7)+.5,
            'velocity_mae': .1, 'wrapped_heading_mae_radians': .2}} for e in range(1, 21)]
    model = {'status': 'completed', 'history': rows, 'selected_epoch': 7}
    for variant in (model, {**model, 'selected_epoch': 8}, {**model, 'history': [{**rows[0], 'train_ticks': 2116}] + rows[1:]}):
        assert outcome(port['_history'], variant) == outcome(orig['_history'], variant)
    assert outcome(port['_history'], model) == ('ok', None)


def test_trainer_epoch_count_check_port_equals_original(tmp_path, locator):
    entry = locator({LEARNING: learning_doc(V2_BASELINE, V2_DEV, V2_RECOVERY)})[LEARNING]
    reader, = reader_namespaces(entry['path'], entry['sha256'], port_tree='T-d')[1:]
    path, results = 'scripts/train_male_recovery.py', []
    rows = [{'epoch': e, 'train_ticks': 2117, 'train_loss': 1.0, 'dev': {'ticks': 1228, 'loss': abs(e-3)+1.,
            'velocity_mae': .1, 'wrapped_heading_mae_radians': .2}} for e in range(1, 21)]
    for rev in (SPEC['trees']['T-d']['base'], SPEC['trees']['T-d']['branch']):
        ns = extract(blob(rev, path), ('validate_fit',), {'math': math, 'data_reader': types.SimpleNamespace(protocol=reader['protocol'])})
        results.append([outcome(ns['validate_fit'], r) for r in (
            {'history': rows, 'selected_epoch': 3}, {'history': [{**rows[0], 'train_ticks': 2118}] + rows[1:], 'selected_epoch': 3})])
    assert results[0] == results[1] and results[0][0] == ('ok', None)


# ------------------------------------------------------------------- S0f: prepare_male_navigation_v2

CASES = [{'id': f'learner-{scene}-seed-{seed}', 'scene_seed': scene, 'learner_seed': seed}
         for scene in range(3100, 3104) for seed in (10, 11, 12)]


def data_v2_doc(tmp_path, old_train, dev, advice):
    return {'immutable_inputs': {'accepted_collection': {'path': str(tmp_path/'s0e/collection/report.json'), 'sha256': 'a'*64},
                                 'old_manifest': {'path': str(tmp_path/'s0c/data-manifest.json'), 'sha256': 'm'*64}},
            'old_baseline_document': {'path': str(tmp_path/'s0a/collection.json'), 'sha256': 'b'*64},
            'source_binding': {'navigation_producer_commit': 'e'*40},
            'counts': {'old_sources': 14, 'new_sources': 12, 'combined_unique_sources': 26, 'old_train_rows': sum(old_train),
                       'new_advice_train_rows': sum(advice), 'augmented_train_rows': sum(old_train) + sum(advice),
                       'recorded_dev_rows': sum(dev), 'combined_rows': sum(old_train) + sum(advice) + sum(dev),
                       'held_out_sources': 0, 'held_out_rows': 0,
                       'per_source': {'old_train': list(old_train), 'dev': list(dev), 'advice': list(advice)},
                       'v2_reference_counts': {'old_train_rows': 2117, 'new_advice_train_rows': 5080,
                                               'augmented_train_rows': 7197, 'recorded_dev_rows': 1228}}}


def s0f_fixture(tmp_path, locator, *, advice=V2_ADVICE, data_advice=None, old_train=None, data_old=None, report_ticks=None):
    """(orig, port, output) for prepare(); every collaborator except the count checks is a stub."""
    old_train = old_train or V2_BASELINE + V2_RECOVERY
    data_advice = data_advice or advice
    rng = np.random.default_rng(5)
    old = {'train': episodes(data_old or old_train, 'old-', rng), 'dev': episodes(V2_DEV, 'dev-', rng), 'held_out': []}
    doc = data_v2_doc(tmp_path, old_train, V2_DEV, advice)
    learning = learning_doc(old_train[:8], V2_DEV, old_train[8:])
    entries = locator({DATA_V2: doc, LEARNING: learning})
    collection = Path(doc['immutable_inputs']['accepted_collection']['path']).parent
    cases, owners, arrays = {}, {}, {}
    for case, n in zip(CASES, data_advice):
        stage = collection/case['id']; run = stage/f'run{case["scene_seed"]}{case["learner_seed"]}'
        cases[case['id']] = {'run': str(run), 'case': case, 'status': 'completed-recording', 'result_path': str(stage/'result.json'),
                             'result_sha256': 'x', 'outcome': 'o', 'contact_incidence': {}, 'supervision': {'status': 'completed', 'returncode': 0}}
        owners[case['id']] = {'case': case, 'outcome': 'o', 'contact_incidence': {}, 'initial_world': {}, 'initial_fingerprint': 'f'}
        arrays[run.name] = (rng.random((n, 388), dtype=np.float32), rng.random((n, 2), dtype=np.float32))
    report = {'status': 'completed-collection', 'profile': 'P', 'study_sha256': 'S', 'contact_profile_sha256': 'C',
              'qualification_claims': [], 'owners_completed': 12, 'numeric_ticks': report_ticks or sum(data_advice),
              'cases': cases, 'source_pins': {'a': 1}, 'final_source_pins': {'a': 1}, 'assets_before': {'ok': True},
              'assets_after': {'ok': True}, 'identities_before': {'10': 'i', '11': 'i', '12': 'i'}, 'identities_after': {'10': 'i', '11': 'i', '12': 'i'},
              'artifacts_sha256': {}}
    clean = {'status': 'completed-collection', 'controls_unchanged': True, 'inventories_unchanged': True, 'outer_inventory_unchanged': True,
             'report_sha256': 'a'*64, 'head': 'e'*40}
    cleanup = {'sampler_stopped': True, 'forced_signals': [], 'survivors': [], 'sample_errors': [], 'conflicting_owned_identities': []}
    old_manifest = {'recovery_admission': [{'run_id': f'old-{i}', 'path': str(tmp_path/f'rec{i}'), 'files': []} for i in (8, 9)],
                    'ordered_sources': {'train': [], 'dev': []}}
    documents = {'accepted_collection': report, 'collection_terminal': {**clean, 'cleanup': cleanup},
                 'collection_enclosing': {**clean, 'outer_cleanup': cleanup},
                 'exec_drain': {'exec_exitcode': 0, 'matching_survivors': [], 'forced_signals': []},
                 'collector_supervisor': {'status': 'completed', 'returncode': 0}, 'launcher_supervisor': {'status': 'completed', 'returncode': 0},
                 'old_manifest': old_manifest,
                 'old_baseline_document': {'runs': [{'run_id': f'old-{i}', 'files': []} for i in range(8)] +
                                                   [{'run_id': f'dev-{i}', 'files': []} for i in range(4)]}}
    published = {}

    def read_json(path, maximum=None, expected=None):
        path = Path(path)
        if path.name == 'result.json': return owners[path.parent.name]
        raw = path.read_bytes()
        if expected is not None and sha(raw) != expected: raise ValueError('Pinned document changed')
        return json.loads(raw)
    storage = types.ModuleType('palimpsest.storage')
    storage.StorageBudget = lambda roots, limits: types.SimpleNamespace(check=lambda *a, **k: None)
    storage.StorageLimits = lambda **k: k
    evaluate = types.ModuleType('palimpsest.evaluate')
    evaluate.bounded_process = lambda *a, **k: {'status': 'completed', 'returncode': 0}
    nav = types.SimpleNamespace(PROFILE='P', PLAN_SHA='S', PROFILE_SHA='C', CASES=CASES,
                                admit_record=lambda run, owner, identity: len(arrays[Path(run).name][1]))
    model = types.SimpleNamespace(FEATURE_PROTOCOL={'f': 1}, digest=lambda v: 'd')
    path = 'scripts/prepare_male_navigation_v2.py'
    out = []
    readers = reader_namespaces(entries[LEARNING]['path'], entries[LEARNING]['sha256'], port_tree='T-f')
    for (rev, port), reader in zip(((SPEC['trees']['T-f']['base'], False), (SPEC['trees']['T-f']['branch'], True)), readers):
        old_module = types.SimpleNamespace(validate_splits=reader['validate_splits'], inventory=lambda run, files, deadline: [])
        ns = {'json': json, 'os': __import__('os'), 'Path': Path, 'hashlib': hashlib, 'math': math, 'time': time, 'sys': sys,
              'ROOT': Path('/nonexistent-root'), 'MiB': 1024**2, 'MAX_JSON': 4*1024**2, 'SELF_SHA': 's'*64,
              'SCRIPT': Path('/nonexistent-root/scripts/prepare_male_navigation_v2.py'),
              'RAW_PAYLOAD_FIELDS': ('action',), 'read_json': read_json,
              'reader_identity': lambda deadline, enforce=True: {'r': 1},
              'pinned_documents': lambda p, deadline: copy.deepcopy(documents),
              'historical_identity': lambda p, deadline, enforce=True: {'h': 1}, 'output_path': lambda output, p: Path(output),
              'write_payload': lambda path, payload, *a, **k: published.__setitem__((port, Path(path).name), payload),
              'read_old_transfer': lambda output, manifest, identity: copy.deepcopy(old),
              'episode_source': lambda run, episode, split, features, targets, deadline, world=None: {
                  'run_id': Path(run).name, 'split': split, 'ticks': len(targets)},
              'advice_arrays': lambda rows, deadline: arrays[rows],
              'validate_after': lambda *a, **k: None, 'disjoint_sources': lambda old, new: None}
        ns['helpers'] = (lambda old_module=old_module: (artifacts_stub(), model, lambda path: Path(path).parent.name, old_module, nav))
        if port: extract(blob(rev, path), (), ns, assigns=('PROTOCOL', 'PROTOCOL_SHA'))
        else: ns.update(PROTOCOL=entries[DATA_V2]['path'], PROTOCOL_SHA=entries[DATA_V2]['sha256'])  # original pins rebound
        out.append(extract(blob(rev, path), ('protocol', 'check_deadline', 'canonical', 'admit_collection', 'prepare'), ns))

    def run(ns, n):
        sys.modules['palimpsest.storage'], sys.modules['palimpsest.evaluate'] = storage, evaluate
        result = outcome(ns['prepare'], tmp_path/f'out-{n}')
        return result if result[0] != 'ok' else ('ok', json.dumps(result[1], sort_keys=True))
    return out[0], out[1], run, documents


@pytest.fixture
def stub_storage_modules(monkeypatch):
    for name in ('palimpsest.storage', 'palimpsest.evaluate'):
        monkeypatch.setitem(sys.modules, name, sys.modules.get(name, types.ModuleType(name)))


def test_s0f_prepare_port_equals_original_on_original_counts(tmp_path, locator, stub_storage_modules):
    orig, port, run, documents = s0f_fixture(tmp_path, locator)
    expected = run(orig, 'orig')
    assert expected[0] == 'ok', expected
    assert run(port, 'port') == expected
    manifest = json.loads(expected[1])
    assert [s['ticks'] for s in manifest['old_sources'] if s['split'] == 'train'] == V2_BASELINE + V2_RECOVERY
    assert [s['ticks'] for s in manifest['new_sources']] == V2_ADVICE


def test_s0f_admit_collection_port_equals_original(tmp_path, locator, stub_storage_modules):
    orig, port, run, documents = s0f_fixture(tmp_path, locator)
    p = orig['protocol']()
    for mutate in (lambda d: None, lambda d: d['accepted_collection'].update(numeric_ticks=5079),
                   lambda d: d['collection_terminal'].update(head='f'*40), lambda d: d['exec_drain'].update(exec_exitcode=1)):
        docs = copy.deepcopy(documents); mutate(docs)
        assert outcome(port['admit_collection'], p, docs) == outcome(orig['admit_collection'], p, docs)


@pytest.mark.parametrize('case, match', [
    ('missing_advice_source', 'Augmented exact arm counts differ'),
    ('advice_over_bound', 'Augmented exact arm counts differ'),
    ('advice_reordered', 'Augmented exact arm counts differ'),
    ('truncated_old_source', 'Fixed research train/dev row counts differ'),
    ('recovery_over_bound', 'Fixed research train/dev row counts differ'),
])
def test_s0f_failure_fixtures_are_refused_by_the_ported_invariants(tmp_path, locator, stub_storage_modules, case, match):
    kwargs = {'missing_advice_source': {'advice': [*V2_ADVICE[:10], V2_ADVICE[10] + V2_ADVICE[11]], 'data_advice': V2_ADVICE},
              'advice_over_bound': {'advice': [601] + V2_ADVICE[1:11] + [V2_ADVICE[11] - 177]},
              'advice_reordered': {'advice': list(reversed(V2_ADVICE)), 'data_advice': V2_ADVICE},
              'truncated_old_source': {'data_old': V2_BASELINE[:7] + [246] + V2_RECOVERY},
              'recovery_over_bound': {'old_train': V2_BASELINE + [67, 121]}}[case]
    orig, port, run, _ = s0f_fixture(tmp_path, locator, **kwargs)
    result = run(port, 'port')
    assert result[0] == 'refused' and result[2] == match, result
    if case in ('advice_over_bound', 'advice_reordered'):
        assert run(orig, 'orig')[0] == 'ok'  # sums alone cannot see either


def test_s0f_off_v2_lengths_are_admitted_with_matching_pins(tmp_path, locator, stub_storage_modules):
    advice = [500, 350, 410, 420, 430, 440, 450, 460, 470, 480, 490, 590]
    orig, port, run, _ = s0f_fixture(tmp_path, locator, advice=advice, old_train=V2_BASELINE[:7] + [250, 70, 64])
    accepted = run(port, 'port')
    assert accepted[0] == 'ok', accepted
    assert json.loads(accepted[1])['counts']['new_advice_train_rows'] == sum(advice)
    assert run(orig, 'orig')[0] == 'refused'
